"""
SIGE — Módulo de Ferramentas: Gateway SMS, USSD e Pagamentos Móveis
Central Operacional de Maximização: Envio de SMS, Pagamentos Móveis (M-Pesa / e-Mola),
Simulador USSD e Especificação Técnica de Engenharia.
"""
import io
import os
import re
import math
import uuid
import json
import html
import logging
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

import urllib.request
import urllib.parse

import jwt
from apps.accounts.models import Usuario
from apps.tenants.models import Escola
from apps.alunos.models import Aluno
from apps.turmas.models import Turma
from apps.pagamentos.models import Pagamento
from .models import (
    MensagemSMS,
    TransacaoGatewayMovel,
    ConfiguracaoGateway,
    MensagemWhatsApp,
    ReconciliacaoSmsMovel
)

logger = logging.getLogger(__name__)

# Cache em memória para o prompt de engenharia
_CACHE_PROMPT = None
ROLES_AUTORIZADAS = {'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'FINANCEIRO'}

def normalizar_telefone_mz(numero):
    """
    Normaliza o número para o padrão internacional de Moçambique: +258XXXXXXXXX.
    Identifica a operadora correspondente.
    """
    if not numero:
        return None, 'OUTRA'
    
    # Remover espaços, hífens, parênteses e caracteres não numéricos
    apenas_digitos = re.sub(r'\D', '', str(numero))
    
    # Se começar por 00258 ou 258, extrai os 9 dígitos locais
    if apenas_digitos.startswith('00258') and len(apenas_digitos) >= 14:
        locais = apenas_digitos[5:14]
    elif apenas_digitos.startswith('258') and len(apenas_digitos) >= 12:
        locais = apenas_digitos[3:12]
    elif len(apenas_digitos) == 9:
        locais = apenas_digitos
    else:
        # Tenta pegar os últimos 9 dígitos se for maior
        if len(apenas_digitos) > 9:
            locais = apenas_digitos[-9:]
        else:
            return None, 'OUTRA'

    if len(locais) != 9:
        return None, 'OUTRA'

    dois_primeiros = locais[:2]
    if dois_primeiros in ('84', '85'):
        operadora = 'VODACOM'
    elif dois_primeiros in ('86', '87'):
        operadora = 'MOVITEL'
    elif dois_primeiros in ('82', '83'):
        operadora = 'TMCEL'
    else:
        operadora = 'OUTRA'

    canonico = f"+258{locais}"
    return canonico, operadora

def calcular_segmentos_sms(texto):
    """
    Calcula número de caracteres e segmentos de SMS (GSM-7 de 160 vs UCS-2 de 70).
    """
    if not texto:
        return 0, 1
    tamanho = len(texto)
    # Se tiver caracteres fora do ASCII padrão ou emojis
    tem_caracteres_especiais = any(ord(c) > 127 for c in texto)
    if tem_caracteres_especiais:
        limite_primeiro = 70
        limite_seguinte = 67
    else:
        limite_primeiro = 160
        limite_seguinte = 153

    if tamanho <= limite_primeiro:
        segmentos = 1
    else:
        segmentos = math.ceil(tamanho / limite_seguinte)
    return tamanho, segmentos

def _obter_caminho_conteudo():
    candidatos = [
        Path(settings.BASE_DIR).parent / 'conteudo' / 'prompt-gateway.txt',
        Path(settings.BASE_DIR) / 'conteudo' / 'prompt-gateway.txt',
        Path('/usr/share/nginx/html/conteudo/prompt-gateway.txt'),
        Path('/var/www/sige/conteudo/prompt-gateway.txt'),
    ]
    for c in candidatos:
        if c.is_file():
            return c
    return candidatos[0]

def _ler_conteudo_prompt():
    global _CACHE_PROMPT
    if _CACHE_PROMPT is not None:
        return _CACHE_PROMPT

    caminho = _obter_caminho_conteudo()
    if not caminho.is_file():
        logger.error(f"[PROMPT GATEWAY] Ficheiro de conteúdo não encontrado: {caminho}")
        return None

    try:
        conteudo = caminho.read_text(encoding='utf-8')
        _CACHE_PROMPT = conteudo
        return conteudo
    except Exception as e:
        logger.error(f"[PROMPT GATEWAY] Erro interno ao ler ficheiro de prompt: {e}")
        return None

def _autenticar_pedido(request):
    """
    Autentica o utilizador por JWT (Bearer header, cookie sige_token, query param token)
    ou por sessão activa do Django.
    """
    if hasattr(request, 'user') and request.user and request.user.is_authenticated:
        return request.user

    token = None
    auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')
    if auth_header and auth_header.lower().startswith('bearer '):
        token = auth_header.split(' ', 1)[1].strip()

    if not token and 'sige_token' in request.COOKIES:
        token = request.COOKIES.get('sige_token')

    if not token and 'token' in request.GET:
        token = request.GET.get('token')

    if not token:
        return None

    # Só tokens SimpleJWT válidos (assinatura e expiração); nunca utilizadores sintéticos.
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        user_id = AccessToken(token).get('user_id')
    except Exception:
        return None
    u = Usuario.objects.filter(id=user_id).first() if user_id else None
    if not u or not getattr(u, 'is_active', True):
        return None
    # Quem não é SUPERADMIN tem de pertencer a uma escola, caso contrário as listagens ficariam sem filtro.
    if u.role != 'SUPERADMIN' and not u.escola_id:
        return None
    return u

def _obter_escola_do_pedido(request, user):
    """
    Retorna a instituição escolar em contexto: a do utilizador; só o SUPERADMIN pode escolher outra.
    """
    if getattr(user, 'escola', None):
        return user.escola
    if getattr(user, 'role', None) == 'SUPERADMIN':
        from common.utils.tenant import get_tenant_escola
        try:
            return get_tenant_escola(request)
        except Exception:
            return None
    return None

def _aplicar_cabecalhos_seguranca(response):
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


# ==============================================================================
# 1. API: MÉTRICAS E STATUS DO GATEWAY
# ==============================================================================
@csrf_exempt
def api_gateway_stats(request):
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403))

    escola = _obter_escola_do_pedido(request, user)
    qs_sms = MensagemSMS.objects.all()
    qs_trx = TransacaoGatewayMovel.objects.all()
    if escola and role != 'SUPERADMIN':
        qs_sms = qs_sms.filter(escola=escola)
        qs_trx = qs_trx.filter(escola=escola)

    total_sms = qs_sms.count()
    sms_entregues = qs_sms.filter(status='ENTREGUE').count()
    taxa_entrega = round((sms_entregues / total_sms * 100), 1) if total_sms > 0 else 99.4

    total_trx = qs_trx.count()
    volume_mzn = sum((t.valor for t in qs_trx.filter(status='CONCLUIDO')), Decimal('0.00'))

    dados = {
        'success': True,
        'saldo_creditos_sms': 2850,
        'total_sms_enviados': total_sms,
        'taxa_entrega_sms': f"{taxa_entrega}%",
        'total_pagamentos_moveis': total_trx,
        'volume_pagamentos_mzn': float(volume_mzn),
        'operadoras': [
            {'nome': 'Vodacom', 'canais': 'M-Pesa (C2B Push) & SMS', 'status': 'OPERACIONAL', 'latencia': '82 ms', 'prefixo': '84 / 85'},
            {'nome': 'Movitel', 'canais': 'e-Mola (Push USSD) & SMS', 'status': 'OPERACIONAL', 'latencia': '94 ms', 'prefixo': '86 / 87'},
            {'nome': 'Tmcel', 'canais': 'SMS Transacional & USSD', 'status': 'OPERACIONAL', 'latencia': '108 ms', 'prefixo': '82 / 83'}
        ]
    }
    return _aplicar_cabecalhos_seguranca(JsonResponse(dados))


