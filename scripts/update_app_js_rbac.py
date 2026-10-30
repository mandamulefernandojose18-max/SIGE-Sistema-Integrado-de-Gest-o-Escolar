import re

path = r'd:\SIGE\frontend\js\app.js'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

# Replace MAPA_PAINEIS
old_mapa = """const MAPA_PAINEIS = {
  SUPERADMIN: 'painel-superadmin',
  ADMIN_ESCOLA: 'painel-escola',
  DIRECTOR_ESCOLA: 'painel-escola',
  DAP: 'painel-escola',
  CHEFE_SECRETARIA: 'painel-escola',
  PROFESSOR: 'painel-professor',
  ALUNO: 'painel-aluno',
  FINANCEIRO: 'painel-financeiro'
};"""

new_mapa = """const MAPA_PAINEIS = {
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
};"""

assert old_mapa in code, "old_mapa not found"
code = code.replace(old_mapa, new_mapa)

# Update MENUS_POR_PAINEL
target_menus_start = "const MENUS_POR_PAINEL = {"
# Find the closing "};" of MENUS_POR_PAINEL
idx_start = code.find(target_menus_start)
idx_end = code.find("};\n\nfunction renderizarSidebarPorNivel", idx_start)

new_menus = """const MENUS_POR_PAINEL = {
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
    { id: 'pagamentos', titulo: 'Consulta de Propinas', icone: 'bi-cash-coin', categoria: 'Consulta & Apoio' },
    { id: 'ocorrencias', titulo: 'Ocorrências Disciplinares', icone: 'bi-exclamation-octagon-fill text-warning', categoria: 'Consulta & Apoio' },
    { id: 'comunicados', titulo: 'Comunicados da Secretaria', icone: 'bi-megaphone-fill text-primary', categoria: 'Comunicação' }
  ],
  'painel-professor': [
    { id: 'professor-perfil', titulo: 'Meu Perfil Docente', icone: 'bi-person-lines-fill text-primary', categoria: 'Espaço do Docente' },
    { id: 'caderneta', titulo: 'Caderneta do Professor (Notas)', icone: 'bi-journal-bookmark-fill text-info', categoria: 'Espaço do Docente' },
    { id: 'presencas', titulo: 'Registo de Presenças & Faltas', icone: 'bi-person-check-fill text-success', categoria: 'Espaço do Docente' },
    { id: 'sumarios', titulo: 'Planos de Aula & Sumários', icone: 'bi-journal-text text-primary', categoria: 'Espaço do Docente' },
    { id: 'ocorrencias', titulo: 'Ocorrências Disciplinares', icone: 'bi-exclamation-octagon-fill text-warning', categoria: 'Espaço do Docente' },
    { id: 'horarios', titulo: 'Horário & Minhas Turmas', icone: 'bi-clock-history text-info', categoria: 'Espaço do Docente' },
    { id: 'pautas', titulo: 'Pautas & Actas Oficiais', icone: 'bi-table', categoria: 'Espaço do Docente' },
    { id: 'exames', titulo: 'Exames', icone: 'bi-file-earmark-spreadsheet-fill text-warning', categoria: 'Espaço do Docente' },
    { id: 'estatisticas-aproveitamento', titulo: 'Estatística das Minhas Turmas', icone: 'bi-bar-chart-line-fill text-success', categoria: 'Espaço do Docente' },
    { id: 'material-escolar', titulo: 'Material Didático & Escolar', icone: 'bi-book-half text-primary', categoria: 'Espaço do Docente' },
    { id: 'comunicados', titulo: 'Comunicados', icone: 'bi-megaphone-fill text-primary', categoria: 'Espaço do Docente' }
  ],
  'painel-aluno': [
    { id: 'aluno-perfil', titulo: 'O Meu Perfil & Filiação', icone: 'bi-person-vcard-fill text-primary', categoria: 'Espaço do Aluno' },
    { id: 'aluno-notas', titulo: 'As Minhas Notas & Boletim', icone: 'bi-card-checklist text-success', categoria: 'Espaço do Aluno' },
    { id: 'presencas', titulo: 'As Minhas Faltas & Presenças', icone: 'bi-person-check-fill text-success', categoria: 'Espaço do Aluno' },
    { id: 'horarios', titulo: 'O Meu Horário Escolar', icone: 'bi-clock-history text-info', categoria: 'Espaço do Aluno' },
    { id: 'aluno-pagamentos', titulo: 'As Minhas Propinas & Mensalidades', icone: 'bi-wallet2 text-warning', categoria: 'Espaço do Aluno' },
    { id: 'material-escolar', titulo: 'Material Escolar da Minha Classe', icone: 'bi-book-half text-info', categoria: 'Espaço do Aluno' },
    { id: 'comunicados', titulo: 'Comunicados Escolares', icone: 'bi-megaphone-fill text-primary', categoria: 'Espaço do Aluno' }
  ],
  'painel-financeiro': [
    { id: 'dashboard', titulo: 'Visão Geral Financeira', icone: 'bi-grid-1x2-fill', categoria: 'Financeiro & Tesouraria' },
    { id: 'pagamentos', titulo: 'Mensalidades & Propinas', icone: 'bi-cash-coin', categoria: 'Financeiro & Tesouraria' },
    { id: 'despesas', titulo: 'Receitas & Despesas (Caixa)', icone: 'bi-wallet-fill text-danger', categoria: 'Financeiro & Tesouraria' },
    { id: 'impressao', titulo: 'Central de Impressão de Recibos', icone: 'bi-printer-fill', categoria: 'Financeiro & Tesouraria' },
    { id: 'prompt-gateway', titulo: 'Gateway SMS & Pagamentos', icone: 'bi-broadcast-pin text-warning', categoria: 'Financeiro & Tesouraria' },
    { id: 'alunos', titulo: 'Consulta de Matrículas', icone: 'bi-people-fill', categoria: 'Apoio & Controlo' },
    { id: 'transferencias', titulo: 'Quitação de Transferências', icone: 'bi-arrow-left-right text-primary', categoria: 'Apoio & Controlo' },
    { id: 'calendario', titulo: 'Calendário Escolar', icone: 'bi-calendar3 text-primary', categoria: 'Apoio & Controlo' },
    { id: 'comunicados', titulo: 'Comunicados Financeiros', icone: 'bi-megaphone-fill text-primary', categoria: 'Comunicação' }
  ],
  'painel-escola': [
    { id: 'dashboard', titulo: 'Painel Principal', icone: 'bi-grid-1x2-fill', categoria: 'Geral' },
    { id: 'escola', titulo: 'Definições & Logótipo', icone: 'bi-building-gear', categoria: 'Gestão Escolar' },
    { id: 'assinatura-escola', titulo: 'Assinatura do Sistema', icone: 'bi-shield-lock-fill text-warning', categoria: 'Gestão Escolar' },
    { id: 'turmas', titulo: 'Turmas & Capacidade', icone: 'bi-diagram-3-fill text-warning', categoria: 'Gestão Escolar' },
    { id: 'alunos', titulo: 'Alunos & Matrículas', icone: 'bi-people-fill', categoria: 'Gestão Escolar' },
    { id: 'professores', titulo: 'Corpo Docente', icone: 'bi-person-badge-fill', categoria: 'Gestão Escolar' },
    { id: 'classes-exames', titulo: 'Classes / Níveis & Exames', icone: 'bi-layers-fill text-success', categoria: 'Área Pedagógica' },
    { id: 'disciplinas', titulo: 'Disciplinas', icone: 'bi-book-fill', categoria: 'Área Pedagógica' },
    { id: 'desbloqueio', titulo: 'Desbloqueio de Trimestre', icone: 'bi-unlock-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'caderneta', titulo: 'Caderneta Pedagógica', icone: 'bi-journal-bookmark-fill text-info', categoria: 'Área Pedagógica' },
    { id: 'pautas', titulo: 'Pautas & Actas Oficiais', icone: 'bi-table', categoria: 'Área Pedagógica' },
    { id: 'exames', titulo: 'Exames', icone: 'bi-file-earmark-spreadsheet-fill text-warning', categoria: 'Área Pedagógica' },
    { id: 'estatisticas-aproveitamento', titulo: 'Estatística de Aproveitamento', icone: 'bi-bar-chart-line-fill text-success', categoria: 'Área Pedagógica' },
    { id: 'material-escolar', titulo: 'Material Escolar', icone: 'bi-book-half text-primary', categoria: 'Área Pedagógica' },
    { id: 'certificados', titulo: 'Certificados (QR Code)', icone: 'bi-award-fill', categoria: 'Financeiro & Secretaria' },
    { id: 'pagamentos', titulo: 'Mensalidades & Propinas', icone: 'bi-cash-coin', categoria: 'Financeiro & Secretaria' },
    { id: 'impressao', titulo: 'Central de Impressão', icone: 'bi-printer-fill', categoria: 'Financeiro & Secretaria' },
    { id: 'usuarios-senhas', titulo: 'Cofre de Credenciais', icone: 'bi-key-fill text-warning', categoria: 'Segurança & Cofre' },
    { id: 'acessos', titulo: 'Auditoria & Acessos', icone: 'bi-shield-check', categoria: 'Segurança & Cofre' }
  ]
}"""

