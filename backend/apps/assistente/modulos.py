"""
Módulos (ecrãs) que pertencem ao painel de cada perfil — espelho de MENUS_POR_PAINEL (frontend/js/app.js).

Regra de segurança do Assistente: só responde sobre o que pertence ao painel do utilizador. Cada capacidade (dados ou guia)
está associada a um módulo; se o módulo não existir no painel do perfil, o assistente recusa, sem revelar nada.
Ao acrescentar um módulo a um painel no frontend, acrescentar também aqui (e correr tests/test_assistente_seguranca.py).
"""

_COMUM = {'assistente'}

_DIRECCAO = {
    'dashboard', 'escola', 'assinatura-escola', 'usuarios-senhas', 'auditoria', 'calendario', 'turmas', 'horarios', 'professores',
    'atribuicoes-cargos', 'plano-curricular', 'desbloqueio', 'caderneta', 'pautas', 'exames', 'calendario-exames', 'provas-anti-ia',
    'folha-resposta', 'estatisticas-aproveitamento', 'material-escolar', 'sumarios', 'alunos', 'presencas', 'transferencias',
    'certificados', 'ocorrencias', 'impressao', 'pagamentos', 'despesas', 'comunicados', 'crm', 'assistente-relatorio',
    'estatistica-inicio-turma', 'estatistica-inicio-classe', 'estatistica-inicio-escola',
}
_PEDAGOGICO = {
    'estatisticas-aproveitamento', 'calendario', 'turmas', 'horarios', 'professores', 'atribuicoes-cargos', 'plano-curricular',
    'desbloqueio', 'caderneta', 'pautas', 'exames', 'calendario-exames', 'provas-anti-ia', 'folha-resposta', 'sumarios', 'alunos',
    'presencas', 'ocorrencias', 'transferencias', 'material-escolar', 'comunicados', 'crm',
    'estatistica-inicio-turma', 'estatistica-inicio-classe', 'estatistica-inicio-escola',
}
_SECRETARIA = {
    'dashboard', 'alunos', 'transferencias', 'presencas', 'turmas', 'pautas', 'certificados', 'impressao', 'calendario', 'horarios',
    'professores', 'pagamentos', 'ocorrencias', 'comunicados', 'crm',
}
_PROFESSOR = {
    'caderneta', 'presencas', 'sumarios', 'ocorrencias', 'horarios', 'pautas', 'exames', 'provas-anti-ia', 'folha-resposta',
    'estatisticas-aproveitamento', 'material-escolar', 'comunicados', 'minhas-atividades', 'professor-perfil',
    'correcao-provas', 'director-classe', 'director-turma',
}
_ALUNO = {
    'aluno-perfil', 'aluno-notas', 'aluno-faltas', 'aluno-calendario', 'horarios', 'aluno-pagamentos', 'material-escolar', 'comunicados',
}
_FINANCEIRO = {'dashboard', 'pagamentos', 'despesas', 'impressao', 'prompt-gateway', 'alunos', 'transferencias', 'calendario', 'comunicados'}
_SUPERADMIN = {'saas', 'pagamentos-saas', 'prompt-gateway', 'usuarios-senhas', 'acessos', 'assistente-relatorio'}

MODULOS_POR_PERFIL = {
    'SUPERADMIN': _SUPERADMIN | _COMUM,
    'ADMIN_ESCOLA': _DIRECCAO | _COMUM,
    'DIRECTOR_ESCOLA': _DIRECCAO | _COMUM,
    'DAP': _PEDAGOGICO | _COMUM,
    'CHEFE_SECRETARIA': _SECRETARIA | _COMUM,
    'SECRETARIA': _SECRETARIA | _COMUM,
    'PROFESSOR': _PROFESSOR | _COMUM,
    'ALUNO': _ALUNO | _COMUM,
    'ENCARREGADO': _ALUNO | _COMUM,
    'FINANCEIRO': _FINANCEIRO | _COMUM,
}


def modulos_do_perfil(role, inspeccionando=False):
    """Módulos do painel. O SuperAdmin a inspeccionar uma escola passa a ver também o painel da Direcção dessa escola."""
    base = set(MODULOS_POR_PERFIL.get(role, _COMUM))
    if role == 'SUPERADMIN' and inspeccionando:
        base |= _DIRECCAO
    return base
