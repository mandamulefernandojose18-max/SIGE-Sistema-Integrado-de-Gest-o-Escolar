// =====================================================================
// SIGE - MÓDULO DE BLINDAGEM ANTI-IA DE PROVAS E AVALIAÇÕES (JS)
// Codificação por QR Code e Código de Barras com Bloqueio Temporal
// =====================================================================

window.state = window.state || {};
window.state.provaAntiIaAtual = null;
window.state.provasAntiIaHistorico = [];

/**
 * Inicialização oficial do módulo quando aberto pelo roteador do SIGE
 */
function inicializarModulo_provas_anti_ia() {
  const dataInput = document.getElementById('aiProvaDataBloqueio');
  if (dataInput && !dataInput.value) {
    const hoje = new Date();
    hoje.setDate(hoje.getDate() + 3);
    const yyyy = hoje.getFullYear();
    const mm = String(hoje.getMonth() + 1).padStart(2, '0');
    const dd = String(hoje.getDate()).padStart(2, '0');
    dataInput.value = `${yyyy}-${mm}-${dd}`;
  }

  // Preencher construtor com uma questão inicial se vazio
  const listaBuilder = document.getElementById('listaQuestoesBuilder');
  if (listaBuilder && listaBuilder.children.length === 0) {
    adicionarQuestaoBuilder();
  }

  iniciarInterfaceZipProvasAntiIa();
  atualizarResumoDataProvaAntiIa();
  carregarHistoricoProvasAntiIa();
}

/**
 * Alterna entre abas operacionais
 */
function alternarAbaProvasAntiIa(tabId) {
  const triggerEl = document.querySelector(`button[data-bs-target="#${tabId}"]`);
  if (triggerEl && typeof bootstrap !== 'undefined') {
    const tab = new bootstrap.Tab(triggerEl);
    tab.show();
  }
}

/**
 * Preenche o formulário com uma avaliação curricular autêntica de Moçambique
 */
function preencherExemploProvaAntiIa() {
  document.getElementById('aiProvaTitulo').value = 'Avaliação Contínua e Sistemática de Matemática (ACS 1)';
  document.getElementById('aiProvaDisciplina').value = 'Matemática';
  document.getElementById('aiProvaClasse').value = '10ª Classe';
  document.getElementById('aiProvaTrimestre').value = '1º Trimestre';
  document.getElementById('aiProvaTipo').value = 'ACS 1';
  document.getElementById('aiProvaDuracao').value = '90';

  const textoExemplo = 
`1. (4.0 val) Resolva a equação quadrática: 2x² - 8x + 6 = 0, indicando as suas raízes no conjunto ℝ.

2. (4.0 val) Determine as coordenadas do vértice e o eixo de simetria da parábola f(x) = x² - 4x + 3.

3. (4.0 val) Calcule o valor do discriminante (Δ) da equação x² + 6x + 9 = 0 e classifique a natureza das suas raízes.

4. (4.0 val) Um projéctil é lançado verticalmente segundo a equação horária h(t) = -5t² + 20t (h em metros, t em segundos). Determine a altura máxima atingida pelo projéctil.

5. (4.0 val) Resolva a inequação quadrática x² - 9 < 0 e represente o conjunto solução na recta real.`;

  document.getElementById('aiProvaTextoCompleto').value = textoExemplo;

  // Ativar a aba de texto
  const tabTexto = document.getElementById('pills-texto-tab');
  if (tabTexto && typeof bootstrap !== 'undefined') {
    new bootstrap.Tab(tabTexto).show();
  }

  if (typeof mostrarNotificacao === 'function') {
    mostrarNotificacao('Exemplo curricular da 10ª classe carregado com sucesso!', 'info');
  }
}

/**
 * Adiciona uma questão no construtor dinâmico
 */
function adicionarQuestaoBuilder() {
  const container = document.getElementById('listaQuestoesBuilder');
  if (!container) return;

  const num = container.children.length + 1;
  const div = document.createElement('div');
  div.className = 'card p-3 border item-questao-builder';
  div.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-2">
      <span class="fw-bold small text-primary"><i class="bi bi-question-circle me-1"></i>Pergunta nº ${num}</span>
      <div class="d-flex align-items-center gap-2">
        <label class="very-small text-muted mb-0">Cotação (val):</label>
        <input type="number" step="0.5" class="form-control form-control-sm text-center q-cotacao" style="width: 75px;" value="4.0">
        <button type="button" class="btn btn-outline-danger btn-sm py-0 px-2" onclick="removerQuestaoBuilder(this)"><i class="bi bi-trash"></i></button>
      </div>
    </div>
    <textarea class="form-control form-control-sm q-enunciado" rows="2" placeholder="Digite o enunciado desta pergunta..."></textarea>
  `;
  container.appendChild(div);
}

function removerQuestaoBuilder(btn) {
  const item = btn.closest('.item-questao-builder');
  if (item) item.remove();
}

/**
 * Trata seleção de arquivo
 */
function aoSelecionarArquivoProva(input) {
  const infoEl = document.getElementById('aiArquivoSelecionadoInfo');
  if (input.files && input.files[0]) {
    const file = input.files[0];
    if (infoEl) {
      infoEl.textContent = `Ficheiro selecionado: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      infoEl.style.display = 'block';
    }
    abrirEditorMarcasProvaAntiIa(file);
  }
}

// ---------------------------------------------------------------------
// Editor de posição dos códigos: pré-visualização real da página selada (PDF).
// `aiMarcas` = null usa as posições predefinidas; ao clicar na página passa a lista editável.
// ---------------------------------------------------------------------
var AI_MARCAS_PREDEFINIDAS = () => ([
  { tipo: 'barras', paginas: 'todas', x: 0.5, y: 0.955, tamanho_mm: 55 },
  { tipo: 'qr', paginas: 'todas', x: 0.92, y: 0.1, tamanho_mm: 20 },
]);
window.state.aiMarcas = null;
var aiPreviaPagina = 0;
var aiPreviaTotal = 1;
var aiPreviaTimer = null;

function aiOpcoesSelosEmFormulario(formData) {
  [['aiSeloAvisoFoto', 'selo_aviso_foto'], ['aiSeloAvisoIa', 'selo_aviso_ia'],
   ['aiSeloAvisoPergunta', 'selo_aviso_pergunta'], ['aiSeloQrPergunta', 'selo_qr_pergunta'],
   ['aiSeloQrMarcaAgua', 'selo_qr_marca_agua'], ['aiSeloBarras', 'selo_barras']].forEach(([id, campo]) => {
    const el = document.getElementById(id);
    if (el) formData.append(campo, el.checked ? '1' : '0');
  });
  const mensagem = (document.getElementById('aiSeloMensagem')?.value || '').trim();
  if (mensagem) formData.append('selo_mensagem_ia', mensagem);
  if (window.state.aiMarcas) formData.append('selo_marcas', JSON.stringify(window.state.aiMarcas));
}

