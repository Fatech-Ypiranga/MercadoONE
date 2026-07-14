# Deploy — Dev e Prod

PyERP sobe em **Railway** (API + Postgres) e **Vercel** (frontend Next.js).
O mesmo `Dockerfile` e o mesmo pipeline servem para Dev e Prod; muda só
environment, domínio e secrets.

## URLs atuais (projeto Railway `pyerp-dev`)

| Ambiente | API | Front |
|----------|-----|-------|
| **Dev** | https://api-production-6b9aa.up.railway.app | Preview Vercel / `NEXT_PUBLIC_API_URL` Dev |
| **Prod** | https://api-prod-prod.up.railway.app | https://pyerp-frontend.vercel.app |

- Railway: environment `production` = **Dev** da app (`ENV=development`); environment `prod` = **Prod** (`ENV=production`).
- Serviços: Dev `api` + `Postgres`; Prod `api-prod` + `Postgres-aW_7` (bancos **separados**).
- Vercel projeto: `pyerp-frontend` (root `frontend/`). Production aponta para a API Prod; Preview/Development apontam para a API Dev.

OpenAPI/docs Dev: https://api-production-6b9aa.up.railway.app/docs  
OpenAPI/docs Prod: https://api-prod-prod.up.railway.app/docs

## Arquitetura

| Camada | Dev | Prod |
|--------|-----|------|
| API FastAPI | Railway env `production` (serviço `api`) | Railway env `prod` (serviço `api-prod`) |
| PostgreSQL | Postgres Dev | Postgres Prod (nunca compartilhar) |
| Front Next.js | Vercel Preview / Development | Vercel Production |
| `ENV` (app) | `development` | `production` |
| Artefato API | `Dockerfile` na raiz | mesma imagem |

Apps externos (Data Sim / PDV) só precisam da URL pública da API e de
origens liberadas em `CORS_ORIGINS` (ou chamadas server-to-server).

## Pré-requisitos no repo

- [`Dockerfile`](../Dockerfile) — Python 3.11 + dependency install
- [`scripts/docker-entrypoint.sh`](../scripts/docker-entrypoint.sh) —
  `alembic upgrade head` + `uvicorn` em `0.0.0.0:$PORT`
- [`.dockerignore`](../.dockerignore)
- [`docker-compose.app.yml`](../docker-compose.app.yml) — paridade local API + Postgres

Seed do admin roda no lifespan da API (`init_db`); defina `ADMIN_PASSWORD` forte.
Em produção o seed **não** rotaciona senha de admin já existente — altere via
`/auth/change-password` ou reset controlado no banco.

## Variáveis de ambiente (API)

Espelho de [`.env.example`](../.env.example):

| Variável | Dev | Prod |
|----------|-----|------|
| `ENV` | `development` | `production` |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | `${{Postgres-aW_7.DATABASE_URL}}` (nome do serviço Prod) |
| `JWT_SECRET` | forte, só Dev | forte, só Prod (outro valor) |
| `ADMIN_PASSWORD` / `ADMIN_*` | fortes, só Dev | fortes, só Prod |
| `CORS_ORIGINS` | URL Vercel + `http://localhost:3000` | `https://pyerp-frontend.vercel.app` (+ apps oficiais) |
| `LOGIN_RATE_LIMIT` | ex. `10` | adequado ao tráfego |
| `PORT` | injetado pelo Railway | injetado pelo Railway |

Com `ENV=production`, `validate_production_config()` recusa subir se
`JWT_SECRET` ou `ADMIN_PASSWORD` estiverem ausentes/fracos.

## Variáveis de ambiente (Front)

| Variável | Development / Preview | Production |
|----------|----------------------|------------|
| `NEXT_PUBLIC_API_URL` | URL API Dev Railway | URL API Prod Railway |

Root do projeto Vercel: `frontend/`.

## Ordem de provisionamento (já executada)

1. Dockerfile + entrypoint + `.dockerignore` + `docker-compose.app.yml`
2. Railway projeto `pyerp-dev` → Postgres + serviço `api`
3. Vercel `pyerp-frontend` com `NEXT_PUBLIC_API_URL`
4. CORS no Railway com URL Vercel
5. Smoke: `/`, `/docs`, login admin, front
6. Esta doc
7. Environment Railway `prod` + secrets novos + API Prod + Vercel Production

## Promote / redeploy manual

```bash
# Dev API
railway up --service api --environment production -m "deploy Dev"

# Prod API
railway up --service api-prod --environment prod -m "deploy Prod"

# Front (Production)
cd frontend && vercel --prod --yes
```

**Regras**

- Nunca apontar o front Prod para a API Dev.
- Nunca migrar dados Dev → Prod (só schema via Alembic em cada ambiente).
- Nunca compartilhar o mesmo banco entre Dev e Prod.

## CI/CD

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — pytest + ruff + build do frontend.

[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) — deploy após CI verde:

| Evento | Ação |
|--------|------|
| Push `main` | API → Railway Dev (`api`) + Vercel Preview |
| Tag `v*` | API → Railway Prod (`api-prod`) + Vercel Production |

Secrets necessários no GitHub (`Settings → Secrets`):

| Secret | Uso |
|--------|-----|
| `RAILWAY_TOKEN` | Token de conta/projeto Railway |
| `VERCEL_TOKEN` | Token Vercel |
| `VERCEL_ORG_ID` | Team/org id |
| `VERCEL_PROJECT_ID` | Project id do `pyerp-frontend` |

## Smoke checklist

- [x] `GET` API Dev `/` e `/docs`
- [x] `POST /auth/login` Dev (`login` + senha admin)
- [x] CORS Vercel → API Dev
- [x] `GET` API Prod `/` e login admin
- [x] Front Production → API Prod

## Custos / riscos (acadêmico)

- Free tier Railway/Vercel costuma bastar para Dev e demos; Prod pode
  precisar plano pago se o processo hibernar.
- Uploads grandes de XML: monitorar timeouts no Railway.
- Apps externos: acrescentar origens em `CORS_ORIGINS`.
