/**
 * SIGE - PAINEL-ESCOLA | Cofre de Credenciais da Escola
 * Ficheiro de código independente do menu: usuarios-senhas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== COFRE DE CREDENCIAIS ====================
async function carregarCofreUsuarios() {
  const container = document.getElementById('tabelaCofreUsuariosCorpo');
  if (!container) return;
  container.innerHTML = '<tr><td colspan="8" class="text-center py-4"><div class="spinner-border text-primary spinner-border-sm me-2"></div>A carregar utilizadores...</td></tr>';
  try {
    const res = await apiFetch('/api/v1/escola-admin/usuarios-credenciais');
    if (res && res.success && res.data) {
      renderizarTabelaCofreUsuarios(res.data);
    } else {
      container.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-danger">Falha ao carregar credenciais.</td></tr>';
    }
  } catch (err) {
    container.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-danger">Erro: ' + (err.message || 'Falha de rede') + '</td></tr>';
  }
}

