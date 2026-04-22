# Dashboard — Operational Risk Board

View de risco operacional consolidada. Abrir antes das 10h todo dia útil.

---

## Incidentes abertos

```dataview
TABLE
  severity AS "Sev",
  status AS "Status",
  opened_at AS "Aberto em",
  related_event AS "Evento",
  related_supplier AS "Fornecedor"
FROM "08 - Learnings"
WHERE type = "incident" AND status != "closed" AND status != "resolved"
SORT severity ASC, opened_at ASC
```

---

## Incidentes CRITICAL / HIGH nos últimos 30 dias

```dataview
TABLE WITHOUT ID
  file.link AS "Incidente",
  severity AS "Sev",
  status AS "Status",
  opened_at AS "Aberto em",
  resolved_at AS "Resolvido em"
FROM "08 - Learnings"
WHERE type = "incident" AND (severity = "CRITICAL" OR severity = "HIGH")
  AND date(opened_at) >= date(today) - dur(30 days)
SORT opened_at DESC
```

---

## Eventos próximos em zona amarela / vermelha

```dataview
TABLE
  event_date AS "Data",
  guests AS "Conv.",
  margin_projected AS "Margem proj.",
  status AS "Status"
FROM "07 - Events"
WHERE type = "event"
  AND date(event_date) >= date(today)
  AND date(event_date) <= date(today) + dur(14 days)
  AND (margin_projected < 0.20 OR status = "in_execution")
SORT event_date ASC
```

---

## Learnings sem próximo passo em ≤ 7 dias do prazo

```dataview
TABLE
  opened_at AS "Aberto",
  deadline AS "Prazo",
  severity AS "Sev"
FROM "08 - Learnings"
WHERE type = "learning"
  AND status != "closed"
  AND deadline
  AND date(deadline) - date(today) <= dur(7 days)
SORT deadline ASC
```

---

Tags: `#dashboard`  `#risco`
Links: `[[Alert Taxonomy]]` • `[[Operational Rhythms]]`
