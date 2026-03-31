import pino from "pino";
import { config } from "../config/env";

// Use pino production-ready logger
const pinoConfig = config.isDev
  ? {
      transport: {
        target: "pino-pretty",
        options: {
          colorize: true,
          translateTime: "HH:MM:ss Z",
          ignore: "pid,hostname",
        },
      },
    }
  : {};

export const logger = pino(pinoConfig);

// Structured JSON logger for compatibility
export const jsonLogger = {
  info(message: string, meta?: unknown) {
    logger.info({ message, meta });
  },
  error(message: string, meta?: unknown) {
    logger.error({ message, meta });
  },
  warn(message: string, meta?: unknown) {
    logger.warn({ message, meta });
  },
  debug(message: string, meta?: unknown) {
    if (config.isDev) {
      console.log(JSON.stringify({ level: "debug", message, meta, at: new Date().toISOString() }));
    }
  }
};

export default logger;
