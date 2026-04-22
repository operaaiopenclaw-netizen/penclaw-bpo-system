import { logger } from "../utils/logger";
import type {
  ChannelDeliveryResult,
  NotificationChannel,
  NotificationPayload,
} from "./types";

export class WebhookChannel implements NotificationChannel {
  readonly name = "webhook";
  private readonly url?: string;
  private readonly authHeader?: string;

  constructor(opts?: { url?: string; authHeader?: string }) {
    this.url = opts?.url ?? process.env.WEBHOOK_URL;
    this.authHeader = opts?.authHeader ?? process.env.WEBHOOK_AUTH;
  }

  isConfigured(): boolean {
    return Boolean(this.url);
  }

  async send(payload: NotificationPayload): Promise<ChannelDeliveryResult> {
    const start = Date.now();

    if (!this.url) {
      return {
        channel: this.name,
        ok: false,
        skipped: true,
        skippedReason: "WEBHOOK_URL not set",
        latencyMs: Date.now() - start,
      };
    }

    try {
      const headers: Record<string, string> = {
        "content-type": "application/json",
        "x-orkestra-source": "alert-engine",
      };
      if (this.authHeader) headers["authorization"] = this.authHeader;

      const res = await fetch(this.url, {
        method: "POST",
        headers,
        body: JSON.stringify({
          ...payload,
          emittedAt: new Date().toISOString(),
        }),
      });

      if (!res.ok) {
        return {
          channel: this.name,
          ok: false,
          error: `HTTP ${res.status}`,
          latencyMs: Date.now() - start,
        };
      }

      return {
        channel: this.name,
        ok: true,
        latencyMs: Date.now() - start,
      };
    } catch (err) {
      logger.error("Webhook channel send failed", {
        error: err instanceof Error ? err.message : String(err),
      });
      return {
        channel: this.name,
        ok: false,
        error: err instanceof Error ? err.message : String(err),
        latencyMs: Date.now() - start,
      };
    }
  }
}

export const webhookChannel = new WebhookChannel();
