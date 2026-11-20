/* SIGE — Filtro global anti-XSS (defesa em profundidade).
 * Todo HTML atribuído via innerHTML / outerHTML / insertAdjacentHTML passa por um parser inerte (<template>),
 * que remove vectores de execução antes de o HTML chegar ao DOM real:
 *  - <script>, <object>, <embed>, <base>, <meta http-equiv>, <link rel=import>;
 *  - atributos srcdoc e manipuladores de eventos que dispararam sozinhos (onerror, onload, onfocus, onmouseover...);
 *  - URLs javascript:/vbscript:/data:text/html em href, src, action, formaction, xlink:href.
 * Os manipuladores de clique/alteração usados pela própria aplicação (onclick, onchange, oninput, onsubmit, onkey*)
 * mantêm-se, porque o SIGE gera os seus botões com templates próprios. A defesa principal continua a ser escapar
 * os dados com escapeHtml(); este filtro cobre o que escapar falhar. */
(function () {
  'use strict';
  if (window.__sigeXssGuard) return;
  window.__sigeXssGuard = true;

  var TAGS_PROIBIDAS = 'script,object,embed,base,applet,noscript';
  var ATRIBUTOS_URL = ['href', 'src', 'action', 'formaction', 'xlink:href', 'data', 'poster', 'background'];
  var HANDLERS_PERMITIDOS = /^on(click|dblclick|change|input|submit|reset|keyup|keydown|keypress|blur|select|scroll|wheel|dragstart|dragover|dragenter|dragleave|drop|contextmenu)$/i;
  var URL_PERIGOSA = /^\s*(javascript|vbscript|data\s*:\s*text\/html)/i;

  function limparArvore(raiz) {
    var i, el, atributos, nome, valor;
    var proibidos = raiz.querySelectorAll(TAGS_PROIBIDAS + ',meta[http-equiv],link[rel~="import"]');
    for (i = 0; i < proibidos.length; i++) proibidos[i].remove();
    var todos = raiz.querySelectorAll('*');
    for (i = 0; i < todos.length; i++) {
      el = todos[i];
      atributos = Array.prototype.slice.call(el.attributes);
      for (var j = 0; j < atributos.length; j++) {
        nome = atributos[j].name.toLowerCase();
        valor = atributos[j].value;
        if (nome === 'srcdoc') { el.removeAttribute(atributos[j].name); continue; }
        if (nome.indexOf('on') === 0 && !HANDLERS_PERMITIDOS.test(nome)) { el.removeAttribute(atributos[j].name); continue; }
        if (ATRIBUTOS_URL.indexOf(nome) !== -1 && URL_PERIGOSA.test(valor.replace(/[\u0000- ]+/g, ''))) {
          el.removeAttribute(atributos[j].name);
        }
      }
    }
  }

  function higienizar(html) {
    if (html == null || typeof html !== 'string' || html.indexOf('<') === -1) return html;
    var t = document.createElement('template');
    t.innerHTML = html;
    limparArvore(t.content);
    return t.innerHTML;
  }
  window.sigeHigienizarHtml = higienizar;

  function embrulharSetter(proto, prop) {
    var d = Object.getOwnPropertyDescriptor(proto, prop);
    if (!d || !d.set || !d.configurable) return;
    Object.defineProperty(proto, prop, {
      configurable: true,
      enumerable: d.enumerable,
      get: d.get,
      set: function (v) { d.set.call(this, higienizar(v)); }
    });
  }
  try {
    embrulharSetter(Element.prototype, 'innerHTML');
    embrulharSetter(Element.prototype, 'outerHTML');
    var original = Element.prototype.insertAdjacentHTML;
    Element.prototype.insertAdjacentHTML = function (pos, html) { return original.call(this, pos, higienizar(html)); };
  } catch (e) { /* ambiente sem suporte: a defesa principal (escapeHtml + CSP) mantém-se */ }
})();
