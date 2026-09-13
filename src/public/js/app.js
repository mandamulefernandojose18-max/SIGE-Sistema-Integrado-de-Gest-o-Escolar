// SIGE — Sistema Integrado de Gestão Escolar (SaaS Multi-Tenant Moçambique)
// Lógica Principal do Frontend SPA em Português de Moçambique

const state = {
  token: localStorage.getItem('sige_token'),
  refreshToken: localStorage.getItem('sige_refresh_token'),
  user: null,
  tenant: null,
  charts: {},
  geografia: {
    provincias: [],
    distritos: {},
    carreiras: [],
    tiposDocumento: [],
    anotacoes: [],
    comportamentos: []
  },
  alocacoesDocente: [],
  alocacaoAtualId: null
};

// ==================== API FETCH & INTERCEPTADORES ====================
async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  // Se o SuperAdmin selecionou outra escola para inspecionar
  const superAdminEscolaId = localStorage.getItem('sige_selected_tenant');
  if (superAdminEscolaId && state.user?.role === 'SUPERADMIN') {
    headers['X-Tenant-ID'] = superAdminEscolaId;
  }

  try {
    const res = await fetch(endpoint, { ...options, headers });
    const json = await res.json();

    // Interceptador de Assinatura Expirada (HTTP 402 - Payment Required)
    if (res.status === 402) {
      document.getElementById('alertaExpiracaoBanner').style.display = 'flex';
      document.getElementById('alertaExpiracaoMensagem').textContent =
        json.message || 'Assinatura expirada. Regularize o contrato de uso do SIGE.';
      
      if (state.user?.role === 'SUPERADMIN') {
        document.getElementById('btnRenovarRapidoContainer').style.display = 'block';
      }
      return json;
    }

    if (!res.ok) {
      if (res.status === 401) {
        fazerLogout();
      }
      let msg = json.message || 'Erro no processamento da requisição';
      if (json.errors && Array.isArray(json.errors) && json.errors.length > 0) {
        const detalhes = json.errors.map(e => `${e.path?.join('.') || 'Campo'}: ${e.message}`).join(', ');
        msg += ` (${detalhes})`;
      }
      throw new Error(msg);
    }

    return json;
  } catch (err) {
    console.error('API Error:', err);
    throw err;
  }
}

// Download de Ficheiros Binários (Excel XLSX / PDF)
async function downloadFicheiroBinario(url, defaultFilename) {
  try {
    const headers = {};
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    const superAdminEscolaId = localStorage.getItem('sige_selected_tenant');
    if (superAdminEscolaId && state.user?.role === 'SUPERADMIN') {
      headers['X-Tenant-ID'] = superAdminEscolaId;
    }

    const res = await fetch(url, { headers });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.message || 'Falha ao descarregar documento');
    }

    const disposition = res.headers.get('content-disposition');
    let filename = defaultFilename;
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) filename = match[1];
    }

    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(downloadUrl);
  } catch (err) {
    alert(err.message || 'Erro ao descarregar ficheiro');
  }
}

// ==================== INICIALIZAÇÃO DA APLICAÇÃO ====================
document.addEventListener('DOMContentLoaded', async () => {
  await carregarDadosGeografia();

  if (!state.token) {
    mostrarTelaLogin();
  } else {
    try {
      const res = await apiFetch('/api/v1/auth/me');
      if (res.success) {
        state.user = res.data.user;
        state.tenant = res.data.tenant;
        iniciarApp();
      } else {
        mostrarTelaLogin();
      }
    } catch {
      mostrarTelaLogin();
    }
  }

  document.getElementById('loginForm')?.addEventListener('submit', realizarLogin);
});

async function carregarDadosGeografia() {
  try {
    const res = await fetch('/api/v1/geografia');
    const json = await res.json();
    if (json.success) {
      state.geografia = json.data;
    }
  } catch (err) {
    console.warn('Falha ao carregar dados geográficos:', err);
  }
}

function preencherLogin(email, senha) {
  document.getElementById('loginEmail').value = email;
  document.getElementById('loginSenha').value = senha;
}

async function realizarLogin(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value;
  const senha = document.getElementById('loginSenha').value;

  try {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, senha })
    });
    const json = await res.json();

    if (json.success) {
      localStorage.setItem('sige_token', json.data.tokens.accessToken);
      localStorage.setItem('sige_refresh_token', json.data.tokens.refreshToken);
      state.token = json.data.tokens.accessToken;
      state.user = json.data.user;
      state.tenant = json.data.escola;
      iniciarApp();
    } else {
      alert(json.message || 'Falha na autenticação. Verifique o e-mail e a palavra-passe.');
    }
  } catch (err) {
    alert('Erro ao conectar ao servidor do SIGE.');
  }
}

function fazerLogout() {
  localStorage.removeItem('sige_token');
  localStorage.removeItem('sige_refresh_token');
  localStorage.removeItem('sige_selected_tenant');
  state.token = null;
  state.user = null;
  state.tenant = null;
  window.location.reload();
}

function mostrarTelaLogin() {
  document.getElementById('loginView').style.display = 'flex';
  document.getElementById('appView').style.display = 'none';
}

async function iniciarApp() {
  document.getElementById('loginView').style.display = 'none';
  document.getElementById('appView').style.display = 'flex';

  // Cabeçalho e Utilizador Activo
  document.getElementById('topbarUserName').textContent = state.user.nome;
  document.getElementById('topbarUserRole').textContent = state.user.role;
  document.getElementById('dropdownUserEmail').textContent = state.user.email;

  // Formatação do Último Acesso
  if (state.user.ultimo_acesso) {
    const dtAcesso = new Date(state.user.ultimo_acesso);
    const dataFormatada = dtAcesso.toLocaleDateString('pt-PT') + ' às ' + dtAcesso.toLocaleTimeString('pt-PT');
    document.getElementById('topbarUltimoAcesso').textContent = `Último acesso: ${dataFormatada}`;
  } else {
    document.getElementById('topbarUltimoAcesso').textContent = 'Primeiro acesso ao sistema';
  }

  // Configuração por Perfil de Utilizador (RBAC)
  aplicarPermissoesVisualizacao(state.user.role);

  if (state.user.role === 'SUPERADMIN') {
    document.getElementById('superAdminTenantSelectWrapper').style.display = 'block';
    await carregarEscolasSuperAdminSelect();
    navegarPara('saas');
  } else if (state.user.role === 'ALUNO') {
    navegarPara('aluno-perfil');
  } else if (state.user.role === 'PROFESSOR') {
    navegarPara('caderneta');
  } else {
    // ADMIN_ESCOLA, DIRECTOR_ESCOLA, DAP, CHEFE_SECRETARIA
    document.getElementById('btnComprovativoEscola')?.classList.remove('d-none');
    navegarPara('dashboard');
  }

  if (state.tenant) {
    atualizarBadgeTenant(state.tenant);
  }
}

function aplicarPermissoesVisualizacao(role) {
  // Reset geral
  document.querySelectorAll('.saas-only').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.escola-admin-only').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.ped-only').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.fin-only').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.aluno-only').forEach(el => el.style.display = 'none');

  if (role === 'SUPERADMIN') {
    document.querySelectorAll('.saas-only').forEach(el => el.style.display = 'flex');
    document.getElementById('nav-dashboard').style.display = 'flex';
  } else if (role === 'ALUNO') {
    document.querySelectorAll('.aluno-only').forEach(el => el.style.display = 'flex');
    document.getElementById('nav-dashboard').style.display = 'none';
    document.getElementById('nav-impressao').style.display = 'none';
    document.getElementById('sidebarTenantCard').style.display = 'none';
  } else if (role === 'PROFESSOR') {
    document.querySelectorAll('.ped-only').forEach(el => el.style.display = 'flex');
    document.getElementById('nav-dashboard').style.display = 'flex';
    document.getElementById('nav-impressao').style.display = 'flex';
  } else {
    // DIRECTOR_ESCOLA, DAP, CHEFE_SECRETARIA, ADMIN_ESCOLA
    document.querySelectorAll('.escola-admin-only').forEach(el => el.style.display = 'flex');
    document.querySelectorAll('.ped-only').forEach(el => el.style.display = 'flex');
    document.querySelectorAll('.fin-only').forEach(el => el.style.display = 'flex');
    document.getElementById('nav-dashboard').style.display = 'flex';
    document.getElementById('nav-impressao').style.display = 'flex';
  }
}

function atualizarBadgeTenant(tenant) {
  document.getElementById('sidebarEscolaNome').textContent = tenant.nome;
  const badge = document.getElementById('sidebarStatusBadge');
  badge.textContent = tenant.status;
  badge.className = `badge badge-${tenant.status.toLowerCase()} mt-1`;

  const prov = tenant.provincia || 'Maputo';
  document.getElementById('sidebarProvinciaBadge').textContent = prov;

  document.getElementById('headerAnoLetivo').textContent = `Ano Lectivo: ${tenant.ano_letivo_ativo || 2026}`;

  if (tenant.status === 'EXPIRADA') {
    document.getElementById('alertaExpiracaoBanner').style.display = 'flex';
  } else {
    document.getElementById('alertaExpiracaoBanner').style.display = 'none';
  }
}

async function carregarEscolasSuperAdminSelect() {
  try {
    const res = await apiFetch('/api/v1/saas-admin/escolas');
    if (res.success) {
      const select = document.getElementById('superAdminTenantSelect');
      select.innerHTML = '<option value="">(Visão Master SaaS)</option>' +
        res.data.map(e => `<option value="${e.id}">${e.nome} [${e.status}]</option>`).join('');

      const saved = localStorage.getItem('sige_selected_tenant');
      if (saved) select.value = saved;
    }
  } catch (err) {}
}

function alternarEscolaSuperAdmin(escolaId) {
  if (escolaId) {
    localStorage.setItem('sige_selected_tenant', escolaId);
  } else {
    localStorage.removeItem('sige_selected_tenant');
  }
  window.location.reload();
}

// ==================== NAVEGAÇÃO ENTRE MÓDULOS ====================
function navegarPara(viewId) {
  if (state.user?.role === 'ALUNO') {
    if (viewId !== 'aluno-perfil' && viewId !== 'aluno-notas') {
      viewId = 'aluno-perfil';
    }
  }

  document.querySelectorAll('.modulo-view').forEach(el => el.style.display = 'none');
  document.querySelectorAll('#sidebar .nav-link').forEach(el => el.classList.remove('active'));

  const viewEl = document.getElementById(`view-${viewId}`);
  if (viewEl) viewEl.style.display = 'block';

  // Marcar link como ativo
  const link = document.getElementById(`nav-${viewId}`) || Array.from(document.querySelectorAll('#sidebar .nav-link')).find(a =>
    a.getAttribute('onclick')?.includes(viewId)
  );
  if (link) link.classList.add('active');

  const titulos = {
    dashboard: 'Painel Principal & Indicadores Gerais',
    saas: 'Painel de Gestão SaaS SuperAdmin (Tenants & Contratos)',
    escola: 'Dados da Escola & Direcção de Turmas',
    alunos: 'Registo de Alunos & Matrículas Oficiais',
    professores: 'Corpo Docente & Carreiras MINEDH',
    disciplinas: 'Disciplinas & Plano Curricular Nacional',
    caderneta: 'Caderneta de Avaliação Contínua do Professor',
    pautas: 'Pautas de Avaliação & Actas Estatísticas',
    certificados: 'Certificados Digitais com QR Code',
    pagamentos: 'Gestão Financeira, Propinas e Mensalidades',
    impressao: 'Central de Impressão de Documentos Oficiais',
    desbloqueio: 'Autorização de Desbloqueio de Trimestre',
    'aluno-perfil': 'O Meu Perfil Escolar & Filiação',
    'aluno-notas': 'As Minhas Notas & Avaliações',
    'aluno-pagamentos': 'Os Meus Pagamentos de Mensalidades',
    acessos: 'Auditoria de Acessos & Segurança de Dados'
  };
  document.getElementById('pageTitle').textContent = titulos[viewId] || 'SIGE';

  // Gatilhos de carregamento específico
  if (viewId === 'dashboard') carregarDashboardGeral();
  if (viewId === 'saas') carregarPainelSaaS();
  if (viewId === 'escola') carregarEscolaETurmas();
  if (viewId === 'alunos') carregarAlunos();
  if (viewId === 'professores') carregarProfessores();
  if (viewId === 'disciplinas') carregarDisciplinas();
  if (viewId === 'caderneta') carregarCadernetaDocente();
  if (viewId === 'pautas') carregarPautas();
  if (viewId === 'certificados') carregarCertificados();
  if (viewId === 'pagamentos') carregarPagamentos();
  if (viewId === 'impressao') prepararCentralImpressao();
  if (viewId === 'desbloqueio') prepararDesbloqueioTrimestre();
  if (viewId === 'aluno-perfil') carregarAlunoPerfil();
  if (viewId === 'aluno-notas') carregarAlunoNotas();
  if (viewId === 'aluno-pagamentos') carregarAlunoPagamentos();
  if (viewId === 'acessos') carregarLogsAcesso();
}

// ==================== 1. DASHBOARD GERAL ====================
async function carregarDashboardGeral() {
  try {
    const res = await apiFetch('/api/v1/dashboard/overview');
    if (!res.success) return;

    const { escola, indicadores } = res.data;
    document.getElementById('statTotalAlunos').textContent = indicadores.totalAlunos;
    document.getElementById('statAlunosAtivos').textContent = indicadores.alunosAtivos;
    document.getElementById('statTotalProfessores').textContent = indicadores.totalProfessores;
    document.getElementById('statReceitaTotal').textContent = indicadores.totalRecebido.toLocaleString('pt-PT') + ' MZN';
    document.getElementById('statReceitaPendente').textContent = indicadores.totalPendente.toLocaleString('pt-PT') + ' MZN';
    document.getElementById('statDiasRestantes').textContent = escola.diasRestantesAssinatura + ' dias';

    const stBadge = document.getElementById('statStatusAssinatura');
    stBadge.textContent = escola.status;
    stBadge.className = `badge badge-${escola.status.toLowerCase()}`;

    // Gráficos
    const resFin = await apiFetch('/api/v1/pagamentos/stats');
    if (resFin.success) {
      renderizarGraficoDashboardFaturamento(resFin.data.historicoMeses || []);
    }

    const resAlunos = await apiFetch('/api/v1/alunos/stats');
    if (resAlunos.success) {
      renderizarGraficoDashboardGenero(resAlunos.data.genero || { M: 0, F: 0 });
    }
  } catch (err) {}
}

function renderizarGraficoDashboardFaturamento(historico) {
  const ctx = document.getElementById('chartDashboardFaturamento');
  if (!ctx) return;
  if (state.charts.dashboardFaturamento) state.charts.dashboardFaturamento.destroy();

  const labels = historico.map(h => h.mes);
  const recebido = historico.map(h => h.recebido);
  const pendente = historico.map(h => h.pendente);

  state.charts.dashboardFaturamento = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Recebido (MZN)', data: recebido, backgroundColor: '#10b981' },
        { label: 'Pendente (MZN)', data: pendente, backgroundColor: '#ef4444' }
      ]
    },
    options: { responsive: true, plugins: { legend: { position: 'top' } } }
  });
}

function renderizarGraficoDashboardGenero(genero) {
  const ctx = document.getElementById('chartDashboardGenero');
  if (!ctx) return;
  if (state.charts.dashboardGenero) state.charts.dashboardGenero.destroy();

  state.charts.dashboardGenero = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Masculino', 'Feminino'],
      datasets: [{
        data: [genero.M || 0, genero.F || 0],
        backgroundColor: ['#3b82f6', '#ec4899']
      }]
    },
    options: { responsive: true }
  });
}

