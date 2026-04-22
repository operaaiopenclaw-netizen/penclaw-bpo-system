# 10 - SOPs

**Propósito**: procedimentos operacionais padrão executáveis. Uma pessoa nova consegue rodar o passo-a-passo sem tribo oral.

## O que mora aqui

SOPs com nome prefixado `SOP - ...`. Cada um contém:

- **Gatilho**: o que faz o SOP começar.
- **Pré-requisitos**: o que precisa estar pronto.
- **Passos**: numerados, um verbo imperativo por item.
- **Verificação**: como sabemos que deu certo.
- **Rollback**: se der errado, o que fazer.

## O que **não** mora aqui

- Playbook genérico sem passo-a-passo → isso é Operations em `02`.
- Política, princípio, trade-off → é Decision em `09`.
- Lição de incidente → Learning em `08` (que pode gerar um SOP novo).

## Convenção de nome

```
SOP - <Nome do procedimento>.md
```

## Ciclo de vida

Todo SOP tem:
- `owner` — quem mantém.
- `last_verified_at` — última data que o dono rodou mentalmente ou em training e confirmou que bate com a realidade.

SOP com `last_verified_at` > 90 dias entra em fila de revisão.

## Ritmo

- Novo SOP nasce quando:
  1. Mesmo procedimento vira `Incident` ou `Learning` 2× → vira SOP na 3ª.
  2. Política de `Decision` exige operacionalização.
- SOP morre quando o sistema automatiza o passo. Registrar morte com Decision `retires-sop`.
