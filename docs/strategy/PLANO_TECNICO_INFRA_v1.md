# PLANO TÉCNICO INFRA v1 — Orkestra Finance Brain

**Versão:** 1.0  
**Data:** 2026-04-08  
**Autor:** Orkestra Finance Brain  
**Status:** PRODUÇÃO

---

## 📋 SUMÁRIO EXECUTIVO

Plano técnico completo para implementação de infraestrutura de logs, auditoria, RBAC e parâmetros do sistema Orkestra Finance Brain.

| Módulo | Complexidade | Estado |
|--------|-------------|--------|
| audit_log | Alto | Especificado |
| decision_log | Alto | Especificado |
| agent_action_log | Médio | Especificado |
| RBAC | Alto | Especificado |
| system_parameters | Médio | Especificado |

---

## 🏗️ ARQUITETURA DE DADOS

### Diagrama de Entidades

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   audit_log     │     │  decision_log   │     │ agent_action_log│
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (UUID PK)    │     │ id (UUID PK)    │     │ id (UUID PK)    │
│ tenant_id (FK)  │◄────┤ tenant_id (FK)  │◄────┤ tenant_id (FK)  │
│ actor_id        │     │ decision_id     │     │ session_id (FK) │
│ action_type     │     │ model_name      │     │ agent_id        │
│ resource_type   │     │ input_context   │     │ tool_name       │
│ resource_id     │     │ output_decision │     │ tool_input      │
│ payload_before  │     │ confidence_score│     │ tool_output     │
│ payload_after   │     │ reasoning_chain │     │ latency_ms      │
│ checksum_sha256 │     │ metadata        │     │ cost_usd        │
│ created_at      │     │ created_at      │     │ created_at      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │         tenant (multi-tenant)         │
              └───────────────────────────────────────┘
```

### RBAC Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ rbac_roles  │◄────┤rbac_user_rol│────►│ rbac_users  │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ id (UUID)   │     │ id (UUID)   │     │ id (UUID)   │
│ tenant_id   │     │ tenant_id   │     │ tenant_id   │
│ name        │     │ user_id(FK) │     │ email       │
│ permissions │◄────┤ role_id(FK) │     │ password_ash│
│ hierarchy   │     │ cost_center │     │ mfa_enabled │
│ inherits    │     │ valid_from  │     │ active      │
└─────────────┘     │ valid_until │     └─────────────┘
                    └─────────────┘
                           │
                    ┌─────────────┐
                    │rbac_access_l│
                    ├─────────────┤
                    │ id (UUID)   │
                    │ user_id(FK) │
                    │ action      │
                    │ resource    │
                    │ permitted   │
                    │ timestamp   │
                    └─────────────┘
```

---

## 📊 ESPECIFICAÇÃO DE TABELAS

### 1. AUDIT_LOG

**Propósito:** Registro imutável de todas as alterações no sistema.

