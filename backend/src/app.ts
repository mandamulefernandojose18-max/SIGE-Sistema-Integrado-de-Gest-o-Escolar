import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import compression from 'compression';

import { errorHandler } from './middlewares/error.middleware';

import authRouter from './modules/auth/auth.routes';
import saasAdminRouter from './modules/saas-admin/saas-admin.routes';
import escolaAdminRouter from './modules/escola-admin/escola-admin.routes';
import alunosRouter from './modules/alunos/alunos.routes';
import professoresRouter from './modules/professores/professores.routes';
import disciplinasRouter from './modules/disciplinas/disciplinas.routes';
import notasRouter from './modules/notas/notas.routes';
import pautasRouter from './modules/pautas/pautas.routes';
import certificadosRouter from './modules/certificados/certificados.routes';
import pagamentosRouter from './modules/pagamentos/pagamentos.routes';
import impressaoRouter from './modules/impressao/impressao.routes';
import dashboardRouter from './modules/dashboard/dashboard.routes';
import materialEscolarRouter from './modules/material-escolar/material-escolar.routes';

const app = express();

// Middlewares de Segurança e Otimização
app.use(helmet({
  contentSecurityPolicy: false // Permite carregar bibliotecas CDN (Bootstrap, Chart.js, Lucide) no dashboard
}));
// Configuração de CORS para suportar clientes Web SPA, Mobile e Ferramentas
const allowedOrigins = process.env.CORS_ORIGIN
  ? process.env.CORS_ORIGIN.split(',').map(o => o.trim())
  : ['http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:80', 'http://localhost:3000'];

app.use(cors({
  origin: (origin, callback) => {
    if (!origin || allowedOrigins.includes(origin) || allowedOrigins.includes('*')) {
      return callback(null, true);
    }
    return callback(new Error(`Origem '${origin}' não autorizada por política de CORS`));
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'x-tenant-id']
}));

app.use(compression());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

if (process.env.NODE_ENV !== 'test') {
  app.use(morgan('dev'));
}

// Rota de Healthcheck
app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    service: 'SIGE — Sistema Integrado de Gestão Escolar (SaaS Multi-Tenant)'
  });
});

// Rotas da API RESTful v1
const api = express.Router();
api.use('/auth', authRouter);
api.use('/saas-admin', saasAdminRouter);
api.use('/escola-admin', escolaAdminRouter);
api.use('/alunos', alunosRouter);
api.use('/professores', professoresRouter);
api.use('/disciplinas', disciplinasRouter);
api.use('/notas', notasRouter);
api.use('/pautas', pautasRouter);
api.use('/certificados', certificadosRouter);
api.use('/pagamentos', pagamentosRouter);
api.use('/impressao', impressaoRouter);
api.use('/dashboard', dashboardRouter);
api.use('/material-escolar', materialEscolarRouter);
import {
  PROVINCIAS_MOCAMBIQUE,
  DISTRITOS_POR_PROVINCIA,
  CARREIRAS_DOCENTES,
  TIPOS_DOCUMENTO,
  ANOTACOES_STATUS,
  COMPORTAMENTOS
} from './utils/geografia-mocambique';

api.get('/geografia', (req, res) => {
  res.json({
    success: true,
    data: {
      provincias: PROVINCIAS_MOCAMBIQUE,
      distritos: DISTRITOS_POR_PROVINCIA,
      carreiras: CARREIRAS_DOCENTES,
      tiposDocumento: TIPOS_DOCUMENTO,
      anotacoes: ANOTACOES_STATUS,
      comportamentos: COMPORTAMENTOS
    }
  });
});

app.use('/api/v1', api);

// Middleware centralizado de tratamento de erros
app.use(errorHandler);

export default app;
