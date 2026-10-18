/**
 * SIGE — Módulo Gateway SMS, USSD e Pagamentos Móveis
 * Central Operacional: Envio de SMS, Cobrança M-Pesa/e-Mola, USSD e Especificação
 */

let stateCarteiraAtiva = 'MPESA';
let stateUssdTextoAcumulado = '';
let stateUssdSessionId = 'USSD-SES-' + Date.now();

async function carregarPromptGateway() {
  await Promise.all([
    carregarEstatisticasGateway(),
    carregarTurmasParaSms(),
    carregarAlunosParaPagamentoMovel(),
    carregarHistoricoSms(),
    carregarTransacoesGateway(),
    carregarConteudoPromptTecnico()
  ]);

  if (typeof window.inicializarPromptGateway === 'function') {
    window.inicializarPromptGateway();
  }
}

// 1. CARREGAR ESTATÍSTICAS
async function carregarEstatisticasGateway() {
  try {
    const res = await apiFetch('/api/v1/ferramentas/stats', { ignoreAuthRedirect: true });
    if (res && res.success) {
      const elSaldo = document.getElementById('gwCardSaldoSms');
      if (elSaldo) elSaldo.textContent = (res.saldo_creditos_sms || 2850).toLocaleString('pt-PT');

      const elTaxa = document.getElementById('gwCardTaxaEntrega');
      if (elTaxa) elTaxa.textContent = res.taxa_entrega_sms || '99.4%';

      const elTotalSms = document.getElementById('gwCardTotalSms');
      if (elTotalSms) elTotalSms.textContent = (res.total_sms_enviados || 0).toLocaleString('pt-PT');

      const elTotalPag = document.getElementById('gwCardTotalPagamentos');
      if (elTotalPag) elTotalPag.textContent = (res.total_pagamentos_moveis || 0).toLocaleString('pt-PT');

      const elVolume = document.getElementById('gwCardVolumeMzn');
      if (elVolume) elVolume.innerHTML = `${(res.volume_pagamentos_mzn || 0).toLocaleString('pt-PT', { minimumFractionDigits: 2 })} <span class="fs-6 text-muted">MZN</span>`;
    }
  } catch (err) {
    console.warn('[GATEWAY] Aviso ao carregar estatísticas:', err);
  }
}

// 2. CARREGAR TURMAS NO SELECT DE SMS
async function carregarTurmasParaSms() {
  const sel = document.getElementById('smsTurmaId');
  if (!sel) return;

  try {
    let turmas = state.todasTurmas || [];
    if (!turmas || turmas.length === 0) {
      const res = await apiFetch('/api/v1/escola-admin/turmas', { ignoreAuthRedirect: true });
      if (res && res.success && Array.isArray(res.data)) {
        turmas = res.data;
        state.todasTurmas = turmas;
      }
    }

    if (turmas && turmas.length > 0) {
      let optHtml = '<option value="">-- Selecione a Turma --</option>';
      turmas.forEach(t => {
        const nomeTurma = t.nome || `${t.grau || ''}ª Classe ${t.seccao || ''}`.trim();
        optHtml += `<option value="${t.id}">${escapeHtml(nomeTurma)}</option>`;
      });
      sel.innerHTML = optHtml;
    } else {
      sel.innerHTML = '<option value="">Nenhuma turma encontrada</option>';
    }
  } catch (_) {
    sel.innerHTML = '<option value="">Turmas indisponíveis</option>';
  }
}

