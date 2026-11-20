/* SIGE — Rotas limpas por perfil (partilhado pelo login e pelo painel).
 *
 *   /login                       ecrã de início de sessão (login.html)
 *   /<perfil>/<página>           painel do perfil (painel.html), ex.: /professor/dashboard
 *
 * O caminho contém apenas o perfil e o identificador da página (nunca dados, IDs de registos nem tokens).
 * A autorização continua a ser aplicada em navegarPara() e no servidor (JWT + tenant + RBAC).
 */
(function () {
  'use strict';

  // role (API) -> segmento de URL do painel
  var SLUG_POR_ROLE = {
    SUPERADMIN: 'saas',
    ADMIN_ESCOLA: 'admin',
    DIRECTOR_ESCOLA: 'direcao',
    DAP: 'pedagogico',
    CHEFE_SECRETARIA: 'secretaria',
    SECRETARIA: 'secretaria',
    PROFESSOR: 'professor',
    ALUNO: 'aluno',
    ENCARREGADO: 'encarregado',
    FINANCEIRO: 'financeiro'
  };

  // Página inicial de cada perfil (a que o URL /<perfil>/dashboard abre quando o painel não tem um "dashboard" próprio)
  var VIEW_INICIAL_POR_ROLE = {
    SUPERADMIN: 'saas',
    ADMIN_ESCOLA: 'dashboard',
    DIRECTOR_ESCOLA: 'dashboard',
    DAP: 'estatisticas-aproveitamento',
    CHEFE_SECRETARIA: 'dashboard',
    SECRETARIA: 'alunos',
    PROFESSOR: 'caderneta',
    ALUNO: 'aluno-perfil',
    ENCARREGADO: 'aluno-perfil',
    FINANCEIRO: 'dashboard'
  };

  var SLUGS = Object.keys(SLUG_POR_ROLE).map(function (r) { return SLUG_POR_ROLE[r]; })
    .filter(function (s, i, a) { return a.indexOf(s) === i; });

  function slugDoRole(role) { return SLUG_POR_ROLE[role] || null; }

  // Página real a abrir após o login
  function viewInicial(role) { return VIEW_INICIAL_POR_ROLE[role] || 'dashboard'; }

  // URL de entrada após o login: /<perfil>/dashboard (alias da página inicial)
  function urlInicial(role) {
    var slug = slugDoRole(role);
    return slug ? '/' + slug + '/dashboard' : '/login';
  }

  // Lê o caminho actual: { slug, view } (view = segmento tal como está no URL, ou '')
  function lerCaminho(pathname) {
    var m = /^\/([a-z]{3,20})(?:\/([a-z0-9-]{1,50}))?\/?$/.exec(pathname || location.pathname);
    if (!m || SLUGS.indexOf(m[1]) < 0) return null;
    return { slug: m[1], view: m[2] || '' };
  }

  window.SIGE_ROTAS = {
    SLUGS: SLUGS,
    SLUG_POR_ROLE: SLUG_POR_ROLE,
    VIEW_INICIAL_POR_ROLE: VIEW_INICIAL_POR_ROLE,
    slugDoRole: slugDoRole,
    viewInicial: viewInicial,
    urlInicial: urlInicial,
    lerCaminho: lerCaminho
  };
})();
