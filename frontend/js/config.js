// Configurações Globais do Front-End SIGE baseadas no .env
(function() {
  const currentConfig = window.SIGE_CONFIG || {};
  const defaultHostname = currentConfig.SYSTEM_HOSTNAME || 'localhost';
  const defaultBackendPort = currentConfig.BACKEND_PORT || '8000';
  const defaultBackendHost = currentConfig.BACKEND_HOST || '127.0.0.1';

  const defaultApiUrl = (typeof window !== 'undefined' && (window.location.protocol === 'file:' || (window.location.port !== '5173' && window.location.port !== '80' && window.location.port !== '443' && window.location.port !== '')))
    ? `http://${defaultBackendHost}:${defaultBackendPort}/api/v1`
    : '/api/v1';

  window.SIGE_CONFIG = {
    SYSTEM_HOSTNAME: defaultHostname,
    BACKEND_PORT: defaultBackendPort,
    BACKEND_HOST: defaultBackendHost,
    API_BASE_URL: window.ENV_API_URL || currentConfig.API_BASE_URL || defaultApiUrl
  };
})();
