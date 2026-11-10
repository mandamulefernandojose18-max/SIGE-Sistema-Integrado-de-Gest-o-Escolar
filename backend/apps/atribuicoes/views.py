from datetime import date

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.disciplinas.models import Disciplina
from apps.material_escolar.views import get_tenant_escola_from_request
from apps.professores.models import Professor
from apps.turmas.models import Turma

from .models import AtividadeModelo, AtribuicaoCargo, CARGO_CHOICES, ESTADO_CHOICES, PRIORIDADE_CHOICES
from .sugestoes import SUGESTOES

PAPEIS_GESTAO = {'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'}
CARGOS = {c for c, _ in CARGO_CHOICES}
ESTADOS = {e for e, _ in ESTADO_CHOICES}
PRIORIDADES = {p for p, _ in PRIORIDADE_CHOICES}


def _role(request):
    return getattr(request.user, 'role', '')


def _e_gestao(request):
    return _role(request) in PAPEIS_GESTAO or getattr(request.user, 'is_superuser', False)


def _erro(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'message': msg}, status=code)


def _nome_prof(p):
    return f'{p.nome} {p.apelido or ""}'.strip()


def _serializar(a):
    hoje = date.today()
    return {
        'id': str(a.id),
        'ano_letivo': a.ano_letivo,
        'cargo': a.cargo,
        'cargo_nome': a.get_cargo_display(),
        'professor_id': str(a.professor_id),
        'professor_nome': _nome_prof(a.professor),
        'classe': a.classe,
        'turma_id': str(a.turma_id) if a.turma_id else None,
        'turma_nome': a.turma.nome if a.turma_id else '',
        'disciplina_id': str(a.disciplina_id) if a.disciplina_id else None,
        'disciplina_nome': a.disciplina.nome if a.disciplina_id else '',
        'titulo': a.titulo,
        'descricao': a.descricao,
        'prioridade': a.prioridade,
        'prazo': a.prazo.isoformat() if a.prazo else None,
        'atrasada': bool(a.prazo and a.prazo < hoje and a.estado != 'CONCLUIDA'),
        'estado': a.estado,
        'nota_responsavel': a.nota_responsavel,
        'atribuido_por': a.atribuido_por,
        'concluida_em': a.concluida_em.isoformat() if a.concluida_em else None,
        'created_at': a.created_at.isoformat(),
    }


def _base_qs(request):
    escola = get_tenant_escola_from_request(request)
    if not escola:
        return AtribuicaoCargo.objects.none(), None
    qs = AtribuicaoCargo.objects.filter(escola=escola).select_related('professor', 'turma', 'disciplina')
    return qs, escola


def _meu_professor_id(request):
    return getattr(request.user, 'professor_id', None)


class SugestoesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = get_tenant_escola_from_request(request)
        cargo = request.query_params.get('cargo')
        if cargo not in CARGOS:
            return _erro('Cargo inválido.')
        dados = [{'titulo': t, 'descricao': d, 'origem': 'SUGESTAO'} for t, d in SUGESTOES[cargo]]
        proprias = AtividadeModelo.objects.filter(escola=escola, cargo=cargo).order_by('titulo') if escola else []
        dados += [{'id': str(m.id), 'titulo': m.titulo, 'descricao': m.descricao, 'origem': 'ESCOLA'} for m in proprias]
        return Response({'success': True, 'data': dados})


class ModeloDetalheView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not _e_gestao(request):
            return _erro('Sem permissão.', status.HTTP_403_FORBIDDEN)
        escola = get_tenant_escola_from_request(request)
        m = AtividadeModelo.objects.filter(id=pk, escola=escola).first() if escola else None
        if not m:
            return _erro('Actividade não encontrada.', status.HTTP_404_NOT_FOUND)
        m.delete()
        return Response({'success': True})


class AtribuicoesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs, escola = _base_qs(request)
        if not _e_gestao(request):
            pid = _meu_professor_id(request)
            qs = qs.filter(professor_id=pid) if pid else qs.none()
        p = request.query_params
        if p.get('ano'):
            qs = qs.filter(ano_letivo=p['ano'])
        if p.get('cargo') in CARGOS:
            qs = qs.filter(cargo=p['cargo'])
        if p.get('classe'):
            qs = qs.filter(classe=p['classe'])
        if p.get('professor_id'):
            qs = qs.filter(professor_id=p['professor_id'])
        if p.get('estado') in ESTADOS:
            qs = qs.filter(estado=p['estado'])
        if p.get('search'):
            s = p['search']
            qs = qs.filter(Q(titulo__icontains=s) | Q(professor__nome__icontains=s) | Q(professor__apelido__icontains=s))
        total = qs.count()
        try:
            page = max(int(p.get('page', 1)), 1)
            size = min(max(int(p.get('page_size', 10)), 1), 50)
        except ValueError:
            page, size = 1, 10
        itens = qs.order_by('estado', 'prazo', '-created_at')[(page - 1) * size: page * size]
        return Response({'success': True, 'data': [_serializar(a) for a in itens],
                         'total': total, 'page': page, 'page_size': size})

    def post(self, request):
        if not _e_gestao(request):
            return _erro('Só a Direcção Pedagógica pode atribuir actividades.', status.HTTP_403_FORBIDDEN)
        escola = get_tenant_escola_from_request(request)
        if not escola:
            return _erro('Instituição de ensino não identificada.')
        d = request.data
        cargo = d.get('cargo')
        if cargo not in CARGOS:
            return _erro('Seleccione o cargo.')
        prof = Professor.objects.filter(id=d.get('professor_id'), escola=escola).first() if d.get('professor_id') else None
        if not prof:
            return _erro('Seleccione o professor responsável.')
        turma = disciplina = None
        classe = (d.get('classe') or '').strip()
        ano = str(d.get('ano_letivo') or '').strip()
        if cargo == 'DIRECTOR_TURMA':
            turma = Turma.objects.filter(id=d.get('turma_id'), escola=escola).first() if d.get('turma_id') else None
            if not turma:
                return _erro('Seleccione a turma do Director de Turma.')
            classe, ano = turma.grau_ano, ano or turma.ano_letivo
        elif cargo == 'DELEGADO_DISCIPLINA':
            disciplina = Disciplina.objects.filter(id=d.get('disciplina_id'), escola=escola).first() if d.get('disciplina_id') else None
            if not disciplina:
                return _erro('Seleccione a disciplina do Delegado.')
            classe, ano = disciplina.classe, ano or disciplina.ano_letivo
        elif not classe:
            return _erro('Seleccione a classe do Director de Classe.')
        if not ano:
            return _erro('Indique o ano lectivo.')

        atividades = d.get('atividades')
        if not isinstance(atividades, list) or not atividades:
            return _erro('Escolha ou escreva pelo menos uma actividade.')
        quem = getattr(request.user, 'nome', None) or getattr(request.user, 'email', '') or 'Direcção Pedagógica'
        criadas = []
        for at in atividades:
            titulo = str((at or {}).get('titulo') or '').strip()
            if not titulo:
                continue
            prazo = parse_date(str(at.get('prazo'))) if at.get('prazo') else None
            prioridade = at.get('prioridade') if at.get('prioridade') in PRIORIDADES else 'NORMAL'
            obj = AtribuicaoCargo.objects.create(
                escola=escola, ano_letivo=ano, cargo=cargo, professor=prof, classe=classe, turma=turma,
                disciplina=disciplina, titulo=titulo[:255], descricao=str(at.get('descricao') or '').strip(),
                prioridade=prioridade, prazo=prazo, atribuido_por=quem,
            )
            criadas.append(obj)
            if at.get('guardar_modelo'):
                AtividadeModelo.objects.get_or_create(
                    escola=escola, cargo=cargo, titulo=titulo[:255],
                    defaults={'descricao': obj.descricao, 'criado_por': quem},
                )
        if not criadas:
            return _erro('Escolha ou escreva pelo menos uma actividade.')
        return Response({'success': True, 'data': [_serializar(a) for a in criadas]}, status=status.HTTP_201_CREATED)


class AtribuicaoDetalheView(APIView):
    permission_classes = [IsAuthenticated]

    def _obter(self, request, pk):
        qs, _ = _base_qs(request)
        return qs.filter(id=pk).first()

    def patch(self, request, pk):
        a = self._obter(request, pk)
        if not a:
            return _erro('Actividade não encontrada.', status.HTTP_404_NOT_FOUND)
        gestao = _e_gestao(request)
        if not gestao and str(a.professor_id) != str(_meu_professor_id(request)):
            return _erro('Sem permissão.', status.HTTP_403_FORBIDDEN)
        d = request.data
        if d.get('estado') in ESTADOS:
            a.estado = d['estado']
            a.concluida_em = timezone.now() if a.estado == 'CONCLUIDA' else None
        if 'nota_responsavel' in d:
            a.nota_responsavel = str(d.get('nota_responsavel') or '')
        if gestao:
            if d.get('titulo') is not None and str(d['titulo']).strip():
                a.titulo = str(d['titulo']).strip()[:255]
            if 'descricao' in d:
                a.descricao = str(d.get('descricao') or '')
            if d.get('prioridade') in PRIORIDADES:
                a.prioridade = d['prioridade']
            if 'prazo' in d:
                a.prazo = parse_date(str(d['prazo'])) if d.get('prazo') else None
        a.save()
        return Response({'success': True, 'data': _serializar(a)})

    def delete(self, request, pk):
        if not _e_gestao(request):
            return _erro('Sem permissão.', status.HTTP_403_FORBIDDEN)
        a = self._obter(request, pk)
        if not a:
            return _erro('Actividade não encontrada.', status.HTTP_404_NOT_FOUND)
        a.delete()
        return Response({'success': True, 'message': 'Actividade removida.'})