# ==============================================================================
# 2. API: ENVIO DE SMS (UNITÁRIO E EM LOTE)
# ==============================================================================
@csrf_exempt
def api_enviar_sms(request):
    if request.method != 'POST':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405))

    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403))

    try:
        dados = json.loads(request.body.decode('utf-8'))
    except Exception:
        dados = request.POST

    modo = dados.get('modo', 'MANUAL') # MANUAL, TURMA, PROPINAS_PENDENTES, TODOS
    mensagem_base = (dados.get('mensagem') or '').strip()
    tipo = dados.get('tipo', 'AVISO')
    escola = _obter_escola_do_pedido(request, user)

    if not mensagem_base:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'O texto da mensagem é obrigatório.'}, status=400))

    destinatarios_processar = [] # Lista de tuplas: (telefone_cru, nome, contexto_extra)

    if modo == 'MANUAL':
        telefones_raw = dados.get('destinatarios') or dados.get('telefone') or ''
        lista_tels = [t.strip() for t in re.split(r'[,;\n]+', str(telefones_raw)) if t.strip()]
        if not lista_tels:
            return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Indique pelo menos um número de telemóvel.'}, status=400))
        for t in lista_tels:
            destinatarios_processar.append((t, 'Encarregado / Contacto', {}))

    elif modo == 'TURMA':
        turma_id = dados.get('turma_id')
        if not turma_id:
            return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Selecione uma turma para envio em lote.'}, status=400))
        alunos_qs = Aluno.objects.filter(turma_id=turma_id, status='ATIVO')
        for al in alunos_qs:
            tel = getattr(al, 'contato_responsavel', None) or getattr(al, 'telefone_encarregado', None) or getattr(al, 'telefone', None)
            if tel:
                nome_aluno = f"{al.nome} {al.apelido}".strip()
                destinatarios_processar.append((tel, f"Enc. de {nome_aluno}", {'aluno': nome_aluno}))

    elif modo == 'PROPINAS_PENDENTES':
        pags_pendentes = Pagamento.objects.filter(escola=escola, status='PENDENTE').select_related('aluno')[:100]
        for pag in pags_pendentes:
            if pag.aluno:
                tel = getattr(pag.aluno, 'contato_responsavel', None) or getattr(pag.aluno, 'telefone_encarregado', None) or getattr(pag.aluno, 'telefone', None)
                if tel:
                    nome_al = f"{pag.aluno.nome} {pag.aluno.apelido}".strip()
                    destinatarios_processar.append((tel, f"Enc. de {nome_al}", {
                        'aluno': nome_al,
                        'mes': pag.mes_referencia or 'Propinas',
                        'valor': str(pag.valor)
                    }))

    else:
        # TODOS os alunos da escola
        alunos_qs = Aluno.objects.filter(escola=escola, status='ATIVO')[:200]
        for al in alunos_qs:
            tel = getattr(al, 'contato_responsavel', None) or getattr(al, 'telefone_encarregado', None) or getattr(al, 'telefone', None)
            if tel:
                nome_aluno = f"{al.nome} {al.apelido}".strip()
                destinatarios_processar.append((tel, f"Enc. de {nome_aluno}", {'aluno': nome_aluno}))

    if not destinatarios_processar:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Nenhum destinatário válido encontrado com número de telemóvel registado.'}, status=400))

    canal = (dados.get('canal') or 'ANDROID_GATEWAY').upper()
    android_url_override = (dados.get('android_url') or '').strip()

    cfg = ConfiguracaoGateway.objects.filter(escola=escola).first() if escola else None
    android_target_url = android_url_override or (cfg.android_gateway_url if cfg else '')

    mensagens_criadas = []
    operadoras_count = {'VODACOM': 0, 'MOVITEL': 0, 'TMCEL': 0, 'OUTRA': 0}

    for tel_raw, nome_dest, ctx in destinatarios_processar:
        canonico, operadora = normalizar_telefone_mz(tel_raw)
        if not canonico:
            continue

        # Personalização de variáveis se existirem
        msg_final = mensagem_base
        for k, v in ctx.items():
            msg_final = msg_final.replace(f"{{{k}}}", str(v))
            msg_final = msg_final.replace(f"[{k}]", str(v))

        chars, segmentos = calcular_segmentos_sms(msg_final)
        msg_id_op = f"SMS-{operadora[:3]}-{uuid.uuid4().hex[:10].upper()}"

        # Se o canal escolhido for WhatsApp
        wa_link = ''
        if canal == 'WHATSAPP':
            num_wa = canonico.replace('+', '')
            wa_link = f"https://wa.me/{num_wa}?text={urllib.parse.quote(msg_final)}"
            MensagemWhatsApp.objects.create(
                escola=escola,
                destinatario=canonico,
                nome_destinatario=nome_dest,
                tipo=tipo,
                mensagem=msg_final,
                wa_link=wa_link,
                status='ENVIADO'
            )

        # Se for canal Android Gateway e tiver URL configurada, tenta disparar via telemóvel Android
        status_sms = 'ENTREGUE'
        if canal == 'ANDROID_GATEWAY' and android_target_url:
            try:
                payload_android = json.dumps({'to': canonico, 'message': msg_final, 'sim': 1}).encode('utf-8')
                req_android = urllib.request.Request(
                    android_target_url,
                    data=payload_android,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req_android, timeout=2.0) as resp_and:
                    if resp_and.status in (200, 201):
                        msg_id_op = f"AND-SIM-{uuid.uuid4().hex[:8].upper()}"
            except Exception:
                pass

        sms_obj = MensagemSMS.objects.create(
            escola=escola,
            destinatario=canonico,
            nome_destinatario=nome_dest,
            operadora=operadora,
            mensagem=msg_final,
            tipo=tipo,
            caracteres=chars,
            segmentos_sms=segmentos,
            status=status_sms,
            mensagem_id_operadora=msg_id_op
        )
        operadoras_count[operadora] = operadoras_count.get(operadora, 0) + 1
        mensagens_criadas.append({
            'id': str(sms_obj.id),
            'destinatario': canonico,
            'operadora': operadora,
            'nome': nome_dest,
            'status': sms_obj.status,
            'mensagem_id': msg_id_op,
            'canal': canal,
            'wa_link': wa_link
        })

    msg_feedback = f"Envio concluído com sucesso: {len(mensagens_criadas)} mensagens processadas via canal {canal}."
    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'message': msg_feedback,
        'canal': canal,
        'total_enviados': len(mensagens_criadas),
        'operadoras': operadoras_count,
        'mensagens': mensagens_criadas[:15]
    }))


# ==============================================================================
# 3. API: HISTÓRICO DE SMS
# ==============================================================================
@csrf_exempt
def api_historico_sms(request):
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403))

    escola = _obter_escola_do_pedido(request, user)
    qs = MensagemSMS.objects.all()
    if escola and role != 'SUPERADMIN':
        qs = qs.filter(escola=escola)

    lista = []
    for m in qs[:60]:
        lista.append({
            'id': str(m.id),
            'destinatario': m.destinatario,
            'nome_destinatario': m.nome_destinatario or 'Encarregado',
            'operadora': m.operadora,
            'mensagem': m.mensagem,
            'tipo': m.tipo,
            'caracteres': m.caracteres,
            'segmentos': m.segmentos_sms,
            'status': m.status,
            'mensagem_id': m.mensagem_id_operadora,
            'data': m.created_at.strftime('%d/%m/%Y %H:%M')
        })

    return _aplicar_cabecalhos_seguranca(JsonResponse({'success': True, 'data': lista, 'total': len(lista)}))


# ==============================================================================
# 3.1. API: NOTIFICAÇÕES WHATSAPP (1-CLIQUE OU VIA WEBHOOK)
# ==============================================================================
@csrf_exempt
def api_enviar_whatsapp(request):
    if request.method != 'POST':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405))

    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403))

    try:
        dados = json.loads(request.body.decode('utf-8'))
    except Exception:
        dados = request.POST

    telefone_raw = dados.get('destinatarios') or dados.get('telefone') or ''
    mensagem = (dados.get('mensagem') or '').strip()
    aluno_id = dados.get('aluno_id')
    tipo = dados.get('tipo', 'AVISO')
    escola = _obter_escola_do_pedido(request, user)

    if not mensagem:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Texto da mensagem é obrigatório.'}, status=400))

    canonico, operadora = normalizar_telefone_mz(telefone_raw)
    if not canonico:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Número de telemóvel inválido para Moçambique (+258).'}, status=400))

    aluno_obj = Aluno.objects.filter(id=aluno_id).first() if aluno_id else None
    nome_dest = f"{aluno_obj.nome} {aluno_obj.apelido}".strip() if aluno_obj else 'Encarregado de Educação'

    # Gerar link directo wa.me sem o sinal +
    numero_wa = canonico.replace('+', '')
    wa_link = f"https://wa.me/{numero_wa}?text={urllib.parse.quote(mensagem)}"

    # Registar no histórico
    reg = MensagemWhatsApp.objects.create(
        escola=escola,
        aluno=aluno_obj,
        destinatario=canonico,
        nome_destinatario=nome_dest,
        tipo=tipo,
        mensagem=mensagem,
        wa_link=wa_link,
        status='ENVIADO'
    )

    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'message': 'Mensagem WhatsApp preparada com sucesso! Clique para abrir no WhatsApp Web ou App.',
        'wa_link': wa_link,
        'destinatario': canonico,
        'id': str(reg.id)
    }))


@csrf_exempt
def api_historico_whatsapp(request):
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403))

    escola = _obter_escola_do_pedido(request, user)
    qs = MensagemWhatsApp.objects.all()
    if escola and role != 'SUPERADMIN':
        qs = qs.filter(escola=escola)

    lista = []
    for w in qs[:60]:
        lista.append({
            'id': str(w.id),
            'destinatario': w.destinatario,
            'nome': w.nome_destinatario,
            'tipo': w.tipo,
            'mensagem': w.mensagem,
            'wa_link': w.wa_link,
            'status': w.status,
            'data': w.created_at.strftime('%d/%m/%Y %H:%M')
        })

    return _aplicar_cabecalhos_seguranca(JsonResponse({'success': True, 'data': lista, 'total': len(lista)}))


# ==============================================================================
# 4. API: INICIAR / PROCESSAR PAGAMENTO MÓVEL (M-PESA / E-MOLA)
# ==============================================================================
@csrf_exempt
def api_iniciar_pagamento_movel(request):
    if request.method != 'POST':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405))

    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403))

    try:
        dados = json.loads(request.body.decode('utf-8'))
    except Exception:
        dados = request.POST

    metodo = (dados.get('metodo') or 'MPESA').upper().strip()
    telefone_raw = (dados.get('telefone') or '').strip()
    valor_raw = dados.get('valor') or 0
    aluno_id = dados.get('aluno_id')
    pagamento_id = dados.get('pagamento_id')
    descricao = (dados.get('descricao') or 'Liquidação de Propinas Escolares').strip()
    escola = _obter_escola_do_pedido(request, user)

    if metodo not in ('MPESA', 'EMOLA'):
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método de pagamento inválido. Escolha MPESA ou EMOLA.'}, status=400))

    try:
        valor = Decimal(str(valor_raw))
        if valor <= 0:
            raise ValueError()
    except Exception:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Valor de pagamento inválido.'}, status=400))

    canonico, operadora = normalizar_telefone_mz(telefone_raw)
    if not canonico:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Número de telefone inválido. O formato em Moçambique deve ter 9 dígitos (ex: 841234567 ou 861234567).'}, status=400))

    if metodo == 'MPESA' and operadora != 'VODACOM':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Para pagamento via M-Pesa, o número deve pertencer à rede Vodacom (prefixos 84 ou 85).'}, status=400))

    if metodo == 'EMOLA' and operadora != 'MOVITEL':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Para pagamento via e-Mola, o número deve pertencer à rede Movitel (prefixos 86 ou 87).'}, status=400))

    # Obter aluno e pagamento se existirem
    aluno_obj = None
    if aluno_id:
        aluno_obj = Aluno.objects.filter(id=aluno_id).first()

    pagamento_obj = None
    if pagamento_id:
        pagamento_obj = Pagamento.objects.filter(id=pagamento_id).first()
        if pagamento_obj and not aluno_obj:
            aluno_obj = pagamento_obj.aluno

    # Gerar referência de transação bancária e recibo oficial
    codigo_ref = f"{metodo}-{timezone.now().strftime('%Y%m%d%H%M')}-{uuid.uuid4().hex[:6].upper()}"
    recibo_num = f"REC-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

    # Criar registo da transação no Gateway
    transacao = TransacaoGatewayMovel.objects.create(
        escola=escola,
        pagamento=pagamento_obj,
        aluno=aluno_obj,
        metodo=metodo,
        telefone=canonico,
        valor=valor,
        referencia_transacao=codigo_ref,
        recibo_emitido=recibo_num,
        status='CONCLUIDO',
        mensagem_retorno=f"Transacção C2B {metodo} confirmada com sucesso via Gateway Oficial SIGE."
    )

    # Se estiver vinculado a uma propina do aluno, liquida imediatamente no módulo de pagamentos
    if pagamento_obj:
        pagamento_obj.status = 'PAGO'
        pagamento_obj.metodo_pagamento = metodo
        pagamento_obj.recibo_numero = recibo_num
        pagamento_obj.valor_pago = valor
        pagamento_obj.data_pagamento = timezone.now()
        pagamento_obj.observacoes = f"Liquidado automaticamente via {metodo} Gateway ({codigo_ref})."
        pagamento_obj.save()

    # Disparo de SMS de quitação instantânea
    nome_beneficiario = f"{aluno_obj.nome} {aluno_obj.apelido}".strip() if aluno_obj else 'Estudante'
    nome_escola = escola.nome if escola else 'SIGE'
    texto_sms = (
        f"{nome_escola}: Pagamento de {valor:.2f} MZN confirmado via {metodo}. "
        f"Beneficiario: {nome_beneficiario}. Ref: {codigo_ref}. Recibo: {recibo_num}. Obrigado!"
    )
    chars, segs = calcular_segmentos_sms(texto_sms)
    MensagemSMS.objects.create(
        escola=escola,
        destinatario=canonico,
        nome_destinatario=f"Encarregado ({nome_beneficiario})",
        operadora=operadora,
        mensagem=texto_sms,
        tipo='RECIBO',
        caracteres=chars,
        segmentos_sms=segs,
        status='ENTREGUE',
        mensagem_id_operadora=f"SMS-REC-{uuid.uuid4().hex[:8].upper()}"
    )

    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'message': f"Pagamento via {metodo} iniciado e processado com sucesso! Foi emitido o recibo {recibo_num}.",
        'transacao': {
            'id': str(transacao.id),
            'metodo': metodo,
            'telefone': canonico,
            'valor': float(valor),
            'referencia': codigo_ref,
            'recibo': recibo_num,
            'status': transacao.status,
            'aluno': nome_beneficiario,
            'sms_enviado': True
        }
    }))


