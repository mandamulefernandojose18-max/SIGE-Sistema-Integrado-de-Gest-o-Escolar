import os
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
    gerar_ficha_pdf, gerar_recibo_pdf, gerar_lote_pdf
)
from .services.docx_service import (
    gerar_boletim_docx, gerar_declaracao_docx, gerar_certificado_docx,
    gerar_ficha_docx, gerar_recibo_docx, gerar_lote_docx
)
from .services.excel_service import (
    gerar_boletim_xlsx, gerar_declaracao_xlsx, gerar_certificado_xlsx,
    gerar_lote_xlsx
)

from apps.pautas.services import obter_disciplinas_pauta_turma
import datetime


from rest_framework.permissions import IsAuthenticated, AllowAny
import unicodedata, re

def _safe_ascii_filename(nome: str) -> str:
    s = unicodedata.normalize('NFKD', str(nome or 'documento')).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9._-]+', '_', s).strip('_')
    return s or 'documento'

def _registrar_log_impressao(escola, request, tipo_documento, descricao):
    try:
        user = getattr(request, 'user', None)
        usuario = user if (user and getattr(user, 'is_authenticated', False)) else None
        LogImpressao.objects.create(
            escola=escola,
            usuario=usuario,
            tipo_documento=tipo_documento,
            descricao=descricao
        )
    except Exception:
        pass


def _obter_aluno_e_escola(request, aluno_id):
    from common.utils.tenant import get_tenant_escola
    from django.core.exceptions import PermissionDenied
    escola = get_tenant_escola(request)
    aluno = Aluno.objects.select_related('turma', 'escola').filter(id=aluno_id).first()
    if not aluno:
        aluno = get_object_or_404(Aluno, id=aluno_id)
    if escola and aluno.escola_id != escola.id:
        raise PermissionDenied("Acesso negado: o estudante pertence a outra instituição de ensino.")
    return aluno, (escola or aluno.escola)


def _obter_turma_e_escola(request, turma_id):
    from common.utils.tenant import get_tenant_escola
    from django.core.exceptions import PermissionDenied
    escola = get_tenant_escola(request)
    turma = Turma.objects.select_related('escola', 'director_turma').filter(id=turma_id).first()
    if not turma:
        turma = get_object_or_404(Turma, id=turma_id)
    if escola and turma.escola_id != escola.id:
        raise PermissionDenied("Acesso negado: a turma pertence a outra instituição de ensino.")
    return turma, (escola or turma.escola)


def _obter_pagamento_e_escola(request, pagamento_id):
    from common.utils.tenant import get_tenant_escola
    from rest_framework.exceptions import PermissionDenied, NotFound
    escola = get_tenant_escola(request)

    pagamento = Pagamento.objects.select_related('aluno', 'aluno__turma', 'escola').filter(id=pagamento_id).first()
    if not pagamento:
        pagamento = Pagamento.objects.select_related('aluno', 'aluno__turma', 'escola').filter(aluno_id=pagamento_id).order_by('-status', '-data_pagamento', '-created_at').first()

    if pagamento:
        if escola and pagamento.escola_id != escola.id:
            raise PermissionDenied("Acesso negado: o registo financeiro pertence a outra instituição de ensino.")
        return pagamento, (escola or pagamento.escola)

    # Fallback final: se for um Aluno válido sem pagamentos registados, sintetizar comprovativo padrão
    aluno = Aluno.objects.select_related('turma', 'escola').filter(id=pagamento_id).first()
    if aluno:
        if escola and aluno.escola_id != escola.id:
            raise PermissionDenied("Acesso negado: o estudante pertence a outra instituição de ensino.")
        pagamento_sintetico = Pagamento(
            id=aluno.id,
            escola=aluno.escola or escola,
            aluno=aluno,
            descricao='Propina / Mensalidade Escolar',
            valor=1500,
            valor_pago=1500,
            mes_referencia=datetime.date.today().strftime('%m/%Y'),
            data_vencimento=datetime.date.today(),
            data_pagamento=datetime.date.today(),
            status='PAGO',
            metodo_pagamento='MPESA',
            recibo_numero=f"REC-{aluno.matricula or str(aluno.id)[:8].upper()}"
        )
        pagamento_sintetico.created_at = datetime.datetime.now()
        return pagamento_sintetico, (aluno.escola or escola)

    raise NotFound("Registo de pagamento não encontrado.")


