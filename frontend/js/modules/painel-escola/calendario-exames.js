// =====================================================================
// SIGE - CALENDÁRIO DOS EXAMES
// Datas/horários por disciplina (1ª e 2ª chamada), formação automática de júris e lista de excluídos.
// Filtros em cascata: Classe → Disciplina → Júri (altura constante, sem listas abertas de botões).
// API: /api/v1/notas/calendario-exames  ·  /api/v1/notas/juris-exame
// =====================================================================
(function () {
  'use strict';
  var API_CAL = '/api/v1/notas/calendario-exames/';
  var API_JURIS = '/api/v1/notas/juris-exame/';
  var PERIODOS = { MANHA: 'Manhã', TARDE: 'Tarde', NOITE: 'Noturno' };
  var ctx = { ano: '', linhas: [], juris: [], aba: 'calendario' };

  function $(id) { return document.getElementById(id); }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML.replace(/"/g, '&quot;'); }
  function toast(m, t) { if (typeof window.mostrarToast === 'function') window.mostrarToast(m, t || 'info'); else alert(m); }
  function classe() { return ($('calExClasse') || {}).value || ''; }
  function fmtNota(v) { return v == null ? '—' : Number(v).toFixed(1).replace('.', ','); }
  function dataPt(iso) { if (!iso) return '—'; var p = iso.split('-'); return p[2] + '/' + p[1] + '/' + p[0]; }
  function q(o) { return Object.keys(o).filter(function (k) { return o[k] !== '' && o[k] != null; })
    .map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(o[k]); }).join('&'); }
  function pode() {
    var r = ((typeof state !== 'undefined' && state && state.user && state.user.role) || '');
    return ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'].indexOf(r) >= 0;
  }

  // hora final = hora inicial + duração (mesmo dia)
  function horaFim(ini, dur) {
    if (!ini || !dur) return '';
    var p = ini.split(':'); var t = parseInt(p[0], 10) * 60 + parseInt(p[1], 10) + parseInt(dur, 10);
    if (isNaN(t) || t >= 1440) return '—';
    return String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0');
  }
  function periodoSugerido(ini) {
    if (!ini) return '';
    var h = parseInt(ini.split(':')[0], 10);
    return h < 12 ? 'MANHA' : (h < 18 ? 'TARDE' : 'NOITE');
  }

  window.carregarCalendarioExames = async function (ano) {
    ctx.ano = ano || ctx.ano || '';
    var sel = $('calExClasse');
    if (!sel) return;
    var atual = sel.value;
    try {
      var r = await apiFetch(API_CAL + '?' + q({ ano: ctx.ano }), { noCache: true });
      var classes = (r && r.data && r.data.classes) || [];
      if (!classes.length) {
        sel.innerHTML = '<option value="">Sem turmas neste ano lectivo</option>';
        $('calExCorpo').innerHTML = '<tr><td colspan="13" class="text-center text-muted py-4"><i class="bi bi-calendar-x d-block fs-2 mb-1"></i>Ainda não há turmas neste ano lectivo. Crie as turmas e o Plano Curricular primeiro.</td></tr>';
        return;
      }
      sel.innerHTML = '<option value="">Escolha a classe...</option>' + classes.map(function (c) {
        return '<option value="' + esc(c) + '"' + (c === atual ? ' selected' : '') + '>' + esc(c) + '</option>';
      }).join('');
      if (atual && classes.indexOf(atual) >= 0) window.calExMudouClasse();
    } catch (e) { toast(e.message || 'Erro ao carregar as classes.', 'danger'); }
  };

  window.calExAba = function (aba) {
    ctx.aba = aba;
    document.querySelectorAll('#calExTabs [data-cx-tab]').forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-cx-tab') === aba); });
    $('calExPainelCalendario').classList.toggle('d-none', aba !== 'calendario');
    $('calExPainelJuris').classList.toggle('d-none', aba !== 'juris');
    $('calExPainelExcluidos').classList.toggle('d-none', aba !== 'excluidos');
    if (aba === 'juris') window.calExCarregarJuris();
    if (aba === 'excluidos') preencherDisciplinas('calExExclDisc');
  };

  window.calExMudouClasse = async function () {
    var c = classe();
    var corpo = $('calExCorpo');
    if (!c) {
      corpo.innerHTML = '<tr><td colspan="13" class="text-center text-muted py-4">Escolha a classe para ver as disciplinas com exame.</td></tr>';
      return;
    }
    corpo.innerHTML = '<tr><td colspan="13" class="text-center text-muted py-4">A carregar...</td></tr>';
    try {
      var r = await apiFetch(API_CAL + '?' + q({ ano: ctx.ano, classe: c }), { noCache: true });
      ctx.linhas = (r.data && r.data.linhas) || [];
      desenharCalendario();
      if (ctx.aba === 'juris') window.calExCarregarJuris();
      if (ctx.aba === 'excluidos') preencherDisciplinas('calExExclDisc');
    } catch (e) { corpo.innerHTML = '<tr><td colspan="13" class="text-danger text-center py-3">' + esc(e.message) + '</td></tr>'; }
  };

  function celulasChamada(i, ep, ch, edit) {
    var dis = edit ? '' : ' disabled';
    var d = ch || {};
    var id = 'cx_' + i + '_' + ep;
    var periodo = '<select class="form-select form-select-sm" id="' + id + '_p"' + dis + '><option value="">—</option>' +
      Object.keys(PERIODOS).map(function (k) { return '<option value="' + k + '"' + (d.periodo === k ? ' selected' : '') + '>' + PERIODOS[k] + '</option>'; }).join('') + '</select>';
    return '<td><input type="date" class="form-control form-control-sm" id="' + id + '_d" value="' + esc(d.data || '') + '"' + dis + '></td>' +
      '<td>' + periodo + '</td>' +
      '<td><input type="time" class="form-control form-control-sm" id="' + id + '_i" value="' + esc(d.hora_inicio || '') + '"' + dis + ' oninput="calExRecalcular(' + i + ',' + ep + ')"></td>' +
      '<td><input type="number" min="10" max="480" step="5" class="form-control form-control-sm" style="min-width:72px" id="' + id + '_u" value="' + esc(d.duracao_minutos || '') + '"' + dis + ' oninput="calExRecalcular(' + i + ',' + ep + ')"></td>' +
      '<td class="text-center fw-bold" id="' + id + '_f">' + esc(d.hora_fim || '—') + '</td>';
  }

  function desenharCalendario() {
    var corpo = $('calExCorpo'); var edit = pode();
    $('calExBtnGuardar').classList.toggle('d-none', !edit);
    if (!ctx.linhas.length) {
      corpo.innerHTML = '<tr><td colspan="13" class="text-center text-muted py-4"><i class="bi bi-journal-x d-block fs-2 mb-1"></i>Esta classe não tem disciplinas com exame no Plano Curricular.</td></tr>';
      return;
    }
    corpo.innerHTML = ctx.linhas.map(function (l, i) {
      return '<tr><td class="fw-semibold">' + esc(l.disciplina) + '</td>' +
        celulasChamada(i, 1, l.chamadas['1'], edit) + celulasChamada(i, 2, l.chamadas['2'], edit) +
        '<td class="text-center"><span class="badge bg-success">' + l.admitidos + '</span></td>' +
        '<td class="text-center"><span class="badge bg-danger">' + l.excluidos + '</span></td></tr>';
    }).join('');
  }

  window.calExRecalcular = function (i, ep) {
    var id = 'cx_' + i + '_' + ep;
    var ini = $(id + '_i').value; var dur = $(id + '_u').value;
    $(id + '_f').textContent = horaFim(ini, dur) || '—';
    var p = $(id + '_p');
    if (p && !p.value && ini) p.value = periodoSugerido(ini);   // sugestão; continua editável
  };

  window.calExGuardar = async function () {
    var c = classe();
    if (!c) { toast('Escolha a classe.', 'warning'); return; }
    var itens = [];
    for (var i = 0; i < ctx.linhas.length; i++) {
      for (var ep = 1; ep <= 2; ep++) {
        var id = 'cx_' + i + '_' + ep;
        var data = $(id + '_d').value;
        var existia = !!ctx.linhas[i].chamadas[String(ep)];
        if (!data && !existia) continue;
        itens.push({ disciplina: ctx.linhas[i].disciplina, epoca: ep, data: data, periodo: $(id + '_p').value,
          hora_inicio: $(id + '_i').value, duracao_minutos: $(id + '_u').value });
      }
    }
    if (!itens.length) { toast('Preencha pelo menos uma data.', 'warning'); return; }
    var btn = $('calExBtnGuardar'); btn.disabled = true;
    try {
      await apiFetch(API_CAL, { method: 'POST', body: JSON.stringify({ ano_letivo: ctx.ano, classe: c, itens: itens }) });
      toast('Calendário de exames guardado.', 'success');
      await window.calExMudouClasse();
    } catch (e) { toast(e.message, 'danger'); }
    finally { btn.disabled = false; }
  };

  window.calExPdfCalendario = async function (todas, formato) {
    var c = classe();
    if (!todas && !c) { toast('Escolha a classe ou use a opção de todas as classes.', 'warning'); return; }
    await downloadFicheiroBinario('/api/v1/notas/calendario-exames/pdf/?' + q({ ano: ctx.ano, classe: todas ? '' : c, formato: formato }), 'calendario_exames.' + (formato || 'pdf'));
  };

  // ------------------------------------------------------------------ Júris
  function preencherDisciplinas(selId) {
    var sel = $(selId); if (!sel) return;
    var ant = sel.value;
    sel.innerHTML = '<option value="">Escolha a disciplina...</option>' + ctx.linhas.map(function (l) {
      return '<option value="' + esc(l.disciplina) + '"' + (l.disciplina === ant ? ' selected' : '') + '>' + esc(l.disciplina) + '</option>';
    }).join('');
  }

  window.calExCarregarJuris = async function () {
    var c = classe();
    preencherDisciplinas('calExDisc');
    $('calExJuri').innerHTML = '<option value="">Escolha o júri...</option>';
    if (!c) { $('calExJuriDetalhe').textContent = 'Escolha a classe.'; return; }
    try {
      var r = await apiFetch(API_JURIS + '?' + q({ ano: ctx.ano, epoca: $('calExEpoca').value, classe: c }), { noCache: true });
      ctx.juris = r.data || [];
      if (ctx.juris.length) {   // pré-preenche o máximo usado na última formação
        $('calExMax').value = ctx.juris[0].max_alunos;
        var comSala = ctx.juris.filter(function (j) { return j.sala; }).length;
        if (!comSala) $('calExSalas').value = '';
      }
      $('calExJuriDetalhe').innerHTML = ctx.juris.length
        ? 'Júris formados: <strong>' + ctx.juris.length + '</strong>. Escolha a disciplina e o júri.'
        : '<i class="bi bi-people d-block fs-2 mb-1"></i>Ainda não há júris formados para esta classe e época.';
    } catch (e) { $('calExJuriDetalhe').innerHTML = '<span class="text-danger">' + esc(e.message) + '</span>'; }
  };

  window.calExMudouDisciplina = function () {
    var d = $('calExDisc').value;
    var js = ctx.juris.filter(function (j) { return j.disciplina === d; });
    $('calExJuri').innerHTML = '<option value="">Escolha o júri...</option>' + js.map(function (j) {
      return '<option value="' + j.id + '">Júri ' + j.numero + (j.sala ? ' · ' + esc(j.sala) : '') + ' (' + j.alunos.length + ' alunos)</option>';
    }).join('');
    if (js.length === 1) { $('calExJuri').value = js[0].id; window.calExMostrarJuri(); }
    else $('calExJuriDetalhe').textContent = js.length ? 'Escolha o júri.' : 'Esta disciplina não tem júris nesta época.';
  };

  window.calExMostrarJuri = function () {
    var id = $('calExJuri').value;
    var j = ctx.juris.filter(function (x) { return x.id === id; })[0];
    if (!j) return;
    var horario = j.hora_inicio ? j.hora_inicio + ' – ' + j.hora_fim + ' (' + j.duracao_minutos + ' min)' : 'por definir';
    $('calExJuriDetalhe').innerHTML =
      '<div class="d-flex flex-wrap gap-3 mb-2 text-dark">' +
      '<span><strong>Disciplina:</strong> ' + esc(j.disciplina) + '</span><span><strong>Júri:</strong> ' + j.numero + '</span>' +
      '<span><strong>Data:</strong> ' + dataPt(j.data) + '</span><span><strong>Período:</strong> ' + (PERIODOS[j.periodo] || '—') + '</span>' +
      '<span><strong>Horário:</strong> ' + horario + '</span><span><strong>Sala:</strong> ' + esc(j.sala || 'Por atribuir') + '</span></div>' +
      '<div class="table-responsive"><table class="table table-sm table-striped align-middle mb-0"><thead class="table-primary text-center"><tr>' +
      '<th>Nº</th><th class="text-start">Nome completo</th><th>Matrícula</th><th>Turma</th><th>Nota de Frequência</th></tr></thead><tbody>' +
      j.alunos.map(function (a) {
        return '<tr><td class="text-center">' + a.ordem + '</td><td>' + esc(a.nome) + '</td><td class="text-center">' + esc(a.matricula || '') +
          '</td><td class="text-center">' + esc(a.turma) + '</td><td class="text-center fw-bold">' + fmtNota(a.freq) + '</td></tr>';
      }).join('') + '</tbody></table></div>';
  };

  window.calExFormarJuris = async function () {
    if (!pode()) { toast('Só a Direcção, a Administração ou o DAP formam júris.', 'warning'); return; }
    var max = parseInt($('calExMax').value, 10);
    if (!max || max < 1) { toast('Indique o número máximo de alunos por júri.', 'warning'); return; }
    var todas = $('calExTodasClasses').checked;
    if (!todas && !classe()) { toast('Escolha a classe ou marque "Formar para todas as classes".', 'warning'); return; }
    var salas = parseInt($('calExSalas').value, 10);
    var btn = $('calExBtnFormar'); btn.disabled = true;
    try {
      var r = await apiFetch(API_JURIS + 'formar/', { method: 'POST', body: JSON.stringify({
        ano_letivo: ctx.ano, epoca: parseInt($('calExEpoca').value, 10), max_alunos: max,
        num_salas: salas > 0 ? salas : null, classe: todas ? null : classe() }) });
      var d = r.data || {};
      var av = (d.avisos || []).map(function (a) { return '<li>' + esc(a) + '</li>'; }).join('');
      $('calExAvisos').innerHTML = '<div class="alert alert-success py-2 mb-1"><i class="bi bi-check-circle-fill me-1"></i>' +
        d.juris_formados + ' júri(s) formado(s) com ' + d.alunos_alocados + ' aluno(s).</div>' +
        (av ? '<div class="alert alert-warning py-2 mb-0 small"><strong>Atenção:</strong><ul class="mb-0">' + av + '</ul></div>' : '');
      await window.calExCarregarJuris();
    } catch (e) { $('calExAvisos').innerHTML = '<div class="alert alert-danger py-2 mb-0">' + esc(e.message) + '</div>'; }
    finally { btn.disabled = false; }
  };

  window.calExPdfJuris = async function (todos, formato) {
    var c = classe();
    if (!c) { toast('Escolha a classe.', 'warning'); return; }
    var disc = todos ? '' : $('calExDisc').value;
    if (!todos && !disc) { toast('Escolha a disciplina ou use a opção de todos os júris.', 'warning'); return; }
    await downloadFicheiroBinario('/api/v1/notas/juris-exame/pdf/?' + q({ ano: ctx.ano, epoca: $('calExEpoca').value, classe: c, disciplina: disc, formato: formato }), 'juris_exame.' + (formato || 'pdf'));
  };

  // -------------------------------------------------------------- Excluídos
  window.calExMostrarExcluidos = async function () {
    var c = classe(); var d = $('calExExclDisc').value; var corpo = $('calExExclCorpo');
    if (!c || !d) { corpo.textContent = 'Escolha a classe e a disciplina.'; return; }
    try {
      var r = await apiFetch('/api/v1/notas/juris-exame/excluidos/?' + q({ ano: ctx.ano, classe: c }), { noCache: true });
      var g = (r.data || []).filter(function (x) { return x.disciplina === d; })[0];
      if (!g || !g.alunos.length) { corpo.innerHTML = '<i class="bi bi-emoji-smile d-block fs-2 mb-1"></i>Nenhum aluno excluído nesta disciplina.'; return; }
      corpo.innerHTML = '<div class="table-responsive"><table class="table table-sm table-striped align-middle mb-0"><thead class="table-danger text-center"><tr>' +
        '<th>Nº</th><th class="text-start">Nome completo</th><th>Matrícula</th><th>Turma</th><th>Nota de Frequência</th></tr></thead><tbody>' +
        g.alunos.map(function (a, i) {
          return '<tr><td class="text-center">' + (i + 1) + '</td><td>' + esc(a.nome) + '</td><td class="text-center">' + esc(a.matricula || '') +
            '</td><td class="text-center">' + esc(a.turma) + '</td><td class="text-center fw-bold text-danger">' + fmtNota(a.freq) + '</td></tr>';
        }).join('') + '</tbody></table></div>';
    } catch (e) { corpo.innerHTML = '<span class="text-danger">' + esc(e.message) + '</span>'; }
  };

  window.calExPdfExcluidos = async function (formato) {
    var c = classe();
    if (!c) { toast('Escolha a classe.', 'warning'); return; }
    await downloadFicheiroBinario('/api/v1/notas/juris-exame/excluidos/pdf/?' + q({ ano: ctx.ano, classe: c, formato: formato }), 'excluidos_exame.' + (formato || 'pdf'));
  };
})();
