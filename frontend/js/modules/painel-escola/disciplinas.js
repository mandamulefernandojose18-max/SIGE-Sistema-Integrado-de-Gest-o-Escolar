/**
 * SIGE - PAINEL-ESCOLA | Disciplinas & Currículo
 * Ficheiro de código independente do menu: disciplinas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 6. DISCIPLINAS ====================
function filtrarDisciplinasClasse(classe) {
  state.filtroDisciplinaClasse = classe || '';
  const selClasse = document.getElementById('filtroDisciplinasClasseSelect');
  if (selClasse && selClasse.value !== (classe || '')) {
    selClasse.value = classe || '';
  }
  atualizarSelectAreasDisciplinas(classe);
  carregarDisciplinas();
}

function filtrarDisciplinasArea(area) {
  state.filtroDisciplinaArea = area || '';
  const selArea = document.getElementById('filtroDisciplinasAreaSelect');
  if (selArea && selArea.value !== (area || '')) {
    selArea.value = area || '';
  }
  carregarDisciplinas();
}

function atualizarSelectAreasDisciplinas(classe = null) {
  const selectArea = document.getElementById('filtroDisciplinasAreaSelect');
  if (!selectArea) return;

  const todasAreas = typeof window.obterTodasAreasOficiais === 'function'
    ? window.obterTodasAreasOficiais(classe || state.filtroDisciplinaClasse)
    : [
        'Ensino Geral',
        'Ciências com Biologia',
        'Ciências com Desenho',
        'Ciências com Geografia',
        'Letras com Geografia',
        'Letras com História'
      ];

  const activeArea = state.filtroDisciplinaArea || '';

  let htmlOptions = `<option value="">Todas as Áreas / Secções (${todasAreas.length})</option>`;
  todasAreas.forEach(a => {
    const isAct = (activeArea && activeArea.toLowerCase() === a.toLowerCase()) ? 'selected' : '';
    htmlOptions += `<option value="${a}" ${isAct}>${a}</option>`;
  });

  selectArea.innerHTML = htmlOptions;

  if (activeArea && !todasAreas.some(x => x.toLowerCase() === activeArea.toLowerCase())) {
    state.filtroDisciplinaArea = '';
    selectArea.value = '';
  } else if (activeArea) {
    selectArea.value = activeArea;
  }
}

function filtrarDisciplinasTabelaTexto() {
  const busca = (document.getElementById('filtroDisciplinasBusca')?.value || '').toLowerCase().trim();
  const rows = document.querySelectorAll('#tabelaDisciplinas tr');
  let visiveis = 0;
  let linhaVazia = document.getElementById('linhaNenhumaDisciplinaBusca');

  rows.forEach(r => {
    if (r.id === 'linhaNenhumaDisciplinaBusca') return;
    if (r.cells.length < 4) return;
    const txt = r.textContent.toLowerCase();
    const show = (!busca || txt.includes(busca));
    r.style.display = show ? '' : 'none';
    if (show) visiveis++;
  });

  const tbody = document.getElementById('tabelaDisciplinas');
  if (tbody && rows.length > 0 && visiveis === 0 && busca) {
    if (!linhaVazia) {
      linhaVazia = document.createElement('tr');
      linhaVazia.id = 'linhaNenhumaDisciplinaBusca';
      linhaVazia.innerHTML = `<td colspan="7" class="text-center py-4 text-muted"><i class="bi bi-search me-1 text-primary"></i> Nenhuma disciplina encontrada com o termo "<strong>${busca}</strong>".</td>`;
      tbody.appendChild(linhaVazia);
    } else {
      linhaVazia.style.display = '';
      linhaVazia.innerHTML = `<td colspan="7" class="text-center py-4 text-muted"><i class="bi bi-search me-1 text-primary"></i> Nenhuma disciplina encontrada com o termo "<strong>${busca}</strong>".</td>`;
    }
  } else if (linhaVazia) {
    linhaVazia.style.display = 'none';
  }
}

function modalNovaSeccaoArea() {
  const classeAtiva = state.filtroDisciplinaClasse || '10ª Classe';
  const classesList = ['7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'];
  const optClasses = classesList.map(c => `<option value="${c}" ${c === classeAtiva ? 'selected' : ''}>${c}</option>`).join('');

  abrirModal('Cadastrar Secção / Área de Estudo', `
    <form id="formModalSeccaoArea">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Classe Correspondente *</label>
        <select id="msaClasse" class="form-select" required>
          ${optClasses}
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nome da Secção ou Área de Estudo *</label>
        <input type="text" id="msaNome" class="form-control" placeholder="Ex: Ciências com Geografia, Ciências com Biologia..." required>
        <small class="text-muted">A nova secção/área aparecerá automaticamente em todas as listas de filtros, turmas e disciplinas.</small>
      </div>
      <button type="submit" class="btn btn-primary w-100 fw-semibold">
        <i class="bi bi-plus-circle me-1"></i> Criar Secção / Área
      </button>
    </form>
  `);

  document.getElementById('formModalSeccaoArea').addEventListener('submit', (e) => {
    e.preventDefault();
    const classeAlvo = document.getElementById('msaClasse').value || classeAtiva;
    const nomeArea = document.getElementById('msaNome').value.trim();
    if (!nomeArea) return;

    const chave = 'sige_custom_areas_' + (classeAlvo || 'geral');
    const existingRaw = localStorage.getItem(chave);
    const existing = existingRaw ? JSON.parse(existingRaw) : [];
    if (!existing.includes(nomeArea)) existing.push(nomeArea);
    localStorage.setItem(chave, JSON.stringify(existing));

    const chaveAll = 'sige_custom_areas_all';
    const allRaw = localStorage.getItem(chaveAll);
    const allExisting = allRaw ? JSON.parse(allRaw) : [];
    if (!allExisting.includes(nomeArea)) allExisting.push(nomeArea);
    localStorage.setItem(chaveAll, JSON.stringify(allExisting));

    fecharModal();

    // Atualiza imediatamente a lista de filtros e seleciona a nova área
    state.filtroDisciplinaClasse = classeAlvo;
    state.filtroDisciplinaArea = nomeArea;

    const selClasse = document.getElementById('filtroDisciplinasClasseSelect');
    if (selClasse) selClasse.value = classeAlvo;

    atualizarSelectAreasDisciplinas(classeAlvo);

    const selArea = document.getElementById('filtroDisciplinasAreaSelect');
    if (selArea) selArea.value = nomeArea;

    carregarDisciplinas();

    if (typeof atualizarFiltroAreasTurmas === 'function') {
      try { atualizarFiltroAreasTurmas(); } catch(err){}
    }

    mostrarNotificacao?.(`Secção / Área "${nomeArea}" cadastrada com sucesso! Ela foi adicionada à lista de filtros.`, 'success');
  });
}

async function carregarDisciplinas() {
  const tbody = document.getElementById('tabelaDisciplinas');
  try {
    const selClasse = document.getElementById('filtroDisciplinasClasseSelect');
    if (selClasse && state.filtroDisciplinaClasse !== undefined) {
      selClasse.value = state.filtroDisciplinaClasse;
    }

    const selArea = document.getElementById('filtroDisciplinasAreaSelect');
    if (selArea && state.filtroDisciplinaArea !== undefined) {
      selArea.value = state.filtroDisciplinaArea;
    }

    const qParams = new URLSearchParams();
    if (state.filtroDisciplinaClasse) qParams.set('classe', state.filtroDisciplinaClasse);
    if (state.filtroDisciplinaArea) qParams.set('area', state.filtroDisciplinaArea);
    const buscaVal = (document.getElementById('filtroDisciplinasBusca')?.value || '').trim();
    if (buscaVal) qParams.set('search', buscaVal);

    const url = '/api/v1/disciplinas' + (qParams.toString() ? '?' + qParams.toString() : '');
    const [resD, resStats] = await Promise.all([
      apiFetch(url),
      apiFetch('/api/v1/disciplinas/stats').catch(() => ({ success: false }))
    ]);

    if (resD && resD.success) {
      let lista = resD.data || [];

      // Filtro defensivo no client-side para garantir 100% de consistência imediata
      if (state.filtroDisciplinaClasse) {
        const digitosClasse = (state.filtroDisciplinaClasse.match(/\d+/) || [''])[0];
        if (digitosClasse) {
          lista = lista.filter(d => (d.classe || '').includes(digitosClasse));
        }
      }
      if (state.filtroDisciplinaArea) {
        const areaFiltroNorm = state.filtroDisciplinaArea.trim().toLowerCase();
        lista = lista.filter(d => {
          const dAreaNorm = (d.area || '').trim().toLowerCase();
          if (areaFiltroNorm.includes('geral')) {
            return dAreaNorm.includes('geral') || !dAreaNorm;
          }
          return dAreaNorm.includes(areaFiltroNorm);
        });
      }
      if (buscaVal) {
        const bLow = buscaVal.toLowerCase();
        lista = lista.filter(d => 
          (d.nome || '').toLowerCase().includes(bLow) || 
          (d.codigo || '').toLowerCase().includes(bLow)
        );
      }

      state.disciplinasFiltradasAtuais = lista;

      // Sincronizar catálogo global se sem filtros restritivos
      if (!state.filtroDisciplinaClasse && !state.filtroDisciplinaArea && !buscaVal) {
        state.todasDisciplinas = lista;
      } else {
        const exist = state.todasDisciplinas || [];
        const ids = new Set(exist.map(x => x.id));
        lista.forEach(d => {
          if (!ids.has(d.id)) exist.push(d);
        });
        state.todasDisciplinas = exist;
      }

      if (!tbody) return;

      if (lista.length === 0) {
        const descClasse = state.filtroDisciplinaClasse || 'Todas as Classes';
        const descArea = state.filtroDisciplinaArea ? `na área "${state.filtroDisciplinaArea}"` : '';
        const descBusca = buscaVal ? `com o termo "${buscaVal}"` : '';
        tbody.innerHTML = `
          <tr>
            <td colspan="7" class="text-center py-5">
              <div class="text-muted">
                <i class="bi bi-info-circle fs-3 text-secondary d-block mb-2"></i>
                <div class="fw-semibold">Nenhuma disciplina encontrada</div>
                <div class="small text-muted mt-1">
                  Não foram encontradas disciplinas cadastradas para <strong>${descClasse}</strong> ${descArea} ${descBusca}.
                </div>
                <div class="mt-3">
                  <button class="btn btn-outline-primary btn-sm me-2" onclick="modalNovaDisciplina()">
                    <i class="bi bi-plus-circle me-1"></i> Cadastrar Disciplina
                  </button>
                  <button class="btn btn-outline-secondary btn-sm" onclick="filtrarDisciplinasClasse(''); filtrarDisciplinasArea('');">
                    <i class="bi bi-arrow-repeat me-1"></i> Limpar Filtros
                  </button>
                </div>
              </div>
            </td>
          </tr>
        `;
      } else {
        tbody.innerHTML = lista.map(d => `
          <tr>
            <td><code>${d.codigo}</code></td>
            <td><strong>${d.nome}</strong></td>
            <td><span class="badge bg-secondary">${d.classe || '10ª Classe'}</span></td>
            <td><small class="text-muted fw-semibold">${d.area || 'Geral'}</small></td>
            <td>${d.carga_horaria} horas/semana</td>
            <td>${d.ano_letivo}</td>
            <td class="text-end">
              <div class="d-inline-flex gap-1">
                <button class="btn btn-outline-primary btn-sm py-0 px-2" onclick="modalEditarDisciplina('${d.id}')" title="Editar Disciplina Curricular">
                  <i class="bi bi-pencil-square me-1"></i>Editar
                </button>
                <button class="btn btn-outline-danger btn-sm py-0 px-2" onclick="eliminarDisciplina('${d.id}', '${(d.nome || '').replace(/'/g, "\\'")}')" title="Eliminar Disciplina">
                  <i class="bi bi-trash me-1"></i>Eliminar
                </button>
              </div>
            </td>
          </tr>
        `).join('');
      }
    } else {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger"><i class="bi bi-exclamation-triangle me-1"></i> Erro ao carregar disciplinas do servidor.</td></tr>`;
      }
    }

    if (resStats && resStats.success) {
      renderizarGraficoReprovacao(resStats.data.rankingReprovacao || []);
    }
  } catch (err) {
    console.error('Erro ao carregar disciplinas:', err);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger"><i class="bi bi-exclamation-triangle me-1"></i> Erro ao carregar disciplinas: ${err.message || 'Falha de comunicação'}</td></tr>`;
    }
  }
}

function renderizarGraficoReprovacao(ranking) {
  const ctx = document.getElementById('chartDisciplinasReprovacao');
  if (!ctx) return;
  if (state.charts.reprovacao) state.charts.reprovacao.destroy();

  const labels = ranking.map(r => r.nome);
  const data = ranking.map(r => r.taxaReprovacao);

  state.charts.reprovacao = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: '% Negativas',
        data,
        backgroundColor: '#dc2626'
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: { legend: { display: false } }
    }
  });
}

function modalNovaDisciplina() {
  const classeInicial = state.filtroDisciplinaClasse || '10ª Classe';
  const areasIniciais = typeof window.obterTodasAreasOficiais === 'function'
    ? window.obterTodasAreasOficiais(classeInicial)
    : ['Ensino Geral', 'Ciências com Biologia', 'Ciências com Desenho', 'Letras com Geografia', 'Letras com História'];

  const optAreas = areasIniciais.map(a => 
    `<option value="${a}" ${state.filtroDisciplinaArea === a ? 'selected' : ''}>${a}</option>`
  ).join('');

  abrirModal('Nova Disciplina Curricular', `
    <form id="formModalDisc">
      <div class="row g-3">
        <div class="col-md-8">
          <label class="form-label small fw-semibold">Nome da Disciplina *</label>
          <input type="text" id="mdNome" class="form-control" required placeholder="Ex: Matemática, Física, Português...">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Código Curricular *</label>
          <input type="text" id="mdCodigo" class="form-control" required placeholder="Ex: MAT-10">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Grupo de Classe *</label>
          <select id="mdClasse" class="form-select" required onchange="aoMudarClasseModalNovaDisc(this.value)">
            <option value="7ª Classe" ${classeInicial === '7ª Classe' ? 'selected' : ''}>7ª Classe</option>
            <option value="8ª Classe" ${classeInicial === '8ª Classe' ? 'selected' : ''}>8ª Classe</option>
            <option value="9ª Classe" ${classeInicial === '9ª Classe' ? 'selected' : ''}>9ª Classe</option>
            <option value="10ª Classe" ${classeInicial === '10ª Classe' ? 'selected' : ''}>10ª Classe</option>
            <option value="11ª Classe" ${classeInicial === '11ª Classe' ? 'selected' : ''}>11ª Classe</option>
            <option value="12ª Classe" ${classeInicial === '12ª Classe' ? 'selected' : ''}>12ª Classe</option>
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Secção / Área de Estudo *</label>
          <select id="mdArea" class="form-select" required>
            ${optAreas}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Carga Horária (Aulas/Semana)</label>
          <input type="number" id="mdCarga" class="form-control" value="5" min="1" max="20" required>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Ano Lectivo</label>
          <input type="text" id="mdAnoLetivo" class="form-control" value="2026" required>
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4"><i class="bi bi-plus-circle me-1"></i> Criar Disciplina no Plano Curricular</button>
    </form>
  `);

  window.aoMudarClasseModalNovaDisc = function(novaClasse) {
    const selArea = document.getElementById('mdArea');
    if (!selArea) return;
    const areas = typeof window.obterTodasAreasOficiais === 'function'
      ? window.obterTodasAreasOficiais(novaClasse)
      : ['Ensino Geral'];
    selArea.innerHTML = areas.map(a => `<option value="${a}">${a}</option>`).join('');
  };

  document.getElementById('formModalDisc').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const areaVal = document.getElementById('mdArea').value;
      const body = {
        nome: document.getElementById('mdNome').value,
        codigo: document.getElementById('mdCodigo').value,
        classe: document.getElementById('mdClasse').value,
        area: areaVal,
        carga_horaria: Number(document.getElementById('mdCarga').value),
        ano_letivo: document.getElementById('mdAnoLetivo').value || '2026'
      };
      const res = await apiFetch('/api/v1/disciplinas', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success) {
        // Garantir que a área cadastrada fique salva no catálogo e apareça no filtro
        if (areaVal) {
          const chAll = 'sige_custom_areas_all';
          const exAll = JSON.parse(localStorage.getItem(chAll) || '[]');
          if (!exAll.includes(areaVal)) {
            exAll.push(areaVal);
            localStorage.setItem(chAll, JSON.stringify(exAll));
          }
        }
        fecharModal();
        await carregarDisciplinas();
        atualizarSelectAreasDisciplinas(state.filtroDisciplinaClasse);
        mostrarNotificacao?.('Disciplina criada com sucesso!', 'success');
      }
    } catch (err) {
      alert(err.message || 'Erro ao criar disciplina');
    }
  });
}

async function modalEditarDisciplina(disciplinaId) {
  try {
    const res = await apiFetch(`/api/v1/disciplinas/${disciplinaId}`);
    if (!res.success || !res.data) return alert('Disciplina não encontrada');
    const d = res.data;

    const classes = ['7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'];
    const optClasses = classes.map(c => `<option value="${c}" ${c === d.classe ? 'selected' : ''}>${c}</option>`).join('');

    const areasDisponiveis = typeof window.obterTodasAreasOficiais === 'function'
      ? window.obterTodasAreasOficiais(d.classe)
      : ['Ensino Geral'];
    if (d.area && !areasDisponiveis.includes(d.area)) {
      areasDisponiveis.push(d.area);
    }
    const optAreas = areasDisponiveis.map(a => `<option value="${a}" ${a === d.area ? 'selected' : ''}>${a}</option>`).join('');

    abrirModal(`Editar Disciplina: ${d.nome}`, `
      <form id="formModalEditarDisc">
        <div class="row g-3">
          <div class="col-md-8">
            <label class="form-label small fw-semibold">Nome da Disciplina *</label>
            <input type="text" id="mdeNome" class="form-control" required value="${d.nome || ''}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Código Curricular *</label>
            <input type="text" id="mdeCodigo" class="form-control" required value="${d.codigo || ''}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Grupo de Classe *</label>
            <select id="mdeClasse" class="form-select" required onchange="aoMudarClasseModalEditarDisc(this.value)">
              ${optClasses}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Secção / Área de Estudo *</label>
            <select id="mdeArea" class="form-select" required>
              ${optAreas}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Carga Horária Semanal (Horas)</label>
            <input type="number" id="mdeCarga" class="form-control" value="${d.carga_horaria || 5}" min="1" max="40" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Ano Lectivo</label>
            <input type="text" id="mdeAnoLetivo" class="form-control" value="${d.ano_letivo || '2026'}" required>
          </div>
        </div>
        <div class="d-flex gap-2 justify-content-end mt-4">
          <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
          <button type="submit" class="btn btn-primary btn-sm px-4">Salvar Alterações</button>
        </div>
      </form>
    `);

    window.aoMudarClasseModalEditarDisc = function(novaClasse) {
      const selArea = document.getElementById('mdeArea');
      if (!selArea) return;
      const areas = typeof window.obterTodasAreasOficiais === 'function'
        ? window.obterTodasAreasOficiais(novaClasse)
        : ['Ensino Geral'];
      selArea.innerHTML = areas.map(a => `<option value="${a}">${a}</option>`).join('');
    };

    document.getElementById('formModalEditarDisc').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const body = {
          nome: document.getElementById('mdeNome').value,
          codigo: document.getElementById('mdeCodigo').value,
          classe: document.getElementById('mdeClasse').value,
          area: document.getElementById('mdeArea').value,
          carga_horaria: Number(document.getElementById('mdeCarga').value),
          ano_letivo: document.getElementById('mdeAnoLetivo').value || '2026'
        };
        const updRes = await apiFetch(`/api/v1/disciplinas/${disciplinaId}`, {
          method: 'PUT',
          body: JSON.stringify(body)
        });
        if (updRes.success) {
          mostrarNotificacao('Disciplina curricular actualizada com sucesso!', 'success');
          fecharModal();
          carregarDisciplinas();
        } else {
          alert(updRes.message || 'Erro ao actualizar disciplina');
        }
      } catch (err) {
        alert(err.message || 'Erro ao comunicar com o servidor');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados da disciplina: ' + err.message);
  }
}

async function eliminarDisciplina(disciplinaId, nome) {
  if (!confirm(`Tem a certeza que deseja eliminar a disciplina curricular "${nome}"?\n\nEsta acção removerá as alocações e avaliações associadas.`)) return;
  try {
    const res = await apiFetch(`/api/v1/disciplinas/${disciplinaId}`, {
      method: 'DELETE'
    });
    if (res.success) {
      mostrarNotificacao('Disciplina curricular eliminada com sucesso!', 'success');
      await carregarDisciplinas();
    } else {
      alert(res.message || 'Erro ao eliminar disciplina');
    }
  } catch (err) {
    alert(err.message || 'Erro ao comunicar com o servidor');
  }
}

