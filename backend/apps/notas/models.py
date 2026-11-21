import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Nota(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='notas')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='notas')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.CASCADE, related_name='notas')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, related_name='notas')
    periodo = models.CharField(max_length=20)  # 1_TRIMESTRE, 2_TRIMESTRE, 3_TRIMESTRE, ANUAL

    teste1 = models.FloatField(
        default=0, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    teste2 = models.FloatField(
        default=0, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    teste3 = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    teste4 = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    trabalho = models.FloatField(
        default=0, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    avaliacao_trimestral = models.FloatField(
        default=0, null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    media_final = models.FloatField(
        default=0,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    
    faltas = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    anotacao = models.CharField(max_length=10, blank=True, null=True)  # D, T, VT, F, AM, PPF, PDF
    comportamento = models.CharField(max_length=5, blank=True, null=True, default='')  # NS, S, B, MB, E
    resultado = models.CharField(max_length=20, default='Aprovado')  # Aprovado, Reprovado

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_notas'
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['aluno']),
            models.Index(fields=['disciplina']),
            models.Index(fields=['turma']),
            models.Index(fields=['periodo']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['escola', 'aluno', 'disciplina', 'turma', 'periodo'],
                name='unique_nota_aluno_disciplina_periodo'
            ),
            models.CheckConstraint(
                check=models.Q(media_final__gte=0.0) & models.Q(media_final__lte=20.0),
                name='check_nota_media_final_range'
            ),
            models.CheckConstraint(
                check=models.Q(faltas__gte=0),
                name='check_nota_faltas_positivas'
            ),
        ]

    def clean(self):
        from common.integrity import (
            validar_escala_nota, validar_faltas, validar_periodo_academico,
            validar_comportamento, validar_anotacao_mec, validar_anotacao_minedh,
            validar_integridade_tenant, verificar_pauta_permite_edicao_nota
        )
        # 1. Integridade de Isolamento Multi-Tenant
        validar_integridade_tenant(self, aluno=self.aluno, disciplina=self.disciplina, turma=self.turma)

        # 2. Integridade de Domínio
        validar_periodo_academico(self.periodo)
        validar_comportamento(self.comportamento)
        validar_anotacao_mec(self.anotacao)
        validar_faltas(self.faltas)

        for campo in ['teste1', 'teste2', 'teste3', 'teste4', 'trabalho', 'avaliacao_trimestral', 'media_final']:
            val = getattr(self, campo, None)
            if val is not None:
                validar_escala_nota(val)

        # 3. Cálculo rigoroso e sincronização automática da média e resultado conforme regras oficiais do MEC
        from common.utils.avaliacoes_mocambique import calcular_media_trimestral
        tem_avaliacoes = any(
            getattr(self, campo, None) is not None and getattr(self, campo, 0) > 0
            for campo in ['teste1', 'teste2', 'teste3', 'teste4', 'trabalho', 'avaliacao_trimestral']
        )
        if tem_avaliacoes:
            calc = calcular_media_trimestral({
                'teste1': self.teste1,
                'teste2': self.teste2,
                'teste3': self.teste3,
                'teste4': self.teste4,
                'trabalho': self.trabalho,
                'avaliacao_trimestral': self.avaliacao_trimestral
            })
            self.media_final = float(calc['mediaFinal'])
            self.resultado = calc['resultado']
            if not self.comportamento:
                self.comportamento = calc['comportamento']
        elif self.media_final is not None and self.media_final > 0:
            self.resultado = 'Aprovado' if self.media_final >= 9.5 else 'Reprovado'
        else:
            if not self.comportamento or self.comportamento == 'S':
                self.comportamento = ''

        # 4. Integridade de Estado / Imutabilidade de Pauta Fechada
        verificar_pauta_permite_edicao_nota(self.escola, self.turma, self.disciplina, self.periodo)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aluno.nome} - {self.disciplina.nome} ({self.periodo}): {self.media_final}"

class PermissaoEdicaoNotas(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='permissoes_edicao')
    professor = models.ForeignKey('professores.Professor', on_delete=models.CASCADE, null=True, blank=True, related_name='permissoes_edicao')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, related_name='permissoes_edicao')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.CASCADE, null=True, blank=True, related_name='permissoes_edicao')
    periodo = models.CharField(max_length=20)  # 1_TRIMESTRE, 2_TRIMESTRE, 3_TRIMESTRE, TODOS
    autorizado_por = models.CharField(max_length=255)
    motivo = models.TextField(blank=True, null=True)
    duracao_horas = models.IntegerField(default=48)
    data_expiracao = models.DateTimeField(null=True, blank=True)
    ativa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_permissoes_edicao_notas'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['professor']),
            models.Index(fields=['ativa']),
        ]

    @property
    def expirada(self):
        from django.utils import timezone
        if self.data_expiracao and timezone.now() > self.data_expiracao:
            return True
        return False

    def clean(self):
        from common.integrity import validar_integridade_tenant, validar_periodo_academico
        validar_integridade_tenant(self, professor=self.professor, turma=self.turma, disciplina=self.disciplina)
        if self.periodo not in ('TODOS', 'ANUAL'):
            validar_periodo_academico(self.periodo)

    def save(self, *args, **kwargs):
        from django.utils import timezone
        from datetime import timedelta
        if not self.data_expiracao and self.duracao_horas:
            self.data_expiracao = timezone.now() + timedelta(hours=self.duracao_horas)
        self.full_clean()
        super().save(*args, **kwargs)


