# PyERP — Backlog de Mudanças (Pós-QA)

Documento para delegação ao squad. **Atualizado pós implementação squad** (julho/2026).

Relatório: **[QA-POST-AUDIT.md](./QA-POST-AUDIT.md)**

## Status geral

| Métrica | Valor |
|---------|-------|
| Testes | ampliada (paginação, rate limit, tenant, cancel purchase) |
| Endpoints montados | **64** + health |
| P0 | **4 FIXED** (force-change 1º login opcional) |
| P1 | **Fechados** |
| P2 | P2-01–07 FIXED (refresh/JWT cookie ainda opcionais) |
| CI | Backend (pytest + ruff) + frontend (`lint` + `build`) |

---

## P0 — Concluídos

| ID | Item | Evidência |
|----|------|-----------|
| P0-01 | JWT_SECRET em produção | `auth/security.py`, `main.py` |
| P0-02 | Seed exige `ADMIN_PASSWORD` | `database/seed.py` `_require_admin_password()` |
| P0-03 | Delete categoria/marca → 409 | services + testes |
| P0-04 | Concorrência vendas | `lock_for_update` + teste |

### Opcional (ex-P0-02)

- [ ] Campo `must_change_password` + bloquear API até troca no 1º login

---

## P1 — Concluídos

| Item | Evidência |
|------|-----------|
| Migrations tenant | `tests/test_migrations.py` includes `companies`/`branches`/`stores` |
| Audit date filters | `test_audit_log_filters_by_date_range` |
| Purchases date filters | `test_list_purchases_filters_by_date_range` |

---

## Itens do squad

### CLEAN-01 — Fixtures órfãos ✅

**Decisão:** opção A — remover do monorepo.

- [x] Código `fixtures/` / router / service ausentes do monorepo
- [x] `tests/fixtures/nfe/` (CI) permanece
- [x] README / INTERNO alinhados

---

### P2-03 — Paginação ✅

- [x] Contrato `{ items, total, offset, limit }` via `models/pagination.py`
- [x] Aplicado em: products, customers, sales, purchases, suppliers, users, categories, brands, branches, stores, audit-log
- [x] Frontend unwrap via `unwrapPageItems`

---

### P2-04 — Idioma OpenAPI ✅

- [x] Tags em PT-BR
- [x] ruff + CI format

---

### P2-05 — Soft vs hard delete ✅

- [x] Política unificada: **hard delete** em todos os cadastros
- Hard+409 quando houver vínculos: category, brand, product, supplier, user (compras)
- Hard: customer, branch, store
- Campo `is_active` permanece para desativação via update, não via DELETE

---

### P2-06 — Segurança ✅ (exceto opcionais)

- [x] CORS (`CORS_ORIGINS`)
- [x] Rate limiting em `/auth/login` (`LOGIN_RATE_LIMIT` / `LOGIN_RATE_WINDOW_SECONDS`)
- [ ] Refresh token (opcional)
- [x] Security headers (`middleware/security.py`)
- [ ] Considerar JWT em cookie httpOnly no frontend (hoje `localStorage`)

---

### P2-extra — Locks de estoque ✅

- [x] `lock_for_update` em `StockMovementService.create_movement`
- [x] Lock em cancel sale / cancel purchase

---

### QA-extra — Cobertura ✅ (parcial)

- [x] Ampliar `test_tenant_isolation` (purchases, customers, products cross-tenant)
- [x] CI frontend: `npm run lint` + `npm run build`
- [x] Teste cancel purchase com estoque insuficiente para estorno

---

## Definition of Done

- [x] ≥ 80 testes, 100% verde
- [x] README onboarding
- [x] P0 bloqueadores fechados
- [x] RBAC 6 perfis
- [x] `test_migrations` = schema completo
- [x] CI backend
- [x] Fixtures sem drift (CLEAN-01)
- [x] Paginação (P2-03)
- [x] Política única de delete (P2-05) — hard delete

---

*Última atualização: squad implementação · julho/2026*
