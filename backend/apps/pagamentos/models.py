import uuid
from django.db import models
from django.core.validators import MinValueValidator

class Pagamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='pagamentos')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='pagamentos')
    descricao = models.CharField(max_length=255)
    mes_referencia = models.CharField(max_length=20)  # ex: 2026-03
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, default='PENDENTE')  # PENDENTE, PAGO, ATRASADO, CANCELADO
    data_vencimento = models.DateTimeField()
    data_pagamento = models.DateTimeField(null=True, blank=True)
    metodo_pagamento = models.CharField(max_length=50, blank=True, null=True)  # MPESA, EMOLA, POS, TRANSFERENCIA, NUMERARIO
    recibo_numero = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_pagamentos'
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['aluno']),
            models.Index(fields=['status']),
            models.Index(fields=['mes_referencia']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(valor__gte=0),
                name='check_pagamento_valor_positivo'
            ),
            models.CheckConstraint(
                check=models.Q(valor_pago__gte=0),
                name='check_pagamento_valor_pago_positivo'
            ),
        ]

    def clean(self):
        from common.integrity import validar_integridade_tenant, IntegrityRuleViolation
        validar_integridade_tenant(self, aluno=self.aluno)
        if self.valor is not None and self.valor < 0:
            raise IntegrityRuleViolation("O valor do pagamento não pode ser negativo.")
        if self.valor_pago is not None and self.valor_pago < 0:
            raise IntegrityRuleViolation("O valor pago não pode ser negativo.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aluno.nome} - {self.descricao} ({self.valor} MZN) [{self.status}]"
