# 04 - Finance

**Propósito**: disciplina financeira do BPO. Como medimos margem, como provisionamos, quando acionamos clawback.

## O que mora aqui

- `[[Margin Framework]]` — o que é margem de contribuição na Orkestra, o que entra e o que não entra.
- `[[Clawback Policy]]` — quando e como reverter comissão paga ou reservada.
- Futuro: `Pricing Guardrails`, `Cash Flow Cadence`.

## O que **não** mora aqui

- DRE real por evento → ORKESTRA `/operations/lifecycle/<id>` (view consolidada).
- Conciliação bancária diária → serviço fiscal/contábil externo.
- Folha de pagamento de comissão → `CommissionEntry.status = PAID` + sistema de folha.

## Ritmo de atualização

- `[[Margin Framework]]` só muda com `Decision` — é definição contábil, não preferência.
- `[[Clawback Policy]]` revisado sempre que `Taxa de clawback` (North Star #4) sai do verde 2 trimestres seguidos.
