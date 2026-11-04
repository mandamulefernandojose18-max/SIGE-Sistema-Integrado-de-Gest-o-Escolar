// Transferências & Anulações de Matrícula — processo completo.
// Regras: filtros em cascata (Classe → Secção/Área → Turma), sem listas abertas, estado vazio real, valores em MZN.
(function () {
  const BASE = '/api/v1/alunos/transferencias/';
  const ROLES_CRIAR = ['SECRETARIA', 'CHEFE_SECRETARIA', 'SUPERADMIN'];
  const ROLES_EDITAR = ['SECRETARIA', 'CHEFE_SECRETARIA', 'SUPERADMIN'];
  const ROLES_APROVAR = ['DIRECTOR_ESCOLA', 'ADMIN_ESCOLA', 'SUPERADMIN'];
  const CATEGORIAS = [
    ['MUDANCA_RESIDENCIA', 'Mudança de residência'], ['DESISTENCIA', 'Desistência'],
    ['FALTA_ASSIDUIDADE', 'Falta de assiduidade'], ['PEDIDO_ENCARREGADO', 'Pedido do encarregado de educação'], ['OUTRO', 'Outro'],
  ];
  const ESTADOS = {
    PENDENTE: ['warning text-dark', 'bi-hourglass-split', 'Pendente de Parecer'],
    APROVADO: ['success', 'bi-check-circle', 'Aprovado pelo Director'],
    REJEITADO: ['danger', 'bi-x-circle', 'Rejeitado'],
    CANCELADO: ['secondary', 'bi-slash-circle', 'Cancelado'],
  };
  const ROTULOS_QUITACAO = {
    propinas: 'Propinas e pagamentos em dia', biblioteca: 'Livros da biblioteca devolvidos',
    material: 'Material escolar devolvido', documentos: 'Documentos do aluno entregues',
  };

  const S = { page: 1, pageSize: 20, turmas: [], sel: new Set(), itens: [], temporizador: null, atrasados: false };

  const role = () => state.user?.role || '';
  const pode = (lista) => lista.includes(role());
  const esc = (v) => escapeHtml(v == null ? '' : String(v));
  const fmtData = (d) => (d ? String(d).slice(0, 10).split('-').reverse().join('/') : '-');
  const fmtDataHora = (d) => (d ? new Date(d).toLocaleString('pt-PT') : '-');
  const fmtMZN = (v) => `${Number(v || 0).toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MZN`;
  const anoAtual = () => (state.anosPorView && state.anosPorView.transferencias) || '';
  const toast = (m, t) => mostrarToast(m, t || 'info');
  const el = (id) => document.getElementById(id);

  // ---------- Filtros em cascata ----------
  async function carregarTurmas() {
    try {
      const res = await apiFetch('/api/v1/escola-admin/turmas');
      S.turmas = Array.isArray(res?.data) ? res.data : (Array.isArray(res?.results) ? res.results : []);
    } catch (_) { S.turmas = []; }
    const classes = [...new Set(S.turmas.map(t => t.grau_ano).filter(Boolean))].sort((a, b) => parseInt(a) - parseInt(b));
    el('trFiltroClasse').innerHTML = '<option value="">Todas</option>' + classes.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('');
    trAoMudarClasse(false);
  }

  function turmasDaSelecao() {
    const c = el('trFiltroClasse').value, a = el('trFiltroArea').value;
    return S.turmas.filter(t => (!c || t.grau_ano === c) && (!a || (t.area || '') === a));
  }

  window.trAoMudarClasse = function (aplicar = true) {
    const c = el('trFiltroClasse').value;
    const areas = [...new Set(S.turmas.filter(t => !c || t.grau_ano === c).map(t => t.area).filter(Boolean))].sort();
    el('trFiltroArea').innerHTML = '<option value="">Todas</option>' + areas.map(a => `<option value="${esc(a)}">${esc(a)}</option>`).join('');
    window.trAoMudarArea(aplicar);
  };

  window.trAoMudarArea = function (aplicar = true) {
    const turmas = turmasDaSelecao();
    el('trFiltroTurma').innerHTML = '<option value="">Todas</option>' + turmas.map(t => `<option value="${esc(t.id)}">${esc(t.nome)}</option>`).join('');
    if (aplicar !== false) trAplicarFiltros();
  };

  function montarQuery(extra = {}) {
    const p = new URLSearchParams();
    const ano = anoAtual();
    if (ano) p.set('ano_letivo', ano);
    const mapa = { search: 'trFiltroBusca', tipo: 'trFiltroTipo', status: 'trFiltroEstado', classe: 'trFiltroClasse', area: 'trFiltroArea', turma_id: 'trFiltroTurma' };
    Object.entries(mapa).forEach(([k, id]) => { const v = (el(id)?.value || '').trim(); if (v) p.set(k, v); });
    if (S.atrasados) p.set('atrasados', '1');
    Object.entries(extra).forEach(([k, v]) => p.set(k, v));
    return p.toString();
  }

  window.trAplicarFiltros = function () { S.page = 1; S.sel.clear(); carregarListaTransferencias(); };
  window.trAoDigitarBusca = function () { clearTimeout(S.temporizador); S.temporizador = setTimeout(window.trAplicarFiltros, 350); };

  window.trFiltrarRapido = function (qual) {
    el('trFiltroTipo').value = qual === 'ANULACAO' ? 'ANULACAO_MATRICULA' : '';
    el('trFiltroEstado').value = (qual === 'PENDENTE' || qual === 'ATRASADOS') ? 'PENDENTE' : (qual === 'APROVADO' ? 'APROVADO' : '');
    S.atrasados = qual === 'ATRASADOS';
    window.trAplicarFiltros();
  };

  // ---------- Resumo ----------
  async function carregarResumo() {
    try {
      const r = (await apiFetch(BASE + 'resumo/')).data || {};
      el('trResPendentes').textContent = r.pendentes ?? 0;
      el('trResAtrasados').textContent = r.atrasados ?? 0;
      el('trResAprovados').textContent = r.aprovados_ano ?? 0;
      el('trResSaidasEntradas').textContent = `${r.saidas_ano ?? 0} saídas • ${r.entradas_ano ?? 0} entradas`;
      el('trResAnulacoes').textContent = r.anulacoes_ano ?? 0;
      const nomes = Object.fromEntries(CATEGORIAS);
      const m = Object.entries(r.motivos_ano || {}).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${esc(nomes[k] || k)}: ${n}`);
      el('trResMotivos').innerHTML = m.length ? `<i class="bi bi-bar-chart me-1"></i>Motivos em ${esc(r.ano)}: ${m.join(' • ')}` : '';
      const aviso = el('trAvisoPendentes');
      if (pode(ROLES_APROVAR) && r.pendentes > 0) {
        aviso.innerHTML = `<i class="bi bi-bell me-1"></i>Tem <strong>${r.pendentes}</strong> processo(s) pendente(s) de parecer` +
          (r.atrasados ? `, <strong class="text-danger">${r.atrasados}</strong> há mais de ${r.prazo_alerta_dias} dias.` : '.');
        aviso.classList.remove('d-none');
      } else aviso.classList.add('d-none');
    } catch (_) { /* o resumo é auxiliar; a lista continua a funcionar */ }
  }

  // ---------- Lista ----------
  function badgeEstado(t) {
    const [cor, icone, texto] = ESTADOS[t.status] || ['secondary', 'bi-question', t.status];
    let extra = '';
    if (t.status === 'PENDENTE' && t.atrasado) extra = `<br><small class="text-danger"><i class="bi bi-exclamation-triangle me-1"></i>${t.dias_pendente} dias sem parecer</small>`;
    if (t.status === 'APROVADO' && t.numero_guia) extra = `<br><small class="text-muted">${esc(t.numero_guia)}</small>`;
    return `<span class="badge bg-${cor}"><i class="bi ${icone} me-1"></i>${esc(texto)}</span>${extra}`;
  }

  function linha(t) {
    const podeAprovar = pode(ROLES_APROVAR) && t.status === 'PENDENTE';
    const marcado = S.sel.has(t.id) ? 'checked' : '';
    const chk = podeAprovar ? `<input type="checkbox" class="form-check-input" ${marcado} onchange="trSelecionar('${esc(t.id)}', this.checked)">` : '';
    const acoes = [`<button class="btn btn-sm btn-outline-primary py-0 px-2" onclick="trDetalhes('${esc(t.id)}')"><i class="bi bi-eye"></i> Detalhes</button>`];
    if (podeAprovar) acoes.push(`<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="trAbrirAprovacao('${esc(t.id)}')"><i class="bi bi-check2"></i> Homologar</button>`);
    if (t.pode_documento) acoes.push(`<button class="btn btn-sm btn-outline-dark py-0 px-2" onclick="trDocumento('${esc(t.id)}')"><i class="bi bi-file-earmark-pdf"></i> ${t.tipo === 'ANULACAO_MATRICULA' ? 'Declaração' : 'Guia'}</button>`);
    return `<tr class="${t.atrasado ? 'table-warning' : ''}">
      <td class="ps-3 tr-sem-rotulo">${chk}</td>
      <td data-label="Data" class="small text-muted">${fmtData(t.data_solicitacao)}</td>
      <td data-label="Aluno"><strong>${esc(t.aluno_nome)}</strong><br><small class="text-muted">${esc(t.aluno_matricula)} • ${esc(t.classe_snapshot)} ${esc(t.turma_snapshot)}</small></td>
      <td data-label="Tipo"><span class="badge bg-light text-dark border">${esc(t.tipo_display)}</span></td>
      <td data-label="Origem/Destino">${esc(t.escola_origem_destino || '-')}</td>
      <td data-label="Motivo" class="small">${esc(t.motivo_categoria_display)}${t.motivo ? `<br><span class="text-muted">${esc(t.motivo)}</span>` : ''}</td>
      <td data-label="Estado">${badgeEstado(t)}</td>
      <td data-label="Acções" class="text-end pe-3"><div class="d-flex flex-wrap gap-1 justify-content-end">${acoes.join('')}</div></td>
    </tr>`;
  }

  function estadoVazio(filtrado) {
    const dica = pode(ROLES_CRIAR) ? ' Clique em <strong>Novo Processo</strong> para registar uma transferência ou anulação.' : '';
    return `<tr><td colspan="8" class="text-center py-5 text-muted"><i class="bi bi-inbox fs-3 d-block mb-2"></i>` +
      (filtrado ? 'Nenhum processo corresponde aos filtros escolhidos.' : `Ainda não há processos de transferência ou anulação neste ano lectivo.${dica}`) + '</td></tr>';
  }

  window.carregarListaTransferencias = async function () {
    const tbody = el('tabelaListaTransferencias');
    if (!tbody) return;
    el('trBtnNovo')?.classList.toggle('d-none', !pode(ROLES_CRIAR));
    el('trAvisoSuperAdmin')?.classList.toggle('d-none', role() !== 'SUPERADMIN');
    if (!S.turmas.length) await carregarTurmas();
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar transferências...</td></tr>';
    try {
      const res = await apiFetch(`${BASE}?${montarQuery({ page: S.page, page_size: S.pageSize })}`);
      S.itens = Array.isArray(res?.data) ? res.data : [];
      const filtrado = !!(el('trFiltroBusca').value || el('trFiltroTipo').value || el('trFiltroEstado').value ||
        el('trFiltroClasse').value || el('trFiltroArea').value || el('trFiltroTurma').value || S.atrasados);
      tbody.innerHTML = S.itens.length ? S.itens.map(linha).join('') : estadoVazio(filtrado);
      const temPendentes = pode(ROLES_APROVAR) && S.itens.some(t => t.status === 'PENDENTE');
      el('trSelTodos').classList.toggle('d-none', !temPendentes);
      atualizarBarraLote();
      renderPaginacao(res);
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-danger">Erro ao carregar processos: ${esc(e.message)}</td></tr>`;
    }
    carregarResumo();
  };

  function renderPaginacao(res) {
    const box = el('trPaginacao');
    const total = res?.count || 0, pages = res?.pages || 1;
    box.innerHTML = `<span class="text-muted">${total} processo(s) • página ${S.page} de ${pages}</span>
      <div class="btn-group btn-group-sm">
        <button class="btn btn-outline-secondary" ${S.page <= 1 ? 'disabled' : ''} onclick="trMudarPagina(-1)"><i class="bi bi-chevron-left"></i> Anterior</button>
        <button class="btn btn-outline-secondary" ${S.page >= pages ? 'disabled' : ''} onclick="trMudarPagina(1)">Seguinte <i class="bi bi-chevron-right"></i></button>
      </div>`;
  }
  window.trMudarPagina = function (d) { S.page = Math.max(1, S.page + d); carregarListaTransferencias(); };

  // ---------- Selecção em lote ----------
  function atualizarBarraLote() {
    el('trLoteContagem').textContent = S.sel.size;
    el('trBarraLote').classList.toggle('d-none', S.sel.size === 0);
  }
  window.trSelecionar = function (id, marcado) { marcado ? S.sel.add(id) : S.sel.delete(id); atualizarBarraLote(); };
  window.trSelecionarTodos = function (marcado) {
    S.itens.filter(t => t.status === 'PENDENTE').forEach(t => (marcado ? S.sel.add(t.id) : S.sel.delete(t.id)));
    document.querySelectorAll('#tabelaListaTransferencias input[type=checkbox]').forEach(c => { c.checked = marcado; });
    atualizarBarraLote();
  };
  window.trAprovarLote = function () {
    const n = S.sel.size;
    abrirModal('Homologar em lote', `
      <p>Vai homologar <strong>${n}</strong> processo(s). O estado de cada aluno será alterado e as guias numeradas.</p>
      <p class="small text-muted mb-3">Só são aprovados os processos com quitação completa; os restantes ficam pendentes e são indicados no fim.</p>
      ${role() === 'SUPERADMIN' ? '<div class="alert alert-warning small">Acção em nome do Director (SuperAdmin em inspecção); fica registada na auditoria.</div>' : ''}
      <div class="d-flex justify-content-end gap-2"><button class="btn btn-light" onclick="fecharModal()">Cancelar</button>
      <button class="btn btn-success" id="trBtnConfLote" onclick="trConfirmarLote()">Confirmar homologação</button></div>`);
  };
  window.trConfirmarLote = async function () {
    const b = el('trBtnConfLote'); b.disabled = true;
    try {
      const r = await apiFetch(BASE + 'aprovar-lote/', { method: 'POST', body: JSON.stringify({ ids: [...S.sel] }) });
      const falhas = (r.falhas || []).map(f => `<li>${esc(f.aluno)} — ${esc(f.motivo)}</li>`).join('');
      abrirModal('Resultado da homologação', `<p class="text-success mb-2"><i class="bi bi-check-circle me-1"></i>${(r.aprovados || []).length} processo(s) homologado(s).</p>` +
        (falhas ? `<p class="mb-1 text-danger">Não homologados:</p><ul class="small">${falhas}</ul><p class="small text-muted">Abra cada um em Detalhes para completar a quitação ou dispensá-la com justificação.</p>` : '') +
        '<div class="text-end"><button class="btn btn-primary" onclick="fecharModal()">Fechar</button></div>');
      S.sel.clear();
      carregarListaTransferencias();
    } catch (e) { toast(e.message, 'danger'); b.disabled = false; }
  };

  // ---------- Novo processo ----------
  window.trNovoProcesso = function () {
    const classes = [...new Set(S.turmas.map(t => t.grau_ano).filter(Boolean))];
    abrirModal('Novo processo', `
      <div class="row g-3">
        <div class="col-12 col-md-6"><label class="form-label small mb-0">Tipo de processo</label>
          <select id="trNTipo" class="form-select form-select-sm" onchange="trAoMudarTipo()">
            <option value="TRANSFERENCIA_SAIDA">Transferência de Saída</option>
            <option value="TRANSFERENCIA_ENTRADA">Transferência de Entrada</option>
            <option value="ANULACAO_MATRICULA">Anulação de Matrícula</option>
          </select></div>
        <div class="col-12 col-md-6"><label class="form-label small mb-0">Motivo</label>
          <select id="trNCategoria" class="form-select form-select-sm">${CATEGORIAS.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join('')}</select></div>

        <div class="col-12" id="trNBlocoAluno">
          <label class="form-label small mb-0">Aluno (pesquise por nome ou código)</label>
          <input id="trNBusca" type="search" class="form-control form-control-sm" placeholder="Escreva pelo menos 2 letras..." autocomplete="off" oninput="trBuscarAluno()">
          <div id="trNResultados" class="list-group tr-resultados-aluno mt-1"></div>
          <div id="trNAlunoEscolhido" class="small mt-2"></div>
          <input type="hidden" id="trNAlunoId">
        </div>

        <div class="col-12 d-none" id="trNBlocoNovo">
          <div class="border rounded p-2 bg-light">
            <div class="small fw-semibold mb-2">Dados do aluno que entra (a matrícula só fica activa quando o Director aprovar)</div>
            <div class="row g-2">
              <div class="col-6"><input id="trNNome" class="form-control form-control-sm" placeholder="Nome *"></div>
              <div class="col-6"><input id="trNApelido" class="form-control form-control-sm" placeholder="Apelido"></div>
              <div class="col-6"><label class="small text-muted mb-0">Data de nascimento *</label><input id="trNNasc" type="date" class="form-control form-control-sm"></div>
              <div class="col-3"><label class="small text-muted mb-0">Género *</label><select id="trNGenero" class="form-select form-select-sm"><option value="M">M</option><option value="F">F</option></select></div>
              <div class="col-3"><label class="small text-muted mb-0">Classe *</label><input id="trNClasse" class="form-control form-control-sm" list="trNClasses" placeholder="ex.: 8ª Classe">
                <datalist id="trNClasses">${classes.map(c => `<option value="${esc(c)}">`).join('')}</datalist></div>
              <div class="col-6"><input id="trNResp" class="form-control form-control-sm" placeholder="Encarregado de educação"></div>
              <div class="col-6"><input id="trNContacto" class="form-control form-control-sm" placeholder="Contacto do encarregado"></div>
            </div>
          </div>
        </div>

        <div class="col-12" id="trNBlocoEscola"><label class="form-label small mb-0" id="trNRotuloEscola">Escola de destino *</label>
          <input id="trNEscola" class="form-control form-control-sm" placeholder="Nome da escola"></div>
        <div class="col-12"><label class="form-label small mb-0">Pormenores do motivo <span class="text-muted" id="trNObrigMotivo"></span></label>
          <textarea id="trNMotivo" class="form-control form-control-sm" rows="2" maxlength="1000"></textarea></div>
        <div class="col-12"><label class="form-label small mb-0">Anexo (pedido do encarregado ou guia da outra escola — PDF, JPG ou PNG, até 5 MB)</label>
          <input id="trNAnexo" type="file" class="form-control form-control-sm" accept=".pdf,.jpg,.jpeg,.png"></div>
      </div>
      <div class="d-flex justify-content-end gap-2 mt-3"><button class="btn btn-light" onclick="fecharModal()">Cancelar</button>
        <button class="btn btn-primary" id="trNGuardar" onclick="trGuardarProcesso()"><i class="bi bi-send me-1"></i>Submeter ao Director</button></div>`);
    const motivoSel = el('trNCategoria');
    motivoSel.addEventListener('change', () => { el('trNObrigMotivo').textContent = motivoSel.value === 'OUTRO' ? '(obrigatório)' : ''; });
    window.trAoMudarTipo();
  };

  window.trAoMudarTipo = function () {
    const tipo = el('trNTipo').value;
    el('trNBlocoAluno').classList.toggle('d-none', tipo === 'TRANSFERENCIA_ENTRADA');
    el('trNBlocoNovo').classList.toggle('d-none', tipo !== 'TRANSFERENCIA_ENTRADA');
    el('trNBlocoEscola').classList.toggle('d-none', tipo === 'ANULACAO_MATRICULA');
    el('trNRotuloEscola').textContent = tipo === 'TRANSFERENCIA_ENTRADA' ? 'Escola de origem *' : 'Escola de destino *';
  };

  let temporizadorBusca = null;
  window.trBuscarAluno = function () {
    clearTimeout(temporizadorBusca);
    temporizadorBusca = setTimeout(async () => {
      const q = el('trNBusca').value.trim(), box = el('trNResultados');
      if (q.length < 2) { box.innerHTML = ''; return; }
      try {
        const r = await apiFetch(`${BASE}buscar-alunos/?q=${encodeURIComponent(q)}`);
        const l = r.data || [];
        box.innerHTML = l.length ? l.map(a => `<button type="button" class="list-group-item list-group-item-action py-1 small"
            onclick="trEscolherAluno('${esc(a.id)}', '${esc(a.nome).replace(/'/g, '&#39;')}', '${esc(a.matricula)}', '${esc(a.classe)} ${esc(a.turma)}')">
            <strong>${esc(a.nome)}</strong> <span class="text-muted">${esc(a.matricula)} • ${esc(a.classe)} ${esc(a.turma)}</span></button>`).join('')
          : '<div class="list-group-item small text-muted">Nenhum aluno activo encontrado.</div>';
      } catch (e) { box.innerHTML = `<div class="list-group-item small text-danger">${esc(e.message)}</div>`; }
    }, 300);
  };

  window.trEscolherAluno = function (id, nome, matricula, turma) {
    el('trNAlunoId').value = id;
    el('trNResultados').innerHTML = '';
    el('trNBusca').value = '';
    el('trNAlunoEscolhido').innerHTML = `<span class="badge bg-primary"><i class="bi bi-person-check me-1"></i>${nome} • ${matricula} • ${turma}</span>`;
  };

  window.trGuardarProcesso = async function () {
    const tipo = el('trNTipo').value;
    const corpo = { tipo, motivo_categoria: el('trNCategoria').value, motivo: el('trNMotivo').value.trim(), escola_origem_destino: el('trNEscola').value.trim() };
    if (tipo === 'TRANSFERENCIA_ENTRADA') {
      corpo.novo_aluno = {
        nome: el('trNNome').value.trim(), apelido: el('trNApelido').value.trim(), data_nascimento: el('trNNasc').value,
        genero: el('trNGenero').value, classe: el('trNClasse').value.trim(),
        nome_responsavel: el('trNResp').value.trim(), contato_responsavel: el('trNContacto').value.trim(),
      };
    } else {
      corpo.aluno = el('trNAlunoId').value;
      if (!corpo.aluno) { toast('Seleccione o aluno na pesquisa.', 'warning'); return; }
    }
    const b = el('trNGuardar'); b.disabled = true;
    try {
      const r = await apiFetch(BASE, { method: 'POST', body: JSON.stringify(corpo) });
      const ficheiro = el('trNAnexo').files[0];
      if (ficheiro) {
        const fd = new FormData(); fd.append('ficheiro', ficheiro);
        try { await apiFetch(`${BASE}${r.data.id}/anexos/`, { method: 'POST', body: fd }); }
        catch (e) { toast('Processo criado, mas o anexo falhou: ' + e.message, 'warning'); }
      }
      fecharModal();
      toast('Processo submetido ao Director para parecer.', 'success');
      carregarListaTransferencias();
    } catch (e) { toast(e.message, 'danger'); b.disabled = false; }
  };

  // ---------- Detalhes ----------
  function blocoQuitacao(t) {
    const q = t.quitacao_info;
    if (!q) return '<p class="small text-muted mb-0">Sem quitação aplicável a este processo.</p>';
    const editavel = pode(ROLES_EDITAR) && t.status === 'PENDENTE';
    const linhas = Object.entries(q.itens).map(([k, v]) => {
      if (k === 'propinas') {
        return `<li class="list-group-item d-flex justify-content-between align-items-center py-1">
          <span><i class="bi ${v.ok ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'} me-2"></i>${ROTULOS_QUITACAO[k]}</span>
          <small class="${v.ok ? 'text-muted' : 'text-danger fw-semibold'}">${v.ok ? 'sem dívidas' : `${v.em_divida} em aberto • ${fmtMZN(v.total_mzn)}`}</small></li>`;
      }
      return `<li class="list-group-item d-flex justify-content-between align-items-center py-1">
        <label class="mb-0"><input type="checkbox" class="form-check-input me-2" ${v.ok ? 'checked' : ''} ${editavel ? '' : 'disabled'}
          onchange="trAlternarQuitacao('${esc(t.id)}','${k}', this.checked)">${ROTULOS_QUITACAO[k]}</label></li>`;
    }).join('');
    return `<ul class="list-group list-group-flush border rounded">${linhas}</ul>
      <p class="small mt-1 mb-0 ${q.completa ? 'text-success' : 'text-warning'}">${q.completa ? 'Quitação completa.' : 'Quitação incompleta: o Director só pode homologar com dispensa justificada.'}</p>`;
  }

  window.trAlternarQuitacao = async function (id, item, valor) {
    try { await apiFetch(`${BASE}${id}/quitacao/`, { method: 'POST', body: JSON.stringify({ [item]: valor }) }); carregarListaTransferencias(); }
    catch (e) { toast(e.message, 'danger'); }
  };

  function blocoAnexos(t) {
    const editavel = pode(ROLES_EDITAR) && t.status === 'PENDENTE';
    const lista = (t.anexos || []).map(a => `<li class="list-group-item d-flex justify-content-between align-items-center py-1 small">
      <a href="#" onclick="trBaixarAnexo('${esc(t.id)}','${esc(a.id)}','${esc(a.nome).replace(/'/g, '&#39;')}'); return false;"><i class="bi bi-paperclip me-1"></i>${esc(a.nome)}</a>
      <span>${(a.tamanho / 1024).toFixed(0)} KB ${editavel ? `<button class="btn btn-sm btn-link text-danger p-0 ms-2" onclick="trRemoverAnexo('${esc(t.id)}','${esc(a.id)}')"><i class="bi bi-trash"></i></button>` : ''}</span></li>`).join('');
    return (lista ? `<ul class="list-group mb-2">${lista}</ul>` : '<p class="small text-muted mb-1">Sem anexos.</p>') +
      (editavel ? `<input type="file" id="trAnexoNovo" class="form-control form-control-sm" accept=".pdf,.jpg,.jpeg,.png" onchange="trEnviarAnexo('${esc(t.id)}')">` : '');
  }

  window.trDetalhes = async function (id) {
    try {
      const [rt, rh] = await Promise.all([apiFetch(`${BASE}${id}/`), apiFetch(`${BASE}${id}/historico/`)]);
      const t = rt.data;
      const linhaTempo = (rh.data || []).map(h => `<li class="mb-1"><span class="badge bg-light text-dark border me-1">${esc(h.acao)}</span>
        <span class="small">${esc(h.descricao)}</span><br><small class="text-muted">${esc(h.usuario)} • ${fmtDataHora(h.data)}</small></li>`).join('');
      const acoes = [];
      if (t.status === 'PENDENTE' && pode(ROLES_APROVAR)) {
        acoes.push(`<button class="btn btn-success btn-sm" onclick="trAbrirAprovacao('${esc(t.id)}')"><i class="bi bi-check2 me-1"></i>Homologar</button>`);
        acoes.push(`<button class="btn btn-outline-danger btn-sm" onclick="trAbrirRejeicao('${esc(t.id)}')"><i class="bi bi-x-lg me-1"></i>Rejeitar</button>`);
      }
      if (t.status === 'PENDENTE' && (pode(ROLES_EDITAR) || pode(ROLES_APROVAR))) acoes.push(`<button class="btn btn-outline-secondary btn-sm" onclick="trCancelar('${esc(t.id)}')">Cancelar pedido</button>`);
      if (t.pode_documento) acoes.push(`<button class="btn btn-dark btn-sm" onclick="trDocumento('${esc(t.id)}')"><i class="bi bi-file-earmark-pdf me-1"></i>${t.tipo === 'ANULACAO_MATRICULA' ? 'Declaração de Anulação' : 'Guia de Transferência'}</button>`);
      abrirModal(`${t.tipo_display} — ${t.aluno_nome}`, `
        <div class="mb-2">${badgeEstado(t)}</div>
        <div class="row g-2 small mb-3">
          <div class="col-6"><span class="text-muted">Código:</span> ${esc(t.aluno_matricula)}</div>
          <div class="col-6"><span class="text-muted">Classe/Turma:</span> ${esc(t.classe_snapshot)} ${esc(t.turma_snapshot)}</div>
          <div class="col-6"><span class="text-muted">Pedido em:</span> ${fmtData(t.data_solicitacao)} por ${esc(t.solicitado_por_nome || '-')}</div>
          <div class="col-6"><span class="text-muted">${t.tipo === 'TRANSFERENCIA_ENTRADA' ? 'Origem' : 'Destino'}:</span> ${esc(t.escola_origem_destino || '-')}</div>
          <div class="col-12"><span class="text-muted">Motivo:</span> ${esc(t.motivo_categoria_display)}${t.motivo ? ' — ' + esc(t.motivo) : ''}</div>
          ${t.status === 'APROVADO' ? `<div class="col-12"><span class="text-muted">Homologado em:</span> ${fmtDataHora(t.data_aprovacao)} por ${esc(t.aprovado_por_nome)}${t.quitacao_dispensada ? `<br><span class="text-warning">Quitação dispensada: ${esc(t.quitacao_justificacao)}</span>` : ''}</div>` : ''}
          ${(t.status === 'REJEITADO' || t.status === 'CANCELADO') ? `<div class="col-12 text-danger"><span class="text-muted">${t.status === 'REJEITADO' ? 'Motivo da rejeição' : 'Motivo do cancelamento'}:</span> ${esc(t.motivo_rejeicao)}</div>` : ''}
        </div>
        ${t.quitacao_info ? `<h6 class="fw-bold small text-uppercase text-muted">Quitação</h6>${blocoQuitacao(t)}<div class="mb-3"></div>` : ''}
        <h6 class="fw-bold small text-uppercase text-muted">Anexos</h6><div class="mb-3">${blocoAnexos(t)}</div>
        <h6 class="fw-bold small text-uppercase text-muted">Histórico</h6>
        <ul class="list-unstyled mb-3" style="max-height:180px;overflow-y:auto">${linhaTempo || '<li class="small text-muted">Sem registos.</li>'}</ul>
        <div class="d-flex flex-wrap justify-content-end gap-2">${acoes.join('')}<button class="btn btn-light btn-sm" onclick="fecharModal()">Fechar</button></div>`);
    } catch (e) { toast(e.message, 'danger'); }
  };

  // ---------- Aprovar / rejeitar / cancelar ----------
  const CONSEQUENCIA = {
    TRANSFERENCIA_SAIDA: 'O aluno passará ao estado <strong>Transferido</strong> e deixará de constar como activo.',
    ANULACAO_MATRICULA: 'O aluno passará ao estado <strong>Inactivo</strong> e deixará de constar como activo.',
    TRANSFERENCIA_ENTRADA: 'A matrícula do aluno ficará <strong>Activa</strong> nesta escola.',
  };

  window.trAbrirAprovacao = async function (id) {
    try {
      const t = (await apiFetch(`${BASE}${id}/`)).data;
      const q = t.quitacao_info;
      const incompleta = q && !q.completa;
      abrirModal('Homologar processo', `
        <p><strong>${esc(t.aluno_nome)}</strong> — ${esc(t.tipo_display)}.</p>
        <p class="small">${CONSEQUENCIA[t.tipo]} Será emitido o documento oficial com número sequencial.</p>
        ${role() === 'SUPERADMIN' ? '<div class="alert alert-warning small py-2">Está a decidir como Engenheiro do Sistema, em nome da Direcção. Fica registado na auditoria.</div>' : ''}
        ${incompleta ? `<div class="alert alert-danger small py-2"><strong>Quitação incompleta.</strong>${blocoQuitacao({ ...t, status: 'APROVADO' })}</div>
          <div class="form-check mb-2"><input class="form-check-input" type="checkbox" id="trDispensa" onchange="document.getElementById('trJust').classList.toggle('d-none', !this.checked)">
            <label class="form-check-label small" for="trDispensa">Dispensar a quitação por decisão da Direcção</label></div>
          <textarea id="trJust" class="form-control form-control-sm d-none mb-2" rows="2" placeholder="Justificação obrigatória (mínimo 10 caracteres)"></textarea>` : ''}
        <div class="d-flex justify-content-end gap-2 mt-3"><button class="btn btn-light" onclick="fecharModal()">Cancelar</button>
          <button class="btn btn-success" id="trBtnConfAprov" onclick="trConfirmarAprovacao('${esc(id)}', ${incompleta ? 'true' : 'false'})">Confirmar homologação</button></div>`);
    } catch (e) { toast(e.message, 'danger'); }
  };

  window.trConfirmarAprovacao = async function (id, incompleta) {
    const corpo = {};
    if (incompleta) {
      if (!el('trDispensa').checked) { toast('Complete a quitação ou marque a dispensa com justificação.', 'warning'); return; }
      corpo.ignorar_quitacao = true; corpo.justificacao = el('trJust').value.trim();
    }
    const b = el('trBtnConfAprov'); b.disabled = true;
    try {
      const r = await apiFetch(`${BASE}${id}/aprovar/`, { method: 'POST', body: JSON.stringify(corpo) });
      fecharModal();
      toast('Processo homologado oficialmente pelo Director.', 'success');
      carregarListaTransferencias();
      if (r.data?.pode_documento && confirm('Descarregar agora o documento oficial?')) window.trDocumento(id);
    } catch (e) { toast(e.message, 'danger'); b.disabled = false; }
  };

  window.trAbrirRejeicao = function (id) {
    abrirModal('Rejeitar processo', `<label class="form-label small">Motivo da rejeição (obrigatório)</label>
      <textarea id="trMotivoRej" class="form-control" rows="3" maxlength="500"></textarea>
      <div class="d-flex justify-content-end gap-2 mt-3"><button class="btn btn-light" onclick="fecharModal()">Voltar</button>
      <button class="btn btn-danger" onclick="trConfirmarRejeicao('${esc(id)}')">Rejeitar</button></div>`);
  };
  window.trConfirmarRejeicao = async function (id) {
    const motivo = el('trMotivoRej').value.trim();
    if (motivo.length < 5) { toast('Indique o motivo da rejeição.', 'warning'); return; }
    try {
      await apiFetch(`${BASE}${id}/rejeitar/`, { method: 'POST', body: JSON.stringify({ motivo }) });
      fecharModal(); toast('Processo rejeitado.', 'success'); carregarListaTransferencias();
    } catch (e) { toast(e.message, 'danger'); }
  };

  window.trCancelar = function (id) {
    abrirModal('Cancelar pedido', `<p class="small">O pedido pendente será cancelado e o aluno fica como estava. Pode indicar o motivo.</p>
      <input id="trMotivoCanc" class="form-control form-control-sm" placeholder="Motivo (opcional)">
      <div class="d-flex justify-content-end gap-2 mt-3"><button class="btn btn-light" onclick="fecharModal()">Voltar</button>
      <button class="btn btn-secondary" onclick="trConfirmarCancelamento('${esc(id)}')">Cancelar pedido</button></div>`);
  };
  window.trConfirmarCancelamento = async function (id) {
    try {
      await apiFetch(`${BASE}${id}/cancelar/`, { method: 'POST', body: JSON.stringify({ motivo: el('trMotivoCanc').value.trim() }) });
      fecharModal(); toast('Pedido cancelado.', 'success'); carregarListaTransferencias();
    } catch (e) { toast(e.message, 'danger'); }
  };

  // ---------- Anexos, documentos e exportação ----------
  window.trEnviarAnexo = async function (id) {
    const f = el('trAnexoNovo').files[0];
    if (!f) return;
    const fd = new FormData(); fd.append('ficheiro', f);
    try { await apiFetch(`${BASE}${id}/anexos/`, { method: 'POST', body: fd }); toast('Anexo adicionado.', 'success'); window.trDetalhes(id); }
    catch (e) { toast(e.message, 'danger'); }
  };
  window.trRemoverAnexo = async function (id, anexoId) {
    try { await apiFetch(`${BASE}${id}/anexos/${anexoId}/`, { method: 'DELETE' }); window.trDetalhes(id); }
    catch (e) { toast(e.message, 'danger'); }
  };
  window.trBaixarAnexo = async function (id, anexoId, nome) {
    try {
      const h = {};
      if (state.token) h.Authorization = `Bearer ${state.token}`;
      const tenant = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null) || state.tenant?.id || state.user?.escola_id;
      if (tenant) h['X-Tenant-ID'] = tenant;
      const resp = await fetch(formatarUrlApi(`${BASE}${id}/anexos/${anexoId}/`), { headers: h });
      if (!resp.ok) throw new Error(`Erro ${resp.status} ao obter o anexo.`);
      const url = URL.createObjectURL(await resp.blob());
      const a = document.createElement('a'); a.href = url; a.download = nome; document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) { toast(e.message, 'danger'); }
  };
  window.trDocumento = function (id) {
    const t = S.itens.find(x => x.id === id);
    return downloadFicheiroBinario(`${BASE}${id}/documento/`, `${t?.numero_guia || 'documento-transferencia'}.pdf`);
  };
  window.trExportar = function (formato) {
    return downloadFicheiroBinario(`${BASE}exportar/?${montarQuery({ formato })}`, `transferencias.${formato}`);
  };
})();
