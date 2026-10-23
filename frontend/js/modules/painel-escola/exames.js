// =====================================================================
// SIGE - Módulo Exames | Pautas Oficiais de Exame (MEC / Moçambique)
// Modelagem e Cálculo Estrito: Dados reais das pautas de frequência,
// lançamento de notas de 1ª e 2ª época, janela de parâmetros (pesos e nota mínima),
// e integração com Certificados e Declarações.
// =====================================================================

window._sigePautaExamesData = null;
window._sigeNotasExameModificadas = new Map();

async function carregarExames() {
  const container = document.getElementById('view-exames');
  if (!container) return;

  // Actualizar imediatamente o cabeçalho oficial com a instituição ativa
  try {
    const escInit = window.state?.tenant || {};
    const escNomeInit = (escInit.nome || 'Escola Secundária de Massinga').toUpperCase();
    const provNomeInit = (escInit.provincia || 'Inhambane').toUpperCase();
    const distNomeInit = (escInit.distrito || 'Massinga').toUpperCase();

    const elEscInit = document.getElementById('pautaExameEscolaNome');
    if (elEscInit) elEscInit.textContent = escNomeInit;
    const elProvInit = document.getElementById('pautaExameProvincia');
    if (elProvInit) elProvInit.textContent = provNomeInit;
    const elDistInit = document.getElementById('pautaExameDistrito');
    if (elDistInit) elDistInit.textContent = distNomeInit;
    const elLogoInit = document.getElementById('pautaExameLogoImg');
    if (elLogoInit && escInit.logo) elLogoInit.src = escInit.logo;
  } catch (_) {}

  // Carregar e sincronizar parâmetros de exame ativos
  try {
    const resParam = await apiFetch('/api/v1/pautas/exames/parametros');
    if (resParam && resParam.success && resParam.parametros) {
      atualizarCamposParametrosExameNaInterface(resParam.parametros);
    }
  } catch (_) {}

  try {
    // 1. Obter classes com regime de exame configurado
    let classesComExame = new Set(['10ª Classe', '12ª Classe']);
    try {
      const resCfg = await apiFetch('/api/v1/escola-admin/classes-exames');
      if (resCfg && resCfg.success && Array.isArray(resCfg.data)) {
        resCfg.data.forEach(item => {
          if (item.tem_exame) {
            classesComExame.add(item.nome);
          }
        });
      }
    } catch (_) {}

    // 2. Obter todas as turmas da instituição
    const resTurmas = await apiFetch('/api/v1/escola-admin/turmas');
    const selectClasse = document.getElementById('exameClasseFilter');
    const selectTurma = document.getElementById('exameTurmaSelect');
    if (!selectClasse || !selectTurma) return;

    if (resTurmas && resTurmas.success && Array.isArray(resTurmas.data)) {
      // Filtrar apenas turmas de classes com regime de exame
      const turmasComExame = resTurmas.data.filter(t => {
        const grau = (t.grau_ano || '').trim();
        const eh10ou12 = /(^|[^\d])(10|12)([ªaº\.\s]|$)/i.test(grau);
        const estaConfigurada = classesComExame.has(grau) || Array.from(classesComExame).some(c => grau.toLowerCase().includes(c.toLowerCase()));
        return eh10ou12 || estaConfigurada || Boolean(t.tem_exame);
      });

      window._sigeTurmasExamesLista = turmasComExame;

      // Extrair classes únicas das turmas com exame
      const classesUnicas = Array.from(new Set(turmasComExame.map(t => t.grau_ano))).filter(Boolean);

      if (classesUnicas.length > 0) {
        selectClasse.innerHTML = classesUnicas.map(c => 
          `<option value="${c}">${c}</option>`
        ).join('');
      } else {
        selectClasse.innerHTML = '<option value="">Sem classes com exame cadastradas</option>';
      }

      filtrarTurmasExamesPorClasse();
    } else {
      selectClasse.innerHTML = '<option value="">Erro ao carregar turmas</option>';
      selectTurma.innerHTML = '<option value="">Nenhuma turma disponível</option>';
    }
  } catch (err) {
    console.error('Erro ao inicializar módulo de exames:', err);
    mostrarToast('Erro ao carregar módulo de exames.', 'danger');
  }
}

function filtrarTurmasExamesPorClasse() {
  const classeSel = document.getElementById('exameClasseFilter')?.value;
  const selectTurma = document.getElementById('exameTurmaSelect');
  if (!selectTurma) return;

  const turmas = window._sigeTurmasExamesLista || [];
  const filtradas = classeSel ? turmas.filter(t => t.grau_ano === classeSel) : turmas;

  if (filtradas.length > 0) {
    selectTurma.innerHTML = filtradas.map(t => {
      const area = t.area && !['geral', 'ensino geral', 'tronco comum'].includes(t.area.toLowerCase()) ? ` (${t.area})` : '';
      return `<option value="${t.id}">${t.grau_ano} &rarr; ${t.nome}${area}</option>`;
    }).join('');
    carregarPautaExamesTurma();
  } else {
    selectTurma.innerHTML = '<option value="">Nenhuma turma encontrada para esta classe</option>';
    document.getElementById('containerTabelaPautaExames').innerHTML = `
      <div class="alert alert-warning text-center my-4">
        <i class="bi bi-exclamation-triangle-fill me-2"></i>
        Nenhuma turma com regime de exame registada para a classe selecionada.
      </div>
    `;
    const rodape = document.getElementById('pautaExameRodapeOficial');
    if (rodape) rodape.classList.add('d-none');
  }
}

async function carregarPautaExamesTurma() {
  const turmaId = document.getElementById('exameTurmaSelect')?.value;
  const anoSelect = document.getElementById('exameAnoSelect');
  const anoLetivo = anoSelect?.value || (window.state?.tenant?.ano_letivo_ativo || '2026');
  const container = document.getElementById('containerTabelaPautaExames');
  if (!turmaId || !container) return;

  container.innerHTML = `
    <div class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="small text-muted mt-2">A carregar pauta oficial de exames e a sincronizar com pautas de frequência...</p>
    </div>
  `;

  try {
    const res = await apiFetch(`/api/v1/pautas/exames/turma/${turmaId}?anoLetivo=${anoLetivo}`);
    if (!res || !res.success) {
      container.innerHTML = `
        <div class="alert alert-danger text-center my-4">
          <i class="bi bi-x-circle-fill me-2"></i>
          ${res?.message || 'Não foi possível carregar a pauta de exames para esta turma.'}
        </div>
      `;
      return;
    }

    const d = res.data || res;
    window._sigePautaExamesData = d;
    if (!window._sigeNotasExameModificadas) {
      window._sigeNotasExameModificadas = new Map();
    }
    window._sigeNotasExameModificadas.clear();

    // Actualizar Cabeçalhos Oficiais Moçambique
    const escData = d.escola || window.state?.tenant || {};
    const escNome = (escData.nome || 'Escola Secundária de Massinga').toUpperCase();
    const provNome = (escData.provincia || 'Inhambane').toUpperCase();
    const distNome = (escData.distrito || 'Massinga').toUpperCase();

    const elEsc = document.getElementById('pautaExameEscolaNome');
    if (elEsc) elEsc.textContent = escNome;
    const elProv = document.getElementById('pautaExameProvincia');
    if (elProv) elProv.textContent = provNome;
    const elDist = document.getElementById('pautaExameDistrito');
    if (elDist) elDist.textContent = distNome;

    const elLogo = document.getElementById('pautaExameLogoImg');
    if (elLogo && escData.logo) elLogo.src = escData.logo;

    const grau = d.turma?.grau_ano || '10ª Classe';
    const area = d.turma?.area ? ` / ${d.turma.area}` : '';
    const elClasse = document.getElementById('pautaExameClasseArea');
    if (elClasse) elClasse.textContent = `Classe / Área ou Secção: ${grau}${area}`;

    const elAno = document.getElementById('pautaExameTituloAno');
    if (elAno) elAno.textContent = `PAUTA DE EXAMES / Ano ${anoLetivo}`;

    const elTurmaBadge = document.getElementById('pautaExameTurmaBadge');
    if (elTurmaBadge) elTurmaBadge.textContent = `Turma: ${d.turma?.nome || ''}`;

    const badgeTotal = document.getElementById('badgeTotalCandidatosExame');
    if (badgeTotal) badgeTotal.textContent = `${(d.alunos || []).length} Candidatos`;

    if (d.parametros) {
      atualizarCamposParametrosExameNaInterface(d.parametros);
    }

    renderizarTabelaExamesHtml(d);
  } catch (err) {
    console.error('Erro ao carregar pauta de exames:', err);
    const msg = err?.message || 'Erro de comunicação ao carregar pauta de exames.';
    const safeMsg = typeof escapeHtml === 'function' ? escapeHtml(msg) : msg;
    container.innerHTML = `
      <div class="alert alert-danger text-center my-4 py-3">
        <i class="bi bi-exclamation-triangle-fill fs-4 text-danger d-block mb-2"></i>
        <div class="fw-bold mb-1">${safeMsg}</div>
        <p class="small text-muted mb-3">Não foi possível carregar a pauta de exames desta turma.</p>
        <button type="button" class="btn btn-sm btn-outline-danger" onclick="carregarPautaExamesTurma()">
          <i class="bi bi-arrow-clockwise me-1"></i> Tentar Novamente
        </button>
      </div>
    `;
  }
}

