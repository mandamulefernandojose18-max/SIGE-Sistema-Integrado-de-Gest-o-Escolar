"""
Constantes e Geografia Oficial da República de Moçambique (MINEDH)
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
