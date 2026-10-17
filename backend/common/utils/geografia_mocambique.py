"""
Constantes e Geografia Oficial da República de Moçambique (MEC)
"""

PROVINCIAS_MOCAMBIQUE = [
    'Cidade de Maputo',
    'Província de Maputo',
    'Gaza',
    'Inhambane',
    'Manica',
    'Sofala',
    'Tete',
    'Zambézia',
    'Nampula',
    'Niassa',
    'Cabo Delgado'
]

DISTRITOS_POR_PROVINCIA = {
    'Cidade de Maputo': [
        'KaMpfumo', 'Nlhamankulu', 'KaMaxakeni', 'KaMavota', 'KaMubukwana', 'KaTembe', 'KaNyaka'
    ],
    'Província de Maputo': [
        'Boane', 'Magude', 'Manhiça', 'Marracuene', 'Matola', 'Matutuíne', 'Moamba', 'Namaacha'
    ],
    'Gaza': [
        'Bilene', 'Chibuto', 'Chicualacuala', 'Chigubo', 'Chókwè', 'Chongoene', 'Guijá',
        'Limpopo', 'Mabalane', 'Manjacaze', 'Massangena', 'Massingir', 'Xai-Xai'
    ],
    'Inhambane': [
        'Funhalouro', 'Govuro', 'Homoíne', 'Inhambane', 'Inharrime', 'Inhassoro', 'Jangamo',
        'Mabote', 'Massinga', 'Maxixe', 'Morrumbene', 'Mupaculane', 'Panda', 'Vilankulo', 'Zavala'
    ],
    'Manica': [
        'Bárue', 'Chimoio', 'Gondola', 'Guro', 'Macate', 'Machaze', 'Macossa',
        'Manica', 'Mossurize', 'Sussundenga', 'Tambara', 'Vanduzi'
    ],
    'Sofala': [
        'Beira', 'Búzi', 'Caia', 'Chemba', 'Cheringoma', 'Chibabava', 'Dondo',
        'Gorongosa', 'Machanga', 'Marínguè', 'Marromeu', 'Muanza', 'Nhamatanda'
    ],
    'Tete': [
        'Angónia', 'Cahora-Bassa', 'Changara', 'Chifunde', 'Chiuta', 'Dôa', 'Macanga',
        'Magoé', 'Marara', 'Marávia', 'Moatize', 'Mutarara', 'Tete', 'Tsangano', 'Zumbo'
    ],
    'Zambézia': [
        'Alto Molócue', 'Chinde', 'Derre', 'Gilé', 'Gurué', 'Ile', 'Inhassunge', 'Luabo',
        'Lugela', 'Maganja da Costa', 'Milange', 'Mocuba', 'Mocubela', 'Molumbo',
        'Mopeia', 'Morrumbala', 'Mulevala', 'Namacurra', 'Namarroi', 'Nicoadala', 'Pebane', 'Quelimane'
    ],
    'Nampula': [
        'Angoche', 'Eráti', 'Ilha de Moçambique', 'Lalaua', 'Larde', 'Liúpo', 'Malema',
        'Meconta', 'Mecubúri', 'Memba', 'Mogincual', 'Mogovolas', 'Moma', 'Monapo',
        'Mossuril', 'Muecate', 'Murrupula', 'Nacala-a-Velha', 'Nacala Porto', 'Nampula', 'Ribaue'
    ],
    'Niassa': [
        'Cuamba', 'Lago', 'Lichinga', 'Majune', 'Mandimba', 'Marrupa', 'Maúa',
        'Mavago', 'Mecanhelas', 'Mecula', 'Metarica', 'Muembe', "N'gauma", 'Nipepe', 'Sanga'
    ],
    'Cabo Delgado': [
        'Ancuabe', 'Balama', 'Chiúre', 'Ibo', 'Macomia', 'Mecúfi', 'Meluco', 'Metuge',
        'Mocímboa da Praia', 'Montepuez', 'Mueda', 'Muidumbe', 'Namuno', 'Nangade', 'Palma', 'Pemba', 'Quissanga'
    ]
}

