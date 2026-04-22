// ============================================================
// VETAGENT: AI Prompt Builder
// ============================================================

import { VetContext } from "./types";

const SYSTEM_PROMPT = `Você é um Assistente Veterinário Inteligente.

SUA FUNÇÃO:
- Analisar sintomas e comportamentos relatados por tutores de pets
- Oferecer informações educativas sobre possíveis causas
- Orientar sobre próximos passos apropriados
- Reconhecer sinais de alerta que exigem atenção veterinária

REGRAS CRÍTICAS DE SEGURANÇA:
1. NUNCA forneça diagnósticos definitivos - sempre qualifique como "possível" ou "potencial"
2. NUNCA prescreva medicamentos específicos, dosagens ou tratamentos
3. NUNCA substitua o julgamento de um veterinário licenciado
4. SEMPRE recomende consulta veterinária para sintomas persistentes ou graves
5. Use linguagem cuidadosa: "pode indicar", "pode ser associado a", "aconselha-se"
6. Priorize a detecção de riscos - quando em dúvida, recomende atendimento

RED FLAGS (Sempre recomende atendimento imediato):
- Dificuldade respiratória ou sinais de asfixia
- Sangramento que não para com pressão direta
- Convulsões ou desmaios
- Inchaço abdominal rápido
- Vômito persistente (várias vezes ao dia ou por mais de 24h)
- Incapacidade de urinar (especialmente gatos machos)
- Trauma (atropelamento, queda de altura, mordida)
- Alteração de consciência ou desorientação súbita

ESTRUTURA DE RESPOSTA OBRIGATÓRIA:
Sua resposta deve ser um JSON válido com:
{
  "analysis": "Análise detalhada da situação em linguagem acessível",
  "possibleCauses": ["Causa potencial 1", "Causa potencial 2"],
  "severity": "low|medium|high",
  "recommendation": "Recomendação clara sobre próximos passos",
  "needsVet": boolean,
  "disclaimer": "Aviso obrigatório sobre limitações"
}

DISCLAIMER PADRÃO:
"⚠️ ESTA É UMA ORIENTAÇÃO INFORMATIVA E NÃO SUBSTITUI A AVALIAÇÃO DE UM VETERINÁRIO. Se o quadro persistir ou piorar, procure atendimento profissional imediatamente."

TOM:
- Empático e acolhedor
- Profissional mas acessível
- Clara sobre limitações
- Prioriza segurança do animal acima de tudo`;

/**
 * Build the complete AI prompt with pet context
 */
export function buildVetPrompt(context: VetContext, userQuestion: string): string {
  const redFlagsSection = context.redFlags.length > 0
    ? `ALERTAS DE SAÚDE IDENTIFICADOS:\n${context.redFlags.map(f => `⚠️ ${f}`).join("\n")}\n`
    : "";

  return `${SYSTEM_PROMPT}

---

CONTEXTO DO PET:
${context.petProfile}

${redFlagsSection}HISTÓRICO DE SAÚDE:
${context.healthSummary}

${context.vaccineStatus}

SITUAÇÃO ATUAL:
${context.symptomContext}

---

PERGUNTA DO TUTOR:
"""${userQuestion}"""

INSTRUÇÃO: Analise a situação com base no contexto acima. Retorne APENAS um JSON válido seguindo a estrutura especificada nas regras. Não inclua markdown, explicações adicionais ou texto fora do JSON.`;
}

/**
 * Build prompt for cases without pet data
 */
export function buildGenericVetPrompt(userQuestion: string): string {
  return `${SYSTEM_PROMPT}

---

CONTEXTO: Nenhum dado de pet disponível. Orientação baseada apenas na descrição do tutor.

PERGUNTA DO TUTOR:
"""${userQuestion}"""

INSTRUÇÃO: Forneça orientações gerais sobre o sintoma/comportamento descrito. Seja ainda mais conservador nas recomendações sem dados do pet. Retorne APENAS um JSON válido.`;
}

/**
 * Parse AI response to structured format
 */
export function parseVetResponse(rawResponse: string): {
  success: boolean;
  data?: {
    analysis: string;
    possibleCauses: string[];
    severity: string;
    recommendation: string;
    needsVet: boolean;
    disclaimer?: string;
  };
  error?: string;
} {
  try {
    // Try to extract JSON from various formats
    let jsonString = rawResponse.trim();
    
    // Remove markdown code blocks
    if (jsonString.startsWith("```json")) {
      jsonString = jsonString.replace(/^```json\s*/, "").replace(/\s*```$/, "");
    } else if (jsonString.startsWith("```")) {
      jsonString = jsonString.replace(/^```\s*/, "").replace(/\s*```$/, "");
    }

    const parsed = JSON.parse(jsonString);

    // Validate required fields
    if (!parsed.analysis || !Array.isArray(parsed.possibleCauses)) {
      throw new Error("Missing required fields in response");
    }

    // Normalize severity
    const severity = parsed.severity?.toLowerCase() || "medium";
    if (!["low", "medium", "high"].includes(severity)) {
      parsed.severity = "medium";
    }

    return {
      success: true,
      data: {
        analysis: parsed.analysis,
        possibleCauses: parsed.possibleCauses,
        severity: parsed.severity,
        recommendation: parsed.recommendation || "Consulte um veterinário para avaliação.",
        needsVet: parsed.needsVet ?? parsed.severity === "high",
        disclaimer: parsed.disclaimer || "⚠️ Orientação informativa - não substitui avaliação veterinária.",
      },
    };
  } catch (error) {
    return {
      success: false,
      error: `Failed to parse AI response: ${error instanceof Error ? error.message : "Unknown error"}`,
    };
  }
}
