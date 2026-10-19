import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

from decimal import Decimal

class Plano(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True, null=True)
    preco = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    duracao_dias = models.IntegerField(default=30, validators=[MinValueValidator(1)])
    max_alunos = models.IntegerField(default=500, validators=[MinValueValidator(1)])
    max_professores = models.IntegerField(default=50, validators=[MinValueValidator(1)])
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_planos'
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'
        constraints = [
            models.CheckConstraint(check=models.Q(preco__gte=0), name='check_plano_preco_positivo'),
            models.CheckConstraint(check=models.Q(max_alunos__gte=1), name='check_plano_max_alunos_positivo'),
            models.CheckConstraint(check=models.Q(max_professores__gte=1), name='check_plano_max_professores_positivo'),
        ]

    def clean(self):
        from common.integrity import IntegrityRuleViolation
        if self.preco is not None and self.preco < 0:
            raise IntegrityRuleViolation("O preço do plano não pode ser negativo.")
        if self.max_alunos is not None and self.max_alunos < 1:
            raise IntegrityRuleViolation("A quota máxima de alunos deve ser de pelo menos 1.")
        if self.max_professores is not None and self.max_professores < 1:
            raise IntegrityRuleViolation("A quota máxima de professores deve ser de pelo menos 1.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.preco} MZN)"

class Escola(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    nif_cnpj = models.CharField(max_length=50, unique=True)
    endereco = models.TextField(blank=True, null=True)
    telefone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(unique=True)
    logo_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, default='ATIVA')  # ATIVA, PENDENTE, EXPIRADA, SUSPENSA
    ano_letivo_ativo = models.CharField(max_length=10, default='2026')
    trimestre_ativo = models.CharField(max_length=20, default='1_TRIMESTRE')
    plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True, blank=True, related_name='escolas')
    data_adesao = models.DateTimeField(default=timezone.now)

    # Dados Oficiais para Documentação MEC
    provincia = models.CharField(max_length=100, default='Maputo')
    distrito = models.CharField(max_length=100, default='Cidade de Maputo')
    tipo_escola = models.CharField(max_length=10, default='S')  # P=Primária, B=Básica, S=Secundária
    director_nome = models.CharField(max_length=255, default='', blank=True)
    director_carreira = models.CharField(max_length=100, default='', blank=True)
    dap_nome = models.CharField(max_length=255, default='', blank=True)
    chefe_secretaria_nome = models.CharField(max_length=255, default='', blank=True)
    usar_emblema_nacional = models.BooleanField(default=True)
    codigo_escola = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    logo_base64 = models.TextField(blank=True, null=True)
    galeria_logos = models.JSONField(default=list, blank=True)
    config_classes_exames = models.JSONField(default=dict, blank=True)
    config_parametros_exames = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuração de pesos e nota mínima dos exames (peso_frequencia, peso_exame, nota_minima_exame)"
    )
    regime_curricular = models.CharField(
        max_length=20,
        default='CLASSES',
        choices=[
            ('CLASSES', 'Regime por Classes (1ª à 12ª Classe)'),
            ('NIVEIS', 'Regime por Níveis (Nível 1, Nível 2...)')
        ]
    )

    def get_config_parametros_exames(self):
        cfg = self.config_parametros_exames or {}
        try:
            pf = float(cfg.get('peso_frequencia', 50))
        except (ValueError, TypeError):
            pf = 50.0
        try:
            pe = float(cfg.get('peso_exame', 50))
        except (ValueError, TypeError):
            pe = 50.0
        try:
            nm = float(cfg.get('nota_minima_exame', 10.0))
        except (ValueError, TypeError):
            nm = 10.0
        return {
            'peso_frequencia': pf,
            'peso_exame': pe,
            'nota_minima_exame': nm,
        }


    # Identidade Visual, Tema e Imagem de Fundo da Instituição
    tema_codigo = models.CharField(max_length=50, default='padrao_azul')
    tema_cor_primaria = models.CharField(max_length=20, default='#1e3a8a', blank=True)
    tema_cor_hover = models.CharField(max_length=20, default='#172554', blank=True)
    tema_cor_sidebar = models.CharField(max_length=20, default='#0f172a', blank=True)
    tema_cor_sidebar_ativa = models.CharField(max_length=20, default='#38bdf8', blank=True)
    imagem_fundo_url = models.TextField(blank=True, null=True)
    imagem_fundo_base64 = models.TextField(blank=True, null=True)
    imagem_fundo_modo = models.CharField(
        max_length=30,
        default='marca_dagua',
        choices=[
            ('marca_dagua', 'Marca de Água Central Sutil'),
            ('cobertura_total', 'Papel de Parede Total (Wallpaper)'),
            ('padrao_textura', 'Padrão Textura Suave'),
            ('nenhum', 'Sem Imagem de Fundo (Apenas Cores)')
        ]
    )
    imagem_fundo_opacidade = models.IntegerField(default=15)
    galeria_fundos = models.JSONField(default=list, blank=True)

    bloqueada_manualmente = models.BooleanField(default=False)
    permitir_visualizacao_notas = models.BooleanField(default=True)
    modo_publicacao_notas = models.CharField(
        max_length=20,
        default='MANUAL',
        choices=[
            ('MANUAL', '1ª Opção: Modo Imediato / Manual'),
            ('DATAS', '2ª Opção: Modo Programado por Datas')
        ]
    )
    publicacao_notas_trimestre = models.CharField(
        max_length=20,
        default='TODOS',
        choices=[
            ('1_TRIMESTRE', '1. I Trimestre (Apenas 1º Trimestre)'),
            ('2_TRIMESTRE', '2. I e II Trimestre (1º e 2º Trimestre)'),
            ('3_TRIMESTRE', '3. III Trimestre (3º Trimestre)'),
            ('TODOS', '4. Todos os Trimestres (I, II e III)'),
            ('NENHUM', '5. Ocultar / Suspender Visualização')
        ]
    )
    # Intervalos de datas para publicação programada (2ª Opção):
    data_inicio_pub_t1 = models.DateField(null=True, blank=True)
    data_fim_pub_t1 = models.DateField(null=True, blank=True)
    data_inicio_pub_t2 = models.DateField(null=True, blank=True)
    data_fim_pub_t2 = models.DateField(null=True, blank=True)
    data_inicio_pub_todos = models.DateField(null=True, blank=True)
    data_fim_pub_todos = models.DateField(null=True, blank=True)


    # Inscrições Online
    inscricoes_abertas = models.BooleanField(default=False)
    inscricoes_inicio = models.DateTimeField(null=True, blank=True)
    inscricoes_fim = models.DateTimeField(null=True, blank=True)

    # Calendarização Oficial de Prazos de Notas (Manual, Automática ou Sempre)
    modo_calendarizacao = models.CharField(max_length=20, default='MANUAL')  # MANUAL, AUTOMATICO, SEMPRE
    tipo_duracao_automatica = models.CharField(max_length=20, default='SEMANAS')  # DIAS, SEMANAS, MESES
    valor_duracao_automatica = models.IntegerField(default=4)
    data_base_automatica = models.DateField(null=True, blank=True)
    data_inicio_t1 = models.DateField(null=True, blank=True)
    data_fim_t1 = models.DateField(null=True, blank=True)
    data_inicio_t2 = models.DateField(null=True, blank=True)
    data_fim_t2 = models.DateField(null=True, blank=True)
    data_inicio_t3 = models.DateField(null=True, blank=True)
    data_fim_t3 = models.DateField(null=True, blank=True)
    permitir_sempre_t1 = models.BooleanField(default=False)
    permitir_sempre_t2 = models.BooleanField(default=False)
    permitir_sempre_t3 = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_escolas'
        verbose_name = 'Escola (Tenant)'
        verbose_name_plural = 'Escolas (Tenants)'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['email']),
            models.Index(fields=['codigo_escola']),
        ]

    @property
    def codigo_gabinete_director(self):
        return f"GD{self.codigo_escola}" if self.codigo_escola else ""

    @property
    def codigo_direccao_pedagogica(self):
        return f"DP{self.codigo_escola}" if self.codigo_escola else ""

    @property
    def codigo_secretaria(self):
        return f"SECR{self.codigo_escola}" if self.codigo_escola else ""

    def save(self, *args, **kwargs):
        import re
        from common.utils.geografia_mocambique import (
            obter_letra_tipo_escola,
            gerar_codigo_unico_escola,
        )
        self.tipo_escola = obter_letra_tipo_escola(self.tipo_escola, self.nome)
        cod_atual = (self.codigo_escola or '').strip().upper()
        if not cod_atual or not re.match(r'^\d{4}[PBS]\d{4,5}$', cod_atual):
            self.codigo_escola = gerar_codigo_unico_escola(
                provincia=self.provincia,
                distrito=self.distrito,
                tipo_escola=self.tipo_escola,
                nome_escola=self.nome,
                exclude_escola_id=self.id,
            )
        else:
            self.codigo_escola = cod_atual
        super().save(*args, **kwargs)
        try:
            from .services import garantir_anos_lectivos_escola
            garantir_anos_lectivos_escola(self)
        except Exception:
            pass

    def resolver_publicacao_notas(self, hoje=None):
        """
        Resolve a publicação activa de notas aos alunos.
        Retorna tupla: (publicacao_trimestre, permitir_visualizacao, modo_ativo, info_detalhe)
        """
        from django.utils import timezone
        if hoje is None:
            hoje = timezone.localdate()

        modo = (self.modo_publicacao_notas or 'MANUAL').upper()
        if modo == 'DATAS':
            # 1. Todos os Trimestres (I, II e III)
            if self.data_inicio_pub_todos:
                # Se não houver data_fim_pub_todos definida, a visualização vigora por tempo infinito a partir da data de início
                if self.data_inicio_pub_todos <= hoje and (not self.data_fim_pub_todos or hoje <= self.data_fim_pub_todos):
                    return 'TODOS', True, 'DATAS', {
                        'periodo': 'TODOS',
                        'inicio': str(self.data_inicio_pub_todos),
                        'fim': str(self.data_fim_pub_todos) if self.data_fim_pub_todos else 'Infinito',
                        'rotulo': 'Todos os Trimestres (I, II e III)'
                    }
            # 2. I e II Trimestre (1º e 2º Trimestre)
            if self.data_inicio_pub_t2 and self.data_fim_pub_t2:
                if self.data_inicio_pub_t2 <= hoje <= self.data_fim_pub_t2:
                    return '2_TRIMESTRE', True, 'DATAS', {
                        'periodo': '2_TRIMESTRE',
                        'inicio': str(self.data_inicio_pub_t2),
                        'fim': str(self.data_fim_pub_t2),
                        'rotulo': 'I e II Trimestre (1º e 2º Trimestre)'
                    }
            # 3. I Trimestre (Apenas 1º Trimestre)
            if self.data_inicio_pub_t1 and self.data_fim_pub_t1:
                if self.data_inicio_pub_t1 <= hoje <= self.data_fim_pub_t1:
                    return '1_TRIMESTRE', True, 'DATAS', {
                        'periodo': '1_TRIMESTRE',
                        'inicio': str(self.data_inicio_pub_t1),
                        'fim': str(self.data_fim_pub_t1),
                        'rotulo': 'I Trimestre (Apenas 1º Trimestre)'
                    }
            # Fora de qualquer intervalo programado
            return 'NENHUM', False, 'DATAS', {
                'periodo': 'NENHUM',
                'inicio': None,
                'fim': None,
                'rotulo': 'Fora do Período Programado'
            }

        # Modo MANUAL
        pub = self.publicacao_notas_trimestre or 'TODOS'
        ativa = bool(self.permitir_visualizacao_notas) and (pub != 'NENHUM')
        return pub if ativa else 'NENHUM', ativa, 'MANUAL', None

    def __str__(self):
        return f"{self.nome} [{self.codigo_escola or self.status}]"