function aiDataTextoProva() {
  const d = document.getElementById('aiProvaDataBloqueio')?.value;
  const h = document.getElementById('aiProvaHoraBloqueio')?.value || '00:00';
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d || '');
  return m ? `${m[3]}/${m[2]}/${m[1]} às ${h}` : 'DD/MM/AAAA às HH:MM';
}

function abrirEditorMarcasProvaAntiIa(file) {
  const editor = document.getElementById('aiEditorMarcas');
  if (!editor) return;
  const ehPdf = /\.pdf$/i.test(file.name);
  editor.hidden = !ehPdf;
  if (!ehPdf) return;
  aiPreviaPagina = 0;
  window.state.aiMarcas = null;
  atualizarListaMarcasProvaAntiIa();
  atualizarPreviaSelosProvaAntiIa();
  if (editor.dataset.pronto === '1') return;
  editor.dataset.pronto = '1';
  const img = document.getElementById('aiPrevia');
  img.addEventListener('click', (e) => {
    const r = img.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const tipo = document.getElementById('aiMarcaTipo').value;
    const faixa = tipo === 'qr' ? [15, 60] : [30, 90];
    let mm = parseFloat(document.getElementById('aiMarcaTamanho').value) || faixa[0];
    mm = Math.min(Math.max(mm, faixa[0]), faixa[1]);
    const marcas = window.state.aiMarcas || AI_MARCAS_PREDEFINIDAS();
    if (marcas.length >= 20) { document.getElementById('aiPreviaEstado').textContent = 'No máximo 20 marcas por prova.'; return; }
    marcas.push({
      tipo, paginas: document.getElementById('aiMarcaPaginas').value, tamanho_mm: mm,
      x: Math.round(((e.clientX - r.left) / r.width) * 1000) / 1000,
      y: Math.round(((e.clientY - r.top) / r.height) * 1000) / 1000,
    });
    window.state.aiMarcas = marcas;
    atualizarListaMarcasProvaAntiIa();
    atualizarPreviaSelosProvaAntiIa();
  });
  document.getElementById('aiMarcaTipo').addEventListener('change', (e) => {
    document.getElementById('aiMarcaTamanho').value = e.target.value === 'qr' ? 20 : 55;
  });
  document.getElementById('aiMarcasPrever').addEventListener('click', atualizarPreviaSelosProvaAntiIa);
  document.getElementById('aiMarcasRepor').addEventListener('click', () => {
    window.state.aiMarcas = null;
    atualizarListaMarcasProvaAntiIa();
    atualizarPreviaSelosProvaAntiIa();
  });
  document.getElementById('aiPreviaAnt').addEventListener('click', () => { aiPreviaPagina = Math.max(aiPreviaPagina - 1, 0); atualizarPreviaSelosProvaAntiIa(); });
  document.getElementById('aiPreviaSeg').addEventListener('click', () => { aiPreviaPagina = Math.min(aiPreviaPagina + 1, aiPreviaTotal - 1); atualizarPreviaSelosProvaAntiIa(); });
}

function atualizarListaMarcasProvaAntiIa() {
  const ul = document.getElementById('aiMarcasLista');
  if (!ul) return;
  const marcas = window.state.aiMarcas;
  if (!marcas) { ul.innerHTML = '<li class="text-muted">Posições predefinidas (código de barras no rodapé e QR no canto). Clica na página para as personalizar.</li>'; return; }
  ul.innerHTML = marcas.map((m, i) => `
    <li class="d-flex align-items-center gap-2 py-1 border-bottom">
      <span class="badge bg-light text-dark border">${m.tipo === 'qr' ? 'QR' : 'Barras'}</span>
      <span>${m.tamanho_mm} mm · ${m.paginas === 'todas' ? 'todas as páginas' : m.paginas === 'primeira' ? 'primeira página' : 'última página'} · (${Math.round(m.x * 100)}%, ${Math.round(m.y * 100)}%)</span>
      <button type="button" class="btn btn-sm btn-outline-danger ms-auto py-0" data-ai-remover="${i}" aria-label="Remover marca"><i class="bi bi-x-lg"></i></button>
    </li>`).join('');
  ul.querySelectorAll('[data-ai-remover]').forEach(b => b.addEventListener('click', () => {
    marcas.splice(+b.dataset.aiRemover, 1);
    atualizarListaMarcasProvaAntiIa();
    atualizarPreviaSelosProvaAntiIa();
  }));
}

function atualizarPreviaSelosProvaAntiIa() {
  clearTimeout(aiPreviaTimer);
  aiPreviaTimer = setTimeout(async () => {
    const input = document.getElementById('aiProvaInputArquivo');
    const file = input && input.files && input.files[0];
    const img = document.getElementById('aiPrevia');
    const estado = document.getElementById('aiPreviaEstado');
    if (!file || !/\.pdf$/i.test(file.name) || !img) return;
    estado.textContent = 'A gerar pré-visualização…';
    const fd = new FormData();
    fd.append('ficheiro', file);
    fd.append('pagina', String(aiPreviaPagina));
    fd.append('data_texto', aiDataTextoProva());
    aiOpcoesSelosEmFormulario(fd);
    try {
      const res = await fetch('/api/v1/ferramentas/provas-anti-ia/previa-selos/', {
        method: 'POST', headers: { 'Authorization': obterTokenSige() ? `Bearer ${obterTokenSige()}` : '' }, body: fd });
      const json = await res.json();
      if (!res.ok || !json.success) { estado.textContent = json.message || 'Não foi possível gerar a pré-visualização.'; return; }
      aiPreviaTotal = json.paginas;
      aiPreviaPagina = json.pagina;
      img.src = json.imagem;
      img.hidden = false;
      document.getElementById('aiPreviaPaginaInfo').textContent = `Página ${json.pagina + 1} de ${json.paginas}`;
      estado.textContent = '';
    } catch (_) {
      estado.textContent = 'Sem ligação ao servidor.';
    }
  }, 250);
}

// ---------------------------------------------------------------------
// Página da prova: estado do embargo com progresso, leituras, cópias e gestão.
// ---------------------------------------------------------------------
var aiPaginaTimer = null;

async function abrirPaginaProvaAntiIa(provaId) {
  try {
    const res = await fetch(`/api/v1/ferramentas/provas-anti-ia/${encodeURIComponent(provaId)}/pagina/`, {
      headers: { 'Authorization': obterTokenSige() ? `Bearer ${obterTokenSige()}` : '' } });
    const json = await res.json();
    if (!res.ok || !json.success) return;
    renderizarPaginaProvaAntiIa(json.data);
    alternarAbaProvasAntiIa('tab-prova-ia');
  } catch (_) { /* sem rede: o painel mantém-se */ }
}

