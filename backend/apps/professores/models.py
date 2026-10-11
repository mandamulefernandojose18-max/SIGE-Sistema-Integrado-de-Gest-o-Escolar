import uuid
from django.db import models
from django.core.validators import MinValueValidator

class Professor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='professores')
    codigo = models.CharField(max_length=50, blank=True, null=True, db_index=True)  # Código fixo (ex: PR0101S0001.001)
    nome = models.CharField(max_length=255)
    apelido = models.CharField(max_length=100, blank=True, null=True)
    genero = models.CharField(max_length=10, default='M')
    email = models.EmailField()
    telefone = models.CharField(max_length=50, blank=True, null=True)
    tipo_documento = models.CharField(max_length=100, default='Bilhete de Identidade')
    numero_documento = models.CharField(max_length=100, blank=True, null=True)
    nuit = models.CharField(max_length=50, blank=True, null=True)
    nacionalidade = models.CharField(max_length=100, default='Moçambicana')
    provincia = models.CharField(max_length=100, default='Maputo')
    distrito = models.CharField(max_length=100, default='Cidade de Maputo')
    carreira = models.CharField(max_length=100, default='DN1')
    especialidade = models.CharField(max_length=100)
    carga_horaria_semanal = models.IntegerField(default=20, validators=[MinValueValidator(1)])
    carga_maxima_por_classe = models.JSONField(default=dict, blank=True, null=True)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_professores'
        verbose_name = 'Professor'
        verbose_name_plural = 'Professores'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['email']),
            models.Index(fields=['codigo']),
        ]

    def save(self, *args, **kwargs):
        # O código do Professor é FIXO: só é gerado uma única vez no registo (ou se estiver vazio)
        if not self.codigo:
            from common.utils.geografia_mocambique import gerar_codigo_fixo_professor
            self.codigo = gerar_codigo_fixo_professor(self.escola, exclude_prof_id=self.id)
        super().save(*args, **kwargs)

        # Sincronizar conta de acesso (Usuario) com o código fixo do professor
        try:
            from apps.accounts.models import Usuario
            nome_completo = f"{self.nome} {self.apelido or ''}".strip()
            u = (
                Usuario.objects.filter(professor_id=self.id).first()
                or (Usuario.objects.filter(email__iexact=self.email).first() if self.email else None)
            )
            if not u:
                email_cand = (self.email or '').strip().lower()
                if not email_cand or Usuario.objects.filter(email__iexact=email_cand).exists():
                    slug_c = (self.codigo or str(self.id)[:8]).lower().replace('.', '_')
                    email_cand = f"{slug_c}@sige.edu.mz"
                Usuario.objects.create_user(
                    email=email_cand,
                    password='123456',
                    nome=nome_completo,
                    role='PROFESSOR',
                    escola=self.escola,
                    telefone=self.telefone or '',
                    professor_id=self.id,
                    codigo_acesso=self.codigo,
                )
            else:
                changed = False
                if u.professor_id != self.id:
                    u.professor_id = self.id
                    changed = True
                if u.codigo_acesso != self.codigo:
                    u.codigo_acesso = self.codigo
                    changed = True
                if u.escola_id != self.escola_id:
                    u.escola = self.escola
                    changed = True
                if changed:
                    u.save()
        except Exception:
            pass

    def __str__(self):
        return f"{self.nome} [{self.codigo or self.especialidade}]"

class AlocacaoDocente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='alocacoes')
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='alocacoes')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.CASCADE, related_name='alocacoes')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.CASCADE, related_name='alocacoes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_professor_disciplina_turma'
        verbose_name = 'Alocação Docente'
        verbose_name_plural = 'Alocações Docentes'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['professor']),
            models.Index(fields=['disciplina']),
            models.Index(fields=['turma']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['escola', 'professor', 'disciplina', 'turma'],
                name='unique_alocacao_docente_disciplina_turma'
            ),
        ]

    def clean(self):
        from common.integrity import validar_integridade_tenant
        validar_integridade_tenant(self, professor=self.professor, disciplina=self.disciplina, turma=self.turma)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
