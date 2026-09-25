import uuid
from django.db import models

class Disciplina(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='disciplinas')
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=50)
    classe = models.CharField(max_length=50, default='10ª Classe')
    area = models.CharField(max_length=50, default='Geral')
    carga_horaria = models.IntegerField(default=60)
    ano_letivo = models.CharField(max_length=10, default='2026')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_disciplinas'
        verbose_name = 'Disciplina'
        verbose_name_plural = 'Disciplinas'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['codigo']),
        ]

    def __str__(self):
        return f"{self.nome} ({self.codigo})"
