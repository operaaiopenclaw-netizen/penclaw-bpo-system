// ============================================================
// Post-deploy smoke test.
// Usage:
//   API_URL=https://api.orkestra.com \
//   ADMIN_EMAIL=admin@orkestra.local ADMIN_PASSWORD=… \
//   OPERATOR_EMAIL=operator@orkestra.local OPERATOR_PASSWORD=… \
//   npx tsx scripts/verify_deployment.ts
//
// Exits non-zero if any check fails. Intended for CI or manual post-deploy.
// ============================================================

const BASE = process.env.API_URL ?? "http://localhost:3010";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? "admin@orkestra.local";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD ?? "admin1234";
const OPERATOR_EMAIL = process.env.OPERATOR_EMAIL ?? "operator@orkestra.local";
const OPERATOR_PASSWORD = process.env.OPERATOR_PASSWORD ?? "operator1234";

let pass = 0;
let fail = 0;

async function check(
  name: string,
  fn: () => Promise<void>,
): Promise<void> {
  try {
    await fn();
    console.log(`  ✓ ${name}`);
    pass++;
  } catch (err) {
    console.log(`  ✗ ${name} — ${err instanceof Error ? err.message : String(err)}`);
    fail++;
  }
}

async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`login ${email} → HTTP ${res.status}`);
  const { token } = (await res.json()) as { token: string };
  return token;
}

async function main() {
  console.log(`🔎 verify_deployment → ${BASE}\n`);

  await check("GET /health → 200", async () => {
    const r = await fetch(`${BASE}/health`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
  });

  await check("GET /ready → 200 + all checks green", async () => {
    const r = await fetch(`${BASE}/ready`);
    const body = (await r.json()) as any;
    if (!r.ok || !body.ok) {
      throw new Error(`not ready: ${JSON.stringify(body.checks)}`);
    }
  });

  await check("POST /auth/login (bad creds) → 401", async () => {
    const r = await fetch(`${BASE}/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        email: "does-not-exist@orkestra.local",
        password: "wrong-password",
      }),
    });
    if (r.status !== 401) throw new Error(`expected 401, got ${r.status}`);
  });

  let adminToken: string | null = null;
  await check("POST /auth/login (admin) → 200", async () => {
    adminToken = await login(ADMIN_EMAIL, ADMIN_PASSWORD);
    if (!adminToken) throw new Error("no token");
  });

  let operatorToken: string | null = null;
  await check("POST /auth/login (operator) → 200", async () => {
    operatorToken = await login(OPERATOR_EMAIL, OPERATOR_PASSWORD);
    if (!operatorToken) throw new Error("no token");
  });

  await check("GET /auth/me (admin) → 200 with role=admin", async () => {
    const r = await fetch(`${BASE}/auth/me`, {
      headers: { authorization: `Bearer ${adminToken}` },
    });
    const body = (await r.json()) as any;
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    if (body.user?.role !== "admin") {
      throw new Error(`role=${body.user?.role}, expected admin`);
    }
  });

  await check("GET /users (admin) → 200", async () => {
    const r = await fetch(`${BASE}/users`, {
      headers: { authorization: `Bearer ${adminToken}` },
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
  });

  await check("GET /users (operator) → 403", async () => {
    const r = await fetch(`${BASE}/users`, {
      headers: { authorization: `Bearer ${operatorToken}` },
    });
    if (r.status !== 403) throw new Error(`expected 403, got ${r.status}`);
  });

  await check(
    "POST /operations/alerts/evaluate (operator) → 403",
    async () => {
      const r = await fetch(`${BASE}/operations/alerts/evaluate`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${operatorToken}`,
        },
        body: JSON.stringify({ eventId: "smoke-test" }),
      });
      if (r.status !== 403) throw new Error(`expected 403, got ${r.status}`);
    },
  );

  await check(
    "POST /operations/reconcile (cross-tenant) → 403",
    async () => {
      const r = await fetch(`${BASE}/operations/reconcile`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${adminToken}`,
        },
        body: JSON.stringify({
          tenantId: "SOME-OTHER-TENANT",
          eventId: "x",
        }),
      });
      // admin may impersonate only with x-impersonate-tenant header — without it, 403
      if (r.status !== 403) throw new Error(`expected 403, got ${r.status}`);
    },
  );

  console.log(`\n${fail === 0 ? "✅" : "❌"} ${pass} passed, ${fail} failed`);
  if (fail > 0) process.exit(1);
}

main().catch((err) => {
  console.error("verify_deployment crashed", err);
  process.exit(2);
});
