// ============================================================
// VETAGENT: Type Definitions
// ============================================================

export interface PetData {
  id: string;
  petId: string;
  name: string;
  species: string;
  breed?: string | null;
  ageYears?: number | null;
  weightKg?: number | null;
  ownerId: string;
  ownerName?: string | null;
}

export interface PetHealthSummary {
  vaccines: VaccineData[];
  healthRecords: HealthRecordData[];
  activeSymptoms: SymptomData[];
}

export interface VaccineData {
  vaccineName: string;
  vaccineType: string;
  administeredAt: Date;
  nextDueDate?: Date | null;
  isValid: boolean;
}

export interface HealthRecordData {
  id: string;
  recordType: string;
  description: string;
  diagnosis?: string | null;
  treatment?: string | null;
  visitDate: Date;
  followUpDate?: Date | null;
}

export interface SymptomData {
  id: string;
  symptomName: string;
  severity: string;
  frequency?: string | null;
  startedAt: Date;
  notes?: string | null;
}

export interface VetAgentRequest {
  petId: string;
  message: string;
  userId?: string;
  metadata?: {
    deviceType?: string;
    appVersion?: string;
  };
}

export interface VetAgentResponse {
  analysis: string;
  possibleCauses: string[];
  severity: "low" | "medium" | "high";
  recommendation: string;
  needsVet: boolean;
  triggeredSafetyRule?: string | null;
  disclaimer: string;
}

export interface VetAgentResult {
  response: VetAgentResponse;
  rawAnalysis?: string;
  tokensUsed: number;
  latencyMs: number;
  safetyTriggered: boolean;
}

export interface SafetyRule {
  id: string;
  patterns: string[]; // Keywords to match
  severity: "high";
  message: string;
  overrideAI: boolean;
}

export interface VetContext {
  petProfile: string;
  healthSummary: string;
  vaccineStatus: string;
  symptomContext: string;
  redFlags: string[];
}
