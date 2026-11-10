import uuid
from django.db import models

CARGO_CHOICES = [
    ('DIRECTOR_TURMA', 'Director de Turma'),
    ('DIRECTOR_CLASSE', 'Director de Classe'),
    ('DELEGADO_DISCIPLINA', 'Delegado da Disciplina'),
]

ESTADO_CHOICES = [
    ('PENDENTE', 'Pendente'),
    ('EM_CURSO', 'Em curso'),
    ('CONCLUIDA', 'Concluída'),
]

PRIORIDADE_CHOICES = [
    ('BAIXA', 'Baixa'),
    ('NORMAL', 'Normal'),
    ('ALTA', 'Alta'),
]


class AtividadeModelo(models.Model):
    """Actividade própria da escola, guardada pela Direcção Pedagógica para reutilizar nas atribuições."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='atividades_modelo')
    cargo = models.CharField(max_length=30, choices=CARGO_CHOICES)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, default='')
    criado_por = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_atividades_modelo'
        verbose_name = 'Actividade Modelo'
        verbose_name_plural = 'Actividades Modelo'
        indexes = [models.Index(fields=['escola', 'cargo'])]
        constraints = [
            models.UniqueConstraint(fields=['escola', 'cargo', 'titulo'], name='unique_atividade_modelo_escola_cargo_titulo'),
        ]

    def __str__(self):
        return f'{self.get_cargo_display()}: {self.titulo}'


class AtribuicaoCargo(models.Model):
    """Actividade atribuída pela Direcção Pedagógica a um Director de Turma, Director de Classe ou Delegado da Disciplina."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='atribuicoes_cargos')
    ano_letivo = models.CharField(max_length=10)
    cargo = models.CharField(max_length=30, choices=CARGO_CHOICES)
    professor = models.ForeignKey('professores.Professor', on_delete=models.CASCADE, related_name='atribuicoes_cargos')
    classe = models.CharField(max_length=50, blank=True, default='')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, null=True, blank=True, related_name='atribuicoes_cargos')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.CASCADE, null=True, blank=True, related_name='atribuicoes_cargos')
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, default='')
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default='NORMAL')
    prazo = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PENDENTE')
    nota_responsavel = models.TextField(blank=True, default='')
    atribuido_por = models.CharField(max_length=255, blank=True, default='')
    concluida_em = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_atribuicoes_cargos'
        verbose_name = 'Atribuição de Actividade'
        verbose_name_plural = 'Atribuições de Actividades'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['escola', 'ano_letivo', 'cargo']),
            models.Index(fields=['professor', 'estado']),
        ]

    def clean(self):
        from common.integrity import validar_integridade_tenant
        validar_integridade_tenant(self, professor=self.professor, turma=self.turma, disciplina=self.disciplina)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_cargo_display()} · {self.titulo}'
