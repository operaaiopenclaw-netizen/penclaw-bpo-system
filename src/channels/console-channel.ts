import { logger } from "../utils/logger";
import type {
  ChannelDeliveryResult,
  NotificationChannel,
  NotificationPayload,
} from "./types";

export class ConsoleChannel implements NotificationChannel {
  readonly name = "console";

  isConfigured(): boolean {
    return true;
  }

  async send(payload: NotificationPayload): Promise<ChannelDeliveryResult> {
    const start = Date.now();
    const line = `[${payload.severity}] ${payload.title} — ${payload.body}`;
    if (payload.severity === "CRITICAL" || payload.severity === "HIGH") {
      logger.warn(line, payload.metadata);
    } else {
      logger.info(line, payload.metadata);
    }
    return {
      channel: this.name,
      ok: true,
      latencyMs: Date.now() - start,
    };
  }
}

export const consoleChannel = new ConsoleChannel();
