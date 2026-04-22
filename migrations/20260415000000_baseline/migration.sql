-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateTable
CREATE TABLE "public"."RiskLevel" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "minValue" INTEGER NOT NULL,
    "maxValue" INTEGER NOT NULL,

    CONSTRAINT "RiskLevel_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."WorkflowType" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,

    CONSTRAINT "WorkflowType_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."agent_action_log" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "cost_center_id" UUID,
    "session_id" UUID NOT NULL,
    "turn_number" INTEGER NOT NULL,
    "agent_id" UUID,
    "tool_name" TEXT NOT NULL,
    "tool_input" JSONB NOT NULL,
    "tool_output" JSONB,
    "tool_error" JSONB,
    "status" TEXT NOT NULL DEFAULT 'started',
    "latency_ms" INTEGER,
    "cost_usd" DECIMAL(10,6),
    "tokens_in" INTEGER,
    "tokens_out" INTEGER,
    "risk_level" TEXT DEFAULT 'none',
    "approval_required" BOOLEAN DEFAULT false,
    "approved_by" UUID,
    "approved_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agent_action_log_pkey" PRIMARY KEY ("id","created_at")
);

-- CreateTable
CREATE TABLE "public"."agent_runs" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "companyId" TEXT,
    "workflowType" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "riskLevel" TEXT NOT NULL DEFAULT 'low',
    "inputSummary" TEXT,
    "outputSummary" TEXT,
    "totalCost" DOUBLE PRECISION,
    "totalTokens" INTEGER,
    "latencyMs" INTEGER,
    "createdBy" TEXT,
    "startedAt" TIMESTAMPTZ(6),
    "finishedAt" TIMESTAMPTZ(6),
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agent_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."agent_sessions" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "user_id" UUID,
    "session_type" TEXT NOT NULL,
    "context" JSONB DEFAULT '{}',
    "started_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ended_at" TIMESTAMPTZ(6),
    "status" TEXT DEFAULT 'active',

    CONSTRAINT "agent_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."agent_steps" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "agentRunId" TEXT NOT NULL,
    "stepOrder" INTEGER NOT NULL,
    "agentName" TEXT NOT NULL,
    "actionType" TEXT NOT NULL,
    "inputPayload" JSONB,
    "outputPayload" JSONB,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "startedAt" TIMESTAMPTZ(6),
    "finishedAt" TIMESTAMPTZ(6),

    CONSTRAINT "agent_steps_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."approval_requests" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "agentRunId" TEXT NOT NULL,
    "riskLevel" TEXT NOT NULL,
    "requestedAction" TEXT NOT NULL,
    "justification" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "approvedBy" TEXT,
    "approvedAt" TIMESTAMPTZ(6),
    "requestedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "approval_requests_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."artifacts" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "agentRunId" TEXT NOT NULL,
    "artifactType" TEXT NOT NULL,
    "fileName" TEXT NOT NULL,
    "storageUrl" TEXT,
    "checksum" TEXT,
    "sizeBytes" INTEGER,
    "contentType" TEXT,
    "version" INTEGER NOT NULL DEFAULT 1,
    "metadata" JSONB,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "artifacts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."audit_log" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "cost_center_id" UUID,
    "actor_id" UUID NOT NULL,
    "actor_type" TEXT NOT NULL,
    "action_type" TEXT NOT NULL,
    "resource_type" TEXT NOT NULL,
    "resource_id" TEXT NOT NULL,
    "payload_before" JSONB,
    "payload_after" JSONB,
    "diff_summary" TEXT,
    "ip_address" INET,
    "user_agent" TEXT,
    "session_id" UUID,
    "checksum_sha256" TEXT NOT NULL,
    "previous_checksum" TEXT,
    "chain_hash" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_log_pkey" PRIMARY KEY ("id","created_at")
);

