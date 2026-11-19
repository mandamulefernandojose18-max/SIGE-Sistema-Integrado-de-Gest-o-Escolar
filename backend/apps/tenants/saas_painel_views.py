"""Endpoints de apoio ao painel SuperAdmin: auditoria de acessos paginada e opções de escolas."""
import uuid

from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import LogAcesso
from common.permissions.rbac import IsSuperAdmin

from .models import Escola


def _inteiro(valor, padrao, minimo, maximo):
    try:
        return max(minimo, min(int(valor), maximo))
    except (TypeError, ValueError):
        return padrao


class SaasLogsAcessoView(APIView):
    """Logs de acesso de todas as escolas, paginados no servidor (filtros: escola, tipo, pesquisa)."""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        p = request.query_params
        qs = LogAcesso.objects.select_related('usuario', 'escola').order_by('-created_at')

        escola_id = (p.get('escola') or '').strip()
        if escola_id:
            try:
                qs = qs.filter(escola_id=uuid.UUID(escola_id))
            except ValueError:
                return Response({'success': False, 'message': 'Escola inválida.'}, status=status.HTTP_400_BAD_REQUEST)
        tipo = (p.get('tipo') or '').strip()
        if tipo:
            qs = qs.filter(tipo=tipo)
        termo = (p.get('q') or '').strip()
        if termo:
            qs = qs.filter(Q(usuario__nome__icontains=termo) | Q(usuario__email__icontains=termo)
                           | Q(usuario__codigo_acesso__icontains=termo))

        tamanho = _inteiro(p.get('tamanho'), 25, 1, 100)
        total = qs.count()
        paginas = max(1, -(-total // tamanho))
        pagina = min(_inteiro(p.get('pagina'), 1, 1, 10 ** 9), paginas)
        itens = qs[(pagina - 1) * tamanho: pagina * tamanho]

        data = [{
            'id': str(l.id),
            'createdAt': l.created_at.isoformat(),
            'usuario': {'nome': l.usuario.nome or l.usuario.email} if l.usuario else None,
            'escola_nome': l.escola.nome if l.escola else None,
            'ip': l.ip,
            'user_agent': l.user_agent or '',
            'tipo': l.tipo,
        } for l in itens]
        return Response({'success': True, 'data': data,
                         'meta': {'total': total, 'pagina': pagina, 'paginas': paginas, 'tamanho': tamanho}})


class SaasEscolasOpcoesView(APIView):
    """Lista leve (id, nome, código) para o filtro de escola nas páginas do SuperAdmin."""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        escolas = Escola.objects.order_by('nome').values('id', 'nome', 'codigo_escola')
        return Response({'success': True, 'data': [
            {'id': str(e['id']), 'nome': e['nome'], 'codigo': e['codigo_escola'] or ''} for e in escolas]})
