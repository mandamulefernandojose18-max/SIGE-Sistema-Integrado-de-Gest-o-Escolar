/**
 * SIGE — Módulo Prompt do Gateway (painel-superadmin)
 */
async function carregarPromptGateway() {
  const pre = document.getElementById('conteudoPrompt');
  if (!pre) return;

  try {
    const token = state.token || sessionStorage.getItem('sige_token');
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`/ferramentas/prompt-gateway/descarregar?token=${encodeURIComponent(token || '')}`, {
      headers: headers
    });

    if (res.ok) {
      const texto = await res.text();
      pre.textContent = texto;
    } else if (res.status === 403) {
      pre.textContent = '[Erro 403: Acesso restrito a administradores e direcção.]';
    } else {
      pre.textContent = '[Erro ao carregar o prompt do servidor.]';
    }
  } catch (err) {
    console.error('[PROMPT GATEWAY] Falha ao carregar conteúdo:', err);
    pre.textContent = '[Erro de rede ao ligar ao servidor.]';
  }

  if (typeof window.inicializarPromptGateway === 'function') {
    window.inicializarPromptGateway();
  }
}

window.carregarPromptGateway = carregarPromptGateway;
