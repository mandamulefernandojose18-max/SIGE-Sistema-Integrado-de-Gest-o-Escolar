// Presenças & Assiduidade — filtros em cascata (Ano Lectivo → Classe → Secção/Área → Turma → Disciplina → Data).
// PROFESSOR: lança presenças/faltas nas suas alocações. Restantes perfis: consulta (só leitura).
const presState = { itens: [], ano: '', alunos: [], registos: {} };

const PRES_ESTADOS = [
  { v: 'PRESENTE', rotulo: 'Presente', cls: 'success' },
  { v: 'FALTA_JUSTIFICADA', rotulo: 'F. Justif.', cls: 'warning' },
  { v: 'FALTA_INJUSTIFICADA', rotulo: 'F. Injustif.', cls: 'danger' },
  { v: 'ATRASO', rotulo: 'Atraso', cls: 'secondary' }
];

function presEhProfessor() { return state.user?.role === 'PROFESSOR'; }
function presHoje() { return new Date().toISOString().split('T')[0]; }
function presLista(res) { return res?.data || res?.results || (Array.isArray(res) ? res : []); }
function presOpcoes(sel, valores, vazio) {
  if (!sel) return;
  sel.innerHTML = valores.length
    ? valores.map(v => `<option value="${escapeHtml(v.valor)}">${escapeHtml(v.texto)}</option>`).join('')
    : `<option value="">${vazio}</option>`;
  sel.disabled = valores.length === 0;
}

// Chamado por executarGatilhosCarregamentoView('presencas', ano) ao clicar em "Buscar"
window.carregarPresencasAno = async function (ano) {
  presState.ano = ano;
  const prof = presEhProfessor();
  const wrapDisc = document.getElementById('presDiscWrap');
  if (wrapDisc) wrapDisc.style.display = prof ? '' : 'none';
  const sub = document.getElementById('presencasSubtitulo');
  if (sub) sub.textContent = prof
    ? 'Lance as presenças e faltas (justificadas/injustificadas) dos alunos das suas turmas.'
    : 'Consulta das presenças e faltas registadas pelos professores, por aula e turma.';
  const data = document.getElementById('presData');
  if (data) { data.max = presHoje(); if (!data.value) data.value = presHoje(); }

  try {
    const q = `?ano_letivo=${encodeURIComponent(ano)}`;
    if (prof) {
      const res = await apiFetch(`/api/v1/professores/minhas-turmas${q}`);
      presState.itens = presLista(res).map(a => ({
        turmaId: String(a.turma?.id || a.turma), turmaNome: a.turma?.nome || a.turma_nome || '',
        classe: a.turma?.grau_ano || a.turma_grau || '', area: normalizarArea(a.turma?.area || a.turma_area),
        discId: String(a.disciplina?.id || a.disciplina), discNome: a.disciplina?.nome || a.disciplina_nome || 'Disciplina'
      }));
    } else {
      const res = await apiFetch(`/api/v1/escola-admin/turmas${q}`);
      presState.itens = presLista(res).map(t => ({
        turmaId: String(t.id), turmaNome: t.nome || '', classe: t.grau_ano || '',
        area: normalizarArea(t.area), discId: '', discNome: ''
      }));
    }
  } catch (e) {
    presState.itens = [];
  }
  presPreencherClasses();
};

function presPreencherClasses() {
  const classes = [...new Set(presState.itens.map(i => i.classe))]
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  presOpcoes(document.getElementById('presClasse'), classes.map(c => ({ valor: c, texto: c })),
    `Sem turmas no ano lectivo ${presState.ano}`);
  presAoMudarClasse();
}

window.presAoMudarClasse = function () {
  const classe = document.getElementById('presClasse')?.value;
  const areas = [...new Set(presState.itens.filter(i => i.classe === classe).map(i => i.area))].sort();
  presOpcoes(document.getElementById('presArea'), areas.map(a => ({ valor: a, texto: a })), '—');
  presAoMudarArea();
};

