# SIGE — Backend Django REST Framework (SaaS Multi-Tenant)

## Visão Geral
Backend oficial do **SIGE — Sistema Integrado de Gestão Escolar**, reestruturado em **Python 3.12**, **Django 5.1** e **Django REST Framework (DRF)** com suporte a **PostgreSQL**, arquitetura **SaaS Multi-Tenant** e conformidade integral com as normas e avaliações do **MINEDH (Ministério da Educação e Desenvolvimento Humano de Moçambique)**.

---

## Estrutura de Diretórios

```
backend/
├── apps/
│   ├── accounts/          # Autenticação JWT, Usuários personalizados e RBAC
│   ├── tenants/           # Escolas, Planos SaaS e Assinaturas
│   ├── alunos/            # Gestão e Matrículas de Estudantes
│   ├── professores/       # Docentes e Alocações
│   ├── turmas/            # Turmas, Classes e Salas
│   ├── disciplinas/       # Matriz Curricular
│   ├── notas/             # Lançamento e Bloqueio de Notas Trimestrais
│   ├── pautas/            # Consolidação de Pautas e Atas Oficiais
│   ├── material_escolar/  # Manuais e Recursos Didáticos
│   ├── documentos/        # Emissão de PDFs, XLSX, DOCX e Logs de Impressão
│   ├── pagamentos/        # Mensalidades e Recibos com QR Code
│   ├── certificados/      # Validação e Emissão de Certificados
│   └── dashboard/         # Métricas e Estatísticas Gerais
├── common/
│   ├── middleware/        # TenantMiddleware e TenantExpirationMiddleware (HTTP 402)
│   ├── permissions/       # RBAC (SuperAdmin, EscolaAdmin, Professor, Aluno)
│   ├── pagination/        # Paginação padronizada DRF
│   └── utils/             # Regras oficiais do MINEDH e Geografia de Moçambique
├── config/
│   ├── settings/          # Configurações base, desenvolvimento e produção
│   ├── urls.py            # Roteamento centralizado (/api/v1/ e Swagger)
│   └── wsgi.py / asgi.py  # Entrada de servidores WSGI e ASGI
├── tests/                 # Suite de testes automatizados com Pytest
├── requirements.txt       # Dependências de produção
├── requirements-dev.txt   # Dependências de teste e desenvolvimento
```

---

## Documentação Técnica Completa

A documentação detalhada e gerada automaticamente está organizada no diretório `docs/`:

- 📐 **[Arquitetura do Sistema](docs/ARCHITECTURE.md):** Padrões de design, fluxo de requisições, middlewares e isolamento multi-tenant.
- 🛡️ **[Regras de Integridade do Sistema](docs/REGRAS_DE_INTEGRIDADE.md):** Os 6 Pilares de Integridade, isolamento multi-tenant hermético, constraints de banco, imutabilidade de pautas e conformidade MINEDH.
- 📡 **[Referência Oficial de Endpoints da API](docs/API_REFERENCE.md):** Lista completa de rotas, métodos HTTP, permissões e requisitos de autenticação.
- 🗄️ **[Catálogo de Modelos de Dados](docs/DATABASE_MODELS.md):** Dicionário de dados, tipos de campos, chaves estrangeiras e relações do Django ORM.
- 🇲🇿 **[Regras Oficiais do MINEDH](docs/MINEDH_RULES.md):** Fórmulas de cálculo de médias, critérios de aprovação, regra da 12ª classe e anotações administrativas.
- 📑 **[OpenAPI 3.0 Schema](schema.yml):** Especificação OpenAPI em formato YAML para importação no Swagger, Postman ou Insomnia.

### Atualização Automática da Documentação (Gatilho)
Sempre que uma nova funcionalidade, modelo ou rota for adicionada, a documentação pode ser atualizada automaticamente:
```bash
# Via comando Django:
python manage.py update_docs

# Ou diretamente pelo script:
python scripts/update_docs.py
```
*O repositório já inclui um **Git Pre-Commit Hook** (`scripts/install_hooks.py`) e uma **GitHub Action** (`.github/workflows/docs-update.yml`) que sincronizam os ficheiros de documentação automaticamente em cada alteração.*

---

## Requisitos de Sistema
- **Python:** >= 3.12
- **PostgreSQL:** >= 16 (ou SQLite para desenvolvimento local)

---

## Configuração do Ambiente Local

1. **Criar e ativar o ambiente virtual:**
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

2. **Instalar as dependências:**
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```

3. **Configurar variáveis de ambiente:**
   Copie `.env.example` para `.env` e configure conforme necessário:
   ```bash
   cp .env.example .env
   ```

4. **Executar migrações do banco de dados:**
   ```bash
   python manage.py migrate
   ```

5. **Popular dados iniciais (Seed):**
   ```bash
   python manage.py seed
   ```

6. **Iniciar o servidor de desenvolvimento:**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

---

## Documentação Interativa da API
Com o servidor em execução, acesse no navegador:
- **Swagger UI:** `http://localhost:8000/api/docs/`
- **OpenAPI Schema (JSON/YAML):** `http://localhost:8000/api/schema/`
- **Health Check:** `http://localhost:8000/health/`

---

## Execução dos Testes Automatizados
O projeto utiliza `pytest` e `pytest-django`:
```bash
pytest -v
```

---

## Regras Oficiais MINEDH (Moçambique)
- **Média Trimestral:** $MT = \text{round}\left(\frac{2 \times MAC + AT}{3}\right)$, arredondado para número inteiro (0 a 20).
- **Aprovação na Pauta (Classes Gerais):** Requer 100% de positivas (0 negativas).
- **Aprovação na 12ª Classe:** Requer média geral $\ge 9.5$, até no máximo 2 negativas e nenhuma negativa inferior a 8 valores.
- **Bloqueio de Inadimplência:** Escolas com assinatura vencida recebem automaticamente status `HTTP 402 Payment Required` em rotas protegidas.
