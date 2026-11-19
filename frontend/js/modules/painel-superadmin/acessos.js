/**
 * SIGE - PAINEL-SUPERADMIN | Auditoria de Acessos SaaS
 * Ficheiro de código independente do menu: acessos.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 * Dados reais de /api/v1/saas-admin/logs-acesso, paginados no servidor (altura constante para n registos).
 */
// ==================== 14. AUDITORIA & ACESSOS ====================
const estadoLogsAcesso = { pagina: 1, paginas: 1, temporizador: null, escolasCarregadas: false };

function _escLog(v) {
  return typeof escapeHtml === 'function'
    ? escapeHtml(String(v ?? ''))
    : String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function carregarOpcoesEscolasLogs() {
  if (estadoLogsAcesso.escolasCarregadas) return;
  const sel = document.getElementById('acessosFiltroEscola');
  if (!sel) return;
  try {
    const res = await apiFetch('/api/v1/saas-admin/escolas-opcoes');
    if (res && res.success && Array.isArray(res.data)) {
      sel.innerHTML = '<option value="">Todas as escolas</option>' + res.data.map(e =>
        `<option value="${_escLog(e.id)}">${_escLog(e.codigo ? e.codigo + ' — ' : '')}${_escLog(e.nome)}</option>`).join('');
      estadoLogsAcesso.escolasCarregadas = true;
    }
  } catch (err) {
    console.warn('Não foi possível carregar as escolas para o filtro:', err);
  }
}

async function carregarLogsAcesso() {
  const tbody = document.getElementById('tabelaLogsAcesso');
  if (!tbody) return;
  carregarOpcoesEscolasLogs();
  tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4"><span class="spinner-border spinner-border-sm me-2"></span>A carregar logs...</td></tr>';
  const params = new URLSearchParams({ pagina: estadoLogsAcesso.pagina, tamanho: 25 });
  const escola = document.getElementById('acessosFiltroEscola')?.value;
  const tipo = document.getElementById('acessosFiltroTipo')?.value;
  const q = (document.getElementById('acessosFiltroBusca')?.value || '').trim();
  if (escola) params.set('escola', escola);
  if (tipo) params.set('tipo', tipo);
  if (q) params.set('q', q);
  try {
    const res = await apiFetch('/api/v1/saas-admin/logs-acesso?' + params.toString());
    if (!res || !res.success || !Array.isArray(res.data)) {
      throw new Error((res && res.message) || 'Resposta inválida do servidor.');
    }
    const meta = res.meta || { total: res.data.length, pagina: 1, paginas: 1 };
    estadoLogsAcesso.pagina = meta.pagina;
    estadoLogsAcesso.paginas = meta.paginas;
    if (res.data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">Sem registos de acesso para os filtros seleccionados.</td></tr>';
    } else {
      tbody.innerHTML = res.data.map(l => {
        const d = l.createdAt ? new Date(l.createdAt) : null;
        const dtStr = d ? d.toLocaleDateString('pt-PT') + ' às ' + d.toLocaleTimeString('pt-PT') : '-';
        const tipoLog = l.tipo || 'DESCONHECIDO';
        const cls = tipoLog === 'LOGIN_SUCESSO' ? 'bg-success' : tipoLog === 'ACESSO_BLOQUEADO_EXPIRADO' ? 'bg-danger' : 'bg-warning text-dark';
        return `
        <tr>
          <td>${_escLog(dtStr)}</td>
          <td><strong>${_escLog(l.usuario ? l.usuario.nome : 'Anónimo / Convidado')}</strong></td>
          <td>${_escLog(l.escola_nome || '-')}</td>
          <td><code>${_escLog(l.ip || '-')}</code></td>
          <td class="small text-muted">${_escLog(l.user_agent || '-')}</td>
          <td><span class="badge ${cls}">${_escLog(tipoLog)}</span></td>
        </tr>`;
      }).join('');
    }
    const info = document.getElementById('acessosPaginacaoInfo');
    if (info) info.textContent = `${meta.total} registo(s) · página ${meta.pagina} de ${meta.paginas}`;
    const ant = document.getElementById('acessosPagAnterior');
    const seg = document.getElementById('acessosPagSeguinte');
    if (ant) ant.disabled = meta.pagina <= 1;
    if (seg) seg.disabled = meta.pagina >= meta.paginas;
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Falha ao carregar os logs: ' + _escLog(err.message || 'erro de rede') + '</td></tr>';
  }
}

function aplicarFiltroLogsAcesso(comAtraso) {
  estadoLogsAcesso.pagina = 1;
  clearTimeout(estadoLogsAcesso.temporizador);
  if (comAtraso) {
    estadoLogsAcesso.temporizador = setTimeout(carregarLogsAcesso, 350);
  } else {
    carregarLogsAcesso();
  }
}

function mudarPaginaLogsAcesso(delta) {
  const nova = estadoLogsAcesso.pagina + delta;
  if (nova < 1 || nova > estadoLogsAcesso.paginas) return;
  estadoLogsAcesso.pagina = nova;
  carregarLogsAcesso();
}

window.carregarLogsAcesso = carregarLogsAcesso;
window.aplicarFiltroLogsAcesso = aplicarFiltroLogsAcesso;
window.mudarPaginaLogsAcesso = mudarPaginaLogsAcesso;
