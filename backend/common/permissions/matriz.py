"""
Matriz de Permissões Oficial do SIGE conforme documento "Tarefas e Permissões".
Legenda:
V = ver
C = criar
E = editar
A = aprovar / validar
— = sem acesso
"""

MATRIZ_PERMISSOES = {
    'utilizadores_permissoes': {
        'DIRECTOR_ESCOLA': ['V', 'C', 'E', 'A'],
        'ADMIN_ESCOLA': ['V', 'C', 'E', 'A'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
        'DAP': [],
        'PROFESSOR': [],
        'SECRETARIA': [],
        'CHEFE_SECRETARIA': [],
        'FINANCEIRO': [],
        'ALUNO': [],
        'ENCARREGADO': [],
    },
    'calendario_escolar': {
        'DIRECTOR_ESCOLA': ['V', 'A'],
        'ADMIN_ESCOLA': ['V', 'A'],
        'DAP': ['C', 'E', 'V'],
        'PROFESSOR': ['V'],
        'SECRETARIA': ['V'],
        'CHEFE_SECRETARIA': ['V'],
        'FINANCEIRO': ['V'],
        'ALUNO': ['V'],
        'ENCARREGADO': ['V'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'matriculas': {
        'DIRECTOR_ESCOLA': ['V', 'A'],
        'ADMIN_ESCOLA': ['V', 'A'],
        'DAP': ['V'],
        'PROFESSOR': [],
        'SECRETARIA': ['C', 'E', 'V'],
        'CHEFE_SECRETARIA': ['C', 'E', 'V'],
        'FINANCEIRO': ['V'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'processo_aluno': {
        'DIRECTOR_ESCOLA': ['V'],
        'ADMIN_ESCOLA': ['V'],
        'DAP': ['V'],
        'PROFESSOR': ['V_TURMA'],
        'SECRETARIA': ['C', 'E', 'V'],
        'CHEFE_SECRETARIA': ['C', 'E', 'V'],
        'FINANCEIRO': ['V'],
        'ALUNO': ['V_PROPRIO'],
        'ENCARREGADO': ['V_PROPRIO'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'turmas_horarios': {
        'DIRECTOR_ESCOLA': ['V', 'A'],
        'ADMIN_ESCOLA': ['V', 'A'],
        'DAP': ['C', 'E', 'V'],
        'PROFESSOR': ['V'],
        'SECRETARIA': ['V'],
        'CHEFE_SECRETARIA': ['V'],
        'FINANCEIRO': [],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'atribuicao_disciplinas': {
        'DIRECTOR_ESCOLA': ['V', 'A'],
        'ADMIN_ESCOLA': ['V', 'A'],
        'DAP': ['C', 'E', 'V'],
        'PROFESSOR': ['V'],
        'SECRETARIA': [],
        'CHEFE_SECRETARIA': [],
        'FINANCEIRO': [],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'presencas_alunos': {
        'DIRECTOR_ESCOLA': ['V'],
        'ADMIN_ESCOLA': ['V'],
        'DAP': ['V'],
        'PROFESSOR': ['C', 'E', 'V'],
        'SECRETARIA': ['V'],
        'CHEFE_SECRETARIA': ['V'],
        'FINANCEIRO': [],
        'ALUNO': ['V_PROPRIO'],
        'ENCARREGADO': ['V_PROPRIO'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'notas_medias': {
        'DIRECTOR_ESCOLA': ['V'],
        'ADMIN_ESCOLA': ['V'],
        'DAP': ['V', 'A'],
        'PROFESSOR': ['C', 'E'],
        'SECRETARIA': ['V'],
        'CHEFE_SECRETARIA': ['V'],
        'FINANCEIRO': [],
        'ALUNO': ['V_PROPRIO'],
        'ENCARREGADO': ['V_PROPRIO'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'pautas_boletins': {
        'DIRECTOR_ESCOLA': ['V', 'A'],
        'ADMIN_ESCOLA': ['V', 'A'],
        'DAP': ['V', 'A'],
        'PROFESSOR': ['V'],
        'SECRETARIA': ['C', 'E', 'V'],
        'CHEFE_SECRETARIA': ['C', 'E', 'V'],
        'FINANCEIRO': [],
        'ALUNO': ['V_PROPRIO'],
        'ENCARREGADO': ['V_PROPRIO'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'plano_aula_sumarios': {
        'DIRECTOR_ESCOLA': ['V'],
        'ADMIN_ESCOLA': ['V'],
        'DAP': ['V', 'A'],
        'PROFESSOR': ['C', 'E', 'V'],
        'SECRETARIA': [],
        'CHEFE_SECRETARIA': [],
        'FINANCEIRO': [],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'ocorrencias_disciplinares': {
        'DIRECTOR_ESCOLA': ['V'],
        'ADMIN_ESCOLA': ['V'],
        'DAP': ['V', 'A'],
        'PROFESSOR': ['C', 'E', 'V'],
        'SECRETARIA': ['V'],
        'CHEFE_SECRETARIA': ['V'],
        'FINANCEIRO': [],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'declaracoes_certificados': {
        'DIRECTOR_ESCOLA': ['A', 'V'],
        'ADMIN_ESCOLA': ['A', 'V'],
        'DAP': ['V'],
        'PROFESSOR': [],
        'SECRETARIA': ['C', 'E', 'V'],
        'CHEFE_SECRETARIA': ['C', 'E', 'V'],
        'FINANCEIRO': [],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'transferencias_anulacoes': {
        'DIRECTOR_ESCOLA': ['A', 'V'],
        'ADMIN_ESCOLA': ['A', 'V'],
        'DAP': ['V'],
        'PROFESSOR': [],
        'SECRETARIA': ['C', 'E', 'V'],
        'CHEFE_SECRETARIA': ['C', 'E', 'V'],
        'FINANCEIRO': ['V'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'propinas_pagamentos': {
        'DIRECTOR_ESCOLA': ['V'],
        'ADMIN_ESCOLA': ['V'],
        'DAP': [],
        'PROFESSOR': [],
        'SECRETARIA': ['V'],
        'CHEFE_SECRETARIA': ['V'],
        'FINANCEIRO': ['C', 'E', 'V'],
        'ALUNO': ['V_PROPRIO'],
        'ENCARREGADO': ['V_PROPRIO'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'recibos_dividas': {
        'DIRECTOR_ESCOLA': ['V'],
        'ADMIN_ESCOLA': ['V'],
        'DAP': [],
        'PROFESSOR': [],
        'SECRETARIA': ['V'],
        'CHEFE_SECRETARIA': ['V'],
        'FINANCEIRO': ['C', 'E', 'V'],
        'ALUNO': ['V_PROPRIO'],
        'ENCARREGADO': ['V_PROPRIO'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'receitas_despesas': {
        'DIRECTOR_ESCOLA': ['V', 'A'],
        'ADMIN_ESCOLA': ['V', 'A'],
        'DAP': [],
        'PROFESSOR': [],
        'SECRETARIA': [],
        'CHEFE_SECRETARIA': [],
        'FINANCEIRO': ['C', 'E', 'V'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'orcamento_relatorios_financeiros': {
        'DIRECTOR_ESCOLA': ['V', 'A'],
        'ADMIN_ESCOLA': ['V', 'A'],
        'DAP': [],
        'PROFESSOR': [],
        'SECRETARIA': [],
        'CHEFE_SECRETARIA': [],
        'FINANCEIRO': ['C', 'E', 'V'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'salarios_pessoal': {
        'DIRECTOR_ESCOLA': ['V', 'A'],
        'ADMIN_ESCOLA': ['V', 'A'],
        'DAP': ['V'],
        'PROFESSOR': [],
        'SECRETARIA': ['V'],
        'CHEFE_SECRETARIA': ['V'],
        'FINANCEIRO': ['C', 'E', 'V'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'inventario_patrimonio': {
        'DIRECTOR_ESCOLA': ['V', 'A'],
        'ADMIN_ESCOLA': ['V', 'A'],
        'DAP': [],
        'PROFESSOR': [],
        'SECRETARIA': [],
        'CHEFE_SECRETARIA': [],
        'FINANCEIRO': ['C', 'E', 'V'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'estatisticas_paineis': {
        'DIRECTOR_ESCOLA': ['V'],
        'ADMIN_ESCOLA': ['V'],
        'DAP': ['V'],
        'PROFESSOR': ['V_TURMA'],
        'SECRETARIA': ['V'],
        'CHEFE_SECRETARIA': ['V'],
        'FINANCEIRO': ['V_FINANCEIRO'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'comunicados': {
        'DIRECTOR_ESCOLA': ['C', 'A', 'V'],
        'ADMIN_ESCOLA': ['C', 'A', 'V'],
        'DAP': ['C', 'V'],
        'PROFESSOR': ['C', 'V'],
        'SECRETARIA': ['C', 'V'],
        'CHEFE_SECRETARIA': ['C', 'V'],
        'FINANCEIRO': ['C', 'V'],
        'ALUNO': ['V'],
        'ENCARREGADO': ['V'],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    },
    'copias_seguranca_parametros': {
        'DIRECTOR_ESCOLA': [],
        'ADMIN_ESCOLA': [],
        'DAP': [],
        'PROFESSOR': [],
        'SECRETARIA': [],
        'CHEFE_SECRETARIA': [],
        'FINANCEIRO': [],
        'ALUNO': [],
        'ENCARREGADO': [],
        'SUPERADMIN': ['V', 'C', 'E', 'A'],
    }
}

def checar_permissao_matriz(role, modulo, acao):
    """
    Verifica se uma determinada role tem a permissão solicitada para o módulo.
    acao: 'V' (ver), 'C' (criar), 'E' (editar), 'A' (aprovar/validar)
    """
    if not role:
        return False
    if role == 'SUPERADMIN':
        return True
    
    permissoes_modulo = MATRIZ_PERMISSOES.get(modulo, {})
    permissoes_role = permissoes_modulo.get(role, [])
    
    if acao in permissoes_role:
        return True
    if acao == 'V' and any(p in permissoes_role for p in ['V_TURMA', 'V_PROPRIO', 'V_FINANCEIRO']):
        return True
        
    return False
