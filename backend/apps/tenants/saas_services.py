from datetime import date, timedelta
from decimal import Decimal
import calendar
from django.utils import timezone
from .models import Escola, SaasPlano, SaasAssinatura, SaasFatura, SaasLogAssinatura


def calcular_data_limite_efectiva_python(fatura):
    if fatura.data_limite_manual:
        return fatura.data_limite_manual

    ass = fatura.assinatura
    inicio = fatura.periodo_inicio
    ano = inicio.year
    mes = inicio.month

    if ass.modo_data_limite == 'dia_fixo' and ass.dia_limite:
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        dia = min(ass.dia_limite, ultimo_dia)
        return date(ano, mes, dia)

    if ass.modo_data_limite == 'automatico':
        if ass.periodicidade == 'mensal':
            return date(ano, mes, 10)
        elif ass.periodicidade == 'trimestral':
            return date(ano, mes, 15)
        elif ass.periodicidade == 'semestral':
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            return date(ano, mes, min(30, ultimo_dia))
        elif ass.periodicidade == 'anual':
            return date(ano, 1, 31)

    return fatura.data_limite


def calcular_tempo_correspondente_valor(valor, preco_mensal, periodicidade='mensal'):
    """
    Calcula com precisão matemática a quanto tempo (meses e dias) corresponde um montante
    em função do preço base mensal do plano e da periodicidade contratada (com descontos aplicáveis).
    """
    try:
        val = Decimal(str(valor))
        p_mensal = Decimal(str(preco_mensal))
    except Exception:
        return {'meses': 0, 'dias': 0, 'preco_efetivo_mensal': Decimal('0.00'), 'preco_diario': Decimal('0.00')}

    if val <= 0 or p_mensal <= 0:
        return {'meses': 0, 'dias': 0, 'preco_efetivo_mensal': p_mensal, 'preco_diario': Decimal('0.00')}

    fator = {
        'trimestral': Decimal('0.95'),
        'semestral': Decimal('0.90'),
        'anual': Decimal('0.85'),
    }.get(str(periodicidade).lower(), Decimal('1.00'))

    preco_efetivo_mensal = p_mensal * fator
    preco_diario = preco_efetivo_mensal / Decimal('30.0')

    meses = int(val // preco_efetivo_mensal)
    resto = val - (Decimal(meses) * preco_efetivo_mensal)
    dias = int(round(resto / preco_diario)) if preco_diario > 0 else 0

    if dias >= 30:
        meses += dias // 30
        dias = dias % 30

    return {
        'meses': meses,
        'dias': dias,
        'preco_efetivo_mensal': preco_efetivo_mensal,
        'preco_diario': preco_diario
    }


def adicionar_meses_e_dias(data_base, meses, dias):
    """
    Adiciona meses e dias a uma data base preservando correctamente os limites mensais e transição de anos.
    """
    if not data_base:
        data_base = timezone.localdate()

    if meses > 0:
        ano = data_base.year + ((data_base.month + meses - 1) // 12)
        mes = ((data_base.month + meses - 1) % 12) + 1
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        dia = min(data_base.day, ultimo_dia_mes)
        data_result = date(ano, mes, dia)
    else:
        data_result = data_base

    if dias > 0:
        data_result = data_result + timedelta(days=dias)

    return data_result


def avaliar_expiracao_assinatura(ass):
    """
    Verificação instantânea em tempo real executada no middleware:
    se a data limite/corte foi atingida, fecha/suspende automaticamente o acesso da instituição.
    """
    if not ass or ass.estado in ('cancelada', 'teste'):
        return ass.estado if ass else 'activa'

    hoje = timezone.localdate()

    # 1. Bloqueio manual discricionário
    if ass.data_bloqueio_manual and hoje >= ass.data_bloqueio_manual:
        if ass.estado != 'suspensa':
            ass.estado = 'suspensa'
            ass.save(update_fields=['estado', 'updated_at'])
            Escola.objects.filter(id=ass.instituicao_id).update(status='SUSPENSA')
            SaasLogAssinatura.objects.create(
                instituicao=ass.instituicao,
                assinatura=ass,
                accao='SUSPENSAO_AUTOMATICA',
                estado_anterior=ass.estado,
                estado_novo='suspensa',
                feito_por='sistema',
                motivo=f'Data limite de corte manual ({ass.data_bloqueio_manual}) alcançada.'
            )
        return 'suspensa'

    # 2. Avaliação de faturas pendentes
    faturas = SaasFatura.objects.filter(
        assinatura=ass,
        estado__in=['aberta', 'paga_parcial', 'em_atraso']
    ).order_by('periodo_inicio')

    em_corte = False
    em_restricao = False
    em_atraso = False

    for fat in faturas:
        data_ef = calcular_data_limite_efectiva_python(fat)
        lim_tol = data_ef + timedelta(days=ass.dias_tolerancia)
        lim_sus = lim_tol + timedelta(days=ass.dias_ate_suspensao)

        if hoje >= lim_sus:
            em_corte = True
            break
        elif hoje > lim_tol:
            em_restricao = True
        elif hoje > data_ef:
            em_atraso = True

    # 3. Avaliação da data de vencimento da assinatura se não houver faturas em atraso
    if not em_corte and not em_restricao and not em_atraso and faturas.count() == 0:
        if ass.proxima_fatura_em:
            lim_tol = ass.proxima_fatura_em + timedelta(days=ass.dias_tolerancia)
            lim_sus = lim_tol + timedelta(days=ass.dias_ate_suspensao)
            if hoje >= lim_sus:
                em_corte = True
            elif hoje > lim_tol:
                em_restricao = True
            elif hoje > ass.proxima_fatura_em:
                em_atraso = True

    novo_estado = ass.estado
    if em_corte:
        novo_estado = 'suspensa'
    elif em_restricao:
        novo_estado = 'restrita'
    elif em_atraso:
        novo_estado = 'em_atraso'

    if novo_estado != ass.estado:
        estado_ant = ass.estado
        ass.estado = novo_estado
        ass.save(update_fields=['estado', 'updated_at'])
        novo_status = 'SUSPENSA' if novo_estado == 'suspensa' else 'ATIVA'
        Escola.objects.filter(id=ass.instituicao_id).update(status=novo_status)
        SaasLogAssinatura.objects.create(
            instituicao=ass.instituicao,
            assinatura=ass,
            accao='SUSPENSAO_AUTOMATICA' if novo_estado == 'suspensa' else 'TRANSICAO_AUTOMATICA_ESTADO',
            estado_anterior=estado_ant,
            estado_novo=novo_estado,
            feito_por='sistema',
            motivo=f'Prazo da subscrição/corte esgotado em {hoje}. Acesso fechado automaticamente.'
        )

    return novo_estado


def aplicar_pagamento_adiantado_python(ass, fatura_principal, valor_pago_total, utilizador='sistema'):
    """
    Aplica o pagamento à fatura principal, liquida eventuais faturas secundárias em dívida
    e, havendo excedente, calcula automaticamente a quanto tempo corresponde (meses e dias)
    em função do plano contratado e prorroga a data da próxima fatura / validade da assinatura.
    """
    total_devido_principal = fatura_principal.valor + fatura_principal.multa_aplicada - fatura_principal.valor_pago
    sobra = valor_pago_total - total_devido_principal

    if valor_pago_total >= total_devido_principal:
        fatura_principal.valor_pago = fatura_principal.valor + fatura_principal.multa_aplicada
        fatura_principal.estado = 'paga'
    else:
        fatura_principal.valor_pago += valor_pago_total
        fatura_principal.estado = 'paga_parcial'
    fatura_principal.save()

    # 1. Abater em outras faturas pendentes da mesma instituição se houver excedente
    if sobra > Decimal('0.00'):
        outras_faturas = SaasFatura.objects.filter(
            instituicao=ass.instituicao,
            estado__in=['aberta', 'paga_parcial', 'em_atraso']
        ).exclude(id=fatura_principal.id).order_by('periodo_inicio')

        for outra in outras_faturas:
            if sobra <= Decimal('0.00'):
                break
            devido_outra = outra.valor + outra.multa_aplicada - outra.valor_pago
            if sobra >= devido_outra:
                outra.valor_pago = outra.valor + outra.multa_aplicada
                outra.estado = 'paga'
                outra.save()
                sobra -= devido_outra
            else:
                outra.valor_pago += sobra
                outra.estado = 'paga_parcial'
                outra.save()
                sobra = Decimal('0.00')

    # 2. Se restar sobra, calcular o tempo adiantado correspondente e estender proxima_fatura_em
    info_adiantado = {
        'valor_excedente': float(sobra),
        'meses': 0,
        'dias': 0,
        'proxima_fatura_anterior': str(ass.proxima_fatura_em),
        'nova_proxima_fatura': str(ass.proxima_fatura_em),
        'descricao': 'Nenhum adiantamento adicional.'
    }

    if sobra > Decimal('0.00') and ass.plano and ass.plano.preco_mensal > Decimal('0.00'):
        tempo = calcular_tempo_correspondente_valor(
            valor=sobra,
            preco_mensal=ass.plano.preco_mensal,
            periodicidade=ass.periodicidade
        )
        meses = tempo['meses']
        dias = tempo['dias']

        base_data = max(ass.proxima_fatura_em or timezone.localdate(), fatura_principal.periodo_fim)
        nova_proxima = adicionar_meses_e_dias(base_data, meses, dias)

        ass.proxima_fatura_em = nova_proxima
        ass.save(update_fields=['proxima_fatura_em', 'updated_at'])

        desc_partes = []
        if meses > 0:
            desc_partes.append(f"{meses} mês(es)")
        if dias > 0:
            desc_partes.append(f"{dias} dia(s)")
        desc_str = " e ".join(desc_partes) if desc_partes else "menos de 1 dia"

        info_adiantado = {
            'valor_excedente': float(sobra),
            'meses': meses,
            'dias': dias,
            'proxima_fatura_anterior': str(base_data),
            'nova_proxima_fatura': str(nova_proxima),
            'descricao': f"Valor excedente de {sobra} MZN corresponde a {desc_str} adicionais de subscrição (validade estendida até {nova_proxima.strftime('%d/%m/%Y')})."
        }

    # 3. Reactivar automaticamente a instituição se não restarem faturas em atraso
    restantes = SaasFatura.objects.filter(
        instituicao=ass.instituicao,
        estado__in=['em_atraso', 'aberta']
    ).count()

    reativada = False
    if restantes == 0:
        ass.estado = 'activa'
        ass.save(update_fields=['estado', 'updated_at'])
        Escola.objects.filter(id=ass.instituicao_id).update(status='ATIVA', bloqueada_manualmente=False)
        reativada = True

    return {
        'sobra_restante': sobra,
        'info_adiantado': info_adiantado,
        'fatura_liquidada': fatura_principal.estado == 'paga',
        'assinatura_reativada': reativada
    }


def avaliar_regras_automaticas_instituicao(instituicao_id, acao_desejada=None, feito_por='sistema', motivo_personalizado=None):
    """
    Avalia e executa a transição de estado automática (Suspensão ou Reactivação)
    para uma instituição com base nas faturas emitidas, prazos de tolerância e corte.

    acao_desejada:
      - 'auto_suspender': Verifica critérios e aplica suspensão automática sob modo automático.
      - 'auto_reactivar': Verifica quitação/prazos e aplica reactivação automática sob modo automático.
      - 'auto_avaliar' / None: Reavalia completamente a instituição, define o estado devido e repõe o modo automático.
    """
    hoje = timezone.localdate()
    escola = Escola.objects.filter(id=instituicao_id).first()
    if not escola:
        return {'sucesso': False, 'mensagem': 'Instituição não encontrada.'}

    ass = SaasAssinatura.objects.filter(instituicao=escola).order_by('-created_at').first()
    if not ass:
        return {'sucesso': False, 'mensagem': 'Assinatura SaaS não encontrada para a instituição.'}

    if ass.estado == 'cancelada':
        return {'sucesso': False, 'mensagem': 'A assinatura da instituição encontra-se cancelada definitivamente.'}

    faturas_pendentes = SaasFatura.objects.filter(
        instituicao=escola,
        estado__in=['aberta', 'paga_parcial', 'em_atraso']
    ).order_by('periodo_inicio')

    faturas_em_corte = []
    faturas_em_restricao = []
    faturas_em_tolerancia = []

    for fat in faturas_pendentes:
        data_efectiva = calcular_data_limite_efectiva_python(fat)
        limite_tolerancia = data_efectiva + timedelta(days=ass.dias_tolerancia)
        limite_suspensao = limite_tolerancia + timedelta(days=ass.dias_ate_suspensao)

        # Aplicar multa caso ultrapasse a data efectiva
        if hoje > data_efectiva and fat.multa_aplicada == 0:
            if ass.multa_tipo == 'fixo':
                fat.multa_aplicada = ass.multa_valor
            elif ass.multa_tipo == 'percentagem':
                fat.multa_aplicada = round(fat.valor * (ass.multa_valor / Decimal('100.0')), 2)
            fat.save()

        if hoje > data_efectiva and fat.estado != 'em_atraso':
            fat.estado = 'em_atraso'
            fat.save()

        passou_corte = (hoje >= limite_suspensao) or (ass.data_bloqueio_manual and hoje >= ass.data_bloqueio_manual)
        if passou_corte:
            faturas_em_corte.append(fat)
        elif hoje > limite_tolerancia:
            faturas_em_restricao.append(fat)
        elif hoje > data_efectiva:
            faturas_em_tolerancia.append(fat)

    # 1. Caso: Solicitação de Reactivação Automática mas existem faturas em corte
    if acao_desejada == 'auto_reactivar' and len(faturas_em_corte) > 0:
        nums = ", ".join([f.numero_fatura for f in faturas_em_corte])
        return {
            'sucesso': False,
            'tipo': 'impedimento_corte',
            'mensagem': (
                f"Não é possível reactivar automaticamente: a instituição possui {len(faturas_em_corte)} fatura(s) "
                f"em atraso ({nums}) que excederam o prazo de tolerância e corte ({ass.dias_ate_suspensao} dias). "
                f"Para restabelecer o acesso, confirme o pagamento pendente, prorrogue o vencimento ou use 'Reactivar Manualmente'."
            ),
            'detalhes': {
                'faturas_em_corte': [f.numero_fatura for f in faturas_em_corte],
                'dias_ate_suspensao': ass.dias_ate_suspensao
            }
        }

    # 2. Caso: Solicitação de Suspensão Automática mas a instituição NÃO tem faturas em corte
    if acao_desejada == 'auto_suspender' and len(faturas_em_corte) == 0:
        return {
            'sucesso': False,
            'tipo': 'sem_motivo_corte',
            'mensagem': (
                f"A instituição não possui faturas que excedam o prazo de corte ({ass.dias_ate_suspensao} dias após a tolerância). "
                f"Pelas regras automáticas do sistema, a instituição não qualifica para suspensão automática. "
                f"Caso pretenda suspender por razões administrativas externas, utilize 'Suspender Manualmente'."
            )
        }

    # 3. Determinar o novo estado do sistema
    estado_anterior = ass.estado
    if len(faturas_em_corte) > 0:
        novo_estado = 'suspensa'
        novo_status_escola = 'SUSPENSA'
        motivo_padrao = f"Suspensão automática aplicada: fatura(s) em atraso além do limite de corte de {ass.dias_ate_suspensao} dias."
        accao_log = 'SUSPENSAO_AUTOMATICA'
        msg_sucesso = "Instituição suspensa automaticamente de acordo com as regras de corte do sistema."
    elif len(faturas_em_restricao) > 0:
        novo_estado = 'restrita'
        novo_status_escola = 'ATIVA'
        motivo_padrao = f"Transição automática: acesso restrito a consulta por tolerância de {ass.dias_tolerancia} dias expirada."
        accao_log = 'TRANSICAO_AUTOMATICA_ESTADO'
        msg_sucesso = "Instituição colocada em modo restrito de acordo com as regras de tolerância."
    elif len(faturas_em_tolerancia) > 0:
        novo_estado = 'em_atraso'
        novo_status_escola = 'ATIVA'
        motivo_padrao = "Transição automática: fatura em atraso dentro do período de tolerância."
        accao_log = 'TRANSICAO_AUTOMATICA_ESTADO'
        msg_sucesso = "Instituição colocada em estado de atraso (dentro da tolerância)."
    elif faturas_pendentes.count() > 0:
        novo_estado = 'fatura_pendente'
        novo_status_escola = 'ATIVA'
        motivo_padrao = "Reactivação automática: obrigações regulares com fatura aberta no prazo."
        accao_log = 'REACTIVACAO_AUTOMATICA' if estado_anterior == 'suspensa' else 'TRANSICAO_AUTOMATICA_ESTADO'
        msg_sucesso = "Instituição reactivada automaticamente (fatura em aberto dentro do prazo)."
    else:
        # Sem faturas pendentes: verificar se a validade geral da assinatura expirou
        if ass.proxima_fatura_em:
            limite_tol = ass.proxima_fatura_em + timedelta(days=ass.dias_tolerancia)
            limite_sus = limite_tol + timedelta(days=ass.dias_ate_suspensao)
            if hoje >= limite_sus:
                novo_estado = 'suspensa'
                novo_status_escola = 'SUSPENSA'
                motivo_padrao = f"Suspensão automática: período da subscrição expirado em {ass.proxima_fatura_em} e tolerância de corte esgotada."
                accao_log = 'SUSPENSAO_AUTOMATICA'
                msg_sucesso = "Instituição suspensa automaticamente por fim de período de subscrição."
            elif hoje > limite_tol:
                novo_estado = 'restrita'
                novo_status_escola = 'ATIVA'
                motivo_padrao = "Transição automática: período expirado além do prazo de tolerância."
                accao_log = 'TRANSICAO_AUTOMATICA_ESTADO'
                msg_sucesso = "Instituição colocada em modo restrito por expiração de subscrição."
            elif hoje > ass.proxima_fatura_em:
                novo_estado = 'em_atraso'
                novo_status_escola = 'ATIVA'
                motivo_padrao = "Transição automática: período expirado dentro da tolerância."
                accao_log = 'TRANSICAO_AUTOMATICA_ESTADO'
                msg_sucesso = "Instituição colocada em estado de atraso (dentro da tolerância de renovação)."
            else:
                novo_estado = 'activa'
                novo_status_escola = 'ATIVA'
                motivo_padrao = "Reactivação automática: todas as faturas quitadas com sucesso."
                accao_log = 'REACTIVACAO_AUTOMATICA' if estado_anterior == 'suspensa' else 'TRANSICAO_AUTOMATICA_ESTADO'
                msg_sucesso = "Instituição reactivada automaticamente (todas as faturas quitadas)."
        else:
            novo_estado = 'activa'
            novo_status_escola = 'ATIVA'
            motivo_padrao = "Reactivação automática: todas as faturas quitadas com sucesso."
            accao_log = 'REACTIVACAO_AUTOMATICA' if estado_anterior == 'suspensa' else 'TRANSICAO_AUTOMATICA_ESTADO'
            msg_sucesso = "Instituição reactivada automaticamente (todas as faturas quitadas)."

    ass.estado = novo_estado
    ass.save()
    Escola.objects.filter(id=instituicao_id).update(
        status=novo_status_escola,
        bloqueada_manualmente=False
    )

    motivo = motivo_personalizado or motivo_padrao
    SaasLogAssinatura.objects.create(
        instituicao=escola,
        assinatura=ass,
        accao=accao_log,
        estado_anterior=estado_anterior,
        estado_novo=novo_estado,
        feito_por=feito_por,
        motivo=motivo
    )

    return {
        'sucesso': True,
        'mensagem': msg_sucesso,
        'estado_anterior': estado_anterior,
        'estado_novo': novo_estado,
        'status_escola': novo_status_escola,
        'modo_controlo': 'automatico',
        'accao': accao_log
    }


def executar_rotina_diaria_saas_python():
    hoje = timezone.localdate()
    faturas_geradas = 0
    alteracoes_estado = 0

    # 1. Gerar Faturas do Dia
    assinaturas = SaasAssinatura.objects.exclude(estado='cancelada').filter(proxima_fatura_em__lte=hoje)
    for ass in assinaturas:
        inicio = ass.proxima_fatura_em
        plano = ass.plano

        if ass.periodicidade == 'mensal':
            # 1 mês
            ano = inicio.year + (inicio.month // 12)
            mes = (inicio.month % 12) + 1
            dia = min(inicio.day, calendar.monthrange(ano, mes)[1])
            proxima = date(ano, mes, dia)
            fim = proxima - timedelta(days=1)
            valor = plano.preco_mensal
            limite = date(inicio.year, inicio.month, 10)
        elif ass.periodicidade == 'trimestral':
            proxima = inicio + timedelta(days=90)
            fim = proxima - timedelta(days=1)
            valor = plano.preco_mensal * Decimal('3') * Decimal('0.95')
            limite = date(inicio.year, inicio.month, 15)
        elif ass.periodicidade == 'semestral':
            proxima = inicio + timedelta(days=180)
            fim = proxima - timedelta(days=1)
            valor = plano.preco_mensal * Decimal('6') * Decimal('0.90')
            limite = date(inicio.year, inicio.month, min(30, calendar.monthrange(inicio.year, inicio.month)[1]))
        elif ass.periodicidade == 'anual':
            proxima = date(inicio.year + 1, inicio.month, min(inicio.day, 28))
            fim = proxima - timedelta(days=1)
            valor = plano.preco_mensal * Decimal('12') * Decimal('0.85')
            limite = date(inicio.year, 1, 31)
        else:
            proxima = inicio + timedelta(days=30)
            fim = proxima - timedelta(days=1)
            valor = plano.preco_mensal
            limite = date(inicio.year, inicio.month, 10)

        if ass.modo_data_limite == 'dia_fixo' and ass.dia_limite:
            ultimo_dia = calendar.monthrange(inicio.year, inicio.month)[1]
            limite = date(inicio.year, inicio.month, min(ass.dia_limite, ultimo_dia))

        num_fatura = f"FAT-{inicio.strftime('%Y%m')}-{str(ass.instituicao_id)[:6]}"

        fatura, created = SaasFatura.objects.get_or_create(
            assinatura=ass,
            periodo_inicio=inicio,
            defaults={
                'instituicao': ass.instituicao,
                'numero_fatura': num_fatura,
                'periodo_fim': fim,
                'valor': valor,
                'data_abertura': hoje,
                'data_limite': limite,
                'estado': 'aberta'
            }
        )

        if created:
            faturas_geradas += 1
            ass.proxima_fatura_em = proxima
            if ass.estado == 'activa':
                ass.estado = 'fatura_pendente'
            ass.save()

            SaasLogAssinatura.objects.create(
                instituicao=ass.instituicao,
                assinatura=ass,
                accao='GERAR_FATURA_AUTOMATICA',
                estado_anterior='activa',
                estado_novo='fatura_pendente',
                valor_novo=valor,
                feito_por='sistema',
                motivo=f'Abertura automática de fatura {num_fatura}'
            )

    # 2. Avaliação Automática de Estados (Suspensão e Reactivação Automáticas)
    # Avalia todas as instituições cujo controlo seja automático (não bloqueadas manualmente)
    todas_assinaturas = SaasAssinatura.objects.exclude(estado='cancelada').select_related('instituicao')
    for ass in todas_assinaturas:
        escola = ass.instituicao
        # Preserva bloqueio manual discricionário se configurado
        if getattr(escola, 'bloqueada_manualmente', False):
            continue

        estado_antes = ass.estado
        res = avaliar_regras_automaticas_instituicao(
            instituicao_id=ass.instituicao_id,
            acao_desejada='auto_avaliar',
            feito_por='sistema'
        )
        if res.get('sucesso') and res.get('estado_novo') != estado_antes:
            alteracoes_estado += 1

    return {
        'sucesso': True,
        'faturas_geradas': faturas_geradas,
        'alteracoes_estado': alteracoes_estado,
        'data_execucao': str(hoje)
    }
