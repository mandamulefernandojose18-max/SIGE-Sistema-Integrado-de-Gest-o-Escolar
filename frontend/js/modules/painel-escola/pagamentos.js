/**
 * SIGE - PAINEL-ESCOLA | Mensalidades & Propinas
 * Ficheiro de código independente do menu: pagamentos.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 10. FINANCEIRO & MENSALIDADES ====================
async function carregarPagamentos() {
  try {
    const [resP, resStats] = await Promise.all([
      apiFetch('/api/v1/pagamentos'),
      apiFetch('/api/v1/pagamentos/stats')
    ]);

    if (resStats.success) {
      const s = resStats.data;
      document.getElementById('finFaturadoCard').innerHTML = formatarMoeda(s.totalFaturado);
      document.getElementById('finAtrasadoCard').innerHTML = formatarMoeda(s.totalAtrasado);
      document.getElementById('finInadimplenciaCard').textContent = s.taxaInadimplencia + '%';
      document.getElementById('finAdimplentesCard').textContent = s.percentualAdimplentes + '%';
    }

    if (resP.success) {
      const tbody = document.getElementById('tabelaPagamentos');
      tbody.innerHTML = resP.data.map(p => `
        <tr>
          <td><strong>${p.aluno.nome}</strong></td>
          <td>${p.descricao}</td>
          <td><code>${p.mes_referencia}</code></td>
          <td><strong class="text-success">${formatarMoeda(p.valor)}</strong></td>
          <td>${new Date(p.data_vencimento).toLocaleDateString('pt-PT')}</td>
          <td>
            <span class="badge ${p.status === 'PAGO' ? 'bg-success' : 'bg-warning text-dark'}">
              ${p.status}
            </span>
          </td>
          <td class="text-end">
            <div class="btn-group btn-group-sm">
              ${p.status === 'PENDENTE' ? `
                <button class="btn btn-outline-success" onclick="liquidarPagamento('${p.id}', ${p.valor})">
                  <i class="bi bi-cash me-1"></i> Liquidar
                </button>
              ` : ''}
              <button class="btn btn-outline-primary" onclick="imprimirReciboPagamento('${p.id}')" title="Visualizar e Imprimir Recibo">
                <i class="bi bi-receipt me-1"></i> Recibo
              </button>
              <button class="btn btn-primary" onclick="descarregarReciboPdf('${p.id}')" title="Descarregar Recibo Oficial em PDF">
                <i class="bi bi-file-earmark-pdf me-1"></i> PDF
              </button>
            </div>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

async function liquidarPagamento(id, valor) {
  if (!confirm(`Confirmar recebimento e liquidação da quantia de ${valor.toLocaleString('pt-PT')} MZN?`)) return;
  try {
    const res = await apiFetch(`/api/v1/pagamentos/${id}/liquidar`, {
      method: 'POST',
      body: JSON.stringify({ valor_pago: Number(valor), metodo_pagamento: 'NUMERARIO_OU_POS' })
    });
    if (res.success) {
      mostrarNotificacao('Pagamento liquidado com sucesso! A emitir recibo oficial...', 'success');
      await carregarPagamentos();
      await abrirModalReciboPagamento(id);
    }
  } catch (err) {
    alert('Erro ao liquidar pagamento: ' + (err.message || ''));
  }
}

async function modalNovoPagamento() {
  const alunosRes = await apiFetch('/api/v1/alunos');
  const optAlunos = (alunosRes.data || []).map(a => `<option value="${a.id}">${a.nome} (${a.matricula})</option>`).join('');

  abrirModal('Lançar Cobrança Individual de Mensalidade', `
    <form id="formModalPag">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Aluno</label>
        <select id="mpagAluno" class="form-select" required>${optAlunos}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Descrição</label>
        <input type="text" id="mpagDesc" class="form-control" value="Mensalidade Escolar" required>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Mês Ref.</label>
          <input type="text" id="mpagMes" class="form-control" value="2026-03" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor em Meticais (MZN)</label>
          <input type="number" id="mpagValor" class="form-control" value="2500" required>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Data de Vencimento</label>
        <input type="date" id="mpagVenc" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Cobrança</button>
    </form>
  `);

  document.getElementById('formModalPag').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/pagamentos', {
        method: 'POST',
        body: JSON.stringify({
          aluno_id: document.getElementById('mpagAluno').value,
          descricao: document.getElementById('mpagDesc').value,
          mes_referencia: document.getElementById('mpagMes').value,
          valor: Number(document.getElementById('mpagValor').value),
          data_vencimento: document.getElementById('mpagVenc').value
        })
      });
      if (res.success) {
        fecharModal();
        carregarPagamentos();
      }
    } catch (err) {
      alert('Erro ao criar cobrança');
    }
  });
}

async function modalGerarMensalidadesTurma() {
  const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
  const optTurmas = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome}</option>`).join('');

  abrirModal('Gerar Mensalidades em Lote para a Turma', `
    <form id="formModalLotePag">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Turma</label>
        <select id="mlotTurma" class="form-select" required>${optTurmas}</select>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Mês Ref. (AAAA-MM)</label>
          <input type="text" id="mlotMes" class="form-control" value="2026-03" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor da Propina (MZN)</label>
          <input type="number" id="mlotValor" class="form-control" value="2500" required>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Data de Vencimento</label>
        <input type="date" id="mlotVenc" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Mensalidades para Todos os Alunos</button>
    </form>
  `);

  document.getElementById('formModalLotePag').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/pagamentos/gerar-turma', {
        method: 'POST',
        body: JSON.stringify({
          turma_id: document.getElementById('mlotTurma').value,
          mes_referencia: document.getElementById('mlotMes').value,
          valor: Number(document.getElementById('mlotValor').value),
          data_vencimento: document.getElementById('mlotVenc').value,
          descricao: `Propina de ${document.getElementById('mlotMes').value}`
        })
      });
      if (res.success) {
        alert(`Mensalidades geradas com sucesso para a turma!`);
        fecharModal();
        carregarPagamentos();
      }
    } catch (err) {
      alert(err.message || 'Erro ao gerar cobranças');
    }
  });
}

async function abrirModalReciboPagamento(pagamentoId) {
  try {
    const res = await apiFetch(`/api/v1/impressao/recibo/${pagamentoId}`);
    if (!res.success || !res.data) {
      alert('Recibo de pagamento não encontrado.');
      return;
    }
    const d = res.data;
    const safeName = (d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
    const carimboDataHora = d.carimboDataHora || (new Date().toLocaleDateString('pt-PT') + ' ' + new Date().toLocaleTimeString('pt-PT'));

    abrirModal(`Recibo Oficial de Pagamento — ${d.pagamento.recibo_numero || 'REC-2026'}`, `
      <div id="modalAreaRecibo" class="p-3 bg-white">
        <div class="text-center border-bottom pb-3 mb-3">
          <img src="/img/emblema-mocambique.png" style="width: 44px; height: 44px; margin-bottom: 3px;" alt="Emblema Nacional">
          <h6 class="fw-bold mb-1">${(d.escola?.nome || 'Escola Secundária').toUpperCase()}</h6>
          <p class="text-muted small mb-0">NUIT: ${d.escola?.nif_cnpj || '-'} | Telefone: ${d.escola?.telefone || '-'}</p>
          <h5 class="mt-2 fw-bold text-success text-uppercase">RECIBO DE PAGAMENTO DE PROPINAS</h5>
          <span class="badge bg-light text-dark border fs-6">Recibo Nº: <strong>${d.pagamento.recibo_numero || 'REC-2026-001'}</strong></span>
        </div>

        <div class="table-responsive">
          <table class="table table-bordered table-sm small mb-3">
            <tr><th class="bg-light w-35">Aluno:</th><td><strong>${d.aluno.nome}</strong> (Matrícula: ${d.aluno.matricula})</td></tr>
            <tr><th class="bg-light">Turma / Classe:</th><td>${d.aluno.turma?.nome || '-'} (${d.aluno.turma?.grau_ano || '-'})</td></tr>
            <tr><th class="bg-light">Descrição da Cobrança:</th><td>${d.pagamento.descricao}</td></tr>
            <tr><th class="bg-light">Mês de Referência:</th><td><code>${d.pagamento.mes_referencia}</code></td></tr>
            <tr><th class="bg-light">Valor Liquidado:</th><td class="fw-bold text-success fs-5">${formatarMoeda(d.pagamento.valor)}</td></tr>
            <tr><th class="bg-light">Forma de Liquidação:</th><td>${d.pagamento.metodo_pagamento || 'Numerário / POS'}</td></tr>
            <tr><th class="bg-light">Data do Pagamento:</th><td>${new Date(d.pagamento.pago_em || d.pagamento.data_pagamento || Date.now()).toLocaleDateString('pt-PT')}</td></tr>
            <tr><th class="bg-light">Estado:</th><td><span class="badge bg-success">LIQUIDADO / PAGO</span></td></tr>
          </table>
        </div>

        <div class="alert alert-light border small text-muted text-center py-2 mb-3">
          <i class="bi bi-clock-history me-1 text-primary"></i>
          Processado por Computador aos <strong>${carimboDataHora}</strong> | Autenticação Digital SIGE
        </div>

        <div class="row text-center pt-3 border-top small">
          <div class="col-6"><p class="mb-0 border-top pt-2 mx-3">A Secretaria / Tesouraria</p></div>
          <div class="col-6"><p class="mb-0 border-top pt-2 mx-3">O Aluno / Depositante</p></div>
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2 mt-3 pt-2 border-top no-print">
        <button type="button" class="btn btn-secondary btn-sm" onclick="fecharModal()">Fechar</button>
        <button type="button" class="btn btn-outline-primary btn-sm" onclick="descarregarReciboPdf('${pagamentoId}')">
          <i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF (PDFKit)
        </button>
        <button type="button" class="btn btn-primary btn-sm" onclick="imprimirElementoRecibo('modalAreaRecibo', 'Recibo_${safeName}_${d.pagamento.mes_referencia}')">
          <i class="bi bi-printer me-1"></i> Imprimir Recibo Oficial
        </button>
      </div>
    `);
  } catch (err) {
    alert('Erro ao carregar recibo de pagamento: ' + (err.message || ''));
  }
}

function imprimirElementoRecibo(elementId, titulo) {
  const el = document.getElementById(elementId);
  if (!el) return window.print();
  const originalTitle = document.title;
  document.title = titulo;
  const printWindow = window.open('', '_blank', 'width=800,height=600');
  if (printWindow) {
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${titulo}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
          body { font-family: Arial, sans-serif; background: #fff; padding: 20px; }
          @media print { .no-print { display: none !important; } }
        </style>
      </head>
      <body>
        ${el.innerHTML}
        <script>
          window.onload = function() { window.print(); };
        <\/script>
      </body>
      </html>
    `);
    printWindow.document.close();
  } else {
    window.print();
  }
  document.title = originalTitle;
}

function imprimirReciboPagamento(pagamentoId) {
  abrirModalReciboPagamento(pagamentoId);
}

async function descarregarReciboPdf(pagamentoId) {
  try {
    mostrarNotificacao('A emitir e descarregar recibo oficial em PDF (PDFKit)...', 'info');
    await downloadFicheiroBinario(`/api/v1/impressao/recibo/${pagamentoId}/pdf`, `Recibo_${pagamentoId}.pdf`);
    mostrarNotificacao('Recibo oficial descarregado com sucesso!', 'success');
  } catch (err) {
    alert('Erro ao descarregar recibo em PDF: ' + (err.message || ''));
  }
}

