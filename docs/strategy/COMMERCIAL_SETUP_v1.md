# DEPARTAMENTO COMERCIAL — Orkestra Finance Brain

**Versão:** 1.0  
**Data:** 2026-04-08  
**Empresas:** QOpera, Laohana, Robusta  
**Status:** Especificação Completa

---

## 📋 OBJETIVO

Estruturar completamente o departamento comercial de 3 empresas de eventos:
- **QOpera:** Eventos corporativos premium
- **Laohana:** Buffet e gastronomia
- **Robusta:** Estrutura e produção

---

## 🏢 ESTRUTURA MULTI-EMPRESA

```
┌─────────────────────────────────────────────────────────────┐
│                    ORKESTRA HOLDING                         │
├─────────────────────────────────────────────────────────────┤
│  QOpera      │  Laohana       │  Robusta                   │
│  ─────────   │  ───────       │  ───────                   │
│  Corporativo │  Buffet/Gastro │  Estrutura                 │
│  Premium     │  Alimentação   │  Técnicos                  │
│  50-500 pax  │  30-300 pax    │  Tendas/Palcos/Luz         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 FUNIL DE VENDAS — PADRÃO ORKESTRA

| Etapa | Nome | Descrição | Probabilidade | SLA |
|-------|------|-----------|---------------|-----|
| 1 | **Lead** | Primeiro contato, interesse manifesto | 10% | 24h |
| 2 | **Qualificação** | Verificar viabilidade, orçamento, prazo | 25% | 48h |
| 3 | **Diagnóstico** | Entender necessidades, visita técnica | 40% | 5 dias |
| 4 | **Proposta** | Apresentar proposta detalhada | 60% | 3 dias |
| 5 | **Negociação** | Ajustes, descontos, termos | 75% | 7 dias |
| 6 | **Fechamento** | Contrato assinado, pagamento entrada | 90% | 24h |
| 7 | **Onboarding** | Briefing, planejamento, produção | 100% | 14 dias |

**Regras de Progressão:**
- Lead → Qualificação: Precisa de interesse confirmado + orçamento estimado
- Qualificação → Diagnóstico: Data definida, tipo de evento claro
- Diagnóstico → Proposta: Visita realizada ou video call completa
- Proposta → Negociação: Proposta enviada + feedback recebido
- Negociação → Fechamento: Aprovação interna (margin ≥ threshold)
- Fechamento → Onboarding: Contrato assinado + entrada pagamento

---

## 🗂️ TABELAS COMERCIAIS

### 1. products_catalog (Catálogo de Produtos/Serviços)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | Identificador único |
| company_id | UUID FK | Empresa (QOpera/Laohana/Robusta) |
| external_id | TEXT | Código próprio da empresa |
| name | TEXT | Nome do produto/serviço |
| description | TEXT | Descrição detalhada |
| category | ENUM | Tipo: `produto`, `servico`, `pacote` |
| subcategory | TEXT | Buffê, Bebida, Estrutura, Técnico, Decor, etc |
| base_cost | NUMERIC | Custo base unitário |
| suggested_price | NUMERIC | Preço sugerido de venda |
| margin_min | DECIMAL(5,2) | Margem mínima aceitável (%) |
| margin_target | DECIMAL(5,2) | Margem alvo (%) |
| unit_type | TEXT | pessoa, hora, m², unidade, kit |
| min_quantity | INTEGER | Quantidade mínima por evento |
| max_quantity | INTEGER | Quantidade máxima por evento |
| is_active | BOOLEAN | Disponível para venda |
| is_upsell | BOOLEAN | Pode ser oferecido como upsell |
| bundle_rules | JSONB | Regras de pacotes |
| seasonal_mult | JSONB | Multiplicadores sazonais |
| created_at | TIMESTAMPTZ | Data criação |
| updated_at | TIMESTAMPTZ | Última atualização |

**Categorias Específicas por Empresa:**

```sql
-- QOpera (Corporativo Premium)
categories_qopera = [
    'coquetel_executivo', 'coffee_break_premium', 'jantar_gala',
    'congresso', 'conferencia', 'lancamento_produto',
    'endomarketing', 'integracao', 'premiacao'
]

-- Laohana (Buffet)
categories_laohana = [
    'buffet_tradicional', 'buffet_churrasco', 'coffee_break',
    'finger_food', 'coquetel', 'jantar_servido',
    'estacao_gastronomica', 'bar_movel', 'garcon']
]

