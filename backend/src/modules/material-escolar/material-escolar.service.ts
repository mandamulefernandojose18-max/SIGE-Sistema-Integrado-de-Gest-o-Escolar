import prisma from '../../config/database';

export class MaterialEscolarService {
  async list(escolaId: string, filtros?: { classe?: string; disciplinaId?: string; search?: string }) {
    const where: any = {
      escola_id: escolaId
    };

    if (filtros?.classe && filtros.classe !== 'TODAS') {
      where.classe = filtros.classe;
    }

    if (filtros?.disciplinaId) {
      where.disciplina_id = filtros.disciplinaId;
    }

    if (filtros?.search) {
      where.OR = [
        { titulo: { contains: filtros.search } },
        { descricao: { contains: filtros.search } },
        { nome_arquivo: { contains: filtros.search } }
      ];
    }

    return prisma.materialEscolar.findMany({
      where,
      include: {
        disciplina: {
          select: { id: true, nome: true, codigo: true }
        }
      },
      orderBy: [
        { classe: 'asc' },
        { createdAt: 'desc' }
      ]
    });
  }

  async getById(escolaId: string, id: string) {
    return prisma.materialEscolar.findFirst({
      where: { id, escola_id: escolaId },
      include: {
        disciplina: {
          select: { id: true, nome: true, codigo: true }
        }
      }
    });
  }

  async create(escolaId: string, dados: {
    classe: string;
    disciplina_id?: string | null;
    titulo: string;
    descricao?: string | null;
    tipo?: string;
    nome_arquivo?: string;
    extensao?: string;
    tamanho_bytes?: number;
    conteudo_base64?: string | null;
    tipo_mime?: string | null;
    arquivo_url?: string | null;
    publicado_por?: string | null;
  }) {
    const extensao = dados.extensao || (dados.nome_arquivo ? dados.nome_arquivo.split('.').pop() || 'pdf' : 'pdf');
    const nome_arquivo = dados.nome_arquivo || `${dados.titulo.replace(/[^a-zA-Z0-9]/g, '_')}.${extensao}`;

    return prisma.materialEscolar.create({
      data: {
        escola_id: escolaId,
        classe: dados.classe,
        disciplina_id: dados.disciplina_id || null,
        titulo: dados.titulo,
        descricao: dados.descricao || null,
        tipo: dados.tipo || 'MANUAL',
        nome_arquivo,
        extensao: extensao.toLowerCase(),
        tamanho_bytes: dados.tamanho_bytes || 0,
        conteudo_base64: dados.conteudo_base64 || null,
        tipo_mime: dados.tipo_mime || (extensao === 'pdf' ? 'application/pdf' : 'application/octet-stream'),
        arquivo_url: dados.arquivo_url || null,
        publicado_por: dados.publicado_por || 'Docente / Administração'
      },
      include: {
        disciplina: true
      }
    });
  }

  async delete(escolaId: string, id: string) {
    return prisma.materialEscolar.deleteMany({
      where: { id, escola_id: escolaId }
    });
  }

  async getClassesDisponiveis(escolaId: string) {
    const classesPadrao = [
      '1ª Classe', '2ª Classe', '3ª Classe', '4ª Classe', '5ª Classe', '6ª Classe',
      '7ª Classe', '8ª Classe', '9ª Classe', '10ª Classe', '11ª Classe', '12ª Classe'
    ];

    // Contagem de materiais por classe
    const materiaisPorClasse = await prisma.materialEscolar.groupBy({
      by: ['classe'],
      where: { escola_id: escolaId },
      _count: { id: true }
    });

    const mapaContagem = new Map<string, number>();
    materiaisPorClasse.forEach(item => {
      mapaContagem.set(item.classe, item._count.id);
    });

    return classesPadrao.map(classe => ({
      classe,
      totalMateriais: mapaContagem.get(classe) || 0
    }));
  }
}
