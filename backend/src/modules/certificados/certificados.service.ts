import crypto from 'crypto';
import prisma from '../../config/database';
import { generateQrCodeDataUrl } from '../../utils/qrcode.util';
import { env } from '../../config/env';

export class CertificadosService {
  async list(escolaId: string, tipo?: string) {
    return prisma.certificado.findMany({
      where: {
        escola_id: escolaId,
        ...(tipo ? { tipo } : {})
      },
      include: {
        aluno: {
          include: { turma: true }
        }
      },
      orderBy: { emitido_em: 'desc' }
    });
  }

  async getById(escolaId: string, id: string) {
    return prisma.certificado.findFirst({
      where: { id, escola_id: escolaId },
      include: {
        aluno: {
          include: { turma: true, notas: { include: { disciplina: true } } }
        },
        escola: true
      }
    });
  }

  async emitir(escolaId: string, dados: {
    aluno_id: string;
    tipo: 'CONCLUSAO' | 'TRANSFERENCIA' | 'MATRICULA';
    emitido_por?: string;
  }) {
    const aluno = await prisma.aluno.findFirst({
      where: { id: dados.aluno_id, escola_id: escolaId },
      include: { escola: true, turma: true }
    });

    if (!aluno) throw new Error('Aluno não encontrado na escola');

    // Gerar código único de autenticidade (UUID)
    const codigoAutenticidade = crypto.randomUUID();

    // URL pública para verificação através do QR Code
    const verificationUrl = `${env.APP_URL}/verificar-certificado.html?codigo=${codigoAutenticidade}`;

    // Gerar o QR Code em Data URL
    const qrcodeData = await generateQrCodeDataUrl(verificationUrl);

    return prisma.certificado.create({
      data: {
        escola_id: escolaId,
        aluno_id: dados.aluno_id,
        tipo: dados.tipo,
        codigo_autenticidade: codigoAutenticidade,
        qrcode_data: qrcodeData,
        emitido_por: dados.emitido_por || 'Secretaria Escolar'
      },
      include: {
        aluno: { include: { turma: true } },
        escola: true
      }
    });
  }

  // Verificação Pública do Certificado pelo QR Code
  async verificarAutenticidade(codigo: string) {
    const certificado = await prisma.certificado.findUnique({
      where: { codigo_autenticidade: codigo },
      include: {
        escola: {
          select: {
            nome: true,
            nif_cnpj: true,
            email: true,
            telefone: true,
            status: true
          }
        },
        aluno: {
          select: {
            nome: true,
            matricula: true,
            numero_documento: true,
            nuit: true,
            data_nascimento: true,
            turma: { select: { nome: true, grau_ano: true } }
          }
        }
      }
    });

    if (!certificado) {
      return {
        autentico: false,
        mensagem: 'Certificado não encontrado ou código de verificação inválido.'
      };
    }

    return {
      autentico: true,
      mensagem: 'Certificado autêntico e registrado oficialmente no SIGE.',
      certificado: {
        codigo: certificado.codigo_autenticidade,
        tipo: certificado.tipo,
        emitido_em: certificado.emitido_em,
        emitido_por: certificado.emitido_por,
        aluno: certificado.aluno,
        escola: certificado.escola
      }
    };
  }

  async getStats(escolaId: string) {
    const certificados = await prisma.certificado.findMany({
      where: { escola_id: escolaId },
      select: { tipo: true, emitido_em: true }
    });

    const porTipo: Record<string, number> = {
      CONCLUSAO: 0,
      TRANSFERENCIA: 0,
      MATRICULA: 0
    };

    // Estatísticas dos últimos 6 meses
    const hoje = new Date();
    const mesesGrafico: Record<string, number> = {};
    for (let i = 5; i >= 0; i--) {
      const d = new Date(hoje.getFullYear(), hoje.getMonth() - i, 1);
      const chave = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      mesesGrafico[chave] = 0;
    }

    certificados.forEach(c => {
      porTipo[c.tipo] = (porTipo[c.tipo] || 0) + 1;

      const mesChave = `${c.emitido_em.getFullYear()}-${String(c.emitido_em.getMonth() + 1).padStart(2, '0')}`;
      if (mesesGrafico[mesChave] !== undefined) {
        mesesGrafico[mesChave]++;
      }
    });

    return {
      totalEmitidos: certificados.length,
      porTipo,
      historicoMensal: mesesGrafico
    };
  }
}

export const certificadosService = new CertificadosService();
