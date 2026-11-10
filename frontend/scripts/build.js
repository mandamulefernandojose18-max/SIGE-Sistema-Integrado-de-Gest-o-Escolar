// SIGE — Build do frontend: copia o site para dist/ e minifica todo o JavaScript proprio.
// Uso: npm run build   (o Nginx de producao serve frontend/dist)
// O codigo-fonte em js/ mantem-se legivel para desenvolvimento; so o dist/ e minificado
// (sem comentarios, sem source maps, identificadores locais encurtados).
// Nomes globais de topo (funcoes usadas em onclick="...") sao preservados: transform sem bundle.
const fs = require('fs');
const path = require('path');
const esbuild = require('esbuild');

const ROOT = path.join(__dirname, '..');
const DIST = path.join(ROOT, 'dist');

const EXCLUIR_RAIZ = new Set([
  'node_modules', 'dist', 'tests', 'scripts', 'docs', '.github',
  'Dockerfile', 'package.json', 'package-lock.json', 'README.md', 'CLAUDE.md',
  'server.js', 'vercel.json', 'nginx.conf', '.dockerignore',
]);
// templates.js: repositorio legado de paginas, ja nao e usado (as paginas carregam de /pages/ por painel).
const EXCLUIR_CAMINHOS = new Set(['js/templates.js']);

let totalAntes = 0;
let totalDepois = 0;
let ficheirosJs = 0;

function jaMinificado(rel) {
  return /\.min\.js$/.test(rel) || rel.startsWith('js/libs/') || /\.bundle\.js$/.test(rel) || /\.iife\.js$/.test(rel) || /\.umd\.js$/.test(rel);
}

function copiar(srcDir, rel) {
  const dir = path.join(srcDir, rel);
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const relPath = (rel ? rel + '/' : '') + ent.name;
    if (!rel && EXCLUIR_RAIZ.has(ent.name)) continue;
    if (EXCLUIR_CAMINHOS.has(relPath)) continue;
    const src = path.join(ROOT, relPath);
    const dst = path.join(DIST, relPath);
    if (ent.isDirectory()) {
      fs.mkdirSync(dst, { recursive: true });
      copiar(srcDir, relPath);
    } else if (ent.name.endsWith('.js') && !jaMinificado(relPath)) {
      const codigo = fs.readFileSync(src, 'utf8');
      const out = esbuild.transformSync(codigo, {
        minify: true,
        legalComments: 'none',
        charset: 'utf8',
        target: 'es2019',
        sourcemap: false,
      }).code;
      fs.writeFileSync(dst, out, 'utf8');
      totalAntes += Buffer.byteLength(codigo);
      totalDepois += Buffer.byteLength(out);
      ficheirosJs++;
    } else {
      fs.copyFileSync(src, dst);
    }
  }
}

fs.rmSync(DIST, { recursive: true, force: true });
fs.mkdirSync(DIST, { recursive: true });
copiar(ROOT, '');
const kb = (n) => Math.round(n / 1024);
console.log(`BUILD OK: ${ficheirosJs} ficheiros JS minificados (${kb(totalAntes)} KB -> ${kb(totalDepois)} KB) em ${DIST}`);
