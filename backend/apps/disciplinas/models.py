import uuid
from django.db import models
from django.core.validators import MinValueValidator

class Disciplina(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='disciplinas')
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=50)
    classe = models.CharField(max_length=50, default='10ª Classe')
    area = models.CharField(max_length=50, default='Geral')
    carga_horaria = models.IntegerField(default=60, validators=[MinValueValidator(1)])
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
        constraints = [
            models.UniqueConstraint(
                fields=['escola', 'codigo', 'ano_letivo'],
                name='unique_disciplina_escola_codigo_ano_letivo'
            ),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.codigo})"
