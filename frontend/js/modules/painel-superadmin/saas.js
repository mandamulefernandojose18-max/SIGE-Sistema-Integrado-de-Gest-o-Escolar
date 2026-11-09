/**
 * SIGE - PAINEL-SUPERADMIN | Gestão de Escolas & Planos SaaS
 * Ficheiro de código independente do menu: saas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */

// ==================== 0. FILTROS EM CASCATA + PAGINAÇÃO (n escolas) ====================
// Altura da tabela constante: no máximo `tamanho` linhas por página, qualquer que seja n.
const saasFiltros = { q: '', provincia: '', distrito: '', estado: '', plano: '', validade: '', ordem: 'nome', pagina: 1, tamanho: 10 };

function dataFimEscolaSaaS(e) {
  const ass = (e.assinaturas && e.assinaturas[0]) || e.assinatura_ativa || null;
  if (!ass?.data_fim) return null;
  const d = new Date(ass.data_fim);
  return isNaN(d) ? null : d;
}

function diasRestantesEscolaSaaS(e) {
  const d = dataFimEscolaSaaS(e);
  if (!d) return null;
  const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
  return Math.ceil((d - hoje) / 86400000);
}

function badgeDiasRestantesSaaS(e) {
  const dias = diasRestantesEscolaSaaS(e);
  if (dias === null) return '';
  let cls = 'bg-success-subtle text-success', txt = `faltam ${dias} dias`;
  if (dias < 0) { cls = 'bg-danger-subtle text-danger'; txt = `expirou há ${-dias} dias`; }
  else if (dias <= 15) cls = 'bg-danger-subtle text-danger';
  else if (dias <= 60) cls = 'bg-warning-subtle text-warning-emphasis';
  return `<span class="badge ${cls}" style="font-size:0.68rem;">${txt}</span>`;
}

