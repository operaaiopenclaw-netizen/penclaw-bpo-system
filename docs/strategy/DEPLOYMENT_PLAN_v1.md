# ORKESTRA.AI — PLANO DE DEPLOYMENT v1

**Data:** 2026-04-18
**Status técnico:** Sprints 1–6 concluídos. Loop fechado (forecast → procure → produce → consume → reconcile → learn). API + canais + dashboard + alertas operacionais.
**Status operacional:** desenvolvimento. Falta decisão humana, RBAC real, deploy gerenciado.

Este documento é o **gate entre sistema pronto e sistema em produção**. Foco: uso real — quem faz o quê, onde, quando, com quais permissões.

---

## 1) PLANO DE INTEGRAÇÃO REAL

### 1.1 Como eventos são criados

| Canal | Origem | Rota API | Quem usa | Frequência |
|---|---|---|---|---|
| **Dashboard web** | Admin cria manualmente em `/operations` | `POST /operations/webhooks/event` (form-backed) | Gerente comercial | Diária |
| **CRM pipeline** | Lead → Proposta → Contrato (aprovado) dispara criação automática | `crm_agent` workflow cria Event ao aprovar contrato | Automação | Por contrato |
| **WhatsApp/Telegram** | Sales envia texto estruturado ao bot | `POST /operations/webhooks/telegram` (bot parseia) | Sales externo | Baixa |
| **Webhook externo** | Integração com plataformas terceiras (ex.: Sympla, Eventbrite) | `POST /operations/webhooks/event` com HMAC | Sistema parceiro | Por evento |

**Decisão canônica:** dashboard = fonte primária. WhatsApp = atalho para sales em rota. CRM = backbone quando contratado.

### 1.2 Como o consumo é registrado

| Canal | Quem | Quando | Rota |
|---|---|---|---|
| **Dashboard mobile** (aba "Execução") | Kitchen lead / operador no evento | Em tempo real durante o evento | Form → `POST /operations/webhooks/consumption` |
| **Checklist pós-evento** | Kitchen lead | D+1 após o evento | Dashboard form → mesma rota |
| **Webhook de balança/POS** | Integração com balança inteligente ou sistema de cozinha | Automático, streaming | `POST /operations/webhooks/consumption` (autenticado) |

**Padrão mínimo:** entrada manual via dashboard. Upgrade futuro: leitor de código de barras + balança.

### 1.3 Como a produção é atualizada

| Evento | Disparo | Efeito |
|---|---|---|
| OS aprovada | Gerente clica "Aprovar" na aba OS | `productionEngine.planProduction()` cria PO + schedules |
| Início de produção | Kitchen lead clica "Iniciar" na aba OP | `ProductionSchedule.actualStart` preenchido, status `IN_PROGRESS` |
| Finalização de produção | Kitchen lead clica "Finalizar" | `completeProductionOrder()` → cria `EventConsumption` automaticamente (fecha loop Sprint 5) |
| Atraso | Kitchen lead preenche `delayReason` | Alerta `PRODUCAO_SOBRECARGA` dispara via canais |

**Fonte de verdade:** dashboard. Webhook `/operations/webhooks/production` para casos de integração terceira.

---

## 2) PAPÉIS DE USUÁRIO

Quatro papéis funcionais. Schema atual tem `admin|user|viewer` — precisa migrar para o modelo abaixo **antes do piloto**.

### 2.1 Matriz de responsabilidades

| Papel | Principais ações | Não pode |
|---|---|---|
| **Operator** (event-ops) | Ver pipeline, marcar execução, registrar consumo no campo, ver alertas do próprio evento | Criar OS, aprovar PO, mexer em preços |
| **Manager** (operações/comercial) | Criar/aprovar OS, aprovar POs R1/R2, dispensar alertas, ver todos eventos | Fechar mês, alterar RBAC |
| **Finance** | Aprovar POs R3 (alto risco), ver margem real vs projetada, fechar reconciliações, exportar relatórios | Marcar produção concluída, criar OS |
| **Kitchen** | Ver OPs do dia, marcar início/fim de produção, registrar consumo, reportar desperdício | Ver margem financeira, aprovar nada |
| **Admin** (interno) | Tudo + gerenciar usuários + configurar canais (Telegram, webhook) | — |

