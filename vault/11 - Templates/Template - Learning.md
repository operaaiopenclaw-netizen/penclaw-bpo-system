---
type: learning
status: open     # open | in_progress | closed
opened_at:
deadline:        # opened_at + 30d
trigger:         # alerta, reconciliacao, cliente, incidente
severity:        # CRITICAL | HIGH | MEDIUM | LOW
related_event:
tags: [aprendizado, ]
---

# Learning — <descrição curta do aprendizado>

## Fato

<O que aconteceu? Objetivo, com números quando possível.>

## Por quê (5 "porquês")

1. **Por que X?**
2. **Por que Y?**
3. **Por que Z?**
4.
5.

**Causa raiz**: <após os porquês, sintetizar a raiz em 1 frase>

## Próximo passo

<Qual é a ação concreta? Decision? SOP? Feature? Parâmetro?>

## Decisão ou SOP alvo

<link para `[[Decision - ...]]` ou `[[SOP - ...]]` que este Learning vai gerar>

**Prazo limite**: YYYY-MM-DD (≤ opened_at + 30 dias)

## Resultado esperado

<Qual evidência vai dizer que o aprendizado grudou? Quantos eventos, qual métrica, qual janela?>

## Status

- [ ] Causa raiz identificada
- [ ] Decision ou SOP criado
- [ ] Mudança no sistema shipped
- [ ] Validação em eventos subsequentes

---

Tags: `#aprendizado`
Links:
