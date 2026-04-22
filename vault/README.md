# ORKESTRA.AI — Knowledge Operating System

Este vault é a **camada de inteligência** sobre o ORKESTRA.AI. Ele não substitui o sistema operacional — ele o **explica**, **questiona** e **melhora**.

---

## Por que este vault existe

O ORKESTRA.AI (Postgres + agentes + dashboards) responde **"o que está acontecendo?"**.
Este vault responde **"por que decidimos assim?"**, **"o que aprendemos com isso?"** e **"como fazemos da próxima vez?"**.

| ORKESTRA (sistema) | Obsidian (este vault) |
|---|---|
| Dados ao vivo (contratos, estoque, parcelas) | Decisões, padrões, lições |
| Alertas em tempo real | Playbooks de resposta a alertas |
| Margem real por evento | Framework de margem (como pensamos) |
| Forecast numérico | Por que acreditamos nesse forecast |
| CommissionEntry (Postgres) | Commission Policy (neste vault) |
| Event (id UUID) | Event — Yohanna 15 anos (nota narrativa) |

Regra de ouro: **se é dado transacional ou estado ao vivo, não entra aqui**. Se é conhecimento que persiste além do evento específico, entra.

---

## Estrutura do vault

```
00 - Inbox/                 ← captura rápida; triagem em 48h
01 - Executive/             ← missão, métricas, princípios
02 - Operations/            ← ritmos, taxonomia de alertas
03 - Commercial/            ← comissão, ICP, playbooks
04 - Finance/               ← margem, clawback, fechamento
05 - Supply & Inventory/    ← política de fornecedores
06 - Production/            ← regras de estações, turnos
07 - Events/                ← uma nota por evento real
08 - Learnings/             ← lições pós-evento, incidente
09 - Decisions/             ← registro de decisões (ADR-style)
10 - SOPs/                  ← procedimentos operacionais padrão
11 - Templates/             ← templates para novas notas
12 - Dashboards & Reviews/  ← visões transversais via Dataview
99 - Archive/               ← arquivamento de notas obsoletas
```

---

## Workflow diário

1. **Captura (Inbox)**: qualquer insight, ideia solta, link do Telegram, observação do operador vai em `00 - Inbox/`. Nome do arquivo não importa — só não esquecer de capturar.
2. **Ação imediata**: se a nota demanda ação no ORKESTRA (atualizar estoque, aprovar compra), faça **no sistema**, não aqui.
3. **Fim do dia**: abrir `12 - Dashboards & Reviews/Dashboard - Operational Risk Board` e olhar alertas ativos. Qualquer alerta ack'd que gerou aprendizado → criar `Learning`.

## Workflow semanal

1. **Segunda, 9h** — Weekly Review: abrir template `[[Template - Weekly Review]]`. Dura 30 min. Revisa KPIs, decisões pendentes, learnings capturados.
2. **Triagem do Inbox**: todo item do `00 - Inbox/` deve ser arquivado, promovido para uma nota estruturada, ou deletado em até 7 dias.
3. **Decisões abertas**: revisar `[[Dashboard - Decision Tracker]]`. Decisão aberta há >14 dias = debt.
4. **Padrões emergentes**: 3 learnings similares em semanas consecutivas = candidato a virar SOP. Criar issue em `10 - SOPs/`.

---

## Regras de uso

1. **Nenhum dado operacional ao vivo.** Nada de "estoque atual de farinha" — isso mora no Postgres.
2. **Um conceito por nota.** Se precisar de seção "Outros assuntos", é hora de quebrar em 2 notas.
3. **Link em vez de copiar.** Não duplique — use `[[...]]`.
4. **Tags > pastas para navegação transversal.** Pasta = domicílio único. Tag = categoria que atravessa pastas.
5. **Timestamps só onde importam.** Events, Decisions, Learnings, Incidents sempre com data.
6. **Curte o backlog.** 50 notas de qualidade > 500 de baixa.
7. **Quando em dúvida, arquive.** É mais fácil ressuscitar do `99 - Archive/` do que deletar.

---

## Convenção de nomenclatura

| Tipo | Padrão | Exemplo |
|---|---|---|
| Event | `Event - <Nome> <AAAA-MM>` | `Event - Yohanna 15 anos 2026-04` |
| Decision | `Decision - <Slug>` | `Decision - Commission on margin not revenue` |
| Learning | `Learning - <Slug>` | `Learning - Forecast undershoot vinho tinto` |
| Incident | `Incident - <AAAA-MM-DD> - <slug>` | `Incident - 2026-03-12 - falta de gelo Yohanna` |
| SOP | `SOP - <Ação>` | `SOP - Stockout Response` |
| Supplier | `Supplier - <Nome>` | `Supplier - Adega Curitiba` |
| Template | `Template - <Tipo>` | `Template - Event` |
| Dashboard | `Dashboard - <Título>` | `Dashboard - Weekly Review Board` |

Nunca use caracteres especiais no nome (Obsidian rejeita `/`, `\`, `:`, `?`, `*`).

---

## Sistema de tags

Obsidian trata tags como classificação transversal — use-as para consultar padrões, não para organizar.

| Tag | Quando usar |
|---|---|
| `#evento` | Qualquer nota que fala sobre um evento específico |
| `#decisao` | Nota que registra uma decisão com alternativas consideradas |
| `#fornecedor` | Nota que descreve comportamento/política de um fornecedor |
| `#incidente` | Evento não-planejado com impacto operacional |
| `#forecast` | Tópico de previsão (qualitativa, não número) |
| `#margem` | Discussão sobre margem, pricing, rentabilidade |
| `#estoque` | Discussão sobre inventário, stockout, reposição |
| `#producao` | Operação de cozinha, estações, turnos |
| `#aprendizado` | Lição pós-evento, padrão observado |
| `#sop` | Procedimento padrão ou candidato a virar SOP |
| `#risco` | Risco identificado que ainda não virou incidente |
| `#prioridade-alta` | Demanda atenção desta semana |

**Combine tags.** `#decisao #margem` é ADR sobre margem. `#aprendizado #estoque #prioridade-alta` é lição urgente sobre inventário.

---

## Estratégia de links

Este vault funciona como um grafo. Cada nota deve linkar pelo menos **uma** outra — senão é uma ilha e vai virar pó.

Caminhos de link típicos:

- **Event** → **Supplier(es)** + **Decision(s)** + **Learning(s)** + **Incident(s)**
- **Supplier** → **Event(s)** onde atuou + **Incident(s)** causados
- **Decision** → **Outcome** (learning que validou ou refutou a decisão) + **SOP(s)** que nasceram dela
- **Learning** → **Event** que gerou + **Decision** que mudou por causa dela + **SOP** que codificou
- **SOP** → **Decision(s)** que embasaram + **Incident(s)** que a SOP previne

Veja `[[INTEGRATION]]` para como converter output do sistema em notas aqui.

---

## Para começar

1. Leia `[[INTEGRATION]]`.
2. Explore `[[Dashboard - Weekly Review Board]]`.
3. Duplique `[[Template - Event]]` na próxima nota que criar.

Dúvidas sobre o vault → Telegram `@orkestra-admin`.
