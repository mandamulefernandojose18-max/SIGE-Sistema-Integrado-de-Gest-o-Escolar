# SIGE - Front-End SPA Autônomo

Aplicação Web SPA oficial para gestão escolar em Moçambique (MINEDH).

## Características
- **Zero Dependências de Instalação**: roda nativamente com Node.js sem necessidade de `npm install`.
- **Desacoplado da API**: configurado via `js/config.js` para comunicar com qualquer servidor de backend via RESTful API com CORS.
- **PWA Ready**: suporte a Service Worker e Web Manifest offline.
- **Central de Impressão e Exportação**:
  - Geração de PDF e XLSX de Boletins, Declarações, Certificados, Pautas e Actas.
  - Exportação e download em formato **JSON** (.json).

## Como Executar
```bash
# Iniciar o servidor front-end (porta padrão: 5173)
npm start
```
Acesse em seu navegador: [http://localhost:5173](http://localhost:5173)

## Configuração da API
Para apontar para um endereço de backend diferente, edite `js/config.js`:
```javascript
window.SIGE_CONFIG = {
  API_BASE_URL: "http://localhost:3000/api/v1"
};
```
