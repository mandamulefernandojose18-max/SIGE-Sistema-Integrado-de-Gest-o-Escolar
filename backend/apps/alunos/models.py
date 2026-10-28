import uuid
import datetime
from django.db import models

def gerar_proxima_matricula(escola=None, ano_ingresso=None, classe=None, turma=None, area=None, aluno_id=None, numero=None, matricula_existente=None):
    from common.utils.geografia_mocambique import gerar_codigo_aluno_oficial
    return gerar_codigo_aluno_oficial(
        escola=escola,
        classe=classe,
        turma=turma,
        ano=ano_ingresso,
        area=area,
        aluno_id=aluno_id,
        numero=numero,
        matricula_existente=matricula_existente,
    )

class Aluno(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='alunos')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.SET_NULL, null=True, blank=True, related_name='alunos')
    classe = models.CharField(max_length=50, blank=True, null=True)  # ex: 10ª Classe
    area = models.CharField(max_length=50, default='Geral', blank=True, null=True)  # ex: Geral, Ciências, Letras
    ano_ingresso = models.CharField(max_length=10, default='2026', blank=True, null=True)
    matricula = models.CharField(max_length=80, db_index=True)  # ex: 0101S0001.12.01.2026.cg
    nome = models.CharField(max_length=255)
    apelido = models.CharField(max_length=100, blank=True, null=True)
    data_nascimento = models.DateField()
    genero = models.CharField(max_length=10)  # M, F
    tipo_documento = models.CharField(max_length=100, default='Bilhete de Identidade')
    numero_documento = models.CharField(max_length=100, blank=True, null=True)
    nuit = models.CharField(max_length=50, blank=True, null=True)
    nacionalidade = models.CharField(max_length=100, default='Moçambicana')
    provincia = models.CharField(max_length=100, default='Maputo')
    distrito = models.CharField(max_length=100, default='Cidade de Maputo')
    pai = models.CharField(max_length=255, blank=True, null=True)
    mae = models.CharField(max_length=255, blank=True, null=True)
    nome_responsavel = models.CharField(max_length=255, blank=True, null=True)
    contato_responsavel = models.CharField(max_length=50, blank=True, null=True)
    email_responsavel = models.EmailField(blank=True, null=True)
    status = models.CharField(max_length=20, default='ATIVO')  # ATIVO, INATIVO, TRANSFERIDO, EVADIDO
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_alunos'
        verbose_name = 'Aluno'
        verbose_name_plural = 'Alunos'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['turma']),
            models.Index(fields=['classe']),
            models.Index(fields=['area']),
            models.Index(fields=['ano_ingresso']),
            models.Index(fields=['matricula']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['escola', 'matricula'],
                name='unique_aluno_escola_matricula'
            ),
        ]

    def clean(self):
        super().clean()
        from common.integrity import validar_integridade_tenant, IntegrityRuleViolation
        from common.utils.geografia_mocambique import codigo_ja_existe_globalmente
        if self.turma:
            validar_integridade_tenant(self, turma=self.turma)
        if self.matricula and codigo_ja_existe_globalmente(self.matricula, exclude_aluno_id=self.id):
            raise IntegrityRuleViolation(
                f"O código de aluno/matrícula '{self.matricula}' já está em uso ou coincide com o código de um funcionário ou outro aluno."
            )

    def save(self, *args, **kwargs):
        if not self.ano_ingresso:
            if self.turma and getattr(self.turma, 'ano_letivo', None):
                self.ano_ingresso = self.turma.ano_letivo
            elif self.escola and getattr(self.escola, 'ano_letivo_ativo', None):
                self.ano_ingresso = self.escola.ano_letivo_ativo
            else:
                self.ano_ingresso = str(datetime.date.today().year)

        if self.turma and getattr(self.turma, 'grau_ano', None):
            self.classe = self.turma.grau_ano

        # Preservar área cadastrada pelo utilizador. Não substituir por 'Geral' se já tiver área definida!
        tem_area_especifica = bool(self.area and str(self.area).strip().lower() not in ['', 'geral', 'ensino geral', 'tronco comum', 'none'])
        if not tem_area_especifica:
            if self.turma and getattr(self.turma, 'area', None) and str(self.turma.area).strip().lower() not in ['', 'geral', 'ensino geral']:
                self.area = self.turma.area
            else:
                cls_str = str(self.classe or '').lower()
                if '11' in cls_str or '12' in cls_str:
                    from apps.disciplinas.models import Disciplina
                    disc_area = Disciplina.objects.filter(
                        escola=self.escola,
                        classe__icontains='11' if '11' in cls_str else '12'
                    ).exclude(area__in=['', 'Geral', 'Ensino Geral']).values_list('area', flat=True).first()
                    self.area = disc_area or 'Ciências com Geografia'
                else:
                    self.area = 'Ensino Geral'

        # O Código do Aluno depende da Escola + Classe + Turma + Ano + Área + Número Sequencial único
        from common.utils.geografia_mocambique import gerar_codigo_aluno_oficial
        self.matricula = gerar_codigo_aluno_oficial(
            escola=self.escola,
            classe=self.classe,
            turma=self.turma,
            ano=self.ano_ingresso,
            area=self.area,
            aluno_id=self.id,
            matricula_existente=self.matricula,
        )

        self.full_clean()
        super().save(*args, **kwargs)

        # Sincronizar conta de acesso (Usuario) do aluno com o código oficial (senha inicial = repetir o código)
        try:
            from apps.accounts.models import Usuario
            nome_completo = f"{self.nome} {self.apelido or ''}".strip()
            u = Usuario.objects.filter(aluno_id=self.id).first()
            if not u:
                email_cand = f"aluno.{str(self.id)[:8].lower()}@sige.edu.mz"
                Usuario.objects.create_user(
                    email=email_cand,
                    password=self.matricula,
                    nome=nome_completo,
                    role='ALUNO',
                    escola=self.escola,
                    telefone=self.contato_responsavel or '',
                    aluno_id=self.id,
                    codigo_acesso=self.matricula,
                    senha_redefinida=False,
                )
            else:
                changed = False
                if u.codigo_acesso != self.matricula:
                    u.codigo_acesso = self.matricula
                    if not u.senha_redefinida:
                        u.set_password(self.matricula)
                    changed = True
                if u.escola_id != self.escola_id:
                    u.escola = self.escola
                    changed = True
                if changed:
                    u.save()
        except Exception:
            pass

    @property
    def nome_completo(self):
        nome = (self.nome or '').strip()
        apelido = (self.apelido or '').strip()
        if not apelido:
            return nome
        if not nome:
            return apelido
        if nome.lower().endswith(apelido.lower()):
            return nome
        return f"{nome} {apelido}"

    def __str__(self):
        return f"{self.nome} ({self.matricula})"
