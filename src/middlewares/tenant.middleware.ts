import { Request, Response, NextFunction } from 'express';
import prisma from '../config/database';
import { sendError } from '../utils/response.util';

export async function tenantMiddleware(req: Request, res: Response, next: NextFunction) {
  try {
    const user = req.user;
    if (!user) {
      return sendError(res, 'Acesso não autenticado', 401, 'UNAUTHORIZED');
    }

    // SuperAdmin pode operar sem tenant vinculado ou especificar X-Tenant-ID para navegar
    let targetEscolaId = user.escola_id;
    const headerTenantId = req.headers['x-tenant-id'] as string;

    if (user.role === 'SUPERADMIN') {
      if (headerTenantId) {
        targetEscolaId = headerTenantId;
      } else {
        // SuperAdmin acessando rotas de nível de plataforma
        return next();
      }
    }

    if (!targetEscolaId) {
      return sendError(res, 'Nenhum contexto de escola (Tenant) associado à requisição', 400, 'TENANT_NOT_FOUND');
    }

    // Buscar a escola e a assinatura mais recente
    const escola = await prisma.escola.findUnique({
      where: { id: targetEscolaId },
      include: {
        assinaturas: {
          orderBy: { data_fim: 'desc' },
          take: 1
        }
      }
    });

    if (!escola) {
      return sendError(res, 'Escola não encontrada no sistema', 404, 'TENANT_NOT_FOUND');
    }

    // VERIFICAÇÃO CHAVE DE EXPIRAÇÃO (HTTP 402)
    // Se o status da escola for EXPIRADA ou se a data de vencimento da assinatura já passou
    const ultimaAssinatura = escola.assinaturas[0];
    const agora = new Date();
    const expiradaPorData = ultimaAssinatura && new Date(ultimaAssinatura.data_fim) < agora;

    if (escola.status === 'EXPIRADA' || (expiradaPorData && escola.status !== 'ATIVA')) {
      // Registrar log de acesso bloqueado
      await prisma.logAcesso.create({
        data: {
          escola_id: escola.id,
          usuario_id: user.id,
          ip: (req.headers['x-forwarded-for'] as string) || req.ip || '127.0.0.1',
          user_agent: req.headers['user-agent'] || 'Desconhecido',
          tipo: 'ACESSO_BLOQUEADO_EXPIRADO'
        }
      }).catch(() => {});

      // SuperAdmin tem permissão para visualizar até escolas expiradas caso deseje
      if (user.role !== 'SUPERADMIN') {
        return res.status(402).json({
          success: false,
          error: 'PAYMENT_REQUIRED',
          message: 'Assinatura expirada. Entre em contato com a administração do sistema para renovação.',
          escola: {
            id: escola.id,
            nome: escola.nome,
            status: 'EXPIRADA',
            data_expiracao: ultimaAssinatura ? ultimaAssinatura.data_fim : null
          }
        });
      }
    }

    if (escola.status === 'SUSPENSA' && user.role !== 'SUPERADMIN') {
      return sendError(res, 'Esta escola encontra-se temporariamente suspensa.', 403, 'TENANT_SUSPENDED');
    }

    // Injeta o contexto do tenant na requisição
    req.tenant = {
      id: escola.id,
      nome: escola.nome,
      status: escola.status as any,
      ano_letivo_ativo: escola.ano_letivo_ativo
    };

    next();
  } catch (error) {
    console.error('Erro no middleware de Tenant:', error);
    return sendError(res, 'Falha interna ao validar tenant da escola', 500, 'INTERNAL_SERVER_ERROR');
  }
}
