/**
 * SIGE - PAINEL-ESCOLA | Atribuição de Actividades aos Cargos Pedagógicos
 * Director de Turma, Director de Classe e Delegado da Disciplina.
 * Filtros em cascata (Cargo -> Classe -> Turma/Disciplina -> Professor); lista paginada (altura constante).
 */
let atrAno = null;
let atrTurmas = [];
let atrDisciplinas = [];
let atrProfessores = [];
let atrSugestoes = [];
let atrFila = [];          // actividades escolhidas para atribuir
let atrPagina = 1;
let atrTimerPesquisa = null;

const ATR_CARGOS = { DIRECTOR_TURMA: 'Director de Turma', DIRECTOR_CLASSE: 'Director de Classe', DELEGADO_DISCIPLINA: 'Delegado da Disciplina' };
const ATR_ESTADOS = { PENDENTE: ['Pendente', 'secondary'], EM_CURSO: ['Em curso', 'warning text-dark'], CONCLUIDA: ['Concluída', 'success'] };

function atrEsc(t) {
  const d = document.createElement('div');
  d.textContent = t == null ? '' : String(t);
  return d.innerHTML.replace(/"/g, '&quot;');
}

function atrNumeroClasse(c) {
  const m = String(c || '').match(/\d+/);
  return m ? parseInt(m[0], 10) : 99;
}

async function carregarAtribuicoesCargos(ano) {
  atrAno = ano || (state.anosPorView && state.anosPorView['atribuicoes-cargos']) || null;
  if (!atrAno) return;
  try {
    const [rt, rd, rp] = await Promise.all([
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/disciplinas'),
      apiFetch('/api/v1/professores')
    ]);
    atrTurmas = (rt.data || []).filter(t => String(t.ano_letivo) === String(atrAno));
    atrDisciplinas = rd.data || [];
    atrProfessores = (rp.data || []).filter(p => p.ativo !== false);
  } catch (err) {
    atrTurmas = []; atrDisciplinas = []; atrProfessores = [];
  }
  atrFila = [];
  atrRenderFila();
  atrPreencherSelect('atrProfessor', atrProfessores.map(p => [p.id, `${p.nome} ${p.apelido || ''}`.trim()]), 'Professor');
  document.getElementById('atrProfessor').disabled = atrProfessores.length === 0;
  const classes = atrClassesDoAno();
  atrPreencherSelect('atrFClasse', classes.map(c => [c, c]), 'Todas as classes');
  atrAoMudarCargo();
  await atrListar(1);
}

function atrClassesDoAno() {
  const set = new Set(atrTurmas.map(t => t.grau_ano));
  atrDisciplinas.forEach(d => { if (d.classe) set.add(d.classe); });
  return [...set].filter(Boolean).sort((a, b) => atrNumeroClasse(a) - atrNumeroClasse(b));
}

function atrPreencherSelect(id, pares, rotuloVazio) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `<option value="">-- ${atrEsc(rotuloVazio)} --</option>` +
    pares.map(([v, t]) => `<option value="${atrEsc(v)}">${atrEsc(t)}</option>`).join('');
}

function atrAoMudarCargo() {
  const cargo = document.getElementById('atrCargo').value;
  const selClasse = document.getElementById('atrClasse');
  const selLocal = document.getElementById('atrLocal');
  const rotulo = document.getElementById('atrLocalRotulo');
  const colLocal = document.getElementById('atrColLocal');
  atrFila = [];
  atrRenderFila();
  if (!cargo) {
    atrPreencherSelect('atrClasse', [], 'Classe'); selClasse.disabled = true;
    atrPreencherSelect('atrLocal', [], 'Local'); selLocal.disabled = true;
    document.getElementById('atrSugestoes').innerHTML = '<div class="text-muted small p-2">Escolha o cargo para ver as sugestões.</div>';
    return;
  }
  atrPreencherSelect('atrClasse', atrClassesDoAno().map(c => [c, c]), 'Classe');
  selClasse.disabled = false;
  colLocal.style.display = cargo === 'DIRECTOR_CLASSE' ? 'none' : '';
  rotulo.textContent = cargo === 'DELEGADO_DISCIPLINA' ? '3. Disciplina' : '3. Turma';
  atrAoMudarClasse();
  atrCarregarSugestoes(cargo);
}

