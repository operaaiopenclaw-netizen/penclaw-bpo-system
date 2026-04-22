# 07 - Events

**Propósito**: índice narrativo de eventos significativos. **Não é o CRM nem o DRE** — é a memória curada, com lições, links para decisões e incidentes.

## O que mora aqui

Uma nota por evento **que vale a pena lembrar**, não todo evento. Critério:

- Gerou `Learning` (qualquer severidade).
- Foi marco comercial (primeiro de uma categoria, maior ticket, cliente âncora).
- Teve `Incident` associado.
- Quebrou forecast em > 25%.
- Virou referência para precificar eventos futuros.

## O que **não** mora aqui

- Todo evento do CRM — a maioria fica só no ORKESTRA.
- Dados operacionais do evento (CMV, produção, consumo) — no ORKESTRA `/operations/lifecycle/<id>`.
- Planejamento de eventos futuros — está no CRM, aqui vira nota só depois de acontecer.

## Convenção de nome

```
Event - <Cliente ou Tipo> <curta descrição> - YYYY-MM.md
```

Exemplo: `Event - Yohanna 15 anos 2026-04.md`

## Estrutura

Usar `[[Template - Event]]`.

## Ritmo

- Criar nota no máximo **72h após reconciliação**, enquanto memória está fresca.
- Atualizar se cliente contratar de novo (linkar eventos sucessivos).
