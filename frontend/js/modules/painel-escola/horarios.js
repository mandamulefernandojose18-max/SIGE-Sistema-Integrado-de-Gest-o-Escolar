async function initHorariosModulo() {
  const selTurma = document.getElementById('horarioSelectTurma');
  if (selTurma && selTurma.options.length <= 1) {
    const turmas = state.turmasList || state.todasTurmas || [];
    let opts = '<option value="">-- Selecione a Turma --</option>';
    turmas.forEach(t => {
      opts += `<option value="${t.id}">${escapeHtml(t.grau_ano || '')} - ${escapeHtml(t.nome)}</option>`;
    });
    selTurma.innerHTML = opts;
  }
}

async function carregarGradeHorarios() {
  const turmaId = document.getElementById('horarioSelectTurma')?.value;
  const tbody = document.getElementById('tabelaGradeHorario');
  if (!turmaId || !tbody) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="py-4 text-muted">Selecione uma turma para visualizar a grade semanal.</td></tr>';
    return;
  }
  tbody.innerHTML = '<tr><td colspan="6" class="py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar horários...</td></tr>';
  try {
    const res = await apiFetch(`/api/v1/turmas/horarios/?turma_id=${turmaId}`);
    const lista = res?.data || res?.results || res || [];
    const tempos = [
      { t: 1, label: '1º Tempo (07:15 - 08:00)' },
      { t: 2, label: '2º Tempo (08:05 - 08:50)' },
      { t: 3, label: '3º Tempo (09:05 - 09:50)' },
      { t: 4, label: '4º Tempo (09:55 - 10:40)' },
      { t: 5, label: '5º Tempo (10:50 - 11:35)' },
      { t: 6, label: '6º Tempo (11:40 - 12:25)' },
    ];
    let html = '';
    tempos.forEach(tempo => {
      html += `<tr><td class="fw-semibold bg-light small text-start ps-3">${tempo.label}</td>`;
      for (let dia = 1; dia <= 5; dia++) {
        const item = Array.isArray(lista) ? lista.find(h => h.dia_semana === dia && h.tempo === tempo.t) : null;
        if (item) {
          html += `<td class="p-2 bg-primary bg-opacity-10 border">
            <strong class="text-primary d-block">${escapeHtml(item.disciplina_nome)}</strong>
            <small class="text-muted d-block">${escapeHtml(item.professor_nome || 'Docente')}</small>
          </td>`;
        } else {
          html += `<td class="text-muted small">-</td>`;
        }
      }
      html += '</tr>';
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="py-4 text-danger">Erro ao carregar horário lectivo.</td></tr>';
  }
}

initHorariosModulo();
