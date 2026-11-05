"""Datas: guardadas em UTC, mostradas e introduzidas na hora de Maputo (CAT, UTC+2, sem hora de verão)."""
from datetime import datetime, timedelta, timezone

CAT = timezone(timedelta(hours=2), "CAT")


SEM_DATA = datetime(2099, 12, 31, 21, 59, tzinfo=timezone.utc)  # «sem data limite»: só a protecção anti-IA, sem embargo
TEXTO_SEM_DATA = "sem data limite"


def e_sem_data(dt):
    return dt >= SEM_DATA


def agora():
    return datetime.now(timezone.utc)


def para_iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def de_iso(texto):
    return datetime.strptime(texto, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def de_campo_local(texto):
    """'2026-11-05T14:00' (campo datetime-local, hora de Maputo) -> datetime UTC."""
    dt = datetime.fromisoformat(texto.strip())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CAT)
    return dt.astimezone(timezone.utc)


def formatar(dt):
    if e_sem_data(dt):
        return TEXTO_SEM_DATA
    return dt.astimezone(CAT).strftime("%d/%m/%Y %H:%M")


def formatar_iso(texto):
    return formatar(de_iso(texto))


def para_campo_local(texto):
    return de_iso(texto).astimezone(CAT).strftime("%Y-%m-%dT%H:%M")