class NotaExame(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='notas_exame')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='notas_exame')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.CASCADE, related_name='notas_exame')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, related_name='notas_exame')
    ano_letivo = models.CharField(max_length=10, default='2026')

    nota_frequencia = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    exame_1epoca = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    exame_2epoca = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    nota_final = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    resultado = models.CharField(max_length=25, default='Pendente')  # Aprovado, Reprovado, Admitido, Excluido, Dispensado

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_notas_exame'
        verbose_name = 'Nota de Exame'
        verbose_name_plural = 'Notas de Exame'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['aluno']),
            models.Index(fields=['disciplina']),
            models.Index(fields=['turma']),
            models.Index(fields=['ano_letivo']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['escola', 'aluno', 'disciplina', 'turma', 'ano_letivo'],
                name='unique_nota_exame_aluno_disc_ano'
            ),
        ]

    def clean(self):
        from common.integrity import validar_integridade_tenant, validar_escala_nota
        validar_integridade_tenant(self, aluno=self.aluno, disciplina=self.disciplina, turma=self.turma)

        for campo in ['nota_frequencia', 'exame_1epoca', 'exame_2epoca', 'nota_final']:
            val = getattr(self, campo, None)
            if val is not None:
                validar_escala_nota(val)

        # Cálculo oficial MEC (Moçambique):
        # Nota do exame: Se fez 2ª época, prevalece a 2ª época; caso contrário, 1ª época
        nota_exame = self.exame_2epoca if self.exame_2epoca is not None else self.exame_1epoca

        if nota_exame is not None:
            if self.nota_frequencia is not None:
                # Média final oficial da disciplina com exame: (MFreq + NE) / 2
                self.nota_final = float(round((self.nota_frequencia + nota_exame) / 2))
            else:
                self.nota_final = float(round(nota_exame))
            self.resultado = 'Aprovado' if self.nota_final >= 9.5 else 'Reprovado'
        elif self.nota_frequencia is not None:
            self.nota_final = float(round(self.nota_frequencia))
            if self.nota_frequencia >= 9.5:
                self.resultado = 'Admitido'
            else:
                self.resultado = 'Excluído'
        else:
            self.resultado = 'Pendente'

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Exame {self.aluno.nome} - {self.disciplina.nome}: Freq={self.nota_frequencia}, 1ª={self.exame_1epoca}, 2ª={self.exame_2epoca}, Final={self.nota_final}"



class PlanoAulaSumario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='sumarios_aulas')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, related_name='sumarios_aulas')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.CASCADE, related_name='sumarios_aulas')
    professor = models.ForeignKey('professores.Professor', on_delete=models.CASCADE, related_name='sumarios_aulas')
    numero_aula = models.IntegerField(default=1)
    data = models.DateField(db_index=True)
    tempo_aula = models.CharField(max_length=50, default='1º e 2º Tempos')
    unidade_tematica = models.CharField(max_length=255, default='Geral')
    tema = models.CharField(max_length=255)
    sumario = models.TextField()
    objetivos = models.TextField(blank=True, default='')
    tarefa_casa = models.TextField(blank=True, default='')
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente de Validação DAP'),
        ('VALIDADO_DAP', 'Validado pelo Director Pedagógico'),
        ('REVISAO_SOLICITADA', 'Revisão Solicitada pelo DAP'),
    ]
    status_validacao = models.CharField(max_length=25, choices=STATUS_CHOICES, default='PENDENTE')
    observacoes_dap = models.TextField(blank=True, default='')
    validado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='sumarios_validados')
    data_validacao = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_planos_sumarios'
        verbose_name = 'Plano de Aula e Sumário'
        verbose_name_plural = 'Planos de Aula e Sumários'
        indexes = [
            models.Index(fields=['escola', 'turma', 'data']),
            models.Index(fields=['professor', 'disciplina']),
            models.Index(fields=['status_validacao']),
        ]

    def __str__(self):
        return f'Aula {self.numero_aula} ({self.data}) - {self.tema}'

