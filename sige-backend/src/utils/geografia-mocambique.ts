export const PROVINCIAS_MOCAMBIQUE = [
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
] as const;

export type ProvinciaMocambique = typeof PROVINCIAS_MOCAMBIQUE[number];

export const DISTRITOS_POR_PROVINCIA: Record<string, string[]> = {
  'Cidade de Maputo': [
    'KaMpfumo',
    'Nlhamankulu',
    'KaMaxakeni',
    'KaMavota',
    'KaMubukwana',
    'KaTembe',
    'KaNyaka'
  ],
  'Província de Maputo': [
    'Boane',
    'Magude',
    'Manhiça',
    'Marracuene',
    'Matola',
    'Matutuíne',
    'Moamba',
    'Namaacha'
  ],
  'Gaza': [
    'Bilene',
    'Chibuto',
    'Chicualacuala',
    'Chigubo',
    'Chókwè',
    'Chongoene',
    'Guijá',
    'Limpopo',
    'Mabalane',
    'Manjacaze',
    'Massangena',
    'Massingir',
    'Xai-Xai'
  ],
  'Inhambane': [
    'Funhalouro',
    'Govuro',
    'Homoíne',
    'Inhambane',
    'Inharrime',
    'Inhassoro',
    'Jangamo',
    'Mabote',
    'Massinga',
    'Maxixe',
    'Morrumbene',
    'Mupaculane',
    'Panda',
    'Vilankulo',
    'Zavala'
  ],
  'Manica': [
    'Bárue',
    'Chimoio',
    'Gondola',
    'Guro',
    'Macate',
    'Machaze',
    'Macossa',
    'Manica',
    'Mossurize',
    'Sussundenga',
    'Tambara',
    'Vanduzi'
  ],
  'Sofala': [
    'Beira',
    'Búzi',
    'Caia',
    'Chemba',
    'Cheringoma',
    'Chibabava',
    'Dondo',
    'Gorongosa',
    'Machanga',
    'Marínguè',
    'Marromeu',
    'Muanza',
    'Nhamatanda'
  ],
  'Tete': [
    'Angónia',
    'Cahora-Bassa',
    'Changara',
    'Chifunde',
    'Chiuta',
    'Dôa',
    'Macanga',
    'Magoé',
    'Marara',
    'Marávia',
    'Moatize',
    'Mutarara',
    'Tete',
    'Tsangano',
    'Zumbo'
  ],
  'Zambézia': [
    'Alto Molócue',
    'Chinde',
    'Derre',
    'Gilé',
    'Gurué',
    'Ile',
    'Inhassunge',
    'Luabo',
    'Lugela',
    'Maganja da Costa',
    'Milange',
    'Mocuba',
    'Mocubela',
    'Molumbo',
    'Mopeia',
    'Morrumbala',
    'Mulevala',
    'Namacurra',
    'Namarroi',
    'Nicoadala',
    'Pebane',
    'Quelimane'
  ],
  'Nampula': [
    'Angoche',
    'Eráti',
    'Ilha de Moçambique',
    'Lalaua',
    'Larde',
    'Liúpo',
    'Malema',
    'Meconta',
    'Mecubúri',
    'Memba',
    'Mogincual',
    'Mogovolas',
    'Moma',
    'Monapo',
    'Mossuril',
    'Muecate',
    'Murrupula',
    'Nacala-a-Velha',
    'Nacala Porto',
    'Nampula',
    'Ribaue'
  ],
  'Niassa': [
    'Cuamba',
    'Lago',
    'Lichinga',
    'Majune',
    'Mandimba',
    'Marrupa',
    'Maúa',
    'Mavago',
    'Mecanhelas',
    'Mecula',
    'Metarica',
    'Muembe',
    'N\'gauma',
    'Nipepe',
    'Sanga'
  ],
  'Cabo Delgado': [
    'Ancuabe',
    'Balama',
    'Chiúre',
    'Ibo',
    'Macomia',
    'Mecúfi',
    'Meluco',
    'Metuge',
    'Mocímboa da Praia',
    'Montepuez',
    'Mueda',
    'Muidumbe',
    'Namuno',
    'Nangade',
    'Palma',
    'Pemba',
    'Quissanga'
  ]
};

export const CARREIRAS_DOCENTES = [
  'DN4',
  'DN3',
  'DN2',
  'DN1',
  'Especialista de Educação',
  'Mestre',
  'Professor Doutor'
] as const;

export const TIPOS_DOCUMENTO = [
  'Bilhete de Identidade',
  'Passaporte',
  'Carta de Condução',
  'Cédula Pessoal'
] as const;

export const ANOTACOES_SITUACAO = {
  D: 'Desistiu',
  T: 'Transferido',
  VT: 'Vem Transferido',
  F: 'Faleceu',
  AM: 'Anulou Matrícula',
  PPF: 'Perdeu o Ano por Faltas',
  PDF: 'Perdeu Direito por Faltas'
} as const;

export const ANOTACOES_STATUS = ANOTACOES_SITUACAO;

export const COMPORTAMENTOS = [
  { codigo: 'NS', nome: 'Não Suficiente' },
  { codigo: 'S', nome: 'Suficiente' },
  { codigo: 'B', nome: 'Bom' },
  { codigo: 'MB', nome: 'Muito Bom' },
  { codigo: 'E', nome: 'Excelente' }
] as const;

export function obterDistritosPorProvincia(provincia: string): string[] {
  return DISTRITOS_POR_PROVINCIA[provincia] || [];
}
