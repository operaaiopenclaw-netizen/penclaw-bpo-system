# PRÓXIMOS PASSOS - Orkestra Finance Brain

## 🔜 ETAPA 5: Dashboard + Integrações

### 1. Dashboard Visual
- [ ] UI para visualizar runs em tempo real
- [ ] Cards de métricas (runs/status, tempo médio)
- [ ] Lista de approvals pendentes
- [ ] Timeline de steps

### 2. Webhooks Externos
- [ ] POST configurável em eventos
- [ ] Eventos: run.created, step.completed, approval.requested
- [ ] Retry com backoff

### 3. Testes E2E
- [ ] Suite de testes: criar run → completar → verificar
- [ ] Teste de resiliência: falhas, retries
- [ ] Teste de carga: múltiplos runs paralelos

### 4. Documentação
- [ ] OpenAPI completo (/docs)
- [ ] README atualizado
- [ ] Guia de integração

## 🎯 V2 - Aprimoramentos

### Performance
- [ ] Cache de steps idênticos
- [ ] Batch processing para runs similares
- [ ] Indexação avançada de memórias

### Recursos
- [ ] UI de configuração de workflows
- [ ] Editor de regras de policy
- [ ] Visualização de memórias (grafo)

### Integrações
- [ ] Slack notifications
- [ ] Email alerts
- [ ] Importação de dados externos

## ✅ COMPLETO (Etapas 1-4)
- Worker real ✅
- Orchestrator ✅
- Steps + Approvals ✅
- Resume + Replay ✅
- Artifacts ✅
- Memory ✅
- Metrics ✅

---
*Atualizado: 2026-04-04*
