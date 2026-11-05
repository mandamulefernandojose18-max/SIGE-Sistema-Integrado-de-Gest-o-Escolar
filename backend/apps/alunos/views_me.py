"""Endpoints do Portal do Aluno: anos lectivos/classes reais e PDF de faltas."""
import io
from collections import OrderedDict

from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aluno, PresencaAluno


def _aluno_do_pedido(request):
    aluno_id = getattr(request.user, 'aluno_id', None)
    if not aluno_id:
        return None
    return Aluno.objects.select_related('escola', 'turma').filter(id=aluno_id).first()


def _turmas_do_aluno(aluno):
    """Turmas reais por onde o aluno passou: actual, notas, notas de exame e presenças."""
    turmas = {}
    if aluno.turma_id:
        turmas[aluno.turma_id] = aluno.turma
    from apps.turmas.models import Turma
    from apps.notas.models import Nota, NotaExame
    ids = set(Nota.objects.filter(aluno=aluno).values_list('turma_id', flat=True))
    ids |= set(NotaExame.objects.filter(aluno=aluno).values_list('turma_id', flat=True))
    ids |= set(PresencaAluno.objects.filter(aluno=aluno).values_list('turma_id', flat=True))
    ids -= set(turmas)
    if ids:
        for t in Turma.objects.filter(id__in=ids, escola=aluno.escola):
            turmas[t.id] = t
    return list(turmas.values())


class AlunoMeAnosView(APIView):
    """Anos lectivos em que o aluno realmente frequentou, com a classe de cada um."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        aluno = _aluno_do_pedido(request)
        if not aluno:
            return Response({'success': False, 'message': 'Utilizador não é um aluno cadastrado.'}, status=status.HTTP_404_NOT_FOUND)
        por_ano = {}
        for t in _turmas_do_aluno(aluno):
            ano = str(t.ano_letivo)
            # Em caso de mais de uma turma no mesmo ano, prevalece a turma actual do aluno.
            if ano not in por_ano or t.id == aluno.turma_id:
                por_ano[ano] = {'ano': ano, 'classe': t.grau_ano, 'turma': t.nome, 'area': t.area}
        dados = [por_ano[a] for a in sorted(por_ano)]
        return Response({'success': True, 'data': dados})


def _faltas_do_aluno(aluno, ano):
    """Resumo por disciplina + registos de falta/atraso do ano lectivo (só presenças reais). None se o ano não for do aluno."""
    turmas = {str(t.ano_letivo): t for t in _turmas_do_aluno(aluno)}
    if not ano or ano not in turmas:
        return None
    qs = (PresencaAluno.objects.filter(aluno=aluno, turma__ano_letivo=ano)
          .select_related('disciplina').order_by('disciplina__nome', 'data'))
    por_disc = OrderedDict()
    registos = []
    for p in qs:
        nome = p.disciplina.nome if p.disciplina else 'Geral'
        r = por_disc.setdefault(nome, {'PRESENTE': 0, 'FALTA_JUSTIFICADA': 0, 'FALTA_INJUSTIFICADA': 0, 'ATRASO': 0})
        r[p.status] = r.get(p.status, 0) + 1
        if p.status != 'PRESENTE':
            registos.append({'id': str(p.id), 'data': p.data.isoformat(), 'disciplina': nome, 'status': p.status,
                             'observacao': p.observacao, 'justificacao': p.justificacao,
                             'pedido_justificacao': p.pedido_justificacao})
    registos.sort(key=lambda r: r['data'], reverse=True)
    return turmas[ano], por_disc, registos


class AlunoMeFaltasView(APIView):
    """Visualização das faltas do próprio aluno (por disciplina e registos), sem precisar de exportar."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        aluno = _aluno_do_pedido(request)
        if not aluno:
            return Response({'success': False, 'message': 'Utilizador não é um aluno cadastrado.'}, status=status.HTTP_404_NOT_FOUND)
        res = _faltas_do_aluno(aluno, str(request.query_params.get('ano') or '').strip())
        if res is None:
            return Response({'success': False, 'message': 'Ano lectivo inválido para este aluno.'}, status=status.HTTP_400_BAD_REQUEST)
        turma, por_disc, registos = res
        disciplinas = [{'disciplina': n, 'presencas': r['PRESENTE'], 'justificadas': r['FALTA_JUSTIFICADA'],
                        'injustificadas': r['FALTA_INJUSTIFICADA'], 'atrasos': r['ATRASO'],
                        'faltas': r['FALTA_JUSTIFICADA'] + r['FALTA_INJUSTIFICADA'],
                        'aulas': sum(r.values())} for n, r in por_disc.items()]
        return Response({'success': True, 'classe': turma.grau_ano, 'turma': turma.nome, 'ano': str(turma.ano_letivo),
                         'disciplinas': disciplinas, 'registos': registos})


