/**
 * SIGE - PAINEL-FINANCEIRO | Central de Recibos & Impressão
 * Ficheiro de código independente do menu: impressao.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 11. CENTRAL DE IMPRESSÃO (INDIVIDUAL E LOTE) ====================
async function prepararCentralImpressao() {
  try {
    const resTurmas = await apiFetch('/api/v1/escola-admin/turmas');
    const selectTurma = document.getElementById('printSelectTurma');
    if (selectTurma) {
      selectTurma.innerHTML = '<option value="">Selecione uma turma...</option>' + 
        (resTurmas.data || []).map(t => `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`).join('');
      
      if (resTurmas.data && resTurmas.data.length > 0) {
        selectTurma.value = resTurmas.data[0].id;
        await aoSelecionarTurmaImpressao();
      }
    }
  } catch (err) {}
}

async function aoSelecionarTurmaImpressao() {
  const turmaId = document.getElementById('printSelectTurma')?.value;
  const selectAluno = document.getElementById('printSelectAluno');
  if (!selectAluno) return;

  if (!turmaId) {
    selectAluno.innerHTML = '<option value="TODOS">-- Todos os Alunos da Turma (Emissão em Lote) --</option>';
    return;
  }

  selectAluno.innerHTML = '<option value="">A carregar alunos da turma...</option>';
  try {
    const res = await apiFetch(`/api/v1/alunos?turmaId=${turmaId}`);
    const alunos = res.data || [];
    let opts = `<option value="TODOS">-- Todos os Alunos da Turma (${alunos.length} Alunos - Emissão em Lote) --</option>`;
    opts += alunos.map((a, idx) => 
      `<option value="${a.id}">${a.numero || idx + 1}. ${a.nome} ${a.apelido || ''} (${a.matricula})</option>`
    ).join('');
    selectAluno.innerHTML = opts;
  } catch (err) {
    selectAluno.innerHTML = '<option value="TODOS">-- Todos os Alunos da Turma (Emissão em Lote) --</option>';
  }
}

function alternarCamposImpressao(tipo) {
  // Ajustes dinâmicos de interface
}

async function carregarVisualizacaoImpressao() {
  const tipo = document.getElementById('printTipoDoc').value;
  const turmaId = document.getElementById('printSelectTurma')?.value;
  const alunoId = document.getElementById('printSelectAluno')?.value;
  const preview = document.getElementById('printAreaPreview');
  preview.style.display = 'block';
  preview.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A processar documento oficial...</p></div>';

  try {
    if (alunoId === 'TODOS' || !alunoId) {
      if (!turmaId) return alert('Por favor, selecione uma turma para emissão em lote');
      if (tipo === 'PAUTA_TURMA') {
        const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/completa`);
        if (res.success) renderizarPautaGeralImpressao(res.data);
        return;
      }
      if (tipo === 'ACTA_CONSELHO') {
        await carregarActaConselho(turmaId);
        const containerActa = document.getElementById('containerActaConselhoCorpo');
        if (containerActa) preview.innerHTML = containerActa.innerHTML;
        return;
      }
      const resLote = await apiFetch(`/api/v1/impressao/lote/turma/${turmaId}?tipo=${tipo}`);
      if (resLote.success) {
        renderizarLoteImpressao(resLote.data);
      } else {
        throw new Error(resLote.message || 'Falha ao emitir lote');
      }
      return;
    }

    // Modo Individual
    if (tipo === 'BOLETIM') {
      const res = await apiFetch(`/api/v1/impressao/boletim/${alunoId}`);
      const d = res.data || res.boletim || res;
      if (res.success && d) renderizarBoletim(d);
      else throw new Error(res.message || 'Falha ao carregar boletim');
    } else if (tipo === 'DECLARACAO') {
      const res = await apiFetch(`/api/v1/impressao/declaracao/${alunoId}`);
      const d = res.data || res.declaracao || res;
      if (res.success && d) renderizarDeclaracao(d);
      else throw new Error(res.message || 'Falha ao carregar declaração');
    } else if (tipo === 'CERTIFICADO') {
      const res = await apiFetch(`/api/v1/impressao/certificado/${alunoId}`);
      const d = res.data || res.certificado || res;
      if (res.success && d) renderizarCertificado(d);
      else throw new Error(res.message || 'Falha ao carregar certificado');
    } else if (tipo === 'FICHA') {
      const res = await apiFetch(`/api/v1/impressao/ficha/${alunoId}`);
      const d = res.data || res.ficha || res;
      if (res.success && d) renderizarFichaAluno(d);
      else throw new Error(res.message || 'Falha ao carregar ficha do aluno');
    } else if (tipo === 'RECIBO') {
      const pagRes = await apiFetch(`/api/v1/pagamentos?alunoId=${alunoId}`).catch(() => ({}));
      if (pagRes.success && pagRes.data && pagRes.data.length > 0) {
        carregarReciboIndividual(pagRes.data[0].id);
      } else {
        carregarReciboIndividual(alunoId);
      }
    } else if (tipo === 'PAUTA_TURMA' || tipo === 'ACTA_CONSELHO') {
      if (turmaId) {
        if (tipo === 'PAUTA_TURMA') {
          const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/completa`);
          if (res.success) renderizarPautaGeralImpressao(res.data);
        } else {
          await carregarActaConselho(turmaId);
          const containerActa = document.getElementById('containerActaConselhoCorpo');
          if (containerActa) preview.innerHTML = containerActa.innerHTML;
        }
      }
    }
  } catch (err) {
    preview.innerHTML = `<div class="alert alert-danger text-center">${err.message || 'Erro ao processar documento'}</div>`;
  }
}

// ==================== GESTÃO AVANÇADA DE ORIENTAÇÃO (PORTRAIT / LANDSCAPE) ====================

function obterOrientacaoAtiva(tipoDoc = null) {
  const seletorCentral = document.getElementById('printOrientacaoSelect');
  const seletorPauta = document.getElementById('pautaOrientacaoSelect');
  const docTipo = tipoDoc || document.getElementById('printTipoDoc')?.value || '';

  // Se o utilizador tiver escolhido explicitamente no seletor da Central de Impressão
  if (seletorCentral && seletorCentral.value && seletorCentral.value !== 'auto') {
    return seletorCentral.value; // 'portrait' ou 'landscape'
  }

  // Se estiver a manipular Pauta ou Acta
  if (docTipo === 'PAUTA_TURMA' || docTipo === 'PAUTA') {
    if (seletorPauta && seletorPauta.value) return seletorPauta.value;
    return 'landscape'; // Pauta Oficial é estritamente Horizontal por defeito
  }

  if (docTipo === 'ACTA_CONSELHO' || docTipo === 'ACTA') {
    if (seletorPauta && seletorPauta.value) return seletorPauta.value;
    return 'portrait'; // Acta é Vertical por defeito
  }

  // Regra padrão automática para todos os outros documentos (Boletins, Declarações, Certificados, Recibos, Fichas):
  // Rigorosamente Vertical (Portrait) conforme normas MEC
  return 'portrait';
}

function definirOrientacaoDocumentoCentral(modo) {
  const sel = document.getElementById('printOrientacaoSelect');
  if (sel) sel.value = modo;

  const btnAuto = document.getElementById('btnOrientacaoAuto');
  const btnPort = document.getElementById('btnOrientacaoPortrait');
  const btnLand = document.getElementById('btnOrientacaoLandscape');

  if (btnAuto) {
    btnAuto.className = modo === 'auto' ? 'btn btn-primary' : 'btn btn-outline-secondary';
  }
  if (btnPort) {
    btnPort.className = modo === 'portrait' ? 'btn btn-primary' : 'btn btn-outline-secondary';
  }
  if (btnLand) {
    btnLand.className = modo === 'landscape' ? 'btn btn-primary' : 'btn btn-outline-secondary';
  }

  atualizarOrientacaoDocumentoCentral(modo);
}

function atualizarOrientacaoDocumentoCentral(modo) {
  const tipo = document.getElementById('printTipoDoc')?.value || '';
  const orientacao = obterOrientacaoAtiva(tipo);

  const preview = document.getElementById('printAreaPreview');
  if (preview) {
    if (orientacao === 'landscape') {
      preview.classList.remove('preview-portrait');
      preview.classList.add('preview-landscape');
      preview.style.maxWidth = '1140px';
    } else {
      preview.classList.remove('preview-landscape');
      preview.classList.add('preview-portrait');
      preview.style.maxWidth = '860px';
    }
  }

  document.body.classList.remove('print-orientacao-landscape', 'print-orientacao-portrait');
  document.body.classList.add(orientacao === 'landscape' ? 'print-orientacao-landscape' : 'print-orientacao-portrait');
}

function aoMudarOrientacaoPauta(valor) {
  const orientacao = valor || document.getElementById('pautaOrientacaoSelect')?.value || 'landscape';
  document.body.classList.remove('print-orientacao-landscape', 'print-orientacao-portrait');
  document.body.classList.add(orientacao === 'landscape' ? 'print-orientacao-landscape' : 'print-orientacao-portrait');

  const pautaContainer = document.getElementById('subViewPautaGeral');
  const actaContainer = document.getElementById('subViewActaConselho');
  if (pautaContainer) {
    pautaContainer.classList.remove('documento-orientacao-portrait', 'documento-orientacao-landscape');
    pautaContainer.classList.add(orientacao === 'landscape' ? 'documento-orientacao-landscape' : 'documento-orientacao-portrait');
  }
  if (actaContainer) {
    actaContainer.classList.remove('documento-orientacao-portrait', 'documento-orientacao-landscape');
    actaContainer.classList.add(orientacao === 'landscape' ? 'documento-orientacao-landscape' : 'documento-orientacao-portrait');
  }
}

function imprimirDocumentoCentral() {
  const tipo = document.getElementById('printTipoDoc')?.value || '';
  const orientacao = obterOrientacaoAtiva(tipo);

  document.body.classList.remove('print-orientacao-landscape', 'print-orientacao-portrait');
  document.body.classList.add(orientacao === 'landscape' ? 'print-orientacao-landscape' : 'print-orientacao-portrait');

  const preview = document.getElementById('printAreaPreview');
  if (!preview || preview.style.display === 'none' || !preview.innerHTML.trim()) {
    carregarVisualizacaoImpressao().then(() => window.print());
    return;
  }
  window.print();
}

async function descarregarPdfCentral() {
  const tipo = document.getElementById('printTipoDoc')?.value || 'BOLETIM';
  const turmaId = await obterTurmaAtivaOuPrimeira(document.getElementById('printSelectTurma')?.value);
  const alunoId = document.getElementById('printSelectAluno')?.value;
  const orientacao = obterOrientacaoAtiva(tipo);

  if (tipo === 'PAUTA_TURMA') {
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/pdf?anoLetivo=2026&orientacao=${orientacao}`, `Pauta_Oficial_${turmaId}.pdf`);
  } else if (tipo === 'ACTA_CONSELHO') {
    const sessao = JSON.parse(localStorage.getItem(`sige_sessao_acta_${turmaId}`) || '{}');
    const params = new URLSearchParams({ anoLetivo: '2026', orientacao: orientacao });
    if (sessao.presidente) params.append('presidente', sessao.presidente);
    if (sessao.data) params.append('data', sessao.data);
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/acta-pdf?${params.toString()}`, `Acta_Conselho_${turmaId}.pdf`);
  } else if (tipo === 'BOLETIM') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/boletim/${alunoId}/pdf?orientacao=${orientacao}`, `Boletim_${alunoId}.pdf`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/pdf?tipo=BOLETIM&orientacao=${orientacao}`, `Boletins_Turma_${turmaId}.pdf`);
    }
  } else if (tipo === 'DECLARACAO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/declaracao/${alunoId}/pdf?orientacao=${orientacao}`, `Declaracao_${alunoId}.pdf`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/pdf?tipo=DECLARACAO&orientacao=${orientacao}`, `Declaracoes_Turma_${turmaId}.pdf`);
    }
  } else if (tipo === 'CERTIFICADO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/certificado/${alunoId}/pdf?orientacao=${orientacao}`, `Certificado_${alunoId}.pdf`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/pdf?tipo=CERTIFICADO&orientacao=${orientacao}`, `Certificados_Turma_${turmaId}.pdf`);
    }
  } else if (tipo === 'RECIBO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/recibo/${alunoId}/pdf?orientacao=${orientacao}`, `Recibo_${alunoId}.pdf`);
    } else if (turmaId) {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/pdf?tipo=RECIBO&orientacao=${orientacao}`, `Recibos_Turma_${turmaId}.pdf`);
    }
  } else if (tipo === 'FICHA') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/ficha/${alunoId}/pdf?orientacao=${orientacao}`, `Ficha_${alunoId}.pdf`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/pdf?tipo=FICHA&orientacao=${orientacao}`, `Fichas_Turma_${turmaId}.pdf`);
    }
  } else {
    const preview = document.getElementById('printAreaPreview');
    if (preview) await exportarElementoParaPdf(preview, `${tipo}_Oficial_2026.pdf`, orientacao);
  }
}

async function descarregarDocxCentral() {
  const tipo = document.getElementById('printTipoDoc')?.value || 'BOLETIM';
  const turmaId = await obterTurmaAtivaOuPrimeira(document.getElementById('printSelectTurma')?.value);
  const alunoId = document.getElementById('printSelectAluno')?.value;
  const orientacao = obterOrientacaoAtiva(tipo);

  if (tipo === 'PAUTA_TURMA') {
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/docx?anoLetivo=2026&orientacao=${orientacao}`, `Pauta_Oficial_${turmaId}.docx`);
  } else if (tipo === 'ACTA_CONSELHO') {
    const sessao = JSON.parse(localStorage.getItem(`sige_sessao_acta_${turmaId}`) || '{}');
    const params = new URLSearchParams({ anoLetivo: '2026', orientacao: orientacao });
    if (sessao.presidente) params.append('presidente', sessao.presidente);
    if (sessao.data) params.append('data', sessao.data);
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/acta-docx?${params.toString()}`, `Acta_Conselho_${turmaId}.docx`);
  } else if (tipo === 'BOLETIM') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/boletim/${alunoId}/docx?orientacao=${orientacao}`, `Boletim_${alunoId}.docx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=BOLETIM&orientacao=${orientacao}`, `Boletins_Turma_${turmaId}.docx`);
    }
  } else if (tipo === 'DECLARACAO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/declaracao/${alunoId}/docx?orientacao=${orientacao}`, `Declaracao_${alunoId}.docx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=DECLARACAO&orientacao=${orientacao}`, `Declaracoes_Turma_${turmaId}.docx`);
    }
  } else if (tipo === 'CERTIFICADO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/certificado/${alunoId}/docx?orientacao=${orientacao}`, `Certificado_${alunoId}.docx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=CERTIFICADO&orientacao=${orientacao}`, `Certificados_Turma_${turmaId}.docx`);
    }
  } else if (tipo === 'RECIBO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/recibo/${alunoId}/docx?orientacao=${orientacao}`, `Recibo_${alunoId}.docx`);
    } else if (turmaId) {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=RECIBO&orientacao=${orientacao}`, `Recibos_Turma_${turmaId}.docx`);
    }
  } else if (tipo === 'FICHA') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/ficha/${alunoId}/docx?orientacao=${orientacao}`, `Ficha_${alunoId}.docx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=FICHA&orientacao=${orientacao}`, `Fichas_Turma_${turmaId}.docx`);
    }
  } else if (turmaId) {
    await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=BOLETIM&orientacao=${orientacao}`, `Documento_Turma_${turmaId}.docx`);
  }
}

async function descarregarXlsxCentral() {
  const tipo = document.getElementById('printTipoDoc')?.value || 'BOLETIM';
  const turmaId = await obterTurmaAtivaOuPrimeira(document.getElementById('printSelectTurma')?.value);
  const alunoId = document.getElementById('printSelectAluno')?.value;
  const orientacao = obterOrientacaoAtiva(tipo);

  if (!turmaId) return;

  if (tipo === 'ACTA_CONSELHO') {
    await exportarActaConselhoExcel(turmaId, '2026', orientacao);
  } else if (tipo === 'PAUTA_TURMA') {
    await exportarPautaGeralExcel(turmaId, '2026', orientacao);
  } else if (tipo === 'BOLETIM') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/boletim/${alunoId}/xlsx?orientacao=${orientacao}`, `Boletim_${alunoId}.xlsx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=BOLETIM&orientacao=${orientacao}`, `Boletins_Turma_${turmaId}.xlsx`);
    }
  } else if (tipo === 'DECLARACAO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/declaracao/${alunoId}/xlsx?orientacao=${orientacao}`, `Declaracao_${alunoId}.xlsx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=DECLARACAO&orientacao=${orientacao}`, `Declaracoes_Turma_${turmaId}.xlsx`);
    }
  } else if (tipo === 'CERTIFICADO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/certificado/${alunoId}/xlsx?orientacao=${orientacao}`, `Certificado_${alunoId}.xlsx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=CERTIFICADO&orientacao=${orientacao}`, `Certificados_Turma_${turmaId}.xlsx`);
    }
  } else if (tipo === 'FICHA' || tipo === 'RECIBO') {
    await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=${tipo}&orientacao=${orientacao}`, `${tipo}_Turma_${turmaId}.xlsx`);
  } else {
    await exportarPautaGeralExcel(turmaId, '2026', orientacao);
  }
}

async function carregarReciboIndividual(pagamentoId) {
  const preview = document.getElementById('printAreaPreview');
  preview.style.display = 'block';
  preview.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';

  try {
    const res = await apiFetch(`/api/v1/impressao/recibo/${pagamentoId}`);
    if (res.success) {
      renderizarRecibo(res.data);
    }
  } catch (err) {
    preview.innerHTML = '<div class="alert alert-danger">Erro ao carregar recibo de pagamento.</div>';
  }
}

function obterIdCanonicoDisciplina(str) {
  if (!str) return '';
  const s = String(str)
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();

  // Quebrar em palavras limpas
  const words = s.replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(Boolean);
  const compact = words.join('');

  // 1. TIC / Informática (palavra exata 'tic', 'tics' ou 'informatica' - JAMAIS substrings de matematica, estatistica, etc.)
  if (
    words.includes('tic') ||
    words.includes('tics') ||
    compact === 'tic' ||
    compact === 'tics' ||
    words.includes('informatica') ||
    compact.includes('tecnologiadeinformacao') ||
    compact.includes('tecnologiasdeinformacao') ||
    compact.includes('tecnologiasdainformacao')
  ) {
    return 'tic';
  }

  // 2. Matemática vs Matemática Aplicada
  if (words.includes('matematica') || compact.startsWith('matematica')) {
    if (words.includes('aplicada') || compact.includes('aplicada')) {
      return 'matematica_aplicada';
    }
    return 'matematica';
  }

  // 3. Educação Física (antes de Física)
  if ((words.includes('educacao') || words.includes('ed')) && (words.includes('fisica') || words.includes('fis'))) {
    return 'educacao_fisica';
  }

  // 4. Física pura
  if (words.includes('fisica') || compact === 'fisica') {
    return 'fisica';
  }

  // 5. Educação Visual / Desenho / Geometria Descritiva
  if (
    ((words.includes('educacao') || words.includes('ed')) && (words.includes('visual') || words.includes('vis'))) ||
    words.includes('desenho') ||
    compact.includes('geometriadescritiva') ||
    compact === 'edvisual' ||
    compact === 'ev' ||
    compact === 'dgd'
  ) {
    return 'educacao_visual';
  }

  // 6. Filosofia
  if (words.includes('filosofia') || compact.includes('filosofia')) {
    return 'filosofia';
  }

  // 7. Química
  if (words.includes('quimica') || compact === 'quimica') {
    return 'quimica';
  }

  // 8. Biologia
  if (words.includes('biologia') || compact === 'biologia') {
    return 'biologia';
  }

  // 9. Geografia
  if (words.includes('geografia') || compact === 'geografia') {
    return 'geografia';
  }

  // 10. História
  if (words.includes('historia') || compact === 'historia') {
    return 'historia';
  }

  // 11. Português
  if (words.includes('portugues') || compact.includes('linguaportuguesa') || compact === 'portugues') {
    return 'portugues';
  }

  // 12. Inglês
  if (words.includes('ingles') || compact.includes('linguainglesa') || compact === 'ingles') {
    return 'ingles';
  }

  // 13. Francês
  if (words.includes('frances') || compact.includes('linguafrancesa') || compact === 'frances') {
    return 'frances';
  }

  // 14. Empreendedorismo
  if (words.includes('empreendedorismo') || compact.includes('empreendedorismo')) {
    return 'empreendedorismo';
  }

  // 15. Agropecuária
  if (words.includes('agropecuaria') || compact.includes('agropecuaria') || words.includes('agro')) {
    return 'agropecuaria';
  }

  // 16. Psicopedagogia
  if (words.includes('psicopedagogia') || compact.includes('psicopedagogia')) {
    return 'psicopedagogia';
  }

  return compact;
}

function matchDisciplinaDocumento(alvo, candidato) {
  const idA = obterIdCanonicoDisciplina(alvo);
  const idC = obterIdCanonicoDisciplina(candidato);
  if (!idA || !idC) return false;
  return idA === idC;
}

function obterNomeCompletoDisciplina(str) {
  if (!str) return '';
  const id = obterIdCanonicoDisciplina(str);
  const mapa = {
    'portugues': 'Português',
    'ingles': 'Inglês',
    'frances': 'Francês',
    'historia': 'História',
    'geografia': 'Geografia',
    'biologia': 'Biologia',
    'fisica': 'Física',
    'quimica': 'Química',
    'matematica': 'Matemática',
    'matematica_aplicada': 'Matemática Aplicada',
    'filosofia': 'Introdução à Filosofia',
    'educacao_visual': 'Educação Visual',
    'educacao_fisica': 'Educação Física',
    'tic': 'Tecnologias de Informação e Comunicação',
    'empreendedorismo': 'Noções de Empreendedorismo',
    'agropecuaria': 'Agropecuária',
    'psicopedagogia': 'Psicopedagogia',
    'desenho': 'Desenho e Geometria Descritiva'
  };
  return mapa[id] || String(str).trim();
}

const PLANO_CURRICULAR_MEC_FRONTEND = {
  '7': {
    'Geral': ['Português', 'Inglês', 'História', 'Geografia', 'Ciências Naturais', 'Matemática', 'Educação Visual', 'Educação Física', 'Tecnologias de Informação e Comunicação']
  },
  '8': {
    'Geral': ['Português', 'Inglês', 'História', 'Geografia', 'Biologia', 'Física', 'Química', 'Matemática', 'Educação Visual', 'Educação Física', 'Tecnologias de Informação e Comunicação', 'Agropecuária']
  },
  '9': {
    'Geral': ['Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Biologia', 'Física', 'Química', 'Matemática', 'Educação Visual', 'Educação Física', 'Tecnologias de Informação e Comunicação', 'Noções de Empreendedorismo']
  },
  '10': {
    'Geral': ['Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Biologia', 'Física', 'Química', 'Matemática', 'Educação Visual', 'Educação Física', 'Tecnologias de Informação e Comunicação', 'Noções de Empreendedorismo']
  },
  '11': {
    'Letras com Geografia': ['Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Introdução à Filosofia', 'Matemática Aplicada', 'Educação Física', 'Tecnologias de Informação e Comunicação'],
    'Letras com História': ['Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Introdução à Filosofia', 'Matemática Aplicada', 'Educação Física', 'Tecnologias de Informação e Comunicação'],
    'Ciências com Biologia': ['Português', 'Inglês', 'Introdução à Filosofia', 'Matemática', 'Física', 'Química', 'Biologia', 'Educação Física', 'Tecnologias de Informação e Comunicação'],
    'Ciências com Desenho': ['Português', 'Inglês', 'Introdução à Filosofia', 'Matemática', 'Física', 'Química', 'Desenho e Geometria Descritiva', 'Educação Física', 'Tecnologias de Informação e Comunicação'],
    'Ciências com Geografia': ['Português', 'Inglês', 'Introdução à Filosofia', 'Matemática', 'Física', 'Química', 'Geografia', 'Educação Física', 'Tecnologias de Informação e Comunicação']
  },
  '12': {
    'Letras com Geografia': ['Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Introdução à Filosofia', 'Matemática Aplicada', 'Educação Física', 'Tecnologias de Informação e Comunicação'],
    'Letras com História': ['Português', 'Inglês', 'Francês', 'História', 'Geografia', 'Introdução à Filosofia', 'Matemática Aplicada', 'Educação Física', 'Tecnologias de Informação e Comunicação'],
    'Ciências com Biologia': ['Português', 'Inglês', 'Introdução à Filosofia', 'Matemática', 'Física', 'Química', 'Biologia', 'Educação Física', 'Tecnologias de Informação e Comunicação'],
    'Ciências com Desenho': ['Português', 'Inglês', 'Introdução à Filosofia', 'Matemática', 'Física', 'Química', 'Desenho e Geometria Descritiva', 'Educação Física', 'Tecnologias de Informação e Comunicação'],
    'Ciências com Geografia': ['Português', 'Inglês', 'Introdução à Filosofia', 'Matemática', 'Física', 'Química', 'Geografia', 'Educação Física', 'Tecnologias de Informação e Comunicação']
  }
};

function obterDisciplinasPlanoCurricularAlunoDoc(d) {
  d = d || {};
  const alunoObj = d.aluno || {};
  const turmaObj = typeof alunoObj.turma === 'object' && alunoObj.turma ? alunoObj.turma : {};
  const classeRaw = String(d.grauAno || alunoObj.classe || alunoObj.grau || turmaObj.grau_ano || turmaObj.nome || '10');
  let numClasse = '10';
  for (const n of ['12', '11', '10', '9', '8', '7']) {
    if (classeRaw.includes(n)) {
      numClasse = n;
      break;
    }
  }

  const areaRaw = String(d.area || alunoObj.area || turmaObj.area || turmaObj.nome || '').toLowerCase();
  const opcoesClasse = PLANO_CURRICULAR_MEC_FRONTEND[numClasse] || PLANO_CURRICULAR_MEC_FRONTEND['10'];
  let nomesPlano = null;

  if (['7', '8', '9', '10'].includes(numClasse)) {
    nomesPlano = opcoesClasse['Geral'];
  } else {
    if (areaRaw.includes('desenho') || areaRaw.includes('dgd')) {
      nomesPlano = opcoesClasse['Ciências com Desenho'];
    } else if (areaRaw.includes('biologia')) {
      nomesPlano = opcoesClasse['Ciências com Biologia'];
    } else if ((areaRaw.includes('ciencia') || areaRaw.includes('ciência')) && areaRaw.includes('geografia')) {
      nomesPlano = opcoesClasse['Ciências com Geografia'];
    } else if (areaRaw.includes('letra') && (areaRaw.includes('historia') || areaRaw.includes('história'))) {
      nomesPlano = opcoesClasse['Letras com História'];
    } else if (areaRaw.includes('letra')) {
      nomesPlano = opcoesClasse['Letras com Geografia'];
    } else {
      nomesPlano = opcoesClasse['Ciências com Biologia'];
    }
  }

  const recebidas = Array.isArray(d.disciplinas) ? d.disciplinas : (Array.isArray(alunoObj.disciplinas) ? alunoObj.disciplinas : []);
  // Se o backend já enviou a lista filtrada pela secção ou se queremos casar as notas com o plano oficial da classe/secção:
  return (nomesPlano || []).map((nomeOficial, idx) => {
    const existente = recebidas.find(item => matchDisciplinaDocumento(nomeOficial, item.nome || item.disciplina || ''));
    if (existente) {
      return { ...existente, nome: nomeOficial, disciplina: nomeOficial };
    }
    return {
      numero: idx + 1,
      nome: nomeOficial,
      disciplina: nomeOficial,
      t1: '---',
      t2: '---',
      t3: '---',
      media_anual: null,
      mediaFinal: null,
      notaFinal: null,
      situacao: '---'
    };
  });
}

function obterHtmlBoletimOficial(d) {
  const escolaObj = d.escola || state.tenant || {};
  const escolaNome = escolaObj.nome || 'Escola Secundária de Cambine';
  const escolaNomeFormatado = escolaNome.toUpperCase().startsWith('ESCOLA') ? escolaNome.toUpperCase() : `ESCOLA SECUNDÁRIA DE ${escolaNome.toUpperCase()}`;
  const provincia = (escolaObj.provincia || 'Inhambane').toUpperCase();
  const distrito = (escolaObj.distrito || 'Morrumbene').toUpperCase();
  const codigoEscola = escolaObj.codigo_escola || escolaObj.codigo || (state.tenant?.codigo_escola ? state.tenant.codigo_escola : 'ESC-1001');
  const anoLetivo = d.anoLetivo || d.anoLectivo || state.tenant?.ano_letivo_ativo || '2026';

  const alunoObj = d.aluno || {};
  const alunoNome = (alunoObj.nomeCompleto || `${alunoObj.nome || ''} ${alunoObj.apelido || ''}`.trim() || 'GRAÇA MONDLANE MONDLANE').toUpperCase();
  const matricula = alunoObj.matricula || alunoObj.codigo || 'MAT-2026-1006';

  let classeTurma = '10ª Classe - 10ª Classe A';
  if (alunoObj.grau && alunoObj.turma) {
    const turmaStr = typeof alunoObj.turma === 'object' ? (alunoObj.turma.nome || '') : String(alunoObj.turma);
    classeTurma = turmaStr.includes(alunoObj.grau) ? `${alunoObj.grau} - ${turmaStr}` : `${alunoObj.grau} - ${turmaStr}`;
  } else if (alunoObj.turma) {
    classeTurma = typeof alunoObj.turma === 'object' ? (alunoObj.turma.nome || '-') : String(alunoObj.turma);
  } else if (alunoObj.grau) {
    classeTurma = alunoObj.grau;
  }

  let turno = alunoObj.turno || (typeof alunoObj.turma === 'object' ? alunoObj.turma.turno : '') || 'Manhã';
  if (turno.toUpperCase() === 'MANHA') turno = 'Manhã';
  else if (turno.toUpperCase() === 'TARDE') turno = 'Tarde';
  else if (turno.toUpperCase() === 'NOITE') turno = 'Noite';

  let listaDisciplinas = [];
  const disciplinasCurricularesAluno = obterDisciplinasPlanoCurricularAlunoDoc(d);
  if (disciplinasCurricularesAluno.length > 0) {
    listaDisciplinas = disciplinasCurricularesAluno.map(item => {
      const nome = obterNomeCompletoDisciplina(item.nome || item.disciplina || 'Disciplina');
      
      const formatarNota = (val) => {
        if (val === undefined || val === null || val === '-' || val === '' || val === '---') return '---';
        const num = Number(val);
        return isNaN(num) ? '---' : Math.round(num);
      };

      const t1 = formatarNota(item.t1);
      const t2 = formatarNota(item.t2);
      const t3 = formatarNota(item.t3);

      let medAnual = '---';
      if (item.media_anual !== undefined && item.media_anual !== null && item.media_anual !== '-' && item.media_anual !== '---' && !isNaN(Number(item.media_anual))) {
        medAnual = Math.round(Number(item.media_anual));
      } else if (item.mediaFinal !== undefined && item.mediaFinal !== null && item.mediaFinal !== '-' && item.mediaFinal !== '---' && !isNaN(Number(item.mediaFinal))) {
        medAnual = Math.round(Number(item.mediaFinal));
      } else {
        const notasValidas = [t1, t2, t3].filter(v => typeof v === 'number');
        if (notasValidas.length > 0) {
          medAnual = Math.round(notasValidas.reduce((a, b) => a + b, 0) / notasValidas.length);
        }
      }

      let situacao = '---';
      if (typeof medAnual === 'number') {
        situacao = medAnual >= 9.5 ? 'Aprovado' : 'Reprovado';
      } else if (item.situacao && item.situacao !== 'Pendente') {
        situacao = item.situacao;
      }

      return { nome, t1, t2, t3, medAnual, situacao };
    });
  }

  // Cálculo da Média Global
  let mediaGlobalInt = '---';
  if (d.mediaGeral !== undefined && d.mediaGeral !== null && d.mediaGeral !== '-' && !isNaN(Number(d.mediaGeral))) {
    mediaGlobalInt = Math.round(Number(d.mediaGeral));
  } else if (d.mediaGlobal !== undefined && d.mediaGlobal !== null && d.mediaGlobal !== '-' && !isNaN(Number(d.mediaGlobal))) {
    mediaGlobalInt = Math.round(Number(d.mediaGlobal));
  } else {
    const mediasValidas = listaDisciplinas.map(l => l.medAnual).filter(v => typeof v === 'number');
    if (mediasValidas.length > 0) {
      mediaGlobalInt = Math.round(mediasValidas.reduce((a, b) => a + b, 0) / mediasValidas.length);
    }
  }

  const situacaoGlobal = typeof mediaGlobalInt === 'number'
    ? (mediaGlobalInt >= 9.5 ? 'Aprovado' : 'Reprovado')
    : (d.situacaoGlobal || d.resultadoFinal || 'Sem Avaliação');

  const corpoTabelaBoletim = listaDisciplinas.length > 0
    ? listaDisciplinas.map(item => `
        <tr>
          <td style="border: 1px solid #777777; padding: 6px 10px; font-size: 11.5pt; font-weight: 600; text-align: left;">${item.nome}</td>
          <td style="border: 1px solid #777777; padding: 6px 6px; font-size: 11pt; text-align: center; color: ${item.t1 === '---' ? '#777777' : '#111111'};">${item.t1}</td>
          <td style="border: 1px solid #777777; padding: 6px 6px; font-size: 11pt; text-align: center; color: ${item.t2 === '---' ? '#777777' : '#111111'};">${item.t2}</td>
          <td style="border: 1px solid #777777; padding: 6px 6px; font-size: 11pt; text-align: center; color: ${item.t3 === '---' ? '#777777' : '#111111'};">${item.t3}</td>
          <td style="border: 1px solid #777777; padding: 6px 6px; font-size: 11.5pt; font-weight: bold; text-align: center;">${item.medAnual}</td>
          <td style="border: 1px solid #777777; padding: 6px 8px; font-size: 10.5pt; font-weight: 600; text-align: center; color: ${item.situacao === 'Reprovado' ? '#dc2626' : '#111827'};">${item.situacao}</td>
        </tr>
      `).join('')
    : `
        <tr>
          <td colspan="6" style="border: 1px solid #777777; padding: 12px; font-size: 10pt; text-align: center; color: #777777; font-style: italic;">
            Nenhuma avaliação registada na caderneta para este aluno.
          </td>
        </tr>
      `;

  const decisaoConselhoHtml = typeof mediaGlobalInt === 'number'
    ? `<span style="font-weight: bold;">Decisão do Conselho:</span> Resultado pedagógico do aluno: <span style="font-weight: 500;">${situacaoGlobal}</span> com média global de <span style="font-weight: 500;">${mediaGlobalInt}</span> valores.`
    : `<span style="font-weight: bold;">Decisão do Conselho:</span> O aluno ainda não possui avaliações concluídas na caderneta.`;

  return `
    <div class="documento-boletim-oficial" style="display: flex; flex-direction: column; justify-content: space-between; width: 100%; max-width: 210mm; min-height: 282mm; box-sizing: border-box; overflow: hidden; padding: 10mm 12mm 8mm 12mm; margin: 0 auto;">
      <!-- MARCA DE ÁGUA CENTRAL DO EMBLEMA NACIONAL -->
      <div style="position: absolute; top: 52%; left: 50%; transform: translate(-50%, -46%); width: 260px; height: 260px; opacity: 0.08; pointer-events: none; z-index: 1; display: flex; align-items: center; justify-content: center;">
        <img src="/img/emblema-mocambique.png" style="width: 100%; height: 100%; object-fit: contain;" alt="Emblema de Moçambique">
      </div>

      <div style="position: relative; z-index: 2; flex: 1; display: flex; flex-direction: column; width: 100%; max-width: 100%; box-sizing: border-box;">
        <!-- CABEÇALHO OFICIAL REPÚBLICA DE MOÇAMBIQUE -->
        <div style="text-align: center; margin-bottom: 4px;">
          <div style="margin-bottom: 4px;">
            <img src="/img/emblema-mocambique.png" style="width: 50px; height: 50px; object-fit: contain;" alt="Emblema Nacional">
          </div>
          <div style="font-size: 12.5pt; font-weight: bold; letter-spacing: 0.5px; line-height: 1.2; text-transform: uppercase;">
            REPÚBLICA DE MOÇAMBIQUE
          </div>
          <div style="font-size: 10pt; font-weight: bold; line-height: 1.2; text-transform: uppercase; margin-top: 2px;">
            GOVERNO DA PROVÍNCIA DE ${provincia}
          </div>
          <div style="font-size: 9pt; font-weight: 500; line-height: 1.2; text-transform: uppercase; margin-top: 2px;">
            SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE ${distrito}
          </div>
          <div style="font-size: 11pt; font-weight: bold; line-height: 1.2; text-transform: uppercase; margin-top: 3px;">
            ${escolaNomeFormatado}
          </div>
          <div style="font-size: 8.5pt; color: #333333; margin-top: 2px;">
            Código da Instituição: ${codigoEscola}
          </div>
        </div>

        <!-- LINHA DIVISÓRIA -->
        <div style="border-bottom: 2px solid #111111; margin-top: 6px; margin-bottom: 8px;"></div>

        <!-- TÍTULO -->
        <div style="text-align: center; font-size: 11.5pt; font-weight: bold; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 8mm;">
          BOLETIM DE APROVEITAMENTO ESCOLAR — ANO LECTIVO ${anoLetivo}
        </div>

        <!-- CAIXA COM DADOS DO ALUNO -->
        <div style="border: 1px solid #777777; border-radius: 1px; padding: 8px 12px; margin-bottom: 12px; background-color: #ffffff; width: 100%; box-sizing: border-box;">
          <table style="width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 9.5pt; font-family: 'Times New Roman', Times, Georgia, serif;">
            <tr>
              <td style="width: 58%; padding: 3px 4px 3px 0; vertical-align: top; overflow-wrap: break-word;">
                <span style="font-weight: bold;">Nome do Aluno:</span> <span style="font-weight: bold; text-transform: uppercase;">${alunoNome}</span>
              </td>
              <td style="width: 42%; padding: 3px 0; vertical-align: top; overflow-wrap: break-word;">
                <span style="font-weight: bold;">Classe / Turma:</span> <span>${classeTurma}</span>
              </td>
            </tr>
            <tr>
              <td style="padding: 3px 4px 3px 0; vertical-align: top;">
                <span style="font-weight: bold;">Nº Matrícula:</span> <span>${matricula}</span>
              </td>
              <td style="padding: 3px 0; vertical-align: top;">
                <span style="font-weight: bold;">Turno:</span> <span>${turno}</span>
              </td>
            </tr>
          </table>
        </div>

        <!-- TABELA DE NOTAS OFICIAL -->
        <table style="width: 100%; max-width: 100%; table-layout: fixed; border-collapse: collapse; margin-bottom: 10px; font-family: 'Times New Roman', Times, Georgia, serif; border: 1.5px solid #444444; box-sizing: border-box;">
          <thead>
            <tr style="background-color: #e9ecf2; border-bottom: 1.5px solid #444444;">
              <th style="border: 1px solid #666666; padding: 5px 8px; font-size: 10.5pt; font-weight: bold; text-align: left; width: 38%;">DISCIPLINA</th>
              <th style="border: 1px solid #666666; padding: 5px 4px; font-size: 9.5pt; font-weight: bold; text-align: center; width: 12%;">1º TRIM</th>
              <th style="border: 1px solid #666666; padding: 5px 4px; font-size: 9.5pt; font-weight: bold; text-align: center; width: 12%;">2º TRIM</th>
              <th style="border: 1px solid #666666; padding: 5px 4px; font-size: 9.5pt; font-weight: bold; text-align: center; width: 12%;">3º TRIM</th>
              <th style="border: 1px solid #666666; padding: 5px 4px; font-size: 9.5pt; font-weight: bold; text-align: center; width: 13%;">MÉD. ANUAL</th>
              <th style="border: 1px solid #666666; padding: 5px 6px; font-size: 9.5pt; font-weight: bold; text-align: center; width: 13%;">SITUAÇÃO</th>
            </tr>
          </thead>
          <tbody>
            ${corpoTabelaBoletim}

            <!-- LINHA DA MÉDIA GLOBAL DO PERÍODO -->
            <tr style="background-color: #e9ecf2; font-weight: bold; border-top: 1.5px solid #444444;">
              <td style="border: 1px solid #666666; padding: 5px 8px; font-size: 10pt; text-align: left;">MÉDIA GLOBAL DO PERÍODO</td>
              <td style="border: 1px solid #666666; padding: 5px 4px; font-size: 9.5pt; text-align: center; color: #777777;">---</td>
              <td style="border: 1px solid #666666; padding: 5px 4px; font-size: 9.5pt; text-align: center; color: #777777;">---</td>
              <td style="border: 1px solid #666666; padding: 5px 4px; font-size: 9.5pt; text-align: center; color: #777777;">---</td>
              <td style="border: 1px solid #666666; padding: 5px 4px; font-size: 10.5pt; text-align: center;">${mediaGlobalInt}</td>
              <td style="border: 1px solid #666666; padding: 5px 6px; font-size: 10pt; text-align: center;">${situacaoGlobal}</td>
            </tr>
          </tbody>
        </table>

        <!-- DECISÃO DO CONSELHO -->
        <div style="font-size: 9.5pt; margin-top: 6px; margin-bottom: 14px; line-height: 1.4;">
          ${decisaoConselhoHtml}
        </div>
      </div>

      <!-- ASSINATURAS OFICIAIS DENTRO DA MOLDURA -->
      <div style="display: flex; justify-content: space-around; align-items: flex-end; padding: 0 10px; margin-bottom: 4mm; position: relative; z-index: 2; width: 100%; box-sizing: border-box;">
        <div style="width: 42%; max-width: 220px; text-align: center;">
          <div style="border-top: 1.2px solid #111111; margin-bottom: 6px;"></div>
          <div style="font-weight: bold; font-size: 9.5pt;">O Director de Turma</div>
        </div>
        <div style="width: 42%; max-width: 220px; text-align: center;">
          <div style="border-top: 1.2px solid #111111; margin-bottom: 6px;"></div>
          <div style="font-weight: bold; font-size: 9.5pt;">O Director da Escola</div>
        </div>
      </div>
    </div>
  `;
}

function renderizarBoletim(d) {
  d = d || {};
  if (!d.aluno) d.aluno = {};
  if (!d.escola) d.escola = {};
  if (!d.disciplinas) d.disciplinas = [];
  const preview = document.getElementById('printAreaPreview');
  const safeName = (d.aluno?.nomeCompleto || d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
  const ano = d.anoLetivo || d.anoLectivo || '2026';
  const alunoId = d.aluno?.id || document.getElementById('printSelectAluno')?.value || '';

  preview.style.display = 'block';
  preview.innerHTML = `
    <div class="no-print mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span class="badge bg-primary px-3 py-2"><i class="bi bi-file-earmark-check me-1"></i> Boletim de Aproveitamento Escolar Oficial A4</span>
      <div class="d-flex gap-2">
        ${alunoId ? `<button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarDocumentoOficialPdf('BOLETIM', '${alunoId}')"><i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF (A4)</button>` : ''}
        <button class="btn btn-primary btn-sm fw-semibold" onclick="imprimirDocumentoComTitulo('Boletim_${safeName}_${ano}')">
          <i class="bi bi-printer me-1"></i> Imprimir / Guardar em PDF
        </button>
      </div>
    </div>
    ${obterHtmlBoletimOficial(d)}
  `;
}

// ==================== DOCUMENTOS OFICIAIS MEC (1 PÁGINA A4) ====================

function obterHtmlDeclaracaoOficial(d) {
  d = d || {};
  if (!d.aluno) d.aluno = {};
  if (!d.escola) d.escola = {};
  if (!d.disciplinas) d.disciplinas = [];
  const escolaNome = (d.escola?.nome || 'Escola Secundária').toUpperCase();
  const provincia = (d.escola?.provincia || 'Inhambane').toUpperCase();
  const distrito = (d.escola?.distrito || 'Massinga');
  const directorNome = d.directorNome || 'Pero Chitofo Murrombe';
  const directorCarreira = d.directorCarreira || 'Especialista de Educação';
  
  const alunoNome = (d.aluno?.nomeCompleto || d.aluno?.nome || 'ALUNO NÃO IDENTIFICADO').toUpperCase();
  const pai = d.aluno?.pai || '...........................................';
  const mae = d.aluno?.mae || '...........................................';
  const anoLectivo = d.anoLectivo || d.anoLetivo || '2026';
  const grauClasse = d.grauAno || d.aluno?.turma?.grau_ano || d.aluno?.classe || '10ª Classe';
  const docTipo = d.aluno?.tipo_documento || 'B.I.';
  const docNum = d.aluno?.numero_documento || '---';
  const termoExames = d.termoExames || '124';
  const folha = d.folha || '32';

  // Disciplinas do plano curricular da classe e secção do aluno
  const disciplinasDoPlano = obterDisciplinasPlanoCurricularAlunoDoc(d);
  const notasMap = {};
  disciplinasDoPlano.forEach(item => {
    const n = (item.disciplina || item.nome || '').trim();
    const v = item.notaFinal !== undefined ? item.notaFinal : (item.mediaFinal !== undefined ? item.mediaFinal : item.media_anual);
    if (n) {
      notasMap[n] = v;
    }
  });

  const obterNotaValor = (nomeDisc) => {
    for (const [ch, vl] of Object.entries(notasMap)) {
      if (matchDisciplinaDocumento(nomeDisc, ch)) {
        if (vl !== null && vl !== undefined && vl !== '-' && vl !== '---' && !isNaN(vl)) {
          const num = Number(vl);
          if (num > 0) {
            return Number.isInteger(num) ? String(num) : num.toFixed(1);
          }
        }
      }
    }
    return null;
  };

  const nomesCurriculares = disciplinasDoPlano.map(item => obterNomeCompletoDisciplina(item.nome || item.disciplina || '')).filter(Boolean);
  const meioDecl = Math.ceil(nomesCurriculares.length / 2);
  const colEsquerda = nomesCurriculares.slice(0, meioDecl);
  const colDireita = nomesCurriculares.slice(meioDecl);

  const renderLinhaDisc = (disc) => {
    const nota = obterNotaValor(disc);
    const notaTexto = nota !== null ? `( ${nota} ) valores` : `( --- )`;
    return `
      <div style="display: flex; justify-content: flex-start; align-items: baseline; margin-bottom: 6px; font-size: 11.5pt; line-height: 1.35; width: 100%; max-width: 100%; box-sizing: border-box; overflow: hidden;">
        <span style="min-width: 0; overflow-wrap: break-word;">${disc}</span>
        <span style="display: inline-block; width: 22px; min-width: 10px; border-bottom: 1px dotted #555; margin: 0 6px; flex-shrink: 1;"></span>
        <span style="font-weight: bold; white-space: nowrap; flex-shrink: 0;">${notaTexto}</span>
      </div>
    `;
  };

  const todasAvaliadasDecl = [...colEsquerda, ...colDireita].every(disc => obterNotaValor(disc) !== null);

  let mediaGlobalVal = null;
  if (todasAvaliadasDecl && d.mediaGlobal !== undefined && d.mediaGlobal !== null && d.mediaGlobal !== '-' && d.mediaGlobal !== '---' && !isNaN(Number(d.mediaGlobal))) {
    mediaGlobalVal = Math.round(Number(d.mediaGlobal));
  } else if (todasAvaliadasDecl && d.mediaGeral !== undefined && d.mediaGeral !== null && d.mediaGeral !== '-' && d.mediaGeral !== '---' && !isNaN(Number(d.mediaGeral))) {
    mediaGlobalVal = Math.round(Number(d.mediaGeral));
  }
  const mediaGlobalStr = mediaGlobalVal !== null ? `( ${mediaGlobalVal} ) valores.` : `( --- )`;
  const resOficial = (!todasAvaliadasDecl && (!d.resultadoOficial || d.resultadoOficial === 'Aprovado')) ? 'Pendente' : (d.resultadoOficial || d.resultadoFinal || 'Pendente');

  const agora = new Date();
  const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

  return `
    <div class="documento-a4-pagina-unica" style="width: 100%; max-width: 210mm; min-height: 282mm; padding: 4mm 6mm; margin: 0 auto; box-sizing: border-box; overflow: hidden; background: #fff; font-family: 'Times New Roman', Times, serif; position: relative; page-break-inside: avoid; page-break-after: always;">
      <div class="borda-oficial-declaracao" style="border: 2px solid #222; padding: 8mm 10mm; width: 100%; max-width: 100%; min-height: 272mm; box-sizing: border-box; overflow: hidden; position: relative; display: flex; flex-direction: column; justify-content: space-between;">
        <img src="/img/emblema-mocambique.png" class="marca-dagua-emblema" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 260px; height: 260px; opacity: 0.07; pointer-events: none; z-index: 0;" alt="Marca d'Água">
        
        <!-- Cabeçalho Oficial -->
        <div style="text-align: center; position: relative; z-index: 1; margin-bottom: 10mm;">
          <img src="/img/emblema-mocambique.png" style="width: 44px; height: 44px; margin-bottom: 2px; object-fit: contain;" alt="Emblema Nacional de Moçambique">
          <div style="font-size: 11pt; font-weight: bold; letter-spacing: 0.5px;">REPÚBLICA DE MOÇAMBIQUE</div>
          <div style="font-size: 10pt; font-weight: bold;">GOVERNO DA PROVÍNCIA DE ${provincia}</div>
          <div style="font-size: 9pt; font-weight: bold;">DIRECÇÃO PROVINCIAL DA EDUCAÇÃO E CULTURA DE ${provincia}</div>
          <div style="font-size: 10.5pt; font-weight: bold; text-transform: uppercase; margin-top: 2px;">${escolaNome}</div>
          <div style="font-size: 13.5pt; font-weight: bold; margin-top: 4px; border-bottom: 1.5px solid #111; display: inline-block; padding-bottom: 2px;">Declaração</div>
        </div>

        <!-- Texto Declarativo Oficial -->
        <div style="position: relative; z-index: 1; flex: 1; width: 100%; max-width: 100%; box-sizing: border-box;">
          <p style="text-align: justify; font-size: 11pt; line-height: 1.5; margin: 0 0 10px 0; text-indent: 20px;">
            Para os devidos efeitos se declara que <strong>${alunoNome}</strong>, filho(a) de <strong>${pai}</strong> e de <strong>${mae}</strong>, portador(a) do <strong>${docTipo}</strong> número <strong>${docNum}</strong>, concluiu com aproveitamento a <strong>${grauClasse}</strong> neste estabelecimento de ensino, no ano lectivo de <strong>${anoLectivo}</strong>, com as seguintes classificações:
          </p>

          <!-- Tabela de Disciplinas em 2 Colunas estritamente contida nas bordas -->
          <div style="display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); column-gap: 16px; margin: 8px 0; width: 100%; max-width: 100%; box-sizing: border-box;">
            <div style="min-width: 0; overflow: hidden;">
              ${colEsquerda.map(renderLinhaDisc).join('')}
            </div>
            <div style="min-width: 0; overflow: hidden;">
              ${colDireita.map(renderLinhaDisc).join('')}
            </div>
          </div>

          <div style="font-size: 11pt; font-weight: bold; margin: 8px 0;">
            Média global da Classe: ${mediaGlobalStr}
          </div>

          <p style="font-size: 10.5pt; line-height: 1.45; margin: 8px 0; text-align: justify;">
            Consta no livro do termo de exames sob o número <strong>${termoExames}</strong>, folha <strong>${folha}</strong>, do ano lectivo de <strong>${anoLectivo}</strong>, que o estudante obteve o resultado de <strong>${resOficial}</strong>.<br>
            Por ser verdade e me haver sido solicitada, mandei passar a presente declaração que vai por mim assinada e autenticada com o carimbo a tinta de óleo em uso nesta instituição.
          </p>
        </div>

        <!-- Secção de Assinaturas e Datação Formal dentro da moldura -->
        <div style="position: relative; z-index: 1; margin-top: auto; padding-bottom: 4mm; width: 100%; box-sizing: border-box;">
          <div style="display: flex; justify-content: space-between; font-size: 9pt; margin-bottom: 10px;">
            <div style="width: 46%;">
              <div>Extraído por: ____________________________</div>
              <div style="margin-top: 4px;">Data: ___ / ___ / 2026</div>
            </div>
            <div style="width: 46%; text-align: left;">
              <div>Conferido por: ____________________________</div>
              <div style="margin-top: 4px;">Data: ___ / ___ / 2026</div>
            </div>
          </div>

          <div style="text-align: center; font-size: 9.5pt;">
            <div style="text-align: right; margin-bottom: 6px; font-size: 10pt;">${distrito}, aos ${agora.getDate()} de ${meses[agora.getMonth()]} de ${agora.getFullYear()}</div>
            <div style="font-weight: bold;">O Director da Escola</div>
            <div style="border-bottom: 1px solid #111; margin: 22px auto 4px; width: 45%;"></div>
            <div style="font-weight: bold;">${directorNome}</div>
            <div style="font-size: 8.5pt; font-style: italic;">/${directorCarreira}/</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderizarDeclaracao(d) {
  d = d || {};
  if (!d.aluno) d.aluno = {};
  if (!d.escola) d.escola = {};
  if (!d.disciplinas) d.disciplinas = [];
  const preview = document.getElementById('printAreaPreview');
  const safeName = (d.aluno?.nomeCompleto || d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
  const ano = d.anoLectivo || d.anoLetivo || '2026';
  const alunoId = d.aluno?.id || document.getElementById('printSelectAluno')?.value || '';

  preview.style.display = 'block';
  preview.innerHTML = `
    <div class="no-print mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span class="badge bg-success px-3 py-2"><i class="bi bi-file-earmark-check me-1"></i> Declaração Oficial com Notas A4</span>
      <div class="d-flex gap-2">
        ${alunoId ? `<button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarDocumentoOficialPdf('DECLARACAO', '${alunoId}')"><i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF (A4)</button>` : ''}
        <button class="btn btn-primary btn-sm fw-semibold" onclick="imprimirDocumentoComTitulo('Declaracao_${safeName}_${ano}')">
          <i class="bi bi-printer me-1"></i> Imprimir / Guardar em PDF
        </button>
      </div>
    </div>
    <div class="printable-document">
      ${obterHtmlDeclaracaoOficial(d)}
    </div>
  `;
}

function obterHtmlCertificadoOficial(d) {
  d = d || {};
  if (!d.aluno) d.aluno = {};
  if (!d.escola) d.escola = {};
  if (!d.disciplinas) d.disciplinas = [];
  const escolaNome = (d.escola?.nome || 'Escola Secundária de Cambine').toUpperCase();
  const escolaNomeFormatado = escolaNome.startsWith('ESCOLA') ? escolaNome : `ESCOLA SECUNDÁRIA DE ${escolaNome}`;
  const provincia = (d.escola?.provincia || 'Inhambane');
  const distrito = (d.escola?.distrito || 'Massinga');
  const directorNome = d.directorNome || 'Prof. Dr. António Costa';
  const directorCarreira = d.directorCarreira || 'Especialista de Educação';
  const chefeNome = d.chefeSecretariaNome || 'Dra. Maria Eunice';
  const chefeCarreira = d.chefeSecretariaCarreira || 'Técnica Profissional';

  const alunoNome = (d.aluno?.nomeCompleto || d.aluno?.nome || 'GRAÇA MONDLANE MONDLANE').toUpperCase();
  const sexo = ((d.aluno?.genero || 'F').toUpperCase().startsWith('F')) ? 'Feminino' : 'Masculino';
  const pai = d.aluno?.pai || 'Eduardo Mondlane Jr.';
  const mae = d.aluno?.mae || 'Janet Mondlane';
  const alunoDistrito = d.aluno?.distrito || 'Cidade de Maputo';
  const alunoProvincia = d.aluno?.provincia || 'Maputo';
  const anoLectivo = d.anoLectivo || d.anoLetivo || '2026';
  const grauClasse = d.grauAno || d.aluno?.turma?.grau_ano || d.aluno?.classe || '10ª Classe';
  const area = d.area || d.aluno?.turma?.area || d.aluno?.area || 'Geral';
  const matricula = d.aluno?.matricula || 'MAT-2026-1006';

  let diaNasc = '09', mesNasc = 'Julho', anoNasc = '2008';
  if (d.aluno?.data_nascimento) {
    const dt = new Date(d.aluno.data_nascimento);
    if (!isNaN(dt.getTime())) {
      diaNasc = String(dt.getDate()).padStart(2, '0');
      const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
      mesNasc = meses[dt.getMonth()];
      anoNasc = String(dt.getFullYear());
    }
  }

  // Disciplinas do plano curricular da classe e secção do aluno
  const disciplinasDoPlano = obterDisciplinasPlanoCurricularAlunoDoc(d);
  const notasMap = {};
  disciplinasDoPlano.forEach(item => {
    const n = (item.disciplina || item.nome || '').trim();
    const v = item.notaFinal !== undefined ? item.notaFinal : (item.mediaFinal !== undefined ? item.mediaFinal : item.media_anual);
    if (n) {
      notasMap[n] = v;
    }
  });

  const obterNotaValor = (nomeDisc) => {
    for (const [ch, vl] of Object.entries(notasMap)) {
      if (matchDisciplinaDocumento(nomeDisc, ch)) {
        if (vl !== null && vl !== undefined && vl !== '-' && vl !== '---' && !isNaN(vl)) {
          const num = Number(vl);
          if (num > 0) {
            return Number.isInteger(num) ? String(num) : num.toFixed(1);
          }
        }
      }
    }
    return null;
  };

  const nomesCurricularesCert = disciplinasDoPlano.map(item => obterNomeCompletoDisciplina(item.nome || item.disciplina || '')).filter(Boolean);
  const meioCert = Math.ceil(nomesCurricularesCert.length / 2);
  const colEsquerda = nomesCurricularesCert.slice(0, meioCert);
  const colDireita = nomesCurricularesCert.slice(meioCert);

  const renderLinhaCert = (disc) => {
    const nota = obterNotaValor(disc);
    const notaTexto = nota !== null ? `( ${nota} ) valores` : `( --- )`;
    return `
      <div style="display: flex; justify-content: flex-start; align-items: baseline; margin-bottom: 5px; font-size: 11.5pt; line-height: 1.35; width: 100%; max-width: 100%; box-sizing: border-box; overflow: hidden;">
        <span style="min-width: 0; overflow-wrap: break-word;">${disc}</span>
        <span style="display: inline-block; width: 22px; min-width: 10px; border-bottom: 1px dotted #555; margin: 0 6px; flex-shrink: 1;"></span>
        <span style="font-weight: bold; white-space: nowrap; flex-shrink: 0;">${notaTexto}</span>
      </div>
    `;
  };

  let mediaGlobalVal = null;
  if (d.mediaGlobal !== undefined && d.mediaGlobal !== null && d.mediaGlobal !== '-' && d.mediaGlobal !== '---' && !isNaN(Number(d.mediaGlobal))) {
    mediaGlobalVal = Math.round(Number(d.mediaGlobal));
  } else if (d.mediaGeral !== undefined && d.mediaGeral !== null && d.mediaGeral !== '-' && d.mediaGeral !== '---' && !isNaN(Number(d.mediaGeral))) {
    mediaGlobalVal = Math.round(Number(d.mediaGeral));
  }
  const mediaGlobalStr = mediaGlobalVal !== null ? `( ${mediaGlobalVal} ) Valores` : `( --- )`;
  const pautaNum = d.pautaNumero || '01';
  const termoExames = d.termoExames || '124';

  const agora = new Date();
  const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
  const diaAtual = agora.getDate();
  const mesAtual = meses[agora.getMonth()];
  const anoAtual = agora.getFullYear();

  const codAuth = d.codigoAutenticidade || d.codigo_autenticidade || `CERT-MZ-5001234567-${matricula}-${anoLectivo}`;
  let qrRaw = d.qrcodeData || d.qrcode_data;
  if (qrRaw && typeof qrRaw === 'string') {
    qrRaw = qrRaw.replace(/http:\/\/139\.84\.226\.46(:\d+)?/g, 'https://sigesaas.duckdns.org')
                 .replace(/https:\/\/139\.84\.226\.46(:\d+)?/g, 'https://sigesaas.duckdns.org');
  }
  const baseUrlCert = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') ? window.location.origin : 'https://sigesaas.duckdns.org';
  const qrSrc = qrRaw || `https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=${encodeURIComponent(baseUrlCert + '/verificar-certificado.html?codigo=' + codAuth)}`;

  return `
    <div class="documento-a4-pagina-unica" style="width: 100%; max-width: 210mm; min-height: 282mm; padding: 4mm 6mm; margin: 0 auto; box-sizing: border-box; overflow: hidden; background: #fff; font-family: 'Times New Roman', Times, serif; position: relative; page-break-inside: avoid; page-break-after: always;">
      <div class="borda-ornamental-certificado" style="border: 6px double #111; padding: 7mm 9mm; width: 100%; max-width: 100%; min-height: 272mm; box-sizing: border-box; overflow: hidden; position: relative; display: flex; flex-direction: column; justify-content: space-between;">
        <img src="/img/emblema-mocambique.png" class="marca-dagua-emblema" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 280px; height: 280px; opacity: 0.08; pointer-events: none; z-index: 0;" alt="Marca d'Água">

        <!-- Cabeçalho Oficial do Certificado -->
        <div style="text-align: center; position: relative; z-index: 1; margin-bottom: 6mm;">
          <img src="/img/emblema-mocambique.png" style="width: 44px; height: 44px; margin-bottom: 2px; object-fit: contain;" alt="Emblema Nacional">
          <div style="font-size: 11pt; font-weight: bold; text-transform: uppercase;">REPÚBLICA DE MOÇAMBIQUE</div>
          <div style="font-size: 10pt; font-weight: bold; text-transform: uppercase;">MINISTÉRIO DA EDUCAÇÃO E CULTURA</div>
          <div style="font-size: 8.5pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">INSTITUTO NACIONAL DE EXAMES, CERTIFICAÇÃO E EQUIVALÊNCIA</div>
          <div style="font-size: 9.5pt; margin-top: 2px;"><u>a) ${escolaNomeFormatado}</u></div>
          <div style="font-size: 13pt; font-weight: bold; text-transform: uppercase; margin-top: 3px; letter-spacing: 0.8px; border-bottom: 1.5px solid #111; display: inline-block; padding-bottom: 2px;">CERTIFICADO DE HABILITAÇÕES</div>
        </div>

        <!-- Texto Declarativo Oficial do Chefe de Secretaria -->
        <div style="position: relative; z-index: 1; flex: 1; width: 100%; max-width: 100%; box-sizing: border-box;">
          <p style="text-align: justify; font-size: 10.5pt; line-height: 1.45; margin: 0 0 8px 0; text-indent: 20px;">
            b) <strong>${chefeNome}</strong>, <em>/${chefeCarreira}/</em>, Chefe da secretaria da <strong>${escolaNomeFormatado}</strong>, distrito de <strong>${distrito}</strong>, província de <strong>${provincia}</strong>, CERTIFICO em cumprimento do despacho exarado em requerimento que fica arquivado nesta secretaria que <strong>${alunoNome}</strong>, do Sexo <strong>${sexo}</strong>, natural de <strong>${alunoDistrito}</strong>, distrito de <strong>${alunoDistrito}</strong>, província de <strong>${alunoProvincia}</strong>, nascido no dia <strong>${diaNasc} de ${mesNasc} de ${anoNasc}</strong>, filho/a de <strong>${pai}</strong> e de <strong>${mae}</strong>, concluiu nesta escola como aluno c) <strong>Interno</strong>, em <strong>Dezembro de ${anoLectivo}</strong>, a <strong>${grauClasse}</strong> na área de <strong>${area}</strong>, tendo obtido os seguintes resultados:
          </p>

          <!-- Grelha de Disciplinas contida rigorosamente dentro das bordas duplas -->
          <div style="display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); column-gap: 16px; margin: 6px 0; width: 100%; max-width: 100%; box-sizing: border-box;">
            <div style="min-width: 0; overflow: hidden;">
              ${colEsquerda.map(renderLinhaCert).join('')}
            </div>
            <div style="min-width: 0; overflow: hidden;">
              ${colDireita.map(renderLinhaCert).join('')}
            </div>
          </div>

          <div style="text-align: center; font-weight: bold; font-size: 11pt; color: #b91c1c; margin: 6px 0;">
            Média Global: ${mediaGlobalStr}
          </div>

          <p style="font-size: 10pt; line-height: 1.4; margin: 6px 0; text-align: justify;">
            Os resultados constam da pauta nº <strong>${pautaNum}</strong> e do livro de Termo de Exames nº <strong>${termoExames}</strong>, código do aluno <strong>${matricula}</strong>.<br>
            E, por ser verdade passo o presente certificado que assino e autentico a tinta de óleo/selo branco em uso neste Estabelecimento de Ensino.
          </p>
        </div>

        <!-- Local, Datação e Assinaturas dentro da moldura -->
        <div style="position: relative; z-index: 1; margin-top: auto; padding-bottom: 3mm; width: 100%; box-sizing: border-box;">
          <div style="text-align: center; font-size: 9.5pt; margin-bottom: 6px;">
            ${distrito}, aos ${diaAtual} de ${mesAtual} de ${anoAtual}
          </div>

          <div style="display: flex; justify-content: space-between; align-items: flex-end; font-size: 9pt; width: 100%; box-sizing: border-box;">
            <div style="width: 34%; text-align: left;">
              <div style="font-size: 8pt; white-space: nowrap;">Extrai: _______&nbsp;&nbsp;Conferi: _______</div>
              <div style="margin-top: 6px; text-align: center;">
                <div style="font-weight: bold;">O Chefe da Secretaria</div>
                <div style="border-bottom: 1px solid #111; margin: 14px auto 3px; width: 85%;"></div>
                <div style="font-weight: bold;">${chefeNome}</div>
                <div style="font-size: 8.5pt; font-style: italic;">/${chefeCarreira}/</div>
              </div>
            </div>

            <div style="width: 28%; text-align: center;">
              <div style="margin-top: 4px;">
                <a href="/verificar-certificado.html?codigo=${encodeURIComponent(codAuth)}" target="_blank" title="Verificar Autenticidade Digital" style="text-decoration: none; color: inherit;">
                  <img src="${qrSrc}" style="width: 46px; height: 46px; margin: 0 auto; display: block;" alt="QR Code">
                  <div style="font-size: 6.5pt; color: #444; margin-top: 2px; word-break: break-all;">${codAuth}</div>
                </a>
              </div>
            </div>

            <div style="width: 34%; text-align: center;">
              <div style="font-weight: bold;">O Director da Escola</div>
              <div style="border-bottom: 1px solid #111; margin: 24px auto 3px; width: 85%;"></div>
              <div style="font-weight: bold;">${directorNome}</div>
              <div style="font-size: 8.5pt; font-style: italic;">/${directorCarreira}/</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderizarCertificado(d) {
  d = d || {};
  if (!d.aluno) d.aluno = {};
  if (!d.escola) d.escola = {};
  if (!d.disciplinas) d.disciplinas = [];
  const preview = document.getElementById('printAreaPreview');
  const safeName = (d.aluno?.nomeCompleto || d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
  const ano = d.anoLectivo || d.anoLetivo || '2026';
  const alunoId = d.aluno?.id || document.getElementById('printSelectAluno')?.value || '';
  const codAuth = d.codigoAutenticidade || d.codigo_autenticidade || `CERT-MZ-5001234567-${d.aluno?.matricula || 'MAT-2026-1006'}-${ano}`;

  preview.style.display = 'block';
  preview.innerHTML = `
    <div class="no-print mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span class="badge bg-primary px-3 py-2"><i class="bi bi-award-fill me-1"></i> Certificado de Habilitações Oficial A4</span>
      <div class="d-flex gap-2">
        <a href="/verificar-certificado.html?codigo=${encodeURIComponent(codAuth)}" target="_blank" class="btn btn-outline-success btn-sm fw-semibold">
          <i class="bi bi-shield-check me-1"></i> Validar Autenticidade
        </a>
        ${alunoId ? `<button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarDocumentoOficialPdf('CERTIFICADO', '${alunoId}')"><i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF (A4)</button>` : ''}
        <button class="btn btn-primary btn-sm fw-semibold" onclick="imprimirDocumentoComTitulo('Certificado_${safeName}_${ano}')">
          <i class="bi bi-printer me-1"></i> Imprimir / Guardar em PDF
        </button>
      </div>
    </div>
    <div class="printable-document">
      ${obterHtmlCertificadoOficial(d)}
    </div>
  `;
}

function renderizarRecibo(d) {
  d = d || {};
  if (!d.aluno) d.aluno = {};
  if (!d.escola) d.escola = {};
  if (!d.pagamento) d.pagamento = {};
  const preview = document.getElementById('printAreaPreview');
  const safeName = (d.aluno?.nomeCompleto || d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
  const carimboDataHora = d.carimboDataHora || (new Date().toLocaleDateString('pt-PT') + ' ' + new Date().toLocaleTimeString('pt-PT'));

  preview.style.display = 'block';
  preview.innerHTML = `
    <div class="text-center border-bottom pb-3 mb-3">
      <h6 class="fw-bold mb-1">${d.escola.nome || 'Escola'}</h6>
      <p class="text-muted small mb-0">NUIT: ${d.escola.nif_cnpj || '-'} | Telefone: ${d.escola.telefone || '-'}</p>
      <h5 class="mt-2 fw-bold text-success text-uppercase">RECIBO DE PAGAMENTO DE PROPINAS</h5>
      <span class="badge bg-light text-dark border">Recibo Nº: ${d.pagamento.recibo_numero || 'REC-2026-001'}</span>
    </div>

    <div class="table-responsive">
      <table class="table table-bordered table-sm small mb-4">
        <tr><th class="bg-light w-35">Aluno:</th><td>${d.aluno.nome || '-'} (Matrícula: ${d.aluno.matricula || '-'})</td></tr>
        <tr><th class="bg-light">Turma:</th><td>${d.aluno.turma?.nome || '-'}</td></tr>
        <tr><th class="bg-light">Descrição da Taxa:</th><td>${d.pagamento.descricao || '-'}</td></tr>
        <tr><th class="bg-light">Mês de Referência:</th><td><code>${d.pagamento.mes_referencia || '-'}</code></td></tr>
        <tr><th class="bg-light">Valor Pago:</th><td class="fw-bold text-success fs-6">${formatarMoeda(d.pagamento.valor || 0)}</td></tr>
        <tr><th class="bg-light">Forma de Liquidação:</th><td>${d.pagamento.metodo_pagamento || 'Depósito / Transferência'}</td></tr>
        <tr><th class="bg-light">Data do Pagamento:</th><td>${new Date(d.pagamento.pago_em || Date.now()).toLocaleDateString('pt-PT')}</td></tr>
      </table>
    </div>

    <!-- Carimbo com Data e Hora Oficial -->
    <div class="alert alert-light border small text-muted text-center py-2 mb-4">
      <i class="bi bi-clock-history me-1 text-primary"></i>
      Processado por Computador aos <strong>${carimboDataHora}</strong> | Autenticação SIGE
    </div>

    <div class="row text-center pt-3 border-top small">
      <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">A Secretaria / Tesouraria</p></div>
      <div class="col-6"><p class="mb-0 border-top pt-2 mx-4">O Depositante</p></div>
    </div>

    <div class="text-center mt-4 no-print">
      <button class="btn btn-primary" onclick="imprimirDocumentoComTitulo('Recibo_${safeName}_${d.pagamento.mes_referencia || '2026'}')">
        <i class="bi bi-printer me-2"></i> Imprimir Recibo
      </button>
    </div>
  `;
}

function renderizarFichaAluno(d) {
  d = d || {};
  if (!d.aluno) d.aluno = {};
  if (!d.escola) d.escola = {};
  const preview = document.getElementById('printAreaPreview');
  const safeName = (d.aluno?.nomeCompleto || d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
  const carimboDataHora = d.carimboDataHora || (new Date().toLocaleDateString('pt-PT') + ' ' + new Date().toLocaleTimeString('pt-PT'));

  const alunoId = d.aluno?.id || document.getElementById('printSelectAluno')?.value || '';
  const classeNome = d.aluno.classe || d.aluno.turma?.grau_ano || '10ª Classe';
  const areaNome = d.aluno.area || d.aluno.turma?.area || 'Ensino Geral';
  const anoLetivo = d.aluno.ano_letivo || d.escola?.ano_letivo || '2026';
  const turnoNome = d.aluno.turno || d.aluno.turma?.turno || 'Manhã';
  const turmaNome = d.aluno.turma?.nome || '-';
  const disciplinas = Array.isArray(d.aluno.disciplinas) ? d.aluno.disciplinas : [];

  let disciplinasRowsHtml = '';
  if (disciplinas.length > 0) {
    disciplinasRowsHtml = disciplinas.map((disc, idx) => `
      <tr>
        <td style="text-align: center; border: 1px solid #000; padding: 4px 6px;">${idx + 1}</td>
        <td style="text-align: center; border: 1px solid #000; padding: 4px 6px; font-weight: bold;">${disc.codigo || '-'}</td>
        <td style="border: 1px solid #000; padding: 4px 6px;">${disc.nome || disc.disciplina || '-'}</td>
        <td style="text-align: center; border: 1px solid #000; padding: 4px 6px;">${disc.carga_horaria || disc.carga || '3 h/sem'}</td>
      </tr>
    `).join('');
  } else {
    disciplinasRowsHtml = `<tr><td colspan="4" style="text-align: center; border: 1px solid #000; padding: 6px; color: #666;">Sem disciplinas associadas ao plano curricular.</td></tr>`;
  }

  preview.style.display = 'block';
  preview.innerHTML = `
    <div class="no-print mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span class="badge bg-primary px-3 py-2"><i class="bi bi-person-badge me-1"></i> Ficha Biográfica do Aluno (Oficial A4)</span>
      <div class="d-flex gap-2">
        ${alunoId ? `<button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarDocumentoOficialPdf('FICHA', '${alunoId}')"><i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF (A4)</button>` : ''}
        ${alunoId ? `<button class="btn btn-outline-primary btn-sm fw-semibold" onclick="descarregarDocxCentral()"><i class="bi bi-file-earmark-word me-1"></i> Descarregar Word (DOCX)</button>` : ''}
        <button class="btn btn-primary btn-sm fw-semibold" onclick="imprimirDocumentoComTitulo('Ficha_${safeName}_${anoLetivo}')">
          <i class="bi bi-printer me-1"></i> Imprimir / Guardar em PDF
        </button>
      </div>
    </div>

    <div class="printable-document" style="font-family: 'Times New Roman', Times, serif; color: #000; max-width: 800px; margin: 0 auto; background: #fff; padding: 20px 25px; border: 1px solid #e0e0e0;">
      <!-- CABEÇALHO OFICIAL -->
      <div style="text-align: center; margin-bottom: 12px; line-height: 1.25;">
        <div style="font-size: 11pt; font-weight: bold; text-transform: uppercase;">REPÚBLICA DE MOÇAMBIQUE</div>
        <div style="font-size: 10pt; font-weight: bold; text-transform: uppercase;">GOVERNO DA PROVÍNCIA DE ${d.escola.provincia || 'INHAMBANE'}</div>
        <div style="font-size: 9.5pt; text-transform: uppercase;">SERVIÇO DISTRITAL DE EDUCAÇÃO, JUVENTUDE E TECNOLOGIA DE ${d.escola.distrito || 'MASSINGA'}</div>
        <div style="font-size: 12pt; font-weight: bold; margin-top: 4px; text-transform: uppercase;">${d.escola.nome || 'ESCOLA SECUNDÁRIA'}</div>
        <div style="font-size: 12pt; font-weight: bold; margin-top: 6px; letter-spacing: 0.5px; border-top: 1.5px solid #000; border-bottom: 1.5px solid #000; padding: 3px 0;">
          FICHA BIOGRÁFICA DO ALUNO
        </div>
        <div style="font-size: 9.5pt; margin-top: 3px; font-weight: bold;">
          MATRÍCULA Nº: ${d.aluno.matricula || '-'} &nbsp;|&nbsp; ANO LECTIVO: ${anoLetivo}
        </div>
      </div>

      <!-- DADOS BIOGRÁFICOS E DE ENQUADRAMENTO ACADÉMICO -->
      <table style="width: 100%; border-collapse: collapse; font-size: 9.5pt; margin-bottom: 12px; border: 1px solid #000;">
        <tr>
          <td style="border: 1px solid #000; padding: 3px 6px; width: 22%; background-color: #f8f9fa; font-weight: bold;">Nome Completo:</td>
          <td style="border: 1px solid #000; padding: 3px 6px; width: 43%; font-weight: bold;">${d.aluno.nome || '-'}</td>
          <td style="border: 1px solid #000; padding: 3px 6px; width: 15%; background-color: #f8f9fa; font-weight: bold;">Apelido:</td>
          <td style="border: 1px solid #000; padding: 3px 6px; width: 20%;">${d.aluno.apelido || '-'}</td>
        </tr>
        <tr>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Data de Nascimento:</td>
          <td style="border: 1px solid #000; padding: 3px 6px;">${d.aluno.data_nascimento ? new Date(d.aluno.data_nascimento).toLocaleDateString('pt-PT') : '-'}</td>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Género:</td>
          <td style="border: 1px solid #000; padding: 3px 6px;">${d.aluno.genero === 'M' ? 'Masculino' : (d.aluno.genero === 'F' ? 'Feminino' : (d.aluno.genero || '-'))}</td>
        </tr>
        <tr>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Documento (BI / DIR):</td>
          <td style="border: 1px solid #000; padding: 3px 6px;">${d.aluno.tipo_documento || 'BI'}: ${d.aluno.numero_documento || '-'}</td>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">NUIT:</td>
          <td style="border: 1px solid #000; padding: 3px 6px;">${d.aluno.nuit || '-'}</td>
        </tr>
        <tr>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Naturalidade / Província:</td>
          <td style="border: 1px solid #000; padding: 3px 6px;">${d.aluno.distrito || '-'} / ${d.aluno.provincia || '-'}</td>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Filiação (Pai):</td>
          <td style="border: 1px solid #000; padding: 3px 6px;">${d.aluno.pai || '-'}</td>
        </tr>
        <tr>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Filiação (Mãe):</td>
          <td style="border: 1px solid #000; padding: 3px 6px;">${d.aluno.mae || '-'}</td>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Encarregado:</td>
          <td style="border: 1px solid #000; padding: 3px 6px;">${d.aluno.nome_responsavel || '-'}${d.aluno.contato_responsavel ? ' (' + d.aluno.contato_responsavel + ')' : ''}</td>
        </tr>
        <tr>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Classe Actual:</td>
          <td style="border: 1px solid #000; padding: 3px 6px; font-weight: bold;">${classeNome}</td>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Área / Secção:</td>
          <td style="border: 1px solid #000; padding: 3px 6px; font-weight: bold;">${areaNome}</td>
        </tr>
        <tr>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Turma Actual:</td>
          <td style="border: 1px solid #000; padding: 3px 6px;">${turmaNome}</td>
          <td style="border: 1px solid #000; padding: 3px 6px; background-color: #f8f9fa; font-weight: bold;">Turno:</td>
          <td style="border: 1px solid #000; padding: 3px 6px;">${turnoNome}</td>
        </tr>
      </table>

      <!-- PLANO CURRICULAR E DISCIPLINAS DA CLASSE -->
      <div style="font-size: 10pt; font-weight: bold; text-transform: uppercase; margin-bottom: 4px; text-align: left; border-bottom: 1px solid #000; padding-bottom: 2px;">
        Plano Curricular & Disciplinas da Classe (${classeNome} — ${areaNome})
      </div>
      <table style="width: 100%; border-collapse: collapse; font-size: 9pt; margin-bottom: 12px; border: 1px solid #000;">
        <thead>
          <tr style="background-color: #f0f0f0;">
            <th style="border: 1px solid #000; padding: 4px 6px; width: 8%; text-align: center;">Nº</th>
            <th style="border: 1px solid #000; padding: 4px 6px; width: 14%; text-align: center;">Código</th>
            <th style="border: 1px solid #000; padding: 4px 6px; width: 56%; text-align: left;">Disciplina Curricular</th>
            <th style="border: 1px solid #000; padding: 4px 6px; width: 22%; text-align: center;">Carga Horária</th>
          </tr>
        </thead>
        <tbody>
          ${disciplinasRowsHtml}
        </tbody>
      </table>

      <!-- ASSINATURAS E REGISTO -->
      <div style="margin-top: 15px; font-size: 9.5pt;">
        <table style="width: 100%; border-collapse: collapse; text-align: center; border: none;">
          <tr>
            <td style="width: 50%; padding-top: 25px; border: none;">
              ___________________________________________<br>
              <strong>O(A) Responsável do Registo Académico</strong>
            </td>
            <td style="width: 50%; padding-top: 25px; border: none;">
              ___________________________________________<br>
              <strong>O(A) Director(a) da Escola</strong>
            </td>
          </tr>
        </table>
      </div>

      <!-- CARIMBO DE EMISSÃO -->
      <div style="margin-top: 15px; font-size: 8pt; text-align: center; color: #555; border-top: 1px dashed #ccc; padding-top: 4px;">
        Registo Informatizado emitido aos <strong>${carimboDataHora}</strong> | Sistema Integrado de Gestão Escolar (SIGE)
      </div>
    </div>
  `;
}

function renderizarLoteImpressao(lista) {
  const docs = Array.isArray(lista) ? lista : (lista?.documentos || []);
  const tipoDoc = lista?.tipoDocumento || 'DOCUMENTO';
  const preview = document.getElementById('printAreaPreview');
  preview.style.display = 'block';
  preview.innerHTML = `
    <div class="no-print mb-4 p-3 bg-light border rounded d-flex justify-content-between align-items-center">
      <div>
        <strong class="text-primary fs-5">Lote Processado: ${docs.length} Documentos</strong>
        <span class="d-block small text-muted">Cada documento possui formatação A4 oficial e quebra de página automática.</span>
      </div>
      <button class="btn btn-primary" onclick="window.print()">
        <i class="bi bi-printer me-2"></i> Imprimir Todo o Lote
      </button>
    </div>
    ${docs.map((item, i) => {
      if (tipoDoc === 'CERTIFICADO' || (item.titulo && item.titulo.includes('CERTIFICADO'))) {
        return `<div class="mb-4" style="page-break-after: always; break-after: page; page-break-inside: avoid;">${obterHtmlCertificadoOficial(item)}</div>`;
      } else if (tipoDoc === 'DECLARACAO' || (item.titulo && (item.titulo.includes('DECLARA') || item.titulo.includes('DECLARAÇÃO')))) {
        return `<div class="mb-4" style="page-break-after: always; break-after: page; page-break-inside: avoid;">${obterHtmlDeclaracaoOficial(item)}</div>`;
      } else if (tipoDoc === 'BOLETIM' || (item.titulo && item.titulo.includes('BOLETIM'))) {
        return `<div class="mb-4" style="page-break-after: always; break-after: page; page-break-inside: avoid;">${obterHtmlBoletimOficial(item)}</div>`;
      }
      return `
        <div class="printable-document mb-5 pb-5 border-bottom" style="page-break-after: always; page-break-inside: avoid;">
          <div class="text-center border-bottom pb-3 mb-3">
            <h6 class="fw-bold mb-1">REPÚBLICA DE MOÇAMBIQUE</h6>
            <h5 class="fw-bold text-primary mb-1">${item.titulo || 'DOCUMENTO ESCOLAR OFICIAL'}</h5>
            <small class="text-muted">Aluno: ${item.aluno?.nome} | Matrícula: ${item.aluno?.matricula}</small>
          </div>
          <div class="p-3 small">
            ${item.conteudoHtml || '<p>Documento oficial emitido em lote pelo SIGE.</p>'}
          </div>
        </div>
      `;
    }).join('')}
  `;
}

function imprimirDocumentoComTitulo(titulo) {
  const originalTitle = document.title;
  document.title = titulo;
  window.print();
  document.title = originalTitle;
}


// Compatibilidade retroativa:
const PLANO_CURRICULAR_MINEDH_FRONTEND = PLANO_CURRICULAR_MEC_FRONTEND;
