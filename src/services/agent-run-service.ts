import { prisma } from "../db";
import { agentRunQueue } from "../queue";

export type CreateAgentRunInput = {
  companyId: string;
  workflowType: string;
  input: Record<string, unknown>;
};

export class AgentRunService {
  async create(input: CreateAgentRunInput) {
    const run = await prisma.agentRun.create({
      data: {
        companyId: input.companyId,
        workflowType: input.workflowType,
        status: "pending",
        riskLevel: "R1",
        inputSummary: JSON.stringify(input.input ?? {}),
        createdAt: new Date()
      }
    });

    await agentRunQueue.add("agent-run", {
      runId: run.id,
      companyId: input.companyId,
      workflowType: input.workflowType,
      input: input.input ?? {}
    });

    return {
      runId: run.id,
      status: "pending"
    };
  }

  async getById(id: string) {
    return prisma.agentRun.findUnique({
      where: { id },
      include: {
        steps: {
          orderBy: { stepOrder: "asc" }
        },
        approvals: true,
        artifacts: true
      }
    });
  }

  async list() {
    return prisma.agentRun.findMany({
      orderBy: { createdAt: "desc" },
      take: 50
    });
  }
}

export const agentRunService = new AgentRunService();