class AssinaturaEscola(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='assinaturas')
    plano = models.ForeignKey(Plano, on_delete=models.CASCADE, related_name='assinaturas')
    data_inicio = models.DateTimeField(default=timezone.now)
    data_fim = models.DateTimeField()
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, default='ATIVA')  # ATIVA, PENDENTE, EXPIRADA, SUSPENSA
    metodo_pagamento = models.CharField(max_length=50, default='TRANSFERENCIA')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_assinaturas_escolas'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['status']),
            models.Index(fields=['data_fim']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(data_fim__gte=models.F('data_inicio')),
                name='check_assinatura_datas_coerentes'
            ),
            models.CheckConstraint(
                check=models.Q(valor__gte=0),
                name='check_assinatura_valor_positivo'
            ),
        ]

    def clean(self):
        from common.integrity import IntegrityRuleViolation
        if self.data_fim and self.data_inicio and self.data_fim < self.data_inicio:
            raise IntegrityRuleViolation("A data de término da assinatura não pode ser anterior à data de início.")
        if self.valor is not None and self.valor < 0:
            raise IntegrityRuleViolation("O valor da assinatura não pode ser negativo.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.escola.nome} - {self.plano.nome} ({self.status})"

class AnoLectivo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='anos_lectivos')
    ano = models.CharField(max_length=10, db_index=True)
    descricao = models.CharField(max_length=100, blank=True)
    ativo = models.BooleanField(default=False)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_anos_lectivos'
        verbose_name = 'Ano Lectivo'
        verbose_name_plural = 'Anos Lectivos'
        ordering = ['-ano']
        constraints = [
            models.UniqueConstraint(fields=['escola', 'ano'], name='unique_escola_ano_lectivo')
        ]

    def save(self, *args, **kwargs):
        if not self.descricao:
            self.descricao = f"Ano Lectivo de {self.ano}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.descricao} ({'Activo' if self.ativo else 'Findo'})"


# =====================================================================
# 💳 MODELOS SAAS: PAGAMENTOS, ASSINATURAS E FATURAÇÃO AUTOMÁTICA
# =====================================================================

class SaasPlano(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True, null=True)
    preco_mensal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0'))])
    limite_alunos = models.IntegerField(default=500, validators=[MinValueValidator(1)])
    limite_professores = models.IntegerField(default=50, validators=[MinValueValidator(1)])
    limites = models.JSONField(default=dict, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_saas_planos'
        verbose_name = 'Plano SaaS'
        verbose_name_plural = 'Planos SaaS'

    def delete(self, *args, **kwargs):
        from django.db import IntegrityError
        raise IntegrityError("Eliminação não permitida: planos e dados são invioláveis.")

    def __str__(self):
        return f"{self.nome} ({self.preco_mensal} MZN/mês)"


class SaasAssinatura(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instituicao = models.ForeignKey(Escola, on_delete=models.RESTRICT, related_name='saas_assinaturas')
    plano = models.ForeignKey(SaasPlano, on_delete=models.RESTRICT, related_name='assinaturas')
    periodicidade = models.CharField(
        max_length=20,
        default='mensal',
        choices=[('mensal', 'Mensal'), ('trimestral', 'Trimestral'), ('semestral', 'Semestral'), ('anual', 'Anual')]
    )
    modo_data_limite = models.CharField(
        max_length=20,
        default='automatico',
        choices=[('automatico', 'Automático'), ('dia_fixo', 'Dia Fixo'), ('manual', 'Manual')]
    )
    dia_limite = models.IntegerField(null=True, blank=True)
    dias_tolerancia = models.IntegerField(default=5)
    dias_ate_suspensao = models.IntegerField(default=15)
    data_bloqueio_manual = models.DateField(null=True, blank=True)
    multa_tipo = models.CharField(
        max_length=20,
        default='nenhuma',
        choices=[('nenhuma', 'Nenhuma'), ('fixo', 'Valor Fixo'), ('percentagem', 'Percentagem')]
    )
    multa_valor = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    estado = models.CharField(
        max_length=30,
        default='activa',
        choices=[
            ('teste', 'Teste'),
            ('activa', 'Activa'),
            ('fatura_pendente', 'Fatura Pendente'),
            ('em_atraso', 'Em Atraso'),
            ('restrita', 'Restrita'),
            ('suspensa', 'Suspensa'),
            ('cancelada', 'Cancelada')
        ]
    )
    data_inicio = models.DateTimeField(default=timezone.now)
    proxima_fatura_em = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_saas_assinaturas'
        verbose_name = 'Assinatura SaaS'
        verbose_name_plural = 'Assinaturas SaaS'
        indexes = [
            models.Index(fields=['instituicao']),
            models.Index(fields=['estado']),
            models.Index(fields=['proxima_fatura_em']),
        ]

    def delete(self, *args, **kwargs):
        from django.db import IntegrityError
        raise IntegrityError("Eliminação não permitida: assinaturas e registos de acesso são invioláveis.")

    def __str__(self):
        return f"{self.instituicao.nome} - {self.plano.nome} [{self.estado}]"


class SaasFatura(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assinatura = models.ForeignKey(SaasAssinatura, on_delete=models.RESTRICT, related_name='faturas')
    instituicao = models.ForeignKey(Escola, on_delete=models.RESTRICT, related_name='saas_faturas')
    numero_fatura = models.CharField(max_length=50)
    periodo_inicio = models.DateField()
    periodo_fim = models.DateField()
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    multa_aplicada = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    data_abertura = models.DateField()
    data_limite = models.DateField()
    data_limite_manual = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        default='aberta',
        choices=[
            ('aberta', 'Aberta'),
            ('paga_parcial', 'Paga Parcial'),
            ('paga', 'Paga'),
            ('em_atraso', 'Em Atraso'),
            ('anulada', 'Anulada')
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def data_limite_efectiva(self):
        from .saas_services import calcular_data_limite_efectiva_python
        return calcular_data_limite_efectiva_python(self)

    class Meta:
        db_table = 'sige_saas_faturas'
        verbose_name = 'Fatura SaaS'
        verbose_name_plural = 'Faturas SaaS'
        constraints = [
            models.UniqueConstraint(fields=['assinatura', 'periodo_inicio'], name='unique_saas_assinatura_periodo_inicio')
        ]
        indexes = [
            models.Index(fields=['instituicao']),
            models.Index(fields=['estado']),
            models.Index(fields=['data_limite']),
        ]

    def delete(self, *args, **kwargs):
        from django.db import IntegrityError
        raise IntegrityError("Eliminação não permitida: faturas são permanentes e invioláveis.")

    @property
    def data_limite_efectiva(self):
        if self.data_limite_manual:
            return self.data_limite_manual
        ass = self.assinatura
        if ass.modo_data_limite == 'dia_fixo' and ass.dia_limite:
            import calendar
            ultimo_dia = calendar.monthrange(self.periodo_inicio.year, self.periodo_inicio.month)[1]
            return self.periodo_inicio.replace(day=min(ass.dia_limite, ultimo_dia))
        return self.data_limite

    def __str__(self):
        return f"{self.numero_fatura} - {self.instituicao.nome} ({self.valor} MZN) [{self.estado}]"


class SaasPagamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fatura = models.ForeignKey(SaasFatura, on_delete=models.RESTRICT, related_name='pagamentos')
    instituicao = models.ForeignKey(Escola, on_delete=models.RESTRICT, related_name='saas_pagamentos')
    metodo = models.CharField(
        max_length=50,
        choices=[
            ('M-Pesa', 'M-Pesa'),
            ('e-Mola', 'e-Mola'),
            ('transferencia_bancaria', 'Transferência Bancária'),
            ('numerario', 'Numerário')
        ]
    )
    referencia = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    comprovativo_path = models.TextField(null=True, blank=True)
    comprovativo_url = models.TextField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        default='enviado',
        choices=[
            ('enviado', 'Enviado'),
            ('confirmado', 'Confirmado'),
            ('rejeitado', 'Rejeitado')
        ]
    )
    confirmado_por = models.CharField(max_length=150, null=True, blank=True)
    confirmado_em = models.DateTimeField(null=True, blank=True)
    motivo_rejeicao = models.TextField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_saas_pagamentos'
        verbose_name = 'Pagamento SaaS'
        verbose_name_plural = 'Pagamentos SaaS'
        indexes = [
            models.Index(fields=['fatura']),
            models.Index(fields=['instituicao']),
            models.Index(fields=['estado']),
        ]

    def delete(self, *args, **kwargs):
        from django.db import IntegrityError
        raise IntegrityError("Eliminação não permitida: registos de pagamento são invioláveis.")

    def __str__(self):
        return f"{self.metodo} - {self.referencia} ({self.valor} MZN) [{self.estado}]"


class SaasLogAssinatura(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instituicao = models.ForeignKey(Escola, on_delete=models.RESTRICT, related_name='saas_logs')
    assinatura = models.ForeignKey(SaasAssinatura, on_delete=models.RESTRICT, null=True, blank=True, related_name='logs')
    fatura = models.ForeignKey(SaasFatura, on_delete=models.RESTRICT, null=True, blank=True, related_name='logs')
    accao = models.CharField(max_length=100)
    estado_anterior = models.CharField(max_length=50, null=True, blank=True)
    estado_novo = models.CharField(max_length=50, null=True, blank=True)
    valor_anterior = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valor_novo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    feito_por = models.CharField(max_length=150, default='sistema')
    motivo = models.TextField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_saas_log_assinaturas'
        verbose_name = 'Log de Assinatura SaaS'
        verbose_name_plural = 'Logs de Assinaturas SaaS'
        indexes = [
            models.Index(fields=['instituicao']),
            models.Index(fields=['criado_em']),
        ]

    def delete(self, *args, **kwargs):
        from django.db import IntegrityError
        raise IntegrityError("Eliminação não permitida: registos de auditoria são imutáveis.")

    def __str__(self):
        return f"{self.instituicao.nome} - {self.accao} por {self.feito_por} em {self.criado_em}"


class SaasCoordenadasPagamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mpesa_numero = models.CharField(max_length=50, blank=True, default='')
    mpesa_titular = models.CharField(max_length=150, blank=True, default='')
    emola_numero = models.CharField(max_length=50, blank=True, default='')
    emola_titular = models.CharField(max_length=150, blank=True, default='')
    bim_conta = models.CharField(max_length=50, blank=True, default='')
    bim_nib = models.CharField(max_length=50, blank=True, default='')
    bim_titular = models.CharField(max_length=150, blank=True, default='')
    bci_conta = models.CharField(max_length=50, blank=True, default='')
    bci_nib = models.CharField(max_length=50, blank=True, default='')
    bci_titular = models.CharField(max_length=150, blank=True, default='')
    nuit_entidade = models.CharField(max_length=50, blank=True, default='')
    instrucoes_adicionais = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_saas_coordenadas'
        verbose_name = 'Coordenadas de Pagamento SaaS'
        verbose_name_plural = 'Coordenadas de Pagamento SaaS'

    @classmethod
    def get_singleton(cls):
        obj = cls.objects.first()
        if not obj:
            obj = cls.objects.create()
        return obj

    def __str__(self):
        return f"Coordenadas de Pagamento SaaS (Atualizado: {self.updated_at})"

