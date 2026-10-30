/**
 * SIGE - Calendário Escolar & Avaliações
 * Gestão de eventos lectivos, importação em lote por ficheiro (Excel/CSV) e documento oficial do calendário (PDF/Word).
 */

async function carregarEventosCalendario() {
  const tbody = document.getElementById('tabelaEventosCalendario');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar calendário...</td></tr>';
  
  const tri = document.getElementById('filtroTrimestreCalendario')?.value || '';
  const tipo = document.getElementById('filtroTipoCalendario')?.value || '';
  let url = '/api/v1/documentos/calendario/?';
  if (tri) url += `trimestre=${encodeURIComponent(tri)}&`;
  if (tipo) url += `tipo=${encodeURIComponent(tipo)}&`;
  
  // Escola activa para SUPERADMIN
  const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id;
  if (escolaAtivaId) url += `escola_id=${encodeURIComponent(escolaAtivaId)}&`;

  try {
    // Carregar em paralelo eventos e documento oficial
    carregarDocumentoOficialCalendario();

    const res = await apiFetch(url);
    const lista = res?.results || res?.data || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">
        <i class="bi bi-calendar-x display-6 d-block mb-2 opacity-50"></i>
        Nenhum evento registado no calendário lectivo.<br>
        <span class="small">Utilize <strong>"Propor Novo Evento"</strong> ou <strong>"Carregar Documento / Ficheiro"</strong> para adicionar eventos.</span>
      </td></tr>`;
      return;
    }
    
    const role = state.user?.role || '';
    const podeAprovar = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'].includes(role);
    let html = '';
    
    lista.forEach(ev => {
      const dt = ev.data_inicio + (ev.data_fim ? ' até ' + ev.data_fim : '');
      const badgeStatus = ev.status_aprovacao === 'APROVADO_DIRECTOR'
        ? '<span class="badge bg-success-subtle text-success border border-success-subtle"><i class="bi bi-check-circle me-1"></i>Aprovado</span>'
        : '<span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle"><i class="bi bi-hourglass-split me-1"></i>Proposto</span>';
      
      let btnAprovar = '';
      if (podeAprovar && ev.status_aprovacao !== 'APROVADO_DIRECTOR') {
        btnAprovar = `<button class="btn btn-sm btn-outline-success py-0 px-2 me-1" onclick="aprovarEventoCalendario('${ev.id}')" title="Aprovar oficialmente"><i class="bi bi-check2"></i> Aprovar</button>`;
      }

      let btnEliminar = '';
      if (podeAprovar) {
        btnEliminar = `<button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="eliminarEventoCalendario('${ev.id}', '${escapeHtml(ev.titulo)}') title="Remover"><i class="bi bi-trash"></i></button>`;
      }

      let anexoHtml = '<span class="text-muted small">-</span>';
      if (ev.tem_documento || ev.nome_documento) {
        const nomeAnexo = ev.nome_documento || 'Documento Anexo';
        anexoHtml = `<button type="button" class="btn btn-sm btn-outline-primary py-0 px-2 text-truncate" style="max-width: 160px;" onclick="descarregarAnexoEventoCalendario('${ev.id}', '${escapeHtml(nomeAnexo)}')" title="Descarregar anexo: ${escapeHtml(nomeAnexo)}">
          <i class="bi bi-paperclip me-1"></i>${escapeHtml(nomeAnexo)}
        </button>`;
      }

      html += `<tr>
        <td class="ps-3 fw-semibold text-nowrap">${escapeHtml(dt)}</td>
        <td>
          <strong class="text-dark">${escapeHtml(ev.titulo)}</strong>
          ${ev.descricao ? `<br><small class="text-muted">${escapeHtml(ev.descricao)}</small>` : ''}
        </td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(ev.tipo_display || ev.tipo)}</span></td>
        <td>${escapeHtml(ev.trimestre || 'Geral')}</td>
        <td>${anexoHtml}</td>
        <td>${badgeStatus}</td>
        <td class="text-end pe-3 text-nowrap">${btnAprovar}${btnEliminar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-danger">Erro ao carregar calendário.</td></tr>';
  }
}

async function carregarDocumentoOficialCalendario() {
  const container = document.getElementById('containerDocumentoOficialCalendario');
  if (!container) return;

  const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id;
  const param = escolaAtivaId ? `?escola_id=${encodeURIComponent(escolaAtivaId)}` : '';

  try {
    const res = await apiFetch(`/api/v1/documentos/calendario/documento_oficial/${param}`);
    const doc = res?.data;
    const role = state.user?.role || '';
    const podeGerir = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'].includes(role);

    if (doc && doc.id) {
      let tamStr = '';
      if (doc.tamanho_bytes > 0) {
        tamStr = doc.tamanho_bytes > 1024 * 1024
          ? (doc.tamanho_bytes / (1024 * 1024)).toFixed(1) + ' MB'
          : Math.round(doc.tamanho_bytes / 1024) + ' KB';
      }
      const dataFormatada = doc.created_at ? new Date(doc.created_at).toLocaleDateString('pt-MZ') : '';

      container.innerHTML = `
        <div class="card border-0 shadow-sm" style="border-left: 5px solid #0d6efd !important; background: #f8fafc;">
          <div class="card-body p-3 p-md-4">
            <div class="d-flex flex-column flex-md-row align-items-start align-items-md-center justify-content-between gap-3">
              <div class="d-flex align-items-start gap-3">
                <div class="bg-primary text-white p-3 rounded-3 shadow-sm d-none d-sm-block">
                  <i class="bi bi-file-earmark-pdf-fill fs-2"></i>
                </div>
                <div>
                  <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
                    <span class="badge bg-primary px-2 py-1"><i class="bi bi-shield-check me-1"></i> Documento Oficial em Vigor</span>
                    ${doc.ano_lectivo ? `<span class="badge bg-secondary-subtle text-secondary border">Ano Lectivo ${escapeHtml(doc.ano_lectivo)}</span>` : ''}
                  </div>
                  <h5 class="fw-bold mb-1 text-dark">${escapeHtml(doc.titulo || 'Calendário Escolar Oficial')}</h5>
                  <div class="small text-muted d-flex align-items-center gap-3 flex-wrap">
                    <span><i class="bi bi-file-earmark me-1"></i>${escapeHtml(doc.nome_arquivo || 'documento.pdf')} ${tamStr ? `(${tamStr})` : ''}</span>
                    ${dataFormatada ? `<span><i class="bi bi-calendar3 me-1"></i>Publicado: ${dataFormatada}</span>` : ''}
                    ${doc.publicado_por_nome ? `<span><i class="bi bi-person-check me-1"></i>Por: ${escapeHtml(doc.publicado_por_nome)}</span>` : ''}
                  </div>
                  ${doc.descricao ? `<p class="small text-secondary mb-0 mt-2">${escapeHtml(doc.descricao)}</p>` : ''}
                </div>
              </div>
              <div class="d-flex gap-2 flex-wrap">
                <button type="button" class="btn btn-primary btn-sm fw-bold shadow-sm" onclick="descarregarDocumentoOficialCalendario('${escapeHtml(doc.nome_arquivo || 'calendario_escolar.pdf')}')">
                  <i class="bi bi-cloud-arrow-down-fill me-1"></i> Descarregar Documento
                </button>
                ${podeGerir ? `
                  <button type="button" class="btn btn-outline-secondary btn-sm" onclick="modalCarregarDocumentoCalendario('oficial')" title="Substituir documento actual">
                    <i class="bi bi-arrow-repeat me-1"></i> Substituir
                  </button>
                  <button type="button" class="btn btn-outline-danger btn-sm" onclick="removerDocumentoOficialCalendario()" title="Remover documento oficial">
                    <i class="bi bi-trash"></i>
                  </button>
                ` : ''}
              </div>
            </div>
          </div>
        </div>
      `;
    } else {
      // Estado vazio informativo com botão rápido para carregar
      container.innerHTML = `
        <div class="card border-0 shadow-sm bg-light">
          <div class="card-body p-3 d-flex flex-column flex-md-row align-items-start align-items-md-center justify-content-between gap-2">
            <div class="d-flex align-items-center gap-2">
              <i class="bi bi-info-circle text-primary fs-4"></i>
              <div>
                <strong class="text-dark small d-block">Documento Oficial do Calendário Escolar (PDF / Word)</strong>
                <small class="text-muted">Pode carregar a circular oficial do MINEDH ou da Direcção para que todos os membros tenham acesso directo ao ficheiro.</small>
              </div>
            </div>
            ${podeGerir ? `
              <button class="btn btn-sm btn-outline-primary fw-semibold" onclick="modalCarregarDocumentoCalendario('oficial')">
                <i class="bi bi-upload me-1"></i> Carregar Documento Oficial
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }
  } catch (err) {
    console.warn('[CALENDARIO] Erro ao obter documento oficial:', err);
  }
}

function descarregarDocumentoOficialCalendario(nomeArquivo) {
  const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id;
  const param = escolaAtivaId ? `?escola_id=${encodeURIComponent(escolaAtivaId)}` : '';
  const url = `/api/v1/documentos/calendario/download_documento_oficial/${param}`;
  downloadFicheiroBinarioDirecto(url, nomeArquivo || 'calendario_escolar_oficial.pdf');
}

function descarregarAnexoEventoCalendario(id, nomeArquivo) {
  const url = `/api/v1/documentos/calendario/${id}/download_anexo/`;
  downloadFicheiroBinarioDirecto(url, nomeArquivo || 'anexo_evento.pdf');
}

async function downloadFicheiroBinarioDirecto(url, nomeArquivo) {
  try {
    mostrarToast('A iniciar transferência do documento...', 'info');
    const token = localStorage.getItem('token') || localStorage.getItem('sige_token');
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
      || state.tenant?.id
      || state.user?.escola_id;
    if (escolaAtivaId) headers['X-Escola-ID'] = escolaAtivaId;

    const resp = await fetch(url, { headers });
    if (!resp.ok) {
      const errJson = await resp.json().catch(() => ({}));
      throw new Error(errJson.message || `Erro ${resp.status} no download`);
    }
    const blob = await resp.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = nomeArquivo;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(blobUrl);
    mostrarToast('Documento descarregado com sucesso!', 'success');
  } catch (e) {
    mostrarToast('Falha ao descarregar documento: ' + e.message, 'danger');
  }
}

function descarregarModeloCalendarioCSV() {
  const url = '/api/v1/documentos/calendario/modelo_csv/';
  downloadFicheiroBinarioDirecto(url, 'modelo_calendario_escolar_sige.csv');
}

async function aprovarEventoCalendario(id) {
  try {
    const res = await apiFetch(`/api/v1/documentos/calendario/${id}/aprovar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Evento do calendário aprovado oficialmente com sucesso!', 'success');
      carregarEventosCalendario();
    }
  } catch (e) {
    mostrarToast('Falha ao aprovar evento: ' + e.message, 'danger');
  }
}