-- CreateTable
CREATE TABLE "public"."commercial_packages" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "tenant_id" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "commercial_packages_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."cost_categories" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "tenant_id" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "cost_categories_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."cost_centers" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "parent_id" UUID,
    "active" BOOLEAN DEFAULT true,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "cost_centers_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."cost_events" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "agentRunId" TEXT NOT NULL,
    "modelName" TEXT,
    "tokensIn" INTEGER NOT NULL DEFAULT 0,
    "tokensOut" INTEGER NOT NULL DEFAULT 0,
    "monetaryCost" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "costCategory" TEXT NOT NULL DEFAULT 'inference',
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "cost_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."decision_log" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "cost_center_id" UUID,
    "decision_id" TEXT NOT NULL,
    "model_name" TEXT NOT NULL,
    "model_version" TEXT NOT NULL,
    "prompt_tokens" INTEGER NOT NULL DEFAULT 0,
    "completion_tokens" INTEGER NOT NULL DEFAULT 0,
    "total_tokens" INTEGER NOT NULL DEFAULT 0,
    "input_context" JSONB NOT NULL,
    "output_decision" JSONB NOT NULL,
    "reasoning_chain" JSONB NOT NULL,
    "confidence_score" DECIMAL(5,4) NOT NULL,
    "confidence_breakdown" JSONB,
    "alternative_decisions" JSONB,
    "latency_ms" INTEGER NOT NULL DEFAULT 0,
    "cost_usd" DECIMAL(10,6) NOT NULL DEFAULT 0,
    "metadata" JSONB,
    "session_id" UUID,
    "agent_id" UUID,
    "review_status" TEXT DEFAULT 'pending',
    "reviewed_by" UUID,
    "reviewed_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "decision_log_pkey" PRIMARY KEY ("id","created_at")
);

