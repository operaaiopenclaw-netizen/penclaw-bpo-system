# Alert Taxonomy

Classificação dos alertas emitidos pelo ORKESTRA. Alinhada com `docs/RUNBOOK.md` do repo. Sempre que o runbook mudar severidade ou SLA, esta página muda junto.

Regra de ouro: **severidade é sobre impacto, não sobre quem acorda**. Um alerta `CRITICAL` pode ser tratado por bot; um `MEDIUM` pode escalar humano se recorrente.

---

## Níveis

### CRITICAL — responde em ≤ 15 min, 24/7

Operação está quebrada ou vai quebrar nas próximas horas.

- `STOCKOUT_IMINENTE` — estoque projetado < consumo previsto para evento em < 24h.
- `MARGEM_NEGATIVA` — evento consolidado fechou com margem < 0%.
- `PAYMENT_GATEWAY_DOWN` — webhooks de pagamento falhando há > 10 min.
- `DATABASE_DOWN` — Postgres não responde healthcheck.
- `APPROVAL_SLA_BREACH` — aprovação crítica pendente há > 4h (contratos, clawback manual).

**Ação default**: Telegram `@orkestra-ops` + página para operador de plantão. Se a causa for de código, criar `Incident` ainda na mesma hora em `08 - Learnings`.

### HIGH — responde em ≤ 2h em horário comercial, ≤ 30 min se fora

Degradação séria, com janela de mitigação.

- `MARGEM_BAIXA` — evento consolidado com margem entre 0% e 15%.
- `RECONCILIACAO_VARIANCIA_ALTA` — variância > 25% forecast × real.
- `CLAWBACK_RATE_ALTO` — `> 5%` do provisionado clawed back no trimestre móvel.
- `LEAD_TIME_PROCUREMENT_ALTO` — `> 120h` em fornecedor primary.
- `CONTRATO_EVENTO_CURTO` — contrato assinado < 14 dias antes do evento (aperto operacional).

**Ação default**: criar `ApprovalRequest` ou `Decision` dependendo do caso, seguir playbook correspondente em `10 - SOPs`.

### MEDIUM — responde no próximo ciclo semanal

Sinal de tendência, não incêndio.

- `FORECAST_ERR_MODERADO` — erro absoluto 15–25% em evento isolado.
- `PROPOSAL_SEM_MOVIMENTO` — proposal `SENT` há > 7 dias sem follow-up.
- `MARGEM_PROJETADA_BAIXA` — contrato entrando em produção com margem projetada 15–20%.

**Ação default**: entrar na pauta do Weekly Review. Se aparecer 3× seguidos, vira HIGH automaticamente.

### LOW — FYI, agrupa em relatório

Ruído útil, não ação individual.

- `ITEM_ADJUSTMENT_SUGERIDO` — EWMA sugere ajuste em `ItemAdjustment`.
- `SUPPLIER_SECONDARY_ATRASO` — atraso em fornecedor não-primary.
- `COMMISSION_LOCKED_CARENCIA` — commission entry liberou após carência (fluxo esperado).

**Ação default**: digest diário/semanal. Nunca pagina humano individualmente.

---

## Tabela de correspondência

| Alerta | Severidade | SLA resposta | Playbook | Métrica afetada |
|---|---|---|---|---|
| `STOCKOUT_IMINENTE` | CRITICAL | 15 min | `[[SOP - Stockout Response]]` | Margem |
| `MARGEM_NEGATIVA` | CRITICAL | 15 min | `[[SOP - Margin Recovery]]` | Margem |
| `DATABASE_DOWN` | CRITICAL | 15 min | `docs/RUNBOOK.md#db` | Disponibilidade |
| `APPROVAL_SLA_BREACH` | CRITICAL | 15 min | `[[SOP - Approval Escalation]]` | Governança |
| `MARGEM_BAIXA` | HIGH | 2h | `[[SOP - Margin Recovery]]` | Margem |
| `RECONCILIACAO_VARIANCIA_ALTA` | HIGH | 2h | `[[SOP - Reconciliation Deep Dive]]` | Forecast accuracy |
| `CLAWBACK_RATE_ALTO` | HIGH | 2h | `[[Clawback Policy]]` | Clawback rate |
| `LEAD_TIME_PROCUREMENT_ALTO` | HIGH | 2h | `[[Supplier Segmentation]]` | Procurement |
| `CONTRATO_EVENTO_CURTO` | HIGH | 2h | `[[Discount Authorization Matrix]]` | Lead contrato→evento |
| `FORECAST_ERR_MODERADO` | MEDIUM | próximo Weekly | `[[SOP - Reconciliation Deep Dive]]` | Forecast accuracy |
| `PROPOSAL_SEM_MOVIMENTO` | MEDIUM | Quarta pipeline | — | Lead contrato→evento |
| `MARGEM_PROJETADA_BAIXA` | MEDIUM | Weekly | `[[Margin Framework]]` | Margem |
| `ITEM_ADJUSTMENT_SUGERIDO` | LOW | digest | — | Forecast accuracy |
| `SUPPLIER_SECONDARY_ATRASO` | LOW | digest | `[[Supplier Segmentation]]` | Procurement |
| `COMMISSION_LOCKED_CARENCIA` | LOW | digest | `[[Commission Policy]]` | — |

---

## Escalação

1. Operador de plantão acusa no Telegram em até o SLA.
2. Se sem ack em 2× SLA → escala para admin.
3. Se sem ack em 4× SLA → escalação automática via PagerDuty (quando plugado).

**Incidente repetido 3× na mesma semana** → abre automaticamente `Incident` em `08 - Learnings` mesmo se cada ocorrência foi resolvida isolada.

---

Tags: `#operacao`  `#alertas`
Links: `[[Operational Rhythms]]` • `[[Dashboard - Operational Risk Board]]` • `docs/RUNBOOK.md`
