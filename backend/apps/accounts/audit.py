import logging
from .models import LogAuditoria

logger = logging.getLogger('sige.audit')

def registrar_auditoria(usuario=None, escola=None, entidade='', acao='', objeto_id='', descricao='', antes=None, depois=None, ip='127.0.0.1'):
    """
    Regista um evento de auditoria no SIGE.
    Obrigatório para alterações em notas, pagamentos, matrículas, transferências e despesas.
    """
    try:
        user_obj = usuario if (usuario and getattr(usuario, 'is_authenticated', False)) else None
        user_nome = getattr(user_obj, 'nome', 'Sistema') if user_obj else 'Sistema'
        user_role = getattr(user_obj, 'role', '') if user_obj else ''
        escola_obj = escola or (getattr(user_obj, 'escola', None) if user_obj else None)
        
        return LogAuditoria.objects.create(
            escola=escola_obj,
            usuario=user_obj,
            usuario_nome=user_nome,
            usuario_role=user_role,
            entidade=str(entidade).upper()[:50],
            acao=str(acao).upper()[:50],
            objeto_id=str(objeto_id)[:100],
            descricao=descricao or f"{acao} em {entidade} #{objeto_id}",
            detalhes_antes=antes,
            detalhes_depois=depois,
            ip=ip or '127.0.0.1'
        )
    except Exception as e:
        logger.warning(f"Falha ao registar auditoria: {e}")
        return None
