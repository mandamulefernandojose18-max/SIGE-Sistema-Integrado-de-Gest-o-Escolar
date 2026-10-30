async function carregarListaOcorrencias() {
  const tbody = document.getElementById('tabelaListaOcorrencias');
  if (!tbody) return;
  try {
    const res = await apiFetch('/api/v1/notas/ocorrencias/');
    const lista = res?.data || res?.results || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Nenhuma ocorrência disciplinar registada.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const isDap = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'].includes(role);
    let html = '';
    lista.forEach(oc => {
      const badgeGrav = {
        'LEVE': '<span class="badge bg-info text-dark">Leve</span>',
        'GRAVE': '<span class="badge bg-warning text-dark">Grave</span>',
        'MUITO_GRAVE': '<span class="badge bg-danger">Muito Grave</span>',
      }[oc.gravidade] || oc.gravidade;
      const badgeSt = oc.status_validacao === 'HOMOLOGADA_DAP'
        ? '<span class="badge bg-success">Homologada pelo DAP</span>'
        : '<span class="badge bg-secondary">Aguardando Parecer</span>';
      let btnHomologar = '';
      if (isDap && oc.status_validacao !== 'HOMOLOGADA_DAP') {
        btnHomologar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="homologarOcorrencia('${oc.id}')"><i class="bi bi-check2"></i> Homologar</button>`;
      }
      html += `<tr>
        <td class="ps-3 small text-muted">${oc.data}</td>
        <td><strong>${escapeHtml(oc.aluno_nome)}</strong><br><small class="text-muted">${escapeHtml(oc.aluno_matricula)}</small></td>
        <td>${badgeGrav}</td>
        <td class="small" style="max-width: 250px;">${escapeHtml(oc.descricao)}</td>
        <td class="small">${escapeHtml(oc.medida_tomada || '-')}</td>
        <td>${badgeSt}</td>
        <td class="text-end pe-3">${btnHomologar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-danger">Erro ao carregar ocorrências.</td></tr>';
  }
}

async function homologarOcorrencia(id) {
  try {
    const res = await apiFetch(`/api/v1/notas/ocorrencias/${id}/homologar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Ocorrência homologada pelo DAP com sucesso!', 'success');
      carregarListaOcorrencias();
    }
  } catch (e) {
    mostrarToast('Erro ao homologar ocorrência: ' + e.message, 'danger');
  }
}

carregarListaOcorrencias();
