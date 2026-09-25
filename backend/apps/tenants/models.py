import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

from decimal import Decimal

class Plano(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True, null=True)
    preco = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    duracao_dias = models.IntegerField(default=30, validators=[MinValueValidator(1)])
    max_alunos = models.IntegerField(default=500, validators=[MinValueValidator(1)])
    max_professores = models.IntegerField(default=50, validators=[MinValueValidator(1)])
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_planos'
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'
        constraints = [
            models.CheckConstraint(check=models.Q(preco__gte=0), name='check_plano_preco_positivo'),
            models.CheckConstraint(check=models.Q(max_alunos__gte=1), name='check_plano_max_alunos_positivo'),
            models.CheckConstraint(check=models.Q(max_professores__gte=1), name='check_plano_max_professores_positivo'),
        ]

    def clean(self):
        from common.integrity import IntegrityRuleViolation
        if self.preco is not None and self.preco < 0:
            raise IntegrityRuleViolation("O preço do plano não pode ser negativo.")
        if self.max_alunos is not None and self.max_alunos < 1:
            raise IntegrityRuleViolation("A quota máxima de alunos deve ser de pelo menos 1.")
        if self.max_professores is not None and self.max_professores < 1:
            raise IntegrityRuleViolation("A quota máxima de professores deve ser de pelo menos 1.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.preco} MZN)"

class Escola(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    nif_cnpj = models.CharField(max_length=50, unique=True)
    endereco = models.TextField(blank=True, null=True)
    telefone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(unique=True)
    logo_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, default='ATIVA')  # ATIVA, PENDENTE, EXPIRADA, SUSPENSA
    ano_letivo_ativo = models.CharField(max_length=10, default='2026')
    trimestre_ativo = models.CharField(max_length=20, default='1_TRIMESTRE')
    plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True, blank=True, related_name='escolas')
    data_adesao = models.DateTimeField(default=timezone.now)

    # Dados Oficiais para Documentação MINEDH
    provincia = models.CharField(max_length=100, default='Maputo')
    distrito = models.CharField(max_length=100, default='Cidade de Maputo')
    director_nome = models.CharField(max_length=255, default='Prof. Dr. António Costa')
    director_carreira = models.CharField(max_length=100, default='Professor Doutor')
    dap_nome = models.CharField(max_length=255, default='Prof. João Baptista')
    chefe_secretaria_nome = models.CharField(max_length=255, default='Dra. Maria Eunice')
    usar_emblema_nacional = models.BooleanField(default=True)
    codigo_escola = models.CharField(max_length=50, blank=True, null=True)
    logo_base64 = models.TextField(blank=True, null=True)
    bloqueada_manualmente = models.BooleanField(default=False)
    permitir_visualizacao_notas = models.BooleanField(default=True)

    # Inscrições Online
    inscricoes_abertas = models.BooleanField(default=False)
    inscricoes_inicio = models.DateTimeField(null=True, blank=True)
    inscricoes_fim = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_escolas'
        verbose_name = 'Escola (Tenant)'
        verbose_name_plural = 'Escolas (Tenants)'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.nome} [{self.status}]"

class AssinaturaEscola(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='assinaturas')
    plano = models.ForeignKey(Plano, on_delete=models.CASCADE, related_name='assinaturas')
    data_inicio = models.DateTimeField(default=timezone.now)
    data_fim = models.DateTimeField()
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, default='ATIVA')  # ATIVA, PENDENTE, EXPIRADA, SUSPENSA
    metodo_pagamento = models.CharField(max_length=50, default='TRANSFERENCIA')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_assinaturas_escolas'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['status']),
            models.Index(fields=['data_fim']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(data_fim__gte=models.F('data_inicio')),
                name='check_assinatura_datas_coerentes'
            ),
            models.CheckConstraint(
                check=models.Q(valor__gte=0),
                name='check_assinatura_valor_positivo'
            ),
        ]

    def clean(self):
        from common.integrity import IntegrityRuleViolation
        if self.data_fim and self.data_inicio and self.data_fim < self.data_inicio:
            raise IntegrityRuleViolation("A data de término da assinatura não pode ser anterior à data de início.")
        if self.valor is not None and self.valor < 0:
            raise IntegrityRuleViolation("O valor da assinatura não pode ser negativo.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.escola.nome} - {self.plano.nome} ({self.status})"
