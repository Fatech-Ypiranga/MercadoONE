# PyERP Backend

API REST de ERP para varejo: produtos, estoque, vendas, compras via NF-e, relatórios e auditoria. Stack: FastAPI, SQLModel e PostgreSQL.

## Como este monorepo se encaixa

| Componente | Repo | Papel |
|------------|------|--------|
| **API + painel web** | este (`pyerp`) | Contrato canônico; catálogo vive aqui; painel para testar a API |
| **Data Sim** | `pyerp-data-sim` (repo separado) | Gera dados fictícios e cadastra via API; XMLs de compra |
| **PDV** | `pyerp-pdv` (repo separado) | Simula caixa físico; vendas via API |

Contrato para integradores: [`docs/INTEGRACOES.md`](docs/INTEGRACOES.md) · OpenAPI: `/openapi.json` (ao vivo) ou [`docs/openapi.json`](docs/openapi.json) (snapshot).

## Pré-requisitos

- Python 3.11+
- Docker e Docker Compose
- Git

## Setup rápido

### 1. Subir o banco de dados

```bash
docker compose up -d
```

O PostgreSQL sobe na porta `5432` com:
- Banco principal: `erp_vendas`
- Banco de testes: `erp_vendas_test` (criado automaticamente via `scripts/init-test-db.sql`)

Opcional: pgAdmin em http://localhost:8080 (`admin@erp.com` / `admin`).

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Ajuste os valores conforme necessário. Em desenvolvimento, os defaults do `.env.example` funcionam — mas **defina `ADMIN_PASSWORD`** antes de subir a API.

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | Conexão do banco principal |
| `TEST_DATABASE_URL` | Conexão do banco de testes |
| `JWT_SECRET` | Chave para assinatura dos tokens JWT |
| `JWT_EXPIRE_HOURS` | Validade do token em horas |
| `ADMIN_*` | Credenciais do usuário admin seed |
| `ENV` | `development` ou `production` (gates de segurança) |
| `CORS_ORIGINS` | Origens permitidas (vírgula). Default: `http://localhost:3000` |
| `LOGIN_RATE_LIMIT` | Tentativas de login por IP/janela (default 10) |
| `LOGIN_RATE_WINDOW_SECONDS` | Janela do rate limit (default 60) |

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Rodar migrações e seed

As migrações Alembic rodam automaticamente no startup da API (`init_db`). O usuário admin e a organização demo (PyERP Demo Ltda → Matriz → Loja Centro) são criados se ainda não existirem.

Para rodar migrações manualmente:

```bash
alembic upgrade head
```

### 5. Iniciar a API

```bash
uvicorn main:app --reload
```

- API: http://localhost:8000
- Documentação interativa (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/

## Testes

Com o Docker rodando (`docker compose up -d`):

```bash
pytest
```

Os testes usam `TEST_DATABASE_URL` (banco `erp_vendas_test`). O schema é recriado na sessão e truncado entre cada caso. XMLs mínimos de NF-e ficam em `tests/fixtures/nfe/` (CI).

Listagens de negócio usam o contrato paginado `{ items, total, offset, limit }` (`offset`/`limit` na query; default 50, máx. 200).

## Multi-empresa (tenant)

Modelo: `companies` → `branches` (filial) → `stores` (loja). O seed cria **PyERP Demo Ltda / Matriz / Loja Centro**. Toda query de negócio filtra por `company_id` do usuário; vendas, estoque e compras usam `store_id` (body ou loja padrão do usuário).

Endpoints: `GET /companies/me`, CRUD `/branches`, CRUD `/stores`. `GET /auth/me` devolve empresa + filial/loja padrão.

## Perfis de usuário (RBAC)

| Perfil | Descrição resumida |
|--------|-------------------|
| `admin` | Acesso total (usuários, auditoria) |
| `gerente` | Gestão operacional, cancelamento de vendas |
| `supervisor` | Supervisão de vendas e estoque |
| `operador` | Vendas e cadastro de clientes |
| `conferente` | Movimentação de estoque e compras (NF-e) |
| `colaborador` | Somente leitura |

### Credenciais de desenvolvimento

Após o primeiro startup com seed (defina `ADMIN_PASSWORD` no `.env` antes de subir a API):

| Campo | Valor |
|-------|-------|
| Username | `admin` (ou `ADMIN_USERNAME`) |
| Email | `admin@pyerp.local` (ou `ADMIN_EMAIL`) |
| Senha | obrigatório: `ADMIN_PASSWORD` no `.env` (sem default no seed) |

> **Segurança:** o seed falha se `ADMIN_PASSWORD` não estiver definido. Em staging/produção use senha forte, `JWT_SECRET` único e altere a senha do admin após o primeiro login. Com `ENV=production`, a API recusa subir se `JWT_SECRET` ou `ADMIN_PASSWORD` estiverem ausentes/fracos.

## Estrutura do projeto

O schema do banco é gerenciado pelo **Alembic** (`alembic upgrade head`). Não há migrações SQL legadas no repositório.

```
├── alembic/          # Migrações de banco
├── auth/             # JWT, permissões, dependências
├── database/         # Conexão, seed, utilitários de migração
├── frontend/         # Painel Next.js 15 (App Router) + shadcn/ui
├── models/           # Modelos SQLModel / schemas Pydantic
├── repositories/     # Acesso a dados
├── routers/          # Endpoints HTTP
├── services/         # Regras de negócio
├── tests/            # Testes de integração (pytest) + fixtures/nfe CI
└── main.py           # Entry point FastAPI
```

## Frontend (painel de desenvolvimento)

O painel em `frontend/` serve para login, CRUDs e listagens contra a API local — **não** é a UI final de produto. Caixa/PDV físico fica no repo `pyerp-pdv`.

Stack: Next.js 15 + TypeScript, Tailwind + shadcn/ui, TanStack Query, RHF + Zod, cliente tipado via OpenAPI. JWT em `localStorage`.

A API libera CORS para `http://localhost:3000` por padrão (`CORS_ORIGINS`).

```bash
# terminal 1 — API
uvicorn main:app --reload

# terminal 2 — frontend
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

App em http://localhost:3000 — detalhes em [`frontend/README.md`](frontend/README.md).

Para republicar o contrato tipado após mudanças na API:

```bash
python scripts/export_openapi.py
cd frontend && npm run generate:api
```

## CI/CD

O pipeline GitHub Actions (`.github/workflows/ci.yml`) roda em cada push/PR para `main`:

- Backend: `ruff check` + `ruff format --check` + `pytest` (PostgreSQL 16)
- Frontend: `npm run lint` + `npm run build` (Node 22)

## Documentação da equipe

| Documento | Conteúdo |
|-----------|----------|
| [docs/INTEGRACOES.md](docs/INTEGRACOES.md) | Contrato Data Sim / PDV (auth, store_id, endpoints) |
| [docs/openapi.json](docs/openapi.json) | Snapshot OpenAPI para apps externos |
| [docs/INTERNO.md](docs/INTERNO.md) | Arquitetura, convenções, fluxos |
| [docs/QA-BACKLOG-SQUAD.md](docs/QA-BACKLOG-SQUAD.md) | Backlog de melhorias |
| [docs/QA-POST-AUDIT.md](docs/QA-POST-AUDIT.md) | Relatório histórico de QA (jul/2026) |

## Dados de demonstração

Catálogo e XMLs de compra fictícios ficam fora do monorepo (Data Sim cadastra via API). Para testes locais/CI, use `tests/fixtures/nfe/` e o seed em `tests/catalog_seed.py`.
