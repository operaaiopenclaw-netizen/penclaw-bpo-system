# 🎛️ BENCHMARK FINAL - Motores LLM OpenClaw

## Data: 2026-04-04
## Status: PARCIAL (Backend bloqueado DATABASE_URL)

---

## ✅ TAREFAS CONCLUÍDAS

### Task 1: Interpretação de Contrato

| Motor | Tempo | Tokens In | Tokens Out | Nota | Destaque |
|-------|-------|-----------|------------|------|----------|
| **Kimi K2.5** | 19s | 12.9k | 1.8k | **9.5/10** | Detectou cláusula abusiva (multa 100% contestável) |
| **Gemma** | 7s | 12.9k | 832 | 8.0/10 | Velocidade superior (4x mais rápida) |
| **Qwen** | 16s | 12.9k | 1.1k | 8.5/10 | Estrutura JSON perfeita c/ valores calculados |

**Vencedor T1: Kimi** (qualidade jurídica superior)

### Task 3: Checklist Operacional

| Motor | Tempo | Status | Nota | Destaque |
|-------|-------|--------|------|----------|
| **Kimi K2.5** | 90s | ⚠️ Timeout | **9.0/10** | Ratios calculados (1:10 staff), termos técnicos |
| **Gemma** | 59s | ✅ Completo | 8.5/10 | Fases bem definidas |
| **Qwen** | 90s | ⚠️ Timeout | 8.0/10 | Cálculo: '3L bebida/pessoa para 6h' |

**Vencedor T3: Kimi** (profundidade técnica)

---

## ❌ TAREFAS BLOQUEADAS

### Task 2: Criação de Agent Run
**Bloqueio:** Backend OFF - Erro `DATABASE_URL`

### Task 4: Risk/Approval Evaluation  
**Bloqueio:** Backend OFF - Policy engine não testável

### Task 5: Tooling Execution
**Bloqueio:** Backend OFF - Precisa do orchestrator

---

## 📊 MÉDIAS GERAIS

| Motor | Velocidade Média | Qualidade Média | Consistência |
|-------|-----------------|-----------------|--------------|
| **Kimi K2.5** | 54.5s | **8.75/10** | ⭐⭐⭐⭐⭐ |
| **Gemma** | 33s | 8.25/10 | ⭐⭐⭐⭐ |
| **Qwen** | 53s | 8.25/10 | ⭐⭐⭐⭐ |

---

## 🏆 CLASSIFICAÇÃO FINAL

| Categoria | Vencedor |
|-----------|----------|
| **Melhor Qualidade** | Kimi K2.5 |
| **Melhor Velocidade** | Gemma |
| **Melhor Custo-Benefício** | Gemma |
| **Mais Detalhado** | Kimi K2.5 |
| **Consistência JSON** | Qwen |

---

## 🎯 RECOMENDAÇÃO

### Arquitetura HÍBRIDA

```
┌─────────────────────────────────────────┐
│  FAST PATH (Gemma)                      │
│  • Checklists operacionais              │
│  • Geração rápida de documentos         │
│  • Tarefas de baixa complexidade        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  DEEP PATH (Kimi)                       │
│  • Análise de contratos                 │
│  • Avaliação de riscos                  │
│  • Decisões estratégicas                │
│  • Tarefas de alta criticidade          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  STRUCTURED PATH (Qwen)                 │
│  • Formatação JSON precisa              │
│  • Validação de schemas                 │
│  • Serialização de dados                │
└─────────────────────────────────────────┘
```

---

## 🔧 BLOQUEIO TÉCNICO

**Erro:** `Database 'openclaw_db' does not exist`

**Causa:** Runtime está buscando `openclaw_db` mas `.env` configura `openclaw`

**Possíveis fix:**
1. Verificar cache de variáveis de ambiente
2. Verificar outro arquivo .env no sistema
3. Reiniciar com `unset DATABASE_URL`

---

## 📝 PRÓXIMO PASSO

1. Resolver conflito DATABASE_URL
2. Subir backend
3. Executar Tasks 2, 4, 5 em cada motor
4. Completar benchmark com aderência ao runtime

---

*Relatório gerado: 2026-04-04 15:43 UTC-3*
*Motores: Kimi K2.5 (Together), Gemma 2 (Google), Qwen 2.5 (Alibaba)*
