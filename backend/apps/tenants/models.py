import uuid
from django.db import models
from django.utils import timezone

class Plano(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True, null=True)
    preco = models.DecimalField(max_digits=12, decimal_places=2)
    duracao_dias = models.IntegerField(default=30)
    max_alunos = models.IntegerField(default=500)
    max_professores = models.IntegerField(default=50)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_planos'
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'

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
    valor = models.DecimalField(max_digits=12, decimal_places=2)
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

    def __str__(self):
        return f"{self.escola.nome} - {self.plano.nome} ({self.status})"
