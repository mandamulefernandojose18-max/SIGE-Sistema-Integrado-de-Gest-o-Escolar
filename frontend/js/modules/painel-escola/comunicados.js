async function carregarListaComunicados() {
  const tbody = document.getElementById('tabelaListaComunicados');
  if (!tbody) return;
  try {
    const res = await apiFetch('/api/v1/documentos/comunicados/');
    const lista = res?.data || res?.results || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhum comunicado escolar publicado.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const isDirector = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'].includes(role);
    let html = '';
    lista.forEach(com => {
      const badgePrio = com.prioridade === 'URGENTE'
        ? '<span class="badge bg-danger">Urgente</span>'
        : (com.prioridade === 'IMPORTANTE' ? '<span class="badge bg-warning text-dark">Importante</span>' : '<span class="badge bg-secondary">Normal</span>');
      let btnAprovar = '';
      if (isDirector && !com.aprovado_pelo_director) {
        btnAprovar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="aprovarComunicado('${com.id}')"><i class="bi bi-check2"></i> Publicar</button>`;
      }
      html += `<tr>
        <td class="ps-3 small text-muted">${new Date(com.data_publicacao).toLocaleDateString('pt-PT')}</td>
        <td><strong>${escapeHtml(com.titulo)}</strong><br><small class="text-muted">${escapeHtml(com.conteudo.substring(0, 80))}...</small></td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(com.publico_alvo_display || com.publico_alvo)}</span></td>
        <td>${badgePrio}</td>
        <td><span class="badge bg-success">Activo</span></td>
        <td class="text-end pe-3">${btnAprovar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Erro ao carregar comunicados.</td></tr>';
  }
}

async function aprovarComunicado(id) {
  try {
    const res = await apiFetch(`/api/v1/documentos/comunicados/${id}/aprovar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Comunicado homologado e publicado com sucesso!', 'success');
      carregarListaComunicados();
    }
  } catch (e) {
    mostrarToast('Erro ao publicar comunicado: ' + e.message, 'danger');
  }
}

carregarListaComunicados();
