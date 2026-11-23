# Mercado One — Comparação, atualização e gráficos

Data: 23/11/2026

Este documento reúne o que foi comparado entre **MercadoONE** (Python/FastAPI + Next.js) e **Mercado-One-Java** (Spring Boot + Angular + PDV JavaFX), o que foi alterado nesta sessão, como verificar e o que ainda falta.

---

## 1. Visão geral dos dois projetos

| | MercadoONE | Mercado-One-Java |
|---|---|---|
| Foco | API/painel de gestão de empresa (multiempresa, compras por NF-e) | ERP para mercado pequeno com PDV offline |
| Backend | Python 3.11+, FastAPI, SQLModel, PostgreSQL, Alembic (15 migrações) | Java 25, Spring Boot 4.1, JPA, Flyway (9 migrações), PostgreSQL 18 |
| Painel web | Next.js 15, Tailwind, shadcn/ui, TanStack Query, Recharts | Angular 22, CSS próprio |
| PDV | Repositório separado (`pyerp-pdv`) | `pdv-desktop` (JavaFX + SQLite), offline-first |
| Deploy | Railway + Vercel, Docker | Render (`render.yaml`) |
| Último commit | 29/10/2026 | 23/11/2026 (75 commits) |

---

## 2. O que o MercadoONE tem e o Java não tem

- **Compra por NF-e (XML):** upload, leitura da nota e confirmação da compra.
- **Custo médio ponderado:** o produto tem `cost_price`, atualizado a cada compra confirmada.
- **Estoque mínimo e relatório de estoque crítico** (`min_stock`).
- **Relatório de ticket médio.**
- **Multiempresa:** empresa → filial → loja, com isolamento por empresa em todas as consultas.
- **Cadastro de empresa** (`/cadastro`) e consulta de **CEP**.
- **Cadastros completos:** cliente e fornecedor com CPF/CNPJ, inscrição estadual, nome fantasia e vários endereços.
- **Cancelamento de compra**, além do cancelamento de venda.
- **Perfis extras:** supervisor, conferente e colaborador (o Java tem admin, gerente, estoquista e operador de caixa).
- **Segurança e infraestrutura:** limite de tentativas de login, paginação padronizada `{items,total,offset,limit}`, OpenAPI publicado, scans no CI (gitleaks, Trivy, pip-audit).
- **Acessibilidade:** modo daltônico e suporte a leitor de tela, com guia próprio (`docs/ACESSIBILIDADE.md`).

## 3. O que o Java tem e o MercadoONE não tem

- **PDV desktop offline-first** (JavaFX + SQLite), com fila de vendas e sincronização.
- **Conflitos de sincronização** (preço, produto, pagamento, estoque) com tela de resolução no admin.
- **Várias formas de pagamento na mesma venda** (dinheiro, cartão, PIX, fiado).
- **Política de desconto por perfil** (`GET /api/sales/discount-policy`).
- **Venda idempotente** por `clientSaleId`.
- **Redefinição de senha por e-mail** (Azure Communication Services / SMTP).
- **Credencial local do PDV** com validade de 30 dias.
- **Leitor de código de barras USB** (modo teclado).
- **Relatórios por operador e por cliente.**
- **Backlog do MVP fechado** e documentação por assunto (`docs/produto`, `docs/arquitetura`, ADRs).

---

## 4. O que foi feito nesta sessão

### 4.1 MercadoONE (branch `feat/atualizacao-graficos`, sem commit)

**Gráficos no dashboard**
- Novo componente `frontend/components/dashboard-charts.tsx`:
  - `RevenueByDayChart`: receita por dia nos últimos 7 dias (barras).
  - `PaymentMethodChart`: receita por forma de pagamento (rosca).
- Novas funções em `frontend/lib/dashboard-metrics.ts`: `salesByDay` (preenche dias sem venda com zero e ignora vendas canceladas) e `salesByPaymentMethod` (agrupa, rotula e ordena por receita; sem forma informada vira "Não informado").
- Testes em `frontend/lib/dashboard-metrics.test.ts` (2 testes novos).
- `frontend/app/(app)/dashboard/page.tsx` passou a exibir os dois gráficos acima das tabelas.
- Os gráficos usam as variáveis `--chart-N`, que já trocam de paleta no modo daltônico, e têm `aria-label` com o resumo dos valores para leitor de tela.
- A página **Relatórios já tinha gráficos** (top produtos e estoque crítico) e não foi alterada.

**Dependências do frontend**
- `npm update` dentro dos ranges existentes.
- `next` 15.5.28 → **15.5.29**, o que zerou o `npm audit` (antes: 1 vulnerabilidade moderada).
- Arquivos alterados: `frontend/package.json` (só a linha do `next`) e `frontend/package-lock.json`.
- O backend (`requirements.txt` / `requirements.lock`) **não foi alterado**.

### 4.2 Mercado-One-Java (sem commit)

**Admin web — dashboard**
- Novo gráfico **"Vendas dos últimos 7 dias"**, sem biblioteca nova (HTML/CSS), usando `--chart-bar` e `--chart-peak` de `brand-tokens.css`. O dia de maior venda fica destacado.
- Os totais de pagamento de hoje ganharam **barras de proporção**, ordenadas do maior para o menor.
- O gráfico faz uma consulta a mais (`GET /api/sales` com `size=200` e `from` seis dias atrás). Considera só vendas `CONFIRMED`. Se houver mais de 200 vendas no período, avisa que usa apenas as primeiras 200.
- Acessível: `role="img"` com `aria-label` resumindo cada dia.
- Arquivos: `dashboard-page.component.ts`, `.html`, `.spec.ts` e `src/styles.css`.
- Os testes existentes foram ajustados para distinguir a consulta de hoje (`size=1`) da consulta da semana (`size=200`), e há um teste novo para o gráfico.

