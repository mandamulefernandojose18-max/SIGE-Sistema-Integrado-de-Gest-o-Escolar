import uuid
from django.db import models

class Pagamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='pagamentos')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='pagamentos')
    descricao = models.CharField(max_length=255)
    mes_referencia = models.CharField(max_length=20)  # ex: 2026-03
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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

    def __str__(self):
        return f"{self.aluno.nome} - {self.descricao} ({self.valor} MZN) [{self.status}]"
