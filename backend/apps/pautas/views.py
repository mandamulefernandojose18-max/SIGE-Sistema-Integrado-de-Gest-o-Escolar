from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
import json
import re

from .models import Pauta
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.alunos.models import Aluno
from apps.notas.models import Nota, NotaExame
from common.utils.avaliacoes_mocambique import avaliar_aprovacao_pauta
from apps.documentos.services.pdf_service import gerar_pauta_pdf, gerar_acta_pdf, gerar_pauta_exames_pdf
from apps.documentos.services.excel_service import (
    gerar_pauta_xlsx, gerar_acta_xlsx, gerar_estatisticas_gerais_xlsx, gerar_pauta_exames_xlsx
)
from apps.documentos.services.docx_service import gerar_pauta_docx, gerar_acta_docx

from .services import (
    resolver_permissoes_exames_usuario,
    obter_disciplinas_com_exame_escola,
    obter_disciplinas_pauta_turma,
    extrair_numero_classe,
    categorizar_area,
    CURRICULO_REGRAS_AREAS,
    consolidar_pauta_exames,
    turma_tem_exame,
)

def consolidar_dados_turma(turma, periodo=None, ano_letivo='2026', alunos_prefetched=None, notas_prefetched=None):
    # Buscar única e estritamente as disciplinas daquela área ou secção da turma
    disciplinas = obter_disciplinas_pauta_turma(turma)

    # Obter todas as notas da turma (1_TRIMESTRE, 2_TRIMESTRE, 3_TRIMESTRE) para histórico completo
    if notas_prefetched is not None:
        todas_notas_qs = notas_prefetched
    else:
        todas_notas_qs = list(Nota.objects.filter(turma=turma).select_related('disciplina'))

    if alunos_prefetched is not None:
        alunos = alunos_prefetched
    else:
        alunos = list(Aluno.objects.filter(turma=turma, status='ATIVO').order_by('nome', 'apelido'))

    # Mapa de notas: (aluno_id, disc_id, periodo) e (aluno_id, disc_nome, periodo)
    notas_map = {}
    notas_por_nome = {}
    for n in todas_notas_qs:
        notas_map[(n.aluno_id, n.disciplina_id, n.periodo)] = n
        if n.disciplina and n.disciplina.nome:
            notas_por_nome[(n.aluno_id, n.disciplina.nome.strip().lower(), n.periodo)] = n

    periodo_selecionado = periodo or '1_TRIMESTRE'
    is_anual = str(periodo_selecionado).upper() in ('ANUAL', 'GERAL', 'TODOS', 'FIM_DO_ANO', 'CONCLUSAO', 'GLOBAL', 'MFD')

    dados_alunos = []
    for idx, aluno in enumerate(alunos, start=1):
        aluno_notas = {}
        notas_disciplinas_map = {}
        notas_disciplinas_calc = []

        t1_list = []
        t2_list = []
        t3_list = []
        mfd_list = []

        for d in disciplinas:
            chave_nome = d.nome.strip().lower()

            def obter_nota_periodo(per):
                return notas_map.get((aluno.id, d.id, per)) or notas_por_nome.get((aluno.id, chave_nome, per))

            n_t1 = obter_nota_periodo('1_TRIMESTRE')
            n_t2 = obter_nota_periodo('2_TRIMESTRE')
            n_t3 = obter_nota_periodo('3_TRIMESTRE')

            def extrair_nota_valida(n_obj):
                if not n_obj:
                    return None
                tem_avaliacoes = any(
                    getattr(n_obj, campo, None) is not None and getattr(n_obj, campo, 0) > 0
                    for campo in ['teste1', 'teste2', 'teste3', 'teste4', 'trabalho', 'avaliacao_trimestral']
                )
                if tem_avaliacoes or (n_obj.media_final is not None and n_obj.media_final > 0) or (n_obj.anotacao):
                    return n_obj.media_final
                return None

            v_t1 = extrair_nota_valida(n_t1)
            v_t2 = extrair_nota_valida(n_t2)
            v_t3 = extrair_nota_valida(n_t3)

            if v_t1 is not None: t1_list.append(v_t1)
            if v_t2 is not None: t2_list.append(v_t2)
            if v_t3 is not None: t3_list.append(v_t3)

            # MFD oficial: calculado estritamente quando os 3 trimestres estão disponíveis
            if v_t1 is not None and v_t2 is not None and v_t3 is not None:
                mfd = round((v_t1 + v_t2 + v_t3) / 3, 1)
                mfd_final = int(round(mfd))
                mfd_list.append(mfd)
            else:
                mfd = None
                mfd_final = None

            # Nota relevante para o período solicitado
            if periodo_selecionado in ('2_TRIMESTRE', 'T2'):
                nota_relevante = v_t2
                res_disc = n_t2.resultado if (n_t2 and v_t2 is not None) else ('Sem Nota' if not n_t2 or not n_t2.anotacao else n_t2.anotacao)
                anot_disc = n_t2.anotacao if n_t2 else None
            elif periodo_selecionado in ('3_TRIMESTRE', 'T3'):
                nota_relevante = v_t3
                res_disc = n_t3.resultado if (n_t3 and v_t3 is not None) else ('Sem Nota' if not n_t3 or not n_t3.anotacao else n_t3.anotacao)
                anot_disc = n_t3.anotacao if n_t3 else None
            elif is_anual:
                nota_relevante = mfd_final
                if mfd_final is not None:
                    res_disc = 'Aprovado' if mfd_final >= 9.5 else 'Reprovado'
                else:
                    res_disc = 'Sem Nota'
                anot_disc = n_t3.anotacao if n_t3 else (n_t2.anotacao if n_t2 else (n_t1.anotacao if n_t1 else None))
            else:  # 1_TRIMESTRE, T1
                nota_relevante = v_t1
                res_disc = n_t1.resultado if (n_t1 and v_t1 is not None) else ('Sem Nota' if not n_t1 or not n_t1.anotacao else n_t1.anotacao)
                anot_disc = n_t1.anotacao if n_t1 else None

            aluno_notas[str(d.id)] = {
                'media_final': nota_relevante if nota_relevante is not None else '-',
                'resultado': res_disc,
                'anotacao': anot_disc,
                't1': v_t1 if v_t1 is not None else '-',
                't2': v_t2 if v_t2 is not None else '-',
                't3': v_t3 if v_t3 is not None else '-',
                'mfd': mfd_final if mfd_final is not None else '-'
            }

            disc_obj_data = {
                't1': v_t1 if v_t1 is not None else '-',
                't2': v_t2 if v_t2 is not None else '-',
                't3': v_t3 if v_t3 is not None else '-',
                'mfd': mfd_final if mfd_final is not None else '-'
            }
            notas_disciplinas_map[str(d.id)] = disc_obj_data
            if d.codigo:
                notas_disciplinas_map[d.codigo] = disc_obj_data
            if d.nome:
                notas_disciplinas_map[d.nome] = disc_obj_data

            if nota_relevante is not None:
                notas_disciplinas_calc.append({'disciplina': d.nome, 'notaFinal': nota_relevante})

        if notas_disciplinas_calc:
            avaliacao = avaliar_aprovacao_pauta(notas_disciplinas_calc, turma.grau_ano)
            media_final_geral = avaliacao['mediaGeral']
            total_negativas = avaliacao['totalNegativas']
            resultado_final = avaliacao['resultado']
            sigla_resultado = avaliacao['siglaResultado']
            motivo_resultado = avaliacao['motivo']
        else:
            media_final_geral = '-'
            total_negativas = 0
            resultado_final = 'Pendente'
            sigla_resultado = '-'
            motivo_resultado = 'Sem notas lançadas na caderneta'

        med_t1 = round(sum(t1_list) / len(t1_list), 1) if t1_list else None
        med_t2 = round(sum(t2_list) / len(t2_list), 1) if t2_list else None
        med_t3 = round(sum(t3_list) / len(t3_list), 1) if t3_list else None

        neg_t1 = sum(1 for v in t1_list if v < 9.5)
        neg_t2 = sum(1 for v in t2_list if v < 9.5)
        neg_t3 = sum(1 for v in t3_list if v < 9.5)
        neg_mfd = sum(1 for v in mfd_list if v < 9.5)

        dados_alunos.append({
            'numero': idx,
            'id': str(aluno.id),
            'alunoId': str(aluno.id),
            'matricula': aluno.matricula,
            'nome': aluno.nome,
            'apelido': aluno.apelido or '',
            'nomeCompleto': f"{aluno.nome} {aluno.apelido or ''}".strip(),
            'genero': aluno.genero or 'M',
            'notas': aluno_notas,
            'notasDisciplinas': notas_disciplinas_map,
            'mediasTrimestrais': {
                't1': med_t1 if med_t1 is not None else '-',
                't2': med_t2 if med_t2 is not None else '-',
                't3': med_t3 if med_t3 is not None else '-'
            },
            'negativas': {'t1': neg_t1, 't2': neg_t2, 't3': neg_t3, 'fimDoAno': neg_mfd},
            'media_geral': media_final_geral,
            'mediaFinalGeral': media_final_geral,
            'total_negativas': total_negativas,
            'resultado': resultado_final,
            'resultadoFinal': resultado_final,
            'siglaResultado': sigla_resultado,
            'motivo': motivo_resultado
        })

    total_alunos = len(dados_alunos)
    total_aprovados = sum(1 for a in dados_alunos if a['resultado'] == 'Aprovado')
    total_reprovados = sum(1 for a in dados_alunos if a['resultado'] == 'Reprovado')
    homens = sum(1 for a in dados_alunos if (a['genero'] or '').upper() == 'M')
    mulheres = sum(1 for a in dados_alunos if (a['genero'] or '').upper().startswith('F'))
    taxa_aprov = round((total_aprovados / (total_aprovados + total_reprovados) * 100), 1) if (total_aprovados + total_reprovados) > 0 else 0.0
    taxa_reprov = round(100.0 - taxa_aprov, 1) if (total_aprovados + total_reprovados) > 0 else 0.0

    estatistica = {
        'totalAlunos': total_alunos,
        'homens': homens,
        'mulheres': mulheres,
        'totalAprovados': total_aprovados,
        'totalReprovados': total_reprovados,
        'aprovados': {
            'total': total_aprovados,
            'pct': taxa_aprov
        },
        'reprovados': {
            'total': total_reprovados,
            'pct': taxa_reprov
        },
        'inscritos': {
            'total': total_alunos,
            'h': homens,
            'm': mulheres
        },
        'avaliados': {
            'total': total_alunos,
            'h': homens,
            'm': mulheres
        },
        'taxaAprovacao': taxa_aprov,
        'taxaReprovacao': taxa_reprov
    }

    return {
        'turma': turma,
        'disciplinas': disciplinas,
        'dados_alunos': dados_alunos,
        'estatistica': estatistica
    }

