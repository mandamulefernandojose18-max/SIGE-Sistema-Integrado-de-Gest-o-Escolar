/**
 * SIGE - PAINEL-ESCOLA | Dashboard Geral da Escola
 * Ficheiro de código independente do menu: dashboard.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 1. DASHBOARD GERAL ====================
async function carregarDashboardGeral() {
  try {
    const res = await apiFetch('/api/v1/dashboard/overview', { ignoreAuthRedirect: true });
    if (!res.success || !res.data) return;

    const data = res.data;
    const ind = data.indicadores || {
      totalAlunos: data.totalAlunos || 0,
      alunosAtivos: data.alunosAtivos || 0,
      totalProfessores: data.totalProfessores || 0,
      totalRecebido: data.propinasRecebidas || 0,
      totalPendente: data.propinasPendentes || 0,
    };
    const esc = data.escola || { nome: 'SIGE', status: 'ATIVA', diasRestantesAssinatura: 365 };

    const elTotalAlunos = document.getElementById('statTotalAlunos');
    if (elTotalAlunos) elTotalAlunos.textContent = ind.totalAlunos ?? 0;

    const elAlunosAtivos = document.getElementById('statAlunosAtivos');
    if (elAlunosAtivos) elAlunosAtivos.textContent = ind.alunosAtivos ?? 0;

    const elTotalProfs = document.getElementById('statTotalProfessores');
    if (elTotalProfs) elTotalProfs.textContent = ind.totalProfessores ?? 0;

    const elReceitaTotal = document.getElementById('statReceitaTotal');
    if (elReceitaTotal) elReceitaTotal.innerHTML = formatarMoeda(ind.totalRecebido || 0);

    const elReceitaPendente = document.getElementById('statReceitaPendente');
    if (elReceitaPendente) elReceitaPendente.innerHTML = formatarMoeda(ind.totalPendente || 0);

    const elDiasRestantes = document.getElementById('statDiasRestantes');
    if (elDiasRestantes) elDiasRestantes.textContent = (esc.diasRestantesAssinatura ?? 0) + ' dias';

    const stBadge = document.getElementById('statStatusAssinatura');
    if (stBadge) {
      stBadge.textContent = esc.status || 'ATIVA';
      stBadge.className = `badge badge-${(esc.status || 'ativa').toLowerCase()}`;
    }

    // Gráficos
    const resFin = await apiFetch('/api/v1/pagamentos/stats', { ignoreAuthRedirect: true });
    if (resFin && resFin.success && resFin.data) {
      renderizarGraficoDashboardFaturamento(resFin.data.historicoMeses || []);
    }

    const resAlunos = await apiFetch('/api/v1/alunos/stats', { ignoreAuthRedirect: true });
    if (resAlunos && resAlunos.success && resAlunos.data) {
      renderizarGraficoDashboardGenero(resAlunos.data.genero || resAlunos.data.porGenero || { M: 0, F: 0 });
    }
  } catch (err) {
    console.error('Erro ao carregar Dashboard Geral:', err);
  }
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

