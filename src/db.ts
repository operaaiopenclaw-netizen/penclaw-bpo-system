import { PrismaClient } from "@prisma/client";

export const prisma = new PrismaClient();

// Configuração com log em desenvolvimento
export const prismaWithLogging = new PrismaClient({
  log: process.env.NODE_ENV === "development" 
    ? ["query", "info", "warn", "error"] 
    : undefined,
});

// Helper para transações
export async function runInTransaction<T>(
  fn: (tx: Omit<PrismaClient, "$connect" | "$disconnect" | "$on" | "$transaction" | "$use" | "$extends">) => Promise<T>
): Promise<T> {
  return prisma.$transaction(fn as (tx: Parameters<PrismaClient["$transaction"]>[0] extends (tx: infer TX) => unknown ? TX : never) => Promise<T>);
}

// Convenience: fetch an AgentRun with all its relations
export async function findAgentRunWithSteps(id: string) {
  return prisma.agentRun.findUnique({
    where: { id },
    include: {
      steps: {
        orderBy: { stepOrder: "asc" },
        include: { toolCalls: true }
      },
      approvals: true,
      artifacts: true
    }
  });
}

// Graceful shutdown
export async function disconnect() {
  await prisma.$disconnect();
}

process.on("SIGINT", async () => {
  await disconnect();
  process.exit(0);
});
