# MercadoONE — Roadmap de Melhorias

Auditoria completa do repositório (arquitetura, segurança, banco de dados, lógica de negócio, concorrência, performance, UX/acessibilidade, código morto, e pesquisa de práticas de mercado), realizada em 2026-09-09 na branch `refactor/vertical-slice-architecture`, via leitura direta de código — não é uma varredura automatizada de ferramenta, é revisão manual dirigida por checklist.

**Objetivo deste documento:** cobertura end-to-end de melhorias, correções, gaps e bugs, para decisão de priorização. Não define ordem de execução — isso é decisão do time. Cada item aprovado para execução vira sua própria branch `feat/<nome-descritivo>`, criada a partir de `refactor/vertical-slice-architecture`.

**Classificações usadas:**
- **FATO** — confirmado por leitura direta do código.
- **PONTO A VALIDAR** — pode ser uma exceção arquitetural consciente, não necessariamente um problema a corrigir.
- Severidade: **CRÍTICO** (perda de dados/corrupção/falha grave em produção) · **ALTO** (falha relevante ou comportamento incorreto) · **MÉDIO** (robustez/manutenção) · **BAIXO** (polimento, ou item confirmado correto — marcado "OK").

---

## Sumário executivo — itens CRÍTICO e ALTO

Estes 8 itens concentram o maior risco real encontrado. Todo o resto do documento é o detalhamento e o contexto por trás deles, mais os itens de menor severidade.

**Atualização 2026-09-16:** 7 dos 8 itens abaixo já foram corrigidos e commitados (branch `refactor/vertical-slice-architecture`). Só falta UX-02.

| ID | Item | Severidade | Área | Status |
|----|------|------------|------|--------|
| PERF-01 | Paginação de `sales`, `purchases` e `customers` é feita em memória — busca **todas** as linhas do banco antes de cortar a página | CRÍTICO | Performance | ✅ Resolvido (`4a549e3`) |
| PERF-02 | `list_purchases`/`get_purchase_detail` fazem N+1 queries (1 busca de fornecedor/produto por linha) | CRÍTICO | Performance | ✅ Resolvido (`48ebd32`) |
| CONC-01 | `confirm_purchase` recalcula o custo médio ponderado do produto sem travar a linha (`lock_for_update`) — duas confirmações de compra concorrentes corrompem `cost_price` silenciosamente (lost update) | CRÍTICO | Concorrência | ✅ Resolvido (`48ebd32`) |
| BUG-01 | **Confirmado**: `confirm_purchase_from_xml` é código morto (nenhuma rota o usa). O único caminho real, `POST /purchases/confirm` → `confirm_purchase`, aceita `unit_cost`/`total_cost` do cliente sem nenhuma validação server-side (só `quantity` tem `gt=0`). O frontend oficial sempre envia o valor correto (`entry_unit_cost` do XML, não editável na UI), mas isso é uma garantia só do cliente — a API em si confia cegamente no payload. Qualquer chamada direta (script, Postman, bug futuro no front, uso indevido da permissão `purchases:write`) corrompe `cost_price` silenciosamente | CRÍTICO | Lógica de negócio | ✅ Resolvido (`48ebd32`) |
| SEC-02 | Gate de produção só dispara se `ENV=production` for setado explicitamente; deploy sem `ENV` definido roda silenciosamente com JWT secret padrão | ALTO | Segurança | ✅ Resolvido (`58259d8`) |
| BUG-02 | Filtros `date_to` em vendas/compras tratam a data como meia-noite (`<=`), excluindo praticamente todo o dia informado | ALTO | Lógica de negócio | ✅ Resolvido (`4a549e3`) |
| UX-01 | Erros de rede crus (ex.: "Failed to fetch") aparecem sem tradução em todas as páginas exceto login | ALTO | Frontend/UX | ✅ Resolvido (`b51849b`) |
| UX-02 | Nenhum formulário CRUD usa validação client-side (react-hook-form+zod), apesar do padrão já existir no login | ALTO | Frontend/UX | ⬜ Pendente |

---

## 1. Backend — Arquitetura e padrões

