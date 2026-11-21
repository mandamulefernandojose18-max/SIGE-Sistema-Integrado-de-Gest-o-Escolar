/* SIGE — Importar de ficheiro (alternativa ao preenchimento manual, em todas as páginas e sub-menus).
 *
 * Em cada página (barra no topo) e em cada janela/formulário (botão no cabeçalho) aparece "Importar de ficheiro".
 * O utilizador carrega um ficheiro .xlsx ou .csv; a primeira linha são os títulos das colunas e as restantes
 * linhas são os registos. O sistema associa cada coluna ao campo com o mesmo nome (rótulo, nome, id ou texto
 * de ajuda) e:
 *   - "Preencher campos" -> coloca a linha escolhida nos campos para o utilizador rever e guardar; ou
 *   - "Registar todas"   -> preenche e guarda uma a uma, usando o botão de guardar do próprio formulário
 *                           (portanto com as mesmas validações e regras de acesso da API).
 * Não cria dados: só usa o que está no ficheiro. A escolha da linha é um único seletor (altura constante,
 * independente do número de linhas). O ficheiro é lido no navegador; nada é enviado antes de guardar.
 */
(function () {
  'use strict';
  if (window.SIGE_IMPORTAR_FICHEIRO) return;

  var ROTULO_BOTAO = 'Importar de ficheiro';
  var RE_ACAO_GUARDAR = /guardar|gravar|registar|registo|salvar|adicionar|cadastrar|criar|enviar|submeter|confirmar|lan[cç]ar|atribuir/i;
  var RE_FILTRO = /^(filtro|pesquisa|busca|search|selectFiltro)|filtro/i;

  var estado = { dados: null, nomeFicheiro: '', alvo: null, mapa: [], linha: 0, aCorrer: false };
  var ultimoAbridor = null;
  var painelEl = null;

  // ---------- utilitários ----------
  function norm(s) {
    return String(s == null ? '' : s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '');
  }
  function aviso(msg, tipo) {
    if (typeof window.mostrarNotificacao === 'function') window.mostrarNotificacao(msg, tipo || 'info');
    else if (typeof window.mostrarToast === 'function') window.mostrarToast(msg, tipo || 'info');
  }
  function esperar(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function visivel(el) {
    if (!el) return false;
    var r = el.getClientRects();
    return !!(r && r.length) && getComputedStyle(el).visibility !== 'hidden';
  }
  function el(tag, cls, texto) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (texto != null) e.textContent = texto;
    return e;
  }

  // ---------- leitura do ficheiro ----------
  function lerCsv(texto) {
    texto = texto.replace(/^﻿/, '');
    var primeira = texto.split(/\r?\n/, 1)[0] || '';
    var delim = ';';
    var melhor = -1;
    [';', ',', '\t', '|'].forEach(function (d) {
      var n = primeira.split(d).length;
      if (n > melhor) { melhor = n; delim = d; }
    });
    var linhas = [], linha = [], campo = '', aspas = false;
    for (var i = 0; i < texto.length; i++) {
      var c = texto[i];
      if (aspas) {
        if (c === '"') { if (texto[i + 1] === '"') { campo += '"'; i++; } else aspas = false; }
        else campo += c;
      } else if (c === '"') aspas = true;
      else if (c === delim) { linha.push(campo); campo = ''; }
      else if (c === '\n' || c === '\r') {
        if (c === '\r' && texto[i + 1] === '\n') i++;
        linha.push(campo); campo = ''; linhas.push(linha); linha = [];
      } else campo += c;
    }
    if (campo !== '' || linha.length) { linha.push(campo); linhas.push(linha); }
    return linhas;
  }

  function valorCelula(v) {
    if (v == null) return '';
    if (v instanceof Date) return v.toISOString().slice(0, 10);
    if (typeof v === 'object') {
      if (v.richText) return v.richText.map(function (p) { return p.text; }).join('');
      if (v.result != null) return valorCelula(v.result);
      if (v.text != null) return String(v.text);
      if (v.hyperlink) return String(v.text || v.hyperlink);
      return '';
    }
    return String(v).trim();
  }

  async function lerFicheiro(file) {
    var nome = (file.name || '').toLowerCase();
    var linhas;
    if (/\.(csv|txt|tsv)$/.test(nome)) {
      linhas = lerCsv(await file.text());
    } else if (/\.xlsx$/.test(nome)) {
      if (!window.ExcelJS) throw new Error('Leitor de Excel indisponível. Use um ficheiro .csv.');
      var wb = new window.ExcelJS.Workbook();
      await wb.xlsx.load(await file.arrayBuffer());
      var ws = wb.worksheets[0];
      if (!ws) throw new Error('O ficheiro Excel não tem folhas.');
      linhas = [];
      ws.eachRow({ includeEmpty: false }, function (row) {
        var cels = [];
        for (var c = 1; c <= ws.columnCount; c++) cels.push(valorCelula(row.getCell(c).value));
        linhas.push(cels);
      });
    } else {
      throw new Error('Formato não suportado. Use .xlsx ou .csv (um .xls antigo deve ser gravado como .xlsx).');
    }
    linhas = linhas.filter(function (l) { return l.some(function (c) { return String(c).trim() !== ''; }); });
    if (linhas.length < 2) throw new Error('O ficheiro precisa de uma linha de títulos e pelo menos uma linha de dados.');
    var cab = linhas[0].map(function (c) { return String(c).trim(); });
    var dados = linhas.slice(1).map(function (l) {
      var o = {};
      cab.forEach(function (h, i) { if (h) o[h] = l[i] == null ? '' : String(l[i]).trim(); });
      return o;
    });
    return { cabecalhos: cab.filter(Boolean), linhas: dados };
  }

  // ---------- campos do formulário ----------
  function alvoActual(preferido) {
    if (preferido && document.body.contains(preferido)) return preferido;
    var modais = Array.prototype.filter.call(document.querySelectorAll('.modal.show'), visivel);
    if (modais.length) return modais[modais.length - 1];
    var vistas = Array.prototype.filter.call(document.querySelectorAll('.modulo-view'), visivel);
    return vistas[0] || null;
  }

  function rotuloDe(campo) {
    var partes = [];
    if (campo.id) {
      var l = document.querySelector('label[for="' + (window.CSS && CSS.escape ? CSS.escape(campo.id) : campo.id) + '"]');
      if (l) partes.push(l.textContent);
    }
    var lw = campo.closest('label');
    if (lw) partes.push(lw.textContent);
    var grupo = campo.closest('.mb-3,.mb-2,.form-group,[class*="col-"],.form-floating');
    if (grupo) { var l2 = grupo.querySelector('label'); if (l2) partes.push(l2.textContent); }
    partes.push(campo.getAttribute('aria-label') || '', campo.placeholder || '', campo.name || '', campo.id || '');
    return partes.filter(function (p) { return p && p.trim(); }).map(function (p) { return p.replace(/\*/g, '').trim(); });
  }

  function camposDe(alvo) {
    if (!alvo) return [];
    var lista = alvo.querySelectorAll('input, select, textarea');
    var out = [];
    Array.prototype.forEach.call(lista, function (c) {
      var t = (c.type || '').toLowerCase();
      if (['hidden', 'button', 'submit', 'reset', 'file', 'search', 'radio', 'image', 'password'].indexOf(t) >= 0) return;
      if (c.disabled || c.readOnly) return;
      if (c.closest('#sige-imp-painel')) return;
      if (c.classList.contains('sige-select-ano-lectivo')) return;
      if (RE_FILTRO.test(c.id || '') || RE_FILTRO.test(c.name || '')) return;
      if (c.closest('.sige-filtros, [data-sige-filtro]')) return;
      if (!visivel(c)) return;
      var rot = rotuloDe(c);
      if (!rot.length) return;
      out.push({ campo: c, rotulos: rot, chaves: rot.map(norm).filter(Boolean) });
    });
    return out;
  }

  function associar(cabecalhos, campos) {
    var usados = new Set(), mapa = [];
    cabecalhos.forEach(function (h) {
      var nh = norm(h);
      if (!nh) return;
      var achado = null;
      campos.forEach(function (f) { if (!achado && !usados.has(f) && f.chaves.indexOf(nh) >= 0) achado = f; });
      if (!achado && nh.length >= 4) {
        campos.forEach(function (f) {
          if (!achado && !usados.has(f) && f.chaves.some(function (k) { return k.length >= 4 && (k.indexOf(nh) >= 0 || nh.indexOf(k) >= 0); })) achado = f;
        });
      }
      if (achado) { usados.add(achado); mapa.push({ cabecalho: h, campo: achado.campo }); }
    });
    return mapa;
  }

  // ---------- preencher ----------
  function disparar(campo, nomes) {
    nomes.forEach(function (n) { campo.dispatchEvent(new Event(n, { bubbles: true })); });
  }
  function paraIso(v) {
    var m = /^(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{4})$/.exec(v);
    if (m) return m[3] + '-' + ('0' + m[2]).slice(-2) + '-' + ('0' + m[1]).slice(-2);
    return v;
  }
  function definir(campo, valor) {
    var tag = campo.tagName.toLowerCase(), tipo = (campo.type || '').toLowerCase();
    valor = valor == null ? '' : String(valor);
    if (tipo === 'checkbox') {
      campo.checked = /^(1|sim|s|yes|y|true|verdadeiro|x)$/i.test(valor.trim());
      disparar(campo, ['input', 'change']); return true;
    }
    if (tag === 'select') {
      var nv = norm(valor), op = null;
      Array.prototype.forEach.call(campo.options, function (o) {
        if (!op && (o.value === valor || norm(o.value) === nv || norm(o.textContent) === nv) && o.value !== '') op = o;
      });
      if (!op && nv) Array.prototype.forEach.call(campo.options, function (o) {
        if (!op && o.value !== '' && norm(o.textContent).indexOf(nv) >= 0) op = o;
      });
      if (!op) return valor === '';
      campo.value = op.value; disparar(campo, ['input', 'change']); return true;
    }
    if (tipo === 'date') valor = paraIso(valor);
    if (tipo === 'number') valor = valor.replace(/\s/g, '').replace(',', '.');
    var proto = tag === 'textarea' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    var desc = Object.getOwnPropertyDescriptor(proto, 'value');
    if (desc && desc.set) desc.set.call(campo, valor); else campo.value = valor;
    disparar(campo, ['input', 'change']);
    return true;
  }
  function preencher(indice) {
    var linha = estado.dados.linhas[indice], falhas = [];
    // Limpar primeiro os campos associados, para não ficar valor antigo de uma linha anterior.
    estado.mapa.forEach(function (m) {
      if (!document.body.contains(m.campo)) { falhas.push(m.cabecalho); return; }
      if (!definir(m.campo, linha[m.cabecalho])) falhas.push(m.cabecalho + ' = "' + linha[m.cabecalho] + '"');
    });
    return falhas;
  }

  // ---------- guardar ----------
  function botaoGuardar(alvo) {
    var cand = Array.prototype.slice.call(alvo.querySelectorAll('button, input[type=submit], a.btn'))
      .filter(function (b) { return visivel(b) && !b.disabled && !b.closest('#sige-imp-painel') && !b.hasAttribute('data-bs-dismiss'); });
    var sub = cand.filter(function (b) { return (b.type || '').toLowerCase() === 'submit'; })[0];
    if (sub) return sub;
    var porTexto = cand.filter(function (b) { return RE_ACAO_GUARDAR.test(b.textContent || b.value || ''); });
    var primario = porTexto.filter(function (b) { return /btn-(primary|success)/.test(b.className); })[0];
    return primario || porTexto[porTexto.length - 1] || null;
  }

  async function registarTodas(ui) {
    if (estado.aCorrer) return;
    var alvo = alvoActual(estado.alvo);
    var ehModal = !!(alvo && alvo.classList && alvo.classList.contains('modal'));
    var abridor = ehModal ? estado.abridor : null;
    var total = estado.dados.linhas.length, ok = 0, falhou = [];
    estado.aCorrer = true;
    ui.btnTodas.disabled = ui.btnPreencher.disabled = true;
    try {
      for (var i = 0; i < total; i++) {
        ui.estado.textContent = 'A registar ' + (i + 1) + ' de ' + total + '…';
        var a = alvoActual(ehModal ? null : estado.alvo);
        if (ehModal && (!a || !a.classList.contains('modal'))) {
          if (abridor && document.body.contains(abridor)) { abridor.click(); await esperar(700); a = alvoActual(null); }
        }
        if (!a || (ehModal && !a.classList.contains('modal'))) { falhou.push(i + 2); continue; }
        estado.alvo = a;
        estado.mapa = associar(estado.dados.cabecalhos, camposDe(a));
        var f = preencher(i);
        var btn = botaoGuardar(a);
        if (!btn) { falhou.push(i + 2); break; }
        btn.click();
        if (ehModal) {
          var fechou = false;
          for (var t = 0; t < 40 && !fechou; t++) { await esperar(250); fechou = !a.classList.contains('show') || !visivel(a); }
          if (fechou) ok++; else { falhou.push(i + 2); }
          await esperar(300);
        } else {
          await esperar(900);
          var invalido = a.querySelector('.is-invalid');
          if (invalido) falhou.push(i + 2); else ok++;
        }
        if (f.length && falhou.indexOf(i + 2) < 0) { /* valores sem correspondência foram deixados em branco */ }
      }
    } finally {
      estado.aCorrer = false;
      ui.btnTodas.disabled = ui.btnPreencher.disabled = false;
    }
    var msg = ok + ' de ' + total + ' linhas enviadas para guardar.';
    if (falhou.length) msg += ' Linhas do ficheiro com problema (confirme os dados): ' + falhou.slice(0, 15).join(', ') + (falhou.length > 15 ? '…' : '') + '.';
    ui.estado.textContent = msg;
    aviso(msg, falhou.length ? 'warning' : 'success');
  }

  // Procura na página o botão que abre o formulário de novo registo e abre-o.
  async function abrirFormularioDaPagina(vista) {
    var ver = vista && vista.classList && vista.classList.contains('modal') ? null : vista;
    if (!ver) return null;
    // Só botões inequívocos de "novo registo". Nunca gerar/lançar/atribuir/bloquear/aprovar, etc.
    var RE_SIM = /(^|\s)(\+\s*)?(novo|nova|adicionar|matricular|cadastrar)\b/i;
    var RE_ONC = /^\s*modal(novo|nova|adicionar)\w*\(/i;
    var RE_NAO = /eliminar|apagar|excluir|remover|exportar|descarregar|imprimir|pdf|excel|word|docx|filtr|pesquis|importar/i;
    var cand = Array.prototype.filter.call(ver.querySelectorAll('button, a.btn'), function (b) {
      if (!visivel(b) || b.disabled || b.closest('tr, .sige-imp-barra, #sige-imp-painel, .modal')) return false;
      var txt = (b.textContent || '').trim(), onc = b.getAttribute('onclick') || '';
      if (RE_NAO.test(txt) || RE_NAO.test(onc)) return false;
      return RE_SIM.test(txt) || RE_ONC.test(onc);
    });
    cand.sort(function (x, y) {
      function pts(b) { return (/btn-(primary|success)/.test(b.className) ? 2 : 0) + (/modal/i.test(b.getAttribute('onclick') || '') ? 1 : 0); }
      return pts(y) - pts(x);
    });
    for (var i = 0; i < cand.length && i < 3; i++) {
      cand[i].click();
      for (var t = 0; t < 16; t++) {
        await esperar(250);
        var m = alvoActual(null);
        if (m && m.classList.contains('modal') && camposDe(m).length) return { modal: m, botao: cand[i] };
      }
    }
    return null;
  }

  // ---------- modelo ----------
  async function descarregarModelo(alvo) {
    var campos = camposDe(alvo);
    if (!campos.length) { aviso('Abra primeiro o formulário (Novo/Adicionar) para gerar o modelo com as colunas certas.', 'info'); return; }
    var cab = campos.map(function (f) { return f.rotulos[0]; });
    if (window.ExcelJS) {
      var wb = new window.ExcelJS.Workbook();
      var ws = wb.addWorksheet('Importação');
      ws.addRow(cab);
      ws.getRow(1).font = { name: 'Times New Roman', size: 12, bold: true };
      ws.getRow(1).alignment = { horizontal: 'center', vertical: 'middle' };
      ws.columns.forEach(function (c, i) { c.width = Math.max(14, cab[i].length + 4); });
      var buf = await wb.xlsx.writeBuffer();
      baixar(new Blob([buf], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), 'modelo-importacao.xlsx');
    } else {
      baixar(new Blob(['﻿' + cab.join(';') + '\n'], { type: 'text/csv;charset=utf-8' }), 'modelo-importacao.csv');
    }
  }
  function baixar(blob, nome) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = nome;
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  // ---------- painel ----------
  function fechar() { if (painelEl) { painelEl.remove(); painelEl = null; } }

  function abrir(alvoPreferido) {
    fechar();
    var alvo = alvoActual(alvoPreferido);
    estado.alvo = alvo;
    estado.abridor = (alvo && alvo.classList && alvo.classList.contains('modal')) ? (alvo._sigeAbridor || ultimoAbridor) : null;
    estado.dados = null; estado.mapa = [];

    var fundo = el('div'); fundo.id = 'sige-imp-painel';
    fundo.style.cssText = 'position:fixed;inset:0;z-index:2100;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;padding:16px;';
    var caixa = el('div', 'bg-white rounded-3 shadow p-3');
    caixa.style.cssText = 'width:100%;max-width:520px;max-height:92vh;overflow:auto;';
    fundo.appendChild(caixa);

    var topo = el('div', 'd-flex align-items-center justify-content-between mb-2');
    var tit = el('h6', 'mb-0 fw-bold'); tit.innerHTML = '<i class="bi bi-file-earmark-arrow-up me-2"></i>';
    tit.appendChild(document.createTextNode(ROTULO_BOTAO));
    var x = el('button', 'btn-close'); x.type = 'button'; x.setAttribute('aria-label', 'Fechar'); x.onclick = fechar;
    topo.appendChild(tit); topo.appendChild(x); caixa.appendChild(topo);

    var ajuda = el('p', 'small text-muted mb-2', 'Carregue um ficheiro Excel (.xlsx) ou CSV. A primeira linha tem os nomes das colunas (iguais aos nomes dos campos do formulário) e cada linha seguinte é um registo.');
    caixa.appendChild(ajuda);

    var ficheiro = el('input', 'form-control form-control-sm mb-2'); ficheiro.type = 'file'; ficheiro.accept = '.xlsx,.csv,.txt,.tsv';
    caixa.appendChild(ficheiro);

    var info = el('div', 'small mb-2');
    caixa.appendChild(info);

    var linhaSel = el('div', 'mb-2'); linhaSel.style.display = 'none';
    var lbl = el('label', 'form-label small fw-semibold mb-1', 'Linha do ficheiro');
    var sel = el('select', 'form-select form-select-sm');
    linhaSel.appendChild(lbl); linhaSel.appendChild(sel); caixa.appendChild(linhaSel);

    var botoes = el('div', 'd-flex flex-wrap gap-2');
    var btnPreencher = el('button', 'btn btn-sm btn-primary', 'Preencher campos'); btnPreencher.type = 'button'; btnPreencher.disabled = true;
    var btnTodas = el('button', 'btn btn-sm btn-success', 'Registar todas'); btnTodas.type = 'button'; btnTodas.disabled = true;
    var btnModelo = el('button', 'btn btn-sm btn-outline-secondary', 'Descarregar modelo'); btnModelo.type = 'button';
    botoes.appendChild(btnPreencher); botoes.appendChild(btnTodas); botoes.appendChild(btnModelo);
    caixa.appendChild(botoes);

    var est = el('div', 'small mt-2');
    caixa.appendChild(est);
    var ui = { btnPreencher: btnPreencher, btnTodas: btnTodas, estado: est };

    btnModelo.onclick = async function () {
      var a = alvoActual(estado.alvo);
      if (!camposDe(a).length) {
        var ab = await abrirFormularioDaPagina(a);
        if (ab) { a = ab.modal; estado.alvo = a; estado.abridor = ab.botao; }
      }
      descarregarModelo(a);
    };

    ficheiro.onchange = async function () {
      var f = ficheiro.files && ficheiro.files[0];
      if (!f) return;
      info.textContent = 'A ler o ficheiro…'; est.textContent = '';
      try {
        estado.dados = await lerFicheiro(f);
      } catch (e) {
        estado.dados = null; info.textContent = ''; est.textContent = e.message || String(e);
        est.className = 'small mt-2 text-danger'; btnPreencher.disabled = btnTodas.disabled = true; return;
      }
      est.className = 'small mt-2';
      var a = alvoActual(estado.alvo); estado.alvo = a;
      var campos = camposDe(a);
      if (!campos.length) {
        // Nenhum formulário aberto: abre sozinho o formulário de "Novo/Adicionar/Matricular" da página.
        info.textContent = 'A abrir o formulário da página…';
        var aberto = await abrirFormularioDaPagina(a);
        if (aberto) { a = aberto.modal; estado.alvo = a; estado.abridor = aberto.botao; campos = camposDe(a); }
      }
      estado.mapa = associar(estado.dados.cabecalhos, campos);
      var n = estado.dados.linhas.length;
      if (!campos.length) {
        info.textContent = n + ' linha(s) lida(s), mas não há campos de formulário abertos nesta página. Abra o formulário (Novo/Adicionar) e use "' + ROTULO_BOTAO + '" dentro dele.';
        btnPreencher.disabled = btnTodas.disabled = true; return;
      }
      info.textContent = n + ' linha(s) lida(s). Colunas associadas a campos: ' + estado.mapa.length + ' de ' + estado.dados.cabecalhos.length + '.';
      var nao = estado.dados.cabecalhos.filter(function (h) { return !estado.mapa.some(function (m) { return m.cabecalho === h; }); });
      if (nao.length) est.textContent = 'Sem campo correspondente (ignoradas): ' + nao.join(', ') + '.';
      sel.innerHTML = '';
      estado.dados.linhas.forEach(function (l, i) {
        var o = el('option', '', 'Linha ' + (i + 2) + ' — ' + (l[estado.dados.cabecalhos[0]] || '(vazio)'));
        o.value = String(i); sel.appendChild(o);
      });
      linhaSel.style.display = '';
      btnPreencher.disabled = !estado.mapa.length;
      btnTodas.disabled = !estado.mapa.length || !botaoGuardar(a);
      if (!estado.mapa.length) est.textContent = 'Nenhuma coluna coincide com os campos. Use "Descarregar modelo" para obter os títulos certos.';
    };

    btnPreencher.onclick = function () {
      if (!estado.dados) return;
      var f = preencher(parseInt(sel.value || '0', 10));
      est.textContent = f.length ? 'Preenchido. Valores sem correspondência: ' + f.join('; ') : 'Campos preenchidos. Reveja e guarde.';
      aviso('Campos preenchidos a partir do ficheiro.', 'success');
    };
    btnTodas.onclick = function () {
      if (!estado.dados) return;
      var n = estado.dados.linhas.length;
      if (!window.confirm('Vai registar ' + n + ' linha(s) do ficheiro, uma a uma, neste formulário. Continuar?')) return;
      registarTodas(ui);
    };

    document.body.appendChild(fundo);
    painelEl = fundo;
  }

  // ---------- pontos de entrada: barra em cada página e botão em cada janela ----------
  function botao(pequeno) {
    var b = el('button', 'btn btn-sm btn-outline-secondary sige-imp-btn');
    b.type = 'button'; b.title = 'Preencher os campos a partir de um ficheiro Excel ou CSV';
    b.innerHTML = '<i class="bi bi-file-earmark-arrow-up me-1"></i>';
    b.appendChild(document.createTextNode(ROTULO_BOTAO));
    if (pequeno) b.style.cssText = 'margin-right:8px;';
    return b;
  }

  function garantirPontosEntrada() {
    Array.prototype.forEach.call(document.querySelectorAll('.modulo-view'), function (v) {
      if (v.querySelector(':scope > .sige-imp-barra')) return;
      var barra = el('div', 'sige-imp-barra d-flex justify-content-end mb-2');
      var b = botao(false);
      b.onclick = function () { abrir(v); };
      barra.appendChild(b);
      v.insertBefore(barra, v.firstChild);
    });
    Array.prototype.forEach.call(document.querySelectorAll('.modal.show'), function (m) {
      if (!m._sigeAbridor && ultimoAbridor) m._sigeAbridor = ultimoAbridor;
      var cab = m.querySelector('.modal-header');
      if (!cab || cab.querySelector('.sige-imp-btn')) return;
      // Só em formulários de registo (com texto livre/data); não em assistentes, geradores ou confirmações.
      var registo = camposDe(m).filter(function (f) {
        var t = (f.campo.type || '').toLowerCase();
        return f.campo.tagName === 'TEXTAREA' || ['text', 'email', 'tel', 'date'].indexOf(t) >= 0;
      });
      if (!registo.length) return;
      var b = botao(true);
      b.onclick = function () { abrir(m); };
      var fechaBtn = cab.querySelector('.btn-close,[data-bs-dismiss="modal"]');
      if (fechaBtn && fechaBtn.parentNode === cab) cab.insertBefore(b, fechaBtn); else cab.appendChild(b);
    });
  }

  document.addEventListener('click', function (e) {
    var t = e.target && e.target.closest ? e.target.closest('button, a, [onclick]') : null;
    if (!t || t.closest('.modal') || t.closest('#sige-imp-painel') || t.closest('.sige-imp-barra')) return;
    ultimoAbridor = t;
  }, true);

  var agendado = false;
  function agendar() {
    if (agendado) return; agendado = true;
    setTimeout(function () { agendado = false; try { garantirPontosEntrada(); } catch (_) {} }, 600);
  }
  function iniciar() {
    // Leve: só reage a novos blocos no #conteudo-modulo e à abertura de janelas (nunca a mudanças de classe).
    var raiz = document.getElementById('conteudo-modulo') || document.querySelector('main.content-area');
    if (raiz) new MutationObserver(agendar).observe(raiz, { childList: true });
    document.addEventListener('shown.bs.modal', agendar);
    agendar();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar); else iniciar();

  window.SIGE_IMPORTAR_FICHEIRO = { abrir: abrir, lerCsv: lerCsv, associar: associar, norm: norm };
})();
