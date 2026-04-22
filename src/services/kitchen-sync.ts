// ============================================================
// KITCHEN SYNC SERVICE
// Bridge: Python pipeline outputs → real PostgreSQL `events` table.
//
// Uses prisma.$queryRaw / $executeRaw (raw SQL) to talk directly
// to snake_case column names in the real DB, bypassing the Prisma
// ORM model (which has no @map decorators and would generate
// wrong camelCase column names against the actual schema).
//
// Requires V004__add_kitchen_bridge.sql to have been applied first.
// ============================================================

import fs from "fs/promises";
import path from "path";
import { prisma } from "../db";
import { logger } from "../utils/logger";
import { stateManager } from "../state-machine/state-manager";
import { agentRunService } from "./agent-run-service";

const PROJECT_ROOT = path.resolve(__dirname, "../../");
const DRE_SUMMARY_PATH = path.join(PROJECT_ROOT, "kitchen_data", "dre_summary.json");
const CMV_LOG_PATH    = path.join(PROJECT_ROOT, "kitchen_data", "cmv_log.json");

// ── Python output shapes ─────────────────────────────────────

interface DreSummaryEvent {
  event_id:     string;
  revenue:      number;
  cmv:          number;
  gross_margin: number; // e.g. 45.64  (percent)
  net_margin:   number; // e.g. 1.35   (percent)
  status:       string;
}

interface DreSummary {
  events_detail: DreSummaryEvent[];
}

interface CmvLogEvent {
  event_id?:        string;
  company?:         string;
  event_type?:      string;
  revenue:          number;
  cmv_total:        number;
  cmv_pct_revenue:  number;
}

interface CmvLog {
  eventos: Record<string, CmvLogEvent>;
}

// ── Internal event record ─────────────────────────────────────

interface EventFinancials {
  revenue:     number;
  cmvTotal:    number;
  marginPct:   number;  // decimal, e.g. 0.4564
  netProfit:   number;
  companyName: string;
  eventType:   string;
}

// ── Public result shape ───────────────────────────────────────

export interface SyncResult {
  success:            boolean;
  eventsProcessed:    number;
  eventsCreated:      number;
  eventsUpdated:      number;
  statesTransitioned: number;
  statesSkipped:      number;
  workflowsQueued:    number;
  workflowsFailed:    number;
  errors:             string[];
}

// ── File helpers ──────────────────────────────────────────────

async function readJson<T>(filePath: string): Promise<T | null> {
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch (err) {
    const code = (err as NodeJS.ErrnoException).code;
    if (code === "ENOENT") {
      logger.warn("KitchenSync: file not found", { path: filePath });
    } else {
      logger.error("KitchenSync: failed to read file", { path: filePath, error: err });
    }
    return null;
  }
}

// ── DB helpers (raw SQL) ──────────────────────────────────────

/** Returns the DB row id and tenant_id if an event with this event_id already exists. */
async function findEventByEventId(
  eventId: string
): Promise<{ rowId: string; tenantId: string } | null> {
  const rows = await prisma.$queryRaw<{ id: string; tenant_id: string }[]>`
    SELECT id, tenant_id FROM events WHERE event_id = ${eventId} LIMIT 1
  `;
  return rows.length > 0 ? { rowId: rows[0].id, tenantId: rows[0].tenant_id } : null;
}

/** Update financial columns on an existing row. */
async function updateEventFinancials(eventId: string, f: EventFinancials): Promise<void> {
  await prisma.$executeRaw`
    UPDATE events
    SET
      company_name  = ${f.companyName},
      revenue_total = ${f.revenue},
      cmv_total     = ${f.cmvTotal},
      margin_pct    = ${f.marginPct},
      net_profit    = ${f.netProfit},
      updated_at    = NOW()
    WHERE event_id = ${eventId}
  `;
}

/**
 * Resolve tenant_id + cost_center_id before inserting.
 *
 * Priority for cost_center:
 *   A) name ILIKE matching companyName keywords (opera, la orana)
 *   B) first cost_center that belongs to the resolved tenant
 *
 * Throws if neither tenant nor cost_center can be resolved.
 */