// ==================== 2. SUPERADMIN SAAS ====================
async function carregarPainelSaaS() {
  try {
    const res = await apiFetch('/api/v1/saas-admin/metrics');
    if (res.success) {
      const d = res.data;
      document.getElementById('saasMRR').textContent = d.mrr.toLocaleString('pt-PT') + ' MZN';
      document.getElementById('saasARR').textContent = d.arr.toLocaleString('pt-PT') + ' MZN';
      document.getElementById('saasChurn').textContent = d.churn + '%';
      document.getElementById('saasTotalEscolas').textContent = d.escolas.total;
      document.getElementById('saasEscolasAtivas').textContent = d.escolas.ativas;
      document.getElementById('saasEscolasExpiradas').textContent = d.escolas.expiradas;
    }

    // Tabela de Escolas
    const resEscolas = await apiFetch('/api/v1/saas-admin/escolas');
    if (resEscolas.success) {
      const tbody = document.getElementById('tabelaSaasEscolas');
      tbody.innerHTML = resEscolas.data.map(e => {
        const ass = e.assinaturas[0];
        const dataFim = ass ? new Date(ass.data_fim).toLocaleDateString('pt-PT') : '-';
        const isAtiva = e.status === 'ATIVA';
        const emblemaIcon = e.usar_emblema_nacional 
          ? '<span class="badge bg-warning text-dark me-1" title="Emblema Nacional">🇲🇿 Emblema</span>' 
          : '';
        const valorContrato = ass?.valor_pago ? `${ass.valor_pago.toLocaleString('pt-PT')} MZN` : `${(e.plano?.preco || 0).toLocaleString('pt-PT')} MZN`;

        return `
          <tr>
            <td>
              <div class="d-flex align-items-center gap-2">
                <div>
                  <strong>${e.nome}</strong> ${emblemaIcon}
                  <br><small class="text-muted">${e.email} | ${e.telefone || '-'}</small>
                </div>
              </div>
            </td>
            <td><small>${e.provincia || '-'}<br><span class="text-muted">${e.distrito || '-'}</span></small></td>
            <td><code>${e.nif_cnpj}</code></td>
            <td>
              <span class="badge bg-light text-dark border">${e.plano?.nome || 'MENSAL'}</span>
              <br><strong class="small text-success">${valorContrato}</strong>
            </td>
            <td><small>${dataFim}</small></td>
            <td><span class="badge badge-${e.status.toLowerCase()}">${e.status}</span></td>
            <td><small>${e._count.alunos} alunos<br>${e._count.professores} profs</small></td>
            <td class="text-end">
              <div class="btn-group btn-group-sm">
                <!-- Botão Toggle Ativar / Desativar -->
                <button class="btn ${isAtiva ? 'btn-outline-danger' : 'btn-outline-success'}" 
                        title="${isAtiva ? 'Desactivar Escola' : 'Activar Escola'}"
                        onclick="toggleStatusEscola('${e.id}', '${e.nome}', '${e.status}')">
                  <i class="bi ${isAtiva ? 'bi-toggle-on text-success' : 'bi-toggle-off text-danger'}"></i>
                  ${isAtiva ? 'Activa' : 'Inactiva'}
                </button>
                <!-- Botão Editar Dados e Prazo -->
                <button class="btn btn-outline-primary" title="Editar Dados & Prazo" onclick="modalEditarEscolaSuperAdmin('${e.id}')">
                  <i class="bi bi-pencil"></i>
                </button>
                <!-- Botão Comprovativo de Contrato -->
                <button class="btn btn-outline-secondary" title="Comprovativo de Contrato" onclick="verComprovativoContrato('${e.id}')">
                  <i class="bi bi-file-earmark-text"></i>
                </button>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }

    // Tabela de Preços dos Planos
    const resPlanos = await apiFetch('/api/v1/saas-admin/planos');
    if (resPlanos.success) {
      const tbodyPlanos = document.getElementById('tabelaSaasPlanos');
      tbodyPlanos.innerHTML = resPlanos.data.map(p => `
        <tr>
          <td><strong>${p.nome}</strong></td>
          <td>${p.duracao_dias} dias</td>
          <td><strong class="text-primary fs-6">${p.preco.toLocaleString('pt-PT')} MZN</strong></td>
          <td><small class="text-muted">${p.descricao || 'Plano de subscrição SIGE'}</small></td>
          <td class="text-end">
            <button class="btn btn-outline-primary btn-sm" onclick="modalEditarPrecoPlano('${p.id}', '${p.nome}', ${p.preco})">
              <i class="bi bi-currency-exchange me-1"></i> Alterar Preço
            </button>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

async function toggleStatusEscola(escolaId, nome, statusAtual) {
  const proximo = statusAtual === 'ATIVA' ? 'SUSPENSA' : 'ATIVA';
  if (!confirm(`Confirma a alteração de estado da escola [${nome}] para ${proximo}?`)) return;

  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/toggle-status`, {
      method: 'PATCH'
    });
    if (res.success) {
      alert(res.message);
      carregarPainelSaaS();
    }
  } catch (err) {
    alert('Erro ao alterar estado da escola.');
  }
}

async function modalCadastrarEscolaSuperAdmin() {
  const planosRes = await apiFetch('/api/v1/saas-admin/planos');
  const optPlanos = (planosRes.data || []).map(p => 
    `<option value="${p.id}">${p.nome} (${p.duracao_dias} dias) — ${p.preco.toLocaleString('pt-PT')} MZN</option>`
  ).join('');

  const optProvincias = (state.geografia.provincias || []).map(p => `<option value="${p}">${p}</option>`).join('');

  abrirModal('Cadastrar Nova Escola no SIGE', `
    <form id="formModalCadastrarEscola">
      <div class="row g-3">
        <div class="col-md-7">
          <label class="form-label small fw-semibold">Nome da Instituição</label>
          <input type="text" id="cadEscolaNome" class="form-control" required placeholder="Ex: Escola Secundária Josina Machel">
        </div>
        <div class="col-md-5">
          <label class="form-label small fw-semibold">NUIT da Escola</label>
          <input type="text" id="cadEscolaNUIT" class="form-control" required placeholder="Ex: 400123456">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">E-mail Administrativo</label>
          <input type="email" id="cadEscolaEmail" class="form-control" required placeholder="secretaria@escola.edu.mz">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Telefone (+258 Padrão)</label>
          <input type="text" id="cadEscolaTelefone" class="form-control" value="+258 " required>
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Província</label>
          <select id="cadEscolaProvincia" class="form-select" onchange="atualizarDistritosCadastroEscola(this.value)" required>
            <option value="">Selecione a Província</option>
            ${optProvincias}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Distrito</label>
          <select id="cadEscolaDistrito" class="form-select" required>
            <option value="">Selecione primeiro a província</option>
          </select>
        </div>

        <div class="col-md-7">
          <label class="form-label small fw-semibold">Plano de Subscrição Inicial</label>
          <select id="cadEscolaPlano" class="form-select" required>${optPlanos}</select>
        </div>
        <div class="col-md-5">
          <label class="form-label small fw-semibold">Valor do Contrato (MZN)</label>
          <input type="number" id="cadEscolaValor" class="form-control" placeholder="Valor acordado em MZN">
        </div>

        <div class="col-md-4">
          <label class="form-label small fw-semibold">Nome do Director / Admin (Opcional)</label>
          <input type="text" id="cadEscolaAdminNome" class="form-control" placeholder="Director(a) da Escola">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">E-mail do Director / Admin (Opcional)</label>
          <input type="email" id="cadEscolaAdminEmail" class="form-control" placeholder="director@escola.edu.mz">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Senha de Acesso (Opcional)</label>
          <input type="password" id="cadEscolaAdminSenha" class="form-control" placeholder="123456 (Padrão)">
        </div>

        <div class="col-12">
          <div class="form-check">
            <input class="form-check-input" type="checkbox" id="cadEscolaEmblema" checked>
            <label class="form-check-label small fw-semibold" for="cadEscolaEmblema">
              Utilizar Emblema Oficial nos documentos e pautas
            </label>
          </div>
        </div>

        <div class="col-12">
          <label class="form-label small fw-semibold">URL do Logótipo Próprio da Escola (Opcional)</label>
          <input type="url" id="cadEscolaLogo" class="form-control" placeholder="https://escola.edu.mz/logo.png">
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4">Concluir Cadastro da Escola</button>
    </form>
  `);

  document.getElementById('formModalCadastrarEscola').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const body = {
        nome: document.getElementById('cadEscolaNome').value,
        nif_cnpj: document.getElementById('cadEscolaNUIT').value,
        email: document.getElementById('cadEscolaEmail').value,
        telefone: document.getElementById('cadEscolaTelefone').value,
        provincia: document.getElementById('cadEscolaProvincia').value,
        distrito: document.getElementById('cadEscolaDistrito').value,
        plano_id: document.getElementById('cadEscolaPlano').value,
        valor_contrato: Number(document.getElementById('cadEscolaValor').value) || undefined,
        adminNome: document.getElementById('cadEscolaAdminNome')?.value || undefined,
        adminEmail: document.getElementById('cadEscolaAdminEmail')?.value || undefined,
        adminSenha: document.getElementById('cadEscolaAdminSenha')?.value || undefined,
        usar_emblema_nacional: document.getElementById('cadEscolaEmblema').checked,
        logo_url: document.getElementById('cadEscolaLogo').value || undefined
      };

      const res = await apiFetch('/api/v1/saas-admin/escolas', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success) {
        alert('Escola cadastrada com sucesso no SIGE!');
        fecharModal();
        carregarPainelSaaS();
      }
    } catch (err) {
      alert(err.message || 'Erro ao cadastrar escola');
    }
  });
}

function atualizarDistritosCadastroEscola(provincia) {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('cadEscolaDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => `<option value="${d}">${d}</option>`).join('');
  }
}

async function modalEditarEscolaSuperAdmin(escolaId) {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas`);
    const escola = res.data.find(e => e.id === escolaId);
    if (!escola) return alert('Escola não encontrada');

    const ass = escola.assinaturas[0];
    const dataFimStr = ass ? new Date(ass.data_fim).toISOString().split('T')[0] : '';
    const optProvincias = (state.geografia.provincias || []).map(p => 
      `<option value="${p}" ${p === escola.provincia ? 'selected' : ''}>${p}</option>`
    ).join('');

    abrirModal(`Editar Escola: ${escola.nome}`, `
      <form id="formModalEditarEscola">
        <div class="row g-3">
          <div class="col-md-7">
            <label class="form-label small fw-semibold">Nome da Instituição</label>
            <input type="text" id="editEscolaNome" class="form-control" value="${escola.nome}" required>
          </div>
          <div class="col-md-5">
            <label class="form-label small fw-semibold">NUIT</label>
            <input type="text" id="editEscolaNUIT" class="form-control" value="${escola.nif_cnpj}" required>
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">E-mail</label>
            <input type="email" id="editEscolaEmail" class="form-control" value="${escola.email}" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Telefone</label>
            <input type="text" id="editEscolaTelefone" class="form-control" value="${escola.telefone || '+258 '}">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Data de Vencimento do Contrato</label>
            <input type="date" id="editEscolaDataFim" class="form-control" value="${dataFimStr}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Estender Prazo (Dias Adicionais)</label>
            <input type="number" id="editEscolaDiasAdicionais" class="form-control" placeholder="Ex: 30" min="0">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Província</label>
            <select id="editEscolaProvincia" class="form-select" onchange="atualizarDistritosEdicaoEscola(this.value)">
              ${optProvincias}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Distrito</label>
            <select id="editEscolaDistrito" class="form-select"></select>
          </div>

          <div class="col-12">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" id="editEscolaEmblema" ${escola.usar_emblema_nacional ? 'checked' : ''}>
              <label class="form-check-label small fw-semibold" for="editEscolaEmblema">
                Utilizar Emblema Oficial
              </label>
            </div>
          </div>
        </div>
        <button type="submit" class="btn btn-primary w-100 mt-4">Actualizar Dados e Prazo</button>
      </form>
    `);

    atualizarDistritosEdicaoEscola(escola.provincia || 'Maputo Cidade', escola.distrito);

    document.getElementById('formModalEditarEscola').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const body = {
          nome: document.getElementById('editEscolaNome').value,
          nif_cnpj: document.getElementById('editEscolaNUIT').value,
          email: document.getElementById('editEscolaEmail').value,
          telefone: document.getElementById('editEscolaTelefone').value,
          data_fim: document.getElementById('editEscolaDataFim').value || undefined,
          data_fim_assinatura: document.getElementById('editEscolaDataFim').value || undefined,
          dias_adicionais: Number(document.getElementById('editEscolaDiasAdicionais').value) || undefined,
          provincia: document.getElementById('editEscolaProvincia').value,
          distrito: document.getElementById('editEscolaDistrito').value,
          usar_emblema_nacional: document.getElementById('editEscolaEmblema').checked
        };

        const updRes = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}`, {
          method: 'PUT',
          body: JSON.stringify(body)
        });
        if (updRes.success) {
          alert('Dados da escola e prazo de contrato actualizados com sucesso!');
          fecharModal();
          carregarPainelSaaS();
        }
      } catch (err) {
        alert(err.message || 'Erro ao actualizar dados');
      }
    });
  } catch (err) {}
}

function atualizarDistritosEdicaoEscola(provincia, distritoSelecionado = '') {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('editEscolaDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => 
      `<option value="${d}" ${d === distritoSelecionado ? 'selected' : ''}>${d}</option>`
    ).join('');
  }
}

function modalEditarPrecoPlano(planoId, nome, precoAtual) {
  abrirModal(`Alterar Preço do Plano: ${nome}`, `
    <form id="formModalPrecoPlano">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Novo Valor do Contrato em Meticais (MZN)</label>
        <div class="input-group">
          <input type="number" step="100" id="mppValor" class="form-control" value="${precoAtual}" required>
          <span class="input-group-text fw-bold">MZN</span>
        </div>
        <small class="text-muted">Este novo valor será aplicado para todas as novas adesões e renovações deste plano.</small>
      </div>
      <button type="submit" class="btn btn-primary w-100">Guardar Novo Preço</button>
    </form>
  `);

  document.getElementById('formModalPrecoPlano').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const preco = Number(document.getElementById('mppValor').value);
      const res = await apiFetch(`/api/v1/saas-admin/planos/${planoId}/preco`, {
        method: 'PUT',
        body: JSON.stringify({ preco })
      });
      if (res.success) {
        alert('Preço do plano atualizado com sucesso!');
        fecharModal();
        carregarPainelSaaS();
      }
    } catch (err) {
      alert(err.message || 'Erro ao alterar preço');
    }
  });
}

async function verComprovativoContrato(escolaId) {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/comprovativo-contrato`);
    if (res.success) {
      exibirComprovativoContratoModal(res.data);
    }
  } catch (err) {
    alert('Erro ao carregar comprovativo de contrato');
  }
}

async function baixarComprovativoMinhaEscola() {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/minha-escola/comprovativo-contrato`);
    if (res.success) {
      exibirComprovativoContratoModal(res.data);
    }
  } catch (err) {
    alert('Erro ao carregar comprovativo');
  }
}

function exibirComprovativoContratoModal(c) {
  abrirModal('Comprovativo Oficial de Contrato e Adesão ao SIGE', `
    <div class="printable-document p-4 bg-white border rounded">
      <div class="text-center border-bottom pb-3 mb-4">
        <h5 class="fw-bold mb-1">SISTEMA INTEGRADO DE GESTÃO ESCOLAR</h5>
        <h6 class="fw-semibold text-primary mb-1">SIGE — Gestão Integrada Escolar (SaaS)</h6>
        <p class="text-muted small mb-0">Comprovativo de Regularização de Licença e Adesão Institucional</p>
      </div>

      <div class="row g-2 mb-4 small">
        <div class="col-6"><strong>Instituição Contratante:</strong> ${c.escola.nome}</div>
        <div class="col-6"><strong>NUIT:</strong> ${c.escola.nif_cnpj}</div>
        <div class="col-6"><strong>Localização:</strong> ${c.escola.distrito || '-'}, ${c.escola.provincia || '-'}</div>
        <div class="col-6"><strong>E-mail:</strong> ${c.escola.email}</div>
      </div>

      <table class="table table-bordered table-sm mb-4 small">
        <thead class="table-light">
          <tr>
            <th>Plano Contratado</th>
            <th>Data de Início</th>
            <th>Data de Término (Validade)</th>
            <th>Valor Pago / Contrato</th>
            <th>Estado da Licença</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>${c.plano.nome}</strong></td>
            <td>${new Date(c.assinatura.data_inicio).toLocaleDateString('pt-PT')}</td>
            <td><strong>${new Date(c.assinatura.data_fim).toLocaleDateString('pt-PT')}</strong></td>
            <td class="text-success fw-bold">${(c.assinatura.valor_pago || c.plano.preco).toLocaleString('pt-PT')} MZN</td>
            <td><span class="badge badge-ativa">${c.escola.status}</span></td>
          </tr>
        </tbody>
      </table>

      <div class="alert alert-light border small text-muted mb-4">
        <i class="bi bi-shield-check text-success me-1"></i>
        Declara-se para os devidos efeitos que a referida instituição possui licença ativa para processamento oficial de Pautas, Boletins, Cadernetas e Certificados Digitais com autenticação QR Code.
      </div>

      <div class="d-flex justify-content-between text-center pt-4 border-top small">
        <div>
          <p class="mb-0 border-top pt-2 px-3">SuperAdmin SIGE — Direcção de Tecnologia</p>
        </div>
        <div>
          <p class="mb-0 border-top pt-2 px-3">O Representante da Instituição de Ensino</p>
        </div>
      </div>

      <div class="text-center mt-4 no-print">
        <button class="btn btn-primary" onclick="window.print()"><i class="bi bi-printer me-1"></i> Imprimir Comprovativo</button>
      </div>
    </div>
  `);
}

async function executarCronVerificacaoManual() {
  try {
    const res = await apiFetch('/api/v1/saas-admin/verificar-expiracoes', { method: 'POST' });
    if (res.success) {
      alert(`Verificação de expiração executada!\nProcessadas: ${res.data.processadas}\nExpiradas: ${res.data.expiradas}`);
      carregarPainelSaaS();
    }
  } catch (err) {
    alert('Erro ao executar verificação.');
  }
}

// ==================== 3. ESCOLA & TURMAS ====================
async function carregarEscolaETurmas() {
  try {
    const resInfo = await apiFetch('/api/v1/escola-admin/info');
    if (resInfo.success) {
      const e = resInfo.data;
      document.getElementById('confEscolaNome').value = e.nome;
      document.getElementById('confEscolaAnoLetivo').value = e.ano_letivo_ativo;
      document.getElementById('confEscolaTrimestreAtivo').value = e.trimestre_ativo || '1_TRIMESTRE';
      document.getElementById('confEscolaTelefone').value = e.telefone || '';
      document.getElementById('confEscolaEmail').value = e.email;
      document.getElementById('confEscolaDirector').value = e.director_nome || '';
      document.getElementById('confEscolaDAP').value = e.dap_nome || '';
      document.getElementById('confEscolaChefeSec').value = e.chefe_secretaria_nome || '';
      document.getElementById('confEscolaEmblema').checked = !!e.usar_emblema_nacional;

      // Províncias
      const selectProv = document.getElementById('confEscolaProvincia');
      selectProv.innerHTML = (state.geografia.provincias || []).map(p => 
        `<option value="${p}" ${p === e.provincia ? 'selected' : ''}>${p}</option>`
      ).join('');
      atualizarDistritosEscola(e.provincia || 'Maputo Cidade', e.distrito);
    }

    const resTurmas = await apiFetch('/api/v1/escola-admin/turmas');
    if (resTurmas.success) {
      const tbody = document.getElementById('tabelaTurmas');
      tbody.innerHTML = resTurmas.data.map(t => `
        <tr>
          <td><strong>${t.nome}</strong></td>
          <td><span class="badge bg-light text-dark border">${t.grau_ano}</span></td>
          <td>${t.turno}</td>
          <td><small>${t.director_turma?.nome || '<span class="text-muted">Não definido</span>'}</small></td>
          <td><small>${t.director_classe?.nome || '<span class="text-muted">Não definido</span>'}</small></td>
          <td><span class="badge bg-primary">${t._count.alunos} alunos</span></td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

function atualizarDistritosEscola(provincia, distritoSelecionado = '') {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('confEscolaDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => 
      `<option value="${d}" ${d === distritoSelecionado ? 'selected' : ''}>${d}</option>`
    ).join('');
  }
}

document.getElementById('formEscolaInfo')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const body = {
      nome: document.getElementById('confEscolaNome').value,
      ano_letivo_ativo: document.getElementById('confEscolaAnoLetivo').value,
      trimestre_ativo: document.getElementById('confEscolaTrimestreAtivo').value,
      telefone: document.getElementById('confEscolaTelefone').value,
      email: document.getElementById('confEscolaEmail').value,
      director_nome: document.getElementById('confEscolaDirector').value,
      dap_nome: document.getElementById('confEscolaDAP').value,
      chefe_secretaria_nome: document.getElementById('confEscolaChefeSec').value,
      provincia: document.getElementById('confEscolaProvincia').value,
      distrito: document.getElementById('confEscolaDistrito').value,
      usar_emblema_nacional: document.getElementById('confEscolaEmblema').checked
    };
    const res = await apiFetch('/api/v1/escola-admin/info', {
      method: 'PUT',
      body: JSON.stringify(body)
    });
    if (res.success) alert('Configurações da escola salvas com sucesso!');
  } catch (err) {
    alert('Erro ao actualizar dados da escola');
  }
});

