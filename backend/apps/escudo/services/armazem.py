"""Armazém do Escudo sobre a base de dados do SIGE (PostgreSQL/SQLite): provas cifradas, leituras e registo."""
import hashlib
from datetime import timedelta

from django.db import transaction
from django.db.models import Count

from ..models import EventoEscudo, LeituraEscudo, ProvaEscudo
from . import tempo
from .cofre import Cofre, cifrar, decifrar

ALFABETO_ID = "ABCDEFGHJKMNPQRSTVWXYZ23456789"


class ArmazemIndisponivel(Exception):
    pass


def _dict(p, leituras=None):
    return {
        "id": p.codigo, "titulo": p.titulo, "disciplina": p.disciplina, "classe": p.classe,
        "criada_em": tempo.para_iso(p.criada_em), "libertacao": tempo.para_iso(p.libertacao),
        "publicar_apos": p.publicar_apos, "tem_gabarito": bool(p.gabarito_cifrado), "paginas": p.paginas,
        "copias": p.copias, "config": p.config or {}, "escola_id": p.escola_id, "dono_id": p.criado_por_id,
        "leituras": leituras if leituras is not None else 0,
    }


class Armazem:
    nome = "Base de dados do SIGE"
    detalhe = "PDFs cifrados com AES-256-GCM antes de serem guardados"
    max_bytes = 10 * 1024 * 1024
    cofre = Cofre()

    def deslocamento(self):
        return timedelta(0)

    def listar(self, qs=None):
        qs = (qs if qs is not None else ProvaEscudo.objects.all()).defer('pdf_cifrado', 'gabarito_cifrado')
        return [_dict(p, p.n_leituras) for p in qs.annotate(n_leituras=Count('leituras'))]

    def obter(self, pid):
        p = ProvaEscudo.objects.filter(codigo=pid).defer('pdf_cifrado', 'gabarito_cifrado').first()
        return _dict(p, p.leituras.count()) if p else None

    def criar(self, d, prova, gabarito, agora_iso, evento, escola=None, criado_por=None):
        with transaction.atomic():
            p = ProvaEscudo.objects.create(
                codigo=d["id"], escola=escola, criado_por=criado_por, titulo=d["titulo"], disciplina=d["disciplina"],
                classe=d["classe"], libertacao=tempo.de_iso(d["libertacao"]), publicar_apos=d["publicar_apos"],
                paginas=d["paginas"], config=d["config"], pdf_cifrado=cifrar(d["id"], "prova", prova),
                gabarito_cifrado=cifrar(d["id"], "gabarito", gabarito) if gabarito else None)
            EventoEscudo.objects.create(prova=p, texto=evento)

    def arquivo(self, pid, tipo):
        p = ProvaEscudo.objects.get(codigo=pid)
        bruto = p.pdf_cifrado if tipo == "prova" else p.gabarito_cifrado
        if not bruto:
            raise FileNotFoundError(tipo)
        return decifrar(pid, tipo, bruto)

    def leituras(self, pid):
        return [{"serial": l.serial, "quando": tempo.para_iso(l.quando), "estado": l.estado,
                 "aparelho": l.aparelho or None, "rede": l.rede or None}
                for l in LeituraEscudo.objects.filter(prova__codigo=pid)[:100]]

    def eventos(self, pid):
        return [{"quando": tempo.para_iso(e.quando), "texto": e.texto} for e in EventoEscudo.objects.filter(prova__codigo=pid)]

    def alterar_data(self, pid, nova_iso, agora_iso, evento):
        p = ProvaEscudo.objects.get(codigo=pid)
        p.libertacao = tempo.de_iso(nova_iso)
        p.save(update_fields=["libertacao"])
        EventoEscudo.objects.create(prova=p, texto=evento)

    def libertar(self, pid, agora_iso, evento):
        self.alterar_data(pid, agora_iso, agora_iso, evento)

    def guardar_geracao(self, pid, config, copias, agora_iso, evento):
        p = ProvaEscudo.objects.get(codigo=pid)
        p.config, p.copias = config, max(p.copias, copias)
        p.save(update_fields=["config", "copias"])
        EventoEscudo.objects.create(prova=p, texto=evento)

    def atualizar(self, pid, campos, config, prova, gabarito, remover_gabarito, paginas, evento):
        """Edita uma prova já guardada: texto, ficheiros (cifrados de novo) e configuração; as leituras e o registo ficam."""
        with transaction.atomic():
            p = ProvaEscudo.objects.get(codigo=pid)
            for k, v in campos.items():
                setattr(p, k, v)
            p.config = config
            if prova:
                p.pdf_cifrado, p.paginas = cifrar(pid, "prova", prova), paginas
            if gabarito:
                p.gabarito_cifrado = cifrar(pid, "gabarito", gabarito)
            elif remover_gabarito:
                p.gabarito_cifrado = None
            p.save()
            EventoEscudo.objects.create(prova=p, texto=evento)

    def apagar(self, pid):
        ProvaEscudo.objects.filter(codigo=pid).delete()

    def verificar(self, pid, serial, agora, aparelho=None, rede=None):
        p = ProvaEscudo.objects.filter(codigo=pid).defer('pdf_cifrado', 'gabarito_cifrado').first()
        if not p:
            return None
        liberada = agora >= p.libertacao
        valido = serial is None or 1 <= serial <= p.copias
        estado = "invalida" if not valido else "libertada" if liberada else "embargo"
        impressao = hashlib.sha256(("escudo-rede:" + (rede or "")).encode()).hexdigest()[:12] if rede else ""
        LeituraEscudo.objects.create(prova=p, serial=serial, estado=estado, aparelho=(aparelho or "")[:120], rede=impressao)
        return {"id": pid, "titulo": p.titulo, "libertacao": tempo.para_iso(p.libertacao), "liberada": liberada,
                "valido": valido, "publicar_apos": p.publicar_apos, "tem_gabarito": bool(p.gabarito_cifrado),
                "mensagem_ia": (p.config or {}).get("mensagem_ia")}

    def arquivo_publico(self, pid, tipo, agora):
        p = ProvaEscudo.objects.filter(codigo=pid).first()
        if not p:
            return None
        if agora < p.libertacao or not p.publicar_apos:
            raise PermissionError("embargo")
        bruto = p.pdf_cifrado if tipo == "prova" else p.gabarito_cifrado
        return decifrar(pid, tipo, bruto) if bruto else None
