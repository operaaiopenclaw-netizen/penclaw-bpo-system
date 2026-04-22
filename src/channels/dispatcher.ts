import { logger } from "../utils/logger";
import { consoleChannel } from "./console-channel";
import { telegramChannel } from "./telegram-channel";
import { webhookChannel } from "./webhook-channel";
import type {
  ChannelDeliveryResult,
  NotificationChannel,
  NotificationPayload,
} from "./types";

/**
 * Notification dispatcher — fan-out payload to every configured channel.
 * Channels declared as "configured" receive the message; others are skipped
 * with a recorded reason. Console is always on as a safety fallback.
 */
export class NotificationDispatcher {
  private channels: NotificationChannel[];

  constructor(channels?: NotificationChannel[]) {
    this.channels = channels ?? [telegramChannel, webhookChannel, consoleChannel];
  }

  listChannels(): Array<{ name: string; configured: boolean }> {
    return this.channels.map((c) => ({
      name: c.name,
      configured: c.isConfigured(),
    }));
  }

  async dispatch(
    payload: NotificationPayload
  ): Promise<ChannelDeliveryResult[]> {
    const results: ChannelDeliveryResult[] = await Promise.all(
      this.channels.map(
        (c): Promise<ChannelDeliveryResult> =>
          c.send(payload).catch(
            (err): ChannelDeliveryResult => ({
              channel: c.name,
              ok: false,
              latencyMs: 0,
              error: err instanceof Error ? err.message : String(err),
            })
          )
      )
    );

    const delivered = results.filter((r) => r.ok).length;
    const skipped = results.filter((r) => r.skipped).length;
    const failed = results.filter((r) => !r.ok && !r.skipped).length;

    logger.info("Notification dispatched", {
      title: payload.title,
      severity: payload.severity,
      delivered,
      skipped,
      failed,
    });

    return results;
  }
}

export const notificationDispatcher = new NotificationDispatcher();
