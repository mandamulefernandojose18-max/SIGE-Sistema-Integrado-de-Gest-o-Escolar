/**
 * SIGE | Mapa Estatístico de Início do Ano Lectivo (levantamento de 03/03)
 * Código partilhado pelas vistas: Estatística da Turma, da Classe, Geral da Escola,
 * Painel do Director de Turma e Painel do Director de Classe.
 * O servidor devolve as páginas já montadas (as mesmas tabelas do PDF e do Excel); aqui só se desenham.
 */
(function () {
  const API = '/api/v1/alunos/estatistica-inicio-ano';
  const CTX = {};   // contexto de descarga por contentor: { tipo, turmaId, classe, ano, nome }

  function esc(v) {
    return String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function urlDe(ctx, formato) {
    const f = formato ? `/${formato}` : '';
    if (ctx.tipo === 'turma') return `${API}/turma/${encodeURIComponent(ctx.turmaId)}${f}`;
    if (ctx.tipo === 'classe') return `${API}/classe${f}?classe=${encodeURIComponent(ctx.classe)}&ano=${encodeURIComponent(ctx.ano)}`;
    return `${API}/escola${f}?ano=${encodeURIComponent(ctx.ano)}`;
  }

  function tabelaHtml(tb) {
    const esq = new Set(tb.esq || []);
    const cab = tb.cab.map((h) => `<th class="text-white" style="background:#1e3a8a">${esc(h)}</th>`).join('');
    const corpo = tb.linhas.map((ln, li) => {
      const ultimo = tb.total && li === tb.linhas.length - 1;
      return `<tr class="${ultimo ? 'fw-bold table-secondary' : ''}">` +
        ln.map((v, ci) => `<td class="${esq.has(ci) ? 'text-start' : ''}">${esc(v)}</td>`).join('') + '</tr>';
    }).join('');
    return `
      <div class="mb-3">
        <div class="fw-bold small mb-1" style="color:#1e3a8a">${esc(tb.titulo)}</div>
        <div class="table-responsive">
          <table class="table table-bordered table-sm text-center align-middle small mb-0" style="font-family:'Times New Roman',serif">
            <thead><tr>${cab}</tr></thead><tbody>${corpo}</tbody>
          </table>
        </div>
        ${tb.nota ? `<div class="text-muted fst-italic" style="font-size:.75rem">${esc(tb.nota)}</div>` : ''}
      </div>`;
  }

  function paginaHtml(pg, dados, primeira) {
    const e = dados.escola || {};
    const vazio = pg.mat_total === 0
      ? `<div class="alert alert-light border text-center"><i class="bi bi-people me-1"></i>Sem alunos matriculados (estado ATIVO) nesta selecção para o ano lectivo ${esc(dados.ano)}. O mapa preenche-se automaticamente a partir das matrículas.</div>`
      : pg.tabelas.map(tabelaHtml).join('');
    return `
      <section ${primeira ? '' : 'style="page-break-before:always"'} class="mb-4">
        <div class="text-center pb-2 mb-3 border-bottom">
          <img src="/img/emblema-mocambique.png" style="width:48px;height:48px;object-fit:contain" alt="">
          <div class="fw-bold text-uppercase small">República de Moçambique</div>
          <div class="text-muted small">Ministério da Educação e Cultura</div>
          <div class="fw-bold text-primary">${esc((e.nome || '').toUpperCase())}</div>
          <div class="fw-bold mt-1" style="font-family:'Times New Roman',serif">${esc(pg.titulo)}</div>
          <div class="small text-muted">${esc(pg.subtitulo)}</div>
        </div>
        ${vazio}
      </section>`;
  }

  function barraAcoes(id) {
    return `
      <div class="d-flex gap-2 flex-wrap no-print mb-3">
        <button class="btn btn-primary btn-sm" onclick="window.print()"><i class="bi bi-printer me-1"></i> Imprimir</button>
        <button class="btn btn-outline-danger btn-sm" onclick="eiaBaixar('${id}','pdf')"><i class="bi bi-file-earmark-pdf me-1"></i> PDF</button>
        <button class="btn btn-outline-success btn-sm" onclick="eiaBaixar('${id}','xlsx')"><i class="bi bi-file-earmark-excel me-1"></i> Excel</button>
      </div>`;
  }

  /** Vai buscar o mapa ao servidor e desenha-o em `container`. `ctx` = { tipo, turmaId?, classe?, ano }. */
  window.eiaMostrar = async function (container, ctx) {
    if (!container) return;
    CTX[container.id] = ctx;
    container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A compilar o mapa a partir das matrículas...</p></div>';
    try {
      const res = await apiFetch(urlDe(ctx));
      if (!res || !res.success || !res.data) throw new Error((res && (res.message || res.detail)) || 'Sem dados.');
      const d = res.data;
      container.innerHTML = barraAcoes(container.id) + (d.paginas || []).map((pg, i) => paginaHtml(pg, d, i === 0)).join('');
    } catch (err) {
      container.innerHTML = `<div class="alert alert-warning text-center">${esc(err.message || 'Não foi possível carregar o mapa estatístico.')}</div>`;
    }
  };

  window.eiaBaixar = function (containerId, formato) {
    const ctx = CTX[containerId];
    if (!ctx) return;
    const nome = `Estatistica_Inicio_Ano_${ctx.tipo}_${ctx.ano || ''}.${formato}`;
    return downloadFicheiroBinario(urlDe(ctx, formato), nome);
  };

  window.eiaVazio = function (container, texto, icone) {
    if (container) container.innerHTML = `<div class="text-center py-5 text-muted"><i class="bi ${icone || 'bi-bar-chart-steps'} display-4 d-block mb-3 opacity-50"></i><p class="fw-semibold mb-0">${esc(texto)}</p></div>`;
  };

  // ---------- Filtros em cascata (Classe → Secção/Área → Turma): altura constante para qualquer n ----------
  const NUM = (s) => { const m = String(s || '').match(/\d+/); return m ? parseInt(m[0], 10) : 999; };
  const opcoes = (lista, vazio) => `<option value="">${vazio}</option>` + lista.map((v) => `<option value="${esc(v.valor)}">${esc(v.rotulo)}</option>`).join('');

  /** Carrega as turmas do ano e liga os selectores `selClasse`, `selArea` (opcional) e `selTurma` (opcional). */
  window.eiaCascata = async function ({ ano, selClasse, selArea, selTurma, aoMudar }) {
    const c = document.getElementById(selClasse);
    const a = selArea ? document.getElementById(selArea) : null;
    const t = selTurma ? document.getElementById(selTurma) : null;
    if (!c) return;
    let turmas = [];
    try {
      const res = await apiFetch('/api/v1/escola-admin/turmas');
      turmas = ((res && res.data) || []).filter((x) => String(x.ano_letivo) === String(ano));
    } catch (_) { /* estado vazio abaixo */ }

    const classes = [...new Set(turmas.map((x) => x.grau_ano))].sort((x, y) => NUM(x) - NUM(y) || x.localeCompare(y));
    c.innerHTML = opcoes(classes.map((v) => ({ valor: v, rotulo: v })), classes.length ? '-- Classe --' : 'Sem turmas neste ano');
    if (a) a.innerHTML = opcoes([], '-- Secção / Área --');
    if (t) t.innerHTML = opcoes([], '-- Turma --');

    const areasDa = (classe) => [...new Set(turmas.filter((x) => x.grau_ano === classe).map((x) => x.area || 'Geral'))].sort();
    c.onchange = () => {
      if (a) {
        const areas = areasDa(c.value);
        a.innerHTML = opcoes(areas.map((v) => ({ valor: v, rotulo: v })), c.value ? '-- Secção / Área --' : '-- Secção / Área --');
        if (areas.length === 1) a.value = areas[0];
      }
      if (t) t.innerHTML = opcoes([], '-- Turma --');
      if (a && a.value) a.onchange();
      else if (!a && t) preencherTurmas();
      if (aoMudar) aoMudar();
    };
    const preencherTurmas = () => {
      const lista = turmas.filter((x) => x.grau_ano === c.value && (!a || (x.area || 'Geral') === a.value))
        .sort((x, y) => String(x.nome).localeCompare(String(y.nome)));
      t.innerHTML = opcoes(lista.map((x) => ({ valor: x.id, rotulo: x.nome })), '-- Turma --');
    };
    if (a) a.onchange = () => { if (t) preencherTurmas(); if (aoMudar) aoMudar(); };
    if (t) t.onchange = () => { if (aoMudar) aoMudar(); };
  };

  window.eiaAnoDaView = function (viewId) {
    return (state.anosPorView && state.anosPorView[viewId]) || '';
  };

  window.EIA_VIEWS = ['estatistica-inicio-turma', 'estatistica-inicio-classe', 'estatistica-inicio-escola', 'director-classe'];

  /** Arranque de cada vista, depois de o utilizador escolher o Ano Lectivo e clicar em Buscar. */
  window.eiaIniciarView = async function (viewId, ano) {
    const $ = (id) => document.getElementById(id);
    if (!ano) return;
    if (viewId === 'estatistica-inicio-turma') {
      const doc = $('eiaTurmaDoc');
      eiaVazio(doc, 'Escolha a Classe, a Secção/Área e a Turma para ver o mapa estatístico.');
      await eiaCascata({
        ano, selClasse: 'eiaTurmaClasse', selArea: 'eiaTurmaArea', selTurma: 'eiaTurmaTurma',
        aoMudar: () => {
          const id = $('eiaTurmaTurma').value;
          if (id) eiaMostrar(doc, { tipo: 'turma', turmaId: id, ano });
          else eiaVazio(doc, 'Escolha a Classe, a Secção/Área e a Turma para ver o mapa estatístico.');
        },
      });
    } else if (viewId === 'estatistica-inicio-classe') {
      const doc = $('eiaClasseDoc');
      eiaVazio(doc, 'Escolha a Classe para ver o mapa estatístico (soma automática dos mapas das suas turmas).');
      await eiaCascata({
        ano, selClasse: 'eiaClasseClasse',
        aoMudar: () => {
          const classe = $('eiaClasseClasse').value;
          if (classe) eiaMostrar(doc, { tipo: 'classe', classe, ano });
          else eiaVazio(doc, 'Escolha a Classe para ver o mapa estatístico (soma automática dos mapas das suas turmas).');
        },
      });
    } else if (viewId === 'estatistica-inicio-escola') {
      eiaMostrar($('eiaEscolaDoc'), { tipo: 'escola', ano });
    } else if (viewId === 'director-classe') {
      const sel = $('dcClasseSelect');
      const doc = $('dcClasseDoc');
      if (!sel || !doc) return;
      try {
        const res = await apiFetch(`${API}/minhas?ano=${encodeURIComponent(ano)}`);
        const classes = (res && res.data && res.data.classes_dc) || [];
        sel.innerHTML = classes.length ? classes.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join('') : '<option value="">Sem classes atribuídas</option>';
        sel.onchange = () => sel.value && eiaMostrar(doc, { tipo: 'classe', classe: sel.value, ano });
        if (classes.length) sel.onchange();
        else eiaVazio(doc, 'Não está nomeado(a) Director(a) de Classe em nenhuma classe neste ano lectivo.', 'bi-person-workspace');
      } catch (_) {
        eiaVazio(doc, 'Não foi possível carregar as suas classes.', 'bi-exclamation-circle');
      }
    }
  };
})();
