// =====================================================================
// SIGE - FOLHA DE RESPOSTA PERSONALIZADA
// Filtros em cascata Classe → Turma → Aluno; exporta PDF/Excel (aluno, turma, classe, em branco).
// API: /api/v1/documentos/folha-resposta/{contexto,alunos,gerar}
// =====================================================================
(function () {
  'use strict';
  var API = '/api/v1/documentos/folha-resposta/';
  var CHAVE_LS = 'sige_folha_resposta_cfg';
  var ctx = null;
  var alunosTurma = [];
  var ligado = false;
  var urlPrevia = null;

  function $(id) { return document.getElementById(id); }
  function token() { try { return ((typeof state !== 'undefined' && state && state.token) || (window.state && window.state.token)) || sessionStorage.getItem('sige_token') || localStorage.getItem('sige_token') || ''; } catch (_) { return ''; } }
  function tenant() {
    try {
      // `state` é uma const global do app.js (não existe em window.state).
      var s = (typeof state !== 'undefined' && state) || window.state || {};
      var sel = null;
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
  function estado(msg) { var e = $('frEstado'); if (e) e.textContent = msg || ''; }
  function ano() { var st = (typeof state !== 'undefined' && state) || window.state || {}; return (st.anosPorView && st.anosPorView['folha-resposta']) || ($('folhaRespostaAnoSelect') || {}).value || ''; }
  function num(v) { var n = parseFloat(String(v).replace(',', '.')); return isFinite(n) ? n : null; }
  function fmt(v) { var r = Math.round(v * 100) / 100; return String(r).replace('.', ','); }

  function guardar() {
    try {
      var c = lerConfig(true);
      localStorage.setItem(CHAVE_LS, JSON.stringify({ n:c.n_perguntas, alt: c.n_alternativas, omr: c.marcas_omr, barras: c.codigo_barras }));
    } catch (_) { /* conveniência apenas */ }
  }
  function restaurar() {
    try {
      var s = JSON.parse(localStorage.getItem(CHAVE_LS) || 'null');
      if (!s) return;
      if (s.n) $('frNPerg').value = s.n;
      if (s.alt) $('frNAlt').value = s.alt;
      $('frOmr').checked = s.omr !== false;
      $('frBarras').checked = s.barras !== false;
    } catch (_) { /* ignorar */ }
  }

  async function pedir(caminho, opcoes) {
    var r = await fetch(API + caminho, Object.assign({ headers: cab() }, opcoes || {}));
    return r;
  }
  async function mensagemErro(r) {
    try { var j = await r.json(); return j.detail || j.message || 'Não foi possível concluir o pedido.'; } catch (_) { return 'Não foi possível concluir o pedido.'; }
  }

  // ---------- Cascata ----------
  function classeActual() { return $('frClasse').value; }
  function areaActual() { return $('frArea').value; }
  function turmasDaClasseTodas() {
    var c = (ctx.classes || []).find(function (x) { return x.classe === classeActual(); });
    return c ? c.turmas : [];
  }
  function turmasDaClasse() {
    var a = areaActual();
    return turmasDaClasseTodas().filter(function (t) { return !a || t.area === a; });
  }
  function preencherClasses() {
    var sel = $('frClasse');
    var ant = sel.value;
    sel.innerHTML = '<option value="">-- Classe --</option>' + (ctx.classes || []).map(function (c) {
      return '<option value="' + esc(c.classe) + '">' + esc(c.classe) + ' (' + c.total_alunos + ' alunos)</option>';
    }).join('');
    if (ant && (ctx.classes || []).some(function (c) { return c.classe === ant; })) sel.value = ant;
    aoMudarClasse();
  }
  function aoMudarClasse() {
    var areas = [];
    turmasDaClasseTodas().forEach(function (t) { if (t.area && areas.indexOf(t.area) < 0) areas.push(t.area); });
    var cl = (ctx.classes || []).find(function (x) { return x.classe === classeActual(); });
    ((cl && cl.areas) || []).forEach(function (a) { if (areas.indexOf(a) < 0) areas.push(a); });
    $('frArea').innerHTML = '<option value="">-- Todas as áreas/secções --</option>' + areas.map(function (a) { return '<option value="' + esc(a) + '">' + esc(a) + '</option>'; }).join('');
    aoMudarArea();
  }
  function aoMudarArea() {
    var sel = $('frTurma');
    sel.innerHTML = '<option value="">-- Turma --</option>' + turmasDaClasse().map(function (t) {
      return '<option value="' + esc(t.id) + '">' + esc(t.nome) + (t.area && t.area !== 'Geral' ? ' · ' + esc(t.area) : '') + ' (' + t.alunos + ')</option>';
    }).join('');
    preencherDisciplinas();
    aoMudarTurma();
  }
  async function aoMudarTurma() {
    alunosTurma = [];
    $('frAluno').innerHTML = '<option value="">-- Aluno --</option>';
    if ($('frEscopo').value === 'aluno' && $('frTurma').value) {
      try {
        var r = await pedir('alunos/?turma_id=' + encodeURIComponent($('frTurma').value));
        if (r.ok) { alunosTurma = (await r.json()).alunos || []; }
        else toast(await mensagemErro(r), 'danger');
      } catch (_) { toast('Falha de ligação ao carregar os alunos.', 'danger'); }
      preencherAlunos();
    }
    resumo();
  }
  function preencherAlunos() {
    var f = ($('frAlunoBusca').value || '').trim().toLowerCase();
    var lista = alunosTurma.filter(function (a) {
      return !f || (a.nome + ' ' + a.apelido + ' ' + a.codigo).toLowerCase().indexOf(f) >= 0;
    });
    var ant = $('frAluno').value;
    $('frAluno').innerHTML = '<option value="">-- Aluno (' + lista.length + ') --</option>' + lista.map(function (a) {
      return '<option value="' + esc(a.id) + '">' + a.numero + '. ' + esc((a.apelido + ' ' + a.nome).trim()) + ' — ' + esc(a.codigo) + '</option>';
    }).join('');
    if (ant && lista.some(function (a) { return a.id === ant; })) $('frAluno').value = ant;
  }
  function preencherDisciplinas() {
    var sel = $('frDisciplina');
    var ant = sel.value;
    var a = areaActual();
    var nomes = [];
    ((ctx.disciplinas_por_classe || {})[classeActual()] || []).forEach(function (d) {
      if ((!a || !d.area || d.area === 'Geral' || d.area === a) && nomes.indexOf(d.nome) < 0) nomes.push(d.nome);
    });
    sel.innerHTML = '<option value="">-- Disciplina --</option>' + nomes.map(function (n) { return '<option value="' + esc(n) + '">' + esc(n) + '</option>'; }).join('') + '<option value="__outra__">Outra disciplina…</option>';
    if (ant && sel.querySelector('option[value="' + ant.replace(/"/g, '\\"') + '"]')) sel.value = ant;
    $('frDisciplinaOutra').classList.toggle('d-none', sel.value !== '__outra__');
  }
  function mostrarCamposEscopo() {
    var e = $('frEscopo').value;
    $('frBlocoClasse').classList.remove('d-none');  // também na lista importada: a classe carrega as disciplinas do Plano Curricular
    $('frBlocoArea').classList.toggle('d-none', e === 'branco' || e === 'lista');
    $('frBlocoTurma').classList.toggle('d-none', e === 'classe' || e === 'branco' || e === 'lista');
    $('frBlocoAluno').classList.toggle('d-none', e !== 'aluno');
    $('frBlocoLista').classList.toggle('d-none', e !== 'lista');
    $('frBlocoCopias').classList.toggle('d-none', e !== 'branco');
    if (e === 'aluno') aoMudarTurma(); else resumo();
  }
  function resumo() {
    var e = $('frEscopo').value, el = $('frResumoAmbito'), c = (ctx.classes || []).find(function (x) { return x.classe === classeActual(); });
    if (c && areaActual()) c = { classe: c.classe, total_alunos: turmasDaClasse().reduce(function (s, x) { return s + x.alunos; }, 0) };
    var t = turmasDaClasse().find(function (x) { return x.id === $('frTurma').value; });
    var txt = 'Escolha a classe e a turma.';
    if (e === 'branco') txt = 'Serão geradas ' + (parseInt($('frCopias').value, 10) || 0) + ' folhas com os dados da escola e da avaliação; os campos do aluno ficam em branco.';
    else if (e === 'lista') txt = 'Será gerada uma folha por aluno da lista importada (o SIGE completa os dados pelo Código e aplica as exclusões).';
    else if (e === 'classe') txt = c ? 'Serão geradas ' + c.total_alunos + ' folhas (todos os alunos activos da ' + c.classe + ').' : 'Escolha a classe.';
    else if (e === 'turma') txt = t ? 'Serão geradas ' + t.alunos + ' folhas (alunos activos da turma ' + t.nome + ').' : 'Escolha a classe e a turma.';
    else txt = $('frAluno').value ? 'Será gerada 1 folha para o aluno escolhido.' : 'Escolha a classe, a turma e o aluno.';
    var semTurmas = !!(ctx && !(ctx.classes || []).some(function (x) { return (x.turmas || []).length; }) && e !== 'branco' && e !== 'lista');
    if (semTurmas) txt = 'Não há turmas registadas neste ano lectivo. Crie turmas e matricule alunos primeiro — ou gere a folha a partir de um ficheiro importado.';
    el.textContent = txt;
    if (semTurmas) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'btn btn-sm btn-outline-primary ms-2';
      b.innerHTML = '<i class="bi bi-upload me-1"></i>Importar ficheiro (Excel/CSV)';
      b.addEventListener('click', function () { $('frEscopo').value = 'lista'; mostrarCamposEscopo(); });
      el.appendChild(b);
    }
  }

  // ---------- Cotação ----------
  function linhaSeccao(ate, cot) {
    var d = document.createElement('div');
    d.className = 'd-flex align-items-center gap-2 fr-seccao';
    d.innerHTML = '<span class="small">Até à pergunta</span><input type="number" min="1" max="200" class="form-control form-control-sm fr-sec-ate" style="width:90px" value="' + (ate || '') + '">' +
      '<span class="small">vale</span><input type="text" inputmode="decimal" class="form-control form-control-sm fr-sec-cot" style="width:90px" value="' + (cot == null ? '' : String(cot).replace('.', ',')) + '">' +
      '<span class="small">val. cada</span><button type="button" class="btn btn-sm btn-outline-danger fr-sec-rm" aria-label="Remover secção"><i class="bi bi-x-lg"></i></button>';
    return d;
  }
  function lerSeccoes() {
    return Array.prototype.map.call(document.querySelectorAll('#frSeccoesLista .fr-seccao'), function (d) {
      return { ate: parseInt(d.querySelector('.fr-sec-ate').value, 10), cotacao: num(d.querySelector('.fr-sec-cot').value) };
    });
  }
  function lerAbertas() {
    if (!$('frAbN')) return [];
    var n = parseInt($('frAbN').value, 10) || 0, c = num($('frAbCot').value);
    return n > 0 ? [{ rotulo: $('frAbRotulo').value.trim(), n: n, cotacao: c == null ? 0 : c }] : [];
  }
  function totalCotacao() {
    var t = totalMultipla(), ab = lerAbertas();
    return t == null ? null : t + (ab.length ? ab[0].n * ab[0].cotacao : 0);
  }
  function totalMultipla() {
    var n = parseInt($('frNPerg').value, 10) || 0;
    if (!n) return null;
    if ($('frModoCot').value === 'seccoes') {
      var tot = 0, ini = 1, secs = lerSeccoes();
      for (var i = 0; i < secs.length; i++) {
        if (!secs[i].ate || secs[i].cotacao == null || secs[i].ate < ini || secs[i].ate > n) return null;
        tot += (secs[i].ate - ini + 1) * secs[i].cotacao; ini = secs[i].ate + 1;
      }
      return ini > n ? tot : null;
    }
    var c = num($('frCotPerg').value);
    return (c == null ? 20 / n : c) * n;
  }
  // Prévia viva da grelha: formada a partir do nº de perguntas e de alternativas definidos no formulário.
  function desenharGrelhaPrevia() {
    var alvo = $('frGrelhaPrevia'); if (!alvo) return;
    var n = parseInt($('frNPerg').value, 10) || 0;
    var alt = parseInt($('frNAlt').value, 10) || 4;
    var info = $('frGrelhaInfo');
    if (n < 1) { alvo.innerHTML = '<span class="text-muted small">Defina o número de perguntas.</span>'; if (info) info.textContent = ''; return; }
    if (n > 100) { n = 100; if (info) info.textContent = 'O máximo é 100 perguntas (a folha cabe numa só página).'; }
    else if (info) info.textContent = n + ' pergunta(s) · ' + alt + ' alternativas · ' + 'A–' + 'ABCDEF'.charAt(alt - 1);
    var cols = n <= 40 ? 2 : n <= 75 ? 3 : 4;
    var linhas = Math.ceil(Math.ceil(n / cols) / 5) * 5;
    var letras = 'ABCDEF'.slice(0, alt).split('');
    var html = '';
    for (var c = 0; c * linhas < n; c++) {
      html += '<div style="min-width:190px">';
      for (var r = 0; r < linhas && c * linhas + r < n; r++) {
        var q = c * linhas + r + 1;
        html += '<div class="d-flex align-items-center gap-1" style="margin-bottom:' + ((r % 5 === 4) ? '8' : '2') + 'px">' +
          '<span class="fw-bold text-end" style="width:28px;font-size:12px;font-family:\'Times New Roman\',serif">' + q + '</span>' +
          letras.map(function (l) { return '<span style="display:inline-block;width:26px;height:15px;line-height:13px;border:1px solid #333;border-radius:4px;text-align:center;font-size:10px;font-family:\'Times New Roman\',serif;color:#555">' + l + '</span>'; }).join('') +
          '</div>';
      }
      html += '</div>';
    }
    alvo.innerHTML = html;
  }
  function actualizarTotal() {
    desenharGrelhaPrevia();
    var t = totalCotacao();
    $('frCotTotal').textContent = t == null ? '—' : fmt(t) + ' val.';
    var n = parseInt($('frNPerg').value, 10) || 0;
    $('frCotPerg').placeholder = n ? 'auto (' + fmt(20 / n) + ')' : 'auto (20 ÷ n)';
  }
  function desenharChaves() {
    var vs = ($('frVersoes').value || '').toUpperCase().split(/[\s,;]+/).filter(Boolean).slice(0, 6);
    if (!vs.length) vs = ['-'];
    var atual = {};
    Array.prototype.forEach.call(document.querySelectorAll('#frChaves textarea'), function (t) { atual[t.dataset.v] = t.value; });
    $('frChaves').innerHTML = vs.map(function (v) {
      return '<div class="col-12 col-md-' + (vs.length > 1 ? '6' : '12') + '"><label class="small text-muted">' + (v === '-' ? 'Chave' : 'Versão ' + esc(v)) +
        '</label><textarea class="form-control form-control-sm" rows="2" data-v="' + esc(v) + '" placeholder="Ex.: A B C D A…">' + esc(atual[v] || '') + '</textarea></div>';
    }).join('');
  }

  // ---------- Configuração e pedidos ----------
  function lerConfig(semValidar) {
    var disc = $('frDisciplina').value === '__outra__' ? $('frDisciplinaOutra').value : $('frDisciplina').value;
    var cfg = {
      tipo_avaliacao: $('frTipo').value, trimestre: $('frTrimestre') ? $('frTrimestre').value : '', disciplina: (disc || '').trim(),
      n_perguntas: parseInt($('frNPerg').value, 10), n_alternativas: parseInt($('frNAlt').value, 10),
      duracao_min: $('frDuracao').value, data: dataBR($('frData').value), hora_inicio: $('frHora').value, hora_fim: $('frHoraFim').value, sala: $('frSala').value,
      professor: $('frProfessor').value, versoes: $('frVersoes').value, instrucao_extra: $('frInstrucao').value,
      marcas_omr: $('frOmr').checked, codigo_barras: $('frBarras').checked, logo_escola: !!($('frLogoEscola') && $('frLogoEscola').checked), incluir_chave: $('frIncluirChave').checked
    };
    if ($('frModoCot').value === 'seccoes') cfg.seccoes = lerSeccoes();
    else if ($('frCotPerg').value.trim()) cfg.cotacao_pergunta = $('frCotPerg').value.trim();
    var ab = lerAbertas();
    if (ab.length) cfg.abertas = ab;
    var gab = {};
    Array.prototype.forEach.call(document.querySelectorAll('#frChaves textarea'), function (t) { if (t.value.trim()) gab[t.dataset.v] = t.value; });
    if (Object.keys(gab).length) cfg.gabaritos = gab;
    if (!semValidar && !cfg.tipo_avaliacao) throw new Error('Escolha o tipo de avaliação.');
    if (!semValidar && !cfg.disciplina) throw new Error('Escolha a disciplina.');
    return cfg;
  }
  function motivosMarcados() {
    return Array.prototype.filter.call(document.querySelectorAll('.fr-motivo'), function (c) { return c.checked; }).map(function (c) { return c.value; });
  }
  function pintarRegra(r) {
    if (!r) return;
    $('frRegraSempre').checked = !!r.verificar_sempre;
    Array.prototype.forEach.call(document.querySelectorAll('.fr-motivo'), function (c) { if (c.value !== 'outros') c.checked = (r.motivos || []).indexOf(c.value) >= 0; });
    $('frFaltasMin').value = r.faltas_minimo || '';
    if (r.cor_excluidos) $('frCor').value = String(r.cor_excluidos).toLowerCase();
    if (r.verificar_sempre) $('frRegraMsg').textContent = 'Verificação automática activa para esta escola.';
  }
  async function guardarRegra() {
    var ms = motivosMarcados().filter(function (m) { return m !== 'outros'; });
    $('frRegraMsg').textContent = 'A guardar…';
    try {
      var r = await pedir('regra/', { method: 'POST', headers: cab({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ verificar_sempre: $('frRegraSempre').checked, motivos: ms, faltas_minimo: $('frFaltasMin').value || 0, cor_excluidos: $('frCor').value }) });
      if (!r.ok) throw new Error(await mensagemErro(r));
      $('frRegraMsg').textContent = $('frRegraSempre').checked ? 'Regra guardada: o sistema verifica sempre antes de gerar.' : 'Verificação automática desactivada.';
    } catch (e) { $('frRegraMsg').textContent = e.message || 'Não foi possível guardar a regra.'; }
  }
  function corpo(formato, previa) {
    var e = $('frEscopo').value;
    // Pré-visualização sem aluno/turma escolhidos: mostra a folha em branco com as definições actuais.
    if (previa && ((e === 'aluno' && !$('frAluno').value) || (e === 'turma' && !$('frTurma').value) || (e === 'classe' && !classeActual()))) {
      return { formato: 'pdf', escopo: 'branco', copias: 1, ano_letivo: ano(), classe: classeActual(), config: lerConfig(false) };
    }
    var c = { formato: formato, escopo: e, ano_letivo: ano(), config: lerConfig(false) };
    if (e !== 'branco') {  // quem não faz a prova (mesma regra do Escudo Anti-IA)
      var ms = motivosMarcados();
      if (ms.length) { c.excluir = true; c.motivos = ms; c.faltas_minimo = $('frFaltasMin').value; c.outros = $('frOutros').value; }
      c.cor_excluidos = $('frCor').value;
      if (previa) c.previa = true;
    }
    if (e === 'aluno') { if (!$('frAluno').value) throw new Error('Escolha o aluno.'); c.aluno_id = $('frAluno').value; }
    else if (e === 'turma') { if (!$('frTurma').value) throw new Error('Escolha a turma.'); c.turma_id = $('frTurma').value; }
    else if (e === 'lista') { if (!$('frLista').files.length) throw new Error('Escolha o ficheiro da lista de alunos (.xlsx ou .csv).'); c.classe = classeActual(); }
    else if (e === 'classe') { if (!classeActual()) throw new Error('Escolha a classe.'); c.classe = classeActual(); c.area = areaActual(); }
    else { c.copias = parseInt($('frCopias').value, 10) || 0; c.classe = classeActual(); }
    return c;
  }
  function nomeFicheiro(r, padrao) {
    var cd = r.headers.get('Content-Disposition') || '', m = /filename\*=UTF-8''([^;]+)/.exec(cd) || /filename="([^"]+)"/.exec(cd);
    try { return m ? decodeURIComponent(m[1]) : padrao; } catch (_) { return padrao; }
  }
  async function gerar(formato, previa) {
    var btns = ['frBtnPdf', 'frBtnXlsx', 'frBtnPrevia'].map($);
    try {
      var c = corpo(previa ? 'pdf' : formato, previa);
      btns.forEach(function (b) { b.disabled = true; });
      estado('A gerar…');
      var r;
      if (c.escopo === 'lista') {  // lista importada: JSON + ficheiro (multipart)
        var fd = new FormData(); fd.append('dados', JSON.stringify(c)); fd.append('lista', $('frLista').files[0]);
        r = await fetch(API + 'gerar/', { method: 'POST', headers: cab(), body: fd });
      } else {
        r = await fetch(API + 'gerar/', { method: 'POST', headers: cab({ 'Content-Type': 'application/json' }), body: JSON.stringify(c) });
      }
      if (!r.ok) throw new Error(await mensagemErro(r));
      var blob = await r.blob();
      var total = r.headers.get('X-Total-Folhas') || '?';
      if (previa) {
        if (urlPrevia) URL.revokeObjectURL(urlPrevia);
        urlPrevia = URL.createObjectURL(blob);
        $('frPreviaFrame').src = urlPrevia + '#toolbar=1&view=FitH';
        $('frBlocoPrevia').classList.remove('d-none');
        $('frBlocoPrevia').scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else {
        var a = document.createElement('a');
        var u = URL.createObjectURL(blob);
        a.href = u; a.download = nomeFicheiro(r, 'Folha_Resposta.' + formato);
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
      }
      estado(total + ' folha(s) geradas.');
      guardar();
    } catch (e) {
      estado('');
      toast(e.message || 'Não foi possível gerar a folha.', 'danger');
    } finally {
      btns.forEach(function (b) { b.disabled = false; });
    }
  }

  function dataBR(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    return m ? m[3] + '/' + m[2] + '/' + m[1] : '';
  }
  // Sem valores inventados: data, hora inicial e duração só existem se o utilizador os indicar;
  // a hora final é calculada a partir deles.
  function aoEscolherData() { calcularHoraFim(); }

  // Hora final = hora inicial + duração (minutos); ao ajustar a hora final, a duração acompanha.
  function minutosDe(hhmm) { var m = /^(\d{1,2}):(\d{2})$/.exec(hhmm || ''); return m ? parseInt(m[1], 10) * 60 + parseInt(m[2], 10) : null; }
  function hhmmDe(total) { total = ((total % 1440) + 1440) % 1440; return ('0' + Math.floor(total / 60)).slice(-2) + ':' + ('0' + (total % 60)).slice(-2); }
  function calcularHoraFim() {
    var ini = minutosDe($('frHora').value), dur = parseInt($('frDuracao').value, 10);
    $('frHoraFim').value = (ini != null && dur > 0) ? hhmmDe(ini + dur) : '';
  }
  function aoEditarHoraFim() {
    var ini = minutosDe($('frHora').value), fim = minutosDe($('frHoraFim').value);
    if (ini != null && fim != null) $('frDuracao').value = ((fim - ini) + 1440) % 1440;
  }

  // Logotipo próprio da escola: opcional; não existe no Exame Final nem se a escola não o tiver carregado.
  function actualizarLogoEscola() {
    var cb = $('frLogoEscola'), dica = $('frLogoEscolaDica');
    if (!cb) return;
    var tem = !!(ctx && ctx.escola && ctx.escola.logo_proprio_disponivel);
    var exame = $('frTipo').value === 'EXAME';
    if ($('frTrimestreBox')) $('frTrimestreBox').style.display = exame ? 'none' : '';   // o Exame Final não tem trimestre
    cb.disabled = exame || !tem;
    if (cb.disabled) cb.checked = false;
    if (dica) dica.textContent = exame ? '(indisponível no Exame Final)' : (!tem ? '(a escola não tem logotipo próprio carregado)' : '');
  }

  function ligar() {
    if (ligado) return;
    ligado = true;
    $('frTipo').addEventListener('change', actualizarLogoEscola);
    $('frHora').addEventListener('input', calcularHoraFim);
    $('frHora').addEventListener('change', calcularHoraFim);
    $('frDuracao').addEventListener('input', calcularHoraFim);
    $('frHoraFim').addEventListener('change', aoEditarHoraFim);
    $('frData').addEventListener('click', function () { try { this.showPicker(); } catch (_) { /* navegador sem showPicker */ } });
    $('frData').addEventListener('change', aoEscolherData);
    $('frTurma').addEventListener('change', aoEscolherData);
    $('frHora').addEventListener('input', function () { this.dataset.auto = '0'; });
    $('frEscopo').addEventListener('change', mostrarCamposEscopo);
    $('frClasse').addEventListener('change', aoMudarClasse);
    $('frArea').addEventListener('change', aoMudarArea);
    $('frTurma').addEventListener('change', aoMudarTurma);
    $('frAluno').addEventListener('change', resumo);
    $('frAlunoBusca').addEventListener('input', preencherAlunos);
    $('frCopias').addEventListener('input', resumo);
    $('frDisciplina').addEventListener('change', function () { $('frDisciplinaOutra').classList.toggle('d-none', this.value !== '__outra__'); });
    $('frModoCot').addEventListener('change', function () {
      var s = this.value === 'seccoes';
      $('frBlocoSeccoes').classList.toggle('d-none', !s);
      $('frBlocoCotUnif').classList.toggle('d-none', s);
      if (s && !$('frSeccoesLista').children.length) {
        var n = parseInt($('frNPerg').value, 10) || 40;
        $('frSeccoesLista').appendChild(linhaSeccao(Math.ceil(n / 2), 0.5));
        $('frSeccoesLista').appendChild(linhaSeccao(n, 1));
      }
      actualizarTotal();
    });
    $('frAddSeccao').addEventListener('click', function () {
      if ($('frSeccoesLista').children.length >= 12) return toast('Máximo de 12 secções.', 'warning');
      $('frSeccoesLista').appendChild(linhaSeccao('', ''));
    });
    $('frSeccoesLista').addEventListener('click', function (ev) {
      var b = ev.target.closest('.fr-sec-rm'); if (b) { b.closest('.fr-seccao').remove(); actualizarTotal(); }
    });
    $('frSeccoesLista').addEventListener('input', actualizarTotal);
    $('frNAlt').addEventListener('change', desenharGrelhaPrevia);
    ['frNPerg', 'frCotPerg', 'frAbN', 'frAbCot'].forEach(function (id) { if ($(id)) $(id).addEventListener('input', actualizarTotal); });
    $('frVersoes').addEventListener('input', desenharChaves);
    $('frMOutros').addEventListener('change', function () { $('frBlocoOutros').classList.toggle('d-none', !this.checked); });
    $('frMTodos').addEventListener('click', function () {
      var cx = Array.prototype.slice.call(document.querySelectorAll('.fr-motivo')), todos = cx.every(function (c) { return c.checked; });
      cx.forEach(function (c) { c.checked = !todos; });
      $('frBlocoOutros').classList.toggle('d-none', !$('frMOutros').checked);
    });
    $('frGuardarRegra').addEventListener('click', guardarRegra);
    $('frBtnPdf').addEventListener('click', function () { gerar('pdf'); });
    $('frBtnXlsx').addEventListener('click', function () { gerar('xlsx'); });
    $('frBtnPrevia').addEventListener('click', function () { gerar('pdf', true); });
    $('frFecharPrevia').addEventListener('click', function () {
      $('frBlocoPrevia').classList.add('d-none'); $('frPreviaFrame').src = 'about:blank';
      if (urlPrevia) { URL.revokeObjectURL(urlPrevia); urlPrevia = null; }
    });
  }

  window.inicializarModulo_folha_resposta = async function () {
    if (!$('frApp')) return;
    ligar();
    estado('A carregar…');
    try {
      var r = await pedir('contexto/?ano=' + encodeURIComponent(ano()));
      if (!r.ok) throw new Error(await mensagemErro(r));
      ctx = await r.json();
      $('frTipo').innerHTML = '<option value="">-- Tipo de avaliação --</option>' + (ctx.tipos_avaliacao || []).map(function (t) { return '<option value="' + esc(t.codigo) + '">' + esc(t.rotulo) + '</option>'; }).join('');
      restaurar();
      // Trimestre da folha: por omissão o activo da escola; o utilizador pode escolher o 1.º, 2.º ou 3.º
      if ($('frTrimestre') && ctx.escola && ctx.escola.trimestre && !$('frTrimestre').dataset.tocado) $('frTrimestre').value = ctx.escola.trimestre;
      $('frTrimestre').addEventListener('change', function () { this.dataset.tocado = '1'; });
      pintarRegra(ctx.regra_exclusao);
      preencherClasses();
      mostrarCamposEscopo();
      actualizarTotal();
      desenharChaves();
      actualizarLogoEscola();
      estado(ctx.escola && ctx.escola.logotipo_disponivel === false ? 'Atenção: a escola não tem o logótipo oficial escolhido para documentos.' : '');
    } catch (e) {
      estado('');
      toast(e.message || 'Não foi possível carregar os dados.', 'danger');
    }
  };
})();
