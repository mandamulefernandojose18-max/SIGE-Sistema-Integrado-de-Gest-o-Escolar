async function carregarTrilhaAuditoria() {
  const tbody = document.getElementById('tabelaTrilhaAuditoria');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar auditoria...</td></tr>';
  const ent = document.getElementById('filtroEntidadeAuditoria')?.value || '';
  const acao = document.getElementById('filtroAcaoAuditoria')?.value || '';
  let url = '/api/v1/auth/auditoria/?';
  if (ent) url += `entidade=${ent}&`;
  if (acao) url += `acao=${acao}&`;
  try {
    const res = await apiFetch(url);
    const lista = res?.data || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhum registo de auditoria encontrado.</td></tr>';
      return;
    }
    let html = '';
    lista.forEach(item => {
      const dt = new Date(item.created_at).toLocaleString('pt-PT');
      const badgeAcao = {
        'CRIACAO': '<span class="badge bg-success">Criação</span>',
        'EDICAO': '<span class="badge bg-primary">Edição</span>',
        'VALIDACAO': '<span class="badge bg-info text-dark">Validação</span>',
        'APROVACAO': '<span class="badge bg-success">Aprovação</span>',
        'ELIMINACAO': '<span class="badge bg-danger">Eliminação</span>',
      }[item.acao] || `<span class="badge bg-secondary">${escapeHtml(item.acao)}</span>`;

      html += `<tr>
        <td class="ps-3 small text-muted">${escapeHtml(dt)}</td>
        <td><strong>${escapeHtml(item.usuario_nome || 'Sistema')}</strong></td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(item.usuario_role || '-')}</span></td>
        <td><span class="fw-semibold text-dark">${escapeHtml(item.entidade)}</span></td>
        <td>${badgeAcao}</td>
        <td class="pe-3 small">${escapeHtml(item.descricao)}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Erro ao carregar auditoria.</td></tr>';
  }
}

if (typeof carregarTrilhaAuditoria === 'function') {
  carregarTrilhaAuditoria();
}