function atrAoMudarClasse() {
  const cargo = document.getElementById('atrCargo').value;
  const classe = document.getElementById('atrClasse').value;
  const selLocal = document.getElementById('atrLocal');
  if (cargo === 'DIRECTOR_TURMA') {
    const turmas = atrTurmas.filter(t => t.grau_ano === classe);
    atrPreencherSelect('atrLocal', turmas.map(t => [t.id, `${t.nome}${t.area && t.area !== 'Geral' ? ' — ' + t.area : ''}`]), 'Turma');
    selLocal.disabled = !classe || turmas.length === 0;
  } else if (cargo === 'DELEGADO_DISCIPLINA') {
    const vistos = new Set();
    const discs = atrDisciplinas.filter(d => d.classe === classe && (!d.ano_letivo || String(d.ano_letivo) === String(atrAno)))
      .filter(d => { const k = `${d.nome}|${d.area}`; if (vistos.has(k)) return false; vistos.add(k); return true; });
    atrPreencherSelect('atrLocal', discs.map(d => [d.id, `${d.nome}${d.area && d.area !== 'Geral' ? ' — ' + d.area : ''}`]), 'Disciplina');
    selLocal.disabled = !classe || discs.length === 0;
  } else {
    atrPreencherSelect('atrLocal', [], 'Local');
    selLocal.disabled = true;
  }
}

async function atrCarregarSugestoes(cargo) {
  const box = document.getElementById('atrSugestoes');
  box.innerHTML = '<div class="text-muted small p-2">A carregar...</div>';
  try {
    const res = await apiFetch(`/api/v1/atribuicoes/sugestoes/?cargo=${cargo}`);
    atrSugestoes = res.data || [];
  } catch (_) { atrSugestoes = []; }
  atrRenderSugestoes();
}

function atrRenderSugestoes() {
  const box = document.getElementById('atrSugestoes');
  if (!atrSugestoes.length) { box.innerHTML = '<div class="text-muted small p-2">Sem sugestões para este cargo.</div>'; return; }
  box.innerHTML = atrSugestoes.map((s, i) => {
    const marcada = atrFila.some(f => f.titulo === s.titulo);
    return `
      <div class="form-check py-1 border-bottom">
        <input class="form-check-input" type="checkbox" id="atrSug${i}" ${marcada ? 'checked' : ''} onchange="atrAlternarSugestao(${i}, this.checked)">
        <label class="form-check-label small" for="atrSug${i}">
          <span class="fw-semibold">${atrEsc(s.titulo)}</span>${s.origem === 'ESCOLA' ? ' <span class="badge bg-info text-dark">da escola</span>' : ''}
          <span class="d-block text-muted" style="font-size: 0.75rem;">${atrEsc(s.descricao)}</span>
        </label>
        ${s.origem === 'ESCOLA' ? `<button type="button" class="btn btn-link btn-sm text-danger p-0 float-end" title="Remover das sugestões" onclick="atrRemoverModelo('${s.id}')"><i class="bi bi-trash"></i></button>` : ''}
      </div>`;
  }).join('');
}

function atrAlternarSugestao(i, marcada) {
  const s = atrSugestoes[i];
  if (!s) return;
  if (marcada) {
    if (!atrFila.some(f => f.titulo === s.titulo)) atrFila.push({ titulo: s.titulo, descricao: s.descricao, prioridade: 'NORMAL', prazo: '' });
  } else {
    atrFila = atrFila.filter(f => f.titulo !== s.titulo);
  }
  atrRenderFila();
}

