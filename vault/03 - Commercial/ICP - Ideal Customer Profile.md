# ICP — Ideal Customer Profile

Quem é cliente bom para a Orkestra.AI. Esta página **filtra pipeline**: leads fora do ICP vão para `REJECTED` com motivo, não para nurturing eterno.

---

## Quem é cliente bom

**Operador de catering / buffet / eventos** com:

- **Volume**: 15–80 eventos/mês. Abaixo, não há repetibilidade para forecast calibrar. Acima, pede ERP completo (fora do escopo atual).
- **Ticket médio por evento**: R$ 8k – R$ 60k. Sweet spot R$ 15k – R$ 30k.
- **Convidados por evento**: 50–500. Evento < 50 não tem economia operacional relevante; > 500 exige features de produção em escala que não temos.
- **Margem de contribuição histórica**: entre 15% e 35%. Operador já com margem > 35% provavelmente tem controle próprio maduro e não precisa. Operador abaixo de 15% tem problema que não é só software.
- **Categoria fiscal**: Lucro Presumido ou Real. MEI simplesmente não suporta a complexidade de contratos + parcelamento + folha comissionada.
- **Geografia**: SP + RJ na largada, depois outras capitais com logística de fornecedor primary já funcional.

---

## Quem não é cliente

Nenhuma dessas organizações deve entrar como oportunidade:

- Buffets casamento-only com < 5 eventos/mês — ciclo longo demais, forecast não calibra.
- Produtoras de eventos corporativos que **não** operam cozinha própria (produtora de evento, não catering) — ORKESTRA otimiza cozinha real.
- Food trucks e operação de balcão — forecast é minuto-a-minuto, lógica diferente.
- Hospitalidade de hotel (serviço contínuo) — não é evento discreto.
- Cliente final pessoa física direto (ex.: noivo buscando organização do casamento).

---

## Sinais de alerta (não rejeição automática, mas bandeira amarela)

- Cliente sem **conta bancária PJ** e sem certificado digital — vai travar emissão de NF.
- Cliente que ainda faz "caixa 2" ou opera majoritariamente em dinheiro. Não negociamos nesse modelo.
- Cliente com **rotatividade > 50% da equipe operacional em 12 meses** — SOPs não vão grudar.
- Cliente com margem média histórica < 10% — ORKESTRA não recupera isso; precisa de consultoria de operação primeiro.

Quando aparecer 2+ sinais, abrir `Decision` antes de avançar além de `QUALIFIED`.

---

## Como operacionalizar

- `sales_manager` valida ICP na primeira call. Leads que não passam viram `Lead.status = DISQUALIFIED` com `metadata.reason` no CRM.
- `sales` recebe este ICP no onboarding e na weekly review sempre que entram leads fora do perfil.
- Métricas de aderência ao ICP entram no Weekly Review mensal — se > 30% do funil vem de fora do ICP, geração de demanda está errada.

---

Tags: `#comercial`  `#icp`  `#politica`
Links: `[[Mission]]` • `[[North Star Metrics]]` • `[[Commission Policy]]`
