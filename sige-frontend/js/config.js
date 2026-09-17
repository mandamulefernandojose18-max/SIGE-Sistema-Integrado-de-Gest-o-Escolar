// Configura��es Globais do Front-End SIGE
window.SIGE_CONFIG = {
  API_BASE_URL: (window.location.port === '5173' || window.location.port === '8080' || window.location.port === '3001')
    ? (window.location.protocol + '//' + window.location.hostname + ':3000/api/v1')
    : '/api/v1'
};
