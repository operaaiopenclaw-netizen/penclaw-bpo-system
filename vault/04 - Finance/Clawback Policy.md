# Clawback Policy

Política oficial de reversão de comissão. Clawback é dor, mas é a dor que preserva a fé no sistema de comissão. Vendedor sabe que ganha de verdade o que entra de verdade.

Princípio-âncora: `[[Operating Principles]]` #8 — pague rápido, mas só o confirmado.

---

## Quando dispara

### Automático

1. **Contrato cancelado** → `onContractCancelled(contractId, reason)`
   - FORECAST/LOCKED/RELEASED → `CLAWED_BACK` imediato.
   - PAID → marca `metadata.clawbackPending = true`, não muda status.
2. **Payment REVERSED** (estorno bancário) → recalcula `onPaymentConfirmed` com delta negativo; RELEASED daquele trecho vira `CLAWED_BACK`.
3. **Parcela inadimplente > 60 dias** → RELEASED daquela parcela vira `CLAWED_BACK`. Se voltar a pagar, recria entry novo (nunca reativa o velho).

### Manual

4. **Margem real < 50% da projetada** — revisão pelo `finance` na reconciliação. Se justificado, abre `POST /contracts/:id/clawback` com motivo.
5. **Fraude / comportamento doloso** — imediato, sem carência, com `Incident` em `08 - Learnings`.

---

## Imutabilidade pós-PAID

Entry com `status = PAID` **nunca muda**. Se cabe clawback, registramos como dívida a compensar:

1. Flag `metadata.clawbackPending = true` + `clawbackReason` no entry original.
2. Criar registro `Debt` contra o vendedor (tabela própria do financeiro/folha).
3. Na próxima folha, a `Debt` é descontada da nova comissão paga.
4. Se o vendedor sair, a `Debt` vira acerto na rescisão — responsabilidade do RH + finance.

Isso preserva auditabilidade: o histórico do que foi pago em cada folha não muda.

---

## Comunicação com o vendedor

- Clawback automático notifica o vendedor via Telegram `@orkestra-sales-<id>` no momento do disparo.
- Manual exige conversa antes do disparo — `sales_manager` aciona o vendedor com o motivo e só depois o `finance` executa.
- Clawback por fraude é exceção: executa primeiro, comunica depois (com RH no loop).

---

## Métrica de acompanhamento

**Taxa de clawback** = `sum(clawedback últimos 90d) / sum(provisionado últimos 90d)`

- Verde: ≤ 3%
- Amarelo: 3–5%
- Vermelho (HIGH): > 5%

Taxa acima da meta por 2 trimestres seguidos → revisar ICP, matriz de desconto e carência. É sinal de sistema, não de pessoa.

---

## O que NÃO é clawback

- **Ajuste retroativo de política** (mudou a regra do jogo após o contrato) — nunca retroage. Contrato antigo roda na política antiga.
- **Inadimplência < 60 dias** — ainda é carência/follow-up, não clawback.
- **Margem real abaixo da projetada em evento único** — só dispara manual se < 50%, e apenas com análise. Margem oscila, clawback é para padrão.

---

Tags: `#financas`  `#clawback`  `#politica`
Links: `[[Commission Policy]]` • `[[Operating Principles]]` • `[[North Star Metrics]]`
