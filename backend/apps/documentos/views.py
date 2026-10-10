import json
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from .models import LogImpressao, DocumentoSalvo
from apps.alunos.models import Aluno
from apps.notas.models import Nota
from apps.disciplinas.models import Disciplina
from apps.turmas.models import Turma
from apps.pagamentos.models import Pagamento
from apps.certificados.models import Certificado
from common.utils.avaliacoes_mocambique import avaliar_aprovacao_pauta, obter_disciplinas_plano_curricular
from .services.pdf_service import (
    gerar_boletim_pdf, gerar_declaracao_pdf, gerar_certificado_pdf,
    gerar_ficha_pdf, gerar_recibo_pdf
)
from .services.docx_service import (
    gerar_boletim_docx, gerar_declaracao_docx, gerar_certificado_docx,
    gerar_ficha_docx, gerar_recibo_docx
)
from .services.excel_service import (
    gerar_boletim_xlsx, gerar_declaracao_xlsx, gerar_certificado_xlsx,
    gerar_lote_xlsx
)

from apps.pautas.services import obter_disciplinas_pauta_turma

def obter_dados_boletim_aluno(aluno, escola):
    notas = list(Nota.objects.filter(aluno=aluno).select_related('disciplina'))

    if aluno.turma:
        disciplinas = obter_disciplinas_pauta_turma(aluno.turma)
    else:
        classe_aluno = aluno.classe or ''
        qs = Disciplina.objects.filter(escola=escola)
        qs_classe = qs.filter(classe__iexact=classe_aluno) if classe_aluno else qs.none()

        disc_ids_com_notas = list(set(n.disciplina_id for n in notas if n.disciplina_id))
        qs_notas = qs.filter(id__in=disc_ids_com_notas) if disc_ids_com_notas else qs.none()

        disciplinas_raw = list(qs_classe) + list(qs_notas)
        if not disciplinas_raw:
            disciplinas_raw = list(qs.order_by('nome'))

        # Deduplicar estritamente por nome normalizado
        nomes_vistos = set()
        disciplinas = []
        for d in sorted(disciplinas_raw, key=lambda x: (x.codigo or '', x.nome or '')):
            chave = d.nome.strip().lower()
            if chave not in nomes_vistos:
                nomes_vistos.add(chave)
                disciplinas.append(d)

    dados_disc = []
    for d in disciplinas:
        chave_d = d.nome.strip().lower()

        # Buscar nota por id ou por nome da disciplina
        def extrair_nota(per):
            for n in notas:
                if n.periodo == per:
                    if n.disciplina_id == d.id or (n.disciplina and n.disciplina.nome.strip().lower() == chave_d):
                        tem_avaliacoes = any(
                            getattr(n, c, None) is not None and getattr(n, c, 0) > 0
                            for c in ['teste1', 'teste2', 'teste3', 'teste4', 'trabalho', 'avaliacao_trimestral']
                        )
                        if tem_avaliacoes or (n.media_final is not None and n.media_final > 0) or n.anotacao:
                            return n.media_final
            return '-'

        n1 = extrair_nota('1_TRIMESTRE')
        n2 = extrair_nota('2_TRIMESTRE')
        n3 = extrair_nota('3_TRIMESTRE')

        vals = [v for v in [n1, n2, n3] if isinstance(v, (int, float))]
        if vals:
            m_val = round(sum(vals) / len(vals), 1)
            media_anual = int(round(m_val))
            situacao = 'Aprovado' if media_anual >= 9.5 else 'Reprovado'
        else:
            media_anual = '-'
            situacao = 'Pendente'

        dados_disc.append({
            'nome': d.nome,
            'disciplina': d.nome,
            'codigo': d.codigo or '',
            't1': n1,
            't2': n2,
            't3': n3,
            'media_anual': media_anual,
            'mediaFinal': media_anual,
            'notaFinal': media_anual,
            'situacao': situacao
        })

    return dados_disc

