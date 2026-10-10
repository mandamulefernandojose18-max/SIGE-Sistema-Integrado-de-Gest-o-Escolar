// Configurações Globais do Front-End SIGE
const defaultApiUrl = (typeof window !== 'undefined' && (window.location.protocol === 'file:' || (window.location.port !== '5173' && window.location.port !== '80' && window.location.port !== '443' && window.location.port !== '')))
  ? 'http://127.0.0.1:8000/api/v1'
  : '/api/v1';

window.SIGE_CONFIG = {
  API_BASE_URL: window.ENV_API_URL || defaultApiUrl
};