window.presAoMudarArea = function () {
  const classe = document.getElementById('presClasse')?.value;
  const area = document.getElementById('presArea')?.value;
  const turmas = new Map();
  presState.itens.filter(i => i.classe === classe && i.area === area).forEach(i => turmas.set(i.turmaId, i.turmaNome));
  const ord = [...turmas.entries()].sort((a, b) => a[1].localeCompare(b[1], undefined, { numeric: true }));
  presOpcoes(document.getElementById('presTurma'), ord.map(([id, nome]) => ({ valor: id, texto: nome })), '—');
  presAoMudarTurma();
};

window.presAoMudarTurma = function () {
  const turmaId = document.getElementById('presTurma')?.value;
  if (presEhProfessor()) {
    const discs = presState.itens.filter(i => i.turmaId === turmaId);
    presOpcoes(document.getElementById('presDisciplina'), discs.map(d => ({ valor: d.discId, texto: d.discNome })), '—');
  }
  presCarregarAlunos();
};

function presLinhaVazia(msg, cls = 'text-muted') {
  return `<tr><td colspan="5" class="text-center py-4 ${cls}">${msg}</td></tr>`;
}

window.presCarregarAlunos = async function () {
  const tbody = document.getElementById('tabelaListaPresencas');
  const acoes = document.getElementById('presAcoes');
  const resumo = document.getElementById('presResumo');
  const turmaId = document.getElementById('presTurma')?.value;
  const discId = document.getElementById('presDisciplina')?.value;
  const data = document.getElementById('presData')?.value;
  const prof = presEhProfessor();
  if (!tbody) return;
  const mostrarAcoes = (v) => { if (acoes) acoes.style.setProperty('display', v ? 'flex' : 'none', 'important'); };
  mostrarAcoes(false);
  if (resumo) resumo.innerHTML = '&nbsp;';

  if (!turmaId || (prof && !discId)) {
    tbody.innerHTML = presLinhaVazia(presState.itens.length
      ? 'Escolha a classe, a secção, a turma e a disciplina para ver a lista de alunos.'
      : `Nenhuma turma atribuída encontrada no ano lectivo ${escapeHtml(presState.ano)}.`);
    return;
  }
  if (!data) { tbody.innerHTML = presLinhaVazia('Escolha a data da aula.'); return; }
  tbody.innerHTML = presLinhaVazia('<i class="bi bi-arrow-repeat spin me-2"></i>A carregar lista de alunos...');

  try {
    let urlPres = `/api/v1/alunos/presencas/?turma_id=${turmaId}&data=${data}&ano_letivo=${encodeURIComponent(presState.ano)}`;
    if (prof) urlPres += `&disciplina_id=${discId}`;
    const [resAlunos, resPres] = await Promise.all([
      apiFetch(`/api/v1/alunos/?turma_id=${turmaId}&status=ATIVO`),
      apiFetch(urlPres)
    ]);
    presState.alunos = presLista(resAlunos);
    presState.registos = {};
    presLista(resPres).forEach(p => { presState.registos[p.aluno] = p; });

    if (!presState.alunos.length) {
      tbody.innerHTML = presLinhaVazia('Nenhum aluno activo nesta turma.');
      return;
    }
    tbody.innerHTML = presState.alunos.map((al, i) => prof ? presLinhaEditavel(al, i) : presLinhaLeitura(al, i)).join('');
    mostrarAcoes(prof);
    presAtualizarResumo();
    if (prof) tbody.querySelectorAll('input[type="radio"]').forEach(r => r.addEventListener('change', presAtualizarResumo));
  } catch (e) {
    tbody.innerHTML = presLinhaVazia('Erro ao carregar a lista de assiduidade.', 'text-danger');
  }
};

function presCelulasBase(al, i) {
  return `<td class="ps-3 text-muted">${i + 1}</td>
    <td class="font-monospace small">${escapeHtml(al.matricula)}</td>
    <td class="fw-semibold">${escapeHtml((al.nome || '') + ' ' + (al.apelido || ''))}</td>`;
}