CARREIRAS_DOCENTES = [
    'DN4',
    'DN3',
    'DN2',
    'DN1',
    'Especialista de Educação',
    'Mestre',
    'Professor Doutor'
]

TIPOS_DOCUMENTO = [
    'Bilhete de Identidade',
    'Passaporte',
    'Carta de Condução',
    'Cédula Pessoal'
]

ANOTACOES_STATUS = {
    'D': 'Desistiu',
    'T': 'Transferido',
    'VT': 'Vem Transferido',
    'F': 'Faleceu',
    'AM': 'Anulou Matrícula',
    'PPF': 'Perdeu o Ano por Faltas',
    'PDF': 'Perdeu Direito por Faltas'
}

COMPORTAMENTOS = [
    {'codigo': 'NS', 'nome': 'Não Suficiente'},
    {'codigo': 'S', 'nome': 'Suficiente'},
    {'codigo': 'B', 'nome': 'Bom'},
    {'codigo': 'MB', 'nome': 'Muito Bom'},
    {'codigo': 'E', 'nome': 'Excelente'}
]

def obter_distritos_por_provincia(provincia: str) -> list[str]:
    return DISTRITOS_POR_PROVINCIA.get(provincia, [])


TIPOS_ESCOLA = [
    {'codigo': 'P', 'nome': 'Escola Primária'},
    {'codigo': 'B', 'nome': 'Escola Básica'},
    {'codigo': 'S', 'nome': 'Escola Secundária'},
]

# Mapeamento oficial dos 2 primeiros dígitos (Província de Moçambique: 01 a 11)
CODIGOS_PROVINCIAS_MOCAMBIQUE = {
    'cidade de maputo': ('01', 'Cidade de Maputo'),
    'maputo cidade': ('01', 'Cidade de Maputo'),
    'maputo': ('01', 'Cidade de Maputo'),
    'provincia de maputo': ('02', 'Província de Maputo'),
    'província de maputo': ('02', 'Província de Maputo'),
    'maputo provincia': ('02', 'Província de Maputo'),
    'maputo província': ('02', 'Província de Maputo'),
    'gaza': ('03', 'Gaza'),
    'inhambane': ('04', 'Inhambane'),
    'manica': ('05', 'Manica'),
    'sofala': ('06', 'Sofala'),
    'tete': ('07', 'Tete'),
    'zambezia': ('08', 'Zambézia'),
    'zambézia': ('08', 'Zambézia'),
    'nampula': ('09', 'Nampula'),
    'niassa': ('10', 'Niassa'),
    'cabo delgado': ('11', 'Cabo Delgado'),
}


def _normalizar_texto_sem_acentos(texto: str) -> str:
    import unicodedata
    s = unicodedata.normalize('NFKD', str(texto or '').strip()).encode('ascii', 'ignore').decode('ascii')
    return s.lower().strip()


def obter_codigo_e_nome_provincia(provincia: str) -> tuple[str, str]:
    """Retorna (codigo_2_digitos, nome_oficial_provincia)."""
    chave = (provincia or '').strip().lower()
    if chave in CODIGOS_PROVINCIAS_MOCAMBIQUE:
        return CODIGOS_PROVINCIAS_MOCAMBIQUE[chave]

    chave_norm = _normalizar_texto_sem_acentos(provincia)
    for k, val in CODIGOS_PROVINCIAS_MOCAMBIQUE.items():
        if _normalizar_texto_sem_acentos(k) == chave_norm:
            return val

    for idx, p_nome in enumerate(PROVINCIAS_MOCAMBIQUE, start=1):
        if _normalizar_texto_sem_acentos(p_nome) == chave_norm:
            return (f"{idx:02d}", p_nome)

    return ('01', 'Cidade de Maputo')


def obter_codigo_distrito(provincia: str, distrito: str) -> str:
    """Retorna os 2 dígitos (3º e 4º dígitos do código da escola) correspondentes ao número do distrito na província."""
    _, nome_prov = obter_codigo_e_nome_provincia(provincia)
    distritos = DISTRITOS_POR_PROVINCIA.get(nome_prov, [])
    if not distritos:
        return '01'

    dist_norm = _normalizar_texto_sem_acentos(distrito)
    for idx, d in enumerate(distritos, start=1):
        if _normalizar_texto_sem_acentos(d) == dist_norm:
            return f"{idx:02d}"

    # Busca parcial caso o distrito venha com prefixo "Cidade de ..." ou "Distrito de ..."
    for idx, d in enumerate(distritos, start=1):
        d_n = _normalizar_texto_sem_acentos(d)
        if d_n and (d_n in dist_norm or dist_norm in d_n):
            return f"{idx:02d}"

    return '01'