code = code[:idx_start] + new_menus + code[idx_end:]

# Update carregarPaginaModulo and carregarScriptModulo with fallback
old_router_funcs = """  const buildParam = (typeof sigeCurrentBuild === 'function' && sigeCurrentBuild()) || Date.now();
  const urlPagina = `/pages/${painel}/${viewId}.html?v=${encodeURIComponent(buildParam)}`;
  try {
    let html = cachePaginasModular[urlPagina];
    if (!html) {
      const resp = await fetch(urlPagina);
      if (resp.ok) {
        html = await resp.text();
        cachePaginasModular[urlPagina] = html;
      }
    }"""

new_router_funcs = """  const buildParam = (typeof sigeCurrentBuild === 'function' && sigeCurrentBuild()) || Date.now();
  const urlPagina = `/pages/${painel}/${viewId}.html?v=${encodeURIComponent(buildParam)}`;
  try {
    let html = cachePaginasModular[urlPagina];
    if (!html) {
      let resp = await fetch(urlPagina);
      if (!resp.ok && (painel === 'painel-direcao' || painel === 'painel-pedagogico' || painel === 'painel-secretaria')) {
        const fallbackUrl = `/pages/painel-escola/${viewId}.html?v=${encodeURIComponent(buildParam)}`;
        resp = await fetch(fallbackUrl);
      }
      if (resp.ok) {
        html = await resp.text();
        cachePaginasModular[urlPagina] = html;
      }
    }"""

