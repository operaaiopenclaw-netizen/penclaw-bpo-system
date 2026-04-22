// ============================================================
// CHANNELS — Types and contracts
// ============================================================
export type ChannelSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type NotificationPayload = {
  title: string;
  body: string;
  severity: ChannelSeverity;
  category?: string;
  tenantId?: string;
  eventId?: string;
  actionUrl?: string;
  metadata?: Record<string, unknown>;
};

export type ChannelDeliveryResult = {
  channel: string;
  ok: boolean;
  latencyMs: number;
  skipped?: boolean;
  skippedReason?: string;
  error?: string;
  externalId?: string;
};

export interface NotificationChannel {
  readonly name: string;
  isConfigured(): boolean;
  send(payload: NotificationPayload): Promise<ChannelDeliveryResult>;
}

export type InboundMessage = {
  channel: "telegram" | "webhook" | "dashboard" | "api";
  source: string;
  text?: string;
  command?: string;
  args?: string[];
  payload?: Record<string, unknown>;
  receivedAt: Date;
};

export type OperationEventType =
  | "event.create"
  | "event.update"
  | "consumption.update"
  | "production.update"
  | "approval.decision";

export type OperationEvent = {
  type: OperationEventType;
  tenantId?: string;
  payload: Record<string, unknown>;
  source: InboundMessage["channel"];
  receivedAt: Date;
};
