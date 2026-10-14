/**
 * SIGE - PAINEL-PROFESSOR | Material Did�tico & Escolar
 * Ficheiro de c�digo independente do menu: material-escolar.js
 * Isolamento estrito de painel: Nenhuma liga��o entre pain�is de n�veis distintos.
 */
// ==================== MATERIAL ESCOLAR POR CLASSE ====================
state.materialEscolar = {
  classeAtiva: 'TODAS',
  materiais: [],
  classes: []
};

const CLASSES_SISTEMA_ORDEM = [
  '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
  '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
];

async function carregarPainelMaterialEscolar(classeFiltro) {
  if (classeFiltro !== undefined) {
    state.materialEscolar.classeAtiva = classeFiltro;
  }
  const grelha = document.getElementById('grelhaMateriaisEscolares');
  const badgeAtiva = document.getElementById('badgeClasseAtiva');
  const btnCarregar = document.getElementById('btnCarregarMaterial');
  const isAluno = state.user?.role === 'ALUNO';

  if (btnCarregar) {
    btnCarregar.style.display = isAluno ? 'none' : '';
  }

  // Escola ativa do usuário / inspeção
  const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id;

  // Limpar materiais em memória antes de carregar para evitar resquícios entre escolas
  state.materialEscolar.materiais = [];

  try {
    // 1. Obter contagens por classe estritamente da escola ativa
    const paramEscola = escolaAtivaId ? `?escola_id=${encodeURIComponent(escolaAtivaId)}` : '';
    const resClasses = await apiFetch(`/api/v1/material-escolar/classes${paramEscola}`);
    if (resClasses.success) {
      state.materialEscolar.classes = resClasses.data || [];
      if (isAluno && state.materialEscolar.classes.length > 0) {
        state.materialEscolar.classeAtiva = state.materialEscolar.classes[0].classe;
      }
      renderizarBotoesClasses();
    }

    if (badgeAtiva) {
      badgeAtiva.textContent = state.materialEscolar.classeAtiva === 'TODAS' ? 'Todas as Classes' : state.materialEscolar.classeAtiva;
    }

    // 2. Obter materiais da classe seleccionada estritamente da escola ativa
    const queryParts = [];
    if (state.materialEscolar.classeAtiva !== 'TODAS') {
      queryParts.push(`classe=${encodeURIComponent(state.materialEscolar.classeAtiva)}`);
    }
    if (escolaAtivaId) {
      queryParts.push(`escola_id=${encodeURIComponent(escolaAtivaId)}`);
    }
    const query = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';
    const resMat = await apiFetch(`/api/v1/material-escolar${query}`);
    if (resMat.success) {
      state.materialEscolar.materiais = resMat.data || [];
      filtrarMateriaisEscolares();
    } else {
      if (grelha) grelha.innerHTML = `<div class="col-12"><div class="alert alert-warning text-center">Não foi possível carregar os materiais escolares.</div></div>`;
    }
  } catch (err) {
    if (grelha) grelha.innerHTML = `<div class="col-12"><div class="alert alert-danger text-center">Erro ao contactar o servidor: ${err.message || ''}</div></div>`;
  }
}

function renderizarBotoesClasses() {
  const container = document.getElementById('containerBotoesClassesMateriais') || document.getElementById('containerBotoesClasses');
  if (!container) return;

  const isAluno = state.user?.role === 'ALUNO';
  const selectMaterialClasse = document.getElementById('filtroMaterialClasseSelect');
  if (isAluno) {
    const clsAluno = state.materialEscolar.classeAtiva !== 'TODAS' ? state.materialEscolar.classeAtiva : (state.materialEscolar.classes[0]?.classe || 'Minha Classe');
    const qtd = state.materialEscolar.classes[0]?.totalMateriais || state.materialEscolar.materiais?.length || 0;
    if (selectMaterialClasse) {
      selectMaterialClasse.innerHTML = `<option value="${clsAluno}">${clsAluno} (${qtd})</option>`;
      selectMaterialClasse.disabled = true;
    }
    return;
  }

  const totalGeral = state.materialEscolar.classes.reduce((acc, c) => acc + (c.totalMateriais || 0), 0);
  const mapaContagens = new Map(state.materialEscolar.classes.map(c => [c.classe, c.totalMateriais || 0]));

  if (selectMaterialClasse) {
    selectMaterialClasse.disabled = false;
    let optHtml = `<option value="TODAS">Todas as Classes (${totalGeral})</option>`;
    CLASSES_SISTEMA_ORDEM.forEach(cls => {
      const qtd = mapaContagens.get(cls) || 0;
      optHtml += `<option value="${cls}">${cls} (${qtd})</option>`;
    });
    selectMaterialClasse.innerHTML = optHtml;
    selectMaterialClasse.value = state.materialEscolar.classeAtiva || 'TODAS';
  }
}

