// ============================================================
// VETAGENT: Main Service
// ============================================================

import { prisma } from "../../db";
import { logger } from "../../utils/logger";
import {
  VetAgentRequest,
  VetAgentResponse,
  VetAgentResult,
  PetData,
  PetHealthSummary,
} from "./types";
import { checkSafetyRules, generateEmergencyResponse } from "./safetyRules";
import { getPetData, buildVetContext, buildFallbackContext } from "./contextBuilder";
import { buildVetPrompt, buildGenericVetPrompt, parseVetResponse } from "./promptBuilder";
import { callVetAI } from "./aiClient";

export class VetAgentService {
  /**
   * Main entry point: Process a veterinary question
   */
  async processQuestion(request: VetAgentRequest): Promise<VetAgentResult> {
    const startTime = Date.now();
    const { petId, message, userId } = request;

    try {
      logger.info({ petId, message: message.substring(0, 100) }, "VetAgent processing question");

      // PHASE 5: Safety check FIRST
      const safetyRule = checkSafetyRules(message);
      if (safetyRule) {
        logger.warn({ ruleId: safetyRule.id, petId }, "Safety rule triggered");
        
        const emergencyResponse = generateEmergencyResponse(safetyRule);
        
        // Log the interaction
        await this.logInteraction(petId, message, emergencyResponse, {
          triggeredSafetyRule: safetyRule.id,
          latencyMs: Date.now() - startTime,
          tokensUsed: 0,
        });

        return {
          response: emergencyResponse,
          tokensUsed: 0,
          latencyMs: Date.now() - startTime,
          safetyTriggered: true,
        };
      }

      // PHASE 1: Get pet data
      const { pet, health } = await getPetData(petId);

      // PHASE 2: Build context
      const context = pet
        ? buildVetContext(pet, health)
        : buildFallbackContext();

      // PHASE 3: Build prompt
      const prompt = pet
        ? buildVetPrompt(context, message)
        : buildGenericVetPrompt(message);

      // Call AI
      const aiResult = await callVetAI({ prompt, temperature: 0.3 });

      // PHASE 4: Parse response
      const parsed = parseVetResponse(aiResult.content);

      if (!parsed.success) {
        logger.error({ error: parsed.error, petId }, "Failed to parse AI response");
        throw new Error("Failed to parse AI response");
      }

      const response: VetAgentResponse = {
        analysis: parsed.data!.analysis,
        possibleCauses: parsed.data!.possibleCauses,
        severity: parsed.data!.severity as "low" | "medium" | "high",
        recommendation: parsed.data!.recommendation,
        needsVet: parsed.data!.needsVet,
        triggeredSafetyRule: null,
        disclaimer: parsed.data!.disclaimer!,
      };

      // Override if AI suggests vet but severity isn't high
      if (response.needsVet && response.severity === "low") {
        response.severity = "medium";
      }

      // PHASE 6: Log interaction
      const latencyMs = Date.now() - startTime;
      await this.logInteraction(petId, message, response, {
        rawAnalysis: aiResult.content,
        latencyMs,
        tokensUsed: aiResult.tokensUsed,
      });

      return {
        response,
        rawAnalysis: aiResult.content,
        tokensUsed: aiResult.tokensUsed,
        latencyMs,
        safetyTriggered: false,
      };

    } catch (error) {
      logger.error({ error, petId }, "VetAgent processing error");
      
      // Return safe fallback
      return {
        response: {
          analysis: "Não foi possível processar sua pergunta no momento. Tente novamente ou consulte um veterinário diretamente.",
          possibleCauses: ["Erro no sistema"],
          severity: "medium",
          recommendation: "Consulte um veterinário para orientação adequada.",
          needsVet: true,
          triggeredSafetyRule: null,
          disclaimer: "⚠️ Sistema temporariamente indisponível. Procure atendimento veterinário.",
        },
        tokensUsed: 0,
        latencyMs: Date.now() - startTime,
        safetyTriggered: false,
      };
    }
  }

  /**
   * PHASE 6: Log interaction to database
   */
  private async logInteraction(
    petId: string,
    question: string,
    response: VetAgentResponse,
    meta: {
      triggeredSafetyRule?: string | null;
      latencyMs: number;
      tokensUsed: number;
      rawAnalysis?: string;
    }
  ): Promise<void> {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const pet = await (prisma as any).pet.findUnique({
        where: { petId },
        select: { id: true },
      });

      if (!pet) {
        logger.warn({ petId }, "Cannot log VetAgent interaction - pet not found");
        return;
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await (prisma as any).vetAgentLog.create({
        data: {
          petId: pet.id,
          question,
          response: response as any,
          rawAnalysis: meta.rawAnalysis || null,
          severity: response.severity,
          needsVet: response.needsVet,
          triggeredSafetyRule: meta.triggeredSafetyRule || null,
          tokensUsed: meta.tokensUsed,
          latencyMs: meta.latencyMs,
        },
      });

      logger.debug({ petId, logId: pet.id }, "VetAgent interaction logged");
    } catch (error) {
      // Don't fail the request if logging fails
      logger.error({ error, petId }, "Failed to log VetAgent interaction");
    }
  }

  /**
   * Get recent interaction logs for a pet (optional feature)
   */
  async getPetInteractionHistory(petId: string, limit: number = 10) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const pet = await (prisma as any).pet.findUnique({
      where: { petId },
      select: { id: true },
    });

    if (!pet) {
      throw new Error("Pet not found");
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (prisma as any).vetAgentLog.findMany({
      where: { petId: pet.id },
      orderBy: { createdAt: "desc" },
      take: limit,
      select: {
        question: true,
        severity: true,
        needsVet: true,
        createdAt: true,
      },
    });
  }
}

// Export singleton instance
export const vetAgent = new VetAgentService();
