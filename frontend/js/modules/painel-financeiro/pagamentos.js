/**
 * SIGE - PAINEL-FINANCEIRO | Gestão de Mensalidades & Propinas
 * Ficheiro de código independente do menu: pagamentos.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 10. FINANCEIRO & MENSALIDADES ====================
async function carregarPagamentos(anoParam) {
  try {
    const ano = anoParam || state.anoLectivoVisualizacao || localStorage.getItem('sige_ano_letivo_selecionado') || state.tenant?.ano_letivo_ativo || '2026';
    const queryAno = (ano && ano !== 'TODOS') ? `?ano_letivo=${encodeURIComponent(ano)}` : '';

    const [resP, resStats] = await Promise.all([
      apiFetch(`/api/v1/pagamentos${queryAno}`),
      apiFetch(`/api/v1/pagamentos/stats${queryAno}`)
    ]);

    if (resStats.success) {
      const s = resStats.data;
      document.getElementById('finFaturadoCard').innerHTML = formatarMoeda(s.totalFaturado);
      document.getElementById('finAtrasadoCard').innerHTML = formatarMoeda(s.totalAtrasado);
      document.getElementById('finInadimplenciaCard').textContent = s.taxaInadimplencia + '%';
      document.getElementById('finAdimplentesCard').textContent = s.percentualAdimplentes + '%';
    }

    if (resP.success) {
      window.listaUltimosPagamentos = resP.data || [];
      const tbody = document.getElementById('tabelaPagamentos');
      tbody.innerHTML = resP.data.map(p => `
        <tr>
          <td><strong>${p.aluno?.nome || (p.aluno_nome || '-')}</strong></td>
          <td>${p.descricao}</td>
          <td>
            ${p.plano ? `<span class="badge bg-primary bg-opacity-10 text-primary border border-primary"><i class="bi bi-tag me-1"></i>${p.plano.nome}</span>` : '<span class="text-muted small">Avulso</span>'}
          </td>
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
                <button class="btn btn-outline-success fw-semibold" onclick="modalLiquidarSaldoCarteira('${p.id}', ${p.valor}, '${(p.aluno?.nome || p.aluno_nome || '').replace(/'/g, "\\'")}', '${(p.descricao || '').replace(/'/g, "\\'")}')" title="Liquidar saldo com carteira móvel (M-Pesa / e-Mola)">
                  <i class="bi bi-wallet2 me-1"></i> Liquidar Saldo
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
      carregarPlanosEscola();
    }
  } catch (err) {}
}

function modalLiquidarSaldoCarteira(id, valor, alunoNome, descricao) {
  const nomeSeguro = escapeHtml(alunoNome || 'Aluno');
  const descSegura = escapeHtml(descricao || 'Propina / Mensalidade');
  const valorFormatado = formatarMoeda(valor);

  abrirModal('Liquidar Saldo de Propina / Mensalidade', `
    <form id="formLiquidarSaldo" onsubmit="confirmarLiquidacaoSaldo(event, '${id}')">
      <div class="p-3 mb-3 bg-light rounded border">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="text-muted small text-uppercase fw-semibold">Aluno</span>
          <strong class="text-dark">${nomeSeguro}</strong>
        </div>
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="text-muted small text-uppercase fw-semibold">Cobrança</span>
          <span>${descSegura}</span>
        </div>
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-muted small text-uppercase fw-semibold">Saldo a Liquidar</span>
          <strong class="text-success fs-5">${valorFormatado}</strong>
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label small fw-semibold">Método de Liquidação *</label>
        <select id="liqMetodo" class="form-select" required onchange="aoMudarMetodoLiquidacao()">
          <option value="MPESA">🔴 M-Pesa (Vodacom)</option>
          <option value="EMOLA">🟡 e-Mola (Movitel)</option>
          <option value="POS">💳 POS / Cartão Bancário</option>
          <option value="TRANSFERENCIA">🏦 Transferência Bancária / Depósito</option>
          <option value="NUMERARIO">💵 Numerário</option>
        </select>
      </div>

      <div id="boxCamposCarteiraMovel" class="p-3 mb-3 rounded border border-warning bg-warning bg-opacity-10">
        <div class="d-flex align-items-center gap-2 mb-2">
          <i class="bi bi-phone-fill text-warning fs-5"></i>
          <strong class="small text-dark" id="liqCarteiraLabel">Carteira Móvel M-Pesa (Vodacom)</strong>
        </div>
        <div class="row g-2">
          <div class="col-sm-6">
            <label class="form-label small fw-semibold">Número de Carteira Móvel (+258)</label>
            <input type="tel" id="liqTelefone" class="form-control" placeholder="Ex: 84XXXXXXX ou 85XXXXXXX" maxlength="15">
          </div>
          <div class="col-sm-6">
            <label class="form-label small fw-semibold">Código / Referência da Transacção</label>
            <input type="text" id="liqReferencia" class="form-control" placeholder="Ex: MP261017.0001">
          </div>
        </div>
        <small class="text-muted d-block mt-2">
          <i class="bi bi-info-circle me-1"></i>Introduza o código da transacção recebido por SMS na carteira móvel para conciliação automática.
        </small>
      </div>

      <div class="mb-3">
        <label class="form-label small fw-semibold">Valor Liquidado em Meticais (MZN) *</label>
        <input type="number" step="0.01" min="0.01" id="liqValorPago" class="form-control fw-bold" value="${Number(valor)}" required>
      </div>

      <div class="d-flex justify-content-end gap-2 pt-2 border-top">
        <button type="button" class="btn btn-secondary" onclick="fecharModal()">Cancelar</button>
        <button type="submit" id="btnConfirmarLiq" class="btn btn-success fw-bold">
          <i class="bi bi-check-circle me-1"></i> Confirmar Liquidação de Saldo
        </button>
      </div>
    </form>
  `);
}

function aoMudarMetodoLiquidacao() {
  const met = document.getElementById('liqMetodo')?.value;
  const box = document.getElementById('boxCamposCarteiraMovel');
  const lbl = document.getElementById('liqCarteiraLabel');
  const tel = document.getElementById('liqTelefone');
  if (!box) return;

  if (met === 'MPESA') {
    box.style.display = 'block';
    if (lbl) lbl.textContent = 'Carteira Móvel M-Pesa (Vodacom)';
    if (tel) tel.placeholder = 'Ex: 84XXXXXXX ou 85XXXXXXX';
  } else if (met === 'EMOLA') {
    box.style.display = 'block';
    if (lbl) lbl.textContent = 'Carteira Móvel e-Mola (Movitel)';
    if (tel) tel.placeholder = 'Ex: 86XXXXXXX ou 87XXXXXXX';
  } else {
    box.style.display = 'none';
  }
}

async function confirmarLiquidacaoSaldo(event, id) {
  event.preventDefault();
  const btn = document.getElementById('btnConfirmarLiq');
  if (btn) btn.disabled = true;

  try {
    const metodo = document.getElementById('liqMetodo')?.value || 'MPESA';
    const valorPago = Number(document.getElementById('liqValorPago')?.value || 0);
    const telefone = document.getElementById('liqTelefone')?.value?.trim() || '';
    const referencia = document.getElementById('liqReferencia')?.value?.trim() || '';

    const res = await apiFetch(`/api/v1/pagamentos/${id}/liquidar`, {
      method: 'POST',
      body: JSON.stringify({
        valor_pago: valorPago,
        metodo_pagamento: metodo,
        telefone: telefone,
        referencia: referencia
      })
    });

    if (res && res.success) {
      fecharModal();
      mostrarNotificacao(res.message || 'Pagamento liquidado com sucesso!', 'success');
      await carregarPagamentos();
      await abrirModalReciboPagamento(id);
    } else {
      mostrarNotificacao(res?.message || 'Falha ao liquidar pagamento.', 'danger');
    }
  } catch (err) {
    mostrarNotificacao('Erro ao liquidar pagamento: ' + (err.message || ''), 'danger');
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function liquidarPagamento(id, valor) {
  return modalLiquidarSaldoCarteira(id, valor, '', '');
}

async function modalNovoPagamento() {
  const [alunosRes, planosRes] = await Promise.all([
    apiFetch('/api/v1/alunos'),
    apiFetch('/api/v1/pagamentos/planos-escola?ativo=true')
  ]);

  const optAlunos = (alunosRes.data || []).map(a => `<option value="${a.id}">${a.nome} (${a.matricula})</option>`).join('');
  const planos = (planosRes.data || []);
  const optPlanos = `<option value="">-- Personalizado / Sem Plano Vinculado --</option>` +
    planos.map(p => `<option value="${p.id}" data-valor="${p.valor}" data-nome="${p.nome}" data-dia="${p.dia_vencimento_padrao}">${p.nome} (${formatarMoeda(p.valor)})</option>`).join('');

  abrirModal('Lançar Cobrança Individual de Mensalidade', `
    <form id="formModalPag">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Aluno *</label>
        <select id="mpagAluno" class="form-select" required>${optAlunos}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Plano de Propinas da Escola (Opcional)</label>
        <select id="mpagPlano" class="form-select">${optPlanos}</select>
        <small class="text-muted">Seleccione um plano criado por esta escola para preenchimento automático.</small>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Descrição *</label>
        <input type="text" id="mpagDesc" class="form-control" value="Mensalidade Escolar" required>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Mês Ref. *</label>
          <input type="text" id="mpagMes" class="form-control" value="2026-03" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor em Meticais (MZN) *</label>
          <input type="number" id="mpagValor" class="form-control" value="2500" required>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Data de Vencimento *</label>
        <input type="date" id="mpagVenc" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Cobrança</button>
    </form>
  `);

  const selPlano = document.getElementById('mpagPlano');
  if (selPlano) {
    selPlano.addEventListener('change', () => {
      const opt = selPlano.options[selPlano.selectedIndex];
      if (opt && opt.value) {
        document.getElementById('mpagDesc').value = opt.getAttribute('data-nome') || '';
        document.getElementById('mpagValor').value = opt.getAttribute('data-valor') || '';
        const dia = opt.getAttribute('data-dia') || '10';
        const hoje = new Date();
        const ano = hoje.getFullYear();
        const mes = String(hoje.getMonth() + 1).padStart(2, '0');
        document.getElementById('mpagVenc').value = `${ano}-${mes}-${String(dia).padStart(2, '0')}`;
      }
    });
  }

  document.getElementById('formModalPag').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const alunoId = document.getElementById('mpagAluno').value;
      const mesRef = document.getElementById('mpagMes').value.trim();
      const planoId = document.getElementById('mpagPlano').value || null;

      // Verificação preventiva local se a fatura já existe no sistema para este mês
      if (window.listaUltimosPagamentos && window.listaUltimosPagamentos.some(p => {
        const pAlunoId = p.aluno?.id || p.aluno_id || (typeof p.aluno === 'string' ? p.aluno : null);
        return String(pAlunoId) === String(alunoId) && String(p.mes_referencia).trim() === mesRef && p.status !== 'CANCELADO';
      })) {
        mostrarAlerta('A factura já foi gerada no sistema.', 'warning', 'Aviso');
        return;
      }

      const res = await apiFetch('/api/v1/pagamentos', {
        method: 'POST',
        body: JSON.stringify({
          aluno_id: alunoId,
          plano_pagamento_id: planoId,
          descricao: document.getElementById('mpagDesc').value,
          mes_referencia: mesRef,
          valor: Number(document.getElementById('mpagValor').value),
          data_vencimento: document.getElementById('mpagVenc').value
        })
      });
      if (res.success) {
        mostrarNotificacao('Cobrança gerada com sucesso!', 'success');
        fecharModal();
        carregarPagamentos();
      }
    } catch (err) {
      const msg = err.message || 'Erro ao criar cobrança';
      mostrarAlerta(msg, 'warning', 'Aviso');
    }
  });
}

async function modalGerarMensalidadesTurma() {
  const [turmasRes, planosRes] = await Promise.all([
    apiFetch('/api/v1/escola-admin/turmas'),
    apiFetch('/api/v1/pagamentos/planos-escola?ativo=true')
  ]);

  const optTurmas = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome}</option>`).join('');
  const planos = (planosRes.data || []);
  const optPlanos = `<option value="">-- Personalizado / Sem Plano Vinculado --</option>` +
    planos.map(p => `<option value="${p.id}" data-valor="${p.valor}" data-nome="${p.nome}" data-dia="${p.dia_vencimento_padrao}">${p.nome} (${formatarMoeda(p.valor)})</option>`).join('');

  abrirModal('Gerar Mensalidades em Lote para a Turma', `
    <form id="formModalLotePag">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Turma *</label>
        <select id="mlotTurma" class="form-select" required>${optTurmas}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Plano de Propinas da Escola (Opcional)</label>
        <select id="mlotPlano" class="form-select">${optPlanos}</select>
        <small class="text-muted">Seleccione um plano criado por esta escola para preenchimento automático.</small>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Descrição da Cobrança *</label>
        <input type="text" id="mlotDesc" class="form-control" value="Propina de 2026-03" required>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Mês Ref. (AAAA-MM) *</label>
          <input type="text" id="mlotMes" class="form-control" value="2026-03" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor da Propina (MZN) *</label>
          <input type="number" id="mlotValor" class="form-control" value="2500" required>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Data de Vencimento *</label>
        <input type="date" id="mlotVenc" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Mensalidades para Todos os Alunos</button>
    </form>
  `);

  const selPlano = document.getElementById('mlotPlano');
  if (selPlano) {
    selPlano.addEventListener('change', () => {
      const opt = selPlano.options[selPlano.selectedIndex];
      if (opt && opt.value) {
        document.getElementById('mlotValor').value = opt.getAttribute('data-valor') || '';
        const nomePlano = opt.getAttribute('data-nome') || '';
        const mesRef = document.getElementById('mlotMes').value || '';
        document.getElementById('mlotDesc').value = `${nomePlano} - ${mesRef}`;
        const dia = opt.getAttribute('data-dia') || '10';
        const hoje = new Date();
        const ano = hoje.getFullYear();
        const mes = String(hoje.getMonth() + 1).padStart(2, '0');
        document.getElementById('mlotVenc').value = `${ano}-${mes}-${String(dia).padStart(2, '0')}`;
      }
    });
  }

  document.getElementById('formModalLotePag').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const turmaId = document.getElementById('mlotTurma').value;
      const mesRef = document.getElementById('mlotMes').value.trim();
      const planoId = document.getElementById('mlotPlano').value || null;

      const res = await apiFetch('/api/v1/pagamentos/gerar-turma', {
        method: 'POST',
        body: JSON.stringify({
          turma_id: turmaId,
          plano_id: planoId,
          mes_referencia: mesRef,
          valor: Number(document.getElementById('mlotValor').value),
          data_vencimento: document.getElementById('mlotVenc').value,
          descricao: document.getElementById('mlotDesc').value
        })
      });
      if (res.success) {
        const msg = res.message || 'Mensalidades geradas com sucesso para a turma!';
        mostrarNotificacao(msg, 'success');
        fecharModal();
        carregarPagamentos();
      }
    } catch (err) {
      const msg = err.message || 'Erro ao gerar cobranças';
      mostrarAlerta(msg, 'warning', 'Aviso');
    }
  });
}

// ==================== GESTÃO DE PLANOS PRÓPRIOS DA ESCOLA ====================
async function carregarPlanosEscola() {
  const tbody = document.getElementById('tabelaPlanosEscola');
  if (!tbody) return;
  try {
    const res = await apiFetch('/api/v1/pagamentos/planos-escola');
    if (res && res.success && Array.isArray(res.data)) {
      window.listaPlanosEscola = res.data;
      if (res.data.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" class="text-center py-4 text-muted">
              <i class="bi bi-info-circle me-1"></i>Nenhum plano ou emolumento criado ainda por esta instituição.
              <br><small>Clique em <strong>Novo Plano Escolar</strong> para definir a tabela oficial de propinas e taxas da escola.</small>
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = res.data.map(plano => `
        <tr>
          <td>
            <strong>${plano.nome}</strong>
            ${plano.descricao ? `<br><small class="text-muted">${plano.descricao}</small>` : ''}
          </td>
          <td>
            <span class="badge bg-info bg-opacity-10 text-info border border-info">
              ${plano.periodicidade_display || plano.periodicidade}
            </span>
          </td>
          <td><strong class="text-success">${formatarMoeda(plano.valor)}</strong></td>
          <td>Dia <strong>${plano.dia_vencimento_padrao}</strong></td>
          <td><span class="badge bg-secondary">${plano.total_faturas || 0} faturas</span></td>
          <td>
            <span class="badge ${plano.ativo ? 'bg-success' : 'bg-secondary'}">
              ${plano.ativo ? 'Activo' : 'Inactivo'}
            </span>
          </td>
          <td class="text-end">
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-primary btn-sm" onclick="modalEditarPlanoEscola('${plano.id}')" title="Editar Plano">
                <i class="bi bi-pencil me-1"></i> Editar
              </button>
              <button class="btn btn-outline-${plano.ativo ? 'danger' : 'success'} btn-sm" onclick="toggleStatusPlanoEscola('${plano.id}', ${plano.ativo})" title="${plano.ativo ? 'Desactivar' : 'Activar'}">
                <i class="bi bi-${plano.ativo ? 'slash-circle' : 'check-circle'} me-1"></i> ${plano.ativo ? 'Desactivar' : 'Activar'}
              </button>
            </div>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">Erro ao carregar planos de pagamento: ${err.message || ''}</td></tr>`;
  }
}

async function modalNovoPlanoEscola() {
  abrirModal('Novo Plano de Propinas / Taxa da Escola', `
    <form id="formModalPlanoEscola">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nome do Plano / Emolumento *</label>
        <input type="text" id="planoNome" class="form-control" placeholder="ex: Propina Regular 10ª Classe, Taxa de Matrícula" required>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor em Meticais (MZN) *</label>
          <input type="number" id="planoValor" class="form-control" min="0" step="0.01" placeholder="2500" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Periodicidade *</label>
          <select id="planoPeriodicidade" class="form-select" required>
            <option value="MENSAL" selected>Mensal</option>
            <option value="TRIMESTRAL">Trimestral</option>
            <option value="SEMESTRAL">Semestral</option>
            <option value="ANUAL">Anual</option>
            <option value="UNICA">Taxa Única / Emolumento</option>
          </select>
        </div>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Dia de Vencimento Padrão *</label>
          <input type="number" id="planoDiaVenc" class="form-control" min="1" max="31" value="10" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Multa por Atraso (%)</label>
          <input type="number" id="planoMulta" class="form-control" min="0" step="0.01" value="0">
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Descrição / Observações</label>
        <textarea id="planoDescricao" class="form-control" rows="2" placeholder="Informações adicionais aplicáveis a esta propina ou taxa"></textarea>
      </div>
      <button type="submit" class="btn btn-primary w-100">Criar Plano de Propinas</button>
    </form>
  `);

  document.getElementById('formModalPlanoEscola').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const payload = {
        nome: document.getElementById('planoNome').value.trim(),
        valor: Number(document.getElementById('planoValor').value),
        periodicidade: document.getElementById('planoPeriodicidade').value,
        dia_vencimento_padrao: Number(document.getElementById('planoDiaVenc').value),
        multa_atraso_percentual: Number(document.getElementById('planoMulta').value || 0),
        descricao: document.getElementById('planoDescricao').value.trim(),
      };
      const res = await apiFetch('/api/v1/pagamentos/planos-escola', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      if (res.success) {
        mostrarNotificacao('Plano de pagamento escolar criado com sucesso!', 'success');
        fecharModal();
        await carregarPlanosEscola();
      }
    } catch (err) {
      mostrarAlerta(err.message || 'Erro ao criar plano', 'danger', 'Erro');
    }
  });
}

async function modalEditarPlanoEscola(planoId) {
  const plano = (window.listaPlanosEscola || []).find(p => String(p.id) === String(planoId));
  if (!plano) return;

  abrirModal('Editar Plano de Propinas da Escola', `
    <form id="formModalEditPlanoEscola">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nome do Plano / Emolumento *</label>
        <input type="text" id="editPlanoNome" class="form-control" value="${plano.nome}" required>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor em Meticais (MZN) *</label>
          <input type="number" id="editPlanoValor" class="form-control" min="0" step="0.01" value="${plano.valor}" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Periodicidade *</label>
          <select id="editPlanoPeriodicidade" class="form-select" required>
            <option value="MENSAL" ${plano.periodicidade === 'MENSAL' ? 'selected' : ''}>Mensal</option>
            <option value="TRIMESTRAL" ${plano.periodicidade === 'TRIMESTRAL' ? 'selected' : ''}>Trimestral</option>
            <option value="SEMESTRAL" ${plano.periodicidade === 'SEMESTRAL' ? 'selected' : ''}>Semestral</option>
            <option value="ANUAL" ${plano.periodicidade === 'ANUAL' ? 'selected' : ''}>Anual</option>
            <option value="UNICA" ${plano.periodicidade === 'UNICA' ? 'selected' : ''}>Taxa Única / Emolumento</option>
          </select>
        </div>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Dia de Vencimento Padrão *</label>
          <input type="number" id="editPlanoDiaVenc" class="form-control" min="1" max="31" value="${plano.dia_vencimento_padrao || 10}" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Multa por Atraso (%)</label>
          <input type="number" id="editPlanoMulta" class="form-control" min="0" step="0.01" value="${plano.multa_atraso_percentual || 0}">
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Descrição / Observações</label>
        <textarea id="editPlanoDescricao" class="form-control" rows="2">${plano.descricao || ''}</textarea>
      </div>
      <button type="submit" class="btn btn-primary w-100">Guardar Alterações</button>
    </form>
  `);

  document.getElementById('formModalEditPlanoEscola').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const payload = {
        nome: document.getElementById('editPlanoNome').value.trim(),
        valor: Number(document.getElementById('editPlanoValor').value),
        periodicidade: document.getElementById('editPlanoPeriodicidade').value,
        dia_vencimento_padrao: Number(document.getElementById('editPlanoDiaVenc').value),
        multa_atraso_percentual: Number(document.getElementById('editPlanoMulta').value || 0),
        descricao: document.getElementById('editPlanoDescricao').value.trim(),
      };
      const res = await apiFetch(`/api/v1/pagamentos/planos-escola/${planoId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
      });
      if (res.success) {
        mostrarNotificacao('Plano actualizado com sucesso!', 'success');
        fecharModal();
        await carregarPlanosEscola();
      }
    } catch (err) {
      mostrarAlerta(err.message || 'Erro ao actualizar plano', 'danger', 'Erro');
    }
  });
}

async function toggleStatusPlanoEscola(planoId, estadoAtual) {
  const novoEstado = !estadoAtual;
  const acaoTexto = novoEstado ? 'activar' : 'desactivar';
  if (!confirm(`Tem a certeza que deseja ${acaoTexto} este plano de pagamento escolar?`)) return;

  try {
    const res = await apiFetch(`/api/v1/pagamentos/planos-escola/${planoId}`, {
      method: 'PATCH',
      body: JSON.stringify({ ativo: novoEstado })
    });
    if (res.success) {
      mostrarNotificacao(`Plano ${novoEstado ? 'activado' : 'desactivado'} com sucesso!`, 'success');
      await carregarPlanosEscola();
    }
  } catch (err) {
    mostrarAlerta(err.message || 'Erro ao alterar estado do plano', 'danger', 'Erro');
  }
}

async function abrirModalReciboPagamento(pagamentoId) {
  try {
    const res = await apiFetch(`/api/v1/impressao/recibo/${pagamentoId}`);
    if (!res.success || !res.data) {
      alert('Recibo de pagamento não encontrado.');
      return;
    }
    const d = res.data;
    const isPago = d.is_pago === true || (d.pagamento && d.pagamento.is_pago === true) || (d.pagamento && d.pagamento.status === 'PAGO' && (d.pagamento.data_pagamento || Number(d.pagamento.valor_pago || 0) > 0));
    const statusLabel = isPago ? 'PAGO' : 'NÃO PAGO';
    const statusClass = isPago ? 'bg-success' : 'bg-danger';
    const textClass = isPago ? 'text-success' : 'text-danger';
    const safeName = (d.aluno?.nome_completo || d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
    const carimboDataHora = d.carimboDataHora || (new Date().toLocaleDateString('pt-PT') + ' ' + new Date().toLocaleTimeString('pt-PT'));

    abrirModal(`Recibo Oficial — ${d.pagamento.recibo_numero || 'REC-2026'} [${statusLabel}]`, `
      <div id="modalAreaRecibo" class="p-4 bg-white position-relative" style="overflow: hidden; border-radius: 8px;">
        <!-- Marca d'Água de Segurança -->
        <div class="watermark-carimbo ${isPago ? 'watermark-pago' : 'watermark-nao-pago'}" style="position: absolute; top: 40%; left: 50%; transform: translate(-50%, -50%) rotate(-30deg); font-size: 64px; font-weight: 900; letter-spacing: 5px; opacity: 0.12; pointer-events: none; user-select: none; z-index: 10; border: 5px ${isPago ? 'solid #16a34a; color: #16a34a' : 'dashed #dc2626; color: #dc2626'}; padding: 10px 40px; border-radius: 12px; white-space: nowrap;">
          ${statusLabel}
        </div>

        <div class="text-center border-bottom pb-3 mb-3">
          <img src="/img/emblema-mocambique.png" style="width: 44px; height: 44px; margin-bottom: 4px;" alt="Emblema Nacional">
          <div class="small fw-semibold text-uppercase text-secondary" style="letter-spacing: 0.5px;">República de Moçambique &bull; Ministério da Educação e Desenvolvimento Humano</div>
          <h6 class="fw-bold mb-1 mt-1 text-dark">${(d.escola?.nome || 'Escola Secundária').toUpperCase()}</h6>
          <p class="text-muted small mb-0">NUIT: ${d.escola?.nif_cnpj || '-'} &bull; ${d.escola?.distrito || '-'}, ${d.escola?.provincia || '-'} &bull; Tel: ${d.escola?.telefone || '-'}</p>
          <h5 class="mt-3 fw-bold ${textClass} text-uppercase" style="letter-spacing: 0.5px;">
            ${isPago ? 'RECIBO DE PAGAMENTO OFICIAL' : 'RECIBO / GUIA DE COBRANÇA (NÃO PAGO)'}
          </h5>
          <span class="badge bg-light text-dark border fs-6">Recibo Nº: <strong>${d.pagamento.recibo_numero || 'REC-2026-001'}</strong></span>
        </div>

        <!-- Banner Destacado de Situação -->
        <div class="p-2 mb-3 rounded text-center fw-bold ${isPago ? 'bg-success bg-opacity-10 text-success border border-success' : 'bg-danger bg-opacity-10 text-danger border border-danger'}">
          <i class="bi ${isPago ? 'bi-check-circle-fill' : 'bi-exclamation-octagon-fill'} me-2"></i>
          SITUAÇÃO: ${statusLabel} ${isPago ? '(LIQUIDADO COM SUCESSO)' : '(PENDENTE DE LIQUIDAÇÃO)'}
        </div>

        <div class="table-responsive">
          <table class="table table-bordered table-sm small mb-3 align-middle">
            <tr><th class="bg-light w-35">Instituição:</th><td><strong>${d.escola?.nome || '-'}</strong> (${d.escola?.distrito || '-'}, ${d.escola?.provincia || '-'})</td></tr>
            <tr><th class="bg-light">Aluno(a):</th><td><strong>${d.aluno?.nome_completo || d.aluno?.nome || '-'}</strong></td></tr>
            <tr><th class="bg-light">Nº de Matrícula:</th><td><code>${d.aluno?.matricula || '-'}</code></td></tr>
            <tr><th class="bg-light">Turma / Classe:</th><td>${d.aluno?.turma?.nome || '-'} (${d.aluno?.turma?.grau_ano || '-'}) ${d.aluno?.turma?.turno ? '&bull; Turno: ' + d.aluno?.turma?.turno : ''}</td></tr>
            <tr><th class="bg-light">Descrição da Cobrança:</th><td>${d.pagamento.descricao || 'Mensalidade / Propina'}</td></tr>
            <tr><th class="bg-light">Mês de Referência:</th><td><code>${d.pagamento.mes_referencia || '-'}</code></td></tr>
            <tr><th class="bg-light">Valor Cobrado:</th><td><strong>${formatarMoeda(d.pagamento.valor || 0)}</strong></td></tr>
            <tr><th class="bg-light">Valor Liquidado:</th><td class="fw-bold ${textClass} fs-6">${isPago ? formatarMoeda(d.pagamento.valor_pago || d.pagamento.valor || 0) : '0,00 MZN (Pendente de Liquidação)'}</td></tr>
            <tr><th class="bg-light">Estado / Situação:</th><td><span class="badge ${statusClass} fs-6">${statusLabel}</span></td></tr>
            <tr><th class="bg-light">Forma de Liquidação:</th><td>${isPago ? (d.pagamento.metodo_pagamento || 'MPESA') : 'Pendente de Liquidação'}</td></tr>
            <tr><th class="bg-light">Data de Confirmação:</th><td>${isPago ? (d.pagamento.data_pagamento || '-') : 'Aguardando Confirmação'}</td></tr>
          </table>
        </div>

        <!-- Aviso Informativo -->
        ${!isPago ? `
          <div class="alert alert-danger py-2 px-3 small mb-3 border border-danger">
            <i class="bi bi-exclamation-triangle-fill text-danger me-1"></i>
            <strong>ATENÇÃO:</strong> Este recibo expressa a condição de <strong>NÃO PAGO</strong>. O documento comprova unicamente a emissão da cobrança e não confere quitação de dívida até a respectiva liquidação no sistema ou por carteira móvel.
          </div>
        ` : `
          <div class="alert alert-success py-2 px-3 small mb-3 border border-success">
            <i class="bi bi-shield-check text-success me-1"></i>
            <strong>COMPROVATIVO DE QUITAÇÃO:</strong> Certifica-se que o valor indicado foi devidamente liquidado e confirmado no sistema oficial SIGE.
          </div>
        `}

        <div class="alert alert-light border small text-muted text-center py-2 mb-3">
          <i class="bi bi-clock-history me-1 text-primary"></i>
          Processado por Computador aos <strong>${carimboDataHora}</strong> | Autenticação Digital SIGE &bull; Sincronizado
        </div>

        <div class="row text-center pt-3 border-top small">
          <div class="col-6"><p class="mb-0 border-top pt-2 mx-3">A Secretaria / Tesouraria<br><small class="text-muted">Assinatura e Carimbo</small></p></div>
          <div class="col-6"><p class="mb-0 border-top pt-2 mx-3">O Aluno / Depositante<br><small class="text-muted">Assinatura</small></p></div>
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2 mt-3 pt-2 border-top no-print">
        <button type="button" class="btn btn-secondary btn-sm" onclick="fecharModal()">Fechar</button>
        <button type="button" class="btn btn-outline-primary btn-sm" onclick="descarregarReciboPdf('${pagamentoId}')">
          <i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF (Oficial)
        </button>
        <button type="button" class="btn btn-primary btn-sm" onclick="imprimirElementoRecibo('modalAreaRecibo', 'Recibo_${safeName}_${d.pagamento.mes_referencia}_${statusLabel}')">
          <i class="bi bi-printer me-1"></i> Imprimir Recibo
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
  const printWindow = window.open('', '_blank', 'width=850,height=750');
  if (printWindow) {
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${titulo}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
          body { font-family: 'Times New Roman', Times, serif; background: #fff; padding: 25px; color: #111; }
          .watermark-carimbo {
            position: absolute;
            top: 45%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-30deg);
            font-size: 64px;
            font-weight: 900;
            letter-spacing: 5px;
            opacity: 0.15;
            pointer-events: none;
            user-select: none;
            z-index: 10;
            padding: 10px 40px;
            border-radius: 12px;
            white-space: nowrap;
          }
          .watermark-nao-pago {
            color: #dc2626 !important;
            border: 5px dashed #dc2626 !important;
          }
          .watermark-pago {
            color: #16a34a !important;
            border: 5px solid #16a34a !important;
          }
          @media print {
            .no-print { display: none !important; }
            body { padding: 10px; }
          }
        </style>
      </head>
      <body>
        <div style="position: relative;">
          ${el.innerHTML}
        </div>
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
