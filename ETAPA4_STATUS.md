# ETAPA 4 - APPROVAL RESUME / REPLAY / ARTIFACTS

**Status:** ✅ IMPLEMENTADO - 2026-04-04

---

## ✅ IMPLEMENTAÇÕES

### 1. Approval Resume
**Arquivo:** `src/controllers/approval-controller.ts`

```typescript
// Ao aprovar (POST /approvals/:id/approve):
if (body.approved) {
  orchestrator.resume(approval.agentRunId)
}
```

**Comportamento:**
- Aprovação atualiza status: `waiting_approval` → `running`
- Busca step pendente e completa
- Retoma orchestrator do ponto de parada
- Continua execução dos steps restantes

### 2. Replay de Runs
**Arquivo:** `src/controllers/agent-run-controller.ts` + `src/routes/agent-runs.ts`

```typescript
// POST /agent-runs/:id/replay
async replay(req, reply) {
  // 1. Busca run original
  // 2. Parse do inputSummary
  // 3. Cria novo run com mesmos params
  // 4. Retorna novo runId
}
```

**Comportamento:**
- Duplica input original
- Cria novo run com novo ID
- Executa do início (não retoma)
- GET /agent-runs mostra ambos (histórico separado)

### 3. Artifacts
**Arquivo:** `src/orchestrator.ts`

```typescript
// Em executeStep, ao completar:
if (shouldCreateArtifact) {
  await prisma.artifact.create({
    agentRunId,
    artifactType: "checklist" | "report" | "json" | "csv",
    fileName: `${agentName}_step${stepOrder}_${type}.json`,
    metadata: { ... }
  })
}
```

**Tipos criados:**
- `checklist` - Checklists operacionais
- `report` - Resumos e análises
- `json` - Dados estruturados
- `csv` - Exportações tabulares

---

## 🔄 FLUXO DE VIDA DO RUN

```
pending → running → waiting_approval ─┬─→ approved → running → completed
                                        │
                                        └─→ rejected → (fim)
```

**Replay:**
```
completed_run ──► POST /:id/replay ──► new_pending_run
```

---

## 📁 ARQUIVOS ALTERADOS

```
src/controllers/approval-controller.ts    # resume()
src/controllers/agent-run-controller.ts     # replay()
src/routes/agent-runs.ts                    # POST /:id/replay
src/orchestrator.ts                         # resume() + artifacts
ETAPA4_STATUS.md                            # Este arquivo
```

---

## 🧪 TESTE SUGERIDO

### Testar Resume:
```bash
# 1. Criar run que gere approval (R3/R4)
curl -X POST http://localhost:3000/agent-runs \
  -H "Content-Type: application/json" \
  -d '{"companyId":"test","workflowType":"financial_transfer","input":{"amount":50000}}'

# 2. Verificar approval criado
curl http://localhost:3000/approvals/pending

# 3. Aprovar (deve retomar run)
curl -X POST http://localhost:3000/approvals/:id/approve \
  -d '{"approved":true}'

# 4. Verificar run completado
curl http://localhost:3000/agent-runs/:runId
```

### Testar Replay:
```bash
# 1. Criar run
curl -X POST http://localhost:3000/agent-runs ...

# 2. Aguardar completar

# 3. Replay
curl -X POST http://localhost:3000/agent-runs/:id/replay

# 4. Listar - deve mostrar 2 runs
curl http://localhost:3000/agent-runs
```

---

## 🎯 PRÓXIMA ETAPA (5)

Sugestões:
1. **Memória Operacional** - Integrar episodicMemory com contexto
2. **Cache de Steps** - Evitar reexecução de steps idênticos
3. **Dashboard** - UI para visualizar runs, approvals, artifacts
4. **Webhooks** - Notificar sistemas externos de eventos
5. **Métricas** - Latência, custos, sucesso/falha

---

*Atualizado: 2026-04-04 16:01*
