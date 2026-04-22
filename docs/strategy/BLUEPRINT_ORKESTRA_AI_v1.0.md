# 🏗️ BLUEPRINT ARQUITETURAL FINAL - ORKESTRA.AI v1.0

**Data:** 2026-04-15  
**Arquiteto:** Chief System Architect + Staff Engineer + Domain Specialist  
**Status:** BLUEPRINT (não migrar ainda)  
**Decisão:** Arquitetura Híbrida (Opção C)

---

## 1️⃣ DIAGNÓSTICO CONSOLIDADO DO ESTADO ATUAL

### 1.1 O que está FUNCIONANDO (Preservar)

| Componente | Status | Evidência |
|------------|--------|-----------|
| Financial Core | ✅ Sólido | 2 empresas, 80 registros financeiros, projeção 90d funcionando |
| Multi-tenant | ✅ Sólido | LA ORANA + STATUS Opera com isolamento correto |
| Alertas/Riscos | ✅ Sólido | CAIXA_NEGATIVO, RECEITA_SEM_CONTRATO detectados |
| Intercompany | ✅ Funcional | R$ 621.680 em transações mapeadas |
| Classificação | ✅ Boa | Categorias automáticas (proteína, bebida, staff, etc.) |
| JSON Schema | ✅ Consistente | Estrutura de payload padronizada |

### 1.2 Problemas CRÍTICOS identificados nos dados

#### Problema A: QUEBRA NO PIPELINE COMERCIAL
```
DADOS REAIS mostram:
- REC-00003: R$ 21.105 "RECEITA_SEM_CONTRATO" (não reconciliada)
- REC-00006: R$ 329.673 "RECEITA_SEM_CONTRATO"
- REC-00009: R$ 90.887 "RECEITA_SEM_CONTRATO"
... total de R$ 1.283.584 em receitas sem contrato vinculado
```

**Diagnóstico:** Não existe entidade `contract` no sistema atual. O fluxo Lead → Qualificação → Proposta → Contrato → Evento está QUEBRADO.

#### Problema B: FALTA ORDEM DE SERVIÇO/PRODUÇÃO
```
EVENTO atual = só data + nome
FALTA:
- OS (Ordem de Serviço) - o que foi vendido
- OP (Ordem de Produção) - o que será produzido
- Link entre OS vendida e OP executada
```

#### Problema C: GAP PRODUÇÃO/LOGÍSTICA
```
Só existe: COMPRA, PAGAMENTO, ESTOQUE_ENTRADA/SAIDA
FALTA:
- Planejamento de produção (quanto fazer, quando, onde)
- Logística (montagem, desmontagem, transporte)
- Consumo real vs previsto
- Fechamento com análise de desvio
```

#### Problema D: SEM TRACKING DE EXECUÇÃO
```
Não existe:
- checklist de execução do evento
- registro de ocorrências
- fotos/documentação vinculada ao evento
- assinatura/responsável por etapa
```

### 1.3 Resumo do Diagnóstico

```
┌─────────────────────────────────────────────────────────────┐
│  INFRAESTRUTURA:       ████████████████  90% - Sólida     │
│  DOMÍNIO NEGÓCIO:       █████████░░░░░   60% - Quebrado    │
│  FLUXO OPERACIONAL:     ██████░░░░░░░░   40% - Crítico      │
│  INTEGRAÇÃO E2E:        █████░░░░░░░░░   30% - Inexistente  │
│  DIGITAL TWIN:          ███░░░░░░░░░░░   20% - Não existe    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ DECISÃO ARQUITETURAL ADOTADA

### 2.1 Rationale

Decisão: **ARQUITETURA HÍBRIDA (Opção C)**

**Por que NÃO migrar agora:**
1. Schema atual não representa a operação real de eventos
2. Migração agora = congelar modelo quebrado
3. Financial Core está funcionando - não quebrar
4. BluePrint primeiro, migração depois

**Estratégia:**
```
Phase 1 (agora):  CONSTRUIR BLUEPRINT
Phase 2:         REFATORAÇÃO SELETIVA (não toca Financial Core)
Phase 3:          MIGRAÇÃO FINAL (apenas dados do novo domínio)
Phase 4:          IMPLANTAÇÃO OPERACIONAL
```

### 2.2 Princípios Arquiteturais

1. **Event Sourcing para domínio transacional** - todo estado é resultado de eventos
2. **CQRS para queries complexas** - separar leitura de escrita
3. **Domain-Driven Design** - entidades ricas, não anêmicas
4. **Multi-tenant nativo** - tenant_id em TUDO, sempre
5. **Audit trail completo** - quem, quando, por quê em toda mudança
6. **State machines explícitas** - não inferência, definição formal

---

## 3️⃣ DOMÍNIOS FINAIS DO SISTEMA

### 3.1 Mapa de Domínios (Bounded Contexts)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           ORKESTRA.AI                                      │
│                         ═══════════════                                    │
│                                                                            │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────┐           │
│  │   🎯 CRM       │   │   📊 INSIGHTS    │   │   ⚙️ SHARED    │           │
│  │   Context      │   │   Context      │   │   KERNEL       │           │
│  └───────┬────────┘   └───────┬────────┘   └───────┬────────┘           │
│          │                    │                    │                      │
│  ┌───────▼────────────────────▼────────────────────▼────────┐           │
│  │              📅 EVENT ENGINE (Core Domain)                  │           │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐             │           │
│  │  │📋 Order   │  │🍽️ Production│  │📦 Logistics │             │           │
│  │  │Context    │  │Context    │  │Context    │             │           │
│  │  └───────────┘  └───────────┘  └───────────┘             │           │
│  └────────────────────────────────────────────────────────────┘           │
│                              │                                             │
│                    ┌─────────▼─────────┐                                   │
│                    │  💰 FINANCIAL     │                                   │
│                    │  Context          │                                   │
│                    │  (Preservado!)    │                                   │
│                    └───────────────────┘                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Domínios Detalhados

#### Domínio: CRM / COMERCIAL
**Responsabilidade:** Pipeline comercial completo

**Entidades:**
- `Lead` (prospect, origem, pontuação)
- `Qualification` (necessidades, orçamento, autoridade, timeline)
- `Proposal` (itens, valores, validade, versões)
- `Contract` (assinado, condições comerciais)

**Integrações:**
- Emite: ContractSigned → Event Engine
- Consome: ProposalFeedback → atualiza lead

#### Domínio: EVENT ENGINE (Core)
**Responsabilidade:** Ciclo de vida do evento

**Entidades:**
- `Event` (dados master do evento)
- `Venue` (local, configuração de espaço)
- `Client` (dados do cliente)
- `EventDate` (datas específicas - pode ter várias)
- `EventConfiguration` (setup do espaço)

**Integrações:**
- Consome: ContractSigned → cria Event
- Emite: EventCreated → OS/OP
- Emite: EventConfirmed → Production/Logistics

#### Domínio: ORDER SYSTEM
**Responsabilidade:** O que foi vendido vs o que será feito

**Entidades:**
- `ServiceOrder` (OS) - o que o cliente comprou (menu, estrutura, etc)
- `ProductionOrder` (OP) - o que a cozinha/operacional vai produzir
- `OSItem` / `OPItem` - linhas detalhadas
- `OSPPMapping` - mapeamento entre OS e OP (nem tudo vendido é produzido 1:1)

**Regra crítica:** Uma OS pode gerar múltiplas OPs (evento grande) ou uma OP pode atender múltiplas OSs (eventos pequenos combinados).

#### Domínio: PROCUREMENT (Compras)
**Responsabilidade:** Aquisição de materiais

**Entidades:**
- `PurchaseRequest` (solicitação da OP)
- `PurchaseOrder` (pedido ao fornecedor)
- `PurchaseOrderItem` (itens do pedido)
- `Supplier` (fornecedores)
- `SupplierQuote` (cotações)

**Integrações:**
- Consome: ProductionOrderCreated → cria PurchaseRequest
- Emite: PurchaseReceived → Inventory

#### Domínio: INVENTORY (Estoque)
**Responsabilidade:** Materiais e insumos

**Entidades:**
- `InventoryItem` (catálogo de itens)
- `InventoryBatch` (lotes com data validade - crítico para comida)
- `Warehouse` (depósitos - pode ter múltiplos)
- `StockMovement` (entrada/saída/ajuste)
- `Reservation` (reserva para evento futuro)

**Integrações:**
- Consome: ItemPurchased → entrada
- Consome: EventConfirmed → cria Reservation
- Consome: EventExecuted → converte Reserva em Saída efetiva

#### Domínio: PRODUCTION (Produção)
**Responsabilidade:** Execução da cozinha/prep

**Entidades:**
- `ProductionBatch` (lote de produção)
- `Recipe` (ficha técnica - ingredientes, processo)
- `ProductionStep` (etapas de preparo)
- `QualityCheck` (controle de qualidade)

**Integrações:**
- Consome: OPScheduled → cria ProductionBatch
- Emite: ProductionComplete → Logistics(movement)

#### Domínio: LOGISTICS
**Responsabilidade:** Transporte, montagem, desmontagem

**Entidades:**
- `LogisticsOrder` (ordem de transporte/montagem)
- `Vehicle` (frota)
- `Crew` (equipe de montagem)
- `Trip` (viagens)
- `EquipmentList` (checklist de equipamentos)

**Integrações:**
- Consome: EventConfirmed → cria LogisticsOrders
- Consome: ProductionComplete → trigger Transport
- Emite: SetupComplete → Event ready
- Emite: TeardownComplete → itens retornam ao estoque

#### Domínio: EXECUTION (Dia do Evento)
**Responsabilidade:** Acompanhamento real-time

**Entidades:**
- `ExecutionSession` (sessão de execução)
- `Checkpoint` (pontos de verificação)
- `Occurrence` (ocorrências/incidentes)
- `Photo` (registro visual)
- `SignOff` (assinatura de conclusão)

**Integrações:**
- Emite: EventStarted, EventCompleted → todos os domínios
- Emite: Data para Learning Layer

#### Domínio: FINANCIAL (Preservado!)
**Responsabilidade:** Controle financeiro (já funciona!)

**Entidades:**
- `AccountPayable` (contas a pagar)
- `AccountReceivable` (contas a receber)
- `CashFlow` (fluxo de caixa)
- `IntercompanyTransaction` (entre empresas)
- `CostCenter` (centros de custo)
- `Budget` (orçamentos)

**Atenção:** Financial Core NÃO MUDA. Apenas recebe eventos dos outros domínios.

#### Domínio: INSIGHTS / LEARNING
**Responsabilidade:** Análise e aprendizado

**Entidades:**
- `EventMetrics` (KPIs do evento)
- `CostAnalysis` (análise de custo)
- `Prediction` (previsões baseadas em histórico)
- `Recommendation` (sugestões de otimização)

---

## 4️⃣ PIPELINE OPERACIONAL FINAL

### 4.1 Fluxo Completo (BPMN-like)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   LEAD      │───▶│ QUALIFICAÇÃO │───▶│   PROPOSTA  │───▶│   CONTRATO  │
│   (novo)    │    │   (novo)     │    │   (novo)    │    │   (novo)    │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                 │
                            ┌───────────────────────────────────┘
                            ▼
              ┌─────────────────────────────┐
              │        EVENTO               │
              │    (já existente,          │
              │     mas enriquecido)       │
              └──────────────┬──────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │      OS      │ │   LOGÍSTICA  │ │   OP + PROD  │
    │  (novo)      │ │   (novo)     │ │   (novo)     │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           │    ┌───────────┴────────────────┘
           │    │
           ▼    ▼
    ┌─────────────────────────────────────┐
    │           EXECUÇÃO                  │
    │  checklist, ocorrências, fotos,     │
    │  assinaturas, consumo real        │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │         FECHAMENTO                  │
    │  reconciliação, análise de desvio,  │
    │  insights, aprendizado              │
    └─────────────────────────────────────┘
```

