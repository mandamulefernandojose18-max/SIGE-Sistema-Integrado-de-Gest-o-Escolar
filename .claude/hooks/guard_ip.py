"""PreToolUse (Write|Edit): bloqueia IPv4 literal (regra inquebravel n.1 do CLAUDE.md)."""
import json
import re
import sys

PERMITIDOS = {"127.0.0.1", "0.0.0.0", "255.255.255.255", "255.255.255.0"}
IPV4 = re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])")


def main():
    dados = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    entrada = dados.get("tool_input", {})
    caminho = (entrada.get("file_path") or "").replace("\\", "/")
    if "/.claude/" in caminho or caminho.endswith(("package-lock.json", ".lock")):
        return 0
    texto = entrada.get("content") or entrada.get("new_string") or ""
    achados = sorted({ip for ip in IPV4.findall(texto) if ip not in PERMITIDOS})
    if achados:
        print(
            "BLOQUEADO: endereco IP detectado (" + ", ".join(achados) + "). "
            "O CLAUDE.md proibe expor IPs; usa https://sigesaas.duckdns.org/ .",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