// 3. CARREGAR ALUNOS NO SELECT DE PAGAMENTOS
async function carregarAlunosParaPagamentoMovel() {
  const sel = document.getElementById('pagamentoAlunoSelect');
  if (!sel) return;

  try {
    let alunos = state.todosAlunos || [];
    if (!alunos || alunos.length === 0) {
      const res = await apiFetch('/api/v1/alunos', { ignoreAuthRedirect: true });
      if (res && res.success && Array.isArray(res.data)) {
        alunos = res.data;
        state.todosAlunos = alunos;
      }
    }

    if (alunos && alunos.length > 0) {
      let optHtml = '<option value="">-- Cobrança Direta / Selecione Aluno --</option>';
      alunos.forEach(al => {
        const nomeCompleto = `${al.nome || ''} ${al.apelido || ''}`.trim();
        const mat = al.matricula || '';
        const tel = al.telefone_encarregado || al.telefone || '';
        optHtml += `<option value="${al.id}" data-telefone="${escapeHtml(tel)}" data-nome="${escapeHtml(nomeCompleto)}">${escapeHtml(nomeCompleto)} (${escapeHtml(mat)})</option>`;
      });
      sel.innerHTML = optHtml;
    }
  } catch (_) {}
}

// ==============================================================================
// GESTÃO DE SMS
// ==============================================================================
function aoMudarModoSms(modo) {
  const boxTurma = document.getElementById('boxSmsTurmaSelect');
  const boxManual = document.getElementById('boxSmsTelefonesManuais');

  if (modo === 'TURMA') {
    boxTurma?.classList.remove('d-none');
    boxManual?.classList.add('d-none');
  } else if (modo === 'MANUAL') {
    boxTurma?.classList.add('d-none');
    boxManual?.classList.remove('d-none');
  } else {
    // PROPINAS_PENDENTES ou TODOS
    boxTurma?.classList.add('d-none');
    boxManual?.classList.add('d-none');
  }
}

const MODELOS_SMS = {
  PROPINA: "Prezado Encarregado de {aluno}, lembramos que a propina de {mes} no valor de {valor} MZN tem vencimento proximo. Evite multas pagando via M-Pesa ou e-Mola. SIGE.",
  RECIBO: "SIGE: Confirmamos a liquidacao da propina de {aluno} referente a {mes}. Valor: {valor} MZN. Recibo disponivel no portal do estudante. Obrigado!",
  REUNIAO: "Convocatoria: Convidamos o encarregado de {aluno} para a Reuniao Geral de Pais e Encarregados de Educacao neste Sabado as 08h30 na escola. Direccao SIGE.",
  FALTA: "Aviso Escolar: O estudante {aluno} registou falta no dia de hoje. Agradecemos contacto com a Direccao Pedagogica ou Professor de Turma. SIGE.",
  PAUTA: "Informacao Escolar: As pautas de avaliacao trimestral de {aluno} ja estao homologadas e disponiveis para consulta no portal e via USSD *123#. SIGE."
};

function aplicarModeloSms(tipoModelo) {
  const txt = MODELOS_SMS[tipoModelo] || '';
  const textarea = document.getElementById('smsTexto');
  if (textarea) {
    textarea.value = txt;
    aoDigitarTextoSms(txt);
  }
}

function aoDigitarTextoSms(texto) {
  const preview = document.getElementById('smsPreviewTexto');
  if (preview) {
    preview.textContent = texto || '[A mensagem digitada aparecerá aqui...]';
  }

  const tam = (texto || '').length;
  const temEspeciais = Array.from(texto || '').some(c => c.charCodeAt(0) > 127);
  const limite1 = temEspeciais ? 70 : 160;
  const limiteSeguintes = temEspeciais ? 67 : 153;

  let segmentos = 1;
  if (tam > limite1) {
    segmentos = Math.ceil(tam / limiteSeguintes);
  }

  const contadorEl = document.getElementById('smsContadorCaracteres');
  if (contadorEl) {
    contadorEl.textContent = `${tam} / ${limite1} car. (${segmentos} SMS)`;
    if (tam > limite1) {
      contadorEl.className = 'small fw-bold text-warning';
    } else {
      contadorEl.className = 'small fw-semibold text-secondary';
    }
  }

  const badgeEl = document.getElementById('smsCodificacaoBadge');
  if (badgeEl) {
    badgeEl.textContent = temEspeciais ? 'Codificação: UCS-2 (70 car.)' : 'Codificação: GSM-7 (160 car.)';
  }
}

