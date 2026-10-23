// ==================== EXPORTAÇÃO E DOWNLOAD EM PDF (CADERNETA, PAUTA, ACTA E DOCUMENTOS) ====================
function inicializarPatchHtml2Pdf() {
  if (!window.html2pdf || window.__html2pdfPatched) return;
  try {
    const dummy = window.html2pdf();
    const proto = Object.getPrototypeOf(dummy);
    if (proto && proto.toContainer) {
      const origToContainer = proto.toContainer;
      proto.toContainer = function() {
        const self = this;
        return origToContainer.call(this).then(() => {
          if (self.prop && self.prop.overlay) {
            self.prop.overlay.style.opacity = '1';
            self.prop.overlay.style.left = '0px';
            self.prop.overlay.style.top = '0px';
            self.prop.overlay.style.visibility = 'visible';
            self.prop.overlay.style.backgroundColor = '#ffffff';
            self.prop.overlay.style.zIndex = '999999';
          }
          if (self.prop && self.prop.container) {
            self.prop.container.style.opacity = '1';
            self.prop.container.style.visibility = 'visible';
            self.prop.container.style.backgroundColor = '#ffffff';
          }
        });
      };
      window.__html2pdfPatched = true;
    }
  } catch (e) {
    console.warn('Patch html2pdf:', e);
  }
}

async function exportarElementoParaPdf(elementoOuId, filename, orientation = 'landscape') {
  const el = typeof elementoOuId === 'string' ? document.getElementById(elementoOuId) : elementoOuId;
  if (!el) {
    alert('Documento não disponível para exportação');
    return;
  }

  inicializarPatchHtml2Pdf();

  let containerTemporario = null;
  let alvoParaRender = el;

  const bgOriginal = el.style.backgroundColor;
  const colorOriginal = el.style.color;
  const displayOriginal = el.style.display;
  let foiExibido = false;

  try {
    const estaOculto = (el.offsetParent === null) || displayOriginal === 'none' || (window.getComputedStyle && window.getComputedStyle(el).display === 'none');
    if (estaOculto) {
      containerTemporario = el.cloneNode(true);
      containerTemporario.style.position = 'fixed';
      containerTemporario.style.left = '-9999px';
      containerTemporario.style.top = '0';
      containerTemporario.style.width = '1000px';
      containerTemporario.style.display = 'block';
      containerTemporario.style.visibility = 'visible';
      containerTemporario.style.backgroundColor = '#ffffff';
      containerTemporario.style.color = '#000000';
      document.body.appendChild(containerTemporario);
      alvoParaRender = containerTemporario;
    } else {
      el.style.backgroundColor = '#ffffff';
      el.style.color = '#000000';
    }
  } catch (errCheck) {
    console.warn('Verificação de visibilidade para exportação PDF:', errCheck);
  }

  const safeFilename = filename.toLowerCase().endsWith('.pdf') ? filename : `${filename}.pdf`;

  if (window.html2pdf) {
    const isPortrait = orientation === 'portrait';
    const opt = {
      margin: isPortrait ? [6, 8, 6, 8] : [5, 5, 5, 5],
      filename: safeFilename,
      image: { type: 'jpeg', quality: 0.98 },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] },
      html2canvas: {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
        ignoreElements: (e) => e.classList?.contains('no-print') || e.tagName === 'BUTTON',
        onclone: (clonedDoc) => {
          // Forçar estritamente Times New Roman e proporções oficiais sem cortes
          const styleClone = clonedDoc.createElement('style');
          styleClone.textContent = `
            * {
              font-family: 'Times New Roman', Times, Georgia, serif !important;
            }
            body, .printable-document, .documento-a4-pagina-unica, .documento-boletim-oficial {
              font-family: 'Times New Roman', Times, Georgia, serif !important;
              color: #000000 !important;
              background-color: #ffffff !important;
            }
            table {
              border-collapse: collapse !important;
              width: 100% !important;
            }
            th, td {
              font-family: 'Times New Roman', Times, Georgia, serif !important;
            }
          `;
          clonedDoc.head.appendChild(styleClone);

          // Remover ícones e botões nos documentos exportados (sem icons)
          const elementosRemover = clonedDoc.querySelectorAll('i, svg, .bi, [class*="bi-"], [class^="bi-"], .fa, [class*="fa-"], [class^="fa-"], button, .btn, .no-print');
          elementosRemover.forEach(elRem => elRem.remove());

          const overlays = clonedDoc.querySelectorAll('.html2pdf__overlay');
          overlays.forEach(ov => {
            ov.style.opacity = '1';
            ov.style.visibility = 'visible';
            ov.style.left = '0px';
            ov.style.top = '0px';
          });
          const containers = clonedDoc.querySelectorAll('.html2pdf__container');
          containers.forEach(ct => {
            ct.style.opacity = '1';
            ct.style.visibility = 'visible';
            ct.style.backgroundColor = '#ffffff';
          });
          const docs = clonedDoc.querySelectorAll('.printable-document, .documento-a4-pagina-unica, table, .table-responsive');
          docs.forEach(doc => {
            doc.style.opacity = '1';
            doc.style.visibility = 'visible';
            doc.style.backgroundColor = '#ffffff';
            doc.style.overflow = 'visible';
            doc.style.maxWidth = 'none';
          });
        }
      },
      jsPDF: {
        unit: 'mm',
        format: 'a4',
        orientation: orientation
      }
    };

    try {
      await window.html2pdf().set(opt).from(alvoParaRender).save();
    } catch (err) {
      console.error('Erro ao gerar PDF com html2pdf:', err);
      window.print();
    } finally {
      if (containerTemporario && containerTemporario.parentNode) {
        containerTemporario.remove();
      }
      el.style.backgroundColor = bgOriginal;
      el.style.color = colorOriginal;
      if (foiExibido) {
        el.style.display = displayOriginal;
      }
    }
  } else {
    if (containerTemporario && containerTemporario.parentNode) {
      containerTemporario.remove();
    }
    el.style.backgroundColor = bgOriginal;
    el.style.color = colorOriginal;
    if (foiExibido) {
      el.style.display = displayOriginal;
    }
    window.print();
  }
}

async function obterTurmaAtivaOuPrimeira(turmaIdExplicit = null) {
  let turmaId = turmaIdExplicit
    || document.getElementById('pautaTurmaSelect')?.value
    || document.getElementById('dtTurmaSelect')?.value
    || document.getElementById('printSelectTurma')?.value;
  if (turmaId) return turmaId;
  const selects = ['pautaTurmaSelect', 'dtTurmaSelect', 'printSelectTurma'];
  for (const id of selects) {
    const sel = document.getElementById(id);
    if (sel && sel.options) {
      for (const opt of sel.options) {
        if (opt.value && opt.value !== 'TODOS') return opt.value;
      }
    }
  }
  try {
    const res = await apiFetch('/api/v1/escola-admin/turmas');
    if (res?.data?.length > 0) return res.data[0].id;
  } catch (_) {}
  return null;
}

async function obterAlocacaoAtivaOuPrimeira() {
  if (state.alocacaoAtualId) return state.alocacaoAtualId;
  const sel = document.getElementById('cadernetaAlocacaoSelect') || document.getElementById('profTurmaSelect');
  if (sel && sel.value) {
    state.alocacaoAtualId = sel.value;
    return sel.value;
  }
  if (sel && sel.options) {
    for (const opt of sel.options) {
      if (opt.value) {
        state.alocacaoAtualId = opt.value;
        return opt.value;
      }
    }
  }
  try {
    const res = await apiFetch('/api/v1/professores/minhas-turmas');
    const lista = res?.data || res || [];
    if (Array.isArray(lista) && lista.length > 0) {
      state.alocacaoAtualId = lista[0].id;
      return lista[0].id;
    }
  } catch (_) {}
  return null;
}

async function exportarPautaGeralExcel(turmaIdExplicit = null, anoExplicit = null, orientacaoExplicit = null) {
  const turmaId = await obterTurmaAtivaOuPrimeira(turmaIdExplicit);
  if (!turmaId) return;
  const ano = anoExplicit || document.getElementById('pautaAnoSelect')?.value || document.getElementById('pautaAnoFiltro')?.value || '2026';
  const orientacao = orientacaoExplicit || document.getElementById('pautaOrientacaoSelect')?.value || 'landscape';
  await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/export-xlsx?anoLetivo=${ano}&orientacao=${orientacao}`, `Pauta_Geral_Turma_${ano}.xlsx`);
}

function imprimirPautaGeralOficial() {
  const orientacao = document.getElementById('pautaOrientacaoSelect')?.value || 'landscape';
  document.body.classList.remove('print-orientacao-landscape', 'print-orientacao-portrait');
  document.body.classList.add(orientacao === 'landscape' ? 'print-orientacao-landscape' : 'print-orientacao-portrait');
  window.print();
}

async function descarregarCadernetaPdf() {
  const alocId = await obterAlocacaoAtivaOuPrimeira();
  if (!alocId) return;
  await downloadFicheiroBinario(`/api/v1/professores/caderneta/${alocId}/pdf`, `Caderneta_Oficial_2026.pdf`);
}

async function descarregarCadernetaExcel() {
  const alocId = await obterAlocacaoAtivaOuPrimeira();
  if (!alocId) return;
  await downloadFicheiroBinario(`/api/v1/professores/caderneta/${alocId}/xlsx`, `Caderneta_Oficial_2026.xlsx`);
}

async function descarregarCadernetaDocx() {
  const alocId = await obterAlocacaoAtivaOuPrimeira();
  if (!alocId) return;
  await downloadFicheiroBinario(`/api/v1/professores/caderneta/${alocId}/docx`, `Caderneta_Oficial_2026.docx`);
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
  await descarregarCadernetaDocx();
}

async function descarregarPautaGeralPdf(turmaIdExplicit = null, orientacaoExplicit = null) {
  const turmaId = await obterTurmaAtivaOuPrimeira(turmaIdExplicit);
  const ano = document.getElementById('pautaAnoSelect')?.value || document.getElementById('pautaAnoFiltro')?.value || '2026';
  const orientacao = orientacaoExplicit || document.getElementById('pautaOrientacaoSelect')?.value || 'landscape';
  if (turmaId) {
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/pdf?anoLetivo=${ano}&orientacao=${orientacao}`, `Pauta_Geral_Turma_${ano}.pdf`);
    return;
  }
  const el = document.getElementById('containerTabelaPautaGeral') || document.getElementById('subViewPautaGeral');
  if (el) await exportarElementoParaPdf(el, `Pauta_Geral_Turma_${ano}.pdf`, orientacao);
}

async function descarregarPautaGeralDocx(turmaIdExplicit = null, orientacaoExplicit = null) {
  const turmaId = await obterTurmaAtivaOuPrimeira(turmaIdExplicit);
  if (!turmaId) return;
  const ano = document.getElementById('pautaAnoSelect')?.value || document.getElementById('pautaAnoFiltro')?.value || '2026';
  const orientacao = orientacaoExplicit || document.getElementById('pautaOrientacaoSelect')?.value || 'landscape';
  await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/docx?anoLetivo=${ano}&orientacao=${orientacao}`, `Pauta_Geral_Turma_${ano}.docx`);
}

async function descarregarActaConselhoPdf(turmaIdExplicit = null, orientacaoExplicit = null) {
  const turmaId = await obterTurmaAtivaOuPrimeira(turmaIdExplicit);
  const ano = document.getElementById('pautaAnoSelect')?.value || document.getElementById('pautaAnoFiltro')?.value || '2026';
  const orientacao = orientacaoExplicit || document.getElementById('pautaOrientacaoSelect')?.value || 'landscape';
  if (turmaId) {
    const rawSessao = localStorage.getItem('sige_acta_params_' + turmaId) || localStorage.getItem(`sige_sessao_acta_${turmaId}`) || '{}';
    let sessao = {};
    try { sessao = JSON.parse(rawSessao) || {}; } catch (e) { sessao = {}; }
    const params = new URLSearchParams({ anoLetivo: ano, orientacao: orientacao });
    Object.entries(sessao).forEach(([k, v]) => {
      if (v) params.append(k, v);
    });
    if (sessao.presidente && !params.has('presidente')) params.append('presidente', sessao.presidente);
    if (sessao.data && !params.has('data')) params.append('data', sessao.data);
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/acta-pdf?${params.toString()}`, `Acta_Conselho_Turma_${ano}.pdf`);
    return;
  }
  const el = document.getElementById('containerActaConselhoCorpo') || document.getElementById('subViewActaConselho');
  if (el) await exportarElementoParaPdf(el, `Acta_Conselho_Turma_${ano}.pdf`, orientacao);
}

async function descarregarActaConselhoDocx(turmaIdExplicit = null, orientacaoExplicit = null) {
  const turmaId = await obterTurmaAtivaOuPrimeira(turmaIdExplicit);
  if (!turmaId) return;
  const ano = document.getElementById('pautaAnoSelect')?.value || document.getElementById('pautaAnoFiltro')?.value || '2026';
  const orientacao = orientacaoExplicit || document.getElementById('pautaOrientacaoSelect')?.value || 'landscape';
  const rawSessao = localStorage.getItem('sige_acta_params_' + turmaId) || localStorage.getItem(`sige_sessao_acta_${turmaId}`) || '{}';
  let sessao = {};
  try { sessao = JSON.parse(rawSessao) || {}; } catch (e) { sessao = {}; }
  const params = new URLSearchParams({ anoLetivo: ano, orientacao: orientacao });
  Object.entries(sessao).forEach(([k, v]) => {
    if (v) params.append(k, v);
  });
  if (sessao.presidente && !params.has('presidente')) params.append('presidente', sessao.presidente);
  if (sessao.data && !params.has('data')) params.append('data', sessao.data);
  await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/acta-docx?${params.toString()}`, `Acta_Conselho_Turma_${ano}.docx`);
}

function obterNomeAlunoParaDownload(alunoId) {
  if (!alunoId || alunoId === 'TODOS') return '';
  const sel = document.getElementById('printSelectAluno');
  if (sel && sel.value === alunoId) {
    const opt = sel.options[sel.selectedIndex];
    if (opt && opt.text && !opt.text.startsWith('--')) {
      return opt.text.replace(/\s*\([^)]*\)\s*$/, '').trim();
    }
  }
  if (window.state && state.alunoAtual?.id === alunoId && state.alunoAtual?.nome) {
    return state.alunoAtual.nome.trim();
  }
  return '';
}

async function descarregarDocumentoOficialPdf(tipo, alunoOuTurmaId) {
  if (!alunoOuTurmaId) alunoOuTurmaId = await obterTurmaAtivaOuPrimeira();
  if (!alunoOuTurmaId) return;
  const t = String(tipo).toUpperCase();
  const nomeAluno = (typeof obterNomeAlunoParaDownload === 'function') ? (obterNomeAlunoParaDownload(alunoOuTurmaId) || 'Estudante') : 'Estudante';
  const ano = (window.state && state.anoLetivo) || '2026';
  const nomePadrao = `${nomeAluno} - ${ano}`;

  if (t === 'BOLETIM') {
    await downloadFicheiroBinario(`/api/v1/impressao/boletim/${alunoOuTurmaId}/pdf`, `Boletim - ${nomePadrao}.pdf`);
  } else if (t === 'DECLARACAO') {
    await downloadFicheiroBinario(`/api/v1/impressao/declaracao/${alunoOuTurmaId}/pdf`, `Declaracao - ${nomePadrao}.pdf`);
  } else if (t === 'CERTIFICADO') {
    await downloadFicheiroBinario(`/api/v1/impressao/certificado/${alunoOuTurmaId}/pdf`, `Certificado - ${nomePadrao}.pdf`);
  } else if (t === 'FICHA') {
    await downloadFicheiroBinario(`/api/v1/impressao/ficha/${alunoOuTurmaId}/pdf`, `Ficha - ${nomePadrao}.pdf`);
  } else if (t === 'RECIBO') {
    await downloadFicheiroBinario(`/api/v1/impressao/recibo/${alunoOuTurmaId}/pdf`, `Recibo - ${nomePadrao}.pdf`);
  } else if (t === 'PAUTA_TURMA' || t === 'PAUTA') {
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${alunoOuTurmaId}/pdf`, `Pauta - Turma - ${ano}.pdf`);
  }
}


function filtrarAlunosCaderneta() {
  const query = (document.getElementById('cadernetaPesquisaAluno')?.value || '').toLowerCase().trim();
  const rows = document.querySelectorAll('#tabelaCadernetaCorpo tr');
  rows.forEach(r => {
    if (!query) {
      r.style.display = '';
      return;
    }
    const texto = r.textContent.toLowerCase();
    r.style.display = texto.includes(query) ? '' : 'none';
  });
}

// SIGE — Sistema Integrado de Gestão Escolar (SaaS Multi-Tenant Moçambique)
// Lógica Principal do Frontend SPA em Português de Moçambique

// ==================== GESTÃO DE ACTUALIZAÇÕES PENDENTES DO SISTEMA (SIGE UPDATER) ====================
// Obtém o build estático injetado no HTML atualmente carregado na janela do navegador
const sigeCurrentBuild = () => {
  const meta = typeof document !== 'undefined' ? document.querySelector('meta[name="sige-build"]') : null;
  return meta ? meta.getAttribute('content') : '';
};

const sigeUpdateState = {
  pendente: false,
  detalhes: null,
  registration: null,
  workerEsperando: null,
  ultimoCheck: 0
};

// Notificar visualmente que há uma actualização pendente (mostra quando houver necessidade através da actualização feita)
window.sigeNotificarActualizacaoPendente = function(detalhes = {}) {
  sigeUpdateState.pendente = true;
  sigeUpdateState.detalhes = detalhes;

  console.log('[SIGE UPDATER] Nova versão detectada para actualização:', detalhes);

  const buildId = detalhes.novoBuild || detalhes.novaVersao || 'novo';
  
  // Respeita suspensão temporária ("Mais tarde") apenas se foi adiada há menos de 15 minutos
  let dispensado = false;
  if (typeof localStorage !== 'undefined') {
    const snoozeAte = localStorage.getItem('sige_snooze_build_' + buildId);
    if (snoozeAte && Date.now() < parseInt(snoozeAte, 10)) {
      dispensado = true;
    }
  }

  // 1. Botão na Topbar (se existir)
  const btnTopbar = document.getElementById('btnActualizacaoPendente');
  if (btnTopbar) {
    btnTopbar.classList.remove('d-none');
    btnTopbar.title = 'Nova actualização disponível. Clique para actualizar.';
  }

  // 2. Banner Flutuante (mostra sempre que houver necessidade através de actualização)
  if (!dispensado) {
    const banner = document.getElementById('sigeBannerActualizacaoPendente');
    const titulo = document.getElementById('sigeTituloActualizacao');
    const desc = document.getElementById('sigeDescricaoActualizacao');
    if (banner) {
      if (titulo) {
        titulo.textContent = 'Nova Actualização Disponível';
      }
      if (desc) {
        desc.textContent = 'Existe uma nova actualização pronta a instalar no sistema.';
      }
      banner.classList.remove('d-none');
    }
  }
};

// Fechar banner temporariamente ao clicar em "Mais tarde" (suspende por 15 minutos)
window.sigeFecharBannerActualizacao = function() {
  const buildId = sigeUpdateState.detalhes?.novoBuild || sigeUpdateState.detalhes?.novaVersao || 'novo';
  if (typeof localStorage !== 'undefined') {
    const snoozeAte = Date.now() + 15 * 60 * 1000;
    localStorage.setItem('sige_snooze_build_' + buildId, snoozeAte.toString());
  }
  const banner = document.getElementById('sigeBannerActualizacaoPendente');
  if (banner) {
    banner.classList.add('d-none');
  }
};

// Aplicar actualização imediatamente (limpa cache, ativa novo service worker e recarrega)
window.sigeAplicarActualizacao = async function() {
  const modalEl = document.getElementById('modalActualizandoSige');
  if (modalEl && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
    const modalInst = new bootstrap.Modal(modalEl);
    modalInst.show();
  } else if (typeof mostrarNotificacao === 'function') {
    mostrarNotificacao('A aplicar actualização do SIGE...', 'info');
  }

  try {
    // 1. Limpar registos de snooze para que a nova versão abra limpa
    if (typeof localStorage !== 'undefined') {
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('sige_snooze_build_') || key.startsWith('sige_dismissed_build_')) {
          localStorage.removeItem(key);
        }
      });
    }

    // 2. Enviar mensagem de ativação para o Service Worker
    if (sigeUpdateState.workerEsperando) {
      sigeUpdateState.workerEsperando.postMessage({ action: 'skipWaiting' });
    } else if (sigeUpdateState.registration && sigeUpdateState.registration.waiting) {
      sigeUpdateState.registration.waiting.postMessage({ action: 'skipWaiting' });
    }

    // 3. Limpar CacheStorage do navegador
    if ('caches' in window) {
      try {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
      } catch (err) {}
    }

    // 4. Forçar recarregamento completo sem cache
    setTimeout(() => {
      window.location.reload(true);
    }, 600);
  } catch (e) {
    window.location.reload(true);
  }
};

// Verificação estrita contra version.json
async function sigeChecarVersaoServidor() {
  try {
    const timestamp = Date.now();
    sigeUpdateState.ultimoCheck = timestamp;
    const resp = await fetch(`/version.json?_t=${timestamp}`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
      }
    });

    if (resp.ok) {
      const data = await resp.json();
      const localBuild = sigeCurrentBuild();
      const remoteBuild = data.build;

      // Se o build do servidor for rigorosamente DIFERENTE do HTML actualmente carregado:
      if (remoteBuild && localBuild && remoteBuild !== localBuild) {
        window.sigeNotificarActualizacaoPendente({
          tipo: 'nova_versao_detectada',
          novaVersao: data.version,
          novoBuild: remoteBuild,
          novidades: data.novidades || data.descricao || ''
        });
        return true;
      }
    }
  } catch (e) {}
  return false;
}

// Inicialização dos detectores em segundo plano (garante disparo fiável quando há nova versão)
function inicializarDetectorActualizacoes() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      const buildAtual = sigeCurrentBuild() || Date.now();
      navigator.serviceWorker.register('/service-worker.js?v=' + encodeURIComponent(buildAtual)).then((reg) => {
        sigeUpdateState.registration = reg;

        // Se já houver um worker esperando ativação
        if (reg.waiting) {
          sigeUpdateState.workerEsperando = reg.waiting;
          sigeChecarVersaoServidor();
        }

        // Ao detectar novo worker instalado enquanto um já controlava a página
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          if (!newWorker) return;

          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              sigeUpdateState.workerEsperando = newWorker;
              sigeChecarVersaoServidor();
            }
          });
        });

        reg.update().catch(() => {});
      }).catch(() => {});
    });
  }

  // Checar version.json logo 2.5 segundos após a carga da página (detecta se abriu a partir de cache)
  window.addEventListener('load', () => {
    setTimeout(() => {
      sigeChecarVersaoServidor();
    }, 2500);
  });

  // Checar ao alternar abas (detecta se houve deploy enquanto a aba esteve em segundo plano)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      if (sigeUpdateState.registration) {
        sigeUpdateState.registration.update().catch(() => {});
      }
      sigeChecarVersaoServidor();
    }
  });

  // Polling a cada 60 segundos (1 minuto) durante o uso contínuo
  setInterval(() => {
    if (sigeUpdateState.registration) {
      sigeUpdateState.registration.update().catch(() => {});
    }
    sigeChecarVersaoServidor();
  }, 60 * 1000);
}

inicializarDetectorActualizacoes();


// Garantir que ao abrir ou atualizar a página não haja auto-login nem persistência automática de sessão
sessionStorage.removeItem('sige_token');
sessionStorage.removeItem('sige_refresh_token');
localStorage.removeItem('sige_token');
localStorage.removeItem('sige_refresh_token');

const state = {
  token: null,
  refreshToken: null,
  user: null,
  tenant: null,
  charts: {},
  geografia: {
    provincias: [],
    distritos: {},
    carreiras: [],
    tiposDocumento: [],
    anotacoes: [],
    comportamentos: []
  },
  alocacoesDocente: [],
  alocacaoAtualId: null,
  filtroDisciplinaClasse: '',
  cadernetaClasseSelecionada: null,
  cadernetaAreaSelecionada: null,
  cadernetaAlocacaoSelecionadaId: null,
  cadernetaProfessorFiltroId: 'TODOS'
};

// ==================== FORMATAÇÃO DE MOEDA (MZN) & RESPONSIVIDADE DE TABELAS ====================
function formatarMoeda(valor) {
  const num = Number(valor || 0);
  return `${num.toLocaleString('pt-PT')} <span class="moeda-sufixo">MZN</span>`;
}

function formatarMoedaTexto(valor) {
  const num = Number(valor || 0);
  return `${num.toLocaleString('pt-PT')} MZN`;
}

function aplicarResponsividadeUniversalTabelas(root = document) {
  try {
    const elRoot = root || document;
    const tabelas = elRoot.querySelectorAll('table.table');
    tabelas.forEach(tbl => {
      if (!tbl.closest('.table-responsive') && !tbl.closest('.printable-document') && !tbl.closest('.documento-a4-pagina-unica')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive';
        tbl.parentNode.insertBefore(wrapper, tbl);
        wrapper.appendChild(tbl);
      }
    });
  } catch (e) {
    console.warn('Erro ao aplicar responsividade universal a tabelas:', e);
  }
}

window.formatarMoeda = formatarMoeda;
window.formatarMoedaTexto = formatarMoedaTexto;
window.aplicarResponsividadeUniversalTabelas = aplicarResponsividadeUniversalTabelas;

// ==================== CONTROLO RESTRITIVO E MÁSCARAS DE CAMPOS NUMÉRICOS, NUIT E TELEFONE ====================
/**
 * Classifica um elemento de formulário quanto à sua natureza numérica:
 * - 'nuit': Número Único de Identificação Tributária — exclusivamente dígitos 0-9, máx. 9 dígitos.
 * - 'telefone': Celular ou telefone — números apenas, sem aceitar letras (permite prefixo + e pontuação telefónica).
 * - 'telefone_multiplo': Lista de números para SMS em lote (permite vírgula/ponto e vírgula).
 * - 'inteiro': Quantidades, vagas, capacidades, anos, faltas, cargas horárias, contas, NIB — apenas dígitos 0-9.
 * - 'decimal': Valores monetários, preços, multas, taxas, notas e percentagens — dígitos e um separador decimal.
 */
function classificarCampoNumerico(input) {
  if (!input || (input.tagName !== 'INPUT' && input.tagName !== 'TEXTAREA')) return null;
  const id = (input.id || '').toLowerCase();
  const name = (input.name || '').toLowerCase();
  const placeholder = (input.placeholder || '').toLowerCase();
  const type = (input.type || '').toLowerCase();
  const dataTipo = (input.getAttribute('data-tipo') || '').toLowerCase();
  const classList = (input.className || '').toLowerCase();

  // Excluir tipos de dados não textuais, senhas, e-mails, arquivos, buscas e referências alfanuméricas
  if (['password', 'email', 'file', 'checkbox', 'radio', 'color', 'range', 'date', 'datetime-local', 'month', 'week', 'time', 'search'].includes(type)) {
    return null;
  }
  if (id.includes('pesquisa') || id.includes('filtro') || id.includes('busca') || id.includes('search')) {
    return null;
  }
  // Número de documento (ex: BI moçambicano '110100234567M' com letra final ou passaporte) e referências de recibos/banco
  if (id.includes('numdoc') || id.includes('numerodocumento') || id.includes('referencia') || id.includes('ref')) {
    return null;
  }

  // 1. NUIT: estritamente 9 dígitos numéricos
  if (id.includes('nuit') || name.includes('nuit') || dataTipo === 'nuit' || placeholder.includes('nuit') || classList.includes('campo-nuit')) {
    return 'nuit';
  }

  // 2. CELULAR / TELEFONE: números apenas, estritamente sem letras
  if (
    type === 'tel' ||
    dataTipo === 'telefone' || dataTipo === 'celular' ||
    classList.includes('campo-telefone') || classList.includes('campo-celular') ||
    id.includes('telefone') || id.includes('celular') || id.includes('msisdn') ||
    id.includes('telresp') || id.includes('escolatelefone') || id.includes('mptel') || id.includes('mpetel') || id.includes('matel') ||
    id.includes('liqtelefone') || id.includes('ussdinptel') ||
    (id.includes('contato') || id.includes('contacto')) && !id.includes('tipo') ||
    name.includes('telefone') || name.includes('celular') || name.includes('contato') || name.includes('contacto') ||
    placeholder.includes('+258') || placeholder.includes('telemóvel') || placeholder.includes('telefone')
  ) {
    if (id.includes('smstelefone') || id.includes('telefones') || id.includes('multiplos')) {
      return 'telefone_multiplo';
    }
    return 'telefone';
  }

  // 3. NÚMEROS, QUANTIDADES, CAPACIDADES, ANOS, DIAS E VALORES
  if (
    type === 'number' ||
    dataTipo === 'numero' || dataTipo === 'quantidade' || dataTipo === 'moeda' || dataTipo === 'inteiro' || dataTipo === 'decimal' ||
    classList.includes('campo-numero') || classList.includes('campo-quantidade') ||
    id.includes('qtd') || id.includes('quant') || id.includes('capacidade') ||
    id.includes('carga') || id.includes('vagas') || id.includes('faltas') ||
    (id.includes('dias') || id.includes('dialimite') || id.includes('diatol') || id.includes('diavenc')) ||
    id.includes('anoletivo') || id.includes('anoingresso') ||
    id.includes('hini') || id.includes('mini') || id.includes('hfim') || id.includes('mfim') ||
    id.includes('bimconta') || id.includes('bimnib') || id.includes('bciconta') || id.includes('bcinib') ||
    id.includes('port') || id.includes('desbloqueiohoras') ||
    id.includes('valor') || id.includes('preco') || id.includes('multa') || id.includes('taxa') || id.includes('desconto') ||
    id.includes('mlnt') || id.includes('mlntrabalho') || id.includes('mlnat')
  ) {
    if (
      id.includes('valor') || id.includes('preco') || id.includes('multa') ||
      id.includes('taxa') || id.includes('desconto') || (input.step && input.step !== '1') ||
      id.includes('mlnt') || id.includes('mlntrabalho') || id.includes('mlnat')
    ) {
      return 'decimal';
    }
    return 'inteiro';
  }

  return null;
}

function sanitizarValorCampoNumerico(input) {
  if (!input) return;
  const categoria = classificarCampoNumerico(input);
  if (!categoria) return;

  const original = input.value || '';
  let limpo = original;

  if (categoria === 'nuit') {
    // Apenas dígitos, máximo 9 dígitos
    limpo = limpo.replace(/\D/g, '').slice(0, 9);
    input.setAttribute('maxlength', '9');
    input.setAttribute('inputmode', 'numeric');
    input.setAttribute('pattern', '[0-9]{1,9}');
  } else if (categoria === 'telefone') {
    // Proibir qualquer letra
    limpo = limpo.replace(/[a-zA-Z\u00C0-\u017F]/g, '');
    // Permitir dígitos, +, espaços, hífens, parênteses
    limpo = limpo.replace(/[^\d+ \-\(\)]/g, '');
    const comecaComMais = limpo.startsWith('+');
    limpo = (comecaComMais ? '+' : '') + limpo.replace(/\+/g, '');
    input.setAttribute('inputmode', 'tel');
  } else if (categoria === 'telefone_multiplo') {
    limpo = limpo.replace(/[a-zA-Z\u00C0-\u017F]/g, '');
    limpo = limpo.replace(/[^\d+;, \-\(\)]/g, '');
    input.setAttribute('inputmode', 'tel');
  } else if (categoria === 'inteiro') {
    limpo = limpo.replace(/\D/g, '');
    input.setAttribute('inputmode', 'numeric');
  } else if (categoria === 'decimal') {
    limpo = limpo.replace(/[a-zA-Z\u00C0-\u017F]/g, '');
    limpo = limpo.replace(/[^\d.,]/g, '');
    const primeiroPonto = limpo.search(/[.,]/);
    if (primeiroPonto !== -1) {
      const sep = limpo[primeiroPonto];
      const antes = limpo.substring(0, primeiroPonto);
      const depois = limpo.substring(primeiroPonto + 1).replace(/[.,]/g, '');
      limpo = antes + sep + depois;
    }
    input.setAttribute('inputmode', 'decimal');
  }

  if (input.value !== limpo) {
    const start = input.selectionStart;
    const diff = original.length - limpo.length;
    input.value = limpo;
    try {
      const newPos = Math.max(0, (start || limpo.length) - (diff > 0 ? diff : 0));
      input.setSelectionRange(newPos, newPos);
    } catch (_) {}
  }
}

function tratarKeydownCampoNumerico(e) {
  const input = e.target;
  const categoria = classificarCampoNumerico(input);
  if (!categoria) return;

  const teclasControle = [
    'Backspace', 'Delete', 'Tab', 'Escape', 'Enter',
    'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
    'Home', 'End'
  ];
  if (teclasControle.includes(e.key) || e.ctrlKey || e.metaKey || e.altKey) {
    return;
  }

  // REGRA MESTRA: Qualquer letra é terminantemente impedida de ser digitada
  if (/^[a-zA-Z\u00C0-\u017F]$/.test(e.key)) {
    e.preventDefault();
    return;
  }

  if (categoria === 'nuit') {
    if (!/^\d$/.test(e.key)) {
      e.preventDefault();
      return;
    }
    const selLen = (input.selectionEnd || 0) - (input.selectionStart || 0);
    const digitosAtuais = (input.value || '').replace(/\D/g, '');
    if (digitosAtuais.length >= 9 && selLen === 0) {
      e.preventDefault();
      return;
    }
  } else if (categoria === 'telefone') {
    if (!/^[\d+ \-\(\)]$/.test(e.key)) {
      e.preventDefault();
      return;
    }
    if (e.key === '+') {
      if ((input.selectionStart || 0) !== 0 || (input.value || '').includes('+')) {
        e.preventDefault();
        return;
      }
    }
  } else if (categoria === 'telefone_multiplo') {
    if (!/^[\d+;, \-\(\)]$/.test(e.key)) {
      e.preventDefault();
      return;
    }
  } else if (categoria === 'inteiro') {
    if (!/^\d$/.test(e.key)) {
      e.preventDefault();
      return;
    }
  } else if (categoria === 'decimal') {
    if (!/^[\d.,]$/.test(e.key)) {
      e.preventDefault();
      return;
    }
    if (e.key === '.' || e.key === ',') {
      if ((input.value || '').includes('.') || (input.value || '').includes(',')) {
        e.preventDefault();
        return;
      }
    }
  }
}

function tratarPasteCampoNumerico(e) {
  const input = e.target;
  const categoria = classificarCampoNumerico(input);
  if (!categoria) return;

  const textoColado = (e.clipboardData || window.clipboardData)?.getData('text') || '';
  if (/[a-zA-Z\u00C0-\u017F]/.test(textoColado)) {
    e.preventDefault();
    let limpo = textoColado.replace(/[a-zA-Z\u00C0-\u017F]/g, '');
    if (categoria === 'nuit') {
      limpo = limpo.replace(/\D/g, '');
      const atual = (input.value || '').replace(/\D/g, '');
      const espacoRestante = Math.max(0, 9 - atual.length);
      limpo = limpo.slice(0, espacoRestante);
    } else if (categoria === 'inteiro') {
      limpo = limpo.replace(/\D/g, '');
    } else if (categoria === 'decimal') {
      limpo = limpo.replace(/[^\d.,]/g, '');
    } else if (categoria === 'telefone') {
      limpo = limpo.replace(/[^\d+ \-\(\)]/g, '');
    }
    try {
      document.execCommand('insertText', false, limpo);
    } catch (_) {
      input.value = (input.value || '') + limpo;
    }
    sanitizarValorCampoNumerico(input);
  } else {
    setTimeout(() => sanitizarValorCampoNumerico(input), 0);
  }
}

function aplicarMascaraCamposNumericos(root = document) {
  try {
    const elRoot = root || document;
    const inputs = elRoot.querySelectorAll('input, textarea');
    inputs.forEach(input => {
      const categoria = classificarCampoNumerico(input);
      if (!categoria) return;

      if (categoria === 'nuit') {
        input.setAttribute('maxlength', '9');
        input.setAttribute('inputmode', 'numeric');
        input.setAttribute('pattern', '[0-9]{1,9}');
        if (!input.placeholder || input.placeholder.includes('Ex:')) {
          input.setAttribute('placeholder', 'Ex: 400123456 (máx. 9 dígitos)');
        }
      } else if (categoria === 'telefone' || categoria === 'telefone_multiplo') {
        input.setAttribute('inputmode', 'tel');
      } else if (categoria === 'inteiro') {
        input.setAttribute('inputmode', 'numeric');
      } else if (categoria === 'decimal') {
        input.setAttribute('inputmode', 'decimal');
      }
      sanitizarValorCampoNumerico(input);
    });
  } catch (err) {
    console.warn('[MASCARAS] Erro ao aplicar máscaras numéricas:', err);
  }
}

function inicializarFiltrosNumericosGlobais() {
  document.addEventListener('keydown', tratarKeydownCampoNumerico, true);
  document.addEventListener('input', (e) => sanitizarValorCampoNumerico(e.target), true);
  document.addEventListener('paste', tratarPasteCampoNumerico, true);
  document.addEventListener('change', (e) => sanitizarValorCampoNumerico(e.target), true);
  aplicarMascaraCamposNumericos(document);
}

// Inicializar imediatamente os interceptores no escopo global
inicializarFiltrosNumericosGlobais();

window.classificarCampoNumerico = classificarCampoNumerico;
window.sanitizarValorCampoNumerico = sanitizarValorCampoNumerico;
window.aplicarMascaraCamposNumericos = aplicarMascaraCamposNumericos;

// ==================== UTILITÁRIOS DE SEGURANÇA E ESCAPE ====================
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
window.escapeHtml = escapeHtml;

// ==================== LIMPEZA DE TEXTO E HIGIENIZAÇÃO DE MENSAGENS ====================
// Garante que nenhuma mensagem, notificação ou alerta exiba domínios, URLs ou links do sistema
function limparTextoMensagem(msg) {
  if (msg === null || msg === undefined) return '';
  let str = String(msg);
  // Remove prefixos de diálogos do navegador como "sigesaas.duckdns.org diz:" ou qualquer domínio
  str = str.replace(/https?:\/\/sigesaas\.duckdns\.org(\/api\/v1)?\/?/gi, '')
           .replace(/sigesaas\.duckdns\.org\s*(diz|says)?:?/gi, '')
           .replace(/^https?:\/\/[^\s/$.?#].[^\s]*\s*(diz|says)?:?/gi, '')
           .replace(/https?:\/\/127\.0\.0\.1(:8000)?(\/api\/v1)?\/?/gi, '')
           .replace(/https?:\/\/localhost(:8000)?(\/api\/v1)?\/?/gi, '')
           .replace(/\b139\.84\.226\.46\b/g, '')
           .trim();
  return str;
}
window.limparTextoMensagem = limparTextoMensagem;

// ==================== NOTIFICAÇÕES TOAST (PROTEÇÃO TOTAL CONTRA XSS E SEM LINKS) ====================
function mostrarNotificacao(mensagem, tipo = 'info') {
  const msgLimpa = limparTextoMensagem(mensagem);
  if (!msgLimpa) return;

  let container = document.getElementById('sigeToastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'sigeToastContainer';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '10070';
    document.body.appendChild(container);
  }

  const bgClass = tipo === 'success' ? 'bg-success text-white' : (tipo === 'danger' ? 'bg-danger text-white' : (tipo === 'warning' ? 'bg-warning text-dark' : 'bg-primary text-white'));
  const icon = tipo === 'success' ? 'bi-check-circle-fill' : (tipo === 'danger' ? 'bi-x-circle-fill' : (tipo === 'warning' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill'));

  const toastEl = document.createElement('div');
  toastEl.className = `toast align-items-center ${bgClass} border-0 shadow show mb-2`;
  toastEl.setAttribute('role', 'alert');

  const dFlex = document.createElement('div');
  dFlex.className = 'd-flex align-items-center';

  const bodyDiv = document.createElement('div');
  bodyDiv.className = 'toast-body d-flex align-items-center gap-2 flex-grow-1';

  const iconEl = document.createElement('i');
  iconEl.className = `bi ${icon} fs-5 flex-shrink-0`;

  const spanEl = document.createElement('span');
  spanEl.textContent = msgLimpa;

  bodyDiv.appendChild(iconEl);
  bodyDiv.appendChild(spanEl);

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'btn-close btn-close-white me-2 m-auto';
  closeBtn.setAttribute('data-bs-dismiss', 'toast');
  closeBtn.onclick = () => {
    if (toastEl.parentNode) toastEl.remove();
  };

  dFlex.appendChild(bodyDiv);
  dFlex.appendChild(closeBtn);
  toastEl.appendChild(dFlex);

  container.appendChild(toastEl);
  setTimeout(() => {
    if (toastEl.parentNode) toastEl.remove();
  }, 4500);
}

window.mostrarNotificacao = mostrarNotificacao;
window.showToast = mostrarNotificacao;
window.mostrarToast = mostrarNotificacao;

// ==================== MODAL DE ALERTA DO SISTEMA (SUBSTITUTO DO ALERT NATIVO) ====================
let modalAlertaInstancia = null;
let ultimoAlertaMensagem = '';
let ultimoAlertaTimestamp = 0;

function mostrarAlerta(mensagem, tipo = 'info', titulo = '') {
  const msgLimpa = limparTextoMensagem(mensagem);
  if (!msgLimpa) return;

  // Prevenção contra chamadas duplicadas idênticas em curto intervalo
  const agora = Date.now();
  if (msgLimpa === ultimoAlertaMensagem && (agora - ultimoAlertaTimestamp) < 1000) {
    return;
  }
  ultimoAlertaMensagem = msgLimpa;
  ultimoAlertaTimestamp = agora;

  const modalEl = document.getElementById('modalAlertaSistema');
  if (!modalEl || typeof bootstrap === 'undefined' || !bootstrap.Modal) {
    mostrarNotificacao(msgLimpa, tipo);
    return;
  }

  const elTitulo = document.getElementById('modalAlertaTitulo');
  const elMsg = document.getElementById('modalAlertaMensagem');
  const elIcone = document.getElementById('modalAlertaIcone');
  const btnOk = document.getElementById('modalAlertaBtnOk');

  let tituloPadrao = 'Informação';
  let iconeHtml = '<i class="bi bi-info-circle-fill text-primary" style="font-size: 2.8rem;"></i>';
  let btnClass = 'btn btn-primary px-4 py-2 fw-semibold rounded-pill shadow-sm';

  const tipoStr = String(tipo || 'info').toLowerCase();
  if (tipoStr === 'warning' || tipoStr === 'aviso' || tipoStr === 'alerta') {
    tituloPadrao = 'Aviso';
    iconeHtml = '<i class="bi bi-exclamation-triangle-fill text-warning" style="font-size: 2.8rem;"></i>';
    btnClass = 'btn btn-warning text-dark px-4 py-2 fw-semibold rounded-pill shadow-sm';
  } else if (tipoStr === 'danger' || tipoStr === 'erro' || tipoStr === 'error') {
    tituloPadrao = 'Atenção';
    iconeHtml = '<i class="bi bi-x-circle-fill text-danger" style="font-size: 2.8rem;"></i>';
    btnClass = 'btn btn-danger px-4 py-2 fw-semibold rounded-pill shadow-sm';
  } else if (tipoStr === 'success' || tipoStr === 'sucesso') {
    tituloPadrao = 'Sucesso';
    iconeHtml = '<i class="bi bi-check-circle-fill text-success" style="font-size: 2.8rem;"></i>';
    btnClass = 'btn btn-success px-4 py-2 fw-semibold rounded-pill shadow-sm';
  }

  if (elTitulo) elTitulo.textContent = titulo ? limparTextoMensagem(titulo) : tituloPadrao;
  if (elMsg) elMsg.textContent = msgLimpa;
  if (elIcone) elIcone.innerHTML = iconeHtml;
  if (btnOk) {
    btnOk.className = btnClass;
    btnOk.textContent = 'OK';
  }

  // Ajuste dinâmico de z-index para empilhamento harmonioso sobre outros modais
  const modaisAbertos = document.querySelectorAll('.modal.show').length;
  const zIndexBase = 10060 + (modaisAbertos * 10);
  modalEl.style.zIndex = zIndexBase;

  modalAlertaInstancia = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
  modalAlertaInstancia.show();

  setTimeout(() => {
    btnOk?.focus();
    const backdrops = document.querySelectorAll('.modal-backdrop');
    if (backdrops.length > 0) {
      backdrops[backdrops.length - 1].style.zIndex = zIndexBase - 1;
    }
  }, 100);
}

window.mostrarAlerta = mostrarAlerta;

// ==================== MODAL DE CONFIRMAÇÃO DO SISTEMA ====================
let modalConfirmacaoInstancia = null;
let callbackConfirmacaoAtual = null;
let callbackCancelamentoAtual = null;

function mostrarConfirmacao(mensagem, onConfirm, onCancel = null, titulo = 'Confirmação') {
  const msgLimpa = limparTextoMensagem(mensagem);
  const modalEl = document.getElementById('modalConfirmacaoSistema');
  if (!modalEl || typeof bootstrap === 'undefined' || !bootstrap.Modal) {
    if (window._nativeConfirm ? window._nativeConfirm(msgLimpa) : true) {
      if (typeof onConfirm === 'function') onConfirm();
    } else {
      if (typeof onCancel === 'function') onCancel();
    }
    return;
  }

  callbackConfirmacaoAtual = onConfirm;
  callbackCancelamentoAtual = onCancel;

  const elTitulo = document.getElementById('modalConfirmacaoTitulo');
  const elMsg = document.getElementById('modalConfirmacaoMensagem');
  if (elTitulo) elTitulo.textContent = titulo ? limparTextoMensagem(titulo) : 'Confirmação';
  if (elMsg) elMsg.textContent = msgLimpa;

  const modaisAbertos = document.querySelectorAll('.modal.show').length;
  const zIndexBase = 10060 + (modaisAbertos * 10);
  modalEl.style.zIndex = zIndexBase;

  modalConfirmacaoInstancia = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
  modalConfirmacaoInstancia.show();

  setTimeout(() => {
    const backdrops = document.querySelectorAll('.modal-backdrop');
    if (backdrops.length > 0) {
      backdrops[backdrops.length - 1].style.zIndex = zIndexBase - 1;
    }
  }, 100);
}

window.mostrarConfirmacao = mostrarConfirmacao;

// Listeners dos botões de confirmação
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('modalConfirmacaoBtnConfirmar')?.addEventListener('click', () => {
    if (modalConfirmacaoInstancia) modalConfirmacaoInstancia.hide();
    if (typeof callbackConfirmacaoAtual === 'function') {
      const fn = callbackConfirmacaoAtual;
      callbackConfirmacaoAtual = null;
      fn();
    }
  });

  document.getElementById('modalConfirmacaoBtnCancelar')?.addEventListener('click', () => {
    if (typeof callbackCancelamentoAtual === 'function') {
      const fn = callbackCancelamentoAtual;
      callbackCancelamentoAtual = null;
      fn();
    }
  });

  document.getElementById('modalConfirmacaoSistema')?.addEventListener('hidden.bs.modal', () => {
    if (typeof callbackCancelamentoAtual === 'function') {
      const fn = callbackCancelamentoAtual;
      callbackCancelamentoAtual = null;
      fn();
    }
  });
});

// ==================== INTERCEPTAÇÃO GLOBAL DO ALERT NATIVO ====================
// Substituição total para garantir que NENHUMA chamada em nenhum ficheiro mostre o domínio do sistema
window.alert = function(mensagem) {
  const msgLimpa = limparTextoMensagem(mensagem);
  if (!msgLimpa) return;

  const str = msgLimpa.toLowerCase();
  let tipo = 'info';
  if (str.includes('erro') || str.includes('falha') || str.includes('rejeit') || str.includes('não foi possível')) {
    tipo = 'danger';
  } else if (str.includes('atenção') || str.includes('aviso') || str.includes('já foi gerada') || str.includes('selecione') || str.includes('preencha') || str.includes('obrigatório')) {
    tipo = 'warning';
  } else if (str.includes('sucesso') || str.includes('salvo') || str.includes('atualizado') || str.includes('cadastrado') || str.includes('eliminado')) {
    tipo = 'success';
  }
  mostrarAlerta(msgLimpa, tipo);
};

// Drenagem de alertas enfileirados antes do carregamento do app.js
if (Array.isArray(window._sigeAlertQueue) && window._sigeAlertQueue.length > 0) {
  const queue = [...window._sigeAlertQueue];
  window._sigeAlertQueue = [];
  queue.forEach(msg => window.alert(msg));
}

// ==================== API FETCH, RENOVAÇÃO UNIFICADA E INTERCEPTADORES ====================
function formatarUrlApi(url, baseUrlOverride = null) {
  if (!url || typeof url !== 'string') return url;
  let cleanUrl = url;
  if (cleanUrl.includes('?')) {
    const parts = cleanUrl.split('?');
    const path = parts[0];
    const query = parts.slice(1).join('?');
    if (!path.endsWith('/') && !/\.[a-zA-Z0-9]+$/.test(path)) {
      cleanUrl = `${path}/?${query}`;
    }
  } else if (!cleanUrl.includes('#') && !/\.[a-zA-Z0-9]+$/.test(cleanUrl) && !cleanUrl.endsWith('/')) {
    cleanUrl = cleanUrl + '/';
  }
  if (cleanUrl.startsWith('http://') || cleanUrl.startsWith('https://')) return cleanUrl;

  const isFile = typeof window !== 'undefined' && window.location && window.location.protocol === 'file:';
  const isHttps = typeof window !== 'undefined' && window.location && window.location.protocol === 'https:';
  const isLocalHost = typeof window !== 'undefined' && window.location && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || isFile);

  const baseUrl = baseUrlOverride || (window.SIGE_CONFIG && window.SIGE_CONFIG.API_BASE_URL) || (isFile ? 'http://127.0.0.1:8000/api/v1' : '/api/v1');

  // Se a aplicação estiver a correr via HTTPS ou domínio web remoto,
  // nunca retornar URLs 'http://' (Mixed Content) nem tentar ligar a 127.0.0.1 que não existe no cliente.
  if (cleanUrl.startsWith('/api/v1')) {
    if (isFile && !baseUrl.startsWith('http')) {
      return 'http://127.0.0.1:8000' + cleanUrl;
    }
    if (baseUrl.startsWith('https://') || (baseUrl.startsWith('http://') && isLocalHost && !isHttps)) {
      return baseUrl.replace(/\/api\/v1\/?$/, '') + cleanUrl;
    }
    return cleanUrl;
  }

  return baseUrl.replace(/\/+$/, '') + '/' + cleanUrl.replace(/^\/+/, '');
}

// ==================== RENOVAÇÃO UNIFICADA DE TOKEN (DEDICADA E SEM CONCORRÊNCIA) ====================
let refreshPromiseEmAndamento = null;

async function renovarTokenAcesso() {
  if (refreshPromiseEmAndamento) {
    return refreshPromiseEmAndamento;
  }

  const storedRefresh = state.refreshToken || sessionStorage.getItem('sige_refresh_token');
  if (!storedRefresh) {
    return null;
  }

  refreshPromiseEmAndamento = (async () => {
    try {
      const resp = await fetch(formatarUrlApi('/api/v1/auth/refresh'), {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ refresh: storedRefresh, refreshToken: storedRefresh })
      });

      if (!resp.ok) {
        return null;
      }

      const data = await resp.json().catch(() => ({}));
      const newAccessToken = data.access || data.accessToken || data.token || data.data?.tokens?.accessToken || data.data?.token;
      const newRefreshToken = data.refresh || data.refreshToken || data.data?.tokens?.refreshToken;

      if (newAccessToken) {
        state.token = newAccessToken;
        sessionStorage.setItem('sige_token', newAccessToken);
        if (newRefreshToken) {
          state.refreshToken = newRefreshToken;
          sessionStorage.setItem('sige_refresh_token', newRefreshToken);
        }
        return newAccessToken;
      }
      return null;
    } catch (err) {
      console.warn('[AUTH] Falha ao renovar token de acesso:', err);
      return null;
    } finally {
      refreshPromiseEmAndamento = null;
    }
  })();

  return refreshPromiseEmAndamento;
}
window.renovarTokenAcesso = renovarTokenAcesso;

async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  // Garantir isolamento rigoroso de tenant em todas as chamadas à API
  const activeTenantId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id;
  if (activeTenantId && !headers['X-Tenant-ID']) {
    headers['X-Tenant-ID'] = activeTenantId;
  }

  const targetUrl = options._fallbackUrl || formatarUrlApi(endpoint);
  try {
    const res = await fetch(targetUrl, { ...options, headers });
    
    // Tratamento seguro de tipo de conteúdo (JSON, texto ou corpo vazio)
    let json = null;
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      try {
        json = await res.json();
      } catch (_) {
        json = null;
      }
    } else {
      try {
        const txt = await res.text();
        json = { message: txt };
      } catch (_) {
        json = null;
      }
    }
    if (!json || typeof json !== 'object') json = {};

    if (!res.ok) {
      if (res.status === 401 && !options._isRetry) {
        const newAccessToken = await renovarTokenAcesso();
        if (newAccessToken) {
          const retryHeaders = { ...headers, Authorization: `Bearer ${newAccessToken}` };
          return apiFetch(endpoint, { ...options, headers: retryHeaders, _isRetry: true });
        }
        if (!options.ignoreAuthRedirect && state.user?.role !== 'SUPERADMIN') {
          fazerLogout();
        }
      }

      // Tratamento seguro de expiração de assinatura institucional (HTTP 402 ou 403)
      if (res.status === 402) {
        const alertaExpiracaoBanner = document.getElementById('alertaExpiracaoBanner');
        if (alertaExpiracaoBanner) {
          alertaExpiracaoBanner.style.display = 'block';
        }
        mostrarNotificacao(json.message || 'Assinatura institucional pendente ou expirada.', 'warning');
      }

      if (res.status === 403 && json && (json.codigo === 'ASSINATURA_SUSPENSA' || json.codigo === 'ASSINATURA_RESTRITA')) {
        tratarAcessoRestritoOuSuspenso(json.codigo, json.message);
      }

      const alertaHeader = res.headers.get('X-Assinatura-Alerta');
      if (alertaHeader) {
        atualizarFaixaAlertaSaaS(alertaHeader);
      }

      let msg = json.message || json.detail || json.error;
      if (!msg && json.non_field_errors) {
        msg = Array.isArray(json.non_field_errors) ? json.non_field_errors.join(', ') : String(json.non_field_errors);
      }
      if (!msg && typeof json === 'object' && json !== null) {
        const fieldErrors = Object.entries(json)
          .filter(([k]) => !['message', 'detail', 'error', 'success', 'statusCode'].includes(k))
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`);
        if (fieldErrors.length > 0) {
          msg = fieldErrors.join(' | ');
        }
      }
      if (json.errors && Array.isArray(json.errors) && json.errors.length > 0) {
        const detalhes = json.errors.map(e => `${e.path?.join('.') || 'Campo'}: ${e.message}`).join(', ');
        msg = (msg ? `${msg} ` : '') + `(${detalhes})`;
      }
      if (!msg) {
        msg = `Erro no processamento da requisição (HTTP ${res.status})`;
      } else if (typeof msg === 'string') {
        const trimmed = msg.trim();
        if (trimmed.startsWith('<') || trimmed.includes('<html') || trimmed.includes('Server Error')) {
          msg = `Erro interno do servidor (HTTP ${res.status})`;
        }
      }
      throw new Error(msg);
    }

    return json;
  } catch (err) {
    if (!options._isFallback) {
      const isFile = typeof window !== 'undefined' && window.location && window.location.protocol === 'file:';
      const isLocalHost = typeof window !== 'undefined' && window.location && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || isFile);
      const isHttps = typeof window !== 'undefined' && window.location && window.location.protocol === 'https:';

      let fallbackUrl = null;
      if (targetUrl.startsWith('https://sigesaas.duckdns.org') && isLocalHost) {
        fallbackUrl = targetUrl.replace('https://sigesaas.duckdns.org', 'http://127.0.0.1:8000');
      } else if (targetUrl.startsWith('http://127.0.0.1:8000') && !isFile && !isHttps) {
        fallbackUrl = targetUrl.replace('http://127.0.0.1:8000', 'https://sigesaas.duckdns.org');
      } else if (targetUrl.startsWith('/api/v1') && isFile) {
        fallbackUrl = 'http://127.0.0.1:8000' + targetUrl;
      }

      if (fallbackUrl && fallbackUrl !== targetUrl) {
        console.warn(`[API FETCH] Falha de comunicação (${err.message || 'rede'}). Tentando rota alternativa: ${fallbackUrl}`);
        try {
          return await apiFetch(endpoint, { ...options, _isFallback: true, _fallbackUrl: fallbackUrl });
        } catch (_) {}
      }
    }
    console.error('API Error:', err);
    throw err;
  }
}

// Download de Ficheiros Binários (Excel XLSX / PDF / DOCX) com ArrayBuffer, Refresh Unificado e Tratamento Seguro de Erros (sem expor token no URL)
async function downloadFicheiroBinario(url, defaultFilename) {
  const fullUrl = formatarUrlApi(url);
  const montarHeaders = () => {
    const h = {};
    if (state.token) h['Authorization'] = `Bearer ${state.token}`;
    const activeTenantId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
      || state.tenant?.id
      || state.user?.escola_id;
    if (activeTenantId) {
      h['X-Tenant-ID'] = activeTenantId;
    }
    return h;
  };

  try {
    let res = await fetch(fullUrl, { headers: montarHeaders() });

    if (res.status === 401) {
      const newToken = await renovarTokenAcesso();
      if (newToken) {
        res = await fetch(fullUrl, { headers: montarHeaders() });
      }
    }

    if (!res.ok) {
      if (res.status === 401) throw new Error('Sessão expirada. Por favor, autentique-se novamente.');
      if (res.status === 403) throw new Error('Acesso negado: sem permissão para descarregar este ficheiro.');
      if (res.status === 404) throw new Error('O ficheiro solicitado não foi encontrado no servidor.');
      if (res.status === 402) throw new Error('Download bloqueado: conta institucional pendente ou suspensa.');
      if (res.status >= 500) throw new Error('Erro interno no servidor ao processar o ficheiro.');
      throw new Error(`Falha no descarregamento (HTTP ${res.status})`);
    }

    const disposition = res.headers.get('content-disposition');
    let filename = defaultFilename;
    if (disposition && disposition.includes('filename')) {
      const starMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
      if (starMatch && starMatch[1]) {
        try {
          filename = decodeURIComponent(starMatch[1].trim());
        } catch (e) {
          filename = starMatch[1].trim();
        }
      } else {
        const match = disposition.match(/filename="?([^";]+)"?/i);
        if (match && match[1]) filename = match[1].trim();
      }
    }

    const arrayBuffer = await res.arrayBuffer();
    const isXlsx = filename.toLowerCase().endsWith('.xlsx') || url.toLowerCase().includes('xlsx');
    const isPdf = filename.toLowerCase().endsWith('.pdf') || url.toLowerCase().includes('pdf');
    const isDocx = filename.toLowerCase().endsWith('.docx') || url.toLowerCase().includes('docx');
    const isJson = filename.toLowerCase().endsWith('.json') || url.toLowerCase().includes('json');
    let mimeType = 'application/octet-stream';
    if (isXlsx) mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    else if (isPdf) mimeType = 'application/pdf';
    else if (isDocx) mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    else if (isJson) mimeType = 'application/json';
    else if (res.headers.get('content-type')) mimeType = res.headers.get('content-type');

    const blob = new Blob([arrayBuffer], { type: mimeType });
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 5000);
    return true;
  } catch (err) {
    console.error('[DOWNLOAD] Falha no download do documento:', err);
    mostrarNotificacao(err.message || 'Falha ao descarregar documento.', 'danger');
    return false;
  }
}

// ==================== UTILITÁRIOS DE DATA E CALENDÁRIO ====================
function formatarParaInputDate(val) {
  if (!val) return '';
  val = String(val).trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(val)) return val;
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(val)) {
    const [d, m, y] = val.split('/');
    return `${y}-${m}-${d}`;
  }
  return '';
}

function formatarDataParaExibicao(val, anoFallback = '2026') {
  if (!val || !val.trim()) return `___/___/${anoFallback}`;
  val = val.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(val)) {
    const [y, m, d] = val.split('-');
    return `${d}/${m}/${y}`;
  }
  return val;
}

let ultimoPickerAberto = null;
let ultimoTimestampPicker = 0;

function abrirSeletorDataSeguro(input) {
  if (!input || typeof input.showPicker !== 'function' || input.disabled || input.readOnly) return;
  const agora = Date.now();
  if (ultimoPickerAberto === input && (agora - ultimoTimestampPicker) < 500) {
    return;
  }
  ultimoPickerAberto = input;
  ultimoTimestampPicker = agora;
  try {
    input.showPicker();
  } catch (err) {
    // Silencioso se o browser rejeitar chamada programática
  }
}

// Abrir com segurança o calendário nativo ao interagir com inputs date ou seus botões/labels
document.addEventListener('click', (e) => {
  const target = e.target;
  if (!target) return;

  // 1. Clicou num label associado a um input type="date"
  if (target.tagName === 'LABEL' && target.htmlFor) {
    const associatedInput = document.getElementById(target.htmlFor);
    if (associatedInput && associatedInput.type === 'date') {
      abrirSeletorDataSeguro(associatedInput);
      return;
    }
  }

  // 2. Clicou num ícone ou botão dentro de um input-group que contém um input date
  const group = target.closest('.input-group');
  if (group) {
    const groupDateInput = group.querySelector('input[type="date"]');
    if (groupDateInput && target !== groupDateInput) {
      abrirSeletorDataSeguro(groupDateInput);
      return;
    }
  }

  // 3. Clicou directamente no input[type="date"]
  const dateInput = target.matches('input[type="date"]') ? target : target.closest('input[type="date"]');
  if (dateInput) {
    abrirSeletorDataSeguro(dateInput);
  }
});

// ==================== INICIALIZAÇÃO DA APLICAÇÃO ====================
document.addEventListener('DOMContentLoaded', async () => {
  // Garantir imediatamente que a tela de login esteja ativa e o painel do sistema totalmente oculto
  mostrarTelaLogin();
  carregarDadosGeografia();

  // Limpeza de sessão ao inicializar ou atualizar a página: NUNCA efetuar login automático via AJAX!
  sessionStorage.removeItem('sige_token');
  sessionStorage.removeItem('sige_refresh_token');
  state.token = null;
  state.refreshToken = null;
  state.user = null;
  state.tenant = null;

  // Pré-preencher apenas o campo do utilizador memorizado (sem senha e sem efectuar login)
  const ultimoUsuario = localStorage.getItem('sige_ultimo_usuario') || '';
  const inpEmail = document.getElementById('loginEmail');
  const inpSenha = document.getElementById('loginSenha');
  if (inpEmail && ultimoUsuario) {
    inpEmail.value = ultimoUsuario;
  }
  if (inpSenha) {
    inpSenha.value = '';
    setTimeout(() => inpSenha.focus(), 150);
  }

  // Garantir isolamento visual multi-tenant estrito: tela de login e master SaaS nunca herdam temas de outras instituições
  try {
    localStorage.removeItem('sige_tema_ativo');
    const token = sessionStorage.getItem('sige_token') || localStorage.getItem('sige_token');
    const tenantSalvoId = localStorage.getItem('sige_selected_tenant');
    if (token && tenantSalvoId) {
      const temaTenantSalvo = localStorage.getItem(`sige_tema_escola_${tenantSalvoId}`);
      if (temaTenantSalvo && typeof aplicarTemaEFundoInstituicao === 'function') {
        aplicarTemaEFundoInstituicao(JSON.parse(temaTenantSalvo));
      }
    } else {
      if (typeof restaurarPadraoTemaEFundo === 'function') {
        restaurarPadraoTemaEFundo();
      }
    }
  } catch (_) {}

  document.getElementById('loginForm')?.addEventListener('submit', realizarLogin);
  aplicarResponsividadeUniversalTabelas();
});

async function carregarDadosGeografia() {
  try {
    const res = await fetch(formatarUrlApi('/api/v1/geografia'));
    const json = await res.json();
    if (json.success) {
      state.geografia = json.data;
    }
  } catch (err) {
    console.warn('Falha ao carregar dados geográficos:', err);
  }
}

function modalEsqueciSenha() {
  abrirModal('Recuperação de Acesso', `
    <div class="text-center p-3">
      <div class="mb-3 text-warning fs-1"><i class="bi bi-shield-lock"></i></div>
      <h6 class="fw-bold mb-2">Esqueceu a sua senha?</h6>
      <p class="text-muted small mb-3">
        Por razões de segurança e integridade institucional, o pedido de redefinição de credenciais deve ser solicitado diretamente ao Administrador do Sistema ou à Direção Pedagógica da sua instituição.
      </p>
      <div class="p-3 bg-light rounded text-start small border mb-3">
        <div class="mb-1"><i class="bi bi-envelope me-1 text-primary"></i> <strong>Apoio Técnico:</strong> suporte@sige.edu.mz</div>
        <div><i class="bi bi-shield-check me-1 text-success"></i> <strong>Administrador:</strong> Eng. Fernando Mandamule</div>
      </div>
      <button class="btn btn-primary w-100" onclick="fecharModal()">Compreendido</button>
    </div>
  `);
}

function modalRedefinirMinhaSenha() {
  const u = state.user || {};
  const cod = u.codigo_acesso || u.email || '';
  const statusSenha = u.senha_redefinida
    ? '<span class="badge bg-success">Personalizada pelo Utilizador</span>'
    : `<span class="badge bg-warning text-dark">Padrão Inicial (Igual ao Código: ${cod})</span>`;

  abrirModal('Meu Perfil de Utilizador & Alterar Palavra-passe', `
    <form id="formRedefinirMinhaSenha">
      <div class="p-3 bg-light rounded border mb-3 small">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span><strong>Utilizador:</strong> ${u.nome || '-'}</span>
          <span class="badge bg-dark font-monospace">${cod}</span>
        </div>
        <div class="mb-1"><strong>Perfil / Cargo:</strong> <span class="badge bg-secondary">${u.role || '-'}</span></div>
        <div><strong>Estado actual da senha:</strong> ${statusSenha}</div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-bold">Senha Actual <span class="text-muted fw-normal">(no 1.º acesso é a repetição do seu código: ${cod})</span></label>
        <input type="password" id="rmsSenhaAtual" class="form-control" placeholder="Informe a senha actual ou o seu código">
      </div>
      <div class="row g-2 mb-3">
        <div class="col-md-6">
          <label class="form-label small fw-bold text-primary">Nova Palavra-passe</label>
          <input type="password" id="rmsNovaSenha" class="form-control" required minlength="4" placeholder="Mínimo 4 caracteres">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-bold text-primary">Confirmar Nova Senha</label>
          <input type="password" id="rmsConfirmarSenha" class="form-control" required minlength="4" placeholder="Repita a nova senha">
        </div>
      </div>
      <div class="d-flex justify-content-end gap-2">
        <button type="button" class="btn btn-light" onclick="fecharModal()">Cancelar</button>
        <button type="submit" class="btn btn-primary fw-semibold px-4">
          <i class="bi bi-key-fill me-1"></i> Actualizar Minha Senha
        </button>
      </div>
    </form>
  `);

  document.getElementById('formRedefinirMinhaSenha')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const senha_atual = document.getElementById('rmsSenhaAtual')?.value || '';
    const nova_senha = document.getElementById('rmsNovaSenha')?.value || '';
    const confirmar = document.getElementById('rmsConfirmarSenha')?.value || '';

    if (nova_senha !== confirmar) {
      return alert('A nova palavra-passe e a confirmação não coincidem.');
    }

    try {
      const res = await apiFetch('/api/v1/auth/minha-senha', {
        method: 'POST',
        body: JSON.stringify({ senha_atual, nova_senha })
      });
      if (res && res.success) {
        if (state.user) state.user.senha_redefinida = true;
        mostrarNotificacao(res.message || 'Palavra-passe redefinida com sucesso!', 'success');
        fecharModal();
      } else {
        alert(res?.message || 'Erro ao redefinir a palavra-passe.');
      }
    } catch (err) {
      alert(err.message || 'Erro ao redefinir a palavra-passe.');
    }
  });
}

function preencherLogin(email, senha) {
  if (document.getElementById('loginEmail')) document.getElementById('loginEmail').value = email;
  if (document.getElementById('loginSenha')) document.getElementById('loginSenha').value = senha;
}

async function realizarLogin(e) {
  if (e && e.preventDefault) e.preventDefault();
  const email = (document.getElementById('loginEmail')?.value || '').trim();
  const senha = document.getElementById('loginSenha')?.value || '';
  const feedbackEl = document.getElementById('loginFeedback');
  if (feedbackEl) {
    feedbackEl.className = 'mb-3 d-none';
    feedbackEl.innerHTML = '';
  }

  if (!email || !senha) {
    const inpEmail = document.getElementById('loginEmail');
    const inpSenha = document.getElementById('loginSenha');
    if (inpEmail) inpEmail.value = '';
    if (inpSenha) inpSenha.value = '';
    localStorage.removeItem('sige_ultimo_usuario');

    if (feedbackEl) {
      feedbackEl.className = 'alert alert-danger mb-3 py-2 px-3 small';
      feedbackEl.innerHTML = '<i class="bi bi-x-circle-fill me-1"></i> Credenciais invalidas.';
      feedbackEl.classList.remove('d-none');
    }
    alert('Credenciais invalidas.');

    if (inpEmail) setTimeout(() => inpEmail.focus(), 80);
    return;
  }

  const submitBtn = document.getElementById('btnLoginSubmit') || document.querySelector('#loginForm button[type="submit"]') || document.querySelector('button[onclick*="realizarLogin"]');
  const originalBtnHtml = submitBtn ? submitBtn.innerHTML : '';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> A autenticar...';
  }

  try {
    const apiUrl = formatarUrlApi('/api/v1/auth/login');
    const res = await fetch(apiUrl, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ 
        email, 
        senha,
        username: email,
        password: senha
      })
    });
    let json = null;
    try {
      json = await res.json();
    } catch (_) {}

    if (res.ok && json && json.success) {
      localStorage.setItem('sige_ultimo_usuario', email);
      sessionStorage.setItem('sige_token', json.data.tokens.accessToken);
      sessionStorage.setItem('sige_refresh_token', json.data.tokens.refreshToken);
      if (json.data.user.role !== 'SUPERADMIN') {
        localStorage.removeItem('sige_selected_tenant');
      }
      state.token = json.data.tokens.accessToken;
      state.refreshToken = json.data.tokens.refreshToken;
      state.user = json.data.user;
      state.tenant = json.data.escola;
      await iniciarApp();
    } else {
      const rawDetail = (json && (json.message || json.detail)) || '';
      const isBlocked = rawDetail && (
        rawDetail.toLowerCase().includes('bloque') ||
        rawDetail.toLowerCase().includes('inactiv') ||
        rawDetail.toLowerCase().includes('desactiv') ||
        rawDetail.toLowerCase().includes('subscri') ||
        rawDetail.toLowerCase().includes('expir')
      );

      let msgErro = 'Credenciais invalidas.';
      if (isBlocked) {
        msgErro = rawDetail;
      } else {
        msgErro = 'Credenciais invalidas.';
      }

      // Limpar logo/imediatamente o utilizador e a senha em caso de erro
      const inpEmail = document.getElementById('loginEmail');
      const inpSenha = document.getElementById('loginSenha');
      if (inpEmail) inpEmail.value = '';
      if (inpSenha) {
        inpSenha.value = '';
        inpSenha.type = 'password';
        const ico = document.getElementById('iconToggleLoginSenha');
        if (ico) ico.className = 'bi bi-eye fs-5';
      }
      localStorage.removeItem('sige_ultimo_usuario');

      if (feedbackEl) {
        feedbackEl.className = 'alert alert-danger mb-3 py-2 px-3 small';
        feedbackEl.innerHTML = `<i class="bi bi-x-circle-fill me-1"></i> ${escapeHtml(msgErro)}`;
        feedbackEl.classList.remove('d-none');
      }
      alert(msgErro);

      if (inpEmail) setTimeout(() => inpEmail.focus(), 80);
      return;
    }
  } catch (err) {
    console.error('Erro de conexão no login:', err);
    const msgConexao = 'Erro ao conectar ao servidor do SIGE: ' + (err.message || 'Verifique a sua ligação de rede.');
    if (feedbackEl) {
      feedbackEl.className = 'alert alert-warning mb-3 py-2 px-3 small';
      feedbackEl.innerHTML = `<i class="bi bi-wifi-off me-1"></i> ${escapeHtml(msgConexao)}`;
      feedbackEl.classList.remove('d-none');
    } else {
      alert(msgConexao);
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      if (originalBtnHtml) submitBtn.innerHTML = originalBtnHtml;
    }
  }
}

function fazerLogout(e) {
  if (e && e.preventDefault) e.preventDefault();
  const ultimoUsuario = localStorage.getItem('sige_ultimo_usuario');

  // Limpar especificamente as chaves de sessão do SIGE em sessionStorage
  try {
    for (let i = sessionStorage.length - 1; i >= 0; i--) {
      const k = sessionStorage.key(i);
      if (k && (k.startsWith('sige_') || k.startsWith('sigesaas_'))) {
        sessionStorage.removeItem(k);
      }
    }
  } catch (_) {}
  sessionStorage.removeItem('sige_token');
  sessionStorage.removeItem('sige_refresh_token');

  // Limpar chaves da aplicação em localStorage sem violar dados de terceiros, preservando último utilizador
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (k && (k.startsWith('sige_') || k.startsWith('sigesaas_')) && k !== 'sige_ultimo_usuario') {
        localStorage.removeItem(k);
      }
    }
  } catch (_) {}

  if (ultimoUsuario) {
    try {
      localStorage.setItem('sige_ultimo_usuario', ultimoUsuario);
    } catch (_) {}
  }

  document.body.classList.remove('role-superadmin');
  document.body.classList.remove('inspecionando-escola');
  state.token = null;
  state.refreshToken = null;
  state.user = null;
  state.tenant = null;
  state.materialEscolar = { classeAtiva: 'TODAS', materiais: [], classes: [] };
  
  if (typeof restaurarPadraoTemaEFundo === 'function') {
    restaurarPadraoTemaEFundo();
  }
  
  mostrarTelaLogin();
  window.location.reload();
}

function mostrarTelaLogin() {
  document.body.classList.remove('authenticated');
  document.body.classList.remove('role-superadmin');
  document.body.classList.remove('inspecionando-escola');
  document.querySelectorAll('.modulo-view').forEach(el => el.style.display = 'none');
  const appEl = document.getElementById('appView');
  if (appEl) appEl.style.display = 'none';
  const loginEl = document.getElementById('loginView');
  if (loginEl) loginEl.style.display = 'flex';

  if (typeof restaurarPadraoTemaEFundo === 'function') {
    restaurarPadraoTemaEFundo();
  }
}

async function iniciarApp() {
  if (!state.user) return;

  // Imediatamente exibir a aplicação principal e ocultar a tela de login
  document.body.classList.add('authenticated');
  const loginView = document.getElementById('loginView');
  if (loginView) loginView.style.display = 'none';
  const appView = document.getElementById('appView');
  if (appView) appView.style.display = 'flex';

  // Ocultar todas as vistas antes de activar o módulo correspondente ao perfil autenticado
  document.querySelectorAll('.modulo-view').forEach(el => el.style.display = 'none');

  // Cabeçalho e Utilizador Activo com verificação segura de existência de elementos
  const elUserName = document.getElementById('topbarUserName');
  if (elUserName) elUserName.textContent = state.user.nome || '';
  const elUserRole = document.getElementById('topbarUserRole');
  if (elUserRole) elUserRole.textContent = state.user.role || '';
  const elUserEmail = document.getElementById('dropdownUserEmail');
  if (elUserEmail) elUserEmail.textContent = state.user.email || '';

  // Formatação segura do Último Acesso e Quem Acessou (sem risco XSS)
  const elUltimoAcesso = document.getElementById('topbarUltimoAcesso');
  const elDropdownDetalhe = document.getElementById('dropdownUltimoAcessoDetalhe');
  const rawData = state.user.ultimo_acesso || state.user.last_login;
  const quemAcessou = state.user.ultimo_acesso_quem || state.user.nome || state.user.email || 'Utilizador';
  const quemEscapado = escapeHtml(quemAcessou);

  if (rawData) {
    const dtAcesso = new Date(rawData);
    const dataFormatada = dtAcesso.toLocaleDateString('pt-PT') + ' às ' + dtAcesso.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
    const dataEscapada = escapeHtml(dataFormatada);
    if (elUltimoAcesso) {
      elUltimoAcesso.innerHTML = `<i class="bi bi-clock-history me-1"></i>Último acesso: <strong>${dataEscapada}</strong> por <strong>${quemEscapado}</strong>`;
      elUltimoAcesso.title = `Último acesso ao sistema por ${quemAcessou} em ${dataFormatada}`;
    }
    if (elDropdownDetalhe) {
      elDropdownDetalhe.innerHTML = `<i class="bi bi-shield-check text-success me-1"></i>Último acesso: <strong>${dataEscapada}</strong> por <strong>${quemEscapado}</strong>`;
    }
  } else {
    const agora = new Date();
    const dataFormatada = agora.toLocaleDateString('pt-PT') + ' às ' + agora.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
    const dataEscapada = escapeHtml(dataFormatada);
    if (elUltimoAcesso) {
      elUltimoAcesso.innerHTML = `<i class="bi bi-clock-history me-1"></i>Acesso actual: <strong>${dataEscapada}</strong> por <strong>${quemEscapado}</strong>`;
    }
    if (elDropdownDetalhe) {
      elDropdownDetalhe.innerHTML = `<i class="bi bi-shield-check text-success me-1"></i>Primeiro acesso por <strong>${quemEscapado}</strong>`;
    }
  }

  // Configuração por Perfil de Utilizador (RBAC)
  aplicarPermissoesVisualizacao(state.user.role);

  // Carregar automaticamente todos os dados essenciais da instituição (turmas, disciplinas, docentes, alunos)
  carregarDadosGlobaisEscola();
  carregarAnosLectivos();

  const savedTenant = localStorage.getItem('sige_selected_tenant');

  if (state.user.role === 'SUPERADMIN') {
    document.body.classList.add('role-superadmin');
    const elSelectWrapper = document.getElementById('superAdminTenantSelectWrapper');
    if (elSelectWrapper) elSelectWrapper.style.display = 'block';
    carregarEscolasSuperAdminSelect();

    if (savedTenant) {
      // SuperAdmin está dentro de uma escola específica (Modo Inspecção)
      document.body.classList.add('inspecionando-escola');
      document.querySelectorAll('.escola-admin-only').forEach(el => el.style.display = 'flex');
      document.querySelectorAll('.ped-only').forEach(el => el.style.display = 'flex');
      document.querySelectorAll('.fin-only').forEach(el => el.style.display = 'flex');
      
      const nomeEscola = state.tenant?.nome || 'Escola Seleccionada';
      const elNome = document.getElementById('superAdminInspecaoNome');
      if (elNome) elNome.textContent = `A Inspecionar: ${nomeEscola}`;
      const elStatus = document.getElementById('superAdminInspecaoStatus');
      if (elStatus) elStatus.textContent = state.tenant?.status || 'ATIVA';
      navegarPara('dashboard');
    } else {
      document.body.classList.remove('inspecionando-escola');
      navegarPara('saas');
    }
  } else {
    // Utilizador Comum (Escolar, Docente, Aluno, Financeiro):
    // RESTRIÇÃO ABSOLUTA: O botão e banner de inspeção são SÓ E SÓ PARA O SUPERADMIN!
    document.body.classList.remove('role-superadmin');
    document.body.classList.remove('inspecionando-escola');
    localStorage.removeItem('sige_selected_tenant');

    if (state.user.role === 'ALUNO') {
      navegarPara('aluno-perfil');
    } else if (state.user.role === 'PROFESSOR') {
      navegarPara('caderneta');
    } else {
      // ADMIN_ESCOLA, DIRECTOR_ESCOLA, DAP, CHEFE_SECRETARIA
      document.getElementById('btnComprovativoEscola')?.classList.remove('d-none');
      navegarPara('dashboard');
    }
  }

  if (state.tenant) {
    atualizarBadgeTenant(state.tenant);
    if (typeof aplicarTemaEFundoInstituicao === 'function') {
      aplicarTemaEFundoInstituicao(state.tenant);
    }
    if (typeof atualizarBotaoToggleNotasDap === 'function') {
      atualizarBotaoToggleNotasDap(state.tenant.publicacao_notas_trimestre, state.tenant.permitir_visualizacao_notas !== false);
    }
  } else {
    // Se for SuperAdmin na Visão Master SaaS (sem tenant activo), garantir tema institucional oficial do SIGE
    if (typeof restaurarPadraoTemaEFundo === 'function') {
      restaurarPadraoTemaEFundo();
    }
  }
}

async function carregarDadosGlobaisEscola() {
  const isSuperAdminNoEscola = (state.user?.role === 'SUPERADMIN' && !localStorage.getItem('sige_selected_tenant'));
  if (isSuperAdminNoEscola) return;

  try {
    const [resTurmas, resDisc, resProfs, resAlunos] = await Promise.all([
      apiFetch('/api/v1/escola-admin/turmas', { ignoreAuthRedirect: true }),
      apiFetch('/api/v1/disciplinas', { ignoreAuthRedirect: true }),
      apiFetch('/api/v1/professores', { ignoreAuthRedirect: true }),
      apiFetch('/api/v1/alunos', { ignoreAuthRedirect: true })
    ]);
    if (resTurmas && resTurmas.success) {
      state.todasTurmas = resTurmas.data || [];
      state.turmasList = resTurmas.data || [];
    }
    if (resDisc && resDisc.success) {
      state.todasDisciplinas = resDisc.data || [];
    }
    if (resProfs && resProfs.success) {
      state.todosProfessores = resProfs.data || [];
    }
    if (resAlunos && resAlunos.success) {
      state.todosAlunos = resAlunos.data || [];
    }
  } catch (e) {
    console.warn('Carregamento inicial de dados globais da escola:', e);
  }
}

const MAPA_PAINEIS = {
  SUPERADMIN: 'painel-superadmin',
  ADMIN_ESCOLA: 'painel-escola',
  DIRECTOR_ESCOLA: 'painel-escola',
  DAP: 'painel-escola',
  CHEFE_SECRETARIA: 'painel-escola',
  PROFESSOR: 'painel-professor',
  ALUNO: 'painel-aluno',
  FINANCEIRO: 'painel-financeiro'
};

const MENUS_POR_PAINEL = {
  'painel-superadmin': [
    { id: 'saas', titulo: 'Gestão de Escolas & Planos', icone: 'bi-buildings-fill text-warning', categoria: 'Administração Geral SaaS' },
    { id: 'pagamentos-saas', titulo: 'Assinaturas & Pagamentos SaaS', icone: 'bi-credit-card-2-front-fill text-warning', categoria: 'Administração Geral SaaS' },
    { id: 'prompt-gateway', titulo: 'Gateway SMS & Pagamentos', icone: 'bi-broadcast-pin text-warning', categoria: 'Ferramentas & Integrações' },
    { id: 'usuarios-senhas', titulo: 'Cofre de Credenciais Master', icone: 'bi-key-fill text-warning', categoria: 'Segurança' },
    { id: 'acessos', titulo: 'Auditoria & Acessos Globais', icone: 'bi-shield-check', categoria: 'Segurança' }
  ],
  'painel-escola': [
    { id: 'dashboard', titulo: 'Painel Principal', icone: 'bi-grid-1x2-fill', categoria: 'Geral' },
    { id: 'escola', titulo: 'Definições & Logótipo', icone: 'bi-building-gear', categoria: 'Gestão Escolar' },
    { id: 'assinatura-escola', titulo: 'Assinatura do Sistema', icone: 'bi-shield-lock-fill text-warning', categoria: 'Gestão Escolar' },
    { id: 'turmas', titulo: 'Turmas & Capacidade', icone: 'bi-diagram-3-fill text-warning', categoria: 'Gestão Escolar' },
    { id: 'classes-exames', titulo: 'Classes / Níveis & Exames', icone: 'bi-layers-fill text-success', categoria: 'Gestão Escolar' },
    { id: 'alunos', titulo: 'Alunos & Matrículas', icone: 'bi-people-fill', categoria: 'Gestão Escolar' },
    { id: 'professores', titulo: 'Corpo Docente', icone: 'bi-person-badge-fill', categoria: 'Gestão Escolar' },
    { id: 'disciplinas', titulo: 'Disciplinas', icone: 'bi-book-fill', categoria: 'Gestão Escolar' },
    { id: 'desbloqueio', titulo: 'Desbloqueio de Trimestre', icone: 'bi-unlock-fill text-warning', categoria: 'Gestão Escolar' },
    { id: 'caderneta', titulo: 'Caderneta Pedagógica', icone: 'bi-journal-bookmark-fill text-info', categoria: 'Pedagógico' },
    { id: 'pautas', titulo: 'Pautas & Actas Oficiais', icone: 'bi-table', categoria: 'Pedagógico' },
    { id: 'exames', titulo: 'Exames', icone: 'bi-file-earmark-spreadsheet-fill text-warning', categoria: 'Pedagógico' },
    { id: 'director-turma', titulo: 'Painel Director de Turma', icone: 'bi-person-workspace text-warning', categoria: 'Pedagógico' },
    { id: 'estatisticas-aproveitamento', titulo: 'Estatística de Aproveitamento', icone: 'bi-bar-chart-line-fill text-success', categoria: 'Pedagógico' },
    { id: 'material-escolar', titulo: 'Material Escolar', icone: 'bi-book-half text-primary', categoria: 'Pedagógico' },
    { id: 'certificados', titulo: 'Certificados (QR Code)', icone: 'bi-award-fill', categoria: 'Financeiro & Secretaria' },
    { id: 'pagamentos', titulo: 'Mensalidades & Propinas', icone: 'bi-cash-coin', categoria: 'Financeiro & Secretaria' },
    { id: 'impressao', titulo: 'Central de Impressão', icone: 'bi-printer-fill', categoria: 'Financeiro & Secretaria' },
    { id: 'prompt-gateway', titulo: 'Gateway SMS & Pagamentos', icone: 'bi-broadcast-pin text-warning', categoria: 'Ferramentas & Integrações' },
    { id: 'usuarios-senhas', titulo: 'Cofre de Credenciais', icone: 'bi-key-fill text-warning', categoria: 'Segurança & Cofre' },
    { id: 'acessos', titulo: 'Auditoria & Acessos', icone: 'bi-shield-check', categoria: 'Segurança & Cofre' }
  ],
  'painel-professor': [
    { id: 'professor-perfil', titulo: 'Meu Perfil Docente', icone: 'bi-person-lines-fill text-primary', categoria: 'Espaço do Docente' },
    { id: 'caderneta', titulo: 'Caderneta do Professor', icone: 'bi-journal-bookmark-fill text-info', categoria: 'Espaço do Docente' },
    { id: 'pautas', titulo: 'Pautas & Actas Oficiais', icone: 'bi-table', categoria: 'Espaço do Docente' },
    { id: 'exames', titulo: 'Exames', icone: 'bi-file-earmark-spreadsheet-fill text-warning', categoria: 'Espaço do Docente' },
    { id: 'director-turma', titulo: 'Painel Director de Turma', icone: 'bi-person-workspace text-warning', categoria: 'Espaço do Docente' },
    { id: 'estatisticas-aproveitamento', titulo: 'Estatística das Minhas Turmas', icone: 'bi-bar-chart-line-fill text-success', categoria: 'Espaço do Docente' },
    { id: 'material-escolar', titulo: 'Material Didático & Escolar', icone: 'bi-book-half text-primary', categoria: 'Espaço do Docente' }
  ],
  'painel-aluno': [
    { id: 'aluno-perfil', titulo: 'O Meu Perfil & Filiação', icone: 'bi-person-vcard-fill text-primary', categoria: 'Espaço do Aluno' },
    { id: 'aluno-notas', titulo: 'As Minhas Notas & Boletim', icone: 'bi-card-checklist text-success', categoria: 'Espaço do Aluno' },
    { id: 'aluno-pagamentos', titulo: 'As Minhas Propinas & Mensalidades', icone: 'bi-wallet2 text-warning', categoria: 'Espaço do Aluno' },
    { id: 'material-escolar', titulo: 'Material Escolar da Minha Classe', icone: 'bi-book-half text-info', categoria: 'Espaço do Aluno' }
  ],
  'painel-financeiro': [
    { id: 'dashboard', titulo: 'Visão Geral Financeira', icone: 'bi-grid-1x2-fill', categoria: 'Financeiro & Tesouraria' },
    { id: 'pagamentos', titulo: 'Mensalidades & Propinas', icone: 'bi-cash-coin', categoria: 'Financeiro & Tesouraria' },
    { id: 'impressao', titulo: 'Central de Impressão de Recibos', icone: 'bi-printer-fill', categoria: 'Financeiro & Tesouraria' },
    { id: 'prompt-gateway', titulo: 'Gateway SMS & Pagamentos', icone: 'bi-broadcast-pin text-warning', categoria: 'Ferramentas & Integrações' }
  ]
};

function renderizarSidebarPorNivel(role) {
  const isSuperAdminInspecionando = (role === 'ADMIN_ESCOLA' && state.user?.role === 'SUPERADMIN' && !!localStorage.getItem('sige_selected_tenant'));
  const painel = MAPA_PAINEIS[role] || 'painel-escola';
  const menus = MENUS_POR_PAINEL[painel] || [];
  const navContainer = document.getElementById('sidebarNavItems');
  if (!navContainer) return;

  let html = '';
  if (isSuperAdminInspecionando) {
    const nomeEscola = state.tenant?.nome || 'Escola em Inspeção';
    html += `
      <div class="px-3 py-2 mb-3 bg-warning bg-opacity-25 border border-warning rounded text-dark small">
        <div class="d-flex align-items-center gap-1 mb-1 fw-bold">
          <i class="bi bi-eye-fill text-warning"></i> <span>A Inspecionar Escola:</span>
        </div>
        <div class="text-truncate fw-semibold mb-2" title="${nomeEscola}">${nomeEscola}</div>
        <button class="btn btn-dark btn-sm w-100 py-1" onclick="sairModoInspecaoSuperAdmin()">
          <i class="bi bi-box-arrow-left me-1"></i> Voltar ao SaaS
        </button>
      </div>
    `;
  }

  let categoriaAtual = '';

  menus.forEach(menu => {
    if (menu.categoria !== categoriaAtual) {
      categoriaAtual = menu.categoria;
      html += `<div class="nav-category">${categoriaAtual}</div>`;
    }
    html += `
      <a class="nav-link" href="#" onclick="navegarPara('${menu.id}')" id="nav-${menu.id}">
        <i class="bi ${menu.icone}"></i> <span>${menu.titulo}</span>
      </a>
    `;
  });

  html += `
    <div class="mt-4 pt-3 border-top px-2">
      <a class="nav-link text-light py-2 rounded d-flex align-items-center gap-2 mb-1" href="javascript:void(0)" onclick="modalRedefinirMinhaSenha()" title="Ver o meu perfil de utilizador e alterar palavra-passe">
        <i class="bi bi-person-gear text-warning fs-5"></i> <span>Meu Perfil & Alterar Senha</span>
      </a>
      <a class="nav-link text-danger fw-bold py-2 rounded d-flex align-items-center gap-2" href="#" onclick="fazerLogout(event)" id="nav-logout-sidebar" title="Terminar sessão com segurança">
        <i class="bi bi-box-arrow-right text-danger fs-5"></i> <span>Sair do Sistema</span>
      </a>
    </div>
  `;

  navContainer.innerHTML = html;
}

function aplicarPermissoesVisualizacao(role) {
  renderizarSidebarPorNivel(role);

  if (role === 'SUPERADMIN') {
    document.body.classList.add('role-superadmin');
    const isSuperAdminInspecionando = !!localStorage.getItem('sige_selected_tenant');
    if (isSuperAdminInspecionando) {
      document.body.classList.add('inspecionando-escola');
    } else {
      document.body.classList.remove('inspecionando-escola');
    }
    document.getElementById('superAdminTenantSelectWrapper')?.style.setProperty('display', 'block');
    document.getElementById('btnToggleNotasDap')?.style.setProperty('display', 'none');
    document.getElementById('btnComprovativoEscola')?.classList.add('d-none');
    document.getElementById('sidebarTenantCard')?.style.setProperty('display', 'block');
  } else {
    // RESTRIÇÃO TOTAL: O banner e o botão [Sair da Escola (Voltar ao SaaS)] NUNCA podem aparecer para outros papéis
    document.body.classList.remove('role-superadmin');
    document.body.classList.remove('inspecionando-escola');
    localStorage.removeItem('sige_selected_tenant');
    document.getElementById('superAdminTenantSelectWrapper')?.style.setProperty('display', 'none');

    if (role === 'ALUNO') {
      document.getElementById('btnToggleNotasDap')?.style.setProperty('display', 'none');
      document.getElementById('btnComprovativoEscola')?.classList.add('d-none');
      document.getElementById('sidebarTenantCard')?.style.setProperty('display', 'none');
    } else if (role === 'PROFESSOR') {
      document.getElementById('btnToggleNotasDap')?.style.setProperty('display', 'none');
      document.getElementById('btnComprovativoEscola')?.classList.add('d-none');
      document.getElementById('sidebarTenantCard')?.style.setProperty('display', 'block');
    } else if (role === 'FINANCEIRO') {
      document.getElementById('btnToggleNotasDap')?.style.setProperty('display', 'none');
      document.getElementById('btnComprovativoEscola')?.classList.add('d-none');
      document.getElementById('sidebarTenantCard')?.style.setProperty('display', 'block');
    } else {
      // ADMIN_ESCOLA, DIRECTOR_ESCOLA, DAP, CHEFE_SECRETARIA
      document.getElementById('btnToggleNotasDap')?.style.setProperty('display', 'flex');
      document.getElementById('btnComprovativoEscola')?.classList.remove('d-none');
      document.getElementById('sidebarTenantCard')?.style.setProperty('display', 'block');
    }
  }
}

function atualizarBadgeTenant(tenant) {
  if (!tenant) return;
  const elNome = document.getElementById('sidebarEscolaNome');
  if (elNome) elNome.textContent = tenant.nome || 'Escola';
  const badge = document.getElementById('sidebarStatusBadge');
  if (badge) {
    const st = tenant.status || 'ATIVA';
    badge.textContent = st;
    badge.className = `badge badge-${st.toLowerCase()} mt-1`;
  }

  const prov = tenant.provincia || 'Maputo';
  const elProv = document.getElementById('sidebarProvinciaBadge');
  if (elProv) elProv.textContent = prov;

  const elAno = document.getElementById('headerAnoLetivo');
  if (elAno) elAno.textContent = `Ano Lectivo: ${tenant.ano_letivo_ativo || 2026}`;

  const elEmblema = document.getElementById('sidebarEmblemaContainer');
  if (elEmblema) {
    if (tenant.usar_emblema_nacional) {
      elEmblema.innerHTML = '<img src="img/emblema-mocambique.png" alt="Emblema Nacional" style="width: 24px; height: 24px; object-fit: contain;">';
    } else if (tenant.logo_url || tenant.logo_base64) {
      const logoSrc = tenant.logo_url || tenant.logo_base64;
      elEmblema.innerHTML = `<img src="${escapeHtml(logoSrc)}" alt="Logo" style="width: 24px; height: 24px; object-fit: contain; border-radius: 4px;">`;
    } else {
      elEmblema.innerHTML = '<i class="bi bi-building text-warning fs-5"></i>';
    }
  }

  // Sincronizar anos lectivos da instituição
  carregarAnosLectivos();
}

// ==================== GESTÃO AUTOMÁTICA E BUSCA POR ANO LECTIVO ====================
async function carregarAnosLectivos() {
  try {
    const res = await apiFetch('/api/v1/anos-letivos', { ignoreAuthRedirect: true });
    if (res && res.success && Array.isArray(res.data) && res.data.length > 0) {
      state.anosLectivos = res.data;
      state.anoLetivoAtivo = res.ano_ativo || state.tenant?.ano_letivo_ativo || '2026';
    } else {
      gerarAnosLectivosFallback();
    }
  } catch (err) {
    console.warn('[ANOS-LECTIVOS] Falha ao carregar da API, gerando anos automaticamente:', err);
    gerarAnosLectivosFallback();
  }

  // Preencher todos os selectores de Ano Lectivo na interface
  renderizarSelectoresAnoLectivo();
}

function gerarAnosLectivosFallback() {
  const anoAtual = new Date().getFullYear();
  const anoAtivo = state.tenant?.ano_letivo_ativo || String(anoAtual);
  const ANO_INICIO = 2026;
  const anoMax = Math.max(ANO_INICIO, anoAtual);
  const anosSet = new Set();
  for (let y = ANO_INICIO; y <= anoMax; y++) {
    anosSet.add(String(y));
  }
  if (anoAtivo && anoAtivo.match(/^\d{4}$/) && parseInt(anoAtivo) >= ANO_INICIO) {
    anosSet.add(anoAtivo);
  }
  (state.todasTurmas || []).forEach(t => { 
    if (t.ano_letivo && parseInt(t.ano_letivo) >= ANO_INICIO) anosSet.add(String(t.ano_letivo)); 
  });
  (state.todosAlunos || []).forEach(a => { 
    if (a.ano_ingresso && parseInt(a.ano_ingresso) >= ANO_INICIO) anosSet.add(String(a.ano_ingresso)); 
  });

  const ordenados = Array.from(anosSet)
    .filter(y => y && y.match(/^\d{4}$/))
    .sort((a, b) => parseInt(b) - parseInt(a));

  state.anosLectivos = ordenados.map(ano => ({
    ano: ano,
    descricao: `Ano Lectivo de ${ano}`,
    ativo: (ano === anoAtivo)
  }));
  state.anoLetivoAtivo = anoAtivo;
}

function renderizarSelectoresAnoLectivo(anoSelecionado) {
  const anos = (state.anosLectivos && state.anosLectivos.length > 0) ? state.anosLectivos : [
    { ano: '2026', descricao: 'Ano Lectivo de 2026', ativo: true }
  ];

  const anoAtivo = state.anoLetivoAtivo || state.tenant?.ano_letivo_ativo || '2026';
  const anoSalvo = localStorage.getItem('sige_ano_letivo_selecionado');
  const valorAtivo = anoSelecionado || state.anoLectivoVisualizacao || anoSalvo || anoAtivo;

  // Montar as opções de acordo com o padrão exato da imagem:
  // -- Escolha ano Lectivo --
  // Ano Lectivo de 2026
  let htmlOpcoes = '<option value="">-- Escolha ano Lectivo --</option>';
  anos.forEach(item => {
    const anoStr = String(item.ano);
    const desc = item.descricao || `Ano Lectivo de ${anoStr}`;
    const sel = (anoStr === String(valorAtivo)) ? 'selected' : '';
    htmlOpcoes += `<option value="${anoStr}" ${sel}>${desc}</option>`;
  });

  const idsSelectores = [
    'headerSelectAnoLectivo',
    'filtroAnoAlunos',
    'filtroTurmasAno',
    'pautaAnoSelect',
    'statAnoFiltro',
    'filtroPagamentosAno'
  ];

  idsSelectores.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.innerHTML = htmlOpcoes;
      if (valorAtivo) el.value = valorAtivo;
    }
  });

  // Selectores por classe
  document.querySelectorAll('.sige-select-ano-lectivo').forEach(sel => {
    if (!idsSelectores.includes(sel.id)) {
      sel.innerHTML = htmlOpcoes;
      if (valorAtivo) sel.value = valorAtivo;
    }
  });

  // Atualizar badge de retrocompatibilidade
  const elBadge = document.getElementById('headerAnoLetivo');
  if (elBadge) {
    elBadge.textContent = `Ano Lectivo: ${valorAtivo || anoAtivo}`;
  }
}

function setCarregandoBuscaAno(carregando) {
  const btns = document.querySelectorAll('.btn-sige-buscar-ano, #headerBtnBuscarAno');
  btns.forEach(btn => {
    if (carregando) {
      if (!btn.dataset.origHtml) btn.dataset.origHtml = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" style="width: 0.85rem; height: 0.85rem;"></span><span style="font-size: 0.78rem;">A buscar...</span>';
    } else {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.origHtml || 'Buscar <i class="bi bi-search ms-1"></i>';
    }
  });

  const selects = document.querySelectorAll('.sige-select-ano-lectivo');
  selects.forEach(sel => {
    sel.style.opacity = carregando ? '0.7' : '1';
  });
}
window.setCarregandoBuscaAno = setCarregandoBuscaAno;

window.aoMudarSelectAnoLectivoGlobal = function(valor) {
  state.anoLectivoVisualizacao = valor;
  if (valor) {
    localStorage.setItem('sige_ano_letivo_selecionado', valor);
  } else {
    localStorage.removeItem('sige_ano_letivo_selecionado');
  }
  // Dependência exclusiva do botão Buscar: a alteração no seletor apenas define o ano sem disparar busca automática
};

window.executarBuscaAnoLectivoGlobal = async function() {
  const selHeader = document.getElementById('headerSelectAnoLectivo');
  const ano = (selHeader && selHeader.value) ? selHeader.value : (state.anoLectivoVisualizacao || state.anoLetivoAtivo || '2026');

  state.anoLectivoVisualizacao = ano;
  if (ano) {
    localStorage.setItem('sige_ano_letivo_selecionado', ano);
  }

  // Sincronizar em todos os selectores da interface
  renderizarSelectoresAnoLectivo(ano);

  // Ativar símbolo de carregamento visual no botão/seletor (sem mensagem toast)
  setCarregandoBuscaAno(true);

  try {
    await atualizarDadosModuloPorAno(ano);
  } catch (err) {
    console.error('[BUSCA-ANO] Erro ao carregar dados do ano lectivo:', err);
  } finally {
    setCarregandoBuscaAno(false);
  }
};

function obterViewAtiva() {
  if (state.currentView) return state.currentView;
  // Detecção pelo DOM da view que está visível
  const views = document.querySelectorAll('.modulo-view');
  for (const v of views) {
    if (v.style.display !== 'none' && !v.classList.contains('d-none')) {
      const vid = v.id.replace('view-', '');
      state.currentView = vid;
      return vid;
    }
  }
  const linkAtivo = document.querySelector('#sidebar .nav-link.active');
  if (linkAtivo) {
    const fn = linkAtivo.getAttribute('onclick') || '';
    const m = fn.match(/navegarPara\(['"]([^'"]+)['"]\)/);
    if (m) {
      state.currentView = m[1];
      return m[1];
    }
  }
  return 'dashboard';
}

async function atualizarDadosModuloPorAno(ano) {
  const view = obterViewAtiva();

  if (view === 'turmas' && typeof carregarTurmas === 'function') {
    await carregarTurmas(ano);
  } else if (view === 'alunos' && typeof carregarAlunos === 'function') {
    state.filtroAlunoAno = ano;
    await carregarAlunos(ano);
  } else if (view === 'pautas') {
    const sel = document.getElementById('pautaAnoSelect');
    if (sel) sel.value = ano;
    if (typeof carregarPautas === 'function') await carregarPautas(ano, true);
    else if (typeof alternarVisualizacaoPautaTurma === 'function') alternarVisualizacaoPautaTurma();
  } else if (view === 'estatisticas-aproveitamento') {
    const sel = document.getElementById('statAnoFiltro');
    if (sel) sel.value = ano;
    if (typeof carregarEstatisticasAproveitamento === 'function') await carregarEstatisticasAproveitamento(true);
  } else if (view === 'caderneta') {
    if (typeof carregarCadernetaDocente === 'function' && state.cadernetaAlocacaoSelecionadaId) await carregarCadernetaDocente(state.cadernetaAlocacaoSelecionadaId);
    else if (typeof inicializarNavegacaoCaderneta === 'function') await inicializarNavegacaoCaderneta(true);
  } else if (view === 'pagamentos' && typeof carregarPagamentos === 'function') {
    await carregarPagamentos();
  } else if (view === 'dashboard' && typeof carregarDashboardGeral === 'function') {
    await carregarDashboardGeral(ano, true);
  }
}


async function carregarEscolasSuperAdminSelect() {
  const select = document.getElementById('superAdminTenantSelect');
  if (!select) return;
  try {
    const res = await apiFetch('/api/v1/saas-admin/escolas');
    if (res && res.success && Array.isArray(res.data)) {
      select.innerHTML = '<option value="">(Visão Master SaaS)</option>' +
        res.data.map(e => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.nome)} [${escapeHtml(e.status)}]</option>`).join('');

      const saved = localStorage.getItem('sige_selected_tenant');
      if (saved) select.value = saved;
    }
  } catch (err) {
    console.warn('[SAAS] Falha ao carregar escolas no selector do SuperAdmin:', err);
  }
}

async function alternarEscolaSuperAdmin(escolaId, escolaNome = '', escolaStatus = '') {
  if (state.user?.role !== 'SUPERADMIN') {
    console.warn('[SEGURANÇA] Tentativa não autorizada de entrar em modo de inspeção.');
    return;
  }

  if (!escolaId) {
    sairModoInspecaoSuperAdmin();
    return;
  }

  // Limpar imediatamente estilos da escola anterior para garantir isolamento visual
  if (typeof restaurarPadraoTemaEFundo === 'function') {
    restaurarPadraoTemaEFundo();
  }

  const st = (escolaStatus || '').toUpperCase();
  // SÓ E SÓ O SUPER ADMIN DEVE TER ACESSO SEMPRE INDEPENDENTEMENTE DE A ESCOLA ESTAR OU NÃO ACTIVA.
  // O SuperAdmin possui privilégios totais de auditoria e inspeciona qualquer instituição sem bloqueio.

  try {
    localStorage.setItem('sige_selected_tenant', escolaId);
    state.materialEscolar = { classeAtiva: 'TODAS', materiais: [], classes: [] };
    state.filtroAlunoClasse = 'TODAS';
    state.filtroAlunoTurma = 'TODAS';
    const nomeLimpo = (escolaNome || '').replace(/\\'/g, "'");
    state.tenant = { id: escolaId, nome: nomeLimpo || 'Escola Seleccionada', status: st || 'ATIVA' };

    // Sincronizar o selector de tenants no topo
    const select = document.getElementById('superAdminTenantSelect');
    if (select) select.value = escolaId;

    // Actualizar badges da escola activa na barra lateral
    atualizarBadgeTenant(state.tenant);
    if (typeof atualizarBotaoToggleNotasDap === 'function') {
      atualizarBotaoToggleNotasDap(state.tenant.publicacao_notas_trimestre, state.tenant.permitir_visualizacao_notas !== false);
    }

    // Activar o banner de inspeção no topo (SÓ E SÓ PARA O SUPERADMIN)
    document.body.classList.add('role-superadmin');
    document.body.classList.add('inspecionando-escola');

    const bannerInspecao = document.getElementById('superAdminInspecaoBanner');
    if (bannerInspecao) {
      bannerInspecao.style.setProperty('display', 'flex', 'important');
      const elNome = document.getElementById('superAdminInspecaoNome');
      if (elNome) elNome.textContent = `A Inspecionar: ${state.tenant.nome}`;
      const elStatus = document.getElementById('superAdminInspecaoStatus');
      if (elStatus) elStatus.textContent = st || 'ATIVA';
    }

    // Re-renderizar sidebar para navegação escolar em modo inspeção
    renderizarSidebarPorNivel('ADMIN_ESCOLA');

    mostrarNotificacao(`Acesso directo concedido à instituição [${state.tenant.nome}] como SuperAdmin. Sem necessidade de credenciais.`, 'success');

    // Navegar imediatamente para o Painel Principal da escola selecionada
    navegarPara('dashboard');

    // Obter dados completos da escola seleccionada em segundo plano sem bloquear a navegação
    try {
      const res = await apiFetch('/api/v1/escola-admin/info', { ignoreAuthRedirect: true });
      if (res && res.success && res.data) {
        state.tenant = res.data;
        atualizarBadgeTenant(state.tenant);
        if (typeof aplicarTemaEFundoInstituicao === 'function') {
          aplicarTemaEFundoInstituicao(state.tenant);
        }
        const elNome = document.getElementById('superAdminInspecaoNome');
        if (elNome) elNome.textContent = `A Inspecionar: ${state.tenant.nome}`;
        const elStatus = document.getElementById('superAdminInspecaoStatus');
        if (elStatus) elStatus.textContent = state.tenant.status || 'ATIVA';
      }
      if (typeof carregarDadosGlobaisEscola === 'function') {
        carregarDadosGlobaisEscola();
      }
    } catch (infoErr) {
      console.warn('Carregamento secundário de info da escola:', infoErr);
    }
  } catch (err) {
    console.error('Erro ao alternar para a escola:', err);
    mostrarNotificacao('Não foi possível entrar na escola: ' + (err.message || 'Erro desconhecido'), 'danger');
  }
}

function sairModoInspecaoSuperAdmin() {
  document.body.classList.remove('inspecionando-escola');
  if (state.user?.role !== 'SUPERADMIN') {
    document.body.classList.remove('role-superadmin');
  }
  localStorage.removeItem('sige_selected_tenant');
  state.materialEscolar = { classeAtiva: 'TODAS', materiais: [], classes: [] };
  state.tenant = null;

  if (typeof restaurarPadraoTemaEFundo === 'function') {
    restaurarPadraoTemaEFundo();
  }

  const select = document.getElementById('superAdminTenantSelect');
  if (select) select.value = '';

  const bannerInspecao = document.getElementById('superAdminInspecaoBanner');
  if (bannerInspecao) bannerInspecao.style.setProperty('display', 'none', 'important');

  // Restaurar badge da sidebar para SIGE Master
  const elNome = document.getElementById('sidebarEscolaNome');
  if (elNome) elNome.textContent = 'SIGE';
  const elStatus = document.getElementById('sidebarStatusBadge');
  if (elStatus) elStatus.textContent = 'ATIVA';
  const elProv = document.getElementById('sidebarProvinciaBadge');
  if (elProv) elProv.textContent = 'SaaS Master';
  const elAno = document.getElementById('headerAnoLetivo');
  if (elAno) elAno.textContent = 'Ano Lectivo: 2026';
  const elEmblema = document.getElementById('sidebarEmblemaContainer');
  if (elEmblema) elEmblema.innerHTML = '<i class="bi bi-shield-lock text-warning fs-5"></i>';

  // Restaurar menus do SuperAdmin
  renderizarSidebarPorNivel('SUPERADMIN');

  mostrarNotificacao('Modo de inspeção encerrado. Retornou à Gestão Master SaaS.', 'info');
  navegarPara('saas');
}

// ==================== NAVEGAÇÃO ENTRE MÓDULOS & MENU MOBILE ====================
function alternarSidebarMobile() {
  document.body.classList.toggle('sidebar-mobile-open');
}

function fecharSidebarMobile() {
  document.body.classList.remove('sidebar-mobile-open');
}

window.alternarSidebarMobile = alternarSidebarMobile;
window.fecharSidebarMobile = fecharSidebarMobile;

const cachePaginasModular = {};

async function carregarPaginaModulo(painel, viewId) {
  // Verificação de actualização oportunista ao navegar entre módulos (a cada 30s)
  if (Date.now() - (sigeUpdateState.ultimoCheck || 0) > 30000) {
    sigeChecarVersaoServidor();
  }

  const container = document.getElementById('conteudo-modulo') || document.querySelector('main.content-area');
  if (!container) return null;

  const idSecao = `view-${viewId}`;
  let viewEl = document.getElementById(idSecao);
  if (viewEl && container.contains(viewEl)) {
    return viewEl;
  }

  const urlPagina = `/pages/${painel}/${viewId}.html`;
  try {
    let html = cachePaginasModular[urlPagina];
    if (!html) {
      const resp = await fetch(urlPagina);
      if (resp.ok) {
        html = await resp.text();
        cachePaginasModular[urlPagina] = html;
      }
    }

    if (!html && window.SIGE_TEMPLATES && window.SIGE_TEMPLATES[`${painel}/${viewId}`]) {
      html = window.SIGE_TEMPLATES[`${painel}/${viewId}`];
    }

    if (html) {
      const tempWrapper = document.createElement('div');
      tempWrapper.innerHTML = html;
      const novaSecao = tempWrapper.querySelector('section') || tempWrapper.firstElementChild;
      if (novaSecao) {
        novaSecao.style.display = 'none';
      }
      while (tempWrapper.firstChild) {
        container.appendChild(tempWrapper.firstChild);
      }
      return novaSecao;
    }
  } catch (err) {
    console.warn(`[ROUTER] Falha ao carregar página modular ${urlPagina}:`, err);
    if (window.SIGE_TEMPLATES && window.SIGE_TEMPLATES[`${painel}/${viewId}`]) {
      const html = window.SIGE_TEMPLATES[`${painel}/${viewId}`];
      const tempWrapper = document.createElement('div');
      tempWrapper.innerHTML = html;
      const novaSecao = tempWrapper.querySelector('section') || tempWrapper.firstElementChild;
      if (novaSecao) {
        novaSecao.style.display = 'none';
      }
      while (tempWrapper.firstChild) {
        container.appendChild(tempWrapper.firstChild);
      }
      return novaSecao;
    }
  }

  return document.getElementById(idSecao);
}

async function carregarScriptModulo(painel, viewId) {
  const idScript = `script-modulo-${painel}-${viewId}`;
  if (document.getElementById(idScript)) return;
  const scriptUrl = `/js/modules/${painel}/${viewId}.js`;
  return new Promise((resolve) => {
    const s = document.createElement('script');
    s.id = idScript;
    s.src = scriptUrl;
    s.onload = () => resolve();
    s.onerror = () => resolve();
    document.body.appendChild(s);
  });
}

function atualizarFaixaAlertaSaaS(estado) {
  const faixa = document.getElementById('faixaAlertaAssinaturaGlobal');
  if (faixa) {
    faixa.style.display = 'none';
  }
}

function tratarAcessoRestritoOuSuspenso(codigo, mensagem) {
  if (state.user?.role === 'SUPERADMIN') return;
  if (codigo === 'ASSINATURA_SUSPENSA') {
    const tela = document.getElementById('telaBloqueioSuspensao');
    if (tela) {
      tela.style.display = 'block';
      document.querySelectorAll('.modulo-view').forEach(el => el.style.display = 'none');
    }
    mostrarToast(mensagem || 'Acesso suspenso: regularize a subscrição.', 'danger');
  } else if (codigo === 'ASSINATURA_RESTRITA') {
    mostrarToast(mensagem || 'Operação bloqueada: o sistema encontra-se em modo de apenas leitura.', 'warning');
  }
}

async function navegarPara(viewId) {
  fecharSidebarMobile();

  const role = state.user?.role || 'ADMIN_ESCOLA';
  const isSuperAdminInspecionando = (role === 'SUPERADMIN' && !!localStorage.getItem('sige_selected_tenant'));
  const painel = isSuperAdminInspecionando 
    ? (['saas', 'pagamentos-saas', 'prompt-gateway', 'usuarios-senhas', 'acessos'].includes(viewId) ? 'painel-superadmin' : 'painel-escola')
    : (MAPA_PAINEIS[role] || 'painel-escola');

  const menusPermitidos = isSuperAdminInspecionando
    ? [...(MENUS_POR_PAINEL['painel-superadmin'] || []).map(m => m.id), ...(MENUS_POR_PAINEL['painel-escola'] || []).map(m => m.id)]
    : (MENUS_POR_PAINEL[painel] || []).map(m => m.id);

  // Isolamento estrito entre painéis: Não pode ter uma ligação entre os painéis!
  if (!menusPermitidos.includes(viewId)) {
    console.warn(`[SEGURANÇA] Bloqueio de ligação inter-painel: Utilizador com role '${role}' (Painel '${painel}') tentou aceder a view '${viewId}'.`);
    mostrarToast('Acesso negado: Este painel não pertence ao seu nível de acesso.', 'danger');
    viewId = menusPermitidos[0] || (role === 'SUPERADMIN' ? 'saas' : 'dashboard');
  }

  state.currentView = viewId;

  if (viewId === 'saas' && !isSuperAdminInspecionando) {
    if (typeof restaurarPadraoTemaEFundo === 'function') {
      restaurarPadraoTemaEFundo();
    }
  }

  // Carregar ficheiro de página (HTML) e módulo (JS) separados correspondentes a este menu
  await carregarPaginaModulo(painel, viewId);
  await carregarScriptModulo(painel, viewId);

  document.querySelectorAll('.modulo-view').forEach(el => el.style.display = 'none');
  document.querySelectorAll('#sidebar .nav-link').forEach(el => el.classList.remove('active'));

  const viewEl = document.getElementById(`view-${viewId}`);
  if (viewEl) viewEl.style.display = 'block';
  try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (_) {}

  // Marcar link como ativo na sidebar
  const link = document.getElementById(`nav-${viewId}`) || Array.from(document.querySelectorAll('#sidebar .nav-link')).find(a =>
    a.getAttribute('onclick')?.includes(viewId)
  );
  if (link) link.classList.add('active');

  // Actualizar Títulos de Topbar
  const menuInfo = (MENUS_POR_PAINEL[painel] || []).find(m => m.id === viewId);
  if (menuInfo && document.getElementById('pageTitle')) {
    document.getElementById('pageTitle').textContent = menuInfo.titulo;
  }
  if (document.getElementById('subPageTitle')) {
    const nomeNivel = {
      'painel-superadmin': 'Nível SuperAdmin SaaS',
      'painel-escola': 'Nível Gestão Escolar & Pedagógica',
      'painel-professor': 'Nível Docente',
      'painel-aluno': 'Nível Discente',
      'painel-financeiro': 'Nível Financeiro & Tesouraria'
    }[painel] || 'SIGE';
    document.getElementById('subPageTitle').textContent = nomeNivel;
  }

  // Sincronizar selectores de Ano Lectivo na view carregada
  renderizarSelectoresAnoLectivo();

  // Gatilhos de carregamento específico
  if (viewId === 'dashboard') carregarDashboardGeral(null, false);
  if (viewId === 'saas') carregarPainelSaaS();
  if (viewId === 'escola') carregarEscolaETurmas();
  if (viewId === 'turmas') carregarTurmas();
  if (viewId === 'classes-exames') { carregarPaginaClassesExames(); return; }
  if (viewId === 'alunos') carregarAlunos();
  if (viewId === 'professores') carregarProfessores();
  if (viewId === 'disciplinas') carregarDisciplinas();
  if (viewId === 'caderneta') inicializarNavegacaoCaderneta();
  if (viewId === 'pautas') carregarPautas(null, false);
  if (viewId === 'exames') carregarExames();
  if (viewId === 'director-turma') carregarPainelDirectorTurma();
  if (viewId === 'estatisticas-aproveitamento') carregarEstatisticasAproveitamento(false);
  if (viewId === 'material-escolar') carregarPainelMaterialEscolar();
  if (viewId === 'certificados') carregarCertificados();
  if (viewId === 'pagamentos') carregarPagamentos();
  if (viewId === 'impressao') prepararCentralImpressao();
  if (viewId === 'desbloqueio') prepararDesbloqueioTrimestre();
  if (viewId === 'aluno-perfil') carregarAlunoPerfil();
  if (viewId === 'aluno-notas') carregarAlunoNotas();
  if (viewId === 'aluno-pagamentos') carregarAlunoPagamentos();
  if (viewId === 'professor-perfil') carregarPerfilDocenteIndividual();
  if (viewId === 'usuarios-senhas') carregarCofreUsuarios();
  if (viewId === 'acessos') carregarLogsAcesso();
  if (viewId === 'prompt-gateway') carregarPromptGateway();

  setTimeout(() => aplicarResponsividadeUniversalTabelas(viewEl || document), 50);
}

// ==================== 1. DASHBOARD GERAL ====================
async function carregarDashboardGeral(anoParam = null, forcarBusca = false) {
  // Se chamado sem forçar a busca (ex: abertura inicial da view), omitir dados e exibir estado inicial
  if (!forcarBusca && !anoParam) {
    const elTotalAlunos = document.getElementById('statTotalAlunos');
    if (elTotalAlunos) elTotalAlunos.textContent = '-';
    const elAlunosAtivos = document.getElementById('statAlunosAtivos');
    if (elAlunosAtivos) elAlunosAtivos.textContent = '-';
    const elTotalProfs = document.getElementById('statTotalProfessores');
    if (elTotalProfs) elTotalProfs.textContent = '-';
    const elReceitaTotal = document.getElementById('statReceitaTotal');
    if (elReceitaTotal) elReceitaTotal.innerHTML = '-';
    const elReceitaPendente = document.getElementById('statReceitaPendente');
    if (elReceitaPendente) elReceitaPendente.innerHTML = '-';
    return;
  }
  try {
    const selAno = document.getElementById('headerSelectAnoLectivo');
    const ano = anoParam || (selAno ? selAno.value : null) || state.anoLectivoVisualizacao || localStorage.getItem('sige_ano_letivo_selecionado') || '2026';
    const queryAno = (ano && ano !== 'TODOS') ? ?ano_letivo= : '';
    const res = await apiFetch(/api/v1/dashboard/overview, { ignoreAuthRedirect: true });
    if (!res.success || !res.data) return;

    const data = res.data;
    const ind = data.indicadores || {
      totalAlunos: data.totalAlunos || 0,
      alunosAtivos: data.alunosAtivos || 0,
      totalProfessores: data.totalProfessores || 0,
      totalRecebido: data.propinasRecebidas || 0,
      totalPendente: data.propinasPendentes || 0,
    };
    const esc = data.escola || { nome: 'SIGE', status: 'ATIVA', diasRestantesAssinatura: 365 };

    const elTotalAlunos = document.getElementById('statTotalAlunos');
    if (elTotalAlunos) elTotalAlunos.textContent = ind.totalAlunos ?? 0;

    const elAlunosAtivos = document.getElementById('statAlunosAtivos');
    if (elAlunosAtivos) elAlunosAtivos.textContent = ind.alunosAtivos ?? 0;

    const elTotalProfs = document.getElementById('statTotalProfessores');
    if (elTotalProfs) elTotalProfs.textContent = ind.totalProfessores ?? 0;

    const elReceitaTotal = document.getElementById('statReceitaTotal');
    if (elReceitaTotal) elReceitaTotal.innerHTML = formatarMoeda(ind.totalRecebido || 0);

    const elReceitaPendente = document.getElementById('statReceitaPendente');
    if (elReceitaPendente) elReceitaPendente.innerHTML = formatarMoeda(ind.totalPendente || 0);

    const elDiasRestantes = document.getElementById('statDiasRestantes');
    if (elDiasRestantes) elDiasRestantes.textContent = (esc.diasRestantesAssinatura ?? 0) + ' dias';

    const stBadge = document.getElementById('statStatusAssinatura');
    if (stBadge) {
      stBadge.textContent = esc.status || 'ATIVA';
      stBadge.className = `badge badge-${(esc.status || 'ativa').toLowerCase()}`;
    }

    // Gráficos
    const resFin = await apiFetch('/api/v1/pagamentos/stats', { ignoreAuthRedirect: true });
    if (resFin && resFin.success && resFin.data) {
      renderizarGraficoDashboardFaturamento(resFin.data.historicoMeses || []);
    }

    const resAlunos = await apiFetch('/api/v1/alunos/stats', { ignoreAuthRedirect: true });
    if (resAlunos && resAlunos.success && resAlunos.data) {
      renderizarGraficoDashboardGenero(resAlunos.data.genero || resAlunos.data.porGenero || { M: 0, F: 0 });
    }
  } catch (err) {
    console.error('Erro ao carregar Dashboard Geral:', err);
  }
}

function renderizarGraficoDashboardFaturamento(historico) {
  const ctx = document.getElementById('chartDashboardFaturamento');
  if (!ctx) return;
  if (state.charts.dashboardFaturamento) state.charts.dashboardFaturamento.destroy();

  const labels = historico.map(h => h.mes);
  const recebido = historico.map(h => h.recebido);
  const pendente = historico.map(h => h.pendente);

  state.charts.dashboardFaturamento = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Recebido (MZN)', data: recebido, backgroundColor: '#10b981' },
        { label: 'Pendente (MZN)', data: pendente, backgroundColor: '#ef4444' }
      ]
    },
    options: { responsive: true, plugins: { legend: { position: 'top' } } }
  });
}

function renderizarGraficoDashboardGenero(genero) {
  const ctx = document.getElementById('chartDashboardGenero');
  if (!ctx) return;
  if (state.charts.dashboardGenero) state.charts.dashboardGenero.destroy();

  state.charts.dashboardGenero = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Masculino', 'Feminino'],
      datasets: [{
        data: [genero.M || 0, genero.F || 0],
        backgroundColor: ['#3b82f6', '#ec4899']
      }]
    },
    options: { responsive: true }
  });
}

// ==================== 2. SUPERADMIN SAAS ====================
async function carregarPainelSaaS() {
  try {
    const res = await apiFetch('/api/v1/saas-admin/metrics');
    if (res && res.success) {
      const d = res.data || res.metrics || {};
      const mrr = Number(d.mrr ?? d.receitaMensalEstimada ?? 0);
      const arr = Number(d.arr ?? (mrr * 12));
      const churn = Number(d.churn ?? 0);
      const totalEscolas = d.escolas?.total ?? d.totalEscolas ?? 0;
      const ativas = d.escolas?.ativas ?? d.escolasAtivas ?? 0;
      const expiradas = d.escolas?.expiradas ?? d.escolasExpiradas ?? 0;

      const elMRR = document.getElementById('saasMRR');
      if (elMRR) elMRR.innerHTML = formatarMoeda(mrr);

      const elARR = document.getElementById('saasARR');
      if (elARR) elARR.innerHTML = formatarMoeda(arr);

      const elChurn = document.getElementById('saasChurn');
      if (elChurn) elChurn.textContent = churn + '%';

      const elTotal = document.getElementById('saasTotalEscolas');
      if (elTotal) elTotal.textContent = totalEscolas;

      const elAtivas = document.getElementById('saasEscolasAtivas');
      if (elAtivas) elAtivas.textContent = ativas;

      const elExpiradas = document.getElementById('saasEscolasExpiradas');
      if (elExpiradas) elExpiradas.textContent = expiradas;
    }

    // Tabela de Escolas
    const resEscolas = await apiFetch('/api/v1/saas-admin/escolas');
    if (resEscolas && resEscolas.success && Array.isArray(resEscolas.data)) {
      const tbody = document.getElementById('tabelaSaasEscolas');
      if (tbody) {
        if (resEscolas.data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">Nenhuma escola cadastrada no momento.</td></tr>';
        } else {
          tbody.innerHTML = resEscolas.data.map(e => {
            const ass = (e.assinaturas && e.assinaturas[0]) || e.assinatura_ativa || null;
            const dataFim = ass?.data_fim ? new Date(ass.data_fim).toLocaleDateString('pt-PT') : '-';
            const isAtiva = e.status === 'ATIVA';
            const emblemaIcon = e.usar_emblema_nacional 
              ? '<span class="badge bg-warning text-dark me-1" title="Emblema Nacional">🇲🇿 Emblema</span>' 
              : '';
            const valorContratoNum = Number(ass?.valor_pago ?? ass?.valor ?? e.plano?.preco ?? 0);
            const valorContrato = formatarMoeda(valorContratoNum);
            const planoNome = e.plano?.nome || e.plano_nome || 'MENSAL';
            const totalAlunos = e._count?.alunos ?? e.total_alunos ?? 0;
            const totalProfs = e._count?.professores ?? e.total_professores ?? 0;
            const nomeEscapado = (e.nome || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            const codEscola = e.codigo_escola || '0101S0001';
            const codGD = e.codigo_gabinete_director || `GD${codEscola}`;
            const codDP = e.codigo_direccao_pedagogica || `DP${codEscola}`;
            const codSECR = e.codigo_secretaria || `SECR${codEscola}`;

            return `
              <tr>
                <td>
                  <div class="d-flex align-items-center gap-2">
                    <div>
                      <span class="badge bg-primary font-monospace me-1" title="Código Único Oficial da Escola">${escapeHtml(codEscola)}</span>
                      <strong>${escapeHtml(e.nome)}</strong> ${emblemaIcon}
                      <br><small class="text-muted">${escapeHtml(e.email)} | ${escapeHtml(e.telefone || '-')}</small>
                      <div class="mt-1 d-flex flex-wrap gap-1">
                        <span class="badge bg-light text-primary border font-monospace" style="font-size: 0.68rem;" title="Gabinete do Director (Admin Geral)">${escapeHtml(codGD)}</span>
                        <span class="badge bg-light text-info border font-monospace" style="font-size: 0.68rem;" title="Direcção Pedagógica (Sub-Admin)">${escapeHtml(codDP)}</span>
                        <span class="badge bg-light text-secondary border font-monospace" style="font-size: 0.68rem;" title="Chefe da Secretaria">${escapeHtml(codSECR)}</span>
                      </div>
                    </div>
                  </div>
                </td>
                <td><small>${escapeHtml(e.provincia || '-')}<br><span class="text-muted">${escapeHtml(e.distrito || '-')}</span></small></td>
                <td><code>${escapeHtml(e.nif_cnpj)}</code></td>
                <td>
                  <span class="badge bg-light text-dark border">${escapeHtml(planoNome)}</span>
                  <br><strong class="small text-success">${valorContrato}</strong>
                </td>
                <td><small>${escapeHtml(dataFim)}</small></td>
                <td><span class="badge badge-${escapeHtml((e.status || 'ativa').toLowerCase())}">${escapeHtml(e.status)}</span></td>
                <td><small>${totalAlunos} alunos<br>${totalProfs} profs</small></td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <!-- Botão Entrar como Escola -->
                    <button class="btn btn-primary" title="Entrar na Escola como SuperAdmin (Acesso Imediato sem Credenciais)" onclick="alternarEscolaSuperAdmin('${escapeHtml(e.id)}', '${escapeHtml(nomeEscapado)}')">
                      <i class="bi bi-box-arrow-in-right me-1"></i> Entrar
                    </button>
                    <!-- Botão Toggle Ativar / Desativar -->
                    <button class="btn ${isAtiva ? 'btn-outline-danger' : 'btn-outline-success'}" 
                            title="${isAtiva ? 'Desactivar Escola' : 'Activar Escola'}"
                            onclick="toggleStatusEscola('${escapeHtml(e.id)}', '${escapeHtml(nomeEscapado)}', '${escapeHtml(e.status)}')">
                      <i class="bi ${isAtiva ? 'bi-toggle-on text-success' : 'bi-toggle-off text-danger'}"></i>
                      ${isAtiva ? 'Activa' : 'Inactiva'}
                    </button>
                    <!-- Botão Editar Dados e Prazo -->
                    <button class="btn btn-outline-primary" title="Editar Dados & Prazo" onclick="modalEditarEscolaSuperAdmin('${escapeHtml(e.id)}')">
                      <i class="bi bi-pencil"></i>
                    </button>
                    <!-- Botão Descarregar Extrato / Contrato -->
                    <button class="btn btn-outline-info" title="Descarregar Extrato / Contrato da Escola" onclick="descarregarExtratoEscolaSuperAdmin('${e.id}')">
                      <i class="bi bi-file-earmark-pdf"></i>
                    </button>
                    <!-- Botão Eliminar Escola (Exclusivo SuperAdmin) -->
                    <button class="btn btn-outline-danger" title="Eliminar Escola Definitivamente" onclick="eliminarEscolaSuperAdmin('${e.id}', '${nomeEscapado}', '${e.codigo_escola || ''}')">
                      <i class="bi bi-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
            `;
          }).join('');
        }
      }
    }

    // Tabela de Preços dos Planos
    const resPlanos = await apiFetch('/api/v1/saas-admin/planos');
    if (resPlanos && resPlanos.success && Array.isArray(resPlanos.data)) {
      const tbodyPlanos = document.getElementById('tabelaSaasPlanos');
      if (tbodyPlanos) {
        if (resPlanos.data.length === 0) {
          tbodyPlanos.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">Nenhum plano cadastrado.</td></tr>';
        } else {
          tbodyPlanos.innerHTML = resPlanos.data.map(p => {
            const precoNum = Number(p.preco || 0);
            return `
              <tr>
                <td><strong>${p.nome}</strong></td>
                <td>${p.duracao_dias} dias</td>
                <td><strong class="text-primary">${formatarMoeda(precoNum)}</strong></td>
                <td><small class="text-muted">${p.descricao || 'Plano de subscrição SIGE'}</small></td>
                <td class="text-end">
                  <button class="btn btn-outline-primary btn-sm" onclick="modalEditarPrecoPlano('${p.id}', '${p.nome}', ${precoNum})">
                    <i class="bi bi-currency-exchange me-1"></i> Alterar Preço
                  </button>
                </td>
              </tr>
            `;
          }).join('');
        }
      }
    }
  } catch (err) {
    console.error('Erro ao carregar Painel SaaS:', err);
  }
}

// ==================== UTILITÁRIOS DE PREVIEW DE CÓDIGOS OFICIAIS (ESCOLA, ÓRGÃOS, ALUNO, DT/DC) ====================
window.gerarPreviewCodigoEscola = function(provincia, distrito, tipoEscola, nomeEscola = '', seqNum = 1) {
  const provs = state.geografia?.provincias || [
    'Maputo Cidade', 'Maputo Província', 'Gaza', 'Inhambane', 'Sofala',
    'Manica', 'Tete', 'Zambézia', 'Nampula', 'Cabo Delgado', 'Niassa'
  ];
  let idxProv = provs.findIndex(p => p.toLowerCase() === (provincia || '').trim().toLowerCase());
  const codProv = String(idxProv >= 0 ? idxProv + 1 : 1).padStart(2, '0');

  const dists = (state.geografia?.distritos && state.geografia.distritos[provincia]) || [];
  let idxDist = dists.findIndex(d => d.toLowerCase() === (distrito || '').trim().toLowerCase());
  const codDist = String(idxDist >= 0 ? idxDist + 1 : 1).padStart(2, '0');

  let letra = (tipoEscola || '').toUpperCase().trim();
  if (!['P', 'B', 'S'].includes(letra)) {
    const nLow = (nomeEscola || '').toLowerCase();
    if (nLow.includes('primária') || nLow.includes('primaria') || nLow.includes('ep1') || nLow.includes('ep2')) letra = 'P';
    else if (nLow.includes('básica') || nLow.includes('basica') || nLow.includes('eb')) letra = 'B';
    else letra = 'S';
  }

  const numEscola = String(seqNum || 1).padStart(4, '0');
  const codigo_escola = `${codProv}${codDist}${letra}${numEscola}`;
  return {
    codigo_escola,
    codigo_gd: `GD${codigo_escola}`,
    codigo_dp: `DP${codigo_escola}`,
    codigo_secr: `SECR${codigo_escola}`
  };
};

window.obterSiglaAreaEstudo = function(areaStr, classeStr = '') {
  const s = (areaStr || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
  if (s.includes('ciencias') && s.includes('geografia')) return 'cg';
  if (s.includes('ciencias') && s.includes('biologia')) return 'cb';
  if (s.includes('ciencias') && s.includes('desenho')) return 'cd';
  if (s.includes('letras') && s.includes('geografia')) return 'lg';
  if (s.includes('letras') && s.includes('historia')) return 'lh';
  if (s === 'cg' || s === 'cb' || s === 'cd' || s === 'lg' || s === 'lh' || s === 'eg') return s;
  if (s.includes('ciencias')) return 'cn';
  if (s.includes('letras')) return 'lt';
  if (s.includes('tecnic')) return 'tc';
  const clsDigits = String(classeStr || '').replace(/\D/g, '');
  if (clsDigits === '11' || clsDigits === '12') return 'cg';
  return 'eg';
};

window.gerarPreviewCodigoAluno = function(codigoEscola, classeStr, turmaNome, anoStr, areaStr) {
  const codEsc = (codigoEscola || state.escolaAtual?.codigo_escola || state.tenant?.codigo_escola || '0101S0001').toUpperCase();
  const clsNum = parseInt(String(classeStr || '10').replace(/\D/g, '')) || 10;
  const cls2d = String(clsNum).padStart(2, '0');

  let tNum = 1;
  if (turmaNome) {
    const idInfo = typeof window.extrairIdentificadorTurma === 'function'
      ? window.extrairIdentificadorTurma(turmaNome, classeStr)
      : { tipo: 'NUMERO', val: 1 };
    if (idInfo.tipo === 'NUMERO' && idInfo.val > 0) tNum = idInfo.val;
    else if (idInfo.tipo === 'LETRA' && idInfo.val) tNum = Math.max(1, idInfo.val.charCodeAt(0) - 64);
  }
  const turma2d = String(tNum).padStart(2, '0');
  const ano4d = String(anoStr || state.tenant?.ano_letivo_ativo || '2026').slice(0, 4);
  const siglaArea = window.obterSiglaAreaEstudo(areaStr, classeStr);
  return `${codEsc}.${cls2d}.${turma2d}.${ano4d}.${siglaArea}`;
};

window.atualizarPreviewModalCadastroEscola = function() {
  const prov = document.getElementById('cadEscolaProvincia')?.value || 'Maputo Cidade';
  const dist = document.getElementById('cadEscolaDistrito')?.value || '';
  const tipo = document.getElementById('cadEscolaTipo')?.value || 'S';
  const nome = document.getElementById('cadEscolaNome')?.value || '';
  const prev = window.gerarPreviewCodigoEscola(prov, dist, tipo, nome, 1);

  const elEsc = document.getElementById('cadPreviewCodEscola');
  const elGD = document.getElementById('cadPreviewCodGD');
  const elDP = document.getElementById('cadPreviewCodDP');
  const elSECR = document.getElementById('cadPreviewCodSECR');
  if (elEsc) elEsc.textContent = prev.codigo_escola;
  if (elGD) elGD.textContent = prev.codigo_gd;
  if (elDP) elDP.textContent = prev.codigo_dp;
  if (elSECR) elSECR.textContent = prev.codigo_secr;
};


async function toggleStatusEscola(escolaId, nome, statusAtual) {
  const proximo = statusAtual === 'ATIVA' ? 'SUSPENSA' : 'ATIVA';
  if (!confirm(`Confirma a alteração de estado da escola [${nome}] para ${proximo}?`)) return;

  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/toggle-status`, {
      method: 'PATCH'
    });
    if (res.success) {
      alert(res.message);
      carregarPainelSaaS();
    }
  } catch (err) {
    alert('Erro ao alterar estado da escola.');
  }
}

async function modalCadastrarEscolaSuperAdmin() {
  const planosRes = await apiFetch('/api/v1/saas-admin/planos');
  const optPlanos = (planosRes.data || []).map(p => 
    `<option value="${p.id}">${p.nome} (${p.duracao_dias} dias) — ${p.preco.toLocaleString('pt-PT')} MZN</option>`
  ).join('');

  const optProvincias = (state.geografia.provincias || []).map(p => `<option value="${p}">${p}</option>`).join('');

  abrirModal('Cadastrar Nova Escola no SIGE', `
    <form id="formModalCadastrarEscola">
      <!-- Painel de Pré-visualização Automática dos Códigos Oficiais -->
      <div class="alert alert-primary border-primary bg-primary bg-opacity-10 py-2 px-3 mb-3">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div>
            <small class="fw-bold text-primary d-block"><i class="bi bi-upc-scan me-1"></i> Geração Automática do Código Único da Escola & Órgãos:</small>
            <small class="text-muted" style="font-size: 0.73rem;">[2 díg. Província] + [2 díg. Distrito] + [P/B/S Nível] + [Nº Escola]</small>
          </div>
          <span class="badge bg-primary fs-6 font-monospace px-3 py-2" id="cadPreviewCodEscola">0101S0001</span>
        </div>
        <div class="row g-2 mt-1 pt-2 border-top border-primary border-opacity-25 text-center small">
          <div class="col-4">
            <span class="text-muted d-block" style="font-size: 0.7rem;">Gabinete do Director (Admin Geral)</span>
            <code class="fw-bold text-primary" id="cadPreviewCodGD">GD0101S0001</code>
          </div>
          <div class="col-4">
            <span class="text-muted d-block" style="font-size: 0.7rem;">Direcção Pedagógica (Sub-Admin)</span>
            <code class="fw-bold text-info" id="cadPreviewCodDP">DP0101S0001</code>
          </div>
          <div class="col-4">
            <span class="text-muted d-block" style="font-size: 0.7rem;">Chefe da Secretaria</span>
            <code class="fw-bold text-secondary" id="cadPreviewCodSECR">SECR0101S0001</code>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-md-5">
          <label class="form-label small fw-semibold">Nome da Instituição</label>
          <input type="text" id="cadEscolaNome" class="form-control" required placeholder="Ex: Escola Secundária de Massinga" oninput="atualizarPreviewModalCadastroEscola()">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-bold text-primary">Nível / Tipo de Escola</label>
          <select id="cadEscolaTipo" class="form-select border-primary fw-semibold" onchange="atualizarPreviewModalCadastroEscola()" required>
            <option value="S" selected>S — Escola Secundária</option>
            <option value="B">B — Escola Básica</option>
            <option value="P">P — Escola Primária</option>
          </select>
        </div>
        <div class="col-md-3">
          <label class="form-label small fw-semibold">NUIT da Escola</label>
          <input type="text" id="cadEscolaNUIT" class="form-control" required placeholder="Ex: 400123456 (máx. 9 dígitos)" maxlength="9" inputmode="numeric" pattern="[0-9]{1,9}">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">E-mail Administrativo</label>
          <input type="email" id="cadEscolaEmail" class="form-control" required placeholder="secretaria@escola.edu.mz">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Telefone (+258 Padrão)</label>
          <input type="tel" id="cadEscolaTelefone" class="form-control" value="+258 " required inputmode="tel" placeholder="+258 ...">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Província (Dígitos 1 e 2)</label>
          <select id="cadEscolaProvincia" class="form-select" onchange="atualizarDistritosCadastroEscola(this.value); atualizarPreviewModalCadastroEscola();" required>
            <option value="">Selecione a Província</option>
            ${optProvincias}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Distrito (Dígitos 3 e 4)</label>
          <select id="cadEscolaDistrito" class="form-select" onchange="atualizarPreviewModalCadastroEscola()" required>
            <option value="">Selecione primeiro a província</option>
          </select>
        </div>

        <div class="col-md-7">
          <label class="form-label small fw-semibold">Plano de Subscrição Inicial</label>
          <select id="cadEscolaPlano" class="form-select" required>${optPlanos}</select>
        </div>
        <div class="col-md-5">
          <label class="form-label small fw-semibold">Valor do Contrato (MZN)</label>
          <input type="number" id="cadEscolaValor" class="form-control" placeholder="Valor acordado em MZN">
        </div>

        <div class="col-md-4">
          <label class="form-label small fw-semibold">Director da Escola (GD - Admin Geral)</label>
          <input type="text" id="cadEscolaAdminNome" class="form-control" placeholder="Nome do Director da Escola">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Director Pedagógico (DP - Sub-Admin)</label>
          <input type="text" id="cadEscolaDapNome" class="form-control" placeholder="Nome do Director Pedagógico">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Chefe da Secretaria (SECR)</label>
          <input type="text" id="cadEscolaChefeSecNome" class="form-control" placeholder="Nome do Chefe da Secretaria">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">E-mail do Director / Admin (Opcional)</label>
          <input type="email" id="cadEscolaAdminEmail" class="form-control" placeholder="director@escola.edu.mz">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Senha Inicial dos Órgãos (Opcional)</label>
          <input type="password" id="cadEscolaAdminSenha" class="form-control" placeholder="123456 (Padrão)">
        </div>

        <div class="col-12">
          <div class="form-check">
            <input class="form-check-input" type="checkbox" id="cadEscolaEmblema" checked>
            <label class="form-check-label small fw-semibold" for="cadEscolaEmblema">
              Utilizar Emblema Oficial nos documentos e pautas
            </label>
          </div>
        </div>

        <div class="col-12">
          <label class="form-label small fw-semibold">Logótipo da Escola (Opcional)</label>
          <div class="row g-2">
            <div class="col-md-6">
              <label class="form-label x-small text-muted mb-1">Carregar Imagem do Computador</label>
              <input type="file" id="cadEscolaLogoFile" accept="image/*" class="form-control form-control-sm" onchange="processarLogoCadastroLocal(this)">
            </div>
            <div class="col-md-6">
              <label class="form-label x-small text-muted mb-1">Ou Link / URL Web</label>
              <input type="url" id="cadEscolaLogo" class="form-control form-control-sm" placeholder="https://escola.edu.mz/logo.png">
            </div>
          </div>
          <input type="hidden" id="cadEscolaLogoBase64" value="">
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4">Concluir Cadastro da Escola & Gerar Códigos Oficiais</button>
    </form>
  `);

  document.getElementById('formModalCadastrarEscola').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const logoFinal = document.getElementById('cadEscolaLogoBase64')?.value || document.getElementById('cadEscolaLogo')?.value || undefined;
      const body = {
        nome: document.getElementById('cadEscolaNome').value,
        tipo_escola: document.getElementById('cadEscolaTipo')?.value || 'S',
        nif_cnpj: document.getElementById('cadEscolaNUIT').value,
        email: document.getElementById('cadEscolaEmail').value,
        telefone: document.getElementById('cadEscolaTelefone').value,
        provincia: document.getElementById('cadEscolaProvincia').value,
        distrito: document.getElementById('cadEscolaDistrito').value,
        plano_id: document.getElementById('cadEscolaPlano').value,
        valor_contrato: Number(document.getElementById('cadEscolaValor').value) || undefined,
        adminNome: document.getElementById('cadEscolaAdminNome')?.value || undefined,
        dap_nome: document.getElementById('cadEscolaDapNome')?.value || undefined,
        chefe_secretaria_nome: document.getElementById('cadEscolaChefeSecNome')?.value || undefined,
        adminEmail: document.getElementById('cadEscolaAdminEmail')?.value || undefined,
        adminSenha: document.getElementById('cadEscolaAdminSenha')?.value || undefined,
        usar_emblema_nacional: document.getElementById('cadEscolaEmblema').checked,
        logo_url: logoFinal
      };

      const res = await apiFetch('/api/v1/saas-admin/escolas', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success) {
        const escData = res.data?.escola || res.data || {};
        const codEscola = escData.codigo_escola || '';
        const codGD = escData.codigo_gabinete_director || (codEscola ? `GD${codEscola}` : '');
        const codDP = escData.codigo_direccao_pedagogica || (codEscola ? `DP${codEscola}` : '');
        const codSECR = escData.codigo_secretaria || (codEscola ? `SECR${codEscola}` : '');
        const senhaPadrao = body.adminSenha || '123456';

        const msg = `Escola cadastrada com sucesso no SIGE!\n\n` +
          `CÓDIGO ÚNICO DA ESCOLA: ${codEscola}\n\n` +
          `CÓDIGOS DE ACESSO DOS ÓRGÃOS DE DIRECÇÃO:\n` +
          `• Director da Escola (Admin Geral): ${codGD}\n` +
          `• Direcção Pedagógica (Sub-Admin): ${codDP}\n` +
          `• Chefe da Secretaria (Secretaria): ${codSECR}\n` +
          `• Senha Inicial: ${senhaPadrao}\n\n` +
          `Guarde e forneça estes códigos oficiais à Direcção da Escola.`;
        alert(msg);
        fecharModal();
        carregarPainelSaaS();
      }
    } catch (err) {
      alert(err.message || 'Erro ao cadastrar escola');
    }
  });
}

function atualizarDistritosCadastroEscola(provincia) {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('cadEscolaDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => `<option value="${d}">${d}</option>`).join('');
  }
}

async function modalEditarEscolaSuperAdmin(escolaId) {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas`);
    const escola = res.data.find(e => e.id === escolaId);
    if (!escola) return alert('Escola não encontrada');

    const ass = escola.assinaturas && escola.assinaturas[0];
    const dataFimStr = ass ? new Date(ass.data_fim).toISOString().split('T')[0] : '';
    const optProvincias = (state.geografia.provincias || []).map(p => 
      `<option value="${p}" ${p === escola.provincia ? 'selected' : ''}>${p}</option>`
    ).join('');
    const codEscola = escola.codigo_escola || '0101S0001';

    abrirModal(`Editar Escola: ${escola.nome} [${codEscola}]`, `
      <form id="formModalEditarEscola">
        <div class="alert alert-light border py-2 px-3 mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div class="small">
            <strong>Código Único da Escola:</strong> <code class="fs-6 fw-bold text-primary ms-1">${codEscola}</code>
          </div>
          <div class="d-flex gap-2 small">
            <span class="badge bg-primary-subtle text-primary border font-monospace">GD: ${escola.codigo_gabinete_director || 'GD' + codEscola}</span>
            <span class="badge bg-info-subtle text-info-emphasis border font-monospace">DP: ${escola.codigo_direccao_pedagogica || 'DP' + codEscola}</span>
            <span class="badge bg-secondary-subtle text-secondary-emphasis border font-monospace">SECR: ${escola.codigo_secretaria || 'SECR' + codEscola}</span>
          </div>
        </div>
        <div class="row g-3">
          <div class="col-md-5">
            <label class="form-label small fw-semibold">Nome da Instituição</label>
            <input type="text" id="editEscolaNome" class="form-control" value="${escola.nome}" required>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-bold text-primary">Nível / Tipo de Escola</label>
            <select id="editEscolaTipo" class="form-select border-primary fw-semibold">
              <option value="S" ${(escola.tipo_escola || 'S') === 'S' ? 'selected' : ''}>S — Escola Secundária</option>
              <option value="B" ${escola.tipo_escola === 'B' ? 'selected' : ''}>B — Escola Básica</option>
              <option value="P" ${escola.tipo_escola === 'P' ? 'selected' : ''}>P — Escola Primária</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">NUIT</label>
            <input type="text" id="editEscolaNUIT" class="form-control" value="${escola.nif_cnpj}" required maxlength="9" inputmode="numeric" pattern="[0-9]{1,9}" placeholder="9 dígitos">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">E-mail</label>
            <input type="email" id="editEscolaEmail" class="form-control" value="${escola.email}" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Telefone</label>
            <input type="tel" id="editEscolaTelefone" class="form-control" value="${escola.telefone || '+258 '}" inputmode="tel" placeholder="+258 ...">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Data de Vencimento do Contrato</label>
            <input type="date" id="editEscolaDataFim" class="form-control" value="${dataFimStr}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Estender Prazo (Dias Adicionais)</label>
            <input type="number" id="editEscolaDiasAdicionais" class="form-control" placeholder="Ex: 30" min="0">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Província</label>
            <select id="editEscolaProvincia" class="form-select" onchange="atualizarDistritosEdicaoEscola(this.value)">
              ${optProvincias}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Distrito</label>
            <select id="editEscolaDistrito" class="form-select"></select>
          </div>

          <div class="col-12">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" id="editEscolaEmblema" ${escola.usar_emblema_nacional ? 'checked' : ''}>
              <label class="form-check-label small fw-semibold" for="editEscolaEmblema">
                Utilizar Emblema Oficial nos documentos
              </label>
            </div>
          </div>

          <div class="col-12">
            <div class="card bg-light border p-3">
              <label class="form-label small fw-bold mb-2">
                <i class="bi bi-image me-1 text-primary"></i> Logótipo da Instituição
              </label>
              <div class="d-flex align-items-center gap-3 mb-2">
                <div class="border rounded bg-white p-1 text-center d-flex align-items-center justify-content-center shadow-sm" style="width: 60px; height: 60px; overflow: hidden;">
                  <img id="editEscolaLogoPreview" src="${escola.logo_url || 'img/emblema-mocambique.png'}" alt="Logo" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                </div>
                <div class="flex-grow-1">
                  <label class="form-label x-small text-muted mb-1 fw-semibold">Carregar Imagem do Computador (PNG, JPG, WebP)</label>
                  <input type="file" id="editEscolaLogoFile" accept="image/*" class="form-control form-control-sm mb-1" onchange="processarUploadLogoModal(this, 'editEscolaLogoFinal', 'editEscolaLogoPreview')">
                  <input type="hidden" id="editEscolaLogoFinal" value="${escola.logo_url || ''}">
                  <div class="d-flex gap-2 align-items-center mt-1">
                    <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-2" style="font-size: 0.75rem;" onclick="document.getElementById('editEscolaLogoFinal').value=''; document.getElementById('editEscolaLogoPreview').src='img/emblema-mocambique.png';">
                      <i class="bi bi-arrow-counterclockwise me-1"></i> Usar Emblema Nacional
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <button type="submit" class="btn btn-primary w-100 mt-4">Actualizar Dados e Prazo</button>
      </form>
    `);

    atualizarDistritosEdicaoEscola(escola.provincia || 'Maputo Cidade', escola.distrito);

    document.getElementById('formModalEditarEscola').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const body = {
          nome: document.getElementById('editEscolaNome').value,
          tipo_escola: document.getElementById('editEscolaTipo')?.value || 'S',
          nif_cnpj: document.getElementById('editEscolaNUIT').value,
          email: document.getElementById('editEscolaEmail').value,
          telefone: document.getElementById('editEscolaTelefone').value,
          data_fim: document.getElementById('editEscolaDataFim').value || undefined,
          data_fim_assinatura: document.getElementById('editEscolaDataFim').value || undefined,
          dias_adicionais: Number(document.getElementById('editEscolaDiasAdicionais').value) || undefined,
          provincia: document.getElementById('editEscolaProvincia').value,
          distrito: document.getElementById('editEscolaDistrito').value,
          usar_emblema_nacional: document.getElementById('editEscolaEmblema').checked,
          logo_url: document.getElementById('editEscolaLogoFinal')?.value || null
        };

        const updRes = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}`, {
          method: 'PUT',
          body: JSON.stringify(body)
        });
        if (updRes.success) {
          alert('Dados da escola e código institucional actualizados com sucesso!');
          fecharModal();
          carregarPainelSaaS();
        }
      } catch (err) {
        alert(err.message || 'Erro ao actualizar dados');
      }
    });
  } catch (err) {
    console.error('Erro ao abrir modal de edição da escola:', err);
    mostrarNotificacao(err.message || 'Falha ao carregar dados da escola', 'danger');
  }
}

function atualizarDistritosEdicaoEscola(provincia, distritoSelecionado = '') {
  const distritos = (state.geografia && state.geografia.distritos && state.geografia.distritos[provincia]) || [];
  const select = document.getElementById('editEscolaDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => 
      `<option value="${escapeHtml(d)}" ${d === distritoSelecionado ? 'selected' : ''}>${escapeHtml(d)}</option>`
    ).join('');
  }
}

function modalEditarPrecoPlano(planoId, nome, precoAtual) {
  abrirModal(`Alterar Preço do Plano: ${nome}`, `
    <form id="formModalPrecoPlano">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Novo Valor do Contrato em Meticais (MZN)</label>
        <div class="input-group">
          <input type="number" step="100" id="mppValor" class="form-control" value="${precoAtual}" required>
          <span class="input-group-text fw-bold">MZN</span>
        </div>
        <small class="text-muted">Este novo valor será aplicado para todas as novas adesões e renovações deste plano.</small>
      </div>
      <button type="submit" class="btn btn-primary w-100">Guardar Novo Preço</button>
    </form>
  `);

  document.getElementById('formModalPrecoPlano').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const preco = Number(document.getElementById('mppValor').value);
      const res = await apiFetch(`/api/v1/saas-admin/planos/${planoId}/preco`, {
        method: 'PUT',
        body: JSON.stringify({ preco })
      });
      if (res.success) {
        alert('Preço do plano atualizado com sucesso!');
        fecharModal();
        carregarPainelSaaS();
      }
    } catch (err) {
      alert(err.message || 'Erro ao alterar preço');
    }
  });
}

async function verComprovativoContrato(escolaId) {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/comprovativo-contrato`);
    if (res.success) {
      exibirComprovativoContratoModal(res.data);
    }
  } catch (err) {
    alert('Erro ao carregar comprovativo de contrato');
  }
}

async function baixarComprovativoMinhaEscola() {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/minha-escola/comprovativo-contrato`);
    if (res.success) {
      exibirComprovativoContratoModal(res.data);
    }
  } catch (err) {
    alert('Erro ao carregar comprovativo');
  }
}

function exibirComprovativoContratoModal(c) {
  abrirModal('Comprovativo Oficial de Contrato e Adesão ao SIGE', `
    <div class="printable-document p-4 bg-white border rounded">
      <div class="text-center border-bottom pb-3 mb-4">
        <h5 class="fw-bold mb-1">SISTEMA INTEGRADO DE GESTÃO ESCOLAR</h5>
        <h6 class="fw-semibold text-primary mb-1">SIGE — Gestão Integrada Escolar (SaaS)</h6>
        <p class="text-muted small mb-0">Comprovativo de Regularização de Licença e Adesão Institucional</p>
      </div>

      <div class="row g-2 mb-4 small">
        <div class="col-6"><strong>Instituição Contratante:</strong> ${c.escola.nome}</div>
        <div class="col-6"><strong>NUIT:</strong> ${c.escola.nif_cnpj}</div>
        <div class="col-6"><strong>Localização:</strong> ${c.escola.distrito || '-'}, ${c.escola.provincia || '-'}</div>
        <div class="col-6"><strong>E-mail:</strong> ${c.escola.email}</div>
      </div>

      <div class="table-responsive">
        <table class="table table-bordered table-sm mb-4 small">
          <thead class="table-light">
            <tr>
              <th>Plano Contratado</th>
              <th>Data de Início</th>
              <th>Data de Término (Validade)</th>
              <th>Valor Pago / Contrato</th>
              <th>Estado da Licença</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>${c.plano.nome}</strong></td>
              <td>${new Date(c.assinatura.data_inicio).toLocaleDateString('pt-PT')}</td>
              <td><strong>${new Date(c.assinatura.data_fim).toLocaleDateString('pt-PT')}</strong></td>
              <td class="text-success fw-bold">${formatarMoeda(Number(c.assinatura?.valor_pago ?? c.assinatura?.valor ?? c.plano?.preco ?? 0))}</td>
              <td><span class="badge badge-ativa">${c.escola.status}</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="alert alert-light border small text-muted mb-4">
        <i class="bi bi-shield-check text-success me-1"></i>
        Declara-se para os devidos efeitos que a referida instituição possui licença ativa para processamento oficial de Pautas, Boletins, Cadernetas e Certificados Digitais com autenticação QR Code.
      </div>

      <div class="d-flex justify-content-between text-center pt-4 border-top small">
        <div>
          <p class="mb-0 border-top pt-2 px-3">SuperAdmin SIGE — Direcção de Tecnologia</p>
        </div>
        <div>
          <p class="mb-0 border-top pt-2 px-3">O Representante da Instituição de Ensino</p>
        </div>
      </div>

      <div class="text-center mt-4 no-print">
        <button class="btn btn-primary" onclick="window.print()"><i class="bi bi-printer me-1"></i> Imprimir Comprovativo</button>
      </div>
    </div>
  `);
}

async function executarCronVerificacaoManual() {
  try {
    const res = await apiFetch('/api/v1/saas-admin/verificar-expiracoes', { method: 'POST' });
    if (res.success) {
      alert(`Verificação de expiração executada!\nProcessadas: ${res.data.processadas}\nExpiradas: ${res.data.expiradas}`);
      carregarPainelSaaS();
    }
  } catch (err) {
    alert('Erro ao executar verificação.');
  }
}

// ==================== 3. ESCOLA & TURMAS ====================
window.atualizarPreviewCodigoEscolaConfig = function() {
  const prov = document.getElementById('confEscolaProvincia')?.value || state.escolaAtual?.provincia || 'Maputo Cidade';
  const dist = document.getElementById('confEscolaDistrito')?.value || state.escolaAtual?.distrito || '';
  const tipo = document.getElementById('confEscolaTipo')?.value || state.escolaAtual?.tipo_escola || 'S';
  const nome = document.getElementById('confEscolaNome')?.value || state.escolaAtual?.nome || '';

  const codExistente = state.escolaAtual?.codigo_escola || '';
  let seqNum = 1;
  if (codExistente && codExistente.length >= 9) {
    const parsedSeq = parseInt(codExistente.slice(5), 10);
    if (!isNaN(parsedSeq) && parsedSeq > 0) seqNum = parsedSeq;
  }

  const prev = window.gerarPreviewCodigoEscola(prov, dist, tipo, nome, seqNum);
  const setTxt = (id, txt) => {
    const el = document.getElementById(id);
    if (el) el.textContent = txt;
  };
  setTxt('confEscolaCodigoBadge', prev.codigo_escola);
  setTxt('confCodigoGD', prev.codigo_gd);
  setTxt('confCodigoDP', prev.codigo_dp);
  setTxt('confCodigoSECR', prev.codigo_secr);
  setTxt('labelBadgeGD', prev.codigo_gd);
  setTxt('labelBadgeDP', prev.codigo_dp);
  setTxt('labelBadgeSECR', prev.codigo_secr);
};

async function carregarEscolaETurmas() {
  try {
    const resInfo = await apiFetch('/api/v1/escola-admin/info');
    if (resInfo.success) {
      const e = resInfo.data;
      state.escolaAtual = e;
      if (state.tenant) {
        state.tenant.codigo_escola = e.codigo_escola;
        state.tenant.tipo_escola = e.tipo_escola;
      }
      document.getElementById('confEscolaNome').value = e.nome;
      document.getElementById('confEscolaAnoLetivo').value = e.ano_letivo_ativo;
      document.getElementById('confEscolaTrimestreAtivo').value = e.trimestre_ativo || '1_TRIMESTRE';
      document.getElementById('confEscolaTelefone').value = e.telefone || '';
      document.getElementById('confEscolaEmail').value = e.email;
      document.getElementById('confEscolaDirector').value = e.director_nome || '';
      document.getElementById('confEscolaDAP').value = e.dap_nome || '';
      document.getElementById('confEscolaChefeSec').value = e.chefe_secretaria_nome || '';
      document.getElementById('confEscolaEmblema').checked = !!e.usar_emblema_nacional;

      const selTipo = document.getElementById('confEscolaTipo');
      if (selTipo) selTipo.value = e.tipo_escola || 'S';

      const codEscola = e.codigo_escola || '0101S0001';
      const codGD = e.codigo_gabinete_director || `GD${codEscola}`;
      const codDP = e.codigo_direccao_pedagogica || `DP${codEscola}`;
      const codSECR = e.codigo_secretaria || `SECR${codEscola}`;
      const setTxt = (id, txt) => {
        const el = document.getElementById(id);
        if (el) el.textContent = txt;
      };
      setTxt('confEscolaCodigoBadge', codEscola);
      setTxt('confCodigoGD', codGD);
      setTxt('confCodigoDP', codDP);
      setTxt('confCodigoSECR', codSECR);
      setTxt('labelBadgeGD', codGD);
      setTxt('labelBadgeDP', codDP);
      setTxt('labelBadgeSECR', codSECR);

      // Logótipo da Escola & Catálogo de Identidade Visual
      if (e.galeria_logos && Array.isArray(e.galeria_logos)) {
        state.escolaAtual.galeria_logos = e.galeria_logos;
        if (state.tenant) state.tenant.galeria_logos = e.galeria_logos;
      }
      const logoVal = e.logo_url || e.logo_base64 || '';
      const finalLogoInput = document.getElementById('confEscolaLogoFinalValue');
      if (finalLogoInput) finalLogoInput.value = logoVal;
      const urlInput = document.getElementById('confEscolaLogoUrl');
      if (urlInput) urlInput.value = '';
      window.atualizarVisualizacaoLogo(logoVal, e.usar_emblema_nacional);
      if (typeof window.renderizarGaleriaLogos === 'function') {
        window.renderizarGaleriaLogos();
      }

      // Identidade Visual, Tema de Cores e Imagem de Fundo
      if (e.galeria_fundos && Array.isArray(e.galeria_fundos)) {
        state.escolaAtual.galeria_fundos = e.galeria_fundos;
        if (state.tenant) state.tenant.galeria_fundos = e.galeria_fundos;
      }
      const temaCod = e.tema_codigo || 'padrao_azul';
      const inputTema = document.getElementById('confEscolaTemaCodigo');
      if (inputTema) inputTema.value = temaCod;
      const corPrim = e.tema_cor_primaria || '#1e3a8a';
      const corHov = e.tema_cor_hover || '#172554';
      const corSide = e.tema_cor_sidebar || '#0f172a';
      const corSideAtiva = e.tema_cor_sidebar_ativa || '#38bdf8';
      const setInpVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
      setInpVal('confEscolaCorPrimaria', corPrim);
      setInpVal('confEscolaCorPrimariaHex', corPrim);
      setInpVal('confEscolaCorHover', corHov);
      setInpVal('confEscolaCorHoverHex', corHov);
      setInpVal('confEscolaCorSidebar', corSide);
      setInpVal('confEscolaCorSidebarHex', corSide);
      setInpVal('confEscolaCorSidebarAtiva', corSideAtiva);
      setInpVal('confEscolaCorSidebarAtivaHex', corSideAtiva);

      const modoFundo = e.imagem_fundo_modo || 'marca_dagua';
      setInpVal('confEscolaFundoModo', modoFundo);

      let fundoVal = e.imagem_fundo_url || e.imagem_fundo_base64 || '';
      if (!fundoVal && modoFundo !== 'nenhum') {
        if (e.usar_emblema_nacional !== false) {
          fundoVal = 'img/emblema-mocambique.png';
        } else if (e.logo_url || e.logo_base64) {
          fundoVal = e.logo_url || e.logo_base64;
        } else {
          fundoVal = 'img/logo-sige.png';
        }
      }
      setInpVal('confEscolaFundoFinalValue', fundoVal);
      const urlFundoInput = document.getElementById('confEscolaFundoUrl');
      if (urlFundoInput) urlFundoInput.value = '';
      const opacFundo = (typeof e.imagem_fundo_opacidade === 'number') ? e.imagem_fundo_opacidade : 15;
      setInpVal('confEscolaFundoOpacidade', opacFundo);
      const lblOpac = document.getElementById('lblFundoOpacidade');
      if (lblOpac) lblOpac.textContent = `${opacFundo}%`;

      if (typeof window.renderizarSeletorTemas === 'function') {
        window.renderizarSeletorTemas();
      }
      if (typeof window.renderizarGaleriaFundos === 'function') {
        window.renderizarGaleriaFundos();
      }
      if (typeof window.atualizarVisualizacaoFundo === 'function') {
        window.atualizarVisualizacaoFundo(fundoVal, modoFundo, opacFundo);
      }
      if (typeof window.aplicarTemaEFundoInstituicao === 'function') {
        window.aplicarTemaEFundoInstituicao(e);
      }

      // Províncias
      const selectProv = document.getElementById('confEscolaProvincia');
      selectProv.innerHTML = (state.geografia.provincias || []).map(p => 
        `<option value="${p}" ${p === e.provincia ? 'selected' : ''}>${p}</option>`
      ).join('');
      atualizarDistritosEscola(e.provincia || 'Maputo Cidade', e.distrito);
    }

    // Carregar turmas no painel integrado e dedicado
    await carregarTurmas();
  } catch (err) {
    console.error('Erro ao carregar dados da escola:', err);
  }
}

// ==================== 3.1 GESTÃO DEDICADA DE TURMAS & CAPACIDADE ====================
async function carregarTurmas() {
  try {
    const [resTurmas, resDisciplinas] = await Promise.all([
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/disciplinas')
    ]);
    if (!resTurmas.success) return;

    state.turmasList = resTurmas.data || [];
    state.todasTurmas = resTurmas.data || [];
    if (resDisciplinas && resDisciplinas.success) {
      state.todasDisciplinas = resDisciplinas.data || [];
    }
    renderizarEstatisticasETabelaTurmas();
  } catch (err) {
    console.error('Erro ao carregar turmas:', err);
  }
}

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
    const classesTurmas = Array.from(new Set(turmas.map(t => (t.grau_ano || '').trim()).filter(Boolean))).sort((a, b) => {
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

  const filtradas = turmas.filter(t => {
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
            ${(typeof window.classeTemExame === 'function' && window.classeTemExame(t.grau_ano))
              ? `<span class="badge bg-danger-subtle text-danger border border-danger-subtle ms-1" style="font-size: 0.68rem;" title="A Classe tem Exame: Sim (Com Exame)"><i class="bi bi-file-earmark-check-fill me-1"></i>Com Exame</span>`
              : `<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle ms-1" style="font-size: 0.68rem;" title="A Classe tem Exame: Não (Sem Exame)"><i class="bi bi-dash-circle me-1"></i>Sem Exame</span>`}
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

function obterGaleriaLogosEscola() {
  const e = state.escolaAtual || state.tenant || {};
  const eId = (e.id || '').toString().trim();
  let galeria = Array.isArray(e.galeria_logos) 
    ? e.galeria_logos.filter(item => item && item.id !== 'emblema_nacional') 
    : [];

  try {
    localStorage.removeItem('sige_galeria_logos_default');
  } catch (_) {}

  if (eId && eId !== 'default' && eId !== 'escola_atual') {
    const chaveLocal = `sige_galeria_logos_${eId}`;
    try {
      const salvoLocal = JSON.parse(localStorage.getItem(chaveLocal) || '[]');
      if (Array.isArray(salvoLocal)) {
        salvoLocal.forEach(item => {
          if (item && item.url && !galeria.some(g => g.id === item.id || g.url === item.url)) {
            galeria.push(item);
          }
        });
      }
    } catch (_) {}
  }

  const logoAtual = e.logo_url || e.logo_base64;
  if (logoAtual && !logoAtual.includes('emblema-mocambique.png')) {
    if (!galeria.some(g => g.url === logoAtual)) {
      galeria.unshift({
        id: 'logo_anterior_' + (eId || Date.now()),
        nome: 'Logótipo da Escola',
        url: logoAtual,
        tipo: 'SALVO',
        criado_em: new Date().toISOString()
      });
    }
  }

  const mapa = new Map();
  galeria.forEach(item => {
    if (item && item.url && !mapa.has(item.url)) {
      mapa.set(item.url, item);
    }
  });

  return Array.from(mapa.values());
}
window.obterGaleriaLogosEscola = obterGaleriaLogosEscola;

function renderizarGaleriaLogos() {
  const container = document.getElementById('galeriaLogosContainer');
  if (!container) return;

  const galeria = obterGaleriaLogosEscola();
  const e = state.escolaAtual || state.tenant || {};
  const logoAtivoAtual = document.getElementById('confEscolaLogoFinalValue')?.value ?? (e.logo_url || e.logo_base64 || '');
  const checkEmblema = document.getElementById('confEscolaEmblema');
  const usarEmblema = checkEmblema ? checkEmblema.checked : (e.usar_emblema_nacional !== false);

  const contadorEl = document.getElementById('contadorGaleriaLogos');
  if (contadorEl) {
    const total = galeria.length + 1;
    contadorEl.textContent = `${total} disponível${total > 1 ? 'is' : ''}`;
  }

  const isEmblemaAtivo = Boolean(usarEmblema || !logoAtivoAtual || logoAtivoAtual === 'img/emblema-mocambique.png');

  let html = `
    <!-- 1. Emblema Nacional Oficial (Permanente e sempre disponível) -->
    <div class="col-6 col-sm-6 col-md-6 col-lg-6">
      <div class="card h-100 p-2 text-center logo-card-item cursor-pointer ${isEmblemaAtivo ? 'border-primary border-2 bg-primary-subtle shadow-sm' : 'border-secondary-subtle bg-white'}"
           onclick="selecionarLogotipoGaleria('emblema_nacional')"
           title="Clique para usar o Emblema Nacional Oficial"
           style="cursor: pointer; transition: all 0.2s; min-height: 120px;">
        <div class="d-flex align-items-center justify-content-center bg-light rounded p-1 mb-1" style="height: 60px;">
          <img src="img/emblema-mocambique.png" alt="Emblema Nacional" style="max-height: 100%; max-width: 100%; object-fit: contain;">
        </div>
        <div class="small fw-bold text-truncate text-dark" style="font-size: 0.74rem;" title="Emblema Nacional (Padrão Oficial)">
          Emblema Nacional
        </div>
        <div class="mt-1">
          ${isEmblemaAtivo 
            ? '<span class="badge bg-primary text-white" style="font-size: 0.68rem;"><i class="bi bi-check-circle-fill me-1"></i>Activo</span>' 
            : '<span class="badge bg-light text-secondary border" style="font-size: 0.68rem;"><i class="bi bi-hand-index-thumb me-1"></i>Usar este</span>'}
        </div>
      </div>
    </div>
  `;

  galeria.forEach((item, idx) => {
    const isAtivo = !isEmblemaAtivo && (logoAtivoAtual === item.url);
    const nomeExibicao = item.nome || `Logótipo ${idx + 1}`;
    html += `
      <div class="col-6 col-sm-6 col-md-6 col-lg-6">
        <div class="card h-100 p-2 text-center logo-card-item cursor-pointer position-relative ${isAtivo ? 'border-primary border-2 bg-primary-subtle shadow-sm' : 'border-secondary-subtle bg-white'}"
             onclick="selecionarLogotipoGaleria('${item.id}')"
             title="Clique para alternar para este logótipo"
             style="cursor: pointer; transition: all 0.2s; min-height: 120px;">
          <button type="button" class="btn btn-sm btn-danger py-0 px-1 position-absolute top-0 end-0 m-1 rounded-circle shadow-sm"
                  style="font-size: 0.65rem; width: 22px; height: 22px; line-height: 1; padding: 0; z-index: 2;"
                  onclick="event.stopPropagation(); removerLogotipoDaGaleria('${item.id}')"
                  title="Eliminar este logótipo da galeria">
            <i class="bi bi-trash"></i>
          </button>
          <div class="d-flex align-items-center justify-content-center bg-light rounded p-1 mb-1" style="height: 60px;">
            <img src="${item.url}" alt="${nomeExibicao}" style="max-height: 100%; max-width: 100%; object-fit: contain;">
          </div>
          <div class="small fw-bold text-truncate text-dark" style="font-size: 0.74rem;" title="${nomeExibicao}">
            ${nomeExibicao}
          </div>
          <div class="mt-1">
            ${isAtivo 
              ? '<span class="badge bg-primary text-white" style="font-size: 0.68rem;"><i class="bi bi-check-circle-fill me-1"></i>Activo</span>' 
              : '<span class="badge bg-light text-secondary border" style="font-size: 0.68rem;"><i class="bi bi-hand-index-thumb me-1"></i>Usar este</span>'}
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}
window.renderizarGaleriaLogos = renderizarGaleriaLogos;

async function selecionarLogotipoGaleria(id) {
  const finalInput = document.getElementById('confEscolaLogoFinalValue');
  const checkEmblema = document.getElementById('confEscolaEmblema');
  const e = state.escolaAtual || state.tenant || {};

  let logoUrlParaSalvar = '';
  let usarEmblemaParaSalvar = false;

  if (id === 'emblema_nacional') {
    if (finalInput) finalInput.value = '';
    if (checkEmblema) checkEmblema.checked = true;
    logoUrlParaSalvar = '';
    usarEmblemaParaSalvar = true;
    atualizarVisualizacaoLogo('', true);
  } else {
    const galeria = obterGaleriaLogosEscola();
    const item = galeria.find(g => g.id === id);
    if (!item) return;

    if (finalInput) finalInput.value = item.url;
    if (checkEmblema) checkEmblema.checked = false;
    logoUrlParaSalvar = item.url;
    usarEmblemaParaSalvar = false;
    atualizarVisualizacaoLogo(item.url, false);
  }

  renderizarGaleriaLogos();

  if (state.escolaAtual) {
    state.escolaAtual.logo_url = logoUrlParaSalvar || null;
    state.escolaAtual.usar_emblema_nacional = usarEmblemaParaSalvar;
  }
  if (state.tenant) {
    state.tenant.logo_url = logoUrlParaSalvar || null;
    state.tenant.usar_emblema_nacional = usarEmblemaParaSalvar;
  }

  try {
    const galeria = obterGaleriaLogosEscola();
    const body = {
      usar_emblema_nacional: usarEmblemaParaSalvar,
      logo_url: logoUrlParaSalvar,
      galeria_logos: galeria
    };
    await apiFetch('/api/v1/escola-admin/info', {
      method: 'PUT',
      body: JSON.stringify(body)
    });
    if (typeof mostrarToast === 'function') {
      mostrarToast(
        usarEmblemaParaSalvar 
          ? 'Emblema Nacional oficial activado com sucesso!' 
          : 'Logótipo alterado e activado com sucesso!',
        'success'
      );
    }
  } catch (err) {
    console.warn('Erro ao auto-salvar permuta de logótipo:', err);
  }
}
window.selecionarLogotipoGaleria = selecionarLogotipoGaleria;

async function adicionarLogotipoAGaleria(url, nome = '') {
  if (!url || !url.trim()) return;
  const urlLimpo = url.trim();
  const galeria = obterGaleriaLogosEscola();
  const e = state.escolaAtual || state.tenant || {};

  const existente = galeria.find(g => g.url === urlLimpo);
  if (existente) {
    await selecionarLogotipoGaleria(existente.id);
    return;
  }

  const novoId = 'logo_' + Date.now();
  const novoItem = {
    id: novoId,
    nome: nome || `Logótipo ${galeria.length + 1}`,
    url: urlLimpo,
    tipo: 'UPLOAD',
    criado_em: new Date().toISOString()
  };

  galeria.push(novoItem);

  const eId = (e.id || '').toString().trim();
  if (eId && eId !== 'default' && eId !== 'escola_atual') {
    const chaveLocal = `sige_galeria_logos_${eId}`;
    try {
      localStorage.setItem(chaveLocal, JSON.stringify(galeria));
    } catch (_) {}
  }

  if (state.escolaAtual) state.escolaAtual.galeria_logos = galeria;
  if (state.tenant) state.tenant.galeria_logos = galeria;

  await selecionarLogotipoGaleria(novoId);
}
window.adicionarLogotipoAGaleria = adicionarLogotipoAGaleria;

async function removerLogotipoDaGaleria(id) {
  if (id === 'emblema_nacional') {
    alert('O Emblema Nacional Oficial é padrão do sistema e não pode ser eliminado.');
    return;
  }
  if (!confirm('Deseja realmente eliminar este logótipo da galeria?')) {
    return;
  }

  let galeria = obterGaleriaLogosEscola();
  const itemRemovido = galeria.find(g => g.id === id);
  galeria = galeria.filter(g => g.id !== id);

  const e = state.escolaAtual || state.tenant || {};
  const eId = (e.id || '').toString().trim();
  if (eId && eId !== 'default' && eId !== 'escola_atual') {
    const chaveLocal = `sige_galeria_logos_${eId}`;
    try {
      localStorage.setItem(chaveLocal, JSON.stringify(galeria));
    } catch (_) {}
  }

  if (state.escolaAtual) state.escolaAtual.galeria_logos = galeria;
  if (state.tenant) state.tenant.galeria_logos = galeria;

  const finalInput = document.getElementById('confEscolaLogoFinalValue');
  if (itemRemovido && finalInput && finalInput.value === itemRemovido.url) {
    await selecionarLogotipoGaleria('emblema_nacional');
  } else {
    renderizarGaleriaLogos();
    try {
      await apiFetch('/api/v1/escola-admin/info', {
        method: 'PUT',
        body: JSON.stringify({ galeria_logos: galeria })
      });
      if (typeof mostrarToast === 'function') {
        mostrarToast('Logótipo removido da galeria.', 'info');
      }
    } catch (_) {}
  }
}
window.removerLogotipoDaGaleria = removerLogotipoDaGaleria;

function atualizarVisualizacaoLogo(logoSrc, usarEmblema = true) {
  const img = document.getElementById('confEscolaLogoPreview');
  const statusEl = document.getElementById('confEscolaLogoStatus');
  const btnRemover = document.getElementById('btnRemoverLogo');

  if (!usarEmblema && logoSrc && logoSrc.trim() && !logoSrc.includes('emblema-mocambique.png')) {
    if (img) img.src = logoSrc;
    const galeria = (typeof obterGaleriaLogosEscola === 'function') ? obterGaleriaLogosEscola() : [];
    const item = galeria.find(g => g.url === logoSrc);
    if (statusEl) statusEl.textContent = item?.nome ? `Logótipo: ${item.nome}` : 'Logótipo Próprio Activo';
    if (btnRemover) btnRemover.style.display = 'inline-block';
  } else {
    if (img) img.src = 'img/emblema-mocambique.png';
    if (statusEl) statusEl.textContent = 'Emblema Nacional (Padrão Oficial)';
    if (btnRemover) btnRemover.style.display = 'none';
  }
}
window.atualizarVisualizacaoLogo = atualizarVisualizacaoLogo;

function processarUploadLogoLocal(input) {
  const file = input.files?.[0];
  if (!file) return;

  if (!file.type.startsWith('image/')) {
    alert('Por favor, seleccione um ficheiro de imagem válido (PNG, JPG, WebP).');
    return;
  }

  if (file.size > 5 * 1024 * 1024) {
    alert('A imagem seleccionada é muito pesada (máximo 5MB).');
    return;
  }

  const reader = new FileReader();
  reader.onload = async function(e) {
    const dataUrl = e.target.result;
    const nomeFicheiro = file.name ? file.name.replace(/\.[^/.]+$/, "") : `Logótipo`;
    await adicionarLogotipoAGaleria(dataUrl, nomeFicheiro);
    input.value = '';
  };
  reader.readAsDataURL(file);
}
window.processarUploadLogoLocal = processarUploadLogoLocal;

async function processarUrlLogo(url) {
  if (!url || !url.trim()) {
    alert('Por favor, insira um link / URL válido da imagem.');
    return;
  }
  const urlLimpo = url.trim();
  await adicionarLogotipoAGaleria(urlLimpo, 'Logótipo Web');
  const inputEl = document.getElementById('confEscolaLogoUrl');
  if (inputEl) inputEl.value = '';
}
window.processarUrlLogo = processarUrlLogo;

async function removerLogotipoEscola() {
  await selecionarLogotipoGaleria('emblema_nacional');
}
window.removerLogotipoEscola = removerLogotipoEscola;

async function alternarEmblemaCheck(checked) {
  if (checked) {
    await selecionarLogotipoGaleria('emblema_nacional');
  } else {
    const galeria = obterGaleriaLogosEscola();
    if (galeria.length > 0) {
      await selecionarLogotipoGaleria(galeria[0].id);
    }
  }
}
window.alternarEmblemaCheck = alternarEmblemaCheck;

function atualizarDistritosEscola(provincia, distritoSelecionado = '') {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('confEscolaDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => 
      `<option value="${d}" ${d === distritoSelecionado ? 'selected' : ''}>${d}</option>`
    ).join('');
  }
}

// ==================== PERSONALIZAÇÃO VISUAL: TEMAS DE CORES & FUNDO DA ESCOLA ====================

window.SIGE_TEMAS = {
  padrao_azul: {
    codigo: 'padrao_azul',
    nome: 'Azul SIGE (Institucional)',
    primaria: '#1e3a8a',
    hover: '#172554',
    sidebar: '#0f172a',
    sidebarAtiva: '#38bdf8',
    acento: '#f59e0b',
    descricao: 'Clássico profissional padrão do SIGE'
  },
  indigo_save: {
    codigo: 'indigo_save',
    nome: 'Índigo Save (Universitário)',
    primaria: '#312e81',
    hover: '#1e1b4b',
    sidebar: '#0f0d2e',
    sidebarAtiva: '#818cf8',
    acento: '#df8704',
    descricao: 'Académico moderno inspirado em universidades'
  },
  verde_esmeralda: {
    codigo: 'verde_esmeralda',
    nome: 'Verde Esmeralda',
    primaria: '#065f46',
    hover: '#044e39',
    sidebar: '#022c22',
    sidebarAtiva: '#34d399',
    acento: '#fbbf24',
    descricao: 'Ecológico, vibrante e pedagógico'
  },
  vermelho_rubi: {
    codigo: 'vermelho_rubi',
    nome: 'Bordeaux & Terracota Nobre',
    primaria: '#991b1b',
    hover: '#7f1d1d',
    sidebar: '#450a0a',
    sidebarAtiva: '#f87171',
    acento: '#fbbf24',
    descricao: 'Tradição, distinção e prestígio'
  },
  dourado_ambar: {
    codigo: 'dourado_ambar',
    nome: 'Âmbar Dourado',
    primaria: '#b45309',
    hover: '#92400e',
    sidebar: '#1c1917',
    sidebarAtiva: '#fbbf24',
    acento: '#f59e0b',
    descricao: 'Tons quentes e solares'
  },
  safira_grafite: {
    codigo: 'safira_grafite',
    nome: 'Grafite & Safira Tecnológico',
    primaria: '#0284c7',
    hover: '#0369a1',
    sidebar: '#0b1120',
    sidebarAtiva: '#38bdf8',
    acento: '#38bdf8',
    descricao: 'Contraste escuro moderno e dinâmico'
  },
  purpura_real: {
    codigo: 'purpura_real',
    nome: 'Púrpura Imperial',
    primaria: '#7e22ce',
    hover: '#6b21a8',
    sidebar: '#2e1065',
    sidebarAtiva: '#c084fc',
    acento: '#facc15',
    descricao: 'Distinção, liderança e nobreza'
  },
  oceano_petroleo: {
    codigo: 'oceano_petroleo',
    nome: 'Petróleo & Ciano Índico',
    primaria: '#0f766e',
    hover: '#115e59',
    sidebar: '#042f2e',
    sidebarAtiva: '#2dd4bf',
    acento: '#5eead4',
    descricao: 'Sereno, contemporâneo e elegante'
  },
  petroleo_ciano: {
    codigo: 'petroleo_ciano',
    nome: 'Petróleo & Ciano Índico',
    primaria: '#0f766e',
    hover: '#115e59',
    sidebar: '#042f2e',
    sidebarAtiva: '#2dd4bf',
    acento: '#5eead4',
    descricao: 'Sereno, contemporâneo e elegante'
  },
  personalizado: {
    codigo: 'personalizado',
    nome: 'Personalizado (Cores Próprias)',
    primaria: '#1e3a8a',
    hover: '#172554',
    sidebar: '#0f172a',
    sidebarAtiva: '#38bdf8',
    acento: '#f59e0b',
    descricao: 'Defina manualmente as cores da instituição'
  }
};

function aplicarTemaEFundoInstituicao(escola, opcoes = {}) {
  if (!escola) {
    if (typeof restaurarPadraoTemaEFundo === 'function') restaurarPadraoTemaEFundo();
    return;
  }
  const temaCodigo = escola.tema_codigo || 'padrao_azul';
  const temaConfig = window.SIGE_TEMAS[temaCodigo] || window.SIGE_TEMAS.padrao_azul;

  const primaria = escola.tema_cor_primaria || temaConfig.primaria;
  const hover = escola.tema_cor_hover || temaConfig.hover;
  const sidebar = escola.tema_cor_sidebar || temaConfig.sidebar;
  const sidebarAtiva = escola.tema_cor_sidebar_ativa || temaConfig.sidebarAtiva;

  const root = document.documentElement;
  root.style.setProperty('--primary-color', primaria);
  root.style.setProperty('--primary-hover', hover);
  root.style.setProperty('--sidebar-bg', sidebar);
  root.style.setProperty('--sidebar-active', sidebarAtiva);

  let styleTag = document.getElementById('sige-tema-dinamico');
  if (!styleTag) {
    styleTag = document.createElement('style');
    styleTag.id = 'sige-tema-dinamico';
    document.head.appendChild(styleTag);
  }

  styleTag.textContent = `
    .btn-primary {
      background-color: ${primaria} !important;
      border-color: ${primaria} !important;
    }
    .btn-primary:hover, .btn-primary:focus, .btn-primary:active {
      background-color: ${hover} !important;
      border-color: ${hover} !important;
    }
    .btn-outline-primary {
      color: ${primaria} !important;
      border-color: ${primaria} !important;
    }
    .btn-outline-primary:hover, .btn-outline-primary:focus, .btn-outline-primary.active {
      background-color: ${primaria} !important;
      border-color: ${primaria} !important;
      color: #ffffff !important;
    }
    .text-primary, a.text-primary {
      color: ${primaria} !important;
    }
    .border-primary {
      border-color: ${primaria} !important;
    }
    .bg-primary {
      background-color: ${primaria} !important;
    }
    .badge.bg-primary {
      background-color: ${primaria} !important;
    }
    .badge.bg-primary-subtle {
      color: ${primaria} !important;
      background-color: rgba(30, 58, 138, 0.12) !important;
    }
    #sidebar {
      background: ${sidebar} !important;
    }
    #sidebar .nav-link.active {
      background: ${primaria} !important;
      color: #ffffff !important;
    }
    #sidebar .nav-link:hover {
      background: rgba(255, 255, 255, 0.08) !important;
    }
    .nav-tabs .nav-link.active {
      border-bottom-color: ${primaria} !important;
      color: ${primaria} !important;
    }
  `;

  // Imagem de Fundo / Marca de Água
  const modoFundo = escola.imagem_fundo_modo || 'marca_dagua';
  const opacidade = (typeof escola.imagem_fundo_opacidade === 'number') ? escola.imagem_fundo_opacidade : 15;
  const opacidadeDecimal = Math.max(0.02, Math.min(0.60, opacidade / 100));

  let imgFundo = escola.imagem_fundo_url || escola.imagem_fundo_base64 || '';
  if (!imgFundo) {
    if (escola.usar_emblema_nacional) {
      imgFundo = 'img/emblema-mocambique.png';
    } else if (escola.logo_url || escola.logo_base64) {
      imgFundo = escola.logo_url || escola.logo_base64;
    } else {
      imgFundo = 'img/logo-sige.png';
    }
  }

  const elMarcaDagua = document.querySelector('.marca-dagua-sistema');
  if (elMarcaDagua) {
    if (modoFundo === 'nenhum' || imgFundo === 'SEM_IMAGEM') {
      elMarcaDagua.style.display = 'none';
    } else if (modoFundo === 'cobertura_total') {
      elMarcaDagua.style.display = 'block';
      elMarcaDagua.style.position = 'fixed';
      elMarcaDagua.style.inset = '0';
      elMarcaDagua.style.width = '100vw';
      elMarcaDagua.style.height = '100vh';
      elMarcaDagua.style.maxWidth = '100vw';
      elMarcaDagua.style.maxHeight = '100vh';
      elMarcaDagua.style.transform = 'none';
      elMarcaDagua.style.backgroundImage = `url("${imgFundo}")`;
      elMarcaDagua.style.backgroundRepeat = 'no-repeat';
      elMarcaDagua.style.backgroundPosition = 'center center';
      elMarcaDagua.style.backgroundSize = 'cover';
      elMarcaDagua.style.opacity = opacidadeDecimal.toString();
      elMarcaDagua.style.mixBlendMode = 'multiply';
      elMarcaDagua.style.pointerEvents = 'none';
      elMarcaDagua.style.zIndex = '0';
    } else if (modoFundo === 'padrao_textura') {
      elMarcaDagua.style.display = 'block';
      elMarcaDagua.style.position = 'fixed';
      elMarcaDagua.style.inset = '0';
      elMarcaDagua.style.width = '100vw';
      elMarcaDagua.style.height = '100vh';
      elMarcaDagua.style.maxWidth = '100vw';
      elMarcaDagua.style.maxHeight = '100vh';
      elMarcaDagua.style.transform = 'none';
      elMarcaDagua.style.backgroundImage = `url("${imgFundo}")`;
      elMarcaDagua.style.backgroundRepeat = 'repeat';
      elMarcaDagua.style.backgroundPosition = 'top left';
      elMarcaDagua.style.backgroundSize = '200px 200px';
      elMarcaDagua.style.opacity = (opacidadeDecimal * 0.75).toString();
      elMarcaDagua.style.mixBlendMode = 'multiply';
      elMarcaDagua.style.pointerEvents = 'none';
      elMarcaDagua.style.zIndex = '0';
    } else {
      // marca_dagua (Central Padrão)
      elMarcaDagua.style.display = 'block';
      elMarcaDagua.style.position = 'fixed';
      elMarcaDagua.style.top = '50%';
      elMarcaDagua.style.left = 'calc(50% + (var(--sidebar-width) / 2))';
      elMarcaDagua.style.transform = 'translate(-50%, -50%)';
      elMarcaDagua.style.width = '520px';
      elMarcaDagua.style.height = '520px';
      elMarcaDagua.style.maxWidth = '65vw';
      elMarcaDagua.style.maxHeight = '65vh';
      elMarcaDagua.style.backgroundImage = `url("${imgFundo}")`;
      elMarcaDagua.style.backgroundRepeat = 'no-repeat';
      elMarcaDagua.style.backgroundPosition = 'center center';
      elMarcaDagua.style.backgroundSize = 'contain';
      elMarcaDagua.style.opacity = opacidadeDecimal.toString();
      elMarcaDagua.style.mixBlendMode = 'multiply';
      elMarcaDagua.style.pointerEvents = 'none';
      elMarcaDagua.style.zIndex = '0';
    }
  }

  // Cache estritamente isolado por Tenant ID - JAMAIS usar chave global sige_tema_ativo
  if (escola && escola.id && escola.id !== 'escola_atual') {
    try {
      localStorage.setItem(`sige_tema_escola_${escola.id}`, JSON.stringify({
        escolaId: escola.id,
        tema_codigo: temaCodigo,
        tema_cor_primaria: primaria,
        tema_cor_hover: hover,
        tema_cor_sidebar: sidebar,
        tema_cor_sidebar_ativa: sidebarAtiva,
        imagem_fundo_modo: modoFundo,
        imagem_fundo_opacidade: opacidade,
        imagem_fundo_url: imgFundo.startsWith('data:') ? 'base64' : imgFundo
      }));
    } catch (_) {}
  }
  try {
    localStorage.removeItem('sige_tema_ativo');
  } catch (_) {}
}
window.aplicarTemaEFundoInstituicao = aplicarTemaEFundoInstituicao;

// Utilitários de Conversão Cromática e Geração de Paleta Harmónica
function hexParaRgb(hex) {
  hex = (hex || '#1e3a8a').replace('#', '').trim();
  if (hex.length === 3) {
    hex = hex.split('').map(c => c + c).join('');
  }
  const num = parseInt(hex, 16) || 0;
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255
  };
}

function rgbParaHex(r, g, b) {
  const c = v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0');
  return `#${c(r)}${c(g)}${c(b)}`;
}

function rgbParaHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h, s, l = (max + min) / 2;
  if (max === min) {
    h = s = 0;
  } else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  return { h: h * 360, s, l };
}

function hslParaRgb(h, s, l) {
  h = ((h % 360) + 360) % 360 / 360;
  if (s === 0) {
    const v = Math.round(l * 255);
    return { r: v, g: v, b: v };
  }
  const hue2rgb = (p, q, t) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1/6) return p + (q - p) * 6 * t;
    if (t < 1/2) return q;
    if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
    return p;
  };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  return {
    r: Math.round(hue2rgb(p, q, h + 1/3) * 255),
    g: Math.round(hue2rgb(p, q, h) * 255),
    b: Math.round(hue2rgb(p, q, h - 1/3) * 255)
  };
}

function gerarPaletaHarmonica(hexPrimaria) {
  try {
    const rgb = hexParaRgb(hexPrimaria);
    const hsl = rgbParaHsl(rgb.r, rgb.g, rgb.b);
    
    // Hover: Tom 20% mais escuro e saturado
    const hoverRgb = hslParaRgb(hsl.h, Math.min(1, hsl.s * 1.1), Math.max(0.12, hsl.l * 0.78));
    
    // Sidebar: Fundo escuro baseado no matiz institucional (luminosidade 8% a 12%)
    const sidebarRgb = hslParaRgb(hsl.h, Math.min(0.60, hsl.s * 0.8), 0.09);
    
    // Sidebar Ativa: Tom luminoso e brilhante (luminosidade 65% a 75%)
    const ativaRgb = hslParaRgb(hsl.h, Math.max(0.75, hsl.s), 0.65);

    return {
      primaria: hexPrimaria.toLowerCase(),
      hover: rgbParaHex(hoverRgb.r, hoverRgb.g, hoverRgb.b),
      sidebar: rgbParaHex(sidebarRgb.r, sidebarRgb.g, sidebarRgb.b),
      sidebarAtiva: rgbParaHex(ativaRgb.r, ativaRgb.g, ativaRgb.b)
    };
  } catch (_) {
    return {
      primaria: hexPrimaria,
      hover: '#172554',
      sidebar: '#0f172a',
      sidebarAtiva: '#38bdf8'
    };
  }
}

function selecionarCorEspectro(hexPrimaria, nomeCor = '') {
  if (!hexPrimaria) return;
  hexPrimaria = hexPrimaria.trim();
  const paleta = gerarPaletaHarmonica(hexPrimaria);

  const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
  setVal('confEscolaCorPrimaria', paleta.primaria);
  setVal('confEscolaCorPrimariaHex', paleta.primaria);
  setVal('confEscolaCorHover', paleta.hover);
  setVal('confEscolaCorHoverHex', paleta.hover);
  setVal('confEscolaCorSidebar', paleta.sidebar);
  setVal('confEscolaCorSidebarHex', paleta.sidebar);
  setVal('confEscolaCorSidebarAtiva', paleta.sidebarAtiva);
  setVal('confEscolaCorSidebarAtivaHex', paleta.sidebarAtiva);

  // Define tema como personalizado ou detecta se bate com algum pré-definido
  let codigoTema = 'personalizado';
  for (const [key, t] of Object.entries(window.SIGE_TEMAS || {})) {
    if (t.codigo !== 'personalizado' && t.primaria.toLowerCase() === paleta.primaria.toLowerCase()) {
      codigoTema = t.codigo;
      break;
    }
  }
  setVal('confEscolaTemaCodigo', codigoTema);

  // Sincroniza o seletor manual / picker
  const pickerManual = document.getElementById('pickerEspectroManual');
  if (pickerManual) pickerManual.value = paleta.primaria;

  // Atualiza indicadores visuais do espectro preservando o nome da cor clicada
  atualizarIndicadoresEspectro(paleta.primaria, nomeCor || (codigoTema === 'personalizado' ? 'Cor Personalizada' : (window.SIGE_TEMAS[codigoTema]?.nome || '')));

  // Atualiza cartões de temas pré-definidos sem sobrescrever o nome do espectro
  renderizarSeletorTemas(false);

  // Aplica ao vivo imediatamente em todo o ecrã
  aplicarTemaEFundoAoVivo();
}
window.selecionarCorEspectro = selecionarCorEspectro;

function aoMoverEspectroSlider(hue) {
  hue = parseFloat(hue) || 0;
  const rgb = hslParaRgb(hue, 0.82, 0.38);
  const hex = rgbParaHex(rgb.r, rgb.g, rgb.b);

  const lbl = document.getElementById('lblMatizEspectro');
  if (lbl) {
    let nomeHue = 'Matiz';
    if (hue >= 345 || hue < 15) nomeHue = 'Vermelho';
    else if (hue < 45) nomeHue = 'Laranja';
    else if (hue < 70) nomeHue = 'Âmbar/Dourado';
    else if (hue < 150) nomeHue = 'Verde';
    else if (hue < 195) nomeHue = 'Ciano/Turquesa';
    else if (hue < 255) nomeHue = 'Azul';
    else if (hue < 290) nomeHue = 'Índigo/Púrpura';
    else if (hue < 345) nomeHue = 'Magenta/Rosa';
    lbl.textContent = `${Math.round(hue)}° (${nomeHue})`;
  }

  selecionarCorEspectro(hex, `Espectro ${Math.round(hue)}°`);
}
window.aoMoverEspectroSlider = aoMoverEspectroSlider;

function atualizarIndicadoresEspectro(hexPrimaria, nomeCor) {
  hexPrimaria = (hexPrimaria || '').toLowerCase();
  
  const badgeHex = document.getElementById('badgeCorAtivaHex');
  if (badgeHex) {
    badgeHex.style.backgroundColor = hexPrimaria;
    badgeHex.textContent = hexPrimaria.toUpperCase();
  }

  const nomeTexto = document.getElementById('nomeCorAtivaTexto');
  if (nomeTexto && nomeCor) {
    nomeTexto.textContent = nomeCor;
  }

  // Destacar o botão de swatch ativo com anel e visto
  document.querySelectorAll('.swatch-cor-espectro').forEach(btn => {
    const title = (btn.getAttribute('title') || '').toLowerCase();
    const onclickAttr = (btn.getAttribute('onclick') || '').toLowerCase();
    const match = title.includes(hexPrimaria) || onclickAttr.includes(hexPrimaria);
    if (match) {
      btn.style.boxShadow = '0 0 0 3px #0f172a, 0 0 8px rgba(0,0,0,0.5)';
      btn.style.transform = 'scale(1.18)';
      btn.innerHTML = '<i class="bi bi-check-lg text-white" style="font-size: 0.9rem; -webkit-text-stroke: 0.5px;"></i>';
    } else {
      btn.style.boxShadow = '';
      btn.style.transform = '';
      btn.innerHTML = '';
    }
  });
}
window.atualizarIndicadoresEspectro = atualizarIndicadoresEspectro;

function renderizarSeletorTemas(atualizarIndicadores = true) {
  const container = document.getElementById('gradeTemasDisponiveis');
  if (!container) return;

  const codigoAtual = document.getElementById('confEscolaTemaCodigo')?.value || 'padrao_azul';
  const corPrimaria = document.getElementById('confEscolaCorPrimaria')?.value || '#1e3a8a';
  const corSidebar = document.getElementById('confEscolaCorSidebar')?.value || '#0f172a';

  const painelCustom = document.getElementById('painelCoresPersonalizadas');
  if (painelCustom) {
    painelCustom.style.display = (codigoAtual === 'personalizado') ? 'block' : 'none';
  }

  // Atualizar cartões de temas pré-renderizados
  const codigos = ['padrao_azul', 'indigo_save', 'verde_esmeralda', 'vermelho_rubi', 'dourado_ambar', 'safira_grafite', 'purpura_real', 'petroleo_ciano', 'personalizado'];
  let temCardPreRenderizado = false;

  codigos.forEach(cod => {
    const card = document.getElementById(`cardTema_${cod}`);
    const badge = document.getElementById(`badgeTema_${cod}`);
    if (card) {
      temCardPreRenderizado = true;
      const isAtivo = (codigoAtual === cod);
      if (isAtivo) {
        card.className = 'card h-100 p-2 text-center tema-card-item cursor-pointer border-primary border-2 bg-primary-subtle shadow-sm';
      } else {
        card.className = 'card h-100 p-2 text-center tema-card-item cursor-pointer border-secondary-subtle bg-white';
      }
      if (badge) {
        badge.innerHTML = isAtivo 
          ? '<span class="badge bg-primary text-white" style="font-size: 0.65rem;"><i class="bi bi-check-circle-fill me-1"></i>Activo</span>' 
          : '<span class="badge bg-light text-secondary border" style="font-size: 0.65rem;">Escolher</span>';
      }
    }
  });

  // Atualizar gradiente do preview do card personalizado caso esteja ativo
  const gradPersonalizado = document.getElementById('gradienteCardPersonalizado');
  if (gradPersonalizado && codigoAtual === 'personalizado') {
    gradPersonalizado.style.background = `linear-gradient(135deg, ${corSidebar} 0%, ${corSidebar} 40%, ${corPrimaria} 40%, ${corPrimaria} 100%)`;
  }

  // Se por algum motivo os cartões não estiverem pré-renderizados no DOM, gera-os dinamicamente como fallback
  if (!temCardPreRenderizado && window.SIGE_TEMAS) {
    let html = '';
    Object.values(window.SIGE_TEMAS).forEach(t => {
      const isAtivo = (codigoAtual === t.codigo);
      const gradiente = (t.codigo === 'personalizado') 
        ? 'background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);'
        : `background: linear-gradient(135deg, ${t.sidebar} 0%, ${t.sidebar} 40%, ${t.primaria} 40%, ${t.primaria} 100%);`;

      html += `
        <div class="col-6 col-sm-4">
          <div class="card h-100 p-2 text-center tema-card-item cursor-pointer position-relative ${isAtivo ? 'border-primary border-2 bg-primary-subtle shadow-sm' : 'border-secondary-subtle bg-white'}"
               id="cardTema_${t.codigo}"
               onclick="selecionarTemaEscola('${t.codigo}')"
               title="${escapeHtml(t.nome)}: ${escapeHtml(t.descricao)}"
               style="cursor: pointer; transition: all 0.2s; min-height: 95px;">
            <div class="rounded mb-2 shadow-sm d-flex align-items-center justify-content-center position-relative" style="height: 36px; ${gradiente}">
              <div style="width: 12px; height: 12px; border-radius: 50%; background: ${t.sidebarAtiva}; box-shadow: 0 0 4px rgba(0,0,0,0.5);" title="Destaque"></div>
            </div>
            <div class="small fw-bold text-truncate text-dark mb-1" style="font-size: 0.73rem;">
              ${escapeHtml(t.nome)}
            </div>
            <div class="mt-auto" id="badgeTema_${t.codigo}">
              ${isAtivo 
                ? '<span class="badge bg-primary text-white" style="font-size: 0.65rem;"><i class="bi bi-check-circle-fill me-1"></i>Activo</span>' 
                : '<span class="badge bg-light text-secondary border" style="font-size: 0.65rem;">Escolher</span>'}
            </div>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
  }

  // Atualizar indicadores visuais do espectro se solicitado
  if (atualizarIndicadores) {
    const nomeAtivo = (window.SIGE_TEMAS[codigoAtual]?.nome) || 'Personalizado';
    atualizarIndicadoresEspectro(corPrimaria, nomeAtivo);
  }
}
window.renderizarSeletorTemas = renderizarSeletorTemas;

function selecionarTemaEscola(codigo) {
  const input = document.getElementById('confEscolaTemaCodigo');
  if (input) input.value = codigo;

  const painelCustom = document.getElementById('painelCoresPersonalizadas');
  if (painelCustom) {
    painelCustom.style.display = (codigo === 'personalizado') ? 'block' : 'none';
  }

  const t = window.SIGE_TEMAS[codigo] || window.SIGE_TEMAS.padrao_azul;
  if (codigo !== 'personalizado') {
    const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
    setVal('confEscolaCorPrimaria', t.primaria);
    setVal('confEscolaCorPrimariaHex', t.primaria);
    setVal('confEscolaCorHover', t.hover);
    setVal('confEscolaCorHoverHex', t.hover);
    setVal('confEscolaCorSidebar', t.sidebar);
    setVal('confEscolaCorSidebarHex', t.sidebar);
    setVal('confEscolaCorSidebarAtiva', t.sidebarAtiva);
    setVal('confEscolaCorSidebarAtivaHex', t.sidebarAtiva);

    const pickerManual = document.getElementById('pickerEspectroManual');
    if (pickerManual) pickerManual.value = t.primaria;
  }

  renderizarSeletorTemas();
  aplicarTemaEFundoAoVivo();
}
window.selecionarTemaEscola = selecionarTemaEscola;

function aoMudarCorCustomizada() {
  const syncHex = (idColor, idHex) => {
    const c = document.getElementById(idColor);
    const h = document.getElementById(idHex);
    if (c && h) h.value = c.value;
  };
  syncHex('confEscolaCorPrimaria', 'confEscolaCorPrimariaHex');
  syncHex('confEscolaCorHover', 'confEscolaCorHoverHex');
  syncHex('confEscolaCorSidebar', 'confEscolaCorSidebarHex');
  syncHex('confEscolaCorSidebarAtiva', 'confEscolaCorSidebarAtivaHex');

  const inputTema = document.getElementById('confEscolaTemaCodigo');
  if (inputTema) inputTema.value = 'personalizado';

  const corPrimaria = document.getElementById('confEscolaCorPrimaria')?.value || '#1e3a8a';
  const pickerManual = document.getElementById('pickerEspectroManual');
  if (pickerManual) pickerManual.value = corPrimaria;

  renderizarSeletorTemas();
  aplicarTemaEFundoAoVivo();
}
window.aoMudarCorCustomizada = aoMudarCorCustomizada;

function aoMudarHexColor(idColor, val) {
  if (val && /^#[0-9A-Fa-f]{6}$/.test(val.trim())) {
    const el = document.getElementById(idColor);
    if (el) el.value = val.trim();
    aoMudarCorCustomizada();
  }
}
window.aoMudarHexColor = aoMudarHexColor;
window.aoMudarHexColor = aoMudarHexColor;

function fundosSaoIguais(urlA, urlB) {
  if (!urlA || !urlB) return false;
  if (urlA === urlB) return true;
  const limpa = u => String(u).trim().replace(/^https?:\/\/[^\/]+/, '').replace(/^\/+/, '');
  return limpa(urlA) === limpa(urlB);
}
window.fundosSaoIguais = fundosSaoIguais;

function obterGaleriaFundosEscola() {
  const e = state.escolaAtual || state.tenant || {};
  const eId = (e.id || '').toString().trim();
  let galeria = Array.isArray(e.galeria_fundos) 
    ? e.galeria_fundos.filter(item => item && !['fundo_logo_escola', 'fundo_emblema_nacional', 'fundo_logo_sige', 'fundo_sem_imagem'].includes(item.id))
    : [];

  try {
    localStorage.removeItem('sige_galeria_fundos_default');
  } catch (_) {}

  if (eId && eId !== 'default' && eId !== 'escola_atual') {
    const chaveLocal = `sige_galeria_fundos_${eId}`;
    try {
      const salvoLocal = JSON.parse(localStorage.getItem(chaveLocal) || '[]');
      if (Array.isArray(salvoLocal)) {
        salvoLocal.forEach(item => {
          if (item && item.url && !galeria.some(g => g.id === item.id || fundosSaoIguais(g.url, item.url))) {
            galeria.push(item);
          }
        });
      }
    } catch (_) {}
  }

  // Se a escola possuir imagem de fundo ativa própria que não está nos padrões nem na lista, adiciona-a como item na galeria
  const fundoAtual = e.imagem_fundo_url || e.imagem_fundo_base64 || '';
  if (fundoAtual && fundoAtual !== 'SEM_IMAGEM') {
    const jaExiste = galeria.some(g => fundosSaoIguais(g.url, fundoAtual))
      || fundosSaoIguais(fundoAtual, 'img/emblema-mocambique.png')
      || fundosSaoIguais(fundoAtual, 'img/logo-sige.png')
      || fundosSaoIguais(fundoAtual, e.logo_url)
      || fundosSaoIguais(fundoAtual, e.logo_base64);

    if (!jaExiste) {
      let nomeFundo = 'Imagem de Fundo';
      try {
        const partes = fundoAtual.split('/');
        const ultima = partes[partes.length - 1].split('?')[0];
        if (ultima && ultima.length > 2 && !ultima.startsWith('data:')) {
          nomeFundo = decodeURIComponent(ultima);
        } else {
          nomeFundo = 'Fundo Oficial da Escola';
        }
      } catch (_) {
        nomeFundo = 'Fundo Oficial da Escola';
      }
      galeria.unshift({
        id: 'fundo_custom_ativo',
        nome: nomeFundo,
        url: fundoAtual,
        tipo: 'UPLOAD',
        criado_em: new Date().toISOString()
      });
    }
  }

  const padroes = [];
  const logoEscola = e.logo_url || e.logo_base64;
  if (logoEscola && !logoEscola.includes('emblema-mocambique.png')) {
    padroes.push({
      id: 'fundo_logo_escola',
      nome: 'Logótipo da Escola',
      url: logoEscola,
      tipo: 'LOGO_ESCOLA',
      descricao: 'Usa a marca oficial da instituição como marca d\'água'
    });
  }

  padroes.push({
    id: 'fundo_emblema_nacional',
    nome: 'Emblema Nacional',
    url: 'img/emblema-mocambique.png',
    tipo: 'OFICIAL_MEC',
    descricao: 'Emblema da República de Moçambique'
  });

  padroes.push({
    id: 'fundo_logo_sige',
    nome: 'Marca Oficial SIGE',
    url: 'img/logo-sige.png',
    tipo: 'PADRAO_SIGE',
    descricao: 'Marca padrão institucional SIGE'
  });

  padroes.push({
    id: 'fundo_sem_imagem',
    nome: 'Sem Imagem (Liso)',
    url: 'SEM_IMAGEM',
    tipo: 'NENHUM',
    descricao: 'Apenas fundo limpo sem marcas d\'água'
  });

  const mapa = new Map();
  padroes.concat(galeria).forEach(item => {
    if (item && item.id && !mapa.has(item.id)) {
      mapa.set(item.id, item);
    }
  });

  return Array.from(mapa.values());
}
window.obterGaleriaFundosEscola = obterGaleriaFundosEscola;

function renderizarGaleriaFundos() {
  const container = document.getElementById('galeriaFundosContainer');
  if (!container) return;

  const e = state.escolaAtual || state.tenant || {};
  const galeria = obterGaleriaFundosEscola();
  const fundoAtivoAtual = document.getElementById('confEscolaFundoFinalValue')?.value || '';
  const modoAtual = document.getElementById('confEscolaFundoModo')?.value || 'marca_dagua';

  const contadorEl = document.getElementById('contadorGaleriaFundos');
  if (contadorEl) {
    contadorEl.textContent = `${galeria.length} opção${galeria.length > 1 ? 'ões' : ''}`;
  }

  let html = '';
  galeria.forEach(item => {
    let isAtivo = false;
    if (modoAtual === 'nenhum' || fundoAtivoAtual === 'SEM_IMAGEM') {
      isAtivo = (item.url === 'SEM_IMAGEM' || item.id === 'fundo_sem_imagem');
    } else {
      if (item.url === 'SEM_IMAGEM' || item.id === 'fundo_sem_imagem') {
        isAtivo = false;
      } else if (fundoAtivoAtual) {
        if (fundosSaoIguais(item.url, fundoAtivoAtual)) {
          isAtivo = true;
        } else if (item.id === 'fundo_emblema_nacional' && (fundoAtivoAtual.includes('emblema-mocambique') || fundosSaoIguais(fundoAtivoAtual, 'img/emblema-mocambique.png'))) {
          isAtivo = true;
        } else if (item.id === 'fundo_logo_escola' && (fundosSaoIguais(fundoAtivoAtual, e.logo_url) || fundosSaoIguais(fundoAtivoAtual, e.logo_base64))) {
          isAtivo = true;
        } else if (item.id === 'fundo_logo_sige' && (fundoAtivoAtual.includes('logo-sige') || fundosSaoIguais(fundoAtivoAtual, 'img/logo-sige.png'))) {
          isAtivo = true;
        }
      } else {
        if (e.usar_emblema_nacional !== false) {
          isAtivo = (item.id === 'fundo_emblema_nacional');
        } else if (e.logo_url || e.logo_base64) {
          isAtivo = (item.id === 'fundo_logo_escola');
        } else {
          isAtivo = (item.id === 'fundo_logo_sige');
        }
      }
    }

    const previewThumb = (item.url === 'SEM_IMAGEM')
      ? `<div class="d-flex align-items-center justify-content-center bg-light rounded text-muted mb-1" style="height: 52px;"><i class="bi bi-slash-circle fs-4"></i></div>`
      : `<div class="d-flex align-items-center justify-content-center bg-white rounded p-1 mb-1 border" style="height: 52px; overflow: hidden;"><img src="${escapeHtml(item.url)}" alt="${escapeHtml(item.nome)}" style="max-height: 100%; max-width: 100%; object-fit: contain;"></div>`;

    html += `
      <div class="col-6 col-sm-4">
        <div class="card h-100 p-2 text-center fundo-card-item cursor-pointer position-relative ${isAtivo ? 'border-primary border-2 bg-primary-subtle shadow-sm' : 'border-secondary-subtle bg-white'}"
             onclick="selecionarFundoGaleria('${item.id}')"
             title="${escapeHtml(item.nome)}"
             style="cursor: pointer; transition: all 0.2s; min-height: 105px;">
          ${previewThumb}
          <div class="small fw-bold text-truncate text-dark mb-1" style="font-size: 0.72rem;">
            ${escapeHtml(item.nome)}
          </div>
          <div class="mt-auto">
            ${isAtivo 
              ? '<span class="badge bg-primary text-white" style="font-size: 0.65rem;"><i class="bi bi-check-circle-fill me-1"></i>Activo</span>' 
              : '<span class="badge bg-light text-secondary border" style="font-size: 0.65rem;">Usar</span>'}
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}
window.renderizarGaleriaFundos = renderizarGaleriaFundos;

function selecionarFundoGaleria(fundoId) {
  const galeria = obterGaleriaFundosEscola();
  const item = galeria.find(g => g.id === fundoId);
  if (!item) return;

  const inputFundo = document.getElementById('confEscolaFundoFinalValue');
  const selModo = document.getElementById('confEscolaFundoModo');

  if (item.url === 'SEM_IMAGEM' || item.id === 'fundo_sem_imagem') {
    if (inputFundo) inputFundo.value = 'SEM_IMAGEM';
    if (selModo) selModo.value = 'nenhum';
  } else {
    if (inputFundo) inputFundo.value = item.url;
    if (selModo && selModo.value === 'nenhum') {
      selModo.value = 'marca_dagua';
    }
  }

  const modo = selModo?.value || 'marca_dagua';
  const opacidade = parseInt(document.getElementById('confEscolaFundoOpacidade')?.value || '15');
  atualizarVisualizacaoFundo(inputFundo?.value || '', modo, opacidade);
  renderizarGaleriaFundos();
  aplicarTemaEFundoAoVivo();
}
window.selecionarFundoGaleria = selecionarFundoGaleria;

function atualizarVisualizacaoFundo(fundoSrc, modo = 'marca_dagua', opacidade = 15) {
  const imgPreview = document.getElementById('confEscolaFundoPreview');
  const statusEl = document.getElementById('confEscolaFundoStatus');
  const modoTxtEl = document.getElementById('confEscolaFundoModoTxt');
  const btnRemover = document.getElementById('btnRemoverFundo');

  const modosNomes = {
    marca_dagua: 'Marca de Água Central Sutil',
    cobertura_total: 'Papel de Parede Total (Wallpaper)',
    padrao_textura: 'Padrão Textura Suave',
    nenhum: 'Sem Imagem de Fundo (Apenas Cores)'
  };

  if (modoTxtEl) {
    modoTxtEl.textContent = `Modo: ${modosNomes[modo] || modo} (${opacidade}%)`;
  }

  if (modo === 'nenhum' || !fundoSrc || fundoSrc === 'SEM_IMAGEM') {
    if (imgPreview) {
      imgPreview.src = 'img/logo-sige.png';
      imgPreview.style.opacity = '0.2';
    }
    if (statusEl) statusEl.textContent = 'Sem Imagem de Fundo Activa';
    if (btnRemover) btnRemover.style.display = 'none';
  } else {
    if (imgPreview) {
      imgPreview.src = fundoSrc;
      imgPreview.style.opacity = '1';
    }
    const galeria = obterGaleriaFundosEscola();
    const item = galeria.find(g => fundosSaoIguais(g.url, fundoSrc) || (g.id === 'fundo_emblema_nacional' && fundoSrc.includes('emblema-mocambique')));
    if (statusEl) statusEl.textContent = item?.nome ? `Fundo: ${item.nome}` : 'Imagem Própria Activa';
    if (btnRemover) btnRemover.style.display = 'inline-block';
  }
}
window.atualizarVisualizacaoFundo = atualizarVisualizacaoFundo;

function atualizarLabelOpacidadeFundo(val) {
  const lbl = document.getElementById('lblFundoOpacidade');
  if (lbl) lbl.textContent = `${val}%`;
  aplicarTemaEFundoAoVivo();
}
window.atualizarLabelOpacidadeFundo = atualizarLabelOpacidadeFundo;

function aoMudarModoFundo(modo) {
  const inputFundo = document.getElementById('confEscolaFundoFinalValue');
  const opacidade = parseInt(document.getElementById('confEscolaFundoOpacidade')?.value || '15');
  atualizarVisualizacaoFundo(inputFundo?.value || '', modo, opacidade);
  renderizarGaleriaFundos();
  aplicarTemaEFundoAoVivo();
}
window.aoMudarModoFundo = aoMudarModoFundo;

function removerImagemFundoEscola() {
  const inputFundo = document.getElementById('confEscolaFundoFinalValue');
  if (inputFundo) inputFundo.value = 'SEM_IMAGEM';
  const selModo = document.getElementById('confEscolaFundoModo');
  if (selModo) selModo.value = 'nenhum';
  const opacidade = parseInt(document.getElementById('confEscolaFundoOpacidade')?.value || '15');
  atualizarVisualizacaoFundo('SEM_IMAGEM', 'nenhum', opacidade);
  renderizarGaleriaFundos();
  aplicarTemaEFundoAoVivo();
}
window.removerImagemFundoEscola = removerImagemFundoEscola;

async function adicionarFundoAGaleria(url, nome) {
  let galeria = obterGaleriaFundosEscola().filter(g => !['fundo_logo_escola', 'fundo_emblema_nacional', 'fundo_logo_sige', 'fundo_sem_imagem'].includes(g.id));
  const novoId = 'fundo_' + Date.now();
  galeria.unshift({
    id: novoId,
    nome: nome || 'Fundo Próprio',
    url: url,
    tipo: 'UPLOAD',
    criado_em: new Date().toISOString()
  });

  const e = state.escolaAtual || state.tenant || {};
  const eId = (e.id || '').toString().trim();
  if (eId && eId !== 'default' && eId !== 'escola_atual') {
    const chaveLocal = `sige_galeria_fundos_${eId}`;
    try {
      localStorage.setItem(chaveLocal, JSON.stringify(galeria));
    } catch (_) {}
  }

  if (state.escolaAtual) state.escolaAtual.galeria_fundos = galeria;
  if (state.tenant) state.tenant.galeria_fundos = galeria;

  const inputFundo = document.getElementById('confEscolaFundoFinalValue');
  if (inputFundo) inputFundo.value = url;
  const selModo = document.getElementById('confEscolaFundoModo');
  if (selModo && selModo.value === 'nenhum') selModo.value = 'marca_dagua';

  const modo = selModo?.value || 'marca_dagua';
  const opacidade = parseInt(document.getElementById('confEscolaFundoOpacidade')?.value || '15');
  atualizarVisualizacaoFundo(url, modo, opacidade);
  renderizarGaleriaFundos();
  aplicarTemaEFundoAoVivo();
}
window.adicionarFundoAGaleria = adicionarFundoAGaleria;

function processarUploadFundoLocal(input) {
  const file = input.files?.[0];
  if (!file) return;

  if (!file.type.startsWith('image/')) {
    alert('Por favor, seleccione um ficheiro de imagem válido (PNG, JPG, WebP).');
    return;
  }

  if (file.size > 8 * 1024 * 1024) {
    alert('A imagem seleccionada é muito pesada (máximo 8MB).');
    return;
  }

  const reader = new FileReader();
  reader.onload = async function(e) {
    const dataUrl = e.target.result;
    const nomeFicheiro = file.name ? file.name.replace(/\.[^/.]+$/, "") : `Fundo Carregado`;
    await adicionarFundoAGaleria(dataUrl, nomeFicheiro);
    input.value = '';
  };
  reader.readAsDataURL(file);
}
window.processarUploadFundoLocal = processarUploadFundoLocal;

async function processarUrlFundo(url) {
  if (!url || !url.trim()) {
    alert('Por favor, insira um link / URL válido da imagem.');
    return;
  }
  const urlLimpo = url.trim();
  await adicionarFundoAGaleria(urlLimpo, 'Fundo Web');
  const inputEl = document.getElementById('confEscolaFundoUrl');
  if (inputEl) inputEl.value = '';
}
window.processarUrlFundo = processarUrlFundo;

function aplicarTemaEFundoAoVivo() {
  const temaCodigo = document.getElementById('confEscolaTemaCodigo')?.value || 'padrao_azul';
  const temaConfig = window.SIGE_TEMAS[temaCodigo] || window.SIGE_TEMAS.padrao_azul;

  const primaria = document.getElementById('confEscolaCorPrimaria')?.value || temaConfig.primaria;
  const hover = document.getElementById('confEscolaCorHover')?.value || temaConfig.hover;
  const sidebar = document.getElementById('confEscolaCorSidebar')?.value || temaConfig.sidebar;
  const sidebarAtiva = document.getElementById('confEscolaCorSidebarAtiva')?.value || temaConfig.sidebarAtiva;

  const fundoSrc = document.getElementById('confEscolaFundoFinalValue')?.value || '';
  const modoFundo = document.getElementById('confEscolaFundoModo')?.value || 'marca_dagua';
  const opacidade = parseInt(document.getElementById('confEscolaFundoOpacidade')?.value || '15');

  const escolaFake = {
    id: state.escolaAtual?.id || state.tenant?.id || 'escola_atual',
    tema_codigo: temaCodigo,
    tema_cor_primaria: primaria,
    tema_cor_hover: hover,
    tema_cor_sidebar: sidebar,
    tema_cor_sidebar_ativa: sidebarAtiva,
    imagem_fundo_url: fundoSrc,
    imagem_fundo_modo: modoFundo,
    imagem_fundo_opacidade: opacidade
  };

  aplicarTemaEFundoInstituicao(escolaFake);
  atualizarVisualizacaoFundo(fundoSrc, modoFundo, opacidade);
}
window.aplicarTemaEFundoAoVivo = aplicarTemaEFundoAoVivo;

function restaurarPadraoTemaEFundo() {
  const root = document.documentElement;
  const t = window.SIGE_TEMAS?.padrao_azul || {
    primaria: '#1e3a8a',
    hover: '#172554',
    sidebar: '#0f172a',
    sidebarAtiva: '#38bdf8'
  };

  root.style.setProperty('--primary-color', t.primaria);
  root.style.setProperty('--primary-hover', t.hover);
  root.style.setProperty('--sidebar-bg', t.sidebar);
  root.style.setProperty('--sidebar-active', t.sidebarAtiva);

  // Remover folha de estilos dinâmicos injectados de escolas específicas
  const styleTag = document.getElementById('sige-tema-dinamico');
  if (styleTag) {
    styleTag.remove();
  }

  // Ocultar marca de água e repor para modo padrão institucional
  const elMarcaDagua = document.querySelector('.marca-dagua-sistema');
  if (elMarcaDagua) {
    elMarcaDagua.style.display = 'none';
    elMarcaDagua.style.backgroundImage = '';
  }

  // Limpar qualquer resquício de chave global antiga
  try {
    localStorage.removeItem('sige_tema_ativo');
  } catch (_) {}

  // Se os campos do formulário de configuração da escola existirem na DOM, repô-los
  const inputTema = document.getElementById('confEscolaTemaCodigo');
  if (inputTema) inputTema.value = 'padrao_azul';

  const setV = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
  setV('confEscolaCorPrimaria', t.primaria);
  setV('confEscolaCorPrimariaHex', t.primaria);
  setV('confEscolaCorHover', t.hover);
  setV('confEscolaCorHoverHex', t.hover);
  setV('confEscolaCorSidebar', t.sidebar);
  setV('confEscolaCorSidebarHex', t.sidebar);
  setV('confEscolaCorSidebarAtiva', t.sidebarAtiva);
  setV('confEscolaCorSidebarAtivaHex', t.sidebarAtiva);
  setV('confEscolaFundoFinalValue', '');
  setV('confEscolaFundoModo', 'marca_dagua');
  setV('confEscolaFundoOpacidade', '15');

  const lbl = document.getElementById('lblFundoOpacidade');
  if (lbl) lbl.textContent = '15%';

  if (typeof renderizarSeletorTemas === 'function') {
    renderizarSeletorTemas();
  }
  if (typeof renderizarGaleriaFundos === 'function') {
    renderizarGaleriaFundos();
  }
}
window.restaurarPadraoTemaEFundo = restaurarPadraoTemaEFundo;

document.getElementById('formEscolaInfo')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const emailLimpo = (document.getElementById('confEscolaEmail')?.value || '').trim().replace(/\.+@/, '@');
    const body = {
      nome: document.getElementById('confEscolaNome').value,
      tipo_escola: document.getElementById('confEscolaTipo')?.value || 'S',
      ano_letivo_ativo: document.getElementById('confEscolaAnoLetivo').value,
      trimestre_ativo: document.getElementById('confEscolaTrimestreAtivo').value,
      publicacao_notas_trimestre: document.getElementById('confEscolaPublicacaoNotas')?.value || 'TODOS',
      telefone: document.getElementById('confEscolaTelefone').value,
      email: emailLimpo,
      director_nome: document.getElementById('confEscolaDirector').value,
      dap_nome: document.getElementById('confEscolaDAP').value,
      chefe_secretaria_nome: document.getElementById('confEscolaChefeSec').value,
      provincia: document.getElementById('confEscolaProvincia').value,
      distrito: document.getElementById('confEscolaDistrito').value,
      usar_emblema_nacional: document.getElementById('confEscolaEmblema').checked,
      logo_url: document.getElementById('confEscolaLogoFinalValue')?.value || '',
      galeria_logos: (typeof obterGaleriaLogosEscola === 'function') 
        ? obterGaleriaLogosEscola().filter(g => g && g.tipo === 'UPLOAD') 
        : [],
      tema_codigo: document.getElementById('confEscolaTemaCodigo')?.value || 'padrao_azul',
      tema_cor_primaria: document.getElementById('confEscolaCorPrimaria')?.value || '#1e3a8a',
      tema_cor_hover: document.getElementById('confEscolaCorHover')?.value || '#172554',
      tema_cor_sidebar: document.getElementById('confEscolaCorSidebar')?.value || '#0f172a',
      tema_cor_sidebar_ativa: document.getElementById('confEscolaCorSidebarAtiva')?.value || '#38bdf8',
      imagem_fundo_url: document.getElementById('confEscolaFundoFinalValue')?.value || '',
      imagem_fundo_modo: document.getElementById('confEscolaFundoModo')?.value || 'marca_dagua',
      imagem_fundo_opacidade: parseInt(document.getElementById('confEscolaFundoOpacidade')?.value || '15'),
      galeria_fundos: (typeof obterGaleriaFundosEscola === 'function') 
        ? obterGaleriaFundosEscola().filter(g => g && g.tipo === 'UPLOAD') 
        : []
    };
    const res = await apiFetch('/api/v1/escola-admin/info', {
      method: 'PUT',
      body: JSON.stringify(body)
    });
    if (res.success) {
      if (state.tenant) {
        state.tenant.publicacao_notas_trimestre = body.publicacao_notas_trimestre;
        state.tenant.permitir_visualizacao_notas = body.publicacao_notas_trimestre !== 'NENHUM';
        if (typeof atualizarBotaoToggleNotasDap === 'function') {
          atualizarBotaoToggleNotasDap(body.publicacao_notas_trimestre, state.tenant.permitir_visualizacao_notas);
        }
      }
      if (res.data) {
        if (state.escolaAtual) Object.assign(state.escolaAtual, res.data);
        if (state.tenant) Object.assign(state.tenant, res.data);
        if (typeof aplicarTemaEFundoInstituicao === 'function') {
          aplicarTemaEFundoInstituicao(res.data);
        }
      }
      await carregarEscolaETurmas();
      if (typeof mostrarToast === 'function') {
        mostrarToast('Configurações da escola, identidade visual, tema e fundo actualizados com sucesso!', 'success');
      }
      alert('Configurações da escola, identidade visual, tema e fundo actualizados com sucesso!');
    }
  } catch (err) {
    console.error('Erro ao actualizar escola:', err);
    alert('Atenção: ' + (err.message || 'Erro ao actualizar dados da escola'));
  }
});

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

  const infoExameEl = document.getElementById('infoExameMtGrau');
  if (infoExameEl) {
    const temExame = typeof window.classeTemExame === 'function' && window.classeTemExame(grauSel);
    if (temExame) {
      infoExameEl.innerHTML = '<span class="badge bg-danger bg-opacity-10 text-danger border border-danger-subtle px-2 py-1"><i class="bi bi-file-earmark-check-fill me-1"></i>A Classe tem Exame: <strong>Sim (Com Exame)</strong></span>';
    } else {
      infoExameEl.innerHTML = '<span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary-subtle px-2 py-1"><i class="bi bi-dash-circle me-1"></i>A Classe tem Exame: <strong>Não (Sem Exame)</strong></span>';
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
            <button type="button" id="btnAdicionarNivelTurma" class="btn btn-link btn-sm p-0 text-success fw-semibold small text-decoration-none" style="display: none;" onclick="window.promptAdicionarNivelModal('mtGrau')">
              <i class="bi bi-plus-circle me-1"></i>+ Nível / Classe
            </button>
          </div>
          <select id="mtGrau" class="form-select" required onchange="if(this.value==='__NOVO_NIVEL__'){ window.promptAdicionarNivelModal('mtGrau'); } else { atualizarAssistenteCriarTurma(); }">
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
          <div id="infoExameMtGrau" class="mt-1"></div>
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
              <i class="bi bi-plus-circle me-1"></i>+ Nível / Classe
            </button>
          </div>
          <select id="mlGrau" class="form-select" required onchange="if(this.value==='__NOVO_NIVEL__'){ window.promptAdicionarNivelModal('mlGrau'); } else { document.getElementById('mlArea').innerHTML = window.obterTodasAreasOficiais(this.value).map(a => '<option value=\\'' + a + '\\'>' + a + '</option>').join(''); window.atualizarInfoExameLote(this.value); }">
            ${optGraus}
          </select>
          <div id="infoExameMlGrau" class="mt-1"></div>
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
    if (typeof window.atualizarInfoExameLote === 'function') window.atualizarInfoExameLote(sel.value);
  };

  window.atualizarInfoExameLote = function(grauVal) {
    const el = document.getElementById('infoExameMlGrau');
    if (!el) return;
    const temExame = typeof window.classeTemExame === 'function' && window.classeTemExame(grauVal);
    if (temExame) {
      el.innerHTML = '<span class="badge bg-danger bg-opacity-10 text-danger border border-danger-subtle px-2 py-1"><i class="bi bi-file-earmark-check-fill me-1"></i>A Classe tem Exame: <strong>Sim (Com Exame)</strong></span>';
    } else {
      el.innerHTML = '<span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary-subtle px-2 py-1"><i class="bi bi-dash-circle me-1"></i>A Classe tem Exame: <strong>Não (Sem Exame)</strong></span>';
    }
  };

  setTimeout(() => {
    const initGrau = document.getElementById('mlGrau')?.value;
    if (initGrau && typeof window.atualizarInfoExameLote === 'function') {
      window.atualizarInfoExameLote(initGrau);
    }
  }, 100);

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
                <i class="bi bi-plus-circle me-1"></i>+ Nível / Classe
              </button>
            </div>
            <select id="mtEditGrau" class="form-select" required onchange="if(this.value==='__NOVO_NIVEL__') { window.promptAdicionarNivelModal('mtEditGrau'); } else { if(typeof window.atualizarInfoExameEditTurma === 'function') window.atualizarInfoExameEditTurma(this.value); }">
              ${optGraus}
            </select>
            <div id="infoExameMtEditGrau" class="mt-1"></div>
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
      if (typeof window.atualizarInfoExameEditTurma === 'function') window.atualizarInfoExameEditTurma(sel.value);
    };

    window.atualizarInfoExameEditTurma = function(grauVal) {
      const el = document.getElementById('infoExameMtEditGrau');
      if (!el) return;
      const temExame = typeof window.classeTemExame === 'function' && window.classeTemExame(grauVal);
      if (temExame) {
        el.innerHTML = '<span class="badge bg-danger bg-opacity-10 text-danger border border-danger-subtle px-2 py-1"><i class="bi bi-file-earmark-check-fill me-1"></i>A Classe tem Exame: <strong>Sim (Com Exame)</strong></span>';
      } else {
        el.innerHTML = '<span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary-subtle px-2 py-1"><i class="bi bi-dash-circle me-1"></i>A Classe tem Exame: <strong>Não (Sem Exame)</strong></span>';
      }
    };

    setTimeout(() => {
      const initG = document.getElementById('mtEditGrau')?.value;
      if (initG && typeof window.atualizarInfoExameEditTurma === 'function') window.atualizarInfoExameEditTurma(initG);
    }, 100);

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

// ==================== 4. ALUNOS ====================
async function carregarAlunos() {
  try {
    const anoAtivo = state.tenant?.ano_letivo_ativo || '2026';
    if (!state.filtroAlunoAno) {
      state.filtroAlunoAno = anoAtivo;
    }

    const [resAlunos, resTurmas, resStats, resDisciplinas] = await Promise.all([
      apiFetch('/api/v1/alunos'),
      apiFetch('/api/v1/escola-admin/turmas'),
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
  if (!state.filtroAlunoAno) {
    state.filtroAlunoAno = anoAtivo;
  }

  const anosSet = new Set([anoAtivo, '2026', '2025', '2024']);
  (state.todosAlunos || []).forEach(a => {
    if (a.ano_ingresso) anosSet.add(String(a.ano_ingresso));
    else if (a.matricula && a.matricula.length >= 4 && a.matricula.slice(0, 4).match(/^\d{4}$/)) {
      anosSet.add(a.matricula.slice(0, 4));
    }
  });
  (state.todasTurmas || []).forEach(t => {
    if (t.ano_letivo) anosSet.add(String(t.ano_letivo));
  });

  const anosOrdenados = Array.from(anosSet).sort((a, b) => parseInt(b) - parseInt(a));
  const valorAtual = state.filtroAlunoAno;

  selAno.innerHTML = `
    <option value="TODOS" ${valorAtual === 'TODOS' ? 'selected' : ''}>Todos os Anos</option>
    ${anosOrdenados.map(ano => `
      <option value="${ano}" ${valorAtual === ano ? 'selected' : ''}>
        ${ano} ${ano === anoAtivo ? '(Activo)' : ''}
      </option>
    `).join('')}
  `;
}

window.aoMudarFiltroAnoAlunos = function(ano) {
  state.filtroAlunoAno = ano;
  renderizarBotoesClassesAlunos();
};

function obterAlunosFiltradosPorAno() {
  const anoFiltro = state.filtroAlunoAno || state.tenant?.ano_letivo_ativo || '2026';
  if (!anoFiltro || anoFiltro === 'TODOS') {
    return state.todosAlunos || [];
  }
  return (state.todosAlunos || []).filter(a => {
    const anoAluno = a.ano_ingresso || (a.matricula && a.matricula.length >= 4 && a.matricula.slice(0, 4).match(/^\d{4}$/) ? a.matricula.slice(0, 4) : null) || (getAlunoTurma(a)?.ano_letivo);
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

// ==================== UTILITÁRIOS PARA ÁREAS/SECÇÕES VINCULADAS ÀS TURMAS ====================
window.obterTodasAreasOficiais = function(classeFiltro = null) {
  // Lista oficial do currículo (exatamente como visível na Secção/Área de Estudo e Turmas)
  const areasPadrao = [
    'Ensino Geral',
    'Ciências com Biologia',
    'Ciências com Desenho',
    'Ciências com Geografia',
    'Letras com Geografia',
    'Letras com História'
  ];

  let areas = [...areasPadrao];

  // 1. Adicionar áreas das disciplinas cadastradas no sistema
  (state.todasDisciplinas || []).forEach(d => {
    if (d.area && d.area.trim()) {
      const aNorm = normalizarArea(d.area);
      if (aNorm && !areas.some(x => x.toLowerCase() === aNorm.toLowerCase())) {
        if (!classeFiltro || classeFiltro === 'TODAS' || !d.classe || normalizarClasse(d.classe) === normalizarClasse(classeFiltro)) {
          areas.push(aNorm);
        }
      }
    }
  });

  // 2. Adicionar áreas personalizadas salvas via botão "Nova Secção / Área" ou localStorage
  try {
    const chaves = Object.keys(localStorage).filter(k => k.startsWith('sige_custom_areas_'));
    chaves.forEach(k => {
      const val = localStorage.getItem(k);
      if (val) {
        const parsed = JSON.parse(val);
        if (Array.isArray(parsed)) {
          parsed.forEach(p => {
            if (p && typeof p === 'string' && p.trim()) {
              const pNorm = normalizarArea(p);
              if (pNorm && !areas.some(x => x.toLowerCase() === pNorm.toLowerCase())) {
                areas.push(pNorm);
              }
            }
          });
        }
      }
    });
  } catch (e) {}

  // 3. Adicionar áreas já cadastradas nas turmas da escola
  const turmas = (Array.isArray(state.todasTurmas) && state.todasTurmas.length > 0)
    ? state.todasTurmas
    : (Array.isArray(window._modalAlunoTurmasCache) && window._modalAlunoTurmasCache.length > 0)
      ? window._modalAlunoTurmasCache
      : (Array.isArray(window._modalEditarAlunoTurmasCache) && window._modalEditarAlunoTurmasCache.length > 0)
        ? window._modalEditarAlunoTurmasCache
        : (state.turmasList || []);

  turmas.forEach(t => {
    if (t.area && t.area.trim()) {
      const aNorm = normalizarArea(t.area);
      if (aNorm && !areas.some(x => x.toLowerCase() === aNorm.toLowerCase())) {
        if (!classeFiltro || classeFiltro === 'TODAS' || !t.grau_ano || normalizarClasse(t.grau_ano) === normalizarClasse(classeFiltro)) {
          areas.push(aNorm);
        }
      }
    }
  });

  // 4. Adicionar áreas cadastradas nos alunos
  (state.todosAlunos || []).forEach(a => {
    const aArea = a.area || a.seccao || a.turma_area;
    if (aArea && aArea.trim()) {
      const aNorm = normalizarArea(aArea);
      if (aNorm && !areas.some(x => x.toLowerCase() === aNorm.toLowerCase())) {
        const aClasse = a.classe || a.turma_grau;
        if (!classeFiltro || classeFiltro === 'TODAS' || !aClasse || normalizarClasse(aClasse) === normalizarClasse(classeFiltro)) {
          areas.push(aNorm);
        }
      }
    }
  });

  // Se filtrado por classe (11ª/12ª ou 7ª/10ª):
  if (classeFiltro && classeFiltro !== 'TODAS' && classeFiltro !== 'SEM_TURMA') {
    const clsNorm = classeFiltro.trim().toLowerCase();
    if (clsNorm.includes('11') || clsNorm.includes('12')) {
      const prioritarias = ['Ciências com Biologia', 'Ciências com Desenho', 'Ciências com Geografia', 'Letras com Geografia', 'Letras com História', 'Ensino Geral'];
      const extras = areas.filter(a => !prioritarias.some(p => p.toLowerCase() === a.toLowerCase()));
      return [...prioritarias, ...extras];
    } else if (clsNorm.includes('7') || clsNorm.includes('8') || clsNorm.includes('9') || clsNorm.includes('10')) {
      const basica = ['Ensino Geral'];
      const extras = areas.filter(a => !basica.some(p => p.toLowerCase() === a.toLowerCase()));
      return [...basica, ...extras];
    }
  }

  return areas;
};

window.extrairAreasDasTurmas = function(turmasList, classeFiltro = null) {
  return window.obterTodasAreasOficiais(classeFiltro);
};

window.obterDescricaoAmigavelArea = function(area) {
  if (!area) return 'Ensino Geral';
  const aNorm = area.trim().toLowerCase();
  if (aNorm === 'geral' || aNorm === 'tronco comum' || aNorm === 'tronco comum / geral' || aNorm === 'ensino geral') {
    return 'Ensino Geral';
  }
  if (aNorm === 'ciências' || aNorm === 'cincias' || aNorm === 'ciencias') {
    return 'Ciências Naturais e Mat. (Grupo B)';
  }
  if (aNorm === 'letras') {
    return 'Comunicação e Ciências Sociais (Grupo A)';
  }
  if (aNorm === 'técnico' || aNorm === 'tecnico') {
    return 'Ensino Técnico Profissional';
  }
  return area;
};

async function modalEditarAluno(id) {
  try {
    const res = await apiFetch(`/api/v1/alunos/${id}`);
    const a = res.data || (res.id ? res : null);
    if (!a) return alert('Aluno não encontrado');

    const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
    const turmas = turmasRes.data || (Array.isArray(turmasRes) ? turmasRes : []) || [];
    window._modalEditarAlunoTurmasCache = turmas;
    const turmaAtualId = a.turma_id || (typeof a.turma === 'object' ? a.turma?.id : a.turma) || '';

    let avisoTurmasHtml = '';
    if (turmas.length === 0) {
      avisoTurmasHtml = `
        <div class="col-12">
          <div class="alert alert-warning py-2 small mb-0">
            <i class="bi bi-exclamation-triangle-fill me-1"></i> A sua instituição ainda não possui turmas cadastradas.
            <a href="javascript:void(0)" onclick="fecharModal(); navegarPara('turmas'); modalCriarTurmasEmLote();" class="fw-bold text-dark text-decoration-underline ms-1">
              Clique aqui para Gerar Turmas (1, 2, 3...)
            </a>
          </div>
        </div>
      `;
    }

    const classesAtivas = typeof window.obterClassesCurricularesAtivas === 'function'
    ? window.obterClassesCurricularesAtivas()
    : [
        '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
        '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
      ];
  const classesSet = new Set(classesAtivas);
    turmas.forEach(t => { if (t.grau_ano) classesSet.add(t.grau_ano.trim()); });
    if (a.classe) classesSet.add(a.classe.trim());
    if (a.turma_grau) classesSet.add(a.turma_grau.trim());

    const classesOrdenadas = Array.from(classesSet).sort((x, y) => {
      const numX = parseInt(x.replace(/\D/g, '')) || 0;
      const numY = parseInt(y.replace(/\D/g, '')) || 0;
      return numX - numY;
    });

    const turmaAtualObj = turmas.find(t => t.id === turmaAtualId);
    const classeAtual = a.classe || (turmaAtualObj ? turmaAtualObj.grau_ano : (a.turma_grau || ''));
    const areaAtual = a.area || (turmaAtualObj ? turmaAtualObj.area : 'Geral') || 'Geral';

    const areasDasTurmas = window.extrairAreasDasTurmas(turmas, classeAtual);
    if (areaAtual && !areasDasTurmas.some(ar => ar.toLowerCase() === areaAtual.toLowerCase())) {
      areasDasTurmas.unshift(areaAtual);
    }
    const opcoesAreas = areasDasTurmas.map(ar => 
      `<option value="${ar}" ${ar.toLowerCase() === areaAtual.toLowerCase() ? 'selected' : ''}>${window.obterDescricaoAmigavelArea(ar)}</option>`
    ).join('');

    const opcoesClasses = classesOrdenadas.map(c => 
      `<option value="${c}" ${c === classeAtual ? 'selected' : ''}>${c}</option>`
    ).join('');

    const opcoesTurmas = turmas.map(t => 
      `<option value="${t.id}" data-grau="${t.grau_ano || ''}" data-area="${t.area || 'Geral'}" ${t.id === turmaAtualId ? 'selected' : ''}>${t.grau_ano} &rarr; ${t.nome} (${t.area || 'Geral'} - ${t.turno || 'Diurno'})</option>`
    ).join('');

    const optProvincias = (state.geografia.provincias || []).map(p => 
      `<option value="${p}" ${p === a.provincia ? 'selected' : ''}>${p}</option>`
    ).join('');
    const distritos = state.geografia.distritos[a.provincia] || [];
    const optDistritos = distritos.map(d => 
      `<option value="${d}" ${d === a.distrito ? 'selected' : ''}>${d}</option>`
    ).join('');

    const dtNasc = a.data_nascimento ? a.data_nascimento.split('T')[0] : '';

    abrirModal(`Editar Aluno: ${a.nome || ''} (${a.matricula || ''})`, `
      <form id="formModalEditarAluno">
        <div class="alert alert-primary border-primary bg-primary bg-opacity-10 py-2 px-3 mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div>
            <small class="fw-bold text-primary d-block"><i class="bi bi-upc-scan me-1"></i> Código Oficial do Aluno (Dinâmico):</small>
            <small class="text-muted" style="font-size: 0.72rem;">Associa: Código da Escola + Classe + Turma + Ano + Área/Secção</small>
          </div>
          <code class="fs-6 fw-bold text-primary bg-white border border-primary px-3 py-1 rounded" id="mePreviewCodAluno">${a.matricula || '0101S0001.12.01.2026.cg'}</code>
        </div>
        <div class="row g-3">
          ${avisoTurmasHtml}
          <div class="col-md-8">
            <label class="form-label small fw-semibold">Nome Completo</label>
            <input type="text" id="meNome" class="form-control" required value="${a.nome || ''}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Apelido</label>
            <input type="text" id="meApelido" class="form-control" value="${a.apelido || ''}">
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-bold text-primary"><i class="bi bi-calendar-event me-1"></i> Ano de Ingresso</label>
            <input type="number" id="meAnoIngresso" class="form-control border-primary fw-semibold" value="${a.ano_ingresso || (a.matricula && a.matricula.length >= 4 && a.matricula.slice(0, 4).match(/^\d{4}$/) ? a.matricula.slice(0, 4) : (state.tenant?.ano_letivo_ativo || new Date().getFullYear()))}" min="2000" max="2099" required title="Ano lectivo de ingresso do aluno" oninput="atualizarPreviewCodigoAlunoEditar()">
            <small class="text-muted" style="font-size: 0.72rem;">Ano de admissão / trabalho anual.</small>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-bold text-primary"><i class="bi bi-mortarboard-fill me-1"></i> Classe do Aluno</label>
            <select id="meClasse" class="form-select border-primary fw-semibold" required onchange="aoMudarClasseEditarAluno()">
              <option value="">Selecione a Classe...</option>
              ${opcoesClasses}
            </select>
            <small class="text-muted" style="font-size: 0.72rem;">Essencial para alocação de turmas.</small>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-bold text-primary"><i class="bi bi-compass-fill me-1"></i> Secção / Área de Estudo</label>
            <select id="meArea" class="form-select border-primary fw-semibold" onchange="aoMudarAreaEditarAluno()">
              ${opcoesAreas}
            </select>
            <small class="text-muted" style="font-size: 0.72rem;">Obtida automaticamente das turmas cadastradas.</small>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-bold text-primary"><i class="bi bi-diagram-3-fill me-1"></i> Turma do Aluno</label>
            <select id="meTurma" class="form-select border-primary fw-semibold" onchange="aoMudarTurmaEditarAluno()">
              <option value="">(Sem turma - Aluno Pendente de Turma)</option>
              ${opcoesTurmas}
            </select>
            <small class="text-muted" style="font-size: 0.72rem;">Pode deixar pendente e gerar automaticamente.</small>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Data de Nascimento</label>
            <input type="date" id="meNasc" class="form-control" required value="${dtNasc}">
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">Género</label>
            <select id="meGenero" class="form-select">
              <option value="M" ${a.genero === 'M' ? 'selected' : ''}>Masculino</option>
              <option value="F" ${a.genero === 'F' ? 'selected' : ''}>Feminino</option>
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Estado do Aluno</label>
            <select id="meStatus" class="form-select">
              <option value="ATIVO" ${a.status === 'ATIVO' ? 'selected' : ''}>ATIVO</option>
              <option value="INATIVO" ${a.status === 'INATIVO' ? 'selected' : ''}>INATIVO</option>
              <option value="TRANSFERIDO" ${a.status === 'TRANSFERIDO' ? 'selected' : ''}>TRANSFERIDO</option>
              <option value="EVADIDO" ${a.status === 'EVADIDO' ? 'selected' : ''}>EVADIDO</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Tipo Documento</label>
            <select id="meTipoDoc" class="form-select">
              <option value="BI" ${a.tipo_documento === 'BI' ? 'selected' : ''}>BI</option>
              <option value="DIRE" ${a.tipo_documento === 'DIRE' ? 'selected' : ''}>DIRE</option>
              <option value="PASSAPORTE" ${a.tipo_documento === 'PASSAPORTE' ? 'selected' : ''}>Passaporte</option>
              <option value="CEDULA" ${a.tipo_documento === 'CEDULA' ? 'selected' : ''}>Cédula</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Nº Documento</label>
            <input type="text" id="meNumDoc" class="form-control" value="${a.numero_documento || ''}">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">NUIT (Opcional)</label>
            <input type="text" id="meNUIT" class="form-control" value="${a.nuit || ''}" placeholder="Ex: 109876543 (máx. 9 dígitos)" maxlength="9" inputmode="numeric" pattern="[0-9]{1,9}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Província</label>
            <select id="meProvincia" class="form-select" onchange="atualizarDistritosEditarAluno(this.value)">
              <option value="">Selecione</option>
              ${optProvincias}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Distrito</label>
            <select id="meDistrito" class="form-select">
              ${optDistritos || '<option value="">Selecione primeiro a província</option>'}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Nome do Pai</label>
            <input type="text" id="mePai" class="form-control" value="${a.pai || ''}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Nome da Mãe</label>
            <input type="text" id="meMae" class="form-control" value="${a.mae || ''}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Encarregado</label>
            <input type="text" id="meResp" class="form-control" value="${a.nome_responsavel || ''}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Contacto Encarregado</label>
            <input type="tel" id="meTelResp" class="form-control" value="${a.contato_responsavel || ''}" placeholder="Ex: 841234567 ou +258..." inputmode="tel">
          </div>
        </div>
        <button type="submit" class="btn btn-primary w-100 mt-4"><i class="bi bi-check2-circle me-1"></i> Guardar Alterações do Aluno</button>
      </form>
    `);

    // Sincronizar opções de turmas visíveis conforme a classe e área selecionadas
    if (typeof aoMudarClasseEditarAluno === 'function') {
      setTimeout(() => aoMudarClasseEditarAluno(false), 50);
    }

    document.getElementById('formModalEditarAluno').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const turmaVal = document.getElementById('meTurma').value || null;
        const classeVal = document.getElementById('meClasse').value || null;
        const areaVal = document.getElementById('meArea').value || 'Geral';
        const body = {
          nome: document.getElementById('meNome').value,
          apelido: document.getElementById('meApelido').value || null,
          ano_ingresso: document.getElementById('meAnoIngresso')?.value || null,
          classe: classeVal,
          area: areaVal,
          grupo: areaVal,
          data_nascimento: document.getElementById('meNasc').value,
          genero: document.getElementById('meGenero').value,
          turma: turmaVal,
          turma_id: turmaVal,
          tipo_documento: document.getElementById('meTipoDoc').value,
          numero_documento: document.getElementById('meNumDoc').value || null,
          nuit: document.getElementById('meNUIT').value || null,
          provincia: document.getElementById('meProvincia').value || null,
          distrito: document.getElementById('meDistrito').value || null,
          pai: document.getElementById('mePai').value || null,
          mae: document.getElementById('meMae').value || null,
          nome_responsavel: document.getElementById('meResp').value || null,
          contato_responsavel: document.getElementById('meTelResp').value || null,
          status: document.getElementById('meStatus').value
        };

        const resUp = await apiFetch(`/api/v1/alunos/${id}`, {
          method: 'PUT',
          body: JSON.stringify(body)
        });
        if (resUp.success || resUp.id) {
          alert('Dados do aluno e turma actualizados com sucesso!');
          fecharModal();
          await carregarAlunos();
          if (typeof carregarEscolaETurmas === 'function') await carregarEscolaETurmas();
        } else {
          alert(resUp.message || 'Erro ao actualizar dados do aluno');
        }
      } catch (err) {
        alert(err.message || 'Erro ao actualizar dados do aluno');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados do aluno: ' + (err.message || 'Servidor indisponível'));
  }
}

window.atualizarPreviewCodigoAlunoEditar = function() {
  const elPrev = document.getElementById('mePreviewCodAluno');
  if (!elPrev) return;
  const cls = document.getElementById('meClasse')?.value || '10ª Classe';
  const area = document.getElementById('meArea')?.value || 'Geral';
  const ano = document.getElementById('meAnoIngresso')?.value || '2026';
  const selTurma = document.getElementById('meTurma');
  let turmaNome = 'Turma 1';
  if (selTurma && selTurma.value) {
    const tObj = (window._modalEditarAlunoTurmasCache || state.todasTurmas || []).find(t => t.id === selTurma.value);
    if (tObj) turmaNome = tObj.nome;
  }
  elPrev.textContent = window.gerarPreviewCodigoAluno(null, cls, turmaNome, ano, area);
};

window.atualizarPreviewCodigoAlunoNovo = function() {
  const elPrev = document.getElementById('maPreviewCodAluno');
  if (!elPrev) return;
  const cls = document.getElementById('maClasse')?.value || '10ª Classe';
  const area = document.getElementById('maArea')?.value || 'Geral';
  const ano = document.getElementById('maAnoIngresso')?.value || '2026';
  const selTurma = document.getElementById('maTurma');
  let turmaNome = 'Turma 1';
  if (selTurma && selTurma.value) {
    const tObj = (window._modalAlunoTurmasCache || state.todasTurmas || []).find(t => t.id === selTurma.value);
    if (tObj) turmaNome = tObj.nome;
  }
  elPrev.textContent = window.gerarPreviewCodigoAluno(null, cls, turmaNome, ano, area);
};

window.aoMudarClasseEditarAluno = function(limparTurma = true) {
  const selClasse = document.getElementById('meClasse');
  const selTurma = document.getElementById('meTurma');
  const selArea = document.getElementById('meArea');
  if (!selClasse || !selTurma) return;
  const cls = selClasse.value;

  if (selArea) {
    const turmas = window._modalEditarAlunoTurmasCache || state.turmasList || [];
    const areasDisponiveis = window.extrairAreasDasTurmas(turmas, cls);
    const valAtual = selArea.value;

    selArea.innerHTML = areasDisponiveis.map(ar => 
      `<option value="${ar}">${window.obterDescricaoAmigavelArea(ar)}</option>`
    ).join('');

    if (areasDisponiveis.some(ar => ar.toLowerCase() === valAtual.toLowerCase())) {
      selArea.value = areasDisponiveis.find(ar => ar.toLowerCase() === valAtual.toLowerCase());
    } else if (areasDisponiveis.length > 0) {
      selArea.value = areasDisponiveis[0];
    }
  }

  window.filtrarOpcoesTurmasEditarAluno(limparTurma);
  window.atualizarPreviewCodigoAlunoEditar();
};

window.aoMudarAreaEditarAluno = function(limparTurma = true) {
  window.filtrarOpcoesTurmasEditarAluno(limparTurma);
  window.atualizarPreviewCodigoAlunoEditar();
};

window.filtrarOpcoesTurmasEditarAluno = function(limparTurma = true) {
  const selClasse = document.getElementById('meClasse');
  const selArea = document.getElementById('meArea');
  const selTurma = document.getElementById('meTurma');
  if (!selTurma) return;

  const cls = selClasse ? selClasse.value.trim().toLowerCase() : '';
  const area = selArea ? selArea.value.trim().toLowerCase() : '';

  if (limparTurma && selTurma.value) {
    const opt = selTurma.options[selTurma.selectedIndex];
    const grau = (opt ? opt.getAttribute('data-grau') : '').trim().toLowerCase();
    const tArea = (opt ? opt.getAttribute('data-area') : '').trim().toLowerCase();
    if (cls && grau && grau !== cls) {
      selTurma.value = '';
    } else if (area && area !== 'geral' && area !== 'ensino geral' && tArea && tArea !== 'geral' && tArea !== 'ensino geral' && tArea !== area && !tArea.includes(area) && !area.includes(tArea)) {
      selTurma.value = '';
    }
  }

  Array.from(selTurma.options).forEach(opt => {
    if (!opt.value) return; // Opção "Sem turma" sempre visível
    const grau = (opt.getAttribute('data-grau') || '').trim().toLowerCase();
    const tArea = (opt.getAttribute('data-area') || 'geral').trim().toLowerCase();

    let matchClasse = !cls || !grau || grau === cls;
    let matchArea = !area || area === 'geral' || area === 'ensino geral' ||
      !tArea || tArea === 'geral' || tArea === 'ensino geral' ||
      tArea === area || tArea.includes(area) || area.includes(tArea);

    if (matchClasse && matchArea) {
      opt.hidden = false;
      opt.disabled = false;
    } else {
      opt.hidden = true;
      opt.disabled = true;
    }
  });
};

window.aoMudarTurmaEditarAluno = function() {
  const selClasse = document.getElementById('meClasse');
  const selArea = document.getElementById('meArea');
  const selTurma = document.getElementById('meTurma');
  if (!selTurma || !selTurma.value) {
    window.atualizarPreviewCodigoAlunoEditar();
    return;
  }

  const opt = selTurma.options[selTurma.selectedIndex];
  if (!opt) return;

  const grau = opt.getAttribute('data-grau');
  const tArea = opt.getAttribute('data-area') || 'Geral';

  if (grau && selClasse) {
    selClasse.value = grau;
    const turmas = window._modalEditarAlunoTurmasCache || state.turmasList || [];
    const areasDaClasse = window.extrairAreasDasTurmas(turmas, grau);
    if (!areasDaClasse.some(ar => ar.toLowerCase() === tArea.toLowerCase())) {
      areasDaClasse.push(tArea);
    }
    if (selArea) {
      selArea.innerHTML = areasDaClasse.map(ar => `<option value="${ar}">${window.obterDescricaoAmigavelArea(ar)}</option>`).join('');
      selArea.value = tArea;
    }
  } else if (tArea && selArea) {
    let found = false;
    for (let i = 0; i < selArea.options.length; i++) {
      if (selArea.options[i].value.toLowerCase() === tArea.toLowerCase()) {
        selArea.selectedIndex = i;
        found = true;
        break;
      }
    }
    if (!found) {
      const newOpt = document.createElement('option');
      newOpt.value = tArea;
      newOpt.textContent = window.obterDescricaoAmigavelArea(tArea);
      selArea.appendChild(newOpt);
      selArea.value = tArea;
    }
  }
  window.atualizarPreviewCodigoAlunoEditar();
};

function atualizarDistritosEditarAluno(provincia) {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('meDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => `<option value="${d}">${d}</option>`).join('');
  }
}

async function modalTransferirAluno(id) {
  try {
    const res = await apiFetch(`/api/v1/alunos/${id}`);
    const a = res.data || (res.id ? res : null);
    if (!a) return alert('Aluno não encontrado');

    const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
    const turmas = turmasRes.data || (Array.isArray(turmasRes) ? turmasRes : []) || [];
    const turmaAtualId = a.turma_id || (typeof a.turma === 'object' ? a.turma?.id : a.turma) || '';
    const turmaAtualNome = (typeof a.turma === 'object' && a.turma?.nome) 
      ? `${a.turma.nome} (${a.turma.grau_ano || ''})` 
      : (a.turma_nome ? a.turma_nome : 'Sem Turma Atribuída');

    if (turmas.length === 0) {
      return alert('Ainda não existem turmas criadas nesta escola. Vá ao menu Turmas e use o botão "Gerar Turmas (1, 2, 3...)" primeiro.');
    }

    const opcoesTurmas = turmas.map(t => 
      `<option value="${t.id}" ${t.id === turmaAtualId ? 'disabled' : ''}>${t.grau_ano} &rarr; ${t.nome} (${t.turno || 'Diurno'})${t.id === turmaAtualId ? ' — Turma Actual' : ''}</option>`
    ).join('');

    abrirModal('Atribuição / Transferência de Turma do Aluno', `
      <form id="formModalTransferirAluno">
        <div class="alert alert-info py-2 small mb-3">
          Aluno: <strong>${a.nome} ${a.apelido || ''}</strong> (Matrícula: <code>${a.matricula}</code>)<br>
          Turma Actual: <strong>${turmaAtualNome}</strong>
        </div>
        <div class="mb-3">
          <label class="form-label small fw-semibold">Selecione a Turma de Destino</label>
          <select id="mtNovaTurma" class="form-select" required>
            <option value="">Selecione a turma...</option>
            ${opcoesTurmas}
          </select>
        </div>
        <button type="submit" class="btn btn-warning w-100"><i class="bi bi-arrow-left-right me-1"></i> Confirmar Atribuição de Turma</button>
      </form>
    `);

    document.getElementById('formModalTransferirAluno').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const novaTurmaId = document.getElementById('mtNovaTurma').value;
        const resTr = await apiFetch(`/api/v1/alunos/${id}/transferir`, {
          method: 'PUT',
          body: JSON.stringify({ novaTurmaId, turma_destino_id: novaTurmaId })
        });
        if (resTr.success) {
          alert('Aluno alocado na turma com sucesso!');
          fecharModal();
          await carregarAlunos();
          if (typeof carregarEscolaETurmas === 'function') await carregarEscolaETurmas();
        } else {
          alert(resTr.message || 'Falha ao transferir aluno');
        }
      } catch (err) {
        alert(err.message || 'Erro ao transferir aluno');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados do aluno');
  }
}

async function excluirAluno(id) {
  if (!confirm('Deseja realmente eliminar o registo deste aluno?')) return;
  try {
    const res = await apiFetch(`/api/v1/alunos/${id}`, { method: 'DELETE' });
    if (res.success) carregarAlunos();
  } catch (err) {
    alert('Erro ao eliminar aluno');
  }
}

window.atualizarTurmasModalAluno = async function(escolaId) {
  const selectTurma = document.getElementById('maTurma');
  const selectClasse = document.getElementById('maClasse');
  const selectArea = document.getElementById('maArea');
  if (!selectTurma) return;
  if (!escolaId) {
    selectTurma.innerHTML = '<option value="">Selecione primeiro a escola</option>';
    return;
  }
  try {
    const res = await apiFetch(`/api/v1/turmas?escola_id=${escolaId}`);
    const turmas = res.data || [];
    window._modalAlunoTurmasCache = turmas;
    if (turmas.length === 0) {
      selectTurma.innerHTML = '<option value="">Sem turmas nesta escola (Ingresso Pendente)</option>';
    } else {
      selectTurma.innerHTML = '<option value="">(Sem turma - Aluno Pendente de Turma)</option>' +
        turmas.map(t => `<option value="${t.id}" data-grau="${t.grau_ano || ''}" data-area="${t.area || 'Geral'}">${t.grau_ano} &rarr; ${t.nome} (${t.area || 'Geral'} - ${t.turno || 'Diurno'})</option>`).join('');
    }

    if (selectArea) {
      const cls = selectClasse ? selectClasse.value : '';
      const areas = window.extrairAreasDasTurmas(turmas, cls);
      selectArea.innerHTML = areas.map(ar => `<option value="${ar}">${window.obterDescricaoAmigavelArea(ar)}</option>`).join('');
    }
    window.atualizarPreviewCodigoAlunoNovo();
  } catch (e) {
    selectTurma.innerHTML = '<option value="">Sem turmas disponíveis</option>';
  }
};

async function modalNovoAluno() {
  let seletorEscolaHtml = '';
  let escolaSelecionadaId = localStorage.getItem('sige_selected_tenant') || (state.tenant ? state.tenant.id : '');

  if (state.user?.role === 'SUPERADMIN') {
    let escolas = [];
    try {
      const resEscolas = await apiFetch('/api/v1/saas-admin/escolas');
      escolas = resEscolas.data || [];
    } catch (e) {
      console.warn('Falha ao carregar escolas no modal de matrícula:', e);
    }

    seletorEscolaHtml = `
      <div class="col-md-12">
        <label class="form-label small fw-bold text-primary"><i class="bi bi-building me-1"></i> Escola de Destino (SuperAdmin)</label>
        <select id="maEscola" class="form-select border-primary" onchange="atualizarTurmasModalAluno(this.value)">
          <option value="">Selecione a Escola para Matricular</option>
          ${escolas.map(e => `<option value="${escapeHtml(e.id)}" ${e.id === escolaSelecionadaId ? 'selected' : ''}>${escapeHtml(e.nome)} [${escapeHtml(e.status)}]</option>`).join('')}
        </select>
      </div>
    `;
  }

  let turmas = [];
  try {
    const urlTurmas = escolaSelecionadaId 
      ? `/api/v1/turmas?escola_id=${escolaSelecionadaId}`
      : '/api/v1/escola-admin/turmas';
    const turmasRes = await apiFetch(urlTurmas);
    turmas = turmasRes.data || [];
  } catch (e) {
    console.warn('Falha ao carregar turmas no modal de matrícula:', e);
  }

  if (!turmas || turmas.length === 0) {
    turmas = state.turmasList || [];
  }
  window._modalAlunoTurmasCache = turmas;

  const classeInicial = (state.filtroAlunoClasse && state.filtroAlunoClasse !== 'TODAS' && state.filtroAlunoClasse !== 'SEM_TURMA') 
    ? state.filtroAlunoClasse 
    : '10ª Classe';

  const classesAtivas = typeof window.obterClassesCurricularesAtivas === 'function'
    ? window.obterClassesCurricularesAtivas()
    : [
        '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
        '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
      ];
  const classesSet = new Set(classesAtivas);
  turmas.forEach(t => { if (t.grau_ano) classesSet.add(t.grau_ano.trim()); });
  const classesOrdenadas = Array.from(classesSet).sort((x, y) => {
    const numX = parseInt(x.replace(/\D/g, '')) || 0;
    const numY = parseInt(y.replace(/\D/g, '')) || 0;
    return numX - numY;
  });
  const optClasses = classesOrdenadas.map(c => `<option value="${c}" ${c === classeInicial ? 'selected' : ''}>${c}</option>`).join('');
  const opcoesTurmas = turmas.map(t => `<option value="${t.id}" data-grau="${t.grau_ano || ''}" data-area="${t.area || 'Geral'}">${t.grau_ano} &rarr; ${t.nome} (${t.area || 'Geral'} - ${t.turno || 'Diurno'})</option>`).join('');
  const optProvincias = (state.geografia.provincias || []).map(p => `<option value="${p}">${p}</option>`).join('');

  const areasDasTurmas = window.extrairAreasDasTurmas(turmas, classeInicial);
  const optAreas = areasDasTurmas.map(ar => `<option value="${ar}">${window.obterDescricaoAmigavelArea(ar)}</option>`).join('');
  const anoDefault = state.filtroAlunoAno && state.filtroAlunoAno !== 'TODOS' ? state.filtroAlunoAno : (state.tenant?.ano_letivo_ativo || new Date().getFullYear());
  const previewInicial = window.gerarPreviewCodigoAluno(null, classeInicial, 'Turma 1', anoDefault, areasDasTurmas[0] || 'Geral');

  abrirModal('Matricular Novo Aluno', `
    <form id="formModalAluno">
      <div class="alert alert-primary border-primary bg-primary bg-opacity-10 py-2 px-3 mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
        <div>
          <small class="fw-bold text-primary d-block"><i class="bi bi-upc-scan me-1"></i> Código Oficial do Aluno (Gerado Automaticamente):</small>
          <small class="text-muted" style="font-size: 0.72rem;">Associa: Código da Escola + Classe + Turma + Ano + Área/Secção</small>
        </div>
        <code class="fs-6 fw-bold text-primary bg-white border border-primary px-3 py-1 rounded" id="maPreviewCodAluno">${previewInicial}</code>
      </div>
      <div class="row g-3">
        ${seletorEscolaHtml}
        <div class="col-md-8">
          <label class="form-label small fw-semibold">Nome Completo</label>
          <input type="text" id="maNome" class="form-control" required placeholder="Nome próprio e do meio">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Apelido</label>
          <input type="text" id="maApelido" class="form-control" placeholder="Sobrenome / Apelido">
        </div>

        <div class="col-md-3">
          <label class="form-label small fw-bold text-primary"><i class="bi bi-calendar-event me-1"></i> Ano de Ingresso</label>
          <input type="number" id="maAnoIngresso" class="form-control border-primary fw-semibold" value="${anoDefault}" min="2000" max="2099" required title="Ano de Ingresso do Aluno" oninput="atualizarPreviewCodigoAlunoNovo()">
          <small class="text-muted" style="font-size: 0.72rem;">Ano de admissão / lectivo activo.</small>
        </div>
        <div class="col-md-3">
          <label class="form-label small fw-bold text-primary"><i class="bi bi-mortarboard-fill me-1"></i> Classe de Ingresso</label>
          <select id="maClasse" class="form-select border-primary fw-semibold" required onchange="aoMudarClasseNovoAluno()">
            <option value="">Selecione a Classe...</option>
            ${optClasses}
          </select>
          <small class="text-muted" style="font-size: 0.72rem;">Essencial para alocação e formação automática.</small>
        </div>
        <div class="col-md-3">
          <label class="form-label small fw-bold text-primary"><i class="bi bi-compass-fill me-1"></i> Secção / Área de Estudo</label>
          <select id="maArea" class="form-select border-primary fw-semibold" onchange="aoMudarAreaNovoAluno()">
            ${optAreas}
          </select>
          <small class="text-muted" style="font-size: 0.72rem;">Obtida automaticamente das turmas cadastradas.</small>
        </div>
        <div class="col-md-3">
          <label class="form-label small fw-bold text-primary"><i class="bi bi-diagram-3-fill me-1"></i> Turma de Ingresso (Opcional)</label>
          <select id="maTurma" class="form-select border-primary fw-semibold" onchange="aoMudarTurmaNovoAluno()">
            <option value="">(Sem turma - Aluno Pendente de Turma)</option>
            ${opcoesTurmas}
          </select>
          <small class="text-muted" style="font-size: 0.72rem;">Pode deixar pendente e formar automaticamente.</small>
        </div>

        <div class="col-md-4">
          <label class="form-label small fw-semibold">Data de Nascimento</label>
          <input type="date" id="maNasc" class="form-control" required>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Género</label>
          <select id="maGenero" class="form-select">
            <option value="M">Masculino</option>
            <option value="F">Feminino</option>
          </select>
        </div>

        <div class="col-md-4">
          <label class="form-label small fw-semibold">Tipo de Documento</label>
          <select id="maTipoDoc" class="form-select">
            <option value="BI">Bilhete de Identidade (BI)</option>
            <option value="DIRE">DIRE</option>
            <option value="PASSAPORTE">Passaporte</option>
            <option value="CEDULA">Cédula Pessoal</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Número do Documento</label>
          <input type="text" id="maNumDoc" class="form-control" placeholder="Ex: 110100234567M">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">NUIT (Opcional)</label>
          <input type="text" id="maNUIT" class="form-control" placeholder="Ex: 109876543 (máx. 9 dígitos)" maxlength="9" inputmode="numeric" pattern="[0-9]{1,9}">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Província de Naturalidade / Residência</label>
          <select id="maProvincia" class="form-select" onchange="atualizarDistritosAluno(this.value)">
            <option value="">Selecione a Província</option>
            ${optProvincias}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Distrito</label>
          <select id="maDistrito" class="form-select">
            <option value="">Selecione primeiro a província</option>
          </select>
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Nome do Pai (Opcional)</label>
          <input type="text" id="maPai" class="form-control" placeholder="Nome completo do pai">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Nome da Mãe (Opcional)</label>
          <input type="text" id="maMae" class="form-control" placeholder="Nome completo da mãe">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Encarregado de Educação / Tutor</label>
          <input type="text" id="maResp" class="form-control" placeholder="Nome do encarregado de educação">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Telefone de Contacto (+258 Padrão)</label>
          <input type="tel" id="maTel" class="form-control" value="+258 " placeholder="+258 ..." inputmode="tel">
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4"><i class="bi bi-person-plus-fill me-1"></i> Confirmar Matrícula Oficial</button>
    </form>
  `);

  document.getElementById('formModalAluno').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const escolaSelect = document.getElementById('maEscola');
      const escola_id = escolaSelect ? escolaSelect.value : (localStorage.getItem('sige_selected_tenant') || undefined);
      if (state.user?.role === 'SUPERADMIN' && !escola_id) {
        return alert('Por favor, seleccione a escola onde o aluno será matriculado.');
      }

      const areaVal = document.getElementById('maArea')?.value || 'Geral';
      const body = {
        escola_id: escola_id || undefined,
        nome: document.getElementById('maNome').value,
        apelido: document.getElementById('maApelido').value || undefined,
        ano_ingresso: document.getElementById('maAnoIngresso')?.value || String(state.tenant?.ano_letivo_ativo || new Date().getFullYear()),
        classe: document.getElementById('maClasse')?.value || undefined,
        area: areaVal,
        grupo: areaVal,
        data_nascimento: document.getElementById('maNasc').value,
        genero: document.getElementById('maGenero').value,
        turma_id: document.getElementById('maTurma').value || null,
        tipo_documento: document.getElementById('maTipoDoc').value,
        numero_documento: document.getElementById('maNumDoc').value || undefined,
        nuit: document.getElementById('maNUIT').value || undefined,
        provincia: document.getElementById('maProvincia').value || undefined,
        distrito: document.getElementById('maDistrito').value || undefined,
        pai: document.getElementById('maPai').value || undefined,
        mae: document.getElementById('maMae').value || undefined,
        nome_responsavel: document.getElementById('maResp').value || undefined,
        contato_responsavel: document.getElementById('maTel').value || undefined
      };
      const res = await apiFetch('/api/v1/alunos', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success) {
        const codAluno = res.data?.matricula || '';
        alert(`Aluno matriculado com sucesso!\n\nCódigo Oficial do Aluno: ${codAluno}`);
        fecharModal();
        carregarAlunos();
      }
    } catch (err) {
      alert(err.message || 'Erro ao matricular aluno');
    }
  });
}

window.aoMudarClasseNovoAluno = function(limparTurma = true) {
  const selClasse = document.getElementById('maClasse');
  const selTurma = document.getElementById('maTurma');
  const selArea = document.getElementById('maArea');
  if (!selClasse || !selTurma) return;
  const cls = selClasse.value;

  if (selArea) {
    const turmas = window._modalAlunoTurmasCache || state.turmasList || [];
    const areasDisponiveis = window.extrairAreasDasTurmas(turmas, cls);
    const valAtual = selArea.value;

    selArea.innerHTML = areasDisponiveis.map(ar => 
      `<option value="${ar}">${window.obterDescricaoAmigavelArea(ar)}</option>`
    ).join('');

    if (areasDisponiveis.some(ar => ar.toLowerCase() === valAtual.toLowerCase())) {
      selArea.value = areasDisponiveis.find(ar => ar.toLowerCase() === valAtual.toLowerCase());
    } else if (areasDisponiveis.length > 0) {
      selArea.value = areasDisponiveis[0];
    }
  }

  window.filtrarOpcoesTurmasNovoAluno(limparTurma);
  window.atualizarPreviewCodigoAlunoNovo();
};

window.aoMudarAreaNovoAluno = function(limparTurma = true) {
  window.filtrarOpcoesTurmasNovoAluno(limparTurma);
  window.atualizarPreviewCodigoAlunoNovo();
};

window.filtrarOpcoesTurmasNovoAluno = function(limparTurma = true) {
  const selClasse = document.getElementById('maClasse');
  const selArea = document.getElementById('maArea');
  const selTurma = document.getElementById('maTurma');
  if (!selTurma) return;

  const cls = selClasse ? selClasse.value.trim().toLowerCase() : '';
  const area = selArea ? selArea.value.trim().toLowerCase() : '';

  if (limparTurma && selTurma.value) {
    const opt = selTurma.options[selTurma.selectedIndex];
    const grau = (opt ? opt.getAttribute('data-grau') : '').trim().toLowerCase();
    const tArea = (opt ? opt.getAttribute('data-area') : '').trim().toLowerCase();
    if (cls && grau && grau !== cls) {
      selTurma.value = '';
    } else if (area && area !== 'geral' && area !== 'ensino geral' && tArea && tArea !== 'geral' && tArea !== 'ensino geral' && tArea !== area && !tArea.includes(area) && !area.includes(tArea)) {
      selTurma.value = '';
    }
  }

  Array.from(selTurma.options).forEach(opt => {
    if (!opt.value) return; // Opção "Sem turma"
    const grau = (opt.getAttribute('data-grau') || '').trim().toLowerCase();
    const tArea = (opt.getAttribute('data-area') || 'geral').trim().toLowerCase();

    let matchClasse = !cls || !grau || grau === cls;
    let matchArea = !area || area === 'geral' || area === 'ensino geral' ||
      !tArea || tArea === 'geral' || tArea === 'ensino geral' ||
      tArea === area || tArea.includes(area) || area.includes(tArea);

    if (matchClasse && matchArea) {
      opt.hidden = false;
      opt.disabled = false;
    } else {
      opt.hidden = true;
      opt.disabled = true;
    }
  });
};

window.aoMudarTurmaNovoAluno = function() {
  const selClasse = document.getElementById('maClasse');
  const selArea = document.getElementById('maArea');
  const selTurma = document.getElementById('maTurma');
  if (!selTurma || !selTurma.value) return;

  const opt = selTurma.options[selTurma.selectedIndex];
  if (!opt) return;

  const grau = opt.getAttribute('data-grau');
  const tArea = opt.getAttribute('data-area') || 'Geral';

  if (grau && selClasse) {
    selClasse.value = grau;
    const turmas = window._modalAlunoTurmasCache || state.turmasList || [];
    const areasDaClasse = window.extrairAreasDasTurmas(turmas, grau);
    if (!areasDaClasse.some(ar => ar.toLowerCase() === tArea.toLowerCase())) {
      areasDaClasse.push(tArea);
    }
    if (selArea) {
      selArea.innerHTML = areasDaClasse.map(ar => `<option value="${ar}">${window.obterDescricaoAmigavelArea(ar)}</option>`).join('');
      selArea.value = tArea;
    }
  } else if (tArea && selArea) {
    let found = false;
    for (let i = 0; i < selArea.options.length; i++) {
      if (selArea.options[i].value.toLowerCase() === tArea.toLowerCase()) {
        selArea.selectedIndex = i;
        found = true;
        break;
      }
    }
    if (!found) {
      const newOpt = document.createElement('option');
      newOpt.value = tArea;
      newOpt.textContent = window.obterDescricaoAmigavelArea(tArea);
      selArea.appendChild(newOpt);
      selArea.value = tArea;
    }
  }
};

function atualizarDistritosAluno(provincia) {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById('maDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => `<option value="${d}">${d}</option>`).join('');
  }
}

// ==================== 5. PROFESSORES ====================
async function carregarProfessores() {
  try {
    const [resProfs, resStats, resTurmas, resDisc] = await Promise.all([
      apiFetch('/api/v1/professores'),
      apiFetch('/api/v1/professores/stats'),
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/disciplinas')
    ]);

    if (resTurmas && resTurmas.success) {
      state.todasTurmas = resTurmas.data || [];
    }
    if (resDisc && resDisc.success) {
      state.todasDisciplinas = resDisc.data || [];
    }

    if (resStats.success) {
      const s = resStats.data;
      document.getElementById('profTotalCard').textContent = s.totalProfessores ?? 0;
      const ratio = (s.proporcaoAlunoProfessor !== undefined && s.proporcaoAlunoProfessor !== null) 
        ? s.proporcaoAlunoProfessor 
        : (s.totalProfessores > 0 ? Math.round(((state.todosAlunos && state.todosAlunos.length) || 0) / s.totalProfessores) : 0);
      document.getElementById('profRatioCard').textContent = `${ratio} : 1`;
      document.getElementById('profAulasMesCard').textContent = s.totalAulasMes ?? (s.totalAlocacoes ? s.totalAlocacoes * 16 : 0);
    }

    state.todosProfessores = resProfs.success ? (resProfs.data || []) : [];
    renderizarBotoesClassesProfessores();
  } catch (err) {
    console.error('Erro ao carregar professores:', err);
  }
}

function obterClassesDocentes() {
  const classesSet = new Set();
  (state.todasTurmas || []).forEach(t => {
    if (t.grau_ano) classesSet.add(t.grau_ano.trim());
  });
  (state.todosProfessores || []).forEach(p => {
    (p.alocacoes || []).forEach(a => {
      const g = a.turma_grau || a.turma?.grau_ano || a.disciplina?.classe;
      if (g) classesSet.add(g.trim());
    });
  });
  (state.todasDisciplinas || []).forEach(d => {
    if (d.classe) classesSet.add(d.classe.trim());
  });
  (state.todosAlunos || []).forEach(a => {
    if (a.classe) classesSet.add(a.classe.trim());
    if (a.turma_grau) classesSet.add(a.turma_grau.trim());
  });

  const ordenadas = Array.from(classesSet).sort((a, b) => {
    const numA = parseInt(a.replace(/\D/g, '')) || 0;
    const numB = parseInt(b.replace(/\D/g, '')) || 0;
    return numA - numB;
  });

  return ordenadas;
}

function calcularMetricasCargaProfessor(p) {
  if (!p) return { totalAlocada: 0, maxNormal: 20, horasNormais: 0, horasExtras: 0, porClasse: {} };

  const maxNormal = Number(p.carga_horaria_semanal) || 20;
  let totalAlocada = 0;
  const porClasse = {};

  (p.alocacoes || []).forEach(a => {
    let ch = Number(a.disciplina_carga_horaria || a.disciplina?.carga_horaria);
    if (!ch || isNaN(ch)) {
      const discId = a.disciplina?.id || a.disciplina;
      const foundD = (state.todasDisciplinas || []).find(d => String(d.id) === String(discId));
      ch = Number(foundD?.carga_horaria) || 5;
    }
    totalAlocada += ch;

    const classe = (a.turma_grau || a.turma?.grau_ano || a.disciplina?.classe || 'Geral').trim();
    if (!porClasse[classe]) {
      const maxClasse = (p.carga_maxima_por_classe && p.carga_maxima_por_classe[classe])
        ? Number(p.carga_maxima_por_classe[classe])
        : maxNormal;
      porClasse[classe] = {
        classe,
        cargaAlocada: 0,
        cargaMaxima: maxClasse,
        turmas: []
      };
    }
    porClasse[classe].cargaAlocada += ch;
    porClasse[classe].turmas.push({
      alocacaoId: a.id,
      turmaNome: a.turma_nome || a.turma?.nome || 'Turma',
      turmaArea: a.turma_area || a.turma?.area || 'Geral',
      disciplinaNome: a.disciplina_nome || a.disciplina?.nome || 'Disciplina',
      cargaHoraria: ch
    });
  });

  Object.values(porClasse).forEach(cData => {
    cData.horasNormais = Math.min(cData.cargaAlocada, cData.cargaMaxima);
    cData.horasExtras = Math.max(0, cData.cargaAlocada - cData.cargaMaxima);
  });

  const horasNormais = Math.min(totalAlocada, maxNormal);
  const horasExtras = Math.max(0, totalAlocada - maxNormal);

  return {
    totalAlocada,
    maxNormal,
    horasNormais,
    horasExtras,
    porClasse
  };
}

function professorPertenceClasse(p, classe) {
  if (!p || !p.alocacoes || p.alocacoes.length === 0) return false;
  return p.alocacoes.some(a => {
    const g = a.turma_grau || a.turma?.grau_ano || a.disciplina?.classe;
    return g && normalizarClasse(g) === normalizarClasse(classe);
  });
}

function renderizarBotoesClassesProfessores() {
  const selectClasse = document.getElementById('selectFiltroProfessorClasse');
  const profs = state.todosProfessores || [];
  const classes = obterClassesDocentes();
  const totalGeral = profs.length;
  const semClasseCount = profs.filter(p => !p.alocacoes || p.alocacoes.length === 0).length;

  if (!state.filtroProfessorClasse) {
    state.filtroProfessorClasse = 'TODAS';
  }

  const contagemEl = document.getElementById('contagemClassesProfessores');
  if (contagemEl) {
    contagemEl.textContent = `${classes.length} classe(s)`;
  }

  if (selectClasse) {
    let htmlOptions = `<option value="TODAS">Todos os Docentes (${totalGeral})</option>`;
    if (semClasseCount > 0) {
      htmlOptions += `<option value="SEM_CLASSE">⚠️ Sem Classe Alocada (${semClasseCount})</option>`;
    }
    classes.forEach(cls => {
      const totalNaClasse = profs.filter(p => professorPertenceClasse(p, cls)).length;
      htmlOptions += `<option value="${cls}">${cls} (${totalNaClasse} docentes)</option>`;
    });
    selectClasse.innerHTML = htmlOptions;
    selectClasse.value = state.filtroProfessorClasse;
  }

  selecionarClasseProfessores(state.filtroProfessorClasse, false);
}

function selecionarClasseProfessores(classe, syncSelect = true) {
  state.filtroProfessorClasse = classe;

  const selectClasse = document.getElementById('selectFiltroProfessorClasse');
  if (selectClasse && syncSelect && selectClasse.value !== classe) {
    selectClasse.value = classe;
  }

  const profs = state.todosProfessores || [];
  let filtrados = profs;
  let labelTexto = 'Todos os Professores';

  if (classe === 'SEM_CLASSE') {
    labelTexto = 'Docentes Sem Turma / Classe Atribuída';
    filtrados = profs.filter(p => !p.alocacoes || p.alocacoes.length === 0);
  } else if (classe !== 'TODAS') {
    labelTexto = `Docentes da ${classe}`;
    filtrados = profs.filter(p => professorPertenceClasse(p, classe));
  }

  const badge = document.getElementById('badgeCaminhoProfessores');
  if (badge) {
    badge.innerHTML = `<i class="bi bi-mortarboard me-1"></i> ${labelTexto} (${filtrados.length} Docentes)`;
  }

  const contagem = document.getElementById('contagemProfessoresExibidos');
  if (contagem) {
    contagem.textContent = `${filtrados.length} docente(s) listado(s)`;
  }

  state.professoresFiltradosAtuais = filtrados;
  renderizarTabelaProfessores(filtrados);
}

function filtrarProfessoresTabela() {
  const termo = (document.getElementById('pesquisaProfessores')?.value || '').toLowerCase().trim();
  let base = state.professoresFiltradosAtuais || state.todosProfessores || [];

  if (termo) {
    let filtrados = base.filter(p => 
      (p.codigo || '').toLowerCase().includes(termo) ||
      (p.nome || '').toLowerCase().includes(termo) ||
      (p.apelido || '').toLowerCase().includes(termo) ||
      (p.email || '').toLowerCase().includes(termo) ||
      (p.especialidade || '').toLowerCase().includes(termo) ||
      (p.carreira || '').toLowerCase().includes(termo) ||
      (p.alocacoes || []).some(a => 
        (a.turma_nome || '').toLowerCase().includes(termo) ||
        (a.turma_grau || '').toLowerCase().includes(termo) ||
        (a.disciplina_nome || '').toLowerCase().includes(termo)
      )
    );

    if (filtrados.length === 0) {
      filtrados = (state.todosProfessores || []).filter(p => 
        (p.codigo || '').toLowerCase().includes(termo) ||
        (p.nome || '').toLowerCase().includes(termo) ||
        (p.apelido || '').toLowerCase().includes(termo) ||
        (p.email || '').toLowerCase().includes(termo) ||
        (p.especialidade || '').toLowerCase().includes(termo)
      );
    }

    renderizarTabelaProfessores(filtrados);
    const contagem = document.getElementById('contagemProfessoresExibidos');
    if (contagem) contagem.textContent = `${filtrados.length} docente(s) encontrado(s) para "${termo}"`;
  } else {
    renderizarTabelaProfessores(base);
    const contagem = document.getElementById('contagemProfessoresExibidos');
    if (contagem) contagem.textContent = `${base.length} docente(s) listado(s)`;
  }
}

function limparFiltrosProfessores() {
  state.filtroProfessorClasse = 'TODAS';
  const inp = document.getElementById('pesquisaProfessores');
  if (inp) inp.value = '';
  const sel = document.getElementById('selectFiltroProfessorClasse');
  if (sel) sel.value = 'TODAS';
  selecionarClasseProfessores('TODAS');
}

function renderizarTabelaProfessores(profs) {
  const tbody = document.getElementById('tabelaProfessores');
  if (!tbody) return;

  if (!profs || profs.length === 0) {
    const semClasseCount = (state.todosProfessores || []).filter(p => !p.alocacoes || p.alocacoes.length === 0).length;
    let dicaExtra = '';
    if (semClasseCount > 0 && state.filtroProfessorClasse !== 'SEM_CLASSE' && state.filtroProfessorClasse !== 'TODAS') {
      dicaExtra = `<div class="mt-2"><span class="badge bg-warning text-dark p-2" role="button" onclick="selecionarClasseProfessores('SEM_CLASSE')"><i class="bi bi-info-circle me-1"></i> Esta escola possui ${semClasseCount} docente(s) sem turma/classe atribuída. Clique aqui para ver e atribuir turmas.</span></div>`;
    }
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted"><i class="bi bi-info-circle me-1"></i> Nenhum docente encontrado para a selecção actual.${dicaExtra}</td></tr>`;
    return;
  }

  const todasTurmas = state.todasTurmas || [];

  tbody.innerHTML = profs.map(p => {
    const nomeCompleto = `${p.nome || ''} ${p.apelido || ''}`.trim();
    const turmasDT = todasTurmas.filter(t => String(t.director_turma_id || t.director_turma) === String(p.id));
    const turmasDC = todasTurmas.filter(t => String(t.director_classe_id || t.director_classe) === String(p.id));

    let cargosBadges = '';
    turmasDT.forEach(t => {
      if (t.homologado_dt && t.codigo_director_turma) {
        cargosBadges += `<span class="badge bg-success bg-opacity-10 text-success border border-success font-monospace me-1 mt-1" style="font-size:0.7rem;" title="Director de Turma Homologado (${t.nome})"><i class="bi bi-patch-check-fill me-1"></i>${t.codigo_director_turma}</span>`;
      } else {
        cargosBadges += `<span class="badge bg-warning text-dark font-monospace me-1 mt-1" style="font-size:0.7rem;" title="Indicado DT (${t.nome}) - Pendente Homologação GD">DT Pendente (${t.nome})</span>`;
      }
    });
    const dcCodigosVistos = new Set();
    turmasDC.forEach(t => {
      const chave = t.codigo_director_classe || t.grau_ano;
      if (dcCodigosVistos.has(chave)) return;
      dcCodigosVistos.add(chave);
      if (t.homologado_dc && t.codigo_director_classe) {
        cargosBadges += `<span class="badge bg-info bg-opacity-10 text-dark border border-info font-monospace me-1 mt-1" style="font-size:0.7rem;" title="Director de Classe Homologado (${t.grau_ano})"><i class="bi bi-patch-check-fill text-primary me-1"></i>${t.codigo_director_classe}</span>`;
      } else {
        cargosBadges += `<span class="badge bg-warning text-dark font-monospace me-1 mt-1" style="font-size:0.7rem;" title="Indicado DC (${t.grau_ano}) - Pendente Homologação GD">DC Pendente (${t.grau_ano})</span>`;
      }
    });

    const alocacoesHtml = (p.alocacoes && p.alocacoes.length > 0)
      ? p.alocacoes.map(a => {
          const classeTurma = a.turma_grau || a.turma?.grau_ano || '';
          const nomeTurma = a.turma_nome || a.turma?.nome || 'Turma';
          const nomeDisc = a.disciplina_nome || a.disciplina?.nome || 'Disciplina';
          return `
            <span class="badge border bg-light text-dark d-inline-flex align-items-center gap-1 mb-1 me-1 p-1 px-2" style="font-size: 0.8rem;" title="${classeTurma} &rarr; ${nomeTurma}: ${nomeDisc}">
              <span class="badge bg-primary bg-opacity-25 text-primary border me-1" style="font-size: 0.7rem;">${classeTurma || 'Classe'}</span>
              <strong>${nomeTurma}</strong> <span class="text-muted">(${nomeDisc})</span>
              <a href="javascript:void(0)" onclick="modalEditarAlocacao('${a.id}', '${p.id}')" class="text-primary ms-1" title="Editar Turma/Disciplina Alocada"><i class="bi bi-pencil-fill" style="font-size: 10px;"></i></a>
              <a href="javascript:void(0)" onclick="eliminarAlocacao('${a.id}', '${p.id}')" class="text-danger" title="Eliminar Alocação"><i class="bi bi-x-circle-fill" style="font-size: 11px;"></i></a>
            </span>
          `;
        }).join('')
      : '<span class="badge bg-warning bg-opacity-25 text-dark border border-warning">Nenhuma turma alocada</span>';

    const metricas = calcularMetricasCargaProfessor(p);
    let cargaBadgeHtml = '';
    if (metricas.totalAlocada === 0) {
      cargaBadgeHtml = `
        <span class="badge bg-light text-muted border">0h / semana</span>
        <div class="small text-muted" style="font-size: 0.72rem;">Máx: ${metricas.maxNormal}h normal</div>
      `;
    } else if (metricas.horasExtras === 0) {
      cargaBadgeHtml = `
        <span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25 fw-semibold" style="font-size: 0.85rem;">
          <i class="bi bi-check-circle-fill me-1"></i>${metricas.totalAlocada}h / semana
        </span>
        <div class="small text-muted mt-1" style="font-size: 0.72rem;">100% Normal (Máx: ${metricas.maxNormal}h)</div>
      `;
    } else {
      cargaBadgeHtml = `
        <span class="badge bg-warning text-dark border border-warning fw-bold" style="font-size: 0.85rem;" title="Transbordo de Carga Máxima">
          <i class="bi bi-exclamation-triangle-fill me-1 text-danger"></i>${metricas.totalAlocada}h / semana
        </span>
        <div class="d-flex flex-wrap gap-1 mt-1">
          <span class="badge bg-success bg-opacity-75" style="font-size: 0.7rem;" title="Carga horária contratual normal">${metricas.horasNormais}h Normal</span>
          <span class="badge bg-danger text-white fw-bold" style="font-size: 0.7rem;" title="Horas extras semanais suplementares">+${metricas.horasExtras}h Extras</span>
        </div>
      `;
    }

    return `
      <tr>
        <td>
          <div class="d-flex align-items-center gap-2">
            <div class="rounded-circle bg-primary bg-opacity-10 text-primary fw-bold d-flex align-items-center justify-content-center" style="width: 36px; height: 36px; font-size: 0.85rem;">
              ${(p.nome || 'P').charAt(0).toUpperCase()}
            </div>
            <div>
              <div class="d-flex align-items-center gap-1 flex-wrap">
                <strong class="text-primary">${nomeCompleto}</strong>
                <span class="badge bg-dark text-white font-monospace" style="font-size: 0.72rem;" title="Código Fixo Oficial do Professor (imutável entre turmas/classes)">${p.codigo || 'PR-FIXO'}</span>
              </div>
              <div class="small text-muted">${p.especialidade || 'Área Geral'}</div>
              ${cargosBadges ? `<div class="d-flex flex-wrap">${cargosBadges}</div>` : ''}
            </div>
          </div>
        </td>
        <td>
          <small class="d-block"><i class="bi bi-envelope me-1 text-muted"></i>${p.email}</small>
          <small class="text-muted"><i class="bi bi-telephone me-1 text-muted"></i>${p.telefone || '-'}</small>
        </td>
        <td>
          <span class="badge bg-light text-dark border fw-semibold">${p.carreira || 'Licenciado'}</span>
          <div class="small text-muted mt-1">${p.ativo !== false ? '<span class="text-success"><i class="bi bi-check-circle-fill me-1"></i>Activo</span>' : '<span class="text-secondary">Inactivo</span>'}</div>
        </td>
        <td><small>${p.distrito || '-'}<br><span class="text-muted">${p.provincia || '-'}</span></small></td>
        <td>${cargaBadgeHtml}</td>
        <td>
          <div class="d-flex flex-wrap align-items-center">
            ${alocacoesHtml}
            <button class="btn btn-link btn-sm p-0 ms-1 text-decoration-none" onclick="modalAlocarProfessor('${p.id}')" title="Alocar nova turma ou classe a este docente">
              <i class="bi bi-plus-circle-fill text-success" style="font-size: 15px;"></i>
            </button>
          </div>
        </td>
        <td class="text-end">
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-primary" onclick="modalEditarProfessor('${p.id}')" title="Editar Dados Cadastrais e Carreira">
              <i class="bi bi-pencil-square me-1"></i>Editar
            </button>
            <button class="btn btn-outline-warning text-dark" onclick="modalTransferirProfessor('${p.id}')" title="Transferir ou Atribuir Nova Classe a este Docente">
              <i class="bi bi-arrow-left-right me-1"></i>Transferir Classe
            </button>
            <button class="btn btn-outline-danger" onclick="excluirProfessor('${p.id}')" title="Eliminar Docente do Quadro">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function modalNovoProfessor() {
  const optCarreiras = (state.geografia.carreiras || ['DN1', 'DN2', 'DN3', 'DN4', 'N1', 'N2', 'N3', 'N4', 'Licenciado', 'Mestre', 'Especialista de Educação']).map(c => `<option value="${c}">${c}</option>`).join('');
  const optProvincias = (state.geografia.provincias || []).map(p => `<option value="${p}">${p}</option>`).join('');

  // Classes disponíveis
  const classesDisponiveis = obterClassesDocentes();
  const checkboxesClassesHtml = classesDisponiveis.map(cls => `
    <div class="form-check form-check-inline">
      <input class="form-check-input check-classe-novo-prof" type="checkbox" value="${cls}" id="chkCls_${cls.replace(/\s+/g, '')}" onchange="aoMudarClassesModalNovoProf()">
      <label class="form-check-label small fw-semibold" for="chkCls_${cls.replace(/\s+/g, '')}">${cls}</label>
    </div>
  `).join('');

  // Disciplinas disponíveis
  const disciplinas = state.todasDisciplinas || [];
  const optDisciplinas = disciplinas.length > 0 
    ? disciplinas.map(d => `<option value="${d.id}">${d.nome} ${d.classe ? `(${d.classe})` : ''}</option>`).join('')
    : '<option value="">Nenhuma disciplina cadastrada</option>';

  const codEsc = state.escolaInfo?.codigo_escola || state.user?.escola?.codigo_escola || '0101S0001';
  const proxSeq = String((state.todosProfessores?.length || 0) + 1).padStart(3, '0');

  abrirModal('Cadastrar Docente & Atribuição de Classes', `
    <form id="formModalProf">
      <div class="row g-3">
        <div class="col-12">
          <div class="p-2 px-3 rounded bg-dark bg-opacity-10 border d-flex justify-content-between align-items-center">
            <span class="small fw-semibold"><i class="bi bi-lock-fill me-1 text-primary"></i>Código Fixo Oficial do Professor (gerado automaticamente e imutável):</span>
            <span class="badge bg-dark text-white font-monospace px-3 py-2">PR${codEsc}.${proxSeq}</span>
          </div>
        </div>
        <div class="col-md-7">
          <label class="form-label small fw-semibold">Nome Completo</label>
          <input type="text" id="mpNome" class="form-control" required placeholder="Prof. Nome Próprio">
        </div>
        <div class="col-md-5">
          <label class="form-label small fw-semibold">Apelido</label>
          <input type="text" id="mpApelido" class="form-control" placeholder="Apelido do docente">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">E-mail Institucional</label>
          <input type="email" id="mpEmail" class="form-control" required placeholder="professor@escola.edu.mz">
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Telefone (+258 Padrão)</label>
          <input type="text" id="mpTel" class="form-control" value="+258 ">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Carreira Docente (Quadro Oficial)</label>
          <select id="mpCarreira" class="form-select">${optCarreiras}</select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Especialidade / Área de Formação</label>
          <input type="text" id="mpEsp" class="form-control" placeholder="Ex: Matemática e Física">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold">Província</label>
          <select id="mpProvincia" class="form-select" onchange="atualizarDistritosProfessor(this.value)">
            <option value="">Selecione a Província</option>
            ${optProvincias}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Distrito</label>
          <select id="mpDistrito" class="form-select">
            <option value="">Selecione primeiro a província</option>
          </select>
        </div>

        <div class="col-md-12">
          <label class="form-label small fw-semibold">Carga Horária Semanal (Horas)</label>
          <input type="number" id="mpCarga" class="form-control" value="20" required min="1" max="60">
        </div>

        <!-- Secção de Atribuição Sequencial: Classe(s) -> Turma(s) -->
        <div class="col-12 mt-3">
          <div class="p-3 bg-light rounded border border-primary border-opacity-25">
            <h6 class="fw-bold text-primary mb-1"><i class="bi bi-mortarboard-fill me-1"></i> Atribuição Sequencial: Classe(s) & Turma(s)</h6>
            <p class="text-muted small mb-2">Pode seleccionar <strong>1 ou 2 classes</strong> para atribuir ao professor. Em seguida, marque as turmas correspondentes:</p>
            
            <div class="mb-3">
              <label class="form-label small fw-bold text-dark mb-1">Passo 1: Seleccione a(s) Classe(s) do Docente:</label>
              <div class="p-2 bg-white rounded border">
                ${checkboxesClassesHtml}
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label small fw-bold text-dark mb-1">Passo 2: Turmas Disponíveis nas Classes Seleccionadas:</label>
              <div id="containerTurmasNovoProf" class="p-2 bg-white rounded border" style="min-height: 50px;">
                <span class="text-muted small"><i class="bi bi-info-circle me-1"></i> Marque uma ou duas classes no Passo 1 para exibir as turmas disponíveis para alocação.</span>
              </div>
            </div>

            <div>
              <label class="form-label small fw-bold text-dark mb-1">Passo 3: Disciplina Curricular a Ministrar:</label>
              <select id="mpDisciplinaInicial" class="form-select">
                <option value="">Selecione a Disciplina Curricular...</option>
                ${optDisciplinas}
              </select>
            </div>
          </div>
        </div>
      </div>
      <div class="d-flex justify-content-end gap-2 mt-4">
        <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
        <button type="submit" class="btn btn-primary btn-sm px-4">Cadastrar Docente & Alocar</button>
      </div>
    </form>
  `);

  window.aoMudarClassesModalNovoProf = function() {
    const checks = document.querySelectorAll('.check-classe-novo-prof:checked');
    const classesSelecionadas = Array.from(checks).map(c => c.value);
    const containerTurmas = document.getElementById('containerTurmasNovoProf');
    if (!containerTurmas) return;

    if (classesSelecionadas.length === 0) {
      containerTurmas.innerHTML = `<span class="text-muted small"><i class="bi bi-info-circle me-1"></i> Marque uma ou duas classes no Passo 1 para exibir as turmas disponíveis para alocação.</span>`;
      return;
    }

    const turmas = (state.todasTurmas || []).filter(t => 
      classesSelecionadas.some(cls => normalizarClasse(t.grau_ano) === normalizarClasse(cls))
    );

    if (turmas.length === 0) {
      containerTurmas.innerHTML = `<span class="text-warning small"><i class="bi bi-exclamation-triangle me-1"></i> Nenhuma turma cadastrada para as classes seleccionadas (${classesSelecionadas.join(', ')}). Pode cadastrar o docente e criar turmas posteriormente.</span>`;
      return;
    }

    let turmasHtml = `<div class="d-flex flex-wrap gap-3">`;
    classesSelecionadas.forEach(cls => {
      const turmasDestaClasse = turmas.filter(t => normalizarClasse(t.grau_ano) === normalizarClasse(cls));
      turmasHtml += `<div class="p-2 border rounded bg-light" style="flex: 1; min-width: 200px;">
        <strong class="d-block text-primary small mb-1 border-bottom pb-1"><i class="bi bi-mortarboard me-1"></i>${cls}:</strong>`;
      if (turmasDestaClasse.length === 0) {
        turmasHtml += `<span class="text-muted small">Sem turmas</span>`;
      } else {
        turmasDestaClasse.forEach(t => {
          turmasHtml += `
            <div class="form-check">
              <input class="form-check-input check-turma-alocar-prof" type="checkbox" value="${t.id}" id="chkTrm_${t.id}">
              <label class="form-check-label small" for="chkTrm_${t.id}">
                <strong>${t.nome}</strong> ${t.area ? `<span class="text-muted">(${t.area})</span>` : ''}
              </label>
            </div>
          `;
        });
      }
      turmasHtml += `</div>`;
    });
    turmasHtml += `</div>`;
    containerTurmas.innerHTML = turmasHtml;
  };

  document.getElementById('formModalProf').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const body = {
        nome: document.getElementById('mpNome').value,
        apelido: document.getElementById('mpApelido').value || undefined,
        email: document.getElementById('mpEmail').value,
        telefone: document.getElementById('mpTel').value || undefined,
        carreira: document.getElementById('mpCarreira').value,
        especialidade: document.getElementById('mpEsp').value || undefined,
        provincia: document.getElementById('mpProvincia').value || undefined,
        distrito: document.getElementById('mpDistrito').value || undefined,
        carga_horaria_semanal: Number(document.getElementById('mpCarga').value)
      };
      const res = await apiFetch('/api/v1/professores', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      if (res.success && res.data?.id) {
        const novoProfId = res.data.id;
        const checksTurmas = document.querySelectorAll('.check-turma-alocar-prof:checked');
        const discId = document.getElementById('mpDisciplinaInicial')?.value;

        if (checksTurmas.length > 0 && discId) {
          const promessasAlocacao = Array.from(checksTurmas).map(chk => {
            return apiFetch('/api/v1/professores/alocar', {
              method: 'POST',
              body: JSON.stringify({
                professor_id: novoProfId,
                turma_id: chk.value,
                disciplina_id: discId
              })
            });
          });
          await Promise.all(promessasAlocacao);
          mostrarNotificacao('Docente cadastrado e alocado à(s) turma(s) com sucesso!', 'success');
        } else {
          mostrarNotificacao('Docente cadastrado com sucesso!', 'success');
        }

        fecharModal();
        carregarProfessores();
      } else {
        alert(res.message || 'Erro ao cadastrar docente');
      }
    } catch (err) {
      alert('Erro ao cadastrar docente: ' + (err.message || 'Erro no servidor'));
    }
  });
}

function atualizarDistritosProfessor(provincia, distritoSelecionado = '', selectId = 'mpDistrito') {
  const distritos = state.geografia.distritos[provincia] || [];
  const select = document.getElementById(selectId);
  if (select) {
    select.innerHTML = distritos.map(d => `<option value="${d}" ${d === distritoSelecionado ? 'selected' : ''}>${d}</option>`).join('');
  }
}

async function modalEditarProfessor(profId) {
  try {
    let p = (state.todosProfessores || []).find(x => String(x.id) === String(profId));
    try {
      const res = await apiFetch(`/api/v1/professores/${profId}`);
      if (res && res.success && res.data) {
        p = res.data;
      } else if (res && (res.id || res.nome)) {
        p = res;
      }
    } catch (apiErr) {
      console.warn('Usando dados de professor em cache local:', apiErr);
    }

    if (!p) return alert('Falha ao obter dados do professor');

    const carreirasPadrao = ['DN1', 'DN2', 'DN3', 'DN4', 'N1', 'N2', 'N3', 'N4', 'Especialista de Educação', 'Mestre', 'Professor Doutor', 'Licenciado', 'Bacharel'];
    const carreiras = (state.geografia.carreiras && state.geografia.carreiras.length) ? state.geografia.carreiras : carreirasPadrao;
    const optCarreiras = carreiras.map(c => `<option value="${c}" ${c === p.carreira ? 'selected' : ''}>${c}</option>`).join('');

    const provincias = state.geografia.provincias || ['Maputo Cidade', 'Maputo Província', 'Gaza', 'Inhambane', 'Sofala', 'Manica', 'Tete', 'Zambézia', 'Nampula', 'Cabo Delgado', 'Niassa'];
    const optProvincias = provincias.map(prov => `<option value="${prov}" ${prov === p.provincia ? 'selected' : ''}>${prov}</option>`).join('');

    const alocacoesHtml = (p.alocacoes && p.alocacoes.length > 0)
      ? p.alocacoes.map(a => `
        <div class="d-flex justify-content-between align-items-center p-2 mb-1 bg-white rounded border">
          <div>
            <span class="badge bg-primary me-1">${a.turma_grau || 'Classe'}</span>
            <strong>${a.turma_nome || a.turma?.nome}</strong> &rarr; <span class="text-muted">${a.disciplina_nome || a.disciplina?.nome}</span>
          </div>
          <button type="button" class="btn btn-outline-danger btn-sm py-0 px-2" onclick="eliminarAlocacao('${a.id}', '${p.id}')" title="Desvincular esta turma">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      `).join('')
      : '<span class="text-muted small">Nenhuma turma alocada até ao momento.</span>';

    abrirModal(`Editar Docente: ${p.nome}`, `
      <form id="formModalEditarProf">
        <div class="row g-3">
          <div class="col-12">
            <div class="p-2 px-3 rounded bg-dark bg-opacity-10 border d-flex justify-content-between align-items-center">
              <span class="small fw-semibold"><i class="bi bi-lock-fill me-1 text-primary"></i>Código Fixo Oficial do Professor (Imutável):</span>
              <span class="badge bg-dark text-white font-monospace px-3 py-2">${p.codigo || 'PR-FIXO'}</span>
            </div>
          </div>
          <div class="col-md-7">
            <label class="form-label small fw-semibold">Nome Completo</label>
            <input type="text" id="mpeNome" class="form-control" required value="${p.nome || ''}">
          </div>
          <div class="col-md-5">
            <label class="form-label small fw-semibold">Apelido</label>
            <input type="text" id="mpeApelido" class="form-control" value="${p.apelido || ''}">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">E-mail Institucional</label>
            <input type="email" id="mpeEmail" class="form-control" required value="${p.email || ''}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Telefone</label>
            <input type="text" id="mpeTel" class="form-control" value="${p.telefone || ''}">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold text-primary">Carreira Docente (Quadro Oficial)</label>
            <select id="mpeCarreira" class="form-select">${optCarreiras}</select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Especialidade / Disciplina</label>
            <input type="text" id="mpeEsp" class="form-control" value="${p.especialidade || ''}">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Província</label>
            <select id="mpeProvincia" class="form-select" onchange="atualizarDistritosProfessor(this.value, '', 'mpeDistrito')">
              <option value="">Selecione a Província</option>
              ${optProvincias}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Distrito</label>
            <select id="mpeDistrito" class="form-select"></select>
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Carga Horária Semanal (Horas)</label>
            <input type="number" id="mpeCarga" class="form-control" value="${p.carga_horaria_semanal || 20}" required min="1" max="60">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Estado do Docente</label>
            <select id="mpeAtivo" class="form-select">
              <option value="true" ${p.ativo !== false ? 'selected' : ''}>Activo no Quadro</option>
              <option value="false" ${p.ativo === false ? 'selected' : ''}>Inactivo / Licença</option>
            </select>
          </div>

          <!-- Carga Horária Normal Máxima por Classe -->
          <div class="col-12 mt-2">
            <div class="p-3 bg-light rounded border">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <h6 class="fw-bold text-primary mb-0"><i class="bi bi-speedometer2 me-1"></i> Carga Horária Normal Máxima por Classe</h6>
                <span class="badge bg-primary bg-opacity-10 text-primary small">Contrato & Limites</span>
              </div>
              <div class="small text-muted mb-2" style="font-size: 0.78rem;">
                Defina o teto normal de aulas semanais para cada classe lecionada. Aulas atribuídas acima destes valores serão contabilizadas automaticamente como <strong>Horas Extras</strong>.
              </div>
              <div class="row g-2">
                ${(() => {
                  const classesEdicao = Array.from(new Set([
                    ...obterClassesDocentes(),
                    ...Object.keys(p.carga_maxima_por_classe || {}),
                    ...(p.alocacoes || []).map(a => a.turma_grau || a.turma?.grau_ano || a.disciplina?.classe).filter(Boolean)
                  ])).sort((a, b) => (parseInt(a.replace(/\D/g, '')) || 0) - (parseInt(b.replace(/\D/g, '')) || 0));

                  if (classesEdicao.length === 0) {
                    return `<div class="col-12 text-muted small fst-italic py-2"><i class="bi bi-info-circle me-1"></i>Nenhuma classe ou nível cadastrado nesta instituição ainda. Cadastre turmas ou disciplinas primeiro.</div>`;
                  }

                  return classesEdicao.map(c => {
                    const val = (p.carga_maxima_por_classe && p.carga_maxima_por_classe[c])
                      ? p.carga_maxima_por_classe[c]
                      : (p.carga_horaria_semanal || 16);
                    return `
                      <div class="col-md-4 col-sm-6">
                        <label class="form-label small fw-semibold mb-1"><i class="bi bi-mortarboard me-1 text-primary"></i>${c}</label>
                        <div class="input-group input-group-sm">
                          <input type="number" class="form-control mpeCargaClasseItem text-center fw-bold" data-classe="${c}" value="${val}" min="1" max="40">
                          <span class="input-group-text bg-white">h/sem</span>
                        </div>
                      </div>
                    `;
                  }).join('');
                })()}
              </div>
            </div>
          </div>

          <!-- Turmas e Classes Actuais do Docente -->
          <div class="col-12 mt-2">
            <div class="p-3 bg-light rounded border">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="fw-bold text-primary mb-0"><i class="bi bi-collection-fill me-1"></i> Classes & Turmas Alocadas</h6>
                <button type="button" class="btn btn-outline-primary btn-sm py-0 px-2" onclick="fecharModal(); modalAlocarProfessor('${p.id}');">
                  <i class="bi bi-plus-lg me-1"></i>Atribuir Nova Turma
                </button>
              </div>
              <div id="containerAlocacoesEditarProf">
                ${alocacoesHtml}
              </div>
            </div>
          </div>
        </div>
        <div class="d-flex gap-2 justify-content-between align-items-center mt-4 pt-2 border-top">
          <button type="button" class="btn btn-outline-danger btn-sm" onclick="fecharModal(); excluirProfessor('${p.id}');">
            <i class="bi bi-trash me-1"></i>Eliminar Docente
          </button>
          <div class="d-flex gap-2">
            <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
            <button type="submit" class="btn btn-primary btn-sm px-4">Salvar Alterações</button>
          </div>
        </div>
      </form>
    `);

    if (p.provincia) {
      atualizarDistritosProfessor(p.provincia, p.distrito || '', 'mpeDistrito');
    }

    document.getElementById('formModalEditarProf').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const cargasMap = {};
        document.querySelectorAll('.mpeCargaClasseItem').forEach(inp => {
          const c = inp.getAttribute('data-classe');
          const val = Number(inp.value);
          if (c && val > 0) cargasMap[c] = val;
        });

        const body = {
          nome: document.getElementById('mpeNome').value,
          apelido: document.getElementById('mpeApelido').value || null,
          email: document.getElementById('mpeEmail').value,
          telefone: document.getElementById('mpeTel').value || null,
          carreira: document.getElementById('mpeCarreira').value,
          especialidade: document.getElementById('mpeEsp').value || null,
          provincia: document.getElementById('mpeProvincia').value || null,
          distrito: document.getElementById('mpeDistrito').value || null,
          carga_horaria_semanal: Number(document.getElementById('mpeCarga').value),
          carga_maxima_por_classe: cargasMap,
          ativo: document.getElementById('mpeAtivo').value === 'true'
        };
        const updateRes = await apiFetch(`/api/v1/professores/${profId}`, {
          method: 'PUT',
          body: JSON.stringify(body)
        });
        if (updateRes.success) {
          mostrarNotificacao('Dados do docente actualizados com sucesso!', 'success');
          fecharModal();
          carregarProfessores();
        } else {
          alert(updateRes.message || 'Erro ao actualizar dados do professor');
        }
      } catch (err) {
        alert(err.message || 'Erro ao actualizar dados do professor');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados do professor: ' + err.message);
  }
}

async function modalAlocarProfessor(professorIdPadrao = '') {
  const [profsRes, turmasRes, discRes] = await Promise.all([
    apiFetch('/api/v1/professores'),
    apiFetch('/api/v1/escola-admin/turmas'),
    apiFetch('/api/v1/disciplinas')
  ]);

  const profs = profsRes.data || state.todosProfessores || [];
  const turmas = turmasRes.data || state.todasTurmas || [];
  const disciplinas = discRes.data || state.todasDisciplinas || [];

  state.todosProfessores = profs;
  state.todasTurmas = turmas;
  state.todasDisciplinas = disciplinas;

  const optProfs = profs.map(p => 
    `<option value="${p.id}" ${p.id === professorIdPadrao ? 'selected' : ''}>${p.nome} ${p.apelido || ''} (${p.especialidade || 'Docente'})</option>`
  ).join('');

  // Obter classes distintas das turmas
  const classesSet = new Set();
  turmas.forEach(t => { if (t.grau_ano) classesSet.add(t.grau_ano.trim()); });
  disciplinas.forEach(d => { if (d.classe) classesSet.add(d.classe.trim()); });
  const classesList = Array.from(classesSet).sort((a, b) => (parseInt(a.replace(/\D/g, '')) || 0) - (parseInt(b.replace(/\D/g, '')) || 0));

  const optClasses = classesList.length > 0
    ? classesList.map(c => `<option value="${c}">${c}</option>`).join('')
    : '<option value="" disabled>-- Nenhuma classe/nível cadastrado nesta instituição --</option>';

  abrirModal('Atribuir Turma & Carga Horária Docente', `
    <form id="formModalAloc">
      <div class="mb-3">
        <label class="form-label small fw-semibold">1. Professor / Docente *</label>
        <select id="malocProf" class="form-select fw-semibold" required onchange="aoMudarProfessorModalAlocar()">${optProfs}</select>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-md-7">
          <label class="form-label small fw-semibold text-primary"><i class="bi bi-mortarboard-fill me-1"></i> 2. Seleccione a Classe / Grau *</label>
          <select id="malocClasse" class="form-select border-primary fw-semibold" required onchange="aoMudarClasseModalAlocar()">
            <option value="">Selecione a Classe...</option>
            ${optClasses}
          </select>
          <small class="text-muted" style="font-size: 0.72rem;">Filtra automaticamente turmas de todas as secções e disciplinas.</small>
        </div>
        <div class="col-md-5">
          <label class="form-label small fw-semibold text-info"><i class="bi bi-speedometer2 me-1"></i> Carga Normal Máx. nesta Classe</label>
          <div class="input-group input-group-sm">
            <input type="number" id="malocCargaMaxClasse" class="form-control fw-bold border-info text-center" value="16" min="1" max="40" oninput="aoAtualizarCalculoCargaAlocar()">
            <span class="input-group-text bg-info bg-opacity-10 text-info fw-bold">h/sem</span>
          </div>
          <small class="text-muted" style="font-size: 0.7rem;">Teto contratual normal do docente para esta classe.</small>
        </div>
      </div>

      <div class="mb-3">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <label class="form-label small fw-semibold text-primary mb-0"><i class="bi bi-collection-fill me-1"></i> 3. Turma da Classe Seleccionada *</label>
          <span class="badge bg-light text-secondary border small" style="font-size: 0.7rem;">Mesma secção ou secções diferentes</span>
        </div>
        <select id="malocTurma" class="form-select border-primary" required onchange="aoAtualizarCalculoCargaAlocar()">
          <option value="">Selecione primeiro a classe acima...</option>
        </select>
      </div>

      <div class="mb-3">
        <label class="form-label small fw-semibold text-primary"><i class="bi bi-book-fill me-1"></i> 4. Disciplina Curricular *</label>
        <select id="malocDisc" class="form-select border-primary" required onchange="aoAtualizarCalculoCargaAlocar()">
          <option value="">Selecione a disciplina curricular...</option>
        </select>
      </div>

      <!-- Painel Dinâmico de Cálculo Automático e Transbordo de Horas Extras -->
      <div id="painelAnaliseCargaDocente" class="mt-3"></div>

      <div class="d-flex gap-2 justify-content-end mt-4 pt-2 border-top">
        <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
        <button type="submit" id="btnConfirmarAlocacao" class="btn btn-primary btn-sm px-4 fw-semibold">
          <i class="bi bi-check2-circle me-1"></i> Confirmar Atribuição
        </button>
      </div>
    </form>
  `);

  window.aoMudarProfessorModalAlocar = function() {
    const profId = document.getElementById('malocProf')?.value;
    const selClasse = document.getElementById('malocClasse')?.value;
    const prof = (state.todosProfessores || []).find(p => String(p.id) === String(profId));
    if (prof && selClasse) {
      const maxClasse = (prof.carga_maxima_por_classe && prof.carga_maxima_por_classe[selClasse])
        ? Number(prof.carga_maxima_por_classe[selClasse])
        : (prof.carga_horaria_semanal || 16);
      const inp = document.getElementById('malocCargaMaxClasse');
      if (inp) inp.value = maxClasse;
    }
    aoAtualizarCalculoCargaAlocar();
  };

  window.aoMudarClasseModalAlocar = function() {
    const selClasse = document.getElementById('malocClasse')?.value;
    const profId = document.getElementById('malocProf')?.value;
    const selTurma = document.getElementById('malocTurma');
    const selDisc = document.getElementById('malocDisc');
    const inpMaxClasse = document.getElementById('malocCargaMaxClasse');
    if (!selTurma || !selDisc) return;

    if (!selClasse) {
      selTurma.innerHTML = '<option value="">Selecione primeiro a classe acima...</option>';
      selDisc.innerHTML = '<option value="">Selecione primeiro a classe acima...</option>';
      aoAtualizarCalculoCargaAlocar();
      return;
    }

    // Carregar limite contratual do professor para esta classe
    const prof = (state.todosProfessores || []).find(p => String(p.id) === String(profId));
    if (prof && inpMaxClasse) {
      const maxClasse = (prof.carga_maxima_por_classe && prof.carga_maxima_por_classe[selClasse])
        ? Number(prof.carga_maxima_por_classe[selClasse])
        : (prof.carga_horaria_semanal || 16);
      inpMaxClasse.value = maxClasse;
    }

    // Filtrar turmas da classe seleccionada (permite qualquer secção ou área)
    const turmasFiltradas = (state.todasTurmas || []).filter(t => 
      normalizarClasse(t.grau_ano) === normalizarClasse(selClasse)
    );

    if (turmasFiltradas.length === 0) {
      selTurma.innerHTML = `<option value="">Nenhuma turma cadastrada para ${selClasse}</option>`;
    } else {
      selTurma.innerHTML = '<option value="">Selecione a Turma...</option>' + 
        turmasFiltradas.map(t => {
          const areaLabel = t.area ? `Secção: ${t.area}` : 'Geral';
          const turnoLabel = t.turno || 'Diurno';
          return `<option value="${t.id}">${t.nome} (${areaLabel} - ${turnoLabel})</option>`;
        }).join('');
    }

    // Filtrar disciplinas da classe
    const discFiltradas = (state.todasDisciplinas || []).filter(d => 
      !d.classe || normalizarClasse(d.classe) === normalizarClasse(selClasse)
    );

    if (discFiltradas.length === 0) {
      selDisc.innerHTML = (state.todasDisciplinas || []).map(d => `<option value="${d.id}">${d.nome} (${d.carga_horaria || 5}h/sem)</option>`).join('');
    } else {
      selDisc.innerHTML = '<option value="">Selecione a Disciplina...</option>' + 
        discFiltradas.map(d => `<option value="${d.id}">${d.nome} (${d.carga_horaria || 5}h/semana${d.area ? ` - ${d.area}` : ''})</option>`).join('');
    }

    aoAtualizarCalculoCargaAlocar();
  };

  window.aoAtualizarCalculoCargaAlocar = function() {
    const profId = document.getElementById('malocProf')?.value;
    const selClasse = document.getElementById('malocClasse')?.value;
    const turmaId = document.getElementById('malocTurma')?.value;
    const discId = document.getElementById('malocDisc')?.value;
    const inputMaxClasse = document.getElementById('malocCargaMaxClasse');
    const container = document.getElementById('painelAnaliseCargaDocente');
    if (!container) return;

    const prof = (state.todosProfessores || []).find(p => String(p.id) === String(profId));
    if (!prof) {
      container.innerHTML = '';
      return;
    }

    const metricas = calcularMetricasCargaProfessor(prof);
    const maxClasse = Number(inputMaxClasse?.value) || (prof.carga_maxima_por_classe?.[selClasse] || prof.carga_horaria_semanal || 16);
    const maxGeral = metricas.maxNormal;

    const cargaClasseAtual = selClasse ? (metricas.porClasse[selClasse]?.cargaAlocada || 0) : 0;
    const cargaGeralAtual = metricas.totalAlocada;

    // Obter carga da disciplina selecionada
    let chNova = 0;
    let discNome = '';
    if (discId) {
      const disc = (state.todasDisciplinas || []).find(d => String(d.id) === String(discId));
      if (disc) {
        chNova = Number(disc.carga_horaria) || 5;
        discNome = disc.nome || '';
      }
    }

    const novaCargaClasse = cargaClasseAtual + chNova;
    const novaCargaGeral = cargaGeralAtual + chNova;

    // Calcular horas normais e transbordo (horas extras)
    const horasExtrasClasse = Math.max(0, novaCargaClasse - maxClasse);
    const horasExtrasGeral = Math.max(0, novaCargaGeral - maxGeral);
    const horasExtrasFinais = Math.max(horasExtrasClasse, horasExtrasGeral);
    const horasNormaisFinais = Math.max(0, novaCargaGeral - horasExtrasFinais);

    // Listar turmas atuais
    const turmasAtuais = (prof.alocacoes || []).map(a => {
      const c = a.turma_grau || a.turma?.grau_ano || 'Classe';
      const t = a.turma_nome || a.turma?.nome || 'Turma';
      const d = a.disciplina_nome || a.disciplina?.nome || 'Disciplina';
      const ch = a.disciplina_carga_horaria || a.disciplina?.carga_horaria || 5;
      return `<li class="d-flex justify-content-between py-1 border-bottom border-light"><span><span class="badge bg-secondary me-1" style="font-size:0.68rem;">${c}</span><strong>${t}</strong>: ${d}</span><span class="badge bg-light text-dark border font-monospace">${ch}h/sem</span></li>`;
    }).join('');

    const temAlocacoes = (prof.alocacoes && prof.alocacoes.length > 0);

    let statusBox = '';
    if (chNova > 0 && horasExtrasFinais > 0) {
      statusBox = `
        <div class="alert alert-warning border border-warning d-flex align-items-start gap-2 mb-2 p-2 rounded">
          <i class="bi bi-exclamation-triangle-fill text-warning fs-4 mt-1"></i>
          <div>
            <div class="fw-bold text-dark">Atenção: Transbordo de Carga Horária Máxima!</div>
            <div class="small text-dark">
              Esta atribuição (${chNova}h/semana) excede o teto contratual normal. O sistema separa e contabiliza automaticamente:
            </div>
            <div class="d-flex gap-2 align-items-center mt-2 flex-wrap">
              <span class="badge bg-success p-2" style="font-size: 0.8rem;">Carga Normal: ${horasNormaisFinais}h / semana</span>
              <span class="badge bg-danger p-2 fs-6 font-monospace" style="font-size: 0.85rem;">+${horasExtrasFinais} Horas Extras / semana</span>
            </div>
            <div class="small text-muted mt-1" style="font-size: 0.72rem;">
              * As horas extras serão reflectidas no mapa de encargos e folha salarial da escola.
            </div>
          </div>
        </div>
      `;
    } else if (chNova > 0) {
      statusBox = `
        <div class="alert alert-success border border-success d-flex align-items-center gap-2 mb-2 p-2 rounded">
          <i class="bi bi-check-circle-fill text-success fs-4"></i>
          <div>
            <div class="fw-bold text-success">Dentro da Carga Horária Normal</div>
            <div class="small text-muted">
              Carga Total: <strong>${novaCargaGeral}h / semana</strong> (100% Carga Normal | <strong>0h Extras</strong>). O docente está dentro do limite máximo de ${maxClasse}h (classe) e ${maxGeral}h (geral).
            </div>
          </div>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="card bg-light border p-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-primary mb-0" style="font-size: 0.85rem;">
            <i class="bi bi-calculator me-1"></i> Análise de Carga Horária do Docente
          </h6>
          <span class="badge bg-secondary font-monospace" style="font-size: 0.75rem;">
            ${prof.nome} ${prof.apelido || ''}
          </span>
        </div>

        <div class="row g-2 text-center mb-2">
          <div class="col-3">
            <div class="p-2 bg-white rounded border">
              <small class="text-muted d-block" style="font-size: 0.68rem;">Carga Atual</small>
              <strong class="fs-6 text-dark">${cargaGeralAtual}h</strong>
              <small class="d-block text-muted" style="font-size: 0.65rem;">${selClasse ? `${cargaClasseAtual}h na ${selClasse.replace('Classe', '').trim()}` : 'Geral'}</small>
            </div>
          </div>
          <div class="col-3">
            <div class="p-2 bg-white rounded border border-primary border-opacity-25">
              <small class="text-primary d-block" style="font-size: 0.68rem;">Desta Turma</small>
              <strong class="fs-6 text-primary">+${chNova}h</strong>
              <small class="d-block text-muted" style="font-size: 0.65rem;">${discNome ? discNome.slice(0, 10) : 'Pendente'}</small>
            </div>
          </div>
          <div class="col-3">
            <div class="p-2 bg-white rounded border ${horasExtrasFinais > 0 ? 'border-warning' : 'border-success'}">
              <small class="d-block text-muted" style="font-size: 0.68rem;">Nova Carga Total</small>
              <strong class="fs-6 ${horasExtrasFinais > 0 ? 'text-warning' : 'text-success'}">${novaCargaGeral}h</strong>
              <small class="d-block ${horasExtrasFinais > 0 ? 'text-danger fw-bold' : 'text-success'}" style="font-size: 0.65rem;">
                ${horasExtrasFinais > 0 ? `+${horasExtrasFinais}h extra` : 'Normal'}
              </small>
            </div>
          </div>
          <div class="col-3">
            <div class="p-2 bg-white rounded border">
              <small class="text-muted d-block" style="font-size: 0.68rem;">Máx. Normal</small>
              <strong class="fs-6 text-info">${maxClasse}h</strong>
              <small class="d-block text-muted" style="font-size: 0.65rem;">Geral: ${maxGeral}h</small>
            </div>
          </div>
        </div>

        ${statusBox}

        ${temAlocacoes ? `
          <div class="mt-1">
            <a class="text-decoration-none small fw-semibold text-secondary d-inline-block" data-bs-toggle="collapse" href="#detalheTurmasAtuaisAloc" role="button">
              <i class="bi bi-chevron-down me-1"></i> Ver ${prof.alocacoes.length} turma(s) já atribuída(s) a este docente
            </a>
            <div class="collapse mt-2" id="detalheTurmasAtuaisAloc">
              <ul class="list-unstyled mb-0 small" style="max-height: 120px; overflow-y: auto;">
                ${turmasAtuais}
              </ul>
            </div>
          </div>
        ` : '<div class="small text-muted fst-italic">Este docente ainda não possui nenhuma turma atribuída.</div>'}
      </div>
    `;
  };

  // Inicializar cálculo inicial
  aoAtualizarCalculoCargaAlocar();

  document.getElementById('formModalAloc').addEventListener('submit', async (e) => {
    e.preventDefault();
    const profId = document.getElementById('malocProf').value;
    const turmaId = document.getElementById('malocTurma').value;
    const discId = document.getElementById('malocDisc').value;
    const cargaMaxClasse = Number(document.getElementById('malocCargaMaxClasse')?.value) || 16;
    const selClasse = document.getElementById('malocClasse')?.value;

    if (!profId || !turmaId || !discId) {
      return alert('Por favor seleccione o professor, a classe, a turma e a disciplina.');
    }

    try {
      const res = await apiFetch('/api/v1/professores/alocar', {
        method: 'POST',
        body: JSON.stringify({
          professor_id: profId,
          turma_id: turmaId,
          disciplina_id: discId,
          carga_maxima_classe: cargaMaxClasse
        })
      });
      if (res.success) {
        mostrarNotificacao('Turma e disciplina alocadas com sucesso! Carga horária e horas extras atualizadas.', 'success');
        fecharModal();
        await carregarProfessores();
      } else {
        alert(res.message || 'Erro ao alocar professor');
      }
    } catch (err) {
      alert(err.message || 'Erro ao alocar professor');
    }
  });
}

async function modalTransferirProfessor(profId) {
  try {
    const prof = (state.todosProfessores || []).find(p => p.id === profId);
    if (!prof) return alert('Docente não encontrado');

    const [turmasRes, discRes] = await Promise.all([
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/disciplinas')
    ]);

    const turmas = turmasRes.data || [];
    const disciplinas = discRes.data || [];
    state.todasTurmas = turmas;
    state.todasDisciplinas = disciplinas;

    const classesSet = new Set();
    turmas.forEach(t => { if (t.grau_ano) classesSet.add(t.grau_ano.trim()); });
    disciplinas.forEach(d => { if (d.classe) classesSet.add(d.classe.trim()); });
    const classesList = Array.from(classesSet).sort((a, b) => (parseInt(a.replace(/\D/g, '')) || 0) - (parseInt(b.replace(/\D/g, '')) || 0));

    const optClasses = classesList.length > 0
      ? classesList.map(c => `<option value="${c}">${c}</option>`).join('')
      : '<option value="" disabled>-- Nenhuma classe/nível cadastrado nesta instituição --</option>';

    const alocacoesAtuaisHtml = (prof.alocacoes && prof.alocacoes.length > 0)
      ? prof.alocacoes.map(a => `
        <span class="badge border bg-light text-dark p-2 me-1 mb-1">
          <i class="bi bi-mortarboard me-1 text-primary"></i>${a.turma_grau || 'Classe'}: <strong>${a.turma_nome || a.turma?.nome}</strong> (${a.disciplina_nome || a.disciplina?.nome})
        </span>
      `).join('')
      : '<span class="text-muted small">Sem turmas atribuídas de momento.</span>';

    abrirModal(`Transferir / Atribuir Nova Classe: ${prof.nome}`, `
      <form id="formModalTransferirProf">
        <div class="mb-3 p-3 bg-light rounded border">
          <div class="small fw-bold text-muted text-uppercase mb-1">Docente Seleccionado:</div>
          <h5 class="fw-bold text-primary mb-1">${prof.nome} ${prof.apelido || ''}</h5>
          <div class="small text-muted mb-2">Carreira: <strong>${prof.carreira || 'Licenciado'}</strong> | Especialidade: <strong>${prof.especialidade || 'Área Geral'}</strong></div>
          <div class="small fw-bold text-muted text-uppercase mb-1">Classes & Turmas Actuais:</div>
          <div class="d-flex flex-wrap gap-1">${alocacoesAtuaisHtml}</div>
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold text-dark">Modo de Operação</label>
          <div class="p-2 border rounded bg-white">
            <div class="form-check mb-1">
              <input class="form-check-input" type="radio" name="modoOperacao" id="modoSubstituir" value="SUBSTITUIR" checked>
              <label class="form-check-label small fw-semibold" for="modoSubstituir">
                Transferir Integralmente (Substituir turmas anteriores pela nova classe)
              </label>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="radio" name="modoOperacao" id="modoAdicionar" value="ADICIONAR">
              <label class="form-check-label small fw-semibold" for="modoAdicionar">
                Atribuir Classe Adicional (Manter turmas actuais e acrescentar a nova classe)
              </label>
            </div>
          </div>
        </div>

        <div class="row g-3">
          <div class="col-md-6">
            <label class="form-label small fw-bold text-primary"><i class="bi bi-mortarboard-fill me-1"></i> 1. Nova Classe / Grau</label>
            <select id="mtransfClasse" class="form-select border-primary fw-semibold" required onchange="aoMudarClasseModalTransferir()">
              <option value="">Selecione a Classe...</option>
              ${optClasses}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-bold text-primary"><i class="bi bi-collection-fill me-1"></i> 2. Turma da Nova Classe</label>
            <select id="mtransfTurma" class="form-select border-primary" required>
              <option value="">Selecione primeiro a classe...</option>
            </select>
          </div>
          <div class="col-12">
            <label class="form-label small fw-bold text-primary"><i class="bi bi-book-fill me-1"></i> 3. Disciplina a Ministrar</label>
            <select id="mtransfDisc" class="form-select border-primary" required>
              <option value="">Selecione a disciplina...</option>
            </select>
          </div>
        </div>

        <div class="d-flex justify-content-end gap-2 mt-4 pt-2 border-top">
          <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
          <button type="submit" class="btn btn-warning text-dark fw-bold btn-sm px-4">
            <i class="bi bi-arrow-left-right me-1"></i> Confirmar Atribuição / Transferência
          </button>
        </div>
      </form>
    `);

    window.aoMudarClasseModalTransferir = function() {
      const cls = document.getElementById('mtransfClasse')?.value;
      const selTurma = document.getElementById('mtransfTurma');
      const selDisc = document.getElementById('mtransfDisc');
      if (!selTurma || !selDisc) return;

      if (!cls) {
        selTurma.innerHTML = '<option value="">Selecione primeiro a classe...</option>';
        selDisc.innerHTML = '<option value="">Selecione primeiro a classe...</option>';
        return;
      }

      const turmasFiltradas = (state.todasTurmas || []).filter(t => 
        normalizarClasse(t.grau_ano) === normalizarClasse(cls)
      );

      if (turmasFiltradas.length === 0) {
        selTurma.innerHTML = `<option value="">Nenhuma turma cadastrada para ${cls}</option>`;
      } else {
        selTurma.innerHTML = '<option value="">Selecione a Turma...</option>' + 
          turmasFiltradas.map(t => `<option value="${t.id}">${t.nome} (${t.area || 'Geral'})</option>`).join('');
      }

      const discFiltradas = (state.todasDisciplinas || []).filter(d => 
        !d.classe || normalizarClasse(d.classe) === normalizarClasse(cls)
      );

      if (discFiltradas.length === 0) {
        selDisc.innerHTML = (state.todasDisciplinas || []).map(d => `<option value="${d.id}">${d.nome}</option>`).join('');
      } else {
        selDisc.innerHTML = '<option value="">Selecione a Disciplina...</option>' + 
          discFiltradas.map(d => `<option value="${d.id}">${d.nome} ${d.classe ? `(${d.classe})` : ''}</option>`).join('');
      }
    };

    document.getElementById('formModalTransferirProf').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const modo = document.querySelector('input[name="modoOperacao"]:checked')?.value || 'SUBSTITUIR';
        const turmaId = document.getElementById('mtransfTurma').value;
        const discId = document.getElementById('mtransfDisc').value;

        if (!turmaId || !discId) {
          return alert('Por favor, seleccione a turma e a disciplina correspondentes.');
        }

        // Se for substituição integral, remove as alocações anteriores
        if (modo === 'SUBSTITUIR' && prof.alocacoes && prof.alocacoes.length > 0) {
          const remocoes = prof.alocacoes.map(a => 
            apiFetch(`/api/v1/professores/alocar/${a.id}`, { method: 'DELETE' })
          );
          await Promise.all(remocoes);
        }

        // Cria a nova alocação
        const resAloc = await apiFetch('/api/v1/professores/alocar', {
          method: 'POST',
          body: JSON.stringify({
            professor_id: profId,
            turma_id: turmaId,
            disciplina_id: discId
          })
        });

        if (resAloc.success) {
          mostrarNotificacao('Docente transferido / atribuído à nova classe com sucesso!', 'success');
          fecharModal();
          carregarProfessores();
        } else {
          alert(resAloc.message || 'Erro ao atribuir nova classe');
        }
      } catch (err) {
        alert(err.message || 'Erro ao realizar transferência');
      }
    });
  } catch (err) {
    alert('Erro ao carregar modal de transferência: ' + err.message);
  }
}

async function excluirProfessor(profId) {
  const p = (state.todosProfessores || []).find(x => x.id === profId);
  const nome = p ? `${p.nome} ${p.apelido || ''}`.trim() : 'este docente';
  if (!confirm(`Tem a certeza que deseja eliminar o docente "${nome}" do quadro escolar? Todas as suas alocações de turmas e disciplinas serão desvinculadas.`)) {
    return;
  }
  try {
    const res = await apiFetch(`/api/v1/professores/${profId}`, {
      method: 'DELETE'
    });
    if (res.success) {
      mostrarNotificacao('Docente eliminado do quadro com sucesso!', 'success');
      await carregarProfessores();
    } else {
      alert(res.message || 'Erro ao eliminar docente');
    }
  } catch (err) {
    alert(err.message || 'Erro ao comunicar com o servidor');
  }
}

async function modalEditarAlocacao(alocacaoId, profId) {
  try {
    const [profsRes, turmasRes, discRes] = await Promise.all([
      apiFetch('/api/v1/professores'),
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/disciplinas')
    ]);

    const prof = (profsRes.data || []).find(p => p.id === profId);
    const aloc = prof ? (prof.alocacoes || []).find(a => a.id === alocacaoId) : null;

    const optTurmas = (turmasRes.data || []).map(t => 
      `<option value="${t.id}" ${aloc && aloc.turma_id === t.id ? 'selected' : ''}>${t.grau_ano} &rarr; ${t.nome} (${normalizarArea(t.area || 'Geral')})</option>`
    ).join('');

    const optDisc = (discRes.data || []).map(d => 
      `<option value="${d.id}" ${aloc && aloc.disciplina_id === d.id ? 'selected' : ''}>${d.nome} (${d.classe || ''})</option>`
    ).join('');

    abrirModal(`Editar Alocação: ${prof ? prof.nome : 'Docente'}`, `
      <form id="formModalEditarAloc">
        <div class="mb-3">
          <label class="form-label small fw-semibold">Professor / Docente</label>
          <input type="text" class="form-control" value="${prof ? prof.nome : ''}" disabled>
        </div>
        <div class="mb-3">
          <label class="form-label small fw-semibold text-primary">Turma Atribuída</label>
          <select id="mEditAlocTurma" class="form-select" required>${optTurmas}</select>
        </div>
        <div class="mb-3">
          <label class="form-label small fw-semibold text-primary">Disciplina Curricular</label>
          <select id="mEditAlocDisc" class="form-select" required>${optDisc}</select>
        </div>
        <div class="d-flex gap-2 justify-content-end mt-4">
          <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
          <button type="submit" class="btn btn-primary btn-sm px-4">Salvar Alterações</button>
        </div>
      </form>
    `);

    document.getElementById('formModalEditarAloc').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const res = await apiFetch(`/api/v1/professores/alocar/${alocacaoId}`, {
          method: 'PUT',
          body: JSON.stringify({
            turma_id: document.getElementById('mEditAlocTurma').value,
            disciplina_id: document.getElementById('mEditAlocDisc').value
          })
        });
        if (res.success) {
          mostrarNotificacao('Alocação actualizada com sucesso!', 'success');
          fecharModal();
          carregarProfessores();
        } else {
          alert(res.message || 'Erro ao actualizar alocação');
        }
      } catch (err) {
        alert(err.message || 'Erro ao comunicar com o servidor');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados da alocação: ' + err.message);
  }
}

async function eliminarAlocacao(alocacaoId, profId) {
  if (!confirm('Tem a certeza que deseja eliminar esta alocação de turma/disciplina do docente?')) return;
  try {
    const res = await apiFetch(`/api/v1/professores/alocar/${alocacaoId}`, {
      method: 'DELETE'
    });
    if (res.success) {
      mostrarNotificacao('Alocação eliminada com sucesso!', 'success');
      await carregarProfessores();
    } else {
      alert(res.message || 'Erro ao eliminar alocação');
    }
  } catch (err) {
    alert(err.message || 'Erro ao comunicar com o servidor');
  }
}

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
  const rows = document.querySelectorAll('.linha-disciplina-item');
  let visiveis = 0;

  if (rows && rows.length > 0) {
    rows.forEach(r => {
      const txt = (r.getAttribute('data-texto') || r.textContent).toLowerCase();
      const show = (!busca || txt.includes(busca));
      r.style.display = show ? '' : 'none';
      if (show) visiveis++;
    });

    const cards = document.querySelectorAll('.area-seccao-card');
    cards.forEach(c => {
      if (!busca) {
        c.style.display = '';
        return;
      }
      const visibleInCard = c.querySelectorAll('.linha-disciplina-item:not([style*="display: none"])');
      c.style.display = visibleInCard.length > 0 ? '' : 'none';
    });
    return;
  }

  const fallbackRows = document.querySelectorAll('#tabelaDisciplinas tr');
  fallbackRows.forEach(r => {
    if (r.cells.length < 4) return;
    const txt = r.textContent.toLowerCase();
    const show = (!busca || txt.includes(busca));
    r.style.display = show ? '' : 'none';
  });
}

// ==================== GESTÃO DE CLASSES E NÍVEIS CURRICULARES (REGIME DE EXAME) ====================
// Regra oficial MEC Moçambique (Ministério da Educação e Cultura):
// 10ª Classe e 12ª Classe: Exame Nacional Obrigatório (Com Exame)
// 1ª à 9ª e 11ª Classes: Avaliação Contínua e Sistemática (Sem Exame por padrão)
window.PADRAO_CLASSES_MOCAMBIQUE_EXAMES = {
  '1ª Classe': false,
  '2ª Classe': false,
  '3ª Classe': false,
  '4ª Classe': false,
  '5ª Classe': false,
  '6ª Classe': false,
  '7ª Classe': false,
  '8ª Classe': false,
  '9ª Classe': false,
  '10ª Classe': true,
  '11ª Classe': false,
  '12ª Classe': true
};

window.PADRAO_NIVEIS_TECNICOS_EXAMES = {
  'Nível 1': false,
  'Nível 2': false,
  'Nível 3': true,
  'Nível 4': false,
  'Nível 5': true
};

window.obterRegimeCurricularInstituicao = function() {
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id
    || 'padrao';
  const chave = `sige_regime_curricular_${escolaId}`;
  return localStorage.getItem(chave) || state.escola?.regime_curricular || state.tenant?.regime_curricular || 'CLASSES';
};

window.definirRegimeCurricularInstituicao = async function(novoRegime) {
  if (!['CLASSES', 'NIVEIS'].includes(novoRegime)) novoRegime = 'CLASSES';
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id
    || 'padrao';
  const chave = `sige_regime_curricular_${escolaId}`;
  localStorage.setItem(chave, novoRegime);
  if (state.escola) state.escola.regime_curricular = novoRegime;
  if (state.tenant) state.tenant.regime_curricular = novoRegime;
  state.regimeCurricular = novoRegime;

  try {
    await apiFetch('/api/v1/escola-admin/classes-exames', {
      method: 'POST',
      body: JSON.stringify({ regime: novoRegime })
    });
  } catch (e) {
    console.warn('Erro ao persistir regime na API:', e);
  }
};

window.obterClassesExamesConfig = function() {
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id
    || 'padrao';
  const chave = `sige_classes_exames_${escolaId}`;

  let configLocal = {};
  try {
    configLocal = JSON.parse(localStorage.getItem(chave) || '{}');
  } catch (_) {}

  const configApi = state.escola?.config_classes_exames || {};
  return { ...configApi, ...configLocal };
};

window.classeTemExame = function(classeOuNivel) {
  if (!classeOuNivel) return false;
  const cNorm = String(classeOuNivel).trim();
  const cfg = window.obterClassesExamesConfig();
  if (cfg[cNorm] !== undefined) return Boolean(cfg[cNorm]);

  const cLow = cNorm.toLowerCase();
  if (cLow.includes('10ª') || cLow.includes('10a') || cLow.includes('12ª') || cLow.includes('12a') || cLow.includes('nível 3') || cLow.includes('nivel 3') || cLow.includes('nível 5') || cLow.includes('nivel 5')) {
    return true;
  }
  return false;
};

window.salvarClassesExamesConfig = async function(novoConfig) {
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id
    || 'padrao';
  const chave = `sige_classes_exames_${escolaId}`;

  try {
    localStorage.setItem(chave, JSON.stringify(novoConfig));
  } catch (_) {}

  if (state.escola) {
    state.escola.config_classes_exames = novoConfig;
  }

  try {
    await apiFetch('/api/v1/escola-admin/classes-exames', {
      method: 'POST',
      body: JSON.stringify({ config: novoConfig })
    });
  } catch (err) {
    console.warn('Sincronização remota de classes-exames salva em cache local:', err);
  }
};

// ==================== CONTROLADOR DA PÁGINA: CLASSES-EXAMES ====================
window.carregarPaginaClassesExames = async function(forcarRecarregamento = false) {
  const viewEl = document.getElementById('view-classes-exames');
  if (!viewEl) return;

  let regime = window.obterRegimeCurricularInstituicao();
  let listaItens = [];

  try {
    const res = await apiFetch('/api/v1/escola-admin/classes-exames');
    if (res && res.success) {
      if (res.regime) {
        regime = res.regime;
        const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
          || state.tenant?.id || state.user?.escola_id || 'padrao';
        localStorage.setItem(`sige_regime_curricular_${escolaId}`, regime);
      }
      listaItens = res.data || [];
      if (state.escola) {
        state.escola.config_classes_exames = res.config_raw || {};
        state.escola.regime_curricular = regime;
      }
    }
  } catch (err) {
    console.warn('Carregamento de classes-exames da API:', err);
    const cfg = state.escola?.config_classes_exames || {};
    listaItens = Object.keys(cfg).map(k => ({
      nome: k,
      tem_exame: Boolean(cfg[k]),
      tipo: regime === 'CLASSES' ? 'CLASSE' : 'NIVEL'
    }));
  }

  state.regimeCurricular = regime;
  state.listaClassesExamesPagina = listaItens;

  const selRegime = document.getElementById('selectRegimeInstituicao');
  if (selRegime) selRegime.value = regime;

  const badgeRegime = document.getElementById('badgeRegimeAtivo');
  if (badgeRegime) {
    badgeRegime.innerHTML = regime === 'CLASSES'
      ? '<i class="bi bi-mortarboard me-1"></i> Classes SNE'
      : '<i class="bi bi-layers me-1"></i> Níveis Técnicos';
  }

  const btnLabel = document.getElementById('btnLabelNovaClasse');
  if (btnLabel) {
    btnLabel.textContent = regime === 'CLASSES' ? '+ Nova Classe' : '+ Novo Nível';
  }

  const tituloTabela = document.getElementById('tituloTabelaItens');
  if (tituloTabela) {
    tituloTabela.innerHTML = `<i class="bi bi-list-check me-2 text-primary"></i>${regime === 'CLASSES' ? 'Classes da Instituição' : 'Níveis da Instituição'}`;
  }

  window.renderizarTabelaClassesExamesPagina();
};

window.renderizarTabelaClassesExamesPagina = function() {
  const tbody = document.getElementById('tbodyClassesExames');
  const placeholder = document.getElementById('placeholderSemItens');
  const badgeTotal = document.getElementById('kpiTotalItensBadge');
  if (!tbody) return;

  const lista = state.listaClassesExamesPagina || [];
  const busca = (document.getElementById('filtroTextoClassesExames')?.value || '').trim().toLowerCase();
  const filtroStatus = document.getElementById('filtroStatusExameSelect')?.value || '';

  const filtrados = lista.filter(item => {
    const matchBusca = !busca || item.nome.toLowerCase().includes(busca);
    const matchStatus = !filtroStatus
      || (filtroStatus === 'SIM' && item.tem_exame)
      || (filtroStatus === 'NAO' && !item.tem_exame);
    return matchBusca && matchStatus;
  });

  if (badgeTotal) badgeTotal.textContent = lista.length;

  if (filtrados.length === 0) {
    tbody.innerHTML = '';
    if (placeholder) placeholder.style.display = 'block';
    return;
  }

  if (placeholder) placeholder.style.display = 'none';

  tbody.innerHTML = filtrados.map((item, idx) => {
    const isClasse = item.tipo === 'CLASSE';
    const badgeRegime = isClasse
      ? '<span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1"><i class="bi bi-mortarboard me-1"></i>Classe SNE</span>'
      : '<span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="bi bi-layers me-1"></i>Nível Técnico</span>';

    const badgeExame = item.tem_exame
      ? `<button type="button" class="btn btn-sm btn-outline-danger py-0 px-2 rounded-pill fw-semibold" onclick="window.alternarExameClasseInline('${item.nome}', false)" title="Clique para alterar para Sem Exame"><i class="bi bi-file-earmark-check-fill me-1"></i>Com Exame (Sim)</button>`
      : `<button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2 rounded-pill fw-semibold" onclick="window.alternarExameClasseInline('${item.nome}', true)" title="Clique para alterar para Com Exame"><i class="bi bi-dash-circle me-1"></i>Sem Exame (Não)</button>`;

    return `
      <tr>
        <td class="text-center text-muted fw-bold">${idx + 1}</td>
        <td>
          <span class="fw-bold text-dark fs-6">${item.nome}</span>
        </td>
        <td>${badgeRegime}</td>
        <td class="text-center">${badgeExame}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-outline-primary py-1 px-2" onclick="window.abrirModalEditarClasse('${item.nome}', ${item.tem_exame})" title="Editar classe">
            <i class="bi bi-pencil-square me-1"></i>Editar
          </button>
          <button class="btn btn-sm btn-outline-danger py-1 px-2 ms-1" onclick="window.excluirClasseItem('${item.nome}')" title="Eliminar classe">
            <i class="bi bi-trash3 me-1"></i>Eliminar
          </button>
        </td>
      </tr>
    `;
  }).join('');
};

window.filtrarTabelaClassesExames = function() {
  window.renderizarTabelaClassesExamesPagina();
};

window.selecionarRegimeCurricularInstituicao = async function(novoRegime) {
  const regimeAtual = window.obterRegimeCurricularInstituicao();
  if (novoRegime === regimeAtual) return;

  const nomeLegivel = novoRegime === 'CLASSES' ? 'Classes (Ensino Geral)' : 'Níveis Técnicos';
  if (!confirm(`Deseja alterar o regime da instituição para "${nomeLegivel}"?`)) {
    const sel = document.getElementById('selectRegimeInstituicao');
    if (sel) sel.value = regimeAtual;
    return;
  }

  await window.definirRegimeCurricularInstituicao(novoRegime);
  if (typeof window.mostrarNotificacao === 'function') {
    window.mostrarNotificacao(`Regime alterado para: ${nomeLegivel}`, 'success');
  }
  await window.carregarPaginaClassesExames(true);
  if (typeof carregarDisciplinas === 'function') carregarDisciplinas();
  if (typeof carregarEscolaETurmas === 'function') carregarEscolaETurmas();
  if (typeof carregarTurmasView === 'function') carregarTurmasView();
};

window.abrirModalNovaClasse = function() {
  const regime = window.obterRegimeCurricularInstituicao();
  const isClasse = regime === 'CLASSES';

  const opcoesClassesSNE = [
    '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
    '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
  ].map(c => `<option value="${c}" ${c === '10ª Classe' ? 'selected' : ''}>${c}</option>`).join('');

  abrirModal(isClasse ? 'Cadastrar Nova Classe' : 'Cadastrar Novo Nível', `
    <form id="formModalNovaClasse" onsubmit="window.submeterNovaClasse(event)">
      <div class="mb-3">
        <label class="form-label small fw-semibold text-secondary">
          <i class="bi ${isClasse ? 'bi-mortarboard text-primary' : 'bi-layers text-success'} me-1"></i>
          ${isClasse ? 'Selecione ou digite a Classe:' : 'Nível Técnico (ex: Nível 1, Nível 2...):'}
        </label>
        ${isClasse ? `
          <select id="modalInputNomeClasse" class="form-select border-primary fw-semibold" onchange="window.aoMudarClasseNovaModal(this.value)">
            ${opcoesClassesSNE}
          </select>
        ` : `
          <div class="input-group">
            <span class="input-group-text bg-light text-success fw-bold">Nível</span>
            <input type="number" id="modalInputNumeroNivel" class="form-control border-success fw-bold" min="1" max="15" value="1" placeholder="Ex: 1">
          </div>
        `}
      </div>

      <div class="mb-4">
        <label class="form-label small fw-bold text-uppercase text-secondary mb-2">
          <i class="bi bi-patch-question text-primary me-1"></i> Tem Exame Final?
        </label>
        <div class="d-flex gap-2">
          <div class="form-check form-check-inline border rounded p-2 px-3 flex-grow-1" onclick="document.getElementById('radioExameNao').checked = true;" style="cursor: pointer;">
            <input class="form-check-input" type="radio" name="modalExameRadio" id="radioExameNao" value="nao" checked>
            <label class="form-check-label fw-semibold text-secondary small" for="radioExameNao" style="cursor: pointer;">
              <i class="bi bi-dash-circle me-1"></i> Não (Sem Exame)
            </label>
          </div>
          <div class="form-check form-check-inline border rounded p-2 px-3 flex-grow-1" onclick="document.getElementById('radioExameSim').checked = true;" style="cursor: pointer;">
            <input class="form-check-input" type="radio" name="modalExameRadio" id="radioExameSim" value="sim">
            <label class="form-check-label fw-semibold text-danger small" for="radioExameSim" style="cursor: pointer;">
              <i class="bi bi-file-earmark-check-fill me-1"></i> Sim (Com Exame)
            </label>
          </div>
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2 pt-2 border-top">
        <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
        <button type="submit" class="btn btn-primary btn-sm fw-semibold shadow-sm">
          <i class="bi bi-check-lg me-1"></i> Salvar Classe
        </button>
      </div>
    </form>
  `);

  window.aoMudarClasseNovaModal = function(val) {
    const temExamePadrao = (val === '10ª Classe' || val === '12ª Classe');
    const rSim = document.getElementById('radioExameSim');
    const rNao = document.getElementById('radioExameNao');
    if (rSim && rNao) {
      rSim.checked = temExamePadrao;
      rNao.checked = !temExamePadrao;
    }
  };
  window.aoMudarClasseNovaModal('10ª Classe');
};

window.submeterNovaClasse = async function(event) {
  if (event) event.preventDefault();
  const regime = window.obterRegimeCurricularInstituicao();
  let nomeItem = '';

  if (regime === 'CLASSES') {
    nomeItem = document.getElementById('modalInputNomeClasse')?.value || '';
  } else {
    const num = parseInt(document.getElementById('modalInputNumeroNivel')?.value || '1', 10);
    nomeItem = `Nível ${isNaN(num) || num < 1 ? 1 : num}`;
  }

  if (!nomeItem.trim()) {
    alert('Informe o nome da classe ou nível.');
    return;
  }

  const temExame = Boolean(document.getElementById('radioExameSim')?.checked);

  try {
    const res = await apiFetch('/api/v1/escola-admin/classes-exames', {
      method: 'POST',
      body: JSON.stringify({
        nome: nomeItem.trim(),
        tem_exame: temExame,
        regime: regime
      })
    });

    if (res && res.success) {
      if (typeof window.mostrarNotificacao === 'function') {
        const txt = temExame ? 'Com Exame (Sim)' : 'Sem Exame (Não)';
        window.mostrarNotificacao(`"${nomeItem}" adicionada com sucesso: ${txt}`, 'success');
      }
      fecharModal();
      await window.carregarPaginaClassesExames(true);
      if (typeof carregarDisciplinas === 'function') carregarDisciplinas();
      if (typeof carregarEscolaETurmas === 'function') carregarEscolaETurmas();
      if (typeof carregarTurmasView === 'function') carregarTurmasView();
    } else {
      alert(res?.message || 'Erro ao cadastrar.');
    }
  } catch (err) {
    alert('Erro de conexão: ' + err.message);
  }
};

window.abrirModalEditarClasse = function(nomeAtual, temExameAtual) {
  abrirModal(`Editar: ${nomeAtual}`, `
    <form id="formModalEditarClasse" onsubmit="window.submeterEdicaoClasse(event, '${nomeAtual}')">
      <div class="mb-3">
        <label class="form-label small fw-semibold text-secondary">
          <i class="bi bi-pencil-square text-primary me-1"></i> Nome da Classe / Nível:
        </label>
        <input type="text" id="modalEditNomeClasse" class="form-control fw-semibold" value="${nomeAtual}" required>
      </div>

      <div class="mb-4">
        <label class="form-label small fw-bold text-uppercase text-secondary mb-2">
          <i class="bi bi-patch-question text-primary me-1"></i> Regime de Exame Final:
        </label>
        <div class="d-flex gap-2">
          <div class="form-check form-check-inline border rounded p-2 px-3 flex-grow-1" onclick="document.getElementById('radioEditExameNao').checked = true;" style="cursor: pointer;">
            <input class="form-check-input" type="radio" name="modalEditExameRadio" id="radioEditExameNao" value="nao" ${!temExameAtual ? 'checked' : ''}>
            <label class="form-check-label fw-semibold text-secondary small" for="radioEditExameNao" style="cursor: pointer;">
              <i class="bi bi-dash-circle me-1"></i> Não (Sem Exame)
            </label>
          </div>
          <div class="form-check form-check-inline border rounded p-2 px-3 flex-grow-1" onclick="document.getElementById('radioEditExameSim').checked = true;" style="cursor: pointer;">
            <input class="form-check-input" type="radio" name="modalEditExameRadio" id="radioEditExameSim" value="sim" ${temExameAtual ? 'checked' : ''}>
            <label class="form-check-label fw-semibold text-danger small" for="radioEditExameSim" style="cursor: pointer;">
              <i class="bi bi-file-earmark-check-fill me-1"></i> Sim (Com Exame)
            </label>
          </div>
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2 pt-2 border-top">
        <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
        <button type="submit" class="btn btn-primary btn-sm fw-semibold shadow-sm">
          <i class="bi bi-check-lg me-1"></i> Salvar Alterações
        </button>
      </div>
    </form>
  `);
};

window.submeterEdicaoClasse = async function(event, nomeAntigo) {
  if (event) event.preventDefault();
  const novoNome = (document.getElementById('modalEditNomeClasse')?.value || '').trim();
  if (!novoNome) {
    alert('O nome da classe não pode estar em branco.');
    return;
  }
  const temExame = Boolean(document.getElementById('radioEditExameSim')?.checked);
  const regime = window.obterRegimeCurricularInstituicao();

  try {
    const res = await apiFetch('/api/v1/escola-admin/classes-exames', {
      method: 'POST',
      body: JSON.stringify({
        nome: novoNome,
        nome_antigo: nomeAntigo,
        tem_exame: temExame,
        regime: regime
      })
    });

    if (res && res.success) {
      if (typeof window.mostrarNotificacao === 'function') {
        window.mostrarNotificacao(`"${novoNome}" atualizada com sucesso!`, 'success');
      }
      fecharModal();
      await window.carregarPaginaClassesExames(true);
      if (typeof carregarDisciplinas === 'function') carregarDisciplinas();
      if (typeof carregarEscolaETurmas === 'function') carregarEscolaETurmas();
      if (typeof carregarTurmasView === 'function') carregarTurmasView();
    } else {
      alert(res?.message || 'Erro ao editar classe.');
    }
  } catch (err) {
    alert('Erro de conexão: ' + err.message);
  }
};

window.excluirClasseItem = async function(nome) {
  if (!confirm(`Tem certeza que deseja eliminar a classe/nível "${nome}" da instituição?`)) return;
  const regime = window.obterRegimeCurricularInstituicao();

  try {
    const res = await apiFetch('/api/v1/escola-admin/classes-exames', {
      method: 'POST',
      body: JSON.stringify({
        remover_nome: nome,
        regime: regime
      })
    });

    if (res && res.success) {
      if (typeof window.mostrarNotificacao === 'function') {
        window.mostrarNotificacao(`"${nome}" eliminada com sucesso.`, 'info');
      }
      await window.carregarPaginaClassesExames(true);
      if (typeof carregarDisciplinas === 'function') carregarDisciplinas();
      if (typeof carregarEscolaETurmas === 'function') carregarEscolaETurmas();
      if (typeof carregarTurmasView === 'function') carregarTurmasView();
    } else {
      alert(res?.message || 'Erro ao eliminar classe.');
    }
  } catch (err) {
    console.error('Erro ao eliminar:', err);
    alert('Erro de conexão ao eliminar: ' + err.message);
  }
};

window.alternarExameClasseInline = async function(nome, novoStatus) {
  const regime = window.obterRegimeCurricularInstituicao();
  try {
    const res = await apiFetch('/api/v1/escola-admin/classes-exames', {
      method: 'POST',
      body: JSON.stringify({
        nome: nome,
        tem_exame: Boolean(novoStatus),
        regime: regime
      })
    });

    if (res && res.success) {
      const txt = novoStatus ? 'Com Exame (Sim)' : 'Sem Exame (Não)';
      if (typeof window.mostrarNotificacao === 'function') {
        window.mostrarNotificacao(`"${nome}" agora: ${txt}`, 'success');
      }
      await window.carregarPaginaClassesExames(true);
      if (typeof carregarDisciplinas === 'function') carregarDisciplinas();
      if (typeof carregarEscolaETurmas === 'function') carregarEscolaETurmas();
      if (typeof carregarTurmasView === 'function') carregarTurmasView();
    }
  } catch (err) {
    console.error('Erro ao alternar exame:', err);
  }
};

// Aliases para compatibilidade
window.salvarItemClasseNivel = window.submeterNovaClasse;
window.alternarExameItemPagina = window.alternarExameClasseInline;
window.removerItemPagina = window.excluirClasseItem;
window.focarFormularioItemCurricular = window.abrirModalNovaClasse;


window.obterNiveisInstituicao = function() {
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id
    || 'padrao';
  const chave = `sige_niveis_instituicao_${escolaId}`;

  let salvos = [];
  try {
    salvos = JSON.parse(localStorage.getItem(chave) || '[]');
  } catch (_) {}

  const setNiveis = new Set([...salvos]);
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

window.renderizarOpcoesNiveisSelect = function(niveis, selecionado = '') {
  if (!niveis || niveis.length === 0) {
    return `<option value="">-- Nenhum nível cadastrado (+ Cadastrar) --</option>` +
           `<option value="__NOVO_NIVEL__">➕ + Cadastrar Nível / Classe...</option>`;
  }
  let html = niveis.map(n => `<option value="${n}" ${n === selecionado ? 'selected' : ''}>${n}</option>`).join('');
  html += `<option value="__NOVO_NIVEL__">➕ + Cadastrar Outro Nível...</option>`;
  return html;
};

window.adicionarNivelInstituicao = function(novoNivel, temExame = false) {
  if (!novoNivel) return null;
  let normalizado = novoNivel.trim();
  if (!normalizado) return null;
  if (/^\d+$/.test(normalizado)) {
    normalizado = `Nível ${normalizado}`;
  } else if (!normalizado.toLowerCase().startsWith('nível') && !normalizado.toLowerCase().startsWith('nivel') && !normalizado.toLowerCase().includes('classe')) {
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

  const cfg = window.obterClassesExamesConfig();
  cfg[normalizado] = Boolean(temExame);
  window.salvarClassesExamesConfig(cfg);

  return normalizado;
};

window.removerNivelInstituicao = async function(nomeNivel) {
  if (!confirm(`Deseja remover o "${nomeNivel}" da lista de níveis personalizados da instituição?`)) return;
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id
    || state.user?.escola_id
    || 'padrao';
  const chave = `sige_niveis_instituicao_${escolaId}`;
  let salvos = [];
  try { salvos = JSON.parse(localStorage.getItem(chave) || '[]'); } catch (_) {}
  salvos = salvos.filter(n => n !== nomeNivel);
  localStorage.setItem(chave, JSON.stringify(salvos));

  const cfg = window.obterClassesExamesConfig();
  delete cfg[nomeNivel];
  await window.salvarClassesExamesConfig(cfg);

  fecharModal();
  window.modalAdicionarNivelCurricular();
  if (typeof carregarDisciplinas === 'function') carregarDisciplinas();
  if (typeof carregarEscolaETurmas === 'function') carregarEscolaETurmas();
};

window.promptAdicionarNivelModal = function(selectId, callback) {
  abrirModal('Cadastrar Classe ou Nível Curricular', `
    <form id="formMiniAdicionarNivel">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nome da Classe ou Nível *</label>
        <input type="text" id="miniNivelNome" class="form-control" placeholder="Ex: 10ª Classe, Nível 1, Nível 2..." required autofocus>
      </div>

      <!-- OPÇÃO 2: A Classe tem Exame: Sim ou Não -->
      <div class="mb-3">
        <label class="form-label small fw-bold text-uppercase text-secondary mb-1">
          <i class="bi bi-patch-question-fill me-1 text-primary"></i> A Classe tem Exame:
        </label>
        <div class="d-flex gap-4 p-2 bg-light rounded border">
          <div class="form-check">
            <input class="form-check-input" type="radio" name="miniTemExame" id="miniTemExameSim" value="sim">
            <label class="form-check-label fw-semibold text-danger" for="miniTemExameSim">
              <i class="bi bi-file-earmark-check-fill me-1"></i> Sim (Com Exame)
            </label>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="radio" name="miniTemExame" id="miniTemExameNao" value="nao" checked>
            <label class="form-check-label fw-semibold text-secondary" for="miniTemExameNao">
              <i class="bi bi-dash-circle me-1"></i> Não (Sem Exame)
            </label>
          </div>
        </div>
        <small class="text-muted" style="font-size: 0.73rem;">Indique se os alunos realizam exame final para aprovação.</small>
      </div>

      <div class="d-flex justify-content-end gap-2 mt-4">
        <button type="button" class="btn btn-secondary" onclick="fecharModal()">Cancelar</button>
        <button type="submit" class="btn btn-success fw-semibold">
          <i class="bi bi-check-lg me-1"></i> Confirmar Cadastro
        </button>
      </div>
    </form>
  `);

  document.getElementById('formMiniAdicionarNivel').addEventListener('submit', (e) => {
    e.preventDefault();
    const nome = document.getElementById('miniNivelNome').value;
    const temExame = document.querySelector('input[name="miniTemExame"]:checked')?.value === 'sim';
    const adicionado = window.adicionarNivelInstituicao(nome, temExame);
    fecharModal();
    if (adicionado && selectId) {
      const sel = document.getElementById(selectId);
      if (sel) {
        const niveis = window.obterNiveisInstituicao();
        sel.innerHTML = window.renderizarOpcoesNiveisSelect(niveis, adicionado);
        sel.value = adicionado;
        if (typeof callback === 'function') callback(adicionado);
      }
    }
  });
};

// ==================== GESTÃO DE CLASSES/NÍVEIS E EXAMES POR DISCIPLINA ====================
window.LISTA_CLASSES_OFICIAIS = [
  '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
  '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
];

window.LISTA_NIVEIS_OFICIAIS = [
  'Nível 1', 'Nível 2', 'Nível 3', 'Nível 4', 'Nível 5', 'Nível 6', 'Nível 7', 'Nível 8'
];

window.obterRegimeInstituicao = function() {
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id || state.user?.escola_id || 'padrao';
  return localStorage.getItem(`sige_regime_instituicao_${escolaId}`) || 'CLASSES';
};

window.selecionarRegimeInstituicao = function(novoRegime) {
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id || state.user?.escola_id || 'padrao';
  localStorage.setItem(`sige_regime_instituicao_${escolaId}`, novoRegime);
  state.regimeInstituicao = novoRegime;
  state.filtroDisciplinaClasse = '';
  const nomeRegime = novoRegime === 'CLASSES' ? 'Classes (1ª à 12ª)' : 'Níveis (Nível 1, 2...)';
  if (typeof mostrarNotificacao === 'function') {
    mostrarNotificacao(`Regime da instituição definido para: ${nomeRegime}`, 'info');
  }
  carregarDisciplinas();
};


// ==================== INTERLIGAÇÃO CENTRALIZADA DE CLASSES / NÍVEIS ATIVOS ====================
window.obterClassesCurricularesAtivas = function() {
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id || state.user?.escola_id || 'padrao';
  const regime = typeof window.obterRegimeCurricularInstituicao === 'function' ? window.obterRegimeCurricularInstituicao() : 'CLASSES';

  // 1. Classes salvas na configuração de exames da instituição
  const configApi = state.escola?.config_classes_exames;
  let classesDaConfig = [];
  if (configApi && typeof configApi === 'object' && Object.keys(configApi).length > 0) {
    classesDaConfig = Object.keys(configApi);
  } else {
    try {
      const local = JSON.parse(localStorage.getItem(`sige_classes_ativas_${escolaId}`) || '[]');
      if (Array.isArray(local) && local.length > 0) classesDaConfig = local;
    } catch (_) {}
  }

  // 2. Extrair das turmas existentes na escola
  const dasTurmas = (state.todasTurmas || state.turmasList || [])
    .map(t => (t.grau_ano || '').trim())
    .filter(Boolean);

  // 3. Extrair dos alunos existentes
  const dosAlunos = (state.alunosList || [])
    .map(a => (a.classe || a.turma_grau || '').trim())
    .filter(Boolean);

  // 4. Se ainda estiver vazio, usar padrão oficial de Moçambique
  const conjunto = new Set([...classesDaConfig, ...dasTurmas, ...dosAlunos]);
  if (conjunto.size === 0) {
    const padrao = regime === 'NIVEIS'
      ? (window.LISTA_NIVEIS_OFICIAIS || ['Nível 1', 'Nível 2', 'Nível 3', 'Nível 4', 'Nível 5'])
      : (window.LISTA_CLASSES_OFICIAIS || [
          '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
          '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
        ]);
    padrao.forEach(c => conjunto.add(c));
  }

  const filtradas = Array.from(conjunto).filter(item => {
    const isNivel = /n[ií]vel/i.test(item);
    return regime === 'NIVEIS' ? isNivel : !isNivel;
  });

  return filtradas.sort((a, b) => {
    const numA = parseInt(a.replace(/\D/g, '')) || 0;
    const numB = parseInt(b.replace(/\D/g, '')) || 0;
    return numA - numB;
  });
};

window.obterClassesInstituicao = function() {
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id || state.user?.escola_id || 'padrao';
  const regime = window.obterRegimeInstituicao();

  const dasDisciplinas = (state.todasDisciplinas || [])
    .map(d => (d.classe || '').trim())
    .filter(Boolean);

  let adicionadas = [];
  try {
    adicionadas = JSON.parse(localStorage.getItem(`sige_classes_ativas_${escolaId}`) || '[]');
  } catch(_) {}

  const todas = Array.from(new Set([...dasDisciplinas, ...adicionadas]));

  const filtradas = todas.filter(item => {
    const isNivel = /n[ií]vel/i.test(item);
    return regime === 'NIVEIS' ? isNivel : !isNivel;
  });

  return filtradas.sort((a, b) => {
    const numA = parseInt(a.replace(/\D/g, '')) || 0;
    const numB = parseInt(b.replace(/\D/g, '')) || 0;
    return numA - numB;
  });
};

window.adicionarClasseInstituicao = function(nomeClasse) {
  if (!nomeClasse) return;
  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id || state.user?.escola_id || 'padrao';

  let ativas = [];
  try {
    ativas = JSON.parse(localStorage.getItem(`sige_classes_ativas_${escolaId}`) || '[]');
  } catch(_) {}

  if (!ativas.includes(nomeClasse)) {
    ativas.push(nomeClasse);
    try {
      localStorage.setItem(`sige_classes_ativas_${escolaId}`, JSON.stringify(ativas));
    } catch(_) {}
  }

  state.filtroDisciplinaClasse = nomeClasse;
  if (typeof mostrarNotificacao === 'function') {
    mostrarNotificacao(`Página da "${nomeClasse}" ativada! Adicione disciplinas e defina se têm exame (Sim ou Não).`, 'success');
  }
  carregarDisciplinas();
};

window.selecionarSubPaginaClasse = function(nomeClasse) {
  state.filtroDisciplinaClasse = nomeClasse;
  const navTabs = document.getElementById('navAbasClassesInstituicao');
  if (navTabs) {
    const botoes = navTabs.querySelectorAll('button[data-classe]');
    botoes.forEach(b => {
      const isAct = b.getAttribute('data-classe') === nomeClasse;
      b.className = `btn btn-sm ${isAct ? 'btn-primary active text-white fw-bold shadow-sm' : 'btn-outline-secondary'}`;
      const badge = b.querySelector('.badge');
      if (badge) {
        badge.className = `badge ${isAct ? 'bg-white text-primary' : 'bg-secondary text-white'} ms-1`;
      }
    });
  }
  window.renderizarSubpaginaClasseAtiva();
};

window.removerClasseDaInstituicaoAtiva = function() {
  const classeAtiva = (state.filtroDisciplinaClasse || '').trim();
  if (!classeAtiva) return;

  const vinculadas = (state.todasDisciplinas || []).filter(d => (d.classe || '').trim().toLowerCase() === classeAtiva.toLowerCase());
  if (vinculadas.length > 0) {
    alert(`Não é possível remover "${classeAtiva}" porque ela possui ${vinculadas.length} disciplina(s) cadastrada(s).\n\nElimine as disciplinas desta classe primeiro.`);
    return;
  }

  if (!confirm(`Deseja remover "${classeAtiva}" da lista de classes ativas da escola?`)) return;

  const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
    || state.tenant?.id || state.user?.escola_id || 'padrao';

  let ativas = [];
  try {
    ativas = JSON.parse(localStorage.getItem(`sige_classes_ativas_${escolaId}`) || '[]');
  } catch(_) {}

  ativas = ativas.filter(c => c.toLowerCase() !== classeAtiva.toLowerCase());
  try {
    localStorage.setItem(`sige_classes_ativas_${escolaId}`, JSON.stringify(ativas));
  } catch(_) {}

  state.filtroDisciplinaClasse = '';
  if (typeof mostrarNotificacao === 'function') {
    mostrarNotificacao(`"${classeAtiva}" removida da lista da escola.`, 'info');
  }
  carregarDisciplinas();
};

window.alternarExameDisciplina = async function(disciplinaId, novoStatus) {
  try {
    const statusBool = Boolean(novoStatus);
    const disc = (state.todasDisciplinas || []).find(x => String(x.id) === String(disciplinaId));
    if (disc && disc.tem_exame === statusBool) return;

    const res = await apiFetch(`/api/v1/disciplinas/${disciplinaId}/toggle-exame/`, {
      method: 'POST',
      body: JSON.stringify({ tem_exame: statusBool })
    });

    if (res && res.success) {
      if (disc) disc.tem_exame = statusBool;
      if (state.disciplinasFiltradasAtuais) {
        const item = state.disciplinasFiltradasAtuais.find(x => String(x.id) === String(disciplinaId));
        if (item) item.tem_exame = statusBool;
      }
      try {
        localStorage.setItem('sige_cache_disciplinas', JSON.stringify(state.todasDisciplinas));
      } catch (_) {}

      if (typeof mostrarNotificacao === 'function') {
        mostrarNotificacao(`"${disc?.nome || 'Disciplina'}": Exame definido como ${statusBool ? 'Sim (Com Exame)' : 'Não (Sem Exame)'}`, 'info');
      }
      window.renderizarSubpaginaClasseAtiva();
    } else {
      if (typeof mostrarNotificacao === 'function') {
        mostrarNotificacao(res?.message || 'Erro ao alterar critério de exame', 'danger');
      }
    }
  } catch (err) {
    console.error('Erro ao alternar exame da disciplina:', err);
    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao('Erro ao comunicar com o servidor: ' + err.message, 'danger');
    }
  }
};

window.modalNovaDisciplinaParaClasseAtiva = function() {
  const classeAtiva = state.filtroDisciplinaClasse || '';
  modalNovaDisciplina(classeAtiva);
};

window.modalNovaSeccaoAreaParaClasseAtiva = function() {
  const classeAtiva = state.filtroDisciplinaClasse || '';
  modalNovaSeccaoArea(classeAtiva);
};

window.modalAdicionarNivelCurricular = function() {
  if (typeof window.abrirModalNovaClasse === 'function') {
    window.abrirModalNovaClasse();
  }
};


function modalNovaSeccaoArea(classePredefinida = '') {
  const classesOficiais = [
    '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
    '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
  ];
  const niveisOficiais = window.obterNiveisInstituicao ? window.obterNiveisInstituicao() : ['Nível 1', 'Nível 2', 'Nível 3'];

  const classeAtiva = (classePredefinida || state.filtroDisciplinaClasse || '10ª Classe').trim();
  const isNivel = classeAtiva.toLowerCase().includes('nível') || classeAtiva.toLowerCase().includes('nivel');
  const optClasses = isNivel
    ? (typeof window.renderizarOpcoesNiveisSelect === 'function' ? window.renderizarOpcoesNiveisSelect(niveisOficiais, classeAtiva) : niveisOficiais.map(n => `<option value="${n}" ${n === classeAtiva ? 'selected' : ''}>${n}</option>`).join(''))
    : classesOficiais.map(c => `<option value="${c}" ${c === classeAtiva ? 'selected' : ''}>${c}</option>`).join('');

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
        </div>
        <select id="msaClasse" class="form-select" required>
          ${optClasses}
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nome da Secção ou Área de Estudo *</label>
        <input type="text" id="msaNome" class="form-control" placeholder="Ex: Ciências com Geografia, Ciências com Biologia, Contabilidade, Eletricidade..." required>
        <small class="text-muted">A nova secção/área aparecerá organizada na página desta classe para inclusão de disciplinas.</small>
      </div>
      <button type="submit" class="btn btn-primary w-100 fw-semibold">
        <i class="bi bi-plus-circle me-1"></i> Criar Secção / Área
      </button>
    </form>
  `);

  window.alternarRegimeModalSeccao = function(regime) {
    const sel = document.getElementById('msaClasse');
    const lbl = document.getElementById('labelMsaClasse');
    if (!sel) return;
    if (regime === 'NIVEL') {
      if (lbl) lbl.textContent = 'Nível Curricular *';
      const niveis = window.obterNiveisInstituicao ? window.obterNiveisInstituicao() : ['Nível 1', 'Nível 2', 'Nível 3'];
      sel.innerHTML = niveis.map(n => `<option value="${n}">${n}</option>`).join('');
    } else {
      if (lbl) lbl.textContent = 'Classe Correspondente *';
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

    state.filtroDisciplinaClasse = classeAlvo;
    carregarDisciplinas();

    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao(`Secção / Área "${nomeArea}" cadastrada para a ${classeAlvo}!`, 'success');
    }
  });
}

async function carregarDisciplinas() {
  const regime = window.obterRegimeInstituicao();

  // 1. Atualizar Botões de Regime no Topo
  const btnClasses = document.getElementById('btnRegimeClasses');
  const btnNiveis = document.getElementById('btnRegimeNiveis');
  const txtBtnAdd = document.getElementById('textoBtnAdicionarClasse');

  if (btnClasses && btnNiveis) {
    if (regime === 'CLASSES') {
      btnClasses.className = 'btn btn-sm btn-primary active text-white fw-bold';
      btnNiveis.className = 'btn btn-sm btn-outline-secondary';
      if (txtBtnAdd) txtBtnAdd.textContent = '+ Adicionar Classe';
    } else {
      btnClasses.className = 'btn btn-sm btn-outline-secondary';
      btnNiveis.className = 'btn btn-sm btn-success active text-white fw-bold';
      if (txtBtnAdd) txtBtnAdd.textContent = '+ Adicionar Nível';
    }
  }

  // 2. Preencher Dropdown com as Classes/Níveis Oficiais para Escolher e Adicionar
  const dropdownLista = document.getElementById('listaDropdownClassesDisponiveis');
  if (dropdownLista) {
    const listaOficial = regime === 'NIVEIS' ? window.LISTA_NIVEIS_OFICIAIS : window.LISTA_CLASSES_OFICIAIS;
    const ativas = window.obterClassesInstituicao();

    dropdownLista.innerHTML = listaOficial.map(item => {
      const jaAdicionada = ativas.some(a => a.toLowerCase() === item.toLowerCase());
      return `
        <li>
          <a class="dropdown-item d-flex justify-content-between align-items-center py-2" href="#" onclick="window.adicionarClasseInstituicao('${item}'); return false;">
            <span class="fw-semibold">${item}</span>
            ${jaAdicionada ? '<span class="badge bg-light text-muted border ms-2 small">Ativa</span>' : '<span class="badge bg-success-subtle text-success border border-success-subtle ms-2 small">+ Adicionar</span>'}
          </a>
        </li>
      `;
    }).join('');
  }

  try {
    let resD = null;
    try {
      resD = await apiFetch('/api/v1/disciplinas');
    } catch (fetchErr) {
      console.warn('Erro ao carregar disciplinas via API, verificando cache offline:', fetchErr);
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
      state.todasDisciplinas = lista;
    }
  } catch (err) {
    console.error('Erro ao buscar disciplinas na API:', err);
  }

  // 3. Atualizar Classes Ativas e Definir Classe Ativa
  const classesAtivas = window.obterClassesInstituicao();
  if (state.filtroDisciplinaClasse && !classesAtivas.some(c => c.toLowerCase() === state.filtroDisciplinaClasse.toLowerCase())) {
    state.filtroDisciplinaClasse = classesAtivas.length > 0 ? classesAtivas[0] : '';
  } else if (!state.filtroDisciplinaClasse && classesAtivas.length > 0) {
    state.filtroDisciplinaClasse = classesAtivas[0];
  }

  // 4. Renderizar Barra de Abas das Classes
  const navTabs = document.getElementById('navAbasClassesInstituicao');
  if (navTabs) {
    const classeAtiva = state.filtroDisciplinaClasse || '';
    const labelTexto = regime === 'NIVEIS' ? 'Níveis:' : 'Classes:';
    let tabsHtml = `
      <span class="small fw-bold text-uppercase text-secondary me-2">
        <i class="bi bi-mortarboard text-primary me-1"></i><span id="labelNavClasses">${labelTexto}</span>
      </span>
    `;

    if (classesAtivas.length === 0) {
      tabsHtml += `<span class="small text-muted fst-italic me-2">Nenhuma ${regime === 'NIVEIS' ? 'nível' : 'classe'} adicionada</span>`;
    } else {
      classesAtivas.forEach(c => {
        const isAct = (c.toLowerCase() === classeAtiva.toLowerCase());
        const num = (state.todasDisciplinas || []).filter(d => (d.classe || '').trim().toLowerCase() === c.toLowerCase()).length;
        tabsHtml += `
          <button type="button" data-classe="${c}" class="btn btn-sm ${isAct ? 'btn-primary active text-white fw-bold shadow-sm' : 'btn-outline-secondary'}" onclick="window.selecionarSubPaginaClasse('${c}')">
            ${c}
            <span class="badge ${isAct ? 'bg-white text-primary' : 'bg-secondary text-white'} ms-1">${num}</span>
          </button>
        `;
      });
    }
    navTabs.innerHTML = tabsHtml;
  }

  // 5. Renderizar a Sub-página da Classe Ativa (com secções/áreas e tabela de disciplinas)
  window.renderizarSubpaginaClasseAtiva();
}

window.renderizarSubpaginaClasseAtiva = function() {
  const container = document.getElementById('containerSubpaginaClasse');
  if (!container) return;

  const regime = window.obterRegimeInstituicao();
  const classesAtivas = window.obterClassesInstituicao();
  const classeAtiva = (state.filtroDisciplinaClasse || '').trim();

  // Caso 1: Nenhuma classe adicionada ainda
  if (!classeAtiva || classesAtivas.length === 0) {
    const listaOficial = regime === 'NIVEIS' ? window.LISTA_NIVEIS_OFICIAIS : window.LISTA_CLASSES_OFICIAIS;
    const nomeRotulo = regime === 'NIVEIS' ? 'Nível' : 'Classe';
    const optDropdown = listaOficial.map(item => `
      <li>
        <a class="dropdown-item py-2 fw-semibold" href="#" onclick="window.adicionarClasseInstituicao('${item}'); return false;">
          <i class="bi bi-plus-circle me-1 text-success"></i> ${item}
        </a>
      </li>
    `).join('');

    container.innerHTML = `
      <div class="card border-dashed p-5 text-center bg-light my-2 shadow-none">
        <div class="text-muted">
          <i class="bi bi-mortarboard fs-1 text-primary d-block mb-3"></i>
          <h5 class="fw-bold text-dark">Nenhuma ${nomeRotulo} Selecionada no Plano Curricular</h5>
          <p class="text-muted small mb-4" style="max-width: 540px; margin: 0 auto;">
            Para estruturar o currículo escolar, clique no botão <strong>+ Adicionar ${nomeRotulo}</strong> e selecione a classe correspondente. O sistema criará a página dessa classe com as suas secções e disciplinas organizadas.
          </p>
          <div class="dropdown d-inline-block">
            <button class="btn btn-primary btn-sm px-4 py-2 fw-bold dropdown-toggle shadow-sm" type="button" data-bs-toggle="dropdown" aria-expanded="false">
              <i class="bi bi-plus-circle me-1"></i> Adicionar Primeira ${nomeRotulo}
            </button>
            <ul class="dropdown-menu shadow">
              ${optDropdown}
            </ul>
          </div>
        </div>
      </div>
    `;
    return;
  }

  // Caso 2: Sub-página da Classe Ativa
  const todasDisciplinas = state.todasDisciplinas || [];
  const discsDaClasse = todasDisciplinas.filter(d => 
    (d.classe || '').trim().toLowerCase() === classeAtiva.toLowerCase()
  );

  const totalDiscs = discsDaClasse.length;
  const comExame = discsDaClasse.filter(d => Boolean(d.tem_exame)).length;
  const semExame = totalDiscs - comExame;

  // Áreas presentes nas disciplinas
  const areasUsadas = Array.from(new Set(discsDaClasse.map(d => (d.area || 'Ensino Geral (Tronco Comum)').trim()))).filter(Boolean);

  // Áreas personalizadas salvas para esta classe
  let customAreas = [];
  try {
    const rawCustom = localStorage.getItem(`sige_custom_areas_${classeAtiva}`);
    if (rawCustom) customAreas = JSON.parse(rawCustom);
  } catch(_) {}

  // Áreas pedagógicas oficiais do Sistema Nacional de Educação (Moçambique)
  const isEnsinoSecundario2Ciclo = /11|12/i.test(classeAtiva);
  let areasPadraoClasse = [];
  if (isEnsinoSecundario2Ciclo) {
    areasPadraoClasse = ['Ciências com Biologia', 'Ciências com Desenho', 'Letras com Geografia', 'Letras com História', 'Ensino Geral (Tronco Comum)'];
  } else if (/n[ií]vel/i.test(classeAtiva)) {
    areasPadraoClasse = ['Formação Vocacional', 'Formação Geral'];
  } else {
    areasPadraoClasse = ['Ensino Geral (Tronco Comum)'];
  }

  let listaAreasExibir = [];
  if (areasUsadas.length > 0) {
    listaAreasExibir = Array.from(new Set([...areasUsadas, ...customAreas]));
  } else {
    listaAreasExibir = Array.from(new Set([...areasPadraoClasse, ...customAreas]));
  }

  // Montar blocos das Áreas / Secções da Classe
  const cardsSeccoesHtml = listaAreasExibir.map(areaNome => {
    const discsArea = discsDaClasse.filter(d => {
      const a = (d.area || '').trim().toLowerCase();
      const ref = areaNome.trim().toLowerCase();
      if (ref.includes('geral') || ref.includes('tronco comum')) {
        return a.includes('geral') || a.includes('tronco comum') || !a;
      }
      return a === ref;
    });

    const comExameArea = discsArea.filter(d => Boolean(d.tem_exame)).length;

    let tabelaCorpo = '';
    if (discsArea.length === 0) {
      tabelaCorpo = `
        <tr>
          <td colspan="5" class="text-center py-4 text-muted">
            <i class="bi bi-info-circle me-1 text-secondary"></i> Nenhuma disciplina vinculada a esta secção ainda.
            <button class="btn btn-link btn-sm p-0 ms-2 text-decoration-none fw-semibold" onclick="modalNovaDisciplina('${classeAtiva}', '${areaNome}')">
              <i class="bi bi-plus-circle me-1"></i>+ Adicionar Disciplina nesta Secção
            </button>
          </td>
        </tr>
      `;
    } else {
      tabelaCorpo = discsArea.map(d => `
        <tr class="linha-disciplina-item" data-texto="${(d.nome + ' ' + d.codigo + ' ' + areaNome).toLowerCase()}">
          <td><code class="fw-bold text-dark fs-7">${d.codigo}</code></td>
          <td>
            <div class="fw-bold text-dark">${d.nome}</div>
            <div class="small text-muted d-sm-none">${areaNome}</div>
          </td>
          <td><span class="text-secondary fw-semibold">${d.carga_horaria} h/sem</span></td>
          <td class="text-center">
            <div class="btn-group btn-group-sm" role="group" aria-label="A Disciplina tem Exame?">
              <button type="button" class="btn btn-sm ${d.tem_exame ? 'btn-danger active text-white fw-bold shadow-sm' : 'btn-outline-secondary'}" onclick="window.alternarExameDisciplina('${d.id}', true)" title="Definir disciplina com exame: Sim">
                <i class="bi bi-check-circle-fill me-1"></i>Sim
              </button>
              <button type="button" class="btn btn-sm ${!d.tem_exame ? 'btn-secondary active text-white fw-bold shadow-sm' : 'btn-outline-secondary'}" onclick="window.alternarExameDisciplina('${d.id}', false)" title="Definir disciplina sem exame: Não">
                Não
              </button>
            </div>
          </td>
          <td class="text-end">
            <div class="d-inline-flex gap-1">
              <button class="btn btn-outline-primary btn-sm py-0 px-2" onclick="modalEditarDisciplina('${d.id}')" title="Editar Disciplina">
                <i class="bi bi-pencil-square"></i>
              </button>
              <button class="btn btn-outline-danger btn-sm py-0 px-2" onclick="eliminarDisciplina('${d.id}', '${(d.nome || '').replace(/'/g, "\\'")}')" title="Eliminar Disciplina">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </td>
        </tr>
      `).join('');
    }

    const iconeArea = /ci[êe]ncias/i.test(areaNome)
      ? 'bi-activity'
      : /letras/i.test(areaNome)
        ? 'bi-journal-richtext'
        : /vocacional|t[ée]cnic/i.test(areaNome)
          ? 'bi-tools'
          : 'bi-diagram-3-fill';

    return `
      <div class="card mb-3 shadow-none border area-seccao-card">
        <div class="card-header bg-white py-2 px-3 border-bottom d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div class="d-flex align-items-center gap-2">
            <i class="bi ${iconeArea} text-primary fs-6"></i>
            <h6 class="fw-bold mb-0 text-dark">${areaNome}</h6>
            <span class="badge bg-light text-secondary border small">${discsArea.length} disciplina(s)</span>
            ${comExameArea > 0 ? `<span class="badge bg-danger-subtle text-danger border border-danger-subtle small"><i class="bi bi-file-earmark-check-fill me-1"></i>${comExameArea} com Exame</span>` : ''}
          </div>
          <div>
            <button class="btn btn-sm btn-outline-primary py-1 px-2 fw-semibold" onclick="modalNovaDisciplina('${classeAtiva}', '${areaNome}')" title="Cadastrar nova disciplina nesta secção">
              <i class="bi bi-plus-lg me-1"></i>+ Disciplina
            </button>
          </div>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light small text-uppercase text-secondary">
              <tr>
                <th style="width: 120px;">Código</th>
                <th>Disciplina</th>
                <th style="width: 140px;">Carga Horária</th>
                <th style="width: 190px;" class="text-center">A Disciplina tem Exame?</th>
                <th class="text-end" style="width: 110px;">Ações</th>
              </tr>
            </thead>
            <tbody>
              ${tabelaCorpo}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <!-- Cabeçalho da Sub-página da Classe -->
    <div class="card bg-light border p-3 mb-3 shadow-none">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div>
          <div class="d-flex align-items-center gap-2 mb-1">
            <span class="badge bg-primary px-3 py-2 fs-6 shadow-sm">
              <i class="bi bi-mortarboard me-1"></i>${classeAtiva}
            </span>
            <h5 class="fw-bold mb-0 text-dark">Plano Curricular & Secções</h5>
          </div>
          <p class="text-muted small mb-0">
            Disciplinas em função da área/secção correspondente ao plano curricular da <strong>${classeAtiva}</strong>. Defina se têm Exame (Sim ou Não).
          </p>
        </div>

        <!-- Indicadores Rápidos (KPIs) -->
        <div class="d-flex align-items-center gap-2 flex-wrap">
          <span class="badge bg-white text-dark border px-2 py-1 small">
            <i class="bi bi-book me-1 text-primary"></i><strong>${totalDiscs}</strong> Disciplinas
          </span>
          <span class="badge bg-danger text-white px-2 py-1 small shadow-sm">
            <i class="bi bi-file-earmark-check-fill me-1"></i><strong>${comExame}</strong> Com Exame
          </span>
          <span class="badge bg-secondary text-white px-2 py-1 small shadow-sm">
            <i class="bi bi-dash-circle me-1"></i><strong>${semExame}</strong> Sem Exame
          </span>
        </div>
      </div>

      <!-- Barra de Ferramentas da Classe: Busca e Ações -->
      <div class="row g-2 align-items-center mt-2 pt-2 border-top">
        <div class="col-md-5">
          <div class="input-group input-group-sm">
            <span class="input-group-text bg-white"><i class="bi bi-search text-muted"></i></span>
            <input type="search" id="filtroDisciplinasBusca" class="form-control" placeholder="Pesquisar disciplina por nome ou código nesta classe..." oninput="filtrarDisciplinasTabelaTexto()" onsearch="filtrarDisciplinasTabelaTexto()">
          </div>
        </div>
        <div class="col-md-7 d-flex justify-content-md-end gap-2 flex-wrap">
          <button class="btn btn-sm btn-primary fw-semibold shadow-sm" onclick="modalNovaDisciplinaParaClasseAtiva()">
            <i class="bi bi-plus-circle me-1"></i>+ Adicionar Disciplina nesta Classe
          </button>
          <button class="btn btn-sm btn-outline-primary fw-semibold" onclick="modalNovaSeccaoAreaParaClasseAtiva()">
            <i class="bi bi-diagram-3 me-1"></i>+ Nova Secção / Área
          </button>
          <button class="btn btn-sm btn-outline-danger" onclick="removerClasseDaInstituicaoAtiva()" title="Remover esta classe da lista da escola se não houver disciplinas cadastradas">
            <i class="bi bi-trash me-1"></i>Remover Classe
          </button>
        </div>
      </div>
    </div>

    <!-- Lista de Áreas / Secções da Classe com as suas Disciplinas -->
    <div id="listaSeccoesAreasContainer">
      ${cardsSeccoesHtml}
    </div>

    <!-- Botão Inferior para Criar Nova Secção/Área -->
    <div class="text-center mt-3 pt-2">
      <button class="btn btn-outline-secondary btn-sm px-4 py-2 border-dashed fw-semibold" onclick="modalNovaSeccaoAreaParaClasseAtiva()">
        <i class="bi bi-plus-circle me-1 text-primary"></i> + Adicionar Outra Secção / Área de Estudo na ${classeAtiva}
      </button>
    </div>
  `;
};

function modalNovaDisciplina(classePredefinida = '', areaPredefinida = '') {
  const regime = window.obterRegimeInstituicao();
  const classesLista = regime === 'NIVEIS' ? window.LISTA_NIVEIS_OFICIAIS : window.LISTA_CLASSES_OFICIAIS;

  const classeInicial = classePredefinida || state.filtroDisciplinaClasse || classesLista[0];

  let areasIniciais = typeof window.obterTodasAreasOficiais === 'function'
    ? window.obterTodasAreasOficiais(classeInicial)
    : ['Ensino Geral (Tronco Comum)', 'Ciências com Biologia', 'Ciências com Desenho', 'Letras com Geografia', 'Letras com História'];

  if (areaPredefinida && !areasIniciais.some(a => a.toLowerCase() === areaPredefinida.toLowerCase())) {
    areasIniciais.unshift(areaPredefinida);
  }

  const optAreas = areasIniciais.map(a => 
    `<option value="${a}" ${(areaPredefinida && a.toLowerCase() === areaPredefinida.toLowerCase()) ? 'selected' : ''}>${a}</option>`
  ).join('');

  const optClassesHtml = classesLista.map(c => 
    `<option value="${c}" ${c === classeInicial ? 'selected' : ''}>${c}</option>`
  ).join('');

  abrirModal('Nova Disciplina Curricular', `
    <form id="formModalDisc">
      <div class="row g-3">
        <div class="col-md-8">
          <label class="form-label small fw-semibold">Nome da Disciplina *</label>
          <input type="text" id="mdNome" class="form-control" required placeholder="Ex: Língua Portuguesa, Matemática, Física, TIC's...">
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold">Código Curricular *</label>
          <input type="text" id="mdCodigo" class="form-control" required placeholder="Ex: MAT-10, PORT-10, TEC-N1">
        </div>

        <div class="col-md-6">
          <label class="form-label small fw-semibold mb-1" id="labelMdClasse">${regime === 'NIVEIS' ? 'Nível Curricular *' : 'Classe *'}</label>
          <select id="mdClasse" class="form-select" required onchange="aoMudarClasseModalNovaDisc(this.value)">
            ${optClassesHtml}
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
          <input type="number" id="mdCarga" class="form-control" value="4" min="1" max="40" required>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-semibold">Ano Lectivo</label>
          <input type="text" id="mdAnoLetivo" class="form-control" value="2026" required>
        </div>

        <!-- DEFINIÇÃO OBRIGATÓRIA: A Disciplina tem Exame: Sim ou Não -->
        <div class="col-12 mt-2">
          <div class="p-3 bg-light rounded border">
            <label class="form-label small fw-bold text-uppercase text-secondary mb-2">
              <i class="bi bi-question-circle-fill me-1 text-primary"></i> A Disciplina tem Exame:
            </label>
            <div class="d-flex gap-4">
              <div class="form-check">
                <input class="form-check-input" type="radio" name="mdTemExame" id="mdTemExameSim" value="true">
                <label class="form-check-label fw-bold text-danger small" for="mdTemExameSim">
                  <i class="bi bi-file-earmark-check-fill me-1"></i> Sim (Com Exame)
                </label>
              </div>
              <div class="form-check">
                <input class="form-check-input" type="radio" name="mdTemExame" id="mdTemExameNao" value="false" checked>
                <label class="form-check-label fw-bold text-secondary small" for="mdTemExameNao">
                  <i class="bi bi-dash-circle me-1"></i> Não (Sem Exame)
                </label>
              </div>
            </div>
            <div class="form-text small mt-1 text-muted">
              Defina se os alunos desta classe realizam Exame nesta disciplina específica (ex: Matemática: Sim; TIC's: Não).
            </div>
          </div>
        </div>
      </div>
      <button type="submit" class="btn btn-primary w-100 mt-4 fw-semibold"><i class="bi bi-plus-circle me-1"></i> Criar Disciplina no Plano Curricular</button>
    </form>
  `);

  window.aoMudarClasseModalNovaDisc = function(novaClasse) {
    const selArea = document.getElementById('mdArea');
    if (!selArea) return;
    const areas = typeof window.obterTodasAreasOficiais === 'function'
      ? window.obterTodasAreasOficiais(novaClasse)
      : ['Ensino Geral (Tronco Comum)'];
    selArea.innerHTML = areas.map(a => `<option value="${a}">${a}</option>`).join('');
  };

  document.getElementById('formModalDisc').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const nomeVal = document.getElementById('mdNome').value.trim();
      const codigoVal = document.getElementById('mdCodigo').value.trim();
      const classeVal = document.getElementById('mdClasse').value;
      const areaVal = document.getElementById('mdArea').value;
      const temExameVal = document.querySelector('input[name="mdTemExame"]:checked')?.value === 'true';

      const body = {
        nome: nomeVal,
        codigo: codigoVal,
        classe: classeVal,
        area: areaVal,
        carga_horaria: Number(document.getElementById('mdCarga').value),
        ano_letivo: document.getElementById('mdAnoLetivo').value || '2026',
        tem_exame: temExameVal
      };

      const res = await apiFetch('/api/v1/disciplinas', {
        method: 'POST',
        body: JSON.stringify(body)
      });

      if (res && res.success) {
        const escolaId = (state.user?.role === 'SUPERADMIN' ? localStorage.getItem('sige_selected_tenant') : null)
          || state.tenant?.id || state.user?.escola_id || 'padrao';
        let ativas = [];
        try { ativas = JSON.parse(localStorage.getItem(`sige_classes_ativas_${escolaId}`) || '[]'); } catch(_) {}
        if (!ativas.includes(classeVal)) {
          ativas.push(classeVal);
          try { localStorage.setItem(`sige_classes_ativas_${escolaId}`, JSON.stringify(ativas)); } catch(_) {}
        }

        fecharModal();
        state.filtroDisciplinaClasse = classeVal;
        await carregarDisciplinas();
        if (typeof mostrarNotificacao === 'function') {
          mostrarNotificacao(`Disciplina "${nomeVal}" criada com sucesso na página da ${classeVal}! (Exame: ${temExameVal ? 'Sim' : 'Não'})`, 'success');
        }
      } else {
        alert(res?.message || 'Erro ao criar disciplina');
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

    const regime = window.obterRegimeInstituicao();
    const classesLista = regime === 'NIVEIS' ? window.LISTA_NIVEIS_OFICIAIS : window.LISTA_CLASSES_OFICIAIS;
    const classeVal = (d.classe || '').trim();

    const listaOpcoes = [...classesLista];
    if (classeVal && !listaOpcoes.includes(classeVal)) {
      listaOpcoes.push(classeVal);
    }

    const optOpcoes = listaOpcoes.map(c => 
      `<option value="${c}" ${c === classeVal ? 'selected' : ''}>${c}</option>`
    ).join('');

    const areasDisponiveis = typeof window.obterTodasAreasOficiais === 'function'
      ? window.obterTodasAreasOficiais(d.classe)
      : ['Ensino Geral (Tronco Comum)'];
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
            <label class="form-label small fw-semibold mb-1" id="labelMdeClasse">${regime === 'NIVEIS' ? 'Nível Curricular *' : 'Classe *'}</label>
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
            <input type="number" id="mdeCarga" class="form-control" value="${d.carga_horaria || 4}" min="1" max="40" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Ano Lectivo</label>
            <input type="text" id="mdeAnoLetivo" class="form-control" value="${d.ano_letivo || '2026'}" required>
          </div>

          <!-- DEFINIÇÃO OBRIGATÓRIA: A Disciplina tem Exame: Sim ou Não -->
          <div class="col-12 mt-2">
            <div class="p-3 bg-light rounded border">
              <label class="form-label small fw-bold text-uppercase text-secondary mb-2">
                <i class="bi bi-question-circle-fill me-1 text-primary"></i> A Disciplina tem Exame:
              </label>
              <div class="d-flex gap-4">
                <div class="form-check">
                  <input class="form-check-input" type="radio" name="mdeTemExame" id="mdeTemExameSim" value="true" ${d.tem_exame ? 'checked' : ''}>
                  <label class="form-check-label fw-bold text-danger small" for="mdeTemExameSim">
                    <i class="bi bi-file-earmark-check-fill me-1"></i> Sim (Com Exame)
                  </label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="radio" name="mdeTemExame" id="mdeTemExameNao" value="false" ${!d.tem_exame ? 'checked' : ''}>
                  <label class="form-check-label fw-bold text-secondary small" for="mdeTemExameNao">
                    <i class="bi bi-dash-circle me-1"></i> Não (Sem Exame)
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="d-flex gap-2 justify-content-end mt-4">
          <button type="button" class="btn btn-light btn-sm" onclick="fecharModal()">Cancelar</button>
          <button type="submit" class="btn btn-primary btn-sm px-4 fw-semibold">Salvar Alterações</button>
        </div>
      </form>
    `);

    window.aoMudarClasseModalEditarDisc = function(novaClasse) {
      const selArea = document.getElementById('mdeArea');
      if (!selArea) return;
      const areas = typeof window.obterTodasAreasOficiais === 'function'
        ? window.obterTodasAreasOficiais(novaClasse)
        : ['Ensino Geral (Tronco Comum)'];
      selArea.innerHTML = areas.map(a => `<option value="${a}">${a}</option>`).join('');
    };

    document.getElementById('formModalEditarDisc').addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const temExameVal = document.querySelector('input[name="mdeTemExame"]:checked')?.value === 'true';
        const body = {
          nome: document.getElementById('mdeNome').value.trim(),
          codigo: document.getElementById('mdeCodigo').value.trim(),
          classe: document.getElementById('mdeClasse').value,
          area: document.getElementById('mdeArea').value,
          carga_horaria: Number(document.getElementById('mdeCarga').value),
          ano_letivo: document.getElementById('mdeAnoLetivo').value || '2026',
          tem_exame: temExameVal
        };
        const updRes = await apiFetch(`/api/v1/disciplinas/${disciplinaId}`, {
          method: 'PUT',
          body: JSON.stringify(body)
        });
        if (updRes && updRes.success) {
          if (typeof mostrarNotificacao === 'function') {
            mostrarNotificacao('Disciplina actualizada com sucesso!', 'success');
          }
          fecharModal();
          carregarDisciplinas();
        } else {
          alert(updRes?.message || 'Erro ao actualizar disciplina');
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
    const wrapperBotoes = document.getElementById('containerBotoesTurmasCadernetaWrapper');
    if (wrapperBotoes) wrapperBotoes.style.setProperty('display', 'none', 'important');
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
    const wrapperBotoes = document.getElementById('containerBotoesTurmasCadernetaWrapper');
    if (wrapperBotoes) wrapperBotoes.style.setProperty('display', 'none', 'important');
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

  // Renderizar botões rápidos de turmas para abertura direta ao clicar
  const wrapperBotoes = document.getElementById('containerBotoesTurmasCadernetaWrapper');
  const containerBotoes = document.getElementById('containerBotoesTurmasCaderneta');
  if (wrapperBotoes && containerBotoes) {
    wrapperBotoes.style.setProperty('display', 'flex', 'important');
    containerBotoes.innerHTML = alocsArea.map(a => {
      const isActiva = a.id === state.cadernetaAlocacaoSelecionadaId;
      const btnCls = isActiva ? 'btn-primary shadow-sm' : 'btn-outline-primary bg-white';
      const turmaNome = a.turma?.nome || a.turma_nome || 'Turma';
      const discNome = a.disciplina?.nome || a.disciplina_nome || '';
      return `
        <button type="button" class="btn btn-sm ${btnCls} fw-bold py-1 px-3 d-inline-flex align-items-center gap-1 turma-caderneta-btn"
                data-aloc-id="${a.id}"
                onclick="selecionarAlocacaoCaderneta('${a.id}')"
                title="Clique para abrir ou visualizar a caderneta de ${turmaNome}">
          <i class="bi bi-people-fill small"></i>
          <span>${turmaNome}</span>
          ${discNome ? `<span class="badge ${isActiva ? 'bg-light text-primary' : 'bg-primary-subtle text-primary border'} ms-1 small" style="font-size: 0.7rem;">${discNome}</span>` : ''}
        </button>
      `;
    }).join('');
  }

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

  // Actualizar estado activo dos botões de turmas
  document.querySelectorAll('.turma-caderneta-btn').forEach(btn => {
    const isActiva = btn.getAttribute('data-aloc-id') === alocId;
    if (isActiva) {
      btn.className = 'btn btn-sm btn-primary shadow-sm fw-bold py-1 px-3 d-inline-flex align-items-center gap-1 turma-caderneta-btn';
      const badge = btn.querySelector('.badge');
      if (badge) badge.className = 'badge bg-light text-primary ms-1 small';
    } else {
      btn.className = 'btn btn-sm btn-outline-primary bg-white fw-bold py-1 px-3 d-inline-flex align-items-center gap-1 turma-caderneta-btn';
      const badge = btn.querySelector('.badge');
      if (badge) badge.className = 'badge bg-primary-subtle text-primary border ms-1 small';
    }
  });

  carregarCadernetaDocente(alocId);
};

window.selecionarAlocacaoCaderneta = function(alocacaoId) {
  const sel = document.getElementById('selectCadernetaAlocacao');
  if (sel) sel.value = alocacaoId;
  aoMudarSelectAlocacaoCaderneta(alocacaoId);
};

function limparCabecalhoCaderneta() {
  const wrapperBotoes = document.getElementById('containerBotoesTurmasCadernetaWrapper');
  if (wrapperBotoes) wrapperBotoes.style.setProperty('display', 'none', 'important');
  const containerBotoes = document.getElementById('containerBotoesTurmasCaderneta');
  if (containerBotoes) containerBotoes.innerHTML = '';
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
  const alocId = await obterAlocacaoAtivaOuPrimeira();
  if (!alocId) return;
  const url = `/api/v1/professores/caderneta/${alocId}/xlsx`;
  await downloadFicheiroBinario(url, `Caderneta_Oficial_2026.xlsx`);
}

function imprimirCadernetaOficial() {
  window.print();
}

// descarregarCadernetaPdf já está definido globalmente chamando /api/v1/professores/caderneta/:id/pdf

async function modalSalvarNotaCaderneta(alunoIdPreSelecionado = null) {
  if (!state.alocacaoAtualId) return alert('Selecione uma turma e disciplina');

  const periodoFiltro = document.getElementById('cadernetaPeriodoSelect')?.value;
  const periodo = (periodoFiltro && periodoFiltro !== 'TODOS') ? periodoFiltro : '1_TRIMESTRE';
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
    selectPeriodo.addEventListener('change', () => carregarNotasAlunoNoModal(selectAluno ? selectAluno.value : alunoIdInicial));
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

// ==================== 8. PAUTAS GERAIS & ACTAS OFICIAIS ====================
let subAbaPautaAtiva = 'pauta';

function mudarSubAbaPauta(aba) {
  subAbaPautaAtiva = aba;
  const btnPauta = document.getElementById('btnAbaPauta');
  const btnActa = document.getElementById('btnAbaActa');
  const viewPauta = document.getElementById('subViewPautaGeral');
  const viewActa = document.getElementById('subViewActaConselho');

  if (aba === 'pauta') {
    btnPauta?.classList.add('active');
    btnActa?.classList.remove('active');
    viewPauta?.classList.remove('d-none');
    viewActa?.classList.add('d-none');
  } else {
    btnActa?.classList.add('active');
    btnPauta?.classList.remove('active');
    viewActa?.classList.remove('d-none');
    viewPauta?.classList.add('d-none');
  }
  alternarVisualizacaoPautaTurma();
}

async function carregarPautas(anoParam, forcarBusca = false) {
  // Nao buscar dados automaticamente — aguardar accao explicita do utilizador (clicar Buscar).
  if (!forcarBusca && !anoParam) {
    const selectTurma = document.getElementById('pautaTurmaSelect');
    if (selectTurma) selectTurma.innerHTML = '<option value="">-- Selecione o Ano e clique em Buscar --</option>';
    const ph = `<div class="text-center py-5 text-muted"><i class="bi bi-calendar2-check display-4 d-block mb-3 opacity-50"></i><p class="fw-semibold">Selecione o <strong>Ano Lectivo</strong> e clique em <strong>Buscar</strong> para visualizar os dados.</p></div>`;
    const containerPauta = document.getElementById('containerTabelaPautaGeral');
    if (containerPauta) containerPauta.innerHTML = ph;
    const containerActa = document.getElementById('containerActaConselhoCorpo');
    if (containerActa) containerActa.innerHTML = ph;
    return;
  }
  try {
    const selAno = document.getElementById('pautaAnoSelect');
    const ano = anoParam || (selAno ? selAno.value : null) || state.anoLectivoVisualizacao || localStorage.getItem('sige_ano_letivo_selecionado') || state.tenant?.ano_letivo_ativo || '2026';
    const queryAno = (ano && ano !== 'TODOS') ? `?ano_letivo=${encodeURIComponent(ano)}` : '';
    const resTurmas = await apiFetch(`/api/v1/escola-admin/turmas${queryAno}`);
    const selectTurma = document.getElementById('pautaTurmaSelect');
    if (!selectTurma) return;

    if (resTurmas.success && resTurmas.data.length > 0) {
      selectTurma.innerHTML = resTurmas.data.map(t => 
        `<option value="${t.id}">${t.grau_ano} &rarr; ${t.nome} (${normalizarArea(t.area || 'Geral')})</option>`
      ).join('');
      alternarVisualizacaoPautaTurma();
    } else {
      selectTurma.innerHTML = '<option value="">Nenhuma turma cadastrada</option>';
    }
  } catch (err) {
    console.error('Erro ao carregar turmas na pauta:', err);
  }
}

async function alternarVisualizacaoPautaTurma() {
  const turmaId = document.getElementById('pautaTurmaSelect')?.value;
  if (!turmaId) return;

  if (subAbaPautaAtiva === 'pauta') {
    await carregarPautaGeral(turmaId);
  } else {
    await carregarActaConselho(turmaId);
  }
}

async function carregarPautaGeral(turmaId) {
  const container = document.getElementById('containerTabelaPautaGeral');
  if (!container) return;
  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar pauta geral da turma...</p></div>';

  try {
    const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/completa`);
    if (!res || !res.success) {
      container.innerHTML = '<div class="alert alert-warning text-center py-3">Não foi possível carregar a pauta para esta turma.</div>';
      return;
    }
    const d = res.data || res;

    const turmaNome = d.turma?.nome || 'Turma';
    const turmaGrau = d.turma?.grau_ano || '';
    const turmaArea = d.turma?.area || '';
    const areaTxt = turmaArea && !['geral', 'ensino geral', 'tronco comum'].includes(turmaArea.toLowerCase()) ? ` — Área: ${turmaArea}` : '';
    const anoLetivo = d.turma?.ano_letivo || '2026';
    const turno = d.turma?.turno || 'Diurno';
    const dirTurma = d.turma?.director_turma || 'Direcção Pedagógica';
    const dirTel = d.turma?.director_turma_tel ? ` (${d.turma.director_turma_tel})` : '';

    const elTitulo = document.getElementById('pautaGeralTitulo');
    if (elTitulo) elTitulo.textContent = `Pauta Oficial de Aproveitamento Pedagógico — ${turmaNome} (${turmaGrau}${areaTxt})`;

    const elSubtitulo = document.getElementById('pautaGeralSubtitulo');
    if (elSubtitulo) elSubtitulo.textContent = `Ano Lectivo: ${anoLetivo} | Turno: ${turno} | Director de Turma: ${dirTurma}${dirTel}`;

    const formatNota = (val) => {
      if (val === null || val === undefined || val === '' || val === '-' || isNaN(Number(val))) return '<span class="text-muted">-</span>';
      const num = Number(val);
      const cls = num >= 9.5 ? 'nota-positiva' : 'nota-negativa';
      return `<span class="${cls}">${Number.isInteger(num) ? num : num.toFixed(1)}</span>`;
    };

    const disciplinas = Array.isArray(d.disciplinas) ? d.disciplinas : [];
    const alunos = Array.isArray(d.alunos) ? d.alunos : [];

    const thDisciplinas = disciplinas.map(disc => 
      `<th colspan="4" class="text-center bg-primary bg-opacity-10 text-primary border-start border-end fw-bold" style="font-size: 0.75rem;">${disc.nome || disc.codigo}</th>`
    ).join('');

    const thSubDisciplinas = disciplinas.map(() => 
      `<th style="font-size: 0.65rem;">1º</th><th style="font-size: 0.65rem;">2º</th><th style="font-size: 0.65rem;">3º</th><th style="font-size: 0.65rem;" class="bg-light fw-bold">MFD</th>`
    ).join('');

    const colSpanTotal = 2 + (disciplinas.length * 4) + 9;

    let trsAlunos = '';
    if (alunos.length === 0) {
      trsAlunos = `
        <tr>
          <td colspan="${colSpanTotal}" class="text-center py-5 text-muted">
            <i class="bi bi-people display-6 d-block mb-2 text-secondary opacity-50"></i>
            <span class="fw-semibold">Nenhum aluno matriculado nesta turma (zero alunos na pauta).</span>
            <p class="small mb-0 mt-1">Matricule ou aloque alunos a esta turma para visualizar notas e médias na pauta geral.</p>
          </td>
        </tr>
      `;
    } else {
      trsAlunos = alunos.map(a => {
        const notasDisc = a.notasDisciplinas || a.notas || {};
        const tdDisciplinas = disciplinas.map(disc => {
          const nd = notasDisc[disc.codigo || disc.id] || notasDisc[disc.id] || notasDisc[disc.nome] || {};
          return `
            <td>${formatNota(nd.t1)}</td>
            <td>${formatNota(nd.t2)}</td>
            <td>${formatNota(nd.t3)}</td>
            <td class="bg-light fw-bold">${(nd.t1 !== '-' && nd.t2 !== '-' && nd.t3 !== '-' && nd.t1 !== null && nd.t2 !== null && nd.t3 !== null && Number(nd.t1) > 0 && Number(nd.t2) > 0 && Number(nd.t3) > 0) ? formatNota(nd.mfd) : '<span class="text-muted">-</span>'}</td>
          `;
        }).join('');

        let badgeResultado = '';
        const resTexto = (a.resultadoFinal || a.resultado || '').trim();
        if (resTexto === 'A' || resTexto === 'Aprovado') {
          badgeResultado = '<span class="fw-bold text-dark" style="font-weight: 700; color: #000000 !important;">Aprovado</span>';
        } else if (resTexto === 'R' || resTexto === 'Reprovado') {
          badgeResultado = '<span class="fw-bold text-danger" style="font-weight: 700; color: #dc2626 !important;">Reprovado</span>';
        } else if (resTexto === 'D' || resTexto === 'Desistente') {
          badgeResultado = '<span class="fw-bold text-secondary">Desistente</span>';
        } else if (resTexto === 'T' || resTexto === 'Transferido') {
          badgeResultado = '<span class="fw-bold text-secondary">Transferido</span>';
        } else {
          badgeResultado = `<span class="fw-bold text-secondary">${resTexto || '-'}</span>`;
        }

        const nomeCompleto = (a.nomeCompleto || `${a.nome || ''} ${a.apelido || ''}`).trim() || 'Sem Nome';
        const isFem = (a.genero || 'M').toUpperCase().startsWith('F');

        return `
          <tr>
            <td class="text-start ps-3 fw-semibold">${nomeCompleto}</td>
            <td><span class="badge ${isFem ? 'bg-info text-white' : 'bg-secondary text-white'}" style="min-width: 22px;">${isFem ? 'F' : 'M'}</span></td>
            ${tdDisciplinas}
            <td class="bg-light">${formatNota(a.mediasTrimestrais?.t1)}</td>
            <td class="bg-light">${formatNota(a.mediasTrimestrais?.t2)}</td>
            <td class="bg-light">${formatNota(a.mediasTrimestrais?.t3)}</td>
            <td>${a.negativas?.t1 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t1}</span>` : '0'}</td>
            <td>${a.negativas?.t2 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t2}</span>` : '0'}</td>
            <td>${a.negativas?.t3 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t3}</span>` : '0'}</td>
            <td class="bg-light">${(a.negativas?.fimDoAno || 0) > 0 ? `<span class="text-danger fw-bold">${a.negativas.fimDoAno}</span>` : '0'}</td>
            <td class="bg-primary bg-opacity-10 fw-bold fs-6">${formatNota(a.mediaFinalGeral)}</td>
            <td>${badgeResultado}</td>
          </tr>
        `;
      }).join('');
    }

    const est = d.estatistica || {};
    const totalInscritos = est.inscritos?.total ?? est.totalAlunos ?? alunos.length;
    const homensInscritos = est.inscritos?.h ?? est.homens ?? alunos.filter(a => !(a.genero || '').toUpperCase().startsWith('F')).length;
    const mulheresInscritos = est.inscritos?.m ?? est.mulheres ?? alunos.filter(a => (a.genero || '').toUpperCase().startsWith('F')).length;
    const totalAvaliados = est.avaliados?.total ?? totalInscritos;
    const aprovadosTotal = typeof est.aprovados === 'object' ? (est.aprovados?.total ?? 0) : (est.aprovados ?? 0);
    const aprovadosPct = typeof est.aprovados === 'object' ? (est.aprovados?.pct ?? 0) : (est.taxaAprovacao ?? 0);
    const reprovadosTotal = typeof est.reprovados === 'object' ? (est.reprovados?.total ?? 0) : (est.reprovados ?? 0);
    const reprovadosPct = typeof est.reprovados === 'object' ? (est.reprovados?.pct ?? 0) : (est.taxaReprovacao ?? 0);

    container.innerHTML = `
      <table class="table table-bordered table-hover align-middle text-center small pauta-tabela" style="min-width: 1400px;">
        <thead class="table-light">
          <tr>
            <th rowspan="2" class="align-middle text-start ps-3" style="min-width: 170px;">Nome Completo do Aluno</th>
            <th rowspan="2" class="align-middle" style="width: 45px;">Gén</th>
            ${thDisciplinas}
            <th colspan="3" class="bg-secondary bg-opacity-10 fw-bold" style="font-size: 0.72rem;">Médias Trimestrais</th>
            <th colspan="4" class="bg-secondary bg-opacity-10 fw-bold" style="font-size: 0.72rem;">Disciplinas Negativas</th>
            <th rowspan="2" class="align-middle bg-primary text-white fw-bold" style="width: 70px;">Média<br>Geral</th>
            <th rowspan="2" class="align-middle bg-secondary text-white fw-bold" style="width: 85px;">Resultado</th>
          </tr>
          <tr>
            ${thSubDisciplinas}
            <th style="font-size: 0.68rem;">1º</th>
            <th style="font-size: 0.68rem;">2º</th>
            <th style="font-size: 0.68rem;">3º</th>
            <th style="font-size: 0.68rem;">1º</th>
            <th style="font-size: 0.68rem;">2º</th>
            <th style="font-size: 0.68rem;">3º</th>
            <th style="font-size: 0.68rem;" class="bg-light fw-bold" title="Total de Disciplinas Negativas">Total</th>
          </tr>
        </thead>
        <tbody>
          ${trsAlunos}
        </tbody>
        <tfoot class="table-light">
          <tr class="table-secondary fw-bold text-start">
            <td colspan="${colSpanTotal}" class="ps-3 py-2">
              <div class="d-flex flex-wrap gap-4 align-items-center">
                <span>Total Inscritos: <strong>${totalInscritos}</strong> (H: ${homensInscritos} | M: ${mulheresInscritos})</span>
                <span>Avaliados: <strong>${totalAvaliados}</strong></span>
                <span class="text-success">Aprovados: <strong>${aprovadosTotal}</strong> (${aprovadosPct}%)</span>
                <span class="text-danger">Reprovados: <strong>${reprovadosTotal}</strong> (${reprovadosPct}%)</span>
              </div>
            </td>
          </tr>
        </tfoot>
      </table>
    `;
  } catch (err) {
    console.error('Erro ao carregar pauta geral da turma:', err);
    container.innerHTML = `<div class="alert alert-danger">Erro ao carregar pauta geral da turma: ${err.message || err}</div>`;
  }
}

async function carregarActaConselho(turmaId) {
  const container = document.getElementById('containerActaConselhoCorpo');
  if (!container) return;
  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar acta do conselho de avaliação...</p></div>';

  try {
    const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
    let cp = {};
    if (savedParamsRaw) {
      try {
        cp = JSON.parse(savedParamsRaw) || {};
        // Se continha os dados fictícios hardcoded de demonstração antigos, limpar para não poluir
        if (cp.dataT1 === '26/05/2026' && cp.dataT2 === '01/09/2026') {
          cp = {};
          localStorage.removeItem('sige_acta_params_' + turmaId);
        }
      } catch (e) {
        cp = {};
      }
    }

    const qParams = new URLSearchParams(cp).toString();
    const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/acta?${qParams}`);
    if (!res || !res.success) {
      container.innerHTML = '<div class="alert alert-warning text-center py-3">Não foi possível carregar a acta do conselho para esta turma.</div>';
      return;
    }
    const d = res.data || res;

    const te = d.tabelaEfectivo;
    const ta = d.tabelaAproveitamento;
    const escola = d.escola || { nome: 'Escola Secundária', provincia: 'Maputo', distrito: 'Cidade de Maputo' };
    const turma = d.turma || { nome: 'Turma', grau_ano: '', turno: 'Diurno' };
    const disciplinas = Array.isArray(d.disciplinas) ? d.disciplinas : [];

    const anoTurma = turma.ano_letivo || '2026';
    const dirTurma = (cp.directorTurma && cp.directorTurma.trim()) ? cp.directorTurma.trim() : (turma.director_turma?.nome || turma.director_turma || '_________________');
    const p1 = (cp.presidenteT1 && cp.presidenteT1.trim()) ? cp.presidenteT1.trim() : '_________________';
    const p2 = (cp.presidenteT2 && cp.presidenteT2.trim()) ? cp.presidenteT2.trim() : '_________________';
    const p3 = (cp.presidenteT3 && cp.presidenteT3.trim()) ? cp.presidenteT3.trim() : '_________________';

    const dt1 = formatarDataParaExibicao(cp.dataT1, anoTurma);
    const dt2 = formatarDataParaExibicao(cp.dataT2, anoTurma);
    const dt3 = formatarDataParaExibicao(cp.dataT3, anoTurma);

    const hIni1 = (cp.horaInicioT1 && cp.horaInicioT1.trim()) ? cp.horaInicioT1.trim() : '__';
    const mIni1 = (cp.minInicioT1 && cp.minInicioT1.trim()) ? cp.minInicioT1.trim() : '__';
    const hFim1 = (cp.horaFimT1 && cp.horaFimT1.trim()) ? cp.horaFimT1.trim() : '__';
    const mFim1 = (cp.minFimT1 && cp.minFimT1.trim()) ? cp.minFimT1.trim() : '__';

    const hIni2 = (cp.horaInicioT2 && cp.horaInicioT2.trim()) ? cp.horaInicioT2.trim() : '__';
    const mIni2 = (cp.minInicioT2 && cp.minInicioT2.trim()) ? cp.minInicioT2.trim() : '__';
    const hFim2 = (cp.horaFimT2 && cp.horaFimT2.trim()) ? cp.horaFimT2.trim() : '__';
    const mFim2 = (cp.minFimT2 && cp.minFimT2.trim()) ? cp.minFimT2.trim() : '__';

    const hIni3 = (cp.horaInicioT3 && cp.horaInicioT3.trim()) ? cp.horaInicioT3.trim() : '__';
    const mIni3 = (cp.minInicioT3 && cp.minInicioT3.trim()) ? cp.minInicioT3.trim() : '__';
    const hFim3 = (cp.horaFimT3 && cp.horaFimT3.trim()) ? cp.horaFimT3.trim() : '__';
    const mFim3 = (cp.minFimT3 && cp.minFimT3.trim()) ? cp.minFimT3.trim() : '__';

    const textoProtocolar = `Sob presidência do senhor professor <strong>${p1}</strong> (Iº Trimestre); <strong>${p2}</strong> (IIº Trimestre); <strong>${p3}</strong> (IIIº Trimestre); director/substituto do director de turma <strong>${dirTurma}</strong> da turma <strong>${turma.nome}</strong> do grupo da <strong>${turma.grau_ano}</strong>, curso <strong>${turma.turno === 'NOITE' ? 'Nocturno' : 'Diurno'}</strong>, realizou-se o Conselho de Avaliação do Iº; IIº, IIIº, Trimestre no dia <strong>${dt1}</strong>; <strong>${dt2}</strong>; <strong>${dt3}</strong>, com início às <strong>${hIni1}</strong> horas e <strong>${mIni1}</strong> minutos e com término às <strong>${hFim1}</strong> horas e <strong>${mFim1}</strong> minutos (Iº Trim); <strong>${hIni2}</strong> horas e <strong>${mIni2}</strong> minutos e com término às <strong>${hFim2}</strong> horas e <strong>${mFim2}</strong> minutos (IIº Trim); <strong>${hIni3}</strong> horas e <strong>${mIni3}</strong> minutos e com término às <strong>${hFim3}</strong> horas e <strong>${mFim3}</strong> minutos (IIIº Trim). No final deste conselho colheram-se os resultados que abaixo vão discriminados de todos os membros que participaram:`;

    const tc = d.trimestresComNotas || { t1: true, t2: false, t3: false, fimAno: false };

    // Renderizador das Linhas da Tabela 1 (Efectivos e Movimento por Género)
    const renderTeLinhas = (categoria, chave) => {
      return ['H', 'M', 'HM'].map((gen, gIdx) => {
        const prop = gen === 'H' ? 'h' : (gen === 'M' ? 'm' : 'hm');
        const pctProp = gen === 'H' ? 'pctH' : (gen === 'M' ? 'pctM' : 'pct');
        const isInicial = (chave === 'inscritos');

        // Iº Trimestre
        const temT1 = tc.t1 || isInicial;
        const vT1 = (temT1 && te?.t1?.[chave] && te.t1[chave][prop] !== undefined)
          ? te.t1[chave][prop]
          : (isInicial && te?.t1?.inscritos ? te.t1.inscritos[prop] : '-');
        const pT1 = (temT1 && te?.t1?.[chave] && te.t1[chave][pctProp] !== undefined)
          ? `${te.t1[chave][pctProp]}%`
          : (isInicial && vT1 !== '-' ? '100%' : '-');

        // IIº Trimestre (Para Matrículas/Efectivo Inicial, replica automaticamente os matriculados do início do ano)
        const temT2 = tc.t2 || isInicial;
        const vT2 = isInicial
          ? (te?.t2?.[chave]?.[prop] ?? vT1)
          : (temT2 && te?.t2?.[chave] ? te.t2[chave][prop] : '-');
        const pT2 = isInicial
          ? (te?.t2?.[chave]?.[pctProp] !== undefined ? `${te.t2[chave][pctProp]}%` : pT1)
          : (temT2 && te?.t2?.[chave] && te.t2[chave][pctProp] !== undefined ? `${te.t2[chave][pctProp]}%` : '-');

        // IIIº Trimestre (Para Matrículas/Efectivo Inicial, replica automaticamente os matriculados do início do ano)
        const temT3 = tc.t3 || isInicial;
        const vT3 = isInicial
          ? (te?.t3?.[chave]?.[prop] ?? vT1)
          : (temT3 && te?.t3?.[chave] ? te.t3[chave][prop] : '-');
        const pT3 = isInicial
          ? (te?.t3?.[chave]?.[pctProp] !== undefined ? `${te.t3[chave][pctProp]}%` : pT1)
          : (temT3 && te?.t3?.[chave] && te.t3[chave][pctProp] !== undefined ? `${te.t3[chave][pctProp]}%` : '-');

        // Fim do Ano (Para Matrículas/Efectivo Inicial, replica automaticamente os matriculados do início do ano)
        const temFA = tc.fimAno || isInicial;
        const vFA = isInicial
          ? (te?.fimAno?.[chave]?.[prop] ?? vT1)
          : (temFA && te?.fimAno?.[chave] ? te.fimAno[chave][prop] : '-');
        const pFA = isInicial
          ? (te?.fimAno?.[chave]?.[pctProp] !== undefined ? `${te.fimAno[chave][pctProp]}%` : pT1)
          : (temFA && te?.fimAno?.[chave] && te.fimAno[chave][pctProp] !== undefined ? `${te.fimAno[chave][pctProp]}%` : '-');

        const tdCat = gIdx === 0 ? `<td rowspan="3" class="text-start ps-2 fw-bold align-middle bg-light border-end">${categoria}</td>` : '';
        const bgCls = gen === 'HM' ? 'table-light fw-bold' : '';

        return `
          <tr class="${bgCls}">
            ${tdCat}
            <td class="fw-semibold text-center">${gen}</td>
            <td>${vT1}</td><td class="text-muted small">${pT1}</td>
            <td>${vT2}</td><td class="text-muted small">${pT2}</td>
            <td>${vT3}</td><td class="text-muted small">${pT3}</td>
            <td>${vFA}</td><td class="text-muted small">${pFA}</td>
          </tr>
        `;
      }).join('');
    };

    // Renderizador das Linhas da Tabela 2 (Aproveitamento Pedagógico por Género)
    const renderTaLinhas = (classificacao, chave, isAprov = false) => {
      return ['H', 'M', 'HM'].map((gen, gIdx) => {
        const prop = gen === 'H' ? 'h' : (gen === 'M' ? 'm' : 'hm');
        const pctProp = gen === 'H' ? 'pctH' : (gen === 'M' ? 'pctM' : 'pct');

        const temNotasT1 = tc.t1 && (ta?.t1?.avaliados?.hm > 0);
        const vT1 = temNotasT1 && ta?.t1?.[chave] ? ta.t1[chave][prop] : '-';
        const pT1 = temNotasT1 && ta?.t1?.[chave] && ta.t1[chave][pctProp] !== undefined ? `${ta.t1[chave][pctProp]}%` : (temNotasT1 && chave === 'avaliados' ? '100%' : '-');

        const temNotasT2 = tc.t2 && (ta?.t2?.avaliados?.hm > 0);
        const vT2 = temNotasT2 && ta?.t2?.[chave] ? ta.t2[chave][prop] : '-';
        const pT2 = temNotasT2 && ta?.t2?.[chave] && ta.t2[chave][pctProp] !== undefined ? `${ta.t2[chave][pctProp]}%` : (temNotasT2 && chave === 'avaliados' ? '100%' : '-');

        const temNotasT3 = tc.t3 && (ta?.t3?.avaliados?.hm > 0);
        const vT3 = temNotasT3 && ta?.t3?.[chave] ? ta.t3[chave][prop] : '-';
        const pT3 = temNotasT3 && ta?.t3?.[chave] && ta.t3[chave][pctProp] !== undefined ? `${ta.t3[chave][pctProp]}%` : (temNotasT3 && chave === 'avaliados' ? '100%' : '-');

        const temNotasFA = tc.fimAno && (ta?.fimAno?.avaliados?.hm > 0);
        const vFA = temNotasFA && ta?.fimAno?.[chave] ? ta.fimAno[chave][prop] : '-';
        const pFA = temNotasFA && ta?.fimAno?.[chave] && ta.fimAno[chave][pctProp] !== undefined ? `${ta.fimAno[chave][pctProp]}%` : (temNotasFA && chave === 'avaliados' ? '100%' : '-');

        // Cálculo de Crescimento condicionado
        let c1_2 = '<span class="text-muted">-</span>';
        if (temNotasT1 && temNotasT2) {
          const nPT1 = ta?.t1?.[chave] && ta.t1[chave][pctProp] ? Number(ta.t1[chave][pctProp]) : 0;
          const nPT2 = ta?.t2?.[chave] && ta.t2[chave][pctProp] ? Number(ta.t2[chave][pctProp]) : 0;
          const dif1_2 = Number((nPT2 - nPT1).toFixed(1));
          c1_2 = dif1_2 > 0 ? `<span class="badge bg-success bg-opacity-25 text-success">+${dif1_2}% Subiu</span>` : (dif1_2 < 0 ? `<span class="badge bg-danger bg-opacity-25 text-danger">${dif1_2}% Desceu</span>` : '<span class="text-muted">0%</span>');
        }

        let c2_3 = '<span class="text-muted">-</span>';
        if (temNotasT2 && temNotasT3) {
          const nPT2 = ta?.t2?.[chave] && ta.t2[chave][pctProp] ? Number(ta.t2[chave][pctProp]) : 0;
          const nPT3 = ta?.t3?.[chave] && ta.t3[chave][pctProp] ? Number(ta.t3[chave][pctProp]) : 0;
          const dif2_3 = Number((nPT3 - nPT2).toFixed(1));
          c2_3 = dif2_3 > 0 ? `<span class="badge bg-success bg-opacity-25 text-success">+${dif2_3}% Subiu</span>` : (dif2_3 < 0 ? `<span class="badge bg-danger bg-opacity-25 text-danger">${dif2_3}% Desceu</span>` : '<span class="text-muted">0%</span>');
        }

        let cGlo = '<span class="text-muted">-</span>';
        if (temNotasT1 && temNotasFA) {
          const nPT1 = ta?.t1?.[chave] && ta.t1[chave][pctProp] ? Number(ta.t1[chave][pctProp]) : 0;
          const nPFA = ta?.fimAno?.[chave] && ta.fimAno[chave][pctProp] ? Number(ta.fimAno[chave][pctProp]) : 0;
          const difGlo = Number((nPFA - nPT1).toFixed(1));
          cGlo = difGlo > 0 ? `<span class="badge bg-success bg-opacity-25 text-success">+${difGlo}% Subiu</span>` : (difGlo < 0 ? `<span class="badge bg-danger bg-opacity-25 text-danger">${difGlo}% Desceu</span>` : '<span class="text-muted">0%</span>');
        }

        const tdCat = gIdx === 0 ? `<td rowspan="3" class="text-start ps-2 fw-bold align-middle bg-light border-end ${isAprov ? 'text-success' : ''}">${classificacao}</td>` : '';
        const bgCls = isAprov ? 'table-success bg-opacity-25 fw-bold' : (gen === 'HM' ? 'table-light fw-bold' : '');

        return `
          <tr class="${bgCls}">
            ${tdCat}
            <td class="fw-semibold text-center">${gen}</td>
            <td>${vT1}</td><td class="text-muted small">${pT1}</td>
            <td>${vT2}</td><td class="text-muted small">${pT2}</td>
            <td>${vT3}</td><td class="text-muted small">${pT3}</td>
            <td>${vFA}</td><td class="text-muted small">${pFA}</td>
            <td class="text-center small">${c1_2}</td>
            <td class="text-center small">${c2_3}</td>
            <td class="text-center small">${cGlo}</td>
          </tr>
        `;
      }).join('');
    };

    container.innerHTML = `
      <!-- Cabeçalho Oficial Bordado da Acta (Imagem 1) -->
      <div class="border rounded p-3 mb-3 bg-light text-center shadow-sm" style="border-color: #1E3A8A !important;">
        <h6 class="fw-bold mb-0 text-uppercase tracking-wider">REPÚBLICA DE MOÇAMBIQUE</h6>
        <small class="text-muted d-block fw-semibold text-uppercase">GOVERNO DA PROVÍNCIA DE ${(escola.provincia || 'MAPUTO').toUpperCase()} | GOVERNO DO DISTRITO DE ${(escola.distrito || 'CIDADE DE MAPUTO').toUpperCase()}</small>
        <h5 class="fw-bold text-dark my-1">${(escola.nome || 'Escola Secundária').toUpperCase()}</h5>
        <small class="fw-bold text-primary text-uppercase">SECTOR PEDAGÓGICO — ACTA DO CONSELHO DE AVALIAÇÃO</small>
      </div>

      <!-- Texto Protocolar com Campos Editáveis (Fiel à Imagem 1) -->
      <div class="acta-texto-protocolar p-3 bg-white rounded border mb-2 shadow-sm text-dark" style="line-height: 1.45; text-align: justify; font-family: 'Times New Roman', serif; font-size: 0.90rem; border-color: #cbd5e1 !important; page-break-after: avoid !important; break-after: avoid !important; page-break-inside: avoid !important;">
        ${textoProtocolar}
      </div>

      <!-- TABELAS LADO A LADO SEGUNDO O MODELO OFICIAL (Imagem 1) - FLUXO CONTÍNUO SEM QUEBRA DE PÁGINA -->
      <div class="acta-tabelas-lado-a-lado row g-2 mb-3" style="page-break-before: avoid !important; break-before: avoid !important;">
        <!-- TABELA 1: Aproveitamento Escolar por Trimestres e Fim do Ano (Efectivos e Movimento) -->
        <div class="col-6">
          <div class="border rounded p-2 bg-white h-100 shadow-sm">
            <h6 class="fw-bold text-center small text-uppercase mb-2 py-2 rounded text-white" style="background: #1E3A8A;">Aproveitamento por Trimestres e Fim do Ano</h6>
            <div class="table-responsive">
              <table class="table table-bordered table-sm text-center mb-0 align-middle" style="font-size: 0.68rem;">
                <thead class="table-light">
                  <tr>
                    <th rowspan="2" class="align-middle text-start ps-2">CATEGORIA</th>
                    <th rowspan="2" class="align-middle">GÉN</th>
                    <th colspan="2">Iº TRIMESTRE</th>
                    <th colspan="2">IIº TRIMESTRE</th>
                    <th colspan="2">IIIº TRIMESTRE</th>
                    <th colspan="2">FIM DO ANO</th>
                  </tr>
                  <tr>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                  </tr>
                </thead>
                <tbody>
                  ${renderTeLinhas('Matrículas / Efectivo Inicial', 'inscritos')}
                  ${renderTeLinhas('Desistentes', 'desistentes')}
                  ${renderTeLinhas('Transferidos', 'transferidos')}
                  ${renderTeLinhas('Falecidos', 'falecidos')}
                  ${renderTeLinhas('Perdeu Ano por Faltas', 'perdeuFaltas')}
                  ${renderTeLinhas('Anulou Matrícula', 'anulouMatricula')}
                  ${renderTeLinhas('Alunos Avaliados', 'avaliados')}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- TABELA 2: Aproveitamento Pedagógico por Faixas e Crescimento -->
        <div class="col-6">
          <div class="border rounded p-2 bg-white h-100 shadow-sm">
            <h6 class="fw-bold text-center small text-uppercase mb-2 py-2 rounded text-white" style="background: #1E3A8A;">Aproveitamento Pedagógico</h6>
            <div class="table-responsive">
              <table class="table table-bordered table-sm text-center mb-0 align-middle" style="font-size: 0.68rem;">
                <thead class="table-light">
                  <tr>
                    <th rowspan="2" class="align-middle text-start ps-2">CLASSIFICAÇÃO</th>
                    <th rowspan="2" class="align-middle">GÉN</th>
                    <th colspan="2">Iº TRIMESTRE</th>
                    <th colspan="2">IIº TRIMESTRE</th>
                    <th colspan="2">IIIº TRIMESTRE</th>
                    <th colspan="2">FIM DO ANO</th>
                    <th colspan="3">CRESCIMENTO</th>
                  </tr>
                  <tr>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Iº-IIº</th><th>IIº-IIIº</th><th>GLOBAL</th>
                  </tr>
                </thead>
                <tbody>
                  ${renderTaLinhas('Alunos Avaliados', 'avaliados')}
                  ${renderTaLinhas('Não Satisfatório (0 a 9,4)', 'naoSatisfatorio')}
                  ${renderTaLinhas('Satisfatório (9,5 a 13,4)', 'satisfatorio')}
                  ${renderTaLinhas('Bom (13,5 a 16,4)', 'bom')}
                  ${renderTaLinhas('Muito Bom (16,5 a 18,4)', 'muitoBom')}
                  ${renderTaLinhas('Excelente (18,5 a 20)', 'excelente')}
                  ${renderTaLinhas('TOTAL APROVADOS', 'aprovados', true)}
                  ${renderTaLinhas('TOTAL REPROVADOS', 'reprovados')}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- TABELA 3: Aproveitamento por Disciplina (Área de Comunicação e Ciências Sociais) -->
      <div class="border rounded p-3 bg-white mb-4 shadow-sm">
        <h6 class="fw-bold text-center small text-uppercase mb-2 py-2 rounded text-white" style="background: #1E3A8A;">Área Curricular & Estatística por Disciplina</h6>
        <div class="table-responsive">
          <table class="table table-bordered table-sm text-center mb-0 align-middle" style="font-size: 0.68rem;">
            <thead class="table-light">
              <tr>
                <th rowspan="2" class="align-middle text-start ps-2">CLASSIFICAÇÃO</th>
                ${d.disciplinas.map(dis => `<th colspan="3" class="fw-bold text-uppercase">${dis.nome}</th>`).join('')}
              </tr>
              <tr>
                ${d.disciplinas.map(() => '<th>H</th><th>M</th><th class="table-secondary">HM</th>').join('')}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="text-start ps-2 fw-semibold">[0 - 9,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa0_9?.h ?? 0}</td><td>${dis.faixa0_9?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa0_9?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[9,5 - 13,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa10_13?.h ?? 0}</td><td>${dis.faixa10_13?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa10_13?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[13,5 - 16,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa14_16?.h ?? 0}</td><td>${dis.faixa14_16?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa14_16?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[16,5 - 18,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa17_18?.h ?? 0}</td><td>${dis.faixa17_18?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa17_18?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[18,5 - 20 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa19_20?.h ?? 0}</td><td>${dis.faixa19_20?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa19_20?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr class="table-light fw-bold">
                <td class="text-start ps-2">Alunos Avaliados</td>
                ${d.disciplinas.map(dis => `<td>${dis.avaliados?.h ?? 0}</td><td>${dis.avaliados?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.avaliados?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr class="table-success bg-opacity-25 fw-bold text-success">
                <td class="text-start ps-2">Notas Positivas</td>
                ${d.disciplinas.map(dis => `<td>${dis.positivas?.h ?? 0}</td><td>${dis.positivas?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.positivas?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr class="table-success bg-opacity-25 fw-bold text-success">
                <td class="text-start ps-2">% Positivas</td>
                ${d.disciplinas.map(dis => `<td>${dis.positivas?.pctH ?? 0}%</td><td>${dis.positivas?.pctM ?? 0}%</td><td class="table-secondary fw-bold">${dis.positivas?.pct ?? 0}%</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 text-muted fst-italic">Assinatura do Docente</td>
                ${d.disciplinas.map(() => '<td colspan="3" class="text-center text-muted fst-italic">_________________</td>').join('')}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = '<div class="alert alert-danger">Erro ao carregar acta do conselho de avaliação.</div>';
  }
}

function modalConfigurarSessaoActa() {
  const turmaId = document.getElementById('pautaTurmaSelect')?.value;
  if (!turmaId) return alert('Selecione uma turma para configurar a sessão da acta');

  const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
  let cp = {};
  if (savedParamsRaw) {
    try {
      cp = JSON.parse(savedParamsRaw) || {};
      if (cp.dataT1 === '26/05/2026' && cp.dataT2 === '01/09/2026') {
        cp = {};
        localStorage.removeItem('sige_acta_params_' + turmaId);
      }
    } catch (e) {
      cp = {};
    }
  }

  abrirModal('Configurar Dados da Sessão do Conselho de Avaliação', `
    <form id="formConfigSessaoActa" onsubmit="salvarConfigSessaoActa(event, '${turmaId}')">
      <div class="alert alert-info py-2 small">
        <i class="bi bi-info-circle me-1"></i> Todos os campos abaixo são <strong>estritamente opcionais</strong>. Se deixados em branco, o sistema utilizará as linhas pontilhadas oficiais para preenchimento manual ou posterior para cada trimestre.
      </div>

      <!-- Director de Turma / Secretário -->
      <div class="card p-3 mb-3 bg-light border-0 shadow-sm">
        <h6 class="fw-bold text-dark mb-2"><i class="bi bi-person-badge me-1"></i> Director de Turma / Secretário (Opcional)</h6>
        <div class="row g-2">
          <div class="col-12">
            <label class="form-label small text-muted">Nome do Director / Substituto (Opcional)</label>
            <input type="text" id="cfgDirectorTurma" class="form-control form-control-sm" value="${cp.directorTurma || ''}" placeholder="Deixe em branco ou nome do director">
          </div>
        </div>
      </div>
      
      <!-- 1º Trimestre -->
      <div class="card p-3 mb-3 bg-light border-0 shadow-sm">
        <h6 class="fw-bold text-primary mb-2">1º Trimestre Lectivo (Opcional)</h6>
        <div class="row g-2">
          <div class="col-md-6">
            <label class="form-label small text-muted">Presidente da Sessão (Opcional)</label>
            <input type="text" id="cfgPresT1" class="form-control form-control-sm" value="${cp.presidenteT1 || ''}" placeholder="Deixe em branco até à realização">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Data da Realização (Opcional)</label>
            <input type="date" id="cfgDataT1" class="form-control form-control-sm" value="${formatarParaInputDate(cp.dataT1)}">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Início (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHIniT1" class="form-control text-center" value="${cp.horaInicioT1 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMIniT1" class="form-control text-center" value="${cp.minInicioT1 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Término (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHFimT1" class="form-control text-center" value="${cp.horaFimT1 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMFimT1" class="form-control text-center" value="${cp.minFimT1 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
        </div>
      </div>

      <!-- 2º Trimestre -->
      <div class="card p-3 mb-3 bg-light border-0 shadow-sm">
        <h6 class="fw-bold text-info mb-2">2º Trimestre Lectivo (Opcional)</h6>
        <div class="row g-2">
          <div class="col-md-6">
            <label class="form-label small text-muted">Presidente da Sessão (Opcional)</label>
            <input type="text" id="cfgPresT2" class="form-control form-control-sm" value="${cp.presidenteT2 || ''}" placeholder="Deixe em branco até à realização">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Data da Realização (Opcional)</label>
            <input type="date" id="cfgDataT2" class="form-control form-control-sm" value="${formatarParaInputDate(cp.dataT2)}">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Início (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHIniT2" class="form-control text-center" value="${cp.horaInicioT2 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMIniT2" class="form-control text-center" value="${cp.minInicioT2 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Término (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHFimT2" class="form-control text-center" value="${cp.horaFimT2 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMFimT2" class="form-control text-center" value="${cp.minFimT2 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
        </div>
      </div>

      <!-- 3º Trimestre -->
      <div class="card p-3 mb-3 bg-light border-0 shadow-sm">
        <h6 class="fw-bold text-secondary mb-2">3º Trimestre Lectivo (Opcional)</h6>
        <div class="row g-2">
          <div class="col-md-6">
            <label class="form-label small text-muted">Presidente da Sessão (Opcional)</label>
            <input type="text" id="cfgPresT3" class="form-control form-control-sm" value="${cp.presidenteT3 || ''}" placeholder="Deixe em branco até à realização">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Data da Realização (Opcional)</label>
            <input type="date" id="cfgDataT3" class="form-control form-control-sm" value="${formatarParaInputDate(cp.dataT3)}">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Início (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHIniT3" class="form-control text-center" value="${cp.horaInicioT3 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMIniT3" class="form-control text-center" value="${cp.minInicioT3 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Término (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHFimT3" class="form-control text-center" value="${cp.horaFimT3 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMFimT3" class="form-control text-center" value="${cp.minFimT3 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
        </div>
      </div>

      <div class="d-flex justify-content-between align-items-center gap-2">
        <button type="button" class="btn btn-outline-secondary btn-sm" onclick="limparConfigSessaoActa('${turmaId}')">
          <i class="bi bi-eraser me-1"></i> Limpar / Deixar em Branco
        </button>
        <div class="d-flex gap-2">
          <button type="button" class="btn btn-secondary btn-sm" onclick="fecharModal()">Cancelar</button>
          <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-check-lg me-1"></i> Salvar e Actualizar Acta</button>
        </div>
      </div>
    </form>
  `);
}

function limparConfigSessaoActa(turmaId) {
  localStorage.removeItem('sige_acta_params_' + turmaId);
  fecharModal();
  carregarActaConselho(turmaId);
}

function salvarConfigSessaoActa(e, turmaId) {
  e.preventDefault();
  const params = {
    directorTurma: document.getElementById('cfgDirectorTurma')?.value?.trim() || '',

    presidenteT1: document.getElementById('cfgPresT1')?.value?.trim() || '',
    dataT1: document.getElementById('cfgDataT1')?.value?.trim() || '',
    horaInicioT1: document.getElementById('cfgHIniT1')?.value?.trim() || '',
    minInicioT1: document.getElementById('cfgMIniT1')?.value?.trim() || '',
    horaFimT1: document.getElementById('cfgHFimT1')?.value?.trim() || '',
    minFimT1: document.getElementById('cfgMFimT1')?.value?.trim() || '',

    presidenteT2: document.getElementById('cfgPresT2')?.value?.trim() || '',
    dataT2: document.getElementById('cfgDataT2')?.value?.trim() || '',
    horaInicioT2: document.getElementById('cfgHIniT2')?.value?.trim() || '',
    minInicioT2: document.getElementById('cfgMIniT2')?.value?.trim() || '',
    horaFimT2: document.getElementById('cfgHFimT2')?.value?.trim() || '',
    minFimT2: document.getElementById('cfgMFimT2')?.value?.trim() || '',

    presidenteT3: document.getElementById('cfgPresT3')?.value?.trim() || '',
    dataT3: document.getElementById('cfgDataT3')?.value?.trim() || '',
    horaInicioT3: document.getElementById('cfgHIniT3')?.value?.trim() || '',
    minInicioT3: document.getElementById('cfgMIniT3')?.value?.trim() || '',
    horaFimT3: document.getElementById('cfgHFimT3')?.value?.trim() || '',
    minFimT3: document.getElementById('cfgMFimT3')?.value?.trim() || ''
  };

  localStorage.setItem('sige_acta_params_' + turmaId, JSON.stringify(params));
  fecharModal();
  carregarActaConselho(turmaId);
}

async function exportarActaConselhoExcel(turmaIdExplicit = null, anoExplicit = null, orientacaoExplicit = null) {
  const turmaId = await obterTurmaAtivaOuPrimeira(turmaIdExplicit);
  if (!turmaId) return;
  const ano = anoExplicit || document.getElementById('pautaAnoFiltro')?.value || '2026';
  const orientacao = orientacaoExplicit || document.getElementById('pautaOrientacaoSelect')?.value || 'landscape';

  const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
  const cp = savedParamsRaw ? JSON.parse(savedParamsRaw) : {};
  const qParams = new URLSearchParams({ anoLetivo: ano, orientacao: orientacao, ...cp }).toString();

  await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/acta-xlsx?${qParams}`, `Acta_Conselho_Turma_${ano}.xlsx`);
}

function imprimirActaConselhoOficial() {
  const orientacao = document.getElementById('pautaOrientacaoSelect')?.value || 'portrait';
  document.body.classList.remove('print-orientacao-landscape', 'print-orientacao-portrait');
  document.body.classList.add(orientacao === 'landscape' ? 'print-orientacao-landscape' : 'print-orientacao-portrait');
  window.print();
}

async function modalGerarPauta() {
  const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
  const optTurmas = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`
  ).join('');

  abrirModal('Consolidar Pauta Oficial de Turma', `
    <form id="formModalPauta">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Turma a Consolidar</label>
        <select id="mpautTurma" class="form-select">${optTurmas}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Período Lectivo</label>
        <select id="mpautPeriodo" class="form-select">
          <option value="1_TRIMESTRE">1º Trimestre</option>
          <option value="2_TRIMESTRE">2º Trimestre</option>
          <option value="3_TRIMESTRE">3º Trimestre</option>
          <option value="ANUAL">Pauta Anual Consolidada Final</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Pauta Oficial</button>
    </form>
  `);

  document.getElementById('formModalPauta').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/pautas/gerar', {
        method: 'POST',
        body: JSON.stringify({
          turma_id: document.getElementById('mpautTurma').value,
          periodo: document.getElementById('mpautPeriodo').value,
          ano_letivo: '2026'
        })
      });
      if (res.success) {
        fecharModal();
        alternarVisualizacaoPautaTurma();
      }
    } catch (err) {
      alert(err.message || 'Erro ao gerar pauta');
    }
  });
}

// ==================== 9. CERTIFICADOS (QR CODE) ====================
async function carregarCertificados() {
  try {
    const res = await apiFetch('/api/v1/certificados');
    if (res && res.success && Array.isArray(res.data)) {
      const tbody = document.getElementById('tabelaCertificados');
      if (!tbody) return;
      tbody.innerHTML = res.data.map(c => `
        <tr>
          <td><code class="text-primary">${escapeHtml(c.codigo_autenticidade)}</code></td>
          <td><strong>${escapeHtml(c.aluno ? c.aluno.nome : 'Aluno')}</strong></td>
          <td><span class="badge bg-light text-dark border">${escapeHtml(c.tipo)}</span></td>
          <td>${c.emitido_em ? new Date(c.emitido_em).toLocaleDateString('pt-PT') : '-'}</td>
          <td>
            <img src="${c.qrcode_data || ''}" alt="QR" width="38" height="38" class="border rounded" style="cursor: pointer;" onclick="verQrCodeGrande('${c.qrcode_data || ''}', '${escapeHtml(c.codigo_autenticidade)}')">
          </td>
          <td class="text-end">
            <div class="btn-group btn-group-sm">
              <button class="btn btn-primary" onclick="descarregarDocumentoOficialPdf('CERTIFICADO', '${escapeHtml(c.aluno ? c.aluno.id : '')}')" title="Descarregar Certificado Oficial em PDF">
                <i class="bi bi-file-earmark-pdf me-1"></i> PDF
              </button>
              <a href="/verificar-certificado.html?codigo=${encodeURIComponent(c.codigo_autenticidade || '')}" target="_blank" class="btn btn-outline-primary">
                <i class="bi bi-shield-check me-1"></i> Validar
              </a>
            </div>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.warn('[CERTIFICADOS] Falha ao carregar lista de certificados:', err);
  }
}

function verQrCodeGrande(qrSrc, codigo) {
  abrirModal('Autenticação Digital por QR Code', `
    <div class="text-center p-3">
      <img src="${qrSrc}" width="220" height="220" class="img-fluid border rounded p-2 mb-3 shadow-sm">
      <p class="font-monospace small text-muted">${codigo}</p>
      <div class="alert alert-info small mb-0">
        Qualquer cidadão ou instituição pode ler este QR Code com a câmara do telemóvel para certificar a autenticidade deste documento emitido pelo SIGE.
      </div>
    </div>
  `);
}

async function modalEmitirCertificado() {
  const alunosRes = await apiFetch('/api/v1/alunos');
  const optAlunos = (alunosRes.data || []).map(a => `<option value="${escapeHtml(a.id)}">${escapeHtml(a.nome)} (${escapeHtml(a.matricula || '-')})</option>`).join('');

  abrirModal('Emitir Certificado com QR Code', `
    <form id="formModalCert">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Aluno Titular</label>
        <select id="mcertAluno" class="form-select" required>${optAlunos}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Tipo de Certificado Oficial</label>
        <select id="mcertTipo" class="form-select">
          <option value="CONCLUSAO">Certificado de Conclusão de Estudos</option>
          <option value="TRANSFERENCIA">Guia de Transferência Oficial</option>
          <option value="MATRICULA">Declaração de Matrícula e Frequência</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary w-100">Emitir Certificado Criptográfico</button>
    </form>
  `);

  document.getElementById('formModalCert').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/certificados', {
        method: 'POST',
        body: JSON.stringify({
          aluno_id: document.getElementById('mcertAluno').value,
          tipo: document.getElementById('mcertTipo').value
        })
      });
      if (res.success) {
        fecharModal();
        carregarCertificados();
      }
    } catch (err) {
      alert('Erro ao emitir certificado: ' + (err.message || ''));
    }
  });
}

// ==================== 10. FINANCEIRO & MENSALIDADES ====================
async function carregarPagamentos() {
  try {
    const [resP, resStats] = await Promise.all([
      apiFetch('/api/v1/pagamentos'),
      apiFetch('/api/v1/pagamentos/stats')
    ]);

    if (resStats && resStats.success && resStats.data) {
      const s = resStats.data;
      const elFat = document.getElementById('finFaturadoCard');
      if (elFat) elFat.innerHTML = formatarMoeda(s.totalFaturado || 0);
      const elAtr = document.getElementById('finAtrasadoCard');
      if (elAtr) elAtr.innerHTML = formatarMoeda(s.totalAtrasado || 0);
      const elInad = document.getElementById('finInadimplenciaCard');
      if (elInad) elInad.textContent = (s.taxaInadimplencia ?? 0) + '%';
      const elAdimp = document.getElementById('finAdimplentesCard');
      if (elAdimp) elAdimp.textContent = (s.percentualAdimplentes ?? 0) + '%';
    }

    if (resP && resP.success && Array.isArray(resP.data)) {
      window.listaUltimosPagamentos = resP.data;
      const tbody = document.getElementById('tabelaPagamentos');
      if (!tbody) return;
      tbody.innerHTML = resP.data.map(p => `
        <tr>
          <td><strong>${escapeHtml(p.aluno ? p.aluno.nome : 'Aluno')}</strong></td>
          <td>${escapeHtml(p.descricao || 'Mensalidade')}</td>
          <td><code>${escapeHtml(p.mes_referencia || '-')}</code></td>
          <td><strong class="text-success">${formatarMoeda(p.valor || 0)}</strong></td>
          <td>${p.data_vencimento ? new Date(p.data_vencimento).toLocaleDateString('pt-PT') : '-'}</td>
          <td>
            <span class="badge ${p.status === 'PAGO' ? 'bg-success' : 'bg-warning text-dark'}">
              ${escapeHtml(p.status || 'PENDENTE')}
            </span>
          </td>
          <td class="text-end">
            <div class="btn-group btn-group-sm">
              ${p.status === 'PENDENTE' ? `
                <button class="btn btn-outline-success" onclick="liquidarPagamento('${escapeHtml(p.id)}', ${Number(p.valor || 0)})">
                  <i class="bi bi-cash me-1"></i> Liquidar
                </button>
              ` : ''}
              <button class="btn btn-outline-primary" onclick="imprimirReciboPagamento('${escapeHtml(p.id)}')" title="Visualizar e Imprimir Recibo">
                <i class="bi bi-receipt me-1"></i> Recibo
              </button>
              <button class="btn btn-primary" onclick="descarregarReciboPdf('${escapeHtml(p.id)}')" title="Descarregar Recibo Oficial em PDF">
                <i class="bi bi-file-earmark-pdf me-1"></i> PDF
              </button>
            </div>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.warn('[FINANCEIRO] Falha ao carregar mensalidades e estatísticas:', err);
  }
}

async function liquidarPagamento(id, valor) {
  if (!confirm(`Confirmar recebimento e liquidação da quantia de ${valor.toLocaleString('pt-PT')} MZN?`)) return;
  try {
    const res = await apiFetch(`/api/v1/pagamentos/${id}/liquidar`, {
      method: 'POST',
      body: JSON.stringify({ valor_pago: Number(valor), metodo_pagamento: 'NUMERARIO_OU_POS' })
    });
    if (res.success) {
      mostrarNotificacao('Pagamento liquidado com sucesso! A emitir recibo oficial...', 'success');
      await carregarPagamentos();
      await abrirModalReciboPagamento(id);
    }
  } catch (err) {
    alert('Erro ao liquidar pagamento: ' + (err.message || ''));
  }
}

async function modalNovoPagamento() {
  const alunosRes = await apiFetch('/api/v1/alunos');
  const optAlunos = (alunosRes.data || []).map(a => `<option value="${a.id}">${a.nome} (${a.matricula})</option>`).join('');

  abrirModal('Lançar Cobrança Individual de Mensalidade', `
    <form id="formModalPag">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Aluno</label>
        <select id="mpagAluno" class="form-select" required>${optAlunos}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Descrição</label>
        <input type="text" id="mpagDesc" class="form-control" value="Mensalidade Escolar" required>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Mês Ref.</label>
          <input type="text" id="mpagMes" class="form-control" value="2026-03" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor em Meticais (MZN)</label>
          <input type="number" id="mpagValor" class="form-control" value="2500" required>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Data de Vencimento</label>
        <input type="date" id="mpagVenc" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Cobrança</button>
    </form>
  `);

  document.getElementById('formModalPag').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const alunoId = document.getElementById('mpagAluno').value;
      const mesRef = document.getElementById('mpagMes').value.trim();

      // Verificação preventiva local se a fatura já existe no sistema para este mês
      if (window.listaUltimosPagamentos && window.listaUltimosPagamentos.some(p => {
        const pAlunoId = p.aluno?.id || p.aluno_id || (typeof p.aluno === 'string' ? p.aluno : null);
        return String(pAlunoId) === String(alunoId) && String(p.mes_referencia).trim() === mesRef && p.status !== 'CANCELADO';
      })) {
        mostrarAlerta('A factura já foi gerada no sistema.', 'warning', 'Aviso');
        return;
      }

      const res = await apiFetch('/api/v1/pagamentos', {
        method: 'POST',
        body: JSON.stringify({
          aluno_id: alunoId,
          descricao: document.getElementById('mpagDesc').value,
          mes_referencia: mesRef,
          valor: Number(document.getElementById('mpagValor').value),
          data_vencimento: document.getElementById('mpagVenc').value
        })
      });
      if (res.success) {
        mostrarNotificacao('Cobrança gerada com sucesso!', 'success');
        fecharModal();
        carregarPagamentos();
      }
    } catch (err) {
      const msg = err.message || 'Erro ao criar cobrança';
      mostrarAlerta(msg, 'warning', 'Aviso');
    }
  });
}

async function modalGerarMensalidadesTurma() {
  const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
  const optTurmas = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome}</option>`).join('');

  abrirModal('Gerar Mensalidades em Lote para a Turma', `
    <form id="formModalLotePag">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Turma</label>
        <select id="mlotTurma" class="form-select" required>${optTurmas}</select>
      </div>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small fw-semibold">Mês Ref. (AAAA-MM)</label>
          <input type="text" id="mlotMes" class="form-control" value="2026-03" required>
        </div>
        <div class="col-6">
          <label class="form-label small fw-semibold">Valor da Propina (MZN)</label>
          <input type="number" id="mlotValor" class="form-control" value="2500" required>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Data de Vencimento</label>
        <input type="date" id="mlotVenc" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Mensalidades para Todos os Alunos</button>
    </form>
  `);

  document.getElementById('formModalLotePag').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const turmaId = document.getElementById('mlotTurma').value;
      const mesRef = document.getElementById('mlotMes').value.trim();

      const res = await apiFetch('/api/v1/pagamentos/gerar-turma', {
        method: 'POST',
        body: JSON.stringify({
          turma_id: turmaId,
          mes_referencia: mesRef,
          valor: Number(document.getElementById('mlotValor').value),
          data_vencimento: document.getElementById('mlotVenc').value,
          descricao: `Propina de ${mesRef}`
        })
      });
      if (res.success) {
        const msg = res.message || 'Mensalidades geradas com sucesso para a turma!';
        mostrarNotificacao(msg, 'success');
        fecharModal();
        carregarPagamentos();
      }
    } catch (err) {
      const msg = err.message || 'Erro ao gerar cobranças';
      mostrarAlerta(msg, 'warning', 'Aviso');
    }
  });
}

async function abrirModalReciboPagamento(pagamentoId) {
  try {
    const res = await apiFetch(`/api/v1/impressao/recibo/${pagamentoId}`);
    if (!res.success || !res.data) {
      alert('Recibo de pagamento não encontrado.');
      return;
    }
    const d = res.data;
    const isPago = d.is_pago === true || (d.pagamento && d.pagamento.is_pago === true) || (d.pagamento && d.pagamento.status === 'PAGO' && (d.pagamento.data_pagamento || Number(d.pagamento.valor_pago || 0) > 0));
    const statusLabel = isPago ? 'PAGO' : 'NÃO PAGO';
    const statusClass = isPago ? 'bg-success' : 'bg-danger';
    const textClass = isPago ? 'text-success' : 'text-danger';
    const safeName = (d.aluno?.nome_completo || d.aluno?.nome || 'Aluno').replace(/[^a-zA-Z0-9]/g, '_');
    const carimboDataHora = d.carimboDataHora || (new Date().toLocaleDateString('pt-PT') + ' ' + new Date().toLocaleTimeString('pt-PT'));

    abrirModal(`Recibo Oficial — ${d.pagamento.recibo_numero || 'REC-2026'} [${statusLabel}]`, `
      <div id="modalAreaRecibo" class="p-4 bg-white position-relative" style="overflow: hidden; border-radius: 8px;">
        <!-- Marca d'Água de Segurança -->
        <div class="watermark-carimbo ${isPago ? 'watermark-pago' : 'watermark-nao-pago'}" style="position: absolute; top: 40%; left: 50%; transform: translate(-50%, -50%) rotate(-30deg); font-size: 64px; font-weight: 900; letter-spacing: 5px; opacity: 0.12; pointer-events: none; user-select: none; z-index: 10; border: 5px ${isPago ? 'solid #16a34a; color: #16a34a' : 'dashed #dc2626; color: #dc2626'}; padding: 10px 40px; border-radius: 12px; white-space: nowrap;">
          ${statusLabel}
        </div>

        <div class="text-center border-bottom pb-3 mb-3">
          <img src="/img/emblema-mocambique.png" style="width: 44px; height: 44px; margin-bottom: 4px;" alt="Emblema Nacional">
          <div class="small fw-semibold text-uppercase text-secondary" style="letter-spacing: 0.5px;">República de Moçambique &bull; Ministério da Educação e Cultura</div>
          <h6 class="fw-bold mb-1 mt-1 text-dark">${(d.escola?.nome || 'Escola Secundária').toUpperCase()}</h6>
          <p class="text-muted small mb-0">NUIT: ${d.escola?.nif_cnpj || '-'} &bull; ${d.escola?.distrito || '-'}, ${d.escola?.provincia || '-'} &bull; Tel: ${d.escola?.telefone || '-'}</p>
          <h5 class="mt-3 fw-bold ${textClass} text-uppercase" style="letter-spacing: 0.5px;">
            ${isPago ? 'RECIBO DE PAGAMENTO OFICIAL' : 'RECIBO / GUIA DE COBRANÇA (NÃO PAGO)'}
          </h5>
          <span class="badge bg-light text-dark border fs-6">Recibo Nº: <strong>${d.pagamento.recibo_numero || 'REC-2026-001'}</strong></span>
        </div>

        <!-- Banner Destacado de Situação -->
        <div class="p-2 mb-3 rounded text-center fw-bold ${isPago ? 'bg-success bg-opacity-10 text-success border border-success' : 'bg-danger bg-opacity-10 text-danger border border-danger'}">
          <i class="bi ${isPago ? 'bi-check-circle-fill' : 'bi-exclamation-octagon-fill'} me-2"></i>
          SITUAÇÃO: ${statusLabel} ${isPago ? '(LIQUIDADO COM SUCESSO)' : '(PENDENTE DE LIQUIDAÇÃO)'}
        </div>

        <div class="table-responsive">
          <table class="table table-bordered table-sm small mb-3 align-middle">
            <tr><th class="bg-light w-35">Instituição:</th><td><strong>${d.escola?.nome || '-'}</strong> (${d.escola?.distrito || '-'}, ${d.escola?.provincia || '-'})</td></tr>
            <tr><th class="bg-light">Aluno(a):</th><td><strong>${d.aluno?.nome_completo || d.aluno?.nome || '-'}</strong></td></tr>
            <tr><th class="bg-light">Nº de Matrícula:</th><td><code>${d.aluno?.matricula || '-'}</code></td></tr>
            <tr><th class="bg-light">Turma / Classe:</th><td>${d.aluno?.turma?.nome || '-'} (${d.aluno?.turma?.grau_ano || '-'}) ${d.aluno?.turma?.turno ? '&bull; Turno: ' + d.aluno?.turma?.turno : ''}</td></tr>
            <tr><th class="bg-light">Descrição da Cobrança:</th><td>${d.pagamento.descricao || 'Mensalidade / Propina'}</td></tr>
            <tr><th class="bg-light">Mês de Referência:</th><td><code>${d.pagamento.mes_referencia || '-'}</code></td></tr>
            <tr><th class="bg-light">Valor Cobrado:</th><td><strong>${formatarMoeda(d.pagamento.valor || 0)}</strong></td></tr>
            <tr><th class="bg-light">Valor Liquidado:</th><td class="fw-bold ${textClass} fs-6">${isPago ? formatarMoeda(d.pagamento.valor_pago || d.pagamento.valor || 0) : '0,00 MZN (Pendente de Liquidação)'}</td></tr>
            <tr><th class="bg-light">Estado / Situação:</th><td><span class="badge ${statusClass} fs-6">${statusLabel}</span></td></tr>
            <tr><th class="bg-light">Forma de Liquidação:</th><td>${isPago ? (d.pagamento.metodo_pagamento || 'MPESA') : 'Pendente de Liquidação'}</td></tr>
            <tr><th class="bg-light">Data de Confirmação:</th><td>${isPago ? (d.pagamento.data_pagamento || '-') : 'Aguardando Confirmação'}</td></tr>
          </table>
        </div>

        <!-- Aviso Informativo -->
        ${!isPago ? `
          <div class="alert alert-danger py-2 px-3 small mb-3 border border-danger">
            <i class="bi bi-exclamation-triangle-fill text-danger me-1"></i>
            <strong>ATENÇÃO:</strong> Este recibo expressa a condição de <strong>NÃO PAGO</strong>. O documento comprova unicamente a emissão da cobrança e não confere quitação de dívida até a respectiva liquidação no sistema ou por carteira móvel.
          </div>
        ` : `
          <div class="alert alert-success py-2 px-3 small mb-3 border border-success">
            <i class="bi bi-shield-check text-success me-1"></i>
            <strong>COMPROVATIVO DE QUITAÇÃO:</strong> Certifica-se que o valor indicado foi devidamente liquidado e confirmado no sistema oficial SIGE.
          </div>
        `}

        <div class="alert alert-light border small text-muted text-center py-2 mb-3">
          <i class="bi bi-clock-history me-1 text-primary"></i>
          Processado por Computador aos <strong>${carimboDataHora}</strong> | Autenticação Digital SIGE &bull; Sincronizado
        </div>

        <div class="row text-center pt-3 border-top small">
          <div class="col-6"><p class="mb-0 border-top pt-2 mx-3">A Secretaria / Tesouraria<br><small class="text-muted">Assinatura e Carimbo</small></p></div>
          <div class="col-6"><p class="mb-0 border-top pt-2 mx-3">O Aluno / Depositante<br><small class="text-muted">Assinatura</small></p></div>
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2 mt-3 pt-2 border-top no-print">
        <button type="button" class="btn btn-secondary btn-sm" onclick="fecharModal()">Fechar</button>
        <button type="button" class="btn btn-outline-primary btn-sm" onclick="descarregarReciboPdf('${pagamentoId}')">
          <i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF (Oficial)
        </button>
        <button type="button" class="btn btn-primary btn-sm" onclick="imprimirElementoRecibo('modalAreaRecibo', 'Recibo_${safeName}_${d.pagamento.mes_referencia}_${statusLabel}')">
          <i class="bi bi-printer me-1"></i> Imprimir Recibo
        </button>
      </div>
    `);
  } catch (err) {
    alert('Erro ao carregar recibo de pagamento: ' + (err.message || ''));
  }
}

function imprimirElementoRecibo(elementId, titulo) {
  const el = document.getElementById(elementId);
  if (!el) return window.print();
  const originalTitle = document.title;
  document.title = titulo;
  const printWindow = window.open('', '_blank', 'width=850,height=750');
  if (printWindow) {
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${titulo}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
          body { font-family: 'Times New Roman', Times, serif; background: #fff; padding: 25px; color: #111; }
          .watermark-carimbo {
            position: absolute;
            top: 45%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-30deg);
            font-size: 64px;
            font-weight: 900;
            letter-spacing: 5px;
            opacity: 0.15;
            pointer-events: none;
            user-select: none;
            z-index: 10;
            padding: 10px 40px;
            border-radius: 12px;
            white-space: nowrap;
          }
          .watermark-nao-pago {
            color: #dc2626 !important;
            border: 5px dashed #dc2626 !important;
          }
          .watermark-pago {
            color: #16a34a !important;
            border: 5px solid #16a34a !important;
          }
          @media print {
            .no-print { display: none !important; }
            body { padding: 10px; }
          }
        </style>
      </head>
      <body>
        <div style="position: relative;">
          ${el.innerHTML}
        </div>
        <script>
          window.onload = function() { window.print(); };
        <\/script>
      </body>
      </html>
    `);
    printWindow.document.close();
  } else {
    window.print();
  }
  document.title = originalTitle;
}

function imprimirReciboPagamento(pagamentoId) {
  abrirModalReciboPagamento(pagamentoId);
}

async function descarregarReciboPdf(pagamentoId) {
  try {
    mostrarNotificacao('A emitir e descarregar recibo oficial em PDF (PDFKit)...', 'info');
    await downloadFicheiroBinario(`/api/v1/impressao/recibo/${pagamentoId}/pdf`, `Recibo_${pagamentoId}.pdf`);
    mostrarNotificacao('Recibo oficial descarregado com sucesso!', 'success');
  } catch (err) {
    alert('Erro ao descarregar recibo em PDF: ' + (err.message || ''));
  }
}

// ==================== 11. CENTRAL DE IMPRESSÃO (INDIVIDUAL E LOTE) ====================
async function prepararCentralImpressao() {
  try {
    const resTurmas = await apiFetch('/api/v1/escola-admin/turmas');
    const selectTurma = document.getElementById('printSelectTurma');
    if (selectTurma) {
      selectTurma.innerHTML = '<option value="">Selecione uma turma...</option>' + 
        (resTurmas && Array.isArray(resTurmas.data) ? resTurmas.data : []).map(t => `<option value="${escapeHtml(t.id)}">${escapeHtml(t.nome)} (${escapeHtml(t.grau_ano || '')})</option>`).join('');
      
      if (resTurmas && resTurmas.data && resTurmas.data.length > 0) {
        selectTurma.value = resTurmas.data[0].id;
        await aoSelecionarTurmaImpressao();
      }
    }
  } catch (err) {
    console.warn('[IMPRESSAO] Falha ao preparar central de impressão:', err);
  }
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
  const nomeAluno = (alunoId && alunoId !== 'TODOS') ? (obterNomeAlunoParaDownload(alunoId) || 'Estudante') : '';
  const anoPadrao = (window.state && state.anoLetivo) || '2026';
  const nomeDocPadrao = `${nomeAluno} - ${anoPadrao}`;

  if (tipo === 'PAUTA_TURMA') {
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/pdf?anoLetivo=${anoPadrao}&orientacao=${orientacao}`, `Pauta - Turma - ${anoPadrao}.pdf`);
  } else if (tipo === 'ACTA_CONSELHO') {
    const sessao = JSON.parse(localStorage.getItem(`sige_sessao_acta_${turmaId}`) || '{}');
    const params = new URLSearchParams({ anoLetivo: anoPadrao, orientacao: orientacao });
    if (sessao.presidente) params.append('presidente', sessao.presidente);
    if (sessao.data) params.append('data', sessao.data);
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/acta-pdf?${params.toString()}`, `Acta - Conselho - ${anoPadrao}.pdf`);
  } else if (tipo === 'BOLETIM') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/boletim/${alunoId}/pdf?orientacao=${orientacao}`, `Boletim - ${nomeDocPadrao}.pdf`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/pdf?tipo=BOLETIM&orientacao=${orientacao}`, `Boletins - Turma - ${anoPadrao}.pdf`);
    }
  } else if (tipo === 'DECLARACAO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/declaracao/${alunoId}/pdf?orientacao=${orientacao}`, `Declaracao - ${nomeDocPadrao}.pdf`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/pdf?tipo=DECLARACAO&orientacao=${orientacao}`, `Declaracoes - Turma - ${anoPadrao}.pdf`);
    }
  } else if (tipo === 'CERTIFICADO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/certificado/${alunoId}/pdf?orientacao=${orientacao}`, `Certificado - ${nomeDocPadrao}.pdf`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/pdf?tipo=CERTIFICADO&orientacao=${orientacao}`, `Certificados - Turma - ${anoPadrao}.pdf`);
    }
  } else if (tipo === 'RECIBO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/recibo/${alunoId}/pdf?orientacao=${orientacao}`, `Recibo - ${nomeDocPadrao}.pdf`);
    } else if (turmaId) {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/pdf?tipo=RECIBO&orientacao=${orientacao}`, `Recibos - Turma - ${anoPadrao}.pdf`);
    }
  } else if (tipo === 'FICHA') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/ficha/${alunoId}/pdf?orientacao=${orientacao}`, `Ficha - ${nomeDocPadrao}.pdf`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/pdf?tipo=FICHA&orientacao=${orientacao}`, `Fichas - Turma - ${anoPadrao}.pdf`);
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
  const nomeAluno = (alunoId && alunoId !== 'TODOS') ? (obterNomeAlunoParaDownload(alunoId) || 'Estudante') : '';
  const anoPadrao = (window.state && state.anoLetivo) || '2026';
  const nomeDocPadrao = `${nomeAluno} - ${anoPadrao}`;

  if (tipo === 'PAUTA_TURMA') {
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/docx?anoLetivo=${anoPadrao}&orientacao=${orientacao}`, `Pauta - Turma - ${anoPadrao}.docx`);
  } else if (tipo === 'ACTA_CONSELHO') {
    const sessao = JSON.parse(localStorage.getItem(`sige_sessao_acta_${turmaId}`) || '{}');
    const params = new URLSearchParams({ anoLetivo: anoPadrao, orientacao: orientacao });
    if (sessao.presidente) params.append('presidente', sessao.presidente);
    if (sessao.data) params.append('data', sessao.data);
    await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/acta-docx?${params.toString()}`, `Acta - Conselho - ${anoPadrao}.docx`);
  } else if (tipo === 'BOLETIM') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/boletim/${alunoId}/docx?orientacao=${orientacao}`, `Boletim - ${nomeDocPadrao}.docx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=BOLETIM&orientacao=${orientacao}`, `Boletins - Turma - ${anoPadrao}.docx`);
    }
  } else if (tipo === 'DECLARACAO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/declaracao/${alunoId}/docx?orientacao=${orientacao}`, `Declaracao - ${nomeDocPadrao}.docx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=DECLARACAO&orientacao=${orientacao}`, `Declaracoes - Turma - ${anoPadrao}.docx`);
    }
  } else if (tipo === 'CERTIFICADO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/certificado/${alunoId}/docx?orientacao=${orientacao}`, `Certificado - ${nomeDocPadrao}.docx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=CERTIFICADO&orientacao=${orientacao}`, `Certificados - Turma - ${anoPadrao}.docx`);
    }
  } else if (tipo === 'RECIBO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/recibo/${alunoId}/docx?orientacao=${orientacao}`, `Recibo - ${nomeDocPadrao}.docx`);
    } else if (turmaId) {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=RECIBO&orientacao=${orientacao}`, `Recibos - Turma - ${anoPadrao}.docx`);
    }
  } else if (tipo === 'FICHA') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/ficha/${alunoId}/docx?orientacao=${orientacao}`, `Ficha - ${nomeDocPadrao}.docx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=FICHA&orientacao=${orientacao}`, `Fichas - Turma - ${anoPadrao}.docx`);
    }
  } else if (turmaId) {
    await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/docx?tipo=BOLETIM&orientacao=${orientacao}`, `Documento - Turma - ${anoPadrao}.docx`);
  }
}

async function descarregarXlsxCentral() {
  const tipo = document.getElementById('printTipoDoc')?.value || 'BOLETIM';
  const turmaId = await obterTurmaAtivaOuPrimeira(document.getElementById('printSelectTurma')?.value);
  const alunoId = document.getElementById('printSelectAluno')?.value;
  const orientacao = obterOrientacaoAtiva(tipo);
  const nomeAluno = (alunoId && alunoId !== 'TODOS') ? (obterNomeAlunoParaDownload(alunoId) || 'Estudante') : '';
  const anoPadrao = (window.state && state.anoLetivo) || '2026';
  const nomeDocPadrao = `${nomeAluno} - ${anoPadrao}`;

  if (!turmaId) return;

  if (tipo === 'ACTA_CONSELHO') {
    await exportarActaConselhoExcel(turmaId, anoPadrao, orientacao);
  } else if (tipo === 'PAUTA_TURMA') {
    await exportarPautaGeralExcel(turmaId, anoPadrao, orientacao);
  } else if (tipo === 'BOLETIM') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/boletim/${alunoId}/xlsx?orientacao=${orientacao}`, `Boletim - ${nomeDocPadrao}.xlsx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=BOLETIM&orientacao=${orientacao}`, `Boletins - Turma - ${anoPadrao}.xlsx`);
    }
  } else if (tipo === 'DECLARACAO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/declaracao/${alunoId}/xlsx?orientacao=${orientacao}`, `Declaracao - ${nomeDocPadrao}.xlsx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=DECLARACAO&orientacao=${orientacao}`, `Declaracoes - Turma - ${anoPadrao}.docx`);
    }
  } else if (tipo === 'CERTIFICADO') {
    if (alunoId && alunoId !== 'TODOS') {
      await downloadFicheiroBinario(`/api/v1/impressao/certificado/${alunoId}/xlsx?orientacao=${orientacao}`, `Certificado - ${nomeDocPadrao}.xlsx`);
    } else {
      await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=CERTIFICADO&orientacao=${orientacao}`, `Certificados - Turma - ${anoPadrao}.xlsx`);
    }
  } else if (tipo === 'FICHA' || tipo === 'RECIBO') {
    await downloadFicheiroBinario(`/api/v1/impressao/lote/turma/${turmaId}/xlsx?tipo=${tipo}&orientacao=${orientacao}`, `${tipo} - Turma - ${anoPadrao}.xlsx`);
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
  const codigoEscola = escolaObj.codigo_escola || escolaObj.codigo || (state.tenant?.codigo_escola ? state.tenant.codigo_escola : '---');
  const anoLetivo = d.anoLetivo || d.anoLectivo || state.tenant?.ano_letivo_ativo || '2026';

  const alunoObj = d.aluno || {};
  const alunoNome = (alunoObj.nomeCompleto || `${alunoObj.nome || ''} ${alunoObj.apelido || ''}`.trim() || '---').toUpperCase();
  const matricula = alunoObj.matricula || alunoObj.codigo || '---';

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
  const directorNome = d.directorNome || d.escola?.director_nome || '';
  const directorCarreira = d.directorCarreira || d.escola?.director_carreira || '';
  const chefeNome = d.chefeSecretariaNome || d.escola?.chefe_secretaria_nome || '';
  const chefeCarreira = d.chefeSecretariaCarreira || d.escola?.chefe_secretaria_carreira || '';

  const alunoNome = (d.aluno?.nomeCompleto || `${d.aluno?.nome || ''} ${d.aluno?.apelido || ''}`.trim() || d.aluno?.nome || '---').toUpperCase();
  const sexo = ((d.aluno?.genero || '').toUpperCase().startsWith('F')) ? 'Feminino' : 'Masculino';
  const pai = d.aluno?.pai || '---';
  const mae = d.aluno?.mae || '---';
  const alunoDistrito = d.aluno?.distrito || '---';
  const alunoProvincia = d.aluno?.provincia || '---';
  const anoLectivo = d.anoLectivo || d.anoLetivo || state.tenant?.ano_letivo_ativo || '2026';
  const grauClasse = d.grauAno || d.aluno?.turma?.grau_ano || d.aluno?.classe || '---';
  const area = d.area || d.aluno?.turma?.area || d.aluno?.area || '---';
  const matricula = d.aluno?.matricula || d.aluno?.codigo || '---';

  let diaNasc = '---', mesNasc = '---', anoNasc = '----';
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
      <button class="btn btn-primary" onclick="imprimirDocumentoComTitulo('Recibo_${safeName}_${d.pagamento?.mes_referencia || '2026'}')">
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

// ==================== 12. DESBLOQUEIO DE TRIMESTRE & CALENDÁRIO DE PRAZOS ====================
async function prepararDesbloqueioTrimestre() {
  try {
    const [turmasRes, profsRes] = await Promise.all([
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/professores')
    ]);

    const selectTurma = document.getElementById('desbloqueioTurma');
    if (selectTurma) {
      selectTurma.innerHTML = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`).join('');
    }

    const selectProf = document.getElementById('desbloqueioProfessor');
    if (selectProf) {
      selectProf.innerHTML = '<option value="">(Todos os Docentes da Turma)</option>' +
        (profsRes.data || []).map(p => `<option value="${p.id}">${p.nome}</option>`).join('');
    }

    // Carregar calendário oficial de prazos e lista de autorizações activas
    await Promise.all([
      carregarPrazosTrimestrais(),
      carregarAutorizacoesDesbloqueio()
    ]);
  } catch (err) {
    console.warn('Erro ao preparar tela de desbloqueio:', err);
  }
}

function alternarModoCalendarizacaoUI(modo) {
  const painelAuto = document.getElementById('painelCalendarizacaoAutomatica');
  const painelSempre = document.getElementById('painelCalendarizacaoSempre');
  const painelDatas = document.getElementById('painelTrimestresDatas');
  const badgeModo = document.getElementById('badgeModoAtivo');

  if (painelAuto) painelAuto.style.display = modo === 'AUTOMATICO' ? 'block' : 'none';
  if (painelSempre) painelSempre.style.display = modo === 'SEMPRE' ? 'block' : 'none';
  if (painelDatas) painelDatas.style.display = modo === 'SEMPRE' ? 'none' : 'block';

  if (badgeModo) {
    if (modo === 'AUTOMATICO') {
      badgeModo.className = 'badge bg-success';
      badgeModo.textContent = 'Modo: Automático (Duração)';
    } else if (modo === 'SEMPRE') {
      badgeModo.className = 'badge bg-warning text-dark';
      badgeModo.textContent = 'Modo: Permitir Sempre';
    } else {
      badgeModo.className = 'badge bg-primary';
      badgeModo.textContent = 'Modo: Manual (Datas)';
    }
  }
}

function calcularPrazosAutomaticosUI() {
  const dataBaseStr = document.getElementById('prazoDataBase')?.value;
  const valor = parseInt(document.getElementById('prazoValorDuracao')?.value || '4', 10);
  const tipo = document.getElementById('prazoTipoDuracao')?.value || 'SEMANAS';

  let dataBase = dataBaseStr ? new Date(dataBaseStr + 'T00:00:00') : new Date(new Date().getFullYear(), 1, 1);

  const somar = (d, v, t) => {
    const res = new Date(d);
    if (t === 'DIAS') {
      res.setDate(res.getDate() + v);
    } else if (t === 'MESES') {
      res.setMonth(res.getMonth() + v);
    } else {
      res.setDate(res.getDate() + (v * 7));
    }
    return res;
  };

  const fmt = (d) => d.toISOString().substring(0, 10);

  const t1Ini = dataBase;
  const t1Fim = somar(t1Ini, valor, tipo);

  const t2Ini = new Date(t1Fim);
  t2Ini.setDate(t2Ini.getDate() + 1);
  const t2Fim = somar(t2Ini, valor, tipo);

  const t3Ini = new Date(t2Fim);
  t3Ini.setDate(t3Ini.getDate() + 1);
  const t3Fim = somar(t3Ini, valor, tipo);

  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val;
  };

  setVal('prazoT1Inicio', fmt(t1Ini));
  setVal('prazoT1Fim', fmt(t1Fim));
  setVal('prazoT2Inicio', fmt(t2Ini));
  setVal('prazoT2Fim', fmt(t2Fim));
  setVal('prazoT3Inicio', fmt(t3Ini));
  setVal('prazoT3Fim', fmt(t3Fim));
}

async function carregarPrazosTrimestrais() {
  try {
    const res = await apiFetch('/api/v1/notas/prazos-trimestres');
    if (res.success && res.data) {
      const p = res.data;
      const modo = p.modo_calendarizacao || 'MANUAL';

      const selectModo = document.getElementById('prazoModoSelect');
      if (selectModo) selectModo.value = modo;
      alternarModoCalendarizacaoUI(modo);

      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val ? val.substring(0, 10) : '';
      };
      const setCheck = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.checked = !!val;
      };

      setVal('prazoDataBase', p.data_base_automatica);
      setVal('prazoValorDuracao', p.valor_duracao_automatica || 4);
      if (document.getElementById('prazoTipoDuracao')) {
        document.getElementById('prazoTipoDuracao').value = p.tipo_duracao_automatica || 'SEMANAS';
      }

      setVal('prazoT1Inicio', p.data_inicio_t1);
      setVal('prazoT1Fim', p.data_fim_t1);
      setVal('prazoT2Inicio', p.data_inicio_t2);
      setVal('prazoT2Fim', p.data_fim_t2);
      setVal('prazoT3Inicio', p.data_inicio_t3);
      setVal('prazoT3Fim', p.data_fim_t3);

      setCheck('prazoT1Sempre', p.permitir_sempre_t1);
      setCheck('prazoT2Sempre', p.permitir_sempre_t2);
      setCheck('prazoT3Sempre', p.permitir_sempre_t3);

      // Renderizar badges de status por trimestre
      if (res.prazos) {
        const renderStatusBadge = (idEl, info) => {
          const el = document.getElementById(idEl);
          if (!el || !info) return;
          let badge = '';
          if (info.sempre || modo === 'SEMPRE') {
            badge = '<span class="badge bg-success-subtle text-success border border-success mt-1"><i class="bi bi-unlock me-1"></i>Sempre Permitido</span>';
          } else if (info.motivo === 'FUTURO') {
            badge = `<span class="badge bg-secondary mt-1"><i class="bi bi-clock me-1"></i>Não Iniciado (Disponível a partir de ${info.inicio})</span>`;
          } else if (info.motivo === 'EXPIRADO') {
            badge = `<span class="badge bg-danger mt-1"><i class="bi bi-lock me-1"></i>Prazo Expirado (Fechado em ${info.fim})</span>`;
          } else if (info.aberto) {
            badge = `<span class="badge bg-success mt-1"><i class="bi bi-check-circle me-1"></i>Aberto para Lançamento (Até ${info.fim || 'final'})</span>`;
          } else {
            badge = '<span class="badge bg-light text-muted border mt-1">Datas Não Definidas</span>';
          }
          el.innerHTML = badge;
        };

        renderStatusBadge('statusT1Msg', res.prazos['1_TRIMESTRE']);
        renderStatusBadge('statusT2Msg', res.prazos['2_TRIMESTRE']);
        renderStatusBadge('statusT3Msg', res.prazos['3_TRIMESTRE']);
      }
    }
  } catch (err) {
    console.warn('Erro ao carregar prazos trimestrais:', err);
  }
}

document.getElementById('formPrazosTrimestrais')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const modo = document.getElementById('prazoModoSelect')?.value || 'MANUAL';
    const body = {
      modo_calendarizacao: modo,
      data_base_automatica: document.getElementById('prazoDataBase')?.value || null,
      valor_duracao_automatica: Number(document.getElementById('prazoValorDuracao')?.value || 4),
      tipo_duracao_automatica: document.getElementById('prazoTipoDuracao')?.value || 'SEMANAS',
      data_inicio_t1: document.getElementById('prazoT1Inicio')?.value || null,
      data_fim_t1: document.getElementById('prazoT1Fim')?.value || null,
      data_inicio_t2: document.getElementById('prazoT2Inicio')?.value || null,
      data_fim_t2: document.getElementById('prazoT2Fim')?.value || null,
      data_inicio_t3: document.getElementById('prazoT3Inicio')?.value || null,
      data_fim_t3: document.getElementById('prazoT3Fim')?.value || null,
      permitir_sempre_t1: document.getElementById('prazoT1Sempre')?.checked || false,
      permitir_sempre_t2: document.getElementById('prazoT2Sempre')?.checked || false,
      permitir_sempre_t3: document.getElementById('prazoT3Sempre')?.checked || false,
    };

    const res = await apiFetch('/api/v1/notas/prazos-trimestres', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    if (res.success) {
      alert(res.message || 'Calendário oficial de prazos de lançamento salvo com sucesso!');
      await carregarPrazosTrimestrais();
    } else {
      alert(res.message || 'Erro ao salvar prazos trimestrais');
    }
  } catch (err) {
    alert(err.message || 'Erro ao salvar prazos trimestrais');
  }
});

async function carregarAutorizacoesDesbloqueio() {
  const tbody = document.getElementById('tabelaAutorizacoesDesbloqueio');
  if (!tbody) return;
  try {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-3 text-muted"><div class="spinner-border spinner-border-sm me-2"></div>A carregar autorizações...</td></tr>';
    const res = await apiFetch('/api/v1/notas/autorizacoes');
    if (res.success && Array.isArray(res.data) && res.data.length > 0) {
      tbody.innerHTML = res.data.map(a => {
        const agora = new Date();
        const expiraEm = a.data_expiracao ? new Date(a.data_expiracao) : null;
        const expirada = a.expirada || (expiraEm && expiraEm < agora);

        const statusBadge = expirada
          ? '<span class="badge bg-secondary">Expirada</span>'
          : '<span class="badge bg-success">Activa</span>';
        
        const dataCriacao = a.created_at ? new Date(a.created_at).toLocaleString('pt-MZ') : '-';
        const dataExp = expiraEm ? expiraEm.toLocaleString('pt-MZ') : '-';
        const profNome = a.professor ? (a.professor.usuario?.nome || a.professor.nome || 'Docente') : '<em class="text-muted">(Toda a Turma)</em>';
        const autorNome = a.autorizado_por || a.autorizador?.nome || 'Direcção / DAP';
        const turmaNome = a.turma?.nome ? `${a.turma.nome} (${a.turma.grau_ano || ''})` : 'Turma';
        const trimLabel = a.periodo === '1_TRIMESTRE' ? '1º Trimestre' : (a.periodo === '2_TRIMESTRE' ? '2º Trimestre' : (a.periodo === '3_TRIMESTRE' ? '3º Trimestre' : a.periodo));

        return `
          <tr>
            <td><strong class="text-primary">${turmaNome}</strong></td>
            <td>${profNome}</td>
            <td><span class="badge bg-light text-dark border">${trimLabel}</span></td>
            <td>${autorNome}</td>
            <td>${dataCriacao}</td>
            <td>
              <div>${a.motivo || 'Autorizado'}</div>
              <small class="text-muted">Expira em: ${dataExp}</small>
            </td>
            <td>${statusBadge}</td>
            <td class="text-end">
              <button class="btn btn-outline-danger btn-sm" onclick="revogarAutorizacaoDesbloqueio('${a.id}')" title="Revogar autorização">
                <i class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        `;
      }).join('');
    } else {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center py-3 text-muted">Nenhuma autorização de desbloqueio registada de momento.</td></tr>';
    }
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-3 text-danger">Erro ao carregar autorizações de desbloqueio.</td></tr>';
  }
}

async function revogarAutorizacaoDesbloqueio(id) {
  if (!confirm('Deseja realmente revogar esta autorização de desbloqueio?')) return;
  try {
    const res = await apiFetch(`/api/v1/notas/autorizacoes/${id}`, { method: 'DELETE' });
    if (res.success) {
      alert('Autorização revogada com sucesso!');
      carregarAutorizacoesDesbloqueio();
    } else {
      alert(res.message || 'Erro ao revogar autorização');
    }
  } catch (err) {
    alert(err.message || 'Erro ao revogar autorização');
  }
}

document.getElementById('formAutorizarDesbloqueio')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const body = {
      turma_id: document.getElementById('desbloqueioTurma').value,
      professor_id: document.getElementById('desbloqueioProfessor').value || undefined,
      periodo: document.getElementById('desbloqueioTrimestre').value,
      duracao_horas: Number(document.getElementById('desbloqueioHoras').value),
      motivo: document.getElementById('desbloqueioMotivo').value
    };

    const res = await apiFetch('/api/v1/notas/autorizar-desbloqueio', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    if (res.success) {
      alert('Autorização de desbloqueio concedida com sucesso!');
      document.getElementById('desbloqueioMotivo').value = '';
      carregarAutorizacoesDesbloqueio();
    }
  } catch (err) {
    alert(err.message || 'Erro ao autorizar desbloqueio');
  }
});

// ==================== 13. PORTAL PRIVADO DO ALUNO ====================
async function carregarAlunoPerfil() {
  try {
    const res = await apiFetch('/api/v1/alunos/perfil/me');
    if (res.success) {
      const a = res.data;
      document.getElementById('alunoPerfilNome').textContent = a.nome;
      document.getElementById('alunoPerfilApelido').textContent = a.apelido || '-';
      document.getElementById('alunoPerfilMatricula').textContent = a.matricula;
      document.getElementById('alunoPerfilTurma').textContent = a.turma ? `${a.turma.nome} (${a.turma.grau_ano})` : 'Sem Turma';
      document.getElementById('alunoPerfilDoc').textContent = `${a.tipo_documento || 'BI'}: ${a.numero_documento || '-'}`;
      document.getElementById('alunoPerfilNUIT').textContent = a.nuit || '-';
      document.getElementById('alunoPerfilLocal').textContent = `${a.distrito || '-'}, ${a.provincia || '-'}`;

      if (document.getElementById('alunoPerfilPai')) document.getElementById('alunoPerfilPai').textContent = a.pai || '-';
      if (document.getElementById('alunoPerfilMae')) document.getElementById('alunoPerfilMae').textContent = a.mae || '-';
      if (document.getElementById('alunoPerfilDataNasc')) {
        document.getElementById('alunoPerfilDataNasc').textContent = a.data_nascimento 
          ? new Date(a.data_nascimento).toLocaleDateString('pt-MZ') 
          : '-';
      }
      if (document.getElementById('alunoPerfilResp')) document.getElementById('alunoPerfilResp').textContent = a.nome_responsavel || '-';
      if (document.getElementById('alunoPerfilTelResp')) document.getElementById('alunoPerfilTelResp').textContent = a.contato_responsavel || '-';
      if (document.getElementById('alunoPerfilEmailResp')) document.getElementById('alunoPerfilEmailResp').textContent = a.email_responsavel || '-';
    }
  } catch (err) {}
}

let stateAlunoNotas = {
  periodoAtivo: 'TODOS',
  dados: null
};

async function alternarTrimestreAluno(periodo) {
  stateAlunoNotas.periodoAtivo = periodo || 'TODOS';
  
  const botoes = {
    'TODOS': 'btnAlunoTrimestreTodos',
    '1_TRIMESTRE': 'btnAlunoTrimestre1',
    '2_TRIMESTRE': 'btnAlunoTrimestre2',
    '3_TRIMESTRE': 'btnAlunoTrimestre3'
  };

  Object.entries(botoes).forEach(([p, id]) => {
    const el = document.getElementById(id);
    if (el) {
      if (p === stateAlunoNotas.periodoAtivo) {
        el.classList.add('active', 'btn-primary');
        el.classList.remove('btn-outline-primary');
      } else {
        el.classList.remove('active', 'btn-primary');
        el.classList.add('btn-outline-primary');
      }
    }
  });

  await carregarAlunoNotas(stateAlunoNotas.periodoAtivo);
}

async function carregarAlunoNotas(periodoParam) {
  const periodo = periodoParam || stateAlunoNotas.periodoAtivo || 'TODOS';
  stateAlunoNotas.periodoAtivo = periodo;

  try {
    const res = await apiFetch(`/api/v1/alunos/me/notas?periodo=${encodeURIComponent(periodo)}`);
    if (!res || !res.success || !res.data) return;

    const d = res.data;
    stateAlunoNotas.dados = d;

    const bannerBloqueado = document.getElementById('bannerNotasBloqueadas');
    const bannerNaoPub = document.getElementById('bannerTrimestreNaoPublicado');
    const tabelaContainer = document.getElementById('tabelaAlunoNotasCorpo')?.closest('.table-responsive');
    const elMediaGeral = document.getElementById('alunoMediaGeral');
    const elPub = document.getElementById('lblPublicacaoEscola');

    // 1. Bloqueio total pela escola
    if (d.permitirVisualizacaoNotas === false || d.publicacaoNotasTrimestre === 'NENHUM') {
      if (bannerBloqueado) bannerBloqueado.classList.remove('d-none');
      if (bannerNaoPub) bannerNaoPub.classList.add('d-none');
      if (tabelaContainer) tabelaContainer.style.display = 'none';
      if (elMediaGeral) elMediaGeral.textContent = '--';
      if (elPub) elPub.innerHTML = '<span class="text-danger fw-bold"><i class="bi bi-lock-fill me-1"></i>Ocultas / Suspensas</span>';
      return;
    } else {
      if (bannerBloqueado) bannerBloqueado.classList.add('d-none');
      if (tabelaContainer) tabelaContainer.style.display = 'block';
    }

    // 2. Rótulo de publicação oficial da escola
    if (elPub) {
      const pubMap = {
        '1_TRIMESTRE': '<span class="text-primary fw-bold"><i class="bi bi-1-circle-fill me-1"></i>I Trimestre Publicado</span>',
        '2_TRIMESTRE': '<span class="text-primary fw-bold"><i class="bi bi-2-circle-fill me-1"></i>II Trimestre Publicado</span>',
        '3_TRIMESTRE': '<span class="text-primary fw-bold"><i class="bi bi-3-circle-fill me-1"></i>III Trimestre Publicado</span>',
        'TODOS': '<span class="text-success fw-bold"><i class="bi bi-check-all me-1"></i>Todos os Trimestres Publicados (I, II e III)</span>'
      };
      elPub.innerHTML = pubMap[d.publicacaoNotasTrimestre] || '<span class="text-success fw-bold">Todos os Trimestres</span>';
    }

    // 3. Verificação de publicação do trimestre selecionado
    const trimestresPublicados = d.trimestresPublicados || ['1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE'];
    const periodoEstaPublicado = (periodo === 'TODOS') || trimestresPublicados.includes(periodo);

    if (!periodoEstaPublicado) {
      if (bannerNaoPub) {
        bannerNaoPub.classList.remove('d-none');
        const nomesT = { '1_TRIMESTRE': '1º Trimestre', '2_TRIMESTRE': '2º Trimestre', '3_TRIMESTRE': '3º Trimestre' };
        bannerNaoPub.innerHTML = `<i class="bi bi-info-circle-fill me-2 fs-5"></i><strong>Trimestre em Consolidação:</strong> As notas do <strong>${nomesT[periodo] || periodo}</strong> ainda não foram publicadas pela Direcção Pedagógica.`;
      }
    } else {
      if (bannerNaoPub) bannerNaoPub.classList.add('d-none');
    }

    // 4. Média Geral e Situação
    if (elMediaGeral) {
      elMediaGeral.textContent = d.mediaGeral !== null && d.mediaGeral !== undefined ? `${d.mediaGeral} valores` : '--';
    }

    const badgeSit = document.getElementById('alunoSituacaoBadge');
    if (badgeSit) {
      if (d.situacao === 'APROVADO' || d.situacao === 'Aprovado') {
        badgeSit.textContent = 'Aprovado';
        badgeSit.className = 'badge bg-success p-2 ms-2';
      } else if (d.situacao === 'REPROVADO' || d.situacao === 'Reprovado') {
        badgeSit.textContent = 'Reprovado';
        badgeSit.className = 'badge bg-danger p-2 ms-2';
      } else {
        badgeSit.textContent = d.situacao || 'Em Curso';
        badgeSit.className = 'badge bg-secondary p-2 ms-2';
      }
    }

    // 5. Cabeçalho da Tabela
    const thead = document.getElementById('tabelaAlunoNotasCabecalho');
    if (thead) {
      if (periodo === 'TODOS') {
        thead.innerHTML = `
          <tr>
            <th class="text-start">Disciplina</th>
            <th>1º Trimestre (T1)</th>
            <th>2º Trimestre (T2)</th>
            <th>3º Trimestre (T3)</th>
            <th>Média Final (MFD)</th>
            <th>Faltas Totais</th>
            <th>Situação Anual</th>
          </tr>
        `;
      } else {
        const nomesPer = { '1_TRIMESTRE': 'I Trimestre', '2_TRIMESTRE': 'II Trimestre', '3_TRIMESTRE': 'III Trimestre' };
        thead.innerHTML = `
          <tr>
            <th class="text-start">Disciplina</th>
            <th>Teste 1 (ACS 1)</th>
            <th>Teste 2 (ACS 2)</th>
            <th>Trabalho (ACT)</th>
            <th>Aval. Trimestral (APT)</th>
            <th>Média ${nomesPer[periodo]}</th>
            <th>Faltas</th>
            <th>Situação</th>
          </tr>
        `;
      }
    }

    // 6. Corpo da Tabela
    const tbody = document.getElementById('tabelaAlunoNotasCorpo');
    if (!tbody) return;

    if (!d.disciplinas || d.disciplinas.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Nenhuma avaliação registada para este aluno.</td></tr>';
      return;
    }

    if (periodo === 'TODOS') {
      tbody.innerHTML = d.disciplinas.map(item => {
        const mfdVal = item.mfd !== null && item.mfd !== undefined ? item.mfd : (item.mediaFinal !== null ? item.mediaFinal : null);
        const mfdCls = mfdVal !== null ? (Number(mfdVal) >= 9.5 ? 'text-success fw-bold' : 'text-danger fw-bold') : 'text-muted';

        const fmtNotaCol = (val, pub) => {
          if (!pub) return '<span class="badge bg-light text-muted border" title="Não publicado pela escola"><i class="bi bi-lock me-1"></i>Oculto</span>';
          if (val === null || val === undefined || val === '-') return '<span class="text-muted">-</span>';
          const n = Number(val);
          return `<span class="${n >= 9.5 ? 'fw-bold text-dark' : 'fw-bold text-danger'}">${n}</span>`;
        };

        const sitBadge = mfdVal !== null 
          ? (Number(mfdVal) >= 9.5 ? '<span class="badge bg-success">Positiva</span>' : '<span class="badge bg-danger">Negativa</span>')
          : '<span class="badge bg-light text-dark border">Pendente</span>';

        return `
          <tr>
            <td class="text-start fw-bold text-dark">${escapeHtml(item.nome)}</td>
            <td>${fmtNotaCol(item.t1, item.publicadoT1 !== false)}</td>
            <td>${fmtNotaCol(item.t2, item.publicadoT2 !== false)}</td>
            <td>${fmtNotaCol(item.t3, item.publicadoT3 !== false)}</td>
            <td class="fs-6 ${mfdCls}">${mfdVal !== null ? mfdVal : '-'}</td>
            <td>${item.faltas || 0}</td>
            <td>${sitBadge}</td>
          </tr>
        `;
      }).join('');
    } else {
      tbody.innerHTML = d.disciplinas.map(item => {
        const det = (item.detalhes && item.detalhes[periodo]) || {};
        if (det.publicado === false) {
          return `
            <tr>
              <td class="text-start fw-bold text-dark">${escapeHtml(item.nome)}</td>
              <td colspan="6" class="text-muted py-2"><i class="bi bi-lock me-1"></i>Notas deste trimestre ainda não publicadas pela escola.</td>
            </tr>
          `;
        }

        const medNum = det.media_final !== null && det.media_final !== undefined ? Number(det.media_final) : null;
        const cls = medNum !== null ? (medNum >= 9.5 ? 'text-success fw-bold fs-6' : 'text-danger fw-bold fs-6') : 'text-muted';

        const fmtVal = v => (v !== null && v !== undefined && v !== '') ? (Number(v) >= 9.5 ? `<strong>${v}</strong>` : `<strong class="text-danger">${v}</strong>`) : '-';

        const sitBadge = medNum !== null 
          ? (medNum >= 9.5 ? '<span class="badge bg-success">Aprovado</span>' : '<span class="badge bg-danger">Reprovado</span>')
          : '<span class="badge bg-light text-dark border">Pendente</span>';

        return `
          <tr>
            <td class="text-start fw-bold text-dark">${escapeHtml(item.nome)}</td>
            <td>${fmtVal(det.teste1)}</td>
            <td>${fmtVal(det.teste2)}</td>
            <td>${fmtVal(det.trabalho)}</td>
            <td>${fmtVal(det.avaliacao_trimestral)}</td>
            <td class="${cls}">${medNum !== null ? medNum : '-'}</td>
            <td>${det.faltas || 0}</td>
            <td>${sitBadge}</td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    console.warn('[NOTAS] Falha ao carregar notas do aluno:', err);
  }
}

async function carregarAlunoPagamentos() {
  try {
    const res = await apiFetch('/api/v1/alunos/me/pagamentos');
    if (res.success && Array.isArray(res.data)) {
      const pagamentos = res.data;
      
      let totalPago = 0;
      let totalPendente = 0;
      let temAtrasado = false;
      const hoje = new Date();

      pagamentos.forEach(p => {
        const val = Number(p.valor || 0);
        if (p.status === 'PAGO') {
          totalPago += Number(p.valor_pago || val);
        } else {
          totalPendente += val;
          if (p.data_vencimento && new Date(p.data_vencimento) < hoje) {
            temAtrasado = true;
          }
        }
      });

      const elPago = document.getElementById('alunoTotalPagoCard');
      if (elPago) elPago.innerHTML = formatarMoeda(totalPago);

      const elPendente = document.getElementById('alunoTotalPendenteCard');
      if (elPendente) elPendente.innerHTML = formatarMoeda(totalPendente);

      const elSituacao = document.getElementById('alunoSituacaoPropinaCard');
      if (elSituacao) {
        if (totalPendente === 0) {
          elSituacao.textContent = 'Regularizado';
          elSituacao.className = 'fw-bold mb-0 text-success';
        } else if (temAtrasado) {
          elSituacao.textContent = 'Em Atraso';
          elSituacao.className = 'fw-bold mb-0 text-danger';
        } else {
          elSituacao.textContent = 'Pendente';
          elSituacao.className = 'fw-bold mb-0 text-warning';
        }
      }

      const tbody = document.getElementById('tabelaAlunoPagamentosCorpo');
      if (tbody) {
        if (pagamentos.length === 0) {
          tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4"><i class="bi bi-info-circle me-1"></i>Nenhuma mensalidade lançada até ao momento.</td></tr>`;
        } else {
          tbody.innerHTML = pagamentos.map(p => `
            <tr>
              <td><strong>${p.descricao || 'Mensalidade Escolar'}</strong></td>
              <td><code>${p.mes_referencia || '-'}</code></td>
              <td><strong class="text-success">${formatarMoeda(p.valor || 0)}</strong></td>
              <td>${p.data_vencimento ? new Date(p.data_vencimento).toLocaleDateString('pt-PT') : '-'}</td>
              <td>
                <span class="badge ${p.status === 'PAGO' ? 'bg-success' : 'bg-warning text-dark'}">
                  ${p.status}
                </span>
              </td>
              <td class="text-end">
                ${p.status === 'PAGO' ? `
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="imprimirReciboPagamento('${p.id}')" title="Visualizar e Imprimir Recibo">
                      <i class="bi bi-printer me-1"></i> Imprimir
                    </button>
                    <button class="btn btn-primary" onclick="descarregarReciboPdf('${p.id}')" title="Descarregar Recibo Oficial em PDF (PDFKit)">
                      <i class="bi bi-file-earmark-pdf me-1"></i> PDF
                    </button>
                  </div>
                ` : '<span class="badge bg-light text-muted border">Pendente</span>'}
              </td>
            </tr>
          `).join('');
        }
      }
    }
  } catch (err) {
    console.error('Erro ao carregar pagamentos do aluno:', err);
  }
}

// ==================== 14. AUDITORIA & ACESSOS ====================
async function carregarLogsAcesso() {
  try {
    const res = await apiFetch('/api/v1/auth/stats');
    if (res && res.success && res.data && Array.isArray(res.data.logsRecentes)) {
      const tbody = document.getElementById('tabelaLogsAcesso');
      if (!tbody) return;
      tbody.innerHTML = res.data.logsRecentes.map(l => {
        const dtStr = l.createdAt ? (new Date(l.createdAt).toLocaleDateString('pt-PT') + ' às ' + new Date(l.createdAt).toLocaleTimeString('pt-PT')) : '-';
        const usuarioNome = l.usuario ? l.usuario.nome : 'Anónimo / Convidado';
        const tipoLog = l.tipo || 'DESCONHECIDO';
        return `
          <tr>
            <td>${escapeHtml(dtStr)}</td>
            <td><strong>${escapeHtml(usuarioNome)}</strong></td>
            <td><code>${escapeHtml(l.ip || '-')}</code></td>
            <td class="small text-muted">${escapeHtml(l.user_agent || '-')}</td>
            <td>
              <span class="badge ${tipoLog === 'LOGIN_SUCESSO' ? 'bg-success' : tipoLog === 'ACESSO_BLOQUEADO_EXPIRADO' ? 'bg-danger' : 'bg-warning text-dark'}">
                ${escapeHtml(tipoLog)}
              </span>
            </td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    console.warn('[ACESSOS] Falha ao carregar logs de acesso:', err);
  }
}

// ==================== HELPERS DE MODAL ====================
let modalInstancia = null;
function abrirModal(titulo, htmlCorpo) {
  const elTitulo = document.getElementById('modalGenericoTitulo');
  if (elTitulo) elTitulo.textContent = titulo;
  const corpo = document.getElementById('modalGenericoCorpo');
  if (corpo) {
    corpo.innerHTML = htmlCorpo;
    aplicarResponsividadeUniversalTabelas(corpo);
    aplicarMascaraCamposNumericos(corpo);
  }
  const el = document.getElementById('modalGenerico');
  if (el && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
    modalInstancia = bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el);
    modalInstancia.show();
  }
}

function fecharModal() {
  if (modalInstancia) modalInstancia.hide();
}


// Cascata de Filtros: Classe -> Turma
function filtrarAlocacoesCadernetaPorClasse() {
  const classe = document.getElementById('cadernetaClasseFilter')?.value;
  const selectAloc = document.getElementById('cadernetaAlocacaoSelect');
  if (!selectAloc) return;

  let filtradas = state.alocacoesDocente;
  if (classe) {
    filtradas = filtradas.filter(a => (a.turma.grau_ano || '').includes(classe));
  }

  if (filtradas.length > 0) {
    selectAloc.innerHTML = filtradas.map(a => 
      `<option value="${a.id}">${a.disciplina.nome} — ${a.turma.nome} (${a.turma.grau_ano})</option>`
    ).join('');
    carregarCadernetaDocente();
  } else {
    selectAloc.innerHTML = '<option value="">Nenhuma alocação nesta classe</option>';
  }
}

let turmasCadastradasCache = [];
async function filtrarTurmasPautaPorClasse() {
  const classe = document.getElementById('pautaClasseFilter')?.value;
  const selectTurma = document.getElementById('pautaTurmaSelect');
  if (!selectTurma) return;

  if (turmasCadastradasCache.length === 0) {
    const res = await apiFetch('/api/v1/escola-admin/turmas');
    if (res.success) turmasCadastradasCache = res.data;
  }

  let turmasFiltradas = turmasCadastradasCache;
  if (classe) {
    turmasFiltradas = turmasFiltradas.filter(t => (t.grau_ano || '').includes(classe));
  }

  if (turmasFiltradas.length > 0) {
    selectTurma.innerHTML = turmasFiltradas.map(t => 
      `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`
    ).join('');
    alternarVisualizacaoPautaTurma();
  } else {
    selectTurma.innerHTML = '<option value="">Nenhuma turma nesta classe</option>';
  }
}



window.alternarAbaPublicacaoNotasDap = function(modo) {
  window._sigeModoPubNotasModal = modo;
  const painelManual = document.getElementById('painelPubNotasManual');
  const painelDatas = document.getElementById('painelPubNotasDatas');
  const btnManual = document.getElementById('btnAbaPubManual');
  const btnDatas = document.getElementById('btnAbaPubDatas');

  if (modo === 'DATAS') {
    if (painelManual) painelManual.classList.add('d-none');
    if (painelDatas) painelDatas.classList.remove('d-none');
    if (btnManual) {
      btnManual.className = 'btn btn-sm flex-fill fw-bold btn-light text-muted border-0';
      btnManual.style.backgroundColor = 'transparent';
      btnManual.style.color = '#6c757d';
    }
    if (btnDatas) {
      btnDatas.className = 'btn btn-sm flex-fill fw-bold text-white shadow-sm';
      btnDatas.style.backgroundColor = '#6200ea';
      btnDatas.style.borderColor = '#6200ea';
    }
  } else {
    if (painelManual) painelManual.classList.remove('d-none');
    if (painelDatas) painelDatas.classList.add('d-none');
    if (btnManual) {
      btnManual.className = 'btn btn-sm flex-fill fw-bold text-white shadow-sm';
      btnManual.style.backgroundColor = '#6200ea';
      btnManual.style.borderColor = '#6200ea';
    }
    if (btnDatas) {
      btnDatas.className = 'btn btn-sm flex-fill fw-bold btn-light text-muted border-0';
      btnDatas.style.backgroundColor = 'transparent';
      btnDatas.style.color = '#6c757d';
    }
  }
};

window.alternarModoFimTodos = function() {
  const inf = document.getElementById('campoFimTodosInfinito');
  const dat = document.getElementById('campoFimTodosData');
  const btn = document.getElementById('btnToggleFimTodos');
  const inputData = document.getElementById('pubDataFimTodos');
  if (!inf || !dat) return;

  const estaInfinito = !inf.classList.contains('d-none');
  if (estaInfinito) {
    inf.classList.add('d-none');
    dat.classList.remove('d-none');
    if (btn) btn.innerHTML = '<i class="bi bi-infinity me-1"></i>Visualizar por Infinito';
  } else {
    dat.classList.add('d-none');
    inf.classList.remove('d-none');
    if (inputData) inputData.value = '';
    if (btn) btn.innerHTML = '<i class="bi bi-pencil me-1"></i>Definir prazo limite';
  }
};

async function toggleVisibilidadeNotasDap() {
  try {
    const res = await apiFetch('/api/v1/escola-admin/toggle-notas');
    const d = res.data || {};
    const pubAtual = d.publicacao_notas_trimestre || state.tenant?.publicacao_notas_trimestre || 'TODOS';
    const ativa = (d.permitir_visualizacao_notas !== false) && (state.tenant?.permitir_visualizacao_notas !== false);
    const modoAtual = (d.modo_publicacao_notas || state.tenant?.modo_publicacao_notas || 'MANUAL').toUpperCase();
    window._sigeModoPubNotasModal = modoAtual;

    const dataInicioT1 = d.data_inicio_pub_t1 || '';
    const dataFimT1 = d.data_fim_pub_t1 || '';
    const dataInicioT2 = d.data_inicio_pub_t2 || '';
    const dataFimT2 = d.data_fim_pub_t2 || '';
    const dataInicioTodos = d.data_inicio_pub_todos || '';
    const dataFimTodos = d.data_fim_pub_todos || '';

    const htmlModal = `
      <div class="p-2">
        <!-- Alternador Superior das Duas Possibilidades -->
        <div class="d-flex p-1 bg-light rounded-pill border mb-3">
          <button type="button" class="btn btn-sm flex-fill fw-bold ${modoAtual === 'MANUAL' ? 'text-white shadow-sm' : 'btn-light text-muted border-0'}" 
                  id="btnAbaPubManual" 
                  style="${modoAtual === 'MANUAL' ? 'background-color: #6200ea; border-color: #6200ea;' : 'background-color: transparent;'}"
                  onclick="alternarAbaPublicacaoNotasDap('MANUAL')">
            <i class="bi bi-hand-index-thumb me-1"></i> 1ª Opção: Modo Imediato / Manual
          </button>
          <button type="button" class="btn btn-sm flex-fill fw-bold ${modoAtual === 'DATAS' ? 'text-white shadow-sm' : 'btn-light text-muted border-0'}" 
                  id="btnAbaPubDatas" 
                  style="${modoAtual === 'DATAS' ? 'background-color: #6200ea; border-color: #6200ea;' : 'background-color: transparent;'}"
                  onclick="alternarAbaPublicacaoNotasDap('DATAS')">
            <i class="bi bi-calendar-range me-1"></i> 2ª Opção: Programado por Datas
          </button>
        </div>

        <!-- 1ª Possibilidade: Modo Manual / Directo -->
        <div id="painelPubNotasManual" class="${modoAtual === 'DATAS' ? 'd-none' : ''}">
          <div class="alert alert-info py-2 small mb-3">
            <i class="bi bi-info-circle-fill me-1"></i> Escolha quais notas devem ficar visíveis no portal para os alunos e encarregados de educação.
          </div>
          <div class="list-group mb-3 shadow-sm">
            <label class="list-group-item list-group-item-action d-flex align-items-center gap-3 p-3 cursor-pointer">
              <input class="form-check-input flex-shrink-0" type="radio" name="radioPubNotasDap" value="1_TRIMESTRE" ${pubAtual === '1_TRIMESTRE' && ativa ? 'checked' : ''}>
              <div class="flex-grow-1">
                <strong class="text-primary d-block"><i class="bi bi-1-circle-fill me-1"></i> 1. I Trimestre (Apenas 1º Trimestre)</strong>
                <small class="text-muted">Apenas as avaliações, testes e média do I Trimestre ficam visíveis para os alunos.</small>
              </div>
            </label>
            <label class="list-group-item list-group-item-action d-flex align-items-center gap-3 p-3 cursor-pointer">
              <input class="form-check-input flex-shrink-0" type="radio" name="radioPubNotasDap" value="2_TRIMESTRE" ${pubAtual === '2_TRIMESTRE' && ativa ? 'checked' : ''}>
              <div class="flex-grow-1">
                <strong class="text-primary d-block"><i class="bi bi-2-circle-fill me-1"></i> 2. I e II Trimestre (1º e 2º Trimestre)</strong>
                <small class="text-muted">Avaliações do II Trimestre (e histórico do I) ficam disponíveis para consulta.</small>
              </div>
            </label>
            <label class="list-group-item list-group-item-action d-flex align-items-center gap-3 p-3 cursor-pointer">
              <input class="form-check-input flex-shrink-0" type="radio" name="radioPubNotasDap" value="TODOS" ${pubAtual === 'TODOS' && ativa ? 'checked' : ''}>
              <div class="flex-grow-1">
                <strong class="text-success d-block"><i class="bi bi-check-all me-1"></i> 4. Todos os Trimestres (I, II e III)</strong>
                <small class="text-muted">Publicação completa de todas as notas do ano (I, II, III trimestres e Média Final).</small>
              </div>
            </label>
            <label class="list-group-item list-group-item-action d-flex align-items-center gap-3 p-3 cursor-pointer">
              <input class="form-check-input flex-shrink-0" type="radio" name="radioPubNotasDap" value="NENHUM" ${!ativa || pubAtual === 'NENHUM' ? 'checked' : ''}>
              <div class="flex-grow-1">
                <strong class="text-danger d-block"><i class="bi bi-eye-slash-fill me-1"></i> 5. Ocultar / Suspender Visualização</strong>
                <small class="text-muted">Suspender temporariamente a exibição de notas no portal (ex: para conselhos de notas).</small>
              </div>
            </label>
          </div>
        </div>

        <!-- 2ª Possibilidade: Modo Baseado em Datas (Agendado) -->
        <div id="painelPubNotasDatas" class="${modoAtual === 'DATAS' ? '' : 'd-none'}">
          <div class="alert alert-info py-2 small mb-3">
            <i class="bi bi-calendar-event-fill me-1"></i> Defina os intervalos de datas oficiais para visualização automática das notas no portal.
          </div>
          <div class="list-group mb-3 shadow-sm">
            <!-- 1. I Trimestre -->
            <div class="list-group-item p-3">
              <div class="d-flex align-items-center justify-content-between mb-2">
                <strong class="text-primary"><i class="bi bi-1-circle-fill me-1"></i> 1. I Trimestre (Apenas 1º Trimestre)</strong>
                <small class="text-muted">Apenas I Trimestre visível no período</small>
              </div>
              <p class="small text-muted mb-2">Dentro deste período, apenas notas, testes e média do I Trimestre ficam visíveis para os alunos.</p>
              <div class="row g-2 align-items-center">
                <div class="col-6">
                  <label class="form-label small text-muted mb-1">Data Início:</label>
                  <input type="date" id="pubDataInicioT1" class="form-control form-control-sm" value="${dataInicioT1}">
                </div>
                <div class="col-6">
                  <label class="form-label small text-muted mb-1">Data Fim:</label>
                  <input type="date" id="pubDataFimT1" class="form-control form-control-sm" value="${dataFimT1}">
                </div>
              </div>
            </div>

            <!-- 2. I e II Trimestre -->
            <div class="list-group-item p-3">
              <div class="d-flex align-items-center justify-content-between mb-2">
                <strong class="text-primary"><i class="bi bi-2-circle-fill me-1"></i> 2. I e II Trimestre (1º e 2º Trimestre)</strong>
                <small class="text-muted">Avaliações do I e II Trimestres visíveis</small>
              </div>
              <p class="small text-muted mb-2">Dentro deste período, as avaliações do I e II Trimestres ficam disponíveis para consulta.</p>
              <div class="row g-2 align-items-center">
                <div class="col-6">
                  <label class="form-label small text-muted mb-1">Data Início:</label>
                  <input type="date" id="pubDataInicioT2" class="form-control form-control-sm" value="${dataInicioT2}">
                </div>
                <div class="col-6">
                  <label class="form-label small text-muted mb-1">Data Fim:</label>
                  <input type="date" id="pubDataFimT2" class="form-control form-control-sm" value="${dataFimT2}">
                </div>
              </div>
            </div>

            <!-- 4. Todos os Trimestres -->
            <div class="list-group-item p-3">
              <div class="d-flex align-items-center justify-content-between mb-2">
                <strong class="text-success"><i class="bi bi-check-all me-1"></i> 4. Todos os Trimestres (I, II e III)</strong>
                <small class="text-muted">Todas as notas e Média Final visíveis</small>
              </div>
              <p class="small text-muted mb-2">Publicação completa de todas as notas do ano (I, II, III trimestres e Média Final).</p>
              <div class="row g-2 align-items-center">
                <div class="col-6">
                  <div class="d-flex justify-content-between align-items-center mb-1">
                    <label class="form-label small text-muted mb-0">Data Início:</label>
                    <a href="javascript:void(0)" class="text-decoration-none small text-primary" style="font-size: 0.72rem;" onclick="document.getElementById('pubDataInicioTodos').value = new Date().toISOString().split('T')[0]"><i class="bi bi-clock me-1"></i>Hoje</a>
                  </div>
                  <input type="date" id="pubDataInicioTodos" class="form-control form-control-sm" value="${dataInicioTodos}">
                  <small class="text-muted d-block mt-1" style="font-size: 0.72rem;">Início da visualização oficial.</small>
                </div>
                <div class="col-6">
                  <div class="d-flex justify-content-between align-items-center mb-1">
                    <label class="form-label small text-muted mb-0">Data Fim:</label>
                    <a href="javascript:void(0)" id="btnToggleFimTodos" class="text-decoration-none small text-muted" style="font-size: 0.72rem;" onclick="alternarModoFimTodos()">
                      ${dataFimTodos ? '<i class=\"bi bi-infinity me-1\"></i>Visualizar por Infinito' : '<i class=\"bi bi-pencil me-1\"></i>Definir prazo limite'}
                    </a>
                  </div>
                  <div id="campoFimTodosInfinito" class="${dataFimTodos ? 'd-none' : ''}">
                    <div class="input-group input-group-sm">
                      <span class="input-group-text bg-success bg-opacity-10 text-success border-success border-opacity-25 fw-bold"><i class="bi bi-infinity fs-6"></i></span>
                      <input type="text" class="form-control form-control-sm bg-success bg-opacity-10 text-success fw-bold border-success border-opacity-25" value="Visualizar por Infinito" readonly disabled>
                    </div>
                    <small class="text-success d-block mt-1" style="font-size: 0.72rem;">
                      <i class="bi bi-check2-circle me-1"></i>Visualização contínua e permanente sem data limite.
                    </small>
                  </div>
                  <div id="campoFimTodosData" class="${dataFimTodos ? '' : 'd-none'}">
                    <input type="date" id="pubDataFimTodos" class="form-control form-control-sm" value="${dataFimTodos}">
                    <small class="text-muted d-block mt-1" style="font-size: 0.72rem;">Data de encerramento da visualização.</small>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="alert alert-light border py-2 px-3 small text-muted mb-3">
            <i class="bi bi-clock-history me-1 text-primary"></i> <strong>Controlo Automático:</strong> Fora dos períodos definidos acima, as notas dos alunos ficarão automaticamente ocultas / suspensas. Para <strong>Todos os Trimestres</strong>, a visualização vigora por tempo infinito a partir da Data Início.
          </div>
        </div>

        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-secondary btn-sm" onclick="fecharModal()">Cancelar</button>
          <button type="button" class="btn btn-primary btn-sm fw-bold px-3 shadow-sm" style="background-color: #6200ea; border-color: #6200ea;" onclick="salvarPublicacaoNotasDapModal()">
            <i class="bi bi-check-circle-fill me-1"></i> Aplicar e Publicar
          </button>
        </div>
      </div>
    `;

    abrirModal('Publicação de Notas aos Alunos (DAP / Direcção)', htmlModal);
  } catch (err) {
    alert(err.message || 'Erro ao carregar opções de publicação de notas');
  }
}

async function salvarPublicacaoNotasDapModal() {
  const modoAtivo = window._sigeModoPubNotasModal || 'MANUAL';
  let payload = { modo_publicacao_notas: modoAtivo };

  if (modoAtivo === 'MANUAL') {
    const selecionado = document.querySelector('input[name="radioPubNotasDap"]:checked')?.value || 'TODOS';
    payload.publicacao_notas_trimestre = selecionado;
    payload.permitir_visualizacao_notas = (selecionado !== 'NENHUM');
  } else {
    payload.data_inicio_pub_t1 = document.getElementById('pubDataInicioT1')?.value || null;
    payload.data_fim_pub_t1 = document.getElementById('pubDataFimT1')?.value || null;
    payload.data_inicio_pub_t2 = document.getElementById('pubDataInicioT2')?.value || null;
    payload.data_fim_pub_t2 = document.getElementById('pubDataFimT2')?.value || null;
    payload.data_inicio_pub_todos = document.getElementById('pubDataInicioTodos')?.value || null;
    const campoFimData = document.getElementById('campoFimTodosData');
    if (campoFimData && !campoFimData.classList.contains('d-none')) {
      payload.data_fim_pub_todos = document.getElementById('pubDataFimTodos')?.value || null;
    } else {
      payload.data_fim_pub_todos = null;
    }
  }

  try {
    const res = await apiFetch('/api/v1/escola-admin/toggle-notas', {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
    if (res.success) {
      const d = res.data;
      if (state.tenant) {
        state.tenant.publicacao_notas_trimestre = d.publicacao_notas_trimestre;
        state.tenant.permitir_visualizacao_notas = d.permitir_visualizacao_notas;
        state.tenant.modo_publicacao_notas = d.modo_publicacao_notas;
      }
      atualizarBotaoToggleNotasDap(d);
      fecharModal();
      alert(res.message || 'Publicação de notas actualizada com sucesso!');
    }
  } catch (err) {
    alert(err.message || 'Erro ao salvar publicação de notas');
  }
}

function atualizarBotaoToggleNotasDap(dadosOuPublicacao, permitir) {
  const btn = document.getElementById('btnToggleNotasDap');
  const icon = document.getElementById('iconToggleNotasDap');
  const label = document.getElementById('labelToggleNotasDap');
  if (!btn || !label) return;

  let pub = 'TODOS';
  let ativa = true;
  let modo = 'MANUAL';
  let resolucao = null;

  if (typeof dadosOuPublicacao === 'object' && dadosOuPublicacao !== null) {
    pub = dadosOuPublicacao.publicacao_notas_trimestre || (dadosOuPublicacao.resolvido?.publicacao) || 'TODOS';
    ativa = dadosOuPublicacao.permitir_visualizacao_notas !== false;
    modo = dadosOuPublicacao.modo_publicacao_notas || 'MANUAL';
    resolucao = dadosOuPublicacao.resolvido;
  } else if (typeof dadosOuPublicacao === 'string') {
    pub = dadosOuPublicacao;
    ativa = typeof permitir === 'boolean' ? permitir : (state.tenant?.permitir_visualizacao_notas !== false);
    modo = state.tenant?.modo_publicacao_notas || 'MANUAL';
  } else {
    pub = state.tenant?.publicacao_notas_trimestre || 'TODOS';
    ativa = state.tenant?.permitir_visualizacao_notas !== false;
    modo = state.tenant?.modo_publicacao_notas || 'MANUAL';
  }

  if (modo === 'DATAS') {
    const resPub = resolucao?.publicacao || pub;
    const resPerm = resolucao?.permitir !== false && ativa && resPub !== 'NENHUM';
    if (!resPerm || resPub === 'NENHUM') {
      btn.className = 'btn btn-outline-secondary btn-sm ped-only';
      if (icon) icon.className = 'bi bi-calendar-x me-1';
      label.textContent = 'Notas: Fora de Prazo (Datas)';
    } else if (resPub === '1_TRIMESTRE') {
      btn.className = 'btn btn-outline-info btn-sm ped-only';
      if (icon) icon.className = 'bi bi-calendar-check me-1';
      label.textContent = 'Notas: I Trimestre (Datas)';
    } else if (resPub === '2_TRIMESTRE') {
      btn.className = 'btn btn-outline-primary btn-sm ped-only';
      if (icon) icon.className = 'bi bi-calendar-check me-1';
      label.textContent = 'Notas: I e II (Datas)';
    } else {
      btn.className = 'btn btn-outline-success btn-sm ped-only';
      if (icon) icon.className = 'bi bi-calendar2-check-fill me-1';
      label.textContent = 'Notas: Todos (Datas)';
    }
  } else {
    // Modo MANUAL
    if (!ativa || pub === 'NENHUM') {
      btn.className = 'btn btn-outline-danger btn-sm ped-only';
      if (icon) icon.className = 'bi bi-eye-slash-fill me-1';
      label.textContent = 'Notas: Ocultas';
    } else if (pub === '1_TRIMESTRE') {
      btn.className = 'btn btn-outline-info btn-sm ped-only';
      if (icon) icon.className = 'bi bi-1-circle-fill me-1';
      label.textContent = 'Notas: I Trimestre';
    } else if (pub === '2_TRIMESTRE') {
      btn.className = 'btn btn-outline-primary btn-sm ped-only';
      if (icon) icon.className = 'bi bi-2-circle-fill me-1';
      label.textContent = 'Notas: I e II Trimestre';
    } else if (pub === '3_TRIMESTRE') {
      btn.className = 'btn btn-outline-warning btn-sm ped-only';
      if (icon) icon.className = 'bi bi-3-circle-fill me-1';
      label.textContent = 'Notas: III Trimestre';
    } else {
      btn.className = 'btn btn-outline-success btn-sm ped-only';
      if (icon) icon.className = 'bi bi-check-all me-1';
      label.textContent = 'Notas: Todos (I, II e III)';
    }
  }
}



async function carregarPerfilDocenteIndividual() {
  const container = document.getElementById('perfilDocenteConteudo');
  if (!container) return;

  container.innerHTML = '<div class="col-12 text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar o seu perfil...</p></div>';

  try {
    const res = await apiFetch('/api/v1/professores/meu-perfil');
    if (!res.success) return;
    const p = res.data;

    const turmasCards = (p.alocacoes || []).map(al => `
      <div class="col-md-4">
        <div class="card border p-3 h-100 shadow-sm">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="badge bg-primary">${al.turma?.grau_ano || 'Ensino Geral'}</span>
            <small class="text-muted">${al.turma?.turno || 'Diurno'}</small>
          </div>
          <h6 class="fw-bold mb-1">${al.disciplina?.nome} (${al.disciplina?.codigo})</h6>
          <p class="small text-muted mb-3">Turma: <strong>${al.turma?.nome}</strong> | Sala: ${al.turma?.sala || '-'}</p>
          <button class="btn btn-outline-primary btn-sm w-100 mt-auto" onclick="abrirCadernetaAlocacao('${al.id}')">
            <i class="bi bi-journal-check me-1"></i> Abrir Caderneta
          </button>
        </div>
      </div>
    `).join('') || '<div class="col-12"><p class="text-muted">Nenhuma disciplina alocada actualmente.</p></div>';

    container.innerHTML = `
      <div class="col-md-4">
        <div class="card p-3 border text-center">
          <i class="bi bi-person-circle fs-1 text-primary mb-2"></i>
          <h5 class="fw-bold mb-0">${p.nome} ${p.apelido || ''}</h5>
          <div class="mt-1 mb-2 d-flex justify-content-center gap-1 flex-wrap">
            <span class="badge bg-dark text-white font-monospace">${p.codigo || 'PR-FIXO'}</span>
            <span class="badge bg-primary bg-opacity-10 text-primary">${p.carreira || 'Docente'}</span>
          </div>
          <p class="small text-muted mb-1"><i class="bi bi-book me-1"></i>Especialidade: <strong>${p.especialidade}</strong></p>
          <p class="small text-muted mb-1"><i class="bi bi-telephone me-1"></i>${p.telefone || '-'}</p>
          <p class="small text-muted mb-2"><i class="bi bi-envelope me-1"></i>${p.email}</p>
          <button class="btn btn-outline-primary btn-sm w-100 mt-1 fw-semibold" onclick="modalRedefinirMinhaSenha()">
            <i class="bi bi-key-fill me-1"></i> Alterar a Minha Senha
          </button>
        </div>
      </div>

      <div class="col-md-8">
        <div class="card p-3 border h-100">
          <h6 class="fw-bold mb-3 text-primary border-bottom pb-2">Dados Funcionais e Institucionais</h6>
          <div class="row g-2 small">
            <div class="col-md-6"><strong>Código Fixo Docente:</strong> <span class="badge bg-dark text-white font-monospace">${p.codigo || '-'}</span></div>
            <div class="col-md-6"><strong>Nacionalidade:</strong> ${p.nacionalidade || 'Moçambicana'}</div>
            <div class="col-md-6"><strong>Província:</strong> ${p.provincia || '-'}</div>
            <div class="col-md-6"><strong>Distrito:</strong> ${p.distrito || '-'}</div>
            <div class="col-md-6"><strong>Documento:</strong> ${p.tipo_documento || 'BI'} (${p.numero_documento || '-'})</div>
            <div class="col-md-6"><strong>Carga Horária:</strong> ${p.carga_horaria_semanal || 20}h semanais</div>
            <div class="col-md-12"><strong>Instituição:</strong> ${p.escola?.nome || '-'} ${p.escola?.codigo_escola ? `(<span class="font-monospace fw-bold">${p.escola.codigo_escola}</span>)` : ''}</div>
          </div>
        </div>
      </div>

      <div class="col-12">
        <h6 class="fw-bold mb-3 text-dark border-bottom pb-2"><i class="bi bi-collection me-2"></i>As Minhas Turmas e Disciplinas Alocadas</h6>
        <div class="row g-3">
          ${turmasCards}
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="col-12 text-center text-danger py-4"><i class="bi bi-exclamation-circle me-1"></i>${err.message || 'Erro ao carregar perfil'}</div>`;
  }
}

function abrirCadernetaAlocacao(alocId) {
  state.alocacaoAtualId = alocId;
  const select = document.getElementById('cadernetaAlocacaoSelect');
  if (select) select.value = alocId;
  navegarPara('caderneta');
  carregarCadernetaDocente();
}



let cacheUsuariosCofre = [];

async function carregarCofreUsuarios() {
  const tbody = document.getElementById('tabelaCofreUsuariosCorpo');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A aceder ao cofre seguro...</p></td></tr>';

  try {
    const res = await apiFetch('/api/v1/escola-admin/usuarios-credenciais');
    if (!res.success) return;
    cacheUsuariosCofre = res.data;
    renderizarTabelaCofre(cacheUsuariosCofre);
  } catch (err) {
    const safeMsg = (err.message || 'Acesso não autorizado ao cofre').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4"><i class="bi bi-shield-x me-1"></i>${safeMsg}</td></tr>`;
  }
}

function renderizarTabelaCofreUsuarios(lista) {
  renderizarTabelaCofre(lista);
}
window.renderizarTabelaCofreUsuarios = renderizarTabelaCofreUsuarios;

function renderizarTabelaCofre(lista) {
  const tbody = document.getElementById('tabelaCofreUsuariosCorpo');
  if (!tbody) return;

  if (lista.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">Nenhum utilizador encontrado.</td></tr>';
    return;
  }

  tbody.innerHTML = lista.map(u => {
    let dtAcesso = 'Nunca';
    if (u.ultimo_acesso) {
      const dt = new Date(u.ultimo_acesso);
      dtAcesso = dt.toLocaleDateString('pt-PT') + ' ' + dt.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
    }

    const codEscapado = (u.codigo_acesso || '').replace(/'/g, "\\'");
    const badgeSenha = u.senha_redefinida
      ? '<span class="badge bg-info bg-opacity-10 text-dark border border-info ms-1" style="font-size: 0.68rem;" title="O utilizador personalizou a sua senha">Senha Redefinida</span>'
      : '<span class="badge bg-warning bg-opacity-25 text-dark border border-warning ms-1" style="font-size: 0.68rem;" title="Senha inicial activa: basta repetir o código de acesso">Senha = Código</span>';

    return `
      <tr>
        <td>
          <span class="badge bg-dark text-white font-monospace">${u.codigo_acesso || '-'}</span>
          <div class="mt-1">${badgeSenha}</div>
        </td>
        <td><strong>${u.nome}</strong></td>
        <td><code>${u.email}</code></td>
        <td><span class="badge bg-secondary">${u.role}</span></td>
        <td>${u.telefone || '-'}</td>
        <td><small class="text-muted">${dtAcesso}</small></td>
        <td><span class="badge ${u.ativo ? 'bg-success' : 'bg-danger'}">${u.ativo ? 'Activo' : 'Inactivo'}</span></td>
        <td class="text-end">
          <button class="btn btn-outline-warning btn-sm" onclick="modalRedefinirSenhaUsuario('${u.id}', '${u.nome.replace(/'/g, "\\'")}', '${codEscapado}')">
            <i class="bi bi-key me-1"></i> Gerir Senha
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function filtrarUsuariosCofre() {
  const termo = (document.getElementById('filtroUsuarioCofre')?.value || '').toLowerCase();
  const role = document.getElementById('filtroRoleCofre')?.value || '';

  const filtrados = cacheUsuariosCofre.filter(u => {
    const bateTexto =
      (u.nome || '').toLowerCase().includes(termo) ||
      (u.email || '').toLowerCase().includes(termo) ||
      (u.codigo_acesso || '').toLowerCase().includes(termo);
    const bateRole = !role || u.role === role;
    return bateTexto && bateRole;
  });

  renderizarTabelaCofre(filtrados);
}

function modalRedefinirSenhaUsuario(userId, userNome, codigoAcesso = '') {
  abrirModal(`Gerir / Redefinir Palavra-passe: ${userNome}`, `
    <form id="formRedefinirSenhaUsuario">
      <div class="p-3 bg-light rounded border mb-3 small">
        <div><strong>Utilizador:</strong> ${userNome}</div>
        ${codigoAcesso ? `<div class="mt-1"><strong>Código Oficial:</strong> <code class="fw-bold text-dark">${codigoAcesso}</code></div>` : ''}
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Definir Nova Palavra-passe Personalizada</label>
        <input type="password" id="novaSenhaUsuarioInput" class="form-control" placeholder="Mínimo 4 caracteres (ou use o botão abaixo para repor o código)" required minlength="4">
      </div>
      <button type="submit" class="btn btn-warning fw-semibold w-100 mb-2">
        <i class="bi bi-check-lg me-1"></i> Gravar Nova Senha
      </button>
      ${codigoAcesso ? `
        <button type="button" class="btn btn-outline-dark btn-sm w-100" onclick="reporSenhaParaCodigoOficial('${userId}', '${codigoAcesso}')">
          <i class="bi bi-arrow-counterclockwise me-1"></i> Repor Senha Padrão (Repetir Código: <strong>${codigoAcesso}</strong>)
        </button>
      ` : ''}
    </form>
  `);

  document.getElementById('formRedefinirSenhaUsuario').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const novaSenha = document.getElementById('novaSenhaUsuarioInput').value;
      await apiFetch(`/api/v1/auth/usuarios/${userId}/redefinir-senha`, {
        method: 'PUT',
        body: JSON.stringify({ novaSenha })
      });

      mostrarNotificacao('Palavra-passe actualizada com sucesso!', 'success');
      fecharModal();
      carregarCofreUsuarios();
    } catch (err) {
      alert(err.message || 'Erro ao actualizar palavra-passe');
    }
  });
}

async function reporSenhaParaCodigoOficial(userId, codigoAcesso) {
  try {
    const res = await apiFetch(`/api/v1/auth/usuarios/${userId}/redefinir-senha`, {
      method: 'PUT',
      body: JSON.stringify({ repor_codigo: true })
    });
    mostrarNotificacao(res?.message || `Senha reposta para o código ${codigoAcesso}!`, 'success');
    fecharModal();
    carregarCofreUsuarios();
  } catch (err) {
    alert(err.message || 'Erro ao repor senha para o código oficial');
  }
}



let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const btn = document.getElementById('btnInstallPwa');
  if (btn) btn.classList.remove('d-none');
});

async function instalarPwa() {
  if (!deferredPrompt) {
    alert('A aplicação SIGE já está pronta para uso no seu navegador.');
    return;
  }
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  if (outcome === 'accepted') {
    const btn = document.getElementById('btnInstallPwa');
    if (btn) btn.classList.add('d-none');
  }
  deferredPrompt = null;
}


function renderizarPautaGeralImpressao(d) {
  const preview = document.getElementById('printAreaPreview');
  preview.style.display = 'block';
  const ano = d.turma?.ano_letivo || '2026';
  const turmaId = d.turma?.id;
  const safeTurma = (d.turma?.nome || 'Turma').replace(/[^a-zA-Z0-9]/g, '_');

  const formatNota = (val) => {
    if (val === null || val === undefined || isNaN(val) || val <= 0) return '<span class="text-muted">-</span>';
    const num = Number(val);
    const cls = num >= 9.5 ? 'text-dark fw-semibold' : 'text-danger fw-bold';
    return `<span class="${cls}">${Math.round(num)}</span>`;
  };

  const thDisciplinas = d.disciplinas.map(disc => {
    const nomeCompleto = obterNomeCompletoDisciplina(disc.nome || disc.codigo);
    return `<th colspan="4" class="text-center border-start border-end fw-bold" style="background-color: #eef2ff !important; color: #4338ca !important; border-color: #c7d2fe !important; font-size: 0.82rem; padding: 4px 6px;">${nomeCompleto}</th>`;
  }).join('');

  const thSubDisciplinas = d.disciplinas.map(() => 
    `<th style="font-size: 0.72rem;">1º</th><th style="font-size: 0.72rem;">2º</th><th style="font-size: 0.72rem;">3º</th><th style="font-size: 0.72rem; background-color: #e2e8f0 !important; font-weight: bold;">MFD</th>`
  ).join('');

  let trsAlunos = d.alunos.map((a, idx) => {
    const tdDisciplinas = d.disciplinas.map(disc => {
      const nd = a.notasDisciplinas[disc.codigo || disc.id] || a.notasDisciplinas[disc.id] || a.notasDisciplinas[disc.nome] || {};
      return `
        <td style="font-size: 0.82rem;">${formatNota(nd.t1)}</td>
        <td style="font-size: 0.82rem;">${formatNota(nd.t2)}</td>
        <td style="font-size: 0.82rem;">${formatNota(nd.t3)}</td>
        <td style="background-color: #f1f5f9 !important; font-weight: bold; font-size: 0.82rem;">${(nd.t1 !== '-' && nd.t2 !== '-' && nd.t3 !== '-' && nd.t1 !== null && nd.t2 !== null && nd.t3 !== null && Number(nd.t1) > 0 && Number(nd.t2) > 0 && Number(nd.t3) > 0) ? formatNota(nd.mfd) : '<span class="text-muted">-</span>'}</td>
      `;
    }).join('');

    let badgeResultado = '';
    const resTexto = (a.resultadoFinal || a.resultado || '').trim();
    if (resTexto === 'A' || resTexto === 'Aprovado') {
      badgeResultado = '<span class="fw-bold" style="font-weight: 700; color: #15803d !important;">Aprovado</span>';
    } else if (resTexto === 'R' || resTexto === 'Reprovado') {
      badgeResultado = '<span class="fw-bold text-danger" style="font-weight: 700; color: #dc2626 !important;">Reprovado</span>';
    } else if (resTexto === 'D' || resTexto === 'Desistente') {
      badgeResultado = '<span class="fw-bold text-secondary">Desistente</span>';
    } else if (resTexto === 'T' || resTexto === 'Transferido') {
      badgeResultado = '<span class="fw-bold text-secondary">Transferido</span>';
    } else {
      badgeResultado = `<span class="fw-bold text-secondary">${resTexto || '-'}</span>`;
    }

    const badgeGen = a.genero === 'F' 
      ? '<span class="badge" style="background-color: #0ea5e9; color: #ffffff; font-size: 0.72rem; padding: 2px 6px;">F</span>' 
      : '<span class="badge" style="background-color: #334155; color: #ffffff; font-size: 0.72rem; padding: 2px 6px;">M</span>';

    const nomeCompletoAluno = (a.nomeCompleto || `${a.nome || ''} ${a.apelido || ''}`.trim()).toUpperCase();

    return `
      <tr>
        <td><strong>${a.numero || (idx + 1)}</strong></td>
        <td class="text-start ps-3 fw-bold" style="font-size: 0.85rem;">${nomeCompletoAluno}</td>
        <td>${badgeGen}</td>
        ${tdDisciplinas}
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${formatNota(a.mediasTrimestrais.t1)}</td>
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${formatNota(a.mediasTrimestrais.t2)}</td>
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${formatNota(a.mediasTrimestrais.t3)}</td>
        <td style="font-size: 0.82rem;">${a.negativas.t1 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t1}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="font-size: 0.82rem;">${a.negativas.t2 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t2}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="font-size: 0.82rem;">${a.negativas.t3 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t3}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${a.negativas.fimDoAno > 0 ? `<span class="text-danger fw-bold">${a.negativas.fimDoAno}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="background-color: #e0e7ff; font-weight: bold; color: #1e1b4b; font-size: 0.95rem;">${formatNota(a.mediaFinalGeral)}</td>
        <td>${badgeResultado}</td>
      </tr>
    `;
  }).join('');

  preview.innerHTML = `
    <div class="no-print mb-3 p-3 bg-light border rounded d-flex justify-content-between align-items-center flex-wrap gap-2">
      <div>
        <strong class="text-primary fs-5"><i class="bi bi-table me-2"></i>Pauta Geral: ${d.turma.nome} (${d.turma.grau_ano})</strong>
        <span class="d-block small text-muted">Ano Lectivo: ${ano} | Turno: ${d.turma.turno || 'Diurno'} | Director de Turma: ${d.turma.director_turma || '-'}</span>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-success btn-sm fw-semibold" onclick="exportarPautaGeralExcel('${turmaId}', '${ano}')">
          <i class="bi bi-file-earmark-excel me-1"></i> Exportar Excel (.xlsx)
        </button>
        <button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarPautaGeralPdf()">
          <i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF (A4 Paisagem)
        </button>
        <button class="btn btn-primary btn-sm fw-semibold" onclick="imprimirDocumentoComTitulo('Pauta_${safeTurma}_${ano}')">
          <i class="bi bi-printer me-1"></i> Imprimir / Guardar em PDF
        </button>
      </div>
    </div>

    <div id="subViewPautaGeral" class="printable-document p-3 bg-white border rounded shadow-sm" style="overflow-x: auto; font-family: 'Times New Roman', Times, serif;">
      <!-- Cabeçalho Oficial a 2cm antes do conteúdo -->
      <div class="text-center border-bottom pb-2" style="margin-bottom: 20mm !important;">
        <img src="/img/emblema-mocambique.png" style="width: 52px; height: 52px; margin-bottom: 2px; object-fit: contain;" alt="Emblema Nacional">
        <h6 class="fw-bold mb-0 text-uppercase" style="letter-spacing: 0.5px;">REPÚBLICA DE MOÇAMBIQUE</h6>
        <small class="text-muted fw-semibold text-uppercase">GOVERNO DA PROVÍNCIA DE ${(d.escola.provincia || 'MAPUTO').toUpperCase()} | DISTRITO DE ${(d.escola.distrito || 'CIDADE DE MAPUTO').toUpperCase()}</small>
        <h5 class="fw-bold text-dark my-1">${(d.escola.nome || 'Escola Secundária').toUpperCase()}</h5>
        <div class="fw-bold text-primary small" style="color: #4338ca !important; font-size: 1.05rem;">PAUTA OFICIAL DE APROVEITAMENTO PEDAGÓGICO — ANO LECTIVO ${ano}</div>
        <small class="text-muted">Turma: <strong>${d.turma.nome}</strong> | Classe: <strong>${d.turma.grau_ano}</strong> | Turno: <strong>${d.turma.turno || 'Diurno'}</strong> | Director de Turma: <strong>${d.turma.director_turma || '-'}</strong></small>
      </div>

      <!-- Tabela da Pauta -->
      <div class="table-responsive">
        <table class="table table-bordered table-sm table-hover align-middle text-center small mb-0">
          <thead class="table-light">
            <tr>
              <th rowspan="2" class="align-middle">Nº</th>
              <th rowspan="2" class="align-middle text-start ps-3" style="min-width: 210px; font-size: 0.85rem;">Nome Completo do Aluno</th>
              <th rowspan="2" class="align-middle">Gén</th>
              ${thDisciplinas}
              <th colspan="3" class="fw-semibold" style="background-color: #f8fafc !important; font-size: 0.75rem;">Médias Trimestrais</th>
              <th colspan="4" class="fw-semibold" style="background-color: #f8fafc !important; font-size: 0.75rem;">Disciplinas Negativas</th>
              <th rowspan="2" class="align-middle fw-bold" style="background-color: #4f46e5 !important; color: #ffffff !important; font-size: 0.8rem;">Média Geral</th>
              <th rowspan="2" class="align-middle fw-bold" style="background-color: #1e293b !important; color: #ffffff !important; font-size: 0.8rem;">Resultado</th>
            </tr>
            <tr>
              ${thSubDisciplinas}
              <th>1º</th><th>2º</th><th>3º</th>
              <th>1º</th><th>2º</th><th>3º</th><th>Total</th>
            </tr>
          </thead>
          <tbody>
            ${trsAlunos}
          </tbody>
        </table>
      </div>

      <!-- Assinaturas Oficiais da Pauta a 1cm da parte inferior -->
      <div class="row text-center mx-0" style="font-size: 9.5pt; margin-top: 25px; padding-bottom: 10mm;">
        <div class="col-4">
          <div style="border-top: 1.2px solid #222; width: 75%; margin: 0 auto 6px;"></div>
          <strong>O Director de Turma</strong>
          <div style="font-size: 8.5pt; color: #475569;">${d.turma?.director_turma || ''}</div>
        </div>
        <div class="col-4">
          <div style="border-top: 1.2px solid #222; width: 75%; margin: 0 auto 6px;"></div>
          <strong>O Director Pedagógico (DAP)</strong>
        </div>
        <div class="col-4">
          <div style="border-top: 1.2px solid #222; width: 75%; margin: 0 auto 6px;"></div>
          <strong>O Director da Escola</strong>
          <div style="font-size: 8.5pt; color: #475569;">${d.escola?.director || ''}</div>
        </div>
      </div>
    </div>
  `;
}

// ==================== PAINEL DO DIRECTOR DE TURMA ====================
let dtTurmaAtivaId = null;
let dtAbaAtiva = 'pauta';

async function carregarPainelDirectorTurma() {
  const select = document.getElementById('dtTurmaSelect');
  if (!select) return;

  try {
    const res = await apiFetch('/api/v1/escola-admin/turmas');
    if (!res.success || !res.data.length) {
      select.innerHTML = '<option value="">Nenhuma turma cadastrada</option>';
      return;
    }

    const turmas = res.data;
    const turmasDirigidas = turmas.filter(t => 
      (t.director_turma_id && (t.director_turma_id === state.user?.id || t.director_turma_id === state.user?.professor_id)) ||
      (t.director_turma && (t.director_turma.id === state.user?.professor_id || t.director_turma.nome?.toLowerCase() === state.user?.nome?.toLowerCase()))
    );

    select.innerHTML = turmas.map(t => {
      const isMinha = turmasDirigidas.some(m => m.id === t.id);
      return `<option value="${t.id}">${t.nome} (${t.grau_ano} - ${t.turno || 'Diurno'})${isMinha ? ' ⭐ (Sua Turma de Direcção)' : ''}</option>`;
    }).join('');

    if (turmasDirigidas.length > 0) {
      dtTurmaAtivaId = turmasDirigidas[0].id;
    } else if (!dtTurmaAtivaId && turmas.length > 0) {
      dtTurmaAtivaId = turmas[0].id;
    }

    if (dtTurmaAtivaId) {
      select.value = dtTurmaAtivaId;
      await aoSelecionarTurmaDT(dtTurmaAtivaId);
    }
  } catch (err) {
    select.innerHTML = '<option value="">Erro ao carregar turmas</option>';
  }
}

async function aoSelecionarTurmaDT(turmaId) {
  if (!turmaId) return;
  dtTurmaAtivaId = turmaId;

  // Carregar parâmetros salvos do conselho
  const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
  let cp = {};
  if (savedParamsRaw) {
    try {
      cp = JSON.parse(savedParamsRaw) || {};
      // Se continha os dados fictícios hardcoded de demonstração antigos, descartar
      if (cp.dataT1 === '26/05/2026' && cp.dataT2 === '01/09/2026') {
        cp = {};
        localStorage.removeItem('sige_acta_params_' + turmaId);
      }
    } catch (e) {
      cp = {};
    }
  }

  document.getElementById('dtPresidenteT1').value = cp.presidenteT1 || '';
  document.getElementById('dtPresidenteT2').value = cp.presidenteT2 || '';
  document.getElementById('dtPresidenteT3').value = cp.presidenteT3 || '';

  document.getElementById('dtDataT1').value = formatarParaInputDate(cp.dataT1);
  document.getElementById('dtDataT2').value = formatarParaInputDate(cp.dataT2);
  document.getElementById('dtDataT3').value = formatarParaInputDate(cp.dataT3);

  document.getElementById('dtHIni1').value = cp.horaInicioT1 || '';
  document.getElementById('dtMIni1').value = cp.minInicioT1 || '';
  document.getElementById('dtHFim1').value = cp.horaFimT1 || '';
  document.getElementById('dtMFim1').value = cp.minFimT1 || '';

  document.getElementById('dtHIni2').value = cp.horaInicioT2 || '';
  document.getElementById('dtMIni2').value = cp.minInicioT2 || '';
  document.getElementById('dtHFim2').value = cp.horaFimT2 || '';
  document.getElementById('dtMFim2').value = cp.minFimT2 || '';

  document.getElementById('dtHIni3').value = cp.horaInicioT3 || '';
  document.getElementById('dtMIni3').value = cp.minInicioT3 || '';
  document.getElementById('dtHFim3').value = cp.horaFimT3 || '';
  document.getElementById('dtMFim3').value = cp.minFimT3 || '';

  await carregarDadosTurmaDT();
}

function limparParametrosSessaoDT() {
  if (!dtTurmaAtivaId) return alert('Selecione uma turma primeiro');
  localStorage.removeItem('sige_acta_params_' + dtTurmaAtivaId);

  document.getElementById('dtPresidenteT1').value = '';
  document.getElementById('dtPresidenteT2').value = '';
  document.getElementById('dtPresidenteT3').value = '';

  document.getElementById('dtDataT1').value = '';
  document.getElementById('dtDataT2').value = '';
  document.getElementById('dtDataT3').value = '';

  document.getElementById('dtHIni1').value = '';
  document.getElementById('dtMIni1').value = '';
  document.getElementById('dtHFim1').value = '';
  document.getElementById('dtMFim1').value = '';

  document.getElementById('dtHIni2').value = '';
  document.getElementById('dtMIni2').value = '';
  document.getElementById('dtHFim2').value = '';
  document.getElementById('dtMFim2').value = '';

  document.getElementById('dtHIni3').value = '';
  document.getElementById('dtMIni3').value = '';
  document.getElementById('dtHFim3').value = '';
  document.getElementById('dtMFim3').value = '';

  alert('Parâmetros da sessão limpos! A Acta da turma voltará a exibir as linhas pontilhadas oficiais em branco.');
  carregarDadosTurmaDT();
}

function salvarParametrosSessaoDT() {
  if (!dtTurmaAtivaId) return alert('Selecione uma turma primeiro');

  const params = {
    presidenteT1: document.getElementById('dtPresidenteT1').value,
    presidenteT2: document.getElementById('dtPresidenteT2').value,
    presidenteT3: document.getElementById('dtPresidenteT3').value,
    dataT1: document.getElementById('dtDataT1').value,
    dataT2: document.getElementById('dtDataT2').value,
    dataT3: document.getElementById('dtDataT3').value,
    horaInicioT1: document.getElementById('dtHIni1').value,
    minInicioT1: document.getElementById('dtMIni1').value,
    horaFimT1: document.getElementById('dtHFim1').value,
    minFimT1: document.getElementById('dtMFim1').value,
    horaInicioT2: document.getElementById('dtHIni2').value,
    minInicioT2: document.getElementById('dtMIni2').value,
    horaFimT2: document.getElementById('dtHFim2').value,
    minFimT2: document.getElementById('dtMFim2').value,
    horaInicioT3: document.getElementById('dtHIni3').value,
    minInicioT3: document.getElementById('dtMIni3').value,
    horaFimT3: document.getElementById('dtHFim3').value,
    minFimT3: document.getElementById('dtMFim3').value
  };

  localStorage.setItem('sige_acta_params_' + dtTurmaAtivaId, JSON.stringify(params));
  alert('Parâmetros da sessão do conselho salvos com sucesso! A Acta da turma foi atualizada.');
  carregarDadosTurmaDT();
}

function alternarAbaDT(aba) {
  dtAbaAtiva = aba;
  document.getElementById('dtTabPautaBtn').className = 'nav-link fw-bold ' + (aba === 'pauta' ? 'active' : '');
  document.getElementById('dtTabActaBtn').className = 'nav-link fw-bold ' + (aba === 'acta' ? 'active' : '');
  carregarDadosTurmaDT();
}

async function carregarDadosTurmaDT() {
  if (!dtTurmaAtivaId) return;
  const container = document.getElementById('dtDocumentoContainer');
  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar documento oficial da turma...</p></div>';

  try {
    if (dtAbaAtiva === 'pauta') {
      const res = await apiFetch(`/api/v1/pautas/turma/${dtTurmaAtivaId}/completa`);
      if (res.success) {
        const d = res.data;
        container.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom flex-wrap gap-2">
            <div>
              <h6 class="fw-bold text-dark mb-0">Pauta Geral: ${d.turma.nome} (${d.turma.grau_ano})</h6>
              <small class="text-muted">Ano Lectivo ${d.turma.ano_letivo} | Turno ${d.turma.turno || 'Diurno'}</small>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-outline-success btn-sm fw-semibold" onclick="exportarPautaGeralExcel('${dtTurmaAtivaId}', '${d.turma.ano_letivo}')">
                <i class="bi bi-file-earmark-excel me-1"></i> Exportar Excel (.xlsx)
              </button>
              <button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarPautaGeralPdf()">
                <i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF
              </button>
              <button class="btn btn-primary btn-sm fw-semibold" onclick="window.print()">
                <i class="bi bi-printer me-1"></i> Imprimir
              </button>
            </div>
          </div>
          <div id="subViewPautaGeral" class="table-responsive">
            <!-- Tabela idêntica para exportação e impressão -->
            ${gerarTabelaPautaHtml(d)}
          </div>
        `;
      }
    } else {
      // Acta do Conselho
      await carregarActaConselho(dtTurmaAtivaId);
      const containerActa = document.getElementById('containerActaConselhoCorpo');
      if (containerActa) {
        container.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom flex-wrap gap-2">
            <div>
              <h6 class="fw-bold text-dark mb-0">Acta Oficial do Conselho de Avaliação</h6>
              <small class="text-muted">Modelo Oficial MEC</small>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-outline-success btn-sm fw-semibold" onclick="exportarActaConselhoExcel('${dtTurmaAtivaId}')">
                <i class="bi bi-file-earmark-excel me-1"></i> Exportar Excel (.xlsx)
              </button>
              <button class="btn btn-outline-danger btn-sm fw-semibold" onclick="descarregarActaConselhoPdf()">
                <i class="bi bi-file-earmark-pdf me-1"></i> Descarregar PDF
              </button>
              <button class="btn btn-primary btn-sm fw-semibold" onclick="window.print()">
                <i class="bi bi-printer me-1"></i> Imprimir
              </button>
            </div>
          </div>
          <div id="subViewActaConselho">
            ${containerActa.innerHTML}
          </div>
        `;
      }
    }
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger">Erro ao carregar dados da turma: ${err.message}</div>`;
  }
}

function gerarTabelaPautaHtml(d) {
  const formatNota = (val) => {
    if (val === null || val === undefined || isNaN(val) || val <= 0) return '<span class="text-muted">-</span>';
    const num = Number(val);
    const cls = num >= 9.5 ? 'text-dark fw-semibold' : 'text-danger fw-bold';
    return `<span class="${cls}">${Math.round(num)}</span>`;
  };

  const thDisciplinas = d.disciplinas.map(disc => 
    `<th colspan="4" class="text-center border-start border-end fw-bold" style="background-color: #eef2ff !important; color: #4338ca !important; border-color: #c7d2fe !important; font-size: 0.82rem;">${obterNomeCompletoDisciplina(disc.nome || disc.codigo)}</th>`
  ).join('');

  const thSubDisciplinas = d.disciplinas.map(() => 
    `<th style="font-size: 0.72rem;">1º</th><th style="font-size: 0.72rem;">2º</th><th style="font-size: 0.72rem;">3º</th><th style="font-size: 0.72rem; background-color: #e2e8f0 !important; font-weight: bold;">MFD</th>`
  ).join('');

  let trsAlunos = d.alunos.map((a, idx) => {
    const tdDisciplinas = d.disciplinas.map(disc => {
      const nd = a.notasDisciplinas[disc.codigo || disc.id] || a.notasDisciplinas[disc.id] || a.notasDisciplinas[disc.nome] || {};
      return `
        <td style="font-size: 0.82rem;">${formatNota(nd.t1)}</td>
        <td style="font-size: 0.82rem;">${formatNota(nd.t2)}</td>
        <td style="font-size: 0.82rem;">${formatNota(nd.t3)}</td>
        <td style="background-color: #f1f5f9 !important; font-weight: bold; font-size: 0.82rem;">${(nd.t1 !== '-' && nd.t2 !== '-' && nd.t3 !== '-' && nd.t1 !== null && nd.t2 !== null && nd.t3 !== null && Number(nd.t1) > 0 && Number(nd.t2) > 0 && Number(nd.t3) > 0) ? formatNota(nd.mfd) : '<span class="text-muted">-</span>'}</td>
      `;
    }).join('');

    let badgeResultado = '';
    const resTexto = (a.resultadoFinal || a.resultado || '').trim();
    if (resTexto === 'A' || resTexto === 'Aprovado') {
      badgeResultado = '<span class="fw-bold" style="font-weight: 700; color: #15803d !important;">Aprovado</span>';
    } else if (resTexto === 'R' || resTexto === 'Reprovado') {
      badgeResultado = '<span class="fw-bold text-danger" style="font-weight: 700; color: #dc2626 !important;">Reprovado</span>';
    } else if (resTexto === 'D' || resTexto === 'Desistente') {
      badgeResultado = '<span class="fw-bold text-secondary">Desistente</span>';
    } else if (resTexto === 'T' || resTexto === 'Transferido') {
      badgeResultado = '<span class="fw-bold text-secondary">Transferido</span>';
    } else {
      badgeResultado = `<span class="fw-bold text-secondary">${resTexto || '-'}</span>`;
    }

    const badgeGen = a.genero === 'F' 
      ? '<span class="badge" style="background-color: #0ea5e9; color: #ffffff; font-size: 0.75rem; padding: 2px 6px;">F</span>' 
      : '<span class="badge" style="background-color: #334155; color: #ffffff; font-size: 0.75rem; padding: 2px 6px;">M</span>';

    const nomeCompleto = a.nomeCompleto || `${a.nome || ''} ${a.apelido || ''}`.trim() || 'Aluno';

    return `
      <tr>
        <td><strong>${a.numero || (idx + 1)}</strong></td>
        <td class="text-start ps-3" style="font-size: 0.85rem;"><strong>${nomeCompleto}</strong></td>
        <td>${badgeGen}</td>
        ${tdDisciplinas}
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${formatNota(a.mediasTrimestrais.t1)}</td>
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${formatNota(a.mediasTrimestrais.t2)}</td>
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${formatNota(a.mediasTrimestrais.t3)}</td>
        <td style="font-size: 0.82rem;">${a.negativas.t1 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t1}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="font-size: 0.82rem;">${a.negativas.t2 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t2}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="font-size: 0.82rem;">${a.negativas.t3 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t3}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="background-color: #f8fafc; font-size: 0.82rem;">${a.negativas.fimDoAno > 0 ? `<span class="text-danger fw-bold">${a.negativas.fimDoAno}</span>` : '<span class="text-muted">0</span>'}</td>
        <td style="background-color: #e0e7ff; font-weight: bold; color: #1e1b4b; font-size: 0.95rem;">${formatNota(a.mediaFinalGeral)}</td>
        <td>${badgeResultado}</td>
      </tr>
    `;
  }).join('');

  return `
    <div class="table-responsive">
      <table class="table table-bordered table-sm table-hover align-middle text-center small mb-0">
        <thead class="table-light">
          <tr>
            <th rowspan="2" class="align-middle">Nº</th>
            <th rowspan="2" class="align-middle text-start ps-3" style="min-width: 210px; font-size: 0.85rem;">Nome Completo do Aluno</th>
            <th rowspan="2" class="align-middle">Gén</th>
            ${thDisciplinas}
            <th colspan="3" class="fw-semibold" style="background-color: #f8fafc !important; font-size: 0.75rem;">Médias Trimestrais</th>
            <th colspan="4" class="fw-semibold" style="background-color: #f8fafc !important; font-size: 0.75rem;">Disciplinas Negativas</th>
            <th rowspan="2" class="align-middle fw-bold" style="background-color: #4f46e5 !important; color: #ffffff !important; font-size: 0.8rem;">Média Final</th>
            <th rowspan="2" class="align-middle fw-bold" style="background-color: #1e293b !important; color: #ffffff !important; font-size: 0.8rem;">Resultado</th>
          </tr>
          <tr>
            ${thSubDisciplinas}
            <th>1º</th><th>2º</th><th>3º</th>
            <th>1º</th><th>2º</th><th>3º</th><th>Total</th>
          </tr>
        </thead>
        <tbody>
          ${trsAlunos}
        </tbody>
      </table>
    </div>
  `;
}

async function eliminarEscolaSuperAdmin(escolaId, nome, codigo = '') {
  const rotulo = codigo ? `[${codigo}] ${nome}` : `[${nome}]`;
  if (!confirm(`ATENÇÃO ENGENHEIRO:\nTem a certeza que deseja ELIMINAR DEFINITIVAMENTE a instituição ${rotulo} e todos os seus dados?\nEsta operação não pode ser revertida!`)) return;

  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}`, {
      method: 'DELETE'
    });
    if (res.success) {
      alert(res.message || 'Escola eliminada com sucesso');
      carregarPainelSaaS();
      carregarEscolasSuperAdminSelect();
    }
  } catch (err) {
    alert(err.message || 'Erro ao eliminar escola');
  }
}

async function descarregarExtratoEscolaSuperAdmin(escolaId) {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/comprovativo-contrato`);
    if (!res.success) throw new Error(res.message || 'Falha ao obter comprovativo');

    const c = res.data;
    const agora = new Date();
    const dataEmissao = agora.toLocaleDateString('pt-PT') + ' ' + agora.toLocaleTimeString('pt-PT');

    abrirModal('Extrato Oficial de Contrato de Prestação de Serviços SIGE', `
      <div id="printExtratoContrato" class="p-4 bg-white" style="font-family: 'Times New Roman', serif;">
        <div class="text-center border-bottom pb-3 mb-4">
          <img src="/img/emblema-mocambique.png" style="width: 50px; height: 50px; margin-bottom: 4px;" alt="Emblema Nacional">
          <h5 class="fw-bold mb-0 text-uppercase">REPÚBLICA DE MOÇAMBIQUE</h5>
          <h6 class="fw-bold text-primary mb-1">SIGE — SISTEMA INTEGRADO DE GESTÃO ESCOLAR</h6>
          <small class="text-muted">EXTRATO OFICIAL DE LICENCIAMENTO E TERMO DE CONTRATO SAAS</small>
        </div>

        <div class="row g-3 mb-4 small">
          <div class="col-6">
            <strong>Instituição de Ensino:</strong> ${c.escola.nome}<br>
            <strong>NUIT / NIF:</strong> ${c.escola.nif_cnpj}<br>
            <strong>Localização:</strong> ${c.escola.distrito || '-'}, ${c.escola.provincia || '-'}<br>
            <strong>Contacto:</strong> ${c.escola.telefone || '-'} | ${c.escola.email}
          </div>
          <div class="col-6 text-end">
            <strong>Referência Contratual:</strong> ${c.comprovativo_numero}<br>
            <strong>Plano Subscrito:</strong> <span class="badge bg-primary">${c.plano.nome}</span><br>
            <strong>Estado da Licença:</strong> <span class="badge bg-success">${c.status_atual}</span><br>
            <strong>Valor Contratual:</strong> ${formatarMoeda(c.assinatura.valor)}
          </div>
        </div>

        <div class="table-responsive">
          <table class="table table-bordered table-sm small mb-4">
            <tr class="table-light"><th colspan="2" class="text-center fw-bold">VIGÊNCIA E CLÁUSULAS CONTRATUAIS</th></tr>
            <tr><th class="w-40">Data de Início:</th><td>${new Date(c.assinatura.data_inicio).toLocaleDateString('pt-PT')}</td></tr>
            <tr><th>Data de Vencimento:</th><td>${new Date(c.assinatura.data_fim).toLocaleDateString('pt-PT')}</td></tr>
            <tr><th>Capacidade Licenciada:</th><td>Até ${c.plano.max_alunos} alunos matriculados e ${c.plano.max_professores} docentes</td></tr>
            <tr><th>Alunos Ativos Registados:</th><td>${c.estatisticas.total_alunos} alunos</td></tr>
            <tr><th>Corpo Docente Ativo:</th><td>${c.estatisticas.total_professores} professores</td></tr>
            <tr><th>Turmas Cadastradas:</th><td>${c.estatisticas.total_turmas} turmas ativas</td></tr>
          </table>
        </div>

        <div class="alert alert-light border small text-muted text-center py-2 mb-4">
          Extrato emitido aos <strong>${dataEmissao}</strong> | Assinado digitalmente pelo Engenheiro de Sistemas SuperAdmin
        </div>

        <div class="row text-center pt-4 border-top small">
          <div class="col-6">
            <p class="mb-0 border-top pt-2 mx-4 fw-bold">O Engenheiro do Sistema (SuperAdmin)</p>
            <small class="text-muted">mandamulefj.@sige.com</small>
          </div>
          <div class="col-6">
            <p class="mb-0 border-top pt-2 mx-4 fw-bold">A Direcção da Escola</p>
            <small class="text-muted">${c.escola.nome}</small>
          </div>
        </div>
      </div>
      <div class="text-end mt-3 no-print">
        <button class="btn btn-primary btn-sm" onclick="imprimirDocumentoComTitulo('Extrato_Contrato_${c.escola.nome.replace(/\s+/g, '_')}')">
          <i class="bi bi-printer me-1"></i> Imprimir / Descarregar em PDF
        </button>
      </div>
    `);
  } catch (err) {
    alert(err.message || 'Erro ao emitir extrato');
  }
}

// ==================== ESTATÍSTICA DO APROVEITAMENTO PEDAGÓGICO ESCOLAR ====================
async function carregarEstatisticasAproveitamento(forcarBusca = false) {
  const container = document.getElementById('containerEstatisticasDocumento');
  if (!container) return;
  if (!forcarBusca) {
    container.innerHTML = '<div class="text-center py-5 text-muted"><i class="bi bi-calendar2-check display-4 d-block mb-3 opacity-50"></i><p class="fw-semibold">Selecione o <strong>Ano Lectivo</strong> e clique em <strong>Buscar</strong> para visualizar as estatísticas.</p></div>';
    return;
  }

  const ano = document.getElementById('statAnoFiltro')?.value || '2026';
  const periodo = document.getElementById('statPeriodoFiltro')?.value || 'GLOBAL';

  container.innerHTML = `
    <div class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="small text-muted mt-2">A compilar estatísticas gerais do aproveitamento pedagógico (${ano})...</p>
    </div>
  `;

  try {
    const res = await apiFetch(`/api/v1/pautas/estatisticas-gerais?anoLetivo=${ano}&periodo=${periodo}`);
    if (!res.success || !res.data) {
      container.innerHTML = `<div class="alert alert-warning text-center">Nenhum registo de notas ou turmas disponível para o ano lectivo ${ano}.</div>`;
      return;
    }

    const d = res.data || {};
    const ge = d.geralEscola || {
      inscritos: { total: 0, h: 0, m: 0 },
      avaliados: { total: 0, h: 0, m: 0 },
      aprovados: { total: 0, h: 0, m: 0, pct: 0 },
      reprovados: { total: 0, h: 0, m: 0, pct: 0 }
    };
    const porTurma = Array.isArray(d.porTurma) ? d.porTurma : [];
    const porClasse = Array.isArray(d.porClasse) ? d.porClasse : [];
    const porDisciplina = Array.isArray(d.porDisciplina) ? d.porDisciplina : [];
    const escolaNome = (d.escola && d.escola.nome) ? d.escola.nome : 'Escola';

    // Atualizar cartões KPI superiores
    if (document.getElementById('statKpiAprovacao')) {
      document.getElementById('statKpiAprovacao').textContent = `${ge.aprovados?.pct ?? 0}%`;
      document.getElementById('statKpiAprovacaoSub').textContent = `${ge.aprovados?.total ?? 0} Aprovados (${ge.aprovados?.h ?? 0} H / ${ge.aprovados?.m ?? 0} M)`;
      document.getElementById('statKpiReprovacao').textContent = `${ge.reprovados?.pct ?? 0}%`;
      document.getElementById('statKpiReprovacaoSub').textContent = `${ge.reprovados?.total ?? 0} Não transitam (${ge.reprovados?.h ?? 0} H / ${ge.reprovados?.m ?? 0} M)`;
      document.getElementById('statKpiAvaliados').textContent = `${ge.avaliados?.total ?? 0}`;
      document.getElementById('statKpiAvaliadosSub').textContent = `${ge.avaliados?.h ?? 0} H / ${ge.avaliados?.m ?? 0} M (Inscritos: ${ge.inscritos?.total ?? 0})`;
      document.getElementById('statKpiTurmas').textContent = `${porTurma.length}`;
      document.getElementById('statKpiTurmasSub').textContent = `${porClasse.length} Níveis de Ensino Secundário`;
    }

    // Renderizar Tabelas Estatísticas
    container.innerHTML = `
      <!-- Cabeçalho Institucional Oficial para Relatório e Impressão -->
      <div class="text-center pb-3 mb-4 border-bottom position-relative">
        <img src="/img/emblema-mocambique.png" style="width: 52px; height: 52px; object-fit: contain; margin-bottom: 3px;" alt="Emblema Nacional">
        <h6 class="fw-bold mb-0 text-uppercase">REPÚBLICA DE MOÇAMBIQUE</h6>
        <div class="text-muted small fw-semibold">MINISTÉRIO DA EDUCAÇÃO E CULTURA</div>
        <h5 class="fw-bold text-primary mt-2 mb-0">${escolaNome.toUpperCase()}</h5>
        <div class="badge bg-primary bg-opacity-10 text-primary border border-primary px-3 py-2 mt-2 fs-6">
          MAPA CONSOLIDADO DO RENDIMENTO E APROVEITAMENTO PEDAGÓGICO — ${ano} (${periodo === 'GLOBAL' ? 'MÉDIA ANUAL / MFD' : periodo})
        </div>
      </div>

      <!-- SECÇÃO 1: RESUMO GERAL DA ESCOLA -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-building me-1 text-primary"></i> 1. Resumo Global da Escola</h6>
          <span class="badge bg-secondary">${porTurma.length} Turmas Activas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-sm text-center align-middle small mb-0">
            <thead class="table-dark">
              <tr>
                <th colspan="3">Inscritos / Matriculados</th>
                <th colspan="3">Efectivo Avaliado</th>
                <th colspan="4">Aproveitamento Positivo (Aprovados)</th>
                <th colspan="4">Não Aproveitamento (Reprovados)</th>
              </tr>
              <tr class="table-light text-dark">
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th><th>% Tx Aprov.</th>
                <th>HM</th><th>M</th><th>Total</th><th>% Tx Reprov.</th>
              </tr>
            </thead>
            <tbody>
              <tr class="fw-bold fs-6">
                <td>${ge.inscritos.h}</td><td>${ge.inscritos.m}</td><td class="bg-light">${ge.inscritos.total}</td>
                <td>${ge.avaliados.h}</td><td>${ge.avaliados.m}</td><td class="bg-light">${ge.avaliados.total}</td>
                <td class="text-success">${ge.aprovados.h}</td><td class="text-success">${ge.aprovados.m}</td>
                <td class="text-success bg-light">${ge.aprovados.total}</td>
                <td class="text-success bg-success bg-opacity-10">${ge.aprovados.pct}%</td>
                <td class="text-danger">${ge.reprovados.h}</td><td class="text-danger">${ge.reprovados.m}</td>
                <td class="text-danger bg-light">${ge.reprovados.total}</td>
                <td class="text-danger bg-danger bg-opacity-10">${ge.reprovados.pct}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- SECÇÃO 2: RESUMO GERAL POR CLASSE (7ª A 12ª CLASSE) -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-layers-fill me-1 text-primary"></i> 2. Rendimento por Classe (7ª, 8ª, 9ª, 10ª, 11ª, 12ª)</h6>
          <span class="badge bg-primary">${porClasse.length} Classes Registadas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-hover table-sm text-center align-middle small mb-0">
            <thead class="table-primary">
              <tr>
                <th rowspan="2" class="align-middle text-start">Nível / Classe</th>
                <th rowspan="2" class="align-middle">Turmas</th>
                <th colspan="3">Inscritos</th>
                <th colspan="3">Avaliados</th>
                <th colspan="3">Aprovados</th>
                <th rowspan="2" class="align-middle bg-success text-white">% Aproveitamento</th>
                <th colspan="3">Reprovados</th>
                <th rowspan="2" class="align-middle bg-danger text-white">% Reprovação</th>
              </tr>
              <tr class="table-light text-dark">
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
                <th>HM</th><th>M</th><th>Total</th>
              </tr>
            </thead>
            <tbody>
              ${porClasse.map(c => `
                <tr>
                  <td class="text-start fw-bold">${c.classe} Classe</td>
                  <td><span class="badge bg-light text-dark border">${c.turmas}</span></td>
                  <td>${c.inscritos.h}</td><td>${c.inscritos.m}</td><td class="fw-bold bg-light">${c.inscritos.total}</td>
                  <td>${c.avaliados.h}</td><td>${c.avaliados.m}</td><td class="fw-bold bg-light">${c.avaliados.total}</td>
                  <td class="text-success">${c.aprovados.h}</td><td class="text-success">${c.aprovados.m}</td>
                  <td class="text-success fw-bold bg-light">${c.aprovados.total}</td>
                  <td class="fw-bold ${c.aprovados.pct >= 50 ? 'text-success' : 'text-danger'}">${c.aprovados.pct}%</td>
                  <td class="text-danger">${c.reprovados.h}</td><td class="text-danger">${c.reprovados.m}</td>
                  <td class="text-danger fw-bold bg-light">${c.reprovados.total}</td>
                  <td class="fw-bold text-danger">${c.reprovados.pct}%</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- SECÇÃO 3: APROVEITAMENTO POR TURMA -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-people-fill me-1 text-primary"></i> 3. Aproveitamento Pedagógico por Turma</h6>
          <span class="badge bg-info text-dark">${porTurma.length} Turmas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-hover table-sm text-center align-middle small mb-0">
            <thead class="table-secondary">
              <tr>
                <th class="text-start">Turma</th>
                <th>Classe</th>
                <th>Turno</th>
                <th class="text-start">Director de Turma</th>
                <th>Inscritos Total</th>
                <th>Avaliados Total</th>
                <th class="text-success">Aprovados</th>
                <th class="bg-success text-white">% Aproveitamento</th>
                <th class="text-danger">Reprovados</th>
                <th class="bg-danger text-white">% Reprovação</th>
              </tr>
            </thead>
            <tbody>
              ${porTurma.map(t => `
                <tr>
                  <td class="text-start fw-bold">${t.turmaNome}</td>
                  <td>${t.grau_ano}</td>
                  <td>${t.turno}</td>
                  <td class="text-start">${t.directorTurma}</td>
                  <td>${t.inscritos.total}</td>
                  <td class="fw-bold">${t.avaliados.total}</td>
                  <td class="text-success fw-bold">${t.aprovados.total}</td>
                  <td class="fw-bold ${t.aprovados.pct >= 50 ? 'text-success bg-success bg-opacity-10' : 'text-danger bg-danger bg-opacity-10'}">${t.aprovados.pct}%</td>
                  <td class="text-danger">${t.reprovados.total}</td>
                  <td class="text-danger">${t.reprovados.pct}%</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- SECÇÃO 4: APROVEITAMENTO POR DISCIPLINA -->
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h6 class="fw-bold text-dark mb-0"><i class="bi bi-book-half me-1 text-primary"></i> 4. Rendimento Comparativo por Disciplina</h6>
          <span class="badge bg-secondary">${porDisciplina.length} Disciplinas</span>
        </div>
        <div class="table-responsive">
          <table class="table table-bordered table-hover table-sm text-center align-middle small mb-0">
            <thead class="table-light">
              <tr>
                <th class="text-start">Disciplina</th>
                <th>Código</th>
                <th>Avaliados (HM)</th>
                <th>Avaliados (M)</th>
                <th>Avaliados Total</th>
                <th class="text-success">Aprovados Total</th>
                <th class="bg-success text-white">% Aproveitamento</th>
                <th class="text-danger">Reprovados Total</th>
                <th class="bg-danger text-white">% Reprovação</th>
                <th class="bg-primary text-white">Média da Disciplina</th>
              </tr>
            </thead>
            <tbody>
              ${porDisciplina.map(disc => `
                <tr>
                  <td class="text-start fw-bold">${disc.nome}</td>
                  <td><code>${disc.codigo}</code></td>
                  <td>${disc.avaliados.h}</td>
                  <td>${disc.avaliados.m}</td>
                  <td class="fw-bold">${disc.avaliados.total}</td>
                  <td class="text-success fw-bold">${disc.aprovados.total}</td>
                  <td class="fw-bold ${disc.aprovados.pct >= 50 ? 'text-success bg-success bg-opacity-10' : 'text-danger bg-danger bg-opacity-10'}">${disc.aprovados.pct}%</td>
                  <td class="text-danger">${disc.reprovados.total}</td>
                  <td class="text-danger">${disc.reprovados.pct}%</td>
                  <td class="fw-bold ${disc.mediaFinal !== null && disc.mediaFinal >= 9.5 ? 'text-primary' : 'text-danger'}">
                    ${disc.mediaFinal !== null ? disc.mediaFinal : '-'}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Rodapé Formal de Validação -->
      <div class="row pt-4 mt-4 border-top text-center small no-print">
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-4">O Director Pedagógico (DAP)</p>
        </div>
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-4">O Chefe da Secretaria</p>
        </div>
        <div class="col-4">
          <p class="mb-0 border-top pt-2 mx-4">O Director da Escola</p>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="alert alert-danger text-center">Erro ao carregar estatísticas do aproveitamento: ${err.message || ''}</div>`;
  }
}

async function descarregarEstatisticasPdf() {
  const container = document.getElementById('containerEstatisticasDocumento');
  if (!container) return alert('Carregue as estatísticas primeiro');
  const ano = document.getElementById('statAnoFiltro')?.value || '2026';
  const table = container.querySelector('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Estatísticas de Aproveitamento Pedagógico',
      subtitulo: `Ano Lectivo ${ano}`,
      orientacao: 'landscape',
      nomeFicheiro: `Estatisticas_Aproveitamento_${ano}.pdf`
    });
    return;
  }
  await exportarElementoParaPdf(container, `Estatisticas_Aproveitamento_Pedagogico_${ano}.pdf`, 'landscape');
}

async function exportarEstatisticasExcel() {
  const container = document.getElementById('containerEstatisticasDocumento');
  const ano = document.getElementById('statAnoFiltro')?.value || '2026';
  const periodo = document.getElementById('statPeriodoFiltro')?.value || 'GLOBAL';
  const table = container?.querySelector('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Estatísticas de Aproveitamento Pedagógico',
      subtitulo: `Ano Lectivo ${ano} | Período: ${periodo}`,
      nomeFicheiro: `Estatisticas_Aproveitamento_${ano}.xlsx`
    });
    return;
  }
  await downloadFicheiroBinario(`/api/v1/pautas/estatisticas-gerais/xlsx?anoLetivo=${ano}&periodo=${periodo}`, `Estatisticas_Aproveitamento_${ano}.xlsx`);
}

async function exportarEstatisticasWord() {
  const container = document.getElementById('containerEstatisticasDocumento');
  const ano = document.getElementById('statAnoFiltro')?.value || '2026';
  const periodo = document.getElementById('statPeriodoFiltro')?.value || 'GLOBAL';
  const table = container?.querySelector('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Estatísticas de Aproveitamento Pedagógico',
      subtitulo: `Ano Lectivo ${ano} | Período: ${periodo}`,
      orientacao: 'landscape',
      nomeFicheiro: `Estatisticas_Aproveitamento_${ano}.docx`
    });
    return;
  }
  await downloadFicheiroBinario(`/api/v1/pautas/estatisticas-gerais/docx?anoLetivo=${ano}&periodo=${periodo}`, `Estatisticas_Aproveitamento_${ano}.docx`);
}

// =========================================================================
// EXPORTAÇÕES SUPER AVANÇADAS EM CADA PAINEL (jsPDF, Excel.js, docx.js)
// =========================================================================

// 1. Alunos (painel-escola)
async function exportarAlunosPdf() {
  const table = document.getElementById('tabelaAlunos')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Relação Nominal de Alunos & Matrículas Oficiais',
      subtitulo: 'Ano Lectivo 2026',
      orientacao: 'landscape',
      nomeFicheiro: 'Alunos_Matriculados_2026.pdf'
    });
  } else {
    mostrarToast('Nenhum dado de alunos disponível para exportar.', 'warning');
  }
}

async function exportarAlunosExcel() {
  const table = document.getElementById('tabelaAlunos')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Relação Nominal de Alunos & Matrículas Oficiais',
      subtitulo: 'Ano Lectivo 2026',
      nomeFicheiro: 'Alunos_Matriculados_2026.xlsx'
    });
  } else {
    mostrarToast('Nenhum dado de alunos disponível para exportar.', 'warning');
  }
}

async function exportarAlunosWord() {
  const table = document.getElementById('tabelaAlunos')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Relação Nominal de Alunos & Matrículas Oficiais',
      subtitulo: 'Ano Lectivo 2026',
      orientacao: 'landscape',
      nomeFicheiro: 'Alunos_Matriculados_2026.docx'
    });
  } else {
    mostrarToast('Nenhum dado de alunos disponível para exportar.', 'warning');
  }
}

// 2. Professores (painel-escola)
async function exportarProfessoresPdf() {
  const table = document.getElementById('tabelaProfessores')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Quadro Geral do Corpo Docente & Alocações',
      subtitulo: 'Ano Lectivo 2026',
      orientacao: 'landscape',
      nomeFicheiro: 'Corpo_Docente_2026.pdf'
    });
  }
}

async function exportarProfessoresExcel() {
  const table = document.getElementById('tabelaProfessores')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Quadro Geral do Corpo Docente & Alocações',
      subtitulo: 'Ano Lectivo 2026',
      nomeFicheiro: 'Corpo_Docente_2026.xlsx'
    });
  }
}

async function exportarProfessoresWord() {
  const table = document.getElementById('tabelaProfessores')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Quadro Geral do Corpo Docente & Alocações',
      subtitulo: 'Ano Lectivo 2026',
      orientacao: 'landscape',
      nomeFicheiro: 'Corpo_Docente_2026.docx'
    });
  }
}

// 3. Turmas (painel-escola)
async function exportarTurmasPdf() {
  const table = document.getElementById('tabelaTurmasView')?.closest('table') || document.getElementById('tabelaTurmas')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Mapa Geral de Turmas & Ocupação Escolar',
      subtitulo: 'Ano Lectivo 2026',
      orientacao: 'landscape',
      nomeFicheiro: 'Mapa_Turmas_2026.pdf'
    });
  }
}

async function exportarTurmasExcel() {
  const table = document.getElementById('tabelaTurmasView')?.closest('table') || document.getElementById('tabelaTurmas')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Mapa Geral de Turmas & Ocupação Escolar',
      subtitulo: 'Ano Lectivo 2026',
      nomeFicheiro: 'Mapa_Turmas_2026.xlsx'
    });
  }
}

async function exportarTurmasWord() {
  const table = document.getElementById('tabelaTurmasView')?.closest('table') || document.getElementById('tabelaTurmas')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Mapa Geral de Turmas & Ocupação Escolar',
      subtitulo: 'Ano Lectivo 2026',
      orientacao: 'landscape',
      nomeFicheiro: 'Mapa_Turmas_2026.docx'
    });
  }
}

// 4. Pagamentos & Mensalidades (painel-escola e painel-financeiro)
async function exportarPagamentosPdf() {
  const table = document.getElementById('tabelaPagamentos')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Relatório Financeiro de Cobranças & Propinas',
      subtitulo: 'Ano Lectivo 2026',
      orientacao: 'landscape',
      nomeFicheiro: 'Relatorio_Pagamentos_2026.pdf'
    });
  }
}

async function exportarPagamentosExcel() {
  const table = document.getElementById('tabelaPagamentos')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Relatório Financeiro de Cobranças & Propinas',
      subtitulo: 'Ano Lectivo 2026',
      nomeFicheiro: 'Relatorio_Pagamentos_2026.xlsx'
    });
  }
}

async function exportarPagamentosWord() {
  const table = document.getElementById('tabelaPagamentos')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Relatório Financeiro de Cobranças & Propinas',
      subtitulo: 'Ano Lectivo 2026',
      orientacao: 'landscape',
      nomeFicheiro: 'Relatorio_Pagamentos_2026.docx'
    });
  }
}

// 5. Aluno: Boletim de Notas (painel-aluno)
async function exportarBoletimAlunoPdf() {
  const table = document.getElementById('tabelaAlunoNotasCorpo')?.closest('table');
  if (window.SigeExport && table) {
    const nomeAluno = state.user?.nome || 'Aluno';
    const mapNomes = { '1_TRIMESTRE': 'I Trimestre', '2_TRIMESTRE': 'II Trimestre', '3_TRIMESTRE': 'III Trimestre', 'TODOS': 'Todos os Trimestres (I, II e III)' };
    const perTexto = mapNomes[stateAlunoNotas?.periodoAtivo] || 'Todos os Trimestres';
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Boletim Oficial de Notas & Avaliações',
      subtitulo: `Aluno(a): ${nomeAluno} | Período: ${perTexto} | Ano Lectivo 2026`,
      orientacao: 'portrait',
      nomeFicheiro: `Boletim_Notas_${nomeAluno.replace(/\\s+/g, '_')}_${stateAlunoNotas?.periodoAtivo || 'TODOS'}_2026.pdf`,
      metadadosExtras: {
        'Aluno': nomeAluno,
        'Período': perTexto,
        'Ano Letivo': '2026'
      }
    });
  }
}

async function exportarBoletimAlunoExcel() {
  const table = document.getElementById('tabelaAlunoNotasCorpo')?.closest('table');
  if (window.SigeExport && table) {
    const nomeAluno = state.user?.nome || 'Aluno';
    const mapNomes = { '1_TRIMESTRE': 'I Trimestre', '2_TRIMESTRE': 'II Trimestre', '3_TRIMESTRE': 'III Trimestre', 'TODOS': 'Todos os Trimestres (I, II e III)' };
    const perTexto = mapNomes[stateAlunoNotas?.periodoAtivo] || 'Todos os Trimestres';
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Boletim Oficial de Notas & Avaliações',
      subtitulo: `Aluno(a): ${nomeAluno} | Período: ${perTexto} | Ano Lectivo 2026`,
      nomeFicheiro: `Boletim_Notas_${nomeAluno.replace(/\\s+/g, '_')}_${stateAlunoNotas?.periodoAtivo || 'TODOS'}_2026.xlsx`
    });
  }
}

async function exportarBoletimAlunoWord() {
  const table = document.getElementById('tabelaAlunoNotasCorpo')?.closest('table');
  if (window.SigeExport && table) {
    const nomeAluno = state.user?.nome || 'Aluno';
    const mapNomes = { '1_TRIMESTRE': 'I Trimestre', '2_TRIMESTRE': 'II Trimestre', '3_TRIMESTRE': 'III Trimestre', 'TODOS': 'Todos os Trimestres (I, II e III)' };
    const perTexto = mapNomes[stateAlunoNotas?.periodoAtivo] || 'Todos os Trimestres';
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Boletim Oficial de Notas & Avaliações',
      subtitulo: `Aluno(a): ${nomeAluno} | Período: ${perTexto} | Ano Lectivo 2026`,
      orientacao: 'portrait',
      nomeFicheiro: `Boletim_Notas_${nomeAluno.replace(/\\s+/g, '_')}_${stateAlunoNotas?.periodoAtivo || 'TODOS'}_2026.docx`
    });
  }
}

// 6. Aluno: Extrato de Mensalidades (painel-aluno)
async function exportarExtratoAlunoPdf() {
  const table = document.getElementById('tabelaAlunoPagamentosCorpo')?.closest('table');
  if (window.SigeExport && table) {
    const nomeAluno = state.user?.nome || 'Aluno';
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Extrato Oficial de Propinas & Mensalidades',
      subtitulo: `Aluno(a): ${nomeAluno} | Ano Lectivo 2026`,
      orientacao: 'portrait',
      nomeFicheiro: `Extrato_Propinas_${nomeAluno.replace(/\\s+/g, '_')}_2026.pdf`
    });
  }
}

async function exportarExtratoAlunoExcel() {
  const table = document.getElementById('tabelaAlunoPagamentosCorpo')?.closest('table');
  if (window.SigeExport && table) {
    const nomeAluno = state.user?.nome || 'Aluno';
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Extrato Oficial de Propinas & Mensalidades',
      subtitulo: `Aluno(a): ${nomeAluno} | Ano Lectivo 2026`,
      nomeFicheiro: `Extrato_Propinas_${nomeAluno.replace(/\\s+/g, '_')}_2026.xlsx`
    });
  }
}

async function exportarExtratoAlunoWord() {
  const table = document.getElementById('tabelaAlunoPagamentosCorpo')?.closest('table');
  if (window.SigeExport && table) {
    const nomeAluno = state.user?.nome || 'Aluno';
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Extrato Oficial de Propinas & Mensalidades',
      subtitulo: `Aluno(a): ${nomeAluno} | Ano Lectivo 2026`,
      orientacao: 'portrait',
      nomeFicheiro: `Extrato_Propinas_${nomeAluno.replace(/\\s+/g, '_')}_2026.docx`
    });
  }
}

// 7. SuperAdmin: Escolas SaaS (painel-superadmin)
async function exportarRelatorioSaasPdf() {
  const table = document.getElementById('tabelaSaasEscolas')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Relatório SaaS — Rede de Instituições & Tenants',
      subtitulo: 'SIGE Cloud Multi-tenant',
      orientacao: 'landscape',
      nomeFicheiro: 'Relatorio_Escolas_SaaS_2026.pdf'
    });
  }
}

async function exportarRelatorioSaasExcel() {
  const table = document.getElementById('tabelaSaasEscolas')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Relatório SaaS — Rede de Instituições & Tenants',
      subtitulo: 'SIGE Cloud Multi-tenant',
      nomeFicheiro: 'Relatorio_Escolas_SaaS_2026.xlsx'
    });
  }
}

async function exportarRelatorioSaasWord() {
  const table = document.getElementById('tabelaSaasEscolas')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Relatório SaaS — Rede de Instituições & Tenants',
      subtitulo: 'SIGE Cloud Multi-tenant',
      orientacao: 'landscape',
      nomeFicheiro: 'Relatorio_Escolas_SaaS_2026.docx'
    });
  }
}

// 8. SuperAdmin & Escola: Cofre de Utilizadores e Senhas
async function exportarUsuariosPdf() {
  const table = document.getElementById('tabelaCofreUsuariosCorpo')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Registo Confidencial de Contas & Códigos de Acesso',
      subtitulo: 'Acesso Restrito — Direcção & SuperAdmin',
      orientacao: 'landscape',
      nomeFicheiro: 'Contas_Utilizadores_2026.pdf'
    });
  }
}

async function exportarUsuariosExcel() {
  const table = document.getElementById('tabelaCofreUsuariosCorpo')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Registo Confidencial de Contas & Códigos de Acesso',
      subtitulo: 'Acesso Restrito — Direcção & SuperAdmin',
      nomeFicheiro: 'Contas_Utilizadores_2026.xlsx'
    });
  }
}

async function exportarUsuariosWord() {
  const table = document.getElementById('tabelaCofreUsuariosCorpo')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Registo Confidencial de Contas & Códigos de Acesso',
      subtitulo: 'Acesso Restrito — Direcção & SuperAdmin',
      orientacao: 'landscape',
      nomeFicheiro: 'Contas_Utilizadores_2026.docx'
    });
  }
}

// 9. SuperAdmin & Escola: Logs de Acesso e Auditoria
async function exportarAcessosPdf() {
  const table = document.getElementById('tabelaLogsAcesso')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'pdf', {
      titulo: 'Relatório de Auditoria de Acessos & Segurança',
      subtitulo: 'Trilha de Auditoria do Sistema',
      orientacao: 'landscape',
      nomeFicheiro: 'Auditoria_Acessos_2026.pdf'
    });
  }
}

async function exportarAcessosExcel() {
  const table = document.getElementById('tabelaLogsAcesso')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'excel', {
      titulo: 'Relatório de Auditoria de Acessos & Segurança',
      subtitulo: 'Trilha de Auditoria do Sistema',
      nomeFicheiro: 'Auditoria_Acessos_2026.xlsx'
    });
  }
}

async function exportarAcessosWord() {
  const table = document.getElementById('tabelaLogsAcesso')?.closest('table');
  if (window.SigeExport && table) {
    await window.SigeExport.exportarTabelaHtml(table, 'word', {
      titulo: 'Relatório de Auditoria de Acessos & Segurança',
      subtitulo: 'Trilha de Auditoria do Sistema',
      orientacao: 'landscape',
      nomeFicheiro: 'Auditoria_Acessos_2026.docx'
    });
  }
}

// ==================== LOGÓTIPO SAAS CADASTRO ====================
function processarLogoCadastroLocal(input) {
  const file = input.files?.[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    alert('Por favor, seleccione um ficheiro de imagem válido.');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    const hidden = document.getElementById('cadEscolaLogoBase64');
    if (hidden) hidden.value = e.target.result;
  };
  reader.readAsDataURL(file);
}

function processarUploadLogoModal(input, hiddenInputId, previewImgId) {
  const file = input.files?.[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    alert('Por favor, seleccione um ficheiro de imagem válido (PNG, JPG, WebP).');
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    alert('A imagem seleccionada é muito pesada (máximo 5MB).');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    const dataUrl = e.target.result;
    const hidden = document.getElementById(hiddenInputId);
    if (hidden) hidden.value = dataUrl;
    const preview = document.getElementById(previewImgId);
    if (preview) preview.src = dataUrl;
  };
  reader.readAsDataURL(file);
}

// ==================== MATERIAL ESCOLAR POR CLASSE ====================
state.materialEscolar = {
  classeAtiva: 'TODAS',
  materiais: [],
  classes: []
};

const CLASSES_SISTEMA_ORDEM = [
  '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
  '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe',
  'Nível 1', 'Nível 2', 'Nível 3', 'Nível 4', 'Nível 5', 'Nível 6'
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
    if (resD && resD.success && Array.isArray(resD.data)) {
      optDisciplinas += resD.data.map(d => `<option value="${escapeHtml(d.id)}">${escapeHtml(d.nome)} (${escapeHtml(d.classe || '')})</option>`).join('');
    }
  } catch (errDisc) {
    console.warn('[MATERIAL] Falha ao carregar disciplinas no modal:', errDisc);
  }

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
          <textarea id="matUploadDescricao" class="form-control" rows="2" placeholder="Ex: Manual oficial adoptado pelo MEC. Exercícios dos capítulos 1 a 4."></textarea>
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
                <i class="bi bi-link-45deg me-1"></i> Importar via Link Web (Google Drive, MEC...)
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
            <input type="url" id="matUploadUrl" class="form-control form-control-sm" placeholder="https://drive.google.com/... ou https://mec.gov.mz/...">
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

// Compatibilidade retroativa:
const PLANO_CURRICULAR_MINEDH_FRONTEND = PLANO_CURRICULAR_MEC_FRONTEND;

// =====================================================================
// SIGE - Módulo Exames | Pautas Oficiais de Exame (MEC / Moçambique)
// Modelagem e Cálculo Estrito: Dados reais das pautas de frequência,
// lançamento de notas de 1ª e 2ª época, janela de parâmetros (pesos e nota mínima),
// e integração com Certificados e Declarações.
// =====================================================================

window._sigePautaExamesData = null;
window._sigeNotasExameModificadas = new Map();

async function carregarExames() {
  const container = document.getElementById('view-exames');
  if (!container) return;

  // Actualizar imediatamente o cabeçalho oficial com a instituição ativa
  try {
    const escInit = window.state?.tenant || {};
    const escNomeInit = (escInit.nome || 'Escola Secundária de Massinga').toUpperCase();
    const provNomeInit = (escInit.provincia || 'Inhambane').toUpperCase();
    const distNomeInit = (escInit.distrito || 'Massinga').toUpperCase();

    const elEscInit = document.getElementById('pautaExameEscolaNome');
    if (elEscInit) elEscInit.textContent = escNomeInit;
    const elProvInit = document.getElementById('pautaExameProvincia');
    if (elProvInit) elProvInit.textContent = provNomeInit;
    const elDistInit = document.getElementById('pautaExameDistrito');
    if (elDistInit) elDistInit.textContent = distNomeInit;
    const elLogoInit = document.getElementById('pautaExameLogoImg');
    if (elLogoInit && escInit.logo) elLogoInit.src = escInit.logo;
  } catch (_) {}

  // Carregar e sincronizar parâmetros de exame ativos
  try {
    const resParam = await apiFetch('/api/v1/pautas/exames/parametros');
    if (resParam && resParam.success && resParam.parametros) {
      atualizarCamposParametrosExameNaInterface(resParam.parametros);
    }
  } catch (_) {}

  try {
    // 1. Obter classes com regime de exame configurado
    let classesComExame = new Set(['10ª Classe', '12ª Classe']);
    try {
      const resCfg = await apiFetch('/api/v1/escola-admin/classes-exames');
      if (resCfg && resCfg.success && Array.isArray(resCfg.data)) {
        resCfg.data.forEach(item => {
          if (item.tem_exame) {
            classesComExame.add(item.nome);
          }
        });
      }
    } catch (_) {}

    // 2. Obter todas as turmas da instituição
    const resTurmas = await apiFetch('/api/v1/escola-admin/turmas');
    const selectClasse = document.getElementById('exameClasseFilter');
    const selectTurma = document.getElementById('exameTurmaSelect');
    if (!selectClasse || !selectTurma) return;

    if (resTurmas && resTurmas.success && Array.isArray(resTurmas.data)) {
      // Filtrar apenas turmas de classes com regime de exame
      const turmasComExame = resTurmas.data.filter(t => {
        const grau = (t.grau_ano || '').trim();
        const eh10ou12 = /(^|[^\d])(10|12)([ªaº\.\s]|$)/i.test(grau);
        const estaConfigurada = classesComExame.has(grau) || Array.from(classesComExame).some(c => grau.toLowerCase().includes(c.toLowerCase()));
        return eh10ou12 || estaConfigurada || Boolean(t.tem_exame);
      });

      window._sigeTurmasExamesLista = turmasComExame;

      // Extrair classes únicas das turmas com exame
      const classesUnicas = Array.from(new Set(turmasComExame.map(t => t.grau_ano))).filter(Boolean);

      if (classesUnicas.length > 0) {
        selectClasse.innerHTML = classesUnicas.map(c => 
          `<option value="${c}">${c}</option>`
        ).join('');
      } else {
        selectClasse.innerHTML = '<option value="">Sem classes com exame cadastradas</option>';
      }

      filtrarTurmasExamesPorClasse();
    } else {
      selectClasse.innerHTML = '<option value="">Erro ao carregar turmas</option>';
      selectTurma.innerHTML = '<option value="">Nenhuma turma disponível</option>';
    }
  } catch (err) {
    console.error('Erro ao inicializar módulo de exames:', err);
    mostrarToast('Erro ao carregar módulo de exames.', 'danger');
  }
}

function filtrarTurmasExamesPorClasse() {
  const classeSel = document.getElementById('exameClasseFilter')?.value;
  const selectTurma = document.getElementById('exameTurmaSelect');
  if (!selectTurma) return;

  const turmas = window._sigeTurmasExamesLista || [];
  const filtradas = classeSel ? turmas.filter(t => t.grau_ano === classeSel) : turmas;

  if (filtradas.length > 0) {
    selectTurma.innerHTML = filtradas.map(t => {
      const area = t.area && !['geral', 'ensino geral', 'tronco comum'].includes(t.area.toLowerCase()) ? ` (${t.area})` : '';
      return `<option value="${t.id}">${t.grau_ano} &rarr; ${t.nome}${area}</option>`;
    }).join('');
    carregarPautaExamesTurma();
  } else {
    selectTurma.innerHTML = '<option value="">Nenhuma turma encontrada para esta classe</option>';
    document.getElementById('containerTabelaPautaExames').innerHTML = `
      <div class="alert alert-warning text-center my-4">
        <i class="bi bi-exclamation-triangle-fill me-2"></i>
        Nenhuma turma com regime de exame registada para a classe selecionada.
      </div>
    `;
    const rodape = document.getElementById('pautaExameRodapeOficial');
    if (rodape) rodape.classList.add('d-none');
  }
}

async function carregarPautaExamesTurma() {
  const turmaId = document.getElementById('exameTurmaSelect')?.value;
  const anoSelect = document.getElementById('exameAnoSelect');
  const anoLetivo = anoSelect?.value || (window.state?.tenant?.ano_letivo_ativo || '2026');
  const container = document.getElementById('containerTabelaPautaExames');
  if (!turmaId || !container) return;

  container.innerHTML = `
    <div class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="small text-muted mt-2">A carregar pauta oficial de exames e a sincronizar com pautas de frequência...</p>
    </div>
  `;

  try {
    const res = await apiFetch(`/api/v1/pautas/exames/turma/${turmaId}?anoLetivo=${anoLetivo}`);
    if (!res || !res.success) {
      container.innerHTML = `
        <div class="alert alert-danger text-center my-4">
          <i class="bi bi-x-circle-fill me-2"></i>
          ${res?.message || 'Não foi possível carregar a pauta de exames para esta turma.'}
        </div>
      `;
      return;
    }

    const d = res.data || res;
    window._sigePautaExamesData = d;
    if (!window._sigeNotasExameModificadas) {
      window._sigeNotasExameModificadas = new Map();
    }
    window._sigeNotasExameModificadas.clear();

    // Actualizar Cabeçalhos Oficiais Moçambique
    const escData = d.escola || window.state?.tenant || {};
    const escNome = (escData.nome || 'Escola Secundária de Massinga').toUpperCase();
    const provNome = (escData.provincia || 'Inhambane').toUpperCase();
    const distNome = (escData.distrito || 'Massinga').toUpperCase();

    const elEsc = document.getElementById('pautaExameEscolaNome');
    if (elEsc) elEsc.textContent = escNome;
    const elProv = document.getElementById('pautaExameProvincia');
    if (elProv) elProv.textContent = provNome;
    const elDist = document.getElementById('pautaExameDistrito');
    if (elDist) elDist.textContent = distNome;

    const elLogo = document.getElementById('pautaExameLogoImg');
    if (elLogo && escData.logo) elLogo.src = escData.logo;

    const grau = d.turma?.grau_ano || '10ª Classe';
    const area = d.turma?.area ? ` / ${d.turma.area}` : '';
    const elClasse = document.getElementById('pautaExameClasseArea');
    if (elClasse) elClasse.textContent = `Classe / Área ou Secção: ${grau}${area}`;

    const elAno = document.getElementById('pautaExameTituloAno');
    if (elAno) elAno.textContent = `PAUTA DE EXAMES / Ano ${anoLetivo}`;

    const elTurmaBadge = document.getElementById('pautaExameTurmaBadge');
    if (elTurmaBadge) elTurmaBadge.textContent = `Turma: ${d.turma?.nome || ''}`;

    const badgeTotal = document.getElementById('badgeTotalCandidatosExame');
    if (badgeTotal) badgeTotal.textContent = `${(d.alunos || []).length} Candidatos`;

    if (d.parametros) {
      atualizarCamposParametrosExameNaInterface(d.parametros);
    }

    renderizarTabelaExamesHtml(d);
  } catch (err) {
    console.error('Erro ao carregar pauta de exames:', err);
    const msg = err?.message || 'Erro de comunicação ao carregar pauta de exames.';
    const safeMsg = typeof escapeHtml === 'function' ? escapeHtml(msg) : msg;
    container.innerHTML = `
      <div class="alert alert-danger text-center my-4 py-3">
        <i class="bi bi-exclamation-triangle-fill fs-4 text-danger d-block mb-2"></i>
        <div class="fw-bold mb-1">${safeMsg}</div>
        <p class="small text-muted mb-3">Não foi possível carregar a pauta de exames desta turma.</p>
        <button type="button" class="btn btn-sm btn-outline-danger" onclick="carregarPautaExamesTurma()">
          <i class="bi bi-arrow-clockwise me-1"></i> Tentar Novamente
        </button>
      </div>
    `;
  }
}

function renderizarTabelaExamesHtml(d) {
  const container = document.getElementById('containerTabelaPautaExames');
  if (!container) return;

  const podeEditar = d.pode_editar !== false;
  const motivoBloqueio = d.motivo_bloqueio || '';

  // Gerir exibição do aviso de permissão de lançamento e estado do botão de salvar
  const elAviso = document.getElementById('avisoBloqueioLancamentoExame');
  const elTextoBloqueio = document.getElementById('textoBloqueioLancamentoExame');
  const btnSalvar = document.getElementById('btnSalvarNotasExame');
  const btnProf = document.getElementById('btnProfessoresExame');

  // Botão de autorizar professores visível apenas para Direcção / DAP
  const userRole = (window.state?.user?.role || '').toUpperCase();
  const isGestao = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'].includes(userRole) || !userRole;
  if (btnProf) {
    if (isGestao) btnProf.classList.remove('d-none');
    else btnProf.classList.add('d-none');
  }

  if (elAviso && elTextoBloqueio) {
    if (!podeEditar) {
      elAviso.classList.remove('d-none');
      elTextoBloqueio.textContent = motivoBloqueio || 'O lançamento das notas de exame nesta classe está reservado ao Director Pedagógico ou professores autorizados.';
      if (btnSalvar) {
        btnSalvar.setAttribute('disabled', 'true');
        btnSalvar.classList.add('opacity-50');
      }
    } else {
      elAviso.classList.add('d-none');
      if (btnSalvar) {
        btnSalvar.removeAttribute('disabled');
        btnSalvar.classList.remove('opacity-50');
      }
    }
  }

  const disciplinasComExame = d.disciplinas_com_exame || [];
  const disciplinasSemExame = d.disciplinas_sem_exame || [];
  const alunos = d.alunos || [];
  const params = d.parametros || { peso_frequencia: 50, peso_exame: 50, nota_minima_exame: 10 };
  const notaMinima = Number(params.nota_minima_exame || 10);

  if (alunos.length === 0) {
    container.innerHTML = `
      <div class="alert alert-info text-center my-4 py-3">
        <i class="bi bi-info-circle-fill fs-4 text-info d-block mb-2"></i>
        <div class="fw-semibold">Não existem alunos matriculados ativos nesta turma de exame.</div>
        <small class="text-muted">Selecione outra turma no filtro acima para visualizar e lançar notas de exame.</small>
      </div>
    `;
    const rodape = document.getElementById('pautaExameRodapeOficial');
    if (rodape) rodape.classList.add('d-none');
    return;
  }

  if (disciplinasComExame.length === 0 && disciplinasSemExame.length === 0) {
    container.innerHTML = `
      <div class="alert alert-warning text-center my-4 py-3">
        <i class="bi bi-exclamation-triangle-fill fs-4 text-warning d-block mb-2"></i>
        <div class="fw-semibold">Não foram encontradas disciplinas do plano curricular associadas à área desta turma.</div>
        <small class="text-muted">Classe: ${d.turma?.grau_ano || ''} | Área: ${d.turma?.area || 'Geral'}</small>
      </div>
    `;
    const rodape = document.getElementById('pautaExameRodapeOficial');
    if (rodape) rodape.classList.add('d-none');
    return;
  }

  // Montar Cabeçalhos da Tabela Fiel ao Modelo MEC (Ajuste Fino ao Conteúdo)
  let thLinha1 = `
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-nowrap px-2" style="font-size: 0.72rem;">Nº</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-nowrap px-2" style="font-size: 0.72rem;">Nº Candidato</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-start ps-2 text-nowrap px-3" style="font-size: 0.75rem;">Nome do Aluno</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-nowrap px-1" style="font-size: 0.72rem;">Gén.</th>
    <th rowspan="3" class="align-middle bg-primary text-white border-end text-nowrap px-2" style="font-size: 0.72rem;">Turma</th>
  `;

  // Disciplinas com exame: 4 colunas cada (sem min-width artificial)
  disciplinasComExame.forEach(disc => {
    thLinha1 += `<th colspan="4" class="text-center bg-primary bg-opacity-10 text-primary fw-bold border-start border-end text-nowrap px-2" style="font-size: 0.75rem;">${disc.nome}</th>`;
  });

  // Disciplinas sem exame: 1 coluna cada
  disciplinasSemExame.forEach(disc => {
    thLinha1 += `<th rowspan="2" class="text-center bg-light text-dark fw-bold border-start border-end text-nowrap px-2" style="font-size: 0.72rem;">${disc.nome}</th>`;
  });

  // RESULTADO FINAL: 3 colunas
  thLinha1 += `<th colspan="3" class="text-center bg-dark text-white fw-bold border-start text-nowrap px-2" style="font-size: 0.75rem;">RESULTADO FINAL</th>`;

  // Linha 2 do cabeçalho
  let thLinha2 = '';
  disciplinasComExame.forEach(() => {
    thLinha2 += `
      <th rowspan="2" class="bg-light text-dark fw-bold border-end align-middle text-nowrap px-1" style="font-size: 0.68rem;">Freq.</th>
      <th colspan="2" class="bg-warning bg-opacity-25 text-dark fw-bold border-end text-nowrap px-1" style="font-size: 0.68rem;">Exame</th>
      <th rowspan="2" class="bg-primary bg-opacity-10 text-primary fw-bold border-end align-middle text-nowrap px-1" style="font-size: 0.68rem;">Média</th>
    `;
  });

  thLinha2 += `
    <th rowspan="2" class="bg-secondary bg-opacity-10 text-dark fw-bold border-end text-nowrap px-2" style="font-size: 0.72rem;">Resultado</th>
    <th rowspan="2" class="bg-secondary bg-opacity-10 text-dark fw-bold border-end text-nowrap px-1" style="font-size: 0.72rem;">MF</th>
    <th rowspan="2" class="bg-secondary bg-opacity-10 text-dark fw-bold text-start ps-2 text-nowrap px-2" style="font-size: 0.72rem;">Disciplina(s) com Negativa</th>
  `;

  // Linha 3 do cabeçalho
  let thLinha3 = '';
  disciplinasComExame.forEach(() => {
    thLinha3 += `
      <th class="bg-warning bg-opacity-10 text-dark fw-bold border-end text-nowrap p-0" style="font-size: 0.65rem; width: 44px; min-width: 44px; max-width: 44px;">1ª</th>
      <th class="bg-warning bg-opacity-10 text-dark fw-bold border-end text-nowrap p-0" style="font-size: 0.65rem; width: 44px; min-width: 44px; max-width: 44px;">2ª</th>
    `;
  });

  disciplinasSemExame.forEach(() => {
    thLinha3 += `<th class="bg-light text-muted border-end text-nowrap px-1" style="font-size: 0.65rem;">Freq.</th>`;
  });

  // Linhas dos Alunos
  let trsCorpo = '';
  alunos.forEach((aluno, idx) => {
    const discMap = aluno.disciplinas || {};
    const resFinal = aluno.resultado_final || {};
    const sufixoGen = (aluno.genero || 'M').toUpperCase().startsWith('F') ? 'a' : 'o';

    let tdsDiscs = '';

    // Disciplinas com exame
    disciplinasComExame.forEach(d => {
      const dData = discMap[d.id] || {};
      const vFreq = dData.frequencia !== undefined && dData.frequencia !== null ? dData.frequencia : '-';
      const e1Val = dData.exame_1epoca !== null && dData.exame_1epoca !== undefined ? dData.exame_1epoca : '';
      const e2Val = dData.exame_2epoca !== null && dData.exame_2epoca !== undefined ? dData.exame_2epoca : '';
      const vMed = dData.media !== undefined && dData.media !== null ? dData.media : '-';

      const temE1 = e1Val !== '' && !isNaN(Number(e1Val));
      const aprovou1e = temE1 && Number(e1Val) >= notaMinima;
      const pode2e = temE1 && Number(e1Val) < notaMinima;

      let estiloE1 = 'background: transparent;';
      let estiloE2 = 'background: transparent;';
      let titleE2 = 'Nota da 2ª época (se necessária)';

      if (aprovou1e) {
        estiloE1 = 'background: #dcfce7; font-weight: bold; color: #166534;';
        estiloE2 = 'background: #f1f5f9; color: #94a3b8; cursor: not-allowed;';
        titleE2 = `Aluno já aprovado na 1ª época (${e1Val} ≥ ${notaMinima})`;
      } else if (pode2e) {
        estiloE1 = 'background: #fee2e2; color: #991b1b;';
        estiloE2 = 'background: #fef3c7; border: 1px dashed #f59e0b !important; font-weight: bold;';
        titleE2 = `Não atingiu nota mínima (${e1Val} < ${notaMinima}). Elegível para a 2ª época!`;
      }

      const corMed = (typeof vMed === 'number' || (!isNaN(Number(vMed)) && vMed !== '-')) 
        ? (Number(vMed) >= 9.5 ? 'text-success fw-bold' : 'text-danger fw-bold') 
        : (vMed === '2ª Época' ? 'text-warning fw-bold' : 'text-muted');

      tdsDiscs += `
        <td class="text-center bg-light border-end font-monospace small text-nowrap px-2">${vFreq}</td>
        <td class="p-1 text-center border-end align-middle text-nowrap" style="width: 44px; min-width: 44px; max-width: 44px;">
          <input type="number" step="0.01" min="0" max="20" class="form-control form-control-sm text-center p-0 font-monospace input-exame-nota shadow-none"
            value="${e1Val}" placeholder="-" data-aluno="${aluno.id}" data-disc="${d.id}" data-epoca="1"
            ${!podeEditar ? 'disabled readonly' : ''}
            onchange="aoMudarNotaExame(this)" oninput="aoMudarNotaExame(this)"
            style="width: 40px; height: 26px; font-size: 0.8rem; border: 1px solid #cbd5e1; ${!podeEditar ? 'background: #f8fafc; cursor: not-allowed;' : 'background: #ffffff;'}"
            title="${!podeEditar ? 'Lançamento reservado ao Director Pedagógico ou professores autorizados' : `1ª Época: Mínimo ${notaMinima} valores para aprovação`}">
        </td>
        <td class="p-1 text-center border-end align-middle text-nowrap" style="width: 44px; min-width: 44px; max-width: 44px;">
          <input type="number" step="0.01" min="0" max="20" class="form-control form-control-sm text-center p-0 font-monospace input-exame-nota shadow-none"
            value="${e2Val}" placeholder="-" data-aluno="${aluno.id}" data-disc="${d.id}" data-epoca="2"
            ${!podeEditar ? 'disabled readonly' : ''}
            onchange="aoMudarNotaExame(this)" oninput="aoMudarNotaExame(this)"
            style="width: 40px; height: 26px; font-size: 0.8rem; border: 1px solid #cbd5e1; ${!podeEditar ? 'background: #f8fafc; cursor: not-allowed;' : 'background: #ffffff;'}"
            title="${!podeEditar ? 'Lançamento reservado ao Director Pedagógico ou professores autorizados' : `2ª Época: Mínimo ${notaMinima} valores para aprovação`}">
        </td>
        <td class="text-center border-end font-monospace small text-nowrap px-2 ${corMed}" id="media_${aluno.id}_${d.id}">
          ${vMed}
        </td>
      `;
    });

    // Disciplinas sem exame
    disciplinasSemExame.forEach(d => {
      const dData = discMap[d.id] || {};
      const vFreq = dData.frequencia !== undefined && dData.frequencia !== null ? dData.frequencia : '-';
      const corFreq = (typeof vFreq === 'number' || (!isNaN(Number(vFreq)) && vFreq !== '-')) 
        ? (Number(vFreq) >= 9.5 ? 'text-success' : 'text-danger') 
        : 'text-muted';
      tdsDiscs += `
        <td class="text-center border-end font-monospace small text-nowrap px-2 ${corFreq}">${vFreq}</td>
      `;
    });

    // Resultado Final do Aluno: Aprovado a preto e Reprovado a vermelho (sem pintar fundo)
    const rawRes = String(resFinal.aprovado || resFinal.resultado || `Reprovad${sufixoGen}`).trim();
    const resAprov = rawRes.includes('Aprovad') ? `Aprovad${sufixoGen}` : `Reprovad${sufixoGen}`;
    const corResClass = resAprov.includes('Aprovad') ? 'text-dark fw-bold' : 'text-danger fw-bold';
    const corResStyle = resAprov.includes('Aprovad') ? 'color: #000000; font-weight: bold;' : 'color: #dc2626; font-weight: bold;';

    const mfVal = resFinal.mf !== undefined && resFinal.mf !== null ? resFinal.mf : 0;
    const discRep = resFinal.disciplinas_reprovou || '---';

    trsCorpo += `
      <tr id="linha_aluno_${aluno.id}">
        <td class="text-center font-monospace text-muted small border-end align-middle text-nowrap px-2">${aluno.numero || idx + 1}</td>
        <td class="text-center font-monospace small border-end fw-semibold text-secondary align-middle text-nowrap px-2">${aluno.candidato || aluno.matricula}</td>
        <td class="text-start ps-2 text-dark fw-bold border-end small text-nowrap align-middle px-3">${aluno.nome}</td>
        <td class="text-center font-monospace small border-end align-middle text-nowrap px-2">${aluno.genero}</td>
        <td class="text-center small border-end text-muted align-middle text-nowrap px-2">${aluno.turma}</td>
        ${tdsDiscs}
        <td class="text-center border-end align-middle text-nowrap px-2">
          <span id="res_aluno_${aluno.id}" class="${corResClass}" style="font-size: 0.82rem; ${corResStyle}">${resAprov}</span>
        </td>
        <td class="text-center font-monospace fw-bold border-end align-middle text-nowrap px-2" id="mf_aluno_${aluno.id}" style="font-size: 0.82rem;">
          ${mfVal}
        </td>
        <td class="text-start ps-2 small text-danger font-monospace align-middle text-nowrap px-3" id="rep_aluno_${aluno.id}" style="font-size: 0.72rem;">
          ${discRep}
        </td>
      </tr>
    `;
  });

  const htmlTabela = `
    <table class="table table-bordered table-sm align-middle text-center sige-tabela-exames mb-0 border" style="font-size: 0.78rem; width: max-content !important; margin: 0 auto !important; border-collapse: collapse;">
      <thead>
        <tr class="align-middle">${thLinha1}</tr>
        <tr class="align-middle">${thLinha2}</tr>
        <tr class="align-middle">${thLinha3}</tr>
      </thead>
      <tbody>
        ${trsCorpo}
      </tbody>
    </table>
  `;

  container.innerHTML = htmlTabela;

  // Renderizar Rodapé Oficial com Resumo e Assinaturas
  const rodape = document.getElementById('pautaExameRodapeOficial');
  const boxEstat = document.getElementById('pautaExameEstatisticasBox');
  if (rodape && boxEstat) {
    const estat = d.estatisticas || {};
    const tot = estat.total || alunos.length;
    const aprov = estat.aprovados || 0;
    const rep = estat.reprovados || 0;
    const adm = estat.admitidos || 0;
    const seg = estat.segunda_epoca || 0;
    const taxa = estat.taxa_aprovacao || 0.0;

    boxEstat.innerHTML = `
      <div><strong>Total de Candidatos:</strong> <span class="badge bg-secondary ms-1">${tot}</span> (H: ${estat.homens || 0} | M: ${estat.mulheres || 0})</div>
      <div><strong>Aprovados:</strong> <span class="badge bg-success ms-1">${aprov}</span></div>
      <div><strong>2ª Época:</strong> <span class="badge bg-warning text-dark ms-1">${seg}</span></div>
      <div><strong>Reprovados:</strong> <span class="badge bg-danger ms-1">${rep}</span></div>
      <div><strong>Admitidos ao Exame:</strong> <span class="badge bg-primary ms-1">${adm}</span></div>
      <div><strong>Taxa de Aprovação:</strong> <span class="badge bg-dark ms-1">${taxa}%</span></div>
    `;

    const elDt = document.getElementById('pautaExameAssinaturaDT');
    if (elDt) elDt.textContent = d.turma?.director_turma || 'Director de Turma';

    const elDap = document.getElementById('pautaExameAssinaturaDAP');
    if (elDap) elDap.textContent = window.state?.tenant?.dap_nome || 'Direcção Pedagógica';

    const elDir = document.getElementById('pautaExameAssinaturaDir');
    if (elDir) elDir.textContent = window.state?.tenant?.director_nome || 'Director da Escola';

    rodape.classList.remove('d-none');
  }
}

function aoMudarNotaExame(inputEl) {
  const alunoId = inputEl.getAttribute('data-aluno');
  const discId = inputEl.getAttribute('data-disc');
  const epoca = inputEl.getAttribute('data-epoca');
  let valStr = inputEl.value.trim().replace(',', '.');
  let valNum = null;

  if (valStr !== '' && !isNaN(Number(valStr))) {
    valNum = Math.max(0, Math.min(20, Number(valStr)));
    valNum = Math.round(valNum * 100) / 100; // Inteiros ou decimais com 1 ou 2 casas decimais em [0, 20]
    inputEl.value = valNum;
  } else {
    inputEl.value = '';
  }

  const chave = `${alunoId}_${discId}`;
  if (!window._sigeNotasExameModificadas.has(chave)) {
    window._sigeNotasExameModificadas.set(chave, { aluno_id: alunoId, disciplina_id: discId });
  }
  const obj = window._sigeNotasExameModificadas.get(chave);
  if (epoca === '1') obj.exame_1epoca = valNum;
  if (epoca === '2') obj.exame_2epoca = valNum;

  // Recalcular dinamicamente Média da Disciplina e Resultado do Aluno na interface
  recalcularLinhaAlunoInterface(alunoId);

  // Destacar botão de salvar com indicação visual de alteração pendente
  const btnSalvar = document.getElementById('btnSalvarNotasExame');
  if (btnSalvar) {
    btnSalvar.classList.add('btn-warning');
    btnSalvar.classList.remove('btn-primary');
    btnSalvar.innerHTML = `<i class="bi bi-floppy-fill me-1"></i> Guardar Alterações (${window._sigeNotasExameModificadas.size})`;
  }
}

function recalcularLinhaAlunoInterface(alunoId) {
  if (!window._sigePautaExamesData) return;
  const d = window._sigePautaExamesData;
  const aluno = (d.alunos || []).find(a => a.id === alunoId);
  if (!aluno) return;

  const params = d.parametros || { peso_frequencia: 50, peso_exame: 50, nota_minima_exame: 10 };
  const pesoFreq = Number(params.peso_frequencia || 50);
  const pesoExame = Number(params.peso_exame || 50);
  const notaMinima = Number(params.nota_minima_exame || 10);

  const disciplinasComExame = d.disciplinas_com_exame || [];
  const disciplinasSemExame = d.disciplinas_sem_exame || [];
  const grauAno = d.turma?.grau_ano || '10ª Classe';
  const is12a = /(^|[^\d])12([ªaº\.\s]|$)/i.test(grauAno);
  const sufixoGen = (aluno.genero || 'M').toUpperCase().startsWith('F') ? 'a' : 'o';

  const notasFinais = [];
  const discReprovadas = [];
  let temAlgumExame = false;
  let alunoTem2ePendente = false;

  disciplinasComExame.forEach(disc => {
    const dId = disc.id;
    const dData = aluno.disciplinas?.[dId] || {};
    const chave = `${alunoId}_${dId}`;
    const mod = window._sigeNotasExameModificadas.get(chave);

    const e1 = mod && mod.exame_1epoca !== undefined ? mod.exame_1epoca : dData.exame_1epoca;
    const e2 = mod && mod.exame_2epoca !== undefined ? mod.exame_2epoca : dData.exame_2epoca;

    const e1Num = (e1 !== null && e1 !== undefined && e1 !== '') ? Number(e1) : null;
    const e2Num = (e2 !== null && e2 !== undefined && e2 !== '') ? Number(e2) : null;

    if (e1Num !== null || e2Num !== null) {
      temAlgumExame = true;
    }

    let neEfetivo = null;
    let discEm2e = false;

    if (e1Num !== null && e1Num >= notaMinima) {
      // Passou logo na 1ª época!
      neEfetivo = e1Num;
    } else if (e1Num !== null && e1Num < notaMinima) {
      // Não passou na 1ª época -> tem direito à 2ª época
      if (e2Num !== null) {
        neEfetivo = e2Num;
      } else {
        // Aguarda 2ª época
        discEm2e = true;
        alunoTem2ePendente = true;
      }
    } else if (e1Num === null && e2Num !== null) {
      neEfetivo = e2Num;
    }

    const freqVal = typeof dData.frequencia_decimal === 'number' ? dData.frequencia_decimal : (typeof dData.frequencia === 'number' ? dData.frequencia : null);
    let mediaFinalDisc = null;

    if (neEfetivo !== null) {
      if (freqVal !== null) {
        mediaFinalDisc = Math.round((freqVal * (pesoFreq / 100)) + (neEfetivo * (pesoExame / 100)));
      } else {
        mediaFinalDisc = Math.round(neEfetivo);
      }
    } else {
      // REGRA SOLICITADA: Se não tem nota num dos exames (1ª ou 2ª) então a Média nessa disciplina é 0
      mediaFinalDisc = 0;
    }

    const elMedia = document.getElementById(`media_${alunoId}_${dId}`);
    if (elMedia) {
      elMedia.textContent = mediaFinalDisc;
      elMedia.className = `text-center border-end font-monospace small align-middle ${mediaFinalDisc >= 9.5 ? 'text-success fw-bold' : 'text-danger fw-bold'}`;
    }

    notasFinais.push(mediaFinalDisc);
    if (mediaFinalDisc < 9.5) {
      discReprovadas.push(disc.nome);
    }
  });

  disciplinasSemExame.forEach(disc => {
    const dData = aluno.disciplinas?.[disc.id] || {};
    const fVal = typeof dData.frequencia === 'number' ? dData.frequencia : 0;
    notasFinais.push(fVal);
    if (fVal < 9.5) discReprovadas.push(disc.nome);
  });

  // Atualizar Resultado Final: 'Aprovado' se todas positivas e MF >= 9.5, caso contrário 'Reprovado'
  let resAprov = `Reprovad${sufixoGen}`;
  let mfGlobal = 0;

  if (notasFinais.length > 0) {
    const soma = notasFinais.reduce((acc, v) => acc + v, 0);
    mfGlobal = Math.round(soma / notasFinais.length);

    const aprovadoGeral = (discReprovadas.length === 0 && mfGlobal >= 9.5);
    resAprov = aprovadoGeral ? `Aprovad${sufixoGen}` : `Reprovad${sufixoGen}`;
  }

  const elRes = document.getElementById(`res_aluno_${alunoId}`);
  if (elRes) {
    elRes.textContent = resAprov;
    // Sem pintar: 'Aprovado' a preto e 'Reprovado' a vermelho
    if (resAprov.includes('Aprovad')) {
      elRes.className = 'text-dark fw-bold';
      elRes.style.color = '#000000';
    } else {
      elRes.className = 'text-danger fw-bold';
      elRes.style.color = '#dc2626';
    }
    elRes.style.background = 'transparent';
  }

  const elMf = document.getElementById(`mf_aluno_${alunoId}`);
  if (elMf) elMf.textContent = mfGlobal;

  const elRep = document.getElementById(`rep_aluno_${alunoId}`);
  if (elRep) elRep.textContent = discReprovadas.length > 0 ? discReprovadas.join(', ') : '---';
}

// Janela & Parâmetros Oficiais de Avaliação de Exame (MEC)
function atualizarCamposParametrosExameNaInterface(p) {
  if (!p) return;
  const pf = p.peso_frequencia !== undefined ? Number(p.peso_frequencia) : 50;
  const pe = p.peso_exame !== undefined ? Number(p.peso_exame) : 50;
  const nm = p.nota_minima_exame !== undefined ? Number(p.nota_minima_exame) : 10.0;

  // Atualizar inputs da janela inline
  const inpInFreq = document.getElementById('inlineParamPesoFreq');
  const inpInEx = document.getElementById('inlineParamPesoExame');
  const inpInMin = document.getElementById('inlineParamNotaMinima');
  if (inpInFreq) inpInFreq.value = pf;
  if (inpInEx) inpInEx.value = pe;
  if (inpInMin) inpInMin.value = nm;

  // Atualizar inputs do modal flutuante
  const inpModFreq = document.getElementById('inputParamPesoFreq');
  const inpModEx = document.getElementById('inputParamPesoExame');
  const inpModMin = document.getElementById('inputParamNotaMinima');
  if (inpModFreq) inpModFreq.value = pf;
  if (inpModEx) inpModEx.value = pe;
  if (inpModMin) inpModMin.value = nm;

  // Atualizar fórmulas visuais
  const lblF = document.getElementById('labelFormulaFreq');
  const lblE = document.getElementById('labelFormulaExame');
  if (lblF) lblF.textContent = `${pf}%`;
  if (lblE) lblE.textContent = `${pe}%`;

  // Atualizar badges
  const badgeParam = document.getElementById('badgeParametrosAtivos');
  if (badgeParam) badgeParam.textContent = `Freq: ${pf}% | Exame: ${pe}% | Mín: ${nm}`;

  const badgeClasse = document.getElementById('classeExameBadgeParametros');
  if (badgeClasse) badgeClasse.textContent = `Freq: ${pf}% | Exame: ${pe}% | Nota Mínima: ${nm}`;

  verificarAlertaPesos(pf, pe);
}

function alternarJanelaParametrosExame() {
  abrirModalParametrosExame();
}

async function abrirModalParametrosExame() {
  const modalEl = document.getElementById('modalParametrosExame');
  if (!modalEl) return;

  try {
    const res = await apiFetch('/api/v1/pautas/exames/parametros');
    if (res && res.success && res.parametros) {
      atualizarCamposParametrosExameNaInterface(res.parametros);
    }
  } catch (err) {
    console.warn('Erro ao carregar parâmetros de exame:', err);
  }

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
}

function aoMudarPesoFrequencia(val) {
  const num = Math.max(0, Math.min(100, Number(val) || 0));
  const comp = 100 - num;
  const inpEx = document.getElementById('inputParamPesoExame');
  if (inpEx) inpEx.value = comp;

  // Sincronizar com inline
  const inpInFreq = document.getElementById('inlineParamPesoFreq');
  const inpInEx = document.getElementById('inlineParamPesoExame');
  if (inpInFreq) inpInFreq.value = num;
  if (inpInEx) inpInEx.value = comp;

  const lblF = document.getElementById('labelFormulaFreq');
  const lblE = document.getElementById('labelFormulaExame');
  if (lblF) lblF.textContent = `${num}%`;
  if (lblE) lblE.textContent = `${comp}%`;

  verificarAlertaPesos(num, comp);
}

function aoMudarPesoExame(val) {
  const num = Math.max(0, Math.min(100, Number(val) || 0));
  const comp = 100 - num;
  const inpFreq = document.getElementById('inputParamPesoFreq');
  if (inpFreq) inpFreq.value = comp;

  // Sincronizar com inline
  const inpInFreq = document.getElementById('inlineParamPesoFreq');
  const inpInEx = document.getElementById('inlineParamPesoExame');
  if (inpInFreq) inpInFreq.value = comp;
  if (inpInEx) inpInEx.value = num;

  const lblF = document.getElementById('labelFormulaFreq');
  const lblE = document.getElementById('labelFormulaExame');
  if (lblF) lblF.textContent = `${comp}%`;
  if (lblE) lblE.textContent = `${num}%`;

  verificarAlertaPesos(comp, num);
}

function aoMudarPesoFrequenciaInline(val) {
  aoMudarPesoFrequencia(val);
}

function aoMudarPesoExameInline(val) {
  aoMudarPesoExame(val);
}

function verificarAlertaPesos(pf, pe) {
  const alertaModal = document.getElementById('alertaSomaPesos');
  const alertaInline = document.getElementById('alertaSomaPesosInline');
  const badgeSoma = document.getElementById('badgeStatusSomaPesos');

  const valido = Math.round(pf + pe) === 100;
  if (!valido) {
    if (alertaModal) alertaModal.classList.remove('d-none');
    if (alertaInline) alertaInline.classList.remove('d-none');
    if (badgeSoma) {
      badgeSoma.className = 'badge bg-danger px-2 py-1';
      badgeSoma.textContent = `Soma: ${Math.round(pf + pe)}% (Inválido)`;
    }
  } else {
    if (alertaModal) alertaModal.classList.add('d-none');
    if (alertaInline) alertaInline.classList.add('d-none');
    if (badgeSoma) {
      badgeSoma.className = 'badge bg-success px-2 py-1';
      badgeSoma.textContent = 'Soma: 100% OK';
    }
  }
}

async function reporParametrosExamePadraoMEC() {
  const pPadrao = { peso_frequencia: 50, peso_exame: 50, nota_minima_exame: 10.0 };
  atualizarCamposParametrosExameNaInterface(pPadrao);
  await salvarParametrosExame();
}

async function salvarParametrosExame() {
  const inpFreq = document.getElementById('inputParamPesoFreq');
  const inpEx = document.getElementById('inputParamPesoExame');
  const inpMin = document.getElementById('inputParamNotaMinima');

  const pf = Number(inpFreq?.value || 50);
  const pe = Number(inpEx?.value || 50);
  const nm = Number(inpMin?.value || 10);

  if (isNaN(pf) || isNaN(pe) || isNaN(nm)) {
    mostrarToast('Preencha valores numéricos válidos.', 'warning');
    return;
  }

  if (Math.round(pf + pe) !== 100) {
    mostrarToast('A soma da percentagem de frequência e exame deve ser exatamente 100%.', 'danger');
    return;
  }

  if (nm < 0 || nm > 20) {
    mostrarToast('A nota mínima do exame deve estar entre 0 e 20 valores.', 'danger');
    return;
  }

  try {
    const res = await apiFetch('/api/v1/pautas/exames/parametros/', {
      method: 'POST',
      body: JSON.stringify({
        peso_frequencia: pf,
        peso_exame: pe,
        nota_minima_exame: nm
      })
    });

    if (res && res.success) {
      mostrarToast(res.message || 'Parâmetros de exame configurados com sucesso!', 'success');
      const modalEl = document.getElementById('modalParametrosExame');
      if (modalEl) {
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
      }
      atualizarCamposParametrosExameNaInterface({
        peso_frequencia: pf,
        peso_exame: pe,
        nota_minima_exame: nm
      });

      // Recarregar pauta de exames para atualizar todos os cálculos
      const turmaId = document.getElementById('exameTurmaSelect')?.value;
      if (turmaId) {
        await carregarPautaExamesTurma();
      }
    } else {
      mostrarToast(res?.message || 'Erro ao guardar parâmetros.', 'danger');
    }
  } catch (err) {
    console.error('Erro ao guardar parâmetros de exame:', err);
    mostrarToast('Erro de comunicação ao guardar parâmetros.', 'danger');
  }
}

async function salvarParametrosExameInline() {
  const inpFreq = document.getElementById('inlineParamPesoFreq');
  const inpEx = document.getElementById('inlineParamPesoExame');
  const inpMin = document.getElementById('inlineParamNotaMinima');

  const pf = Number(inpFreq?.value || 50);
  const pe = Number(inpEx?.value || 50);
  const nm = Number(inpMin?.value || 10);

  if (isNaN(pf) || isNaN(pe) || isNaN(nm)) {
    mostrarToast('Preencha valores numéricos válidos.', 'warning');
    return;
  }

  if (Math.round(pf + pe) !== 100) {
    mostrarToast('A soma da percentagem de frequência e exame deve ser exatamente 100%.', 'danger');
    return;
  }

  if (nm < 0 || nm > 20) {
    mostrarToast('A nota mínima do exame deve estar entre 0 e 20 valores.', 'danger');
    return;
  }

  const btnSalvar = document.getElementById('btnSalvarParametrosInline');
  if (btnSalvar) {
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> A guardar...`;
  }

  try {
    const res = await apiFetch('/api/v1/pautas/exames/parametros/', {
      method: 'POST',
      body: JSON.stringify({
        peso_frequencia: pf,
        peso_exame: pe,
        nota_minima_exame: nm
      })
    });

    if (res && res.success) {
      mostrarToast(res.message || 'Parâmetros de exame configurados com sucesso!', 'success');
      atualizarCamposParametrosExameNaInterface({
        peso_frequencia: pf,
        peso_exame: pe,
        nota_minima_exame: nm
      });

      // Recarregar pauta de exames para atualizar todos os cálculos
      const turmaId = document.getElementById('exameTurmaSelect')?.value;
      if (turmaId) {
        await carregarPautaExamesTurma();
      }
    } else {
      mostrarToast(res?.message || 'Erro ao guardar parâmetros.', 'danger');
    }
  } catch (err) {
    console.error('Erro ao guardar parâmetros de exame:', err);
    mostrarToast('Erro de comunicação ao guardar parâmetros.', 'danger');
  } finally {
    if (btnSalvar) {
      btnSalvar.disabled = false;
      btnSalvar.innerHTML = `<i class="bi bi-check-circle-fill me-1"></i> Guardar Parâmetros`;
    }
  }
}

async function salvarNotasExame() {
  const turmaId = document.getElementById('exameTurmaSelect')?.value;
  const anoSelect = document.getElementById('exameAnoSelect');
  const anoLetivo = anoSelect?.value || (window.state?.tenant?.ano_letivo_ativo || '2026');
  if (!turmaId) {
    mostrarToast('Selecione uma turma de exame primeiro.', 'warning');
    return;
  }

  if (window._sigeNotasExameModificadas.size === 0) {
    mostrarToast('Nenhuma alteração de nota de exame para guardar.', 'info');
    return;
  }

  const notasPayload = Array.from(window._sigeNotasExameModificadas.values());
  const btnSalvar = document.getElementById('btnSalvarNotasExame');
  if (btnSalvar) {
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> A guardar...`;
  }

  try {
    const res = await apiFetch(`/api/v1/pautas/exames/turma/${turmaId}/salvar/`, {
      method: 'POST',
      body: JSON.stringify({
        ano_letivo: anoLetivo,
        notas: notasPayload
      })
    });

    if (res && res.success) {
      mostrarToast(res.message || 'Notas de exame guardadas com sucesso na base de dados!', 'success');
      window._sigeNotasExameModificadas.clear();
      if (btnSalvar) {
        btnSalvar.disabled = false;
        btnSalvar.classList.remove('btn-warning');
        btnSalvar.classList.add('btn-primary');
        btnSalvar.innerHTML = `<i class="bi bi-floppy-fill me-1"></i> Guardar Notas de Exame`;
      }
      // Recarregar dados para sincronizar cálculos com o backend
      await carregarPautaExamesTurma();
    } else {
      mostrarToast(res?.message || 'Erro ao guardar notas de exame.', 'danger');
      if (btnSalvar) btnSalvar.disabled = false;
    }
  } catch (err) {
    console.error('Erro ao salvar notas de exame:', err);
    mostrarToast('Erro de comunicação ao salvar notas.', 'danger');
    if (btnSalvar) btnSalvar.disabled = false;
  }
}

async function exportarPautaExamesExcel() {
  const turmaId = document.getElementById('exameTurmaSelect')?.value;
  const anoSelect = document.getElementById('exameAnoSelect');
  const anoLetivo = anoSelect?.value || (window.state?.tenant?.ano_letivo_ativo || '2026');
  if (!turmaId) {
    mostrarToast('Selecione uma turma com exame para exportar.', 'warning');
    return;
  }
  const nomeTurma = (document.getElementById('exameTurmaSelect')?.selectedOptions[0]?.text || 'Turma').replace(/[^\w\-]/g, '_');
  await downloadFicheiroBinario(`/api/v1/pautas/exames/turma/${turmaId}/xlsx?anoLetivo=${anoLetivo}`, `Pauta_Exames_${nomeTurma}_${anoLetivo}.xlsx`);
}

async function descarregarPautaExamesPdf() {
  const turmaId = document.getElementById('exameTurmaSelect')?.value;
  const anoSelect = document.getElementById('exameAnoSelect');
  const anoLetivo = anoSelect?.value || (window.state?.tenant?.ano_letivo_ativo || '2026');
  if (!turmaId) {
    mostrarToast('Selecione uma turma com exame para exportar.', 'warning');
    return;
  }
  const nomeTurma = (document.getElementById('exameTurmaSelect')?.selectedOptions[0]?.text || 'Turma').replace(/[^\w\-]/g, '_');
  await downloadFicheiroBinario(`/api/v1/pautas/exames/turma/${turmaId}/pdf?anoLetivo=${anoLetivo}`, `Pauta_Exames_${nomeTurma}_${anoLetivo}.pdf`);
}

function imprimirPautaExames() {
  document.body.classList.remove('print-orientacao-portrait');
  document.body.classList.add('print-orientacao-landscape');
  window.print();
}

// Exportar globalmente para chamadas do HTML e navegação SPA
window.carregarExames = carregarExames;
window.filtrarTurmasExamesPorClasse = filtrarTurmasExamesPorClasse;
window.carregarPautaExamesTurma = carregarPautaExamesTurma;
window.aoMudarNotaExame = aoMudarNotaExame;
window.salvarNotasExame = salvarNotasExame;
window.exportarPautaExamesExcel = exportarPautaExamesExcel;
window.descarregarPautaExamesPdf = descarregarPautaExamesPdf;
window.imprimirPautaExames = imprimirPautaExames;
window.abrirModalParametrosExame = abrirModalParametrosExame;
window.aoMudarPesoFrequencia = aoMudarPesoFrequencia;
window.aoMudarPesoExame = aoMudarPesoExame;
window.salvarParametrosExame = salvarParametrosExame;
window.alternarJanelaParametrosExame = alternarJanelaParametrosExame;
window.aoMudarPesoFrequenciaInline = aoMudarPesoFrequenciaInline;
window.aoMudarPesoExameInline = aoMudarPesoExameInline;
window.salvarParametrosExameInline = salvarParametrosExameInline;
window.reporParametrosExamePadraoMEC = reporParametrosExamePadraoMEC;
window.atualizarCamposParametrosExameNaInterface = atualizarCamposParametrosExameNaInterface;


// =====================================================================
// DELEGAÇÃO DE PERMISSÕES DE LANÇAMENTO DE EXAMES (DIRECTOR PEDAGÓGICO)
// =====================================================================

let _professoresExameCache = [];
let _classesExameCache = [];
let _autorizacoesExameCache = new Map();
let _modoPermissaoExames = 'ALGUNS_PROFESSORES';

function selecionarModoPermissaoExame(modo) {
  _modoPermissaoExames = modo || 'ALGUNS_PROFESSORES';

  const radioDap = document.getElementById('radioModoApenasDap');
  const radioAlguns = document.getElementById('radioModoAlgunsProfessores');
  const radioTodos = document.getElementById('radioModoTodosProfessores');

  if (radioDap) radioDap.checked = (_modoPermissaoExames === 'APENAS_DAP');
  if (radioAlguns) radioAlguns.checked = (_modoPermissaoExames === 'ALGUNS_PROFESSORES');
  if (radioTodos) radioTodos.checked = (_modoPermissaoExames === 'TODOS_PROFESSORES');

  const cardDap = document.getElementById('cardModoApenasDap');
  const cardAlguns = document.getElementById('cardModoAlgunsProfessores');
  const cardTodos = document.getElementById('cardModoTodosProfessores');

  [cardDap, cardAlguns, cardTodos].forEach(c => {
    if (c) {
      c.classList.remove('border-primary', 'bg-primary', 'bg-opacity-10', 'border-danger', 'bg-danger', 'border-success', 'bg-success');
    }
  });

  const containerMatriz = document.getElementById('containerMatrizProfessoresClasses');
  const avisoModo = document.getElementById('avisoModoPermissaoSelecionado');
  const textoModo = document.getElementById('textoModoPermissaoSelecionado');

  if (_modoPermissaoExames === 'APENAS_DAP') {
    if (cardDap) cardDap.classList.add('border-danger', 'bg-danger', 'bg-opacity-10');
    if (containerMatriz) containerMatriz.classList.add('d-none');
    if (avisoModo && textoModo) {
      avisoModo.className = 'alert alert-danger py-2 px-3 small mb-3';
      textoModo.innerHTML = '<strong>Regime Exclusivo:</strong> O lançamento de notas de exame nesta instituição é exclusivo do <strong>Director Pedagógico</strong> e Directoria da Escola. Professores têm apenas acesso para consulta e visualização das pautas.';
      avisoModo.classList.remove('d-none');
    }
  } else if (_modoPermissaoExames === 'TODOS_PROFESSORES') {
    if (cardTodos) cardTodos.classList.add('border-success', 'bg-success', 'bg-opacity-10');
    if (containerMatriz) containerMatriz.classList.add('d-none');
    if (avisoModo && textoModo) {
      avisoModo.className = 'alert alert-success py-2 px-3 small mb-3';
      textoModo.innerHTML = '<strong>Regime Aberto:</strong> Todos os professores ativos da instituição têm permissão para lançar notas de exame em todas as turmas e classes com exame.';
      avisoModo.classList.remove('d-none');
    }
  } else {
    // ALGUNS_PROFESSORES (indicados)
    if (cardAlguns) cardAlguns.classList.add('border-primary', 'bg-primary', 'bg-opacity-10');
    if (containerMatriz) containerMatriz.classList.remove('d-none');
    if (avisoModo) avisoModo.classList.add('d-none');
  }
}

async function abrirModalProfessoresExame() {
  const modalEl = document.getElementById('modalProfessoresExame');
  if (!modalEl) return;

  const bsModal = new bootstrap.Modal(modalEl);
  bsModal.show();

  const tbody = document.getElementById('tbodyProfessoresExameModal');
  const theadRow = document.getElementById('theadProfessoresExameRow');
  const badgesBox = document.getElementById('modalExameBadgesClasses');
  const contadorInfo = document.getElementById('contadorProfessoresAutorizadosInfo');

  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="py-4 text-center text-muted">
          <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
          A carregar professores e classes com exame da instituição...
        </td>
      </tr>
    `;
  }

  try {
    const data = await apiFetch('/api/v1/pautas/exames/professores-autorizados/');
    if (!data || !data.success) {
      throw new Error(data?.message || 'Falha ao consultar permissões de exames');
    }

    _professoresExameCache = data.professores || [];
    _classesExameCache = data.classes_com_exame || ['10ª Classe', '12ª Classe'];
    _autorizacoesExameCache.clear();

    const modo = data.modo_permissao || 'ALGUNS_PROFESSORES';
    selecionarModoPermissaoExame(modo);

    const autorizacoes = data.autorizacoes || [];
    autorizacoes.forEach(a => {
      if (a.professor_id && a.ativo !== false) {
        _autorizacoesExameCache.set(String(a.professor_id), new Set(a.classes || []));
      }
    });

    // Renderizar badges das classes com exame disponíveis automaticamente
    if (badgesBox) {
      badgesBox.innerHTML = _classesExameCache.map(c => `
        <span class="badge bg-primary px-2 py-1"><i class="bi bi-mortarboard me-1"></i>${c}</span>
      `).join(' ');
    }

    // Renderizar cabeçalho da tabela com colunas dinâmicas para cada classe com exame
    if (theadRow) {
      let ths = `
        <th class="text-start ps-3" style="min-width: 200px;">Professor</th>
        <th style="min-width: 120px;">Especialidade</th>
      `;
      _classesExameCache.forEach(c => {
        ths += `<th class="text-center" style="min-width: 100px;"><i class="bi bi-check2-circle text-primary me-1"></i>${c}</th>`;
      });
      ths += `<th style="min-width: 110px;">Ações Rápidas</th>`;
      theadRow.innerHTML = ths;
    }

    renderizarLinhasProfessoresModalExame();

  } catch (err) {
    console.error('Erro ao abrir modal de professores autorizados:', err);
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" class="py-3 text-center text-danger">
            <i class="bi bi-exclamation-triangle-fill me-1"></i> Não foi possível carregar os dados de professores e classes.
          </td>
        </tr>
      `;
    }
  }
}

function renderizarLinhasProfessoresModalExame() {
  const tbody = document.getElementById('tbodyProfessoresExameModal');
  const contadorInfo = document.getElementById('contadorProfessoresAutorizadosInfo');
  if (!tbody) return;

  const termo = (document.getElementById('filtroProfessoresExameInput')?.value || '').toLowerCase().trim();
  const profsFiltrados = _professoresExameCache.filter(p => {
    if (!termo) return true;
    return (p.nome || '').toLowerCase().includes(termo) ||
           (p.codigo || '').toLowerCase().includes(termo) ||
           (p.especialidade || '').toLowerCase().includes(termo);
  });

  if (profsFiltrados.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="${_classesExameCache.length + 3}" class="py-4 text-center text-muted">
          Nenhum professor encontrado com os critérios de pesquisa.
        </td>
      </tr>
    `;
    return;
  }

  let totalAutorizados = 0;
  _professoresExameCache.forEach(p => {
    const s = _autorizacoesExameCache.get(String(p.id));
    if (s && s.size > 0) totalAutorizados++;
  });

  if (contadorInfo) {
    contadorInfo.innerHTML = `<strong>${totalAutorizados}</strong> de <strong>${_professoresExameCache.length}</strong> professor(es) com autorização activa.`;
  }

  let trs = '';
  profsFiltrados.forEach(p => {
    const pId = String(p.id);
    const classesAutorizadas = _autorizacoesExameCache.get(pId) || new Set();

    let tdsClasses = '';
    _classesExameCache.forEach(c => {
      const isChecked = classesAutorizadas.has(c);
      tdsClasses += `
        <td class="text-center align-middle">
          <input type="checkbox" class="form-check-input chk-prof-classe shadow-none"
            style="width: 19px; height: 19px; cursor: pointer;"
            data-prof-id="${pId}" data-classe="${c}"
            ${isChecked ? 'checked' : ''}
            onchange="aoAlternarPermissaoClasseProf('${pId}', '${c}', this.checked)">
        </td>
      `;
    });

    trs += `
      <tr id="linha_prof_perm_${pId}">
        <td class="text-start ps-3 align-middle">
          <div class="fw-bold text-dark">${p.nome}</div>
          <small class="text-muted font-monospace">${p.codigo || 'Docente'}</small>
        </td>
        <td class="align-middle text-muted small">${p.especialidade || '---'}</td>
        ${tdsClasses}
        <td class="align-middle">
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-primary btn-sm py-0 px-2" style="font-size: 0.75rem;" onclick="marcarClassesDoProfessor('${pId}', true)" title="Autorizar em todas as classes com exame">
              Todas
            </button>
            <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-2" style="font-size: 0.75rem;" onclick="marcarClassesDoProfessor('${pId}', false)" title="Revogar de todas as classes">
              Nenhuma
            </button>
          </div>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = trs;
}

function aoAlternarPermissaoClasseProf(pId, classe, isChecked) {
  if (!_autorizacoesExameCache.has(pId)) {
    _autorizacoesExameCache.set(pId, new Set());
  }
  const setClasses = _autorizacoesExameCache.get(pId);
  if (isChecked) {
    setClasses.add(classe);
  } else {
    setClasses.delete(classe);
  }
  atualizarContadorModalProfessores();
}

function marcarClassesDoProfessor(pId, marcar) {
  if (!_autorizacoesExameCache.has(pId)) {
    _autorizacoesExameCache.set(pId, new Set());
  }
  const setClasses = _autorizacoesExameCache.get(pId);
  if (marcar) {
    _classesExameCache.forEach(c => setClasses.add(c));
  } else {
    setClasses.clear();
  }
  renderizarLinhasProfessoresModalExame();
}

function marcarTodosProfessoresTodasClasses(marcar) {
  _professoresExameCache.forEach(p => {
    const pId = String(p.id);
    if (!_autorizacoesExameCache.has(pId)) {
      _autorizacoesExameCache.set(pId, new Set());
    }
    const setClasses = _autorizacoesExameCache.get(pId);
    if (marcar) {
      _classesExameCache.forEach(c => setClasses.add(c));
    } else {
      setClasses.clear();
    }
  });
  renderizarLinhasProfessoresModalExame();
}

function filtrarTabelaProfessoresExame() {
  renderizarLinhasProfessoresModalExame();
}

function atualizarContadorModalProfessores() {
  let totalAutorizados = 0;
  _professoresExameCache.forEach(p => {
    const s = _autorizacoesExameCache.get(String(p.id));
    if (s && s.size > 0) totalAutorizados++;
  });
  const contadorInfo = document.getElementById('contadorProfessoresAutorizadosInfo');
  if (contadorInfo) {
    contadorInfo.innerHTML = `<strong>${totalAutorizados}</strong> de <strong>${_professoresExameCache.length}</strong> professor(es) com autorização activa.`;
  }
}

async function salvarProfessoresAutorizadosExame() {
  const btn = document.getElementById('btnSalvarProfessoresExame');
  const txtOriginal = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> A guardar...';
  }

  const payloadAutorizacoes = [];
  _professoresExameCache.forEach(p => {
    const pId = String(p.id);
    const setClasses = _autorizacoesExameCache.get(pId);
    if (setClasses && setClasses.size > 0) {
      payloadAutorizacoes.push({
        professor_id: pId,
        professor_nome: p.nome,
        classes: Array.from(setClasses),
        ativo: true
      });
    }
  });

  try {
    const json = await apiFetch('/api/v1/pautas/exames/professores-autorizados/', {
      method: 'POST',
      body: JSON.stringify({
        modo_permissao: _modoPermissaoExames,
        autorizacoes: payloadAutorizacoes
      })
    });

    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao(json.message || 'Permissões guardadas com sucesso!', 'success');
    } else if (typeof mostrarToast === 'function') {
      mostrarToast(json.message || 'Permissões guardadas com sucesso!', 'success');
    }

    const modalEl = document.getElementById('modalProfessoresExame');
    if (modalEl) {
      const modalInst = bootstrap.Modal.getInstance(modalEl);
      if (modalInst) modalInst.hide();
    }

    if (typeof carregarPautaExamesTurma === 'function') {
      carregarPautaExamesTurma();
    }
  } catch (err) {
    console.error('Erro ao guardar autorizações de exame:', err);
    if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao(err.message || 'Erro ao guardar autorizações', 'danger');
    } else if (typeof mostrarToast === 'function') {
      mostrarToast(err.message || 'Erro ao guardar autorizações', 'danger');
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = txtOriginal;
    }
  }
}

window.abrirModalProfessoresExame = abrirModalProfessoresExame;
window.renderizarLinhasProfessoresModalExame = renderizarLinhasProfessoresModalExame;
window.aoAlternarPermissaoClasseProf = aoAlternarPermissaoClasseProf;
window.marcarClassesDoProfessor = marcarClassesDoProfessor;
window.marcarTodosProfessoresTodasClasses = marcarTodosProfessoresTodasClasses;
window.filtrarTabelaProfessoresExame = filtrarTabelaProfessoresExame;
window.salvarProfessoresAutorizadosExame = salvarProfessoresAutorizadosExame;


// =====================================================================
// FORMULÁRIO INDIVIDUAL DE LANÇAMENTO DE NOTAS DE EXAME
// Pesquisa, seleção e formulário amigável de lançamento por candidato
// =====================================================================
window._formExameAlunoAtualId = null;
window._formExameListaAlunos = [];

function abrirModalFormularioLancamentoExame() {
  const modalEl = document.getElementById('modalFormularioLancamentoExame');
  if (!modalEl) return;

  const d = window._sigePautaExamesData;
  if (!d || !Array.isArray(d.alunos) || d.alunos.length === 0) {
    if (typeof mostrarToast === 'function') {
      mostrarToast('Por favor, selecione primeiro uma turma com exame que contenha alunos matriculados.', 'warning');
    } else if (typeof mostrarNotificacao === 'function') {
      mostrarNotificacao('Por favor, selecione primeiro uma turma com exame que contenha alunos matriculados.', 'warning');
    }
    return;
  }

  const podeEditar = d.pode_editar !== false;
  const btnSalvar = document.getElementById('btnSalvarFormExame');
  const btnProximo = document.getElementById('btnSalvarEProximoFormExame');
  if (btnSalvar) btnSalvar.style.display = podeEditar ? '' : 'none';
  if (btnProximo) btnProximo.style.display = podeEditar ? '' : 'none';

  // Atualizar badge dos parâmetros no modal
  const params = d.parametros || { peso_frequencia: 50, peso_exame: 50, nota_minima_exame: 10 };
  const badgeParam = document.getElementById('formExameParametrosBadge');
  if (badgeParam) {
    badgeParam.textContent = `Freq: ${params.peso_frequencia || 50}% | Exame: ${params.peso_exame || 50}% | Mín: ${params.nota_minima_exame || 10}`;
  }

  window._formExameListaAlunos = d.alunos;

  const inputBusca = document.getElementById('formExameAlunoSearch');
  if (inputBusca) inputBusca.value = '';

  popularSelectAlunosFormulario(d.alunos);

  // Selecionar primeiro aluno ou o atual se já existir
  const alunoId = window._formExameAlunoAtualId && d.alunos.some(a => a.id === window._formExameAlunoAtualId)
    ? window._formExameAlunoAtualId
    : d.alunos[0].id;

  selecionarAlunoFormularioExame(alunoId);

  const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
  bsModal.show();
}

function popularSelectAlunosFormulario(alunos) {
  const sel = document.getElementById('formExameAlunoSelect');
  if (!sel) return;
  if (!alunos || alunos.length === 0) {
    sel.innerHTML = '<option value="">Nenhum candidato encontrado</option>';
    return;
  }
  sel.innerHTML = alunos.map((a, idx) => `
    <option value="${a.id}">Nº ${a.numero || idx + 1} - ${a.nome}</option>
  `).join('');
}

function filtrarAlunosFormularioExame(termo) {
  const t = (termo || '').toLowerCase().trim();
  const todos = window._sigePautaExamesData?.alunos || [];
  const filtrados = todos.filter(a => {
    if (!t) return true;
    return (a.nome || '').toLowerCase().includes(t) ||
           String(a.numero || '').includes(t) ||
           (a.matricula || '').toLowerCase().includes(t) ||
           (a.candidato || '').toLowerCase().includes(t);
  });

  popularSelectAlunosFormulario(filtrados);
  if (filtrados.length > 0) {
    selecionarAlunoFormularioExame(filtrados[0].id);
  } else {
    const container = document.getElementById('formExameDisciplinasContainer');
    if (container) {
      container.innerHTML = '<div class="alert alert-warning text-center small my-2">Nenhum candidato encontrado com esse nome ou número.</div>';
    }
  }
}

function navegarAlunoFormularioExame(direcao) {
  const lista = window._sigePautaExamesData?.alunos || [];
  if (lista.length === 0) return;

  const curId = window._formExameAlunoAtualId;
  const curIdx = lista.findIndex(a => a.id === curId);
  let novoIdx = curIdx + direcao;

  if (novoIdx < 0) novoIdx = 0;
  if (novoIdx >= lista.length) novoIdx = lista.length - 1;

  const novoAluno = lista[novoIdx];
  if (novoAluno) {
    selecionarAlunoFormularioExame(novoAluno.id);
  }
}

function selecionarAlunoFormularioExame(alunoId) {
  window._formExameAlunoAtualId = alunoId;
  const d = window._sigePautaExamesData;
  if (!d) return;

  const alunos = d.alunos || [];
  const aluno = alunos.find(a => a.id === alunoId);
  if (!aluno) return;

  const sel = document.getElementById('formExameAlunoSelect');
  if (sel && sel.value !== alunoId) sel.value = alunoId;

  // Atualizar Ficha Resumo do Aluno
  const elNome = document.getElementById('formExameAlunoNome');
  const elNum = document.getElementById('formExameAlunoNumero');
  const elCand = document.getElementById('formExameAlunoCandidato');
  const elTurma = document.getElementById('formExameAlunoTurma');
  const elIniciais = document.getElementById('formExameAlunoIniciais');
  const elPosicao = document.getElementById('formExamePosicaoAlunoInfo');

  const alunoIdx = alunos.findIndex(a => a.id === alunoId);
  if (elNome) elNome.textContent = aluno.nome;
  if (elNum) elNum.textContent = aluno.numero || (alunoIdx + 1);
  if (elCand) elCand.textContent = aluno.candidato || aluno.matricula || '--';
  if (elTurma) elTurma.textContent = aluno.turma || d.turma?.nome || '--';

  if (elIniciais) {
    const partes = (aluno.nome || '').trim().split(/\s+/);
    const init = (partes[0]?.[0] || '') + (partes[partes.length - 1]?.[0] || '');
    elIniciais.textContent = init.toUpperCase() || 'AL';
  }

  if (elPosicao) {
    elPosicao.textContent = `Candidato ${alunoIdx + 1} de ${alunos.length}`;
  }

  // Renderizar disciplinas com exame do aluno
  const container = document.getElementById('formExameDisciplinasContainer');
  const podeEditar = d.pode_editar !== false;
  const disciplinasComExame = d.disciplinas_com_exame || [];

  if (disciplinasComExame.length === 0) {
    if (container) {
      container.innerHTML = `
        <div class="alert alert-warning small text-center my-2">
          Nenhuma disciplina com exame cadastrada para esta classe/turma.
        </div>
      `;
    }
    return;
  }

  let htmlDiscs = '';
  disciplinasComExame.forEach(disc => {
    const dData = aluno.disciplinas?.[disc.id] || {};
    const chave = `${alunoId}_${disc.id}`;
    const mod = window._sigeNotasExameModificadas.get(chave);

    const e1 = (mod && mod.exame_1epoca !== undefined) ? mod.exame_1epoca : dData.exame_1epoca;
    const e2 = (mod && mod.exame_2epoca !== undefined) ? mod.exame_2epoca : dData.exame_2epoca;

    const e1Val = (e1 !== null && e1 !== undefined && e1 !== '') ? e1 : '';
    const e2Val = (e2 !== null && e2 !== undefined && e2 !== '') ? e2 : '';

    const freqVal = (dData.frequencia !== undefined && dData.frequencia !== null) ? dData.frequencia : '-';

    htmlDiscs += `
      <div class="card p-3 border shadow-none bg-white disc-exame-row" id="formDiscRow_${alunoId}_${disc.id}">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-primary px-2 py-1">${disc.codigo || 'EXAME'}</span>
            <strong class="text-dark fs-6">${disc.nome}</strong>
          </div>
          <div class="d-flex align-items-center gap-2">
            <span class="small text-muted">Média de Frequência:</span>
            <span class="badge bg-light text-dark border font-monospace fs-6 px-2 py-1">${freqVal}</span>
          </div>
        </div>

        <div class="row g-2 align-items-center">
          <div class="col-md-4">
            <label class="form-label x-small fw-bold text-muted mb-1">
              <i class="bi bi-pencil me-1"></i>1ª Época (0 a 20)
            </label>
            <input type="number" step="0.01" min="0" max="20"
              class="form-control form-control-sm text-center fw-bold font-monospace form-input-exame"
              id="formInputE1_${alunoId}_${disc.id}"
              placeholder="ex: 12 ou 14.5"
              value="${e1Val}"
              ${!podeEditar ? 'disabled readonly' : ''}
              oninput="aoMudarNotaFormularioExame('${alunoId}', '${disc.id}', '1', this.value)"
              onchange="aoMudarNotaFormularioExame('${alunoId}', '${disc.id}', '1', this.value)">
          </div>

          <div class="col-md-4">
            <label class="form-label x-small fw-bold text-muted mb-1">
              <i class="bi bi-pencil me-1"></i>2ª Época (se necessária)
            </label>
            <input type="number" step="0.01" min="0" max="20"
              class="form-control form-control-sm text-center fw-bold font-monospace form-input-exame"
              id="formInputE2_${alunoId}_${disc.id}"
              placeholder="ex: 10 ou 11.25"
              value="${e2Val}"
              ${!podeEditar ? 'disabled readonly' : ''}
              oninput="aoMudarNotaFormularioExame('${alunoId}', '${disc.id}', '2', this.value)"
              onchange="aoMudarNotaFormularioExame('${alunoId}', '${disc.id}', '2', this.value)">
          </div>

          <div class="col-md-4">
            <label class="form-label x-small fw-bold text-muted mb-1">
              <i class="bi bi-calculator me-1"></i>Média Final da Disciplina
            </label>
            <div class="d-flex align-items-center justify-content-between p-1 px-2 border rounded bg-light">
              <span class="font-monospace fw-bold fs-6" id="formDiscMedia_${alunoId}_${disc.id}">-</span>
              <span class="badge" id="formDiscBadge_${alunoId}_${disc.id}">---</span>
            </div>
          </div>
        </div>
      </div>
    `;
  });

  if (container) container.innerHTML = htmlDiscs;

  recalcularFormularioExame(alunoId);
}

function aoMudarNotaFormularioExame(alunoId, discId, epoca, valor) {
  let valStr = String(valor || '').trim().replace(',', '.');
  let valNum = null;

  if (valStr !== '' && !isNaN(Number(valStr))) {
    valNum = Math.max(0, Math.min(20, Number(valStr)));
    valNum = Math.round(valNum * 100) / 100; // Suporta decimais até 2 casas
  }

  const chave = `${alunoId}_${discId}`;
  if (!window._sigeNotasExameModificadas.has(chave)) {
    window._sigeNotasExameModificadas.set(chave, { aluno_id: alunoId, disciplina_id: discId });
  }
  const obj = window._sigeNotasExameModificadas.get(chave);
  if (epoca === '1') obj.exame_1epoca = valNum;
  if (epoca === '2') obj.exame_2epoca = valNum;

  // Sincronizar input correspondente na tabela principal (se existir)
  const inputTabela = document.querySelector(`input.input-exame-nota[data-aluno="${alunoId}"][data-disc="${discId}"][data-epoca="${epoca}"]`);
  if (inputTabela) {
    inputTabela.value = (valNum !== null) ? valNum : '';
  }

  // Recalcular cálculos na tabela principal
  recalcularLinhaAlunoInterface(alunoId);

  // Recalcular cálculos no modal do formulário
  recalcularFormularioExame(alunoId);

  // Destacar botão de salvar com indicação visual de alteração pendente
  const btnSalvar = document.getElementById('btnSalvarNotasExame');
  if (btnSalvar) {
    btnSalvar.classList.add('btn-warning');
    btnSalvar.classList.remove('btn-primary');
    btnSalvar.innerHTML = `<i class="bi bi-floppy-fill me-1"></i> Guardar Alterações (${window._sigeNotasExameModificadas.size})`;
  }
}

function recalcularFormularioExame(alunoId) {
  const d = window._sigePautaExamesData;
  if (!d) return;

  const aluno = (d.alunos || []).find(a => a.id === alunoId);
  if (!aluno) return;

  const params = d.parametros || { peso_frequencia: 50, peso_exame: 50, nota_minima_exame: 10 };
  const pesoFreq = Number(params.peso_frequencia || 50);
  const pesoExame = Number(params.peso_exame || 50);
  const notaMinima = Number(params.nota_minima_exame || 10);

  const disciplinasComExame = d.disciplinas_com_exame || [];
  const disciplinasSemExame = d.disciplinas_sem_exame || [];
  const sufixoGen = (aluno.genero || 'M').toUpperCase().startsWith('F') ? 'a' : 'o';

  const notasFinais = [];
  const discReprovadas = [];

  disciplinasComExame.forEach(disc => {
    const dId = disc.id;
    const dData = aluno.disciplinas?.[dId] || {};
    const chave = `${alunoId}_${dId}`;
    const mod = window._sigeNotasExameModificadas.get(chave);

    const e1 = (mod && mod.exame_1epoca !== undefined) ? mod.exame_1epoca : dData.exame_1epoca;
    const e2 = (mod && mod.exame_2epoca !== undefined) ? mod.exame_2epoca : dData.exame_2epoca;

    const e1Num = (e1 !== null && e1 !== undefined && e1 !== '') ? Number(e1) : null;
    const e2Num = (e2 !== null && e2 !== undefined && e2 !== '') ? Number(e2) : null;

    let neEfetivo = null;
    if (e1Num !== null && e1Num >= notaMinima) {
      neEfetivo = e1Num;
    } else if (e1Num !== null && e1Num < notaMinima) {
      if (e2Num !== null) neEfetivo = e2Num;
    } else if (e1Num === null && e2Num !== null) {
      neEfetivo = e2Num;
    }

    const freqVal = typeof dData.frequencia_decimal === 'number' ? dData.frequencia_decimal : (typeof dData.frequencia === 'number' ? dData.frequencia : null);
    let mediaFinalDisc = null;

    if (neEfetivo !== null) {
      if (freqVal !== null) {
        mediaFinalDisc = Math.round((freqVal * (pesoFreq / 100)) + (neEfetivo * (pesoExame / 100)));
      } else {
        mediaFinalDisc = Math.round(neEfetivo);
      }
    } else {
      // REGRA: Se não tem nota num dos exames (1ª ou 2ª) então a Média nessa disciplina é 0
      mediaFinalDisc = 0;
    }

    const elMedia = document.getElementById(`formDiscMedia_${alunoId}_${dId}`);
    const elBadge = document.getElementById(`formDiscBadge_${alunoId}_${dId}`);
    if (elMedia) {
      elMedia.textContent = mediaFinalDisc;
      elMedia.className = `font-monospace fw-bold fs-6 ${mediaFinalDisc >= 9.5 ? 'text-success' : 'text-danger'}`;
    }
    if (elBadge) {
      if (mediaFinalDisc >= 9.5) {
        elBadge.className = 'badge bg-success';
        elBadge.textContent = 'Aprovado';
      } else {
        elBadge.className = 'badge bg-danger';
        elBadge.textContent = 'Reprovado';
      }
    }

    notasFinais.push(mediaFinalDisc);
    if (mediaFinalDisc < 9.5) {
      discReprovadas.push(disc.nome);
    }
  });

  disciplinasSemExame.forEach(disc => {
    const dData = aluno.disciplinas?.[disc.id] || {};
    const fVal = typeof dData.frequencia === 'number' ? dData.frequencia : 0;
    notasFinais.push(fVal);
    if (fVal < 9.5) discReprovadas.push(disc.nome);
  });

  let resAprov = `Reprovad${sufixoGen}`;
  let mfGlobal = 0;

  if (notasFinais.length > 0) {
    const soma = notasFinais.reduce((acc, v) => acc + v, 0);
    mfGlobal = Math.round(soma / notasFinais.length);
    const aprovadoGeral = (discReprovadas.length === 0 && mfGlobal >= 9.5);
    resAprov = aprovadoGeral ? `Aprovad${sufixoGen}` : `Reprovad${sufixoGen}`;
  }

  const elResGeral = document.getElementById('formExameAlunoResultadoGeral');
  if (elResGeral) {
    elResGeral.textContent = `${resAprov} (MF: ${mfGlobal})`;
    // Aprovado a preto e Reprovado a vermelho
    if (resAprov.includes('Aprovad')) {
      elResGeral.className = 'fw-bold fs-6';
      elResGeral.style.color = '#000000';
    } else {
      elResGeral.className = 'fw-bold fs-6 text-danger';
      elResGeral.style.color = '#dc2626';
    }
  }
}

async function salvarNotasFormularioExame(irParaProximo = false) {
  const btn = irParaProximo ? document.getElementById('btnSalvarEProximoFormExame') : document.getElementById('btnSalvarFormExame');
  const txtOriginal = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> A guardar...';
  }

  try {
    await salvarNotasExame();
    if (irParaProximo) {
      navegarAlunoFormularioExame(1);
    } else if (window._formExameAlunoAtualId) {
      recalcularFormularioExame(window._formExameAlunoAtualId);
    }
  } catch (err) {
    console.error('Erro ao guardar notas via formulário:', err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = txtOriginal;
    }
  }
}

window.selecionarModoPermissaoExame = selecionarModoPermissaoExame;
window.abrirModalFormularioLancamentoExame = abrirModalFormularioLancamentoExame;
window.filtrarAlunosFormularioExame = filtrarAlunosFormularioExame;
window.selecionarAlunoFormularioExame = selecionarAlunoFormularioExame;
window.navegarAlunoFormularioExame = navegarAlunoFormularioExame;
window.aoMudarNotaFormularioExame = aoMudarNotaFormularioExame;
window.recalcularFormularioExame = recalcularFormularioExame;
window.salvarNotasFormularioExame = salvarNotasFormularioExame;
