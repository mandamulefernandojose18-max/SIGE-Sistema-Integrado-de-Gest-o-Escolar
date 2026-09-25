import uuid
from django.db import models

class MaterialEscolar(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, related_name='materiais_escolares')
    disciplina = models.ForeignKey('disciplinas.Disciplina', on_delete=models.SET_NULL, null=True, blank=True, related_name='materiais')
    classe = models.CharField(max_length=50)  # ex: "10ª Classe", "12ª Classe"
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, null=True)
    nome_arquivo = models.CharField(max_length=255, default='material.pdf')
    extensao = models.CharField(max_length=20, default='pdf')
    tamanho_bytes = models.BigIntegerField(default=0)
    conteudo_base64 = models.TextField(blank=True, null=True)
    tipo_mime = models.CharField(max_length=100, default='application/pdf')
    arquivo_url = models.URLField(blank=True, null=True)
    
    TIPO_CHOICES = [
        ('MANUAL', 'Manual Escolar'),
        ('FICHA', 'Ficha de Exercícios'),
        ('LIVRO', 'Livro Didático'),
        ('EXERCICIOS', 'Caderno de Exercícios'),
        ('GUIA', 'Guia do Professor'),
        ('OUTRO', 'Outro Recurso'),
    ]
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, default='MANUAL')
    publicado_por = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sige_material_escolar'
        verbose_name = 'Material Escolar'
        verbose_name_plural = 'Materiais Escolares'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['classe']),
            models.Index(fields=['tipo']),
        ]

    def clean(self):
        from common.integrity import validar_integridade_tenant
        if self.disciplina:
            validar_integridade_tenant(self, disciplina=self.disciplina)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titulo} - {self.classe} ({self.tipo})"