async function eliminarEventoCalendario(id, titulo) {
  if (!confirm(`Tem a certeza que deseja eliminar o evento "${titulo}"?`)) return;
  try {
    await apiFetch(`/api/v1/documentos/calendario/${id}/`, { method: 'DELETE' });
    mostrarToast('Evento eliminado com sucesso!', 'success');
    carregarEventosCalendario();
  } catch (e) {
    mostrarToast('Falha ao eliminar evento: ' + e.message, 'danger');
  }
}

async function removerDocumentoOficialCalendario() {
  if (!confirm('Deseja realmente remover o documento oficial do calendário escolar em vigor?')) return;
  try {
    const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
      || state.tenant?.id
      || state.user?.escola_id;
    const param = escolaAtivaId ? `?escola_id=${encodeURIComponent(escolaAtivaId)}` : '';
    const res = await apiFetch(`/api/v1/documentos/calendario/remover_documento_oficial/${param}`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Documento oficial removido com sucesso!', 'success');
      carregarDocumentoOficialCalendario();
    }
  } catch (e) {
    mostrarToast('Erro ao remover documento: ' + e.message, 'danger');
  }
}

// ==================== MODAL CARREGAR DOCUMENTO / FICHEIRO ====================
let _eventosPreviaImportacao = [];

function modalCarregarDocumentoCalendario(abaPadrao = 'ficheiro') {
  _eventosPreviaImportacao = [];
  const modalHtml = `
    <div class="modal fade" id="modalUploadDocCalendario" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-primary text-white">
            <h5 class="modal-title fw-bold"><i class="bi bi-file-earmark-arrow-up me-2"></i>Carregar Calendário por Documento / Ficheiro</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body p-4">
            <!-- Abas de Navegação -->
            <ul class="nav nav-pills nav-fill mb-4 bg-light p-1 rounded-3" id="tabCalendarioUpload">
              <li class="nav-item">
                <button class="nav-link py-2 fw-semibold ${abaPadrao !== 'oficial' ? 'active' : ''}" id="tab-lote-btn" type="button" onclick="alternarAbaUploadCalendario('lote')">
                  <i class="bi bi-file-earmark-spreadsheet me-1"></i> 1. Importar Eventos via Ficheiro (Excel / CSV)
                </button>
              </li>
              <li class="nav-item">
                <button class="nav-link py-2 fw-semibold ${abaPadrao === 'oficial' ? 'active' : ''}" id="tab-doc-btn" type="button" onclick="alternarAbaUploadCalendario('doc')">
                  <i class="bi bi-file-earmark-pdf me-1"></i> 2. Documento Oficial (PDF / Word / Circular)
                </button>
              </li>
            </ul>

            <!-- CONTEÚDO DA ABA 1: IMPORTAÇÃO DE EVENTOS VIA EXCEL/CSV -->
            <div id="painelUploadLote" style="${abaPadrao === 'oficial' ? 'display: none;' : 'display: block;'}">
              <div class="alert alert-info border-0 shadow-sm d-flex align-items-center justify-content-between flex-wrap gap-2 py-2 px-3 mb-3">
                <div class="small">
                  <i class="bi bi-info-circle-fill me-1"></i>
                  Carregue um ficheiro com a lista de datas, trimestres e provas para preencher o calendário automaticamente.
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary bg-white fw-semibold" onclick="descarregarModeloCalendarioCSV()">
                  <i class="bi bi-download me-1"></i> Descarregar Modelo CSV
                </button>
              </div>

              <div class="border rounded-3 p-4 bg-light text-center mb-3" id="dropzoneCalendario" style="border: 2px dashed #0d6efd !important; cursor: pointer;" onclick="document.getElementById('inputFicheiroCalendario').click()">
                <i class="bi bi-file-earmark-excel text-success display-5 d-block mb-2"></i>
                <h6 class="fw-bold mb-1">Clique para seleccionar ou arraste o ficheiro aqui</h6>
                <p class="text-muted small mb-2">Formatos suportados: Excel (.xlsx, .xls) ou Texto delimitado (.csv)</p>
                <input type="file" id="inputFicheiroCalendario" class="d-none" accept=".xlsx,.xls,.csv,.txt" onchange="processarFicheiroCalendarioSelecionado(this)">
                <span class="badge bg-secondary-subtle text-secondary" id="nomeFicheiroCalendarioSelecionado">Nenhum ficheiro seleccionado</span>
              </div>

              <!-- Pré-visualização -->
              <div id="blocoPreviaImportacao" style="display: none;">
                <div class="d-flex justify-content-between align-items-center mb-2">
                  <h6 class="fw-bold mb-0 text-dark"><i class="bi bi-eye me-1 text-primary"></i>Eventos Detectados (<span id="contagemEventosPrevia">0</span>)</h6>
                  <small class="text-muted">Valide as linhas antes de confirmar a importação</small>
                </div>
                <div class="table-responsive border rounded mb-3" style="max-height: 220px; overflow-y: auto;">
                  <table class="table table-sm table-striped align-middle mb-0" style="font-size: 0.85rem;">
                    <thead class="table-light sticky-top">
                      <tr>
                        <th>Data</th>
                        <th>Título</th>
                        <th>Categoria</th>
                        <th>Trimestre</th>
                        <th>Descrição</th>
                      </tr>
                    </thead>
                    <tbody id="tabelaPreviaEventosBody"></tbody>
                  </table>
                </div>
              </div>

              <div class="d-flex gap-2 justify-content-end mt-4">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-primary fw-bold" id="btnConfirmarImportacaoLote" onclick="confirmarImportacaoEventosLote()" disabled>
                  <i class="bi bi-check-circle-fill me-1"></i> Confirmar e Importar Eventos
                </button>
              </div>
            </div>

            <!-- CONTEÚDO DA ABA 2: DOCUMENTO OFICIAL DO CALENDÁRIO (PDF/DOCX) -->
            <div id="painelUploadDocOficial" style="${abaPadrao === 'oficial' ? 'display: block;' : 'display: none;'}">
              <div class="alert alert-secondary border-0 small py-2 px-3 mb-3">
                <i class="bi bi-shield-lock me-1 text-primary"></i>
                O documento oficial ficará arquivado e disponível para consulta e download imediato por todos os professores e membros autorizados da escola.
              </div>

              <div class="row g-3">
                <div class="col-md-8">
                  <label class="form-label small fw-semibold">Título do Documento <span class="text-danger">*</span></label>
                  <input type="text" id="inputDocOficialTitulo" class="form-control" value="Calendário Escolar Oficial" placeholder="Ex: Calendário do Ensino Geral 2026 - Diploma Ministerial">
                </div>
                <div class="col-md-4">
                  <label class="form-label small fw-semibold">Ano Lectivo</label>
                  <input type="text" id="inputDocOficialAno" class="form-control" value="2026" placeholder="2026">
                </div>
                <div class="col-12">
                  <label class="form-label small fw-semibold">Ficheiro Oficial (PDF, DOCX, Imagem) <span class="text-danger">*</span></label>
                  <input type="file" id="inputDocOficialFicheiro" class="form-control" accept=".pdf,.doc,.docx,.png,.jpg,.jpeg">
                  <small class="text-muted">Envie o documento digitalizado ou em formato PDF/DOCX emitido pelo MINEDH / DPE.</small>
                </div>
                <div class="col-12">
                  <label class="form-label small fw-semibold">Descrição / Observações / Número da Circular (Opcional)</label>
                  <textarea id="inputDocOficialDesc" class="form-control" rows="2" placeholder="Ex: Circular nº 03/MINEDH/2026 referente aos períodos lectivos e exames nacionais."></textarea>
                </div>
              </div>

              <div class="d-flex gap-2 justify-content-end mt-4">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-primary fw-bold" id="btnSalvarDocOficial" onclick="gravarDocumentoOficialCalendario()">
                  <i class="bi bi-cloud-arrow-up-fill me-1"></i> Publicar Documento Oficial
                </button>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  `;

  const el = document.getElementById('modalUploadDocCalendario');
  if (el) el.remove();
  document.body.insertAdjacentHTML('beforeend', modalHtml);
  const modal = new bootstrap.Modal(document.getElementById('modalUploadDocCalendario'));
  modal.show();
}

