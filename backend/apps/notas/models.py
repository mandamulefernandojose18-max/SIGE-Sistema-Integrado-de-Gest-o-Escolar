import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Nota(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='notas')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='notas')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.CASCADE, related_name='notas')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, related_name='notas')
    periodo = models.CharField(max_length=20)  # 1_TRIMESTRE, 2_TRIMESTRE, 3_TRIMESTRE, ANUAL

    teste1 = models.FloatField(
        default=0, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    teste2 = models.FloatField(
        default=0, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    teste3 = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    teste4 = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    trabalho = models.FloatField(
        default=0, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    avaliacao_trimestral = models.FloatField(
        default=0, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    media_final = models.FloatField(
        default=0,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    
    faltas = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    anotacao = models.CharField(max_length=10, blank=True, null=True)  # D, T, VT, F, AM, PPF, PDF
    comportamento = models.CharField(max_length=5, default='S')  # NS, S, B, MB, E
    resultado = models.CharField(max_length=20, default='Aprovado')  # Aprovado, Reprovado

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_notas'
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['aluno']),
            models.Index(fields=['disciplina']),
            models.Index(fields=['turma']),
            models.Index(fields=['periodo']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['escola', 'aluno', 'disciplina', 'turma', 'periodo'],
                name='unique_nota_aluno_disciplina_periodo'
            ),
            models.CheckConstraint(
                check=models.Q(media_final__gte=0.0) & models.Q(media_final__lte=20.0),
                name='check_nota_media_final_range'
            ),
            models.CheckConstraint(
                check=models.Q(faltas__gte=0),
                name='check_nota_faltas_positivas'
            ),
        ]

    def clean(self):
        from common.integrity import (
            validar_escala_nota, validar_faltas, validar_periodo_academico,
            validar_comportamento, validar_anotacao_minedh,
            validar_integridade_tenant, verificar_pauta_permite_edicao_nota
        )
        # 1. Integridade de Isolamento Multi-Tenant
        validar_integridade_tenant(self, aluno=self.aluno, disciplina=self.disciplina, turma=self.turma)

        # 2. Integridade de Domínio
        validar_periodo_academico(self.periodo)
        validar_comportamento(self.comportamento)
        validar_anotacao_minedh(self.anotacao)
        validar_faltas(self.faltas)

        for campo in ['teste1', 'teste2', 'teste3', 'teste4', 'trabalho', 'avaliacao_trimestral', 'media_final']:
            val = getattr(self, campo, None)
            if val is not None:
                validar_escala_nota(val)

        # 3. Integridade de Estado / Imutabilidade de Pauta Fechada
        verificar_pauta_permite_edicao_nota(self.escola, self.turma, self.disciplina, self.periodo)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aluno.nome} - {self.disciplina.nome} ({self.periodo}): {self.media_final}"

class PermissaoEdicaoNotas(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='permissoes_edicao')
    professor = models.ForeignKey('professores.Professor', on_delete=models.CASCADE, related_name='permissoes_edicao')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, related_name='permissoes_edicao')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.CASCADE, related_name='permissoes_edicao')
    periodo = models.CharField(max_length=20)  # 1_TRIMESTRE, 2_TRIMESTRE
    autorizado_por = models.CharField(max_length=255)
    motivo = models.TextField(blank=True, null=True)
    ativa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_permissoes_edicao_notas'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['professor']),
            models.Index(fields=['ativa']),
        ]

    def clean(self):
        from common.integrity import validar_integridade_tenant, validar_periodo_academico
        validar_integridade_tenant(self, professor=self.professor, turma=self.turma, disciplina=self.disciplina)
        validar_periodo_academico(self.periodo)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