async function modalCriarTurma() {
  const profsRes = await apiFetch('/api/v1/professores');
  const optProfs = '<option value="">(Nenhum seleccionado)</option>' + 
    (profsRes.data || []).map(p => `<option value="${p.id}">${p.nome}</option>`).join('');

  abrirModal('Cadastrar Nova Turma Oficial', `
    <form id="formModalTurma">
      <div class="row g-3">
        <div class="col-md-7">
          <label class="form-label small fw-semibold">Nome da Turma</label>
          <input type="text" id="mtNome" class="form-control" required placeholder="Ex: 10ª Classe Turma A">
        </div>
        <div class="col-md-5">
          <label class="form-label small fw-semibold">Classe / Grau</label>
          <select id="mtGrau" class="form-select" required>
            <option value="8ª Classe">8ª Classe</option>
            <option value="9ª Classe">9ª Classe</option>
            <option value="10ª Classe">10ª Classe</option>
            <option value="11ª Classe">11ª Classe</option>
            <option value="12ª Classe">12ª Classe</option>
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Turno</label>
          <select id="mtTurno" class="form-select">
            <option value="MANHA">Manhã</option>
            <option value="TARDE">Tarde</option>
            <option value="NOITE">Noite</option>
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Sala de Aula</label>
          <input type="text" id="mtSala" class="form-control" placeholder="Ex: Sala 04">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Director de Turma</label>
          <select id="mtDirTurma" class="form-select">${optProfs}</select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Director de Classe</label>
          <select id="mtDirClasse" class="form-select">${optProfs}</select>
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4">Criar Turma</button>
    </form>
  `);

  document.getElementById('formModalTurma').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/escola-admin/turmas', {
        method: 'POST',
        body: JSON.stringify({
          nome: document.getElementById('mtNome').value,
          grau_ano: document.getElementById('mtGrau').value,
          turno: document.getElementById('mtTurno').value,
          sala: document.getElementById('mtSala').value,
          director_turma_id: document.getElementById('mtDirTurma').value || null,
          director_classe_id: document.getElementById('mtDirClasse').value || null
        })
      });
      if (res.success) {
        fecharModal();
        carregarEscolaETurmas();
      }
    } catch (err) {
      alert('Erro ao criar turma');
    }
  });
}

// ==================== 4. ALUNOS ====================
async function carregarAlunos() {
  try {
    const [resAlunos, resStats] = await Promise.all([
      apiFetch('/api/v1/alunos'),
      apiFetch('/api/v1/alunos/stats')
    ]);

    if (resStats.success) {
      const s = resStats.data;
      document.getElementById('alunoTotalCard').textContent = s.totalGeral;
      document.getElementById('alunoRetencaoCard').textContent = s.taxaRetencao + '%';
      document.getElementById('alunoEvasaoCard').textContent = s.taxaEvasao + '%';
      document.getElementById('alunoGeneroRatioCard').textContent = `${s.genero.M} M / ${s.genero.F} F`;
    }

    if (resAlunos.success) {
      const tbody = document.getElementById('tabelaAlunos');
      tbody.innerHTML = resAlunos.data.map(a => `
        <tr>
          <td><code>${a.matricula}</code></td>
          <td><strong>${a.nome}</strong></td>
          <td>${a.turma ? a.turma.nome : '<span class="text-muted">Sem Turma</span>'}</td>
          <td><small>${a.tipo_documento || 'BI'}: ${a.numero_documento || '-'}</small></td>
          <td><small>${a.distrito || '-'}<br><span class="text-muted">${a.provincia || '-'}</span></small></td>
          <td><small>Pai: ${a.pai || '-'}<br>Mãe: ${a.mae || '-'}</small></td>
          <td><span class="badge bg-success">${a.status}</span></td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-danger" onclick="excluirAluno('${a.id}')"><i class="bi bi-trash"></i></button>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

async function excluirAluno(id) {
  if (!confirm('Deseja realmente eliminar o registo deste aluno?')) return;
  try {
    const res = await apiFetch(`/api/v1/alunos/${id}`, { method: 'DELETE' });
    if (res.success) carregarAlunos();
  } catch (err) {
    alert('Erro ao eliminar aluno');
  }
}

async function modalNovoAluno() {
  const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
  const opcoesTurmas = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`).join('');
  const optProvincias = (state.geografia.provincias || []).map(p => `<option value="${p}">${p}</option>`).join('');

  abrirModal('Matricular Novo Aluno', `
    <form id="formModalAluno">
      <div class="row g-3">
        <div class="col-md-8">
          <label class="form-label small fw-semibold">Nome Completo</label>
          <input type="text" id="maNome" class="form-control" required placeholder="Nome próprio e do meio">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Apelido</label>
          <input type="text" id="maApelido" class="form-control" placeholder="Sobrenome / Apelido">
        </div>

        <div class="col-md-4">
          <label class="form-label small fw-semibold">Data de Nascimento</label>
          <input type="date" id="maNasc" class="form-control" required>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Género</label>
          <select id="maGenero" class="form-select">
            <option value="M">Masculino</option>
            <option value="F">Feminino</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Turma de Ingresso</label>
          <select id="maTurma" class="form-select">
            <option value="">Selecione a turma</option>
            ${opcoesTurmas}
          </select>
        </div>

        <div class="col-md-4">
          <label class="form-label small fw-semibold">Tipo de Documento</label>
          <select id="maTipoDoc" class="form-select">
            <option value="BI">Bilhete de Identidade (BI)</option>
            <option value="DIRE">DIRE</option>
            <option value="PASSAPORTE">Passaporte</option>
            <option value="CEDULA">Cédula Pessoal</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Número do Documento</label>
          <input type="text" id="maNumDoc" class="form-control" placeholder="Ex: 110100234567M">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">NUIT</label>
          <input type="text" id="maNUIT" class="form-control" placeholder="Ex: 109876543">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Província de Naturalidade / Residência</label>
          <select id="maProvincia" class="form-select" onchange="atualizarDistritosAluno(this.value)">
            <option value="">Selecione a Província</option>
            ${optProvincias}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Distrito</label>
          <select id="maDistrito" class="form-select">
            <option value="">Selecione primeiro a província</option>
          </select>
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Nome do Pai (Opcional)</label>
          <input type="text" id="maPai" class="form-control" placeholder="Nome completo do pai">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Nome da Mãe (Opcional)</label>
          <input type="text" id="maMae" class="form-control" placeholder="Nome completo da mãe">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Encarregado de Educação / Tutor</label>
          <input type="text" id="maResp" class="form-control" placeholder="Nome do encarregado de educação">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Telefone de Contacto (+258 Padrão)</label>
          <input type="text" id="maTel" class="form-control" value="+258 ">
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4">Confirmar Matrícula Oficial</button>
    </form>
  `);

  document.getElementById('formModalAluno').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const body = {
        nome: document.getElementById('maNome').value,
        apelido: document.getElementById('maApelido').value || undefined,
        data_nascimento: document.getElementById('maNasc').value,
        genero: document.getElementById('maGenero').value,
        turma_id: document.getElementById('maTurma').value || null,
        tipo_documento: document.getElementById('maTipoDoc').value,
        numero_documento: document.getElementById('maNumDoc').value || undefined,
        nuit: document.getElementById('maNUIT').value || undefined,
        provincia: document.getElementById('maProvincia').value || undefined,
        distrito: document.getElementById('maDistrito').value || undefined,
        pai: document.getElementById('maPai').value || undefined,
        mae: document.getElementById('maMae').value || undefined,
        nome_responsavel: document.getElementById('maResp').value || undefined,
        contato_responsavel: document.getElementById('maTel').value || undefined
      };
      const res = await apiFetch('/api/v1/alunos', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success) {
        fecharModal();
        carregarAlunos();
      }
    } catch (err) {
      alert(err.message || 'Erro ao matricular aluno');
    }
  });
}

function atualizarDistritosAluno(provincia) {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('maDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => `<option value="${d}">${d}</option>`).join('');
  }
}

