import uuid
from django.db import models

class MensagemSMS(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(
        'tenants.Escola',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mensagens_sms',
        db_index=True
    )
    destinatario = models.CharField(max_length=30, db_index=True)
    nome_destinatario = models.CharField(max_length=150, blank=True, default='')
    operadora = models.CharField(
        max_length=30,
        default='VODACOM',
        choices=[
            ('VODACOM', 'Vodacom Moçambique (84/85)'),
            ('MOVITEL', 'Movitel Moçambique (86/87)'),
            ('TMCEL', 'Tmcel Moçambique (82/83)'),
            ('OUTRA', 'Outra Operadora')
        ]
    )
    mensagem = models.TextField()
    tipo = models.CharField(
        max_length=40,
        default='TRANSACIONAL',
        choices=[
            ('TRANSACIONAL', 'SMS Transacional / Cobrança'),
            ('PROPINAS', 'Aviso de Propinas / Vencimento'),
            ('RECIBO', 'Confirmação de Pagamento'),
            ('AVISO', 'Aviso Geral'),
            ('FALTA', 'Falta ou Ocorrência Disciplinar'),
            ('PAUTA', 'Pauta / Desempenho Escolar')
        ]
    )
    caracteres = models.IntegerField(default=0)
    segmentos_sms = models.IntegerField(default=1)
    status = models.CharField(
        max_length=30,
        default='ENTREGUE',
        choices=[
            ('ENTREGUE', 'Entregue com Sucesso'),
            ('ENVIADO', 'Enviado à Operadora'),
            ('PENDENTE', 'Na Fila de Envio'),
            ('FALHADO', 'Falha no Envio')
        ],
        db_index=True
    )
    mensagem_id_operadora = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'sige_gateway_mensagens_sms'
        verbose_name = 'Mensagem SMS'
        verbose_name_plural = 'Mensagens SMS'
        ordering = ['-created_at']

    def __str__(self):
        return f"SMS [{self.operadora}] {self.destinatario} - {self.status}"


class TransacaoGatewayMovel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(
        'tenants.Escola',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='transacoes_gateway',
        db_index=True
    )
    pagamento = models.ForeignKey(
        'pagamentos.Pagamento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gateway_transacoes'
    )
    aluno = models.ForeignKey(
        'alunos.Aluno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gateway_transacoes'
    )
    metodo = models.CharField(
        max_length=20,
        default='MPESA',
        choices=[
            ('MPESA', 'M-Pesa Moçambique (Vodacom)'),
            ('EMOLA', 'e-Mola Moçambique (Movitel)')
        ],
        db_index=True
    )
    telefone = models.CharField(max_length=30)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    referencia_transacao = models.CharField(max_length=100, unique=True, db_index=True)
    recibo_emitido = models.CharField(max_length=50, blank=True, default='')
    status = models.CharField(
        max_length=30,
        default='CONCLUIDO',
        choices=[
            ('CONCLUIDO', 'Pagamento Concluído com Sucesso'),
            ('PENDENTE_PIN', 'A Aguardar Entrada de PIN no Telemóvel'),
            ('FALHADO', 'Falha / Saldo Insuficiente'),
            ('CANCELADO', 'Cancelado pelo Utilizador')
        ],
        db_index=True
    )
    mensagem_retorno = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'sige_gateway_transacoes_moveis'
        verbose_name = 'Transação de Gateway Móvel'
        verbose_name_plural = 'Transações de Gateway Móvel'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.metodo} - {self.referencia_transacao} - {self.valor} MZN ({self.status})"
