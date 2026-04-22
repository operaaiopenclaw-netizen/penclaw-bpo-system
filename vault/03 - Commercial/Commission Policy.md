# Commission Policy

Política oficial da Orkestra.AI para cálculo, provisão e pagamento de comissão. Reflete o motor implementado em `src/services/commission-engine.ts`. Qualquer divergência entre esta página e o código **é bug** — código ganha, esta página é atualizada.

Princípio-âncora: `[[Operating Principles]]` #7 — comissão alinhada à margem.

---

## 1. Base de cálculo: margem, não receita

Default: `baseType = MARGIN`. Comissão incide sobre **margem de contribuição projetada** do contrato, não sobre `totalValue`.

```
baseAmount = contract.projectedMargin
```

Se `projectedMargin` não foi preenchido na assinatura, calcular como:

```
projectedMargin = totalValue − Σ(items[i].estimatedCost × quantity)
```

Fallback para `baseType = REVENUE` só em casos de exceção, sempre com `Decision` registrada. Ver `[[Decision - Commission on margin not revenue]]`.

---

## 2. Distribuição temporal: 40 / 60

```
signing_part     = baseAmount × commissionPct × signingPct      // default 0.40
installment_part = baseAmount × commissionPct × installmentPct  // default 0.60
```

- **40% na assinatura** — LOCKED no final do mês da `signedAt`. Libera automaticamente pelo tick `releaseDueLocks` quando `scheduledFor` vence.
- **60% proporcional às parcelas** — cada `ContractInstallment` reserva uma fatia proporcional a `amount / totalValue`. Cada `Payment` CONFIRMED emite `CommissionEntry` RELEASED pelo delta pago × fatia.

Ambos entram no **forecast de despesas** (`ProvisionedExpense`) já na assinatura, com status LOCKED. Só viram RELEASED com pagamento confirmado.

---

## 3. Splits: closer, SDR, manager

Três papéis possíveis por contrato:

| Papel | Campo | Recebe | Obs |
|---|---|---|---|
| Closer | `Contract.salespersonId` | 100% − sdrSplitPct | Obrigatório. Paga sempre. |
| SDR | `Contract.sdrId` | `sdrSplitPct` (default 0.30 se preenchido) | Opcional. Se ausente, closer fica com o total. |
| Manager | `Contract.salesManagerId` | `managerOverridePct` (default 0.10) | Override sobre o total, não desconta do closer. Representa custo adicional para o BPO. |

Fórmula efetiva:

```
closer_pct      = 1 − sdrSplitPct
sdr_pct         = sdrSplitPct            (se sdrId)
manager_pct     = managerOverridePct     (adicional, se salesManagerId)
```

Todos os entries são gravados com `role` (CLOSER | SDR | MANAGER_OVERRIDE) e `effectivePct` real, para auditoria.

---

## 4. Penalidade por desconto

Se o vendedor queimou margem via desconto, queima junto a própria comissão.

```
if (discountAppliedPct > discountThreshold)
  commissionPct × = (1 − discountPenaltyPct)
```

Defaults:
- `discountThreshold = 0.05`  (5%)
- `discountPenaltyPct = 0.20` (comissão cai 20% se ultrapassou 5% de desconto)

Descontos > 10% exigem aprovação explícita — ver `[[Discount Authorization Matrix]]`.

---

## 5. Carência antes de liberar

```
scheduledFor = addDays(installment.dueDate, carencyDays)   // default 7
```

Por quê: clawback é pior que comissão atrasada (princípio #8). A carência cobre estornos de cartão, PIX contestado e ajuste de boleto pago a maior/menor.

Durante a carência o entry fica **LOCKED** — visível para o vendedor (forecast), mas não sacável.

---

## 6. Clawback

Disparadores:

1. **Cancelamento de contrato** — `onContractCancelled` muda FORECAST/LOCKED/RELEASED → CLAWED_BACK.
2. **Payment REVERSED** — re-executa `onPaymentConfirmed` com delta negativo.
3. **Margem real < 50% da projetada** — manual, via `POST /contracts/:id/clawback` com `reason`.

Se o entry já está **PAID**, o estado não muda (imutabilidade pós-pagamento). Flag `metadata.clawbackPending = true` e cria-se `Debt` a descontar da próxima folha.

Detalhes por tipo: `[[Clawback Policy]]`.

---

## 7. Imutabilidade pós-PAID

Uma vez que `CommissionEntry.status = PAID` e `paidInPayrollId` preenchido, **nenhum campo pode mudar**. Ajuste retroativo vira novo entry compensatório, nunca edit no original. Auditoria acima de tudo (princípio #3).

---

## 8. Bônus (composição diferente)

Bônus **não** está nesta política. Vive em `BonusRule` + `BonusComponent` + `BonusAccrual`, com:

- `weight` por componente, soma = 1.0
- `acceleratorBands` piecewise (ex.: 100–120% → 1.5×, > 120% → 2.0×)
- `rampUpFactor` em meses iniciais do vendedor (default 0.6 nos primeiros 3 meses)
- `maxPayout` cap por período

Métricas aceitas hoje: `REVENUE`, `MARGIN`, `EVENTS_CLOSED`, `TICKET_AVG`, `CONVERSION`. `NPS` previsto, ainda não plugado.

---

## 9. Parâmetros atuais (2026-Q2)

| Parâmetro | Valor default | Onde muda |
|---|---|---|
| `baseType` | MARGIN | `CommissionPlan` por contrato |
| `commissionPct` | 0.05 (5%) | `CommissionPlan` |
| `signingPct` / `installmentPct` | 0.40 / 0.60 | `CommissionPlan` |
| `sdrSplitPct` | 0.30 | Se `sdrId` preenchido |
| `managerOverridePct` | 0.10 | Se `salesManagerId` preenchido |
| `discountThreshold` / `discountPenaltyPct` | 0.05 / 0.20 | Global por tenant |
| `carencyDays` | 7 | `CommissionPlan` |

Mudança em qualquer um destes exige `Decision` em `09 - Decisions`.

---

Tags: `#comercial`  `#comissao`  `#politica`
Links: `[[Operating Principles]]` • `[[Clawback Policy]]` • `[[Discount Authorization Matrix]]` • `[[Decision - Commission on margin not revenue]]`