async function executarEnvioSms() {
  const modo = document.getElementById('smsModoSelect')?.value || 'MANUAL';
  const mensagem = (document.getElementById('smsTexto')?.value || '').trim();
  const tipo = document.getElementById('smsTipoSelect')?.value || 'AVISO';

  if (!mensagem) {
    mostrarToast('Por favor, introduza o texto da mensagem antes de enviar.', 'warning');
    document.getElementById('smsTexto')?.focus();
    return;
  }

  const payload = { modo, mensagem, tipo };

  if (modo === 'MANUAL') {
    const tels = (document.getElementById('smsTelefones')?.value || '').trim();
    if (!tels) {
      mostrarToast('Por favor, introduza pelo menos um número de telemóvel.', 'warning');
      document.getElementById('smsTelefones')?.focus();
      return;
    }
    payload.destinatarios = tels;
  } else if (modo === 'TURMA') {
    const turmaId = document.getElementById('smsTurmaId')?.value;
    if (!turmaId) {
      mostrarToast('Por favor, selecione uma turma.', 'warning');
      return;
    }
    payload.turma_id = turmaId;
  }

  const btn = document.getElementById('btnDispararSms');
  const btnOriginal = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> A disparar SMS na rede...';
  }

  try {
    const res = await apiFetch('/api/v1/ferramentas/sms/enviar', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res && res.success) {
      mostrarToast(res.message || 'SMS enviado com sucesso!', 'success');
      if (document.getElementById('smsTexto')) document.getElementById('smsTexto').value = '';
      if (document.getElementById('smsTelefones')) document.getElementById('smsTelefones').value = '';
      aoDigitarTextoSms('');
      await carregarHistoricoSms();
      await carregarEstatisticasGateway();
    } else {
      mostrarToast((res && res.message) || 'Falha ao enviar SMS.', 'danger');
    }
  } catch (err) {
    console.error('[SMS] Erro ao enviar:', err);
    mostrarToast('Erro de conexão ao enviar SMS: ' + (err.message || ''), 'danger');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = btnOriginal;
    }
  }
}

