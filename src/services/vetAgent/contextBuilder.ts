// ============================================================
// VETAGENT: Context Builder - Construct Pet Context for AI
// ============================================================

import { prisma } from "../../db";
import { PetData, PetHealthSummary, VetContext } from "./types";

/**
 * Fetch complete pet data including health records
 */
export async function getPetData(petId: string): Promise<{
  pet: PetData | null;
  health: PetHealthSummary;
}> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pet = await (prisma as any).pet.findUnique({
    where: { petId },
    include: {
      vaccines: {
        where: { isValid: true },
        orderBy: { administeredAt: "desc" },
      },
      healthRecords: {
        orderBy: { visitDate: "desc" },
        take: 5, // Last 5 records
      },
      symptoms: {
        where: { isActive: true },
        orderBy: { startedAt: "desc" },
      },
    },
  });

  if (!pet) {
    return { pet: null, health: { vaccines: [], healthRecords: [], activeSymptoms: [] } };
  }

  return {
    pet: {
      id: pet.id,
      petId: pet.petId,
      name: pet.name,
      species: pet.species,
      breed: pet.breed,
      ageYears: pet.ageYears || calculateAge(pet.dateOfBirth),
      weightKg: pet.weightKg,
      ownerId: pet.ownerId,
      ownerName: pet.ownerName,
    },
    health: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vaccines: (pet.vaccines || []).map((v: any) => ({
        vaccineName: v.vaccineName,
        vaccineType: v.vaccineType,
        administeredAt: v.administeredAt,
        nextDueDate: v.nextDueDate,
        isValid: v.isValid,
      })),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      healthRecords: (pet.healthRecords || []).map((h: any) => ({
        id: h.id,
        recordType: h.recordType,
        description: h.description,
        diagnosis: h.diagnosis,
        treatment: h.treatment,
        visitDate: h.visitDate,
        followUpDate: h.followUpDate,
      })),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      activeSymptoms: (pet.symptoms || []).map((s: any) => ({
        id: s.id,
        symptomName: s.symptomName,
        severity: s.severity,
        frequency: s.frequency,
        startedAt: s.startedAt,
        notes: s.notes,
      })),
    },
  };
}

/**
 * Calculate age from date of birth
 */
function calculateAge(dateOfBirth: Date | null): number | undefined {
  if (!dateOfBirth) return undefined;
  const diff = Date.now() - dateOfBirth.getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24 * 365.25));
}

/**
 * Build comprehensive vet context for AI prompt
 */
export function buildVetContext(
  pet: PetData,
  health: PetHealthSummary
): VetContext {
  const petProfile = buildPetProfile(pet);
  const healthSummary = buildHealthSummary(health);
  const vaccineStatus = buildVaccineStatus(health.vaccines);
  const symptomContext = buildSymptomContext(health.activeSymptoms);
  const redFlags = identifyRedFlags(health);

  return {
    petProfile,
    healthSummary,
    vaccineStatus,
    symptomContext,
    redFlags,
  };
}

/**
 * Build pet profile string
 */
function buildPetProfile(pet: PetData): string {
  const parts: string[] = [
    `Nome: ${pet.name}`,
    `Espécie: ${pet.species}${pet.breed ? ` (${pet.breed})` : ""}`,
  ];

  if (pet.ageYears !== undefined && pet.ageYears !== null) {
    parts.push(`Idade: ${formatAge(pet.ageYears)}`);
  } else {
    parts.push("Idade: não registrada");
  }

  if (pet.weightKg) {
    parts.push(`Peso: ${pet.weightKg}kg`);
  }

  return parts.join("\n");
}

/**
 * Format age in years to human readable
 */
function formatAge(years: number): string {
  if (years < 1) {
    const months = Math.round(years * 12);
    return `${months} ${months === 1 ? "mês" : "meses"}`;
  }
  return `${years} ${years === 1 ? "ano" : "anos"}`;
}