### 4.2 Estados e Transições

#### State Machine: Lead
```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  NEW    │───▶│CONTACTED│───▶│QUALIFIED│───▶│ PROPOSAL│───▶│  WON    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │               │
     └──────────────┴──────────────┴──────────────┴───────────────▶ LOST

Eventos emitidos:
- LeadCreated, LeadContacted, LeadQualified, ProposalSent, LeadWon, LeadLost
```

#### State Machine: Proposal
```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  DRAFT  │───▶│ SENT    │───▶│ PENDING │───▶│APPROVED │───▶│CONVERTED│
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                      │            │                           │
                      └────────────┴───────────────────────────▶ REJECTED
                       (rejected ou timeout)

Eventos emitidos:
- ProposalCreated, ProposalSent, ProposalViewed, ProposalApproved, ProposalRejected
```

#### State Machine: Event
```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ PLANNED │───▶│CONFIRMED│───▶│PREPARING│───▶│ EXECUTING│───▶│COMPLETED│
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                    │                                              │
                    └────────────▶ CANCELLED ◀────────────────────┘

Sub-states de EXECUTING:
  ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
  │ SETUP  │──▶│SERVICE │──▶│SERVICE │──▶│TEARDOWN│──▶│ REVIEW │
  │        │   │ START  │   │  END   │   │        │   │        │
  └────────┘   └────────┘   └────────┘   └────────┘   └────────┘

Eventos emitidos:
- EventPlanned, EventConfirmed, EventPrepStarted, EventSetupComplete,
- EventStarted, EventEnded, EventTeardownComplete, EventCompleted, EventCancelled
```

#### State Machine: ServiceOrder
```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  DRAFT  │───▶│PENDING  │───▶│APPROVED │───▶│IN_PROD  │───▶│DELIVERED│
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                    │                           │
                                    └─────────────────────────▶ CANCELLED

Eventos emitidos:
- SOCreated, SOSubmittedForApproval, SOApproved, SOInProduction, SODelivered, SOCancelled
```

#### State Machine: ProductionOrder
```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  PENDING│───▶│SCHEDULED│───▶│ IN_PROD │───▶│  READY  │───▶│COMPLETED│
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                     │                          │
                                     └────────────────────────▶ CANCELLED

Eventos emitidos:
- POCreated, POScheduled, POStarted, POCompleted, POCancelled
```

#### State Machine: Purchase Order
```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  DRAFT  │───▶│ SENT    │───▶│CONFIRMED│───▶│ RECEIVED│───▶│ INVOICED│
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     │                                              │             │
     └──────────────────────────────────────────────┴─────────────▶ PAID
                                    (parcial ou total)

Eventos emitidos:
- POCreated, POSent, POConfirmed, POReceived, POInvoiced, POPaid
```

#### State Machine: Inventory Item
```
AVAILABLE ──▶ RESERVED ──▶ COMMITTED ──▶ IN_USE ──▶ RETURNED ──▶ AVAILABLE
                │                              │
                └──────────────────────────────▶ CONSUMED/DAMAGED/LOST

Eventos emitidos:
- ItemReserved, ItemCommitted, ItemInUse, ItemReturned, ItemConsumed
```

---

## 5️⃣ SCHEMA-ALVO MÍNIMO RECOMENDADO

### 5.1 Estratégia de Schema

**Princípio:** Schema mínimo viável + extensível. Não over-engineering.

**Convenções:**
- Todas as tabelas têm: `id` (UUID), `tenant_id`, `created_at`, `updated_at`, `created_by`, `updated_by`
- Soft delete: `deleted_at` (nullable)
- JSONB para metadados extensíveis: `metadata`
- Campos obrigatórios = NOT NULL, resto = NULLABLE

### 5.2 Schema SQL (PostgreSQL)