function renderizarPaginaProvaAntiIa(p) {
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set('aiProvaTituloPag', p.titulo);
  set('aiProvaMetaPag', `${p.disciplina} · ${p.classe} · ${p.trimestre} · ${p.tipo_avaliacao} · ${p.codigo_autenticidade}`);
  set('aiPagCopias', p.total_copias);
  set('aiPagLeituras', p.total_acessos);
  set('aiPagTentativas', p.tentativas_bloqueadas);
  set('aiPagFormato', p.formato);
  set('aiProvaPrazoPag', `Protegida até ${formatarDataHora(p.data_bloqueio_ia)} (hora de Maputo)`);

  const estado = document.getElementById('aiProvaEstadoPag');
  const barra = document.getElementById('aiProvaProgressoPag');
  const relogio = document.getElementById('aiProvaRelogioPag');
  if (aiPaginaTimer) { clearInterval(aiPaginaTimer); aiPaginaTimer = null; }
  const ini = new Date(p.criada_em).getTime(), fim = new Date(p.data_bloqueio_ia).getTime();
  const pad = (n) => String(n).padStart(2, '0');
  const tick = () => {
    const agora = Date.now();
    const livre = agora >= fim;
    estado.className = `badge ${livre ? 'bg-success' : 'bg-danger'}`;
    estado.innerHTML = livre ? '<i class="bi bi-unlock-fill me-1"></i>Libertada' : '<i class="bi bi-lock-fill me-1"></i>Sob embargo';
    barra.className = `progress-bar ${livre ? 'bg-success' : 'bg-danger'}`;
    barra.style.width = `${fim > ini ? Math.min(Math.max((agora - ini) / (fim - ini), 0), 1) * 100 : 100}%`;
    const falta = Math.max(Math.floor((fim - agora) / 1000), 0);
    relogio.textContent = livre ? 'O período de proteção terminou.' :
      `Faltam ${Math.floor(falta / 86400)}d ${pad(Math.floor(falta % 86400 / 3600))}:${pad(Math.floor(falta % 3600 / 60))}:${pad(falta % 60)}`;
    if (livre && aiPaginaTimer) { clearInterval(aiPaginaTimer); aiPaginaTimer = null; }
  };
  tick();
  aiPaginaTimer = setInterval(tick, 1000);

  const nomeId = aiEscapar(p.id), nomeCod = aiEscapar(p.codigo_autenticidade);
  document.getElementById('aiProvaAccoesPag').innerHTML = `
    <button type="button" class="btn btn-danger btn-sm" onclick="descarregarFicheiroAutenticado('/api/v1/ferramentas/provas-anti-ia/${nomeId}/descarregar-pdf/', 'Prova_${nomeCod}')"><i class="bi bi-download me-1"></i>Descarregar prova</button>
    <button type="button" class="btn btn-outline-dark btn-sm" onclick="abrirCopiasPorAluno('${nomeId}')"><i class="bi bi-people me-1"></i>Cópias por aluno</button>
    <button type="button" class="btn btn-outline-secondary btn-sm text-danger" onclick="eliminarProvaHistorico('${nomeId}').then(() => alternarAbaProvasAntiIa('tab-painel-ia'))"><i class="bi bi-trash me-1"></i>Eliminar</button>`;

  const acessos = document.getElementById('aiPagAcessos');
  acessos.innerHTML = p.acessos.length ? p.acessos.map(a => `
    <tr><td class="small">${aiEscapar(formatarDataHora(a.quando))}</td><td>${a.questao || '–'}</td>
    <td class="small">${aiEscapar(a.sistema)}</td><td>${a.bloqueado ? '<span class="badge bg-danger">Bloqueado</span>' : '<span class="badge bg-success">Libertado</span>'}</td></tr>`).join('')
    : '<tr><td colspan="4" class="text-center text-muted py-3">Ainda ninguém leu os códigos desta prova.</td></tr>';
  const copias = document.getElementById('aiPagCopiasLista');
  copias.innerHTML = p.copias.length ? p.copias.map(c => `
    <tr><td class="font-monospace small">${aiEscapar(c.codigo)}</td><td>${aiEscapar(c.aluno)}</td><td class="small">${aiEscapar(c.turma)}</td></tr>`).join('')
    : '<tr><td colspan="3" class="text-center text-muted py-3">Ainda não foram geradas cópias numeradas.</td></tr>';
}

/**
 * Submissão e Codificação da Prova
 */
async function aoSubmeterCodificacaoProva(event) {
  event.preventDefault();

  const btnSubmit = document.getElementById('btnCodificarProvaSubmit');
  const originalHtml = btnSubmit.innerHTML;
  btnSubmit.disabled = true;
  btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Codificando Questões e Bloqueando IA...';

  try {
    const titulo = document.getElementById('aiProvaTitulo').value.trim();
    const disciplina = document.getElementById('aiProvaDisciplina').value.trim();
    const classe = document.getElementById('aiProvaClasse').value;
    const trimestre = document.getElementById('aiProvaTrimestre').value;
    const tipo = document.getElementById('aiProvaTipo').value;
    const duracao = parseInt(document.getElementById('aiProvaDuracao').value) || 90;
    const dataBloq = document.getElementById('aiProvaDataBloqueio').value;
    const horaBloq = document.getElementById('aiProvaHoraBloqueio').value || '12:00';

    const dataBloqueioCompleta = `${dataBloq}T${horaBloq}:00`;

    // Verificar se há ficheiro selecionado
    const inputFile = document.getElementById('aiProvaInputArquivo');
    const tabArquivoAtiva = document.getElementById('pills-arquivo-tab')?.classList.contains('active');

    let response;

    if (tabArquivoAtiva && inputFile && inputFile.files && inputFile.files[0]) {
      // Envio via FormData
      const formData = new FormData();
      formData.append('ficheiro', inputFile.files[0]);
      if (document.getElementById('aiAnalisarProva')?.checked) formData.append('analisar', '1');
      formData.append('titulo', titulo);
      formData.append('disciplina', disciplina);
      formData.append('classe', classe);
      formData.append('trimestre', trimestre);
      formData.append('tipo_avaliacao', tipo);
      formData.append('duracao_minutos', duracao);
      formData.append('data_bloqueio_ia', dataBloqueioCompleta);
      // Selos do PDF: opções, mensagem de recusa à IA e posições escolhidas no editor
      aiOpcoesSelosEmFormulario(formData);

      response = await fetch('/api/v1/ferramentas/provas-anti-ia/codificar/', {
        method: 'POST',
        headers: {
          'Authorization': obterTokenSige() ? `Bearer ${obterTokenSige()}` : ''
        },
        body: formData
      });
    } else {
      // Envio via JSON
      let questoes = [];
      const tabItensAtiva = document.getElementById('pills-itens-tab')?.classList.contains('active');

      if (tabItensAtiva) {
        const itens = document.querySelectorAll('.item-questao-builder');
        itens.forEach((it, idx) => {
          const enunc = it.querySelector('.q-enunciado')?.value.trim();
          const cot = parseFloat(it.querySelector('.q-cotacao')?.value) || 2.0;
          if (enunc) {
            questoes.push({ numero: idx + 1, enunciado: enunc, cotacao: cot });
          }
        });
      }

      const textoProva = document.getElementById('aiProvaTextoCompleto')?.value.trim();

      const payload = {
        titulo,
        disciplina,
        classe,
        trimestre,
        tipo_avaliacao: tipo,
        duracao_minutos: duracao,
        data_bloqueio_ia: dataBloqueioCompleta,
        texto_prova: textoProva,
        questoes: questoes
      };

      response = await fetch('/api/v1/ferramentas/provas-anti-ia/codificar/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': obterTokenSige() ? `Bearer ${obterTokenSige()}` : ''
        },
        body: JSON.stringify(payload)
      });
    }

    let resJson;
    try {
      resJson = await response.json();
    } catch (_) {
      // O servidor devolveu HTML (ex.: 502 enquanto o sistema está a ser actualizado), não JSON
      throw new Error(response.status >= 500
        ? 'O servidor está temporariamente indisponível (pode estar a actualizar). Aguarde um minuto e tente novamente.'
        : 'Resposta inesperada do servidor. Tente novamente.');
    }

    if (!response.ok || !resJson.success) {
      throw new Error(resJson.message || 'Falha ao codificar prova.');
    }

    window.state.provaAntiIaAtual = resJson.data;

    // Renderizar prova codificada
    if (resJson.data.ficheiro_codificado) {
      renderizarResultadoFicheiroCodificado(resJson.data);
    } else {
      renderizarProvaCodificadaNaPreview(resJson.data);
    }

    // Alternar para a aba de pré-visualização e download
    alternarAbaProvasAntiIa('tab-preview-prova');

    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao('Prova codificada com sucesso! Todas as perguntas contam com QR Code e trava temporal Anti-IA.', 'success');
    }

    // Atualizar histórico em background
    carregarHistoricoProvasAntiIa();

  } catch (err) {
    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao(err.message || 'Erro ao processar prova.', 'danger');
    } else {
      alert(err.message);
    }
  } finally {
    btnSubmit.disabled = false;
    btnSubmit.innerHTML = originalHtml;
  }
}