```json
{
  "table": "audit_log",
  "partitioning": "RANGE (created_at) MONTHLY",
  "immutable": true,
  "retention": "7 years",
  "fields": [
    {"name": "id", "type": "UUID", "default": "gen_random_uuid()", "primary": true},
    {"name": "tenant_id", "type": "UUID", "not_null": true, "indexed": true},
    {"name": "cost_center_id", "type": "UUID", "nullable": true, "indexed": true},
    {"name": "actor_id", "type": "UUID", "not_null": true, "indexed": true},
    {"name": "actor_type", "type": "ENUM", "values": ["user", "system", "api", "agent"], "not_null": true},
    {"name": "action_type", "type": "ENUM", "values": ["CREATE", "UPDATE", "DELETE", "EXPORT", "IMPORT", "LOGIN", "LOGOUT", "APPROVE", "REJECT"], "not_null": true},
    {"name": "resource_type", "type": "TEXT", "not_null": true, "indexed": true},
    {"name": "resource_id", "type": "TEXT", "not_null": true, "indexed": true},
    {"name": "payload_before", "type": "JSONB", "nullable": true},
    {"name": "payload_after", "type": "JSONB", "nullable": true},
    {"name": "diff_summary", "type": "TEXT", "nullable": true},
    {"name": "ip_address", "type": "INET", "nullable": true},
    {"name": "user_agent", "type": "TEXT", "nullable": true},
    {"name": "session_id", "type": "UUID", "nullable": true, "indexed": true},
    {"name": "checksum_sha256", "type": "TEXT", "not_null": true, "length": 64},
    {"name": "previous_checksum", "type": "TEXT", "nullable": true, "indexed": true},
    {"name": "chain_hash", "type": "TEXT", "not_null": true},
    {"name": "created_at", "type": "TIMESTAMPTZ", "not_null": true, "indexed": true, "partition_key": true}
  ],
  "indexes": [
    "idx_audit_tenant_created ON (tenant_id, created_at)",
    "idx_audit_actor_action ON (actor_id, action_type)",
    "idx_audit_resource ON (resource_type, resource_id, created_at)",
    "idx_audit_session ON (session_id, created_at)",
    "GIN idx_audit_payload_before ON (payload_before)",
    "GIN idx_audit_payload_after ON (payload_after)"
  ],
  "constraints": [
    "foreign_key (tenant_id) references tenants(id)",
    "foreign_key (actor_id) references rbac_users(id)",
    "check (checksum_sha256 ~ '^[a-f0-9]{64}$')"
  ],
  "triggers": [
    "trg_audit_immutable: PREVENT UPDATE/DELETE",
    "trg_audit_checksum: AUTO GENERATE SHA256",
    "trg_audit_partition: AUTO CREATE MONTHLY PARTITIONS"
  ]
}
```

**Endpoints:**
- `GET /api/v1/audit` — Listar logs com filtros
- `GET /api/v1/audit/:id` — Obter log específico
- `GET /api/v1/audit/verify/:id` — Verificar integridade (checksum)
- `POST /api/v1/audit/search` — Busca avançada (JSONB)

---

### 2. DECISION_LOG

**Propósito:** Rastreabilidade de decisões da IA com explainability.

```json
{
  "table": "decision_log",
  "partitioning": "RANGE (created_at) MONTHLY",
  "immutable": true,
  "retention": "3 years",
  "fields": [
    {"name": "id", "type": "UUID", "default": "gen_random_uuid()", "primary": true},
    {"name": "tenant_id", "type": "UUID", "not_null": true, "indexed": true},
    {"name": "cost_center_id", "type": "UUID", "nullable": true, "indexed": true},
    {"name": "decision_id", "type": "TEXT", "not_null": true, "unique": true},
    {"name": "model_name", "type": "TEXT", "not_null": true, "indexed": true},
    {"name": "model_version", "type": "TEXT", "not_null": true},
    {"name": "prompt_tokens", "type": "INTEGER", "not_null": true},
    {"name": "completion_tokens", "type": "INTEGER", "not_null": true},
    {"name": "total_tokens", "type": "INTEGER", "not_null": true, "indexed": true},
    {"name": "input_context", "type": "JSONB", "not_null": true, "compressed": true},
    {"name": "output_decision", "type": "JSONB", "not_null": true, "compressed": true},
    {"name": "reasoning_chain", "type": "JSONB", "not_null": true, "compressed": true},
    {"name": "confidence_score", "type": "DECIMAL(5,4)", "not_null": true, "check": "0 <= confidence <= 1"},
    {"name": "confidence_breakdown", "type": "JSONB", "nullable": true},
    {"name": "alternative_decisions", "type": "JSONB", "nullable": true},
    {"name": "latency_ms", "type": "INTEGER", "not_null": true, "indexed": true},
    {"name": "cost_usd", "type": "DECIMAL(10,6)", "not_null": true},
    {"name": "metadata", "type": "JSONB", "nullable": true},
    {"name": "session_id", "type": "UUID", "nullable": true, "indexed": true},
    {"name": "agent_id", "type": "UUID", "nullable": true, "indexed": true},
    {"name": "review_status", "type": "ENUM", "values": ["pending", "approved", "rejected", "flagged"], "default": "pending"},
    {"name": "reviewed_by", "type": "UUID", "nullable": true},
    {"name": "reviewed_at", "type": "TIMESTAMPTZ", "nullable": true},
    {"name": "created_at", "type": "TIMESTAMPTZ", "not_null": true, "indexed": true, "partition_key": true}
  ],
  "indexes": [
    "idx_decisions_tenant_model ON (tenant_id, model_name, created_at)",
    "idx_decisions_confidence ON (confidence_score, created_at) WHERE confidence_score < 0.7",
    "idx_decisions_review_status ON (review_status, created_at)",
    "GIN idx_decisions_input ON (input_context)",
    "GIN idx_decisions_output ON (output_decision)"
  ],
  "constraints": [
    "foreign_key (tenant_id) references tenants(id)",
    "foreign_key (agent_id) references agent_sessions(id)",
    "foreign_key (reviewed_by) references rbac_users(id)"
  ]
}
```

