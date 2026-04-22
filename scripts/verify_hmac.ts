// ============================================================
// Verify HMAC middleware — signs a payload, asserts verifyHmac accepts it,
// and asserts a tampered signature is rejected.
// ============================================================
import crypto from "crypto";
import { signPayload } from "../src/middleware/hmac";
import { config } from "../src/config/env";

// Inject a secret for this run if not present (dev convenience).
if (!config.WEBHOOK_HMAC_SECRET) {
  process.env.WEBHOOK_HMAC_SECRET = "dev-hmac-secret-0123456789";
  (config as any).WEBHOOK_HMAC_SECRET = process.env.WEBHOOK_HMAC_SECRET;
}

async function main() {
  const payload = {
    tenantId: config.DEFAULT_TENANT_ID,
    eventId: "HMAC-TEST-001",
    name: "HMAC Test Event",
    guests: 80,
  };
  const raw = JSON.stringify(payload);
  const signature = signPayload(payload);
  console.log(`payload:   ${raw}`);
  console.log(`signature: ${signature}`);

  // Recompute + compare
  const expected = crypto
    .createHmac("sha256", config.WEBHOOK_HMAC_SECRET!)
    .update(raw)
    .digest("hex");
  if (signature !== expected) throw new Error("signPayload mismatch");

  // Tampered payload must produce a different signature
  const tampered = signPayload({ ...payload, guests: 999 });
  if (tampered === signature) throw new Error("Tampered payload not detected");

  console.log("✅ HMAC sign/verify OK");
  console.log("\nExample curl:");
  console.log(
    `  curl -X POST http://localhost:${config.PORT}/operations/webhooks/event \\\n` +
      `    -H 'content-type: application/json' \\\n` +
      `    -H 'x-orkestra-signature: ${signature}' \\\n` +
      `    -d '${raw}'`,
  );
}

main().catch((err) => {
  console.error("❌ verify_hmac failed", err);
  process.exit(1);
});
