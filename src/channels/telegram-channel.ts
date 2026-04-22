import { logger } from "../utils/logger";
import type {
  ChannelDeliveryResult,
  NotificationChannel,
  NotificationPayload,
} from "./types";

const TELEGRAM_API = "https://api.telegram.org";

function severityEmoji(sev: NotificationPayload["severity"]): string {
  switch (sev) {
    case "CRITICAL":
      return "🚨";
    case "HIGH":
      return "⚠️";
    case "MEDIUM":
      return "⚡";
    case "LOW":
      return "ℹ️";
    default:
      return "🔔";
  }
}

export class TelegramChannel implements NotificationChannel {
  readonly name = "telegram";
  private readonly botToken?: string;
  private readonly chatId?: string;

  constructor(opts?: { botToken?: string; chatId?: string }) {
    this.botToken = opts?.botToken ?? process.env.TELEGRAM_BOT_TOKEN;
    this.chatId = opts?.chatId ?? process.env.TELEGRAM_CHAT_ID;
  }

  isConfigured(): boolean {
    return Boolean(this.botToken && this.chatId);
  }

  async send(payload: NotificationPayload): Promise<ChannelDeliveryResult> {
    const start = Date.now();

    if (!this.isConfigured()) {
      return {
        channel: this.name,
        ok: false,
        skipped: true,
        skippedReason: "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set",
        latencyMs: Date.now() - start,
      };
    }

    const emoji = severityEmoji(payload.severity);
    const text = [
      `${emoji} *${payload.title}*`,
      ``,
      payload.body,
      payload.category ? `\n_Categoria:_ ${payload.category}` : "",
      payload.eventId ? `_Evento:_ \`${payload.eventId}\`` : "",
      payload.actionUrl ? `\n[Abrir](${payload.actionUrl})` : "",
    ]
      .filter(Boolean)
      .join("\n");

    try {
      const res = await fetch(
        `${TELEGRAM_API}/bot${this.botToken}/sendMessage`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            chat_id: this.chatId,
            text,
            parse_mode: "Markdown",
            disable_web_page_preview: true,
          }),
        }
      );

      const json = (await res.json().catch(() => ({}))) as {
        ok?: boolean;
        result?: { message_id?: number };
        description?: string;
      };

      if (!res.ok || !json.ok) {
        return {
          channel: this.name,
          ok: false,
          error: json.description ?? `HTTP ${res.status}`,
          latencyMs: Date.now() - start,
        };
      }

      return {
        channel: this.name,
        ok: true,
        externalId: json.result?.message_id?.toString(),
        latencyMs: Date.now() - start,
      };
    } catch (err) {
      logger.error("Telegram channel send failed", {
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

export const telegramChannel = new TelegramChannel();