function presLinhaEditavel(al, i) {
  const reg = presState.registos[al.id];
  const st = reg?.status || 'PRESENTE';
  const radios = PRES_ESTADOS.map(e => `
    <input type="radio" class="btn-check" name="pres_${al.id}" id="p_${e.v}_${al.id}" value="${e.v}" ${st === e.v ? 'checked' : ''}>
    <label class="btn btn-outline-${e.cls}" for="p_${e.v}_${al.id}">${e.rotulo}</label>`).join('');
  return `<tr>${presCelulasBase(al, i)}
    <td class="text-center"><div class="btn-group btn-group-sm flex-wrap" role="group">${radios}</div></td>
    <td class="pe-3"><input type="text" class="form-control form-control-sm" id="obs_${al.id}" maxlength="255" value="${escapeHtml(reg?.observacao || '')}" placeholder="Nota..."></td>
  </tr>`;
}

function presLinhaLeitura(al, i) {
  const reg = presState.registos[al.id];
  const e = PRES_ESTADOS.find(x => x.v === reg?.status);
  const badge = e
    ? `<span class="badge bg-${e.cls}">${e.rotulo}</span>${reg.disciplina_nome ? ` <small class="text-muted">${escapeHtml(reg.disciplina_nome)}</small>` : ''}`
    : '<span class="badge bg-light text-muted border">Sem registo</span>';
  return `<tr>${presCelulasBase(al, i)}<td class="text-center">${badge}</td>
    <td class="pe-3 small text-muted">${escapeHtml(reg?.observacao || '')}</td></tr>`;
}

function presAtualizarResumo() {
  const resumo = document.getElementById('presResumo');
  if (!resumo) return;
  const cont = { PRESENTE: 0, FALTA_JUSTIFICADA: 0, FALTA_INJUSTIFICADA: 0, ATRASO: 0 };
  if (presEhProfessor()) {
    document.querySelectorAll('#tabelaListaPresencas input[type="radio"]:checked').forEach(r => { cont[r.value]++; });
  } else {
    Object.values(presState.registos).forEach(r => { if (r.status in cont) cont[r.status]++; });
  }
  resumo.innerHTML = `${presState.alunos.length} alunos · <span class="text-success">${cont.PRESENTE} presentes</span> · ` +
    `<span class="text-warning">${cont.FALTA_JUSTIFICADA} F. justif.</span> · ` +
    `<span class="text-danger">${cont.FALTA_INJUSTIFICADA} F. injustif.</span> · ${cont.ATRASO} atrasos`;
}

window.presMarcarTodosPresentes = function () {
  document.querySelectorAll('#tabelaListaPresencas input[value="PRESENTE"]').forEach(r => { r.checked = true; });
  presAtualizarResumo();
};

window.presSalvarLote = async function () {
  const turma = document.getElementById('presTurma')?.value;
  const disciplina = document.getElementById('presDisciplina')?.value;
  const data = document.getElementById('presData')?.value;
  if (!turma || !disciplina || !data) {
    mostrarToast('Selecione a turma, a disciplina e a data.', 'warning');
    return;
  }
  const registos = [...document.querySelectorAll('#tabelaListaPresencas input[type="radio"]:checked')].map(r => {
    const aluno = r.name.replace('pres_', '');
    return { aluno, status: r.value, observacao: document.getElementById(`obs_${aluno}`)?.value || '' };
  });
  if (!registos.length) { mostrarToast('Nenhum aluno na lista para guardar.', 'warning'); return; }

  const btn = document.getElementById('presBtnSalvar');
  if (btn) btn.disabled = true;
  try {
    const res = await apiFetch('/api/v1/alunos/presencas/lote/', {
      method: 'POST', body: JSON.stringify({ turma, disciplina, data, registos })
    });
    if (res?.success) {
      mostrarToast(`Assiduidade lançada com sucesso (${res.guardados} alunos).`, 'success');
      presCarregarAlunos();
    } else {
      mostrarToast(res?.message || res?.detail || 'Não foi possível lançar a assiduidade.', 'danger');
    }
  } catch (e) {
    mostrarToast(e?.message || 'Erro ao lançar a assiduidade.', 'danger');
  } finally {
    if (btn) btn.disabled = false;
  }
};
