// Global type declarations
import { ToolRegistry } from "./src/tools/registry";

declare global {
  var __toolRegistry: ToolRegistry | undefined;
}

export {};
