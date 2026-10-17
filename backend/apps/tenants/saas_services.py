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

    # 2. Actualizar Estados
    faturas_abertas = SaasFatura.objects.filter(estado__in=['aberta', 'paga_parcial', 'em_atraso'])
    for fat in faturas_abertas:
        ass = fat.assinatura
        data_efectiva = calcular_data_limite_efectiva_python(fat)
        limite_tolerancia = data_efectiva + timedelta(days=ass.dias_tolerancia)
        limite_suspensao = limite_tolerancia + timedelta(days=ass.dias_ate_suspensao)

        # Aplicar multa
        if hoje > data_efectiva and fat.multa_aplicada == 0:
            if ass.multa_tipo == 'fixo':
                fat.multa_aplicada = ass.multa_valor
            elif ass.multa_tipo == 'percentagem':
                fat.multa_aplicada = round(fat.valor * (ass.multa_valor / Decimal('100.0')), 2)
            fat.save()

        if hoje > data_efectiva and fat.estado != 'em_atraso':
            fat.estado = 'em_atraso'
            fat.save()

        # Transição de estado da assinatura
        if ass.estado != 'cancelada':
            novo_estado = ass.estado

            if ass.data_bloqueio_manual and hoje >= ass.data_bloqueio_manual:
                novo_estado = 'suspensa'
            elif hoje >= limite_suspensao:
                novo_estado = 'suspensa'
            elif hoje > limite_tolerancia:
                novo_estado = 'restrita'
            elif hoje > data_efectiva:
                novo_estado = 'em_atraso'

            if novo_estado != ass.estado:
                ass.estado = novo_estado
                ass.save()

                Escola.objects.filter(id=ass.instituicao_id).update(
                    status='SUSPENSA' if novo_estado == 'suspensa' else 'ATIVA'
                )

                SaasLogAssinatura.objects.create(
                    instituicao=ass.instituicao,
                    assinatura=ass,
                    fatura=fat,
                    accao='TRANSICAO_AUTOMATICA_ESTADO',
                    estado_anterior=fat.assinatura.estado,
                    estado_novo=novo_estado,
                    feito_por='sistema',
                    motivo=f'Transição automática para {novo_estado} em {hoje}'
                )
                alteracoes_estado += 1

    return {
        'sucesso': True,
        'faturas_geradas': faturas_geradas,
        'alteracoes_estado': alteracoes_estado,
        'data_execucao': str(hoje)
    }
