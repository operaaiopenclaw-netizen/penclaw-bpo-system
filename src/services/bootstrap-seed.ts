import bcrypt from "bcrypt";
import { prisma } from "../db";
import { config } from "../config/env";
import { logger } from "../utils/logger";

const SEED_USERS = [
  { email: "admin@orkestra.local",    name: "Admin Seed",    role: "admin",    password: "admin1234" },
  { email: "manager@orkestra.local",  name: "Manager Seed",  role: "manager",  password: "manager1234" },
  { email: "finance@orkestra.local",  name: "Finance Seed",  role: "finance",  password: "finance1234" },
  { email: "operator@orkestra.local", name: "Operator Seed", role: "operator", password: "operator1234" },
  { email: "kitchen@orkestra.local",  name: "Kitchen Seed",  role: "kitchen",  password: "kitchen1234" },
];

// Creates the 5 seed users ONLY when the users table is empty. Idempotent and
// safe on every boot — existing deploys are a no-op. Never overwrites passwords
// (unlike scripts/seed_users.ts, which upserts and is meant for dev).
export async function bootstrapSeedIfEmpty(): Promise<void> {
  const count = await prisma.user.count();
  if (count > 0) {
    logger.info({ users: count }, "Bootstrap: users already present, skipping seed");
    return;
  }

  logger.warn("Bootstrap: users table empty, seeding 5 default accounts");
  for (const seed of SEED_USERS) {
    const passwordHash = await bcrypt.hash(seed.password, 10);
    await prisma.user.create({
      data: {
        tenantId: config.DEFAULT_TENANT_ID,
        email: seed.email,
        name: seed.name,
        role: seed.role,
        passwordHash,
      },
    });
  }
  logger.warn(
    { emails: SEED_USERS.map((s) => s.email) },
    "Bootstrap: seeded 5 users with default passwords — ROTATE via PATCH /users before exposing the API publicly",
  );
}
