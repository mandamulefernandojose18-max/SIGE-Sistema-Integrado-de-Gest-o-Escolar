"""Stop: avisa se codigo mudou sem actualizar docs/ (regra n.5 do CLAUDE.md). Nao bloqueia."""
import json
import subprocess
import sys


def main():
    try:
        saida = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                               text=True, timeout=20).stdout
    except Exception:
        return 0
    ficheiros = [l[3:].strip().replace("\\", "/") for l in saida.splitlines() if len(l) > 3]
    codigo = [f for f in ficheiros if f.startswith(("backend/apps/", "backend/common/", "frontend/js/", "frontend/pages/"))]
    docs = [f for f in ficheiros if f.startswith("docs/") or f == "README.md"]
    if codigo and not docs:
        print(json.dumps({"systemMessage": "Lembrete: ha alteracoes de codigo sem actualizacao em docs/ "
                          "(usa /sync-docs antes do commit/deploy)."}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