// ==================== 5. PROFESSORES ====================
async function carregarProfessores() {
  try {
    const [resProfs, resStats] = await Promise.all([
      apiFetch('/api/v1/professores'),
      apiFetch('/api/v1/professores/stats')
    ]);

    if (resStats.success) {
      const s = resStats.data;
      document.getElementById('profTotalCard').textContent = s.totalProfessores;
      document.getElementById('profRatioCard').textContent = `${s.proporcaoAlunoProfessor} : 1`;
      document.getElementById('profAulasMesCard').textContent = s.totalAulasMes;
    }

    if (resProfs.success) {
      const tbody = document.getElementById('tabelaProfessores');
      tbody.innerHTML = resProfs.data.map(p => `
        <tr>
          <td><strong>${p.nome}</strong></td>
          <td><small>${p.email}<br>${p.telefone || '-'}</small></td>
          <td><span class="badge bg-light text-dark border">${p.carreira || 'Licenciado'}</span></td>
          <td><small>${p.distrito || '-'}<br><span class="text-muted">${p.provincia || '-'}</span></small></td>
          <td>${p.carga_horaria_semanal}h / semana</td>
          <td>
            ${p.alocacoes.map(a => `<span class="badge bg-primary-subtle text-primary border">${a.disciplina.nome} (${a.turma.nome})</span>`).join(' ')}
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

async function modalNovoProfessor() {
  const optCarreiras = (state.geografia.carreiras || []).map(c => `<option value="${c}">${c}</option>`).join('');
  const optProvincias = (state.geografia.provincias || []).map(p => `<option value="${p}">${p}</option>`).join('');

  abrirModal('Cadastrar Docente', `
    <form id="formModalProf">
      <div class="row g-3">
        <div class="col-md-7">
          <label class="form-label small fw-semibold">Nome Completo</label>
          <input type="text" id="mpNome" class="form-control" required placeholder="Prof. Nome Próprio">
        </div>
        <div class="col-md-5">
          <label class="form-label small fw-semibold">Apelido</label>
          <input type="text" id="mpApelido" class="form-control" placeholder="Apelido do docente">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">E-mail Institucional</label>
          <input type="email" id="mpEmail" class="form-control" required placeholder="professor@escola.edu.mz">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Telefone (+258 Padrão)</label>
          <input type="text" id="mpTel" class="form-control" value="+258 ">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Carreira Docente (Quadro Oficial)</label>
          <select id="mpCarreira" class="form-select">${optCarreiras}</select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Especialidade / Área de Formação</label>
          <input type="text" id="mpEsp" class="form-control" placeholder="Ex: Matemática e Física">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Província</label>
          <select id="mpProvincia" class="form-select" onchange="atualizarDistritosProfessor(this.value)">
            <option value="">Selecione a Província</option>
            ${optProvincias}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Distrito</label>
          <select id="mpDistrito" class="form-select">
            <option value="">Selecione primeiro a província</option>
          </select>
        </div>

        <div class="col-12">
          <label class="form-label small fw-semibold">Carga Horária Semanal (Horas)</label>
          <input type="number" id="mpCarga" class="form-control" value="20" required>
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4">Cadastrar Docente</button>
    </form>
  `);

  document.getElementById('formModalProf').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const body = {
        nome: document.getElementById('mpNome').value,
        apelido: document.getElementById('mpApelido').value || undefined,
        email: document.getElementById('mpEmail').value,
        telefone: document.getElementById('mpTel').value || undefined,
        carreira: document.getElementById('mpCarreira').value,
        especialidade: document.getElementById('mpEsp').value || undefined,
        provincia: document.getElementById('mpProvincia').value || undefined,
        distrito: document.getElementById('mpDistrito').value || undefined,
        carga_horaria_semanal: Number(document.getElementById('mpCarga').value)
      };
      const res = await apiFetch('/api/v1/professores', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success) {
        fecharModal();
        carregarProfessores();
      }
    } catch (err) {
      alert('Erro ao cadastrar docente');
    }
  });
}

function atualizarDistritosProfessor(provincia) {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('mpDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => `<option value="${d}">${d}</option>`).join('');
  }
}

async function modalAlocarProfessor() {
  const [profsRes, turmasRes, discRes] = await Promise.all([
    apiFetch('/api/v1/professores'),
    apiFetch('/api/v1/escola-admin/turmas'),
    apiFetch('/api/v1/disciplinas')
  ]);

  const optProfs = (profsRes.data || []).map(p => `<option value="${p.id}">${p.nome}</option>`).join('');
  const optTurmas = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome}</option>`).join('');
  const optDisc = (discRes.data || []).map(d => `<option value="${d.id}">${d.nome}</option>`).join('');

  abrirModal('Alocar Professor a Turma e Disciplina', `
    <form id="formModalAloc">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Professor</label>
        <select id="malocProf" class="form-select" required>${optProfs}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Turma</label>
        <select id="malocTurma" class="form-select" required>${optTurmas}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Disciplina</label>
        <select id="malocDisc" class="form-select" required>${optDisc}</select>
      </div>
      <button type="submit" class="btn btn-primary w-100">Confirmar Alocação</button>
    </form>
  `);

  document.getElementById('formModalAloc').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/professores/alocar', {
        method: 'POST',
        body: JSON.stringify({
          professor_id: document.getElementById('malocProf').value,
          turma_id: document.getElementById('malocTurma').value,
          disciplina_id: document.getElementById('malocDisc').value
        })
      });
      if (res.success) {
        fecharModal();
        carregarProfessores();
      }
    } catch (err) {
      alert('Erro ao alocar professor');
    }
  });
}

// ==================== 6. DISCIPLINAS ====================
async function carregarDisciplinas() {
  try {
    const [resD, resStats] = await Promise.all([
      apiFetch('/api/v1/disciplinas'),
      apiFetch('/api/v1/disciplinas/stats')
    ]);

    if (resD.success) {
      const tbody = document.getElementById('tabelaDisciplinas');
      tbody.innerHTML = resD.data.map(d => `
        <tr>
          <td><code>${d.codigo}</code></td>
          <td><strong>${d.nome}</strong></td>
          <td>${d.carga_horaria} horas</td>
          <td>${d.ano_letivo}</td>
        </tr>
      `).join('');
    }

    if (resStats.success) {
      renderizarGraficoReprovacao(resStats.data.rankingReprovacao || []);
    }
  } catch (err) {}
}

function renderizarGraficoReprovacao(ranking) {
  const ctx = document.getElementById('chartDisciplinasReprovacao');
  if (!ctx) return;
  if (state.charts.reprovacao) state.charts.reprovacao.destroy();

  const labels = ranking.map(r => r.nome);
  const data = ranking.map(r => r.taxaReprovacao);

  state.charts.reprovacao = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: '% Negativas',
        data,
        backgroundColor: '#dc2626'
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: { legend: { display: false } }
    }
  });
}

function modalNovaDisciplina() {
  abrirModal('Nova Disciplina Curricular', `
    <form id="formModalDisc">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nome da Disciplina</label>
        <input type="text" id="mdNome" class="form-control" required placeholder="Ex: Matemática">
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Código Curricular</label>
        <input type="text" id="mdCodigo" class="form-control" required placeholder="Ex: MAT-10">
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Carga Horária (Horas/Ano)</label>
        <input type="number" id="mdCarga" class="form-control" value="60" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Criar Disciplina</button>
    </form>
  `);

  document.getElementById('formModalDisc').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const body = {
        nome: document.getElementById('mdNome').value,
        codigo: document.getElementById('mdCodigo').value,
        carga_horaria: Number(document.getElementById('mdCarga').value)
      };
      const res = await apiFetch('/api/v1/disciplinas', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success) {
        fecharModal();
        carregarDisciplinas();
      }
    } catch (err) {
      alert('Erro ao criar disciplina');
    }
  });
}

// ==================== 7. CADERNETA DO PROFESSOR (6 AVALIAÇÕES) ====================
// ==================== 7. CADERNETA DO PROFESSOR (3 TRIMESTRES E ESTATÍSTICA POR COLUNA) ====================
async function carregarCadernetaDocente() {
  try {
    const selectAloc = document.getElementById('cadernetaAlocacaoSelect');
    if (!selectAloc) return;

    // Se ainda não carregou alocações
    if (state.alocacoesDocente.length === 0) {
      const resTurmas = await apiFetch('/api/v1/professores/minhas-turmas');
      if (resTurmas.success && resTurmas.data.length > 0) {
        state.alocacoesDocente = resTurmas.data;
        selectAloc.innerHTML = resTurmas.data.map(a => 
          `<option value="${a.id}">${a.disciplina.nome} — ${a.turma.nome} (${a.turma.grau_ano})</option>`
        ).join('');
      } else {
        selectAloc.innerHTML = '<option value="">Nenhuma turma ou disciplina alocada</option>';
        return;
      }
    }

    const alocacaoId = selectAloc.value;
    if (!alocacaoId) return;
    state.alocacaoAtualId = alocacaoId;

    const resCaderneta = await apiFetch(`/api/v1/professores/caderneta/${alocacaoId}/completa`);
    if (!resCaderneta.success) return;
    const d = resCaderneta.data;

    // Preencher Caixas de Cabeçalho Institucional Oficial (Imagem 2)
    if (document.getElementById('cadHeaderEscola')) {
      document.getElementById('cadHeaderEscola').textContent = (d.escola?.nome || 'Escola Secundária').toUpperCase();
      document.getElementById('cadHeaderSub').textContent = `PROVÍNCIA DE ${d.escola?.provincia || 'MAPUTO'} | DISTRITO DE ${d.escola?.distrito || 'CIDADE DE MAPUTO'}`.toUpperCase();
      document.getElementById('cadHeaderAno').textContent = d.turma?.ano_letivo || '2026';

      document.getElementById('cadBoxDisciplina').textContent = `${d.disciplina?.nome || '-'} (${d.disciplina?.codigo || '-'})`;
      document.getElementById('cadBoxProfessor').textContent = `${d.professor?.nome || '-'} ${d.professor?.apelido || ''}`.trim();
      document.getElementById('cadBoxContacto').textContent = d.professor?.telefone || '-';
      document.getElementById('cadBoxArea').textContent = d.professor?.especialidade || 'Ensino Geral';
      document.getElementById('cadBoxTurmaDirector').textContent = `${d.turma?.nome || '-'} | Dir: ${d.directorTurma ? d.directorTurma.nome : '-'}`;
      document.getElementById('cadBoxClasseTurno').textContent = `${d.turma?.grau_ano || '-'} | ${d.turma?.turno || 'Diurno'}`;
      document.getElementById('cadBoxEfectivo').textContent = `H: ${d.efectivo?.h || 0} | M: ${d.efectivo?.m || 0} | Total: ${d.efectivo?.total || 0}`;
    }

    // Preencher Tabela de Alunos com todos os 3 Trimestres (Imagem 2)
    const tbody = document.getElementById('tabelaCadernetaCorpo');
    if (!d.alunos || d.alunos.length === 0) {
      tbody.innerHTML = '<tr><td colspan="32" class="text-center py-4">Nenhum aluno matriculado nesta turma.</td></tr>';
      return;
    }

    const formatVal = (val, isMedia = false) => {
      if (val === null || val === undefined || isNaN(val) || val <= 0) return '<span class="text-muted">-</span>';
      const num = Number(val);
      const cls = num >= 9.5 ? 'nota-positiva' : 'nota-negativa';
      const displayVal = isMedia ? Math.round(num) : (Number.isInteger(num) ? num : num.toFixed(1));
      return `<span class="${cls}">${displayVal}</span>`;
    };

    tbody.innerHTML = d.alunos.map((a, idx) => {
      return `
        <tr>
          <td><strong>${idx + 1}</strong></td>
          <td class="text-start"><strong>${a.nome}</strong></td>
          <td class="text-start">${a.apelido || '-'}</td>
          <td><span class="badge ${a.genero === 'F' ? 'bg-info text-dark' : 'bg-secondary'}">${a.genero}</span></td>
          <!-- 1º Trimestre -->
          <td>${formatVal(a.t1.t1)}</td>
          <td>${formatVal(a.t1.t2)}</td>
          <td>${formatVal(a.t1.t3)}</td>
          <td class="bg-light">${formatVal(a.t1.map)}</td>
          <td>${formatVal(a.t1.mac3)}</td>
          <td>${formatVal(a.t1.at)}</td>
          <td class="bg-light fw-bold fs-6">${formatVal(a.t1.mt, true)}</td>
          <td><small>${a.t1.comportamento || 'S'}</small></td>
          <td><span class="badge bg-light text-dark border">${a.t1.anotacao || '-'}</span></td>
          <!-- 2º Trimestre -->
          <td>${formatVal(a.t2.t1)}</td>
          <td>${formatVal(a.t2.t2)}</td>
          <td>${formatVal(a.t2.t3)}</td>
          <td class="bg-light">${formatVal(a.t2.map)}</td>
          <td>${formatVal(a.t2.mac3)}</td>
          <td>${formatVal(a.t2.at)}</td>
          <td class="bg-light fw-bold fs-6">${formatVal(a.t2.mt, true)}</td>
          <td><small>${a.t2.comportamento || 'S'}</small></td>
          <td><span class="badge bg-light text-dark border">${a.t2.anotacao || '-'}</span></td>
          <!-- 3º Trimestre -->
          <td>${formatVal(a.t3.t1)}</td>
          <td>${formatVal(a.t3.t2)}</td>
          <td>${formatVal(a.t3.t3)}</td>
          <td class="bg-light">${formatVal(a.t3.map)}</td>
          <td>${formatVal(a.t3.mac3)}</td>
          <td>${formatVal(a.t3.at)}</td>
          <td class="bg-light fw-bold fs-6">${formatVal(a.t3.mt, true)}</td>
          <td><small>${a.t3.comportamento || 'S'}</small></td>
          <td><span class="badge bg-light text-dark border">${a.t3.anotacao || '-'}</span></td>
          <!-- MFD -->
          <td class="bg-light fw-bold fs-6">${formatVal(a.mfd, true)}</td>
        </tr>
      `;
    }).join('');

    // Preencher Linhas de Estatística por Coluna no Rodapé (Imagem 2)
    const tfoot = document.getElementById('tabelaCadernetaRodape');
    if (tfoot && d.estatisticasColunas) {
      const stats = d.estatisticasColunas;
      const chavesColunas = [
        't1_t1', 't1_t2', 't1_t3', 't1_map', null, 't1_at', 't1_mt', null, null,
        't2_t1', 't2_t2', 't2_t3', 't2_map', null, 't2_at', 't2_mt', null, null,
        't3_t1', 't3_t2', 't3_t3', 't3_map', null, 't3_at', 't3_mt', null, null,
        'mfd'
      ];

      const renderCelulasEstatistica = (extrator) => {
        return chavesColunas.map(key => {
          if (!key || !stats[key]) return '<td>-</td>';
          return `<td>${extrator(stats[key])}</td>`;
        }).join('');
      };

      tfoot.innerHTML = `
        <tr class="table-secondary">
          <td colspan="4" class="text-start ps-3 fw-bold">Alunos Avaliados</td>
          ${renderCelulasEstatistica(s => s.avaliados.total > 0 ? `<strong>${s.avaliados.total}</strong>` : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-3 text-success fw-semibold">Notas Positivas (>= 10)</td>
          ${renderCelulasEstatistica(s => s.positivas.total > 0 ? `<span class="text-success fw-bold">${s.positivas.total}</span>` : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-3 text-success fw-semibold">% Positivas</td>
          ${renderCelulasEstatistica(s => s.avaliados.total > 0 ? `<span class="text-success">${s.positivas.pct}%</span>` : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-3 text-danger fw-semibold">Notas Negativas (< 10)</td>
          ${renderCelulasEstatistica(s => s.negativas.total > 0 ? `<span class="text-danger fw-bold">${s.negativas.total}</span>` : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-3 text-danger fw-semibold">% Negativas</td>
          ${renderCelulasEstatistica(s => s.avaliados.total > 0 ? `<span class="text-danger">${s.negativas.pct}%</span>` : '-')}
        </tr>
        <tr class="table-light">
          <td colspan="4" class="text-start ps-3 fw-bold text-primary">Média da Coluna</td>
          ${renderCelulasEstatistica(s => s.media > 0 ? `<strong class="text-primary">${s.media}</strong>` : '-')}
        </tr>
      `;
    }
  } catch (err) {
    console.error('Erro ao carregar caderneta:', err);
  }
}

function exportarCadernetaExcel() {
  if (!state.alocacaoAtualId) return alert('Selecione uma alocação de turma');
  const url = `/api/v1/professores/caderneta/${state.alocacaoAtualId}/xlsx`;
  downloadFicheiroBinario(url, `Caderneta_Oficial_2026.xlsx`);
}

function imprimirCadernetaOficial() {
  window.print();
}

