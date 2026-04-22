---
type: learning
status: in_progress
opened_at: 2026-04-21
deadline: 2026-05-21
trigger: reconciliacao_variancia
severity: MEDIUM
related_event: "[[Event - Yohanna 15 anos 2026-04]]"
tags: [aprendizado, cmv, forecast, ingredientes-importados]
---

# Learning — Ingredientes importados descalibram CMV

## Fato

No evento Yohanna 15 anos (2026-04-19), 4 de 161 ingredientes responderam por ~60% do desvio total de CMV:

| Item | Catálogo | Real | Δ |
|---|---|---|---|
| Trufa negra | R$ 980/kg | R$ 1.100/kg | +12.2% |
| Azeite premium | R$ 68/L | R$ 75/L | +10.3% |
| Queijo envelhecido | R$ 120/kg | R$ 130/kg | +8.3% |
| Balsâmico reserva | R$ 220/L | R$ 253/L | +15.0% |

Volume consumido: pequeno em peso, alto em valor. Resultado: CMV real R$ 16.948,97 vs projetado R$ 15.580 → margem 27% vs 32% projetados.

## Por quê (5 "porquês")

1. **Por que o CMV desviou?** Porque 4 itens importados custaram mais que o catálogo.
2. **Por que o catálogo estava desatualizado?** Porque esses itens são comprados esporadicamente (< 1×/mês), não entram na rotina de atualização semanal do preço médio.
3. **Por que não entram na rotina semanal?** Porque o job `UpdateCatalogPrices` só olha itens com > 2 movimentações nos últimos 30d.
4. **Por que esse corte existe?** Para não pesar o job com itens raros e reduzir ruído no catálogo principal.
5. **Por que ruído é problema?** Porque outros subsistemas (forecast, proposta) leem catálogo e devem ver preço estável.

Causa raiz: política de "estabilidade de catálogo" está em conflito com realidade de itens premium de baixo giro e alta volatilidade de preço. **Ambos os comportamentos são legítimos — precisam coexistir.**

## Próximo passo

**Opção proposta**: criar tabela `volatile_ingredient` com flag explícita, e sub-job `UpdateVolatileCatalog` rodando **antes de cada proposta** nesses itens. Catálogo principal continua estável; proposta já busca o preço spot.

Alternativa de curto prazo (já feita): `ItemAdjustment` manual criado para os 4 itens com ajuste médio +12%.

## Decisão alvo

A criar: `[[Decision - Tabela de ingredientes voláteis com preço spot]]`

Prazo limite: **2026-05-21** (30 dias).

## Resultado esperado

Evento similar (aniversário 15 anos social, ~120 convidados, menu com trufa/azeite/queijo importados) deve fechar com desvio de CMV ≤ 3% em 2 eventos consecutivos após a mudança.

## Status

- [x] Variância identificada e ItemAdjustment aplicado (2026-04-21)
- [ ] Decision criada em `09`
- [ ] Feature de `volatile_ingredient` shipped
- [ ] Validação em 2 eventos consecutivos

---

Tags: `#aprendizado`  `#cmv`  `#ingredientes-importados`
Links: `[[Event - Yohanna 15 anos 2026-04]]` • `[[Margin Framework]]` • `[[North Star Metrics]]`