function atrAdicionarPropria() {
  const titulo = document.getElementById('atrNovoTitulo').value.trim();
  if (!titulo) return alert('Escreva o título da actividade.');
  if (atrFila.some(f => f.titulo === titulo)) return alert('Esta actividade já está na lista.');
  atrFila.push({
    titulo,
    descricao: document.getElementById('atrNovoDescricao').value.trim(),
    prazo: document.getElementById('atrNovoPrazo').value,
    prioridade: document.getElementById('atrNovoPrioridade').value,
    guardar_modelo: document.getElementById('atrGuardarModelo').checked
  });
  ['atrNovoTitulo', 'atrNovoDescricao', 'atrNovoPrazo'].forEach(id => { document.getElementById(id).value = ''; });
  document.getElementById('atrGuardarModelo').checked = false;
  atrRenderFila();
}

function atrRenderFila() {
  const el = document.getElementById('atrFila');
  if (!el) return;
  document.getElementById('atrContaFila').textContent = atrFila.length;
  if (!atrFila.length) { el.innerHTML = '<span class="text-muted">Nenhuma actividade escolhida.</span>'; return; }
  el.innerHTML = atrFila.map((f, i) => `
    <div class="d-flex align-items-center gap-2 py-1 border-bottom flex-wrap">
      <span class="flex-grow-1 fw-semibold">${atrEsc(f.titulo)}</span>
      <input type="date" class="form-control form-control-sm" style="width: 140px;" value="${atrEsc(f.prazo || '')}" title="Prazo" onchange="atrFila[${i}].prazo = this.value">
      <select class="form-select form-select-sm" style="width: 100px;" onchange="atrFila[${i}].prioridade = this.value">
        ${['NORMAL', 'ALTA', 'BAIXA'].map(p => `<option value="${p}" ${f.prioridade === p ? 'selected' : ''}>${p[0] + p.slice(1).toLowerCase()}</option>`).join('')}
      </select>
      <button type="button" class="btn btn-sm btn-outline-danger py-0" onclick="atrTirarDaFila(${i})"><i class="bi bi-x-lg"></i></button>
    </div>`).join('');
}

function atrTirarDaFila(i) {
  atrFila.splice(i, 1);
  atrRenderFila();
  atrRenderSugestoes();
}

function atrLimparFormulario() {
  document.getElementById('atrCargo').value = '';
  atrAoMudarCargo();
  document.getElementById('atrProfessor').value = '';
}

async function atrRemoverModelo(id) {
  if (!confirm('Remover esta actividade das sugestões da escola? As actividades já atribuídas não são afectadas.')) return;
  try {
    await apiFetch(`/api/v1/atribuicoes/modelos/${id}`, { method: 'DELETE' });
    await atrCarregarSugestoes(document.getElementById('atrCargo').value);
  } catch (err) { alert(err.message || 'Erro ao remover.'); }
}

async function atrAtribuir() {
  const cargo = document.getElementById('atrCargo').value;
  const classe = document.getElementById('atrClasse').value;
  const local = document.getElementById('atrLocal').value;
  const professor = document.getElementById('atrProfessor').value;
  if (!cargo) return alert('Seleccione o cargo.');
  if (!classe) return alert('Seleccione a classe.');
  if (cargo === 'DIRECTOR_TURMA' && !local) return alert('Seleccione a turma.');
  if (cargo === 'DELEGADO_DISCIPLINA' && !local) return alert('Seleccione a disciplina.');
  if (!professor) return alert('Seleccione o professor responsável.');
  if (!atrFila.length) return alert('Escolha ou escreva pelo menos uma actividade.');

  const corpo = { cargo, professor_id: professor, classe, ano_letivo: atrAno, atividades: atrFila };
  if (cargo === 'DIRECTOR_TURMA') corpo.turma_id = local;
  if (cargo === 'DELEGADO_DISCIPLINA') corpo.disciplina_id = local;

  const btn = document.getElementById('atrBtnAtribuir');
  btn.disabled = true;
  try {
    const res = await apiFetch('/api/v1/atribuicoes/', { method: 'POST', body: JSON.stringify(corpo) });
    if (res.success) {
      alert(`${res.data.length} actividade(s) atribuída(s) com sucesso.`);
      atrFila = [];
      atrRenderFila();
      await atrCarregarSugestoes(cargo);
      await atrListar(1);
    }
  } catch (err) {
    alert(err.message || 'Erro ao atribuir actividades.');
  } finally {
    btn.disabled = false;
  }
}

