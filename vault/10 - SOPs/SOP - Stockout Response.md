---
type: sop
sop_id: SOP-002
owner: operator
last_verified_at: 2026-04-22
tags: [sop, supply, stockout, emergencia]
---

# SOP — Stockout Response

Procedimento quando alerta `STOCKOUT_IMINENTE` (CRITICAL) dispara — estoque projetado de um item crítico < consumo previsto para evento em < 24h.

## Gatilho

- Alerta `STOCKOUT_IMINENTE` no `/operations/overview`.
- Pode ser disparado por: evento novo aumentando demanda de última hora, descarte/quebra em cozinha, fornecedor cancelando PO.

## Pré-requisitos

Nenhum — é emergência. Mas antes de qualquer ação externa:

- [x] Confirmar que o alerta é real (não bug de contagem): dar conferência física no item.
- [x] Confirmar evento que consome o item existe e está confirmado (não cancelado ou movido).

## Passos

### Nos primeiros 15 minutos

1. **Confirmar consumo exato projetado** — abrir `EventPlan` do evento em risco, ver quantidade final por receita × RSVP atualizado.
2. **Confirmar estoque físico** — pedir conferência presencial na cozinha do item (não confiar só no sistema).
3. **Calcular gap real**: `gap = consumo_projetado − (estoque_físico + entregas_confirmadas ≤ D)`.

### Nos próximos 60 minutos

4. **Primary push**: ligar para primary do item, confirmar se tem ajuste de quantidade possível (mesmo que com preço maior). Aceitar até +10% sobre preço de catálogo sem aprovação.
5. Se primary não atende → **Secondary**. Aceitar até +20% sobre catálogo.
6. Se secondary não atende → **Backup**. Aceitar até +40% (mas acima disso, escalar).
7. Em paralelo, avaliar **substituição de receita** — o menu tem flexibilidade? Prato alternativo com ingredientes que temos?

### Decisão Go / No-Go

8. Se gap não foi coberto em 90 min OU custo adicional > 15% do CMV do evento:

   a. Comunicar `sales_manager` e `sales` imediatamente.
   b. `sales_manager` decide: negociar substituição com cliente OU absorver custo.
   c. Nunca entregar evento com buraco de item sem comunicar cliente — preservar relação.

### Depois do evento

9. Registrar `Incident` em `08 - Learnings` com:
   - Item, quantidade, causa raiz.
   - Tier do fornecedor que atendeu no fim (quanto custou extra).
   - Se houve substituição de receita, link para plano revisto.
10. Se 2+ stockouts do mesmo item no trimestre → abrir `Decision` para aumentar **safety stock** ou promover secondary a primary.
11. Atualizar `ItemAdjustment` se o consumo projetado estava subestimado (não foi ruptura pura).

## Verificação

- Evento executou com o item na quantidade correta.
- Margem do evento fechou dentro de ±5 p.p. da projetada (se extrapolou muito, é sinal de que o SOP aceitou custo alto demais — revisar os thresholds).
- `Incident` aberto em ≤ 72h após evento.

## Rollback

Não se aplica — é SOP de resposta, não de decisão estrutural. Mas:

- Se o stockout for por bug (contagem errada), priorizar fix no `Inventory` acima da compra emergencial.
- Se for ruptura persistente de primary (> 2× no mês), **não** prossiga com primary normalmente — abra Decision para troca antes do próximo evento.

---

Tags: `#sop`  `#supply`  `#stockout`
Links: `[[Alert Taxonomy]]` • `[[Supplier Segmentation]]` • `[[Operating Principles]]`
