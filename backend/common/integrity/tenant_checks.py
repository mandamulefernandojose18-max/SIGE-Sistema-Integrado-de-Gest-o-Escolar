"""
Verificações de Integridade Referencial, Isolamento Multi-Tenant e Imutabilidade.
"""
from .exceptions import CrossTenantViolation, ImmutableRecordViolation

def validar_integridade_tenant(master_instance, **related_objects):
    """
    Garante que todos os objetos relacionados pertençam estritamente ao mesmo Tenant (Escola).
    Impede vazamento de dados ou vinculação acidental entre escolas diferentes.
    """
    if hasattr(master_instance, 'escola_id'):
        master_escola_id = master_instance.escola_id
    elif hasattr(master_instance, 'pk') and master_instance.__class__.__name__ == 'Escola':
        master_escola_id = master_instance.pk
    else:
        master_escola_id = getattr(master_instance, 'escola', None)
        if hasattr(master_escola_id, 'pk'):
            master_escola_id = master_escola_id.pk

    if not master_escola_id:
        return

    for rel_name, rel_obj in related_objects.items():
        if rel_obj is None:
            continue

        if hasattr(rel_obj, 'escola_id'):
            rel_escola_id = rel_obj.escola_id
        elif hasattr(rel_obj, 'pk') and rel_obj.__class__.__name__ == 'Escola':
            rel_escola_id = rel_obj.pk
        else:
            rel_escola_id = getattr(rel_obj, 'escola', None)
            if hasattr(rel_escola_id, 'pk'):
                rel_escola_id = rel_escola_id.pk

        if rel_escola_id and str(master_escola_id) != str(rel_escola_id):
            raise CrossTenantViolation(
                f"Violação de integridade multi-tenant: O objeto relacionado '{rel_name}' pertence à "
                f"escola '{rel_escola_id}', divergindo da escola principal '{master_escola_id}'."
            )

def verificar_pauta_permite_edicao_nota(escola, turma, disciplina, periodo, professor=None):
    """
    Garante a regra de imutabilidade acadêmica:
    Quando uma Pauta é FECHADA (Homologada), as notas não podem ser alteradas,
    a menos que exista uma PermissaoEdicaoNotas explícita e ativa.
    """
    from apps.pautas.models import Pauta
    from apps.notas.models import PermissaoEdicaoNotas

    if not escola or not turma or not periodo:
        return

    pauta_fechada = Pauta.objects.filter(
        escola=escola,
        turma=turma,
        periodo=periodo,
        status='FECHADA'
    ).exists()

    if pauta_fechada:
        perm_qs = PermissaoEdicaoNotas.objects.filter(
            escola=escola,
            turma=turma,
            disciplina=disciplina,
            periodo=periodo,
            ativa=True
        )
        if professor:
            perm_qs = perm_qs.filter(professor=professor)

        if not perm_qs.exists():
            raise ImmutableRecordViolation(
                f"A pauta da turma '{getattr(turma, 'nome', turma)}' referente ao período '{periodo}' "
                f"está homologada e FECHADA. Alterações de notas requerem autorização pedagógica expressa."
            )