async function modalSalvarNotaCaderneta() {
  if (!state.alocacaoAtualId) return alert('Selecione uma turma e disciplina');

  const periodo = document.getElementById('cadernetaPeriodoSelect')?.value || '1_TRIMESTRE';
  const resCaderneta = await apiFetch(`/api/v1/professores/caderneta/${state.alocacaoAtualId}/completa`);
  if (!resCaderneta.success || !resCaderneta.data.alunos?.length) {
    return alert('Não há alunos nesta turma');
  }

  const optAlunos = resCaderneta.data.alunos.map(item => 
    `<option value="${item.alunoId}">${item.nome} ${item.apelido || ''}</option>`
  ).join('');

  const optAnotacoes = (state.geografia.anotacoes || []).map(a => 
    `<option value="${a.codigo}">${a.codigo} — ${a.significado}</option>`
  ).join('');

  const optComp = (state.geografia.comportamentos || []).map(c => 
    `<option value="${c.sigla}" ${c.sigla === 'B' ? 'selected' : ''}>${c.sigla} — ${c.descricao}</option>`
  ).join('');

  abrirModal('Lançar Avaliações do Aluno', `
    <form id="formModalLancamentoNota">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Aluno Seleccionado</label>
        <select id="mlnAluno" class="form-select" required>${optAlunos}</select>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-md-6">
          <label class="form-label small fw-semibold">1ª ACS (0-20)</label>
          <input type="number" step="0.5" min="0" max="20" id="mlnT1" class="form-control" value="12" required>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">2ª ACS (0-20)</label>
          <input type="number" step="0.5" min="0" max="20" id="mlnT2" class="form-control" value="13" required>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">3ª ACS (Opcional, 0-20)</label>
          <input type="number" step="0.5" min="0" max="20" id="mlnT3" class="form-control" placeholder="Opcional">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Trabalho / MAC3 (0-20)</label>
          <input type="number" step="0.5" min="0" max="20" id="mlnTrabalho" class="form-control" value="14" required>
        </div>
        <div class="col-md-12">
          <label class="form-label small fw-semibold">Avaliação Trimestral - AT (0-20)</label>
          <input type="number" step="0.5" min="0" max="20" id="mlnAT" class="form-control" value="12" required>
        </div>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Faltas</label>
          <input type="number" id="mlnFaltas" class="form-control" value="0" min="0">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Anotação Especial</label>
          <select id="mlnAnotacao" class="form-select">
            <option value="">(Nenhuma)</option>
            ${optAnotacoes}
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Comportamento</label>
          <select id="mlnComp" class="form-select">${optComp}</select>
        </div>
      </div>

      <button type="submit" class="btn btn-primary w-100">Gravar Avaliação no Trimestre</button>
    </form>
  `);

  document.getElementById('formModalLancamentoNota').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const aloc = state.alocacoesDocente.find(a => a.id === state.alocacaoAtualId);
      const body = {
        aluno_id: document.getElementById('mlnAluno').value,
        turma_id: aloc.turma_id,
        disciplina_id: aloc.disciplina_id,
        periodo: periodo,
        teste1: Number(document.getElementById('mlnT1').value),
        teste2: Number(document.getElementById('mlnT2').value),
        teste3: document.getElementById('mlnT3').value ? Number(document.getElementById('mlnT3').value) : undefined,
        nota_trabalho: Number(document.getElementById('mlnTrabalho').value),
        avaliacao_trimestral: Number(document.getElementById('mlnAT').value),
        faltas: Number(document.getElementById('mlnFaltas').value) || 0,
        anotacao: document.getElementById('mlnAnotacao').value || undefined,
        comportamento: document.getElementById('mlnComp').value || 'B'
      };

      const res = await apiFetch('/api/v1/notas', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success) {
        fecharModal();
        carregarCadernetaDocente();
      }
    } catch (err) {
      alert(err.message || 'Erro ao lançar avaliação');
    }
  });
}

// ==================== 8. PAUTAS GERAIS & ACTAS OFICIAIS ====================
let subAbaPautaAtiva = 'pauta';

function mudarSubAbaPauta(aba) {
  subAbaPautaAtiva = aba;
  const btnPauta = document.getElementById('btnAbaPauta');
  const btnActa = document.getElementById('btnAbaActa');
  const viewPauta = document.getElementById('subViewPautaGeral');
  const viewActa = document.getElementById('subViewActaConselho');

  if (aba === 'pauta') {
    btnPauta?.classList.add('active');
    btnActa?.classList.remove('active');
    viewPauta?.classList.remove('d-none');
    viewActa?.classList.add('d-none');
  } else {
    btnActa?.classList.add('active');
    btnPauta?.classList.remove('active');
    viewActa?.classList.remove('d-none');
    viewPauta?.classList.add('d-none');
  }
  alternarVisualizacaoPautaTurma();
}

async function carregarPautas() {
  try {
    const resTurmas = await apiFetch('/api/v1/escola-admin/turmas');
    const selectTurma = document.getElementById('pautaTurmaSelect');
    if (!selectTurma) return;

    if (resTurmas.success && resTurmas.data.length > 0) {
      selectTurma.innerHTML = resTurmas.data.map(t => 
        `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`
      ).join('');
      alternarVisualizacaoPautaTurma();
    } else {
      selectTurma.innerHTML = '<option value="">Nenhuma turma cadastrada</option>';
    }
  } catch (err) {
    console.error('Erro ao carregar turmas na pauta:', err);
  }
}

async function alternarVisualizacaoPautaTurma() {
  const turmaId = document.getElementById('pautaTurmaSelect')?.value;
  if (!turmaId) return;

  if (subAbaPautaAtiva === 'pauta') {
    await carregarPautaGeral(turmaId);
  } else {
    await carregarActaConselho(turmaId);
  }
}

async function carregarPautaGeral(turmaId) {
  const container = document.getElementById('containerTabelaPautaGeral');
  if (!container) return;
  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar pauta geral da turma...</p></div>';

  try {
    const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/completa`);
    if (!res.success) return;
    const d = res.data;

    document.getElementById('pautaGeralTitulo').textContent = `Pauta Oficial de Aproveitamento Pedagógico — ${d.turma.nome} (${d.turma.grau_ano})`;
    document.getElementById('pautaGeralSubtitulo').textContent = `Ano Lectivo: ${d.turma.ano_letivo} | Turno: ${d.turma.turno || 'Diurno'} | Director de Turma: ${d.turma.director_turma} (${d.turma.director_turma_tel || ''})`;

    const formatNota = (val) => {
      if (val === null || val === undefined || isNaN(val) || val <= 0) return '<span class="text-muted">-</span>';
      const num = Number(val);
      const cls = num >= 9.5 ? 'nota-positiva' : 'nota-negativa';
      return `<span class="${cls}">${Number.isInteger(num) ? num : num.toFixed(1)}</span>`;
    };

    const thDisciplinas = d.disciplinas.map(disc => 
      `<th colspan="4" class="text-center bg-primary bg-opacity-10 text-primary border-start border-end fw-bold" style="font-size: 0.72rem;">${disc.codigo || disc.nome}</th>`
    ).join('');

    const thSubDisciplinas = d.disciplinas.map(() => 
      `<th style="font-size: 0.65rem;">1º</th><th style="font-size: 0.65rem;">2º</th><th style="font-size: 0.65rem;">3º</th><th style="font-size: 0.65rem;" class="bg-light fw-bold">MFD</th>`
    ).join('');

    let trsAlunos = d.alunos.map(a => {
      const tdDisciplinas = d.disciplinas.map(disc => {
        const nd = a.notasDisciplinas[disc.codigo || disc.id] || a.notasDisciplinas[disc.id] || {};
        return `
          <td>${formatNota(nd.t1)}</td>
          <td>${formatNota(nd.t2)}</td>
          <td>${formatNota(nd.t3)}</td>
          <td class="bg-light fw-bold">${formatNota(nd.mfd)}</td>
        `;
      }).join('');

      let badgeResultado = '';
      if (a.resultadoFinal === 'A') {
        badgeResultado = '<span class="badge badge-aprovado px-2 py-1">A</span>';
      } else if (a.resultadoFinal === 'R') {
        badgeResultado = '<span class="badge badge-reprovado px-2 py-1">R</span>';
      } else if (a.resultadoFinal === 'D') {
        badgeResultado = '<span class="badge bg-warning text-dark px-2 py-1">D</span>';
      } else {
        badgeResultado = '<span class="badge bg-info text-dark px-2 py-1">T</span>';
      }

      return `
        <tr>
          <td><strong>${a.numero}</strong></td>
          <td class="text-start"><strong>${a.nome}</strong></td>
          <td class="text-start">${a.apelido || '-'}</td>
          <td><span class="badge ${a.genero === 'F' ? 'bg-info text-dark' : 'bg-secondary'}">${a.genero}</span></td>
          ${tdDisciplinas}
          <td class="bg-light">${formatNota(a.mediasTrimestrais.t1)}</td>
          <td class="bg-light">${formatNota(a.mediasTrimestrais.t2)}</td>
          <td class="bg-light">${formatNota(a.mediasTrimestrais.t3)}</td>
          <td>${a.negativas.t1 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t1}</span>` : '0'}</td>
          <td>${a.negativas.t2 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t2}</span>` : '0'}</td>
          <td>${a.negativas.t3 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t3}</span>` : '0'}</td>
          <td class="bg-light">${a.negativas.fimDoAno > 0 ? `<span class="text-danger fw-bold">${a.negativas.fimDoAno}</span>` : '0'}</td>
          <td class="bg-light fw-bold fs-6">${formatNota(a.mediaFinalGeral)}</td>
          <td>${badgeResultado}</td>
        </tr>
      `;
    }).join('');

    const est = d.estatistica;

    container.innerHTML = `
      <table class="table table-bordered table-hover align-middle text-center small pauta-tabela" style="min-width: 1400px;">
        <thead class="table-light">
          <tr>
            <th rowspan="2" class="align-middle" style="width: 35px;">Nº</th>
            <th rowspan="2" class="align-middle text-start" style="min-width: 130px;">NOME DO ALUNO</th>
            <th rowspan="2" class="align-middle text-start" style="min-width: 80px;">Apelido</th>
            <th rowspan="2" class="align-middle" style="width: 35px;">Gên</th>
            ${thDisciplinas}
            <th colspan="3" class="bg-secondary bg-opacity-10 fw-bold">MÉDIAS TRIMESTRAIS</th>
            <th colspan="4" class="bg-danger bg-opacity-10 text-danger fw-bold">Nº DE NEGATIVAS</th>
            <th rowspan="2" class="align-middle bg-primary bg-opacity-10 text-primary fw-bold" style="width: 60px;">MÉDIA FINAL</th>
            <th rowspan="2" class="align-middle fw-bold" style="width: 50px;">RESULTADO</th>
          </tr>
          <tr>
            ${thSubDisciplinas}
            <th style="font-size: 0.68rem;">I</th>
            <th style="font-size: 0.68rem;">II</th>
            <th style="font-size: 0.68rem;">III</th>
            <th style="font-size: 0.68rem;">1º</th>
            <th style="font-size: 0.68rem;">2º</th>
            <th style="font-size: 0.68rem;">3º</th>
            <th style="font-size: 0.68rem;" class="bg-light fw-bold">Fim</th>
          </tr>
        </thead>
        <tbody>
          ${trsAlunos}
        </tbody>
        <tfoot class="table-light">
          <tr class="table-secondary fw-bold text-start">
            <td colspan="${4 + (d.disciplinas.length * 4) + 9}" class="ps-3 py-2">
              <div class="d-flex flex-wrap gap-4 align-items-center">
                <span>Total Inscritos: <strong>${est.inscritos.total}</strong> (H: ${est.inscritos.h} | M: ${est.inscritos.m})</span>
                <span>Avaliados: <strong>${est.avaliados.total}</strong></span>
                <span class="text-success">Aprovados: <strong>${est.aprovados.total}</strong> (${est.aprovados.pct}%)</span>
                <span class="text-danger">Reprovados: <strong>${est.reprovados.total}</strong> (${est.reprovados.pct}%)</span>
              </div>
            </td>
          </tr>
        </tfoot>
      </table>
    `;
  } catch (err) {
    container.innerHTML = '<div class="alert alert-danger">Erro ao carregar pauta geral da turma.</div>';
  }
}

