/**
 * SIGE - PAINEL-SUPERADMIN | Auditoria de Acessos SaaS
 * Ficheiro de código independente do menu: acessos.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
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

