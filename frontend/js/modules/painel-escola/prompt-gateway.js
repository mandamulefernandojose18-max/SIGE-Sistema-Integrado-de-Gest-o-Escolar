/**
 * SIGE — Módulo Prompt do Gateway
 */
async function carregarPromptGateway() {
  const pre = document.getElementById('conteudoPrompt');
  if (!pre) return;

  try {
    const token = (typeof state !== 'undefined' && state.token) || sessionStorage.getItem('sige_token');
    const headers = { 'Accept': 'application/json, text/plain, */*' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // 1. Tentar endpoint da API REST
    let obtido = false;
    try {
      const apiUrl = `/api/v1/ferramentas/prompt-gateway/conteudo?token=${encodeURIComponent(token || '')}`;
      const res = await fetch(apiUrl, { headers: headers });
      if (res.ok) {
        const json = await res.json();
        if (json && json.conteudo) {
          pre.textContent = json.conteudo;
          obtido = true;
        }
      }
    } catch (_) {}

    // 2. Se falhar, tentar rota directa de descarga
    if (!obtido) {
      try {
        const res = await fetch(`/ferramentas/prompt-gateway/descarregar?token=${encodeURIComponent(token || '')}`, { headers });
        if (res.ok) {
          const texto = await res.text();
          if (texto && !texto.trim().startsWith('<!DOCTYPE') && !texto.trim().startsWith('<html')) {
            pre.textContent = texto;
            obtido = true;
          }
        }
      } catch (_) {}
    }

    // 3. Se falhar, tentar ficheiro estático directo
    if (!obtido) {
      try {
        const res = await fetch('/conteudo/prompt-gateway.txt');
        if (res.ok) {
          const texto = await res.text();
          if (texto && !texto.trim().startsWith('<!DOCTYPE')) {
            pre.textContent = texto;
            obtido = true;
          }
        }
      } catch (_) {}
    }

    if (!obtido && (!pre.textContent || pre.textContent === '[A carregar prompt...]')) {
      pre.textContent = '[Aviso: Não foi possível obter o ficheiro de conteúdo do servidor.]';
    }
  } catch (err) {
    console.error('[PROMPT GATEWAY] Falha ao carregar conteúdo:', err);
  }

  if (typeof window.inicializarPromptGateway === 'function') {
    window.inicializarPromptGateway();
  }
}

window.carregarPromptGateway = carregarPromptGateway;
