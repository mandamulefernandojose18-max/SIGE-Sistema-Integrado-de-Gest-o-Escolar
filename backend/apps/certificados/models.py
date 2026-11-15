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

    def clean(self):
        from common.integrity import validar_integridade_tenant
        validar_integridade_tenant(self, aluno=self.aluno)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo} - {self.aluno.nome} ({self.codigo_autenticidade})"


class ChaveAssinaturaEscola(models.Model):
    """Par de chaves Ed25519 de cada escola (nível C do carimbo). A chave privada nunca sai do servidor
    e é guardada cifrada (ver `carimbo.py`); a chave pública é a que valida a assinatura publicamente."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.OneToOneField('tenants.Escola', on_delete=models.CASCADE, related_name='chave_assinatura')
    chave_publica_pem = models.TextField()
    chave_privada_cifrada = models.TextField()
    impressao_digital = models.CharField(max_length=64)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_chaves_assinatura_escolas'

    def delete(self, *args, **kwargs):
        from django.db import IntegrityError
        raise IntegrityError('Eliminação não permitida: apagar a chave invalidaria os documentos já assinados.')


class DocumentoCarimbado(models.Model):
    """Registo de cada documento emitido com carimbo de nível B ou C. É este registo que a página pública
    de verificação consulta; o mesmo documento (escola + tipo + referência) mantém sempre o mesmo código."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='documentos_carimbados')
    tipo = models.CharField(max_length=50)
    referencia = models.CharField(max_length=200)
    descricao = models.CharField(max_length=255, blank=True, default='')
    codigo = models.CharField(max_length=40, unique=True)
    nivel = models.CharField(max_length=20)
    emitido_por = models.CharField(max_length=255, blank=True, default='')
    emitido_em = models.DateTimeField(auto_now_add=True)
    assinatura = models.TextField(blank=True, default='')
    impressao_digital_chave = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        db_table = 'sige_documentos_carimbados'
        constraints = [
            models.UniqueConstraint(fields=['escola', 'tipo', 'referencia'], name='unique_doc_carimbado_escola_tipo_ref'),
        ]
        indexes = [models.Index(fields=['codigo'])]

    def delete(self, *args, **kwargs):
        from django.db import IntegrityError
        raise IntegrityError('Eliminação não permitida: o registo de autenticidade é permanente.')

    def __str__(self):
        return f"{self.tipo} {self.codigo}"
