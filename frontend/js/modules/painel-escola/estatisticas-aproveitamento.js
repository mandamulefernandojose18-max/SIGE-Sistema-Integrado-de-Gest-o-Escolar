/**
 * SIGE - PAINEL-ESCOLA | Estatísticas de Aproveitamento
 * Ficheiro de código independente do menu: estatisticas-aproveitamento.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== ESTATÍSTICA DO APROVEITAMENTO PEDAGÓGICO ESCOLAR ====================
async function carregarEstatisticasAproveitamento() {
  const container = document.getElementById('containerEstatisticasDocumento');
  if (!container) return;

  const selAno = document.getElementById('statAnoFiltro');
  const ano = (selAno && selAno.value) ? selAno.value : (state.anoLectivoVisualizacao || localStorage.getItem('sige_ano_letivo_selecionado') || state.tenant?.ano_letivo_ativo || '2026');
  if (selAno && ano && selAno.value !== ano) selAno.value = ano;
  const periodo = document.getElementById('statPeriodoFiltro')?.value || 'GLOBAL';

  container.innerHTML = `
    <div class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="small text-muted mt-2">A compilar estatísticas gerais do aproveitamento pedagógico (${ano})...</p>
    </div>
  `;

  try {
    const res = await apiFetch(`/api/v1/pautas/estatisticas-gerais?anoLetivo=${ano}&periodo=${periodo}`);
    if (!res.success || !res.data) {
      container.innerHTML = `<div class="alert alert-warning text-center">Nenhum registo de notas ou turmas disponível para o ano lectivo ${ano}.</div>`;
      return;
    }

    const d = res.data || {};
    const ge = d.geralEscola || {
      inscritos: { total: 0, h: 0, m: 0 },
      avaliados: { total: 0, h: 0, m: 0 },
      aprovados: { total: 0, h: 0, m: 0, pct: 0 },
      reprovados: { total: 0, h: 0, m: 0, pct: 0 }
    };
    const porTurma = Array.isArray(d.porTurma) ? d.porTurma : [];
    const porClasse = Array.isArray(d.porClasse) ? d.porClasse : [];
    const porDisciplina = Array.isArray(d.porDisciplina) ? d.porDisciplina : [];
    const escolaNome = (d.escola && d.escola.nome) ? d.escola.nome : 'Escola';

    // Atualizar cartões KPI superiores
    if (document.getElementById('statKpiAprovacao')) {
      document.getElementById('statKpiAprovacao').textContent = `${ge.aprovados?.pct ?? 0}%`;
      document.getElementById('statKpiAprovacaoSub').textContent = `${ge.aprovados?.total ?? 0} Aprovados (${ge.aprovados?.h ?? 0} H / ${ge.aprovados?.m ?? 0} M)`;
      document.getElementById('statKpiReprovacao').textContent = `${ge.reprovados?.pct ?? 0}%`;
      document.getElementById('statKpiReprovacaoSub').textContent = `${ge.reprovados?.total ?? 0} Não transitam (${ge.reprovados?.h ?? 0} H / ${ge.reprovados?.m ?? 0} M)`;
      document.getElementById('statKpiAvaliados').textContent = `${ge.avaliados?.total ?? 0}`;
      document.getElementById('statKpiAvaliadosSub').textContent = `${ge.avaliados?.h ?? 0} H / ${ge.avaliados?.m ?? 0} M (Inscritos: ${ge.inscritos?.total ?? 0})`;
      document.getElementById('statKpiTurmas').textContent = `${porTurma.length}`;
      document.getElementById('statKpiTurmasSub').textContent = `${porClasse.length} Níveis de Ensino Secundário`;
    }

    // Renderizar Tabelas Estatísticas
    container.innerHTML = `
      <!-- Cabeçalho Institucional Oficial para Relatório e Impressão -->
      <div class="text-center pb-3 mb-4 border-bottom position-relative">
        <img src="/img/emblema-mocambique.png" style="width: 52px; height: 52px; object-fit: contain; margin-bottom: 3px;" alt="Emblema Nacional">
        <h6 class="fw-bold mb-0 text-uppercase">REPÚBLICA DE MOÇAMBIQUE</h6>
        <div class="text-muted small fw-semibold">MINISTÉRIO DA EDUCAÇÃO E CULTURA</div>
        <h5 class="fw-bold text-primary mt-2 mb-0">${escolaNome.toUpperCase()}</h5>
        <div class="badge bg-primary bg-opacity-10 text-primary border border-primary px-3 py-2 mt-2 fs-6">
          MAPA CONSOLIDADO DO RENDIMENTO E APROVEITAMENTO PEDAGÓGICO — ${ano} (${periodo === 'GLOBAL' ? 'MÉDIA ANUAL / MFD' : periodo})
        </div>
      </div>

      <!-- SECÇÃO 1: RESUMO GERAL DA ESCOLA -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-building me-1 text-primary"></i> 1. Resumo Global da Escola</h6>
          <span class="badge bg-secondary">${porTurma.length} Turmas Activas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-sm text-center align-middle small mb-0">
            <thead class="table-dark">
              <tr>
                <th colspan="3">Inscritos / Matriculados</th>
                <th colspan="3">Efectivo Avaliado</th>
                <th colspan="4">Aproveitamento Positivo (Aprovados)</th>
                <th colspan="4">Não Aproveitamento (Reprovados)</th>
              </tr>
              <tr class="table-light text-dark">
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th><th>% Tx Aprov.</th>
                <th>HM</th><th>M</th><th>Total</th><th>% Tx Reprov.</th>
              </tr>
            </thead>
            <tbody>
              <tr class="fw-bold fs-6">
                <td>${ge.inscritos.h}</td><td>${ge.inscritos.m}</td><td class="bg-light">${ge.inscritos.total}</td>
                <td>${ge.avaliados.h}</td><td>${ge.avaliados.m}</td><td class="bg-light">${ge.avaliados.total}</td>
                <td class="text-success">${ge.aprovados.h}</td><td class="text-success">${ge.aprovados.m}</td>
                <td class="text-success bg-light">${ge.aprovados.total}</td>
                <td class="text-success bg-success bg-opacity-10">${ge.aprovados.pct}%</td>
                <td class="text-danger">${ge.reprovados.h}</td><td class="text-danger">${ge.reprovados.m}</td>
                <td class="text-danger bg-light">${ge.reprovados.total}</td>
                <td class="text-danger bg-danger bg-opacity-10">${ge.reprovados.pct}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- SECÇÃO 2: RESUMO GERAL POR CLASSE (7ª A 12ª CLASSE) -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-layers-fill me-1 text-primary"></i> 2. Rendimento por Classe (7ª, 8ª, 9ª, 10ª, 11ª, 12ª)</h6>
          <span class="badge bg-primary">${porClasse.length} Classes Registadas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-hover table-sm text-center align-middle small mb-0">
            <thead class="table-primary">
              <tr>
                <th rowspan="2" class="align-middle text-start">Nível / Classe</th>
                <th rowspan="2" class="align-middle">Turmas</th>
                <th colspan="3">Inscritos</th>
                <th colspan="3">Avaliados</th>
                <th colspan="3">Aprovados</th>
                <th rowspan="2" class="align-middle bg-success text-white">% Aproveitamento</th>
                <th colspan="3">Reprovados</th>
                <th rowspan="2" class="align-middle bg-danger text-white">% Reprovação</th>
              </tr>
              <tr class="table-light text-dark">
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
              </tr>
            </thead>
            <tbody>
              ${porClasse.map(c => `
                <tr>
                  <td class="text-start fw-bold">${c.classe} Classe</td>
                  <td><span class="badge bg-light text-dark border">${c.turmas}</span></td>
                  <td>${c.inscritos.h}</td><td>${c.inscritos.m}</td><td class="fw-bold bg-light">${c.inscritos.total}</td>
                  <td>${c.avaliados.h}</td><td>${c.avaliados.m}</td><td class="fw-bold bg-light">${c.avaliados.total}</td>
                  <td class="text-success">${c.aprovados.h}</td><td class="text-success">${c.aprovados.m}</td>
                  <td class="text-success fw-bold bg-light">${c.aprovados.total}</td>
                  <td class="fw-bold ${c.aprovados.pct >= 50 ? 'text-success' : 'text-danger'}">${c.aprovados.pct}%</td>
                  <td class="text-danger">${c.reprovados.h}</td><td class="text-danger">${c.reprovados.m}</td>
                  <td class="text-danger fw-bold bg-light">${c.reprovados.total}</td>
                  <td class="fw-bold text-danger">${c.reprovados.pct}%</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- SECÇÃO 3: APROVEITAMENTO POR TURMA -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-people-fill me-1 text-primary"></i> 3. Aproveitamento Pedagógico por Turma</h6>
          <span class="badge bg-info text-dark">${porTurma.length} Turmas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-hover table-sm text-center align-middle small mb-0">
            <thead class="table-secondary">
              <tr>
                <th class="text-start">Turma</th>
                <th>Classe</th>
                <th>Turno</th>
                <th class="text-start">Director de Turma</th>
                <th>Inscritos Total</th>
                <th>Avaliados Total</th>
                <th class="text-success">Aprovados</th>
                <th class="bg-success text-white">% Aproveitamento</th>
                <th class="text-danger">Reprovados</th>
                <th class="bg-danger text-white">% Reprovação</th>
              </tr>
            </thead>
            <tbody>
              ${porTurma.map(t => `
                <tr>
                  <td class="text-start fw-bold">${t.turmaNome}</td>
                  <td>${t.grau_ano}</td>
                  <td>${t.turno}</td>
                  <td class="text-start">${t.directorTurma}</td>
                  <td>${t.inscritos.total}</td>
                  <td class="fw-bold">${t.avaliados.total}</td>
                  <td class="text-success fw-bold">${t.aprovados.total}</td>
                  <td class="fw-bold ${t.aprovados.pct >= 50 ? 'text-success bg-success bg-opacity-10' : 'text-danger bg-danger bg-opacity-10'}">${t.aprovados.pct}%</td>
                  <td class="text-danger">${t.reprovados.total}</td>
                  <td class="text-danger">${t.reprovados.pct}%</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- SECÇÃO 4: APROVEITAMENTO POR DISCIPLINA -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-book-half me-1 text-primary"></i> 4. Rendimento Comparativo por Disciplina</h6>
          <span class="badge bg-secondary">${porDisciplina.length} Disciplinas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-hover table-sm text-center align-middle small mb-0">
            <thead class="table-light">
              <tr>
                <th class="text-start">Disciplina</th>
                <th>Código</th>
                <th>Avaliados (HM)</th>
                <th>Avaliados (M)</th>
                <th>Avaliados Total</th>
                <th class="text-success">Aprovados Total</th>
                <th class="bg-success text-white">% Aproveitamento</th>
                <th class="text-danger">Reprovados Total</th>
                <th class="bg-danger text-white">% Reprovação</th>
                <th class="bg-primary text-white">Média da Disciplina</th>
              </tr>
            </thead>
            <tbody>
              ${porDisciplina.map(disc => `
                <tr>
                  <td class="text-start fw-bold">${disc.nome}</td>
                  <td><code>${disc.codigo}</code></td>
                  <td>${disc.avaliados.h}</td>
                  <td>${disc.avaliados.m}</td>
                  <td class="fw-bold">${disc.avaliados.total}</td>
                  <td class="text-success fw-bold">${disc.aprovados.total}</td>
                  <td class="fw-bold ${disc.aprovados.pct >= 50 ? 'text-success bg-success bg-opacity-10' : 'text-danger bg-danger bg-opacity-10'}">${disc.aprovados.pct}%</td>
                  <td class="text-danger">${disc.reprovados.total}</td>
                  <td class="text-danger">${disc.reprovados.pct}%</td>
                  <td class="fw-bold ${disc.mediaFinal !== null && disc.mediaFinal >= 9.5 ? 'text-primary' : 'text-danger'}">
                    ${disc.mediaFinal !== null ? disc.mediaFinal : '-'}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Rodapé Formal de Validação -->
      <div class="row pt-4 mt-4 border-top text-center small no-print">
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-4">O Director Pedagógico (DAP)</p>
        </div>
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-4">O Chefe da Secretaria</p>
        </div>
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-4">O Director da Escola</p>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger text-center">Erro ao carregar estatísticas do aproveitamento: ${err.message || ''}</div>`;
  }
}

async function descarregarEstatisticasPdf() {
  const container = document.getElementById('containerEstatisticasDocumento');
  if (!container) return alert('Carregue as estatísticas primeiro');
  const ano = document.getElementById('statAnoFiltro')?.value || '2026';
  await exportarElementoParaPdf(container, `Estatisticas_Aproveitamento_Pedagogico_${ano}.pdf`, 'landscape');
}

function exportarEstatisticasExcel() {
  const ano = document.getElementById('statAnoFiltro')?.value || '2026';
  const periodo = document.getElementById('statPeriodoFiltro')?.value || 'GLOBAL';
  downloadFicheiroBinario(`/api/v1/pautas/estatisticas-gerais/xlsx?anoLetivo=${ano}&periodo=${periodo}`, `Estatisticas_Aproveitamento_${ano}.xlsx`);
}

