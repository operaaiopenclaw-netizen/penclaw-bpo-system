# 🎛️ ORKESTRA AGENTS

Sistema multi-agentes para gestão financeira e operacional de eventos.

## Estrutura

```
orkestra_agents/
├── core/                    # Agentes transacionais (operam dados)
├── intelligence/           # Agentes analíticos (geram insights)
├── schemas/               # JSON Schemas para validação
├── memory/                # Memória operacional persistente
└── README.md             # Este arquivo
```

---

## Core Agents

### financial_agent.md
**Função:** Rastreamento de transações financeiras
- Receitas (RECEBIMENTO)
- Despesas (COMPRA, PAGAMENTO)
- Movimentações de estoque

**Script:** `../scripts/financial_analyzer.py`

### procurement_agent.md
**Função:** Geração inteligente de ordens de compra
- Consolida necessidade de eventos
- Subtrai estoque existente
- Adiciona margem de segurança 20%

**Script:** `../scripts/procurement_agent.py`

---

## Intelligence Agents

### financial_intelligence_agent.md
**Função:** Análise financeira com alertas
- Detecta margem < 30%
- Detecta categoria > 40% do custo
- Sugere ações corretivas

**Script:** `../scripts/financial_analyzer.py`

### event_profitability_agent.md
**Função:** Avaliação de viabilidade de eventos
- Decisão: APROVAR / REVISAR / RECUSAR
- Threshold mínimo: 30% margem
- Análise de complexidade operacional

**Script:** `../scripts/event_profitability_agent.py`

### self_improvement_agent.md
**Função:** Aprendizado de padrões
- Analisa histórico de decisões
- Identifica o que funciona
- Sugere ajustes estruturados

**Script:** `../scripts/self_improvement_agent.py`

---

## Memory Layer

### decisions.json
Histórico de decisões:
- Evento, margem antes/depois
- Causa do problema
- Ação tomada
- Resultado

### errors.json
Registro de erros:
- Tipo de erro
- Severidade
- Impacto
- Prevenção

### performance.json
Métricas de performance:
- Receita, custos, margem
- Targets atingidos/perdidos
- KPIs

---

## Schemas

### financial_schema.json
Validação JSON para transações financeiras com:
- Tipos enumerados (income/expense/estoque)
- Categorias padronizadas
- Formatos de data/hora
- Meta-dados de análise

---

## Fluxo de Dados

```
Entrada Humana
      ↓
[Financial Agent] → Registra transação
      ↓
[Memory Layer] → Salva em decisions.json
      ↓
[Financial Intelligence] → Analisa + alerta
      ↓
[Event Profitability] → Avalia viabilidade
      ↓
[Self Improvement] → Aprende padrões
      ↓
[Output] → Sugetões de ajuste
```

---

## Status de Implementação

| Componente | Status | Script |
|------------|--------|--------|
| Financial Agent | ✅ | scripts/financial_analyzer.py |
| Procurement Agent | ✅ | scripts/procurement_agent.py |
| Profitability Agent | ✅ | scripts/event_profitability_agent.py |
| Self Improvement | ✅ | scripts/self_improvement_agent.py |
| Memory Layer | ✅ | scripts/memory_manager.py |
| Data Normalizer | ✅ | scripts/data_normalizer.py |

---

## Próximos Passos

1. [ ] Conectar agents à Memory Layer
2. [ ] Criar orchestrator unificado
3. [ ] Implementar API REST simples
4. [ ] Dashboard de visualização
5. [ ] Integração ClickUp

---

*Orkestra Finance Brain v1.0*
*Atualizado: 26/03/2026*
