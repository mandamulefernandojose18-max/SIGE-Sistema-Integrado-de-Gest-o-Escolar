import uuid
from django.db import models

class Turma(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='turmas')
    nome = models.CharField(max_length=100)
    grau_ano = models.CharField(max_length=50)  # ex: 10ª Classe
    turno = models.CharField(max_length=20, default='MANHA')  # MANHA, TARDE, NOITE
    sala = models.CharField(max_length=50, blank=True, null=True)
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

    def __str__(self):
        return f"{self.nome} ({self.ano_letivo})"
