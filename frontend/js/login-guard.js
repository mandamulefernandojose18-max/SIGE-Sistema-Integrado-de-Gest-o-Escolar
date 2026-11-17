/* Dissuasao leve na tela de login (NAO e seguranca real: a protecao esta no servidor).
 * Activo apenas enquanto o utilizador nao esta autenticado (body sem classe "authenticated").
 * Nao bloqueia colar nem seleccionar texto nos campos de formulario. */
(function () {
  'use strict';
  function naLogin() {
    return !document.body.classList.contains('authenticated');
  }
  document.addEventListener('contextmenu', function (e) {
    if (!naLogin()) return;
    var t = e.target;
    if (t && t.closest && t.closest('input, textarea')) return; // mantem colar nos campos
    e.preventDefault();
  });
  document.addEventListener('keydown', function (e) {
    if (!naLogin()) return;
    var k = (e.key || '').toLowerCase();
    var ctrlShift = (e.ctrlKey || e.metaKey) && e.shiftKey && (k === 'i' || k === 'j' || k === 'c');
    var verFonte = (e.ctrlKey || e.metaKey) && k === 'u';
    if (e.key === 'F12' || ctrlShift || verFonte) {
      e.preventDefault();
      e.stopPropagation();
    }
  }, true);
})();