def _calcular_tabelas_acta(alunos, disciplinas):
    total = len(alunos)
    h = sum(1 for a in alunos if (a.get('genero') or '').upper() == 'M')
    m = sum(1 for a in alunos if (a.get('genero') or '').upper().startswith('F'))

    def bloco_genero(qtd_h, qtd_m, base_h=None, base_m=None):
        bh = base_h if base_h is not None else h
        bm = base_m if base_m is not None else m
        hm = qtd_h + qtd_m
        bhm = bh + bm
        return {
            'h': qtd_h,
            'm': qtd_m,
            'hm': hm,
            'pctH': round(qtd_h / bh * 100, 1) if bh > 0 else 0.0,
            'pctM': round(qtd_m / bm * 100, 1) if bm > 0 else 0.0,
            'pct': round(hm / bhm * 100, 1) if bhm > 0 else 0.0,
        }

    desist_h = sum(1 for a in alunos if a.get('resultado') in ('D', 'Desistente') and (a.get('genero') or '').upper() == 'M')
    desist_m = sum(1 for a in alunos if a.get('resultado') in ('D', 'Desistente') and (a.get('genero') or '').upper().startswith('F'))
    transf_h = sum(1 for a in alunos if a.get('resultado') in ('T', 'Transferido') and (a.get('genero') or '').upper() == 'M')
    transf_m = sum(1 for a in alunos if a.get('resultado') in ('T', 'Transferido') and (a.get('genero') or '').upper().startswith('F'))

    avaliados_h = max(0, h - desist_h - transf_h)
    avaliados_m = max(0, m - desist_m - transf_m)

    def nota_numerica_valida(val):
        if val is None or val in ('-', '', 'Sem Nota'):
            return None
        try:
            num = float(val)
            return num if num > 0 else None
        except (ValueError, TypeError):
            return None

    tem_t1 = any(nota_numerica_valida((a.get('mediasTrimestrais') or {}).get('t1')) is not None for a in alunos)
    tem_t2 = any(nota_numerica_valida((a.get('mediasTrimestrais') or {}).get('t2')) is not None for a in alunos)
    tem_t3 = any(nota_numerica_valida((a.get('mediasTrimestrais') or {}).get('t3')) is not None for a in alunos)
    tem_fim_ano = bool(tem_t1 and tem_t2 and tem_t3)

    trimestres_com_notas = {
        't1': bool(tem_t1),
        't2': bool(tem_t2),
        't3': bool(tem_t3),
        'fimAno': bool(tem_fim_ano)
    }

    def gerar_periodo_efectivo(ativo=True):
        return {
            'inscritos': bloco_genero(h, m),
            'desistentes': bloco_genero(desist_h, desist_m) if ativo else bloco_genero(0, 0, 0, 0),
            'transferidos': bloco_genero(transf_h, transf_m) if ativo else bloco_genero(0, 0, 0, 0),
            'falecidos': bloco_genero(0, 0) if ativo else bloco_genero(0, 0, 0, 0),
            'perdeuFaltas': bloco_genero(0, 0) if ativo else bloco_genero(0, 0, 0, 0),
            'anulouMatricula': bloco_genero(0, 0) if ativo else bloco_genero(0, 0, 0, 0),
            'avaliados': bloco_genero(avaliados_h, avaliados_m) if ativo else bloco_genero(0, 0, 0, 0),
        }

    tabela_efectivo = {
        't1': gerar_periodo_efectivo(tem_t1),
        't2': gerar_periodo_efectivo(tem_t2),
        't3': gerar_periodo_efectivo(tem_t3),
        'fimAno': gerar_periodo_efectivo(tem_fim_ano)
    }

    def calcular_faixas(periodo_key):
        faixas = {
            'avaliados': [0, 0],
            'naoSatisfatorio': [0, 0],
            'satisfatorio': [0, 0],
            'bom': [0, 0],
            'muitoBom': [0, 0],
            'excelente': [0, 0],
            'aprovados': [0, 0],
            'reprovados': [0, 0]
        }

        # Se o trimestre ainda não tem notas disponíveis, retorna faixas zeradas
        if periodo_key == 't1' and not tem_t1:
            return {k: bloco_genero(0, 0, 0, 0) for k in faixas}
        if periodo_key == 't2' and not tem_t2:
            return {k: bloco_genero(0, 0, 0, 0) for k in faixas}
        if periodo_key == 't3' and not tem_t3:
            return {k: bloco_genero(0, 0, 0, 0) for k in faixas}
        if periodo_key == 'mediaFinalGeral' and not tem_fim_ano:
            return {k: bloco_genero(0, 0, 0, 0) for k in faixas}

        for a in alunos:
            gen_idx = 1 if (a.get('genero') or '').upper().startswith('F') else 0
            if periodo_key == 'mediaFinalGeral':
                nota = a.get('mediaFinalGeral')
            else:
                nota = (a.get('mediasTrimestrais') or {}).get(periodo_key)

            num = nota_numerica_valida(nota)
            if num is None:
                continue

            faixas['avaliados'][gen_idx] += 1
            if num < 9.5:
                faixas['naoSatisfatorio'][gen_idx] += 1
                faixas['reprovados'][gen_idx] += 1
            else:
                faixas['aprovados'][gen_idx] += 1
                if num < 13.5:
                    faixas['satisfatorio'][gen_idx] += 1
                elif num < 16.5:
                    faixas['bom'][gen_idx] += 1
                elif num < 18.5:
                    faixas['muitoBom'][gen_idx] += 1
                else:
                    faixas['excelente'][gen_idx] += 1

        av_h, av_m = faixas['avaliados']
        res = {}
        for k, v in faixas.items():
            res[k] = bloco_genero(v[0], v[1], av_h, av_m)
        return res

    tabela_aproveitamento = {
        't1': calcular_faixas('t1'),
        't2': calcular_faixas('t2'),
        't3': calcular_faixas('t3'),
        'fimAno': calcular_faixas('mediaFinalGeral')
    }

    disciplinas_enriquecidas = []
    for d in disciplinas:
        d_id = str(d.id)
        d_cod = d.codigo or ''
        d_nome = d.nome
        f0_9 = [0, 0]
        f10_13 = [0, 0]
        f14_16 = [0, 0]
        f17_18 = [0, 0]
        f19_20 = [0, 0]
        av = [0, 0]
        pos = [0, 0]
        neg = [0, 0]

        for a in alunos:
            gen_idx = 1 if (a.get('genero') or '').upper().startswith('F') else 0
            nd = (a.get('notasDisciplinas') or {}).get(d_cod) or (a.get('notasDisciplinas') or {}).get(d_id) or (a.get('notas') or {}).get(d_id) or {}
            val = nd.get('mfd') if nd.get('mfd') not in (None, '-') else (nd.get('media_final') or nd.get('t1'))
            if val is not None and val != '-':
                try:
                    num = float(val)
                    av[gen_idx] += 1
                    if num < 9.5:
                        f0_9[gen_idx] += 1
                        neg[gen_idx] += 1
                    else:
                        pos[gen_idx] += 1
                        if num < 13.5:
                            f10_13[gen_idx] += 1
                        elif num < 16.5:
                            f14_16[gen_idx] += 1
                        elif num < 18.5:
                            f17_18[gen_idx] += 1
                        else:
                            f19_20[gen_idx] += 1
                except (ValueError, TypeError):
                    pass

        av_h, av_m = av
        disciplinas_enriquecidas.append({
            'id': d_id,
            'codigo': d_cod,
            'nome': d_nome,
            'faixa0_9': bloco_genero(f0_9[0], f0_9[1], av_h, av_m),
            'faixa10_13': bloco_genero(f10_13[0], f10_13[1], av_h, av_m),
            'faixa14_16': bloco_genero(f14_16[0], f14_16[1], av_h, av_m),
            'faixa17_18': bloco_genero(f17_18[0], f17_18[1], av_h, av_m),
            'faixa19_20': bloco_genero(f19_20[0], f19_20[1], av_h, av_m),
            'avaliados': bloco_genero(av[0], av[1], av_h, av_m),
            'positivas': bloco_genero(pos[0], pos[1], av_h, av_m),
            'negativas': bloco_genero(neg[0], neg[1], av_h, av_m)
        })

    return tabela_efectivo, tabela_aproveitamento, disciplinas_enriquecidas, trimestres_com_notas

