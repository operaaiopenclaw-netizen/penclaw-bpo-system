# 11 - Templates

Templates Obsidian para garantir consistência. Criar nova nota **sempre** a partir de um template — nunca do zero.

## Como usar

1. Comando Obsidian: `Templates: Insert template` (plugin core) ou `QuickAdd` se configurado.
2. Copiar conteúdo do `[[Template - ...]]`, renomear arquivo conforme convenção da pasta-destino.
3. Preencher **frontmatter** completo antes do conteúdo.

## Templates disponíveis

- `[[Template - Event]]`
- `[[Template - Decision]]`
- `[[Template - Supplier]]`
- `[[Template - Incident]]`
- `[[Template - Weekly Review]]`
- `[[Template - SOP]]`
- `[[Template - Learning]]`

## Regra do frontmatter

- `type`: obrigatório, bate com nome do template (event, decision, supplier, incident, weekly-review, sop, learning).
- `status`: obrigatório, vocabulário por tipo.
- `tags`: no mínimo 2 — uma da taxonomia global (`#evento`, `#decisao`, etc.) + uma específica.
- Datas sempre em `YYYY-MM-DD`. Nunca relativas.
