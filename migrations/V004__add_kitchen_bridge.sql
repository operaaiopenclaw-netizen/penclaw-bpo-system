-- ============================================================
-- MIGRATION V004 — KITCHEN BRIDGE
-- Adds financial tracking columns to existing `events` table.
-- All statements are idempotent (IF NOT EXISTS / IF NULL).
-- Safe: no drops, no resets, no FK changes.
-- ============================================================

-- 1. Add missing columns
ALTER TABLE events ADD COLUMN IF NOT EXISTS event_id     TEXT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS company_name TEXT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS revenue_total NUMERIC(14,2);
ALTER TABLE events ADD COLUMN IF NOT EXISTS cmv_total     NUMERIC(14,2);
ALTER TABLE events ADD COLUMN IF NOT EXISTS margin_pct    NUMERIC(8,4);
ALTER TABLE events ADD COLUMN IF NOT EXISTS net_profit    NUMERIC(14,2);
ALTER TABLE events ADD COLUMN IF NOT EXISTS updated_at    TIMESTAMPTZ DEFAULT NOW();

-- 2. Backfill event_id for pre-existing rows so no NULLs exist
--    Uses id::text as a stable, unique default value
UPDATE events
SET event_id = id::text
WHERE event_id IS NULL;

-- 3. Partial unique index — only non-null rows (safe for legacy inserts
--    that don't set event_id, while still allowing ON CONFLICT lookups
--    from the bridge)
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_event_id
    ON events (event_id)
    WHERE event_id IS NOT NULL;

-- Verify: check column list after migration
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'events' ORDER BY ordinal_position;