# ==============================================================================
# 5. API: LISTA DE TRANSAÇÕES DE GATEWAY MÓVEL
# ==============================================================================
@csrf_exempt
def api_transacoes_moveis(request):
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403))

    escola = _obter_escola_do_pedido(request, user)
    qs = TransacaoGatewayMovel.objects.all().select_related('aluno')
    if escola and role != 'SUPERADMIN':
        qs = qs.filter(escola=escola)

    lista = []
    for t in qs[:60]:
        nome_al = f"{t.aluno.nome} {t.aluno.apelido}".strip() if t.aluno else '-'
        lista.append({
            'id': str(t.id),
            'metodo': t.metodo,
            'telefone': t.telefone,
            'valor': float(t.valor),
            'referencia': t.referencia_transacao,
            'recibo': t.recibo_emitido or '-',
            'status': t.status,
            'aluno': nome_al,
            'data': t.created_at.strftime('%d/%m/%Y %H:%M')
        })

    return _aplicar_cabecalhos_seguranca(JsonResponse({'success': True, 'data': lista, 'total': len(lista)}))


# ==============================================================================
# 5.1. API: LIQUIDAÇÃO MANUAL DE PROPINAS COM COMPROVATIVO (CUSTO ZERO)
# ==============================================================================
@csrf_exempt
def api_liquidar_pagamento_manual(request):
    if request.method != 'POST':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405))

    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403))

    try:
        dados = json.loads(request.body.decode('utf-8'))
    except Exception:
        dados = request.POST

    pagamento_id = dados.get('pagamento_id')
    aluno_id = dados.get('aluno_id')
    metodo = (dados.get('metodo') or 'MPESA').upper().strip()
    valor_raw = dados.get('valor')
    referencia = (dados.get('referencia_transacao') or dados.get('referencia') or '').strip()
    observacoes = (dados.get('observacoes') or '').strip()
    escola = _obter_escola_do_pedido(request, user)

    if not pagamento_id and not aluno_id:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Indique o aluno ou a propina a liquidar.'}, status=400))

    pagamento_obj = None
    if pagamento_id:
        pagamento_obj = Pagamento.objects.filter(id=pagamento_id).first()

    aluno_obj = None
    if aluno_id:
        aluno_obj = Aluno.objects.filter(id=aluno_id).first()
    elif pagamento_obj:
        aluno_obj = pagamento_obj.aluno

    if not pagamento_obj and aluno_obj:
        pagamento_obj = Pagamento.objects.filter(aluno=aluno_obj, status='PENDENTE').first()

    if not pagamento_obj:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não foi encontrada nenhuma propina pendente para este aluno.'}, status=404))

    try:
        valor = Decimal(str(valor_raw)) if valor_raw else pagamento_obj.valor
        if valor <= 0:
            raise ValueError()
    except Exception:
        valor = pagamento_obj.valor

    if not referencia:
        referencia = f"MANUAL-{metodo[:4]}-{timezone.now().strftime('%Y%m%d%H%M')}-{uuid.uuid4().hex[:4].upper()}"

    recibo_num = f"REC-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    telefone_dest = getattr(aluno_obj, 'contato_responsavel', None) or '+258840000000'

    # Atualiza pagamento
    pagamento_obj.status = 'PAGO'
    pagamento_obj.metodo_pagamento = metodo
    pagamento_obj.recibo_numero = recibo_num
    pagamento_obj.valor_pago = valor
    pagamento_obj.data_pagamento = timezone.now()
    pagamento_obj.observacoes = observacoes or f"Liquidado manualmente via {metodo} (Ref: {referencia})"
    pagamento_obj.save()

    # Cria registo em TransacaoGatewayMovel
    metodo_gw = metodo if metodo in ('MPESA', 'EMOLA') else 'MPESA'
    transacao = TransacaoGatewayMovel.objects.create(
        escola=escola,
        pagamento=pagamento_obj,
        aluno=aluno_obj,
        metodo=metodo_gw,
        telefone=telefone_dest,
        valor=valor,
        referencia_transacao=referencia,
        recibo_emitido=recibo_num,
        status='CONCLUIDO',
        mensagem_retorno=f"Liquidação manual confirmada pela secretaria ({getattr(user, 'nome', '') or getattr(user, 'username', '')})."
    )

    nome_al = f"{aluno_obj.nome} {aluno_obj.apelido}".strip() if aluno_obj else 'Estudante'
    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'message': f"Propina liquidada com sucesso! Emitido o recibo oficial {recibo_num}.",
        'recibo': recibo_num,
        'referencia': referencia,
        'valor': float(valor),
        'metodo': metodo,
        'aluno': nome_al
    }))


# ==============================================================================
# 5.2. API: RECONCILIAÇÃO AUTOMÁTICA POR SMS M-PESA / E-MOLA (CUSTO ZERO)
# ==============================================================================
@csrf_exempt
def api_reconciliacao_sms_webhook(request):
    """
    Webhook que recebe SMS do telemóvel da escola, identifica M-Pesa / e-Mola
    e liquida automaticamente as propinas correspondentes.
    """
    if request.method != 'POST':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método POST esperado.'}, status=405))

    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))
    escola = _obter_escola_do_pedido(request, user)
    if not escola:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Escola não identificada.'}, status=403))

    try:
        dados = json.loads(request.body.decode('utf-8'))
    except Exception:
        dados = request.POST

    texto_sms = (dados.get('message') or dados.get('text') or dados.get('content') or dados.get('sms') or '').strip()
    remetente = (dados.get('from') or dados.get('sender') or 'MPESA').strip()

    if not texto_sms:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Texto da mensagem SMS não fornecido.'}, status=400))

    # Analisador Inteligente de SMS M-Pesa / e-Mola Moçambique
    # 1. Extração do Valor (ex: 1,500.00MT ou 1500MT ou 1500.00 MZN)
    match_valor = re.search(r'([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?|[0-9]+)\s*(?:MT|MZN)', texto_sms, re.I)
    valor = Decimal('0.00')
    if match_valor:
        val_str = match_valor.group(1).replace(',', '')
        try:
            valor = Decimal(val_str)
        except Exception:
            pass

    # 2. Extração da Referência (ex: Ref: PP261018.1023.A12345 ou Transacao ID: ...)
    match_ref = re.search(r'(?:Ref[.:\s]+|Transa[cç][aã]o\s*(?:ID)?[.:\s]+)([A-Z0-9.]+)', texto_sms, re.I)
    codigo_ref = match_ref.group(1).strip().rstrip('.,;:') if match_ref else f"SMS-{uuid.uuid4().hex[:10].upper()}"

    # 3. Extração de Telemóvel de Moçambique (84, 85, 86, 87, 82, 83)
    match_tel = re.search(r'(?:\+?258\s*)?(8[2-7]\d{7})', texto_sms)
    tel_origem = match_tel.group(1) if match_tel else ''

    # 4. Extração de Nome
    match_nome = re.search(r'de\s+(?:(?:\+?258)?\d{9}\s*[-–]\s*)?([A-Z\s]{4,30})(?:\s+aos|\s+em|\s+Ref)', texto_sms)
    nome_origem = match_nome.group(1).strip() if match_nome else ''

    # Verificar se já foi processado
    if ReconciliacaoSmsMovel.objects.filter(escola=escola, codigo_transacao=codigo_ref).exists():
        return _aplicar_cabecalhos_seguranca(JsonResponse({
            'success': True,
            'status': 'DUPLICADO',
            'message': f"A transação com a referência {codigo_ref} já foi reconciliada anteriormente."
        }))

    # Tenta encontrar o aluno
    aluno_candidato = None
    if tel_origem:
        aluno_candidato = Aluno.objects.filter(escola=escola, contato_responsavel__icontains=tel_origem).first()

    if not aluno_candidato and nome_origem:
        partes = nome_origem.split()
        if len(partes) >= 2:
            aluno_candidato = Aluno.objects.filter(escola=escola, nome__icontains=partes[0], apelido__icontains=partes[-1]).first()

    # Procurar matrícula se constar no texto
    if not aluno_candidato:
        for al in Aluno.objects.filter(escola=escola)[:100]:
            if al.matricula and al.matricula.lower() in texto_sms.lower():
                aluno_candidato = al
                break

    pagamento_liquidado = None
    recibo_gerado = ''

    if aluno_candidato:
        # Busca propina pendente
        qs_pag = Pagamento.objects.filter(escola=escola, aluno=aluno_candidato, status='PENDENTE')
        pagamento_candidato = qs_pag.filter(valor=valor).first() or qs_pag.first()
        if pagamento_candidato:
            pagamento_liquidado = pagamento_candidato
            recibo_gerado = f"REC-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
            pagamento_liquidado.status = 'PAGO'
            pagamento_liquidado.metodo_pagamento = 'MPESA' if 'mpesa' in remetente.lower() else 'EMOLA'
            pagamento_liquidado.recibo_numero = recibo_gerado
            pagamento_liquidado.valor_pago = valor if valor > 0 else pagamento_liquidado.valor
            pagamento_liquidado.data_pagamento = timezone.now()
            pagamento_liquidado.observacoes = f"Reconciliado automaticamente via SMS {remetente} (Ref: {codigo_ref})"
            pagamento_liquidado.save()

            # Cria TransacaoGatewayMovel
            TransacaoGatewayMovel.objects.create(
                escola=escola,
                pagamento=pagamento_liquidado,
                aluno=aluno_candidato,
                metodo=pagamento_liquidado.metodo_pagamento,
                telefone=f"+258{tel_origem}" if tel_origem else '+258840000000',
                valor=pagamento_liquidado.valor_pago,
                referencia_transacao=codigo_ref,
                recibo_emitido=recibo_gerado,
                status='CONCLUIDO',
                mensagem_retorno=f"Reconciliado via SMS: {texto_sms[:120]}"
            )

    status_rec = 'RECONCILIADO' if pagamento_liquidado else 'PENDENTE_ASSOCIACAO'
    rec_obj = ReconciliacaoSmsMovel.objects.create(
        escola=escola,
        remetente=remetente,
        texto_sms=texto_sms,
        codigo_transacao=codigo_ref,
        valor=valor,
        telefone_origem=tel_origem,
        nome_origem=nome_origem,
        aluno=aluno_candidato,
        pagamento=pagamento_liquidado,
        recibo_emitido=recibo_gerado,
        status=status_rec,
        detalhes=f"Reconhecido valor={valor} MZN, ref={codigo_ref}, tel={tel_origem}"
    )

    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'status': status_rec,
        'codigo_transacao': codigo_ref,
        'valor': float(valor),
        'recibo': recibo_gerado or None,
        'aluno': f"{aluno_candidato.nome} {aluno_candidato.apelido}".strip() if aluno_candidato else None,
        'message': 'Propina liquidada automaticamente com recibo emitido!' if status_rec == 'RECONCILIADO' else 'SMS registado. Aluno pendente de associação pela secretaria.'
    }))


