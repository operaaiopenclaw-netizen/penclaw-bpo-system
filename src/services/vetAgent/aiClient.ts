// ============================================================
// VETAGENT: AI Client Integration
// Currently uses OpenClaw's session_spawn (simulated for now)
// Production: Replace with actual LLM API
// ============================================================

import { logger } from "../../utils/logger";

interface AIRequest {
  prompt: string;
  systemPrompt?: string;
  temperature?: number;
  maxTokens?: number;
}

interface AIResponse {
  content: string;
  tokensUsed: number;
  latencyMs: number;
}

/**
 * Call AI service with prompt
 * Production: Replace with actual LLM integration (OpenAI, Claude, etc.)
 */
export async function callVetAI(request: AIRequest): Promise<AIResponse> {
  const startTime = Date.now();

  try {
    // Simulate AI call for development
    // Production: Implement actual LLM integration
    const simulatedResponse = await simulateAIResponse(request);

    return {
      content: simulatedResponse,
      tokensUsed: Math.floor(request.prompt.length / 4) + Math.floor(simulatedResponse.length / 4),
      latencyMs: Date.now() - startTime,
    };
  } catch (error) {
    logger.error({ error }, "VetAI call failed");
    throw new Error("Failed to get AI response");
  }
}

/**
 * Simulated AI response for development
 * Remove this in production and use actual LLM
 */
async function simulateAIResponse(request: AIRequest): Promise<string> {
  const prompt = request.prompt.toLowerCase();

  // Emergency patterns simulation
  if (prompt.includes("bleeding") || prompt.includes("sangue")) {
    return JSON.stringify({
      analysis: "⚠️ URGENTE: Sangramento detectado. Leve seu pet para um veterinário IMEDIATAMENTE. Sangramento pode indicar trauma interno ou externo sério que requer atenção veterinária de emergência.",
      possibleCauses: ["Trauma externo", "Trauma interno", "Coagulação comprometida"],
      severity: "high",
      recommendation: "Procure atendimento veterinário de emergência IMEDIATAMENTE. Mantenha pressão direta no local, se possível, e transporte o pet de forma segura.",
      needsVet: true,
      disclaimer: "⚠️ ESTA É UMA ORIENTAÇÃO DE EMERGÊNCIA E NÃO SUBSTITUI AVALIAÇÃO VETERINÁRIA IMEDIATA."
    });
  }

  if (prompt.includes("ear infection") || prompt.includes("otite") || prompt.includes("orelha")) {
    return JSON.stringify({
      analysis: "A inflamação no ouvido com odor e secreção é característica de otite externa. Cães com orelhas caídas (como o descrito, se for da raça indicada) são mais propensos devido à falta de ventilação.",
      possibleCauses: ["Otite externa bacteriana", "Otite por fungos/levaduras", "Infestação de carrapatos ou ácaros", "Alergia alimentar ou ambiental"],
      severity: "medium",
      recommendation: "Agende uma consulta veterinária nos próximos 2-3 dias. Enquanto isso, mantenha a orelha seca e evite que o pet coce excessivamente. NÃO use cotonetes ou medicamentos sem orientação.",
      needsVet: true,
      disclaimer: "⚠️ ESTA É UMA ORIENTAÇÃO INFORMATIVA E NÃO SUBSTITUI A AVALIAÇÃO DE UM VETERINÁRIO."
    });
  }

  if (prompt.includes("vomit") || prompt.includes("vomito")) {
    const severity = prompt.includes("blood") || prompt.includes("sangue") ? "high" : "medium";
    const needsVet = severity === "high" || prompt.includes("diar") || prompt.includes("constante") || prompt.includes("dias");
    
    return JSON.stringify({
      analysis: severity === "high" 
        ? "🚨 URGENTE: Vômito com sangue ou persistente é uma emergência. Pode indicar hemorragia gastrointestinal, corpo estranho, ou intoxicação."
        : "Vômito pode ter diversas causas, desde digestão sensível até condições mais graves. Monitore hidratação e comportamento.",
      possibleCauses: ["Digestão sensível", "Mudança de alimentação", "Corpo estranho", "Intoxicação", "Doença gastrointestinal", "Insolação"],
      severity: severity,
      recommendation: needsVet 
        ? "Procure atendimento veterinário urgentemente, especialmente se houver sangue, letargia, ou vômito persistente."
        : "Retire alimentação por 12-24h, ofereça água em pequenas quantidades frequentes. Se voltar a vomitar ou apresentar letargia, procure atendimento em até 24h.",
      needsVet: needsVet,
      disclaimer: "⚠️ ESTA É UMA ORIENTAÇÃO INFORMATIVA E NÃO SUBSTITUI A AVALIAÇÃO DE UM VETERINÁRIO."
    });
  }

  if (prompt.includes("lethargy") || prompt.includes("letargo") || prompt.includes("cansado") || prompt.includes("apatico")) {
    return JSON.stringify({
      analysis: "Letargia (apatia, cansaço excessivo) pode ser um sinal de diversas condições, desde simples cansaço até doenças sistêmicas graves. A duração e a presença de outros sintomas são importantes.",
      possibleCauses: ["Cansaço normal", "Febre ou infecção", "Doença hepática ou renal", "Desidratação", "Anemia", "Leishmaniose ou outras doenças vetoriais"],
      severity: prompt.includes("dias") || prompt.includes("semana") ? "high" : "medium",
      recommendation: prompt.includes("dias") || prompt.includes("semana")
        ? "⚠️ Letargia prolongada requer avaliação veterinária. Agende consulta nas próximas 24h."
        : "Monitore por 24h. Se persistir, se houver febre, ou recusa de alimento/água, procure atendimento em 48h.",
      needsVet: prompt.includes("dias") || prompt.includes("semana"),
      disclaimer: "⚠️ ESTA É UMA ORIENTAÇÃO INFORMATIVA E NÃO SUBSTITUI A AVALIAÇÃO DE UM VETERINÁRIO."
    });
  }

  // Default response
  return JSON.stringify({
    analysis: "Based on the information provided, I've analyzed your concern. Without more specific details, I can offer general guidance.",
    possibleCauses: ["Várias condições podem causar este sintoma", "Requer avaliação física para diagnóstico"],
    severity: "low",
    recommendation: "Monitore o comportamento do pet nas próximas 24-48h. Se o sintoma persistir, piorar, ou surgirem outros sinais (como febre, falta de apetite, ou alteração no comportamento), agende uma consulta veterinária.",
    needsVet: false,
    disclaimer: "⚠️ ESTA É UMA ORIENTAÇÃO INFORMATIVA E NÃO SUBSTITUI A AVALIAÇÃO DE UM VETERINÁRIO."
  });
}

/**
 * Production implementation placeholder
 * Replace simulateAIResponse with actual API call
 */
export async function callLLMAPI(
  prompt: string,
  model: string = "gpt-4",
  temperature: number = 0.3
): Promise<AIResponse> {
  const startTime = Date.now();
  
  // Production: Implement actual API call
  // Example for OpenAI:
  /*
  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [{ role: "user", content: prompt }],
      temperature,
      response_format: { type: "json_object" },
    }),
  });
  
  const data = await response.json();
  return {
    content: data.choices[0].message.content,
    tokensUsed: data.usage.total_tokens,
    latencyMs: Date.now() - startTime,
  };
  */
  
  // For now, use simulation
  return callVetAI({ prompt, temperature });
}
