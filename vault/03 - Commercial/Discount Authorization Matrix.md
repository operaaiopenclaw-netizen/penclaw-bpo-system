# Discount Authorization Matrix

Quem pode autorizar qual desconto. **Desconto é empréstimo de margem — sempre paga alguém.** Esta matriz define quem assina o cheque.

Princípio-âncora: `[[Operating Principles]]` #1 (margem antes de volume) e #7 (comissão alinhada à margem).

---

## Matriz

| Desconto (% sobre proposta) | Aprovador obrigatório | Impacto em comissão | Registro necessário |
|---|---|---|---|
| 0 – 5% | Closer (sozinho) | Nenhum | Automático no CRM |
| 5 – 10% | `sales_manager` | Penalidade padrão (20%) | `discountAuthorizedById` preenchido |
| 10 – 15% | `sales_manager` + `finance` | Penalidade aumentada caso-a-caso | `Decision` registrada |
| > 15% | `admin` + `finance` | Comissão = 0 + análise de margem | `Decision` + review em Weekly |
| Margem projetada < 20% | Veto default, só admin libera | Comissão = 0 | `Decision` obrigatória |

---

## Como aprovar

1. Vendedor anota desconto pretendido no Proposal (`discountAppliedPct`).
2. Sistema emite `ApprovalRequest` se `discountAppliedPct > 0.05`.
3. Aprovador assina em `/approvals/...` preenchendo `discountAuthorizedById` + `discountAuthorizedAt`.
4. Se > 10%, aprovador também abre `[[Template - Decision]]` registrando o **porquê** (retenção estratégica? volume? conta âncora?).

---

## Exceções recorrentes viram SOP

Se o mesmo tipo de exceção aparece 3× no trimestre (ex.: contas âncora pedem 12% consistentemente), não trate como exceção — crie/atualize `[[SOP - Pricing Exceptions]]` e revise esta matriz.

---

## O que nunca é aceitável

- Desconto sem `discountAuthorizedById` preenchido → contrato **não entra em produção**.
- Reduzir margem projetada abaixo de 15% sem `Decision` ou aprovação de admin — ainda que o cliente pague à vista.
- "Desconto verbal" com o cliente que não aparece no Proposal — isso vira sinistro em reconciliação e gera clawback.

---

Tags: `#comercial`  `#desconto`  `#politica`
Links: `[[Commission Policy]]` • `[[Margin Framework]]` • `[[Operating Principles]]`
