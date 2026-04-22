# 05 - Supply & Inventory

**Propósito**: como compramos, de quem, em que ordem, com que tolerância. A qualidade do forecast não salva nada se o procurement atrasar.

## O que mora aqui

- `[[Supplier Segmentation]]` — tiers (primary, secondary, backup) e regras de acionamento.
- Futuro: `Inventory Counting SOP`, `Spoilage Tolerance Table`.

## O que **não** mora aqui

- Cadastro de fornecedor individual → ORKESTRA `Supplier` (tabela).
- POs ao vivo, pendências de recebimento → ORKESTRA `/supply/...`.
- Ajustes em `ItemAdjustment` → ação do sistema, documentado pelo histórico.

## Ritmo de atualização

- `[[Supplier Segmentation]]` reavaliado mensalmente com base em lead time real e variância de preço.
- Fornecedor novo só entra após `[[Template - Supplier]]` preenchido e 2 eventos de teste.