function renderizarTabelaExamesHtml(d) {
  const container = document.getElementById('containerTabelaPautaExames');
  if (!container) return;

  const podeEditar = d.pode_editar !== false;
  const motivoBloqueio = d.motivo_bloqueio || '';

  // Gerir exibição do aviso de permissão de lançamento e estado do botão de salvar
  const elAviso = document.getElementById('avisoBloqueioLancamentoExame');
  const elTextoBloqueio = document.getElementById('textoBloqueioLancamentoExame');
  const btnSalvar = document.getElementById('btnSalvarNotasExame');
  const btnProf = document.getElementById('btnProfessoresExame');

  // Botão de autorizar professores visível apenas para Direcção / DAP
  const userRole = (window.state?.user?.role || '').toUpperCase();
  const isGestao = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'].includes(userRole) || !userRole;
  if (btnProf) {
    if (isGestao) btnProf.classList.remove('d-none');
    else btnProf.classList.add('d-none');
  }

  if (elAviso && elTextoBloqueio) {
    if (!podeEditar) {
      elAviso.classList.remove('d-none');
      elTextoBloqueio.textContent = motivoBloqueio || 'O lançamento das notas de exame nesta classe está reservado ao Director Pedagógico ou professores autorizados.';
      if (btnSalvar) {
        btnSalvar.setAttribute('disabled', 'true');
        btnSalvar.classList.add('opacity-50');
      }
    } else {
      elAviso.classList.add('d-none');
      if (btnSalvar) {
        btnSalvar.removeAttribute('disabled');
        btnSalvar.classList.remove('opacity-50');
      }
    }
  }

  const disciplinasComExame = d.disciplinas_com_exame || [];
  const disciplinasSemExame = d.disciplinas_sem_exame || [];
  const alunos = d.alunos || [];
  const params = d.parametros || { peso_frequencia: 50, peso_exame: 50, nota_minima_exame: 10 };
  const notaMinima = Number(params.nota_minima_exame || 10);

  if (alunos.length === 0) {
    container.innerHTML = `
      <div class="alert alert-info text-center my-4 py-3">
        <i class="bi bi-info-circle-fill fs-4 text-info d-block mb-2"></i>
        <div class="fw-semibold">Não existem alunos matriculados ativos nesta turma de exame.</div>
        <small class="text-muted">Selecione outra turma no filtro acima para visualizar e lançar notas de exame.</small>
      </div>
    `;
    const rodape = document.getElementById('pautaExameRodapeOficial');
    if (rodape) rodape.classList.add('d-none');
    return;
  }

  if (disciplinasComExame.length === 0 && disciplinasSemExame.length === 0) {
    container.innerHTML = `
      <div class="alert alert-warning text-center my-4 py-3">
        <i class="bi bi-exclamation-triangle-fill fs-4 text-warning d-block mb-2"></i>
        <div class="fw-semibold">Não foram encontradas disciplinas do plano curricular associadas à área desta turma.</div>
        <small class="text-muted">Classe: ${d.turma?.grau_ano || ''} | Área: ${d.turma?.area || 'Geral'}</small>
      </div>
    `;
    const rodape = document.getElementById('pautaExameRodapeOficial');
    if (rodape) rodape.classList.add('d-none');
    return;
  }

  // Montar Cabeçalhos da Tabela Fiel ao Modelo MEC (Ajuste Fino ao Conteúdo)
  let thLinha1 = `
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-nowrap px-2" style="font-size: 0.72rem;">Nº</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-nowrap px-2" style="font-size: 0.72rem;">Nº Candidato</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-start ps-2 text-nowrap px-3" style="font-size: 0.75rem;">Nome do Aluno</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-nowrap px-1" style="font-size: 0.72rem;">Gén.</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-nowrap px-2" style="font-size: 0.72rem;">Turma</th>
  `;

  // Disciplinas com exame: 4 colunas cada (sem min-width artificial)
  disciplinasComExame.forEach(disc => {
    thLinha1 += `<th colspan="4" class="text-center bg-primary bg-opacity-10 text-primary fw-bold border-start border-end text-nowrap px-2" style="font-size: 0.75rem;">${disc.nome}</th>`;
  });

  // Disciplinas sem exame: 1 coluna cada
  disciplinasSemExame.forEach(disc => {
    thLinha1 += `<th rowspan="2" class="text-center bg-light text-dark fw-bold border-start border-end text-nowrap px-2" style="font-size: 0.72rem;">${disc.nome}</th>`;
  });

  // RESULTADO FINAL: 3 colunas
  thLinha1 += `<th colspan="3" class="text-center bg-dark text-white fw-bold border-start text-nowrap px-2" style="font-size: 0.75rem;">RESULTADO FINAL</th>`;

  // Linha 2 do cabeçalho
  let thLinha2 = '';
  disciplinasComExame.forEach(() => {
    thLinha2 += `
      <th rowspan="2" class="bg-light text-dark fw-bold border-end align-middle text-nowrap px-1" style="font-size: 0.68rem;">Freq.</th>
      <th colspan="2" class="bg-warning bg-opacity-25 text-dark fw-bold border-end text-nowrap px-1" style="font-size: 0.68rem;">Exame</th>
      <th rowspan="2" class="bg-primary bg-opacity-10 text-primary fw-bold border-end align-middle text-nowrap px-1" style="font-size: 0.68rem;">Média</th>
    `;
  });

  thLinha2 += `
    <th rowspan="2" class="bg-secondary bg-opacity-10 text-dark fw-bold border-end text-nowrap px-2" style="font-size: 0.72rem;">Resultado</th>
    <th rowspan="2" class="bg-secondary bg-opacity-10 text-dark fw-bold border-end text-nowrap px-1" style="font-size: 0.72rem;">MF</th>
    <th rowspan="2" class="bg-secondary bg-opacity-10 text-dark fw-bold text-start ps-2 text-nowrap px-2" style="font-size: 0.72rem;">Disciplina(s) com Negativa</th>
  `;

  // Linha 3 do cabeçalho
  let thLinha3 = '';
  disciplinasComExame.forEach(() => {
    thLinha3 += `
      <th class="bg-warning bg-opacity-10 text-dark fw-bold border-end text-nowrap p-0" style="font-size: 0.65rem; width: 44px; min-width: 44px; max-width: 44px;">1ª</th>
      <th class="bg-warning bg-opacity-10 text-dark fw-bold border-end text-nowrap p-0" style="font-size: 0.65rem; width: 44px; min-width: 44px; max-width: 44px;">2ª</th>
    `;
  });

  disciplinasSemExame.forEach(() => {
    thLinha3 += `<th class="bg-light text-muted border-end text-nowrap px-1" style="font-size: 0.65rem;">Freq.</th>`;
  });

  // Linhas dos Alunos
  let trsCorpo = '';
  alunos.forEach((aluno, idx) => {
    const discMap = aluno.disciplinas || {};
    const resFinal = aluno.resultado_final || {};
    const sufixoGen = (aluno.genero || 'M').toUpperCase().startsWith('F') ? 'a' : 'o';

    let tdsDiscs = '';

    // Disciplinas com exame
    disciplinasComExame.forEach(d => {
      const dData = discMap[d.id] || {};
      const vFreq = dData.frequencia !== undefined && dData.frequencia !== null ? dData.frequencia : '-';
      const e1Val = dData.exame_1epoca !== null && dData.exame_1epoca !== undefined ? dData.exame_1epoca : '';
      const e2Val = dData.exame_2epoca !== null && dData.exame_2epoca !== undefined ? dData.exame_2epoca : '';
      const vMed = dData.media !== undefined && dData.media !== null ? dData.media : '-';

      const temE1 = e1Val !== '' && !isNaN(Number(e1Val));
      const aprovou1e = temE1 && Number(e1Val) >= notaMinima;
      const pode2e = temE1 && Number(e1Val) < notaMinima;

      let estiloE1 = 'background: transparent;';
      let estiloE2 = 'background: transparent;';
      let titleE2 = 'Nota da 2ª época (se necessária)';

      if (aprovou1e) {
        estiloE1 = 'background: #dcfce7; font-weight: bold; color: #166534;';
        estiloE2 = 'background: #f1f5f9; color: #94a3b8; cursor: not-allowed;';
        titleE2 = `Aluno já aprovado na 1ª época (${e1Val} ≥ ${notaMinima})`;
      } else if (pode2e) {
        estiloE1 = 'background: #fee2e2; color: #991b1b;';
        estiloE2 = 'background: #fef3c7; border: 1px dashed #f59e0b !important; font-weight: bold;';
        titleE2 = `Não atingiu nota mínima (${e1Val} < ${notaMinima}). Elegível para a 2ª época!`;
      }

      const corMed = (typeof vMed === 'number' || (!isNaN(Number(vMed)) && vMed !== '-')) 
        ? (Number(vMed) >= 9.5 ? 'text-success fw-bold' : 'text-danger fw-bold') 
        : (vMed === '2ª Época' ? 'text-warning fw-bold' : 'text-muted');

      tdsDiscs += `
        <td class="text-center bg-light border-end font-monospace small text-nowrap px-2">${vFreq}</td>
        <td class="p-1 text-center border-end align-middle text-nowrap" style="width: 44px; min-width: 44px; max-width: 44px;">
          <input type="number" step="0.01" min="0" max="20" class="form-control form-control-sm text-center p-0 font-monospace input-exame-nota shadow-none"
            value="${e1Val}" placeholder="-" data-aluno="${aluno.id}" data-disc="${d.id}" data-epoca="1"
            ${!podeEditar ? 'disabled readonly' : ''}
            onchange="aoMudarNotaExame(this)" oninput="aoMudarNotaExame(this)"
            style="width: 40px; height: 26px; font-size: 0.8rem; border: 1px solid #cbd5e1; ${!podeEditar ? 'background: #f8fafc; cursor: not-allowed;' : 'background: #ffffff;'}"
            title="${!podeEditar ? 'Lançamento reservado ao Director Pedagógico ou professores autorizados' : `1ª Época: Mínimo ${notaMinima} valores para aprovação`}">
        </td>
        <td class="p-1 text-center border-end align-middle text-nowrap" style="width: 44px; min-width: 44px; max-width: 44px;">
          <input type="number" step="0.01" min="0" max="20" class="form-control form-control-sm text-center p-0 font-monospace input-exame-nota shadow-none"
            value="${e2Val}" placeholder="-" data-aluno="${aluno.id}" data-disc="${d.id}" data-epoca="2"
            ${!podeEditar ? 'disabled readonly' : ''}
            onchange="aoMudarNotaExame(this)" oninput="aoMudarNotaExame(this)"
            style="width: 40px; height: 26px; font-size: 0.8rem; border: 1px solid #cbd5e1; ${!podeEditar ? 'background: #f8fafc; cursor: not-allowed;' : 'background: #ffffff;'}"
            title="${!podeEditar ? 'Lançamento reservado ao Director Pedagógico ou professores autorizados' : `2ª Época: Mínimo ${notaMinima} valores para aprovação`}">
        </td>
        <td class="text-center border-end font-monospace small text-nowrap px-2 ${corMed}" id="media_${aluno.id}_${d.id}">
          ${vMed}
        </td>
      `;
    });

    // Disciplinas sem exame
    disciplinasSemExame.forEach(d => {
      const dData = discMap[d.id] || {};
      const vFreq = dData.frequencia !== undefined && dData.frequencia !== null ? dData.frequencia : '-';
      const corFreq = (typeof vFreq === 'number' || (!isNaN(Number(vFreq)) && vFreq !== '-')) 
        ? (Number(vFreq) >= 9.5 ? 'text-success' : 'text-danger') 
        : 'text-muted';
      tdsDiscs += `
        <td class="text-center border-end font-monospace small text-nowrap px-2 ${corFreq}">${vFreq}</td>
      `;
    });

    // Resultado Final do Aluno: Aprovado a preto e Reprovado a vermelho (sem pintar fundo)
    const rawRes = String(resFinal.aprovado || resFinal.resultado || `Reprovad${sufixoGen}`).trim();
    const resAprov = rawRes.includes('Aprovad') ? `Aprovad${sufixoGen}` : `Reprovad${sufixoGen}`;
    const corResClass = resAprov.includes('Aprovad') ? 'text-dark fw-bold' : 'text-danger fw-bold';
    const corResStyle = resAprov.includes('Aprovad') ? 'color: #000000; font-weight: bold;' : 'color: #dc2626; font-weight: bold;';

    const mfVal = resFinal.mf !== undefined && resFinal.mf !== null ? resFinal.mf : 0;
    const discRep = resFinal.disciplinas_reprovou || '---';

    trsCorpo += `
      <tr id="linha_aluno_${aluno.id}">
        <td class="text-center font-monospace text-muted small border-end align-middle text-nowrap px-2">${aluno.numero || idx + 1}</td>
        <td class="text-center font-monospace small border-end fw-semibold text-secondary align-middle text-nowrap px-2">${aluno.candidato || aluno.matricula}</td>
        <td class="text-start ps-2 text-dark fw-bold border-end small text-nowrap align-middle px-3">${aluno.nome}</td>
        <td class="text-center font-monospace small border-end align-middle text-nowrap px-2">${aluno.genero}</td>
        <td class="text-center small border-end text-muted align-middle text-nowrap px-2">${aluno.turma}</td>
        ${tdsDiscs}
        <td class="text-center border-end align-middle text-nowrap px-2">
          <span id="res_aluno_${aluno.id}" class="${corResClass}" style="font-size: 0.82rem; ${corResStyle}">${resAprov}</span>
        </td>
        <td class="text-center font-monospace fw-bold border-end align-middle text-nowrap px-2" id="mf_aluno_${aluno.id}" style="font-size: 0.82rem;">
          ${mfVal}
        </td>
        <td class="text-start ps-2 small text-danger font-monospace align-middle text-nowrap px-3" id="rep_aluno_${aluno.id}" style="font-size: 0.72rem;">
          ${discRep}
        </td>
      </tr>
    `;
  });

  const htmlTabela = `
    <table class="table table-bordered table-sm align-middle text-center sige-tabela-exames mb-0 border" style="font-size: 0.78rem; width: max-content !important; margin: 0 auto !important; border-collapse: collapse;">
      <thead>
        <tr class="align-middle">${thLinha1}</tr>
        <tr class="align-middle">${thLinha2}</tr>
        <tr class="align-middle">${thLinha3}</tr>
      </thead>
      <tbody>
        ${trsCorpo}
      </tbody>
    </table>
  `;

  container.innerHTML = htmlTabela;

  // Renderizar Rodapé Oficial com Resumo e Assinaturas
  const rodape = document.getElementById('pautaExameRodapeOficial');
  const boxEstat = document.getElementById('pautaExameEstatisticasBox');
  if (rodape && boxEstat) {
    const estat = d.estatisticas || {};
    const tot = estat.total || alunos.length;
    const aprov = estat.aprovados || 0;
    const rep = estat.reprovados || 0;
    const adm = estat.admitidos || 0;
    const seg = estat.segunda_epoca || 0;
    const taxa = estat.taxa_aprovacao || 0.0;

    boxEstat.innerHTML = `
      <div><strong>Total de Candidatos:</strong> <span class="badge bg-secondary ms-1">${tot}</span> (H: ${estat.homens || 0} | M: ${estat.mulheres || 0})</div>
      <div><strong>Aprovados:</strong> <span class="badge bg-success ms-1">${aprov}</span></div>
      <div><strong>2ª Época:</strong> <span class="badge bg-warning text-dark ms-1">${seg}</span></div>
      <div><strong>Reprovados:</strong> <span class="badge bg-danger ms-1">${rep}</span></div>
      <div><strong>Admitidos ao Exame:</strong> <span class="badge bg-primary ms-1">${adm}</span></div>
      <div><strong>Taxa de Aprovação:</strong> <span class="badge bg-dark ms-1">${taxa}%</span></div>
    `;

    const elDt = document.getElementById('pautaExameAssinaturaDT');
    if (elDt) elDt.textContent = d.turma?.director_turma || 'Director de Turma';

    const elDap = document.getElementById('pautaExameAssinaturaDAP');
    if (elDap) elDap.textContent = window.state?.tenant?.dap_nome || 'Direcção Pedagógica';

    const elDir = document.getElementById('pautaExameAssinaturaDir');
    if (elDir) elDir.textContent = window.state?.tenant?.director_nome || 'Director da Escola';

    rodape.classList.remove('d-none');
  }
}

