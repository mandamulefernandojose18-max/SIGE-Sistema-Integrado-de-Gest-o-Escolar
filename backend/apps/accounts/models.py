import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório.')
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'SUPERADMIN')
        return self.create_user(email, password, **extra_fields)

class Usuario(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=255)
    
    ROLE_CHOICES = [
        ('SUPERADMIN', 'Super Administrador do SaaS'),
        ('ADMIN_ESCOLA', 'Administrador da Escola'),
        ('DIRECTOR_ESCOLA', 'Director de Escola'),
        ('DAP', 'Director Adjunto Pedagógico (DAP)'),
        ('CHEFE_SECRETARIA', 'Chefe de Secretaria'),
        ('PROFESSOR', 'Professor'),
        ('ALUNO', 'Aluno'),
        ('FINANCEIRO', 'Financeiro'),
    ]
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='ADMIN_ESCOLA')
    escola = models.ForeignKey(
        'tenants.Escola',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='usuarios'
    )
    ativo = models.BooleanField(default=True)
    telefone = models.CharField(max_length=50, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    aluno_id = models.UUIDField(null=True, blank=True)
    professor_id = models.UUIDField(null=True, blank=True)

    username = models.CharField(max_length=150, unique=True, blank=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    def save(self, *args, **kwargs):
        if not self.username and self.email:
            self.username = self.email
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'sige_usuarios'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.nome} ({self.email}) - {self.role}"

class LogAcesso(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escola = models.ForeignKey('tenants.Escola', on_delete=models.CASCADE, null=True, blank=True, related_name='logs_acesso')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_acesso')
    ip = models.CharField(max_length=50, default='127.0.0.1')
    user_agent = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=50)  # LOGIN_SUCESSO, LOGIN_FALHA, ACESSO_BLOQUEADO_EXPIRADO
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sige_logs_acesso'
        indexes = [
            models.Index(fields=['escola']),
            models.Index(fields=['tipo']),
            models.Index(fields=['created_at']),
        ]
