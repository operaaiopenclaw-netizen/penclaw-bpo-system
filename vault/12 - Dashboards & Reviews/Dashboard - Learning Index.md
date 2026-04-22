# Dashboard — Learning Index

Índice de todos os Learnings. Princípio #9: aprendizado tem prazo.

---

## Learnings em atraso (sem próximo passo > 30 dias)

```dataview
TABLE
  opened_at AS "Aberto",
  deadline AS "Prazo",
  severity AS "Sev",
  (date(today) - date(deadline)).day AS "Dias em atraso"
FROM "08 - Learnings"
WHERE type = "learning"
  AND status != "closed"
  AND deadline
  AND date(deadline) < date(today)
SORT deadline ASC
```

Itens aqui são automaticamente pauta do próximo Weekly Review.

---

## Learnings abertos (dentro do prazo)

```dataview
TABLE
  opened_at AS "Aberto",
  deadline AS "Prazo",
  severity AS "Sev",
  status AS "Status"
FROM "08 - Learnings"
WHERE type = "learning"
  AND status != "closed"
  AND (!deadline OR date(deadline) >= date(today))
SORT severity ASC, deadline ASC
```

---

## Fechados nos últimos 90 dias

```dataview
TABLE
  opened_at AS "Aberto",
  severity AS "Sev"
FROM "08 - Learnings"
WHERE type = "learning"
  AND status = "closed"
  AND date(opened_at) >= date(today) - dur(90 days)
SORT opened_at DESC
```

---

## Por gatilho (últimos 90 dias)

```dataview
TABLE WITHOUT ID
  trigger AS "Gatilho",
  length(rows) AS "Qtd"
FROM "08 - Learnings"
WHERE type = "learning"
  AND date(opened_at) >= date(today) - dur(90 days)
GROUP BY trigger
SORT length(rows) DESC
```

Gatilho dominante sinaliza onde o sistema está apanhando mais.

---

Tags: `#dashboard`  `#aprendizado`
Links: `[[Operating Principles]]` • `[[Template - Learning]]`
