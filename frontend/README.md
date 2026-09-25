# SIGE Frontend — Interface Web SPA Autônoma

Aplicação Web Single-Page Application (SPA / PWA) oficial para gestão escolar em Moçambique (MINEDH).

---

## Características
- **Desacoplado da API**: comunica-se com o backend Django REST Framework via RESTful API com CORS e autenticação Bearer JWT.
- **Zero Dependências Externas em Runtime**: pode ser servido localmente via Node.js nativo (`server.js`) ou em produção via Nginx Alpine (`nginx.conf`).
- **PWA Ready**: suporte a Service Worker (`service-worker.js`) e Web App Manifest (`manifest.json`) com suporte a cache offline.
- **Detecção Dinâmica de Ambiente**: configurado via `js/config.js` para apontar automaticamente para a API em desenvolvimento (`http://localhost:8000/api/v1`) ou produção.
- **Central de Impressão e Gestão**:
  - Geração e visualização de Boletins, Pautas, Actas, Certificados e Declarações.
  - Módulo completo de Material Escolar e Estoque.

---

## Documentação Técnica Completa

A documentação detalhada da interface está organizada no diretório `docs/`:

- 📐 **[Arquitetura do Frontend](docs/ARCHITECTURE.md):** Padrões SPA Vanilla, roteamento client-side, gestão de sessão JWT, tratamento de erro HTTP 402 e estratégia offline PWA.
- 📱 **[Catálogo de Telas e Módulos](docs/PAGES_AND_MODULES.md):** Relação completa das 21 telas/visões detectadas no DOM, tabelas, formulários e mais de 65 chamadas à API RESTful mapeadas.
- 🔌 **[Guia de Integração Frontend ↔ Backend](docs/INTEGRATION_GUIDE.md):** Detalhes da função `apiFetch`, injeção de tokens Bearer JWT, rotas consumidas por módulo e download de arquivos (PDF, XLSX, DOCX).

---

## Atualização Automática da Documentação (Gatilho)

Sempre que uma nova tela, formulário ou funcionalidade for adicionada ao `index.html` ou `js/app.js`, a documentação pode ser atualizada automaticamente:

```bash
# Executar a atualização da documentação:
npm run docs
```

### Gatilhos Ativos no Projeto:
1. **Git Pre-Commit Hook Local:**
   O script `node scripts/install_hooks.js` instala um hook no Git que analisa os arquivos em `index.html` e `js/` a cada commit e atualiza a documentação automaticamente.
2. **GitHub Actions Workflow:**
   O arquivo `.github/workflows/docs-update.yml` analisa alterações em `push` ou `pull_request` nas branches `main` e `develop` e atualiza a documentação no repositório.

---

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

---

## Configuração da API
Para apontar para um endereço de backend diferente, defina `window.ENV_API_URL` ou edite `js/config.js`:
```javascript
window.SIGE_CONFIG = {
  API_BASE_URL: "http://localhost:8000/api/v1"
};
```
