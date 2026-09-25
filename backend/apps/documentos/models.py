import uuid
from django.db import models

class LogImpressao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='logs_impressao')
    usuario = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_impressao')
    tipo_documento = models.CharField(max_length=50)  # BOLETIM, DECLARACAO, CERTIFICADO, PAUTA, CADERNETA, RECIBO, FICHA_ALUNO, ACTA
    descricao = models.CharField(max_length=255)
    conteudo_json = models.TextField(blank=True, null=True)
    data_emissao = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_logs_impressao'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['tipo_documento']),
            models.Index(fields=['data_emissao']),
        ]

class DocumentoSalvo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='documentos_salvos')
    usuario = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_salvos')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_salvos')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_salvos')
    tipo_documento = models.CharField(max_length=50)
    titulo = models.CharField(max_length=255)
    ano_letivo = models.CharField(max_length=10, default='2026')
    dados_json = models.TextField()
    hash_md5 = models.CharField(max_length=64, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_documentos_salvos'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['tipo_documento']),
            models.Index(fields=['aluno']),
            models.Index(fields=['turma']),
        ]
