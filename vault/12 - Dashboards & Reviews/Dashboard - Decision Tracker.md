# Dashboard — Decision Tracker

Todas as Decisions do vault por status. Auditoria de governança.

---

## Propostas abertas (envelhecimento)

```dataview
TABLE WITHOUT ID
  file.link AS "Decision",
  decision_id AS "ID",
  decided_at AS "Aberta em",
  (date(today) - date(decided_at)).day AS "Dias abertos"
FROM "09 - Decisions"
WHERE type = "decision" AND status = "proposed"
SORT decided_at ASC
```

Qualquer proposta aberta > 14 dias vai automaticamente para Weekly Review.

---

## Aceitas, não implementadas

```dataview
TABLE WITHOUT ID
  file.link AS "Decision",
  decision_id AS "ID",
  decided_at AS "Decidida",
  decided_by AS "Por"
FROM "09 - Decisions"
WHERE type = "decision" AND status = "accepted"
SORT decided_at ASC
```

---

## Implementadas (últimas 10)

```dataview
TABLE WITHOUT ID
  file.link AS "Decision",
  decision_id AS "ID",
  decided_at AS "Data",
  decided_by AS "Por"
FROM "09 - Decisions"
WHERE type = "decision" AND status = "implemented"
SORT decided_at DESC
LIMIT 10
```

---

## Superseded

```dataview
TABLE WITHOUT ID
  file.link AS "Decision",
  decision_id AS "ID",
  supersedes AS "Substitui"
FROM "09 - Decisions"
WHERE type = "decision" AND status = "superseded"
SORT decided_at DESC
```

---

## Contagem por status

```dataview
TABLE WITHOUT ID
  status AS "Status",
  length(rows) AS "Quantidade"
FROM "09 - Decisions"
WHERE type = "decision"
GROUP BY status
```

---

Tags: `#dashboard`  `#decisao`  `#governanca`
Links: `[[Operating Principles]]` • `[[Template - Decision]]`
