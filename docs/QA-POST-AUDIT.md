# PyERP — Relatório de QA (histórico)

> **Snapshot de julho/2026.** Números e itens abertos desta varredura ficaram desatualizados (suíte atual: **114** testes; rate limit, paginação e CI frontend já existem). Use [`QA-BACKLOG-SQUAD.md`](QA-BACKLOG-SQUAD.md) e [`INTERNO.md`](INTERNO.md) como referência viva.

**Data:** julho/2026  
**Método:** auditoria de testes/CI · segurança · arquitetura/docs  
**Evidência na época:** 108 testes passando

---

## Veredito executivo (histórico)

O backend havia fechado gaps P1 (migrations tenant + filtros de data) e P0 de seed (senha admin obrigatória). À época a suíte tinha **108** testes (fixtures/router de fixtures já desmontados). Itens então abertos (paginação, rate limit, CI front) foram tratados depois — confira o backlog atual.

| Área | #3 | #4 (histórico) | Hoje |
|------|----|----------------|------|
| Testes | 113 | 108 | **114** |
| Fixtures bank | drift | router desmontado | fora do monorepo |
| P2 CORS/paginação/rate limit | parcial | abertos | feitos |
| CI | pytest + ruff | só backend | backend + frontend |

**Conclusão da época:** core estável para seguir com frontend.

---

## Evidência de runtime

```
108 tests collected
108 passed in 80.58s
```

| Arquivo | # |
|---------|---|
| `test_permissions.py` | 13 |
| `test_security.py` | 12 |
| `test_purchases.py` | 11 |
| `test_auth.py` | 8 |
| `test_brands.py` | 8 |
| `test_categories.py` | 8 |
| `test_customers.py` | 7 |
| `test_users.py` | 7 |
| `test_audit.py` | 6 |
| `test_products.py` | 6 |
| `test_tenant_isolation.py` | 6 |
| `test_sales.py` | 5 |
| `test_stock.py` | 4 |
| `test_nfe_parser.py` | 3 |
| `test_reports.py` | 3 |
| `test_migrations.py` | 1 |

---

## P0 — Status

| ID | Item | Status | Evidência |
|----|------|--------|-----------|
| P0-01 | JWT_SECRET produção | ✅ FIXED | `validate_production_config()` + lifespan |
| P0-02 | Credenciais admin | ✅ FIXED* | `seed.py` exige `ADMIN_PASSWORD` (sem default). *Opcional: `must_change_password` no 1º login ainda não existe |
| P0-03 | Delete categoria/marca | ✅ FIXED | 409 `ConflictException` |
| P0-04 | Concorrência vendas | ✅ FIXED | `lock_for_update` + teste paralelo |

---

## P1 — Status

| Item | Status |
|------|--------|
| `test_migrations` com `companies`/`branches`/`stores` | ✅ FIXED |
| Audit `date_from`/`date_to` | ✅ FIXED (`test_audit_log_filters_by_date_range`) |
| Purchases filtros de data | ✅ FIXED (`test_list_purchases_filters_by_date_range`) |
| RBAC 6 perfis | ✅ FIXED |
| CI + README | ✅ FIXED |

---

## P2 — Status

| ID | Item | Status |
|----|------|--------|
| P2-01 | SQL legado | ✅ FIXED |
| P2-02 | Audit nos services | ✅ FIXED |
| P2-03 | Paginação | ❌ OPEN |
| P2-04 | Idioma OpenAPI | ⚠️ PARTIAL (ruff OK; tags EN) |
| P2-05 | Soft vs hard delete | ❌ OPEN |
| P2-06 | Segurança extra | ⚠️ PARTIAL (CORS ✅; rate limit / refresh / headers ❌) |
| P2-07 | `.gitignore` | ✅ FIXED |

---

## Achados novos / drift

### Fixtures órfãos (alta prioridade de limpeza)

| Artefato | Estado |
|----------|--------|
| Pasta `fixtures/` (~150 XMLs + catalog) | **Ainda no repo** |
| `routers/fixtures_router.py` | Existe, **não montado** em `main.py` |
| `fixtures:read` em permissions | **Ausente** |
| `tests/test_fixtures.py` | **Removido** da suite |
| README / INTERNO | Dizem que bank **não** fica versionado |

→ Docs e código desalinhados. Remontar com permissão + gate seguro, **ou** apagar pasta/router/service e alinhar docs.

### Outros riscos

| Risco | Severidade |
|-------|------------|
| Sem rate limit em `/auth/login` | Média |
| Stock move sem `FOR UPDATE` | Baixa–média |
| JWT só em `localStorage` (frontend) | Média (XSS) |
| CI sem lint/build frontend | Baixa |
| Isolamento tenant estreito (só subset de módulos) | Baixa |
| INTERNO dizia 19 tabelas — reality **18** | Doc drift |

---

## API / schema

- **15 routers montados**, **64 endpoints** de negócio + `GET /`
- **18 tabelas** SQLModel + `alembic_version`
- **4 migrações** Alembic (head: `c3d4e5f6a7b8`)
- Frontend Next.js conectado à API (sem testes automatizados)

---

## Prioridades para o squad

1. **Decidir destino de `fixtures/`** (remover do monorepo ou remountar com segurança)
2. **P2-06** — rate limit no login
3. **P2-03** — paginação nas listagens
4. **P2-05** — política única de delete
5. (Opcional) `must_change_password` no admin
6. Ampliar `test_tenant_isolation` (purchases/customers/products)
7. CI frontend (`lint` + `build`)

---

## Definition of Done

| Critério | Status |
|----------|--------|
| ≥ 80 testes, 100% verde | ✅ **108** |
| README onboarding | ✅ |
| Nenhum P0 bloqueador | ✅ (force-change opcional) |
| RBAC 6 perfis | ✅ |
| Migrations = schema completo | ✅ |
| CI backend | ✅ |
| Docs sincronizadas | ✅ (esta varredura) |

---

*Relatório histórico · julho/2026*
