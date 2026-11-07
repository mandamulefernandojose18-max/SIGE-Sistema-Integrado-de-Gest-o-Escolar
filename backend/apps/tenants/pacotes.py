"""
Pacotes de funcionalidades do SIGE (Essencial, Pedagógico, Completo).

- Catálogo de funcionalidades (chave -> rótulo/descrição) usado na matriz do SuperAdmin e no menu das escolas.
- Mapeamento de prefixos da API para a funcionalidade que os protege (aplicado por middleware).
- Cálculo de preço por período: preço mensal do pacote x meses, menos o desconto da periodicidade,
  arredondado a 50 MZN.

Escola sem pacote atribuído (`pacote` nulo) mantém acesso total (retrocompatibilidade).
"""
import time
from decimal import Decimal, ROUND_HALF_UP

# (chave, rótulo, descrição)
CATALOGO_FUNCIONALIDADES = [
    ('exames', 'Exames e classes de exame', 'Configuração e lançamento de notas de exame, MEC.'),
    ('estatisticas', 'Estatísticas de aproveitamento', 'Indicadores de aproveitamento por turma e disciplina.'),
    ('rotina', 'Horários, sumários, presenças e ocorrências', 'Rotina diária da escola.'),
    ('pedagogia', 'Direcção de turma, área pedagógica e DAP', 'Gestão pedagógica e controlo DAP.'),
    ('comunicacao', 'Calendário, transferências e comunicados', 'Comunicação e movimentos de alunos.'),
    ('material_escolar', 'Material escolar', 'Gestão de material escolar.'),
    ('portal_aluno', 'Painel do aluno', 'Notas, faltas e calendário para o aluno.'),
    ('exportacao', 'Exportação Word e Excel', 'Documentos oficiais em .docx e .xlsx.'),
    ('financas', 'Finanças escolares', 'Pagamentos escolares, despesas, impressão e painel financeiro.'),
    ('auditoria', 'Auditoria avançada', 'Registo detalhado de operações.'),
    ('ia_anti_ia', 'Provas Anti-IA e IA do Guião', 'Escudo anti-IA e assistente de IA (com quota).'),
    ('gateway', 'Gateway SMS, WhatsApp e pagamentos móveis', 'Canais digitais com custo por consumo.'),
]
CHAVES_FUNCIONALIDADES = [c[0] for c in CATALOGO_FUNCIONALIDADES]

# Prefixos da API protegidos por funcionalidade (o núcleo MEC nunca é bloqueado).
PREFIXOS_API_FUNCIONALIDADE = [
    ('/api/v1/pagamentos', 'financas'),
    ('/api/v1/ferramentas/sms', 'gateway'),
    ('/api/v1/ferramentas/whatsapp', 'gateway'),
    ('/api/v1/ferramentas/pagamentos', 'gateway'),
    ('/api/v1/ferramentas/stats', 'gateway'),
    ('/api/v1/escudo', 'ia_anti_ia'),
    ('/api/v1/escola-admin/turmas/horarios', 'rotina'),
    ('/api/v1/turmas/horarios', 'rotina'),
    ('/api/v1/notas/planos-sumarios', 'rotina'),
    ('/api/v1/notas/ocorrencias', 'rotina'),
    ('/api/v1/alunos/presencas', 'rotina'),
    ('/api/v1/alunos/transferencias', 'comunicacao'),
    ('/api/v1/documentos/calendario', 'comunicacao'),
    ('/api/v1/documentos/comunicados', 'comunicacao'),
    ('/api/v1/material-escolar', 'material_escolar'),
]

PERIODOS_MESES = {'mensal': 1, 'trimestral': 3, 'semestral': 6, 'anual': 12}
# Descontos que reproduzem os preços actuais do plano Pedagógico (1500 / 4200 / 7800 / 14500 MZN).
DESCONTOS_PADRAO = {'mensal': 0, 'trimestral': 6.67, 'semestral': 13.33, 'anual': 19.44}

