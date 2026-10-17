// =====================================================================
// SIGE - PAINEL-SUPERADMIN | Módulo de Controlo de Assinaturas e Pagamentos SaaS
// =====================================================================

var listaAssinaturasCache = [];
var assinaturaAtualSelecionada = null;

async function inicializarModuloPagamentosSaas() {
  await carregarResumoSuperAdmin();
  await carregarCoordenadasPagamento();
  await carregarPagamentosPendentes();
  await carregarAssinaturasSuperAdmin();
}

async function carregarResumoSuperAdmin() {
  try {
    const res = await apiFetch('/saas/resumo/');
    if (res && res.success && res.data) {
      const d = res.data;
      const elDiv = document.getElementById('saasValorDivida');
      if (elDiv) elDiv.innerHTML = `${formatarValorMZN(d.valor_em_divida_mzn)} <span class="moeda-sufixo">MZN</span>`;

      const elRec = document.getElementById('saasReceitaMes');
      if (elRec) elRec.innerHTML = `${formatarValorMZN(d.receita_mes_mzn)} <span class="moeda-sufixo">MZN</span>`;

      const elComp = document.getElementById('saasComprovativosPendentes');
      if (elComp) elComp.innerText = d.pagamentos_pendentes_validacao || 0;

      const elTot = document.getElementById('saasTotalInstituicoes');
      if (elTot) elTot.innerText = d.total_instituicoes || 0;

      const elRes = document.getElementById('saasResumoEstados');
      if (elRes && d.estados) {
        elRes.innerText = `${d.estados.activa || 0} Activas | ${d.estados.em_atraso || 0} Atraso | ${d.estados.restrita || 0} Restritas | ${d.estados.suspensa || 0} Suspensas`;
      }
    }
  } catch (err) {
    console.error('[SAAS] Erro ao carregar resumo:', err);
  }
}

