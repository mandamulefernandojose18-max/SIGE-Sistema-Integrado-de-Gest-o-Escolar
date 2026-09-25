import uuid
from django.db import models

class Professor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='professores')
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
    carga_horaria_semanal = models.IntegerField(default=20)
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
        ]

    def __str__(self):
        return f"{self.nome} ({self.especialidade})"

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
