import re

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils.tenant import get_tenant_escola
from . import alertas, capacidades, engine
from .models import ConsultaAssistente

TAMANHO_MAX = 500
PAGINA_VALIDA = re.compile(r'^[a-z0-9\-]{1,60}$')
PAGINA_VALIDA_ID = re.compile(r'^[a-z0-9_]{1,60}$')


def _pagina(request):
    p = (request.data.get('pagina') if hasattr(request, 'data') else None) or request.query_params.get('pagina') or ''
    p = str(p).strip().lower()
    return p if PAGINA_VALIDA.match(p) else ''


def _escola(request):
    """Escola do pedido. O Super Admin sem escola em inspecção fica em modo plataforma (devolve None); os outros perfis precisam de escola."""
    escola = get_tenant_escola(request)
    if not escola and getattr(request.user, 'role', '') != 'SUPERADMIN':
        raise ValidationError({'escola': 'Nenhuma escola identificada.'})
    return escola


class PerguntarView(APIView):
    """POST /assistente/perguntar/ {pergunta, aluno_id?, pagina?} — nível 0, só leitura, isolado por escola."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        escola = _escola(request)
        pergunta = (request.data.get('pergunta') or '').strip()
        if not pergunta:
            raise ValidationError({'pergunta': 'Escreva a sua pergunta.'})
        if len(pergunta) > TAMANHO_MAX:
            raise ValidationError({'pergunta': f'A pergunta não pode exceder {TAMANHO_MAX} caracteres.'})
        aluno_id = request.data.get('aluno_id') or None
        pagina = _pagina(request)
        anterior = str(request.data.get('anterior') or '')
        anterior = anterior if PAGINA_VALIDA_ID.match(anterior) else None
        try:
            intencao, aluno, resposta = engine.responder(request.user, escola, pergunta, aluno_id, pagina or None, anterior)
        except (ValueError, TypeError, DjangoValidationError):
            raise ValidationError({'aluno_id': 'Identificador de aluno inválido.'})
        consulta = ConsultaAssistente.objects.create(escola=escola, usuario=request.user, aluno=aluno, pergunta=pergunta,
                                                     intencao=intencao, pagina=pagina)
        resposta['consulta_id'] = str(consulta.id)
        return Response(resposta)


class FeedbackView(APIView):
    """POST /assistente/feedback/ {consulta_id, util} — "foi útil?" (só o próprio utilizador, na sua escola)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        escola = _escola(request)
        util = request.data.get('util')
        if not isinstance(util, bool):
            raise ValidationError({'util': 'Indique true ou false.'})
        try:
            n = ConsultaAssistente.objects.filter(id=request.data.get('consulta_id'), escola=escola, usuario=request.user).update(util=util)   # só o autor
        except (ValueError, TypeError, DjangoValidationError):
            raise ValidationError({'consulta_id': 'Identificador inválido.'})
        if not n:
            raise ValidationError({'consulta_id': 'Consulta não encontrada.'})
        return Response({'success': True})


ACCAO_SUGERIDA = {
    'sem resposta': 'Criar capacidade ou acrescentar palavras-chave (capacidades.py / guias.py)',
    'fora do painel': 'Confirmar que pertence mesmo a outro painel; se for do painel, ligar o módulo em modulos.py',
    'não útil': 'Rever a resposta e a escolha da capacidade',
}


def _celula_csv(valor):
    """Texto de utilizadores nunca pode ser interpretado como fórmula no Excel (=, +, -, @ no início)."""
    texto = str(valor).replace('\r', ' ').replace('\n', ' ')
    return "'" + texto if texto[:1] in ('=', '+', '-', '@', '\t') else texto


def _csv_relatorio(grupos, dias, da_escola):
    import csv
    from django.http import HttpResponse
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="perguntas-a-melhorar-{dias}d.csv"'
    resp.write('﻿')      # Excel abre em UTF-8 com acentos
    w = csv.writer(resp, delimiter=';')
    cabecalho = ['Pergunta', 'Vezes', 'Motivos', 'Acção sugerida', 'Decisão (preencher)', 'Notas']
    if not da_escola:
        cabecalho.insert(3, 'Escolas')
    w.writerow(cabecalho)
    for g in grupos:
        motivos = sorted(g['motivos'])
        linha = [_celula_csv(g['pergunta']), g['vezes'], ', '.join(motivos), '; '.join(ACCAO_SUGERIDA[m] for m in motivos if m in ACCAO_SUGERIDA), '', '']
        if not da_escola:
            linha.insert(3, _celula_csv(', '.join(sorted(g['escolas']))))
        w.writerow(linha)
    return resp


