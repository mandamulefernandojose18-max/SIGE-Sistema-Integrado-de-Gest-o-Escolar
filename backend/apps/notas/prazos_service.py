import calendar
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Q

def somar_meses(d, meses):
    novo_mes = d.month + meses
    ano = d.year + (novo_mes - 1) // 12
    mes = (novo_mes - 1) % 12 + 1
    max_dias = calendar.monthrange(ano, mes)[1]
    dia = min(d.day, max_dias)
    return date(ano, mes, dia)

def obter_configuracao_prazos(escola):
    """
    Retorna as datas de início e fim calculadas para cada trimestre com base
    no modo de calendarização da escola (MANUAL, AUTOMATICO ou SEMPRE).
    """
    modo = getattr(escola, 'modo_calendarizacao', 'MANUAL') or 'MANUAL'
    tipo_duracao = getattr(escola, 'tipo_duracao_automatica', 'SEMANAS') or 'SEMANAS'
    valor_duracao = getattr(escola, 'valor_duracao_automatica', 4) or 4
    data_base = getattr(escola, 'data_base_automatica', None)

    ano_atual = timezone.now().year
    if not data_base:
        data_base = date(ano_atual, 2, 1)

    def somar_duracao(d_ini, valor, tipo):
        if tipo == 'DIAS':
            return d_ini + timedelta(days=valor)
        elif tipo == 'MESES':
            return somar_meses(d_ini, valor)
        else: # SEMANAS
            return d_ini + timedelta(weeks=valor)

    if modo == 'AUTOMATICO':
        # Cálculo sequencial automático dos 3 trimestres
        t1_ini = data_base
        t1_fim = somar_duracao(t1_ini, valor_duracao, tipo_duracao)

        t2_ini = t1_fim + timedelta(days=1)
        t2_fim = somar_duracao(t2_ini, valor_duracao, tipo_duracao)

        t3_ini = t2_fim + timedelta(days=1)
        t3_fim = somar_duracao(t3_ini, valor_duracao, tipo_duracao)
    else:
        # MANUAL ou fallback
        t1_ini = getattr(escola, 'data_inicio_t1', None)
        t1_fim = getattr(escola, 'data_fim_t1', None)
        t2_ini = getattr(escola, 'data_inicio_t2', None)
        t2_fim = getattr(escola, 'data_fim_t2', None)
        t3_ini = getattr(escola, 'data_inicio_t3', None)
        t3_fim = getattr(escola, 'data_fim_t3', None)

    return {
        'modo': modo,
        'tipo_duracao': tipo_duracao,
        'valor_duracao': valor_duracao,
        'data_base': data_base,
        '1_TRIMESTRE': {'inicio': t1_ini, 'fim': t1_fim, 'sempre': getattr(escola, 'permitir_sempre_t1', False) or modo == 'SEMPRE'},
        '2_TRIMESTRE': {'inicio': t2_ini, 'fim': t2_fim, 'sempre': getattr(escola, 'permitir_sempre_t2', False) or modo == 'SEMPRE'},
        '3_TRIMESTRE': {'inicio': t3_ini, 'fim': t3_fim, 'sempre': getattr(escola, 'permitir_sempre_t3', False) or modo == 'SEMPRE'},
    }


def verificar_prazo_lancamento_trimestre(escola, periodo, professor=None, turma=None, disciplina=None, user=None):
    """
    Verifica se a inserção ou alteração de notas é permitida para o trimestre especificado.
    Retorna uma tupla: (permitido: bool, motivo: str, mensagem: str, info: dict)
    """
    if not escola:
        return True, 'OK', 'Sem escola vinculada.', {}

    # SuperAdmin tem permissão ilimitada de gestão
    if user and getattr(user, 'role', '') == 'SUPERADMIN':
        return True, 'SUPERADMIN', 'Acesso irrestrito de SuperAdmin.', {}

    if periodo in ('TODOS', 'ANUAL', ''):
        return True, 'OK', 'Período aberto.', {}

    from apps.notas.models import PermissaoEdicaoNotas
    agora = timezone.now()

    # 1. Verificar se existe autorização temporária de desbloqueio ativa
    if turma:
        perm_qs = PermissaoEdicaoNotas.objects.filter(
            escola=escola,
            turma=turma,
            periodo__in=[periodo, 'TODOS'],
            ativa=True
        ).filter(
            Q(data_expiracao__isnull=True) | Q(data_expiracao__gt=agora)
        )

        if professor:
            perm_qs = perm_qs.filter(Q(professor=professor) | Q(professor__isnull=True))
        if disciplina:
            perm_qs = perm_qs.filter(Q(disciplina=disciplina) | Q(disciplina__isnull=True))

        if perm_qs.exists():
            perm = perm_qs.first()
            exp_str = perm.data_expiracao.strftime('%d/%m/%Y às %H:%M') if perm.data_expiracao else 'Indeterminada'
            return True, 'DESBLOQUEIO_TEMPORARIO', f"Desbloqueio temporário concedido por {perm.autorizado_por}. Válido até {exp_str}.", {
                'autorizado_por': perm.autorizado_por,
                'data_expiracao': perm.data_expiracao
            }

    # 2. Obter datas e modo
    cfg = obter_configuracao_prazos(escola)
    modo = cfg['modo']
    p_info = cfg.get(periodo)

    nome_trimestre = '1º Trimestre' if periodo == '1_TRIMESTRE' else ('2º Trimestre' if periodo == '2_TRIMESTRE' else '3º Trimestre')

    # Se estiver no modo 'SEMPRE' ou com flag de permitir sempre para este trimestre
    if modo == 'SEMPRE' or (p_info and p_info.get('sempre')):
        return True, 'SEMPRE_PERMITIDO', f"Lançamento sempre permitido para o {nome_trimestre}.", {}

    if not p_info:
        return True, 'OK', 'Sem restrições de calendário para o período.', {}

    d_ini = p_info.get('inicio')
    d_fim = p_info.get('fim')
    hoje = agora.date()

    # Se não houver datas configuradas para este trimestre, permite normalmente
    if not d_ini and not d_fim:
        return True, 'SEM_DATAS', f"Calendário de prazos não definido para o {nome_trimestre}. Lançamento disponível.", {}

    # Caso 1: Período ainda não começou (FUTURO)
    if d_ini and hoje < d_ini:
        msg = f"Período de lançamento ainda não disponível para o {nome_trimestre}. As notas só poderão ser lançadas a partir de {d_ini.strftime('%d/%m/%Y')}."
        return False, 'FUTURO', msg, {'inicio': d_ini, 'fim': d_fim}

    # Caso 2: Período expirado (PASSADO)
    if d_fim and hoje > d_fim:
        msg = f"Período de lançamento expirado para o {nome_trimestre}. O prazo encerrou em {d_fim.strftime('%d/%m/%Y')}. Contacte a Direcção da Escola ou DAP para solicitar autorização de desbloqueio."
        return False, 'EXPIRADO', msg, {'inicio': d_ini, 'fim': d_fim}

    # Caso 3: Dentro do prazo regulamentar
    return True, 'ABERTO', f"Período aberto dentro do prazo oficial até {d_fim.strftime('%d/%m/%Y') if d_fim else 'o final do trimestre'}.", {'inicio': d_ini, 'fim': d_fim}