### 2.2 Matriz de permissões por rota

| Rota | operator | manager | finance | kitchen | admin |
|---|---|---|---|---|---|
| `GET /operations/overview` | ✅ | ✅ | ✅ | ✅ (limitado) | ✅ |
| `POST /operations/webhooks/event` | ❌ | ✅ | ❌ | ❌ | ✅ |
| `POST /operations/webhooks/consumption` | ✅ | ✅ | ❌ | ✅ | ✅ |
| `POST /operations/webhooks/production` | ❌ | ✅ | ❌ | ✅ | ✅ |
| `POST /operations/reconcile` | ❌ | ✅ | ✅ | ❌ | ✅ |
| `POST /approvals/:id/approve` (R3) | ❌ | ❌ | ✅ | ❌ | ✅ |
| `POST /approvals/:id/approve` (R1/R2) | ❌ | ✅ | ✅ | ❌ | ✅ |
| `GET /intelligence/*` | ❌ | ✅ | ✅ | ❌ | ✅ |
| `GET /operations/risks` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /operations/alerts/evaluate` | ❌ | ✅ | ✅ | ❌ | ✅ |

### 2.3 Mudanças necessárias no código antes do piloto

1. `src/middleware/auth.ts` — expandir enum `role` para `operator|manager|finance|kitchen|admin`.
2. Adicionar `User` + `UserRole` ao schema.prisma (hoje não existe).
3. Aplicar `requireRole(...)` nas rotas conforme matriz acima.
4. Tela de login + gestão de usuários (admin-only) no dashboard.
5. Token refresh + logout funcional.

---

## 3) FLUXOS OPERACIONAIS

### 3.1 Ciclo de vida do evento (end-to-end)

```
[Sales]  Lead registrado
   ↓
[Manager] Proposta enviada
   ↓
[Finance] Contrato assinado → Event criado (T-30 dias)
   ↓
[Manager] OS aprovada (T-14 dias)
   ↓
[System] Forecast + ProcurementDecisions geradas automaticamente
   ↓
[R1 auto] POs confirmados direto
[R2]     → fila /approvals — Manager aprova (T-7 dias)
[R3]     → fila /approvals — Finance aprova (T-7 dias)
   ↓
[Kitchen] ProductionSchedules geradas (T-1 dia)
   ↓
[Kitchen] Produção executada (D-Day)
   ↓
[Operator] Consumo registrado durante o evento
   ↓
[System]  Reconciliation automática (D+1)
   ↓