function aoMudarNotaExame(inputEl) {
  const alunoId = inputEl.getAttribute('data-aluno');
  const discId = inputEl.getAttribute('data-disc');
  const epoca = inputEl.getAttribute('data-epoca');
  let valStr = inputEl.value.trim().replace(',', '.');
  let valNum = null;

  if (valStr !== '' && !isNaN(Number(valStr))) {
    valNum = Math.max(0, Math.min(20, Number(valStr)));
    valNum = Math.round(valNum * 100) / 100; // Inteiros ou decimais com 1 ou 2 casas decimais em [0, 20]
    inputEl.value = valNum;
  } else {
    inputEl.value = '';
  }

  const chave = `${alunoId}_${discId}`;
  if (!window._sigeNotasExameModificadas.has(chave)) {
    window._sigeNotasExameModificadas.set(chave, { aluno_id: alunoId, disciplina_id: discId });
  }
  const obj = window._sigeNotasExameModificadas.get(chave);
  if (epoca === '1') obj.exame_1epoca = valNum;
  if (epoca === '2') obj.exame_2epoca = valNum;

  // Recalcular dinamicamente Média da Disciplina e Resultado do Aluno na interface
  recalcularLinhaAlunoInterface(alunoId);

  // Destacar botão de salvar com indicação visual de alteração pendente
  const btnSalvar = document.getElementById('btnSalvarNotasExame');
  if (btnSalvar) {
    btnSalvar.classList.add('btn-warning');
    btnSalvar.classList.remove('btn-primary');
    btnSalvar.innerHTML = `<i class="bi bi-floppy-fill me-1"></i> Guardar Alterações (${window._sigeNotasExameModificadas.size})`;
  }
}

