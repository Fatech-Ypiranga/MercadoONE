# Deploy — Dev e Prod

PyERP sobe em **Railway** (API + Postgres) e **Vercel** (frontend Next.js).
O mesmo `Dockerfile` e o mesmo pipeline servem para Dev e Prod; muda só
environment, domínio e secrets.

Imagens imutáveis da API também são publicadas no **GHCR**
(`ghcr.io/<owner>/pyerp/api:<sha|tag>`) a cada push em `main` e tag `v*`.

## URLs atuais (projeto Railway `pyerp-dev`)

| Ambiente | API | Front |
|----------|-----|-------|
| **Dev** | https://api-production-6b9aa.up.railway.app | Preview Vercel / `NEXT_PUBLIC_API_URL` Dev |
| **Prod** | https://api-prod-prod.up.railway.app | https://pyerp-frontend.vercel.app |

### Renomear environments Railway (recomendado)

Alvo alinhado à app:

| Papel | Railway environment (alvo) | Serviço | `ENV` da app |
|-------|----------------------------|---------|--------------|
| Dev | `development` | `api` | `development` |
| Prod | `production` | `api-prod` | `production` |

**Hoje** o pipeline ainda faz fallback para os nomes antigos (`production`=Dev, `prod`=Prod)
para não quebrar deploys. Migração:

1. No Railway, renomeie `production` → `development` e `prod` → `production`
2. Defina GitHub Variables:
   - `RAILWAY_DEV_ENVIRONMENT=development`
   - `RAILWAY_PROD_ENVIRONMENT=production`

Ou, sem renomear no Railway, mantenha Variables apontando aos nomes atuais.

## Arquitetura

| Camada | Dev | Prod |
|--------|-----|------|
| API FastAPI | Railway env `development` (serviço `api`) | Railway env `production` (serviço `api-prod`) |
| PostgreSQL | Postgres Dev | Postgres Prod (nunca compartilhar) |
| Front Next.js | Vercel Preview / Development | Vercel Production |
| `ENV` (app) | `development` | `production` |
| Artefato API | `Dockerfile` + GHCR | mesma imagem / tag `v*` |

Apps externos (Data Sim / PDV) só precisam da URL pública da API e de
origens liberadas em `CORS_ORIGINS` (ou chamadas server-to-server).

## Pré-requisitos no repo

- [`Dockerfile`](../Dockerfile) — Python 3.11 + `requirements.lock`
- [`scripts/docker-entrypoint.sh`](../scripts/docker-entrypoint.sh) —
  migrate opcional (`RUN_MIGRATIONS`) + `uvicorn` (`UVICORN_WORKERS`)
- [`scripts/migrate-only.sh`](../scripts/migrate-only.sh) — job só de schema
- [`.dockerignore`](../.dockerignore)
- [`docker-compose.app.yml`](../docker-compose.app.yml) — paridade local API + Postgres

Seed do admin roda no lifespan da API (`init_db`); defina `ADMIN_PASSWORD` forte.
Em produção o seed **não** rotaciona senha de admin já existente — altere via
`/auth/change-password` ou reset controlado no banco.

### Migrações em multi-réplica

Padrão: `RUN_MIGRATIONS=1` no boot (entrypoint + lifespan).

Para N réplicas sem race:

1. Rode um release one-shot: `scripts/migrate-only.sh`
2. Suba a API com `RUN_MIGRATIONS=0`

## Variáveis de ambiente (API)

Espelho de [`.env.example`](../.env.example):

| Variável | Dev | Prod |
|----------|-----|------|
| `ENV` | `development` | `production` |
| `DATABASE_URL` | Postgres Dev | Postgres Prod |
| `JWT_SECRET` | forte, só Dev | forte, só Prod (outro valor) |
| `ADMIN_PASSWORD` / `ADMIN_*` | fortes, só Dev | fortes, só Prod |
| `CORS_ORIGINS` | URL Vercel + `http://localhost:3000` | `https://pyerp-frontend.vercel.app` (+ apps oficiais) |
| `LOGIN_RATE_LIMIT` | ex. `10` | adequado ao tráfego |
| `REDIS_URL` | opcional | recomendado com >1 réplica |
| `TRUSTED_PROXY_HOSTS` | peer do proxy Railway | idem |
| `SENTRY_DSN` | opcional | recomendado |
| `PLATFORM_API_KEY` | opcional (Appsmith local) | secreto forte |
| `PORT` | injetado pelo Railway | injetado pelo Railway |
| `RUN_MIGRATIONS` | `1` | `1` (ou `0` + migrate job) |
| `UVICORN_WORKERS` | `1` | conforme CPU |

