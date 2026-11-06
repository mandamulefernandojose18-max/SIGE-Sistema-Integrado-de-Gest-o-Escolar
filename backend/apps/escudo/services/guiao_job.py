"""Geração do Guião em segundo plano (a IA demora minutos: o pedido HTTP não pode esperar) e guarda do resultado cifrado.

O estado fica em `ProvaEscudo.config["guiao"]` e o Guião em `config["guiao_cifrado"]` (AES-256-GCM, como a prova).
"""
import base64
import json
import logging
import threading
import time

from django.db import connection

from ..models import EventoEscudo, ProvaEscudo
from . import cofre, ia_sige

log = logging.getLogger(__name__)
LIMITE_24H = 5          # gerações por prova e por dia (controla o custo da IA)
EXPIRA_SEGUNDOS = 1800  # uma geração «a decorrer» há mais de 30 min considera-se interrompida (ex.: servidor reiniciado)
SINCRONO = False        # os testes executam a geração no próprio pedido


def estado(config):
    """Estado actual do Guião de uma prova (a partir do `config`)."""
    g = dict((config or {}).get("guiao") or {})
    if g.get("estado") == "gerando" and time.time() - g.get("inicio", 0) > EXPIRA_SEGUNDOS:
        g.update(estado="erro", mensagem="A geração foi interrompida. Tente de novo.")
    g.setdefault("estado", "nenhum")
    g["geracoes_24h"] = sum(1 for t in g.get("geracoes", []) if time.time() - t < 86400)
    g["limite_24h"] = LIMITE_24H
    g["pronto"] = g["estado"] == "pronto" and bool((config or {}).get("guiao_cifrado"))
    return g


def dados(codigo, config):
    """O Guião decifrado (dict), ou None se ainda não existe."""
    bruto = (config or {}).get("guiao_cifrado")
    if not bruto:
        return None
    return json.loads(cofre.decifrar(codigo, "guiao", base64.b64decode(bruto)))


def _guardar(codigo, mudancas=None, guiao_dados=None):
    """Junta as mudanças ao `config` da base (relê antes, para não apagar o que mudou entretanto)."""
    p = ProvaEscudo.objects.defer("pdf_cifrado", "gabarito_cifrado").get(codigo=codigo)
    config = dict(p.config or {})
    g = dict(config.get("guiao") or {})
    g.update(mudancas or {})
    config["guiao"] = g
    if guiao_dados is not None:
        config["guiao_cifrado"] = base64.b64encode(
            cofre.cifrar(codigo, "guiao", json.dumps(guiao_dados, ensure_ascii=False).encode("utf-8"))).decode()
    ProvaEscudo.objects.filter(codigo=codigo).update(config=config)
    return p


def iniciar(codigo):
    """Põe a geração em marcha. Devolve (estado, mensagem de erro ou None)."""
    if not ia_sige.disponivel():
        return None, "A IA do SIGE ainda não está activada neste servidor (falta a chave da IA)."
    p = ProvaEscudo.objects.defer("pdf_cifrado", "gabarito_cifrado").get(codigo=codigo)
    atual = estado(p.config)
    if atual["estado"] == "gerando":
        return atual, None
    if atual["geracoes_24h"] >= LIMITE_24H:
        return None, f"Limite de {LIMITE_24H} gerações por prova em 24 horas atingido. Tente amanhã ou use o Guião já gerado."
    agora = time.time()
    geracoes = [t for t in (p.config.get("guiao") or {}).get("geracoes", []) if agora - t < 86400] + [agora]
    _guardar(codigo, {"estado": "gerando", "inicio": agora, "fim": None, "mensagem": "", "geracoes": geracoes,
                      "modelo": ia_sige.modelo()})
    EventoEscudo.objects.create(prova=p, texto="Guião (resolução detalhada) pedido à IA do SIGE.")
    if SINCRONO:
        _executar(codigo, fechar_ligacao=False)
    else:
        threading.Thread(target=_executar, args=(codigo,), daemon=True, name=f"guiao-{codigo}").start()
    return estado(ProvaEscudo.objects.defer("pdf_cifrado", "gabarito_cifrado").get(codigo=codigo).config), None


def _executar(codigo, fechar_ligacao=True):
    try:
        p = ProvaEscudo.objects.get(codigo=codigo)
        pdf = cofre.decifrar(codigo, "prova", p.pdf_cifrado)
        r = ia_sige.resolver_prova(pdf, p.titulo, p.disciplina, p.classe)
        _guardar(codigo, {"estado": "pronto", "fim": time.time(), "mensagem": "", "uso": r["uso"], "revisto": False,
                          "questoes": len(r["dados"]["questoes"])}, guiao_dados=r["dados"])
        EventoEscudo.objects.create(prova=p, texto=f"Guião gerado pela IA ({len(r['dados']['questoes'])} questões).")
    except ia_sige.IAIndisponivel as e:
        _guardar(codigo, {"estado": "erro", "fim": time.time(), "mensagem": str(e)})
    except Exception:  # noqa: BLE001 - o professor vê uma mensagem clara; o detalhe vai para o registo do servidor
        log.exception("Falha ao gerar o guião da prova %s", codigo)
        _guardar(codigo, {"estado": "erro", "fim": time.time(), "mensagem": "Não foi possível gerar o guião. Tente de novo."})
    finally:
        if fechar_ligacao:
            connection.close()


def resumo_questoes(guiao):
    """Resumo para o professor rever no ecrã (número, opção, resposta, confiança)."""
    return [{"numero": q.get("numero"), "tipo": q.get("tipo"), "opcao_correcta": q.get("opcao_correcta", ""),
             "resposta_final": q.get("resposta_final", ""), "confianca": q.get("confianca", "media"),
             "observacao": q.get("observacao", ""), "passos": len(q.get("passos", []))} for q in guiao.get("questoes", [])]


def corrigir(codigo, numero, opcao=None, resposta=None):
    """O professor corrige a opção ou a resposta final de uma questão (a IA pode errar)."""
    p = ProvaEscudo.objects.defer("pdf_cifrado", "gabarito_cifrado").get(codigo=codigo)
    guiao = dados(codigo, p.config)
    if not guiao:
        raise ValueError("Ainda não há Guião para corrigir.")
    alvo = next((q for q in guiao["questoes"] if str(q.get("numero")) == str(numero)), None)
    if not alvo:
        raise ValueError("Questão não encontrada no Guião.")
    if opcao is not None:
        opcao = opcao.strip().upper()
        if opcao and opcao not in list("ABCDE"):
            raise ValueError("A opção deve ser A, B, C, D ou E (ou vazia).")
        alvo["opcao_correcta"] = opcao
        if not opcao:
            alvo["texto_opcao_correcta"] = alvo["justificacao_opcao"] = ""
    if resposta is not None:
        alvo["resposta_final"] = resposta.strip()[:500]
    alvo["confianca"] = "alta"  # verificada pelo professor
    _guardar(codigo, {"revisto": True}, guiao_dados=guiao)
    return guiao
