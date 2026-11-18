// Presenças & Assiduidade — filtros em cascata (Ano Lectivo → Classe → Secção/Área → Turma → Disciplina → Data).
// PROFESSOR: lança presenças/faltas nas suas alocações. Restantes perfis: consulta (só leitura).
const presState = { itens: [], ano: '', alunos: [], registos: {}, todosRegistos: [] };

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
  if (wrapDisc) wrapDisc.style.display = '';
  const wrapAulas = document.getElementById('presAulasWrap');
  if (wrapAulas) wrapAulas.style.display = prof ? '' : 'none';
  const infoAulas = document.getElementById('presAulasInfoWrap');
  if (infoAulas) infoAulas.style.display = prof ? '' : 'none';
  document.getElementById('presAulas')?.addEventListener('change', presAtualizarInfoAulas);
  const sub = document.getElementById('presencasSubtitulo');
  if (sub) sub.textContent = prof
    ? 'Lance as presenças e faltas (justificadas/injustificadas) dos alunos das suas turmas.'
    : 'Consulta das presenças e faltas registadas pelos professores, por aula e turma.';
  const data = document.getElementById('presData');
  if (data) { data.max = presHoje(); }

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

window.presAoMudarTurma = async function () {
  const turmaId = document.getElementById('presTurma')?.value;
  if (presEhProfessor()) {
    const discs = presState.itens.filter(i => i.turmaId === turmaId);
    presOpcoes(document.getElementById('presDisciplina'), discs.map(d => ({ valor: d.discId, texto: d.discNome })), '—');
  } else {
    await presCarregarDisciplinasConsulta();
  }
  presCarregarAlunos();
};

// Consulta: disciplinas reais da classe/secção escolhida (cadastradas na escola) + opção "Todas as disciplinas".
async function presCarregarDisciplinasConsulta() {
  const sel = document.getElementById('presDisciplina');
  if (!sel) return;
  const classe = document.getElementById('presClasse')?.value || '';
  const area = document.getElementById('presArea')?.value || '';
  const anterior = sel.value;
  let discs = [];
  if (classe) {
    try {
      const res = await apiFetch(`/api/v1/disciplinas/?classe=${encodeURIComponent(classe)}&area=${encodeURIComponent(area)}`);
      discs = presLista(res);
    } catch (e) { discs = []; }
  }
  sel.innerHTML = '<option value="">Todas as disciplinas</option>' +
    discs.map(d => `<option value="${escapeHtml(String(d.id))}">${escapeHtml(d.nome || 'Disciplina')}</option>`).join('');
  sel.value = discs.some(d => String(d.id) === anterior) ? anterior : '';
  sel.disabled = false;
}

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
    presState.resumoTurma = [];
    presState.resumoDisciplina = '';
    presRenderResumoTurma();
    tbody.innerHTML = presLinhaVazia(presState.itens.length
      ? 'Escolha a classe, a secção, a turma e a disciplina para ver a lista de alunos.'
      : `Nenhuma turma atribuída encontrada no ano lectivo ${escapeHtml(presState.ano)}.`);
    return;
  }
  if (!data) { tbody.innerHTML = presLinhaVazia('Escolha a data da aula.'); return; }
  presMostrarTrimestre(data);
  tbody.innerHTML = presLinhaVazia('<i class="bi bi-arrow-repeat spin me-2"></i>A carregar lista de alunos...');

  try {
    let urlPres = `/api/v1/alunos/presencas/?turma_id=${turmaId}&data=${data}&ano_letivo=${encodeURIComponent(presState.ano)}`;
    if (prof) urlPres += `&disciplina_id=${discId}`;
    const [resAlunos, resPres] = await Promise.all([
      apiFetch(`/api/v1/alunos/?turma_id=${turmaId}&status=ATIVO`),
      apiFetch(urlPres)
    ]);
    presState.alunos = presLista(resAlunos);
    presState.todosRegistos = presLista(resPres);
    // Tipo de aula: pré-selecciona o já gravado para esta aula; sem registo o professor tem de indicar
    const selAulas = document.getElementById('presAulas');
    if (selAulas && prof) {
      const gravado = presState.todosRegistos.find(p => p.aulas);
      selAulas.value = gravado ? String(gravado.aulas) : '';
    }
    await presCarregarRisco(turmaId);
    presRenderLista();
  } catch (e) {
    tbody.innerHTML = presLinhaVazia('Erro ao carregar a lista de assiduidade.', 'text-danger');
  }
};

// Consulta: o filtro de disciplina só lista disciplinas com registos reais na data (nunca inventadas).
function presPopularDisciplinasConsulta() {
  const sel = document.getElementById('presDisciplina');
  if (!sel) return;
  const anterior = sel.value;
  const discs = new Map();
  presState.todosRegistos.forEach(p => { if (p.disciplina) discs.set(String(p.disciplina), p.disciplina_nome || 'Disciplina'); });
  sel.innerHTML = '<option value="">Todas as disciplinas</option>' +
    [...discs.entries()].map(([id, nome]) => `<option value="${escapeHtml(id)}">${escapeHtml(nome)}</option>`).join('');
  sel.value = discs.has(anterior) ? anterior : '';
  sel.disabled = discs.size === 0;
}