| ID | Item | Classificação | Evidência |
|----|------|----------------|-----------|
| BE-01 | `audit_log/router.py` não tem `service.py`/`repository.py` próprios — chama `shared/audit.py` diretamente, fora do padrão vertical-slice usado pelos demais domínios | PONTO A VALIDAR | `backend/audit_log/router.py`, `backend/shared/audit.py` |
| BE-02 | `reports/service.py` usa métodos estáticos que consultam models de outros domínios diretamente, sem `repository.py` próprio | PONTO A VALIDAR | `backend/reports/service.py` |
| BE-03 | `organization/` tem 3 routers para 1 único `service.py`/`repository.py`, diferente do padrão 1:1:1 dos outros domínios | PONTO A VALIDAR | `backend/organization/` |
| BE-04 | Falta `test_organization.py` dedicado — só testado incidentalmente via fixtures de outros testes | FATO | `backend/tests/` (ausência do arquivo) |
| BE-05 | SQLModel ainda em versão pré-1.0 — risco de instabilidade de API em upgrades futuros | PONTO A VALIDAR (observação) | `backend/requirements.txt` |
| BE-06 | Sem mypy configurado — checagem de tipos não roda em CI, só ruff (lint/format) | FATO | `backend/pyproject.toml`, `.github/workflows/ci.yml` |

## 2. Frontend — Arquitetura e padrões

| ID | Item | Classificação | Evidência |
|----|------|----------------|-----------|
| FE-01 | Boilerplate de diálogo CRUD duplicado quase identicamente em 7 páginas, sem hook/componente compartilhado | FATO | `products/page.tsx` (662 linhas), `users/page.tsx` (596), `customers/page.tsx` (564), `purchases/page.tsx` (498), `suppliers/page.tsx` (358), `stock/page.tsx` (325), `categories/page.tsx` (297) |
| FE-02 | Zero testes de componente ou E2E — cobertura limitada a 3 testes unitários de funções puras em `lib/` | FATO | `frontend/lib/*.test.ts`; ausência de Testing Library/Vitest/Playwright |
| FE-03 | Páginas com tamanho muito desbalanceado sugerindo lógica que poderia migrar para `lib/` | PONTO A VALIDAR | `products/page.tsx` vs. `lib/format.ts`, `lib/scope.ts`, `lib/permissions.ts` |

## 3. Infraestrutura e Projeto

| ID | Item | Classificação | Evidência |
|----|------|----------------|-----------|
| INFRA-01 | Linha de base saudável — CI/CD, gestão de config de produção e scans de segurança já maduros (contexto, não pendência) | FATO / OK | `.github/workflows/ci.yml` (ruff, pytest ≥55%, pip-audit, gitleaks, trivy), `.github/workflows/deploy.yml` (Railway + Vercel), `backend/.env.example` |

## 4. Segurança

| ID | Item | Severidade | Evidência |
|----|------|------------|-----------|
| SEC-01 | Upload de NFe (`POST /purchases/upload-xml`) lê o arquivo inteiro em memória sem limite de tamanho nem validação de `content_type`; parsing sem hardening contra expansão de entidades (DoS). Confirmado por dois agentes independentes (segurança e NFe). **✅ Resolvido (`48ebd32`, `a478793`)**: limite de 5MB, exige extensão `.xml`, bloqueia DOCTYPE | MÉDIO | `backend/purchases/router.py:29-36`, `backend/purchases/nfe_parser.py:8,133` |
| SEC-02 | Ver sumário executivo | ALTO | `backend/shared/identity/security.py:13,27,34-46,36` |
| SEC-03 | Testes de isolamento de tenant cobrem só leitura (GET/list). Não há teste de PUT/DELETE/PATCH cross-tenant; `update`/`delete` de `ProductService`/`CustomerService`/`UserService` não foram auditados diretamente quanto a filtro por `company_id` | MÉDIO | `backend/tests/test_tenant_isolation.py` |
| SEC-04 | Rate limiting real, mas cobre só 5 endpoints; fallback em memória não compartilha estado entre workers (mitigado parcialmente pelo gate de produção) | MÉDIO | `backend/middleware/security.py:27-33,140-160` |
| SEC-05 | Autorização por endpoint, validação de input, paginação limitada, sem dados sensíveis em logs/erros — confirmado correto | BAIXO / OK | `backend/products/router.py`, `backend/shared/pagination.py`, `backend/shared/exceptions.py` |
| SEC-06 | Fluxo de credenciais PDV (CSPRNG, Argon2, tokens curtos/tipados, revogação via `token_version`) — sem fragilidade encontrada | BAIXO / OK | `backend/shared/identity/pdv_credentials.py` |