def obter_dados_boletim_aluno(aluno, escola, disciplinas_prefetched=None, notas_prefetched=None):
    from apps.pautas.services import identificar_materia_canonica, turma_tem_exame
    from apps.notas.models import NotaExame
    from .services.pdf_service import match_disciplina

    if notas_prefetched is not None:
        notas = notas_prefetched
    else:
        notas = list(Nota.objects.filter(aluno=aluno).select_related('disciplina'))

    # Carregar notas de exame do aluno para integração mandatória com Certificado e Declaração
    notas_exame_list = list(NotaExame.objects.filter(aluno=aluno).select_related('disciplina'))
    tem_regime_exame = turma_tem_exame(getattr(aluno, 'turma', None), escola)

    # Carregar estritamente as disciplinas do plano curricular da classe e secção/área que o aluno estuda
    plano_curricular = obter_disciplinas_plano_curricular(aluno, escola)

    # Se existirem disciplinas pré-carregadas da turma, usar apenas para enriquecer IDs sem sair do plano curricular da área do aluno
    disc_db_map = {}
    if disciplinas_prefetched:
        for d_obj in disciplinas_prefetched:
            mk = identificar_materia_canonica(d_obj)
            if mk:
                disc_db_map[mk] = d_obj

    dados_disc = []
    for item_plano in plano_curricular:
        nome_disc = item_plano['nome']
        cod_disc = item_plano.get('codigo', '')

        class _DummyDisc:
            def __init__(self, nome, codigo):
                self.nome = nome
                self.codigo = codigo

        mat_canon = identificar_materia_canonica(_DummyDisc(nome_disc, cod_disc))
        d_db = disc_db_map.get(mat_canon) if mat_canon else None

        def extrair_nota(per):
            for n in notas:
                if n.periodo == per and n.disciplina:
                    n_mat = identificar_materia_canonica(n.disciplina)
                    bate = False
                    if d_db and n.disciplina_id == d_db.id:
                        bate = True
                    elif mat_canon and n_mat and (mat_canon == n_mat or {mat_canon, n_mat} == {'MAT', 'MATA'}):
                        bate = True
                    elif match_disciplina(nome_disc, n.disciplina.nome):
                        bate = True

                    if bate:
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
            media_freq = int(round(m_val))
        else:
            media_freq = None

        # Procurar NotaExame desta disciplina
        ne_encontrada = None
        for ne in notas_exame_list:
            if ne.disciplina:
                ne_canon = identificar_materia_canonica(ne.disciplina)
                if d_db and ne.disciplina_id == d_db.id:
                    ne_encontrada = ne
                    break
                elif mat_canon and ne_canon and (mat_canon == ne_canon or {mat_canon, ne_canon} == {'MAT', 'MATA'}):
                    ne_encontrada = ne
                    break
                elif match_disciplina(nome_disc, ne.disciplina.nome):
                    ne_encontrada = ne
                    break

        # Regra de negócio mandatória:
        # Em classes/níveis com regime de exame, a nota oficial no Certificado e na Declaração
        # sai directamente da Pauta de Exames (se houver nota final de exame/frequência).
        if ne_encontrada and ne_encontrada.nota_final is not None:
            media_anual = int(round(ne_encontrada.nota_final))
            situacao = 'Aprovado' if media_anual >= 9.5 else 'Reprovado'
        elif ne_encontrada and ne_encontrada.nota_frequencia is not None:
            media_anual = int(round(ne_encontrada.nota_frequencia))
            situacao = 'Aprovado' if media_anual >= 9.5 else 'Reprovado'
        elif media_freq is not None:
            media_anual = media_freq
            situacao = 'Aprovado' if media_anual >= 9.5 else 'Reprovado'
        else:
            media_anual = '-'
            situacao = 'Pendente'

        dados_disc.append({
            'nome': nome_disc,
            'disciplina': nome_disc,
            'codigo': cod_disc,
            't1': n1,
            't2': n2,
            't3': n3,
            'frequencia': media_freq if media_freq is not None else '-',
            'exame_1epoca': getattr(ne_encontrada, 'exame_1epoca', None) if ne_encontrada else None,
            'exame_2epoca': getattr(ne_encontrada, 'exame_2epoca', None) if ne_encontrada else None,
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

def montar_payload_certificado(aluno, escola, dados_disc, media_global, avaliacao, usuario=None, cert_prefetched=None):
    codigo_inst = getattr(escola, 'codigo_escola', None) or f"ESC-{str(escola.id)[:4].upper()}"
    grau_ano_str = (aluno.turma.grau_ano if aluno.turma else aluno.classe) or '12ª Classe'
    area_str = (aluno.turma.area if aluno.turma else aluno.area) or 'Ciências e Letras'

    cert = cert_prefetched
    if not cert:
        cert = Certificado.objects.filter(escola=escola, aluno=aluno, tipo='CONCLUSAO').first()
    if not cert:
        codigo_auth = f"CERT-{uuid.uuid4().hex[:10].upper()}"
        domain_base = os.environ.get('SIGE_PUBLIC_URL', 'https://sigesaas.duckdns.org').rstrip('/')
        qr_url = f"{domain_base}/verificar-certificado.html?codigo={codigo_auth}"
        cert = Certificado.objects.create(
            escola=escola,
            aluno=aluno,
            tipo='CONCLUSAO',
            codigo_autenticidade=codigo_auth,
            qrcode_data=qr_url,
            emitido_por=usuario.nome if (usuario and hasattr(usuario, 'nome')) else 'Secretaria'
        )

    qr_img_b64 = cert.qrcode_data or ''
    if not str(qr_img_b64).startswith('data:image/'):
        try:
            import base64
            from apps.documentos.services.pdf_service import gerar_qr_code_image
            domain_base = os.environ.get('SIGE_PUBLIC_URL', 'https://sigesaas.duckdns.org').rstrip('/')
            url_verif = f"{domain_base}/verificar-certificado.html?codigo={cert.codigo_autenticidade}"
            qr_buf = gerar_qr_code_image(url_verif)
            qr_img_b64 = f"data:image/png;base64,{base64.b64encode(qr_buf.getvalue()).decode('ascii')}"
        except Exception:
            pass

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
        'codigoAutenticidade': cert.codigo_autenticidade,
        'qrcode_data': qr_img_b64,
        'qrcodeData': qr_img_b64,
        'certificado': {
            'aluno': aluno.nome,
            'matricula': aluno.matricula,
            'turma': aluno.turma.nome if aluno.turma else '',
            'escola': escola.nome,
            'codigo_autenticidade': cert.codigo_autenticidade,
            'codigoAutenticidade': cert.codigo_autenticidade
        }
    }

def calcular_desempenho_documento(dados_disc, grau_ano=None, tipo='BOLETIM'):
    total_disc = len(dados_disc)
    vals = [d['media_anual'] for d in dados_disc if isinstance(d.get('media_anual'), (int, float))]

    if tipo in ['BOLETIM', 'DECLARACAO']:
        media_global = round(sum(vals) / len(vals), 1) if vals else '-'
        if vals:
            avaliacao = avaliar_aprovacao_pauta(
                [{'disciplina': d['nome'], 'notaFinal': d['media_anual']} for d in dados_disc if isinstance(d.get('media_anual'), (int, float))],
                grau_ano
            )
        else:
            avaliacao = {'aprovado': False, 'resultado': 'Pendente', 'siglaResultado': '-', 'mediaGeral': '-'}
        return media_global, avaliacao

    # Para CERTIFICADO (Conclusão Oficial):
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
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, avaliacao = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='BOLETIM'
        )

        _registrar_log_impressao(escola, request, 'BOLETIM', f"Consulta de Boletim de {aluno.nome}")

        dados_boletim = montar_payload_boletim(aluno, escola, dados_disc, media_global, avaliacao)

        return Response({
            'success': True,
            'data': dados_boletim,
            **dados_boletim
        })

class BoletimPDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        orientacao = request.query_params.get('orientacao', 'portrait')

        pdf_bytes = gerar_boletim_pdf(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            orientacao=orientacao
        )

        _registrar_log_impressao(escola, request, 'BOLETIM', f"Emissão PDF de Boletim de {aluno.nome}")

        fname = _safe_ascii_filename(f"Boletim_{aluno.matricula or aluno.id}.pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class BoletimDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        orientacao = request.query_params.get('orientacao', 'portrait')

        docx_bytes = gerar_boletim_docx(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            orientacao=orientacao
        )

        fname = _safe_ascii_filename(f"Boletim_{aluno.matricula or aluno.id}.docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class BoletimXLSXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        orientacao = request.query_params.get('orientacao', 'portrait')

        xlsx_bytes = gerar_boletim_xlsx(
            aluno=aluno,
            escola=escola,
            ano_letivo=escola.ano_letivo_ativo or '2026',
            notas_disciplinas=dados_disc,
            orientacao=orientacao
        )

        fname = _safe_ascii_filename(f"Boletim_{aluno.matricula or aluno.id}.xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class DeclaracaoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
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
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
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

        _registrar_log_impressao(escola, request, 'DECLARACAO', f"Emissão PDF de Declaração de {aluno.nome}")

        fname = _safe_ascii_filename(f"Declaracao_{aluno.matricula or aluno.id}.pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class DeclaracaoDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
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

        fname = _safe_ascii_filename(f"Declaracao_{aluno.matricula or aluno.id}.docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class DeclaracaoXLSXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
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

        fname = _safe_ascii_filename(f"Declaracao_{aluno.matricula or aluno.id}.xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class CertificadoImpressaoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
        dados_disc = obter_dados_boletim_aluno(aluno, escola)
        media_global, avaliacao = calcular_desempenho_documento(
            dados_disc, aluno.turma.grau_ano if aluno.turma else None, tipo='CERTIFICADO'
        )

        dados_cert = montar_payload_certificado(aluno, escola, dados_disc, media_global, avaliacao, getattr(request, 'user', None))

        _registrar_log_impressao(escola, request, 'CERTIFICADO', f"Consulta de Certificado de {aluno.nome}")

        return Response({
            'success': True,
            'data': dados_cert,
            'certificado': dados_cert,
            **dados_cert
        })

class CertificadoPDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
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

        _registrar_log_impressao(escola, request, 'CERTIFICADO', f"Emissão PDF de Certificado de {aluno.nome}")

        fname = _safe_ascii_filename(f"Certificado_{aluno.matricula or aluno.id}.pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class CertificadoDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
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

        fname = _safe_ascii_filename(f"Certificado_{aluno.matricula or aluno.id}.docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class CertificadoXLSXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
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

        fname = _safe_ascii_filename(f"Certificado_{aluno.matricula or aluno.id}.xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

def _compilar_documentos_lote(request, turma, escola, tipo):
    alunos = list(Aluno.objects.filter(turma=turma, status='ATIVO').select_related('turma').order_by('nome'))
    disciplinas_turma = obter_disciplinas_pauta_turma(turma)
    todas_notas = list(Nota.objects.filter(aluno__in=alunos).select_related('disciplina'))
    notas_por_aluno = {}
    for n in todas_notas:
        notas_por_aluno.setdefault(n.aluno_id, []).append(n)

    certs_por_aluno = {}
    if tipo == 'CERTIFICADO' and alunos:
        for c in Certificado.objects.filter(escola=escola, aluno__in=alunos, tipo='CONCLUSAO'):
            certs_por_aluno[c.aluno_id] = c

    documentos = []
    for aluno in alunos:
        aluno.turma = turma
        dados_disc = obter_dados_boletim_aluno(
            aluno,
            escola,
            disciplinas_prefetched=disciplinas_turma,
            notas_prefetched=notas_por_aluno.get(aluno.id, [])
        )
        media_global, avaliacao = calcular_desempenho_documento(
            dados_disc, turma.grau_ano, tipo=tipo
        )
        if tipo == 'DECLARACAO':
            doc = montar_payload_declaracao(aluno, escola, dados_disc, media_global, avaliacao)
        elif tipo == 'CERTIFICADO':
            doc = montar_payload_certificado(
                aluno, escola, dados_disc, media_global, avaliacao,
                getattr(request, 'user', None), cert_prefetched=certs_por_aluno.get(aluno.id)
            )
        else:
            doc = montar_payload_boletim(aluno, escola, dados_disc, media_global, avaliacao)
        documentos.append(doc)
    return documentos

class LoteImpressaoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()
        documentos = _compilar_documentos_lote(request, turma, escola, tipo)

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
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()
        orientacao = request.query_params.get('orientacao', 'portrait')
        documentos = _compilar_documentos_lote(request, turma, escola, tipo)

        xlsx_bytes = gerar_lote_xlsx(turma, escola, tipo, documentos, orientacao=orientacao)
        fname = _safe_ascii_filename(f"Lote_{tipo}_{turma.nome}.xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class LotePDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()
        orientacao = request.query_params.get('orientacao', 'portrait')
        documentos = _compilar_documentos_lote(request, turma, escola, tipo)

        pdf_bytes = gerar_lote_pdf(turma, escola, tipo, documentos, orientacao=orientacao)
        fname = _safe_ascii_filename(f"Lote_{tipo}_{turma.nome}.pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class LoteDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()
        orientacao = request.query_params.get('orientacao', 'portrait')
        documentos = _compilar_documentos_lote(request, turma, escola, tipo)

        docx_bytes = gerar_lote_docx(turma, escola, tipo, documentos, orientacao=orientacao)
        fname = _safe_ascii_filename(f"Lote_{tipo}_{turma.nome}.docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class ReciboImpressaoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pagamento_id):
        pagamento, escola = _obter_pagamento_e_escola(request, pagamento_id)
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
    permission_classes = [AllowAny]

    def get(self, request, pagamento_id):
        pagamento, escola = _obter_pagamento_e_escola(request, pagamento_id)
        orientacao = request.query_params.get('orientacao', 'portrait')

        pdf_bytes = gerar_recibo_pdf(pagamento, escola, orientacao=orientacao)
        fname = _safe_ascii_filename(f"Recibo_{pagamento.id}.pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class ReciboDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pagamento_id):
        pagamento, escola = _obter_pagamento_e_escola(request, pagamento_id)
        orientacao = request.query_params.get('orientacao', 'portrait')

        docx_bytes = gerar_recibo_docx(pagamento, escola, orientacao=orientacao)
        fname = _safe_ascii_filename(f"Recibo_{pagamento.id}.docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class FichaAlunoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)

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
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
        orientacao = request.query_params.get('orientacao', 'portrait')

        pdf_bytes = gerar_ficha_pdf(aluno, escola, orientacao=orientacao)
        fname = _safe_ascii_filename(f"Ficha_{aluno.matricula or aluno.id}.pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class FichaDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
        orientacao = request.query_params.get('orientacao', 'portrait')

        docx_bytes = gerar_ficha_docx(aluno, escola, orientacao=orientacao)
        fname = _safe_ascii_filename(f"Ficha_{aluno.matricula or aluno.id}.docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response


