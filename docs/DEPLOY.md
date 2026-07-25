# Deploy — Dev e Prod

PyERP sobe em **Railway** (API + Postgres) e **Vercel** (frontend Next.js).
O mesmo `Dockerfile` e o mesmo pipeline servem para Dev e Prod; muda só
environment, domínio e secrets.

Imagens imutáveis da API também são publicadas no **GHCR**
(`ghcr.io/<owner>/<repo>/api:<sha|tag>`) a cada deploy Dev/Prod e no CI `main`.

## URLs atuais (projeto Railway `pyerp-dev`)

| Ambiente | API | Front |
|----------|-----|-------|
| **Dev** | https://api-development-6b9aa.up.railway.app | Preview Vercel / `NEXT_PUBLIC_API_URL` Dev |
| **Prod** | https://api-prod-prod.up.railway.app | https://pyerp-frontend.vercel.app |

### Environments Railway

| Papel | Railway environment | Serviço | `ENV` da app |
|-------|---------------------|---------|--------------|
| Dev | `development` | `api` | `development` |
| Prod | `production` | `api-prod` | `production` |

GitHub Variables (recomendado; defaults do workflow já batem com a tabela):

- `RAILWAY_DEV_ENVIRONMENT=development`
- `RAILWAY_PROD_ENVIRONMENT=production`
- `RAILWAY_DEV_SERVICE=api`
- `RAILWAY_PROD_SERVICE=api-prod`
- `DEV_API_URL` / `PROD_API_URL` (smoke + `NEXT_PUBLIC_API_URL`)

## Arquitetura

| Camada | Dev | Prod |
|--------|-----|------|
| API FastAPI | Railway `development` (`api`) | Railway `production` (`api-prod`) |
| PostgreSQL | Postgres Dev | Postgres Prod (nunca compartilhar) |
| Front Next.js | Vercel Preview | Vercel Production |
| `ENV` (app) | `development` | `production` |
| Artefato API | Dockerfile + GHCR `:sha` / `:main` | mesma imagem / tag `v*` + `:prod` |

Apps externos (Data Sim / PDV) só precisam da URL pública da API e de
origens liberadas em `CORS_ORIGINS` (ou chamadas server-to-server).

## Pré-requisitos no repo

- [`Dockerfile`](../Dockerfile) — Python 3.11 + `requirements.lock` + `HEALTHCHECK` `/livez`
- [`scripts/docker-entrypoint.sh`](../scripts/docker-entrypoint.sh) —
  migrate opcional (`RUN_MIGRATIONS`) + `uvicorn`
- [`scripts/migrate-only.sh`](../scripts/migrate-only.sh) — job só de schema
- [`railway.toml`](../railway.toml) — healthcheck / Dockerfile path
- [`.dockerignore`](../.dockerignore)
- [`docker-compose.app.yml`](../docker-compose.app.yml) — paridade local API + Postgres

Seed do admin roda no lifespan da API (`init_db`); defina `ADMIN_PASSWORD` forte.
Em produção o seed **não** rotaciona senha de admin já existente — altere via
`/auth/change-password` ou reset controlado no banco.

### Migrações

**Caminho único no container:** entrypoint quando `RUN_MIGRATIONS=1` (local/compose).

**Railway (Dev e Prod):**

1. Pre-deploy: `python -c "from database.migrate import upgrade_head; upgrade_head()"`
2. Serviço com `RUN_MIGRATIONS=0` (entrypoint não remigra)
3. Lifespan só faz seed (não roda Alembic)

Rollback de schema: preferir **forward-fix** (nova revision). Downgrade
manual só em emergência: `alembic downgrade -1` (ou `make migrate-down`) com
backup/restore sob sua responsabilidade.

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
| `REDIS_URL` | opcional | obrigatório se `UVICORN_WORKERS>1` |
| `TRUSTED_PROXY_HOSTS` | peers exatos do proxy Railway (sem CIDR) | idem |
| `SENTRY_DSN` | opcional | obrigatório (ou `ALLOW_MISSING_SENTRY=1`) |
| `PLATFORM_API_KEY` | opcional (Appsmith) | secreto forte |
| `PORT` | injetado pelo Railway | injetado pelo Railway |
| `RUN_MIGRATIONS` | `0` (pre-deploy) | `0` (pre-deploy) |
| `UVICORN_WORKERS` | `1` | conforme CPU |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | defaults 5 / 10 | ajustar ao plano |