## 5. Banco de Dados

| ID | Item | Severidade | Evidência |
|----|------|------------|-----------|
| DB-01 | `sales` sem índice composto `(company_id, sale_date, status)` nem em `customer_id` — hot path de listagem. **✅ Resolvido (`ffd9066`)** | MÉDIO | `backend/sales/models.py`, `backend/sales/repository.py:77-93` |
| DB-02 | Nenhuma FK tem `ondelete` explícito — proteção contra exclusão com dependências depende 100% de checagem manual no service | MÉDIO | `backend/categories/service.py:151-158`, `backend/products/service.py:268-276` |
| DB-03 | `purchase_orders.entry_date`/`status` sem índice (só unique parcial em `invoice_key`) — mesmo padrão do DB-01, achado pela revisão de performance. **✅ Resolvido (`ffd9066`)** | MÉDIO | `backend/purchases/models.py` |
| DB-04 | `StockMovement` tem índices single-column em `product_id`/`company_id`/`store_id`/`created_at`, mas o cálculo de saldo filtra por `(product_id, store_id, type)` — Postgres só usa um índice por vez aqui. Roda a cada venda/compra/cancelamento. **✅ Resolvido (`ffd9066`)** | MÉDIO | `backend/stock/repository.py` (`get_current_stock`) |
| DB-05 | Trilha de auditoria, transações multi-etapa, multi-tenancy e migrations (downgrades simétricos, exceto uma irreversível e documentada por ser dado sensível) — confirmado correto | BAIXO / OK | `backend/shared/audit.py:19-42`, `backend/alembic/versions/k1f2a3b4c5d6_*.py:19-26` |

## 6. NFe e Processamento em Lote

| ID | Item | Severidade | Evidência |
|----|------|------------|-----------|
| NFE-01 | Sem limite de itens por NFe — XML com milhares de `<det>` processado de forma síncrona no request (mesma raiz do SEC-01). **✅ Resolvido (`a478793`)**: limite de 500 itens | MÉDIO | `backend/purchases/nfe_parser.py` |
| NFE-02 | Falha em item no meio do lote é tratada corretamente como tudo-ou-nada, mas sem teste dedicado para esse cenário específico | BAIXO (comportamento correto, gap de teste) | `backend/purchases/service.py:81-186` |
| NFE-03 | Idempotência de import (chave de acesso única por `company_id`) e ausência de dependência externa — confirmado correto | BAIXO / OK | `backend/purchases/models.py:82-90` |

## 7. Lógica de Negócio (bugs reais, verificados linha a linha)

| ID | Item | Severidade | Evidência |
|----|------|------------|-----------|
| BUG-01 | Ver sumário executivo — `unit_cost`/`total_cost` sem validação server-side em `confirm_purchase`; `confirm_purchase_from_xml` confirmado como código morto (sem rota). **✅ Resolvido (`48ebd32`)** | CRÍTICO | `backend/purchases/models.py:172,176`, `backend/purchases/service.py:81-186,188-256,590-599`, `backend/purchases/router.py:39-54` |
| BUG-02 | Ver sumário executivo — `date_to` tratado como meia-noite exclui o dia inteiro. **✅ Resolvido (`4a549e3`)**: `shared/dates.py::inclusive_end_of_day` aplicado em sales/purchases/audit_log | ALTO | `backend/sales/repository.py:88-91`, `backend/purchases/repository.py:31-34` |
| BUG-03 | Custo médio ponderado (fórmula, ordem flush-antes-de-ler-estoque, fallback para estoque zero/negativo) — verificado correto | BAIXO / OK | `backend/purchases/service.py:576-601` |
| BUG-04 | Overselling/duplicidade em vendas — itens agregados por produto antes da checagem de estoque, produtos travados em ordem determinística — verificado correto, é proteção intencional | BAIXO / OK | `backend/sales/service.py:32-173` |
| BUG-05 | Máquina de estados de cancelamento (compra e venda) — bloqueia duplo cancelamento/confirmação, revalida estoque antes de reverter — verificado correto | BAIXO / OK | `backend/purchases/service.py:306-374`, `backend/sales/service.py:175-244` |
| BUG-06 | Nenhuma exceção é engolida silenciosamente (`except: pass`) nos 4 domínios mais críticos revisados; Decimal usado consistentemente para dinheiro (nenhum float encontrado) | BAIXO / OK | `products`, `stock`, `sales`, `purchases` services |

