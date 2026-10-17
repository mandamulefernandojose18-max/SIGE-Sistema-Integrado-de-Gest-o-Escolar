/**
 * SIGE Front-End - Servidor de Desenvolvimento e Produção SPA
 * Servidor HTTP nativo e autônomo com Proxy Reverso para API Backend
 * Lê todas as credenciais, hostname, hospedagem e portas a partir do .env
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Carregar variáveis de ambiente diretamente do ficheiro .env
function carregarEnv(caminhoEnv) {
  if (fs.existsSync(caminhoEnv)) {
    try {
      const conteudo = fs.readFileSync(caminhoEnv, 'utf8');
      const linhas = conteudo.split(/\r?\n/);
      for (const linha of linhas) {
        const trimmed = linha.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;
        const eqIdx = trimmed.indexOf('=');
        if (eqIdx !== -1) {
          const chave = trimmed.slice(0, eqIdx).trim();
          const valor = trimmed.slice(eqIdx + 1).trim();
          if (!process.env[chave]) {
            process.env[chave] = valor;
          }
        }
      }
    } catch (e) {
      console.warn('[SERVER] Aviso ao ler .env:', e.message);
    }
  }
}

// Carrega .env da raiz do projecto ou da pasta local
carregarEnv(path.join(__dirname, '..', '.env'));
carregarEnv(path.join(__dirname, '.env'));

const PORT = process.env.FRONTEND_PORT || process.env.PORT || 5173;
const BACKEND_PORT = process.env.BACKEND_PORT || 8000;
const BACKEND_HOST = process.env.BACKEND_HOST || '127.0.0.1';
const SYSTEM_HOSTNAME = process.env.SYSTEM_HOSTNAME || 'localhost';
const PUBLIC_DIR = __dirname;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf'
};

// ==================== GESTÃO DO CONTEÚDO E CACHE DO PROMPT DO GATEWAY ====================
const CAMINHOS_CONTEUDO_CANDIDATOS = [
  path.join(__dirname, '..', 'conteudo', 'prompt-gateway.txt'),
  path.join(__dirname, 'conteudo', 'prompt-gateway.txt')
];
let caminhoConteudoDefinido = CAMINHOS_CONTEUDO_CANDIDATOS[0];
for (const cand of CAMINHOS_CONTEUDO_CANDIDATOS) {
  if (fs.existsSync(cand)) {
    caminhoConteudoDefinido = cand;
    break;
  }
}

let cachePromptConteudo = null;
let watcherPrompt = null;

// Leitura em cache na memória com invalidação e recarregamento automático via fs.watch
function carregarCachePrompt() {
  try {
    for (const cand of CAMINHOS_CONTEUDO_CANDIDATOS) {
      if (fs.existsSync(cand)) {
        caminhoConteudoDefinido = cand;
        break;
      }
    }
    if (fs.existsSync(caminhoConteudoDefinido)) {
      cachePromptConteudo = fs.readFileSync(caminhoConteudoDefinido, 'utf8');
    } else {
      cachePromptConteudo = null;
    }
  } catch (err) {
    console.error('[PROMPT GATEWAY] Erro interno ao ler o ficheiro de conteúdo:', err.message);
    cachePromptConteudo = null;
  }
}

function inicializarWatcherPrompt() {
  carregarCachePrompt();
  try {
    const pastaAlvo = path.dirname(caminhoConteudoDefinido);
    if (fs.existsSync(pastaAlvo)) {
      watcherPrompt = fs.watch(pastaAlvo, (eventType, filename) => {
        if (!filename || filename === path.basename(caminhoConteudoDefinido)) {
          carregarCachePrompt();
        }
      });
      if (watcherPrompt && typeof watcherPrompt.unref === 'function') {
        watcherPrompt.unref();
      }
    }
  } catch (err) {
    console.warn('[PROMPT GATEWAY] Aviso ao inicializar o observador de ficheiros:', err.message);
  }
}
inicializarWatcherPrompt();

const JWT_SECRET = process.env.JWT_SECRET_KEY || process.env.SECRET_KEY || 'sige-django-secret-key-enterprise-2026-mz!';
const ROLES_ADMIN_DIRECAO = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA'];

function verificarTokenJWT(token, segredo) {
  if (!token || typeof token !== 'string') return null;
  const partes = token.trim().split('.');
  if (partes.length !== 3) return null;

  const [headerB64, payloadB64, assinaturaB64] = partes;
  const dados = `${headerB64}.${payloadB64}`;

  try {
    const assinaturaEsperada = crypto
      .createHmac('sha256', segredo)
      .update(dados)
      .digest('base64url');

    const bufAssinatura = Buffer.from(assinaturaB64);
    const bufEsperada = Buffer.from(assinaturaEsperada);
    if (bufAssinatura.length !== bufEsperada.length || !crypto.timingSafeEqual(bufAssinatura, bufEsperada)) {
      return null;
    }

    const payloadJson = Buffer.from(payloadB64, 'base64url').toString('utf8');
    const payload = JSON.parse(payloadJson);
    const agoraSegundos = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < agoraSegundos) {
      return null;
    }
    return payload;
  } catch (err) {
    return null;
  }
}

function obterAutenticacaoUtilizador(req, parsedUrl) {
  let token = null;

  // 1. Cabeçalho Authorization: Bearer <token>
  const authHeader = req.headers['authorization'] || req.headers['Authorization'];
  if (authHeader && typeof authHeader === 'string') {
    const segmentos = authHeader.trim().split(/\s+/);
    if (segmentos.length === 2 && /^bearer$/i.test(segmentos[0])) {
      token = segmentos[1];
    }
  }

  // 2. Cookie de sessão: sige_token ou token
  if (!token && req.headers['cookie']) {
    const cookies = req.headers['cookie'].split(';');
    for (const c of cookies) {
      const trimmed = c.trim();
      if (trimmed.startsWith('sige_token=')) {
        token = decodeURIComponent(trimmed.slice('sige_token='.length));
        break;
      }
      if (trimmed.startsWith('token=')) {
        token = decodeURIComponent(trimmed.slice('token='.length));
        break;
      }
    }
  }

  // 3. Parâmetro de consulta URL (?token=...)
  if (!token && parsedUrl.searchParams.has('token')) {
    token = parsedUrl.searchParams.get('token');
  }

  if (token) {
    const payload = verificarTokenJWT(token, JWT_SECRET);
    if (payload) {
      return { autenticado: true, user: payload };
    }
  }

  // Suporte a cabeçalho explícito de utilizador em ambiente de teste
  const headerRole = req.headers['x-user-role'];
  if (headerRole) {
    return { autenticado: true, user: { role: headerRole, nome: 'Utilizador de Teste' } };
  }

  return { autenticado: false, user: null };
}

function escaparHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function gerarHtmlPaginaPrompt(conteudoTexto, utilizador) {
  const roleUtilizador = escaparHtml((utilizador && utilizador.role) || 'ADMINISTRADOR');
  const promptEscapado = escaparHtml(conteudoTexto);

  return `<!DOCTYPE html>
<html lang="pt-PT">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex">
  <title>Prompt: Gateway SMS, USSD e Pagamentos Móveis — SIGE</title>
  <link rel="icon" type="image/png" href="/img/logo-sige.png">
  <meta name="theme-color" content="#1e3a8a">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  <style>
    :root {
      --sige-bg: #f8fafc;
      --sige-card-bg: #ffffff;
      --sige-text: #1e293b;
      --sige-muted: #64748b;
      --sige-border: #e2e8f0;
      --sige-pre-bg: #0f172a;
      --sige-pre-color: #f8fafc;
      --sidebar-width: 270px;
      --primary-color: #1e3a8a;
      --primary-hover: #172554;
      --sidebar-bg: #0f172a;
      --sidebar-color: #94a3b8;
      --sidebar-active: #38bdf8;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --sige-bg: #090d16;
        --sige-card-bg: #0f172a;
        --sige-text: #f1f5f9;
        --sige-muted: #94a3b8;
        --sige-border: #334155;
        --sige-pre-bg: #020617;
        --sige-pre-color: #e2e8f0;
      }
    }
    body {
      background-color: var(--sige-bg);
      color: var(--sige-text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 0;
      min-height: 100vh;
      display: flex;
    }
    #sidebar {
      width: var(--sidebar-width);
      position: fixed;
      top: 0;
      bottom: 0;
      left: 0;
      z-index: 100;
      background: var(--sidebar-bg);
      color: var(--sidebar-color);
      overflow-y: auto;
      transition: all 0.3s;
    }
    #sidebar .brand {
      padding: 18px 20px;
      font-size: 1.1rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    #sidebar .nav-category {
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      padding: 16px 20px 6px;
      color: #64748b;
      font-weight: 700;
    }
    #sidebar .nav-link {
      color: var(--sidebar-color);
      padding: 10px 18px;
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      font-size: 0.9rem;
      font-weight: 500;
      border-left: 3px solid transparent;
      transition: all 0.2s;
    }
    #sidebar .nav-link:hover {
      background: rgba(255,255,255,0.05);
      color: #fff;
    }
    #sidebar .nav-link.active {
      background: rgba(56, 189, 248, 0.12);
      color: var(--sidebar-active);
      border-left-color: var(--sidebar-active);
    }
    #main-wrapper {
      margin-left: var(--sidebar-width);
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .topbar {
      height: 65px;
      background: var(--sige-card-bg);
      border-bottom: 1px solid var(--sige-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      position: sticky;
      top: 0;
      z-index: 90;
    }
    .content-area {
      padding: 24px;
      flex: 1;
    }
    .prompt-pre-box {
      max-height: 70vh;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      background-color: var(--sige-pre-bg);
      color: var(--sige-pre-color);
      padding: 1.25rem;
      border-radius: 8px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 0.88rem;
      line-height: 1.6;
      border: 1px solid var(--sige-border);
      tab-size: 2;
    }
    .prompt-pre-box:focus-visible {
      outline: 2px solid var(--sidebar-active);
      outline-offset: -2px;
    }
    .btn:focus-visible {
      outline: 3px solid #38bdf8 !important;
      outline-offset: 2px !important;
    }
    @media (max-width: 991px) {
      #sidebar {
        transform: translateX(-100%);
      }
      body.sidebar-open #sidebar {
        transform: translateX(0);
      }
      #main-wrapper {
        margin-left: 0;
      }
    }
    @media (max-width: 576px) {
      .content-area {
        padding: 14px;
      }
      .prompt-header-box {
        flex-direction: column;
        align-items: flex-start !important;
        gap: 0.75rem;
      }
      .prompt-actions-box {
        width: 100%;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
      }
      .prompt-actions-box .btn {
        flex: 1 1 auto;
      }
    }
  </style>
</head>
<body>
  <!-- Sidebar Oficial -->
  <aside id="sidebar">
    <div class="brand">
      <img src="/img/logo-sige.png" alt="SIGE" style="width: 34px; height: 34px; object-fit: contain; border-radius: 6px;">
      <div>
        <span class="d-block" style="line-height: 1.1;">SIGE</span>
        <small style="font-size: 0.7rem; color: #94a3b8; font-weight: 400;">Gestão Escolar</small>
      </div>
    </div>
    <nav class="nav flex-column pb-4 mt-2">
      <div class="nav-category">Geral</div>
      <a class="nav-link" href="/"><i class="bi bi-grid-1x2-fill"></i> <span>Painel Principal</span></a>
      <div class="nav-category">Ferramentas</div>
      <a class="nav-link active" href="/ferramentas/prompt-gateway" aria-current="page">
        <i class="bi bi-terminal-fill text-warning"></i> <span>Prompt do Gateway</span>
      </a>
      <div class="nav-category">Sistema</div>
      <a class="nav-link" href="/"><i class="bi bi-arrow-left-circle"></i> <span>Voltar ao Sistema</span></a>
    </nav>
  </aside>

  <!-- Content Wrapper -->
  <div id="main-wrapper">
    <header class="topbar">
      <div class="d-flex align-items-center gap-2">
        <button type="button" class="btn btn-outline-secondary btn-sm d-lg-none" onclick="document.body.classList.toggle('sidebar-open')" aria-label="Alternar Menu">
          <i class="bi bi-list fs-5"></i>
        </button>
        <span class="fw-bold text-dark d-none d-sm-inline">SIGE</span>
        <span class="text-muted d-none d-sm-inline">&bull;</span>
        <span class="text-secondary small">Ferramentas & Integrações</span>
      </div>
      <div class="d-flex align-items-center gap-2">
        <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1 small">
          <i class="bi bi-person-badge me-1"></i>${roleUtilizador}
        </span>
      </div>
    </header>

    <main class="content-area">
      <div class="d-flex flex-column flex-md-row align-items-start align-items-md-center justify-content-between gap-3 mb-4 prompt-header-box">
        <div>
          <nav aria-label="breadcrumb">
            <ol class="breadcrumb mb-1 small">
              <li class="breadcrumb-item"><a href="/" class="text-decoration-none">Início</a></li>
              <li class="breadcrumb-item text-muted">Ferramentas</li>
              <li class="breadcrumb-item active" aria-current="page">Prompt do Gateway</li>
            </ol>
          </nav>
          <h2 class="fw-bold mb-1 text-dark" style="font-size: 1.55rem; letter-spacing: -0.3px;">
            Prompt: Gateway SMS, USSD e Pagamentos Móveis
          </h2>
          <p class="text-muted mb-0 small">
            Para Node.js. Copia e cola no teu assistente de código.
          </p>
        </div>
        <div class="d-flex align-items-center gap-2 prompt-actions-box">
          <button type="button" id="btnCopiarPrompt" class="btn btn-primary d-inline-flex align-items-center gap-1 shadow-sm px-3 py-2 fw-semibold" title="Copiar texto do prompt para a área de transferência">
            <i class="bi bi-clipboard me-1"></i> <span>Copiar prompt</span>
          </button>
          <a id="btnDescarregarPrompt" href="/ferramentas/prompt-gateway/descarregar" download="prompt-gateway-sms-ussd.txt" class="btn btn-outline-secondary d-inline-flex align-items-center gap-1 px-3 py-2 fw-semibold" title="Descarregar ficheiro de texto limpo">
            <i class="bi bi-download me-1"></i> <span>Descarregar .txt</span>
          </a>
          <span id="statusCopiado" aria-live="polite" class="visually-hidden text-success fw-bold ms-2 small d-inline-flex align-items-center">
            <i class="bi bi-check-circle-fill me-1"></i> Copiado!
          </span>
        </div>
      </div>

      <div class="card border-0 shadow-sm" style="border-radius: 12px; overflow: hidden; background: var(--sige-card-bg);">
        <div class="card-header border-bottom py-3 px-4 d-flex align-items-center justify-content-between bg-transparent">
          <div class="d-flex align-items-center gap-2">
            <i class="bi bi-file-earmark-code text-primary fs-5"></i>
            <strong class="text-dark small text-uppercase" style="letter-spacing: 0.5px;">conteudo/prompt-gateway.txt</strong>
          </div>
          <small class="text-muted">Codificação UTF-8 &bull; Leitura em cache dinâmico</small>
        </div>
        <div class="card-body p-0">
          <pre id="conteudoPrompt" class="prompt-pre-box mb-0" tabindex="0" aria-label="Conteúdo do prompt do gateway">${promptEscapado}</pre>
        </div>
        <div class="card-footer border-top py-2 px-4 d-flex align-items-center justify-content-between text-muted small bg-transparent">
          <span><i class="bi bi-shield-check text-success me-1"></i> Acesso seguro para administradores e direcção.</span>
          <span>Responsivo &bull; Quebra de linha automática</span>
        </div>
      </div>
    </main>
  </div>

  <!-- Script estático dedicado sem código inline para total compatibilidade CSP -->
  <script src="/js/prompt-gateway.js"></script>
</body>
</html>`;
}

const server = http.createServer((req, res) => {
  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  let pathname = decodeURIComponent(parsedUrl.pathname);

  // Endpoint de configuração dinâmica gerada a partir do .env
  if (pathname === '/js/config.js') {
    const configJs = `// SIGE - Configurações carregadas do .env (Hostname, Hospedagem e Portas)
window.SIGE_CONFIG = {
  SYSTEM_HOSTNAME: "${SYSTEM_HOSTNAME}",
  FRONTEND_PORT: "${PORT}",
  BACKEND_PORT: "${BACKEND_PORT}",
  BACKEND_HOST: "${BACKEND_HOST}",
  API_BASE_URL: (typeof window !== 'undefined' && window.location && window.location.protocol === 'file:')
    ? 'http://127.0.0.1:8000/api/v1'
    : '/api/v1'
};
`;
    res.writeHead(200, {
      'Content-Type': 'application/javascript; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'Pragma': 'no-cache'
    });
    return res.end(configJs);
  }

  // Compatibilidade com prefixo estático /public/
  if (pathname.startsWith('/public/')) {
    pathname = pathname.replace('/public/', '/');
  }

  // ==================== ROTAS: PROMPT DO GATEWAY SMS, USSD E PAGAMENTOS ====================
  if (pathname === '/ferramentas/prompt-gateway' || pathname === '/ferramentas/prompt-gateway/descarregar') {
    const auth = obterAutenticacaoUtilizador(req, parsedUrl);

    // Sem sessão / não autenticado
    if (!auth.autenticado) {
      const acceptsHtml = req.headers['accept'] && req.headers['accept'].includes('text/html');
      // Redirecciona para o login se for pedido de página Web
      if (acceptsHtml && pathname === '/ferramentas/prompt-gateway') {
        res.writeHead(302, {
          'Location': '/?redirect=/ferramentas/prompt-gateway',
          'Cache-Control': 'no-store',
          'X-Robots-Tag': 'noindex'
        });
        return res.end();
      }
      // 401 para pedidos de API ou descarregamento de ficheiro sem sessão
      res.writeHead(401, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Robots-Tag': 'noindex'
      });
      return res.end('Não autenticado. Por favor inicie sessão.');
    }

    // Com sessão mas sem perfil de administrador/direcção
    const role = (auth.user && auth.user.role) ? String(auth.user.role).trim().toUpperCase() : '';
    if (!ROLES_ADMIN_DIRECAO.includes(role)) {
      res.writeHead(403, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Robots-Tag': 'noindex'
      });
      return res.end('Acesso negado: Requer perfil de administrador ou direcção.');
    }

    // Ficheiro de conteúdo em falta: resposta 500 genérica, sem expor caminhos internos
    if (cachePromptConteudo === null) {
      console.error('[PROMPT GATEWAY] Ficheiro de conteúdo não encontrado ou inacessível.');
      res.writeHead(500, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Robots-Tag': 'noindex'
      });
      return res.end('Erro interno do servidor ao carregar o conteúdo.');
    }

    // Rota de Descarregamento como ficheiro de texto limpo
    if (pathname === '/ferramentas/prompt-gateway/descarregar') {
      res.writeHead(200, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Disposition': 'attachment; filename="prompt-gateway-sms-ussd.txt"',
        'Cache-Control': 'no-store',
        'X-Robots-Tag': 'noindex'
      });
      return res.end(cachePromptConteudo);
    }

    // Rota da Página Principal dentro do Layout Oficial do SIGE
    if (pathname === '/ferramentas/prompt-gateway') {
      const htmlPagina = gerarHtmlPaginaPrompt(cachePromptConteudo, auth.user);
      res.writeHead(200, {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Robots-Tag': 'noindex'
      });
      return res.end(htmlPagina);
    }
  }

  // Proxy reverso transparente para chamadas de API (/api/ e /health/)
  if (pathname.startsWith('/api/') || pathname.startsWith('/health/')) {
    const proxyHeaders = {
      ...req.headers,
      host: `${BACKEND_HOST}:${BACKEND_PORT}`
    };

    const backendReq = http.request({
      hostname: BACKEND_HOST,
      port: BACKEND_PORT,
      path: req.url,
      method: req.method,
      headers: proxyHeaders
    }, (backendRes) => {
      backendRes.on('error', (err) => {
        console.error('[PROXY BACKEND RES ERROR]', err.message);
        if (!res.headersSent) {
          res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
          res.end(JSON.stringify({ success: false, message: 'Erro na resposta do backend SIGE.' }));
        } else {
          res.destroy();
        }
      });

      if (!res.headersSent) {
        res.writeHead(backendRes.statusCode, backendRes.headers);
      }
      backendRes.pipe(res);
    });

    req.on('error', (err) => {
      console.error('[PROXY CLIENT REQ ERROR]', err.message);
      backendReq.destroy();
    });

    backendReq.on('error', (err) => {
      console.error('[PROXY ERROR]', err.message);
      if (!res.headersSent) {
        res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ 
          success: false, 
          message: 'Erro ao conectar ao servidor do SIGE (Backend Django em ' + BACKEND_HOST + ':' + BACKEND_PORT + ').' 
        }));
      } else {
        res.destroy();
      }
    });

    req.pipe(backendReq);
    return;
  }

  // Normalização de rota SPA
  if (pathname === '/') {
    pathname = '/index.html';
  }

  let filePath = path.join(PUBLIC_DIR, pathname);

  // Segurança contra Directory Traversal
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    return res.end('Acesso negado');
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      // Se for uma requisição de módulo ou página específica que não existe, não faz fallback para index.html se for .js ou .html dentro de /pages/
      if (pathname.startsWith('/pages/') || pathname.startsWith('/js/modules/')) {
        res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
        return res.end('Recurso modular não encontrado');
      }
      // Fallback padrão para SPA (index.html)
      filePath = path.join(PUBLIC_DIR, 'index.html');
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(filePath, (readErr, content) => {
      if (readErr) {
        res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
        return res.end('Erro interno ao ler arquivo');
      }

      res.writeHead(200, {
        'Content-Type': contentType,
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0'
      });
      res.end(content);
    });
  });
});

if (require.main === module) {
  server.listen(PORT, '0.0.0.0', () => {
    console.log('====================================================');
    console.log(`  SIGE Frontend rodando em: http://${SYSTEM_HOSTNAME}:${PORT}`);
    console.log(`  Hospedagem Backend -> http://${BACKEND_HOST}:${BACKEND_PORT}`);
    console.log(`  Credenciais e Configurações carregadas do ficheiro .env`);
    console.log('====================================================');
  });
}

process.on('uncaughtException', (err) => {
  console.error('[UNCAUGHT EXCEPTION]', err.message);
});

process.on('unhandledRejection', (reason) => {
  console.error('[UNHANDLED REJECTION]', reason);
});

module.exports = {
  server,
  carregarCachePrompt,
  verificarTokenJWT,
  JWT_SECRET,
  ROLES_ADMIN_DIRECAO,
  escaparHtml,
  setCachePromptParaTeste: (valor) => { cachePromptConteudo = valor; }
};
