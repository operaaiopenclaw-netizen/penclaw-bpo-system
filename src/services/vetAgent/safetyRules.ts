// ============================================================
// VETAGENT: Safety Rules - Emergency Keyword Detection
// ============================================================

import { SafetyRule, VetAgentResponse } from "./types";

// Critical emergency patterns that require immediate vet attention
export const SAFETY_RULES: SafetyRule[] = [
  {
    id: "EMERGENCY_BLEEDING",
    patterns: [
      "bleeding", "blood", "hemorrhage", "bleeding heavily",
      "sangrando", "sangue", "hemorr", "sangra"
    ],
    severity: "high",
    message: "🚨 URGENTE: Sangramento detectado. Leve seu pet para um veterinário IMEDIATAMENTE. Sangramento pode indicar trauma interno ou externo sério que requer atenção veterinária de emergência.",
    overrideAI: true,
  },
  {
    id: "EMERGENCY_SEIZURES",
    patterns: [
      "seizure", "convulsion", "seizures", "convulsing", "fitting",
      "convulsão", "convulsa", "ataque", "convulsiona", "tonico-clonica"
    ],
    severity: "high",
    message: "🚨 URGENTE: Convulsão detectada. Isso é uma EMERGÊNCIA VETERINÁRIA. Mantenha o pet em segurança (afaste objetos ao redor), NÃO coloque nada na boca, e procure atendimento veterinário IMEDIATAMENTE.",
    overrideAI: true,
  },
  {
    id: "EMERGENCY_BREATHING",
    patterns: [
      "breathing", "can't breathe", "difficulty breathing", "choking",
      "gasping", "dyspnea", "respirar", "falta de ar", "engasgo",
      "sufocando", "cianose", "lábios azuis", "respiração ofegante"
    ],
    severity: "high",
    message: "🚨 URGENTE: Problemas respiratórios detectados. Isso é uma EMERGÊNCIA. Procure atendimento veterinário IMEDIATAMENTE. Problemas respiratórios podem se tornar fatais rapidamente.",
    overrideAI: true,
  },
  {
    id: "EMERGENCY_POISONING",
    patterns: [
      "poison", "poisoned", "toxin", "toxic", "ate chocolate",
      "veneno", "intoxicação", "toxicidade", "antifreeze", "cunha",
      "comeu chocolate", "ração estragada", "produto de limpeza",
      "inseticida", "pesticida"
    ],
    severity: "high",
    message: "🚨 URGENTE: Possível intoxicação. Isso é uma EMERGÊNCIA. Ligue para um veterinário ou centro de toxicologia ANIMAL IMEDIATAMENTE. Tempos de reação são cruciais em intoxicações.",
    overrideAI: true,
  },
  {
    id: "EMERGENCY_COLLAPSE",
    patterns: [
      "collapsed", "unconscious", "not responding", "coma",
      "desmaiou", "desacordado", "inconsciente", "não reage",
      "desmaiada", "inconsciente"
    ],
    severity: "high",
    message: "🚨 URGENTE: Pet desmaiado ou inconsciente. Isso é uma EMERGÊNCIA EXTREMA. Verifique se está respirando, e procure atendimento veterinário de EMERGÊNCIA IMEDIATAMENTE.",
    overrideAI: true,
  },
  {
    id: "EMERGENCY_BLOAT",
    patterns: [
      "bloated", "swollen belly", "surgical emergency",
      "estômago dilatado", "volvo", "bloat", "barriga estendida"
    ],
    severity: "high",
    message: "🚨 URGENTE: Inchaço abdominal pode indicar \"Bloat\" ou torção gástrica - uma emergência cirúrgica. Leve ao veterinário IMEDIATAMENTE. Cada minuto conta.",
    overrideAI: true,
  },
  {
    id: "EMERGENCY_HEAT_STROKE",
    patterns: [
      "heat stroke", "overheated", "hyperthermia", "hot pavement",
      "insolação", "golpe de calor", "superaquecimento",
      "desmaio calor", "tosse exercicio"
    ],
    severity: "high",
    message: "🚨 URGENTE: Sinais de insolação/golpe de calor. Mova o pet para um local fresco IMEDIATAMENTE, ofereça água (não force), e procure atendimento veterinário URGENTE. O calor excessivo pode causar danos internos graves.",
    overrideAI: true,
  },
  {
    id: "URGENT_NO_URINE",
    patterns: [
      "not urinating", "can't pee", "straining to urinate", "urinary blockage",
      "não urina", "não consegue urinar", "bloqueio urinario",
      "retenção urinaria", "tentando urinar"
    ],
    severity: "high",
    message: "🚨 URGENTE: Incapacidade de urinar é uma emergência, especialmente em gatos machos. Isso pode indicar obstrução uretral que é fatal em 24-48h. Procure um veterinário IMEDIATAMENTE.",
    overrideAI: true,
  },
  {
    id: "URGENT_PROLONGED_VOMITING",
    patterns: [
      "vomiting for days", "can't keep food down", "vomiting blood",
      "vômito constante", "vomitando sangue", "vômito há dias",
      "vomito persistente"
    ],
    severity: "high",
    message: "🚨 URGENTE: Vômito persistente ou com sangue requer atenção veterinária imediata. Risco de desidratação séria ou condição subjacente grave. Procure atendimento HOJE.",
    overrideAI: true,
  },
  {
    id: "URGENT_BIRTH_COMPLICATIONS",
    patterns: [
      "labor", "giving birth", "puppy stuck", "kitten stuck",
      "parto", "trabalho de parto", "filhote preso", "não nasce"
    ],
    severity: "high",
    message: "🚨 URGENTE: Complicações no parto são emergências. Se o trabalho de parto dura mais de 2h sem resultado, ou entre filhotes passam mais de 2-4h, procure atendimento veterinário IMEDIATAMENTE.",
    overrideAI: true,
  },
];

/**
 * Check user message against safety rules
 * Returns the first triggered rule or null if safe
 */
export function checkSafetyRules(message: string): SafetyRule | null {
  const lowerMessage = message.toLowerCase();
  
  for (const rule of SAFETY_RULES) {
    for (const pattern of rule.patterns) {
      if (lowerMessage.includes(pattern.toLowerCase())) {
        return rule;
      }
    }
  }
  
  return null;
}

/**
 * Generate emergency response when safety rule is triggered
 */
export function generateEmergencyResponse(rule: SafetyRule): VetAgentResponse {
  return {
    analysis: rule.message,
    possibleCauses: ["Condição de emergência médica detectada"],
    severity: rule.severity,
    recommendation: "Procure atendimento veterinário de emergência IMEDIATAMENTE. Não espere.",
    needsVet: true,
    triggeredSafetyRule: rule.id,
    disclaimer: "⚠️ ALERTA DE EMERGÊNCIA: Esta condição requer atenção veterinária imediata. Não tente tratar em casa.",
  };
}
