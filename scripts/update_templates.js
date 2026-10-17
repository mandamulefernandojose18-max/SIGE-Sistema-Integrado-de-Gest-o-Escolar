const fs = require('fs');
const path = require('path');

const superHtmlPath = path.join(__dirname, '..', 'frontend', 'pages', 'painel-superadmin', 'pagamentos-saas.html');
const escolaHtmlPath = path.join(__dirname, '..', 'frontend', 'pages', 'painel-escola', 'assinatura-escola.html');
const templatesPath = path.join(__dirname, '..', 'frontend', 'js', 'templates.js');

if (fs.existsSync(superHtmlPath) && fs.existsSync(escolaHtmlPath) && fs.existsSync(templatesPath)) {
  const pSuper = fs.readFileSync(superHtmlPath, 'utf8');
  const pEscola = fs.readFileSync(escolaHtmlPath, 'utf8');
  let tpl = fs.readFileSync(templatesPath, 'utf8');

  // Remove existing keys if already present
  if (tpl.includes('"painel-superadmin/pagamentos-saas"')) {
    console.log('Template already present, skipping.');
    process.exit(0);
  }

  const idx = tpl.lastIndexOf('};');
  if (idx !== -1) {
    const injection = ',\n  "painel-superadmin/pagamentos-saas": ' + JSON.stringify(pSuper) + ',\n  "painel-escola/assinatura-escola": ' + JSON.stringify(pEscola) + '\n';
    tpl = tpl.slice(0, idx) + injection + tpl.slice(idx);
    fs.writeFileSync(templatesPath, tpl, 'utf8');
    console.log('TEMPLATES INJECTED SUCCESSFULLY');
  }
}
