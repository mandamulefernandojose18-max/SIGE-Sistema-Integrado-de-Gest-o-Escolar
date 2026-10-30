# -*- coding: utf-8 -*-
"""
Script para aplicar isolamento estrito de painéis no frontend (app.js):
- Professores -> painel-professor
- Secretaria -> painel-secretaria
- Aluno -> painel-aluno
- Administração e Finanças -> painel-financeiro
- Direcção da Escola -> painel-direcao
- Direcção Pedagógica (DAP) -> painel-pedagogico
- Superadmin -> painel-superadmin
"""

with open('frontend/js/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Atualizar VIEW_INICIAL_POR_ROLE e redirect em inicializarApp
alvo_inicial = """    if (state.user.role === 'ALUNO') {
      navegarPara('aluno-perfil');
    } else if (state.user.role === 'PROFESSOR') {
      navegarPara('caderneta');
    } else {
      // ADMIN_ESCOLA, DIRECTOR_ESCOLA, DAP, CHEFE_SECRETARIA
      document.getElementById('btnComprovativoEscola')?.classList.remove('d-none');
      navegarPara('dashboard');
    }"""

subst_inicial = """    const roleUser = state.user?.role || 'ADMIN_ESCOLA';
    if (['DIRECTOR_ESCOLA', 'ADMIN_ESCOLA'].includes(roleUser)) {
      document.getElementById('btnComprovativoEscola')?.classList.remove('d-none');
    } else {
      document.getElementById('btnComprovativoEscola')?.classList.add('d-none');
    }
    const viewInicial = VIEW_INICIAL_POR_ROLE[roleUser] || 'dashboard';
    navegarPara(viewInicial);"""

if alvo_inicial in text:
    text = text.replace(alvo_inicial, subst_inicial)
    print("Atualizado redirect de inicializarApp!")
else:
    print("Aviso: alvo_inicial não encontrado diretamente, verificando alternativas...")

# 2. Atualizar bloco de definições RBAC e Mapas
alvo_mapas_inicio = "const MAPA_PAINEIS = {"
idx_mapas = text.find(alvo_mapas_inicio)
idx_faixa = text.find("function atualizarFaixaAlertaSaaS")

if idx_mapas != -1 and idx_faixa != -1:
    bloco_novo = """const INFO_PAINEIS = {
  'painel-superadmin': {
    titulo: 'Governação Master SaaS',
    subtitulo: 'Gestão Multi-Tenant & Infraestrutura Global',
    icone: 'bi-shield-shaded',
    badgeClass: 'bg-dark',
    badgeText: 'SUPER ADMIN'
  },
  'painel-direcao': {
    titulo: 'Painel da Direcção da Escola',
    subtitulo: 'Governação Institucional, Homologações & Despesas',
    icone: 'bi-building',
    badgeClass: 'bg-primary',
    badgeText: 'DIRECÇÃO'
  },
  'painel-pedagogico': {
    titulo: 'Direcção Pedagógica (DAP)',
    subtitulo: 'Supervisão Pedagógica, Pautas, Horários & Cadernetas',
    icone: 'bi-diagram-3-fill',
    badgeClass: 'bg-info text-dark',
    badgeText: 'PEDAGÓGICO'
  },
  'painel-secretaria': {
    titulo: 'Painel da Secretaria Escolar',
    subtitulo: 'Matrículas, Processos de Alunos & Expediente Oficial',
    icone: 'bi-folder2-open',
    badgeClass: 'bg-secondary',
    badgeText: 'SECRETARIA'
  },
  'painel-professor': {
    titulo: 'Painel do Docente',
    subtitulo: 'Cadernetas, Notas, Presenças & Planos de Aula',
    icone: 'bi-mortarboard-fill',
    badgeClass: 'bg-success',
    badgeText: 'PROFESSOR'
  },
  'painel-aluno': {
    titulo: 'Portal do Aluno',
    subtitulo: 'Consultas de Notas, Horários, Faltas & Propinas',
    icone: 'bi-person-circle',
    badgeClass: 'bg-primary',
    badgeText: 'ALUNO'
  },
  'painel-financeiro': {
    titulo: 'Administração & Finanças',
    subtitulo: 'Propinas, Caixa, Folha de Salário & Património',
    icone: 'bi-cash-coin',
    badgeClass: 'bg-warning text-dark',
    badgeText: 'FINANÇAS'
  },
  'painel-escola': {
    titulo: 'Gestão Escolar Integrada',
    subtitulo: 'Administração e Gestão da Escola',
    icone: 'bi-building',
    badgeClass: 'bg-primary',
    badgeText: 'ESCOLA'
  }
};

const VIEW_INICIAL_POR_ROLE = {
  SUPERADMIN: 'saas',
  ADMIN_ESCOLA: 'dashboard',
  DIRECTOR_ESCOLA: 'dashboard',
  DAP: 'estatisticas-aproveitamento',
  CHEFE_SECRETARIA: 'dashboard',
  SECRETARIA: 'alunos',
  PROFESSOR: 'caderneta',
  ALUNO: 'aluno-perfil',
  ENCARREGADO: 'aluno-perfil',
  FINANCEIRO: 'pagamentos'
};

const MAPA_PAINEIS = {
  SUPERADMIN: 'painel-superadmin',
  ADMIN_ESCOLA: 'painel-direcao',
  DIRECTOR_ESCOLA: 'painel-direcao',
  DAP: 'painel-pedagogico',
  CHEFE_SECRETARIA: 'painel-secretaria',
  SECRETARIA: 'painel-secretaria',
  PROFESSOR: 'painel-professor',
  ALUNO: 'painel-aluno',
  ENCARREGADO: 'painel-aluno',
  FINANCEIRO: 'painel-financeiro'
};

const MENUS_POR_PAINEL = {
  'painel-superadmin': [
    { id: 'saas', titulo: 'Gestão de Escolas & Planos', icone: 'bi-buildings-fill text-warning', categoria: 'Administração Geral SaaS' },
    { id: 'pagamentos-saas', titulo: 'Assinaturas & Pagamentos SaaS', icone: 'bi-credit-card-2-front-fill text-warning', categoria: 'Administração Geral SaaS' },
    { id: 'prompt-gateway', titulo: 'Gateway SMS & Pagamentos', icone: 'bi-broadcast-pin text-warning', categoria: 'Ferramentas & Integrações' },
    { id: 'usuarios-senhas', titulo: 'Cofre de Credenciais Master', icone: 'bi-key-fill text-warning', categoria: 'Segurança' },
    { id: 'acessos', titulo: 'Auditoria & Acessos Globais', icone: 'bi-shield-check', categoria: 'Segurança' }
  ],
  'painel-direcao': [
    { id: 'dashboard', titulo: 'Painel Principal Executivo', icone: 'bi-grid-1x2-fill', categoria: 'Visão Geral' },
    { id: 'escola', titulo: 'Definições & Logótipo', icone: 'bi-building-gear', categoria: 'Gestão & Governação' },
    { id: 'assinatura-escola', titulo: 'Assinatura do Sistema', icone: 'bi-shield-lock-fill text-warning', categoria: 'Gestão & Governação' },
    { id: 'usuarios-senhas', titulo: 'Utilizadores & Permissões', icone: 'bi-key-fill text-warning', categoria: 'Gestão & Governação' },
    { id: 'auditoria', titulo: 'Auditoria de Operações', icone: 'bi-shield-lock-fill text-info', categoria: 'Gestão & Governação' },
    { id: 'calendario', titulo: 'Calendário Escolar', icone: 'bi-calendar3 text-primary', categoria: 'Área Pedagógica' },
    { id: 'turmas', titulo: 'Turmas & Capacidade', icone: 'bi-diagram-3-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'horarios', titulo: 'Horários Lectivos', icone: 'bi-clock-history text-info', categoria: 'Área Pedagógica' },
    { id: 'professores', titulo: 'Atribuição & Docentes', icone: 'bi-person-badge-fill', categoria: 'Área Pedagógica' },
    { id: 'classes-exames', titulo: 'Classes / Níveis & Exames', icone: 'bi-layers-fill text-success', categoria: 'Área Pedagógica' },
    { id: 'disciplinas', titulo: 'Disciplinas', icone: 'bi-book-fill', categoria: 'Área Pedagógica' },
    { id: 'desbloqueio', titulo: 'Desbloqueio de Trimestre', icone: 'bi-unlock-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'caderneta', titulo: 'Caderneta Pedagógica', icone: 'bi-journal-bookmark-fill text-info', categoria: 'Área Pedagógica' },
    { id: 'pautas', titulo: 'Pautas & Actas Oficiais', icone: 'bi-table', categoria: 'Área Pedagógica' },
    { id: 'exames', titulo: 'Exames', icone: 'bi-file-earmark-spreadsheet-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'estatisticas-aproveitamento', titulo: 'Estatística de Aproveitamento', icone: 'bi-bar-chart-line-fill text-success', categoria: 'Área Pedagógica' },
    { id: 'sumarios', titulo: 'Planos de Aula & Sumários', icone: 'bi-journal-text text-primary', categoria: 'Área Pedagógica' },
    { id: 'alunos', titulo: 'Alunos & Matrículas', icone: 'bi-people-fill', categoria: 'Secretaria & Expediente' },
    { id: 'presencas', titulo: 'Presenças dos Alunos', icone: 'bi-person-check-fill text-success', categoria: 'Secretaria & Expediente' },
    { id: 'transferencias', titulo: 'Transferências & Anulações', icone: 'bi-arrow-left-right text-primary', categoria: 'Secretaria & Expediente' },
    { id: 'certificados', titulo: 'Certificados & Declarações', icone: 'bi-award-fill', categoria: 'Secretaria & Expediente' },
    { id: 'ocorrencias', titulo: 'Ocorrências Disciplinares', icone: 'bi-exclamation-octagon-fill text-warning', categoria: 'Secretaria & Expediente' },
    { id: 'impressao', titulo: 'Central de Impressão', icone: 'bi-printer-fill', categoria: 'Secretaria & Expediente' },
    { id: 'pagamentos', titulo: 'Propinas & Mensalidades', icone: 'bi-cash-coin', categoria: 'Gestão Financeira & Bens' },
    { id: 'despesas', titulo: 'Receitas & Despesas (Aprovação)', icone: 'bi-wallet-fill text-danger', categoria: 'Gestão Financeira & Bens' },
    { id: 'comunicados', titulo: 'Comunicados Oficiais', icone: 'bi-megaphone-fill text-primary', categoria: 'Comunicação' }
  ],
  'painel-pedagogico': [
    { id: 'estatisticas-aproveitamento', titulo: 'Painel Pedagógico Geral', icone: 'bi-bar-chart-line-fill text-success', categoria: 'Visão Pedagógica' },
    { id: 'calendario', titulo: 'Calendário Escolar & Provas', icone: 'bi-calendar3 text-primary', categoria: 'Área Pedagógica' },
    { id: 'turmas', titulo: 'Turmas & Distribuição', icone: 'bi-diagram-3-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'horarios', titulo: 'Horários Lectivos', icone: 'bi-clock-history text-info', categoria: 'Área Pedagógica' },
    { id: 'professores', titulo: 'Atribuição de Disciplinas', icone: 'bi-person-badge-fill', categoria: 'Área Pedagógica' },
    { id: 'classes-exames', titulo: 'Classes & Exames', icone: 'bi-layers-fill text-success', categoria: 'Área Pedagógica' },
    { id: 'disciplinas', titulo: 'Disciplinas Curriculares', icone: 'bi-book-fill', categoria: 'Área Pedagógica' },
    { id: 'desbloqueio', titulo: 'Desbloqueio de Trimestre', icone: 'bi-unlock-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'caderneta', titulo: 'Caderneta Pedagógica', icone: 'bi-journal-bookmark-fill text-info', categoria: 'Área Pedagógica' },
    { id: 'pautas', titulo: 'Pautas, Actas & Conselhos', icone: 'bi-table', categoria: 'Área Pedagógica' },
    { id: 'exames', titulo: 'Controlo de Exames', icone: 'bi-file-earmark-spreadsheet-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'sumarios', titulo: 'Planos de Aula & Sumários', icone: 'bi-journal-text text-primary', categoria: 'Área Pedagógica' },
    { id: 'alunos', titulo: 'Processo do Aluno & Turmas', icone: 'bi-people-fill', categoria: 'Acompanhamento Discente' },
    { id: 'presencas', titulo: 'Presenças dos Alunos', icone: 'bi-person-check-fill text-success', categoria: 'Acompanhamento Discente' },
    { id: 'ocorrencias', titulo: 'Ocorrências Disciplinares', icone: 'bi-exclamation-octagon-fill text-warning', categoria: 'Acompanhamento Discente' },
    { id: 'transferencias', titulo: 'Transferências & Anulações', icone: 'bi-arrow-left-right text-primary', categoria: 'Acompanhamento Discente' },
    { id: 'material-escolar', titulo: 'Material Didático & Escolar', icone: 'bi-book-half text-primary', categoria: 'Acompanhamento Discente' },
    { id: 'comunicados', titulo: 'Comunicados Pedagógicos', icone: 'bi-megaphone-fill text-primary', categoria: 'Comunicação' }
  ],
  'painel-secretaria': [
    { id: 'dashboard', titulo: 'Painel da Secretaria', icone: 'bi-grid-1x2-fill', categoria: 'Visão Geral' },
    { id: 'alunos', titulo: 'Matrículas & Confirmações', icone: 'bi-people-fill', categoria: 'Alunos & Matrículas' },
    { id: 'transferencias', titulo: 'Guias de Transferência & Anulação', icone: 'bi-arrow-left-right text-primary', categoria: 'Alunos & Matrículas' },
    { id: 'presencas', titulo: 'Consulta de Presenças', icone: 'bi-person-check-fill text-success', categoria: 'Alunos & Matrículas' },
    { id: 'turmas', titulo: 'Turmas & Listas de Alunos', icone: 'bi-diagram-3-fill text-warning', categoria: 'Alunos & Matrículas' },
    { id: 'pautas', titulo: 'Emissão de Pautas & Boletins', icone: 'bi-table', categoria: 'Documentos & Pautas' },
    { id: 'certificados', titulo: 'Declarações & Certificados', icone: 'bi-award-fill', categoria: 'Documentos & Pautas' },
    { id: 'impressao', titulo: 'Central de Impressão Oficial', icone: 'bi-printer-fill', categoria: 'Documentos & Pautas' },
    { id: 'calendario', titulo: 'Calendário Escolar', icone: 'bi-calendar3 text-primary', categoria: 'Consulta & Apoio' },
    { id: 'horarios', titulo: 'Horários das Turmas', icone: 'bi-clock-history text-info', categoria: 'Consulta & Apoio' },
    { id: 'professores', titulo: 'Registo de Funcionários', icone: 'bi-person-badge-fill', categoria: 'Consulta & Apoio' },
    { id: 'pagamentos', titulo: 'Consulta de Propinas & Recibos', icone: 'bi-cash-coin', categoria: 'Consulta & Apoio' },
    { id: 'ocorrencias', titulo: 'Ocorrências Disciplinares', icone: 'bi-exclamation-octagon-fill text-warning', categoria: 'Consulta & Apoio' },
    { id: 'comunicados', titulo: 'Comunicados da Secretaria', icone: 'bi-megaphone-fill text-primary', categoria: 'Comunicação' }
  ],
  'painel-professor': [
    { id: 'caderneta', titulo: 'Caderneta do Professor (Notas)', icone: 'bi-journal-bookmark-fill text-info', categoria: 'Espaço do Docente' },
    { id: 'presencas', titulo: 'Registo de Presenças & Faltas', icone: 'bi-person-check-fill text-success', categoria: 'Espaço do Docente' },
    { id: 'sumarios', titulo: 'Planos de Aula & Sumários', icone: 'bi-journal-text text-primary', categoria: 'Espaço do Docente' },
    { id: 'ocorrencias', titulo: 'Ocorrências Disciplinares', icone: 'bi-exclamation-octagon-fill text-warning', categoria: 'Espaço do Docente' },
    { id: 'horarios', titulo: 'Horário & Minhas Turmas', icone: 'bi-clock-history text-info', categoria: 'Espaço do Docente' },
    { id: 'pautas', titulo: 'Pautas & Actas da Turma', icone: 'bi-table', categoria: 'Espaço do Docente' },
    { id: 'exames', titulo: 'Consulta de Exames', icone: 'bi-file-earmark-spreadsheet-fill text-warning', categoria: 'Espaço do Docente' },
    { id: 'estatisticas-aproveitamento', titulo: 'Estatística das Minhas Turmas', icone: 'bi-bar-chart-line-fill text-success', categoria: 'Espaço do Docente' },
    { id: 'material-escolar', titulo: 'Material Didático & Escolar', icone: 'bi-book-half text-primary', categoria: 'Espaço do Docente' },
    { id: 'comunicados', titulo: 'Comunicados Oficiais', icone: 'bi-megaphone-fill text-primary', categoria: 'Espaço do Docente' },
    { id: 'professor-perfil', titulo: 'Meu Perfil Docente', icone: 'bi-person-lines-fill text-primary', categoria: 'Espaço do Docente' }
  ],
  'painel-aluno': [
    { id: 'aluno-perfil', titulo: 'O Meu Perfil & Matrícula', icone: 'bi-person-vcard-fill text-primary', categoria: 'Espaço do Aluno' },
    { id: 'aluno-notas', titulo: 'As Minhas Notas & Boletim', icone: 'bi-card-checklist text-success', categoria: 'Espaço do Aluno' },
    { id: 'presencas', titulo: 'As Minhas Faltas & Presenças', icone: 'bi-person-check-fill text-success', categoria: 'Espaço do Aluno' },
    { id: 'horarios', titulo: 'O Meu Horário Escolar', icone: 'bi-clock-history text-info', categoria: 'Espaço do Aluno' },
    { id: 'aluno-pagamentos', titulo: 'As Minhas Propinas & Recibos', icone: 'bi-wallet2 text-warning', categoria: 'Espaço do Aluno' },
    { id: 'material-escolar', titulo: 'Material Escolar da Classe', icone: 'bi-book-half text-info', categoria: 'Espaço do Aluno' },
    { id: 'comunicados', titulo: 'Comunicados Escolares', icone: 'bi-megaphone-fill text-primary', categoria: 'Espaço do Aluno' }
  ],
  'painel-financeiro': [
    { id: 'dashboard', titulo: 'Visão Geral Financeira', icone: 'bi-grid-1x2-fill', categoria: 'Financeiro & Tesouraria' },
    { id: 'pagamentos', titulo: 'Mensalidades & Propinas', icone: 'bi-cash-coin', categoria: 'Financeiro & Tesouraria' },
    { id: 'despesas', titulo: 'Receitas, Despesas & Caixa', icone: 'bi-wallet-fill text-danger', categoria: 'Financeiro & Tesouraria' },
    { id: 'impressao', titulo: 'Central de Impressão de Recibos', icone: 'bi-printer-fill', categoria: 'Financeiro & Tesouraria' },
    { id: 'prompt-gateway', titulo: 'Gateway SMS & Pagamentos', icone: 'bi-broadcast-pin text-warning', categoria: 'Financeiro & Tesouraria' },
    { id: 'alunos', titulo: 'Consulta de Matrículas', icone: 'bi-people-fill', categoria: 'Apoio & Controlo' },
    { id: 'transferencias', titulo: 'Quitação de Transferências', icone: 'bi-arrow-left-right text-primary', categoria: 'Apoio & Controlo' },
    { id: 'calendario', titulo: 'Calendário Escolar', icone: 'bi-calendar3 text-primary', categoria: 'Apoio & Controlo' },
    { id: 'comunicados', titulo: 'Comunicados Financeiros', icone: 'bi-megaphone-fill text-primary', categoria: 'Comunicação' }
  ],
  'painel-escola': [
    { id: 'dashboard', titulo: 'Painel Principal Executivo', icone: 'bi-grid-1x2-fill', categoria: 'Visão Geral' },
    { id: 'escola', titulo: 'Definições & Logótipo', icone: 'bi-building-gear', categoria: 'Gestão & Governação' },
    { id: 'assinatura-escola', titulo: 'Assinatura do Sistema', icone: 'bi-shield-lock-fill text-warning', categoria: 'Gestão & Governação' },
    { id: 'usuarios-senhas', titulo: 'Utilizadores & Permissões', icone: 'bi-key-fill text-warning', categoria: 'Gestão & Governação' },
    { id: 'auditoria', titulo: 'Auditoria de Operações', icone: 'bi-shield-lock-fill text-info', categoria: 'Gestão & Governação' },
    { id: 'calendario', titulo: 'Calendário Escolar', icone: 'bi-calendar3 text-primary', categoria: 'Área Pedagógica' },
    { id: 'turmas', titulo: 'Turmas & Capacidade', icone: 'bi-diagram-3-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'horarios', titulo: 'Horários Lectivos', icone: 'bi-clock-history text-info', categoria: 'Área Pedagógica' },
    { id: 'professores', titulo: 'Atribuição & Docentes', icone: 'bi-person-badge-fill', categoria: 'Área Pedagógica' },
    { id: 'classes-exames', titulo: 'Classes / Níveis & Exames', icone: 'bi-layers-fill text-success', categoria: 'Área Pedagógica' },
    { id: 'disciplinas', titulo: 'Disciplinas', icone: 'bi-book-fill', categoria: 'Área Pedagógica' },
    { id: 'desbloqueio', titulo: 'Desbloqueio de Trimestre', icone: 'bi-unlock-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'caderneta', titulo: 'Caderneta Pedagógica', icone: 'bi-journal-bookmark-fill text-info', categoria: 'Área Pedagógica' },
    { id: 'pautas', titulo: 'Pautas & Actas Oficiais', icone: 'bi-table', categoria: 'Área Pedagógica' },
    { id: 'exames', titulo: 'Exames', icone: 'bi-file-earmark-spreadsheet-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'estatisticas-aproveitamento', titulo: 'Estatística de Aproveitamento', icone: 'bi-bar-chart-line-fill text-success', categoria: 'Área Pedagógica' },
    { id: 'sumarios', titulo: 'Planos de Aula & Sumários', icone: 'bi-journal-text text-primary', categoria: 'Área Pedagógica' },
    { id: 'alunos', titulo: 'Alunos & Matrículas', icone: 'bi-people-fill', categoria: 'Secretaria & Expediente' },
    { id: 'presencas', titulo: 'Presenças dos Alunos', icone: 'bi-person-check-fill text-success', categoria: 'Secretaria & Expediente' },
    { id: 'transferencias', titulo: 'Transferências & Anulações', icone: 'bi-arrow-left-right text-primary', categoria: 'Secretaria & Expediente' },
    { id: 'certificados', titulo: 'Certificados & Declarações', icone: 'bi-award-fill', categoria: 'Secretaria & Expediente' },
    { id: 'ocorrencias', titulo: 'Ocorrências Disciplinares', icone: 'bi-exclamation-octagon-fill text-warning', categoria: 'Secretaria & Expediente' },
    { id: 'impressao', titulo: 'Central de Impressão', icone: 'bi-printer-fill', categoria: 'Secretaria & Expediente' },
    { id: 'pagamentos', titulo: 'Propinas & Mensalidades', icone: 'bi-cash-coin', categoria: 'Gestão Financeira & Bens' },
    { id: 'despesas', titulo: 'Receitas & Despesas (Aprovação)', icone: 'bi-wallet-fill text-danger', categoria: 'Gestão Financeira & Bens' },
    { id: 'comunicados', titulo: 'Comunicados Oficiais', icone: 'bi-megaphone-fill text-primary', categoria: 'Comunicação' }
  ]
};

function renderizarSidebarPorNivel(role) {
  const isSuperAdmin = (role === 'SUPERADMIN' || state.user?.role === 'SUPERADMIN' || !!state.user?.is_superuser);
  const isSuperAdminInspecionando = isSuperAdmin && !!localStorage.getItem('sige_selected_tenant');
  const painel = isSuperAdminInspecionando ? 'painel-direcao' : (MAPA_PAINEIS[role] || 'painel-escola');
  const infoPainel = INFO_PAINEIS[painel] || INFO_PAINEIS['painel-escola'];
  const menus = MENUS_POR_PAINEL[painel] || [];
  const navContainer = document.getElementById('sidebarNavItems');
  if (!navContainer) return;

  const ITENS_SUBNAV_PEDAGOGICO = [
    'classes-exames',
    'disciplinas',
    'desbloqueio',
    'caderneta',
    'pautas',
    'exames',
    'estatisticas-aproveitamento'
  ];

  let html = '';
  if (isSuperAdminInspecionando) {
    const nomeEscola = state.tenant?.nome || 'Escola em Inspeção';
    html += `
      <div class="px-3 py-2 mb-3 bg-warning bg-opacity-25 border border-warning rounded text-dark small">
        <div class="d-flex align-items-center gap-1 mb-1 fw-bold">
          <i class="bi bi-eye-fill text-warning"></i> <span>A Inspecionar Escola:</span>
        </div>
        <div class="text-truncate fw-semibold mb-2" title="${nomeEscola}">${nomeEscola}</div>
        <button class="btn btn-dark btn-sm w-100 py-1" onclick="sairModoInspecaoSuperAdmin()">
          <i class="bi bi-box-arrow-left me-1"></i> Voltar ao SaaS
        </button>
      </div>
    `;
  } else {
    // Destaque do Painel Exclusivo no Topo da Barra Lateral
    html += `
      <div class="px-3 py-2 mb-3 rounded border border-light border-opacity-10 shadow-sm" style="background: rgba(255,255,255,0.06);">
        <div class="d-flex align-items-center justify-content-between mb-1">
          <small class="text-uppercase fw-bold text-white-50" style="font-size: 0.60rem; letter-spacing: 0.6px;">Acesso Exclusivo</small>
          <span class="badge ${infoPainel.badgeClass}" style="font-size: 0.62rem;">${infoPainel.badgeText}</span>
        </div>
        <div class="fw-bold text-white small d-flex align-items-center gap-2">
          <i class="bi ${infoPainel.icone}"></i> <span class="text-truncate">${infoPainel.titulo}</span>
        </div>
      </div>
    `;
  }

  const painelUsaAcordeaoPedagogico = ['painel-direcao', 'painel-pedagogico', 'painel-escola'].includes(painel);
  let categoriaAtual = '';

  menus.forEach(menu => {
    if (menu.categoria !== categoriaAtual) {
      categoriaAtual = menu.categoria;
      html += `<div class="nav-category">${categoriaAtual}</div>`;
      if (categoriaAtual === 'Área Pedagógica' && painelUsaAcordeaoPedagogico) {
        html += `
          <a class="nav-link d-flex align-items-center justify-content-between" href="javascript:void(0)" onclick="toggleSubmenuAreaPedagogica(event)" id="nav-area-pedagogica">
            <div class="d-flex align-items-center gap-2">
              <i class="bi bi-mortarboard-fill text-primary"></i> <span>Área Pedagógica</span>
            </div>
            <i class="bi bi-chevron-down small" id="seta-area-pedagogica" style="transition: transform 0.2s;"></i>
          </a>
          <div id="subnav-area-pedagogica" class="ps-3 border-start ms-3 my-1" style="display: none;">
            <a class="nav-link py-1 small" href="javascript:void(0)" onclick="navegarPara('classes-exames')" id="subnav-classes-exames">
              <i class="bi bi-layers-fill text-success me-1"></i> <span>Classes / Níveis & Exames</span>
            </a>
            <a class="nav-link py-1 small" href="javascript:void(0)" onclick="navegarPara('disciplinas')" id="subnav-disciplinas">
              <i class="bi bi-book-fill text-primary me-1"></i> <span>Disciplinas</span>
            </a>
            <a class="nav-link py-1 small" href="javascript:void(0)" onclick="navegarPara('desbloqueio')" id="subnav-desbloqueio">
              <i class="bi bi-unlock-fill text-warning me-1"></i> <span>Desbloqueio de Trimestre</span>
            </a>
            <a class="nav-link py-1 small" href="javascript:void(0)" onclick="navegarPara('caderneta')" id="subnav-caderneta">
              <i class="bi bi-journal-bookmark-fill text-info me-1"></i> <span>Caderneta Pedagógica</span>
            </a>
            <a class="nav-link py-1 small" href="javascript:void(0)" onclick="navegarPara('pautas')" id="subnav-pautas">
              <i class="bi bi-table text-primary me-1"></i> <span>Pautas & Actas Oficiais</span>
            </a>
            <a class="nav-link py-1 small" href="javascript:void(0)" onclick="navegarPara('exames')" id="subnav-exames">
              <i class="bi bi-file-earmark-spreadsheet-fill text-warning me-1"></i> <span>Exames</span>
            </a>
            <a class="nav-link py-1 small" href="javascript:void(0)" onclick="navegarPara('estatisticas-aproveitamento')" id="subnav-estatisticas-aproveitamento">
              <i class="bi bi-bar-chart-line-fill text-success me-1"></i> <span>Estatística de Aproveitamento</span>
            </a>
          </div>
        `;
      }
    }

    // Se o item estiver dentro do submenu colapsável da Área Pedagógica no painel que usa acordeão, não renderizar como link solto
    if (painelUsaAcordeaoPedagogico && menu.categoria === 'Área Pedagógica' && ITENS_SUBNAV_PEDAGOGICO.includes(menu.id)) {
      return;
    }

    html += `
      <a class="nav-link" href="#" onclick="navegarPara('${menu.id}')" id="nav-${menu.id}">
        <i class="bi ${menu.icone}"></i> <span>${menu.titulo}</span>
      </a>
    `;
  });

  html += `
    <div class="mt-4 pt-3 border-top px-2">
      <a class="nav-link text-light py-2 rounded d-flex align-items-center gap-2 mb-1" href="javascript:void(0)" onclick="modalRedefinirMinhaSenha()" title="Ver o meu perfil de utilizador e alterar palavra-passe">
        <i class="bi bi-person-gear text-warning fs-5"></i> <span>Meu Perfil & Alterar Senha</span>
      </a>
      <a class="nav-link text-danger fw-bold py-2 rounded d-flex align-items-center gap-2" href="#" onclick="fazerLogout(event)" id="nav-logout-sidebar" title="Terminar sessão com segurança">
        <i class="bi bi-box-arrow-right text-danger fs-5"></i> <span>Sair do Sistema</span>
      </a>
    </div>
  `;

  navContainer.innerHTML = html;
}

function aplicarPermissoesVisualizacao(role) {
  const isSuperAdmin = (role === 'SUPERADMIN' || state.user?.role === 'SUPERADMIN' || !!state.user?.is_superuser);
  const isSuperAdminInspecionando = isSuperAdmin && !!localStorage.getItem('sige_selected_tenant');
  const painel = isSuperAdminInspecionando ? 'painel-direcao' : (MAPA_PAINEIS[role] || 'painel-escola');
  const infoPainel = INFO_PAINEIS[painel] || INFO_PAINEIS['painel-direcao'];

  // Atualizar cabeçalho superior (Topbar) com o nome e escopo do painel activo
  const elPageTitle = document.getElementById('pageTitle');
  const elSubPageTitle = document.getElementById('subPageTitle');
  if (elPageTitle && infoPainel) elPageTitle.textContent = infoPainel.titulo;
  if (elSubPageTitle && infoPainel) elSubPageTitle.textContent = infoPainel.subtitulo;

  renderizarSidebarPorNivel(isSuperAdminInspecionando ? 'ADMIN_ESCOLA' : role);

  const btnPromptGateway = document.getElementById('btnTopbarPromptGateway');
  const btnToggleNotas = document.getElementById('btnToggleNotasDap');
  const btnComprovativo = document.getElementById('btnComprovativoEscola');
  const tenantCard = document.getElementById('sidebarTenantCard');
  const tenantSelectWrapper = document.getElementById('superAdminTenantSelectWrapper');

  if (isSuperAdmin) {
    document.body.classList.add('role-superadmin');
    if (isSuperAdminInspecionando) {
      document.body.classList.add('inspecionando-escola');
    } else {
      document.body.classList.remove('inspecionando-escola');
    }
    if (tenantSelectWrapper) tenantSelectWrapper.style.display = 'block';
    if (btnToggleNotas) btnToggleNotas.style.display = 'flex';
    if (btnComprovativo) btnComprovativo.classList.remove('d-none');
    if (btnPromptGateway) btnPromptGateway.style.display = 'inline-flex';
    if (tenantCard) tenantCard.style.display = 'block';
  } else {
    // Restrição absoluta: controles de inspeção SuperAdmin nunca aparecem para outros papéis
    document.body.classList.remove('role-superadmin');
    document.body.classList.remove('inspecionando-escola');
    localStorage.removeItem('sige_selected_tenant');
    if (tenantSelectWrapper) tenantSelectWrapper.style.display = 'none';

    if (role === 'ALUNO' || role === 'ENCARREGADO') {
      if (btnToggleNotas) btnToggleNotas.style.display = 'none';
      if (btnComprovativo) btnComprovativo.classList.add('d-none');
      if (btnPromptGateway) btnPromptGateway.style.display = 'none';
      if (tenantCard) tenantCard.style.display = 'none';
    } else if (role === 'PROFESSOR') {
      if (btnToggleNotas) btnToggleNotas.style.display = 'none';
      if (btnComprovativo) btnComprovativo.classList.add('d-none');
      if (btnPromptGateway) btnPromptGateway.style.display = 'none';
      if (tenantCard) tenantCard.style.display = 'block';
    } else if (role === 'SECRETARIA' || role === 'CHEFE_SECRETARIA') {
      if (btnToggleNotas) btnToggleNotas.style.display = 'none';
      if (btnComprovativo) btnComprovativo.classList.add('d-none');
      if (btnPromptGateway) btnPromptGateway.style.display = 'none';
      if (tenantCard) tenantCard.style.display = 'block';
    } else if (role === 'FINANCEIRO') {
      if (btnToggleNotas) btnToggleNotas.style.display = 'none';
      if (btnComprovativo) btnComprovativo.classList.add('d-none');
      if (btnPromptGateway) btnPromptGateway.style.display = 'inline-flex';
      if (tenantCard) tenantCard.style.display = 'block';
    } else if (role === 'DAP') {
      if (btnToggleNotas) btnToggleNotas.style.display = 'flex';
      if (btnComprovativo) btnComprovativo.classList.add('d-none');
      if (btnPromptGateway) btnPromptGateway.style.display = 'none';
      if (tenantCard) tenantCard.style.display = 'block';
    } else {
      // DIRECTOR_ESCOLA, ADMIN_ESCOLA
      if (btnToggleNotas) btnToggleNotas.style.display = 'flex';
      if (btnComprovativo) btnComprovativo.classList.remove('d-none');
      if (btnPromptGateway) btnPromptGateway.style.display = 'inline-flex';
      if (tenantCard) tenantCard.style.display = 'block';
    }
  }
}

function atualizarBadgeTenant(tenant) {
  if (!tenant) return;
  const elNome = document.getElementById('sidebarEscolaNome');
  if (elNome) elNome.textContent = tenant.nome || 'Escola';
  const badge = document.getElementById('sidebarStatusBadge');
  if (badge) {
    const st = tenant.status || 'ATIVA';
    badge.textContent = st;
    badge.className = `badge badge-${st.toLowerCase()} mt-1`;
  }

  const prov = tenant.provincia || 'Maputo';
  const elProv = document.getElementById('sidebarProvinciaBadge');
  if (elProv) elProv.textContent = prov;

  const elAno = document.getElementById('headerAnoLetivo');
  if (elAno) elAno.textContent = `Ano Lectivo: ${tenant.ano_letivo_ativo || 2026}`;

  const elEmblema = document.getElementById('sidebarEmblemaContainer');
  if (elEmblema) {
    if (tenant.usar_emblema_nacional) {
      elEmblema.innerHTML = '<img src="/img/emblema-mocambique.png" alt="Emblema Nacional" style="width: 48px; height: 48px; object-fit: contain;">';
      elEmblema.style.display = 'block';
    } else if (tenant.logo_url || tenant.logo_base64) {
      const srcLogo = tenant.logo_base64 || tenant.logo_url;
      elEmblema.innerHTML = `<img src="${srcLogo}" alt="Logótipo da Escola" style="width: 48px; height: 48px; object-fit: contain; border-radius: 6px;">`;
      elEmblema.style.display = 'block';
    } else {
      elEmblema.style.display = 'none';
    }
  }
}

async function carregarAnosLectivos() {
  try {
    const res = await apiFetch('/api/v1/configuracoes/anos-lectivos', { ignoreAuthRedirect: true });
    if (res && res.success && Array.isArray(res.data) && res.data.length > 0) {
      state.anosLectivos = res.data;
    } else {
      state.anosLectivos = gerarAnosLectivosFallback();
    }
  } catch (_) {
    state.anosLectivos = gerarAnosLectivosFallback();
  }
  renderizarSelectoresAnoLectivo();
}

function gerarAnosLectivosFallback() {
  const anoAtual = new Date().getFullYear();
  return [
    { ano: anoAtual + 1, status: 'PLANEADO' },
    { ano: anoAtual, status: 'ACTIVO' },
    { ano: anoAtual - 1, status: 'ENCERRADO' },
    { ano: anoAtual - 2, status: 'ENCERRADO' }
  ];
}

function renderizarSelectoresAnoLectivo() {
  const selects = document.querySelectorAll('.sige-select-ano-lectivo');
  if (!selects.length) return;
  const anoAtivo = state.tenant?.ano_letivo_ativo || new Date().getFullYear();
  selects.forEach(sel => {
    const valAtual = sel.value;
    sel.innerHTML = '<option value="">-- Escolha ano Lectivo --</option>';
    (state.anosLectivos || []).forEach(item => {
      const opt = document.createElement('option');
      opt.value = item.ano;
      opt.textContent = `${item.ano} (${item.status || 'ENCERRADO'})`;
      sel.appendChild(opt);
    });
    if (valAtual) sel.value = valAtual;
  });
}

function setCarregandoBuscaAno(carregando) {
  document.querySelectorAll('.btn-sige-buscar-ano').forEach(btn => {
    btn.disabled = carregando;
    if (carregando) {
      btn.dataset.oldHtml = btn.innerHTML;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> A buscar...';
    } else if (btn.dataset.oldHtml) {
      btn.innerHTML = btn.dataset.oldHtml;
    }
  });
}

function obterViewAtiva() {
  return state.currentView || 'dashboard';
}

async function atualizarDadosModuloPorAno(ano) {
  state.anoLectivoFiltro = ano;
  const viewAtiva = obterViewAtiva();
  if (typeof aoSelecionarAnoLectivoMestre === 'function') {
    try {
      await aoSelecionarAnoLectivoMestre(ano);
    } catch (e) {
      console.warn('Erro ao disparar aoSelecionarAnoLectivoMestre:', e);
    }
  }
}

async function carregarEscolasSuperAdminSelect() {
  const sel = document.getElementById('superAdminTenantSelect');
  if (!sel) return;
  try {
    const res = await apiFetch('/api/v1/saas-admin/escolas');
    if (res && res.success && Array.isArray(res.data)) {
      state.escolasSaaS = res.data;
      sel.innerHTML = '<option value="">(Visão Master SaaS)</option>';
      const tenantAtivo = localStorage.getItem('sige_selected_tenant');
      res.data.forEach(esc => {
        const opt = document.createElement('option');
        opt.value = esc.id;
        opt.textContent = `${esc.nome} [${esc.codigo_escola || esc.codigo || ''}] - ${esc.status}`;
        if (tenantAtivo && esc.id === tenantAtivo) opt.selected = true;
        sel.appendChild(opt);
      });
    }
  } catch (err) {
    console.warn('Erro ao carregar lista de escolas para SuperAdmin:', err);
  }
}

async function alternarEscolaSuperAdmin(escolaId, escolaNome = '', escolaStatus = '') {
  if (!escolaId) {
    localStorage.removeItem('sige_selected_tenant');
    state.tenant = null;
    document.body.classList.remove('inspecionando-escola');
    renderizarSidebarPorNivel('SUPERADMIN');
    navegarPara('saas');
    return;
  }
  localStorage.setItem('sige_selected_tenant', escolaId);
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}`);
    if (res && res.success) {
      state.tenant = res.data;
    } else {
      state.tenant = { id: escolaId, nome: escolaNome || 'Escola', status: escolaStatus || 'ATIVA' };
    }
  } catch (_) {
    state.tenant = { id: escolaId, nome: escolaNome || 'Escola', status: escolaStatus || 'ATIVA' };
  }
  document.body.classList.add('inspecionando-escola');
  renderizarSidebarPorNivel('ADMIN_ESCOLA');
  atualizarBadgeTenant(state.tenant);
  navegarPara('dashboard');
}

function sairModoInspecaoSuperAdmin() {
  alternarEscolaSuperAdmin('');
}

function alternarSidebarMobile() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('show');
}

function fecharSidebarMobile() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar && sidebar.classList.contains('show')) {
    sidebar.classList.remove('show');
  }
}

function navegarPara(viewId) {
  fecharSidebarMobile();

  const role = state.user?.role || 'ADMIN_ESCOLA';
  const isSuperAdmin = (role === 'SUPERADMIN' || state.user?.role === 'SUPERADMIN' || !!state.user?.is_superuser);
  const isSuperAdminInspecionando = (isSuperAdmin && !!localStorage.getItem('sige_selected_tenant'));

  const painel = isSuperAdmin
    ? (isSuperAdminInspecionando ? 'painel-direcao' : 'painel-superadmin')
    : (MAPA_PAINEIS[role] || 'painel-escola');

  const infoPainel = INFO_PAINEIS[painel] || INFO_PAINEIS['painel-direcao'];

  // Lista estrita de menus autorizados para o perfil actual
  const todosMenus = Array.from(new Set(Object.values(MENUS_POR_PAINEL).flatMap(lista => lista.map(m => m.id))));
  const menusPermitidos = isSuperAdmin
    ? todosMenus
    : (isSuperAdminInspecionando
        ? [...(MENUS_POR_PAINEL['painel-superadmin'] || []).map(m => m.id), ...(MENUS_POR_PAINEL['painel-direcao'] || []).map(m => m.id)]
        : (MENUS_POR_PAINEL[painel] || []).map(m => m.id));

  // Se o painel usar acordeão pedagógico, incluir os subitens
  if (['painel-direcao', 'painel-pedagogico', 'painel-escola'].includes(painel)) {
    ['classes-exames', 'disciplinas', 'desbloqueio', 'caderneta', 'pautas', 'exames', 'estatisticas-aproveitamento'].forEach(id => {
      if (!menusPermitidos.includes(id)) menusPermitidos.push(id);
    });
  }

  // ISOLAMENTO ESTRITO ENTRE PAINÉIS (Professores, Secretaria, Aluno, Administração e Finanças, etc.)
  if (!isSuperAdmin && !menusPermitidos.includes(viewId)) {
    console.warn(`[SEGURANÇA] Bloqueio estrito de painel: Perfil '${role}' (${painel}) tentou aceder à view não autorizada '${viewId}'.`);
    mostrarToast(`Acesso restrito: O seu perfil (${role}) tem acesso exclusivo ao ${infoPainel.titulo}.`, 'danger');
    viewId = VIEW_INICIAL_POR_ROLE[role] || menusPermitidos[0] || 'dashboard';
  }

  // Se o SuperAdmin está acedendo a um módulo escolar sem escola selecionada, selecionar a primeira escola disponível
  if (isSuperAdmin && painel === 'painel-direcao' && !localStorage.getItem('sige_selected_tenant')) {
    let escolaPadrao = state.escolasSaaS?.[0];
    if (!escolaPadrao) {
      try {
        apiFetch('/api/v1/saas-admin/escolas').then(res => {
          if (res && res.success && Array.isArray(res.data) && res.data.length > 0) {
            state.escolasSaaS = res.data;
            alternarEscolaSuperAdmin(res.data[0].id, res.data[0].nome, res.data[0].status);
          }
        }).catch(() => {});
      } catch (_) {}
    } else {
      alternarEscolaSuperAdmin(escolaPadrao.id, escolaPadrao.nome, escolaPadrao.status);
    }
  }

  state.currentView = viewId;

  if (viewId === 'saas' && !isSuperAdminInspecionando) {
    if (typeof restaurarPadraoTemaEFundo === 'function') {
      restaurarPadraoTemaEFundo();
    }
  }

  // Carregar ficheiro de página (HTML) e módulo (JS)
  carregarPaginaModulo(painel, viewId).then(() => {
    carregarScriptModulo(painel, viewId).then(() => {
      // Ocultar todas as views e exibir a view solicitada
      document.querySelectorAll('.modulo-view').forEach(v => {
        v.style.display = 'none';
        v.classList.remove('active');
      });
      const elSecao = document.getElementById(`view-${viewId}`);
      if (elSecao) {
        elSecao.style.display = 'block';
        elSecao.classList.add('active');
      }

      // Marcar link activo na barra lateral
      document.querySelectorAll('#sidebarNavItems .nav-link').forEach(link => link.classList.remove('active'));
      const linkAtivo = document.getElementById(`nav-${viewId}`) || document.getElementById(`subnav-${viewId}`);
      if (linkAtivo) linkAtivo.classList.add('active');

      // Se for subitem da Área Pedagógica, manter o acordeão aberto
      const subnav = document.getElementById('subnav-area-pedagogica');
      const seta = document.getElementById('seta-area-pedagogica');
      const ITENS_SUBNAV_PEDAGOGICO = ['classes-exames', 'disciplinas', 'desbloqueio', 'caderneta', 'pautas', 'exames', 'estatisticas-aproveitamento'];
      if (ITENS_SUBNAV_PEDAGOGICO.includes(viewId) && subnav) {
        subnav.style.display = 'block';
        if (seta) seta.style.transform = 'rotate(180deg)';
        const navMae = document.getElementById('nav-area-pedagogica');
        if (navMae) navMae.classList.add('active');
      }

      // Disparar gancho de inicialização do módulo, se existir
      const fnNome = `inicializarModulo_${viewId.replace(/-/g, '_')}`;
      if (typeof window[fnNome] === 'function') {
        window[fnNome]();
      }
    });
  });
}

const cachePaginasModular = {};

async function carregarPaginaModulo(painel, viewId) {
  if (Date.now() - (sigeUpdateState.ultimoCheck || 0) > 30000) {
    sigeChecarVersaoServidor();
  }

  const container = document.getElementById('conteudo-modulo') || document.querySelector('main.content-area');
  if (!container) return null;

  const idSecao = `view-${viewId}`;
  let viewEl = document.getElementById(idSecao);
  if (viewEl && container.contains(viewEl)) {
    return viewEl;
  }

  const buildParam = (typeof sigeCurrentBuild === 'function' && sigeCurrentBuild()) || Date.now();

  // Resolução inteligente da pasta para evitar erros 404 no console
  const ARQUIVOS_PROPRIOS = {
    'painel-aluno': ['aluno-notas', 'aluno-pagamentos', 'aluno-perfil', 'material-escolar'],
    'painel-professor': ['caderneta', 'director-turma', 'estatisticas-aproveitamento', 'exames', 'material-escolar', 'pautas', 'professor-perfil'],
    'painel-financeiro': ['dashboard', 'impressao', 'pagamentos', 'prompt-gateway'],
    'painel-superadmin': ['acessos', 'pagamentos-saas', 'prompt-gateway', 'saas', 'usuarios-senhas']
  };

  let pastaCarregamento = 'painel-escola';
  if (ARQUIVOS_PROPRIOS[painel] && ARQUIVOS_PROPRIOS[painel].includes(viewId)) {
    pastaCarregamento = painel;
  } else if (painel === 'painel-superadmin') {
    pastaCarregamento = 'painel-superadmin';
  }

  const urlPagina = `/pages/${pastaCarregamento}/${viewId}.html?v=${encodeURIComponent(buildParam)}`;
  try {
    let html = cachePaginasModular[urlPagina];
    if (!html) {
      let resp = await fetch(urlPagina);
      if (!resp.ok) {
        const fallbacks = ['painel-escola', 'painel-superadmin', 'painel-professor', 'painel-aluno', 'painel-financeiro']
          .filter(p => p !== pastaCarregamento);
        for (const fbPainel of fallbacks) {
          const fallbackUrl = `/pages/${fbPainel}/${viewId}.html?v=${encodeURIComponent(buildParam)}`;
          try {
            const fbResp = await fetch(fallbackUrl);
            if (fbResp.ok) {
              resp = fbResp;
              break;
            }
          } catch (_) {}
        }
      }
      if (resp && resp.ok) {
        html = await resp.text();
        cachePaginasModular[urlPagina] = html;
      }
    }
    if (html) {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = html;
      const novaView = wrapper.querySelector('.modulo-view') || wrapper.firstElementChild;
      if (novaView) {
        if (!novaView.id) novaView.id = idSecao;
        container.appendChild(novaView);
        return novaView;
      }
    }
  } catch (err) {
    console.error(`Erro ao carregar template modular ${urlPagina}:`, err);
  }
  return null;
}

async function carregarScriptModulo(painel, viewId) {
  const idScript = `script-modulo-${viewId}`;
  if (document.getElementById(idScript)) return;
  const buildParam = (typeof sigeCurrentBuild === 'function' && sigeCurrentBuild()) || Date.now();

  const SCRIPTS_PROPRIOS = {
    'painel-aluno': ['aluno-notas', 'aluno-pagamentos', 'aluno-perfil', 'material-escolar'],
    'painel-professor': ['caderneta', 'director-turma', 'estatisticas-aproveitamento', 'material-escolar', 'pautas'],
    'painel-financeiro': ['dashboard', 'impressao', 'pagamentos', 'prompt-gateway'],
    'painel-superadmin': ['acessos', 'pagamentos-saas', 'prompt-gateway', 'saas', 'usuarios-senhas']
  };

  let pastaScript = 'painel-escola';
  if (SCRIPTS_PROPRIOS[painel] && SCRIPTS_PROPRIOS[painel].includes(viewId)) {
    pastaScript = painel;
  } else if (painel === 'painel-superadmin') {
    pastaScript = 'painel-superadmin';
  }

  const scriptUrl = `/js/modules/${pastaScript}/${viewId}.js?v=${encodeURIComponent(buildParam)}`;
  return new Promise((resolve) => {
    const s = document.createElement('script');
    s.id = idScript;
    s.src = scriptUrl;
    s.onload = () => resolve();
    s.onerror = () => {
      const fallbacks = ['painel-escola', 'painel-superadmin', 'painel-professor', 'painel-aluno', 'painel-financeiro']
        .filter(p => p !== pastaScript);
      let i = 0;
      function tentarProximo() {
        if (i >= fallbacks.length) return resolve();
        const fbPainel = fallbacks[i++];
        const fb = document.createElement('script');
        fb.id = `${idScript}-fallback-${fbPainel}`;
        fb.src = `/js/modules/${fbPainel}/${viewId}.js?v=${encodeURIComponent(buildParam)}`;
        fb.onload = () => resolve();
        fb.onerror = () => tentarProximo();
        document.body.appendChild(fb);
      }
      tentarProximo();
    };
    document.body.appendChild(s);
  });
}
"""

    text = text[:idx_mapas] + bloco_novo + text[idx_faixa:]
    print("Bloco de RBAC, Mapas e Navegação substituído com sucesso!")

with open('frontend/js/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("app.js atualizado com sucesso!")