function alternarAbaUploadCalendario(aba) {
  const painelLote = document.getElementById('painelUploadLote');
  const painelDoc = document.getElementById('painelUploadDocOficial');
  const btnLote = document.getElementById('tab-lote-btn');
  const btnDoc = document.getElementById('tab-doc-btn');
  
  if (aba === 'lote') {
    painelLote.style.display = 'block';
    painelDoc.style.display = 'none';
    btnLote.classList.add('active');
    btnDoc.classList.remove('active');
  } else {
    painelLote.style.display = 'none';
    painelDoc.style.display = 'block';
    btnLote.classList.remove('active');
    btnDoc.classList.add('active');
  }
}

// Processamento do ficheiro de calendário na Aba 1
let _arquivoCalendarioSelecionado = null;

async function processarFicheiroCalendarioSelecionado(input) {
  const file = input?.files?.[0];
  if (!file) return;
  _arquivoCalendarioSelecionado = file;
  
  const label = document.getElementById('nomeFicheiroCalendarioSelecionado');
  if (label) {
    label.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
    label.className = 'badge bg-success-subtle text-success border border-success-subtle';
  }

  const btnConfirmar = document.getElementById('btnConfirmarImportacaoLote');
  const blocoPrevia = document.getElementById('blocoPreviaImportacao');
  const tbodyPrevia = document.getElementById('tabelaPreviaEventosBody');
  const contagemEl = document.getElementById('contagemEventosPrevia');

  // Leitura de CSV no browser para pré-visualização imediata
  const ext = file.name.split('.').pop().toLowerCase();
  if (ext === 'csv' || ext === 'txt') {
    try {
      const reader = new FileReader();
      reader.onload = function(e) {
        const texto = e.target.result;
        const linhas = parseCsvLinhasCalendario(texto);
        _eventosPreviaImportacao = linhas;
        if (linhas.length > 0) {
          contagemEl.textContent = linhas.length;
          tbodyPrevia.innerHTML = linhas.slice(0, 50).map(l => `
            <tr>
              <td class="text-nowrap fw-semibold">${escapeHtml(l.data_inicio + (l.data_fim ? ' a ' + l.data_fim : ''))}</td>
              <td class="fw-semibold">${escapeHtml(l.titulo)}</td>
              <td><span class="badge bg-light text-dark border">${escapeHtml(l.tipo)}</span></td>
              <td>${escapeHtml(l.trimestre)}</td>
              <td class="small text-muted">${escapeHtml(l.descricao || '')}</td>
            </tr>
          `).join('');
          blocoPrevia.style.display = 'block';
          btnConfirmar.disabled = false;
        } else {
          blocoPrevia.style.display = 'none';
          btnConfirmar.disabled = false; // Deixa o backend tentar
        }
      };
      reader.readAsText(file);
    } catch (_) {
      btnConfirmar.disabled = false;
    }
  } else {
    // Para .xlsx, o backend processa directamente
    blocoPrevia.style.display = 'block';
    tbodyPrevia.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-primary"><i class="bi bi-file-earmark-excel me-2"></i>Folha Excel pronta para importação no servidor.</td></tr>`;
    contagemEl.textContent = 'A processar no envio';
    btnConfirmar.disabled = false;
  }
}

