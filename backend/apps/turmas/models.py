import uuid
from django.db import models

class Turma(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='turmas')
    nome = models.CharField(max_length=100)
    grau_ano = models.CharField(max_length=50)  # ex: 10ª Classe
    turno = models.CharField(max_length=20, default='MANHA')  # MANHA, TARDE, NOITE
    sala = models.CharField(max_length=50, blank=True, null=True)
    capacidade_maxima = models.PositiveIntegerField(default=50)
    ano_letivo = models.CharField(max_length=10, default='2026')
    area = models.CharField(max_length=50, default='Geral')
    
    director_turma = models.ForeignKey(
        'professores.Professor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turmas_como_director_turma'
    )
    dt_status_homologacao = models.CharField(
        max_length=30,
        default='NAO_DEFINIDO'  # NAO_DEFINIDO, PENDENTE_HOMOLOGACAO, HOMOLOGADO, REJEITADO
    )
    dt_nomeado_por = models.CharField(max_length=255, blank=True, null=True)
    dt_data_nomeacao = models.DateTimeField(blank=True, null=True)
    dt_homologado_por = models.CharField(max_length=255, blank=True, null=True)
    dt_data_homologacao = models.DateTimeField(blank=True, null=True)
    codigo_director_turma = models.CharField(max_length=80, blank=True, null=True, db_index=True)

    director_classe = models.ForeignKey(
        'professores.Professor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turmas_como_director_classe'
    )
    dc_status_homologacao = models.CharField(
        max_length=30,
        default='NAO_DEFINIDO'  # NAO_DEFINIDO, PENDENTE_HOMOLOGACAO, HOMOLOGADO, REJEITADO
    )
    dc_nomeado_por = models.CharField(max_length=255, blank=True, null=True)
    dc_data_nomeacao = models.DateTimeField(blank=True, null=True)
    dc_homologado_por = models.CharField(max_length=255, blank=True, null=True)
    dc_data_homologacao = models.DateTimeField(blank=True, null=True)
    codigo_director_classe = models.CharField(max_length=80, blank=True, null=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_turmas'
        verbose_name = 'Turma'
        verbose_name_plural = 'Turmas'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['ano_letivo']),
            models.Index(fields=['grau_ano']),
            models.Index(fields=['codigo_director_turma']),
            models.Index(fields=['codigo_director_classe']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['escola', 'grau_ano', 'nome', 'ano_letivo'],
                name='unique_turma_escola_grau_nome_ano_letivo'
            ),
        ]

    def clean(self):
        from common.integrity import validar_integridade_tenant
        validar_integridade_tenant(self, director_turma=self.director_turma, director_classe=self.director_classe)
        validar_numero = True
        if self.id and not self._state.adding:
            antiga = Turma.objects.filter(id=self.id).values('nome', 'grau_ano', 'ano_letivo').first()
            if antiga and antiga['nome'] == self.nome and antiga['grau_ano'] == self.grau_ano and antiga['ano_letivo'] == self.ano_letivo:
                validar_numero = False
        if validar_numero:
            from .utils import validar_unicidade_turma_na_classe
            validar_unicidade_turma_na_classe(
                escola=self.escola,
                grau_ano=self.grau_ano,
                nome=self.nome,
                ano_letivo=self.ano_letivo,
                exclude_id=self.id
            )

    def save(self, *args, **kwargs):
        from django.utils import timezone
        from common.utils.geografia_mocambique import (
            gerar_codigo_director_turma,
            gerar_codigo_director_classe,
        )

        # Fluxo de Nomeação (Director Pedagógico) e Homologação (Director da Escola) para Director de Turma (DT)
        if not self.director_turma_id:
            self.dt_status_homologacao = 'NAO_DEFINIDO'
            self.codigo_director_turma = None
            self.dt_nomeado_por = None
            self.dt_data_nomeacao = None
            self.dt_homologado_por = None
            self.dt_data_homologacao = None
        else:
            if not self.dt_status_homologacao or self.dt_status_homologacao == 'NAO_DEFINIDO':
                self.dt_status_homologacao = 'PENDENTE_HOMOLOGACAO'
                if not self.dt_nomeado_por:
                    self.dt_nomeado_por = getattr(self.escola, 'dap_nome', None) or 'Direcção Pedagógica'
                if not self.dt_data_nomeacao:
                    self.dt_data_nomeacao = timezone.now()

            if self.dt_status_homologacao == 'HOMOLOGADO':
                self.codigo_director_turma = gerar_codigo_director_turma(self)
                if not self.dt_homologado_por:
                    self.dt_homologado_por = getattr(self.escola, 'director_nome', None) or 'Director da Escola'
                if not self.dt_data_homologacao:
                    self.dt_data_homologacao = timezone.now()
            else:
                self.codigo_director_turma = None

        # Fluxo de Nomeação (Director Pedagógico) e Homologação (Director da Escola) para Director de Classe (DC)
        if not self.director_classe_id:
            self.dc_status_homologacao = 'NAO_DEFINIDO'
            self.codigo_director_classe = None
            self.dc_nomeado_por = None
            self.dc_data_nomeacao = None
            self.dc_homologado_por = None
            self.dc_data_homologacao = None
        else:
            if not self.dc_status_homologacao or self.dc_status_homologacao == 'NAO_DEFINIDO':
                self.dc_status_homologacao = 'PENDENTE_HOMOLOGACAO'
                if not self.dc_nomeado_por:
                    self.dc_nomeado_por = getattr(self.escola, 'dap_nome', None) or 'Direcção Pedagógica'
                if not self.dc_data_nomeacao:
                    self.dc_data_nomeacao = timezone.now()

            if self.dc_status_homologacao == 'HOMOLOGADO':
                self.codigo_director_classe = gerar_codigo_director_classe(self)
                if not self.dc_homologado_por:
                    self.dc_homologado_por = getattr(self.escola, 'director_nome', None) or 'Director da Escola'
                if not self.dc_data_homologacao:
                    self.dc_data_homologacao = timezone.now()
            else:
                self.codigo_director_classe = None

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.ano_letivo})"
