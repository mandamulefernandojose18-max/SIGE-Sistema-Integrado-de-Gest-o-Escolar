from apps.tenants.models import Escola

def get_tenant_escola(request):
    """
    Função central e inquebrável de isolamento Multi-Tenant do SIGE:
    NENHUM cadastro, documento, nota, turma, publicação ou dado de uma escola
    pode reflectir noutra instituição ou escola.
    
    1. Se for SUPERADMIN:
       - Respeita o tenant ativo indicado via header 'X-Tenant-ID' ou query/data 'escola_id'/'tenant_id'.
       - Fallback para request.tenant ou request.user.escola (se houver).
    2. Utilizadores normais vinculados a uma escola (ADMIN_ESCOLA, DAP, PROFESSOR, ALUNO, etc.):
       - Ficam estritamente restritos à sua própria escola (request.tenant ou request.user.escola).
       - NUNCA veem nem gravam dados de outra instituição.
    """
    if not request:
        return None

    user = getattr(request, 'user', None)
    is_super = getattr(user, 'role', '') == 'SUPERADMIN'

    if is_super:
        tenant_id = (
            request.headers.get('X-Tenant-ID')
            or (hasattr(request, 'query_params') and (request.query_params.get('escola_id') or request.query_params.get('tenant_id')))
            or (hasattr(request, 'GET') and (request.GET.get('escola_id') or request.GET.get('tenant_id')))
            or (isinstance(getattr(request, 'data', None), dict) and (request.data.get('escola_id') or request.data.get('escola')))
        )
        if tenant_id:
            return Escola.objects.filter(id=tenant_id).first()
        return getattr(request, 'tenant', None) or getattr(user, 'escola', None)

    escola = getattr(request, 'tenant', None)
    if not escola and user and getattr(user, 'is_authenticated', False):
        escola = getattr(user, 'escola', None)

    if not escola:
        tenant_id = (
            request.headers.get('X-Tenant-ID')
            or (hasattr(request, 'query_params') and (request.query_params.get('escola_id') or request.query_params.get('tenant_id')))
            or (hasattr(request, 'GET') and (request.GET.get('escola_id') or request.GET.get('tenant_id')))
            or (isinstance(getattr(request, 'data', None), dict) and (request.data.get('escola_id') or request.data.get('escola')))
        )
        if tenant_id:
            escola = Escola.objects.filter(id=tenant_id).first()

    return escola