**Endpoints:**
- `GET /api/v1/decisions` — Listar decisões
- `GET /api/v1/decisions/:id` — Detalhe completo com reasoning
- `POST /api/v1/decisions/:id/review` — Revisar decisão
- `GET /api/v1/decisions/stats` — Métricas de confiança

---

### 3. AGENT_ACTION_LOG

**Propósito:** Rastrear tool calls e ações de agentes.

```json
{
  "table": "agent_action_log",
  "partitioning": "RANGE (created_at) MONTHLY",
  "immutable": true,
  "retention": "1 year",
  "fields": [
    {"name": "id", "type": "UUID", "default": "gen_random_uuid()", "primary": true},
    {"name": "tenant_id", "type": "UUID", "not_null": true, "indexed": true},
    {"name": "cost_center_id", "type": "UUID", "nullable": true},
    {"name": "session_id", "type": "UUID", "not_null": true, "indexed": true},
    {"name": "turn_number", "type": "INTEGER", "not_null": true},
    {"name": "agent_id", "type": "UUID", "nullable": true, "indexed": true},
    {"name": "tool_name", "type": "TEXT", "not_null": true, "indexed": true},
    {"name": "tool_input", "type": "JSONB", "not_null": true, "encrypted": true},
    {"name": "tool_output", "type": "JSONB", "nullable": true, "encrypted": true},
    {"name": "tool_error", "type": "JSONB", "nullable": true, "encrypted": true},
    {"name": "status", "type": "ENUM", "values": ["started", "completed", "failed", "timeout", "cancelled"], "not_null": true},
    {"name": "latency_ms", "type": "INTEGER", "nullable": true, "indexed": true},
    {"name": "cost_usd", "type": "DECIMAL(10,6)", "nullable": true},
    {"name": "tokens_in", "type": "INTEGER", "nullable": true},
    {"name": "tokens_out", "type": "INTEGER", "nullable": true},
    {"name": "risk_level", "type": "ENUM", "values": ["none", "low", "medium", "high", "critical"], "default": "none"},
    {"name": "approval_required", "type": "BOOLEAN", "default": false},
    {"name": "approved_by", "type": "UUID", "nullable": true},
    {"name": "approved_at", "type": "TIMESTAMPTZ", "nullable": true},
    {"name": "created_at", "type": "TIMESTAMPTZ", "not_null": true, "indexed": true, "partition_key": true}
  ],
  "indexes": [
    "idx_actions_session_turn ON (session_id, turn_number)",
    "idx_actions_tool_status ON (tool_name, status, created_at)",
    "idx_actions_risk_level ON (risk_level, created_at) WHERE risk_level IN ('high', 'critical')",
    "idx_actions_cost ON (cost_center_id, cost_usd) WHERE cost_usd > 0"
  ],
  "constraints": [
    "foreign_key (tenant_id) references tenants(id)",
    "foreign_key (session_id) references agent_sessions(id)",
    "check (turn_number > 0)"
  ]
}
```