class OcorrenciaDisciplinar(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='ocorrencias_disciplinares')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='ocorrencias_disciplinares')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.SET_NULL, null=True, blank=True, related_name='ocorrencias_disciplinares')
    autor = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, related_name='ocorrencias_autor')
    data = models.DateField(db_index=True)
    GRAVIDADE_CHOICES = [
        ('LEVE', 'Falta Leve'),
        ('GRAVE', 'Falta Grave'),
        ('MUITO_GRAVE', 'Falta Muito Grave'),
    ]
    gravidade = models.CharField(max_length=20, choices=GRAVIDADE_CHOICES, default='LEVE')
    descricao = models.TextField()
    medida_tomada = models.TextField(blank=True, default='')
    notificar_encarregado = models.BooleanField(default=True)
    STATUS_CHOICES = [
        ('REGISTADA', 'Registada (Aguardando Parecer)'),
        ('HOMOLOGADA_DAP', 'Homologada pelo DAP'),
        ('CONCLUIDA', 'Resolvida / Concluída'),
    ]
    status_validacao = models.CharField(max_length=25, choices=STATUS_CHOICES, default='REGISTADA')
    parecer_dap = models.TextField(blank=True, default='')
    validado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='ocorrencias_homologadas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_ocorrencias_disciplinares'
        verbose_name = 'Ocorrência Disciplinar'
        verbose_name_plural = 'Ocorrências Disciplinares'
        indexes = [
            models.Index(fields=['escola', 'aluno']),
            models.Index(fields=['data']),
            models.Index(fields=['gravidade']),
            models.Index(fields=['status_validacao']),
        ]

    def __str__(self):
        return f'{self.gravidade}: {self.aluno.nome} ({self.data})'


class CalendarioExame(models.Model):
    """Data, período e horário de cada disciplina com exame, por classe e chamada (1ª ou 2ª época)."""
    EPOCAS = [(1, '1ª Chamada/Época'), (2, '2ª Chamada/Época')]
    PERIODOS = [('MANHA', 'Manhã'), ('TARDE', 'Tarde'), ('NOITE', 'Noturno')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='calendario_exames')
    ano_letivo = models.CharField(max_length=10)
    classe = models.CharField(max_length=50)
    disciplina = models.CharField(max_length=100)
    epoca = models.PositiveSmallIntegerField(choices=EPOCAS, default=1)
    data = models.DateField()
    periodo = models.CharField(max_length=10, choices=PERIODOS, blank=True, default='')
    hora_inicio = models.TimeField()
    duracao_minutos = models.PositiveSmallIntegerField()
    hora_fim = models.TimeField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_calendario_exames'
        verbose_name = 'Calendário de Exame'
        verbose_name_plural = 'Calendário de Exames'
        indexes = [models.Index(fields=['escola', 'ano_letivo', 'classe'])]
        constraints = [
            models.UniqueConstraint(
                fields=['escola', 'ano_letivo', 'classe', 'disciplina', 'epoca'],
                name='unique_calendario_exame_disc_epoca',
            ),
        ]

    def save(self, *args, **kwargs):
        from datetime import datetime, timedelta
        fim = datetime.combine(self.data, self.hora_inicio) + timedelta(minutes=int(self.duracao_minutos))
        self.hora_fim = fim.time()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.classe} · {self.disciplina} · {self.epoca}ª época · {self.data}'


