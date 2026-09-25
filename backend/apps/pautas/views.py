from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
import json

from .models import Pauta
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.alunos.models import Aluno
from apps.notas.models import Nota
from common.utils.avaliacoes_mocambique import avaliar_aprovacao_pauta
from apps.documentos.services.pdf_service import gerar_pauta_pdf
from apps.documentos.services.excel_service import gerar_pauta_xlsx
from apps.documentos.services.docx_service import gerar_pauta_docx

def consolidar_dados_turma(turma, periodo, ano_letivo):
    disciplinas = list(Disciplina.objects.filter(escola=turma.escola).order_by('codigo'))
    alunos = list(Aluno.objects.filter(turma=turma, status='ATIVO').order_by('nome'))
    notas_qs = Nota.objects.filter(turma=turma, periodo=periodo)

    notas_map = {}
    for n in notas_qs:
        notas_map[(n.aluno_id, n.disciplina_id)] = n

    dados_alunos = []
    for aluno in alunos:
        aluno_notas = {}
        notas_disciplinas_calc = []
        for d in disciplinas:
            nota_obj = notas_map.get((aluno.id, d.id))
            if nota_obj:
                aluno_notas[str(d.id)] = {
                    'media_final': nota_obj.media_final,
                    'resultado': nota_obj.resultado,
                    'anotacao': nota_obj.anotacao
                }
                notas_disciplinas_calc.append({'disciplina': d.nome, 'notaFinal': nota_obj.media_final})
            else:
                aluno_notas[str(d.id)] = {'media_final': 0, 'resultado': 'Sem Nota', 'anotacao': None}

        avaliacao = avaliar_aprovacao_pauta(notas_disciplinas_calc, turma.grau_ano)

        dados_alunos.append({
            'id': str(aluno.id),
            'matricula': aluno.matricula,
            'nome': aluno.nome,
            'notas': aluno_notas,
            'media_geral': avaliacao['mediaGeral'],
            'total_negativas': avaliacao['totalNegativas'],
            'resultado': avaliacao['resultado'],
            'siglaResultado': avaliacao['siglaResultado'],
            'motivo': avaliacao['motivo']
        })

    return {
        'turma': turma,
        'disciplinas': disciplinas,
        'dados_alunos': dados_alunos
    }

class PautaGerarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        turma_id = request.data.get('turma_id')
        periodo = request.data.get('periodo', '1_TRIMESTRE')
        ano_letivo = request.data.get('ano_letivo', '2026')

        escola = request.tenant or request.user.escola
        turma = get_object_or_404(Turma, id=turma_id, escola=escola)

        pauta, _ = Pauta.objects.update_or_create(
            escola=escola,
            turma=turma,
            periodo=periodo,
            ano_letivo=ano_letivo,
            defaults={'status': 'EM_CONSOLIDACAO'}
        )

        dados = consolidar_dados_turma(turma, periodo, ano_letivo)

        return Response({
            'success': True,
            'message': f"Pauta da turma {turma.nome} consolidada com sucesso!",
            'pautaId': str(pauta.id),
            'totalAlunos': len(dados['dados_alunos'])
        })

class PautaCompletaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, turma_id):
        escola = request.tenant or request.user.escola
        turma = get_object_or_404(Turma, id=turma_id, escola=escola)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano_letivo = request.query_params.get('anoLetivo', '2026')

        dados = consolidar_dados_turma(turma, periodo, ano_letivo)

        disc_data = [{'id': str(d.id), 'nome': d.nome, 'codigo': d.codigo} for d in dados['disciplinas']]

        return Response({
            'success': True,
            'turma': {'id': str(turma.id), 'nome': turma.nome, 'grau': turma.grau_ano, 'turno': turma.turno},
            'periodo': periodo,
            'anoLetivo': ano_letivo,
            'disciplinas': disc_data,
            'alunos': dados['dados_alunos']
        })

class PautaPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, turma_id):
        escola = request.tenant or request.user.escola
        turma = get_object_or_404(Turma, id=turma_id, escola=escola)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')

        dados = consolidar_dados_turma(turma, periodo, ano)
        pdf_bytes = gerar_pauta_pdf(turma, escola, periodo, ano, dados['dados_alunos'], dados['disciplinas'])

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Pauta_{turma.nome}_{ano}.pdf"'
        return response

class PautaXLSXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, turma_id):
        escola = request.tenant or request.user.escola
        turma = get_object_or_404(Turma, id=turma_id, escola=escola)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')

        dados = consolidar_dados_turma(turma, periodo, ano)
        xlsx_bytes = gerar_pauta_xlsx(turma, escola, periodo, ano, dados['dados_alunos'], dados['disciplinas'])

        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Pauta_{turma.nome}_{ano}.xlsx"'
        return response

class PautaDOCXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, turma_id):
        escola = request.tenant or request.user.escola
        turma = get_object_or_404(Turma, id=turma_id, escola=escola)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')

        dados = consolidar_dados_turma(turma, periodo, ano)
        docx_bytes = gerar_pauta_docx(turma, escola, periodo, ano, dados['dados_alunos'], dados['disciplinas'])

        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="Pauta_{turma.nome}_{ano}.docx"'
        return response

class PautaExportJSONView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, turma_id):
        escola = request.tenant or request.user.escola
        turma = get_object_or_404(Turma, id=turma_id, escola=escola)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')

        dados = consolidar_dados_turma(turma, periodo, ano)
        disc_data = [{'id': str(d.id), 'nome': d.nome, 'codigo': d.codigo} for d in dados['disciplinas']]

        payload = {
            'escola': escola.nome,
            'turma': turma.nome,
            'periodo': periodo,
            'anoLetivo': ano,
            'disciplinas': disc_data,
            'alunos': dados['dados_alunos']
        }
        response = HttpResponse(json.dumps(payload, indent=2, ensure_ascii=False), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="Pauta_{turma.nome}_{ano}.json"'
        return response

class PautasEstatisticasGeraisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        escola = request.tenant or request.user.escola
        total_alunos = Aluno.objects.filter(escola=escola, status='ATIVO').count()
        total_turmas = Turma.objects.filter(escola=escola).count()

        return Response({
            'success': True,
            'data': {
                'totalAlunos': total_alunos,
                'totalTurmas': total_turmas,
                'taxaAprovacaoEstimada': 87.5,
                'taxaReprovacaoEstimada': 12.5
            }
        })
