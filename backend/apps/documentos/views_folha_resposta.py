"""
SIGE — API da Folha de Resposta Personalizada.

  GET  /api/v1/documentos/folha-resposta/contexto/   escola, ano, classes→turmas, tipos de avaliação
  GET  /api/v1/documentos/folha-resposta/alunos/     alunos activos de uma turma (filtro em cascata)
  POST /api/v1/documentos/folha-resposta/gerar/      PDF ou Excel: um aluno, a turma, a classe ou em branco

Tudo isolado por escola (tenant). Só dados reais: sem alunos reais não há folhas personalizadas.
"""
from django.http import HttpResponse
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alunos.models import Aluno
from apps.disciplinas.models import Disciplina
from apps.turmas.models import Turma
from common.utils.tenant import get_tenant_escola

from .services import folha_resposta_service as fr
from .services.pdf_service import DocumentoSemLogoError
from .services.xlsx_seguro import XlsxInvalidoError
from .views import (
    _definir_content_disposition,
    _obter_aluno_e_escola,
    _obter_turma_e_escola,
    _registrar_log_impressao,
    _safe_ascii_filename,
)

ROLES_BLOQUEADAS = {'ALUNO', 'ENCARREGADO'}
XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class PodeEmitirFolhas(BasePermission):
    message = 'O seu perfil não pode emitir folhas de resposta.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and getattr(u, 'role', '') not in ROLES_BLOQUEADAS)


def _escola_ou_erro(request):
    escola = get_tenant_escola(request)
    if not escola:
        raise PermissionDenied('Nenhuma escola associada ao pedido.')
    return escola


def _alunos_da_turma(turma):
    """Alunos activos da turma por ordem alfabética, com o nº de ordem real da turma."""
    qs = Aluno.objects.filter(turma=turma, status='ATIVO').select_related('turma').order_by('nome', 'apelido')
    return list(qs)


class FolhaRespostaContextoView(APIView):
    permission_classes = [IsAuthenticated, PodeEmitirFolhas]

    def get(self, request):
        escola = _escola_ou_erro(request)
        ano = request.query_params.get('ano') or escola.ano_letivo_ativo
        turmas = Turma.objects.filter(escola=escola, ano_letivo=ano).order_by('grau_ano', 'nome')
        contagem = {}
        for t_id in Aluno.objects.filter(escola=escola, status='ATIVO', turma__in=turmas).values_list('turma_id', flat=True):
            contagem[t_id] = contagem.get(t_id, 0) + 1
        classes = {}
        for t in turmas:
            classes.setdefault(t.grau_ano, []).append({
                'id': str(t.id), 'nome': t.nome, 'area': t.area, 'turno': t.turno,
                'alunos': contagem.get(t.id, 0),
            })
        disciplinas = {}
        for d in Disciplina.objects.filter(escola=escola, ano_letivo=ano).order_by('nome'):
            lista = disciplinas.setdefault(d.classe, [])
            if not any(x['nome'] == d.nome and x['area'] == d.area for x in lista):
                lista.append({'nome': d.nome, 'area': d.area})
        logo = fr.resolver_logo_documento_escola(escola)[0]
        return Response({
            'escola': {
                'nome': escola.nome, 'codigo': escola.codigo_escola or '', 'provincia': escola.provincia,
                'distrito': escola.distrito, 'ano_letivo': escola.ano_letivo_ativo,
                'trimestre': escola.trimestre_ativo, 'logotipo_disponivel': bool(logo),
            },
            'ano_letivo': ano,
            'tipos_avaliacao': [{'codigo': c, 'rotulo': r} for c, r in fr.TIPOS_AVALIACAO],
            'classes': [{'classe': k, 'turmas': v, 'total_alunos': sum(x['alunos'] for x in v)} for k, v in classes.items()],
            'disciplinas_por_classe': disciplinas,
            'limites': {'max_perguntas': fr.MAX_PERGUNTAS, 'max_folhas': fr.MAX_FOLHAS,
                        'max_folhas_branco': fr.MAX_FOLHAS_BRANCO},
        })


class FolhaRespostaAlunosView(APIView):
    permission_classes = [IsAuthenticated, PodeEmitirFolhas]

    def get(self, request):
        turma_id = request.query_params.get('turma_id')
        if not turma_id:
            return Response({'detail': 'Indique a turma.'}, status=400)
        turma, _ = _obter_turma_e_escola(request, turma_id)
        alunos = _alunos_da_turma(turma)
        return Response({'turma': turma.nome, 'classe': turma.grau_ano, 'alunos': [
            {'id': str(a.id), 'numero': i, 'apelido': a.apelido or '', 'nome': a.nome, 'codigo': a.matricula}
            for i, a in enumerate(alunos, start=1)
        ]})