def obter_letra_tipo_escola(tipo_escola: str = None, nome_escola: str = None) -> str:
    """
    Retorna a letra oficial do nível/tipo de escola:
    - P: Escola Primária
    - B: Escola Básica
    - S: Escola Secundária
    """
    t = _normalizar_texto_sem_acentos(tipo_escola)
    if t in ['p', 'primaria', 'escola primaria']:
        return 'P'
    if t in ['b', 'basica', 'escola basica']:
        return 'B'
    if t in ['s', 'secundaria', 'escola secundaria']:
        return 'S'

    nome_n = _normalizar_texto_sem_acentos(nome_escola)
    if 'primaria' in nome_n or 'ep1' in nome_n or 'ep2' in nome_n or 'epc' in nome_n:
        return 'P'
    if 'basica' in nome_n or 'eb ' in nome_n:
        return 'B'
    return 'S'


def gerar_codigo_unico_escola(provincia: str, distrito: str, tipo_escola: str = None, nome_escola: str = None, exclude_escola_id=None) -> str:
    """
    Gera o código único da escola no formato oficial:
    Exemplo: 0101S0001
    - 1º e 2º dígitos: número da província de Moçambique (01..11)
    - 3º e 4º dígitos: número do distrito naquela província (01..99)
    - Letra (5º caractere): P (Primária), B (Básica) ou S (Secundária)
    - Dígitos seguintes: número sequencial da escola (0001, 0002, ...)
    """
    import re
    from apps.tenants.models import Escola

    cod_prov, _ = obter_codigo_e_nome_provincia(provincia)
    cod_dist = obter_codigo_distrito(provincia, distrito)
    letra = obter_letra_tipo_escola(tipo_escola, nome_escola)
    prefixo = f"{cod_prov}{cod_dist}{letra}"

    qs = Escola.objects.all()
    if exclude_escola_id:
        qs = qs.exclude(id=exclude_escola_id)

    max_seq = 0
    for esc in qs.filter(codigo_escola__istartswith=prefixo):
        cod = (esc.codigo_escola or '').strip().upper()
        resto = cod[len(prefixo):]
        m = re.match(r'^(\d+)$', resto)
        if m:
            val = int(m.group(1))
            if val > max_seq:
                max_seq = val

    seq = max_seq + 1
    candidato = f"{prefixo}{seq:04d}"
    while qs.filter(codigo_escola__iexact=candidato).exists():
        seq += 1
        candidato = f"{prefixo}{seq:04d}"

    return candidato


def obter_codigos_orgaos_escola(codigo_escola: str) -> dict:
    """
    Para os códigos do Gabinete do Director, Direcção Pedagógica e Secretaria,
    inicia pelas letras (GD, DP, SECR) e em seguida o código da escola.
    """
    cod = (codigo_escola or '0101S0001').strip().upper()
    return {
        'gabinete_director': f"GD{cod}",
        'direccao_pedagogica': f"DP{cod}",
        'secretaria': f"SECR{cod}",
    }


def extrair_codigo_classe_2d(classe_str: str) -> str:
    """Extrai o número da classe com 2 dígitos (ex: '12ª Classe' -> '12', '7ª Classe' -> '07')."""
    import re
    m = re.search(r'(\d+)', str(classe_str or ''))
    if m:
        num = int(m.group(1))
        return f"{num:02d}"
    return '10'


