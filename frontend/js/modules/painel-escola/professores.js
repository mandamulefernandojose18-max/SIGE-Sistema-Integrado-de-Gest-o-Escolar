/**
 * SIGE - PAINEL-ESCOLA | Corpo Docente
 * Ficheiro de código independente do menu: professores.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 5. PROFESSORES ====================
async function carregarProfessores() {
  try {
    const [resProfs, resStats, resTurmas, resDisc] = await Promise.all([
      apiFetch('/api/v1/professores'),
      apiFetch('/api/v1/professores/stats'),
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/disciplinas')
    ]);

    if (resTurmas && resTurmas.success) {
      state.todasTurmas = resTurmas.data || [];
    }
    if (resDisc && resDisc.success) {
      state.todasDisciplinas = resDisc.data || [];
    }

    if (resStats.success) {
      const s = resStats.data;
      document.getElementById('profTotalCard').textContent = s.totalProfessores ?? 0;
      const ratio = (s.proporcaoAlunoProfessor !== undefined && s.proporcaoAlunoProfessor !== null) 
        ? s.proporcaoAlunoProfessor 
        : (s.totalProfessores > 0 ? Math.round(((state.todosAlunos && state.todosAlunos.length) || 0) / s.totalProfessores) : 0);
      document.getElementById('profRatioCard').textContent = `${ratio} : 1`;
      document.getElementById('profAulasMesCard').textContent = s.totalAulasMes ?? (s.totalAlocacoes ? s.totalAlocacoes * 16 : 0);
    }

    state.todosProfessores = resProfs.success ? (resProfs.data || []) : [];
    renderizarBotoesClassesProfessores();
  } catch (err) {
    console.error('Erro ao carregar professores:', err);
  }
}

function obterClassesDocentes() {
  const classesSet = new Set();
  (state.todasTurmas || []).forEach(t => {
    if (t.grau_ano) classesSet.add(t.grau_ano.trim());
  });
  (state.todosProfessores || []).forEach(p => {
    (p.alocacoes || []).forEach(a => {
      const g = a.turma_grau || a.turma?.grau_ano || a.disciplina?.classe;
      if (g) classesSet.add(g.trim());
    });
  });
  (state.todasDisciplinas || []).forEach(d => {
    if (d.classe) classesSet.add(d.classe.trim());
  });
  (state.todosAlunos || []).forEach(a => {
    if (a.classe) classesSet.add(a.classe.trim());
    if (a.turma_grau) classesSet.add(a.turma_grau.trim());
  });

  const ordenadas = Array.from(classesSet).sort((a, b) => {
    const numA = parseInt(a.replace(/\D/g, '')) || 0;
    const numB = parseInt(b.replace(/\D/g, '')) || 0;
    return numA - numB;
  });

  return ordenadas;
}

function calcularMetricasCargaProfessor(p) {
  if (!p) return { totalAlocada: 0, maxNormal: 20, horasNormais: 0, horasExtras: 0, porClasse: {} };

  const maxNormal = Number(p.carga_horaria_semanal) || 20;
  let totalAlocada = 0;
  const porClasse = {};

  (p.alocacoes || []).forEach(a => {
    let ch = Number(a.disciplina_carga_horaria || a.disciplina?.carga_horaria);
    if (!ch || isNaN(ch)) {
      const discId = a.disciplina?.id || a.disciplina;
      const foundD = (state.todasDisciplinas || []).find(d => String(d.id) === String(discId));
      ch = Number(foundD?.carga_horaria) || 5;
    }
    totalAlocada += ch;

    const classe = (a.turma_grau || a.turma?.grau_ano || a.disciplina?.classe || 'Geral').trim();
    if (!porClasse[classe]) {
      const maxClasse = (p.carga_maxima_por_classe && p.carga_maxima_por_classe[classe])
        ? Number(p.carga_maxima_por_classe[classe])
        : maxNormal;
      porClasse[classe] = {
        classe,
        cargaAlocada: 0,
        cargaMaxima: maxClasse,
        turmas: []
      };
    }
    porClasse[classe].cargaAlocada += ch;
    porClasse[classe].turmas.push({
      alocacaoId: a.id,
      turmaNome: a.turma_nome || a.turma?.nome || 'Turma',
      turmaArea: a.turma_area || a.turma?.area || 'Geral',
      disciplinaNome: a.disciplina_nome || a.disciplina?.nome || 'Disciplina',
      cargaHoraria: ch
    });
  });

  Object.values(porClasse).forEach(cData => {
    cData.horasNormais = Math.min(cData.cargaAlocada, cData.cargaMaxima);
    cData.horasExtras = Math.max(0, cData.cargaAlocada - cData.cargaMaxima);
  });

  const horasNormais = Math.min(totalAlocada, maxNormal);
  const horasExtras = Math.max(0, totalAlocada - maxNormal);

  return {
    totalAlocada,
    maxNormal,
    horasNormais,
    horasExtras,
    porClasse
  };
}

function professorPertenceClasse(p, classe) {
  if (!p || !p.alocacoes || p.alocacoes.length === 0) return false;
  return p.alocacoes.some(a => {
    const g = a.turma_grau || a.turma?.grau_ano || a.disciplina?.classe;
    return g && normalizarClasse(g) === normalizarClasse(classe);
  });
}

function renderizarBotoesClassesProfessores() {
  const selectClasse = document.getElementById('selectFiltroProfessorClasse');
  const profs = state.todosProfessores || [];
  const classes = obterClassesDocentes();
  const totalGeral = profs.length;
  const semClasseCount = profs.filter(p => !p.alocacoes || p.alocacoes.length === 0).length;

  if (!state.filtroProfessorClasse) {
    state.filtroProfessorClasse = 'TODAS';
  }

  const contagemEl = document.getElementById('contagemClassesProfessores');
  if (contagemEl) {
    contagemEl.textContent = `${classes.length} classe(s)`;
  }

  if (selectClasse) {
    let htmlOptions = `<option value="TODAS">Todos os Docentes (${totalGeral})</option>`;
    if (semClasseCount > 0) {
      htmlOptions += `<option value="SEM_CLASSE">⚠️ Sem Classe Alocada (${semClasseCount})</option>`;
    }
    classes.forEach(cls => {
      const totalNaClasse = profs.filter(p => professorPertenceClasse(p, cls)).length;
      htmlOptions += `<option value="${cls}">${cls} (${totalNaClasse} docentes)</option>`;
    });
    selectClasse.innerHTML = htmlOptions;
    selectClasse.value = state.filtroProfessorClasse;
  }

  selecionarClasseProfessores(state.filtroProfessorClasse, false);
}

function selecionarClasseProfessores(classe, syncSelect = true) {
  state.filtroProfessorClasse = classe;

  const selectClasse = document.getElementById('selectFiltroProfessorClasse');
  if (selectClasse && syncSelect && selectClasse.value !== classe) {
    selectClasse.value = classe;
  }

  const profs = state.todosProfessores || [];
  let filtrados = profs;
  let labelTexto = 'Todos os Professores';

  if (classe === 'SEM_CLASSE') {
    labelTexto = 'Docentes Sem Turma / Classe Atribuída';
    filtrados = profs.filter(p => !p.alocacoes || p.alocacoes.length === 0);
  } else if (classe !== 'TODAS') {
    labelTexto = `Docentes da ${classe}`;
    filtrados = profs.filter(p => professorPertenceClasse(p, classe));
  }

  const badge = document.getElementById('badgeCaminhoProfessores');
  if (badge) {
    badge.innerHTML = `<i class="bi bi-mortarboard me-1"></i> ${labelTexto} (${filtrados.length} Docentes)`;
  }

  const contagem = document.getElementById('contagemProfessoresExibidos');
  if (contagem) {
    contagem.textContent = `${filtrados.length} docente(s) listado(s)`;
  }

  state.professoresFiltradosAtuais = filtrados;
  renderizarTabelaProfessores(filtrados);
}

function filtrarProfessoresTabela() {
  const termo = (document.getElementById('pesquisaProfessores')?.value || '').toLowerCase().trim();
  let base = state.professoresFiltradosAtuais || state.todosProfessores || [];

  if (termo) {
    let filtrados = base.filter(p => 
      (p.codigo || '').toLowerCase().includes(termo) ||
      (p.nome || '').toLowerCase().includes(termo) ||
      (p.apelido || '').toLowerCase().includes(termo) ||
      (p.email || '').toLowerCase().includes(termo) ||
      (p.especialidade || '').toLowerCase().includes(termo) ||
      (p.carreira || '').toLowerCase().includes(termo) ||
      (p.alocacoes || []).some(a => 
        (a.turma_nome || '').toLowerCase().includes(termo) ||
        (a.turma_grau || '').toLowerCase().includes(termo) ||
        (a.disciplina_nome || '').toLowerCase().includes(termo)
      )
    );

    if (filtrados.length === 0) {
      filtrados = (state.todosProfessores || []).filter(p => 
        (p.codigo || '').toLowerCase().includes(termo) ||
        (p.nome || '').toLowerCase().includes(termo) ||
        (p.apelido || '').toLowerCase().includes(termo) ||
        (p.email || '').toLowerCase().includes(termo) ||
        (p.especialidade || '').toLowerCase().includes(termo)
      );
    }

    renderizarTabelaProfessores(filtrados);
    const contagem = document.getElementById('contagemProfessoresExibidos');
    if (contagem) contagem.textContent = `${filtrados.length} docente(s) encontrado(s) para "${termo}"`;
  } else {
    renderizarTabelaProfessores(base);
    const contagem = document.getElementById('contagemProfessoresExibidos');
    if (contagem) contagem.textContent = `${base.length} docente(s) listado(s)`;
  }
}

function limparFiltrosProfessores() {
  state.filtroProfessorClasse = 'TODAS';
  const inp = document.getElementById('pesquisaProfessores');
  if (inp) inp.value = '';
  const sel = document.getElementById('selectFiltroProfessorClasse');
  if (sel) sel.value = 'TODAS';
  selecionarClasseProfessores('TODAS');
}

function renderizarTabelaProfessores(profs) {
  const tbody = document.getElementById('tabelaProfessores');
  if (!tbody) return;

  if (!profs || profs.length === 0) {
    const semClasseCount = (state.todosProfessores || []).filter(p => !p.alocacoes || p.alocacoes.length === 0).length;
    let dicaExtra = '';
    if (semClasseCount > 0 && state.filtroProfessorClasse !== 'SEM_CLASSE' && state.filtroProfessorClasse !== 'TODAS') {
      dicaExtra = `<div class="mt-2"><span class="badge bg-warning text-dark p-2" role="button" onclick="selecionarClasseProfessores('SEM_CLASSE')"><i class="bi bi-info-circle me-1"></i> Esta escola possui ${semClasseCount} docente(s) sem turma/classe atribuída. Clique aqui para ver e atribuir turmas.</span></div>`;
    }
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted"><i class="bi bi-info-circle me-1"></i> Nenhum docente encontrado para a selecção actual.${dicaExtra}</td></tr>`;
    return;
  }

  const todasTurmas = state.todasTurmas || [];

  tbody.innerHTML = profs.map(p => {
    const nomeCompleto = `${p.nome || ''} ${p.apelido || ''}`.trim();
    const turmasDT = todasTurmas.filter(t => String(t.director_turma_id || t.director_turma) === String(p.id));
    const turmasDC = todasTurmas.filter(t => String(t.director_classe_id || t.director_classe) === String(p.id));

    let cargosBadges = '';
    turmasDT.forEach(t => {
      if (t.homologado_dt && t.codigo_director_turma) {
        cargosBadges += `<span class="badge bg-success bg-opacity-10 text-success border border-success font-monospace me-1 mt-1" style="font-size:0.7rem;" title="Director de Turma Homologado (${t.nome})"><i class="bi bi-patch-check-fill me-1"></i>${t.codigo_director_turma}</span>`;
      } else {
        cargosBadges += `<span class="badge bg-warning text-dark font-monospace me-1 mt-1" style="font-size:0.7rem;" title="Indicado DT (${t.nome}) - Pendente Homologação GD">DT Pendente (${t.nome})</span>`;
      }
    });
    const dcCodigosVistos = new Set();
    turmasDC.forEach(t => {
      const chave = t.codigo_director_classe || t.grau_ano;
      if (dcCodigosVistos.has(chave)) return;
      dcCodigosVistos.add(chave);
      if (t.homologado_dc && t.codigo_director_classe) {
        cargosBadges += `<span class="badge bg-info bg-opacity-10 text-dark border border-info font-monospace me-1 mt-1" style="font-size:0.7rem;" title="Director de Classe Homologado (${t.grau_ano})"><i class="bi bi-patch-check-fill text-primary me-1"></i>${t.codigo_director_classe}</span>`;
      } else {
        cargosBadges += `<span class="badge bg-warning text-dark font-monospace me-1 mt-1" style="font-size:0.7rem;" title="Indicado DC (${t.grau_ano}) - Pendente Homologação GD">DC Pendente (${t.grau_ano})</span>`;
      }
    });

    const alocacoesHtml = (p.alocacoes && p.alocacoes.length > 0)
      ? p.alocacoes.map(a => {
          const classeTurma = a.turma_grau || a.turma?.grau_ano || '';
          const nomeTurma = a.turma_nome || a.turma?.nome || 'Turma';
          const nomeDisc = a.disciplina_nome || a.disciplina?.nome || 'Disciplina';
          return `
            <span class="badge border bg-light text-dark d-inline-flex align-items-center gap-1 mb-1 me-1 p-1 px-2" style="font-size: 0.8rem;" title="${classeTurma} &rarr; ${nomeTurma}: ${nomeDisc}">
              <span class="badge bg-primary bg-opacity-25 text-primary border me-1" style="font-size: 0.7rem;">${classeTurma || 'Classe'}</span>
              <strong>${nomeTurma}</strong> <span class="text-muted">(${nomeDisc})</span>
              <a href="javascript:void(0)" onclick="modalEditarAlocacao('${a.id}', '${p.id}')" class="text-primary ms-1" title="Editar Turma/Disciplina Alocada"><i class="bi bi-pencil-fill" style="font-size: 10px;"></i></a>
              <a href="javascript:void(0)" onclick="eliminarAlocacao('${a.id}', '${p.id}')" class="text-danger" title="Eliminar Alocação"><i class="bi bi-x-circle-fill" style="font-size: 11px;"></i></a>
            </span>
          `;
        }).join('')
      : '<span class="badge bg-warning bg-opacity-25 text-dark border border-warning">Nenhuma turma alocada</span>';

    const metricas = calcularMetricasCargaProfessor(p);
    let cargaBadgeHtml = '';
    if (metricas.totalAlocada === 0) {
      cargaBadgeHtml = `
        <span class="badge bg-light text-muted border">0h / semana</span>
        <div class="small text-muted" style="font-size: 0.72rem;">Máx: ${metricas.maxNormal}h normal</div>
      `;
    } else if (metricas.horasExtras === 0) {
      cargaBadgeHtml = `
        <span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25 fw-semibold" style="font-size: 0.85rem;">
          <i class="bi bi-check-circle-fill me-1"></i>${metricas.totalAlocada}h / semana
        </span>
        <div class="small text-muted mt-1" style="font-size: 0.72rem;">100% Normal (Máx: ${metricas.maxNormal}h)</div>
      `;
    } else {
      cargaBadgeHtml = `
        <span class="badge bg-warning text-dark border border-warning fw-bold" style="font-size: 0.85rem;" title="Transbordo de Carga Máxima">
          <i class="bi bi-exclamation-triangle-fill me-1 text-danger"></i>${metricas.totalAlocada}h / semana
        </span>
        <div class="d-flex flex-wrap gap-1 mt-1">
          <span class="badge bg-success bg-opacity-75" style="font-size: 0.7rem;" title="Carga horária contratual normal">${metricas.horasNormais}h Normal</span>
          <span class="badge bg-danger text-white fw-bold" style="font-size: 0.7rem;" title="Horas extras semanais suplementares">+${metricas.horasExtras}h Extras</span>
        </div>
      `;
    }

    return `
      <tr>
        <td>
          <div class="d-flex align-items-center gap-2">
            <div class="rounded-circle bg-primary bg-opacity-10 text-primary fw-bold d-flex align-items-center justify-content-center" style="width: 36px; height: 36px; font-size: 0.85rem;">
              ${(p.nome || 'P').charAt(0).toUpperCase()}
            </div>
            <div>
              <div class="d-flex align-items-center gap-1 flex-wrap">
                <strong class="text-primary">${nomeCompleto}</strong>
                <span class="badge bg-dark text-white font-monospace" style="font-size: 0.72rem;" title="Código Fixo Oficial do Professor (imutável entre turmas/classes)">${p.codigo || 'PR-FIXO'}</span>
              </div>
              <div class="small text-muted">${p.especialidade || 'Área Geral'}</div>
              ${cargosBadges ? `<div class="d-flex flex-wrap">${cargosBadges}</div>` : ''}
            </div>
          </div>
        </td>
        <td>
          <small class="d-block"><i class="bi bi-envelope me-1 text-muted"></i>${p.email}</small>
          <small class="text-muted"><i class="bi bi-telephone me-1 text-muted"></i>${p.telefone || '-'}</small>
        </td>
        <td>
          <span class="badge bg-light text-dark border fw-semibold">${p.carreira || 'Licenciado'}</span>
          <div class="small text-muted mt-1">${p.ativo !== false ? '<span class="text-success"><i class="bi bi-check-circle-fill me-1"></i>Activo</span>' : '<span class="text-secondary">Inactivo</span>'}</div>
        </td>
        <td><small>${p.distrito || '-'}<br><span class="text-muted">${p.provincia || '-'}</span></small></td>
        <td>${cargaBadgeHtml}</td>
        <td>
          <div class="d-flex flex-wrap align-items-center">
            ${alocacoesHtml}
            <button class="btn btn-link btn-sm p-0 ms-1 text-decoration-none" onclick="modalAlocarProfessor('${p.id}')" title="Alocar nova turma ou classe a este docente">
              <i class="bi bi-plus-circle-fill text-success" style="font-size: 15px;"></i>
            </button>
          </div>
        </td>
        <td class="text-end">
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-primary" onclick="modalEditarProfessor('${p.id}')" title="Editar Dados Cadastrais e Carreira">
              <i class="bi bi-pencil-square me-1"></i>Editar
            </button>
            <button class="btn btn-outline-warning text-dark" onclick="modalTransferirProfessor('${p.id}')" title="Transferir ou Atribuir Nova Classe a este Docente">
              <i class="bi bi-arrow-left-right me-1"></i>Transferir Classe
            </button>
            <button class="btn btn-outline-danger" onclick="excluirProfessor('${p.id}')" title="Eliminar Docente do Quadro">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function modalNovoProfessor() {
  const optCarreiras = (state.geografia.carreiras || ['DN1', 'DN2', 'DN3', 'DN4', 'N1', 'N2', 'N3', 'N4', 'Licenciado', 'Mestre', 'Especialista de Educação']).map(c => `<option value="${c}">${c}</option>`).join('');
  const optProvincias = (state.geografia.provincias || []).map(p => `<option value="${p}">${p}</option>`).join('');

  // Classes disponíveis
  const classesDisponiveis = obterClassesDocentes();
  const checkboxesClassesHtml = classesDisponiveis.length > 0
    ? classesDisponiveis.map(cls => `
      <div class="form-check form-check-inline">
        <input class="form-check-input check-classe-novo-prof" type="checkbox" value="${cls}" id="chkCls_${cls.replace(/\s+/g, '')}" onchange="aoMudarClassesModalNovoProf()">
        <label class="form-check-label small fw-semibold" for="chkCls_${cls.replace(/\s+/g, '')}">${cls}</label>
      </div>
    `).join('')
    : '<span class="text-muted small fst-italic">Nenhuma classe ou nível cadastrado nesta instituição ainda.</span>';

  // Disciplinas disponíveis
  const disciplinas = state.todasDisciplinas || [];
  const optDisciplinas = disciplinas.length > 0 
    ? disciplinas.map(d => `<option value="${d.id}">${d.nome} ${d.classe ? `(${d.classe})` : ''}</option>`).join('')
    : '<option value="">Nenhuma disciplina cadastrada</option>';

  const codEsc = state.escolaInfo?.codigo_escola || state.user?.escola?.codigo_escola || '0101S0001';
  const proxSeq = String((state.todosProfessores?.length || 0) + 1).padStart(3, '0');

  abrirModal('Cadastrar Docente & Atribuição de Classes', `
    <form id="formModalProf">
      <div class="row g-3">
        <div class="col-12">
          <div class="p-2 px-3 rounded bg-dark bg-opacity-10 border d-flex justify-content-between align-items-center">
            <span class="small fw-semibold"><i class="bi bi-lock-fill me-1 text-primary"></i>Código Fixo Oficial do Professor (gerado automaticamente e imutável):</span>
            <span class="badge bg-dark text-white font-monospace px-3 py-2">PR${codEsc}.${proxSeq}</span>
          </div>
        </div>
        <div class="col-md-7">
          <label class="form-label small fw-semibold">Nome Completo</label>
          <input type="text" id="mpNome" class="form-control" required placeholder="Prof. Nome Próprio">
        </div>
        <div class="col-md-5">
          <label class="form-label small fw-semibold">Apelido</label>
          <input type="text" id="mpApelido" class="form-control" placeholder="Apelido do docente">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">E-mail Institucional</label>
          <input type="email" id="mpEmail" class="form-control" required placeholder="professor@escola.edu.mz">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Telefone (+258 Padrão)</label>
          <input type="text" id="mpTel" class="form-control" value="+258 ">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Carreira Docente (Quadro Oficial)</label>
          <select id="mpCarreira" class="form-select">${optCarreiras}</select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Especialidade / Área de Formação</label>
          <input type="text" id="mpEsp" class="form-control" placeholder="Ex: Matemática e Física">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Província</label>
          <select id="mpProvincia" class="form-select" onchange="atualizarDistritosProfessor(this.value)">
            <option value="">Selecione a Província</option>
            ${optProvincias}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Distrito</label>
          <select id="mpDistrito" class="form-select">
            <option value="">Selecione primeiro a província</option>
          </select>
        </div>

        <div class="col-md-12">
          <label class="form-label small fw-semibold">Carga Horária Semanal (Horas)</label>
          <input type="number" id="mpCarga" class="form-control" value="20" required min="1" max="60">
        </div>

        <!-- Secção de Atribuição Sequencial: Classe(s) -> Turma(s) -->
        <div class="col-12 mt-3">
          <div class="p-3 bg-light rounded border border-primary border-opacity-25">
            <h6 class="fw-bold text-primary mb-1"><i class="bi bi-mortarboard-fill me-1"></i> Atribuição Sequencial: Classe(s) & Turma(s)</h6>
            <p class="text-muted small mb-2">Pode seleccionar <strong>1 ou 2 classes</strong> para atribuir ao professor. Em seguida, marque as turmas correspondentes:</p>
            
            <div class="mb-3">
              <label class="form-label small fw-bold text-dark mb-1">Passo 1: Seleccione a(s) Classe(s) do Docente:</label>
              <div class="p-2 bg-white rounded border">
                ${checkboxesClassesHtml}
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label small fw-bold text-dark mb-1">Passo 2: Turmas Disponíveis nas Classes Seleccionadas:</label>
              <div id="containerTurmasNovoProf" class="p-2 bg-white rounded border" style="min-height: 50px;">
                <span class="text-muted small"><i class="bi bi-info-circle me-1"></i> Marque uma ou duas classes no Passo 1 para exibir as turmas disponíveis para alocação.</span>
              </div>
            </div>

            <div>
              <label class="form-label small fw-bold text-dark mb-1">Passo 3: Disciplina Curricular a Ministrar:</label>
              <select id="mpDisciplinaInicial" class="form-select">
                <option value="">Selecione a Disciplina Curricular...</option>
                ${optDisciplinas}
              </select>
            </div>
          </div>
        </div>
      </div>
      <div class="d-flex justify-content-end gap-2 mt-4">
        <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
        <button type="submit" class="btn btn-primary btn-sm px-4">Cadastrar Docente & Alocar</button>
      </div>
    </form>
  `);

  window.aoMudarClassesModalNovoProf = function() {
    const checks = document.querySelectorAll('.check-classe-novo-prof:checked');
    const classesSelecionadas = Array.from(checks).map(c => c.value);
    const containerTurmas = document.getElementById('containerTurmasNovoProf');
    if (!containerTurmas) return;

    if (classesSelecionadas.length === 0) {
      containerTurmas.innerHTML = `<span class="text-muted small"><i class="bi bi-info-circle me-1"></i> Marque uma ou duas classes no Passo 1 para exibir as turmas disponíveis para alocação.</span>`;
      return;
    }

    const turmas = (state.todasTurmas || []).filter(t => 
      classesSelecionadas.some(cls => normalizarClasse(t.grau_ano) === normalizarClasse(cls))
    );

    if (turmas.length === 0) {
      containerTurmas.innerHTML = `<span class="text-warning small"><i class="bi bi-exclamation-triangle me-1"></i> Nenhuma turma cadastrada para as classes seleccionadas (${classesSelecionadas.join(', ')}). Pode cadastrar o docente e criar turmas posteriormente.</span>`;
      return;
    }

    let turmasHtml = `<div class="d-flex flex-wrap gap-3">`;
    classesSelecionadas.forEach(cls => {
      const turmasDestaClasse = turmas.filter(t => normalizarClasse(t.grau_ano) === normalizarClasse(cls));
      turmasHtml += `<div class="p-2 border rounded bg-light" style="flex: 1; min-width: 200px;">
        <strong class="d-block text-primary small mb-1 border-bottom pb-1"><i class="bi bi-mortarboard me-1"></i>${cls}:</strong>`;
      if (turmasDestaClasse.length === 0) {
        turmasHtml += `<span class="text-muted small">Sem turmas</span>`;
      } else {
        turmasDestaClasse.forEach(t => {
          turmasHtml += `
            <div class="form-check">
              <input class="form-check-input check-turma-alocar-prof" type="checkbox" value="${t.id}" id="chkTrm_${t.id}">
              <label class="form-check-label small" for="chkTrm_${t.id}">
                <strong>${t.nome}</strong> ${t.area ? `<span class="text-muted">(${t.area})</span>` : ''}
              </label>
            </div>
          `;
        });
      }
      turmasHtml += `</div>`;
    });
    turmasHtml += `</div>`;
    containerTurmas.innerHTML = turmasHtml;
  };

  document.getElementById('formModalProf').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const body = {
        nome: document.getElementById('mpNome').value,
        apelido: document.getElementById('mpApelido').value || undefined,
        email: document.getElementById('mpEmail').value,
        telefone: document.getElementById('mpTel').value || undefined,
        carreira: document.getElementById('mpCarreira').value,
        especialidade: document.getElementById('mpEsp').value || undefined,
        provincia: document.getElementById('mpProvincia').value || undefined,
        distrito: document.getElementById('mpDistrito').value || undefined,
        carga_horaria_semanal: Number(document.getElementById('mpCarga').value)
      };
      const res = await apiFetch('/api/v1/professores', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success && res.data?.id) {
        const novoProfId = res.data.id;
        const checksTurmas = document.querySelectorAll('.check-turma-alocar-prof:checked');
        const discId = document.getElementById('mpDisciplinaInicial')?.value;

        if (checksTurmas.length > 0 && discId) {
          const promessasAlocacao = Array.from(checksTurmas).map(chk => {
            return apiFetch('/api/v1/professores/alocar', {
              method: 'POST',
              body: JSON.stringify({
                professor_id: novoProfId,
                turma_id: chk.value,
                disciplina_id: discId
              })
            });
          });
          await Promise.all(promessasAlocacao);
          mostrarNotificacao('Docente cadastrado e alocado à(s) turma(s) com sucesso!', 'success');
        } else {
          mostrarNotificacao('Docente cadastrado com sucesso!', 'success');
        }

        fecharModal();
        carregarProfessores();
      } else {
        alert(res.message || 'Erro ao cadastrar docente');
      }
    } catch (err) {
      alert('Erro ao cadastrar docente: ' + (err.message || 'Erro no servidor'));
    }
  });
}

function atualizarDistritosProfessor(provincia, distritoSelecionado = '', selectId = 'mpDistrito') {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById(selectId);
  if (select) {
    select.innerHTML = distritos.map(d => `<option value="${d}" ${d === distritoSelecionado ? 'selected' : ''}>${d}</option>`).join('');
  }
}

async function modalEditarProfessor(profId) {
  try {
    let p = (state.todosProfessores || []).find(x => String(x.id) === String(profId));
    try {
      const res = await apiFetch(`/api/v1/professores/${profId}`);
      if (res && res.success && res.data) {
        p = res.data;
      } else if (res && (res.id || res.nome)) {
        p = res;
      }
    } catch (apiErr) {
      console.warn('Usando dados de professor em cache local:', apiErr);
    }

    if (!p) return alert('Falha ao obter dados do professor');

    const carreirasPadrao = ['DN1', 'DN2', 'DN3', 'DN4', 'N1', 'N2', 'N3', 'N4', 'Especialista de Educação', 'Mestre', 'Professor Doutor', 'Licenciado', 'Bacharel'];
    const carreiras = (state.geografia.carreiras && state.geografia.carreiras.length) ? state.geografia.carreiras : carreirasPadrao;
    const optCarreiras = carreiras.map(c => `<option value="${c}" ${c === p.carreira ? 'selected' : ''}>${c}</option>`).join('');

    const provincias = state.geografia.provincias || ['Maputo Cidade', 'Maputo Província', 'Gaza', 'Inhambane', 'Sofala', 'Manica', 'Tete', 'Zambézia', 'Nampula', 'Cabo Delgado', 'Niassa'];
    const optProvincias = provincias.map(prov => `<option value="${prov}" ${prov === p.provincia ? 'selected' : ''}>${prov}</option>`).join('');

    const alocacoesHtml = (p.alocacoes && p.alocacoes.length > 0)
      ? p.alocacoes.map(a => `
        <div class="d-flex justify-content-between align-items-center p-2 mb-1 bg-white rounded border">
          <div>
            <span class="badge bg-primary me-1">${a.turma_grau || 'Classe'}</span>
            <strong>${a.turma_nome || a.turma?.nome}</strong> &rarr; <span class="text-muted">${a.disciplina_nome || a.disciplina?.nome}</span>
          </div>
          <button type="button" class="btn btn-outline-danger btn-sm py-0 px-2" onclick="eliminarAlocacao('${a.id}', '${p.id}')" title="Desvincular esta turma">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      `).join('')
      : '<span class="text-muted small">Nenhuma turma alocada até ao momento.</span>';

    abrirModal(`Editar Docente: ${p.nome}`, `
      <form id="formModalEditarProf">
        <div class="row g-3">
          <div class="col-12">
            <div class="p-2 px-3 rounded bg-dark bg-opacity-10 border d-flex justify-content-between align-items-center">
              <span class="small fw-semibold"><i class="bi bi-lock-fill me-1 text-primary"></i>Código Fixo Oficial do Professor (Imutável):</span>
              <span class="badge bg-dark text-white font-monospace px-3 py-2">${p.codigo || 'PR-FIXO'}</span>
            </div>
          </div>
          <div class="col-md-7">
            <label class="form-label small fw-semibold">Nome Completo</label>
            <input type="text" id="mpeNome" class="form-control" required value="${p.nome || ''}">
          </div>
          <div class="col-md-5">
            <label class="form-label small fw-semibold">Apelido</label>
            <input type="text" id="mpeApelido" class="form-control" value="${p.apelido || ''}">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">E-mail Institucional</label>
            <input type="email" id="mpeEmail" class="form-control" required value="${p.email || ''}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Telefone</label>
            <input type="text" id="mpeTel" class="form-control" value="${p.telefone || ''}">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold text-primary">Carreira Docente (Quadro Oficial)</label>
            <select id="mpeCarreira" class="form-select">${optCarreiras}</select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Especialidade / Disciplina</label>
            <input type="text" id="mpeEsp" class="form-control" value="${p.especialidade || ''}">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Província</label>
            <select id="mpeProvincia" class="form-select" onchange="atualizarDistritosProfessor(this.value, '', 'mpeDistrito')">
              <option value="">Selecione a Província</option>
              ${optProvincias}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Distrito</label>
            <select id="mpeDistrito" class="form-select"></select>
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Carga Horária Semanal (Horas)</label>
            <input type="number" id="mpeCarga" class="form-control" value="${p.carga_horaria_semanal || 20}" required min="1" max="60">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Estado do Docente</label>
            <select id="mpeAtivo" class="form-select">
              <option value="true" ${p.ativo !== false ? 'selected' : ''}>Activo no Quadro</option>
              <option value="false" ${p.ativo === false ? 'selected' : ''}>Inactivo / Licença</option>
            </select>
          </div>

          <!-- Carga Horária Normal Máxima por Classe -->
          <div class="col-12 mt-2">
            <div class="p-3 bg-light rounded border">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <h6 class="fw-bold text-primary mb-0"><i class="bi bi-speedometer2 me-1"></i> Carga Horária Normal Máxima por Classe</h6>
                <span class="badge bg-primary bg-opacity-10 text-primary small">Contrato & Limites</span>
              </div>
              <div class="small text-muted mb-2" style="font-size: 0.78rem;">
                Defina o teto normal de aulas semanais para cada classe lecionada. Aulas atribuídas acima destes valores serão contabilizadas automaticamente como <strong>Horas Extras</strong>.
              </div>
              <div class="row g-2">
                ${(() => {
                  const classesEdicao = Array.from(new Set([
                    ...obterClassesDocentes(),
                    ...Object.keys(p.carga_maxima_por_classe || {}),
                    ...(p.alocacoes || []).map(a => a.turma_grau || a.turma?.grau_ano || a.disciplina?.classe).filter(Boolean)
                  ])).sort((a, b) => (parseInt(a.replace(/\D/g, '')) || 0) - (parseInt(b.replace(/\D/g, '')) || 0));

                  if (classesEdicao.length === 0) {
                    return `<div class="col-12 text-muted small fst-italic py-2"><i class="bi bi-info-circle me-1"></i>Nenhuma classe ou nível cadastrado nesta instituição ainda. Cadastre turmas ou disciplinas primeiro.</div>`;
                  }

                  return classesEdicao.map(c => {
                    const val = (p.carga_maxima_por_classe && p.carga_maxima_por_classe[c])
                      ? p.carga_maxima_por_classe[c]
                      : (p.carga_horaria_semanal || 16);
                    return `
                      <div class="col-md-4 col-sm-6">
                        <label class="form-label small fw-semibold mb-1"><i class="bi bi-mortarboard me-1 text-primary"></i>${c}</label>
                        <div class="input-group input-group-sm">
                          <input type="number" class="form-control mpeCargaClasseItem text-center fw-bold" data-classe="${c}" value="${val}" min="1" max="40">
                          <span class="input-group-text bg-white">h/sem</span>
                        </div>
                      </div>
                    `;
                  }).join('');
                })()}
              </div>
            </div>
          </div>

          <!-- Turmas e Classes Actuais do Docente -->
          <div class="col-12 mt-2">
            <div class="p-3 bg-light rounded border">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="fw-bold text-primary mb-0"><i class="bi bi-collection-fill me-1"></i> Classes & Turmas Alocadas</h6>
                <button type="button" class="btn btn-outline-primary btn-sm py-0 px-2" onclick="fecharModal(); modalAlocarProfessor('${p.id}');">
                  <i class="bi bi-plus-lg me-1"></i>Atribuir Nova Turma
                </button>
              </div>
              <div id="containerAlocacoesEditarProf">
                ${alocacoesHtml}
              </div>
            </div>
          </div>
        </div>
        <div class="d-flex gap-2 justify-content-between align-items-center mt-4 pt-2 border-top">
          <button type="button" class="btn btn-outline-danger btn-sm" onclick="fecharModal(); excluirProfessor('${p.id}');">
            <i class="bi bi-trash me-1"></i>Eliminar Docente
          </button>
          <div class="d-flex gap-2">
            <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
            <button type="submit" class="btn btn-primary btn-sm px-4">Salvar Alterações</button>
          </div>
        </div>
      </form>
    `);

    if (p.provincia) {
      atualizarDistritosProfessor(p.provincia, p.distrito || '', 'mpeDistrito');
    }

    document.getElementById('formModalEditarProf').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const cargasMap = {};
        document.querySelectorAll('.mpeCargaClasseItem').forEach(inp => {
          const c = inp.getAttribute('data-classe');
          const val = Number(inp.value);
          if (c && val > 0) cargasMap[c] = val;
        });

        const body = {
          nome: document.getElementById('mpeNome').value,
          apelido: document.getElementById('mpeApelido').value || null,
          email: document.getElementById('mpeEmail').value,
          telefone: document.getElementById('mpeTel').value || null,
          carreira: document.getElementById('mpeCarreira').value,
          especialidade: document.getElementById('mpeEsp').value || null,
          provincia: document.getElementById('mpeProvincia').value || null,
          distrito: document.getElementById('mpeDistrito').value || null,
          carga_horaria_semanal: Number(document.getElementById('mpeCarga').value),
          carga_maxima_por_classe: cargasMap,
          ativo: document.getElementById('mpeAtivo').value === 'true'
        };
        const updateRes = await apiFetch(`/api/v1/professores/${profId}`, {
          method: 'PUT',
          body: JSON.stringify(body)
        });
        if (updateRes.success) {
          mostrarNotificacao('Dados do docente actualizados com sucesso!', 'success');
          fecharModal();
          carregarProfessores();
        } else {
          alert(updateRes.message || 'Erro ao actualizar dados do professor');
        }
      } catch (err) {
        alert(err.message || 'Erro ao actualizar dados do professor');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados do professor: ' + err.message);
  }
}

async function modalAlocarProfessor(professorIdPadrao = '') {
  const [profsRes, turmasRes, discRes] = await Promise.all([
    apiFetch('/api/v1/professores'),
    apiFetch('/api/v1/escola-admin/turmas'),
    apiFetch('/api/v1/disciplinas')
  ]);

  const profs = profsRes.data || state.todosProfessores || [];
  const turmas = turmasRes.data || state.todasTurmas || [];
  const disciplinas = discRes.data || state.todasDisciplinas || [];

  state.todosProfessores = profs;
  state.todasTurmas = turmas;
  state.todasDisciplinas = disciplinas;

  const optProfs = profs.map(p => 
    `<option value="${p.id}" ${p.id === professorIdPadrao ? 'selected' : ''}>${p.nome} ${p.apelido || ''} (${p.especialidade || 'Docente'})</option>`
  ).join('');

  // Obter classes distintas das turmas
  const classesSet = new Set();
  turmas.forEach(t => { if (t.grau_ano) classesSet.add(t.grau_ano.trim()); });
  disciplinas.forEach(d => { if (d.classe) classesSet.add(d.classe.trim()); });
  const classesList = Array.from(classesSet).sort((a, b) => (parseInt(a.replace(/\D/g, '')) || 0) - (parseInt(b.replace(/\D/g, '')) || 0));

  const optClasses = classesList.length > 0
    ? classesList.map(c => `<option value="${c}">${c}</option>`).join('')
    : '<option value="" disabled>-- Nenhuma classe/nível cadastrado nesta instituição --</option>';

  abrirModal('Atribuir Turma & Carga Horária Docente', `
    <form id="formModalAloc">
      <div class="mb-3">
        <label class="form-label small fw-semibold">1. Professor / Docente *</label>
        <select id="malocProf" class="form-select fw-semibold" required onchange="aoMudarProfessorModalAlocar()">${optProfs}</select>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-md-7">
          <label class="form-label small fw-semibold text-primary"><i class="bi bi-mortarboard-fill me-1"></i> 2. Seleccione a Classe / Grau *</label>
          <select id="malocClasse" class="form-select border-primary fw-semibold" required onchange="aoMudarClasseModalAlocar()">
            <option value="">Selecione a Classe...</option>
            ${optClasses}
          </select>
          <small class="text-muted" style="font-size: 0.72rem;">Filtra automaticamente turmas de todas as secções e disciplinas.</small>
        </div>
        <div class="col-md-5">
          <label class="form-label small fw-semibold text-info"><i class="bi bi-speedometer2 me-1"></i> Carga Normal Máx. nesta Classe</label>
          <div class="input-group input-group-sm">
            <input type="number" id="malocCargaMaxClasse" class="form-control fw-bold border-info text-center" value="16" min="1" max="40" oninput="aoAtualizarCalculoCargaAlocar()">
            <span class="input-group-text bg-info bg-opacity-10 text-info fw-bold">h/sem</span>
          </div>
          <small class="text-muted" style="font-size: 0.7rem;">Teto contratual normal do docente para esta classe.</small>
        </div>
      </div>

      <div class="mb-3">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <label class="form-label small fw-semibold text-primary mb-0"><i class="bi bi-collection-fill me-1"></i> 3. Turma da Classe Seleccionada *</label>
          <span class="badge bg-light text-secondary border small" style="font-size: 0.7rem;">Mesma secção ou secções diferentes</span>
        </div>
        <select id="malocTurma" class="form-select border-primary" required onchange="aoAtualizarCalculoCargaAlocar()">
          <option value="">Selecione primeiro a classe acima...</option>
        </select>
      </div>

      <div class="mb-3">
        <label class="form-label small fw-semibold text-primary"><i class="bi bi-book-fill me-1"></i> 4. Disciplina Curricular *</label>
        <select id="malocDisc" class="form-select border-primary" required onchange="aoAtualizarCalculoCargaAlocar()">
          <option value="">Selecione a disciplina curricular...</option>
        </select>
      </div>

      <!-- Painel Dinâmico de Cálculo Automático e Transbordo de Horas Extras -->
      <div id="painelAnaliseCargaDocente" class="mt-3"></div>

      <div class="d-flex gap-2 justify-content-end mt-4 pt-2 border-top">
        <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
        <button type="submit" id="btnConfirmarAlocacao" class="btn btn-primary btn-sm px-4 fw-semibold">
          <i class="bi bi-check2-circle me-1"></i> Confirmar Atribuição
        </button>
      </div>
    </form>
  `);

  window.aoMudarProfessorModalAlocar = function() {
    const profId = document.getElementById('malocProf')?.value;
    const selClasse = document.getElementById('malocClasse')?.value;
    const prof = (state.todosProfessores || []).find(p => String(p.id) === String(profId));
    if (prof && selClasse) {
      const maxClasse = (prof.carga_maxima_por_classe && prof.carga_maxima_por_classe[selClasse])
        ? Number(prof.carga_maxima_por_classe[selClasse])
        : (prof.carga_horaria_semanal || 16);
      const inp = document.getElementById('malocCargaMaxClasse');
      if (inp) inp.value = maxClasse;
    }
    aoAtualizarCalculoCargaAlocar();
  };

  window.aoMudarClasseModalAlocar = function() {
    const selClasse = document.getElementById('malocClasse')?.value;
    const profId = document.getElementById('malocProf')?.value;
    const selTurma = document.getElementById('malocTurma');
    const selDisc = document.getElementById('malocDisc');
    const inpMaxClasse = document.getElementById('malocCargaMaxClasse');
    if (!selTurma || !selDisc) return;

    if (!selClasse) {
      selTurma.innerHTML = '<option value="">Selecione primeiro a classe acima...</option>';
      selDisc.innerHTML = '<option value="">Selecione primeiro a classe acima...</option>';
      aoAtualizarCalculoCargaAlocar();
      return;
    }

    // Carregar limite contratual do professor para esta classe
    const prof = (state.todosProfessores || []).find(p => String(p.id) === String(profId));
    if (prof && inpMaxClasse) {
      const maxClasse = (prof.carga_maxima_por_classe && prof.carga_maxima_por_classe[selClasse])
        ? Number(prof.carga_maxima_por_classe[selClasse])
        : (prof.carga_horaria_semanal || 16);
      inpMaxClasse.value = maxClasse;
    }

    // Filtrar turmas da classe seleccionada (permite qualquer secção ou área)
    const turmasFiltradas = (state.todasTurmas || []).filter(t => 
      normalizarClasse(t.grau_ano) === normalizarClasse(selClasse)
    );

    if (turmasFiltradas.length === 0) {
      selTurma.innerHTML = `<option value="">Nenhuma turma cadastrada para ${selClasse}</option>`;
    } else {
      selTurma.innerHTML = '<option value="">Selecione a Turma...</option>' + 
        turmasFiltradas.map(t => {
          const areaLabel = t.area ? `Secção: ${t.area}` : 'Geral';
          const turnoLabel = t.turno || 'Diurno';
          return `<option value="${t.id}">${t.nome} (${areaLabel} - ${turnoLabel})</option>`;
        }).join('');
    }

    // Filtrar disciplinas da classe
    const discFiltradas = (state.todasDisciplinas || []).filter(d => 
      !d.classe || normalizarClasse(d.classe) === normalizarClasse(selClasse)
    );

    if (discFiltradas.length === 0) {
      selDisc.innerHTML = (state.todasDisciplinas || []).map(d => `<option value="${d.id}">${d.nome} (${d.carga_horaria || 5}h/sem)</option>`).join('');
    } else {
      selDisc.innerHTML = '<option value="">Selecione a Disciplina...</option>' + 
        discFiltradas.map(d => `<option value="${d.id}">${d.nome} (${d.carga_horaria || 5}h/semana${d.area ? ` - ${d.area}` : ''})</option>`).join('');
    }

    aoAtualizarCalculoCargaAlocar();
  };

  window.aoAtualizarCalculoCargaAlocar = function() {
    const profId = document.getElementById('malocProf')?.value;
    const selClasse = document.getElementById('malocClasse')?.value;
    const turmaId = document.getElementById('malocTurma')?.value;
    const discId = document.getElementById('malocDisc')?.value;
    const inputMaxClasse = document.getElementById('malocCargaMaxClasse');
    const container = document.getElementById('painelAnaliseCargaDocente');
    if (!container) return;

    const prof = (state.todosProfessores || []).find(p => String(p.id) === String(profId));
    if (!prof) {
      container.innerHTML = '';
      return;
    }

    const metricas = calcularMetricasCargaProfessor(prof);
    const maxClasse = Number(inputMaxClasse?.value) || (prof.carga_maxima_por_classe?.[selClasse] || prof.carga_horaria_semanal || 16);
    const maxGeral = metricas.maxNormal;

    const cargaClasseAtual = selClasse ? (metricas.porClasse[selClasse]?.cargaAlocada || 0) : 0;
    const cargaGeralAtual = metricas.totalAlocada;

    // Obter carga da disciplina selecionada
    let chNova = 0;
    let discNome = '';
    if (discId) {
      const disc = (state.todasDisciplinas || []).find(d => String(d.id) === String(discId));
      if (disc) {
        chNova = Number(disc.carga_horaria) || 5;
        discNome = disc.nome || '';
      }
    }

    const novaCargaClasse = cargaClasseAtual + chNova;
    const novaCargaGeral = cargaGeralAtual + chNova;

    // Calcular horas normais e transbordo (horas extras)
    const horasExtrasClasse = Math.max(0, novaCargaClasse - maxClasse);
    const horasExtrasGeral = Math.max(0, novaCargaGeral - maxGeral);
    const horasExtrasFinais = Math.max(horasExtrasClasse, horasExtrasGeral);
    const horasNormaisFinais = Math.max(0, novaCargaGeral - horasExtrasFinais);

    // Listar turmas atuais
    const turmasAtuais = (prof.alocacoes || []).map(a => {
      const c = a.turma_grau || a.turma?.grau_ano || 'Classe';
      const t = a.turma_nome || a.turma?.nome || 'Turma';
      const d = a.disciplina_nome || a.disciplina?.nome || 'Disciplina';
      const ch = a.disciplina_carga_horaria || a.disciplina?.carga_horaria || 5;
      return `<li class="d-flex justify-content-between py-1 border-bottom border-light"><span><span class="badge bg-secondary me-1" style="font-size:0.68rem;">${c}</span><strong>${t}</strong>: ${d}</span><span class="badge bg-light text-dark border font-monospace">${ch}h/sem</span></li>`;
    }).join('');

    const temAlocacoes = (prof.alocacoes && prof.alocacoes.length > 0);

    let statusBox = '';
    if (chNova > 0 && horasExtrasFinais > 0) {
      statusBox = `
        <div class="alert alert-warning border border-warning d-flex align-items-start gap-2 mb-2 p-2 rounded">
          <i class="bi bi-exclamation-triangle-fill text-warning fs-4 mt-1"></i>
          <div>
            <div class="fw-bold text-dark">Atenção: Transbordo de Carga Horária Máxima!</div>
            <div class="small text-dark">
              Esta atribuição (${chNova}h/semana) excede o teto contratual normal. O sistema separa e contabiliza automaticamente:
            </div>
            <div class="d-flex gap-2 align-items-center mt-2 flex-wrap">
              <span class="badge bg-success p-2" style="font-size: 0.8rem;">Carga Normal: ${horasNormaisFinais}h / semana</span>
              <span class="badge bg-danger p-2 fs-6 font-monospace" style="font-size: 0.85rem;">+${horasExtrasFinais} Horas Extras / semana</span>
            </div>
            <div class="small text-muted mt-1" style="font-size: 0.72rem;">
              * As horas extras serão reflectidas no mapa de encargos e folha salarial da escola.
            </div>
          </div>
        </div>
      `;
    } else if (chNova > 0) {
      statusBox = `
        <div class="alert alert-success border border-success d-flex align-items-center gap-2 mb-2 p-2 rounded">
          <i class="bi bi-check-circle-fill text-success fs-4"></i>
          <div>
            <div class="fw-bold text-success">Dentro da Carga Horária Normal</div>
            <div class="small text-muted">
              Carga Total: <strong>${novaCargaGeral}h / semana</strong> (100% Carga Normal | <strong>0h Extras</strong>). O docente está dentro do limite máximo de ${maxClasse}h (classe) e ${maxGeral}h (geral).
            </div>
          </div>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="card bg-light border p-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-primary mb-0" style="font-size: 0.85rem;">
            <i class="bi bi-calculator me-1"></i> Análise de Carga Horária do Docente
          </h6>
          <span class="badge bg-secondary font-monospace" style="font-size: 0.75rem;">
            ${prof.nome} ${prof.apelido || ''}
          </span>
        </div>

        <div class="row g-2 text-center mb-2">
          <div class="col-3">
            <div class="p-2 bg-white rounded border">
              <small class="text-muted d-block" style="font-size: 0.68rem;">Carga Atual</small>
              <strong class="fs-6 text-dark">${cargaGeralAtual}h</strong>
              <small class="d-block text-muted" style="font-size: 0.65rem;">${selClasse ? `${cargaClasseAtual}h na ${selClasse.replace('Classe', '').trim()}` : 'Geral'}</small>
            </div>
          </div>
          <div class="col-3">
            <div class="p-2 bg-white rounded border border-primary border-opacity-25">
              <small class="text-primary d-block" style="font-size: 0.68rem;">Desta Turma</small>
              <strong class="fs-6 text-primary">+${chNova}h</strong>
              <small class="d-block text-muted" style="font-size: 0.65rem;">${discNome ? discNome.slice(0, 10) : 'Pendente'}</small>
            </div>
          </div>
          <div class="col-3">
            <div class="p-2 bg-white rounded border ${horasExtrasFinais > 0 ? 'border-warning' : 'border-success'}">
              <small class="d-block text-muted" style="font-size: 0.68rem;">Nova Carga Total</small>
              <strong class="fs-6 ${horasExtrasFinais > 0 ? 'text-warning' : 'text-success'}">${novaCargaGeral}h</strong>
              <small class="d-block ${horasExtrasFinais > 0 ? 'text-danger fw-bold' : 'text-success'}" style="font-size: 0.65rem;">
                ${horasExtrasFinais > 0 ? `+${horasExtrasFinais}h extra` : 'Normal'}
              </small>
            </div>
          </div>
          <div class="col-3">
            <div class="p-2 bg-white rounded border">
              <small class="text-muted d-block" style="font-size: 0.68rem;">Máx. Normal</small>
              <strong class="fs-6 text-info">${maxClasse}h</strong>
              <small class="d-block text-muted" style="font-size: 0.65rem;">Geral: ${maxGeral}h</small>
            </div>
          </div>
        </div>

        ${statusBox}

        ${temAlocacoes ? `
          <div class="mt-1">
            <a class="text-decoration-none small fw-semibold text-secondary d-inline-block" data-bs-toggle="collapse" href="#detalheTurmasAtuaisAloc" role="button">
              <i class="bi bi-chevron-down me-1"></i> Ver ${prof.alocacoes.length} turma(s) já atribuída(s) a este docente
            </a>
            <div class="collapse mt-2" id="detalheTurmasAtuaisAloc">
              <ul class="list-unstyled mb-0 small" style="max-height: 120px; overflow-y: auto;">
                ${turmasAtuais}
              </ul>
            </div>
          </div>
        ` : '<div class="small text-muted fst-italic">Este docente ainda não possui nenhuma turma atribuída.</div>'}
      </div>
    `;
  };

  // Inicializar cálculo inicial
  aoAtualizarCalculoCargaAlocar();

  document.getElementById('formModalAloc').addEventListener('submit', async (e) => {
    e.preventDefault();
    const profId = document.getElementById('malocProf').value;
    const turmaId = document.getElementById('malocTurma').value;
    const discId = document.getElementById('malocDisc').value;
    const cargaMaxClasse = Number(document.getElementById('malocCargaMaxClasse')?.value) || 16;
    const selClasse = document.getElementById('malocClasse')?.value;

    if (!profId || !turmaId || !discId) {
      return alert('Por favor seleccione o professor, a classe, a turma e a disciplina.');
    }

    try {
      const res = await apiFetch('/api/v1/professores/alocar', {
        method: 'POST',
        body: JSON.stringify({
          professor_id: profId,
          turma_id: turmaId,
          disciplina_id: discId,
          carga_maxima_classe: cargaMaxClasse
        })
      });
      if (res.success) {
        mostrarNotificacao('Turma e disciplina alocadas com sucesso! Carga horária e horas extras atualizadas.', 'success');
        fecharModal();
        await carregarProfessores();
      } else {
        alert(res.message || 'Erro ao alocar professor');
      }
    } catch (err) {
      alert(err.message || 'Erro ao alocar professor');
    }
  });
}

async function modalTransferirProfessor(profId) {
  try {
    const prof = (state.todosProfessores || []).find(p => p.id === profId);
    if (!prof) return alert('Docente não encontrado');

    const [turmasRes, discRes] = await Promise.all([
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/disciplinas')
    ]);

    const turmas = turmasRes.data || [];
    const disciplinas = discRes.data || [];
    state.todasTurmas = turmas;
    state.todasDisciplinas = disciplinas;

    const classesSet = new Set();
    turmas.forEach(t => { if (t.grau_ano) classesSet.add(t.grau_ano.trim()); });
    disciplinas.forEach(d => { if (d.classe) classesSet.add(d.classe.trim()); });
    const classesList = Array.from(classesSet).sort((a, b) => (parseInt(a.replace(/\D/g, '')) || 0) - (parseInt(b.replace(/\D/g, '')) || 0));

    const optClasses = classesList.length > 0
      ? classesList.map(c => `<option value="${c}">${c}</option>`).join('')
      : '<option value="" disabled>-- Nenhuma classe/nível cadastrado nesta instituição --</option>';

    const alocacoesAtuaisHtml = (prof.alocacoes && prof.alocacoes.length > 0)
      ? prof.alocacoes.map(a => `
        <span class="badge border bg-light text-dark p-2 me-1 mb-1">
          <i class="bi bi-mortarboard me-1 text-primary"></i>${a.turma_grau || 'Classe'}: <strong>${a.turma_nome || a.turma?.nome}</strong> (${a.disciplina_nome || a.disciplina?.nome})
        </span>
      `).join('')
      : '<span class="text-muted small">Sem turmas atribuídas de momento.</span>';

    abrirModal(`Transferir / Atribuir Nova Classe: ${prof.nome}`, `
      <form id="formModalTransferirProf">
        <div class="mb-3 p-3 bg-light rounded border">
          <div class="small fw-bold text-muted text-uppercase mb-1">Docente Seleccionado:</div>
          <h5 class="fw-bold text-primary mb-1">${prof.nome} ${prof.apelido || ''}</h5>
          <div class="small text-muted mb-2">Carreira: <strong>${prof.carreira || 'Licenciado'}</strong> | Especialidade: <strong>${prof.especialidade || 'Área Geral'}</strong></div>
          <div class="small fw-bold text-muted text-uppercase mb-1">Classes & Turmas Actuais:</div>
          <div class="d-flex flex-wrap gap-1">${alocacoesAtuaisHtml}</div>
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold text-dark">Modo de Operação</label>
          <div class="p-2 border rounded bg-white">
            <div class="form-check mb-1">
              <input class="form-check-input" type="radio" name="modoOperacao" id="modoSubstituir" value="SUBSTITUIR" checked>
              <label class="form-check-label small fw-semibold" for="modoSubstituir">
                Transferir Integralmente (Substituir turmas anteriores pela nova classe)
              </label>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="radio" name="modoOperacao" id="modoAdicionar" value="ADICIONAR">
              <label class="form-check-label small fw-semibold" for="modoAdicionar">
                Atribuir Classe Adicional (Manter turmas actuais e acrescentar a nova classe)
              </label>
            </div>
          </div>
        </div>

        <div class="row g-3">
          <div class="col-md-6">
            <label class="form-label small fw-bold text-primary"><i class="bi bi-mortarboard-fill me-1"></i> 1. Nova Classe / Grau</label>
            <select id="mtransfClasse" class="form-select border-primary fw-semibold" required onchange="aoMudarClasseModalTransferir()">
              <option value="">Selecione a Classe...</option>
              ${optClasses}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-bold text-primary"><i class="bi bi-collection-fill me-1"></i> 2. Turma da Nova Classe</label>
            <select id="mtransfTurma" class="form-select border-primary" required>
              <option value="">Selecione primeiro a classe...</option>
            </select>
          </div>
          <div class="col-12">
            <label class="form-label small fw-bold text-primary"><i class="bi bi-book-fill me-1"></i> 3. Disciplina a Ministrar</label>
            <select id="mtransfDisc" class="form-select border-primary" required>
              <option value="">Selecione a disciplina...</option>
            </select>
          </div>
        </div>

        <div class="d-flex justify-content-end gap-2 mt-4 pt-2 border-top">
          <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
          <button type="submit" class="btn btn-warning text-dark fw-bold btn-sm px-4">
            <i class="bi bi-arrow-left-right me-1"></i> Confirmar Atribuição / Transferência
          </button>
        </div>
      </form>
    `);

    window.aoMudarClasseModalTransferir = function() {
      const cls = document.getElementById('mtransfClasse')?.value;
      const selTurma = document.getElementById('mtransfTurma');
      const selDisc = document.getElementById('mtransfDisc');
      if (!selTurma || !selDisc) return;

      if (!cls) {
        selTurma.innerHTML = '<option value="">Selecione primeiro a classe...</option>';
        selDisc.innerHTML = '<option value="">Selecione primeiro a classe...</option>';
        return;
      }

      const turmasFiltradas = (state.todasTurmas || []).filter(t => 
        normalizarClasse(t.grau_ano) === normalizarClasse(cls)
      );

      if (turmasFiltradas.length === 0) {
        selTurma.innerHTML = `<option value="">Nenhuma turma cadastrada para ${cls}</option>`;
      } else {
        selTurma.innerHTML = '<option value="">Selecione a Turma...</option>' + 
          turmasFiltradas.map(t => `<option value="${t.id}">${t.nome} (${t.area || 'Geral'})</option>`).join('');
      }

      const discFiltradas = (state.todasDisciplinas || []).filter(d => 
        !d.classe || normalizarClasse(d.classe) === normalizarClasse(cls)
      );

      if (discFiltradas.length === 0) {
        selDisc.innerHTML = (state.todasDisciplinas || []).map(d => `<option value="${d.id}">${d.nome}</option>`).join('');
      } else {
        selDisc.innerHTML = '<option value="">Selecione a Disciplina...</option>' + 
          discFiltradas.map(d => `<option value="${d.id}">${d.nome} ${d.classe ? `(${d.classe})` : ''}</option>`).join('');
      }
    };

    document.getElementById('formModalTransferirProf').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const modo = document.querySelector('input[name="modoOperacao"]:checked')?.value || 'SUBSTITUIR';
        const turmaId = document.getElementById('mtransfTurma').value;
        const discId = document.getElementById('mtransfDisc').value;

        if (!turmaId || !discId) {
          return alert('Por favor, seleccione a turma e a disciplina correspondentes.');
        }

        // Se for substituição integral, remove as alocações anteriores
        if (modo === 'SUBSTITUIR' && prof.alocacoes && prof.alocacoes.length > 0) {
          const remocoes = prof.alocacoes.map(a => 
            apiFetch(`/api/v1/professores/alocar/${a.id}`, { method: 'DELETE' })
          );
          await Promise.all(remocoes);
        }

        // Cria a nova alocação
        const resAloc = await apiFetch('/api/v1/professores/alocar', {
          method: 'POST',
          body: JSON.stringify({
            professor_id: profId,
            turma_id: turmaId,
            disciplina_id: discId
          })
        });

        if (resAloc.success) {
          mostrarNotificacao('Docente transferido / atribuído à nova classe com sucesso!', 'success');
          fecharModal();
          carregarProfessores();
        } else {
          alert(resAloc.message || 'Erro ao atribuir nova classe');
        }
      } catch (err) {
        alert(err.message || 'Erro ao realizar transferência');
      }
    });
  } catch (err) {
    alert('Erro ao carregar modal de transferência: ' + err.message);
  }
}

async function excluirProfessor(profId) {
  const p = (state.todosProfessores || []).find(x => x.id === profId);
  const nome = p ? `${p.nome} ${p.apelido || ''}`.trim() : 'este docente';
  if (!confirm(`Tem a certeza que deseja eliminar o docente "${nome}" do quadro escolar? Todas as suas alocações de turmas e disciplinas serão desvinculadas.`)) {
    return;
  }
  try {
    const res = await apiFetch(`/api/v1/professores/${profId}`, {
      method: 'DELETE'
    });
    if (res.success) {
      mostrarNotificacao('Docente eliminado do quadro com sucesso!', 'success');
      await carregarProfessores();
    } else {
      alert(res.message || 'Erro ao eliminar docente');
    }
  } catch (err) {
    alert(err.message || 'Erro ao comunicar com o servidor');
  }
}

async function modalEditarAlocacao(alocacaoId, profId) {
  try {
    const [profsRes, turmasRes, discRes] = await Promise.all([
      apiFetch('/api/v1/professores'),
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/disciplinas')
    ]);

    const prof = (profsRes.data || []).find(p => p.id === profId);
    const aloc = prof ? (prof.alocacoes || []).find(a => a.id === alocacaoId) : null;

    const optTurmas = (turmasRes.data || []).map(t => 
      `<option value="${t.id}" ${aloc && aloc.turma_id === t.id ? 'selected' : ''}>${t.grau_ano} &rarr; ${t.nome} (${normalizarArea(t.area || 'Geral')})</option>`
    ).join('');

    const optDisc = (discRes.data || []).map(d => 
      `<option value="${d.id}" ${aloc && aloc.disciplina_id === d.id ? 'selected' : ''}>${d.nome} (${d.classe || ''})</option>`
    ).join('');

    abrirModal(`Editar Alocação: ${prof ? prof.nome : 'Docente'}`, `
      <form id="formModalEditarAloc">
        <div class="mb-3">
          <label class="form-label small fw-semibold">Professor / Docente</label>
          <input type="text" class="form-control" value="${prof ? prof.nome : ''}" disabled>
        </div>
        <div class="mb-3">
          <label class="form-label small fw-semibold text-primary">Turma Atribuída</label>
          <select id="mEditAlocTurma" class="form-select" required>${optTurmas}</select>
        </div>
        <div class="mb-3">
          <label class="form-label small fw-semibold text-primary">Disciplina Curricular</label>
          <select id="mEditAlocDisc" class="form-select" required>${optDisc}</select>
        </div>
        <div class="d-flex gap-2 justify-content-end mt-4">
          <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
          <button type="submit" class="btn btn-primary btn-sm px-4">Salvar Alterações</button>
        </div>
      </form>
    `);

    document.getElementById('formModalEditarAloc').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const res = await apiFetch(`/api/v1/professores/alocar/${alocacaoId}`, {
          method: 'PUT',
          body: JSON.stringify({
            turma_id: document.getElementById('mEditAlocTurma').value,
            disciplina_id: document.getElementById('mEditAlocDisc').value
          })
        });
        if (res.success) {
          mostrarNotificacao('Alocação actualizada com sucesso!', 'success');
          fecharModal();
          carregarProfessores();
        } else {
          alert(res.message || 'Erro ao actualizar alocação');
        }
      } catch (err) {
        alert(err.message || 'Erro ao comunicar com o servidor');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados da alocação: ' + err.message);
  }
}

async function eliminarAlocacao(alocacaoId, profId) {
  if (!confirm('Tem a certeza que deseja eliminar esta alocação de turma/disciplina do docente?')) return;
  try {
    const res = await apiFetch(`/api/v1/professores/alocar/${alocacaoId}`, {
      method: 'DELETE'
    });
    if (res.success) {
      mostrarNotificacao('Alocação eliminada com sucesso!', 'success');
      await carregarProfessores();
    } else {
      alert(res.message || 'Erro ao eliminar alocação');
    }
  } catch (err) {
    alert(err.message || 'Erro ao comunicar com o servidor');
  }
}