function atrPesquisarDebounce() {
  clearTimeout(atrTimerPesquisa);
  atrTimerPesquisa = setTimeout(() => atrListar(1), 350);
}

async function atrListar(pagina) {
  if (!atrAno) return;
  atrPagina = pagina || 1;
  const lista = document.getElementById('atrLista');
  const q = new URLSearchParams({ ano: atrAno, page: atrPagina, page_size: 10 });
  [['cargo', 'atrFCargo'], ['classe', 'atrFClasse'], ['estado', 'atrFEstado'], ['search', 'atrFPesquisa']].forEach(([k, id]) => {
    const v = document.getElementById(id)?.value?.trim();
    if (v) q.set(k, v);
  });
  lista.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary"></div></div>';
  try {
    const res = await apiFetch(`/api/v1/atribuicoes/?${q}`, { noCache: true });
    atrRenderLista(res);
  } catch (err) {
    lista.innerHTML = `<div class="alert alert-danger small mb-0">${atrEsc(err.message || 'Erro ao carregar as actividades.')}</div>`;
  }
}

function atrBadgeEstado(e) {
  const [nome, cls] = ATR_ESTADOS[e] || [e, 'secondary'];
  return `<span class="badge bg-${cls}">${nome}</span>`;
}

function atrRenderLista(res) {
  const lista = document.getElementById('atrLista');
  const itens = res.data || [];
  if (!itens.length) {
    lista.innerHTML = '<div class="text-center text-muted py-4"><i class="bi bi-clipboard fs-3 d-block mb-1"></i>Ainda não há actividades atribuídas para estes filtros.</div>';
    document.getElementById('atrPaginacao').innerHTML = '';
    return;
  }
  lista.innerHTML = `
    <div class="table-responsive">
      <table class="table table-sm table-bordered align-middle small mb-0">
        <thead class="table-light text-center">
          <tr><th>Cargo</th><th>Responsável</th><th>Classe / Local</th><th class="text-start">Actividade</th><th>Prazo</th><th>Estado</th><th class="no-print">Acções</th></tr>
        </thead>
        <tbody>
          ${itens.map(a => `
            <tr>
              <td>${atrEsc(a.cargo_nome)}</td>
              <td>${atrEsc(a.professor_nome)}</td>
              <td>${atrEsc(a.classe)}${a.turma_nome ? ' — ' + atrEsc(a.turma_nome) : ''}${a.disciplina_nome ? ' — ' + atrEsc(a.disciplina_nome) : ''}</td>
              <td class="text-start">
                <span class="fw-semibold">${atrEsc(a.titulo)}</span>${a.prioridade === 'ALTA' ? ' <span class="badge bg-danger">Alta</span>' : ''}
                ${a.descricao ? `<div class="text-muted" style="font-size: 0.75rem;">${atrEsc(a.descricao)}</div>` : ''}
                ${a.nota_responsavel ? `<div class="text-primary" style="font-size: 0.75rem;"><i class="bi bi-chat-left-text me-1"></i>${atrEsc(a.nota_responsavel)}</div>` : ''}
              </td>
              <td class="text-center ${a.atrasada ? 'text-danger fw-bold' : ''}">${a.prazo ? new Date(a.prazo + 'T00:00:00').toLocaleDateString('pt-PT') : '-'}${a.atrasada ? '<br>(em atraso)' : ''}</td>
              <td class="text-center">${atrBadgeEstado(a.estado)}</td>
              <td class="text-center text-nowrap no-print">
                <button class="btn btn-sm btn-outline-primary py-0" title="Atribuir mais actividades a este responsável" onclick='atrMaisParaResponsavel(${JSON.stringify(a).replace(/'/g, "&#39;")})'><i class="bi bi-plus-lg"></i></button>
                <button class="btn btn-sm btn-outline-secondary py-0" title="Editar" onclick='atrEditar(${JSON.stringify(a).replace(/'/g, "&#39;")})'><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-outline-danger py-0" title="Remover" onclick="atrRemover('${a.id}')"><i class="bi bi-trash"></i></button>
              </td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
  const totalPaginas = Math.max(1, Math.ceil(res.total / res.page_size));
  document.getElementById('atrPaginacao').innerHTML = `
    <span class="text-muted">${res.total} actividade(s) · página ${res.page} de ${totalPaginas}</span>
    <div class="btn-group btn-group-sm">
      <button class="btn btn-outline-secondary" ${res.page <= 1 ? 'disabled' : ''} onclick="atrListar(${res.page - 1})"><i class="bi bi-chevron-left"></i></button>
      <button class="btn btn-outline-secondary" ${res.page >= totalPaginas ? 'disabled' : ''} onclick="atrListar(${res.page + 1})"><i class="bi bi-chevron-right"></i></button>
    </div>`;
}