function recalcularLinhaAlunoInterface(alunoId) {
  if (!window._sigePautaExamesData) return;
  const d = window._sigePautaExamesData;
  const aluno = (d.alunos || []).find(a => a.id === alunoId);
  if (!aluno) return;

  const params = d.parametros || { peso_frequencia: 50, peso_exame: 50, nota_minima_exame: 10 };
  const pesoFreq = Number(params.peso_frequencia || 50);
  const pesoExame = Number(params.peso_exame || 50);
  const notaMinima = Number(params.nota_minima_exame || 10);

  const disciplinasComExame = d.disciplinas_com_exame || [];
  const disciplinasSemExame = d.disciplinas_sem_exame || [];
  const grauAno = d.turma?.grau_ano || '10ª Classe';
  const is12a = /(^|[^\d])12([ªaº\.\s]|$)/i.test(grauAno);
  const sufixoGen = (aluno.genero || 'M').toUpperCase().startsWith('F') ? 'a' : 'o';

  const notasFinais = [];
  const discReprovadas = [];
  let temAlgumExame = false;
  let alunoTem2ePendente = false;

  disciplinasComExame.forEach(disc => {
    const dId = disc.id;
    const dData = aluno.disciplinas?.[dId] || {};
    const chave = `${alunoId}_${dId}`;
    const mod = window._sigeNotasExameModificadas.get(chave);

    const e1 = mod && mod.exame_1epoca !== undefined ? mod.exame_1epoca : dData.exame_1epoca;
    const e2 = mod && mod.exame_2epoca !== undefined ? mod.exame_2epoca : dData.exame_2epoca;

    const e1Num = (e1 !== null && e1 !== undefined && e1 !== '') ? Number(e1) : null;
    const e2Num = (e2 !== null && e2 !== undefined && e2 !== '') ? Number(e2) : null;

    if (e1Num !== null || e2Num !== null) {
      temAlgumExame = true;
    }

    let neEfetivo = null;
    let discEm2e = false;

    if (e1Num !== null && e1Num >= notaMinima) {
      // Passou logo na 1ª época!
      neEfetivo = e1Num;
    } else if (e1Num !== null && e1Num < notaMinima) {
      // Não passou na 1ª época -> tem direito à 2ª época
      if (e2Num !== null) {
        neEfetivo = e2Num;
      } else {
        // Aguarda 2ª época
        discEm2e = true;
        alunoTem2ePendente = true;
      }
    } else if (e1Num === null && e2Num !== null) {
      neEfetivo = e2Num;
    }

    const freqVal = typeof dData.frequencia_decimal === 'number' ? dData.frequencia_decimal : (typeof dData.frequencia === 'number' ? dData.frequencia : null);
    let mediaFinalDisc = null;

    if (neEfetivo !== null) {
      if (freqVal !== null) {
        mediaFinalDisc = Math.round((freqVal * (pesoFreq / 100)) + (neEfetivo * (pesoExame / 100)));
      } else {
        mediaFinalDisc = Math.round(neEfetivo);
      }
    } else {
      // REGRA SOLICITADA: Se não tem nota num dos exames (1ª ou 2ª) então a Média nessa disciplina é 0
      mediaFinalDisc = 0;
    }

    const elMedia = document.getElementById(`media_${alunoId}_${dId}`);
    if (elMedia) {
      elMedia.textContent = mediaFinalDisc;
      elMedia.className = `text-center border-end font-monospace small align-middle ${mediaFinalDisc >= 9.5 ? 'text-success fw-bold' : 'text-danger fw-bold'}`;
    }

    notasFinais.push(mediaFinalDisc);
    if (mediaFinalDisc < 9.5) {
      discReprovadas.push(disc.nome);
    }
  });

  disciplinasSemExame.forEach(disc => {
    const dData = aluno.disciplinas?.[disc.id] || {};
    const fVal = typeof dData.frequencia === 'number' ? dData.frequencia : 0;
    notasFinais.push(fVal);
    if (fVal < 9.5) discReprovadas.push(disc.nome);
  });

  // Atualizar Resultado Final: 'Aprovado' se todas positivas e MF >= 9.5, caso contrário 'Reprovado'
  let resAprov = `Reprovad${sufixoGen}`;
  let mfGlobal = 0;

  if (notasFinais.length > 0) {
    const soma = notasFinais.reduce((acc, v) => acc + v, 0);
    mfGlobal = Math.round(soma / notasFinais.length);

    const aprovadoGeral = (discReprovadas.length === 0 && mfGlobal >= 9.5);
    resAprov = aprovadoGeral ? `Aprovad${sufixoGen}` : `Reprovad${sufixoGen}`;
  }

  const elRes = document.getElementById(`res_aluno_${alunoId}`);
  if (elRes) {
    elRes.textContent = resAprov;
    // Sem pintar: 'Aprovado' a preto e 'Reprovado' a vermelho
    if (resAprov.includes('Aprovad')) {
      elRes.className = 'text-dark fw-bold';
      elRes.style.color = '#000000';
    } else {
      elRes.className = 'text-danger fw-bold';
      elRes.style.color = '#dc2626';
    }
    elRes.style.background = 'transparent';
  }

  const elMf = document.getElementById(`mf_aluno_${alunoId}`);
  if (elMf) elMf.textContent = mfGlobal;

  const elRep = document.getElementById(`rep_aluno_${alunoId}`);
  if (elRep) elRep.textContent = discReprovadas.length > 0 ? discReprovadas.join(', ') : '---';
}

// Janela & Parâmetros Oficiais de Avaliação de Exame (MEC)
function atualizarCamposParametrosExameNaInterface(p) {
  if (!p) return;
  const pf = p.peso_frequencia !== undefined ? Number(p.peso_frequencia) : 50;
  const pe = p.peso_exame !== undefined ? Number(p.peso_exame) : 50;
  const nm = p.nota_minima_exame !== undefined ? Number(p.nota_minima_exame) : 10.0;

  // Atualizar inputs da janela inline
  const inpInFreq = document.getElementById('inlineParamPesoFreq');
  const inpInEx = document.getElementById('inlineParamPesoExame');
  const inpInMin = document.getElementById('inlineParamNotaMinima');
  if (inpInFreq) inpInFreq.value = pf;
  if (inpInEx) inpInEx.value = pe;
  if (inpInMin) inpInMin.value = nm;

  // Atualizar inputs do modal flutuante
  const inpModFreq = document.getElementById('inputParamPesoFreq');
  const inpModEx = document.getElementById('inputParamPesoExame');
  const inpModMin = document.getElementById('inputParamNotaMinima');
  if (inpModFreq) inpModFreq.value = pf;
  if (inpModEx) inpModEx.value = pe;
  if (inpModMin) inpModMin.value = nm;

  // Atualizar fórmulas visuais
  const lblF = document.getElementById('labelFormulaFreq');
  const lblE = document.getElementById('labelFormulaExame');
  if (lblF) lblF.textContent = `${pf}%`;
  if (lblE) lblE.textContent = `${pe}%`;

  // Atualizar badges
  const badgeParam = document.getElementById('badgeParametrosAtivos');
  if (badgeParam) badgeParam.textContent = `Freq: ${pf}% | Exame: ${pe}% | Mín: ${nm}`;

  const badgeClasse = document.getElementById('classeExameBadgeParametros');
  if (badgeClasse) badgeClasse.textContent = `Freq: ${pf}% | Exame: ${pe}% | Nota Mínima: ${nm}`;

  verificarAlertaPesos(pf, pe);
}

function alternarJanelaParametrosExame() {
  abrirModalParametrosExame();
}

async function abrirModalParametrosExame() {
  const modalEl = document.getElementById('modalParametrosExame');
  if (!modalEl) return;

  try {
    const res = await apiFetch('/api/v1/pautas/exames/parametros');
    if (res && res.success && res.parametros) {
      atualizarCamposParametrosExameNaInterface(res.parametros);
    }
  } catch (err) {
    console.warn('Erro ao carregar parâmetros de exame:', err);
  }

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
}

function aoMudarPesoFrequencia(val) {
  const num = Math.max(0, Math.min(100, Number(val) || 0));
  const comp = 100 - num;
  const inpEx = document.getElementById('inputParamPesoExame');
  if (inpEx) inpEx.value = comp;

  // Sincronizar com inline
  const inpInFreq = document.getElementById('inlineParamPesoFreq');
  const inpInEx = document.getElementById('inlineParamPesoExame');
  if (inpInFreq) inpInFreq.value = num;
  if (inpInEx) inpInEx.value = comp;

  const lblF = document.getElementById('labelFormulaFreq');
  const lblE = document.getElementById('labelFormulaExame');
  if (lblF) lblF.textContent = `${num}%`;
  if (lblE) lblE.textContent = `${comp}%`;

  verificarAlertaPesos(num, comp);
}

function aoMudarPesoExame(val) {
  const num = Math.max(0, Math.min(100, Number(val) || 0));
  const comp = 100 - num;
  const inpFreq = document.getElementById('inputParamPesoFreq');
  if (inpFreq) inpFreq.value = comp;

  // Sincronizar com inline
  const inpInFreq = document.getElementById('inlineParamPesoFreq');
  const inpInEx = document.getElementById('inlineParamPesoExame');
  if (inpInFreq) inpInFreq.value = comp;
  if (inpInEx) inpInEx.value = num;

  const lblF = document.getElementById('labelFormulaFreq');
  const lblE = document.getElementById('labelFormulaExame');
  if (lblF) lblF.textContent = `${comp}%`;
  if (lblE) lblE.textContent = `${num}%`;

  verificarAlertaPesos(comp, num);
}

function aoMudarPesoFrequenciaInline(val) {
  aoMudarPesoFrequencia(val);
}

function aoMudarPesoExameInline(val) {
  aoMudarPesoExame(val);
}

function verificarAlertaPesos(pf, pe) {
  const alertaModal = document.getElementById('alertaSomaPesos');
  const alertaInline = document.getElementById('alertaSomaPesosInline');
  const badgeSoma = document.getElementById('badgeStatusSomaPesos');

  const valido = Math.round(pf + pe) === 100;
  if (!valido) {
    if (alertaModal) alertaModal.classList.remove('d-none');
    if (alertaInline) alertaInline.classList.remove('d-none');
    if (badgeSoma) {
      badgeSoma.className = 'badge bg-danger px-2 py-1';
      badgeSoma.textContent = `Soma: ${Math.round(pf + pe)}% (Inválido)`;
    }
  } else {
    if (alertaModal) alertaModal.classList.add('d-none');
    if (alertaInline) alertaInline.classList.add('d-none');
    if (badgeSoma) {
      badgeSoma.className = 'badge bg-success px-2 py-1';
      badgeSoma.textContent = 'Soma: 100% OK';
    }
  }
}

async function reporParametrosExamePadraoMEC() {
  const pPadrao = { peso_frequencia: 50, peso_exame: 50, nota_minima_exame: 10.0 };
  atualizarCamposParametrosExameNaInterface(pPadrao);
  await salvarParametrosExame();
}

