# 🗺️ MAPA DE INTEGRAÇÃO - ORKESTRA.AI

**Data:** 2026-04-15  
**Status:** CONSOLIDAÇÃO DE ARQUITETURA EXISTENTE  
**Artefatos Auditados:** 9 arquivos críticos

---

## 📊 INVENTÁRIO DE ARTEFATOS EXISTENTES

### ✅ ARTEFATOS JÁ IMPLEMENTADOS

| Artefato | Status | Conteúdo | Tamanho |
|----------|--------|----------|---------|
| `orkestra_schema_v1.sql` | ✅ **COMPLETO** | Infraestrutura logging, audit, RBAC, decisions | ~900 linhas |
| `PLANO_TECNICO_INFRA_v1.md` | ✅ **COMPLETO** | APIs REST, segurança, endpoints | ~800 linhas |
| `openclaw_learning_rules.json` | ✅ **VALIDADO** | Regras ML, alertas, benchmarks | ~500 linhas |
| `pricing_engine.json` | ✅ **FUNCIONAL** | Motor de precificação, decisões | ~300 linhas |
| `backtest_*.md` (3 arquivos) | ✅ **ANÁLISE REAL** | 16 eventos analisados | ~2000 linhas |
| `dashboard_data.json` | ✅ **GERADO** | KPIs, rankings, projeções | ~200 linhas |

### 📦 ESTADO ATUAL DO SISTEMA

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ORKESTRA.AI - ESTADO ATUAL                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🏗️ INFRAESTRUTURA (100% - FUNCIONANDO)                                 ││
│  │ ├── audit_log          ✅ PostgreSQL particionado                       ││
│  │ ├── decision_log       ✅ Event sourcing + reasoning chain              ││
│  │ ├── agent_action_log   ✅ Tracking de tool calls                        ││
│  │ ├── rbac_roles/users   ✅ RBAC completo                               ││
│  │ ├── system_parameters  ✅ Configuração versionada                     ││
│  │ └── Views analíticas   ✅ v_audit_daily_summary, v_decision_accuracy   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 💰 FINANCIAL CORE (90% - RODANDO COM R$ 7.7M)                          ││
│  │ ├── accounts_payable      ✅ 27 registros                             ││
│  │ ├── accounts_receivable   ✅ 53 registros                             ││
│  │ ├── cashflow_projection   ✅ 90 dias                                  ││
│  │ ├── cash_position         ✅ 2 empresas                               ││
│  │ ├── multi-tenant          ✅ LA ORANA + STATUS Opera                  ││
│  │ └── alertas               ✅ CAIXA_NEGATIVO, RECEITA_SEM_CONTRATO   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                              ↓                                              │
│  │ ⚠️ FALTANDO: Pipeline Comercial + Evento + Produção                  ││
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 🤖 ENGINES ANALÍTICOS (70% - PARCIAL)                                  ││
│  │ ├── learning_rules.json   ✅ Benchmarks, regras de decisão            ││
│  │ ├── pricing_engine        ✅ Forecast, decisões                       ││
│  │ ├── backtest_analyzer     ✅ 16 eventos analisados                   ││
│  │ ├── dashboard generator   ✅ KPIs, rankings                          ││
│  │ └── engines executáveis   ⚠️ kitchen_control, fixed_cost, DRE         ││
│  │                            (completam mas com dados mock)              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 GAPS IDENTIFICADOS (Análise Profunda)

### GAP CRÍTICO #1: Pipeline Comercial → Evento

```
PROBLEMA ENCONTRADO NOS BACKTESTS:
├── R$ 1.283.584 em receitas SEM CONTRATO vinculado
├── 5 eventos com DRE contaminado (EV-011, EV-013, EV-014)
├── Não existe: Lead, Qualification, Proposal, Contract
└── Consequência: R$ 7.7M de receita sem rastreabilidade comercial

SOLUÇÃO: Criar módulo CRM + Contract
├── leads table (orkestra_schema já tem audit pra isso)
├── proposals table (com versioning)
├── contracts table (assinatura digital)
└── integração: ContractSigned → EventCreated
```

### GAP CRÍTICO #2: OS/OP + Produção

