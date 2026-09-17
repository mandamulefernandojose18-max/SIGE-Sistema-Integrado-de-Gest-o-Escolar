
// ==================== EXPORTAÇÃO E DOWNLOAD EM PDF (CADERNETA, PAUTA, ACTA E DOCUMENTOS) ====================
function inicializarPatchHtml2Pdf() {
  if (!window.html2pdf || window.__html2pdfPatched) return;
  try {
    const dummy = window.html2pdf();
    const proto = Object.getPrototypeOf(dummy);
    if (proto && proto.toContainer) {
      const origToContainer = proto.toContainer;
      proto.toContainer = function() {
        return origToContainer.call(this).then(function() {
          if (this.prop && this.prop.overlay) {
            this.prop.overlay.style.opacity = '1';
            this.prop.overlay.style.left = '-99999px';
            this.prop.overlay.style.visibility = 'visible';
          }
          if (this.prop && this.prop.container) {
            this.prop.container.style.opacity = '1';
            this.prop.container.style.visibility = 'visible';
            this.prop.container.style.backgroundColor = '#ffffff';
          }
        });
      };
      window.__html2pdfPatched = true;
    }
  } catch (e) {
    console.warn('Patch html2pdf:', e);
  }
}

async function exportarElementoParaPdf(elementoOuId, filename, orientation = 'landscape') {
  const el = typeof elementoOuId === 'string' ? document.getElementById(elementoOuId) : elementoOuId;
  if (!el) {
    alert('Documento não disponível para exportação');
    return;
  }

  inicializarPatchHtml2Pdf();

  // Assegurar visibilidade no DOM caso o container esteja com display: none
  const displayOriginal = el.style.display;
  let foiExibido = false;
  try {
    if (displayOriginal === 'none' || window.getComputedStyle(el).display === 'none') {
      el.style.display = 'block';
      foiExibido = true;
    }
  } catch (_) {}

  // Assegurar estilo de fundo branco e cor de texto escura no elemento durante a captura
  const bgOriginal = el.style.backgroundColor;
  const colorOriginal = el.style.color;
  el.style.backgroundColor = '#ffffff';
  el.style.color = '#000000';

  const safeFilename = filename.toLowerCase().endsWith('.pdf') ? filename : `${filename}.pdf`;

  if (window.html2pdf) {
    const isPortrait = orientation === 'portrait';
    const opt = {
      margin: isPortrait ? [6, 8, 6, 8] : [5, 5, 5, 5],
      filename: safeFilename,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
        ignoreElements: (e) => e.classList?.contains('no-print') || e.tagName === 'BUTTON',
        onclone: (clonedDoc) => {
          const overlays = clonedDoc.querySelectorAll('.html2pdf__overlay');
          overlays.forEach(ov => {
            ov.style.opacity = '1';
            ov.style.visibility = 'visible';
          });
          const containers = clonedDoc.querySelectorAll('.html2pdf__container');
          containers.forEach(ct => {
            ct.style.opacity = '1';
            ct.style.visibility = 'visible';
            ct.style.backgroundColor = '#ffffff';
          });
          const docs = clonedDoc.querySelectorAll('.printable-document, .documento-a4-pagina-unica, table');
          docs.forEach(doc => {
            doc.style.opacity = '1';
            doc.style.visibility = 'visible';
            doc.style.backgroundColor = '#ffffff';
          });
        }
      },
      jsPDF: {
        unit: 'mm',
        format: 'a4',
        orientation: orientation
      }
    };

    try {
      await window.html2pdf().set(opt).from(el).save();
    } catch (err) {
      console.error('Erro ao gerar PDF:', err);
      window.print();
    } finally {
      el.style.backgroundColor = bgOriginal;
      el.style.color = colorOriginal;
      if (foiExibido) {
        el.style.display = displayOriginal;
      }
    }
  } else {
    el.style.backgroundColor = bgOriginal;
    el.style.color = colorOriginal;
    if (foiExibido) {
      el.style.display = displayOriginal;
    }
    window.print();
  }
}

