/**
 * SIGE - PAINEL-SUPERADMIN | Cofre de Credenciais Master
 * Ficheiro de código independente do menu: usuarios-senhas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 * Pesquisa, filtros (Escola → Perfil) e paginação são feitos no servidor: altura constante para n utilizadores.
 */
// ==================== COFRE DE CREDENCIAIS MASTER ====================
const estadoCofre = { pagina: 1, paginas: 1, temporizador: null, escolasCarregadas: false };
let cacheUsuariosCofre = [];

function _escCofre(v) {
  return typeof escapeHtml === 'function'
    ? escapeHtml(String(v ?? ''))
    : String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function carregarOpcoesEscolasCofre() {
  if (estadoCofre.escolasCarregadas) return;
  const sel = document.getElementById('filtroEscolaCofre');
  if (!sel) return;
  try {
    const res = await apiFetch('/api/v1/saas-admin/escolas-opcoes');
    if (res && res.success && Array.isArray(res.data)) {
      sel.innerHTML = '<option value="">Todas as escolas</option>' + res.data.map(e =>
        `<option value="${_escCofre(e.id)}">${_escCofre(e.codigo ? e.codigo + ' — ' : '')}${_escCofre(e.nome)}</option>`).join('');
      estadoCofre.escolasCarregadas = true;
    }
  } catch (err) {
    console.warn('Não foi possível carregar as escolas para o filtro:', err);
  }
}

async function carregarCofreUsuarios() {
  const container = document.getElementById('tabelaCofreUsuariosCorpo');
  if (!container) return;
  carregarOpcoesEscolasCofre();
  container.innerHTML = '<tr><td colspan="9" class="text-center py-4"><div class="spinner-border text-primary spinner-border-sm me-2"></div>A aceder ao cofre seguro...</td></tr>';

  const params = new URLSearchParams({ pagina: estadoCofre.pagina, tamanho: 25 });
  const escola = document.getElementById('filtroEscolaCofre')?.value;
  const role = document.getElementById('filtroRoleCofre')?.value;
  const q = (document.getElementById('filtroUsuarioCofre')?.value || '').trim();
  if (escola) params.set('escola', escola);
  if (role) params.set('role', role);
  if (q) params.set('q', q);

  try {
    const res = await apiFetch('/api/v1/escola-admin/usuarios-credenciais?' + params.toString());
    if (res && res.success && Array.isArray(res.data)) {
      cacheUsuariosCofre = res.data;
      const meta = res.meta || { total: res.data.length, pagina: 1, paginas: 1 };
      estadoCofre.pagina = meta.pagina;
      estadoCofre.paginas = meta.paginas;
      renderizarTabelaCofreUsuarios(cacheUsuariosCofre);
      const info = document.getElementById('cofrePaginacaoInfo');
      if (info) info.textContent = `${meta.total} utilizador(es) · página ${meta.pagina} de ${meta.paginas}`;
      const ant = document.getElementById('cofrePagAnterior');
      const seg = document.getElementById('cofrePagSeguinte');
      if (ant) ant.disabled = meta.pagina <= 1;
      if (seg) seg.disabled = meta.pagina >= meta.paginas;
    } else {
      container.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-danger">Falha ao carregar credenciais.</td></tr>';
    }
  } catch (err) {
    container.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-danger">Erro: ' + _escCofre(err.message || 'Falha de rede') + '</td></tr>';
  }
}

function renderizarTabelaCofreUsuarios(lista) {
  const tbody = document.getElementById('tabelaCofreUsuariosCorpo');
  if (!tbody) return;

  const dados = Array.isArray(lista) ? lista : [];
  if (dados.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">Nenhum utilizador encontrado para os filtros seleccionados.</td></tr>';
    return;
  }

  tbody.innerHTML = dados.map(u => {
    let dtAcesso = 'Nunca';
    if (u.ultimo_acesso) {
      try {
        const dt = new Date(u.ultimo_acesso);
        dtAcesso = dt.toLocaleDateString('pt-PT') + ' ' + dt.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
      } catch (_) {
        dtAcesso = u.ultimo_acesso;
      }
    }

    const badgeSenha = u.senha_redefinida
      ? '<span class="badge bg-info bg-opacity-10 text-dark border border-info ms-1" style="font-size: 0.68rem;" title="O utilizador personalizou a sua senha">Senha Redefinida</span>'
      : '<span class="badge bg-warning bg-opacity-25 text-dark border border-warning ms-1" style="font-size: 0.68rem;" title="Senha inicial activa: basta repetir o código de acesso">Senha = Código</span>';

    // Valores em atributos data-*: o browser decodifica-os, sem risco de quebrar o JavaScript inline.
    return `
      <tr>
        <td>
          <span class="badge bg-dark text-white font-monospace">${_escCofre(u.codigo_acesso || '-')}</span>
          <div class="mt-1">${badgeSenha}</div>
        </td>
        <td><strong>${_escCofre(u.nome || '-')}</strong></td>
        <td><small>${_escCofre(u.escola_nome || (u.role === 'SUPERADMIN' ? 'Plataforma' : '-'))}</small></td>
        <td><code>${_escCofre(u.email || '-')}</code></td>
        <td><span class="badge bg-secondary">${_escCofre(u.role || '-')}</span></td>
        <td>${_escCofre(u.telefone || '-')}</td>
        <td><small class="text-muted">${_escCofre(dtAcesso)}</small></td>
        <td><span class="badge ${u.ativo ? 'bg-success' : 'bg-danger'}">${u.ativo ? 'Activo' : 'Inactivo'}</span></td>
        <td class="text-end">
          <button class="btn btn-outline-warning btn-sm" data-id="${_escCofre(u.id)}" data-nome="${_escCofre(u.nome || '')}" data-cod="${_escCofre(u.codigo_acesso || '')}" onclick="abrirGestaoSenhaCofre(this)">
            <i class="bi bi-key me-1"></i> Gerir Senha
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function abrirGestaoSenhaCofre(btn) {
  modalRedefinirSenhaUsuario(btn.dataset.id, btn.dataset.nome || '', btn.dataset.cod || '');
}

function renderizarTabelaCofre(lista) {
  renderizarTabelaCofreUsuarios(lista);
}

function filtrarUsuariosCofre(comAtraso) {
  estadoCofre.pagina = 1;
  clearTimeout(estadoCofre.temporizador);
  if (comAtraso === true) {
    estadoCofre.temporizador = setTimeout(carregarCofreUsuarios, 350);
  } else {
    carregarCofreUsuarios();
  }
}

function mudarPaginaCofre(delta) {
  const nova = estadoCofre.pagina + delta;
  if (nova < 1 || nova > estadoCofre.paginas) return;
  estadoCofre.pagina = nova;
  carregarCofreUsuarios();
}

// Exportação global explícita para evitar erros de escopo
window.carregarCofreUsuarios = carregarCofreUsuarios;
window.renderizarTabelaCofreUsuarios = renderizarTabelaCofreUsuarios;
window.renderizarTabelaCofre = renderizarTabelaCofre;
window.filtrarUsuariosCofre = filtrarUsuariosCofre;
window.mudarPaginaCofre = mudarPaginaCofre;
window.abrirGestaoSenhaCofre = abrirGestaoSenhaCofre;