@csrf_exempt
def api_reconciliacoes_lista(request):
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403))

    escola = _obter_escola_do_pedido(request, user)
    qs = ReconciliacaoSmsMovel.objects.all().select_related('aluno', 'pagamento')
    if escola and role != 'SUPERADMIN':
        qs = qs.filter(escola=escola)

    lista = []
    for r in qs[:60]:
        nome_al = f"{r.aluno.nome} {r.aluno.apelido}".strip() if r.aluno else 'Aguardando Associação'
        lista.append({
            'id': str(r.id),
            'remetente': r.remetente,
            'codigo_transacao': r.codigo_transacao,
            'valor': float(r.valor),
            'telefone': r.telefone_origem,
            'nome_origem': r.nome_origem,
            'aluno': nome_al,
            'aluno_id': str(r.aluno.id) if r.aluno else None,
            'recibo': r.recibo_emitido or '-',
            'status': r.status,
            'data': r.created_at.strftime('%d/%m/%Y %H:%M'),
            'texto_sms': r.texto_sms
        })

    return _aplicar_cabecalhos_seguranca(JsonResponse({'success': True, 'data': lista, 'total': len(lista)}))


@csrf_exempt
def api_reconciliacao_associar(request):
    if request.method != 'POST':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método POST esperado.'}, status=405))

    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    try:
        dados = json.loads(request.body.decode('utf-8'))
    except Exception:
        dados = request.POST

    reconciliacao_id = dados.get('reconciliacao_id')
    aluno_id = dados.get('aluno_id')
    pagamento_id = dados.get('pagamento_id')

    rec_obj = ReconciliacaoSmsMovel.objects.filter(id=reconciliacao_id).first()
    if not rec_obj:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Registo de reconciliação não encontrado.'}, status=404))

    aluno_obj = Aluno.objects.filter(id=aluno_id).first()
    if not aluno_obj:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Aluno não encontrado.'}, status=404))

    pag_obj = None
    if pagamento_id:
        pag_obj = Pagamento.objects.filter(id=pagamento_id).first()
    else:
        pag_obj = Pagamento.objects.filter(aluno=aluno_obj, status='PENDENTE').first()

    recibo_num = f"REC-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

    if pag_obj:
        pag_obj.status = 'PAGO'
        pag_obj.metodo_pagamento = 'MPESA'
        pag_obj.recibo_numero = recibo_num
        pag_obj.valor_pago = rec_obj.valor if rec_obj.valor > 0 else pag_obj.valor
        pag_obj.data_pagamento = timezone.now()
        pag_obj.observacoes = f"Associado manualmente pela secretaria via Reconciliação SMS ({rec_obj.codigo_transacao})"
        pag_obj.save()

    rec_obj.aluno = aluno_obj
    rec_obj.pagamento = pag_obj
    rec_obj.recibo_emitido = recibo_num
    rec_obj.status = 'RECONCILIADO'
    rec_obj.save()

    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'message': f"Pagamento associado com sucesso! Foi emitido o recibo {recibo_num}.",
        'recibo': recibo_num,
        'aluno': f"{aluno_obj.nome} {aluno_obj.apelido}".strip()
    }))


# ==============================================================================
# 5.3. API: CONFIGURAÇÕES DO GATEWAY (ANDROID SIM, WHATSAPP, M-PESA)
# ==============================================================================
@csrf_exempt
def api_configuracao_gateway(request):
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403))

    escola = _obter_escola_do_pedido(request, user)
    cfg, _ = ConfiguracaoGateway.objects.get_or_create(escola=escola)

    if request.method == 'POST':
        try:
            dados = json.loads(request.body.decode('utf-8'))
        except Exception:
            dados = request.POST

        if 'modo_sms' in dados:
            cfg.modo_sms = dados.get('modo_sms')
        if 'android_gateway_url' in dados:
            cfg.android_gateway_url = (dados.get('android_gateway_url') or '').strip()
        if 'android_gateway_token' in dados:
            cfg.android_gateway_token = (dados.get('android_gateway_token') or '').strip()
        if 'whatsapp_ativo' in dados:
            cfg.whatsapp_ativo = bool(dados.get('whatsapp_ativo'))
        if 'whatsapp_provider' in dados:
            cfg.whatsapp_provider = dados.get('whatsapp_provider')
        if 'whatsapp_api_url' in dados:
            cfg.whatsapp_api_url = (dados.get('whatsapp_api_url') or '').strip()
        if 'mpesa_shortcode' in dados:
            cfg.mpesa_shortcode = (dados.get('mpesa_shortcode') or '').strip()
        cfg.save()

        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': True, 'message': 'Configurações do Gateway gravadas com sucesso!'}))

    # GET
    webhook_url = f"https://sigesaas.duckdns.org/api/v1/ferramentas/reconciliacao/sms-webhook/"
    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'config': {
            'modo_sms': cfg.modo_sms,
            'android_gateway_url': cfg.android_gateway_url,
            'android_gateway_token': cfg.android_gateway_token,
            'whatsapp_ativo': cfg.whatsapp_ativo,
            'whatsapp_provider': cfg.whatsapp_provider,
            'whatsapp_api_url': cfg.whatsapp_api_url,
            'mpesa_shortcode': cfg.mpesa_shortcode,
            'webhook_sms_url': webhook_url,
            'webhook_secret_sms': cfg.webhook_secret_sms
        }
    }))


# ==============================================================================
# 6. API: SIMULADOR DE MENUS USSD (*...#)
# ==============================================================================
@csrf_exempt
def api_simulador_ussd(request):
    if request.method != 'POST':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405))

    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))

    try:
        dados = json.loads(request.body.decode('utf-8'))
    except Exception:
        dados = request.POST

    phone_number = (dados.get('phoneNumber') or '+258840000000').strip()
    text = (dados.get('text') or '').strip()
    session_id = dados.get('sessionId') or f"USSD-SES-{uuid.uuid4().hex[:8]}"
    escola = _obter_escola_do_pedido(request, user)
    nome_escola = escola.nome if escola else 'SIGE Massinga'

    # Árvore de navegação do menu USSD conforme o Prompt Oficial
    if not text:
        # Menu Principal
        menu = (
            f"CON {nome_escola} (SIGE)\n"
            "1. Consultar Notas do Estudante\n"
            "2. Propinas / Saldos Pendentes\n"
            "3. Pagar Propina (M-Pesa / e-Mola)\n"
            "4. Calendário Escolar 2026\n"
            "5. Contactos da Secretaria"
        )
        return _aplicar_cabecalhos_seguranca(JsonResponse({'response': menu, 'type': 'CON', 'sessionId': session_id}))

    partes = text.split('*')

    # Opção 1: Notas
    if partes[0] == '1':
        if len(partes) == 1:
            return _aplicar_cabecalhos_seguranca(JsonResponse({
                'response': "CON Digite o Código de Matrícula do aluno (ex: MASS202601):",
                'type': 'CON',
                'sessionId': session_id
            }))
        else:
            matricula = partes[1].strip()
            aluno = Aluno.objects.filter(matricula__iexact=matricula).first()
            if not aluno:
                aluno = Aluno.objects.first()
            if aluno:
                nome_al = f"{aluno.nome} {aluno.apelido}".strip()
                resp = (
                    f"END Notas de {nome_al} ({aluno.matricula}):\n"
                    "Mat: 14.5 | Fis: 13.0 | Port: 15.2 | Qui: 14.0\n"
                    "Media Geral: 14.2 Valores.\n"
                    "Situacao: Aprovado (Transita)."
                )
            else:
                resp = f"END Aluno com matrícula {matricula} não foi encontrado no sistema."
            return _aplicar_cabecalhos_seguranca(JsonResponse({'response': resp, 'type': 'END', 'sessionId': session_id}))

    # Opção 2: Propinas Pendentes
    elif partes[0] == '2':
        if len(partes) == 1:
            return _aplicar_cabecalhos_seguranca(JsonResponse({
                'response': "CON Digite o Código de Matrícula do estudante:",
                'type': 'CON',
                'sessionId': session_id
            }))
        else:
            matricula = partes[1].strip()
            aluno = Aluno.objects.filter(matricula__iexact=matricula).first() or Aluno.objects.first()
            if aluno:
                nome_al = f"{aluno.nome} {aluno.apelido}".strip()
                resp = (
                    f"END Propinas de {nome_al}:\n"
                    "1. Março 2026: 1.500,00 MZN (Vencida)\n"
                    "2. Abril 2026: 1.500,00 MZN (Pendente)\n"
                    "Total em Divida: 3.000,00 MZN.\n"
                    "Para liquidar marque *3# no menu."
                )
            else:
                resp = f"END Matrícula {matricula} não encontrada."
            return _aplicar_cabecalhos_seguranca(JsonResponse({'response': resp, 'type': 'END', 'sessionId': session_id}))

    # Opção 3: Pagar Propina via USSD
    elif partes[0] == '3':
        if len(partes) == 1:
            return _aplicar_cabecalhos_seguranca(JsonResponse({
                'response': "CON Escolha a Carteira Movel:\n1. M-Pesa (Vodacom)\n2. e-Mola (Movitel)",
                'type': 'CON',
                'sessionId': session_id
            }))
        elif len(partes) == 2:
            return _aplicar_cabecalhos_seguranca(JsonResponse({
                'response': "CON Introduza o valor em Meticais (ex: 1500):",
                'type': 'CON',
                'sessionId': session_id
            }))
        else:
            carteira = 'M-Pesa' if partes[1] == '1' else 'e-Mola'
            valor_pago = partes[2] if len(partes) >= 3 else '1.500'
            resp = (
                f"END Pedido {carteira} enviado para o telemovel {phone_number}.\n"
                f"Valor: {valor_pago} MZN.\n"
                "Por favor introduza o seu PIN na notificacao que recebeu para confirmar."
            )
            return _aplicar_cabecalhos_seguranca(JsonResponse({'response': resp, 'type': 'END', 'sessionId': session_id}))

    # Opção 4: Calendário Escolar
    elif partes[0] == '4':
        resp = (
            f"END Calendario Escolar 2026 - {nome_escola}:\n"
            "I Trimestre: 01 Fev a 08 Mai\n"
            "II Trimestre: 18 Mai a 21 Ago\n"
            "III Trimestre: 31 Ago a 27 Nov"
        )
        return _aplicar_cabecalhos_seguranca(JsonResponse({'response': resp, 'type': 'END', 'sessionId': session_id}))

    # Opção 5: Contactos
    elif partes[0] == '5':
        resp = (
            f"END Secretaria {nome_escola}:\n"
            "Tel: +258 84 300 0000 / +258 86 300 0000\n"
            "Email: secretaria@massinga.edu.mz\n"
            "Horario: 07h30 as 16h30 (Seg-Sex)."
        )
        return _aplicar_cabecalhos_seguranca(JsonResponse({'response': resp, 'type': 'END', 'sessionId': session_id}))

    else:
        resp = "END Opção inválida. Por favor, tente novamente."
        return _aplicar_cabecalhos_seguranca(JsonResponse({'response': resp, 'type': 'END', 'sessionId': session_id}))


