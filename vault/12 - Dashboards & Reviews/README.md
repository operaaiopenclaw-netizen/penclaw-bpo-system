# 12 - Dashboards & Reviews

**Propósito**: views agregadas sobre o próprio vault, via plugin **Dataview**. Usadas em Weekly Review, Risk Board, decisão retroativa.

## Requisitos

- Plugin **Dataview** instalado (obsidian://show-plugin?id=dataview).
- Dataview settings:
  - Enable JavaScript Queries: **on** (recomendado, mas não obrigatório — todos os dashboards aqui rodam com DQL simples).
  - Enable Inline Queries: **on**.

## Dashboards disponíveis

- `[[Dashboard - Operational Risk Board]]` — incidentes abertos, alertas críticos recentes, eventos em zona amarela.
- `[[Dashboard - Weekly Review Board]]` — pauta automatizada da Segunda 9h.
- `[[Dashboard - Decision Tracker]]` — todas as Decisions por status, com envelhecimento.
- `[[Dashboard - Learning Index]]` — todos os Learnings, priorizando os sem próximo passo em 30d.
- `[[Dashboard - Supplier Performance Overview]]` — fornecedores por tier e score.

## Regra de dashboards

- Um dashboard é **view**, não fonte. A fonte são as notas individuais com frontmatter.
- Dashboard que fica "desalinhado" com a realidade é sinal de que o frontmatter das notas está errado, nunca o contrário.
- Dashboards são diff-friendly: se precisar mudar uma query, mude na nota do dashboard, não em muitas notas.
