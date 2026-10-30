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


class CalendarioEscolar(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='eventos_calendario')
    titulo = models.CharField(max_length=255)
    TIPO_CHOICES = [
        ('AVALIACAO_TESTE', 'Avaliação / Teste (ACS / ACP)'),
        ('EXAME', 'Época de Exames'),
        ('CONSELHO_TURMA', 'Conselho de Turma / Avaliação'),
        ('FERIADO_PAUSA', 'Feriado Oficial / Pausa Lectiva'),
        ('REUNIAO_ENCARREGADOS', 'Reunião de Encarregados de Educação'),
        ('EVENTO_ESCOLAR', 'Evento Escolar / Cultural'),
    ]
    tipo = models.CharField(max_length=25, choices=TIPO_CHOICES, default='AVALIACAO_TESTE')
    data_inicio = models.DateField(db_index=True)
    data_fim = models.DateField(null=True, blank=True)
    trimestre = models.CharField(
        max_length=20,
        choices=[('1_TRIMESTRE', '1º Trimestre'), ('2_TRIMESTRE', '2º Trimestre'), ('3_TRIMESTRE', '3º Trimestre'), ('GERAL', 'Geral')],
        default='GERAL'
    )
    descricao = models.TextField(blank=True, default='')
    nome_documento = models.CharField(max_length=255, blank=True, default='')
    documento_base64 = models.TextField(blank=True, null=True)
    documento_tipo = models.CharField(max_length=100, blank=True, default='')
    documento_tamanho = models.BigIntegerField(default=0)
    STATUS_CHOICES = [
        ('PROPOSTO_DAP', 'Proposto pelo Director Pedagógico'),
        ('APROVADO_DIRECTOR', 'Aprovado pelo Director da Escola'),
    ]
    status_aprovacao = models.CharField(max_length=25, choices=STATUS_CHOICES, default='APROVADO_DIRECTOR')
    criado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, related_name='calendarios_criados')
    aprovado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='calendarios_aprovados')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_calendario_escolar'
        verbose_name = 'Evento do Calendário Escolar'
        verbose_name_plural = 'Calendário Escolar'
        indexes = [
            models.Index(fields=['escola', 'data_inicio']),
            models.Index(fields=['tipo']),
            models.Index(fields=['trimestre']),
        ]

    def __str__(self):
        return f'{self.titulo} ({self.data_inicio}) - {self.tipo}'



class DocumentoCalendarioOficial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='documentos_calendario')
    titulo = models.CharField(max_length=255, default='Calendário Escolar Oficial')
    ano_lectivo = models.CharField(max_length=20, blank=True, default='2026')
    descricao = models.TextField(blank=True, default='')
    nome_arquivo = models.CharField(max_length=255, default='calendario_escolar.pdf')
    extensao = models.CharField(max_length=20, default='pdf')
    tamanho_bytes = models.BigIntegerField(default=0)
    conteudo_base64 = models.TextField(blank=True, null=True)
    tipo_mime = models.CharField(max_length=100, default='application/pdf')
    publicado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_calendario_publicados')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_documentos_calendario_oficial'
        verbose_name = 'Documento Oficial do Calendário'
        verbose_name_plural = 'Documentos Oficiais do Calendário'
        indexes = [
            models.Index(fields=['escola', 'ano_lectivo']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.titulo} - {self.ano_lectivo} ({self.escola.nome})'

class ComunicadoEscolar(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='comunicados')
    titulo = models.CharField(max_length=255)
    conteudo = models.TextField()
    ALVO_CHOICES = [
        ('TODOS', 'Toda a Comunidade Escolar'),
        ('PROFESSORES', 'Corpo Docente (Professores)'),
        ('ALUNOS', 'Alunos'),
        ('ENCARREGADOS', 'Encarregados de Educação'),
        ('SECRETARIA', 'Secretaria e Funcionários'),
    ]
    publico_alvo = models.CharField(max_length=20, choices=ALVO_CHOICES, default='TODOS')
    PRIORIDADE_CHOICES = [
        ('NORMAL', 'Normal'),
        ('IMPORTANTE', 'Importante'),
        ('URGENTE', 'Urgente'),
    ]
    prioridade = models.CharField(max_length=15, choices=PRIORIDADE_CHOICES, default='NORMAL')
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('PUBLICADO', 'Publicado e Activo'),
        ('ARQUIVADO', 'Arquivado'),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PUBLICADO')
    aprovado_pelo_director = models.BooleanField(default=True)
    autor = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, related_name='comunicados_emitidos')
    aprovado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='comunicados_aprovados')
    data_publicacao = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_comunicados_escolares'
        verbose_name = 'Comunicado Escolar'
        verbose_name_plural = 'Comunicados Escolares'
        indexes = [
            models.Index(fields=['escola', 'publico_alvo']),
            models.Index(fields=['status']),
            models.Index(fields=['data_publicacao']),
        ]

    def __str__(self):
        return f'{self.titulo} - Para: {self.publico_alvo}'
