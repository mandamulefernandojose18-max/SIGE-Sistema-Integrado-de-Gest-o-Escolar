// =====================================================================
// SIGE - Módulo Exames | Pautas Oficiais de Exame (MEC / Moçambique)
// Modelagem e Cálculo Estrito: Dados reais das pautas de frequência,
// lançamento de notas de 1ª e 2ª época, e integração com Certificados e Declarações.
// =====================================================================

window._sigePautaExamesData = null;
window._sigeNotasExameModificadas = new Map();

async function carregarExames() {
  const container = document.getElementById('view-exames');
  if (!container) return;

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
    window._sigeNotasExameModificadas.clear();

    // Actualizar Cabeçalhos
    const escNome = (window.state?.tenant?.nome || 'ESCOLA SECUNDÁRIA').toUpperCase();
    const elEsc = document.getElementById('pautaExameEscolaNome');
    if (elEsc) elEsc.textContent = escNome;

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

    renderizarTabelaExamesHtml(d);
  } catch (err) {
    console.error('Erro ao carregar pauta de exames:', err);
    container.innerHTML = `
      <div class="alert alert-danger text-center my-4">
        <i class="bi bi-exclamation-triangle-fill me-2"></i>
        Erro de comunicação ao carregar pauta de exames.
      </div>
    `;
  }
}

