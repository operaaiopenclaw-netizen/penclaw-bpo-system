# Orkestra · Arquitetura de Informação

## Seus questionamentos são válidos — aqui vai a explicação

### 1. CRM vs Comercial — **DECISÃO FINAL (2026-04-23)**

**Comercial = jornada do cliente até a assinatura do contrato.** Nada depois disso.
Abas do módulo Comercial:
- **Pipeline** (leads, qualificação, SDR → vendedor)
- **Propostas** (orçamentos enviados, negociação)
- **Contratos** (geração, assinatura, status)
- **Relatórios** de pipeline (taxa de conversão, tempo médio, funil)

**Pós-assinatura = onboarding em 3 áreas (não é Comercial):**
- **ADM** — cadastro do cliente, coleta de docs, setup de acesso
- **Financeiro** — cobrança, faturamento, provisão de comissão
- **Operações** — evento/OS/OP criado, agenda, responsáveis atribuídos

**Comissões saem do Comercial e vão para o Financeiro** — comissão é despesa, não venda.
Dentro do Financeiro, dashboard com:
- Provisão de comissão por período (mês / ano / vitalício)
- Payout efetivo
- Filtros: vendedor, cliente, evento
- Visual no dashboard financeiro principal

---

### 2. Eventos vs Operações

**Minha intenção original:**
- **Eventos** = domínio de negócio (festa da Yohanna, aniversário, casamento) — dados de UM evento específico
- **Operações** = tela meta/runtime (o que os **agentes** estão rodando, aprovações pendentes, audit log, saúde do sistema)

**Por que separei:** Eventos é o "o quê". Operações é o "como está sendo processado".

**Você está certo que o nome "Operações" é enganoso.** Deveria se chamar **"Sistema"** ou **"Runtime"** — é uma tela de SRE, não de operação diária. Proposta:
- Renomear "Operações" → **"Sistema"** (agent runs, aprovações, auditoria, métricas)
- "Eventos" fica como está (é o core do negócio de eventos)

---

### 3. Produção vs Cozinha

**Minha intenção original:**
- **Produção (OP)** = ordem de produção genérica (pode ser qualquer item, não só comida)
- **Cozinha/CMV** = específico da operação food: receitas, ingredientes, CMV calculado

**Por que separei:** Se no futuro Orkestra atender um cliente que produz brindes (não comida), "Produção" generaliza; "Cozinha" é um vertical.

**Você está certo que para cliente food isso duplica.** Proposta:
- **Módulo único "Produção"** com abas: Ordens (OP) · Receitas · Ingredientes · CMV
- A aba "Receitas/Ingredientes/CMV" só aparece se o tenant for do setor food (flag `tenant.industry = 'food'`)

---

## Nova arquitetura proposta (consolidada)

Em vez de 17 itens no nav, **11 grupos**:

| # | Módulo | Subseções (abas internas) | Roles |
|---|---|---|---|
| 1 | **Home** | KPIs globais, resumo diário | todos |
| 2 | **Calendário** | Semana / Mês unificado | todos |
| 3 | **Comercial** | Pipeline · Propostas · Contratos · Relatórios | admin, manager, finance, sales |
| 4 | **Onboarding** | Novos clientes pós-assinatura (ADM · Financeiro · Operações) | admin, manager, finance, operator |
| 5 | **Eventos** | Lista · Timeline · Execução ao vivo | admin, manager, operator |
| 6 | **Produção** | Ordens · Receitas · Ingredientes · CMV | admin, manager, operator, kitchen |
| 7 | **Financeiro** | DRE · Caixa · Faturamento · **Comissões** · Conciliação | admin, finance |
| 7 | **Marketing** | Campanhas · Criativos · Performance | admin, manager, finance |
| 8 | **WhatsApp** | Inbox · Envio · Templates | admin, manager, operator |
| 9 | **RH** | Vagas · Candidatos · Pré-seleção IA | admin, manager |
| 10 | **AI Chat** | Conversa com agentes | todos |
| 11 | **Sistema** | Agent Runs · Aprovações · Auditoria · Documentos · Usuários · Métricas | admin |

---

## Trade-off

**Benefício da consolidação:**
- Nav cabe em uma linha
- Menos confusão mental
- Abas agrupam o que pertence junto

**Custo:**
- Páginas ficam maiores (precisam de tabs internas)
- Refactor de nav + login redirect + algum HTML

**Recomendação:** fazer essa consolidação **agora, antes de adicionar mais features**. Senão vamos acumular 5 novas telas sobre uma IA já confusa.

Se você confirmar, eu:
1. Colapso CRM + Comercial numa única tela "Comercial" com 5 abas
2. Colapso OS + OP + Cozinha numa única tela "Produção" com 4 abas
3. Renomeio "Operações" → "Sistema" e agrupo agent-runs + approvals + audit + users + vault
4. Deixo Calendário + Eventos + Financeiro + Marketing + WhatsApp + RH + AI Chat como módulos de 1º nível
