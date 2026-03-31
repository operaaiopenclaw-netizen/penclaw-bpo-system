import { FastifyReply, FastifyRequest } from "fastify";
import { AppError } from "./app-error";
import { logger } from "./logger";

export function errorHandler(error: Error, _request: FastifyRequest, reply: FastifyReply) {
  if (error instanceof AppError) {
    return reply.status(error.statusCode).send({
      success: false,
      error: error.code,
      message: error.message,
    });
  }

  logger.error("Unhandled error", { error: error.message, stack: error.stack });

  return reply.status(500).send({
    success: false,
    error: "INTERNAL_SERVER_ERROR",
    message: "Unexpected internal error",
  });
}

export async function notFoundHandler(request: FastifyRequest, reply: FastifyReply) {
  return reply.status(404).send({
    success: false,
    error: "NOT_FOUND",
    message: `Route ${request.method} ${request.url} not found`,
  });
}