**Endpoints:**
- `GET /api/v1/agents/actions` — Listar ações
- `GET /api/v1/agents/sessions/:id/actions` — Ações por sessão
- `POST /api/v1/agents/actions/:id/approve` — Aprovar ação crítica

---

### 4. RBAC (5 tabelas)

#### 4.1 rbac_roles

```json
{
  "table": "rbac_roles",
  "fields": [
    {"name": "id", "type": "UUID", "primary": true},
    {"name": "tenant_id", "type": "UUID", "not_null": true, "indexed": true, "unique_with": ["name"]},
    {"name": "name", "type": "TEXT", "not_null": true},
    {"name": "description", "type": "TEXT"},
    {"name": "permissions", "type": "JSONB", "not_null": true, "default": "[]"},
    {"name": "parent_role_id", "type": "UUID", "nullable": true, "indexed": true},
    {"name": "hierarchy_level", "type": "INTEGER", "not_null": true, "default": 0},
    {"name": "is_system", "type": "BOOLEAN", "default": false},
    {"name": "created_at", "type": "TIMESTAMPTZ", "default": "NOW()"},
    {"name": "updated_at", "type": "TIMESTAMPTZ", "default": "NOW()"}
  ],
  "indexes": [
    "idx_roles_tenant ON (tenant_id, hierarchy_level)",
    "idx_roles_parent ON (parent_role_id)"
  ],
  "constraints": [
    "foreign_key (parent_role_id) references rbac_roles(id)",
    "no_cycles CHECK hierarchy"
  ]
}
```

#### 4.2 rbac_users

```json
{
  "table": "rbac_users",
  "fields": [
    {"name": "id", "type": "UUID", "primary": true},
    {"name": "tenant_id", "type": "UUID", "not_null": true, "indexed": true},
    {"name": "email", "type": "TEXT", "not_null": true, "unique": true},
    {"name": "password_hash", "type": "TEXT", "not_null": true},
    {"name": "first_name", "type": "TEXT"},
    {"name": "last_name", "type": "TEXT"},
    {"name": "phone", "type": "TEXT"},
    {"name": "mfa_enabled", "type": "BOOLEAN", "default": false},
    {"name": "mfa_secret", "type": "TEXT", "encrypted": true},
    {"name": "session_config", "type": "JSONB", "default": "{ 'ttl_minutes': 60 }"},
    {"name": "last_login_at", "type": "TIMESTAMPTZ"},
    {"name": "failed_logins", "type": "INTEGER", "default": 0},
    {"name": "locked_until", "type": "TIMESTAMPTZ"},
    {"name": "active", "type": "BOOLEAN", "default": true},
    {"name": "created_at", "type": "TIMESTAMPTZ", "default": "NOW()"},
    {"name": "updated_at", "type": "TIMESTAMPTZ", "default": "NOW()"}
  ],
  "indexes": [
    "idx_users_email ON (email)",
    "idx_users_tenant_active ON (tenant_id, active)"
  ]
}
```

#### 4.3 rbac_user_roles

```json
{
  "table": "rbac_user_roles",
  "fields": [
    {"name": "id", "type": "UUID", "primary": true},
    {"name": "tenant_id", "type": "UUID", "not_null": true},
    {"name": "user_id", "type": "UUID", "not_null": true, "indexed": true},
    {"name": "role_id", "type": "UUID", "not_null": true, "indexed": true},
    {"name": "cost_center_id", "type": "UUID", "nullable": true},
    {"name": "valid_from", "type": "TIMESTAMPTZ", "not_null": true, "default": "NOW()"},
    {"name": "valid_until", "type": "TIMESTAMPTZ"},
    {"name": "granted_by", "type": "UUID", "not_null": true},
    {"name": "created_at", "type": "TIMESTAMPTZ", "default": "NOW()"}
  ],
  "indexes": [
    "idx_user_roles_user ON (user_id, valid_from, valid_until)",
    "idx_user_roles_active ON (user_id) WHERE valid_until IS NULL"
  ],
  "constraints": [
    "unique (user_id, role_id, cost_center_id, valid_from)"
  ]
}
```

