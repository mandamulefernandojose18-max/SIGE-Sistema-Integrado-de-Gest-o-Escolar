/**
 * SIGE - PAINEL-ALUNO | As Minhas Propinas & Mensalidades
 * Ficheiro de código independente do menu: aluno-pagamentos.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
async function carregarAlunoPagamentos() {
  try {
    const res = await apiFetch('/api/v1/alunos/me/pagamentos');
    if (res.success && Array.isArray(res.data)) {
      const pagamentos = res.data;
      
      let totalPago = 0;
      let totalPendente = 0;
      let temAtrasado = false;
      const hoje = new Date();

      pagamentos.forEach(p => {
        const val = Number(p.valor || 0);
        if (p.status === 'PAGO') {
          totalPago += Number(p.valor_pago || val);
        } else {
          totalPendente += val;
          if (p.data_vencimento && new Date(p.data_vencimento) < hoje) {
            temAtrasado = true;
          }
        }
      });

      const elPago = document.getElementById('alunoTotalPagoCard');
      if (elPago) elPago.innerHTML = formatarMoeda(totalPago);

      const elPendente = document.getElementById('alunoTotalPendenteCard');
      if (elPendente) elPendente.innerHTML = formatarMoeda(totalPendente);

      const elSituacao = document.getElementById('alunoSituacaoPropinaCard');
      if (elSituacao) {
        if (totalPendente === 0) {
          elSituacao.textContent = 'Regularizado';
          elSituacao.className = 'fw-bold mb-0 text-success';
        } else if (temAtrasado) {
          elSituacao.textContent = 'Em Atraso';
          elSituacao.className = 'fw-bold mb-0 text-danger';
        } else {
          elSituacao.textContent = 'Pendente';
          elSituacao.className = 'fw-bold mb-0 text-warning';
        }
      }

      const tbody = document.getElementById('tabelaAlunoPagamentosCorpo');
      if (tbody) {
        if (pagamentos.length === 0) {
          tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4"><i class="bi bi-info-circle me-1"></i>Nenhuma mensalidade lançada até ao momento.</td></tr>`;
        } else {
          tbody.innerHTML = pagamentos.map(p => `
            <tr>
              <td><strong>${p.descricao || 'Mensalidade Escolar'}</strong></td>
              <td><code>${p.mes_referencia || '-'}</code></td>
              <td><strong class="text-success">${formatarMoeda(p.valor || 0)}</strong></td>
              <td>${p.data_vencimento ? new Date(p.data_vencimento).toLocaleDateString('pt-PT') : '-'}</td>
              <td>
                <span class="badge ${p.status === 'PAGO' ? 'bg-success' : 'bg-warning text-dark'}">
                  ${p.status}
                </span>
              </td>
              <td class="text-end">
                <div class="d-inline-flex gap-1 align-items-center justify-content-end">
                  ${p.status !== 'PAGO' ? `
                    <button class="btn btn-sm btn-success fw-bold shadow-sm d-inline-flex align-items-center gap-1" onclick="modalPagarSaldoCarteiraAluno('${p.id}', ${p.valor || 0}, '${(p.descricao || 'Mensalidade Escolar').replace(/'/g, "\\'")}', '${p.mes_referencia || ''}')" title="Efectuar pagamento do saldo com M-Pesa ou e-Mola">
                      <i class="bi bi-phone-fill"></i> <span>Pagar</span>
                    </button>
                  ` : ''}
                  <div class="btn-group btn-group-sm">
                    <button class="btn ${p.status === 'PAGO' ? 'btn-outline-primary' : 'btn-outline-secondary'}" onclick="imprimirReciboPagamento('${p.id}')" title="Visualizar e Imprimir Recibo ${p.status === 'PAGO' ? '(Pago)' : '(Não Pago)'}">
                      <i class="bi bi-printer me-1"></i> Imprimir
                    </button>
                    <button class="btn ${p.status === 'PAGO' ? 'btn-primary' : 'btn-outline-danger'}" onclick="descarregarReciboPdf('${p.id}')" title="Descarregar Recibo Oficial em PDF ${p.status === 'PAGO' ? '(Pago)' : '(Não Pago)'}">
                      <i class="bi bi-file-earmark-pdf me-1"></i> PDF
                    </button>
                  </div>
                </div>
              </td>
            </tr>
          `).join('');
        }
      }
    }
  } catch (err) {
    console.warn('Erro ao carregar pagamentos do aluno:', err);
  }
}

function modalPagarSaldoCarteiraAluno(id, valor, descricao, mesRef) {
  const descSegura = escapeHtml(descricao || 'Mensalidade Escolar');
  const valorFormatado = formatarMoeda(valor);

  abrirModal('Pagar Saldo com Carteira Móvel', `
    <form id="formPagarSaldoAluno" onsubmit="confirmarPagamentoSaldoAluno(event, '${id}')">
      <div class="p-3 mb-3 bg-light rounded border">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="text-muted small text-uppercase fw-semibold">Cobrança</span>
          <strong class="text-dark">${descSegura} ${mesRef ? `(${mesRef})` : ''}</strong>
        </div>
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-muted small text-uppercase fw-semibold">Saldo a Pagar</span>
          <strong class="text-success fs-5">${valorFormatado}</strong>
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label small fw-semibold">Seleccione a Carteira Móvel *</label>
        <select id="alunoLiqMetodo" class="form-select" required onchange="aoMudarCarteiraAluno()">
          <option value="MPESA">🔴 M-Pesa (Vodacom - 84 / 85)</option>
          <option value="EMOLA">🟡 e-Mola (Movitel - 86 / 87)</option>
        </select>
      </div>

      <div class="p-3 mb-3 rounded border border-success bg-success bg-opacity-10">
        <div class="d-flex align-items-center gap-2 mb-2">
          <i class="bi bi-phone-fill text-success fs-5"></i>
          <strong class="small text-dark" id="alunoCarteiraTitulo">Pagamento M-Pesa (Vodacom)</strong>
        </div>
        <div class="row g-2">
          <div class="col-sm-6">
            <label class="form-label small fw-semibold">Número do Telemóvel (+258) *</label>
            <input type="tel" id="alunoLiqTelefone" class="form-control" placeholder="Ex: 84XXXXXXX ou 85XXXXXXX" maxlength="15" required>
          </div>
          <div class="col-sm-6">
            <label class="form-label small fw-semibold">Código / Referência da Transacção</label>
            <input type="text" id="alunoLiqReferencia" class="form-control" placeholder="Ex: MP261017.0001 (ou deixe em branco)">
          </div>
        </div>
        <small class="text-muted d-block mt-2">
          <i class="bi bi-shield-check me-1"></i>O saldo será debitado e liquidado no sistema, emitindo imediatamente o recibo oficial autenticado.
        </small>
      </div>

      <div class="d-flex justify-content-end gap-2 pt-2 border-top">
        <button type="button" class="btn btn-secondary" onclick="fecharModal()">Cancelar</button>
        <button type="submit" id="btnAlunoPagar" class="btn btn-success fw-bold">
          <i class="bi bi-check-circle me-1"></i> Confirmar Pagamento do Saldo
        </button>
      </div>
    </form>
  `);
}

function aoMudarCarteiraAluno() {
  const met = document.getElementById('alunoLiqMetodo')?.value;
  const tit = document.getElementById('alunoCarteiraTitulo');
  const tel = document.getElementById('alunoLiqTelefone');
  if (met === 'EMOLA') {
    if (tit) tit.textContent = 'Pagamento e-Mola (Movitel)';
    if (tel) tel.placeholder = 'Ex: 86XXXXXXX ou 87XXXXXXX';
  } else {
    if (tit) tit.textContent = 'Pagamento M-Pesa (Vodacom)';
    if (tel) tel.placeholder = 'Ex: 84XXXXXXX ou 85XXXXXXX';
  }
}

async function confirmarPagamentoSaldoAluno(event, id) {
  event.preventDefault();
  const btn = document.getElementById('btnAlunoPagar');
  if (btn) btn.disabled = true;

  try {
    const metodo = document.getElementById('alunoLiqMetodo')?.value || 'MPESA';
    const telefone = document.getElementById('alunoLiqTelefone')?.value?.trim() || '';
    const referencia = document.getElementById('alunoLiqReferencia')?.value?.trim() || '';

    const res = await apiFetch(`/api/v1/alunos/me/pagamentos/`, {
      method: 'POST',
      body: JSON.stringify({
        pagamento_id: id,
        metodo_pagamento: metodo,
        telefone: telefone,
        referencia: referencia
      })
    });

    if (res && res.success) {
      fecharModal();
      mostrarNotificacao(res.message || 'Pagamento com carteira móvel concluído com sucesso!', 'success');
      await carregarAlunoPagamentos();
    } else {
      mostrarNotificacao(res?.message || 'Falha ao processar pagamento com carteira móvel.', 'danger');
    }
  } catch (err) {
    mostrarNotificacao('Erro ao pagar saldo com carteira móvel: ' + (err.message || ''), 'danger');
  } finally {
    if (btn) btn.disabled = false;
  }
}

if (typeof window.imprimirReciboPagamento !== 'function') {
  window.imprimirReciboPagamento = function(pagamentoId) {
    if (typeof abrirModalReciboPagamento === 'function') {
      abrirModalReciboPagamento(pagamentoId);
    }
  };
}

if (typeof window.descarregarReciboPdf !== 'function') {
  window.descarregarReciboPdf = async function(pagamentoId) {
    try {
      if (typeof mostrarNotificacao === 'function') {
        mostrarNotificacao('A emitir e descarregar recibo oficial em PDF...', 'info');
      }
      if (typeof downloadFicheiroBinario === 'function') {
        await downloadFicheiroBinario(`/api/v1/impressao/recibo/${pagamentoId}/pdf`, `Recibo_${pagamentoId}.pdf`);
      } else {
        window.open(`/api/v1/impressao/recibo/${pagamentoId}/pdf`, '_blank');
      }
      if (typeof mostrarNotificacao === 'function') {
        mostrarNotificacao('Recibo oficial descarregado com sucesso!', 'success');
      }
    } catch (err) {
      alert('Erro ao descarregar recibo em PDF: ' + (err.message || ''));
    }
  };
}

window.modalPagarSaldoCarteiraAluno = modalPagarSaldoCarteiraAluno;
window.aoMudarCarteiraAluno = aoMudarCarteiraAluno;
window.confirmarPagamentoSaldoAluno = confirmarPagamentoSaldoAluno;