async function carregarPagamentosPendentes() {
  try {
    const res = await apiFetch('/saas/pagamentos/pendentes/');
    const card = document.getElementById('cardFilaComprovativos');
    const tbody = document.getElementById('tabelaPagamentosPendentes');
    if (!tbody) return;

    if (!res || !res.success || !res.data || res.data.length === 0) {
      if (card) card.style.display = 'none';
      tbody.innerHTML = '<tr><td colspan="8" class="text-center py-3 text-muted">Nenhum pagamento pendente de validação.</td></tr>';
      return;
    }

    if (card) card.style.display = 'block';

    tbody.innerHTML = res.data.map(p => {
      const compBtn = p.comprovativo_url
        ? `<a href="${p.comprovativo_url}" target="_blank" class="btn btn-sm btn-outline-primary" title="Abrir Comprovativo"><i class="bi bi-file-earmark-arrow-down me-1"></i> Ver Anexo</a>`
        : `<span class="badge bg-secondary">Sem anexo</span>`;

      return `
        <tr>
          <td><strong>${p.instituicao_nome || '-'}</strong></td>
          <td><span class="badge bg-light text-dark border">${p.numero_fatura || 'Fatura'}</span> <small class="text-muted d-block">${p.fatura_periodo || ''}</small></td>
          <td><span class="badge bg-info text-dark">${p.metodo}</span></td>
          <td><code>${p.referencia}</code></td>
          <td class="fw-bold text-success">${formatarValorMZN(p.valor)} <span class="moeda-sufixo">MZN</span></td>
          <td><small>${formatarDataHoraPt(p.criado_em)}</small></td>
          <td>${compBtn}</td>
          <td class="text-end">
            <div class="btn-group btn-group-sm">
              <button class="btn btn-success" onclick="confirmarPagamentoSuperAdmin('${p.id}')" title="Confirmar e Liquidar Fatura">
                <i class="bi bi-check-lg me-1"></i> Confirmar
              </button>
              <button class="btn btn-outline-danger" onclick="abrirModalRejeitarPagamento('${p.id}')" title="Rejeitar Comprovativo">
                <i class="bi bi-x-lg me-1"></i> Rejeitar
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('[SAAS] Erro ao carregar pagamentos pendentes:', err);
  }
}

async function carregarAssinaturasSuperAdmin() {
  const tbody = document.getElementById('tabelaSaasAssinaturas');
  if (!tbody) return;

  const estado = document.getElementById('filtroSaasEstado')?.value || '';
  const periodicidade = document.getElementById('filtroSaasPeriodicidade')?.value || '';

  let url = '/saas/assinaturas/?';
  if (estado) url += `estado=${estado}&`;
  if (periodicidade) url += `periodicidade=${periodicidade}&`;

  try {
    const res = await apiFetch(url);
    if (!res || !res.success || !res.data) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-danger">Falha ao obter assinaturas.</td></tr>';
      return;
    }

    listaAssinaturasCache = res.data;
    renderizarTabelaAssinaturas(listaAssinaturasCache);
  } catch (err) {
    console.error('[SAAS] Erro ao carregar assinaturas:', err);
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-danger">Erro de ligação ao carregar dados.</td></tr>';
  }
}

function filtrarTabelaAssinaturas() {
  const busca = (document.getElementById('filtroSaasBusca')?.value || '').toLowerCase().trim();
  if (!busca) {
    renderizarTabelaAssinaturas(listaAssinaturasCache);
    return;
  }

  const filtrados = listaAssinaturasCache.filter(a => {
    const nome = (a.instituicao_nome || '').toLowerCase();
    const cod = (a.instituicao_codigo || '').toLowerCase();
    const nuit = (a.instituicao_nuit || '').toLowerCase();
    return nome.includes(busca) || cod.includes(busca) || nuit.includes(busca);
  });
  renderizarTabelaAssinaturas(filtrados);
}

function renderizarTabelaAssinaturas(lista) {
  const tbody = document.getElementById('tabelaSaasAssinaturas');
  if (!tbody) return;

  if (lista.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">Nenhuma instituição encontrada com os filtros actuais.</td></tr>';
    return;
  }

  tbody.innerHTML = lista.map(a => {
    let planoNome = a.plano_detalhes?.nome || 'Plano Básico';
    planoNome = planoNome.replace(/Moçambique/gi, '').replace(/Mocambique/gi, '').trim() || 'Plano Básico';
    const preco = a.plano_detalhes?.preco_mensal ? `${formatarValorMZN(a.plano_detalhes.preco_mensal)} MZN` : '-';
    const proxFatura = a.proxima_fatura_em ? formatarDataPt(a.proxima_fatura_em) : '-';
    const badgeEstado = obterBadgeEstadoAssinatura(a.estado);

    return `
      <tr>
        <td>
          <div class="fw-bold">${a.instituicao_nome}</div>
          <small class="text-muted">Cód: ${a.instituicao_codigo || 'N/D'} | NUIT: ${a.instituicao_nuit || 'N/D'}</small>
        </td>
        <td>
          <span class="badge bg-light text-dark border">${planoNome}</span>
          <small class="text-muted d-block">${preco}/mês</small>
        </td>
        <td><span class="badge bg-secondary bg-opacity-10 text-dark text-capitalize">${a.periodicidade}</span></td>
        <td>
          <small class="d-block fw-semibold text-capitalize">${a.modo_data_limite.replace('_', ' ')}</small>
          ${a.dia_limite ? `<small class="text-muted">Dia ${a.dia_limite}</small>` : ''}
        </td>
        <td><strong>${proxFatura}</strong></td>
        <td>
          <small class="d-block">Tolerância: <strong>${a.dias_tolerancia}d</strong></small>
          <small class="text-muted">Suspensão: <strong>${a.dias_ate_suspensao}d</strong></small>
        </td>
        <td>${badgeEstado}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-primary" onclick="abrirFichaInstituicao('${a.id}')" title="Ver Histórico, Faturas e Configuração">
            <i class="bi bi-eye me-1"></i> Gerir
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function obterBadgeEstadoAssinatura(estado) {
  switch (estado) {
    case 'activa':
      return '<span class="badge bg-success">Activa</span>';
    case 'fatura_pendente':
      return '<span class="badge bg-info text-dark">Fatura Aberta</span>';
    case 'em_atraso':
      return '<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle-fill me-1"></i>Em Atraso</span>';
    case 'restrita':
      return '<span class="badge bg-danger bg-opacity-75"><i class="bi bi-lock me-1"></i>Restrita (Só Leitura)</span>';
    case 'suspensa':
      return '<span class="badge bg-danger"><i class="bi bi-slash-circle me-1"></i>Suspensa (Bloqueada)</span>';
    case 'cancelada':
      return '<span class="badge bg-dark">Cancelada</span>';
    case 'teste':
      return '<span class="badge bg-primary">Período de Teste</span>';
    default:
      return `<span class="badge bg-secondary">${estado}</span>`;
  }
}

async function abrirFichaInstituicao(assinaturaId) {
  try {
    const res = await apiFetch(`/saas/assinaturas/${assinaturaId}/`);
    if (!res || !res.success || !res.data) {
      mostrarToast('Falha ao obter detalhes da assinatura.', 'danger');
      return;
    }

    const d = res.data;
    assinaturaAtualSelecionada = d.assinatura;

    const elTitulo = document.getElementById('modalFichaInstituicaoTitulo');
    if (elTitulo) elTitulo.innerText = `Ficha de Faturação: ${assinaturaAtualSelecionada.instituicao_nome || ''}`;
    const elEscolaNome = document.getElementById('fichaEscolaNome');
    if (elEscolaNome) elEscolaNome.innerText = assinaturaAtualSelecionada.instituicao_nome || '-';
    const elEscolaCodigo = document.getElementById('fichaEscolaCodigo');
    if (elEscolaCodigo) elEscolaCodigo.innerText = assinaturaAtualSelecionada.instituicao_codigo || '-';
    const elEscolaNuit = document.getElementById('fichaEscolaNuit');
    if (elEscolaNuit) elEscolaNuit.innerText = assinaturaAtualSelecionada.instituicao_nuit || '-';
    const elEscolaProvincia = document.getElementById('fichaEscolaProvincia');
    if (elEscolaProvincia) elEscolaProvincia.innerText = assinaturaAtualSelecionada.instituicao_provincia || 'Maputo';
    const elEscolaEstado = document.getElementById('fichaEscolaEstadoBadge');
    if (elEscolaEstado) elEscolaEstado.innerHTML = obterBadgeEstadoAssinatura(assinaturaAtualSelecionada.estado);

    const elPlanoNome = document.getElementById('fichaPlanoNome');
    if (elPlanoNome) {
      let nomePlano = assinaturaAtualSelecionada.plano_detalhes?.nome || 'Plano Básico';
      nomePlano = nomePlano.replace(/Moçambique/gi, '').replace(/Mocambique/gi, '').trim() || 'Plano Básico';
      elPlanoNome.innerText = nomePlano;
    }
    const elPlanoPreco = document.getElementById('fichaPlanoPreco');
    if (elPlanoPreco) elPlanoPreco.innerText = formatarValorMZN(assinaturaAtualSelecionada.plano_detalhes?.preco_mensal || 0);
    const elPeriodicidade = document.getElementById('fichaPeriodicidade');
    if (elPeriodicidade) elPeriodicidade.innerText = (assinaturaAtualSelecionada.periodicidade || '').toUpperCase();
    const elModoDataLimite = document.getElementById('fichaModoDataLimite');
    if (elModoDataLimite) elModoDataLimite.innerText = `${(assinaturaAtualSelecionada.modo_data_limite || '').toUpperCase()} ${assinaturaAtualSelecionada.dia_limite ? '(Dia ' + assinaturaAtualSelecionada.dia_limite + ')' : ''}`;
    const elTolerancia = document.getElementById('fichaToleranciaInfo');
    if (elTolerancia) elTolerancia.innerText = `${assinaturaAtualSelecionada.dias_tolerancia} dias tolerância | ${assinaturaAtualSelecionada.dias_ate_suspensao} dias até suspensão`;
    
    const precoMensalPlano = parseFloat(assinaturaAtualSelecionada.plano_detalhes?.preco_mensal || 0);
    let multaStr = 'Nenhuma';
    if (assinaturaAtualSelecionada.multa_tipo === 'percentagem') {
      const pct = parseFloat(assinaturaAtualSelecionada.multa_valor || 0);
      const valProc = precoMensalPlano * (pct / 100);
      multaStr = `${pct}% sobre valor base (Processado: ${formatarValorMZN(valProc)} MZN)`;
    } else if (assinaturaAtualSelecionada.multa_tipo === 'fixo') {
      multaStr = `${formatarValorMZN(assinaturaAtualSelecionada.multa_valor)} MZN (Fixo)`;
    }
    const elMulta = document.getElementById('fichaMultaInfo');
    if (elMulta) elMulta.innerText = multaStr;

    // 1. Tabela Faturas
    const tbodyFat = document.getElementById('tabelaFichaFaturas');
    if (tbodyFat) {
      if (d.faturas && d.faturas.length > 0) {
        tbodyFat.innerHTML = d.faturas.map(f => {
          const estadoFat = f.estado === 'paga' 
            ? '<span class="badge bg-success">Paga</span>' 
            : (f.estado === 'em_atraso' ? '<span class="badge bg-danger">Em Atraso</span>' : '<span class="badge bg-warning text-dark">Aberta</span>');

          return `
            <tr>
              <td><strong>${f.numero_fatura}</strong></td>
              <td><small>${formatarDataPt(f.periodo_inicio)} a ${formatarDataPt(f.periodo_fim)}</small></td>
              <td>${formatarValorMZN(f.valor)} MZN</td>
              <td><span class="text-danger">${formatarValorMZN(f.multa_aplicada)} MZN</span></td>
              <td class="text-success fw-bold">${formatarValorMZN(f.valor_pago)} MZN</td>
              <td><span class="badge bg-light text-dark border">${formatarDataPt(f.data_limite_efectiva)}</span></td>
              <td>${estadoFat}</td>
              <td class="text-end">
                ${f.estado !== 'paga' ? `<button class="btn btn-sm btn-outline-info" onclick="abrirModalProrrogarFatura('${f.id}', '${f.numero_fatura}', '${f.data_limite_efectiva}')"><i class="bi bi-calendar-plus me-1"></i> Prorrogar</button>` : '<span class="text-muted small">Liquidada</span>'}
              </td>
            </tr>
          `;
        }).join('');
      } else {
        tbodyFat.innerHTML = '<tr><td colspan="8" class="text-center py-3 text-muted">Nenhuma fatura emitida para este período.</td></tr>';
      }
    }

    // 2. Tabela Pagamentos
    const tbodyPag = document.getElementById('tabelaFichaPagamentos');
    if (tbodyPag) {
      if (d.pagamentos && d.pagamentos.length > 0) {
        tbodyPag.innerHTML = d.pagamentos.map(p => `
          <tr>
            <td><small>${formatarDataHoraPt(p.criado_em)}</small></td>
            <td><span class="badge bg-light text-dark border">${p.metodo}</span></td>
            <td><code>${p.referencia}</code></td>
            <td class="fw-bold text-success">${formatarValorMZN(p.valor)} MZN</td>
            <td><span class="badge ${p.estado === 'confirmado' ? 'bg-success' : (p.estado === 'rejeitado' ? 'bg-danger' : 'bg-warning text-dark')}">${p.estado}</span></td>
            <td><small>${p.confirmado_por || '-'}</small></td>
            <td class="text-end">
              ${p.comprovativo_url ? `<a href="${p.comprovativo_url}" target="_blank" class="btn btn-sm btn-outline-secondary"><i class="bi bi-download"></i></a>` : '-'}
            </td>
          </tr>
        `).join('');
      } else {
        tbodyPag.innerHTML = '<tr><td colspan="7" class="text-center py-3 text-muted">Nenhum pagamento registado.</td></tr>';
      }
    }

    // 3. Tabela Auditoria
    const tbodyAud = document.getElementById('tabelaFichaAuditoria');
    if (tbodyAud) {
      if (d.auditoria && d.auditoria.length > 0) {
        tbodyAud.innerHTML = d.auditoria.map(l => `
          <tr>
            <td><small>${formatarDataHoraPt(l.criado_em)}</small></td>
            <td><span class="badge bg-light text-dark border">${l.accao}</span></td>
            <td><small>${l.estado_anterior || '-'} ➔ <strong>${l.estado_novo || '-'}</strong></small></td>
            <td><small>${l.feito_por}</small></td>
            <td><small class="text-muted">${l.motivo || '-'}</small></td>
          </tr>
        `).join('');
      } else {
        tbodyAud.innerHTML = '<tr><td colspan="5" class="text-center py-3 text-muted">Sem registos de auditoria adicionais.</td></tr>';
      }
    }

    const modalEl = document.getElementById('modalFichaInstituicao');
    if (modalEl && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
      const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
      modal.show();
    }
  } catch (err) {
    console.error('[SAAS] Erro ao abrir ficha:', err);
    mostrarToast('Erro ao carregar dados da instituição: ' + (err.message || 'Falha de renderização'), 'danger');
  }
}

function abrirModalConfigurarAssinatura() {
  if (!assinaturaAtualSelecionada) return;

  document.getElementById('cfgAssinaturaId').value = assinaturaAtualSelecionada.id;
  document.getElementById('cfgPeriodicidade').value = assinaturaAtualSelecionada.periodicidade;
  document.getElementById('cfgModoDataLimite').value = assinaturaAtualSelecionada.modo_data_limite;
  document.getElementById('cfgDiaLimite').value = assinaturaAtualSelecionada.dia_limite || '';
  document.getElementById('cfgDiasTolerancia').value = assinaturaAtualSelecionada.dias_tolerancia;
  document.getElementById('cfgDiasAteSuspensao').value = assinaturaAtualSelecionada.dias_ate_suspensao;
  document.getElementById('cfgDataBloqueioManual').value = assinaturaAtualSelecionada.data_bloqueio_manual || '';

  const tipoMulta = assinaturaAtualSelecionada.multa_tipo || 'percentagem';
  document.getElementById('cfgMultaTipo').value = tipoMulta;

  const inputPct = document.getElementById('cfgMultaPercentagem');
  if (tipoMulta === 'percentagem') {
    inputPct.value = (assinaturaAtualSelecionada.multa_valor != null && parseFloat(assinaturaAtualSelecionada.multa_valor) > 0)
      ? parseFloat(assinaturaAtualSelecionada.multa_valor)
      : 10.0;
  } else if (tipoMulta === 'fixo') {
    inputPct.value = assinaturaAtualSelecionada.multa_valor != null ? parseFloat(assinaturaAtualSelecionada.multa_valor) : 0.0;
  } else {
    inputPct.value = 0;
  }

  aoMudarModoDataLimite();
  aoMudarTipoMulta();
  calcularMultaAutomatica();

  const modalEl = document.getElementById('modalConfigurarAssinatura');
  if (modalEl && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.show();
  }
}

function aoMudarModoDataLimite() {
  const modo = document.getElementById('cfgModoDataLimite').value;
  const boxDia = document.getElementById('boxDiaFixo');
  if (boxDia) {
    boxDia.style.display = modo === 'dia_fixo' ? 'block' : 'none';
  }
}

function obterValorBaseContrato() {
  const precoMensal = parseFloat(assinaturaAtualSelecionada?.plano_detalhes?.preco_mensal || 0);
  const per = document.getElementById('cfgPeriodicidade')?.value || 'mensal';
  if (per === 'trimestral') return precoMensal * 3 * 0.95;
  if (per === 'semestral') return precoMensal * 6 * 0.90;
  if (per === 'anual') return precoMensal * 12 * 0.85;
  return precoMensal;
}

function aoMudarPeriodicidadeConfig() {
  calcularMultaAutomatica();
}

function aoMudarTipoMulta() {
  const tipo = document.getElementById('cfgMultaTipo')?.value || 'percentagem';
  const boxPct = document.getElementById('boxMultaPercentagem');
  const boxProc = document.getElementById('boxMultaValorProcessado');
  const lblEntrada = document.getElementById('lblMultaEntrada');
  const sufixoEntrada = document.getElementById('sufixoMultaEntrada');
  const ajudaEntrada = document.getElementById('ajudaMultaEntrada');
  const inputPct = document.getElementById('cfgMultaPercentagem');

  if (tipo === 'percentagem') {
    if (boxPct) boxPct.style.display = 'block';
    if (boxProc) boxProc.style.display = 'block';
    if (lblEntrada) lblEntrada.innerText = 'Percentagem da Multa (%)';
    if (sufixoEntrada) sufixoEntrada.innerText = '%';
    if (ajudaEntrada) ajudaEntrada.innerText = 'Taxa percentual aplicada à fatura.';
    if (inputPct && (!inputPct.value || parseFloat(inputPct.value) === 0)) {
      inputPct.value = '10.0';
    }
  } else if (tipo === 'fixo') {
    if (boxPct) boxPct.style.display = 'block';
    if (boxProc) boxProc.style.display = 'block';
    if (lblEntrada) lblEntrada.innerText = 'Valor Fixo da Multa (MZN)';
    if (sufixoEntrada) sufixoEntrada.innerText = 'MZN';
    if (ajudaEntrada) ajudaEntrada.innerText = 'Montante estipulado em Meticais.';
  } else {
    // nenhuma
    if (boxPct) boxPct.style.display = 'none';
    if (boxProc) boxProc.style.display = 'none';
  }
  calcularMultaAutomatica();
}

function calcularMultaAutomatica() {
  const tipo = document.getElementById('cfgMultaTipo')?.value || 'percentagem';
  const valorBase = obterValorBaseContrato();
  const elCalculado = document.getElementById('cfgMultaValorCalculado');
  const elBaseInfo = document.getElementById('cfgMultaBaseInfo');
  const elHidden = document.getElementById('cfgMultaValor');
  const inputPct = document.getElementById('cfgMultaPercentagem');

  if (tipo === 'percentagem') {
    const pct = parseFloat(inputPct?.value || 0);
    const valorMulta = valorBase * (pct / 100);
    if (elCalculado) elCalculado.value = formatarValorMZN(valorMulta);
    if (elBaseInfo) {
      elBaseInfo.innerHTML = `Base: <strong>${formatarValorMZN(valorBase)} MZN</strong> × <strong>${pct}%</strong> = <span class="text-danger fw-bold">${formatarValorMZN(valorMulta)} MZN</span>`;
    }
    if (elHidden) elHidden.value = pct;
  } else if (tipo === 'fixo') {
    const val = parseFloat(inputPct?.value || 0);
    if (elCalculado) elCalculado.value = formatarValorMZN(val);
    if (elBaseInfo) {
      elBaseInfo.innerText = `Valor fixo por atraso: ${formatarValorMZN(val)} MZN`;
    }
    if (elHidden) elHidden.value = val;
  } else {
    if (elCalculado) elCalculado.value = '0,00';
    if (elBaseInfo) elBaseInfo.innerText = 'Isento de multa por atraso.';
    if (elHidden) elHidden.value = '0.00';
  }
}

async function salvarConfiguracaoAssinatura(event) {
  event.preventDefault();
  const id = document.getElementById('cfgAssinaturaId').value;
  const tipoMulta = document.getElementById('cfgMultaTipo').value;
  let valorMulta = 0;
  if (tipoMulta === 'percentagem' || tipoMulta === 'fixo') {
    valorMulta = parseFloat(document.getElementById('cfgMultaPercentagem').value || 0);
  }

  const payload = {
    periodicidade: document.getElementById('cfgPeriodicidade').value,
    modo_data_limite: document.getElementById('cfgModoDataLimite').value,
    dia_limite: document.getElementById('cfgDiaLimite').value ? parseInt(document.getElementById('cfgDiaLimite').value) : null,
    dias_tolerancia: parseInt(document.getElementById('cfgDiasTolerancia').value),
    dias_ate_suspensao: parseInt(document.getElementById('cfgDiasAteSuspensao').value),
    data_bloqueio_manual: document.getElementById('cfgDataBloqueioManual').value || null,
    multa_tipo: tipoMulta,
    multa_valor: valorMulta
  };

  try {
    const res = await apiFetch(`/saas/assinaturas/${id}/configurar/`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });

    if (res && res.success) {
      mostrarToast('Parâmetros da assinatura actualizados com sucesso!', 'success');
      bootstrap.Modal.getInstance(document.getElementById('modalConfigurarAssinatura'))?.hide();
      await abrirFichaInstituicao(id);
      await carregarAssinaturasSuperAdmin();
    } else {
      mostrarToast(res?.message || 'Erro ao guardar configuração.', 'danger');
    }
  } catch (err) {
    console.error('[SAAS] Erro ao salvar configuração:', err);
    mostrarToast('Erro de comunicação ao salvar parâmetros.', 'danger');
  }
}

async function confirmarPagamentoSuperAdmin(pagamentoId) {
  if (!confirm('Tem a certeza que deseja confirmar este pagamento? A fatura será liquidada e a instituição reactivada imediatamente.')) return;

  try {
    const res = await apiFetch(`/saas/pagamentos/${pagamentoId}/confirmar/`, {
      method: 'POST'
    });

    if (res && res.success) {
      mostrarToast('Pagamento confirmado e fatura liquidada com sucesso!', 'success');
      await carregarResumoSuperAdmin();
      await carregarPagamentosPendentes();
      await carregarAssinaturasSuperAdmin();
      if (assinaturaAtualSelecionada) {
        await abrirFichaInstituicao(assinaturaAtualSelecionada.id);
      }
    } else {
      mostrarToast(res?.message || 'Falha ao confirmar pagamento.', 'danger');
    }
  } catch (err) {
    console.error('[SAAS] Erro ao confirmar pagamento:', err);
    mostrarToast('Falha na ligação com o servidor.', 'danger');
  }
}

function abrirModalRejeitarPagamento(pagamentoId) {
  document.getElementById('rejeitarPagamentoId').value = pagamentoId;
  document.getElementById('rejeitarMotivo').value = '';
  const modal = new bootstrap.Modal(document.getElementById('modalRejeitarPagamento'));
  modal.show();
}

async function salvarRejeicaoPagamento(event) {
  event.preventDefault();
  const id = document.getElementById('rejeitarPagamentoId').value;
  const motivo = document.getElementById('rejeitarMotivo').value.trim();

  if (!motivo) {
    mostrarToast('A justificação é obrigatória.', 'warning');
    return;
  }

  try {
    const res = await apiFetch(`/saas/pagamentos/${id}/rejeitar/`, {
      method: 'POST',
      body: JSON.stringify({ motivo: motivo })
    });

    if (res && res.success) {
      mostrarToast('Comprovativo de pagamento rejeitado com sucesso.', 'info');
      bootstrap.Modal.getInstance(document.getElementById('modalRejeitarPagamento'))?.hide();
      await carregarPagamentosPendentes();
      await carregarAssinaturasSuperAdmin();
    } else {
      mostrarToast(res?.message || 'Falha ao rejeitar pagamento.', 'danger');
    }
  } catch (err) {
    console.error('[SAAS] Erro ao rejeitar:', err);
    mostrarToast('Erro de comunicação.', 'danger');
  }
}

function abrirModalProrrogarFatura(faturaId, numeroFatura, dataLimiteAtual) {
  document.getElementById('prorrogarFaturaId').value = faturaId;
  document.getElementById('prorrogarFaturaNumero').value = numeroFatura;
  document.getElementById('prorrogarNovaData').value = dataLimiteAtual || '';
  document.getElementById('prorrogarMotivo').value = '';

  const modal = new bootstrap.Modal(document.getElementById('modalProrrogarFatura'));
  modal.show();
}

async function salvarProrrogacaoFatura(event) {
  event.preventDefault();
  const faturaId = document.getElementById('prorrogarFaturaId').value;
  const novaData = document.getElementById('prorrogarNovaData').value;
  const motivo = document.getElementById('prorrogarMotivo').value.trim();

  try {
    const res = await apiFetch(`/saas/faturas/${faturaId}/prorrogar/`, {
      method: 'POST',
      body: JSON.stringify({ nova_data: novaData, motivo: motivo })
    });

    if (res && res.success) {
      mostrarToast('Data-limite prorrogada com sucesso!', 'success');
      bootstrap.Modal.getInstance(document.getElementById('modalProrrogarFatura'))?.hide();
      if (assinaturaAtualSelecionada) {
        await abrirFichaInstituicao(assinaturaAtualSelecionada.id);
      }
      await carregarAssinaturasSuperAdmin();
    } else {
      mostrarToast(res?.message || 'Erro ao prorrogar data.', 'danger');
    }
  } catch (err) {
    console.error('[SAAS] Erro ao prorrogar:', err);
    mostrarToast('Falha na comunicação com o servidor.', 'danger');
  }
}

function modalSuspenderManualInstituicao() {
  if (!assinaturaAtualSelecionada) return;
  document.getElementById('acaoManualTipo').value = 'suspender';
  document.getElementById('acaoManualInstituicaoId').value = assinaturaAtualSelecionada.instituicao;
  document.getElementById('modalAcaoManualTitulo').innerText = 'Suspender Acesso da Instituição';
  document.getElementById('modalAcaoManualHeader').className = 'modal-header bg-danger text-white';
  document.getElementById('btnAcaoManualSubmit').className = 'btn btn-danger fw-bold';
  document.getElementById('btnAcaoManualSubmit').innerText = 'Confirmar Suspensão';
  document.getElementById('acaoManualAviso').innerHTML = `<strong>Atenção:</strong> O acesso de todos os utilizadores da instituição <em>${assinaturaAtualSelecionada.instituicao_nome}</em> será bloqueado. Apenas o administrador terá acesso ao ecrã de regularização. <strong>Nenhum dado será apagado.</strong>`;
  document.getElementById('acaoManualMotivo').value = '';

  const modal = new bootstrap.Modal(document.getElementById('modalAcaoManualInstituicao'));
  modal.show();
}

function modalReactivarManualInstituicao() {
  if (!assinaturaAtualSelecionada) return;
  document.getElementById('acaoManualTipo').value = 'reactivar';
  document.getElementById('acaoManualInstituicaoId').value = assinaturaAtualSelecionada.instituicao;
  document.getElementById('modalAcaoManualTitulo').innerText = 'Reactivar Acesso da Instituição';
  document.getElementById('modalAcaoManualHeader').className = 'modal-header bg-success text-white';
  document.getElementById('btnAcaoManualSubmit').className = 'btn btn-success fw-bold';
  document.getElementById('btnAcaoManualSubmit').innerText = 'Confirmar Reactivação';
  document.getElementById('acaoManualAviso').innerHTML = `O acesso da instituição <em>${assinaturaAtualSelecionada.instituicao_nome}</em> será totalmente restaurado de imediato com todos os dados intactos.`;
  document.getElementById('acaoManualMotivo').value = '';

  const modal = new bootstrap.Modal(document.getElementById('modalAcaoManualInstituicao'));
  modal.show();
}

async function salvarAcaoManualInstituicao(event) {
  event.preventDefault();
  const acao = document.getElementById('acaoManualTipo').value;
  const instituicaoId = document.getElementById('acaoManualInstituicaoId').value;
  const motivo = document.getElementById('acaoManualMotivo').value.trim();

  if (!motivo) {
    mostrarToast('A justificação é obrigatória.', 'warning');
    return;
  }

  try {
    const res = await apiFetch(`/saas/instituicoes/${instituicaoId}/suspender-reactivar/`, {
      method: 'POST',
      body: JSON.stringify({ acao: acao, motivo: motivo })
    });

    if (res && res.success) {
      mostrarToast(`Instituição ${acao === 'suspender' ? 'suspensa' : 'reactivada'} com sucesso!`, 'success');
      bootstrap.Modal.getInstance(document.getElementById('modalAcaoManualInstituicao'))?.hide();
      if (assinaturaAtualSelecionada) {
        await abrirFichaInstituicao(assinaturaAtualSelecionada.id);
      }
      await carregarAssinaturasSuperAdmin();
      await carregarResumoSuperAdmin();
    } else {
      mostrarToast(res?.message || 'Falha ao executar operação.', 'danger');
    }
  } catch (err) {
    console.error('[SAAS] Erro em operação manual:', err);
    mostrarToast('Erro de comunicação.', 'danger');
  }
}

async function executarCicloDiarioManual() {
  if (!confirm('Deseja executar a rotina diária de faturação e atualização de estados agora?')) return;

  try {
    const res = await apiFetch('/saas/rotina-diaria/', { method: 'POST' });
    if (res && res.success) {
      mostrarToast('Ciclo diário processado com sucesso!', 'success');
      await inicializarModuloPagamentosSaas();
    } else {
      mostrarToast(res?.message || 'Falha na execução do ciclo.', 'danger');
    }
  } catch (err) {
    console.error('[SAAS] Erro ao executar ciclo:', err);
    mostrarToast('Falha na comunicação.', 'danger');
  }
}

function formatarValorMZN(valor) {
  const num = parseFloat(valor || 0);
  return num.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatarDataPt(dataStr) {
  if (!dataStr) return '-';
  const d = new Date(dataStr + 'T00:00:00');
  return isNaN(d) ? dataStr : d.toLocaleDateString('pt-PT');
}

function formatarDataHoraPt(dtStr) {
  if (!dtStr) return '-';
  const d = new Date(dtStr);
  return isNaN(d) ? dtStr : d.toLocaleString('pt-PT');
}

var coordenadasPagamentoCache = null;

async function carregarCoordenadasPagamento() {
  try {
    const res = await apiFetch('/saas/coordenadas/');
    const elResumo = document.getElementById('resumoCoordenadasSuperAdmin');
    if (res && res.success && res.data) {
      coordenadasPagamentoCache = res.data;
      const c = res.data;
      const partes = [];
      if (c.mpesa_numero) partes.push(`M-Pesa: ${c.mpesa_numero}`);
      if (c.emola_numero) partes.push(`e-Mola: ${c.emola_numero}`);
      if (c.bim_conta) partes.push(`BIM Conta: ${c.bim_conta}`);
      if (c.bci_conta) partes.push(`BCI Conta: ${c.bci_conta}`);
      if (c.nuit_entidade) partes.push(`NUIT: ${c.nuit_entidade}`);

      if (elResumo) {
        if (partes.length > 0) {
          elResumo.innerHTML = `<span class="text-success"><i class="bi bi-check-circle me-1"></i>Configuradas:</span> ${partes.join(' | ')}`;
        } else {
          elResumo.innerHTML = `<span class="text-warning"><i class="bi bi-dash-circle me-1"></i>Deixado em branco para inserção (nenhuma conta fictícia registada). Clique em 'Inserir / Editar Dados'.</span>`;
        }
      }
    }
  } catch (err) {
    console.error('[SAAS] Erro ao carregar coordenadas:', err);
  }
}

function abrirModalCoordenadasPagamento() {
  const c = coordenadasPagamentoCache || {};
  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val || '';
  };

  setVal('coordInpMpesaNumero', c.mpesa_numero);
  setVal('coordInpMpesaTitular', c.mpesa_titular);
  setVal('coordInpEmolaNumero', c.emola_numero);
  setVal('coordInpEmolaTitular', c.emola_titular);
  setVal('coordInpBimConta', c.bim_conta);
  setVal('coordInpBimNib', c.bim_nib);
  setVal('coordInpBimTitular', c.bim_titular);
  setVal('coordInpBciConta', c.bci_conta);
  setVal('coordInpBciNib', c.bci_nib);
  setVal('coordInpBciTitular', c.bci_titular);
  setVal('coordInpNuit', c.nuit_entidade);
  setVal('coordInpInstrucoes', c.instrucoes_adicionais);

  const modal = new bootstrap.Modal(document.getElementById('modalCoordenadasPagamento'));
  modal.show();
}

async function salvarCoordenadasPagamento(event) {
  event.preventDefault();
  const btn = document.getElementById('btnSalvarCoordenadas');
  if (btn) btn.disabled = true;

  const getVal = (id) => (document.getElementById(id)?.value || '').trim();

  const payload = {
    mpesa_numero: getVal('coordInpMpesaNumero'),
    mpesa_titular: getVal('coordInpMpesaTitular'),
    emola_numero: getVal('coordInpEmolaNumero'),
    emola_titular: getVal('coordInpEmolaTitular'),
    bim_conta: getVal('coordInpBimConta'),
    bim_nib: getVal('coordInpBimNib'),
    bim_titular: getVal('coordInpBimTitular'),
    bci_conta: getVal('coordInpBciConta'),
    bci_nib: getVal('coordInpBciNib'),
    bci_titular: getVal('coordInpBciTitular'),
    nuit_entidade: getVal('coordInpNuit'),
    instrucoes_adicionais: getVal('coordInpInstrucoes')
  };

  try {
    const res = await apiFetch('/saas/coordenadas/', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res && res.success) {
      mostrarToast('Contas oficiais atualizadas com sucesso!', 'success');
      bootstrap.Modal.getInstance(document.getElementById('modalCoordenadasPagamento'))?.hide();
      await carregarCoordenadasPagamento();
    } else {
      mostrarToast(res?.message || 'Falha ao guardar contas oficiais.', 'danger');
    }
  } catch (err) {
    console.error('[SAAS] Erro ao salvar coordenadas:', err);
    mostrarToast('Falha de ligação com o servidor.', 'danger');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// Invocação automática ao carregar a página
if (document.getElementById('view-pagamentos-saas')) {
  inicializarModuloPagamentosSaas();
}