-- CreateTable
CREATE TABLE "public"."domain_integrity_checks" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "tenantId" TEXT NOT NULL,
    "checkName" TEXT NOT NULL,
    "checkType" TEXT NOT NULL,
    "fromDomain" TEXT NOT NULL,
    "toDomain" TEXT NOT NULL,
    "ruleCondition" JSONB NOT NULL,
    "errorMessage" TEXT NOT NULL,
    "severity" TEXT NOT NULL DEFAULT 'warning',
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "lastCheckedAt" TIMESTAMPTZ(6),
    "lastFailedAt" TIMESTAMPTZ(6),
    "failureCount" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "domain_integrity_checks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."domain_logs" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "systemEventId" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "domain" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "oldState" JSONB,
    "newState" JSONB NOT NULL,
    "processedBy" TEXT,
    "processingTimeMs" INTEGER,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "domain_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."domain_rules" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "companyId" TEXT,
    "domain" TEXT NOT NULL,
    "ruleName" TEXT NOT NULL,
    "ruleDescription" TEXT,
    "ruleLogic" JSONB NOT NULL,
    "priority" INTEGER NOT NULL DEFAULT 100,
    "active" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "domain_rules_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."entity_states" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "tenantId" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "currentState" TEXT NOT NULL,
    "previousState" TEXT,
    "enteredAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "enteredBy" TEXT,
    "actorType" TEXT NOT NULL DEFAULT 'system',
    "reason" TEXT,
    "source" TEXT,
    "version" INTEGER NOT NULL DEFAULT 1,
    "validFrom" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "validUntil" TIMESTAMPTZ(6),
    "isCurrent" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "entity_states_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."event_costs" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "event_id" UUID NOT NULL,
    "category_id" UUID NOT NULL,
    "descricao" TEXT,
    "valor" DECIMAL(12,2),
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "event_costs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."event_financials" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "event_id" UUID NOT NULL,
    "receita_prevista" DECIMAL(12,2) NOT NULL,
    "custo_bebidas_previsto" DECIMAL(12,2) NOT NULL,
    "custo_gelo_previsto" DECIMAL(12,2) NOT NULL,
    "custo_staff_previsto" DECIMAL(12,2) NOT NULL,
    "custo_total_previsto" DECIMAL(12,2) NOT NULL,
    "margem_bruta_prevista" DECIMAL(12,2) NOT NULL,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "event_financials_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."event_items" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "event_id" UUID NOT NULL,
    "product_id" UUID NOT NULL,
    "quantity" DECIMAL(12,2),
    "unit_price" DECIMAL(12,2),
    "total_price" DECIMAL(12,2),
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "event_items_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."event_planning" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "event_id" UUID NOT NULL,
    "category" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "value" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "event_planning_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."event_processors" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "tenantId" TEXT NOT NULL,
    "processorName" TEXT NOT NULL,
    "handlerType" TEXT NOT NULL DEFAULT 'sync',
    "eventTypes" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "aggregateTypes" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "status" TEXT NOT NULL DEFAULT 'active',
    "lastProcessedAt" TIMESTAMPTZ(6),
    "lastEventId" TEXT,
    "eventsProcessed" INTEGER NOT NULL DEFAULT 0,
    "eventsFailed" INTEGER NOT NULL DEFAULT 0,
    "averageLatencyMs" DOUBLE PRECISION,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "event_processors_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."event_snapshots" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "tenantId" TEXT NOT NULL,
    "aggregateType" TEXT NOT NULL,
    "aggregateId" TEXT NOT NULL,
    "version" INTEGER NOT NULL,
    "state" JSONB NOT NULL,
    "lastEventId" TEXT NOT NULL,
    "lastEventType" TEXT NOT NULL,
    "eventCount" INTEGER NOT NULL,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "event_snapshots_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."events" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "tenant_id" UUID NOT NULL,
    "cost_center_id" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "event_type" TEXT,
    "event_date" DATE,
    "guests" INTEGER,
    "status" TEXT DEFAULT 'planned',
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,
    "event_id" TEXT,
    "company_name" TEXT,
    "revenue_total" DECIMAL(14,2),
    "cmv_total" DECIMAL(14,2),
    "margin_pct" DECIMAL(8,4),
    "net_profit" DECIMAL(14,2),
    "updated_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."integrity_check_logs" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "tenantId" TEXT NOT NULL,
    "checkId" TEXT NOT NULL,
    "checkName" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "passed" BOOLEAN NOT NULL,
    "violations" JSONB,
    "errorDetails" TEXT,
    "actionTaken" TEXT,
    "actionBy" TEXT,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "integrity_check_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."inventory_items" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "currentQty" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "unit" TEXT NOT NULL,
    "unitPrice" DOUBLE PRECISION,
    "supplier" TEXT,
    "minStockLevel" DOUBLE PRECISION,
    "reorderPoint" DOUBLE PRECISION,
    "entryHistory" JSONB,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "inventory_items_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."memory_items" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "companyId" TEXT,
    "memoryType" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "tags" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "sourceType" TEXT,
    "sourceRef" TEXT,
    "confidenceScore" DOUBLE PRECISION,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "memory_items_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."package_items" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "package_id" UUID NOT NULL,
    "product_id" UUID NOT NULL,

    CONSTRAINT "package_items_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."products_services" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "tenant_id" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "category" TEXT,
    "unit" TEXT,
    "base_price" DECIMAL(12,2),
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "products_services_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."rbac_access_log" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "session_id" UUID,
    "action" TEXT NOT NULL,
    "resource" TEXT NOT NULL,
    "resource_id" TEXT,
    "permitted" BOOLEAN NOT NULL,
    "denied_reason" TEXT,
    "ip_address" INET,
    "user_agent" TEXT,
    "latency_ms" INTEGER,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "rbac_access_log_pkey" PRIMARY KEY ("id","created_at")
);