window.presAoMudarDisciplina = async function () {
  if (presEhProfessor()) { presCarregarAlunos(); return; }
  await presCarregarRisco(document.getElementById('presTurma')?.value);
  presRenderLista();
};

window.presRenderLista = function () {
  const tbody = document.getElementById('tabelaListaPresencas');
  const acoes = document.getElementById('presAcoes');
  const prof = presEhProfessor();
  if (!tbody) return;
  const discFiltro = !prof ? (document.getElementById('presDisciplina')?.value || '') : '';
  presState.registos = {};
  presState.todosRegistos
    .filter(p => !discFiltro || String(p.disciplina) === discFiltro)
    .forEach(p => {
      if (prof) presState.registos[p.aluno] = p;
      else (presState.registos[p.aluno] = presState.registos[p.aluno] || []).push(p);
    });

  if (!presState.alunos.length) {
    tbody.innerHTML = presLinhaVazia('Nenhum aluno activo nesta turma.');
    return;
  }
  const termo = (document.getElementById('presBusca')?.value || '').trim().toLowerCase();
  const visiveis = presState.alunos
    .map((al, i) => ({ al, i }))
    .filter(({ al }) => !termo || `${al.nome || ''} ${al.apelido || ''} ${al.matricula || ''}`.toLowerCase().includes(termo));
  tbody.innerHTML = visiveis.length
    ? visiveis.map(({ al, i }) => prof ? presLinhaEditavel(al, i) : presLinhaLeitura(al, i)).join('')
    : presLinhaVazia('Nenhum aluno corresponde à pesquisa.');
  if (acoes) acoes.style.setProperty('display', prof ? 'flex' : 'none', 'important');
  presAtualizarResumo();
  if (prof) tbody.querySelectorAll('input[type="radio"]').forEach(r => r.addEventListener('change', presAtualizarResumo));
};

// Pesquisa: no modo professor preserva as marcações já feitas antes de re-renderizar.
window.presAoPesquisar = function () {
  if (presEhProfessor()) presGuardarMarcacoesLocais();
  presRenderLista();
};

function presGuardarMarcacoesLocais() {
  document.querySelectorAll('#tabelaListaPresencas input[type="radio"]:checked').forEach(r => {
    const id = r.name.replace('pres_', '');
    presState.registos[id] = { ...(presState.registos[id] || {}), aluno: id, status: r.value };
    const obs = document.getElementById(`obs_${id}`);
    if (obs) presState.registos[id].observacao = obs.value;
    const idx = presState.todosRegistos.findIndex(p => String(p.aluno) === id);
    if (idx >= 0) presState.todosRegistos[idx] = presState.registos[id];
    else presState.todosRegistos.push(presState.registos[id]);
  });
}

// Exporta o resumo de assiduidade (todo o ano lectivo da turma escolhida; disciplina opcional) em PDF/XLSX.
window.presExportar = function (formato) {
  const turmaId = document.getElementById('presTurma')?.value;
  if (!turmaId) { mostrarToast('Escolha a classe, a secção e a turma para exportar.', 'warning'); return; }
  const discId = document.getElementById('presDisciplina')?.value;
  let q = `formato=${formato}&turma_id=${encodeURIComponent(turmaId)}&ano_letivo=${encodeURIComponent(presState.ano)}`;
  if (discId) q += `&disciplina_id=${encodeURIComponent(discId)}`;
  return downloadFicheiroBinario(`/api/v1/alunos/presencas/exportar/?${q}`, `assiduidade.${formato}`);
};

