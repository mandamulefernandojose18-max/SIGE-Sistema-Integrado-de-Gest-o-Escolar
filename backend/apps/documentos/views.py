from rest_framework import permissions
import os
import json
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

import zipfile
import io
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
    gerar_ficha_pdf, gerar_recibo_pdf, gerar_lote_pdf,
    gerar_lote_mapa_pdf, gerar_documento_individual_pdf
)
from .services.docx_service import (
    gerar_boletim_docx, gerar_declaracao_docx, gerar_certificado_docx,
    gerar_ficha_docx, gerar_recibo_docx, gerar_lote_docx,
    gerar_lote_mapa_docx, gerar_documento_individual_docx
)
from .services.excel_service import (
    gerar_boletim_xlsx, gerar_declaracao_xlsx, gerar_certificado_xlsx,
    gerar_lote_xlsx
)

from apps.pautas.services import obter_disciplinas_pauta_turma
import datetime


from rest_framework.permissions import IsAuthenticated, AllowAny
import unicodedata, re, urllib.parse

def _sanitizar_para_nome_arquivo(texto: str) -> str:
    if not texto:
        return ""
    s = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', ' ', s)
    s = re.sub(r'[^A-Za-z0-9 ._\-]+', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip(' .-_')

def _obter_nome_completo_aluno(aluno) -> str:
    if not aluno:
        return "Estudante"
    nome = (getattr(aluno, 'nome', '') or '').strip()
    apelido = (getattr(aluno, 'apelido', '') or '').strip()
    if apelido and apelido.lower() not in nome.lower():
        nome_completo = f"{nome} {apelido}".strip()
    else:
        nome_completo = nome or "Estudante"
    return _sanitizar_para_nome_arquivo(nome_completo) or "Estudante"

def _obter_ano_letivo_documento(aluno=None, escola=None, pagamento=None) -> str:
    if aluno and getattr(aluno, 'turma', None) and getattr(aluno.turma, 'ano_letivo', None):
        ano_turma = str(aluno.turma.ano_letivo).strip()
        if ano_turma:
            return _sanitizar_para_nome_arquivo(ano_turma)
    if pagamento and getattr(pagamento, 'mes_referencia', None):
        partes = str(pagamento.mes_referencia).strip().split('/')
        if len(partes) == 2 and len(partes[1]) == 4:
            return partes[1]
    if aluno and getattr(aluno, 'ano_ingresso', None):
        ano_ing = str(aluno.ano_ingresso).strip()
        if ano_ing:
            return _sanitizar_para_nome_arquivo(ano_ing)
    if escola and getattr(escola, 'ano_letivo_ativo', None):
        ano_esc = str(escola.ano_letivo_ativo).strip()
        if ano_esc:
            return _sanitizar_para_nome_arquivo(ano_esc)
    return str(datetime.date.today().year)

def _gerar_nome_documento_aluno(tipo_doc: str, aluno, ano: str = None, extensao: str = "pdf") -> str:
    tipo_sanitizado = _sanitizar_para_nome_arquivo(tipo_doc) or "Documento"
    aluno_sanitizado = _obter_nome_completo_aluno(aluno)
    ano_sanitizado = _sanitizar_para_nome_arquivo(str(ano or datetime.date.today().year))
    ext = extensao.lstrip('.').lower()
    return f"{tipo_sanitizado} - {aluno_sanitizado} - {ano_sanitizado}.{ext}"

def _safe_ascii_filename(nome: str) -> str:
    return _sanitizar_para_nome_arquivo(nome) or 'documento'

def _definir_content_disposition(response: HttpResponse, nome_arquivo: str) -> HttpResponse:
    nome_quoted = nome_arquivo.replace('"', '')
    nome_encoded = urllib.parse.quote(nome_arquivo)
    response['Content-Disposition'] = f'attachment; filename="{nome_quoted}"; filename*=UTF-8\'\'{nome_encoded}'
    return response

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
            valor_pago=0,
            mes_referencia=datetime.date.today().strftime('%m/%Y'),
            data_vencimento=datetime.date.today(),
            data_pagamento=None,
            status='PENDENTE',
            metodo_pagamento='Pendente de Liquidação',
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
        'resultadoOficial': avaliacao.get('resultado', 'Pendente') if isinstance(avaliacao, dict) else (str(avaliacao) if avaliacao else 'Pendente'),
        'resultadoFinal': avaliacao.get('resultado', 'Pendente') if isinstance(avaliacao, dict) else (str(avaliacao) if avaliacao else 'Pendente'),
        'situacaoGlobal': avaliacao.get('resultado', 'Pendente') if isinstance(avaliacao, dict) else (str(avaliacao) if avaliacao else 'Pendente'),
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
        'resultadoFinal': avaliacao.get('resultado', 'Pendente') if isinstance(avaliacao, dict) else (str(avaliacao) if avaliacao else 'Pendente'),
        'situacaoGlobal': avaliacao.get('resultado', 'Pendente') if isinstance(avaliacao, dict) else (str(avaliacao) if avaliacao else 'Pendente'),
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

        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Boletim", aluno, ano_doc, "pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        _definir_content_disposition(response, fname)
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

        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Boletim", aluno, ano_doc, "docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        _definir_content_disposition(response, fname)
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

        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Boletim", aluno, ano_doc, "xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        _definir_content_disposition(response, fname)
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

        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Declaracao", aluno, ano_doc, "pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        _definir_content_disposition(response, fname)
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

        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Declaracao", aluno, ano_doc, "docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        _definir_content_disposition(response, fname)
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

        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Declaracao", aluno, ano_doc, "xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        _definir_content_disposition(response, fname)
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

        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Certificado", aluno, ano_doc, "pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        _definir_content_disposition(response, fname)
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

        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Certificado", aluno, ano_doc, "docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        _definir_content_disposition(response, fname)
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

        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Certificado", aluno, ano_doc, "xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        _definir_content_disposition(response, fname)
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

    pagamentos_por_aluno = {}
    if tipo == 'RECIBO' and alunos:
        try:
            for p in Pagamento.objects.filter(aluno__in=alunos).order_by('-data_pagamento', '-created_at'):
                if p.aluno_id not in pagamentos_por_aluno:
                    pagamentos_por_aluno[p.aluno_id] = p
        except Exception:
            pass

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
        elif tipo == 'FICHA':
            doc = {
                'id': str(aluno.id),
                'aluno': {
                    'id': str(aluno.id),
                    'nome': aluno.nome,
                    'nomeCompleto': f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip(),
                    'matricula': aluno.matricula,
                    'classe': getattr(turma, 'grau_ano', '10ª Classe'),
                    'turma': turma.nome,
                    'turno': getattr(turma, 'turno', 'Diurno'),
                    'dataNascimento': str(aluno.data_nascimento or '---'),
                    'pai': getattr(aluno, 'pai', '---'),
                    'mae': getattr(aluno, 'mae', '---'),
                },
                'tipo': 'FICHA',
                'mediaGlobal': media_global,
                'situacaoGlobal': avaliacao.get('resultado', 'Pendente') if isinstance(avaliacao, dict) else (str(avaliacao) if avaliacao else 'Pendente'),
                'resultadoFinal': avaliacao.get('resultado', 'Pendente') if isinstance(avaliacao, dict) else (str(avaliacao) if avaliacao else 'Pendente'),
                'avaliacao': avaliacao,
            }
        elif tipo == 'RECIBO':
            pag_obj = pagamentos_por_aluno.get(aluno.id)
            doc = {
                'id': str(aluno.id),
                'aluno': {
                    'id': str(aluno.id),
                    'nome': aluno.nome,
                    'nomeCompleto': f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip(),
                    'matricula': aluno.matricula,
                    'classe': getattr(turma, 'grau_ano', '10ª Classe'),
                    'turma': turma.nome,
                },
                'tipo': 'RECIBO',
                'mediaGlobal': media_global,
                'situacaoGlobal': avaliacao.get('resultado', 'Pendente') if isinstance(avaliacao, dict) else (str(avaliacao) if avaliacao else 'Pendente'),
                'resultadoFinal': avaliacao.get('resultado', 'Pendente') if isinstance(avaliacao, dict) else (str(avaliacao) if avaliacao else 'Pendente'),
                'avaliacao': avaliacao,
                '_pagamento_obj': pag_obj
            }
        else:
            doc = montar_payload_boletim(aluno, escola, dados_disc, media_global, avaliacao)

        doc['_aluno_obj'] = aluno
        doc['_dados_disc'] = dados_disc
        documentos.append(doc)
    return documentos

class LoteImpressaoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()
        documentos = _compilar_documentos_lote(request, turma, escola, tipo)

        # Sanitiza documentos para resposta JSON (remove instâncias de modelos internos)
        docs_json = []
        for d in documentos:
            docs_json.append({k: v for k, v in d.items() if not k.startswith('_')})

        retorno = {
            'success': True,
            'tipoDocumento': tipo,
            'total': len(docs_json),
            'documentos': docs_json
        }
        retorno['data'] = {
            'tipoDocumento': tipo,
            'total': len(docs_json),
            'documentos': docs_json
        }
        return Response(retorno)

class LoteXLSXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()
        orientacao = request.query_params.get('orientacao', 'portrait')
        ano_doc = turma.ano_letivo or (getattr(escola, 'ano_letivo_ativo', None) if escola else None) or str(datetime.date.today().year)

        if tipo == 'PAUTA_EXAME':
            from apps.pautas.services import consolidar_pauta_exames
            from apps.documentos.services.excel_service import gerar_pauta_exames_xlsx
            dados_exame = consolidar_pauta_exames(turma, ano_letivo=ano_doc)
            xlsx_bytes = gerar_pauta_exames_xlsx(dados_exame, escola or turma.escola, ano_letivo=ano_doc, orientacao=orientacao)
            fname = f"Pauta_Exames_{_sanitizar_para_nome_arquivo(turma.nome)}_{ano_doc}.xlsx"
            response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            _definir_content_disposition(response, fname)
            return response
        documentos = _compilar_documentos_lote(request, turma, escola, tipo)

        xlsx_bytes = gerar_lote_xlsx(turma, escola, tipo, documentos, orientacao=orientacao)
        ano_doc = turma.ano_letivo or escola.ano_letivo_ativo or str(datetime.date.today().year)
        tipo_lbl = "Boletins" if tipo == 'BOLETIM' else ("Declaracoes" if tipo == 'DECLARACAO' else ("Certificados" if tipo == 'CERTIFICADO' else tipo.capitalize()))
        fname = f"{tipo_lbl} - {turma.nome} - {ano_doc}.xlsx"
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        _definir_content_disposition(response, fname)
        return response

class LotePDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()
        orientacao = request.query_params.get('orientacao', 'portrait')
        ano_doc = turma.ano_letivo or (getattr(escola, 'ano_letivo_ativo', None) if escola else None) or str(datetime.date.today().year)

        if tipo == 'PAUTA_EXAME':
            from apps.pautas.services import consolidar_pauta_exames
            from apps.documentos.services.pdf_service import gerar_pauta_exames_pdf
            dados_exame = consolidar_pauta_exames(turma, ano_letivo=ano_doc)
            pdf_bytes = gerar_pauta_exames_pdf(dados_exame, escola or turma.escola, ano_letivo=ano_doc, orientacao=orientacao)
            fname = f"Pauta_Exames_{_sanitizar_para_nome_arquivo(turma.nome)}_{ano_doc}.pdf"
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            _definir_content_disposition(response, fname)
            return response
        documentos = _compilar_documentos_lote(request, turma, escola, tipo)

        pdf_bytes = gerar_lote_pdf(turma, escola, tipo, documentos, orientacao=orientacao)
        ano_doc = turma.ano_letivo or escola.ano_letivo_ativo or str(datetime.date.today().year)
        tipo_lbl = "Boletins" if tipo == 'BOLETIM' else ("Declaracoes" if tipo == 'DECLARACAO' else ("Certificados" if tipo == 'CERTIFICADO' else tipo.capitalize()))
        fname = f"{tipo_lbl} - {turma.nome} - {ano_doc}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        _definir_content_disposition(response, fname)
        return response

class LoteDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()
        orientacao = request.query_params.get('orientacao', 'portrait')
        ano_doc = turma.ano_letivo or (getattr(escola, 'ano_letivo_ativo', None) if escola else None) or str(datetime.date.today().year)

        if tipo == 'PAUTA_EXAME':
            from apps.pautas.services import consolidar_pauta_exames
            from apps.documentos.services.docx_service import gerar_pauta_exames_docx
            dados_exame = consolidar_pauta_exames(turma, ano_letivo=ano_doc)
            docx_bytes = gerar_pauta_exames_docx(dados_exame, escola or turma.escola, ano_letivo=ano_doc, orientacao=orientacao)
            fname = f"Pauta_Exames_{_sanitizar_para_nome_arquivo(turma.nome)}_{ano_doc}.docx"
            response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            _definir_content_disposition(response, fname)
            return response
        documentos = _compilar_documentos_lote(request, turma, escola, tipo)

        docx_bytes = gerar_lote_docx(turma, escola, tipo, documentos, orientacao=orientacao)
        ano_doc = turma.ano_letivo or escola.ano_letivo_ativo or str(datetime.date.today().year)
        tipo_lbl = "Boletins" if tipo == 'BOLETIM' else ("Declaracoes" if tipo == 'DECLARACAO' else ("Certificados" if tipo == 'CERTIFICADO' else tipo.capitalize()))
        fname = f"{tipo_lbl} - {turma.nome} - {ano_doc}.docx"
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        _definir_content_disposition(response, fname)
        return response

class LoteZIPView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        tipo = request.query_params.get('tipo', 'BOLETIM').upper()
        orientacao = request.query_params.get('orientacao', 'portrait')
        ano_doc = turma.ano_letivo or (getattr(escola, 'ano_letivo_ativo', None) if escola else None) or str(datetime.date.today().year)

        if tipo == 'PAUTA_EXAME':
            from apps.pautas.services import consolidar_pauta_exames
            from apps.documentos.services.pdf_service import gerar_pauta_exames_pdf
            from apps.documentos.services.excel_service import gerar_pauta_exames_xlsx
            from apps.documentos.services.docx_service import gerar_pauta_exames_docx

            dados_exame = consolidar_pauta_exames(turma, ano_letivo=ano_doc)
            safe_t = _sanitizar_para_nome_arquivo(turma.nome)

            pdf_b = gerar_pauta_exames_pdf(dados_exame, escola or turma.escola, ano_letivo=ano_doc, orientacao='landscape')
            xlsx_b = gerar_pauta_exames_xlsx(dados_exame, escola or turma.escola, ano_letivo=ano_doc, orientacao='landscape')
            docx_b = gerar_pauta_exames_docx(dados_exame, escola or turma.escola, ano_letivo=ano_doc, orientacao='landscape')

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr(f"Pauta_Exames_{safe_t}_{ano_doc}.pdf", pdf_b)
                zip_file.writestr(f"Pauta_Exames_{safe_t}_{ano_doc}.xlsx", xlsx_b)
                zip_file.writestr(f"Pauta_Exames_{safe_t}_{ano_doc}.docx", docx_b)

            zip_buffer.seek(0)
            fname = f"PACOTE_PAUTA_EXAMES_{safe_t}_{ano_doc}.zip"
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            _definir_content_disposition(response, fname)
            return response

        documentos = _compilar_documentos_lote(request, turma, escola, tipo)
        tipo_lbl = "Boletins" if tipo == 'BOLETIM' else ("Declaracoes" if tipo == 'DECLARACAO' else ("Certificados" if tipo == 'CERTIFICADO' else tipo.capitalize()))

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Mapa Oficial da Lista dos Emitidos em Lote (PDF)
            mapa_bytes = gerar_lote_mapa_pdf(turma, escola, tipo, documentos, orientacao=orientacao)
            mapa_name = f"00_MAPA_OFICIAL_EMISSAO_{tipo}_{_sanitizar_para_nome_arquivo(turma.nome)}.pdf"
            zip_file.writestr(mapa_name, mapa_bytes)

            # 2. Documento Unificado Completo (Lista + Todos os Documentos) (PDF)
            unificado_bytes = gerar_lote_pdf(turma, escola, tipo, documentos, orientacao=orientacao)
            unif_name = f"TODOS_DOCUMENTOS_COMPLETO_{tipo}_{_sanitizar_para_nome_arquivo(turma.nome)}.pdf"
            zip_file.writestr(unif_name, unificado_bytes)

            # 3. Todos os Documentos Individuais de Cada Aluno (PDF)
            for idx, doc_item in enumerate(documentos, start=1):
                al_info = doc_item.get('aluno') or {}
                nome_aluno = _sanitizar_para_nome_arquivo(al_info.get('nomeCompleto') or al_info.get('nome') or f"Aluno_{idx}")
                mat = _sanitizar_para_nome_arquivo(al_info.get('matricula') or str(idx))
                doc_bytes = gerar_documento_individual_pdf(tipo, doc_item, turma, escola, orientacao=orientacao)
                doc_name = f"documentos_individuais/{idx:02d}_{tipo}_{nome_aluno}_{mat}.pdf"
                zip_file.writestr(doc_name, doc_bytes)

        zip_buffer.seek(0)
        fname = f"PACOTE_LOTE_{tipo_lbl}_{_sanitizar_para_nome_arquivo(turma.nome)}_{ano_doc}.zip"
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        _definir_content_disposition(response, fname)
        return response

class ReciboImpressaoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pagamento_id):
        pagamento, escola = _obter_pagamento_e_escola(request, pagamento_id)
        aluno = pagamento.aluno

        status_raw = str(getattr(pagamento, 'status', '')).upper().strip()
        valor_pago_val = float(getattr(pagamento, 'valor_pago', 0) or 0)
        tem_data_pag = bool(getattr(pagamento, 'data_pagamento', None))
        is_pago = (status_raw == 'PAGO') and (tem_data_pag or valor_pago_val > 0)

        status_texto = 'PAGO' if is_pago else 'NÃO PAGO'
        status_badge = 'success' if is_pago else 'danger'
        valor_liquidado_str = str(getattr(pagamento, 'valor_pago', None) or pagamento.valor) if is_pago else '0.00'
        metodo_str = (pagamento.metodo_pagamento or 'MPESA') if is_pago else 'Pendente de Liquidação'
        data_pag_str = str(pagamento.data_pagamento or pagamento.created_at)[:10] if is_pago else 'Aguardando Liquidação'

        from .services.numero_extenso import numero_para_extenso_meticais, formatar_valor_com_extenso
        valor_extenso = numero_para_extenso_meticais(pagamento.valor)
        valor_com_extenso = formatar_valor_com_extenso(pagamento.valor, 'MT')
        if is_pago:
            val_liq_obj = getattr(pagamento, 'valor_pago', None) or pagamento.valor
            valor_pago_extenso = numero_para_extenso_meticais(val_liq_obj)
            valor_pago_com_extenso = formatar_valor_com_extenso(val_liq_obj, 'MT')
        else:
            valor_pago_extenso = 'Zero meticais'
            valor_pago_com_extenso = '0 MT (Zero meticais) — Aguardando Liquidação'

        dados_rec = {
            'valor_extenso': valor_extenso,
            'valor_com_extenso': valor_com_extenso,
            'valor_pago_extenso': valor_pago_extenso,
            'valor_pago_com_extenso': valor_pago_com_extenso,
            'numero': pagamento.recibo_numero or f"REC-{pagamento.id}",
            'is_pago': is_pago,
            'status': status_texto,
            'status_label': status_texto,
            'status_badge': status_badge,
            'aluno': {
                'id': str(aluno.id) if aluno else '',
                'nome': aluno.nome if aluno else '',
                'apelido': aluno.apelido or '' if aluno else '',
                'nome_completo': f"{aluno.nome} {getattr(aluno, 'apelido', '') or ''}".strip().upper() if aluno else '',
                'matricula': aluno.matricula if aluno else '',
                'turma': {
                    'nome': aluno.turma.nome if aluno and aluno.turma else '-',
                    'grau_ano': getattr(aluno.turma, 'grau_ano', '-') if aluno and aluno.turma else '-',
                    'turno': getattr(aluno.turma, 'turno', '-') if aluno and aluno.turma else '-',
                    'sala': getattr(aluno.turma, 'sala', '-') if aluno and aluno.turma else '-',
                } if aluno else None,
                'encarregado': getattr(aluno, 'encarregado_nome', '') or getattr(aluno, 'nome_pai', '') or getattr(aluno, 'nome_mae', '') or '-',
                'telefone': getattr(aluno, 'telefone', '') or getattr(aluno, 'encarregado_telefone', '') or '-'
            },
            'escola': {
                'id': str(escola.id) if escola else '',
                'nome': escola.nome if escola else '',
                'nif_cnpj': getattr(escola, 'nuit', None) or getattr(escola, 'nif_cnpj', '-') or '-',
                'provincia': getattr(escola, 'provincia', '-') or '-',
                'distrito': getattr(escola, 'distrito', '-') or '-',
                'endereco': getattr(escola, 'endereco', '-') or '-',
                'telefone': getattr(escola, 'telefone', '-') or '-',
                'email': getattr(escola, 'email', '-') or '-'
            },
            'pagamento': {
                'id': str(pagamento.id),
                'recibo_numero': pagamento.recibo_numero or f"REC-{pagamento.id}",
                'descricao': pagamento.descricao,
                'mes_referencia': pagamento.mes_referencia,
                'valor': str(pagamento.valor),
                'valor_pago': valor_liquidado_str,
                'is_pago': is_pago,
                'status': status_texto,
                'metodo_pagamento': metodo_str,
                'valor_extenso': valor_extenso,
                'valor_com_extenso': valor_com_extenso,
                'valor_pago_extenso': valor_pago_extenso,
                'valor_pago_com_extenso': valor_pago_com_extenso,
                'data_pagamento': data_pag_str,
                'data_vencimento': str(getattr(pagamento, 'data_vencimento', '') or '')[:10] if getattr(pagamento, 'data_vencimento', None) else '-',
            },
            'carimboDataHora': datetime.datetime.now().strftime('%d/%m/%Y às %H:%M:%S'),
            'descricao': pagamento.descricao,
            'mes': pagamento.mes_referencia,
            'valor': str(pagamento.valor),
            'valor_pago': valor_liquidado_str,
            'metodo': metodo_str,
            'data': data_pag_str
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
        aluno = getattr(pagamento, 'aluno', None)
        ano_doc = _obter_ano_letivo_documento(aluno, escola, pagamento)
        fname = _gerar_nome_documento_aluno("Recibo", aluno, ano_doc, "pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        _definir_content_disposition(response, fname)
        return response

class ReciboDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pagamento_id):
        pagamento, escola = _obter_pagamento_e_escola(request, pagamento_id)
        orientacao = request.query_params.get('orientacao', 'portrait')

        docx_bytes = gerar_recibo_docx(pagamento, escola, orientacao=orientacao)
        aluno = getattr(pagamento, 'aluno', None)
        ano_doc = _obter_ano_letivo_documento(aluno, escola, pagamento)
        fname = _gerar_nome_documento_aluno("Recibo", aluno, ano_doc, "docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        _definir_content_disposition(response, fname)
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
        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Ficha", aluno, ano_doc, "pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        _definir_content_disposition(response, fname)
        return response

class FichaDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, aluno_id):
        aluno, escola = _obter_aluno_e_escola(request, aluno_id)
        orientacao = request.query_params.get('orientacao', 'portrait')

        docx_bytes = gerar_ficha_docx(aluno, escola, orientacao=orientacao)
        ano_doc = _obter_ano_letivo_documento(aluno, escola)
        fname = _gerar_nome_documento_aluno("Ficha", aluno, ano_doc, "docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        _definir_content_disposition(response, fname)
        return response




from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from .models import CalendarioEscolar, ComunicadoEscolar, DocumentoCalendarioOficial
from .serializers import CalendarioEscolarSerializer, ComunicadoEscolarSerializer, DocumentoCalendarioOficialSerializer
from apps.accounts.audit import registrar_auditoria
from apps.tenants.models import Escola
import base64
import csv

def _converter_data_calendario(valor):
    if not valor:
        return None
    if isinstance(valor, datetime.date):
        return valor
    if isinstance(valor, datetime.datetime):
        return valor.date()
    val_str = str(valor).strip()
    if not val_str:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y/%m/%d'):
        try:
            return datetime.datetime.strptime(val_str, fmt).date()
        except Exception:
            pass
    try:
        val_float = float(val_str)
        if 30000 < val_float < 60000:
            base = datetime.date(1899, 12, 30)
            return base + datetime.timedelta(days=int(val_float))
    except Exception:
        pass
    return None

def _mapear_tipo_evento_calendario(texto):
    s = (texto or '').strip().upper()
    if 'EXAME' in s:
        return 'EXAME'
    if 'CONSELHO' in s:
        return 'CONSELHO_TURMA'
    if 'FERIADO' in s or 'PAUSA' in s or 'INTERRUP' in s:
        return 'FERIADO_PAUSA'
    if 'REUNIAO' in s or 'ENCARREGADO' in s or 'PAIS' in s:
        return 'REUNIAO_ENCARREGADOS'
    if 'CULTURAL' in s or 'FESTA' in s or 'EVENTO' in s:
        return 'EVENTO_ESCOLAR'
    return 'AVALIACAO_TESTE'

def _mapear_trimestre_calendario(texto):
    s = (texto or '').strip().upper()
    if '1' in s or 'I ' in s or 'PRIMEIRO' in s:
        return '1_TRIMESTRE'
    if '2' in s or 'II ' in s or 'SEGUNDO' in s:
        return '2_TRIMESTRE'
    if '3' in s or 'III ' in s or 'TERCEIRO' in s:
        return '3_TRIMESTRE'
    return 'GERAL'

class CalendarioEscolarViewSet(viewsets.ModelViewSet):
    queryset = CalendarioEscolar.objects.all()
    serializer_class = CalendarioEscolarSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _obter_escola_requisicao(self, request):
        user = request.user
        role = getattr(user, 'role', '')
        escola = getattr(request, 'tenant', None) or getattr(user, 'escola', None)
        if not escola and role == 'SUPERADMIN':
            escola_id = request.query_params.get('escola_id') or request.data.get('escola_id') or request.headers.get('X-Escola-ID')
            if escola_id:
                escola = Escola.objects.filter(id=escola_id).first()
            if not escola and user.escola:
                escola = user.escola
        return escola

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', '')
        escola = self._obter_escola_requisicao(self.request)
        qs = CalendarioEscolar.objects.all()
        if escola:
            qs = qs.filter(escola=escola)
        elif role != 'SUPERADMIN' and user.escola:
            qs = qs.filter(escola=user.escola)
        elif role != 'SUPERADMIN':
            return CalendarioEscolar.objects.none()

        trimestre = self.request.query_params.get('trimestre')
        if trimestre:
            qs = qs.filter(trimestre=trimestre)
        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs.order_by('data_inicio')

    def perform_create(self, serializer):
        escola = self._obter_escola_requisicao(self.request)
        obj = serializer.save(escola=escola, criado_por=self.request.user)
        registrar_auditoria(self.request.user, escola, 'CALENDARIO', 'CRIACAO', obj.id, f'Evento no calendário: {obj.titulo} ({obj.data_inicio})')

    @action(detail=True, methods=['post'], url_path='aprovar')
    def aprovar(self, request, pk=None):
        role = getattr(request.user, 'role', '')
        if role not in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'] and not getattr(request.user, 'is_superuser', False):
            return Response({'success': False, 'message': 'Aprovação de calendário exclusiva do Director da Escola.'}, status=403)
        obj = self.get_object()
        obj.status_aprovacao = 'APROVADO_DIRECTOR'
        obj.aprovado_por = request.user
        obj.save()
        registrar_auditoria(request.user, obj.escola, 'CALENDARIO', 'APROVACAO', obj.id, f'Aprovação do calendário oficial pelo Director')
        return Response({'success': True, 'message': 'Calendário escolar aprovado com sucesso!', 'data': self.get_serializer(obj).data})

    @action(detail=False, methods=['get'], url_path='documento_oficial')
    def documento_oficial(self, request):
        escola = self._obter_escola_requisicao(request)
        if not escola:
            return Response({'success': False, 'message': 'Escola não identificada.'}, status=400)
        doc = DocumentoCalendarioOficial.objects.filter(escola=escola).order_by('-created_at').first()
        if not doc:
            return Response({'success': True, 'data': None, 'message': 'Nenhum documento oficial carregado ainda.'})
        return Response({'success': True, 'data': DocumentoCalendarioOficialSerializer(doc).data})

    @action(detail=False, methods=['post'], url_path='carregar_documento_oficial')
    def carregar_documento_oficial(self, request):
        escola = self._obter_escola_requisicao(request)
        if not escola:
            return Response({'success': False, 'message': 'Escola não identificada.'}, status=400)
        
        titulo = request.data.get('titulo') or 'Calendário Escolar Oficial'
        ano_lectivo = request.data.get('ano_lectivo') or '2026'
        descricao = request.data.get('descricao') or ''
        
        arquivo = request.FILES.get('documento') or request.FILES.get('arquivo')
        conteudo_base64 = request.data.get('conteudo_base64')
        nome_arquivo = request.data.get('nome_arquivo') or (arquivo.name if arquivo else 'calendario_escolar.pdf')
        extensao = request.data.get('extensao') or 'pdf'
        tipo_mime = request.data.get('tipo_mime') or 'application/pdf'
        tamanho_bytes = int(request.data.get('tamanho_bytes') or 0)

        if arquivo:
            nome_arquivo = arquivo.name
            extensao = nome_arquivo.split('.')[-1].lower() if '.' in nome_arquivo else 'pdf'
            tamanho_bytes = arquivo.size
            tipo_mime = getattr(arquivo, 'content_type', 'application/pdf') or 'application/pdf'
            raw_data = arquivo.read()
            conteudo_base64 = base64.b64encode(raw_data).decode('utf-8')
        elif conteudo_base64:
            if ',' in conteudo_base64:
                prefix, b64_clean = conteudo_base64.split(',', 1)
                conteudo_base64 = b64_clean
                if 'application/pdf' in prefix:
                    tipo_mime = 'application/pdf'
                elif 'vnd.openxmlformats' in prefix or 'spreadsheet' in prefix:
                    tipo_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            if not tamanho_bytes:
                tamanho_bytes = len(conteudo_base64) * 3 // 4
        else:
            return Response({'success': False, 'message': 'Nenhum ficheiro fornecido. Seleccione um ficheiro para carregar.'}, status=400)

        doc = DocumentoCalendarioOficial.objects.create(
            escola=escola,
            titulo=titulo,
            ano_lectivo=ano_lectivo,
            descricao=descricao,
            nome_arquivo=nome_arquivo,
            extensao=extensao,
            tamanho_bytes=tamanho_bytes,
            conteudo_base64=conteudo_base64,
            tipo_mime=tipo_mime,
            publicado_por=request.user
        )
        registrar_auditoria(request.user, escola, 'CALENDARIO', 'UPLOAD_DOC', doc.id, f'Carregamento de documento oficial do calendário: {doc.titulo} ({doc.nome_arquivo})')
        return Response({
            'success': True,
            'message': 'Documento oficial do calendário carregado com sucesso!',
            'data': DocumentoCalendarioOficialSerializer(doc).data
        })

    @action(detail=False, methods=['get'], url_path='download_documento_oficial')
    def download_documento_oficial(self, request):
        escola = self._obter_escola_requisicao(request)
        if not escola:
            return Response({'success': False, 'message': 'Escola não identificada.'}, status=400)
        doc = DocumentoCalendarioOficial.objects.filter(escola=escola).order_by('-created_at').first()
        if not doc or not doc.conteudo_base64:
            return Response({'success': False, 'message': 'Nenhum documento oficial registado para descarregar.'}, status=404)
        
        try:
            b64_clean = doc.conteudo_base64
            if ',' in b64_clean:
                b64_clean = b64_clean.split(',', 1)[1]
            raw_bytes = base64.b64decode(b64_clean)
        except Exception as e:
            return Response({'success': False, 'message': f'Erro ao descodificar ficheiro: {str(e)}'}, status=500)

        resp = HttpResponse(raw_bytes, content_type=doc.tipo_mime or 'application/octet-stream')
        nome_limpo = _sanitizar_para_nome_arquivo(doc.nome_arquivo) or 'calendario_escolar.pdf'
        resp['Content-Disposition'] = f'attachment; filename="{nome_limpo}"'
        return resp

    @action(detail=False, methods=['delete', 'post'], url_path='remover_documento_oficial')
    def remover_documento_oficial(self, request):
        escola = self._obter_escola_requisicao(request)
        if not escola:
            return Response({'success': False, 'message': 'Escola não identificada.'}, status=400)
        docs = DocumentoCalendarioOficial.objects.filter(escola=escola)
        qtd = docs.count()
        docs.delete()
        registrar_auditoria(request.user, escola, 'CALENDARIO', 'REMOCAO_DOC', None, 'Remoção do documento oficial do calendário')
        return Response({'success': True, 'message': f'Documento oficial removido com sucesso ({qtd} registos eliminados).'})

    @action(detail=False, methods=['get'], url_path='modelo_csv')
    def modelo_csv(self, request):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Data Início', 'Data Fim', 'Título do Evento', 'Tipo de Evento', 'Trimestre', 'Descrição'])
        writer.writerow(['2026-02-02', '', 'Abertura Solene do Ano Lectivo 2026', 'EVENTO_ESCOLAR', '1_TRIMESTRE', 'Cerimónia oficial de boas-vindas com professores, encarregados e alunos'])
        writer.writerow(['2026-03-09', '2026-03-13', '1ª Ronda de Avaliações Contínuas (ACS)', 'AVALIACAO_TESTE', '1_TRIMESTRE', 'Semana de realização de ACS em todas as disciplinas'])
        writer.writerow(['2026-04-13', '2026-04-17', 'Realização da ACP do 1º Trimestre', 'AVALIACAO_TESTE', '1_TRIMESTRE', 'Avaliações Periódicas Trimestrais'])
        writer.writerow(['2026-04-20', '2026-04-24', 'Conselhos de Turma do 1º Trimestre', 'CONSELHO_TURMA', '1_TRIMESTRE', 'Reunião de avaliação e validação das notas do 1º Trimestre'])
        writer.writerow(['2026-05-01', '', 'Dia Internacional do Trabalhador', 'FERIADO_PAUSA', 'GERAL', 'Feriado nacional oficial'])
        writer.writerow(['2026-05-18', '', 'Início das Aulas do 2º Trimestre', 'EVENTO_ESCOLAR', '2_TRIMESTRE', 'Retomada lectiva do segundo período'])
        writer.writerow(['2026-06-25', '', 'Dia da Independência Nacional de Moçambique', 'FERIADO_PAUSA', 'GERAL', 'Feriado nacional oficial'])
        writer.writerow(['2026-07-20', '2026-07-24', 'Realização da ACP do 2º Trimestre', 'AVALIACAO_TESTE', '2_TRIMESTRE', 'Provas trimestrais do 2º Trimestre'])
        writer.writerow(['2026-07-27', '2026-07-31', 'Conselhos de Turma do 2º Trimestre', 'CONSELHO_TURMA', '2_TRIMESTRE', 'Lançamento de pautas e deliberação pedagógica'])
        writer.writerow(['2026-08-31', '', 'Início do 3º Trimestre Lectivo', 'EVENTO_ESCOLAR', '3_TRIMESTRE', 'Início das aulas do último trimestre'])
        writer.writerow(['2026-10-19', '2026-10-23', 'Realização da ACP do 3º Trimestre', 'AVALIACAO_TESTE', '3_TRIMESTRE', 'Provas finais dos alunos'])
        writer.writerow(['2026-11-16', '2026-11-27', 'Época Especial e Geral de Exames Nacionais', 'EXAME', '3_TRIMESTRE', 'Exames finais do Ensino Secundário Geral'])
        
        csv_data = output.getvalue()
        resp = HttpResponse(csv_data.encode('utf-8-sig'), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="modelo_calendario_escolar_sige.csv"'
        return resp

    @action(detail=False, methods=['post'], url_path='importar_ficheiro')
    def importar_ficheiro(self, request):
        escola = self._obter_escola_requisicao(request)
        if not escola:
            return Response({'success': False, 'message': 'Escola não identificada.'}, status=400)
        
        lista_linhas = []
        
        eventos_json = request.data.get('eventos')
        if isinstance(eventos_json, list) and len(eventos_json) > 0:
            for item in eventos_json:
                if isinstance(item, dict):
                    lista_linhas.append(item)
        
        arquivo = request.FILES.get('ficheiro') or request.FILES.get('documento')
        conteudo_base64 = request.data.get('conteudo_base64')
        nome_arquivo = request.data.get('nome_arquivo') or (arquivo.name if arquivo else '')
        
        if not lista_linhas and (arquivo or conteudo_base64):
            raw_bytes = None
            if arquivo:
                raw_bytes = arquivo.read()
            elif conteudo_base64:
                b64_clean = conteudo_base64
                if ',' in b64_clean:
                    b64_clean = b64_clean.split(',', 1)[1]
                try:
                    raw_bytes = base64.b64decode(b64_clean)
                except Exception:
                    raw_bytes = None
            
            if raw_bytes:
                ext = nome_arquivo.split('.')[-1].lower() if '.' in nome_arquivo else ''
                if ext in ['xlsx', 'xlsm', 'xltx']:
                    try:
                        import openpyxl
                        wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
                        ws = wb.active
                        rows = list(ws.iter_rows(values_only=True))
                        if rows and len(rows) > 1:
                            headers = [str(h or '').strip().lower() for h in rows[0]]
                            for r in rows[1:]:
                                if not any(r): continue
                                r_dict = {}
                                for i, h in enumerate(headers):
                                    if i < len(r):
                                        r_dict[h] = r[i]
                                lista_linhas.append(r_dict)
                    except Exception as err:
                        return Response({'success': False, 'message': f'Erro ao ler folha Excel: {str(err)}'}, status=400)
                else:
                    try:
                        texto = None
                        for enc in ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252'):
                            try:
                                texto = raw_bytes.decode(enc)
                                break
                            except Exception:
                                pass
                        if texto:
                            primeira_linha = texto.splitlines()[0] if texto.splitlines() else ''
                            delim = ';' if ';' in primeira_linha else (',' if ',' in primeira_linha else '	')
                            reader = csv.reader(io.StringIO(texto), delimiter=delim)
                            csv_rows = list(reader)
                            if csv_rows and len(csv_rows) > 1:
                                headers = [h.strip().lower() for h in csv_rows[0]]
                                for r in csv_rows[1:]:
                                    if not any(c.strip() for c in r if isinstance(c, str)): continue
                                    r_dict = {}
                                    for i, h in enumerate(headers):
                                        if i < len(r):
                                            r_dict[h] = r[i]
                                    lista_linhas.append(r_dict)
                    except Exception as err:
                        return Response({'success': False, 'message': f'Erro ao ler ficheiro CSV: {str(err)}'}, status=400)

        if not lista_linhas:
            return Response({'success': False, 'message': 'Nenhum evento detectado no ficheiro ou dados enviados.'}, status=400)

        criados = []
        erros = []
        for idx, row in enumerate(lista_linhas, start=1):
            titulo = None
            dt_inicio = None
            dt_fim = None
            tipo = None
            trimestre = None
            descricao = ''

            for k, v in row.items():
                if v is None: continue
                val_str = str(v).strip()
                if not val_str: continue
                
                # Normalizar chave sem acentos para mapeamento infalivel
                k_norm = unicodedata.normalize('NFKD', str(k)).encode('ascii', 'ignore').decode('ascii').lower()

                if any(x in k_norm for x in ['titulo', 'evento', 'nome', 'title', 'actividade', 'atividade']):
                    if not titulo: titulo = val_str
                elif any(x in k_norm for x in ['inicio', 'start', 'abertura', 'de']) or 'data' in k_norm and 'fim' not in k_norm:
                    if not dt_inicio: dt_inicio = _converter_data_calendario(v)
                elif any(x in k_norm for x in ['fim', 'end', 'encerramento', 'ate', 'termino']):
                    if not dt_fim: dt_fim = _converter_data_calendario(v)
                elif any(x in k_norm for x in ['tipo', 'categoria', 'classificacao', 'type']):
                    if not tipo: tipo = _mapear_tipo_evento_calendario(val_str)
                elif any(x in k_norm for x in ['trimestre', 'periodo', 'etapa', 'term']):
                    if not trimestre: trimestre = _mapear_trimestre_calendario(val_str)
                elif any(x in k_norm for x in ['desc', 'detalhe', 'obs', 'nota']):
                    descricao = val_str

            if not titulo and len(row) >= 2:
                valores = list(row.values())
                dt_inicio = _converter_data_calendario(valores[0])
                titulo = str(valores[1] or '').strip()
                if len(valores) > 2 and not dt_fim:
                    dt_fim = _converter_data_calendario(valores[2])

            if not titulo:
                erros.append(f'Linha {idx}: título do evento em falta.')
                continue
            if not dt_inicio:
                erros.append(f'Linha {idx} ({titulo}): data de início inválida ou em falta.')
                continue

            tipo_final = tipo or 'AVALIACAO_TESTE'
            trimestre_final = trimestre or 'GERAL'

            ev = CalendarioEscolar.objects.create(
                escola=escola,
                titulo=titulo,
                tipo=tipo_final,
                trimestre=trimestre_final,
                data_inicio=dt_inicio,
                data_fim=dt_fim,
                descricao=descricao,
                status_aprovacao='APROVADO_DIRECTOR',
                criado_por=request.user
            )
            criados.append(ev)

        if not criados:
            return Response({
                'success': False,
                'message': 'Não foi possível importar nenhum evento do ficheiro. Verifique os formatos de data e colunas.',
                'erros': erros[:10]
            }, status=400)

        registrar_auditoria(
            request.user, escola, 'CALENDARIO', 'IMPORTACAO_LOTE', None,
            f'Importação em lote de {len(criados)} eventos para o calendário a partir de documento/ficheiro.'
        )

        return Response({
            'success': True,
            'count': len(criados),
            'erros_contagem': len(erros),
            'message': f'Foram carregados e importados {len(criados)} eventos com sucesso no calendário escolar!',
            'data': CalendarioEscolarSerializer(criados, many=True).data
        })

    @action(detail=True, methods=['get'], url_path='download_anexo')
    def download_anexo(self, request, pk=None):
        obj = self.get_object()
        if not obj.documento_base64:
            return Response({'success': False, 'message': 'Este evento não tem documento anexo.'}, status=404)
        
        try:
            b64_clean = obj.documento_base64
            if ',' in b64_clean:
                b64_clean = b64_clean.split(',', 1)[1]
            raw_bytes = base64.b64decode(b64_clean)
        except Exception as e:
            return Response({'success': False, 'message': f'Erro ao ler anexo: {str(e)}'}, status=500)

        nome = obj.nome_documento or f"anexo_{obj.id}.pdf"
        resp = HttpResponse(raw_bytes, content_type=obj.documento_tipo or 'application/octet-stream')
        resp['Content-Disposition'] = f'attachment; filename="{_sanitizar_para_nome_arquivo(nome)}"'
        return resp

class ComunicadoEscolarViewSet(viewsets.ModelViewSet):
    queryset = ComunicadoEscolar.objects.all()
    serializer_class = ComunicadoEscolarSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', '')
        escola = getattr(self.request, 'tenant', None) or getattr(user, 'escola', None)
        qs = ComunicadoEscolar.objects.all()
        if escola:
            qs = qs.filter(escola=escola)
        elif role != 'SUPERADMIN' and user.escola:
            qs = qs.filter(escola=user.escola)
        elif role != 'SUPERADMIN':
            return ComunicadoEscolar.objects.none()

        if role == 'ALUNO':
            qs = qs.filter(publico_alvo__in=['TODOS', 'ALUNOS'], status='PUBLICADO')
        elif role == 'ENCARREGADO':
            qs = qs.filter(publico_alvo__in=['TODOS', 'ENCARREGADOS'], status='PUBLICADO')
        elif role == 'PROFESSOR':
            qs = qs.filter(publico_alvo__in=['TODOS', 'PROFESSORES'])

        return qs.order_by('-data_publicacao')

    def perform_create(self, serializer):
        escola = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'escola', None)
        role = getattr(self.request.user, 'role', '')
        aprovado = (role in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA']) or getattr(self.request.user, 'is_superuser', False)
        obj = serializer.save(escola=escola, autor=self.request.user, aprovado_pelo_director=aprovado)
        registrar_auditoria(self.request.user, escola, 'COMUNICADO', 'CRIACAO', obj.id, f'Emissão de comunicado: {obj.titulo}')

    @action(detail=True, methods=['post'], url_path='aprovar')
    def aprovar(self, request, pk=None):
        role = getattr(request.user, 'role', '')
        if role not in ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'] and not getattr(request.user, 'is_superuser', False):
            return Response({'success': False, 'message': 'Competência exclusiva do Director da Escola.'}, status=403)
        obj = self.get_object()
        obj.aprovado_pelo_director = True
        obj.status = 'PUBLICADO'
        obj.aprovado_por = request.user
        obj.save()
        registrar_auditoria(request.user, obj.escola, 'COMUNICADO', 'APROVACAO', obj.id, f'Aprovação de comunicado pelo Director')
        return Response({'success': True, 'message': 'Comunicado aprovado e publicado com sucesso!', 'data': self.get_serializer(obj).data})