```
PROBLEMA NOS ENGINES:
├── kitchen_control: items não existem no inventário
├── DRE: sem CMV real (dados mock)
├── fixed_cost: funcionando mas apenas rateio
└── Não existe: ServiceOrder, ProductionOrder, Recipe, ProductionBatch

SOLUÇÃO: Criar módulo Order + Production
├── service_orders (O que foi vendido)
├── production_orders (O que será produzido)
├── recipes (Fichas técnicas)
├── production_batches (Execução)
└── integração: POCompleted → InventoryConsumption
```

### GAP CRÍTICO #3: Digital Twin

```
PROBLEMA:
├── Sistema prevê consumo mas não compara com real
├── Não existe: ExecutionSession, Checkpoint, RealConsumption
├── Engine detecta gaps mas não fecha o loop
└── Consequência: Sem learning real

SOLUÇÃO: Criar Execution Engine
├── execution_sessions (Dia do evento)
├── execution_checkpoints (Checklists)
├── real_consumption vs predicted
└── feedback loop para pricing_engine
```

---

## 🎯 INTEGRAÇÃO: BLUEPRINT ↔ ARTEFATOS EXISTENTES

### 1. INFRAESTRUTURA (Manter + Estender)

**Artefato Existente:** `orkestra_schema_v1.sql`

```sql
-- JÁ EXISTE (preservar):
- audit_log (imutável, particionado)
- decision_log (com reasoning_chain)
- agent_action_log (tool tracking)
- rbac_* (permissões)
- system_parameters (config)

-- ESTENDER com tabelas do blueprint:
- leads
- proposals
- contracts
- events (enriquecer)
- service_orders
- production_orders
- recipes
- production_batches
- execution_sessions
```

**Chave de Integração:**
```sql
-- Todo novo registro emite evento para audit_log
-- Exemplo: ContractSigned
INSERT INTO contracts (...) VALUES (...);
-- Trigger automático cria audit_log entry
-- Trigger automático cria domain_events entry
```

### 2. APIS (Manter + Estender)

**Artefato Existente:** `PLANO_TECNICO_INFRA_v1.md`

```yaml
# JÁ EXISTE:
- /api/v1/audit-log/*
- /api/v1/decisions/*
- /api/v1/agent-logs/*
- /api/v1/rbac/*
- /api/v1/parameters/*

# ADICIONAR (do blueprint):
- /api/v1/crm/leads
- /api/v1/crm/proposals
- /api/v1/crm/contracts
- /api/v1/events
- /api/v1/orders/*
- /api/v1/production/*
- /api/v1/execution/*
```

### 3. REGRAS DE NEGÓCIO (Manter + Refinar)

**Artefato Existente:** `openclaw_learning_rules.json`

```json
{
  "rules": {
    // JÁ EXISTE - validar com dados reais:
    "margin_patterns": { "formaturas_media_grande": { "healthy_range": [0.25, 0.32] }},
    "ticket_rules": { "extreme_risk": { "condition": "ticket < 70" }},
    "cost_classification": { "DIRECT_COST", "SHARED_COST", "CAC", "INDIRECT" },
    "alert_triggers": { "MARGEM_FALSA", "DRE_CONTAMINADO", "TICKET_BAIXO" }
  }
}
```

**Refinamento com Blueprint:**
```json
{
  // ADICIONAR state machine rules:
  "state_transitions": {
    "lead_status": ["NEW", "CONTACTED", "QUALIFIED", "WON", "LOST"],
    "proposal_status": ["DRAFT", "SENT", "APPROVED", "REJECTED"],
    "event_status": ["PLANNED", "CONFIRMED", "PREPARING", "EXECUTING", "COMPLETED"]
  }
}
```

### 4. PREÇOS E DECISÕES (Manter + Conectar)

**Artefato Existente:** `pricing_engine.json`

```json
{
  "forecast_module": { /* JÁ EXISTE - benchmarks por tipo */ },
  "cost_structure": { /* JÁ EXISTE - estrutura de custo */ },
  "decision_matrix": { /* JÁ EXISTE - SAUDAVEL, AJUSTAR, RISCO, PREJUIZO */ }
}
```

**Conexão com Blueprint:**
```
Quando Contract criado:
  └── pricing_engine calcula projeção
      └── decision_log registra decisão
          └── Se REPRICE: Proposal version +1
          └── Se APROVAR: Event criado automaticamente
```

### 5. ENGINES EXECUTÁVEIS (Corrigir)

**Artefato Existente:** Runtime Summary mostra:

| Engine | Status | Problema | Solução |
|--------|--------|----------|---------|
| `kitchen_control.py` | ⚠️ | Items não existem (`CAR-001`, etc.) | Criar catalog_products + inventory |
| `fixed_cost_engine.py` | ✅ | Funcionando! | Manter, integrar com Event |
| `dre_engine.py` | ⚠️ | CMV vazio | Conectar com Production → InventoryBatch |
| `margin_validation.py` | ❌ | NO_DRE_DATA | Resolver dependência DRE |
| `financial_truth_audit.py` | ❌ | Crash | Fix bug estoque_saida |
| `executive_report.py` | ⚠️ | Genérico | Popular com dados reais |
| `ceo_dashboard.py` | ⚠️ | Mock data | Conectar com dashboard_data.json |

---

## 📋 ROADMAP REVISADO: INCREMENTAL

### FASE 1.5: ATIVAÇÃO (Semana 1) - NOVO!

**Objetivo:** Fazer o que já existe funcionar com dados reais.

```
✅ Semana 1.1: Correções urgentes
├── Fix financial_truth_audit.py (bug estoque_saida)
├── Criar catalog_products (items CAR-001, LEG-001, etc.)
├── Popular inventory_batches com dados reais
└── Resultado: DRE engine funciona com dados reais

✅ Semana 1.2: Integração
├── Conectar fixed_cost_engine → Evento real
├── Conectar dashboard → dashboard_data.json
└── Resultado: Engines mostram dados de R$ 7.7M

✅ Semana 1.3: Validação
├── Rodar full pipeline com dados reais
├── Comparar output com backtest_insights.md
└── Resultado: Consistência validada
```

### FASE 2: CRM + Event (Semana 2-4)

Baseado no blueprint, mas aproveitando infra existente:

```
Semana 2.1: CRM Schema
├── Reutilizar audit_log para leads, proposals, contracts
├── Reutilizar decision_log para scoring de leads
├── Reutilizar rbac para permissões CRM
└── DDL: leads, proposals, contracts tables

Semana 2.2: CRM API
├── Leverage endpoints de PLANO_TECNICO_INFRA
├── /api/v1/crm/* endpoints
└── Webhook: ContractSigned → Event

Semana 2.3: Event Enrichment
├── Reutilizar eventos do backtest
├── Adicionar FK: evento.contract_id
├── Adicionar status machine
└── Migração: Vincular eventos existentes a contracts
```

### FASE 3: Order System (Semana 5-6)

```
Semana 5.1: OS/OP Schema
├── service_orders table
├── production_orders table
├── so_to_po_mapping table
└── integração: Contract → SO → PO

Semana 5.2: Execution
├── ProductionBatch table
├── Recipe table
├── RecipeIngredient table
└── integração: PO → ProductionBatch → Inventory

Semana 6: Correction do GAP
├── DRE engine vê CMV real
├── kitchen_control acha items
├── margin_validation funciona
└── Resultado: Financial truth audit passa
```

### FASE 4: Digital Twin (Semana 7-8)

```
Semana 7: Execution Tracking
├── execution_sessions table
├── execution_checkpoints table
├── occurrences table
└── Integration: Event → ExecutionSession

Semana 8: Feedback Loop
├── Real vs Predicted comparison
├── Update pricing_engine com resultados
├── Update learning_rules com padrões
└── Resultado: Sistema aprende
```

### FASE 5: Go-Live (Semana 9-10)

```
├── Deploy schema completo
├── Migração de dados históricos
├── Treinamento equipe (CRM + Event)
├── Go-live: Novos leads no novo sistema
└── Manter: Eventos em andamento no sistema antigo
```

---

## 🔗 MATRIZ DE INTEGRAÇÃO