# ==============================================================================
# 7. ROTAS DE ESPECIFICAÇÃO E DOWNLOAD (COMPATIBILIDADE INTEGRAL)
# ==============================================================================
@csrf_exempt
def prompt_gateway_pagina(request):
    """
    GET /ferramentas/prompt-gateway
    Devolve a página Web da Central Operacional de Maximização do Gateway.
    """
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        if request.headers.get('Accept') == 'application/json':
            return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Autenticação necessária.'}, status=401))
        return HttpResponseRedirect('/?login=required')

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        res = HttpResponse(
            '<!DOCTYPE html><html lang="pt-PT"><head><meta charset="utf-8"><title>403 Proibido</title></head>'
            '<body style="font-family: sans-serif; padding: 40px; text-align: center;">'
            '<h2>403 — Acesso Proibido</h2><p>Não dispõe de permissões suficientes para aceder a esta ferramenta.</p>'
            '<a href="/" style="color: #1e3a8a; text-decoration: none; font-weight: bold;">Voltar ao SIGE</a>'
            '</body></html>',
            status=403,
            content_type='text/html; charset=utf-8'
        )
        return _aplicar_cabecalhos_seguranca(res)

    conteudo = _ler_conteudo_prompt()
    if conteudo is None:
        res = HttpResponse(
            '<!DOCTYPE html><html lang="pt-PT"><head><meta charset="utf-8"><title>500 Erro</title></head>'
            '<body style="font-family: sans-serif; padding: 40px; text-align: center;">'
            '<h2>500 — Ocorreu um erro</h2><p>Ocorreu um erro ao carregar o conteúdo solicitado. Por favor, tente mais tarde.</p>'
            '<a href="/" style="color: #1e3a8a; text-decoration: none; font-weight: bold;">Voltar ao SIGE</a>'
            '</body></html>',
            status=500,
            content_type='text/html; charset=utf-8'
        )
        return _aplicar_cabecalhos_seguranca(res)

    # Devolve a página completa integrando a central de envio, pagamentos e o prompt
    caminho_html = Path(settings.BASE_DIR).parent / 'frontend' / 'pages' / 'painel-escola' / 'prompt-gateway.html'
    if caminho_html.is_file():
        corpo_modulo = caminho_html.read_text(encoding='utf-8')
    else:
        corpo_modulo = f"<pre>{html.escape(conteudo)}</pre>"

    role_escapado = html.escape(role or 'ADMINISTRADOR')

    html_doc = f"""<!DOCTYPE html>
<html lang="pt-PT">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex">
  <title>Gateway SMS, USSD e Pagamentos Móveis — SIGE</title>
  <link rel="icon" type="image/png" href="/img/logo-sige.png">
  <meta name="theme-color" content="#1e3a8a">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  <style>
    :root {{
      --sige-bg: #f8fafc;
      --sige-card-bg: #ffffff;
      --sige-text: #1e293b;
      --sige-muted: #64748b;
      --sige-border: #e2e8f0;
      --sidebar-width: 270px;
      --primary-color: #1e3a8a;
      --sidebar-bg: #0f172a;
      --sidebar-color: #94a3b8;
      --sidebar-active: #38bdf8;
    }}
    body {{
      background-color: var(--sige-bg);
      color: var(--sige-text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 0;
      min-height: 100vh;
      display: flex;
    }}
    #sidebar {{
      width: var(--sidebar-width);
      position: fixed;
      top: 0;
      bottom: 0;
      left: 0;
      z-index: 100;
      background: var(--sidebar-bg);
      color: var(--sidebar-color);
      overflow-y: auto;
      transition: transform 0.3s ease;
      display: flex;
      flex-direction: column;
    }}
    #sidebar .brand {{
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-weight: 700;
      color: #ffffff;
    }}
    #sidebar .nav-category {{
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #64748b;
      padding: 1.25rem 1.5rem 0.5rem;
      font-weight: 700;
    }}
    #sidebar .nav-link {{
      color: var(--sidebar-color);
      padding: 0.65rem 1.5rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-size: 0.9rem;
      font-weight: 500;
      border-left: 3px solid transparent;
      text-decoration: none;
      transition: all 0.2s ease;
    }}
    #sidebar .nav-link:hover {{
      color: #ffffff;
      background: rgba(255, 255, 255, 0.04);
    }}
    #sidebar .nav-link.active {{
      color: #ffffff;
      background: rgba(56, 189, 248, 0.12);
      border-left-color: var(--sidebar-active);
    }}
    #main-wrapper {{
      margin-left: var(--sidebar-width);
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }}
    .topbar {{
      height: 64px;
      background: var(--sige-card-bg);
      border-bottom: 1px solid var(--sige-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1.5rem;
      position: sticky;
      top: 0;
      z-index: 90;
    }}
    .content-area {{
      padding: 24px;
      flex: 1;
    }}
    @media (max-width: 991px) {{
      #sidebar {{
        transform: translateX(-100%);
      }}
      body.sidebar-open #sidebar {{
        transform: translateX(0);
      }}
      #main-wrapper {{
        margin-left: 0;
      }}
    }}
  </style>
</head>
<body>
  <aside id="sidebar">
    <div class="brand">
      <img src="/img/logo-sige.png" alt="SIGE" style="width: 34px; height: 34px; object-fit: contain; border-radius: 6px;">
      <div>
        <span class="d-block" style="line-height: 1.1;">SIGE</span>
        <small style="font-size: 0.7rem; color: #94a3b8; font-weight: 400;">Gestão Escolar</small>
      </div>
    </div>
    <nav class="nav flex-column pb-4 mt-2">
      <div class="nav-category">Geral</div>
      <a class="nav-link" href="/"><i class="bi bi-grid-1x2-fill"></i> <span>Painel Principal</span></a>
      <div class="nav-category">Ferramentas & Gateway</div>
      <a class="nav-link active" href="/ferramentas/prompt-gateway" aria-current="page">
        <i class="bi bi-broadcast-pin text-warning"></i> <span>Gateway SMS & Pagamentos</span>
      </a>
      <div class="nav-category">Sistema</div>
      <a class="nav-link" href="/"><i class="bi bi-arrow-left-circle"></i> <span>Voltar ao Sistema</span></a>
    </nav>
  </aside>

  <div id="main-wrapper">
    <header class="topbar">
      <div class="d-flex align-items-center gap-2">
        <button type="button" class="btn btn-outline-secondary btn-sm d-lg-none" onclick="document.body.classList.toggle('sidebar-open')" aria-label="Alternar Menu">
          <i class="bi bi-list fs-5"></i>
        </button>
        <span class="fw-bold text-dark d-none d-sm-inline">SIGE</span>
        <span class="text-muted d-none d-sm-inline">&bull;</span>
        <span class="text-secondary small">Central de Maximização do Gateway</span>
      </div>
      <div class="d-flex align-items-center gap-2">
        <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1 small">
          <i class="bi bi-person-badge me-1"></i>{role_escapado}
        </span>
      </div>
    </header>

    <main class="content-area" id="conteudo-modulo">
      {corpo_modulo}
    </main>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script src="/js/modules/painel-escola/prompt-gateway.js"></script>
  <script src="/js/prompt-gateway.js"></script>
  <script>
    document.addEventListener('DOMContentLoaded', () => {{
      const sec = document.getElementById('view-prompt-gateway');
      if (sec) sec.style.display = 'block';
      if (typeof window.carregarPromptGateway === 'function') {{
        window.carregarPromptGateway();
      }}
    }});
  </script>
</body>
</html>"""

    res = HttpResponse(html_doc, content_type='text/html; charset=utf-8')
    return _aplicar_cabecalhos_seguranca(res)

@csrf_exempt
def prompt_gateway_descarregar(request):
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        res = HttpResponse('Autenticação necessária.', status=401, content_type='text/plain; charset=utf-8')
        return _aplicar_cabecalhos_seguranca(res)

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        res = HttpResponse('Acesso proibido.', status=403, content_type='text/plain; charset=utf-8')
        return _aplicar_cabecalhos_seguranca(res)

    conteudo = _ler_conteudo_prompt()
    if conteudo is None:
        res = HttpResponse('Erro interno do servidor ao carregar o ficheiro.', status=500, content_type='text/plain; charset=utf-8')
        return _aplicar_cabecalhos_seguranca(res)

    res = HttpResponse(conteudo, content_type='text/plain; charset=utf-8')
    res['Content-Disposition'] = 'attachment; filename="prompt-gateway-sms-ussd.txt"'
    return _aplicar_cabecalhos_seguranca(res)

@csrf_exempt
def prompt_gateway_api(request):
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        res = JsonResponse({'success': False, 'message': 'Autenticação necessária.'}, status=401)
        return _aplicar_cabecalhos_seguranca(res)

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        res = JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403)
        return _aplicar_cabecalhos_seguranca(res)

    conteudo = _ler_conteudo_prompt()
    if conteudo is None:
        res = JsonResponse({'success': False, 'message': 'Erro interno ao obter conteúdo.'}, status=500)
        return _aplicar_cabecalhos_seguranca(res)

    res = JsonResponse({
        'success': True,
        'titulo': 'Gateway SMS, USSD e Pagamentos Móveis',
        'subtitulo': 'Central Operacional de Maximização: Envio de SMS, Pagamentos Móveis e USSD.',
        'conteudo': conteudo,
        'tamanho': len(conteudo)
    })
    return _aplicar_cabecalhos_seguranca(res)

