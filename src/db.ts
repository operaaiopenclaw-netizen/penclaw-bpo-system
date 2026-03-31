import { PrismaClient } from "@prisma/client";

export const prisma = new PrismaClient();

// Configuração com log em desenvolvimento
export const prismaWithLogging = new PrismaClient({
  log: process.env.NODE_ENV === "development" 
    ? ["query", "info", "warn", "error"] 
    : undefined,
});

// Extensão com métodos úteis
export const prismaExtended = new PrismaClient().$extends({
  model: {
    agentRun: {
      async findWithSteps(id: string) {
        return this.findUnique({
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
      },
    },
  },
});

// Helper para transações
export async function runInTransaction<T>(
  fn: (tx: PrismaClient) => Promise<T>
): Promise<T> {
  return prisma.$transaction(fn);
}

// Graceful shutdown
export async function disconnect() {
  await prisma.$disconnect();
}

process.on("SIGINT", async () => {
  await disconnect();
  process.exit(0);
});
