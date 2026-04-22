# Orkestra — Operational Runbook

Guia de resposta a incidentes, degradação e operações de rotina.
Escopo: operador de plantão + admin. Atualizado: 2026-04-22.

---

## 0) Primeiro minuto

Ao receber qualquer alerta:

1. Abrir `/operations/overview` → verificar `kpi-ops-upcoming` e `kpi-pos` estão de pé.
2. `curl https://<host>/ready` → confirmar DB + Redis.
3. Checar Telegram/webhook channel — conferir se o alerta chegou nos canais externos.
4. Registrar o horário e abrir ticket antes de agir.

---

## 1) Severidades & SLA

| Severidade | SLA ack | SLA fix | Exemplo |
|---|---|---|---|
| **CRITICAL** | 5 min  | 30 min | `ESTOQUE_INSUFICIENTE` em evento em <24h, `MARGEM_REAL_CRITICA` (<5%) |
| **HIGH**     | 15 min | 2 h    | `PRODUCAO_SOBRECARGA_CRITICA`, `MARGEM_REAL_BAIXA` (<15%) |
| **MEDIUM**   | 1 h    | 24 h   | `RECONCILIACAO_VARIANCIA_ALTA`, `FORECAST_ACCURACY_BAIXA` |
| **LOW**      | best-effort | — | `ESTOQUE_PROX_SEGURANCA` |

Regra: CRITICAL não-ackd em 15 min → escalar para admin.

---

## 2) Playbooks por alerta

### `ESTOQUE_INSUFICIENTE`
1. Rodar `GET /operations/risks?eventId=<id>` para o detalhamento.
2. Decisão:
   - Dá pra comprar a tempo? → criar PO manual (bypass fila automática) via `POST /intelligence/procure`.
   - Não dá? → negociar redução de cardápio com o cliente (operator + manager).
3. Atualizar estoque real via `POST /kitchen/inventory/adjust` quando entrega chegar.
4. Pós-mortem: evento → verificar por que forecast subiu de última hora.

### `MARGEM_REAL_CRITICA`
1. Congelar aprovações futuras do tenant: `PATCH /users/<id> { "isActive": false }` para todo role != admin (se hemorragia).
2. Rodar `POST /operations/reconcile` para confirmar números.
3. Comparar `projectedMargin` vs `realMargin` no `/operations/lifecycle/<eventId>`.
4. Decisão de parar o cicle loop: setar `ENABLE_AGENT_RUNS=false` e reiniciar API.

### `PRODUCAO_SOBRECARGA_CRITICA`
1. Olhar `/operations/risks` → quais stations estão sobrecarregadas.
2. Opções (em ordem): adicionar turno, redistribuir para outra station, terceirizar prep.
3. Após decisão: regravar `ProductionSchedule` via `/production-orders/<id>/reschedule`.

### `RECONCILIACAO_VARIANCIA_ALTA`
1. Comparar `EventConsumption` reportado vs forecast — geralmente é falha de registro pela cozinha.
2. Se real: `ItemAdjustment` foi atualizado automaticamente (EWMA). Não intervir por 2 eventos.
3. Se registro: corrigir via `PATCH /operations/webhooks/consumption` (admin-only em prod).

### Canal Telegram/Webhook silencioso
1. `GET /operations/channels` → ver `configured`.
2. Token expirado? Rotacionar via Secret Manager → redeploy.
3. Chat_id removido do whitelist? Conferir `TELEGRAM_ALLOWED_CHATS`.

---

## 3) Pausar o sistema

Ordem (menos → mais invasivo):

1. **Pausar notificações**: remover `TELEGRAM_ALLOWED_CHATS` + `WEBHOOK_URL` do env, redeploy.
2. **Pausar decisões automáticas**: `ENABLE_AGENT_RUNS=false`.
3. **Kill switch total**: desativar todos os users não-admin com
   ```sql
   UPDATE users SET is_active=false WHERE role <> 'admin';
   ```
4. **Emergência absoluta**: `fly scale count=0` (API fica off).

---

## 4) Rollback

- **Schema**: `git revert <migration commit>` + `npx prisma migrate deploy` (staging primeiro).
- **Código**: `fly deploy --image <previous tag>` — nunca faça hotfix em prod sem PR.
- **Dados**: restore do último snapshot gerenciado (RDS/Neon/Fly Postgres). NUNCA `pg_restore` sem double-check de tenant isolation.

---

## 5) Rotação de credenciais

Frequência mínima: **90 dias** (JWT_SECRET, WEBHOOK_HMAC_SECRET, DATABASE_URL).

Procedimento JWT_SECRET:
1. Emitir novo secret no Secret Manager.
2. Subir API com `JWT_SECRET_NEXT=<novo>` enquanto `JWT_SECRET=<antigo>` (suporte dual-sign).
3. Invalidar todos os tokens emitidos antes da rotação: `UPDATE users SET last_login_at=NULL;` (força re-login).
4. Em 24h promover `JWT_SECRET_NEXT` → `JWT_SECRET`.

Procedimento WEBHOOK_HMAC_SECRET: idem, porém coordenar com consumidores externos.

---

## 6) Template de incidente

```
## Incidente <ID curto>
- Início: <ISO datetime>
- Severidade inicial: CRITICAL/HIGH
- Alertas disparados: <lista>
- Impacto: <eventos/tenants/ usuarios afetados>
- Ação imediata: <o que foi feito nos primeiros 15 min>
- Root cause: <a preencher no post-mortem>
- Prevenção: <nova regra/alert/test>
- Fechado em: <ISO datetime>
```

Salvar em `docs/incidents/YYYY-MM-DD-<slug>.md` e commitar no mesmo dia.

---

## 7) Contatos & escalação

- L1 (operator/manager): Telegram group `@orkestra-ops`.
- L2 (finance/admin): Telegram `@orkestra-admin` + PagerDuty.
- Vendor BD (managed Postgres): ver `ops/vendor-contacts.md`.
- Vendor Redis: idem.

---

## 8) Checklist de final de plantão

- [ ] Todos os alertas CRITICAL/HIGH do turno estão ack'd.
- [ ] `/ready` verde.
- [ ] Nenhuma aprovação pendente há mais de 2h sem motivo.
- [ ] Handoff no Telegram com resumo em 3 bullets.
