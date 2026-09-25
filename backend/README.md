# SIGE Backend — API RESTful (Moçambique)

API RESTful construída em Node.js, Express, TypeScript e Prisma ORM para gestão escolar em conformidade com as normas do Ministério da Educação e Desenvolvimento Humano (MINEDH) de Moçambique.

## Arquitetura e Recursos
- **Multi-Tenant Corporativo**: isolamento por escola e bloqueio automático por expiração (HTTP 402).
- **Autenticação RBAC**: papéis nominais (SUPERADMIN, DIRECTOR_ESCOLA, DAP, CHEFE_SECRETARIA, PROFESSOR, ALUNO).
- **Avaliações Moçambique**: cálculo oficial de médias trimestrais e anuais, anotações (D, T, VT, F, AM, PPF, PDF), comportamentos e arredondamento a inteiros.
- **Central de Impressão e Exportação**:
  - Geração nativa OpenXML (.xlsx).
  - Emissão de relatórios em Word (.docx) e PDF oficial (PDFKit).
  - Geração e download em JSON (.json).
- **Módulo de Material Escolar**: gestão de estoques, categorias e requisições escolares.
- **CORS Habilitado e Parametrizável**: configurado via variável `CORS_ORIGIN`.

## Como Executar
```bash
# Instalar dependências
npm install

# Gerar cliente do Prisma
npm run prisma:generate

# Aplicar schema no banco de dados
npm run prisma:push

# Iniciar servidor em desenvolvimento
npm run dev

# Compilar e iniciar em produção
npm run build
npm start
```

Servidor disponível em: `http://localhost:3000`  
Healthcheck: `http://localhost:3000/health`

## Testes Automatizados
```bash
npm test
```
