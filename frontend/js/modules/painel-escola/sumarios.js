async function initSumariosModulo() {
  const selTurma = document.getElementById('sumarioSelectTurma');
  if (selTurma && selTurma.options.length <= 1) {
    const turmas = state.turmasList || state.todasTurmas || [];
    let opts = '<option value="">-- Todas as Turmas --</option>';
    turmas.forEach(t => {
      opts += `<option value="${t.id}">${escapeHtml(t.grau_ano || '')} - ${escapeHtml(t.nome)}</option>`;
    });
    selTurma.innerHTML = opts;
  }
  carregarListaSumarios();
}

async function carregarListaSumarios() {
  const tbody = document.getElementById('tabelaListaSumarios');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar sumários...</td></tr>';
  const turmaId = document.getElementById('sumarioSelectTurma')?.value || '';
  let url = '/api/v1/notas/planos-sumarios/?';
  if (turmaId) url += `turma_id=${turmaId}&`;
  try {
    const res = await apiFetch(url);
    const lista = res?.data || res?.results || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhum sumário ou plano de aula registado.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const isDap = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'].includes(role);
    let html = '';
    lista.forEach(s => {
      const badgeVal = s.status_validacao === 'VALIDADO_DAP'
        ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Validado pelo DAP</span>'
        : '<span class="badge bg-warning text-dark"><i class="bi bi-clock me-1"></i>Pendente de Validação</span>';
      let btnValidar = '';
      if (isDap && s.status_validacao !== 'VALIDADO_DAP') {
        btnValidar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="validarSumarioDap('${s.id}')"><i class="bi bi-check2"></i> Validar</button>`;
      }
      html += `<tr>
        <td class="ps-3"><strong>Aula ${s.numero_aula}</strong><br><small class="text-muted">${s.data}</small></td>
        <td><strong>${escapeHtml(s.turma_nome || '')}</strong><br><span class="badge bg-light text-dark border">${escapeHtml(s.disciplina_nome || '')}</span></td>
        <td><strong>${escapeHtml(s.tema)}</strong><br><small class="text-muted">${escapeHtml(s.unidade_tematica || '')}</small></td>
        <td class="small text-truncate" style="max-width: 250px;">${escapeHtml(s.sumario)}</td>
        <td>${badgeVal}</td>
        <td class="text-end pe-3">${btnValidar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Erro ao carregar sumários.</td></tr>';
  }
}

async function validarSumarioDap(id) {
  try {
    const res = await apiFetch(`/api/v1/notas/planos-sumarios/${id}/validar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Sumário validado pedagogicamente com sucesso!', 'success');
      carregarListaSumarios();
    }
  } catch (e) {
    mostrarToast('Erro ao validar sumário: ' + e.message, 'danger');
  }
}

initSumariosModulo();