PACOTES_PADRAO = [
    {
        'codigo': 'essencial', 'nome': 'Essencial', 'ordem': 1, 'recomendado': False,
        'descricao': 'Núcleo oficial do MEC: alunos, turmas, caderneta, pautas e certificados.',
        'preco_mensal': Decimal('900'), 'limite_alunos': 300, 'limite_professores': 30,
        'funcionalidades': [],
    },
    {
        'codigo': 'pedagogico', 'nome': 'Pedagógico', 'ordem': 2, 'recomendado': True,
        'descricao': 'Gestão pedagógica completa: exames, rotina, DAP, comunicação e portal do aluno.',
        'preco_mensal': Decimal('1500'), 'limite_alunos': 800, 'limite_professores': 80,
        'funcionalidades': ['exames', 'estatisticas', 'rotina', 'pedagogia', 'comunicacao',
                            'material_escolar', 'portal_aluno', 'exportacao'],
    },
    {
        'codigo': 'completo', 'nome': 'Completo', 'ordem': 3, 'recomendado': False,
        'descricao': 'Tudo do Pedagógico, mais finanças, auditoria, IA e canais digitais.',
        'preco_mensal': Decimal('2400'), 'limite_alunos': 2000, 'limite_professores': 200,
        'funcionalidades': list(CHAVES_FUNCIONALIDADES),
    },
]


def preco_periodo(preco_mensal, meses, desconto_pct):
    """Preço do período = mensal x meses x (1 - desconto), arredondado a 50 MZN."""
    bruto = Decimal(str(preco_mensal)) * Decimal(meses)
    liquido = bruto * (Decimal('100') - Decimal(str(desconto_pct))) / Decimal('100')
    return (liquido / Decimal('50')).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * Decimal('50')


def tabela_precos(pacote):
    """Preços por periodicidade de um pacote, com o desconto aplicado."""
    descontos = {**DESCONTOS_PADRAO, **(pacote.descontos or {})}
    saida = {}
    for periodo, meses in PERIODOS_MESES.items():
        d = descontos.get(periodo, 0)
        saida[periodo] = {
            'meses': meses,
            'desconto_percentual': float(d),
            'preco': float(preco_periodo(pacote.preco_mensal, meses, d)),
            'preco_mensal_equivalente': float((preco_periodo(pacote.preco_mensal, meses, d) / meses).quantize(Decimal('1'))),
        }
    return saida


# ---- Funcionalidades efectivas de uma escola (cache curto, como o estado da assinatura) ----
_CACHE = {}
_TTL = 45


def limpar_cache_funcionalidades(escola_id=None):
    if escola_id:
        _CACHE.pop(str(escola_id), None)
    else:
        _CACHE.clear()


def funcionalidades_da_escola(escola):
    """Lista de chaves incluídas no pacote da escola; None = acesso total (sem pacote)."""
    if escola is None:
        return None
    chave = str(escola.id)
    agora = time.time()
    c = _CACHE.get(chave)
    if c and agora - c[0] < _TTL:
        return c[1]
    from .models import Pacote
    pacote_id = getattr(escola, 'pacote_id', None)
    if not pacote_id:
        valor = None
    else:
        p = Pacote.objects.filter(id=pacote_id).only('funcionalidades').first()
        valor = None if p is None else list(p.funcionalidades or [])
    _CACHE[chave] = (agora, valor)
    return valor


# Rotas usadas pelo núcleo MEC (ex.: caderneta) que ficam sempre acessíveis.
EXCECOES_NUCLEO = ('/api/v1/alunos/presencas/faltas-trimestre',)


def funcionalidade_para_caminho(caminho):
    if caminho.startswith(EXCECOES_NUCLEO):
        return None
    for prefixo, chave in PREFIXOS_API_FUNCIONALIDADE:
        if caminho.startswith(prefixo):
            return chave
    return None
