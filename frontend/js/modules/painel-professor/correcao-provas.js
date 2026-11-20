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
    if (ok) {
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
    if ($('cpTipo').value !== 'MULTIPLA_ESCOLHA' || !(parseInt($('cpNPerg').value, 10) > 0)) return false;
    var tem = false;
    document.querySelectorAll('#cpGabaritos .cp-gab').forEach(function (i) { if (/[A-Fa-f]/.test(i.value)) tem = true; });
    return tem;
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
    var res = await chamar(API, json('POST', corpo));
    if (!res.ok) { toast(msg(res), 'danger'); return false; }
    toast(automatica === true ? 'Prova criada com o gabarito importado.' : 'Prova criada com este gabarito. Passo 2: carregue as provas dos alunos.', 'success');
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
    estadoCartaoAuto();
    if (!prova.alunos.length) { estadoVazio('Esta turma não tem alunos activos.'); return; }
    preencherAlunos();
    mostrarAluno(Math.min(idxAluno, prova.alunos.length - 1));
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
    if (!prova || !confirm('Eliminar a prova "' + prova.titulo + '" e todas as correcções e páginas digitalizadas?')) return;
    var res = await chamar(API + encodeURIComponent(prova.id) + '/', { method: 'DELETE' });
    if (!res.ok) { toast(msg(res), 'danger'); return; }
    toast('Prova eliminada.', 'success');
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
    estadoCartaoAuto();
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
    $('cpAutoImg').src = it.previa;
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
    // grava a correcção, desenha a folha corrigida (vistos, círculos, acertos, nota e nome do professor, a vermelho)
    // e lança logo na caderneta
    var res = await chamar(API + encodeURIComponent(prova.id) + '/correcoes/' + encodeURIComponent(it.aluno_id) + '/confirmar-omr/',
      json('POST', { respostas: fin.texto, versao: it.versao || '', imagem: it.imagem, lancar: true }));
    if (!res.ok) return msg(res);
    it.estado = 'confirmada'; it.nota = res.json.data.nota;
    it.lancada = !!(res.json.lancamento && res.json.lancamento.ok);
    it.msgLancamento = (res.json.lancamento && !res.json.lancamento.ok) ? res.json.lancamento.message : '';
    it.imagemId = res.json.imagem ? res.json.imagem.id : '';
    if (res.json.aviso_imagem) it.msgLancamento = (it.msgLancamento ? it.msgLancamento + ' ' : '') + res.json.aviso_imagem;
    return '';
  }
  async function lerFolhas() {
    var fich = Array.prototype.slice.call($('cpAutoFicheiros').files || []);
    if (!fich.length) { toast('Escolha as fotografias ou PDFs das folhas.', 'warning'); return; }
    if ((!prova || prova.tipo !== 'MULTIPLA_ESCOLHA') && gabaritoNoFormulario()) {
      // gabarito já importado no Passo 1: cria a prova com ele (precisa de turma, disciplina e trimestre) e segue
      $('cpAutoLer').disabled = true;
      var criada = await criarProva(true);
      estadoCartaoAuto();
      if (!criada) return;
    }
    if (!prova || prova.tipo !== 'MULTIPLA_ESCOLHA') { toast('Importe ou escreva o gabarito no Passo 1 (ou escolha uma prova já criada) para poder corrigir as folhas.', 'warning'); return; }
    lote = []; loteProva = prova.id; revIdx = -1;
    var prog = $('cpAutoProgresso'); $('cpAutoLer').disabled = true;
    try {
      for (var k = 0; k < fich.length; k++) {
        var ini = 0;
        while (ini !== null) {
          prog.textContent = 'A ler ' + fich[k].name + ' (' + (k + 1) + '/' + fich.length + ')' + (ini ? ' — a partir da página ' + (ini + 1) : '') + '…';
          var fd = new FormData(); fd.append('ficheiro', fich[k]); fd.append('pagina_ini', ini);
          var res = await chamar(API + encodeURIComponent(prova.id) + '/leitura-omr/', { method: 'POST', headers: cab(), body: fd });
          if (!res.ok) { lote.push({ estado: 'erro', origem: fich[k].name, pagina: ini + 1, erro: msg(res), respostas: [], duvidas: [], avisos: [] }); break; }
          res.json.data.paginas.forEach(function (p) {
            if (!p.ok) { lote.push({ estado: 'erro', origem: fich[k].name, pagina: p.pagina, erro: p.erro, respostas: [], duvidas: [], avisos: [] }); return; }
            lote.push({ estado: 'pendente', origem: fich[k].name, pagina: p.pagina, aluno_id: p.aluno ? p.aluno.id : '', versao: p.versao || '',
              respostas: p.respostas.split(''), duvidas: p.duvidas || [], avisos: p.avisos || [], previa: p.previa, imagem: p.imagem, resolvidas: {} });
          });
          ini = res.json.data.proxima;
          marcarRepetidos(); painelLote();
        }
      }
    } finally { estadoCartaoAuto(); }
    prog.textContent = lote.length ? 'Leitura concluída.' : 'Não foi lida nenhuma folha.';
    marcarRepetidos(); painelLote();
  }
  async function confirmarActual() {
    guardarCamposRevisao();
    var it = lote[revIdx]; if (!it || it.estado !== 'pendente') return;
    var a = prova.alunos.filter(function (x) { return x.aluno_id === it.aluno_id; })[0];
    if (a && a.correcao && a.correcao.estado !== 'RASCUNHO' && !confirm(a.nome + ' já tem correcção (' + rotuloEstado(a.correcao) + '). Substituir?')) return;
    var erro = await enviarItem(it);
    if (erro) { toast(erro, 'warning'); painelLote(); return; }
    toast('Folha corrigida: ' + fmt(it.nota) + ' valores' + (it.lancada ? ' — lançada na caderneta.' : '.') + (it.msgLancamento ? ' ' + it.msgLancamento : ''), it.msgLancamento ? 'warning' : 'success');
    await recarregarMantendo(); painelLote();
    // última folha por rever do lote: descarrega logo as provas corrigidas e a lista de notas
    if (!lote.some(function (x) { return x.estado === 'pendente'; })) await descarregarResultados();
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
    // sem folhas por rever: descarrega as provas corrigidas (PDF) e a lista de notas (PDF e Excel)
    if (feitas && !lote.some(function (x) { return x.estado === 'pendente'; })) await descarregarResultados();
  }
  function moverRevisao(d) {
    guardarCamposRevisao();
    var vis = visiveis(), p = vis.indexOf(revIdx);
    if (!vis.length) return;
    revIdx = vis[(p + d + vis.length) % vis.length]; painelLote();
  }
  function descartarActual() {
    if (revIdx < 0 || !lote[revIdx]) return;
    lote.splice(revIdx, 1); revIdx = -1; painelLote();
  }

  function ligar() {
    if (ligado) return; ligado = true;
    $('cpBtnLerGab').addEventListener('click', importarGabarito);
    $('cpAutoLer').addEventListener('click', lerFolhas);
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
