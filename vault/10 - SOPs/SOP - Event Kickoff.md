---
type: sop
sop_id: SOP-001
owner: operator
last_verified_at: 2026-04-22
tags: [sop, evento, operacao, kickoff]
---

# SOP — Event Kickoff

Procedimento para iniciar execução de evento: do momento em que o evento entra na janela de 7 dias até o briefing da equipe na manhã do evento.

## Gatilho

- Evento com `Contract.status = SIGNED` e `eventDate ≤ now + 7 dias` dispara alerta LOW `EVENTO_PROXIMO`.
- Operador de plantão abre este SOP a partir desse alerta.

## Pré-requisitos

- [x] Contrato assinado e parcela 1 com `Payment.status = CONFIRMED` (se a política do cliente exige sinal).
- [x] `EventPlan` aprovado (menu, convidados, endereço, horário de entrega).
- [x] `ProductionPlan` gerado pelo motor sem alertas CRITICAL.
- [x] `POSuggestion` executadas — POs em trânsito ou recebidas.

Se algum destes falhar, **não prossiga**. Acione `sales_manager` ou `sales`.

## Passos

### D−7 (terça, se evento sábado)

1. Rodar `/operations/risks?eventId=<id>`. Qualquer `CRITICAL` ou `HIGH` abre plano de mitigação imediato.
2. Confirmar RSVP com cliente — variação > 10% em convidados dispara recálculo de forecast.
3. Checar recebimento de POs em primary. Atraso > 24h no lead time esperado → escalar para secondary.

### D−3 (quarta)

4. Rodar `/operations/overview` do evento. Margem projetada ainda ≥ faixa contratada? Se não, `Incident`.
5. Confirmar equipe operacional escalada (responsabilidade do operador, não do sistema, mas anote no evento).
6. Validar `ProductionPlan` — saturação de estação recalculada com RSVP atualizado.

### D−1 (sexta)

7. Rodar check final de estoque da cozinha para os 10 itens mais críticos do evento (maior peso em CMV).
8. Mise-en-place iniciada conforme `ProductionPlan` das receitas de longa dianteira.
9. Briefing 30 min com maître / chef de produção → pontos de atenção deste evento.
10. Registrar `ExecutionCheckpoint { type: "D_MINUS_1", ok: true/false, notes }`.

### D (dia do evento, manhã)

11. Briefing geral 45 min antes de iniciar produção. Passar RSVP final, timing, pontos de atenção.
12. Conferir entrega/logística programada (motorista, veículo, seguro de transporte se aplicável).
13. Registrar `ExecutionCheckpoint { type: "START" }`.

## Verificação

No final do dia D:

- `ExecutionCheckpoint { type: "END" }` registrado.
- Nenhum `Incident` aberto durante execução, OU incidente aberto com responsável e prazo.
- Comentário do cliente capturado (pelo maître, dentro de 24h).

## Rollback

Se qualquer passo D−7..D−1 falhar com consequência material:

1. Parar execução no ponto de falha.
2. Abrir `Incident` em `08 - Learnings` com severidade adequada.
3. Acionar `sales_manager` imediatamente se impactar contrato/cliente.
4. Se margem projetada cair > 10 p.p. por causa externa, avaliar renegociação com cliente antes de absorver.

## Verificação periódica

Operador revisa este SOP antes de cada primeiro evento em nova cozinha. Atualiza `last_verified_at` se rodou sem desvio.

---

Tags: `#sop`  `#evento`  `#kickoff`
Links: `[[Operational Rhythms]]` • `[[Alert Taxonomy]]` • `[[Station Load Rules]]`