Com `ENV=production`, `validate_production_config()` recusa subir se
`JWT_SECRET` ou `ADMIN_PASSWORD` estiverem ausentes/fracos, e `/docs` fica off.

## Variáveis de ambiente (Front)

| Variável | Development / Preview | Production |
|----------|----------------------|------------|
| `NEXT_PUBLIC_API_URL` | URL API Dev Railway | URL API Prod Railway |

Root do projeto Vercel: `frontend/`. A CSP `connect-src` inclui a origin de
`NEXT_PUBLIC_API_URL` automaticamente no build.

## Ordem de provisionamento (já executada)

1. Dockerfile + entrypoint + `.dockerignore` + `docker-compose.app.yml`
2. Railway projeto `pyerp-dev` → Postgres + serviço `api`
3. Vercel `pyerp-frontend` com `NEXT_PUBLIC_API_URL`
4. CORS no Railway com URL Vercel
5. Smoke: `/`, `/healthz`, login admin, front
6. Esta doc
7. Environment Railway Prod + secrets novos + API Prod + Vercel Production
8. Renomear envs Railway / setar Variables (ver acima)
9. (Opcional) Redis + Sentry + GHCR image source no Railway

## Promote / redeploy manual

```bash
# Dev API
railway up --service api --environment development -m "deploy Dev"

# Prod API
railway up --service api-prod --environment production -m "deploy Prod"

# Front (Production)
cd frontend && vercel --prod --yes
```

**Regras**

- Nunca apontar o front Prod para a API Dev.
- Nunca migrar dados Dev → Prod (só schema via Alembic em cada ambiente).
- Nunca compartilhar o mesmo banco entre Dev e Prod.

## CI/CD

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — pytest+coverage, ruff,
frontend test/lint/build, build/push GHCR em `main`.

[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) — deploy após CI verde:

| Evento | Ação |
|--------|------|
| Push `main` | API → Railway Dev + smoke `/healthz` + Vercel Preview |
| Tag `v*` | pytest smoke → GHCR tag → Railway Prod → smoke `/healthz` → Vercel `--prod` |

Secrets necessários no GitHub (`Settings → Secrets`):

| Secret | Uso |
|--------|-----|
| `RAILWAY_TOKEN` | Token de conta/projeto Railway |
| `VERCEL_TOKEN` | Token Vercel |
| `VERCEL_ORG_ID` | Team/org id |
| `VERCEL_PROJECT_ID` | Project id do `pyerp-frontend` |

Variables recomendadas (`Settings → Variables`):

| Variable | Uso |
|----------|-----|
| `DEV_API_URL` | URL pública API Dev (smoke) |
| `PROD_API_URL` | URL pública API Prod (smoke + CSP build) |
| `RAILWAY_DEV_ENVIRONMENT` | default legado `production` (após rename: `development`) |
| `RAILWAY_PROD_ENVIRONMENT` | default legado `prod` (após rename: `production`) |
| `RAILWAY_DEV_SERVICE` / `RAILWAY_PROD_SERVICE` | defaults `api` / `api-prod` |

Dependabot: [`.github/dependabot.yml`](../.github/dependabot.yml) (pip, npm, Actions, Docker).

### Lockfile Python

- Ranges em [`requirements.txt`](../requirements.txt)
- Pins em [`requirements.lock`](../requirements.lock) (`pip-compile`)
- Dev: [`requirements-dev.txt`](../requirements-dev.txt)

Regenerar:

```bash
uv pip compile requirements.txt -o requirements.lock --python 3.11 --strip-extras
# ou: python -m piptools compile requirements.txt -o requirements.lock --strip-extras
```

## Smoke checklist

- [ ] `GET` API Dev `/healthz` e (Dev) `/docs`
- [ ] `POST /auth/login` Dev (`login` + senha admin)
- [ ] CORS Vercel → API Dev
- [ ] `GET` API Prod `/healthz` (sem `/docs`)
- [ ] Front Production → API Prod (CSP connect-src ok)

## Custos / riscos (acadêmico)

- Free tier Railway/Vercel costuma bastar para Dev e demos; Prod pode
  precisar plano pago se o processo hibernar.
- Uploads grandes de XML: monitorar timeouts no Railway.
- Apps externos: acrescentar origens em `CORS_ORIGINS`.
- Com várias réplicas: configure `REDIS_URL` e migrate one-shot.
