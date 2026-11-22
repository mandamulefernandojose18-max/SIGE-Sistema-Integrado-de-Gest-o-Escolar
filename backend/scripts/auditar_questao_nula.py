"""Auditoria do erro grave «Questão nula» (ver .claude/skills/controlo-questao-nula). Uso: python scripts/auditar_questao_nula.py <pdf>"""
import os
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django  # noqa: E402

django.setup()
from apps.notas import omr_servico as omr  # noqa: E402

FORTE = omr.LIMIAR_FRACA


def main(caminho, n=40, n_alt=4):
    dados = open(caminho, 'rb').read()
    total = omr.contar_paginas(dados)
    capturado = {}
    original = omr.decidir

    def espiar(scores, letras):
        capturado['s'] = scores
        return original(scores, letras)
    omr.decidir = espiar
    suspeitas = 0
    for i in range(total):
        img, orig, erro = omr.abrir_lote(dados, [i])[0]
        if img is None:
            print(f'pág. {i + 1}: {erro}')
            continue
        try:
            r = omr.ler_pagina(img, n, n_alt, procurar_qr=False, fonte=orig, com_imagens=False)
        except omr.ErroOMR as e:
            print(f'pág. {i + 1}: não lida ({str(e)[:60]})')
            continue
        for q, ch in enumerate(r['respostas'], start=1):
            if ch not in 'N-':
                continue
            s = capturado['s'][q - 1]
            fortes = sum(1 for x in s if x >= FORTE)
            ok = (ch == 'N' and fortes >= 2) or (ch == '-' and max(s) < FORTE)
            print(f'pág. {i + 1:2d} P{q:02d} {ch} {[round(x, 2) for x in s]} {"ok" if ok else "SUSPEITA"}')
            suspeitas += 0 if ok else 1
    print(f'\nSUSPEITAS: {suspeitas}')
    return 1 if suspeitas else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))