/**
 * Script de Geração e Atualização Automática de Documentação — SIGE Frontend (SPA)
 * Analisa index.html e js/app.js para extrair páginas, módulos, rotas e chamadas de API.
 */
const fs = require('fs');
const path = require('path');

const FRONTEND_DIR = path.resolve(__dirname, '..');
const INDEX_HTML_PATH = path.join(FRONTEND_DIR, 'index.html');
const APP_JS_PATH = path.join(FRONTEND_DIR, 'js', 'app.js');
const DOCS_DIR = path.join(FRONTEND_DIR, 'docs');

function extractViewsFromHTML(htmlContent) {
    const views = [];
    // Busca por seções ou divs com id contendo 'view' ou 'section'
    const sectionRegex = /<section[^>]*id=["']([^"']+)["'][^>]*>([\s\S]*?)<\/section>/gi;
    let match;

    while ((match = sectionRegex.exec(htmlContent)) !== null) {
        const id = match[1];
        const content = match[2];

        // Título da página
        const titleMatch = content.match(/<h[1-4][^>]*>([^<]+)<\/h[1-4]>/i);
        const title = titleMatch ? titleMatch[1].trim() : id.replace(/[-_]/g, ' ');

        // Formulários e tabelas
        const hasForm = /<form/i.test(content);
        const hasTable = /<table/i.test(content);
        const buttons = [];
        const btnRegex = /<button[^>]*class=["']([^"']*)["'][^>]*>([\s\S]*?)<\/button>/gi;
        let btnMatch;
        while ((btnMatch = btnRegex.exec(content)) !== null) {
            const label = btnMatch[2].replace(/<[^>]+>/g, '').trim();
            if (label && !buttons.includes(label)) {
                buttons.push(label);
            }
        }

        views.push({
            id,
            title,
            hasForm,
            hasTable,
            buttons: buttons.slice(0, 5)
        });
    }

    // Se nenhuma section com id foi capturada, busca divs principais com id
    if (views.length === 0) {
        const divRegex = /<div[^>]*id=["'](view-[^"']+|page-[^"']+|tab-[^"']+)["'][^>]*>/gi;
        while ((match = divRegex.exec(htmlContent)) !== null) {
            views.push({
                id: match[1],
                title: match[1].replace(/[-_]/g, ' '),
                hasForm: false,
                hasTable: false,
                buttons: []
            });
        }
    }

    return views;
}

function extractAPICallsFromJS(jsContent) {
    const apiCalls = new Set();
    // Procura chamadas apiFetch('/api/v1/...') ou `...`
    const fetchRegex = /apiFetch\(\s*[`'"]([^`'"]+)[`'"]/g;
    let match;
    while ((match = fetchRegex.exec(jsContent)) !== null) {
        apiCalls.add(match[1]);
    }
    return Array.from(apiCalls).sort();
}

function extractControllerFunctions(jsContent) {
    const functions = [];
    const funcRegex = /function\s+([a-zA-Z0-9_]+)\s*\(/g;
    let match;
    while ((match = funcRegex.exec(jsContent)) !== null) {
        const name = match[1];
        if (name.startsWith('carregar') || name.startsWith('render') || name.startsWith('salvar') || name.startsWith('abrir') || name.startsWith('emitir')) {
            functions.push(name);
        }
    }
    return functions;
}

function generateDocumentation() {
    console.log('[DOCS] Analisando index.html e js/app.js do Frontend...');

    const htmlContent = fs.readFileSync(INDEX_HTML_PATH, 'utf-8');
    const jsContent = fs.readFileSync(APP_JS_PATH, 'utf-8');

    const views = extractViewsFromHTML(htmlContent);
    const apiCalls = extractAPICallsFromJS(jsContent);
    const functions = extractControllerFunctions(jsContent);

    let doc = `# Catálogo de Telas e Módulos — SIGE Frontend (SPA)\n\n`;
    doc += `> Documento gerado automaticamente via introspecção do \`index.html\` e \`js/app.js\`.\n\n`;
    doc += `**Total de Telas / Visões Detectadas:** ${views.length}\n`;
    doc += `**Total de Chamadas a Endpoints:** ${apiCalls.length}\n\n---\n\n`;

    doc += `## 1. Módulos e Telas da Interface\n\n`;
    doc += `| Identificador (ID) | Título da Página | Componentes Detectados | Ações Principais |\n`;
    doc += `| :--- | :--- | :---: | :--- |\n`;

    views.forEach(v => {
        const comps = [];
        if (v.hasTable) comps.push('Tabela');
        if (v.hasForm) comps.push('Formulário');
        const compsStr = comps.length > 0 ? comps.join(', ') : 'Painel / Visual';
        const btnsStr = v.buttons.length > 0 ? v.buttons.join(', ') : 'Navegação';
        doc += `| \`${v.id}\` | **${v.title}** | ${compsStr} | ${btnsStr} |\n`;
    });

    doc += `\n---\n\n## 2. Endpoints do Backend Consumidos no Código-Fonte\n\n`;
    doc += `| Rota da API Backend | Módulo de Destino Estimado |\n`;
    doc += `| :--- | :--- |\n`;
    apiCalls.forEach(call => {
        let modulo = 'Geral';
        if (call.includes('auth')) modulo = 'Autenticação';
        else if (call.includes('turma')) modulo = 'Turmas';
        else if (call.includes('aluno')) modulo = 'Alunos';
        else if (call.includes('professor')) modulo = 'Professores';
        else if (call.includes('nota') || call.includes('caderneta')) modulo = 'Notas e Avaliações';
        else if (call.includes('pauta')) modulo = 'Pautas e Atas';
        else if (call.includes('material')) modulo = 'Material Escolar';
        else if (call.includes('pagamento')) modulo = 'Financeiro / Pagamentos';
        else if (call.includes('certificado')) modulo = 'Certificados';
        else if (call.includes('saas') || call.includes('escola')) modulo = 'Administração SaaS';
        doc += `| \`${call}\` | **${modulo}** |\n`;
    });

    doc += `\n---\n\n## 3. Funções Controladoras de Interface Identificadas\n\n`;
    doc += `Foram detectadas **${functions.length}** funções essenciais de carregamento e manipulação de estado:\n\n`;
    functions.slice(0, 40).forEach(f => {
        doc += `- \`${f}()\`\n`;
    });
    if (functions.length > 40) {
        doc += `- *... e mais ${functions.length - 40} funções auxiliares.*\n`;
    }

    if (!fs.existsSync(DOCS_DIR)) {
        fs.mkdirSync(DOCS_DIR, { recursive: true });
    }

    const targetFile = path.join(DOCS_DIR, 'PAGES_AND_MODULES.md');
    fs.writeFileSync(targetFile, doc, 'utf-8');
    console.log(`[OK] Catálogo de telas e módulos gerado em: ${targetFile}`);
}

if (require.main === module) {
    generateDocumentation();
}

module.exports = { generateDocumentation };