Com `ENV=production`, `validate_production_config()` recusa subir se
`JWT_SECRET` / `ADMIN_PASSWORD` fracos, ou se faltar `SENTRY_DSN` (salvo bypass).

Health:

| Path | Papel |
|------|-------|
| `/livez` | processo up |
| `/readyz` | DB ok |
| `/healthz` | alias de `/readyz` (compat) |

## Variáveis de ambiente (Front)

| Variável | Development / Preview | Production |
|----------|----------------------|------------|
| `NEXT_PUBLIC_API_URL` | URL API Dev Railway (`DEV_API_URL`) | URL API Prod (`PROD_API_URL`) |

Root do projeto Vercel: `frontend/`. A CSP `connect-src` inclui a origin de
`NEXT_PUBLIC_API_URL` automaticamente no build.

## GHCR (imagem imutável)

O pipeline **builda e publica** a imagem no GHCR antes do `railway up`.
Hoje o Railway ainda faz build via `railway up` (RAILPACK/Dockerfile); a imagem
GHCR serve para auditoria, rollback manual e migração futura para **Docker Image
source**.

Para apontar o serviço Railway à imagem (opcional):

1. Em Settings → Source → Docker Image: `ghcr.io/<owner>/<repo>/api:main` (Dev)
   ou `:prod` (Prod)
2. Se o package for privado, configure credenciais GHCR no Railway
3. Remova o step `railway up` do workflow (ou troque por redeploy / image update)
4. Tags flutuantes `:main` / `:prod` permitem [image auto-updates](https://docs.railway.com/deployments/image-auto-updates)

## Ordem de provisionamento (já executada)

1. Dockerfile + entrypoint + `.dockerignore` + `docker-compose.app.yml`
2. Railway projeto `pyerp-dev` → Postgres + serviço `api`
3. Vercel `pyerp-frontend` com `NEXT_PUBLIC_API_URL`
4. CORS no Railway com URL Vercel
5. Smoke: `/`, `/healthz`, login admin, front
6. Esta doc
7. Environment Railway Prod + secrets novos + API Prod + Vercel Production
8. Envs Railway `development` / `production` + Variables no GitHub
9. Pre-deploy migrate + `RUN_MIGRATIONS=0` nos serviços API
10. (Opcional) Redis + Sentry + GHCR image source no Railway

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
- Backup automatizado: fora do escopo atual (orçamento); avalie quando houver
  dados críticos em Prod.

## CI/CD

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — pytest+coverage, ruff,
pip-audit, frontend test/lint/build/npm-audit, gitleaks, Docker+Trivy, push GHCR em `main`.

[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) — deploy após CI verde:

| Evento | Ação |
|--------|------|
| Push `main` | GHCR → Railway Dev + smoke `/healthz` + Vercel Preview (`DEV_API_URL`) |
| Tag `v*` | pytest → GHCR → Railway Prod → smoke → Vercel `--prod` |

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
| `DEV_API_URL` | URL pública API Dev (smoke + preview) |
| `PROD_API_URL` | URL pública API Prod (smoke + CSP build) |
| `RAILWAY_DEV_ENVIRONMENT` | default `development` |
| `RAILWAY_PROD_ENVIRONMENT` | default `production` |
| `RAILWAY_DEV_SERVICE` / `RAILWAY_PROD_SERVICE` | defaults `api` / `api-prod` |

Dependabot: [`.github/dependabot.yml`](../.github/dependabot.yml) (pip, npm, Actions, Docker).

### Lockfile Python

- Ranges em [`requirements.txt`](../requirements.txt)
- Pins em [`requirements.lock`](../requirements.lock) (`pip-compile`)
- Dev: [`requirements-dev.txt`](../requirements-dev.txt)

Regenerar: `make lock`

## Smoke checklist

- [ ] `GET` API Dev `/livez`, `/readyz` (ou `/healthz`) e (Dev) `/docs`
- [ ] `POST /auth/login` Dev (`login` + senha admin)
- [ ] CORS Vercel → API Dev
- [ ] `GET` API Prod `/readyz` (sem `/docs`)
- [ ] Front Production → API Prod (CSP connect-src ok)

## Custos / riscos (acadêmico)

- Free tier Railway/Vercel costuma bastar para Dev e demos; Prod pode
  precisar plano pago se o processo hibernar.
- Uploads grandes de XML: monitorar timeouts no Railway.
- Apps externos: acrescentar origens em `CORS_ORIGINS`.
- Com várias réplicas: `REDIS_URL` + manter pre-deploy migrate (já one-shot).
