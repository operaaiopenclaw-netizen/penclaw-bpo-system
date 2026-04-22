# Operational Rhythms

Cadências fixas da operação. Se um ritmo falha 3× seguidas, renegocie ou corte. Ritmo performático > ritmo "bonito".

---

## Diário

### Por operador de plantão

- **Manhã (7h)**: abrir `/operations/overview` → confirmar `/ready` verde, nenhum alerta CRITICAL pendurado.
- **Início/fim de cada evento**: registrar `ExecutionCheckpoint` no ORKESTRA.
- **Fim do dia (22h)**: handoff no Telegram `@orkestra-ops` com 3 bullets: o que rodou, o que quebrou, o que ficou pendente.

### Por admin

- Conferir `[[Dashboard - Operational Risk Board]]` antes das 10h.
- Revisar qualquer alerta CRITICAL aberto há mais de o SLA.

---

## Semanal

### Segunda, 9h — Weekly Review (30 min)

Abrir `[[Template - Weekly Review]]`. Participantes: admin + sales_manager + operator de plantão da semana.

Pauta:
1. 5 North Star Metrics — qual está vermelho?
2. Learnings capturados na semana passada → decisão sobre promoção
3. Decisions abertas > 14 dias
4. Calendário de eventos da semana — riscos conhecidos

### Quarta, 14h — Pipeline commercial (20 min)

Somente `sales_manager` + `sales`. Revisa:
- Leads em `QUALIFIED` sem movimento há >5 dias
- Proposals `SENT` sem retorno há >7 dias (follow-up hoje)
- Contratos a assinar esta semana — comissão já prevista?

### Sexta, 17h — Preparação final eventos do fim de semana

- Run `/operations/risks?eventId=...` para cada evento de sábado e domingo.
- Qualquer `CRITICAL` → plano de mitigação no Telegram até 18h.

---

## Mensal

### Dia 3 útil — Fechamento financeiro

`finance` consolida:
- Margem real por evento do mês anterior
- Comissões RELEASED → PAID (folha)
- Clawback pendente: revisar com vendedor antes da folha
- DRE consolidado no `/operations/lifecycle/<id>`

### Dia 5 útil — Retrospectiva operacional

30 min + todos leads de área. Foco em padrões, não em números absolutos.

### Último dia útil — Forecast do mês seguinte

Ajustes em `ItemAdjustment` baseados em reconciliações do mês que fecha. Quando desvio > 15% em ≥ 3 eventos do mesmo item → manual intervention.

---

## Trimestral

### Última semana do trimestre — Review estratégico

- `[[North Star Metrics]]` atualizado
- Revisar `[[Operating Principles]]` — algum princípio virou obsoleto?
- SOPs criados no trimestre → quais pegaram? quais morreram?

---

Tags: `#operacao`  `#ritmos`
Links: `[[Alert Taxonomy]]` • `[[Dashboard - Weekly Review Board]]` • `[[Commission Policy]]`
