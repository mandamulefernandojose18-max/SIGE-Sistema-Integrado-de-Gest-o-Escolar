async function carregarListaTransferencias() {
  const tbody = document.getElementById('tabelaListaTransferencias');
  if (!tbody) return;
  try {
    const res = await apiFetch('/api/v1/alunos/transferencias/');
    const lista = res?.data || res?.results || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Nenhum processo de transferência ou anulação registado.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const isDirector = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'].includes(role);
    let html = '';
    lista.forEach(tr => {
      const badgeSt = tr.status === 'APROVADO'
        ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Aprovado pelo Director</span>'
        : '<span class="badge bg-warning text-dark"><i class="bi bi-hourglass-split me-1"></i>Pendente de Parecer</span>';
      let btnAprovar = '';
      if (isDirector && tr.status !== 'APROVADO') {
        btnAprovar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="aprovarTransferencia('${tr.id}')"><i class="bi bi-check2"></i> Homologar</button>`;
      }
      html += `<tr>
        <td class="ps-3 small text-muted">${tr.data_solicitacao}</td>
        <td><strong>${escapeHtml(tr.aluno_nome)}</strong><br><small class="text-muted">${escapeHtml(tr.aluno_matricula)}</small></td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(tr.tipo)}</span></td>
        <td>${escapeHtml(tr.escola_origem_destino || '-')}</td>
        <td class="small">${escapeHtml(tr.motivo)}</td>
        <td>${badgeSt}</td>
        <td class="text-end pe-3">${btnAprovar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-danger">Erro ao carregar processos.</td></tr>';
  }
}

async function aprovarTransferencia(id) {
  try {
    const res = await apiFetch(`/api/v1/alunos/transferencias/${id}/aprovar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Transferência homologada oficialmente pelo Director!', 'success');
      carregarListaTransferencias();
    }
  } catch (e) {
    mostrarToast('Erro ao homologar transferência: ' + e.message, 'danger');
  }
}

carregarListaTransferencias();