```sql
-- =============================================================
-- EXTENSÕES
-- =============================================================
extension "uuid-ossp";
extension "pg_trgm";
extension "btree_gist";

-- =============================================================
-- TABELAS COMPARTILHADAS (SHARED KERNEL)
-- =============================================================

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) CHECK (type IN ('HQ', 'CATERING', 'LOCACAO', 'SERVICO')),
    parent_tenant_id UUID REFERENCES tenants(id),
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'commercial', 'operational', 'finance', 'kitchen')),
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices críticos
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- =============================================================
-- DOMÍNIO: CRM / COMERCIAL
-- =============================================================

CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Dados do prospect
    company_name VARCHAR(255),
    contact_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    source VARCHAR(100), -- 'site', 'indicacao', 'feira', 'social'
    
    -- Qualificação BANT
    budget DECIMAL(15,2),
    authority VARCHAR(255), -- quem decide
    need TEXT,
    timeline DATE,
    
    -- Estado
    status VARCHAR(50) DEFAULT 'NEW' CHECK (status IN ('NEW', 'CONTACTED', 'QUALIFIED', 'PROPOSAL_SENT', 'WON', 'LOST')),
    score INTEGER CHECK (score >= 0 AND score <= 100),
    assigned_to UUID REFERENCES users(id),
    
    -- Timestamps
    contacted_at TIMESTAMP WITH TIME ZONE,
    qualified_at TIMESTAMP WITH TIME ZONE,
    converted_at TIMESTAMP WITH TIME ZONE,
    lost_at TIMESTAMP WITH TIME ZONE,
    lost_reason TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE lead_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES leads(id),
    user_id UUID REFERENCES users(id),
    activity_type VARCHAR(50) NOT NULL, -- 'call', 'email', 'meeting', 'note'
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    lead_id UUID REFERENCES leads(id),
    
    -- Numeração
    proposal_number VARCHAR(50) UNIQUE NOT NULL,
    version INTEGER DEFAULT 1,
    
    -- Valores
    subtotal DECIMAL(15,2) NOT NULL,
    tax_amount DECIMAL(15,2) DEFAULT 0,
    total_amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'BRL',
    
    -- Datas
    valid_until DATE NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,
    
    -- Estado
    status VARCHAR(50) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'SENT', 'PENDING', 'APPROVED', 'REJECTED', 'CONVERTED')),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_reason TEXT,
    
    -- Documento
    document_url TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE proposal_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposal_id UUID NOT NULL REFERENCES proposals(id),
    
    -- Item
    item_type VARCHAR(50) NOT NULL, -- 'menu', 'bar', 'structure', 'service', 'staff'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Valores
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(50),
    unit_price DECIMAL(15,2) NOT NULL,
    total_price DECIMAL(15,2) NOT NULL,
    
    -- Custo estimado (para análise de margem)
    estimated_cost DECIMAL(15,2),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    proposal_id UUID NOT NULL UNIQUE REFERENCES proposals(id),
    lead_id UUID NOT NULL REFERENCES leads(id),
    
    -- Numeração
    contract_number VARCHAR(50) UNIQUE NOT NULL,
    
    -- Evento vinculado (criado automaticamente após assinatura)
    event_id UUID, -- será preenchido após criar evento
    
    -- Datas do contrato
    signed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    signed_by_client VARCHAR(255),
    signed_by_company VARCHAR(255),
    
    -- Termos
    total_value DECIMAL(15,2) NOT NULL,
    payment_terms TEXT,
    cancellation_policy TEXT,
    
    -- Documentos
    contract_document_url TEXT,
    
    status VARCHAR(50) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CANCELLED', 'COMPLETED')),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices CRM
CREATE INDEX idx_leads_tenant ON leads(tenant_id);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_assigned ON leads(assigned_to);
CREATE INDEX idx_proposals_tenant ON proposals(tenant_id);
CREATE INDEX idx_proposals_lead ON proposals(lead_id);
CREATE INDEX idx_contracts_event ON contracts(event_id);

-- =============================================================
-- DOMÍNIO: EVENT ENGINE
-- =============================================================

CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Dados cadastrais
    name VARCHAR(255) NOT NULL,
    document VARCHAR(50), -- CPF/CNPJ
    email VARCHAR(255),
    phone VARCHAR(50),
    
    -- Endereço
    address JSONB,
    
    -- Segmento
    client_type VARCHAR(50) CHECK (client_type IN ('PF', 'PJ')),
    segment VARCHAR(100), -- 'corporativo', 'casamento', 'festa', etc
    
    -- Relacionamento
    lead_id UUID REFERENCES leads(id),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE venues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    address JSONB NOT NULL,
    
    -- Capacidades
    capacity_standing INTEGER,
    capacity_seated INTEGER,
    
    -- Configurações
    has_kitchen BOOLEAN DEFAULT false,
    has_parking BOOLEAN DEFAULT false,
    accessibility JSONB,
    
    -- Contato
    contact_name VARCHAR(255),
    contact_phone VARCHAR(50),
    
    is_active BOOLEAN DEFAULT true,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    contract_id UUID REFERENCES contracts(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    venue_id UUID REFERENCES venues(id),
    
    -- Identificação
    event_name VARCHAR(255) NOT NULL,
    event_code VARCHAR(50) UNIQUE NOT NULL, -- "EVT-2026-001"
    
    -- Tipo e estilo
    event_type VARCHAR(100) NOT NULL, -- 'corporate', 'wedding', 'birthday', 'graduation'
    event_style VARCHAR(100), -- 'cocktail', 'seated', 'buffet', 'finger_food'
    
    -- Público
    expected_guests INTEGER,
    confirmed_guests INTEGER,
    
    -- Estado
    status VARCHAR(50) DEFAULT 'PLANNED' CHECK (status IN ('PLANNED', 'CONFIRMED', 'PREPARING', 'SETUP', 'EXECUTING', 'TEARDOWN', 'COMPLETED', 'CANCELLED')),
    
    -- Responsáveis
    sales_manager_id UUID REFERENCES users(id),
    operational_manager_id UUID REFERENCES users(id),
    chef_id UUID REFERENCES users(id),
    
    -- Orçamento total do evento (do contrato)
    total_budget DECIMAL(15,2),
    
    -- Análise pós-evento
    actual_revenue DECIMAL(15,2),
    actual_cost DECIMAL(15,2),
    margin_percentage DECIMAL(5,2),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Event pode ter múltiplas datas (multi-day events)
CREATE TABLE event_dates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id),
    
    date DATE NOT NULL,
    -- Horários podem variar por dia
    setup_start_time TIME,
    service_start_time TIME,
    service_end_time TIME,
    teardown_end_time TIME,
    
    is_main_date BOOLEAN DEFAULT false, -- qual data principal para cobrança
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE event_configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id),
    venue_id UUID REFERENCES venues(id),
    
    -- Configuração do espaço
    layout_type VARCHAR(100), -- 'theater', 'u_shape', 'round_tables', etc
    number_of_tables INTEGER,
    chairs_per_table INTEGER,
    
    -- Equipamentos no local
    needs_stage BOOLEAN DEFAULT false,
    needs_dance_floor BOOLEAN DEFAULT false,
    needs_lighting BOOLEAN DEFAULT false,
    needs_sound BOOLEAN DEFAULT false,
    
    -- Áreas
    has_bar_area BOOLEAN DEFAULT false,
    number_of_bar_stations INTEGER,
    has_catering_area BOOLEAN DEFAULT false,
    
    notes TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices Event
CREATE INDEX idx_events_tenant ON events(tenant_id);
CREATE INDEX idx_events_client ON events(client_id);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_dates ON event_dates(event_id, date);

-- =============================================================
-- DOMÍNIO: ORDER SYSTEM (OS + OP)
-- =============================================================

CREATE TABLE service_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    event_id UUID NOT NULL REFERENCES events(id),
    proposal_id UUID REFERENCES proposals(id),
    
    -- Numeração
    so_number VARCHAR(50) UNIQUE NOT NULL, -- "OS-2026-001"
    
    -- Tipo
    so_type VARCHAR(50) NOT NULL, -- 'CATERING', 'BAR', 'STRUCTURE', 'STAFF'
    
    -- Estado
    status VARCHAR(50) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'IN_PRODUCTION', 'DELIVERED', 'CANCELLED')),
    
    -- Valores
    subtotal DECIMAL(15,2) NOT NULL,
    total DECIMAL(15,2) NOT NULL,
    
    -- Timeline
    required_delivery TIMESTAMP WITH TIME ZONE,
    actual_delivery TIMESTAMP WITH TIME ZONE,
    
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE service_order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_order_id UUID NOT NULL REFERENCES service_orders(id),
    
    -- Item
    item_category VARCHAR(50) NOT NULL, -- 'MENU', 'DRINK', 'EQUIPMENT', 'SERVICE'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Quantidade e valores
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(50),
    unit_price DECIMAL(15,2) NOT NULL,
    total_price DECIMAL(15,2) NOT NULL,
    
    -- Link com produção
    -- Este campo conecta o que foi VENDIDO com o que será FEITO
    produces_item_id UUID, -- referência ao item de estoque/produção
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE production_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    event_id UUID NOT NULL REFERENCES events(id),
    
    -- Pode ser criado a partir de uma ou mais SOs
    source_so_ids UUID[] DEFAULT '{}',
    
    -- Numeração
    po_number VARCHAR(50) UNIQUE NOT NULL, -- "OP-2026-001"
    
    -- Estado
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SCHEDULED', 'IN_PRODUCTION', 'READY', 'DELIVERED', 'CANCELLED')),
    
    -- Produção
    production_date DATE,
    production_location VARCHAR(255), -- qual cozinha/fábrica
    responsible_chef_id UUID REFERENCES users(id),
    
    -- Timeline
    required_ready_at TIMESTAMP WITH TIME ZONE,
    actual_ready_at TIMESTAMP WITH TIME ZONE,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE production_order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    production_order_id UUID NOT NULL REFERENCES production_orders(id),
    
    -- Item a produzir
    recipe_id UUID, -- se tiver ficha técnica
    item_name VARCHAR(255) NOT NULL,
    
    -- Quantidades
    planned_quantity DECIMAL(10,2) NOT NULL,
    produced_quantity DECIMAL(10,2),
    wasted_quantity DECIMAL(10,2) DEFAULT 0,
    
    -- Custo
    estimated_cost DECIMAL(15,2),
    actual_cost DECIMAL(15,2),
    
    -- Link com SO
    source_so_item_id UUID REFERENCES service_order_items(id),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Mapeamento explícito entre OS e OP (muitos-para-muitos)
CREATE TABLE so_to_po_mapping (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_order_id UUID NOT NULL REFERENCES service_orders(id),
    production_order_id UUID NOT NULL REFERENCES production_orders(id),
    
    -- Detalhes do mapeamento
    so_item_id UUID REFERENCES service_order_items(id),
    po_item_id UUID REFERENCES production_order_items(id),
    
    mapped_by UUID REFERENCES users(id),
    mapped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    notes TEXT
);

-- Índices Order System
CREATE INDEX idx_service_orders_event ON service_orders(event_id);
CREATE INDEX idx_service_orders_status ON service_orders(status);
CREATE INDEX idx_production_orders_event ON production_orders(event_id);
CREATE INDEX idx_production_orders_date ON production_orders(production_date);

-- =============================================================
-- DOMÍNIO: PROCUREMENT
-- =============================================================

CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    name VARCHAR(255) NOT NULL,
    document VARCHAR(50),
    category VARCHAR(100), -- 'proteins', 'beverages', 'disposables', 'equipment'
    
    -- Contato
    contact_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    address JSONB,
    
    -- Termos comerciais
    payment_terms VARCHAR(100),
    delivery_time_days INTEGER,
    minimum_order DECIMAL(15,2),
    
    is_approved BOOLEAN DEFAULT false,
    rating DECIMAL(2,1) CHECK (rating >= 0 AND rating <= 5),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Identificação
    sku VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    
    -- Unidade
    unit_of_measure VARCHAR(50) NOT NULL,
    
    -- Estoque
    is_stockable BOOLEAN DEFAULT true,
    min_stock_level DECIMAL(10,2),
    ideal_stock_level DECIMAL(10,2),
    
    -- Custo
    standard_cost DECIMAL(15,2),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    supplier_id UUID NOT NULL REFERENCES suppliers(id),
    
    -- Origem
    production_order_id UUID REFERENCES production_orders(id),
    event_id UUID REFERENCES events(id),
    
    -- Numeração
    po_number VARCHAR(50) UNIQUE NOT NULL,
    
    -- Estado
    status VARCHAR(50) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'SENT', 'CONFIRMED', 'PARTIAL', 'RECEIVED', 'INVOICED', 'PAID', 'CANCELLED')),
    
    -- Datas
    order_date DATE NOT NULL,
    expected_delivery DATE,
    actual_delivery DATE,
    
    -- Financeiro
    subtotal DECIMAL(15,2) NOT NULL,
    tax_amount DECIMAL(15,2) DEFAULT 0,
    total DECIMAL(15,2) NOT NULL,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE purchase_order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id),
    product_id UUID REFERENCES products(id),
    
    -- Item
    description VARCHAR(255) NOT NULL,
    
    -- Quantidade
    quantity_ordered DECIMAL(10,2) NOT NULL,
    quantity_received DECIMAL(10,2) DEFAULT 0,
    
    -- Valores
    unit_price DECIMAL(15,2) NOT NULL,
    total_price DECIMAL(15,2) NOT NULL,
    
    -- Requisição original
    requested_for_po_item_id UUID REFERENCES production_order_items(id),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices Procurement
CREATE INDEX idx_purchase_orders_supplier ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);
CREATE INDEX idx_purchase_orders_event ON purchase_orders(event_id);

-- =============================================================
-- DOMÍNIO: INVENTORY
-- =============================================================

CREATE TABLE warehouses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) CHECK (type IN ('CENTRAL', 'KITCHEN', 'MOBILE', 'SUPPLIER')),
    address JSONB,
    is_active BOOLEAN DEFAULT true,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE inventory_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    product_id UUID NOT NULL REFERENCES products(id),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    
    -- Origem
    purchase_order_item_id UUID REFERENCES purchase_order_items(id),
    
    -- Lote
    batch_number VARCHAR(100),
    
    -- Quantidades
    initial_quantity DECIMAL(10,2) NOT NULL,
    current_quantity DECIMAL(10,2) NOT NULL,
    reserved_quantity DECIMAL(10,2) DEFAULT 0,
    
    -- Datas críticas (especialmente para alimentos)
    manufactured_date DATE,
    expiry_date DATE NOT NULL,
    
    -- Custo
    unit_cost DECIMAL(15,2) NOT NULL,
    
    status VARCHAR(50) DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE', 'RESERVED', 'IN_USE', 'DEPLETED', 'EXPIRED', 'DAMAGED')),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE stock_movements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Referências
    batch_id UUID REFERENCES inventory_batches(id),
    product_id UUID NOT NULL REFERENCES products(id),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    
    -- Tipo de movimento
    movement_type VARCHAR(50) NOT NULL CHECK (movement_type IN ('IN', 'OUT', 'TRANSFER', 'ADJUSTMENT', 'WASTE', 'RETURN')),
    
    -- Quantidade (positiva para entrada, negativa para saída)
    quantity DECIMAL(10,2) NOT NULL,
    
    -- Origem/destino
    source_type VARCHAR(50), -- 'PURCHASE', 'PRODUCTION', 'EVENT', 'ADJUSTMENT'
    source_id UUID,
    
    -- Evento relacionado
    event_id UUID REFERENCES events(id),
    
    -- Responsável
    responsible_user_id UUID REFERENCES users(id),
    
    -- Razão
    reason TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE inventory_reservations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    event_id UUID NOT NULL REFERENCES events(id),
    batch_id UUID REFERENCES inventory_batches(id),
    product_id UUID NOT NULL REFERENCES products(id),
    
    -- Quantidade
    quantity_reserved DECIMAL(10,2) NOT NULL,
    quantity_committed DECIMAL(10,2) DEFAULT 0,
    quantity_consumed DECIMAL(10,2) DEFAULT 0,
    quantity_returned DECIMAL(10,2) DEFAULT 0,
    
    -- Estado
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'COMMITTED', 'PARTIAL_USED', 'FULLY_USED', 'CANCELLED', 'RELEASED')),
    
    required_by TIMESTAMP WITH TIME ZONE,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices Inventory
CREATE INDEX idx_inventory_batches_product ON inventory_batches(product_id);
CREATE INDEX idx_inventory_batches_warehouse ON inventory_batches(warehouse_id);
CREATE INDEX idx_inventory_batches_expiry ON inventory_batches(expiry_date);
CREATE INDEX idx_stock_movements_product ON stock_movements(product_id);
CREATE INDEX idx_stock_movements_event ON stock_movements(event_id);
CREATE INDEX idx_reservations_event ON inventory_reservations(event_id);

-- =============================================================
-- DOMÍNIO: PRODUCTION (Produção/Cozinha)
-- =============================================================

CREATE TABLE recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100), -- 'appetizer', 'main', 'dessert', 'drink'
    
    -- Rendimento
    yield_quantity DECIMAL(10,2),
    yield_unit VARCHAR(50),
    
    -- Modo de preparo
    preparation_time_minutes INTEGER,
    cooking_time_minutes INTEGER,
    instructions TEXT,
    
    -- Custo padrão calculado
    standard_cost DECIMAL(15,2),
    
    is_active BOOLEAN DEFAULT true,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE recipe_ingredients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipe_id UUID NOT NULL REFERENCES recipes(id),
    product_id UUID NOT NULL REFERENCES products(id),
    
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    
    -- Custo
    cost_per_unit DECIMAL(15,2),
    
    is_optional BOOLEAN DEFAULT false,
    notes TEXT,
    
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE production_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    production_order_id UUID NOT NULL REFERENCES production_orders(id),
    recipe_id UUID REFERENCES recipes(id),
    
    -- Identificação
    batch_number VARCHAR(100),
    
    -- Quantidades
    planned_quantity DECIMAL(10,2) NOT NULL,
    produced_quantity DECIMAL(10,2),
    wasted_quantity DECIMAL(10,2) DEFAULT 0,
    
    -- Qualidade
    quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 10),
    quality_notes TEXT,
    
    -- Responsável
    prepared_by UUID REFERENCES users(id),
    checked_by UUID REFERENCES users(id),
    
    -- Tempos
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    status VARCHAR(50) DEFAULT 'SCHEDULED' CHECK (status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'REJECTED', 'WASTED')),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE production_consumption (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    production_batch_id UUID NOT NULL REFERENCES production_batches(id),
    batch_id UUID NOT NULL REFERENCES inventory_batches(id),
    product_id UUID NOT NULL REFERENCES products(id),
    
    quantity_used DECIMAL(10,2) NOT NULL,
    unit_cost DECIMAL(15,2) NOT NULL,
    total_cost DECIMAL(15,2) NOT NULL,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices Production
CREATE INDEX idx_recipes_tenant ON recipes(tenant_id);
CREATE INDEX idx_production_batches_po ON production_batches(production_order_id);
CREATE INDEX idx_production_batches_recipe ON production_batches(recipe_id);

-- =============================================================
-- DOMÍNIO: LOGISTICS
-- =============================================================

CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    name VARCHAR(255) NOT NULL,
    plate VARCHAR(50),
    type VARCHAR(100), -- 'truck', 'van', 'trailer'
    capacity_kg DECIMAL(10,2),
    capacity_m3 DECIMAL(10,2),
    
    is_active BOOLEAN DEFAULT true,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE crews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    name VARCHAR(255) NOT NULL,
    leader_id UUID REFERENCES users(id),
    
    -- Especialidades
    specialties VARCHAR[] DEFAULT '{}', -- ['assembly', 'catering', 'bar', 'sound']
    
    is_active BOOLEAN DEFAULT true,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE crew_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crew_id UUID NOT NULL REFERENCES crews(id),
    user_id UUID REFERENCES users(id),
    
    -- Se não for usuário do sistema, dados básicos
    name VARCHAR(255),
    phone VARCHAR(50),
    role VARCHAR(100),
    
    is_leader BOOLEAN DEFAULT false,
    
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE logistics_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    event_id UUID NOT NULL REFERENCES events(id),
    
    -- Tipo
    logistics_type VARCHAR(50) NOT NULL CHECK (logistics_type IN ('SETUP', 'TRANSPORT', 'TEARDOWN', 'EQUIPMENT_RETURN')),
    
    -- Estado
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    
    -- Recursos
    vehicle_id UUID REFERENCES vehicles(id),
    crew_id UUID REFERENCES crews(id),
    
    -- Timeline
    scheduled_start TIMESTAMP WITH TIME ZONE,
    scheduled_end TIMESTAMP WITH TIME ZONE,
    actual_start TIMESTAMP WITH TIME ZONE,
    actual_end TIMESTAMP WITH TIME ZONE,
    
    -- Localização
    from_location JSONB,
    to_location JSONB,
    
    -- Observações
    notes TEXT,
    issues TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE logistics_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    logistics_order_id UUID NOT NULL REFERENCES logistics_orders(id),
    
    item_type VARCHAR(50) NOT NULL, -- 'EQUIPMENT', 'SUPPLY', 'PRODUCTION'
    item_id UUID, -- ID do item específico
    name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10,2),
    
    -- Checklist
    loaded BOOLEAN DEFAULT false,
    loaded_at TIMESTAMP WITH TIME ZONE,
    delivered BOOLEAN DEFAULT false,
    delivered_at TIMESTAMP WITH TIME ZONE,
    returned BOOLEAN DEFAULT false,
    returned_at TIMESTAMP WITH TIME ZONE,
    
    condition_notes TEXT,
    
    metadata JSONB DEFAULT '{}'
);

-- Índices Logistics
CREATE INDEX idx_logistics_orders_event ON logistics_orders(event_id);
CREATE INDEX idx_logistics_orders_status ON logistics_orders(status);

-- =============================================================
-- DOMÍNIO: EXECUTION (Execução do Evento)
-- =============================================================

CREATE TABLE execution_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    event_id UUID NOT NULL REFERENCES events(id),
    event_date_id UUID NOT NULL REFERENCES event_dates(id),
    
    -- Estado da execução
    phase VARCHAR(50) NOT NULL CHECK (phase IN ('SETUP', 'PRE_SERVICE', 'SERVICE', 'POST_SERVICE', 'TEARDOWN', 'COMPLETE')),
    
    -- Responsáveis presentes
    manager_on_duty_id UUID REFERENCES users(id),
    chef_on_duty_id UUID REFERENCES users(id),
    
    -- Timeline real
    setup_started_at TIMESTAMP WITH TIME ZONE,
    setup_completed_at TIMESTAMP WITH TIME ZONE,
    service_started_at TIMESTAMP WITH TIME ZONE,
    service_ended_at TIMESTAMP WITH TIME ZONE,
    teardown_completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Métricas
    guest_count_actual INTEGER,
    guest_count_peak INTEGER,
    
    -- Clima (afeta eventos externos)
    weather_conditions JSONB,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE execution_checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_session_id UUID NOT NULL REFERENCES execution_sessions(id),
    
    -- Checklist
    checkpoint_name VARCHAR(255) NOT NULL,
    category VARCHAR(100), -- 'SETUP', 'SERVICE', 'SAFETY', 'CLEANING'
    
    -- Estado
    is_completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMP WITH TIME ZONE,
    completed_by UUID REFERENCES users(id),
    
    -- Problemas
    has_issues BOOLEAN DEFAULT false,
    issue_description TEXT,
    issue_severity VARCHAR(50) CHECK (issue_severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    
    notes TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE occurrences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    execution_session_id UUID NOT NULL REFERENCES execution_sessions(id),
    
    -- Classificação
    occurrence_type VARCHAR(100) NOT NULL, -- 'INCIDENT', 'NEAR_MISS', 'COMPLIMENT', 'QUALITY_ISSUE'
    severity VARCHAR(50) CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    
    -- Descrição
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Ação
    action_taken TEXT,
    action_required TEXT,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Status
    status VARCHAR(50) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED')),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE execution_photos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_session_id UUID NOT NULL REFERENCES execution_sessions(id),
    
    photo_type VARCHAR(100) NOT NULL, -- 'SETUP', 'DURING', 'FOOD', 'DECOR', 'ISSUE', 'TEARDOWN'
    photo_url TEXT NOT NULL,
    thumbnail_url TEXT,
    
    -- Contexto
    taken_by UUID REFERENCES users(id),
    taken_at TIMESTAMP WITH TIME ZONE,
    location_notes TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE execution_signatures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_session_id UUID NOT NULL REFERENCES execution_sessions(id),
    
    -- Quem assina
    signer_name VARCHAR(255) NOT NULL,
    signer_role VARCHAR(100), -- 'CLIENT', 'MANAGER', 'CHEF', 'VENUE_CONTACT'
    
    -- O que está sendo assinado
    signature_type VARCHAR(100) NOT NULL, -- 'SETUP_COMPLETE', 'SERVICE_COMPLETE', 'TEARDOWN_COMPLETE', 'FINAL_ACCEPTANCE'
    
    -- Dados
    signature_data TEXT, -- base64 da assinatura
    photo_proof_url TEXT, -- foto da assinatura no papel
    
    signed_at TIMESTAMP WITH TIME ZONE,
    
    notes TEXT,
    
    metadata JSONB DEFAULT '{}'
);

-- Índices Execution
CREATE INDEX idx_execution_sessions_event ON execution_sessions(event_id);
CREATE INDEX idx_execution_sessions_phase ON execution_sessions(phase);
CREATE INDEX idx_occurrences_session ON occurrences(execution_session_id);
CREATE INDEX idx_occurrences_type ON occurrences(occurrence_type);

-- =============================================================
-- DOMÍNIO: FINANCIAL (Preservado e estendido)
-- =============================================================

-- Financial Core já existe e funciona - APENAS adicionar FKs
-- para linkar com novo schema

ALTER TABLE accounts_payable ADD COLUMN IF NOT EXISTS
    purchase_order_id UUID REFERENCES purchase_orders(id);

ALTER TABLE accounts_payable ADD COLUMN IF NOT EXISTS
    event_id UUID REFERENCES events(id);

ALTER TABLE accounts_receivable ADD COLUMN IF NOT EXISTS
    contract_id UUID REFERENCES contracts(id);

ALTER TABLE accounts_receivable ADD COLUMN IF NOT EXISTS
    event_id UUID REFERENCES events(id);

-- Tabela nova: Event Cost Analysis
CREATE TABLE event_cost_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    event_id UUID NOT NULL UNIQUE REFERENCES events(id),
    
    -- Previsto (do contrato/OS)
    projected_revenue DECIMAL(15,2),
    projected_cost DECIMAL(15,2),
    projected_margin DECIMAL(5,2),
    
    -- Real (após execução)
    actual_revenue DECIMAL(15,2),
    actual_cost DECIMAL(15,2),
    actual_margin DECIMAL(5,2),
    
    -- Breakdown
    cost_by_category JSONB DEFAULT '{}', -- estrutura flexível
    cost_by_supplier JSONB DEFAULT '{}',
    
    -- Análise
    variance_amount DECIMAL(15,2),
    variance_percentage DECIMAL(5,2),
    analysis_notes TEXT,
    
    -- Reconciliação
    reconciled_at TIMESTAMP WITH TIME ZONE,
    reconciled_by UUID REFERENCES users(id),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================
-- DOMÍNIO: INSIGHTS / LEARNING
-- =============================================================

CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Contexto
    prediction_type VARCHAR(100) NOT NULL, -- 'guest_count', 'food_consumption', 'cost_per_head'
    event_type VARCHAR(100),
    
    -- Inputs
    input_features JSONB NOT NULL,
    
    -- Predição
    predicted_value DECIMAL(15,2),
    confidence DECIMAL(3,2), -- 0-1
    
    -- Validação
    actual_value DECIMAL(15,2),
    accuracy DECIMAL(15,2),
    
    -- Modelo
    model_version VARCHAR(50),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Contexto
    recommendation_type VARCHAR(100) NOT NULL, -- 'menu_optimization', 'staffing', 'cost_reduction'
    priority VARCHAR(20) CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')),
    
    -- Conteúdo
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Fonte
    based_on_event_ids UUID[] DEFAULT '{}',
    based_on_data JSONB DEFAULT '{}',
    
    -- Ação
    suggested_action TEXT,
    estimated_impact DECIMAL(15,2),
    
    -- Status
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'IMPLEMENTED')),
    
    implemented_at TIMESTAMP WITH TIME ZONE,
    result_notes TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================
-- EVENT STREAMING (Event Sourcing)
-- =============================================================

CREATE TABLE domain_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Identificação
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    
    -- Contexto
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Dados
    payload JSONB NOT NULL,
    
    -- Rastreamento
    correlation_id UUID,
    causation_id UUID REFERENCES domain_events(id),
    
    -- Metadata
    emitted_by UUID REFERENCES users(id),
    emitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Consumo
    processed_by UUID[], DEFAULT '{}',
    
    -- Índices
    CONSTRAINT idx_domain_events_aggregate UNIQUE (aggregate_type, aggregate_id, emitted_at)
);

CREATE INDEX idx_domain_events_type ON domain_events(event_type);
CREATE INDEX idx_domain_events_correlation ON domain_events(correlation_id);
CREATE INDEX idx_domain_events_tenant ON domain_events(tenant_id);

-- =============================================================
-- TRIGGERS E ATUALIZAÇÃO AUTOMÁTICA
-- =============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar trigger em todas as tabelas com updated_at
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN (
            'leads', 'proposals', 'contracts', 'clients', 'venues', 'events',
            'service_orders', 'production_orders', 'purchase_orders',
            'suppliers', 'products', 'recipes', 'inventory_batches',
            'production_batches', 'logistics_orders', 'execution_sessions',
            'occurrences', 'event_cost_analysis', 'recommendations'
        )
    LOOP
        EXECUTE format('CREATE TRIGGER update_%s_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()', t, t);
    END LOOP;
END $$;
```