async function salvarParametrosExame() {
  const inpFreq = document.getElementById('inputParamPesoFreq');
  const inpEx = document.getElementById('inputParamPesoExame');
  const inpMin = document.getElementById('inputParamNotaMinima');

  const pf = Number(inpFreq?.value || 50);
  const pe = Number(inpEx?.value || 50);
  const nm = Number(inpMin?.value || 10);

  if (isNaN(pf) || isNaN(pe) || isNaN(nm)) {
    mostrarToast('Preencha valores numéricos válidos.', 'warning');
    return;
  }

  if (Math.round(pf + pe) !== 100) {
    mostrarToast('A soma da percentagem de frequência e exame deve ser exatamente 100%.', 'danger');
    return;
  }

  if (nm < 0 || nm > 20) {
    mostrarToast('A nota mínima do exame deve estar entre 0 e 20 valores.', 'danger');
    return;
  }

  try {
    const res = await apiFetch('/api/v1/pautas/exames/parametros/', {
      method: 'POST',
      body: JSON.stringify({
        peso_frequencia: pf,
        peso_exame: pe,
        nota_minima_exame: nm
      })
    });

    if (res && res.success) {
      mostrarToast(res.message || 'Parâmetros de exame configurados com sucesso!', 'success');
      const modalEl = document.getElementById('modalParametrosExame');
      if (modalEl) {
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
      }
      atualizarCamposParametrosExameNaInterface({
        peso_frequencia: pf,
        peso_exame: pe,
        nota_minima_exame: nm
      });

      // Recarregar pauta de exames para atualizar todos os cálculos
      const turmaId = document.getElementById('exameTurmaSelect')?.value;
      if (turmaId) {
        await carregarPautaExamesTurma();
      }
    } else {
      mostrarToast(res?.message || 'Erro ao guardar parâmetros.', 'danger');
    }
  } catch (err) {
    console.error('Erro ao guardar parâmetros de exame:', err);
    mostrarToast('Erro de comunicação ao guardar parâmetros.', 'danger');
  }
}

async function salvarParametrosExameInline() {
  const inpFreq = document.getElementById('inlineParamPesoFreq');
  const inpEx = document.getElementById('inlineParamPesoExame');
  const inpMin = document.getElementById('inlineParamNotaMinima');

  const pf = Number(inpFreq?.value || 50);
  const pe = Number(inpEx?.value || 50);
  const nm = Number(inpMin?.value || 10);

  if (isNaN(pf) || isNaN(pe) || isNaN(nm)) {
    mostrarToast('Preencha valores numéricos válidos.', 'warning');
    return;
  }

  if (Math.round(pf + pe) !== 100) {
    mostrarToast('A soma da percentagem de frequência e exame deve ser exatamente 100%.', 'danger');
    return;
  }

  if (nm < 0 || nm > 20) {
    mostrarToast('A nota mínima do exame deve estar entre 0 e 20 valores.', 'danger');
    return;
  }

  const btnSalvar = document.getElementById('btnSalvarParametrosInline');
  if (btnSalvar) {
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> A guardar...`;
  }

  try {
    const res = await apiFetch('/api/v1/pautas/exames/parametros/', {
      method: 'POST',
      body: JSON.stringify({
        peso_frequencia: pf,
        peso_exame: pe,
        nota_minima_exame: nm
      })
    });

    if (res && res.success) {
      mostrarToast(res.message || 'Parâmetros de exame configurados com sucesso!', 'success');
      atualizarCamposParametrosExameNaInterface({
        peso_frequencia: pf,
        peso_exame: pe,
        nota_minima_exame: nm
      });

      // Recarregar pauta de exames para atualizar todos os cálculos
      const turmaId = document.getElementById('exameTurmaSelect')?.value;
      if (turmaId) {
        await carregarPautaExamesTurma();
      }
    } else {
      mostrarToast(res?.message || 'Erro ao guardar parâmetros.', 'danger');
    }
  } catch (err) {
    console.error('Erro ao guardar parâmetros de exame:', err);
    mostrarToast('Erro de comunicação ao guardar parâmetros.', 'danger');
  } finally {
    if (btnSalvar) {
      btnSalvar.disabled = false;
      btnSalvar.innerHTML = `<i class="bi bi-check-circle-fill me-1"></i> Guardar Parâmetros`;
    }
  }
}

async function salvarNotasExame() {
  const turmaId = document.getElementById('exameTurmaSelect')?.value;
  const anoSelect = document.getElementById('exameAnoSelect');
  const anoLetivo = anoSelect?.value || (window.state?.tenant?.ano_letivo_ativo || '2026');
  if (!turmaId) {
    mostrarToast('Selecione uma turma de exame primeiro.', 'warning');
    return;
  }

  if (window._sigeNotasExameModificadas.size === 0) {
    mostrarToast('Nenhuma alteração de nota de exame para guardar.', 'info');
    return;
  }

  const notasPayload = Array.from(window._sigeNotasExameModificadas.values());
  const btnSalvar = document.getElementById('btnSalvarNotasExame');
  if (btnSalvar) {
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> A guardar...`;
  }

  try {
    const res = await apiFetch(`/api/v1/pautas/exames/turma/${turmaId}/salvar/`, {
      method: 'POST',
      body: JSON.stringify({
        ano_letivo: anoLetivo,
        notas: notasPayload
      })
    });

    if (res && res.success) {
      mostrarToast(res.message || 'Notas de exame guardadas com sucesso na base de dados!', 'success');
      window._sigeNotasExameModificadas.clear();
      if (btnSalvar) {
        btnSalvar.disabled = false;
        btnSalvar.classList.remove('btn-warning');
        btnSalvar.classList.add('btn-primary');
        btnSalvar.innerHTML = `<i class="bi bi-floppy-fill me-1"></i> Guardar Notas de Exame`;
      }
      // Recarregar dados para sincronizar cálculos com o backend
      await carregarPautaExamesTurma();
    } else {
      mostrarToast(res?.message || 'Erro ao guardar notas de exame.', 'danger');
      if (btnSalvar) btnSalvar.disabled = false;
    }
  } catch (err) {
    console.error('Erro ao salvar notas de exame:', err);
    mostrarToast('Erro de comunicação ao salvar notas.', 'danger');
    if (btnSalvar) btnSalvar.disabled = false;
  }
}

async function exportarPautaExamesExcel() {
  const turmaId = document.getElementById('exameTurmaSelect')?.value;
  const anoSelect = document.getElementById('exameAnoSelect');
  const anoLetivo = anoSelect?.value || (window.state?.tenant?.ano_letivo_ativo || '2026');
  if (!turmaId) {
    mostrarToast('Selecione uma turma com exame para exportar.', 'warning');
    return;
  }
  const nomeTurma = (document.getElementById('exameTurmaSelect')?.selectedOptions[0]?.text || 'Turma').replace(/[^\w\-]/g, '_');
  await downloadFicheiroBinario(`/api/v1/pautas/exames/turma/${turmaId}/xlsx?anoLetivo=${anoLetivo}`, `Pauta_Exames_${nomeTurma}_${anoLetivo}.xlsx`);
}

async function descarregarPautaExamesPdf() {
  const turmaId = document.getElementById('exameTurmaSelect')?.value;
  const anoSelect = document.getElementById('exameAnoSelect');
  const anoLetivo = anoSelect?.value || (window.state?.tenant?.ano_letivo_ativo || '2026');
  if (!turmaId) {
    mostrarToast('Selecione uma turma com exame para exportar.', 'warning');
    return;
  }
  const nomeTurma = (document.getElementById('exameTurmaSelect')?.selectedOptions[0]?.text || 'Turma').replace(/[^\w\-]/g, '_');
  await downloadFicheiroBinario(`/api/v1/pautas/exames/turma/${turmaId}/pdf?anoLetivo=${anoLetivo}`, `Pauta_Exames_${nomeTurma}_${anoLetivo}.pdf`);
}

function imprimirPautaExames() {
  document.body.classList.remove('print-orientacao-portrait');
  document.body.classList.add('print-orientacao-landscape');
  window.print();
}

// Exportar globalmente para chamadas do HTML e navegação SPA
window.carregarExames = carregarExames;
window.filtrarTurmasExamesPorClasse = filtrarTurmasExamesPorClasse;
window.carregarPautaExamesTurma = carregarPautaExamesTurma;
window.aoMudarNotaExame = aoMudarNotaExame;
window.salvarNotasExame = salvarNotasExame;
window.exportarPautaExamesExcel = exportarPautaExamesExcel;
window.descarregarPautaExamesPdf = descarregarPautaExamesPdf;
window.imprimirPautaExames = imprimirPautaExames;
window.abrirModalParametrosExame = abrirModalParametrosExame;
window.aoMudarPesoFrequencia = aoMudarPesoFrequencia;
window.aoMudarPesoExame = aoMudarPesoExame;
window.salvarParametrosExame = salvarParametrosExame;
window.alternarJanelaParametrosExame = alternarJanelaParametrosExame;
window.aoMudarPesoFrequenciaInline = aoMudarPesoFrequenciaInline;
window.aoMudarPesoExameInline = aoMudarPesoExameInline;
window.salvarParametrosExameInline = salvarParametrosExameInline;
window.reporParametrosExamePadraoMEC = reporParametrosExamePadraoMEC;
window.atualizarCamposParametrosExameNaInterface = atualizarCamposParametrosExameNaInterface;


// =====================================================================
// DELEGAÇÃO DE PERMISSÕES DE LANÇAMENTO DE EXAMES (DIRECTOR PEDAGÓGICO)
// =====================================================================

let _professoresExameCache = [];
let _classesExameCache = [];
let _autorizacoesExameCache = new Map();
let _modoPermissaoExames = 'ALGUNS_PROFESSORES';