class FolhaRespostaGerarView(APIView):
    permission_classes = [IsAuthenticated, PodeEmitirFolhas]

    def post(self, request):
        dados = request.data if isinstance(request.data, dict) else {}
        escopo = str(dados.get('escopo') or '').lower()
        formato = str(dados.get('formato') or 'pdf').lower()
        if formato not in ('pdf', 'xlsx'):
            return Response({'detail': 'Formato inválido (pdf ou xlsx).'}, status=400)
        if escopo not in ('aluno', 'turma', 'classe', 'branco'):
            return Response({'detail': 'Âmbito inválido (aluno, turma, classe ou branco).'}, status=400)

        escola = _escola_ou_erro(request)
        ano = str(dados.get('ano_letivo') or escola.ano_letivo_ativo)
        esc = fr.montar_dados_escola(escola)
        alunos, etiqueta, classe_ref, area_ref = [], '', '', ''

        if escopo == 'aluno':
            aluno, escola = _obter_aluno_e_escola(request, dados.get('aluno_id'))
            esc = fr.montar_dados_escola(escola)
            numero = None
            if aluno.turma_id:
                ordem = _alunos_da_turma(aluno.turma)
                numero = next((i for i, a in enumerate(ordem, start=1) if a.id == aluno.id), None)
            alunos = [fr.montar_dados_aluno(aluno, numero)]
            etiqueta = f'{aluno.apelido or ""} {aluno.nome}'.strip()
            classe_ref = alunos[0]['classe']
            area_ref = aluno.turma.area if aluno.turma_id else (aluno.area or '')
        elif escopo == 'turma':
            turma, escola = _obter_turma_e_escola(request, dados.get('turma_id'))
            esc = fr.montar_dados_escola(escola)
            alunos = [fr.montar_dados_aluno(a, i) for i, a in enumerate(_alunos_da_turma(turma), start=1)]
            etiqueta = f'{turma.grau_ano} {turma.nome}'
            classe_ref, area_ref = turma.grau_ano, turma.area
        elif escopo == 'classe':
            classe_ref = str(dados.get('classe') or '').strip()
            if not classe_ref:
                return Response({'detail': 'Indique a classe.'}, status=400)
            area_ref = str(dados.get('area') or '').strip()
            turmas_qs = Turma.objects.filter(escola=escola, ano_letivo=ano, grau_ano=classe_ref)
            if area_ref:
                turmas_qs = turmas_qs.filter(area=area_ref)
            for turma in turmas_qs.order_by('nome'):
                alunos += [fr.montar_dados_aluno(a, i) for i, a in enumerate(_alunos_da_turma(turma), start=1)]
            etiqueta = f'{classe_ref} {area_ref}'.strip()
        else:
            classe_ref = str(dados.get('classe') or '').strip()
            try:
                copias = int(dados.get('copias') or 0)
            except (TypeError, ValueError):
                copias = 0
            if copias < 1 or copias > fr.MAX_FOLHAS_BRANCO:
                return Response({'detail': f'Indique entre 1 e {fr.MAX_FOLHAS_BRANCO} folhas em branco.'}, status=400)
            alunos = [None] * copias
            etiqueta = 'em branco'

        if not alunos:
            return Response({'detail': 'Não existem alunos activos neste âmbito: não há folhas personalizadas a gerar.'}, status=404)

        cfg_in = dict(dados.get('config') or {})
        if classe_ref:
            discs = Disciplina.objects.filter(escola=escola, ano_letivo=ano, classe=classe_ref)
            if area_ref:
                discs = discs.filter(area__in=['Geral', area_ref])
            cfg_in['disciplinas_classe'] = list(discs.order_by('nome').values_list('nome', flat=True).distinct())
        try:
            config = fr.normalizar_config(cfg_in, esc)
            if formato == 'pdf':
                conteudo, total = fr.gerar_folhas_pdf(esc, alunos, config, ano)
            else:
                conteudo, total = fr.gerar_folhas_xlsx(esc, alunos, config, ano)
        except fr.ConfigFolhaInvalida as e:
            return Response({'detail': str(e)}, status=400)
        except DocumentoSemLogoError as e:
            return Response({'detail': str(e)}, status=409)
        except XlsxInvalidoError as e:
            return Response({'detail': f'Não foi possível gerar o Excel: {e}'}, status=500)

        _registrar_log_impressao(
            escola, request, 'FOLHA_RESPOSTA',
            f"Folha de resposta ({formato.upper()}) · {config['tipo_rotulo']} · {config['disciplina']} · {etiqueta} · {total} folha(s)",
        )
        nome = _safe_ascii_filename(f"Folha_Resposta_{config['disciplina']}_{config['tipo_rotulo']}_{etiqueta}_{ano}") + f'.{formato}'
        resp = HttpResponse(conteudo, content_type='application/pdf' if formato == 'pdf' else XLSX_MIME)
        resp['X-Total-Folhas'] = str(total)
        resp['Access-Control-Expose-Headers'] = 'Content-Disposition, X-Total-Folhas'
        return _definir_content_disposition(resp, nome)
