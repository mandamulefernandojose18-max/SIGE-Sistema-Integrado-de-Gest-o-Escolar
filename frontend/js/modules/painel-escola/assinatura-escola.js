// =====================================================================
// SIGE - PAINEL-ESCOLA | Módulo de Assinatura e Pagamentos SaaS
// =====================================================================

var dadosMinhaAssinaturaCache = null;

async function inicializarModuloAssinaturaEscola() {
  await carregarMinhaAssinaturaEscola();
}

async function carregarMinhaAssinaturaEscola() {
  try {
    const res = await apiFetch('/saas/minha-assinatura/');
    if (!res || !res.success || !res.data) {
      console.warn('[SAAS-ESCOLA] Não foi possível carregar os dados da assinatura.');
      return;
    }

    dadosMinhaAssinaturaCache = res.data;
    const a = res.data.assinatura;
    const faturas = res.data.faturas || [];
    const alerta = res.data.alerta;

    // Atualizar Coordenadas Oficiais de Pagamento
    atualizarCoordenadasTela(res.data.coordenadas);

    // 1. Atualizar Alerta de Topo se aplicável
    const banner = document.getElementById('bannerAlertaAssinaturaEscola');
    if (banner) {
      if (alerta) {
        banner.className = `alert alert-${alerta.tipo} d-flex align-items-center mb-4 shadow-sm`;
        banner.innerHTML = `
          <i class="bi bi-exclamation-triangle-fill fs-4 me-3"></i>
          <div>
            <h6 class="fw-bold mb-1">${alerta.titulo}</h6>
            <div class="small">${alerta.mensagem}</div>
          </div>
        `;
        banner.classList.remove('d-none');
      } else {
        banner.classList.add('d-none');
      }
    }

    // 2. Atualizar Cartões de Resumo
    if (a) {
      const elEst = document.getElementById('escolaAssinaturaEstado');
      const elBadge = document.getElementById('escolaAssinaturaBadge');
      const elDesc = document.getElementById('escolaAssinaturaDescricao');

      const estadoTexto = {
        'activa': 'Activa',
        'fatura_pendente': 'Fatura Aberta',
        'em_atraso': 'Em Atraso',
        'restrita': 'Restrita (Só Leitura)',
        'suspensa': 'Suspensa',
        'cancelada': 'Cancelada',
        'teste': 'Período de Teste'
      }[a.estado] || a.estado;

      if (elEst) elEst.innerText = estadoTexto;

      if (elBadge) {
        const bgCor = {
          'activa': 'bg-success',
          'fatura_pendente': 'bg-info text-dark',
          'em_atraso': 'bg-warning text-dark',
          'restrita': 'bg-danger bg-opacity-75',
          'suspensa': 'bg-danger',
          'cancelada': 'bg-dark',
          'teste': 'bg-primary'
        }[a.estado] || 'bg-secondary';
        elBadge.className = `badge ${bgCor} fs-6`;
        elBadge.innerText = a.estado.toUpperCase();
      }

      if (elDesc) {
        if (a.estado === 'em_atraso') {
          elDesc.innerText = 'Prazo ultrapassado. Encontra-se dentro do período de tolerância.';
        } else if (a.estado === 'restrita') {
          elDesc.innerText = 'Período de tolerância expirado. Apenas modo de leitura permitido.';
        } else if (a.estado === 'suspensa') {
          elDesc.innerText = 'Acesso normal suspenso até confirmação de pagamento.';
        } else {
          elDesc.innerText = 'A sua instituição usufrui de todas as funcionalidades contratadas.';
        }
      }

      const elPlanoNome = document.getElementById('escolaPlanoNome');
      if (elPlanoNome) {
        let nomePlano = a.plano_detalhes?.nome || 'Plano Básico';
        nomePlano = nomePlano.replace(/Moçambique/gi, '').replace(/Mocambique/gi, '').trim();
        elPlanoNome.innerText = nomePlano || 'Plano Básico';
      }

      const elPlanoPreco = document.getElementById('escolaPlanoPreco');
      if (elPlanoPreco) elPlanoPreco.innerHTML = `${formatarValorMZN(a.plano_detalhes?.preco_mensal || 0)} <span class="moeda-sufixo">MZN</span>`;

      const elPer = document.getElementById('escolaPlanoPeriodicidade');
      if (elPer) elPer.innerText = `Periodicidade ${a.periodicidade.toUpperCase()}`;

      const elVenc = document.getElementById('escolaProximoVencimento');
      if (elVenc) {
        elVenc.innerText = a.proxima_fatura_em ? formatarDataPt(a.proxima_fatura_em) : '-';
      }
    }

    // 3. Renderizar Tabela de Faturas
    renderizarFaturasEscola(faturas);

    // 4. Preencher Dropdown do Modal de Pagamentos
    const sel = document.getElementById('escolaPagFaturaId');
    if (sel) {
      sel.innerHTML = '<option value="">-- Selecione a fatura correspondente --</option>' + faturas.map(f => {
        const saldoDevido = f.total_devido - f.valor_pago;
        const textoFatura = `${f.numero_fatura} (${formatarDataPt(f.periodo_inicio)} a ${formatarDataPt(f.periodo_fim)}) - Devido: ${formatarValorMZN(saldoDevido)} MZN [${f.estado}]`;
        return `<option value="${f.id}" data-saldo="${saldoDevido}" ${f.estado !== 'paga' ? 'selected' : ''}>${textoFatura}</option>`;
      }).join('');
      aoMudarFaturaSelecionadaEscola();
    }
  } catch (err) {
    console.error('[SAAS-ESCOLA] Erro ao carregar assinatura:', err);
  }
}

