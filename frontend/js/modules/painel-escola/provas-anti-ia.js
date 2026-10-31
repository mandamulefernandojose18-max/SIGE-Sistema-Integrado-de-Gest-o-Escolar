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
  }
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
      document.getElementById('statTotalProvas').textContent = json.stats.total_provas || 0;
      document.getElementById('statProvasBloqueadas').textContent = json.stats.provas_bloqueadas || 0;
      document.getElementById('statProvasLiberadas').textContent = json.stats.provas_liberadas || 0;
    }

    renderizarTabelaHistoricoProvas(json.data || []);

  } catch (_) {}
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

function formatarDataHora(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleString('pt-PT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (_) {
    return isoStr;
  }
}
