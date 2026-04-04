import { Worker } from "bullmq";
import { redisConnection } from "./queue";
import { logger } from "./utils/logger";
import { orchestrator } from "./orchestrator";

const worker = new Worker(
  "agent-run",
  async (job) => {
    const { runId, companyId, workflowType, input } = job.data;
    
    logger.info(`🔥 PROCESSING JOB: ${job.id}`);
    logger.info(`➡️ RUN ID: ${runId}`);
    logger.info(`➡️ WORKFLOW: ${workflowType}`);
    logger.info(`➡️ COMPANY: ${companyId}`);

    try {
      // Execute real orchestrator
      const result = await orchestrator.execute({
        agentRunId: runId,
        companyId,
        workflowType,
        input: input || {}
      });

      logger.info(`✅ JOB COMPLETED: ${runId}`, { result });
      return { success: true, runId, result };
      
    } catch (error) {
      logger.error(`❌ JOB FAILED: ${runId}`, error);
      throw error;
    }
  },
  {
    connection: redisConnection,
  }
);

worker.on("completed", (job) => {
  logger.info(`🎯 WORKER COMPLETED: ${job.id}`);
});

worker.on("failed", (job, err) => {
  logger.error(`❌ WORKER FAILED: ${job?.id}`, err);
});

export async function closeWorker() {
  await worker.close();
}

export default worker;