class AlunoMeFaltasXlsxView(APIView):
    """XLSX das faltas do próprio aluno (Times New Roman), igual ao resumo do ecrã."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from openpyxl import Workbook
        from openpyxl.styles import Font
        aluno = _aluno_do_pedido(request)
        if not aluno:
            return Response({'success': False, 'message': 'Utilizador não é um aluno cadastrado.'}, status=status.HTTP_404_NOT_FOUND)
        ano = str(request.query_params.get('ano') or '').strip()
        res = _faltas_do_aluno(aluno, ano)
        if res is None:
            return Response({'success': False, 'message': 'Ano lectivo inválido para este aluno.'}, status=status.HTTP_400_BAD_REQUEST)
        turma, por_disc, _ = res
        wb = Workbook()
        ws = wb.active
        ws.title = 'Faltas'
        ws.append([(aluno.escola.nome or '').upper()])
        ws.append([f'MAPA DE FALTAS — ANO LECTIVO {ano}'])
        ws.append([f'Aluno: {aluno.nome_completo} | Código: {aluno.matricula} | {turma.grau_ano} Turma {turma.nome}'])
        ws.append([])
        ws.append(['Disciplina', 'Presenças', 'Faltas Just.', 'Faltas Injust.', 'Atrasos', 'Total Faltas'])
        if not por_disc:
            ws.append(['Não existem registos de presenças/faltas para este ano lectivo.'])
        tot = [0, 0, 0, 0]
        for nome, r in por_disc.items():
            fj, fi = r['FALTA_JUSTIFICADA'], r['FALTA_INJUSTIFICADA']
            ws.append([nome, r['PRESENTE'], fj, fi, r['ATRASO'], fj + fi])
            tot = [tot[0] + r['PRESENTE'], tot[1] + fj, tot[2] + fi, tot[3] + r['ATRASO']]
        if por_disc:
            ws.append(['TOTAL', tot[0], tot[1], tot[2], tot[3], tot[1] + tot[2]])
        normal, negrito = Font(name='Times New Roman', size=11), Font(name='Times New Roman', size=11, bold=True)
        for row in ws.iter_rows():
            for c in row:
                c.font = normal
        for r in (1, 2, 5):
            for c in ws[r]:
                c.font = negrito
        if por_disc:
            for c in ws[ws.max_row]:
                c.font = negrito
        for i, w in enumerate([32, 11, 13, 14, 9, 13], start=1):
            ws.column_dimensions[chr(64 + i)].width = w
        buf = io.BytesIO()
        wb.save(buf)
        resp = HttpResponse(buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = f'attachment; filename="faltas_{ano}.xlsx"'
        return resp


class AlunoMeFaltasPdfView(APIView):
    """PDF de faltas do aluno, gerado a partir das presenças de todas as disciplinas."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        aluno = _aluno_do_pedido(request)
        if not aluno:
            return Response({'success': False, 'message': 'Utilizador não é um aluno cadastrado.'}, status=status.HTTP_404_NOT_FOUND)
        ano = str(request.query_params.get('ano') or '').strip()
        turmas = {str(t.ano_letivo): t for t in _turmas_do_aluno(aluno)}
        if not ano or ano not in turmas:
            return Response({'success': False, 'message': 'Ano lectivo inválido para este aluno.'}, status=status.HTTP_400_BAD_REQUEST)

        qs = (PresencaAluno.objects
              .filter(aluno=aluno, turma__ano_letivo=ano)
              .select_related('disciplina')
              .order_by('disciplina__nome', 'data'))
        resumo = OrderedDict()
        for p in qs:
            nome = p.disciplina.nome if p.disciplina else 'Geral'
            r = resumo.setdefault(nome, {'PRESENTE': 0, 'FALTA_JUSTIFICADA': 0, 'FALTA_INJUSTIFICADA': 0, 'ATRASO': 0})
            r[p.status] = r.get(p.status, 0) + 1

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        turma = turmas[ano]
        s_c = ParagraphStyle('FC', fontName='Times-Bold', fontSize=12, leading=16, alignment=1)
        s_b = ParagraphStyle('FB', fontName='Times-Roman', fontSize=12, leading=16)
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
        elems = [
            Paragraph('REPÚBLICA DE MOÇAMBIQUE — MINISTÉRIO DA EDUCAÇÃO E CULTURA', s_c),
            Paragraph((aluno.escola.nome or '').upper(), s_c),
            Spacer(1, 0.5 * cm),
            Paragraph(f'MAPA DE FALTAS — ANO LECTIVO {ano}', s_c),
            Spacer(1, 0.4 * cm),
            Paragraph(f'<b>Aluno:</b> {aluno.nome_completo} &nbsp;&nbsp; <b>Código:</b> {aluno.matricula}', s_b),
            Paragraph(f'<b>Classe:</b> {turma.grau_ano} &nbsp;&nbsp; <b>Turma:</b> {turma.nome}', s_b),
            Spacer(1, 0.4 * cm),
        ]
        if not resumo:
            elems.append(Paragraph('Não existem registos de presenças/faltas para este ano lectivo.', s_b))
        else:
            linhas = [['Disciplina', 'Presenças', 'Faltas Just.', 'Faltas Injust.', 'Atrasos', 'Total Faltas']]
            tot = [0, 0, 0, 0]
            for nome, r in resumo.items():
                fj, fi = r['FALTA_JUSTIFICADA'], r['FALTA_INJUSTIFICADA']
                linhas.append([nome, r['PRESENTE'], fj, fi, r['ATRASO'], fj + fi])
                tot[0] += r['PRESENTE']; tot[1] += fj; tot[2] += fi; tot[3] += r['ATRASO']
            linhas.append(['TOTAL', tot[0], tot[1], tot[2], tot[3], tot[1] + tot[2]])
            t = Table(linhas, colWidths=[5.5 * cm, 2 * cm, 2.2 * cm, 2.4 * cm, 1.8 * cm, 2.3 * cm], repeatRows=1)
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTNAME', (0, 1), (-1, -2), 'Times-Roman'),
                ('FONTNAME', (0, -1), (-1, -1), 'Times-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elems.append(t)
        doc.build(elems)
        resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="faltas_{ano}.pdf"'
        return resp