function exportarPautaGeralExcel(turmaIdExplicit = null, anoExplicit = null) {
  const turmaId = turmaIdExplicit || document.getElementById('pautaTurmaSelect')?.value || document.getElementById('dtTurmaSelect')?.value;
  if (!turmaId) return alert('Selecione uma turma para exportar a pauta');
  const ano = anoExplicit || document.getElementById('pautaAnoFiltro')?.value || '2026';
  downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/export-xlsx?anoLetivo=${ano}`, `Pauta_Geral_Turma_${ano}.xlsx`);
}

function imprimirPautaGeralOficial() {
  window.print();
}

async function descarregarCadernetaPdf() {
  const el = document.getElementById('cadernetaPrintContainer');
  if (!el) return alert('Selecione uma alocação para visualizar a caderneta');
  await exportarElementoParaPdf(el, `Caderneta_Oficial_${state.alocacaoAtualId || '2026'}.pdf`, 'landscape');
}

function descarregarCadernetaExcel() {
  if (!state.alocacaoAtualId) return alert('Selecione uma alocação para exportar a caderneta');
  downloadFicheiroBinario(`/api/v1/professores/caderneta/${state.alocacaoAtualId}/xlsx`, `Caderneta_Oficial_2026.xlsx`);
}

async function descarregarPautaGeralPdf() {
  const el = document.getElementById('subViewPautaGeral');
  if (!el) return alert('Selecione uma turma para visualizar a pauta');
  const ano = document.getElementById('pautaAnoFiltro')?.value || '2026';
  await exportarElementoParaPdf(el, `Pauta_Geral_Turma_${ano}.pdf`, 'landscape');
}

async function descarregarActaConselhoPdf() {
  const el = document.getElementById('subViewActaConselho');
  if (!el) return alert('Selecione uma turma para visualizar a acta');
  const ano = document.getElementById('pautaAnoFiltro')?.value || '2026';
  await exportarElementoParaPdf(el, `Acta_Conselho_Turma_${ano}.pdf`, 'landscape');
}


function filtrarAlunosCaderneta() {
  const query = (document.getElementById('cadernetaPesquisaAluno')?.value || '').toLowerCase().trim();
  const rows = document.querySelectorAll('#tabelaCadernetaCorpo tr');
  rows.forEach(r => {
    if (!query) {
      r.style.display = '';
      return;
    }
    const texto = r.textContent.toLowerCase();
    r.style.display = texto.includes(query) ? '' : 'none';
  });
}

// SIGE — Sistema Integrado de Gestão Escolar (SaaS Multi-Tenant Moçambique)
// Lógica Principal do Frontend SPA em Português de Moçambique

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {});
  });
}

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
  alocacaoAtualId: null,
  filtroDisciplinaClasse: ''
};

// ==================== API FETCH & INTERCEPTADORES ====================
function formatarUrlApi(url) {
  if (!url || typeof url !== 'string') return url;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const baseUrl = (window.SIGE_CONFIG && window.SIGE_CONFIG.API_BASE_URL)
    || (window.location.port === '5173' || window.location.port === '8080' || window.location.port === '3001' ? 'http://localhost:3000/api/v1' : '/api/v1');
  if (url.startsWith('/api/v1')) {
    return baseUrl.replace(/\/api\/v1\/?$/, '') + url;
  }
  return baseUrl.replace(/\/+$/, '') + '/' + url.replace(/^\/+/, '');
}

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
    const res = await fetch(formatarUrlApi(endpoint), { ...options, headers });
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

// Download de Ficheiros Binários (Excel XLSX / PDF) com ArrayBuffer e MIME estrito
async function downloadFicheiroBinario(url, defaultFilename) {
  try {
    const headers = {};
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    const superAdminEscolaId = localStorage.getItem('sige_selected_tenant');
    if (superAdminEscolaId && state.user?.role === 'SUPERADMIN') {
      headers['X-Tenant-ID'] = superAdminEscolaId;
    }

    const res = await fetch(formatarUrlApi(url), { headers });
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

    const arrayBuffer = await res.arrayBuffer();
    const isXlsx = filename.toLowerCase().endsWith('.xlsx') || url.toLowerCase().includes('xlsx');
    const isPdf = filename.toLowerCase().endsWith('.pdf') || url.toLowerCase().includes('pdf');
    const isJson = filename.toLowerCase().endsWith('.json') || url.toLowerCase().includes('json');
    let mimeType = 'application/octet-stream';
    if (isXlsx) mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    else if (isPdf) mimeType = 'application/pdf';
    else if (isJson) mimeType = 'application/json';
    else if (res.headers.get('content-type')) mimeType = res.headers.get('content-type');

    const blob = new Blob([arrayBuffer], { type: mimeType });
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 5000);
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

        // Se for SuperAdmin e tiver uma escola seleccionada, carregar os dados daquela escola
        const savedTenantId = localStorage.getItem('sige_selected_tenant');
        if (state.user?.role === 'SUPERADMIN' && savedTenantId) {
          try {
            const escolaRes = await apiFetch('/api/v1/escola-admin/info');
            if (escolaRes.success && escolaRes.data) {
              state.tenant = escolaRes.data;
            }
          } catch(e) {}
        }

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
      if (json.data.user.role !== 'SUPERADMIN') {
        localStorage.removeItem('sige_selected_tenant');
      }
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

function fazerLogout(e) {
  if (e && e.preventDefault) e.preventDefault();
  localStorage.clear();
  sessionStorage.clear();
  state.token = null;
  state.user = null;
  state.tenant = null;
  window.location.href = '/';
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

  const savedTenant = localStorage.getItem('sige_selected_tenant');

  if (state.user.role === 'SUPERADMIN') {
    document.getElementById('superAdminTenantSelectWrapper').style.display = 'block';
    await carregarEscolasSuperAdminSelect();

    if (savedTenant) {
      // SuperAdmin está dentro de uma escola específica (Modo Inspecção)
      document.querySelectorAll('.escola-admin-only').forEach(el => el.style.display = 'flex');
      document.querySelectorAll('.ped-only').forEach(el => el.style.display = 'flex');
      document.querySelectorAll('.fin-only').forEach(el => el.style.display = 'flex');
      
      const bannerInspecao = document.getElementById('superAdminInspecaoBanner');
      if (bannerInspecao) {
        bannerInspecao.style.setProperty('display', 'flex', 'important');
        const nomeEscola = state.tenant?.nome || 'Escola Seleccionada';
        document.getElementById('superAdminInspecaoNome').textContent = `A Inspecionar: ${nomeEscola}`;
        document.getElementById('superAdminInspecaoStatus').textContent = state.tenant?.status || 'ATIVA';
      }
      navegarPara('dashboard');
    } else {
      const bannerInspecao = document.getElementById('superAdminInspecaoBanner');
      if (bannerInspecao) bannerInspecao.style.setProperty('display', 'none', 'important');
      navegarPara('saas');
    }
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
    if (typeof atualizarBotaoToggleNotasDap === 'function') {
      atualizarBotaoToggleNotasDap(state.tenant.permitir_visualizacao_notas !== false);
    }
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
    document.querySelectorAll('.professor-only').forEach(el => el.style.display = 'block');
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

function sairModoInspecaoSuperAdmin() {
  localStorage.removeItem('sige_selected_tenant');
  window.location.reload();
}

// ==================== NAVEGAÇÃO ENTRE MÓDULOS ====================
function navegarPara(viewId) {
  if (viewId === 'professor-perfil') carregarPerfilDocenteIndividual();
  if (viewId === 'usuarios-senhas') carregarCofreUsuarios();
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
    'director-turma': 'Painel Oficial do Director de Turma (Pauta & Acta)',
    'estatisticas-aproveitamento': 'Estatística do Aproveitamento Pedagógico Escolar',
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
  if (viewId === 'director-turma') carregarPainelDirectorTurma();
  if (viewId === 'estatisticas-aproveitamento') carregarEstatisticasAproveitamento();
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
                <!-- Botão Entrar como Escola -->
                <button class="btn btn-outline-dark" title="Entrar como Escola (Mudar de Tenant)" onclick="alternarEscolaSuperAdmin('${e.id}')">
                  <i class="bi bi-box-arrow-in-right"></i> Entrar
                </button>
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
                <!-- Botão Descarregar Extrato / Contrato -->
                <button class="btn btn-outline-info" title="Descarregar Extrato / Contrato da Escola" onclick="descarregarExtratoEscolaSuperAdmin('${e.id}')">
                  <i class="bi bi-file-earmark-pdf"></i>
                </button>
                <!-- Botão Eliminar Escola (Exclusivo SuperAdmin) -->
                <button class="btn btn-outline-danger" title="Eliminar Escola Definitivamente" onclick="eliminarEscolaSuperAdmin('${e.id}', '${e.nome}')">
                  <i class="bi bi-trash"></i>
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
        const adminData = res.data?.adminUser;
        const msg = adminData 
          ? `Escola cadastrada com sucesso no SIGE!\n\nCREDENCIAIS DO ADMINISTRADOR DA ESCOLA:\nNome: ${adminData.nome}\nE-mail: ${adminData.email}\nSenha: ${body.adminSenha || '123456'}\n\nGuarde e forneça estas credenciais à Direcção da Escola.`
          : 'Escola cadastrada com sucesso no SIGE!';
        alert(msg);
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
            <button class="btn btn-sm btn-outline-primary me-1" onclick="modalEditarAluno('${a.id}')" title="Editar Dados"><i class="bi bi-pencil"></i></button>
            <button class="btn btn-sm btn-outline-warning me-1" onclick="modalTransferirAluno('${a.id}')" title="Transferir de Turma"><i class="bi bi-arrow-left-right"></i></button>
            <button class="btn btn-sm btn-outline-danger" onclick="excluirAluno('${a.id}')" title="Eliminar"><i class="bi bi-trash"></i></button>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

async function modalEditarAluno(id) {
  try {
    const res = await apiFetch(`/api/v1/alunos/${id}`);
    if (!res.success) return alert('Aluno não encontrado');
    const a = res.data;
    const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
    const opcoesTurmas = (turmasRes.data || []).map(t => 
      `<option value="${t.id}" ${t.id === a.turma_id ? 'selected' : ''}>${t.nome} (${t.grau_ano})</option>`
    ).join('');
    const optProvincias = (state.geografia.provincias || []).map(p => 
      `<option value="${p}" ${p === a.provincia ? 'selected' : ''}>${p}</option>`
    ).join('');
    const distritos = state.geografia.distritos[a.provincia] || [];
    const optDistritos = distritos.map(d => 
      `<option value="${d}" ${d === a.distrito ? 'selected' : ''}>${d}</option>`
    ).join('');

    const dtNasc = a.data_nascimento ? a.data_nascimento.split('T')[0] : '';

    abrirModal('Editar Dados do Aluno', `
      <form id="formModalEditarAluno">
        <div class="row g-3">
          <div class="col-md-8">
            <label class="form-label small fw-semibold">Nome Completo</label>
            <input type="text" id="meNome" class="form-control" required value="${a.nome || ''}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Apelido</label>
            <input type="text" id="meApelido" class="form-control" value="${a.apelido || ''}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Data de Nascimento</label>
            <input type="date" id="meNasc" class="form-control" required value="${dtNasc}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Género</label>
            <select id="meGenero" class="form-select">
              <option value="M" ${a.genero === 'M' ? 'selected' : ''}>Masculino</option>
              <option value="F" ${a.genero === 'F' ? 'selected' : ''}>Feminino</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Turma</label>
            <select id="meTurma" class="form-select">
              <option value="">(Sem turma)</option>
              ${opcoesTurmas}
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Tipo Documento</label>
            <select id="meTipoDoc" class="form-select">
              <option value="BI" ${a.tipo_documento === 'BI' ? 'selected' : ''}>BI</option>
              <option value="DIRE" ${a.tipo_documento === 'DIRE' ? 'selected' : ''}>DIRE</option>
              <option value="PASSAPORTE" ${a.tipo_documento === 'PASSAPORTE' ? 'selected' : ''}>Passaporte</option>
              <option value="CEDULA" ${a.tipo_documento === 'CEDULA' ? 'selected' : ''}>Cédula</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Nº Documento</label>
            <input type="text" id="meNumDoc" class="form-control" value="${a.numero_documento || ''}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">NUIT</label>
            <input type="text" id="meNUIT" class="form-control" value="${a.nuit || ''}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Província</label>
            <select id="meProvincia" class="form-select" onchange="atualizarDistritosEditarAluno(this.value)">
              <option value="">Selecione</option>
              ${optProvincias}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Distrito</label>
            <select id="meDistrito" class="form-select">
              ${optDistritos || '<option value="">Selecione primeiro a província</option>'}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Nome do Pai</label>
            <input type="text" id="mePai" class="form-control" value="${a.pai || ''}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Nome da Mãe</label>
            <input type="text" id="meMae" class="form-control" value="${a.mae || ''}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Encarregado</label>
            <input type="text" id="meResp" class="form-control" value="${a.nome_responsavel || ''}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Contacto Encarregado</label>
            <input type="text" id="meTelResp" class="form-control" value="${a.contato_responsavel || ''}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Estado do Aluno</label>
            <select id="meStatus" class="form-select">
              <option value="ATIVO" ${a.status === 'ATIVO' ? 'selected' : ''}>ATIVO</option>
              <option value="INATIVO" ${a.status === 'INATIVO' ? 'selected' : ''}>INATIVO</option>
              <option value="TRANSFERIDO" ${a.status === 'TRANSFERIDO' ? 'selected' : ''}>TRANSFERIDO</option>
              <option value="EVADIDO" ${a.status === 'EVADIDO' ? 'selected' : ''}>EVADIDO</option>
            </select>
          </div>
        </div>
        <button type="submit" class="btn btn-primary w-100 mt-4"><i class="bi bi-check2-circle me-1"></i> Guardar Alterações do Aluno</button>
      </form>
    `);

    document.getElementById('formModalEditarAluno').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const body = {
          nome: document.getElementById('meNome').value,
          apelido: document.getElementById('meApelido').value || null,
          data_nascimento: document.getElementById('meNasc').value,
          genero: document.getElementById('meGenero').value,
          turma_id: document.getElementById('meTurma').value || null,
          tipo_documento: document.getElementById('meTipoDoc').value,
          numero_documento: document.getElementById('meNumDoc').value || null,
          nuit: document.getElementById('meNUIT').value || null,
          provincia: document.getElementById('meProvincia').value || null,
          distrito: document.getElementById('meDistrito').value || null,
          pai: document.getElementById('mePai').value || null,
          mae: document.getElementById('meMae').value || null,
          nome_responsavel: document.getElementById('meResp').value || null,
          contato_responsavel: document.getElementById('meTelResp').value || null,
          status: document.getElementById('meStatus').value
        };

        const resUp = await apiFetch(`/api/v1/alunos/${id}`, {
          method: 'PUT',
          body: JSON.stringify(body)
        });
        if (resUp.success) {
          alert('Dados do aluno actualizados com sucesso!');
          fecharModal();
          carregarAlunos();
        }
      } catch (err) {
        alert(err.message || 'Erro ao actualizar dados do aluno');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados do aluno');
  }
}

function atualizarDistritosEditarAluno(provincia) {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('meDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => `<option value="${d}">${d}</option>`).join('');
  }
}

async function modalTransferirAluno(id) {
  try {
    const res = await apiFetch(`/api/v1/alunos/${id}`);
    if (!res.success) return alert('Aluno não encontrado');
    const a = res.data;
    const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
    const opcoesTurmas = (turmasRes.data || []).map(t => 
      `<option value="${t.id}" ${t.id === a.turma_id ? 'disabled' : ''}>${t.nome} (${t.grau_ano} - ${t.turno || 'Diurno'})${t.id === a.turma_id ? ' — Turma Actual' : ''}</option>`
    ).join('');

    abrirModal('Transferência de Turma do Aluno', `
      <form id="formModalTransferirAluno">
        <div class="alert alert-info py-2 small mb-3">
          Aluno: <strong>${a.nome} ${a.apelido || ''}</strong> (Matrícula: <code>${a.matricula}</code>)<br>
          Turma Actual: <strong>${a.turma ? a.turma.nome + ' (' + a.turma.grau_ano + ')' : 'Sem Turma'}</strong>
        </div>
        <div class="mb-3">
          <label class="form-label small fw-semibold">Nova Turma de Destino</label>
          <select id="mtNovaTurma" class="form-select" required>
            <option value="">Selecione a nova turma...</option>
            ${opcoesTurmas}
          </select>
        </div>
        <button type="submit" class="btn btn-warning w-100"><i class="bi bi-arrow-left-right me-1"></i> Confirmar Transferência de Turma</button>
      </form>
    `);

    document.getElementById('formModalTransferirAluno').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const novaTurmaId = document.getElementById('mtNovaTurma').value;
        const resTr = await apiFetch(`/api/v1/alunos/${id}/transferir`, {
          method: 'PUT',
          body: JSON.stringify({ novaTurmaId })
        });
        if (resTr.success) {
          alert('Aluno transferido com sucesso para a nova turma!');
          fecharModal();
          carregarAlunos();
        }
      } catch (err) {
        alert(err.message || 'Erro ao transferir aluno');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados do aluno');
  }
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
function filtrarDisciplinasClasse(classe) {
  state.filtroDisciplinaClasse = classe;
  const pills = document.querySelectorAll('#pillsDisciplinasClasses .nav-link');
  pills.forEach(p => {
    if ((!classe && p.textContent.trim() === 'Todas') || p.textContent.trim() === classe) {
      p.classList.add('active');
    } else {
      p.classList.remove('active');
    }
  });
  atualizarPillsAreasParaClasse(classe);
  carregarDisciplinas();
}

function filtrarDisciplinasArea(area) {
  state.filtroDisciplinaArea = area;
  const btns = document.querySelectorAll('#pillsDisciplinasAreas button');
  btns.forEach(b => {
    if ((!area && b.textContent.includes('Todas')) || b.textContent.trim() === area) {
      b.className = 'btn btn-sm btn-primary py-1 px-2 small';
    } else {
      b.className = 'btn btn-sm btn-outline-secondary py-1 px-2 small';
    }
  });
  carregarDisciplinas();
}

function atualizarPillsAreasParaClasse(classe) {
  const container = document.getElementById('pillsDisciplinasAreas');
  if (!container) return;

  let areas = ['Ensino Geral'];
  if (classe.includes('11') || classe.includes('12')) {
    areas = ['Ciências com Biologia', 'Ciências com Desenho', 'Letras com Geografia', 'Letras com História', 'Ensino Geral'];
  } else if (classe.includes('7') || classe.includes('8') || classe.includes('9') || classe.includes('10')) {
    areas = ['Ensino Geral', 'Área de Comunicação', 'Área de Ciências Naturais'];
  }

  // Carregar áreas personalizadas salvas
  const savedCustom = localStorage.getItem('sige_custom_areas_' + (classe || 'geral'));
  if (savedCustom) {
    try {
      const parsed = JSON.parse(savedCustom);
      areas = Array.from(new Set([...areas, ...parsed]));
    } catch (e) {}
  }

  const activeArea = state.filtroDisciplinaArea || '';
  let htmlBtns = `<button class="btn btn-sm ${!activeArea ? 'btn-primary' : 'btn-outline-secondary'} py-1 px-2 small" onclick="filtrarDisciplinasArea('')">Todas as Áreas</button>`;
  areas.forEach(a => {
    const isAct = activeArea === a;
    htmlBtns += `<button class="btn btn-sm ${isAct ? 'btn-primary' : 'btn-outline-secondary'} py-1 px-2 small" onclick="filtrarDisciplinasArea('${a}')">${a}</button>`;
  });

  container.innerHTML = htmlBtns;
}

function modalNovaSeccaoArea() {
  const classeAtiva = state.filtroDisciplinaClasse || '10ª Classe';
  abrirModal('Cadastrar Secção / Área de Estudo da Classe', `
    <form id="formModalSeccaoArea">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Classe Correspondente</label>
        <input type="text" id="msaClasse" class="form-control" value="${classeAtiva}" readonly>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nome da Secção ou Área de Estudo *</label>
        <input type="text" id="msaNome" class="form-control" placeholder="Ex: Secção de Ciências / Área de Engenharia" required>
        <small class="text-muted">Ex: Ciências com Biologia, Letras com Geografia, Ensino Comercial, etc.</small>
      </div>
      <button type="submit" class="btn btn-primary w-100 fw-semibold">
        <i class="bi bi-plus-circle me-1"></i> Criar Secção / Área na Classe
      </button>
    </form>
  `);

  document.getElementById('formModalSeccaoArea').addEventListener('submit', (e) => {
    e.preventDefault();
    const nomeArea = document.getElementById('msaNome').value.trim();
    if (!nomeArea) return;

    const chave = 'sige_custom_areas_' + (classeAtiva || 'geral');
    const existingRaw = localStorage.getItem(chave);
    const existing = existingRaw ? JSON.parse(existingRaw) : [];
    existing.push(nomeArea);
    localStorage.setItem(chave, JSON.stringify(existing));

    fecharModal();
    filtrarDisciplinasClasse(classeAtiva);
    filtrarDisciplinasArea(nomeArea);
    alert(`Secção / Área de Estudo "${nomeArea}" cadastrada com sucesso para a ${classeAtiva}!`);
  });
}

async function carregarDisciplinas() {
  try {
    const qParams = new URLSearchParams();
    if (state.filtroDisciplinaClasse) qParams.set('classe', state.filtroDisciplinaClasse);
    if (state.filtroDisciplinaArea) qParams.set('area', state.filtroDisciplinaArea);
    const url = '/api/v1/disciplinas' + (qParams.toString() ? '?' + qParams.toString() : '');
    const [resD, resStats] = await Promise.all([
      apiFetch(url),
      apiFetch('/api/v1/disciplinas/stats')
    ]);

    if (resD.success) {
      const tbody = document.getElementById('tabelaDisciplinas');
      if (resD.data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhuma disciplina cadastrada para este filtro de classe.</td></tr>';
      } else {
        tbody.innerHTML = resD.data.map(d => `
          <tr>
            <td><code>${d.codigo}</code></td>
            <td><strong>${d.nome}</strong></td>
            <td><span class="badge bg-secondary">${d.classe || '10ª Classe'}</span></td>
            <td><small class="text-muted">${d.area || 'Geral'}</small></td>
            <td>${d.carga_horaria} horas/semana</td>
            <td>${d.ano_letivo}</td>
          </tr>
        `).join('');
      }
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
      <div class="row g-3">
        <div class="col-md-8">
          <label class="form-label small fw-semibold">Nome da Disciplina</label>
          <input type="text" id="mdNome" class="form-control" required placeholder="Ex: Matemática">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Código Curricular</label>
          <input type="text" id="mdCodigo" class="form-control" required placeholder="Ex: MAT-10">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Grupo de Classe *</label>
          <select id="mdClasse" class="form-select" required>
            <option value="7ª Classe" ${state.filtroDisciplinaClasse === '7ª Classe' ? 'selected' : ''}>7ª Classe</option>
            <option value="8ª Classe" ${state.filtroDisciplinaClasse === '8ª Classe' ? 'selected' : ''}>8ª Classe</option>
            <option value="9ª Classe" ${state.filtroDisciplinaClasse === '9ª Classe' ? 'selected' : ''}>9ª Classe</option>
            <option value="10ª Classe" ${(!state.filtroDisciplinaClasse || state.filtroDisciplinaClasse === '10ª Classe') ? 'selected' : ''}>10ª Classe</option>
            <option value="11ª Classe" ${state.filtroDisciplinaClasse === '11ª Classe' ? 'selected' : ''}>11ª Classe</option>
            <option value="12ª Classe" ${state.filtroDisciplinaClasse === '12ª Classe' ? 'selected' : ''}>12ª Classe</option>
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Secção / Área de Estudo *</label>
          <input type="text" id="mdArea" class="form-control" list="listaAreasSugeridas" value="${state.filtroDisciplinaArea || 'Geral'}" required placeholder="Ex: Ciências com Biologia">
          <datalist id="listaAreasSugeridas">
            <option value="Geral">Ensino Geral</option>
            <option value="Ciências com Biologia">Ciências com Biologia</option>
            <option value="Ciências com Desenho">Ciências com Desenho</option>
            <option value="Letras com Geografia">Letras com Geografia</option>
            <option value="Letras com História">Letras com História</option>
          </datalist>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Carga Horária (Aulas/Semana)</label>
          <input type="number" id="mdCarga" class="form-control" value="5" min="1" max="20" required>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Ano Lectivo</label>
          <input type="text" id="mdAnoLetivo" class="form-control" value="2026" required>
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4"><i class="bi bi-plus-circle me-1"></i> Criar Disciplina no Plano Curricular</button>
    </form>
  `);

  document.getElementById('formModalDisc').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const body = {
        nome: document.getElementById('mdNome').value,
        codigo: document.getElementById('mdCodigo').value,
        classe: document.getElementById('mdClasse').value,
        area: document.getElementById('mdArea').value,
        carga_horaria: Number(document.getElementById('mdCarga').value),
        ano_letivo: document.getElementById('mdAnoLetivo').value || '2026'
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
      alert(err.message || 'Erro ao criar disciplina');
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
          <td class="text-start" style="cursor: pointer;" onclick="modalSalvarNotaCaderneta('${a.alunoId}')" title="Clique para lançar avaliações deste aluno"><strong class="text-primary">${a.nome}</strong> <i class="bi bi-pencil-square text-muted ms-1 small"></i></td>
          <td class="text-start">${a.apelido || '-'}</td>
          <td><span class="badge ${a.genero === 'F' ? 'bg-info text-dark' : 'bg-secondary'}">${a.genero}</span></td>
          <!-- 1º Trimestre -->
          <td>${formatVal(a.t1.t1)}</td>
          <td>${formatVal(a.t1.t2)}</td>
          <td>${formatVal(a.t1.t3)}</td>
          <td class="bg-light">${formatVal(a.t1.map)}</td>
          <td>${formatVal(a.t1.mas ?? a.t1.mac3)}</td>
          <td>${formatVal(a.t1.at)}</td>
          <td class="bg-light fw-bold fs-6">${formatVal(a.t1.mt, true)}</td>
          <td><small>${a.t1.comportamento || 'S'}</small></td>
          <td><span class="badge bg-light text-dark border">${a.t1.anotacao || '-'}</span></td>
          <!-- 2º Trimestre -->
          <td>${formatVal(a.t2.t1)}</td>
          <td>${formatVal(a.t2.t2)}</td>
          <td>${formatVal(a.t2.t3)}</td>
          <td class="bg-light">${formatVal(a.t2.map)}</td>
          <td>${formatVal(a.t2.mas ?? a.t2.mac3)}</td>
          <td>${formatVal(a.t2.at)}</td>
          <td class="bg-light fw-bold fs-6">${formatVal(a.t2.mt, true)}</td>
          <td><small>${a.t2.comportamento || 'S'}</small></td>
          <td><span class="badge bg-light text-dark border">${a.t2.anotacao || '-'}</span></td>
          <!-- 3º Trimestre -->
          <td>${formatVal(a.t3.t1)}</td>
          <td>${formatVal(a.t3.t2)}</td>
          <td>${formatVal(a.t3.t3)}</td>
          <td class="bg-light">${formatVal(a.t3.map)}</td>
          <td>${formatVal(a.t3.mas ?? a.t3.mac3)}</td>
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
        't1_t1', 't1_t2', 't1_t3', 't1_map', 't1_mas', 't1_at', 't1_mt', null, null,
        't2_t1', 't2_t2', 't2_t3', 't2_map', 't2_mas', 't2_at', 't2_mt', null, null,
        't3_t1', 't3_t2', 't3_t3', 't3_map', 't3_mas', 't3_at', 't3_mt', null, null,
        'mfd'
      ];

      const renderCelulasEstatistica = (extrator) => {
        return chavesColunas.map(key => {
          if (!key) return '<td class="bg-light text-muted">-</td>';
          const colStat = stats[key] || stats[key.replace('_mas', '_mac3')];
          if (!colStat) return '<td>-</td>';
          return `<td>${extrator(colStat)}</td>`;
        }).join('');
      };

      tfoot.innerHTML = `
        <!-- 1. Avaliados: M, F, M+F (3 Linhas Separadas Oficial Imagem 2) -->
        <tr>
          <td rowspan="3" class="text-start ps-2 fw-bold align-middle bg-light border-end">Avaliados</td>
          <td colspan="3" class="fw-bold bg-light">M</td>
          ${renderCelulasEstatistica(s => s.avaliados ? (s.avaliados.h ?? s.avaliados.m ?? 0) : '-')}
        </tr>
        <tr>
          <td colspan="3" class="fw-bold bg-light">F</td>
          ${renderCelulasEstatistica(s => s.avaliados ? (s.avaliados.f ?? s.avaliados.m ?? 0) : '-')}
        </tr>
        <tr class="table-secondary">
          <td colspan="3" class="fw-bold">M+F</td>
          ${renderCelulasEstatistica(s => s.avaliados ? `<strong>${s.avaliados.total}</strong>` : '-')}
        </tr>

        <!-- 2. Positivos: M, F, M+F (3 Linhas Separadas Oficial Imagem 2) -->
        <tr>
          <td rowspan="3" class="text-start ps-2 fw-bold align-middle text-success bg-light border-end">Positivos</td>
          <td colspan="3" class="fw-semibold text-success bg-light">M</td>
          ${renderCelulasEstatistica(s => s.positivas ? (s.positivas.h ?? 0) : '-')}
        </tr>
        <tr>
          <td colspan="3" class="fw-semibold text-success bg-light">F</td>
          ${renderCelulasEstatistica(s => s.positivas ? (s.positivas.m ?? 0) : '-')}
        </tr>
        <tr class="table-success bg-opacity-25">
          <td colspan="3" class="fw-bold text-success">M+F</td>
          ${renderCelulasEstatistica(s => s.positivas ? `<strong>${s.positivas.total}</strong>` : '-')}
        </tr>

        <!-- 3. % Positivos: M, F, M+F (3 Linhas Separadas Oficial Imagem 2) -->
        <tr>
          <td rowspan="3" class="text-start ps-2 fw-bold align-middle text-success bg-light border-end">% Positivos</td>
          <td colspan="3" class="fw-semibold text-success bg-light">M</td>
          ${renderCelulasEstatistica(s => s.positivas ? (s.positivas.pctH !== undefined ? `${s.positivas.pctH}%` : '-') : '-')}
        </tr>
        <tr>
          <td colspan="3" class="fw-semibold text-success bg-light">F</td>
          ${renderCelulasEstatistica(s => s.positivas ? (s.positivas.pctM !== undefined ? `${s.positivas.pctM}%` : '-') : '-')}
        </tr>
        <tr class="table-success bg-opacity-25">
          <td colspan="3" class="fw-bold text-success">M+F</td>
          ${renderCelulasEstatistica(s => s.positivas ? `<strong>${s.positivas.pct}%</strong>` : '-')}
        </tr>

        <!-- 4. Negativos: M, F, M+F (3 Linhas Separadas Oficial Imagem 2) -->
        <tr>
          <td rowspan="3" class="text-start ps-2 fw-bold align-middle text-danger bg-light border-end">Negativos</td>
          <td colspan="3" class="fw-semibold text-danger bg-light">M</td>
          ${renderCelulasEstatistica(s => s.negativas ? (s.negativas.h ?? 0) : '-')}
        </tr>
        <tr>
          <td colspan="3" class="fw-semibold text-danger bg-light">F</td>
          ${renderCelulasEstatistica(s => s.negativas ? (s.negativas.m ?? 0) : '-')}
        </tr>
        <tr class="table-danger bg-opacity-25">
          <td colspan="3" class="fw-bold text-danger">M+F</td>
          ${renderCelulasEstatistica(s => s.negativas ? `<strong>${s.negativas.total}</strong>` : '-')}
        </tr>

        <!-- 5. % Negativos: M, F, M+F (3 Linhas Separadas Oficial Imagem 2) -->
        <tr>
          <td rowspan="3" class="text-start ps-2 fw-bold align-middle text-danger bg-light border-end">% Negativos</td>
          <td colspan="3" class="fw-semibold text-danger bg-light">M</td>
          ${renderCelulasEstatistica(s => s.negativas ? (s.negativas.pctH !== undefined ? `${s.negativas.pctH}%` : '-') : '-')}
        </tr>
        <tr>
          <td colspan="3" class="fw-semibold text-danger bg-light">F</td>
          ${renderCelulasEstatistica(s => s.negativas ? (s.negativas.pctM !== undefined ? `${s.negativas.pctM}%` : '-') : '-')}
        </tr>
        <tr class="table-danger bg-opacity-25">
          <td colspan="3" class="fw-bold text-danger">M+F</td>
          ${renderCelulasEstatistica(s => s.negativas ? `<strong>${s.negativas.pct}%</strong>` : '-')}
        </tr>

        <!-- 6. Faixas oficiais (0 a 9,4 | 9,5 a 13,4 | 13,5 a 16,4 | 16,5 a 18,4 | 18,5 a 20) -->
        <tr>
          <td colspan="4" class="text-start ps-2 fw-semibold bg-light">0 a 9,4</td>
          ${renderCelulasEstatistica(s => s.faixas ? s.faixas.f0_94.total : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-2 fw-semibold bg-light">9,5 a 13,4</td>
          ${renderCelulasEstatistica(s => s.faixas ? s.faixas.f95_134.total : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-2 fw-semibold bg-light">13,5 a 16,4</td>
          ${renderCelulasEstatistica(s => s.faixas ? s.faixas.f135_164.total : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-2 fw-semibold bg-light">16,5 a 18,4</td>
          ${renderCelulasEstatistica(s => s.faixas ? s.faixas.f165_184.total : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-2 fw-semibold bg-light">18,5 a 20</td>
          ${renderCelulasEstatistica(s => s.faixas ? s.faixas.f185_20.total : '-')}
        </tr>

        <!-- 7. Média da Coluna -->
        <tr class="table-primary fw-bold">
          <td colspan="4" class="text-start ps-2">Média da Coluna</td>
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

async function modalSalvarNotaCaderneta(alunoIdPreSelecionado = null) {
  if (!state.alocacaoAtualId) return alert('Selecione uma turma e disciplina');

  const periodo = document.getElementById('cadernetaPeriodoSelect')?.value || '1_TRIMESTRE';
  const resCaderneta = await apiFetch(`/api/v1/professores/caderneta/${state.alocacaoAtualId}/completa`);
  if (!resCaderneta.success || !resCaderneta.data.alunos?.length) {
    return alert('Não há alunos nesta turma');
  }

  const optAlunos = resCaderneta.data.alunos.map(item => {
    const isSelected = alunoIdPreSelecionado && item.alunoId === alunoIdPreSelecionado ? 'selected' : '';
    return `<option value="${item.alunoId}" ${isSelected}>${item.nome} ${item.apelido || ''}</option>`;
  }).join('');

  const listaAnotacoesPadrao = [
    { codigo: 'D', significado: 'Desistiu' },
    { codigo: 'T', significado: 'Transferido' },
    { codigo: 'VT', significado: 'Vem Transferido' },
    { codigo: 'F', significado: 'Faleceu' },
    { codigo: 'AM', significado: 'Anulou Matrícula' },
    { codigo: 'PPF', significado: 'Perdeu o Ano por Faltas' },
    { codigo: 'PDF', significado: 'Perdeu Direito por Faltas' }
  ];
  const anotacoesDisponiveis = (state.geografia.anotacoes && state.geografia.anotacoes.length > 0)
    ? state.geografia.anotacoes
    : listaAnotacoesPadrao;
  const optAnotacoes = anotacoesDisponiveis.map(a => 
    `<option value="${a.codigo}">${a.codigo} — ${a.significado || a.nome || a.codigo}</option>`
  ).join('');

  abrirModal('Lançar Avaliações do Aluno (Oficial MINEDH)', `
    <form id="formModalLancamentoNota">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Aluno Seleccionado</label>
        <select id="mlnAluno" class="form-select" required>${optAlunos}</select>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-md-6">
          <label class="form-label small fw-semibold text-primary">1ª ACS (Obrigatória, 0 a 20) *</label>
          <input type="number" step="any" min="0" max="20" id="mlnT1" class="form-control" value="12" required oninput="calcularPrevisoesCadernetaModal()">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold text-primary">2ª ACS (Obrigatória, 0 a 20) *</label>
          <input type="number" step="any" min="0" max="20" id="mlnT2" class="form-control" value="13" required oninput="calcularPrevisoesCadernetaModal()">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold text-muted">3ª ACS (Opcional, 0 a 20)</label>
          <input type="number" step="any" min="0" max="20" id="mlnT3" class="form-control" placeholder="Opcional" oninput="calcularPrevisoesCadernetaModal()">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold text-muted">MAP - Aulas Práticas (Opcional, 0 a 20)</label>
          <input type="number" step="any" min="0" max="20" id="mlnTrabalho" class="form-control" placeholder="Opcional" oninput="calcularPrevisoesCadernetaModal()">
        </div>
        <div class="col-md-12">
          <label class="form-label small fw-semibold text-primary">AT - Avaliação Trimestral (Obrigatória, 0 a 20) *</label>
          <input type="number" step="any" min="0" max="20" id="mlnAT" class="form-control" value="12" required oninput="calcularPrevisoesCadernetaModal()">
        </div>
      </div>

      <!-- Caixa Informativa de Médias Calculadas em Tempo Real -->
      <div class="p-3 bg-light rounded border mb-3">
        <div class="row text-center">
          <div class="col-4">
            <small class="text-muted d-block">MAS (Média ACS/MAP)</small>
            <strong id="previewMlnMAS" class="text-primary fs-6">12.5</strong>
          </div>
          <div class="col-4">
            <small class="text-muted d-block">MT (Média Trimestre)</small>
            <strong id="previewMlnMT" class="text-success fs-6">12</strong>
          </div>
          <div class="col-4">
            <small class="text-muted d-block">Comportamento</small>
            <strong id="previewMlnComp" class="text-dark fs-6">S (Suficiente)</strong>
          </div>
        </div>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Faltas no Trimestre</label>
          <input type="number" id="mlnFaltas" class="form-control" value="0" min="0">
        </div>
        <div class="col-md-8">
          <label class="form-label small fw-semibold">Anotação Especial do Aluno</label>
          <select id="mlnAnotacao" class="form-select">
            <option value="">(Nenhuma)</option>
            ${optAnotacoes}
          </select>
        </div>
      </div>

      <button type="submit" class="btn btn-primary w-100">
        <i class="bi bi-check-circle me-1"></i> Gravar Avaliação no Trimestre
      </button>
    </form>
  `);

  calcularPrevisoesCadernetaModal();

  document.getElementById('formModalLancamentoNota').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const aloc = state.alocacoesDocente.find(a => a.id === state.alocacaoAtualId);
      const vT1 = parseFloat(document.getElementById('mlnT1').value);
      const vT2 = parseFloat(document.getElementById('mlnT2').value);
      const vT3 = document.getElementById('mlnT3').value ? parseFloat(document.getElementById('mlnT3').value) : null;
      const vMAP = document.getElementById('mlnTrabalho').value ? parseFloat(document.getElementById('mlnTrabalho').value) : null;
      const vAT = parseFloat(document.getElementById('mlnAT').value);

      // Calcular médias e comportamento
      const testes = [vT1, vT2];
      if (vT3 !== null && !isNaN(vT3)) testes.push(vT3);
      if (vMAP !== null && !isNaN(vMAP)) testes.push(vMAP);
      const masVal = testes.reduce((a, b) => a + b, 0) / testes.length;
      const mtVal = Math.round((2 * masVal + vAT) / 3);

      let compAuto = 'S';
      if (mtVal < 9.5) compAuto = 'NS';
      else if (mtVal <= 13.4) compAuto = 'S';
      else if (mtVal <= 16.4) compAuto = 'B';
      else if (mtVal <= 18.4) compAuto = 'MB';
      else compAuto = 'E';

      const body = {
        aluno_id: document.getElementById('mlnAluno').value,
        turma_id: aloc.turma_id,
        disciplina_id: aloc.disciplina_id,
        periodo: periodo,
        teste1: vT1,
        teste2: vT2,
        teste3: vT3 !== null ? vT3 : undefined,
        trabalho: vMAP !== null ? vMAP : undefined,
        avaliacao_trimestral: vAT,
        faltas: Number(document.getElementById('mlnFaltas').value) || 0,
        anotacao: document.getElementById('mlnAnotacao').value || undefined,
        comportamento: compAuto
      };

      const res = await apiFetch('/api/v1/notas', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success) {
        fecharModal();
        await carregarCadernetaDocente();
        // Sincronizar pauta e acta em segundo plano se turmaId corresponder
        if (typeof alternarVisualizacaoPautaTurma === 'function') {
          alternarVisualizacaoPautaTurma().catch(() => {});
        }
      }
    } catch (err) {
      alert(err.message || 'Erro ao lançar avaliação');
    }
  });
}

function calcularPrevisoesCadernetaModal() {
  const t1 = parseFloat(document.getElementById('mlnT1')?.value || '0');
  const t2 = parseFloat(document.getElementById('mlnT2')?.value || '0');
  const t3Val = document.getElementById('mlnT3')?.value;
  const t3 = t3Val ? parseFloat(t3Val) : null;
  const mapVal = document.getElementById('mlnTrabalho')?.value;
  const map = mapVal ? parseFloat(mapVal) : null;
  const at = parseFloat(document.getElementById('mlnAT')?.value || '0');

  const avaliacoes = [t1, t2];
  if (t3 !== null && !isNaN(t3)) avaliacoes.push(t3);
  if (map !== null && !isNaN(map)) avaliacoes.push(map);

  const mas = Number((avaliacoes.reduce((a, b) => a + b, 0) / avaliacoes.length).toFixed(1));
  const mt = Math.round((2 * mas + at) / 3);

  let comp = 'S (Suficiente)';
  if (mt < 9.5) comp = 'NS (Não Suficiente)';
  else if (mt <= 13.4) comp = 'S (Suficiente)';
  else if (mt <= 16.4) comp = 'B (Bom)';
  else if (mt <= 18.4) comp = 'MB (Muito Bom)';
  else comp = 'E (Excelente)';

  if (document.getElementById('previewMlnMAS')) document.getElementById('previewMlnMAS').textContent = mas;
  if (document.getElementById('previewMlnMT')) document.getElementById('previewMlnMT').textContent = mt;
  if (document.getElementById('previewMlnComp')) document.getElementById('previewMlnComp').textContent = comp;
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
            <th colspan="4" class="bg-danger bg-opacity-10 text-danger fw-bold">CADEIRAS NEGATIVAS</th>
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
            <th style="font-size: 0.68rem;" class="bg-light fw-bold" title="Cadeiras Negativas no Fim do Ano">Cadeiras Neg.</th>
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
    const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
    const cp = savedParamsRaw ? JSON.parse(savedParamsRaw) : {
      presidenteT1: 'Fernando José Mandamule',
      presidenteT2: 'Fernando José Mandamule',
      presidenteT3: '_________________',
      dataT1: '26/05/2026',
      dataT2: '01/09/2026',
      dataT3: '____/____/2026',
      horaInicioT1: '09',
      minInicioT1: '30',
      horaFimT1: '10',
      minFimT1: '00',
      horaInicioT2: '09',
      minInicioT2: '30',
      horaFimT2: '11',
      minFimT2: '00',
      horaInicioT3: '____',
      minInicioT3: '____',
      horaFimT3: '____',
      minFimT3: '____'
    };

    const qParams = new URLSearchParams(cp).toString();
    const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/acta?${qParams}`);
    if (!res.success) return;
    const d = res.data;

    const te = d.tabelaEfectivo;
    const ta = d.tabelaAproveitamento;

    const p1 = cp.presidenteT1 || d.conselho?.presidenteT1 || 'Fernando José Mandamule';
    const p2 = cp.presidenteT2 || d.conselho?.presidenteT2 || 'Fernando José Mandamule';
    const p3 = cp.presidenteT3 || d.conselho?.presidenteT3 || '_________________';

    const dt1 = cp.dataT1 || '26/05/2026';
    const dt2 = cp.dataT2 || '01/09/2026';
    const dt3 = cp.dataT3 || '____/____/2026';

    const hIni1 = cp.horaInicioT1 || '09';
    const mIni1 = cp.minInicioT1 || '30';
    const hFim1 = cp.horaFimT1 || '10';
    const mFim1 = cp.minFimT1 || '00';

    const hIni2 = cp.horaInicioT2 || '09';
    const mIni2 = cp.minInicioT2 || '30';
    const hFim2 = cp.horaFimT2 || '11';
    const mFim2 = cp.minFimT2 || '00';

    const hIni3 = cp.horaInicioT3 || '____';
    const mIni3 = cp.minInicioT3 || '____';
    const hFim3 = cp.horaFimT3 || '____';
    const mFim3 = cp.minFimT3 || '____';

    const textoProtocolar = `Sob presidência do senhor professor <strong>${p1}</strong> (Iº Trimestre); <strong>${p2}</strong> (IIº Trimestre); <strong>${p3}</strong> (IIIº Trimestre); director/substituto do director de turma <strong>${d.turma.nome}</strong> do grupo da <strong>${d.turma.grau_ano}</strong>, curso <strong>${d.turma.turno === 'NOITE' ? 'Nocturno' : 'Diurno'}</strong>, realizou-se o Conselho de Avaliação do Iº; IIº, IIIº, Trimestre no dia <strong>${dt1}</strong>; <strong>${dt2}</strong>; <strong>${dt3}</strong>, com início às <strong>${hIni1}</strong> horas e <strong>${mIni1}</strong> minutos e com término às <strong>${hFim1}</strong> horas e <strong>${mFim1}</strong> minutos (Iº Trim); <strong>${hIni2}</strong> horas e <strong>${mIni2}</strong> minutos e com término às <strong>${hFim2}</strong> horas e <strong>${mFim2}</strong> minutos (IIº Trim); <strong>${hIni3}</strong> horas e <strong>${mIni3}</strong> minutos e com término às <strong>${hFim3}</strong> horas e <strong>${mFim3}</strong> minutos (IIIº Trim). No final deste conselho colheram-se os resultados que abaixo vão discriminados de todos os membros que participaram:`;

    const tc = d.trimestresComNotas || { t1: true, t2: false, t3: false, fimAno: false };

    // Renderizador das Linhas da Tabela 1 (Efectivos e Movimento por Género)
    const renderTeLinhas = (categoria, chave) => {
      return ['H', 'M', 'HM'].map((gen, gIdx) => {
        const prop = gen === 'H' ? 'h' : (gen === 'M' ? 'm' : 'hm');
        const pctProp = gen === 'H' ? 'pctH' : (gen === 'M' ? 'pctM' : 'pct');

        const vT1 = tc.t1 && te.t1[chave] ? te.t1[chave][prop] : (tc.t1 ? 0 : '-');
        const pT1 = tc.t1 && te.t1[chave] && te.t1[chave][pctProp] !== undefined ? `${te.t1[chave][pctProp]}%` : '-';

        const vT2 = tc.t2 && te.t2[chave] ? te.t2[chave][prop] : (tc.t2 ? 0 : '-');
        const pT2 = tc.t2 && te.t2[chave] && te.t2[chave][pctProp] !== undefined ? `${te.t2[chave][pctProp]}%` : '-';

        const vT3 = tc.t3 && te.t3[chave] ? te.t3[chave][prop] : (tc.t3 ? 0 : '-');
        const pT3 = tc.t3 && te.t3[chave] && te.t3[chave][pctProp] !== undefined ? `${te.t3[chave][pctProp]}%` : '-';

        const vFA = tc.fimAno && te.fimAno[chave] ? te.fimAno[chave][prop] : (tc.fimAno ? 0 : '-');
        const pFA = tc.fimAno && te.fimAno[chave] && te.fimAno[chave][pctProp] !== undefined ? `${te.fimAno[chave][pctProp]}%` : '-';

        const tdCat = gIdx === 0 ? `<td rowspan="3" class="text-start ps-2 fw-bold align-middle bg-light border-end">${categoria}</td>` : '';
        const bgCls = gen === 'HM' ? 'table-light fw-bold' : '';

        return `
          <tr class="${bgCls}">
            ${tdCat}
            <td class="fw-semibold text-center">${gen}</td>
            <td>${vT1}</td><td class="text-muted small">${pT1}</td>
            <td>${vT2}</td><td class="text-muted small">${pT2}</td>
            <td>${vT3}</td><td class="text-muted small">${pT3}</td>
            <td>${vFA}</td><td class="text-muted small">${pFA}</td>
          </tr>
        `;
      }).join('');
    };

    // Renderizador das Linhas da Tabela 2 (Aproveitamento Pedagógico por Género)
    const renderTaLinhas = (classificacao, chave, isAprov = false) => {
      return ['H', 'M', 'HM'].map((gen, gIdx) => {
        const prop = gen === 'H' ? 'h' : (gen === 'M' ? 'm' : 'hm');
        const pctProp = gen === 'H' ? 'pctH' : (gen === 'M' ? 'pctM' : 'pct');

        const vT1 = tc.t1 && ta.t1[chave] ? ta.t1[chave][prop] : (tc.t1 ? 0 : '-');
        const pT1 = tc.t1 && ta.t1[chave] && ta.t1[chave][pctProp] !== undefined ? `${ta.t1[chave][pctProp]}%` : (tc.t1 && chave === 'avaliados' ? '100%' : '-');

        const vT2 = tc.t2 && ta.t2[chave] ? ta.t2[chave][prop] : (tc.t2 ? 0 : '-');
        const pT2 = tc.t2 && ta.t2[chave] && ta.t2[chave][pctProp] !== undefined ? `${ta.t2[chave][pctProp]}%` : (tc.t2 && chave === 'avaliados' ? '100%' : '-');

        const vT3 = tc.t3 && ta.t3[chave] ? ta.t3[chave][prop] : (tc.t3 ? 0 : '-');
        const pT3 = tc.t3 && ta.t3[chave] && ta.t3[chave][pctProp] !== undefined ? `${ta.t3[chave][pctProp]}%` : (tc.t3 && chave === 'avaliados' ? '100%' : '-');

        const vFA = tc.fimAno && ta.fimAno[chave] ? ta.fimAno[chave][prop] : (tc.fimAno ? 0 : '-');
        const pFA = tc.fimAno && ta.fimAno[chave] && ta.fimAno[chave][pctProp] !== undefined ? `${ta.fimAno[chave][pctProp]}%` : (tc.fimAno && chave === 'avaliados' ? '100%' : '-');

        // Cálculo de Crescimento condicionado
        let c1_2 = '<span class="text-muted">-</span>';
        if (tc.t1 && tc.t2) {
          const nPT1 = ta.t1[chave] && ta.t1[chave][pctProp] ? Number(ta.t1[chave][pctProp]) : 0;
          const nPT2 = ta.t2[chave] && ta.t2[chave][pctProp] ? Number(ta.t2[chave][pctProp]) : 0;
          const dif1_2 = Number((nPT2 - nPT1).toFixed(1));
          c1_2 = dif1_2 > 0 ? `<span class="badge bg-success bg-opacity-25 text-success">+${dif1_2}% Subiu</span>` : (dif1_2 < 0 ? `<span class="badge bg-danger bg-opacity-25 text-danger">${dif1_2}% Desceu</span>` : '<span class="text-muted">0%</span>');
        }

        let c2_3 = '<span class="text-muted">-</span>';
        if (tc.t2 && tc.t3) {
          const nPT2 = ta.t2[chave] && ta.t2[chave][pctProp] ? Number(ta.t2[chave][pctProp]) : 0;
          const nPT3 = ta.t3[chave] && ta.t3[chave][pctProp] ? Number(ta.t3[chave][pctProp]) : 0;
          const dif2_3 = Number((nPT3 - nPT2).toFixed(1));
          c2_3 = dif2_3 > 0 ? `<span class="badge bg-success bg-opacity-25 text-success">+${dif2_3}% Subiu</span>` : (dif2_3 < 0 ? `<span class="badge bg-danger bg-opacity-25 text-danger">${dif2_3}% Desceu</span>` : '<span class="text-muted">0%</span>');
        }

        let cGlo = '<span class="text-muted">-</span>';
        if (tc.t1 && tc.fimAno) {
          const nPT1 = ta.t1[chave] && ta.t1[chave][pctProp] ? Number(ta.t1[chave][pctProp]) : 0;
          const nPFA = ta.fimAno[chave] && ta.fimAno[chave][pctProp] ? Number(ta.fimAno[chave][pctProp]) : 0;
          const difGlo = Number((nPFA - nPT1).toFixed(1));
          cGlo = difGlo > 0 ? `<span class="badge bg-success bg-opacity-25 text-success">+${difGlo}% Subiu</span>` : (difGlo < 0 ? `<span class="badge bg-danger bg-opacity-25 text-danger">${difGlo}% Desceu</span>` : '<span class="text-muted">0%</span>');
        }

        const tdCat = gIdx === 0 ? `<td rowspan="3" class="text-start ps-2 fw-bold align-middle bg-light border-end ${isAprov ? 'text-success' : ''}">${classificacao}</td>` : '';
        const bgCls = isAprov ? 'table-success bg-opacity-25 fw-bold' : (gen === 'HM' ? 'table-light fw-bold' : '');

        return `
          <tr class="${bgCls}">
            ${tdCat}
            <td class="fw-semibold text-center">${gen}</td>
            <td>${vT1}</td><td class="text-muted small">${pT1}</td>
            <td>${vT2}</td><td class="text-muted small">${pT2}</td>
            <td>${vT3}</td><td class="text-muted small">${pT3}</td>
            <td>${vFA}</td><td class="text-muted small">${pFA}</td>
            <td class="text-center small">${c1_2}</td>
            <td class="text-center small">${c2_3}</td>
            <td class="text-center small">${cGlo}</td>
          </tr>
        `;
      }).join('');
    };

    container.innerHTML = `
      <!-- Cabeçalho Oficial Bordado da Acta (Imagem 1) -->
      <div class="border rounded p-3 mb-3 bg-light text-center shadow-sm" style="border-color: #1E3A8A !important;">
        <h6 class="fw-bold mb-0 text-uppercase tracking-wider">REPÚBLICA DE MOÇAMBIQUE</h6>
        <small class="text-muted d-block fw-semibold text-uppercase">GOVERNO DA PROVÍNCIA DE ${(d.escola.provincia || 'MAPUTO').toUpperCase()} | GOVERNO DO DISTRITO DE ${(d.escola.distrito || 'CIDADE DE MAPUTO').toUpperCase()}</small>
        <h5 class="fw-bold text-dark my-1">${(d.escola.nome || 'Escola Secundária').toUpperCase()}</h5>
        <small class="fw-bold text-primary text-uppercase">SECTOR PEDAGÓGICO — ACTA DO CONSELHO DE AVALIAÇÃO</small>
      </div>

      <!-- Texto Protocolar com Campos Editáveis (Fiel à Imagem 1) -->
      <div class="p-3 bg-white rounded border mb-4 shadow-sm text-dark" style="line-height: 1.8; text-align: justify; font-family: 'Times New Roman', serif; font-size: 0.95rem; border-color: #cbd5e1 !important;">
        ${textoProtocolar}
      </div>

      <!-- TABELAS LADO A LADO SEGUNDO O MODELO OFICIAL (Imagem 1) -->
      <div class="row g-3 mb-4">
        <!-- TABELA 1: Aproveitamento Escolar por Trimestres e Fim do Ano (Efectivos e Movimento) -->
        <div class="col-xl-6">
          <div class="border rounded p-2 bg-white h-100 shadow-sm">
            <h6 class="fw-bold text-center small text-uppercase mb-2 py-2 rounded text-white" style="background: #1E3A8A;">Aproveitamento por Trimestres e Fim do Ano</h6>
            <div class="table-responsive">
              <table class="table table-bordered table-sm text-center mb-0 align-middle" style="font-size: 0.68rem;">
                <thead class="table-light">
                  <tr>
                    <th rowspan="2" class="align-middle text-start ps-2">CATEGORIA</th>
                    <th rowspan="2" class="align-middle">GÉN</th>
                    <th colspan="2">Iº TRIMESTRE</th>
                    <th colspan="2">IIº TRIMESTRE</th>
                    <th colspan="2">IIIº TRIMESTRE</th>
                    <th colspan="2">FIM DO ANO</th>
                  </tr>
                  <tr>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                  </tr>
                </thead>
                <tbody>
                  ${renderTeLinhas('Matrículas / Efectivo Inicial', 'inscritos')}
                  ${renderTeLinhas('Desistentes', 'desistentes')}
                  ${renderTeLinhas('Transferidos', 'transferidos')}
                  ${renderTeLinhas('Falecidos', 'falecidos')}
                  ${renderTeLinhas('Perdeu Ano por Faltas', 'perdeuFaltas')}
                  ${renderTeLinhas('Anulou Matrícula', 'anulouMatricula')}
                  ${renderTeLinhas('Alunos Avaliados', 'avaliados')}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- TABELA 2: Aproveitamento Pedagógico por Faixas e Crescimento -->
        <div class="col-xl-6">
          <div class="border rounded p-2 bg-white h-100 shadow-sm">
            <h6 class="fw-bold text-center small text-uppercase mb-2 py-2 rounded text-white" style="background: #1E3A8A;">Aproveitamento Pedagógico</h6>
            <div class="table-responsive">
              <table class="table table-bordered table-sm text-center mb-0 align-middle" style="font-size: 0.68rem;">
                <thead class="table-light">
                  <tr>
                    <th rowspan="2" class="align-middle text-start ps-2">CLASSIFICAÇÃO</th>
                    <th rowspan="2" class="align-middle">GÉN</th>
                    <th colspan="2">Iº TRIMESTRE</th>
                    <th colspan="2">IIº TRIMESTRE</th>
                    <th colspan="2">IIIº TRIMESTRE</th>
                    <th colspan="2">FIM DO ANO</th>
                    <th colspan="3">CRESCIMENTO</th>
                  </tr>
                  <tr>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Iº-IIº</th><th>IIº-IIIº</th><th>GLOBAL</th>
                  </tr>
                </thead>
                <tbody>
                  ${renderTaLinhas('Alunos Avaliados', 'avaliados')}
                  ${renderTaLinhas('Não Satisfatório (0 a 9,4)', 'naoSatisfatorio')}
                  ${renderTaLinhas('Satisfatório (9,5 a 13,4)', 'satisfatorio')}
                  ${renderTaLinhas('Bom (13,5 a 16,4)', 'bom')}
                  ${renderTaLinhas('Muito Bom (16,5 a 18,4)', 'muitoBom')}
                  ${renderTaLinhas('Excelente (18,5 a 20)', 'excelente')}
                  ${renderTaLinhas('TOTAL APROVADOS', 'aprovados', true)}
                  ${renderTaLinhas('TOTAL REPROVADOS', 'reprovados')}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- TABELA 3: Aproveitamento por Disciplina (Área de Comunicação e Ciências Sociais) -->
      <div class="border rounded p-3 bg-white mb-4 shadow-sm">
        <h6 class="fw-bold text-center small text-uppercase mb-2 py-2 rounded text-white" style="background: #1E3A8A;">Área Curricular & Estatística por Disciplina</h6>
        <div class="table-responsive">
          <table class="table table-bordered table-sm text-center mb-0 align-middle" style="font-size: 0.68rem;">
            <thead class="table-light">
              <tr>
                <th rowspan="2" class="align-middle text-start ps-2">CLASSIFICAÇÃO</th>
                ${d.disciplinas.map(dis => `<th colspan="3" class="fw-bold text-uppercase">${dis.nome}</th>`).join('')}
              </tr>
              <tr>
                ${d.disciplinas.map(() => '<th>H</th><th>M</th><th class="table-secondary">HM</th>').join('')}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="text-start ps-2 fw-semibold">[0 - 9,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa0_9?.h ?? 0}</td><td>${dis.faixa0_9?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa0_9?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[9,5 - 13,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa10_13?.h ?? 0}</td><td>${dis.faixa10_13?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa10_13?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[13,5 - 16,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa14_16?.h ?? 0}</td><td>${dis.faixa14_16?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa14_16?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[16,5 - 18,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa17_18?.h ?? 0}</td><td>${dis.faixa17_18?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa17_18?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[18,5 - 20 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa19_20?.h ?? 0}</td><td>${dis.faixa19_20?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa19_20?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr class="table-light fw-bold">
                <td class="text-start ps-2">Alunos Avaliados</td>
                ${d.disciplinas.map(dis => `<td>${dis.avaliados?.h ?? 0}</td><td>${dis.avaliados?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.avaliados?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr class="table-success bg-opacity-25 fw-bold text-success">
                <td class="text-start ps-2">Notas Positivas</td>
                ${d.disciplinas.map(dis => `<td>${dis.positivas?.h ?? 0}</td><td>${dis.positivas?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.positivas?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr class="table-success bg-opacity-25 fw-bold text-success">
                <td class="text-start ps-2">% Positivas</td>
                ${d.disciplinas.map(dis => `<td>${dis.positivas?.pctH ?? 0}%</td><td>${dis.positivas?.pctM ?? 0}%</td><td class="table-secondary fw-bold">${dis.positivas?.pct ?? 0}%</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 text-muted fst-italic">Assinatura do Docente</td>
                ${d.disciplinas.map(() => '<td colspan="3" class="text-center text-muted fst-italic">_________________</td>').join('')}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = '<div class="alert alert-danger">Erro ao carregar acta do conselho de avaliação.</div>';
  }
}

function modalConfigurarSessaoActa() {
  const turmaId = document.getElementById('pautaTurmaSelect')?.value;
  if (!turmaId) return alert('Selecione uma turma para configurar a sessão da acta');

  const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
  const cp = savedParamsRaw ? JSON.parse(savedParamsRaw) : {
    presidenteT1: 'Fernando José Mandamule',
    presidenteT2: 'Fernando José Mandamule',
    presidenteT3: '_________________',
    dataT1: '26/05/2026',
    dataT2: '01/09/2026',
    dataT3: '____/____/2026',
    horaInicioT1: '09', minInicioT1: '30', horaFimT1: '10', minFimT1: '00',
    horaInicioT2: '09', minInicioT2: '30', horaFimT2: '11', minFimT2: '00',
    horaInicioT3: '____', minInicioT3: '____', horaFimT3: '____', minFimT3: '____'
  };

  abrirModal('Configurar Dados da Sessão do Conselho de Avaliação', `
    <form id="formConfigSessaoActa" onsubmit="salvarConfigSessaoActa(event, '${turmaId}')">
      <div class="alert alert-info py-2 small">
        <i class="bi bi-info-circle me-1"></i> Preencha os nomes dos presidentes, datas e horários de cada trimestre. O restante dos dados biográficos, turmas e notas são calculados automaticamente pelo sistema.
      </div>
      
      <!-- 1º Trimestre -->
      <div class="card p-3 mb-3 bg-light">
        <h6 class="fw-bold text-primary mb-2">1º Trimestre Lectivo</h6>
        <div class="row g-2">
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Presidente da Sessão</label>
            <input type="text" id="cfgPresT1" class="form-control form-control-sm" value="${cp.presidenteT1 || 'Fernando José Mandamule'}" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Data da Realização</label>
            <input type="text" id="cfgDataT1" class="form-control form-control-sm" value="${cp.dataT1 || '26/05/2026'}" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Horário Início (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHIniT1" class="form-control text-center" value="${cp.horaInicioT1 || '09'}">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMIniT1" class="form-control text-center" value="${cp.minInicioT1 || '30'}">
            </div>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Horário Término (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHFimT1" class="form-control text-center" value="${cp.horaFimT1 || '10'}">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMFimT1" class="form-control text-center" value="${cp.minFimT1 || '00'}">
            </div>
          </div>
        </div>
      </div>

      <!-- 2º Trimestre -->
      <div class="card p-3 mb-3 bg-light">
        <h6 class="fw-bold text-primary mb-2">2º Trimestre Lectivo</h6>
        <div class="row g-2">
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Presidente da Sessão</label>
            <input type="text" id="cfgPresT2" class="form-control form-control-sm" value="${cp.presidenteT2 || 'Fernando José Mandamule'}" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Data da Realização</label>
            <input type="text" id="cfgDataT2" class="form-control form-control-sm" value="${cp.dataT2 || '01/09/2026'}" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Horário Início (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHIniT2" class="form-control text-center" value="${cp.horaInicioT2 || '09'}">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMIniT2" class="form-control text-center" value="${cp.minInicioT2 || '30'}">
            </div>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Horário Término (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHFimT2" class="form-control text-center" value="${cp.horaFimT2 || '11'}">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMFimT2" class="form-control text-center" value="${cp.minFimT2 || '00'}">
            </div>
          </div>
        </div>
      </div>

      <!-- 3º Trimestre -->
      <div class="card p-3 mb-3 bg-light">
        <h6 class="fw-bold text-primary mb-2">3º Trimestre Lectivo</h6>
        <div class="row g-2">
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Presidente da Sessão</label>
            <input type="text" id="cfgPresT3" class="form-control form-control-sm" value="${cp.presidenteT3 || '_________________'}" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Data da Realização</label>
            <input type="text" id="cfgDataT3" class="form-control form-control-sm" value="${cp.dataT3 || '____/____/2026'}" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Horário Início (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHIniT3" class="form-control text-center" value="${cp.horaInicioT3 || '____'}">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMIniT3" class="form-control text-center" value="${cp.minInicioT3 || '____'}">
            </div>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Horário Término (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHFimT3" class="form-control text-center" value="${cp.horaFimT3 || '____'}">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMFimT3" class="form-control text-center" value="${cp.minFimT3 || '____'}">
            </div>
          </div>
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2">
        <button type="button" class="btn btn-secondary btn-sm" onclick="fecharModal()">Cancelar</button>
        <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-check-lg me-1"></i> Salvar e Actualizar Acta</button>
      </div>
    </form>
  `);
}

function salvarConfigSessaoActa(e, turmaId) {
  e.preventDefault();
  const params = {
    presidenteT1: document.getElementById('cfgPresT1').value,
    dataT1: document.getElementById('cfgDataT1').value,
    horaInicioT1: document.getElementById('cfgHIniT1').value,
    minInicioT1: document.getElementById('cfgMIniT1').value,
    horaFimT1: document.getElementById('cfgHFimT1').value,
    minFimT1: document.getElementById('cfgMFimT1').value,

    presidenteT2: document.getElementById('cfgPresT2').value,
    dataT2: document.getElementById('cfgDataT2').value,
    horaInicioT2: document.getElementById('cfgHIniT2').value,
    minInicioT2: document.getElementById('cfgMIniT2').value,
    horaFimT2: document.getElementById('cfgHFimT2').value,
    minFimT2: document.getElementById('cfgMFimT2').value,

    presidenteT3: document.getElementById('cfgPresT3').value,
    dataT3: document.getElementById('cfgDataT3').value,
    horaInicioT3: document.getElementById('cfgHIniT3').value,
    minInicioT3: document.getElementById('cfgMIniT3').value,
    horaFimT3: document.getElementById('cfgHFimT3').value,
    minFimT3: document.getElementById('cfgMFimT3').value
  };

  localStorage.setItem('sige_acta_params_' + turmaId, JSON.stringify(params));
  fecharModal();
  carregarActaConselho(turmaId);
}

function exportarActaConselhoExcel(turmaIdExplicit = null, anoExplicit = null) {
  const turmaId = turmaIdExplicit || document.getElementById('pautaTurmaSelect')?.value || document.getElementById('dtTurmaSelect')?.value;
  if (!turmaId) return alert('Selecione uma turma para exportar');
  const ano = anoExplicit || document.getElementById('pautaAnoFiltro')?.value || '2026';

  const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
  const cp = savedParamsRaw ? JSON.parse(savedParamsRaw) : {};
  const qParams = new URLSearchParams({ anoLetivo: ano, ...cp }).toString();

  downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/acta-xlsx?${qParams}`, `Acta_Conselho_Turma_${ano}.xlsx`);
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
  if (!confirm(`Confirmar recebimento e liquidação da quantia de ${valor.toLocaleString('pt-PT')} MZN?`)) return;
  try {
    const res = await apiFetch(`/api/v1/pagamentos/${id}/liquidar`, {
      method: 'POST',
      body: JSON.stringify({ valor_pago: Number(valor), metodo_pagamento: 'NUMERARIO_OU_POS' })
    });
    if (res.success) {
      mostrarNotificacao('Pagamento liquidado com sucesso! Estado atualizado para PAGO.', 'success');
      await carregarPagamentos();
    }
  } catch (err) {
    alert('Erro ao liquidar pagamento: ' + (err.message || ''));
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
    const resTurmas = await apiFetch('/api/v1/escola-admin/turmas');
    const selectTurma = document.getElementById('printSelectTurma');
    if (selectTurma) {
      selectTurma.innerHTML = '<option value="">Selecione uma turma...</option>' + 
        (resTurmas.data || []).map(t => `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`).join('');
      
      if (resTurmas.data && resTurmas.data.length > 0) {
        selectTurma.value = resTurmas.data[0].id;
        await aoSelecionarTurmaImpressao();
      }
    }
  } catch (err) {}
}

async function aoSelecionarTurmaImpressao() {
  const turmaId = document.getElementById('printSelectTurma')?.value;
  const selectAluno = document.getElementById('printSelectAluno');
  if (!selectAluno) return;

  if (!turmaId) {
    selectAluno.innerHTML = '<option value="TODOS">-- Todos os Alunos da Turma (Emissão em Lote) --</option>';
    return;
  }

  selectAluno.innerHTML = '<option value="">A carregar alunos da turma...</option>';
  try {
    const res = await apiFetch(`/api/v1/alunos?turmaId=${turmaId}`);
    const alunos = res.data || [];
    let opts = `<option value="TODOS">-- Todos os Alunos da Turma (${alunos.length} Alunos - Emissão em Lote) --</option>`;
    opts += alunos.map((a, idx) => 
      `<option value="${a.id}">${a.numero || idx + 1}. ${a.nome} ${a.apelido || ''} (${a.matricula})</option>`
    ).join('');
    selectAluno.innerHTML = opts;
  } catch (err) {
    selectAluno.innerHTML = '<option value="TODOS">-- Todos os Alunos da Turma (Emissão em Lote) --</option>';
  }
}

function alternarCamposImpressao(tipo) {
  // Ajustes dinâmicos de interface
}

async function carregarVisualizacaoImpressao() {
  const tipo = document.getElementById('printTipoDoc').value;
  const turmaId = document.getElementById('printSelectTurma')?.value;
  const alunoId = document.getElementById('printSelectAluno')?.value;
  const preview = document.getElementById('printAreaPreview');
  preview.style.display = 'block';
  preview.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A processar documento oficial...</p></div>';

  try {
    if (alunoId === 'TODOS' || !alunoId) {
      if (!turmaId) return alert('Por favor, selecione uma turma para emissão em lote');
      if (tipo === 'PAUTA_TURMA') {
        const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/completa`);
        if (res.success) renderizarPautaGeralImpressao(res.data);
        return;
      }
      if (tipo === 'ACTA_CONSELHO') {
        await carregarActaConselho(turmaId);
        const containerActa = document.getElementById('containerActaConselhoCorpo');
        if (containerActa) preview.innerHTML = containerActa.innerHTML;
        return;
      }
      const resLote = await apiFetch(`/api/v1/impressao/lote/turma/${turmaId}?tipo=${tipo}`);
      if (resLote.success) {
        renderizarLoteImpressao(resLote.data);
      } else {
        throw new Error(resLote.message || 'Falha ao emitir lote');
      }
      return;
    }

    // Modo Individual
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
      const pagRes = await apiFetch(`/api/v1/pagamentos?alunoId=${alunoId}`);
      if (pagRes.success && pagRes.data.length > 0) {
        carregarReciboIndividual(pagRes.data[0].id);
      } else {
        preview.innerHTML = '<div class="alert alert-warning text-center">Nenhum recibo de pagamento emitido para este aluno.</div>';
      }
    } else if (tipo === 'PAUTA_TURMA' || tipo === 'ACTA_CONSELHO') {
      if (turmaId) {
        if (tipo === 'PAUTA_TURMA') {
          const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/completa`);
          if (res.success) renderizarPautaGeralImpressao(res.data);
        } else {
          await carregarActaConselho(turmaId);
          const containerActa = document.getElementById('containerActaConselhoCorpo');
          if (containerActa) preview.innerHTML = containerActa.innerHTML;
        }
      }
    }
  } catch (err) {
    preview.innerHTML = `<div class="alert alert-danger text-center">${err.message || 'Erro ao processar documento'}</div>`;
  }
}

function imprimirDocumentoCentral() {
  const preview = document.getElementById('printAreaPreview');
  if (!preview || preview.style.display === 'none' || !preview.innerHTML.trim()) {
    carregarVisualizacaoImpressao().then(() => window.print());
    return;
  }
  window.print();
}

async function descarregarPdfCentral() {
  const preview = document.getElementById('printAreaPreview');
  const turmaId = document.getElementById('printSelectTurma')?.value;
  if (!turmaId) return alert('Por favor, selecione uma turma antes de descarregar o documento');

  if (!preview || preview.style.display === 'none' || !preview.innerHTML.trim() || preview.innerHTML.includes('spinner-border')) {
    await carregarVisualizacaoImpressao();
  }

  if (!preview || preview.innerHTML.includes('spinner-border') || !preview.innerText.trim()) {
    return alert('Aguarde o carregamento do documento oficial ou verifique a turma selecionada.');
  }

  const tipo = document.getElementById('printTipoDoc')?.value || 'DOCUMENTO';
  const isLandscape = tipo === 'PAUTA_TURMA' || tipo === 'ACTA_CONSELHO';
  await exportarElementoParaPdf(preview, `${tipo}_Oficial_2026.pdf`, isLandscape ? 'landscape' : 'portrait');
}

function descarregarXlsxCentral() {
  const tipo = document.getElementById('printTipoDoc')?.value;
  const turmaId = document.getElementById('printSelectTurma')?.value;
  const alunoId = document.getElementById('printSelectAluno')?.value;
  if (!turmaId) return alert('Selecione uma turma para exportar o documento em Excel');

  if (tipo === 'ACTA_CONSELHO') {
    exportarActaConselhoExcel(turmaId);
  } else if (tipo === 'PAUTA_TURMA') {
    exportarPautaGeralExcel(turmaId);
  } else if (tipo === 'BOLETIM') {
    if (alunoId && alunoId !== 'TODOS') {
      downloadFicheiroBinario(`/api/v1/impressao/boletim/${alunoId}/xlsx`, `Boletim_${alunoId}.xlsx`);
    } else {
      downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=BOLETIM`, `Boletins_Turma_${turmaId}.xlsx`);
    }
  } else if (tipo === 'DECLARACAO') {
    if (alunoId && alunoId !== 'TODOS') {
      downloadFicheiroBinario(`/api/v1/impressao/declaracao/${alunoId}/xlsx`, `Declaracao_${alunoId}.xlsx`);
    } else {
      downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=DECLARACAO`, `Declaracoes_Turma_${turmaId}.xlsx`);
    }
  } else if (tipo === 'CERTIFICADO') {
    if (alunoId && alunoId !== 'TODOS') {
      downloadFicheiroBinario(`/api/v1/impressao/certificado/${alunoId}/xlsx`, `Certificado_${alunoId}.xlsx`);
    } else {
      downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=CERTIFICADO`, `Certificados_Turma_${turmaId}.xlsx`);
    }
  } else {
    exportarPautaGeralExcel(turmaId);
  }
}

