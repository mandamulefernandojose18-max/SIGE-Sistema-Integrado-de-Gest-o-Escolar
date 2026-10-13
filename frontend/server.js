/**
 * SIGE Front-End - Servidor de Desenvolvimento e Produção SPA
 * Servidor HTTP nativo e autônomo com Proxy Reverso para API Backend
 * Lê todas as credenciais, hostname, hospedagem e portas a partir do .env
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

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

server.listen(PORT, '0.0.0.0', () => {
  console.log('====================================================');
  console.log(`  SIGE Frontend rodando em: http://${SYSTEM_HOSTNAME}:${PORT}`);
  console.log(`  Hospedagem Backend -> http://${BACKEND_HOST}:${BACKEND_PORT}`);
  console.log(`  Credenciais e Configurações carregadas do ficheiro .env`);
  console.log('====================================================');
});

process.on('uncaughtException', (err) => {
  console.error('[UNCAUGHT EXCEPTION]', err.message);
});

process.on('unhandledRejection', (reason) => {
  console.error('[UNHANDLED REJECTION]', reason);
});
