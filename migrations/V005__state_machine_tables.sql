-- ============================================================
-- MIGRATION V005 — STATE MACHINE TABLES
--
-- Creates the minimum database layer for the existing
-- TypeScript StateManager (src/state-machine/state-manager.ts).
--
-- IMPORTANT — COLUMN NAMING:
--   Prisma models have NO @map field decorators, so Prisma quotes
--   and uses camelCase column names verbatim in every generated SQL
--   query. Column names here MUST match Prisma field names exactly
--   (e.g. "tenantId", NOT "tenant_id").
--
-- TABLES CREATED:
--   entity_states          — current + historical state per entity
--   state_transitions      — full transition audit log
--   state_transition_rules — rule lookup (queried on every transition,
--                            can stay empty; empty = falls through to
--                            built-in isValidTransition() logic)
--
-- Safe: idempotent, no drops, no resets.
-- ============================================================

-- ── 1. entity_states ──────────────────────────────────────────
-- Used by: getCurrentState, setInitialState, transition, rollback
-- Operations: findFirst, create, updateMany

CREATE TABLE IF NOT EXISTS entity_states (
    "id"            TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "tenantId"      TEXT        NOT NULL,
    "entityType"    TEXT        NOT NULL,
    "entityId"      TEXT        NOT NULL,
    "currentState"  TEXT        NOT NULL,
    "previousState" TEXT,
    "enteredAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "enteredBy"     TEXT,
    "actorType"     TEXT        NOT NULL DEFAULT 'system',
    "reason"        TEXT,
    "source"        TEXT,
    "version"       INTEGER     NOT NULL DEFAULT 1,
    "validFrom"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "validUntil"    TIMESTAMPTZ,
    "isCurrent"     BOOLEAN     NOT NULL DEFAULT TRUE,
    "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

-- Partial unique index: only ONE current state per entity is allowed.
-- Intentionally NOT the full @@unique([tenantId, entityType, entityId, isCurrent])
-- from the Prisma schema — that would block multiple historical (isCurrent=FALSE)
-- rows for the same entity after the second transition.
CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_states_one_current
    ON entity_states ("tenantId", "entityType", "entityId")
    WHERE "isCurrent" = TRUE;

-- Supporting indexes (match Prisma @@index declarations)
CREATE INDEX IF NOT EXISTS idx_entity_states_lookup
    ON entity_states ("tenantId", "entityType", "entityId");

CREATE INDEX IF NOT EXISTS idx_entity_states_current_state
    ON entity_states ("tenantId", "currentState", "isCurrent");

CREATE INDEX IF NOT EXISTS idx_entity_states_type_state
    ON entity_states ("tenantId", "entityType", "currentState");

CREATE INDEX IF NOT EXISTS idx_entity_states_validity
    ON entity_states ("validFrom", "validUntil");


-- ── 2. state_transitions ──────────────────────────────────────
-- Used by: logTransition (called inside transition + rollback)
-- Operations: create, findMany, updateMany

CREATE TABLE IF NOT EXISTS state_transitions (
    "id"               TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "tenantId"         TEXT        NOT NULL,
    "entityType"       TEXT        NOT NULL,
    "entityId"         TEXT        NOT NULL,
    "fromState"        TEXT        NOT NULL DEFAULT '',
    "toState"          TEXT        NOT NULL DEFAULT '',
    "actorType"        TEXT        NOT NULL DEFAULT 'system',
    "actorId"          TEXT,
    "reason"           TEXT,
    "triggerEvent"     TEXT,
    "source"           TEXT,
    "ipAddress"        TEXT,
    "validationResult" JSONB,
    "warnings"         TEXT[]      NOT NULL DEFAULT '{}',
    "blockedBy"        TEXT,
    "systemEventId"    TEXT,
    "attemptedAt"      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "completedAt"      TIMESTAMPTZ,
    "durationMs"       INTEGER,
    "status"           TEXT        NOT NULL DEFAULT 'completed',
    "errorMessage"     TEXT,
    "resultingStateId" TEXT,
    PRIMARY KEY ("id")
);

-- Supporting indexes (match Prisma @@index declarations)
CREATE INDEX IF NOT EXISTS idx_state_transitions_entity
    ON state_transitions ("tenantId", "entityType", "entityId", "attemptedAt");

CREATE INDEX IF NOT EXISTS idx_state_transitions_states
    ON state_transitions ("tenantId", "fromState", "toState");

CREATE INDEX IF NOT EXISTS idx_state_transitions_actor
    ON state_transitions ("tenantId", "actorType", "actorId");

CREATE INDEX IF NOT EXISTS idx_state_transitions_system_event
    ON state_transitions ("systemEventId");

CREATE INDEX IF NOT EXISTS idx_state_transitions_attempted
    ON state_transitions ("attemptedAt");


-- ── 3. state_transition_rules ─────────────────────────────────
-- Used by: transition() — findFirst on every call
-- Operations: findFirst ONLY (never written from the bridge)
-- Purpose: custom per-tenant overrides. Empty table = all transitions
--          fall through to the built-in isValidTransition() code path.

CREATE TABLE IF NOT EXISTS state_transition_rules (
    "id"               TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    "tenantId"         TEXT        NOT NULL,
    "entityType"       TEXT        NOT NULL,
    "fromState"        TEXT        NOT NULL,
    "toState"          TEXT        NOT NULL,
    "preConditions"    JSONB       NOT NULL DEFAULT '{}',
    "requiredFields"   TEXT[]      NOT NULL DEFAULT '{}',
    "allowedActors"    TEXT[]      NOT NULL DEFAULT '{}',
    "requiresApproval" BOOLEAN     NOT NULL DEFAULT FALSE,
    "approvalLevel"    TEXT,
    "autoActions"      JSONB,
    "sideEffects"      JSONB,
    "isActive"         BOOLEAN     NOT NULL DEFAULT TRUE,
    "priority"         INTEGER     NOT NULL DEFAULT 100,
    "successMessage"   TEXT        NOT NULL DEFAULT 'Transição realizada com sucesso',
    "failureMessage"   TEXT,
    "createdAt"        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_state_transition_rules_unique
    ON state_transition_rules ("tenantId", "entityType", "fromState", "toState");

CREATE INDEX IF NOT EXISTS idx_state_transition_rules_active
    ON state_transition_rules ("tenantId", "entityType", "isActive");


-- ── Verify after running ──────────────────────────────────────
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
--   AND table_name IN ('entity_states','state_transitions','state_transition_rules')
-- ORDER BY table_name;
-- Expected: 3 rows