---

## 6️⃣ STATE MACHINE RECOMENDADA

### 6.1 Implementação State Machine (TypeScript-ready)

```typescript
// =============================================================
// STATE MACHINE FRAMEWORK
// =============================================================

interface StateMachineConfig<S extends string, E extends string> {
  initial: S;
  states: Record<S, {
    on: Partial<Record<E, { target: S; action?: string; guard?: string }>>;
    entry?: string[];
    exit?: string[];
  }>;
}

interface StateTransition<S extends string, E extends string> {
  from: S;
  to: S;
  event: E;
  guard?: (context: any) => boolean;
  action?: (context: any, payload: any) => void;
}

// =============================================================
// STATE MACHINE: EVENT (Simplified)
// =============================================================

const EventStateMachine: StateMachineConfig<
  'PLANNED' | 'CONFIRMED' | 'PREPARING' | 'SETUP' | 'EXECUTING' | 'TEARDOWN' | 'COMPLETED' | 'CANCELLED',
  'CONFIRM' | 'CANCEL' | 'START_PREP' | 'START_SETUP' | 'CONFIRM_SETUP' | 'START_EXECUTION' | 'COMPLETE_EXECUTION' | 'START_TEARDOWN' | 'COMPLETE' | 'UNDO'
> = {
  initial: 'PLANNED',
  states: {
    PLANNED: {
      on: {
        CONFIRM: { target: 'CONFIRMED' },
        CANCEL: { target: 'CANCELLED', guard: 'not_within_48h' }
      }
    },
    CONFIRMED: {
      on: {
        START_PREP: { target: 'PREPARING' },
        CANCEL: { target: 'CANCELLED', action: 'log_cancellation_cost' }
      }
    },
    PREPARING: {
      entry: ['create_os', 'create_op'],
      on: {
        START_SETUP: { target: 'SETUP', guard: 'all_logistics_ready' }
      }
    },
    SETUP: {
      entry: ['create_execution_session'],
      on: {
        CONFIRM_SETUP: { target: 'EXECUTING', guard: 'setup_checklist_complete' }
      }
    },
    EXECUTING: {
      on: {
        COMPLETE_EXECUTION: { target: 'TEARDOWN', action: 'calculate_actual_consumption' }
      }
    },
    TEARDOWN: {
      on: {
        COMPLETE: { target: 'COMPLETED', action: 'trigger_reconciliation' }
      }
    },
    COMPLETED: {
      entry: ['generate_cost_analysis', 'update_event_metrics'],
      type: 'final'
    },
    CANCELLED: {
      entry: ['cancel_reservations', 'cancel_orders'],
      type: 'final'
    }
  }
};

// =============================================================
// STATE MACHINE: SERVICE_ORDER
// =============================================================

const ServiceOrderStateMachine: StateMachineConfig<
  'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'IN_PRODUCTION' | 'READY' | 'DELIVERED' | 'CANCELLED',
  'SUBMIT' | 'APPROVE' | 'REJECT' | 'START_PROD' | 'COMPLETE_PROD' | 'DELIVER' | 'CANCEL' | 'REOPEN'
> = {
  initial: 'DRAFT',
  states: {
    DRAFT: {
      on: {
        SUBMIT: { target: 'PENDING_APPROVAL', guard: 'has_items' }
      }
    },
    PENDING_APPROVAL: {
      on: {
        APPROVE: { target: 'APPROVED', action: 'emit_to_production' },
        REJECT: { target: 'DRAFT', action: 'notify_revision' }
      }
    },
    APPROVED: {
      on: {
        START_PROD: { target: 'IN_PRODUCTION' }
      }
    },
    IN_PRODUCTION: {
      on: {
        COMPLETE_PROD: { target: 'READY', action: 'notify_logistics' }
      }
    },
    READY: {
      on: {
        DELIVER: { target: 'DELIVERED', action: 'update_event_status' }
      }
    },
    DELIVERED: { type: 'final' },
    CANCELLED: {
      entry: ['release_reservations'],
      type: 'final'
    }
  }
};

// =============================================================
// STATE MACHINE: INVENTORY_BATCH
// =============================================================

const InventoryBatchStateMachine: StateMachineConfig<
  'AVAILABLE' | 'RESERVED' | 'COMMITTED' | 'IN_USE' | 'DEPLETED' | 'EXPIRED' | 'DAMAGED' | 'RETURNED',
  'RESERVE' | 'COMMIT' | 'CONSUME' | 'RELEASE' | 'DAMAGE' | 'EXPIRE' | 'RETURN'
> = {
  initial: 'AVAILABLE',
  states: {
    AVAILABLE: {
      on: {
        RESERVE: { target: 'RESERVED', guard: 'quantity_available' },
        EXPIRE: { target: 'EXPIRED' }
      }
    },
    RESERVED: {
      on: {
        COMMIT: { target: 'COMMITTED' },
        RELEASE: { target: 'AVAILABLE' }
      }
    },
    COMMITTED: {
      on: {
        CONSUME: { target: 'IN_USE', action: 'create_consumption_record' },
        RELEASE: { target: 'AVAILABLE' }
      }
    },
    IN_USE: {
      on: {
        RETURN: { target: 'RETURNED', action: 'calculate_waste' },
        DAMAGE: { target: 'DAMAGED', action: 'log_loss' }
      }
    },
    RETURNED: {
      entry: ['update_stock', 'calculate_utilization'],
      on: {
        EXPIRE: { target: 'EXPIRED' }
      }
    },
    DEPLETED: { type: 'final' },
    EXPIRED: { type: 'final' },
    DAMAGED: { type: 'final' }
  }
};
```