function selecionarModoPermissaoExame(modo) {
  _modoPermissaoExames = modo || 'ALGUNS_PROFESSORES';

  const radioDap = document.getElementById('radioModoApenasDap');
  const radioAlguns = document.getElementById('radioModoAlgunsProfessores');
  const radioTodos = document.getElementById('radioModoTodosProfessores');

  if (radioDap) radioDap.checked = (_modoPermissaoExames === 'APENAS_DAP');
  if (radioAlguns) radioAlguns.checked = (_modoPermissaoExames === 'ALGUNS_PROFESSORES');
  if (radioTodos) radioTodos.checked = (_modoPermissaoExames === 'TODOS_PROFESSORES');

  const cardDap = document.getElementById('cardModoApenasDap');
  const cardAlguns = document.getElementById('cardModoAlgunsProfessores');
  const cardTodos = document.getElementById('cardModoTodosProfessores');

  [cardDap, cardAlguns, cardTodos].forEach(c => {
    if (c) {
      c.classList.remove('border-primary', 'bg-primary', 'bg-opacity-10', 'border-danger', 'bg-danger', 'border-success', 'bg-success');
    }
  });

  const containerMatriz = document.getElementById('containerMatrizProfessoresClasses');
  const avisoModo = document.getElementById('avisoModoPermissaoSelecionado');
  const textoModo = document.getElementById('textoModoPermissaoSelecionado');

  if (_modoPermissaoExames === 'APENAS_DAP') {
    if (cardDap) cardDap.classList.add('border-danger', 'bg-danger', 'bg-opacity-10');
    if (containerMatriz) containerMatriz.classList.add('d-none');
    if (avisoModo && textoModo) {
      avisoModo.className = 'alert alert-danger py-2 px-3 small mb-3';
      textoModo.innerHTML = '<strong>Regime Exclusivo:</strong> O lançamento de notas de exame nesta instituição é exclusivo do <strong>Director Pedagógico</strong> e Directoria da Escola. Professores têm apenas acesso para consulta e visualização das pautas.';
      avisoModo.classList.remove('d-none');
    }
  } else if (_modoPermissaoExames === 'TODOS_PROFESSORES') {
    if (cardTodos) cardTodos.classList.add('border-success', 'bg-success', 'bg-opacity-10');
    if (containerMatriz) containerMatriz.classList.add('d-none');
    if (avisoModo && textoModo) {
      avisoModo.className = 'alert alert-success py-2 px-3 small mb-3';
      textoModo.innerHTML = '<strong>Regime Aberto:</strong> Todos os professores ativos da instituição têm permissão para lançar notas de exame em todas as turmas e classes com exame.';
      avisoModo.classList.remove('d-none');
    }
  } else {
    // ALGUNS_PROFESSORES (indicados)
    if (cardAlguns) cardAlguns.classList.add('border-primary', 'bg-primary', 'bg-opacity-10');
    if (containerMatriz) containerMatriz.classList.remove('d-none');
    if (avisoModo) avisoModo.classList.add('d-none');
  }
}

async function abrirModalProfessoresExame() {
  const modalEl = document.getElementById('modalProfessoresExame');
  if (!modalEl) return;

  const bsModal = new bootstrap.Modal(modalEl);
  bsModal.show();

  const tbody = document.getElementById('tbodyProfessoresExameModal');
  const theadRow = document.getElementById('theadProfessoresExameRow');
  const badgesBox = document.getElementById('modalExameBadgesClasses');
  const contadorInfo = document.getElementById('contadorProfessoresAutorizadosInfo');

  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="py-4 text-center text-muted">
          <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
          A carregar professores e classes com exame da instituição...
        </td>
      </tr>
    `;
  }

  try {
    const data = await apiFetch('/api/v1/pautas/exames/professores-autorizados/');
    if (!data || !data.success) {
      throw new Error(data?.message || 'Falha ao consultar permissões de exames');
    }

    _professoresExameCache = data.professores || [];
    _classesExameCache = data.classes_com_exame || ['10ª Classe', '12ª Classe'];
    _autorizacoesExameCache.clear();

    const modo = data.modo_permissao || 'ALGUNS_PROFESSORES';
    selecionarModoPermissaoExame(modo);

    const autorizacoes = data.autorizacoes || [];
    autorizacoes.forEach(a => {
      if (a.professor_id && a.ativo !== false) {
        _autorizacoesExameCache.set(String(a.professor_id), new Set(a.classes || []));
      }
    });

    // Renderizar badges das classes com exame disponíveis automaticamente
    if (badgesBox) {
      badgesBox.innerHTML = _classesExameCache.map(c => `
        <span class="badge bg-primary px-2 py-1"><i class="bi bi-mortarboard me-1"></i>${c}</span>
      `).join(' ');
    }

    // Renderizar cabeçalho da tabela com colunas dinâmicas para cada classe com exame
    if (theadRow) {
      let ths = `
        <th class="text-start ps-3" style="min-width: 200px;">Professor</th>
        <th style="min-width: 120px;">Especialidade</th>
      `;
      _classesExameCache.forEach(c => {
        ths += `<th class="text-center" style="min-width: 100px;"><i class="bi bi-check2-circle text-primary me-1"></i>${c}</th>`;
      });
      ths += `<th style="min-width: 110px;">Ações Rápidas</th>`;
      theadRow.innerHTML = ths;
    }

    renderizarLinhasProfessoresModalExame();

  } catch (err) {
    console.error('Erro ao abrir modal de professores autorizados:', err);
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" class="py-3 text-center text-danger">
            <i class="bi bi-exclamation-triangle-fill me-1"></i> Não foi possível carregar os dados de professores e classes.
          </td>
        </tr>
      `;
    }
  }
}

function renderizarLinhasProfessoresModalExame() {
  const tbody = document.getElementById('tbodyProfessoresExameModal');
  const contadorInfo = document.getElementById('contadorProfessoresAutorizadosInfo');
  if (!tbody) return;

  const termo = (document.getElementById('filtroProfessoresExameInput')?.value || '').toLowerCase().trim();
  const profsFiltrados = _professoresExameCache.filter(p => {
    if (!termo) return true;
    return (p.nome || '').toLowerCase().includes(termo) ||
           (p.codigo || '').toLowerCase().includes(termo) ||
           (p.especialidade || '').toLowerCase().includes(termo);
  });

  if (profsFiltrados.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="${_classesExameCache.length + 3}" class="py-4 text-center text-muted">
          Nenhum professor encontrado com os critérios de pesquisa.
        </td>
      </tr>
    `;
    return;
  }

  let totalAutorizados = 0;
  _professoresExameCache.forEach(p => {
    const s = _autorizacoesExameCache.get(String(p.id));
    if (s && s.size > 0) totalAutorizados++;
  });

  if (contadorInfo) {
    contadorInfo.innerHTML = `<strong>${totalAutorizados}</strong> de <strong>${_professoresExameCache.length}</strong> professor(es) com autorização activa.`;
  }

  let trs = '';
  profsFiltrados.forEach(p => {
    const pId = String(p.id);
    const classesAutorizadas = _autorizacoesExameCache.get(pId) || new Set();

    let tdsClasses = '';
    _classesExameCache.forEach(c => {
      const isChecked = classesAutorizadas.has(c);
      tdsClasses += `
        <td class="text-center align-middle">
          <input type="checkbox" class="form-check-input chk-prof-classe shadow-none"
            style="width: 19px; height: 19px; cursor: pointer;"
            data-prof-id="${pId}" data-classe="${c}"
            ${isChecked ? 'checked' : ''}
            onchange="aoAlternarPermissaoClasseProf('${pId}', '${c}', this.checked)">
        </td>
      `;
    });

    trs += `
      <tr id="linha_prof_perm_${pId}">
        <td class="text-start ps-3 align-middle">
          <div class="fw-bold text-dark">${p.nome}</div>
          <small class="text-muted font-monospace">${p.codigo || 'Docente'}</small>
        </td>
        <td class="align-middle text-muted small">${p.especialidade || '---'}</td>
        ${tdsClasses}
        <td class="align-middle">
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-primary btn-sm py-0 px-2" style="font-size: 0.75rem;" onclick="marcarClassesDoProfessor('${pId}', true)" title="Autorizar em todas as classes com exame">
              Todas
            </button>
            <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-2" style="font-size: 0.75rem;" onclick="marcarClassesDoProfessor('${pId}', false)" title="Revogar de todas as classes">
              Nenhuma
            </button>
          </div>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = trs;
}

function aoAlternarPermissaoClasseProf(pId, classe, isChecked) {
  if (!_autorizacoesExameCache.has(pId)) {
    _autorizacoesExameCache.set(pId, new Set());
  }
  const setClasses = _autorizacoesExameCache.get(pId);
  if (isChecked) {
    setClasses.add(classe);
  } else {
    setClasses.delete(classe);
  }
  atualizarContadorModalProfessores();
}

function marcarClassesDoProfessor(pId, marcar) {
  if (!_autorizacoesExameCache.has(pId)) {
    _autorizacoesExameCache.set(pId, new Set());
  }
  const setClasses = _autorizacoesExameCache.get(pId);
  if (marcar) {
    _classesExameCache.forEach(c => setClasses.add(c));
  } else {
    setClasses.clear();
  }
  renderizarLinhasProfessoresModalExame();
}

function marcarTodosProfessoresTodasClasses(marcar) {
  _professoresExameCache.forEach(p => {
    const pId = String(p.id);
    if (!_autorizacoesExameCache.has(pId)) {
      _autorizacoesExameCache.set(pId, new Set());
    }
    const setClasses = _autorizacoesExameCache.get(pId);
    if (marcar) {
      _classesExameCache.forEach(c => setClasses.add(c));
    } else {
      setClasses.clear();
    }
  });
  renderizarLinhasProfessoresModalExame();
}

function filtrarTabelaProfessoresExame() {
  renderizarLinhasProfessoresModalExame();
}

function atualizarContadorModalProfessores() {
  let totalAutorizados = 0;
  _professoresExameCache.forEach(p => {
    const s = _autorizacoesExameCache.get(String(p.id));
    if (s && s.size > 0) totalAutorizados++;
  });
  const contadorInfo = document.getElementById('contadorProfessoresAutorizadosInfo');
  if (contadorInfo) {
    contadorInfo.innerHTML = `<strong>${totalAutorizados}</strong> de <strong>${_professoresExameCache.length}</strong> professor(es) com autorização activa.`;
  }
}

async function salvarProfessoresAutorizadosExame() {
  const btn = document.getElementById('btnSalvarProfessoresExame');
  const txtOriginal = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> A guardar...';
  }

  const payloadAutorizacoes = [];
  _professoresExameCache.forEach(p => {
    const pId = String(p.id);
    const setClasses = _autorizacoesExameCache.get(pId);
    if (setClasses && setClasses.size > 0) {
      payloadAutorizacoes.push({
        professor_id: pId,
        professor_nome: p.nome,
        classes: Array.from(setClasses),
        ativo: true
      });
    }
  });

  try {
    const json = await apiFetch('/api/v1/pautas/exames/professores-autorizados/', {
      method: 'POST',
      body: JSON.stringify({
        modo_permissao: _modoPermissaoExames,
        autorizacoes: payloadAutorizacoes
      })
    });

    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao(json.message || 'Permissões guardadas com sucesso!', 'success');
    } else if (typeof mostrarToast === 'function') {
      mostrarToast(json.message || 'Permissões guardadas com sucesso!', 'success');
    }

    const modalEl = document.getElementById('modalProfessoresExame');
    if (modalEl) {
      const modalInst = bootstrap.Modal.getInstance(modalEl);
      if (modalInst) modalInst.hide();
    }

    if (typeof carregarPautaExamesTurma === 'function') {
      carregarPautaExamesTurma();
    }
  } catch (err) {
    console.error('Erro ao guardar autorizações de exame:', err);
    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao(err.message || 'Erro ao guardar autorizações', 'danger');
    } else if (typeof mostrarToast === 'function') {
      mostrarToast(err.message || 'Erro ao guardar autorizações', 'danger');
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = txtOriginal;
    }
  }
}

