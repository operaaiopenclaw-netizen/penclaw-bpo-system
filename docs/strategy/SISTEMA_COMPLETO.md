# 🎛️ SISTEMA ORKESTRA - VERSÃO OPERACIONAL

**Data:** 2026-04-04
**Status:** PRONTO PARA TESTE REAL

---

## ✅ FLUXO COMPLETO IMPLEMENTADO

### 1. Requisição Entra
```
POST /agent-runs
{
  "companyId": "sua-empresa",
  "workflowType": "contract_onboarding",
  "input": {
    "clientName": "João Silva",
    "eventType": "casamento",
    "eventDate": "2026-05-15",
    "numGuests": 150,
    "venue": "Espaco Gardens"
  }
}
```

### 2. Sequência de Agentes Executa

| Ordem | Agente | Saída | Artifact |
|-------|--------|--------|----------|
| 1 | contract_agent | Campos extraídos, obrigações | - |
| 2 | sales_agent | Proposta formatada, follow-up | **proposal** |
| 3 | operations_agent | Checklist completo, riscos | **checklist** |
| 4 | supply_agent | Lista de compras, previsões | **supply_plan** |
| 5 | finance_agent | Análise financeira | - |
| 6 | reporting_agent | Resumo executivo | - |

### 3. Alertas Gerados (automático)
- Evento >200 pessoas → ALERTA LOGÍSTICO
- Margem <20% → ALERTA FINANCEIRO
- Prazo <7 dias → ALERTA OPERACIONAL

### 4. Artifacts Persistidos
```
GET /agent-runs/:id → retorna com:
- artifacts[] (proposal, checklist, supply_plan)
- steps[] (logs detalhados)
- approvals[] (se houver)
- alerts[] (via memory)
```

---

## 📊 DADOS DE NEGÓCIO COLETADOS

### Métricas Disponíveis
- `GET /metrics` → runs, steps, latência
- `GET /metrics/business` → propostas, margens, conversão
- `GET /memory/:companyId` → decisões, alertas, padrões

### Memory Logs (automático)
- Tipo: "decision" → steps completados
- Tipo: "alert" → riscos detectados
- Tipo: "error" → falhas
- Tipo: "pattern" → para futura IA

---

## 🎯 VALIDAÇÃO COM EVENTOS REAIS

### Teste Simples:
```bash
# 1. Criar evento
POST /agent-runs
{
  "companyId": "teste-real-001",
  "workflowType": "contract_onboarding",
  "input": {
    "clientName": "Cliente Real",
    "eventType": "formatura",
    "eventDate": "2026-06-20",
    "numGuests": 120,
    "venue": "Local Real",
    "budget": 35000
  }
}

# 2. Aguardar 5-10s

# 3. Verificar resultado
GET /agent-runs/:id

# Deve retornar:
# - status: "completed"
# - artifacts: [proposal, checklist, supply_plan]
# - steps: logs de cada agente
```

### Critérios de Sucesso:
- [ ] Proposta gerada em <30s
- [ ] Checklist coerente com tipo de evento
- [ ] Supply plan com quantidades realistas
- [ ] Nenhum campo obrigatório faltando
- [ ] Alertas pertinentes (se aplicável)

---

## 🔧 PRÓXIMOS AJUSTES (pós-teste real)

1. **Custo/cobrir:** Base de preços reais vs estimados
2. **Staff ratio:** 1 garçom/25 ou 1/30? (testar)
3. **Consumo:** Ajustar regras supply_agent
4. **Follow-up:** Template de mensagem WhatsApp
5. **Alertas:** Thresholds reais (não genéricos)

---

## ⚡ PRONTO PARA USO

**Commits:** `fd42b2f`, `22a8515`
**Rotas ativas:** /agent-runs, /approvals, /metrics, /memory
**Backend:** UP (quando reiniciar)

```bash
# Comando para testar:
curl -X POST http://localhost:3000/agent-runs \
  -H "Content-Type: application/json" \
  -d '{"companyId":"seu-negocio","workflowType":"contract_onboarding","input":{"clientName":"Teste","eventType":"casamento","eventDate":"2026-05-20","numGuests":100}}'
```

**Sistema completo. Pronto para evento real.** ✅
