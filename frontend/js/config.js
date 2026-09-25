// Configurações Globais do Front-End SIGE
window.SIGE_CONFIG = {
  API_BASE_URL: window.ENV_API_URL || (
    (window.location.port && window.location.port !== '3000')
      ? (window.location.protocol + '//' + window.location.hostname + ':3000/api/v1')
      : '/api/v1'
  )
};
