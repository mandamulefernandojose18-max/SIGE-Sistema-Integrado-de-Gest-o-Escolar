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
            validar_comportamento, validar_anotacao_minedh,
            validar_integridade_tenant, verificar_pauta_permite_edicao_nota
        )
        # 1. Integridade de Isolamento Multi-Tenant
        validar_integridade_tenant(self, aluno=self.aluno, disciplina=self.disciplina, turma=self.turma)

        # 2. Integridade de Domínio
        validar_periodo_academico(self.periodo)
        validar_comportamento(self.comportamento)
        validar_anotacao_minedh(self.anotacao)
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