async function carregarActaConselho(turmaId) {
  const container = document.getElementById('containerActaConselhoCorpo');
  if (!container) return;
  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar acta do conselho de avaliação...</p></div>';

  try {
    const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/acta`);
    if (!res.success) return;
    const d = res.data;

    const te = d.tabelaEfectivo;
    const ta = d.tabelaAproveitamento;

    container.innerHTML = `
      <!-- Cabeçalho Oficial da Acta (Imagem 1) -->
      <div class="row align-items-center mb-3">
        <div class="col-8 text-start">
          <h6 class="fw-bold mb-0 text-uppercase">REPÚBLICA DE MOÇAMBIQUE</h6>
          <small class="text-muted d-block fw-semibold text-uppercase">GOVERNO DA PROVÍNCIA DE ${d.escola.provincia || 'MAPUTO'}</small>
          <small class="text-muted d-block fw-semibold text-uppercase">GOVERNO DO DISTRITO DE ${d.escola.distrito || 'CIDADE DE MAPUTO'}</small>
          <h5 class="fw-bold text-dark mt-1 mb-0">${(d.escola.nome || 'Escola Secundária').toUpperCase()}</h5>
          <small class="fw-bold text-primary text-uppercase">SECTOR PEDAGÓGICO</small>
        </div>
        <div class="col-4 text-end">
          <div class="d-inline-flex border p-2 bg-light rounded text-center small" style="font-size: 0.72rem;">
            <div class="px-2 border-end"><strong>1º Trimestre</strong><br>${d.conselho.dataT1 || '__/__/2026'}</div>
            <div class="px-2 border-end"><strong>2º Trimestre</strong><br>${d.conselho.dataT2 || '__/__/2026'}</div>
            <div class="px-2"><strong>3º Trimestre</strong><br>${d.conselho.dataT3 || '__/__/2026'}</div>
          </div>
        </div>
      </div>

      <div class="text-center my-3">
        <h4 class="fw-bold text-uppercase border-bottom border-top py-2 tracking-wide">ACTA DO CONSELHO DE AVALIAÇÃO</h4>
      </div>

      <!-- Texto Protocolar do Conselho de Avaliação (Imagem 1) -->
      <div class="p-3 bg-light rounded border mb-4 small" style="line-height: 1.8; text-align: justify;">
        Sob presidência do senhor professor <strong>${d.conselho.presidente}</strong> (Iº Trimestre); 
        <strong>${d.conselho.presidente}</strong> (IIº Trimestre); 
        director/substituto do director de turma <strong>${d.turma.nome}</strong> do grupo da <strong>${d.turma.grau_ano}</strong>, 
        curso <strong>${d.turma.turno === 'NOITE' ? 'Nocturno' : 'Diurno'}</strong>, realizou-se o Conselho de Avaliação do Iº, IIº e IIIº Trimestres 
        no dia <strong>${d.conselho.dataT1}</strong>, com início às <strong>${d.conselho.horaInicio}</strong> e com término às <strong>${d.conselho.horaFim}</strong>. 
        No final deste conselho colheram-se os resultados que abaixo vão discriminados de todos os membros que participaram:
      </div>

      <div class="row g-3 mb-4">
        <!-- TABELA 1: Aproveitamento Pedagógico por Trimestre e Fim do Ano (Efectivos e Movimento) -->
        <div class="col-lg-6">
          <div class="border rounded p-2 bg-white h-100 shadow-sm">
            <h6 class="fw-bold text-center small text-uppercase mb-2 bg-primary bg-opacity-10 py-1 rounded">Aproveitamento por Trimestre e Fim do Ano</h6>
            <div class="table-responsive">
              <table class="table table-bordered table-sm text-center mb-0" style="font-size: 0.68rem;">
                <thead class="table-light">
                  <tr>
                    <th rowspan="2" class="align-middle text-start">CATEGORIA</th>
                    <th colspan="3">Iº TRIMESTRE</th>
                    <th colspan="3">IIº TRIMESTRE</th>
                    <th colspan="3">IIIº TRIMESTRE</th>
                    <th colspan="3">FIM DO ANO</th>
                  </tr>
                  <tr>
                    <th>H</th><th>M</th><th>HM</th>
                    <th>H</th><th>M</th><th>HM</th>
                    <th>H</th><th>M</th><th>HM</th>
                    <th>H</th><th>M</th><th>HM</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="text-start fw-semibold">Efectivo Inicial</td>
                    <td>${te.t1.inscritos.h}</td><td>${te.t1.inscritos.m}</td><td class="fw-bold">${te.t1.inscritos.hm}</td>
                    <td>${te.t2.inscritos.h}</td><td>${te.t2.inscritos.m}</td><td class="fw-bold">${te.t2.inscritos.hm}</td>
                    <td>${te.t3.inscritos.h}</td><td>${te.t3.inscritos.m}</td><td class="fw-bold">${te.t3.inscritos.hm}</td>
                    <td>${te.fimAno.inscritos.h}</td><td>${te.fimAno.inscritos.m}</td><td class="fw-bold">${te.fimAno.inscritos.hm}</td>
                  </tr>
                  <tr>
                    <td class="text-start">Desistentes</td>
                    <td>${te.t1.desistentes.h}</td><td>${te.t1.desistentes.m}</td><td>${te.t1.desistentes.hm}</td>
                    <td>${te.t2.desistentes.h}</td><td>${te.t2.desistentes.m}</td><td>${te.t2.desistentes.hm}</td>
                    <td>${te.t3.desistentes.h}</td><td>${te.t3.desistentes.m}</td><td>${te.t3.desistentes.hm}</td>
                    <td>${te.fimAno.desistentes.h}</td><td>${te.fimAno.desistentes.m}</td><td>${te.fimAno.desistentes.hm}</td>
                  </tr>
                  <tr>
                    <td class="text-start">Transferidos</td>
                    <td>${te.t1.transferidos.h}</td><td>${te.t1.transferidos.m}</td><td>${te.t1.transferidos.hm}</td>
                    <td>${te.t2.transferidos.h}</td><td>${te.t2.transferidos.m}</td><td>${te.t2.transferidos.hm}</td>
                    <td>${te.t3.transferidos.h}</td><td>${te.t3.transferidos.m}</td><td>${te.t3.transferidos.hm}</td>
                    <td>${te.fimAno.transferidos.h}</td><td>${te.fimAno.transferidos.m}</td><td>${te.fimAno.transferidos.hm}</td>
                  </tr>
                  <tr>
                    <td class="text-start">Falecidos</td>
                    <td>${te.t1.falecidos.h}</td><td>${te.t1.falecidos.m}</td><td>${te.t1.falecidos.hm}</td>
                    <td>${te.t2.falecidos.h}</td><td>${te.t2.falecidos.m}</td><td>${te.t2.falecidos.hm}</td>
                    <td>${te.t3.falecidos.h}</td><td>${te.t3.falecidos.m}</td><td>${te.t3.falecidos.hm}</td>
                    <td>${te.fimAno.falecidos.h}</td><td>${te.fimAno.falecidos.m}</td><td>${te.fimAno.falecidos.hm}</td>
                  </tr>
                  <tr class="table-light fw-bold">
                    <td class="text-start">Efectivo Final (Avaliados)</td>
                    <td>${te.t1.avaliados.h}</td><td>${te.t1.avaliados.m}</td><td>${te.t1.avaliados.hm}</td>
                    <td>${te.t2.avaliados.h}</td><td>${te.t2.avaliados.m}</td><td>${te.t2.avaliados.hm}</td>
                    <td>${te.t3.avaliados.h}</td><td>${te.t3.avaliados.m}</td><td>${te.t3.avaliados.hm}</td>
                    <td>${te.fimAno.avaliados.h}</td><td>${te.fimAno.avaliados.m}</td><td>${te.fimAno.avaliados.hm}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- TABELA 2: Classificação Pedagógica por Faixas de Notas -->
        <div class="col-lg-6">
          <div class="border rounded p-2 bg-white h-100 shadow-sm">
            <h6 class="fw-bold text-center small text-uppercase mb-2 bg-info bg-opacity-10 py-1 rounded">Aproveitamento Pedagógico por Faixas</h6>
            <div class="table-responsive">
              <table class="table table-bordered table-sm text-center mb-0" style="font-size: 0.68rem;">
                <thead class="table-light">
                  <tr>
                    <th rowspan="2" class="align-middle text-start">CLASSIFICAÇÃO</th>
                    <th colspan="2">Iº TRIMESTRE</th>
                    <th colspan="2">IIº TRIMESTRE</th>
                    <th colspan="2">IIIº TRIMESTRE</th>
                    <th colspan="2">FIM DO ANO</th>
                  </tr>
                  <tr>
                    <th>HM</th><th>%</th>
                    <th>HM</th><th>%</th>
                    <th>HM</th><th>%</th>
                    <th>HM</th><th>%</th>
                  </tr>
                </thead>
                <tbody>
                  <tr class="table-secondary fw-bold">
                    <td class="text-start">Alunos Avaliados</td>
                    <td>${ta.t1.avaliados.hm}</td><td>100%</td>
                    <td>${ta.t2.avaliados.hm}</td><td>100%</td>
                    <td>${ta.t3.avaliados.hm}</td><td>100%</td>
                    <td>${ta.fimAno.avaliados.hm}</td><td>100%</td>
                  </tr>
                  <tr>
                    <td class="text-start text-danger">Não Satisfatório (0 a 9)</td>
                    <td>${ta.t1.naoSatisfatorio.hm}</td><td>${ta.t1.naoSatisfatorio.pct}%</td>
                    <td>${ta.t2.naoSatisfatorio.hm}</td><td>${ta.t2.naoSatisfatorio.pct}%</td>
                    <td>${ta.t3.naoSatisfatorio.hm}</td><td>${ta.t3.naoSatisfatorio.pct}%</td>
                    <td>${ta.fimAno.naoSatisfatorio.hm}</td><td>${ta.fimAno.naoSatisfatorio.pct}%</td>
                  </tr>
                  <tr>
                    <td class="text-start">Satisfatório (10 a 13)</td>
                    <td>${ta.t1.satisfatorio.hm}</td><td>${ta.t1.satisfatorio.pct}%</td>
                    <td>${ta.t2.satisfatorio.hm}</td><td>${ta.t2.satisfatorio.pct}%</td>
                    <td>${ta.t3.satisfatorio.hm}</td><td>${ta.t3.satisfatorio.pct}%</td>
                    <td>${ta.fimAno.satisfatorio.hm}</td><td>${ta.fimAno.satisfatorio.pct}%</td>
                  </tr>
                  <tr>
                    <td class="text-start">Bom (14 a 16)</td>
                    <td>${ta.t1.bom.hm}</td><td>${ta.t1.bom.pct}%</td>
                    <td>${ta.t2.bom.hm}</td><td>${ta.t2.bom.pct}%</td>
                    <td>${ta.t3.bom.hm}</td><td>${ta.t3.bom.pct}%</td>
                    <td>${ta.fimAno.bom.hm}</td><td>${ta.fimAno.bom.pct}%</td>
                  </tr>
                  <tr>
                    <td class="text-start">Muito Bom (17 a 18)</td>
                    <td>${ta.t1.muitoBom.hm}</td><td>${ta.t1.muitoBom.pct}%</td>
                    <td>${ta.t2.muitoBom.hm}</td><td>${ta.t2.muitoBom.pct}%</td>
                    <td>${ta.t3.muitoBom.hm}</td><td>${ta.t3.muitoBom.pct}%</td>
                    <td>${ta.fimAno.muitoBom.hm}</td><td>${ta.fimAno.muitoBom.pct}%</td>
                  </tr>
                  <tr>
                    <td class="text-start">Excelente (19 a 20)</td>
                    <td>${ta.t1.excelente.hm}</td><td>${ta.t1.excelente.pct}%</td>
                    <td>${ta.t2.excelente.hm}</td><td>${ta.t2.excelente.pct}%</td>
                    <td>${ta.t3.excelente.hm}</td><td>${ta.t3.excelente.pct}%</td>
                    <td>${ta.fimAno.excelente.hm}</td><td>${ta.fimAno.excelente.pct}%</td>
                  </tr>
                  <tr class="table-success fw-bold">
                    <td class="text-start">Total Aprovados</td>
                    <td>${ta.t1.aprovados.hm}</td><td>${ta.t1.aprovados.pct}%</td>
                    <td>${ta.t2.aprovados.hm}</td><td>${ta.t2.aprovados.pct}%</td>
                    <td>${ta.t3.aprovados.hm}</td><td>${ta.t3.aprovados.pct}%</td>
                    <td>${ta.fimAno.aprovados.hm}</td><td>${ta.fimAno.aprovados.pct}%</td>
                  </tr>
                  <tr class="table-danger fw-bold">
                    <td class="text-start">Total Reprovados</td>
                    <td>${ta.t1.reprovados.hm}</td><td>${ta.t1.reprovados.pct}%</td>
                    <td>${ta.t2.reprovados.hm}</td><td>${ta.t2.reprovados.pct}%</td>
                    <td>${ta.t3.reprovados.hm}</td><td>${ta.t3.reprovados.pct}%</td>
                    <td>${ta.fimAno.reprovados.hm}</td><td>${ta.fimAno.reprovados.pct}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- TABELA 3: Estatística por Disciplina (Imagem 1) -->
      <div class="border rounded p-3 bg-white mb-4 shadow-sm">
        <h6 class="fw-bold text-center small text-uppercase mb-2 bg-secondary bg-opacity-10 py-1 rounded">Estatística de Aproveitamento por Disciplina Curricular</h6>
        <div class="table-responsive">
          <table class="table table-bordered table-sm text-center mb-0" style="font-size: 0.7rem;">
            <thead class="table-light">
              <tr>
                <th class="text-start">DISCIPLINA</th>
                <th>[0 - 9]</th>
                <th>[10 - 13]</th>
                <th>[14 - 16]</th>
                <th>[17 - 18]</th>
                <th>[19 - 20]</th>
                <th class="bg-light fw-bold">AVALIADOS</th>
                <th class="text-success fw-bold">POSITIVAS</th>
                <th class="text-success fw-bold">% POSITIVAS</th>
                <th class="text-danger fw-bold">NEGATIVAS</th>
                <th class="text-danger fw-bold">% NEGATIVAS</th>
              </tr>
            </thead>
            <tbody>
              ${d.disciplinas.map(disc => `
                <tr>
                  <td class="text-start fw-bold">${disc.nome}</td>
                  <td class="${disc.faixa0_9.hm > 0 ? 'text-danger fw-bold' : ''}">${disc.faixa0_9.hm}</td>
                  <td>${disc.faixa10_13.hm}</td>
                  <td>${disc.faixa14_16.hm}</td>
                  <td>${disc.faixa17_18.hm}</td>
                  <td>${disc.faixa19_20.hm}</td>
                  <td class="bg-light fw-bold">${disc.avaliados.hm}</td>
                  <td class="text-success fw-bold">${disc.positivas.hm}</td>
                  <td class="text-success">${disc.positivas.pct}%</td>
                  <td class="text-danger fw-bold">${disc.negativas.hm}</td>
                  <td class="text-danger">${disc.negativas.pct}%</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Assinaturas Formais dos Membros do Conselho de Avaliação (Imagem 1) -->
      <div class="row text-center pt-4 border-top mt-5 small">
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-3 fw-semibold">O Director de Turma (Presidente)</p>
          <small class="text-muted">${d.conselho.presidente}</small>
        </div>
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-3 fw-semibold">O Secretário do Conselho</p>
          <small class="text-muted">Docente Designado</small>
        </div>
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-3 fw-semibold">O Director Adjunto Pedagógico (DAP)</p>
          <small class="text-muted">Visto & Homologado</small>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = '<div class="alert alert-danger">Erro ao carregar acta do conselho de avaliação.</div>';
  }
}

function exportarPautaGeralExcel() {
  const turmaId = document.getElementById('pautaTurmaSelect')?.value;
  if (!turmaId) return alert('Selecione uma turma');
  const ano = document.getElementById('pautaAnoSelect')?.value || '2026';
  downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/export-xlsx?anoLetivo=${ano}`, `Pauta_Geral_Turma_${ano}.xlsx`);
}

function exportarActaConselhoExcel() {
  const turmaId = document.getElementById('pautaTurmaSelect')?.value;
  if (!turmaId) return alert('Selecione uma turma');
  const ano = document.getElementById('pautaAnoSelect')?.value || '2026';
  downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/acta-xlsx?anoLetivo=${ano}`, `Acta_Conselho_Turma_${ano}.xlsx`);
}

function imprimirPautaGeralOficial() {
  window.print();
}

function imprimirActaConselhoOficial() {
  window.print();
}

async function modalGerarPauta() {
  const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
  const optTurmas = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`
  ).join('');

  abrirModal('Consolidar Pauta Oficial de Turma', `
    <form id="formModalPauta">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Turma a Consolidar</label>
        <select id="mpautTurma" class="form-select">${optTurmas}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Período Lectivo</label>
        <select id="mpautPeriodo" class="form-select">
          <option value="1_TRIMESTRE">1º Trimestre</option>
          <option value="2_TRIMESTRE">2º Trimestre</option>
          <option value="3_TRIMESTRE">3º Trimestre</option>
          <option value="ANUAL">Pauta Anual Consolidada Final</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Pauta Oficial</button>
    </form>
  `);

  document.getElementById('formModalPauta').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/pautas/gerar', {
        method: 'POST',
        body: JSON.stringify({
          turma_id: document.getElementById('mpautTurma').value,
          periodo: document.getElementById('mpautPeriodo').value,
          ano_letivo: '2026'
        })
      });
      if (res.success) {
        fecharModal();
        alternarVisualizacaoPautaTurma();
      }
    } catch (err) {
      alert(err.message || 'Erro ao gerar pauta');
    }
  });
}

// ==================== 9. CERTIFICADOS (QR CODE) ====================
async function carregarCertificados() {
  try {
    const res = await apiFetch('/api/v1/certificados');
    if (res.success) {
      const tbody = document.getElementById('tabelaCertificados');
      tbody.innerHTML = res.data.map(c => `
        <tr>
          <td><code class="text-primary">${c.codigo_autenticidade}</code></td>
          <td><strong>${c.aluno.nome}</strong></td>
          <td><span class="badge bg-light text-dark border">${c.tipo}</span></td>
          <td>${new Date(c.emitido_em).toLocaleDateString('pt-PT')}</td>
          <td>
            <img src="${c.qrcode_data}" alt="QR" width="38" height="38" class="border rounded" style="cursor: pointer;" onclick="verQrCodeGrande('${c.qrcode_data}', '${c.codigo_autenticidade}')">
          </td>
          <td class="text-end">
            <a href="/verificar-certificado.html?codigo=${c.codigo_autenticidade}" target="_blank" class="btn btn-sm btn-outline-primary">
              <i class="bi bi-shield-check me-1"></i> Validar
            </a>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

function verQrCodeGrande(qrSrc, codigo) {
  abrirModal('Autenticação Digital por QR Code', `
    <div class="text-center p-3">
      <img src="${qrSrc}" width="220" height="220" class="img-fluid border rounded p-2 mb-3 shadow-sm">
      <p class="font-monospace small text-muted">${codigo}</p>
      <div class="alert alert-info small mb-0">
        Qualquer cidadão ou instituição pode ler este QR Code com a câmara do telemóvel para certificar a autenticidade deste documento emitido pelo SIGE.
      </div>
    </div>
  `);
}

async function modalEmitirCertificado() {
  const alunosRes = await apiFetch('/api/v1/alunos');
  const optAlunos = (alunosRes.data || []).map(a => `<option value="${a.id}">${a.nome} (${a.matricula})</option>`).join('');

  abrirModal('Emitir Certificado com QR Code', `
    <form id="formModalCert">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Aluno Titular</label>
        <select id="mcertAluno" class="form-select" required>${optAlunos}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Tipo de Certificado Oficial</label>
        <select id="mcertTipo" class="form-select">
          <option value="CONCLUSAO">Certificado de Conclusão de Estudos</option>
          <option value="TRANSFERENCIA">Guia de Transferência Oficial</option>
          <option value="MATRICULA">Declaração de Matrícula e Frequência</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary w-100">Emitir Certificado Criptográfico</button>
    </form>
  `);

  document.getElementById('formModalCert').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/certificados', {
        method: 'POST',
        body: JSON.stringify({
          aluno_id: document.getElementById('mcertAluno').value,
          tipo: document.getElementById('mcertTipo').value
        })
      });
      if (res.success) {
        fecharModal();
        carregarCertificados();
      }
    } catch (err) {
      alert('Erro ao emitir certificado');
    }
  });
}

// ==================== 10. FINANCEIRO & MENSALIDADES ====================
async function carregarPagamentos() {
  try {
    const [resP, resStats] = await Promise.all([
      apiFetch('/api/v1/pagamentos'),
      apiFetch('/api/v1/pagamentos/stats')
    ]);

    if (resStats.success) {
      const s = resStats.data;
      document.getElementById('finFaturadoCard').textContent = s.totalFaturado.toLocaleString('pt-PT') + ' MZN';
      document.getElementById('finAtrasadoCard').textContent = s.totalAtrasado.toLocaleString('pt-PT') + ' MZN';
      document.getElementById('finInadimplenciaCard').textContent = s.taxaInadimplencia + '%';
      document.getElementById('finAdimplentesCard').textContent = s.percentualAdimplentes + '%';
    }

    if (resP.success) {
      const tbody = document.getElementById('tabelaPagamentos');
      tbody.innerHTML = resP.data.map(p => `
        <tr>
          <td><strong>${p.aluno.nome}</strong></td>
          <td>${p.descricao}</td>
          <td><code>${p.mes_referencia}</code></td>
          <td><strong class="text-success">${p.valor.toLocaleString('pt-PT')} MZN</strong></td>
          <td>${new Date(p.data_vencimento).toLocaleDateString('pt-PT')}</td>
          <td>
            <span class="badge ${p.status === 'PAGO' ? 'bg-success' : 'bg-warning text-dark'}">
              ${p.status}
            </span>
          </td>
          <td class="text-end">
            ${p.status === 'PENDENTE' ? `
              <button class="btn btn-sm btn-outline-success" onclick="liquidarPagamento('${p.id}', ${p.valor})">
                <i class="bi bi-cash me-1"></i> Liquidar
              </button>
            ` : `
              <button class="btn btn-sm btn-outline-primary" onclick="imprimirReciboPagamento('${p.id}')">
                <i class="bi bi-receipt me-1"></i> Recibo
              </button>
            `}
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

async function liquidarPagamento(id, valor) {
  if (!confirm(`Confirmar recebimento da quantia de ${valor.toLocaleString('pt-PT')} MZN?`)) return;
  try {
    const res = await apiFetch(`/api/v1/pagamentos/${id}/liquidar`, {
      method: 'POST',
      body: JSON.stringify({ valor_pago: valor, metodo_pagamento: 'TRANSFERENCIA_MZN' })
    });
    if (res.success) carregarPagamentos();
  } catch (err) {
    alert('Erro ao liquidar pagamento');
  }
}

async function modalNovoPagamento() {
  const alunosRes = await apiFetch('/api/v1/alunos');
  const optAlunos = (alunosRes.data || []).map(a => `<option value="${a.id}">${a.nome} (${a.matricula})</option>`).join('');

  abrirModal('Lançar Cobrança Individual de Mensalidade', `
    <form id="formModalPag">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Aluno</label>
        <select id="mpagAluno" class="form-select" required>${optAlunos}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Descrição</label>
        <input type="text" id="mpagDesc" class="form-control" value="Mensalidade Escolar" required>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Mês Ref.</label>
          <input type="text" id="mpagMes" class="form-control" value="2026-03" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor em Meticais (MZN)</label>
          <input type="number" id="mpagValor" class="form-control" value="2500" required>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Data de Vencimento</label>
        <input type="date" id="mpagVenc" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Cobrança</button>
    </form>
  `);

  document.getElementById('formModalPag').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/pagamentos', {
        method: 'POST',
        body: JSON.stringify({
          aluno_id: document.getElementById('mpagAluno').value,
          descricao: document.getElementById('mpagDesc').value,
          mes_referencia: document.getElementById('mpagMes').value,
          valor: Number(document.getElementById('mpagValor').value),
          data_vencimento: document.getElementById('mpagVenc').value
        })
      });
      if (res.success) {
        fecharModal();
        carregarPagamentos();
      }
    } catch (err) {
      alert('Erro ao criar cobrança');
    }
  });
}

