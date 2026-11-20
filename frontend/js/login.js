/* SIGE — Lógica exclusiva da página de início de sessão (/login).
 * Não contém nada do painel. Após autenticar, entrega a sessão ao painel (passagem única em
 * sessionStorage, apagada pelo painel ao ler) e navega para /<perfil>/dashboard.
 * Continua sem sessão persistente: atualizar o painel (F5) volta a pedir o login. */
(function () {
  'use strict';

  var CHAVE_PASSAGEM = 'sige_handoff';

  function el(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function urlApi(caminho) {
    var base = (window.SIGE_CONFIG && window.SIGE_CONFIG.API_BASE_URL) || '/api/v1';
    base = String(base).replace(/\/api\/v1\/?$/, '');
    return base + caminho + (caminho.slice(-1) === '/' ? '' : '/');
  }

  function mostrarFeedback(tipo, icone, texto) {
    var fb = el('loginFeedback');
    if (!fb) return;
    fb.className = 'alert alert-' + tipo + ' mb-3 py-2 px-3 small';
    fb.innerHTML = '<i class="bi ' + icone + ' me-1"></i> ' + esc(texto);
  }

  function limparFeedback() {
    var fb = el('loginFeedback');
    if (fb) { fb.className = 'mb-3 d-none'; fb.innerHTML = ''; }
  }

  function limparCampos() {
    var e = el('loginEmail'), s = el('loginSenha');
    if (e) e.value = '';
    if (s) {
      s.value = '';
      s.type = 'password';
    }
    var ico = el('iconToggleLoginSenha');
    if (ico) ico.className = 'bi bi-eye fs-5';
    try { localStorage.removeItem('sige_ultimo_usuario'); } catch (_) {}
  }

  async function realizarLogin(ev) {
    if (ev && ev.preventDefault) ev.preventDefault();
    var email = (el('loginEmail').value || '').trim();
    var senha = el('loginSenha').value || '';
    var campo2fa = el('loginCodigo2FA');
    var codigo2fa = campo2fa ? campo2fa.value.trim() : '';
    limparFeedback();

    if (!email || !senha) {
      limparCampos();
      mostrarFeedback('danger', 'bi-x-circle-fill', 'Credenciais invalidas.');
      el('loginEmail').focus();
      return;
    }

    var btn = el('btnLoginSubmit');
    var htmlBtn = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> A autenticar...';
    }

    var entrou = false;
    try {
      var corpo = { email: email, senha: senha, username: email, password: senha };
      if (codigo2fa) corpo.codigo_2fa = codigo2fa;
      var res = await fetch(urlApi('/api/v1/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(corpo)
      });
      var json = null;
      try { json = await res.json(); } catch (_) {}

      if (res.ok && json && json.success) {
        var d = json.data;
        try { localStorage.setItem('sige_ultimo_usuario', email); } catch (_) {}
        if (d.user.role !== 'SUPERADMIN') {
          try { localStorage.removeItem('sige_selected_tenant'); } catch (_) {}
        }
        var destino = window.SIGE_ROTAS.urlInicial(d.user.role);
        if (destino === '/login') {
          mostrarFeedback('danger', 'bi-x-circle-fill', 'Perfil sem painel associado. Contacte o administrador.');
          return;
        }
        sessionStorage.setItem(CHAVE_PASSAGEM, JSON.stringify({
          token: d.tokens.accessToken,
          refresh: d.tokens.refreshToken,
          user: d.user,
          escola: d.escola,
          t: Date.now()
        }));
        entrou = true;
        window.location.replace(destino);
        return;
      }

      if (json && json.requer_2fa) {
        // Palavra-passe correcta; falta (ou falhou) o segundo factor.
        var bloco = el('loginBloco2FA');
        if (bloco) bloco.classList.remove('d-none');
        if (campo2fa) { campo2fa.value = ''; setTimeout(function () { campo2fa.focus(); }, 80); }
        mostrarFeedback(codigo2fa ? 'danger' : 'info', 'bi-shield-lock-fill', json.message || 'Introduza o código de verificação.');
        return;
      }

      var bloco2 = el('loginBloco2FA');
      if (bloco2) bloco2.classList.add('d-none');
      var detalhe = (json && (json.message || json.detail)) || '';
      var l = detalhe.toLowerCase();
      var bloqueado = detalhe && (l.indexOf('bloque') >= 0 || l.indexOf('inactiv') >= 0 || l.indexOf('desactiv') >= 0 ||
        l.indexOf('subscri') >= 0 || l.indexOf('expir') >= 0);
      limparCampos();
      mostrarFeedback('danger', 'bi-x-circle-fill', bloqueado ? detalhe : 'Credenciais invalidas.');
      el('loginEmail').focus();
    } catch (err) {
      mostrarFeedback('warning', 'bi-wifi-off', 'Erro ao conectar ao servidor do SIGE: ' + (err && err.message ? err.message : 'Verifique a sua ligação de rede.'));
    } finally {
      if (btn && !entrou) {
        btn.disabled = false;
        if (htmlBtn) btn.innerHTML = htmlBtn;
      }
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Sem sessão persistente: qualquer resto de sessão/passagem anterior é apagado ao abrir o login.
    try {
      sessionStorage.removeItem(CHAVE_PASSAGEM);
      sessionStorage.removeItem('sige_token');
      sessionStorage.removeItem('sige_refresh_token');
      localStorage.removeItem('sige_token');
      localStorage.removeItem('sige_refresh_token');
      localStorage.removeItem('sige_tema_ativo');
    } catch (_) {}

    var ultimo = '';
    try { ultimo = localStorage.getItem('sige_ultimo_usuario') || ''; } catch (_) {}
    var inpEmail = el('loginEmail'), inpSenha = el('loginSenha');
    if (inpEmail && ultimo) inpEmail.value = ultimo;
    if (inpSenha) setTimeout(function () { inpSenha.focus(); }, 150);

    el('loginForm').addEventListener('submit', realizarLogin);

    el('btnToggleLoginSenha').addEventListener('click', function () {
      var ico = el('iconToggleLoginSenha');
      if (inpSenha.type === 'password') { inpSenha.type = 'text'; ico.className = 'bi bi-eye-slash fs-5'; }
      else { inpSenha.type = 'password'; ico.className = 'bi bi-eye fs-5'; }
    });

    el('linkEsqueciSenha').addEventListener('click', function () {
      if (window.bootstrap && bootstrap.Modal) new bootstrap.Modal(el('modalEsqueciSenha')).show();
    });
  });
})();
