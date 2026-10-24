/**
 * SIGE - PAINEL-PROFESSOR | Caderneta Oficial MEC
 * Ficheiro de código independente do menu: caderneta.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 7. CADERNETA DO PROFESSOR (NAVEGAÇÃO EM 3 NÍVEIS & MAPA OFICIAL) ====================
window.inicializarNavegacaoCaderneta = async function(forcarRecarregar = false) {
  try {
    const isDocente = state.user?.role === 'PROFESSOR';
    const wrapperProf = document.getElementById('wrapperFiltroProfessorCaderneta');
    const badgePerfil = document.getElementById('cadernetaBadgePerfil');

    if (badgePerfil) {
      if (isDocente) {
        badgePerfil.className = 'badge bg-success-subtle text-success border border-success-subtle px-2 py-1';
        badgePerfil.innerHTML = `<i class="bi bi-person-check-fill me-1"></i>Minhas Turmas Atribuídas: ${state.user.nome}`;
      } else {
        badgePerfil.className = 'badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1';
        badgePerfil.innerHTML = `<i class="bi bi-shield-lock-fill me-1"></i>Visão Administrativa da Escola`;
      }
    }

    // Se o utilizador for Admin / DAP, carregar seletor de professores
    if (!isDocente && wrapperProf) {
      wrapperProf.style.display = 'block';
      await carregarSelectProfessoresCaderneta();
    } else if (wrapperProf) {
      wrapperProf.style.display = 'none';
    }

    // Carregar alocações se vazio ou forçado
    if (forcarRecarregar || !state.alocacoesDocente || state.alocacoesDocente.length === 0) {
      let url = '/api/v1/professores/minhas-turmas';
      if (!isDocente && state.cadernetaProfessorFiltroId && state.cadernetaProfessorFiltroId !== 'TODOS') {
        url += `?professor_id=${state.cadernetaProfessorFiltroId}`;
      }
      const resTurmas = await apiFetch(url);
      if (resTurmas.success) {
        state.alocacoesDocente = resTurmas.data || [];
      } else {
        state.alocacoesDocente = [];
      }
    }

    renderizarBotoesClassesCaderneta();
  } catch (err) {
    console.error('Erro ao inicializar navegação da caderneta:', err);
  }
};

async function carregarSelectProfessoresCaderneta() {
  const selectProf = document.getElementById('cadernetaFiltroProfessor');
  if (!selectProf) return;

  try {
    const resProfs = await apiFetch('/api/v1/professores');
    const professores = resProfs.data || [];
    let html = '<option value="TODOS">Todos os Professores (Visão Geral)</option>';
    professores.forEach(p => {
      const isSel = p.id === state.cadernetaProfessorFiltroId ? 'selected' : '';
      html += `<option value="${p.id}" ${isSel}>${p.nome} ${p.apelido || ''} (${p.especialidade || p.carreira || 'Docente'})</option>`;
    });
    selectProf.innerHTML = html;
  } catch (e) {
    console.error('Erro ao carregar lista de professores para caderneta:', e);
  }
}

window.aoMudarFiltroProfessorCaderneta = async function(profId) {
  state.cadernetaProfessorFiltroId = profId;
  state.cadernetaClasseSelecionada = null;
  state.cadernetaAreaSelecionada = null;
  state.cadernetaAlocacaoSelecionadaId = null;
  await window.inicializarNavegacaoCaderneta(true);
};

function renderizarBotoesClassesCaderneta() {
  const container = document.getElementById('containerCadernetaClasses');
  const countEl = document.getElementById('contagemClassesCaderneta');
  const seccaoArea = document.getElementById('seccaoAreasCaderneta');
  const seccaoTurmas = document.getElementById('seccaoCadernetasDisponiveis');
  if (!container) return;

  const alocs = state.alocacoesDocente || [];
  if (alocs.length === 0) {
    container.innerHTML = `
      <div class="alert alert-warning py-3 px-3 small mb-0 w-100 border text-center">
        <i class="bi bi-info-circle-fill me-2 fs-5 text-warning align-middle"></i>
        <span>Nenhuma turma ou caderneta atribuída encontrada para este utilizador / perfil.</span>
      </div>
    `;
    if (countEl) countEl.textContent = '0 classes';
    if (seccaoArea) seccaoArea.style.display = 'none';
    if (seccaoTurmas) seccaoTurmas.style.display = 'none';
    limparCabecalhoCaderneta();
    return;
  }

  // Extrair classes únicas das alocações
  const classesSet = new Set();
  alocs.forEach(a => {
    const grau = a.turma_grau || a.turma?.grau_ano || '';
    if (grau) classesSet.add(grau.trim());
  });

  const ordem = ['7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'];
  const classesDisponiveis = Array.from(classesSet).sort((a, b) => {
    const idxA = ordem.indexOf(a);
    const idxB = ordem.indexOf(b);
    if (idxA !== -1 && idxB !== -1) return idxA - idxB;
    return a.localeCompare(b);
  });

  if (countEl) {
    countEl.textContent = `${classesDisponiveis.length} ${classesDisponiveis.length === 1 ? 'classe' : 'classes'}`;
  }

  if (!state.cadernetaClasseSelecionada || !classesDisponiveis.includes(state.cadernetaClasseSelecionada)) {
    state.cadernetaClasseSelecionada = classesDisponiveis[0] || null;
  }

  const selectClasse = document.getElementById('selectCadernetaClasse');
  if (selectClasse) {
    selectClasse.disabled = false;
    selectClasse.innerHTML = classesDisponiveis.map(cls => {
      const qtdAlocs = alocs.filter(a => (a.turma_grau || a.turma?.grau_ano || '').trim() === cls).length;
      return `<option value="${cls}">${cls} (${qtdAlocs} ${qtdAlocs === 1 ? 'turma' : 'turmas'})</option>`;
    }).join('');
    selectClasse.value = state.cadernetaClasseSelecionada;
  }

  if (state.cadernetaClasseSelecionada) {
    renderizarBotoesAreasCaderneta(state.cadernetaClasseSelecionada);
  }
}

window.aoMudarSelectClasseCaderneta = function(classe) {
  state.cadernetaClasseSelecionada = classe;
  state.cadernetaAreaSelecionada = null;
  state.cadernetaAlocacaoSelecionadaId = null;
  renderizarBotoesAreasCaderneta(classe);
};

window.selecionarClasseCaderneta = function(classe) {
  const sel = document.getElementById('selectCadernetaClasse');
  if (sel) sel.value = classe;
  aoMudarSelectClasseCaderneta(classe);
};

function renderizarBotoesAreasCaderneta(classe) {
  const selectArea = document.getElementById('selectCadernetaArea');
  const countEl = document.getElementById('contagemAreasCaderneta');

  const alocsClasse = (state.alocacoesDocente || []).filter(a => {
    const grau = a.turma_grau || a.turma?.grau_ano || '';
    return normalizarClasse(grau) === normalizarClasse(classe);
  });

  const areasSet = new Set();
  alocsClasse.forEach(a => {
    const ar = a.turma_area || a.turma?.area || 'Ensino Geral';
    areasSet.add(normalizarArea(ar));
  });

  const areasDisponiveis = Array.from(areasSet);
  if (countEl) {
    countEl.textContent = `${areasDisponiveis.length} ${areasDisponiveis.length === 1 ? 'secção' : 'secções'}`;
  }

  if (areasDisponiveis.length === 0) {
    if (selectArea) {
      selectArea.innerHTML = '<option value="">Nenhuma secção disponível</option>';
      selectArea.disabled = true;
    }
    const selectAloc = document.getElementById('selectCadernetaAlocacao');
    if (selectAloc) {
      selectAloc.innerHTML = '<option value="">Sem turmas</option>';
      selectAloc.disabled = true;
    }
    limparCabecalhoCaderneta();
    return;
  }

  if (!state.cadernetaAreaSelecionada || !areasDisponiveis.includes(state.cadernetaAreaSelecionada)) {
    state.cadernetaAreaSelecionada = areasDisponiveis[0];
  }

  if (selectArea) {
    selectArea.disabled = false;
    selectArea.innerHTML = areasDisponiveis.map(ar => {
      const qtdAlocs = alocsClasse.filter(a => normalizarArea(a.turma_area || a.turma?.area || 'Ensino Geral') === ar).length;
      return `<option value="${ar}">${ar} (${qtdAlocs} ${qtdAlocs === 1 ? 'turma' : 'turmas'})</option>`;
    }).join('');
    selectArea.value = state.cadernetaAreaSelecionada;
  }

  if (state.cadernetaAreaSelecionada) {
    renderizarBotoesCadernetasDisponiveis(classe, state.cadernetaAreaSelecionada);
  }
}

window.aoMudarSelectAreaCaderneta = function(area) {
  state.cadernetaAreaSelecionada = area;
  state.cadernetaAlocacaoSelecionadaId = null;
  renderizarBotoesCadernetasDisponiveis(state.cadernetaClasseSelecionada, area);
};

window.selecionarAreaCaderneta = function(area) {
  const sel = document.getElementById('selectCadernetaArea');
  if (sel) sel.value = area;
  aoMudarSelectAreaCaderneta(area);
};

function renderizarBotoesCadernetasDisponiveis(classe, area) {
  const selectAloc = document.getElementById('selectCadernetaAlocacao');
  const countEl = document.getElementById('contagemTurmasCaderneta');
  const hiddenSelectAloc = document.getElementById('cadernetaAlocacaoSelect');

  const alocsArea = (state.alocacoesDocente || []).filter(a => {
    const grau = a.turma_grau || a.turma?.grau_ano || '';
    const aArea = a.turma_area || a.turma?.area || 'Ensino Geral';
    return normalizarClasse(grau) === normalizarClasse(classe) && normalizarArea(aArea) === normalizarArea(area);
  });

  // Ordenar turmas de forma natural e consistente: Turma 1, Turma 2, Turma 3...
  alocsArea.sort((a, b) => {
    const tA = (a.turma?.nome || a.turma_nome || '').trim();
    const tB = (b.turma?.nome || b.turma_nome || '').trim();
    const cmp = tA.localeCompare(tB, undefined, { numeric: true, sensitivity: 'base' });
    if (cmp !== 0) return cmp;
    const dA = (a.disciplina?.nome || a.disciplina_nome || '').trim();
    const dB = (b.disciplina?.nome || b.disciplina_nome || '').trim();
    return dA.localeCompare(dB, undefined, { numeric: true, sensitivity: 'base' });
  });

  if (countEl) {
    countEl.textContent = `${alocsArea.length} ${alocsArea.length === 1 ? 'turma' : 'turmas'}`;
  }

  if (alocsArea.length === 0) {
    if (selectAloc) {
      selectAloc.innerHTML = '<option value="">Nenhuma turma disponível nesta secção</option>';
      selectAloc.disabled = true;
    }
    limparCabecalhoCaderneta();
    return;
  }

  // Auto-selecionar primeira caderneta se nenhuma activa
  if (!state.cadernetaAlocacaoSelecionadaId || !alocsArea.some(a => a.id === state.cadernetaAlocacaoSelecionadaId)) {
    state.cadernetaAlocacaoSelecionadaId = alocsArea[0].id;
  }

  if (selectAloc) {
    selectAloc.disabled = false;
    selectAloc.innerHTML = alocsArea.map(a => {
      const turmaNome = a.turma?.nome || a.turma_nome || 'Turma';
      const discNome = a.disciplina?.nome || a.disciplina_nome || 'Disciplina';
      const turno = a.turma?.turno || a.turma_turno || 'MANHA';
      return `<option value="${a.id}">${turmaNome} — ${discNome} (${turno})</option>`;
    }).join('');
    selectAloc.value = state.cadernetaAlocacaoSelecionadaId;
  }

  // Botoes rapidos de turmas removidos: seleccao feita pelo dropdown selectCadernetaAlocacao

  if (hiddenSelectAloc) {
    hiddenSelectAloc.innerHTML = alocsArea.map(a => 
      `<option value="${a.id}">${a.disciplina?.nome || a.disciplina_nome} — ${a.turma?.nome || a.turma_nome}</option>`
    ).join('');
    hiddenSelectAloc.value = state.cadernetaAlocacaoSelecionadaId;
  }

  // Dados omitidos na abertura inicial: aguardando clique em Buscar pelo seletor de ano ou busca
  // carregarCadernetaDocente(state.cadernetaAlocacaoSelecionadaId);
}

window.aoMudarSelectAlocacaoCaderneta = function(alocId) {
  state.cadernetaAlocacaoSelecionadaId = alocId;
  const hiddenSelectAloc = document.getElementById('cadernetaAlocacaoSelect');
  if (hiddenSelectAloc) hiddenSelectAloc.value = alocId;

  // Estado visual dos botoes de turmas removido junto com os proprios botoes

  carregarCadernetaDocente(alocId);
};

window.selecionarAlocacaoCaderneta = function(alocacaoId) {
  const sel = document.getElementById('selectCadernetaAlocacao');
  if (sel) sel.value = alocacaoId;
  aoMudarSelectAlocacaoCaderneta(alocacaoId);
};

function limparCabecalhoCaderneta() {
  if (document.getElementById('cadBoxDisciplina')) document.getElementById('cadBoxDisciplina').textContent = '-';
  if (document.getElementById('cadBoxProfessor')) document.getElementById('cadBoxProfessor').textContent = '-';
  if (document.getElementById('cadBoxContacto')) document.getElementById('cadBoxContacto').textContent = '-';
  if (document.getElementById('cadBoxArea')) document.getElementById('cadBoxArea').textContent = '-';
  if (document.getElementById('cadBoxTurmaDirector')) document.getElementById('cadBoxTurmaDirector').textContent = '-';
  if (document.getElementById('cadBoxClasseTurno')) document.getElementById('cadBoxClasseTurno').textContent = '-';
  if (document.getElementById('cadBoxEfectivo')) document.getElementById('cadBoxEfectivo').textContent = 'H: 0 | M: 0 | Total: 0';
  const tbody = document.getElementById('tabelaCadernetaCorpo');
  if (tbody) tbody.innerHTML = '<tr><td colspan="32" class="text-center py-4 text-muted">Selecione uma turma e disciplina para visualizar a Caderneta Oficial.</td></tr>';
}

window.destacarTrimestreTabelaCaderneta = function(periodo) {
  const tabela = document.querySelector('.caderneta-tabela');
  if (!tabela) return;

  // Se período for TODOS, restaura visualização padrão
  const thCols = tabela.querySelectorAll('thead th');
  thCols.forEach(th => th.style.opacity = '1');
  const tdCols = tabela.querySelectorAll('tbody td, tfoot td');
  tdCols.forEach(td => td.style.opacity = '1');
};

async function carregarCadernetaDocente(alocacaoIdParam = null) {
  try {
    const selectAloc = document.getElementById('cadernetaAlocacaoSelect');
    const alocacaoId = alocacaoIdParam || state.cadernetaAlocacaoSelecionadaId || selectAloc?.value;
    if (!alocacaoId) {
      limparCabecalhoCaderneta();
      return;
    }

    state.alocacaoAtualId = alocacaoId;
    state.cadernetaAlocacaoSelecionadaId = alocacaoId;

    const resCaderneta = await apiFetch(`/api/v1/professores/caderneta/${alocacaoId}/completa`);
    if (!resCaderneta.success) {
      limparCabecalhoCaderneta();
      return;
    }
    const d = resCaderneta.data || resCaderneta;

    // Preencher Caixas de Cabeçalho Institucional Oficial automaticamente com os dados cadastrados
    if (document.getElementById('cadHeaderEscola')) {
      document.getElementById('cadHeaderEscola').textContent = (d.escola?.nome || state.tenant?.nome || 'REPÚBLICA DE MOÇAMBIQUE').toUpperCase();
      document.getElementById('cadHeaderSub').textContent = `PROVÍNCIA DE ${d.escola?.provincia || state.tenant?.provincia || 'MAPUTO'} | DISTRITO DE ${d.escola?.distrito || state.tenant?.distrito || 'CIDADE DE MAPUTO'}`.toUpperCase();
      document.getElementById('cadHeaderAno').textContent = d.turma?.ano_letivo || state.tenant?.ano_letivo_ativo || '2026';

      const discNome = d.disciplina?.nome || '-';
      const discCod = d.disciplina?.codigo ? ` (${d.disciplina.codigo})` : '';
      document.getElementById('cadBoxDisciplina').textContent = `${discNome}${discCod}`;

      const profNome = `${d.professor?.nome || d.alocacao?.professor_nome || '-'} ${d.professor?.apelido || ''}`.trim();
      document.getElementById('cadBoxProfessor').textContent = profNome;
      document.getElementById('cadBoxContacto').textContent = d.professor?.telefone || d.alocacao?.professor_telefone || '-';
      document.getElementById('cadBoxArea').textContent = d.professor?.especialidade || d.alocacao?.professor_especialidade || d.turma?.area || 'Ensino Geral';

      const dtNome = d.directorTurma?.nome && d.directorTurma.nome !== '-' ? d.directorTurma.nome : (d.turma?.director_turma_nome || d.alocacao?.director_turma_nome || '-');
      document.getElementById('cadBoxTurmaDirector').textContent = `${d.turma?.nome || d.alocacao?.turma_nome || '-'} | DT: ${dtNome}`;
      document.getElementById('cadBoxClasseTurno').textContent = `${d.turma?.grau_ano || d.alocacao?.turma_grau || '-'} | ${d.turma?.turno || d.alocacao?.turma_turno || 'Diurno'}`;
      document.getElementById('cadBoxEfectivo').textContent = `H: ${d.efectivo?.h || 0} | M: ${d.efectivo?.m || 0} | Total: ${d.efectivo?.total || 0}`;
    }

    const infoResumo = document.getElementById('cadernetaInfoResumo');
    if (infoResumo) {
      infoResumo.innerHTML = `<span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="bi bi-check-circle-fill me-1"></i> Caderneta Sincronizada: <strong>${(d.alunos || []).length} alunos</strong></span>`;
    }

    // Preencher Tabela de Alunos com todos os 3 Trimestres (Imagem 2)
    const tbody = document.getElementById('tabelaCadernetaCorpo');
    if (!tbody) return;

    if (!d.alunos || d.alunos.length === 0) {
      tbody.innerHTML = '<tr><td colspan="32" class="text-center py-4 text-muted"><i class="bi bi-info-circle me-1"></i> Nenhum aluno matriculado nesta turma.</td></tr>';
      return;
    }

    const notaValida = (val) => {
      if (val === null || val === undefined || val === '' || val === '-') return false;
      const num = Number(val);
      return !isNaN(num) && num >= 0 && num <= 20;
    };

    const temRequisitosCadernetaMT = (trimData) => {
      if (!trimData) return false;
      return notaValida(trimData.t1) && notaValida(trimData.t2) && notaValida(trimData.at);
    };

    const formatVal = (val, isMedia = false) => {
      if (val === null || val === undefined || isNaN(val) || val <= 0) return '<span class="text-muted">-</span>';
      const num = Number(val);
      const cls = num >= 9.5 ? 'nota-positiva' : 'nota-negativa';
      const displayVal = isMedia ? Math.round(num) : (Number.isInteger(num) ? num : num.toFixed(1));
      return `<span class="${cls}">${displayVal}</span>`;
    };

    const formatMT = (trimData) => {
      if (!temRequisitosCadernetaMT(trimData)) return '<span class="text-muted">-</span>';
      return formatVal(trimData.mt, true);
    };

    const formatComportamento = (trimData) => {
      if (!trimData) return '<span class="text-muted">-</span>';
      if (!temRequisitosCadernetaMT(trimData) || !trimData.comportamento) return '<span class="text-muted">-</span>';
      return `<small class="fw-semibold">${trimData.comportamento}</small>`;
    };

    tbody.innerHTML = d.alunos.map((a, idx) => {
      const t1TemMT = temRequisitosCadernetaMT(a.t1);
      const t2TemMT = temRequisitosCadernetaMT(a.t2);
      const t3TemMT = temRequisitosCadernetaMT(a.t3);
      const podeExibirMFD = t1TemMT && t2TemMT && t3TemMT && (a.mfd !== null && a.mfd !== undefined && a.mfd > 0);

      return `
        <tr>
          <td><strong>${idx + 1}</strong></td>
          <td class="text-start" style="cursor: pointer;" onclick="modalSalvarNotaCaderneta('${a.alunoId}')" title="Clique para lançar avaliações deste aluno"><strong class="text-primary">${a.nome}</strong> <i class="bi bi-pencil-square text-muted ms-1 small no-print d-print-none"></i></td>
          <td class="text-start">${a.apelido || '-'}</td>
          <td><span class="badge ${a.genero === 'F' ? 'bg-info text-dark' : 'bg-secondary'}">${a.genero}</span></td>
          <!-- 1º Trimestre -->
          <td>${formatVal(a.t1.t1)}</td>
          <td>${formatVal(a.t1.t2)}</td>
          <td>${formatVal(a.t1.t3)}</td>
          <td class="bg-light">${formatVal(a.t1.map)}</td>
          <td>${formatVal(a.t1.mas ?? a.t1.mac3)}</td>
          <td>${formatVal(a.t1.at)}</td>
          <td class="bg-light fw-bold fs-6">${formatMT(a.t1)}</td>
          <td>${formatComportamento(a.t1)}</td>
          <td><span class="badge bg-light text-dark border">${a.t1.anotacao || '-'}</span></td>
          <!-- 2º Trimestre -->
          <td>${formatVal(a.t2.t1)}</td>
          <td>${formatVal(a.t2.t2)}</td>
          <td>${formatVal(a.t2.t3)}</td>
          <td class="bg-light">${formatVal(a.t2.map)}</td>
          <td>${formatVal(a.t2.mas ?? a.t2.mac3)}</td>
          <td>${formatVal(a.t2.at)}</td>
          <td class="bg-light fw-bold fs-6">${formatMT(a.t2)}</td>
          <td>${formatComportamento(a.t2)}</td>
          <td><span class="badge bg-light text-dark border">${a.t2.anotacao || '-'}</span></td>
          <!-- 3º Trimestre -->
          <td>${formatVal(a.t3.t1)}</td>
          <td>${formatVal(a.t3.t2)}</td>
          <td>${formatVal(a.t3.t3)}</td>
          <td class="bg-light">${formatVal(a.t3.map)}</td>
          <td>${formatVal(a.t3.mas ?? a.t3.mac3)}</td>
          <td>${formatVal(a.t3.at)}</td>
          <td class="bg-light fw-bold fs-6">${formatMT(a.t3)}</td>
          <td>${formatComportamento(a.t3)}</td>
          <td><span class="badge bg-light text-dark border">${a.t3.anotacao || '-'}</span></td>
          <!-- MFD: só exibe quando as médias dos 3 trimestres estiverem disponíveis -->
          <td class="bg-light fw-bold fs-6">${podeExibirMFD ? formatVal(a.mfd, true) : '<span class="text-muted">-</span>'}</td>
        </tr>
      `;
    }).join('');

    // Preencher Linhas de Estatística por Coluna no Rodapé (Imagem 2)
    const tfoot = document.getElementById('tabelaCadernetaRodape');
    if (tfoot && d.estatisticasColunas) {
      const stats = d.estatisticasColunas;
      const chavesColunas = [
        't1_t1', 't1_t2', 't1_t3', 't1_map', 't1_mas', 't1_at', 't1_mt', null, null,
        't2_t1', 't2_t2', 't2_t3', 't2_map', 't2_mas', 't2_at', 't2_mt', null, null,
        't3_t1', 't3_t2', 't3_t3', 't3_map', 't3_mas', 't3_at', 't3_mt', null, null,
        'mfd'
      ];

      // Garantir que faixas e média existam calculando dinamicamente a partir de d.alunos se não vierem da API
      chavesColunas.forEach(key => {
        if (!key) return;
        const colStat = stats[key] || stats[key.replace('_mas', '_mac3')];
        if (colStat && (!colStat.faixas || colStat.media === undefined)) {
          const [per, cmp] = key.includes('_') ? key.split('_') : [null, key];
          const notasValidas = (d.alunos || []).map(al => {
            if (cmp === 'mt' && per) {
              if (!temRequisitosCadernetaMT(al[per])) return null;
            }
            const v = per ? al[per]?.[cmp] : al[cmp];
            return (v !== null && v !== undefined && v !== '' && !isNaN(v) && Number(v) > 0) ? Number(v) : null;
          }).filter(v => v !== null);

          const tot = notasValidas.length;
          colStat.media = tot > 0 ? Number((notasValidas.reduce((a, b) => a + b, 0) / tot).toFixed(1)) : 0;
          colStat.faixas = {
            f0_94: { total: notasValidas.filter(n => n < 9.5).length },
            f95_134: { total: notasValidas.filter(n => n >= 9.5 && n < 13.5).length },
            f135_164: { total: notasValidas.filter(n => n >= 13.5 && n < 16.5).length },
            f165_184: { total: notasValidas.filter(n => n >= 16.5 && n < 18.5).length },
            f185_20: { total: notasValidas.filter(n => n >= 18.5).length },
          };
        }
      });

      const renderCelulasEstatistica = (extrator) => {
        return chavesColunas.map(key => {
          if (!key) return '<td class="bg-light text-muted">-</td>';
          const colStat = stats[key] || stats[key.replace('_mas', '_mac3')];
          if (!colStat) return '<td>-</td>';
          return `<td>${extrator(colStat)}</td>`;
        }).join('');
      };

      tfoot.innerHTML = `
        <!-- Linha Parametro estatistico conforme a foto -->
        <tr class="table-secondary fw-bold text-center text-uppercase" style="letter-spacing: 0.5px;">
          <td colspan="${4 + chavesColunas.length}">Parametro estatistico</td>
        </tr>

        <!-- 1. Avaliados: M, F, M+F (3 Linhas Separadas Oficial Imagem 2) -->
        <tr>
          <td rowspan="3" class="text-start ps-2 fw-bold align-middle bg-light border-end">Avaliados</td>
          <td colspan="3" class="fw-bold bg-light">M</td>
          ${renderCelulasEstatistica(s => s.avaliados ? (s.avaliados.h ?? s.avaliados.m ?? 0) : '-')}
        </tr>
        <tr>
          <td colspan="3" class="fw-bold bg-light">F</td>
          ${renderCelulasEstatistica(s => s.avaliados ? (s.avaliados.f ?? s.avaliados.m ?? 0) : '-')}
        </tr>
        <tr class="table-secondary">
          <td colspan="3" class="fw-bold">M+F</td>
          ${renderCelulasEstatistica(s => s.avaliados ? `<strong>${s.avaliados.total}</strong>` : '-')}
        </tr>

        <!-- 2. Positivos: M, F, M+F (3 Linhas Separadas Oficial Imagem 2) -->
        <tr>
          <td rowspan="3" class="text-start ps-2 fw-bold align-middle text-success bg-light border-end">Positivos</td>
          <td colspan="3" class="fw-semibold text-success bg-light">M</td>
          ${renderCelulasEstatistica(s => s.positivas ? (s.positivas.h ?? 0) : '-')}
        </tr>
        <tr>
          <td colspan="3" class="fw-semibold text-success bg-light">F</td>
          ${renderCelulasEstatistica(s => s.positivas ? (s.positivas.m ?? 0) : '-')}
        </tr>
        <tr class="table-success bg-opacity-25">
          <td colspan="3" class="fw-bold text-success">M+F</td>
          ${renderCelulasEstatistica(s => s.positivas ? `<strong>${s.positivas.total}</strong>` : '-')}
        </tr>

        <!-- 3. % Positivos: M, F, M+F (3 Linhas Separadas Oficial Imagem 2) -->
        <tr>
          <td rowspan="3" class="text-start ps-2 fw-bold align-middle text-success bg-light border-end">% Positivos</td>
          <td colspan="3" class="fw-semibold text-success bg-light">M</td>
          ${renderCelulasEstatistica(s => s.positivas ? (s.positivas.pctH !== undefined ? `${s.positivas.pctH}%` : '-') : '-')}
        </tr>
        <tr>
          <td colspan="3" class="fw-semibold text-success bg-light">F</td>
          ${renderCelulasEstatistica(s => s.positivas ? (s.positivas.pctM !== undefined ? `${s.positivas.pctM}%` : '-') : '-')}
        </tr>
        <tr class="table-success bg-opacity-25">
          <td colspan="3" class="fw-bold text-success">M+F</td>
          ${renderCelulasEstatistica(s => s.positivas ? `<strong>${s.positivas.pct}%</strong>` : '-')}
        </tr>

        <!-- 4. Negativos: M, F, M+F (3 Linhas Separadas Oficial Imagem 2) -->
        <tr>
          <td rowspan="3" class="text-start ps-2 fw-bold align-middle text-danger bg-light border-end">Negativos</td>
          <td colspan="3" class="fw-semibold text-danger bg-light">M</td>
          ${renderCelulasEstatistica(s => s.negativas ? (s.negativas.h ?? 0) : '-')}
        </tr>
        <tr>
          <td colspan="3" class="fw-semibold text-danger bg-light">F</td>
          ${renderCelulasEstatistica(s => s.negativas ? (s.negativas.m ?? 0) : '-')}
        </tr>
        <tr class="table-danger bg-opacity-25">
          <td colspan="3" class="fw-bold text-danger">M+F</td>
          ${renderCelulasEstatistica(s => s.negativas ? `<strong>${s.negativas.total}</strong>` : '-')}
        </tr>

        <!-- 5. % Negativos: M, F, M+F (3 Linhas Separadas Oficial Imagem 2) -->
        <tr>
          <td rowspan="3" class="text-start ps-2 fw-bold align-middle text-danger bg-light border-end">% Negativos</td>
          <td colspan="3" class="fw-semibold text-danger bg-light">M</td>
          ${renderCelulasEstatistica(s => s.negativas ? (s.negativas.pctH !== undefined ? `${s.negativas.pctH}%` : '-') : '-')}
        </tr>
        <tr>
          <td colspan="3" class="fw-semibold text-danger bg-light">F</td>
          ${renderCelulasEstatistica(s => s.negativas ? (s.negativas.pctM !== undefined ? `${s.negativas.pctM}%` : '-') : '-')}
        </tr>
        <tr class="table-danger bg-opacity-25">
          <td colspan="3" class="fw-bold text-danger">M+F</td>
          ${renderCelulasEstatistica(s => s.negativas ? `<strong>${s.negativas.pct}%</strong>` : '-')}
        </tr>

        <!-- 6. Faixas oficiais (0 a 9,4 | 9,5 a 13,4 | 13,5 a 16,4 | 16,5 a 18,4 | 18,5 a 20) -->
        <tr>
          <td colspan="4" class="text-start ps-2 fw-semibold bg-light">0 a 9,4</td>
          ${renderCelulasEstatistica(s => (s.avaliados?.total > 0 && s.faixas?.f0_94?.total !== undefined) ? s.faixas.f0_94.total : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-2 fw-semibold bg-light">9,5 a 13,4</td>
          ${renderCelulasEstatistica(s => (s.avaliados?.total > 0 && s.faixas?.f95_134?.total !== undefined) ? s.faixas.f95_134.total : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-2 fw-semibold bg-light">13,5 a 16,4</td>
          ${renderCelulasEstatistica(s => (s.avaliados?.total > 0 && s.faixas?.f135_164?.total !== undefined) ? s.faixas.f135_164.total : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-2 fw-semibold bg-light">16,5 a 18,4</td>
          ${renderCelulasEstatistica(s => (s.avaliados?.total > 0 && s.faixas?.f165_184?.total !== undefined) ? s.faixas.f165_184.total : '-')}
        </tr>
        <tr>
          <td colspan="4" class="text-start ps-2 fw-semibold bg-light">18,5 a 20</td>
          ${renderCelulasEstatistica(s => (s.avaliados?.total > 0 && s.faixas?.f185_20?.total !== undefined) ? s.faixas.f185_20.total : '-')}
        </tr>

        <!-- 7. Média da Coluna -->
        <tr class="table-primary fw-bold">
          <td colspan="4" class="text-start ps-2">Média da Coluna</td>
          ${renderCelulasEstatistica(s => (s.avaliados?.total > 0 && s.media > 0) ? `<strong class="text-primary">${s.media}</strong>` : '-')}
        </tr>
      `;
    }
  } catch (err) {
    console.error('Erro ao carregar caderneta:', err);
  }
}

async function exportarCadernetaExcel() {
  const table = document.querySelector('.caderneta-tabela');
  if (window.SigeExport && table && table.querySelectorAll('tbody tr').length > 0 && !table.innerText.includes('Selecione uma turma')) {
    const disciplina = document.getElementById('cadBoxDisciplina')?.innerText || 'Disciplina';
    const turma = document.getElementById('cadBoxTurmaDirector')?.innerText || 'Turma';
    const ano = document.getElementById('cadHeaderAno')?.innerText || '2026';
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Caderneta Escolar Oficial — Registo de Avaliações',
      subtitulo: `${disciplina} | ${turma} | Ano Lectivo ${ano}`,
      nomeFicheiro: `Caderneta_${disciplina}_${turma}_${ano}.xlsx`,
      metadadosExtras: {
        'Disciplina': disciplina,
        'Turma': turma,
        'Ano': ano
      }
    });
    return;
  }
  const alocId = await obterAlocacaoAtivaOuPrimeira();
  if (!alocId) {
    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao('Por favor, selecione primeiro a classe, área e turma para descarregar a caderneta em Excel.', 'warning');
    } else {
      alert('Por favor, selecione primeiro a classe, área e turma para descarregar a caderneta em Excel.');
    }
    return;
  }
  const url = `/api/v1/professores/caderneta/${alocId}/xlsx`;
  await downloadFicheiroBinario(url, `Caderneta_Oficial_2026.xlsx`);
}

async function descarregarCadernetaPdf() {
  const table = document.querySelector('.caderneta-tabela');
  if (window.SigeExport && table && table.querySelectorAll('tbody tr').length > 0 && !table.innerText.includes('Selecione uma turma')) {
    const disciplina = document.getElementById('cadBoxDisciplina')?.innerText || 'Disciplina';
    const turma = document.getElementById('cadBoxTurmaDirector')?.innerText || 'Turma';
    const ano = document.getElementById('cadHeaderAno')?.innerText || '2026';
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Caderneta Escolar Oficial — Registo de Avaliações',
      subtitulo: `${disciplina} | ${turma} | Ano Lectivo ${ano}`,
      orientacao: 'landscape',
      nomeFicheiro: `Caderneta_${disciplina}_${turma}_${ano}.pdf`,
      metadadosExtras: {
        'Disciplina': disciplina,
        'Turma': turma,
        'Ano': ano
      }
    });
    return;
  }
  const alocId = await obterAlocacaoAtivaOuPrimeira();
  if (!alocId) {
    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao('Por favor, selecione primeiro a classe, área e turma para descarregar a caderneta em PDF.', 'warning');
    } else {
      alert('Por favor, selecione primeiro a classe, área e turma para descarregar a caderneta em PDF.');
    }
    return;
  }
  await downloadFicheiroBinario(`/api/v1/professores/caderneta/${alocId}/pdf`, `Caderneta_Oficial_2026.pdf`);
}

async function exportarCadernetaWord() {
  const table = document.querySelector('.caderneta-tabela');
  if (window.SigeExport && table && table.querySelectorAll('tbody tr').length > 0 && !table.innerText.includes('Selecione uma turma')) {
    const disciplina = document.getElementById('cadBoxDisciplina')?.innerText || 'Disciplina';
    const turma = document.getElementById('cadBoxTurmaDirector')?.innerText || 'Turma';
    const ano = document.getElementById('cadHeaderAno')?.innerText || '2026';
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Caderneta Escolar Oficial — Registo de Avaliações',
      subtitulo: `${disciplina} | ${turma} | Ano Lectivo ${ano}`,
      orientacao: 'landscape',
      nomeFicheiro: `Caderneta_${disciplina}_${turma}_${ano}.docx`,
      metadadosExtras: {
        'Disciplina': disciplina,
        'Turma': turma,
        'Ano': ano
      }
    });
    return;
  }
  const alocId = await obterAlocacaoAtivaOuPrimeira();
  if (!alocId) return;
  await downloadFicheiroBinario(`/api/v1/professores/caderneta/${alocId}/docx`, `Caderneta_Oficial_2026.docx`);
}

function imprimirCadernetaOficial() {
  window.print();
}

async function modalSalvarNotaCaderneta(alunoIdPreSelecionado = null) {
  if (!state.alocacaoAtualId) return alert('Selecione uma turma e disciplina');

  const periodoFiltro = document.getElementById('cadernetaPeriodoSelect')?.value;
  const periodo = (periodoFiltro && periodoFiltro !== 'TODOS') ? periodoFiltro : '1_TRIMESTRE';

  // Validação oficial de prazos de calendarização (Expirado ou Futuro)
  try {
    const resPrazos = await apiFetch('/api/v1/notas/prazos-trimestres');
    if (resPrazos.success && resPrazos.prazos && resPrazos.prazos[periodo]) {
      const pInfo = resPrazos.prazos[periodo];
      if (!pInfo.aberto && !pInfo.sempre && state.user?.role !== 'SUPERADMIN') {
        alert(pInfo.mensagem || `Lançamento não permitido para o ${pInfo.nome}.`);
        return;
      }
    }
  } catch (errP) {
    console.warn('Verificação de prazos:', errP);
  }

  const resCaderneta = await apiFetch(`/api/v1/professores/caderneta/${state.alocacaoAtualId}/completa`);
  if (!resCaderneta.success || !resCaderneta.data.alunos?.length) {
    return alert('Não há alunos nesta turma');
  }

  const optAlunos = resCaderneta.data.alunos.map(item => {
    const isSelected = alunoIdPreSelecionado && item.alunoId === alunoIdPreSelecionado ? 'selected' : '';
    return `<option value="${item.alunoId}" ${isSelected}>${item.nome} ${item.apelido || ''}</option>`;
  }).join('');

  const listaAnotacoesPadrao = [
    { codigo: 'D', significado: 'Desistiu' },
    { codigo: 'T', significado: 'Transferido' },
    { codigo: 'VT', significado: 'Vem Transferido' },
    { codigo: 'F', significado: 'Faleceu' },
    { codigo: 'AM', significado: 'Anulou Matrícula' },
    { codigo: 'PPF', significado: 'Perdeu o Ano por Faltas' },
    { codigo: 'PDF', significado: 'Perdeu Direito por Faltas' }
  ];
  const anotacoesDisponiveis = (state.geografia.anotacoes && state.geografia.anotacoes.length > 0)
    ? state.geografia.anotacoes
    : listaAnotacoesPadrao;
  const optAnotacoes = anotacoesDisponiveis.map(a => 
    `<option value="${a.codigo}">${a.codigo} — ${a.significado || a.nome || a.codigo}</option>`
  ).join('');

  const idTurmaPadrao = resCaderneta.data?.turma?.id || resCaderneta.data?.alocacao?.turma_id || '';
  const idDisciplinaPadrao = resCaderneta.data?.disciplina?.id || resCaderneta.data?.alocacao?.disciplina_id || '';

  abrirModal('Lançar Avaliações do Aluno (Oficial MEC)', `
    <form id="formModalLancamentoNota">
      <input type="hidden" id="mlnTurmaId" value="${idTurmaPadrao}">
      <input type="hidden" id="mlnDisciplinaId" value="${idDisciplinaPadrao}">
      <div class="row g-2 mb-3">
        <div class="col-md-7">
          <label class="form-label small fw-semibold">Aluno Seleccionado</label>
          <select id="mlnAluno" class="form-select" required>${optAlunos}</select>
        </div>
        <div class="col-md-5">
          <label class="form-label small fw-semibold text-primary">Trimestre Lectivo</label>
          <select id="mlnPeriodo" class="form-select fw-semibold" required>
            <option value="1_TRIMESTRE" ${periodo === '1_TRIMESTRE' ? 'selected' : ''}>1º Trimestre</option>
            <option value="2_TRIMESTRE" ${periodo === '2_TRIMESTRE' ? 'selected' : ''}>2º Trimestre</option>
            <option value="3_TRIMESTRE" ${periodo === '3_TRIMESTRE' ? 'selected' : ''}>3º Trimestre</option>
          </select>
        </div>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-md-6">
          <label class="form-label small fw-semibold text-primary">1ª ACS (0 a 20)</label>
          <input type="number" step="any" min="0" max="20" id="mlnT1" class="form-control" placeholder="0 a 20" oninput="calcularPrevisoesCadernetaModal()">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold text-primary">2ª ACS (0 a 20)</label>
          <input type="number" step="any" min="0" max="20" id="mlnT2" class="form-control" placeholder="0 a 20" oninput="calcularPrevisoesCadernetaModal()">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold text-muted">3ª ACS (0 a 20)</label>
          <input type="number" step="any" min="0" max="20" id="mlnT3" class="form-control" placeholder="Opcional" oninput="calcularPrevisoesCadernetaModal()">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold text-muted">MAP - Aulas Práticas (0 a 20)</label>
          <input type="number" step="any" min="0" max="20" id="mlnTrabalho" class="form-control" placeholder="Opcional" oninput="calcularPrevisoesCadernetaModal()">
        </div>
        <div class="col-md-12">
          <label class="form-label small fw-semibold text-primary">AT - Avaliação Trimestral (0 a 20)</label>
          <input type="number" step="any" min="0" max="20" id="mlnAT" class="form-control" placeholder="0 a 20" oninput="calcularPrevisoesCadernetaModal()">
        </div>
      </div>

      <!-- Caixa Informativa de Médias Calculadas em Tempo Real -->
      <div class="p-3 bg-light rounded border mb-3">
        <div class="row text-center">
          <div class="col-4">
            <small class="text-muted d-block">MAS (Média ACS/MAP)</small>
            <strong id="previewMlnMAS" class="text-primary fs-6">-</strong>
          </div>
          <div class="col-4">
            <small class="text-muted d-block">MT (Média Trimestre)</small>
            <strong id="previewMlnMT" class="text-success fs-6">-</strong>
          </div>
          <div class="col-4">
            <small class="text-muted d-block">Comportamento</small>
            <strong id="previewMlnComp" class="text-dark fs-6">-</strong>
          </div>
        </div>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Faltas no Trimestre</label>
          <input type="number" id="mlnFaltas" class="form-control" value="0" min="0">
        </div>
        <div class="col-md-8">
          <label class="form-label small fw-semibold">Anotação Especial do Aluno</label>
          <select id="mlnAnotacao" class="form-select">
            <option value="">(Nenhuma)</option>
            ${optAnotacoes}
          </select>
        </div>
      </div>

      <button type="submit" class="btn btn-primary w-100">
        <i class="bi bi-check-circle me-1"></i> Gravar Avaliação no Trimestre
      </button>
    </form>
  `);

  const alunoIdInicial = alunoIdPreSelecionado || (resCaderneta.data.alunos[0]?.alunoId);
  const selectAluno = document.getElementById('mlnAluno');

  function carregarNotasAlunoNoModal(alunoId) {
    const pAtual = document.getElementById('mlnPeriodo')?.value || periodo;
    const aluno = resCaderneta.data.alunos.find(a => String(a.alunoId) === String(alunoId));
    const trimKey = pAtual === '2_TRIMESTRE' ? 't2' : (pAtual === '3_TRIMESTRE' ? 't3' : 't1');
    const trimData = aluno ? aluno[trimKey] : null;

    const elT1 = document.getElementById('mlnT1');
    const elT2 = document.getElementById('mlnT2');
    const elT3 = document.getElementById('mlnT3');
    const elMAP = document.getElementById('mlnTrabalho');
    const elAT = document.getElementById('mlnAT');
    const elFaltas = document.getElementById('mlnFaltas');
    const elAnotacao = document.getElementById('mlnAnotacao');

    const temNotaCadastrada = trimData && (
      (trimData.t1 !== null && trimData.t1 !== undefined) ||
      (trimData.t2 !== null && trimData.t2 !== undefined) ||
      (trimData.t3 !== null && trimData.t3 !== undefined) ||
      (trimData.map !== null && trimData.map !== undefined) ||
      (trimData.at !== null && trimData.at !== undefined)
    );

    if (temNotaCadastrada) {
      if (elT1) elT1.value = trimData.t1 !== null && trimData.t1 !== undefined ? trimData.t1 : '';
      if (elT2) elT2.value = trimData.t2 !== null && trimData.t2 !== undefined ? trimData.t2 : '';
      if (elT3) elT3.value = trimData.t3 !== null && trimData.t3 !== undefined ? trimData.t3 : '';
      if (elMAP) elMAP.value = trimData.map !== null && trimData.map !== undefined ? trimData.map : '';
      if (elAT) elAT.value = trimData.at !== null && trimData.at !== undefined ? trimData.at : '';
      if (elFaltas) elFaltas.value = trimData.faltas ?? 0;
      if (elAnotacao) elAnotacao.value = trimData.anotacao || '';
    } else {
      // Se o professor ainda não lançou nota para este aluno, tudo em branco
      if (elT1) elT1.value = '';
      if (elT2) elT2.value = '';
      if (elT3) elT3.value = '';
      if (elMAP) elMAP.value = '';
      if (elAT) elAT.value = '';
      if (elFaltas) elFaltas.value = '0';
      if (elAnotacao) elAnotacao.value = '';
    }
    calcularPrevisoesCadernetaModal();
  }

  const selectPeriodo = document.getElementById('mlnPeriodo');
  if (selectPeriodo) {
    selectPeriodo.addEventListener('change', async () => {
      const pSel = selectPeriodo.value;
      try {
        const resP = await apiFetch('/api/v1/notas/prazos-trimestres');
        if (resP.success && resP.prazos && resP.prazos[pSel]) {
          const info = resP.prazos[pSel];
          const btnSalvar = document.querySelector('#formModalLancamentoNota button[type="submit"]');
          let avisoEl = document.getElementById('avisoModalPrazoTrimestre');
          if (!info.aberto && !info.sempre && state.user?.role !== 'SUPERADMIN') {
            if (!avisoEl) {
              avisoEl = document.createElement('div');
              avisoEl.id = 'avisoModalPrazoTrimestre';
              selectPeriodo.parentNode.appendChild(avisoEl);
            }
            avisoEl.className = 'alert alert-danger small mt-2 mb-0 py-1 px-2';
            avisoEl.innerHTML = `<i class="bi bi-exclamation-octagon me-1"></i> ${info.mensagem}`;
            if (btnSalvar) btnSalvar.disabled = true;
            alert(info.mensagem);
          } else {
            if (avisoEl) avisoEl.remove();
            if (btnSalvar) btnSalvar.disabled = false;
          }
        }
      } catch (_) {}
      carregarNotasAlunoNoModal(selectAluno ? selectAluno.value : alunoIdInicial);
    });
  }

  if (selectAluno) {
    if (alunoIdInicial) selectAluno.value = alunoIdInicial;
    selectAluno.addEventListener('change', (e) => carregarNotasAlunoNoModal(e.target.value));
    carregarNotasAlunoNoModal(selectAluno.value);
  } else {
    calcularPrevisoesCadernetaModal();
  }

  document.getElementById('formModalLancamentoNota').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const aloc = state.alocacoesDocente.find(a => a.id === state.alocacaoAtualId);
      const strT1 = document.getElementById('mlnT1').value.trim();
      const strT2 = document.getElementById('mlnT2').value.trim();
      const strT3 = document.getElementById('mlnT3').value.trim();
      const strMAP = document.getElementById('mlnTrabalho').value.trim();
      const strAT = document.getElementById('mlnAT').value.trim();

      const vT1 = strT1 !== '' ? parseFloat(strT1) : null;
      const vT2 = strT2 !== '' ? parseFloat(strT2) : null;
      const vT3 = strT3 !== '' ? parseFloat(strT3) : null;
      const vMAP = strMAP !== '' ? parseFloat(strMAP) : null;
      const vAT = strAT !== '' ? parseFloat(strAT) : null;

      // Calcular médias e comportamento de forma flexível (conforme notas já lançadas)
      const testes = [];
      if (vT1 !== null && !isNaN(vT1)) testes.push(vT1);
      if (vT2 !== null && !isNaN(vT2)) testes.push(vT2);
      if (vT3 !== null && !isNaN(vT3)) testes.push(vT3);
      if (vMAP !== null && !isNaN(vMAP)) testes.push(vMAP);

      // Regra Oficial MEC: Só forma e exibe MT quando o aluno tiver no mínimo 2 ACS sendo (1ª, 2ª) e AT
      const temRequisitosMT = (vT1 !== null && !isNaN(vT1)) && (vT2 !== null && !isNaN(vT2)) && (vAT !== null && !isNaN(vAT));

      let masVal = null;
      if (testes.length > 0) {
        masVal = testes.reduce((a, b) => a + b, 0) / testes.length;
      }

      let mtVal = null;
      if (temRequisitosMT && masVal !== null) {
        mtVal = Math.round((2 * masVal + vAT) / 3);
      }

      let compAuto = '';
      if (mtVal !== null) {
        if (mtVal < 9.5) compAuto = 'NS';
        else if (mtVal <= 13.4) compAuto = 'S';
        else if (mtVal <= 16.4) compAuto = 'B';
        else if (mtVal <= 18.4) compAuto = 'MB';
        else compAuto = 'E';
      }

      // Obter IDs automaticamente da alocação da caderneta activa
      const alunoId = document.getElementById('mlnAluno')?.value || alunoIdInicial;
      const turmaId = document.getElementById('mlnTurmaId')?.value || resCaderneta.data?.turma?.id || resCaderneta.data?.alocacao?.turma_id || aloc?.turma_id || aloc?.turma?.id;
      const disciplinaId = document.getElementById('mlnDisciplinaId')?.value || resCaderneta.data?.disciplina?.id || resCaderneta.data?.alocacao?.disciplina_id || aloc?.disciplina_id || aloc?.disciplina?.id;

      if (!alunoId || !turmaId || !disciplinaId) {
        alert('Não foi possível identificar automaticamente o aluno, a turma ou a disciplina. Selecione uma turma na caderneta e tente novamente.');
        return;
      }

      const periodoEscolhido = document.getElementById('mlnPeriodo')?.value || periodo;

      const body = {
        aluno_id: alunoId,
        turma_id: turmaId,
        disciplina_id: disciplinaId,
        periodo: periodoEscolhido,
        teste1: vT1 !== null ? vT1 : null,
        teste2: vT2 !== null ? vT2 : null,
        teste3: vT3 !== null ? vT3 : null,
        trabalho: vMAP !== null ? vMAP : null,
        avaliacao_trimestral: vAT !== null ? vAT : null,
        faltas: Number(document.getElementById('mlnFaltas').value) || 0,
        anotacao: document.getElementById('mlnAnotacao').value || undefined,
        comportamento: compAuto || undefined
      };

      const res = await apiFetch('/api/v1/notas', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success) {
        fecharModal();
        await carregarCadernetaDocente();
        // Sincronizar pauta e acta em segundo plano se turmaId corresponder
        if (typeof alternarVisualizacaoPautaTurma === 'function') {
          alternarVisualizacaoPautaTurma().catch(() => {});
        }
      } else {
        alert(res.message || 'Erro ao lançar avaliação');
      }
    } catch (err) {
      alert(err.message || 'Erro ao lançar avaliação');
    }
  });
}

function calcularPrevisoesCadernetaModal() {
  const v1Str = document.getElementById('mlnT1')?.value?.trim() || '';
  const v2Str = document.getElementById('mlnT2')?.value?.trim() || '';
  const v3Str = document.getElementById('mlnT3')?.value?.trim() || '';
  const mapStr = document.getElementById('mlnTrabalho')?.value?.trim() || '';
  const atStr = document.getElementById('mlnAT')?.value?.trim() || '';

  const avaliacoes = [];
  if (v1Str !== '' && !isNaN(Number(v1Str))) avaliacoes.push(Number(v1Str));
  if (v2Str !== '' && !isNaN(Number(v2Str))) avaliacoes.push(Number(v2Str));
  if (v3Str !== '' && !isNaN(Number(v3Str))) avaliacoes.push(Number(v3Str));
  if (mapStr !== '' && !isNaN(Number(mapStr))) avaliacoes.push(Number(mapStr));

  let mas = null;
  if (avaliacoes.length > 0) {
    mas = Number((avaliacoes.reduce((a, b) => a + b, 0) / avaliacoes.length).toFixed(1));
  }

  // Regra Oficial: Só deve formar e mostrar MT quando o aluno tiver no mínimo 2 ACS sendo (1ª, 2ª) e AT
  const temRequisitosMT = (v1Str !== '' && !isNaN(Number(v1Str))) &&
                          (v2Str !== '' && !isNaN(Number(v2Str))) &&
                          (atStr !== '' && !isNaN(Number(atStr)));

  let mt = null;
  if (temRequisitosMT && mas !== null) {
    mt = Math.round((2 * mas + Number(atStr)) / 3);
  }

  let comp = '-';
  if (mt !== null) {
    if (mt < 9.5) comp = 'NS (Não Suficiente)';
    else if (mt <= 13.4) comp = 'S (Suficiente)';
    else if (mt <= 16.4) comp = 'B (Bom)';
    else if (mt <= 18.4) comp = 'MB (Muito Bom)';
    else comp = 'E (Excelente)';
  }

  const elMas = document.getElementById('previewMlnMAS');
  const elMt = document.getElementById('previewMlnMT');
  const elComp = document.getElementById('previewMlnComp');

  if (elMas) elMas.textContent = mas !== null ? mas : '-';
  if (elMt) elMt.textContent = mt !== null ? mt : '-';
  if (elComp) elComp.textContent = comp;
}

