import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class PlanoPagamentoEscola(models.Model):
    """
    Plano de Pagamentos / Tabela de Propinas e Emolumentos Própria da Instituição.
    Isolamento total:
    - O plano do Super Admin aplica-se unicamente às instituições (B2B SaaS).
    - Cada instituição cria e gere os seus próprios planos para aplicar aos seus alunos.
    - O que uma instituição faz no seu sistema não compromete nem reflecte noutra.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(
        'tenants.Escola',
        on_delete=models.CASCADE,
        related_name='planos_pagamento_escola',
        db_index=True
    )
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True, default='')
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    periodicidade = models.CharField(
        max_length=30,
        default='MENSAL',
        choices=[
            ('MENSAL', 'Mensal'),
            ('TRIMESTRAL', 'Trimestral'),
            ('SEMESTRAL', 'Semestral'),
            ('ANUAL', 'Anual'),
            ('UNICA', 'Taxa Única / Emolumento')
        ]
    )
    dia_vencimento_padrao = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    multa_atraso_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    multa_atraso_fixo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    ativo = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_planos_pagamento_escola'
        verbose_name = 'Plano de Pagamento da Escola'
        verbose_name_plural = 'Planos de Pagamento da Escola'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['ativo']),
            models.Index(fields=['periodicidade']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(valor__gte=0),
                name='check_plano_escola_valor_positivo'
            ),
            models.UniqueConstraint(
                fields=['escola', 'nome'],
                name='unique_escola_plano_nome'
            )
        ]

    def clean(self):
        from common.integrity import validar_integridade_tenant, IntegrityRuleViolation
        validar_integridade_tenant(self)
        if self.valor is not None and self.valor < 0:
            raise IntegrityRuleViolation("O valor do plano de pagamento não pode ser negativo.")
        if self.dia_vencimento_padrao and (self.dia_vencimento_padrao < 1 or self.dia_vencimento_padrao > 31):
            raise IntegrityRuleViolation("O dia de vencimento padrão deve situar-se entre 1 e 31.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.valor} MZN) [{self.escola.nome}]"


class Pagamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='pagamentos')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='pagamentos')
    plano_pagamento = models.ForeignKey(
        PlanoPagamentoEscola,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagamentos'
    )
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
            models.Index(fields=['plano_pagamento']),
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
            models.UniqueConstraint(
                fields=['escola', 'aluno', 'mes_referencia'],
                condition=~models.Q(status='CANCELADO'),
                name='unique_pagamento_aluno_mes'
            ),
        ]

    def clean(self):
        from common.integrity import validar_integridade_tenant, IntegrityRuleViolation
        validar_integridade_tenant(self, aluno=self.aluno, plano=self.plano_pagamento)
        if self.valor is not None and self.valor < 0:
            raise IntegrityRuleViolation("O valor do pagamento não pode ser negativo.")
        if self.valor_pago is not None and self.valor_pago < 0:
            raise IntegrityRuleViolation("O valor pago não pode ser negativo.")

        # Impedir duplicação de factura para o mesmo aluno e mês de referência
        if self.aluno_id and self.mes_referencia and self.status != 'CANCELADO':
            qs = Pagamento.objects.filter(
                escola_id=self.escola_id or (self.aluno.escola_id if self.aluno else None),
                aluno_id=self.aluno_id,
                mes_referencia=self.mes_referencia
            ).exclude(status='CANCELADO')
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise IntegrityRuleViolation("A factura já foi gerada no sistema.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aluno.nome} - {self.descricao} ({self.valor} MZN) [{self.status}]"
