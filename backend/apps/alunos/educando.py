"""
Educandos de uma conta (Portal do Aluno / Encarregado).

- ALUNO: o seu `aluno_id`.
- ENCARREGADO: os alunos que a escola associou à conta (`crm.VinculoEncarregado`) mais o `aluno_id` antigo, se existir.
- Outros perfis: o `aluno_id` da conta, se houver (comportamento anterior).

`aluno_alvo_id(request)` devolve o aluno do pedido. Um encarregado escolhe o educando com `?aluno_id=`; se o aluno não for
um dos seus devolve 403 e, havendo vários sem escolha, 400 ("Escolha o educando").
"""
from rest_framework.exceptions import PermissionDenied, ValidationError


def educandos_ids(user):
    ids = set()
    if getattr(user, 'aluno_id', None):
        ids.add(user.aluno_id)
    if getattr(user, 'role', '') == 'ENCARREGADO':
        from apps.crm.models import VinculoEncarregado
        ids |= set(VinculoEncarregado.objects.filter(usuario=user, escola_id=user.escola_id).values_list('aluno_id', flat=True))
    return ids


def _pedido(request):
    valor = request.query_params.get('aluno_id') or request.query_params.get('alunoId')
    if not valor and getattr(request, 'method', 'GET') != 'GET':
        valor = request.data.get('aluno_id') if hasattr(request.data, 'get') else None
    return valor


def aluno_alvo_id(request):
    user = request.user
    if getattr(user, 'role', '') != 'ENCARREGADO':
        return getattr(user, 'aluno_id', None)
    ids = educandos_ids(user)
    pedido = _pedido(request)
    if pedido:
        for i in ids:
            if str(i) == str(pedido):
                return i
        raise PermissionDenied('Esse aluno não está associado à sua conta.')
    if len(ids) == 1:
        return next(iter(ids))
    if not ids:
        return None
    raise ValidationError({'aluno_id': 'Escolha o educando.', 'escolher_educando': True})