def montar_payload_boletim(aluno, escola, dados_disc, media_global, avaliacao):
    codigo_inst = getattr(escola, 'codigo_escola', None) or f"ESC-{str(escola.id)[:4].upper()}"
    turno_nome = getattr(aluno.turma, 'turno', 'Manhã') if aluno.turma else 'Manhã'
    if str(turno_nome).upper() == 'MANHA':
        turno_nome = 'Manhã'
    elif str(turno_nome).upper() == 'TARDE':
        turno_nome = 'Tarde'
    elif str(turno_nome).upper() == 'NOITE':
        turno_nome = 'Noite'

    return {
        'titulo': f"BOLETIM DE APROVEITAMENTO — {aluno.nome.upper()}",
        'aluno': {
            'id': str(aluno.id),
            'nome': aluno.nome,
            'nomeCompleto': f"{aluno.nome} {aluno.apelido or ''}".strip(),
            'apelido': aluno.apelido or '',
            'matricula': aluno.matricula,
            'turma': {
                'nome': aluno.turma.nome if aluno.turma else 'Sem Turma',
                'grau_ano': aluno.turma.grau_ano if aluno.turma else '',
                'area': aluno.turma.area if aluno.turma else '',
                'turno': turno_nome
            } if aluno.turma else None,
            'grau': aluno.turma.grau_ano if aluno.turma else (aluno.classe or ''),
            'turno': turno_nome
        },
        'escola': {
            'id': str(escola.id),
            'nome': escola.nome,
            'provincia': escola.provincia or 'Inhambane',
            'distrito': escola.distrito or 'Morrumbene',
            'codigo_escola': codigo_inst
        },
        'anoLetivo': escola.ano_letivo_ativo or '2026',
        'anoLectivo': escola.ano_letivo_ativo or '2026',
        'disciplinas': dados_disc,
        'mediaGlobal': media_global,
        'mediaGeral': media_global,
        'situacaoGlobal': avaliacao['resultado'],
        'resultadoFinal': avaliacao['resultado']
    }

def montar_payload_declaracao(aluno, escola, dados_disc, media_global, avaliacao):
    codigo_inst = getattr(escola, 'codigo_escola', None) or f"ESC-{str(escola.id)[:4].upper()}"
    grau_ano_str = (aluno.turma.grau_ano if aluno.turma else aluno.classe) or '10ª Classe'

    return {
        'titulo': f"DECLARAÇÃO ESCOLAR — {aluno.nome.upper()}",
        'aluno': {
            'id': str(aluno.id),
            'nome': aluno.nome,
            'nomeCompleto': f"{aluno.nome} {aluno.apelido or ''}".strip(),
            'apelido': aluno.apelido or '',
            'matricula': aluno.matricula,
            'genero': aluno.genero or 'M',
            'pai': aluno.pai or '',
            'mae': aluno.mae or '',
            'tipo_documento': aluno.tipo_documento or 'B.I.',
            'numero_documento': aluno.numero_documento or getattr(aluno, 'bi_numero', None) or aluno.matricula or '---',
            'data_nascimento': str(aluno.data_nascimento) if aluno.data_nascimento else None,
            'distrito': aluno.distrito or escola.distrito or 'Massinga',
            'provincia': aluno.provincia or escola.provincia or 'Inhambane',
            'turma': {
                'nome': aluno.turma.nome if aluno.turma else '',
                'grau_ano': grau_ano_str,
                'area': aluno.turma.area if aluno.turma else (aluno.area or 'Geral')
            } if aluno.turma else None
        },
        'escola': {
            'id': str(escola.id),
            'nome': escola.nome,
            'provincia': escola.provincia or 'Inhambane',
            'distrito': escola.distrito or 'Morrumbene',
            'codigo_escola': codigo_inst
        },
        'disciplinas': dados_disc,
        'anoLetivo': escola.ano_letivo_ativo or '2026',
        'anoLectivo': escola.ano_letivo_ativo or '2026',
        'grauAno': grau_ano_str,
        'mediaGlobal': media_global,
        'mediaGeral': media_global,
        'resultadoOficial': avaliacao['resultado'],
        'resultadoFinal': avaliacao['resultado'],
        'directorNome': escola.director_nome or 'Pero Chitofo Murrombe',
        'directorCarreira': getattr(escola, 'director_carreira', 'Especialista de Educação'),
        'declaracao': {
            'aluno': aluno.nome,
            'matricula': aluno.matricula,
            'turma': aluno.turma.nome if aluno.turma else '',
            'anoLetivo': escola.ano_letivo_ativo or '2026',
            'escola': escola.nome,
            'director': escola.director_nome
        }
    }

