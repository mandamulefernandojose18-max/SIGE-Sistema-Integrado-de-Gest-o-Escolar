// Configurações Globais do Front-End SIGE baseadas no .env
(function() {
  const currentConfig = window.SIGE_CONFIG || {};
  const isFile = typeof window !== 'undefined' && window.location && window.location.protocol === 'file:';
  const isLocalHost = typeof window !== 'undefined' && window.location && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

  // Em qualquer ambiente web (HTTPS de produção, VM, duckdns, IP ou dev local),
  // a API deve usar sempre o caminho relativo '/api/v1' pelo proxy reverso do Nginx/Node.
  // Isso elimina 100% de erros de CORS, Mixed Content (HTTPS bloqueando HTTP) e chamadas inválidas a 127.0.0.1 no cliente móvel.
  let defaultApiUrl = '/api/v1';
  if (isFile) {
    defaultApiUrl = isLocalHost ? 'http://127.0.0.1:8000/api/v1' : 'https://sigesaas.duckdns.org/api/v1';
  }

  window.SIGE_CONFIG = {
    SYSTEM_HOSTNAME: currentConfig.SYSTEM_HOSTNAME || (typeof window !== 'undefined' && window.location ? window.location.hostname : 'localhost'),
    BACKEND_PORT: currentConfig.BACKEND_PORT || '8000',
    BACKEND_HOST: currentConfig.BACKEND_HOST || '127.0.0.1',
    API_BASE_URL: window.ENV_API_URL || currentConfig.API_BASE_URL || defaultApiUrl
  };
})();