---

## 7️⃣ BACKBONE DE EVENTOS RECOMENDADO

### 7.1 Taxonomia de Eventos

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     ORKESTRA.AI EVENT BACKBONE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    EVENT CATEGORIES                              │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                 │   │
│  │  🎯 CRM Events           →  lead.*, proposal.*, contract.*    │   │
│  │  📅 Event Engine Events  →  event.*, venue.*, client.*          │   │
│  │  📋 Order Events         →  service_order.*, production_order.*│   │
│  │  🛒 Procurement Events   →  purchase.*, supplier.*             │   │
│  │  📦 Inventory Events     →  inventory.*, stock.*, batch.*        │   │
│  │  🍽️ Production Events    →  recipe.*, production.*             │   │
│  │  🚚 Logistics Events     →  logistics.*, vehicle.*, crew.*       │   │
│  │  ✅ Execution Events     →  execution.*, occurrence.*            │   │
│  │  💰 Financial Events   →  invoice.*, payment.*, cost.*         │   │
│  │  🔍 Insight Events     →  prediction.*, recommendation.*         │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    EVENT LIFECYCLE                             │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                 │   │
│  │  [CREATED] → [UPDATED]* → [COMPLETED|CANCELLED]                │   │
│  │                                                                 │   │
│  │  Todo evento tem lifecycle padrão.                             │   │
│  │  * = pode ter múltiplos UPDATED com mudanças de estado         │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    EVENT PRIORITIES                            │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                 │   │
│  │  CRITICAL  →  Event state changes, Financial transactions     │   │
│  │  HIGH      →  Order state changes, Inventory movements          │   │
│  │  NORMAL    →  Logistics updates, Execution checkpoints            │   │
│  │  LOW       →  Analytics, Predictions, Insights                │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Event Schema (JSON Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://orkestra.ai/schemas/domain-event",
  "title": "Domain Event",
  "type": "object",
  "required": ["id", "event_type", "aggregate_type", "aggregate_id", "tenant_id", "payload", "emitted_at"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "ID único do evento"
    },
    "event_type": {
      "type": "string",
      "pattern": "^[a-z_]+\\.(created|updated|deleted|completed|cancelled|approved|rejected|started|ended|failed)$",
      "description": "Tipo do evento seguindo convenção domain.action"
    },
    "aggregate_type": {
      "type": "string",
      "enum": [
        "lead", "proposal", "contract", "client", "venue", "event",
        "service_order", "production_order", "purchase_order",
        "supplier", "product", "inventory_batch", "stock_movement",
        "recipe", "production_batch", "logistics_order", "execution_session",
        "occurrence", "invoice", "payment", "prediction", "recommendation"
      ]
    },
    "aggregate_id": {
      "type": "string",
      "format": "uuid"
    },
    "tenant_id": {
      "type": "string",
      "format": "uuid"
    },
    "payload": {
      "type": "object",
      "description": "Dados específicos do evento"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "correlation_id": {
          "type": "string",
          "format": "uuid",
          "description": "ID que correlaciona eventos de uma mesma transação"
        },
        "causation_id": {
          "type": "string",
          "format": "uuid",
          "description": "ID do evento que causou este"
        },
        "emitted_by": {
          "type": "string",
          "format": "uuid",
          "description": "ID do usuário/agente que emitiu"
        },
        "source": {
          "type": "string",
          "description": "Origem: 'user', 'system', 'agent', 'integration'"
        },
        "version": {
          "type": "integer",
          "description": "Versão do schema"
        }
      }
    },
    "emitted_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### 7.3 Eventos Primários por Domínio

