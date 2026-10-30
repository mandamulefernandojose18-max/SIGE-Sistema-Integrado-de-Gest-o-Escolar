async function carregarListaDespesas() {
  const tbody = document.getElementById('tabelaListaDespesas');
  if (!tbody) return;
  try {
    const res = await apiFetch('/api/v1/pagamentos/transacoes/');
    const lista = res?.data || res?.results || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Nenhuma despesa ou receita registada.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const isDirector = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'].includes(role);
    let html = '';
    lista.forEach(item => {
      const badgeTipo = item.tipo === 'RECEITA'
        ? '<span class="badge bg-success">Receita</span>'
        : '<span class="badge bg-danger">Despesa</span>';
      const badgeSt = item.status_aprovacao === 'APROVADO_DIRECTOR'
        ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Aprovado pelo Director</span>'
        : '<span class="badge bg-warning text-dark"><i class="bi bi-hourglass-split me-1"></i>Pendente Aprovação</span>';
      let btnAprovar = '';
      if (isDirector && item.status_aprovacao !== 'APROVADO_DIRECTOR') {
        btnAprovar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="aprovarDespesa('${item.id}')"><i class="bi bi-check2"></i> Aprovar</button>`;
      }
      html += `<tr>
        <td class="ps-3 small text-muted">${item.data}</td>
        <td>${badgeTipo}</td>
        <td><strong>${escapeHtml(item.categoria)}</strong><br><small class="text-muted">${escapeHtml(item.descricao)}</small></td>
        <td class="fw-bold">${Number(item.valor).toLocaleString('pt-MZ', { minimumFractionDigits: 2 })} MT</td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(item.forma_pagamento)}</span></td>
        <td>${badgeSt}</td>
        <td class="text-end pe-3">${btnAprovar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-danger">Erro ao carregar despesas.</td></tr>';
  }
}

async function aprovarDespesa(id) {
  try {
    const res = await apiFetch(`/api/v1/pagamentos/transacoes/${id}/aprovar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Despesa aprovada oficialmente com sucesso!', 'success');
      carregarListaDespesas();
    }
  } catch (e) {
    mostrarToast('Erro ao aprovar despesa: ' + e.message, 'danger');
  }
}

carregarListaDespesas();
