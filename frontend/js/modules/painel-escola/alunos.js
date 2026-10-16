/**
 * SIGE - PAINEL-ESCOLA | Alunos & Matrículas
 * Ficheiro de código independente do menu: alunos.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 4. ALUNOS ====================
async function carregarAlunos(anoParam) {
  try {
    const selAno = document.getElementById('filtroAnoAlunos');
    const anoAtivo = state.tenant?.ano_letivo_ativo || '2026';
    const ano = anoParam || (selAno ? selAno.value : null) || state.anoLectivoVisualizacao || localStorage.getItem('sige_ano_letivo_selecionado') || anoAtivo;
    state.filtroAlunoAno = ano;

    const queryAno = (ano && ano !== 'TODOS') ? `?ano_letivo=${encodeURIComponent(ano)}` : '';
    const [resAlunos, resTurmas, resStats, resDisciplinas] = await Promise.all([
      apiFetch(`/api/v1/alunos${queryAno}`),
      apiFetch(`/api/v1/escola-admin/turmas${queryAno}`),
      apiFetch('/api/v1/alunos/stats'),
      apiFetch('/api/v1/disciplinas')
    ]);

    if (resStats.success) {
      const s = resStats.data;
      document.getElementById('alunoTotalCard').textContent = s.totalGeral;
      document.getElementById('alunoRetencaoCard').textContent = s.taxaRetencao + '%';
      document.getElementById('alunoEvasaoCard').textContent = s.taxaEvasao + '%';
      document.getElementById('alunoGeneroRatioCard').textContent = `${s.genero.M} M / ${s.genero.F} F`;
    }

    state.todosAlunos = resAlunos.success ? (resAlunos.data || []) : [];
    state.todasTurmas = resTurmas.success ? (resTurmas.data || []) : [];
    if (resDisciplinas && resDisciplinas.data) {
      state.todasDisciplinas = resDisciplinas.data || [];
    }

    atualizarSeletorAnosAlunos();
    renderizarBotoesClassesAlunos();
  } catch (err) {
    console.error('Erro ao carregar alunos:', err);
  }
}

function atualizarSeletorAnosAlunos() {
  const selAno = document.getElementById('filtroAnoAlunos');
  if (!selAno) return;

  const anoAtivo = state.tenant?.ano_letivo_ativo || '2026';
  const anosList = (state.anosLectivos && state.anosLectivos.length > 0)
    ? state.anosLectivos.map(a => String(a.ano))
    : ['2026'];

  const anosSet = new Set([anoAtivo, ...anosList]);
  (state.todosAlunos || []).forEach(a => {
    if (a.ano_ingresso) anosSet.add(String(a.ano_ingresso));
    else if (a.matricula && a.matricula.length >= 4 && a.matricula.slice(0, 4).match(/^\d{4}$/)) {
      anosSet.add(a.matricula.slice(0, 4));
    }
  });
  (state.todasTurmas || []).forEach(t => {
    if (t.ano_letivo) anosSet.add(String(t.ano_letivo));
  });

  const anosOrdenados = Array.from(anosSet)
    .filter(y => y && y.match(/^\d{4}$/) && parseInt(y) >= 2026)
    .sort((a, b) => parseInt(b) - parseInt(a));
  const valorAtual = state.filtroAlunoAno || state.anoLectivoVisualizacao || localStorage.getItem('sige_ano_letivo_selecionado') || anoAtivo;

  selAno.innerHTML = `
    <option value="">-- Escolha ano Lectivo --</option>
    ${anosOrdenados.map(ano => `
      <option value="${ano}" ${String(valorAtual) === String(ano) ? 'selected' : ''}>
        Ano Lectivo de ${ano}
      </option>
    `).join('')}
  `;
}

window.aoMudarFiltroAnoAlunos = function(ano) {
  state.filtroAlunoAno = ano;
};

window.aoClicarBuscarAlunosPorAno = async function() {
  const sel = document.getElementById('filtroAnoAlunos');
  const ano = sel ? sel.value : '';
  state.filtroAlunoAno = ano;
  if (ano) {
    state.anoLectivoVisualizacao = ano;
    localStorage.setItem('sige_ano_letivo_selecionado', ano);
  }
  const selHeader = document.getElementById('headerSelectAnoLectivo');
  if (selHeader && ano) selHeader.value = ano;

  if (typeof setCarregandoBuscaAno === 'function') setCarregandoBuscaAno(true);
  try {
    await carregarAlunos(ano);
  } finally {
    if (typeof setCarregandoBuscaAno === 'function') setCarregandoBuscaAno(false);
  }
};

function obterAlunosFiltradosPorAno() {
  const anoFiltro = state.filtroAlunoAno || state.anoLectivoVisualizacao || state.tenant?.ano_letivo_ativo || '2026';
  if (!anoFiltro || anoFiltro === 'TODOS') {
    return state.todosAlunos || [];
  }
  return (state.todosAlunos || []).filter(a => {
    const t = getAlunoTurma(a);
    const anoTurma = t?.ano_letivo ? String(t.ano_letivo) : null;
    const anoIngresso = a.ano_ingresso ? String(a.ano_ingresso) : null;
    const anoMatricula = (a.matricula && a.matricula.length >= 4 && a.matricula.slice(0, 4).match(/^\d{4}$/)) ? a.matricula.slice(0, 4) : null;
    const anoAluno = anoTurma || anoIngresso || anoMatricula;
    return String(anoAluno) === String(anoFiltro);
  });
}


function getAlunoTurma(a) {
  if (!a) return null;
  if (a.turma && typeof a.turma === 'object' && a.turma.nome) return a.turma;
  const tId = a.turma_id || (typeof a.turma === 'string' ? a.turma : null);
  if (tId && Array.isArray(state.todasTurmas)) {
    const found = state.todasTurmas.find(t => t.id === tId);
    if (found) return found;
  }
  if (a.turma_nome || a.turma_grau) {
    return {
      id: tId,
      nome: a.turma_nome || 'Turma',
      grau_ano: a.turma_grau || ''
    };
  }
  return null;
}

function normalizarClasse(str) {
  if (!str) return '';
  return str.toString()
    .replace(/[ªº°\.]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function normalizarArea(str) {
  if (!str) return 'Ensino Geral';
  let s = str.toString().trim();
  // Corrigir possíveis inconsistências de encoding / acentos corrompidos
  s = s.replace(/Ci[\uFFFD\u00EA\u00E9e\?]?ncias/gi, 'Ciências');
  s = s.replace(/^Cincias/gi, 'Ciências');
  s = s.replace(/Cincias/gi, 'Ciências');

  const lower = s.toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, ""); // remove acentos

  if (lower === 'geral' || lower === 'tronco comum' || lower === 'tronco comum / geral' || lower === 'ensino geral') {
    return 'Ensino Geral';
  }
  // Verificar combinações específicas primeiro antes de palavras isoladas!
  if (lower.includes('ciencias') && lower.includes('geografia')) {
    return 'Ciências com Geografia';
  }
  if (lower.includes('letras') && lower.includes('geografia')) {
    return 'Letras com Geografia';
  }
  if (lower.includes('letras') && lower.includes('historia')) {
    return 'Letras com História';
  }
  if (lower.includes('ciencias') && lower.includes('biologia')) {
    return 'Ciências com Biologia';
  }
  if (lower.includes('ciencias') && lower.includes('desenho')) {
    return 'Ciências com Desenho';
  }
  if (lower === 'ciencias' || lower === 'cincias') {
    return 'Ciências';
  }
  if (lower === 'letras') {
    return 'Letras';
  }
  if (lower === 'geografia') {
    return 'Letras com Geografia';
  }
  if (lower === 'historia') {
    return 'Letras com História';
  }
  return s;
}

function getAlunoArea(a) {
  if (!a) return 'Ensino Geral';
  const t = getAlunoTurma(a);

  const isEspecifica = (val) => {
    if (!val) return false;
    const v = String(val).trim().toLowerCase();
    return v !== '' && v !== 'geral' && v !== 'ensino geral' && v !== 'tronco comum' && v !== 'none' && v !== 'null';
  };

  if (isEspecifica(a.area)) return normalizarArea(a.area);
  if (isEspecifica(a.seccao)) return normalizarArea(a.seccao);
  if (isEspecifica(t?.area)) return normalizarArea(t.area);
  if (isEspecifica(a.turma_area)) return normalizarArea(a.turma_area);

  // Se o aluno estiver na 11ª ou 12ª Classe, nunca deve ser 'Ensino Geral'
  const classeAluno = a.classe || t?.grau_ano || a.turma_grau || '';
  const clsNorm = normalizarClasse(classeAluno);
  if (clsNorm.includes('11') || clsNorm.includes('12')) {
    // Buscar área nas disciplinas cadastradas para esta classe na escola
    const discComArea = (state.todasDisciplinas || []).find(d => {
      const dCls = normalizarClasse(d.classe || '');
      return (clsNorm.includes('11') ? dCls.includes('11') : dCls.includes('12')) && isEspecifica(d.area);
    });
    if (discComArea && discComArea.area) {
      return normalizarArea(discComArea.area);
    }
    // Buscar em turmas da classe que tenham área específica
    const turmaComArea = (state.todasTurmas || []).find(tur => {
      const tCls = normalizarClasse(tur.grau_ano || '');
      return (clsNorm.includes('11') ? tCls.includes('11') : tCls.includes('12')) && isEspecifica(tur.area);
    });
    if (turmaComArea && turmaComArea.area) {
      return normalizarArea(turmaComArea.area);
    }
    return 'Ciências com Geografia';
  }

  const raw = a.area || a.seccao || (t && t.area) || a.turma_area || 'Ensino Geral';
  return normalizarArea(raw);
}

function getBadgeAreaEstudo(area) {
  const norm = normalizarArea(area);
  if (norm.includes('Letras')) {
    return `<span class="badge border" style="background-color: #f3e8ff; color: #6b21a8; border-color: #d8b4fe !important; font-size: 0.75rem;"><i class="bi bi-book me-1"></i>${norm}</span>`;
  }
  if (norm.includes('Ciências') || norm.includes('Ciencias')) {
    return `<span class="badge border" style="background-color: #e0f2fe; color: #0369a1; border-color: #7dd3fc !important; font-size: 0.75rem;"><i class="bi bi-cpu me-1"></i>${norm}</span>`;
  }
  if (norm === 'Ensino Geral') {
    return `<span class="badge border" style="background-color: #f1f5f9; color: #475569; border-color: #cbd5e1 !important; font-size: 0.75rem;"><i class="bi bi-mortarboard me-1"></i>${norm}</span>`;
  }
  return `<span class="badge border" style="background-color: #fef3c7; color: #92400e; border-color: #fde68a !important; font-size: 0.75rem;"><i class="bi bi-tag me-1"></i>${norm}</span>`;
}

function renderizarFiltrosAlunos() {
  const selectClasse = document.getElementById('selectFiltroAlunoClasse');
  if (!selectClasse) return;

  const alunosAno = obterAlunosFiltradosPorAno();
  const anoFiltro = state.filtroAlunoAno || state.tenant?.ano_letivo_ativo || '2026';

  // 1. Extrair classes únicas das turmas, alunos e disciplinas
  const classesSet = new Set();
  (state.todasTurmas || []).forEach(t => {
    if (t.grau_ano && (anoFiltro === 'TODOS' || !t.ano_letivo || String(t.ano_letivo) === String(anoFiltro))) {
      classesSet.add(t.grau_ano.trim());
    }
  });
  alunosAno.forEach(a => {
    const t = getAlunoTurma(a);
    if (a.classe) classesSet.add(a.classe.trim());
    if (t?.grau_ano) classesSet.add(t.grau_ano.trim());
  });
  (state.todasDisciplinas || []).forEach(d => {
    if (d.classe) classesSet.add(d.classe.trim());
  });

  const classesOrdenadas = Array.from(classesSet).sort((a, b) => {
    const numA = parseInt(a.replace(/\D/g, '')) || 0;
    const numB = parseInt(b.replace(/\D/g, '')) || 0;
    return numA - numB;
  });

  if (!state.filtroAlunoClasse) state.filtroAlunoClasse = 'TODAS';
  if (!state.filtroAlunoArea) state.filtroAlunoArea = 'TODAS';
  if (!state.filtroAlunoTurma) state.filtroAlunoTurma = 'TODAS';

  const totalGeralAlunos = alunosAno.length;
  const semTurmaCount = alunosAno.filter(a => !getAlunoTurma(a)).length;

  const contagemClassesEl = document.getElementById('contagemClassesAlunos');
  if (contagemClassesEl) {
    contagemClassesEl.textContent = `${classesOrdenadas.length} classe(s)/nível(eis)`;
  }

  let htmlClasse = `<option value="TODAS">Todas as Classes / Níveis (${totalGeralAlunos})</option>`;
  if (semTurmaCount > 0) {
    htmlClasse += `<option value="SEM_TURMA">⚠️ Sem Turma Atribuída (${semTurmaCount})</option>`;
  }
  if (classesOrdenadas.length === 0) {
    htmlClasse += `<option value="" disabled>-- Nenhuma classe/nível com alunos cadastrados --</option>`;
  }

  classesOrdenadas.forEach(cls => {
    const totalNaClasse = alunosAno.filter(a => {
      const t = getAlunoTurma(a);
      const aClasse = a.classe || t?.grau_ano || a.turma_grau;
      return aClasse && normalizarClasse(aClasse) === normalizarClasse(cls);
    }).length;
    htmlClasse += `<option value="${cls}">${cls} (${totalNaClasse} alunos)</option>`;
  });

  selectClasse.innerHTML = htmlClasse;
  selectClasse.value = state.filtroAlunoClasse;

  atualizarDropdownAreasAlunos();
}

function aoMudarSelectClasseAlunos(classe) {
  state.filtroAlunoClasse = classe;
  state.filtroAlunoArea = 'TODAS';
  state.filtroAlunoTurma = 'TODAS';

  const selectArea = document.getElementById('selectFiltroAlunoArea');
  const selectTurma = document.getElementById('selectFiltroAlunoTurma');

  if (classe === 'SEM_TURMA') {
    if (selectArea) {
      selectArea.innerHTML = `<option value="TODAS">Não aplicável</option>`;
      selectArea.disabled = true;
    }
    if (selectTurma) {
      selectTurma.innerHTML = `<option value="TODAS">Sem Turma</option>`;
      selectTurma.disabled = true;
    }
    aplicarFiltroHierarquicoAlunos();
    return;
  }

  if (selectArea) selectArea.disabled = false;
  if (selectTurma) selectTurma.disabled = false;

  atualizarDropdownAreasAlunos();
}

function atualizarDropdownAreasAlunos() {
  const selectArea = document.getElementById('selectFiltroAlunoArea');
  const contagemAreas = document.getElementById('contagemAreasClasse');
  if (!selectArea) return;

  const classe = state.filtroAlunoClasse || 'TODAS';
  const alunosAno = obterAlunosFiltradosPorAno();
  const anoFiltro = state.filtroAlunoAno || state.tenant?.ano_letivo_ativo || '2026';

  if (classe === 'SEM_TURMA') {
    selectArea.innerHTML = `<option value="TODAS">Não aplicável</option>`;
    selectArea.disabled = true;
    atualizarDropdownTurmasAlunos();
    return;
  }

  selectArea.disabled = false;

  // Alunos desta classe
  const alunosClasse = (classe === 'TODAS') 
    ? alunosAno 
    : alunosAno.filter(a => {
        const t = getAlunoTurma(a);
        const aClasse = a.classe || t?.grau_ano || a.turma_grau;
        return aClasse && normalizarClasse(aClasse) === normalizarClasse(classe);
      });

  // Turmas desta classe no ano lectivo
  const turmasClasse = (state.todasTurmas || []).filter(t => {
    if (anoFiltro !== 'TODOS' && t.ano_letivo && String(t.ano_letivo) !== String(anoFiltro)) {
      return false;
    }
    if (classe === 'TODAS') return true;
    return normalizarClasse(t.grau_ano) === normalizarClasse(classe);
  });

  // Carregar TODAS as secções cadastradas (oficiais, de disciplinas, de turmas, alunos e personalizadas)
  const todasAreasCadastradas = window.obterTodasAreasOficiais(classe);
  const areasSet = new Set(todasAreasCadastradas.map(a => normalizarArea(a)));

  turmasClasse.forEach(t => {
    if (t.area) areasSet.add(normalizarArea(t.area));
  });
  alunosClasse.forEach(a => {
    areasSet.add(getAlunoArea(a));
  });

  const areasLista = Array.from(areasSet).sort((a, b) => {
    if (a === 'Ensino Geral') return -1;
    if (b === 'Ensino Geral') return 1;
    const totalA = alunosClasse.filter(al => getAlunoArea(al) === a).length + turmasClasse.filter(t => normalizarArea(t.area) === a).length;
    const totalB = alunosClasse.filter(al => getAlunoArea(al) === b).length + turmasClasse.filter(t => normalizarArea(t.area) === b).length;
    if (totalB !== totalA) return totalB - totalA;
    return a.localeCompare(b);
  });

  if (contagemAreas) {
    contagemAreas.textContent = `${areasLista.length} secção(ões)`;
  }

  if (state.filtroAlunoArea !== 'TODAS' && !areasLista.includes(state.filtroAlunoArea)) {
    state.filtroAlunoArea = 'TODAS';
  }

  let htmlArea = `<option value="TODAS">${classe === 'TODAS' ? 'Todas as Secções / Áreas' : 'Todas as Secções da Classe'} (${alunosClasse.length})</option>`;
  areasLista.forEach(ar => {
    const totalAlunosNaArea = alunosClasse.filter(a => getAlunoArea(a) === ar).length;
    const totalTurmasNaArea = turmasClasse.filter(t => normalizarArea(t.area) === ar).length;
    let info = '';
    if (totalTurmasNaArea > 0 && totalAlunosNaArea > 0) {
      info = ` (${totalAlunosNaArea} alunos, ${totalTurmasNaArea} turma(s))`;
    } else if (totalTurmasNaArea > 0) {
      info = ` (0 alunos, ${totalTurmasNaArea} turma(s))`;
    } else if (totalAlunosNaArea > 0) {
      info = ` (${totalAlunosNaArea} alunos)`;
    } else {
      info = ` (0 alunos)`;
    }
    htmlArea += `<option value="${ar}">${ar}${info}</option>`;
  });

  selectArea.innerHTML = htmlArea;
  selectArea.value = state.filtroAlunoArea;

  atualizarDropdownTurmasAlunos();
}

function aoMudarSelectAreaAlunos(area) {
  state.filtroAlunoArea = area;
  state.filtroAlunoTurma = 'TODAS';
  atualizarDropdownTurmasAlunos();
}

function atualizarDropdownTurmasAlunos() {
  const selectTurma = document.getElementById('selectFiltroAlunoTurma');
  const contagemTurmas = document.getElementById('contagemTurmasClasse');
  if (!selectTurma) return;

  const classe = state.filtroAlunoClasse || 'TODAS';
  const area = state.filtroAlunoArea || 'TODAS';
  const alunosAno = obterAlunosFiltradosPorAno();
  const anoFiltro = state.filtroAlunoAno || state.tenant?.ano_letivo_ativo || '2026';

  if (classe === 'SEM_TURMA') {
    selectTurma.innerHTML = `<option value="TODAS">Sem Turma</option>`;
    selectTurma.disabled = true;
    aplicarFiltroHierarquicoAlunos();
    return;
  }

  selectTurma.disabled = false;

  // Filtrar estritamente as turmas pertencentes àquela área e classe!
  const turmasFiltradas = (state.todasTurmas || []).filter(t => {
    if (anoFiltro !== 'TODOS' && t.ano_letivo && String(t.ano_letivo) !== String(anoFiltro)) {
      return false;
    }
    if (classe !== 'TODAS' && normalizarClasse(t.grau_ano) !== normalizarClasse(classe)) {
      return false;
    }
    if (area !== 'TODAS' && normalizarArea(t.area) !== normalizarArea(area)) {
      return false;
    }
    return true;
  });

  if (contagemTurmas) {
    contagemTurmas.textContent = `${turmasFiltradas.length} turma(s)`;
  }

  let labelTodasTurmas = 'Todas as Turmas da Secção';
  if (classe === 'TODAS' && area === 'TODAS') labelTodasTurmas = 'Todas as Turmas';
  else if (area === 'TODAS') labelTodasTurmas = 'Todas as Turmas da Classe';

  // Alunos no contexto
  const alunosContexto = alunosAno.filter(a => {
    const t = getAlunoTurma(a);
    const aClasse = a.classe || t?.grau_ano || a.turma_grau;
    if (classe !== 'TODAS' && (!aClasse || normalizarClasse(aClasse) !== normalizarClasse(classe))) {
      return false;
    }
    if (area !== 'TODAS' && normalizarArea(getAlunoArea(a)) !== normalizarArea(area)) {
      return false;
    }
    return true;
  });

  let htmlTurmas = `<option value="TODAS">${labelTodasTurmas} (${alunosContexto.length})</option>`;
  turmasFiltradas.forEach(t => {
    const totalAlunosTurma = alunosAno.filter(a => {
      const at = getAlunoTurma(a);
      return at?.id === t.id || a.turma_id === t.id;
    }).length;
    htmlTurmas += `<option value="${t.id}">${t.nome} (${totalAlunosTurma} alunos)</option>`;
  });

  selectTurma.innerHTML = htmlTurmas;

  const pertence = turmasFiltradas.some(t => t.id === state.filtroAlunoTurma);
  if (!pertence) {
    state.filtroAlunoTurma = 'TODAS';
  }
  selectTurma.value = state.filtroAlunoTurma;

  aplicarFiltroHierarquicoAlunos();
}

function aoMudarSelectTurmaAlunos(turmaId) {
  state.filtroAlunoTurma = turmaId;
  aplicarFiltroHierarquicoAlunos();
}

function limparFiltrosAlunos() {
  state.filtroAlunoClasse = 'TODAS';
  state.filtroAlunoArea = 'TODAS';
  state.filtroAlunoTurma = 'TODAS';
  const inputPesquisa = document.getElementById('pesquisaAlunosHierarquia');
  if (inputPesquisa) inputPesquisa.value = '';
  renderizarFiltrosAlunos();
}

// Aliases para retrocompatibilidade
function renderizarBotoesClassesAlunos() {
  renderizarFiltrosAlunos();
}
function selecionarClasseAlunos(c) {
  const sel = document.getElementById('selectFiltroAlunoClasse');
  if (sel) sel.value = c;
  aoMudarSelectClasseAlunos(c);
}
function selecionarAreaAlunos(a) {
  const sel = document.getElementById('selectFiltroAlunoArea');
  if (sel) sel.value = a;
  aoMudarSelectAreaAlunos(a);
}
function selecionarTurmaAlunos(t) {
  const sel = document.getElementById('selectFiltroAlunoTurma');
  if (sel) sel.value = t;
  aoMudarSelectTurmaAlunos(t);
}

function aplicarFiltroHierarquicoAlunos() {
  const classe = state.filtroAlunoClasse || 'TODAS';
  const area = state.filtroAlunoArea || 'TODAS';
  const turmaId = state.filtroAlunoTurma || 'TODAS';
  const badge = document.getElementById('badgeCaminhoHierarquia');

  let alunos = obterAlunosFiltradosPorAno();

  let nomeClasse = 'Todas as Classes';
  let nomeArea = 'Todas as Secções';
  let nomeTurma = 'Todas as Turmas';

  if (classe === 'SEM_TURMA') {
    nomeClasse = 'Sem Turma Atribuída';
    nomeArea = '—';
    nomeTurma = '—';
    alunos = alunos.filter(a => !getAlunoTurma(a));
  } else {
    // 1. Filtro de Classe
    if (classe && classe !== 'TODAS') {
      nomeClasse = classe;
      alunos = alunos.filter(a => {
        const t = getAlunoTurma(a);
        const aClasse = a.classe || t?.grau_ano || a.turma_grau;
        return aClasse && normalizarClasse(aClasse) === normalizarClasse(classe);
      });
    }

    // 2. Filtro de Secção / Área
    if (area && area !== 'TODAS') {
      nomeArea = area;
      alunos = alunos.filter(a => normalizarArea(getAlunoArea(a)) === normalizarArea(area));
    }

    // 3. Filtro de Turma
    if (turmaId && turmaId !== 'TODAS') {
      alunos = alunos.filter(a => {
        const t = getAlunoTurma(a);
        return t?.id === turmaId || a.turma_id === turmaId;
      });
      const objTurma = (state.todasTurmas || []).find(t => t.id === turmaId);
      if (objTurma) nomeTurma = objTurma.nome;
    }
  }

  const anoFiltro = state.filtroAlunoAno || state.tenant?.ano_letivo_ativo || '2026';
  const textoAno = anoFiltro === 'TODOS' ? 'Todos os Anos' : `Ano: ${anoFiltro}`;

  if (badge) {
    if (classe === 'SEM_TURMA') {
      badge.innerHTML = `<i class="bi bi-person-exclamation me-1"></i> <span class="badge bg-light text-primary border me-1">${textoAno}</span> <span class="fw-bold">${nomeClasse}</span> (${alunos.length} Alunos)`;
    } else {
      badge.innerHTML = `<i class="bi bi-diagram-3 me-1"></i> <span class="badge bg-light text-primary border me-1">${textoAno}</span> ${nomeClasse} &rarr; <span class="badge bg-light border me-1" style="color: #7c3aed; border-color: #d8b4fe !important;">${nomeArea}</span> &rarr; <span class="fw-bold">${nomeTurma}</span> (${alunos.length} Alunos)`;
    }
  }

  const contagem = document.getElementById('contagemAlunosExibidos');
  if (contagem) contagem.textContent = `${alunos.length} aluno(s) listado(s)`;

  state.alunosFiltradosAtuais = alunos;
  renderizarTabelaAlunos(alunos);
}

function filtrarAlunosHierarquia() {
  const termo = (document.getElementById('pesquisaAlunosHierarquia')?.value || '').toLowerCase().trim();
  let baseAlunos = state.alunosFiltradosAtuais || state.todosAlunos || [];

  // Se a pesquisa estiver activa e não encontrar no subconjunto, busca no universo global de alunos
  if (termo) {
    let filtrados = baseAlunos.filter(a => 
      (a.nome || '').toLowerCase().includes(termo) ||
      (a.apelido || '').toLowerCase().includes(termo) ||
      (a.matricula || '').toLowerCase().includes(termo) ||
      (a.numero_documento || '').toLowerCase().includes(termo) ||
      (getAlunoArea(a) || '').toLowerCase().includes(termo)
    );

    if (filtrados.length === 0) {
      filtrados = (state.todosAlunos || []).filter(a => 
        (a.nome || '').toLowerCase().includes(termo) ||
        (a.apelido || '').toLowerCase().includes(termo) ||
        (a.matricula || '').toLowerCase().includes(termo) ||
        (a.numero_documento || '').toLowerCase().includes(termo) ||
        (getAlunoArea(a) || '').toLowerCase().includes(termo)
      );
    }

    renderizarTabelaAlunos(filtrados);
    const contagem = document.getElementById('contagemAlunosExibidos');
    if (contagem) contagem.textContent = `${filtrados.length} aluno(s) encontrado(s) para "${termo}"`;
  } else {
    renderizarTabelaAlunos(baseAlunos);
    const contagem = document.getElementById('contagemAlunosExibidos');
    if (contagem) contagem.textContent = `${baseAlunos.length} aluno(s) listado(s)`;
  }
}

function renderizarTabelaAlunos(alunos) {
  const tbody = document.getElementById('tabelaAlunos');
  if (!tbody) return;

  if (!alunos || alunos.length === 0) {
    const semTurmaCount = (state.todosAlunos || []).filter(a => !getAlunoTurma(a)).length;
    let dicaExtra = '';
    if (semTurmaCount > 0 && state.filtroAlunoClasse !== 'SEM_TURMA' && state.filtroAlunoClasse !== 'TODAS') {
      dicaExtra = `<div class="mt-2"><span class="badge bg-warning text-dark p-2" role="button" onclick="selecionarClasseAlunos('SEM_TURMA')"><i class="bi bi-info-circle me-1"></i> Esta escola possui ${semTurmaCount} aluno(s) sem turma atribuída. Clique aqui para ver e atribuir turmas.</span></div>`;
    }
    tbody.innerHTML = `<tr><td colspan="11" class="text-center py-4 text-muted"><i class="bi bi-info-circle me-1"></i> Nenhum aluno encontrado para a selecção actual.${dicaExtra}</td></tr>`;
    return;
  }

  tbody.innerHTML = alunos.map((a, idx) => {
    const nomeCompleto = `${a.nome || ''} ${a.apelido && !a.nome.endsWith(a.apelido) ? a.apelido : ''}`.trim();
    const t = getAlunoTurma(a);
    const classe = a.classe || t?.grau_ano || a.turma_grau || '<span class="text-muted fst-italic">Sem Grau</span>';
    const areaAluno = getAlunoArea(a);
    const areaBadge = getBadgeAreaEstudo(areaAluno);
    const turma = t?.nome || a.turma_nome 
      ? `<span class="badge bg-primary bg-opacity-10 text-primary border border-primary">${t?.nome || a.turma_nome}</span>` 
      : '<span class="badge bg-warning bg-opacity-25 text-dark border border-warning" title="Aluno ainda sem turma">Sem Turma</span>';
    const doc = `${a.tipo_documento || 'BI'}: ${a.numero_documento || '-'}`;
    const encarregado = a.contato_responsavel ? `${a.nome_responsavel || 'Enc.'} (${a.contato_responsavel})` : (a.nome_responsavel || '-');
    const isAtivo = a.status === 'ATIVO';

    return `
      <tr>
        <td class="text-center fw-bold text-muted">${idx + 1}</td>
        <td>
          <code>${a.matricula}</code>
          <div class="mt-1">
            <span class="badge bg-light text-dark border" style="font-size: 0.7rem;" title="Ano de Ingresso / Trabalho Anual">
              <i class="bi bi-calendar-check text-primary me-1"></i>Ingresso: <strong>${a.ano_ingresso || (a.matricula && a.matricula.length >= 4 && a.matricula.slice(0, 4).match(/^\d{4}$/) ? a.matricula.slice(0, 4) : '2026')}</strong>
            </span>
          </div>
        </td>
        <td><strong class="text-primary">${nomeCompleto}</strong></td>
        <td><span class="badge bg-light text-dark border">${classe}</span></td>
        <td>${areaBadge}</td>
        <td>${turma}</td>
        <td><small class="text-muted">${doc}</small></td>
        <td class="text-center"><span class="badge ${a.genero === 'F' ? 'bg-info text-dark' : 'bg-secondary'}">${a.genero || 'M'}</span></td>
        <td><small>${encarregado}</small></td>
        <td><span class="badge ${isAtivo ? 'bg-success' : 'bg-secondary'}">${a.status || 'ATIVO'}</span></td>
        <td class="text-end">
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-primary" onclick="modalEditarAluno('${a.id}')" title="Editar Dados Cadastrais"><i class="bi bi-pencil"></i></button>
            <button class="btn btn-outline-warning" onclick="modalTransferirAluno('${a.id}')" title="Transferir / Atribuir Turma"><i class="bi bi-arrow-left-right"></i></button>
            <button class="btn btn-outline-danger" onclick="excluirAluno('${a.id}')" title="Eliminar Aluno"><i class="bi bi-trash"></i></button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