## 8. Concorrência

| ID | Item | Severidade | Evidência |
|----|------|------------|-----------|
| CONC-01 | Ver sumário executivo — `confirm_purchase` não trava o produto antes de recalcular `cost_price`. **✅ Resolvido (`48ebd32`)**: `_resolve_product` agora usa `lock_for_update` | CRÍTICO | `backend/purchases/service.py:153-158,412,476,576-601` |
| CONC-02 | Mesma causa raiz do CONC-01: leitura de `current_stock` via `SUM()` sem lock pode interlear entre confirmações concorrentes do mesmo produto, compondo a inconsistência. **✅ Resolvido (`48ebd32`)**, mesma correção do CONC-01 | MÉDIO (mesma correção resolve) | `backend/purchases/service.py` |
| CONC-03 | Alocação de código de material/fornecedor (`pg_advisory_xact_lock` + `with_for_update`), débito de estoque em vendas/cancelamentos (produtos travados em ordem ordenada, evita deadlock), e unicidade de `invoice_key` via constraint — tudo verificado correto e consistente | BAIXO / OK | `backend/products/service.py:317-336`, `backend/suppliers/service.py:250-316`, `backend/sales/service.py:82-97,201-224`, `backend/purchases/service.py:319-330` |

## 9. Performance

| ID | Item | Severidade | Evidência |
|----|------|------------|-----------|
| PERF-01 | Ver sumário executivo — paginação em memória em sales/purchases/customers. **✅ Resolvido (`4a549e3`, `48ebd32`)**: `LIMIT`/`OFFSET` + `COUNT` real, mesmo padrão do `audit_log` | CRÍTICO | `backend/shared/pagination.py:20-24` (`paginate()` fatia lista Python, sem `LIMIT`/`OFFSET` SQL), usado por `sales/service.py`, `purchases/service.py`, `customers/service.py` |
| PERF-02 | Ver sumário executivo — N+1 em `list_purchases` (fornecedor por linha) e `get_purchase_detail` (produto por item). **✅ Resolvido (`48ebd32`)**: `SupplierRepository.find_by_ids`/`ProductRepository.find_by_ids` em lote | CRÍTICO | `backend/purchases/service.py:279,290-299` |
| PERF-03 | `reports/service.py` já agrega via SQL (`func.sum`/`func.avg`), sem loop Python — modelo a ser replicado nos itens acima | BAIXO / OK | `backend/reports/service.py:58-59` |
| PERF-04 | `audit_log` já faz paginação SQL real (`.offset().limit()` + `COUNT(*)`) — é o padrão correto já existente no projeto, só precisa ser replicado em sales/purchases/customers | BAIXO / OK (template a seguir) | `backend/shared/audit.py` |
| PERF-05 | Upload/parsing de NFe roda de forma síncrona no event loop (não é crítico hoje pelo tamanho típico do XML, mas não escala se volume/tamanho crescer) | MÉDIO | `backend/purchases/router.py:29`, `backend/purchases/nfe_parser.py` |

## 10. Frontend — UX, Acessibilidade e Tratamento de Erro

