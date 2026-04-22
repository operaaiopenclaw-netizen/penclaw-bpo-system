# 06 - Production

**Propósito**: como a cozinha do operador executa. Regras de balanceamento, estações, timing, entrega.

## O que mora aqui

- `[[Station Load Rules]]` — carga máxima por estação, regras de divisão e fallback.
- Futuro: `Plating Cadence Rules`, `Service Team Ratios`.

## O que **não** mora aqui

- Escala de equipe — responsabilidade do operador, fora do escopo do BPO.
- Timing detalhado de cada receita — está na `Recipe` do ORKESTRA.

## Ritmo de atualização

- `[[Station Load Rules]]` muda após `RECONCILIACAO_VARIANCIA_ALTA` com causa "estação gargalo" em 2+ eventos similares.