[Finance] Revisão de margem real; feedback loop ativo
```

**Gates humanos obrigatórios:** contrato (jurídico), OS (comercial), PO R3 (finance), margem real <15% (finance).

### 3.2 Fluxo de procurement

1. Forecast roda a cada mudança de OS ou cron diário para eventos próximos.
2. `ProcurementEngine` classifica decisões:
   - **R1** (rotina, valor < R$5k, fornecedor preferred): confirmed direto
   - **R2** (R$5k–R$20k): `pending_approval` → Manager aprova
   - **R3** (>R$20k ou margem afetada): `pending_approval` → Finance aprova
3. Aprovação dispara envio do PO (por enquanto: e-mail manual; fase 2: EDI/API do fornecedor).
4. Recebimento registrado por Operator na entrega → `PurchaseOrderItem.quantityReceived`.
5. Supplier score atualizado (entrega + qualidade) a cada recebimento.

### 3.3 Fluxo de produção

1. Ao aprovar OS, `planProduction()` cria `ProductionOrder` + `ProductionSchedule` por estação.
2. `getStationLoad()` roda diariamente — se utilization > 100%, alerta dispara para Manager.
3. Kitchen lead abre aba OP, vê lista do dia ordenada por `scheduledStart`.
4. Botão "Iniciar" preenche `actualStart`; "Finalizar" chama `completeProductionOrder()`.
5. Consumo dos insumos é calculado e gravado em `EventConsumption` automaticamente.
6. Divergência (producedQuantity vs plannedQuantity) gera memória de padrão para próximo forecast.

### 3.4 Tratamento de alertas

| Severidade | Canal primário | Canal secundário | SLA resposta | Escalonamento |
|---|---|---|---|---|
| CRITICAL | Telegram (instant) + Email | Dashboard toast | 15 min | Auto-ping Manager se 15 min sem ack |
| HIGH | Telegram | Email diário | 2 h | Manager |
| MEDIUM | Dashboard | Email diário | Próximo ciclo | — |
| LOW | Dashboard | — | — | — |

- Alertas persistem em `MemoryItem` (já implementado).
- Ack explícito = registrar decisão (aprovar / ignorar / delegar) com justificativa.
- Dashboard mostra alertas não-ack em badge vermelho no header.

**Cron sugerido:** `POST /operations/alerts/evaluate` para cada evento dos próximos 14 dias, a cada 30 min entre 08:00–20:00.

---

## 4) SETUP MÍNIMO DE PRODUÇÃO

### 4.1 Infraestrutura

| Componente | Tecnologia atual | Recomendação produção | Custo/mês estimado |
|---|---|---|---|
| **Banco principal** | Postgres local (brew) | Managed Postgres — Supabase / Neon / AWS RDS t3.small | R$150–400 |
| **Cache + fila** | Redis (colima local — quebrado) | Upstash Redis serverless ou Elasticache | R$0–150 |
| **API** | Fastify node local | Railway / Fly.io / VPS (Hetzner ~R$100) | R$100–300 |
| **Dashboard** | HTML estático servido local | Vercel / Netlify / S3+CloudFront | R$0 |
| **Storage de artefatos** | `./storage/artifacts` (local) | S3 / R2 com lifecycle rules | R$20–50 |
| **Observabilidade** | pino log no stdout | Grafana Cloud free tier + Sentry | R$0 |
| **Secrets** | `.env` | Doppler / AWS Secrets Manager / Railway vars | R$0–50 |

**Total mínimo: R$270–950/mês** para operar 3 empresas (QOpera + Laohana + Robusta).

### 4.2 Pontos de acesso

| Componente | URL de produção | Autenticação |
|---|---|---|
| Dashboard web | `https://ops.orkestra.ai` | JWT via login + refresh token |
| API REST | `https://api.orkestra.ai` | JWT Bearer no header |
| Swagger docs | `https://api.orkestra.ai/docs` | Admin-only (basic auth) |
| Telegram bot | `@OrkestraOpsBot` | chat_id whitelist por tenant |
| Webhook genérico | `https://api.orkestra.ai/operations/webhooks/*` | HMAC-SHA256 assinado com secret por integração |

### 4.3 Permissões e segurança

1. **Tenant isolation**: já implementado (`tenantId` em todos os models). Antes do piloto: adicionar middleware que injeta `tenantId` a partir do token JWT e bloqueia cross-tenant.
2. **HMAC em webhooks externos**: verificar header `x-orkestra-signature` antes de aceitar payload.
3. **Rate limit por rota**: `rate-limit.ts` existe — aplicar agressivo nos webhooks (100 req/min/IP) e em login (10/min).
4. **Dados sensíveis**: preços de fornecedor e margem só via role `manager`/`finance`.
5. **Auditoria**: toda mudança de status vai pro `MemoryItem` com `sourceRef`; log append-only.
6. **Backup**: Postgres daily snapshot (managed provider cuida) + `pg_dump` semanal pra S3 redundante.
7. **Monitoramento**: alerta SLO em p95 > 500ms na API, erro > 1% em 5 min.

---

## 5) ESTRATÉGIA DE ROLLOUT

Três fases gated por evidência, não por tempo.

### Fase 0 — Shadow mode (1 semana)

**Objetivo:** sistema roda em paralelo ao processo atual, mas não executa nada.

- Deploy em staging com dados reais.
- Forecast roda para eventos reais. Decisões vão pra fila mas não são aprovadas.
- Alertas disparam para canal privado do time (não pro cliente final).
- Comparar decisões do sistema com decisões reais do time. Medir: quantas bateriam? quantas seriam erradas?
- **Gate de saída:** ≥80% das decisões R1 do sistema coincidem com o que o time fez manualmente.

