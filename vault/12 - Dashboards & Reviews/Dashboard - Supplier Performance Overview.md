# Dashboard — Supplier Performance Overview

Fornecedores por tier e saúde. Auditoria de `[[Supplier Segmentation]]`.

---

## Primary — performance

```dataview
TABLE WITHOUT ID
  file.link AS "Fornecedor",
  lead_time_hours AS "Lead (h)",
  price_variance_index AS "Var. preço",
  reliability_score AS "Score",
  last_reviewed_at AS "Rev. em"
FROM "05 - Supply & Inventory"
WHERE type = "supplier" AND tier = "primary" AND status = "active"
SORT reliability_score DESC
```

Alerta: primary com `lead_time_hours > 96` ou `price_variance_index > 0.10` é candidato a rebaixamento.

---

## Secondary

```dataview
TABLE WITHOUT ID
  file.link AS "Fornecedor",
  lead_time_hours AS "Lead (h)",
  price_variance_index AS "Var. preço",
  reliability_score AS "Score"
FROM "05 - Supply & Inventory"
WHERE type = "supplier" AND tier = "secondary" AND status = "active"
SORT reliability_score DESC
```

Secondary com alta performance (lead ≤ 72h + variância ≤ 5%) é candidato a promoção para primary.

---

## Em probation

```dataview
TABLE WITHOUT ID
  file.link AS "Fornecedor",
  tier AS "Tier",
  last_reviewed_at AS "Última revisão"
FROM "05 - Supply & Inventory"
WHERE type = "supplier" AND status = "probation"
SORT last_reviewed_at ASC
```

---

## Blacklisted

```dataview
TABLE WITHOUT ID
  file.link AS "Fornecedor",
  last_reviewed_at AS "Banido em"
FROM "05 - Supply & Inventory"
WHERE type = "supplier" AND status = "blacklisted"
```

---

## Contagem por categoria × tier

```dataview
TABLE WITHOUT ID
  tier AS "Tier",
  length(rows) AS "Qtd"
FROM "05 - Supply & Inventory"
WHERE type = "supplier" AND status = "active"
GROUP BY tier
```

---

Tags: `#dashboard`  `#supply`
Links: `[[Supplier Segmentation]]` • `[[Template - Supplier]]`
