# Supplier Segmentation

Como classificamos fornecedores. **Tier define direito de uso, não promessa eterna.** Fornecedor desce de tier quando lead time, preço ou qualidade saem da faixa.

---

## Tiers

### Primary

Default do motor de compras. `POSuggestion` prefere este tier sempre que disponível.

Requisitos:
- Lead time médio ≤ 72h medido em ≥ 20 POs dos últimos 90 dias.
- Variância de preço vs. índice de referência ≤ ±5% em 90 dias.
- Taxa de rejeição/troca de produto ≤ 2%.
- NF emitida corretamente em 100% dos casos auditados.

**Métrica North Star #5** é medida **só** em primary.

### Secondary

Usado quando primary não atende (ruptura, preço fora da faixa, janela de entrega impossível).

Requisitos:
- Lead time médio ≤ 120h.
- Pode ter variância maior de preço (até ±15%).
- Sem obrigação de uso contínuo, mas cadastro ativo.

Uso > 25% do volume em 30 dias automaticamente promove o fornecedor para primary candidate em review mensal.

### Backup

Emergência declarada: stockout iminente, primary e secondary indisponíveis. Uso requer anotação explícita no `POSuggestion.reason`.

Requisitos:
- Cadastro mínimo (CNPJ + contato + método pagamento).
- Sem exigência de lead time — é "quem atende agora".
- Preço pode estar fora da faixa; é custo de não-planejamento.

Uso recorrente de backup é sintoma de falha em primary/secondary, não virtude.

---

## Regras operacionais

1. **Concentração máxima**: nenhum insumo pode ter > 70% do volume em um único fornecedor primary. Se acontecer, abrir `Decision` + buscar segundo primary.
2. **Rotação ativa**: rodar ao menos 1 PO/mês em secondary dos itens críticos. Senão eles atrofam e somem da base.
3. **Auditoria trimestral**: revisão das métricas (lead time, variância, rejeição) e reclassificação se necessário.
4. **Blacklist**: fornecedor com fraude de NF, produto adulterado ou atraso deliberado em evento crítico → blacklist permanente, registrar como `Incident`.

---

## Como promover / rebaixar

**Promover secondary → primary** quando:
- ≥ 20 POs nos últimos 90 dias.
- Lead time médio ≤ 72h.
- Variância de preço ≤ ±5%.
- Sem incidente reportado.

**Rebaixar primary → secondary** quando:
- Lead time médio > 96h em trimestre.
- Variância > 10% em 90 dias.
- 2+ `LEAD_TIME_PROCUREMENT_ALTO` alerts do mesmo fornecedor no trimestre.

Reclassificação sempre vira `Decision` registrada, com métricas do período.

---

## Campos no schema

- `Supplier.tier` — enum `PRIMARY | SECONDARY | BACKUP`.
- `Supplier.leadTimeHours` — média móvel 90d.
- `Supplier.priceVarianceIndex` — desvio vs. catálogo de referência.
- `Supplier.reliabilityScore` — composto calculado mensalmente.

---

Tags: `#supply`  `#fornecedor`  `#politica`
Links: `[[North Star Metrics]]` • `[[Alert Taxonomy]]` • `[[Template - Supplier]]`