// "+" numa linha: pré-preenche o formulário com o mesmo cargo/local/responsável para acrescentar mais actividades.
function atrMaisParaResponsavel(a) {
  const selCargo = document.getElementById('atrCargo');
  selCargo.value = a.cargo;
  atrAoMudarCargo();
  document.getElementById('atrClasse').value = a.classe;
  atrAoMudarClasse();
  if (a.cargo === 'DIRECTOR_TURMA') document.getElementById('atrLocal').value = a.turma_id || '';
  if (a.cargo === 'DELEGADO_DISCIPLINA') document.getElementById('atrLocal').value = a.disciplina_id || '';
  document.getElementById('atrProfessor').value = a.professor_id;
  document.getElementById('atrCardNova').scrollIntoView({ behavior: 'smooth', block: 'start' });
  document.getElementById('atrNovoTitulo').focus();
}

function atrEditar(a) {
  abrirModal('Editar actividade', `
    <div class="mb-2"><label class="form-label small fw-bold">Título</label><input type="text" id="atrEdTitulo" class="form-control form-control-sm" value="${atrEsc(a.titulo)}" maxlength="255"></div>
    <div class="mb-2"><label class="form-label small fw-bold">Descrição</label><textarea id="atrEdDescricao" class="form-control form-control-sm" rows="3">${atrEsc(a.descricao)}</textarea></div>
    <div class="row g-2 mb-3">
      <div class="col-6"><label class="form-label small fw-bold">Prazo</label><input type="date" id="atrEdPrazo" class="form-control form-control-sm" value="${atrEsc(a.prazo || '')}"></div>
      <div class="col-6"><label class="form-label small fw-bold">Prioridade</label>
        <select id="atrEdPrioridade" class="form-select form-select-sm">
          ${['NORMAL', 'ALTA', 'BAIXA'].map(p => `<option value="${p}" ${a.prioridade === p ? 'selected' : ''}>${p[0] + p.slice(1).toLowerCase()}</option>`).join('')}
        </select></div>
    </div>
    <div class="text-end"><button class="btn btn-sm btn-primary" onclick="atrGravarEdicao('${a.id}')"><i class="bi bi-save me-1"></i> Gravar</button></div>`);
}

async function atrGravarEdicao(id) {
  const titulo = document.getElementById('atrEdTitulo').value.trim();
  if (!titulo) return alert('O título é obrigatório.');
  try {
    await apiFetch(`/api/v1/atribuicoes/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify({
        titulo,
        descricao: document.getElementById('atrEdDescricao').value,
        prazo: document.getElementById('atrEdPrazo').value || null,
        prioridade: document.getElementById('atrEdPrioridade').value
      })
    });
    fecharModal();
    await atrListar(atrPagina);
  } catch (err) { alert(err.message || 'Erro ao gravar.'); }
}

async function atrRemover(id) {
  if (!confirm('Remover esta actividade atribuída?')) return;
  try {
    await apiFetch(`/api/v1/atribuicoes/${id}/`, { method: 'DELETE' });
    await atrListar(atrPagina);
  } catch (err) { alert(err.message || 'Erro ao remover.'); }
}
