# Dashboard — Weekly Review Board

Pauta automatizada da Weekly Review (Segunda 9h, 30 min).

---

## Última review

```dataview
TABLE WITHOUT ID
  file.link AS "Review",
  week_of AS "Semana",
  attendees AS "Participantes"
FROM "12 - Dashboards & Reviews"
WHERE type = "weekly-review"
SORT week_of DESC
LIMIT 4
```

---

## Decisions a discutir

### Propostas sem resolução

```dataview
TABLE WITHOUT ID
  file.link AS "Decision",
  decided_at AS "Aberta",
  (date(today) - date(decided_at)).day AS "Dias"
FROM "09 - Decisions"
WHERE type = "decision" AND status = "proposed"
SORT decided_at ASC
```

### Aceitas mas não implementadas

```dataview
TABLE WITHOUT ID
  file.link AS "Decision",
  status AS "Status",
  decided_at AS "Decidida"
FROM "09 - Decisions"
WHERE type = "decision" AND status = "accepted"
SORT decided_at ASC
```

---

## Learnings abertos

```dataview
TABLE
  severity AS "Sev",
  opened_at AS "Aberto",
  deadline AS "Prazo"
FROM "08 - Learnings"
WHERE type = "learning" AND status != "closed"
SORT deadline ASC
```

---

## Eventos da semana

```dataview
TABLE
  event_date AS "Data",
  client_type AS "Tipo",
  guests AS "Conv.",
  margin_projected AS "Margem proj."
FROM "07 - Events"
WHERE type = "event"
  AND date(event_date) >= date(today)
  AND date(event_date) <= date(today) + dur(7 days)
SORT event_date ASC
```

---

## Eventos encerrados na última semana

```dataview
TABLE
  event_date AS "Data",
  margin_real AS "Margem real",
  margin_projected AS "Margem proj."
FROM "07 - Events"
WHERE type = "event"
  AND status = "closed"
  AND date(reconciled_at) >= date(today) - dur(7 days)
SORT reconciled_at DESC
```

---

Tags: `#dashboard`  `#weekly`
Links: `[[Operational Rhythms]]` • `[[Template - Weekly Review]]`
