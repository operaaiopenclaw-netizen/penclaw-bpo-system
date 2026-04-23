# Orkestra.AI — Auditoria de Features
_Data: 2026-04-23_

Varredura completa: rotas backend × páginas dashboard × fluxos de negócio.

---

## ✅ O que já está funcional (backend + UI)

| Domínio | Backend | UI | Status |
|---|---|---|---|
| **Auth** (login, JWT, roles) | `auth.ts`, `users.ts` | `login.html`, `users.html` | Completo |
| **CRM** (leads, propostas, contratos) | `crm.ts` | `crm.html` | Completo |
| **Eventos** (event-store + state machine) | `events.ts`, `states.ts` | `events.html` | Completo |
| **OS** (ordens de serviço) | `service-orders.ts` | `service-orders.html` | Completo |
| **OP** (ordens de produção) | `production-orders.ts` | `production-orders.html` | Completo |
| **Execução** (sessões, checkpoints) | `execution.ts` | `execution.html` | Completo |
| **Cozinha/CMV** (Python bridge) | `kitchen.ts` | `kitchen.html` | Completo |
| **Comercial** (comissões, bônus) | `commercial.ts` | `commercial.html` | Completo |
| **Aprovações** (risk-gated) | `approvals.ts` | `approvals.html` | Completo |
| **Operações** (agregador) | `operations.ts` | `operations.html` | Completo |
| **Financeiro** (dashboard principal) | `dashboard.ts` | `index.html` | Completo |

---

## 🔴 Gaps críticos — backend existe, UI falta

São rotas já implementadas sem tela correspondente. Cada uma é uma feature
perdida até criar UI.

### 1. `aiChat.ts` — **CHAT COM IA** ⚠️ PRIORIDADE MÁXIMA
Você tem conversação com os agentes (eles são o cérebro do sistema) mas não tem
onde conversar. Toda interação com IA é "invisível" hoje.
- **Cria tela:** `ai-chat.html` com janela tipo Claude/ChatGPT
- **Peso de produto:** é o diferencial vs ERP. Sem isso, a "AI" fica só no slogan.
- **Deve aparecer:** atalho ⌘K global + aba dedicada

### 2. `agent-runs.ts` — **Logs de execução dos agentes**
Auditoria de quando cada agente rodou, input/output, duração, custo.
- **Cria tela:** `agent-runs.html` — tabela com filtro por agente, timeline
- **Porquê importa:** debugging + compliance (mostrar "a IA fez X porque...")

### 3. `artifacts.ts` — **Explorador de artefatos**
Relatórios gerados, CSVs, PDFs, planos de ação que a IA produz.
- **Cria tela:** `artifacts.html` — lista com preview + download
- **Uso:** cliente baixa relatório mensal, PDF de evento, CSV de comissão

### 4. `memory.ts` — **Memória dos agentes**
Contexto persistente que os agentes acumulam (preferências do cliente, histórico).
- **Cria tela:** `memory.html` — visualizar + editar memória por tenant/agente
- **Porquê importa:** cliente quer "saber o que a IA lembra sobre ele"

### 5. `intelligence.ts` — **Insights e análises**
Camada de BI: tendências, anomalias, recomendações proativas.
- **Cria tela:** `intelligence.html` — dashboard de insights semanais/mensais
- **Uso:** "evento Y teve margem 12% abaixo do padrão — 3 possíveis causas"

### 6. `metrics.ts` — **Observabilidade**
Métricas operacionais (latência, uso, custos de IA, uptime).
- **Cria tela:** `metrics.html` — admin-only. Gráficos de request/s, token spend.
- **Uso:** você, admin, monitora saúde da plataforma

---

## 🟡 Gaps de domínio — features esperadas num BPO que ainda não existem

Listadas pelo impacto de negócio, não pelo esforço.

### Alto impacto
- **Faturamento / NF-e / Boletos**
  - Emitir nota fiscal de serviço, gerar boleto cobrança.
  - Integração: Asaas, Iugu, ou NFSe.io.
  - **Porquê crítico:** sem isso, cliente ainda depende de outro sistema para cobrar.

