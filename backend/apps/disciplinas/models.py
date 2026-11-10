import uuid
from django.db import models
from django.core.validators import MinValueValidator

class DisciplinaCatalogo(models.Model):
    """Catálogo 'Todas Disciplinas de Ensino' da escola: qualquer disciplina que possa vir a ser usada nas classes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='disciplinas_catalogo')
    nome = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_disciplinas_catalogo'
        verbose_name = 'Disciplina do Catálogo'
        verbose_name_plural = 'Catálogo de Disciplinas'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(models.functions.Lower('nome'), 'escola', name='unique_catalogo_escola_nome_ci'),
        ]

    def __str__(self):
        return self.nome


class Disciplina(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='disciplinas')
    catalogo = models.ForeignKey(DisciplinaCatalogo, on_delete=models.SET_NULL, null=True, blank=True, related_name='disciplinas_classe')
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=50)
    classe = models.CharField(max_length=50, default='10ª Classe')
    area = models.CharField(max_length=50, default='Geral')
    carga_horaria = models.IntegerField(default=60, validators=[MinValueValidator(1)])
    ano_letivo = models.CharField(max_length=10, default='2026')
    tem_exame = models.BooleanField(default=False, verbose_name="Tem Exame")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_disciplinas'
        verbose_name = 'Disciplina'
        verbose_name_plural = 'Disciplinas'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['codigo']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['escola', 'codigo', 'ano_letivo'],
                name='unique_disciplina_escola_codigo_ano_letivo'
            ),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.codigo})"


class AreaSeccao(models.Model):
    """Área / Secção de uma Classe ou Nível (Plano Curricular). Ex.: Ciências com Biologia na 11ª Classe."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='areas_seccoes')
    classe = models.CharField(max_length=50)
    nome = models.CharField(max_length=80)
    ordem = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_areas_seccoes'
        verbose_name = 'Área / Secção'
        verbose_name_plural = 'Áreas / Secções'
        ordering = ['classe', 'ordem', 'nome']
        indexes = [models.Index(fields=['escola', 'classe'])]
        constraints = [
            models.UniqueConstraint(fields=['escola', 'classe', 'nome'], name='unique_area_seccao_escola_classe_nome'),
        ]

    def __str__(self):
        return f"{self.classe} — {self.nome}"


class AreaSeccaoDisciplina(models.Model):
    """Disciplina pertencente a uma Área/Secção, com indicação se tem exame nessa área."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='areas_seccoes_disciplinas')
    area = models.ForeignKey(AreaSeccao, on_delete=models.CASCADE, related_name='vinculos')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name='vinculos_area')
    tem_exame = models.BooleanField(default=False)

    class Meta:
        db_table = 'sige_areas_seccoes_disciplinas'
        constraints = [
            models.UniqueConstraint(fields=['area', 'disciplina'], name='unique_area_seccao_disciplina'),
        ]

    def __str__(self):
        return f"{self.area} / {self.disciplina}"