#### 4.4 rbac_permissions (tabela de referência)

```json
{
  "table": "rbac_permissions",
  "fields": [
    {"name": "id", "type": "UUID", "primary": true},
    {"name": "code", "type": "TEXT", "not_null": true, "unique": true},
    {"name": "name", "type": "TEXT", "not_null": true},
    {"name": "description", "type": "TEXT"},
    {"name": "resource", "type": "TEXT", "not_null": true},
    {"name": "action", "type": "TEXT", "not_null": true},
    {"name": "conditions", "type": "JSONB"},
    {"name": "created_at", "type": "TIMESTAMPTZ", "default": "NOW()"}
  ],
  "seed": [
    {"code": "event.read", "name": "Ver Eventos", "resource": "event", "action": "read"},
    {"code": "event.write", "name": "Editar Eventos", "resource": "event", "action": "write"},
    {"code": "event.delete", "name": "Excluir Eventos", "resource": "event", "action": "delete"},
    {"code": "financial.read", "name": "Ver Financeiro", "resource": "financial", "action": "read"},
    {"code": "financial.write", "name": "Editar Financeiro", "resource": "financial", "action": "write"},
    {"code": "pricing.calculate", "name": "Calcular Preços", "resource": "pricing", "action": "execute"},
    {"code": "agent.run", "name": "Executar Agentes", "resource": "agent", "action": "execute"},
    {"code": "audit.read", "name": "Ver Auditoria", "resource": "audit", "action": "read"},
    {"code": "admin.full", "name": "Administração Completa", "resource": "*", "action": "*"}
  ]
}
```

#### 4.5 rbac_access_log

```json
{
  "table": "rbac_access_log",
  "partitioning": "RANGE (created_at) MONTHLY",
  "retention": "2 years",
  "fields": [
    {"name": "id", "type": "UUID", "primary": true},
    {"name": "tenant_id", "type": "UUID", "not_null": true},
    {"name": "user_id", "type": "UUID", "not_null": true, "indexed": true},
    {"name": "session_id", "type": "UUID", "indexed": true},
    {"name": "action", "type": "TEXT", "not_null": true, "indexed": true},
    {"name": "resource", "type": "TEXT", "not_null": true},
    {"name": "resource_id", "type": "TEXT"},
    {"name": "permitted", "type": "BOOLEAN", "not_null": true},
    {"name": "denied_reason", "type": "TEXT"},
    {"name": "ip_address", "type": "INET"},
    {"name": "user_agent", "type": "TEXT"},
    {"name": "latency_ms", "type": "INTEGER"},
    {"name": "created_at", "type": "TIMESTAMPTZ", "not_null": true, "indexed": true}
  ],
  "indexes": [
    "idx_access_user ON (user_id, created_at)",
    "idx_access_permitted ON (permitted, created_at)"
  ]
}
```

**Endpoints RBAC:**
- `POST /api/v1/auth/login` — Login com JWT
- `POST /api/v1/auth/refresh` — Refresh token
- `POST /api/v1/auth/logout` — Logout
- `GET /api/v1/users/me` — Perfil atual
- `GET /api/v1/users/:id/permissions` — Permissões efetivas
- `POST /api/v1/roles` — CRUD roles
- `POST /api/v1/users/:id/roles` — Atribuir/remover roles
- `GET /api/v1/access-check` — Verificar permissão (para middleware)

---

### 5. SYSTEM_PARAMETERS

**Propósito:** Configuração centralizada com versionamento.

```json
{
  "table": "system_parameters",
  "fields": [
    {"name": "id", "type": "UUID", "primary": true},
    {"name": "tenant_id", "type": "UUID", "not_null": true, "indexed": true},
    {"name": "cost_center_id", "type": "UUID", "nullable": true},
    {"name": "category", "type": "TEXT", "not_null": true, "indexed": true},
    {"name": "key", "type": "TEXT", "not_null": true},
    {"name": "value", "type": "JSONB", "not_null": true},
    {"name": "value_type", "type": "ENUM", "values": ["string", "number", "boolean", "json", "array"], "not_null": true},
    {"name": "description", "type": "TEXT"},
    {"name": "default_value", "type": "JSONB"},
    {"name": "min_value", "type": "NUMERIC"},
    {"name": "max_value", "type": "NUMERIC"},
    {"name": "allowed_values", "type": "JSONB"},
    {"name": "is_computed", "type": "BOOLEAN", "default": false},
    {"name": "computed_formula", "type": "TEXT"},
    {"name": "requires_restart", "type": "BOOLEAN", "default": false},
    {"name": "is_encrypted", "type": "BOOLEAN", "default": false},
    {"name": "version", "type": "INTEGER", "default": 1},
    {"name": "created_by", "type": "UUID", "not_null": true},
    {"name": "created_at", "type": "TIMESTAMPTZ", "default": "NOW()"},
    {"name": "updated_at", "type": "TIMESTAMPTZ", "default": "NOW()"}
  ],
  "indexes": [
    "idx_params_tenant_cat ON (tenant_id, category)",
    "idx_params_key ON (tenant_id, key)"
  ],
  "unique": ["tenant_id", "cost_center_id", "key"]
}
```

**Categorias de Parâmetros:**
- `financial`: margem_minima, limite_variancia_cmvw
- `pricing`: markup_default, markup_alimentacao
- `scoring`: threshold_go, limite_confianca
- `forecast`: dias_previsao, buffer_perc
- `security`: max_tentativas_login, session_ttl
- `integrations`: api_timeout, retry_attempts

**Endpoints:**
- `GET /api/v1/parameters` — Listar com hierarquia
- `GET /api/v1/parameters/:key` — Valor específico
- `POST /api/v1/parameters` — Criar parâmetro
- `PUT /api/v1/parameters/:key` — Atualizar com versionamento
- `GET /api/v1/parameters/:key/history` — Histórico de mudanças
- `POST /api/v1/parameters/bulk` — Atualização em lote

---

## 🔌 FLUXOS E INTEGRAÇÃO

### Fluxo de Autenticação (RBAC)

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│   Login   │────►│  Verify   │────►│  Load     │────►│ Generate  │
│  Request  │     │ Password  │     │  Roles    │     │   JWT     │
└───────────┘     └───────────┘     └───────────┘     └─────┬─────┘
                                                            │
┌─────────────────────────────────────────────────────────────┼─────┐
│                         MIDDLEWARE                          │     │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │     │
│  │ Validate│───►│ Extract │───►│  Check  │───►│  Load   │◄─┘     │
│  │   JWT   │    │  Roles  │    │Permission    │ Context │        │
│  └─────────┘    └─────────┘    └─────┬───┘    └─────────┘        │
│                                      │                           │
│                            ┌─────────▼──────────┐              │
│                            │  rbac_access_log   │              │
│                            │  (permitted/denied)│              │
│                            └────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo de Auditoria

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│   User    │────►│  Action   │────►│  Generate │────►│   Store   │
│  Action   │     │  Detect   │     │ Checksum  │     │  Audit    │
└───────────┘     └───────────┘     └───────────┘     └─────┬─────┘
                                                            │
                                                            ▼
                                              ┌──────────────────────┐
                                              │  Immutable Storage   │
                                              │  Monthly Partition   │
                                              └──────────────────────┘

Chain Hash: SHA256(previous_checksum + current_data)
```

### Fluxo de Decision Log

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│   Agent   │────►│  Model    │────►│  Capture  │────►│  Store    │
│  Request  │     │  Call     │     │  Context  │     │ Decision  │
└───────────┘     └─────┬─────┘     └───────────┘     └─────┬─────┘
                        │                                 │
                        ▼                                 ▼
              ┌─────────────────┐               ┌───────────────────┐
              │ input_context   │               │ reasoning_chain   │
              │ output_decision │               │ confidence_score│
              │ tokens/cost     │               │ review_status     │
              └─────────────────┘               └───────────────────┘
```

