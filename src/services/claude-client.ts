import Anthropic from "@anthropic-ai/sdk";
import { logger } from "../utils/logger";

const MODEL = "claude-opus-4-7";

let _client: Anthropic | null = null;

function getClient(): Anthropic {
  if (!_client) {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) throw new Error("ANTHROPIC_API_KEY not configured");
    _client = new Anthropic({ apiKey });
  }
  return _client;
}

export interface ClaudeAnalysisRequest {
  systemPrompt: string;
  userContent: string;
  maxTokens?: number;
}

export interface ClaudeAnalysisResult {
  text: string;
  inputTokens: number;
  outputTokens: number;
  cached?: boolean;
}

export async function analyzeWithClaude(req: ClaudeAnalysisRequest): Promise<ClaudeAnalysisResult> {
  const client = getClient();

  const stream = await client.messages.stream({
    model: MODEL,
    max_tokens: req.maxTokens ?? 1024,
    thinking: { type: "adaptive" },
    system: [
      {
        type: "text",
        text: req.systemPrompt,
        cache_control: { type: "ephemeral" }
      }
    ],
    messages: [{ role: "user", content: req.userContent }]
  });

  const message = await stream.finalMessage();

  const textBlock = message.content.find(b => b.type === "text");
  const text = textBlock?.type === "text" ? textBlock.text : "";

  const usage = message.usage as { input_tokens: number; output_tokens: number; cache_read_input_tokens?: number };

  logger.debug("Claude analysis complete", {
    model: MODEL,
    inputTokens: usage.input_tokens,
    outputTokens: usage.output_tokens,
    cacheHit: (usage.cache_read_input_tokens ?? 0) > 0
  });

  return {
    text,
    inputTokens: usage.input_tokens,
    outputTokens: usage.output_tokens,
    cached: (usage.cache_read_input_tokens ?? 0) > 0
  };
}

export function isClaudeAvailable(): boolean {
  return !!process.env.ANTHROPIC_API_KEY;
}
