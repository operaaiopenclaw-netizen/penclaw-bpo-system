// ============================================================
// VETAGENT: Service Export
// ============================================================

export { vetAgent, VetAgentService } from "./index";
export { checkSafetyRules, generateEmergencyResponse } from "./safetyRules";
export { getPetData, buildVetContext, buildFallbackContext } from "./contextBuilder";
export { buildVetPrompt, buildGenericVetPrompt, parseVetResponse } from "./promptBuilder";
export { callVetAI, callLLMAPI } from "./aiClient";
export * from "./types";
