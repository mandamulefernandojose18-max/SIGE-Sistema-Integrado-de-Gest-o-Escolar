import uuid
from django.db import models

class Certificado(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='certificados')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='certificados')
    tipo = models.CharField(max_length=50)  # CONCLUSAO, TRANSFERENCIA, DECLARACAO, MATRICULA
    codigo_autenticidade = models.CharField(max_length=100, unique=True)
    qrcode_data = models.TextField()
    emitido_em = models.DateTimeField(auto_now_add=True)
    emitido_por = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_certificados'
        verbose_name = 'Certificado'
        verbose_name_plural = 'Certificados'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['aluno']),
            models.Index(fields=['codigo_autenticidade']),
        ]

    def __str__(self):
        return f"{self.tipo} - {self.aluno.nome} ({self.codigo_autenticidade})"