/**
 * Prova importada: não se refaz nem se pré-visualiza; devolve-se o mesmo ficheiro, apenas codificado.
 */
function ajustarBarraResultado(importado, ext) {
  const btn = document.getElementById('btnDescarregarPdfOficial');
  if (!btn) return;
  const imprimir = btn.nextElementSibling;
  if (imprimir) imprimir.style.display = importado ? 'none' : '';
  const icone = importado ? 'bi-download' : 'bi-file-earmark-pdf-fill';
  const rotulo = importado ? `Descarregar prova codificada (${ext})` : 'Descarregar Prova Codificada (.pdf)';
  btn.innerHTML = `<i class="bi ${icone} me-2"></i>${rotulo}`;
}

function renderizarResultadoFicheiroCodificado(prova) {
  const ext = (prova.extensao || '').replace('.', '').toUpperCase();
  ajustarBarraResultado(true, ext);
  document.getElementById('previewTituloExame').textContent = 'Prova codificada';
  document.getElementById('previewSubtituloExame').textContent = 'A prova foi mantida igual, apenas codificada contra IA.';
  document.getElementById('folhaProvaConteudoDinamico').style.display = 'none';
  const ph = document.getElementById('previewEmptyPlaceholder');
  ph.style.display = 'block';
  ph.innerHTML = '';
  const card = document.createElement('div');
  card.className = 'text-center p-4';
  const titulo = document.createElement('h5');
  titulo.textContent = 'Prova codificada';
  const info = document.createElement('p');
  info.className = 'text-muted';
  info.textContent = `${prova.nome_original} — a prova foi mantida igual (${ext}), apenas codificada contra IA até ${formatarDataHora(prova.data_bloqueio_ia)}. Código: ${prova.codigo_autenticidade}`;
  card.append(titulo, info);
  if (prova.qr_ia) {
    // QR da página pública com as instruções à IA. O ficheiro da prova não é alterado: o QR é para colocar onde quiser.
    const qr = document.createElement('img');
    qr.src = prova.qr_ia;
    qr.alt = 'QR Code da página de instruções à IA';
    qr.style.cssText = 'width:160px;height:160px;display:block;margin:12px auto 4px';
    const link = document.createElement('div');
    link.className = 'small text-muted font-monospace mb-2';
    link.textContent = prova.url_ia;
    const btnQr = document.createElement('a');
    btnQr.className = 'btn btn-outline-dark btn-sm';
    btnQr.href = prova.qr_ia;
    btnQr.download = `QR_instrucoes_IA_${prova.codigo_autenticidade}.png`;
    btnQr.textContent = 'Descarregar QR (PNG)';
    card.append(qr, link, btnQr);
  }
  if (prova.analise) card.appendChild(montarRelatorioAnalise(prova.analise));
  ph.appendChild(card);
}

/**
 * Relatório da análise: perguntas genéricas (uma IA resolve de memória) e perguntas já existentes na internet.
 */
function montarRelatorioAnalise(analise) {
  const box = document.createElement('div');
  box.className = 'text-start border rounded p-3 mt-3 bg-light small';
  const linha = (rotulo, texto) => {
    const p = document.createElement('p');
    p.className = 'mb-2';
    const b = document.createElement('strong');
    b.textContent = rotulo + ' ';
    p.append(b, document.createTextNode(texto));
    box.appendChild(p);
  };
  const h = document.createElement('div');
  h.className = 'fw-bold mb-2';
  h.textContent = 'Análise da prova (antes de aplicar)';
  box.appendChild(h);
  if (analise.erro) {
    linha('', analise.erro);
    return box;
  }
  const d = analise.dependencia_da_turma;
  if (d) {
    linha('Dependência da turma:', `${d.percentagem_genericas}% das ${d.total_questoes} perguntas são genéricas` +
      (d.genericas.length ? ` (nº ${d.genericas.join(', ')}).` : '.'));
    linha('Sugestão:', d.sugestao);
  }
  const o = analise.originalidade;
  if (o && o.disponivel) {
    linha('Já existem na internet:', o.ja_existem_na_internet.length
      ? `perguntas nº ${o.ja_existem_na_internet.join(', ')} (verificadas ${o.verificadas}).` : `nenhuma das ${o.verificadas} verificadas.`);
    linha('Sugestão:', o.sugestao);
  } else if (o) {
    linha('Pesquisa na internet:', o.motivo);
  }
  return box;
}

/**
 * Alertas: avisa o professor quando alguém abre a página de instruções de uma prova ainda bloqueada.
 */
async function consultarAlertasProvasAntiIa() {
  const token = obterTokenSige();
  if (!token) return;
  try {
    const resp = await fetch('/api/v1/ferramentas/provas-anti-ia/alertas/', { headers: { 'Authorization': `Bearer ${token}` } });
    if (!resp.ok) return;
    const json = await resp.json();
    (json.alertas || []).slice(0, 3).forEach(a => {
      const quem = a.agente_ia ? `uma IA (${a.sistema})` : 'um leitor de QR Code ou navegador';
      if (typeof mostrarNotificacao === 'function') {
        mostrarNotificacao(`Prova ${a.prova}: ${quem} abriu a página de instruções às ${a.quando}.`, a.agente_ia ? 'danger' : 'warning');
      }
    });
    if (json.total > 3 && typeof mostrarNotificacao === 'function') {
      mostrarNotificacao(`Mais ${json.total - 3} acessos a provas bloqueadas. Veja o histórico.`, 'warning');
    }
  } catch (e) { /* sem rede: tenta no próximo ciclo */ }
}
if (!window.__sigeAlertasProvasIA) {
  window.__sigeAlertasProvasIA = setInterval(consultarAlertasProvasAntiIa, 60000);
  setTimeout(consultarAlertasProvasAntiIa, 3000);
}