-- Robusta (Estrutura)
categories_robusta = [
    'tenda', 'palco', 'tablado', 'cobertura',
    'iluminacao', 'sonorizacao', 'energia', 'ar_condicionado',
    'mobiliaria', 'sinalizacao', 'camarim'
]
```

---

### 2. pricing_rules (Regras de Precificação)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| company_id | UUID FK | Empresa |
| product_id | UUID FK | Produto (NULL = regra geral) |
| rule_type | ENUM | markup, tier, volume, seasonal, loyalty |
| min_volume | INTEGER | Quantidade mínima para aplicar |
| max_volume | INTEGER | Quantidade máxima |
| markup_mult | DECIMAL(5,3) | Multiplicador sobre custo |
| discount_max | DECIMAL(5,2) | Desconto máximo permitido (%) |
| conditions | JSONB | Condições da regra |
| priority | INTEGER | Ordem de aplicação |
| valid_from | DATE | Início vigência |
| valid_until | DATE | Fim vigência |
| is_active | BOOLEAN | |

**Tipos de Regra:**

1. **MarkUp**: `custo × multiplicador`
2. **Tier**: Preço por faixa de volume
   - 1-50 pax: R$ 85/pessoa
   - 51-100: R$ 78/pessoa
   - 101-200: R$ 72/pessoa
3. **Volume**: Desconto por quantidade total
4. **Seasonal**: Multiplicador por período
   - Alta temporada (Dez/Jan): ×1.3
   - Baixa (Fev): ×0.9
5. **Loyalty**: Desconto acumulativo por recorrência

---

### 3. discount_policies (Políticas de Desconto)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| company_id | UUID FK | |
| role_id | UUID FK | Aplica-se a qual perfil |
| policy_name | TEXT | Nome da política |
| max_discount_pct | DECIMAL(5,2) | % máximo de desconto |
| max_discount_value | NUMERIC | Valor máximo absoluto |
| min_margin_pct | DECIMAL(5,2) | Margem mínima após desconto |
| approval_required | BOOLEAN | Precisa aprovação superior? |
| approval_threshold | NUMERIC | Acima deste valor, requer aprovação |
| reason_required | BOOLEAN | Exige justificativa? |
| exceptions | JSONB | Produtos excluídos ou especiais |

**Perfis de Desconto:**

```
┌─────────────────┬────────────┬──────────────┬───────────────┐
│ Perfil          │ Desconto   │ Sem Aprovar  │ Com Aprovação │
├─────────────────┼────────────┼──────────────┼───────────────┤
│ Vendedor JR     │ até 5%     │ até R$ 500   │ > R$ 500      │
│ Vendedor PL     │ até 10%    │ até R$ 2.000 │ > R$ 2.000    │
│ Vendedor SR     │ até 15%    │ até R$ 5.000 │ > R$ 5.000    │
│ Gerente Com.    │ até 20%    │ até R$ 10.000│ > R$ 10.000   │
│ Diretor         │ até 30%    │ até R$ 50.000│ > R$ 50.000   │
└─────────────────┴────────────┴──────────────┴───────────────┘
```

---

### 4. sales_targets (Metas Comerciais)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| company_id | UUID FK | |
| user_id | UUID FK | Vendedor (NULL = meta da unidade) |
| period_type | ENUM | monthly, quarterly, yearly |
| period_start | DATE | Início do período |
| period_end | DATE | Fim do período |
| target_revenue | NUMERIC | Meta faturamento |
| target_deals | INTEGER | Meta número de contratos |
| target_leads | INTEGER | Meta leads convertidos |
| target_margin | DECIMAL(5,2) | Margem média esperada |
| weight_new | DECIMAL(3,2) | Peso clientes novos |
| weight_recurring | DECIMAL(3,2) | Peso recorrência |
| bonus_threshold | DECIMAL(5,2) | % acima da meta para bônus |
| bonus_multiplier | DECIMAL(4,2) | Multiplicador de comissão |

---

### 5. sales_pipeline (Pipeline de Vendas)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| company_id | UUID FK | |
| opportunity_id | TEXT | Código único (OPP-XXXX) |
| client_id | UUID FK | Cliente (lead) |
| event_type | TEXT | Tipo de evento |
| event_date | DATE | Data prevista |
| guests_estimate | INTEGER | Estimativa de convidados |
| budget_estimate | NUMERIC | Orçamento estimado do cliente |
| current_stage | INTEGER | Etapa atual (1-7) |
| stage_history | JSONB | Histórico de mudanças de etapa |
| assigned_to | UUID FK | Vendedor responsável |
| probability | DECIMAL(5,2) | Probabilidade fechamento |
| expected_value | NUMERIC | Valor esperado (prob × total) |
| products | JSONB | Produtos/serviços cotados |
| discount_approved | NUMERIC | Desconto aprovado |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| closed_at | TIMESTAMPTZ | Data fechamento |
| closed_value | NUMERIC | Valor final fechado |
| close_reason | ENUM | won, lost, cancelled, postponed |
| lost_reason | TEXT | Por que perdeu? |

---

### 6. upsell_rules (Regras de Upsell)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| company_id | UUID FK | |
| trigger_product_id | UUID FK | Produto que dispara sugestão |
| suggested_product_id | UUID FK | Produto sugerido |
| rule_type | ENUM | automatic, manual, conditional |
| condition_logic | JSONB | Condições para exibir |
| discount_auto | DECIMAL(5,2) | Desconto automático no combo |
| urgency_text | TEXT | Texto de urgência/persuasão |
| max_suggestions | INTEGER | Máximo de vezes para sugerir |
| conversion_target | DECIMAL(5,2) | Taxa de conversão esperada |
| is_active | BOOLEAN | |

**Exemplos de Upsell:**
- Contratou Buffet → Sugerir: Bar móvel, Decoração, Som
- Contratou Tenda → Sugerir: Iluminação, Palco, Energia
- Evento > 100 pax → Sugerir: Segurança, Copeiro extra
- Casamento → Sugerir: Lounge, Mesa de doces, Foto

---

## 🔌 INTEGRAÇÃO COM SISTEMAS

### comercial ↔ financial_core
```python
pipeline.closed → financial.accounts_receivable.create()
pipeline.discount_approved → financial.validate_margin()
pricing.calculated → financial.cmv_projection()
```

### comercial ↔ decision_engine
```python
pricing.calculate() → decision_engine.score_event()
upsell.suggest() → decision_engine.calculate_affinity()
pipeline.probability → decision_engine.forecast_revenue()
```

### comercial ↔ event_engine
```python
pipeline.won → event_engine.create_event()
products.selected → event_engine.allocate_inventory()
```

---

## 📊 VISÕES ANALÍTICAS

### Pipeline Health
```sql
SELECT 
    company_id,
    DATE_TRUNC('month', created_at) as month,
    current_stage,
    COUNT(*) as opportunities,
    SUM(expected_value) as pipeline_value,
    AVG(probability) as avg_probability,
    SUM(CASE WHEN close_reason = 'won' THEN closed_value END) as won_value