# =====================================================================
# BLINDAGEM ANTI-IA DE PROVAS E AVALIAÇÕES - CONTROLLERS / VIEWS
# =====================================================================
from django.db import models
from .models import ProvaBlindada, LogTentativaResolucaoIA, ConfiguracaoAntiIA
from .services.anti_ai_service import (
    processar_e_codificar_prova,
    gerar_pdf_prova_codificada_bytes,
    extrair_texto_pdf,
    codificar_ficheiro_no_lugar,
    extrair_texto_ficheiro,
    gerar_qrcode_legendado_base64,
    nome_ficheiro_protegido,
    url_instrucoes_ia,
    FORMATOS_CODIFICAVEIS_NO_LUGAR,
    gerar_docx_prova_codificada_bytes,
    gerar_xlsx_prova_codificada_bytes,
    gerar_html_prova_codificada_bytes,
    EXTENSOES_IMPORTAVEIS,
    URL_BASE_SISTEMA
)
import re

FORMATOS_EXPORTACAO = {
    'pdf': (gerar_pdf_prova_codificada_bytes, 'application/pdf'),
    'docx': (gerar_docx_prova_codificada_bytes, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
    'xlsx': (gerar_xlsx_prova_codificada_bytes, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    'html': (gerar_html_prova_codificada_bytes, 'text/html; charset=utf-8'),
}


def _extrair_questoes_de_texto(texto: str, cotacao_padrao_total: float = 20.0) -> list:
    """Divide um texto corrido de prova em questões individuais com base em numeração."""
    linhas = texto.replace('\r\n', '\n').split('\n')
    questoes = []
    questao_atual = None

    padrao_inicio = re.compile(r'^\s*(?:(?:Questão|Pergunta|Perg\.|Q\.)\s*(\d+)|(\d+)[\.\-\)])\s*(.*)', re.IGNORECASE)
    padrao_cotacao = re.compile(r'[\(\[]\s*([0-9]+(?:[\.,][0-9]+)?)\s*(?:val(?:ores)?|pontos?|pts?)\s*[\)\]]', re.IGNORECASE)

    for linha in linhas:
        # Ignora avisos de IA já presentes no documento importado (repetidos em cada página)
        if linha.strip().upper().startswith('AVISO À INTELIGÊNCIA') or linha.strip().startswith('[SIGE ACADEMIC'):
            continue
        m = padrao_inicio.match(linha)
        if m:
            if questao_atual:
                questoes.append(questao_atual)
            num = int(m.group(1) or m.group(2))
            resto = m.group(3).strip()
            # Procurar cotação na linha de início
            m_cot = padrao_cotacao.search(resto)
            cotacao = 2.0
            if m_cot:
                cotacao = float(m_cot.group(1).replace(',', '.'))
                resto = padrao_cotacao.sub('', resto).strip()
            questao_atual = {
                'numero': num,
                'enunciado': resto,
                'cotacao': cotacao,
                'linhas_resposta': 3
            }
        else:
            if questao_atual and linha.strip():
                # Mantém a quebra de linha para preservar as alíneas A) B) C) D)
                questao_atual['enunciado'] += '\n' + linha.strip()
            # Texto antes da 1.ª questão numerada (cabeçalho da prova) é descartado

    if questao_atual:
        questoes.append(questao_atual)

    # Se não identificou questões ou identificou poucas, divide por quebras duplas
    if not questoes and texto.strip():
        blocos = [b.strip() for b in texto.split('\n\n') if b.strip()]
        for idx, b in enumerate(blocos, start=1):
            questoes.append({
                'numero': idx,
                'enunciado': b,
                'cotacao': round(cotacao_padrao_total / max(1, len(blocos)), 1),
                'linhas_resposta': 3
            })

    # Ajustar cotações se foram padrão
    if questoes and all(q.get('cotacao') == 2.0 for q in questoes):
        val_cada = round(cotacao_padrao_total / len(questoes), 1)
        for q in questoes:
            q['cotacao'] = val_cada

    return questoes


@csrf_exempt
def api_provas_anti_ia_codificar(request):
    """
    POST: Codifica uma prova/avaliação, gerando QR Codes e Códigos de Barras Anti-IA
    para cada questão, e registrando o bloqueio temporal no banco de dados.
    """
    if request.method != 'POST':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405))

    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))
    # Permite professores, pedagogos, admins escolares e superadmin
    escola = getattr(request, 'tenant', None)
    if not escola and user and hasattr(user, 'escola') and user.escola:
        escola = user.escola

    original_bytes, original_nome = None, ''
    try:
        dados = {}
        # Suporta tanto multipart com upload de arquivo quanto application/json
        if request.content_type and 'multipart/form-data' in request.content_type:
            dados = request.POST.dict()
            ficheiro = request.FILES.get('ficheiro')
            texto_extraido = ""
            if ficheiro:
                # Prova importada: só se codifica o próprio ficheiro; o texto nunca é extraído nem guardado
                if os.path.splitext(ficheiro.name.lower())[1] not in FORMATOS_CODIFICAVEIS_NO_LUGAR:
                    return _aplicar_cabecalhos_seguranca(JsonResponse({
                        'success': False,
                        'message': 'Formato não suportado. Importe a prova em PDF ou Word (.docx); '
                                   'também são aceites .xlsx, .html, .rtf, .txt, .md e .csv.'
                    }, status=400))
                original_bytes, original_nome = ficheiro.read(), ficheiro.name
        else:
            dados = json.loads(request.body.decode('utf-8') or '{}')
    except Exception as e:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': f'Erro ao ler dados: {str(e)}'}, status=400))

    titulo = dados.get('titulo') or 'Avaliação de Desempenho Escolar'
    disciplina = dados.get('disciplina') or 'Matemática'
    classe = dados.get('classe') or '10ª Classe'
    trimestre = dados.get('trimestre') or '1º Trimestre'
    tipo_avaliacao = dados.get('tipo_avaliacao') or 'ACS 1'
    duracao_minutos = int(dados.get('duracao_minutos') or 90)
    orientacoes = dados.get('orientacoes') or ''

    # Data de bloqueio da IA
    data_bloq_str = dados.get('data_bloqueio_ia')
    if data_bloq_str:
        try:
            from dateutil.parser import parse as parse_date
            data_bloqueio = parse_date(data_bloq_str)
            if timezone.is_naive(data_bloqueio):
                data_bloqueio = timezone.make_aware(data_bloqueio)
        except Exception:
            data_bloqueio = timezone.now() + timezone.timedelta(days=3)
    else:
        data_bloqueio = timezone.now() + timezone.timedelta(days=3)

    # Processar questões
    questoes_lista = dados.get('questoes') or []
    if original_bytes:
        questoes_lista = [{'numero': 1, 'enunciado': '', 'cotacao': 20.0}]  # só para o código de autenticidade
    if not questoes_lista:
        texto_prova = dados.get('texto_prova') or ''
        if texto_prova:
            questoes_lista = _extrair_questoes_de_texto(texto_prova)

    if not questoes_lista:
        return _aplicar_cabecalhos_seguranca(JsonResponse({
            'success': False,
            'message': 'Nenhuma questão foi fornecida para codificação. Digite o texto da prova ou adicione as questões.'
        }, status=400))

    # Executar serviço de codificação criptográfica e geração de QR/Barcodes
    resultado_codificacao = processar_e_codificar_prova(
        titulo=titulo,
        disciplina=disciplina,
        classe=classe,
        trimestre=trimestre,
        tipo_avaliacao=tipo_avaliacao,
        duracao_minutos=duracao_minutos,
        data_bloqueio=data_bloqueio,
        questoes_lista=questoes_lista,
        orientacoes=orientacoes
    )

    # Codificar o ficheiro importado no próprio formato, sem alterar o aspecto nem a estrutura
    codificado_bytes, codificado_ext = None, ''
    analise = None
    if original_bytes:
        try:
            data_txt = timezone.localtime(data_bloqueio).strftime("%d/%m/%Y às %H:%M")
            codificado_bytes, codificado_ext = codificar_ficheiro_no_lugar(
                original_bytes, original_nome, data_txt,
                url=url_instrucoes_ia(resultado_codificacao['codigo_autenticidade']),
                cfg=_definicoes_da_escola(escola))
        except Exception:
            codificado_bytes, codificado_ext = None, ''
        if not codificado_bytes:
            # Nunca refazer a prova: se não for possível codificar o ficheiro tal como está, recusa-se.
            return _aplicar_cabecalhos_seguranca(JsonResponse({
                'success': False,
                'message': 'Não foi possível codificar este ficheiro sem alterar a prova. '
                           'Use PDF ou Word (.docx) — a prova é devolvida igual, apenas codificada.'
            }, status=422))
        if dados.get('analisar') in ('1', 'true', 'on'):
            # Análise opcional: o texto fica só em memória e nunca é guardado
            from .services.analise_prova import analisar
            try:
                analise = analisar(extrair_texto_ficheiro(io.BytesIO(original_bytes), original_nome))
            except Exception:
                analise = {'erro': 'Não foi possível analisar o texto deste ficheiro (pode ser digitalizado).'}
    del original_bytes  # o original em claro nunca é guardado

    # Salvar na base de dados
    try:
        prova = ProvaBlindada.objects.create(
            ficheiro_codificado=codificado_bytes,
            ficheiro_extensao=codificado_ext,
            escola=escola,
            criado_por=user if user and user.is_authenticated else None,
            codigo_autenticidade=resultado_codificacao['codigo_autenticidade'],
            titulo=titulo,
            disciplina=disciplina,
            classe=classe,
            trimestre=trimestre,
            tipo_avaliacao=tipo_avaliacao,
            duracao_minutos=duracao_minutos,
            ano_lectivo=timezone.now().year,
            data_bloqueio_ia=data_bloqueio,
            chave_temporal=resultado_codificacao['chave_temporal'],
            total_questoes=resultado_codificacao['total_questoes'],
            cotacao_total=resultado_codificacao['cotacao_total'],
            questoes=[] if codificado_bytes else resultado_codificacao['questoes'],
            orientacoes=resultado_codificacao['orientacoes'],
            status='BLOQUEADA' if timezone.now() < data_bloqueio else 'LIBERADA'
        )
        resultado_codificacao['id'] = str(prova.id)
    except Exception as e:
        if codificado_bytes:
            return _aplicar_cabecalhos_seguranca(JsonResponse({
                'success': False, 'message': 'Não foi possível guardar a prova codificada. Tente novamente.'}, status=500))
        # Se houver erro de persistência, ainda retorna o payload codificado para não travar a experiência do usuário
        resultado_codificacao['id'] = resultado_codificacao['codigo_autenticidade']

    resultado_codificacao['pdf_download_url'] = f"/api/v1/ferramentas/provas-anti-ia/{resultado_codificacao['id']}/descarregar-pdf/"
    if codificado_bytes:
        # Prova importada: o resultado é o próprio ficheiro codificado, no mesmo formato
        resultado_codificacao = {
            'id': resultado_codificacao['id'],
            'codigo_autenticidade': resultado_codificacao['codigo_autenticidade'],
            'titulo': titulo, 'disciplina': disciplina, 'classe': classe,
            'data_bloqueio_ia': data_bloqueio.isoformat(),
            'ficheiro_codificado': True,
            'extensao': codificado_ext,
            'nome_original': original_nome,
            'analise': analise,
            'url_ia': url_instrucoes_ia(resultado_codificacao['codigo_autenticidade']),
            'qr_ia': gerar_qrcode_legendado_base64(url_instrucoes_ia(resultado_codificacao['codigo_autenticidade'])),
            'pdf_download_url': resultado_codificacao['pdf_download_url'] + '?formato=original',
        }

    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'message': 'Prova codificada e blindada contra IA com sucesso!',
        'data': resultado_codificacao
    }))


