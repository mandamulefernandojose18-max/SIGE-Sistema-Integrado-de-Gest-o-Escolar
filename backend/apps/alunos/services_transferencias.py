"""Serviços do processo de Transferências & Anulações de Matrícula.

Tudo é calculado a partir de registos reais (pagamentos, notas, presenças); nada é inventado.
Valores monetários em MZN.
"""
import io
import secrets
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Max, Q
from django.utils import timezone

from .models import PresencaAluno, TransferenciaAnulacao

PRAZO_ALERTA_DIAS = 7
ITENS_QUITACAO_MANUAIS = ('biblioteca', 'material', 'documentos')
ROTULOS_QUITACAO = {
    'propinas': 'Propinas e pagamentos em dia',
    'biblioteca': 'Livros da biblioteca devolvidos',
    'material': 'Material escolar devolvido',
    'documentos': 'Documentos do aluno entregues',
}
PAGAMENTOS_EM_ABERTO = ('PENDENTE', 'ATRASADO')


def quitacao_info(t):
    """Quitação do processo. As propinas vêm dos pagamentos reais em aberto já vencidos (em MZN)."""
    from apps.pagamentos.models import Pagamento
    agora = timezone.now()
    em_aberto = Pagamento.objects.filter(
        aluno=t.aluno, escola=t.escola, status__in=PAGAMENTOS_EM_ABERTO, data_vencimento__lte=agora,
    ).filter(valor_pago__lt=F('valor'))
    total = Decimal('0')
    n = 0
    for p in em_aberto.only('valor', 'valor_pago'):
        total += (p.valor or 0) - (p.valor_pago or 0)
        n += 1
    manual = t.quitacao if isinstance(t.quitacao, dict) else {}
    itens = {
        'propinas': {'ok': n == 0, 'em_divida': n, 'total_mzn': str(total), 'moeda': 'MZN'},
    }
    for k in ITENS_QUITACAO_MANUAIS:
        itens[k] = {'ok': bool(manual.get(k))}
    completa = all(v['ok'] for v in itens.values())
    return {'itens': itens, 'completa': completa, 'dispensada': t.quitacao_dispensada}


def aluno_com_divida(aluno, escola):
    from apps.pagamentos.models import Pagamento
    return Pagamento.objects.filter(
        aluno=aluno, escola=escola, status__in=PAGAMENTOS_EM_ABERTO, data_vencimento__lte=timezone.now(),
    ).filter(valor_pago__lt=F('valor')).exists()


def novo_codigo_verificacao():
    return 'TR-' + secrets.token_hex(5).upper()


@transaction.atomic
def atribuir_numero_oficial(t):
    """Número sequencial por escola e ano (GT-AAAA-NNNN / DA-AAAA-NNNN) e código público de verificação."""
    ano = str(timezone.now().year)
    ultimo = (TransferenciaAnulacao.objects.select_for_update()
              .filter(escola=t.escola, ano_guia=ano).aggregate(m=Max('numero_sequencial'))['m'] or 0)
    t.ano_guia = ano
    t.numero_sequencial = ultimo + 1
    if not t.codigo_verificacao:
        t.codigo_verificacao = novo_codigo_verificacao()
    t.guia_numero = t.numero_guia_oficial
    return t


def resumo_faltas(aluno):
    qs = PresencaAluno.objects.filter(aluno=aluno)
    return {
        'justificadas': qs.filter(status='FALTA_JUSTIFICADA').count(),
        'injustificadas': qs.filter(status='FALTA_INJUSTIFICADA').count(),
    }


def historico_escolar(aluno, escola):
    """Notas oficiais por disciplina, reutilizando o cálculo central do boletim (sem duplicar fórmulas)."""
    try:
        from apps.documentos.views import obter_dados_boletim_aluno
        return obter_dados_boletim_aluno(aluno, escola)
    except Exception:
        return []


def _fmt_nota(v):
    return f'{v:.0f}' if isinstance(v, (int, float)) else '-'


