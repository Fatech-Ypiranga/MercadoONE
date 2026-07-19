# Appsmith — operações da gestora (PyERP)

Painel **externo** ao ERP. Cadastro self-service continua na landing (`/cadastro`);
a gestora avalia, aprova e rejeita aqui.

## Ambientes

| Env | URL da API | Quando usar |
|-----|------------|-------------|
| **Prod** | `https://api-prod-prod.up.railway.app` | Operação real |
| **Local** | `http://SEU_IP_LAN:8000` (ex. `http://192.168.15.11:8000`) | Dev / teste |

> Não use `localhost`, `127.0.0.1` nem `host.docker.internal` no Appsmith Docker (“Host not allowed” / connection refused).

### Pré-requisito Prod

1. Código de `company-registrations` **deployado** em `api-prod` (sem isso o GET retorna 404).
2. Variável `PLATFORM_API_KEY` no Railway (`api-prod`).
3. No datasource Appsmith, header `X-Platform-Key` = **só o valor** da key (sem `PLATFORM_API_KEY=`).

Gerar/atualizar a key no Railway (serviço já linkado):

```bash
railway variables --set "PLATFORM_API_KEY=$(openssl rand -hex 32)"
```

## Subir Appsmith (local)

```bash
cd ops/appsmith
docker compose up -d
```

UI: http://localhost:8088

Porta padrão do host: **8088** (8080 costuma estar com pgAdmin).

## Datasource (prod)

1. Datasources → **Authenticated API** (ou REST API)
2. Nome: `PyERP Prod`
3. URL: `https://api-prod-prod.up.railway.app`
4. Header:
   - Key: `X-Platform-Key` (sem `:`)
   - Value: valor de `PLATFORM_API_KEY` do Railway
5. Authentication: **None**
6. Environments Appsmith: use **Production** no datasource prod; se quiser, crie um segundo datasource `PyERP Local` para IP LAN.

## App operacional (UX recomendada)

### Queries

| Nome | Method | Path |
|------|--------|------|
| `listPending` | GET | `/company-registrations/?status=pending&limit=100` |
| `listAll` | GET | `/company-registrations/?limit=100` (sem status, ou filtro na UI) |
| `approve` | POST | `/company-registrations/{{TablePending.selectedRow.id}}/approve` body `{}` |
| `reject` | POST | `/company-registrations/{{TablePending.selectedRow.id}}/reject` body JSON abaixo |

Body `reject`:

```json
{
  "notes": "{{InputRejectNotes.text}}"
}
```

Marque `listPending` com **Run on page load**.

### Layout sugerido (uma página)

1. **Text** título: `Cadastros de empresas — pendentes`
2. **Button** “Atualizar” → onClick JS: `listPending.run()`
3. **Table** `TablePending` — Table data: `{{listPending.data.items}}`
   - Colunas úteis: `id`, `legal_name`, `document`, `admin_email`, `admin_name`, `declared_store_count`, `created_at`, `status`
4. **Text** resumo: `{{"Pendentes: " + (listPending.data.total || 0)}}`
5. **Input** `InputRejectNotes` — placeholder “Motivo da rejeição”
6. **Button** Aprovar (verde) / **Button** Rejeitar (vermelho)
7. Opcional: segunda Table `TableHistory` com `listAll` + filtro approved/rejected (tabs ou Select)

### onClick — Aprovar (JS, sem `return Api1.run()`)

```js
approve.run(
  (data) => {
    showAlert(
      "Aprovado — " + data.admin_email +
      " | user: " + data.admin_username +
      " | senha: " + data.temporary_password,
      "success"
    );
    listPending.run();
  },
  (err) => {
    showAlert(
      (err && (err.message || err.error)) || "Falha ao aprovar",
      "error"
    );
  }
)
```

Guarde a senha do alert — **só aparece uma vez**.

### onClick — Rejeitar (JS)

```js
reject.run(
  () => {
    showAlert("Rejeitado", "success");
    listPending.run();
    InputRejectNotes.setValue("");
  },
  (err) => {
    showAlert(
      (err && (err.message || err.error)) || "Falha ao rejeitar",
      "error"
    );
  }
)
```

### Checklist visual rápido

- [ ] Datasource aponta para **prod** HTTPS
- [ ] Header sem `PLATFORM_API_KEY=`
- [ ] Table usa `.data.items` (não o envelope inteiro)
- [ ] Selecionar linha antes de aprovar/rejeitar
- [ ] Botão Atualizar + run on page load
- [ ] Alert de senha no approve; refresh da lista sem `return` na promise

## Contrato da API

| Method | Path | Auth |
|--------|------|------|
| GET | `/company-registrations/?status=pending` | `X-Platform-Key` |
| GET | `/company-registrations/{id}` | `X-Platform-Key` |
| POST | `/company-registrations/{id}/approve` | `X-Platform-Key` |
| POST | `/company-registrations/{id}/reject` | `X-Platform-Key` |
| POST | `/company-registrations/` | público (landing) |

Self-service da landing **não** usa Appsmith.

## Outros usos do Appsmith (gestora)

Além da fila de cadastro, o Appsmith serve bem para ops internas sem poluir o ERP:

| Ideia | Como |
|-------|------|
| **Histórico de solicitações** | `listAll` + Table filtrável (approved/rejected) |
| **Reset de tenant / checagens** | Queries autenticadas por API key só de leitura quando existirem endpoints platform |
| **Monitor simples** | GET `/` health da API prod/dev em cards |
| **Fila comercial 16+ lojas** | Planilha/CRM no Appsmith (ou Google Sheets datasource) para leads que não passam no self-service |
| **Auditoria leve** | Export CSV da Table de registrations para compartilhar com vendas |

Evitar no Appsmith (ficar no ERP): cadastro de produtos, PDV, estoque do dia a dia do tenant.

## Troubleshooting

| Sintoma | Causa comum |
|---------|-------------|
| Host not allowed | URL com `host.docker.internal` / localhost |
| Connection refused | API local sem `--host 0.0.0.0` ou API parada |
| 401 | Key errada / colou `PLATFORM_API_KEY=` no value |
| 404 nos registrations | Código ainda não deployado no `api-prod` |
| Sucesso + erro no approve | `return listPending.run()` no callback — remova o `return` |
| `listPending is not defined` | Nome real da query é outro (`Api1`) — use o nome exato |