def montar_payload_certificado(aluno, escola, dados_disc, media_global, avaliacao, usuario=None):
    codigo_inst = getattr(escola, 'codigo_escola', None) or f"ESC-{str(escola.id)[:4].upper()}"
    grau_ano_str = (aluno.turma.grau_ano if aluno.turma else aluno.classe) or '12ª Classe'
    area_str = (aluno.turma.area if aluno.turma else aluno.area) or 'Ciências e Letras'

    cert = Certificado.objects.filter(escola=escola, aluno=aluno, tipo='CONCLUSAO').first()
    if not cert:
        codigo_auth = f"CERT-{uuid.uuid4().hex[:10].upper()}"
        qr_url = f"https://sige.co.mz/verificar-certificado.html?codigo={codigo_auth}"
        cert = Certificado.objects.create(
            escola=escola,
            aluno=aluno,
            tipo='CONCLUSAO',
            codigo_autenticidade=codigo_auth,
            qrcode_data=qr_url,
            emitido_por=usuario.nome if (usuario and hasattr(usuario, 'nome')) else 'Secretaria'
        )

    return {
        'titulo': f"CERTIFICADO DE HABILITAÇÕES — {aluno.nome.upper()}",
        'aluno': {
            'id': str(aluno.id),
            'nome': aluno.nome,
            'nomeCompleto': f"{aluno.nome} {aluno.apelido or ''}".strip(),
            'apelido': aluno.apelido or '',
            'matricula': aluno.matricula,
            'genero': aluno.genero or 'M',
            'pai': aluno.pai or '',
            'mae': aluno.mae or '',
            'tipo_documento': aluno.tipo_documento or 'BI',
            'numero_documento': aluno.numero_documento or getattr(aluno, 'bi_numero', None) or '',
            'data_nascimento': str(aluno.data_nascimento) if aluno.data_nascimento else None,
            'distrito': aluno.distrito or escola.distrito or 'Massinga',
            'provincia': aluno.provincia or escola.provincia or 'Inhambane',
            'turma': {
                'nome': aluno.turma.nome if aluno.turma else '',
                'grau_ano': grau_ano_str,
                'area': area_str,
                'turno': aluno.turma.turno if aluno.turma else 'MANHA'
            } if aluno.turma else None
        },
        'escola': {
            'id': str(escola.id),
            'nome': escola.nome,
            'provincia': escola.provincia or 'Inhambane',
            'distrito': escola.distrito or 'Morrumbene',
            'codigo_escola': codigo_inst
        },
        'disciplinas': [
            {
                'disciplina': d['nome'],
                'nome': d['nome'],
                'codigo': d['codigo'],
                'notaFinal': d['media_anual'] if isinstance(d['media_anual'], (int, float)) else '-',
                'mediaFinal': d['media_anual'] if isinstance(d['media_anual'], (int, float)) else '-',
                't1': d['t1'],
                't2': d['t2'],
                't3': d['t3'],
                'situacao': d['situacao']
            }
            for d in dados_disc
        ],
        'grauAno': grau_ano_str,
        'area': area_str,
        'mediaGlobal': media_global,
        'mediaGeral': media_global,
        'resultadoFinal': avaliacao['resultado'],
        'anoLectivo': escola.ano_letivo_ativo or '2026',
        'anoLetivo': escola.ano_letivo_ativo or '2026',
        'directorNome': escola.director_nome or 'Pero Chitofo Murrombe',
        'directorCarreira': getattr(escola, 'director_carreira', 'Especialista de Educação'),
        'chefeSecretariaNome': getattr(escola, 'chefe_secretaria_nome', 'Glória João Zunguze'),
        'chefeSecretariaCarreira': getattr(escola, 'chefe_secretaria_carreira', 'Técnica Profissional'),
        'codigo_autenticidade': cert.codigo_autenticidade,
        'qrcode_data': cert.qrcode_data,
        'certificado': {
            'aluno': aluno.nome,
            'matricula': aluno.matricula,
            'turma': aluno.turma.nome if aluno.turma else '',
            'escola': escola.nome,
            'codigo_autenticidade': cert.codigo_autenticidade
        }
    }