window.abrirModalProfessoresExame = abrirModalProfessoresExame;
window.renderizarLinhasProfessoresModalExame = renderizarLinhasProfessoresModalExame;
window.aoAlternarPermissaoClasseProf = aoAlternarPermissaoClasseProf;
window.marcarClassesDoProfessor = marcarClassesDoProfessor;
window.marcarTodosProfessoresTodasClasses = marcarTodosProfessoresTodasClasses;
window.filtrarTabelaProfessoresExame = filtrarTabelaProfessoresExame;
window.salvarProfessoresAutorizadosExame = salvarProfessoresAutorizadosExame;


// =====================================================================
// FORMULÁRIO INDIVIDUAL DE LANÇAMENTO DE NOTAS DE EXAME
// Pesquisa, seleção e formulário amigável de lançamento por candidato
// =====================================================================
window._formExameAlunoAtualId = null;
window._formExameListaAlunos = [];

function abrirModalFormularioLancamentoExame() {
  const modalEl = document.getElementById('modalFormularioLancamentoExame');
  if (!modalEl) return;

  const d = window._sigePautaExamesData;
  if (!d || !Array.isArray(d.alunos) || d.alunos.length === 0) {
    if (typeof mostrarToast === 'function') {
      mostrarToast('Por favor, selecione primeiro uma turma com exame que contenha alunos matriculados.', 'warning');
    } else if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao('Por favor, selecione primeiro uma turma com exame que contenha alunos matriculados.', 'warning');
    }
    return;
  }

  const podeEditar = d.pode_editar !== false;
  const btnSalvar = document.getElementById('btnSalvarFormExame');
  const btnProximo = document.getElementById('btnSalvarEProximoFormExame');
  if (btnSalvar) btnSalvar.style.display = podeEditar ? '' : 'none';
  if (btnProximo) btnProximo.style.display = podeEditar ? '' : 'none';

  // Atualizar badge dos parâmetros no modal
  const params = d.parametros || { peso_frequencia: 50, peso_exame: 50, nota_minima_exame: 10 };
  const badgeParam = document.getElementById('formExameParametrosBadge');
  if (badgeParam) {
    badgeParam.textContent = `Freq: ${params.peso_frequencia || 50}% | Exame: ${params.peso_exame || 50}% | Mín: ${params.nota_minima_exame || 10}`;
  }

  window._formExameListaAlunos = d.alunos;

  const inputBusca = document.getElementById('formExameAlunoSearch');
  if (inputBusca) inputBusca.value = '';

  popularSelectAlunosFormulario(d.alunos);

  // Selecionar primeiro aluno ou o atual se já existir
  const alunoId = window._formExameAlunoAtualId && d.alunos.some(a => a.id === window._formExameAlunoAtualId)
    ? window._formExameAlunoAtualId
    : d.alunos[0].id;

  selecionarAlunoFormularioExame(alunoId);

  const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
  bsModal.show();
}

function popularSelectAlunosFormulario(alunos) {
  const sel = document.getElementById('formExameAlunoSelect');
  if (!sel) return;
  if (!alunos || alunos.length === 0) {
    sel.innerHTML = '<option value="">Nenhum candidato encontrado</option>';
    return;
  }
  sel.innerHTML = alunos.map((a, idx) => `
    <option value="${a.id}">Nº ${a.numero || idx + 1} - ${a.nome}</option>
  `).join('');
}

function filtrarAlunosFormularioExame(termo) {
  const t = (termo || '').toLowerCase().trim();
  const todos = window._sigePautaExamesData?.alunos || [];
  const filtrados = todos.filter(a => {
    if (!t) return true;
    return (a.nome || '').toLowerCase().includes(t) ||
           String(a.numero || '').includes(t) ||
           (a.matricula || '').toLowerCase().includes(t) ||
           (a.candidato || '').toLowerCase().includes(t);
  });

  popularSelectAlunosFormulario(filtrados);
  if (filtrados.length > 0) {
    selecionarAlunoFormularioExame(filtrados[0].id);
  } else {
    const container = document.getElementById('formExameDisciplinasContainer');
    if (container) {
      container.innerHTML = '<div class="alert alert-warning text-center small my-2">Nenhum candidato encontrado com esse nome ou número.</div>';
    }
  }
}

function navegarAlunoFormularioExame(direcao) {
  const lista = window._sigePautaExamesData?.alunos || [];
  if (lista.length === 0) return;

  const curId = window._formExameAlunoAtualId;
  const curIdx = lista.findIndex(a => a.id === curId);
  let novoIdx = curIdx + direcao;

  if (novoIdx < 0) novoIdx = 0;
  if (novoIdx >= lista.length) novoIdx = lista.length - 1;

  const novoAluno = lista[novoIdx];
  if (novoAluno) {
    selecionarAlunoFormularioExame(novoAluno.id);
  }
}

function selecionarAlunoFormularioExame(alunoId) {
  window._formExameAlunoAtualId = alunoId;
  const d = window._sigePautaExamesData;
  if (!d) return;

  const alunos = d.alunos || [];
  const aluno = alunos.find(a => a.id === alunoId);
  if (!aluno) return;

  const sel = document.getElementById('formExameAlunoSelect');
  if (sel && sel.value !== alunoId) sel.value = alunoId;

  // Atualizar Ficha Resumo do Aluno
  const elNome = document.getElementById('formExameAlunoNome');
  const elNum = document.getElementById('formExameAlunoNumero');
  const elCand = document.getElementById('formExameAlunoCandidato');
  const elTurma = document.getElementById('formExameAlunoTurma');
  const elIniciais = document.getElementById('formExameAlunoIniciais');
  const elPosicao = document.getElementById('formExamePosicaoAlunoInfo');

  const alunoIdx = alunos.findIndex(a => a.id === alunoId);
  if (elNome) elNome.textContent = aluno.nome;
  if (elNum) elNum.textContent = aluno.numero || (alunoIdx + 1);
  if (elCand) elCand.textContent = aluno.candidato || aluno.matricula || '--';
  if (elTurma) elTurma.textContent = aluno.turma || d.turma?.nome || '--';

  if (elIniciais) {
    const partes = (aluno.nome || '').trim().split(/\s+/);
    const init = (partes[0]?.[0] || '') + (partes[partes.length - 1]?.[0] || '');
    elIniciais.textContent = init.toUpperCase() || 'AL';
  }

  if (elPosicao) {
    elPosicao.textContent = `Candidato ${alunoIdx + 1} de ${alunos.length}`;
  }

  // Renderizar disciplinas com exame do aluno
  const container = document.getElementById('formExameDisciplinasContainer');
  const podeEditar = d.pode_editar !== false;
  const disciplinasComExame = d.disciplinas_com_exame || [];

  if (disciplinasComExame.length === 0) {
    if (container) {
      container.innerHTML = `
        <div class="alert alert-warning small text-center my-2">
          Nenhuma disciplina com exame cadastrada para esta classe/turma.
        </div>
      `;
    }
    return;
  }

  let htmlDiscs = '';
  disciplinasComExame.forEach(disc => {
    const dData = aluno.disciplinas?.[disc.id] || {};
    const chave = `${alunoId}_${disc.id}`;
    const mod = window._sigeNotasExameModificadas.get(chave);

    const e1 = (mod && mod.exame_1epoca !== undefined) ? mod.exame_1epoca : dData.exame_1epoca;
    const e2 = (mod && mod.exame_2epoca !== undefined) ? mod.exame_2epoca : dData.exame_2epoca;

    const e1Val = (e1 !== null && e1 !== undefined && e1 !== '') ? e1 : '';
    const e2Val = (e2 !== null && e2 !== undefined && e2 !== '') ? e2 : '';

    const freqVal = (dData.frequencia !== undefined && dData.frequencia !== null) ? dData.frequencia : '-';

    htmlDiscs += `
      <div class="card p-3 border shadow-none bg-white disc-exame-row" id="formDiscRow_${alunoId}_${disc.id}">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-primary px-2 py-1">${disc.codigo || 'EXAME'}</span>
            <strong class="text-dark fs-6">${disc.nome}</strong>
          </div>
          <div class="d-flex align-items-center gap-2">
            <span class="small text-muted">Média de Frequência:</span>
            <span class="badge bg-light text-dark border font-monospace fs-6 px-2 py-1">${freqVal}</span>
          </div>
        </div>

        <div class="row g-2 align-items-center">
          <div class="col-md-4">
            <label class="form-label x-small fw-bold text-muted mb-1">
              <i class="bi bi-pencil me-1"></i>1ª Época (0 a 20)
            </label>
            <input type="number" step="0.01" min="0" max="20"
              class="form-control form-control-sm text-center fw-bold font-monospace form-input-exame"
              id="formInputE1_${alunoId}_${disc.id}"
              placeholder="ex: 12 ou 14.5"
              value="${e1Val}"
              ${!podeEditar ? 'disabled readonly' : ''}
              oninput="aoMudarNotaFormularioExame('${alunoId}', '${disc.id}', '1', this.value)"
              onchange="aoMudarNotaFormularioExame('${alunoId}', '${disc.id}', '1', this.value)">
          </div>

          <div class="col-md-4">
            <label class="form-label x-small fw-bold text-muted mb-1">
              <i class="bi bi-pencil me-1"></i>2ª Época (se necessária)
            </label>
            <input type="number" step="0.01" min="0" max="20"
              class="form-control form-control-sm text-center fw-bold font-monospace form-input-exame"
              id="formInputE2_${alunoId}_${disc.id}"
              placeholder="ex: 10 ou 11.25"
              value="${e2Val}"
              ${!podeEditar ? 'disabled readonly' : ''}
              oninput="aoMudarNotaFormularioExame('${alunoId}', '${disc.id}', '2', this.value)"
              onchange="aoMudarNotaFormularioExame('${alunoId}', '${disc.id}', '2', this.value)">
          </div>

          <div class="col-md-4">
            <label class="form-label x-small fw-bold text-muted mb-1">
              <i class="bi bi-calculator me-1"></i>Média Final da Disciplina
            </label>
            <div class="d-flex align-items-center justify-content-between p-1 px-2 border rounded bg-light">
              <span class="font-monospace fw-bold fs-6" id="formDiscMedia_${alunoId}_${disc.id}">-</span>
              <span class="badge" id="formDiscBadge_${alunoId}_${disc.id}">---</span>
            </div>
          </div>
        </div>
      </div>
    `;
  });

  if (container) container.innerHTML = htmlDiscs;

  recalcularFormularioExame(alunoId);
}

