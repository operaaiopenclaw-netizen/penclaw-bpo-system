import { Worker } from "bullmq";
import { redisConnection } from "./queue";
import { logger } from "./utils/logger";

const worker = new Worker(
  "agent-run",
  async (job) => {
    const { agentRunId, workflowType } = job.data;
    
    logger.info(`🔥 PROCESSING JOB: ${job.id}`);
    logger.info(`➡️ RUN ID: ${agentRunId}`);
    logger.info(`➡️ WORKFLOW: ${workflowType}`);

    // TEMP: simulação de execução
    await new Promise((r) => setTimeout(r, 1000));

    logger.info(`✅ JOB COMPLETED: ${agentRunId}`);

    return { success: true, agentRunId };
  },
  {
    connection: redisConnection,
  }
);

worker.on("completed", (job) => {
  logger.info(`🎯 COMPLETED: ${job.id}`);
});

worker.on("failed", (job, err) => {
  logger.error(`❌ FAILED: ${job?.id}`, err);
});

export async function closeWorker() {
  await worker.close();
}

export default worker;