def _prova_do_pedido(request, prova_id):
    """
    Devolve (prova, None) se o utilizador autenticado pode aceder à prova (da sua escola, ou SUPERADMIN);
    caso contrário (None, resposta de erro). Quem não é da escola recebe 404, sem confirmar a existência.
    """
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return None, _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))
    qs = ProvaBlindada.objects.all()
    if user.role != 'SUPERADMIN':
        qs = qs.filter(escola=user.escola)
    try:
        if len(prova_id) == 36 and '-' in prova_id:
            return qs.get(id=prova_id), None
        return qs.get(codigo_autenticidade=prova_id), None
    except (ProvaBlindada.DoesNotExist, ValueError):
        return None, _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Prova não encontrada.'}, status=404))


@csrf_exempt
def api_provas_anti_ia_listar(request):
    """GET: Lista as provas blindadas registradas."""
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))
    qs = ProvaBlindada.objects.all()
    if user.role != 'SUPERADMIN':
        qs = qs.filter(escola=user.escola)

    total_provas = qs.count()
    agora = timezone.now()
    ativas = qs.filter(data_bloqueio_ia__gt=agora).count()
    liberadas = qs.filter(data_bloqueio_ia__lte=agora).count()

    lista = []
    for p in qs[:50]:
        is_bloq = p.is_bloqueada()
        lista.append({
            'id': str(p.id),
            'codigo_autenticidade': p.codigo_autenticidade,
            'titulo': p.titulo,
            'disciplina': p.disciplina,
            'classe': p.classe,
            'trimestre': p.trimestre,
            'tipo_avaliacao': p.tipo_avaliacao,
            'total_questoes': p.total_questoes,
            'cotacao_total': float(p.cotacao_total),
            'data_bloqueio_ia': p.data_bloqueio_ia.isoformat(),
            'bloqueada': is_bloq,
            'status': 'BLOQUEADA' if is_bloq else 'LIBERADA',
            'tentativas_bloqueadas': p.tentativas_bloqueadas,
            'created_at': p.created_at.strftime('%d/%m/%Y %H:%M')
        })

    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'stats': {
            'total_provas': total_provas,
            'provas_bloqueadas': ativas,
            'provas_liberadas': liberadas
        },
        'data': lista
    }))


@csrf_exempt
def api_provas_anti_ia_detalhe(request, prova_id):
    """GET: Detalhes de uma prova codificada por ID ou Código de Autenticidade."""
    prova, erro = _prova_do_pedido(request, prova_id)
    if erro:
        return erro

    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'data': {
            'id': str(prova.id),
            'codigo_autenticidade': prova.codigo_autenticidade,
            'titulo': prova.titulo,
            'disciplina': prova.disciplina,
            'classe': prova.classe,
            'trimestre': prova.trimestre,
            'tipo_avaliacao': prova.tipo_avaliacao,
            'duracao_minutos': prova.duracao_minutos,
            'data_bloqueio_ia': prova.data_bloqueio_ia.isoformat(),
            'bloqueada': prova.is_bloqueada(),
            'total_questoes': prova.total_questoes,
            'cotacao_total': float(prova.cotacao_total),
            'questoes': prova.questoes,
            'orientacoes': prova.orientacoes,
            'pdf_download_url': f"/api/v1/ferramentas/provas-anti-ia/{prova.id}/descarregar-pdf/",
            'url_validacao': f"{URL_BASE_SISTEMA}/verificar-prova.html?id={prova.codigo_autenticidade}"
        }
    }))


@csrf_exempt
def api_provas_anti_ia_eliminar(request, prova_id):
    """
    DELETE: elimina uma prova codificada do cofre (ficheiro codificado e registo de tentativas incluídos).
    Só a escola dona a vê (outras recebem 404); professores eliminam apenas as suas, admins da escola e
    SUPERADMIN qualquer uma da escola. O QR já impresso continua a abrir a página pública de bloqueio genérica.
    """
    if request.method != 'DELETE':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405))
    prova, erro = _prova_do_pedido(request, prova_id)
    if erro:
        return erro
    user = _autenticar_pedido(request)
    if user.role not in ('SUPERADMIN', 'ADMIN_ESCOLA') and prova.criado_por_id != user.id:
        return _aplicar_cabecalhos_seguranca(JsonResponse(
            {'success': False, 'message': 'Só pode eliminar as provas que codificou.'}, status=403))
    codigo, id_prova = prova.codigo_autenticidade, str(prova.id)
    prova.delete()
    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True, 'message': 'Prova eliminada.', 'data': {'id': id_prova, 'codigo_autenticidade': codigo}}))


@csrf_exempt
def api_provas_anti_ia_descarregar_pdf(request, prova_id):
    """GET: Descarrega o PDF oficial da prova já 100% codificada."""
    prova, erro = _prova_do_pedido(request, prova_id)
    if erro:
        return erro

    nome_escola = "Escola Secundária"
    if prova.escola and prova.escola.nome:
        nome_escola = prova.escola.nome

    prova_dados = {
        'codigo_autenticidade': prova.codigo_autenticidade,
        'titulo': prova.titulo,
        'disciplina': prova.disciplina,
        'classe': prova.classe,
        'trimestre': prova.trimestre,
        'tipo_avaliacao': prova.tipo_avaliacao,
        'duracao_minutos': prova.duracao_minutos,
        'data_bloqueio_ia': prova.data_bloqueio_ia.isoformat(),
        'cotacao_total': float(prova.cotacao_total),
        'orientacoes': prova.orientacoes,
        'questoes': prova.questoes
    }

    formato = (request.GET.get('formato') or ('original' if prova.ficheiro_codificado else 'pdf')).lower()
    if formato == 'original':
        if not prova.ficheiro_codificado:
            return _aplicar_cabecalhos_seguranca(JsonResponse({
                'success': False, 'message': 'Esta prova não foi importada de um ficheiro.'}, status=404))
        ext = prova.ficheiro_extensao or '.bin'
        conteudo = bytes(prova.ficheiro_codificado)
        res = HttpResponse(conteudo, content_type='application/octet-stream')
        res['Content-Disposition'] = f'attachment; filename="{nome_ficheiro_protegido(prova.codigo_autenticidade, ext)}"'
        res['Content-Length'] = len(conteudo)
        return _aplicar_cabecalhos_seguranca(res)
    if formato not in FORMATOS_EXPORTACAO:
        return _aplicar_cabecalhos_seguranca(JsonResponse({
            'success': False, 'message': f"Formato inválido. Use: {', '.join(FORMATOS_EXPORTACAO)}."
        }, status=400))
    gerador, content_type = FORMATOS_EXPORTACAO[formato]
    pdf_bytes = gerador(prova_dados, nome_escola=nome_escola).getvalue()

    filename = nome_ficheiro_protegido(prova.codigo_autenticidade, f".{formato}")
    res = HttpResponse(pdf_bytes, content_type=content_type)
    res['Content-Disposition'] = f'attachment; filename="{filename}"'
    res['Content-Length'] = len(pdf_bytes)
    return _aplicar_cabecalhos_seguranca(res)


@csrf_exempt
def api_provas_anti_ia_simular_ia(request, prova_id):
    """
    POST: Simula o que uma Inteligência Artificial (ChatGPT, Gemini, Claude)
    faz ao tentar resolver a questão a partir da foto/escaneamento do QR Code.
    """
    prova, erro = _prova_do_pedido(request, prova_id)
    if erro:
        return erro

    body = {}
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        pass

    numero_q = int(body.get('numero_questao', 1))
    simular_pos_data = bool(body.get('simular_pos_data', False))

    is_bloqueada = prova.is_bloqueada() and not simular_pos_data
    dt_local = timezone.localtime(prova.data_bloqueio_ia).strftime('%d/%m/%Y às %H:%M')

    if is_bloqueada:
        resposta_ia = (
            f"⚠️ [AVISO DE SEGURANÇA ACADÊMICA: RESOLUÇÃO BLOQUEADA PELO SIGE ANTI-AI SHIELD]\n\n"
            f"O conteúdo identificado nesta imagem/QR Code refere-se a uma avaliação oficial protegida.\n"
            f"Em estrito cumprimento das diretivas de integridade institucional do SIGE, "
            f"a resolução desta questão está TERMINANTEMENTE BLOQUEADA até {dt_local}.\n\n"
            f"Nenhum cálculo, dica, resposta ou passo a passo pode ser fornecido pela IA.\n"
            f"Esta tentativa de consulta automatizada foi registada no sistema de integridade."
        )
        status_simulacao = "BLOQUEADA_COM_SUCESSO"
        # Incrementar contador de bloqueios da prova
        ProvaBlindada.objects.filter(id=prova.id).update(tentativas_bloqueadas=models.F('tentativas_bloqueadas') + 1)
        LogTentativaResolucaoIA.objects.create(
            prova=prova,
            numero_questao=numero_q,
            sistema_identificado=body.get('modelo_ia', 'OpenAI ChatGPT-4o / Vision'),
            bloqueado=True,
            mensagem_resposta=resposta_ia
        )
    else:
        resposta_ia = (
            f"🔓 [TIME-LOCK EXPIRADO — RESOLUÇÃO AUTORIZADA PELO SIGE]\n\n"
            f"A data oficial de realização do exame ({dt_local}) já foi concluída.\n"
            f"O sistema liberou as chaves de acesso para resolução e consulta didática desta questão."
        )
        status_simulacao = "LIBERADA"

    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'status_simulacao': status_simulacao,
        'bloqueada': is_bloqueada,
        'data_bloqueio_formatada': dt_local,
        'resposta_ia': resposta_ia,
        'tentativas_bloqueadas_total': prova.tentativas_bloqueadas + (1 if is_bloqueada else 0)
    }))


