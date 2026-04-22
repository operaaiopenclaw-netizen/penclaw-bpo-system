# 09 - Decisions

**Propósito**: registro formal de decisões com consequência estrutural — que impactam política, schema, motor, comissão, ou contrato com clientes/vendedores.

Uma Decision é **imutável** uma vez aceita. Para reverter, cria-se nova Decision que referencia a antiga (`supersedes`).

## O que mora aqui

Decisões que:

- Mudam um princípio, SOP, política de comissão, matriz de desconto, margem mínima.
- Criam ou removem fornecedor da blacklist.
- Aprovam exceção a regra padrão com impacto > R$ 10k.
- Aceitam trade-off explícito entre duas North Star Metrics.

## O que **não** mora aqui

- Decisão operacional do dia-a-dia ("comprar X do fornecedor Y") — vive no ORKESTRA.
- Rumo estratégico de produto (roadmap) — vive em `/product` ou backlog.
- Experimento reversível sem consequência financeira — só entra se der errado e virar Learning.

## Convenção de nome

```
Decision - <descrição curta imperativa> YYYY-MM.md
```

## Estrutura

Usar `[[Template - Decision]]` — frontmatter inclui `decision_id`, `status`, `decided_at`, `decided_by`, `supersedes`.

## Ciclo de vida

1. **proposed** — em discussão. Aberto via Weekly Review ou ad-hoc.
2. **accepted** — consenso atingido, responsável definido.
3. **implemented** — execução concluída (commit/PR/mudança de política efetivada).
4. **superseded** — substituída por outra Decision. Nunca deletar.
5. **reverted** — raro; exige nova Decision justificando.

## Ritmo

- Decision aberta > 14 dias sem movimento entra na pauta obrigatória do Weekly Review.
- `[[Dashboard - Decision Tracker]]` lista todas por status.