def gerar_pdf_documento(t, url_base):
    """Guia de Transferência (saída/entrada) ou Declaração de Anulação de Matrícula, em Times New Roman."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    import qrcode

    aluno, escola = t.aluno, t.escola
    eh_anulacao = t.tipo == 'ANULACAO_MATRICULA'
    s_c = ParagraphStyle('GC', fontName='Times-Bold', fontSize=12, leading=16, alignment=1)
    s_t = ParagraphStyle('GT', fontName='Times-Bold', fontSize=14, leading=18, alignment=1)
    s_b = ParagraphStyle('GB', fontName='Times-Roman', fontSize=12, leading=17, alignment=4)
    s_s = ParagraphStyle('GS', fontName='Times-Roman', fontSize=9, leading=12, alignment=1)

    titulo = 'DECLARAÇÃO DE ANULAÇÃO DE MATRÍCULA' if eh_anulacao else 'GUIA DE TRANSFERÊNCIA'
    classe = t.classe_snapshot or aluno.classe or '-'
    turma = t.turma_snapshot or (aluno.turma.nome if aluno.turma else '-')
    ano = t.ano_letivo_snapshot or '-'
    director = (escola.director_nome or '').strip() or 'O Director da Escola'
    data_aprov = timezone.localtime(t.data_aprovacao).strftime('%d/%m/%Y') if t.data_aprovacao else '-'
    esc = lambda s: (str(s or '')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    if t.tipo == 'TRANSFERENCIA_SAIDA':
        corpo = (f'Para os devidos efeitos se declara que o(a) aluno(a) <b>{esc(aluno.nome_completo)}</b>, código <b>{esc(aluno.matricula)}</b>, '
                 f'nascido(a) a {aluno.data_nascimento.strftime("%d/%m/%Y")}, frequentou a <b>{esc(classe)}</b>, turma <b>{esc(turma)}</b>, '
                 f'no ano lectivo de <b>{esc(ano)}</b>, nesta instituição, e foi <b>transferido(a)</b> para '
                 f'<b>{esc(t.escola_origem_destino) or "outra instituição de ensino"}</b>, por aprovação da Direcção em {data_aprov}. '
                 f'Motivo: {esc(t.get_motivo_categoria_display())}{(" — " + esc(t.motivo)) if t.motivo else ""}.')
    elif t.tipo == 'TRANSFERENCIA_ENTRADA':
        corpo = (f'Para os devidos efeitos se declara que o(a) aluno(a) <b>{esc(aluno.nome_completo)}</b>, código <b>{esc(aluno.matricula)}</b>, '
                 f'proveniente de <b>{esc(t.escola_origem_destino) or "outra instituição de ensino"}</b>, foi <b>admitido(a) por transferência</b> '
                 f'nesta instituição, na <b>{esc(classe)}</b>, ano lectivo <b>{esc(ano)}</b>, por aprovação da Direcção em {data_aprov}.')
    else:
        corpo = (f'Para os devidos efeitos se declara que a matrícula do(a) aluno(a) <b>{esc(aluno.nome_completo)}</b>, código <b>{esc(aluno.matricula)}</b>, '
                 f'na <b>{esc(classe)}</b>, turma <b>{esc(turma)}</b>, ano lectivo <b>{esc(ano)}</b>, foi <b>anulada</b> por aprovação da Direcção em {data_aprov}. '
                 f'Motivo: {esc(t.get_motivo_categoria_display())}{(" — " + esc(t.motivo)) if t.motivo else ""}.')

    url_verif = f'{url_base.rstrip("/")}/verificar-transferencia.html?codigo={t.codigo_verificacao}'
    qr_buf = io.BytesIO()
    qrcode.make(url_verif).save(qr_buf, format='PNG')
    qr_buf.seek(0)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm)
    el = [
        Paragraph('REPÚBLICA DE MOÇAMBIQUE', s_c),
        Paragraph('MINISTÉRIO DA EDUCAÇÃO E CULTURA', s_c),
        Paragraph(esc(escola.nome).upper(), s_c),
        Paragraph(f'{esc(escola.distrito)} — {esc(escola.provincia)}', s_s),
        Spacer(1, 0.5 * cm),
        Paragraph(titulo, s_t),
        Paragraph(f'N.º {t.numero_guia_oficial}', s_c),
        Spacer(1, 0.5 * cm),
        Paragraph(corpo, s_b),
        Spacer(1, 0.4 * cm),
    ]

    if not eh_anulacao:
        disc = historico_escolar(aluno, escola)
        faltas = resumo_faltas(aluno)
        el.append(Paragraph('<b>Aproveitamento escolar registado</b>', s_b))
        if disc:
            linhas = [['Disciplina', 'MT1', 'MT2', 'MT3', 'Média Anual', 'Situação']]
            estilos = [
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'), ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 10), ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')), ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ]
            for i, d in enumerate(disc, start=1):
                linhas.append([d.get('nome', ''), _fmt_nota(d.get('t1')), _fmt_nota(d.get('t2')), _fmt_nota(d.get('t3')),
                               _fmt_nota(d.get('media_anual')), d.get('situacao', '')])
                for col, k in ((1, 't1'), (2, 't2'), (3, 't3'), (4, 'media_anual')):
                    v = d.get(k)
                    if isinstance(v, (int, float)) and v < 10:
                        estilos.append(('TEXTCOLOR', (col, i), (col, i), colors.red))
            tb = Table(linhas, colWidths=[6 * cm, 1.6 * cm, 1.6 * cm, 1.6 * cm, 2.6 * cm, 2.4 * cm], repeatRows=1)
            tb.setStyle(TableStyle(estilos))
            el.append(tb)
        else:
            el.append(Paragraph('Sem notas registadas no sistema para este aluno.', s_b))
        el.append(Spacer(1, 0.2 * cm))
        el.append(Paragraph(f'Faltas registadas: {faltas["justificadas"]} justificadas e {faltas["injustificadas"]} injustificadas.', s_b))

    el.append(Spacer(1, 1.2 * cm))
    assin = Table([[
        Paragraph(f'Emitido em {timezone.localtime().strftime("%d/%m/%Y")}<br/><br/>_____________________________<br/>'
                  f'{esc(director)}<br/>O Director da Escola', s_s),
        Image(qr_buf, width=2.6 * cm, height=2.6 * cm),
    ]], colWidths=[11 * cm, 4 * cm])
    assin.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'BOTTOM'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    el.append(assin)
    el.append(Spacer(1, 0.2 * cm))
    el.append(Paragraph(f'Código de verificação: {t.codigo_verificacao} • Validar em {url_verif}', s_s))
    doc.build(el)
    return buf.getvalue()


def gerar_xlsx_lista(itens):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = 'Transferências'
    cab = ['Data', 'Aluno', 'Código', 'Classe', 'Turma', 'Tipo', 'Escola origem/destino', 'Motivo', 'Estado', 'N.º Guia']
    ws.append(cab)
    fonte = Font(name='Times New Roman', size=11)
    for c in ws[1]:
        c.font = Font(name='Times New Roman', size=11, bold=True)
    for t in itens:
        ws.append([
            t.data_solicitacao.strftime('%d/%m/%Y'), t.aluno.nome_completo, t.aluno.matricula,
            t.classe_snapshot, t.turma_snapshot, t.get_tipo_display(), t.escola_origem_destino,
            t.get_motivo_categoria_display(), t.get_status_display(), t.numero_guia_oficial,
        ])
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = fonte
    for i, w in enumerate([12, 32, 22, 14, 12, 24, 30, 28, 22, 14], start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def gerar_pdf_lista(itens, escola):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    s_c = ParagraphStyle('LC', fontName='Times-Bold', fontSize=12, leading=16, alignment=1)
    s_n = ParagraphStyle('LN', fontName='Times-Roman', fontSize=9, leading=11)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    el = [Paragraph((escola.nome if escola else '').upper(), s_c),
          Paragraph('TRANSFERÊNCIAS E ANULAÇÕES DE MATRÍCULA', s_c), Spacer(1, 0.4 * cm)]
    if not itens:
        el.append(Paragraph('Sem processos registados para os filtros indicados.', s_n))
    else:
        linhas = [['Data', 'Aluno', 'Código', 'Classe/Turma', 'Tipo', 'Origem/Destino', 'Motivo', 'Estado', 'N.º Guia']]
        for t in itens:
            linhas.append([
                t.data_solicitacao.strftime('%d/%m/%Y'), Paragraph(t.aluno.nome_completo, s_n), t.aluno.matricula,
                f'{t.classe_snapshot} {t.turma_snapshot}'.strip(), Paragraph(t.get_tipo_display(), s_n),
                Paragraph(t.escola_origem_destino or '-', s_n), Paragraph(t.get_motivo_categoria_display(), s_n),
                t.get_status_display(), t.numero_guia_oficial or '-',
            ])
        tb = Table(linhas, repeatRows=1, colWidths=[1.9 * cm, 4.5 * cm, 3.6 * cm, 3 * cm, 3 * cm, 3.6 * cm, 3 * cm, 2.4 * cm, 2 * cm])
        tb.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'), ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 8), ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        el.append(tb)
    doc.build(el)
    return buf.getvalue()
