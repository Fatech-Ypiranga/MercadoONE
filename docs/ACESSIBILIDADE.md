# MercadoONE — Acessibilidade

> Como o painel web atende pessoas com daltonismo e quem usa leitor de tela (TalkBack, VoiceOver, NVDA), e as regras para manter isso funcionando em telas novas.

---

## Resumo

| Recurso | Para quem | Onde fica |
|---------|-----------|-----------|
| Modo para daltonismo | Protanopia, deuteranopia, tritanopia, acromatopsia e as variações "-anomalia" | Ícone de olho no cabeçalho do painel e no canto superior direito do login/cadastro |
| Suporte a leitor de tela | Usuários de TalkBack (Android), VoiceOver (iOS/macOS), NVDA/JAWS (Windows) | Embutido em todo o app, não tem botão para ligar |

---

## 1. Modo para daltonismo

### Como o usuário usa

1. Clicar no **ícone de olho** no cabeçalho (ou no canto da tela de login).
2. Escolher o modo:

| Opção | Cobre | Troca aplicada |
|-------|-------|----------------|
| Padrão | — | Cores originais |
| Protanopia | Protanopia e protanomalia (vermelho) | Erro → laranja · Sucesso → azul |
| Deuteranopia | Deuteranopia e deuteranomalia (verde) | Erro → vermelho-alaranjado · Sucesso → azul |
| Tritanopia | Tritanopia e tritanomalia (azul/amarelo) | Erro → vermelho-rosado · Sucesso → ciano |
| Acromatopsia | Monocromacia (sem percepção de cor) | Tudo em tons de cinza com claridades bem diferentes |

A escolha fica salva no navegador (`localStorage`) e vale para todas as telas, inclusive com o tema escuro.

### Como funciona

- O modo ativo vai no atributo `data-cvd` do `<html>` (ex.: `<html data-cvd="tritanopia">`). No modo Padrão o atributo não existe.
- [`frontend/app/globals.css`](../frontend/app/globals.css) tem um bloco por modo (claro e escuro) que redefine **só as cores com significado**: `--success`, `--destructive` e `--chart-1` a `--chart-5`. A cor da marca (navy) não muda.
- As paletas partem da paleta Okabe-Ito, que é segura para os três tipos de dicromacia. Os pares (erro × sucesso, séries de gráfico) foram escolhidos para diferirem também em **luminosidade**, não só em matiz.
- Em qualquer modo daltônico, `.text-destructive` fica em **negrito**: uma pista que não depende de cor (essencial na acromatopsia).
- Um script inline no `<head>` ([`frontend/app/layout.tsx`](../frontend/app/layout.tsx)) aplica o modo salvo **antes** da hidratação, para as cores padrão não piscarem no carregamento.

| Arquivo | Papel |
|---------|-------|
| [`frontend/lib/color-vision.ts`](../frontend/lib/color-vision.ts) | Lista de modos, rótulos, leitura/validação da preferência, script de inicialização |
| [`frontend/lib/color-vision.test.ts`](../frontend/lib/color-vision.test.ts) | Testes (`npm test`) |
| [`frontend/components/color-vision-select.tsx`](../frontend/components/color-vision-select.tsx) | Seletor (ícone de olho) |
| [`frontend/app/(auth)/layout.tsx`](<../frontend/app/(auth)/layout.tsx>) | Exibe o seletor no login e no cadastro |

### Regras para telas novas

- **Nunca use cores fixas** do Tailwind (`text-red-600`, `bg-green-500`, `#e11d48`…) para transmitir significado. Use os tokens semânticos: `text-destructive`, `bg-success`, `var(--color-chart-2)` etc. Cor fixa não é trocada pelos modos e quebra o recurso naquela tela.
- Em gráficos (Recharts), use `fill="var(--color-chart-N)"`, `var(--color-destructive)` ou `var(--color-primary)`.
- **Cor nunca pode ser a única informação.** Status precisa de texto ou ícone junto (ex.: um `Badge` com "Cancelada", não só uma bolinha vermelha).

### Como adicionar um modo novo

1. Incluir o valor em `COLOR_VISION_MODES` e o rótulo em `COLOR_VISION_OPTIONS` ([`color-vision.ts`](../frontend/lib/color-vision.ts)).
2. Criar os blocos `[data-cvd="novo"]` e `.dark[data-cvd="novo"]` em `globals.css`.
3. Rodar `npm test`: o teste já percorre todos os modos da lista.

---

## 2. Suporte a leitor de tela (TalkBack)

### O que já está implementado

