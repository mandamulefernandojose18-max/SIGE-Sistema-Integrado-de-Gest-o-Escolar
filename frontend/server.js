/**
 * SIGE Front-End - Servidor de Desenvolvimento e Produção SPA
 * Servidor HTTP nativo e autônomo com Proxy Reverso para API Backend
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 5173;
const BACKEND_PORT = process.env.BACKEND_PORT || 8000;
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

  // Proxy reverso transparente para chamadas de API (/api/ e /health/)
  if (pathname.startsWith('/api/') || pathname.startsWith('/health/')) {
    const proxyHeaders = {
      ...req.headers,
      host: `127.0.0.1:${BACKEND_PORT}`
    };

    const backendReq = http.request({
      hostname: '127.0.0.1',
      port: BACKEND_PORT,
      path: req.url,
      method: req.method,
      headers: proxyHeaders
    }, (backendRes) => {
      res.writeHead(backendRes.statusCode, backendRes.headers);
      backendRes.pipe(res);
    });

    backendReq.on('error', (err) => {
      console.error('[PROXY ERROR]', err.message);
      res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ 
        success: false, 
        message: 'Erro ao conectar ao servidor do SIGE (Backend Django na porta ' + BACKEND_PORT + ').' 
      }));
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
      // Fallback para SPA (index.html)
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
        'Access-Control-Allow-Origin': '*'
      });
      res.end(content);
    });
  });
});

server.listen(PORT, () => {
  console.log('====================================================');
  console.log(`  SIGE Frontend SPA rodando em: http://localhost:${PORT}`);
  console.log(`  Proxy Reverso API ativado -> http://127.0.0.1:${BACKEND_PORT}`);
  console.log('====================================================');
});