-- CreateTable
CREATE TABLE "public"."rbac_permissions" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "resource" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "conditions" JSONB,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "rbac_permissions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."rbac_roles" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "permissions" JSONB NOT NULL DEFAULT '[]',
    "parent_role_id" UUID,
    "hierarchy_level" INTEGER NOT NULL DEFAULT 0,
    "is_system" BOOLEAN DEFAULT false,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "rbac_roles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."rbac_user_roles" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "role_id" UUID NOT NULL,
    "cost_center_id" UUID,
    "valid_from" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "valid_until" TIMESTAMPTZ(6),
    "granted_by" UUID NOT NULL,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "rbac_user_roles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."rbac_users" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "first_name" TEXT,
    "last_name" TEXT,
    "phone" TEXT,
    "mfa_enabled" BOOLEAN DEFAULT false,
    "mfa_secret" TEXT,
    "session_config" JSONB DEFAULT '{"ttl_minutes": 60}',
    "last_login_at" TIMESTAMPTZ(6),
    "failed_logins" INTEGER DEFAULT 0,
    "locked_until" TIMESTAMPTZ(6),
    "active" BOOLEAN DEFAULT true,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "rbac_users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."recipes" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "recipeId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "category" TEXT,
    "yield" INTEGER,
    "prepTimeMin" INTEGER,
    "complexity" TEXT,
    "ingredients" JSONB,
    "costPerServing" DOUBLE PRECISION,
    "instructions" TEXT,
    "active" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "recipes_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."schema_migrations" (
    "version" INTEGER NOT NULL,
    "description" TEXT,
    "executed_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,
    "execution_time_ms" INTEGER,

    CONSTRAINT "schema_migrations_pkey" PRIMARY KEY ("version")
);

-- CreateTable
CREATE TABLE "public"."state_transition_rules" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "tenantId" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "fromState" TEXT NOT NULL,
    "toState" TEXT NOT NULL,
    "preConditions" JSONB NOT NULL DEFAULT '{}',
    "requiredFields" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "allowedActors" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "requiresApproval" BOOLEAN NOT NULL DEFAULT false,
    "approvalLevel" TEXT,
    "autoActions" JSONB,
    "sideEffects" JSONB,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "priority" INTEGER NOT NULL DEFAULT 100,
    "successMessage" TEXT NOT NULL DEFAULT 'Transição realizada com sucesso',
    "failureMessage" TEXT,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "state_transition_rules_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."state_transitions" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "tenantId" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "fromState" TEXT NOT NULL DEFAULT '',
    "toState" TEXT NOT NULL DEFAULT '',
    "actorType" TEXT NOT NULL DEFAULT 'system',
    "actorId" TEXT,
    "reason" TEXT,
    "triggerEvent" TEXT,
    "source" TEXT,
    "ipAddress" TEXT,
    "validationResult" JSONB,
    "warnings" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "blockedBy" TEXT,
    "systemEventId" TEXT,
    "attemptedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completedAt" TIMESTAMPTZ(6),
    "durationMs" INTEGER,
    "status" TEXT NOT NULL DEFAULT 'completed',
    "errorMessage" TEXT,
    "resultingStateId" TEXT,

    CONSTRAINT "state_transitions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."system_events" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "tenantId" TEXT NOT NULL,
    "aggregateType" TEXT NOT NULL,
    "aggregateId" TEXT NOT NULL,
    "eventType" TEXT NOT NULL,
    "payload" JSONB NOT NULL,
    "source" TEXT NOT NULL DEFAULT 'api',
    "correlationId" TEXT,
    "causationId" TEXT,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "errorMessage" TEXT,
    "processedAt" TIMESTAMPTZ(6),
    "createdBy" TEXT,
    "ipAddress" TEXT,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "system_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."system_parameter_changes" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "param_id" UUID NOT NULL,
    "previous_value" JSONB NOT NULL,
    "new_value" JSONB NOT NULL,
    "changed_by" UUID NOT NULL,
    "changed_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "change_reason" TEXT,
    "rolled_back" BOOLEAN DEFAULT false,
    "rolled_back_at" TIMESTAMPTZ(6),
    "rolled_back_by" UUID,

    CONSTRAINT "system_parameter_changes_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."system_parameters" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "tenant_id" UUID NOT NULL,
    "cost_center_id" UUID,
    "category" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "value" JSONB NOT NULL,
    "value_type" TEXT NOT NULL,
    "description" TEXT,
    "default_value" JSONB,
    "min_value" DECIMAL,
    "max_value" DECIMAL,
    "allowed_values" JSONB,
    "is_computed" BOOLEAN DEFAULT false,
    "computed_formula" TEXT,
    "requires_restart" BOOLEAN DEFAULT false,
    "is_encrypted" BOOLEAN DEFAULT false,
    "version" INTEGER DEFAULT 1,
    "created_by" UUID NOT NULL,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "system_parameters_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."tenants" (
    "id" UUID NOT NULL DEFAULT uuid_generate_v4(),
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "settings" JSONB DEFAULT '{}',
    "active" BOOLEAN DEFAULT true,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "tenants_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."tool_calls" (
    "id" TEXT NOT NULL DEFAULT (gen_random_uuid())::text,
    "agentStepId" TEXT NOT NULL,
    "toolName" TEXT NOT NULL,
    "toolInput" JSONB,
    "toolOutput" JSONB,
    "context" JSONB,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "latencyMs" INTEGER,
    "costEstimate" DOUBLE PRECISION,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "tool_calls_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "idx_actions_session_turn" ON "public"."agent_action_log"("session_id" ASC, "turn_number" ASC);

