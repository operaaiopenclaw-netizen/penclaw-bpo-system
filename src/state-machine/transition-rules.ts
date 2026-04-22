// ============================================================
// STATE MACHINE - Predefined Transition Rules
// SPRINT 2: Default Rules for Event Flow
// ============================================================

import { PrismaClient, Prisma } from "@prisma/client";

const prisma = new PrismaClient();

export interface TransitionRuleDefinition {
  entityType: string;
  fromState: string;
  toState: string;
  preConditions?: Record<string, unknown>;
  requiredFields?: string[];
  allowedActors?: string[];
  requiresApproval?: boolean;
  successMessage: string;
  failureMessage?: string;
  autoActions?: string[];
}

// Pipeline principal de eventos
export const EVENT_PIPELINE_RULES: TransitionRuleDefinition[] = [
  // Fluxo Comercial
  {
    entityType: "event",
    fromState: "LEAD",
    toState: "QUALIFIED",
    requiredFields: ["clientName", "eventType"],
    allowedActors: ["user", "system"],
    successMessage: "Lead qualificado com sucesso"
  },
  {
    entityType: "event",
    fromState: "QUALIFIED",
    toState: "PROPOSED",
    requiredFields: ["numGuests", "eventDate"],
    allowedActors: ["user", "system", "agent:commercial_agent"],
    successMessage: "Proposta gerada e enviada"
  },
  {
    entityType: "event",
    fromState: "PROPOSED",
    toState: "APPROVED",
    requiredFields: ["revenueTotal", "cmvTotal", "marginPct"],
    allowedActors: ["user:manager", "system"],
    successMessage: "Proposta aprovada pelo cliente"
  },
  {
    entityType: "event",
    fromState: "APPROVED",
    toState: "CONTRACTED",
    requiredFields: ["nCtt"],
    allowedActors: ["user", "system"],
    successMessage: "Contrato formalizado com sucesso"
  },
  
  // Fluxo de Operação
  {
    entityType: "event",
    fromState: "CONTRACTED",
    toState: "PLANNED",
    allowedActors: ["user", "agent:operations_agent"],
    successMessage: "Planejamento operacional concluído"
  },
  {
    entityType: "event",
    fromState: "PLANNED",
    toState: "READY_FOR_PRODUCTION",
    allowedActors: ["user", "agent:inventory_agent"],
    successMessage: "Estoque verificado e disponível"
  },
  {
    entityType: "event",
    fromState: "READY_FOR_PRODUCTION",
    toState: "IN_PRODUCTION",
    allowedActors: ["user:production", "system"],
    successMessage: "Produção iniciada em setores"
  },
  {
    entityType: "event",
    fromState: "IN_PRODUCTION",
    toState: "READY_FOR_EXECUTION",
    allowedActors: ["user:production"],
    successMessage: "Produção finalizada e inspecionada"
  },
  {
    entityType: "event",
    fromState: "READY_FOR_EXECUTION",
    toState: "EXECUTING",
    allowedActors: ["user:operations"],
    successMessage: "Evento em execução no local"
  },
  {
    entityType: "event",
    fromState: "EXECUTING",
    toState: "CLOSED",
    allowedActors: ["user:operations"],
    successMessage: "Evento concluído e finalizado"
  },
  {
    entityType: "event",
    fromState: "CLOSED",
    toState: "ANALYZED",
    allowedActors: ["user:manager", "agent:reporting_agent"],
    successMessage: "Análise pós-evento concluída"
  },
  
  // Cancelamentos
  {
    entityType: "event",
    fromState: "LEAD",
    toState: "CANCELLED",
    allowedActors: ["user", "system"],
    successMessage: "Lead cancelado"
  },
  {
    entityType: "event",
    fromState: "QUALIFIED",
    toState: "CANCELLED",
    allowedActors: ["user", "system"],
    successMessage: "Qualificação cancelada"
  },
  {
    entityType: "event",
    fromState: "PROPOSED",
    toState: "CANCELLED",
    allowedActors: ["user", "system"],
    successMessage: "Proposta recusada ou expirada"
  },
  {
    entityType: "event",
    fromState: "APPROVED",
    toState: "CANCELLED",
    allowedActors: ["user:manager"],
    requiresApproval: true,
    successMessage: "Evento cancelado após aprovação"
  }
];

// Transições inválidas (para validação)
export const INVALID_TRANSITIONS = [
  // Não pode pular estados
  { from: "LEAD", to: "APPROVED", reason: "Must pass through QUALIFIED and PROPOSED" },
  { from: "LEAD", to: "CONTRACTED", reason: "Must follow sales pipeline" },
  { from: "PROPOSED", to: "IN_PRODUCTION", reason: "Must be CONTRACTED first" },
  { from: "APPROVED", to: "IN_PRODUCTION", reason: "Must be CONTRACTED first" },
  
  // Não pode retornar no pipeline sem rollback
  { from: "CONTRACTED", to: "PROPOSED", reason: "Contract already signed" },
  { from: "IN_PRODUCTION", to: "PLANNED", reason: "Use rollback" },
  { from: "CLOSED", to: "EXECUTING", reason: "Event already closed" },
];

/**
 * Criar regras default no banco
 */
export async function seedTransitionRules(tenantId: string): Promise<void> {
  console.log("Seeding transition rules for tenant:", tenantId);

  const created = await prisma.stateTransitionRule.createMany({
    data: EVENT_PIPELINE_RULES.map(rule => ({
      tenantId,
      entityType: rule.entityType,
      fromState: rule.fromState,
      toState: rule.toState,
      preConditions: (rule.preConditions || {}) as Prisma.InputJsonValue,
      requiredFields: rule.requiredFields || [],
      allowedActors: rule.allowedActors || ["user", "system"],
      requiresApproval: rule.requiresApproval || false,
      successMessage: rule.successMessage,
      failureMessage: rule.failureMessage || `Failed to transition from ${rule.fromState} to ${rule.toState}`,
      autoActions: rule.autoActions || [],
      isActive: true
    })),
    skipDuplicates: true
  });

  console.log(`Created ${created.count} transition rules`);
}

/**
 * Verificar se transição é inválida conhecida
 */
export function isKnownInvalidTransition(
  fromState: string,
  toState: string
): { valid: boolean; reason?: string } {
  const invalid = INVALID_TRANSITIONS.find(
    t => t.from === fromState && t.to === toState
  );

  if (invalid) {
    return { valid: false, reason: invalid.reason };
  }

  return { valid: true };
}

/**
 * Obter caminho esperado para um estado
 */
export function getExpectedPath(targetState: string): string[] {
  const pipeline = ["LEAD", "QUALIFIED", "PROPOSED", "APPROVED", "CONTRACTED", "PLANNED", "READY_FOR_PRODUCTION", "IN_PRODUCTION", "READY_FOR_EXECUTION", "EXECUTING", "CLOSED", "ANALYZED"];
  
  const targetIndex = pipeline.indexOf(targetState);
  if (targetIndex === -1) return [];
  
  return pipeline.slice(0, targetIndex + 1);
}

/**
 * Verificar quais estados estão faltantes
 */
export function getMissingStates(
  currentState: string,
  targetState: string
): string[] {
  const currentIndex = getExpectedPath(currentState).length - 1;
  const fullPath = getExpectedPath(targetState);
  
  return fullPath.slice(currentIndex + 1);
}