def calcular_desempenho_documento(dados_disc, grau_ano=None, tipo='BOLETIM'):
    total_disc = len(dados_disc)
    vals = [d['media_anual'] for d in dados_disc if isinstance(d.get('media_anual'), (int, float))]

    if tipo == 'BOLETIM':
        media_global = round(sum(vals) / len(vals), 1) if vals else '-'
        if vals:
            avaliacao = avaliar_aprovacao_pauta(
                [{'disciplina': d['nome'], 'notaFinal': d['media_anual']} for d in dados_disc if isinstance(d.get('media_anual'), (int, float))],
                grau_ano
            )
        else:
            avaliacao = {'aprovado': False, 'resultado': 'Pendente', 'siglaResultado': '-', 'mediaGeral': '-'}
        return media_global, avaliacao

    # Para CERTIFICADO e DECLARAÇÃO DE CONCLUSÃO:
    # SÓ existe média global e resultado de aprovação se TODAS as disciplinas requeridas tiverem sido avaliadas.
    # Se o aluno foi avaliado apenas em parte das disciplinas (ex: só Matemática), não tem média global de conclusão nem resultado falso.
    todas_avaliadas = len(vals) > 0 and len(vals) == total_disc
    if todas_avaliadas:
        media_global = round(sum(vals) / len(vals), 1)
        avaliacao = avaliar_aprovacao_pauta(
            [{'disciplina': d['nome'], 'notaFinal': d['media_anual']} for d in dados_disc if isinstance(d.get('media_anual'), (int, float))],
            grau_ano
        )
    else:
        media_global = '-'
        avaliacao = {
            'aprovado': False,
            'resultado': 'Pendente',
            'siglaResultado': '-',
            'mediaGeral': '-',
            'totalNegativas': sum(1 for v in vals if v < 9.5),
            'motivo': 'Aluno com disciplinas pendentes / avaliações parciais'
        }
    return media_global, avaliacao

class BoletimView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, avaliacao = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='BOLETIM'
        )

        LogImpressao.objects.create(
            escola=escola,
            usuario=request.user,
            tipo_documento='BOLETIM',
            descricao=f"Consulta de Boletim de {aluno.nome}"
        )

        dados_boletim = montar_payload_boletim(aluno, escola, dados_disc, media_global, avaliacao)

        return Response({
            'success': True,
            'data': dados_boletim,
            **dados_boletim
        })

class BoletimPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        orientacao = request.query_params.get('orientacao', 'portrait')

        pdf_bytes = gerar_boletim_pdf(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            orientacao=orientacao
        )

        LogImpressao.objects.create(
            escola=escola,
            usuario=request.user,
            tipo_documento='BOLETIM',
            descricao=f"Emissão PDF de Boletim de {aluno.nome}"
        )

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Boletim_{aluno.matricula}.pdf"'
        return response

class BoletimDOCXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        orientacao = request.query_params.get('orientacao', 'portrait')

        docx_bytes = gerar_boletim_docx(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            orientacao=orientacao
        )

        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="Boletim_{aluno.matricula}.docx"'
        return response

class BoletimXLSXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        orientacao = request.query_params.get('orientacao', 'portrait')

        xlsx_bytes = gerar_boletim_xlsx(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            orientacao=orientacao
        )

        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Boletim_{aluno.matricula}.xlsx"'
        return response

class DeclaracaoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, avaliacao = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='DECLARACAO'
        )

        dados_decl = montar_payload_declaracao(aluno, escola, dados_disc, media_global, avaliacao)

        return Response({
            'success': True,
            'data': dados_decl,
            'declaracao': dados_decl,
            **dados_decl
        })

class DeclaracaoPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, _ = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='DECLARACAO'
        )
        media_pdf = media_global if media_global != '-' else None
        orientacao = request.query_params.get('orientacao', 'portrait')

        pdf_bytes = gerar_declaracao_pdf(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            media_global=media_pdf,
            director_nome=escola.director_nome,
            orientacao=orientacao
        )

        LogImpressao.objects.create(
            escola=escola,
            usuario=request.user,
            tipo_documento='DECLARACAO',
            descricao=f"Emissão PDF de Declaração de {aluno.nome}"
        )

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Declaracao_{aluno.matricula}.pdf"'
        return response

class DeclaracaoDOCXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, _ = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='DECLARACAO'
        )
        media_val = media_global if media_global != '-' else None
        orientacao = request.query_params.get('orientacao', 'portrait')

        docx_bytes = gerar_declaracao_docx(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            media_global=media_val,
            director_nome=escola.director_nome,
            orientacao=orientacao
        )

        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="Declaracao_{aluno.matricula}.docx"'
        return response

class DeclaracaoXLSXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, _ = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='DECLARACAO'
        )
        media_val = media_global if media_global != '-' else None
        orientacao = request.query_params.get('orientacao', 'portrait')

        xlsx_bytes = gerar_declaracao_xlsx(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            media_global=media_val,
            director_nome=escola.director_nome,
            orientacao=orientacao
        )

        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Declaracao_{aluno.matricula}.xlsx"'
        return response

class CertificadoImpressaoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, avaliacao = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='CERTIFICADO'
        )

        dados_cert = montar_payload_certificado(aluno, escola, dados_disc, media_global, avaliacao, request.user)

        LogImpressao.objects.create(
            escola=escola,
            usuario=request.user,
            tipo_documento='CERTIFICADO',
            descricao=f"Consulta de Certificado de {aluno.nome}"
        )

        return Response({
            'success': True,
            'data': dados_cert,
            'certificado': dados_cert,
            **dados_cert
        })

class CertificadoPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, _ = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='CERTIFICADO'
        )
        media_pdf = media_global if media_global != '-' else None
        orientacao = request.query_params.get('orientacao', 'portrait')

        cert = Certificado.objects.filter(escola=escola, aluno=aluno, tipo='CONCLUSAO').first()
        cod = cert.codigo_autenticidade if cert else f"CERT-{aluno.matricula}-2026"

        pdf_bytes = gerar_certificado_pdf(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            media_global=media_pdf,
            codigo_autenticidade=cod,
            orientacao=orientacao
        )

        LogImpressao.objects.create(
            escola=escola,
            usuario=request.user,
            tipo_documento='CERTIFICADO',
            descricao=f"Emissão PDF de Certificado de {aluno.nome}"
        )

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Certificado_{aluno.matricula}.pdf"'
        return response

class CertificadoDOCXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, _ = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='CERTIFICADO'
        )
        media_val = media_global if media_global != '-' else None
        orientacao = request.query_params.get('orientacao', 'portrait')

        cert = Certificado.objects.filter(escola=escola, aluno=aluno, tipo='CONCLUSAO').first()
        cod = cert.codigo_autenticidade if cert else f"CERT-{aluno.matricula}-2026"

        docx_bytes = gerar_certificado_docx(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            media_global=media_val,
            codigo_autenticidade=cod,
            orientacao=orientacao
        )

        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="Certificado_{aluno.matricula}.docx"'
        return response

class CertificadoXLSXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, _ = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='CERTIFICADO'
        )
        media_val = media_global if media_global != '-' else None
        orientacao = request.query_params.get('orientacao', 'portrait')

        cert = Certificado.objects.filter(escola=escola, aluno=aluno, tipo='CONCLUSAO').first()
        cod = cert.codigo_autenticidade if cert else f"CERT-{aluno.matricula}-2026"

        xlsx_bytes = gerar_certificado_xlsx(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            media_global=media_val,
            codigo_autenticidade=cod,
            orientacao=orientacao
        )

        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Certificado_{aluno.matricula}.xlsx"'
        return response

class LoteImpressaoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, turma_id):
        escola = request.tenant or request.user.escola
        turma = get_object_or_404(Turma, id=turma_id, escola=escola)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()

        alunos = Aluno.objects.filter(turma=turma, status='ATIVO').order_by('nome')
        documentos = []

        for aluno in alunos:
            dados_disc = obter_dados_boletim_aluno(aluno, escola)
            media_global, avaliacao = calcular_desempenho_documento(
                dados_disc, turma.grau_ano, tipo=tipo
            )

            if tipo == 'DECLARACAO':
                doc = montar_payload_declaracao(aluno, escola, dados_disc, media_global, avaliacao)
            elif tipo == 'CERTIFICADO':
                doc = montar_payload_certificado(aluno, escola, dados_disc, media_global, avaliacao, request.user)
            else:
                doc = montar_payload_boletim(aluno, escola, dados_disc, media_global, avaliacao)

            documentos.append(doc)

        retorno = {
            'success': True,
            'tipoDocumento': tipo,
            'total': len(documentos),
            'documentos': documentos
        }
        retorno['data'] = {
            'tipoDocumento': tipo,
            'total': len(documentos),
            'documentos': documentos
        }
        return Response(retorno)

class LoteXLSXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, turma_id):
        escola = request.tenant or request.user.escola
        turma = get_object_or_404(Turma, id=turma_id, escola=escola)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()
        orientacao = request.query_params.get('orientacao', 'portrait')

        alunos = Aluno.objects.filter(turma=turma, status='ATIVO').order_by('nome')
        documentos = []

        for aluno in alunos:
            dados_disc = obter_dados_boletim_aluno(aluno, escola)
            media_global, avaliacao = calcular_desempenho_documento(
                dados_disc, turma.grau_ano, tipo=tipo
            )
            if tipo == 'DECLARACAO':
                doc = montar_payload_declaracao(aluno, escola, dados_disc, media_global, avaliacao)
            elif tipo == 'CERTIFICADO':
                doc = montar_payload_certificado(aluno, escola, dados_disc, media_global, avaliacao, request.user)
            else:
                doc = montar_payload_boletim(aluno, escola, dados_disc, media_global, avaliacao)
            documentos.append(doc)

        xlsx_bytes = gerar_lote_xlsx(turma, escola, tipo, documentos, orientacao=orientacao)
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Lote_{tipo}_{turma.nome}.xlsx"'
        return response

class ReciboImpressaoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pagamento_id):
        escola = request.tenant or request.user.escola
        pagamento = get_object_or_404(Pagamento, id=pagamento_id, escola=escola)
        aluno = pagamento.aluno
        dados_rec = {
            'numero': pagamento.recibo_numero or f"REC-{pagamento.id}",
            'aluno': {
                'id': str(aluno.id) if aluno else '',
                'nome': aluno.nome if aluno else '',
                'apelido': aluno.apelido or '' if aluno else '',
                'matricula': aluno.matricula if aluno else '',
                'turma': {
                    'nome': aluno.turma.nome if aluno and aluno.turma else '-'
                } if aluno else None
            },
            'escola': {
                'nome': escola.nome,
                'nif_cnpj': getattr(escola, 'nuit', None) or getattr(escola, 'nif_cnpj', '400000000'),
                'telefone': getattr(escola, 'telefone', '-')
            },
            'pagamento': {
                'recibo_numero': pagamento.recibo_numero or f"REC-{pagamento.id}",
                'descricao': pagamento.descricao,
                'mes_referencia': pagamento.mes_referencia,
                'valor': str(pagamento.valor_pago or pagamento.valor),
                'metodo_pagamento': pagamento.metodo_pagamento or 'MPESA',
                'data_pagamento': pagamento.data_pagamento or pagamento.created_at
            },
            'descricao': pagamento.descricao,
            'mes': pagamento.mes_referencia,
            'valor': str(pagamento.valor_pago or pagamento.valor),
            'metodo': pagamento.metodo_pagamento or 'MPESA',
            'data': pagamento.data_pagamento or pagamento.created_at
        }
        return Response({
            'success': True,
            'data': dados_rec,
            'recibo': dados_rec
        })

class ReciboPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pagamento_id):
        escola = request.tenant or request.user.escola
        pagamento = get_object_or_404(Pagamento, id=pagamento_id, escola=escola)
        orientacao = request.query_params.get('orientacao', 'portrait')

        pdf_bytes = gerar_recibo_pdf(pagamento, escola, orientacao=orientacao)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Recibo_{pagamento.id}.pdf"'
        return response

class ReciboDOCXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pagamento_id):
        escola = request.tenant or request.user.escola
        pagamento = get_object_or_404(Pagamento, id=pagamento_id, escola=escola)
        orientacao = request.query_params.get('orientacao', 'portrait')

        docx_bytes = gerar_recibo_docx(pagamento, escola, orientacao=orientacao)
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="Recibo_{pagamento.id}.docx"'
        return response

class FichaAlunoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)

        classe_str = getattr(aluno, 'classe', None) or (aluno.turma.grau_ano if aluno.turma else None) or '10ª Classe'
        area_str = getattr(aluno, 'area', None) or (aluno.turma.area if aluno.turma else None) or 'Ensino Geral'
        ano_letivo_str = getattr(aluno.turma, 'ano_letivo', None) or getattr(aluno, 'ano_ingresso', None) or escola.ano_letivo_ativo or '2026'
        turno_str = getattr(aluno.turma, 'turno', None) or getattr(aluno, 'turno', None) or 'Manhã'
        disciplinas = obter_disciplinas_plano_curricular(aluno, escola)

        dados_ficha = {
            'aluno': {
                'id': str(aluno.id),
                'nome': aluno.nome,
                'apelido': aluno.apelido or '',
                'matricula': aluno.matricula,
                'data_nascimento': str(aluno.data_nascimento) if aluno.data_nascimento else None,
                'genero': aluno.genero or 'M',
                'tipo_documento': aluno.tipo_documento or 'BI',
                'numero_documento': aluno.numero_documento or aluno.bi_numero or '',
                'nuit': getattr(aluno, 'nuit', None) or '',
                'distrito': aluno.distrito or '',
                'provincia': aluno.provincia or '',
                'pai': aluno.pai or '',
                'mae': aluno.mae or '',
                'nome_responsavel': getattr(aluno, 'nome_responsavel', None) or '',
                'contato_responsavel': getattr(aluno, 'contato_responsavel', None) or '',
                'classe': classe_str,
                'area': area_str,
                'ano_letivo': ano_letivo_str,
                'turno': turno_str,
                'turma': {
                    'nome': aluno.turma.nome if aluno.turma else '-',
                    'grau_ano': aluno.turma.grau_ano if aluno.turma else classe_str,
                    'area': aluno.turma.area if aluno.turma else area_str,
                    'turno': turno_str
                },
                'disciplinas': disciplinas
            },
            'escola': {
                'nome': escola.nome,
                'provincia': escola.provincia or '',
                'distrito': escola.distrito or '',
                'ano_letivo': escola.ano_letivo_ativo or '2026'
            }
        }
        return Response({
            'success': True,
            'data': dados_ficha,
            'ficha': dados_ficha
        })

class FichaPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        orientacao = request.query_params.get('orientacao', 'portrait')

        pdf_bytes = gerar_ficha_pdf(aluno, escola, orientacao=orientacao)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Ficha_{aluno.matricula}.pdf"'
        return response

class FichaDOCXView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, aluno_id):
        escola = request.tenant or request.user.escola
        aluno = get_object_or_404(Aluno, id=aluno_id, escola=escola)
        orientacao = request.query_params.get('orientacao', 'portrait')

        docx_bytes = gerar_ficha_docx(aluno, escola, orientacao=orientacao)
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="Ficha_{aluno.matricula}.docx"'
        return response