from rest_framework.permissions import AllowAny
import unicodedata

def _safe_ascii_filename(nome: str) -> str:
    s = unicodedata.normalize('NFKD', str(nome or 'documento')).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9._-]+', '_', s).strip('_')
    return s or 'documento'

def _obter_turma_e_escola(request, turma_id):
    from common.utils.tenant import get_tenant_escola
    from rest_framework.exceptions import PermissionDenied, NotFound

    escola = get_tenant_escola(request)
    turma = Turma.objects.select_related('escola', 'director_turma').filter(id=turma_id).first()
    if not turma:
        raise NotFound("Turma não encontrada.")

    # Se a instituição foi resolvida a partir do tenant/usuário e não coincide com a turma, bloquear
    if escola and turma.escola_id and turma.escola_id != escola.id:
        raise PermissionDenied("Acesso negado: a turma pertence a outra instituição.")

    escola_final = turma.escola or escola
    return turma, escola_final

class PautaGerarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        turma_id = request.data.get('turma_id')
        periodo = request.data.get('periodo', '1_TRIMESTRE')
        ano_letivo = request.data.get('ano_letivo', '2026')

        turma, escola = _obter_turma_e_escola(request, turma_id)

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
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano_letivo = request.query_params.get('anoLetivo', '2026')

        dados = consolidar_dados_turma(turma, periodo, ano_letivo)

        dt_nome = turma.director_turma.nome if getattr(turma, 'director_turma', None) else 'Direcção Pedagógica'
        dt_tel = getattr(turma.director_turma, 'telefone', '') if getattr(turma, 'director_turma', None) else ''

        # Identificar área real e oficial da secção/área para turmas do 2º Ciclo
        num_c = extrair_numero_classe(turma.grau_ano)
        area_oficial = turma.area or 'Geral'
        if num_c and num_c in (11, 12):
            _, sub_t = categorizar_area(turma.area, turma.nome)
            regras = CURRICULO_REGRAS_AREAS.get(sub_t)
            if regras and regras.get('nome_oficial'):
                area_oficial = regras['nome_oficial']

        turma_info = {
            'id': str(turma.id),
            'nome': turma.nome,
            'grau': turma.grau_ano,
            'grau_ano': turma.grau_ano,
            'area': area_oficial,
            'turno': turma.turno or 'Diurno',
            'ano_letivo': ano_letivo or turma.ano_letivo or '2026',
            'director_turma': dt_nome,
            'director_turma_tel': dt_tel
        }

        te, ta, disc_enriquecidas, tc = _calcular_tabelas_acta(dados['dados_alunos'], dados['disciplinas'])

        escola_info = {
            'nome': escola.nome if escola else 'Escola',
            'provincia': (getattr(escola, 'provincia', '') or 'Maputo') if escola else 'Maputo',
            'distrito': (getattr(escola, 'distrito', '') or 'Cidade de Maputo') if escola else 'Cidade de Maputo',
            'codigo_escola': (getattr(escola, 'codigo_escola', '') or '') if escola else ''
        }

        data_payload = {
            'turma': turma_info,
            'escola': escola_info,
            'periodo': periodo,
            'anoLetivo': ano_letivo,
            'disciplinas': disc_enriquecidas,
            'alunos': dados['dados_alunos'],
            'estatistica': dados.get('estatistica', {}),
            'tabelaEfectivo': te,
            'tabelaAproveitamento': ta,
            'trimestresComNotas': tc
        }
        retorno = {
            'success': True,
            **data_payload,
            'data': data_payload
        }
        return Response(retorno)

class PautaPDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')
        orientacao = request.query_params.get('orientacao', 'landscape')

        dados = consolidar_dados_turma(turma, periodo, ano)
        pdf_bytes = gerar_pauta_pdf(turma, escola, periodo, ano, dados['dados_alunos'], dados['disciplinas'], orientacao=orientacao)

        fname = _safe_ascii_filename(f"Pauta_{turma.nome}_{ano}.pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class PautaXLSXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')
        orientacao = request.query_params.get('orientacao', 'landscape')

        dados = consolidar_dados_turma(turma, periodo, ano)
        xlsx_bytes = gerar_pauta_xlsx(turma, escola, periodo, ano, dados['dados_alunos'], dados['disciplinas'], orientacao=orientacao)

        fname = _safe_ascii_filename(f"Pauta_{turma.nome}_{ano}.xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class PautaDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')
        orientacao = request.query_params.get('orientacao', 'landscape')

        dados = consolidar_dados_turma(turma, periodo, ano)
        docx_bytes = gerar_pauta_docx(turma, escola, periodo, ano, dados['dados_alunos'], dados['disciplinas'], orientacao=orientacao)

        fname = _safe_ascii_filename(f"Pauta_{turma.nome}_{ano}.docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class ActaPDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')
        presidente = request.query_params.get('presidente')
        data_sessao = request.query_params.get('data')
        orientacao = request.query_params.get('orientacao', 'landscape')

        dados = consolidar_dados_turma(turma, periodo, ano)
        te, ta, disc_enriquecidas, tc = _calcular_tabelas_acta(dados['dados_alunos'], dados['disciplinas'])
        pdf_bytes = gerar_acta_pdf(
            turma, escola, periodo, ano, dados['dados_alunos'],
            tabela_efectivo=te,
            tabela_aproveitamento=ta,
            disciplinas=disc_enriquecidas,
            trimestres_com_notas=tc,
            estatisticas=dados.get('estatisticas'),
            presidente=presidente, data_sessao=data_sessao,
            orientacao=orientacao,
            params_sessao=request.query_params
        )

        fname = _safe_ascii_filename(f"Acta_{turma.nome}_{ano}.pdf")
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class ActaDOCXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')
        presidente = request.query_params.get('presidente')
        data_sessao = request.query_params.get('data')
        orientacao = request.query_params.get('orientacao', 'landscape')

        dados = consolidar_dados_turma(turma, periodo, ano)
        te, ta, disc_enriquecidas, tc = _calcular_tabelas_acta(dados['dados_alunos'], dados['disciplinas'])
        docx_bytes = gerar_acta_docx(
            turma, escola, periodo, ano, dados['dados_alunos'],
            tabela_efectivo=te,
            tabela_aproveitamento=ta,
            disciplinas=disc_enriquecidas,
            trimestres_com_notas=tc,
            estatisticas=dados.get('estatisticas'),
            presidente=presidente, data_sessao=data_sessao,
            orientacao=orientacao,
            params_sessao=request.query_params
        )

        fname = _safe_ascii_filename(f"Acta_{turma.nome}_{ano}.docx")
        response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class ActaXLSXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')
        presidente = request.query_params.get('presidente')
        data_sessao = request.query_params.get('data')
        orientacao = request.query_params.get('orientacao', 'landscape')

        dados = consolidar_dados_turma(turma, periodo, ano)
        te, ta, disc_enriquecidas, tc = _calcular_tabelas_acta(dados['dados_alunos'], dados['disciplinas'])
        xlsx_bytes = gerar_acta_xlsx(
            turma, escola, periodo, ano, dados['dados_alunos'],
            tabela_efectivo=te,
            tabela_aproveitamento=ta,
            disciplinas=disc_enriquecidas,
            trimestres_com_notas=tc,
            estatisticas=dados.get('estatisticas'),
            presidente=presidente, data_sessao=data_sessao,
            orientacao=orientacao,
            params_sessao=request.query_params
        )

        fname = _safe_ascii_filename(f"Acta_{turma.nome}_{ano}.xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

class PautaExportJSONView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        turma, escola = _obter_turma_e_escola(request, turma_id)
        periodo = request.query_params.get('periodo', '1_TRIMESTRE')
        ano = request.query_params.get('anoLetivo', '2026')

        dados = consolidar_dados_turma(turma, periodo, ano)
        disc_data = [{'id': str(d.id), 'nome': d.nome, 'codigo': d.codigo} for d in dados['disciplinas']]

        payload = {
            'escola': escola.nome if escola else 'Escola',
            'turma': turma.nome,
            'periodo': periodo,
            'anoLetivo': ano,
            'disciplinas': disc_data,
            'alunos': dados['dados_alunos']
        }
        fname = _safe_ascii_filename(f"Pauta_{turma.nome}_{ano}.json")
        response = HttpResponse(json.dumps(payload, indent=2, ensure_ascii=False), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response

def compilar_estatisticas_gerais_escola(escola, ano_letivo='2026', periodo='GLOBAL'):
    per_upper = str(periodo or 'GLOBAL').strip().upper()
    if per_upper in ('T1', '1_TRIMESTRE', '1'):
        periodo_norm = '1_TRIMESTRE'
    elif per_upper in ('T2', '2_TRIMESTRE', '2'):
        periodo_norm = '2_TRIMESTRE'
    elif per_upper in ('T3', '3_TRIMESTRE', '3'):
        periodo_norm = '3_TRIMESTRE'
    else:
        periodo_norm = 'ANUAL'

    if escola:
        turmas_qs = Turma.objects.filter(ano_letivo=ano_letivo, escola=escola)
    else:
        turmas_qs = Turma.objects.none()
    turmas = list(turmas_qs.select_related('director_turma', 'escola').order_by('grau_ano', 'nome'))

    todos_alunos = list(Aluno.objects.filter(turma__in=turmas, status='ATIVO').order_by('nome', 'apelido'))
    alunos_por_turma = {}
    for al in todos_alunos:
        alunos_por_turma.setdefault(al.turma_id, []).append(al)

    todas_notas_escola = list(Nota.objects.filter(turma__in=turmas).select_related('disciplina'))
    notas_por_turma = {}
    for nt in todas_notas_escola:
        notas_por_turma.setdefault(nt.turma_id, []).append(nt)

    por_turma = []
    turmas_por_classe = {}
    disciplinas_stats = {}

    geral_inscritos_h = 0
    geral_inscritos_m = 0
    geral_avaliados_h = 0
    geral_avaliados_m = 0
    geral_aprovados_h = 0
    geral_aprovados_m = 0
    geral_reprovados_h = 0
    geral_reprovados_m = 0

    for turma in turmas:
        dados = consolidar_dados_turma(
            turma,
            periodo=periodo_norm,
            ano_letivo=ano_letivo,
            alunos_prefetched=alunos_por_turma.get(turma.id, []),
            notas_prefetched=notas_por_turma.get(turma.id, [])
        )
        alunos_t = dados['dados_alunos']
        disciplinas_t = dados['disciplinas']

        insc_h = sum(1 for a in alunos_t if (a.get('genero') or '').upper() == 'M')
        insc_m = sum(1 for a in alunos_t if (a.get('genero') or '').upper().startswith('F'))
        insc_total = len(alunos_t)

        desist_h = sum(1 for a in alunos_t if a.get('resultado') in ('D', 'Desistente') and (a.get('genero') or '').upper() == 'M')
        desist_m = sum(1 for a in alunos_t if a.get('resultado') in ('D', 'Desistente') and (a.get('genero') or '').upper().startswith('F'))
        transf_h = sum(1 for a in alunos_t if a.get('resultado') in ('T', 'Transferido') and (a.get('genero') or '').upper() == 'M')
        transf_m = sum(1 for a in alunos_t if a.get('resultado') in ('T', 'Transferido') and (a.get('genero') or '').upper().startswith('F'))

        av_h = max(0, insc_h - desist_h - transf_h)
        av_m = max(0, insc_m - desist_m - transf_m)
        av_total = av_h + av_m

        ap_h = sum(1 for a in alunos_t if a.get('resultado') == 'Aprovado' and (a.get('genero') or '').upper() == 'M')
        ap_m = sum(1 for a in alunos_t if a.get('resultado') == 'Aprovado' and (a.get('genero') or '').upper().startswith('F'))
        ap_total = ap_h + ap_m

        rep_h = sum(1 for a in alunos_t if a.get('resultado') == 'Reprovado' and (a.get('genero') or '').upper() == 'M')
        rep_m = sum(1 for a in alunos_t if a.get('resultado') == 'Reprovado' and (a.get('genero') or '').upper().startswith('F'))
        rep_total = rep_h + rep_m

        pct_ap = round((ap_total / av_total * 100), 1) if av_total > 0 else 0.0
        pct_rep = round((rep_total / av_total * 100), 1) if av_total > 0 else 0.0

        dir_nome = turma.director_turma.nome if turma.director_turma else '-'

        turma_dict = {
            'turmaId': str(turma.id),
            'turmaNome': turma.nome,
            'grau_ano': turma.grau_ano,
            'turno': turma.turno,
            'directorTurma': dir_nome,
            'inscritos': {'total': insc_total, 'h': insc_h, 'm': insc_m},
            'avaliados': {'total': av_total, 'h': av_h, 'm': av_m},
            'aprovados': {'total': ap_total, 'h': ap_h, 'm': ap_m, 'pct': pct_ap},
            'reprovados': {'total': rep_total, 'h': rep_h, 'm': rep_m, 'pct': pct_rep},
        }
        por_turma.append(turma_dict)

        geral_inscritos_h += insc_h
        geral_inscritos_m += insc_m
        geral_avaliados_h += av_h
        geral_avaliados_m += av_m
        geral_aprovados_h += ap_h
        geral_aprovados_m += ap_m
        geral_reprovados_h += rep_h
        geral_reprovados_m += rep_m

        num_c = extrair_numero_classe(turma.grau_ano)
        if num_c:
            classe_limpa = f"{num_c}ª"
        else:
            classe_limpa = re.sub(r'(?i)\s*classe\s*', '', str(turma.grau_ano or '')).strip()
            if not classe_limpa.endswith('ª') and classe_limpa.isdigit():
                classe_limpa += 'ª'
            if not classe_limpa:
                classe_limpa = 'Geral'

        if classe_limpa not in turmas_por_classe:
            turmas_por_classe[classe_limpa] = {
                'classe': classe_limpa,
                'turmas': 0,
                'insc_h': 0, 'insc_m': 0,
                'av_h': 0, 'av_m': 0,
                'ap_h': 0, 'ap_m': 0,
                'rep_h': 0, 'rep_m': 0,
            }
        c_entry = turmas_por_classe[classe_limpa]
        c_entry['turmas'] += 1
        c_entry['insc_h'] += insc_h
        c_entry['insc_m'] += insc_m
        c_entry['av_h'] += av_h
        c_entry['av_m'] += av_m
        c_entry['ap_h'] += ap_h
        c_entry['ap_m'] += ap_m
        c_entry['rep_h'] += rep_h
        c_entry['rep_m'] += rep_m

        for d in disciplinas_t:
            d_id = str(d.id)
            if d_id not in disciplinas_stats:
                disciplinas_stats[d_id] = {
                    'id': d_id,
                    'nome': d.nome,
                    'codigo': d.codigo or '',
                    'av_h': 0, 'av_m': 0,
                    'ap_total': 0,
                    'rep_total': 0,
                    'notas': []
                }
            d_stat = disciplinas_stats[d_id]

            for a in alunos_t:
                notas_disc = (a.get('notasDisciplinas') or {}).get(d.codigo) or (a.get('notasDisciplinas') or {}).get(d_id) or (a.get('notas') or {}).get(d_id) or {}
                if periodo_norm == 'ANUAL':
                    val = notas_disc.get('mfd') if notas_disc.get('mfd') not in (None, '-') else (notas_disc.get('media_final') or notas_disc.get('t1'))
                elif periodo_norm == '2_TRIMESTRE':
                    val = notas_disc.get('t2')
                elif periodo_norm == '3_TRIMESTRE':
                    val = notas_disc.get('t3')
                else:
                    val = notas_disc.get('t1')

                if val is not None and val != '-' and val != '':
                    try:
                        num = float(val)
                        is_f = (a.get('genero') or '').upper().startswith('F')
                        if is_f:
                            d_stat['av_m'] += 1
                        else:
                            d_stat['av_h'] += 1

                        if num >= 9.5:
                            d_stat['ap_total'] += 1
                        else:
                            d_stat['rep_total'] += 1

                        d_stat['notas'].append(num)
                    except (ValueError, TypeError):
                        pass

    def chave_classe(item):
        m = re.search(r'\d+', item['classe'])
        return int(m.group(0)) if m else 999

    por_classe = []
    for c_entry in sorted(turmas_por_classe.values(), key=chave_classe):
        total_insc = c_entry['insc_h'] + c_entry['insc_m']
        total_av = c_entry['av_h'] + c_entry['av_m']
        total_ap = c_entry['ap_h'] + c_entry['ap_m']
        total_rep = c_entry['rep_h'] + c_entry['rep_m']
        pct_ap = round((total_ap / total_av * 100), 1) if total_av > 0 else 0.0
        pct_rep = round((total_rep / total_av * 100), 1) if total_av > 0 else 0.0

        por_classe.append({
            'classe': c_entry['classe'],
            'turmas': c_entry['turmas'],
            'inscritos': {'total': total_insc, 'h': c_entry['insc_h'], 'm': c_entry['insc_m']},
            'avaliados': {'total': total_av, 'h': c_entry['av_h'], 'm': c_entry['av_m']},
            'aprovados': {'total': total_ap, 'h': c_entry['ap_h'], 'm': c_entry['ap_m'], 'pct': pct_ap},
            'reprovados': {'total': total_rep, 'h': c_entry['rep_h'], 'm': c_entry['rep_m'], 'pct': pct_rep},
        })

    geral_insc_total = geral_inscritos_h + geral_inscritos_m
    geral_av_total = geral_avaliados_h + geral_avaliados_m
    geral_ap_total = geral_aprovados_h + geral_aprovados_m
    geral_rep_total = geral_reprovados_h + geral_reprovados_m
    geral_pct_ap = round((geral_ap_total / geral_av_total * 100), 1) if geral_av_total > 0 else 0.0
    geral_pct_rep = round((geral_rep_total / geral_av_total * 100), 1) if geral_av_total > 0 else 0.0

    geral_escola = {
        'inscritos': {'total': geral_insc_total, 'h': geral_inscritos_h, 'm': geral_inscritos_m},
        'avaliados': {'total': geral_av_total, 'h': geral_avaliados_h, 'm': geral_avaliados_m},
        'aprovados': {'total': geral_ap_total, 'h': geral_aprovados_h, 'm': geral_aprovados_m, 'pct': geral_pct_ap},
        'reprovados': {'total': geral_rep_total, 'h': geral_reprovados_h, 'm': geral_reprovados_m, 'pct': geral_pct_rep},
    }

    por_disciplina = []
    for d_id, d_stat in disciplinas_stats.items():
        av_tot = d_stat['av_h'] + d_stat['av_m']
        ap_tot = d_stat['ap_total']
        rep_tot = d_stat['rep_total']
        pct_ap = round((ap_tot / av_tot * 100), 1) if av_tot > 0 else 0.0
        pct_rep = round((rep_tot / av_tot * 100), 1) if av_tot > 0 else 0.0
        media_final = round(sum(d_stat['notas']) / len(d_stat['notas']), 1) if d_stat['notas'] else None

        por_disciplina.append({
            'id': d_id,
            'nome': d_stat['nome'],
            'codigo': d_stat['codigo'],
            'avaliados': {'total': av_tot, 'h': d_stat['av_h'], 'm': d_stat['av_m']},
            'aprovados': {'total': ap_tot, 'pct': pct_ap},
            'reprovados': {'total': rep_tot, 'pct': pct_rep},
            'mediaFinal': media_final
        })

    from .services import ORDEM_CURRICULAR_CANONICA
    def ordem_disc(item):
        cod = (item.get('codigo') or '').upper()
        for idx, c in enumerate(ORDEM_CURRICULAR_CANONICA):
            if cod.startswith(c):
                return idx
        return 999

    por_disciplina.sort(key=lambda x: (ordem_disc(x), x['nome']))

    nome_escola = escola.nome if escola else 'Escola Secundária'

    return {
        'escola': {'nome': nome_escola},
        'anoLetivo': ano_letivo,
        'periodo': periodo_norm,
        'geralEscola': geral_escola,
        'porClasse': por_classe,
        'porTurma': por_turma,
        'porDisciplina': por_disciplina,
        'totalAlunos': geral_insc_total,
        'totalTurmas': len(por_turma),
    }

class PautasEstatisticasGeraisView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Instituição não identificada.'}, status=400)

        ano_letivo = request.query_params.get('anoLetivo', '2026')
        periodo = request.query_params.get('periodo', 'GLOBAL')

        dados = compilar_estatisticas_gerais_escola(escola, ano_letivo=ano_letivo, periodo=periodo)
        return Response({
            'success': True,
            'data': dados
        })

class PautasEstatisticasGeraisXLSXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        if not escola:
            return Response({'success': False, 'message': 'Instituição não identificada.'}, status=400)

        ano_letivo = request.query_params.get('anoLetivo', '2026')
        periodo = request.query_params.get('periodo', 'GLOBAL')

        dados = compilar_estatisticas_gerais_escola(escola, ano_letivo=ano_letivo, periodo=periodo)
        xlsx_bytes = gerar_estatisticas_gerais_xlsx(escola, ano_letivo, periodo, dados)

        fname = _safe_ascii_filename(f"Estatisticas_Aproveitamento_{ano_letivo}.xlsx")
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response


# =====================================================================
# ENDPOINTS REST: PAUTA DE EXAMES OFICIAIS (MEC / MOÇAMBIQUE)
# =====================================================================

class PautaExamesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        turma = get_object_or_404(Turma, id=turma_id)
        if escola and turma.escola_id != escola.id:
            if getattr(request.user, 'role', '') == 'SUPERADMIN':
                escola = turma.escola
            else:
                return Response({'success': False, 'message': 'Acesso negado: a turma pertence a outra instituição.'}, status=403)

        ano_letivo = request.query_params.get('anoLetivo', getattr(escola, 'ano_letivo_ativo', '2026') or '2026')
        dados_exame = consolidar_pauta_exames(turma, ano_letivo=ano_letivo)

        esc = escola or getattr(turma, 'escola', None)
        if esc:
            dados_exame['escola'] = {
                'id': str(esc.id),
                'nome': getattr(esc, 'nome', '') or 'Escola Secundária de Massinga',
                'provincia': getattr(esc, 'provincia', '') or 'Inhambane',
                'distrito': getattr(esc, 'distrito', '') or 'Massinga',
                'codigo_escola': getattr(esc, 'codigo_escola', '') or '',
                'logo': getattr(esc, 'logo', '') or '',
            }

        # Permissões de edição e lançamento de notas de exame (com suporte a permissão parcial por grupo de disciplina)
        user = getattr(request, 'user', None)
        perm_info = resolver_permissoes_exames_usuario(
            user=user,
            escola=esc,
            turma=turma,
            disciplinas_info=dados_exame.get('disciplinas')
        )
        dados_exame['pode_editar'] = perm_info['pode_editar']
        dados_exame['motivo_bloqueio'] = perm_info['motivo_bloqueio']
        dados_exame['is_gestao'] = perm_info['is_gestao']
        dados_exame['disciplinas_autorizadas_ids'] = perm_info['disciplinas_autorizadas_ids']
        dados_exame['disciplinas_autorizadas_nomes'] = perm_info['disciplinas_autorizadas_nomes']
        dados_exame['is_permissao_parcial'] = perm_info['is_permissao_parcial']

        return Response({
            'success': True,
            'data': dados_exame,
            **dados_exame
        })

    def post(self, request, turma_id):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        turma = get_object_or_404(Turma, id=turma_id)
        if escola and turma.escola_id != escola.id:
            if getattr(request.user, 'role', '') == 'SUPERADMIN':
                escola = turma.escola
            else:
                return Response({'success': False, 'message': 'Acesso negado: a turma pertence a outra instituição.'}, status=403)

        # Validação mandatória de permissão de salvamento de notas de exame (integral ou parcial por disciplina)
        user = getattr(request, 'user', None)
        perm_info = resolver_permissoes_exames_usuario(
            user=user,
            escola=escola or turma.escola,
            turma=turma
        )
        if not perm_info['pode_editar']:
            return Response({
                'success': False,
                'message': perm_info['motivo_bloqueio'] or "Acesso negado: apenas o Director Pedagógico ou professores autorizados podem lançar notas de exame."
            }, status=403)

        discs_permitidas = perm_info.get('disciplinas_autorizadas_ids')

        ano_letivo = request.data.get('ano_letivo') or getattr(escola, 'ano_letivo_ativo', '2026') or '2026'
        notas_payload = request.data.get('notas', [])

        if not isinstance(notas_payload, list):
            return Response({'success': False, 'message': 'Formato inválido: lista de notas esperada.'}, status=400)

        # Restrição de salvamento estritamente para disciplinas autorizadas em regime parcial
        if discs_permitidas is not None:
            discs_permitidas_set = set(str(x) for x in discs_permitidas)
            notas_payload = [item for item in notas_payload if str(item.get('disciplina_id')) in discs_permitidas_set]
            if not notas_payload:
                return Response({
                    'success': False,
                    'message': 'Nenhuma nota de disciplina autorizada foi submetida para gravação nesta turma.'
                }, status=403)

        salvos = 0
        for item in notas_payload:
            aluno_id = item.get('aluno_id')
            disc_id = item.get('disciplina_id')
            if not aluno_id or not disc_id:
                continue

            e1 = item.get('exame_1epoca')
            e2 = item.get('exame_2epoca')
            mfreq = item.get('nota_frequencia') or item.get('frequencia')

            def parse_num(v):
                if v is None or v == '' or v == '-':
                    return None
                try:
                    # Suporte a inteiros e decimais com vírgula ou ponto (1 ou 2 casas decimais) em [0, 20]
                    v_str = str(v).strip().replace(',', '.')
                    num = float(v_str)
                    num = round(num, 2)
                    return max(0.0, min(20.0, num))
                except (ValueError, TypeError):
                    return None

            e1_num = parse_num(e1)
            e2_num = parse_num(e2)
            mfreq_num = parse_num(mfreq)

            ne_obj, _ = NotaExame.objects.get_or_create(
                escola=escola or turma.escola,
                aluno_id=aluno_id,
                disciplina_id=disc_id,
                turma=turma,
                ano_letivo=ano_letivo
            )

            if mfreq_num is not None:
                ne_obj.nota_frequencia = mfreq_num

            # Regra Oficial de Admissão ao Exame:
            # Se na nota de frequência tiver uma nota <= 9.4 (negativa), o aluno não tem direito ao exame:
            # os campos de exame devem ficar vazios, não aceita notas e o resultado é 'Excluído'.
            if mfreq_num is not None and mfreq_num <= 9.4:
                ne_obj.exame_1epoca = None
                ne_obj.exame_2epoca = None
                ne_obj.nota_final = int(round(mfreq_num))
                ne_obj.resultado = 'Excluído'
                ne_obj.save()
                salvos += 1
                continue

            ne_obj.exame_1epoca = e1_num
            ne_obj.exame_2epoca = e2_num

            # Calcular e salvar nota_final ponderada e resultado oficial
            esc_obj = escola or turma.escola
            cfg_p = esc_obj.get_config_parametros_exames() if hasattr(esc_obj, 'get_config_parametros_exames') else {}
            p_freq = float(cfg_p.get('peso_frequencia', 50.0))
            p_exame = float(cfg_p.get('peso_exame', 50.0))
            n_min = float(cfg_p.get('nota_minima_exame', 10.0))

            nota_ex = None
            if e1_num is not None and e1_num >= n_min:
                nota_ex = e1_num
            elif e1_num is not None and e1_num < n_min:
                if e2_num is not None:
                    nota_ex = e2_num
            elif e1_num is None and e2_num is not None:
                nota_ex = e2_num

            if nota_ex is not None:
                if mfreq_num is not None:
                    nf_val = round((mfreq_num * (p_freq / 100.0)) + (nota_ex * (p_exame / 100.0)), 1)
                    ne_obj.nota_final = int(round(nf_val))
                else:
                    ne_obj.nota_final = int(round(nota_ex))
                ne_obj.resultado = 'Aprovado' if ne_obj.nota_final >= 9.5 else 'Reprovado'
            else:
                # Se não tem nota num dos exames (1ª ou 2ª) então a Média nessa disciplina é 0
                ne_obj.nota_final = 0
                ne_obj.resultado = 'Reprovado'

            ne_obj.save()
            salvos += 1

        return Response({
            'success': True,
            'message': f"{salvos} nota(s) de exame atualizada(s) com sucesso na pauta oficial!",
            'salvos': salvos
        })


class PautaExamesXLSXView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        turma = get_object_or_404(Turma, id=turma_id)
        if escola and turma.escola_id != escola.id:
            if getattr(request.user, 'role', '') == 'SUPERADMIN':
                escola = turma.escola
            else:
                return Response({'success': False, 'message': 'Acesso negado.'}, status=403)

        ano_letivo = request.query_params.get('anoLetivo', getattr(escola, 'ano_letivo_ativo', '2026') or '2026')
        orientacao = request.query_params.get('orientacao', 'landscape')

        dados = consolidar_pauta_exames(turma, ano_letivo=ano_letivo)
        xlsx_bytes = gerar_pauta_exames_xlsx(dados, escola or turma.escola, ano_letivo=ano_letivo, orientacao=orientacao)

        safe_turma = re.sub(r'[^\w\-]', '_', turma.nome)
        fname = f"Pauta_Exames_{safe_turma}_{ano_letivo}.xlsx"
        response = HttpResponse(xlsx_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response


class PautaExamesPDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, turma_id):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        turma = get_object_or_404(Turma, id=turma_id)
        if escola and turma.escola_id != escola.id:
            if getattr(request.user, 'role', '') == 'SUPERADMIN':
                escola = turma.escola
            else:
                return Response({'success': False, 'message': 'Acesso negado.'}, status=403)

        ano_letivo = request.query_params.get('anoLetivo', getattr(escola, 'ano_letivo_ativo', '2026') or '2026')
        orientacao = request.query_params.get('orientacao', 'landscape')

        dados = consolidar_pauta_exames(turma, ano_letivo=ano_letivo)
        pdf_bytes = gerar_pauta_exames_pdf(dados, escola or turma.escola, ano_letivo=ano_letivo, orientacao=orientacao)

        safe_turma = re.sub(r'[^\w\-]', '_', turma.nome)
        fname = f"Pauta_Exames_{safe_turma}_{ano_letivo}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response


class ParametrosExamesView(APIView):
    """
    Endpoint para consultar e definir percentagens da nota de frequência, nota de exame
    e nota mínima de exame da instituição escolar (ou padrão MEC).
    """
    permission_classes = [AllowAny]  # Validação manual por token/tenant ou AllowAny para flexibilidade

    def get(self, request):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        if not escola:
            # Fallback para primeira escola ativa
            from apps.tenants.models import Escola
            escola = Escola.objects.first()

        if not escola:
            return Response({'success': False, 'message': 'Nenhuma instituição encontrada.'}, status=404)

        cfg = escola.get_config_parametros_exames()
        return Response({
            'success': True,
            'parametros': cfg
        })

    def post(self, request):
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(request)
        if not escola:
            from apps.tenants.models import Escola
            escola = Escola.objects.first()

        if not escola:
            return Response({'success': False, 'message': 'Nenhuma instituição encontrada.'}, status=404)

        peso_freq = request.data.get('peso_frequencia')
        peso_exame = request.data.get('peso_exame')
        nota_minima = request.data.get('nota_minima_exame')

        try:
            pf = float(peso_freq)
            pe = float(peso_exame)
            nm = float(nota_minima)
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'message': 'Os valores de percentagem e nota mínima devem ser numéricos válidos.'
            }, status=400)

        if pf < 0 or pf > 100 or pe < 0 or pe > 100:
            return Response({
                'success': False,
                'message': 'As percentagens devem estar entre 0% e 100%.'
            }, status=400)

        if round(pf + pe, 1) != 100.0:
            return Response({
                'success': False,
                'message': f'A soma da percentagem de frequência ({pf}%) e de exame ({pe}%) deve totalizar exatamente 100%.'
            }, status=400)

        if nm < 0 or nm > 20:
            return Response({
                'success': False,
                'message': 'A nota mínima do exame deve estar entre 0 e 20 valores.'
            }, status=400)

        cfg = dict(escola.config_parametros_exames or {})
        cfg['peso_frequencia'] = pf
        cfg['peso_exame'] = pe
        cfg['nota_minima_exame'] = nm
        escola.config_parametros_exames = cfg
        escola.save(update_fields=['config_parametros_exames'])

        return Response({
            'success': True,
            'message': 'Parâmetros de exame configurados com sucesso!',
            'parametros': escola.get_config_parametros_exames()
        })

class ProfessoresAutorizadosExamesView(APIView):
    """
    Endpoint para gerenciar permissões de lançamento de notas de exame por professor e por classe.
    Competência primária: Director Pedagógico (DAP) ou Direcção da Escola.
    Todas as classes com exame da instituição ficam automaticamente disponíveis.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from common.utils.tenant import get_tenant_escola
        from apps.professores.models import Professor
        from apps.pautas.services import obter_classes_com_exame_escola
        from apps.tenants.models import Escola

        escola = get_tenant_escola(request)
        if not escola:
            escola = Escola.objects.first()

        if not escola:
            return Response({'success': False, 'message': 'Nenhuma instituição encontrada.'}, status=404)

        user = getattr(request, 'user', None)
        user_role = getattr(user, 'role', '') if user else ''
        is_gestao = user_role in ('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', '')

        # 1. Classes e Disciplinas com exame da escola disponíveis automaticamente
        classes_exame = obter_classes_com_exame_escola(escola)
        disciplinas_com_exame = obter_disciplinas_com_exame_escola(escola)

        # 2. Lista de professores ativos da escola com disciplinas alocadas
        from apps.professores.models import AlocacaoDocente
        alocacoes_qs = AlocacaoDocente.objects.filter(escola=escola).select_related('disciplina', 'professor')
        alocs_map = {}
        for al in alocacoes_qs:
            if al.professor_id and al.disciplina:
                p_id_str = str(al.professor_id)
                if p_id_str not in alocs_map:
                    alocs_map[p_id_str] = set()
                alocs_map[p_id_str].add(al.disciplina.nome)

        profs_qs = Professor.objects.filter(escola=escola, ativo=True).order_by('nome')
        professores = []
        for p in profs_qs:
            p_id_str = str(p.id)
            professores.append({
                'id': p_id_str,
                'nome': p.nome,
                'codigo': p.codigo or '',
                'especialidade': p.especialidade or '',
                'email': p.email or '',
                'disciplinas_alocadas': sorted(list(alocs_map.get(p_id_str, set())))
            })

        # 3. Configurações atuais de professores autorizados e regime de lançamento
        cfg_p = escola.get_config_parametros_exames()
        profs_autorizados = cfg_p.get('professores_autorizados_exame', [])
        modo_permissao = cfg_p.get('modo_permissao_exames', 'ALGUNS_PROFESSORES')

        return Response({
            'success': True,
            'classes_com_exame': classes_exame,
            'disciplinas_com_exame': disciplinas_com_exame,
            'professores': professores,
            'autorizacoes': profs_autorizados,
            'modo_permissao': modo_permissao,
            'is_gestao': is_gestao
        })

    def post(self, request):
        from common.utils.tenant import get_tenant_escola
        from apps.tenants.models import Escola
        from django.utils import timezone

        escola = get_tenant_escola(request)
        if not escola:
            escola = Escola.objects.first()

        if not escola:
            return Response({'success': False, 'message': 'Nenhuma instituição encontrada.'}, status=404)

        user = getattr(request, 'user', None)
        user_role = getattr(user, 'role', '') if user else ''
        is_gestao = user_role in ('SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', '')

        if user and getattr(user, 'is_authenticated', False) and not is_gestao:
            return Response({
                'success': False,
                'message': 'Apenas o Director Pedagógico ou administradores da escola podem configurar permissões de professores para lançamento de exames.'
            }, status=403)

        modo_permissao = request.data.get('modo_permissao', 'ALGUNS_PROFESSORES')
        if modo_permissao not in ('APENAS_DAP', 'ALGUNS_PROFESSORES', 'TODOS_PROFESSORES'):
            modo_permissao = 'ALGUNS_PROFESSORES'

        autorizacoes_payload = request.data.get('autorizacoes', [])
        if not isinstance(autorizacoes_payload, list):
            autorizacoes_payload = []

        cfg = dict(escola.config_parametros_exames or {})
        autorizado_por = getattr(user, 'nome', '') or 'Director Pedagógico'
        data_agora = timezone.now().isoformat()

        novas_autorizacoes = []
        for item in autorizacoes_payload:
            p_id = item.get('professor_id')
            p_nome = item.get('professor_nome', '')
            classes = item.get('classes', [])
            disciplinas = item.get('disciplinas', [])
            ativo = item.get('ativo', True)
            if p_id and (classes or disciplinas):
                novas_autorizacoes.append({
                    'professor_id': str(p_id),
                    'professor_nome': p_nome,
                    'classes': [str(c).strip() for c in classes if str(c).strip()],
                    'disciplinas': [str(d).strip() for d in disciplinas if str(d).strip()],
                    'ativo': bool(ativo),
                    'autorizado_por': autorizado_por,
                    'data_autorizacao': data_agora
                })

        cfg['modo_permissao_exames'] = modo_permissao
        cfg['professores_autorizados_exame'] = novas_autorizacoes
        escola.config_parametros_exames = cfg
        escola.save(update_fields=['config_parametros_exames'])

        msg_modo = {
            'APENAS_DAP': 'Lançamento restrito exclusivamente ao Director Pedagógico.',
            'TODOS_PROFESSORES': 'Lançamento autorizado para todos os professores da instituição.',
            'ALGUNS_PROFESSORES': f'{len(novas_autorizacoes)} professor(es) configurado(s) com autorização por classe.'
        }.get(modo_permissao, 'Permissões atualizadas com sucesso!')

        return Response({
            'success': True,
            'message': f'Permissões de exames guardadas com sucesso! {msg_modo}',
            'modo_permissao': modo_permissao,
            'autorizacoes': novas_autorizacoes
        })

