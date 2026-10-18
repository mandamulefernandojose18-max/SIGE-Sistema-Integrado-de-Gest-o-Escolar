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


class ConfiguracaoGateway(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.OneToOneField(
        'tenants.Escola',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='config_gateway'
    )
    # Opção 1: Gateway Android Local (Custo Zero)
    modo_sms = models.CharField(
        max_length=30,
        default='SANDBOX',
        choices=[
            ('SANDBOX', 'Simulação / Ambiente de Testes'),
            ('ANDROID_GATEWAY', 'Gateway Android Local (Cartão SIM da Escola)'),
            ('WHATSAPP_ONLY', 'Apenas Notificações WhatsApp'),
            ('API_EXTERNA', 'Provedor SMS Externo (API Key)')
        ]
    )
    android_gateway_url = models.CharField(max_length=255, blank=True, default='')
    android_gateway_token = models.CharField(max_length=150, blank=True, default='')

    # Opção 2: Notificações WhatsApp
    whatsapp_ativo = models.BooleanField(default=True)
    whatsapp_provider = models.CharField(
        max_length=30,
        default='WA_ME',
        choices=[
            ('WA_ME', 'Link Direto WhatsApp Web (1-Clique Gratuito)'),
            ('EVOLUTION_API', 'Evolution API / Baileys (Webhook Automático)'),
            ('CUSTOM_WEBHOOK', 'Webhook Customizado')
        ]
    )
    whatsapp_api_url = models.CharField(max_length=255, blank=True, default='')
    whatsapp_api_token = models.CharField(max_length=200, blank=True, default='')

    # Opção 3: Pagamentos M-Pesa OpenAPI & Reconciliação Automática por SMS
    mpesa_shortcode = models.CharField(max_length=30, blank=True, default='')
    mpesa_api_key = models.CharField(max_length=255, blank=True, default='')
    mpesa_public_key = models.TextField(blank=True, default='')
    
    # Token de segurança para webhook do app Android encaminhar SMS M-Pesa recebidos
    webhook_secret_sms = models.CharField(max_length=100, blank=True, default='sige-secret-webhook-sms-2026')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_gateway_configuracoes'
        verbose_name = 'Configuração do Gateway'
        verbose_name_plural = 'Configurações do Gateway'

    def __str__(self):
        nome = self.escola.nome if self.escola else "Global"
        return f"Config Gateway ({nome}) - {self.modo_sms}"


class MensagemWhatsApp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(
        'tenants.Escola',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mensagens_whatsapp'
    )
    aluno = models.ForeignKey(
        'alunos.Aluno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mensagens_whatsapp'
    )
    destinatario = models.CharField(max_length=30, db_index=True)
    nome_destinatario = models.CharField(max_length=150, blank=True, default='')
    tipo = models.CharField(max_length=40, default='AVISO')
    mensagem = models.TextField()
    wa_link = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=30,
        default='ENVIADO',
        choices=[
            ('ENVIADO', 'Enviado com Sucesso'),
            ('PENDENTE', 'Pendente / Link Gerado'),
            ('FALHADO', 'Falha no Envio')
        ],
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'sige_gateway_mensagens_whatsapp'
        verbose_name = 'Mensagem WhatsApp'
        verbose_name_plural = 'Mensagens WhatsApp'
        ordering = ['-created_at']

    def __str__(self):
        return f"WhatsApp {self.destinatario} - {self.status}"


class ReconciliacaoSmsMovel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(
        'tenants.Escola',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reconciliacoes_sms'
    )
    remetente = models.CharField(max_length=50, default='MPESA')
    texto_sms = models.TextField()
    codigo_transacao = models.CharField(max_length=100, db_index=True, blank=True, default='')
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    telefone_origem = models.CharField(max_length=30, blank=True, default='')
    nome_origem = models.CharField(max_length=150, blank=True, default='')
    aluno = models.ForeignKey(
        'alunos.Aluno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliacoes_sms'
    )
    pagamento = models.ForeignKey(
        'pagamentos.Pagamento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliacoes_sms'
    )
    recibo_emitido = models.CharField(max_length=50, blank=True, default='')
    status = models.CharField(
        max_length=40,
        default='RECONCILIADO',
        choices=[
            ('RECONCILIADO', 'Liquidado Automaticamente com Sucesso'),
            ('PENDENTE_ASSOCIACAO', 'Recebido mas Sem Aluno Identificado'),
            ('DUPLICADO', 'Transação Já Processada Anteriormente'),
            ('INVALIDO', 'Texto Não Reconhecido como Comprovativo M-Pesa/e-Mola')
        ],
        db_index=True
    )
    detalhes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'sige_gateway_reconciliacoes_sms'
        verbose_name = 'Reconciliação de SMS Móvel'
        verbose_name_plural = 'Reconciliações de SMS Móvel'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reconciliação [{self.remetente}] {self.codigo_transacao} - {self.valor} MZN ({self.status})"