function descarregarJsonCentral() {
  const tipo = document.getElementById('printTipoDoc')?.value;
  const turmaId = document.getElementById('printSelectTurma')?.value;
  const alunoId = document.getElementById('printSelectAluno')?.value;
  if (!turmaId) return alert('Selecione uma turma para exportar o documento em JSON');

  if (tipo === 'ACTA_CONSELHO') {
    exportarActaConselhoJson(turmaId);
  } else if (tipo === 'PAUTA_TURMA') {
    exportarPautaGeralJson(turmaId);
  } else if (tipo === 'BOLETIM') {
    if (alunoId && alunoId !== 'TODOS') {
      downloadFicheiroBinario(`/api/v1/impressao/boletim/${alunoId}/json`, `Boletim_${alunoId}.json`);
    } else {
      downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/json?tipo=BOLETIM`, `Boletins_Turma_${turmaId}.json`);
    }
  } else if (tipo === 'DECLARACAO') {
    if (alunoId && alunoId !== 'TODOS') {
      downloadFicheiroBinario(`/api/v1/impressao/declaracao/${alunoId}/json`, `Declaracao_${alunoId}.json`);
    } else {
      downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/json?tipo=DECLARACAO`, `Declaracoes_Turma_${turmaId}.json`);
    }
  } else if (tipo === 'CERTIFICADO') {
    if (alunoId && alunoId !== 'TODOS') {
      downloadFicheiroBinario(`/api/v1/impressao/certificado/${alunoId}/json`, `Certificado_${alunoId}.json`);
    } else {
      downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/json?tipo=CERTIFICADO`, `Certificados_Turma_${turmaId}.json`);
    }
  } else {
    exportarPautaGeralJson(turmaId);
  }
}

function exportarPautaGeralJson(turmaId) {
  const tId = turmaId || document.getElementById('selectPautaTurma')?.value || document.getElementById('printSelectTurma')?.value;
  if (!tId) return alert('Selecione uma turma primeiro para exportar a Pauta em JSON.');
  const ano = document.getElementById('selectPautaAnoLetivo')?.value || '2026';
  downloadFicheiroBinario(`/api/v1/pautas/turma/${tId}/export-json?anoLetivo=${ano}`, `Pauta_Turma_${ano}.json`);
}

function exportarActaConselhoJson(turmaId) {
  const tId = turmaId || document.getElementById('selectPautaTurma')?.value || document.getElementById('printSelectTurma')?.value;
  if (!tId) return alert('Selecione uma turma primeiro para exportar a Acta em JSON.');
  const ano = document.getElementById('selectPautaAnoLetivo')?.value || '2026';
  const sessao = JSON.parse(localStorage.getItem(`sige_sessao_acta_${tId}`) || '{}');
  const params = new URLSearchParams({ anoLetivo: ano });
  if (sessao.presidente) params.append('presidente', sessao.presidente);
  if (sessao.data) params.append('data', sessao.data);
  if (sessao.horaInicio) params.append('horaInicio', sessao.horaInicio);
  if (sessao.horaFim) params.append('horaFim', sessao.horaFim);
  downloadFicheiroBinario(`/api/v1/pautas/turma/${tId}/acta-json?${params.toString()}`, `Acta_Conselho_Turma_${ano}.json`);
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

function obterHtmlBoletimOficial(d) {
  const mediaGlobalInt = Math.round(Number(d.mediaGeral !== undefined ? d.mediaGeral : (d.mediaGlobal !== undefined ? d.mediaGlobal : 14)) || 14);
  const resultado = d.resultado || (mediaGlobalInt >= 9.5 ? 'APROVADO' : 'REPROVADO');
  const safeName = (d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
  const anoLetivo = d.anoLetivo || d.anoLectivo || '2026';

  return `
    <div class="printable-document p-4 bg-white" style="page-break-after: always; break-after: page; page-break-inside: avoid;">
      <div class="text-center border-bottom pb-3 mb-4">
        <img src="/img/emblema-mocambique.png" style="width: 44px; height: 44px; margin-bottom: 3px;" alt="Emblema Nacional">
        <h5 class="fw-bold mb-1">REPÚBLICA DE MOÇAMBIQUE</h5>
        <h6 class="fw-bold mb-1">${d.escola?.nome || 'Escola Secundária'}</h6>
        <p class="text-muted small mb-0">NUIT: ${d.escola?.nif_cnpj || '-'} | ${d.escola?.distrito || '-'}, ${d.escola?.provincia || 'Maputo'}</p>
        <h5 class="mt-3 fw-bold text-primary">${d.titulo || 'BOLETIM OFICIAL DE AVALIAÇÃO TRIMESTRAL'} — ANO LECTIVO ${anoLetivo}</h5>
      </div>

      <div class="row g-2 mb-4 p-3 bg-light rounded small">
        <div class="col-6"><strong>Aluno:</strong> ${d.aluno?.nome || d.aluno?.nomeCompleto}</div>
        <div class="col-6"><strong>Nº Matrícula:</strong> ${d.aluno?.matricula || '-'}</div>
        <div class="col-6"><strong>Turma:</strong> ${d.aluno?.turma?.nome || d.aluno?.turma || '-'}</div>
        <div class="col-6"><strong>Grau / Classe:</strong> ${d.aluno?.grau || d.aluno?.turma?.grau_ano || '-'}</div>
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
          ${(d.disciplinas || []).map(item => {
            const t1 = item.t1 !== null && item.t1 !== undefined ? Math.round(item.t1) : '-';
            const t2 = item.t2 !== null && item.t2 !== undefined ? Math.round(item.t2) : '-';
            const t3 = item.t3 !== null && item.t3 !== undefined ? Math.round(item.t3) : '-';
            const mVal = item.mediaFinal !== undefined && item.mediaFinal !== null ? item.mediaFinal : item.notaFinal;
            const mfd = mVal !== undefined && mVal !== null ? Math.round(mVal) : '-';
            const isPos = typeof mfd === 'number' ? mfd >= 9.5 : false;
            return `
              <tr>
                <td class="text-start"><strong>${item.nome || item.disciplina}</strong></td>
                <td>${t1}</td>
                <td>${t2}</td>
                <td>${t3}</td>
                <td class="fw-bold ${typeof mfd === 'number' ? (isPos ? 'text-success' : 'text-danger') : ''}">${mfd}</td>
                <td>${item.faltas || 0}</td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>

      <div class="d-flex justify-content-between align-items-center p-3 border rounded mb-4 small">
        <div><strong>Média Global:</strong> <span class="fs-5 fw-bold text-primary">${mediaGlobalInt}</span> valores</div>
        <div><strong>Resultado Final:</strong> <span class="badge ${resultado.toUpperCase().includes('APROV') ? 'bg-success' : 'bg-danger'} fs-6">${resultado}</span></div>
      </div>

      <!-- Data Formal sem Hora no Boletim Oficial -->
      <div class="text-end mb-4 small">
        <em>${d.dataEmissaoExtenso || d.dataExtenso || 'Maputo, ' + new Date().toLocaleDateString('pt-PT')}</em>
      </div>

      <div class="row text-center pt-4 border-top small">
        <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">O Director Pedagógico (DAP)</p></div>
        <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">O Encarregado de Educação</p></div>
      </div>
    </div>
  `;
}

function renderizarBoletim(d) {
  const preview = document.getElementById('printAreaPreview');
  const safeName = (d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
  const ano = d.anoLetivo || d.anoLectivo || '2026';

  preview.style.display = 'block';
  preview.innerHTML = `
    <div class="text-end mb-3 no-print">
      <button class="btn btn-primary btn-sm" onclick="imprimirDocumentoComTitulo('Boletim_${safeName}_${ano}')">
        <i class="bi bi-printer me-2"></i> Imprimir / Guardar em PDF
      </button>
    </div>
    ${obterHtmlBoletimOficial(d)}
  `;
}

// ==================== DOCUMENTOS OFICIAIS MINEDH (1 PÁGINA A4) ====================

function obterHtmlDeclaracaoOficial(d) {
  const escolaNome = (d.escola?.nome || 'Escola Secundária').toUpperCase();
  const provincia = (d.escola?.provincia || 'Inhambane').toUpperCase();
  const distrito = (d.escola?.distrito || 'Massinga');
  const directorNome = d.directorNome || 'Pero Chitofo Murrombe';
  const directorCarreira = d.directorCarreira || 'Especialista de Educação';
  
  const alunoNome = (d.aluno?.nomeCompleto || d.aluno?.nome || 'ALUNO NÃO IDENTIFICADO').toUpperCase();
  const sexo = ((d.aluno?.genero || 'M').toUpperCase() === 'M') ? 'Masculino' : 'Feminino';
  const pai = d.aluno?.pai || '...........................................';
  const mae = d.aluno?.mae || '...........................................';
  const alunoDistrito = d.aluno?.distrito || distrito;
  const alunoProvincia = d.aluno?.provincia || d.escola?.provincia || 'Inhambane';
  const anoLectivo = d.anoLectivo || d.anoLetivo || '2026';
  const grauClasse = d.grauAno || d.aluno?.turma?.grau_ano || '12ª';
  const grupoArea = d.area || d.aluno?.turma?.area || 'Geral';
  const matricula = d.aluno?.matricula || '-';
  const turmaNome = d.aluno?.turma?.nome || d.aluno?.turma || '-';
  
  let dataNascFormatada = '___ de ______________ de 20___';
  if (d.aluno?.data_nascimento) {
    const dt = new Date(d.aluno.data_nascimento);
    if (!isNaN(dt.getTime())) {
      const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
      dataNascFormatada = `${String(dt.getDate()).padStart(2, '0')} de ${meses[dt.getMonth()]} de ${dt.getFullYear()}`;
    }
  }

  // Verbo de resultado oficial MINEDH
  let resultadoVerbo = 'concluiu com aproveitamento';
  const resOf = (d.resultadoOficial || d.resultado || '').toLowerCase();
  if (resOf.includes('transita')) {
    resultadoVerbo = 'transitou';
  } else if (resOf.includes('aprova')) {
    resultadoVerbo = 'aprovou';
  } else if (resOf.includes('não') || resOf.includes('reprova')) {
    resultadoVerbo = 'não transitou';
  }

  // Mapa de notas por disciplina
  const notasMap = {};
  if (d.disciplinas && Array.isArray(d.disciplinas)) {
    d.disciplinas.forEach(item => {
      const n = (item.disciplina || item.nome || '').toLowerCase().trim();
      const v = item.notaFinal !== undefined ? item.notaFinal : (item.mediaFinal !== undefined ? item.mediaFinal : null);
      notasMap[n] = v;
    });
  }

  const obterNotaValor = (nomeDisc) => {
    const k = nomeDisc.toLowerCase().trim();
    for (const [ch, vl] of Object.entries(notasMap)) {
      if (ch.includes(k) || k.includes(ch)) {
        if (vl !== null && vl !== undefined && !isNaN(vl)) {
          const num = Number(vl);
          return Number.isInteger(num) ? String(num) : num.toFixed(1);
        }
      }
    }
    return '---';
  };

  const colEsquerda = [
    'Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Biologia', 'Química'
  ];
  const colDireita = [
    'Física', 'Matemática', 'Educação Visual', 'Agropecuária', 'Noções de Empreendedorismo', 'Educação Física', 'TIC\'s'
  ];

  const renderLinhaDisc = (disc) => {
    const nota = obterNotaValor(disc);
    return `
      <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; font-size: 11pt;">
        <span>${disc}</span>
        <span style="flex-grow: 1; border-bottom: 1px dotted #666; margin: 0 6px;"></span>
        <span style="font-weight: bold; white-space: nowrap;">( ${nota} ) valores</span>
      </div>
    `;
  };

  const mediaGlobalVal = Math.round(Number(d.mediaGlobal !== undefined ? d.mediaGlobal : (d.mediaGeral !== undefined ? d.mediaGeral : 14)) || 14);

  return `
    <div class="documento-a4-pagina-unica" style="width: 210mm; min-height: 288mm; height: 288mm; max-height: 288mm; padding: 4mm 6mm; box-sizing: border-box; overflow: hidden; background: #fff; font-family: 'Times New Roman', Times, serif; position: relative; page-break-inside: avoid; page-break-after: always;">
      <div class="borda-oficial-declaracao" style="border: 4px double #111; padding: 8mm 11mm; height: 100%; box-sizing: border-box; position: relative; display: flex; flex-direction: column; justify-content: space-between;">
        <img src="/img/emblema-mocambique.png" class="marca-dagua-emblema" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 300px; height: 300px; opacity: 0.08; pointer-events: none; z-index: 0;" alt="Marca d'Água">
        
        <!-- Cabeçalho Oficial com Emblema Nacional Oficial -->
        <div style="text-align: center; position: relative; z-index: 1;">
          <img src="/img/emblema-mocambique.png" style="width: 50px; height: 50px; margin-bottom: 2px; object-fit: contain;" alt="Emblema Nacional de Moçambique">
          <div style="font-size: 11.5pt; font-weight: bold; letter-spacing: 0.5px;">República de Moçambique</div>
          <div style="font-size: 10.5pt; font-weight: bold;">Governo da Província de ${provincia}</div>
          <div style="font-size: 9.5pt; font-weight: bold;">Direcção Provincial de Educação e Cultura de ${provincia}</div>
          <div style="font-size: 11pt; font-weight: bold; text-transform: uppercase; margin-top: 2px;">${escolaNome}</div>
          <div style="font-size: 16pt; font-weight: bold; margin-top: 4px; letter-spacing: 1px;">Declaração</div>
        </div>

        <!-- Texto Declarativo Oficial -->
        <div style="position: relative; z-index: 1;">
          <p style="text-align: justify; font-size: 12pt; line-height: 1.62; margin: 8px 0 10px 0; text-indent: 20px;">
            Eu, <strong>${directorNome}</strong>, Director da <strong>${escolaNome}</strong>, declaro, em face dos dados constantes dos registos académicos existentes nesta instituição, que <strong>${alunoNome}</strong>, de sexo <strong>${sexo}</strong>, de nacionalidade Moçambicana, nascido aos <strong>${dataNascFormatada}</strong>, filho de <strong>${pai}</strong> e de <strong>${mae}</strong>, natural de <strong>${alunoDistrito}</strong>, Província de <strong>${alunoProvincia}</strong>, <strong>${resultadoVerbo}</strong> no Ano Lectivo de <strong>${anoLectivo}</strong> a <strong>${grauClasse}</strong> Classe, grupo <strong>${grupoArea}</strong> com as seguintes classificações:
          </p>

          <!-- Tabela de Disciplinas em 2 Colunas -->
          <div style="display: flex; gap: 26px; margin: 6px 0;">
            <div style="flex: 1;">
              ${colEsquerda.map(renderLinhaDisc).join('')}
            </div>
            <div style="flex: 1;">
              ${colDireita.map(renderLinhaDisc).join('')}
            </div>
          </div>

          <div style="font-size: 12pt; font-weight: bold; margin: 9px 0; display: flex; align-items: baseline;">
            <span>Média global da Classe: ( ${mediaGlobalVal} ) valores.</span>
            <span style="flex-grow: 1; border-bottom: 1px solid #111; margin-left: 8px;"></span>
          </div>

          <p style="font-size: 11pt; line-height: 1.5; margin: 8px 0; text-align: justify;">
            Os resultados constam do Livro de Registo Académico de <strong>${anoLectivo}</strong>, com o número <strong>${matricula}</strong> turma <strong>${turmaNome}</strong> / <strong>${anoLectivo}</strong>.<br>
            E, por ser verdade e ter sido requerido, passo a presente declaração, assinada e autenticada com o carimbo a tinta de óleo em uso nesta instituição.
          </p>
        </div>

        <!-- Secção de Assinaturas e Datação Formal -->
        <div style="position: relative; z-index: 1; margin-top: 4px;">
          <div style="display: flex; justify-content: space-between; font-size: 9.5pt; margin-bottom: 8px;">
            <div style="width: 45%;">
              <div><strong>Extraído por:</strong> ____________________________</div>
              <div style="margin-top: 4px;">Data: ___ / ___ / 20___</div>
            </div>
            <div style="width: 45%; text-align: right;">
              <div><strong>Conferido por:</strong> ____________________________</div>
              <div style="margin-top: 4px;">Data: ___ / ___ / 20___</div>
            </div>
          </div>

          <div style="text-align: center; font-size: 10pt;">
            <div>${distrito}, aos ___ de ______________ de ${anoLectivo}</div>
            <div style="font-weight: bold; margin-top: 4px;">O Director</div>
            <div style="border-bottom: 1px solid #111; margin: 26px auto 4px; width: 50%;"></div>
            <div style="font-weight: bold;">${directorNome}</div>
            <div style="font-size: 9pt; font-style: italic;">/${directorCarreira}/</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderizarDeclaracao(d) {
  const preview = document.getElementById('printAreaPreview');
  const safeName = (d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
  const ano = d.anoLectivo || d.anoLetivo || '2026';

  preview.style.display = 'block';
  preview.innerHTML = `
    <div class="no-print mb-3 text-end d-flex justify-content-between align-items-center">
      <span class="badge bg-success"><i class="bi bi-file-earmark-check me-1"></i> Declaração Oficial A4 (Página Única)</span>
      <button class="btn btn-primary btn-sm" onclick="imprimirDocumentoComTitulo('Declaracao_${safeName}_${ano}')">
        <i class="bi bi-printer me-2"></i> Imprimir / Guardar em PDF
      </button>
    </div>
    <div class="printable-document">
      ${obterHtmlDeclaracaoOficial(d)}
    </div>
  `;
}

function obterHtmlCertificadoOficial(d) {
  const escolaNome = (d.escola?.nome || 'Escola Secundária').toUpperCase();
  const provincia = (d.escola?.provincia || 'Inhambane');
  const distrito = (d.escola?.distrito || 'Massinga');
  const directorNome = d.directorNome || 'Pero Chitofo Murrombe';
  const directorCarreira = d.directorCarreira || 'Especialista de Educação';
  const chefeNome = d.chefeSecretariaNome || 'Glória João Zunguze';
  const chefeCarreira = d.chefeSecretariaCarreira || 'Técnica Profissional';

  const alunoNome = (d.aluno?.nomeCompleto || d.aluno?.nome || 'ALUNO NÃO IDENTIFICADO').toUpperCase();
  const sexo = ((d.aluno?.genero || 'M').toUpperCase() === 'M') ? 'Masculino' : 'Feminino';
  const pai = d.aluno?.pai || '...........................................';
  const mae = d.aluno?.mae || '...........................................';
  const alunoDistrito = d.aluno?.distrito || distrito;
  const alunoProvincia = d.aluno?.provincia || provincia;
  const anoLectivo = d.anoLectivo || d.anoLetivo || '2026';
  const grauClasse = d.grauAno || d.aluno?.turma?.grau_ano || '12ª';
  const area = d.area || d.aluno?.turma?.area || 'Ciências e Letras';
  const matricula = d.aluno?.matricula || '-';

  let diaNasc = '___', mesNasc = '___________', anoNasc = '20__';
  if (d.aluno?.data_nascimento) {
    const dt = new Date(d.aluno.data_nascimento);
    if (!isNaN(dt.getTime())) {
      diaNasc = String(dt.getDate()).padStart(2, '0');
      const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
      mesNasc = meses[dt.getMonth()];
      anoNasc = String(dt.getFullYear());
    }
  }

  // Mapa de notas por disciplina
  const notasMap = {};
  if (d.disciplinas && Array.isArray(d.disciplinas)) {
    d.disciplinas.forEach(item => {
      const n = (item.disciplina || item.nome || '').toLowerCase().trim();
      const v = item.notaFinal !== undefined ? item.notaFinal : (item.mediaFinal !== undefined ? item.mediaFinal : null);
      notasMap[n] = v;
    });
  }

  const obterNotaValor = (nomeDisc) => {
    const k = nomeDisc.toLowerCase().trim();
    for (const [ch, vl] of Object.entries(notasMap)) {
      if (ch.includes(k) || k.includes(ch)) {
        if (vl !== null && vl !== undefined && !isNaN(vl)) {
          const num = Number(vl);
          return Number.isInteger(num) ? String(num) : num.toFixed(1);
        }
      }
    }
    return '---';
  };

  const col1 = ['Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Intr. Filosofia'];
  const col2 = ['Matemática', 'Química', 'Física', 'Biologia', 'Desenho e Geom. Descritiva', 'Educação Visual'];
  const col3 = ['Educação Física', 'TIC\'s', 'Noções de Empreendedorismo', 'Agropecuária', 'Psicopedagogia'];

  const renderLinhaCert = (disc) => {
    const nota = obterNotaValor(disc);
    return `
      <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4.5px; font-size: 10.5pt;">
        <span>${disc}</span>
        <span style="flex-grow: 1; border-bottom: 1px dotted #777; margin: 0 4px;"></span>
        <span style="font-weight: bold; white-space: nowrap;">( ${nota} ) valores</span>
      </div>
    `;
  };

  const mediaGlobalVal = Math.round(Number(d.mediaGlobal !== undefined ? d.mediaGlobal : (d.mediaGeral !== undefined ? d.mediaGeral : 14)) || 14);
  const pautaNum = d.pautaNumero || '01';
  const termoExames = d.termoExames || '124';

  const agora = new Date();
  const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
  const diaAtual = agora.getDate();
  const mesAtual = meses[agora.getMonth()];
  const anoAtual = agora.getFullYear();

  return `
    <div class="documento-a4-pagina-unica" style="width: 210mm; min-height: 288mm; height: 288mm; max-height: 288mm; padding: 4mm 6mm; box-sizing: border-box; overflow: hidden; background: #fff; font-family: 'Times New Roman', Times, serif; position: relative; page-break-inside: avoid; page-break-after: always;">
      <div class="borda-ornamental-certificado" style="border: 6px double #111; padding: 8mm 11mm; height: 100%; box-sizing: border-box; position: relative; display: flex; flex-direction: column; justify-content: space-between;">
        <img src="/img/emblema-mocambique.png" class="marca-dagua-emblema" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 310px; height: 310px; opacity: 0.08; pointer-events: none; z-index: 0;" alt="Marca d'Água">

        <!-- Cabeçalho Oficial do Certificado -->
        <div style="text-align: center; position: relative; z-index: 1;">
          <img src="/img/emblema-mocambique.png" style="width: 48px; height: 48px; margin-bottom: 2px; object-fit: contain;" alt="Emblema Nacional">
          <div style="font-size: 11pt; font-weight: bold; text-transform: uppercase;">REPÚBLICA DE MOÇAMBIQUE</div>
          <div style="font-size: 10pt; font-weight: bold; text-transform: uppercase;">MINISTÉRIO DA EDUCAÇÃO E CULTURA</div>
          <div style="font-size: 9pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">INSTITUTO NACIONAL DE EXAMES, CERTIFICAÇÃO E EQUIVALÊNCIA</div>
          <div style="font-size: 9.5pt; margin-top: 2px;"><u>a) ${escolaNome}</u></div>
          <div style="font-size: 14pt; font-weight: bold; text-transform: uppercase; margin-top: 3px; letter-spacing: 0.8px; border-bottom: 1.5px solid #111; display: inline-block; padding-bottom: 2px;">CERTIFICADO DE HABILITAÇÕES</div>
        </div>

        <!-- Texto Declarativo Oficial do Chefe de Secretaria -->
        <div style="position: relative; z-index: 1;">
          <p style="text-align: justify; font-size: 12pt; line-height: 1.6; margin: 8px 0 10px 0; text-indent: 20px;">
            b) <strong>${chefeNome}</strong>, <em>${chefeCarreira}</em>, Chefe da secretaria da <strong>${escolaNome}</strong>, distrito de <strong>${distrito}</strong>, província de <strong>${provincia}</strong>, CERTIFICO em cumprimento do despacho exarado em requerimento que fica arquivado nesta secretaria que <strong>${alunoNome}</strong>, do Sexo <strong>${sexo}</strong>, natural de <strong>${alunoDistrito}</strong>, distrito de <strong>${alunoDistrito}</strong>, província de <strong>${alunoProvincia}</strong>, nascido no dia <strong>${diaNasc}</strong> de <strong>${mesNasc}</strong> de <strong>${anoNasc}</strong>, filho/a de <strong>${pai}</strong> e de <strong>${mae}</strong>, concluiu nesta escola como aluno c) <strong>Interno</strong>, em <strong>Dezembro</strong> de <strong>${anoLectivo}</strong>, a <strong>${grauClasse}</strong> Classe na área de <strong>${area}</strong>, tendo obtido os seguintes resultados:
          </p>

          <!-- Tabela com 3 Colunas de Disciplinas -->
          <div style="display: flex; gap: 14px; margin: 5px 0;">
            <div style="flex: 1;">
              ${col1.map(renderLinhaCert).join('')}
            </div>
            <div style="flex: 1;">
              ${col2.map(renderLinhaCert).join('')}
            </div>
            <div style="flex: 1;">
              ${col3.map(renderLinhaCert).join('')}
            </div>
          </div>

          <div style="text-align: center; font-weight: bold; font-size: 12pt; margin: 8px 0;">
            Média Global: ( ${mediaGlobalVal} ) Valores
          </div>

          <p style="font-size: 10.5pt; line-height: 1.48; margin: 7px 0; text-align: justify;">
            Os resultados constam da pauta nº <strong>${pautaNum}</strong> e do livro de Termo de Exames nº <strong>${termoExames}</strong>, código do aluno <strong>${matricula}</strong>.<br>
            E, por ser verdade passo o presente certificado que assino e autentico a tinta de óleo/selo branco em uso neste Estabelecimento de Ensino.
          </p>
        </div>

        <!-- Local, Datação e Assinaturas (Tudo contido na 1ª Página A4) -->
        <div style="position: relative; z-index: 1; margin-top: 3px;">
          <div style="text-align: center; font-size: 9.5pt; margin-bottom: 5px;">
            ${distrito}, aos ${diaAtual} de ${mesAtual} de ${anoAtual}
          </div>

          <div style="display: flex; justify-content: space-between; align-items: flex-end; font-size: 9pt;">
            <div style="width: 33%; text-align: left;">
              <div>Extraí: _________________________</div>
              <div style="margin-top: 8px; text-align: center;">
                <div style="font-weight: bold;">O Chefe da Secretaria</div>
                <div style="border-bottom: 1px solid #111; margin: 14px auto 2px; width: 85%;"></div>
                <div style="font-weight: bold;">${chefeNome}</div>
                <div style="font-size: 8.5pt; font-style: italic;">/${chefeCarreira}/</div>
              </div>
            </div>

            <div style="width: 28%; text-align: center;">
              <div>Conferi: ________________________</div>
              <div style="margin-top: 6px;">
                ${d.qrcodeData ? `<img src="${d.qrcodeData}" style="width: 48px; height: 48px; margin: 0 auto; display: block;" alt="QR Code">` : ''}
                <div style="font-size: 7.5pt; color: #555; margin-top: 1px;">${d.codigoAutenticidade || ''}</div>
              </div>
            </div>

            <div style="width: 33%; text-align: center;">
              <div style="font-weight: bold;">O Director da Escola</div>
              <div style="border-bottom: 1px solid #111; margin: 30px auto 3px; width: 85%;"></div>
              <div style="font-weight: bold;">${directorNome}</div>
              <div style="font-size: 8.5pt; font-style: italic;">/${directorCarreira}/</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderizarCertificado(d) {
  const preview = document.getElementById('printAreaPreview');
  const safeName = (d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
  const ano = d.anoLectivo || d.anoLetivo || '2026';

  preview.style.display = 'block';
  preview.innerHTML = `
    <div class="no-print mb-3 text-end d-flex justify-content-between align-items-center">
      <span class="badge bg-primary"><i class="bi bi-award-fill me-1"></i> Certificado Oficial A4 (Página Única)</span>
      <button class="btn btn-primary btn-sm" onclick="imprimirDocumentoComTitulo('Certificado_${safeName}_${ano}')">
        <i class="bi bi-printer me-2"></i> Imprimir / Guardar em PDF
      </button>
    </div>
    <div class="printable-document">
      ${obterHtmlCertificadoOficial(d)}
    </div>
  `;
}

function renderizarRecibo(d) {
  const preview = document.getElementById('printAreaPreview');
  const safeName = d.aluno.nome.replace(/[^a-zA-Z0-9]/g, '_');
  const carimboDataHora = d.carimboDataHora || (new Date().toLocaleDateString('pt-PT') + ' ' + new Date().toLocaleTimeString('pt-PT'));

  preview.style.display = 'block';
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

  preview.style.display = 'block';
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
  const docs = Array.isArray(lista) ? lista : (lista?.documentos || []);
  const tipoDoc = lista?.tipoDocumento || 'DOCUMENTO';
  const preview = document.getElementById('printAreaPreview');
  preview.style.display = 'block';
  preview.innerHTML = `
    <div class="no-print mb-4 p-3 bg-light border rounded d-flex justify-content-between align-items-center">
      <div>
        <strong class="text-primary fs-5">Lote Processado: ${docs.length} Documentos</strong>
        <span class="d-block small text-muted">Cada documento possui formatação A4 oficial e quebra de página automática.</span>
      </div>
      <button class="btn btn-primary" onclick="window.print()">
        <i class="bi bi-printer me-2"></i> Imprimir Todo o Lote
      </button>
    </div>
    ${docs.map((item, i) => {
      if (tipoDoc === 'CERTIFICADO' || (item.titulo && item.titulo.includes('CERTIFICADO'))) {
        return `<div class="mb-4" style="page-break-after: always; break-after: page; page-break-inside: avoid;">${obterHtmlCertificadoOficial(item)}</div>`;
      } else if (tipoDoc === 'DECLARACAO' || (item.titulo && (item.titulo.includes('DECLARA') || item.titulo.includes('DECLARAÇÃO')))) {
        return `<div class="mb-4" style="page-break-after: always; break-after: page; page-break-inside: avoid;">${obterHtmlDeclaracaoOficial(item)}</div>`;
      } else if (tipoDoc === 'BOLETIM' || (item.titulo && item.titulo.includes('BOLETIM'))) {
        return `<div class="mb-4" style="page-break-after: always; break-after: page; page-break-inside: avoid;">${obterHtmlBoletimOficial(item)}</div>`;
      }
      return `
        <div class="printable-document mb-5 pb-5 border-bottom" style="page-break-after: always; page-break-inside: avoid;">
          <div class="text-center border-bottom pb-3 mb-3">
            <h6 class="fw-bold mb-1">REPÚBLICA DE MOÇAMBIQUE</h6>
            <h5 class="fw-bold text-primary mb-1">${item.titulo || 'DOCUMENTO ESCOLAR OFICIAL'}</h5>
            <small class="text-muted">Aluno: ${item.aluno?.nome} | Matrícula: ${item.aluno?.matricula}</small>
          </div>
          <div class="p-3 small">
            ${item.conteudoHtml || '<p>Documento oficial emitido em lote pelo SIGE.</p>'}
          </div>
        </div>
      `;
    }).join('')}
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
      if (document.getElementById('alunoPerfilDataNasc')) {
        document.getElementById('alunoPerfilDataNasc').textContent = a.data_nascimento 
          ? new Date(a.data_nascimento).toLocaleDateString('pt-MZ') 
          : '-';
      }
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

      const banner = document.getElementById('bannerNotasBloqueadas');
      const tabelaContainer = document.getElementById('tabelaAlunoNotasCorpo')?.closest('.table-responsive');

      if (d.permitirVisualizacaoNotas === false) {
        if (banner) banner.style.display = 'block';
        if (tabelaContainer) tabelaContainer.style.display = 'none';
        document.getElementById('alunoMediaGeral').textContent = '--';
        return;
      } else {
        if (banner) banner.style.display = 'none';
        if (tabelaContainer) tabelaContainer.style.display = 'block';
      }

      document.getElementById('alunoMediaGeral').textContent = d.mediaGeral ? `${Math.round(d.mediaGeral)} valores` : '--';
      
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


// Cascata de Filtros: Classe -> Turma
function filtrarAlocacoesCadernetaPorClasse() {
  const classe = document.getElementById('cadernetaClasseFilter')?.value;
  const selectAloc = document.getElementById('cadernetaAlocacaoSelect');
  if (!selectAloc) return;

  let filtradas = state.alocacoesDocente;
  if (classe) {
    filtradas = filtradas.filter(a => (a.turma.grau_ano || '').includes(classe));
  }

  if (filtradas.length > 0) {
    selectAloc.innerHTML = filtradas.map(a => 
      `<option value="${a.id}">${a.disciplina.nome} — ${a.turma.nome} (${a.turma.grau_ano})</option>`
    ).join('');
    carregarCadernetaDocente();
  } else {
    selectAloc.innerHTML = '<option value="">Nenhuma alocação nesta classe</option>';
  }
}

let turmasCadastradasCache = [];
async function filtrarTurmasPautaPorClasse() {
  const classe = document.getElementById('pautaClasseFilter')?.value;
  const selectTurma = document.getElementById('pautaTurmaSelect');
  if (!selectTurma) return;

  if (turmasCadastradasCache.length === 0) {
    const res = await apiFetch('/api/v1/escola-admin/turmas');
    if (res.success) turmasCadastradasCache = res.data;
  }

  let turmasFiltradas = turmasCadastradasCache;
  if (classe) {
    turmasFiltradas = turmasFiltradas.filter(t => (t.grau_ano || '').includes(classe));
  }

  if (turmasFiltradas.length > 0) {
    selectTurma.innerHTML = turmasFiltradas.map(t => 
      `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`
    ).join('');
    alternarVisualizacaoPautaTurma();
  } else {
    selectTurma.innerHTML = '<option value="">Nenhuma turma nesta classe</option>';
  }
}



async function toggleVisibilidadeNotasDap() {
  try {
    const res = await apiFetch('/api/v1/escola-admin/toggle-notas', { method: 'PUT' });
    if (res.success) {
      const ativa = res.data.permitir_visualizacao_notas;
      atualizarBotaoToggleNotasDap(ativa);
      alert(res.message);
    }
  } catch (err) {
    alert(err.message || 'Erro ao alterar visibilidade de notas');
  }
}

function atualizarBotaoToggleNotasDap(permitir) {
  const btn = document.getElementById('btnToggleNotasDap');
  const icon = document.getElementById('iconToggleNotasDap');
  const label = document.getElementById('labelToggleNotasDap');
  if (!btn || !label) return;

  if (permitir) {
    btn.className = 'btn btn-outline-success btn-sm ped-only';
    if (icon) icon.className = 'bi bi-eye-fill me-1';
    label.textContent = 'Notas Alunos: Visíveis';
  } else {
    btn.className = 'btn btn-outline-danger btn-sm ped-only';
    if (icon) icon.className = 'bi bi-eye-slash-fill me-1';
    label.textContent = 'Notas Alunos: Ocultas';
  }
}



async function carregarPerfilDocenteIndividual() {
  const container = document.getElementById('perfilDocenteConteudo');
  if (!container) return;

  container.innerHTML = '<div class="col-12 text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar o seu perfil...</p></div>';

  try {
    const res = await apiFetch('/api/v1/professores/meu-perfil');
    if (!res.success) return;
    const p = res.data;

    const turmasCards = (p.alocacoes || []).map(al => `
      <div class="col-md-4">
        <div class="card border p-3 h-100 shadow-sm">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="badge bg-primary">${al.turma?.grau_ano || 'Ensino Geral'}</span>
            <small class="text-muted">${al.turma?.turno || 'Diurno'}</small>
          </div>
          <h6 class="fw-bold mb-1">${al.disciplina?.nome} (${al.disciplina?.codigo})</h6>
          <p class="small text-muted mb-3">Turma: <strong>${al.turma?.nome}</strong> | Sala: ${al.turma?.sala || '-'}</p>
          <button class="btn btn-outline-primary btn-sm w-100 mt-auto" onclick="abrirCadernetaAlocacao('${al.id}')">
            <i class="bi bi-journal-check me-1"></i> Abrir Caderneta
          </button>
        </div>
      </div>
    `).join('') || '<div class="col-12"><p class="text-muted">Nenhuma disciplina alocada actualmente.</p></div>';

    container.innerHTML = `
      <div class="col-md-4">
        <div class="card p-3 border text-center">
          <i class="bi bi-person-circle fs-1 text-primary mb-2"></i>
          <h5 class="fw-bold mb-0">${p.nome} ${p.apelido || ''}</h5>
          <span class="badge bg-primary bg-opacity-10 text-primary mt-1 mb-2">${p.carreira || 'Docente'}</span>
          <p class="small text-muted mb-1"><i class="bi bi-book me-1"></i>Especialidade: <strong>${p.especialidade}</strong></p>
          <p class="small text-muted mb-1"><i class="bi bi-telephone me-1"></i>${p.telefone || '-'}</p>
          <p class="small text-muted mb-0"><i class="bi bi-envelope me-1"></i>${p.email}</p>
        </div>
      </div>

      <div class="col-md-8">
        <div class="card p-3 border h-100">
          <h6 class="fw-bold mb-3 text-primary border-bottom pb-2">Dados Funcionais e Institucionais</h6>
          <div class="row g-2 small">
            <div class="col-md-6"><strong>Nacionalidade:</strong> ${p.nacionalidade || 'Moçambicana'}</div>
            <div class="col-md-6"><strong>Província:</strong> ${p.provincia || '-'}</div>
            <div class="col-md-6"><strong>Distrito:</strong> ${p.distrito || '-'}</div>
            <div class="col-md-6"><strong>Documento:</strong> ${p.tipo_documento || 'BI'} (${p.numero_documento || '-'})</div>
            <div class="col-md-6"><strong>Carga Horária:</strong> ${p.carga_horaria_semanal || 20}h semanais</div>
            <div class="col-md-6"><strong>Instituição:</strong> ${p.escola?.nome || '-'}</div>
          </div>
        </div>
      </div>

      <div class="col-12">
        <h6 class="fw-bold mb-3 text-dark border-bottom pb-2"><i class="bi bi-collection me-2"></i>As Minhas Turmas e Disciplinas Alocadas</h6>
        <div class="row g-3">
          ${turmasCards}
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="col-12 text-center text-danger py-4"><i class="bi bi-exclamation-circle me-1"></i>${err.message || 'Erro ao carregar perfil'}</div>`;
  }
}

function abrirCadernetaAlocacao(alocId) {
  state.alocacaoAtualId = alocId;
  const select = document.getElementById('cadernetaAlocacaoSelect');
  if (select) select.value = alocId;
  navegarPara('caderneta');
  carregarCadernetaDocente();
}



let cacheUsuariosCofre = [];

async function carregarCofreUsuarios() {
  const tbody = document.getElementById('tabelaCofreUsuariosCorpo');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A aceder ao cofre seguro...</p></td></tr>';

  try {
    const res = await apiFetch('/api/v1/escola-admin/usuarios-credenciais');
    if (!res.success) return;
    cacheUsuariosCofre = res.data;
    renderizarTabelaCofre(cacheUsuariosCofre);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4"><i class="bi bi-shield-x me-1"></i>${err.message || 'Acesso não autorizado ao cofre'}</td></tr>`;
  }
}

function renderizarTabelaCofre(lista) {
  const tbody = document.getElementById('tabelaCofreUsuariosCorpo');
  if (!tbody) return;

  if (lista.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">Nenhum utilizador encontrado.</td></tr>';
    return;
  }

  tbody.innerHTML = lista.map(u => {
    let dtAcesso = 'Nunca';
    if (u.ultimo_acesso) {
      const dt = new Date(u.ultimo_acesso);
      dtAcesso = dt.toLocaleDateString('pt-PT') + ' ' + dt.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
    }

    return `
      <tr>
        <td><strong>${u.nome}</strong></td>
        <td><code>${u.email}</code></td>
        <td><span class="badge bg-secondary">${u.role}</span></td>
        <td>${u.telefone || '-'}</td>
        <td><small class="text-muted">${dtAcesso}</small></td>
        <td><span class="badge ${u.ativo ? 'bg-success' : 'bg-danger'}">${u.ativo ? 'Activo' : 'Inactivo'}</span></td>
        <td class="text-end">
          <button class="btn btn-outline-warning btn-sm" onclick="modalRedefinirSenhaUsuario('${u.id}', '${u.nome.replace(/'/g, "\\'")}')">
            <i class="bi bi-key me-1"></i> Nova Senha
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function filtrarUsuariosCofre() {
  const termo = (document.getElementById('filtroUsuarioCofre')?.value || '').toLowerCase();
  const role = document.getElementById('filtroRoleCofre')?.value || '';

  const filtrados = cacheUsuariosCofre.filter(u => {
    const bateTexto = u.nome.toLowerCase().includes(termo) || u.email.toLowerCase().includes(termo);
    const bateRole = !role || u.role === role;
    return bateTexto && bateRole;
  });

  renderizarTabelaCofre(filtrados);
}

function modalRedefinirSenhaUsuario(userId, userNome) {
  abrirModal(`Redefinir Palavra-passe: ${userNome}`, `
    <form id="formRedefinirSenhaUsuario">
      <p class="small text-muted mb-3">Defina a nova palavra-passe para o utilizador <strong>${userNome}</strong>.</p>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nova Palavra-passe</label>
        <input type="password" id="novaSenhaUsuarioInput" class="form-control" placeholder="Mínimo 6 caracteres" required minlength="6">
      </div>
      <button type="submit" class="btn btn-warning w-100">
        <i class="bi bi-check-lg me-1"></i> Gravar Nova Senha
      </button>
    </form>
  `);

  document.getElementById('formRedefinirSenhaUsuario').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const novaSenha = document.getElementById('novaSenhaUsuarioInput').value;
      const res = await apiFetch(`/api/v1/auth/usuarios/${userId}/redefinir-senha`, {
        method: 'PUT',
        body: JSON.stringify({ novaSenha })
      }).catch(async () => {
        // Fallback genérico para rota de utilizador
        return apiFetch(`/api/v1/escola-admin/administrativos/${userId}`, {
          method: 'PUT',
          body: JSON.stringify({ senha: novaSenha })
        });
      });

      alert('Palavra-passe actualizada com sucesso!');
      fecharModal();
      carregarCofreUsuarios();
    } catch (err) {
      alert(err.message || 'Erro ao actualizar palavra-passe');
    }
  });
}



let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const btn = document.getElementById('btnInstallPwa');
  if (btn) btn.classList.remove('d-none');
});

async function instalarPwa() {
  if (!deferredPrompt) {
    alert('A aplicação SIGE já está pronta para uso no seu navegador.');
    return;
  }
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  if (outcome === 'accepted') {
    const btn = document.getElementById('btnInstallPwa');
    if (btn) btn.classList.add('d-none');
  }
  deferredPrompt = null;
}


function renderizarPautaGeralImpressao(d) {
  const preview = document.getElementById('printAreaPreview');
  preview.style.display = 'block';
  const ano = d.turma?.ano_letivo || '2026';
  const turmaId = d.turma?.id;
  const safeTurma = (d.turma?.nome || 'Turma').replace(/[^a-zA-Z0-9]/g, '_');

  const formatNota = (val) => {
    if (val === null || val === undefined || isNaN(val) || val <= 0) return '<span class="text-muted">-</span>';
    const num = Number(val);
    const cls = num >= 9.5 ? 'text-dark fw-semibold' : 'text-danger fw-bold';
    return `<span class="${cls}">${Math.round(num)}</span>`;
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
      badgeResultado = '<span class="badge bg-success px-2 py-1">Aprovado</span>';
    } else if (a.resultadoFinal === 'R') {
      badgeResultado = '<span class="badge bg-danger px-2 py-1">Reprovado</span>';
    } else if (a.resultadoFinal === 'D') {
      badgeResultado = '<span class="badge bg-warning text-dark px-2 py-1">Desistiu</span>';
    } else if (a.resultadoFinal === 'T') {
      badgeResultado = '<span class="badge bg-info text-dark px-2 py-1">Transferido</span>';
    } else {
      badgeResultado = `<span class="badge bg-secondary px-2 py-1">${a.resultadoFinal}</span>`;
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

  preview.innerHTML = `
    <div class="no-print mb-3 p-3 bg-light border rounded d-flex justify-content-between align-items-center flex-wrap gap-2">
      <div>
        <strong class="text-primary fs-5"><i class="bi bi-table me-2"></i>Pauta Geral: ${d.turma.nome} (${d.turma.grau_ano})</strong>
        <span class="d-block small text-muted">Ano Lectivo: ${ano} | Turno: ${d.turma.turno || 'Diurno'} | Director de Turma: ${d.turma.director_turma || '-'}</span>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-success btn-sm fw-semibold" onclick="exportarPautaGeralExcel('${turmaId}', '${ano}')">
          <i class="bi bi-file-earmark-excel me-1"></i> Exportar Excel (.xlsx)
        </button>
        <button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarPautaGeralPdf()">
          <i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF (A4 Paisagem)
        </button>
        <button class="btn btn-primary btn-sm fw-semibold" onclick="imprimirDocumentoComTitulo('Pauta_${safeTurma}_${ano}')">
          <i class="bi bi-printer me-1"></i> Imprimir
        </button>
      </div>
    </div>

    <div id="subViewPautaGeral" class="printable-document p-3 bg-white border rounded shadow-sm" style="overflow-x: auto;">
      <!-- Cabeçalho Oficial -->
      <div class="text-center border-bottom pb-2 mb-3">
        <img src="/img/emblema-mocambique.png" style="width: 52px; height: 52px; margin-bottom: 2px;" alt="Emblema Nacional">
        <h6 class="fw-bold mb-0 text-uppercase">REPÚBLICA DE MOÇAMBIQUE</h6>
        <small class="text-muted fw-semibold text-uppercase">GOVERNO DA PROVÍNCIA DE ${(d.escola.provincia || 'MAPUTO').toUpperCase()} | DISTRITO DE ${(d.escola.distrito || 'CIDADE DE MAPUTO').toUpperCase()}</small>
        <h5 class="fw-bold text-dark my-1">${(d.escola.nome || 'Escola Secundária').toUpperCase()}</h5>
        <div class="fw-bold text-primary small">PAUTA OFICIAL DE APROVEITAMENTO PEDAGÓGICO — ANO LECTIVO ${ano}</div>
        <small class="text-muted">Turma: <strong>${d.turma.nome}</strong> | Classe: <strong>${d.turma.grau_ano}</strong> | Turno: <strong>${d.turma.turno || 'Diurno'}</strong> | Director de Turma: <strong>${d.turma.director_turma || '-'}</strong></small>
      </div>

      <!-- Tabela da Pauta -->
      <div class="table-responsive">
        <table class="table table-bordered table-sm table-hover align-middle text-center small mb-0">
          <thead class="table-light">
            <tr>
              <th rowspan="2" class="align-middle">Nº</th>
              <th rowspan="2" class="align-middle text-start" style="min-width: 180px;">Nome Completo</th>
              <th rowspan="2" class="align-middle text-start" style="min-width: 90px;">Apelido</th>
              <th rowspan="2" class="align-middle">Gén</th>
              ${thDisciplinas}
              <th colspan="3" class="bg-light">Médias Trimestrais</th>
              <th colspan="4" class="bg-light">Disciplinas Negativas</th>
              <th rowspan="2" class="align-middle bg-primary text-white fw-bold">Média Geral</th>
              <th rowspan="2" class="align-middle bg-secondary text-white fw-bold">Resultado</th>
            </tr>
            <tr>
              ${thSubDisciplinas}
              <th>1º</th><th>2º</th><th>3º</th>
              <th>1º</th><th>2º</th><th>3º</th><th>Total</th>
            </tr>
          </thead>
          <tbody>
            ${trsAlunos}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// ==================== PAINEL DO DIRECTOR DE TURMA ====================
let dtTurmaAtivaId = null;
let dtAbaAtiva = 'pauta';

async function carregarPainelDirectorTurma() {
  const select = document.getElementById('dtTurmaSelect');
  if (!select) return;

  try {
    const res = await apiFetch('/api/v1/escola-admin/turmas');
    if (!res.success || !res.data.length) {
      select.innerHTML = '<option value="">Nenhuma turma cadastrada</option>';
      return;
    }

    const turmas = res.data;
    const turmasDirigidas = turmas.filter(t => 
      (t.director_turma_id && (t.director_turma_id === state.user?.id || t.director_turma_id === state.user?.professor_id)) ||
      (t.director_turma && (t.director_turma.id === state.user?.professor_id || t.director_turma.nome?.toLowerCase() === state.user?.nome?.toLowerCase()))
    );

    select.innerHTML = turmas.map(t => {
      const isMinha = turmasDirigidas.some(m => m.id === t.id);
      return `<option value="${t.id}">${t.nome} (${t.grau_ano} - ${t.turno || 'Diurno'})${isMinha ? ' ⭐ (Sua Turma de Direcção)' : ''}</option>`;
    }).join('');

    if (turmasDirigidas.length > 0) {
      dtTurmaAtivaId = turmasDirigidas[0].id;
    } else if (!dtTurmaAtivaId && turmas.length > 0) {
      dtTurmaAtivaId = turmas[0].id;
    }

    if (dtTurmaAtivaId) {
      select.value = dtTurmaAtivaId;
      await aoSelecionarTurmaDT(dtTurmaAtivaId);
    }
  } catch (err) {
    select.innerHTML = '<option value="">Erro ao carregar turmas</option>';
  }
}

async function aoSelecionarTurmaDT(turmaId) {
  if (!turmaId) return;
  dtTurmaAtivaId = turmaId;

  // Carregar parâmetros salvos do conselho
  const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
  const cp = savedParamsRaw ? JSON.parse(savedParamsRaw) : {};

  document.getElementById('dtPresidenteT1').value = cp.presidenteT1 || 'Fernando José Mandamule';
  document.getElementById('dtPresidenteT2').value = cp.presidenteT2 || 'Fernando José Mandamule';
  document.getElementById('dtPresidenteT3').value = cp.presidenteT3 || 'Fernando José Mandamule';

  document.getElementById('dtDataT1').value = cp.dataT1 || '26/05/2026';
  document.getElementById('dtDataT2').value = cp.dataT2 || '01/09/2026';
  document.getElementById('dtDataT3').value = cp.dataT3 || '15/11/2026';

  document.getElementById('dtHIni1').value = cp.horaInicioT1 || '09';
  document.getElementById('dtMIni1').value = cp.minInicioT1 || '30';
  document.getElementById('dtHFim1').value = cp.horaFimT1 || '10';
  document.getElementById('dtMFim1').value = cp.minFimT1 || '00';

  document.getElementById('dtHIni2').value = cp.horaInicioT2 || '09';
  document.getElementById('dtMIni2').value = cp.minInicioT2 || '30';
  document.getElementById('dtHFim2').value = cp.horaFimT2 || '11';
  document.getElementById('dtMFim2').value = cp.minFimT2 || '00';

  document.getElementById('dtHIni3').value = cp.horaInicioT3 || '09';
  document.getElementById('dtMIni3').value = cp.minInicioT3 || '30';
  document.getElementById('dtHFim3').value = cp.horaFimT3 || '11';
  document.getElementById('dtMFim3').value = cp.minFimT3 || '00';

  await carregarDadosTurmaDT();
}

function salvarParametrosSessaoDT() {
  if (!dtTurmaAtivaId) return alert('Selecione uma turma primeiro');

  const params = {
    presidenteT1: document.getElementById('dtPresidenteT1').value,
    presidenteT2: document.getElementById('dtPresidenteT2').value,
    presidenteT3: document.getElementById('dtPresidenteT3').value,
    dataT1: document.getElementById('dtDataT1').value,
    dataT2: document.getElementById('dtDataT2').value,
    dataT3: document.getElementById('dtDataT3').value,
    horaInicioT1: document.getElementById('dtHIni1').value,
    minInicioT1: document.getElementById('dtMIni1').value,
    horaFimT1: document.getElementById('dtHFim1').value,
    minFimT1: document.getElementById('dtMFim1').value,
    horaInicioT2: document.getElementById('dtHIni2').value,
    minInicioT2: document.getElementById('dtMIni2').value,
    horaFimT2: document.getElementById('dtHFim2').value,
    minFimT2: document.getElementById('dtMFim2').value,
    horaInicioT3: document.getElementById('dtHIni3').value,
    minInicioT3: document.getElementById('dtMIni3').value,
    horaFimT3: document.getElementById('dtHFim3').value,
    minFimT3: document.getElementById('dtMFim3').value
  };

  localStorage.setItem('sige_acta_params_' + dtTurmaAtivaId, JSON.stringify(params));
  alert('Parâmetros da sessão do conselho salvos com sucesso! A Acta da turma foi atualizada.');
  carregarDadosTurmaDT();
}

function alternarAbaDT(aba) {
  dtAbaAtiva = aba;
  document.getElementById('dtTabPautaBtn').className = 'nav-link fw-bold ' + (aba === 'pauta' ? 'active' : '');
  document.getElementById('dtTabActaBtn').className = 'nav-link fw-bold ' + (aba === 'acta' ? 'active' : '');
  carregarDadosTurmaDT();
}

async function carregarDadosTurmaDT() {
  if (!dtTurmaAtivaId) return;
  const container = document.getElementById('dtDocumentoContainer');
  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar documento oficial da turma...</p></div>';

  try {
    if (dtAbaAtiva === 'pauta') {
      const res = await apiFetch(`/api/v1/pautas/turma/${dtTurmaAtivaId}/completa`);
      if (res.success) {
        const d = res.data;
        container.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom flex-wrap gap-2">
            <div>
              <h6 class="fw-bold text-dark mb-0">Pauta Geral: ${d.turma.nome} (${d.turma.grau_ano})</h6>
              <small class="text-muted">Ano Lectivo ${d.turma.ano_letivo} | Turno ${d.turma.turno || 'Diurno'}</small>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-outline-success btn-sm fw-semibold" onclick="exportarPautaGeralExcel('${dtTurmaAtivaId}', '${d.turma.ano_letivo}')">
                <i class="bi bi-file-earmark-excel me-1"></i> Exportar Excel (.xlsx)
              </button>
              <button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarPautaGeralPdf()">
                <i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF
              </button>
              <button class="btn btn-primary btn-sm fw-semibold" onclick="window.print()">
                <i class="bi bi-printer me-1"></i> Imprimir
              </button>
            </div>
          </div>
          <div id="subViewPautaGeral" class="table-responsive">
            <!-- Tabela idêntica para exportação e impressão -->
            ${gerarTabelaPautaHtml(d)}
          </div>
        `;
      }
    } else {
      // Acta do Conselho
      await carregarActaConselho(dtTurmaAtivaId);
      const containerActa = document.getElementById('containerActaConselhoCorpo');
      if (containerActa) {
        container.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom flex-wrap gap-2">
            <div>
              <h6 class="fw-bold text-dark mb-0">Acta Oficial do Conselho de Avaliação</h6>
              <small class="text-muted">Modelo Oficial MINEDH Moçambique</small>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-outline-success btn-sm fw-semibold" onclick="exportarActaConselhoExcel('${dtTurmaAtivaId}')">
                <i class="bi bi-file-earmark-excel me-1"></i> Exportar Excel (.xlsx)
              </button>
              <button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarActaConselhoPdf()">
                <i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF
              </button>
              <button class="btn btn-primary btn-sm fw-semibold" onclick="window.print()">
                <i class="bi bi-printer me-1"></i> Imprimir
              </button>
            </div>
          </div>
          <div id="subViewActaConselho">
            ${containerActa.innerHTML}
          </div>
        `;
      }
    }
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">Erro ao carregar dados da turma: ${err.message}</div>`;
  }
}

function gerarTabelaPautaHtml(d) {
  const formatNota = (val) => {
    if (val === null || val === undefined || isNaN(val) || val <= 0) return '<span class="text-muted">-</span>';
    const num = Number(val);
    const cls = num >= 9.5 ? 'text-dark fw-semibold' : 'text-danger fw-bold';
    return `<span class="${cls}">${Math.round(num)}</span>`;
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
      badgeResultado = '<span class="badge bg-success px-2 py-1">A</span>';
    } else if (a.resultadoFinal === 'R') {
      badgeResultado = '<span class="badge bg-danger px-2 py-1">R</span>';
    } else if (a.resultadoFinal === 'D') {
      badgeResultado = '<span class="badge bg-warning text-dark px-2 py-1">D</span>';
    } else {
      badgeResultado = `<span class="badge bg-info text-dark px-2 py-1">${a.resultadoFinal}</span>`;
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

  return `
    <table class="table table-bordered table-sm table-hover align-middle text-center small mb-0">
      <thead class="table-light">
        <tr>
          <th rowspan="2" class="align-middle">Nº</th>
          <th rowspan="2" class="align-middle text-start" style="min-width: 170px;">Nome Completo</th>
          <th rowspan="2" class="align-middle text-start" style="min-width: 90px;">Apelido</th>
          <th rowspan="2" class="align-middle">Gén</th>
          ${thDisciplinas}
          <th colspan="3" class="bg-light">Médias</th>
          <th colspan="4" class="bg-light">Negativas</th>
          <th rowspan="2" class="align-middle bg-primary text-white fw-bold">Média Final</th>
          <th rowspan="2" class="align-middle bg-secondary text-white fw-bold">Resultado</th>
        </tr>
        <tr>
          ${thSubDisciplinas}
          <th>1º</th><th>2º</th><th>3º</th>
          <th>1º</th><th>2º</th><th>3º</th><th>Total</th>
        </tr>
      </thead>
      <tbody>
        ${trsAlunos}
      </tbody>
    </table>
  `;
}

async function eliminarEscolaSuperAdmin(escolaId, nome) {
  if (!confirm(`ATENÇÃO ENGENHEIRO:\nTem a certeza que deseja ELIMINAR DEFINITIVAMENTE a escola [${nome}] e todos os seus dados?\nEsta operação não pode ser revertida!`)) return;

  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}`, {
      method: 'DELETE'
    });
    if (res.success) {
      alert(res.message || 'Escola eliminada com sucesso');
      carregarPainelSaaS();
      carregarEscolasSuperAdminSelect();
    }
  } catch (err) {
    alert(err.message || 'Erro ao eliminar escola');
  }
}

async function descarregarExtratoEscolaSuperAdmin(escolaId) {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/comprovativo-contrato`);
    if (!res.success) throw new Error(res.message || 'Falha ao obter comprovativo');

    const c = res.data;
    const agora = new Date();
    const dataEmissao = agora.toLocaleDateString('pt-PT') + ' ' + agora.toLocaleTimeString('pt-PT');

    abrirModal('Extrato Oficial de Contrato de Prestação de Serviços SIGE', `
      <div id="printExtratoContrato" class="p-4 bg-white" style="font-family: 'Times New Roman', serif;">
        <div class="text-center border-bottom pb-3 mb-4">
          <img src="/img/emblema-mocambique.png" style="width: 50px; height: 50px; margin-bottom: 4px;" alt="Emblema Nacional">
          <h5 class="fw-bold mb-0 text-uppercase">REPÚBLICA DE MOÇAMBIQUE</h5>
          <h6 class="fw-bold text-primary mb-1">SIGE — SISTEMA INTEGRADO DE GESTÃO ESCOLAR</h6>
          <small class="text-muted">EXTRATO OFICIAL DE LICENCIAMENTO E TERMO DE CONTRATO SAAS</small>
        </div>

        <div class="row g-3 mb-4 small">
          <div class="col-6">
            <strong>Instituição de Ensino:</strong> ${c.escola.nome}<br>
            <strong>NUIT / NIF:</strong> ${c.escola.nif_cnpj}<br>
            <strong>Localização:</strong> ${c.escola.distrito || '-'}, ${c.escola.provincia || '-'}<br>
            <strong>Contacto:</strong> ${c.escola.telefone || '-'} | ${c.escola.email}
          </div>
          <div class="col-6 text-end">
            <strong>Referência Contratual:</strong> ${c.comprovativo_numero}<br>
            <strong>Plano Subscrito:</strong> <span class="badge bg-primary">${c.plano.nome}</span><br>
            <strong>Estado da Licença:</strong> <span class="badge bg-success">${c.status_atual}</span><br>
            <strong>Valor Contratual:</strong> ${c.assinatura.valor.toLocaleString('pt-PT')} MZN
          </div>
        </div>

        <table class="table table-bordered table-sm small mb-4">
          <tr class="table-light"><th colspan="2" class="text-center fw-bold">VIGÊNCIA E CLÁUSULAS CONTRATUAIS</th></tr>
          <tr><th class="w-40">Data de Início:</th><td>${new Date(c.assinatura.data_inicio).toLocaleDateString('pt-PT')}</td></tr>
          <tr><th>Data de Vencimento:</th><td>${new Date(c.assinatura.data_fim).toLocaleDateString('pt-PT')}</td></tr>
          <tr><th>Capacidade Licenciada:</th><td>Até ${c.plano.max_alunos} alunos matriculados e ${c.plano.max_professores} docentes</td></tr>
          <tr><th>Alunos Ativos Registados:</th><td>${c.estatisticas.total_alunos} alunos</td></tr>
          <tr><th>Corpo Docente Ativo:</th><td>${c.estatisticas.total_professores} professores</td></tr>
          <tr><th>Turmas Cadastradas:</th><td>${c.estatisticas.total_turmas} turmas ativas</td></tr>
        </table>

        <div class="alert alert-light border small text-muted text-center py-2 mb-4">
          Extrato emitido aos <strong>${dataEmissao}</strong> | Assinado digitalmente pelo Engenheiro de Sistemas SuperAdmin
        </div>

        <div class="row text-center pt-4 border-top small">
          <div class="col-6">
            <p class="mb-0 border-top pt-2 mx-4 fw-bold">O Engenheiro do Sistema (SuperAdmin)</p>
            <small class="text-muted">mandamulefj.@sige.com</small>
          </div>
          <div class="col-6">
            <p class="mb-0 border-top pt-2 mx-4 fw-bold">A Direcção da Escola</p>
            <small class="text-muted">${c.escola.nome}</small>
          </div>
        </div>
      </div>
      <div class="text-end mt-3 no-print">
        <button class="btn btn-primary btn-sm" onclick="imprimirDocumentoComTitulo('Extrato_Contrato_${c.escola.nome.replace(/\s+/g, '_')}')">
          <i class="bi bi-printer me-1"></i> Imprimir / Descarregar em PDF
        </button>
      </div>
    `);
  } catch (err) {
    alert(err.message || 'Erro ao emitir extrato');
  }
}

// ==================== ESTATÍSTICA DO APROVEITAMENTO PEDAGÓGICO ESCOLAR ====================
async function carregarEstatisticasAproveitamento() {
  const container = document.getElementById('containerEstatisticasDocumento');
  if (!container) return;

  const ano = document.getElementById('statAnoFiltro')?.value || '2026';
  const periodo = document.getElementById('statPeriodoFiltro')?.value || 'GLOBAL';

  container.innerHTML = `
    <div class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="small text-muted mt-2">A compilar estatísticas gerais do aproveitamento pedagógico (${ano})...</p>
    </div>
  `;

  try {
    const res = await apiFetch(`/api/v1/pautas/estatisticas-gerais?anoLetivo=${ano}&periodo=${periodo}`);
    if (!res.success || !res.data) {
      container.innerHTML = `<div class="alert alert-warning text-center">Nenhum registo de notas ou turmas disponível para o ano lectivo ${ano}.</div>`;
      return;
    }

    const d = res.data;
    const ge = d.geralEscola;

    // Atualizar cartões KPI superiores
    if (document.getElementById('statKpiAprovacao')) {
      document.getElementById('statKpiAprovacao').textContent = `${ge.aprovados.pct}%`;
      document.getElementById('statKpiAprovacaoSub').textContent = `${ge.aprovados.total} Aprovados (${ge.aprovados.h} H / ${ge.aprovados.m} M)`;
      document.getElementById('statKpiReprovacao').textContent = `${ge.reprovados.pct}%`;
      document.getElementById('statKpiReprovacaoSub').textContent = `${ge.reprovados.total} Não transitam (${ge.reprovados.h} H / ${ge.reprovados.m} M)`;
      document.getElementById('statKpiAvaliados').textContent = `${ge.avaliados.total}`;
      document.getElementById('statKpiAvaliadosSub').textContent = `${ge.avaliados.h} H / ${ge.avaliados.m} M (Inscritos: ${ge.inscritos.total})`;
      document.getElementById('statKpiTurmas').textContent = `${d.porTurma.length}`;
      document.getElementById('statKpiTurmasSub').textContent = `${d.porClasse.length} Níveis de Ensino Secundário`;
    }

    // Renderizar Tabelas Estatísticas
    container.innerHTML = `
      <!-- Cabeçalho Institucional Oficial para Relatório e Impressão -->
      <div class="text-center pb-3 mb-4 border-bottom position-relative">
        <img src="/img/emblema-mocambique.png" style="width: 52px; height: 52px; object-fit: contain; margin-bottom: 3px;" alt="Emblema Nacional">
        <h6 class="fw-bold mb-0 text-uppercase">REPÚBLICA DE MOÇAMBIQUE</h6>
        <div class="text-muted small fw-semibold">MINISTÉRIO DA EDUCAÇÃO E DESENVOLVIMENTO HUMANO</div>
        <h5 class="fw-bold text-primary mt-2 mb-0">${d.escola.nome.toUpperCase()}</h5>
        <div class="badge bg-primary bg-opacity-10 text-primary border border-primary px-3 py-2 mt-2 fs-6">
          MAPA CONSOLIDADO DO RENDIMENTO E APROVEITAMENTO PEDAGÓGICO — ${ano} (${periodo === 'GLOBAL' ? 'MÉDIA ANUAL / MFD' : periodo})
        </div>
      </div>

      <!-- SECÇÃO 1: RESUMO GERAL DA ESCOLA -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-building me-1 text-primary"></i> 1. Resumo Global da Escola</h6>
          <span class="badge bg-secondary">${d.porTurma.length} Turmas Activas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-sm text-center align-middle small mb-0">
            <thead class="table-dark">
              <tr>
                <th colspan="3">Inscritos / Matriculados</th>
                <th colspan="3">Efectivo Avaliado</th>
                <th colspan="4">Aproveitamento Positivo (Aprovados)</th>
                <th colspan="4">Não Aproveitamento (Reprovados)</th>
              </tr>
              <tr class="table-light text-dark">
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th><th>% Tx Aprov.</th>
                <th>HM</th><th>M</th><th>Total</th><th>% Tx Reprov.</th>
              </tr>
            </thead>
            <tbody>
              <tr class="fw-bold fs-6">
                <td>${ge.inscritos.h}</td><td>${ge.inscritos.m}</td><td class="bg-light">${ge.inscritos.total}</td>
                <td>${ge.avaliados.h}</td><td>${ge.avaliados.m}</td><td class="bg-light">${ge.avaliados.total}</td>
                <td class="text-success">${ge.aprovados.h}</td><td class="text-success">${ge.aprovados.m}</td>
                <td class="text-success bg-light">${ge.aprovados.total}</td>
                <td class="text-success bg-success bg-opacity-10">${ge.aprovados.pct}%</td>
                <td class="text-danger">${ge.reprovados.h}</td><td class="text-danger">${ge.reprovados.m}</td>
                <td class="text-danger bg-light">${ge.reprovados.total}</td>
                <td class="text-danger bg-danger bg-opacity-10">${ge.reprovados.pct}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- SECÇÃO 2: RESUMO GERAL POR CLASSE (7ª A 12ª CLASSE) -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-layers-fill me-1 text-primary"></i> 2. Rendimento por Classe (7ª, 8ª, 9ª, 10ª, 11ª, 12ª)</h6>
          <span class="badge bg-primary">${d.porClasse.length} Classes Registadas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-hover table-sm text-center align-middle small mb-0">
            <thead class="table-primary">
              <tr>
                <th rowspan="2" class="align-middle text-start">Nível / Classe</th>
                <th rowspan="2" class="align-middle">Turmas</th>
                <th colspan="3">Inscritos</th>
                <th colspan="3">Avaliados</th>
                <th colspan="3">Aprovados</th>
                <th rowspan="2" class="align-middle bg-success text-white">% Aproveitamento</th>
                <th colspan="3">Reprovados</th>
                <th rowspan="2" class="align-middle bg-danger text-white">% Reprovação</th>
              </tr>
              <tr class="table-light text-dark">
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
              </tr>
            </thead>
            <tbody>
              ${d.porClasse.map(c => `
                <tr>
                  <td class="text-start fw-bold">${c.classe} Classe</td>
                  <td><span class="badge bg-light text-dark border">${c.turmas}</span></td>
                  <td>${c.inscritos.h}</td><td>${c.inscritos.m}</td><td class="fw-bold bg-light">${c.inscritos.total}</td>
                  <td>${c.avaliados.h}</td><td>${c.avaliados.m}</td><td class="fw-bold bg-light">${c.avaliados.total}</td>
                  <td class="text-success">${c.aprovados.h}</td><td class="text-success">${c.aprovados.m}</td>
                  <td class="text-success fw-bold bg-light">${c.aprovados.total}</td>
                  <td class="fw-bold ${c.aprovados.pct >= 50 ? 'text-success' : 'text-danger'}">${c.aprovados.pct}%</td>
                  <td class="text-danger">${c.reprovados.h}</td><td class="text-danger">${c.reprovados.m}</td>
                  <td class="text-danger fw-bold bg-light">${c.reprovados.total}</td>
                  <td class="fw-bold text-danger">${c.reprovados.pct}%</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- SECÇÃO 3: APROVEITAMENTO POR TURMA -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-people-fill me-1 text-primary"></i> 3. Aproveitamento Pedagógico por Turma</h6>
          <span class="badge bg-info text-dark">${d.porTurma.length} Turmas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-hover table-sm text-center align-middle small mb-0">
            <thead class="table-secondary">
              <tr>
                <th class="text-start">Turma</th>
                <th>Classe</th>
                <th>Turno</th>
                <th class="text-start">Director de Turma</th>
                <th>Inscritos Total</th>
                <th>Avaliados Total</th>
                <th class="text-success">Aprovados</th>
                <th class="bg-success text-white">% Aproveitamento</th>
                <th class="text-danger">Reprovados</th>
                <th class="bg-danger text-white">% Reprovação</th>
              </tr>
            </thead>
            <tbody>
              ${d.porTurma.map(t => `
                <tr>
                  <td class="text-start fw-bold">${t.turmaNome}</td>
                  <td>${t.grau_ano}</td>
                  <td>${t.turno}</td>
                  <td class="text-start">${t.directorTurma}</td>
                  <td>${t.inscritos.total}</td>
                  <td class="fw-bold">${t.avaliados.total}</td>
                  <td class="text-success fw-bold">${t.aprovados.total}</td>
                  <td class="fw-bold ${t.aprovados.pct >= 50 ? 'text-success bg-success bg-opacity-10' : 'text-danger bg-danger bg-opacity-10'}">${t.aprovados.pct}%</td>
                  <td class="text-danger">${t.reprovados.total}</td>
                  <td class="text-danger">${t.reprovados.pct}%</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- SECÇÃO 4: APROVEITAMENTO POR DISCIPLINA -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-book-half me-1 text-primary"></i> 4. Rendimento Comparativo por Disciplina</h6>
          <span class="badge bg-secondary">${d.porDisciplina.length} Disciplinas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-hover table-sm text-center align-middle small mb-0">
            <thead class="table-light">
              <tr>
                <th class="text-start">Disciplina</th>
                <th>Código</th>
                <th>Avaliados (HM)</th>
                <th>Avaliados (M)</th>
                <th>Avaliados Total</th>
                <th class="text-success">Aprovados Total</th>
                <th class="bg-success text-white">% Aproveitamento</th>
                <th class="text-danger">Reprovados Total</th>
                <th class="bg-danger text-white">% Reprovação</th>
                <th class="bg-primary text-white">Média da Disciplina</th>
              </tr>
            </thead>
            <tbody>
              ${d.porDisciplina.map(disc => `
                <tr>
                  <td class="text-start fw-bold">${disc.nome}</td>
                  <td><code>${disc.codigo}</code></td>
                  <td>${disc.avaliados.h}</td>
                  <td>${disc.avaliados.m}</td>
                  <td class="fw-bold">${disc.avaliados.total}</td>
                  <td class="text-success fw-bold">${disc.aprovados.total}</td>
                  <td class="fw-bold ${disc.aprovados.pct >= 50 ? 'text-success bg-success bg-opacity-10' : 'text-danger bg-danger bg-opacity-10'}">${disc.aprovados.pct}%</td>
                  <td class="text-danger">${disc.reprovados.total}</td>
                  <td class="text-danger">${disc.reprovados.pct}%</td>
                  <td class="fw-bold ${disc.mediaFinal !== null && disc.mediaFinal >= 9.5 ? 'text-primary' : 'text-danger'}">
                    ${disc.mediaFinal !== null ? disc.mediaFinal : '-'}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Rodapé Formal de Validação -->
      <div class="row pt-4 mt-4 border-top text-center small no-print">
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-4">O Director Pedagógico (DAP)</p>
        </div>
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-4">O Chefe da Secretaria</p>
        </div>
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-4">O Director da Escola</p>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger text-center">Erro ao carregar estatísticas do aproveitamento: ${err.message || ''}</div>`;
  }
}

async function descarregarEstatisticasPdf() {
  const container = document.getElementById('containerEstatisticasDocumento');
  if (!container) return alert('Carregue as estatísticas primeiro');
  const ano = document.getElementById('statAnoFiltro')?.value || '2026';
  await exportarElementoParaPdf(container, `Estatisticas_Aproveitamento_Pedagogico_${ano}.pdf`, 'landscape');
}

function exportarEstatisticasExcel() {
  const ano = document.getElementById('statAnoFiltro')?.value || '2026';
  const periodo = document.getElementById('statPeriodoFiltro')?.value || 'GLOBAL';
  downloadFicheiroBinario(`/api/v1/pautas/estatisticas-gerais/xlsx?anoLetivo=${ano}&periodo=${periodo}`, `Estatisticas_Aproveitamento_${ano}.xlsx`);
}