function renderizarFaturasEscola(faturas) {
  const tbody = document.getElementById('tabelaMinhasFaturas');
  if (!tbody) return;

  if (faturas.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">Nenhuma fatura emitida até ao momento.</td></tr>';
    return;
  }

  tbody.innerHTML = faturas.map(f => {
    let badge = '<span class="badge bg-warning text-dark">Aberta</span>';
    if (f.estado === 'paga') badge = '<span class="badge bg-success">Liquidada</span>';
    else if (f.estado === 'paga_parcial') badge = '<span class="badge bg-info text-dark">Paga Parcial</span>';
    else if (f.estado === 'em_atraso') badge = '<span class="badge bg-danger">Em Atraso</span>';

    const saldo = Math.max(0, (f.valor + f.multa_aplicada) - f.valor_pago);

    return `
      <tr>
        <td><strong>${f.numero_fatura}</strong></td>
        <td><small>${formatarDataPt(f.periodo_inicio)} a ${formatarDataPt(f.periodo_fim)}</small></td>
        <td>${formatarValorMZN(f.valor)} <span class="moeda-sufixo">MZN</span></td>
        <td>${f.multa_aplicada > 0 ? `<span class="text-danger fw-bold">+${formatarValorMZN(f.multa_aplicada)} MZN</span>` : '-'}</td>
        <td class="text-success fw-bold">${formatarValorMZN(f.valor_pago)} <span class="moeda-sufixo">MZN</span></td>
        <td><span class="badge bg-light text-dark border">${formatarDataPt(f.data_limite_efectiva)}</span></td>
        <td>${badge}</td>
        <td class="text-end">
          ${saldo > 0 ? `
            <button class="btn btn-sm btn-warning fw-bold" onclick="abrirModalRegistarPagamentoEscola('${f.id}')">
              <i class="bi bi-upload me-1"></i> Pagar
            </button>
          ` : `<span class="text-muted small"><i class="bi bi-check-circle-fill text-success me-1"></i>Liquidada</span>`}
        </td>
      </tr>
    `;
  }).join('');
}

function abrirModalRegistarPagamentoEscola(faturaId) {
  if (faturaId) {
    const sel = document.getElementById('escolaPagFaturaId');
    if (sel) {
      sel.value = faturaId;
      aoMudarFaturaSelecionadaEscola();
    }
  }
  const modal = new bootstrap.Modal(document.getElementById('modalRegistarPagamentoEscola'));
  modal.show();
}

function aoMudarFaturaSelecionadaEscola() {
  const sel = document.getElementById('escolaPagFaturaId');
  const opt = sel.options[sel.selectedIndex];
  if (opt && opt.dataset.saldo) {
    const saldo = parseFloat(opt.dataset.saldo);
    const inpValor = document.getElementById('escolaPagValor');
    if (inpValor && saldo > 0) {
      inpValor.value = saldo.toFixed(2);
    }
  }
}

