# 99 - Archive

**Propósito**: morgue de notas obsoletas. **Nunca deletar** conteúdo com peso histórico — move para cá.

## O que vem pra cá

- SOPs aposentados (substituídos por automação ou nova versão).
- Decisions substituídas (`status = superseded`).
- Fornecedores descontinuados (`status = retired` ou `blacklisted`).
- Learnings fechados com resultado, > 180 dias desde fechamento.
- Events com > 2 anos de reconciliação confirmada.
- Templates obsoletos.

## O que **não** vem pra cá

- Nota que ainda pode virar referência frequente (mesmo que antiga).
- Nota com link entrada de dashboard ou outra nota ativa — primeiro desvincular.
- Nota ainda sem status de encerramento.

## Como arquivar

1. Atualizar `status` no frontmatter para o valor de encerramento (`retired`, `closed`, `superseded`).
2. Mover arquivo físico para esta pasta mantendo nome original.
3. Atualizar links de entrada (ou deixar quebrarem intencionalmente, para marcar obsolescência).
4. Manter tags originais + adicionar `#arquivado`.

## Como recuperar

1. Mover de volta para a pasta semântica original.
2. Atualizar `status` para o valor ativo.
3. Se política ou processo mudou, refletir na descrição — nunca ressuscitar silenciosamente.

---

Tags: `#arquivado`
