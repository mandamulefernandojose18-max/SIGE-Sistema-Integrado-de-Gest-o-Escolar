import uuid
from django.db import models


class ConsultaAssistente(models.Model):
    """Auditoria das perguntas feitas ao assistente (por escola). Não guarda a resposta nem dados do aluno."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='consultas_assistente')
    usuario = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    pergunta = models.CharField(max_length=500)
    intencao = models.CharField(max_length=40, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_assistente_consultas'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['escola', 'created_at'])]
