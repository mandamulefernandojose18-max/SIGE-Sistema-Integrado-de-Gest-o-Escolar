"""PostToolUse (Write|Edit): corre `manage.py check` apos editar Python do backend."""
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(RAIZ, "backend")


def main():
    dados = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    caminho = (dados.get("tool_input", {}).get("file_path") or "").replace("\\", "/")
    if not caminho.endswith(".py") or "/backend/" not in caminho or "/venv/" in caminho:
        return 0
    py = os.path.join(BACKEND, "venv", "Scripts", "python.exe")
    if not os.path.exists(py):
        py = sys.executable
    env = dict(os.environ, DJANGO_SETTINGS_MODULE="config.settings.development")
    try:
        r = subprocess.run([py, "manage.py", "check"], cwd=BACKEND, env=env,
                           capture_output=True, text=True, timeout=90)
    except Exception as exc:
        print(f"django check nao executou: {exc}", file=sys.stderr)
        return 0
    if r.returncode != 0:
        print("manage.py check falhou:\n" + (r.stderr or r.stdout)[-1500:], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
