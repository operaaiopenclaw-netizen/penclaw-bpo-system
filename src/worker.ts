/**
 * Worker - Process jobs from BullMQ queue
 * Handles agent runs asynchronously
 */

import { Worker, Job } from "bullmq";
import IORedis from "ioredis";
import { logger } from "./utils/logger";
import { prisma } from "./db";
import { orchestrator } from "./orchestrator";
import { AgentRunJobData } from "./queue";
import { WorkflowType } from "./types/core";

// Redis connection
const redisConnection = new IORedis.Redis({
  host: process.env.REDIS_HOST || "localhost",
  port: parseInt(process.env.REDIS_PORT || "6379"),
  maxRetriesPerRequest: null,
});

// Worker instance
const agentRunWorker = new Worker<AgentRunJobData>(
  "agent-run",
  async (job: Job<AgentRunJobData>) => {
    const { agentRunId, companyId, workflowType, input, userId } = job.data;

    logger.info(`Worker processing: ${job.id} - ${workflowType}`);

    try {
      // Update run status to running
      await prisma.agentRun.update({
        where: { id: agentRunId },
        data: {
          status: "running",
          startedAt: new Date(),
        },
      });

      // Execute orchestrator
      const result = await orchestrator.execute({
        agentRunId,
        companyId,
        workflowType: workflowType as WorkflowType,
        input,
      });

      // Update run with result
      await prisma.agentRun.update({
        where: { id: agentRunId },
        data: {
          status: result.success ? "completed" : "failed",
          finishedAt: new Date(),
          outputSummary: result.output ? JSON.stringify(result.output).slice(0, 500) : null,
        },
      });

      logger.info(`Worker completed: ${job.id} - Success: ${result.success}`);
      return result;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";

      // Update run with failure
      await prisma.agentRun.update({
        where: { id: agentRunId },
        data: {
          status: "failed",
          finishedAt: new Date(),
          outputSummary: `Error: ${errorMessage}`,
        },
      });

      logger.error(`Worker failed: ${job.id} - ${errorMessage}`);
      throw error;
    }
  },
  {
    connection: redisConnection,
    concurrency: parseInt(process.env.WORKER_CONCURRENCY || "5"),
    lockDuration: 30000, // 30 seconds
    stalledInterval: 30000,
  }
);

// Event handlers
agentRunWorker.on("completed", (job) => {
  logger.info(`Job completed: ${job.id}`);
});

agentRunWorker.on("failed", (job, err) => {
  logger.error(`Job failed: ${job?.id} - ${err.message}`);
});

agentRunWorker.on("stalled", (jobId) => {
  logger.warn(`Job stalled: ${jobId}`);
});

// Graceful shutdown
export async function closeWorker() {
  await agentRunWorker.close();
  await redisConnection.quit();
  logger.info("Worker shutdown complete");
}

// For manual worker management
export function getWorkerStatus() {
  return {
    isRunning: agentRunWorker.isRunning(),
    isActive: !agentRunWorker.isPaused(),
  };
}

export async function pauseWorker() {
  await agentRunWorker.pause();
  logger.info("Worker paused");
}

export async function resumeWorker() {
  await agentRunWorker.resume();
  logger.info("Worker resumed");
}

export default agentRunWorker;
