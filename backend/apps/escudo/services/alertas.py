"""Aviso ao dono da prova quando alguém lê um código (QR ou barras) durante o embargo.

O que se capta: a hora, o código da cópia (e a pergunta/página), o tipo de aparelho e uma impressão (hash) da rede, nunca o IP.
O local só existe se quem leu autorizar a localização no navegador (o pedido é do próprio navegador, com aviso visível na página).
O aviso segue por e-mail (SMTP do servidor). Para não encher a caixa, no máximo um e-mail por prova a cada JANELA_S, a juntar as leituras.
"""
import os
import threading
import time
from datetime import timedelta

from django.core.mail import send_mail
from django.utils import timezone

from ..models import LeituraEscudo
from . import tempo

JANELA_S = 300
ATRASO_S = 25   # espera pelo local, que chega logo depois da leitura se a pessoa autorizar


def email_activo():
    return bool((os.environ.get("EMAIL_HOST") or "").strip())


def email_da_conta(prova_codigo):
    from ..models import ProvaEscudo
    p = ProvaEscudo.objects.select_related("criado_por").filter(codigo=prova_codigo).first()
    return getattr(p.criado_por, "email", "") if p and p.criado_por_id else ""


def _linha(l):
    quando = tempo.formatar(l.quando)
    cod = f"{l.prova.codigo}-{l.serial:03d}" if l.serial else l.prova.codigo
    est = "código não reconhecido" if l.estado == "invalida" else "durante o embargo"
    if l.latitude is not None:
        mapa = f"https://www.openstreetmap.org/?mlat={l.latitude}&mlon={l.longitude}#map=17/{l.latitude}/{l.longitude}"
        onde = f"local (±{l.precisao_m or '?'} m): {mapa}"
    else:
        onde = "local: não disponível (quem leu não autorizou a localização)"
    return (f"- {quando} (Maputo) · cópia {cod} · {est}\n"
            f"  aparelho: {l.aparelho or 'desconhecido'} · rede (impressão): {l.rede or '—'}\n  {onde}")


def enviar_aviso(prova_codigo):
    """Envia (se houver o que avisar e a janela o permitir). Devolve nº de leituras avisadas, 0 se não havia, -1 se adiado."""
    from ..models import ProvaEscudo
    if not email_activo():
        return 0
    prova = ProvaEscudo.objects.select_related("criado_por").filter(codigo=prova_codigo).first()
    if not prova or not (prova.config or {}).get("notificar_leituras", True):
        return 0
    destino = (prova.config or {}).get("email_avisos") or (getattr(prova.criado_por, "email", "") if prova.criado_por_id else "")
    pendentes = list(LeituraEscudo.objects.filter(prova=prova, notificada=False).exclude(estado="libertada").order_by("quando"))
    if not destino or not pendentes:
        return 0
    recente = LeituraEscudo.objects.filter(prova=prova, notificada=True, quando__gte=timezone.now() - timedelta(seconds=JANELA_S)).exists()
    if recente:
        return -1
    corpo = (f"Alguém leu o código da prova «{prova.titulo}» ({prova.codigo}) durante a protecção.\n"
             f"Isto acontece quando a folha, a fotografia ou a captura do ecrã com o QR é lida por um telemóvel.\n\n"
             + "\n".join(_linha(l) for l in pendentes[:20])
             + (f"\n... e mais {len(pendentes) - 20} leituras." if len(pendentes) > 20 else "")
             + "\n\nO SIGE não identifica a pessoa: mostra o aparelho e, se ela autorizou, o local aproximado. "
               "Vê o histórico em Provas Anti-IA > a prova > Leituras. Para deixar de receber estes avisos, desliga-os em Gerir.\n")
    send_mail(f"[SIGE] Código da prova {prova.codigo} lido durante a protecção", corpo, None, [destino], fail_silently=False)
    LeituraEscudo.objects.filter(pk__in=[l.pk for l in pendentes]).update(notificada=True)
    return len(pendentes)


def _tarefa(prova_codigo, atraso):
    try:
        time.sleep(atraso)
        for _ in range(3):
            if enviar_aviso(prova_codigo) != -1:
                return
            time.sleep(JANELA_S)
    except Exception:  # noqa: BLE001 - nunca estraga a página pública
        pass
    finally:
        from django.db import connection
        connection.close()


def agendar(prova_codigo, atraso=ATRASO_S):
    if email_activo():
        threading.Thread(target=_tarefa, args=(prova_codigo, atraso), daemon=True).start()