| ID | Item | Severidade | Evidência |
|----|------|------------|-----------|
| UX-01 | Ver sumário executivo — erros de rede crus fora do login. **✅ Resolvido (`b51849b`)** | ALTO | `frontend/lib/format.ts:33-36` (`errorMessage`), contraste com `login-form.tsx:56-58` |
| UX-02 | Ver sumário executivo — nenhuma página CRUD usa react-hook-form+zod, só `useState` com validação mínima (botão desabilitado) | ALTO | grep `useForm|zodResolver` em `app/` retorna zero; `login-form.tsx:81-83,95-97,109-111` tem o padrão correto |
| UX-03 | Confirmação de exclusão usa `window.confirm()` nativo em vez do `AlertDialog` do próprio design system — funciona, mas é inconsistente visualmente e não localizável/estilizável | MÉDIO | `categories/page.tsx:160`, mesmo padrão em customers/suppliers/users/products/purchases |
| UX-04 | Sem toast/notificação — erros só aparecem como `<Alert>` inline, que pode passar despercebido em formulários longos e scrollados | MÉDIO | `components/ui-states.tsx:7-14` |
| UX-05 | `LoadingState` é só texto, não skeleton — funcional mas pouco polido | BAIXO | `components/ui-states.tsx:40-42` |
| UX-06 | Acessibilidade: labels corretos na maioria dos formulários, botão de ícone único (menu) com `aria-label`, foco de diálogo delegado ao Radix (correto); checkbox "Ativa" em categorias sem `id`/`htmlFor` explícito (funciona por estar aninhado, mas inconsistente) | BAIXO | `login-form.tsx:73-112`, `components/app-header.tsx:30-39`, `categories/page.tsx:269-278` |
| UX-07 | Sem optimistic updates em nenhuma mutation — mais seguro (sem risco de rollback incorreto), mas todo save tem round-trip completo sem feedback visual imediato além do botão "Salvando…" | BAIXO / OK (trade-off aceitável) | grep `onMutate/setQueryData/optimistic` em todo o frontend retorna zero |

## 11. Código Morto e TODOs

| ID | Item | Severidade | Evidência |
|----|------|------------|-----------|
| DEAD-01 | **Confirmado**: `confirm_purchase_from_xml` não é exposto por nenhuma rota (`router.py` só liga `/confirm` a `confirm_purchase`) — é código morto. Ver BUG-01 para o impacto disso (a validação "seria segura" nunca roda no servidor). **✅ Resolvido (`48ebd32`)**: função removida | FATO | `backend/purchases/service.py:188`, `backend/purchases/router.py:39-54` |
| DEAD-02 | `SupplierRepository.update` e `ProductRepository.update` sem chamadores — o próprio código já documenta isso em comentário ("sem callers atuais, service muta inline") | MÉDIO (parece API viva mas é inalcançável/não testado) | `backend/suppliers/repository.py:8-14`, `backend/products/repository.py:8-14` |
| DEAD-03 | `ProductRepository.find_by_category` sem chamadores nem testes | BAIXO | `backend/products/repository.py:70` |
| DEAD-04 | Pequenos exports não utilizados fora do próprio arquivo no frontend (`LIVE_REFETCH_INTERVAL_MS`, `NAV_SECTIONS`, `getActiveStoreId`, `ForbiddenState`) | BAIXO | `frontend/lib/live-query.ts:2`, `lib/nav.ts:35`, `lib/scope.ts:9`, `components/require-permission.tsx:14` |
| DEAD-05 | Nenhum TODO/FIXME/HACK real encontrado, nenhum código comentado, nenhuma duplicação de utilitário além do já consolidado, nenhum `print()`/`console.log` fora de scripts CLI — repositório limpo nessas frentes | BAIXO / OK | busca em todo `backend/` e `frontend/` |

## 12. Pesquisa de Mercado — Comparação com Práticas Estabelecidas

Pesquisa externa (fontes citadas nos achados), não é auditoria de código — são recomendações a avaliar, não bugs.