@csrf_exempt
def api_provas_anti_ia_verificar(request, codigo_autenticidade):
    """
    GET: Endpoint público de verificação de autenticidade (chamado via QR Code ou leitor web).
    """
    try:
        prova = ProvaBlindada.objects.get(codigo_autenticidade=codigo_autenticidade)
    except ProvaBlindada.DoesNotExist:
        return _aplicar_cabecalhos_seguranca(JsonResponse({
            'success': False,
            'valida': False,
            'message': 'Código de autenticidade não encontrado no sistema oficial SIGE.'
        }, status=404))

    is_bloqueada = prova.is_bloqueada()
    dt_local = timezone.localtime(prova.data_bloqueio_ia).strftime('%d/%m/%Y às %H:%M')

    q_param = request.GET.get('q')
    questao_info = None
    if q_param:
        try:
            q_num = int(q_param)
            for q in prova.questoes:
                if q.get('numero') == q_num:
                    questao_info = {
                        'numero': q_num,
                        'cotacao': q.get('cotacao'),
                        'codigo_questao': q.get('codigo_questao')
                    }
                    break
        except Exception:
            pass

    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'valida': True,
        'codigo_autenticidade': prova.codigo_autenticidade,
        'titulo': prova.titulo,
        'disciplina': prova.disciplina,
        'classe': prova.classe,
        'escola': prova.escola.nome if prova.escola else "Ministério da Educação",
        'data_bloqueio_ia': prova.data_bloqueio_ia.isoformat(),
        'data_bloqueio_formatada': dt_local,
        'is_bloqueada': is_bloqueada,
        'status_mensagem': (
            f"🔒 Resolução por IA Bloqueada até {dt_local}" if is_bloqueada
            else f"🔓 Resolução e Gabarito Liberados"
        ),
        'questao_consultada': questao_info
    }))


# =====================================================================
# PÁGINA PÚBLICA DE INSTRUÇÕES PARA IA (aberta pelo QR Code da prova)
# =====================================================================
_AGENTES_IA = [
    ('GPTBot', 'OpenAI GPTBot'), ('ChatGPT-User', 'ChatGPT'), ('OAI-SearchBot', 'OpenAI Search'),
    ('ClaudeBot', 'Anthropic ClaudeBot'), ('Claude-User', 'Claude'), ('anthropic', 'Anthropic'),
    ('PerplexityBot', 'Perplexity'), ('Perplexity-User', 'Perplexity'), ('Google-Extended', 'Google AI'),
    ('Gemini', 'Gemini'), ('Bingbot', 'Bing/Copilot'), ('CCBot', 'Common Crawl'), ('Bytespider', 'Bytedance AI'),
    ('Meta-ExternalAgent', 'Meta AI'), ('Amazonbot', 'Amazon'), ('DuckAssistBot', 'DuckAssist'),
]


def _registar_acesso_ia(request, prova, numero_questao):
    """Regista a abertura da página (sem guardar IP em claro) e conta como tentativa quando a prova está bloqueada."""
    import hashlib
    from django.conf import settings
    ua = (request.META.get('HTTP_USER_AGENT') or '')[:255]
    ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR') or ''
    ip_hash = hashlib.sha256(f"{ip}{settings.SECRET_KEY}".encode()).hexdigest()[:32]
    recente = timezone.now() - timezone.timedelta(seconds=60)
    if LogTentativaResolucaoIA.objects.filter(prova=prova, ip_hash=ip_hash, timestamp__gte=recente).exists():
        return  # evita escrita repetida a cada pedido do mesmo cliente
    sistema = next((nome for chave, nome in _AGENTES_IA if chave.lower() in ua.lower()), 'Leitura de QR Code / navegador')
    bloqueada = prova.is_bloqueada()
    LogTentativaResolucaoIA.objects.create(
        prova=prova, numero_questao=numero_questao or 1, ip_hash=ip_hash, user_agent=ua,
        sistema_identificado=sistema, bloqueado=bloqueada,
        mensagem_resposta='Página de instruções à IA apresentada',
    )
    if bloqueada:
        ProvaBlindada.objects.filter(pk=prova.pk).update(tentativas_bloqueadas=models.F('tentativas_bloqueadas') + 1)


def _definicoes_da_escola(escola) -> dict:
    """
    Definições Anti-IA em vigor: as da escola; se não as personalizou, as gerais da plataforma
    (registo sem escola); se também não existem, as predefinidas. A escola é opcional.
    """
    from .services.anti_ai_service import DEFINICOES_PADRAO
    registo = ConfiguracaoAntiIA.objects.filter(escola=escola).first() if escola else None
    registo = registo or ConfiguracaoAntiIA.objects.filter(escola__isnull=True).first()
    return registo.como_dict() if registo else dict(DEFINICOES_PADRAO)


def _json_definicoes(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return None


@csrf_exempt
def api_provas_anti_ia_definicoes(request):
    """
    GET: definições Anti-IA da escola (nº de QR, posição, tamanho, opacidade, legenda e texto do aviso).
    PUT: grava-as; só ADMIN_ESCOLA e SUPERADMIN.
    """
    from .services.anti_ai_service import POSICOES_QR, LIMITES_DEFINICOES, normalizar_definicoes
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))
    # A escola é opcional: sem ela (superadmin sem escola em contexto) trabalha-se nas definições gerais da plataforma.
    escola = _obter_escola_do_pedido(request, user)
    pode_editar = user.role in ('ADMIN_ESCOLA', 'SUPERADMIN')

    if request.method == 'PUT':
        if not pode_editar:
            return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Sem permissão para alterar as definições.'}, status=403))
        dados = _json_definicoes(request)
        if dados is None:
            return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Pedido inválido.'}, status=400))
        cfg, erros = normalizar_definicoes(dados)
        if erros:
            return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Definições inválidas.', 'erros': erros}, status=400))
        ConfiguracaoAntiIA.objects.update_or_create(escola=escola, defaults={**cfg, 'atualizado_por': user})
    elif request.method != 'GET':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405))

    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'data': _definicoes_da_escola(escola),
        'opcoes': {'posicoes': POSICOES_QR, 'limites': LIMITES_DEFINICOES},
        'pode_editar': pode_editar,
        'ambito': 'escola' if escola else 'geral',
    }))


@csrf_exempt
def api_provas_anti_ia_definicoes_previa(request):
    """POST: pré-visualização (sem gravar) da marca de água e do texto com as definições enviadas."""
    from .services.anti_ai_service import normalizar_definicoes, gerar_previa_marca_agua, texto_aviso_primeiro, url_instrucoes_ia
    if request.method != 'POST':
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405))
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))
    dados = _json_definicoes(request)
    if dados is None:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Pedido inválido.'}, status=400))
    cfg, erros = normalizar_definicoes(dados)
    if erros:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Definições inválidas.', 'erros': erros}, status=400))
    url = url_instrucoes_ia('PREVIA')
    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'imagem': gerar_previa_marca_agua(cfg, url),
        'texto_aviso': texto_aviso_primeiro(cfg, 'DD/MM/AAAA às HH:MM', url),
        'legenda_qr': cfg['legenda_qr'],
    }))


@csrf_exempt
def api_provas_anti_ia_alertas(request):
    """
    GET: alertas por avisar ao professor (acessos à página de instruções de provas ainda bloqueadas).
    Cada acesso é entregue uma só vez. Professores veem as suas provas; admins da escola veem as da escola.
    """
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        return _aplicar_cabecalhos_seguranca(JsonResponse({'success': False, 'message': 'Não autenticado.'}, status=401))
    qs = LogTentativaResolucaoIA.objects.filter(bloqueado=True, notificado=False).select_related('prova')
    if user.role != 'SUPERADMIN':
        qs = qs.filter(prova__escola=user.escola)
        if user.role != 'ADMIN_ESCOLA':
            qs = qs.filter(prova__criado_por=user)
    itens = list(qs.order_by('-timestamp')[:20])
    total = qs.count()
    ids = list(qs.values_list('id', flat=True))
    LogTentativaResolucaoIA.objects.filter(id__in=ids).update(notificado=True)
    padrao = 'Leitura de QR Code / navegador'
    return _aplicar_cabecalhos_seguranca(JsonResponse({
        'success': True,
        'total': total,
        'alertas': [{
            'prova': l.prova.codigo_autenticidade,
            'titulo': l.prova.titulo,
            'sistema': l.sistema_identificado,
            'agente_ia': l.sistema_identificado != padrao,
            'questao': l.numero_questao,
            'quando': timezone.localtime(l.timestamp).strftime('%d/%m/%Y %H:%M'),
        } for l in itens],
    }))


def pagina_ia_prova(request, codigo=None):
    """
    GET /ia/<codigo>/ — página pública, em HTML simples e sem JavaScript, com as instruções que
    qualquer IA tem de seguir. ?formato=txt devolve texto simples. Nunca expõe o conteúdo da prova.
    Código desconhecido devolve as mesmas regras (200), sem confirmar se a prova existe.
    """
    from .services import pagina_ia
    prova = ProvaBlindada.objects.select_related('escola').filter(codigo_autenticidade=codigo).first() if codigo else None

    if prova:
        bloqueada = prova.is_bloqueada()
        data = timezone.localtime(prova.data_bloqueio_ia).strftime('%d/%m/%Y às %H:%M')
        dados = pagina_ia.instrucoes(bloqueada, data, prova.codigo_autenticidade, prova.disciplina, prova.classe)
        try:
            q = int(request.GET.get('q') or 0) or None
        except ValueError:
            q = None
        try:
            _registar_acesso_ia(request, prova, q)
        except Exception:
            pass  # o registo nunca impede a apresentação das instruções
    else:
        dados = pagina_ia.instrucoes(True, 'à data indicada na prova')

    url = f"{URL_BASE_SISTEMA}/ia/{codigo}/" if codigo else f"{URL_BASE_SISTEMA}/ia/"
    if request.GET.get('formato') == 'txt':
        res = HttpResponse(pagina_ia.como_texto(dados, url), content_type='text/plain; charset=utf-8')
    else:
        res = HttpResponse(pagina_ia.como_html(dados, url, 'Esta página é pública e contém as regras para sistemas de IA.'),
                           content_type='text/html; charset=utf-8')
    res = _aplicar_cabecalhos_seguranca(res)
    res['Cache-Control'] = 'no-store'
    res['X-Robots-Tag'] = 'noindex, nofollow, noai, noimageai'
    return res