async function carregarHistoricoSms() {
  const tbody = document.getElementById('tabelaHistoricoSmsCorpo');
  if (!tbody) return;

  try {
    const res = await apiFetch('/api/v1/ferramentas/sms/historico', { ignoreAuthRedirect: true });
    const lista = (res && res.data) || [];

    if (lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">Nenhum SMS enviado recentemente.</td></tr>';
      return;
    }

    let html = '';
    lista.forEach(m => {
      let badgeOp = '<span class="badge bg-secondary">OUTRA</span>';
      if (m.operadora === 'VODACOM') badgeOp = '<span class="badge bg-danger">Vodacom</span>';
      if (m.operadora === 'MOVITEL') badgeOp = '<span class="badge bg-warning text-dark">Movitel</span>';
      if (m.operadora === 'TMCEL') badgeOp = '<span class="badge bg-info text-dark">Tmcel</span>';

      html += `
        <tr>
          <td class="small text-muted text-nowrap">${escapeHtml(m.data)}</td>
          <td>
            <div class="fw-semibold small">${escapeHtml(m.destinatario)}</div>
            <small class="text-muted">${escapeHtml(m.nome_destinatario)}</small>
          </td>
          <td>${badgeOp}</td>
          <td class="small text-truncate" style="max-width: 200px;" title="${escapeHtml(m.mensagem)}">
            ${escapeHtml(m.mensagem)}
          </td>
          <td>
            <span class="badge bg-success-subtle text-success border border-success-subtle small">
              <i class="bi bi-check-all me-1"></i>${escapeHtml(m.status)}
            </span>
          </td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (_) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3 text-muted">Histórico não disponível.</td></tr>';
  }
}

// ==============================================================================
// GESTÃO DE PAGAMENTOS MÓVEIS (M-PESA / E-MOLA)
// ==============================================================================
function selecionarCarteiraGateway(metodo) {
  stateCarteiraAtiva = metodo;
  const optMpesa = document.getElementById('optCarteiraMpesa');
  const optEmola = document.getElementById('optCarteiraEmola');
  const btnDisparar = document.getElementById('btnDispararStkPush');
  const lblPrefixo = document.getElementById('lblPrefixoOperadora');
  const statusOp = document.getElementById('statusOperadoraTelefone');

  if (metodo === 'MPESA') {
    optMpesa?.classList.add('active');
    optMpesa?.style.setProperty('border-color', '#dc2626', 'important');
    optMpesa?.style.setProperty('background', 'rgba(220, 38, 38, 0.05)', 'important');

    optEmola?.classList.remove('active');
    optEmola?.style.setProperty('border-color', '#e5e7eb', 'important');
    optEmola?.style.setProperty('background', '#ffffff', 'important');

    if (btnDisparar) {
      btnDisparar.className = 'btn btn-danger fw-bold w-100 py-2 shadow-sm';
      btnDisparar.innerHTML = '<i class="bi bi-send-plus-fill me-1"></i> Disparar Cobrança M-Pesa (PIN STK Push)';
    }
    if (statusOp) statusOp.textContent = 'Introduza um número Vodacom (84 ou 85) para confirmação de PIN M-Pesa.';
  } else {
    optEmola?.classList.add('active');
    optEmola?.style.setProperty('border-color', '#d97706', 'important');
    optEmola?.style.setProperty('background', 'rgba(217, 119, 6, 0.05)', 'important');

    optMpesa?.classList.remove('active');
    optMpesa?.style.setProperty('border-color', '#e5e7eb', 'important');
    optMpesa?.style.setProperty('background', '#ffffff', 'important');

    if (btnDisparar) {
      btnDisparar.className = 'btn btn-warning text-dark fw-bold w-100 py-2 shadow-sm';
      btnDisparar.innerHTML = '<i class="bi bi-send-plus-fill me-1"></i> Disparar Cobrança e-Mola (PIN Push)';
    }
    if (statusOp) statusOp.textContent = 'Introduza um número Movitel (86 ou 87) para confirmação de PIN e-Mola.';
  }
}

function aoSelecionarAlunoParaPagamento(alunoId) {
  const sel = document.getElementById('pagamentoAlunoSelect');
  if (!sel || !alunoId) return;

  const opt = sel.options[sel.selectedIndex];
  if (opt) {
    const tel = opt.getAttribute('data-telefone') || '';
    const nome = opt.getAttribute('data-nome') || '';
    if (tel && document.getElementById('pagamentoTelefone')) {
      document.getElementById('pagamentoTelefone').value = tel;
      aoDigitarTelefonePagamento(tel);
    }
    if (nome && document.getElementById('pagamentoDescricao')) {
      document.getElementById('pagamentoDescricao').value = `Propina Escolar - ${nome}`;
    }
    if (!document.getElementById('pagamentoValor')?.value) {
      document.getElementById('pagamentoValor').value = '1500.00';
    }
  }
}

function aoDigitarTelefonePagamento(tel) {
  const limpo = (tel || '').replace(/\D/g, '');
  let ddd = '';
  if (limpo.startsWith('258') && limpo.length >= 5) {
    ddd = limpo.slice(3, 5);
  } else if (limpo.length >= 2) {
    ddd = limpo.slice(0, 2);
  }

  if (['84', '85'].includes(ddd)) {
    selecionarCarteiraGateway('MPESA');
  } else if (['86', '87'].includes(ddd)) {
    selecionarCarteiraGateway('EMOLA');
  }
}

async function executarStkPushPagamento() {
  const metodo = stateCarteiraAtiva || 'MPESA';
  const telefone = (document.getElementById('pagamentoTelefone')?.value || '').trim();
  const valor = parseFloat(document.getElementById('pagamentoValor')?.value || 0);
  const alunoId = document.getElementById('pagamentoAlunoSelect')?.value || null;
  const descricao = (document.getElementById('pagamentoDescricao')?.value || '').trim();

  if (!telefone) {
    mostrarToast('Por favor, introduza o número de telemóvel para a cobrança.', 'warning');
    document.getElementById('pagamentoTelefone')?.focus();
    return;
  }

  if (!valor || valor <= 0) {
    mostrarToast('Por favor, introduza um valor válido em Meticais (MZN).', 'warning');
    document.getElementById('pagamentoValor')?.focus();
    return;
  }

  const btn = document.getElementById('btnDispararStkPush');
  const btnOriginal = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> A aguardar PIN no telemóvel...';
  }

  try {
    const res = await apiFetch('/api/v1/ferramentas/pagamentos-moveis/iniciar', {
      method: 'POST',
      body: JSON.stringify({
        metodo,
        telefone,
        valor,
        aluno_id: alunoId,
        descricao
      })
    });

    if (res && res.success) {
      const recibo = res.transacao?.recibo || 'REC-CONFIRMADO';
      mostrarToast(`Pagamento ${metodo} concluído com sucesso! Recibo: ${recibo}`, 'success');
      alert(`✅ SUCESSO: Cobrança ${metodo} liquidada!\n\nValor: ${valor.toFixed(2)} MZN\nRecibo Oficial: ${recibo}\nSMS de quitação enviado ao encarregado.`);

      if (document.getElementById('pagamentoValor')) document.getElementById('pagamentoValor').value = '';
      if (document.getElementById('pagamentoTelefone')) document.getElementById('pagamentoTelefone').value = '';
      if (document.getElementById('pagamentoDescricao')) document.getElementById('pagamentoDescricao').value = '';

      await carregarTransacoesGateway();
      await carregarEstatisticasGateway();
      await carregarHistoricoSms();
    } else {
      mostrarToast((res && res.message) || 'Falha ao processar pagamento móvel.', 'danger');
    }
  } catch (err) {
    console.error('[PAGAMENTO MOVEL] Erro:', err);
    mostrarToast('Erro ao ligar ao Gateway móvel: ' + (err.message || ''), 'danger');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = btnOriginal;
    }
  }
}

async function carregarTransacoesGateway() {
  const tbody = document.getElementById('tabelaTransacoesGatewayCorpo');
  if (!tbody) return;

  try {
    const res = await apiFetch('/api/v1/ferramentas/pagamentos-moveis/transacoes', { ignoreAuthRedirect: true });
    const lista = (res && res.data) || [];

    if (lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Nenhuma transação móvel efetuada recentemente.</td></tr>';
      return;
    }

    let html = '';
    lista.forEach(t => {
      const badgeMetodo = t.metodo === 'MPESA'
        ? '<span class="badge bg-danger">M-Pesa</span>'
        : '<span class="badge bg-warning text-dark">e-Mola</span>';

      html += `
        <tr>
          <td class="small text-muted text-nowrap">${escapeHtml(t.data)}</td>
          <td>${badgeMetodo}</td>
          <td class="font-monospace small">${escapeHtml(t.telefone)}</td>
          <td class="small fw-semibold">${escapeHtml(t.aluno || '-')}</td>
          <td class="fw-bold text-dark">${(t.valor || 0).toLocaleString('pt-PT', { minimumFractionDigits: 2 })} MT</td>
          <td><span class="badge bg-light text-dark border font-monospace">${escapeHtml(t.recibo)}</span></td>
          <td>
            <span class="badge bg-success-subtle text-success border border-success-subtle small">
              <i class="bi bi-check-circle-fill me-1"></i>${escapeHtml(t.status)}
            </span>
          </td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (_) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-3 text-muted">Transações indisponíveis.</td></tr>';
  }
}

// ==============================================================================
// SIMULADOR USSD (*...#)
// ==============================================================================
function teclarUssd(d) {
  const inp = document.getElementById('ussdInputComando');
  if (inp) {
    inp.value += d;
    inp.focus();
  }
}

function reiniciarSessaoUssd() {
  stateUssdTextoAcumulado = '';
  stateUssdSessionId = 'USSD-SES-' + Date.now();
  const inp = document.getElementById('ussdInputComando');
  if (inp) inp.value = '';

  const statusEl = document.getElementById('ussdSessionStatus');
  if (statusEl) statusEl.textContent = 'Sessão Reiniciada';

  enviarComandoUssd(true);
}

async function enviarComandoUssd(forceRoot = false) {
  const inp = document.getElementById('ussdInputComando');
  const comandoDigitado = forceRoot ? '' : (inp ? inp.value.trim() : '');

  if (comandoDigitado) {
    if (stateUssdTextoAcumulado) {
      stateUssdTextoAcumulado += '*' + comandoDigitado;
    } else {
      stateUssdTextoAcumulado = comandoDigitado;
    }
  }

  const ecra = document.getElementById('ussdEcraTexto');
  if (ecra) ecra.textContent = 'A comunicar com a operadora GSM...';

  try {
    const res = await apiFetch('/api/v1/ferramentas/ussd/simular', {
      method: 'POST',
      body: JSON.stringify({
        phoneNumber: '+258840000000',
        text: stateUssdTextoAcumulado,
        sessionId: stateUssdSessionId
      })
    });

    if (res && res.response) {
      if (ecra) ecra.textContent = res.response;
      const statusEl = document.getElementById('ussdSessionStatus');
      if (statusEl) {
        if (res.type === 'END') {
          statusEl.textContent = 'Sessão Concluída (END)';
          stateUssdTextoAcumulado = '';
        } else {
          statusEl.textContent = 'A aguardar entrada (CON)';
        }
      }
    }
  } catch (err) {
    if (ecra) ecra.textContent = 'Erro de rede na sessão USSD. Tente novamente.';
  } finally {
    if (inp) inp.value = '';
  }
}

// ==============================================================================
// ESPECIFICAÇÃO & PROMPT TÉCNICO (ABA 4)
// ==============================================================================
async function carregarConteudoPromptTecnico() {
  const pre = document.getElementById('conteudoPrompt');
  if (!pre) return;

  try {
    const res = await apiFetch('/api/v1/ferramentas/prompt-gateway/conteudo', { ignoreAuthRedirect: true });
    if (res && res.conteudo) {
      pre.textContent = res.conteudo;
      return;
    }
  } catch (_) {}

  try {
    const r2 = await fetch('/ferramentas/prompt-gateway/descarregar');
    if (r2.ok) {
      const txt = await r2.text();
      if (txt && !txt.trim().startsWith('<!DOCTYPE')) {
        pre.textContent = txt;
      }
    }
  } catch (_) {}
}

// Tornar métodos disponíveis globalmente para os botões do DOM
window.carregarPromptGateway = carregarPromptGateway;
window.aoMudarModoSms = aoMudarModoSms;
window.aplicarModeloSms = aplicarModeloSms;
window.aoDigitarTextoSms = aoDigitarTextoSms;
window.executarEnvioSms = executarEnvioSms;
window.carregarHistoricoSms = carregarHistoricoSms;
window.selecionarCarteiraGateway = selecionarCarteiraGateway;
window.aoSelecionarAlunoParaPagamento = aoSelecionarAlunoParaPagamento;
window.aoDigitarTelefonePagamento = aoDigitarTelefonePagamento;
window.executarStkPushPagamento = executarStkPushPagamento;
window.carregarTransacoesGateway = carregarTransacoesGateway;
window.teclarUssd = teclarUssd;
window.reiniciarSessaoUssd = reiniciarSessaoUssd;
window.enviarComandoUssd = enviarComandoUssd;