---

## 5. Verificação

| Item | Resultado |
|---|---|
| MercadoONE: `npm test` (18 testes) | passou |
| MercadoONE: ESLint e `tsc` nos arquivos alterados | sem erros |
| MercadoONE: `npm audit --omit=dev` | 0 vulnerabilidades |
| MercadoONE: `next build` | **não concluído** — o ambiente não alcança o Google Fonts (`Geist Mono`, `IBM Plex Sans`) |
| Java: `ng build` | passou |
| Java: type-check do spec (`tsc -p tsconfig.spec.json`) | passou |
| Java: testes Karma (`ng test`) | **não executados** — não há Chrome no ambiente |
| Backend Python (`pytest`) | **não executado** — sem PostgreSQL/Docker e Python 3.10 no ambiente (o projeto exige 3.11+) |

### Comandos para você rodar

```bash
# MercadoONE
cd MercadoONE/frontend
npm ci            # necessário: o node_modules desta pasta ficou inconsistente
npm test
npm run lint
npm run build

# Mercado-One-Java
cd Mercado-One-Java/admin-web
npm test -- --watch=false     # precisa de Chrome ou CHROME_BIN
```

---

## 6. Atenções

1. **`node_modules` do MercadoONE/frontend:** um `npm update` rodado diretamente na sua pasta estourou o tempo limite e deixou a pasta incompleta. Rode `npm ci` antes de usar. O `package.json` e o lock não foram afetados por esse incidente.
2. **Fim de linha:** os arquivos alterados foram gravados com LF, que é o formato guardado no Git nos dois repositórios. O Git no Windows normaliza para CRLF na sua pasta.
3. **Nada foi commitado.** No MercadoONE foi criada a branch `feat/atualizacao-graficos`; o Java continua na `main` com as alterações no working tree.
4. **O que eu havia dito sobre "42 arquivos modificados" no MercadoONE estava errado:** era só diferença de fim de linha. Não havia trabalho pendente de segurança.

---

## 7. O que falta: portar o Java para o MercadoONE

Não foi feito porque exige migrações de banco e mudanças de API que não pude testar. Ordem sugerida, da mais simples para a mais complexa.

### 7.1 Várias formas de pagamento por venda
- **Hoje no MercadoONE:** `Sale.payment_method` é um único texto (`backend/sales/models.py`).
- **No Java:** a venda tem uma lista de pagamentos (`method`, `amount`).
- **Trabalho:**
  1. Nova tabela `sale_payments` (migração Alembic) com `sale_id`, `method`, `amount`, mais cópia dos dados existentes de `payment_method`.
  2. `SaleCreateInput` aceitar `payments: [{method, amount}]`, validando que a soma cobre o total; manter `payment_method` aceito por compatibilidade.
  3. Atualizar `SaleDetailResponse`, o OpenAPI (`docs/openapi.json`) e `frontend/lib/api/schema.ts` (`npm run generate:api`).
  4. Ajustar `salesByPaymentMethod` no dashboard para somar por pagamento, não por venda.

### 7.2 Política de desconto por perfil
- Endpoint `GET /sales/discount-policy` devolvendo o percentual máximo por perfil.
- O MercadoONE já tem `supervisor_authorization` para desconto acima do limite; falta expor a política e aplicá-la de forma consistente na criação da venda.

### 7.3 Redefinição de senha por e-mail
- No Java: `POST /api/auth/password/request`, `/check` e `/confirm`, com migração `V9__user_email_and_password_reset.sql`.
- No MercadoONE: tabela de tokens de redefinição (hash, validade curta, uso único), envio de e-mail (SMTP configurável por variável de ambiente), limite de tentativas e telas "esqueci a senha" e "nova senha" no Next.js.

### 7.4 Idempotência de venda (`clientSaleId`)
- Adicionar `client_sale_id` único por empresa em `sales` e fazer o `POST /sales` devolver a venda existente quando repetido. É pré-requisito para qualquer PDV offline.

### 7.5 Sincronização offline e conflitos
- Só faz sentido se o PDV do MercadoONE (`pyerp-pdv`) for trabalhar offline.
- No Java: `POST /api/offline/sales/sync`, `GET /conflicts`, `POST /conflicts/{id}/resolve`, `GET /status`, migrações V6 e V7.
- É a maior parte do trabalho: tabelas de fila e conflito, regras de aceite (preço, produto, pagamento, estoque) e tela de resolução no painel.

### 7.6 Opcional
- Relatórios por operador e por cliente (o MercadoONE tem `user_id` e `customer_id` na venda; falta o endpoint e a tela).

---

## 8. Itens do MercadoONE que o Java ainda não tem (se quiser levar para lá)

Por ordem de esforço:
1. `min_stock` no produto e relatório de estoque crítico.
2. Relatório de ticket médio.
3. Limite de tentativas de login (rate limit).
4. Custo do produto e custo médio ponderado.
5. Cadastros de cliente e fornecedor com endereço e CNPJ.
6. Importação de compra por NF-e (maior).

O backlog do Java declara multi-loja e emissão fiscal como "fora do MVP"; trate esses itens como decisão de produto, não como defeito.