/**
 * Renderiza a prova codificada na Aba de Pré-visualização
 */
function renderizarProvaCodificadaNaPreview(prova) {
  ajustarBarraResultado(false, '');
  document.getElementById('previewEmptyPlaceholder').style.display = 'none';
  document.getElementById('folhaProvaConteudoDinamico').style.display = 'block';

  document.getElementById('previewTituloExame').textContent = `${prova.titulo} (${prova.codigo_autenticidade})`;
  document.getElementById('previewSubtituloExame').textContent = `${prova.disciplina} • ${prova.classe} • ${prova.total_questoes} Perguntas • Trava Anti-IA ativa até ${formatarDataHora(prova.data_bloqueio_ia)}`;

  document.getElementById('docNomeEscola').textContent = (window.state && window.state.tenant && window.state.tenant.nome) ? window.state.tenant.nome.toUpperCase() : 'ESCOLA SECUNDÁRIA';
  document.getElementById('docTituloAvaliacao').textContent = `${prova.tipo_avaliacao} DE ${prova.disciplina.toUpperCase()}`;
  document.getElementById('docClasse').innerHTML = `<strong>Classe:</strong> ${prova.classe}`;
  document.getElementById('docTrimestre').innerHTML = `<strong>Trimestre:</strong> ${prova.trimestre}`;
  document.getElementById('docDuracao').innerHTML = `<strong>Duração:</strong> ${prova.duracao_minutos} Min`;
  document.getElementById('docCotacao').innerHTML = `<strong>Cotação:</strong> ${prova.cotacao_total} Val.`;

  document.getElementById('docDataBloqueioTexto').textContent = formatarDataHora(prova.data_bloqueio_ia);

  // Renderizar questões com QR Codes
  const containerQ = document.getElementById('docListaQuestoesRenderizadas');
  containerQ.innerHTML = '';

  (prova.questoes || []).forEach(q => {
    const qDiv = document.createElement('div');
    qDiv.className = 'd-flex justify-content-between align-items-start gap-3 p-3 border rounded bg-light';
    qDiv.innerHTML = `
      <div class="flex-grow-1">
        <div class="fw-bold mb-1 text-dark">
          <span class="badge bg-primary me-1">${q.numero}</span> (${parseFloat(q.cotacao).toFixed(1)} val) ${q.enunciado}
        </div>
        <div class="text-muted very-small mt-2">
          Espaço de Resolução:
          <div class="border-bottom border-secondary border-dashed my-2" style="height: 1px;"></div>
          <div class="border-bottom border-secondary border-dashed my-2" style="height: 1px;"></div>
          <div class="border-bottom border-secondary border-dashed my-2" style="height: 1px;"></div>
        </div>
      </div>
      <div class="text-center p-2 bg-white rounded border shadow-sm" style="min-width: 140px;">
        <img src="${q.qrcode_data}" alt="QR Anti-IA" style="width: 100px; height: 100px; display: block; margin: 0 auto;">
        <div class="very-small fw-bold text-dark mt-1">Q.${String(q.numero).padStart(2, '0')} ANTI-IA</div>
        <div class="very-small text-muted font-monospace" style="font-size: 0.65rem;">${q.codigo_questao.slice(-14)}</div>
      </div>
    `;
    containerQ.appendChild(qDiv);
  });

  // Atualizar também o select do simulador
  const simSelect = document.getElementById('simuladorQuestaoSelect');
  if (simSelect) {
    simSelect.innerHTML = '';
    (prova.questoes || []).forEach(q => {
      const opt = document.createElement('option');
      opt.value = q.numero;
      opt.textContent = `Questão nº ${q.numero} (${q.cotacao} val)`;
      simSelect.appendChild(opt);
    });
  }
}

/**
 * Descarrega o PDF oficial da prova codificada
 */
/**
 * Descarrega um ficheiro da API com o token de sessão (um link directo não envia o Authorization).
 */
function obterTokenSige() {
  return (window.state && window.state.token)
    || sessionStorage.getItem('sige_token')
    || localStorage.getItem('sige_token')
    || '';
}

async function descarregarFicheiroAutenticado(url, nomeFallback) {
  try {
    const pedir = (token) => fetch(url, { headers: token ? { 'Authorization': `Bearer ${token}` } : {} });
    let resp = await pedir(obterTokenSige());
    if (resp.status === 401 && typeof renovarTokenAcesso === 'function') {
      const novo = await renovarTokenAcesso();  // token expirado: renova e tenta de novo
      if (novo) resp = await pedir(novo);
    }
    if (!resp.ok) {
      let msg = 'Erro ao descarregar.';
      try { msg = (await resp.json()).message || msg; } catch (e) { /* resposta não JSON */ }
      throw new Error(msg);
    }
    const cd = resp.headers.get('Content-Disposition') || '';
    const m = cd.match(/filename="?([^";]+)"?/i);
    const blob = await resp.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = m ? m[1] : nomeFallback;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao('Descarregamento da prova codificada concluído!', 'success');
    }
  } catch (err) {
    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao(err.message, 'danger');
    } else {
      alert(err.message);
    }
  }
}

function descarregarProvaCodificadaPdfAtual() {
  const prova = window.state.provaAntiIaAtual;
  if (!prova || !prova.id) {
    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao('Nenhuma prova codificada para descarregar. Codifique uma primeiro.', 'warning');
    }
    return;
  }

  const url = prova.pdf_download_url || `/api/v1/ferramentas/provas-anti-ia/${prova.id}/descarregar-pdf/`;
  descarregarFicheiroAutenticado(url, `Prova_Blindada_${prova.codigo_autenticidade}.pdf`);
}

/**
 * Imprime folha de exame
 */
function imprimirFolhaExameCodificada() {
  window.print();
}

/**
 * Executa simulação de ataque de IA
 */
