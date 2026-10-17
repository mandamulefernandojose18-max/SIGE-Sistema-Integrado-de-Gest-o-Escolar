const fs = require('fs');
const path = require('path');

const pagesDir = path.join(__dirname, '..', 'frontend', 'pages');
const tplPath = path.join(__dirname, '..', 'frontend', 'js', 'templates.js');

const templates = {};

function scanDir(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      scanDir(fullPath);
    } else if (entry.isFile() && entry.name.endsWith('.html')) {
      const rel = path.relative(pagesDir, fullPath).replace(/\\/g, '/').replace(/\.html$/, '');
      const content = fs.readFileSync(fullPath, 'utf8');
      templates[rel] = content;
    }
  }
}

scanDir(pagesDir);

const jsContent = `// Repositório de Modelos e Fallback Modular de Páginas
// Permite renderização imediata sem latência e suporte offline
window.SIGE_TEMPLATES = ${JSON.stringify(templates, null, 2)};
`;

fs.writeFileSync(tplPath, jsContent, 'utf8');
console.log(`SINCRONIZADOS ${Object.keys(templates).length} TEMPLATES COM SUCESSO!`);