---

## 🔧 IMPLEMENTAÇÃO

### Estrutura de Arquivos

```
~/.openclaw/workspace-openclaw-bpo/
├── PLANO_TECNICO_INFRA_v1.md      # Este arquivo
├── orkestra_schema_v1.sql          # DDL completo
├── docker-compose.yml              # PostgreSQL + serviços
├── 
├── api/
│   ├── main.py                     # FastAPI REST
│   ├── auth.py                     # JWT + RBAC middleware
│   ├── config.py                   # Settings
│   └── dependencies.py             # DB connection
│
├── migrations/
│   ├── README.md                   # Documentação
│   ├── migrate.sh                  # Script CLI
│   ├── V001__baseline.sql          # Schema inicial
│   ├── V002__seed_data.sql         # Dados iniciais
│   └── V003__advanced_triggers.sql # Triggers + functions
│
├── dashboard/
│   └── index.html                  # Dashboard HTML
│
└── sql/
    └── views_analytics.sql         # Views para BI
```

### Roles Padrão

| Role | Permissões | Herança |
|------|-----------|---------|
| super_admin | * (tudo) | - |
| admin | admin.full, event.*, financial.*, pricing.*, agent.*, audit.read | - |
| manager | event.read, event.write, financial.read, pricing.calculate | - |
| financeiro | financial.*, event.read, audit.read | - |
| operador | event.read, event.write, pricing.calculate | - |
| viewer | event.read, financial.read | - |

---

## 📊 MÉTRICAS E MONITORAMENTO

### Views Analíticas

```sql
-- v_audit_daily_summary: Atividades por dia
CREATE VIEW v_audit_daily_summary AS
SELECT 
    tenant_id,
    DATE(created_at) as date,
    action_type,
    resource_type,
    COUNT(*) as count,
    COUNT(DISTINCT actor_id) as unique_actors
FROM audit_log
GROUP BY tenant_id, DATE(created_at), action_type, resource_type;

-- v_decision_accuracy: Métricas de ML
CREATE VIEW v_decision_accuracy AS
SELECT 
    tenant_id,
    model_name,
    DATE(created_at) as date,
    AVG(confidence_score) as avg_confidence,
    COUNT(CASE WHEN confidence_score < 0.7 THEN 1 END) as low_confidence_count,
    AVG(latency_ms) as avg_latency,
    SUM(cost_usd) as total_cost
FROM decision_log
GROUP BY tenant_id, model_name, DATE(created_at);

-- v_agent_performance: Custo e eficiência
CREATE VIEW v_agent_performance AS
SELECT 
    tenant_id,
    agent_id,
    DATE(created_at) as date,
    COUNT(*) as total_calls,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failures,
    AVG(latency_ms) as avg_latency,
    SUM(cost_usd) as total_cost,
    SUM(tokens_in + tokens_out) as total_tokens
FROM agent_action_log
GROUP BY tenant_id, agent_id, DATE(created_at);

-- v_user_permissions: Permissões ativas
CREATE VIEW v_user_permissions AS
SELECT 
    u.tenant_id,
    u.id as user_id,
    u.email,
    r.name as role_name,
    r.permissions,
    ur.valid_from,
    ur.valid_until,
    ur.cost_center_id
FROM rbac_users u
JOIN rbac_user_roles ur ON ur.user_id = u.id
JOIN rbac_roles r ON r.id = ur.role_id
WHERE ur.valid_until IS NULL OR ur.valid_until > NOW();
```

---

## 🚀 PRÓXIMOS PASSOS

1. **Esta semana:** Schema DDL + Migrations V001
2. **Próxima semana:** Docker compose + API FastAPI
3. **Week 3:** Dashboard + Integração completa
4. **Week 4:** Produção com PostgreSQL + backups

---

🎛️ **Orkestra Finance Brain — INFRA v1.0**
*Zero erros. Zero perdas. 100% rastreável.*
