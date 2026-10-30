from rest_framework.permissions import BasePermission
from .matriz import checar_permissao_matriz

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'role', '') == 'SUPERADMIN')

class IsEscolaAdmin(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        role = getattr(request.user, 'role', '')
        return role in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'SECRETARIA']

class IsDirectorEscola(BasePermission):
    """Apenas Director de Escola, Administrador Escolar ou SuperAdmin."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        role = getattr(request.user, 'role', '')
        return role in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA']

class IsDAP(BasePermission):
    """Director Pedagógico, Direcção ou SuperAdmin."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        role = getattr(request.user, 'role', '')
        return role in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP']

class IsSecretaria(BasePermission):
    """Secretaria, Direcção ou SuperAdmin."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        role = getattr(request.user, 'role', '')
        return role in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'CHEFE_SECRETARIA', 'SECRETARIA']

class IsProfessor(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        role = getattr(request.user, 'role', '')
        return role in ['SUPERADMIN', 'PROFESSOR', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP']

class IsFinanceiro(BasePermission):
    """Administração e Finanças, Direcção ou SuperAdmin."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        role = getattr(request.user, 'role', '')
        return role in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'FINANCEIRO']

class IsAluno(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        role = getattr(request.user, 'role', '')
        return role in ['SUPERADMIN', 'ALUNO', 'ENCARREGADO']

class TemPermissaoMatriz(BasePermission):
    """
    Verifica a permissão da ação HTTP com base na Matriz Oficial de Permissões:
    GET -> 'V' (Ver)
    POST -> 'C' (Criar)
    PUT/PATCH -> 'E' (Editar)
    Aprovação explícita -> 'A' (Aprovar)
    """
    def __init__(self, modulo):
        self.modulo = modulo

    def __call__(self):
        return self

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        role = getattr(request.user, 'role', '')
        if role == 'SUPERADMIN':
            return True

        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            acao = 'V'
        elif request.method == 'POST':
            if 'aprovar' in getattr(request, 'path', '').lower():
                acao = 'A'
            else:
                acao = 'C'
        elif request.method in ['PUT', 'PATCH']:
            if 'aprovar' in getattr(request, 'path', '').lower():
                acao = 'A'
            else:
                acao = 'E'
        elif request.method == 'DELETE':
            acao = 'E'
        else:
            acao = 'V'

        return checar_permissao_matriz(role, self.modulo, acao)