class JuriExame(models.Model):
    """Júri de exame formado automaticamente para uma disciplina/classe/época (com sala opcional)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='juris_exame')
    ano_letivo = models.CharField(max_length=10)
    classe = models.CharField(max_length=50)
    disciplina = models.CharField(max_length=100)
    epoca = models.PositiveSmallIntegerField(default=1)
    numero = models.PositiveIntegerField()
    sala = models.CharField(max_length=50, blank=True, default='')
    max_alunos = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_juris_exame'
        verbose_name = 'Júri de Exame'
        verbose_name_plural = 'Júris de Exame'
        ordering = ['classe', 'disciplina', 'epoca', 'numero']
        indexes = [models.Index(fields=['escola', 'ano_letivo', 'classe', 'epoca'])]
        constraints = [
            models.UniqueConstraint(
                fields=['escola', 'ano_letivo', 'classe', 'disciplina', 'epoca', 'numero'],
                name='unique_juri_exame_numero',
            ),
        ]


class JuriExameAluno(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    juri = models.ForeignKey(JuriExame, on_delete=models.CASCADE, related_name='alunos_juri')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='juris_exame')
    ordem = models.PositiveIntegerField()

    class Meta:
        db_table = 'sige_juris_exame_alunos'
        ordering = ['juri', 'ordem']
        constraints = [
            models.UniqueConstraint(fields=['juri', 'aluno'], name='unique_juri_exame_aluno'),
        ]


class ProvaFisica(models.Model):
    """Prova em papel a corrigir com apoio do sistema (grelha de cotações por pergunta)."""
    INSTRUMENTOS = [
        ('teste1', '1º Teste (ACS)'), ('teste2', '2º Teste (ACS)'), ('teste3', '3º Teste (ACS)'),
        ('teste4', '4º Teste (ACS)'), ('trabalho', 'Trabalho (MAP)'), ('avaliacao_trimestral', 'Avaliação Trimestral (AT)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='provas_fisicas')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, related_name='provas_fisicas')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.CASCADE, related_name='provas_fisicas')
    periodo = models.CharField(max_length=20)
    instrumento = models.CharField(max_length=30, choices=INSTRUMENTOS)
    titulo = models.CharField(max_length=255)
    TIPOS = [('DISCURSIVA', 'Discursiva (pontos por pergunta)'),
             ('MULTIPLA_ESCOLHA', 'Escolha múltipla (Folha de Resposta do sistema)')]
    tipo = models.CharField(max_length=20, choices=TIPOS, default='DISCURSIVA')
    perguntas = models.JSONField(
        default=list, help_text='[{"numero": 1, "cotacao": 2.5, "tipo": "MC"|"ABERTA"|"LIVRE"}, ...]')
    cotacao_total = models.FloatField(validators=[MinValueValidator(0.01)])
    # Escolha múltipla: mesma configuração da Folha de Resposta gerada (alternativas, versões e chaves de correcção)
    n_alternativas = models.PositiveSmallIntegerField(default=0)
    versoes = models.JSONField(default=list, blank=True)
    gabaritos = models.JSONField(default=dict, blank=True, help_text='{"A": "ABCD...", "-": "..."}; nunca devolvido pela API')
    criado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='provas_fisicas_criadas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_provas_fisicas'
        verbose_name = 'Prova Física'
        verbose_name_plural = 'Provas Físicas'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['escola', 'turma', 'disciplina', 'periodo'])]

    def __str__(self):
        return f'{self.titulo} ({self.periodo})'


class CorrecaoProva(models.Model):
    ESTADOS = [('RASCUNHO', 'Rascunho'), ('CORRIGIDA', 'Corrigida'), ('LANCADA', 'Lançada na caderneta')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='correcoes_prova')
    prova = models.ForeignKey(ProvaFisica, on_delete=models.CASCADE, related_name='correcoes')
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='correcoes_prova')
    pontos = models.JSONField(default=list, help_text='Pontos por pergunta (null = ainda por corrigir)')
    # Escolha múltipla: versão da folha e respostas assinaladas pelo aluno ("-" = em branco)
    versao = models.CharField(max_length=2, blank=True, default='')
    respostas = models.CharField(max_length=120, blank=True, default='')
    total = models.FloatField(default=0)
    nota = models.FloatField(default=0, validators=[MinValueValidator(0.0), MaxValueValidator(20.0)])
    estado = models.CharField(max_length=12, choices=ESTADOS, default='RASCUNHO')
    corrigido_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='correcoes_prova')
    lancada_em = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_correcoes_prova'
        verbose_name = 'Correção de Prova'
        verbose_name_plural = 'Correções de Provas'
        indexes = [models.Index(fields=['escola', 'prova'])]
        constraints = [models.UniqueConstraint(fields=['prova', 'aluno'], name='unique_correcao_prova_aluno')]


class CorrecaoImagem(models.Model):
    """Página digitalizada da prova; o ficheiro fica em MEDIA_ROOT/provas_fisicas/<escola>/ e só se serve autenticado."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='correcoes_imagens')
    correcao = models.ForeignKey(CorrecaoProva, on_delete=models.CASCADE, related_name='imagens')
    caminho = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20)
    tamanho = models.PositiveIntegerField(default=0)
    ordem = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_correcoes_imagens'
        ordering = ['correcao', 'ordem']


class GabaritoGuardado(models.Model):
    """Gabarito / guião de correcção guardado pelo professor para reutilizar noutras provas (não precisa de recomeçar)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='gabaritos_guardados')
    criado_por = models.ForeignKey('accounts.Usuario', on_delete=models.CASCADE, related_name='gabaritos_guardados')
    nome = models.CharField(max_length=120)
    n_perguntas = models.PositiveSmallIntegerField()
    n_alternativas = models.PositiveSmallIntegerField(default=4)
    versoes = models.JSONField(default=list, blank=True)
    gabaritos = models.JSONField(default=dict, help_text='{"A": "ABCD...", "-": "ABCD..."}')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_gabaritos_guardados'
        verbose_name = 'Gabarito guardado'
        verbose_name_plural = 'Gabaritos guardados'
        ordering = ['nome']
        constraints = [models.UniqueConstraint(fields=['escola', 'criado_por', 'nome'], name='uniq_gabarito_guardado_nome')]
        indexes = [models.Index(fields=['escola', 'criado_por'])]

    def __str__(self):
        return f'{self.nome} ({self.n_perguntas})'