assert old_router_funcs in code, "old_router_funcs not found"
code = code.replace(old_router_funcs, new_router_funcs)

old_script_func = """async function carregarScriptModulo(painel, viewId) {
  const idScript = `script-modulo-${painel}-${viewId}`;
  if (document.getElementById(idScript)) return;
  const buildParam = (typeof sigeCurrentBuild === 'function' && sigeCurrentBuild()) || Date.now();
  const scriptUrl = `/js/modules/${painel}/${viewId}.js?v=${encodeURIComponent(buildParam)}`;
  return new Promise((resolve) => {
    const s = document.createElement('script');
    s.id = idScript;
    s.src = scriptUrl;
    s.onload = () => resolve();
    s.onerror = () => resolve();
    document.body.appendChild(s);
  });
}"""

new_script_func = """async function carregarScriptModulo(painel, viewId) {
  const idScript = `script-modulo-${painel}-${viewId}`;
  if (document.getElementById(idScript)) return;
  const buildParam = (typeof sigeCurrentBuild === 'function' && sigeCurrentBuild()) || Date.now();
  const scriptUrl = `/js/modules/${painel}/${viewId}.js?v=${encodeURIComponent(buildParam)}`;
  return new Promise((resolve) => {
    const s = document.createElement('script');
    s.id = idScript;
    s.src = scriptUrl;
    s.onload = () => resolve();
    s.onerror = () => {
      if (painel === 'painel-direcao' || painel === 'painel-pedagogico' || painel === 'painel-secretaria') {
        const fb = document.createElement('script');
        fb.id = `${idScript}-fallback`;
        fb.src = `/js/modules/painel-escola/${viewId}.js?v=${encodeURIComponent(buildParam)}`;
        fb.onload = () => resolve();
        fb.onerror = () => resolve();
        document.body.appendChild(fb);
      } else {
        resolve();
      }
    };
    document.body.appendChild(s);
  });
}"""

assert old_script_func in code, "old_script_func not found"
code = code.replace(old_script_func, new_script_func)

with open(path, 'w', encoding='utf-8') as f:
    f.write(code)

print('app.js updated successfully!')
