# North Star Metrics

Os 5 números que resumem a saúde da Orkestra.AI. Revisados trimestralmente. Qualquer decisão que **piore** um destes exige registro em `[[Dashboard - Decision Tracker]]` com justificativa.

---

## 1. Margem de contribuição média por evento

**Meta**: ≥ 30%
**Alerta**: < 25% (HIGH) • < 15% (CRITICAL)

Calculada no ORKESTRA como `(revenueTotal - cmvTotal - custos diretos) / revenueTotal` por evento consolidado.

Aqui no vault: quando cair, abrir `Learning` para entender **por quê**, não para corrigir o número.

---

## 2. Accuracy de forecast (CMV)

**Meta**: erro absoluto ≤ 10% vs CMV real
**Alerta**: > 15% (MEDIUM) • > 25% (HIGH)

Forecast ruim cascateia em compra errada, estoque morto ou stockout no evento. Este é o input mais importante do sistema.

Toda `RECONCILIACAO_VARIANCIA_ALTA` com causa raiz identificada vira `#aprendizado` aqui.

---

## 3. Tempo entre contrato → evento

**Meta**: mediana ≥ 21 dias
**Alerta**: < 14 dias (MEDIUM) porque operação fica apertada

Métrica comercial, não financeira. Eventos próximos demais comem margem em compras de última hora.

Acompanhada em `[[Dashboard - Weekly Review Board]]`.

---

## 4. Taxa de clawback de comissão

**Meta**: ≤ 3% do total provisionado em 90 dias
**Alerta**: > 5% (HIGH)

Clawback alto = vendedor fechando contrato que não se paga. Ver `[[Commission Policy]]`.

---

## 5. Lead time médio do procurement

**Meta**: 72h entre PO emitida e entrega
**Alerta**: > 120h (HIGH)

Medido só em fornecedores `tier=primary`. Secundários não entram.

---

## Como atualizar esta página

1. Abrir ORKESTRA `/operations/overview` e tomar snapshot dos 5 números.
2. Atualizar tabela abaixo **apenas se** revisão trimestral.
3. Se o valor trimestral indica tendência preocupante, criar `Learning` apontando a causa.

| Trimestre | Margem | Forecast err. | Lead contrato | Clawback | Procurement |
|---|---|---|---|---|---|
| 2026-Q1 | — | — | — | — | — |
| 2026-Q2 | — | — | — | — | — |

---

Tags: `#metricas`  `#norte`
Links: `[[Mission]]` • `[[Dashboard - Weekly Review Board]]` • `[[Commission Policy]]`