class RelatorioView(APIView):
    """GET /assistente/relatorio/?dias=30 — onde o assistente falha: perguntas sem resposta, fora do painel ou marcadas "não útil".

    Super Admin: todas as escolas (ou a escola em inspecção). Direcção (Administrador/Director): só a sua escola. Outros perfis: 403.
    Não devolve respostas nem dados de alunos; apenas o texto das perguntas (cortado) e contagens.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import datetime
        from django.db.models import Count, Q
        from django.utils import timezone
        from rest_framework.exceptions import PermissionDenied
        role = getattr(request.user, 'role', '')
        if role not in ('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'):
            raise PermissionDenied('Apenas o Super Admin e a Direcção da escola podem ver este relatório.')
        try:
            dias = min(max(int(request.query_params.get('dias', 30)), 1), 180)
        except ValueError:
            dias = 30
        escola = get_tenant_escola(request)
        qs = ConsultaAssistente.objects.filter(created_at__gte=timezone.now() - datetime.timedelta(days=dias))
        if escola:
            qs = qs.filter(escola=escola)
        elif role != 'SUPERADMIN':
            qs = qs.none()
        total = qs.count()
        base = {'periodo_dias': dias, 'total': total, 'ambito': 'escola' if escola else 'plataforma'}
        if not total:
            if request.query_params.get('formato') == 'csv':
                return _csv_relatorio([], dias, bool(escola))
            return Response({**base, 'taxas': {}, 'por_intencao': [], 'por_perfil': [], 'perguntas_a_melhorar': []})
        pct = lambda n: round(100 * n / total, 1)
        sem_resp = qs.filter(intencao='desconhecida').count()
        fora = qs.filter(intencao='fora_do_painel').count()
        uteis, nao_uteis = qs.filter(util=True).count(), qs.filter(util=False).count()
        taxas = {'sem_resposta_pct': pct(sem_resp), 'fora_do_painel_pct': pct(fora), 'util_pct': pct(uteis), 'nao_util_pct': pct(nao_uteis),
                 'com_feedback': uteis + nao_uteis}
        linhas = qs.filter(Q(intencao__in=('desconhecida', 'fora_do_painel')) | Q(util=False)).values('pergunta', 'intencao', 'util', 'escola__nome')[:1000]
        grupos = {}
        for r in linhas:
            chave = capacidades.normalizar(r['pergunta']).strip()
            g = grupos.setdefault(chave, {'pergunta': r['pergunta'][:120], 'vezes': 0, 'motivos': set(), 'intencao': r['intencao'], 'escolas': set()})
            g['vezes'] += 1
            g['motivos'].add('sem resposta' if r['intencao'] == 'desconhecida' else ('fora do painel' if r['intencao'] == 'fora_do_painel' else 'não útil'))
            if r['util'] is False:
                g['motivos'].add('não útil')
            if r['escola__nome'] and not escola:
                g['escolas'].add(r['escola__nome'])
        melhorar = sorted(grupos.values(), key=lambda g: -g['vezes'])[:25]
        for g in melhorar:
            g['motivos'], g['escolas'] = sorted(g['motivos']), sorted(g['escolas'])[:3]
        if request.query_params.get('formato') == 'csv':
            return _csv_relatorio(sorted(grupos.values(), key=lambda g: -g['vezes'])[:200], dias, bool(escola))
        return Response({**base, 'taxas': taxas,
                         'por_intencao': list(qs.values('intencao').annotate(n=Count('id')).order_by('-n')[:12]),
                         'por_perfil': list(qs.values('usuario__role').annotate(n=Count('id')).order_by('-n')[:10]),
                         'perguntas_a_melhorar': melhorar})


class AlertasView(APIView):
    """GET /assistente/alertas/ — o que merece atenção do perfil, em dados reais (vazio se nada a assinalar)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = get_tenant_escola(request)
        if not escola and getattr(request.user, 'role', '') != 'SUPERADMIN':
            return Response({'alertas': [], 'total': 0, 'urgentes': 0})
        lista = alertas.alertas_do_utilizador(request.user, escola)
        return Response({'alertas': lista, 'total': len(lista), 'urgentes': sum(1 for a in lista if a['nivel'] == 'alta')})


class EducandosView(APIView):
    """GET /assistente/educandos/ — educandos associados à conta de Encarregado (vazio para os outros perfis)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = _escola(request)
        if getattr(request.user, 'role', '') != 'ENCARREGADO':
            return Response({'educandos': []})
        return Response({'educandos': [{'id': str(a.id), 'nome': a.nome, 'matricula': a.matricula, 'classe': a.classe, 'turma': a.turma.nome if a.turma else None}
                                       for a in engine.educandos_do_encarregado(request.user, escola)]})


class SugestoesView(APIView):
    """GET /assistente/sugestoes/?pagina= — perguntas sugeridas para o perfil e a página actual."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'sugestoes': capacidades.sugestoes(getattr(request.user, 'role', ''), _pagina(request))})
