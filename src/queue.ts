/**
 * Queue System - BullMQ
 * Async job processing for orchestrator
 */

import { Queue, Job } from "bullmq";
import { logger } from "./utils/logger";
import { WorkflowType } from "./types/core";

// Redis connection - simple config
export const redisConnection = {
  host: "127.0.0.1",
  port: 6379,
};

// Main queue for agent runs
export const agentRunQueue = new Queue("agent-run", {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: "exponential",
      delay: 1000,
    },
    removeOnComplete: 100,
    removeOnFail: 50,
  },
});

// Queue types
export type AgentRunJobData = {
  agentRunId: string;
  companyId: string;
  workflowType: WorkflowType;
  input: Record<string, unknown>;
  userId?: string;
};

// Add job to queue
export async function enqueueAgentRun(
  data: AgentRunJobData,
  options?: { delay?: number; priority?: number }
): Promise<Job<AgentRunJobData>> {
  const job = await agentRunQueue.add(
    `agent-run-${data.workflowType}`,
    data,
    {
      delay: options?.delay,
      priority: options?.priority,
      jobId: data.agentRunId, // Use our ID as job ID
    }
  );

  logger.info(`Job enqueued: ${job.id} for workflow ${data.workflowType}`);
  return job;
}

// Get queue status
export async function getQueueStatus() {
  const [waiting, active, completed, failed, delayed] = await Promise.all([
    agentRunQueue.getWaitingCount(),
    agentRunQueue.getActiveCount(),
    agentRunQueue.getCompletedCount(),
    agentRunQueue.getFailedCount(),
    agentRunQueue.getDelayedCount(),
  ]);

  return {
    waiting,
    active,
    completed,
    failed,
    delayed,
    total: waiting + active + completed + failed + delayed,
  };
}

// Clean old jobs
export async function cleanQueue(olderThan: number = 24 * 60 * 60 * 1000) {
  await agentRunQueue.clean(olderThan, 0, "completed");
  await agentRunQueue.clean(olderThan, 0, "failed");
  logger.info("Queue cleaned");
}

// Close connections
export async function closeQueue() {
  await agentRunQueue.close();
  await redisConnection.quit();
  logger.info("Queue connections closed");
}

export default agentRunQueue;
