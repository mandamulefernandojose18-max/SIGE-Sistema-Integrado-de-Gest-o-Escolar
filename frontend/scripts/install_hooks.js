/**
 * Instalador do Git Hook de Atualização Automática de Documentação no Frontend.
 */
const fs = require('fs');
const path = require('path');

const FRONTEND_DIR = path.resolve(__dirname, '..');
const GIT_DIR = fs.existsSync(path.join(FRONTEND_DIR, '.git')) ? path.join(FRONTEND_DIR, '.git') : path.join(FRONTEND_DIR, '..', '.git');
const HOOKS_DIR = path.join(GIT_DIR, 'hooks');

const HOOK_CONTENT = `#!/bin/sh
# Git Hook: Atualização automática de documentação do Frontend SIGE
echo "[HOOK] Verificando alteracoes em telas, componentes ou scripts do Frontend..."

CHANGED_FILES=$(git diff --cached --name-only | grep -E '^(index\\.html|js/|css/)')

if [ -n "$CHANGED_FILES" ]; then
    echo "[HOOK] Telas ou scripts modificados. Atualizando catalogo de documentacao..."
    if command -v node >/dev/null 2>&1; then
        node scripts/update_docs.js
    fi
    git add docs/
    echo "[HOOK] Documentacao do Frontend sincronizada e adicionada ao commit!"
fi

exit 0
`;

function installHook() {
    if (!fs.existsSync(GIT_DIR)) {
        console.error('[ERRO] Diretório .git não encontrado no frontend.');
        return false;
    }

    if (!fs.existsSync(HOOKS_DIR)) {
        fs.mkdirSync(HOOKS_DIR, { recursive: true });
    }

    const hookFile = path.join(HOOKS_DIR, 'pre-commit');
    fs.writeFileSync(hookFile, HOOK_CONTENT, { encoding: 'utf-8', mode: 0o755 });

    console.log(`[SUCESSO] Git Pre-Commit Hook instalado em: ${hookFile}`);
    return true;
}

if (require.main === module) {
    installHook();
}

module.exports = { installHook };
