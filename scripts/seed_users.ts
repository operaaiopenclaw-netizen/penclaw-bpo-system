// ============================================================
// Seed one user per role for the DEFAULT_TENANT.
// Idempotent (upsert by email).
// Dev-only passwords — rotate via /users PATCH before any real use.
// ============================================================
import bcrypt from "bcrypt";
import { prisma } from "../src/db";
import { config } from "../src/config/env";
import { ROLES } from "../src/middleware/auth";

const TENANT = config.DEFAULT_TENANT_ID;

const SEEDS = [
  { email: "admin@orkestra.local",    name: "Admin Seed",    role: "admin",    password: "admin1234" },
  { email: "manager@orkestra.local",  name: "Manager Seed",  role: "manager",  password: "manager1234" },
  { email: "finance@orkestra.local",  name: "Finance Seed",  role: "finance",  password: "finance1234" },
  { email: "operator@orkestra.local", name: "Operator Seed", role: "operator", password: "operator1234" },
  { email: "kitchen@orkestra.local",  name: "Kitchen Seed",  role: "kitchen",  password: "kitchen1234" },
];

async function main() {
  console.log(`🌱 Seeding users for tenant=${TENANT}`);
  for (const seed of SEEDS) {
    if (!(ROLES as readonly string[]).includes(seed.role)) {
      throw new Error(`Invalid role: ${seed.role}`);
    }
    const passwordHash = await bcrypt.hash(seed.password, 10);
    const user = await prisma.user.upsert({
      where: { email: seed.email },
      update: {
        name: seed.name,
        role: seed.role,
        tenantId: TENANT,
        isActive: true,
      },
      create: {
        tenantId: TENANT,
        email: seed.email,
        name: seed.name,
        role: seed.role,
        passwordHash,
      },
      select: { id: true, email: true, role: true },
    });
    console.log(`  • ${user.role.padEnd(9)} ${user.email}  id=${user.id}`);
  }
  console.log("\n✅ 5 users seeded");
}

main()
  .catch((err) => {
    console.error("❌ seed_users failed", err);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