#### CRM Events
```yaml
crm.lead.created:
  payload:
    lead_id: UUID
    company_name: string
    contact_name: string
    source: string
    score: integer
    
crm.lead.qualified:
  payload:
    lead_id: UUID
    qualification_data: object
    score: integer
    
crm.proposal.sent:
  payload:
    proposal_id: UUID
    lead_id: UUID
    total_amount: decimal
    valid_until: date
    sent_to: string
    
crm.contract.signed:
  payload:
    contract_id: UUID
    proposal_id: UUID
    total_value: decimal
    signed_at: datetime
    event_id: UUID  # Evento é criado automático
```

#### Event Engine Events
```yaml
event.created:
  payload:
    event_id: UUID
    contract_id: UUID
    client_id: UUID
    event_name: string
    event_type: string
    event_date: date
    expected_guests: integer
    
event.confirmed:
  payload:
    event_id: UUID
    confirmed_at: datetime
    confirmed_by: UUID
    
event.cancelled:
  payload:
    event_id: UUID
    cancelled_at: datetime
    reason: string
    cancellation_cost: decimal
    
event.checklist.completed:
  payload:
    event_id: UUID
    phase: string
    completed_items: array
```

#### Order Events
```yaml
order.service_order.approved:
  payload:
    so_id: UUID
    event_id: UUID
    approved_by: UUID
    # Dispara: criação automática da OP
    
order.production_order.scheduled:
  payload:
    po_id: UUID
    so_id: UUID  # source
    production_date: date
    responsible_chef: UUID
    
order.production_order.completed:
  payload:
    po_id: UUID
    produced_items: array
    actual_cost: decimal
    # Dispara: notificação logística
```

