import dotenv from "dotenv";
import { z } from "zod";
import { join } from "path";

// Load .env file
dotenv.config();

// Define schema with Zod for type safety
const envSchema = z.object({
  // App
  PORT: z.coerce.number().default(3333),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  
  // Database
  DATABASE_URL: z.string().min(1, "DATABASE_URL is required"),

  // Redis (BullMQ). redis:// for plaintext, rediss:// for TLS (Upstash/Fly).
  REDIS_URL: z.string().default("redis://127.0.0.1:6379"),
  
  // Security
  JWT_SECRET: z.string().min(32, "JWT_SECRET must be at least 32 characters"),
  JWT_REFRESH_SECRET: z.string().min(32, "JWT_REFRESH_SECRET is required"),
  JWT_EXPIRES_IN: z.string().default("1d"),
  
  // Storage
  ARTIFACTS_DIR: z.string().default("./storage/artifacts"),
  STORAGE_TYPE: z.enum(["local", "s3"]).default("local"),
  
  // Logging
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
  
  // CORS
  CORS_ORIGIN: z.string().optional(),

  // Default tenant (resolved once at startup — overridable via env)
  DEFAULT_TENANT_ID: z.string().default("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),

  // Anthropic
  ANTHROPIC_API_KEY: z.string().optional(),

  // Webhook HMAC — required in prod for /operations/webhooks/*
  WEBHOOK_HMAC_SECRET: z.string().optional(),

  // Telegram — comma-separated chat_id whitelist (required for /webhooks/telegram in prod)
  TELEGRAM_ALLOWED_CHATS: z.string().optional(),
});

function loadEnv() {
  const parsed = envSchema.safeParse(process.env);
  
  if (!parsed.success) {
    console.error("❌ Invalid environment variables:");
    parsed.error.errors.forEach(e => {
      console.error(`  - ${e.path.join(".")}: ${e.message}`);
    });
    process.exit(1);
  }
  
  return parsed.data;
}

export const env = loadEnv();

// Derived values
export const config = {
  ...env,
  
  // Paths
  artifactsPath: join(process.cwd(), env.ARTIFACTS_DIR),
  
  // Flags
  isDev: env.NODE_ENV === "development",
  isProd: env.NODE_ENV === "production",
  isTest: env.NODE_ENV === "test",
  
  // CORS origins array
  corsOrigins: env.CORS_ORIGIN?.split(",").map(o => o.trim()) || ["http://localhost:3000"],

  // Telegram chat_id whitelist (empty array = reject all in prod)
  telegramAllowedChats: env.TELEGRAM_ALLOWED_CHATS
    ? env.TELEGRAM_ALLOWED_CHATS.split(",").map((s) => s.trim()).filter(Boolean)
    : [],
};

export type Env = z.infer<typeof envSchema>;
