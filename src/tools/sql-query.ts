import { prisma } from "../db";
import { ToolImplementation, ToolExecutionInput, ToolExecutionOutput } from "../types/tools";
import { logger } from "../utils/logger";

/**
 * SQL Query Tool
 * Execute safe read-only SELECT queries
 */
export class SqlQueryTool implements ToolImplementation {
  name = "sql.query";
  description = "Execute read-only SQL SELECT queries";

  // Only ALLOWED keywords for safety
  private readonly ALLOWED_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "AND", "OR", "IN", "NOT",
    "NULL", "IS", "LIKE", "LIMIT", "OFFSET", "ORDER", "BY",
    "ASC", "DESC", "LEFT", "RIGHT", "INNER", "OUTER", "JOIN",
    "ON", "AS", "DISTINCT", "ALL", "CASE", "WHEN", "THEN",
    "ELSE", "END", "COALESCE", "NULLIF", "EXTRACT", "DATE",
    "TIME", "TIMESTAMP", "INTERVAL", "NOW", "COUNT", "SUM",
    "AVG", "MIN", "MAX", "GROUP", "HAVING", "UNION", "INTERSECT",
    "EXCEPT"
  ];

  // Block dangerous keywords
  private readonly BLOCKED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "GRANT", "REVOKE", "COMMIT", "ROLLBACK",
    "BEGIN", "EXECUTE", "CALL", "DECLARE", "SET", "SHOW"
  ];

  // Maximum query length
  private readonly MAX_QUERY_LENGTH = 5000;

  async execute({ input, context }: ToolExecutionInput): Promise<ToolExecutionOutput> {
    const startTime = Date.now();
    
    let query = String(input.query || "");
    
    logger.info("SqlQueryTool executing", { 
      queryLength: query.length,
      runId: context.agentRunId 
    });

    // Validate query
    const validation = this.validateQuery(query);
    if (!validation.valid) {
      return {
        success: false,
        data: null,
        error: validation.error,
        latencyMs: Date.now() - startTime
      };
    }

    try {
      // Add company filter if needed
      if (context.companyId && !query.includes("WHERE")) {
        // Auto-add company filter for certain tables
        const companyTables = ["agent_runs", "events", "recipes", "memory_items"];
        for (const table of companyTables) {
          if (query.toLowerCase().includes(`from ${table}`)) {
            query = this.addCompanyFilter(query, context.companyId);
            break;
          }
        }
      }

      // Execute query
      const result = await prisma.$queryRawUnsafe(query);
      
      const rowCount = Array.isArray(result) ? result.length : 1;
      
      logger.info("SQL query executed", { 
        rows: rowCount,
        latency: Date.now() - startTime
      });

      return {
        success: true,
        data: {
          rows: result,
          count: rowCount,
          query: query.slice(0, 100) + (query.length > 100 ? "..." : "")
        },
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      logger.error("SQL query failed", { 
        error: errorMessage,
        query: query.slice(0, 100)
      });

      // Check for specific database errors
      if (errorMessage.includes("relation")) {
        return {
          success: false,
          data: null,
          error: `Table not found: ${this.extractTableName(errorMessage)}`,
          latencyMs: Date.now() - startTime
        };
      }

      if (errorMessage.includes("column")) {
        return {
          success: false,
          data: null,
          error: `Column not found: ${this.extractColumnName(errorMessage)}`,
          latencyMs: Date.now() - startTime
        };
      }

      return {
        success: false,
        data: null,
        error: `Query failed: ${errorMessage.slice(0, 200)}`,
        latencyMs: Date.now() - startTime
      };
    }
  }

  /**
   * Validate SQL query for safety
   */
  private validateQuery(query: string): { valid: boolean; error?: string } {
    // Check empty
    if (!query.trim()) {
      return { valid: false, error: "Query is required" };
    }

    // Check length
    if (query.length > this.MAX_QUERY_LENGTH) {
      return { valid: false, error: `Query too long: ${query.length} chars (max: ${this.MAX_QUERY_LENGTH})` };
    }

    // Check for blocked keywords (case-insensitive)
    const queryUpper = query.toUpperCase();
    
    for (const keyword of this.BLOCKED_KEYWORDS) {
      // Use regex to avoid matching keywords inside other words
      const regex = new RegExp(`\\b${keyword}\\b`, "i");
      if (regex.test(queryUpper)) {
        return { valid: false, error: `Query contains disallowed keyword: ${keyword}` };
      }
    }

    // Must start with SELECT
    const trimmed = query.trim().toUpperCase();
    if (!trimmed.startsWith("SELECT")) {
      return { valid: false, error: "Query must start with SELECT (only read queries allowed)" };
    }

    // Don't allow comments that might hide malicious code
    if (query.includes("/*") || query.includes("*/") || query.includes("--")) {
      return { valid: false, error: "Comments not allowed in queries" };
    }

    return { valid: true };
  }

  /**
   * Add company filter to query
   */
  private addCompanyFilter(query: string, companyId: string): string {
    // Simple regex to find WHERE clause
    const whereMatch = /\bWHERE\b/i;
    
    if (whereMatch.test(query)) {
      // Add company condition before other WHERE conditions
      return query.replace(
        /\bWHERE\b/i,
        `WHERE "companyId" = '${companyId}' AND`
      );
    } else {
      // Add WHERE before ORDER BY, GROUP BY, LIMIT, or end
      const clauseMatch = /\b(ORDER|GROUP|LIMIT)\b/i;
      if (clauseMatch.test(query)) {
        const match = query.match(clauseMatch);
        if (match?.index !== undefined) {
          return `${query.slice(0, match.index)}WHERE "companyId" = '${companyId}' ${query.slice(match.index)}`;
        }
      }
      return `${query} WHERE "companyId" = '${companyId}'`;
    }
  }

  /**
   * Extract table name from error message
   */
  private extractTableName(error: string): string {
    const match = error.match(/relation "([^"]+)"/i);
    return match ? match[1] : "unknown";
  }

  /**
   * Extract column name from error message
   */
  private extractColumnName(error: string): string {
    const match = error.match(/column "([^"]+)"/i);
    return match ? match[1] : "unknown";
  }
}

// Export singleton
export const sqlQueryTool = new SqlQueryTool();
