import uuid
from django.db import models

class Nota(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='notas')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='notas')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.CASCADE, related_name='notas')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, related_name='notas')
    periodo = models.CharField(max_length=20)  # 1_TRIMESTRE, 2_TRIMESTRE, 3_TRIMESTRE

    teste1 = models.FloatField(default=0, null=True, blank=True)
    teste2 = models.FloatField(default=0, null=True, blank=True)
    teste3 = models.FloatField(null=True, blank=True)
    teste4 = models.FloatField(null=True, blank=True)
    trabalho = models.FloatField(default=0, null=True, blank=True)
    avaliacao_trimestral = models.FloatField(default=0, null=True, blank=True)
    media_final = models.FloatField(default=0)  # Arredondada oficial
    
    faltas = models.IntegerField(default=0)
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