// Secretaria/direcção: justificar falta injustificada (com motivo, fica auditado).
const PRES_PERFIS_JUSTIFICAR = ['DIRECTOR_ESCOLA', 'ADMIN_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'SECRETARIA', 'SUPERADMIN'];
window.presJustificar = async function (id) {
  const motivo = (prompt('Motivo da justificação da falta (ex.: doença, luto):') || '').trim();
  if (!motivo) return;
  try {
    const res = await apiFetch(`/api/v1/alunos/presencas/${id}/justificar/`, {
      method: 'POST', body: JSON.stringify({ motivo })
    });
    if (res?.success) { mostrarToast('Falta justificada.', 'success'); presCarregarAlunos(); }
    else mostrarToast(res?.message || res?.detail || 'Não foi possível justificar.', 'danger');
  } catch (e) {
    mostrarToast(e?.message || 'Erro ao justificar a falta.', 'danger');
  }
};

// Alerta de risco: % de faltas do ano lectivo (todas as aulas da turma) >= limite definido pela direcção.
async function presCarregarRisco(turmaId) {
  presState.risco = {};
  presState.limite = null;
  presState.resumoTurma = [];
  const base = `/api/v1/alunos/presencas/resumo/?turma_id=${turmaId}&ano_letivo=${encodeURIComponent(presState.ano)}`;
  const discId = document.getElementById('presDisciplina')?.value;
  try {
    // Risco: sempre sobre todas as disciplinas da turma no ano lectivo.
    const res = await apiFetch(base);
    presState.limite = res?.limite_percent ?? null;
    (res?.resultados || []).forEach(r => { if (r.em_risco) presState.risco[r.aluno] = r; });
    // Painel de resumo: com a disciplina escolhida (professor: a sua), senão toda a turma.
    const resPainel = discId ? await apiFetch(`${base}&disciplina_id=${encodeURIComponent(discId)}`) : res;
    presState.resumoTurma = resPainel?.resultados || [];
    presState.resumoDisciplina = discId ? (document.getElementById('presDisciplina')?.selectedOptions?.[0]?.textContent || '') : '';
  } catch (e) { /* sem alerta/resumo se falhar */ }
  presRenderResumoTurma();
}

// Resumo de assiduidade da turma no ecrã (visualização, além de exportar). Altura fixa com scroll.
function presRenderResumoTurma() {
  const tbody = document.getElementById('presResumoTurmaCorpo');
  const titulo = document.getElementById('presResumoTurmaTitulo');
  if (!tbody) return;
  if (titulo) titulo.textContent = presState.resumoDisciplina ? `Resumo de assiduidade — ${presState.resumoDisciplina}` : 'Resumo de assiduidade da turma';
  const dados = presState.resumoTurma || [];
  if (!dados.length) {
    tbody.innerHTML = '<tr><td colspan="13" class="text-center text-muted py-3">Ainda não existem registos de assiduidade para esta turma neste ano lectivo.</td></tr>';
    return;
  }
  const pct = (v) => String(v).replace('.', ',') + '%';
  tbody.innerHTML = dados.map((r, i) => `<tr class="${r.em_risco ? 'table-danger' : ''}">
      <td class="ps-3 text-muted">${i + 1}</td>
      <td class="font-monospace small">${escapeHtml(r.matricula)}</td>
      <td class="fw-semibold">${escapeHtml(r.nome)}${r.em_risco ? ' <span class="badge bg-danger">Em risco</span>' : ''}</td>
      <td class="text-center">${r.total}</td><td class="text-center">${r.presentes}</td>
      <td class="text-center">${r.justificadas}</td>
      <td class="text-center ${r.injustificadas ? 'text-danger fw-semibold' : ''}">${r.injustificadas}</td>
      <td class="text-center">${r.atrasos}</td><td class="text-center">${pct(r.percent_faltas)}</td>
      <td class="text-center">${r.f1 ?? 0}</td><td class="text-center">${r.f2 ?? 0}</td><td class="text-center">${r.f3 ?? 0}</td>
      <td class="text-center fw-bold pe-3">${r.faltas_total ?? 0}</td></tr>`).join('');
}

// Trimestre da data da aula (calendário da escola) — mostra o selo ao lado da data.
async function presMostrarTrimestre(data) {
  const el = document.getElementById('presTrimestreBadge');
  if (!el) return;
  try {
    const res = await apiFetch(`/api/v1/alunos/presencas/trimestre/?data=${encodeURIComponent(data)}`);
    el.textContent = res?.trimestre ? `${res.trimestre}.º Trimestre` : 'Fora dos trimestres';
  } catch (e) { el.textContent = ''; }
}

// ===================== LISTA GERAL DE FALTAS (aluno × disciplina × trimestre) =====================
// Um aluno por linha; disciplinas na horizontal (1.º/2.º/3.º trimestre = faltas efectivas, já sem as justificadas);
// coluna final «Faltas justificadas» (ex.: Mat: 2). Filtros em cascata mantêm a altura constante para qualquer n.
const pgState = { alunos: [], discs: [], discsTodas: [], aluno: null, detalhe: null };

window.presAbrirGeral = function () {
  if (!presState.ano) return;
  if (!document.getElementById('pgClasse')?.options.length) presGeralPreencherClasses();
  presCarregarGeral();
};

function presGeralPreencherClasses() {
  const classes = [...new Set(presState.itens.map(i => i.classe))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  const sel = document.getElementById('pgClasse');
  if (sel) sel.innerHTML = '<option value="">Todas as classes</option>' + classes.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
  presGeralMudouClasse(false);
  const sd = document.getElementById('pgDisciplina');
  if (sd && presEhProfessor()) {
    const m = new Map();
    presState.itens.forEach(i => m.set(i.discId, i.discNome));
    sd.innerHTML = '<option value="">Todas as minhas disciplinas</option>' + [...m.entries()].map(([id, n]) => `<option value="${escapeHtml(id)}">${escapeHtml(n)}</option>`).join('');
  }
}

window.presGeralMudouClasse = function (recarregar = true) {
  const classe = document.getElementById('pgClasse')?.value;
  const areas = [...new Set(presState.itens.filter(i => !classe || i.classe === classe).map(i => i.area))].sort();
  const sel = document.getElementById('pgArea');
  if (sel) sel.innerHTML = '<option value="">Todas as secções</option>' + areas.map(a => `<option value="${escapeHtml(a)}">${escapeHtml(a)}</option>`).join('');
  presGeralMudouArea(recarregar);
};

window.presGeralMudouArea = function (recarregar = true) {
  const classe = document.getElementById('pgClasse')?.value;
  const area = document.getElementById('pgArea')?.value;
  const m = new Map();
  presState.itens.filter(i => (!classe || i.classe === classe) && (!area || i.area === area)).forEach(i => m.set(i.turmaId, `${i.classe} ${i.turmaNome}`.trim()));
  const ord = [...m.entries()].sort((a, b) => a[1].localeCompare(b[1], undefined, { numeric: true }));
  const sel = document.getElementById('pgTurma');
  if (sel) sel.innerHTML = '<option value="">Todas as turmas</option>' + ord.map(([id, n]) => `<option value="${escapeHtml(id)}">${escapeHtml(n)}</option>`).join('');
  if (recarregar !== false) presCarregarGeral();
};

window.presGeralMudouPeriodo = function () {
  const pers = document.getElementById('pgPeriodo')?.value === 'PERSONALIZADO';
  document.querySelectorAll('.pg-datas').forEach(el => { el.style.display = pers ? '' : 'none'; });
  presCarregarGeral();
};

function presParamsGeral() {
  const p = new URLSearchParams({ ano_letivo: presState.ano });
  const v = (id) => document.getElementById(id)?.value || '';
  if (v('pgClasse')) p.set('classe', v('pgClasse'));
  if (v('pgArea')) p.set('area', v('pgArea'));
  if (v('pgTurma')) p.set('turma_id', v('pgTurma'));
  if (v('pgDisciplina')) p.set('disciplina_id', v('pgDisciplina'));
  const per = v('pgPeriodo') || 'ANO';
  p.set('periodo', per);
  if (per === 'PERSONALIZADO') {
    if (v('pgDe')) p.set('data_inicio', v('pgDe'));
    if (v('pgAte')) p.set('data_fim', v('pgAte'));
  }
  return p;
}

window.presCarregarGeral = async function () {
  const corpo = document.getElementById('pgCorpo');
  if (!corpo || !presState.ano) return;
  corpo.innerHTML = '<tr><td class="text-muted py-4"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar...</td></tr>';
  try {
    const res = await apiFetch(`/api/v1/alunos/presencas/faltas-geral/?${presParamsGeral()}`);
    if (res?.success === false) throw new Error(res.message || res.detail || 'Erro');
    pgState.alunos = res?.alunos || [];
    pgState.discs = res?.disciplinas || [];
    // opções do filtro de disciplina (consulta): as que existem no resultado sem filtro de disciplina
    const sd = document.getElementById('pgDisciplina');
    if (sd && !presEhProfessor() && !sd.value) {
      sd.innerHTML = '<option value="">Todas as disciplinas</option>' + pgState.discs.map(d => `<option value="${escapeHtml(d.id)}">${escapeHtml(d.nome)}</option>`).join('');
    }
    presRenderGeral();
  } catch (e) {
    pgState.alunos = []; pgState.discs = [];
    document.getElementById('pgCabeca').innerHTML = '';
    corpo.innerHTML = `<tr><td class="text-danger py-4">${escapeHtml(e?.message || 'Erro ao carregar a lista geral de faltas.')}</td></tr>`;
  }
};

window.presRenderGeral = function () {
  const cab = document.getElementById('pgCabeca');
  const corpo = document.getElementById('pgCorpo');
  const resumo = document.getElementById('pgResumo');
  if (!cab || !corpo) return;
  const termo = (document.getElementById('pgBusca')?.value || '').trim().toLowerCase();
  const alunos = pgState.alunos.filter(a => !termo || `${a.nome} ${a.matricula}`.toLowerCase().includes(termo));
  if (!pgState.alunos.length) {
    cab.innerHTML = '';
    corpo.innerHTML = '<tr><td class="text-muted py-4">Ainda não existem registos de assiduidade para os filtros escolhidos.</td></tr>';
    if (resumo) resumo.innerHTML = '&nbsp;';
    return;
  }
  const D = pgState.discs;
  const stick = 'position: sticky; left: 0; background: #fff; z-index: 1;';
  const bl = 'border-left: 2px solid #1e3a8a !important;';
  cab.innerHTML = `<tr>
      <th rowspan="2" class="align-middle">#</th>
      <th rowspan="2" class="align-middle text-start" style="min-width: 190px; position: sticky; left: 0; z-index: 2; background: #f8f9fa;">Aluno</th>
      <th rowspan="2" class="align-middle">Turma</th>
      ${D.map(d => `<th colspan="3" class="text-nowrap" style="${bl}" title="${escapeHtml(d.nome)}">${escapeHtml(d.nome)}</th>`).join('')}
      <th rowspan="2" class="align-middle" style="${bl}">Total</th>
      <th rowspan="2" class="align-middle" style="min-width: 150px;">Faltas justificadas</th>
    </tr><tr>${D.map(() => `<th style="${bl}">1.º T</th><th>2.º T</th><th>3.º T</th>`).join('')}</tr>`;
  const cel = (n) => n ? `<span class="text-danger fw-semibold">${n}</span>` : '<span class="text-muted">0</span>';
  corpo.innerHTML = alunos.length ? alunos.map((a, i) => `<tr>
      <td class="text-muted">${i + 1}</td>
      <td class="text-start fw-semibold" style="${stick}"><a href="#" class="text-decoration-none" onclick="presAbrirFaltasAluno('${escapeHtml(a.aluno)}'); return false;" title="Ver datas e justificar">${escapeHtml(a.nome)}</a><div class="small text-muted font-monospace">${escapeHtml(a.matricula || '')}</div></td>
      <td class="text-nowrap">${escapeHtml((a.classe + ' ' + a.turma).trim())}</td>
      ${D.map(d => { const x = a.disc[d.id]; return x ? `<td style="${bl}">${cel(x.f1)}</td><td>${cel(x.f2)}</td><td>${cel(x.f3)}</td>` : `<td style="${bl}" class="text-muted">–</td><td class="text-muted">–</td><td class="text-muted">–</td>`; }).join('')}
      <td class="fw-bold" style="${bl}">${a.total}</td>
      <td class="small text-start">${a.justificadas_txt ? escapeHtml(a.justificadas_txt) : '<span class="text-muted">–</span>'}</td>
    </tr>`).join('') : `<tr><td colspan="${5 + 3 * D.length}" class="text-muted py-4">Nenhum aluno corresponde à pesquisa.</td></tr>`;
  if (resumo) {
    const tot = alunos.reduce((s, a) => s + a.total, 0);
    const j = alunos.reduce((s, a) => s + a.justificadas_total, 0);
    resumo.innerHTML = `${alunos.length} aluno(s) · ${D.length} disciplina(s) · <b class="text-danger">${tot}</b> falta(s) efectiva(s) · ${j} justificada(s)`;
  }
};

window.presExportarGeral = function (formato, modo) {
  const p = presParamsGeral();
  p.set('formato', formato);
  p.set('modo', modo);
  return downloadFicheiroBinario(`/api/v1/alunos/presencas/faltas-geral/?${p}`, `${modo === 'detalhado' ? 'faltas-detalhadas' : 'faltas-acumuladas'}.${formato}`);
};

// ---- Janela: faltas do aluno por data + justificação por quantidade ----
window.presAbrirFaltasAluno = async function (alunoId) {
  pgState.aluno = pgState.alunos.find(a => a.aluno === alunoId) || null;
  document.getElementById('pmNome').textContent = pgState.aluno ? `${pgState.aluno.nome} — faltas por data` : 'Faltas do aluno';
  const el = document.getElementById('presModalFaltas');
  if (!el) return;
  bootstrap.Modal.getOrCreateInstance(el).show();
  await presRecarregarModal();
};

async function presRecarregarModal() {
  const a = pgState.aluno;
  if (!a) return;
  const corpo = document.getElementById('pmFaltas');
  corpo.innerHTML = '<tr><td colspan="8" class="text-muted py-3">A carregar...</td></tr>';
  const p = new URLSearchParams({ ano_letivo: presState.ano, aluno_id: a.aluno });
  try {
    const res = await apiFetch(`/api/v1/alunos/presencas/faltas-detalhe/?${p}`);
    pgState.detalhe = res || { faltas: [], justificacoes: [] };
  } catch (e) { pgState.detalhe = { faltas: [], justificacoes: [] }; }
  const f = pgState.detalhe.faltas;
  const fmtData = (iso) => iso.split('-').reverse().join('/');
  corpo.innerHTML = f.length ? f.map(r => {
    const estado = r.efectivas === 0 ? '<span class="badge bg-success">Justificada</span>' : r.justificadas ? '<span class="badge bg-warning text-dark">Parcialmente justificada</span>' : '<span class="badge bg-danger">Injustificada</span>';
    const nota = [r.observacao, r.justificacao ? `Justif.: ${r.justificacao}` : ''].filter(Boolean).join(' · ');
    return `<tr><td class="text-nowrap">${fmtData(r.data)}</td><td>${escapeHtml(r.disciplina)}</td><td class="text-center">${r.trimestre ? r.trimestre + '.º' : '–'}</td>
      <td class="text-center">${r.aulas === 2 ? 'Dupla (2 aulas)' : 'Simples (1 aula)'}</td><td class="text-center">${r.aulas}</td>
      <td class="text-center">${r.justificadas}</td><td class="text-center fw-bold ${r.efectivas ? 'text-danger' : ''}">${r.efectivas}</td>
      <td>${estado}<div class="small text-muted">${escapeHtml(nota)}</div></td></tr>`;
  }).join('') : '<tr><td colspan="8" class="text-center text-muted py-3">Este aluno não tem faltas registadas.</td></tr>';
  const totB = f.reduce((s, r) => s + r.aulas, 0), totJ = f.reduce((s, r) => s + r.justificadas, 0);
  document.getElementById('pmResumo').innerHTML = `<span class="badge bg-secondary fs-6">Marcadas: ${totB}</span><span class="badge bg-success fs-6">Justificadas: ${totJ}</span><span class="badge bg-danger fs-6">Efectivas: ${totB - totJ}</span>`;
  const js = pgState.detalhe.justificacoes || [];
  const podeJ = PRES_PERFIS_JUSTIFICAR.includes(state.user?.role);
  document.getElementById('pmJustificacoes').innerHTML = js.length ? js.map(j => `<tr class="${j.anulada ? 'text-decoration-line-through text-muted' : ''}">
      <td>${fmtData(j.data)}</td><td>${escapeHtml(j.disciplina)}</td><td class="text-center">${j.trimestre}.º</td><td class="text-center">${j.quantidade}</td>
      <td>${escapeHtml(j.motivo)}</td><td>${escapeHtml(j.por || '')}</td>
      <td class="text-end">${podeJ && !j.anulada ? `<button class="btn btn-sm btn-outline-danger" onclick="presAnularJustificacao('${escapeHtml(j.id)}')">Anular</button>` : (j.anulada ? 'anulada' : '')}</td></tr>`).join('')
    : '<tr><td colspan="7" class="text-center text-muted py-3">Sem justificações registadas.</td></tr>';
  // formulário: só combinações disciplina × trimestre com faltas por justificar
  const alvo = {};
  f.forEach(r => {
    if (!r.trimestre) return;
    const k = `${r.disciplina_id}|${r.trimestre}`;
    alvo[k] = alvo[k] || { disc: r.disciplina, pend: 0 };
    alvo[k].pend += r.efectivas;
  });
  const opts = Object.entries(alvo).filter(([, v]) => v.pend > 0);
  pgState.alvos = Object.fromEntries(opts);
  const form = document.getElementById('pmFormJustificar');
  form.style.display = podeJ ? '' : 'none';
  const sel = document.getElementById('pmAlvo');
  sel.innerHTML = opts.length ? opts.map(([k, v]) => `<option value="${escapeHtml(k)}">${escapeHtml(v.disc)} — ${k.split('|')[1]}.º T (${v.pend} por justificar)</option>`).join('')
    : '<option value="">Sem faltas por justificar</option>';
  document.getElementById('pmBtn').disabled = !opts.length;
  presModalAlvo();
}

window.presModalAlvo = function () {
  const v = pgState.alvos?.[document.getElementById('pmAlvo')?.value];
  const q = document.getElementById('pmQtd');
  document.getElementById('pmMax').textContent = v ? `(máx. ${v.pend})` : '';
  if (q) { q.max = v ? v.pend : ''; q.value = v ? Math.min(1, v.pend) : ''; }
};

window.presModalJustificar = async function () {
  const [disciplina, trimestre] = (document.getElementById('pmAlvo')?.value || '').split('|');
  const quantidade = Number(document.getElementById('pmQtd')?.value || 0);
  const motivo = (document.getElementById('pmMotivo')?.value || '').trim();
  if (!disciplina || !quantidade || quantidade < 1) { mostrarToast('Indique o número de faltas a justificar.', 'warning'); return; }
  if (!motivo) { mostrarToast('Indique o motivo da justificação.', 'warning'); return; }
  try {
    const res = await apiFetch('/api/v1/alunos/presencas/justificar-faltas/', {
      method: 'POST', body: JSON.stringify({ aluno: pgState.aluno.aluno, disciplina, trimestre: Number(trimestre), quantidade, motivo })
    });
    if (res?.success) {
      mostrarToast(`${quantidade} falta(s) justificada(s). As faltas efectivas foram reduzidas.`, 'success');
      document.getElementById('pmMotivo').value = '';
      await presRecarregarModal();
      presCarregarGeral();
    } else mostrarToast(res?.message || res?.detail || 'Não foi possível justificar.', 'danger');
  } catch (e) { mostrarToast(e?.message || 'Erro ao justificar as faltas.', 'danger'); }
};

window.presAnularJustificacao = async function (id) {
  if (!confirm('Anular esta justificação? As faltas voltam a contar.')) return;
  try {
    const res = await apiFetch('/api/v1/alunos/presencas/anular-justificacao/', { method: 'POST', body: JSON.stringify({ id }) });
    if (res?.success) { mostrarToast('Justificação anulada.', 'success'); await presRecarregarModal(); presCarregarGeral(); }
    else mostrarToast(res?.message || res?.detail || 'Não foi possível anular.', 'danger');
  } catch (e) { mostrarToast(e?.message || 'Erro ao anular a justificação.', 'danger'); }
};
const PRES_PERFIS_LIMITE = ['DIRECTOR_ESCOLA', 'ADMIN_ESCOLA', 'SUPERADMIN'];
const PRES_PERFIS_SMS = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'FINANCEIRO'];

window.presDefinirLimite = async function () {
  const atual = presState.limite ?? '';
  const v = prompt('Limite de faltas (%) a partir do qual o aluno entra em risco (1-100). Deixe vazio para desactivar os alertas:', atual);
  if (v === null) return;
  try {
    const res = await apiFetch('/api/v1/alunos/presencas/limite/', { method: 'POST', body: JSON.stringify({ limite_percent: v.trim() }) });
    if (res?.success) { mostrarToast(res.limite_percent ? `Limite definido: ${res.limite_percent}%.` : 'Alertas de risco desactivados.', 'success'); presCarregarAlunos(); }
    else mostrarToast(res?.message || res?.detail || 'Não foi possível definir o limite.', 'danger');
  } catch (e) { mostrarToast(e?.message || 'Erro ao definir o limite.', 'danger'); }
};

// Aviso manual ao encarregado (confirmado pelo utilizador) pelo gateway SMS já configurado da escola.
window.presAvisarEncarregado = async function (alunoId, dataTxt, disciplina) {
  const al = presState.alunos.find(a => String(a.id) === String(alunoId));
  if (!al?.contato_responsavel) { mostrarToast('Este aluno não tem contacto do encarregado registado.', 'warning'); return; }
  const [a, m, d] = String(dataTxt).split('-');
  const texto = `Aviso da escola: o educando ${al.nome || ''} ${al.apelido || ''} faltou em ${d}/${m}/${a}${disciplina ? ' (' + disciplina + ')' : ''}. Em caso de motivo justificado, contacte a secretaria.`.replace(/\s+/g, ' ');
  if (!confirm(`Enviar SMS ao encarregado (${al.contato_responsavel})?\n\n${texto}`)) return;
  try {
    const res = await apiFetch('/api/v1/ferramentas/sms/enviar', {
      method: 'POST',
      body: JSON.stringify({ modo: 'MANUAL', destinatarios: al.contato_responsavel, mensagem: texto, tipo: 'FALTA', canal: 'ANDROID_GATEWAY' })
    });
    if (res?.success) mostrarToast('Aviso enviado ao encarregado.', 'success');
    else mostrarToast(res?.message || res?.detail || 'Não foi possível enviar o aviso.', 'danger');
  } catch (e) { mostrarToast(e?.message || 'Erro ao enviar o aviso.', 'danger'); }
};

function presCelulasBase(al, i) {
  const r = presState.risco?.[String(al.id)];
  const risco = r ? ` <span class="badge bg-danger" title="${r.percent_faltas}% de faltas (limite ${presState.limite}%)"><i class="bi bi-exclamation-triangle-fill me-1"></i>Em risco ${String(r.percent_faltas).replace('.', ',')}%</span>` : '';
  return `<td class="ps-3 text-muted">${i + 1}</td>
    <td class="font-monospace small">${escapeHtml(al.matricula)}</td>
    <td class="fw-semibold">${escapeHtml((al.nome || '') + ' ' + (al.apelido || ''))}${risco}</td>`;
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
  const regs = presState.registos[al.id] || [];
  const podeJustificar = PRES_PERFIS_JUSTIFICAR.includes(state.user?.role);
  const badges = regs.length ? regs.map(reg => {
    const e = PRES_ESTADOS.find(x => x.v === reg.status);
    const disc = reg.disciplina_nome ? ` <small class="text-muted">${escapeHtml(reg.disciplina_nome)}</small>` : '';
    const falta = reg.status === 'FALTA_INJUSTIFICADA';
    let btn = (podeJustificar && falta)
      ? ` <button type="button" class="btn btn-link btn-sm p-0 align-baseline" onclick="presJustificar('${escapeHtml(String(reg.id))}')">Justificar</button>` : '';
    if (falta && PRES_PERFIS_SMS.includes(state.user?.role)) {
      btn += ` <button type="button" class="btn btn-link btn-sm p-0 align-baseline" title="Enviar SMS ao encarregado" onclick="presAvisarEncarregado('${escapeHtml(String(al.id))}','${escapeHtml(String(reg.data))}','${escapeHtml(reg.disciplina_nome || '')}')"><i class="bi bi-chat-dots"></i> Avisar</button>`;
    }
    return `<div><span class="badge bg-${e?.cls || 'secondary'}">${e?.rotulo || escapeHtml(reg.status)}</span>${disc}${btn}</div>`;
  }).join('') : '<span class="badge bg-light text-muted border">Sem registo</span>';
  const obs = regs.map(r => [
    r.observacao,
    r.justificacao ? `Justificação: ${r.justificacao}` : '',
    (r.pedido_justificacao && r.status === 'FALTA_INJUSTIFICADA') ? `Pedido do encarregado: ${r.pedido_justificacao}` : ''
  ].filter(Boolean).join(' · ')).filter(Boolean).join(' | ');
  return `<tr>${presCelulasBase(al, i)}<td class="text-center">${badges}</td>
    <td class="pe-3 small text-muted">${escapeHtml(obs)}</td></tr>`;
}

function presAtualizarResumo() {
  const resumo = document.getElementById('presResumo');
  if (!resumo) return;
  const cont = { PRESENTE: 0, FALTA_JUSTIFICADA: 0, FALTA_INJUSTIFICADA: 0, ATRASO: 0 };
  if (presEhProfessor()) {
    // Conta todos os alunos (inclui os ocultos pela pesquisa): marcação local > registo guardado > Presente.
    const visiveis = {};
    document.querySelectorAll('#tabelaListaPresencas input[type="radio"]:checked').forEach(r => { visiveis[r.name.replace('pres_', '')] = r.value; });
    presState.alunos.forEach(al => {
      const st = visiveis[al.id] || presState.registos[al.id]?.status || 'PRESENTE';
      if (st in cont) cont[st]++;
    });
  } else {
    Object.values(presState.registos).flat().forEach(r => { if (r.status in cont) cont[r.status]++; });
  }
  const nRisco = Object.keys(presState.risco || {}).length;
  const limiteTxt = presState.limite ? ` · <span class="${nRisco ? 'text-danger fw-semibold' : ''}">${nRisco} em risco (≥ ${presState.limite}% faltas)</span>` : '';
  const btnLimite = PRES_PERFIS_LIMITE.includes(state.user?.role)
    ? ` · <a href="#" class="small" onclick="presDefinirLimite(); return false;">${presState.limite ? 'alterar' : 'definir'} limite de faltas</a>` : '';
  resumo.innerHTML = `${presState.alunos.length} alunos${limiteTxt}${btnLimite} ·<span class="text-success">${cont.PRESENTE} presentes</span> · ` +
    `<span class="text-warning">${cont.FALTA_JUSTIFICADA} F. justif.</span> · ` +
    `<span class="text-danger">${cont.FALTA_INJUSTIFICADA} F. injustif.</span> · ${cont.ATRASO} atrasos` +
    (presEhProfessor() && document.getElementById('presAulas')?.value
      ? ` · <b>${(cont.FALTA_JUSTIFICADA + cont.FALTA_INJUSTIFICADA) * Number(document.getElementById('presAulas').value)} falta(s) a registar</b>` : '');
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
  const aulas = Number(document.getElementById('presAulas')?.value || 0);
  if (![1, 2].includes(aulas)) {
    mostrarToast('Indique primeiro se é 1 aula ou aula dupla (2 aulas) antes de lançar as faltas.', 'warning');
    document.getElementById('presAulas')?.focus();
    return;
  }
  presGuardarMarcacoesLocais();
  const registos = presState.alunos.map(al => ({
    aluno: String(al.id),
    status: presState.registos[al.id]?.status || 'PRESENTE',
    observacao: presState.registos[al.id]?.observacao || ''
  }));
  if (!registos.length) { mostrarToast('Nenhum aluno na lista para guardar.', 'warning'); return; }

  const btn = document.getElementById('presBtnSalvar');
  if (btn) btn.disabled = true;
  try {
    const res = await apiFetch('/api/v1/alunos/presencas/lote/', {
      method: 'POST', body: JSON.stringify({ turma, disciplina, data, aulas, registos })
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

// Aviso imediato do que cada ausência vai valer (1 aula = 1 falta; aula dupla = 2 faltas).
function presAtualizarInfoAulas() {
  const v = document.getElementById('presAulas')?.value;
  const el = document.getElementById('presAulasInfo');
  if (!el) return;
  el.className = 'alert py-2 px-3 mb-0 small ' + (v === '2' ? 'alert-warning' : 'alert-info');
  el.innerHTML = v === '2'
    ? '<i class="bi bi-2-square me-1"></i><b>Aula dupla (2 aulas):</b> cada aluno ausente fica com <b>2 faltas</b> automaticamente.'
    : v === '1'
      ? '<i class="bi bi-1-square me-1"></i><b>1 aula:</b> cada aluno ausente fica com <b>1 falta</b>.'
      : '<i class="bi bi-info-circle me-1"></i>Escolha o tipo de aula: <b>1 aula = 1 falta</b> · <b>aula dupla (2 aulas) = 2 faltas</b>, contadas automaticamente por aluno ausente.';
  presAtualizarResumo();
}
