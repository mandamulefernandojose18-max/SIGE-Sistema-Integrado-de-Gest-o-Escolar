/**
 * SIGE - PAINEL-ESCOLA | Cofre de Credenciais da Escola
 * Ficheiro de código independente do menu: usuarios-senhas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== COFRE DE CREDENCIAIS DA ESCOLA ====================
let cacheUsuariosCofre = [];

async function carregarCofreUsuarios() {
  const container = document.getElementById('tabelaCofreUsuariosCorpo');
  if (!container) return;
  container.innerHTML = '<tr><td colspan="8" class="text-center py-4"><div class="spinner-border text-primary spinner-border-sm me-2"></div>A aceder ao cofre da escola...</td></tr>';
  try {
    const res = await apiFetch('/api/v1/escola-admin/usuarios-credenciais');
    if (res && res.success && Array.isArray(res.data)) {
      cacheUsuariosCofre = res.data;
      renderizarTabelaCofreUsuarios(cacheUsuariosCofre);
    } else {
      container.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-danger">Falha ao carregar credenciais.</td></tr>';
    }
  } catch (err) {
    const safeMsg = (err.message || 'Falha de rede').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    container.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-danger">Erro: ' + safeMsg + '</td></tr>';
  }
}

function renderizarTabelaCofreUsuarios(lista) {
  const tbody = document.getElementById('tabelaCofreUsuariosCorpo');
  if (!tbody) return;

  const dados = Array.isArray(lista) ? lista : [];
  if (dados.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">Nenhum utilizador encontrado no cofre.</td></tr>';
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

    const codEscapado = (u.codigo_acesso || '').replace(/'/g, "\\'");
    const badgeSenha = u.senha_redefinida
      ? '<span class="badge bg-info bg-opacity-10 text-dark border border-info ms-1" style="font-size: 0.68rem;" title="O utilizador personalizou a sua senha">Senha Redefinida</span>'
      : '<span class="badge bg-warning bg-opacity-25 text-dark border border-warning ms-1" style="font-size: 0.68rem;" title="Senha inicial activa: basta repetir o código de acesso">Senha = Código</span>';

    return `
      <tr>
        <td>
          <span class="badge bg-dark text-white font-monospace">${u.codigo_acesso || '-'}</span>
          <div class="mt-1">${badgeSenha}</div>
        </td>
        <td><strong>${u.nome || '-'}</strong></td>
        <td><code>${u.email || '-'}</code></td>
        <td><span class="badge bg-secondary">${u.role || '-'}</span></td>
        <td>${u.telefone || '-'}</td>
        <td><small class="text-muted">${dtAcesso}</small></td>
        <td><span class="badge ${u.ativo ? 'bg-success' : 'bg-danger'}">${u.ativo ? 'Activo' : 'Inactivo'}</span></td>
        <td class="text-end">
          <button class="btn btn-outline-warning btn-sm" onclick="modalRedefinirSenhaUsuario('${u.id}', '${(u.nome || '').replace(/'/g, "\\'")}', '${codEscapado}')">
            <i class="bi bi-key me-1"></i> Gerir Senha
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function renderizarTabelaCofre(lista) {
  renderizarTabelaCofreUsuarios(lista);
}

function filtrarUsuariosCofre() {
  const termo = (document.getElementById('filtroUsuarioCofre')?.value || '').toLowerCase().trim();
  const role = document.getElementById('filtroRoleCofre')?.value || '';

  const filtrados = (cacheUsuariosCofre || []).filter(u => {
    const bateTexto = !termo ||
      (u.nome || '').toLowerCase().includes(termo) ||
      (u.email || '').toLowerCase().includes(termo) ||
      (u.codigo_acesso || '').toLowerCase().includes(termo);
    const bateRole = !role || u.role === role;
    return bateTexto && bateRole;
  });

  renderizarTabelaCofreUsuarios(filtrados);
}

// Exportação global explícita para evitar erros de escopo
window.carregarCofreUsuarios = carregarCofreUsuarios;
window.renderizarTabelaCofreUsuarios = renderizarTabelaCofreUsuarios;
window.renderizarTabelaCofre = renderizarTabelaCofre;
window.filtrarUsuariosCofre = filtrarUsuariosCofre;
