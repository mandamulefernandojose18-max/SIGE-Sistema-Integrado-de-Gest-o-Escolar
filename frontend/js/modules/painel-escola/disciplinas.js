/**
 * SIGE - PAINEL-ESCOLA | Disciplinas & Currículo
 * Ficheiro de código independente do menu: disciplinas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== GESTÃO DE NÍVEIS CURRICULARES DA INSTITUIÇÃO ====================
window.obterNiveisInstituicao = function() {
  const padrao = ['Nível 1', 'Nível 2', 'Nível 3', 'Nível 4', 'Nível 5', 'Nível 6'];
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id
    || 'padrao';
  const chave = `sige_niveis_instituicao_${escolaId}`;

  let salvos = [];
  try {
    salvos = JSON.parse(localStorage.getItem(chave) || '[]');
  } catch (_) {}

  const setNiveis = new Set([...padrao, ...salvos]);
  (state.todasDisciplinas || []).forEach(d => {
    const c = (d.classe || '').trim();
    if (c.toLowerCase().includes('nível') || c.toLowerCase().includes('nivel')) {
      setNiveis.add(c);
    }
  });
  (state.todasTurmas || []).forEach(t => {
    const g = (t.grau_ano || '').trim();
    if (g.toLowerCase().includes('nível') || g.toLowerCase().includes('nivel')) {
      setNiveis.add(g);
    }
  });

  return Array.from(setNiveis).sort((a, b) => {
    const numA = parseInt(a.replace(/\D/g, '')) || 0;
    const numB = parseInt(b.replace(/\D/g, '')) || 0;
    return numA - numB;
  });
};

window.adicionarNivelInstituicao = function(novoNivel) {
  if (!novoNivel) return null;
  let normalizado = novoNivel.trim();
  if (!normalizado) return null;
  if (/^\d+$/.test(normalizado)) {
    normalizado = `Nível ${normalizado}`;
  } else if (!normalizado.toLowerCase().startsWith('nível') && !normalizado.toLowerCase().startsWith('nivel')) {
    normalizado = `Nível ${normalizado}`;
  }

  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id
    || 'padrao';
  const chave = `sige_niveis_instituicao_${escolaId}`;

  let salvos = [];
  try {
    salvos = JSON.parse(localStorage.getItem(chave) || '[]');
  } catch (_) {}

  if (!salvos.includes(normalizado)) {
    salvos.push(normalizado);
    localStorage.setItem(chave, JSON.stringify(salvos));
  }
  return normalizado;
};

window.promptAdicionarNivelModal = function(selectId, callback) {
  const nome = prompt('Digite o Nível que deseja adicionar à instituição (ex: Nível 1, Nível 2, Nível 3...):', 'Nível ');
  if (!nome || !nome.trim()) {
    const sel = document.getElementById(selectId);
    if (sel && sel.value === '__NOVO_NIVEL__') {
      const niveis = window.obterNiveisInstituicao();
      sel.value = niveis[0] || 'Nível 1';
    }
    return;
  }
  const adicionado = window.adicionarNivelInstituicao(nome);
  if (adicionado) {
    const sel = document.getElementById(selectId);
    if (sel) {
      const niveis = window.obterNiveisInstituicao();
      sel.innerHTML = niveis.map(n => `<option value="${n}" ${n === adicionado ? 'selected' : ''}>${n}</option>`).join('') +
        `<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>`;
      sel.value = adicionado;
      if (typeof callback === 'function') callback(adicionado);
    }
  }
};

window.modalAdicionarNivelCurricular = function() {
  const niveisAtuais = window.obterNiveisInstituicao();
  const listaNiveisHtml = niveisAtuais.map(n => `
    <span class="badge bg-success bg-opacity-10 text-success border border-success p-2 fs-6">
      <i class="bi bi-layers-fill me-1"></i>${n}
    </span>
  `).join('');

  abrirModal('Gerir & Adicionar Níveis Curriculares da Instituição', `
    <form id="formAdicionarNivelInst">
      <div class="alert alert-info py-2 small mb-3">
        <i class="bi bi-info-circle-fill me-1"></i> Se a sua instituição oferece ensino técnico, profissionalizante ou superior baseado em <strong>Níveis</strong> em vez de classes, adicione aqui os níveis curriculares utilizados (ex: Nível 1, Nível 2, Nível 3, Nível 4, Nível 5...).
      </div>

      <div class="mb-3">
        <label class="form-label small fw-bold text-uppercase text-secondary">Níveis Actualmente Activos na Instituição:</label>
        <div class="d-flex flex-wrap gap-2 p-3 bg-light rounded border">
          ${listaNiveisHtml}
        </div>
      </div>

      <div class="row g-2 mb-3 align-items-end">
        <div class="col-md-8">
          <label class="form-label small fw-semibold">Novo Nível Curricular *</label>
          <input type="text" id="inputNovoNivelNome" class="form-control" placeholder="Ex: Nível 1, Nível 2, Nível 3... ou apenas o número (1, 2...)" required autofocus>
          <small class="text-muted" style="font-size: 0.73rem;">Se digitar apenas "1", será salvo automaticamente como "Nível 1".</small>
        </div>
        <div class="col-md-4">
          <button type="submit" class="btn btn-success w-100 fw-semibold">
            <i class="bi bi-plus-circle me-1"></i> Adicionar Nível
          </button>
        </div>
      </div>

      <div class="p-3 bg-light rounded border mb-3">
        <div class="small fw-bold text-muted text-uppercase mb-2">Adição Rápida de Níveis Padrão:</div>
        <div class="d-flex flex-wrap gap-2">
          ${[1, 2, 3, 4, 5, 6].map(i => `
            <button type="button" class="btn btn-outline-secondary btn-sm" onclick="adicionarNivelRapido('Nível ${i}')">
              + Nível ${i}
            </button>
          `).join('')}
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2 mt-4">
        <button type="button" class="btn btn-primary px-4" onclick="fecharModal(); carregarDisciplinas(); if (typeof carregarEscolaETurmas === 'function') carregarEscolaETurmas();">
          <i class="bi bi-check-lg me-1"></i> Concluído
        </button>
      </div>
    </form>
  `);

  window.adicionarNivelRapido = function(nivelNome) {
    window.adicionarNivelInstituicao(nivelNome);
    fecharModal();
    window.modalAdicionarNivelCurricular();
  };

  document.getElementById('formAdicionarNivelInst').addEventListener('submit', (e) => {
    e.preventDefault();
    const val = document.getElementById('inputNovoNivelNome').value;
    const add = window.adicionarNivelInstituicao(val);
    if (add) {
      fecharModal();
      window.modalAdicionarNivelCurricular();
      if (typeof carregarDisciplinas === 'function') carregarDisciplinas();
      if (typeof carregarEscolaETurmas === 'function') carregarEscolaETurmas();
    }
  });
};

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
  const classesOficiais = [
    '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
    '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
  ];
  const niveisOficiais = window.obterNiveisInstituicao();

  const classeAtiva = (state.filtroDisciplinaClasse || '10ª Classe').trim();
  const isNivel = classeAtiva.toLowerCase().includes('nível') || classeAtiva.toLowerCase().includes('nivel');
  const listaInicial = isNivel ? niveisOficiais : classesOficiais;
  let optClasses = listaInicial.map(c => `<option value="${c}" ${c === classeAtiva ? 'selected' : ''}>${c}</option>`).join('');
  if (isNivel) {
    optClasses += `<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>`;
  }

  abrirModal('Cadastrar Secção / Área de Estudo', `
    <form id="formModalSeccaoArea">
      <div class="mb-3">
        <label class="form-label small fw-bold text-uppercase text-secondary mb-1">
          <i class="bi bi-sliders me-1 text-primary"></i> Modalidade Curricular:
        </label>
        <div class="d-flex gap-4 p-2 bg-light rounded border">
          <div class="form-check">
            <input class="form-check-input" type="radio" name="msaRegime" id="msaRegimeClasse" value="CLASSE" ${!isNivel ? 'checked' : ''} onchange="window.alternarRegimeModalSeccao(this.value)">
            <label class="form-check-label fw-semibold" for="msaRegimeClasse">
              <i class="bi bi-mortarboard me-1 text-primary"></i> Classe (1ª à 12ª)
            </label>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="radio" name="msaRegime" id="msaRegimeNivel" value="NIVEL" ${isNivel ? 'checked' : ''} onchange="window.alternarRegimeModalSeccao(this.value)">
            <label class="form-check-label fw-semibold" for="msaRegimeNivel">
              <i class="bi bi-layers-fill me-1 text-success"></i> Nível (Nível 1, 2, ...)
            </label>
          </div>
        </div>
      </div>
      <div class="mb-3">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <label class="form-label small fw-semibold mb-0" id="labelMsaClasse">${isNivel ? 'Nível Correspondente *' : 'Classe Correspondente *'}</label>
          <button type="button" id="btnAdicionarNivelSeccao" class="btn btn-link btn-sm p-0 text-success fw-semibold small text-decoration-none" style="${isNivel ? '' : 'display: none;'}" onclick="window.promptAdicionarNivelModal('msaClasse')">
            <i class="bi bi-plus-circle me-1"></i>+ Adicionar Nível
          </button>
        </div>
        <select id="msaClasse" class="form-select" required onchange="if(this.value==='__NOVO_NIVEL__') window.promptAdicionarNivelModal('msaClasse')">
          ${optClasses}
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nome da Secção ou Área de Estudo *</label>
        <input type="text" id="msaNome" class="form-control" placeholder="Ex: Ciências com Geografia, Ciências com Biologia, Contabilidade, Eletricidade..." required>
        <small class="text-muted">A nova secção/área aparecerá automaticamente em todas as listas de filtros, turmas e disciplinas.</small>
      </div>
      <button type="submit" class="btn btn-primary w-100 fw-semibold">
        <i class="bi bi-plus-circle me-1"></i> Criar Secção / Área
      </button>
    </form>
  `);

  window.alternarRegimeModalSeccao = function(regime) {
    const sel = document.getElementById('msaClasse');
    const lbl = document.getElementById('labelMsaClasse');
    const btnAdd = document.getElementById('btnAdicionarNivelSeccao');
    if (!sel) return;
    if (regime === 'NIVEL') {
      if (lbl) lbl.textContent = 'Nível Correspondente *';
      if (btnAdd) btnAdd.style.display = 'inline-block';
      const niveis = window.obterNiveisInstituicao();
      sel.innerHTML = niveis.map(n => `<option value="${n}">${n}</option>`).join('') +
        `<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>`;
    } else {
      if (lbl) lbl.textContent = 'Classe Correspondente *';
      if (btnAdd) btnAdd.style.display = 'none';
      sel.innerHTML = classesOficiais.map(c => `<option value="${c}">${c}</option>`).join('');
    }
  };

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
    let resD = null;
    let resStats = null;
    try {
      const [rD, rS] = await Promise.all([
        apiFetch(url),
        apiFetch('/api/v1/disciplinas/stats').catch(() => ({ success: false }))
      ]);
      resD = rD;
      resStats = rS;
    } catch (fetchErr) {
      console.warn('Erro na requisição à API de disciplinas, verificando contingência offline:', fetchErr);
      const cacheLocal = localStorage.getItem('sige_cache_disciplinas');
      if (state.todasDisciplinas && state.todasDisciplinas.length > 0) {
        resD = { success: true, data: state.todasDisciplinas, _fromCache: true };
      } else if (cacheLocal) {
        try {
          const parsed = JSON.parse(cacheLocal);
          if (Array.isArray(parsed) && parsed.length > 0) {
            resD = { success: true, data: parsed, _fromCache: true };
          }
        } catch (_) {}
      }
      if (!resD) throw fetchErr;
    }

    if (resD && resD.success) {
      let lista = resD.data || [];
      if (!resD._fromCache) {
        try { localStorage.setItem('sige_cache_disciplinas', JSON.stringify(lista)); } catch(_) {}
      }

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

      // Sincronizar dinamicamente o seletor de filtro apenas com as Classes ou Níveis reais da instituição
      const selClasseEl = document.getElementById('filtroDisciplinasClasseSelect');
      if (selClasseEl) {
        const classesUnicas = Array.from(new Set(
          (state.todasDisciplinas || []).map(d => (d.classe || '').trim()).filter(Boolean)
        )).sort((a, b) => {
          const numA = parseInt(a.replace(/\D/g, '')) || 0;
          const numB = parseInt(b.replace(/\D/g, '')) || 0;
          return numA - numB;
        });

        if (classesUnicas.length === 0) {
          selClasseEl.innerHTML = '<option value="">-- Nenhuma classe/nível cadastrado --</option>';
        } else {
          let optHtml = '<option value="">Todas as Classes / Níveis</option>';
          classesUnicas.forEach(c => {
            const isAct = (state.filtroDisciplinaClasse === c) ? 'selected' : '';
            optHtml += `<option value="${c}" ${isAct}>${c}</option>`;
          });
          selClasseEl.innerHTML = optHtml;
        }
      }

      if (!tbody) return;

      if (lista.length === 0) {
        const totalInstituicao = (state.todasDisciplinas || []).length;
        if (totalInstituicao === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="7" class="text-center py-5">
                <div class="text-muted">
                  <i class="bi bi-mortarboard fs-2 text-primary d-block mb-2"></i>
                  <div class="fw-semibold">Nenhuma disciplina cadastrada nesta instituição</div>
                  <div class="small text-muted mt-1">
                    Cada instituição define as suas políticas curriculares (<strong>Classe da 1ª à 12ª</strong> ou <strong>Nível 1, 2...</strong>).<br>
                    Cadastre as disciplinas em função das políticas e critérios que a sua instituição define.
                  </div>
                  <div class="mt-3">
                    <button class="btn btn-primary btn-sm px-4" onclick="modalNovaDisciplina()">
                      <i class="bi bi-plus-circle me-1"></i> Cadastrar Primeira Disciplina
                    </button>
                  </div>
                </div>
              </td>
            </tr>
          `;
        } else {
          const descClasse = state.filtroDisciplinaClasse || 'Todas as Classes / Níveis';
          const descArea = state.filtroDisciplinaArea ? `na área "${state.filtroDisciplinaArea}"` : '';
          const descBusca = buscaVal ? `com o termo "${buscaVal}"` : '';
          tbody.innerHTML = `
            <tr>
              <td colspan="7" class="text-center py-5">
                <div class="text-muted">
                  <i class="bi bi-info-circle fs-3 text-secondary d-block mb-2"></i>
                  <div class="fw-semibold">Nenhuma disciplina encontrada com estes filtros</div>
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
        }
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
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center py-5">
            <div class="text-danger mb-2">
              <i class="bi bi-exclamation-triangle-fill fs-3 text-danger d-block mb-2"></i>
              <div class="fw-semibold">Falha de comunicação ao carregar disciplinas</div>
              <div class="small text-muted mt-1">
                ${err.message || 'Verifique a ligação à rede ou confirme se o servidor SIGE está ativo.'}
              </div>
            </div>
            <div class="mt-3">
              <button class="btn btn-outline-primary btn-sm px-3" onclick="carregarDisciplinas()">
                <i class="bi bi-arrow-clockwise me-1"></i> Tentar Novamente
              </button>
            </div>
          </td>
        </tr>
      `;
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
  const classesOficiais = [
    '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
    '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
  ];
  const niveisOficiais = window.obterNiveisInstituicao();

  const classeFiltroAtiva = (state.filtroDisciplinaClasse || '').trim();
  const isNivelInicial = classeFiltroAtiva.toLowerCase().includes('nível') || classeFiltroAtiva.toLowerCase().includes('nivel');
  const regimeInicial = isNivelInicial ? 'NIVEL' : 'CLASSE';

  const opcoesIniciais = isNivelInicial ? niveisOficiais : classesOficiais;
  const itemInicial = opcoesIniciais.includes(classeFiltroAtiva) ? classeFiltroAtiva : opcoesIniciais[0];

  const areasIniciais = typeof window.obterTodasAreasOficiais === 'function'
    ? window.obterTodasAreasOficiais(itemInicial)
    : ['Ensino Geral', 'Ciências com Biologia', 'Ciências com Desenho', 'Letras com Geografia', 'Letras com História'];

  const optAreas = areasIniciais.map(a => 
    `<option value="${a}" ${state.filtroDisciplinaArea === a ? 'selected' : ''}>${a}</option>`
  ).join('');

  let optOpcoesHtml = opcoesIniciais.map(o => 
    `<option value="${o}" ${itemInicial === o ? 'selected' : ''}>${o}</option>`
  ).join('');
  if (isNivelInicial) {
    optOpcoesHtml += `<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>`;
  }

  abrirModal('Nova Disciplina Curricular', `
    <form id="formModalDisc">
      <div class="row g-3">
        <!-- SELETOR DE MODALIDADE: CLASSE OU NÍVEL -->
        <div class="col-md-12">
          <label class="form-label small fw-bold text-uppercase text-secondary mb-1">
            <i class="bi bi-sliders me-1 text-primary"></i> 1. Modalidade Curricular:
          </label>
          <div class="d-flex gap-4 p-2 bg-light rounded border">
            <div class="form-check">
              <input class="form-check-input" type="radio" name="modalRegimeCurricular" id="regimeClasse" value="CLASSE" ${regimeInicial === 'CLASSE' ? 'checked' : ''} onchange="window.alternarRegimeModalNovaDisc(this.value)">
              <label class="form-check-label fw-semibold" for="regimeClasse">
                <i class="bi bi-mortarboard me-1 text-primary"></i> Classe (1ª à 12ª Classe)
              </label>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="radio" name="modalRegimeCurricular" id="regimeNivel" value="NIVEL" ${regimeInicial === 'NIVEL' ? 'checked' : ''} onchange="window.alternarRegimeModalNovaDisc(this.value)">
              <label class="form-check-label fw-semibold" for="regimeNivel">
                <i class="bi bi-layers me-1 text-success"></i> Nível (Nível 1, Nível 2...)
              </label>
            </div>
          </div>
        </div>

        <div class="col-md-8">
          <label class="form-label small fw-semibold">Nome da Disciplina *</label>
          <input type="text" id="mdNome" class="form-control" required placeholder="Ex: Matemática, Física, Português, Desenho Técnico...">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Código Curricular *</label>
          <input type="text" id="mdCodigo" class="form-control" required placeholder="Ex: MAT-10 ou TEC-N1">
        </div>

        <div class="col-md-6">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <label class="form-label small fw-semibold mb-0" id="labelMdClasse">${regimeInicial === 'NIVEL' ? 'Nível Curricular *' : 'Classe / Grau *'}</label>
            <button type="button" id="btnAdicionarNivelNovaDisc" class="btn btn-link btn-sm p-0 text-success fw-semibold small text-decoration-none" style="${regimeInicial === 'NIVEL' ? '' : 'display: none;'}" onclick="window.promptAdicionarNivelModal('mdClasse', window.aoMudarClasseModalNovaDisc)">
              <i class="bi bi-plus-circle me-1"></i>+ Adicionar Nível
            </button>
          </div>
          <select id="mdClasse" class="form-select" required onchange="aoMudarClasseModalNovaDisc(this.value)">
            ${optOpcoesHtml}
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
          <input type="number" id="mdCarga" class="form-control" value="5" min="1" max="40" required>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Ano Lectivo</label>
          <input type="text" id="mdAnoLetivo" class="form-control" value="2026" required>
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4"><i class="bi bi-plus-circle me-1"></i> Criar Disciplina no Plano Curricular</button>
    </form>
  `);

  window.alternarRegimeModalNovaDisc = function(regime) {
    const sel = document.getElementById('mdClasse');
    const lbl = document.getElementById('labelMdClasse');
    const btnAdd = document.getElementById('btnAdicionarNivelNovaDisc');
    if (!sel) return;
    if (regime === 'NIVEL') {
      if (lbl) lbl.textContent = 'Nível Curricular *';
      if (btnAdd) btnAdd.style.display = 'inline-block';
      const niveis = window.obterNiveisInstituicao();
      sel.innerHTML = niveis.map(n => `<option value="${n}">${n}</option>`).join('') +
        `<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>`;
    } else {
      if (lbl) lbl.textContent = 'Classe / Grau *';
      if (btnAdd) btnAdd.style.display = 'none';
      sel.innerHTML = classesOficiais.map(c => `<option value="${c}">${c}</option>`).join('');
    }
    if (typeof window.aoMudarClasseModalNovaDisc === 'function') {
      window.aoMudarClasseModalNovaDisc(sel.value);
    }
  };

  window.aoMudarClasseModalNovaDisc = function(novaClasse) {
    if (novaClasse === '__NOVO_NIVEL__') {
      return window.promptAdicionarNivelModal('mdClasse', window.aoMudarClasseModalNovaDisc);
    }
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

    const classesOficiais = [
      '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
      '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
    ];
    const niveisOficiais = window.obterNiveisInstituicao();

    const classeVal = (d.classe || '').trim();
    const isNivel = classeVal.toLowerCase().includes('nível') || classeVal.toLowerCase().includes('nivel');
    const regime = isNivel ? 'NIVEL' : 'CLASSE';
    const listaOpcoes = isNivel ? [...niveisOficiais] : [...classesOficiais];

    if (!listaOpcoes.includes(classeVal) && classeVal) {
      listaOpcoes.push(classeVal);
    }
    let optOpcoes = listaOpcoes.map(c => `<option value="${c}" ${c === classeVal ? 'selected' : ''}>${c}</option>`).join('');
    if (isNivel) {
      optOpcoes += `<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>`;
    }

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
          <!-- MODALIDADE: CLASSE OU NÍVEL -->
          <div class="col-md-12">
            <label class="form-label small fw-bold text-uppercase text-secondary mb-1">
              <i class="bi bi-sliders me-1 text-primary"></i> Modalidade Curricular:
            </label>
            <div class="d-flex gap-4 p-2 bg-light rounded border">
              <div class="form-check">
                <input class="form-check-input" type="radio" name="editRegimeCurricular" id="editRegimeClasse" value="CLASSE" ${regime === 'CLASSE' ? 'checked' : ''} onchange="window.alternarRegimeModalEditarDisc(this.value)">
                <label class="form-check-label fw-semibold" for="editRegimeClasse">
                  <i class="bi bi-mortarboard me-1 text-primary"></i> Classe (1ª à 12ª Classe)
                </label>
              </div>
              <div class="form-check">
                <input class="form-check-input" type="radio" name="editRegimeCurricular" id="editRegimeNivel" value="NIVEL" ${regime === 'NIVEL' ? 'checked' : ''} onchange="window.alternarRegimeModalEditarDisc(this.value)">
                <label class="form-check-label fw-semibold" for="editRegimeNivel">
                  <i class="bi bi-layers me-1 text-success"></i> Nível (Nível 1, Nível 2...)
                </label>
              </div>
            </div>
          </div>

          <div class="col-md-8">
            <label class="form-label small fw-semibold">Nome da Disciplina *</label>
            <input type="text" id="mdeNome" class="form-control" required value="${d.nome || ''}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Código Curricular *</label>
            <input type="text" id="mdeCodigo" class="form-control" required value="${d.codigo || ''}">
          </div>
          <div class="col-md-6">
            <div class="d-flex justify-content-between align-items-center mb-1">
              <label class="form-label small fw-semibold mb-0" id="labelMdeClasse">${regime === 'NIVEL' ? 'Nível Curricular *' : 'Classe / Grau *'}</label>
              <button type="button" id="btnAdicionarNivelEditDisc" class="btn btn-link btn-sm p-0 text-success fw-semibold small text-decoration-none" style="${regime === 'NIVEL' ? '' : 'display: none;'}" onclick="window.promptAdicionarNivelModal('mdeClasse', window.aoMudarClasseModalEditarDisc)">
                <i class="bi bi-plus-circle me-1"></i>+ Adicionar Nível
              </button>
            </div>
            <select id="mdeClasse" class="form-select" required onchange="aoMudarClasseModalEditarDisc(this.value)">
              ${optOpcoes}
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

    window.alternarRegimeModalEditarDisc = function(novoRegime) {
      const sel = document.getElementById('mdeClasse');
      const lbl = document.getElementById('labelMdeClasse');
      const btnAdd = document.getElementById('btnAdicionarNivelEditDisc');
      if (!sel) return;
      if (novoRegime === 'NIVEL') {
        if (lbl) lbl.textContent = 'Nível Curricular *';
        if (btnAdd) btnAdd.style.display = 'inline-block';
        const niveis = window.obterNiveisInstituicao();
        sel.innerHTML = niveis.map(n => `<option value="${n}">${n}</option>`).join('') +
          `<option value="__NOVO_NIVEL__">➕ + Adicionar Outro Nível...</option>`;
      } else {
        if (lbl) lbl.textContent = 'Classe / Grau *';
        if (btnAdd) btnAdd.style.display = 'none';
        sel.innerHTML = classesOficiais.map(c => `<option value="${c}">${c}</option>`).join('');
      }
      if (typeof window.aoMudarClasseModalEditarDisc === 'function') {
        window.aoMudarClasseModalEditarDisc(sel.value);
      }
    };

    window.aoMudarClasseModalEditarDisc = function(novaClasse) {
      if (novaClasse === '__NOVO_NIVEL__') {
        return window.promptAdicionarNivelModal('mdeClasse', window.aoMudarClasseModalEditarDisc);
      }
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

