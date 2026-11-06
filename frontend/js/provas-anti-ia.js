// =====================================================================
// SIGE - ESCUDO ANTI-IA DE PROVAS (interface refeita a partir da plataforma Pedagogia)
// Vistas: Painel · Carregar prova · Página da prova · Selos e cópias
// API: /api/v1/escudo/...  ·  QR/códigos abrem /ia/v/<prova>/<cópia>/...
// =====================================================================
(function () {
  'use strict';
  var API = '/api/v1/escudo/';
  var estado = { vista: 'painel', pid: null, catalogo: null, timers: [], pronto: false };

  function token() { try { return (window.state && window.state.token) || sessionStorage.getItem('sige_token') || localStorage.getItem('sige_token') || ''; } catch (_) { return ''; } }
  function cab() { var t = token(); return t ? { 'Authorization': 'Bearer ' + t } : {}; }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML.replace(/"/g, '&quot;'); }
  function $(sel, raiz) { return (raiz || document).querySelector(sel); }
  function $$(sel, raiz) { return Array.prototype.slice.call((raiz || document).querySelectorAll(sel)); }
  function ico(id) { return '<svg class="i"><use href="#i-' + id + '"/></svg>'; }
  function raiz() { return document.getElementById('escudoConteudo'); }
  function plural(n, a, b) { return n + ' ' + (n === 1 ? a : b); }

  async function api(caminho, opcoes) {
    var r = await fetch(API + caminho, Object.assign({ headers: cab() }, opcoes || {}));
    var tipo = r.headers.get('Content-Type') || '';
    if (tipo.indexOf('application/json') >= 0) {
      var j = await r.json();
      if (!r.ok || j.success === false) throw new Error(j.message || 'Não foi possível concluir o pedido.');
      return j;
    }
    if (!r.ok) throw new Error('Não foi possível concluir o pedido.');
    return r;
  }

  function limparTimers() {
    estado.timers.forEach(function (t) { if (t && t.limpar) t.limpar(); else clearInterval(t); });
    estado.timers = [];
  }

  function aviso(msg, tipo) {
    var el = $('#escudoAviso');
    if (!el) return;
    el.innerHTML = msg ? '<p class="aviso ' + (tipo || '') + '" role="status">' + ico(tipo === 'atencao' ? 'alert' : 'info') + '<span>' + esc(msg) + '</span></p>' : '';
    if (msg) el.scrollIntoView({ block: 'nearest' });
  }

  function marcarMenu() {
    $$('#escudoApp .menu [data-vista]').forEach(function (a) {
      var ativo = a.dataset.vista === estado.vista || (a.dataset.vista === 'painel' && (estado.vista === 'prova' || estado.vista === 'configurar'));
      if (ativo) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
  }

  async function ir(vista, pid) {
    limparTimers();
    estado.vista = vista; estado.pid = pid || null;
    marcarMenu();
    var c = raiz();
    if (!c) return;
    c.innerHTML = '<p class="suave">A carregar…</p>';
    try {
      if (vista === 'painel') await vistaPainel(c);
      else if (vista === 'nova') await vistaNova(c);
      else if (vista === 'prova') await vistaProva(c, pid);
      else if (vista === 'configurar') await vistaConfigurar(c, pid);
    } catch (e) {
      c.innerHTML = '<div id="escudoAviso"></div><div class="vazio">' + ico('alert') + '<strong>' + esc(e.message) + '</strong><button class="btn secundario" data-ir="painel">Voltar ao painel</button></div>';
    }
    estado.pronto = true;
    c.scrollIntoView({ block: 'nearest' });
  }

  // ---------------- relógio ----------------
  function iniciarRelogios() {
    var els = $$('#escudoConteudo .relogio[data-alvo]');
    if (!els.length) return;
    var pad = function (n) { return String(n).padStart(2, '0'); };
    var tick = function () {
      var recarregar = false;
      els.forEach(function (el) {
        var falta = Math.max(Math.floor((new Date(el.dataset.alvo) - Date.now()) / 1000), 0);
        var v = { d: Math.floor(falta / 86400), h: Math.floor(falta % 86400 / 3600), m: Math.floor(falta % 3600 / 60), s: falta % 60 };
        Object.keys(v).forEach(function (u) { var b = $('[data-u="' + u + '"]', el); if (b) b.textContent = u === 'd' ? String(v[u]) : pad(v[u]); });
        if (falta === 0) recarregar = true;
      });
      if (recarregar) { limparTimers(); setTimeout(function () { ir(estado.vista, estado.pid); }, 1500); }
    };
    tick();
    estado.timers.push(setInterval(tick, 1000));
  }
  function relogio(alvo, classe) {
    return '<div class="relogio ' + (classe || '') + '" data-alvo="' + esc(alvo) + '" role="timer" aria-label="Tempo até à libertação">' +
      '<div><b data-u="d">--</b><small>dias</small></div><div><b data-u="h">--</b><small>horas</small></div>' +
      '<div><b data-u="m">--</b><small>min</small></div><div><b data-u="s">--</b><small>seg</small></div></div>';
  }

  // ---------------- PAINEL ----------------
  async function vistaPainel(c) {
    var d = (await api('lista/')).data, r = d.resumo, p = d.proxima;
    var h = '<header class="cabecalho"><div><h1>Painel</h1><p class="suave">As tuas provas com proteção anti-IA, o período de proteção e quem já leu os códigos.</p></div>' +
      '<div class="acoes"><button class="btn" data-ir="nova">' + ico('plus') + ' Carregar prova</button></div></header><div id="escudoAviso"></div>';
    if (p) {
      h += '<section class="destaque" aria-label="Próxima libertação"><div><h2>Próxima prova a sair da proteção</h2><p class="titulo">' + esc(p.titulo) + '</p>' +
        '<p class="pequeno">' + esc(p.estado.texto) + ' (Maputo) · <a href="#" data-ir="prova" data-pid="' + esc(p.id) + '">abrir prova</a></p></div>' + relogio(p.estado.iso) + '</section>';
    }
    h += '<div class="metricas"><div class="metrica embargo"><span class="valor">' + r.embargo + '</span><span class="nome">Protegidas</span></div>' +
      '<div class="metrica livre"><span class="valor">' + r.libertadas + '</span><span class="nome">Concluídas</span></div>' +
      '<div class="metrica"><span class="valor">' + r.copias + '</span><span class="nome">Cópias numeradas</span></div>' +
      '<div class="metrica"><span class="valor">' + r.leituras + '</span><span class="nome">Leituras dos códigos</span></div></div>';
    if (d.provas.length) {
      h += '<div class="barra-filtros"><div class="segmentado" role="group" aria-label="Filtrar por estado">' +
        '<button type="button" data-valor="todas" aria-pressed="true">Todas (' + r.total + ')</button>' +
        '<button type="button" data-valor="embargo" aria-pressed="false">Sob embargo (' + r.embargo + ')</button>' +
        '<button type="button" data-valor="livre" aria-pressed="false">Libertadas (' + r.libertadas + ')</button></div>' +
        '<input class="pesquisa" type="search" placeholder="Procurar prova…" aria-label="Procurar prova" id="escudoPesquisa"></div><div class="lista-provas" id="escudoLista">';
      d.provas.forEach(function (x) {
        var e = x.estado, tile = e.sem_data ? '<div class="data-tile"><b>IA</b><small>anti</small></div>' :
          '<div class="data-tile ' + (e.liberada ? 'livre' : '') + '"><b>' + esc(x.dia) + '</b><small>' + esc(x.mes) + '</small></div>';
        h += '<a class="item-prova" href="#" data-ir="prova" data-pid="' + esc(x.id) + '" data-estado="' + (e.liberada ? 'livre' : 'embargo') +
          '" data-texto="' + esc((x.titulo + ' ' + x.disciplina + ' ' + x.classe + ' ' + x.id).toLowerCase()) + '">' + tile +
          '<div><div class="titulo">' + esc(x.titulo) + '</div><div class="meta">' + (x.disciplina ? '<span>' + esc(x.disciplina) + (x.classe ? ' · ' + esc(x.classe) : '') + '</span>' : '') +
          '<span>' + esc(e.texto) + '</span><span class="mono">' + esc(x.id) + '</span></div></div><div class="lado">' +
          (e.liberada ? '<span class="pilula livre">' + ico('unlock') + ' Libertada</span>' : '<span class="pilula embargo">' + ico('lock') + ' Sob embargo</span>') +
          '<span>' + plural(x.copias, 'cópia', 'cópias') + ' · ' + plural(x.leituras, 'leitura', 'leituras') + '</span></div></a>';
      });
      h += '</div><p class="vazio" id="escudoSemResultados" hidden>Nenhuma prova corresponde ao filtro.</p>';
    } else {
      h += '<div class="vazio">' + ico('file') + '<strong>Ainda não carregaste nenhuma prova</strong><span>Carrega um PDF ou Word, escolhe a data de libertação e gera as cópias seladas.</span>' +
        '<button class="btn" data-ir="nova">Carregar a primeira prova</button></div>';
    }
    c.innerHTML = h;
    iniciarRelogios();
    var filtro = 'todas', lista = $('#escudoLista');
    if (lista) {
      var aplicar = function () {
        var q = ($('#escudoPesquisa').value || '').trim().toLowerCase(), vis = 0;
        $$('.item-prova', lista).forEach(function (it) {
          var ok = (filtro === 'todas' || it.dataset.estado === filtro) && (!q || it.dataset.texto.indexOf(q) >= 0);
          it.hidden = !ok; if (ok) vis++;
        });
        $('#escudoSemResultados').hidden = vis > 0;
      };
      $$('.segmentado button', c).forEach(function (b) {
        b.addEventListener('click', function () {
          filtro = b.dataset.valor;
          $$('.segmentado button', c).forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
          aplicar();
        });
      });
      $('#escudoPesquisa').addEventListener('input', aplicar);
    }
  }

  // ---------------- CARREGAR PROVA ----------------
  function opcoes(lista) {
    return '<option value="">Escolhe…</option>' + lista.map(function (o) { return '<option>' + esc(o) + '</option>'; }).join('');
  }
  function dropzone(nome, accept, icone, titulo, sub) {
    return '<label class="dropzone" data-dropzone>' + ico(icone) + '<strong data-nome>' + titulo + '</strong><span class="suave pequeno">' + sub + '</span>' +
      '<input type="file" name="' + nome + '" accept="' + accept + '"></label>';
  }

  async function vistaNova(c) {
    if (!estado.catalogo) estado.catalogo = (await api('catalogo/')).data;
    var k = estado.catalogo;
    c.innerHTML = '<div class="migalhas"><a href="#" data-ir="painel">Painel</a> / <span>Carregar prova</span></div>' +
      '<header class="cabecalho"><div><h1>Carregar prova</h1><p class="suave">Carrega a prova, escolhe as proteções anti-IA e gera as cópias numeradas. Enquanto o período de proteção durar, o conteúdo não é entregue a ninguém.</p></div></header>' +
      '<div id="escudoAviso"></div><form class="grelha configurador" id="escudoFormNova" novalidate><div class="passos">' +
      '<section class="passo cartao"><h2>Ficheiros</h2>' +
      dropzone('prova', '.docx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'upload',
        'Escolhe ou larga aqui o ficheiro Word (.docx) ou PDF da prova', 'Até ' + k.max_mb + ' MB · o Word sai sempre em PDF') +
      dropzone('modelo', 'application/json,.json', 'qr', 'Ou um modelo com variantes (JSON): cada cópia com valores diferentes', 'Substitui o ficheiro. O gabarito de cada cópia é calculado.') +
      dropzone('gabarito', '.docx,.pdf,application/pdf', 'file', 'Gabarito ou resolução em Word ou PDF (opcional)', 'Fica cifrado e é libertado na mesma data') + '</section>' +
      '<section class="passo cartao"><h2>Variantes por cópia <small class="suave">(recomendado)</small></h2>' +
      '<p class="suave pequeno">Cada cópia sai com números diferentes: a resolução da IA ou do colega não serve a outra cópia e uma resposta copiada denuncia-se. No Word, escreve os valores como campos: <code>Uma resistência de {R1} Ω ligada a {U} V</code>. Podes fazer contas: <code>{U/R1:.2f}</code>.</p>' +
      '<label class="campo"><span>Variáveis <small>(uma por linha)</small></span><textarea name="variaveis_word" rows="4" placeholder="R1 = 2 a 12&#10;U = 6 a 24 passo 6&#10;k = 1,5; 2; 2,5"></textarea></label>' +
      '<label class="campo"><span>Condições <small>(opcional, uma por linha)</small></span><textarea name="condicoes_word" rows="2" placeholder="R1 != R2"></textarea></label>' +
      '<label class="campo"><span>Respostas para o gabarito <small>(opcional: n.º da questão e resposta)</small></span><textarea name="respostas_word" rows="3" placeholder="3: I = {U/R1:.2f} A&#10;4: P = {U**2/R1:.1f} W"></textarea></label></section>' +
      '<section class="passo cartao"><h2>Identificação</h2><div class="duas">' +
      '<label class="campo"><span>Tipo de avaliação</span><select name="tipo_avaliacao" required>' + opcoes(k.tipos) + '</select></label>' +
      '<label class="campo"><span>Trimestre <small>(opcional)</small></span><select name="trimestre"><option value="">—</option>' + k.trimestres.map(function (t) { return '<option>' + esc(t) + '</option>'; }).join('') + '</select></label></div>' +
      '<div class="duas"><label class="campo"><span>Disciplina</span><select name="disciplina" required>' + opcoes(k.disciplinas) + '</select></label>' +
      '<label class="campo"><span>Classe</span><select name="classe" required>' + opcoes(k.classes) + '</select></label></div>' +
      '<p class="suave pequeno">O título fica, por exemplo, «1.ª ACS de Física · 11.ª Classe · II Trimestre».</p></section>' +
      '<section class="passo cartao"><h2>Período de proteção <small class="suave">(opcional)</small></h2>' +
      '<p class="suave pequeno">Deixa vazio para aplicar só as proteções anti-IA, sem embargo: o conteúdo nunca é entregue por código.</p>' +
      '<label class="campo"><span>Proteger até (hora de Maputo)</span><input type="datetime-local" name="libertacao" id="escudoData"></label>' +
      '<div class="chips" aria-label="Atalhos de data"><button type="button" class="chip" data-dias="1">Amanhã 08:00</button><button type="button" class="chip" data-dias="7">Daqui a 1 semana</button>' +
      '<button type="button" class="chip" data-dias="14">Daqui a 2 semanas</button><button type="button" class="chip" data-dias="30">Daqui a 1 mês</button></div>' +
      '<p class="resumo-data" id="escudoResumoData" hidden></p>' +
      '<label class="caixa"><input type="checkbox" name="publicar_apos" checked><span>Depois da data, disponibilizar a prova e o gabarito a quem ler o código<small>Se desligares, o código só confirma que o embargo terminou.</small></span></label></section>' +
      '</div><aside class="lateral-config"><section class="cartao"><h2>O que vai acontecer</h2><ol class="linha-tempo">' +
      '<li><strong>Variantes</strong><time>Com campos {R1} no Word, cada cópia sai com números próprios e o gabarito de cada uma: a resolução de uma cópia não serve às outras.</time></li>' +
      '<li><strong>Rastreio</strong><time>O código da cópia em toda a página, QR em cada página e código de barras: qualquer foto que circule diz de que cópia saiu. Cada leitura regista o aparelho.</time></li>' +
      '<li><strong>Avisos</strong><time>Aviso «IA: não resolver» visível nas fotografias. Dissuade, mas não obriga a IA a recusar.</time></li>' +
      '<li><strong>Protecção</strong><time>O ficheiro fica cifrado e guardado em segurança até à data escolhida.</time></li></ol></section>' +
      '<button class="btn bloco" id="escudoContinuar">' + ico('shield') + ' Continuar para as proteções anti-IA</button></aside></form>';
    ligarFormNova(c);
  }

  function agoraMaputo() {
    var p = {};
    new Intl.DateTimeFormat('en-CA', { timeZone: 'Africa/Maputo', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
      .formatToParts(new Date()).forEach(function (x) { p[x.type] = x.value; });
    return Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute);
  }

  function ligarFormNova() {
    var form = $('#escudoFormNova'), campo = $('#escudoData'), resumo = $('#escudoResumoData');
    var dias = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado'];
    var meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
    var pad = function (n) { return String(n).padStart(2, '0'); };
    var escrever = function () {
      var m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(campo.value);
      if (!m) { resumo.hidden = true; return; }
      var alvo = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]), d = new Date(alvo), falta = Math.round((alvo - agoraMaputo()) / 86400000);
      var quando = falta < 0 ? 'Esta data já passou.' : falta === 0 ? 'Hoje.' : 'Daqui a ' + plural(falta, 'dia', 'dias') + '.';
      resumo.textContent = 'Libertada ' + dias[d.getUTCDay()] + ', ' + d.getUTCDate() + ' de ' + meses[d.getUTCMonth()] + ' de ' + d.getUTCFullYear() + ', às ' + m[4] + ':' + m[5] + ' (hora de Maputo). ' + quando;
      resumo.hidden = false;
    };
    $$('[data-dias]', form).forEach(function (b) {
      b.addEventListener('click', function () {
        var d = new Date(agoraMaputo() + (+b.dataset.dias) * 86400000);
        campo.value = d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()) + 'T08:00';
        escrever();
      });
    });
    campo.addEventListener('input', escrever);
    $$('[data-dropzone]', form).forEach(function (zona) {
      var input = $('input[type=file]', zona), nome = $('[data-nome]', zona), original = nome.textContent;
      var atualizar = function () {
        var f = input.files[0];
        zona.classList.toggle('cheia', !!f);
        nome.textContent = f ? f.name + ' (' + (f.size / 1048576).toFixed(2) + ' MB)' : original;
      };
      input.addEventListener('change', atualizar);
      ['dragenter', 'dragover'].forEach(function (t) { zona.addEventListener(t, function (e) { e.preventDefault(); zona.classList.add('sobre'); }); });
      ['dragleave', 'drop'].forEach(function (t) { zona.addEventListener(t, function () { zona.classList.remove('sobre'); }); });
      zona.addEventListener('drop', function (e) { e.preventDefault(); if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; atualizar(); } });
    });
    var enviar = async function () {
      var btn = $('#escudoContinuar');
      btn.disabled = true;
      aviso('');
      try {
        var r = await api('criar/', { method: 'POST', body: new FormData(form) });
        await ir('configurar', r.data.id);
        aviso('Prova cifrada e guardada. Define agora onde colocar os códigos.');
      } catch (e) {
        aviso(e.message, 'atencao');
        btn.disabled = false;
      }
    };
    $('#escudoContinuar').addEventListener('click', function (e) { e.preventDefault(); enviar(); });
    form.addEventListener('submit', function (e) { e.preventDefault(); enviar(); });
  }

  // ---------------- PÁGINA DA PROVA ----------------
  async function vistaProva(c, pid) {
    var p = (await api(pid + '/')).data, e = p.estado, n = Math.max(p.copias, 1);
    var h = '<div class="migalhas"><a href="#" data-ir="painel">Painel</a> / <span>' + esc(p.id) + '</span></div>' +
      '<header class="cabecalho"><div><h1>' + esc(p.titulo) + '</h1><p class="suave">' + (p.disciplina ? esc(p.disciplina) + (p.classe ? ' · ' + esc(p.classe) : '') + ' · ' : '') +
      plural(p.paginas, 'página', 'páginas') + ' · código <span class="mono">' + esc(p.id) + '</span></p></div>' +
      '<div class="acoes"><button class="btn" data-ir="configurar" data-pid="' + esc(p.id) + '">' + ico('qr') + ' Selos e cópias</button></div></header><div id="escudoAviso"></div>' +
      '<section class="cartao"><div class="estado-grande"><div>' +
      (e.sem_data ? '<span class="pilula embargo">' + ico('shield') + ' Protegida contra IA</span><h2>Sem data limite</h2><p class="suave">Só as proteções anti-IA: os códigos nunca entregam a prova. Define uma data abaixo se quiseres um embargo.</p>'
        : e.liberada ? '<span class="pilula livre">' + ico('unlock') + ' Libertada</span><h2>Embargo terminado</h2><p class="suave">Libertada em ' + esc(e.texto) + ' (hora de Maputo).</p>'
        : '<span class="pilula embargo">' + ico('lock') + ' Sob embargo</span><h2>Será libertada em ' + esc(e.texto) + '</h2><p class="suave">Hora de Maputo. Até lá, os códigos não entregam nada.</p>') +
      '</div>' + (!e.liberada && !e.sem_data ? relogio(e.iso, 'escuro') : '') + '</div>' +
      '<div class="barra-progresso ' + (e.liberada ? 'livre' : '') + '" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + p.progresso + '"><i data-pct="' + p.progresso + '"></i></div>' +
      '<div class="extremos"><span>Carregada em ' + esc(p.criada_texto) + '</span><span>' + p.progresso + '%</span><span>' + esc(e.texto) + '</span></div></section>';
    if (p.variantes) {
      h += '<section class="cartao"><h2>Variantes por cópia</h2><p class="sub">Cada cópia tem valores diferentes (' + p.variantes.perguntas + ' perguntas; variáveis: ' + (p.variantes.variaveis.join(', ') || 'nenhuma') + '). Há ' + p.variantes.combinacoes + ' combinações possíveis' +
        (p.copias > p.variantes.combinacoes ? ', <strong>menos do que as ' + p.copias + ' cópias geradas: haverá cópias repetidas</strong>' : '') + '.</p>' +
        '<button class="btn secundario" data-gabarito="' + esc(p.id) + '">' + ico('file') + ' Gabarito das ' + n + ' cópia' + (n === 1 ? '' : 's') + ' (só para o professor)</button></section>';
    }
    if (p.tem_chave) {
      h += '<section class="cartao"><h2>Conferir respostas de um aluno</h2><p class="sub">Indica a cópia do aluno e as respostas dele. O sistema diz quais estão certas para a cópia dele e quais coincidem com a chave de <strong>outra</strong> cópia (sinal de cópia ou de resolução feita para outra cópia).</p>' +
        '<form class="grelha-form" id="escudoFormConferir"><label class="campo"><span>Cópia n.º</span><input type="number" name="copia" min="1" max="' + n + '" required></label>' +
        '<label class="campo"><span>Respostas</span><input name="respostas" required placeholder="1: C; 2: 2,5 A; 3: B"></label><button class="btn">Conferir</button></form><div id="escudoConferido"></div></section>';
    }
    var cont = p.contagem;
    h += '<div class="abas" role="tablist" id="escudoAbas"><button class="aba" role="tab" aria-selected="true" data-alvo="aba-leituras">Leituras (' + p.leituras_lista.length + ')</button>' +
      '<button class="aba" role="tab" aria-selected="false" data-alvo="aba-registo">Registo</button><button class="aba" role="tab" aria-selected="false" data-alvo="aba-gerir">Gerir</button></div>' +
      '<section id="aba-leituras" data-painel-aba><div class="contagens"><span class="pilula embargo">' + cont.embargo + ' durante o embargo</span><span class="pilula livre">' + cont.libertada + ' depois da libertação</span>' +
      '<span class="pilula ' + (cont.invalida ? 'perigo' : '') + '">' + plural(cont.invalida, 'código não reconhecido', 'códigos não reconhecidos') + '</span></div>';
    if (p.leituras_lista.length) {
      var rot = { embargo: 'Lida durante o embargo', libertada: 'Lida depois da libertação', invalida: 'Código não reconhecido' };
      h += '<div class="tabela-rolar"><table><thead><tr><th>Quando (Maputo)</th><th>Cópia</th><th>Aparelho</th><th>Rede</th><th>Resultado</th></tr></thead><tbody>' +
        p.leituras_lista.map(function (l) {
          return '<tr><td>' + esc(l.quando_texto) + '</td><td>' + (l.codigo_copia ? '<span class="mono">' + esc(l.codigo_copia) + '</span>' : '<span class="suave">código geral</span>') +
            '</td><td>' + esc(l.aparelho || '—') + '</td><td class="mono">' + esc(l.rede || '—') + '</td><td>' + esc(rot[l.estado] || l.estado) + '</td></tr>';
        }).join('') + '</tbody></table></div>';
    } else {
      h += '<div class="vazio">' + ico('eye') + '<strong>Ainda ninguém leu os códigos</strong><span>Quando alguém ler um QR ou código de barras, aparece aqui com a cópia e a hora.</span></div>';
    }
    h += '</section><section id="aba-registo" data-painel-aba hidden><div class="cartao"><ol class="linha-tempo">' +
      p.eventos.map(function (ev) { return '<li><time>' + esc(ev.quando_texto) + '</time>' + esc(ev.texto) + '</li>'; }).join('') + '</ol></div></section>' +
      '<section id="aba-gerir" data-painel-aba hidden><div class="grelha dois"><div class="cartao"><h2>Mudar a data</h2><p class="sub">Os selos já impressos continuam válidos; o aviso impresso mostra a data antiga.</p>' +
      '<form id="escudoFormData"><label class="campo"><span>Nova data e hora (Maputo)</span><input type="datetime-local" name="libertacao" value="' + esc(p.campo_data) + '" required></label>' +
      '<button class="btn secundario">Guardar nova data</button></form>' + (!e.liberada ? '<p></p><button class="btn secundario" id="escudoLibertar">Libertar agora</button>' : '') + '</div>' +
      '<div class="cartao"><h2>Ligação dos códigos</h2><p class="sub">É para aqui que os QR e os códigos de barras levam.</p><dl class="lista-chave">' +
      '<div><dt>Endereço</dt><dd><code>' + esc(p.link) + '</code></dd></div><div><dt>Cópias válidas</dt><dd>' + p.copias + '</dd></div>' +
      '<div><dt>Depois da data</dt><dd>' + (p.publicar_apos ? 'entrega a prova' : 'só confirma') + '</dd></div><div><dt>Gabarito</dt><dd>' + (p.tem_gabarito ? 'guardado' : 'sem gabarito') + '</dd></div></dl></div></div>' +
      '<div class="perigo-zona"><h2>Apagar prova</h2><p class="sub">Remove a prova, os ficheiros cifrados e as leituras. Não se pode desfazer.</p><button class="btn perigo" id="escudoApagar">Apagar prova</button></div></section>';
    c.innerHTML = h;
    $$('[data-pct]', c).forEach(function (el) { requestAnimationFrame(function () { el.style.width = el.dataset.pct + '%'; }); });
    iniciarRelogios();
    var abas = $$('#escudoAbas .aba');
    abas.forEach(function (b) {
      b.addEventListener('click', function () {
        abas.forEach(function (x) { x.setAttribute('aria-selected', String(x === b)); });
        $$('[data-painel-aba]', c).forEach(function (s) { s.hidden = s.id !== b.dataset.alvo; });
      });
    });
    var g = $('[data-gabarito]', c);
    if (g) g.addEventListener('click', function () { descarregar('GET', pid + '/gabarito-copias/?n=' + n, null, 'gabarito_copias.pdf'); });
    var conf = $('#escudoFormConferir');
    if (conf) conf.addEventListener('submit', async function (ev) {
      ev.preventDefault();
      var saida = $('#escudoConferido'), fd = new FormData(conf);
      try { saida.innerHTML = resultadoConferir((await api(pid + '/conferir/', { method: 'POST', body: fd })).data, fd.get('respostas')); }
      catch (er) { saida.innerHTML = '<p class="aviso atencao">' + ico('alert') + '<span>' + esc(er.message) + '</span></p>'; }
    });
    $('#escudoFormData').addEventListener('submit', async function (ev) {
      ev.preventDefault();
      try { var r = await api(pid + '/data/', { method: 'POST', body: new FormData(ev.target) }); await ir('prova', pid); aviso(r.message); }
      catch (er) { aviso(er.message, 'atencao'); }
    });
    var lib = $('#escudoLibertar');
    if (lib) lib.addEventListener('click', async function () {
      if (!confirm('Libertar já? A prova passará a estar disponível a quem ler os códigos.')) return;
      try { var r = await api(pid + '/libertar/', { method: 'POST' }); await ir('prova', pid); aviso(r.message); } catch (er) { aviso(er.message, 'atencao'); }
    });
    $('#escudoApagar').addEventListener('click', async function () {
      if (!confirm('Apagar esta prova do cofre? Esta acção não se pode desfazer.')) return;
      try { await api(pid + '/apagar/', { method: 'POST' }); await ir('painel'); aviso('Prova apagada do cofre.'); } catch (er) { aviso(er.message, 'atencao'); }
    });
  }

  function resultadoConferir(r, respostas) {
    var h = '<hr><h2>Cópia n.º ' + r.serial + ': ' + r.certas + ' de ' + r.linhas.length + ' certas</h2><p class="suave">Respostas: ' + esc(respostas) + '</p>';
    if (r.alerta) h += '<p class="aviso atencao" role="alert">' + ico('alert') + '<span><strong>Forte sinal de cópia:</strong> as respostas batem com a chave da <strong>cópia ' + r.semelhanca[0][0] + '</strong> em ' + r.semelhanca[0][1] + ' de ' + r.total + ' questões, e com a chave da própria cópia só em ' + r.certas + '. Confirma com um oral.</span></p>';
    h += '<p class="suave">Semelhança com outras cópias: ' + r.semelhanca.map(function (s) { return 'cópia ' + s[0] + ': ' + s[1] + '/' + r.total; }).join(' · ') + ' · própria cópia: ' + r.certas + '/' + r.total + '</p>';
    h += r.suspeitas.length ? '<p class="aviso atencao" role="alert">' + ico('alert') + '<span>Respostas erradas para esta cópia, mas certas noutra: ' + r.suspeitas.slice(0, 5).map(function (s) { return '<strong>cópia ' + s[0] + '</strong> (' + plural(s[1], 'resposta', 'respostas') + ')'; }).join(', ') + '. Muitas coincidências com a mesma cópia indicam cópia ou uma resolução feita para essa cópia. Confirma com um oral.</span></p>'
      : '<p class="aviso" role="status">' + ico('check') + '<span>Nenhuma resposta errada coincide com a chave de outra cópia.</span></p>';
    h += '<div class="tabela-rolar"><table><thead><tr><th>Questão</th><th>Resposta do aluno</th><th>Certa nesta cópia</th><th>Resultado</th><th>Coincide com a cópia</th></tr></thead><tbody>' +
      r.linhas.map(function (l) {
        return '<tr><td>' + esc(l.n) + '</td><td>' + esc(l.dada) + '</td><td>' + esc(l.certa || '—') + '</td><td>' + (l.certo ? '<span class="pilula livre">Certa</span>' : '<span class="pilula ' + (l.outras.length ? 'perigo' : '') + '">Errada</span>') + '</td><td>' + esc(l.outras.join(', ') || '—') + '</td></tr>';
      }).join('') + '</tbody></table></div>';
    return h;
  }

  async function descarregar(metodo, caminho, corpo, nomeOmissao) {
    try {
      var r = await fetch(API + caminho, { method: metodo, headers: cab(), body: corpo });
      if (!r.ok) { var j = await r.json().catch(function () { return {}; }); throw new Error(j.message || 'Não foi possível gerar o ficheiro.'); }
      var nome = (/filename="([^"]+)"/.exec(r.headers.get('Content-Disposition') || '') || [])[1] || nomeOmissao;
      var url = URL.createObjectURL(await r.blob()), a = document.createElement('a');
      a.href = url; a.download = nome; document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
      return true;
    } catch (e) { aviso(e.message, 'atencao'); return false; }
  }

  // ---------------- SELOS E CÓPIAS ----------------
  async function vistaConfigurar(c, pid) {
    var k = (await api(pid + '/configurar/')).data, o = k.opcoes, marcas = JSON.parse(JSON.stringify(k.marcas)), paginaAtual = 1, sel = -1;
    var cx = function (nome, titulo, sub, extra) {
      return '<label class="caixa"><input type="checkbox" name="' + nome + '"' + (o[nome] ? ' checked' : '') + '><span>' + titulo + (sub ? '<small>' + sub + '</small>' : '') + (extra || '') + '</span></label>';
    };
    var pg = k.perguntas, resumoPerg = pg.total ? '<small><strong>' + plural(pg.total, 'pergunta detetada', 'perguntas detetadas') + ', QR em ' + pg.com_qr +
      (pg.sem_qr.length ? ' (sem espaço livre em ' + pg.sem_qr.join(', ') + ')' : '') + '.</strong></small>' : '<small><strong>Nenhuma pergunta numerada detetada (1., 2., Questão 3:…); só se aplicam os avisos gerais.</strong></small>';
    var h = '<div class="migalhas"><a href="#" data-ir="painel">Painel</a> / <a href="#" data-ir="prova" data-pid="' + esc(pid) + '">' + esc(k.titulo) + '</a> / <span>Selos</span></div>' +
      '<header class="cabecalho"><div><h1>Selos e cópias</h1><p class="suave">Clica na página para pôr um código; arrasta para o mover. Podes pôr vários, em qualquer parte.</p></div></header><div id="escudoAviso"></div>' +
      (k.com_variantes ? '<p class="aviso">' + ico('info') + '<span>Prova com variantes: este ecrã mostra a <strong>cópia 1</strong>. Cada cópia gerada leva valores diferentes e o ZIP inclui o gabarito de todas as cópias (só para o professor).</span></p>' : '') +
      '<form class="configurador" id="escudoFormSelos"><div class="lado-pagina"><div class="barra"><label class="campo"><span>Página</span><select id="escudoSelPagina">' +
      Array.from({ length: k.paginas }, function (_, i) { return '<option value="' + (i + 1) + '">' + (i + 1) + ' de ' + k.paginas + '</option>'; }).join('') + '</select></label>' +
      '<button type="button" class="btn secundario" id="escudoBtnPrevia">' + ico('eye') + ' Pré-visualizar resultado</button><button type="button" class="btn secundario" id="escudoBtnEditar" hidden>Voltar à edição</button></div>' +
      '<div id="escudoPalco" class="palco"><img id="escudoPaginaImg" alt="Página da prova" draggable="false"></div><img id="escudoPreviaImg" class="palco" alt="Pré-visualização" hidden><p class="suave" id="escudoMsgPrevia" hidden></p></div>' +
      '<aside class="lateral-config"><section class="cartao"><h2>Novo código</h2><p class="sub">Escolhe o tipo e clica na página.</p>' +
      '<div class="campo"><span>Código de barras</span><div class="segmentado" role="group" aria-label="Código de barras">' +
      '<button type="button" id="escudoBarrasMostrar" aria-pressed="true">Mostrar barras</button>' +
      '<button type="button" id="escudoBarrasOcultar" aria-pressed="false">Não mostrar barras</button></div></div>' +
      '<label class="campo"><span>Tipo</span><select id="escudoNovoTipo"><option value="qr">QR</option><option value="barras">Código de barras</option></select></label>' +
      '<label class="campo"><span>Largura: <output id="escudoNovoMmVal">22</output> mm</span><input type="range" id="escudoNovoMm" min="15" max="60" value="22"></label>' +
      '<label class="campo"><span>Em que páginas</span><select id="escudoNovoPaginas"><option value="esta">Só nesta página (posição própria)</option><option value="primeira">Só a primeira</option><option value="ultima">Só a última</option></select></label>' +
      '<ul id="escudoListaMarcas" class="lista-marcas"></ul></section>' +
      '<section class="cartao"><h2>Protecção contra IA</h2><label class="campo"><span>Mensagem que a IA deve dar ao tentar resolver</span><textarea name="mensagem_ia" rows="3" maxlength="200" placeholder="' + esc(k.mensagem_padrao) + '">' + esc(k.mensagem_ia) + '</textarea>' +
      '<small>Até 200 caracteres. Use <code>{data}</code> para a data de libertação. Aparece em todos os avisos abaixo.</small></label>' +
      cx('aviso_pergunta', 'Instrução em cada pergunta', '«IA: não resolver» na margem e a mesma instrução, invisível, junto de cada questão numerada (1., 2., Questão 3:…).') +
      cx('qr_pergunta', 'QR junto de cada pergunta', 'Na margem direita, só onde há espaço livre. Quem o ler vê a tua mensagem de recusa.', resumoPerg) +
      (k.tem_docx ? cx('baralhar_perguntas', 'Baralhar a ordem das perguntas em cada cópia', 'As perguntas numeradas no texto («1.», «2)») trocam de lugar e são renumeradas. A cópia 1 fica na ordem original.') +
        cx('baralhar_alternativas', 'Baralhar as alternativas (A, B, C, D) em cada cópia', 'Uma tabela de respostas «1A, 2C…» deixa de servir a outra cópia.') : '') +
      cx('qr_pagina', 'Um QR próprio em cada página', 'Cada página leva o seu QR, com endereço da página, num sítio livre escolhido só por essa página: a posição não é a mesma nas outras páginas nem nas outras cópias.') +
      cx('qr_marca_agua', 'QR como marca de água', 'Um QR grande e claro por trás de toda a página, com o endereço da cópia. Não se elimina recortando um canto.') +
      cx('aviso_foto', 'Aviso legível em fotografias', 'Faixa no topo, faixas laterais e marca de água «IA: não resolver».') +
      cx('aviso_ia', 'Texto invisível para assistentes de IA', 'Lido por quem envia o PDF; não aparece numa foto.') +
      cx('rasterizar', 'Converter páginas em imagem', 'Retira o texto copiável do PDF.') +
      cx('aviso_visivel', 'Rodapé com a data de embargo') + '</section>' +
      '<section class="cartao"><h2>Gerar</h2>' +
      '<label class="campo"><span>Formato de saída</span><select name="formato"><option value="pdf"' + (k.formato === 'pdf' ? ' selected' : '') + '>PDF</option>' +
      (k.tem_docx ? '<option value="word"' + (k.formato === 'word' ? ' selected' : '') + '>Word (.docx)</option><option value="ambos"' + (k.formato === 'ambos' ? ' selected' : '') + '>PDF e Word</option>' : '') + '</select>' +
      (k.tem_docx ? '<small>O Word sai editável, com os avisos, o QR de marca de água e o código da cópia; o PDF sai selado, com os QR por página e por pergunta. Com as duas opções, o ZIP leva as cópias nos dois formatos.</small>'
        : '<small>Para sair também em Word, carrega a prova em Word (.docx): esta prova só existe em PDF.</small>') + '</label>' +
      '<label class="campo"><span>Guião (resolução detalhada)</span><select name="guiao" id="escudoGuiaoSel"><option value="sem">Sem Guião</option>' +
      '<option value="com"' + (k.usa_guiao === 'com' ? ' selected' : '') + '>Com Guião</option></select>' +
      '<small>A IA do SIGE resolve a prova passo a passo, sem omitir cálculos, com as equações em forma matemática e a opção correcta no fim. Sai em PDF e em Word, só para o professor.</small></label>' +
      '<div id="escudoGuiaoCaixa" class="guiao-caixa" hidden></div>' +
      '<label class="campo"><span>Cópias numeradas</span><input type="number" name="copias" min="1" max="200" value="' + esc(k.copias) + '"></label>' +
      '<input type="hidden" name="url_base" value="' + esc(k.url_base) + '"><p class="suave pequeno">Os códigos abrem <code>' + esc(k.url_base) + '/v/' + esc(pid) + '</code>.</p>' +
      '<button class="btn bloco" id="escudoGerar">' + ico('file') + ' Gerar e descarregar</button></section>' +
      '<section class="cartao nota"><h2>O que isto garante</h2><ul><li><strong>Garantido:</strong> a prova guardada só é libertada na data; a ligação do QR não dá nada antes.</li>' +
      '<li><strong>Dissuasão, não bloqueio:</strong> quem fotografar as perguntas pode usá-las numa IA. O aviso legível e o texto invisível ajudam, mas dependem de a IA os respeitar.</li>' +
      '<li><strong>Rastreio:</strong> cada cópia tem número próprio e as leituras ficam registadas.</li></ul></section></aside></form>';
    c.innerHTML = h;
    var form = $('#escudoFormSelos'), palco = $('#escudoPalco'), img = $('#escudoPaginaImg'), lista = $('#escudoListaMarcas');
    var tipo = $('#escudoNovoTipo'), mm = $('#escudoNovoMm'), mmVal = $('#escudoNovoMmVal'), paginas = $('#escudoNovoPaginas');
    palco.style.aspectRatio = k.largura_mm + ' / ' + k.altura_mm;
    var visivel = function (m) { return typeof m.paginas !== 'number' || m.paginas === paginaAtual; };
    var rotulo = function (m) { return typeof m.paginas === 'number' ? 'pág. ' + m.paginas : m.paginas; };
    var dimMm = function (m) { return m.tipo === 'qr' ? [m.tamanho_mm, m.tamanho_mm] : [m.tamanho_mm, Math.max(8, m.tamanho_mm * 0.22) + 4 + 3.5]; };
    var limites = { qr: [15, 60, 22], barras: [30, 90, 50] };
    var carregarImagem = async function (alvo, caminho, opcoesFetch) {
      try {
        var r = await fetch(API + caminho, Object.assign({ headers: cab() }, opcoesFetch || {}));
        if (!r.ok) { var j = await r.json().catch(function () { return {}; }); throw new Error(j.message || 'Não foi possível carregar a imagem.'); }
        alvo.src = URL.createObjectURL(await r.blob());
        return true;
      } catch (e) { aviso(e.message, 'atencao'); return false; }
    };
    tipo.addEventListener('change', function () { var l = limites[tipo.value]; mm.min = l[0]; mm.max = l[1]; mm.value = l[2]; mmVal.textContent = l[2]; });
    mm.addEventListener('input', function () { mmVal.textContent = mm.value; });
    var fraccao = function (ev) { var r = palco.getBoundingClientRect(); return [Math.min(Math.max((ev.clientX - r.left) / r.width, 0), 1), Math.min(Math.max((ev.clientY - r.top) / r.height, 0), 1)]; };
    var desenhar = function () {
      $$('.marca', palco).forEach(function (n) { palco.removeChild(n); });
      lista.replaceChildren();
      marcas.forEach(function (m, i) {
        if (!visivel(m)) return;
        if (!m.oculta) {
          var d = dimMm(m), el = document.createElement('div');
          el.className = 'marca' + (i === sel ? ' sel' : '');
          el.style.left = (m.x * 100) + '%'; el.style.top = (m.y * 100) + '%';
          el.style.width = (d[0] / k.largura_mm * 100) + '%'; el.style.height = (d[1] / k.altura_mm * 100) + '%';
          el.textContent = m.tipo === 'qr' ? 'QR' : '|||| ||';
          el.addEventListener('pointerdown', function (ev) {
            ev.preventDefault(); ev.stopPropagation(); sel = i; el.setPointerCapture(ev.pointerId);
            var mover = function (e) { var f = fraccao(e); m.x = f[0]; m.y = f[1]; el.style.left = m.x * 100 + '%'; el.style.top = m.y * 100 + '%'; };
            var fim = function () { el.removeEventListener('pointermove', mover); el.removeEventListener('pointerup', fim); desenhar(); };
            el.addEventListener('pointermove', mover); el.addEventListener('pointerup', fim);
          });
          palco.appendChild(el);
        }
        // cada código tem «Ocultar/Mostrar» (guarda a posição) e «Remover» (apaga-o)
        var li = document.createElement('li'), txt = document.createElement('span'), acoes = document.createElement('span');
        txt.textContent = (m.tipo === 'qr' ? 'QR' : 'Barras') + ' · ' + m.tamanho_mm + ' mm · ' + rotulo(m) + (m.oculta ? ' · oculto' : '');
        if (m.oculta) txt.className = 'suave';
        var alt = document.createElement('button');
        alt.type = 'button'; alt.className = 'ligacao'; alt.textContent = m.oculta ? 'Mostrar' : 'Ocultar';
        alt.addEventListener('click', function () { if (m.oculta) delete m.oculta; else m.oculta = true; desenhar(); });
        var rm = document.createElement('button');
        rm.type = 'button'; rm.className = 'ligacao'; rm.textContent = 'Remover';
        rm.addEventListener('click', function () { marcas.splice(i, 1); sel = -1; desenhar(); });
        acoes.style.display = 'inline-flex'; acoes.style.gap = '12px';
        acoes.appendChild(alt); acoes.appendChild(rm);
        li.appendChild(txt); li.appendChild(acoes); lista.appendChild(li);
      });
      // estado do botão «Mostrar barras / Não mostrar barras»
      var barrasVisiveis = marcas.some(function (m) { return m.tipo === 'barras' && !m.oculta; });
      var bm = $('#escudoBarrasMostrar'), bo = $('#escudoBarrasOcultar');
      if (bm && bo) { bm.setAttribute('aria-pressed', String(barrasVisiveis)); bo.setAttribute('aria-pressed', String(!barrasVisiveis)); }
    };
    var ativas = function () { return marcas.filter(function (m) { return !m.oculta; }); };
    var barrasMostrar = $('#escudoBarrasMostrar'), barrasOcultar = $('#escudoBarrasOcultar');
    if (barrasMostrar && barrasOcultar) {
      barrasMostrar.addEventListener('click', function () {
        var existentes = marcas.filter(function (m) { return m.tipo === 'barras'; });
        if (existentes.length) existentes.forEach(function (m) { delete m.oculta; });
        else marcas.push({ tipo: 'barras', paginas: 'primeira', x: 0.5, y: 0.91, tamanho_mm: 50 });  // a posição predefinida
        desenhar();
      });
      barrasOcultar.addEventListener('click', function () {
        marcas.forEach(function (m) { if (m.tipo === 'barras') m.oculta = true; });
        desenhar();
      });
    }
    palco.addEventListener('click', function (ev) {
      if (ev.target.closest('.marca')) return;
      var f = fraccao(ev);
      marcas.push({ tipo: tipo.value, paginas: paginas.value === 'esta' ? paginaAtual : paginas.value, x: f[0], y: f[1], tamanho_mm: parseFloat(mm.value) });
      sel = marcas.length - 1; desenhar();
    });
    $('#escudoSelPagina').addEventListener('change', async function (ev) {
      paginaAtual = parseInt(ev.target.value, 10); sel = -1; desenhar();
      await carregarImagem(img, pid + '/pagina/' + paginaAtual + '.png');
    });
    var dados = function () {
      var fd = new FormData(form);
      fd.set('marcas', JSON.stringify(ativas())); fd.set('pagina', String(paginaAtual));  // os ocultos não vão
      return fd;
    };
    var previa = $('#escudoPreviaImg'), msg = $('#escudoMsgPrevia'), bPrevia = $('#escudoBtnPrevia'), bEditar = $('#escudoBtnEditar');
    bPrevia.addEventListener('click', async function () {
      msg.hidden = false; msg.textContent = 'A gerar pré-visualização…';
      var ok = await carregarImagem(previa, pid + '/previa/', { method: 'POST', body: dados() });
      if (!ok) { msg.hidden = true; return; }
      previa.hidden = false; palco.hidden = true; bEditar.hidden = false; bPrevia.hidden = true; msg.hidden = true;
    });
    bEditar.addEventListener('click', function () { previa.hidden = true; palco.hidden = false; bEditar.hidden = true; bPrevia.hidden = false; });
    form.addEventListener('submit', async function (ev) {
      ev.preventDefault();
      if (guiaoSel.value === 'com' && !(guiaoEstado && guiaoEstado.pronto)) {
        aviso('O Guião ainda não está pronto: carrega em «Gerar Guião com a IA» e espera, ou escolhe «Sem Guião».', 'atencao');
        return;
      }
      if (!ativas().length && !confirm('Não colocaste nenhum código. Gerar mesmo assim?')) return;
      var btn = $('#escudoGerar'); btn.disabled = true; aviso('A gerar as cópias seladas…');
      var ok = await descarregar('POST', pid + '/gerar/', dados(), 'copias.zip');
      btn.disabled = false;
      if (ok) aviso('Cópias geradas e descarregadas.');
    });
    // ---- Guião (resolução detalhada pela IA do SIGE) ----
    var guiaoSel = $('#escudoGuiaoSel'), guiaoCaixa = $('#escudoGuiaoCaixa'), guiaoTimer = null, guiaoEstado = k.guiao;
    var fmtUsd = function (v) { return v == null ? '' : 'US$ ' + v.toFixed(2).replace('.', ','); };
    var pararGuiaoTimer = function () { if (guiaoTimer) { clearInterval(guiaoTimer); guiaoTimer = null; } };
    estado.timers.push({ limpar: pararGuiaoTimer });
    var pintarGuiao = function (g) {
      guiaoEstado = g;
      if (guiaoSel.value !== 'com') { guiaoCaixa.hidden = true; return; }
      guiaoCaixa.hidden = false;
      var h = '';
      if (!g.disponivel) {
        h = '<p class="aviso atencao">' + ico('alert') + '<span>A IA do SIGE ainda não está activada neste servidor. O administrador tem de configurar a chave da IA. Enquanto isso, escolhe «Sem Guião».</span></p>';
      } else if (g.estado === 'gerando') {
        h = '<p class="aviso">' + ico('clock') + '<span><strong>A IA está a resolver a prova…</strong> Pode demorar alguns minutos (provas longas, até uns 10). Podes esperar aqui: o estado actualiza-se sozinho.</span></p>';
      } else if (g.pronto) {
        h = '<p class="aviso">' + ico('check') + '<span><strong>Guião pronto</strong> · ' + plural(g.questoes.length, 'questão', 'questões') + (g.custo_usd != null ? ' · custo aproximado ' + fmtUsd(g.custo_usd) : '') +
          (g.revisto ? ' · revisto por ti' : '') + '. <strong>Confere-o antes de usar: foi escrito por IA e pode errar.</strong></span></p>' +
          '<div class="tabela-rolar"><table><thead><tr><th>Q.</th><th>Opção</th><th>Resposta</th><th>Confiança</th></tr></thead><tbody>' +
          g.questoes.map(function (q) {
            var opcoes = ['', 'A', 'B', 'C', 'D', 'E'].map(function (o) { return '<option value="' + o + '"' + (o === (q.opcao_correcta || '') ? ' selected' : '') + '>' + (o || '—') + '</option>'; }).join('');
            var conf = q.confianca === 'baixa' ? '<span class="pilula perigo" title="' + esc(q.observacao) + '">Baixa</span>' : q.confianca === 'media' ? '<span class="pilula embargo" title="' + esc(q.observacao) + '">Média</span>' : '<span class="pilula livre">Alta</span>';
            return '<tr><td>' + esc(q.numero) + '</td><td>' + (q.tipo === 'escolha_multipla' || q.opcao_correcta ? '<select data-guiao-opcao="' + esc(q.numero) + '" aria-label="Opção correcta da questão ' + esc(q.numero) + '">' + opcoes + '</select>' : '<span class="suave">—</span>') +
              '</td><td>' + esc((q.resposta_final || '').replace(/\$/g, '')) + '</td><td>' + conf + '</td></tr>';
          }).join('') + '</tbody></table></div>' +
          '<div class="acoes"><button type="button" class="btn secundario pequeno" data-guiao-baixar="pdf">' + ico('file') + ' Guião em PDF</button>' +
          '<button type="button" class="btn secundario pequeno" data-guiao-baixar="word">' + ico('file') + ' Guião em Word</button>' +
          '<button type="button" class="btn secundario pequeno" data-guiao-gerar>Voltar a gerar</button></div>' +
          '<p class="suave pequeno">Gerações hoje: ' + g.geracoes_24h + ' de ' + g.limite_24h + '. Se mudares a opção correcta de uma questão, o Guião passa a usá-la.</p>';
      } else {
        h = (g.estado === 'erro' ? '<p class="aviso atencao">' + ico('alert') + '<span>' + esc(g.mensagem || 'Não foi possível gerar o Guião.') + '</span></p>' : '') +
          '<p class="suave pequeno">A IA do SIGE lê a prova e escreve a resolução completa (' + esc(g.modelo) + '). Demora alguns minutos e tem um custo aproximado de <strong>US$ 0,20 a 0,60</strong> por prova. ' +
          'O texto da prova é enviado à IA só quando carregares em «Gerar Guião».</p>' +
          '<button type="button" class="btn bloco" data-guiao-gerar>' + ico('shield') + ' Gerar Guião com a IA</button>';
      }
      guiaoCaixa.innerHTML = h;
      if (g.estado === 'gerando' && !guiaoTimer) {
        guiaoTimer = setInterval(async function () {
          try { var r = await api(pid + '/guiao/'); if (r.data.estado !== 'gerando') pararGuiaoTimer(); pintarGuiao(r.data); } catch (_) { /* tenta no próximo ciclo */ }
        }, 5000);
      }
      if (g.estado !== 'gerando') pararGuiaoTimer();
    };
    guiaoSel.addEventListener('change', function () { pintarGuiao(guiaoEstado); });
    guiaoCaixa.addEventListener('click', async function (ev) {
      var b = ev.target.closest('button');
      if (!b) return;
      if (b.hasAttribute('data-guiao-gerar')) {
        if (guiaoEstado.pronto && !confirm('Já existe um Guião (e a tua revisão). Gerar outro substitui-o e tem custo. Continuar?')) return;
        b.disabled = true;
        try { var r = await api(pid + '/guiao/gerar/', { method: 'POST' }); pintarGuiao(r.data); }
        catch (e) { aviso(e.message, 'atencao'); b.disabled = false; }
      } else if (b.dataset.guiaoBaixar) {
        descarregar('GET', pid + '/guiao/descarregar/?formato=' + b.dataset.guiaoBaixar, null, 'guiao.' + (b.dataset.guiaoBaixar === 'word' ? 'docx' : 'pdf'));
      }
    });
    guiaoCaixa.addEventListener('change', async function (ev) {
      var s = ev.target.closest('select[data-guiao-opcao]');
      if (!s) return;
      var fd = new FormData(); fd.append('numero', s.dataset.guiaoOpcao); fd.append('opcao_correcta', s.value);
      try { var r = await api(pid + '/guiao/corrigir/', { method: 'POST', body: fd }); pintarGuiao(r.data); aviso('Opção da questão ' + s.dataset.guiaoOpcao + ' actualizada no Guião.'); }
      catch (e) { aviso(e.message, 'atencao'); }
    });
    pintarGuiao(k.guiao);
    await carregarImagem(img, pid + '/pagina/1.png');
    desenhar();
  }

  // ---------------- eventos globais ----------------
  function ligar() {
    var app = document.getElementById('escudoApp');
    if (!app || app.dataset.ligado === '1') return;
    app.dataset.ligado = '1';
    app.addEventListener('click', function (ev) {
      var alvo = ev.target.closest('[data-ir]');
      if (alvo) { ev.preventDefault(); ir(alvo.dataset.ir, alvo.dataset.pid); return; }
      var menu = ev.target.closest('[data-vista]');
      if (menu) { ev.preventDefault(); ir(menu.dataset.vista); }
    });
    // O router do SIGE só mostra o módulo depois de escolher o Ano Lectivo: desenha o painel quando ficar visível.
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) {
        if (!estado.pronto && es.some(function (e) { return e.isIntersecting; })) ir('painel');
      }).observe(app);
    }
  }

  window.inicializarModulo_provas_anti_ia = function () {
    ligar();
    return ir('painel');
  };
})();