async function executarSimulacaoAntiIa() {
  const prova = window.state.provaAntiIaAtual;
  if (!prova || !prova.id) {
    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao('Por favor, codifique uma prova primeiro antes de rodar o simulador.', 'warning');
    }
    return;
  }

  const modelo = document.getElementById('simuladorModeloIA').value;
  const questaoNum = document.getElementById('simuladorQuestaoSelect').value;
  const simularPosData = document.getElementById('simuladorSimularPosData').checked;

  const consoleEl = document.getElementById('simuladorConsoleOutput');
  const badgeEl = document.getElementById('simuladorStatusBadge');

  badgeEl.className = 'badge bg-warning text-dark';
  badgeEl.textContent = 'A Interceptar...';
  consoleEl.textContent = `[SIMULADOR SIGE] A enviar imagem e payload do QR Code para o modelo: ${modelo}...\nA testar diretivas de Time-Lock e integridade acadêmica...`;

  try {
    const res = await fetch(`/api/v1/ferramentas/provas-anti-ia/${prova.id}/simular-ia/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': obterTokenSige() ? `Bearer ${obterTokenSige()}` : ''
      },
      body: JSON.stringify({
        numero_questao: questaoNum,
        modelo_ia: modelo,
        simular_pos_data: simularPosData
      })
    });

    const json = await res.json();
    if (!res.ok || !json.success) {
      throw new Error(json.message || 'Falha na simulação.');
    }

    if (json.bloqueada) {
      badgeEl.className = 'badge bg-danger';
      badgeEl.textContent = 'RESOLUÇÃO BLOQUEADA COM SUCESSO';
    } else {
      badgeEl.className = 'badge bg-success';
      badgeEl.textContent = 'TIME-LOCK EXPIRADO (LIBERADO)';
    }

    consoleEl.textContent = 
`[RESPOSTA OFICIAL CAPTURADA DO MODELO DE IA: ${modelo}]
STATUS: ${json.status_simulacao}
DATA LIMITE DO EXAME: ${json.data_bloqueio_formatada}
TENTATIVAS REPELIDAS REGISTADAS: ${json.tentativas_bloqueadas_total}

------------------------------------------------------------
${json.resposta_ia}
------------------------------------------------------------`;

    // Atualizar métricas
    const statTentativas = document.getElementById('statTentativasRepelidas');
    if (statTentativas) {
      statTentativas.textContent = json.tentativas_bloqueadas_total;
    }

  } catch (err) {
    badgeEl.className = 'badge bg-danger';
    badgeEl.textContent = 'ERRO';
    consoleEl.textContent = `Erro ao executar simulação: ${err.message}`;
  }
}

/**
 * Carrega Histórico e Estatísticas
 */
async function carregarHistoricoProvasAntiIa() {
  try {
    const res = await fetch('/api/v1/ferramentas/provas-anti-ia/lista/', {
      headers: {
        'Authorization': obterTokenSige() ? `Bearer ${obterTokenSige()}` : ''
      }
    });

    if (!res.ok) return;
    const json = await res.json();
    if (!json.success) return;

    window.state.provasAntiIaHistorico = json.data || [];

    // Atualizar stats
    if (json.stats) {
      // Os cartões de métricas foram retirados da página; só se actualiza o que existir.
      [['statTotalProvas', json.stats.total_provas], ['statProvasBloqueadas', json.stats.provas_bloqueadas],
       ['statProvasLiberadas', json.stats.provas_liberadas]].forEach(([id, valor]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = valor || 0;
      });
    }

    renderizarTabelaHistoricoProvas(json.data || []);
    renderizarPainelProvasAntiIa(json.data || [], json.stats || {});

  } catch (_) {}
}

// ---------------------------------------------------------------------
// Painel (no modelo da plataforma Pedagogia): próxima libertação com contagem
// decrescente, métricas, filtro por estado e pesquisa. Só mostra registos reais.
// ---------------------------------------------------------------------
var AI_MESES_CURTOS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
var AI_MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
var AI_DIAS = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado'];
var aiPainelEstado = 'todas';
var aiRelogioTimer = null;

function aiEscapar(texto) {
  const d = document.createElement('div');
  d.textContent = texto == null ? '' : String(texto);
  return d.innerHTML;
}

function renderizarPainelProvasAntiIa(lista, stats) {
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set('aiMetProtegidas', stats.provas_bloqueadas || 0);
  set('aiMetConcluidas', stats.provas_liberadas || 0);
  set('aiMetTotal', stats.copias || 0);
  set('aiMetTentativas', stats.leituras || 0);

  // próxima prova a sair da proteção
  const destaque = document.getElementById('aiPainelDestaque');
  const proximas = (lista || []).filter(p => p.bloqueada).sort((a, b) => new Date(a.data_bloqueio_ia) - new Date(b.data_bloqueio_ia));
  if (aiRelogioTimer) { clearInterval(aiRelogioTimer); aiRelogioTimer = null; }
  if (destaque) {
    if (proximas.length) {
      const p = proximas[0];
      document.getElementById('aiPainelDestaqueTitulo').textContent = p.titulo;
      document.getElementById('aiPainelDestaqueData').textContent = `${formatarDataHora(p.data_bloqueio_ia)} · ${p.codigo_autenticidade}`;
      destaque.hidden = false;
      const alvo = new Date(p.data_bloqueio_ia).getTime();
      const relogio = document.getElementById('aiPainelRelogio');
      const pad = (n) => String(n).padStart(2, '0');
      const tick = () => {
        const falta = Math.max(Math.floor((alvo - Date.now()) / 1000), 0);
        const v = { d: Math.floor(falta / 86400), h: Math.floor(falta % 86400 / 3600), m: Math.floor(falta % 3600 / 60), s: falta % 60 };
        Object.entries(v).forEach(([u, n]) => { const el = relogio.querySelector(`[data-u="${u}"]`); if (el) el.textContent = u === 'd' ? String(n) : pad(n); });
        if (falta === 0) { clearInterval(aiRelogioTimer); aiRelogioTimer = null; setTimeout(carregarHistoricoProvasAntiIa, 1500); }
      };
      tick();
      aiRelogioTimer = setInterval(tick, 1000);
    } else {
      destaque.hidden = true;
    }
  }

  const caixa = document.getElementById('aiPainelLista');
  if (!caixa) return;
  caixa.innerHTML = (lista || []).map(p => {
    const d = new Date(p.data_bloqueio_ia);
    const livre = !p.bloqueada;
    const texto = `${p.titulo} ${p.disciplina} ${p.classe} ${p.codigo_autenticidade}`.toLowerCase();
    return `
      <div class="ai-item" data-estado="${livre ? 'livre' : 'embargo'}" data-texto="${aiEscapar(texto)}">
        <div class="ai-data-tile ${livre ? 'ai-livre' : ''}"><b>${isNaN(d) ? '–' : d.getDate()}</b><small>${isNaN(d) ? '' : AI_MESES_CURTOS[d.getMonth()]}</small></div>
        <div>
          <div class="ai-item-titulo"><a href="#" class="text-decoration-none text-reset" onclick="abrirPaginaProvaAntiIa('${aiEscapar(p.id)}'); return false;">${aiEscapar(p.titulo)}</a></div>
          <div class="ai-item-meta">
            <span>${aiEscapar(p.disciplina)} · ${aiEscapar(p.classe)}</span>
            <span>${livre ? 'Protecção terminada' : 'Protegida até ' + aiEscapar(formatarDataHora(p.data_bloqueio_ia))}</span>
            <span class="font-monospace">${aiEscapar(p.codigo_autenticidade)}</span>
          </div>
        </div>
        <div class="ai-item-lado d-flex flex-wrap align-items-center gap-2">
          ${livre ? '<span class="badge bg-success"><i class="bi bi-unlock-fill me-1"></i>Libertada</span>' : '<span class="badge bg-danger"><i class="bi bi-lock-fill me-1"></i>Sob embargo</span>'}
          <span class="small text-muted">${p.copias || 0} cópia${(p.copias || 0) === 1 ? '' : 's'} · ${p.leituras || 0} leitura${(p.leituras || 0) === 1 ? '' : 's'}</span>
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-danger" title="Descarregar prova codificada" onclick="descarregarFicheiroAutenticado('/api/v1/ferramentas/provas-anti-ia/${aiEscapar(p.id)}/descarregar-pdf/', 'Prova_${aiEscapar(p.codigo_autenticidade)}')"><i class="bi bi-download"></i></button>
            <button type="button" class="btn btn-outline-dark" title="Uma cópia por aluno" onclick="abrirCopiasPorAluno('${aiEscapar(p.id)}')"><i class="bi bi-people"></i></button>
            <button type="button" class="btn btn-outline-primary" title="Abrir a página da prova" onclick="abrirPaginaProvaAntiIa('${aiEscapar(p.id)}')"><i class="bi bi-eye"></i></button>
          </div>
        </div>
      </div>`;
  }).join('');

  const vazio = document.getElementById('aiPainelVazio');
  if (vazio && !(lista || []).length) {
    vazio.innerHTML = '<i class="bi bi-file-earmark-lock2 fs-2 d-block mb-2"></i><strong class="d-block">Ainda não carregaste nenhuma prova</strong>' +
      '<span class="small d-block mb-3">Carrega um PDF ou Word, escolhe a data de libertação e as proteções anti-IA.</span>' +
      '<button type="button" class="btn btn-primary btn-sm" onclick="alternarAbaProvasAntiIa(\'tab-nova-prova\')">Carregar a primeira prova</button>';
    vazio.hidden = false;
  }
  aplicarFiltroPainelProvasAntiIa();
}

function aplicarFiltroPainelProvasAntiIa() {
  const caixa = document.getElementById('aiPainelLista');
  const vazio = document.getElementById('aiPainelVazio');
  if (!caixa) return;
  const q = (document.getElementById('aiPainelPesquisa')?.value || '').trim().toLowerCase();
  const itens = [...caixa.querySelectorAll('.ai-item')];
  let visiveis = 0;
  itens.forEach(it => {
    const ok = (aiPainelEstado === 'todas' || it.dataset.estado === aiPainelEstado) && (!q || it.dataset.texto.includes(q));
    it.hidden = !ok;
    if (ok) visiveis += 1;
  });
  if (vazio && itens.length) {
    vazio.hidden = visiveis > 0;
    vazio.textContent = 'Nenhuma prova corresponde ao filtro.';
  }
}

function aiDataMaputoAgora() {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Africa/Maputo', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date()).map(x => [x.type, x.value]));
  return Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute);
}

function atualizarResumoDataProvaAntiIa() {
  const data = document.getElementById('aiProvaDataBloqueio')?.value;
  const hora = document.getElementById('aiProvaHoraBloqueio')?.value || '00:00';
  const resumo = document.getElementById('aiResumoData');
  if (!resumo) return;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(data || '');
  if (!m) { resumo.hidden = true; return; }
  const alvo = Date.UTC(+m[1], +m[2] - 1, +m[3]);
  const d = new Date(alvo);
  const hoje = aiDataMaputoAgora();
  const falta = Math.round((alvo - Date.UTC(new Date(hoje).getUTCFullYear(), new Date(hoje).getUTCMonth(), new Date(hoje).getUTCDate())) / 86400000);
  const quando = falta < 0 ? 'Esta data já passou.' : falta === 0 ? 'Hoje.' : `Daqui a ${falta} dia${falta === 1 ? '' : 's'}.`;
  resumo.textContent = `Libertada ${AI_DIAS[d.getUTCDay()]}, ${d.getUTCDate()} de ${AI_MESES[d.getUTCMonth()]} de ${d.getUTCFullYear()}, às ${hora} (hora de Maputo). ${quando}`;
  resumo.hidden = false;
}

function iniciarInterfaceZipProvasAntiIa() {
  const raiz = document.getElementById('view-provas-anti-ia');
  if (!raiz || raiz.dataset.zipPronto === '1') return;
  raiz.dataset.zipPronto = '1';
  raiz.querySelectorAll('#aiPainelFiltros button[data-valor]').forEach(b => b.addEventListener('click', () => {
    aiPainelEstado = b.dataset.valor;
    raiz.querySelectorAll('#aiPainelFiltros button[data-valor]').forEach(x => {
      x.classList.toggle('active', x === b);
      x.setAttribute('aria-pressed', String(x === b));
    });
    aplicarFiltroPainelProvasAntiIa();
  }));
  document.getElementById('aiPainelPesquisa')?.addEventListener('input', aplicarFiltroPainelProvasAntiIa);
  raiz.querySelectorAll('[data-ai-dias]').forEach(b => b.addEventListener('click', () => {
    const d = new Date(aiDataMaputoAgora() + (+b.dataset.aiDias) * 86400000);
    const pad = (n) => String(n).padStart(2, '0');
    document.getElementById('aiProvaDataBloqueio').value = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
    document.getElementById('aiProvaHoraBloqueio').value = '08:00';
    atualizarResumoDataProvaAntiIa();
  }));
  ['aiProvaDataBloqueio', 'aiProvaHoraBloqueio'].forEach(id => document.getElementById(id)?.addEventListener('input', atualizarResumoDataProvaAntiIa));
  atualizarResumoDataProvaAntiIa();
}

/**
 * Renderiza tabela do histórico
 */
function renderizarTabelaHistoricoProvas(lista) {
  const tbody = document.getElementById('tabelaHistoricoProvasBody');
  if (!tbody) return;

  if (!lista || lista.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">Nenhuma avaliação blindada cadastrada até ao momento.</td></tr>';
    return;
  }

  tbody.innerHTML = lista.map(p => {
    const statusBadge = p.bloqueada 
      ? '<span class="badge bg-danger"><i class="bi bi-lock-fill me-1"></i>Bloqueada (Time-Lock)</span>'
      : '<span class="badge bg-success"><i class="bi bi-unlock-fill me-1"></i>Liberada</span>';

    return `
      <tr>
        <td class="font-monospace fw-bold text-dark small">${p.codigo_autenticidade}</td>
        <td>
          <div class="fw-bold text-dark">${p.titulo}</div>
          <small class="text-muted">${p.tipo_avaliacao} &bull; ${p.total_questoes} Perguntas &bull; ${p.cotacao_total} val.</small>
        </td>
        <td>${p.disciplina}</td>
        <td><span class="badge bg-light text-dark border">${p.classe}</span></td>
        <td class="small text-muted">${formatarDataHora(p.data_bloqueio_ia)}</td>
        <td>${statusBadge}</td>
        <td class="text-center fw-bold text-danger">${p.tentativas_bloqueadas || 0}</td>
        <td class="text-end">
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-danger" onclick="descarregarFicheiroAutenticado('/api/v1/ferramentas/provas-anti-ia/${p.id}/descarregar-pdf/', 'Prova_${p.codigo_autenticidade}')" title="Descarregar prova codificada">
              <i class="bi bi-download me-1"></i> Prova
            </button>
            <button type="button" class="btn btn-outline-dark" onclick="abrirCopiasPorAluno('${p.id}')" title="Uma cópia por aluno, com código único (rastreio)">
              <i class="bi bi-people me-1"></i> Cópias
            </button>
            <button type="button" class="btn btn-outline-primary" onclick="abrirDetalheProvaHistorico('${p.id}')" title="Ver Detalhes">
              <i class="bi bi-eye"></i>
            </button>
            <button type="button" class="btn btn-outline-secondary text-danger" onclick="eliminarProvaHistorico('${p.id}')" title="Eliminar prova">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function filtrarTabelaProvasAntiIa(termo) {
  const busca = (termo || '').toLowerCase().trim();
  const filtrados = (window.state.provasAntiIaHistorico || []).filter(p => {
    return p.titulo.toLowerCase().includes(busca) ||
           p.disciplina.toLowerCase().includes(busca) ||
           p.codigo_autenticidade.toLowerCase().includes(busca) ||
           p.classe.toLowerCase().includes(busca);
  });
  renderizarTabelaHistoricoProvas(filtrados);
}

async function eliminarProvaHistorico(provaId) {
  const prova = (window.state.provasAntiIaHistorico || []).find(p => p.id === provaId);
  const nome = prova ? `"${prova.titulo}" (${prova.codigo_autenticidade})` : 'esta prova';
  const aviso = prova && prova.bloqueada
    ? '\n\nA prova ainda está bloqueada: os QR já impressos continuam a avisar as IAs, mas o ficheiro codificado deixa de existir no sistema.'
    : '';
  if (!confirm(`Eliminar ${nome} do cofre?${aviso}\n\nEsta acção não pode ser desfeita.`)) return;
  try {
    const res = await fetch(`/api/v1/ferramentas/provas-anti-ia/${provaId}/eliminar/`, {
      method: 'DELETE',
      headers: { 'Authorization': obterTokenSige() ? `Bearer ${obterTokenSige()}` : '' }
    });
    const json = await res.json().catch(() => ({}));
    if (!res.ok || !json.success) throw new Error(json.message || 'Não foi possível eliminar a prova.');
    if (window.state.provaAntiIaAtual && window.state.provaAntiIaAtual.id === provaId) window.state.provaAntiIaAtual = null;
    await carregarHistoricoProvasAntiIa();
  } catch (err) {
    alert(err.message);
  }
}

async function abrirDetalheProvaHistorico(provaId) {
  try {
    const res = await fetch(`/api/v1/ferramentas/provas-anti-ia/${provaId}/detalhe/`, {
      headers: {
        'Authorization': obterTokenSige() ? `Bearer ${obterTokenSige()}` : ''
      }
    });
    const json = await res.json();
    if (json.success && json.data) {
      window.state.provaAntiIaAtual = json.data;
      renderizarProvaCodificadaNaPreview(json.data);
      alternarAbaProvasAntiIa('tab-preview-prova');
    }
  } catch (_) {}
}

/**
 * Cópias por aluno: filtros em cascata Classe -> Turma (altura constante, qualquer que seja o nº de turmas).
 * Gera um ZIP com uma cópia por aluno activo, cada uma com código único impresso no rodapé.
 */
async function abrirCopiasPorAluno(provaId) {
  const prova = (window.state.provasAntiIaHistorico || []).find(p => p.id === provaId);
  const antigo = document.getElementById('modalCopiasAntiIa');
  if (antigo) antigo.remove();
  document.body.insertAdjacentHTML('beforeend', `
    <div class="modal fade" id="modalCopiasAntiIa" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-dialog-centered"><div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title"><i class="bi bi-people me-2"></i>Cópias por aluno</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
        </div>
        <div class="modal-body">
          <p class="small text-muted mb-3">Cada aluno activo da turma recebe uma cópia de
            <strong>${prova ? prova.titulo : 'esta prova'}</strong> com um código único impresso no rodapé. Se uma cópia
            aparecer resolvida ou partilhada, o código identifica a quem foi entregue. As questões não são alteradas.</p>
          <label class="form-label small fw-bold" for="copiasClasse">Classe</label>
          <select id="copiasClasse" class="form-select mb-3" disabled><option>A carregar...</option></select>
          <label class="form-label small fw-bold" for="copiasTurma">Turma</label>
          <select id="copiasTurma" class="form-select" disabled><option value="">Escolha primeiro a classe</option></select>
          <div id="copiasMsg" class="small text-danger mt-3"></div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Fechar</button>
          <button type="button" class="btn btn-danger" id="copiasDescarregar" disabled><i class="bi bi-download me-1"></i>Descarregar (.zip)</button>
        </div>
      </div></div>
    </div>`);
  const modalEl = document.getElementById('modalCopiasAntiIa');
  const selClasse = modalEl.querySelector('#copiasClasse');
  const selTurma = modalEl.querySelector('#copiasTurma');
  const btn = modalEl.querySelector('#copiasDescarregar');
  const msg = modalEl.querySelector('#copiasMsg');
  new bootstrap.Modal(modalEl).show();
  modalEl.addEventListener('hidden.bs.modal', () => modalEl.remove());

  let turmas = [];
  try {
    const res = await apiFetch('/api/v1/escola-admin/turmas');
    turmas = (res && res.data) || [];
  } catch (_) { /* sem permissão ou sem rede: estado vazio abaixo */ }
  if (!turmas.length) {
    selClasse.innerHTML = '<option>Sem turmas registadas</option>';
    msg.textContent = 'Não há turmas registadas a que o seu perfil tenha acesso.';
    return;
  }
  const classes = [...new Set(turmas.map(t => t.grau_ano).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt', { numeric: true }));
  selClasse.innerHTML = '<option value="">Seleccione a classe</option>' + classes.map(c => `<option>${c}</option>`).join('');
  selClasse.disabled = false;
  selClasse.addEventListener('change', () => {
    const doGrau = turmas.filter(t => t.grau_ano === selClasse.value);
    selTurma.innerHTML = '<option value="">Seleccione a turma</option>' + doGrau.map(t => `<option value="${t.id}">${t.nome}</option>`).join('');
    selTurma.disabled = !doGrau.length;
    btn.disabled = true;
    msg.textContent = '';
  });
  selTurma.addEventListener('change', () => { btn.disabled = !selTurma.value; msg.textContent = ''; });
  btn.addEventListener('click', async () => {
    btn.disabled = true;
    await descarregarFicheiroAutenticado(
      `/api/v1/ferramentas/provas-anti-ia/${provaId}/copias/?turma_id=${encodeURIComponent(selTurma.value)}`, 'Copias_prova.zip');
    btn.disabled = false;
  });
}

function formatarDataHora(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleString('pt-PT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (_) {
    return isoStr;
  }
}