function renderizarTabelaExamesHtml(d) {
  const container = document.getElementById('containerTabelaPautaExames');
  if (!container) return;

  const disciplinasComExame = d.disciplinas_com_exame || [];
  const disciplinasSemExame = d.disciplinas_sem_exame || [];
  const alunos = d.alunos || [];

  if (alunos.length === 0) {
    container.innerHTML = `
      <div class="alert alert-info text-center my-4">
        <i class="bi bi-info-circle-fill me-2"></i>
        Não existem alunos matriculados ativos nesta turma de exame.
      </div>
    `;
    const rodape = document.getElementById('pautaExameRodapeOficial');
    if (rodape) rodape.classList.add('d-none');
    return;
  }

  // Montar Cabeçalhos da Tabela Fiel ao Modelo MEC
  let thLinha1 = `
    <th rowspan="3" class="align-middle bg-primary text-white border-end" style="min-width: 45px; font-size: 0.72rem;">Nº de Ordem</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end" style="min-width: 85px; font-size: 0.72rem;">Nº Candidato</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-start ps-2" style="min-width: 220px; font-size: 0.78rem;">Nome do Aluno</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end" style="min-width: 45px; font-size: 0.72rem;">Género</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end" style="min-width: 70px; font-size: 0.72rem;">Turma</th>
  `;

  // Disciplinas com exame: 4 colunas cada
  disciplinasComExame.forEach(disc => {
    thLinha1 += `<th colspan="4" class="text-center bg-primary bg-opacity-10 text-primary fw-bold border-start border-end" style="font-size: 0.75rem;">${disc.nome}</th>`;
  });

  // Disciplinas sem exame: 1 coluna cada
  disciplinasSemExame.forEach(disc => {
    thLinha1 += `<th rowspan="2" class="text-center bg-light text-dark fw-bold border-start border-end" style="font-size: 0.72rem; min-width: 75px;">${disc.nome}</th>`;
  });

  // RESULTADO FINAL: 3 colunas
  thLinha1 += `<th colspan="3" class="text-center bg-dark text-white fw-bold border-start" style="font-size: 0.78rem;">RESULTADO FINAL</th>`;

  // Linha 2 do cabeçalho
  let thLinha2 = '';
  disciplinasComExame.forEach(() => {
    thLinha2 += `
      <th class="bg-light text-dark fw-bold border-end" style="font-size: 0.68rem;">de</th>
      <th class="bg-light text-dark fw-bold border-end" style="font-size: 0.68rem;">Frequência</th>
      <th colspan="2" class="bg-warning bg-opacity-25 text-dark fw-bold border-end" style="font-size: 0.68rem;">Exame</th>
      <th class="bg-primary bg-opacity-10 text-primary fw-bold border-end" style="font-size: 0.68rem;">Média</th>
    `;
  });

  thLinha2 += `
    <th rowspan="2" class="bg-secondary bg-opacity-10 text-dark fw-bold border-end" style="min-width: 85px; font-size: 0.72rem;">Aprovado(a)</th>
    <th rowspan="2" class="bg-secondary bg-opacity-10 text-dark fw-bold border-end" style="min-width: 50px; font-size: 0.72rem;">MF</th>
    <th rowspan="2" class="bg-secondary bg-opacity-10 text-dark fw-bold text-start ps-2" style="min-width: 160px; font-size: 0.72rem;">Disciplina(s) que Reprovou</th>
  `;

  // Linha 3 do cabeçalho
  let thLinha3 = '';
  disciplinasComExame.forEach(() => {
    thLinha3 += `
      <th class="bg-light text-dark fw-semibold border-end" style="font-size: 0.65rem;">Proven.</th>
      <th class="bg-light text-dark fw-semibold border-end" style="font-size: 0.65rem;">-</th>
      <th class="bg-warning bg-opacity-10 text-dark fw-bold border-end" style="font-size: 0.65rem; min-width: 50px;">1ª</th>
      <th class="bg-warning bg-opacity-10 text-dark fw-bold border-end" style="font-size: 0.65rem; min-width: 50px;">2ª</th>
      <th class="bg-primary bg-opacity-10 text-primary fw-bold border-end" style="font-size: 0.65rem;">-</th>
    `;
  });

  disciplinasSemExame.forEach(() => {
    thLinha3 += `<th class="bg-light text-muted border-end" style="font-size: 0.65rem;">Frequência</th>`;
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

      const corMed = (typeof vMed === 'number' || !isNaN(Number(vMed))) 
        ? (Number(vMed) >= 9.5 ? 'text-success fw-bold' : 'text-danger fw-bold') 
        : 'text-muted';

      tdsDiscs += `
        <td class="text-center bg-light border-end font-monospace small">${vFreq}</td>
        <td class="text-center bg-light border-end font-monospace small">${vFreq}</td>
        <td class="p-0 text-center border-end" style="min-width: 48px;">
          <input type="number" step="0.1" min="0" max="20" class="form-control form-control-sm text-center border-0 p-1 font-monospace input-exame-nota"
            value="${e1Val}" placeholder="-" data-aluno="${aluno.id}" data-disc="${d.id}" data-epoca="1"
            onchange="aoMudarNotaExame(this)" oninput="aoMudarNotaExame(this)" style="font-size: 0.8rem; background: transparent;">
        </td>
        <td class="p-0 text-center border-end" style="min-width: 48px;">
          <input type="number" step="0.1" min="0" max="20" class="form-control form-control-sm text-center border-0 p-1 font-monospace input-exame-nota"
            value="${e2Val}" placeholder="-" data-aluno="${aluno.id}" data-disc="${d.id}" data-epoca="2"
            onchange="aoMudarNotaExame(this)" oninput="aoMudarNotaExame(this)" style="font-size: 0.8rem; background: transparent;">
        </td>
        <td class="text-center border-end font-monospace small ${corMed}" id="media_${aluno.id}_${d.id}">
          ${vMed}
        </td>
      `;
    });

    // Disciplinas sem exame
    disciplinasSemExame.forEach(d => {
      const dData = discMap[d.id] || {};
      const vFreq = dData.frequencia !== undefined && dData.frequencia !== null ? dData.frequencia : '-';
      const corFreq = (typeof vFreq === 'number' || !isNaN(Number(vFreq))) 
        ? (Number(vFreq) >= 9.5 ? 'text-success' : 'text-danger') 
        : 'text-muted';
      tdsDiscs += `
        <td class="text-center border-end font-monospace small ${corFreq}">${vFreq}</td>
      `;
    });

    // Resultado Final do Aluno
    const resAprov = String(resFinal.aprovado || 'Pendente').trim();
    let badgeResClass = 'bg-secondary';
    if (resAprov.includes('Aprovad')) badgeResClass = 'bg-success';
    else if (resAprov.includes('Reprovad') || resAprov.includes('Excluíd')) badgeResClass = 'bg-danger';
    else if (resAprov.includes('Admitid')) badgeResClass = 'bg-primary';

    const mfVal = resFinal.mf !== undefined && resFinal.mf !== null ? resFinal.mf : '-';
    const discRep = resFinal.disciplinas_reprovou || '---';

    trsCorpo += `
      <tr id="linha_aluno_${aluno.id}">
        <td class="text-center font-monospace text-muted small border-end">${aluno.numero || idx + 1}</td>
        <td class="text-center font-monospace small border-end fw-semibold text-secondary">${aluno.candidato || aluno.matricula}</td>
        <td class="text-start ps-2 text-dark fw-bold border-end small text-nowrap">${aluno.nome}</td>
        <td class="text-center font-monospace small border-end">${aluno.genero}</td>
        <td class="text-center small border-end text-muted">${aluno.turma}</td>
        ${tdsDiscs}
        <td class="text-center border-end">
          <span class="badge ${badgeResClass} px-2 py-1" id="res_aluno_${aluno.id}" style="font-size: 0.72rem;">${resAprov}</span>
        </td>
        <td class="text-center font-monospace fw-bold border-end" id="mf_aluno_${aluno.id}" style="font-size: 0.85rem;">
          ${mfVal}
        </td>
        <td class="text-start ps-2 small text-danger font-monospace" id="rep_aluno_${aluno.id}" style="font-size: 0.7rem;">
          ${discRep}
        </td>
      </tr>
    `;
  });

  const htmlTabela = `
    <table class="table table-bordered table-sm align-middle text-center sige-tabela-exames mb-0 border" style="font-size: 0.8rem;">
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
    const taxa = estat.taxa_aprovacao || 0.0;

    boxEstat.innerHTML = `
      <div><strong>Total de Candidatos:</strong> <span class="badge bg-secondary ms-1">${tot}</span> (H: ${estat.homens || 0} | M: ${estat.mulheres || 0})</div>
      <div><strong>Aprovados:</strong> <span class="badge bg-success ms-1">${aprov}</span></div>
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

  const disciplinasComExame = d.disciplinas_com_exame || [];
  const disciplinasSemExame = d.disciplinas_sem_exame || [];
  const grauAno = d.turma?.grau_ano || '10ª Classe';
  const is12a = /(^|[^\d])12([ªaº\.\s]|$)/i.test(grauAno);
  const sufixoGen = (aluno.genero || 'M').toUpperCase().startsWith('F') ? 'a' : 'o';

  const notasFinais = [];
  const discReprovadas = [];
  let temAlgumExame = false;

  disciplinasComExame.forEach(disc => {
    const dId = disc.id;
    const dData = aluno.disciplinas?.[dId] || {};
    const chave = `${alunoId}_${dId}`;
    const mod = window._sigeNotasExameModificadas.get(chave);

    const e1 = mod && mod.exame_1epoca !== undefined ? mod.exame_1epoca : dData.exame_1epoca;
    const e2 = mod && mod.exame_2epoca !== undefined ? mod.exame_2epoca : dData.exame_2epoca;
    const neEfetivo = e2 !== null && e2 !== undefined ? e2 : e1;

    if (neEfetivo !== null && neEfetivo !== undefined) {
      temAlgumExame = true;
    }

    const freqVal = typeof dData.frequencia_decimal === 'number' ? dData.frequencia_decimal : (typeof dData.frequencia === 'number' ? dData.frequencia : null);
    let mediaFinalDisc = null;

    if (neEfetivo !== null && neEfetivo !== undefined) {
      if (freqVal !== null) {
        mediaFinalDisc = Math.round((freqVal + neEfetivo) / 2);
      } else {
        mediaFinalDisc = Math.round(neEfetivo);
      }
    } else if (freqVal !== null) {
      mediaFinalDisc = Math.round(freqVal);
    }

    const elMedia = document.getElementById(`media_${alunoId}_${dId}`);
    if (elMedia) {
      elMedia.textContent = mediaFinalDisc !== null ? mediaFinalDisc : '-';
      elMedia.className = `text-center border-end font-monospace small ${mediaFinalDisc !== null && mediaFinalDisc >= 9.5 ? 'text-success fw-bold' : 'text-danger fw-bold'}`;
    }

    if (mediaFinalDisc !== null) {
      notasFinais.push(mediaFinalDisc);
      if (mediaFinalDisc < 9.5) {
        discReprovadas.push(disc.nome);
      }
    }
  });

  disciplinasSemExame.forEach(disc => {
    const dData = aluno.disciplinas?.[disc.id] || {};
    const fVal = typeof dData.frequencia === 'number' ? dData.frequencia : null;
    if (fVal !== null) {
      notasFinais.push(fVal);
      if (fVal < 9.5) discReprovadas.push(disc.nome);
    }
  });

  // Atualizar Resultado Final
  let resAprov = 'Pendente';
  let mfGlobal = '-';

  if (notasFinais.length > 0) {
    const soma = notasFinais.reduce((acc, v) => acc + v, 0);
    mfGlobal = Math.round(soma / notasFinais.length);

    let aprovadoGeral = false;
    if (!is12a) {
      aprovadoGeral = (discReprovadas.length === 0 && mfGlobal >= 9.5);
    } else {
      const temAbaixo8 = notasFinais.some(v => v < 8);
      aprovadoGeral = (mfGlobal >= 9.5 && discReprovadas.length <= 2 && !temAbaixo8);
    }

    if (temAlgumExame) {
      resAprov = aprovadoGeral ? `Aprovad${sufixoGen}` : `Reprovad${sufixoGen}`;
    } else {
      resAprov = mfGlobal >= 9.5 ? `Admitid${sufixoGen}` : `Excluíd${sufixoGen}`;
    }
  }

  const elRes = document.getElementById(`res_aluno_${alunoId}`);
  if (elRes) {
    elRes.textContent = resAprov;
    let badgeCls = 'bg-secondary';
    if (resAprov.includes('Aprovad')) badgeCls = 'bg-success';
    else if (resAprov.includes('Reprovad') || resAprov.includes('Excluíd')) badgeCls = 'bg-danger';
    else if (resAprov.includes('Admitid')) badgeCls = 'bg-primary';
    elRes.className = `badge ${badgeCls} px-2 py-1`;
  }

  const elMf = document.getElementById(`mf_aluno_${alunoId}`);
  if (elMf) elMf.textContent = mfGlobal;

  const elRep = document.getElementById(`rep_aluno_${alunoId}`);
  if (elRep) elRep.textContent = discReprovadas.length > 0 ? discReprovadas.join(', ') : '---';
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
