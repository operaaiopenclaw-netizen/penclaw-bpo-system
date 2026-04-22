---
type: decision
decision_id: DEC-2026-001
status: implemented
decided_at: 2026-04-22
decided_by: [admin, finance, sales_manager]
supersedes: null
tags: [decisao, comercial, comissao, politica]
---

# Decision — Comissão sobre margem, não faturamento

## Contexto

A Orkestra.AI precisa desenhar seu motor de comissão do zero. Duas bases possíveis:

- **Faturamento (REVENUE)**: simples, comum no mercado de catering, vendedor entende na hora.
- **Margem de contribuição (MARGIN)**: alinha vendedor ao interesse da empresa, pune desconto que destrói margem, exige transparência de custo.

## Problema

Eventos com margem baixa são um dos principais riscos da operação — um vendedor comissionado sobre faturamento fecha com qualquer margem, desde que o ticket total seja grande. Isso conflita diretamente com `[[Operating Principles]]` #1 (margem antes de volume) e North Star #1 (margem média ≥ 30%).

Além disso, o motor precisa provisionar despesa realista — comissão sobre receita superestima custo quando margem é boa e subestima quando margem é ruim. Comissão sobre margem é sempre proporcional ao "valor gerado" para o negócio.

## Opções avaliadas

### A. Comissão sobre faturamento (REVENUE)
- **Prós**: padrão do mercado, vendedor se adapta rápido, mais simples explicar ao CLT.
- **Contras**: desalinhamento direto com margem; desconto é risco zero para o vendedor; forecast financeiro superestima comissão em ~30% em média.

### B. Comissão sobre margem (MARGIN)
- **Prós**: alinhamento total com North Star #1; vendedor internaliza desconto; forecast financeiro fica preciso.
- **Contras**: exige mostrar custo do CMV para o comercial (transparência interna); se cálculo de margem projetada for frágil, vendedor disputa valor.

### C. Híbrido (piso REVENUE × bônus MARGIN)
- **Prós**: transição suave para quem vem da indústria.
- **Contras**: complexidade que compensa pouco; duas curvas para explicar.

## Decisão

**Adotamos B: comissão sobre margem de contribuição projetada (`baseType=MARGIN`)**.

Para mitigar os contras:

1. Motor expõe `Contract.projectedMargin` no CRM do vendedor com detalhamento dos custos considerados.
2. Fallback para REVENUE só em contrato flagrante atípico (ex.: revenda pura sem CMV típico), com exceção registrada via nova Decision.
3. Treinamento obrigatório de 1h para todo vendedor novo sobre como ler margem.
4. Penalidade de desconto acima do limite (`discountThreshold 0.05`, `discountPenaltyPct 0.20`) previne que vendedor queime margem para fechar — ver `[[Discount Authorization Matrix]]`.

## Impacto

- **Schema**: `CommissionPlan.baseType = MARGIN` default.
- **Engine**: `src/services/commission-engine.ts` calcula sobre `contract.projectedMargin`.
- **Política**: `[[Commission Policy]]` publicada com esta base.
- **Princípio**: valida `[[Operating Principles]]` #7.

## Consequências esperadas

- Vendedor com ticket grande e margem ruim perde comissão relativa — é feature, não bug.
- Provisão de despesa (`ProvisionedExpense`) cai em ~30% no forecast vs. modelo hipotético REVENUE.
- Discussão sobre definição de "custos diretos" em `[[Margin Framework]]` torna-se crítica.

## Reversão

Para reverter, abrir Decision nova referenciando esta como `supersedes=DEC-2026-001` com evidência de que a política está causando mais dano que benefício (ex.: churn de vendedores top + cohort análise).

---

Tags: `#decisao`  `#comercial`  `#comissao`
Links: `[[Commission Policy]]` • `[[Margin Framework]]` • `[[Operating Principles]]`