function aoMudarNotaFormularioExame(alunoId, discId, epoca, valor) {
  let valStr = String(valor || '').trim().replace(',', '.');
  let valNum = null;

  if (valStr !== '' && !isNaN(Number(valStr))) {
    valNum = Math.max(0, Math.min(20, Number(valStr)));
    valNum = Math.round(valNum * 100) / 100; // Suporta decimais até 2 casas
  }

  const chave = `${alunoId}_${discId}`;
  if (!window._sigeNotasExameModificadas.has(chave)) {
    window._sigeNotasExameModificadas.set(chave, { aluno_id: alunoId, disciplina_id: discId });
  }
  const obj = window._sigeNotasExameModificadas.get(chave);
  if (epoca === '1') obj.exame_1epoca = valNum;
  if (epoca === '2') obj.exame_2epoca = valNum;

  // Sincronizar input correspondente na tabela principal (se existir)
  const inputTabela = document.querySelector(`input.input-exame-nota[data-aluno="${alunoId}"][data-disc="${discId}"][data-epoca="${epoca}"]`);
  if (inputTabela) {
    inputTabela.value = (valNum !== null) ? valNum : '';
  }

  // Recalcular cálculos na tabela principal
  recalcularLinhaAlunoInterface(alunoId);

  // Recalcular cálculos no modal do formulário
  recalcularFormularioExame(alunoId);

  // Destacar botão de salvar com indicação visual de alteração pendente
  const btnSalvar = document.getElementById('btnSalvarNotasExame');
  if (btnSalvar) {
    btnSalvar.classList.add('btn-warning');
    btnSalvar.classList.remove('btn-primary');
    btnSalvar.innerHTML = `<i class="bi bi-floppy-fill me-1"></i> Guardar Alterações (${window._sigeNotasExameModificadas.size})`;
  }
}

function recalcularFormularioExame(alunoId) {
  const d = window._sigePautaExamesData;
  if (!d) return;

  const aluno = (d.alunos || []).find(a => a.id === alunoId);
  if (!aluno) return;

  const params = d.parametros || { peso_frequencia: 50, peso_exame: 50, nota_minima_exame: 10 };
  const pesoFreq = Number(params.peso_frequencia || 50);
  const pesoExame = Number(params.peso_exame || 50);
  const notaMinima = Number(params.nota_minima_exame || 10);

  const disciplinasComExame = d.disciplinas_com_exame || [];
  const disciplinasSemExame = d.disciplinas_sem_exame || [];
  const sufixoGen = (aluno.genero || 'M').toUpperCase().startsWith('F') ? 'a' : 'o';

  const notasFinais = [];
  const discReprovadas = [];

  disciplinasComExame.forEach(disc => {
    const dId = disc.id;
    const dData = aluno.disciplinas?.[dId] || {};
    const chave = `${alunoId}_${dId}`;
    const mod = window._sigeNotasExameModificadas.get(chave);

    const e1 = (mod && mod.exame_1epoca !== undefined) ? mod.exame_1epoca : dData.exame_1epoca;
    const e2 = (mod && mod.exame_2epoca !== undefined) ? mod.exame_2epoca : dData.exame_2epoca;

    const e1Num = (e1 !== null && e1 !== undefined && e1 !== '') ? Number(e1) : null;
    const e2Num = (e2 !== null && e2 !== undefined && e2 !== '') ? Number(e2) : null;

    let neEfetivo = null;
    if (e1Num !== null && e1Num >= notaMinima) {
      neEfetivo = e1Num;
    } else if (e1Num !== null && e1Num < notaMinima) {
      if (e2Num !== null) neEfetivo = e2Num;
    } else if (e1Num === null && e2Num !== null) {
      neEfetivo = e2Num;
    }

    const freqVal = typeof dData.frequencia_decimal === 'number' ? dData.frequencia_decimal : (typeof dData.frequencia === 'number' ? dData.frequencia : null);
    let mediaFinalDisc = null;

    if (neEfetivo !== null) {
      if (freqVal !== null) {
        mediaFinalDisc = Math.round((freqVal * (pesoFreq / 100)) + (neEfetivo * (pesoExame / 100)));
      } else {
        mediaFinalDisc = Math.round(neEfetivo);
      }
    } else {
      // REGRA: Se não tem nota num dos exames (1ª ou 2ª) então a Média nessa disciplina é 0
      mediaFinalDisc = 0;
    }

    const elMedia = document.getElementById(`formDiscMedia_${alunoId}_${dId}`);
    const elBadge = document.getElementById(`formDiscBadge_${alunoId}_${dId}`);
    if (elMedia) {
      elMedia.textContent = mediaFinalDisc;
      elMedia.className = `font-monospace fw-bold fs-6 ${mediaFinalDisc >= 9.5 ? 'text-success' : 'text-danger'}`;
    }
    if (elBadge) {
      if (mediaFinalDisc >= 9.5) {
        elBadge.className = 'badge bg-success';
        elBadge.textContent = 'Aprovado';
      } else {
        elBadge.className = 'badge bg-danger';
        elBadge.textContent = 'Reprovado';
      }
    }

    notasFinais.push(mediaFinalDisc);
    if (mediaFinalDisc < 9.5) {
      discReprovadas.push(disc.nome);
    }
  });

  disciplinasSemExame.forEach(disc => {
    const dData = aluno.disciplinas?.[disc.id] || {};
    const fVal = typeof dData.frequencia === 'number' ? dData.frequencia : 0;
    notasFinais.push(fVal);
    if (fVal < 9.5) discReprovadas.push(disc.nome);
  });

  let resAprov = `Reprovad${sufixoGen}`;
  let mfGlobal = 0;

  if (notasFinais.length > 0) {
    const soma = notasFinais.reduce((acc, v) => acc + v, 0);
    mfGlobal = Math.round(soma / notasFinais.length);
    const aprovadoGeral = (discReprovadas.length === 0 && mfGlobal >= 9.5);
    resAprov = aprovadoGeral ? `Aprovad${sufixoGen}` : `Reprovad${sufixoGen}`;
  }

  const elResGeral = document.getElementById('formExameAlunoResultadoGeral');
  if (elResGeral) {
    elResGeral.textContent = `${resAprov} (MF: ${mfGlobal})`;
    // Aprovado a preto e Reprovado a vermelho
    if (resAprov.includes('Aprovad')) {
      elResGeral.className = 'fw-bold fs-6';
      elResGeral.style.color = '#000000';
    } else {
      elResGeral.className = 'fw-bold fs-6 text-danger';
      elResGeral.style.color = '#dc2626';
    }
  }
}

async function salvarNotasFormularioExame(irParaProximo = false) {
  const btn = irParaProximo ? document.getElementById('btnSalvarEProximoFormExame') : document.getElementById('btnSalvarFormExame');
  const txtOriginal = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> A guardar...';
  }

  try {
    await salvarNotasExame();
    if (irParaProximo) {
      navegarAlunoFormularioExame(1);
    } else if (window._formExameAlunoAtualId) {
      recalcularFormularioExame(window._formExameAlunoAtualId);
    }
  } catch (err) {
    console.error('Erro ao guardar notas via formulário:', err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = txtOriginal;
    }
  }
}

window.selecionarModoPermissaoExame = selecionarModoPermissaoExame;
window.abrirModalFormularioLancamentoExame = abrirModalFormularioLancamentoExame;
window.filtrarAlunosFormularioExame = filtrarAlunosFormularioExame;
window.selecionarAlunoFormularioExame = selecionarAlunoFormularioExame;
window.navegarAlunoFormularioExame = navegarAlunoFormularioExame;
window.aoMudarNotaFormularioExame = aoMudarNotaFormularioExame;
window.recalcularFormularioExame = recalcularFormularioExame;
window.salvarNotasFormularioExame = salvarNotasFormularioExame;
