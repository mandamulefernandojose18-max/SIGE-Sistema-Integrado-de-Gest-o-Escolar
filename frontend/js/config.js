// Configurações Globais do Front-End SIGE
window.SIGE_CONFIG = {
  API_BASE_URL: window.ENV_API_URL || (
    (window.location.port && window.location.port !== '8000' && window.location.port !== '80')
      ? (window.location.protocol + '//' + window.location.hostname + ':8000/api/v1')
      : '/api/v1'
  )
};