function parseCsvLinhasCalendario(texto) {
  const resultado = [];
  const linhas = texto.split(/\r?\n/).filter(l => l.trim().length > 0);
  if (linhas.length <= 1) return resultado;

  const primeira = linhas[0];
  const delim = primeira.includes(';') ? ';' : (primeira.includes('\t') ? '\t' : ',');
  const cabecalho = linhas[0].split(delim).map(c => c.replace(/["']/g, '').trim().toLowerCase());

  for (let i = 1; i < linhas.length; i++) {
    const colunas = linhas[i].split(delim).map(c => c.replace(/^["']|["']$/g, '').trim());
    if (colunas.length === 0 || !colunas.some(c => c.length > 0)) continue;

    let dtInicio = '', dtFim = '', titulo = '', tipo = 'AVALIACAO_TESTE', trimestre = 'GERAL', desc = '';
    cabecalho.forEach((h, idx) => {
      const v = colunas[idx] || '';
      if (!v) return;
      if (h.includes('inicio') || h.includes('abertura') || h === 'data') dtInicio = v;
      else if (h.includes('fim') || h.includes('encerramento') || h.includes('ate')) dtFim = v;
      else if (h.includes('titulo') || h.includes('evento') || h.includes('nome')) titulo = v;
      else if (h.includes('tipo') || h.includes('categoria')) tipo = v;
      else if (h.includes('trimestre') || h.includes('periodo')) trimestre = v;
      else if (h.includes('desc') || h.includes('obs')) desc = v;
    });

    // Fallback se não detectou por header
    if (!titulo && colunas.length >= 2) {
      dtInicio = colunas[0];
      titulo = colunas[1];
      if (colunas.length >= 3) dtFim = colunas[2];
    }

    if (titulo) {
      resultado.push({
        data_inicio: dtInicio,
        data_fim: dtFim,
        titulo: titulo,
        tipo: tipo,
        trimestre: trimestre,
        descricao: desc
      });
    }
  }
  return resultado;
}

async function confirmarImportacaoEventosLote() {
  if (!_arquivoCalendarioSelecionado && _eventosPreviaImportacao.length === 0) {
    mostrarToast('Seleccione um ficheiro para importar.', 'warning');
    return;
  }

  const btn = document.getElementById('btnConfirmarImportacaoLote');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> A importar eventos...';

  try {
    const payload = {};
    if (_eventosPreviaImportacao.length > 0) {
      payload.eventos = _eventosPreviaImportacao;
    } else if (_arquivoCalendarioSelecionado) {
      // Ler em base64
      const file = _arquivoCalendarioSelecionado;
      const b64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      payload.conteudo_base64 = b64;
      payload.nome_arquivo = file.name;
    }

    const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
      || state.tenant?.id
      || state.user?.escola_id;
    if (escolaAtivaId) payload.escola_id = escolaAtivaId;

    const res = await apiFetch('/api/v1/documentos/calendario/importar_ficheiro/', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res && res.success !== false) {
      mostrarToast(res.message || 'Eventos importados com sucesso!', 'success');
      bootstrap.Modal.getInstance(document.getElementById('modalUploadDocCalendario'))?.hide();
      carregarEventosCalendario();
    } else {
      mostrarToast(res.message || 'Erro ao importar ficheiro.', 'danger');
    }
  } catch (e) {
    mostrarToast('Falha na importação: ' + e.message, 'danger');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Confirmar e Importar Eventos';
  }
}

async function gravarDocumentoOficialCalendario() {
  const titulo = document.getElementById('inputDocOficialTitulo')?.value;
  const ano_lectivo = document.getElementById('inputDocOficialAno')?.value || '2026';
  const descricao = document.getElementById('inputDocOficialDesc')?.value || '';
  const fileInput = document.getElementById('inputDocOficialFicheiro');
  const file = fileInput?.files?.[0];

  if (!titulo) {
    mostrarToast('Indique o título do documento.', 'warning');
    return;
  }
  if (!file) {
    mostrarToast('Seleccione o ficheiro oficial (PDF, DOCX, imagem) para carregar.', 'warning');
    return;
  }

  const btn = document.getElementById('btnSalvarDocOficial');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> A carregar documento...';

  try {
    const b64 = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

    const payload = {
      titulo,
      ano_lectivo,
      descricao,
      nome_arquivo: file.name,
      extensao: file.name.split('.').pop().toLowerCase(),
      tamanho_bytes: file.size,
      tipo_mime: file.type || 'application/pdf',
      conteudo_base64: b64
    };

    const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
      || state.tenant?.id
      || state.user?.escola_id;
    if (escolaAtivaId) payload.escola_id = escolaAtivaId;

    const res = await apiFetch('/api/v1/documentos/calendario/carregar_documento_oficial/', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res && res.success !== false) {
      mostrarToast('Documento oficial do calendário publicado com sucesso!', 'success');
      bootstrap.Modal.getInstance(document.getElementById('modalUploadDocCalendario'))?.hide();
      carregarDocumentoOficialCalendario();
    } else {
      mostrarToast(res.message || 'Erro ao carregar documento oficial.', 'danger');
    }
  } catch (e) {
    mostrarToast('Falha no upload do documento: ' + e.message, 'danger');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-cloud-arrow-up-fill me-1"></i> Publicar Documento Oficial';
  }
}

// ==================== MODAL PROPOR NOVO EVENTO INDIVIDUAL ====================
function modalNovoEventoCalendario() {
  const modalHtml = `
    <div class="modal fade" id="modalAddCalendario" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-primary text-white">
            <h5 class="modal-title fw-bold"><i class="bi bi-calendar-plus me-2"></i>Propor Evento no Calendário</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body p-4">
            <div class="mb-3">
              <label class="form-label fw-semibold">Título do Evento <span class="text-danger">*</span></label>
              <input type="text" id="calTitulo" class="form-control" placeholder="Ex: Provas Trimestrais de ACS">
            </div>
            <div class="row g-2 mb-3">
              <div class="col-6">
                <label class="form-label fw-semibold">Tipo</label>
                <select id="calTipo" class="form-select">
                  <option value="AVALIACAO_TESTE">Avaliação / Teste</option>
                  <option value="EXAME">Exame</option>
                  <option value="CONSELHO_TURMA">Conselho de Turma</option>
                  <option value="FERIADO_PAUSA">Feriado / Pausa</option>
                  <option value="REUNIAO_ENCARREGADOS">Reunião de Encarregados</option>
                  <option value="EVENTO_ESCOLAR">Evento Cultural</option>
                </select>
              </div>
              <div class="col-6">
                <label class="form-label fw-semibold">Trimestre</label>
                <select id="calTrimestre" class="form-select">
                  <option value="1_TRIMESTRE">1º Trimestre</option>
                  <option value="2_TRIMESTRE">2º Trimestre</option>
                  <option value="3_TRIMESTRE">3º Trimestre</option>
                  <option value="GERAL">Geral</option>
                </select>
              </div>
            </div>
            <div class="row g-2 mb-3">
              <div class="col-6">
                <label class="form-label fw-semibold">Data de Início <span class="text-danger">*</span></label>
                <input type="date" id="calDataInicio" class="form-control">
              </div>
              <div class="col-6">
                <label class="form-label fw-semibold">Data de Fim (Opcional)</label>
                <input type="date" id="calDataFim" class="form-control">
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label fw-semibold">Descrição / Orientações</label>
              <textarea id="calDescricao" class="form-control" rows="2" placeholder="Notas explicativas, orientações para professores ou alunos..."></textarea>
            </div>
            <div class="mb-3">
              <label class="form-label fw-semibold small text-muted">
                <i class="bi bi-paperclip me-1"></i>Anexar Documento / Ficheiro ao Evento (Opcional - PDF, Circular, Guia)
              </label>
              <input type="file" id="calAnexoDocumento" class="form-control form-control-sm" accept=".pdf,.doc,.docx,.png,.jpg,.jpeg">
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
            <button type="button" class="btn btn-primary fw-bold" id="btnSalvarEventoCal" onclick="salvarEventoCalendario()">Salvar Evento</button>
          </div>
        </div>
      </div>
    </div>
  `;
  const el = document.getElementById('modalAddCalendario');
  if (el) el.remove();
  document.body.insertAdjacentHTML('beforeend', modalHtml);
  const modal = new bootstrap.Modal(document.getElementById('modalAddCalendario'));
  modal.show();
}

async function salvarEventoCalendario() {
  const titulo = document.getElementById('calTitulo')?.value;
  const tipo = document.getElementById('calTipo')?.value;
  const trimestre = document.getElementById('calTrimestre')?.value;
  const data_inicio = document.getElementById('calDataInicio')?.value;
  const data_fim = document.getElementById('calDataFim')?.value || null;
  const descricao = document.getElementById('calDescricao')?.value || '';
  const fileInput = document.getElementById('calAnexoDocumento');
  const file = fileInput?.files?.[0];

  if (!titulo || !data_inicio) {
    mostrarToast('Preencha o título e a data de início.', 'warning');
    return;
  }

  const btn = document.getElementById('btnSalvarEventoCal');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> A guardar...';
  }

  try {
    const payload = { titulo, tipo, trimestre, data_inicio, data_fim, descricao };
    
    if (file) {
      payload.nome_documento = file.name;
      payload.documento_tipo = file.type || 'application/pdf';
      payload.documento_tamanho = file.size;
      const b64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      payload.documento_base64 = b64;
    }

    const escolaAtivaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
      || state.tenant?.id
      || state.user?.escola_id;
    if (escolaAtivaId) payload.escola_id = escolaAtivaId;

    const res = await apiFetch('/api/v1/documentos/calendario/', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    if (res && res.success !== false) {
      mostrarToast('Evento adicionado ao calendário!', 'success');
      bootstrap.Modal.getInstance(document.getElementById('modalAddCalendario'))?.hide();
      carregarEventosCalendario();
    }
  } catch (e) {
    mostrarToast('Erro ao salvar evento: ' + e.message, 'danger');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = 'Salvar Evento';
    }
  }
}

if (typeof carregarEventosCalendario === 'function') {
  carregarEventosCalendario();
}
