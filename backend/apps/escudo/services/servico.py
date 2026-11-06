"""Regras comuns à interface web e à linha de comandos, sobre um armazém (local ou Supabase)."""
import base64
import json
import os
import re
import secrets
import unicodedata
from pathlib import Path

from . import conversao, selos, tempo, variantes, variantes_word
from .armazem import ALFABETO_ID, Armazem

MAX_COPIAS = 200
MARCAS_INICIAIS = [  # o QR de cada página é automático (qr_pagina); aqui só o código de barras da primeira
    {"tipo": "barras", "paginas": "primeira", "x": 0.5, "y": 0.91, "tamanho_mm": 50},
]
FORMATOS_SAIDA = ("pdf", "word", "ambos")
CHAVES_CONFIG = ("formato", "guiao_opcao", "marcas", "url_base", "rasterizar", "aviso_visivel", "aviso_ia", "aviso_foto", "aviso_pergunta",
                 "qr_pergunta", "qr_marca_agua", "qr_pagina", "baralhar_perguntas", "baralhar_alternativas", "mensagem_ia", "copias")


class BaseSelagem:
    """PDF pronto a selar (já rasterizado, se for caso) e posição das perguntas, detectada no original."""

    def __init__(self, pdf, ancoras, zonas_agua=None):
        self.pdf, self.ancoras, self.zonas_agua = pdf, ancoras, zonas_agua

    def para(self, serial):
        return self


class BaseVariantesWord:
    """Variantes de uma prova em Word: cada cópia é o .docx preenchido com os seus valores e convertido para PDF.

    A cópia 1 já está guardada em PDF (serve a pré-visualização sem converter nada); as outras convertem-se todas
    de uma vez, à primeira que for pedida.
    """

    def __init__(self, svc, p, modelo, op, detetar, agua):
        self.svc, self.p, self.modelo, self.op, self.detetar, self.agua = svc, p, modelo, op, detetar, agua
        self._bases = {}

    def docx_copia(self, docx, serial):
        """O .docx da cópia: valores da cópia (se houver variáveis) e ordem das perguntas/alternativas (se pedido)."""
        if self.modelo and self.modelo.get("variaveis"):
            docx = variantes_word.preencher_docx(docx, variantes.escolher_valores(self.modelo, self.p["id"], serial))
        if self.op.get("baralhar_perguntas") or self.op.get("baralhar_alternativas"):
            docx, _ = variantes_word.baralhar_docx(docx, self.p["id"], serial, self.op.get("baralhar_perguntas"),
                                                   self.op.get("baralhar_alternativas"))
        return docx

    def _base(self, pdf):
        if self.op.get("aviso_foto") or self.op.get("aviso_visivel"):
            pdf = selos.reservar_margens(pdf)
        return BaseSelagem(selos.preparar_base(pdf, self.op["rasterizar"]),
                           selos.detectar_perguntas(pdf) if self.detetar else None,
                           selos.espaco_marca_agua(pdf) if self.agua else None)

    def para(self, serial):
        if serial not in self._bases:
            if serial == 1:
                self._bases[1] = self._base(self.svc.abrir(self.p["id"]))
            else:
                docx = self.svc.docx(self.p)
                seriais = [s for s in range(2, max(self.op["copias"], serial) + 1) if s not in self._bases]
                copias = [self.docx_copia(docx, s) for s in seriais]
                for s, pdf in zip(seriais, conversao.docxs_para_pdfs(copias)):
                    self._bases[s] = self._base(pdf)
        return self._bases[serial]


class BaseVariantes:
    """Uma base por cópia: o PDF de cada cópia sai do modelo, com os valores dessa cópia."""

    def __init__(self, modelo, pid, rasterizar, detetar, agua=False):
        self.modelo, self.pid, self.rasterizar, self.detetar, self.agua = modelo, pid, rasterizar, detetar, agua
        self._ultima = None

    def para(self, serial):
        if not self._ultima or self._ultima[0] != serial:
            pdf = variantes.pdf_copia(self.modelo, self.pid, serial)
            ancoras = selos.detectar_perguntas(pdf) if self.detetar else None
            zonas = selos.espaco_marca_agua(pdf) if self.agua else None
            self._ultima = (serial, BaseSelagem(selos.preparar_base(pdf, self.rasterizar), ancoras, zonas))
        return self._ultima[1]


def nome_seguro(texto):
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", ascii_).strip("_")[:60] or "prova"


