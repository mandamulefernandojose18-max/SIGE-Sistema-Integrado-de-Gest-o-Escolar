import uuid
import datetime
from django.db import models

def gerar_proxima_matricula(escola=None, ano_ingresso=None):
    if ano_ingresso and str(ano_ingresso).strip().isdigit():
        ano = int(str(ano_ingresso).strip())
    elif escola and hasattr(escola, 'ano_letivo_ativo') and escola.ano_letivo_ativo and str(escola.ano_letivo_ativo).strip().isdigit():
        ano = int(str(escola.ano_letivo_ativo).strip())
    else:
        ano = datetime.date.today().year

    prefixo = str(ano)
    qs = Aluno.objects.filter(matricula__startswith=prefixo)
    ultimo = qs.order_by('-matricula').first()
    if ultimo and ultimo.matricula and ultimo.matricula.isdigit():
        try:
            proximo = int(ultimo.matricula) + 1
            cand = str(proximo)
            if not Aluno.objects.filter(matricula=cand).exists():
                return cand
        except (ValueError, TypeError):
            pass
    count = qs.count() + 1
    cand = f"{ano}{count:03d}"
    while Aluno.objects.filter(matricula=cand).exists():
        count += 1
        cand = f"{ano}{count:03d}"
    return cand

class Aluno(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='alunos')
    turma = models.ForeignKey('turmas.Turma', on_delete=models.SET_NULL, null=True, blank=True, related_name='alunos')
    classe = models.CharField(max_length=50, blank=True, null=True)  # ex: 10ª Classe
    area = models.CharField(max_length=50, default='Geral', blank=True, null=True)  # ex: Geral, Ciências, Letras
    ano_ingresso = models.CharField(max_length=10, default='2026', blank=True, null=True)
    matricula = models.CharField(max_length=50, unique=True)
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

    def clean(self):
        from common.integrity import validar_integridade_tenant
        if self.turma:
            validar_integridade_tenant(self, turma=self.turma)

    def save(self, *args, **kwargs):
        if not self.ano_ingresso:
            if self.turma and getattr(self.turma, 'ano_letivo', None):
                self.ano_ingresso = self.turma.ano_letivo
            elif self.escola and getattr(self.escola, 'ano_letivo_ativo', None):
                self.ano_ingresso = self.escola.ano_letivo_ativo
            else:
                self.ano_ingresso = str(datetime.date.today().year)
        if not self.matricula:
            self.matricula = gerar_proxima_matricula(self.escola, self.ano_ingresso)
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
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.matricula})"
