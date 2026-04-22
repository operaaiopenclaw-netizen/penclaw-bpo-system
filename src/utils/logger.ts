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

const _pinoLogger = pino(pinoConfig);

// Flexible structured logger — accepts both call conventions:
//   logger.info("msg", { meta })   — common app style
//   logger.info({ meta }, "msg")   — pino native style
function makeLogFn(level: "info" | "error" | "warn" | "debug") {
  return function logFn(msgOrObj: string | Record<string, unknown>, metaOrMsg?: unknown): void {
    if (level === "debug" && !config.isDev) return;
    if (typeof msgOrObj === "string") {
      // logger.info("msg", { meta })
      _pinoLogger[level]({ meta: metaOrMsg }, msgOrObj);
    } else {
      // logger.info({ meta }, "msg")
      const msg = typeof metaOrMsg === "string" ? metaOrMsg : "";
      _pinoLogger[level](msgOrObj, msg);
    }
  };
}

// Unified logger — drop-in compatible with all call sites
export const logger = {
  info: makeLogFn("info"),
  error: makeLogFn("error"),
  warn: makeLogFn("warn"),
  debug: makeLogFn("debug"),
};

// Alias for legacy imports
export const jsonLogger = logger;

export default logger;
