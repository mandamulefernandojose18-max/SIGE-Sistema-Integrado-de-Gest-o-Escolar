import uuid
from django.db import models

class Pauta(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='pautas')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, related_name='pautas')
    ano_letivo = models.CharField(max_length=10, default='2026')
    periodo = models.CharField(max_length=20)  # 1_TRIMESTRE, 2_TRIMESTRE, 3_TRIMESTRE, ANUAL
    status = models.CharField(max_length=20, default='ABERTA')  # ABERTA, EM_CONSOLIDACAO, FECHADA
    data_fechamento = models.DateTimeField(null=True, blank=True)
    homologado_por = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_pautas'
        verbose_name = 'Pauta'
        verbose_name_plural = 'Pautas'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['turma']),
            models.Index(fields=['periodo']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Pauta {self.turma.nome} - {self.periodo} ({self.ano_letivo})"
