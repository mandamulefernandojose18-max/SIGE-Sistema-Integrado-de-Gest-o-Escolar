/**
 * SIGE - PAINEL-ESCOLA | Turmas & Capacidade
 * Ficheiro de código independente do menu: turmas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 3.1 GESTÃO DEDICADA DE TURMAS & CAPACIDADE ====================
async function carregarTurmas(anoParam) {
  try {
    const selAno = document.getElementById('filtroTurmasAno');
    const ano = anoParam || (selAno ? selAno.value : null) || state.anoLectivoVisualizacao || state.tenant?.ano_letivo_ativo || '2026';
    const queryAno = (ano && ano !== 'TODOS') ? `?ano_letivo=${encodeURIComponent(ano)}` : '';

    const [resTurmas, resDisciplinas] = await Promise.all([
      apiFetch(`/api/v1/escola-admin/turmas${queryAno}`),
      apiFetch('/api/v1/disciplinas')
    ]);
    if (!resTurmas.success) return;

    state.turmasList = resTurmas.data || [];
    state.todasTurmas = resTurmas.data || [];
    if (resDisciplinas && resDisciplinas.success) {
      state.todasDisciplinas = resDisciplinas.data || [];
    }
    renderizarEstatisticasETabelaTurmas();
    if (typeof renderizarSelectoresAnoLectivo === 'function' && anoParam) {
      renderizarSelectoresAnoLectivo(ano);
    }
  } catch (err) {
    console.error('Erro ao carregar turmas:', err);
  }
}

window.aplicarFiltroAnoTurmas = async function() {
  const sel = document.getElementById('filtroTurmasAno');
  const ano = sel ? sel.value : '';
  if (!ano) {
    if (typeof mostrarToast === 'function') {
      mostrarToast('Por favor, selecione primeiro um Ano Lectivo antes de clicar em Buscar.', 'warning');
    }
    return;
  }
  if (!state.anosPorView) state.anosPorView = {};
  state.anosPorView['turmas'] = ano;
  state.anoLectivoVisualizacao = ano;

  const dynamicWrap = document.getElementById('turmasConteudoDinamico');
  if (dynamicWrap) dynamicWrap.classList.remove('d-none');
  const viewEl = document.getElementById('view-turmas');
  if (viewEl && typeof removerBloqueioVisualAnoNaoSelecionado === 'function') {
    removerBloqueioVisualAnoNaoSelecionado(viewEl);
  }

  if (typeof setCarregandoBuscaAno === 'function') setCarregandoBuscaAno(true);
  try {
    await carregarTurmas(ano);
  } finally {
    if (typeof setCarregandoBuscaAno === 'function') setCarregandoBuscaAno(false);
  }
};

function renderizarEstatisticasETabelaTurmas() {
  const turmas = state.turmasList || [];

  // Calcular métricas gerais
  const totalTurmas = turmas.length;
  let capacidadeTotal = 0;
  let alunosAlocados = 0;

  turmas.forEach(t => {
    const ocup = t._count?.alunos ?? t.total_alunos ?? 0;
    const cap = t.capacidade_maxima || 50;
    capacidadeTotal += cap;
    alunosAlocados += ocup;
  });

  const vagasLivres = Math.max(0, capacidadeTotal - alunosAlocados);
  const taxaOcupacao = capacidadeTotal > 0 ? Math.round((alunosAlocados / capacidadeTotal) * 100) : 0;

  // Actualizar Cards de Métricas no DOM
  const elTotal = document.getElementById('statTurmasTotal');
  if (elTotal) elTotal.textContent = totalTurmas;

  const elCap = document.getElementById('statTurmasCapacidade');
  if (elCap) elCap.textContent = capacidadeTotal;

  const elAlunos = document.getElementById('statTurmasAlunos');
  if (elAlunos) elAlunos.textContent = alunosAlocados;

  const elVagas = document.getElementById('statTurmasVagasLivres');
  if (elVagas) elVagas.textContent = vagasLivres;

  const elTaxa = document.getElementById('statTurmasTaxa');
  if (elTaxa) elTaxa.textContent = `${taxaOcupacao}%`;

  const elStatus = document.getElementById('statTurmasStatus');
  if (elStatus) {
    if (taxaOcupacao >= 100) {
      elStatus.className = 'badge bg-danger text-white';
      elStatus.textContent = 'Lotada';
    } else if (taxaOcupacao >= 80) {
      elStatus.className = 'badge bg-warning text-dark';
      elStatus.textContent = 'Próxima do Limite';
    } else {
      elStatus.className = 'badge bg-success text-white';
      elStatus.textContent = 'Vagas Disponíveis';
    }
  }

  // Sincronizar dinamicamente o select de filtro apenas com as Classes ou Níveis reais das turmas da escola
  const elFiltroClasse = document.getElementById('filtroTurmasClasse');
  if (elFiltroClasse) {
    const ativasEscola = typeof window.obterClassesCurricularesAtivas === 'function' ? window.obterClassesCurricularesAtivas() : [];
    const classesTurmas = Array.from(new Set([...ativasEscola, ...turmas.map(t => (t.grau_ano || '').trim()).filter(Boolean)])).sort((a, b) => {
      const numA = parseInt(a.replace(/\D/g, '')) || 0;
      const numB = parseInt(b.replace(/\D/g, '')) || 0;
      return numA - numB;
    });

    const valorSelecionado = elFiltroClasse.value || 'TODAS';
    if (classesTurmas.length === 0) {
      elFiltroClasse.innerHTML = '<option value="TODAS">-- Nenhuma classe/nível cadastrado --</option>';
    } else {
      let optCls = '<option value="TODAS">Todas as Classes / Níveis</option>';
      classesTurmas.forEach(c => {
        const isSel = (valorSelecionado === c) ? 'selected' : '';
        optCls += `<option value="${c}" ${isSel}>${c}</option>`;
      });
      elFiltroClasse.innerHTML = optCls;
      if (classesTurmas.includes(valorSelecionado)) {
        elFiltroClasse.value = valorSelecionado;
      }
    }
  }

  if (typeof atualizarFiltroAreasTurmas === 'function') {
    atualizarFiltroAreasTurmas();
  }
  aplicarFiltrosTurmas();
}

window.atualizarFiltroAreasTurmas = function() {
  const elClasse = document.getElementById('filtroTurmasClasse');
  const elArea = document.getElementById('filtroTurmasArea');
  if (!elArea) return;
  const classeSel = elClasse ? elClasse.value : 'TODAS';
  const valorAtual = elArea.value;

  const areas = typeof window.obterTodasAreasOficiais === 'function' ? window.obterTodasAreasOficiais(classeSel) : [];
  let html = '<option value="TODAS">Todas as Secções / Áreas</option>';
  areas.forEach(a => {
    html += `<option value="${a}">${a}</option>`;
  });
  elArea.innerHTML = html;
  if (areas.includes(valorAtual)) {
    elArea.value = valorAtual;
  } else {
    elArea.value = 'TODAS';
  }
};

function aplicarFiltrosTurmas() {
  const turmas = state.turmasList || [];
  const filtroClasse = document.getElementById('filtroTurmasClasse')?.value || 'TODAS';
  const filtroArea = document.getElementById('filtroTurmasArea')?.value || 'TODAS';
  const filtroTurno = document.getElementById('filtroTurmasTurno')?.value || 'TODOS';
  const filtroBusca = (document.getElementById('filtroTurmasBusca')?.value || '').toLowerCase().trim();

  const anoFiltro = document.getElementById('filtroTurmasAno')?.value || state.anoLectivoVisualizacao || state.tenant?.ano_letivo_ativo || '2026';

  const filtradas = turmas.filter(t => {
    if (anoFiltro && anoFiltro !== 'TODOS') {
      if (t.ano_letivo && String(t.ano_letivo) !== String(anoFiltro)) return false;
    }
    if (filtroClasse !== 'TODAS') {
      const clsTurma = typeof normalizarClasse === 'function' ? normalizarClasse(t.grau_ano) : (t.grau_ano || '');
      const clsFiltro = typeof normalizarClasse === 'function' ? normalizarClasse(filtroClasse) : filtroClasse;
      if (clsTurma !== clsFiltro) return false;
    }
    if (filtroArea !== 'TODAS') {
      const aTurma = typeof normalizarArea === 'function' ? normalizarArea(t.area || 'Geral') : (t.area || 'Geral');
      const aFiltro = typeof normalizarArea === 'function' ? normalizarArea(filtroArea) : filtroArea;
      if (aTurma !== aFiltro) return false;
    }
    if (filtroTurno !== 'TODOS' && (t.turno || 'MANHA') !== filtroTurno) return false;
    if (filtroBusca) {
      const matchNome = (t.nome || '').toLowerCase().includes(filtroBusca);
      const matchArea = (t.area || '').toLowerCase().includes(filtroBusca);
      const matchSala = (t.sala || '').toLowerCase().includes(filtroBusca);
      const matchDT = (t.director_turma?.nome || t.director_turma_nome || t.codigo_director_turma || '').toLowerCase().includes(filtroBusca);
      const matchDC = (t.director_classe?.nome || t.director_classe_nome || t.codigo_director_classe || '').toLowerCase().includes(filtroBusca);
      if (!matchNome && !matchArea && !matchSala && !matchDT && !matchDC) return false;
    }
    return true;
  });

  renderizarTabelaTurmasNoDOM(filtradas);
}

window.homologarDirectoresTurmaRapido = async function(turmaId, alvo = 'AMBOS') {
  try {
    const res = await apiFetch(`/api/v1/escola-admin/turmas/${turmaId}/homologar-directores`, {
      method: 'POST',
      body: JSON.stringify({ acao: 'HOMOLOGAR', alvo })
    });
    if (res.success) {
      const t = res.data || {};
      let msg = res.message || 'Homologação realizada com sucesso!';
      if (t.codigo_director_turma) msg += `\n• Código Director de Turma: ${t.codigo_director_turma}`;
      if (t.codigo_director_classe) msg += `\n• Código Director de Classe: ${t.codigo_director_classe}`;
      alert(msg);
      await carregarEscolaETurmas();
      if (typeof carregarProfessores === 'function') await carregarProfessores();
    } else {
      alert(res.message || 'Erro ao homologar nomeação');
    }
  } catch (err) {
    alert(err.message || 'Erro ao homologar nomeação');
  }
};

function renderizarTabelaTurmasNoDOM(turmas) {
  // Renderizar tanto no painel view-turmas (tabelaTurmasView) quanto no view-escola (tabelaTurmas)
  const tbodyView = document.getElementById('tabelaTurmasView');
  const tbodyEscola = document.getElementById('tabelaTurmas');
  const podeHomologar = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'].includes(state.user?.role);

  const renderDirectorCell = (nome, statusHomolog, codigoGerado, turmaId, alvo) => {
    if (!nome) return '<small class="text-muted">Não definido</small>';
    let badgeHtml = '';
    if (statusHomolog === 'HOMOLOGADO' && codigoGerado) {
      badgeHtml = `<div class="mt-1"><span class="badge bg-success-subtle text-success border border-success-subtle font-monospace" style="font-size: 0.68rem;" title="Homologado pelo Director da Escola"><i class="bi bi-patch-check-fill me-1"></i>${codigoGerado}</span></div>`;
    } else if (statusHomolog === 'PENDENTE') {
      const btnHomolog = podeHomologar
        ? `<button type="button" class="btn btn-success btn-sm py-0 px-1 ms-1" style="font-size: 0.65rem;" onclick="homologarDirectoresTurmaRapido('${turmaId}', '${alvo}')" title="Homologar Nomeação (Director da Escola)"><i class="bi bi-check2-circle"></i> Homologar</button>`
        : '';
      badgeHtml = `<div class="mt-1 d-flex align-items-center flex-wrap gap-1"><span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle" style="font-size: 0.66rem;" title="Nomeado pelo Director Pedagógico — Aguarda Homologação do Director da Escola"><i class="bi bi-hourglass-split me-1"></i>Nomeado DP (Pendente)</span>${btnHomolog}</div>`;
    }
    return `<div><small class="fw-semibold text-dark">${nome}</small>${badgeHtml}</div>`;
  };

  const gerarHtmlLinhas = (isViewPrincipal) => {
    if (turmas.length === 0) {
      return `<tr><td colspan="${isViewPrincipal ? '9' : '7'}" class="text-center py-4 text-muted"><i class="bi bi-info-circle me-1"></i> Nenhuma turma encontrada. Utilize o botão <strong>"Gerar Turmas (1, 2, 3...)"</strong> para criar as turmas da classe ou <strong>"Nova Turma"</strong>.</td></tr>`;
    }

    return turmas.map(t => {
      const ocupacao = t._count?.alunos ?? t.total_alunos ?? 0;
      const maximo = t.capacidade_maxima || 50;
      const pct = Math.min(100, Math.round((ocupacao / maximo) * 100));

      let badgeClass = 'bg-success text-white';
      let progressClass = 'bg-success';
      let statusTexto = 'Vagas livres';

      if (pct >= 100) {
        badgeClass = 'bg-danger text-white';
        progressClass = 'bg-danger';
        statusTexto = 'Capacidade atingida';
      } else if (pct >= 80) {
        badgeClass = 'bg-warning text-dark';
        progressClass = 'bg-warning';
        statusTexto = 'Próxima do limite';
      }

      const areaText = t.area || 'Geral';
      const badgeAreaHtml = typeof getBadgeAreaEstudo === 'function' ? getBadgeAreaEstudo(areaText) : `<span class="badge bg-info-subtle text-dark border border-info-subtle fw-semibold">${areaText}</span>`;
      const areaHtml = isViewPrincipal ? `<td>${badgeAreaHtml}</td>` : '';
      const salaHtml = isViewPrincipal ? `<td><small class="text-muted">${t.sala || '—'}</small></td>` : '';
      const botaoAlunosHtml = isViewPrincipal ? `
        <button class="btn btn-outline-info btn-sm py-0 px-2" onclick="abrirAlunosDaTurma('${t.id}', '${(t.grau_ano || '').replace(/'/g, "\\'")}')" title="Ver lista de alunos matriculados nesta turma">
          <i class="bi bi-people me-1"></i>Alunos
        </button>
      ` : '';

      const dtNome = t.director_turma?.nome || t.director_turma_nome || '';
      const dcNome = t.director_classe?.nome || t.director_classe_nome || '';

      return `
        <tr>
          <td><strong>${t.nome}</strong></td>
          <td>
            <span class="badge bg-light text-dark border">${t.grau_ano}</span>
            ${!isViewPrincipal && t.area && t.area !== 'Geral' ? `<span class="badge bg-info-subtle text-dark border border-info-subtle ms-1">${t.area}</span>` : ''}
          </td>
          ${areaHtml}
          <td><span class="badge bg-light text-secondary border">${t.turno || 'Diurno'}</span></td>
          ${salaHtml}
          <td>
            <div class="d-flex align-items-center justify-content-between mb-1" style="min-width: 140px; max-width: 170px;">
              <span class="badge ${badgeClass} fw-semibold">${ocupacao} / ${maximo} alunos</span>
              <small class="text-muted ms-1" style="font-size: 0.72rem;">${pct}%</small>
            </div>
            <div class="progress" style="height: 6px; min-width: 140px; max-width: 170px;">
              <div class="progress-bar ${progressClass}" style="width: ${pct}%" title="${statusTexto}: ${ocupacao}/${maximo}"></div>
            </div>
          </td>
          <td>${renderDirectorCell(dtNome, t.dt_status_homologacao, t.codigo_director_turma, t.id, 'DT')}</td>
          <td>${renderDirectorCell(dcNome, t.dc_status_homologacao, t.codigo_director_classe, t.id, 'DC')}</td>
          <td class="text-end">
            <div class="d-inline-flex gap-1">
              ${botaoAlunosHtml}
              <button class="btn btn-outline-primary btn-sm py-0 px-2" onclick="modalEditarTurma('${t.id}')" title="Editar Turma, Nomear (DP) e Homologar Directores (GD)">
                <i class="bi bi-pencil-square me-1"></i>Editar
              </button>
              <button class="btn btn-outline-danger btn-sm py-0 px-2" onclick="eliminarTurma('${t.id}', '${(t.nome || '').replace(/'/g, "\\'")}')" title="Eliminar Turma">
                <i class="bi bi-trash me-1"></i>Eliminar
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  };

  if (tbodyView) tbodyView.innerHTML = gerarHtmlLinhas(true);
  if (tbodyEscola) tbodyEscola.innerHTML = gerarHtmlLinhas(false);
}

function abrirAlunosDaTurma(turmaId, grauAno) {
  navegarPara('alunos');
  setTimeout(() => {
    const turmaObj = (state.todasTurmas || []).find(t => t.id === turmaId);
    if (typeof selecionarClasseAlunos === 'function' && grauAno) {
      selecionarClasseAlunos(grauAno, true);
    }
    setTimeout(() => {
      if (turmaObj && turmaObj.area && typeof selecionarAreaAlunos === 'function') {
        selecionarAreaAlunos(normalizarArea(turmaObj.area), true);
      }
      setTimeout(() => {
        if (typeof selecionarTurmaAlunos === 'function' && turmaId) {
          selecionarTurmaAlunos(turmaId, true);
        }
      }, 100);
    }, 100);
  }, 100);
}

function atualizarVisualizacaoLogo(logoSrc, usarEmblema = true) {
  const img = document.getElementById('confEscolaLogoPreview');
  const statusEl = document.getElementById('confEscolaLogoStatus');
  const btnRemover = document.getElementById('btnRemoverLogo');

  if (logoSrc && logoSrc.trim()) {
    if (img) img.src = logoSrc;
    if (statusEl) statusEl.textContent = 'Logótipo Próprio Activo';
    if (btnRemover) btnRemover.style.display = 'inline-block';
  } else {
    if (img) img.src = 'img/emblema-mocambique.png';
    if (statusEl) statusEl.textContent = 'Emblema Nacional (Padrão Oficial)';
    if (btnRemover) btnRemover.style.display = 'none';
  }
}

function processarUploadLogoLocal(input) {
  if (typeof window.processarUploadLogoLocal === 'function') {
    return window.processarUploadLogoLocal(input);
  }
}

function processarUrlLogo(url) {
  if (typeof window.processarUrlLogo === 'function') {
    return window.processarUrlLogo(url);
  }
}

function removerLogotipoEscola() {
  if (typeof window.removerLogotipoEscola === 'function') {
    return window.removerLogotipoEscola();
  }
}

function alternarEmblemaCheck(checked) {
  if (typeof window.alternarEmblemaCheck === 'function') {
    return window.alternarEmblemaCheck(checked);
  }
}

function atualizarDistritosEscola(provincia, distritoSelecionado = '') {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('confEscolaDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => 
      `<option value="${d}" ${d === distritoSelecionado ? 'selected' : ''}>${d}</option>`
    ).join('');
  }
}

window.extrairIdentificadorTurma = function(nome, grauAno = '') {
  if (!nome) return { tipo: 'NENHUM', val: 0, rotulo: '' };
  const limpo = String(nome).trim().replace(/\s*\(\d+\)$/, '');
  const mNum = limpo.match(/turma\s*(\d+)/i);
  if (mNum) return { tipo: 'NUMERO', val: parseInt(mNum[1]), rotulo: `Turma ${mNum[1]}` };
  const mLetra = limpo.match(/turma\s*([a-zA-Z])\b/i);
  if (mLetra) return { tipo: 'LETRA', val: mLetra[1].toUpperCase(), rotulo: `Turma ${mLetra[1].toUpperCase()}` };

  let resto = limpo;
  if (grauAno) {
    resto = resto.replace(new RegExp(grauAno.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'), 'gi'), '');
    const numsGrau = grauAno.match(/\d+/);
    if (numsGrau) {
      resto = resto.replace(new RegExp(`\\b${numsGrau[0]}[ªºa-zA-Z\\s]*classe\\b`, 'gi'), '');
      resto = resto.replace(new RegExp(`\\b${numsGrau[0]}[ªº]\\b`, 'gi'), '');
    }
  }
  const nums = resto.match(/\d+/g);
  if (nums) return { tipo: 'NUMERO', val: parseInt(nums[nums.length - 1]), rotulo: `Turma ${nums[nums.length - 1]}` };
  const letras = resto.match(/\b([a-zA-Z])\b/g);
  if (letras) return { tipo: 'LETRA', val: letras[letras.length - 1].toUpperCase(), rotulo: `Turma ${letras[letras.length - 1].toUpperCase()}` };
  return { tipo: 'OUTRO', val: limpo.toUpperCase(), rotulo: limpo };
};

window.atualizarAssistenteCriarTurma = function() {
  const grauSel = document.getElementById('mtGrau')?.value || '10ª Classe';
  const areaInput = (document.getElementById('mtArea')?.value || 'Geral').trim();
  const infoText = document.getElementById('infoAlunosPendentesCriarTurma');
  const nomeInput = document.getElementById('mtNome');
  const btnAuto = document.getElementById('btnGerarAutoCriarTurma');

  const pendentes = (state.todosAlunos || []).filter(a => {
    const semTurma = !a.turma_id && (!a.turma || typeof a.turma !== 'object' || !a.turma.nome);
    if (!semTurma) return false;
    const aCls = a.classe || a.turma_grau || '';
    if (normalizarClasse(aCls) !== normalizarClasse(grauSel)) return false;
    const aAr = (a.area || 'Geral').toLowerCase();
    const targetAr = areaInput.toLowerCase();
    if (targetAr.includes('geral') && aAr.includes('geral')) return true;
    return aAr === targetAr;
  });

  const turmasExistentes = (state.todasTurmas || []).filter(t => {
    return normalizarClasse(t.grau_ano) === normalizarClasse(grauSel);
  });

  // Calcular o próximo número disponível usando o MAIOR número já existente
  // para esta classe, globalmente (independente da secção/área) — numeração contínua sem repetições
  let maxNumTurma = 0;
  turmasExistentes.forEach(t => {
    const idInfo = window.extrairIdentificadorTurma(t.nome, t.grau_ano);
    if (idInfo.tipo === 'NUMERO' && idInfo.val > maxNumTurma) {
      maxNumTurma = idInfo.val;
    }
  });
  const proximoNum = maxNumTurma + 1;
  if (nomeInput && (!nomeInput.value || nomeInput.value.includes('Turma') || nomeInput.value.trim() === 'Turma 1')) {
    nomeInput.value = `Turma ${proximoNum}`;
  }

  const qtdTurmasAuto = Math.max(1, Math.ceil(pendentes.length / 50));

  if (infoText) {
    if (pendentes.length > 0) {
      infoText.innerHTML = `Detectados <strong>${pendentes.length} alunos</strong> matriculados na <strong>${grauSel} (${areaInput})</strong> aguardando turma. O sistema pode gerar automaticamente <strong>${qtdTurmasAuto} turma(s) (Turma ${proximoNum}...)</strong> contínuas sem conflito entre secções.`;
    } else {
      infoText.innerHTML = `Não foram detectados alunos pendentes de turma na <strong>${grauSel} (${areaInput})</strong> no momento. Próxima turma livre da classe: <strong>Turma ${proximoNum}</strong>.`;
    }
  }
};

window.executarFormacaoAutomaticaParaClasse = async function() {
  const grau = document.getElementById('mtGrau')?.value || '10ª Classe';
  const area = (document.getElementById('mtArea')?.value || 'Geral').trim();
  fecharModal();
  modalFormacaoAutomaticaTurmas(grau, area);
};

async function modalCriarTurma() {
  const profsRes = await apiFetch('/api/v1/professores');
  const optProfs = '<option value="">(Nenhum seleccionado)</option>' + 
    (profsRes.data || []).map(p => `<option value="${p.id}">${p.nome}</option>`).join('');

  abrirModal('Cadastrar Nova Turma Oficial', `
    <div class="card p-3 mb-3 border-primary bg-primary bg-opacity-10 shadow-sm" id="cardAutoAssistente">
      <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
        <div>
          <span class="badge bg-primary px-2 py-1 mb-1"><i class="bi bi-magic me-1"></i> Automação Completa Baseada nos Alunos</span>
          <div class="fw-bold text-dark small" id="infoAlunosPendentesCriarTurma">A verificar alunos matriculados...</div>
          <div class="text-muted small" style="font-size: 0.72rem;">Cria e enturma Turma 1, Turma 2, Turma 3... na base da idade, género e secção dos alunos.</div>
        </div>
        <button type="button" class="btn btn-primary btn-sm fw-bold shadow-sm" id="btnGerarAutoCriarTurma" onclick="executarFormacaoAutomaticaParaClasse()">
          <i class="bi bi-lightning-charge-fill me-1"></i> Gerar Turmas 1, 2, 3... Automaticamente
        </button>
      </div>
    </div>

    <form id="formModalTurma">
      <div class="row g-3">
        <!-- MODALIDADE: CLASSE OU NÍVEL -->
        <div class="col-md-12">
          <label class="form-label small fw-bold text-uppercase text-secondary mb-1">
            <i class="bi bi-sliders me-1 text-primary"></i> Modalidade Curricular da Turma:
          </label>
          <div class="d-flex gap-4 p-2 bg-light rounded border">
            <div class="form-check">
              <input class="form-check-input" type="radio" name="modalRegimeTurma" id="regimeTurmaClasse" value="CLASSE" checked onchange="window.alternarRegimeModalTurma(this.value)">
              <label class="form-check-label fw-semibold" for="regimeTurmaClasse">
                <i class="bi bi-mortarboard me-1 text-primary"></i> Classe (1ª à 12ª Classe)
              </label>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="radio" name="modalRegimeTurma" id="regimeTurmaNivel" value="NIVEL" onchange="window.alternarRegimeModalTurma(this.value)">
              <label class="form-check-label fw-semibold" for="regimeTurmaNivel">
                <i class="bi bi-layers me-1 text-success"></i> Nível (Nível 1, Nível 2...)
              </label>
            </div>
          </div>
        </div>

        <div class="col-md-5">
          <label class="form-label small fw-semibold">Nome da Turma *</label>
          <input type="text" id="mtNome" class="form-control" required placeholder="Ex: Turma 1">
          <small class="text-muted" style="font-size: 0.72rem;">Sugerido automaticamente com base na sequência.</small>
        </div>
        <div class="col-md-4">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <label class="form-label small fw-semibold mb-0" id="labelMtGrau">Classe / Grau *</label>
            <button type="button" id="btnAdicionarNivelTurma" class="btn btn-link btn-sm p-0 text-success fw-semibold small text-decoration-none" style="display: none;" onclick="window.promptAdicionarNivelModal('mtGrau', window.atualizarAssistenteCriarTurma)">
              <i class="bi bi-plus-circle me-1"></i>+ Adicionar Nível
            </button>
          </div>
          <select id="mtGrau" class="form-select" required onchange="if(this.value==='__NOVO_NIVEL__') { window.promptAdicionarNivelModal('mtGrau', window.atualizarAssistenteCriarTurma); } else { atualizarAssistenteCriarTurma(); }">
            <option value="1ª Classe">1ª Classe</option>
            <option value="2ª Classe">2ª Classe</option>
            <option value="3ª Classe">3ª Classe</option>
            <option value="4ª Classe">4ª Classe</option>
            <option value="5ª Classe">5ª Classe</option>
            <option value="6ª Classe">6ª Classe</option>
            <option value="7ª Classe">7ª Classe</option>
            <option value="8ª Classe">8ª Classe</option>
            <option value="9ª Classe">9ª Classe</option>
            <option value="10ª Classe">10ª Classe</option>
            <option value="11ª Classe" selected>11ª Classe</option>
            <option value="12ª Classe">12ª Classe</option>
          </select>
        </div>
        <div class="col-md-3">
          <label class="form-label small fw-semibold">Secção / Área de Estudo</label>
          <input type="text" list="listaAreasEstudoTurma" id="mtArea" class="form-control" value="Geral" placeholder="Geral / Ciências..." oninput="atualizarAssistenteCriarTurma()">
          <datalist id="listaAreasEstudoTurma">
            <option value="Geral">Tronco Comum / Geral</option>
            <option value="Ciências com Biologia">Ciências com Biologia</option>
            <option value="Ciências com Desenho">Ciências com Desenho</option>
            <option value="Letras com Geografia">Letras com Geografia</option>
            <option value="Letras com História">Letras com História</option>
          </datalist>
          <small class="text-muted" style="font-size: 0.72rem;">Secção vinculada à turma.</small>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Turno</label>
          <select id="mtTurno" class="form-select">
            <option value="MANHA">Manhã</option>
            <option value="TARDE">Tarde</option>
            <option value="NOITE">Noite</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Capacidade Máxima (Alunos)</label>
          <input type="number" id="mtCapacidade" class="form-control" value="50" min="1" max="150" required>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Sala de Aula</label>
          <input type="text" id="mtSala" class="form-control" placeholder="Ex: Sala 01">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Director de Turma</label>
          <select id="mtDirTurma" class="form-select">${optProfs}</select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Director de Classe</label>
          <select id="mtDirClasse" class="form-select">${optProfs}</select>
        </div>
      </div>
      <div class="d-flex gap-2 justify-content-end mt-4">
        <button type="button" class="btn btn-outline-secondary" onclick="fecharModal()">Cancelar</button>
        <button type="submit" class="btn btn-primary px-4"><i class="bi bi-check2-circle me-1"></i> Criar Turma Manual</button>
      </div>
    </form>
  `);

  window.alternarRegimeModalTurma = function(regime) {
    const sel = document.getElementById('mtGrau');
    const lbl = document.getElementById('labelMtGrau');
    const btnAdd = document.getElementById('btnAdicionarNivelTurma');
    if (!sel) return;
    if (regime === 'NIVEL') {
      if (lbl) lbl.textContent = 'Nível Curricular *';
      if (btnAdd) btnAdd.style.display = 'inline-block';
      const niveis = typeof window.obterNiveisInstituicao === 'function' ? window.obterNiveisInstituicao() : [];
      sel.innerHTML = typeof window.renderizarOpcoesNiveisSelect === 'function'
        ? window.renderizarOpcoesNiveisSelect(niveis)
        : (niveis.length ? niveis.map(n => `<option value="${n}">${n}</option>`).join('') + '<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>' : '<option value="">-- Nenhum nível cadastrado (+ Adicionar) --</option><option value="__NOVO_NIVEL__">➕ + Adicionar Nível...</option>');
      if (niveis.length === 0) {
        setTimeout(() => { if (typeof window.promptAdicionarNivelModal === 'function') window.promptAdicionarNivelModal('mtGrau'); }, 150);
      }
    } else {
      if (lbl) lbl.textContent = 'Classe / Grau *';
      if (btnAdd) btnAdd.style.display = 'none';
      const classes = [
        '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
        '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
      ];
      sel.innerHTML = classes.map(c => `<option value="${c}">${c}</option>`).join('');
    }
    if (typeof atualizarAssistenteCriarTurma === 'function') {
      atualizarAssistenteCriarTurma();
    }
  };

  setTimeout(() => {
    if (typeof atualizarAssistenteCriarTurma === 'function') {
      atualizarAssistenteCriarTurma();
    }
  }, 100);

  document.getElementById('formModalTurma').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const nomeTurma = document.getElementById('mtNome').value.trim();
      const grau_ano = document.getElementById('mtGrau').value;
      const area = (document.getElementById('mtArea')?.value || 'Geral').trim();

      const idInfo = window.extrairIdentificadorTurma(nomeTurma, grau_ano);
      if (idInfo.tipo === 'NUMERO' || idInfo.tipo === 'LETRA') {
        const duplicada = (state.todasTurmas || []).find(t => {
          if (normalizarClasse(t.grau_ano) !== normalizarClasse(grau_ano)) return false;
          const tId = window.extrairIdentificadorTurma(t.nome, t.grau_ano);
          return tId.tipo === idInfo.tipo && tId.val === idInfo.val;
        });
        if (duplicada) {
          alert(`Atenção: Já existe a ${idInfo.rotulo} cadastrada na ${grau_ano} (Secção/Área: "${duplicada.area || 'Geral'}", Turno: ${duplicada.turno || 'Diurno'}).\n\nNa mesma classe não pode haver turmas com a mesma numeração, independentemente da secção ou área.`);
          return;
        }
      }

      const res = await apiFetch('/api/v1/escola-admin/turmas', {
        method: 'POST',
        body: JSON.stringify({
          nome: nomeTurma,
          grau_ano: grau_ano,
          area: area,
          turno: document.getElementById('mtTurno').value,
          capacidade_maxima: parseInt(document.getElementById('mtCapacidade').value) || 50,
          sala: document.getElementById('mtSala').value,
          director_turma_id: document.getElementById('mtDirTurma').value || null,
          director_classe_id: document.getElementById('mtDirClasse').value || null
        })
      });
      if (res.success) {
        fecharModal();
        await carregarEscolaETurmas();
        if (typeof carregarAlunos === 'function') await carregarAlunos();
      } else {
        alert(res.message || 'Erro ao criar turma');
      }
    } catch (err) {
      alert('Erro ao criar turma: ' + (err.message || 'Servidor indisponível'));
    }
  });
}

async function modalCriarTurmasEmLote() {
  const graus = [
    '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
    '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
  ];
  const optGraus = graus.map(g => `<option value="${g}" ${g === '10ª Classe' ? 'selected' : ''}>${g}</option>`).join('');
  const areasLote = window.obterTodasAreasOficiais('10ª Classe');
  const optAreasLote = areasLote.map(a => `<option value="${a}" ${a === 'Ensino Geral' ? 'selected' : ''}>${a}</option>`).join('');

  abrirModal('Gerar Turmas em Lote (1, 2, 3...)', `
    <form id="formModalTurmasLote">
      <div class="alert alert-info py-2 small mb-3">
        <i class="bi bi-layers-fill me-1"></i> Crie rapidamente as turmas da classe ou nível sequencialmente com capacidade máxima definida e distribuição automática imediata dos alunos.
      </div>
      <div class="row g-3">
        <!-- MODALIDADE: CLASSE OU NÍVEL -->
        <div class="col-md-12">
          <label class="form-label small fw-bold text-uppercase text-secondary mb-1">
            <i class="bi bi-sliders me-1 text-primary"></i> Modalidade Curricular:
          </label>
          <div class="d-flex gap-4 p-2 bg-light rounded border">
            <div class="form-check">
              <input class="form-check-input" type="radio" name="loteRegime" id="loteRegimeClasse" value="CLASSE" checked onchange="window.alternarRegimeLote(this.value)">
              <label class="form-check-label fw-semibold" for="loteRegimeClasse">
                <i class="bi bi-mortarboard me-1 text-primary"></i> Classe (1ª à 12ª Classe)
              </label>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="radio" name="loteRegime" id="loteRegimeNivel" value="NIVEL" onchange="window.alternarRegimeLote(this.value)">
              <label class="form-check-label fw-semibold" for="loteRegimeNivel">
                <i class="bi bi-layers me-1 text-success"></i> Nível (Nível 1, Nível 2...)
              </label>
            </div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <label class="form-label small fw-semibold mb-0" id="labelMlGrau">Classe / Grau</label>
            <button type="button" id="btnAdicionarNivelLote" class="btn btn-link btn-sm p-0 text-success fw-semibold small text-decoration-none" style="display: none;" onclick="window.promptAdicionarNivelModal('mlGrau')">
              <i class="bi bi-plus-circle me-1"></i>+ Adicionar Nível
            </button>
          </div>
          <select id="mlGrau" class="form-select" required onchange="if(this.value==='__NOVO_NIVEL__'){ window.promptAdicionarNivelModal('mlGrau'); } else { document.getElementById('mlArea').innerHTML = window.obterTodasAreasOficiais(this.value).map(a => '<option value=\\'' + a + '\\'>' + a + '</option>').join(''); }">
            ${optGraus}
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Secção / Área de Estudo</label>
          <select id="mlArea" class="form-select">
            ${optAreasLote}
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Quantidade de Turmas a Criar</label>
          <input type="number" id="mlQtd" class="form-control" value="3" min="1" max="20" required>
          <small class="text-muted">Ex: 3 cria Turma 1, Turma 2 e Turma 3</small>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Identificação da Turma</label>
          <select id="mlSufixo" class="form-select">
            <option value="NUMERO">Numérica (Turma 1, Turma 2, Turma 3...)</option>
            <option value="LETRA">Alfabética (Turma A, Turma B, Turma C...)</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Turno Predeterminado</label>
          <select id="mlTurno" class="form-select">
            <option value="MANHA">Manhã</option>
            <option value="TARDE">Tarde</option>
            <option value="NOITE">Noite</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Número Máximo de Alunos (Capacidade)</label>
          <input type="number" id="mlCapacidade" class="form-control" value="50" min="5" max="150" required>
        </div>
        <div class="col-12 mt-2">
          <div class="card p-3 bg-light border">
            <div class="form-check form-switch mb-2">
              <input class="form-check-input" type="checkbox" id="mlDistribuirAuto" checked onchange="document.getElementById('mlCriterioBox').style.display = this.checked ? 'block' : 'none'">
              <label class="form-check-label fw-bold text-success" for="mlDistribuirAuto">
                <i class="bi bi-magic me-1"></i> Distribuir automaticamente alunos pendentes desta classe após gerar as turmas
              </label>
            </div>
            <div id="mlCriterioBox">
              <label class="form-label small fw-semibold">Critério de Distribuição dos Alunos</label>
              <select id="mlCriterio" class="form-select form-select-sm">
                <option value="EQUILIBRIO_IDADE_GENERO" selected>⚖️ Equilíbrio Misto: Idade + Género (50% F / 50% M)</option>
                <option value="IDADE_ASC">🎂 Idade: Mais jovens primeiro (Homogéneo por Idade)</option>
                <option value="IDADE_DESC">🎂 Idade: Mais velhos primeiro</option>
                <option value="GENERO_EQUILIBRADO">⚖️ Equilíbrio de Género (50% F / 50% M)</option>
                <option value="ALFABETICO">🔤 Ordem Alfabética (Nomes de A a Z)</option>
                <option value="ALEATORIO">🎲 Distribuição Aleatória / Equitativa</option>
              </select>
              <small class="text-muted" style="font-size: 0.72rem;">Os alunos matriculados nesta classe e área que ainda não têm turma serão imediatamente alocados.</small>
            </div>
          </div>
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4"><i class="bi bi-plus-circle me-1"></i> Gerar Turmas da Classe</button>
    </form>
  `);

  window.alternarRegimeLote = function(regime) {
    const sel = document.getElementById('mlGrau');
    const lbl = document.getElementById('labelMlGrau');
    const btnAdd = document.getElementById('btnAdicionarNivelLote');
    if (!sel) return;
    if (regime === 'NIVEL') {
      if (lbl) lbl.textContent = 'Nível Curricular *';
      if (btnAdd) btnAdd.style.display = 'inline-block';
      const niveis = typeof window.obterNiveisInstituicao === 'function' ? window.obterNiveisInstituicao() : [];
      sel.innerHTML = typeof window.renderizarOpcoesNiveisSelect === 'function'
        ? window.renderizarOpcoesNiveisSelect(niveis)
        : (niveis.length ? niveis.map(n => `<option value="${n}">${n}</option>`).join('') + '<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>' : '<option value="">-- Nenhum nível cadastrado (+ Adicionar) --</option><option value="__NOVO_NIVEL__">➕ + Adicionar Nível...</option>');
      if (niveis.length === 0) {
        setTimeout(() => { if (typeof window.promptAdicionarNivelModal === 'function') window.promptAdicionarNivelModal('mlGrau'); }, 150);
      }
    } else {
      if (lbl) lbl.textContent = 'Classe / Grau *';
      if (btnAdd) btnAdd.style.display = 'none';
      const classes = [
        '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
        '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
      ];
      sel.innerHTML = classes.map(c => `<option value="${c}">${c}</option>`).join('');
    }
    document.getElementById('mlArea').innerHTML = window.obterTodasAreasOficiais(sel.value).map(a => '<option value="' + a + '">' + a + '</option>').join('');
  };

  document.getElementById('formModalTurmasLote').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const grau_ano = document.getElementById('mlGrau').value;
      const area = document.getElementById('mlArea').value || 'Geral';
      const quantidade = parseInt(document.getElementById('mlQtd').value) || 1;
      const tipo_sufixo = document.getElementById('mlSufixo').value;
      const turno = document.getElementById('mlTurno').value;
      const capacidade_maxima = parseInt(document.getElementById('mlCapacidade').value) || 50;
      const distribuir_automaticamente = document.getElementById('mlDistribuirAuto').checked;
      const criterio = document.getElementById('mlCriterio').value;

      const res = await apiFetch('/api/v1/escola-admin/turmas/criar-lote', {
        method: 'POST',
        body: JSON.stringify({ grau_ano, area, quantidade, tipo_sufixo, turno, capacidade_maxima, distribuir_automaticamente, criterio })
      });

      if (res.success) {
        alert(res.message || 'Turmas geradas com sucesso!');
        fecharModal();
        await carregarEscolaETurmas();
        if (typeof carregarAlunos === 'function') await carregarAlunos();
      } else {
        alert(res.message || 'Erro ao gerar turmas');
      }
    } catch (err) {
      alert(err.message || 'Erro de comunicação');
    }
  });
}

async function corrigirNumeracaoTurmas() {
  const anoAtivo = state.filtroAlunoAno || state.tenant?.ano_letivo_ativo || '2026';
  if (!confirm(`Isto irá renumerar todas as turmas do ano ${anoAtivo} de forma contínua (Turma 1, Turma 2, Turma 3...) por classe, eliminando sobreposições e nomes como "Turma 1 (1)".\n\nContinuar?`)) return;
  try {
    const res = await apiFetch('/api/v1/escola-admin/turmas/renumerar-turmas', {
      method: 'POST',
      body: JSON.stringify({ ano_letivo: anoAtivo })
    });
    if (res.success) {
      alert(res.message || 'Numeração corrigida com sucesso!');
      await carregarEscolaETurmas();
      if (typeof carregarAlunos === 'function') await carregarAlunos();
    } else {
      alert(res.message || 'Erro ao corrigir numeração');
    }
  } catch (err) {
    alert(err.message || 'Erro de comunicação');
  }
}

window.modalFormacaoAutomaticaTurmas = async function(classeFiltro = 'TODAS', areaFiltro = 'TODAS') {
  const anoAtivo = state.filtroAlunoAno || state.tenant?.ano_letivo_ativo || '2026';
  abrirModal('Formação Automática de Turmas & Enturmação', `
    <div class="text-center py-4 text-muted">
      <div class="spinner-border text-primary mb-2" role="status"></div>
      <div>A analisar alunos matriculados, idades, géneros e secções...</div>
    </div>
  `);

  try {
    const resPrevia = await apiFetch(`/api/v1/escola-admin/turmas/previa-formacao-automatica?ano_letivo=${anoAtivo}&grau_ano=${classeFiltro}&area=${areaFiltro}`);
    const grupos = resPrevia.grupos || [];
    const totalPendentes = resPrevia.total_alunos_pendentes || 0;

    let tabelaPreviaHtml = '';
    if (grupos.length === 0) {
      tabelaPreviaHtml = `
        <div class="alert alert-success py-3 text-center mb-0">
          <i class="bi bi-check-circle-fill text-success fs-3 d-block mb-1"></i>
          <strong>Excelente! Todos os alunos matriculados já possuem turma.</strong>
          <p class="small text-muted mb-0 mt-1">Ao matricular novos alunos ou no início do ano lectivo, utilize esta ferramenta para criar as turmas (1, 2, 3...) e enturmar automaticamente.</p>
        </div>
      `;
    } else {
      tabelaPreviaHtml = `
        <div class="table-responsive border rounded mb-3">
          <table class="table table-sm table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Classe / Grau</th>
                <th>Secção / Área</th>
                <th class="text-center">Alunos Elegíveis</th>
                <th class="text-center">Idades (Faixa)</th>
                <th class="text-center">Género (M/F)</th>
                <th>Turmas a Gerar Automaticamente</th>
              </tr>
            </thead>
            <tbody>
              ${grupos.map(g => {
                const badgesTurmas = (g.propostas || []).map(p => 
                  `<span class="badge ${p.turno === 'MANHA' ? 'bg-primary' : 'bg-info text-dark'} me-1 mb-1" title="Capacidade: ${p.capacidade} alunos | Turno: ${p.turno}">
                    <i class="bi bi-door-closed me-1"></i>${p.nome} (${p.turno})
                  </span>`
                ).join('');
                return `
                  <tr>
                    <td><strong>${g.grau_ano}</strong></td>
                    <td><span class="badge bg-light text-dark border">${g.area}</span></td>
                    <td class="text-center"><span class="badge bg-secondary">${g.total_alunos} alunos</span></td>
                    <td class="text-center small text-muted">${g.idade_minima} a ${g.idade_maxima} anos <br><span style="font-size: 0.7rem;">(Média: ${g.idade_media})</span></td>
                    <td class="text-center small"><span class="text-primary fw-bold">${g.total_masculino} M</span> / <span class="text-danger fw-bold">${g.total_feminino} F</span></td>
                    <td>${badgesTurmas || '<span class="text-muted small">Turmas existentes suficientes</span>'}</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    const classesSet = new Set();
    (state.todosAlunos || []).forEach(a => { if (a.classe) classesSet.add(a.classe.trim()); });
    (state.todasTurmas || []).forEach(t => { if (t.grau_ano) classesSet.add(t.grau_ano.trim()); });
    (state.todasDisciplinas || []).forEach(d => { if (d.classe) classesSet.add(d.classe.trim()); });
    const classesList = Array.from(classesSet).sort((a, b) => (parseInt(a.replace(/\D/g, '')) || 0) - (parseInt(b.replace(/\D/g, '')) || 0));

    const optClasses = classesList.length > 0
      ? ['<option value="TODAS">Todas as Classes / Níveis da Escola</option>']
          .concat(classesList.map(c => `<option value="${c}" ${c === classeFiltro ? 'selected' : ''}>${c}</option>`))
          .join('')
      : '<option value="" disabled>-- Nenhuma classe/nível cadastrado nesta instituição --</option>';

    abrirModal('Formação Automática de Turmas & Enturmação (1, 2, 3...)', `
      <form id="formModalFormacaoAuto">
        <div class="alert alert-primary py-2 small mb-3">
          <div class="d-flex align-items-center gap-2">
            <i class="bi bi-magic fs-4 text-primary"></i>
            <div>
              <strong>Criação e Enturmação Totalmente Automáticas:</strong>
              <div>O sistema calcula a quantidade de turmas necessárias (Turma 1, Turma 2, Turma 3...) com base nos alunos matriculados, distribuindo-os automaticamente por <strong>idade, secção de estudo, género (paridade 50/50)</strong> e <strong>capacidade da sala</strong>.</div>
            </div>
          </div>
        </div>

        ${tabelaPreviaHtml}

        <div class="row g-3">
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Classe / Grau Alvo</label>
            <select id="mfaClasse" class="form-select" onchange="modalFormacaoAutomaticaTurmas(this.value, document.getElementById('mfaArea').value)">
              ${optClasses}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Secção / Área de Estudo</label>
            <select id="mfaArea" class="form-select" onchange="modalFormacaoAutomaticaTurmas(document.getElementById('mfaClasse').value, this.value)">
              <option value="TODAS" ${areaFiltro === 'TODAS' ? 'selected' : ''}>Todas as Áreas / Geral</option>
              <option value="Ensino Geral" ${areaFiltro === 'Ensino Geral' || areaFiltro === 'Geral' ? 'selected' : ''}>Ensino Geral / Tronco Comum</option>
              <option value="Ciências com Biologia" ${areaFiltro === 'Ciências com Biologia' ? 'selected' : ''}>Ciências com Biologia</option>
              <option value="Ciências com Desenho" ${areaFiltro === 'Ciências com Desenho' ? 'selected' : ''}>Ciências com Desenho</option>
              <option value="Letras com Geografia" ${areaFiltro === 'Letras com Geografia' ? 'selected' : ''}>Letras com Geografia</option>
              <option value="Letras com História" ${areaFiltro === 'Letras com História' ? 'selected' : ''}>Letras com História</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Critério Pedagógico & Paridade</label>
            <select id="mfaCriterio" class="form-select">
              <option value="EQUILIBRIO_IDADE_GENERO" selected>⚖️ Equilíbrio Misto: Idade + Género (50% F / 50% M)</option>
              <option value="IDADE_ASC">🎂 Idade: Mais jovens primeiro (Manhã) & Tarde</option>
              <option value="IDADE_DESC">🎂 Idade: Mais velhos primeiro</option>
              <option value="GENERO_EQUILIBRADO">⚖️ Equilíbrio de Género Rigoroso (50% F / 50% M)</option>
              <option value="ALFABETICO">🔤 Ordem Alfabética (Nomes de A a Z)</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Distribuição de Turnos</label>
            <select id="mfaTurno" class="form-select">
              <option value="AUTO_IDADE" selected>🌞 Inteligente por Idade (Jovens de Manhã, Tarde)</option>
              <option value="MANHA">Todas de Manhã</option>
              <option value="TARDE">Todas de Tarde</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Capacidade Máxima por Turma</label>
            <input type="number" id="mfaCapacidade" class="form-control" value="50" min="10" max="150" required>
            <small class="text-muted" style="font-size: 0.72rem;">Padrão MEC: 50 alunos por sala.</small>
          </div>
        </div>

        <div class="d-flex gap-2 justify-content-end mt-4">
          <button type="button" class="btn btn-light" onclick="fecharModal()">Cancelar</button>
          <button type="submit" class="btn btn-primary px-4 fw-bold shadow-sm" ${totalPendentes === 0 ? 'disabled' : ''}>
            <i class="bi bi-lightning-charge-fill me-1"></i> Gerar Turmas 1, 2, 3... e Enturmar Automaticamente
          </button>
        </div>
      </form>
    `);

    document.getElementById('formModalFormacaoAuto').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const grau_ano = document.getElementById('mfaClasse').value;
        const area = document.getElementById('mfaArea').value;
        const criterio = document.getElementById('mfaCriterio').value;
        const turno = document.getElementById('mfaTurno').value;
        const capacidade_maxima = parseInt(document.getElementById('mfaCapacidade').value) || 50;

        const res = await apiFetch('/api/v1/escola-admin/turmas/gerar-e-enturmar-automatico', {
          method: 'POST',
          body: JSON.stringify({
            grau_ano,
            area,
            criterio,
            turno,
            capacidade_maxima,
            ano_letivo: anoAtivo,
            apenas_sem_turma: true
          })
        });

        if (res.success) {
          alert(res.message || 'Turmas geradas e alunos enturmados com sucesso!');
          fecharModal();
          await carregarEscolaETurmas();
          if (typeof carregarAlunos === 'function') await carregarAlunos();
        } else {
          alert(res.message || 'Erro ao gerar turmas automaticamente');
        }
      } catch (err) {
        alert(err.message || 'Erro de comunicação');
      }
    });
  } catch (err) {
    alert('Erro ao carregar prévia de formação de turmas: ' + err.message);
  }
};

window.modalDistribuirAlunosAutomatico = window.modalFormacaoAutomaticaTurmas;

async function modalEditarTurma(turmaId) {
  try {
    const [turmasRes, profsRes] = await Promise.all([
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/professores')
    ]);

    if (!turmasRes.success) return alert('Falha ao obter dados da turma');
    const turma = (turmasRes.data || []).find(t => t.id === turmaId);
    if (!turma) return alert('Turma não encontrada');

    const professores = profsRes.data || [];
    const optDirTurma = '<option value="">(Nenhum seleccionado)</option>' +
      professores.map(p => `<option value="${p.id}" ${p.id === turma.director_turma_id ? 'selected' : ''}>${p.nome} ${p.apelido || ''} [${p.codigo || 'Docente'}]</option>`).join('');

    const optDirClasse = '<option value="">(Nenhum seleccionado)</option>' +
      professores.map(p => `<option value="${p.id}" ${p.id === turma.director_classe_id ? 'selected' : ''}>${p.nome} ${p.apelido || ''} [${p.codigo || 'Docente'}]</option>`).join('');

    const classesOficiais = [
      '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
      '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
    ];
    const niveisOficiais = typeof window.obterNiveisInstituicao === 'function' ? window.obterNiveisInstituicao() : [];

    const grauAtual = (turma.grau_ano || '').trim();
    const isNivel = grauAtual.toLowerCase().includes('nível') || grauAtual.toLowerCase().includes('nivel');
    const regime = isNivel ? 'NIVEL' : 'CLASSE';
    const listaGraus = isNivel ? [...niveisOficiais] : [...classesOficiais];
    if (!listaGraus.includes(grauAtual) && grauAtual) {
      listaGraus.push(grauAtual);
    }
    const optGraus = isNivel
      ? (typeof window.renderizarOpcoesNiveisSelect === 'function' ? window.renderizarOpcoesNiveisSelect(listaGraus, grauAtual) : listaGraus.map(g => `<option value="${g}" ${g === grauAtual ? 'selected' : ''}>${g}</option>`).join('') + '<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>')
      : classesOficiais.map(g => `<option value="${g}" ${g === grauAtual ? 'selected' : ''}>${g}</option>`).join('');

    const podeHomologar = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'].includes(state.user?.role);
    const dtBadgeStatus = turma.dt_status_homologacao === 'HOMOLOGADO' && turma.codigo_director_turma
      ? `<span class="badge bg-success font-monospace"><i class="bi bi-patch-check-fill me-1"></i>Homologado: ${turma.codigo_director_turma}</span>`
      : (turma.director_turma_id ? `<span class="badge bg-warning text-dark"><i class="bi bi-hourglass-split me-1"></i>Pendente de Homologação (Nomeado pelo DP)</span>` : `<span class="badge bg-secondary">Sem Nomeação</span>`);

    const dcBadgeStatus = turma.dc_status_homologacao === 'HOMOLOGADO' && turma.codigo_director_classe
      ? `<span class="badge bg-success font-monospace"><i class="bi bi-patch-check-fill me-1"></i>Homologado: ${turma.codigo_director_classe}</span>`
      : (turma.director_classe_id ? `<span class="badge bg-warning text-dark"><i class="bi bi-hourglass-split me-1"></i>Pendente de Homologação (Nomeado pelo DP)</span>` : `<span class="badge bg-secondary">Sem Nomeação</span>`);

    abrirModal(`Editar Turma: ${turma.nome}`, `
      <form id="formModalEditarTurma">
        <div class="row g-3">
          <div class="col-12">
            <div class="d-flex gap-4 p-2 bg-light rounded border align-items-center">
              <span class="small fw-bold text-uppercase text-secondary"><i class="bi bi-sliders me-1 text-primary"></i> Modalidade:</span>
              <div class="form-check mb-0">
                <input class="form-check-input" type="radio" name="editRegimeTurma" id="editRegimeClasse" value="CLASSE" ${!isNivel ? 'checked' : ''} onchange="window.alternarRegimeEditTurma(this.value)">
                <label class="form-check-label fw-semibold small" for="editRegimeClasse">
                  <i class="bi bi-mortarboard me-1 text-primary"></i> Classe (1ª à 12ª)
                </label>
              </div>
              <div class="form-check mb-0">
                <input class="form-check-input" type="radio" name="editRegimeTurma" id="editRegimeNivel" value="NIVEL" ${isNivel ? 'checked' : ''} onchange="window.alternarRegimeEditTurma(this.value)">
                <label class="form-check-label fw-semibold small" for="editRegimeNivel">
                  <i class="bi bi-layers-fill me-1 text-success"></i> Nível (Nível 1, 2, ...)
                </label>
              </div>
            </div>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Nome da Turma</label>
            <input type="text" id="mtEditNome" class="form-control" required value="${turma.nome || ''}">
          </div>
          <div class="col-md-3">
            <div class="d-flex justify-content-between align-items-center mb-1">
              <label class="form-label small fw-semibold mb-0" id="labelMtEditGrau">${isNivel ? 'Nível Curricular *' : 'Classe / Grau *'}</label>
              <button type="button" id="btnAdicionarNivelEditTurma" class="btn btn-link btn-sm p-0 text-success fw-semibold small text-decoration-none" style="${isNivel ? '' : 'display: none;'}" onclick="window.promptAdicionarNivelModal('mtEditGrau')">
                <i class="bi bi-plus-circle me-1"></i>+ Adicionar Nível
              </button>
            </div>
            <select id="mtEditGrau" class="form-select" required onchange="if(this.value==='__NOVO_NIVEL__') window.promptAdicionarNivelModal('mtEditGrau')">
              ${optGraus}
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Secção / Área de Estudo</label>
            <input type="text" list="listaAreasEstudoTurmaEdit" id="mtEditArea" class="form-control" value="${turma.area || 'Geral'}" placeholder="Geral / Ciências...">
            <datalist id="listaAreasEstudoTurmaEdit">
              <option value="Geral">Tronco Comum / Geral</option>
              <option value="Ciências com Geografia">Ciências com Geografia (cg)</option>
              <option value="Ciências com Biologia">Ciências com Biologia (cb)</option>
              <option value="Ciências com Desenho">Ciências com Desenho (cd)</option>
              <option value="Letras com Geografia">Letras com Geografia (lg)</option>
              <option value="Letras com História">Letras com História (lh)</option>
            </datalist>
            <small class="text-muted" style="font-size: 0.72rem;">Secção vinculada à turma.</small>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Turno</label>
            <select id="mtEditTurno" class="form-select">
              <option value="MANHA" ${turma.turno === 'MANHA' ? 'selected' : ''}>Manhã</option>
              <option value="TARDE" ${turma.turno === 'TARDE' ? 'selected' : ''}>Tarde</option>
              <option value="NOITE" ${turma.turno === 'NOITE' ? 'selected' : ''}>Noite</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Capacidade Máxima (Alunos)</label>
            <input type="number" id="mtEditCapacidade" class="form-control" value="${turma.capacidade_maxima || 50}" min="1" max="150" required>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Sala de Aula</label>
            <input type="text" id="mtEditSala" class="form-control" value="${turma.sala || ''}" placeholder="Ex: Sala 04">
          </div>

          <!-- Fluxo Institucional: Nomeação pelo Director Pedagógico (DP) & Homologação pelo Director da Escola (GD) -->
          <div class="col-12">
            <div class="p-3 rounded border border-primary border-opacity-25 bg-light">
              <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
                <h6 class="fw-bold text-primary mb-0">
                  <i class="bi bi-award-fill me-1"></i> Nomeação (Direcção Pedagógica - DP) & Homologação (Director da Escola - GD)
                </h6>
                <small class="text-muted" style="font-size: 0.72rem;">O código de DT e DC é gerado após homologação pelo Director da Escola</small>
              </div>
              <div class="row g-3">
                <div class="col-md-6">
                  <div class="d-flex justify-content-between align-items-center mb-1">
                    <label class="form-label small fw-bold text-dark mb-0">Director de Turma (DT)</label>
                    ${dtBadgeStatus}
                  </div>
                  <select id="mtEditDirTurma" class="form-select">${optDirTurma}</select>
                  <small class="text-muted" style="font-size: 0.71rem;">
                    ${turma.dt_nomeado_por_nome ? `Nomeado por: <strong>${turma.dt_nomeado_por_nome}</strong>` : 'Seleccione o docente para nomear como Director de Turma.'}
                    ${turma.dt_homologado_por_nome ? ` | Homologado por: <strong>${turma.dt_homologado_por_nome}</strong>` : ''}
                  </small>
                </div>
                <div class="col-md-6">
                  <div class="d-flex justify-content-between align-items-center mb-1">
                    <label class="form-label small fw-bold text-dark mb-0">Director de Classe (DC)</label>
                    ${dcBadgeStatus}
                  </div>
                  <select id="mtEditDirClasse" class="form-select">${optDirClasse}</select>
                  <small class="text-muted" style="font-size: 0.71rem;">
                    ${turma.dc_nomeado_por_nome ? `Nomeado por: <strong>${turma.dc_nomeado_por_nome}</strong>` : 'Seleccione o docente para nomear como Director de Classe.'}
                    ${turma.dc_homologado_por_nome ? ` | Homologado por: <strong>${turma.dc_homologado_por_nome}</strong>` : ''}
                  </small>
                </div>
              </div>
              <div class="d-flex flex-wrap gap-2 mt-3 pt-2 border-top">
                <button type="button" class="btn btn-outline-info btn-sm fw-semibold" onclick="nomearDirectoresNoModal('${turma.id}')">
                  <i class="bi bi-person-plus-fill me-1"></i> 1. Nomear Directores (Direcção Pedagógica - DP)
                </button>
                ${podeHomologar ? `
                  <button type="button" class="btn btn-success btn-sm fw-semibold" onclick="homologarDirectoresNoModal('${turma.id}')">
                    <i class="bi bi-patch-check-fill me-1"></i> 2. Homologar Nomeação & Gerar Códigos DT/DC (Director da Escola)
                  </button>
                ` : ''}
              </div>
            </div>
          </div>
        </div>
        <div class="d-flex gap-2 justify-content-end mt-4">
          <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
          <button type="submit" class="btn btn-primary btn-sm px-4">Salvar Alterações</button>
        </div>
      </form>
    `);

    window.alternarRegimeEditTurma = function(regimeSel) {
      const sel = document.getElementById('mtEditGrau');
      const lbl = document.getElementById('labelMtEditGrau');
      const btnAdd = document.getElementById('btnAdicionarNivelEditTurma');
      if (!sel) return;
      if (regimeSel === 'NIVEL') {
        if (lbl) lbl.textContent = 'Nível Curricular *';
        if (btnAdd) btnAdd.style.display = 'inline-block';
        const niveis = typeof window.obterNiveisInstituicao === 'function' ? window.obterNiveisInstituicao() : [];
        sel.innerHTML = typeof window.renderizarOpcoesNiveisSelect === 'function'
          ? window.renderizarOpcoesNiveisSelect(niveis, grauAtual)
          : (niveis.length ? niveis.map(n => `<option value="${n}">${n}</option>`).join('') + '<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>' : '<option value="">-- Nenhum nível cadastrado (+ Adicionar) --</option><option value="__NOVO_NIVEL__">➕ + Adicionar Nível...</option>');
        if (niveis.length === 0) {
          setTimeout(() => { if (typeof window.promptAdicionarNivelModal === 'function') window.promptAdicionarNivelModal('mtEditGrau'); }, 150);
        }
      } else {
        if (lbl) lbl.textContent = 'Classe / Grau *';
        if (btnAdd) btnAdd.style.display = 'none';
        const classes = [
          '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
          '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
        ];
        sel.innerHTML = classes.map(c => `<option value="${c}">${c}</option>`).join('');
      }
    };

    window.nomearDirectoresNoModal = async function(tId) {
      try {
        const dtId = document.getElementById('mtEditDirTurma')?.value || null;
        const dcId = document.getElementById('mtEditDirClasse')?.value || null;
        const res = await apiFetch(`/api/v1/escola-admin/turmas/${tId}/nomear-directores`, {
          method: 'POST',
          body: JSON.stringify({ director_turma_id: dtId, director_classe_id: dcId })
        });
        if (res.success) {
          alert(res.message || 'Nomeação registada pelo Director Pedagógico! Aguarda homologação do Director da Escola.');
          fecharModal();
          await carregarEscolaETurmas();
        } else {
          alert(res.message || 'Erro ao registar nomeação');
        }
      } catch (err) {
        alert(err.message || 'Erro ao registar nomeação');
      }
    };

    window.homologarDirectoresNoModal = async function(tId) {
      try {
        // Primeiro garantir que os directores seleccionados estão salvos se foram alterados
        const dtId = document.getElementById('mtEditDirTurma')?.value || null;
        const dcId = document.getElementById('mtEditDirClasse')?.value || null;
        if (dtId !== turma.director_turma_id || dcId !== turma.director_classe_id) {
          await apiFetch(`/api/v1/escola-admin/turmas/${tId}/nomear-directores`, {
            method: 'POST',
            body: JSON.stringify({ director_turma_id: dtId, director_classe_id: dcId })
          });
        }
        const res = await apiFetch(`/api/v1/escola-admin/turmas/${tId}/homologar-directores`, {
          method: 'POST',
          body: JSON.stringify({ acao: 'HOMOLOGAR', alvo: 'AMBOS' })
        });
        if (res.success) {
          const t = res.data || {};
          let msg = `${res.message || 'Homologação concluída com sucesso pelo Director da Escola!'}\n`;
          if (t.codigo_director_turma) msg += `\n• Código Oficial do Director de Turma: ${t.codigo_director_turma}`;
          if (t.codigo_director_classe) msg += `\n• Código Oficial do Director de Classe: ${t.codigo_director_classe}`;
          alert(msg);
          fecharModal();
          await carregarEscolaETurmas();
          if (typeof carregarProfessores === 'function') await carregarProfessores();
        } else {
          alert(res.message || 'Erro ao homologar directores');
        }
      } catch (err) {
        alert(err.message || 'Erro ao homologar directores');
      }
    };

    document.getElementById('formModalEditarTurma').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const novoNome = document.getElementById('mtEditNome').value.trim();
        const novoGrau = document.getElementById('mtEditGrau').value;
        const idInfo = window.extrairIdentificadorTurma(novoNome, novoGrau);
        if (idInfo.tipo === 'NUMERO' || idInfo.tipo === 'LETRA') {
          const duplicada = (state.todasTurmas || []).find(t => {
            if (t.id === turmaId) return false;
            if (normalizarClasse(t.grau_ano) !== normalizarClasse(novoGrau)) return false;
            const tId = window.extrairIdentificadorTurma(t.nome, t.grau_ano);
            return tId.tipo === idInfo.tipo && tId.val === idInfo.val;
          });
          if (duplicada) {
            alert(`Atenção: Já existe a ${idInfo.rotulo} cadastrada na ${novoGrau} (Secção/Área: "${duplicada.area || 'Geral'}", Turno: ${duplicada.turno || 'Diurno'}).\n\nNa mesma classe não pode haver turmas com a mesma numeração, independentemente da secção ou área.`);
            return;
          }
        }

        const body = {
          nome: novoNome,
          grau_ano: novoGrau,
          area: (document.getElementById('mtEditArea')?.value || 'Geral').trim(),
          turno: document.getElementById('mtEditTurno').value,
          capacidade_maxima: parseInt(document.getElementById('mtEditCapacidade').value) || 50,
          sala: document.getElementById('mtEditSala').value || null,
          director_turma_id: document.getElementById('mtEditDirTurma').value || null,
          director_classe_id: document.getElementById('mtEditDirClasse').value || null
        };
        const res = await apiFetch(`/api/v1/escola-admin/turmas/${turmaId}`, {
          method: 'PUT',
          body: JSON.stringify(body)
        });
        if (res.success) {
          alert('Turma e Direcção actualizadas com sucesso!');
          fecharModal();
          await carregarEscolaETurmas();
          if (typeof carregarAlunos === 'function') await carregarAlunos();
        } else {
          alert(res.message || 'Erro ao actualizar turma');
        }
      } catch (err) {
        alert('Erro ao actualizar turma: ' + (err.message || 'Servidor indisponível'));
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados da turma');
  }
}

async function eliminarTurma(turmaId, nome) {
  if (!confirm(`Tem certeza que deseja eliminar a turma "${nome}"?\n\nEsta operação desassociará os alunos e removerá as alocações da turma.`)) return;
  try {
    const res = await apiFetch(`/api/v1/escola-admin/turmas/${turmaId}`, {
      method: 'DELETE'
    });
    if (res.success) {
      mostrarNotificacao('Turma eliminada com sucesso!', 'success');
      await carregarEscolaETurmas();
    } else {
      alert(res.message || 'Erro ao eliminar turma');
    }
  } catch (err) {
    alert(err.message || 'Erro ao comunicar com o servidor');
  }
}