#### Inventory Events
```yaml
inventory.batch.received:
  payload:
    batch_id: UUID
    product_id: UUID
    quantity: decimal
    unit_cost: decimal
    expiry_date: date
    received_from_po: UUID
    
inventory.batch.reserved:
  payload:
    batch_id: UUID
    event_id: UUID
    quantity_reserved: decimal
    required_by: datetime
    
inventory.batch.consumed:
  payload:
    batch_id: UUID
    event_id: UUID
    quantity_consumed: decimal
    consumed_in_production: UUID
    actual_cost: decimal  # custo real para COGS
```

#### Financial Events (Integração c/ Core existente)
```yaml
financial.payment.received:
  payload:
    receivable_id: UUID
    amount: decimal
    payment_method: string
    received_at: datetime
    # Atualiza event cost analysis
    
financial.invoice.paid:
  payload:
    payable_id: UUID
    purchase_order_id: UUID
    amount: decimal
    # Atualiza OP cost tracking
```

### 7.4 Consumers Pattern

```typescript
// Event Consumer Interface
interface EventConsumer {
  eventTypes: string[];
  handle(event: DomainEvent): Promise<void>;
}

// Exemplo: Consumer que cria PO quando SO é aprovada
class SOApprovedCreatesPOConsumer implements EventConsumer {
  eventTypes = ['order.service_order.approved'];
  
  async handle(event: DomainEvent): Promise<void> {
    const { so_id, event_id } = event.payload;
    
    // Busca OS com items
    const so = await serviceOrderRepo.findById(so_id);
    
    // Cria PO
    const po = await productionOrderService.create({
      event_id,
      source_so_ids: [so_id],
      items: so.items.map(item => ({
        source_so_item_id: item.id,
        planned_quantity: item.quantity,
        recipe_id: item.produces_item_id
      }))
    });
    
    // Emite evento
    await eventBus.emit({
      event_type: 'order.production_order.created',
      aggregate_type: 'production_order',
      aggregate_id: po.id,
      payload: { po_id: po.id, source_so_id: so_id },
      causation_id: event.id,
      correlation_id: event.metadata.correlation_id
    });
  }
}
```

---

## 8️⃣ PLANO DE EXECUÇÃO EM FASES