### Fase 1 — Piloto (1 evento de baixo risco)

**Objetivo:** uma empresa, um evento, aprovação humana em tudo.

- Escolher evento **pequeno** (≤50 convidados) e **distante** (≥21 dias) de **QOpera** (maior histórico).
- Todas as POs exigem aprovação manual (mesmo R1).
- Consumo registrado manualmente pela equipe de cozinha na dashboard.
- Reconciliação rodada com Finance presente na sala.
- **Sucesso = zero erro operacional + margem real dentro de ±3pp da projetada.**
- Duração: 1 semana do evento ao fechamento.

### Fase 2 — Small batch (4–6 eventos, 2–3 semanas)

**Objetivo:** sistema suporta cadência real de uma empresa.

- Todos os eventos de QOpera nesse período.
- R1 passa a ser auto-confirmado. R2/R3 seguem manual.
- Kitchen registra produção via dashboard (sem webhook externo ainda).
- Telegram bot ativo para alertas CRITICAL/HIGH.
- **Gate:** accuracy média ≥75%, zero alerta CRITICAL sem ack em 15 min, feedback positivo de ≥3/4 papéis.

### Fase 3 — Rollout completo (mês 2)

**Objetivo:** QOpera + Laohana + Robusta em produção.

- Onboarding de Laohana e Robusta semana por semana (dados históricos importados via `import_yohanna_inventory.ts` + scripts equivalentes).
- Adjustments aprendidos de QOpera servem como prior para as outras (eventType + category).
- Relatório semanal executivo gerado automaticamente (workflow `ceo_daily_briefing` existente).
- SLA 99.5% uptime. Suporte 8h/dia nas primeiras 4 semanas de cada onboarding.

### Critérios de abort (qualquer fase)

- Margem real <10% por 2 eventos consecutivos em empresas diferentes → pausa, auditoria do forecast.
- Alerta CRITICAL ignorado que resultou em falta de produto no evento → pausa, revisão do dispatch.
- Vazamento de dados cross-tenant → rollback imediato, investigação.

---

## 6) CHECKLIST DE "DEIXAR O DEV MODE"

Pré-piloto (Fase 1), em ordem:

- [ ] DB gerenciado provisionado + migração aplicada + backup validado
- [ ] Redis gerenciado provisionado + worker conectado
- [ ] API deployada com domínio HTTPS e health check público
- [ ] Dashboard buildado e servido em CDN
- [ ] Secrets movidos de `.env` para secret manager
- [ ] `User` + `UserRole` schema criado; 4 papéis implementados; `requireRole` aplicado em todas as rotas sensíveis
- [ ] Tela de login + gestão de usuários no dashboard
- [ ] Multi-tenant middleware (inject `tenantId` from JWT, block cross-tenant)
- [ ] HMAC em webhooks externos
- [ ] Telegram bot configurado com `TELEGRAM_BOT_TOKEN` + whitelist de chat_id
- [ ] Webhook de alertas `WEBHOOK_URL` apontando para ferramenta de ops (Slack/Discord)
- [ ] Cron de `alerts/evaluate` agendado (Fly.io scheduled machines ou similar)
- [ ] Logs centralizados + alerta de erro
- [ ] Runbook escrito: o que fazer quando alerta CRITICAL chega, como pausar decisões, como rollback

Nada do acima é código novo — é **operacionalização do que já existe**.

---

## RESUMO EXECUTIVO

Sistema técnico: **pronto**. Faltam três coisas para produção:

1. **Papéis reais** (operator/manager/finance/kitchen) substituindo `admin|user|viewer`.
2. **Infra gerenciada** (DB, Redis, API, dashboard) em vez de local.
3. **Rollout gated**: shadow → piloto 1 evento → 5 eventos → 3 empresas.

Ordem de ataque sugerida: papéis (1 semana) → infra (1 semana) → shadow mode (1 semana) → piloto (1 semana). **Um mês até o primeiro evento real.**
