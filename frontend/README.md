# PyERP Frontend

Painel web para login, CRUDs e consultas contra a API PyERP. Serve para desenvolvimento e demonstração — **não** é a UI final de produto (caixa físico fica no `pyerp-pdv`).

Stack: Next.js 15 (App Router) + TypeScript, Tailwind + shadcn/ui, TanStack Query, React Hook Form + Zod.

## Papel no ecossistema

| Componente | Repo | Papel |
|------------|------|--------|
| **API + este painel** | `pyerp` | Contrato canônico; catálogo no ERP |
| **Data Sim** | `pyerp-data-sim` | Cadastra catálogo/compras fictícios via API |
| **PDV** | `pyerp-pdv` | Caixa físico; vendas via API |

Contrato: [`docs/INTEGRACOES.md`](../docs/INTEGRACOES.md).

## Pré-requisitos

- Node.js 20+ (CI usa Node 22)
- API PyERP em `http://localhost:8000` (CORS liberando `http://localhost:3000`)

## Setup

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

- App: http://localhost:3000
- Login: credenciais do admin seed (`ADMIN_EMAIL` / `ADMIN_PASSWORD` no `.env` da API)

Variável mínima em `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```


## Scripts

| Comando | Descrição |
|---------|-----------|
| `npm run dev` | Dev server (Turbopack) |
| `npm run build` | Build de produção |
| `npm run lint` | ESLint |
| `npm run generate:api` | Regenera `lib/api/schema.ts` a partir de `openapi.json` |

Contrato canônico dos apps externos: [`docs/INTEGRACOES.md`](../docs/INTEGRACOES.md).

Para atualizar o OpenAPI (snapshot em `docs/` + `frontend/`) a partir da API:

```bash
# na raiz do monorepo
python scripts/export_openapi.py
cd frontend && npm run generate:api
```

## Estrutura

```
app/
  (auth)/login/     # Login público
  (app)/            # Shell autenticado (sidebar RBAC + header + seletor de loja)
    dashboard/
    products|categories|customers|suppliers|...
    sales|sales/[id]|stock|purchases|reports
    branches|stores|users|audit
lib/
  api/              # Client tipado + schema OpenAPI
  auth.ts           # JWT em localStorage
  scope.ts          # Empresa / loja ativa
  permissions.ts    # Espelho da matriz RBAC do backend
  nav.ts            # Itens do menu filtrados por perfil
```

## Shell

- Sidebar filtra itens por perfil (ex.: Usuários só Admin; Filiais/Lojas só Admin/Gerente)
- Header mostra empresa (somente leitura) + seletor de loja (`GET /stores/`)
- `activeStoreId` em contexto + `localStorage` — estoque/compras/vendas usam essa loja
- Rotas protegidas: sem token → `/login`; sem permissão → 403 na página

## Telas do mockup

| Área | O que faz |
|------|-----------|
| Dashboard | Ticket médio, top produtos, estoque crítico, últimas vendas/compras |
| Cadastros | CRUD de produtos, categorias, marcas, clientes, fornecedores (fonte da verdade no ERP; espelho do Data Sim) |
| Vendas | Listagem + detalhe + cancelamento (RBAC); sem caixa/PDV — vendas vêm do app externo |
| Estoque | Saldo, extrato e movimentação por loja ativa |
| Compras | Lista, importação XML (preview + mapeamento + confirmação), cancelamento |
| Relatórios | Top produtos, ticket médio, estoque crítico |
| Org | Lista de usuários / filiais / lojas / auditoria |

Não há rota de PDV/`nova venda` neste front — vendas novas vêm do `pyerp-pdv` ou de `POST /sales` direto na API.