| Recurso | Onde | O que o leitor faz |
|---------|------|--------------------|
| Link "Pular para o conteúdo" | [`app/(app)/layout.tsx`](<../frontend/app/(app)/layout.tsx>) | Primeiro item focável; leva direto ao `<main id="conteudo">` sem passar pelo menu |
| Regiões de navegação nomeadas | [`nav-rail.tsx`](../frontend/components/nav-rail.tsx), [`app-sidebar.tsx`](../frontend/components/app-sidebar.tsx) | Anuncia "Seções", "Menu principal" e o nome da seção atual |
| Item de menu atual | Mesmos arquivos (`aria-current`) | Anuncia qual é a página atual |
| Ícones da barra lateral | `nav-rail.tsx` (`aria-label`) | Lê o nome da seção, não "link" sem nome |
| Botão de menu (mobile) | [`app-header.tsx`](../frontend/components/app-header.tsx) (`aria-expanded`) | Diz se o menu está aberto ou fechado |
| Ordenação de tabelas | [`ui/data-table.tsx`](../frontend/components/ui/data-table.tsx) (`aria-sort` + texto oculto) | "em ordem crescente", "em ordem decrescente" ou "ordenar" |
| Erros de formulário e de servidor | Páginas de cadastro, login (`role="alert"`) | Lê o erro assim que ele aparece |
| Carregamentos | [`ui-states.tsx`](../frontend/components/ui-states.tsx) `LoadingState`, telas de sessão (`role="status"`) | Anuncia "Carregando…" sem interromper |
| Ícones decorativos | `aria-hidden` | São ignorados, sem ruído na leitura |

### Regras para telas novas

- **Botão só com ícone precisa de `aria-label`** (ex.: `aria-label="Editar produto"`). `title` sozinho não é lido de forma confiável pelo TalkBack.
- **Mensagem de erro que aparece depois de uma ação**: `<p role="alert" className="text-sm text-destructive">`. Aviso fixo que já está na tela ao abrir **não** leva `role="alert"`, senão é anunciado toda vez que a tela abre.
- **Carregamento**: use o `LoadingState` (já tem `role="status"`) em vez de um `<p>` solto.
- **Toda página tem um `<h1>`**: o `PageHeader` já cria. TalkBack navega por títulos.
- **Tabelas**: use o `DataTable`, que já anuncia a ordenação.
- **Ícone ao lado de texto** recebe `aria-hidden`, para o leitor não ler o nome do ícone.
- **Campos de formulário** precisam de `<Label htmlFor>` ligado ao `id` do campo.
- **Foco visível**: não remova o anel de foco (`focus-visible:ring-*`) dos componentes.

---

## 3. Como testar

### Daltonismo

1. Rodar o painel (`npm run dev` em `frontend/`) e trocar os modos pelo ícone de olho.
2. Conferir dashboard, relatórios (gráficos) e um formulário com erro, nos temas claro **e** escuro.
3. Para ver como uma pessoa daltônica enxerga: Chrome DevTools → menu ⋮ → *More tools* → **Rendering** → *Emulate vision deficiencies*. Com o modo correspondente ligado no app, erro e sucesso devem continuar distinguíveis.

### TalkBack (Android)

1. **Configurações → Acessibilidade → TalkBack → Ativar.** Atalho: segurar os dois botões de volume por 3 segundos.
2. Abrir o painel no Chrome do celular.
3. Gestos básicos: **deslizar para a direita/esquerda** passa para o próximo/anterior item; **toque duplo** ativa; **deslizar para baixo e depois para a direita** abre o menu do leitor (navegar por títulos, links etc.).
4. Roteiro mínimo:
   - O primeiro item lido é "Pular para o conteúdo".
   - No menu, o item atual é anunciado como página atual.
   - Numa tabela, tocar no cabeçalho de uma coluna anuncia a ordenação.
   - Enviar um formulário vazio: o erro é lido sem precisar procurá-lo.

### No computador

- **NVDA** (Windows, gratuito) ou **VoiceOver** (macOS: `Cmd + F5`) seguem o mesmo roteiro.
- Chrome DevTools → **Lighthouse** → categoria *Accessibility* dá uma auditoria automática rápida.

---

## Limitações conhecidas

- O seletor de daltonismo troca as cores com significado, não a interface inteira. Imagens e logos não são alterados.
- Os gráficos do Recharts não descrevem os dados em texto para o leitor de tela. Os mesmos números aparecem nas tabelas e nos cards da página.
- Os campos de formulário ainda não ligam a mensagem de erro ao campo com `aria-describedby`. O erro é anunciado (`role="alert"`), mas não é relido quando o foco volta ao campo.
