-- ============================================================
-- MIGRATION V006 — PRISMA ORM RUNTIME TABLES
--
-- Creates ALL tables required by the Prisma ORM models that
-- were never migrated to the real database.
--
-- Rules:
--   • ONLY creates missing tables — does NOT touch:
--     events, entity_states, state_transitions,
--     state_transition_rules, tenants, cost_centers, or
--     any other existing operational table
--   • All column names are camelCase (matching Prisma field
--     names verbatim — no @map decorators on these models)
--   • All statements are idempotent (IF NOT EXISTS)
--   • Foreign keys are deferred to the end
-- ============================================================


-- ── 1. agent_runs ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_runs (
    "id"            TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "companyId"     TEXT,
    "workflowType"  TEXT        NOT NULL,
    "status"        TEXT        NOT NULL DEFAULT 'pending',
    "riskLevel"     TEXT        NOT NULL DEFAULT 'low',
    "inputSummary"  TEXT,
    "outputSummary" TEXT,
    "totalCost"     FLOAT8,
    "totalTokens"   INTEGER,
    "latencyMs"     INTEGER,
    "createdBy"     TEXT,
    "startedAt"     TIMESTAMPTZ,
    "finishedAt"    TIMESTAMPTZ,
    "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_company
    ON agent_runs ("companyId");
CREATE INDEX IF NOT EXISTS idx_agent_runs_status
    ON agent_runs ("status");
CREATE INDEX IF NOT EXISTS idx_agent_runs_workflow
    ON agent_runs ("workflowType");
CREATE INDEX IF NOT EXISTS idx_agent_runs_created
    ON agent_runs ("createdAt");


-- ── 2. agent_steps ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_steps (
    "id"             TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "agentRunId"     TEXT        NOT NULL,
    "stepOrder"      INTEGER     NOT NULL,
    "agentName"      TEXT        NOT NULL,
    "actionType"     TEXT        NOT NULL,
    "inputPayload"   JSONB,
    "outputPayload"  JSONB,
    "status"         TEXT        NOT NULL DEFAULT 'pending',
    "startedAt"      TIMESTAMPTZ,
    "finishedAt"     TIMESTAMPTZ,
    PRIMARY KEY ("id"),
    UNIQUE ("agentRunId", "stepOrder"),
    FOREIGN KEY ("agentRunId") REFERENCES agent_runs("id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_steps_run
    ON agent_steps ("agentRunId");
CREATE INDEX IF NOT EXISTS idx_agent_steps_status
    ON agent_steps ("status");
CREATE INDEX IF NOT EXISTS idx_agent_steps_action
    ON agent_steps ("actionType");


-- ── 3. tool_calls ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tool_calls (
    "id"           TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "agentStepId"  TEXT        NOT NULL,
    "toolName"     TEXT        NOT NULL,
    "toolInput"    JSONB,
    "toolOutput"   JSONB,
    "context"      JSONB,
    "status"       TEXT        NOT NULL DEFAULT 'pending',
    "latencyMs"    INTEGER,
    "costEstimate" FLOAT8,
    "createdAt"    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id"),
    FOREIGN KEY ("agentStepId") REFERENCES agent_steps("id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_step
    ON tool_calls ("agentStepId");
CREATE INDEX IF NOT EXISTS idx_tool_calls_tool
    ON tool_calls ("toolName");
CREATE INDEX IF NOT EXISTS idx_tool_calls_status
    ON tool_calls ("status");
CREATE INDEX IF NOT EXISTS idx_tool_calls_created
    ON tool_calls ("createdAt");


-- ── 4. approval_requests ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS approval_requests (
    "id"              TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "agentRunId"      TEXT        NOT NULL,
    "riskLevel"       TEXT        NOT NULL,
    "requestedAction" TEXT        NOT NULL,
    "justification"   TEXT        NOT NULL,
    "status"          TEXT        NOT NULL DEFAULT 'pending',
    "approvedBy"      TEXT,
    "approvedAt"      TIMESTAMPTZ,
    "requestedAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id"),
    FOREIGN KEY ("agentRunId") REFERENCES agent_runs("id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_approvals_run
    ON approval_requests ("agentRunId");
CREATE INDEX IF NOT EXISTS idx_approvals_status
    ON approval_requests ("status");
CREATE INDEX IF NOT EXISTS idx_approvals_risk
    ON approval_requests ("riskLevel");


-- ── 5. memory_items ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memory_items (
    "id"              TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "companyId"       TEXT,
    "memoryType"      TEXT        NOT NULL,
    "title"           TEXT        NOT NULL,
    "content"         TEXT        NOT NULL,
    "tags"            TEXT[]      NOT NULL DEFAULT '{}',
    "sourceType"      TEXT,
    "sourceRef"       TEXT,
    "confidenceScore" FLOAT8,
    "createdAt"       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS idx_memory_company
    ON memory_items ("companyId");
CREATE INDEX IF NOT EXISTS idx_memory_type
    ON memory_items ("memoryType");
CREATE INDEX IF NOT EXISTS idx_memory_created
    ON memory_items ("createdAt");


-- ── 6. domain_rules ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS domain_rules (
    "id"              TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "companyId"       TEXT,
    "domain"          TEXT        NOT NULL,
    "ruleName"        TEXT        NOT NULL,
    "ruleDescription" TEXT,
    "ruleLogic"       JSONB       NOT NULL,
    "priority"        INTEGER     NOT NULL DEFAULT 100,
    "active"          BOOLEAN     NOT NULL DEFAULT TRUE,
    "createdAt"       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_domain_rules_unique
    ON domain_rules ("companyId", "domain", "ruleName");
CREATE INDEX IF NOT EXISTS idx_domain_rules_company
    ON domain_rules ("companyId");
CREATE INDEX IF NOT EXISTS idx_domain_rules_domain
    ON domain_rules ("domain");
CREATE INDEX IF NOT EXISTS idx_domain_rules_active
    ON domain_rules ("active");


-- ── 7. artifacts ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifacts (
    "id"           TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "agentRunId"   TEXT        NOT NULL,
    "artifactType" TEXT        NOT NULL,
    "fileName"     TEXT        NOT NULL,
    "storageUrl"   TEXT,
    "checksum"     TEXT,
    "sizeBytes"    INTEGER,
    "contentType"  TEXT,
    "version"      INTEGER     NOT NULL DEFAULT 1,
    "metadata"     JSONB,
    "createdAt"    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id"),
    FOREIGN KEY ("agentRunId") REFERENCES agent_runs("id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_artifacts_run
    ON artifacts ("agentRunId");
CREATE INDEX IF NOT EXISTS idx_artifacts_type
    ON artifacts ("artifactType");
CREATE INDEX IF NOT EXISTS idx_artifacts_created
    ON artifacts ("createdAt");


-- ── 8. cost_events ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cost_events (
    "id"           TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "agentRunId"   TEXT        NOT NULL,
    "modelName"    TEXT,
    "tokensIn"     INTEGER     NOT NULL DEFAULT 0,
    "tokensOut"    INTEGER     NOT NULL DEFAULT 0,
    "monetaryCost" FLOAT8      NOT NULL DEFAULT 0,
    "costCategory" TEXT        NOT NULL DEFAULT 'inference',
    "createdAt"    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id"),
    FOREIGN KEY ("agentRunId") REFERENCES agent_runs("id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cost_events_run
    ON cost_events ("agentRunId");
CREATE INDEX IF NOT EXISTS idx_cost_events_model
    ON cost_events ("modelName");
CREATE INDEX IF NOT EXISTS idx_cost_events_created
    ON cost_events ("createdAt");


-- ── 9. system_events ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_events (
    "id"            TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "tenantId"      TEXT        NOT NULL,
    "aggregateType" TEXT        NOT NULL,
    "aggregateId"   TEXT        NOT NULL,
    "eventType"     TEXT        NOT NULL,
    "payload"       JSONB       NOT NULL,
    "source"        TEXT        NOT NULL DEFAULT 'api',
    "correlationId" TEXT,
    "causationId"   TEXT,
    "status"        TEXT        NOT NULL DEFAULT 'pending',
    "errorMessage"  TEXT,
    "processedAt"   TIMESTAMPTZ,
    "createdBy"     TEXT,
    "ipAddress"     TEXT,
    "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS idx_system_events_tenant_agg
    ON system_events ("tenantId", "aggregateType", "aggregateId");
CREATE INDEX IF NOT EXISTS idx_system_events_tenant_type
    ON system_events ("tenantId", "eventType", "createdAt");
CREATE INDEX IF NOT EXISTS idx_system_events_tenant_status
    ON system_events ("tenantId", "status", "createdAt");
CREATE INDEX IF NOT EXISTS idx_system_events_correlation
    ON system_events ("correlationId");
CREATE INDEX IF NOT EXISTS idx_system_events_created
    ON system_events ("createdAt");
CREATE INDEX IF NOT EXISTS idx_system_events_agg
    ON system_events ("aggregateId", "aggregateType");


-- ── 10. domain_logs ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS domain_logs (
    "id"               TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "systemEventId"    TEXT        NOT NULL,
    "tenantId"         TEXT        NOT NULL,
    "domain"           TEXT        NOT NULL,
    "action"           TEXT        NOT NULL,
    "entityId"         TEXT        NOT NULL,
    "entityType"       TEXT        NOT NULL,
    "oldState"         JSONB,
    "newState"         JSONB       NOT NULL,
    "processedBy"      TEXT,
    "processingTimeMs" INTEGER,
    "createdAt"        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id"),
    FOREIGN KEY ("systemEventId") REFERENCES system_events("id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_domain_logs_tenant_domain
    ON domain_logs ("tenantId", "domain", "createdAt");
CREATE INDEX IF NOT EXISTS idx_domain_logs_entity
    ON domain_logs ("tenantId", "entityType", "entityId");
CREATE INDEX IF NOT EXISTS idx_domain_logs_action
    ON domain_logs ("tenantId", "action", "createdAt");
CREATE INDEX IF NOT EXISTS idx_domain_logs_system_event
    ON domain_logs ("systemEventId");


-- ── 11. event_processors ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS event_processors (
    "id"               TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "tenantId"         TEXT        NOT NULL,
    "processorName"    TEXT        NOT NULL,
    "handlerType"      TEXT        NOT NULL DEFAULT 'sync',
    "eventTypes"       TEXT[]      NOT NULL DEFAULT '{}',
    "aggregateTypes"   TEXT[]      NOT NULL DEFAULT '{}',
    "status"           TEXT        NOT NULL DEFAULT 'active',
    "lastProcessedAt"  TIMESTAMPTZ,
    "lastEventId"      TEXT,
    "eventsProcessed"  INTEGER     NOT NULL DEFAULT 0,
    "eventsFailed"     INTEGER     NOT NULL DEFAULT 0,
    "averageLatencyMs" FLOAT8,
    "createdAt"        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_processors_unique
    ON event_processors ("tenantId", "processorName");
CREATE INDEX IF NOT EXISTS idx_event_processors_status
    ON event_processors ("tenantId", "status", "lastProcessedAt");


-- ── 12. event_snapshots ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS event_snapshots (
    "id"            TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "tenantId"      TEXT        NOT NULL,
    "aggregateType" TEXT        NOT NULL,
    "aggregateId"   TEXT        NOT NULL,
    "version"       INTEGER     NOT NULL,
    "state"         JSONB       NOT NULL,
    "lastEventId"   TEXT        NOT NULL,
    "lastEventType" TEXT        NOT NULL,
    "eventCount"    INTEGER     NOT NULL,
    "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_snapshots_unique
    ON event_snapshots ("tenantId", "aggregateType", "aggregateId", "version");
CREATE INDEX IF NOT EXISTS idx_event_snapshots_lookup
    ON event_snapshots ("tenantId", "aggregateType", "aggregateId");


-- ── 13. domain_integrity_checks ───────────────────────────────
CREATE TABLE IF NOT EXISTS domain_integrity_checks (
    "id"            TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "tenantId"      TEXT        NOT NULL,
    "checkName"     TEXT        NOT NULL,
    "checkType"     TEXT        NOT NULL,
    "fromDomain"    TEXT        NOT NULL,
    "toDomain"      TEXT        NOT NULL,
    "ruleCondition" JSONB       NOT NULL,
    "errorMessage"  TEXT        NOT NULL,
    "severity"      TEXT        NOT NULL DEFAULT 'warning',
    "isActive"      BOOLEAN     NOT NULL DEFAULT TRUE,
    "lastCheckedAt" TIMESTAMPTZ,
    "lastFailedAt"  TIMESTAMPTZ,
    "failureCount"  INTEGER     NOT NULL DEFAULT 0,
    "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_integrity_checks_unique
    ON domain_integrity_checks ("tenantId", "checkName");
CREATE INDEX IF NOT EXISTS idx_integrity_checks_active
    ON domain_integrity_checks ("tenantId", "checkType", "isActive");


-- ── 14. integrity_check_logs ──────────────────────────────────
CREATE TABLE IF NOT EXISTS integrity_check_logs (
    "id"           TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "tenantId"     TEXT        NOT NULL,
    "checkId"      TEXT        NOT NULL,
    "checkName"    TEXT        NOT NULL,
    "entityType"   TEXT        NOT NULL,
    "entityId"     TEXT        NOT NULL,
    "passed"       BOOLEAN     NOT NULL,
    "violations"   JSONB,
    "errorDetails" TEXT,
    "actionTaken"  TEXT,
    "actionBy"     TEXT,
    "createdAt"    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS idx_integrity_logs_entity
    ON integrity_check_logs ("tenantId", "checkId", "entityType", "entityId");
CREATE INDEX IF NOT EXISTS idx_integrity_logs_status
    ON integrity_check_logs ("tenantId", "passed", "createdAt");


-- ── 15. recipes ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recipes (
    "id"             TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "recipeId"       TEXT        NOT NULL,
    "name"           TEXT        NOT NULL,
    "category"       TEXT,
    "yield"          INTEGER,
    "prepTimeMin"    INTEGER,
    "complexity"     TEXT,
    "ingredients"    JSONB,
    "costPerServing" FLOAT8,
    "instructions"   TEXT,
    "active"         BOOLEAN     NOT NULL DEFAULT TRUE,
    "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_recipes_recipe_id
    ON recipes ("recipeId");
CREATE INDEX IF NOT EXISTS idx_recipes_category
    ON recipes ("category");
CREATE INDEX IF NOT EXISTS idx_recipes_active
    ON recipes ("active");


-- ── 16. inventory_items ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS inventory_items (
    "id"            TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "code"          TEXT        NOT NULL,
    "name"          TEXT        NOT NULL,
    "currentQty"    FLOAT8      NOT NULL DEFAULT 0,
    "unit"          TEXT        NOT NULL,
    "unitPrice"     FLOAT8,
    "supplier"      TEXT,
    "minStockLevel" FLOAT8,
    "reorderPoint"  FLOAT8,
    "entryHistory"  JSONB,
    "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_code
    ON inventory_items ("code");
CREATE INDEX IF NOT EXISTS idx_inventory_supplier
    ON inventory_items ("supplier");
CREATE INDEX IF NOT EXISTS idx_inventory_qty
    ON inventory_items ("currentQty");


-- ── 17. WorkflowType / RiskLevel lookup tables ────────────────
-- These match Prisma models with no @@map — table names are quoted
CREATE TABLE IF NOT EXISTS "WorkflowType" (
    "id"          TEXT NOT NULL,
    "name"        TEXT NOT NULL,
    "description" TEXT,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "RiskLevel" (
    "id"       TEXT    NOT NULL,
    "name"     TEXT    NOT NULL,
    "minValue" INTEGER NOT NULL,
    "maxValue" INTEGER NOT NULL,
    PRIMARY KEY ("id")
);


-- ── 18. Seed: permissive state transition rule ────────────────
-- Allows system/agent actors to transition any event to CLOSED
-- regardless of prior state (handles kitchen-sync path where
-- events are born from Python pipeline, not TS state machine).
-- ON CONFLICT: safe to re-run — skips if rule already exists.
INSERT INTO state_transition_rules (
    "id",
    "tenantId",
    "entityType",
    "fromState",
    "toState",
    "preConditions",
    "requiredFields",
    "allowedActors",
    "requiresApproval",
    "isActive",
    "priority",
    "successMessage"
)
SELECT
    gen_random_uuid()::text,
    (SELECT id::text FROM tenants ORDER BY created_at LIMIT 1),
    'event',
    '',
    'CLOSED',
    '{}'::jsonb,
    '{}'::text[],
    ARRAY['system', 'agent', 'api', 'webhook']::text[],
    false,
    true,
    100,
    'Event closed after financial sync'
WHERE EXISTS (SELECT 1 FROM tenants)
ON CONFLICT ("tenantId", "entityType", "fromState", "toState") DO NOTHING;


-- ── Verify ────────────────────────────────────────────────────
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
--   AND table_name IN (
--     'agent_runs','agent_steps','tool_calls','approval_requests',
--     'memory_items','domain_rules','artifacts','cost_events',
--     'system_events','domain_logs','event_processors','event_snapshots',
--     'domain_integrity_checks','integrity_check_logs','recipes','inventory_items'
--   )
-- ORDER BY table_name;
-- Expected: 16 rows