async function resolveTenantAndCostCenter(
  companyName: string
): Promise<{ tenantId: string; costCenterId: string }> {
  // 1. Resolve tenant (always use the first/default tenant)
  const tenantRows = await prisma.$queryRaw<{ id: string }[]>`
    SELECT id FROM tenants ORDER BY created_at LIMIT 1
  `;
  if (tenantRows.length === 0) {
    throw new Error("KitchenSync: no tenant found in DB — run V001 baseline migration");
  }
  const tenantId = tenantRows[0].id;

  // 2a. Try to match cost center by companyName keyword
  const nameLower = companyName.toLowerCase();
  let keyword: string | null = null;
  if (nameLower.includes("opera"))    keyword = "%opera%";
  if (nameLower.includes("la_orana") || nameLower.includes("la orana")) keyword = "%la orana%";

  if (keyword !== null) {
    const ccRows = await prisma.$queryRaw<{ id: string }[]>`
      SELECT id FROM cost_centers
      WHERE tenant_id = ${tenantId}::uuid
        AND name ILIKE ${keyword}
        AND active = TRUE
      LIMIT 1
    `;
    if (ccRows.length > 0) {
      return { tenantId, costCenterId: ccRows[0].id };
    }
    logger.warn("KitchenSync: no cost_center matched keyword — falling back to first", {
      companyName,
      keyword,
    });
  }

  // 2b. Fallback: first active cost center for this tenant
  const fallbackRows = await prisma.$queryRaw<{ id: string }[]>`
    SELECT id FROM cost_centers
    WHERE tenant_id = ${tenantId}::uuid
      AND active = TRUE
    ORDER BY created_at
    LIMIT 1
  `;
  if (fallbackRows.length === 0) {
    throw new Error(
      `KitchenSync: no cost_center found for tenant ${tenantId} — seed cost_centers first`
    );
  }

  return { tenantId, costCenterId: fallbackRows[0].id };
}

/**
 * Insert a new event row.
 * Resolves tenant_id and cost_center_id before inserting.
 * Returns { rowId, tenantId } of the created row for state machine use.
 */
async function insertEvent(
  eventId: string,
  f: EventFinancials
): Promise<{ rowId: string; tenantId: string }> {
  const { tenantId, costCenterId } = await resolveTenantAndCostCenter(f.companyName);

  logger.info("KitchenSync: resolved IDs for insert", {
    eventId,
    tenantId,
    costCenterId,
  });

  const inserted = await prisma.$queryRaw<{ id: string }[]>`
    INSERT INTO events (
      id,
      tenant_id,
      cost_center_id,
      name,
      event_type,
      company_name,
      status,
      revenue_total,
      cmv_total,
      margin_pct,
      net_profit,
      event_id,
      created_at,
      updated_at
    ) VALUES (
      gen_random_uuid(),
      ${tenantId}::uuid,
      ${costCenterId}::uuid,
      ${eventId},
      ${f.eventType},
      ${f.companyName},
      'COMPLETED',
      ${f.revenue},
      ${f.cmvTotal},
      ${f.marginPct},
      ${f.netProfit},
      ${eventId},
      NOW(),
      NOW()
    )
    RETURNING id
  `;

  return { rowId: inserted[0].id, tenantId };
}

// ── State machine integration ─────────────────────────────────

/**
 * Transitions an event to CLOSED in the state machine after a successful sync.
 *
 * Idempotency rules:
 *  - already CLOSED → "skipped" (no duplicate transition)
 *  - incomplete financials → "missing_data" (no transition attempted)
 *  - any other state (or no state) → transition to CLOSED
 *
 * autoValidate: false bypasses the "must come from EXECUTING" integrity check,
 * because these events were executed in the real world via the Python pipeline,
 * not through the TypeScript state machine.
 */
async function transitionEventToClosed(
  rowId:     string,
  tenantId:  string,
  financials: EventFinancials
): Promise<"transitioned" | "skipped" | "missing_data"> {
  // Guard: all three financial fields must be present and non-zero
  if (!financials.revenue || !financials.cmvTotal || !financials.marginPct) {
    logger.warn("KitchenSync: skipping state transition — incomplete financials", { rowId });
    return "missing_data";
  }

  // Check current state — skip if already CLOSED (idempotent)
  const current = await stateManager.getCurrentState(tenantId, "event", rowId);
  if (current?.state === "CLOSED") {
    logger.info("KitchenSync: event already CLOSED — skipping", { rowId });
    return "skipped";
  }

  const transition = await stateManager.transition({
    tenantId,
    entityType:    "event",
    entityId:      rowId,
    toState:       "CLOSED",
    reason:        "Financial data synced from kitchen pipeline",
    actorType:     "system",
    actorId:       "kitchen-sync",
    source:        "kitchen_sync",
    autoValidate:  false,   // bypass "must be EXECUTING" check — event ran in Python world
  });

  if (transition.success) {
    logger.info("KitchenSync: transitioned to CLOSED", { rowId, tenantId });
    return "transitioned";
  }

  // Non-fatal: log and skip rather than failing the whole sync
  logger.warn("KitchenSync: state transition failed — skipping", {
    rowId,
    error:     transition.error,
    blockedBy: transition.blockedBy,
  });
  return "skipped";
}

// ── Core sync logic ───────────────────────────────────────────

