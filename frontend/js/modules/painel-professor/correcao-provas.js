// =====================================================================
// SIGE - CORRECÇÃO ASSISTIDA DE PROVAS FÍSICAS (Painel do Professor)
// Cascata Classe → Secção/Área → Turma → Disciplina → Trimestre → Prova (altura constante para qualquer n).
// API: /api/v1/notas/provas-fisicas/  ·  /api/v1/professores/minhas-turmas/
// A nota só chega à caderneta quando o professor confirma em "Lançar corrigidas na caderneta".
// =====================================================================
(function () {
  'use strict';
  var API = '/api/v1/notas/provas-fisicas/';
  var NOTA_MINIMA = 9.5; // abaixo disto a nota é negativa e vai a vermelho
  var alocs = [];
  var prova = null;       // detalhe da prova aberta (com alunos)
  var idxAluno = 0;
  var urlsImagens = [];   // object URLs a libertar ao mudar de aluno
  var ligado = false;

  function $(id) { return document.getElementById(id); }
  function st() { return (typeof state !== 'undefined' && state) || window.state || {}; }
  function token() { try { return st().token || sessionStorage.getItem('sige_token') || localStorage.getItem('sige_token') || ''; } catch (_) { return ''; } }
  function tenant() {
    try {
      var s = st(), sel = null;
      try { sel = localStorage.getItem('sige_selected_tenant'); } catch (_) { /* sem storage */ }
      var superadmin = s.user && s.user.role === 'SUPERADMIN';
      return (superadmin || !s.user ? sel : null) || (s.tenant && s.tenant.id) || (s.user && s.user.escola_id) || '';
    } catch (_) { return ''; }
  }
  function cab(extra) {
    var h = Object.assign({}, extra || {});
    var t = token(); if (t) h['Authorization'] = 'Bearer ' + t;
    var tn = tenant(); if (tn) h['X-Tenant-ID'] = tn;
    return h;
  }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML.replace(/"/g, '&quot;'); }
  function toast(msg, tipo) { if (typeof window.mostrarToast === 'function') window.mostrarToast(msg, tipo || 'info'); else alert(msg); }
  function ano() { return (st().anosPorView && st().anosPorView['correcao-provas']) || ($('correcaoProvasAnoSelect') || {}).value || ''; }
  function fmt(v) { return String(Math.round(v * 100) / 100).replace('.', ','); }
  function num(v) { if (v === '' || v == null) return null; var n = parseFloat(String(v).replace(',', '.')); return isFinite(n) ? n : NaN; }

  async function chamar(url, opcoes) {
    var r = await fetch(url, Object.assign({ headers: cab() }, opcoes || {}));
    var j = null; try { j = await r.json(); } catch (_) { /* resposta sem corpo JSON */ }
    return { ok: r.ok, status: r.status, json: j || {} };
  }
  function json(metodo, corpo) { return { method: metodo, headers: cab({ 'Content-Type': 'application/json' }), body: JSON.stringify(corpo) }; }
  function msg(res, padrao) { return (res.json && (res.json.message || res.json.detail)) || padrao || 'Não foi possível concluir o pedido.'; }

  // ---------- Cascata ----------
  function grau(a) { return (a.turma && a.turma.grau_ano) || a.turma_grau || ''; }
  function area(a) { return (a.turma && a.turma.area) || a.turma_area || ''; }
  function turmaId(a) { return (a.turma && a.turma.id) || a.turma || ''; }
  function turmaNome(a) { return (a.turma && a.turma.nome) || a.turma_nome || ''; }
  function discId(a) { return (a.disciplina && a.disciplina.id) || a.disciplina || ''; }
  function discNome(a) { return a.disciplina_nome || (a.disciplina && a.disciplina.nome) || ''; }
  function unicos(lista) { var v = []; lista.forEach(function (x) { if (x && v.indexOf(x) < 0) v.push(x); }); return v.sort(); }
  function opcoes(sel, rotulo, itens) {
    var ant = sel.value;
    sel.innerHTML = '<option value="">' + esc(rotulo) + '</option>' + itens.map(function (i) {
      return '<option value="' + esc(i.v) + '">' + esc(i.t) + '</option>';
    }).join('');
    if (ant && itens.some(function (i) { return i.v === ant; })) sel.value = ant;
  }
  function daClasse() { var c = $('cpClasse').value; return alocs.filter(function (a) { return !c || grau(a) === c; }); }
  function daArea() { var ar = $('cpArea').value; return daClasse().filter(function (a) { return !ar || area(a) === ar; }); }
  function daTurma() { var t = $('cpTurma').value; return daArea().filter(function (a) { return a.turma && turmaId(a) === t || (!a.turma && false); }); }

  function preencherClasses() {
    opcoes($('cpClasse'), '-- Classe --', unicos(alocs.map(grau)).map(function (g) { return { v: g, t: g }; }));
    aoMudarClasse();
  }
  function aoMudarClasse() {
    opcoes($('cpArea'), '-- Secção / Área --', unicos(daClasse().map(area)).map(function (g) { return { v: g, t: g }; }));
    aoMudarArea();
  }
  function aoMudarArea() {
    var vistos = {}, itens = [];
    daArea().forEach(function (a) {
      var id = turmaId(a); if (!id || vistos[id]) return; vistos[id] = 1;
      itens.push({ v: id, t: turmaNome(a) });
    });
    opcoes($('cpTurma'), '-- Turma --', itens);
    aoMudarTurma();
  }
  function aoMudarTurma() {
    var t = $('cpTurma').value, vistos = {}, itens = [];
    alocs.filter(function (a) { return t && turmaId(a) === t; }).forEach(function (a) {
      var id = discId(a); if (!id || vistos[id]) return; vistos[id] = 1;
      itens.push({ v: id, t: discNome(a) });
    });
    opcoes($('cpDisciplina'), '-- Disciplina --', itens);
    carregarProvas();
  }

  function estadoVazio(texto) {
    $('cpVazio').classList.remove('d-none');
    $('cpVazioTexto').textContent = texto;
    $('cpAreaCorreccao').classList.add('d-none');
    $('cpBtnEliminar').classList.add('d-none');
    estadoCartaoAuto();
  }
  // Passo 2 (carregar as provas dos alunos) está sempre visível; só fica activo com uma prova de escolha múltipla aberta.
  function estadoCartaoAuto() {
    var av = $('cpAutoAviso');
    if (!av) return;
    var ok = !!(prova && prova.tipo === 'MULTIPLA_ESCOLHA' && prova.alunos && prova.alunos.length);
    $('cpAutoFicheiros').disabled = false; $('cpAutoLer').disabled = false;
    var formAberto = !$('cpCartaoNova').classList.contains('d-none');
    if (formAberto && gabaritoNoFormulario()) {
      var nf = parseInt($('cpNPerg').value, 10) || 0;
      av.className = 'alert alert-success py-2 small mb-2';
      av.innerHTML = '<i class="bi bi-check-circle me-1"></i>As folhas serão corrigidas com o <strong>gabarito do Passo 1</strong> (' + nf + ' perguntas, ' +
        (parseInt($('cpNAlt').value, 10) || 4) + ' alternativas): a prova é criada ao iniciar (com a turma, disciplina e trimestre escolhidos acima)' +
        (prova ? '; a prova «' + esc(prova.titulo) + '» que está aberta não é usada' : '') + '.';
    } else if (ok) {
      av.className = 'alert alert-success py-2 small mb-2';
      av.innerHTML = '<i class="bi bi-check-circle me-1"></i>As folhas serão corrigidas com o gabarito da prova <strong>' + esc(prova.titulo) + '</strong> (' +
        prova.perguntas.filter(function (p) { return p.tipo === 'MC'; }).length + ' perguntas, ' + prova.n_alternativas + ' alternativas' +
        ((prova.versoes || []).length ? ', versões ' + esc(prova.versoes.join('/')) : '') + ') · ' + esc(prova.disciplina_nome) + ', ' + esc(prova.turma_nome) + '.';
    } else if (prova && prova.tipo !== 'MULTIPLA_ESCOLHA') {
      av.className = 'alert alert-warning py-2 small mb-2';
      av.textContent = 'A prova seleccionada é discursiva: a leitura automática só serve para provas de escolha múltipla com Folha de Resposta. Use a correcção manual abaixo.';
    } else if (prova) {
      av.className = 'alert alert-warning py-2 small mb-2';
      av.textContent = 'Esta turma não tem alunos activos.';
    } else if (gabaritoNoFormulario()) {
      av.className = 'alert alert-success py-2 small mb-2';
      av.innerHTML = '<i class="bi bi-check-circle me-1"></i>Gabarito importado no Passo 1 (' + (parseInt($('cpNPerg').value, 10) || 0) +
        ' perguntas). Escolha as folhas e carregue em «Ler folhas»: a prova é criada com este gabarito (precisa da turma, disciplina e trimestre escolhidos acima).';
    } else {
      av.className = 'alert alert-secondary py-2 small mb-2';
      av.textContent = 'Pode já escolher as folhas dos alunos. Para as ler, escolha a turma, a disciplina, o trimestre e a prova, ou crie a prova no Passo 1 com o gabarito importado.';
    }
  }

  async function carregarAlocacoes() {
    try {
      var res = await chamar('/api/v1/professores/minhas-turmas/?ano=' + encodeURIComponent(ano()));
      alocs = res.ok && Array.isArray(res.json.data) ? res.json.data : [];
    } catch (_) { alocs = []; toast('Falha de ligação ao carregar as suas turmas.', 'danger'); }
    preencherClasses();
    if (!alocs.length) estadoVazio('Não tem turmas e disciplinas atribuídas neste ano lectivo.');
  }

  async function carregarProvas(abrirId) {
    var t = $('cpTurma').value, d = $('cpDisciplina').value, p = $('cpPeriodo').value;
    prova = null;
    opcoes($('cpProva'), '-- Prova --', []);
    if (!t || !d || !p) { estadoVazio('Escolha a turma, a disciplina e o trimestre para ver as provas, ou crie uma nova prova.'); return; }
    var res = await chamar(API + '?turma_id=' + encodeURIComponent(t) + '&disciplina_id=' + encodeURIComponent(d) + '&periodo=' + encodeURIComponent(p));
    if (!res.ok) { toast(msg(res), 'danger'); estadoVazio('Não foi possível carregar as provas.'); return; }
    var lista = res.json.data || [];
    opcoes($('cpProva'), lista.length ? '-- Prova --' : '-- Sem provas --', lista.map(function (x) { return { v: x.id, t: x.titulo }; }));
    if (!lista.length) { estadoVazio('Ainda não há provas para esta turma, disciplina e trimestre. Use "Nova prova" para criar a grelha de cotações.'); return; }
    if (abrirId) $('cpProva').value = abrirId;
    else if (lista.length === 1) $('cpProva').value = lista[0].id;
    if ($('cpProva').value) await abrirProva($('cpProva').value);
    else estadoVazio('Escolha a prova a corrigir.');
  }

  // ---------- Nova prova ----------
  function lerCotacoes() {
    return $('cpCotacoes').value.split(/[\s,;]+/).filter(Boolean).map(num);
  }
  function resumoCotacoes() {
    var c = lerCotacoes(), el = $('cpResumoCotacoes');
    if (!c.length) { el.textContent = 'Indique as cotações para ver o total.'; return; }
    if (c.some(function (x) { return !(x > 0 && x <= 20); })) { el.textContent = 'Cada cotação deve estar entre 0 (exclusivo) e 20.'; return; }
    var tot = c.reduce(function (s, x) { return s + x; }, 0);
    el.textContent = c.length + ' pergunta(s) · total ' + fmt(tot) + (Math.abs(tot - 20) > 0.001 ? ' (a nota será reescalada para 0–20)' : '');
  }
  // Escolha múltipla: os mesmos dados da Folha de Resposta gerada (tipo, perguntas, alternativas, versões, chave)
  function listaVersoes() {
    return ($('cpVersoes').value || '').toUpperCase().split(/[\s,;]+/).filter(Boolean).slice(0, 6);
  }
  function desenharGabaritos() {
    var vs = listaVersoes(), box = $('cpGabaritos');
    var guardados = {};
    box.querySelectorAll('input[data-v]').forEach(function (i) { guardados[i.getAttribute('data-v')] = i.value; });
    var alvo = vs.length ? vs : [''];
    box.innerHTML = '<div class="row g-2">' + alvo.map(function (v) {
      return '<div class="col-12 col-md-6"><label class="form-label small mb-1">Chave de correcção' + (v ? ' da versão ' + esc(v) : '') + ' (uma letra por pergunta)</label>' +
        '<input data-v="' + esc(v) + '" class="form-control form-control-sm font-monospace cp-gab" autocomplete="off" spellcheck="false" placeholder="Ex.: ABCDDACB" value="' + esc(guardados[v] || '') + '"></div>';
    }).join('') + '</div>';
    desenharFolhaVisual();
  }
  // Folha de Resposta do sistema (visual): clicar na alternativa certa de cada pergunta preenche a chave de correcção
  function chaveDaFolha(v) {
    var inp = document.querySelector('#cpGabaritos .cp-gab[data-v="' + v + '"]');
    return { inp: inp, texto: ((inp && inp.value) || '').replace(/\s+/g, '').toUpperCase() };
  }
  function desenharFolhaVisual() {
    var box = $('cpFolhaVisual'); if (!box) return;
    var n = parseInt($('cpNPerg').value, 10), nAlt = Math.max(2, Math.min(6, parseInt($('cpNAlt').value, 10) || 4));
    var cont = $('cpFolhaContagem'), sel = $('cpFolhaVersao');
    if (!(n > 0 && n <= 100)) { box.innerHTML = '<div class="small text-muted">Indique o nº de perguntas (1–100) para aparecer a folha de resposta.</div>'; cont.textContent = ''; sel.classList.add('d-none'); return; }
    var vs = listaVersoes(), v = '';
    if (vs.length) {
      var antes = sel.value;
      sel.innerHTML = vs.map(function (x) { return '<option value="' + esc(x) + '">Versão ' + esc(x) + '</option>'; }).join('');
      sel.value = vs.indexOf(antes) >= 0 ? antes : vs[0]; v = sel.value; sel.classList.remove('d-none');
    } else sel.classList.add('d-none');
    var ch = chaveDaFolha(v).texto, letras = 'ABCDEF'.slice(0, nAlt);
    var cols = n <= 20 ? 1 : n <= 60 ? 2 : 3, por = Math.ceil(n / cols), marcadas = 0, html = '';
    box.style.gridTemplateColumns = 'repeat(' + cols + ', minmax(0, 1fr))';
    for (var c = 0; c < cols; c++) {
      html += '<div class="cp-fv-col"><div class="cp-fv-cab"><span style="min-width:2rem"></span>' + letras.split('').map(function (l) { return '<span style="width:2.6rem;text-align:center">' + l + '</span>'; }).join('') + '</div>';
      for (var k = c * por; k < Math.min(n, (c + 1) * por); k++) {
        var cert = ch.charAt(k);
        if (letras.indexOf(cert) >= 0) marcadas++;
        html += '<div class="cp-fv-lin' + ((k + 1) % 5 === 0 ? ' cp-fv-g' : '') + '"><span class="cp-fv-num">' + (k + 1) + '</span>' +
          letras.split('').map(function (l) { return '<button type="button" class="cp-fv-bolha' + (cert === l ? ' cp-fv-certa' : '') + '" data-k="' + k + '" data-l="' + l + '" aria-label="Pergunta ' + (k + 1) + ', alternativa ' + l + '" aria-pressed="' + (cert === l) + '">' + l + '</button>'; }).join('') + '</div>';
      }
      html += '</div>';
    }
    box.innerHTML = html;
    cont.className = 'small ms-auto ' + (marcadas === n ? 'text-success fw-semibold' : 'text-muted');
    cont.textContent = marcadas + ' de ' + n + ' respostas certas indicadas';
  }
  function aoClicarFolhaVisual(ev) {
    var b = ev.target.closest && ev.target.closest('.cp-fv-bolha'); if (!b) return;
    var n = parseInt($('cpNPerg').value, 10); if (!(n > 0)) return;
    var vs = listaVersoes(), v = vs.length ? ($('cpFolhaVersao').value || vs[0]) : '';
    var o = chaveDaFolha(v); if (!o.inp) { desenharGabaritos(); o = chaveDaFolha(v); if (!o.inp) return; }
    var k = parseInt(b.getAttribute('data-k'), 10), l = b.getAttribute('data-l');
    var arr = []; for (var i = 0; i < n; i++) arr.push(o.texto.charAt(i) || '?');
    arr[k] = arr[k] === l ? '?' : l;
    o.inp.value = arr.join('');
    desenharFolhaVisual(); estadoCartaoAuto();
  }
  // ---------- Gabaritos guardados (reutilizar sem recomeçar) ----------
  var guardados = [];
  async function carregarGuardados(seleccionar) {
    var sel = $('cpGabGuardados'); if (!sel) return;
    var res = await chamar(API + 'gabaritos-guardados/');
    guardados = (res.ok && res.json && res.json.data) || [];
    sel.innerHTML = '<option value="">' + (guardados.length ? '-- escolha --' : 'Ainda não guardou nenhum') + '</option>' +
      guardados.map(function (g) { return '<option value="' + esc(g.id) + '">' + esc(g.nome) + ' · ' + g.n_perguntas + ' perguntas</option>'; }).join('');
    if (seleccionar) sel.value = seleccionar;
  }
  function usarGuardado() {
    var id = $('cpGabGuardados').value, g = guardados.filter(function (x) { return x.id === id; })[0];
    var msg_ = $('cpGabGuardadoMsg');
    if (!g) { msg_.className = 'small mt-1 text-warning-emphasis'; msg_.textContent = 'Escolha um gabarito guardado.'; return; }
    $('cpTipo').value = 'MULTIPLA_ESCOLHA'; alternarTipoNova();
    $('cpNPerg').value = g.n_perguntas; $('cpNAlt').value = g.n_alternativas;
    $('cpVersoes').value = (g.versoes || []).join(' ');
    desenharGabaritos();
    Object.keys(g.gabaritos || {}).forEach(function (v) {
      var el = document.querySelector('#cpGabaritos .cp-gab[data-v="' + (v === '-' ? '' : v) + '"]');
      if (el) el.value = g.gabaritos[v];
    });
    $('cpGabNome').value = g.nome;
    desenharFolhaVisual(); estadoCartaoAuto();
    msg_.className = 'small mt-1 text-success';
    msg_.textContent = 'Gabarito «' + g.nome + '» carregado (' + g.n_perguntas + ' perguntas). Escolha a turma, a disciplina e o trimestre e crie a prova, ou carregue as folhas e inicie a correcção.';
  }
  async function guardarGabarito() {
    var msg_ = $('cpGabGuardadoMsg'), nome = ($('cpGabNome').value || '').trim();
    if (!nome) { msg_.className = 'small mt-1 text-warning-emphasis'; msg_.textContent = 'Dê um nome ao gabarito para o guardar.'; return; }
    var vs = listaVersoes(), gabs = {};
    document.querySelectorAll('#cpGabaritos .cp-gab').forEach(function (i) { gabs[i.getAttribute('data-v') || '-'] = i.value; });
    var res = await chamar(API + 'gabaritos-guardados/', json('POST', {
      nome: nome, n_perguntas: $('cpNPerg').value, n_alternativas: $('cpNAlt').value, versoes: vs, gabaritos: gabs }));
    if (!res.ok) { msg_.className = 'small mt-1 text-danger'; msg_.textContent = msg(res); return; }
    msg_.className = 'small mt-1 text-success'; msg_.textContent = (res.json.message || 'Gabarito guardado.') + ' Fica disponível para reutilizar.';
    await carregarGuardados(res.json.data.id);
  }
  // Descarrega o gabarito em PDF: o do formulário (guarda-o primeiro no sistema, com o nome indicado ou um automático)
  // ou, se o formulário estiver vazio, o gabarito guardado que está escolhido na lista.
  async function descarregarGabaritoPdf() {
    var msg_ = $('cpGabGuardadoMsg'), id = '';
    var temChave = false;
    document.querySelectorAll('#cpGabaritos .cp-gab').forEach(function (i) { if (/[A-Fa-f]/.test(i.value || '')) temChave = true; });
    if (temChave) {
      var nome = ($('cpGabNome').value || '').trim();
      if (!nome) {
        nome = 'Gabarito ' + (parseInt($('cpNPerg').value, 10) || 0) + ' perguntas · ' + new Date().toLocaleDateString('pt-PT');
        $('cpGabNome').value = nome;
      }
      var vs = listaVersoes(), gabs = {};
      document.querySelectorAll('#cpGabaritos .cp-gab').forEach(function (i) { gabs[i.getAttribute('data-v') || '-'] = i.value; });
      var res = await chamar(API + 'gabaritos-guardados/', json('POST', {
        nome: nome, n_perguntas: $('cpNPerg').value, n_alternativas: $('cpNAlt').value, versoes: vs, gabaritos: gabs }));
      if (!res.ok) { msg_.className = 'small mt-1 text-danger'; msg_.textContent = msg(res); return; }
      id = res.json.data.id;
      await carregarGuardados(id);
    } else {
      id = $('cpGabGuardados').value;
    }
    if (!id) { msg_.className = 'small mt-1 text-warning-emphasis'; msg_.textContent = 'Indique o gabarito (folha de resposta, chave ou ficheiro) ou escolha um gabarito guardado.'; return; }
    var g = guardados.filter(function (x) { return x.id === id; })[0];
    msg_.className = 'small mt-1 text-success'; msg_.textContent = 'Gabarito guardado no sistema. A descarregar o PDF…';
    await downloadFicheiroBinario(API + 'gabaritos-guardados/' + encodeURIComponent(id) + '/pdf/',
      ('Gabarito - ' + (g ? g.nome : 'guiao de correccao')).replace(/[\\/:*?"<>|]+/g, ' ') + '.pdf');
  }
  async function eliminarGuardado() {
    var id = $('cpGabGuardados').value, g = guardados.filter(function (x) { return x.id === id; })[0];
    if (!g) return;
    if (!confirm('Eliminar o gabarito guardado «' + g.nome + '»? (as provas já criadas não mudam)')) return;
    var res = await chamar(API + 'gabaritos-guardados/' + encodeURIComponent(id) + '/', { method: 'DELETE' });
    var msg_ = $('cpGabGuardadoMsg');
    msg_.className = 'small mt-1 ' + (res.ok ? 'text-success' : 'text-danger');
    msg_.textContent = res.ok ? 'Gabarito eliminado.' : msg(res);
    await carregarGuardados();
  }
  function alternarTipoNova() {
    var mc = $('cpTipo').value === 'MULTIPLA_ESCOLHA';
    document.querySelectorAll('#cpCartaoNova .cp-bloco-mc').forEach(function (e) { e.classList.toggle('d-none', !mc); });
    document.querySelectorAll('#cpCartaoNova .cp-bloco-disc').forEach(function (e) { e.classList.toggle('d-none', mc); });
    if (mc) desenharGabaritos();
  }
  function corpoEscolhaMultipla() {
    var vs = listaVersoes(), folha = {
      tipo_avaliacao: $('cpTipoAval').value, n_perguntas: $('cpNPerg').value, n_alternativas: $('cpNAlt').value,
      cotacao_pergunta: $('cpCotPerg').value.trim().replace(',', '.'), versoes: vs.join(' ')
    };
    var gabs = {};
    document.querySelectorAll('#cpGabaritos .cp-gab').forEach(function (i) { gabs[i.getAttribute('data-v') || '-'] = i.value; });
    if (vs.length) folha.gabaritos = gabs; else folha.gabarito = gabs['-'] || '';
    var nAb = parseInt($('cpNAbertas').value, 10) || 0;
    if (nAb > 0) folha.abertas = [{ rotulo: 'Perguntas abertas', n: nAb, cotacao: $('cpCotAbertas').value.trim().replace(',', '.') }];
    return folha;
  }
  // Há um gabarito (importado ou escrito) no formulário do Passo 1, mesmo sem a prova criada?
  function gabaritoNoFormulario() {
    var maior = 0;
    document.querySelectorAll('#cpGabaritos .cp-gab').forEach(function (i) {
      var v = (i.value || '').replace(/\s+/g, '');
      if (/[A-Fa-f]/.test(v) && v.length > maior) maior = v.length;
    });
    if (!maior) return false;
    // chave escrita à mão sem indicar o nº de perguntas: o nº é o tamanho da chave
    if (!(parseInt($('cpNPerg').value, 10) > 0)) $('cpNPerg').value = maior;
    if ($('cpTipo').value !== 'MULTIPLA_ESCOLHA') { $('cpTipo').value = 'MULTIPLA_ESCOLHA'; alternarTipoNova(); }
    return true;
  }
  async function criarProva(automatica) {
    var mc = $('cpTipo').value === 'MULTIPLA_ESCOLHA';
    var corpo = {
      turma_id: $('cpTurma').value, disciplina_id: $('cpDisciplina').value, periodo: $('cpPeriodo').value,
      titulo: $('cpTitulo').value.trim(), tipo: $('cpTipo').value
    };
    if (automatica === true && !corpo.titulo) corpo.titulo = 'Teste ' + new Date().toLocaleDateString('pt-PT');
    if (mc) corpo.folha = corpoEscolhaMultipla();
    else { corpo.instrumento = $('cpInstrumento').value; corpo.perguntas = lerCotacoes().map(function (x) { return { cotacao: x }; }); }
    if (!corpo.turma_id || !corpo.disciplina_id || !corpo.periodo) { toast('Escolha primeiro a turma, a disciplina e o trimestre.', 'warning'); return false; }
    if (mc) {   // a chave tem de ter a alternativa certa de todas as perguntas (use a folha de resposta acima)
      var nTot = parseInt($('cpNPerg').value, 10) || 0, semResp = [];
      document.querySelectorAll('#cpGabaritos .cp-gab').forEach(function (i) {
        var t = (i.value || '').replace(/\s+/g, ''), f = [];
        for (var q = 0; q < nTot; q++) if (!/[A-Fa-f]/.test(t.charAt(q))) f.push(q + 1);
        if (f.length > semResp.length) semResp = f;
      });
      if (semResp.length) {
        toast('Falta a resposta certa da(s) pergunta(s) ' + semResp.slice(0, 12).join(', ') + (semResp.length > 12 ? '…' : '') +
          ': clique na alternativa certa na folha de resposta do Passo 1.', 'warning'); return false;
      }
    }
    var res = await chamar(API, json('POST', corpo));
    if (!res.ok) { toast(msg(res), 'danger'); return false; }
    toast(automatica === true ? 'Prova criada com o gabarito importado.' : 'Prova criada com este gabarito. Passo 2: carregue as provas dos alunos.', 'success');
    if (mc) {   // tudo fica guardado: o gabarito desta prova guarda-se também na lista de gabaritos (para reutilizar/exportar)
      try {
        var fo = corpo.folha, gb = fo.gabaritos || { '-': fo.gabarito };
        await chamar(API + 'gabaritos-guardados/', json('POST', {
          nome: ((corpo.titulo || 'Gabarito') + ' · ' + new Date().toLocaleDateString('pt-PT')).slice(0, 120),
          n_perguntas: fo.n_perguntas, n_alternativas: fo.n_alternativas,
          versoes: String(fo.versoes || '').split(/\s+/).filter(Boolean), gabaritos: gb }));
        await carregarGuardados();
      } catch (_) { /* o gabarito da prova já está guardado na própria prova */ }
    }
    $('cpCartaoNova').classList.add('d-none');
    $('cpTitulo').value = ''; $('cpCotacoes').value = ''; $('cpNPerg').value = ''; $('cpVersoes').value = '';
    $('cpCotPerg').value = ''; $('cpNAbertas').value = '0'; $('cpCotAbertas').value = '';
    desenharGabaritos();
    await carregarProvas(res.json.data.id);
    if (automatica !== true && mc && prova && $('cpCartaoAuto').scrollIntoView) $('cpCartaoAuto').scrollIntoView({ behavior: 'smooth', block: 'start' });
    return true;
  }

  // ---------- Correcção ----------
  async function abrirProva(id) {
    var res = await chamar(API + encodeURIComponent(id) + '/');
    if (!res.ok) { toast(msg(res), 'danger'); estadoVazio('Não foi possível abrir a prova.'); return; }
    prova = res.json.data;
    $('cpVazio').classList.add('d-none');
    $('cpAreaCorreccao').classList.remove('d-none');
    $('cpBtnEliminar').classList.remove('d-none');
    $('cpCotTotal').textContent = fmt(prova.cotacao_total);
    if (loteProva && loteProva !== prova.id) { lote = []; loteProva = ''; revIdx = -1; $('cpAutoProgresso').textContent = ''; painelLote(); }
    await restaurarPendentes();
    estadoCartaoAuto();
    if (!prova.alunos.length) { estadoVazio('Esta turma não tem alunos activos.'); return; }
    preencherAlunos();
    mostrarAluno(Math.min(idxAluno, prova.alunos.length - 1));
    mostrarConcluido();
  }
  // Tudo fica guardado no sistema: ao abrir a prova voltam as folhas lidas que ainda não têm aluno atribuído
  async function restaurarPendentes() {
    if (!prova || prova.tipo !== 'MULTIPLA_ESCOLHA') return;
    var res = await chamar(API + encodeURIComponent(prova.id) + '/folhas-pendentes/');
    if (!res.ok || !res.json) return;
    loteProva = prova.id;
    (res.json.data || []).forEach(function (f) {
      if (lote.some(function (x) { return x.pendente_id === f.id; })) return;
      lote.push({ estado: 'pendente', origem: f.origem, pagina: f.pagina, aluno_id: '', versao: f.versao || '', pendente_id: f.id,
        respostas: (f.respostas || '').split(''), duvidas: f.duvidas || [], avisos: f.avisos || [], previa: '', imagem: '', resolvidas: {},
        corrigida: '', notaPrev: f.nota, acertos: f.acertos });
      f.duvidas.forEach(function (d) { lote[lote.length - 1].resolvidas[d.n] = d.sugerida || '-'; });
    });
    lote.filter(function (x) { return x.estado === 'pendente' && x.pendente_id; }).forEach(function (x) { x.avisos = (x.avisos || []); });
    painelLote();
  }
  // imagem guardada no servidor (pedido autenticado → endereço temporário do navegador)
  async function imagemGuardada(caminho) {
    var r = await fetch(API + caminho, { headers: cab() });
    if (!r.ok) throw new Error('indisponível');
    var u = URL.createObjectURL(await r.blob()); urlsImagens.push(u); return u;
  }
  function rotuloEstado(c) {
    if (!c) return 'por corrigir';
    return { RASCUNHO: 'rascunho', CORRIGIDA: 'corrigida', LANCADA: 'lançada' }[c.estado] || c.estado;
  }
  function preencherAlunos() {
    $('cpAluno').innerHTML = prova.alunos.map(function (a, i) {
      return '<option value="' + i + '">' + esc(a.nome) + ' — ' + rotuloEstado(a.correcao) + (a.correcao && a.correcao.estado !== 'RASCUNHO' ? ' (' + fmt(a.correcao.nota) + ')' : '') + '</option>';
    }).join('');
    var r = prova.resumo;
    $('cpCabProva').textContent = prova.titulo + ' · ' + prova.disciplina_nome + ' · ' + prova.turma_nome;
    $('cpResumoProva').textContent = r.corrigidas + '/' + r.total_alunos + ' corrigidas · ' + r.lancadas + ' lançadas';
  }
  function libertarImagens() { urlsImagens.forEach(function (u) { try { URL.revokeObjectURL(u); } catch (_) { /* nada */ } }); urlsImagens = []; }

  function mostrarAluno(i) {
    idxAluno = i;
    $('cpAluno').value = String(i);
    var a = prova.alunos[i], c = a.correcao;
    var pontos = (c && c.pontos) || [];
    var mc = prova.tipo === 'MULTIPLA_ESCOLHA';
    // Perguntas com pontos do professor: todas (discursiva) ou só as abertas (escolha múltipla)
    $('cpGrelha').innerHTML = prova.perguntas.map(function (p, k) {
      if (p.tipo === 'MC') return '';
      var v = pontos[k];
      return '<div class="col-4 col-md-3 col-xl-3"><label class="form-label small mb-1" for="cpP' + k + '">P' + p.numero + ' <span class="text-muted">/ ' + fmt(p.cotacao) + '</span></label>' +
        '<input id="cpP' + k + '" data-k="' + k + '" type="text" inputmode="decimal" class="form-control form-control-sm cp-ponto" value="' + (v == null ? '' : esc(fmt(v))) + '" autocomplete="off"></div>';
    }).join('');
    $('cpGrelha').querySelectorAll('.cp-ponto').forEach(function (el) { el.addEventListener('input', recalcular); });
    $('cpBlocoMC').classList.toggle('d-none', !mc);
    $('cpTituloAbertas').classList.toggle('d-none', !(mc && prova.perguntas.some(function (p) { return p.tipo !== 'MC'; })));
    if (mc) desenharEscolhaMultipla(c); else recalcular();
    var badge = $('cpEstadoAluno');
    badge.textContent = rotuloEstado(c);
    badge.className = 'badge ' + (!c ? 'text-bg-secondary' : c.estado === 'LANCADA' ? 'text-bg-success' : c.estado === 'CORRIGIDA' ? 'text-bg-primary' : 'text-bg-warning');
    desenharImagens((c && c.imagens) || []);
    var temCorr = !!(c && c.estado && c.estado !== 'RASCUNHO');
    $('cpAcoesFolha').classList.toggle('d-none', !c);
    $('cpBtnPdfAluno').classList.toggle('d-none', !(c && (c.imagens || []).length));
    $('cpBtnElimCorr').classList.toggle('d-none', !(c && (c.imagens || []).length));
    $('cpBtnElimCorr').title = 'Elimina só a prova corrigida (PDF); a nota na caderneta não muda';
  }

  // Um ponto por pergunta, na ordem da prova; as de escolha múltipla ficam a null (o servidor corrige-as pelo gabarito)
  function lerPontos() {
    return prova.perguntas.map(function (p, k) {
      var el = $('cpP' + k);
      return el ? num(el.value) : null;
    });
  }
  function mostrarNota(total, nota) {
    $('cpTotal').textContent = total == null ? '–' : fmt(total);
    var el = $('cpNota');
    el.textContent = nota == null ? '–' : fmt(nota);
    el.style.color = nota != null && nota < NOTA_MINIMA ? '#dc3545' : ''; // notas negativas a vermelho
  }
  function recalcular() {
    var pontos = lerPontos(), total = 0, erro = false;
    pontos.forEach(function (v, k) {
      var el = $('cpP' + k); if (!el) return;
      var mau = v !== null && (isNaN(v) || v < 0 || v > prova.perguntas[k].cotacao);
      el.classList.toggle('is-invalid', mau);
      if (mau) erro = true; else if (v !== null) total += v;
    });
    if (erro) { mostrarNota(null, null); return; }
    if (prova.tipo === 'MULTIPLA_ESCOLHA') return; // a nota final vem do servidor ao guardar (chave de correcção)
    mostrarNota(total, Math.min(20, total / prova.cotacao_total * 20));
  }

  // ---------- Escolha múltipla (grelha igual à Folha de Resposta impressa) ----------
  var respAtual = [];   // uma letra por pergunta de escolha múltipla ('' = ainda não assinalada, '-' = em branco)
  var LETRAS = 'ABCDEF';
  function perguntasMC() { return prova.perguntas.filter(function (p) { return p.tipo === 'MC'; }); }
  function desenharEscolhaMultipla(c) {
    var mc = perguntasMC(), pontos = (c && c.pontos) || [];
    var guardadas = (c && c.respostas) || '';
    respAtual = mc.map(function (_, k) { return guardadas.charAt(k) || ''; });
    var vs = prova.versoes || [];
    $('cpBlocoVersao').classList.toggle('d-none', !vs.length);
    $('cpVersao').innerHTML = '<option value="">--</option>' + vs.map(function (v) { return '<option value="' + esc(v) + '">' + esc(v) + '</option>'; }).join('');
    $('cpVersao').value = (c && c.versao) || '';
    var nAlt = prova.n_alternativas || 4;
    $('cpGrelhaMC').innerHTML = mc.map(function (p, k) {
      var estado = c && guardadas ? (pontos[p.numero - 1] > 0 ? 'certa' : 'errada') : '';
      var bolas = '';
      for (var a = 0; a < nAlt; a++) bolas += '<button type="button" class="btn btn-outline-secondary cp-bolha" data-k="' + k + '" data-l="' + LETRAS[a] + '" aria-label="Pergunta ' + p.numero + ', alternativa ' + LETRAS[a] + '">' + LETRAS[a] + '</button>';
      bolas += '<button type="button" class="btn btn-outline-secondary cp-bolha" data-k="' + k + '" data-l="-" title="Em branco" aria-label="Pergunta ' + p.numero + ', em branco">–</button>';
      bolas += '<button type="button" class="btn btn-outline-secondary cp-bolha" data-k="' + k + '" data-l="N" title="Nula (mais de uma alternativa assinalada)" aria-label="Pergunta ' + p.numero + ', nula">N</button>';
      return '<div class="cp-mc-linha ' + estado + '" id="cpL' + k + '"><span class="num">' + p.numero + '</span><div class="btn-group btn-group-sm">' + bolas + '</div></div>';
    }).join('');
    $('cpGrelhaMC').querySelectorAll('.cp-bolha').forEach(function (b) {
      b.addEventListener('click', function () {
        var k = parseInt(b.getAttribute('data-k'), 10), l = b.getAttribute('data-l');
        respAtual[k] = respAtual[k] === l ? '' : l;
        pintarBolhas();
      });
    });
    pintarBolhas();
    var ab = (c && c.estado && c.estado !== 'RASCUNHO') || (c && guardadas);
    mostrarNota(ab ? c.total : null, ab ? c.nota : null);
    var acertos = c && guardadas ? mc.filter(function (p) { return pontos[p.numero - 1] > 0; }).length : null;
    $('cpAcertos').textContent = acertos == null ? 'A nota é calculada pelo sistema contra a chave de correcção ao guardar.' : acertos + ' certa(s) em ' + mc.length + ' · verde = certa, vermelho = errada ou em branco.';
  }
  function pintarBolhas() {
    $('cpGrelhaMC').querySelectorAll('.cp-bolha').forEach(function (b) {
      var activo = respAtual[parseInt(b.getAttribute('data-k'), 10)] === b.getAttribute('data-l');
      b.classList.toggle('btn-primary', activo);
      b.classList.toggle('btn-outline-secondary', !activo);
    });
    $('cpRespostas').value = respAtual.map(function (r) { return r || '·'; }).join('');
  }
  function aoEscreverRespostas() {
    var nAlt = prova.n_alternativas || 4, ok = LETRAS.slice(0, nAlt) + '-N';
    var txt = ($('cpRespostas').value || '').toUpperCase().replace(/\s+/g, '');
    respAtual = respAtual.map(function (_, k) { var ch = txt.charAt(k); return ok.indexOf(ch) >= 0 && ch ? ch : ''; });
    $('cpGrelhaMC').querySelectorAll('.cp-bolha').forEach(function (b) {
      var activo = respAtual[parseInt(b.getAttribute('data-k'), 10)] === b.getAttribute('data-l');
      b.classList.toggle('btn-primary', activo);
      b.classList.toggle('btn-outline-secondary', !activo);
    });
  }

  async function desenharImagens(imagens) {
    libertarImagens();
    var box = $('cpImagens');
    if (!imagens.length) { box.innerHTML = 'Ainda sem páginas digitalizadas para este aluno.'; return; }
    box.innerHTML = '';
    for (var k = 0; k < imagens.length; k++) {
      var im = imagens[k];
      try {
        var r = await fetch(API + 'imagens/' + encodeURIComponent(im.id) + '/', { headers: cab() });
        if (!r.ok) throw new Error('indisponível');
        var url = URL.createObjectURL(await r.blob());
        urlsImagens.push(url);
        var bloco = document.createElement('div');
        bloco.className = 'position-relative mb-2';
        var conteudo = im.tipo === 'application/pdf'
          ? '<iframe class="w-100 border rounded" style="height:60vh" title="Prova (PDF)" src="' + url + '"></iframe>'
          : '<img class="img-fluid border rounded" alt="Página ' + im.ordem + ' da prova" src="' + url + '">';
        bloco.innerHTML = conteudo + '<button type="button" class="btn btn-sm btn-light border position-absolute top-0 end-0 m-1 cp-rem" data-id="' + esc(im.id) + '" title="Remover página"><i class="bi bi-x-lg"></i></button>';
        box.appendChild(bloco);
      } catch (_) {
        var aviso = document.createElement('div'); aviso.textContent = 'Página ' + im.ordem + ' indisponível.'; box.appendChild(aviso);
      }
    }
    box.querySelectorAll('.cp-rem').forEach(function (b) {
      b.addEventListener('click', async function () {
        if (!confirm('Remover esta página digitalizada?')) return;
        var res = await chamar(API + 'imagens/' + encodeURIComponent(b.getAttribute('data-id')) + '/', { method: 'DELETE' });
        if (!res.ok) { toast(msg(res), 'danger'); return; }
        await recarregarMantendo();
      });
    });
  }

  async function recarregarMantendo() {
    var i = idxAluno;
    await abrirProva(prova.id);
    if (prova && prova.alunos.length) mostrarAluno(Math.min(i, prova.alunos.length - 1));
  }

  async function guardar(avancar) {
    var pontos = lerPontos();
    if (pontos.some(function (v, k) { return v !== null && (isNaN(v) || v < 0 || v > prova.perguntas[k].cotacao); })) {
      toast('Há pontos inválidos: cada valor deve estar entre 0 e a cotação da pergunta.', 'warning'); return false;
    }
    var a = prova.alunos[idxAluno], corpo = { pontos: pontos };
    if (prova.tipo === 'MULTIPLA_ESCOLHA') {
      var feitas = respAtual.filter(Boolean).length;
      if (feitas && feitas < respAtual.length) {
        toast('Faltam ' + (respAtual.length - feitas) + ' pergunta(s) por assinalar: use «–» para as deixadas em branco pelo aluno.', 'warning'); return false;
      }
      corpo.respostas = feitas ? respAtual.join('') : '';
      corpo.versao = $('cpVersao').value;
    }
    var res = await chamar(API + encodeURIComponent(prova.id) + '/correcoes/' + encodeURIComponent(a.aluno_id) + '/', json('PUT', corpo));
    if (!res.ok) { toast(msg(res), 'danger'); return false; }
    var prox = avancar ? Math.min(idxAluno + 1, prova.alunos.length - 1) : idxAluno;
    toast('Correcção guardada: ' + fmt(res.json.data.nota) + ' valores' + (res.json.data.estado === 'RASCUNHO' ? ' (rascunho: faltam perguntas)' : '') + '.', 'success');
    await abrirProva(prova.id);
    mostrarAluno(prox);
    return true;
  }

  async function enviarPagina(ev) {
    var f = ev.target.files && ev.target.files[0];
    ev.target.value = '';
    if (!f || !prova) return;
    var fd = new FormData(); fd.append('ficheiro', f);
    var a = prova.alunos[idxAluno];
    var res = await chamar(API + encodeURIComponent(prova.id) + '/correcoes/' + encodeURIComponent(a.aluno_id) + '/imagens/', { method: 'POST', headers: cab(), body: fd });
    if (!res.ok) { toast(msg(res), 'danger'); return; }
    var guardados = lerPontos(); // não perder o que já foi escrito/assinalado no ecrã
    var respostas = respAtual.slice(), versao = $('cpVersao').value;
    await recarregarMantendo();
    guardados.forEach(function (v, k) { var el = $('cpP' + k); if (el && v !== null && !isNaN(v)) el.value = fmt(v); });
    if (prova.tipo === 'MULTIPLA_ESCOLHA') { respAtual = respostas; $('cpVersao').value = versao; pintarBolhas(); }
    recalcular();
  }

  // Descarrega o PDF das folhas corrigidas (pedido autenticado → ficheiro). alunoId vazio = toda a turma.
  async function descarregarPdf(alunoId) {
    if (!prova) return;
    // Nome do ficheiro: Avaliacao corrigida - Disciplina - Tipo de avaliação - Ano
    var nome = ('Avaliacao corrigida - ' + prova.disciplina_nome + ' - ' + (prova.instrumento_nome || prova.titulo) + ' - ' + (prova.ano_letivo || '')).replace(/[\\/:*?"<>|]+/g, ' ').replace(/[\s-]+$/, '') + '.pdf';
    // usa o descarregamento do sistema (pergunta «com/sem carimbo da escola» e trata a sessão e os erros)
    await downloadFicheiroBinario(API + encodeURIComponent(prova.id) + '/folhas-corrigidas/' + (alunoId ? '?aluno_id=' + encodeURIComponent(alunoId) : ''), nome);
  }
  // Elimina só a prova corrigida (PDF/folha); a correcção e a nota na caderneta mantêm-se.
  // Lista de resultados (Nº, código, nome, turma, nota, tipo de avaliação, disciplina, ano…) em PDF ou Excel.
  async function descarregarLista(formato, carimbo) {
    if (!prova) return;
    var ext = formato === 'xlsx' ? 'xlsx' : 'pdf';
    var nome = ('Lista de notas - ' + prova.disciplina_nome + ' - ' + (prova.instrumento_nome || prova.titulo) + ' - ' + (prova.ano_letivo || '')).replace(/[\\/:*?"<>|]+/g, ' ').replace(/[\s-]+$/, '') + '.' + ext;
    await downloadFicheiroBinario(API + encodeURIComponent(prova.id) + '/lista-notas/?formato=' + ext + (carimbo ? '&carimbo=' + carimbo : ''), nome);
  }
  // Depois da correcção automática: descarrega as provas corrigidas (PDF) e a lista de notas (PDF e Excel).
  // Pergunta «com/sem carimbo» uma só vez para os três ficheiros.
  async function descarregarResultados() {
    if (!prova) return;
    var escolha = typeof perguntarCarimboDocumento === 'function' ? await perguntarCarimboDocumento() : 'nao';
    if (!escolha) return;
    await downloadFicheiroBinario(API + encodeURIComponent(prova.id) + '/folhas-corrigidas/?carimbo=' + escolha,
      ('Avaliacao corrigida - ' + prova.disciplina_nome + ' - ' + (prova.instrumento_nome || prova.titulo) + ' - ' + (prova.ano_letivo || '')).replace(/[\\/:*?"<>|]+/g, ' ').replace(/[\s-]+$/, '') + '.pdf');
    await descarregarLista('pdf', escolha);
    await descarregarLista('xlsx', escolha);
  }
  async function eliminarCorreccao() {
    var a = prova && prova.alunos[idxAluno];
    if (!a || !a.correcao || !(a.correcao.imagens || []).length) return;
    if (!confirm('Eliminar a prova corrigida de ' + a.nome + '?\n\nSó o PDF/folha corrigida é eliminado: a nota e a caderneta não mudam. Não pode ser desfeito.')) return;
    var res = await chamar(API + encodeURIComponent(prova.id) + '/correcoes/' + encodeURIComponent(a.aluno_id) + '/', { method: 'DELETE' });
    if (!res.ok) { toast(msg(res), 'danger'); return; }
    toast(res.json.message || 'Prova corrigida eliminada.', 'success');
    await recarregarMantendo();
  }

  async function lancar() {
    if (!prova) return;
    var r = prova.resumo;
    if (!confirm('Lançar na caderneta (' + prova.disciplina_nome + ', ' + prova.turma_nome + ') as notas das correcções completas ainda não lançadas?\n\nEsta acção fica registada na auditoria.')) return;
    var res = await chamar(API + encodeURIComponent(prova.id) + '/lancar/', json('POST', {}));
    var falhas = (res.json && res.json.falhas) || [];
    if (!res.ok && !falhas.length) { toast(msg(res), 'warning'); return; }
    toast(res.json.message + (falhas.length ? ' ' + falhas.map(function (f) { return f.nome + ': ' + f.message; }).join(' | ') : ''), falhas.length ? 'warning' : 'success');
    await recarregarMantendo();
  }

  async function eliminar() {
    var lanc = prova && prova.resumo ? prova.resumo.lancadas : 0;
    if (!prova || !confirm('Eliminar a prova "' + prova.titulo + '", todas as correcções, as provas corrigidas e as folhas guardadas?' +
        (lanc ? '\n\nAs ' + lanc + ' nota(s) já lançada(s) na caderneta NÃO são alteradas.' : '') + '\n\nNão pode ser desfeito.')) return;
    var res = await chamar(API + encodeURIComponent(prova.id) + '/', { method: 'DELETE' });
    if (!res.ok) { toast(msg(res), 'danger'); return; }
    toast(res.json.message || 'Prova eliminada.', 'success');
    await carregarProvas();
  }

  // ---------- Passo 1b: importar o gabarito (só propõe; o professor revê nas caixas da chave) ----------
  async function importarGabarito() {
    var f = $('cpGabFicheiro').files && $('cpGabFicheiro').files[0], texto = $('cpGabTexto').value.trim();
    var box = $('cpGabAvisos');
    if (!f && !texto) { toast('Escolha um ficheiro ou cole a chave de correcção.', 'warning'); return; }
    var res;
    if (f) { var fd = new FormData(); fd.append('ficheiro', f); res = await chamar(API + 'gabarito/importar/', { method: 'POST', headers: cab(), body: fd }); }
    else res = await chamar(API + 'gabarito/importar/', json('POST', { texto: texto }));
    box.classList.remove('d-none');
    if (!res.ok) { box.className = 'small mt-2 text-danger'; box.textContent = msg(res); return; }
    var d = res.json.data, chaves = Object.keys(d.versoes);
    $('cpNPerg').value = d.n_perguntas; $('cpNAlt').value = d.n_alternativas;
    $('cpVersoes').value = chaves.filter(function (v) { return v !== '-'; }).join(' ');
    desenharGabaritos();
    chaves.forEach(function (v) {
      var el = document.querySelector('#cpGabaritos .cp-gab[data-v="' + (v === '-' ? '' : v) + '"]');
      if (el) el.value = d.versoes[v].map(function (l) { return l || '?'; }).join('');
    });
    desenharFolhaVisual(); estadoCartaoAuto();
    box.className = 'small mt-2 text-success';
    box.innerHTML = '<i class="bi bi-check-circle me-1"></i>Chave lida: ' + d.n_perguntas + ' perguntas, ' + d.n_alternativas + ' alternativas. Confira nas caixas da chave abaixo (corrija o que estiver mal; «?» = sem resposta lida) e depois crie a prova.' +
      (d.avisos || []).map(function (a) { return '<div class="text-muted">• ' + esc(a) + '</div>'; }).join('');
  }

  // ---------- Passo 2: correcção automática das folhas (leitura óptica) ----------
  var lote = [], loteProva = '', revIdx = -1;
  var LETRAS = 'ABCDEF';

  function precisaRevisao(it) {
    if (it.estado !== 'pendente') return false;
    var exigeVersao = prova && (prova.versoes || []).length > 0;
    return !it.aluno_id || it.respostas.indexOf('*') >= 0 || (it.duvidas || []).length > 0 || (it.avisos || []).length > 0 || (exigeVersao && !it.versao);
  }
  function visiveis() {
    var f = $('cpAutoFiltro').value;
    return lote.map(function (it, i) { return i; }).filter(function (i) {
      var it = lote[i];
      if (f === 'feitas') return it.estado === 'confirmada';
      if (f === 'todas') return it.estado === 'pendente';
      return precisaRevisao(it) || it.estado === 'erro';
    });
  }
  function resumoLote() {
    var n = lote.length, conf = 0, lim = 0, rev = 0, err = 0;
    lote.forEach(function (it) {
      if (it.estado === 'confirmada') conf++;
      else if (it.estado === 'erro') err++;
      else if (it.estado === 'pendente') { if (precisaRevisao(it)) rev++; else lim++; }
    });
    $('cpAutoResumo').innerHTML = '<strong>' + n + '</strong> página(s) lida(s): <span class="text-success">' + lim + ' sem dúvidas</span> · <span class="text-warning-emphasis">' + rev + ' para rever</span> · <span class="text-danger">' + err + ' com erro</span> · ' + conf + ' confirmada(s)';
    $('cpAutoConfirmarLimpas').disabled = !lim;
  }
  function marcarRepetidos() {
    var vistos = {};
    lote.forEach(function (it) {
      if (!it.aluno_id || it.estado === 'erro') return;
      if (vistos[it.aluno_id]) { var av = 'Aluno já aparece noutra folha deste lote: confirme qual é a certa.'; if (it.avisos.indexOf(av) < 0) it.avisos.push(av); }
      vistos[it.aluno_id] = true;
    });
  }
  function painelLote() {
    $('cpAutoPainel').classList.toggle('d-none', !lote.length);
    resumoLote();
    var vis = visiveis();
    if (!vis.length) { revIdx = -1; $('cpAutoRevisao').classList.add('d-none'); $('cpAutoPos').textContent = ''; return; }
    if (vis.indexOf(revIdx) < 0) revIdx = vis[0];
    $('cpAutoRevisao').classList.remove('d-none');
    mostrarRevisao(vis);
  }
  function mostrarRevisao(vis) {
    var it = lote[revIdx];
    $('cpAutoPos').textContent = (vis.indexOf(revIdx) + 1) + ' de ' + vis.length;
    if (it.estado === 'erro') {
      $('cpAutoImg').removeAttribute('src');
      $('cpAutoAvisos').innerHTML = '<div class="text-danger"><i class="bi bi-x-circle me-1"></i>' + esc(it.origem + ' · pág. ' + it.pagina + ': ' + it.erro) + '</div>';
      $('cpAutoDuvidas').innerHTML = ''; $('cpAutoLida').textContent = '';
      $('cpAutoConfirmar').disabled = true;
      return;
    }
    $('cpAutoConfirmar').disabled = it.estado !== 'pendente';
    if (it.previa) $('cpAutoImg').src = it.previa;
    else if (it.pendente_id) {      // folha guardada no sistema: carrega a correcção a vermelho
      $('cpAutoImg').removeAttribute('src');
      imagemGuardada(encodeURIComponent(prova.id) + '/folhas-pendentes/' + encodeURIComponent(it.pendente_id) + '/imagem/').then(function (u) {
        it.previa = u; it.corrigida = u; if (lote[revIdx] === it) $('cpAutoImg').src = u;
      }).catch(function () { /* sem imagem */ });
    }
    var alunos = prova.alunos.map(function (a) { return '<option value="' + esc(a.aluno_id) + '">' + esc(a.nome) + ' — ' + rotuloEstado(a.correcao) + '</option>'; }).join('');
    $('cpAutoAluno').innerHTML = '<option value="">-- Escolha o aluno --</option>' + alunos;
    $('cpAutoAluno').value = it.aluno_id || '';
    var vs = prova.versoes || [];
    $('cpAutoBlocoVersao').classList.toggle('d-none', !vs.length);
    $('cpAutoVersao').innerHTML = '<option value="">-- Versão --</option>' + vs.map(function (v) { return '<option>' + esc(v) + '</option>'; }).join('');
    $('cpAutoVersao').value = it.versao || '';
    $('cpAutoAvisos').innerHTML = (it.avisos || []).map(function (a) { return '<div class="text-warning-emphasis"><i class="bi bi-exclamation-triangle me-1"></i>' + esc(a) + '</div>'; }).join('') || '<div class="text-success"><i class="bi bi-check-circle me-1"></i>Sem avisos.</div>';
    var motivo = { DUPLA: 'duas marcas', RASURA: 'rasura ao lado', FRACA: 'marca fraca', COR: 'tinta que não é azul nem preta' };
    $('cpAutoDuvidas').innerHTML = (it.duvidas || []).map(function (d) {
      var ops = '<option value="">-- escolha --</option>' + LETRAS.slice(0, prova.n_alternativas).split('').map(function (l) { return '<option>' + l + '</option>'; }).join('') + '<option value="-">em branco</option><option value="N">nula</option>';
      return '<div class="d-flex align-items-center gap-2 mb-1"><span class="small" style="width:12rem">Pergunta <strong>' + d.n + '</strong> (' + (motivo[d.motivo] || d.motivo) + '; lido: ' + d.candidatas.join('/') + ')</span>' +
        '<select class="form-select form-select-sm w-auto cp-auto-duv" data-n="' + d.n + '">' + ops + '</select></div>';
    }).join('');
    document.querySelectorAll('#cpAutoDuvidas .cp-auto-duv').forEach(function (s) { var n = s.getAttribute('data-n'); if (it.resolvidas && it.resolvidas[n]) s.value = it.resolvidas[n]; });
    $('cpAutoLida').textContent = it.respostas.join('');
  }
  function guardarCamposRevisao() {
    var it = lote[revIdx]; if (!it || it.estado === 'erro') return;
    it.aluno_id = $('cpAutoAluno').value; it.versao = $('cpAutoVersao').value || it.versao;
    it.resolvidas = it.resolvidas || {};
    document.querySelectorAll('#cpAutoDuvidas .cp-auto-duv').forEach(function (s) { it.resolvidas[s.getAttribute('data-n')] = s.value; });
  }
  function respostasFinais(it) {
    var r = it.respostas.slice(), faltam = 0;
    (it.duvidas || []).forEach(function (d) { var v = it.resolvidas && it.resolvidas[d.n]; if (v) r[d.n - 1] = v; });
    r.forEach(function (c) { if (c === '*') faltam++; });
    return { texto: r.join(''), faltam: faltam };
  }
  async function enviarItem(it) {
    var fin = respostasFinais(it);
    if (!it.aluno_id) return 'Escolha o aluno.';
    if (fin.faltam) return 'Resolva as dúvidas assinaladas (' + fin.faltam + ').';
    if ((prova.versoes || []).length && !it.versao) return 'Escolha a versão da folha.';
    // grava a correcção e desenha a folha corrigida (vistos, círculos, acertos, nota e nome do professor, a vermelho).
    // NÃO lança na caderneta: o lançamento é o passo seguinte («Iniciar lançamento automático»).
    var res = await chamar(API + encodeURIComponent(prova.id) + '/correcoes/' + encodeURIComponent(it.aluno_id) + '/confirmar-omr/',
      json('POST', { respostas: fin.texto, versao: it.versao || '', imagem: it.pendente_id ? undefined : (it.imagem || undefined), pendente_id: it.pendente_id || undefined, lancar: false }));
    if (!res.ok) return msg(res);
    it.estado = 'confirmada'; it.nota = res.json.data.nota; it.pendente_id = '';
    it.imagemId = res.json.imagem ? res.json.imagem.id : '';
    if (res.json.folha) it.corrigida = res.json.folha;
    it.msgLancamento = res.json.aviso_imagem || '';
    return '';
  }

  // ---------- Passo 2: terminou → ver, descarregar e iniciar o lançamento ----------
  var visorIdx = 0;
  function nomeAluno(id) {
    var a = prova && prova.alunos ? prova.alunos.filter(function (x) { return x.aluno_id === id; })[0] : null;
    return a ? a.nome : '';
  }
  // Tudo o que o sistema corrigiu fica guardado: este painel mostra o que está guardado (também depois de recarregar a página)
  function guardadasDaProva() {
    return (prova && prova.alunos ? prova.alunos : []).filter(function (a) { return a.correcao && (a.correcao.imagens || []).length; });
  }
  function mostrarConcluido() {
    var box = $('cpAutoConcluido'); if (!box || !prova) return;
    var guardadas = guardadasDaProva().length;
    var semAluno = lote.filter(function (x) { return x.estado === 'pendente'; }).length;
    var erros = lote.filter(function (x) { return x.estado === 'erro'; }).length;
    var porLancar = (prova.alunos || []).filter(function (a) { return a.correcao && a.correcao.estado === 'CORRIGIDA'; }).length;
    var lancadas = (prova.resumo && prova.resumo.lancadas) || 0;
    box.classList.toggle('d-none', !(guardadas || semAluno || erros));
    $('cpAutoConcluidoTexto').innerHTML = '<span class="text-success"><strong>' + guardadas + '</strong> prova(s) corrigida(s) guardada(s) no sistema</span>' +
      (semAluno ? ' · <span class="text-warning-emphasis"><strong>' + semAluno + '</strong> corrigida(s) sem aluno identificado, também guardada(s) (escolha o aluno na lista abaixo)</span>' : '') +
      (erros ? ' · <span class="text-danger"><strong>' + erros + '</strong> com erro</span>' : '') +
      '. Notas por lançar: <strong>' + porLancar + '</strong> · já lançadas: <strong>' + lancadas + '</strong>. Tudo fica guardado até o eliminar.';
    // Os botões ficam SEMPRE activos: ao carregar explicam o que falta (nunca ficam «mortos»). As folhas corrigidas sem aluno
    // também entram no PDF e na lista.
    ['cpAutoVer', 'cpAutoPdf', 'cpAutoListaPdf', 'cpAutoListaXlsx', 'cpAutoLancar'].forEach(function (id) { $(id).disabled = false; });
    $('cpAutoLancar').title = porLancar ? '' : 'Ainda não há notas por lançar: atribua os alunos às folhas corrigidas';
  }
  // Lista do visor: folhas deste lote (corrigidas ou guardadas sem aluno) + provas corrigidas já guardadas no sistema
  function listaVisor() {
    var l = [];
    lote.forEach(function (x, k) { if (x.estado !== 'erro' && (x.corrigida || x.pendente_id)) l.push({ tipo: 'lote', x: x, k: k }); });
    guardadasDaProva().forEach(function (a) {
      if (l.some(function (o) { return o.tipo === 'lote' && o.x.aluno_id === a.aluno_id && o.x.estado === 'confirmada' && o.x.corrigida; })) return;
      l.push({ tipo: 'guardada', aluno: a });
    });
    return l;
  }
  async function mostrarVisor(i) {
    var lista = listaVisor();
    if (!lista.length) { toast('Ainda não há provas corrigidas para ver.', 'warning'); return; }
    visorIdx = (i + lista.length) % lista.length;
    var o = lista[visorIdx], img = $('cpAutoVerImg'), legenda = $('cpAutoVerLegenda');
    $('cpAutoVisor').classList.remove('d-none');
    // folha ainda sem aluno: mostra a escolha do aluno (e da versão) por baixo
    var pendente = o.tipo === 'lote' && o.x.estado === 'pendente';
    $('cpAutoVerAtribuir').classList.toggle('d-none', !pendente);
    if (pendente) {
      $('cpAutoVerAluno').innerHTML = '<option value="">-- escolha o aluno --</option>' +
        (prova.alunos || []).map(function (a) { return '<option value="' + esc(a.aluno_id) + '">' + esc(a.nome) + ' — ' + rotuloEstado(a.correcao) + '</option>'; }).join('');
      $('cpAutoVerAluno').value = o.x.aluno_id || '';
      $('cpAutoVerDados').removeAttribute('src');
      if (o.x.pendente_id) imagemGuardada(encodeURIComponent(prova.id) + '/folhas-pendentes/' + encodeURIComponent(o.x.pendente_id) + '/dados/').then(function (u) { if (lote[visorIdx] || true) $('cpAutoVerDados').src = u; }).catch(function () {});
      var vsv = prova.versoes || [];
      $('cpAutoVerBlocoVersao').classList.toggle('d-none', !vsv.length);
      $('cpAutoVerVersao').innerHTML = '<option value="">--</option>' + vsv.map(function (v) { return '<option>' + esc(v) + '</option>'; }).join('');
      $('cpAutoVerVersao').value = o.x.versao || '';
    }
    var nome, nota, estado, url = '';
    if (o.tipo === 'lote') {
      var it = o.x; nome = nomeAluno(it.aluno_id); nota = it.nota != null ? it.nota : it.notaPrev;
      estado = it.estado === 'confirmada' ? 'guardada' : 'guardada, sem aluno';
      url = it.corrigida || '';
      if (!url && it.pendente_id) { try { url = it.corrigida = it.previa = await imagemGuardada(encodeURIComponent(prova.id) + '/folhas-pendentes/' + encodeURIComponent(it.pendente_id) + '/imagem/'); } catch (_) { url = ''; } }
    } else {
      var c = o.aluno.correcao; nome = o.aluno.nome; nota = c.nota; estado = c.estado === 'LANCADA' ? 'guardada · nota lançada' : 'guardada · nota por lançar';
      try { url = await imagemGuardada('imagens/' + encodeURIComponent(c.imagens[0].id) + '/'); } catch (_) { url = ''; }
    }
    if (visorIdx !== ((i + lista.length) % lista.length)) return;   // o utilizador já mudou de folha
    if (url) img.src = url; else img.removeAttribute('src');
    legenda.textContent = (visorIdx + 1) + '/' + lista.length + ' · ' + (nome || 'aluno por identificar') +
      (nota != null ? ' · nota ' + fmt(nota) : '') + ' · ' + estado;
  }
  // Atribui a folha corrigida (sem aluno) ao aluno escolhido: grava a correcção e a prova corrigida desse aluno
  async function atribuirDoVisor() {
    var lista = listaVisor(), o = lista[visorIdx];
    if (!o || o.tipo !== 'lote' || o.x.estado !== 'pendente') return;
    var id = $('cpAutoVerAluno').value;
    if (!id) { toast('Escolha o aluno a quem pertence esta folha.', 'warning'); return; }
    var it = o.x; it.aluno_id = id; it.versao = $('cpAutoVerVersao').value || it.versao;
    $('cpAutoVerGuardar').disabled = true;
    try {
      var e = await enviarItem(it);
      if (e) { toast(e, 'warning'); return; }
      toast('Prova corrigida guardada para ' + nomeAluno(id) + ': ' + fmt(it.nota) + ' valores.', 'success');
      await recarregarMantendo(); painelLote(); mostrarConcluido();
      var resto = listaVisor();
      if (resto.length) mostrarVisor(Math.min(visorIdx, resto.length - 1)); else $('cpAutoVisor').classList.add('d-none');
    } finally { $('cpAutoVerGuardar').disabled = false; }
  }
  // O professor elimina quando quiser: só esta prova corrigida (a nota na caderneta não muda) ou a folha guardada sem aluno
  async function eliminarDoVisor() {
    var lista = listaVisor(); var o = lista[visorIdx]; if (!o) return;
    if (o.tipo === 'lote' && o.x.pendente_id) {
      if (!confirm('Eliminar esta folha guardada (sem aluno)? Não pode ser desfeito.')) return;
      var r = await chamar(API + encodeURIComponent(prova.id) + '/folhas-pendentes/' + encodeURIComponent(o.x.pendente_id) + '/', { method: 'DELETE' });
      if (!r.ok) { toast(msg(r), 'danger'); return; }
      lote.splice(o.k, 1); painelLote(); mostrarConcluido();
      toast('Folha eliminada.', 'success');
    } else {
      var aluno = o.tipo === 'guardada' ? o.aluno : prova.alunos.filter(function (a) { return a.aluno_id === o.x.aluno_id; })[0];
      if (!aluno) return;
      if (!confirm('Eliminar a prova corrigida de ' + aluno.nome + '?\n\nSó o PDF/folha corrigida é eliminado: a nota e a caderneta não mudam. Não pode ser desfeito.')) return;
      var r2 = await chamar(API + encodeURIComponent(prova.id) + '/correcoes/' + encodeURIComponent(aluno.aluno_id) + '/', { method: 'DELETE' });
      if (!r2.ok) { toast(msg(r2), 'danger'); return; }
      if (o.tipo === 'lote') o.x.corrigida = '';
      toast(r2.json.message || 'Prova corrigida eliminada.', 'success');
      await recarregarMantendo();
    }
    var restantes = listaVisor();
    if (restantes.length) mostrarVisor(Math.min(visorIdx, restantes.length - 1)); else $('cpAutoVisor').classList.add('d-none');
  }  async function lancarAutomatico() {
    if (!prova) return;
    var out = $('cpAutoLancarResultado'), btn = $('cpAutoLancar');
    var porLancarN = (prova.alunos || []).filter(function (a) { return a.correcao && a.correcao.estado === 'CORRIGIDA'; }).length;
    if (!porLancarN) {
      out.className = 'small text-warning-emphasis';
      out.innerHTML = '<i class="bi bi-info-circle me-1"></i>Ainda não há notas por lançar: as folhas corrigidas ainda não têm aluno. Carregue em «Ver provas corrigidas», escolha o aluno de cada folha e «Atribuir ao aluno e guardar»; depois volte a carregar aqui.';
      return;
    }
    btn.disabled = true; out.className = 'small text-muted'; out.textContent = 'A lançar as notas nas cadernetas…';
    var res = await chamar(API + encodeURIComponent(prova.id) + '/lancar/', json('POST', {}));
    var j = res.json || {};
    if (!res.ok && !j.falhas) { out.className = 'small text-danger'; out.textContent = msg(res); btn.disabled = false; return; }
    var falhas = j.falhas || [];
    out.className = 'small ' + (falhas.length ? 'text-warning-emphasis' : 'text-success');
    out.innerHTML = '<i class="bi bi-journal-check me-1"></i><strong>Lançamento terminado:</strong> ' + (j.lancadas || 0) + ' nota(s) lançada(s) nas cadernetas.' +
      falhas.map(function (f) { return '<div>• ' + esc(f.nome) + ': ' + esc(f.message) + '</div>'; }).join('');
    await recarregarMantendo(); painelLote();
    btn.disabled = false;
  }
  async function lerFolhas() {
    var fich = Array.prototype.slice.call($('cpAutoFicheiros').files || []);
    if (!fich.length) { toast('Escolha as fotografias ou PDFs das folhas.', 'warning'); return; }
    // O gabarito do Passo 1 (folha de resposta clicada, chave escrita, ficheiro importado ou colado) tem PRIORIDADE sobre
    // uma prova antiga que tenha ficado aberta: era isso que fazia comparar as folhas com a prova errada.
    var formAberto = !$('cpCartaoNova').classList.contains('d-none');
    if (formAberto && !gabaritoNoFormulario() &&
        (($('cpGabFicheiro').files && $('cpGabFicheiro').files.length) || ($('cpGabTexto').value || '').trim())) {
      await importarGabarito();      // ficheiro escolhido/colado mas ainda sem «Ler gabarito»: lê-o agora
    }
    if (formAberto && gabaritoNoFormulario()) {
      // cria a prova com este gabarito (precisa de turma, disciplina e trimestre escolhidos) e usa-a nesta correcção
      $('cpAutoLer').disabled = true;
      var criada = await criarProva(true);
      estadoCartaoAuto();
      if (!criada) return;
    }
    if (!prova || prova.tipo !== 'MULTIPLA_ESCOLHA') { toast('Importe ou escreva o gabarito no Passo 1 (ou escolha uma prova já criada) para poder corrigir as folhas.', 'warning'); return; }
    lote = []; loteProva = prova.id; revIdx = -1;
    $('cpAutoConcluido').classList.add('d-none'); $('cpAutoVisor').classList.add('d-none'); $('cpAutoLancarResultado').textContent = '';
    var prog = $('cpAutoProgresso'); $('cpAutoLer').disabled = true;
    var barra = $('cpAutoBarra'), barraI = $('cpAutoBarraI');
    barra.classList.remove('d-none'); barraI.style.width = '3%';
    prog.className = 'small mt-2 text-primary'; prog.textContent = 'Correcção automática iniciada…';
    var feitoTotal = 0, totalGeral = 0;
    // Uma folha lida: regista-a e, com o aluno identificado (QR ou código de barras), grava a correcção e a folha corrigida
    // (não lança na caderneta). Dúvidas resolvidas pela leitura: marca fraca/rasura = letra mais provável; o resto em branco;
    // duas marcas = nula.
    function tratarPagina(nomeFicheiro, p) {
      if (!p.ok) { lote.push({ estado: 'erro', origem: nomeFicheiro, pagina: p.pagina, erro: p.erro, respostas: [], duvidas: [], avisos: [] }); return null; }
      var it = { estado: 'pendente', origem: nomeFicheiro, pagina: p.pagina, aluno_id: p.aluno ? p.aluno.id : '', versao: p.versao || '',
        respostas: p.respostas.split(''), duvidas: p.duvidas || [], avisos: p.avisos || [], previa: p.previa, imagem: p.imagem, resolvidas: {},
        corrigida: p.corrigida || '', notaPrev: p.nota, acertos: p.acertos, pendente_id: p.pendente_id || '' };
      lote.push(it);
      if (p.guardada) {        // corrigida e guardada pelo servidor, sem passar imagens pelo navegador
        it.estado = 'confirmada'; it.nota = p.nota; it.imagem = ''; it.previa = ''; it.corrigida = '';
        return null;
      }
      it.duvidas.forEach(function (d) { it.resolvidas[d.n] = d.sugerida || '-'; });
      var repetido = lote.some(function (o) { return o !== it && o.aluno_id && o.aluno_id === it.aluno_id && o.estado !== 'erro'; });
      if (it.aluno_id && !repetido && (!(prova.versoes || []).length || it.versao)) {
        return enviarItem(it).then(function (e) {
          if (e) it.erroAuto = e;
          else { it.imagem = ''; it.previa = ''; it.corrigida = ''; }      // já está guardada no servidor: poupa memória
        });
      }
      return null;
    }
    // O ficheiro envia-se UMA vez; os pedidos de leitura só referem o envio (não reenviam o PDF inteiro cada vez)
    async function pedir(envio, ini) {
      var fd = new FormData(); fd.append('upload_id', envio.id); fd.append('nome', envio.nome); fd.append('pagina_ini', ini);
      fd.append('guardar', '1');      // o servidor corrige e guarda logo as folhas com aluno identificado
      return chamar(API + encodeURIComponent(prova.id) + '/leitura-omr/', { method: 'POST', headers: cab(), body: fd });
    }
    function progresso(nome) {
      prog.textContent = 'A corrigir ' + nome + ' — ' + feitoTotal + (totalGeral ? '/' + totalGeral : '') + ' folha(s) corrigida(s)…';
      barraI.style.width = Math.max(3, Math.min(97, Math.round(100 * feitoTotal / Math.max(1, totalGeral || feitoTotal + 4)))) + '%';
    }
    try {
      // Correcção em LOTE no servidor (≤ 1 min, qualquer que seja o nº de folhas): envia-se o ficheiro UMA vez e o servidor
      // lê, corrige e desenha todas as folhas em paralelo; aqui só se acompanha o progresso.
      var t0 = Date.now();
      for (var k = 0; k < fich.length; k++) {
        var nomeF = fich[k].name;
        prog.textContent = 'A enviar ' + nomeF + '…';
        var fdUp = new FormData(); fdUp.append('ficheiro', fich[k]);
        var up = await chamar(API + encodeURIComponent(prova.id) + '/leitura-omr/upload/', { method: 'POST', headers: cab(), body: fdUp });
        if (!up.ok) { lote.push({ estado: 'erro', origem: nomeF, pagina: 1, erro: msg(up), respostas: [], duvidas: [], avisos: [] }); continue; }
        var ini = await chamar(API + encodeURIComponent(prova.id) + '/corrigir-lote/', json('POST', { upload_id: up.json.data.upload_id, nome: nomeF }));
        if (!ini.ok) { lote.push({ estado: 'erro', origem: nomeF, pagina: 1, erro: msg(ini), respostas: [], duvidas: [], avisos: [] }); continue; }
        var jobId = ini.json.data.job_id; totalGeral += ini.json.data.total_paginas;
        var est = null;
        while (true) {
          await new Promise(function (r) { setTimeout(r, 700); });
          var st = await chamar(API + encodeURIComponent(prova.id) + '/corrigir-lote/' + encodeURIComponent(jobId) + '/');
          if (!st.ok) { lote.push({ estado: 'erro', origem: nomeF, pagina: 1, erro: msg(st), respostas: [], duvidas: [], avisos: [] }); break; }
          est = st.json.data;
          prog.textContent = 'A corrigir ' + nomeF + ' — ' + est.feitas + '/' + est.total + ' folha(s) em ' + Math.round((Date.now() - t0) / 1000) + ' s…';
          barraI.style.width = Math.max(3, Math.min(97, Math.round(100 * est.feitas / Math.max(1, est.total)))) + '%';
          if (est.estado !== 'A_CORRER') break;
        }
        if (est && est.estado === 'ERRO') lote.push({ estado: 'erro', origem: nomeF, pagina: 1, erro: est.mensagem || 'Falhou a correcção.', respostas: [], duvidas: [], avisos: [] });
        if (est) (est.itens || []).filter(function (x) { return x.estado === 'ERRO'; }).forEach(function (x) {
          lote.push({ estado: 'erro', origem: nomeF, pagina: x.pagina, erro: x.erro || 'Erro', respostas: [], duvidas: [], avisos: [] });
        });
        feitoTotal += est ? est.feitas : 0;
      }
      // folhas lidas sem aluno identificado: ficam guardadas no servidor; mostra-as para o professor escolher o aluno
      var pend = await chamar(API + encodeURIComponent(prova.id) + '/folhas-pendentes/');
      if (pend.ok) (pend.json.data || []).forEach(function (f) {
        lote.push({ estado: 'pendente', origem: f.origem, pagina: f.pagina, aluno_id: '', versao: f.versao || '', respostas: f.respostas.split(''),
          duvidas: f.duvidas || [], avisos: f.avisos || [], previa: '', imagem: '', resolvidas: {}, corrigida: '', notaPrev: f.nota, acertos: f.acertos, pendente_id: f.id });
        (f.duvidas || []).forEach(function (d) { lote[lote.length - 1].resolvidas[d.n] = d.sugerida || '-'; });
      });
      await recarregarMantendo();
      // lançamento automático nas cadernetas (só as folhas com aluno identificado), logo a seguir
      var porLancarAuto = (prova.alunos || []).filter(function (a) { return a.correcao && a.correcao.estado === 'CORRIGIDA'; }).length;
      if (porLancarAuto) { prog.textContent = 'A lançar as notas nas cadernetas…'; await lancarAutomatico(); }
      // PDF das provas corrigidas: descarrega logo que a correcção termina
      if (guardadasDaProva().length) { try { await descarregarPdf(''); } catch (_) { toast('Não foi possível descarregar o PDF das provas corrigidas.', 'warning'); } }
      var seg = Math.round((Date.now() - t0) / 1000);
      lote.sort(function (a, b) { return a.origem === b.origem ? a.pagina - b.pagina : (a.origem < b.origem ? -1 : 1); });
      prog.dataset.seg = String(seg);
    } finally { estadoCartaoAuto(); barra.classList.add('d-none'); }
    var feitas = lote.filter(function (x) { return x.estado === 'confirmada'; }).length;
    prog.className = 'small mt-2 ' + (feitas ? 'text-success fw-semibold' : 'text-danger');
    prog.textContent = !lote.length ? 'Não foi lida nenhuma folha.' : ('Correcção terminada em ' + (prog.dataset.seg || '?') + ' s: notas lançadas nas cadernetas e PDF descarregado.');
    marcarRepetidos(); painelLote();
    if (feitas) { await recarregarMantendo(); painelLote(); }
    mostrarConcluido();
    if (listaVisor().length) mostrarVisor(0);
  }
  async function confirmarActual() {
    guardarCamposRevisao();
    var it = lote[revIdx]; if (!it || it.estado !== 'pendente') return;
    var a = prova.alunos.filter(function (x) { return x.aluno_id === it.aluno_id; })[0];
    if (a && a.correcao && a.correcao.estado !== 'RASCUNHO' && !confirm(a.nome + ' já tem correcção (' + rotuloEstado(a.correcao) + '). Substituir?')) return;
    var erro = await enviarItem(it);
    if (erro) { toast(erro, 'warning'); painelLote(); return; }
    toast('Folha corrigida e guardada: ' + fmt(it.nota) + ' valores (ainda por lançar).' + (it.msgLancamento ? ' ' + it.msgLancamento : ''), it.msgLancamento ? 'warning' : 'success');
    await recarregarMantendo(); painelLote(); mostrarConcluido();
  }
  async function confirmarLimpas() {
    var alvo = lote.filter(function (it) { return it.estado === 'pendente' && !precisaRevisao(it); });
    if (!alvo.length) return;
    var subst = alvo.filter(function (it) { var a = prova.alunos.filter(function (x) { return x.aluno_id === it.aluno_id; })[0]; return a && a.correcao && a.correcao.estado !== 'RASCUNHO'; }).length;
    if (!confirm('Confirmar ' + alvo.length + ' folha(s) sem dúvidas?' + (subst ? '\n' + subst + ' aluno(s) já tinham correcção e serão substituídos.' : '') + '\n\nCada folha é corrigida (vistos e círculos a vermelho, acertos, nota e o seu nome) e a nota é lançada na caderneta.')) return;
    var feitas = 0, lancadas = 0, falhas = [];
    for (var i = 0; i < alvo.length; i++) {
      var e = await enviarItem(alvo[i]);
      if (e) falhas.push(alvo[i].origem + ' pág. ' + alvo[i].pagina + ': ' + e);
      else { feitas++; if (alvo[i].lancada) lancadas++; else if (alvo[i].msgLancamento) falhas.push(alvo[i].origem + ' pág. ' + alvo[i].pagina + ': ' + alvo[i].msgLancamento); }
      $('cpAutoProgresso').textContent = 'A confirmar… ' + (i + 1) + '/' + alvo.length;
    }
    $('cpAutoProgresso').textContent = '';
    toast(feitas + ' folha(s) corrigida(s); ' + lancadas + ' nota(s) lançada(s) na caderneta.' + (falhas.length ? ' Falhas: ' + falhas.join(' | ') : ''), falhas.length ? 'warning' : 'success');
    await recarregarMantendo(); painelLote();
    mostrarConcluido();
  }
  function moverRevisao(d) {
    guardarCamposRevisao();
    var vis = visiveis(), p = vis.indexOf(revIdx);
    if (!vis.length) return;
    revIdx = vis[(p + d + vis.length) % vis.length]; painelLote();
  }
  async function descartarActual() {
    if (revIdx < 0 || !lote[revIdx]) return;
    var it = lote[revIdx];
    if (it.pendente_id) {          // guardada no sistema: elimina-a também no servidor
      var r = await chamar(API + encodeURIComponent(prova.id) + '/folhas-pendentes/' + encodeURIComponent(it.pendente_id) + '/', { method: 'DELETE' });
      if (!r.ok) { toast(msg(r), 'danger'); return; }
    }
    lote.splice(revIdx, 1); revIdx = -1; painelLote(); mostrarConcluido();
  }

  // ---------- Sub-menu «Provas corrigidas»: provas da turma/disciplina/trimestre escolhidos, 6 por página (altura constante) ----------
  var listaProvas = [], pagCorr = 0;
  function nomeBase(x, pref) {
    return (pref + ' - ' + x.disciplina_nome + ' - ' + (x.instrumento_nome || x.titulo) + ' - ' + (x.ano_letivo || '')).replace(/[\\/:*?"<>|]+/g, ' ').replace(/[\s-]+$/, '');
  }
  function painelCorrigidas() {
    var corpo = $('cpCorrigidasCorpo'); if (!corpo) return;
    var por = 6, tot = listaProvas.length, pags = Math.max(1, Math.ceil(tot / por));
    pagCorr = Math.max(0, Math.min(pagCorr, pags - 1));
    var fatia = listaProvas.slice(pagCorr * por, pagCorr * por + por);
    corpo.innerHTML = fatia.length ? fatia.map(function (x) {
      return '<tr><td class="small"><strong>' + esc(x.titulo) + '</strong><div class="text-muted">' + esc(x.disciplina_nome) + ' · ' + esc(x.turma_nome) + ' · ' + esc(x.periodo) + '</div></td>' +
        '<td class="text-end text-nowrap"><button type="button" class="btn btn-sm btn-outline-danger me-1 cp-cor-b" data-id="' + esc(x.id) + '" data-t="folhas"><i class="bi bi-file-earmark-pdf"></i> Provas</button>' +
        '<button type="button" class="btn btn-sm btn-outline-primary me-1 cp-cor-b" data-id="' + esc(x.id) + '" data-t="pdf"><i class="bi bi-file-earmark-pdf"></i> Lista</button>' +
        '<button type="button" class="btn btn-sm btn-outline-success cp-cor-b" data-id="' + esc(x.id) + '" data-t="xlsx"><i class="bi bi-file-earmark-excel"></i> Excel</button></td></tr>';
    }).join('') : '<tr><td colspan="2" class="text-muted small">' + (($('cpTurma').value && $('cpDisciplina').value && $('cpPeriodo').value) ? 'Ainda não há provas para esta turma, disciplina e trimestre.' : 'Escolha a turma, a disciplina e o trimestre.') + '</td></tr>';
    $('cpCorrigidasPos').textContent = tot ? ('Página ' + (pagCorr + 1) + ' de ' + pags + ' · ' + tot + ' prova(s)') : '';
    $('cpCorrigidasAnt').disabled = pagCorr <= 0; $('cpCorrigidasSeg').disabled = pagCorr >= pags - 1;
  }
  async function baixarDaLista(id, t) {
    var x = listaProvas.filter(function (p) { return p.id === id; })[0]; if (!x) return;
    var escolha = typeof perguntarCarimboDocumento === 'function' ? await perguntarCarimboDocumento() : 'nao';
    if (!escolha) return;
    var u = API + encodeURIComponent(id);
    if (t === 'folhas') await downloadFicheiroBinario(u + '/folhas-corrigidas/?carimbo=' + escolha, nomeBase(x, 'Avaliacao corrigida') + '.pdf');
    else await downloadFicheiroBinario(u + '/lista-notas/?formato=' + t + '&carimbo=' + escolha, nomeBase(x, 'Lista de notas') + '.' + t);
  }

  // ---------- Digitalizar com o scanner deste computador (assistente local sige-scanner) ----------
  var AGENTE = 'http://127.0.0.1:47811';
  async function digitalizarComScanner() {
    var prog = $('cpAutoProgresso');
    if (!prova || prova.tipo !== 'MULTIPLA_ESCOLHA') { toast('Escolha (ou crie) a prova de escolha múltipla antes de digitalizar.', 'warning'); return; }
    prog.className = 'small mt-2 text-primary';
    try { var e = await fetch(AGENTE + '/estado', { cache: 'no-store' }); if (!e.ok) throw new Error('x'); }
    catch (_) {
      prog.className = 'small mt-2 text-warning-emphasis';
      prog.innerHTML = '<i class="bi bi-printer me-1"></i>Falta ligar o scanner a este computador: <a href="/downloads/sige-scanner.ps1" download>descarregue o assistente de scanner</a>, execute-o (botão direito → «Executar com o PowerShell»), deixe a janela aberta e carregue de novo em «Digitalizar com o scanner».';
      return;
    }
    var t0 = Date.now(), btn = $('cpAutoScanner'); btn.disabled = true;
    var tick = setInterval(function () { prog.textContent = 'A digitalizar todas as folhas no scanner… ' + Math.round((Date.now() - t0) / 1000) + ' s'; }, 500);
    prog.textContent = 'A digitalizar todas as folhas no scanner… 0 s';
    var ficheiro = null;
    try {
      var r = await fetch(AGENTE + '/digitalizar?dpi=200', { cache: 'no-store' });
      if (!r.ok) { var j = {}; try { j = await r.json(); } catch (_) {} throw new Error(j.erro || 'O scanner não respondeu.'); }
      var blob = await r.blob();
      ficheiro = new File([blob], 'Digitalizacao ' + new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-') + '.pdf', { type: 'application/pdf' });
    } catch (err) {
      clearInterval(tick); btn.disabled = false;
      prog.className = 'small mt-2 text-danger'; prog.textContent = 'Digitalização falhou: ' + ((err && err.message) || 'erro desconhecido');
      return;
    }
    clearInterval(tick); btn.disabled = false;
    var segScan = Math.round((Date.now() - t0) / 1000);
    var dt = new DataTransfer(); dt.items.add(ficheiro); $('cpAutoFicheiros').files = dt.files;
    toast('Digitalização terminada em ' + segScan + ' s. A corrigir…', 'success');
    await lerFolhas();
    prog.textContent += ' (digitalização: ' + segScan + ' s)';
  }
  function ligar() {
    if (ligado) return; ligado = true;
    $('cpBtnLerGab').addEventListener('click', importarGabarito);
    $('cpAutoLer').addEventListener('click', lerFolhas);
    $('cpBtnCorrigidas').addEventListener('click', function () { var p = $('cpPainelCorrigidas'); p.classList.toggle('d-none'); $('cpBtnCorrigidas').setAttribute('aria-expanded', String(!p.classList.contains('d-none'))); painelCorrigidas(); });
    $('cpCorrigidasAnt').addEventListener('click', function () { pagCorr--; painelCorrigidas(); });
    $('cpCorrigidasSeg').addEventListener('click', function () { pagCorr++; painelCorrigidas(); });
    $('cpCorrigidasCorpo').addEventListener('click', function (ev) { var b = ev.target.closest('.cp-cor-b'); if (b) baixarDaLista(b.getAttribute('data-id'), b.getAttribute('data-t')).catch(function (e) { toast((e && e.message) || 'Não foi possível descarregar.', 'danger'); }); });
    $('cpAutoScanner').addEventListener('click', digitalizarComScanner);
    $('cpAutoConfirmar').addEventListener('click', confirmarActual);
    $('cpAutoConfirmarLimpas').addEventListener('click', confirmarLimpas);
    $('cpAutoSaltar').addEventListener('click', function () { moverRevisao(1); });
    $('cpAutoAnt').addEventListener('click', function () { moverRevisao(-1); });
    $('cpAutoSeg').addEventListener('click', function () { moverRevisao(1); });
    $('cpAutoDescartar').addEventListener('click', descartarActual);
    $('cpAutoFiltro').addEventListener('change', function () { guardarCamposRevisao(); revIdx = -1; painelLote(); });
    $('cpAutoAluno').addEventListener('change', guardarCamposRevisao);
    $('cpAutoVersao').addEventListener('change', guardarCamposRevisao);
    $('cpClasse').addEventListener('change', aoMudarClasse);
    $('cpArea').addEventListener('change', aoMudarArea);
    $('cpTurma').addEventListener('change', aoMudarTurma);
    $('cpDisciplina').addEventListener('change', function () { carregarProvas(); });
    $('cpPeriodo').addEventListener('change', function () { carregarProvas(); });
    $('cpProva').addEventListener('change', function () { var v = $('cpProva').value; if (v) abrirProva(v); else estadoVazio('Escolha a prova a corrigir.'); });
    $('cpBtnNova').addEventListener('click', function () { $('cpCartaoNova').classList.toggle('d-none'); });
    $('cpBtnCancelarNova').addEventListener('click', function () { $('cpCartaoNova').classList.add('d-none'); });
    $('cpCotacoes').addEventListener('input', resumoCotacoes);
    $('cpTipo').addEventListener('change', alternarTipoNova);
    $('cpVersoes').addEventListener('input', desenharGabaritos);
    $('cpNPerg').addEventListener('input', function () { desenharFolhaVisual(); estadoCartaoAuto(); });
    $('cpNAlt').addEventListener('input', desenharFolhaVisual);
    $('cpFolhaVersao').addEventListener('change', desenharFolhaVisual);
    $('cpGabUsar').addEventListener('click', usarGuardado);
    $('cpGabGuardar').addEventListener('click', guardarGabarito);
    $('cpGabPdf').addEventListener('click', function () {
      Promise.resolve().then(descarregarGabaritoPdf).catch(function (e) { toast((e && e.message) || 'Não foi possível descarregar o gabarito.', 'danger'); });
    });
    $('cpGabEliminar').addEventListener('click', eliminarGuardado);
    carregarGuardados();
    $('cpFolhaVisual').addEventListener('click', aoClicarFolhaVisual);
    $('cpGabaritos').addEventListener('input', function () { desenharFolhaVisual(); estadoCartaoAuto(); });
    $('cpRespostas').addEventListener('input', aoEscreverRespostas);
    alternarTipoNova();
    $('cpBtnCriar').addEventListener('click', criarProva);
    $('cpBtnEliminar').addEventListener('click', eliminar);
    $('cpAluno').addEventListener('change', function () { mostrarAluno(parseInt($('cpAluno').value, 10) || 0); });
    $('cpAnt').addEventListener('click', function () { if (prova && idxAluno > 0) mostrarAluno(idxAluno - 1); });
    $('cpSeg').addEventListener('click', function () { if (prova && idxAluno < prova.alunos.length - 1) mostrarAluno(idxAluno + 1); });
    $('cpBtnGuardar').addEventListener('click', function () { guardar(false); });
    $('cpBtnGuardarSeg').addEventListener('click', function () { guardar(true); });
    $('cpBtnLancar').addEventListener('click', lancar);
    $('cpBtnPdfAluno').addEventListener('click', function () { var a = prova && prova.alunos[idxAluno]; if (a) descarregarPdf(a.aluno_id); });
    $('cpBtnPdfTodas').addEventListener('click', function () { descarregarPdf(''); });
    $('cpAutoVer').addEventListener('click', function () { mostrarVisor(0); $('cpAutoVisor').scrollIntoView && $('cpAutoVisor').scrollIntoView({ behavior: 'smooth', block: 'nearest' }); });
    $('cpAutoVerAnt').addEventListener('click', function () { mostrarVisor(visorIdx - 1); });
    $('cpAutoVerSeg').addEventListener('click', function () { mostrarVisor(visorIdx + 1); });
    $('cpAutoVerEliminar').addEventListener('click', eliminarDoVisor);
    $('cpAutoVerGuardar').addEventListener('click', atribuirDoVisor);
    // Descarregar: nunca falha em silêncio (qualquer erro aparece como aviso)
    function seguro(fn) {
      return function () {
        Promise.resolve().then(fn).catch(function (e) { toast((e && e.message) || 'Não foi possível descarregar o ficheiro.', 'danger'); });
      };
    }
    $('cpAutoPdf').addEventListener('click', seguro(function () { return descarregarPdf(''); }));
    $('cpAutoListaPdf').addEventListener('click', seguro(function () { return descarregarLista('pdf'); }));
    $('cpAutoListaXlsx').addEventListener('click', seguro(function () { return descarregarLista('xlsx'); }));
    $('cpAutoLancar').addEventListener('click', lancarAutomatico);
    $('cpBtnListaPdf').addEventListener('click', function () { descarregarLista('pdf'); });
    $('cpBtnListaXlsx').addEventListener('click', function () { descarregarLista('xlsx'); });
    $('cpBtnElimCorr').addEventListener('click', eliminarCorreccao);
    $('cpFicheiro').addEventListener('change', enviarPagina);
  }

  window.inicializarModulo_correcao_provas = async function () {
    ligar();
    prova = null; idxAluno = 0;
    estadoCartaoAuto();
    await carregarAlocacoes();
  };
})();