async function modalGerarMensalidadesTurma() {
  const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
  const optTurmas = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome}</option>`).join('');

  abrirModal('Gerar Mensalidades em Lote para a Turma', `
    <form id="formModalLotePag">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Turma</label>
        <select id="mlotTurma" class="form-select" required>${optTurmas}</select>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Mês Ref. (AAAA-MM)</label>
          <input type="text" id="mlotMes" class="form-control" value="2026-03" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor da Propina (MZN)</label>
          <input type="number" id="mlotValor" class="form-control" value="2500" required>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Data de Vencimento</label>
        <input type="date" id="mlotVenc" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Mensalidades para Todos os Alunos</button>
    </form>
  `);

  document.getElementById('formModalLotePag').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/pagamentos/gerar-turma', {
        method: 'POST',
        body: JSON.stringify({
          turma_id: document.getElementById('mlotTurma').value,
          mes_referencia: document.getElementById('mlotMes').value,
          valor: Number(document.getElementById('mlotValor').value),
          data_vencimento: document.getElementById('mlotVenc').value,
          descricao: `Propina de ${document.getElementById('mlotMes').value}`
        })
      });
      if (res.success) {
        alert(`Mensalidades geradas com sucesso para a turma!`);
        fecharModal();
        carregarPagamentos();
      }
    } catch (err) {
      alert(err.message || 'Erro ao gerar cobranças');
    }
  });
}

function imprimirReciboPagamento(pagamentoId) {
  alternarModoImpressao('INDIVIDUAL');
  document.getElementById('printTipoDoc').value = 'RECIBO';
  navegarPara('impressao');
  carregarReciboIndividual(pagamentoId);
}

// ==================== 11. CENTRAL DE IMPRESSÃO (INDIVIDUAL E LOTE) ====================
async function prepararCentralImpressao() {
  try {
    const [alunosRes, turmasRes] = await Promise.all([
      apiFetch('/api/v1/alunos'),
      apiFetch('/api/v1/escola-admin/turmas')
    ]);

    const selectAluno = document.getElementById('printSelectAluno');
    selectAluno.innerHTML = (alunosRes.data || []).map(a => 
      `<option value="${a.id}">${a.nome} (${a.matricula})</option>`
    ).join('');

    const selectTurma = document.getElementById('printSelectTurma');
    selectTurma.innerHTML = (turmasRes.data || []).map(t => 
      `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`
    ).join('');
  } catch (err) {}
}

function alternarModoImpressao(modo) {
  const containerAluno = document.getElementById('printSelectAlunoContainer');
  const containerTurma = document.getElementById('printSelectTurmaContainer');

  if (modo === 'LOTE') {
    containerAluno.classList.add('d-none');
    containerTurma.classList.remove('d-none');
  } else {
    containerAluno.classList.remove('d-none');
    containerTurma.classList.add('d-none');
  }
}

function alternarCamposImpressao(tipo) {
  // Ajustes de interface caso necessário
}

async function carregarVisualizacaoImpressao() {
  const tipo = document.getElementById('printTipoDoc').value;
  const modo = document.getElementById('printModoEmissao').value;
  const preview = document.getElementById('printAreaPreview');
  preview.style.display = 'block';
  preview.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A processar documento oficial...</p></div>';

  try {
    if (modo === 'LOTE') {
      const turmaId = document.getElementById('printSelectTurma').value;
      if (!turmaId) return alert('Selecione uma turma para emissão em lote');
      const resLote = await apiFetch(`/api/v1/impressao/lote/turma/${turmaId}?tipo=${tipo}`);
      if (resLote.success) {
        renderizarLoteImpressao(resLote.data);
      }
      return;
    }

    // Modo Individual
    const alunoId = document.getElementById('printSelectAluno').value;
    if (!alunoId) return alert('Selecione um aluno');

    if (tipo === 'BOLETIM') {
      const res = await apiFetch(`/api/v1/impressao/boletim/${alunoId}`);
      if (res.success) renderizarBoletim(res.data);
    } else if (tipo === 'DECLARACAO') {
      const res = await apiFetch(`/api/v1/impressao/declaracao/${alunoId}`);
      if (res.success) renderizarDeclaracao(res.data);
    } else if (tipo === 'CERTIFICADO') {
      const res = await apiFetch(`/api/v1/impressao/certificado/${alunoId}`);
      if (res.success) renderizarCertificado(res.data);
    } else if (tipo === 'FICHA') {
      const res = await apiFetch(`/api/v1/impressao/ficha/${alunoId}`);
      if (res.success) renderizarFichaAluno(res.data);
    } else if (tipo === 'RECIBO') {
      // Procura o último pagamento do aluno
      const pagRes = await apiFetch(`/api/v1/pagamentos?alunoId=${alunoId}`);
      if (pagRes.success && pagRes.data.length > 0) {
        carregarReciboIndividual(pagRes.data[0].id);
      } else {
        preview.innerHTML = '<div class="alert alert-warning">Nenhum recibo de pagamento emitido para este aluno.</div>';
      }
    }
  } catch (err) {
    preview.innerHTML = `<div class="alert alert-danger">${err.message || 'Erro ao carregar documento'}</div>`;
  }
}

async function carregarReciboIndividual(pagamentoId) {
  const preview = document.getElementById('printAreaPreview');
  preview.style.display = 'block';
  preview.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';

  try {
    const res = await apiFetch(`/api/v1/impressao/recibo/${pagamentoId}`);
    if (res.success) {
      renderizarRecibo(res.data);
    }
  } catch (err) {
    preview.innerHTML = '<div class="alert alert-danger">Erro ao carregar recibo de pagamento.</div>';
  }
}

function renderizarBoletim(d) {
  const preview = document.getElementById('printAreaPreview');
  const safeName = d.aluno.nome.replace(/[^a-zA-Z0-9]/g, '_');

  preview.innerHTML = `
    <div class="text-center border-bottom pb-3 mb-4">
      <h5 class="fw-bold mb-1">SISTEMA INTEGRADO DE GESTÃO ESCOLAR</h5>
      <h6 class="fw-bold mb-1">${d.escola.nome}</h6>
      <p class="text-muted small mb-0">NUIT: ${d.escola.nif_cnpj || '-'} | ${d.escola.distrito || '-'}, ${d.escola.provincia || 'Maputo'}</p>
      <h5 class="mt-3 fw-bold text-primary">${d.titulo} — ANO LECTIVO ${d.anoLetivo}</h5>
    </div>

    <div class="row g-2 mb-4 p-3 bg-light rounded small">
      <div class="col-6"><strong>Aluno:</strong> ${d.aluno.nome}</div>
      <div class="col-6"><strong>Nº Matrícula:</strong> ${d.aluno.matricula}</div>
      <div class="col-6"><strong>Turma:</strong> ${d.aluno.turma}</div>
      <div class="col-6"><strong>Grau / Classe:</strong> ${d.aluno.grau}</div>
    </div>

    <table class="table table-bordered table-sm mb-4 small text-center">
      <thead class="table-light">
        <tr>
          <th class="text-start">Disciplina</th>
          <th>1º Trimestre</th>
          <th>2º Trimestre</th>
          <th>3º Trimestre</th>
          <th class="bg-light fw-bold">Média Final</th>
          <th>Faltas</th>
        </tr>
      </thead>
      <tbody>
        ${d.disciplinas.map(item => `
          <tr>
            <td class="text-start"><strong>${item.nome}</strong></td>
            <td>${item.t1 !== null ? item.t1 : '-'}</td>
            <td>${item.t2 !== null ? item.t2 : '-'}</td>
            <td>${item.t3 !== null ? item.t3 : '-'}</td>
            <td class="fw-bold ${item.mediaFinal >= 9.5 ? 'nota-positiva' : 'nota-negativa'}">${item.mediaFinal !== null ? item.mediaFinal : '-'}</td>
            <td>${item.faltas}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>

    <div class="d-flex justify-content-between align-items-center p-3 border rounded mb-5 small">
      <div><strong>Média Global:</strong> <span class="fs-5 fw-bold text-primary">${d.mediaGeral}</span></div>
      <div><strong>Resultado Final:</strong> <span class="badge ${d.resultado === 'APROVADO' ? 'badge-aprovado' : 'badge-reprovado'} fs-6">${d.resultado}</span></div>
    </div>

    <!-- Data Formal sem Hora no Boletim Oficial -->
    <div class="text-end mb-4 small">
      <em>${d.dataEmissaoExtenso || 'Maputo, ' + new Date().toLocaleDateString('pt-PT')}</em>
    </div>

    <div class="row text-center pt-4 border-top small">
      <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">O Director Pedagógico (DAP)</p></div>
      <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">O Encarregado de Educação</p></div>
    </div>

    <div class="text-center mt-4 no-print">
      <button class="btn btn-primary" onclick="imprimirDocumentoComTitulo('Boletim_${safeName}_${d.anoLetivo}')">
        <i class="bi bi-printer me-2"></i> Imprimir / Guardar em PDF
      </button>
    </div>
  `;
}

function renderizarDeclaracao(d) {
  const preview = document.getElementById('printAreaPreview');
  const safeName = d.aluno.nome.replace(/[^a-zA-Z0-9]/g, '_');

  preview.innerHTML = `
    <div class="text-center border-bottom pb-3 mb-4">
      <h5 class="fw-bold mb-1">SISTEMA INTEGRADO DE GESTÃO ESCOLAR</h5>
      <h6 class="fw-bold mb-1">${d.escola.nome}</h6>
      <p class="text-muted small mb-0">NUIT: ${d.escola.nif_cnpj || '-'} | Ministério da Educação e Desenvolvimento Humano</p>
      <h4 class="mt-4 fw-bold text-dark text-uppercase tracking-wide">DECLARAÇÃO ESCOLAR</h4>
    </div>

    <div class="p-4 small" style="line-height: 2; text-align: justify;">
      Para os devidos efeitos, a Direcção da <strong>${d.escola.nome}</strong> declara que o(a) aluno(a)
      <strong>${d.aluno.nome}</strong>, titular do documento de identificação nº <strong>${d.aluno.numero_documento || 'Pendente'}</strong>,
      filho(a) de <strong>${d.aluno.pai || '...........................................'}</strong> e de 
      <strong>${d.aluno.mae || '...........................................'}</strong>, natural de 
      <strong>${d.aluno.distrito || '..................'}</strong>, Província de <strong>${d.aluno.provincia || '..................'}</strong>,
      encontra-se regularmente matriculado(a) nesta instituição sob o nº <strong>${d.aluno.matricula}</strong>,
      a frequentar a <strong>${d.aluno.turma?.nome || 'sua respectiva turma'}</strong> no Ano Lectivo de <strong>${d.anoLetivo}</strong>.
    </div>

    <!-- Data Formal sem Hora -->
    <div class="text-end my-5 small">
      <em>${d.dataEmissaoExtenso || 'Maputo, ' + new Date().toLocaleDateString('pt-PT')}</em>
    </div>

    <div class="row text-center pt-5 border-top small">
      <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">O Director da Escola</p></div>
      <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">O Chefe da Secretaria</p></div>
    </div>

    <div class="text-center mt-4 no-print">
      <button class="btn btn-primary" onclick="imprimirDocumentoComTitulo('Declaracao_${safeName}_${d.anoLetivo}')">
        <i class="bi bi-printer me-2"></i> Imprimir / Guardar em PDF
      </button>
    </div>
  `;
}

function renderizarCertificado(d) {
  const preview = document.getElementById('printAreaPreview');
  const safeName = d.aluno.nome.replace(/[^a-zA-Z0-9]/g, '_');

  preview.innerHTML = `
    <div class="text-center border-bottom pb-3 mb-4">
      <h5 class="fw-bold mb-1">SISTEMA INTEGRADO DE GESTÃO ESCOLAR</h5>
      <h6 class="fw-bold mb-1">${d.escola.nome}</h6>
      <p class="text-muted small mb-0">MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO</p>
      <h3 class="mt-4 fw-bold text-dark text-uppercase tracking-wider">CERTIFICADO OFICIAL</h3>
    </div>

    <div class="p-4 small" style="line-height: 2.2; text-align: justify;">
      Certifica-se que <strong>${d.aluno.nome}</strong>, com o documento nº <strong>${d.aluno.numero_documento || '-'}</strong>,
      filho(a) de <strong>${d.aluno.pai || '-'}</strong> e de <strong>${d.aluno.mae || '-'}</strong>, concluiu com aproveitamento 
      os estudos regulamentares na <strong>${d.aluno.turma?.nome || 'respectiva classe'}</strong> no Ano Lectivo de <strong>${d.anoLetivo}</strong>,
      obtendo a classificação final de <strong>${d.aluno.mediaGeral || '14'} valores</strong> (Aprovado).
    </div>

    <div class="d-flex justify-content-between align-items-center my-4 p-3 border rounded small">
      <div>
        <small class="text-muted d-block">Autenticidade Criptográfica Digital:</small>
        <code class="fw-bold">${d.codigoAutenticidade || 'SIGE-MZ-2026-OK'}</code>
      </div>
      <div>
        <img src="${d.qrcodeData || ''}" alt="QR Code" width="70" height="70" class="border p-1">
      </div>
    </div>

    <!-- Data Formal sem Hora -->
    <div class="text-end mb-5 small">
      <em>${d.dataEmissaoExtenso || 'Maputo, ' + new Date().toLocaleDateString('pt-PT')}</em>
    </div>

    <div class="row text-center pt-4 border-top small">
      <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">O Director da Escola</p></div>
      <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">O Director Adjunto Pedagógico</p></div>
    </div>

    <div class="text-center mt-4 no-print">
      <button class="btn btn-primary" onclick="imprimirDocumentoComTitulo('Certificado_${safeName}_${d.anoLetivo}')">
        <i class="bi bi-printer me-2"></i> Imprimir / Guardar em PDF
      </button>
    </div>
  `;
}

function renderizarRecibo(d) {
  const preview = document.getElementById('printAreaPreview');
  const safeName = d.aluno.nome.replace(/[^a-zA-Z0-9]/g, '_');

  // Recibo exige carimbo com DATA E HORA
  const carimboDataHora = d.carimboDataHora || (new Date().toLocaleDateString('pt-PT') + ' ' + new Date().toLocaleTimeString('pt-PT'));

  preview.innerHTML = `
    <div class="text-center border-bottom pb-3 mb-3">
      <h6 class="fw-bold mb-1">${d.escola.nome}</h6>
      <p class="text-muted small mb-0">NUIT: ${d.escola.nif_cnpj} | Telefone: ${d.escola.telefone || '-'}</p>
      <h5 class="mt-2 fw-bold text-success text-uppercase">RECIBO DE PAGAMENTO DE PROPINAS</h5>
      <span class="badge bg-light text-dark border">Recibo Nº: ${d.pagamento.recibo_numero || 'REC-2026-001'}</span>
    </div>

    <table class="table table-bordered table-sm small mb-4">
      <tr><th class="bg-light w-35">Aluno:</th><td>${d.aluno.nome} (Matrícula: ${d.aluno.matricula})</td></tr>
      <tr><th class="bg-light">Turma:</th><td>${d.aluno.turma?.nome || '-'}</td></tr>
      <tr><th class="bg-light">Descrição da Taxa:</th><td>${d.pagamento.descricao}</td></tr>
      <tr><th class="bg-light">Mês de Referência:</th><td><code>${d.pagamento.mes_referencia}</code></td></tr>
      <tr><th class="bg-light">Valor Pago:</th><td class="fw-bold text-success fs-6">${d.pagamento.valor.toLocaleString('pt-PT')} MZN</td></tr>
      <tr><th class="bg-light">Forma de Liquidação:</th><td>${d.pagamento.metodo_pagamento || 'Depósito / Transferência'}</td></tr>
      <tr><th class="bg-light">Data do Pagamento:</th><td>${new Date(d.pagamento.pago_em || Date.now()).toLocaleDateString('pt-PT')}</td></tr>
    </table>

    <!-- Carimbo com Data e Hora Oficial -->
    <div class="alert alert-light border small text-muted text-center py-2 mb-4">
      <i class="bi bi-clock-history me-1 text-primary"></i>
      Processado por Computador aos <strong>${carimboDataHora}</strong> | Autenticação SIGE
    </div>

    <div class="row text-center pt-3 border-top small">
      <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">A Secretaria / Tesouraria</p></div>
      <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">O Depositante</p></div>
    </div>

    <div class="text-center mt-4 no-print">
      <button class="btn btn-primary" onclick="imprimirDocumentoComTitulo('Recibo_${safeName}_${d.pagamento.mes_referencia}')">
        <i class="bi bi-printer me-2"></i> Imprimir Recibo
      </button>
    </div>
  `;
}

function renderizarFichaAluno(d) {
  const preview = document.getElementById('printAreaPreview');
  const safeName = d.aluno.nome.replace(/[^a-zA-Z0-9]/g, '_');
  const carimboDataHora = d.carimboDataHora || (new Date().toLocaleDateString('pt-PT') + ' ' + new Date().toLocaleTimeString('pt-PT'));

  preview.innerHTML = `
    <div class="text-center border-bottom pb-3 mb-4">
      <h5 class="fw-bold mb-1">${d.escola.nome}</h5>
      <h6 class="text-muted mb-2">FICHA BIOGRÁFICA DO ALUNO</h6>
      <span class="badge bg-primary">Matrícula Nº: ${d.aluno.matricula}</span>
    </div>

    <table class="table table-bordered table-sm small mb-4">
      <tr><th class="bg-light w-35">Nome Completo:</th><td><strong>${d.aluno.nome}</strong></td></tr>
      <tr><th class="bg-light">Apelido:</th><td>${d.aluno.apelido || '-'}</td></tr>
      <tr><th class="bg-light">Data de Nascimento:</th><td>${new Date(d.aluno.data_nascimento).toLocaleDateString('pt-PT')}</td></tr>
      <tr><th class="bg-light">Género:</th><td>${d.aluno.genero === 'M' ? 'Masculino' : 'Feminino'}</td></tr>
      <tr><th class="bg-light">Documento de Identificação:</th><td>${d.aluno.tipo_documento || 'BI'}: ${d.aluno.numero_documento || '-'}</td></tr>
      <tr><th class="bg-light">NUIT:</th><td>${d.aluno.nuit || '-'}</td></tr>
      <tr><th class="bg-light">Naturalidade / Província:</th><td>${d.aluno.distrito || '-'} / ${d.aluno.provincia || '-'}</td></tr>
      <tr><th class="bg-light">Filiação:</th><td>Pai: ${d.aluno.pai || '-'}<br>Mãe: ${d.aluno.mae || '-'}</td></tr>
      <tr><th class="bg-light">Encarregado de Educação:</th><td>${d.aluno.nome_responsavel || '-'} (${d.aluno.contato_responsavel || '-'})</td></tr>
      <tr><th class="bg-light">Turma Actual:</th><td>${d.aluno.turma?.nome || '-'}</td></tr>
    </table>

    <!-- Carimbo com Data e Hora Oficial -->
    <div class="alert alert-light border small text-muted text-center py-2 mb-4">
      <i class="bi bi-clock-history me-1 text-primary"></i>
      Registo Informatizado emitido aos <strong>${carimboDataHora}</strong>
    </div>

    <div class="text-center mt-4 no-print">
      <button class="btn btn-primary" onclick="imprimirDocumentoComTitulo('Ficha_${safeName}_2026')">
        <i class="bi bi-printer me-2"></i> Imprimir Ficha
      </button>
    </div>
  `;
}

function renderizarLoteImpressao(lista) {
  const preview = document.getElementById('printAreaPreview');
  preview.innerHTML = `
    <div class="no-print mb-4 p-3 bg-light border rounded d-flex justify-content-between align-items-center">
      <div>
        <strong class="text-primary fs-5">Lote Processado: ${lista.length} Documentos</strong>
        <span class="d-block small text-muted">Cada documento possui quebra de página A4 automática para impressão.</span>
      </div>
      <button class="btn btn-primary" onclick="window.print()">
        <i class="bi bi-printer me-2"></i> Imprimir Todo o Lote
      </button>
    </div>
    ${lista.map((item, i) => `
      <div class="printable-document mb-5 pb-5 border-bottom" style="page-break-after: always;">
        <div class="text-center border-bottom pb-3 mb-3">
          <h6 class="fw-bold mb-1">REPÚBLICA DE MOÇAMBIQUE</h6>
          <h5 class="fw-bold text-primary mb-1">${item.titulo || 'DOCUMENTO ESCOLAR OFICIAL'}</h5>
          <small class="text-muted">Aluno: ${item.aluno?.nome} | Matrícula: ${item.aluno?.matricula}</small>
        </div>
        <div class="p-3 small">
          ${item.conteudoHtml || '<p>Documento oficial emitido em lote pelo SIGE.</p>'}
        </div>
      </div>
    `).join('')}
  `;
}

function imprimirDocumentoComTitulo(titulo) {
  const originalTitle = document.title;
  document.title = titulo;
  window.print();
  document.title = originalTitle;
}

// ==================== 12. DESBLOQUEIO DE TRIMESTRE ====================
async function prepararDesbloqueioTrimestre() {
  try {
    const [turmasRes, profsRes] = await Promise.all([
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/professores')
    ]);

    const selectTurma = document.getElementById('desbloqueioTurma');
    selectTurma.innerHTML = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome}</option>`).join('');

    const selectProf = document.getElementById('desbloqueioProfessor');
    selectProf.innerHTML = '<option value="">(Todos os Docentes da Turma)</option>' +
      (profsRes.data || []).map(p => `<option value="${p.id}">${p.nome}</option>`).join('');
  } catch (err) {}
}

document.getElementById('formAutorizarDesbloqueio')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const body = {
      turma_id: document.getElementById('desbloqueioTurma').value,
      professor_id: document.getElementById('desbloqueioProfessor').value || undefined,
      periodo: document.getElementById('desbloqueioTrimestre').value,
      duracao_horas: Number(document.getElementById('desbloqueioHoras').value),
      motivo: document.getElementById('desbloqueioMotivo').value
    };

    const res = await apiFetch('/api/v1/notas/autorizar-desbloqueio', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    if (res.success) {
      alert('Autorização de desbloqueio concedida com sucesso!');
      document.getElementById('desbloqueioMotivo').value = '';
    }
  } catch (err) {
    alert(err.message || 'Erro ao autorizar desbloqueio');
  }
});

// ==================== 13. PORTAL PRIVADO DO ALUNO ====================
async function carregarAlunoPerfil() {
  try {
    const res = await apiFetch('/api/v1/alunos/perfil/me');
    if (res.success) {
      const a = res.data;
      document.getElementById('alunoPerfilNome').textContent = a.nome;
      document.getElementById('alunoPerfilApelido').textContent = a.apelido || '-';
      document.getElementById('alunoPerfilMatricula').textContent = a.matricula;
      document.getElementById('alunoPerfilTurma').textContent = a.turma ? `${a.turma.nome} (${a.turma.grau_ano})` : 'Sem Turma';
      document.getElementById('alunoPerfilDoc').textContent = `${a.tipo_documento || 'BI'}: ${a.numero_documento || '-'}`;
      document.getElementById('alunoPerfilNUIT').textContent = a.nuit || '-';
      document.getElementById('alunoPerfilLocal').textContent = `${a.distrito || '-'}, ${a.provincia || '-'}`;

      if (document.getElementById('alunoPerfilPai')) document.getElementById('alunoPerfilPai').textContent = a.pai || '-';
      if (document.getElementById('alunoPerfilMae')) document.getElementById('alunoPerfilMae').textContent = a.mae || '-';
      if (document.getElementById('alunoPerfilResp')) document.getElementById('alunoPerfilResp').textContent = a.nome_responsavel || '-';
      if (document.getElementById('alunoPerfilTelResp')) document.getElementById('alunoPerfilTelResp').textContent = a.contato_responsavel || '-';
      if (document.getElementById('alunoPerfilEmailResp')) document.getElementById('alunoPerfilEmailResp').textContent = a.email_responsavel || '-';
    }
  } catch (err) {}
}

async function carregarAlunoNotas() {
  try {
    const res = await apiFetch('/api/v1/alunos/me/notas');
    if (res.success) {
      const d = res.data;
      document.getElementById('alunoMediaGeral').textContent = d.mediaGeral || '--';
      
      const badgeSit = document.getElementById('alunoSituacaoBadge');
      if (d.situacao === 'APROVADO') {
        badgeSit.textContent = 'Aprovado';
        badgeSit.className = 'badge badge-aprovado p-2 ms-2';
      } else if (d.situacao === 'REPROVADO') {
        badgeSit.textContent = 'Reprovado';
        badgeSit.className = 'badge badge-reprovado p-2 ms-2';
      } else {
        badgeSit.textContent = d.situacao || 'Em Curso';
        badgeSit.className = 'badge bg-secondary p-2 ms-2';
      }

      const tbody = document.getElementById('tabelaAlunoNotasCorpo');
      if (!d.disciplinas || d.disciplinas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4">Nenhuma avaliação lançada até ao momento.</td></tr>';
        return;
      }

      tbody.innerHTML = d.disciplinas.map(item => {
        const medNum = item.mediaFinal !== null ? Number(item.mediaFinal) : null;
        const cls = medNum !== null ? (medNum >= 9.5 ? 'nota-positiva' : 'nota-negativa') : 'text-muted';

        return `
          <tr>
            <td class="text-start"><strong>${item.nome}</strong></td>
            <td>${item.t1 !== null ? item.t1 : '-'}</td>
            <td>${item.t2 !== null ? item.t2 : '-'}</td>
            <td>${item.t3 !== null ? item.t3 : '-'}</td>
            <td class="fw-bold fs-6 ${cls}">${medNum !== null ? Math.round(medNum) : '-'}</td>
            <td>${item.faltas || 0}</td>
            <td>
              ${medNum !== null 
                ? (medNum >= 9.5 ? '<span class="badge badge-aprovado">Positiva</span>' : '<span class="badge badge-reprovado">Negativa</span>')
                : '<span class="badge bg-light text-dark border">Pendente</span>'
              }
            </td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {}
}

async function carregarAlunoPagamentos() {
  try {
    const res = await apiFetch('/api/v1/alunos/me/pagamentos');
    if (res.success) {
      const tbody = document.getElementById('tabelaAlunoPagamentosCorpo');
      tbody.innerHTML = res.data.map(p => `
        <tr>
          <td><strong>${p.descricao}</strong></td>
          <td><code>${p.mes_referencia}</code></td>
          <td><strong class="text-success">${p.valor.toLocaleString('pt-PT')} MZN</strong></td>
          <td>${new Date(p.data_vencimento).toLocaleDateString('pt-PT')}</td>
          <td>
            <span class="badge ${p.status === 'PAGO' ? 'bg-success' : 'bg-warning text-dark'}">
              ${p.status}
            </span>
          </td>
          <td class="text-end">
            ${p.status === 'PAGO' ? `
              <button class="btn btn-sm btn-outline-primary" onclick="imprimirReciboPagamento('${p.id}')">
                <i class="bi bi-printer me-1"></i> Imprimir Recibo
              </button>
            ` : '<span class="text-muted small">Pendente de pagamento</span>'}
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

// ==================== 14. AUDITORIA & ACESSOS ====================
async function carregarLogsAcesso() {
  try {
    const res = await apiFetch('/api/v1/auth/stats');
    if (res.success) {
      const tbody = document.getElementById('tabelaLogsAcesso');
      tbody.innerHTML = res.data.logsRecentes.map(l => `
        <tr>
          <td>${new Date(l.createdAt).toLocaleDateString('pt-PT')} às ${new Date(l.createdAt).toLocaleTimeString('pt-PT')}</td>
          <td><strong>${l.usuario ? l.usuario.nome : 'Anónimo / Convidado'}</strong></td>
          <td><code>${l.ip}</code></td>
          <td class="small text-muted">${l.user_agent || '-'}</td>
          <td>
            <span class="badge ${l.tipo === 'LOGIN_SUCESSO' ? 'bg-success' : l.tipo === 'ACESSO_BLOQUEADO_EXPIRADO' ? 'bg-danger' : 'bg-warning text-dark'}">
              ${l.tipo}
            </span>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

// ==================== HELPERS DE MODAL ====================
let modalInstancia = null;
function abrirModal(titulo, htmlCorpo) {
  document.getElementById('modalGenericoTitulo').textContent = titulo;
  document.getElementById('modalGenericoCorpo').innerHTML = htmlCorpo;
  const el = document.getElementById('modalGenerico');
  modalInstancia = new bootstrap.Modal(el);
  modalInstancia.show();
}

function fecharModal() {
  if (modalInstancia) modalInstancia.hide();
}
