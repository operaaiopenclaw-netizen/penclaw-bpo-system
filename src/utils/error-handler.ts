import { FastifyReply, FastifyRequest } from "fastify";
import path from "node:path";
import { promises as fs } from "node:fs";
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

  logger.error(`Unhandled error: ${error.message}`);

  return reply.status(500).send({
    success: false,
    error: "INTERNAL_SERVER_ERROR",
    message: "Unexpected internal error",
  });
}

export async function notFoundHandler(request: FastifyRequest, reply: FastifyReply) {
  // Serve the branded HTML 404 to browsers; JSON to API clients.
  // Heuristic: the Accept header's preference for text/html tells us it's a page load.
  const accept = (request.headers.accept ?? "").toLowerCase();
  if (request.method === "GET" && accept.includes("text/html")) {
    try {
      const buf = await fs.readFile(
        path.resolve(process.cwd(), "dashboard", "404.html"),
      );
      return reply.status(404).type("text/html; charset=utf-8").send(buf);
    } catch {
      // fall through to JSON if the file is missing for any reason
    }
  }

  return reply.status(404).send({
    success: false,
    error: "NOT_FOUND",
    message: `Route ${request.method} ${request.url} not found`,
  });
}
