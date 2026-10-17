/**
 * SIGE — Ferramentas: Script da Página do Prompt do Gateway
 * Ficheiro estático autónomo e compatível com políticas CSP rigorosas (sem scripts inline).
 * Fornece cópia acessível com fallback (navigator.clipboard -> Range + execCommand)
 * e gestão da região acessível aria-live.
 */
(function () {
  'use strict';

  function inicializarPromptGateway() {
    const btnCopiar = document.getElementById('btnCopiarPrompt');
    const preElemento = document.getElementById('conteudoPrompt');
    const statusCopiado = document.getElementById('statusCopiado');
    const linkDownload = document.getElementById('btnDescarregarPrompt');

    if (!btnCopiar || !preElemento) return;

    // Se estiver no contexto do SIGE com token em sessionStorage, propaga token para o download caso necessário
    try {
      const token = sessionStorage.getItem('sige_token');
      if (token && linkDownload) {
        const hrefAtual = linkDownload.getAttribute('href') || '/ferramentas/prompt-gateway/descarregar';
        if (!hrefAtual.includes('token=')) {
          const separador = hrefAtual.includes('?') ? '&' : '?';
          linkDownload.setAttribute('href', `${hrefAtual}${separador}token=${encodeURIComponent(token)}`);
        }
      }
    } catch (_) {}

    let timeoutAviso = null;

    function exibirFeedbackCopiado() {
      if (!statusCopiado) return;
      if (timeoutAviso) {
        clearTimeout(timeoutAviso);
      }

      statusCopiado.textContent = 'Copiado!';
      statusCopiado.classList.remove('visually-hidden');
      statusCopiado.setAttribute('aria-hidden', 'false');

      if (btnCopiar) {
        btnCopiar.classList.remove('btn-primary');
        btnCopiar.classList.add('btn-success');
        const icone = btnCopiar.querySelector('i');
        if (icone) {
          icone.className = 'bi bi-check2-circle me-1';
        }
      }

      timeoutAviso = setTimeout(function () {
        statusCopiado.textContent = '';
        statusCopiado.classList.add('visually-hidden');
        statusCopiado.setAttribute('aria-hidden', 'true');
        if (btnCopiar) {
          btnCopiar.classList.remove('btn-success');
          btnCopiar.classList.add('btn-primary');
          const icone = btnCopiar.querySelector('i');
          if (icone) {
            icone.className = 'bi bi-clipboard me-1';
          }
        }
      }, 2500);
    }

    async function copiarTextoPrompt() {
      const texto = preElemento.textContent || '';
      if (!texto) return;

      // 1. Abordagem primária: navigator.clipboard.writeText
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        try {
          await navigator.clipboard.writeText(texto);
          exibirFeedbackCopiado();
          return;
        } catch (errClipboard) {
          console.warn('[PROMPT GATEWAY] navigator.clipboard indisponível ou rejeitado, a recorrer a fallback:', errClipboard);
        }
      }

      // 2. Abordagem alternativa: Selecção Range + execCommand('copy')
      try {
        const selecao = window.getSelection();
        if (selecao) {
          const range = document.createRange();
          range.selectNodeContents(preElemento);
          selecao.removeAllRanges();
          selecao.addRange(range);

          const copiadoComSucesso = document.execCommand('copy');
          selecao.removeAllRanges();

          if (copiadoComSucesso) {
            exibirFeedbackCopiado();
            return;
          }
        }
      } catch (errRange) {
        console.warn('[PROMPT GATEWAY] Fallback Range + execCommand falhou:', errRange);
      }

      // 3. Abordagem de reserva extrema: elemento textarea temporário
      try {
        const textareaTemp = document.createElement('textarea');
        textareaTemp.value = texto;
        textareaTemp.setAttribute('readonly', '');
        textareaTemp.style.position = 'fixed';
        textareaTemp.style.top = '-9999px';
        textareaTemp.style.left = '-9999px';
        document.body.appendChild(textareaTemp);
        textareaTemp.select();
        const sucessoTextarea = document.execCommand('copy');
        document.body.removeChild(textareaTemp);

        if (sucessoTextarea) {
          exibirFeedbackCopiado();
        }
      } catch (errFinal) {
        console.error('[PROMPT GATEWAY] Não foi possível copiar o texto:', errFinal);
      }
    }

    btnCopiar.addEventListener('click', copiarTextoPrompt);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarPromptGateway);
  } else {
    inicializarPromptGateway();
  }

  // Exportar para utilização modular no ecossistema SPA do SIGE
  if (typeof window !== 'undefined') {
    window.inicializarPromptGateway = inicializarPromptGateway;
  }
})();