### Como os artefatos se conectam:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FLUXO DE DADOS                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │    USER      │───→│   AGENT      │───→│  TOOL CALL   │             │
│  │  (Orkestra)  │    │  (OpenClaw)  │    │  (read/exec) │             │
│  └──────────────┘    └──────┬───────┘    └──────┬───────┘             │
│                             │                   │                      │
│                             ↓                   ↓                      │
│                    ┌──────────────────┐ ┌──────────────────┐           │
│                    │  AGENT_ACTION_LOG│ │  FILE/SYSTEM     │           │
│                    │  (já existe)     │ │  (artefatos)     │           │
│                    └────────┬─────────┘ └────────┬─────────┘           │
│                             │                    │                     │
│                             ↓                    ↓                     │
│                    ┌──────────────────────────────────────┐           │
│                    │           AUDIT_LOG                  │           │
│                    │  (imutável, todo change tracked)    │           │
│                    └──────────────┬───────────────────────┘           │
│                                   │                                   │
│                                   ↓                                   │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                     DECISION LOG                             │    │
│  │   (pricing_engine + learning_rules → decisões)             │    │
│  └──────────────────────────┬───────────────────────────────────┘    │
│                             │                                         │
│         ┌───────────────────┼───────────────────┐                      │
│         ↓                   ↓                   ↓                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                │
│  │   FINANCIAL  │   │    EVENT     │   │  DASHBOARD   │                │
│  │    CORE      │   │   ENGINE     │   │   DATA       │                │
│  │   (existente)│   │   (novo)     │   │   (existente)│                │
│  └──────────────┘   └──────────────┘   └──────────────┘                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📝 CHECKLIST DE IMPLEMENTAÇÃO

### ✅ JÁ ESTÁ PRONTO (Manter)

- [x] PostgreSQL schema para audit, decisions, actions, rbac
- [x] APIs REST para infraestrutura
- [x] Pricing engine com benchmarks
- [x] ML rules com alertas
- [x] Backtest analysis (16 eventos)
- [x] Dashboard data (KPIs)
- [x] Fixed cost allocation engine

### 🔄 PRECISA CONEXÃO (Integrar)

- [ ] Conectar financial_truth_audit com dados reais
- [ ] Popular catalog_products (items do kitchen)
- [ ] Criar inventory_batches reais
- [ ] Link: fixed_cost → Event
- [ ] Link: dashboard → dashboard_data

### 🆕 PRECISA CONSTRUIR (Novo)

- [ ] CRM: leads, proposals, contracts
- [ ] Order: service_orders, production_orders
- [ ] Production: recipes, production_batches
- [ ] Execution: sessions, checkpoints, real_consumption
- [ ] Event Backbone: domain_events table + bus

---

## 💡 RECOMENDAÇÃO EXECUTIVA (ATUALIZADA)

### O QUE JÁ TEM (Não reinventar):
1. **Infraestrutura de logging** - Completa e imutável
2. **Pricing engine** - Validado com benchmarks reais
3. **Regras de negócio** - Extraídas de 16 eventos reais
4. **Backtest** - Dados de R$ 7.7M analisados

### O QUE PRECISA (Prioridade):
1. **CRM Pipeline** - Lead → Contract (quebra fluxo comercial)
2. **Event Enrichment** - Contrato, datas múltiplas, status
3. **Order System** - OS/OP (rastreabilidade produção)
4. **Digital Twin** - Execução vs Previsão (closing the loop)

### INVESTIMENTO ESTIMADO:
| Componente | Esforço | Status |
|------------|---------|--------|
| Infra | 0 semanas | ✅ Pronto |
| CRM | 2 semanas | 🆕 Novo |
| Order | 2 semanas | 🆕 Novo |
| Execution | 2 semanas | 🆕 Novo |
| Integração | 1 semana | 🔄 Conectar |
| **Total** | **7 semanas** | |

### MENOR ESFORÇO, MAIOR IMPACTO:
1. **Semana 1:** Corrigir engines → DRE funciona (impacto imediato)
2. **Semana 2-3:** CRM básico → Pipeline comercial
3. **Semana 4-5:** OS/OP → Produção rastreável
4. **Semana 6-7:** Execution → Digital Twin

---

## 🎯 PRÓXIMA AÇÃO

### Opção A: Correção Imediata (Recomendado)
```
Prioridade: Fazer funcionar o que já existe
├── Corrigir financial_truth_audit.py
├── Criar catalog_products.json com items reais
├── Popular inventory
└── Resultado: Engines geram insights de R$ 7.7M
```

### Opção B: Blueprint Completo
```
Prioridade: Seguir o blueprint arquitetural
├── Implementar CRM + schemas
├── Implementar Order System
├── Implementar Execution
└── Resultado: Sistema end-to-end em 7 semanas
```

### Opção C: Híbrida (Estratégica)
```
Semana 1: Correção + Integração (ativar o que existe)
Semana 2+: Implementar CRM/Order/Execution
Resultado: Base sólida + evolução
```

---

**🎛️ ORKESTRA INTEGRATION MAP v1.0**
*Consolidação de arquitetura existente + blueprint*

Qual opção seguir? A, B, ou C?
