// ============================================================
// Verify RBAC — tests hasPermission + login + JWT payload.
// Runs against the local DB (users seeded by scripts/seed_users.ts).
// ============================================================
import jwt from "jsonwebtoken";
import { prisma } from "../src/db";
import { config } from "../src/config/env";
import { userService } from "../src/services/user-service";
import {
  hasPermission,
  ROLES,
  type Role,
  type Permission,
  type JwtPayload,
} from "../src/middleware/auth";

type Expectation = [Permission, readonly Role[]];

const EXPECTED: Expectation[] = [
  ["operations.overview.read",     ["operator", "manager", "finance", "kitchen", "admin"]],
  ["operations.event.write",       ["manager", "admin"]],
  ["operations.consumption.write", ["operator", "manager", "kitchen", "admin"]],
  ["operations.production.write",  ["manager", "kitchen", "admin"]],
  ["operations.reconcile.execute", ["manager", "finance", "admin"]],
  ["approvals.low.approve",        ["manager", "finance", "admin"]],
  ["approvals.high.approve",       ["finance", "admin"]],
  ["intelligence.read",            ["manager", "finance", "admin"]],
  ["users.manage",                 ["admin"]],
];

function line() {
  console.log("─".repeat(72));
}

async function testMatrix() {
  console.log("\n🔐 [1] Permission matrix check");
  line();
  let failures = 0;
  for (const [perm, allowed] of EXPECTED) {
    for (const role of ROLES) {
      const got = hasPermission(role, perm);
      const want = allowed.includes(role);
      const mark = got === want ? "✓" : "✗";
      if (got !== want) failures++;
      console.log(
        `  ${mark} ${perm.padEnd(32)} ${role.padEnd(9)} want=${want} got=${got}`
      );
    }
  }
  if (failures > 0) throw new Error(`${failures} permission mismatches`);
  console.log("✅ Matrix OK");
}

async function testLogins() {
  console.log("\n🔑 [2] Login each seeded user + inspect JWT payload");
  line();
  const emails = [
    "admin@orkestra.local",
    "manager@orkestra.local",
    "finance@orkestra.local",
    "operator@orkestra.local",
    "kitchen@orkestra.local",
  ];
  const passwords: Record<string, string> = {
    "admin@orkestra.local":    "admin1234",
    "manager@orkestra.local":  "manager1234",
    "finance@orkestra.local":  "finance1234",
    "operator@orkestra.local": "operator1234",
    "kitchen@orkestra.local":  "kitchen1234",
  };
  for (const email of emails) {
    const { user, token } = await userService.login(email, passwords[email]);
    const decoded = jwt.verify(token, config.JWT_SECRET) as JwtPayload;
    const sample = {
      id: decoded.id,
      email: decoded.email,
      name: decoded.name,
      role: decoded.role,
      tenantId: decoded.tenantId,
      exp: decoded.exp,
    };
    console.log(
      `  • ${user.role.padEnd(9)} ${user.email.padEnd(30)} token_len=${token.length} exp=${decoded.exp}`
    );
    console.log("    payload =", JSON.stringify(sample));
    if (decoded.id !== user.id || decoded.tenantId !== user.tenantId) {
      throw new Error("JWT payload mismatch");
    }
  }
  console.log("✅ All logins OK, payloads valid");
}

async function testWrongPassword() {
  console.log("\n🚫 [3] Wrong password rejected");
  line();
  try {
    await userService.login("admin@orkestra.local", "wrong");
    throw new Error("Login should have failed");
  } catch (err: any) {
    if (err?.code === "UNAUTHORIZED") {
      console.log("✅ Wrong password → 401 as expected");
    } else {
      throw err;
    }
  }
}

async function testAuditLogSanity() {
  console.log("\n🧾 [4] Audit table is writable");
  line();
  const before = await prisma.auditLog.count();
  await prisma.auditLog.create({
    data: {
      tenantId: config.DEFAULT_TENANT_ID,
      action: "test",
      resource: "verify_rbac",
      method: "POST",
      path: "/verify-rbac",
      statusCode: 200,
    },
  });
  const after = await prisma.auditLog.count();
  console.log(`  audit_logs rows ${before} → ${after}`);
  if (after !== before + 1) throw new Error("audit_log write failed");
  console.log("✅ Audit table operational");
}

async function main() {
  console.log("\n🛡️  RBAC E2E verification");
  console.log(`tenant=${config.DEFAULT_TENANT_ID}`);

  await testMatrix();
  await testLogins();
  await testWrongPassword();
  await testAuditLogSanity();

  console.log("\n🎉 All RBAC checks passed.\n");
}

main()
  .catch((err) => {
    console.error("❌ verify_rbac failed", err);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
