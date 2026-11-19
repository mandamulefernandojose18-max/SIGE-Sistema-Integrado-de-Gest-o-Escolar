import uuid
from django.db import models


class Atendimento(models.Model):
    """Pedido ou reclamação de um encarregado/aluno, com estado e responsável (isolado por escola)."""
    CANAIS = [('PRESENCIAL', 'Presencial'), ('TELEFONE', 'Telefone'), ('EMAIL', 'E-mail'), ('APP', 'Aplicação')]
    ESTADOS = [('ABERTO', 'Aberto'), ('EM_CURSO', 'Em curso'), ('RESOLVIDO', 'Resolvido')]
    PRIORIDADES = [('BAIXA', 'Baixa'), ('NORMAL', 'Normal'), ('ALTA', 'Alta')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='crm_atendimentos')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.SET_NULL, null=True, blank=True, related_name='crm_atendimentos')
    assunto = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, default='')
    canal = models.CharField(max_length=20, choices=CANAIS, default='PRESENCIAL')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ABERTO', db_index=True)
    prioridade = models.CharField(max_length=10, choices=PRIORIDADES, default='NORMAL')
    responsavel = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    criado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    resolucao = models.TextField(blank=True, default='')
    resolvido_em = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_crm_atendimentos'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['escola', 'estado'])]

    def clean(self):
        from common.integrity import validar_integridade_tenant
        rel = {}
        if self.aluno_id:
            rel['aluno'] = self.aluno
        if self.responsavel_id:
            rel['responsavel'] = self.responsavel
        if rel:
            validar_integridade_tenant(self, **rel)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.assunto} [{self.estado}]'


class Comunicacao(models.Model):
    """Registo do histórico de contactos com o encarregado (não envia mensagens externas)."""
    TIPOS = [('REUNIAO', 'Convocatória de reunião'), ('FALTAS', 'Faltas'), ('PROPINA', 'Propina'),
             ('PAUTA', 'Pauta / Notas'), ('OUTRO', 'Outro')]
    CANAIS = [('INAPP', 'Aplicação'), ('EMAIL', 'E-mail'), ('TELEFONE', 'Telefone'), ('PRESENCIAL', 'Presencial')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='crm_comunicacoes')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='crm_comunicacoes')
    tipo = models.CharField(max_length=20, choices=TIPOS, default='OUTRO')
    canal = models.CharField(max_length=20, choices=CANAIS, default='INAPP')
    mensagem = models.TextField()
    destinatario = models.CharField(max_length=255, blank=True, default='')
    registado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_crm_comunicacoes'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['escola', 'aluno'])]

    def clean(self):
        from common.integrity import validar_integridade_tenant
        validar_integridade_tenant(self, aluno=self.aluno)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class VinculoEncarregado(models.Model):
    """Associa uma conta de Encarregado de Educação a um educando (um encarregado pode ter vários; um aluno pode ter vários encarregados).

    A associação é feita pela escola (gestão). O `aluno_id` antigo da conta continua a valer como um educando adicional.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='crm_vinculos_encarregado')
    usuario = models.ForeignKey('accounts.Usuario', on_delete=models.CASCADE, related_name='vinculos_educandos')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='vinculos_encarregado')
    criado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_crm_vinculos_encarregado'
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['escola', 'usuario', 'aluno'], name='unique_vinculo_encarregado_aluno')]
        indexes = [models.Index(fields=['escola', 'usuario'])]

    def clean(self):
        from django.core.exceptions import ValidationError
        from common.integrity import validar_integridade_tenant
        validar_integridade_tenant(self, aluno=self.aluno, usuario=self.usuario)
        if self.usuario.role != 'ENCARREGADO':
            raise ValidationError('A conta tem de ser de um Encarregado de Educação.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
