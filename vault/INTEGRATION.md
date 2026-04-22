# Integração ORKESTRA ↔ Obsidian

Fluxo de informação entre o sistema operacional e o vault de conhecimento. Cada linha abaixo é um **gatilho** ORKESTRA que deve virar uma nota aqui.

---

## Gatilhos → Notas

| Evento no ORKESTRA | Nota a criar | Pasta | Template |
|---|---|---|---|
| Alerta `MARGEM_REAL_CRITICA` ack'd | Incident + Learning | `08 - Learnings` | `[[Template - Incident]]` + `[[Template - Learning]]` |
| `RECONCILIACAO_VARIANCIA_ALTA` 3× no mesmo item | Pattern candidate | `08 - Learnings` | `[[Template - Learning]]` |
| Escolha entre 2+ fornecedores em PO | Decision | `09 - Decisions` | `[[Template - Decision]]` |
| Novo evento fechado (Contract signed) | Event | `07 - Events` | `[[Template - Event]]` |
| Incidente em cozinha (queimadura, falha equipamento) | Incident | `08 - Learnings` | `[[Template - Incident]]` |
| Mudança em política de comissão/margem | Decision + SOP update | `09 - Decisions` + `10 - SOPs` | `[[Template - Decision]]` |
| Novo fornecedor adicionado | Supplier profile | `05 - Supply & Inventory` | `[[Template - Supplier]]` |
| 3 learnings com mesma causa raiz | SOP candidate | `10 - SOPs` | `[[Template - SOP]]` |

---

## Como criar uma nota a partir de um alerta

1. No ORKESTRA, pegar o `alertId` + `eventId` + payload.
2. Abrir Obsidian → `Ctrl+N` → nome conforme convenção (ex: `Incident - 2026-04-22 - vinho curto Yohanna`).
3. Colar template `[[Template - Incident]]`.
4. Preencher:
   - Link do alerta: `orkestra://alerts/<alertId>` (ou colar o ID)
   - Link do evento: `[[Event - Yohanna 15 anos 2026-04]]`
   - Timestamp do ack
5. Ao final, marcar 1-2 **Learnings** derivadas em `## Learnings`.
6. Cada Learning vira uma nota própria em `08 - Learnings/`, linkada de volta.

> Regra: alerta sem nota em 48h = alerta esquecido. O vault é a memória institucional que o Postgres não preserva.

---

## Como converter uma decisão em SOP

Uma **Decision** documenta: "decidimos X entre alternativas {Y, Z} por essas razões". Ela é **pontual no tempo**.

Uma **SOP** documenta: "sempre que Y acontecer, execute X". Ela é **repetível**.

Promoção Decision → SOP quando:

- A decisão foi aplicada 3+ vezes com sucesso
- Outros na equipe precisam replicar sem reabrir o debate
- O contexto onde se aplica é identificável por alguém que não estava na decisão original

Procedimento:

1. Abrir a Decision relevante.
2. Criar nova nota com `[[Template - SOP]]`.
3. Na seção `## Quando aplicar` da SOP, descrever o gatilho.
4. Na seção `## Passos`, codificar o "como".
5. Linkar de volta na Decision: `## Resultado → codificado em [[SOP - <Nome>]]`.

---

## Como converter um learning em mudança de sistema

Um **Learning** sozinho não muda nada. Ele precisa virar:

- (a) uma **Decision** (mudança explícita de política / regra), OU
- (b) uma **SOP** (novo procedimento operacional), OU
- (c) uma **feature no ORKESTRA** (issue técnico), OU
- (d) um **ajuste de parâmetro** (ex: `ALERT_HORIZON_DAYS`, `discountThreshold`).

Na nota de Learning, a seção `## Próximo passo` deve apontar para UM desses quatro. Learning sem próximo passo é fofoca, não aprendizado.

---

## Fluxo de revisão semanal

Segunda-feira, 9h:

1. Abrir `[[Dashboard - Weekly Review Board]]`.
2. Triar `00 - Inbox/` — cada item vira (promovido / arquivado / deletado).
3. Ler novos `Learning` da semana → decidir se algum vira SOP/Decision.
4. Revisar `[[Dashboard - Decision Tracker]]` — decisões abertas há >14 dias.
5. Atualizar `[[North Star Metrics]]` se houve mudança de número relevante.

---

## Comandos úteis no Obsidian

| Atalho | O que faz |
|---|---|
| `Ctrl+P` | Command palette — acesso a tudo |
| `Ctrl+O` | Abrir nota por nome |
| `Ctrl+Shift+F` | Busca global no vault |
| `Ctrl+N` | Nova nota |
| `Ctrl+L` | Inserir link `[[...]]` |
| `Alt+click` no link | Abre em novo painel (compara duas notas) |

Plugins recomendados: **Dataview** (requeries nos dashboards), **Templater** (auto-preencher templates), **Tasks** (rastrear checklists transversais).

---

## Sync

Recomendado: repositório git privado. Este vault **deve** estar em git (já está sob `vault/` do repo Orkestra).
- Commits: pelo menos 1×/dia se houve edição.
- Branch: commitar direto em `main` — vault não precisa de review formal.
- Conflitos: raros; resolva no markdown mesmo.

**Não use Obsidian Sync pago** — o repo já dá histórico + multi-device grátis.
