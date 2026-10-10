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
    director_classe = models.ForeignKey(
        'professores.Professor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turmas_como_director_classe'
    )
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
        from .utils import validar_unicidade_turma_na_classe
        validar_unicidade_turma_na_classe(
            escola=self.escola,
            grau_ano=self.grau_ano,
            nome=self.nome,
            ano_letivo=self.ano_letivo,
            exclude_id=self.id
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.ano_letivo})"