async function salvarPagamentoEscola(event) {
  event.preventDefault();
  const btn = document.getElementById('btnSubmeterPagamentoEscola');
  if (btn) btn.disabled = true;

  const faturaId = document.getElementById('escolaPagFaturaId').value;
  const metodo = document.getElementById('escolaPagMetodo').value;
  const referencia = document.getElementById('escolaPagReferencia').value.trim();
  const valor = document.getElementById('escolaPagValor').value;
  const fileInput = document.getElementById('escolaPagComprovativo');

  if (!faturaId || !metodo || !referencia || !valor) {
    mostrarToast('Preencha todos os campos obrigatórios.', 'warning');
    if (btn) btn.disabled = false;
    return;
  }

  const formData = new FormData();
  formData.append('fatura_id', faturaId);
  formData.append('metodo', metodo);
  formData.append('referencia', referencia);
  formData.append('valor', valor);

  if (fileInput && fileInput.files && fileInput.files[0]) {
    formData.append('comprovativo', fileInput.files[0]);
  }

  try {
    const token = localStorage.getItem('sige_access_token');
    const apiBase = window.SIGE_CONFIG?.API_BASE_URL || '/api/v1';
    const res = await fetch(`${apiBase}/saas/registar-pagamento/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });

    const data = await res.json();

    if (data && data.success) {
      mostrarToast('Comprovativo submetido com sucesso! O pagamento será verificado pelo Administrador do Sistema.', 'success');
      bootstrap.Modal.getInstance(document.getElementById('modalRegistarPagamentoEscola'))?.hide();
      document.getElementById('formRegistarPagamentoEscola').reset();
      await carregarMinhaAssinaturaEscola();
    } else {
      mostrarToast(data?.message || 'Falha ao submeter comprovativo.', 'danger');
    }
  } catch (err) {
    console.error('[SAAS-ESCOLA] Erro ao submeter pagamento:', err);
    mostrarToast('Erro de ligação ao servidor.', 'danger');
  } finally {
    if (btn) btn.disabled = false;
  }
}

function atualizarCoordenadasTela(coord) {
  const elMpesaNum = document.getElementById('coordMpesaNumero');
  const elMpesaTit = document.getElementById('coordMpesaTitular');
  const elEmolaNum = document.getElementById('coordEmolaNumero');
  const elEmolaTit = document.getElementById('coordEmolaTitular');
  const elBimConta = document.getElementById('coordBimConta');
  const elBimNib = document.getElementById('coordBimNib');
  const elBimTit = document.getElementById('coordBimTitular');
  const elBciConta = document.getElementById('coordBciConta');
  const elBciNib = document.getElementById('coordBciNib');
  const elBciTit = document.getElementById('coordBciTitular');
  const boxExtra = document.getElementById('boxCoordNuitInstrucoes');
  const elNuit = document.getElementById('coordNuitInfo');
  const elInst = document.getElementById('coordInstrucoesInfo');

  if (coord) {
    if (elMpesaNum) elMpesaNum.innerText = coord.mpesa_numero || '';
    if (elMpesaTit) elMpesaTit.innerText = coord.mpesa_titular || '';
    if (elEmolaNum) elEmolaNum.innerText = coord.emola_numero || '';
    if (elEmolaTit) elEmolaTit.innerText = coord.emola_titular || '';
    if (elBimConta) elBimConta.innerText = coord.bim_conta || '';
    if (elBimNib) elBimNib.innerText = coord.bim_nib || '';
    if (elBimTit) elBimTit.innerText = coord.bim_titular || '';
    if (elBciConta) elBciConta.innerText = coord.bci_conta || '';
    if (elBciNib) elBciNib.innerText = coord.bci_nib || '';
    if (elBciTit) elBciTit.innerText = coord.bci_titular || '';

    if (boxExtra) {
      let temExtra = false;
      if (coord.nuit_entidade && elNuit) {
        elNuit.innerHTML = `<strong>NUIT:</strong> ${coord.nuit_entidade}`;
        temExtra = true;
      } else if (elNuit) {
        elNuit.innerHTML = '';
      }
      if (coord.instrucoes_adicionais && elInst) {
        elInst.innerHTML = `<i class="bi bi-info-circle me-1"></i>${coord.instrucoes_adicionais}`;
        temExtra = true;
      } else if (elInst) {
        elInst.innerHTML = '';
      }
      boxExtra.style.display = temExtra ? 'block' : 'none';
    }
  }
}

// Invocação ao abrir módulo
if (document.getElementById('view-assinatura-escola')) {
  inicializarModuloAssinaturaEscola();
}