-- CreateIndex
CREATE INDEX "idx_actions_tool_status" ON "public"."agent_action_log"("tool_name" ASC, "status" ASC, "created_at" ASC);

-- CreateIndex
CREATE INDEX "idx_agent_runs_company" ON "public"."agent_runs"("companyId" ASC);

-- CreateIndex
CREATE INDEX "idx_agent_runs_created" ON "public"."agent_runs"("createdAt" ASC);

-- CreateIndex
CREATE INDEX "idx_agent_runs_status" ON "public"."agent_runs"("status" ASC);

-- CreateIndex
CREATE INDEX "idx_agent_runs_workflow" ON "public"."agent_runs"("workflowType" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "agent_steps_agentRunId_stepOrder_key" ON "public"."agent_steps"("agentRunId" ASC, "stepOrder" ASC);

-- CreateIndex
CREATE INDEX "idx_agent_steps_action" ON "public"."agent_steps"("actionType" ASC);

-- CreateIndex
CREATE INDEX "idx_agent_steps_run" ON "public"."agent_steps"("agentRunId" ASC);

-- CreateIndex
CREATE INDEX "idx_agent_steps_status" ON "public"."agent_steps"("status" ASC);

-- CreateIndex
CREATE INDEX "idx_approvals_risk" ON "public"."approval_requests"("riskLevel" ASC);

-- CreateIndex
CREATE INDEX "idx_approvals_run" ON "public"."approval_requests"("agentRunId" ASC);

-- CreateIndex
CREATE INDEX "idx_approvals_status" ON "public"."approval_requests"("status" ASC);

-- CreateIndex
CREATE INDEX "idx_artifacts_created" ON "public"."artifacts"("createdAt" ASC);

-- CreateIndex
CREATE INDEX "idx_artifacts_run" ON "public"."artifacts"("agentRunId" ASC);

-- CreateIndex
CREATE INDEX "idx_artifacts_type" ON "public"."artifacts"("artifactType" ASC);

-- CreateIndex
CREATE INDEX "idx_audit_actor_action" ON "public"."audit_log"("actor_id" ASC, "action_type" ASC);

-- CreateIndex
CREATE INDEX "idx_audit_resource" ON "public"."audit_log"("resource_type" ASC, "resource_id" ASC, "created_at" ASC);

-- CreateIndex
CREATE INDEX "idx_audit_tenant_created" ON "public"."audit_log"("tenant_id" ASC, "created_at" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "cost_centers_tenant_id_code_key" ON "public"."cost_centers"("tenant_id" ASC, "code" ASC);

-- CreateIndex
CREATE INDEX "idx_cost_centers_tenant" ON "public"."cost_centers"("tenant_id" ASC);

-- CreateIndex
CREATE INDEX "idx_cost_events_created" ON "public"."cost_events"("createdAt" ASC);

-- CreateIndex
CREATE INDEX "idx_cost_events_model" ON "public"."cost_events"("modelName" ASC);

-- CreateIndex
CREATE INDEX "idx_cost_events_run" ON "public"."cost_events"("agentRunId" ASC);

-- CreateIndex
CREATE INDEX "idx_decisions_tenant_model" ON "public"."decision_log"("tenant_id" ASC, "model_name" ASC, "created_at" ASC);

-- CreateIndex
CREATE INDEX "idx_integrity_checks_active" ON "public"."domain_integrity_checks"("tenantId" ASC, "checkType" ASC, "isActive" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "idx_integrity_checks_unique" ON "public"."domain_integrity_checks"("tenantId" ASC, "checkName" ASC);

-- CreateIndex
CREATE INDEX "idx_domain_logs_action" ON "public"."domain_logs"("tenantId" ASC, "action" ASC, "createdAt" ASC);

-- CreateIndex
CREATE INDEX "idx_domain_logs_entity" ON "public"."domain_logs"("tenantId" ASC, "entityType" ASC, "entityId" ASC);

-- CreateIndex
CREATE INDEX "idx_domain_logs_system_event" ON "public"."domain_logs"("systemEventId" ASC);

-- CreateIndex
CREATE INDEX "idx_domain_logs_tenant_domain" ON "public"."domain_logs"("tenantId" ASC, "domain" ASC, "createdAt" ASC);

-- CreateIndex
CREATE INDEX "idx_domain_rules_active" ON "public"."domain_rules"("active" ASC);

-- CreateIndex
CREATE INDEX "idx_domain_rules_company" ON "public"."domain_rules"("companyId" ASC);

-- CreateIndex
CREATE INDEX "idx_domain_rules_domain" ON "public"."domain_rules"("domain" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "idx_domain_rules_unique" ON "public"."domain_rules"("companyId" ASC, "domain" ASC, "ruleName" ASC);

-- CreateIndex
CREATE INDEX "idx_entity_states_current_state" ON "public"."entity_states"("tenantId" ASC, "currentState" ASC, "isCurrent" ASC);

-- CreateIndex
CREATE INDEX "idx_entity_states_lookup" ON "public"."entity_states"("tenantId" ASC, "entityType" ASC, "entityId" ASC);

-- CreateIndex
CREATE INDEX "idx_entity_states_type_state" ON "public"."entity_states"("tenantId" ASC, "entityType" ASC, "currentState" ASC);

-- CreateIndex
CREATE INDEX "idx_entity_states_validity" ON "public"."entity_states"("validFrom" ASC, "validUntil" ASC);

-- CreateIndex
CREATE INDEX "idx_event_processors_status" ON "public"."event_processors"("tenantId" ASC, "status" ASC, "lastProcessedAt" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "idx_event_processors_unique" ON "public"."event_processors"("tenantId" ASC, "processorName" ASC);

-- CreateIndex
CREATE INDEX "idx_event_snapshots_lookup" ON "public"."event_snapshots"("tenantId" ASC, "aggregateType" ASC, "aggregateId" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "idx_event_snapshots_unique" ON "public"."event_snapshots"("tenantId" ASC, "aggregateType" ASC, "aggregateId" ASC, "version" ASC);

-- CreateIndex
CREATE INDEX "idx_integrity_logs_entity" ON "public"."integrity_check_logs"("tenantId" ASC, "checkId" ASC, "entityType" ASC, "entityId" ASC);

-- CreateIndex
CREATE INDEX "idx_integrity_logs_status" ON "public"."integrity_check_logs"("tenantId" ASC, "passed" ASC, "createdAt" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "idx_inventory_code" ON "public"."inventory_items"("code" ASC);

-- CreateIndex
CREATE INDEX "idx_inventory_qty" ON "public"."inventory_items"("currentQty" ASC);

-- CreateIndex
CREATE INDEX "idx_inventory_supplier" ON "public"."inventory_items"("supplier" ASC);

-- CreateIndex
CREATE INDEX "idx_memory_company" ON "public"."memory_items"("companyId" ASC);

-- CreateIndex
CREATE INDEX "idx_memory_created" ON "public"."memory_items"("createdAt" ASC);

-- CreateIndex
CREATE INDEX "idx_memory_type" ON "public"."memory_items"("memoryType" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "rbac_permissions_code_key" ON "public"."rbac_permissions"("code" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "rbac_roles_tenant_id_name_key" ON "public"."rbac_roles"("tenant_id" ASC, "name" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "rbac_user_roles_user_id_role_id_cost_center_id_valid_from_key" ON "public"."rbac_user_roles"("user_id" ASC, "role_id" ASC, "cost_center_id" ASC, "valid_from" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "rbac_users_tenant_id_email_key" ON "public"."rbac_users"("tenant_id" ASC, "email" ASC);

-- CreateIndex
CREATE INDEX "idx_recipes_active" ON "public"."recipes"("active" ASC);

-- CreateIndex
CREATE INDEX "idx_recipes_category" ON "public"."recipes"("category" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "idx_recipes_recipe_id" ON "public"."recipes"("recipeId" ASC);

-- CreateIndex
CREATE INDEX "idx_state_transition_rules_active" ON "public"."state_transition_rules"("tenantId" ASC, "entityType" ASC, "isActive" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "idx_state_transition_rules_unique" ON "public"."state_transition_rules"("tenantId" ASC, "entityType" ASC, "fromState" ASC, "toState" ASC);

-- CreateIndex
CREATE INDEX "idx_state_transitions_actor" ON "public"."state_transitions"("tenantId" ASC, "actorType" ASC, "actorId" ASC);

-- CreateIndex
CREATE INDEX "idx_state_transitions_attempted" ON "public"."state_transitions"("attemptedAt" ASC);

-- CreateIndex
CREATE INDEX "idx_state_transitions_entity" ON "public"."state_transitions"("tenantId" ASC, "entityType" ASC, "entityId" ASC, "attemptedAt" ASC);

-- CreateIndex
CREATE INDEX "idx_state_transitions_states" ON "public"."state_transitions"("tenantId" ASC, "fromState" ASC, "toState" ASC);

-- CreateIndex
CREATE INDEX "idx_state_transitions_system_event" ON "public"."state_transitions"("systemEventId" ASC);

-- CreateIndex
CREATE INDEX "idx_system_events_agg" ON "public"."system_events"("aggregateId" ASC, "aggregateType" ASC);

-- CreateIndex
CREATE INDEX "idx_system_events_correlation" ON "public"."system_events"("correlationId" ASC);

-- CreateIndex
CREATE INDEX "idx_system_events_created" ON "public"."system_events"("createdAt" ASC);

-- CreateIndex
CREATE INDEX "idx_system_events_tenant_agg" ON "public"."system_events"("tenantId" ASC, "aggregateType" ASC, "aggregateId" ASC);

-- CreateIndex
CREATE INDEX "idx_system_events_tenant_status" ON "public"."system_events"("tenantId" ASC, "status" ASC, "createdAt" ASC);

-- CreateIndex
CREATE INDEX "idx_system_events_tenant_type" ON "public"."system_events"("tenantId" ASC, "eventType" ASC, "createdAt" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "system_parameters_tenant_id_cost_center_id_key_key" ON "public"."system_parameters"("tenant_id" ASC, "cost_center_id" ASC, "key" ASC);

-- CreateIndex
CREATE INDEX "idx_tenants_slug" ON "public"."tenants"("slug" ASC);

-- CreateIndex
CREATE UNIQUE INDEX "tenants_slug_key" ON "public"."tenants"("slug" ASC);

-- CreateIndex
CREATE INDEX "idx_tool_calls_created" ON "public"."tool_calls"("createdAt" ASC);

-- CreateIndex
CREATE INDEX "idx_tool_calls_status" ON "public"."tool_calls"("status" ASC);

-- CreateIndex
CREATE INDEX "idx_tool_calls_step" ON "public"."tool_calls"("agentStepId" ASC);

-- CreateIndex
CREATE INDEX "idx_tool_calls_tool" ON "public"."tool_calls"("toolName" ASC);

-- AddForeignKey
ALTER TABLE "public"."agent_action_log" ADD CONSTRAINT "agent_action_log_cost_center_id_fkey" FOREIGN KEY ("cost_center_id") REFERENCES "public"."cost_centers"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."agent_action_log" ADD CONSTRAINT "agent_action_log_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."agent_sessions" ADD CONSTRAINT "agent_sessions_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."agent_sessions" ADD CONSTRAINT "agent_sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."rbac_users"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."agent_steps" ADD CONSTRAINT "agent_steps_agentRunId_fkey" FOREIGN KEY ("agentRunId") REFERENCES "public"."agent_runs"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."approval_requests" ADD CONSTRAINT "approval_requests_agentRunId_fkey" FOREIGN KEY ("agentRunId") REFERENCES "public"."agent_runs"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."artifacts" ADD CONSTRAINT "artifacts_agentRunId_fkey" FOREIGN KEY ("agentRunId") REFERENCES "public"."agent_runs"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."audit_log" ADD CONSTRAINT "audit_log_cost_center_id_fkey" FOREIGN KEY ("cost_center_id") REFERENCES "public"."cost_centers"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."audit_log" ADD CONSTRAINT "audit_log_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."cost_centers" ADD CONSTRAINT "cost_centers_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "public"."cost_centers"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."cost_centers" ADD CONSTRAINT "cost_centers_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."cost_events" ADD CONSTRAINT "cost_events_agentRunId_fkey" FOREIGN KEY ("agentRunId") REFERENCES "public"."agent_runs"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."decision_log" ADD CONSTRAINT "decision_log_cost_center_id_fkey" FOREIGN KEY ("cost_center_id") REFERENCES "public"."cost_centers"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."decision_log" ADD CONSTRAINT "decision_log_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."domain_logs" ADD CONSTRAINT "domain_logs_systemEventId_fkey" FOREIGN KEY ("systemEventId") REFERENCES "public"."system_events"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."rbac_access_log" ADD CONSTRAINT "rbac_access_log_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."rbac_roles" ADD CONSTRAINT "rbac_roles_parent_role_id_fkey" FOREIGN KEY ("parent_role_id") REFERENCES "public"."rbac_roles"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."rbac_roles" ADD CONSTRAINT "rbac_roles_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."rbac_user_roles" ADD CONSTRAINT "rbac_user_roles_cost_center_id_fkey" FOREIGN KEY ("cost_center_id") REFERENCES "public"."cost_centers"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."rbac_user_roles" ADD CONSTRAINT "rbac_user_roles_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."rbac_roles"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."rbac_user_roles" ADD CONSTRAINT "rbac_user_roles_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."rbac_user_roles" ADD CONSTRAINT "rbac_user_roles_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."rbac_users"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."rbac_users" ADD CONSTRAINT "rbac_users_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."system_parameter_changes" ADD CONSTRAINT "system_parameter_changes_param_id_fkey" FOREIGN KEY ("param_id") REFERENCES "public"."system_parameters"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."system_parameter_changes" ADD CONSTRAINT "system_parameter_changes_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."system_parameters" ADD CONSTRAINT "system_parameters_cost_center_id_fkey" FOREIGN KEY ("cost_center_id") REFERENCES "public"."cost_centers"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."system_parameters" ADD CONSTRAINT "system_parameters_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "public"."tool_calls" ADD CONSTRAINT "tool_calls_agentStepId_fkey" FOREIGN KEY ("agentStepId") REFERENCES "public"."agent_steps"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