class Servico:
    def __init__(self, relogio=None):
        self.arm = Armazem()
        self.relogio = relogio or tempo.agora

    @property
    def max_bytes(self):
        return self.arm.max_bytes

    def agora(self):
        return self.relogio() + self.arm.deslocamento()

    def estado(self, p):
        lib = tempo.de_iso(p["libertacao"])
        return {"liberada": self.agora() >= lib, "dt": lib, "texto": tempo.formatar(lib), "sem_data": tempo.e_sem_data(lib)}

    def _agora_iso(self):
        return tempo.para_iso(self.agora())

    # ---- consulta ----
    def listar(self):
        return self.arm.listar()

    def prova(self, pid):
        return self.arm.obter(pid)

    def abrir(self, pid, tipo="prova"):
        return self.arm.arquivo(pid, tipo)

    def leituras(self, pid):
        return self.arm.leituras(pid)

    def eventos(self, pid):
        return self.arm.eventos(pid)

    # ---- escrita ----
    def validar_opcoes(self, *, marcas, copias, url_base, rasterizar=False, aviso_visivel=True,
                       aviso_foto=True, aviso_ia=True, aviso_pergunta=True, qr_pergunta=True, qr_marca_agua=True, qr_pagina=True, mensagem_ia=None,
                       baralhar_perguntas=False, baralhar_alternativas=False):
        """Valida as opções de selagem e devolve o dicionário usado por `selar_copia`."""
        marcas = selos.validar_marcas(marcas)
        if not 1 <= copias <= MAX_COPIAS:
            raise ValueError(f"O número de cópias deve estar entre 1 e {MAX_COPIAS}.")
        url_base = url_base.strip().rstrip("/")
        if not re.match(r"^https?://[^\s/]+[^\s]*$", url_base):
            raise ValueError("O endereço público deve começar por http:// ou https://.")
        return {"marcas": marcas, "copias": copias, "url_base": url_base, "rasterizar": rasterizar,
                "aviso_visivel": aviso_visivel, "aviso_foto": aviso_foto, "aviso_ia": aviso_ia,
                "aviso_pergunta": aviso_pergunta, "qr_pergunta": qr_pergunta, "qr_marca_agua": qr_marca_agua, "qr_pagina": qr_pagina,
                "baralhar_perguntas": bool(baralhar_perguntas), "baralhar_alternativas": bool(baralhar_alternativas),
                "mensagem_ia": selos.normalizar_mensagem(mensagem_ia)}

    def registar(self, *, titulo, libertacao, pdf=b"", gabarito=b"", disciplina="", classe="", publicar_apos=True,
                 modelo=b"", so_word=False, dono="", variaveis_word="", condicoes_word="", respostas_word="",
                 escola=None, criado_por=None):
        """Valida, cifra e guarda uma prova nova; devolve o código. `libertacao` é um datetime UTC.

        Com `modelo` (JSON de variantes) a prova é gerada por cópia: guarda-se o modelo cifrado e a cópia 1 como PDF.
        """
        titulo = titulo.strip()[:120]
        limite = f"{self.max_bytes // (1024 * 1024)} MB"
        if not titulo:
            raise ValueError("Indica o título da prova.")
        if libertacao <= self.agora():
            raise ValueError("A data de libertação deve estar no futuro.")
        dados_modelo = None
        if modelo:
            dados_modelo = variantes.carregar_modelo(modelo)
            publicar_apos, gabarito = False, b""  # a cópia 1 não é «a prova»; o gabarito é por cópia
        elif not pdf:
            raise ValueError("Escolhe o PDF da prova ou o modelo de variantes.")
        pid = "".join(secrets.choice(ALFABETO_ID) for _ in range(8))
        config = {"marcas": MARCAS_INICIAIS, "dono": dono}
        com_variaveis = bool((variaveis_word or "").strip())
        if not dados_modelo and conversao.eh_docx(pdf) and len(pdf) <= self.max_bytes // 2:
            # o .docx fica guardado (cifrado): permite variantes e baralhar a ordem em cada cópia
            config["docx_cifrado"] = base64.b64encode(self.arm.cofre.cifrar(pid, "docx", pdf)).decode()
        elif com_variaveis and not dados_modelo:
            if not conversao.eh_docx(pdf):
                raise ValueError("As variantes precisam da prova em Word (.docx) com campos como {R1}.")
            raise ValueError(f"Com variantes, o Word pode ter no máximo {self.max_bytes // (2 * 1024 * 1024)} MB.")
        if not dados_modelo and (com_variaveis or (respostas_word or "").strip()) and "docx_cifrado" in config:
            # Word com campos {R1}… e/ou chave de respostas: o modelo dá os valores e o gabarito de cada cópia
            dados_modelo = variantes_word.modelo_word(pdf, variaveis_word, condicoes_word, respostas_word, titulo)
            if com_variaveis:
                pdf = variantes_word.preencher_docx(pdf, variantes.escolher_valores(dados_modelo, pid, 1))
                publicar_apos, gabarito = False, b""  # a cópia 1 não é «a prova»; o gabarito é por cópia
            config["modelo_cifrado"] = base64.b64encode(self.arm.cofre.cifrar(
                pid, "modelo", json.dumps(dados_modelo, ensure_ascii=False).encode("utf-8"))).decode()
        if dados_modelo and dados_modelo.get("origem") != "word":
            pdf = variantes.pdf_copia(dados_modelo, pid, 1)
            config["modelo_cifrado"] = base64.b64encode(self.arm.cofre.cifrar(
                pid, "modelo", json.dumps(dados_modelo, ensure_ascii=False).encode("utf-8"))).decode()
        if len(pdf) > self.max_bytes:
            raise ValueError(f"O ficheiro da prova excede {limite}.")
        if so_word and not dados_modelo and not conversao.eh_docx(pdf):  # (com variantes do Word já foi verificado)
            raise ValueError("A prova tem de ser um ficheiro Word (.docx). A saída é sempre em PDF.")
        pdf = conversao.garantir_pdf(pdf)
        paginas, _, _ = selos.info_pdf(pdf)
        if gabarito:
            if len(gabarito) > self.max_bytes:
                raise ValueError(f"O ficheiro do gabarito excede {limite}.")
            if so_word and not conversao.eh_docx(gabarito):
                raise ValueError("O gabarito tem de ser um ficheiro Word (.docx).")
            gabarito = conversao.garantir_pdf(gabarito)
            selos.info_pdf(gabarito)
        self.arm.criar(
            {"id": pid, "titulo": titulo, "disciplina": disciplina.strip()[:60], "classe": classe.strip()[:30],
             "libertacao": tempo.para_iso(libertacao), "publicar_apos": bool(publicar_apos), "paginas": paginas,
             "config": config},
            pdf, gabarito or None, self._agora_iso(), f"Prova carregada; libertação em {tempo.formatar(libertacao)}.",
            escola=escola, criado_por=criado_por)
        return pid

    def alterar_data(self, pid, libertacao):
        p = self.arm.obter(pid)
        self.arm.alterar_data(pid, tempo.para_iso(libertacao), self._agora_iso(),
                              f"Libertação alterada de {tempo.formatar_iso(p['libertacao'])} para {tempo.formatar(libertacao)}.")

    def libertar(self, pid):
        p = self.arm.obter(pid)
        self.arm.libertar(pid, self._agora_iso(), f"Libertada manualmente (data prevista: {tempo.formatar_iso(p['libertacao'])}).")

    def apagar(self, pid):
        self.arm.apagar(pid)

    # ---- página pública ----
    def verificar(self, pid, serial=None, aparelho=None, rede=None):
        """Regista a leitura (com o aparelho e a rede de quem leu) e devolve (prova, estado, válido), ou None se a prova não existe."""
        r = self.arm.verificar(pid, serial, self.agora(), aparelho, rede)
        if r is None:
            return None
        lib = tempo.de_iso(r["libertacao"])
        return r, {"liberada": r["liberada"], "dt": lib, "texto": tempo.formatar(lib), "sem_data": tempo.e_sem_data(lib)}, r["valido"]

    def pdf_publico(self, pid, tipo):
        """PDF depois da data; PermissionError durante o embargo; None se não existir."""
        return self.arm.arquivo_publico(pid, tipo, self.agora())

    # ---- variantes ----
    def modelo(self, p):
        """Modelo de variantes decifrado, ou None se a prova é um PDF único."""
        cifrado = (p.get("config") or {}).get("modelo_cifrado")
        if not cifrado:
            return None
        return json.loads(self.arm.cofre.decifrar(p["id"], "modelo", base64.b64decode(cifrado)))

    def docx(self, p):
        """O .docx original (com os campos {…}) de uma prova com variantes do Word."""
        return self.arm.cofre.decifrar(p["id"], "docx", base64.b64decode(p["config"]["docx_cifrado"]))

    def mapas_copias(self, p, copias):
        """Ordem das perguntas e alternativas de cada cópia 1..copias (vazio se a prova não é baralhada)."""
        cfg = p.get("config") or {}
        if not (cfg.get("baralhar_perguntas") or cfg.get("baralhar_alternativas")) or not cfg.get("docx_cifrado"):
            return {s: {} for s in range(1, copias + 1)}
        docx = self.docx(p)
        return {s: variantes_word.baralhar_docx(docx, p["id"], s, cfg.get("baralhar_perguntas"),
                                                cfg.get("baralhar_alternativas"))[1] for s in range(1, copias + 1)}

    def gabarito_copias(self, pid, copias):
        """PDF (só para o professor) com os valores e as respostas de cada cópia 1..copias."""
        p = self.prova(pid)
        modelo = self.modelo(p) if p else None
        if not modelo:
            raise ValueError("Esta prova não tem variantes.")
        copias = max(1, min(copias, MAX_COPIAS))
        if modelo.get("origem") == "word":
            mapas = self.mapas_copias(p, copias)
            return variantes_word.pdf_gabarito_word(modelo, pid, copias, mapas)
        return variantes.pdf_gabarito(modelo, pid, copias)

    def conferir(self, pid, serial, texto):
        """Compara as respostas de um aluno com a chave da cópia dele e com as das outras cópias.

        Uma resposta errada na cópia dele mas certa noutra cópia (para a mesma pergunta, ou para o mesmo número)
        é sinal de cópia ou de uma resolução feita para outra cópia (por exemplo, por IA).
        """
        p = self.prova(pid)
        modelo = self.modelo(p) if p else None
        if not modelo or not modelo.get("perguntas"):
            raise ValueError("Para conferir, a prova precisa das respostas (indicadas ao carregar o Word).")
        copias = max(p.get("copias") or 1, 1)
        if not 1 <= serial <= copias:
            raise ValueError(f"A cópia deve estar entre 1 e {copias}.")
        mapas = self.mapas_copias(p, copias)
        chaves = {s: variantes_word.chave_copia(modelo, pid, s, mapas[s]) for s in range(1, copias + 1)}
        respostas = variantes_word.ler_respostas_aluno(texto)
        linhas, por_copia = [], {}
        for n in sorted(respostas, key=int):
            dada = respostas[n]
            original, certa = chaves[serial].get(n, (None, None))
            certo = certa is not None and variantes_word.coincide(dada, certa)
            outras = []
            if not certo:
                for s, chave in chaves.items():
                    if s == serial:
                        continue
                    mesma = any(o == original and variantes_word.coincide(dada, r) for o, r in chave.values()) if original else False
                    mesmo_n = n in chave and variantes_word.coincide(dada, chave[n][1])
                    if mesma or mesmo_n:
                        outras.append(s)
                        por_copia[s] = por_copia.get(s, 0) + 1
            linhas.append({"n": n, "dada": dada, "certa": certa, "certo": certo, "outras": outras})
        suspeitas = sorted(por_copia.items(), key=lambda x: -x[1])
        # semelhança global: quantas respostas (certas ou não) batem com a chave de cada outra cópia, número a número
        certas = sum(l["certo"] for l in linhas)
        semelhanca = sorted(((s, sum(1 for n, d in respostas.items() if n in chave and variantes_word.coincide(d, chave[n][1])))
                             for s, chave in chaves.items() if s != serial), key=lambda x: -x[1])
        mais = semelhanca[0] if semelhanca else None
        alerta = bool(mais and mais[1] > certas and mais[1] >= 0.6 * len(respostas))
        return {"serial": serial, "linhas": linhas, "certas": certas, "suspeitas": suspeitas,
                "semelhanca": semelhanca[:3], "alerta": alerta, "total": len(respostas)}

    # ---- selagem ----
    def preparar_base(self, pid, op):
        detetar = bool(op.get("aviso_pergunta") or op.get("qr_pergunta"))
        agua = bool(op.get("qr_marca_agua"))
        p = self.prova(pid)
        modelo = self.modelo(p)
        baralhar = (op.get("baralhar_perguntas") or op.get("baralhar_alternativas")) and (p.get("config") or {}).get("docx_cifrado")
        if (modelo and modelo.get("origem") == "word" and modelo.get("variaveis")) or baralhar:
            return BaseVariantesWord(self, p, modelo, op, detetar, agua)
        if modelo:
            return BaseVariantes(modelo, pid, op["rasterizar"], detetar, agua)
        original = self.abrir(pid)
        if op.get("aviso_foto") or op.get("aviso_visivel"):
            original = selos.reservar_margens(original)  # as faixas de aviso não podem tapar o conteúdo
        ancoras = selos.detectar_perguntas(original) if detetar else None
        zonas = selos.espaco_marca_agua(original) if agua else None
        return BaseSelagem(selos.preparar_base(original, op["rasterizar"]), ancoras, zonas)

    def selar_copia(self, p, op, serial, base=None):
        base = (base or self.preparar_base(p["id"], op)).para(serial)
        return selos.selar(base.pdf, op["marcas"], url_base=op["url_base"], pid=p["id"], serial=serial,
                           libertacao=self.estado(p)["texto"], titulo=p["titulo"],
                           aviso_visivel=op["aviso_visivel"], aviso_ia=op["aviso_ia"], aviso_foto=op["aviso_foto"],
                           mensagem_ia=op["mensagem_ia"], aviso_pergunta=op["aviso_pergunta"],
                           qr_pergunta=op["qr_pergunta"], qr_marca_agua=op["qr_marca_agua"], qr_pagina=op.get("qr_pagina", True), ancoras=base.ancoras,
                           zonas_marca_agua=base.zonas_agua)

    def tem_word(self, p):
        """O .docx original está guardado (cifrado): só então a prova pode sair também em Word."""
        return bool((p.get("config") or {}).get("docx_cifrado"))

    def docx_da_copia(self, p, op, serial):
        """O .docx da cópia (valores e ordem), ainda sem protecção."""
        pid, docx = p["id"], self.docx(p)
        modelo = self.modelo(p)
        if modelo and modelo.get("variaveis"):
            docx = variantes_word.preencher_docx(docx, variantes.escolher_valores(modelo, pid, serial))
        if op.get("baralhar_perguntas") or op.get("baralhar_alternativas"):
            docx, _ = variantes_word.baralhar_docx(docx, pid, serial, op.get("baralhar_perguntas"), op.get("baralhar_alternativas"))
        return docx

    def zona_word(self, p, op):
        """Onde cabe o QR de fundo no Word: mede-se a cópia 1, que tem a mesma paginação que o Word final (uma conversão por geração)."""
        from . import word_selo
        try:
            pdf = conversao.docx_para_pdf(self.docx_da_copia(p, op, 1))
            op["pdf_layout_word"] = pdf  # mesma paginação do Word final: serve para pôr as marcas e o QR lateral página a página
            zonas = selos.espaco_marca_agua(pdf)
            return zonas[0] if zonas else None
        except Exception:
            return None
    def selar_word(self, p, op, serial):
        """A cópia `serial` em Word (.docx) editável: valores e ordem da cópia, avisos, QR de marca de água e código da cópia.

        Parte do Word original (equações e formatação intactas): não passa pelo PDF.
        """
        if not self.tem_word(p):
            raise ValueError("Para sair em Word, carrega a prova em Word (.docx).")
        pid = p["id"]
        docx = self.docx_da_copia(p, op, serial)
        from . import word_selo
        zona = op.get("zona_word")
        if zona is None and "zona_word" not in op and (op.get("qr_marca_agua") or op.get("qr_pagina") or op["marcas"]):
            zona = self.zona_word(p, op)
        return word_selo.selar_docx(
            docx, pid=pid, serial=serial, libertacao=self.estado(p)["texto"], titulo=p["titulo"], url_base=op["url_base"],
            marcas=op["marcas"], zona_agua=zona, aviso_foto=op["aviso_foto"], aviso_ia=op["aviso_ia"],
            aviso_pergunta=op["aviso_pergunta"], qr_pergunta=op["qr_pergunta"], qr_marca_agua=op["qr_marca_agua"],
            aviso_visivel=op["aviso_visivel"], mensagem_ia=op["mensagem_ia"], qr_pagina=op.get("qr_pagina", True),
            pdf_layout=op.get("pdf_layout_word"))

    def resumo_perguntas(self, pid):
        """Quantas perguntas numeradas foram detetadas e em quantas cabe um QR (margem direita livre)."""
        achadas = [a for pagina in selos.detectar_perguntas(self.abrir(pid)) for a in pagina]
        return {"total": len(achadas), "com_qr": sum(1 for a in achadas if a["qr"]),
                "sem_qr": [a["n"] for a in achadas if not a["qr"]]}

    def registar_geracao(self, pid, op):
        """Guarda a configuração usada e o nº de cópias válidas, e regista o evento."""
        anterior = (self.prova(pid) or {}).get("config") or {}
        config = {**anterior, **{k: op[k] for k in CHAVES_CONFIG}}  # mantém o modelo cifrado, se houver
        self.arm.guardar_geracao(
            pid, config, op["copias"], self._agora_iso(),
            f"Geradas {op['copias']} cópia(s) seladas ({len(op['marcas'])} marca(s)"
            f"{', rasterizada' if op['rasterizar'] else ''}).")
