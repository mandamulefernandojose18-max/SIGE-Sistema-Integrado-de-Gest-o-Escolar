# SIGE Frontend — Interface Web SPA Autônoma

Aplicação Web Single-Page Application (SPA / PWA) oficial para gestão escolar em Moçambique (MINEDH).

## Características
- **Desacoplado da API**: comunica-se com o backend via RESTful API com CORS e autenticação Bearer JWT.
- **Zero Dependências Externas em Runtime**: pode ser servido localmente via Node.js nativo (`server.js`) ou em produção via Nginx Alpine (`nginx.conf`).
- **PWA Ready**: suporte a Service Worker (`service-worker.js`) e Web App Manifest (`manifest.json`).
- **Detecção Dinâmica de Ambiente**: configurado via `js/config.js` para apontar automaticamente para a API em desenvolvimento ou produção.
- **Central de Impressão e Gestão**:
  - Geração e visualização de Boletins, Pautas, Actas, Certificados e Declarações.
  - Módulo completo de Material Escolar e Estoque.

## Como Executar

### Modo Desenvolvimento Local (Node.js nativo)
```bash
# Iniciar o servidor front-end (porta padrão: 5173)
npm start
```
Acesse no navegador: `http://localhost:5173`

### Modo Produção (Docker / Nginx)
```bash
docker build -t sige-frontend .
docker run -p 80:80 sige-frontend
```

## Configuração da API
Para apontar para um endereço de backend diferente, defina `window.ENV_API_URL` ou edite `js/config.js`:
```javascript
window.SIGE_CONFIG = {
  API_BASE_URL: "http://localhost:3000/api/v1"
};
```
