import { ToolImplementation, ToolExecutionInput, ToolExecutionOutput } from "../types/tools";
import { logger } from "../utils/logger";

/**
 * HTTP Request Tool
 * Makes HTTP requests with allowlist validation
 */
export class HttpRequestTool implements ToolImplementation {
  name = "http.request";
  description = "Make HTTP requests to allowed endpoints";

  // Allowlist of domains (empty = all allowed in dev mode)
  private readonly allowlist: string[] = [
    "api.orkestra.ai",
    "openclaw.ai",
    "localhost:3333",
    "localhost:3000",
    "wttr.in", // Weather API for demo
    "jsonplaceholder.typicode.com", // Demo API
  ];

  // Blocklist of dangerous patterns
  private readonly blocklist = [
    "169.254", // Link-local
    "10.",      // Private
    "192.168.", // Private
    "127.",     // Localhost (unless in allowlist)
    "0.0.0.0",
    "::1",
    "file://",
    "ftp://",
    "ldap://",
    "smtp://",
    "telnet://",
  ];

  // Maximum response size (1MB)
  private readonly MAX_RESPONSE_SIZE = 1024 * 1024;

  // Request timeout (30s)
  private readonly TIMEOUT_MS = 30000;

  async execute({ input, context }: ToolExecutionInput): Promise<ToolExecutionOutput> {
    const startTime = Date.now();
    
    const url = String(input.url || "");
    const method = String(input.method || "GET").toUpperCase();
    
    logger.info("HttpRequestTool executing", { 
      url,
      method,
      runId: context.agentRunId 
    });

    // Validate URL
    const validation = this.validateUrl(url);
    if (!validation.valid) {
      return {
        success: false,
        data: null,
        error: validation.error,
        latencyMs: Date.now() - startTime
      };
    }

    // Validate method
    const allowedMethods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"];
    if (!allowedMethods.includes(method)) {
      return {
        success: false,
        data: null,
        error: `HTTP method not allowed: ${method}`,
        latencyMs: Date.now() - startTime
      };
    }

    try {
      // Parse headers
      const headers: Record<string, string> = {
        "User-Agent": "Orkestra-Agent/1.0",
        ...(input.headers as Record<string, string> || {})
      };

      // Add content-type for body requests
      if (["POST", "PUT", "PATCH"].includes(method) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
      }

      // Prepare body
      let body: string | undefined;
      if (["POST", "PUT", "PATCH"].includes(method) && input.body) {
        body = typeof input.body === "string" 
          ? input.body 
          : JSON.stringify(input.body);
      }

      // Create abort controller for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.TIMEOUT_MS);

      // Make request
      const response = await fetch(url, {
        method,
        headers,
        body: body || undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Check response size
      const contentLength = parseInt(response.headers.get("content-length") || "0");
      if (contentLength > this.MAX_RESPONSE_SIZE) {
        return {
          success: false,
          data: null,
          error: `Response too large: ${contentLength} bytes (max: ${this.MAX_RESPONSE_SIZE})`,
          latencyMs: Date.now() - startTime
        };
      }

      // Read response
      const responseText = await response.text();
      
      // Try to parse JSON
      let responseData: unknown = responseText;
      try {
        responseData = JSON.parse(responseText);
      } catch {
        // Keep as text if not JSON
      }

      logger.info("HTTP request completed", { 
        url,
        status: response.status,
        latency: Date.now() - startTime
      });

      return {
        success: response.ok,
        data: {
          url,
          method,
          status: response.status,
          statusText: response.statusText,
          headers: Object.fromEntries(response.headers.entries()),
          body: responseData,
          size: responseText.length
        },
        error: response.ok ? undefined : `HTTP ${response.status}: ${response.statusText}`,
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      logger.error("HTTP request failed", { 
        url, 
        error: errorMessage 
      });

      // Handle specific errors
      if (errorMessage.includes("abort")) {
        return {
          success: false,
          data: null,
          error: `Request timeout after ${this.TIMEOUT_MS}ms`,
          latencyMs: Date.now() - startTime
        };
      }

      if (errorMessage.includes("ECONNREFUSED")) {
        return {
          success: false,
          data: null,
          error: `Connection refused: ${url}`,
          latencyMs: Date.now() - startTime
        };
      }

      if (errorMessage.includes("ENOTFOUND")) {
        return {
          success: false,
          data: null,
          error: `Host not found: ${url}`,
          latencyMs: Date.now() - startTime
        };
      }

      return {
        success: false,
        data: null,
        error: `Request failed: ${errorMessage}`,
        latencyMs: Date.now() - startTime
      };
    }
  }

  /**
   * Validate URL against allowlist/blocklist
   */
  private validateUrl(url: string): { valid: boolean; error?: string } {
    if (!url) {
      return { valid: false, error: "URL is required" };
    }

    // Parse URL
    let parsed: URL;
    try {
      parsed = new URL(url);
    } catch {
      return { valid: false, error: "Invalid URL format" };
    }

    // Only HTTP/HTTPS
    if (!["http:", "https:"].includes(parsed.protocol)) {
      return { valid: false, error: `Protocol not allowed: ${parsed.protocol}` };
    }

    // Check blocklist
    for (const block of this.blocklist) {
      if (url.includes(block)) {
        return { valid: false, error: `URL contains blocked pattern: ${block}` };
      }
    }

    // Check allowlist (if configured)
    if (this.allowlist.length > 0) {
      const allowed = this.allowlist.some(domain => 
        parsed.hostname === domain || parsed.hostname.endsWith(`.${domain}`)
      );
      
      if (!allowed) {
        return { 
          valid: false, 
          error: `Domain not in allowlist: ${parsed.hostname}` 
        };
      }
    }

    // Block credential URLs
    if (parsed.username || parsed.password) {
      return { valid: false, error: "URLs with credentials not allowed" };
    }

    return { valid: true };
  }
}

// Export singleton
export const httpRequestTool = new HttpRequestTool();
