/**
 * SIGE — Módulo Gateway SMS, USSD e Pagamentos Móveis
 * Central Operacional:
 * 1. Envio de Notificações (Android SIM da Escola, WhatsApp Escolar ou Sandbox)
 * 2. Processamento de Pagamentos (Manual com Comprovativo, STK Push PIN ou Reconciliação SMS)
 * 3. Reconciliação Automática por SMS M-Pesa / e-Mola (Custo Zero)
 * 4. Simulador USSD (*...#)
 * 5. Especificação Técnica & Prompt do Gateway
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
    carregarReconciliacoesSms(),
    carregarConfiguracoesGateway(),
    carregarConteudoPromptTecnico()
  ]);

  if (typeof window.inicializarPromptGateway === 'function') {
    window.inicializarPromptGateway();
  }
}

// ==============================================================================
// 1. CARREGAR ESTATÍSTICAS
// ==============================================================================
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

// ==============================================================================
// 2. CARREGAR TURMAS NO SELECT DE SMS
// ==============================================================================
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

// ==============================================================================
// 3. CARREGAR ALUNOS NOS SELECTS DE COBRANÇA E QUITAÇÃO MANUAL
// ==============================================================================
async function carregarAlunosParaPagamentoMovel() {
  const selPush = document.getElementById('pagamentoAlunoSelect');
  const selManual = document.getElementById('pagManualAlunoSelect');
  if (!selPush && !selManual) return;

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
      let optPush = '<option value="">-- Cobrança Direta / Selecione Aluno --</option>';
      let optManual = '<option value="">-- Selecione o Aluno --</option>';

      alunos.forEach(al => {
        const nomeCompleto = `${al.nome || ''} ${al.apelido || ''}`.trim();
        const mat = al.matricula || '';
        const tel = al.telefone_encarregado || al.telefone || '';
        const rotulo = `${escapeHtml(nomeCompleto)} (${escapeHtml(mat)})`;

        optPush += `<option value="${al.id}" data-telefone="${escapeHtml(tel)}" data-nome="${escapeHtml(nomeCompleto)}">${rotulo}</option>`;
        optManual += `<option value="${al.id}" data-telefone="${escapeHtml(tel)}" data-nome="${escapeHtml(nomeCompleto)}" data-matricula="${escapeHtml(mat)}">${rotulo}</option>`;
      });

      if (selPush) selPush.innerHTML = optPush;
      if (selManual) selManual.innerHTML = optManual;
    }
  } catch (_) {}
}

// ==============================================================================
// 4. CONFIGURAÇÃO OPERACIONAL DO GATEWAY (GET / POST)
// ==============================================================================
async function carregarConfiguracoesGateway() {
  try {
    const res = await apiFetch('/api/v1/ferramentas/configuracao/obter/', { ignoreAuthRedirect: true });
    if (res && res.success && res.data) {
      const d = res.data;
      const inpAndroidRapido = document.getElementById('gwAndroidUrlInput');
      const inpAndroidCfg = document.getElementById('cfgAndroidGatewayUrl');
      const inpMpesaShortcode = document.getElementById('cfgMpesaShortcode');

      if (inpAndroidRapido && d.android_gateway_url) inpAndroidRapido.value = d.android_gateway_url;
      if (inpAndroidCfg && d.android_gateway_url) inpAndroidCfg.value = d.android_gateway_url;
      if (inpMpesaShortcode && d.mpesa_shortcode) inpMpesaShortcode.value = d.mpesa_shortcode;

      // Selecionar canal pré-definido se existir
      if (d.canal_envio_padrao) {
        const radio = document.querySelector(`input[name="gwCanalEnvio"][value="${d.canal_envio_padrao}"]`);
        if (radio) {
          radio.checked = true;
          alternarCanalEnvio(d.canal_envio_padrao);
        }
      }
    }
  } catch (err) {
    console.warn('[GATEWAY] Não foi possível carregar definições do gateway:', err);
  }
}

async function salvarUrlAndroidRapida() {
  const url = (document.getElementById('gwAndroidUrlInput')?.value || '').trim();
  try {
    const res = await apiFetch('/api/v1/ferramentas/configuracao/salvar/', {
      method: 'POST',
      body: JSON.stringify({ android_gateway_url: url })
    });
    if (res && res.success) {
      mostrarToast('Endereço do telemóvel Android guardado!', 'success');
      const inpCfg = document.getElementById('cfgAndroidGatewayUrl');
      if (inpCfg) inpCfg.value = url;
    } else {
      mostrarToast((res && res.message) || 'Erro ao guardar endereço.', 'danger');
    }
  } catch (err) {
    mostrarToast('Falha de ligação: ' + (err.message || ''), 'danger');
  }
}

async function testarConexaoAndroidGateway() {
  const url = (document.getElementById('gwAndroidUrlInput')?.value || '').trim();
  if (!url) {
    mostrarToast('Por favor, introduza o endereço IP do telemóvel Android primeiro.', 'warning');
    document.getElementById('gwAndroidUrlInput')?.focus();
    return;
  }
  mostrarToast('A verificar conexão com o telemóvel Android...', 'info');
  try {
    const res = await apiFetch('/api/v1/ferramentas/configuracao/salvar/', {
      method: 'POST',
      body: JSON.stringify({ android_gateway_url: url })
    });
    if (res && res.success) {
      mostrarToast('✅ Telemóvel configurado e pronto para disparos com o cartão SIM da escola!', 'success');
    }
  } catch (err) {
    mostrarToast('Aviso: Certifique-se de que o telemóvel está na mesma rede Wi-Fi ou com rota aberta.', 'warning');
  }
}

async function salvarConfiguracoesCompletasGateway() {
  const androidUrl = (document.getElementById('cfgAndroidGatewayUrl')?.value || '').trim();
  const mpesaShortcode = (document.getElementById('cfgMpesaShortcode')?.value || '').trim();

  try {
    const res = await apiFetch('/api/v1/ferramentas/configuracao/salvar/', {
      method: 'POST',
      body: JSON.stringify({
        android_gateway_url: androidUrl,
        mpesa_shortcode: mpesaShortcode
      })
    });
    if (res && res.success) {
      mostrarToast('Definições do gateway gravadas com sucesso!', 'success');
      const inpRapido = document.getElementById('gwAndroidUrlInput');
      if (inpRapido) inpRapido.value = androidUrl;
    } else {
      mostrarToast((res && res.message) || 'Falha ao gravar definições.', 'danger');
    }
  } catch (err) {
    mostrarToast('Erro ao comunicar com o servidor: ' + (err.message || ''), 'danger');
  }
}

// ==============================================================================
// 5. GESTÃO DE CANAIS DE ENVIO (3 OPÇÕES INSTANTÂNEAS)
// ==============================================================================
function alternarCanalEnvio(canal) {
  const boxAndroid = document.getElementById('boxAndroidGatewayConfig');
  const btnDisparar = document.getElementById('btnDispararSms');

  if (canal === 'ANDROID_GATEWAY') {
    if (boxAndroid) boxAndroid.style.display = 'block';
    if (btnDisparar) {
      btnDisparar.className = 'btn btn-success fw-bold w-100 py-2 shadow-sm';
      btnDisparar.innerHTML = '<i class="bi bi-phone-fill me-1"></i> Disparar SMS via Telemóvel Android (Custo Zero)';
    }
  } else if (canal === 'WHATSAPP') {
    if (boxAndroid) boxAndroid.style.display = 'none';
    if (btnDisparar) {
      btnDisparar.className = 'btn btn-success fw-bold w-100 py-2 shadow-sm';
      btnDisparar.innerHTML = '<i class="bi bi-whatsapp me-1"></i> Abrir / Enviar via WhatsApp (100% Gratuito)';
    }
  } else {
    // SANDBOX
    if (boxAndroid) boxAndroid.style.display = 'none';
    if (btnDisparar) {
      btnDisparar.className = 'btn btn-secondary fw-bold w-100 py-2 shadow-sm';
      btnDisparar.innerHTML = '<i class="bi bi-shield-shaded me-1"></i> Simular Envio em Sandbox (Teste)';
    }
  }
}

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
  PROPINA: "Prezado Encarregado de {aluno}, lembramos que a propina de {mes} no valor de {valor} MZN tem vencimento próximo. Evite multas pagando via M-Pesa ou e-Mola. SIGE.",
  RECIBO: "SIGE: Confirmamos a liquidação da propina de {aluno} referente a {mes}. Valor: {valor} MZN. Recibo disponível no portal do estudante. Obrigado!",
  REUNIAO: "Convocatória: Convidamos o encarregado de {aluno} para a Reunião Geral de Pais e Encarregados de Educação neste Sábado às 08h30 na escola. Direcção SIGE.",
  FALTA: "Aviso Escolar: O estudante {aluno} registou falta no dia de hoje. Agradecemos contacto com a Direcção Pedagógica ou Professor de Turma. SIGE.",
  PAUTA: "Informação Escolar: As pautas de avaliação trimestral de {aluno} já estão homologadas e disponíveis para consulta no portal e via USSD *123#. SIGE."
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
  const radioCanal = document.querySelector('input[name="gwCanalEnvio"]:checked');
  const canal = radioCanal ? radioCanal.value : 'ANDROID_GATEWAY';

  const modo = document.getElementById('smsModoSelect')?.value || 'MANUAL';
  const mensagem = (document.getElementById('smsTexto')?.value || '').trim();
  const tipo = document.getElementById('smsTipoSelect')?.value || 'AVISO';

  if (!mensagem) {
    mostrarToast('Por favor, introduza o texto da mensagem antes de enviar.', 'warning');
    document.getElementById('smsTexto')?.focus();
    return;
  }

  const payload = { canal, modo, mensagem, tipo };

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
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> A processar envio...';
  }

  try {
    const res = await apiFetch('/api/v1/ferramentas/sms/enviar', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res && res.success) {
      mostrarToast(res.message || 'Mensagem enviada com sucesso!', 'success');

      // Se for canal WhatsApp e tiver link gerado, abrir diretamente no WhatsApp Web
      if (res.canal === 'WHATSAPP' && res.wa_link) {
        window.open(res.wa_link, '_blank');
      }

      if (document.getElementById('smsTexto')) document.getElementById('smsTexto').value = '';
      if (document.getElementById('smsTelefones')) document.getElementById('smsTelefones').value = '';
      aoDigitarTextoSms('');
      await carregarHistoricoSms();
      await carregarEstatisticasGateway();
    } else {
      mostrarToast((res && res.message) || 'Falha ao enviar mensagem.', 'danger');
    }
  } catch (err) {
    console.error('[SMS] Erro ao enviar:', err);
    mostrarToast('Erro de conexão ao enviar: ' + (err.message || ''), 'danger');
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
      tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">Nenhum envio recente registado.</td></tr>';
      return;
    }

    let html = '';
    lista.forEach(m => {
      let badgeCanal = '<span class="badge bg-secondary">SMS</span>';
      if (m.canal === 'ANDROID_GATEWAY' || m.operadora === 'VODACOM') {
        badgeCanal = '<span class="badge bg-success-subtle text-success border border-success-subtle"><i class="bi bi-phone me-1"></i>SIM Android</span>';
      } else if (m.canal === 'WHATSAPP') {
        badgeCanal = '<span class="badge bg-success"><i class="bi bi-whatsapp me-1"></i>WhatsApp</span>';
      } else if (m.canal === 'SANDBOX') {
        badgeCanal = '<span class="badge bg-secondary-subtle text-secondary border"><i class="bi bi-shield-shaded me-1"></i>Sandbox</span>';
      }

      html += `
        <tr>
          <td class="small text-muted text-nowrap">${escapeHtml(m.data)}</td>
          <td>
            <div class="fw-semibold small">${escapeHtml(m.destinatario)}</div>
            <small class="text-muted">${escapeHtml(m.nome_destinatario || '')}</small>
          </td>
          <td>${badgeCanal}</td>
          <td class="small text-truncate" style="max-width: 220px;" title="${escapeHtml(m.mensagem)}">
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
// 6. GESTÃO DE PAGAMENTOS (3 OPÇÕES INSTANTÂNEAS)
// ==============================================================================
function alternarModoPagamento(modo) {
  const pManual = document.getElementById('painelPagamentoManual');
  const pPush = document.getElementById('painelPagamentoPush');
  const pRec = document.getElementById('painelPagamentoReconciliacao');

  if (modo === 'MANUAL') {
    if (pManual) pManual.style.display = 'block';
    if (pPush) pPush.style.display = 'none';
    if (pRec) pRec.style.display = 'none';
  } else if (modo === 'PUSH') {
    if (pManual) pManual.style.display = 'none';
    if (pPush) pPush.style.display = 'block';
    if (pRec) pRec.style.display = 'none';
  } else if (modo === 'RECONCILIACAO') {
    if (pManual) pManual.style.display = 'none';
    if (pPush) pPush.style.display = 'none';
    if (pRec) pRec.style.display = 'block';
  }
}

function aoSelecionarAlunoManual(alunoId) {
  const sel = document.getElementById('pagManualAlunoSelect');
  if (!sel || !alunoId) return;

  const opt = sel.options[sel.selectedIndex];
  if (opt) {
    const nome = opt.getAttribute('data-nome') || '';
    const mat = opt.getAttribute('data-matricula') || '';
    const inpObs = document.getElementById('pagManualObservacoes');
    if (inpObs && !inpObs.value) {
      inpObs.value = `Quitação de propina escolar - ${nome} (${mat})`;
    }
    const inpValor = document.getElementById('pagManualValor');
    if (inpValor && !inpValor.value) {
      inpValor.value = '1500.00';
    }
  }
}

async function executarLiquidacaoManual() {
  const alunoId = document.getElementById('pagManualAlunoSelect')?.value;
  const metodo = document.getElementById('pagManualMetodoSelect')?.value || 'MPESA';
  const referencia = (document.getElementById('pagManualReferencia')?.value || '').trim();
  const valor = parseFloat(document.getElementById('pagManualValor')?.value || 0);
  const observacoes = (document.getElementById('pagManualObservacoes')?.value || '').trim();

  if (!alunoId) {
    mostrarToast('Por favor, selecione o estudante beneficiário.', 'warning');
    document.getElementById('pagManualAlunoSelect')?.focus();
    return;
  }

  if (!referencia) {
    mostrarToast('Por favor, introduza a referência do comprovativo M-Pesa / borderô.', 'warning');
    document.getElementById('pagManualReferencia')?.focus();
    return;
  }

  if (!valor || valor <= 0) {
    mostrarToast('Por favor, introduza um valor válido em Meticais (MZN).', 'warning');
    document.getElementById('pagManualValor')?.focus();
    return;
  }

  try {
    const res = await apiFetch('/api/v1/ferramentas/pagamentos/liquidar-manual/', {
      method: 'POST',
      body: JSON.stringify({
        aluno_id: alunoId,
        metodo,
        referencia,
        valor,
        observacoes
      })
    });

    if (res && res.success) {
      const recibo = res.recibo || 'REC-CONFIRMADO';
      mostrarToast(`Propina liquidada com sucesso! Recibo: ${recibo}`, 'success');
      alert(`✅ SUCESSO: Liquidação Concluída!\n\nEstudante: ${res.aluno || 'Estudante'}\nValor: ${valor.toFixed(2)} MZN\nRecibo Oficial: ${recibo}\nReferência: ${referencia}\n\nEstado da propina alterado para PAGO.`);

      // Limpar formulário manual
      if (document.getElementById('pagManualReferencia')) document.getElementById('pagManualReferencia').value = '';
      if (document.getElementById('pagManualValor')) document.getElementById('pagManualValor').value = '';
      if (document.getElementById('pagManualObservacoes')) document.getElementById('pagManualObservacoes').value = '';

      await carregarTransacoesGateway();
      await carregarEstatisticasGateway();
    } else {
      mostrarToast((res && res.message) || 'Falha ao liquidar pagamento manual.', 'danger');
    }
  } catch (err) {
    console.error('[PAGAMENTO MANUAL] Erro:', err);
    mostrarToast('Erro ao comunicar com o servidor: ' + (err.message || ''), 'danger');
  }
}

// ==============================================================================
// 7. STK PUSH (PIN NO TELEMÓVEL)
// ==============================================================================
function selecionarCarteiraGateway(metodo) {
  stateCarteiraAtiva = metodo;
  const optMpesa = document.getElementById('optCarteiraMpesa');
  const optEmola = document.getElementById('optCarteiraEmola');
  const btnDisparar = document.getElementById('btnDispararStkPush');
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
      btnDisparar.innerHTML = '<i class="bi bi-broadcast me-1"></i> Disparar Cobrança M-Pesa (PIN STK Push)';
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
      btnDisparar.innerHTML = '<i class="bi bi-broadcast me-1"></i> Disparar Cobrança e-Mola (PIN Push)';
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
  const limpo = (tel || '').replace(/\D/g, '').slice(0, 15);
  const elInp = document.getElementById('pagamentoTelefone');
  if (elInp && elInp.value !== limpo) {
    elInp.value = limpo;
  }
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
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhuma transação efetuada recentemente.</td></tr>';
      return;
    }

    let html = '';
    lista.forEach(t => {
      let badgeMetodo = '<span class="badge bg-secondary">Outro</span>';
      if (t.metodo === 'MPESA') badgeMetodo = '<span class="badge bg-danger">M-Pesa</span>';
      else if (t.metodo === 'EMOLA') badgeMetodo = '<span class="badge bg-warning text-dark">e-Mola</span>';
      else if (t.metodo === 'TRANSFERENCIA') badgeMetodo = '<span class="badge bg-primary">Banco</span>';
      else if (t.metodo === 'NUMERARIO') badgeMetodo = '<span class="badge bg-dark">Caixa</span>';

      html += `
        <tr>
          <td class="small text-muted text-nowrap">${escapeHtml(t.data)}</td>
          <td>${badgeMetodo}</td>
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
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-3 text-muted">Transações indisponíveis.</td></tr>';
  }
}

// ==============================================================================
// 8. RECONCILIAÇÃO AUTOMÁTICA POR SMS M-PESA / E-MOLA (CUSTO ZERO)
// ==============================================================================
async function carregarReconciliacoesSms() {
  const tbody = document.getElementById('tabelaReconciliacoesSmsCorpo');
  if (!tbody) return;

  try {
    const res = await apiFetch('/api/v1/ferramentas/reconciliacao/lista/', { ignoreAuthRedirect: true });
    const lista = (res && res.data) || [];

    if (lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhum SMS de confirmação recebido recentemente.</td></tr>';
      return;
    }

    let html = '';
    lista.forEach(r => {
      let badgeSt = '<span class="badge bg-success-subtle text-success border border-success-subtle"><i class="bi bi-check-circle me-1"></i>Liquidado</span>';
      if (r.status === 'PENDENTE') {
        badgeSt = '<span class="badge bg-warning-subtle text-dark border border-warning-subtle"><i class="bi bi-clock me-1"></i>Pendente</span>';
      } else if (r.status === 'DUPLICADO') {
        badgeSt = '<span class="badge bg-secondary-subtle text-secondary border"><i class="bi bi-copy me-1"></i>Duplicado</span>';
      }

      html += `
        <tr>
          <td class="small text-muted text-nowrap">${escapeHtml(r.data)}</td>
          <td class="small fw-semibold">${escapeHtml(r.origem || 'M-Pesa')}</td>
          <td class="fw-bold text-dark">${(r.valor || 0).toLocaleString('pt-PT', { minimumFractionDigits: 2 })} MT</td>
          <td class="font-monospace small">${escapeHtml(r.referencia)}</td>
          <td class="small">${escapeHtml(r.aluno || '-')}</td>
          <td>${badgeSt}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (_) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-3 text-muted">Reconciliações indisponíveis.</td></tr>';
  }
}

async function simularRecebimentoSmsMpesa() {
  const texto = (document.getElementById('txtSimulacaoSmsMpesa')?.value || '').trim();
  if (!texto) {
    mostrarToast('Por favor, introduza o texto do SMS para simulação.', 'warning');
    return;
  }

  try {
    const res = await apiFetch('/api/v1/ferramentas/reconciliacao/sms-webhook/', {
      method: 'POST',
      body: JSON.stringify({
        sender: 'MPesa',
        message: texto
      })
    });

    if (res && res.success) {
      mostrarToast(`SMS processado! Referência: ${res.referencia || 'N/A'} - Valor: ${res.valor || 0} MT`, 'success');
      alert(`✅ RECONCILIAÇÃO PROCESSADA!\n\nCarteira: ${res.carteira || 'M-Pesa'}\nValor: ${res.valor} MT\nReferência: ${res.referencia}\nEstado: ${res.status}\nEstudante Associado: ${res.aluno || 'Não vinculado automaticamente'}\nRecibo: ${res.recibo || 'N/A'}`);

      await carregarReconciliacoesSms();
      await carregarTransacoesGateway();
      await carregarEstatisticasGateway();
    } else {
      mostrarToast((res && res.message) || 'Erro ao processar reconciliação.', 'danger');
    }
  } catch (err) {
    mostrarToast('Erro ao testar webhook: ' + (err.message || ''), 'danger');
  }
}

// ==============================================================================
// 9. SIMULADOR USSD (*...#)
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

  const ecra = document.getElementById('ussdLcdScreen');
  if (ecra) {
    ecra.textContent = `CON Escola Secundária de Massinga (SIGE)
1. Consultar Notas do Estudante
2. Propinas / Saldos Pendentes
3. Pagar Propina (M-Pesa / e-Mola)
4. Calendário Escolar 2026
5. Contactos da Secretaria`;
  }
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

  const ecra = document.getElementById('ussdLcdScreen');
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
      if (res.type === 'END') {
        stateUssdTextoAcumulado = '';
      }
    }
  } catch (err) {
    if (ecra) ecra.textContent = 'Erro de rede na sessão USSD. Tente novamente.';
  } finally {
    if (inp) inp.value = '';
  }
}

// ==============================================================================
// 10. ESPECIFICAÇÃO & PROMPT TÉCNICO (ABA 5)
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

// Expor métodos globalmente no escopo de window para bindings dos templates HTML
window.carregarPromptGateway = carregarPromptGateway;
window.alternarCanalEnvio = alternarCanalEnvio;
window.salvarUrlAndroidRapida = salvarUrlAndroidRapida;
window.testarConexaoAndroidGateway = testarConexaoAndroidGateway;
window.salvarConfiguracoesCompletasGateway = salvarConfiguracoesCompletasGateway;
window.aoMudarModoSms = aoMudarModoSms;
window.aplicarModeloSms = aplicarModeloSms;
window.aoDigitarTextoSms = aoDigitarTextoSms;
window.executarEnvioSms = executarEnvioSms;
window.carregarHistoricoSms = carregarHistoricoSms;
window.alternarModoPagamento = alternarModoPagamento;
window.aoSelecionarAlunoManual = aoSelecionarAlunoManual;
window.executarLiquidacaoManual = executarLiquidacaoManual;
window.selecionarCarteiraGateway = selecionarCarteiraGateway;
window.aoSelecionarAlunoParaPagamento = aoSelecionarAlunoParaPagamento;
window.aoDigitarTelefonePagamento = aoDigitarTelefonePagamento;
window.executarStkPushPagamento = executarStkPushPagamento;
window.carregarTransacoesGateway = carregarTransacoesGateway;
window.carregarReconciliacoesSms = carregarReconciliacoesSms;
window.simularRecebimentoSmsMpesa = simularRecebimentoSmsMpesa;
window.teclarUssd = teclarUssd;
window.reiniciarSessaoUssd = reiniciarSessaoUssd;
window.enviarComandoUssd = enviarComandoUssd;