export async function syncKitchenFinancials(filterEventId?: string): Promise<SyncResult> {
  const result: SyncResult = {
    success:            true,
    eventsProcessed:    0,
    eventsCreated:      0,
    eventsUpdated:      0,
    statesTransitioned: 0,
    statesSkipped:      0,
    workflowsQueued:    0,
    workflowsFailed:    0,
    errors:             [],
  };

  // 1. Read source files
  const dreSummary = await readJson<DreSummary>(DRE_SUMMARY_PATH);
  const cmvLog     = await readJson<CmvLog>(CMV_LOG_PATH);

  if (!dreSummary?.events_detail?.length) {
    logger.warn("KitchenSync: dre_summary.json missing or empty — trying cmv_log.json fallback");
  }

  // 2. Build unified event map
  //    dre_summary is authoritative for financials (has net margin)
  //    cmv_log provides company/event_type metadata
  const cmvIndex = cmvLog?.eventos ?? {};

  const eventMap = new Map<string, EventFinancials>();

  if (dreSummary?.events_detail) {
    for (const ev of dreSummary.events_detail) {
      if (filterEventId && ev.event_id !== filterEventId) continue;
      const meta = cmvIndex[ev.event_id];
      eventMap.set(ev.event_id, {
        revenue:     ev.revenue,
        cmvTotal:    ev.cmv,
        marginPct:   ev.gross_margin / 100,  // 45.64 → 0.4564
        netProfit:   ev.revenue * (ev.net_margin / 100),
        companyName: meta?.company   ?? "Orkestra",
        eventType:   meta?.event_type ?? "",
      });
    }
  }

  // Fill any events present only in cmv_log
  for (const [eventId, ev] of Object.entries(cmvIndex)) {
    if (filterEventId && eventId !== filterEventId) continue;
    if (!eventMap.has(eventId)) {
      eventMap.set(eventId, {
        revenue:     ev.revenue,
        cmvTotal:    ev.cmv_total,
        marginPct:   1 - ev.cmv_pct_revenue / 100,
        netProfit:   0,
        companyName: ev.company    ?? "Orkestra",
        eventType:   ev.event_type ?? "",
      });
    }
  }

  if (eventMap.size === 0) {
    logger.warn("KitchenSync: no events to sync");
    result.success = false;
    result.errors.push("No data found in dre_summary.json or cmv_log.json");
    return result;
  }

  logger.info("KitchenSync: starting sync", {
    eventsFound: eventMap.size,
    filter: filterEventId ?? "all",
  });

  // 3. Persist: update if exists, insert if not — then transition state
  for (const [eventId, financials] of eventMap.entries()) {
    result.eventsProcessed++;

    let rowId:    string | null = null;
    let tenantId: string | null = null;

    try {
      const existing = await findEventByEventId(eventId);

      if (existing) {
        rowId    = existing.rowId;
        tenantId = existing.tenantId;
        await updateEventFinancials(eventId, financials);
        logger.info("KitchenSync: updated", {
          eventId,
          revenue:     financials.revenue,
          grossMargin: (financials.marginPct * 100).toFixed(1) + "%",
        });
        result.eventsUpdated++;
      } else {
        const created = await insertEvent(eventId, financials);
        rowId    = created.rowId;
        tenantId = created.tenantId;
        logger.info("KitchenSync: created", {
          eventId,
          companyName: financials.companyName,
          revenue:     financials.revenue,
          grossMargin: (financials.marginPct * 100).toFixed(1) + "%",
        });
        result.eventsCreated++;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      logger.error("KitchenSync: failed to persist", { eventId, error: msg });
      result.errors.push(`${eventId}: ${msg}`);
      continue; // skip state transition if persist failed
    }

    // 4. Transition to CLOSED (non-fatal — failures are counted, not thrown)
    try {
      const stateOutcome = await transitionEventToClosed(rowId!, tenantId!, financials);
      if (stateOutcome === "transitioned") {
        result.statesTransitioned++;
        // 5. Fire post_event_closure workflow — fire-and-forget, never blocks sync
        agentRunService.create({
          companyId: tenantId!,
          workflowType: "post_event_closure",
          input: {
            eventId,                          // kitchen event ID (EVT001 etc.)
            rowId:        rowId!,             // DB UUID of the events row
            companyName:  financials.companyName,
            eventType:    financials.eventType,
            revenueForecast: financials.revenue,
            cmvTotal:     financials.cmvTotal,
            marginPct:    financials.marginPct,
            netProfit:    financials.netProfit,
            source:       "kitchen_sync",
          }
        }).then(run => {
          result.workflowsQueued++;
          logger.info("KitchenSync: post_event_closure queued", { eventId, runId: run.runId });
        }).catch(err => {
          result.workflowsFailed++;
          const msg = err instanceof Error ? err.message : String(err);
          logger.error("KitchenSync: failed to queue post_event_closure", { eventId, error: msg });
          result.errors.push(`workflow:${eventId}: ${msg}`);
        });
      } else {
        result.statesSkipped++;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      logger.error("KitchenSync: state transition threw unexpectedly", { eventId, rowId, error: msg });
      result.statesSkipped++;
      // do NOT push to result.errors — persist succeeded, state is best-effort
    }
  }

  result.success = result.errors.length === 0;

  logger.info("KitchenSync: complete", {
    eventsProcessed:    result.eventsProcessed,
    eventsCreated:      result.eventsCreated,
    eventsUpdated:      result.eventsUpdated,
    statesTransitioned: result.statesTransitioned,
    statesSkipped:      result.statesSkipped,
    errors:             result.errors.length,
  });

  return result;
}
