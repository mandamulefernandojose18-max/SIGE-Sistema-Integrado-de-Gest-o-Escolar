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
                ${p.status === 'PAGO' ? `
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="imprimirReciboPagamento('${p.id}')" title="Visualizar e Imprimir Recibo">
                      <i class="bi bi-printer me-1"></i> Imprimir
                    </button>
                    <button class="btn btn-primary" onclick="descarregarReciboPdf('${p.id}')" title="Descarregar Recibo Oficial em PDF (PDFKit)">
                      <i class="bi bi-file-earmark-pdf me-1"></i> PDF
                    </button>
                  </div>
                ` : '<span class="badge bg-light text-muted border">Pendente</span>'}
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