def extrair_codigo_turma_2d(turma_nome: str, grau_ano: str = '') -> str:
    """Extrai o número da turma com 2 dígitos (ex: 'Turma 1' -> '01', 'Turma B' -> '02')."""
    import re
    if not turma_nome:
        return '01'
    limpo = str(turma_nome).strip()
    m_num = re.search(r'turma\s*(\d+)', limpo, re.IGNORECASE)
    if m_num:
        return f"{int(m_num.group(1)):02d}"
    m_let = re.search(r'turma\s*([a-zA-Z])\b', limpo, re.IGNORECASE)
    if m_let:
        idx = ord(m_let.group(1).upper()) - ord('A') + 1
        return f"{max(1, idx):02d}"

    # Remover o número da classe antes de procurar dígitos restantes
    resto = limpo
    if grau_ano:
        m_cls = re.search(r'(\d+)', str(grau_ano))
        if m_cls:
            resto = re.sub(rf'\b{m_cls.group(1)}[ªºa-zA-Z\s]*classe\b', '', resto, flags=re.IGNORECASE)
            resto = re.sub(rf'\b{m_cls.group(1)}[ªº]\b', '', resto, flags=re.IGNORECASE)

    nums = re.findall(r'\d+', resto)
    if nums:
        return f"{int(nums[-1]):02d}"

    letras = re.findall(r'\b([a-zA-Z])\b', resto)
    if letras:
        idx = ord(letras[-1].upper()) - ord('A') + 1
        return f"{max(1, idx):02d}"

    return '01'