- **Pipeline de vendas visual (Kanban)**
  - Hoje `crm.html` é tabela. Falta Kanban drag-drop para SDR usar.
  - **Porquê:** SDR é visual, não tabular.

- **Calendário operacional unificado**
  - Ver eventos, OSs, OPs e execuções em uma grade semanal/mensal.
  - **Porquê:** gerente olha "o que tem na semana que vem" — hoje precisa abrir 4 telas.

- **Estoque e ingredientes (master)**
  - CMV já funciona, mas falta cadastro mestre de ingredientes com preços históricos,
    fornecedores e alertas de ruptura.

- **Fornecedores**
  - Cadastro + histórico de compras + performance (prazo, qualidade).
  - Base para negociação.

- **Integração WhatsApp / Telegram**
  - Há `TELEGRAM_COMMANDS_GUIDE.md` no repo sugerindo que começou. Finalizar.
  - **Peso:** BPO sem canal de mensagem é cego.

### Médio impacto
- **Onboarding multi-tenant** (criar novo cliente em 1 clique, com seed de dados)
- **Relatórios agendados** (PDF semanal para CEO, sem pedir)
- **Dark-launch de agentes** (rodar em sombra antes de promover a produção)
- **Webhooks out** (cliente recebe ping quando evento fecha)
- **API pública + API keys por tenant** (cliente integra com sistema próprio)
- **Billing / planos** (free, pro, enterprise — se for SaaS multi-cliente)

### Baixo impacto (nice-to-have)
- **Temas claro/escuro alternáveis** (hoje só dark)
- **i18n** (PT-BR + EN — no futuro LATAM)
- **Mobile responsive** (tabelas quebram abaixo de 900px hoje)
- **PWA / app mobile** (instalar no home screen)

---

## 🔵 Gaps de infraestrutura / operação

- **Sentry** (monitoramento de erros em produção) — mencionado no backlog
- **Testes de integração para /commercial/*** — mencionado no backlog
- **Backup automatizado do Postgres** (Railway tem, mas validar retenção)
- **Staging environment** (hoje só production)
- **CI/CD com lint + test gate antes do deploy**
- **Status page pública** (para clientes enterprise)
- **LGPD: política de dados + cookie banner + direito ao esquecimento**

---

## 🎯 Roadmap sugerido (ordem de execução)

**Sprint 1 (essencial antes de vender):**
1. Logo final + aplicar em login + favicon
2. Tela ai-chat.html (é o ativo mais valioso escondido)
3. Site institucional + domínio
4. Registro de marca (em paralelo, é lento)

**Sprint 2 (antes de primeiro cliente pago):**
5. Faturamento (NF-e + boleto)
6. WhatsApp integration
7. Calendar view
8. Kanban CRM

**Sprint 3 (escalar):**
9. Multi-tenant onboarding
10. Billing / planos
11. API pública
12. Sentry + staging

---

## 📌 O que eu pontuaria como "você deixou passar"

Em ordem de gravidade:

1. **AI Chat** — você tem o cérebro pronto e não expôs a janela de conversa. É como ter ChatGPT sem interface.
2. **Faturamento** — um BPO que não cobra não fecha o ciclo.
3. **WhatsApp** — mercado brasileiro não opera sem isso.
4. **LGPD** — se for vender pra empresa, alguém vai pedir DPA em até 3 meses.
5. **Mobile responsive** — metade dos usuários operacionais vão abrir no celular.

Sobre o que está no repo: achei `QR_GENERATOR_SYSTEM.py`, `SDR_AI_VOICE_WHATSAPP_v1.md`,
`SALES_ENGINE_v1.md` — são planos/rascunhos que nunca viraram produto.
Vale decidir: cada um é **ship** (implementa agora), **shelf** (guarda na prateleira) ou **scratch** (apaga do repo).