function popularFiltrosEscolasSaaS() {
  const lista = state.escolasSaaS || [];
  const unicos = (fn) => [...new Set(lista.map(fn).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt'));
  const preencher = (id, rotulo, valores, atual) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = `<option value="">${rotulo}</option>` + valores.map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join('');
    el.value = valores.includes(atual) ? atual : '';
  };
  preencher('saasFiltroProvincia', 'Todas as províncias', unicos(e => e.provincia), saasFiltros.provincia);
  const base = saasFiltros.provincia ? lista.filter(e => e.provincia === saasFiltros.provincia) : lista;
  preencher('saasFiltroDistrito', 'Todos os distritos', [...new Set(base.map(e => e.distrito).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt')), saasFiltros.distrito);
  preencher('saasFiltroPlano', 'Todos os planos', unicos(e => e.plano?.nome || e.plano_nome), saasFiltros.plano);
}

function aplicarFiltroEscolasSaaS(campo, valor) {
  saasFiltros[campo] = valor;
  if (campo === 'provincia') { saasFiltros.distrito = ''; popularFiltrosEscolasSaaS(); }
  saasFiltros.pagina = 1;
  renderizarTabelaEscolasSaaS();
}

function limparFiltrosEscolasSaaS() {
  Object.assign(saasFiltros, { q: '', provincia: '', distrito: '', estado: '', plano: '', validade: '', ordem: 'nome', pagina: 1 });
  ['saasFiltroBusca', 'saasFiltroEstado', 'saasFiltroValidade', 'saasFiltroOrdem'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = id === 'saasFiltroOrdem' ? 'nome' : '';
  });
  popularFiltrosEscolasSaaS();
  renderizarTabelaEscolasSaaS();
}

function mudarPaginaEscolasSaaS(p) {
  saasFiltros.pagina = p;
  renderizarTabelaEscolasSaaS();
}

function renderizarTabelaEscolasSaaS() {
  const tbody = document.getElementById('tabelaSaasEscolas');
  if (!tbody || typeof window._linhaEscolaSaaS !== 'function') return;
  const f = saasFiltros;
  const q = f.q.trim().toLowerCase();
  let lista = (state.escolasSaaS || []).filter(e => {
    const estado = (e.status || 'ATIVA').toUpperCase();
    const dias = diasRestantesEscolaSaaS(e);
    if (q) {
      const alvo = [e.nome, e.nif_cnpj, e.codigo_escola, e.codigo_gabinete_director, e.codigo_direccao_pedagogica, e.codigo_secretaria, e.email]
        .filter(Boolean).join(' ').toLowerCase();
      if (!alvo.includes(q)) return false;
    }
    if (f.provincia && e.provincia !== f.provincia) return false;
    if (f.distrito && e.distrito !== f.distrito) return false;
    if (f.estado && estado !== f.estado) return false;
    if (f.plano && (e.plano?.nome || e.plano_nome) !== f.plano) return false;
    if (f.validade === 'expiradas' && !(dias !== null && dias < 0)) return false;
    if (f.validade && f.validade !== 'expiradas') {
      if (dias === null || dias < 0 || dias > Number(f.validade)) return false;
    }
    return true;
  });

  lista.sort((a, b) => {
    if (f.ordem === 'validade') {
      const da = diasRestantesEscolaSaaS(a), db = diasRestantesEscolaSaaS(b);
      return (da ?? Infinity) - (db ?? Infinity);
    }
    return (a.nome || '').localeCompare(b.nome || '', 'pt');
  });

  const total = lista.length;
  const paginas = Math.max(1, Math.ceil(total / f.tamanho));
  if (f.pagina > paginas) f.pagina = paginas;
  const ini = (f.pagina - 1) * f.tamanho;
  const pagina = lista.slice(ini, ini + f.tamanho);

  if (total === 0) {
    const semEscolas = (state.escolasSaaS || []).length === 0;
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted">${semEscolas ? 'Nenhuma escola cadastrada no momento.' : 'Nenhuma escola corresponde aos filtros aplicados.'}</td></tr>`;
  } else {
    tbody.innerHTML = pagina.map(window._linhaEscolaSaaS).join('');
  }

  const info = document.getElementById('saasPaginacaoInfo');
  if (info) info.textContent = total === 0 ? '0 escolas' : `${ini + 1}–${ini + pagina.length} de ${total} escola(s)`;
  const nav = document.getElementById('saasPaginacaoNav');
  if (nav) {
    nav.innerHTML = `
      <button class="btn btn-outline-secondary btn-sm" ${f.pagina <= 1 ? 'disabled' : ''} onclick="mudarPaginaEscolasSaaS(${f.pagina - 1})" aria-label="Página anterior"><i class="bi bi-chevron-left"></i></button>
      <span class="small mx-2">Página ${f.pagina} / ${paginas}</span>
      <button class="btn btn-outline-secondary btn-sm" ${f.pagina >= paginas ? 'disabled' : ''} onclick="mudarPaginaEscolasSaaS(${f.pagina + 1})" aria-label="Página seguinte"><i class="bi bi-chevron-right"></i></button>`;
  }
}

// ==================== 0.2 SUPERVISÃO DE PAGAMENTOS (ALARMES) ====================
const ALARME_ESTILO = {
  critica: { cls: 'danger', icone: 'bi-exclamation-octagon-fill', rotulo: 'Crítico' },
  aviso: { cls: 'warning', icone: 'bi-exclamation-triangle-fill', rotulo: 'Atenção' },
  info: { cls: 'info', icone: 'bi-info-circle-fill', rotulo: 'Info' }
};

function actualizarBadgeAlarmesSaaS(total, nivel) {
  const link = document.getElementById('nav-pagamentos-saas');
  if (!link) return;
  let badge = link.querySelector('.badge-alarmes-saas');
  if (!total) { if (badge) badge.remove(); return; }
  if (!badge) {
    badge = document.createElement('span');
    badge.className = 'badge rounded-pill ms-auto badge-alarmes-saas';
    link.appendChild(badge);
  }
  badge.className = `badge rounded-pill ms-auto badge-alarmes-saas bg-${nivel === 'critica' ? 'danger' : 'warning text-dark'}`;
  badge.textContent = total > 99 ? '99+' : total;
  badge.title = `${total} alerta(s) de supervisão de pagamentos`;
}

// Botões de acção directa em cada item do alarme (confirmar/rejeitar comprovativo, abrir ou adiar suspensão)
function botoesAccaoAlarme(codigo, item) {
  const id = escapeHtml(item.instituicao_id || '');
  if (codigo === 'comprovativos_pendentes' && item.pagamento_id) {
    const pid = escapeHtml(item.pagamento_id);
    return `<button class="btn btn-success btn-sm py-0 px-2" onclick="decidirPagamentoAlarme('${pid}', true)" title="Confirmar pagamento"><i class="bi bi-check-lg"></i> Confirmar</button>
            <button class="btn btn-outline-danger btn-sm py-0 px-2" onclick="decidirPagamentoAlarme('${pid}', false)" title="Rejeitar pagamento"><i class="bi bi-x-lg"></i> Rejeitar</button>`;
  }
  if (!item.instituicao_id) return '';
  if (codigo === 'a_entrar_em_suspensao') {
    return `<button class="btn btn-outline-warning btn-sm py-0 px-2" onclick="modalEditarEscolaSuperAdmin('${id}', 'acesso')" title="Registar excepção de suspensão"><i class="bi bi-shield-exclamation"></i> Adiar suspensão</button>`;
  }
  return `<button class="btn btn-outline-primary btn-sm py-0 px-2" onclick="modalEditarEscolaSuperAdmin('${id}')" title="Abrir escola"><i class="bi bi-box-arrow-up-right"></i> Abrir</button>`;
}

async function decidirPagamentoAlarme(pagamentoId, confirmar) {
  try {
    let corpo;
    if (confirmar) {
      if (!confirm('Confirmar este pagamento? A fatura será abatida e, se estiver liquidada, a escola é reactivada.')) return;
    } else {
      const motivo = prompt('Motivo da rejeição (obrigatório):');
      if (motivo === null) return;
      if (!motivo.trim()) return alert('O motivo de rejeição é obrigatório.');
      corpo = JSON.stringify({ motivo: motivo.trim() });
    }
    const res = await apiFetch(`/api/v1/saas/pagamentos/${pagamentoId}/${confirmar ? 'confirmar' : 'rejeitar'}`, { method: 'POST', body: corpo });
    mostrarNotificacao((res && (res.message || res.data?.mensagem)) || (confirmar ? 'Pagamento confirmado.' : 'Pagamento rejeitado.'), 'success');
    carregarAlarmesSaaS();
    carregarPainelSaaS();
  } catch (err) {
    alert(err.message || 'Não foi possível concluir a operação.');
  }
}

async function carregarAlarmesSaaS() {
  const lista = document.getElementById('listaAlarmesSaas');
  const resumo = document.getElementById('resumoAlarmesSaas');
  const icone = document.getElementById('iconeAlarmesSaas');
  try {
    const res = await apiFetch('/api/v1/saas/alarmes', { ignoreAuthRedirect: true });
    if (!res || !res.success) throw new Error((res && res.message) || 'Resposta inválida');
    const d = res.data;
    actualizarBadgeAlarmesSaaS(d.total_alertas, d.nivel);
    if (!lista) return;
    if (icone) icone.className = `bi bi-bell-fill me-2 text-${d.nivel === 'critica' ? 'danger' : d.nivel === 'aviso' ? 'warning' : 'success'}`;
    const ultima = d.ultima_rotina ? new Date(d.ultima_rotina).toLocaleString('pt-PT') : 'nunca';
    if (resumo) resumo.textContent = d.total_alertas
      ? `${d.total_alertas} escola(s)/item(ns) com alertas, ${d.criticos} crítico(s). Última rotina diária: ${ultima}.`
      : `Sem alertas. Última rotina diária: ${ultima}.`;
    if (!d.alarmes.length) {
      lista.innerHTML = '<div class="alert alert-success py-2 mb-0 small"><i class="bi bi-check-circle-fill me-2"></i>Tudo em ordem: não há pagamentos por supervisionar.</div>';
      return;
    }
    lista.innerHTML = '<div class="row g-2">' + d.alarmes.map(a => {
      const est = ALARME_ESTILO[a.severidade] || ALARME_ESTILO.info;
      const itens = a.itens.map(i => `<li class="small mb-1"><div class="d-flex justify-content-between align-items-start gap-2 flex-wrap">
          <span><strong>${escapeHtml(i.instituicao)}</strong> <span class="text-muted">— ${escapeHtml(i.detalhe)}</span></span>
          <span class="d-flex gap-1">${botoesAccaoAlarme(a.codigo, i)}</span></div></li>`).join('');
      const mais = a.total > a.itens.length ? `<li class="small text-muted">… e mais ${a.total - a.itens.length}. <a href="javascript:void(0)" onclick="navegarPara('pagamentos-saas')">Ver todos em Assinaturas &amp; Pagamentos</a>.</li>` : '';
      return `<div class="col-12 col-lg-6">
        <details ${a.severidade === 'critica' ? 'open' : ''} class="border border-${est.cls} border-opacity-50 rounded p-2 bg-${est.cls} bg-opacity-10 h-100">
          <summary class="d-flex align-items-center gap-2 fw-semibold" style="cursor:pointer">
            <i class="bi ${est.icone} text-${est.cls}"></i>
            <span class="flex-grow-1">${escapeHtml(a.titulo)}</span>
            <span class="badge bg-${est.cls} ${est.cls === 'warning' ? 'text-dark' : ''}">${a.total}</span>
          </summary>
          ${a.descricao ? `<div class="small text-muted mt-1">${escapeHtml(a.descricao)}</div>` : ''}
          <ul class="mt-2 mb-0 ps-3">${itens}${mais}</ul>
        </details></div>`;
    }).join('') + '</div>';
  } catch (err) {
    if (resumo) resumo.textContent = 'Não foi possível verificar os alarmes agora.';
    if (lista) lista.innerHTML = `<div class="alert alert-secondary py-2 mb-0 small">Falha ao carregar alarmes (${escapeHtml(err.message || 'erro')}). <button class="btn btn-sm btn-outline-primary ms-2" onclick="carregarAlarmesSaaS()">Tentar novamente</button></div>`;
  }
}

// Monitor: actualiza o distintivo do menu a cada 5 minutos enquanto o SuperAdmin tiver sessão.
function iniciarMonitorAlarmesSaaS() {
  if (window._monitorAlarmesSaaS) return;
  window._monitorAlarmesSaaS = setInterval(() => {
    if (state?.user?.role === 'SUPERADMIN' && !document.hidden) carregarAlarmesSaaS();
  }, 300000);
}

// ==================== 0.1 PACOTES DE FUNCIONALIDADES ====================
const PERIODOS_PACOTE = [['mensal', 'Mensal', 1], ['trimestral', 'Trimestral', 3], ['semestral', 'Semestral', 6], ['anual', 'Anual', 12]];

function precoPeriodoPacote(mensal, meses, descontoPct) {
  const liquido = Number(mensal || 0) * meses * (100 - Number(descontoPct || 0)) / 100;
  return Math.floor(liquido / 50 + 0.5) * 50;
}

// Opções <option> dos pacotes para os modais de escola. `selecionado` = id ou código do pacote.
function opcoesPacotesSaaS(selecionado, porCodigo) {
  const lista = (state.pacotesSaaS || []).filter(p => p.ativo !== false);
  let html = porCodigo ? '' : '<option value="">Acesso total (sem restrições)</option>';
  html += lista.map(p => {
    const sel = porCodigo ? p.codigo === selecionado : p.id === selecionado;
    return `<option value="${escapeHtml(p.id)}" ${sel ? 'selected' : ''}>${escapeHtml(p.nome)} — ${formatarMoeda(Number(p.preco_mensal))}/mês</option>`;
  }).join('');
  return html || '<option value="">Acesso total (sem restrições)</option>';
}

async function carregarPacotesSaaS() {
  const tabela = document.getElementById('tabelaPacotesSaas');
  if (!tabela) return;
  try {
    const res = await apiFetch('/api/v1/saas-admin/pacotes');
    if (!res || !res.success || !Array.isArray(res.data)) throw new Error((res && res.message) || 'Resposta inválida');
    state.pacotesSaaS = res.data;
    state.catalogoPacotesSaaS = res.catalogo || [];
    const catalogo = res.catalogo || [];
    if (res.data.length === 0) {
      tabela.innerHTML = '<tbody><tr><td class="text-center py-4 text-muted">Nenhum pacote configurado.</td></tr></tbody>';
      return;
    }
    const cols = res.data;
    let html = '<thead class="table-light"><tr><th style="min-width:230px">Pacote</th>';
    cols.forEach(p => {
      html += `<th class="text-center" style="min-width:190px">${escapeHtml(p.nome)}
        ${p.recomendado ? '<span class="badge bg-success ms-1">Recomendado</span>' : ''}
        <div class="small fw-normal text-muted">${Number(p.total_escolas || 0)} escola(s)</div></th>`;
    });
    html += '</tr></thead><tbody>';

    html += '<tr><th class="table-light">Preço mensal base (MZN)</th>' + cols.map(p =>
      `<td><input type="number" min="0" step="50" class="form-control form-control-sm text-center fw-bold" id="pac-${p.id}-preco" value="${Number(p.preco_mensal)}" oninput="recalcularPrecosPacote('${p.id}')" aria-label="Preço mensal de ${escapeHtml(p.nome)}"></td>`).join('') + '</tr>';

    html += '<tr><th class="table-light">Limite de alunos / professores</th>' + cols.map(p =>
      `<td><div class="d-flex gap-1"><input type="number" min="1" class="form-control form-control-sm text-center" id="pac-${p.id}-alunos" value="${p.limite_alunos}" title="Alunos"><input type="number" min="1" class="form-control form-control-sm text-center" id="pac-${p.id}-profs" value="${p.limite_professores}" title="Professores"></div></td>`).join('') + '</tr>';

    html += `<tr class="table-light"><th colspan="${cols.length + 1}" class="small text-uppercase text-muted">Funcionalidades incluídas <span class="fw-normal">(o núcleo MEC — alunos, turmas, caderneta, pautas, certificados — está sempre incluído)</span></th></tr>`;
    catalogo.forEach(f => {
      html += `<tr><td><span class="fw-semibold">${escapeHtml(f.rotulo)}</span><br><small class="text-muted">${escapeHtml(f.descricao)}</small></td>` + cols.map(p =>
        `<td class="text-center"><input type="checkbox" class="form-check-input" id="pac-${p.id}-f-${f.chave}" ${(p.funcionalidades || []).includes(f.chave) ? 'checked' : ''} aria-label="${escapeHtml(f.rotulo)} no pacote ${escapeHtml(p.nome)}"></td>`).join('') + '</tr>';
    });

    html += '<tr><th class="table-light">Desconto por período (%)</th>' + cols.map(p => {
      const d = (p.precos || {});
      return `<td>${PERIODOS_PACOTE.filter(x => x[0] !== 'mensal').map(([k, rot]) =>
        `<div class="input-group input-group-sm mb-1"><span class="input-group-text" style="width:92px">${rot}</span><input type="number" min="0" max="90" step="0.01" class="form-control text-center" id="pac-${p.id}-d-${k}" value="${d[k]?.desconto_percentual ?? 0}" oninput="recalcularPrecosPacote('${p.id}')"></div>`).join('')}</td>`;
    }).join('') + '</tr>';

    html += '<tr><th class="table-light">Preço por período (calculado)</th>' + cols.map(p =>
      `<td class="small" id="pac-${p.id}-precos"></td>`).join('') + '</tr>';

    html += '<tr><th class="table-light"></th>' + cols.map(p =>
      `<td class="text-center"><button class="btn btn-primary btn-sm" onclick="guardarPacoteSaaS('${p.id}')"><i class="bi bi-save me-1"></i>Guardar</button></td>`).join('') + '</tr></tbody>';

    tabela.innerHTML = html;
    cols.forEach(p => recalcularPrecosPacote(p.id));
  } catch (err) {
    tabela.innerHTML = `<tbody><tr><td class="text-center py-4 text-danger"><i class="bi bi-exclamation-triangle-fill me-2"></i>Falha ao carregar pacotes (${escapeHtml(err.message || 'erro')}). <button class="btn btn-sm btn-outline-primary ms-2" onclick="carregarPacotesSaaS()">Tentar novamente</button></td></tr></tbody>`;
  }
}

function recalcularPrecosPacote(id) {
  const mensal = Number(document.getElementById(`pac-${id}-preco`)?.value || 0);
  const el = document.getElementById(`pac-${id}-precos`);
  if (!el) return;
  el.innerHTML = PERIODOS_PACOTE.map(([k, rot, meses]) => {
    const d = k === 'mensal' ? 0 : Number(document.getElementById(`pac-${id}-d-${k}`)?.value || 0);
    const preco = precoPeriodoPacote(mensal, meses, d);
    return `<div class="d-flex justify-content-between"><span>${rot}</span><strong>${formatarMoeda(preco)}</strong></div>`;
  }).join('');
}

async function guardarPacoteSaaS(id) {
  const pacote = (state.pacotesSaaS || []).find(p => p.id === id);
  if (!pacote) return;
  const funcionalidades = [...document.querySelectorAll(`[id^="pac-${id}-f-"]`)]
    .filter(c => c.checked).map(c => c.id.replace(`pac-${id}-f-`, ''));
  const descontos = {};
  PERIODOS_PACOTE.filter(x => x[0] !== 'mensal').forEach(([k]) => {
    descontos[k] = Number(document.getElementById(`pac-${id}-d-${k}`)?.value || 0);
  });
  const payload = {
    preco_mensal: Number(document.getElementById(`pac-${id}-preco`)?.value || 0),
    limite_alunos: Number(document.getElementById(`pac-${id}-alunos`)?.value || 1),
    limite_professores: Number(document.getElementById(`pac-${id}-profs`)?.value || 1),
    funcionalidades,
    descontos
  };
  // Pré-visualização do impacto (não grava nada) antes de confirmar
  let imp = null;
  try {
    const r = await apiFetch(`/api/v1/saas-admin/pacotes/${id}/impacto`, { method: 'POST', body: JSON.stringify(payload) });
    imp = r && r.success ? r.data : null;
  } catch (err) {
    return alert('Não foi possível calcular o impacto: ' + (err.message || 'erro'));
  }
  if (!imp) return alert('Não foi possível calcular o impacto da alteração.');

  window._pacotePendente = { id, payload, nome: pacote.nome };
  const lista = (arr, cls) => arr.length ? `<ul class="mb-0 ${cls}">${arr.map(x => `<li>${escapeHtml(x)}</li>`).join('')}</ul>` : '<span class="text-muted">Nenhuma</span>';
  const delta = imp.variacao_receita_mensal;
  const acima = imp.total_acima_do_limite
    ? `<div class="alert alert-warning py-2 small mb-2"><strong>${imp.total_acima_do_limite} escola(s)</strong> já ultrapassam os novos limites (não perdem dados, mas não poderão adicionar mais):
        <ul class="mb-0">${imp.escolas_acima_do_limite.map(e => `<li>${escapeHtml(e.nome)} — ${e.alunos} alunos, ${e.professores} professores</li>`).join('')}</ul></div>` : '';
  const perigo = imp.funcionalidades_removidas.length && imp.total_escolas
    ? `<div class="alert alert-danger py-2 small mb-2"><i class="bi bi-exclamation-octagon-fill me-1"></i>Retirar funcionalidades <strong>bloqueia de imediato</strong> o acesso de ${imp.total_escolas} escola(s) a estas áreas.</div>` : '';
  abrirModal(`Confirmar alterações: ${pacote.nome}`, `
    ${perigo}${acima}
    <div class="row g-2 small mb-3">
      <div class="col-6"><div class="border rounded p-2 h-100"><div class="text-muted">Escolas neste pacote</div><div class="fs-5 fw-bold">${imp.total_escolas}</div><div class="text-muted">${imp.escolas_facturadas_por_pacote} facturadas pelo pacote</div></div></div>
      <div class="col-6"><div class="border rounded p-2 h-100"><div class="text-muted">Preço mensal</div><div class="fs-5 fw-bold">${formatarMoeda(imp.preco_mensal_anterior)} → ${formatarMoeda(imp.preco_mensal_novo)}</div>
        <div class="${delta > 0 ? 'text-success' : delta < 0 ? 'text-danger' : 'text-muted'}">Receita mensal ${delta >= 0 ? '+' : ''}${formatarMoeda(delta)} (só próximas faturas)</div></div></div>
      <div class="col-6"><div class="fw-semibold">Funcionalidades retiradas</div>${lista(imp.funcionalidades_removidas, 'text-danger')}</div>
      <div class="col-6"><div class="fw-semibold">Funcionalidades adicionadas</div>${lista(imp.funcionalidades_adicionadas, 'text-success')}</div>
    </div>
    <div class="d-flex justify-content-end gap-2">
      <button class="btn btn-outline-secondary" onclick="fecharModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="confirmarGuardarPacoteSaaS()"><i class="bi bi-save me-1"></i>Confirmar e guardar</button>
    </div>`);
}

async function confirmarGuardarPacoteSaaS() {
  const p = window._pacotePendente;
  if (!p) return;
  try {
    const res = await apiFetch(`/api/v1/saas-admin/pacotes/${p.id}`, { method: 'PATCH', body: JSON.stringify(p.payload) });
    if (res && res.success) {
      window._pacotePendente = null;
      fecharModal();
      mostrarNotificacao(`Pacote ${p.nome} actualizado e registado na auditoria.`, 'success');
      carregarPacotesSaaS();
    } else {
      alert((res && res.message) || 'Não foi possível guardar o pacote.');
    }
  } catch (err) {
    alert(err.message || 'Erro ao guardar o pacote.');
  }
}

// ==================== 1. CARREGAMENTO DO PAINEL SAAS ====================
async function carregarPainelSaaS() {
  const tbodyEscolas = document.getElementById('tabelaSaasEscolas');
  const tbodyPlanos = document.getElementById('tabelaSaasPlanos');

  if (tbodyEscolas && !tbodyEscolas.innerHTML.includes('spinner-border')) {
    tbodyEscolas.innerHTML = '<tr><td colspan="8" class="text-center py-4"><span class="spinner-border spinner-border-sm text-primary me-2" role="status"></span>A carregar escolas...</td></tr>';
  }
  if (tbodyPlanos && !tbodyPlanos.innerHTML.includes('spinner-border')) {
    tbodyPlanos.innerHTML = '<tr><td colspan="5" class="text-center py-4"><span class="spinner-border spinner-border-sm text-warning me-2" role="status"></span>A carregar planos...</td></tr>';
  }

  try {
    const [settledMetrics, settledEscolas, settledPlanos] = await Promise.allSettled([
      apiFetch('/api/v1/saas-admin/metrics'),
      apiFetch('/api/v1/saas-admin/escolas'),
      apiFetch('/api/v1/saas-admin/planos')
    ]);

    // 1. Métricas do SaaS
    if (settledMetrics.status === 'fulfilled' && settledMetrics.value && settledMetrics.value.success) {
      const d = settledMetrics.value.data || settledMetrics.value.metrics || {};
      const mrr = Number(d.mrr ?? d.receitaMensalEstimada ?? 0);
      const arr = Number(d.arr ?? (mrr * 12));
      const churn = Number(d.churn ?? 0);
      const totalEscolas = d.escolas?.total ?? d.totalEscolas ?? 0;
      const ativas = d.escolas?.ativas ?? d.escolasAtivas ?? 0;
      const expiradas = d.escolas?.expiradas ?? d.escolasExpiradas ?? 0;

      const elMRR = document.getElementById('saasMRR');
      if (elMRR) elMRR.innerHTML = formatarMoeda(mrr);

      const elARR = document.getElementById('saasARR');
      if (elARR) elARR.innerHTML = formatarMoeda(arr);

      const elChurn = document.getElementById('saasChurn');
      if (elChurn) elChurn.textContent = churn + '%';

      const elTotal = document.getElementById('saasTotalEscolas');
      if (elTotal) elTotal.textContent = totalEscolas;

      const elAtivas = document.getElementById('saasEscolasAtivas');
      if (elAtivas) elAtivas.textContent = ativas;

      const elExpiradas = document.getElementById('saasEscolasExpiradas');
      if (elExpiradas) elExpiradas.textContent = expiradas;
    }

    // 2. Tabela de Escolas
    if (tbodyEscolas) {
      if (settledEscolas.status === 'fulfilled' && settledEscolas.value && settledEscolas.value.success && Array.isArray(settledEscolas.value.data)) {
        const listaEscolas = settledEscolas.value.data;
        state.escolasSaaS = listaEscolas;
        const superAdminSelect = document.getElementById('superAdminTenantSelect');
        if (superAdminSelect && listaEscolas.length > 0) {
          superAdminSelect.innerHTML = '<option value="">(Visão Master SaaS)</option>' +
            listaEscolas.map(e => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.nome)} [${escapeHtml(e.status)}]</option>`).join('');
          const saved = localStorage.getItem('sige_selected_tenant');
          if (saved) superAdminSelect.value = saved;
        }
        saasFiltros.pagina = 1;
        {
          window._linhaEscolaSaaS = (e) => {
            const ass = (e.assinaturas && e.assinaturas[0]) || e.assinatura_ativa || null;
            const dataFim = ass?.data_fim ? new Date(ass.data_fim).toLocaleDateString('pt-PT') : '-';
            const statusUpper = (e.status || 'ATIVA').toUpperCase();
            const isAtiva = statusUpper === 'ATIVA';
            const emblemaIcon = e.usar_emblema_nacional 
              ? '<span class="badge bg-warning text-dark me-1" title="Emblema Nacional">🇲🇿 Emblema</span>' 
              : '';
            const valorContratoNum = Number(ass?.valor_pago ?? ass?.valor ?? e.plano?.preco ?? 0);
            const valorContrato = formatarMoeda(valorContratoNum);
            const planoNome = e.plano?.nome || e.plano_nome || 'MENSAL';
            const totalAlunos = e._count?.alunos ?? e.total_alunos ?? 0;
            const totalProfs = e._count?.professores ?? e.total_professores ?? 0;
            const nomeEscapado = (e.nome || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            const codEscola = e.codigo_escola || '0101S0001';
            const codGD = e.codigo_gabinete_director || `GD${codEscola}`;
            const codDP = e.codigo_direccao_pedagogica || `DP${codEscola}`;
            const codSECR = e.codigo_secretaria || `SECR${codEscola}`;

            let badgeClasse = 'bg-success';
            if (statusUpper === 'SUSPENSA') badgeClasse = 'bg-warning text-dark';
            else if (statusUpper === 'EXPIRADA' || statusUpper === 'INACTIVA') badgeClasse = 'bg-danger';

            return `
              <tr>
                <td>
                  <div class="d-flex align-items-center gap-2">
                    <div>
                      <span class="badge bg-primary font-monospace me-1" title="Código Único Oficial da Escola">${escapeHtml(codEscola)}</span>
                      <strong>${escapeHtml(e.nome)}</strong> ${emblemaIcon}
                      <br><small class="text-muted">${escapeHtml(e.email)} | ${escapeHtml(e.telefone || '-')}</small>
                      <div class="mt-1 d-flex flex-wrap gap-1">
                        <span class="badge bg-light text-primary border font-monospace" style="font-size: 0.68rem;" title="Gabinete do Director (Admin Geral)">${escapeHtml(codGD)}</span>
                        <span class="badge bg-light text-info border font-monospace" style="font-size: 0.68rem;" title="Direcção Pedagógica (Sub-Admin)">${escapeHtml(codDP)}</span>
                        <span class="badge bg-light text-secondary border font-monospace" style="font-size: 0.68rem;" title="Chefe da Secretaria">${escapeHtml(codSECR)}</span>
                      </div>
                    </div>
                  </div>
                </td>
                <td><small>${escapeHtml(e.provincia || '-')}<br><span class="text-muted">${escapeHtml(e.distrito || '-')}</span></small></td>
                <td><code>${escapeHtml(e.nif_cnpj)}</code></td>
                <td>
                  <span class="badge bg-light text-dark border">${escapeHtml(planoNome)}</span>
                  <span class="badge bg-primary-subtle text-primary border border-primary-subtle" title="Pacote de funcionalidades">${escapeHtml(e.pacote_nome || 'Acesso total')}</span>
                  <br><strong class="small text-success">${valorContrato}</strong>
                </td>
                <td><small>${escapeHtml(dataFim)}</small><br>${badgeDiasRestantesSaaS(e)}</td>
                <td><span class="badge ${badgeClasse}">${escapeHtml(statusUpper)}</span></td>
                <td><small>${totalAlunos} alunos<br>${totalProfs} profs</small></td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-primary" title="Entrar na Escola como SuperAdmin" onclick="alternarEscolaSuperAdmin('${escapeHtml(e.id)}', '${escapeHtml(nomeEscapado)}')">
                      <i class="bi bi-box-arrow-in-right me-1"></i> Entrar
                    </button>
                    <button class="btn ${isAtiva ? 'btn-outline-danger' : 'btn-outline-success'}" 
                            title="${isAtiva ? 'Desactivar Escola' : 'Activar Escola'}"
                            onclick="toggleStatusEscola('${escapeHtml(e.id)}', '${escapeHtml(nomeEscapado)}', '${escapeHtml(statusUpper)}')">
                      <i class="bi ${isAtiva ? 'bi-toggle-on text-success' : 'bi-toggle-off text-danger'}"></i>
                      ${isAtiva ? 'Activa' : 'Inactiva'}
                    </button>
                    <button class="btn btn-outline-primary" title="Editar Dados & Prazo" onclick="modalEditarEscolaSuperAdmin('${escapeHtml(e.id)}')">
                      <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-info" title="Descarregar Extrato / Contrato da Escola" onclick="descarregarExtratoEscolaSuperAdmin('${escapeHtml(e.id)}')">
                      <i class="bi bi-file-earmark-pdf"></i>
                    </button>
                    <button class="btn btn-outline-danger" title="Eliminar Escola Definitivamente" onclick="eliminarEscolaSuperAdmin('${escapeHtml(e.id)}', '${escapeHtml(nomeEscapado)}', '${escapeHtml(e.codigo_escola || '')}')">
                      <i class="bi bi-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
            `;
          };
          popularFiltrosEscolasSaaS();
          renderizarTabelaEscolasSaaS();
        }
      } else {
        const errMsg = settledEscolas.reason?.message || (settledEscolas.value && settledEscolas.value.message) || 'Erro de comunicação ao carregar lista de instituições';
        tbodyEscolas.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-danger"><i class="bi bi-exclamation-triangle-fill me-2"></i>Falha ao carregar escolas (${escapeHtml(errMsg)}). <button class="btn btn-sm btn-outline-primary ms-2" onclick="carregarPainelSaaS()"><i class="bi bi-arrow-clockwise me-1"></i> Recarregar</button></td></tr>`;
      }
    }

    // 2.1 Pacotes de funcionalidades e alarmes de supervisão (não bloqueiam o resto do painel)
    carregarPacotesSaaS();
    carregarAlarmesSaaS();
    iniciarMonitorAlarmesSaaS();

    // 3. Tabela de Preços dos Planos
    if (tbodyPlanos) {
      if (settledPlanos.status === 'fulfilled' && settledPlanos.value && settledPlanos.value.success && Array.isArray(settledPlanos.value.data)) {
        const listaPlanos = settledPlanos.value.data;
        if (listaPlanos.length === 0) {
          tbodyPlanos.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">Nenhum plano cadastrado.</td></tr>';
        } else {
          tbodyPlanos.innerHTML = listaPlanos.map(p => {
            const precoNum = Number(p.preco || 0);
            return `
              <tr>
                <td><strong>${escapeHtml(p.nome)}</strong></td>
                <td>${p.duracao_dias} dias</td>
                <td><strong class="text-primary">${formatarMoeda(precoNum)}</strong></td>
                <td><small class="text-muted">${escapeHtml(p.descricao || 'Plano de subscrição SIGE')}</small></td>
                <td class="text-end">
                  <button class="btn btn-outline-primary btn-sm" onclick="modalEditarPrecoPlano('${escapeHtml(p.id)}', '${escapeHtml(p.nome)}', ${precoNum})">
                    <i class="bi bi-currency-exchange me-1"></i> Alterar Preço
                  </button>
                </td>
              </tr>
            `;
          }).join('');
        }
      } else {
        const errMsgPlanos = settledPlanos.reason?.message || (settledPlanos.value && settledPlanos.value.message) || 'Erro de comunicação ao carregar planos';
        tbodyPlanos.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-danger"><i class="bi bi-exclamation-triangle-fill me-2"></i>Falha ao carregar planos (${escapeHtml(errMsgPlanos)}). <button class="btn btn-sm btn-outline-primary ms-2" onclick="carregarPainelSaaS()"><i class="bi bi-arrow-clockwise me-1"></i> Recarregar</button></td></tr>`;
      }
    }
  } catch (err) {
    console.error('Erro ao carregar Painel SaaS:', err);
    if (tbodyEscolas) {
      tbodyEscolas.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-danger"><i class="bi bi-exclamation-triangle-fill me-2"></i>Erro ao carregar escolas. <button class="btn btn-sm btn-outline-primary ms-2" onclick="carregarPainelSaaS()"><i class="bi bi-arrow-clockwise me-1"></i> Tentar Novamente</button></td></tr>`;
    }
    if (tbodyPlanos) {
      tbodyPlanos.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-danger"><i class="bi bi-exclamation-triangle-fill me-2"></i>Erro ao carregar planos. <button class="btn btn-sm btn-outline-primary ms-2" onclick="carregarPainelSaaS()"><i class="bi bi-arrow-clockwise me-1"></i> Tentar Novamente</button></td></tr>`;
    }
  }
}

// ==================== 2. MODO INSPEÇÃO & VALIDAÇÃO DE ESTADO ====================
async function alternarEscolaSuperAdmin(escolaId, escolaNome = '', escolaStatus = '') {
  if (!escolaId) {
    sairModoInspecaoSuperAdmin();
    return;
  }

  const st = (escolaStatus || '').toUpperCase();
  // SÓ E SÓ O SUPER ADMIN DEVE TER ACESSO SEMPRE INDEPENDENTEMENTE DE A ESCOLA ESTAR OU NÃO ACTIVA.
  // O SuperAdmin possui privilégios totais de auditoria e inspeciona qualquer instituição sem bloqueio.

  try {
    localStorage.setItem('sige_selected_tenant', escolaId);
    state.filtroAlunoClasse = 'TODAS';
    state.filtroAlunoTurma = 'TODAS';
    const nomeLimpo = (escolaNome || '').replace(/\\'/g, "'");
    state.tenant = { id: escolaId, nome: nomeLimpo || 'Escola Seleccionada', status: st || 'ATIVA' };

    // Sincronizar selector no topo
    const select = document.getElementById('superAdminTenantSelect');
    if (select) select.value = escolaId;

    // Atualizar badges
    atualizarBadgeTenant(state.tenant);
    if (typeof atualizarBotaoToggleNotasDap === 'function') {
      atualizarBotaoToggleNotasDap(state.tenant.permitir_visualizacao_notas !== false);
    }

    // Auditoria: regista o início da inspeção (não bloqueia a navegação se falhar)
    apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/inspecao`, { method: 'POST', body: JSON.stringify({ fase: 'INICIO' }), ignoreAuthRedirect: true }).catch(() => {});

    // Activar banner de inspeção (SÓ E SÓ PARA O SUPERADMIN)
    document.body.classList.add('role-superadmin');
    document.body.classList.add('inspecionando-escola');

    const bannerInspecao = document.getElementById('superAdminInspecaoBanner');
    if (bannerInspecao) {
      bannerInspecao.style.setProperty('display', 'flex', 'important');
      const elNome = document.getElementById('superAdminInspecaoNome');
      if (elNome) elNome.textContent = `A Inspecionar: ${state.tenant.nome}`;
      const elStatus = document.getElementById('superAdminInspecaoStatus');
      if (elStatus) elStatus.textContent = st || 'ATIVA';
    }

    // Re-renderizar sidebar para navegação escolar em modo inspeção
    renderizarSidebarPorNivel('ADMIN_ESCOLA');

    mostrarNotificacao(`Acesso directo concedido à instituição [${state.tenant.nome}] em modo de inspeção.`, 'success');

    // Navegar para o painel principal da instituição
    navegarPara('dashboard');

    // Carregar dados complementares em segundo plano
    try {
      const res = await apiFetch('/api/v1/escola-admin/info', { ignoreAuthRedirect: true });
      if (res && res.success && res.data) {
        state.tenant = res.data;
        atualizarBadgeTenant(state.tenant);
        if (typeof aplicarFuncionalidadesPacoteNoMenu === 'function') aplicarFuncionalidadesPacoteNoMenu();
      }
      if (typeof carregarDadosGlobaisEscola === 'function') {
        carregarDadosGlobaisEscola();
      }
    } catch (_) {}
  } catch (err) {
    console.error('Erro ao alternar para a escola:', err);
    alert('Não foi possível entrar na escola: ' + (err.message || 'Erro desconhecido'));
  }
}

function sairModoInspecaoSuperAdmin() {
  const tenantId = state.tenant?.id || localStorage.getItem('sige_selected_tenant');
  if (tenantId) {
    apiFetch(`/api/v1/saas-admin/escolas/${tenantId}/inspecao`, { method: 'POST', body: JSON.stringify({ fase: 'FIM' }), ignoreAuthRedirect: true }).catch(() => {});
  }
  document.body.classList.remove('inspecionando-escola');
  if (state.user?.role !== 'SUPERADMIN') {
    document.body.classList.remove('role-superadmin');
  }
  localStorage.removeItem('sige_selected_tenant');
  state.tenant = null;

  const select = document.getElementById('superAdminTenantSelect');
  if (select) select.value = '';

  const bannerInspecao = document.getElementById('superAdminInspecaoBanner');
  if (bannerInspecao) bannerInspecao.style.setProperty('display', 'none', 'important');

  // Restaurar badge da sidebar para SIGE Master
  const elNome = document.getElementById('sidebarEscolaNome');
  if (elNome) elNome.textContent = 'SIGE';
  const elStatus = document.getElementById('sidebarStatusBadge');
  if (elStatus) elStatus.textContent = 'ATIVA';
  const elProv = document.getElementById('sidebarProvinciaBadge');
  if (elProv) elProv.textContent = 'SaaS Master';
  const elAno = document.getElementById('headerAnoLetivo');
  if (elAno) elAno.textContent = 'Ano Lectivo: 2026';

  // Restaurar menus do SuperAdmin
  renderizarSidebarPorNivel('SUPERADMIN');

  mostrarNotificacao('Modo de inspeção encerrado. Retornou à Gestão Master SaaS.', 'info');
  navegarPara('saas');
}

// ==================== 3. ACTIVAR / DESACTIVAR ESCOLA ====================
async function toggleStatusEscola(escolaId, nome, statusAtual) {
  const stUpper = (statusAtual || 'ATIVA').toUpperCase();
  const proximo = stUpper === 'ATIVA' ? 'SUSPENSA' : 'ATIVA';
  if (!confirm(`Confirma a alteração de estado da instituição [${nome}] para [${proximo}]?`)) return;

  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/toggle-status`, {
      method: 'PATCH'
    });
    if (res && res.success) {
      alert(res.message || `Estado da escola alterado para ${proximo} com sucesso.`);
      carregarPainelSaaS();
    } else {
      alert((res && res.message) || 'Erro ao alterar estado da escola.');
    }
  } catch (err) {
    alert('Erro ao alterar estado da escola: ' + (err.message || 'Erro de comunicação'));
  }
}

// Valor do contrato = preço do período do pacote escolhido (só leitura enquanto houver preço de pacote).
function atualizarValorContratoCadastro() {
  const pacoteId = document.getElementById('cadEscolaPacote')?.value;
  const periodo = document.getElementById('cadEscolaPlano')?.selectedOptions[0]?.dataset.periodo;
  const pacote = (state.pacotesSaaS || []).find(p => p.id === pacoteId);
  const campo = document.getElementById('cadEscolaValor');
  const info = document.getElementById('cadEscolaValorInfo');
  if (!campo) return;
  const preco = pacote?.precos?.[periodo]?.preco;
  if (preco != null) {
    campo.value = preco;
    campo.readOnly = true;
    if (info) info.textContent = `Calculado: pacote ${pacote.nome} · ${periodo} (${formatarMoeda(pacote.precos[periodo].preco_mensal_equivalente)}/mês equivalente, desconto ${pacote.precos[periodo].desconto_percentual}%).`;
  } else {
    campo.readOnly = false;
    if (info) info.textContent = 'Sem preço de pacote para este período: indique o valor do contrato.';
  }
}

// ==================== 4. CADASTRO DE NOVA ESCOLA ====================
async function modalCadastrarEscolaSuperAdmin() {
  try {
    const planosRes = await apiFetch('/api/v1/saas-admin/planos');
    // A periodicidade (plano) define o período; o preço vem do pacote escolhido (calculado, sem contradições)
    const optPlanos = (planosRes.data || []).map(p =>
      `<option value="${p.id}" data-periodo="${escapeHtml((p.nome || '').toLowerCase())}">${escapeHtml(p.nome)} (${p.duracao_dias} dias)</option>`
    ).join('');
    if (!state.pacotesSaaS) { try { const rp = await apiFetch('/api/v1/saas-admin/pacotes'); state.pacotesSaaS = rp.data || []; } catch (_) {} }

    const optProvincias = (state.geografia?.provincias || [
      'Maputo Cidade', 'Maputo Província', 'Gaza', 'Inhambane', 'Sofala',
      'Manica', 'Tete', 'Zambézia', 'Nampula', 'Cabo Delgado', 'Niassa'
    ]).map(p => `<option value="${p}">${p}</option>`).join('');

    abrirModal('Cadastrar Nova Escola no SIGE', `
      <form id="formModalCadastrarEscola">
        <div class="alert alert-primary border-primary bg-primary bg-opacity-10 py-2 px-3 mb-3">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <small class="fw-bold text-primary d-block"><i class="bi bi-upc-scan me-1"></i> Geração Automática do Código Único da Escola & Órgãos:</small>
              <small class="text-muted" style="font-size: 0.73rem;">[2 díg. Província] + [2 díg. Distrito] + [P/B/S Nível] + [Nº Escola]</small>
            </div>
            <span class="badge bg-primary fs-6 font-monospace px-3 py-2" id="cadPreviewCodEscola">0101S0001</span>
          </div>
          <div class="row g-2 mt-1 pt-2 border-top border-primary border-opacity-25 text-center small">
            <div class="col-4">
              <span class="text-muted d-block" style="font-size: 0.7rem;">Gabinete do Director (GD)</span>
              <code class="fw-bold text-primary" id="cadPreviewCodGD">GD0101S0001</code>
            </div>
            <div class="col-4">
              <span class="text-muted d-block" style="font-size: 0.7rem;">Direcção Pedagógica (DP)</span>
              <code class="fw-bold text-info" id="cadPreviewCodDP">DP0101S0001</code>
            </div>
            <div class="col-4">
              <span class="text-muted d-block" style="font-size: 0.7rem;">Chefe da Secretaria (SECR)</span>
              <code class="fw-bold text-secondary" id="cadPreviewCodSECR">SECR0101S0001</code>
            </div>
          </div>
        </div>

        <div class="row g-3">
          <div class="col-md-5">
            <label class="form-label small fw-semibold">Nome da Instituição</label>
            <input type="text" id="cadEscolaNome" class="form-control" required placeholder="Ex: Escola Secundária de Massinga" oninput="atualizarPreviewModalCadastroEscola()">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-bold text-primary">Nível / Tipo de Escola</label>
            <select id="cadEscolaTipo" class="form-select border-primary fw-semibold" onchange="atualizarPreviewModalCadastroEscola()" required>
              <option value="S" selected>S — Escola Secundária</option>
              <option value="B">B — Escola Básica</option>
              <option value="P">P — Escola Primária</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">NUIT da Escola</label>
            <input type="text" id="cadEscolaNUIT" class="form-control" required placeholder="Ex: 400123456">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">E-mail Administrativo</label>
            <input type="email" id="cadEscolaEmail" class="form-control" required placeholder="secretaria@escola.edu.mz">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Telefone (+258 Padrão)</label>
            <input type="text" id="cadEscolaTelefone" class="form-control" value="+258 " required>
          </div>

          <div class="col-12">
            <div class="border rounded p-2 bg-light">
              <label class="form-label small fw-bold text-primary mb-1"><i class="bi bi-upc-scan me-1"></i> Definição do Código da Escola</label>
              <div class="d-flex flex-wrap gap-3 align-items-center">
                <div class="form-check mb-0">
                  <input class="form-check-input" type="radio" name="cadCodModo" id="cadCodModoAuto" value="auto" checked onchange="alternarModoCodigoEscola()">
                  <label class="form-check-label small" for="cadCodModoAuto">Automático (gerado pelo sistema)</label>
                </div>
                <div class="form-check mb-0">
                  <input class="form-check-input" type="radio" name="cadCodModo" id="cadCodModoManual" value="manual" onchange="alternarModoCodigoEscola()">
                  <label class="form-check-label small" for="cadCodModoManual">Definir manualmente</label>
                </div>
                <input type="text" id="cadEscolaCodigoManual" class="form-control form-control-sm font-monospace text-uppercase d-none" style="max-width: 200px;" maxlength="9" placeholder="Ex: 0101S0001" oninput="atualizarPreviewModalCadastroEscola()">
              </div>
              <small class="text-muted d-none" id="cadCodManualAjuda" style="font-size: 0.72rem;">Formato oficial (0101S0001) ou código numérico de até 8 dígitos. Tem de ser único.</small>
            </div>
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Província</label>
            <select id="cadEscolaProvincia" class="form-select" onchange="atualizarDistritosCadastroEscola(this.value); atualizarPreviewModalCadastroEscola();" required>
              <option value="">Selecione a Província</option>
              ${optProvincias}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Distrito</label>
            <select id="cadEscolaDistrito" class="form-select" onchange="atualizarPreviewModalCadastroEscola()" required>
              <option value="">Selecione primeiro a província</option>
            </select>
          </div>

          <div class="col-md-5">
            <label class="form-label small fw-semibold">Pacote de Funcionalidades</label>
            <select id="cadEscolaPacote" class="form-select" onchange="atualizarValorContratoCadastro()">${opcoesPacotesSaaS('pedagogico', true)}</select>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Periodicidade do Contrato</label>
            <select id="cadEscolaPlano" class="form-select" onchange="atualizarValorContratoCadastro()" required>${optPlanos}</select>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Valor do Contrato (MZN)</label>
            <input type="number" id="cadEscolaValor" class="form-control fw-bold" placeholder="Valor em MZN">
          </div>
          <div class="col-12 -mt-2"><small class="text-muted" id="cadEscolaValorInfo"></small></div>

          <div class="col-md-4">
            <label class="form-label small fw-semibold">Director da Escola (GD)</label>
            <input type="text" id="cadEscolaAdminNome" class="form-control" placeholder="Nome do Director">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Director Pedagógico (DP)</label>
            <input type="text" id="cadEscolaDapNome" class="form-control" placeholder="Nome do Director Pedagógico">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Chefe da Secretaria (SECR)</label>
            <input type="text" id="cadEscolaChefeSecNome" class="form-control" placeholder="Nome do Chefe da Secretaria">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">E-mail do Director (Opcional)</label>
            <input type="email" id="cadEscolaAdminEmail" class="form-control" placeholder="director@escola.edu.mz">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Senha Inicial Padrão</label>
            <input type="password" id="cadEscolaAdminSenha" class="form-control" placeholder="123456 (Padrão)">
          </div>

          <div class="col-12">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" id="cadEscolaEmblema" checked>
              <label class="form-check-label small fw-semibold" for="cadEscolaEmblema">
                Utilizar Emblema Oficial nos documentos e pautas
              </label>
            </div>
          </div>

          <div class="col-12">
            <div class="card bg-light border p-3">
              <label class="form-label small fw-bold mb-2">
                <i class="bi bi-image me-1 text-primary"></i> Logótipo da Instituição
              </label>
              <div class="d-flex align-items-center gap-3">
                <div class="border rounded bg-white p-1 text-center d-flex align-items-center justify-content-center shadow-sm" style="width: 60px; height: 60px; overflow: hidden;">
                  <img id="cadEscolaLogoPreview" src="img/emblema-mocambique.png" alt="Logo" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                </div>
                <div class="flex-grow-1">
                  <input type="file" id="cadEscolaLogoFile" accept="image/*" class="form-control form-control-sm mb-1" onchange="processarUploadLogoModal(this, 'cadEscolaLogoFinal', 'cadEscolaLogoPreview')">
                  <input type="hidden" id="cadEscolaLogoFinal" value="">
                </div>
              </div>
            </div>
          </div>
        </div>
        <button type="submit" class="btn btn-primary w-100 mt-4">Concluir Cadastro da Escola</button>
      </form>
    `);

    // Event listener do formulário
    document.getElementById('formModalCadastrarEscola')?.addEventListener('submit', submeterCadastroEscolaSuperAdmin);
    atualizarValorContratoCadastro();
  } catch (err) {
    console.error('Erro ao abrir modal de cadastro:', err);
    alert('Erro ao carregar dados do cadastro: ' + err.message);
  }
}

function atualizarDistritosCadastroEscola(provincia) {
  const distritos = state.geografia?.distritos?.[provincia] || [];
  const select = document.getElementById('cadEscolaDistrito');
  if (select) {
    if (distritos.length === 0) {
      select.innerHTML = '<option value="">Nenhum distrito registado</option>';
    } else {
      select.innerHTML = distritos.map(d => `<option value="${d}">${d}</option>`).join('');
    }
  }
}

function atualizarPreviewModalCadastroEscola() {
  const prov = document.getElementById('cadEscolaProvincia')?.value || '';
  const dist = document.getElementById('cadEscolaDistrito')?.value || '';
  const tipo = document.getElementById('cadEscolaTipo')?.value || 'S';

  let codProv = '01';
  let codDist = '01';

  const mapaProv = {
    'Niassa': '01', 'Cabo Delgado': '02', 'Nampula': '03', 'Zambézia': '04',
    'Tete': '05', 'Manica': '06', 'Sofala': '07', 'Inhambane': '08',
    'Gaza': '09', 'Maputo Província': '10', 'Maputo Cidade': '11'
  };
  if (mapaProv[prov]) codProv = mapaProv[prov];

  let codFinal = `${codProv}${codDist}${tipo}0001`;
  if (document.getElementById('cadCodModoManual')?.checked) {
    const man = (document.getElementById('cadEscolaCodigoManual')?.value || '').trim().toUpperCase();
    if (man) codFinal = man;
  }

  const elCod = document.getElementById('cadPreviewCodEscola');
  if (elCod) elCod.textContent = codFinal;
  const elGD = document.getElementById('cadPreviewCodGD');
  if (elGD) elGD.textContent = `GD${codFinal}`;
  const elDP = document.getElementById('cadPreviewCodDP');
  if (elDP) elDP.textContent = `DP${codFinal}`;
  const elSECR = document.getElementById('cadPreviewCodSECR');
  if (elSECR) elSECR.textContent = `SECR${codFinal}`;
}

function alternarModoCodigoEscola() {
  const manual = document.getElementById('cadCodModoManual')?.checked;
  document.getElementById('cadEscolaCodigoManual')?.classList.toggle('d-none', !manual);
  document.getElementById('cadCodManualAjuda')?.classList.toggle('d-none', !manual);
  atualizarPreviewModalCadastroEscola();
}
window.alternarModoCodigoEscola = alternarModoCodigoEscola;

async function submeterCadastroEscolaSuperAdmin(e) {
  e.preventDefault();
  try {
    let codigoManual;
    if (document.getElementById('cadCodModoManual')?.checked) {
      codigoManual = (document.getElementById('cadEscolaCodigoManual')?.value || '').trim().toUpperCase();
      if (!/^(\d{4}[PBS]\d{4,5}|\d{1,8})$/.test(codigoManual)) {
        alert('Código da escola inválido. Use o formato 0101S0001 ou um código numérico de até 8 dígitos.');
        return;
      }
    }
    const nome = document.getElementById('cadEscolaNome')?.value?.trim();
    const tipo = document.getElementById('cadEscolaTipo')?.value || 'S';
    const nuit = document.getElementById('cadEscolaNUIT')?.value?.trim();
    const email = document.getElementById('cadEscolaEmail')?.value?.trim();
    const telefone = document.getElementById('cadEscolaTelefone')?.value?.trim();
    const provincia = document.getElementById('cadEscolaProvincia')?.value;
    const distrito = document.getElementById('cadEscolaDistrito')?.value;
    const planoId = document.getElementById('cadEscolaPlano')?.value;
    const valor = Number(document.getElementById('cadEscolaValor')?.value) || undefined;
    const adminNome = document.getElementById('cadEscolaAdminNome')?.value?.trim();
    const dapNome = document.getElementById('cadEscolaDapNome')?.value?.trim();
    const secrNome = document.getElementById('cadEscolaChefeSecNome')?.value?.trim();
    const adminEmail = document.getElementById('cadEscolaAdminEmail')?.value?.trim();
    const adminSenha = document.getElementById('cadEscolaAdminSenha')?.value?.trim() || '123456';
    const usarEmblema = document.getElementById('cadEscolaEmblema')?.checked !== false;
    const logoUrl = document.getElementById('cadEscolaLogoFinal')?.value || null;

    if (!nome || !nuit || !email || !provincia) {
      alert('Preencha os campos obrigatórios: Nome da Escola, NUIT, E-mail e Província.');
      return;
    }

    const payload = {
      nome,
      tipo_escola: tipo,
      codigo_escola: codigoManual || undefined,
      nif_cnpj: nuit,
      email,
      telefone,
      provincia,
      distrito,
      plano_id: planoId,
      pacote_id: document.getElementById('cadEscolaPacote')?.value || undefined,
      valor_contrato: valor,
      director_nome: adminNome || undefined,
      dap_nome: dapNome || undefined,
      chefe_secretaria_nome: secrNome || undefined,
      adminEmail: adminEmail || undefined,
      adminSenha: adminSenha || undefined,
      usar_emblema_nacional: usarEmblema,
      logo_url: logoUrl
    };

    const res = await apiFetch('/api/v1/saas-admin/escolas', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res && res.success) {
      alert(res.message || 'Instituição de ensino cadastrada com sucesso!');
      fecharModal();
      carregarPainelSaaS();
    } else {
      alert((res && res.message) || 'Erro ao cadastrar instituição de ensino.');
    }
  } catch (err) {
    alert('Erro ao cadastrar escola: ' + (err.message || 'Erro de comunicação'));
  }
}

// ==================== 5. EDIÇÃO DE ESCOLA & PRAZO ====================
// Pré-visualização do pacote escolhido na edição: preços por período e funcionalidades ganhas/perdidas.
function atualizarPreviewPacoteEdicao(escolaFuncionalidades) {
  const sel = document.getElementById('editEscolaPacote');
  const caixa = document.getElementById('editEscolaPreviewPacote');
  const chkWrap = document.getElementById('editEscolaFacturarWrap');
  if (!sel || !caixa) return;
  const pacote = (state.pacotesSaaS || []).find(p => p.id === sel.value);
  if (chkWrap) chkWrap.style.display = pacote ? '' : 'none';
  if (!pacote) {
    caixa.innerHTML = '<div class="small text-muted">Acesso total: sem restrições de funcionalidades nem limites.</div>';
    return;
  }
  const catalogo = state.catalogoPacotesSaaS || [];
  const rot = c => (catalogo.find(x => x.chave === c) || {}).rotulo || c;
  const actuais = new Set(escolaFuncionalidades || []);
  const novas = new Set(pacote.funcionalidades || []);
  const ganha = [...novas].filter(c => !actuais.has(c)).map(rot);
  const perde = [...actuais].filter(c => !novas.has(c)).map(rot);
  const linhasPreco = ['mensal', 'trimestral', 'semestral', 'anual'].map(k => {
    const p = pacote.precos?.[k];
    return p ? `<div class="d-flex justify-content-between"><span class="text-capitalize">${k}</span><strong>${formatarMoeda(p.preco)}</strong></div>` : '';
  }).join('');
  caixa.innerHTML = `
    <div class="row g-2 small">
      <div class="col-md-5"><div class="fw-semibold mb-1">Preços do pacote ${escapeHtml(pacote.nome)}</div>${linhasPreco}
        <div class="text-muted mt-1">Limites: ${pacote.limite_alunos} alunos · ${pacote.limite_professores} professores</div></div>
      <div class="col-md-7">
        <div class="fw-semibold text-success">A escola passa a ter</div>${ganha.length ? `<ul class="mb-1">${ganha.map(x => `<li>${escapeHtml(x)}</li>`).join('')}</ul>` : '<div class="text-muted mb-1">Nada de novo</div>'}
        <div class="fw-semibold text-danger">A escola deixa de ter</div>${perde.length ? `<ul class="mb-0">${perde.map(x => `<li>${escapeHtml(x)}</li>`).join('')}</ul>` : '<div class="text-muted">Nada retirado</div>'}
      </div>
    </div>`;
}

async function modalEditarEscolaSuperAdmin(escolaId, aba) {
  try {
    const res = await apiFetch('/api/v1/saas-admin/escolas');
    const escola = (res.data || []).find(e => e.id === escolaId);
    if (!escola) return alert('Escola não encontrada');
    if (!state.pacotesSaaS) { try { const rp = await apiFetch('/api/v1/saas-admin/pacotes'); state.pacotesSaaS = rp.data || []; state.catalogoPacotesSaaS = rp.catalogo || []; } catch (_) {} }

    const ass = escola.assinaturas && escola.assinaturas[0];
    const dataFimStr = ass?.data_fim ? new Date(ass.data_fim).toISOString().split('T')[0] : '';
    const optProvincias = (state.geografia?.provincias || [
      'Maputo Cidade', 'Maputo Província', 'Gaza', 'Inhambane', 'Sofala',
      'Manica', 'Tete', 'Zambézia', 'Nampula', 'Cabo Delgado', 'Niassa'
    ]).map(p =>
      `<option value="${p}" ${p === escola.provincia ? 'selected' : ''}>${p}</option>`
    ).join('');
    const codEscola = escola.codigo_escola || '0101S0001';
    const adiada = escola.suspensao_adiada;
    const avisoAdiada = adiada
      ? `<div class="alert alert-warning py-2 small mb-2"><i class="bi bi-shield-exclamation me-1"></i>Excepção <strong>activa até ${new Date(adiada.ate).toLocaleDateString('pt-PT')}</strong>${adiada.motivo ? ` — ${escapeHtml(adiada.motivo)}` : ''}
           <button type="button" class="btn btn-outline-danger btn-sm py-0 ms-2" id="btnRemoverAdiamento">Remover</button></div>`
      : '<div class="small text-muted mb-2">Sem excepção activa.</div>';

    abrirModal(`Editar Escola: ${escapeHtml(escola.nome)} [${codEscola}]`, `
      <form id="formModalEditarEscola">
        <div class="alert alert-light border py-2 px-3 mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div class="small">
            <strong>Código Único da Escola:</strong> <code class="fs-6 fw-bold text-primary ms-1">${codEscola}</code>
          </div>
          <div class="d-flex gap-2 small">
            <span class="badge bg-primary-subtle text-primary border font-monospace">GD: ${escola.codigo_gabinete_director || 'GD' + codEscola}</span>
            <span class="badge bg-info-subtle text-info-emphasis border font-monospace">DP: ${escola.codigo_direccao_pedagogica || 'DP' + codEscola}</span>
            <span class="badge bg-secondary-subtle text-secondary-emphasis border font-monospace">SECR: ${escola.codigo_secretaria || 'SECR' + codEscola}</span>
          </div>
        </div>

        <ul class="nav nav-tabs mb-3" role="tablist">
          <li class="nav-item"><button class="nav-link active" id="tabEdDados" type="button" data-bs-toggle="tab" data-bs-target="#paneEdDados" role="tab"><i class="bi bi-building me-1"></i>Dados</button></li>
          <li class="nav-item"><button class="nav-link" id="tabEdContrato" type="button" data-bs-toggle="tab" data-bs-target="#paneEdContrato" role="tab"><i class="bi bi-boxes me-1"></i>Contrato &amp; Pacote</button></li>
          <li class="nav-item"><button class="nav-link" id="tabEdAcesso" type="button" data-bs-toggle="tab" data-bs-target="#paneEdAcesso" role="tab"><i class="bi bi-shield-exclamation me-1"></i>Excepções</button></li>
        </ul>

        <div class="tab-content">
          <div class="tab-pane fade show active" id="paneEdDados" role="tabpanel">
            <div class="row g-3">
              <div class="col-md-5">
                <label class="form-label small fw-semibold">Nome da Instituição</label>
                <input type="text" id="editEscolaNome" class="form-control" value="${escapeHtml(escola.nome)}" required>
              </div>
              <div class="col-md-4">
                <label class="form-label small fw-bold text-primary">Nível / Tipo de Escola</label>
                <select id="editEscolaTipo" class="form-select border-primary fw-semibold">
                  <option value="S" ${(escola.tipo_escola || 'S') === 'S' ? 'selected' : ''}>S — Escola Secundária</option>
                  <option value="B" ${escola.tipo_escola === 'B' ? 'selected' : ''}>B — Escola Básica</option>
                  <option value="P" ${escola.tipo_escola === 'P' ? 'selected' : ''}>P — Escola Primária</option>
                </select>
              </div>
              <div class="col-md-3">
                <label class="form-label small fw-semibold">NUIT</label>
                <input type="text" id="editEscolaNUIT" class="form-control" value="${escapeHtml(escola.nif_cnpj)}" required>
              </div>
              <div class="col-md-6">
                <label class="form-label small fw-semibold">E-mail</label>
                <input type="email" id="editEscolaEmail" class="form-control" value="${escapeHtml(escola.email)}" required>
              </div>
              <div class="col-md-6">
                <label class="form-label small fw-semibold">Telefone</label>
                <input type="text" id="editEscolaTelefone" class="form-control" value="${escapeHtml(escola.telefone || '+258 ')}">
              </div>
              <div class="col-md-6">
                <label class="form-label small fw-semibold">Província</label>
                <select id="editEscolaProvincia" class="form-select" onchange="atualizarDistritosEdicaoEscola(this.value)">
                  ${optProvincias}
                </select>
              </div>
              <div class="col-md-6">
                <label class="form-label small fw-semibold">Distrito</label>
                <select id="editEscolaDistrito" class="form-select"></select>
              </div>
              <div class="col-12">
                <div class="border rounded p-2 bg-light">
                  <label class="form-label small fw-bold text-primary mb-1"><i class="bi bi-upc-scan me-1"></i> Código da Escola</label>
                  <div class="d-flex flex-wrap gap-3 align-items-center">
                    <div class="form-check mb-0">
                      <input class="form-check-input" type="radio" name="editCodModo" id="editCodModoManter" value="manter" checked onchange="alternarModoCodigoEdicaoEscola()">
                      <label class="form-check-label small" for="editCodModoManter">Manter actual (<code>${escapeHtml(codEscola)}</code>)</label>
                    </div>
                    <div class="form-check mb-0">
                      <input class="form-check-input" type="radio" name="editCodModo" id="editCodModoAuto" value="auto" onchange="alternarModoCodigoEdicaoEscola()">
                      <label class="form-check-label small" for="editCodModoAuto">Automático (gerado pelo sistema)</label>
                    </div>
                    <div class="form-check mb-0">
                      <input class="form-check-input" type="radio" name="editCodModo" id="editCodModoManual" value="manual" onchange="alternarModoCodigoEdicaoEscola()">
                      <label class="form-check-label small" for="editCodModoManual">Definir manualmente</label>
                    </div>
                    <input type="text" id="editEscolaCodigoManual" class="form-control form-control-sm font-monospace text-uppercase d-none" style="max-width: 200px;" maxlength="9" value="${escapeHtml(escola.codigo_escola || '')}" placeholder="Ex: 0101S0001">
                  </div>
                  <small class="text-muted d-none" id="editCodManualAjuda" style="font-size: 0.72rem;">Formato oficial (0101S0001) ou código numérico de até 8 dígitos. Tem de ser único.</small>
                  <small class="text-warning-emphasis d-none" id="editCodAviso" style="font-size: 0.72rem;"><i class="bi bi-exclamation-triangle me-1"></i>Ao mudar o código, os códigos de acesso GD, DP e SECR da escola são actualizados.</small>
                </div>
              </div>
              <div class="col-12">
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" id="editEscolaEmblema" ${escola.usar_emblema_nacional ? 'checked' : ''}>
                  <label class="form-check-label small fw-semibold" for="editEscolaEmblema">Utilizar Emblema Oficial nos documentos</label>
                </div>
              </div>
              <div class="col-12">
                <div class="card bg-light border p-3">
                  <label class="form-label small fw-bold mb-2"><i class="bi bi-image me-1 text-primary"></i> Logótipo da Instituição</label>
                  <div class="d-flex align-items-center gap-3 mb-2">
                    <div class="border rounded bg-white p-1 text-center d-flex align-items-center justify-content-center shadow-sm" style="width: 60px; height: 60px; overflow: hidden;">
                      <img id="editEscolaLogoPreview" src="${escola.logo_url || 'img/emblema-mocambique.png'}" alt="Logo" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                    </div>
                    <div class="flex-grow-1">
                      <input type="file" id="editEscolaLogoFile" accept="image/*" class="form-control form-control-sm mb-1" onchange="processarUploadLogoModal(this, 'editEscolaLogoFinal', 'editEscolaLogoPreview')">
                      <input type="hidden" id="editEscolaLogoFinal" value="${escola.logo_url || ''}">
                      <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-2" style="font-size: 0.75rem;" onclick="document.getElementById('editEscolaLogoFinal').value=''; document.getElementById('editEscolaLogoPreview').src='img/emblema-mocambique.png';">
                        <i class="bi bi-arrow-counterclockwise me-1"></i> Usar Emblema Nacional
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="tab-pane fade" id="paneEdContrato" role="tabpanel">
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label small fw-bold text-primary">Pacote de Funcionalidades</label>
                <select id="editEscolaPacote" class="form-select border-primary">${opcoesPacotesSaaS(escola.pacote, false)}</select>
                <div id="editEscolaFacturarWrap" class="form-check mt-2" ${escola.pacote ? '' : 'style="display:none"'}>
                  <input class="form-check-input" type="checkbox" id="editEscolaFacturarPacote" ${escola.facturar_por_pacote ? 'checked' : ''}>
                  <label class="form-check-label small" for="editEscolaFacturarPacote">
                    <strong>Facturar pelo preço do pacote</strong> — as <em>próximas</em> faturas e adiantamentos usam o preço e os descontos do pacote. Faturas já emitidas e contratos antigos (desmarcado) não mudam.
                  </label>
                </div>
              </div>
              <div class="col-12"><div class="border rounded p-2 bg-light" id="editEscolaPreviewPacote"></div></div>
              <div class="col-md-6">
                <label class="form-label small fw-semibold">Data de Vencimento do Contrato</label>
                <input type="date" id="editEscolaDataFim" class="form-control" value="${dataFimStr}">
              </div>
              <div class="col-md-6">
                <label class="form-label small fw-semibold">Estender Prazo (Dias Adicionais)</label>
                <input type="number" id="editEscolaDiasAdicionais" class="form-control" placeholder="Ex: 30" min="0">
              </div>
            </div>
          </div>

          <div class="tab-pane fade" id="paneEdAcesso" role="tabpanel">
            <div class="border rounded p-3 bg-light">
              <label class="form-label small fw-bold mb-1"><i class="bi bi-shield-exclamation text-warning me-1"></i>Excepção: não suspender automaticamente</label>
              ${avisoAdiada}
              <div class="row g-2">
                <div class="col-md-4"><input type="date" id="editEscolaAdiarAte" class="form-control form-control-sm" aria-label="Não suspender até"></div>
                <div class="col-md-8"><input type="text" id="editEscolaAdiarMotivo" class="form-control form-control-sm" placeholder="Motivo obrigatório (ex.: acordo de pagamento)" maxlength="500"></div>
              </div>
              <small class="text-muted">Até à data indicada (máx. 90 dias) a escola fica no máximo em modo restrito. Fica registado na auditoria. Deixe vazio para não alterar.</small>
            </div>
          </div>
        </div>
        <div id="editEscolaErro" class="alert alert-danger py-2 small mt-3 mb-0" style="display:none" role="alert"></div>
        <button type="submit" class="btn btn-primary w-100 mt-3">Guardar alterações</button>
      </form>
    `);

    atualizarDistritosEdicaoEscola(escola.provincia || 'Maputo Cidade', escola.distrito);
    atualizarPreviewPacoteEdicao(escola.funcionalidades);
    document.getElementById('editEscolaPacote')?.addEventListener('change', () => atualizarPreviewPacoteEdicao(escola.funcionalidades));
    if (aba === 'acesso' && typeof bootstrap !== 'undefined') bootstrap.Tab.getOrCreateInstance(document.getElementById('tabEdAcesso')).show();

    const mostrarErro = (msg) => {
      const el = document.getElementById('editEscolaErro');
      if (el) { el.textContent = msg; el.style.display = ''; el.scrollIntoView({ block: 'nearest' }); }
    };

    document.getElementById('btnRemoverAdiamento')?.addEventListener('click', async () => {
      if (!confirm('Remover a excepção de suspensão desta escola?')) return;
      try {
        const r = await apiFetch(`/api/v1/saas/instituicoes/${escolaId}/adiar-suspensao`, { method: 'POST', body: JSON.stringify({ ate: null }) });
        mostrarNotificacao((r && r.message) || 'Excepção removida.', 'success');
        fecharModal();
        carregarAlarmesSaaS();
        carregarPainelSaaS();
      } catch (err) { mostrarErro(err.message || 'Erro ao remover excepção.'); }
    });

    document.getElementById('formModalEditarEscola')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const erroEl = document.getElementById('editEscolaErro');
      if (erroEl) erroEl.style.display = 'none';
      try {
        const adiarAte = document.getElementById('editEscolaAdiarAte')?.value;
        const adiarMotivo = document.getElementById('editEscolaAdiarMotivo')?.value?.trim();
        if (adiarAte) {
          if (!adiarMotivo || adiarMotivo.length < 5) {
            bootstrap.Tab.getOrCreateInstance(document.getElementById('tabEdAcesso')).show();
            return mostrarErro('Indique o motivo da excepção de suspensão (mínimo 5 caracteres).');
          }
          const rAd = await apiFetch(`/api/v1/saas/instituicoes/${escolaId}/adiar-suspensao`, {
            method: 'POST', body: JSON.stringify({ ate: adiarAte, motivo: adiarMotivo })
          });
          if (!rAd || !rAd.success) return mostrarErro((rAd && rAd.message) || 'Não foi possível registar a excepção.');
        }
        const pacoteSel = document.getElementById('editEscolaPacote')?.value || null;
        const modoCod = document.querySelector('input[name="editCodModo"]:checked')?.value || 'manter';
        let codigoManualEd;
        if (modoCod === 'manual') {
          codigoManualEd = (document.getElementById('editEscolaCodigoManual')?.value || '').trim().toUpperCase();
          if (!/^(\d{4}[PBS]\d{4,5}|\d{1,8})$/.test(codigoManualEd)) {
            return mostrarErro('Código da escola inválido. Use o formato 0101S0001 ou um código numérico de até 8 dígitos.');
          }
        }
        const body = {
          codigo_modo: modoCod,
          codigo_escola: codigoManualEd,
          nome: document.getElementById('editEscolaNome').value,
          tipo_escola: document.getElementById('editEscolaTipo')?.value || 'S',
          nif_cnpj: document.getElementById('editEscolaNUIT').value,
          email: document.getElementById('editEscolaEmail').value,
          telefone: document.getElementById('editEscolaTelefone').value,
          data_fim: document.getElementById('editEscolaDataFim').value || undefined,
          data_fim_assinatura: document.getElementById('editEscolaDataFim').value || undefined,
          dias_adicionais: Number(document.getElementById('editEscolaDiasAdicionais').value) || undefined,
          provincia: document.getElementById('editEscolaProvincia').value,
          distrito: document.getElementById('editEscolaDistrito').value,
          pacote: pacoteSel,
          facturar_por_pacote: !!document.getElementById('editEscolaFacturarPacote')?.checked && !!pacoteSel,
          usar_emblema_nacional: document.getElementById('editEscolaEmblema').checked,
          logo_url: document.getElementById('editEscolaLogoFinal')?.value || null
        };

        const updRes = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}`, {
          method: 'PATCH',
          body: JSON.stringify(body)
        });
        if (updRes && updRes.success) {
          fecharModal();
          mostrarNotificacao('Dados da escola actualizados com sucesso.', 'success');
          carregarPainelSaaS();
        } else {
          mostrarErro((updRes && updRes.message) || 'Erro ao actualizar dados');
        }
      } catch (err) {
        mostrarErro(err.message || 'Erro ao actualizar dados');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados da escola para edição: ' + err.message);
  }
}

function alternarModoCodigoEdicaoEscola() {
  const modo = document.querySelector('input[name="editCodModo"]:checked')?.value || 'manter';
  document.getElementById('editEscolaCodigoManual')?.classList.toggle('d-none', modo !== 'manual');
  document.getElementById('editCodManualAjuda')?.classList.toggle('d-none', modo !== 'manual');
  document.getElementById('editCodAviso')?.classList.toggle('d-none', modo === 'manter');
}
window.alternarModoCodigoEdicaoEscola = alternarModoCodigoEdicaoEscola;

function atualizarDistritosEdicaoEscola(provincia, distritoSelecionado = '') {
  const distritos = state.geografia?.distritos?.[provincia] || [];
  const select = document.getElementById('editEscolaDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => 
      `<option value="${d}" ${d === distritoSelecionado ? 'selected' : ''}>${d}</option>`
    ).join('');
  }
}

// ==================== 6. PREÇO DO PLANO ====================
function modalEditarPrecoPlano(planoId, nome, precoAtual) {
  const precoStr = prompt(`Defina o novo preço mensal para o plano [${nome}] em Meticais (MZN):`, precoAtual);
  if (precoStr === null) return;
  const novoPreco = parseFloat(precoStr);
  if (isNaN(novoPreco) || novoPreco < 0) {
    alert('Por favor insira um valor monetário válido.');
    return;
  }

  apiFetch(`/api/v1/saas-admin/planos/${planoId}/preco`, {
    method: 'PATCH',
    body: JSON.stringify({ preco: novoPreco })
  }).then(res => {
    if (res && res.success) {
      alert(`Preço do plano [${nome}] actualizado com sucesso para ${novoPreco.toLocaleString('pt-PT')} MZN.`);
      carregarPainelSaaS();
    } else {
      alert((res && res.message) || 'Erro ao actualizar preço.');
    }
  }).catch(err => {
    alert('Erro de comunicação: ' + err.message);
  });
}

// ==================== 7. EXTRATO / CONTRATO EM PDF ====================
async function descarregarExtratoEscolaSuperAdmin(escolaId) {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/comprovativo-contrato`);
    if (!res || !res.success) throw new Error((res && res.message) || 'Falha ao obter comprovativo');

    const c = res.data;
    const agora = new Date();
    const dataEmissao = agora.toLocaleDateString('pt-PT') + ' ' + agora.toLocaleTimeString('pt-PT');

    abrirModal('Extrato Oficial de Contrato de Prestação de Serviços SIGE', `
      <div id="printExtratoContrato" class="p-4 bg-white" style="font-family: 'Times New Roman', serif;">
        <div class="text-center border-bottom pb-3 mb-4">
          <img src="/img/emblema-mocambique.png" style="width: 50px; height: 50px; margin-bottom: 4px;" alt="Emblema Nacional">
          <h5 class="fw-bold mb-0 text-uppercase">REPÚBLICA DE MOÇAMBIQUE</h5>
          <h6 class="fw-bold text-primary mb-1">SIGE — SISTEMA INTEGRADO DE GESTÃO ESCOLAR</h6>
          <small class="text-muted">EXTRATO OFICIAL DE LICENCIAMENTO E TERMO DE CONTRATO SAAS</small>
        </div>

        <div class="row g-3 mb-4 small">
          <div class="col-6">
            <strong>Instituição de Ensino:</strong> ${c.escola?.nome}<br>
            <strong>NUIT / NIF:</strong> ${c.escola?.nif_cnpj}<br>
            <strong>Localização:</strong> ${c.escola?.distrito || '-'}, ${c.escola?.provincia || '-'}<br>
            <strong>Contacto:</strong> ${c.escola?.telefone || '-'} | ${c.escola?.email || '-'}
          </div>
          <div class="col-6 text-end">
            <strong>Referência Contratual:</strong> ${c.comprovativo_numero}<br>
            <strong>Plano Subscrito:</strong> <span class="badge bg-primary">${c.plano?.nome || 'MENSAL'}</span><br>
            <strong>Estado da Licença:</strong> <span class="badge bg-success">${c.status_atual}</span><br>
            <strong>Valor Contratual:</strong> ${formatarMoeda(c.assinatura?.valor || 0)}
          </div>
        </div>

        <div class="table-responsive">
          <table class="table table-bordered table-sm small mb-4">
            <tr class="table-light"><th colspan="2" class="text-center fw-bold">VIGÊNCIA E CLÁUSULAS CONTRATUAIS</th></tr>
            <tr><th class="w-40">Data de Início:</th><td>${c.assinatura?.data_inicio ? new Date(c.assinatura.data_inicio).toLocaleDateString('pt-PT') : '-'}</td></tr>
            <tr><th>Data de Vencimento:</th><td>${c.assinatura?.data_fim ? new Date(c.assinatura.data_fim).toLocaleDateString('pt-PT') : '-'}</td></tr>
            <tr><th>Capacidade Licenciada:</th><td>Até ${c.plano?.max_alunos || 5000} alunos matriculados e ${c.plano?.max_professores || 500} docentes</td></tr>
            <tr><th>Alunos Registados:</th><td>${c.estatisticas?.total_alunos ?? 0} alunos</td></tr>
            <tr><th>Corpo Docente Ativo:</th><td>${c.estatisticas?.total_professores ?? 0} professores</td></tr>
            <tr><th>Turmas Cadastradas:</th><td>${c.estatisticas?.total_turmas ?? 0} turmas ativas</td></tr>
          </table>
        </div>

        <div class="alert alert-light border small text-muted text-center py-2 mb-4">
          Extrato emitido aos <strong>${dataEmissao}</strong> | Assinado digitalmente pelo Engenheiro de Sistemas SuperAdmin
        </div>

        <div class="row text-center pt-4 border-top small">
          <div class="col-6">
            <p class="mb-0 border-top pt-2 mx-4 fw-bold">O Engenheiro do Sistema (SuperAdmin)</p>
            <small class="text-muted">mandamulefj.@sige.com</small>
          </div>
          <div class="col-6">
            <p class="mb-0 border-top pt-2 mx-4 fw-bold">A Direcção da Escola</p>
            <small class="text-muted">${c.escola?.nome}</small>
          </div>
        </div>
      </div>
      <div class="d-flex justify-content-end gap-2 mt-3">
        <button class="btn btn-primary" onclick="window.print()"><i class="bi bi-printer me-1"></i> Imprimir Extrato</button>
      </div>
    `);
  } catch (err) {
    alert('Erro ao gerar extrato: ' + (err.message || 'Erro desconhecido'));
  }
}

// ==================== 8. ELIMINAR ESCOLA ====================
async function eliminarEscolaSuperAdmin(escolaId, nome, codigo = '') {
  const nomeLimpo = (nome || '').replace(/\\'/g, "'");
  const rotulo = codigo ? `[${escapeHtml(codigo)}] ${escapeHtml(nomeLimpo)}` : `[${escapeHtml(nomeLimpo)}]`;
  window._eliminarEscolaPendente = { escolaId, nome: nomeLimpo };
  // Confirmação reforçada: o nome da escola tem de ser digitado; o botão só activa quando coincide.
  abrirModal('Eliminar escola definitivamente', `
    <div class="alert alert-danger small mb-3">
      <i class="bi bi-exclamation-octagon-fill me-1"></i>
      Vai eliminar <strong>${rotulo}</strong> e <strong>todos os seus dados</strong>. Esta operação <strong>não pode ser revertida</strong> e fica registada na auditoria.
    </div>
    <label class="form-label small fw-semibold" for="inputConfirmarEliminarEscola">Para confirmar, digite o nome exacto da escola:</label>
    <div class="form-text mb-1 user-select-all fw-bold">${escapeHtml(nomeLimpo)}</div>
    <input type="text" id="inputConfirmarEliminarEscola" class="form-control" autocomplete="off" oninput="validarConfirmacaoEliminarEscola()">
    <div id="erroEliminarEscola" class="text-danger small mt-2" style="display:none" role="alert"></div>
    <div class="d-flex justify-content-end gap-2 mt-3">
      <button class="btn btn-outline-secondary" onclick="fecharModal()">Cancelar</button>
      <button class="btn btn-danger" id="btnConfirmarEliminarEscola" disabled onclick="confirmarEliminarEscolaSuperAdmin()"><i class="bi bi-trash me-1"></i>Eliminar definitivamente</button>
    </div>`);
}

function validarConfirmacaoEliminarEscola() {
  const p = window._eliminarEscolaPendente;
  const digitado = (document.getElementById('inputConfirmarEliminarEscola')?.value || '').trim().toLowerCase();
  const btn = document.getElementById('btnConfirmarEliminarEscola');
  if (btn && p) btn.disabled = digitado !== p.nome.trim().toLowerCase();
}

async function confirmarEliminarEscolaSuperAdmin() {
  const p = window._eliminarEscolaPendente;
  const digitado = (document.getElementById('inputConfirmarEliminarEscola')?.value || '').trim();
  const erro = document.getElementById('erroEliminarEscola');
  if (!p || digitado.toLowerCase() !== p.nome.trim().toLowerCase()) return;
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${p.escolaId}`, {
      method: 'DELETE',
      body: JSON.stringify({ confirmar_nome: digitado })
    });
    if (res && res.success) {
      window._eliminarEscolaPendente = null;
      fecharModal();
      mostrarNotificacao(res.message || 'Instituição eliminada com sucesso.', 'success');
      carregarPainelSaaS();
      if (typeof carregarEscolasSuperAdminSelect === 'function') carregarEscolasSuperAdminSelect();
    } else if (erro) {
      erro.textContent = (res && res.message) || 'Erro ao eliminar instituição.'; erro.style.display = '';
    }
  } catch (err) {
    if (erro) { erro.textContent = err.message || 'Erro ao eliminar escola'; erro.style.display = ''; }
  }
}
// ==================== 9. LOGÓTIPO SAAS CADASTRO ====================
function processarLogoCadastroLocal(input) {
  const file = input.files?.[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    alert('Por favor, seleccione um ficheiro de imagem válido.');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    const hidden = document.getElementById('cadEscolaLogoBase64');
    if (hidden) hidden.value = e.target.result;
  };
  reader.readAsDataURL(file);
}

function processarUploadLogoModal(input, hiddenInputId, previewImgId) {
  const file = input.files?.[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    alert('Por favor, seleccione um ficheiro de imagem válido (PNG, JPG, WebP).');
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    alert('A imagem seleccionada é muito pesada (máximo 5MB).');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    const dataUrl = e.target.result;
    const hidden = document.getElementById(hiddenInputId);
    if (hidden) hidden.value = dataUrl;
    const preview = document.getElementById(previewImgId);
    if (preview) preview.src = dataUrl;
  };
  reader.readAsDataURL(file);
}

async function executarCronVerificacaoManual() {
  try {
    const res = await apiFetch('/api/v1/saas-admin/verificar-expiracoes', { method: 'POST' });
    if (res && res.success) {
      alert(`Verificação de expiração executada com sucesso!\nProcessadas: ${res.data?.processadas ?? 0}\nExpiradas: ${res.data?.expiradas ?? 0}`);
      carregarPainelSaaS();
    } else {
      alert((res && res.message) || 'Erro ao executar verificação.');
    }
  } catch (err) {
    alert('Erro ao executar verificação de expiração: ' + (err.message || 'Erro de comunicação'));
  }
}

// ==================== BINDING GLOBAL PARA ACESSO IMEDIATO ====================
window.carregarPainelSaaS = carregarPainelSaaS;
window.alternarEscolaSuperAdmin = alternarEscolaSuperAdmin;
window.sairModoInspecaoSuperAdmin = sairModoInspecaoSuperAdmin;
window.toggleStatusEscola = toggleStatusEscola;
window.executarCronVerificacaoManual = executarCronVerificacaoManual;
window.modalCadastrarEscolaSuperAdmin = modalCadastrarEscolaSuperAdmin;
window.atualizarDistritosCadastroEscola = atualizarDistritosCadastroEscola;
window.atualizarPreviewModalCadastroEscola = atualizarPreviewModalCadastroEscola;
window.submeterCadastroEscolaSuperAdmin = submeterCadastroEscolaSuperAdmin;
window.modalEditarEscolaSuperAdmin = modalEditarEscolaSuperAdmin;
window.atualizarDistritosEdicaoEscola = atualizarDistritosEdicaoEscola;
window.modalEditarPrecoPlano = modalEditarPrecoPlano;
window.descarregarExtratoEscolaSuperAdmin = descarregarExtratoEscolaSuperAdmin;
window.eliminarEscolaSuperAdmin = eliminarEscolaSuperAdmin;
window.processarLogoCadastroLocal = processarLogoCadastroLocal;
window.processarUploadLogoModal = processarUploadLogoModal;

// Auto-disparo imediato e resiliente se a tabela estiver em estado de carregamento
if (typeof document !== 'undefined') {
  const elEscolas = document.getElementById('tabelaSaasEscolas');
  if (elEscolas && (elEscolas.innerHTML.includes('spinner-border') || elEscolas.innerHTML.includes('A carregar escolas'))) {
    setTimeout(() => { carregarPainelSaaS(); }, 50);
  }
}

