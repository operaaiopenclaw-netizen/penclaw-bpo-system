# Margin Framework

Como a Orkestra.AI define e mede margem. Esta é a **definição oficial** usada em toda decisão comercial, bônus, clawback, e reporte.

Princípio-âncora: `[[Operating Principles]]` #1 (margem antes de volume).

---

## Hierarquia de margens

```
  RECEITA BRUTA (totalValue)
      − Impostos sobre venda         →  RECEITA LÍQUIDA
      − CMV (insumos diretos)         →  MARGEM BRUTA
      − Custos diretos de execução    →  MARGEM DE CONTRIBUIÇÃO   ← âncora
      − Despesas operacionais fixas   →  EBITDA por evento (view interna)
      − Comissão + bônus provisionado →  MARGEM LÍQUIDA DO EVENTO
```

A **Margem de Contribuição** é a métrica-norte. Todas as outras são derivadas.

---

## O que entra em CMV

- Ingredientes e bebidas consumidos no evento (por Recipe × receita produzida).
- Descartáveis específicos do evento (bandeja aluminada, box individual, etc.).
- Embalagem para transporte quando consumível (não reutilizável).

**Não entra em CMV**: utensílios reutilizáveis, gasto com estrutura, combustível, mão de obra.

---

## O que entra em "Custos diretos de execução"

- Mão de obra operacional direta do evento (cozinheiros extras, garçons, maître).
- Logística do evento (fretes específicos ida+volta).
- Aluguel de equipamento (quando aplicável àquele evento).
- Taxa de serviço de terceiro direto (ex.: bartender contratado por fora).

**Não entra aqui**: equipe CLT fixa da cozinha matriz, aluguel da cozinha matriz, utilities (luz/gás/água) da matriz.

---

## O que **nunca** entra na margem de contribuição por evento

- Custos de sede (rateio de aluguel, CLT de back office).
- Marketing e vendas (custos do funil, ferramentas, salários comerciais).
- Impostos sobre lucro (IRPJ/CSLL).
- Depreciação de ativos.

Esses entram no EBITDA e no resultado consolidado, não no evento. Atribuí-los evento-a-evento mata comparação inter-evento.

---

## Regras de reconhecimento

1. **CMV reconhece no consumo**, não na compra. `CMVLog.finalizedAt` marca o momento, com snapshot dos preços médios dos insumos consumidos.
2. **Receita reconhece no evento**, não no pagamento. Pagamentos alimentam `Payment` + `CashFlow` mas não alteram margem do evento.
3. **Ajustes pós-evento** (variância reconciliação) sempre atualizam a `MarginRealSnapshot` — margem real é mutável até 72h após evento, depois imutável.
4. **Descontos sobre proposta** reduzem Receita Bruta e, portanto, Margem — não são custo.

---

## Faixas de qualidade de margem

| Faixa | Classificação | Ação default |
|---|---|---|
| ≥ 35% | Excelente | Estudar como replicar |
| 25 – 35% | Saudável | Esperado para evento médio |
| 20 – 25% | Aceitável | Monitorar padrão por cliente |
| 15 – 20% | Zona amarela | `MARGEM_PROJETADA_BAIXA` medium |
| 0 – 15% | Crítico | `MARGEM_BAIXA` high + Learning |
| < 0% | Insustentável | `MARGEM_NEGATIVA` critical + Learning + Decision |

A meta da empresa é **margem de contribuição média ≥ 30%** (North Star #1).

---

## Campos no schema

- `Contract.projectedMargin` — margem de contribuição **projetada** na assinatura (input da comissão).
- `Event.marginForecast` — re-estimativa antes do evento.
- `Event.marginRealized` — margem real fechada na reconciliação.
- `ItemAdjustment` — ajuste histórico que refina forecast para próximos eventos.

---

Tags: `#financas`  `#margem`  `#politica`
Links: `[[Operating Principles]]` • `[[North Star Metrics]]` • `[[Commission Policy]]` • `[[Clawback Policy]]`
