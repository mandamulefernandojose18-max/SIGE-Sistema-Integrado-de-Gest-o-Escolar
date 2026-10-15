/**
 * SIGE - PAINEL-ESCOLA | Director de Turma
 * Ficheiro de código independente do menu: director-turma.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== PAINEL DO DIRECTOR DE TURMA ====================
let dtTurmaAtivaId = null;
let dtAbaAtiva = 'pauta';

async function carregarPainelDirectorTurma() {
  const select = document.getElementById('dtTurmaSelect');
  if (!select) return;

  try {
    const res = await apiFetch('/api/v1/escola-admin/turmas');
    if (!res.success || !res.data.length) {
      select.innerHTML = '<option value="">Nenhuma turma cadastrada</option>';
      return;
    }

    const turmas = res.data;
    const turmasDirigidas = turmas.filter(t => 
      (t.director_turma_id && (t.director_turma_id === state.user?.id || t.director_turma_id === state.user?.professor_id)) ||
      (t.director_turma && (t.director_turma.id === state.user?.professor_id || t.director_turma.nome?.toLowerCase() === state.user?.nome?.toLowerCase()))
    );

    select.innerHTML = turmas.map(t => {
      const isMinha = turmasDirigidas.some(m => m.id === t.id);
      return `<option value="${t.id}">${t.nome} (${t.grau_ano} - ${t.turno || 'Diurno'})${isMinha ? ' ⭐ (Sua Turma de Direcção)' : ''}</option>`;
    }).join('');

    if (turmasDirigidas.length > 0) {
      dtTurmaAtivaId = turmasDirigidas[0].id;
    } else if (!dtTurmaAtivaId && turmas.length > 0) {
      dtTurmaAtivaId = turmas[0].id;
    }

    if (dtTurmaAtivaId) {
      select.value = dtTurmaAtivaId;
      await aoSelecionarTurmaDT(dtTurmaAtivaId);
    }
  } catch (err) {
    select.innerHTML = '<option value="">Erro ao carregar turmas</option>';
  }
}

async function aoSelecionarTurmaDT(turmaId) {
  if (!turmaId) return;
  dtTurmaAtivaId = turmaId;

  // Carregar parâmetros salvos do conselho
  const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
  let cp = {};
  if (savedParamsRaw) {
    try {
      cp = JSON.parse(savedParamsRaw) || {};
      // Se continha os dados fictícios hardcoded de demonstração antigos, descartar
      if (cp.dataT1 === '26/05/2026' && cp.dataT2 === '01/09/2026') {
        cp = {};
        localStorage.removeItem('sige_acta_params_' + turmaId);
      }
    } catch (e) {
      cp = {};
    }
  }

  document.getElementById('dtPresidenteT1').value = cp.presidenteT1 || '';
  document.getElementById('dtPresidenteT2').value = cp.presidenteT2 || '';
  document.getElementById('dtPresidenteT3').value = cp.presidenteT3 || '';

  document.getElementById('dtDataT1').value = formatarParaInputDate(cp.dataT1);
  document.getElementById('dtDataT2').value = formatarParaInputDate(cp.dataT2);
  document.getElementById('dtDataT3').value = formatarParaInputDate(cp.dataT3);

  document.getElementById('dtHIni1').value = cp.horaInicioT1 || '';
  document.getElementById('dtMIni1').value = cp.minInicioT1 || '';
  document.getElementById('dtHFim1').value = cp.horaFimT1 || '';
  document.getElementById('dtMFim1').value = cp.minFimT1 || '';

  document.getElementById('dtHIni2').value = cp.horaInicioT2 || '';
  document.getElementById('dtMIni2').value = cp.minInicioT2 || '';
  document.getElementById('dtHFim2').value = cp.horaFimT2 || '';
  document.getElementById('dtMFim2').value = cp.minFimT2 || '';

  document.getElementById('dtHIni3').value = cp.horaInicioT3 || '';
  document.getElementById('dtMIni3').value = cp.minInicioT3 || '';
  document.getElementById('dtHFim3').value = cp.horaFimT3 || '';
  document.getElementById('dtMFim3').value = cp.minFimT3 || '';

  await carregarDadosTurmaDT();
}

function limparParametrosSessaoDT() {
  if (!dtTurmaAtivaId) return alert('Selecione uma turma primeiro');
  localStorage.removeItem('sige_acta_params_' + dtTurmaAtivaId);

  document.getElementById('dtPresidenteT1').value = '';
  document.getElementById('dtPresidenteT2').value = '';
  document.getElementById('dtPresidenteT3').value = '';

  document.getElementById('dtDataT1').value = '';
  document.getElementById('dtDataT2').value = '';
  document.getElementById('dtDataT3').value = '';

  document.getElementById('dtHIni1').value = '';
  document.getElementById('dtMIni1').value = '';
  document.getElementById('dtHFim1').value = '';
  document.getElementById('dtMFim1').value = '';

  document.getElementById('dtHIni2').value = '';
  document.getElementById('dtMIni2').value = '';
  document.getElementById('dtHFim2').value = '';
  document.getElementById('dtMFim2').value = '';

  document.getElementById('dtHIni3').value = '';
  document.getElementById('dtMIni3').value = '';
  document.getElementById('dtHFim3').value = '';
  document.getElementById('dtMFim3').value = '';

  alert('Parâmetros da sessão limpos! A Acta da turma voltará a exibir as linhas pontilhadas oficiais em branco.');
  carregarDadosTurmaDT();
}

function salvarParametrosSessaoDT() {
  if (!dtTurmaAtivaId) return alert('Selecione uma turma primeiro');

  const params = {
    presidenteT1: document.getElementById('dtPresidenteT1').value,
    presidenteT2: document.getElementById('dtPresidenteT2').value,
    presidenteT3: document.getElementById('dtPresidenteT3').value,
    dataT1: document.getElementById('dtDataT1').value,
    dataT2: document.getElementById('dtDataT2').value,
    dataT3: document.getElementById('dtDataT3').value,
    horaInicioT1: document.getElementById('dtHIni1').value,
    minInicioT1: document.getElementById('dtMIni1').value,
    horaFimT1: document.getElementById('dtHFim1').value,
    minFimT1: document.getElementById('dtMFim1').value,
    horaInicioT2: document.getElementById('dtHIni2').value,
    minInicioT2: document.getElementById('dtMIni2').value,
    horaFimT2: document.getElementById('dtHFim2').value,
    minFimT2: document.getElementById('dtMFim2').value,
    horaInicioT3: document.getElementById('dtHIni3').value,
    minInicioT3: document.getElementById('dtMIni3').value,
    horaFimT3: document.getElementById('dtHFim3').value,
    minFimT3: document.getElementById('dtMFim3').value
  };

  localStorage.setItem('sige_acta_params_' + dtTurmaAtivaId, JSON.stringify(params));
  alert('Parâmetros da sessão do conselho salvos com sucesso! A Acta da turma foi atualizada.');
  carregarDadosTurmaDT();
}

function alternarAbaDT(aba) {
  dtAbaAtiva = aba;
  document.getElementById('dtTabPautaBtn').className = 'nav-link fw-bold ' + (aba === 'pauta' ? 'active' : '');
  document.getElementById('dtTabActaBtn').className = 'nav-link fw-bold ' + (aba === 'acta' ? 'active' : '');
  carregarDadosTurmaDT();
}

async function carregarDadosTurmaDT() {
  if (!dtTurmaAtivaId) return;
  const container = document.getElementById('dtDocumentoContainer');
  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar documento oficial da turma...</p></div>';

  try {
    if (dtAbaAtiva === 'pauta') {
      const res = await apiFetch(`/api/v1/pautas/turma/${dtTurmaAtivaId}/completa`);
      if (res.success) {
        const d = res.data;
        container.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom flex-wrap gap-2">
            <div>
              <h6 class="fw-bold text-dark mb-0">Pauta Geral: ${d.turma.nome} (${d.turma.grau_ano})</h6>
              <small class="text-muted">Ano Lectivo ${d.turma.ano_letivo} | Turno ${d.turma.turno || 'Diurno'}</small>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-outline-success btn-sm fw-semibold" onclick="exportarPautaGeralExcel('${dtTurmaAtivaId}', '${d.turma.ano_letivo}')">
                <i class="bi bi-file-earmark-excel me-1"></i> Excel
              </button>
              <button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarPautaGeralPdf()">
                <i class="bi bi-file-earmark-pdf me-1"></i> PDF
              </button>
              <button class="btn btn-primary btn-sm fw-semibold" onclick="window.print()">
                <i class="bi bi-printer me-1"></i> Imprimir
              </button>
            </div>
          </div>
          <div id="subViewPautaGeral" class="table-responsive">
            <!-- Tabela idêntica para exportação e impressão -->
            ${gerarTabelaPautaHtml(d)}
          </div>
        `;
      }
    } else {
      // Acta do Conselho
      await carregarActaConselho(dtTurmaAtivaId);
      const containerActa = document.getElementById('containerActaConselhoCorpo');
      if (containerActa) {
        container.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom flex-wrap gap-2">
            <div>
              <h6 class="fw-bold text-dark mb-0">Acta Oficial do Conselho de Avaliação</h6>
              <small class="text-muted">Modelo Oficial MEC Moçambique</small>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-outline-success btn-sm fw-semibold" onclick="exportarActaConselhoExcel('${dtTurmaAtivaId}')">
                <i class="bi bi-file-earmark-excel me-1"></i> Excel
              </button>
              <button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarActaConselhoPdf()">
                <i class="bi bi-file-earmark-pdf me-1"></i> PDF
              </button>
              <button class="btn btn-primary btn-sm fw-semibold" onclick="window.print()">
                <i class="bi bi-printer me-1"></i> Imprimir
              </button>
            </div>
          </div>
          <div id="subViewActaConselho">
            ${containerActa.innerHTML}
          </div>
        `;
      }
    }
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">Erro ao carregar dados da turma: ${err.message}</div>`;
  }
}

function gerarTabelaPautaHtml(d) {
  const formatNota = (val) => {
    if (val === null || val === undefined || isNaN(val) || val <= 0) return '<span class="text-muted">-</span>';
    const num = Number(val);
    const cls = num >= 9.5 ? 'text-dark fw-semibold' : 'text-danger fw-bold';
    return `<span class="${cls}">${Math.round(num)}</span>`;
  };

  const thDisciplinas = d.disciplinas.map(disc => 
    `<th colspan="4" class="text-center border-start border-end fw-bold" style="background-color: #eef2ff !important; color: #4338ca !important; border-color: #c7d2fe !important; font-size: 0.82rem;">${obterNomeCompletoDisciplina(disc.nome || disc.codigo)}</th>`
  ).join('');

  const thSubDisciplinas = d.disciplinas.map(() => 
    `<th style="font-size: 0.72rem;">1º</th><th style="font-size: 0.72rem;">2º</th><th style="font-size: 0.72rem;">3º</th><th style="font-size: 0.72rem; background-color: #e2e8f0 !important; font-weight: bold;">MFD</th>`
  ).join('');

  let trsAlunos = d.alunos.map((a, idx) => {
    const tdDisciplinas = d.disciplinas.map(disc => {
      const nd = a.notasDisciplinas[disc.codigo || disc.id] || a.notasDisciplinas[disc.id] || a.notasDisciplinas[disc.nome] || {};
      return `
        <td style="font-size: 0.82rem;">${formatNota(nd.t1)}</td>
        <td style="font-size: 0.82rem;">${formatNota(nd.t2)}</td>
        <td style="font-size: 0.82rem;">${formatNota(nd.t3)}</td>
        <td style="background-color: #f1f5f9 !important; font-weight: bold; font-size: 0.82rem;">${(nd.t1 !== '-' && nd.t2 !== '-' && nd.t3 !== '-' && nd.t1 !== null && nd.t2 !== null && nd.t3 !== null && Number(nd.t1) > 0 && Number(nd.t2) > 0 && Number(nd.t3) > 0) ? formatNota(nd.mfd) : '<span class="text-muted">-</span>'}</td>
      `;
    }).join('');

    let badgeResultado = '';
    const resTexto = (a.resultadoFinal || a.resultado || '').trim();
    if (resTexto === 'A' || resTexto === 'Aprovado') {
      badgeResultado = '<span class="fw-bold" style="font-weight: 700; color: #15803d !important;">Aprovado</span>';
    } else if (resTexto === 'R' || resTexto === 'Reprovado') {
      badgeResultado = '<span class="fw-bold text-danger" style="font-weight: 700; color: #dc2626 !important;">Reprovado</span>';
    } else if (resTexto === 'D' || resTexto === 'Desistente') {
      badgeResultado = '<span class="fw-bold text-secondary">Desistente</span>';
    } else if (resTexto === 'T' || resTexto === 'Transferido') {
      badgeResultado = '<span class="fw-bold text-secondary">Transferido</span>';
    } else {
      badgeResultado = `<span class="fw-bold text-secondary">${resTexto || '-'}</span>`;
    }

    const badgeGen = a.genero === 'F' 
      ? '<span class="badge" style="background-color: #0ea5e9; color: #ffffff; font-size: 0.75rem; padding: 2px 6px;">F</span>' 
      : '<span class="badge" style="background-color: #334155; color: #ffffff; font-size: 0.75rem; padding: 2px 6px;">M</span>';

    const nomeCompleto = a.nomeCompleto || `${a.nome || ''} ${a.apelido || ''}`.trim() || 'Aluno';

    return `
      <tr>
        <td><strong>${a.numero || (idx + 1)}</strong></td>
        <td class="text-start ps-3" style="font-size: 0.85rem;"><strong>${nomeCompleto}</strong></td>
        <td>${badgeGen}</td>
        ${tdDisciplinas}
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${formatNota(a.mediasTrimestrais.t1)}</td>
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${formatNota(a.mediasTrimestrais.t2)}</td>
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${formatNota(a.mediasTrimestrais.t3)}</td>
        <td style="font-size: 0.82rem;">${a.negativas.t1 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t1}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="font-size: 0.82rem;">${a.negativas.t2 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t2}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="font-size: 0.82rem;">${a.negativas.t3 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t3}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${a.negativas.fimDoAno > 0 ? `<span class="text-danger fw-bold">${a.negativas.fimDoAno}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="background-color: #e0e7ff; font-weight: bold; color: #1e1b4b; font-size: 0.95rem;">${formatNota(a.mediaFinalGeral)}</td>
        <td>${badgeResultado}</td>
      </tr>
    `;
  }).join('');

  return `
    <div class="table-responsive">
      <table class="table table-bordered table-sm table-hover align-middle text-center small mb-0">
        <thead class="table-light">
          <tr>
            <th rowspan="2" class="align-middle">Nº</th>
            <th rowspan="2" class="align-middle text-start ps-3" style="min-width: 210px; font-size: 0.85rem;">Nome Completo do Aluno</th>
            <th rowspan="2" class="align-middle">Gén</th>
            ${thDisciplinas}
            <th colspan="3" class="fw-semibold" style="background-color: #f8fafc !important; font-size: 0.75rem;">Médias Trimestrais</th>
            <th colspan="4" class="fw-semibold" style="background-color: #f8fafc !important; font-size: 0.75rem;">Disciplinas Negativas</th>
            <th rowspan="2" class="align-middle fw-bold" style="background-color: #4f46e5 !important; color: #ffffff !important; font-size: 0.8rem;">Média Final</th>
            <th rowspan="2" class="align-middle fw-bold" style="background-color: #1e293b !important; color: #ffffff !important; font-size: 0.8rem;">Resultado</th>
          </tr>
          <tr>
            ${thSubDisciplinas}
            <th>1º</th><th>2º</th><th>3º</th>
            <th>1º</th><th>2º</th><th>3º</th><th>Total</th>
          </tr>
        </thead>
        <tbody>
          ${trsAlunos}
        </tbody>
      </table>
    </div>
  `;
}

async function eliminarEscolaSuperAdmin(escolaId, nome) {
  if (!confirm(`ATENÇÃO ENGENHEIRO:\nTem a certeza que deseja ELIMINAR DEFINITIVAMENTE a escola [${nome}] e todos os seus dados?\nEsta operação não pode ser revertida!`)) return;

  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}`, {
      method: 'DELETE'
    });
    if (res.success) {
      alert(res.message || 'Escola eliminada com sucesso');
      carregarPainelSaaS();
      carregarEscolasSuperAdminSelect();
    }
  } catch (err) {
    alert(err.message || 'Erro ao eliminar escola');
  }
}

async function descarregarExtratoEscolaSuperAdmin(escolaId) {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/comprovativo-contrato`);
    if (!res.success) throw new Error(res.message || 'Falha ao obter comprovativo');

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
            <strong>Instituição de Ensino:</strong> ${c.escola.nome}<br>
            <strong>NUIT / NIF:</strong> ${c.escola.nif_cnpj}<br>
            <strong>Localização:</strong> ${c.escola.distrito || '-'}, ${c.escola.provincia || '-'}<br>
            <strong>Contacto:</strong> ${c.escola.telefone || '-'} | ${c.escola.email}
          </div>
          <div class="col-6 text-end">
            <strong>Referência Contratual:</strong> ${c.comprovativo_numero}<br>
            <strong>Plano Subscrito:</strong> <span class="badge bg-primary">${c.plano.nome}</span><br>
            <strong>Estado da Licença:</strong> <span class="badge bg-success">${c.status_atual}</span><br>
            <strong>Valor Contratual:</strong> ${formatarMoeda(c.assinatura.valor)}
          </div>
        </div>

        <div class="table-responsive">
          <table class="table table-bordered table-sm small mb-4">
            <tr class="table-light"><th colspan="2" class="text-center fw-bold">VIGÊNCIA E CLÁUSULAS CONTRATUAIS</th></tr>
            <tr><th class="w-40">Data de Início:</th><td>${new Date(c.assinatura.data_inicio).toLocaleDateString('pt-PT')}</td></tr>
            <tr><th>Data de Vencimento:</th><td>${new Date(c.assinatura.data_fim).toLocaleDateString('pt-PT')}</td></tr>
            <tr><th>Capacidade Licenciada:</th><td>Até ${c.plano.max_alunos} alunos matriculados e ${c.plano.max_professores} docentes</td></tr>
            <tr><th>Alunos Ativos Registados:</th><td>${c.estatisticas.total_alunos} alunos</td></tr>
            <tr><th>Corpo Docente Ativo:</th><td>${c.estatisticas.total_professores} professores</td></tr>
            <tr><th>Turmas Cadastradas:</th><td>${c.estatisticas.total_turmas} turmas ativas</td></tr>
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
            <small class="text-muted">${c.escola.nome}</small>
          </div>
        </div>
      </div>
      <div class="text-end mt-3 no-print">
        <button class="btn btn-primary btn-sm" onclick="imprimirDocumentoComTitulo('Extrato_Contrato_${c.escola.nome.replace(/\s+/g, '_')}')">
          <i class="bi bi-printer me-1"></i> Imprimir / Descarregar em PDF
        </button>
      </div>
    `);
  } catch (err) {
    alert(err.message || 'Erro ao emitir extrato');
  }
}

