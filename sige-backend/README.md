# SIGE - Back-End (API RESTful Moçambique)

API RESTful pura construída em Node.js, Express, TypeScript e Prisma ORM para gestão escolar segundo as normas do Ministério da Educação e Desenvolvimento Humano (MINEDH) de Moçambique.

## Arquitetura e Módulos
- **Multi-Tenant**: isolamento de dados por instituição com bloqueio automático por expiração (HTTP 402).
- **Autenticação RBAC**: papéis nominais (SUPERADMIN, DIRECTOR_ESCOLA, DAP, CHEFE_SECRETARIA, PROFESSOR, ALUNO).
- **Avaliações Moçambique**: cálculo oficial de médias, anotações (D, T, VT, F, AM, PPF, PDF), comportamentos e arredondamento a inteiros.
- **Central de Impressão e Exportação**:
  - Geração nativa OpenXML (.xlsx) com formatação A4.
  - Geração e download em **JSON** (.json).
  - Persistência e auditoria de snapshots JSON no banco de dados (`DocumentoSalvo` e `LogImpressao`).
- **CORS Habilitado**: integração direta com aplicações front-end web e mobile.

## Como Executar
```bash
# Instalar dependências (caso não existam)
npm install

# Executar migrações do Prisma
npm run prisma:push

# Iniciar servidor em desenvolvimento
npm run dev

# Compilar e iniciar em produção
npm run build
npm start
```
Servidor disponível em: [http://localhost:3000](http://localhost:3000)

## Testes Automatizados
```bash
npm test
```