/**
 * Build health summary from records
 */
function buildHealthSummary(health: PetHealthSummary): string {
  if (health.healthRecords.length === 0) {
    return "Sem histórico médico registrado.";
  }

  const summaries = health.healthRecords
    .slice(0, 3)
    .map((record) => {
      const date = record.visitDate.toLocaleDateString("pt-BR");
      const diagnosis = record.diagnosis ? ` - Diagnóstico: ${record.diagnosis}` : "";
      return `${date}: ${record.recordType} - ${record.description}${diagnosis}`;
    });

  return `Últimos registros:\n${summaries.join("\n")}`;
}

/**
 * Build vaccine status summary
 */
function buildVaccineStatus(vaccines: PetHealthSummary["vaccines"]): string {
  if (vaccines.length === 0) {
    return "Vacinação: Nenhuma vacina registrada no sistema.";
  }

  const coreVaccines = vaccines.filter((v) => v.vaccineType === "core");
  const vaccinesList = vaccines
    .map((v) => {
      const dueDate = v.nextDueDate
        ? ` (próxima: ${v.nextDueDate.toLocaleDateString("pt-BR")})`
        : "";
      return `- ${v.vaccineName}${dueDate}`;
    })
    .join("\n");

  return `Vacinas registradas (${coreVaccines.length} essenciais):\n${vaccinesList}`;
}

/**
 * Build symptom context
 */
function buildSymptomContext(symptoms: PetHealthSummary["activeSymptoms"]): string {
  if (symptoms.length === 0) {
    return "Nenhum sintoma ativo registrado.";
  }

  const symptomList = symptoms
    .map((s) => {
      const startDate = s.startedAt.toLocaleDateString("pt-BR");
      const freq = s.frequency ? ` (${s.frequency})` : "";
      const notes = s.notes ? ` - ${s.notes}` : "";
      return `- ${s.symptomName} [${s.severity}] desde ${startDate}${freq}${notes}`;
    })
    .join("\n");

  return `Sintomas ativos (${symptoms.length}):\n${symptomList}`;
}

/**
 * Identify red flags from health data
 */
function identifyRedFlags(health: PetHealthSummary): string[] {
  const flags: string[] = [];

  // Check for severe symptoms
  const severeSymptoms = health.activeSymptoms.filter(
    (s) => s.severity === "severe" || s.severity === "grave"
  );
  if (severeSymptoms.length > 0) {
    flags.push(`Sintomas graves ativos: ${severeSymptoms.map((s) => s.symptomName).join(", ")}`);
  }

  // Check for overdue vaccines
  const overdueVaccines = health.vaccines.filter(
    (v) => v.nextDueDate && v.nextDueDate < new Date()
  );
  if (overdueVaccines.length > 0) {
    flags.push(`Vacinas vencidas: ${overdueVaccines.map((v) => v.vaccineName).join(", ")}`);
  }

  // Check for recent surgeries
  const recentSurgery = health.healthRecords.find(
    (h) => h.recordType === "surgery" && h.visitDate > new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
  );
  if (recentSurgery) {
    flags.push(`Cirurgia recente: ${recentSurgery.description}`);
  }

  // Check for chronic conditions
  const chronicConditions = health.healthRecords.filter(
    (h) => h.recordType === "chronic_condition"
  );
  if (chronicConditions.length > 0) {
    flags.push(`Condições crônicas: ${chronicConditions.map((c) => c.diagnosis || c.description).join(", ")}`);
  }

  return flags;
}

/**
 * Generate fallback context when pet data is not available
 */
export function buildFallbackContext(): VetContext {
  return {
    petProfile: "Pet não identificado no sistema.\nUsando orientações veterinárias genéricas.",
    healthSummary: "Sem histórico de saúde disponível.",
    vaccineStatus: "Status de vacinação desconhecido.",
    symptomContext: "Sem sintomas anteriores registrados.",
    redFlags: [],
  };
}
