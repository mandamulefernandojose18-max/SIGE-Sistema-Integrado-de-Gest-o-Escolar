import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from .models import LogImpressao, DocumentoSalvo
from apps.alunos.models import Aluno
from apps.notas.models import Nota
from apps.disciplinas.models import Disciplina
from apps.pagamentos.models import Pagamento
from .services.pdf_service import gerar_boletim_pdf

def obter_dados_boletim_aluno(aluno, escola):
    notas = Nota.objects.filter(aluno=aluno).select_related('disciplina')
    disciplinas = Disciplina.objects.filter(escola=escola).order_by('nome')

    dados_disc = []
    for d in disciplinas:
        n1 = next((n.media_final for n in notas if n.disciplina_id == d.id and n.periodo == '1_TRIMESTRE'), '-')
        n2 = next((n.media_final for n in notas if n.disciplina_id == d.id and n.periodo == '2_TRIMESTRE'), '-')
        n3 = next((n.media_final for n in notas if n.disciplina_id == d.id and n.periodo == '3_TRIMESTRE'), '-')
        
        # Média anual aproximada dos trimestres lançados
        vals = [v for v in [n1, n2, n3] if isinstance(v, (int, float))]
        media_anual = round(sum(vals) / len(vals), 1) if vals else '-'

        dados_disc.append({
            'nome': d.nome,
            'codigo': d.codigo,
            't1': n1,
            't2': n2,
            't3': n3,
            'media_anual': media_anual,
            'situacao': 'Aprovado' if isinstance(media_anual, (int, float)) and media_anual >= 9.5 else ('Reprovado' if isinstance(media_anual, (int, float)) else 'Pendente')
        })

    return dados_disc

class BoletimView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)

        # Auditoria
        LogImpressao.objects.create(
            escola=escola,
            usuario=request.user,
            tipo_documento='BOLETIM',
            descricao=f"Consulta de Boletim de {aluno.nome}"
        )

        return Response({
            'success': True,
            'aluno': {
                'id': str(aluno.id),
                'nome': aluno.nome,
                'matricula': aluno.matricula,
                'turma': aluno.turma.nome if aluno.turma else 'Sem Turma',
                'grau': aluno.turma.grau_ano if aluno.turma else ''
            },
            'escola': escola.nome,
            'anoLetivo': escola.ano_letivo_ativo,
            'disciplinas': dados_disc
        })

class BoletimPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)

        pdf_bytes = gerar_boletim_pdf(aluno, escola, escola.ano_letivo_ativo, dados_disc)

        LogImpressao.objects.create(
            escola=escola,
            usuario=request.user,
            tipo_documento='BOLETIM',
            descricao=f"Emissão PDF de Boletim de {aluno.nome}"
        )

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Boletim_{aluno.matricula}.pdf"'
        return response

class DeclaracaoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)

        return Response({
            'success': True,
            'declaracao': {
                'aluno': aluno.nome,
                'matricula': aluno.matricula,
                'turma': aluno.turma.nome if aluno.turma else '',
                'anoLetivo': escola.ano_letivo_ativo,
                'escola': escola.nome,
                'director': escola.director_nome
            }
        })

class DeclaracaoPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        pdf_bytes = gerar_boletim_pdf(aluno, escola, escola.ano_letivo_ativo, dados_disc)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Declaracao_{aluno.matricula}.pdf"'
        return response

class CertificadoImpressaoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        return Response({
            'success': True,
            'certificado': {
                'aluno': aluno.nome,
                'matricula': aluno.matricula,
                'turma': aluno.turma.nome if aluno.turma else '',
                'escola': escola.nome
            }
        })

class ReciboImpressaoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pagamento_id):
        escola = request.tenant or request.user.escola
        pagamento = get_object_or_404(Pagamento, id=pagamento_id, escola=escola)
        return Response({
            'success': True,
            'recibo': {
                'numero': pagamento.recibo_numero or f"REC-{pagamento.id}",
                'aluno': pagamento.aluno.nome,
                'matricula': pagamento.aluno.matricula,
                'descricao': pagamento.descricao,
                'mes': pagamento.mes_referencia,
                'valor': str(pagamento.valor_pago or pagamento.valor),
                'metodo': pagamento.metodo_pagamento or 'MPESA',
                'data': pagamento.data_pagamento or pagamento.created_at
            }
        })

class FichaAlunoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        return Response({
            'success': True,
            'ficha': {
                'id': str(aluno.id),
                'nome': aluno.nome,
                'matricula': aluno.matricula,
                'nascimento': aluno.data_nascimento,
                'genero': aluno.genero,
                'turma': aluno.turma.nome if aluno.turma else '',
                'provincia': aluno.provincia,
                'distrito': aluno.distrito
            }
        })