FROM sales_pipeline
GROUP BY 1, 2, 3;
```

### Performance por Vendedor
```sql
SELECT 
    assigned_to,
    COUNT(*) as total_deals,
    COUNT(CASE WHEN close_reason = 'won' THEN 1 END) as won_deals,
    ROUND(100.0 * COUNT(CASE WHEN close_reason = 'won' THEN 1 END) / COUNT(*), 2) as conversion_rate,
    SUM(closed_value) as total_revenue,
    AVG(closed_value) as avg_ticket
FROM sales_pipeline
WHERE closed_at >= DATE_TRUNC('month', NOW())
GROUP BY assigned_to;
```

### Produtos Mais Vendidos
```sql
SELECT 
    p.name,
    p.subcategory,
    COUNT(*) as times_sold,
    SUM((item->>'quantity')::int) as total_quantity,
    SUM((item->>'total')::numeric) as total_revenue
FROM sales_pipeline sp,
LATERAL jsonb_array_elements(sp.products) as item
JOIN products_catalog p ON p.id = (item->>'product_id')::uuid
WHERE sp.close_reason = 'won'
GROUP BY p.id, p.name, p.subcategory
ORDER BY total_revenue DESC;
```

---

## 🎯 MÉTRICAS COMERCIAIS

| Métrica | Fórmula | Meta |
|---------|---------|------|
| Pipeline Velocity | Closed Value / Days in Pipeline | > R$ 50K/mês |
| Conversion Rate | Won / Total × 100 | > 25% |
| Average Deal Size | Total Revenue / Won Deals | > R$ 30K |
| Sales Cycle Length | AVG(closed_at - created_at) | < 45 dias |
| Upsell Rate | Upsells / Total Won × 100 | > 15% |
| Discount Average | AVG(discount_approved / total) × 100 | < 10% |

---

🎛️ **Orkestra Commercial Engine v1.0**
