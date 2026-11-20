import uuid

from django.db import models


class MensagemContacto(models.Model):
    """Mensagem enviada pelo formulário de contacto do site público.

    Excepção deliberada à regra de `escola_id`: é a caixa de entrada da PLATAFORMA (visitantes ainda sem escola),
    só acessível ao Super Admin (Django admin). Não guarda endereços IP nem dados de navegação.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=120)
    email = models.EmailField()
    assunto = models.CharField(max_length=160)
    mensagem = models.TextField(max_length=3000)
    lida = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_site_mensagens_contacto'
        ordering = ['-created_at']
        verbose_name = 'Mensagem de contacto'
        verbose_name_plural = 'Mensagens de contacto'

    def __str__(self):
        return f'{self.assunto} — {self.nome}'
