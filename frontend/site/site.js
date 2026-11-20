// SIGE — site público: navegação, rodapé, verificação de cookies e formulário de contacto. Sem dependências além do Bootstrap local.
(function () {
  'use strict';
  var PAGINAS = [
    { href: '/', texto: 'Início', id: 'inicio' },
    { href: '/#funcionalidades', texto: 'Funcionalidades', id: 'func' },
    { href: '/#seguranca', texto: 'Segurança', id: 'seg' },
    { href: '/contacto.html', texto: 'Contacto', id: 'contacto' }
  ];

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  function cabecalho() {
    var alvo = document.getElementById('site-cabecalho');
    if (!alvo) return;
    var atual = document.body.getAttribute('data-pagina') || '';
    alvo.innerHTML =
      '<a class="salta" href="#conteudo">Saltar para o conteúdo</a>' +
      '<nav class="navbar navbar-expand-lg site-nav" aria-label="Navegação principal"><div class="container">' +
      '<a class="navbar-brand" href="/"><img src="/img/logo-sige.png" alt="" width="36" height="36"><span>SIGE</span></a>' +
      '<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#menuSite" aria-controls="menuSite" aria-expanded="false" aria-label="Abrir menu"><span class="navbar-toggler-icon"></span></button>' +
      '<div class="collapse navbar-collapse" id="menuSite"><ul class="navbar-nav ms-auto align-items-lg-center gap-lg-1">' +
      PAGINAS.map(function (p) { return '<li class="nav-item"><a class="nav-link' + (p.id === atual ? ' active' : '') + '"' + (p.id === atual ? ' aria-current="page"' : '') + ' href="' + p.href + '">' + p.texto + '</a></li>'; }).join('') +
      '<li class="nav-item ms-lg-2 mt-2 mt-lg-0"><a class="btn btn-sige" href="/login"><i class="bi bi-box-arrow-in-right me-1"></i>Entrar</a></li>' +
      '</ul></div></div></nav>';
  }

  function rodape() {
    var alvo = document.getElementById('site-rodape');
    if (!alvo) return;
    alvo.innerHTML =
      '<footer class="site-rodape"><div class="container"><div class="row g-4">' +
      '<div class="col-md-5"><h3>SIGE — Sistema Integrado de Gestão Escolar</h3><p>Plataforma de gestão escolar para Moçambique, alinhada com o padrão oficial de avaliação do MEC.</p></div>' +
      '<div class="col-6 col-md-3"><h3>Navegar</h3><ul><li><a href="/">Início</a></li><li><a href="/#funcionalidades">Funcionalidades</a></li><li><a href="/#seguranca">Segurança</a></li><li><a href="/contacto.html">Contacto</a></li><li><a href="/login">Entrar no sistema</a></li></ul></div>' +
      '<div class="col-6 col-md-4"><h3>Legal</h3><ul><li><a href="/privacidade.html">Política de privacidade</a></li><li><a href="/termos.html">Termos de uso</a></li><li><a href="/privacidade.html#cookies">Política de cookies</a></li><li><a href="#" data-cookies-abrir>Gerir cookies</a></li></ul></div>' +
      '</div><div class="linha d-flex flex-wrap justify-content-between gap-2"><span>© <span id="ano-site"></span> SIGE. Todos os direitos reservados.</span><span>sigesaas.duckdns.org</span></div></div></footer>';
    var a = document.getElementById('ano-site');
    if (a) a.textContent = new Date().getFullYear();
  }

  // ------------------------------------------------------------------ verificação de cookies
  var CHAVE = 'sige_cookies';
  function lerEscolha() {
    try { var v = JSON.parse(localStorage.getItem(CHAVE) || 'null'); return v && v.versao === 1 ? v : null; } catch (e) { return null; }
  }
  function gravarEscolha(preferencias) {
    var v = { versao: 1, essenciais: true, preferencias: !!preferencias, data: new Date().toISOString() };
    try { localStorage.setItem(CHAVE, JSON.stringify(v)); } catch (e) { /* armazenamento bloqueado: a faixa volta a aparecer */ }
    // cópia em cookie (só a escolha; sem identificadores) para que o servidor a possa respeitar
    document.cookie = 'sige_consent=' + (preferencias ? 'prefs' : 'essenciais') + '; max-age=31536000; path=/; SameSite=Lax' + (location.protocol === 'https:' ? '; Secure' : '');
    if (!preferencias) { try { localStorage.removeItem('sige_tema'); localStorage.removeItem('sige_idioma'); } catch (e) { /* ignora */ } }
    document.dispatchEvent(new CustomEvent('sige:cookies', { detail: v }));
    return v;
  }
  function criarFaixa() {
    var f = document.createElement('div');
    f.className = 'cookie-faixa'; f.id = 'cookieFaixa'; f.setAttribute('role', 'dialog'); f.setAttribute('aria-live', 'polite'); f.setAttribute('aria-label', 'Verificação de cookies'); f.hidden = true;
    f.innerHTML = '<div class="container"><div class="row align-items-center g-2">' +
      '<div class="col-lg-7"><p><strong><i class="bi bi-shield-check me-1"></i>Cookies e privacidade.</strong> Usamos cookies essenciais (sessão e segurança) e, com o seu consentimento, cookies de preferências. Não usamos publicidade nem rastreadores de terceiros. <a href="/privacidade.html#cookies">Saber mais</a>.</p></div>' +
      '<div class="col-lg-5 d-flex flex-wrap gap-2 justify-content-lg-end">' +
      '<button type="button" class="btn btn-outline-secondary btn-sm" data-cookies-acao="personalizar">Personalizar</button>' +
      '<button type="button" class="btn btn-outline-primary btn-sm" data-cookies-acao="essenciais">Apenas essenciais</button>' +
      '<button type="button" class="btn btn-primary btn-sm" data-cookies-acao="aceitar">Aceitar tudo</button></div></div></div>';
    document.body.appendChild(f);
    var m = document.createElement('div');
    m.className = 'cookie-modal-fundo'; m.id = 'cookieModal'; m.hidden = true;
    m.innerHTML = '<div class="cookie-modal" role="dialog" aria-modal="true" aria-labelledby="cookieTitulo"><h2 class="h5" id="cookieTitulo">Preferências de cookies</h2>' +
      '<div class="opcao"><div class="form-check form-switch"><input class="form-check-input" type="checkbox" id="ckEss" checked disabled><label class="form-check-label fw-semibold" for="ckEss">Essenciais (sempre activos)</label></div><small class="text-muted">Mantêm a sessão iniciada, protegem contra fraude e guardam esta escolha. Sem eles o sistema não funciona.</small></div>' +
      '<div class="opcao"><div class="form-check form-switch"><input class="form-check-input" type="checkbox" id="ckPref"><label class="form-check-label fw-semibold" for="ckPref">Preferências</label></div><small class="text-muted">Lembram o tema e o idioma neste dispositivo.</small></div>' +
      '<p class="small text-muted">Não existem cookies de publicidade nem de análise de terceiros.</p>' +
      '<div class="d-flex justify-content-end gap-2"><button type="button" class="btn btn-outline-secondary btn-sm" data-cookies-acao="fechar">Cancelar</button><button type="button" class="btn btn-primary btn-sm" data-cookies-acao="guardar">Guardar escolha</button></div></div>';
    document.body.appendChild(m);
    document.addEventListener('click', function (ev) {
      var alvo = ev.target.closest('[data-cookies-acao],[data-cookies-abrir]');
      if (!alvo) return;
      ev.preventDefault();
      var acao = alvo.getAttribute('data-cookies-acao');
      if (alvo.hasAttribute('data-cookies-abrir') || acao === 'personalizar') { abrirModal(); return; }
      if (acao === 'fechar') { m.hidden = true; return; }
      if (acao === 'aceitar') gravarEscolha(true);
      else if (acao === 'essenciais') gravarEscolha(false);
      else if (acao === 'guardar') gravarEscolha(document.getElementById('ckPref').checked);
      f.hidden = true; m.hidden = true;
    });
    document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') m.hidden = true; });
    return f;
  }
  function abrirModal() {
    var e = lerEscolha();
    document.getElementById('ckPref').checked = !!(e && e.preferencias);
    document.getElementById('cookieModal').hidden = false;
    document.getElementById('ckPref').focus();
  }
  function verificarCookies() {
    var f = criarFaixa();
    if (!lerEscolha()) f.hidden = false;
  }
  window.SigeCookies = { escolha: lerEscolha, abrir: abrirModal };

  // ------------------------------------------------------------------ contacto
  function contacto() {
    var info = document.getElementById('contacto-info');
    if (info) {
      fetch('/api/v1/site/info/', { headers: { Accept: 'application/json' } }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
        var c = d && d.contacto || {}, l = [];
        if (c.email) l.push('<li class="mb-2"><i class="bi bi-envelope me-2"></i><a href="mailto:' + esc(c.email) + '">' + esc(c.email) + '</a></li>');
        if (c.telefone) l.push('<li class="mb-2"><i class="bi bi-telephone me-2"></i>' + esc(c.telefone) + '</li>');
        if (c.endereco) l.push('<li class="mb-2"><i class="bi bi-geo-alt me-2"></i>' + esc(c.endereco) + '</li>');
        l.push('<li class="mb-2"><i class="bi bi-globe me-2"></i><a href="https://sigesaas.duckdns.org/">sigesaas.duckdns.org</a></li>');
        info.innerHTML = l.join('') + (c.email || c.telefone ? '' : '<li class="text-muted small">Os contactos directos ainda não foram publicados; use o formulário.</li>');
      }).catch(function () { info.innerHTML = '<li class="text-muted">Não foi possível carregar os contactos agora. Use o formulário.</li>'; });
    }
    var form = document.getElementById('form-contacto');
    if (!form) return;
    var aviso = document.getElementById('contacto-aviso');
    function mostrar(tipo, txt) { aviso.className = 'alert alert-' + tipo + ' mt-3'; aviso.textContent = txt; aviso.hidden = false; }
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      if (!form.checkValidity()) { form.classList.add('was-validated'); return; }
      var btn = form.querySelector('button[type=submit]'); btn.disabled = true;
      var corpo = {}; new FormData(form).forEach(function (v, k) { corpo[k] = v; });
      fetch('/api/v1/site/contacto/', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(corpo) })
        .then(function (r) {
          if (r.status === 201) { form.reset(); form.classList.remove('was-validated'); mostrar('success', 'Mensagem enviada. Obrigado — responderemos assim que possível.'); }
          else if (r.status === 429) mostrar('warning', 'Enviou várias mensagens seguidas. Tente de novo dentro de uma hora.');
          else if (r.status >= 500) mostrar('warning', 'De momento não conseguimos receber a sua mensagem. Tente novamente dentro de instantes.');
          else mostrar('danger', 'Verifique os campos (email válido, mensagem com pelo menos 10 caracteres, sem código HTML).');
        })
        .catch(function () { mostrar('danger', 'Sem ligação ao servidor. Tente novamente.'); })
        .then(function () { btn.disabled = false; });
    });
  }

  document.addEventListener('DOMContentLoaded', function () { cabecalho(); rodape(); verificarCookies(); contacto(); });
})();
