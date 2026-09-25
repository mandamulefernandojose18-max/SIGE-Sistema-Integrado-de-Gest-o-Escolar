"""
Instalador do Git Hook de Atualização Automática de Documentação no Backend.
"""
from pathlib import Path
import os
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
GIT_DIR = BASE_DIR / '.git' if (BASE_DIR / '.git').exists() else (BASE_DIR.parent / '.git')
HOOKS_DIR = GIT_DIR / 'hooks'

HOOK_CONTENT = """#!/bin/sh
# Git Hook: Atualização automática de documentação do Backend SIGE
echo "[HOOK] Verificando alteracoes em modelos, rotas ou configuracoes..."

CHANGED_FILES=$(git diff --cached --name-only | grep -E '^(apps/|config/|common/)')

if [ -n "$CHANGED_FILES" ]; then
    echo "[HOOK] Mudancas detectadas no codigo-fonte. Atualizando documentacao..."
    if [ -f "./venv/Scripts/python.exe" ]; then
        ./venv/Scripts/python.exe scripts/update_docs.py
    elif command -v python >/dev/null 2>&1; then
        python scripts/update_docs.py
    elif command -v py >/dev/null 2>&1; then
        py scripts/update_docs.py
    elif command -v python3 >/dev/null 2>&1; then
        python3 scripts/update_docs.py
    fi
    git add docs/ schema.yml
    echo "[HOOK] Documentacao sincronizada e adicionada ao commit!"
fi

exit 0
"""

def install_hook():
    if not GIT_DIR.exists():
        print("[ERRO] Diretorio .git nao encontrado no backend.")
        return False

    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    hook_file = HOOKS_DIR / 'pre-commit'
    hook_file.write_text(HOOK_CONTENT, encoding='utf-8')
    
    # Tornar executável no Unix
    try:
        os.chmod(hook_file, 0o755)
    except Exception:
        pass

    print(f"[SUCESSO] Git Pre-Commit Hook instalado em: {hook_file}")
    return True

if __name__ == '__main__':
    install_hook()