### 8.1 Resumo Visual

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         ROADMAP ORKESTRA.AI                                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐     │
│  │ FASE 1: BLUEPRINT (NOW - Semanas 1-2)                             │     │
│  │ ════════════════════════════════════                             │     │
│  │ ✓ Blueprint arquitetural finalizado                               │     │
│  │ ☐ Validar com stakeholders                                       │     │
│  │ ☐ Aprovar schema e state machines                                │     │
│  │ ☐ Definir prioridades de implementação                         │     │
│  └──────────────────────────────────────────────────────────────────┘     │
│                              │                                             │
│                              ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────┐     │
│  │ FASE 2: REFATORAÇÃO SELETIVA (Semanas 3-8)                        │     │
│  │ ═════════════════════════════════════════                        │     │
│  │ ☐ Módulo CRM (Lead → Proposal → Contract)                       │     │
│  │ ☐ Extensão Event Engine (enriquecer entity existente)            │     │
│  │ ☐ Módulo Order System (OS + OP)                                │     │
│  │ ☐ Event Backbone (event sourcing layer)                        │     │
│  │ ☐ NO TOCAR FINANCIAL CORE                                      │     │
│  └──────────────────────────────────────────────────────────────────┘     │
│                              │                                             │
│                              ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────┐     │
│  │ FASE 3: MIGRAÇÃO FINAL (Semanas 9-10)                           │     │
│  │ ═══════════════════════════════════                              │     │
│  │ ☐ Criar schema novo em ambiente isolado                        │     │
│  │ ☐ Migrar dados de domínios novos (não existiam)                │     │
│  │ ☐ Linkar IDs com Financial Core existente                      │     │
│  │ ☐ Validar integridade referencial                              │     │
│  │ ☐ Testes end-to-end                                            │     │
│  └──────────────────────────────────────────────────────────────────┘     │
│                              │                                             │
│                              ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────┐     │
│  │ FASE 4: IMPLANTAÇÃO OPERACIONAL (Semana 11+)                      │     │
│  │ ═════════════════════════════════════════                       │     │
│  │ ☐ Deploy em produção                                            │     │
│  │ ☐ Treinamento da equipe                                        │     │
│  │ ☐ Go-live (eventos novos no novo sistema)                      │     │
│  │ ☐ Eventos em andamento: modo híbrido                           │     │
│  │ ☐ Eventos futuros: 100% novo sistema                           │     │
│  │ ☐ Monitoramento e ajustes                                      │     │
│  └──────────────────────────────────────────────────────────────────┘     │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Detalhamento por Fase

#### FASE 1: BLUEPRINT (2 semanas)

**Objetivo:** Finalizar, validar e aprovar o blueprint.

**Deliverables:**
- [ ] Validar com operação real (chefs, logística, comercial)
- [ ] Ajustar state machines baseado em feedback
- [ ] Criar protótipos de fluxo (diagramas visuais)
- [ ] Definir critérios de aceite por módulo

**Riscos:**
- Stakeholders pedem features fora do scope → Defender MVP
- Análise paralisia → Timebox de 2 semanas é firme

**Sucesso:** Blueprint assinado por todos os stakeholders.

---

#### FASE 2: REFATORAÇÃO SELETIVA (6 semanas)

**Semana 3-4: CRM Module**
```
Entidades: Lead, Proposal, Contract
Prioridade: ALTA
Dependências: Nenhuma

Tasks:
□ Create entity Lead + state machine
□ Create entity Proposal + versioning
□ Create entity Contract + digital signature placeholder
□ Create API endpoints
□ Create basic UI forms
□ Unit tests
□ Integration tests
```

**Semana 5: Event Engine Extension**
```
Entidades: Enriquecer Event, add Client, add Venue
Prioridade: ALTA
Dependências: Contract

Tasks:
□ Refactor Event: add contract FK, status machine
□ Create Client entity
□ Create Venue entity
□ Link Event dates (multi-day support)
□ Migration script para eventos existentes
□ Update existing queries
```

**Semana 6-7: Order System (OS + OP)**
```
Entidades: ServiceOrder, ProductionOrder
Prioridade: CRÍTICA
Dependências: Event

Tasks:
□ Create ServiceOrder entity + state machine
□ Create ProductionOrder entity + state machine
□ SO-ProductionOrder mapping logic
□ Event consumer: SOApproved → creates OP
□ Event consumer: ContractSigned → creates Event → creates SO
□ Cost tracking integration (links to Financial Core)
```

**Semana 8: Event Backbone**
```
Prioridade: ALTA
Dependências: Todas as anteriores

Tasks:
□ Implement event bus (Redis/RabbitMQ/PostgreSQL pub-sub)
□ Create domain_events table
□ Implement audit trail automatic
□ Create event consumers framework
□ Implement logging e dead letter queue
```

**NO PHASE 2:**
- ❌ NÃO implementar Inventory, Production, Logistics, Execution ainda
- ❌ NÃO modificar Financial Core
- ❌ NÃO fazer migração de dados

---

#### FASE 3: MIGRAÇÃO FINAL (2 semanas)

**Preparação:**
```
□ Criar ambiente de staging idêntico à produção
□ Rodar schema SQL do Blueprint
□ Criar scripts de migração idempotentes
```

**Migração de Dados:**
```
□ Leads atuais (do ClickUp/manual) → table leads
□ Propostas em aberto → table proposals
□ Contratos sem evento vinculado → table contracts
□ Eventos futuros → table events (enriquecido)
□ OS atuais (se existirem) → table service_orders
□ Mapear FKs corretamente
```

**Validação:**
```
□ Verificar integridade referencial
□ Testar end-to-end com dados reais (anonymized)
□ Performance testing
□ Rollback plan documentado
```

---

#### FASE 4: IMPLANTAÇÃO OPERACIONAL (Semana 11+)

**Go-Live Strategy:**
```
Semana 11: Deploy | Novos leads no novo sistema
Semana 12-13: Eventos existentes → modo híbrido
               (continuam nos sistemas antigos)
Semana 14+: Eventos novos → 100% novo sistema
Mês 3+: Eventos em andamento → migração gradual
Mês 6+: Descontinuar sistemas antigos
```

**Treinamento:**
- Equipe comercial: CRM module
- Equipe operacional: Event + Order modules
- Financeiro: Não muda (ainda usa ClickUp/financeiro atual)

**Monitoramento:**
- Dashboard de adoção
- Erros em tempo real
- Time de suporte dedicado (2 semanas)

---

### 8.3 Critérios de Sucesso por Fase

| Fase | Critério de Sucesso | Métrica |
|------|---------------------|---------|
| 1 | Blueprint aprovado | 100% stakeholders signed off |
| 2 | Módulos testados | >90% code coverage, zero critical bugs |
| 3 | Dados migrados | Zero data loss, referential integrity OK |
| 4 | Go-live | Novos eventos usando novo sistema |

---

## 🎯 RECOMENDAÇÃO EXECUTIVA

### O QUE PRESERVAR 🟢

| Componente | Por quê |
|------------|---------|
| Financial Core | Funcionando, testado, dados reais funcionando |
| Multi-tenant | Já funciona para 2 empresas |
| JSON Schema pattern | Consistente, extensível |
| Classification engine | Categorização automática funcionando |
| Alert system | CAIXA_NEGATIVO, etc. detectando corretamente |
| Intercompany flow | R$ 600k+ transacionados sem erro |

### O QUE REFATORAR 🟡

| Componente | Prioridade | Esforço |
|------------|-----------|---------|
| Adicionar CRM Module | Alta | 2 semanas |
| Enriquecer Event entity | Alta | 1 semana |
| Criar OS/OP entities | Crítica | 2 semanas |
| Implementar State Machines | Alta | 1 semana |
| Criar Event Backbone | Alta | 1 semana |

### O QUE CORTAR 🔴

| Componente | Razão |
|------------|-------|
| Inventory completo | Fase 4 - não bloquear go-live |
| Production completo | Fase 4 - não bloquear go-live |
| Logistics completo | Fase 4 - não bloquear go-live |
| Execution real-time | Fase 4 - não bloquear go-live |
| Predictions ML | Phase 5 - insight layer |
| Complex RBAC | Simplificar para roles básicos |

### O QUE CONSTRUIR PRIMEIRO 🚀

**MVP (Semanas 3-6):**
1. **CRM Module** → Lead → Proposal → Contract
2. **Event + Order** → Contract cria Event → cria OS → aprova → cria OP
3. **Integration c/ Financial** → OP gera Purchase Request → atualiza cashflow

**Isso permite:**
- Fechar vendas no novo sistema
- Planejar eventos com rastreabilidade
- Manter controle financeiro funcionando

---

## 📋 PRÓXIMAS AÇÕES IMEDIATAS

1. **HOJE:** Validar este blueprint com stakeholders
2. **Amanhã:** Priorizar módulos (ordem de implementação)
3. **Esta semana:** Criar protótipos de UI/UX para CRM
4. **Semana que vem:** Iniciar desenvolvimento Fase 2

---

**Assinado:** Chief System Architect  
**Data:** 2026-04-15  
**Status:** BLUEPRINT COMPLETO - AGUARDANDO APROVAÇÃO

🎛️ **ORKESTRA.AI - Architecture Blueprint v1.0**
