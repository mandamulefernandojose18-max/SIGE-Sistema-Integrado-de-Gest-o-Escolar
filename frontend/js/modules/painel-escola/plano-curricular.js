/**
 * SIGE - PAINEL-ESCOLA | Plano Curricular
 * Ficheiro de código independente do menu: plano-curricular.js
 *
 * Ordem lógica (única página, substitui "Classes / Níveis & Exames" e "Disciplinas"):
 *   1) Classe / Nível e se tem exame (Sim / Não)
 *   2) Disciplinas da Classe / Nível
 *   3) Áreas / Secções da Classe / Nível
 *   4) Disciplinas de cada Área / Secção (e, se a classe tem exame, quais têm exame)
 * Tudo funciona por filtros em cascata e listas (altura constante, para qualquer número de classes/áreas/disciplinas).
 */
(function () {
  'use strict';

  const API_CLASSES = '/api/v1/escola-admin/classes-exames';
  const API_PLANO = '/api/v1/plano-curricular';

  const P = {
    regime: 'CLASSES',
    classes: [],          // [{nome, tem_exame}] do regime activo
    estrutura: { classes: [] },
    catalogo: [],         // [{id, nome, usos}] "Todas Disciplinas de Ensino"
    classe: '',           // classe seleccionada
    dados: null,          // plano da classe seleccionada
    areaId: '',
    marcas: {},           // {disciplinaId: {marcado, exame}} da área seleccionada
    passo: 1,
    codigoManual: false
  };

  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const normTxt = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  function aviso(texto, tipo) {
    if (typeof window.mostrarNotificacao === 'function') window.mostrarNotificacao(texto, tipo || 'info');
    else if (typeof window.mostrarToast === 'function') window.mostrarToast(texto, tipo || 'info');
  }
  function erro(e) { aviso((e && e.message) || 'Não foi possível concluir a operação.', 'danger'); }
  function pedir(url, opcoes) { return window.apiFetch(url, opcoes); }
  function json(metodo, corpo) { return { method: metodo, body: JSON.stringify(corpo || {}) }; }
  function anoActivo() {
    return (typeof state !== 'undefined' && state.anosPorView && state.anosPorView['plano-curricular']) || (typeof state !== 'undefined' && state.anoLectivoVisualizacao) || '2026';
  }
  const ehNivel = (nome) => /n[ií]vel/i.test(nome);

  async function sincronizarGlobais() {
    try {
      const r = await pedir('/api/v1/disciplinas');
      if (r && r.success) state.todasDisciplinas = r.data || [];
    } catch (_) { /* a página continua com o que já tem */ }
    if (typeof window.carregarEstruturaPlano === 'function') {
      P.estrutura = await window.carregarEstruturaPlano();
    }
  }

  // ---------------------------------------------------------------- carregamento
  async function carregarClasses() {
    const r = await pedir(API_CLASSES);
    if (!r || !r.success) throw new Error((r && r.message) || 'Não foi possível carregar as classes.');
    P.regime = r.regime || 'CLASSES';
    const todas = Array.isArray(r.data) ? r.data : [];
    P.classes = todas.filter((c) => (P.regime === 'NIVEIS') === ehNivel(c.nome));
    if (P.classe && !P.classes.some((c) => c.nome === P.classe)) P.classe = '';
    if (!P.classe && P.classes.length) P.classe = P.classes[0].nome;
    const reg = $('pcRegime');
    if (reg) reg.value = P.regime;
  }

  async function carregarClasseActual() {
    P.dados = null;
    if (!P.classe) return;
    const r = await pedir(API_PLANO + '/classe/?classe=' + encodeURIComponent(P.classe));
    if (r && r.success) P.dados = r.data;
    if (P.dados && !P.dados.areas.some((a) => a.id === P.areaId)) P.areaId = P.dados.areas.length ? P.dados.areas[0].id : '';
  }

  async function carregarCatalogo() {
    const r = await pedir(API_PLANO + '/catalogo/');
    P.catalogo = (r && r.success && Array.isArray(r.data)) ? r.data : [];
  }

  async function recarregar(manterPasso) {
    try {
      await carregarCatalogo();
      await carregarClasses();
      await carregarClasseActual();
      await sincronizarGlobais();
    } catch (e) { erro(e); }
    desenhar(manterPasso);
  }

  // ---------------------------------------------------------------- desenho
  function desenhar() {
    desenharPassos();
    desenharFiltroClasse();
    desenharCatalogo();
    desenharClasses();
    desenharDisciplinas();
    desenharListaCatalogo();
    desenharAreas();
    desenharSelectAreas();
    desenharVinculos();
  }

  function desenharPassos() {
    document.querySelectorAll('#pcPassos .nav-link').forEach((b) => {
      const ativo = Number(b.dataset.passo) === P.passo;
      b.classList.toggle('active', ativo);
      const badge = b.querySelector('.badge');
      if (badge) badge.className = 'badge me-1 ' + (ativo ? 'bg-white text-primary' : 'bg-primary text-white');
    });
    for (let i = 0; i <= 4; i++) {
      const el = $('pcPasso' + i);
      if (el) el.classList.toggle('d-none', i !== P.passo);
    }
    const filtro = $('pcFiltroClasse');
    if (filtro) filtro.classList.toggle('d-none', P.passo <= 1 || !P.classes.length);
    const av = $('pcAviso');
    if (av) {
      let msg = '';
      if (P.passo > 1 && !P.classes.length) msg = 'Cadastre primeiro, no passo 1, a Classe / Nível.';
      else if (P.passo === 2 && !P.catalogo.length) msg = 'Ainda não há disciplinas em "Todas Disciplinas de Ensino": cadastre-as primeiro nesse separador.';
      else if (P.passo === 4 && P.dados && !P.dados.areas.length) msg = 'Esta classe ainda não tem Áreas / Secções: cadastre-as no passo 3.';
      else if (P.passo === 4 && P.dados && !P.dados.disciplinas.length) msg = 'Esta classe ainda não tem disciplinas: cadastre-as no passo 2.';
      av.textContent = msg;
      av.classList.toggle('d-none', !msg);
    }
  }

  function desenharFiltroClasse() {
    const sel = $('pcClasseSelect');
    if (!sel) return;
    sel.innerHTML = P.classes.map((c) => '<option value="' + esc(c.nome) + '"' + (c.nome === P.classe ? ' selected' : '') + '>' + esc(c.nome) + '</option>').join('');
    const cls = P.classes.find((c) => c.nome === P.classe);
    const b = $('pcBadgeExame');
    if (b) {
      b.className = 'badge ' + (cls ? (cls.tem_exame ? 'bg-danger' : 'bg-secondary') : 'bg-secondary');
      b.textContent = cls ? (cls.tem_exame ? 'Com exame (Sim)' : 'Sem exame (Não)') : '—';
    }
  }

  function infoClasse(nome) {
    const e = (P.estrutura.classes || []).find((c) => c.nome === nome);
    return e || { total_disciplinas: 0, areas: [] };
  }

  function desenharCatalogo() {
    const tb = $('pcTabelaCatalogo');
    if (!tb) return;
    const q = normTxt(($('pcCatBusca') || {}).value);
    const vis = P.catalogo.filter((c) => !q || normTxt(c.nome).includes(q));
    const r = $('pcCatResumo');
    if (r) r.textContent = P.catalogo.length ? (vis.length + ' de ' + P.catalogo.length + ' disciplina(s)') : '';
    if (!P.catalogo.length) {
      tb.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4"><i class="bi bi-collection fs-3 text-primary d-block mb-1"></i>Ainda não há disciplinas. Cadastre a primeira acima (ou várias de uma vez).</td></tr>';
      return;
    }
    if (!vis.length) {
      tb.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-3">Nenhuma disciplina corresponde à pesquisa.</td></tr>';
      return;
    }
    tb.innerHTML = vis.map((c) => '<tr><td class="fw-semibold">' + esc(c.nome) + '</td>' +
      '<td class="text-center"><span class="badge bg-light text-dark border">' + (c.usos || 0) + '</span></td>' +
      '<td class="text-end"><button class="btn btn-outline-primary btn-sm py-0 px-2 me-1" title="Renomear" onclick="PlanoCurricular.editarCatalogo(\'' + esc(c.id) + '\')"><i class="bi bi-pencil-square"></i></button>' +
      '<button class="btn btn-outline-danger btn-sm py-0 px-2" title="Eliminar" onclick="PlanoCurricular.eliminarCatalogo(\'' + esc(c.id) + '\')"><i class="bi bi-trash"></i></button></td></tr>').join('');
  }

  // Lista (datalist) do passo 2: só disciplinas do catálogo que ainda não estão nesta classe.
  function desenharListaCatalogo() {
    const dl = $('pcDiscLista');
    if (!dl) return;
    const jaNaClasse = new Set(((P.dados && P.dados.disciplinas) || []).map((d) => d.catalogo));
    dl.innerHTML = P.catalogo.filter((c) => !jaNaClasse.has(c.id)).map((c) => '<option value="' + esc(c.nome) + '"></option>').join('');
  }

  function desenharClasses() {
    const oficiais = P.regime === 'NIVEIS' ? (window.LISTA_NIVEIS_OFICIAIS || []) : (window.LISTA_CLASSES_OFICIAIS || []);
    const livres = oficiais.filter((n) => !P.classes.some((c) => c.nome === n));
    const sel = $('pcNovaClasse');
    if (sel) {
      sel.innerHTML = livres.length
        ? livres.map((n) => '<option value="' + esc(n) + '">' + esc(n) + '</option>').join('')
        : '<option value="">Todas já cadastradas</option>';
      sel.disabled = !livres.length;
    }
    const rot = $('pcRotuloNovaClasse');
    if (rot) rot.textContent = P.regime === 'NIVEIS' ? 'Nível a cadastrar' : 'Classe a cadastrar';

    const tb = $('pcTabelaClasses');
    if (!tb) return;
    if (!P.classes.length) {
      tb.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4"><i class="bi bi-mortarboard fs-3 text-primary d-block mb-1"></i>Ainda não há ' + (P.regime === 'NIVEIS' ? 'níveis cadastrados' : 'classes cadastradas') + '. Comece por cadastrar a primeira acima.</td></tr>';
      return;
    }
    tb.innerHTML = P.classes.map((c, i) => {
      const inf = infoClasse(c.nome);
      return '<tr>' +
        '<td class="fw-semibold">' + esc(c.nome) + '</td>' +
        '<td><select class="form-select form-select-sm" onchange="PlanoCurricular.mudarExame(' + i + ', this.value)">' +
        '<option value="nao"' + (c.tem_exame ? '' : ' selected') + '>Não</option><option value="sim"' + (c.tem_exame ? ' selected' : '') + '>Sim</option></select></td>' +
        '<td class="text-center"><span class="badge bg-light text-dark border">' + (inf.total_disciplinas || 0) + '</span></td>' +
        '<td class="text-center"><span class="badge bg-light text-dark border">' + (inf.areas || []).length + '</span></td>' +
        '<td class="text-end"><button class="btn btn-outline-primary btn-sm py-0 px-2 me-1" title="Gerir disciplinas e áreas desta classe" onclick="PlanoCurricular.abrirClasse(' + i + ')"><i class="bi bi-arrow-right-circle"></i></button>' +
        '<button class="btn btn-outline-danger btn-sm py-0 px-2" title="Remover" onclick="PlanoCurricular.removerClasse(' + i + ')"><i class="bi bi-trash"></i></button></td></tr>';
    }).join('');
  }

  function desenharDisciplinas() {
    const tb = $('pcTabelaDisciplinas');
    if (!tb) return;
    const lista = (P.dados && P.dados.disciplinas) || [];
    const q = normTxt(($('pcDiscBusca') || {}).value);
    const vis = lista.filter((d) => !q || normTxt(d.nome).includes(q) || normTxt(d.codigo).includes(q));
    if (!lista.length) {
      tb.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">Nenhuma disciplina cadastrada nesta classe. Use o formulário acima.</td></tr>';
      return;
    }
    if (!vis.length) {
      tb.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">Nenhuma disciplina corresponde à pesquisa.</td></tr>';
      return;
    }
    tb.innerHTML = vis.map((d) => '<tr>' +
      '<td><code class="text-dark">' + esc(d.codigo) + '</code></td>' +
      '<td class="fw-semibold">' + esc(d.nome) + '</td>' +
      '<td>' + esc(d.carga_horaria) + ' h/sem</td>' +
      '<td class="small text-muted">' + (d.areas.length ? esc(d.areas.join(', ')) : '<span class="fst-italic">sem área</span>') + '</td>' +
      '<td class="text-end"><button class="btn btn-outline-primary btn-sm py-0 px-2 me-1" title="Editar" onclick="PlanoCurricular.editarDisciplina(\'' + esc(d.id) + '\')"><i class="bi bi-pencil-square"></i></button>' +
      '<button class="btn btn-outline-danger btn-sm py-0 px-2" title="Eliminar" onclick="PlanoCurricular.eliminarDisciplina(\'' + esc(d.id) + '\')"><i class="bi bi-trash"></i></button></td></tr>').join('');
  }

  function desenharAreas() {
    const tb = $('pcTabelaAreas');
    if (!tb) return;
    const areas = (P.dados && P.dados.areas) || [];
    if (!areas.length) {
      tb.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">Nenhuma Área / Secção cadastrada nesta classe. Use o formulário acima.</td></tr>';
      return;
    }
    tb.innerHTML = areas.map((a) => {
      const comExame = a.disciplinas.filter((x) => x.tem_exame).length;
      return '<tr><td class="fw-semibold">' + esc(a.nome) + '</td>' +
        '<td class="text-center"><span class="badge bg-light text-dark border">' + a.disciplinas.length + '</span></td>' +
        '<td class="text-center">' + (P.dados.tem_exame ? '<span class="badge ' + (comExame ? 'bg-danger' : 'bg-light text-dark border') + '">' + comExame + '</span>' : '<span class="text-muted small">classe sem exame</span>') + '</td>' +
        '<td class="text-end"><button class="btn btn-outline-success btn-sm py-0 px-2 me-1" title="Escolher as disciplinas desta área" onclick="PlanoCurricular.abrirArea(\'' + esc(a.id) + '\')"><i class="bi bi-list-check"></i></button>' +
        '<button class="btn btn-outline-primary btn-sm py-0 px-2 me-1" title="Renomear" onclick="PlanoCurricular.editarArea(\'' + esc(a.id) + '\')"><i class="bi bi-pencil-square"></i></button>' +
        '<button class="btn btn-outline-danger btn-sm py-0 px-2" title="Eliminar" onclick="PlanoCurricular.eliminarArea(\'' + esc(a.id) + '\')"><i class="bi bi-trash"></i></button></td></tr>';
    }).join('');
  }

  function areaActual() { return P.dados ? P.dados.areas.find((a) => a.id === P.areaId) : null; }

  function desenharSelectAreas() {
    const sel = $('pcAreaSelect');
    if (!sel) return;
    const areas = (P.dados && P.dados.areas) || [];
    sel.innerHTML = areas.length
      ? areas.map((a) => '<option value="' + esc(a.id) + '"' + (a.id === P.areaId ? ' selected' : '') + '>' + esc(a.nome) + '</option>').join('')
      : '<option value="">Sem áreas nesta classe</option>';
    sel.disabled = !areas.length;
    carregarMarcas();
  }

  function carregarMarcas() {
    P.marcas = {};
    const a = areaActual();
    if (a) a.disciplinas.forEach((v) => { P.marcas[v.disciplina] = { marcado: true, exame: !!v.tem_exame }; });
  }

  function desenharVinculos() {
    const tb = $('pcTabelaVinculos');
    if (!tb) return;
    const com = !!(P.dados && P.dados.tem_exame);
    const col = $('pcColExame');
    if (col) col.textContent = com ? 'Tem exame?' : 'Exame (classe sem exame)';
    const btn = $('pcVincGuardar');
    const a = areaActual();
    if (btn) btn.disabled = !a;
    const lista = (P.dados && P.dados.disciplinas) || [];
    if (!a || !lista.length) {
      tb.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">Escolha uma Área / Secção que tenha disciplinas cadastradas na classe.</td></tr>';
      const r = $('pcVincResumo'); if (r) r.textContent = '';
      return;
    }
    const q = normTxt(($('pcVincBusca') || {}).value);
    const vis = lista.filter((d) => !q || normTxt(d.nome).includes(q) || normTxt(d.codigo).includes(q));
    tb.innerHTML = vis.map((d) => {
      const m = P.marcas[d.id] || { marcado: false, exame: false };
      return '<tr class="' + (m.marcado ? 'table-active' : '') + '">' +
        '<td class="text-center"><input type="checkbox" class="form-check-input" ' + (m.marcado ? 'checked' : '') + ' onchange="PlanoCurricular.marcar(\'' + esc(d.id) + '\', this.checked)"></td>' +
        '<td><code class="text-dark">' + esc(d.codigo) + '</code></td><td class="fw-semibold">' + esc(d.nome) + '</td>' +
        '<td>' + (com
          ? '<select class="form-select form-select-sm" ' + (m.marcado ? '' : 'disabled') + ' onchange="PlanoCurricular.marcarExame(\'' + esc(d.id) + '\', this.value)"><option value="nao"' + (m.exame ? '' : ' selected') + '>Não</option><option value="sim"' + (m.exame ? ' selected' : '') + '>Sim</option></select>'
          : '<span class="text-muted small">—</span>') + '</td></tr>';
    }).join('') || '<tr><td colspan="4" class="text-center text-muted py-3">Nenhuma disciplina corresponde ao filtro.</td></tr>';
    const total = Object.values(P.marcas).filter((m) => m.marcado).length;
    const ex = Object.values(P.marcas).filter((m) => m.marcado && m.exame).length;
    const r = $('pcVincResumo');
    if (r) r.textContent = total + ' disciplina(s) nesta área' + (com ? ' · ' + ex + ' com exame' : '') + ' · de ' + lista.length + ' cadastradas na classe. Clique em "Guardar Área" para gravar.';
    const todas = $('pcVincTodas');
    if (todas) todas.checked = vis.length > 0 && vis.every((d) => (P.marcas[d.id] || {}).marcado);
  }

  // ---------------------------------------------------------------- acções públicas
  const API = {
    async init() {
      const sel = $('pcClasseSelect');
      if (!sel) return;
      await recarregar();
    },

    irPasso(n) {
      P.passo = n;
      if (n > 1 && P.classe && !P.dados) carregarClasseActual().then(desenhar);
      desenhar();
    },

    async escolherClasse(nome) {
      P.classe = nome; P.areaId = '';
      await carregarClasseActual();
      desenhar();
    },

    async mudarRegime(regime) {
      try {
        await pedir(API_CLASSES, json('PUT', { regime }));
        P.classe = ''; P.areaId = '';
        await recarregar();
      } catch (e) { erro(e); }
    },

    async adicionarClasse(ev) {
      ev.preventDefault();
      const nome = ($('pcNovaClasse') || {}).value;
      if (!nome) return;
      const tem = ($('pcNovaClasseExame') || {}).value === 'sim';
      try {
        await pedir(API_CLASSES, json('PUT', { nome, tem_exame: tem }));
        P.classe = nome;
        aviso(nome + ' cadastrada. Agora cadastre as suas disciplinas (passo 2).', 'success');
        await recarregar();
      } catch (e) { erro(e); }
    },

    async mudarExame(i, valor) {
      const c = P.classes[i];
      if (!c) return;
      const tem = valor === 'sim';
      if (!tem && c.tem_exame && !confirm('A ' + c.nome + ' passa a SEM exame: as disciplinas dela marcadas com exame deixam de ter exame. Continuar?')) {
        desenharClasses(); return;
      }
      try {
        await pedir(API_CLASSES, json('PUT', { nome: c.nome, tem_exame: tem }));
        aviso('Regime de exame da ' + c.nome + ' actualizado.', 'success');
        await recarregar();
      } catch (e) { erro(e); desenharClasses(); }
    },

    async abrirClasse(i) {
      const c = P.classes[i];
      if (!c) return;
      P.classe = c.nome; P.areaId = '';
      await carregarClasseActual();
      API.irPasso(2);
    },

    async removerClasse(i) {
      const c = P.classes[i];
      if (!c || !confirm('Remover ' + c.nome + ' do Plano Curricular?')) return;
      try {
        await pedir(API_CLASSES, json('PUT', { remover_nome: c.nome }));
        aviso(c.nome + ' removida.', 'success');
        await recarregar();
      } catch (e) { erro(e); }
    },

    // ---- disciplinas
    sugerirCodigo() {
      if (P.codigoManual || ($('pcDiscId') || {}).value) return;
      const num = (String(P.classe).match(/\d+/) || [''])[0];
      const cod = $('pcDiscCodigo');
      if (!cod) return;
      // Disciplinas diferentes têm códigos diferentes: 1.ª palavra (3 letras) + iniciais das restantes
      // (Matemática Letras → MATL11; Matemática Ciências → MATC11; Matemática → MAT11).
      const palavras = normTxt(($('pcDiscNome') || {}).value).split(/[^a-z]+/)
        .filter((p) => p && !['de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o'].includes(p));
      if (!palavras.length) { cod.value = ''; return; }
      const iniciais = palavras.slice(1).map((p) => p[0]).join('');
      const usados = new Set([...(P.dados && P.dados.disciplinas || []), ...(state.todasDisciplinas || [])]
        .map((d) => String(d.codigo || '').toUpperCase()).filter(Boolean));
      const montar = (n) => (palavras[0].slice(0, n) + iniciais).toUpperCase() + num;
      let sug = montar(3);
      // Se já existir, usa mais letras da 1.ª palavra e, em último caso, um sufixo numérico.
      for (let n = 4; usados.has(sug) && n <= palavras[0].length; n++) sug = montar(n);
      for (let k = 2; usados.has(sug); k++) sug = montar(3) + '-' + k;
      cod.value = sug;
    },

    async guardarDisciplina(ev) {
      ev.preventDefault();
      if (!P.classe) return aviso('Escolha primeiro a Classe / Nível.', 'warning');
      const id = ($('pcDiscId') || {}).value;
      const corpo = {
        codigo: $('pcDiscCodigo').value.trim().toUpperCase(),
        carga_horaria: parseInt($('pcDiscCarga').value, 10) || 1
      };
      if (!id) {
        // Nova disciplina da classe: tem de ser escolhida do catálogo "Todas Disciplinas de Ensino".
        const nome = $('pcDiscNome').value.trim().toLocaleLowerCase();
        const item = P.catalogo.find((c) => c.nome.toLocaleLowerCase() === nome);
        if (!item) {
          aviso('Escolha uma disciplina da lista. Se ainda não existe, cadastre-a primeiro em "Todas Disciplinas de Ensino".', 'warning');
          return;
        }
        if (((P.dados && P.dados.disciplinas) || []).some((d) => d.catalogo === item.id)) {
          aviso('"' + item.nome + '" já está nesta classe.', 'warning');
          return;
        }
        corpo.catalogo = item.id;
        corpo.classe = P.classe;
        corpo.ano_letivo = String(anoActivo());
      }
      try {
        if (id) await pedir('/api/v1/disciplinas/' + id + '/', json('PATCH', corpo));
        else await pedir('/api/v1/disciplinas/', json('POST', corpo));
        aviso(id ? 'Disciplina actualizada.' : 'Disciplina cadastrada.', 'success');
        API.cancelarEdicaoDisciplina();
        await carregarCatalogo();
        await carregarClasseActual();
        await sincronizarGlobais();
        desenhar();
        const n = $('pcDiscNome'); if (n) n.focus();
      } catch (e) { erro(e); }
    },

    editarDisciplina(id) {
      const d = ((P.dados && P.dados.disciplinas) || []).find((x) => x.id === id);
      if (!d) return;
      $('pcDiscId').value = d.id; $('pcDiscNome').value = d.nome; $('pcDiscCodigo').value = d.codigo; $('pcDiscCarga').value = d.carga_horaria;
      $('pcDiscNome').readOnly = true; // o nome altera-se em "Todas Disciplinas de Ensino"
      $('pcDiscBtn').innerHTML = '<i class="bi bi-check2 me-1"></i>Guardar';
      $('pcDiscCancelar').classList.remove('d-none');
      $('pcDiscNome').focus();
    },

    cancelarEdicaoDisciplina() {
      ['pcDiscId', 'pcDiscNome', 'pcDiscCodigo'].forEach((i) => { const el = $(i); if (el) el.value = ''; });
      const c = $('pcDiscCarga'); if (c) c.value = 4;
      const nm = $('pcDiscNome'); if (nm) nm.readOnly = false;
      P.codigoManual = false;
      const b = $('pcDiscBtn'); if (b) b.innerHTML = '<i class="bi bi-plus-lg me-1"></i>Cadastrar';
      const x = $('pcDiscCancelar'); if (x) x.classList.add('d-none');
    },

    async eliminarDisciplina(id) {
      const d = ((P.dados && P.dados.disciplinas) || []).find((x) => x.id === id);
      if (!d || !confirm('Eliminar a disciplina "' + d.nome + '"? Será retirada também das áreas.')) return;
      try {
        await pedir('/api/v1/disciplinas/' + id + '/', { method: 'DELETE' });
        aviso('Disciplina eliminada.', 'success');
        await carregarClasseActual();
        await sincronizarGlobais();
        desenhar();
      } catch (e) { erro(e); }
    },

    desenharDisciplinas, desenharVinculos, desenharCatalogo,

    // ---- Todas Disciplinas de Ensino (catálogo)
    async guardarCatalogo(ev) {
      ev.preventDefault();
      const id = ($('pcCatId') || {}).value;
      const nome = $('pcCatNome').value.trim();
      try {
        if (id) await pedir(API_PLANO + '/catalogo/' + id + '/', json('PATCH', { nome }));
        else await pedir(API_PLANO + '/catalogo/', json('POST', { nome }));
        aviso(id ? 'Disciplina actualizada.' : 'Disciplina cadastrada.', 'success');
        API.cancelarEdicaoCatalogo();
        await carregarCatalogo();
        await carregarClasseActual();
        await sincronizarGlobais();
        desenhar();
        const n = $('pcCatNome'); if (n) n.focus();
      } catch (e) { erro(e); }
    },

    async guardarCatalogoVarias() {
      const nomes = ($('pcCatVarias').value || '').split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
      if (!nomes.length) return aviso('Escreva uma disciplina por linha.', 'warning');
      try {
        const r = await pedir(API_PLANO + '/catalogo/', json('POST', { nomes }));
        const rep = (r.repetidas || []).length;
        aviso((r.data || []).length + ' disciplina(s) cadastrada(s)' + (rep ? '; ' + rep + ' já existia(m).' : '.'), 'success');
        $('pcCatVarias').value = '';
        await carregarCatalogo();
        desenhar();
      } catch (e) { erro(e); }
    },

    editarCatalogo(id) {
      const c = P.catalogo.find((x) => x.id === id);
      if (!c) return;
      $('pcCatId').value = c.id; $('pcCatNome').value = c.nome;
      $('pcCatBtn').innerHTML = '<i class="bi bi-check2 me-1"></i>Guardar';
      $('pcCatCancelar').classList.remove('d-none');
      $('pcCatNome').focus();
    },

    cancelarEdicaoCatalogo() {
      const i = $('pcCatId'); if (i) i.value = '';
      const n = $('pcCatNome'); if (n) n.value = '';
      const b = $('pcCatBtn'); if (b) b.innerHTML = '<i class="bi bi-plus-lg me-1"></i>Cadastrar';
      const x = $('pcCatCancelar'); if (x) x.classList.add('d-none');
    },

    async eliminarCatalogo(id) {
      const c = P.catalogo.find((x) => x.id === id);
      if (!c || !confirm('Eliminar "' + c.nome + '" de Todas Disciplinas de Ensino?')) return;
      try {
        await pedir(API_PLANO + '/catalogo/' + id + '/', { method: 'DELETE' });
        aviso('Disciplina eliminada.', 'success');
        await carregarCatalogo();
        desenhar();
      } catch (e) { erro(e); }
    },

    // ---- áreas / secções
    async guardarArea(ev) {
      ev.preventDefault();
      if (!P.classe) return aviso('Escolha primeiro a Classe / Nível.', 'warning');
      const id = ($('pcAreaId') || {}).value;
      const nome = $('pcAreaNome').value.trim();
      try {
        if (id) await pedir(API_PLANO + '/areas/' + id + '/', json('PATCH', { nome }));
        else await pedir(API_PLANO + '/areas/', json('POST', { classe: P.classe, nome }));
        aviso(id ? 'Área / Secção actualizada.' : 'Área / Secção cadastrada. Agora escolha as suas disciplinas (passo 4).', 'success');
        API.cancelarEdicaoArea();
        await carregarClasseActual();
        await sincronizarGlobais();
        desenhar();
      } catch (e) { erro(e); }
    },

    editarArea(id) {
      const a = ((P.dados && P.dados.areas) || []).find((x) => x.id === id);
      if (!a) return;
      $('pcAreaId').value = a.id; $('pcAreaNome').value = a.nome;
      $('pcAreaBtn').innerHTML = '<i class="bi bi-check2 me-1"></i>Guardar';
      $('pcAreaCancelar').classList.remove('d-none');
      $('pcAreaNome').focus();
    },

    cancelarEdicaoArea() {
      const i = $('pcAreaId'); if (i) i.value = '';
      const n = $('pcAreaNome'); if (n) n.value = '';
      const b = $('pcAreaBtn'); if (b) b.innerHTML = '<i class="bi bi-plus-lg me-1"></i>Cadastrar';
      const x = $('pcAreaCancelar'); if (x) x.classList.add('d-none');
    },

    async eliminarArea(id) {
      const a = ((P.dados && P.dados.areas) || []).find((x) => x.id === id);
      if (!a || !confirm('Eliminar a Área / Secção "' + a.nome + '"?')) return;
      try {
        await pedir(API_PLANO + '/areas/' + id + '/', { method: 'DELETE' });
        aviso('Área / Secção eliminada.', 'success');
        await carregarClasseActual();
        await sincronizarGlobais();
        desenhar();
      } catch (e) { erro(e); }
    },

    abrirArea(id) { P.areaId = id; carregarMarcas(); API.irPasso(4); },

    // ---- disciplinas de cada área
    escolherArea(id) { P.areaId = id; carregarMarcas(); desenharVinculos(); },

    marcar(id, marcado) {
      const m = P.marcas[id] || { marcado: false, exame: false };
      m.marcado = !!marcado;
      if (!marcado) m.exame = false;
      P.marcas[id] = m;
      desenharVinculos();
    },

    marcarExame(id, valor) {
      const m = P.marcas[id];
      if (m) m.exame = valor === 'sim';
      desenharVinculos();
    },

    marcarTodasVinculos(marcado) {
      const q = normTxt(($('pcVincBusca') || {}).value);
      ((P.dados && P.dados.disciplinas) || [])
        .filter((d) => !q || normTxt(d.nome).includes(q) || normTxt(d.codigo).includes(q))
        .forEach((d) => {
          const m = P.marcas[d.id] || { marcado: false, exame: false };
          m.marcado = !!marcado;
          if (!marcado) m.exame = false;
          P.marcas[d.id] = m;
        });
      desenharVinculos();
    },

    async guardarVinculos() {
      const a = areaActual();
      if (!a) return;
      const disciplinas = Object.keys(P.marcas)
        .filter((id) => P.marcas[id].marcado)
        .map((id) => ({ disciplina: id, tem_exame: !!(P.dados.tem_exame && P.marcas[id].exame) }));
      try {
        await pedir(API_PLANO + '/areas/' + a.id + '/disciplinas/', json('PUT', { disciplinas }));
        aviso('Disciplinas da área "' + a.nome + '" guardadas.', 'success');
        await carregarClasseActual();
        await sincronizarGlobais();
        desenhar();
      } catch (e) { erro(e); }
    }
  };

  window.PlanoCurricular = API;

  // Chamado pelo router ao concluir "Buscar" (ano lectivo escolhido) e ao abrir a página já com ano.
  window.carregarPlanoCurricular = () => API.init();
  window.inicializarModulo_plano_curricular = function () {
    if (typeof state !== 'undefined' && state.anosPorView && state.anosPorView['plano-curricular']) API.init();
  };

  document.addEventListener('input', (ev) => {
    if (ev.target && ev.target.id === 'pcDiscCodigo') P.codigoManual = !!ev.target.value;
  });
})();