function selecionarClasseMaterial(classe) {
  if (state.user?.role === 'ALUNO') return; // Aluno não pode trocar para outras classes
  state.materialEscolar.classeAtiva = classe;
  const badgeAtiva = document.getElementById('badgeClasseAtiva');
  if (badgeAtiva) badgeAtiva.textContent = classe === 'TODAS' ? 'Todas as Classes' : classe;
  const selectMaterialClasse = document.getElementById('filtroMaterialClasseSelect');
  if (selectMaterialClasse && selectMaterialClasse.value !== classe) {
    selectMaterialClasse.value = classe;
  }
  renderizarBotoesClasses();
  carregarPainelMaterialEscolar(classe);
}

function filtrarMateriaisEscolares() {
  const grelha = document.getElementById('grelhaMateriaisEscolares');
  const contador = document.getElementById('contadorMateriaisEncontrados');
  if (!grelha) return;

  const termo = (document.getElementById('filtroMaterialBusca')?.value || '').toLowerCase().trim();
  const tipoFiltro = document.getElementById('filtroMaterialTipo')?.value || '';
  const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id;

  const filtrados = (state.materialEscolar.materiais || []).filter(m => {
    // Isolamento estrito no cliente: nunca exibir publicações de outra escola
    if (escolaAtivaId && m.escola_id && String(m.escola_id) !== String(escolaAtivaId)) {
      return false;
    }

    const matchTermo = !termo ||
      m.titulo.toLowerCase().includes(termo) ||
      (m.descricao && m.descricao.toLowerCase().includes(termo)) ||
      (m.disciplina?.nome && m.disciplina.nome.toLowerCase().includes(termo)) ||
      (m.nome_arquivo && m.nome_arquivo.toLowerCase().includes(termo));

    const matchTipo = !tipoFiltro || m.tipo === tipoFiltro;

    return matchTermo && matchTipo;
  });

  if (contador) {
    contador.textContent = `${filtrados.length} ${filtrados.length === 1 ? 'material disponível' : 'materiais disponíveis'}`;
  }

  const isAluno = state.user?.role === 'ALUNO';

  if (filtrados.length === 0) {
    grelha.innerHTML = `
      <div class="col-12 text-center py-5">
        <div class="p-4 bg-light rounded-4 border d-inline-block">
          <i class="bi bi-folder-x text-muted display-4 d-block mb-2"></i>
          <h6 class="fw-bold text-secondary mb-1">Nenhum material encontrado</h6>
          <p class="text-muted small mb-3">Não existem ficheiros carregados para esta selecção.</p>
          ${!isAluno ? `
            <button class="btn btn-primary btn-sm rounded-pill" onclick="modalCarregarMaterialEscolar()">
              <i class="bi bi-cloud-arrow-up-fill me-1"></i> Carregar Primeiro Material da Classe
            </button>
          ` : ''}
        </div>
      </div>
    `;
    return;
  }

  grelha.innerHTML = filtrados.map(m => {
    const ext = (m.extensao || 'pdf').toLowerCase();
    let icone = '<i class="bi bi-file-earmark-text text-secondary fs-1"></i>';
    if (ext === 'pdf') {
      icone = '<i class="bi bi-file-earmark-pdf-fill text-danger fs-1"></i>';
    } else if (['docx', 'doc', 'odt', 'rtf'].includes(ext)) {
      icone = '<i class="bi bi-file-earmark-word-fill text-primary fs-1"></i>';
    } else if (['xlsx', 'xls', 'csv'].includes(ext)) {
      icone = '<i class="bi bi-file-earmark-excel-fill text-success fs-1"></i>';
    } else if (['pptx', 'ppt'].includes(ext)) {
      icone = '<i class="bi bi-file-earmark-ppt-fill text-warning fs-1"></i>';
    } else if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) {
      icone = '<i class="bi bi-file-earmark-zip-fill text-secondary fs-1"></i>';
    } else if (['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg'].includes(ext)) {
      icone = '<i class="bi bi-file-earmark-image-fill text-info fs-1"></i>';
    } else if (['mp4', 'mkv', 'avi', 'mov'].includes(ext)) {
      icone = '<i class="bi bi-file-earmark-play-fill text-danger fs-1"></i>';
    } else if (['mp3', 'wav', 'ogg'].includes(ext)) {
      icone = '<i class="bi bi-file-earmark-music-fill text-success fs-1"></i>';
    } else if (m.arquivo_url && !m.conteudo_base64) {
      icone = '<i class="bi bi-link-45deg text-info fs-1"></i>';
    }

    const tamStr = m.tamanho_bytes ? (m.tamanho_bytes < 1024 * 1024 
      ? `${(m.tamanho_bytes / 1024).toFixed(1)} KB` 
      : `${(m.tamanho_bytes / (1024 * 1024)).toFixed(1)} MB`) : '';

    const discNome = m.disciplina?.nome || 'Geral';

    return `
      <div class="col-md-6 col-lg-4">
        <div class="card h-100 shadow-sm border-0" style="border-radius: 12px; border-left: 4px solid #2563eb !important;">
          <div class="card-body p-3 d-flex flex-column justify-content-between">
            <div>
              <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
                <span class="badge bg-primary text-white fw-bold px-2 py-1 rounded">${m.classe}</span>
                <span class="badge bg-light text-dark border px-2 py-1 rounded">${m.tipo || 'MANUAL'}</span>
              </div>

              <div class="d-flex align-items-center gap-2 mb-2">
                ${icone}
                <div class="overflow-hidden">
                  <h6 class="fw-bold mb-0 text-truncate" title="${m.titulo}">${m.titulo}</h6>
                  <span class="badge bg-info-subtle text-info-emphasis small">${discNome}</span>
                </div>
              </div>

              ${m.descricao ? `<p class="small text-muted mb-2 text-truncate-2" style="font-size: 0.82rem;">${m.descricao}</p>` : ''}
              
              <div class="small text-muted d-flex align-items-center justify-content-between border-top pt-2 mt-2" style="font-size: 0.75rem;">
                <span class="text-truncate" title="${m.nome_arquivo || ''}">
                  <i class="bi bi-paperclip me-1"></i>${m.nome_arquivo || 'Ficheiro'} ${tamStr ? `(${tamStr})` : ''}
                </span>
                <span><i class="bi bi-calendar3 me-1"></i>${new Date(m.createdAt).toLocaleDateString('pt-MZ')}</span>
              </div>
            </div>

            <div class="d-flex gap-2 mt-3 pt-2 border-top">
              <button type="button" class="btn btn-outline-primary btn-sm w-100 fw-bold" onclick="descarregarMaterialEscolarArquivo('${m.id}', '${(m.nome_arquivo || m.titulo || 'material').replace(/'/g, "\\'")}')">
                <i class="bi bi-cloud-arrow-down-fill me-1"></i> Descarregar
              </button>
              ${!isAluno ? `
                <button class="btn btn-outline-danger btn-sm px-2" onclick="eliminarMaterialEscolar('${m.id}', '${m.titulo.replace(/'/g, "\\'")}')" title="Eliminar material">
                  <i class="bi bi-trash"></i>
                </button>
              ` : ''}
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function descarregarMaterialEscolarArquivo(id, nome) {
  downloadFicheiroBinario(`/api/v1/material-escolar/${id}/download`, nome);
}

async function modalCarregarMaterialEscolar() {
  const classePrevia = state.materialEscolar.classeAtiva !== 'TODAS' ? state.materialEscolar.classeAtiva : '10ª Classe';
  const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id;
  
  // Buscar disciplinas da escola ativa
  let optDisciplinas = '<option value="">(Geral / Todas as Disciplinas)</option>';
  try {
    const urlDisc = '/api/v1/disciplinas' + (escolaAtivaId ? `?escola_id=${encodeURIComponent(escolaAtivaId)}` : '');
    const resD = await apiFetch(urlDisc);
    if (resD.success && Array.isArray(resD.data)) {
      optDisciplinas += resD.data.map(d => `<option value="${d.id}">${d.nome} (${d.classe || ''})</option>`).join('');
    }
  } catch (_) {}

  const optClasses = CLASSES_SISTEMA_ORDEM.map(c => 
    `<option value="${c}" ${c === classePrevia ? 'selected' : ''}>${c}</option>`
  ).join('');

  abrirModal('Carregar / Importar Material Escolar Oficial', `
    <form id="formCarregarMaterial">
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Classe de Destino <span class="text-danger">*</span></label>
          <select id="matUploadClasse" class="form-select" required>
            ${optClasses}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Disciplina / Área</label>
          <select id="matUploadDisciplina" class="form-select">
            ${optDisciplinas}
          </select>
        </div>

        <div class="col-md-8">
          <label class="form-label small fw-semibold">Título do Material / Livro <span class="text-danger">*</span></label>
          <input type="text" id="matUploadTitulo" class="form-control" required placeholder="Ex: Livro do Aluno de Matemática - 10ª Classe">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Tipo de Material</label>
          <select id="matUploadTipo" class="form-select">
            <option value="MANUAL">Livro / Manual Escolar</option>
            <option value="FICHA">Ficha de Exercícios</option>
            <option value="GUIA">Guia do Professor / Apoio</option>
            <option value="APOSTILA">Apostila / Resumo</option>
            <option value="OUTRO">Outro Recurso</option>
          </select>
        </div>

        <div class="col-12">
          <label class="form-label small fw-semibold">Descrição ou Instruções aos Alunos (Opcional)</label>
          <textarea id="matUploadDescricao" class="form-control" rows="2" placeholder="Ex: Manual oficial adoptado pelo MINEDH. Exercícios dos capítulos 1 a 4."></textarea>
        </div>

        <!-- Abas de Opções: Ficheiro Local ou Link -->
        <div class="col-12">
          <ul class="nav nav-pills nav-fill mb-2" id="pills-tab-upload">
            <li class="nav-item">
              <button class="nav-link active py-1 small fw-semibold" id="tab-file-btn" type="button" onclick="alternarAbaUploadMaterial('arquivo')">
                <i class="bi bi-file-earmark-arrow-up me-1"></i> Carregar Ficheiro Local (Qualquer Extensão)
              </button>
            </li>
            <li class="nav-item">
              <button class="nav-link py-1 small fw-semibold" id="tab-link-btn" type="button" onclick="alternarAbaUploadMaterial('link')">
                <i class="bi bi-link-45deg me-1"></i> Importar via Link Web (Google Drive, MINEDH...)
              </button>
            </li>
          </ul>

          <div id="blocoUploadArquivo" class="border rounded p-3 bg-light text-center">
            <i class="bi bi-cloud-arrow-up text-primary display-6 d-block mb-2"></i>
            <label class="form-label fw-semibold small mb-1">Seleccione o ficheiro no computador</label>
            <input type="file" id="matUploadArquivo" class="form-control form-control-sm mb-2" accept="*">
            <small class="text-muted d-block">Formatos suportados: qualquer extensão de documento ou ficheiro (PDF, Word, Excel, PowerPoint, ZIP, RAR, imagens, etc.).</small>
          </div>

          <div id="blocoUploadLink" class="border rounded p-3 bg-light" style="display: none;">
            <label class="form-label small fw-semibold mb-1">Endereço Web / URL do Ficheiro ou Pasta</label>
            <input type="url" id="matUploadUrl" class="form-control form-control-sm" placeholder="https://drive.google.com/... ou https://minedh.gov.mz/...">
            <small class="text-muted d-block mt-1">Insira um link público directo para os alunos consultarem e descarregarem.</small>
          </div>
        </div>
      </div>

      <div class="mt-4 pt-2 border-top d-flex gap-2">
        <button type="button" class="btn btn-secondary w-50" onclick="fecharModal()">Cancelar</button>
        <button type="submit" class="btn btn-primary w-50 fw-bold" id="btnSalvarMaterial">
          <i class="bi bi-check-circle me-1"></i> Publicar Material
        </button>
      </div>
    </form>
  `);

  document.getElementById('formCarregarMaterial')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btnSalvarMaterial');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> A carregar...';

    try {
      const classe = document.getElementById('matUploadClasse').value;
      const disciplina_id = document.getElementById('matUploadDisciplina').value || null;
      const titulo = document.getElementById('matUploadTitulo').value;
      const tipo = document.getElementById('matUploadTipo').value;
      const descricao = document.getElementById('matUploadDescricao').value || null;

      const fileInput = document.getElementById('matUploadArquivo');
      const file = fileInput?.files?.[0];
      const linkUrl = document.getElementById('matUploadUrl')?.value || null;

      const payload = {
        classe,
        disciplina_id,
        titulo,
        tipo,
        descricao,
        escola_id: escolaAtivaId
      };

      if (file) {
        payload.nome_arquivo = file.name;
        payload.extensao = file.name.split('.').pop() || 'pdf';
        payload.tamanho_bytes = file.size;
        payload.tipo_mime = file.type || 'application/octet-stream';

        // Leitura em Base64
        const reader = new FileReader();
        const base64Promise = new Promise((resolve, reject) => {
          reader.onload = () => resolve(reader.result);
          reader.onerror = reject;
        });
        reader.readAsDataURL(file);
        payload.conteudo_base64 = await base64Promise;
      } else if (linkUrl) {
        payload.arquivo_url = linkUrl;
        payload.nome_arquivo = `${titulo}.link`;
        payload.extensao = 'link';
      } else {
        alert('Por favor, seleccione um ficheiro local ou indique um link web do material.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle me-1"></i> Publicar Material';
        return;
      }

      const res = await apiFetch('/api/v1/material-escolar', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (res.success) {
        alert('Material escolar carregado e publicado com sucesso!');
        fecharModal();
        selecionarClasseMaterial(classe);
      } else {
        alert(res.message || 'Erro ao publicar material escolar');
      }
    } catch (err) {
      alert(`Erro: ${err.message || 'Falha no upload do material'}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-check-circle me-1"></i> Publicar Material';
    }
  });
}

function alternarAbaUploadMaterial(tipo) {
  const btnFile = document.getElementById('tab-file-btn');
  const btnLink = document.getElementById('tab-link-btn');
  const blocoFile = document.getElementById('blocoUploadArquivo');
  const blocoLink = document.getElementById('blocoUploadLink');

  if (tipo === 'arquivo') {
    btnFile.classList.add('active');
    btnLink.classList.remove('active');
    blocoFile.style.display = 'block';
    blocoLink.style.display = 'none';
  } else {
    btnFile.classList.remove('active');
    btnLink.classList.add('active');
    blocoFile.style.display = 'none';
    blocoLink.style.display = 'block';
  }
}

async function eliminarMaterialEscolar(id, titulo) {
  if (!confirm(`Tem a certeza que deseja eliminar o material escolar "${titulo}"?`)) return;
  try {
    const res = await apiFetch(`/api/v1/material-escolar/${id}`, { method: 'DELETE' });
    if (res.success) {
      alert('Material removido com sucesso!');
      carregarPainelMaterialEscolar();
    } else {
      alert(res.message || 'Erro ao remover material');
    }
  } catch (err) {
    alert(`Erro ao eliminar material: ${err.message}`);
  }
}

