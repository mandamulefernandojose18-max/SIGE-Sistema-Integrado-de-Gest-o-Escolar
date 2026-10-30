async function initPresencasModulo() {
  const dtInput = document.getElementById('presencaData');
  if (dtInput && !dtInput.value) {
    dtInput.value = new Date().toISOString().split('T')[0];
  }
  const selTurma = document.getElementById('presencaSelectTurma');
  if (selTurma && selTurma.options.length <= 1) {
    const turmas = state.turmasList || state.todasTurmas || [];
    let opts = '<option value="">-- Selecione a Turma --</option>';
    turmas.forEach(t => {
      opts += `<option value="${t.id}">${escapeHtml(t.grau_ano || '')} - ${escapeHtml(t.nome)}</option>`;
    });
    selTurma.innerHTML = opts;
  }
}

async function carregarAlunosParaPresenca() {
  const turmaId = document.getElementById('presencaSelectTurma')?.value;
  const tbody = document.getElementById('tabelaListaPresencas');
  if (!turmaId || !tbody) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">Selecione uma turma para registar presenças.</td></tr>';
    return;
  }
  tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar lista de alunos...</td></tr>';
  const data = document.getElementById('presencaData')?.value || new Date().toISOString().split('T')[0];
  try {
    const [resAlunos, resPres] = await Promise.all([
      apiFetch(`/api/v1/alunos/?turma_id=${turmaId}&status=ATIVO`),
      apiFetch(`/api/v1/alunos/presencas/?turma_id=${turmaId}&data=${data}`)
    ]);
    const alunos = resAlunos?.data || resAlunos?.results || resAlunos || [];
    const presencas = resPres?.data || resPres?.results || resPres || [];
    const mapaPres = {};
    if (Array.isArray(presencas)) {
      presencas.forEach(p => { mapaPres[p.aluno] = p; });
    }
    if (!Array.isArray(alunos) || alunos.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">Nenhum aluno ativo nesta turma.</td></tr>';
      return;
    }
    let html = '';
    alunos.forEach((al, idx) => {
      const pres = mapaPres[al.id];
      const st = pres?.status || 'PRESENTE';
      const obs = pres?.observacao || '';
      html += `<tr>
        <td class="ps-3 text-muted">${idx + 1}</td>
        <td class="font-monospace small">${escapeHtml(al.matricula)}</td>
        <td class="fw-semibold">${escapeHtml(al.nome + ' ' + (al.apelido || ''))}</td>
        <td class="text-center">
          <div class="btn-group btn-group-sm" role="group">
            <input type="radio" class="btn-check" name="pres_${al.id}" id="p_p_${al.id}" value="PRESENTE" ${st === 'PRESENTE' ? 'checked' : ''}>
            <label class="btn btn-outline-success" for="p_p_${al.id}">Presente</label>
            <input type="radio" class="btn-check" name="pres_${al.id}" id="p_fj_${al.id}" value="FALTA_JUSTIFICADA" ${st === 'FALTA_JUSTIFICADA' ? 'checked' : ''}>
            <label class="btn btn-outline-warning" for="p_fj_${al.id}">F. Justif.</label>
            <input type="radio" class="btn-check" name="pres_${al.id}" id="p_fi_${al.id}" value="FALTA_INJUSTIFICADA" ${st === 'FALTA_INJUSTIFICADA' ? 'checked' : ''}>
            <label class="btn btn-outline-danger" for="p_fi_${al.id}">F. Injustif.</label>
          </div>
        </td>
        <td class="pe-3">
          <input type="text" class="form-control form-control-sm" id="obs_${al.id}" value="${escapeHtml(obs)}" placeholder="Nota...">
        </td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-danger">Erro ao carregar lista de assiduidade.</td></tr>';
  }
}

async function salvarPresencasLote() {
  const turmaId = document.getElementById('presencaSelectTurma')?.value;
  const data = document.getElementById('presencaData')?.value;
  if (!turmaId || !data) {
    mostrarToast('Selecione a turma e a data.', 'warning');
    return;
  }
  const radios = document.querySelectorAll('#tabelaListaPresencas input[type="radio"]:checked');
  if (!radios.length) {
    mostrarToast('Nenhum aluno na lista para salvar.', 'warning');
    return;
  }
  let salvos = 0;
  for (const r of radios) {
    const alunoId = r.name.replace('pres_', '');
    const status = r.value;
    const obs = document.getElementById(`obs_${alunoId}`)?.value || '';
    try {
      await apiFetch('/api/v1/alunos/presencas/', {
        method: 'POST',
        body: JSON.stringify({ aluno: alunoId, turma: turmaId, data, status, observacao: obs })
      });
      salvos++;
    } catch (_) {}
  }
  mostrarToast(`Assiduidade registada com sucesso (${salvos} registos)!`, 'success');
  carregarAlunosParaPresenca();
}

initPresencasModulo();
