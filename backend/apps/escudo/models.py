"""Escudo Anti-IA: provas cifradas (AES-256-GCM), com embargo opcional, leituras dos códigos e cópias seladas."""
from django.db import models


class ProvaEscudo(models.Model):
    codigo = models.CharField(max_length=8, unique=True, db_index=True)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, null=True, blank=True, related_name='provas_escudo')
    criado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    titulo = models.CharField(max_length=120)
    disciplina = models.CharField(max_length=60, blank=True, default='')
    classe = models.CharField(max_length=30, blank=True, default='')
    libertacao = models.DateTimeField(db_index=True, help_text='Fim do embargo (UTC); 2099 = sem data limite')
    publicar_apos = models.BooleanField(default=True)
    paginas = models.PositiveIntegerField(default=1)
    copias = models.PositiveIntegerField(default=1)
    config = models.JSONField(default=dict, blank=True)
    pdf_cifrado = models.BinaryField(editable=False)
    gabarito_cifrado = models.BinaryField(null=True, blank=True, editable=False)
    criada_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'sige_escudo_provas'
        ordering = ['libertacao']
        verbose_name = 'Prova do Escudo Anti-IA'
        verbose_name_plural = 'Provas do Escudo Anti-IA'

    def __str__(self):
        return f'{self.codigo} {self.titulo}'


class LeituraEscudo(models.Model):
    prova = models.ForeignKey(ProvaEscudo, on_delete=models.CASCADE, related_name='leituras')
    serial = models.PositiveIntegerField(null=True, blank=True)
    estado = models.CharField(max_length=10)  # embargo | libertada | invalida
    aparelho = models.CharField(max_length=120, blank=True, default='')
    rede = models.CharField(max_length=16, blank=True, default='', help_text='Impressão (hash) da rede, nunca o IP')
    quando = models.DateTimeField(auto_now_add=True, db_index=True)
    latitude = models.FloatField(null=True, blank=True)  # só se quem leu autorizou no navegador
    longitude = models.FloatField(null=True, blank=True)
    precisao_m = models.PositiveIntegerField(null=True, blank=True)
    notificada = models.BooleanField(default=False, db_index=True)
    vista = models.BooleanField(default=True, db_index=True)  # False = leitura nova que o professor ainda não viu no SIGE

    class Meta:
        db_table = 'sige_escudo_leituras'
        ordering = ['-id']


class CapturaEscudo(models.Model):
    """Foto de quem leu o código (selfie) e/ou da prova, com o local e o aparelho. Só existe se a pessoa autorizou
    a câmara e a localização no navegador e carregou em «Registar». As imagens ficam cifradas (AES-256-GCM)."""
    leitura = models.ForeignKey(LeituraEscudo, on_delete=models.CASCADE, related_name='capturas')
    prova = models.ForeignKey(ProvaEscudo, on_delete=models.CASCADE, related_name='capturas')
    foto_leitor_cifrada = models.BinaryField(null=True, blank=True, editable=False)
    foto_prova_cifrada = models.BinaryField(null=True, blank=True, editable=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    precisao_m = models.PositiveIntegerField(null=True, blank=True)
    aparelho = models.JSONField(default=dict, blank=True, help_text='Referências do telefone: marca, modelo, sistema, ecrã, memória, idioma e fuso (nunca o IP)')
    imei_cifrado = models.BinaryField(null=True, blank=True, editable=False, help_text='IMEI do telefone (15 dígitos, validado), cifrado')
    imagem_aparelho = models.BinaryField(null=True, blank=True, editable=False, help_text='Imagem do modelo do telefone, pesquisada na internet')
    imagem_aparelho_fonte = models.CharField(max_length=300, blank=True, default='')
    criada_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'sige_escudo_capturas'
        ordering = ['-id']


class EventoEscudo(models.Model):
    prova = models.ForeignKey(ProvaEscudo, on_delete=models.CASCADE, related_name='eventos')
    texto = models.CharField(max_length=300)
    quando = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_escudo_eventos'
        ordering = ['-id']


class RegraExclusaoEscudo(models.Model):
    """Regra da escola para a folha de resposta personalizada: quem fica de fora, verificada automaticamente e sempre."""
    escola = models.OneToOneField('tenants.Escola', on_delete=models.CASCADE, related_name='regra_exclusao_escudo')
    verificar_sempre = models.BooleanField(default=False)
    motivos = models.JSONField(default=list, blank=True)
    faltas_minimo = models.PositiveIntegerField(default=0, help_text='Total de faltas acumuladas a partir do qual o aluno é excluído (0 = não definido)')
    cor_excluidos = models.CharField(max_length=7, default='#FDE2E2', help_text='Cor das linhas dos alunos excluídos nas listas (PDF/Excel)')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_escudo_regra_exclusao'
        verbose_name = 'Regra de exclusão do Escudo Anti-IA'