| ID | Item | Confiança da evidência | Recomendação |
|----|------|------------------------|---------------|
| ARCH-01 | Multi-tenancy via `company_id` manual em cada query é o padrão correto para o porte atual (SMB), mas backends maduros adicionam **Row-Level Security do Postgres** como defesa em profundidade — um filtro esquecido em um dos muitos métodos de repositório passa a ser impossível de vazar dados entre tenants, não só "improvável" | Alta (múltiplas fontes técnicas independentes) | Maior alavancagem de segurança do projeto a médio prazo — considerar como próxima camada, não substituindo os filtros atuais |
| ARCH-02 | Parsing síncrono de NFe já autorizada (sem chamada à SEFAZ) está correto para o estágio atual — a justificativa para fila assíncrona em sistemas comerciais (nfe.io, Focus NFe) é a latência do SEFAZ, que este projeto não tem hoje | Alta | Não é ação necessária agora; revisitar se o projeto passar a consultar SEFAZ ou importar em lote (múltiplos arquivos por request) |
| ARCH-03 | Projeto ainda não tem fila de background (Celery/RQ/arq); `arq` é a recomendação natural para uma base async-first como esta (FastAPI), por ser nativo de asyncio e mais leve que Celery | Alta | Não é urgente — sinais de alerta claros: I/O externo de latência incerta, operações >algumas centenas de ms, necessidade de retry/observabilidade. Nenhum desses está presente hoje |
| ARCH-04 | Vertical Slice Architecture é um padrão real e documentado para FastAPI (mais maduro em .NET), com uma armadilha bem descrita: a pasta `shared/` vira "gaveta de tudo" ou lógica se duplica entre domínios por falta de lugar óbvio. **O projeto já está no ponto de inflexão onde isso costuma começar** (commits recentes já extraindo helpers para `shared/`) | Média-alta (padrão bem documentado, fontes de qualidade mista) | Definir convenção explícita agora: "lógica de domínio → shared/domain; preocupação transversal (auth, transação, erro) → middleware/dependency injection, nunca em shared solto". Aplicar "regra de três": só abstrair após 3+ duplicações idênticas e estáveis |
| ARCH-05 | Estoque como ledger de movimentos (soma, não contador mutável) já é o padrão usado aqui (`StockMovement` + `SUM()`) — alinhado com a prática de mercado (outbox/ledger pattern) para evitar contenção de escrita em sistemas de estoque multi-escritor | Média | Confirma que a escolha atual está certa; não é uma pendência |
| ARCH-06 | ERPs maduros (Odoo, ERPNext) isolam lógica fiscal específica de país atrás de uma interface bem definida, em vez de embutir o parsing direto no handler de compras — relevante apenas se o projeto vier a precisar de um segundo tipo de documento fiscal ou fluxo de exportação | Baixa-média (boa prática geral, não checklist obrigatório) | Não é ação agora — manter em mente se escopo fiscal crescer |

---

## Próximos passos

**Concluído em 2026-09-16** (commits `48ebd32`, `4a549e3`, `58259d8`, `b51849b`, `ffd9066`, `a478793`): todos os itens CRÍTICO, mais SEC-02, BUG-02, UX-01, SEC-01 e NFE-01. Ver status por item nas tabelas acima.

**Pendente:**
1. UX-02 (validação client-side nos formulários CRUD) — único item ALTO do sumário executivo ainda em aberto.
2. Itens MÉDIO ainda não atacados: DB-02 (ondelete em FKs), SEC-03/SEC-04, PERF-05, DEAD-02/03/04, UX-03/04/05/06.
3. Revisar os itens PONTO A VALIDAR (seções 1 e 2) — confirmar quais são exceções arquiteturais conscientes.
4. Escolher o próximo item para virar `feat/<nome-descritivo>`, retomando o protocolo completo (compreensão → decomposição → desenho da solução → revisão crítica) antes de implementar.

## Dimensões cobertas nesta auditoria

Arquitetura/estrutura (backend e frontend) · segurança · banco de dados · NFe e processamento em lote · lógica de negócio (bugs reais) · concorrência em todos os domínios · performance (N+1, paginação, índices) · UX/acessibilidade/tratamento de erro do frontend · código morto e TODOs · pesquisa de práticas de mercado.

**Ainda não coberto** (fora do escopo desta rodada, listar aqui se decidirmos aprofundar depois): testes de carga reais (números acima são estimativas de leitura de código, não benchmark), auditoria de dependências além do que o CI já roda (pip-audit/npm audit), revisão de UX em dispositivos móveis/telas pequenas, i18n (o projeto assume português fixo).