def obter_sigla_area_estudo(area: str, classe: str = '') -> str:
    """
    Retorna a sigla em minúsculas da área/secção de estudo:
    Exemplo:
    - 'Ciências com Geografia' -> 'cg'
    - 'Ciências com Biologia' -> 'cb'
    - 'Ciências com Desenho' -> 'cd'
    - 'Letras com Geografia' -> 'lg'
    - 'Letras com História' -> 'lh'
    - 'Ensino Geral' / 'Geral' -> 'eg'
    """
    a_norm = _normalizar_texto_sem_acentos(area)
    mapa_direto = {
        'ciencias com geografia': 'cg',
        'ciencias com biologia': 'cb',
        'ciencias com desenho': 'cd',
        'letras com geografia': 'lg',
        'letras com historia': 'lh',
        'ciencias': 'cn',
        'letras': 'lt',
        'geral': 'eg',
        'ensino geral': 'eg',
        'tronco comum': 'eg',
        '': 'eg',
    }
    if a_norm in mapa_direto:
        return mapa_direto[a_norm]

    # Se já for uma sigla curta (ex: 'cg', 'cb', 'cd')
    if 1 <= len(a_norm) <= 4 and a_norm.isalpha():
        return a_norm

    stopwords = {'com', 'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'para', 'a', 'o', 'na', 'no'}
    palavras = [p for p in a_norm.replace('-', ' ').replace('/', ' ').split() if p and p not in stopwords]
    if len(palavras) >= 2:
        return ''.join(p[0] for p in palavras).lower()
    elif len(palavras) == 1:
        return palavras[0][:2].lower()
    return 'eg'


def gerar_codigo_aluno_oficial(escola=None, classe: str = None, turma=None, ano: str = None, area: str = None, aluno_id=None, numero=None, matricula_existente: str = None) -> str:
    """
    Gera o código oficial único do aluno associando:
    CodigoEscola + Classe + Turma + Ano + Area/Secção de estudo + Número sequencial do aluno na turma
    Exemplo: 0101S0001.12.01.2026.cg.01
    Garante que nenhum aluno tenha código duplicado na mesma turma/escola.
    """
    import datetime
    cod_escola = '0101S0001'
    if escola:
        if getattr(escola, 'codigo_escola', None):
            cod_escola = escola.codigo_escola.strip().upper()
        else:
            cod_escola = gerar_codigo_unico_escola(
                getattr(escola, 'provincia', 'Cidade de Maputo'),
                getattr(escola, 'distrito', 'KaMpfumo'),
                getattr(escola, 'tipo_escola', 'S'),
                getattr(escola, 'nome', ''),
                exclude_escola_id=getattr(escola, 'id', None)
            )

    cls_str = classe or (getattr(turma, 'grau_ano', None) if turma else None) or '10ª Classe'
    cod_classe = extrair_codigo_classe_2d(cls_str)

    if turma:
        t_nome = getattr(turma, 'nome', '') if not isinstance(turma, str) else turma
        t_grau = getattr(turma, 'grau_ano', cls_str) if not isinstance(turma, str) else cls_str
        cod_turma = extrair_codigo_turma_2d(t_nome, t_grau)
    else:
        cod_turma = '01'

    ano_str = str(
        ano
        or (getattr(turma, 'ano_letivo', None) if turma and not isinstance(turma, str) else None)
        or (getattr(escola, 'ano_letivo_ativo', None) if escola else None)
        or datetime.date.today().year
    ).strip()

    area_str = area
    if not area_str or _normalizar_texto_sem_acentos(area_str) in ['', 'geral', 'ensino geral', 'tronco comum', 'none']:
        if turma and not isinstance(turma, str) and getattr(turma, 'area', None):
            area_str = turma.area
    sigla_area = obter_sigla_area_estudo(area_str or 'Geral', cls_str)

    base_prefix = f"{cod_escola}.{cod_classe}.{cod_turma}.{ano_str}.{sigla_area}"

    # Se a matrícula existente já possui o base_prefix e sufixo numérico de ordem, preserva (desde que não colida globalmente)
    if matricula_existente and matricula_existente.startswith(base_prefix + '.'):
        partes = matricula_existente.split('.')
        if len(partes) >= 6 and partes[-1].isdigit():
            if not codigo_ja_existe_globalmente(matricula_existente, exclude_aluno_id=aluno_id):
                return matricula_existente

    if numero is not None and int(numero) > 0:
        cand_num = f"{base_prefix}.{int(numero):02d}"
        if not codigo_ja_existe_globalmente(cand_num, exclude_aluno_id=aluno_id):
            return cand_num

    # Buscar próximo número sequencial na turma/escola para garantir unicidade absoluta
    try:
        from apps.alunos.models import Aluno
        qs = Aluno.objects.filter(escola=escola, matricula__startswith=base_prefix)
        if aluno_id:
            qs = qs.exclude(id=aluno_id)

        numeros_usados = set()
        for mat in qs.values_list('matricula', flat=True):
            partes = (mat or '').split('.')
            if len(partes) >= 6 and partes[-1].isdigit():
                numeros_usados.add(int(partes[-1]))

        prox = 1
        # Garantir que o código não colide com NENHUM funcionário (professor, director, admin, etc.) nem outro aluno
        while prox in numeros_usados or codigo_ja_existe_globalmente(
            f"{base_prefix}.{prox:02d}",
            exclude_aluno_id=aluno_id,
        ):
            prox += 1
        return f"{base_prefix}.{prox:02d}"
    except Exception:
        return f"{base_prefix}.01"


def codigo_ja_existe_globalmente(codigo: str, exclude_aluno_id=None, exclude_prof_id=None, exclude_usuario_id=None, exclude_turma_id=None) -> bool:
    """
    Verifica se um código já existe em QUALQUER tabela do sistema (Aluno, Professor, Usuario ou Turma).
    Garante que nunca haja coincidência de código entre alunos e funcionários de qualquer tipo.

    Args:
        codigo: O código a verificar (case-insensitive).
        exclude_aluno_id:   UUID do aluno a excluir da verificação.
        exclude_prof_id:    UUID do professor a excluir da verificação.
        exclude_usuario_id: UUID do utilizador a excluir da verificação.
        exclude_turma_id:   UUID da turma a excluir da verificação (DT ou DC).

    Returns:
        True se o código já existe noutro registo; False se está disponível.
    """
    if not codigo:
        return False
    cod_clean = str(codigo).strip()

    try:
        from apps.alunos.models import Aluno
        qs_aluno = Aluno.objects.filter(matricula__iexact=cod_clean)
        if exclude_aluno_id:
            qs_aluno = qs_aluno.exclude(id=exclude_aluno_id)
        if qs_aluno.exists():
            return True
    except Exception:
        pass

    try:
        from apps.professores.models import Professor
        qs_prof = Professor.objects.filter(codigo__iexact=cod_clean)
        if exclude_prof_id:
            qs_prof = qs_prof.exclude(id=exclude_prof_id)
        if qs_prof.exists():
            return True
    except Exception:
        pass

    try:
        from apps.accounts.models import Usuario
        qs_user = Usuario.objects.filter(codigo_acesso__iexact=cod_clean)
        if exclude_usuario_id:
            qs_user = qs_user.exclude(id=exclude_usuario_id)
        if exclude_aluno_id:
            qs_user = qs_user.exclude(aluno_id=exclude_aluno_id)
        if exclude_prof_id:
            qs_user = qs_user.exclude(professor_id=exclude_prof_id)
        if qs_user.exists():
            return True
    except Exception:
        pass

    try:
        from apps.turmas.models import Turma
        from django.db.models import Q
        qs_turma = Turma.objects.filter(
            Q(codigo_director_turma__iexact=cod_clean) | Q(codigo_director_classe__iexact=cod_clean)
        )
        if exclude_turma_id:
            qs_turma = qs_turma.exclude(id=exclude_turma_id)
        if qs_turma.exists():
            return True
    except Exception:
        pass

    return False


def gerar_codigo_director_turma(turma) -> str:
    """
    Gera o código oficial do Director de Turma (após nomeação pelo DP e homologação pelo Director da Escola).
    Formato: DT{codigo_escola}.{classe}.{turma}.{ano}.{sigla_area}
    Exemplo: DT0101S0001.12.01.2026.cg
    """
    escola = getattr(turma, 'escola', None)
    cod_escola = (getattr(escola, 'codigo_escola', None) or '0101S0001').strip().upper()
    cod_classe = extrair_codigo_classe_2d(getattr(turma, 'grau_ano', '10ª Classe'))
    cod_turma = extrair_codigo_turma_2d(getattr(turma, 'nome', 'Turma 1'), getattr(turma, 'grau_ano', ''))
    ano_str = str(getattr(turma, 'ano_letivo', None) or (getattr(escola, 'ano_letivo_ativo', None) if escola else '2026') or '2026').strip()
    sigla_area = obter_sigla_area_estudo(getattr(turma, 'area', 'Geral'), getattr(turma, 'grau_ano', ''))
    return f"DT{cod_escola}.{cod_classe}.{cod_turma}.{ano_str}.{sigla_area}"


def gerar_codigo_director_classe(turma) -> str:
    """
    Gera o código oficial do Director de Classe (após nomeação pelo DP e homologação pelo Director da Escola).
    Formato: DC{codigo_escola}.{classe}.{ano}
    Exemplo: DC0101S0001.12.2026
    """
    escola = getattr(turma, 'escola', None)
    cod_escola = (getattr(escola, 'codigo_escola', None) or '0101S0001').strip().upper()
    cod_classe = extrair_codigo_classe_2d(getattr(turma, 'grau_ano', '10ª Classe'))
    ano_str = str(getattr(turma, 'ano_letivo', None) or (getattr(escola, 'ano_letivo_ativo', None) if escola else '2026') or '2026').strip()
    return f"DC{cod_escola}.{cod_classe}.{ano_str}"


def gerar_codigo_fixo_professor(escola, exclude_prof_id=None) -> str:
    """
    Gera um código fixo e permanente para o Professor na escola.
    Formato: PR{codigo_escola}.{sequencia:03d} (Exemplo: PR0101S0001.001)
    Não se altera quando o professor muda de turma, classe ou ano lectivo.
    """
    import re
    from apps.professores.models import Professor

    cod_escola = (getattr(escola, 'codigo_escola', None) or '0101S0001').strip().upper()
    prefixo = f"PR{cod_escola}."

    qs = Professor.objects.filter(escola=escola) if escola else Professor.objects.all()
    if exclude_prof_id:
        qs = qs.exclude(id=exclude_prof_id)

    max_seq = 0
    for p in qs.filter(codigo__istartswith=prefixo):
        c = (p.codigo or '').strip()
        resto = c[len(prefixo):]
        m = re.match(r'^(\d+)$', resto)
        if m:
            val = int(m.group(1))
            if val > max_seq:
                max_seq = val

    seq = max_seq + 1
    cand = f"{prefixo}{seq:03d}"
    # Verificar também colisão global com matrículas de alunos e codigo_acesso de outros utilizadores
    while (
        Professor.objects.exclude(id=exclude_prof_id).filter(codigo__iexact=cand).exists()
        or codigo_ja_existe_globalmente(cand, exclude_prof_id=exclude_prof_id)
    ):
        seq += 1
        cand = f"{prefixo}{seq:03d}"
    return cand


def sincronizar_todos_codigos_oficiais() -> dict:
    """
    Sincroniza e preenche todos os códigos oficiais (Escolas, GD/DP/SECR, Professores, DT/DC e Alunos)
    na base de dados para garantir conformidade imediata em ambientes existentes.
    """
    import re
    from apps.tenants.models import Escola
    from apps.accounts.models import Usuario
    from apps.professores.models import Professor
    from apps.turmas.models import Turma
    from apps.alunos.models import Aluno

    resumo = {
        'escolas': 0,
        'usuarios': 0,
        'professores': 0,
        'turmas': 0,
        'alunos': 0,
    }

    padrao_escola = re.compile(r'^\d{4}[PBS]\d{4,5}$')
    for esc in Escola.objects.all().order_by('created_at'):
        mudou = False
        if not esc.tipo_escola:
            esc.tipo_escola = obter_letra_tipo_escola(None, esc.nome)
            mudou = True
        cod_atual = (esc.codigo_escola or '').strip().upper()
        if not cod_atual or not padrao_escola.match(cod_atual):
            esc.codigo_escola = gerar_codigo_unico_escola(
                esc.provincia or 'Cidade de Maputo',
                esc.distrito or 'KaMpfumo',
                esc.tipo_escola,
                esc.nome,
                exclude_escola_id=esc.id
            )
            mudou = True
        if mudou:
            esc.save()
        resumo['escolas'] += 1

    for prof in Professor.objects.select_related('escola').all().order_by('created_at'):
        cod_esc = (prof.escola.codigo_escola if prof.escola else '0101S0001').strip().upper()
        if not prof.codigo or not prof.codigo.upper().startswith(f"PR{cod_esc}."):
            prof.codigo = gerar_codigo_fixo_professor(prof.escola, exclude_prof_id=prof.id)
            prof.save(update_fields=['codigo', 'updated_at'])
        Usuario.objects.filter(escola=prof.escola, email__iexact=prof.email, role='PROFESSOR').exclude(codigo_acesso=prof.codigo).update(codigo_acesso=prof.codigo)
        resumo['professores'] += 1

    from apps.tenants.views import garantir_contas_institucionais_escola
    for esc in Escola.objects.all():
        garantir_contas_institucionais_escola(esc)
        cod_esc = (esc.codigo_escola or '0101S0001').strip().upper()
        resumo['usuarios'] += Usuario.objects.filter(escola=esc, role__in=['ADMIN_ESCOLA', 'DIRECTOR_ESCOLA']).exclude(codigo_acesso=f"GD{cod_esc}").update(codigo_acesso=f"GD{cod_esc}")
        resumo['usuarios'] += Usuario.objects.filter(escola=esc, role='DAP').exclude(codigo_acesso=f"DP{cod_esc}").update(codigo_acesso=f"DP{cod_esc}")
        resumo['usuarios'] += Usuario.objects.filter(escola=esc, role__in=['CHEFE_SECRETARIA', 'ADMINISTRATIVO']).exclude(codigo_acesso=f"SECR{cod_esc}").update(codigo_acesso=f"SECR{cod_esc}")

    from django.db.models import Q
    for t in Turma.objects.select_related('escola', 'director_turma', 'director_classe').filter(
        Q(director_turma__isnull=False) | Q(director_classe__isnull=False)
    ):
        t.save()
        resumo['turmas'] += 1

    for a in Aluno.objects.select_related('escola', 'turma').all():
        novo_cod = gerar_codigo_aluno_oficial(
            escola=a.escola,
            classe=a.classe,
            turma=a.turma,
            ano=a.ano_ingresso,
            area=a.area,
            aluno_id=a.id,
            matricula_existente=a.matricula,
        )
        if a.matricula != novo_cod:
            Aluno.objects.filter(id=a.id).update(matricula=novo_cod)
        Usuario.objects.filter(aluno_id=a.id).exclude(codigo_acesso=novo_cod).update(codigo_acesso=novo_cod)
        resumo['alunos'] += 1

    return resumo


