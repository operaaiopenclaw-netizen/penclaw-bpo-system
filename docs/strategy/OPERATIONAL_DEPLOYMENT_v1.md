# OPERATIONAL DEPLOYMENT — Orkestra Finance Brain

**Versão:** 1.0  
**Data:** 2026-04-08  
**Arquitetura:** 3 Camadas (Operação → Execução → Gestão)  
**Status:** Plano de Implantação Completo

---

## 🏗️ ARQUITETURA DE 3 CAMADAS

```
┌─────────────────────────────────────────────────────────────────┐
│                         OPERAÇÃO                                │
│                    (Telegram + Mobile)                          │
├─────────────────────────────────────────────────────────────────┤
│  📱 TELEGRAM ENGINE          │  📦 STOCK MOBILE ENGINE        │
│  ├─ bot_comercial            │  ├─ Barcode / QR Code          │
│  ├─ bot_operacoes            │  ├─ Entrada/Saída/Retorno      │
│  ├─ bot_estoque              │  ├─ Kits Logísticos            │
│  ├─ bot_financeiro           │  └─ Impressão Bluetooth        │
│  └─ bot_diretoria            │                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Webhooks / APIs
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                         EXECUÇÃO                                │
│                        (OpenClaw)                               │
├─────────────────────────────────────────────────────────────────┤
│  🤖 Orkestra Finance Brain                                     │
│  ├─ Event Engine                                               │
│  ├─ Inventory Engine                                           │
│  ├─ Financial Core                                            │
│  ├─ Sales Engine                                              │
│  ├─ SDR AI Engine                                             │
│  └─ Decision Engine                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Dados / Consultas
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                         GESTÃO                                  │
│                     (Dashboard Mínimo)                          │
├─────────────────────────────────────────────────────────────────┤
│  📊 KPIs em Tempo Real         │  🚨 Alertas Automáticos        │
│  ├─ Receita Proj vs Real       │  ├─ Estoque Crítico            │
│  ├─ Eventos da Semana          │  ├─ Evento com Risco           │
│  ├─ Pipeline Comercial         │  ├─ Lead Parado                │
│  └─ Status Geral               │  └─ Caixa Crítico              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📱 1. TELEGRAM ENGINE — Sistema de Bots

### 1.1 Estrutura de Bots

```
OrkestraBots (Grupo no Telegram)
├── 🤖 @OrkestraComercialBot  (Vendas + Leads)
├── 🤖 @OrkestraOperacoesBot  (Eventos + Checklist)
├── 🤖 @OrkestraEstoqueBot    (Inventário + Movimentação)
├── 🤖 @OrkestraFinanceiroBot (Fluxo de Caixa + Contas)
└── 🤖 @OrkestraDiretoriaBot   (KPIs + Aprovações + Alertas)
```

### 1.2 Comandos Estruturados

#### **BOT COMERCIAL** (@OrkestraComercialBot)

```markdown
# Comandos Principais:

/lead [nome] [tipo] [pessoas] [orçamento]
→ "lead João casamento 150 25000"
  ✓ Lead registrado: ORG-2025-0001
  ✓ Score: 75 (ALTA PRIORIDADE)
  ✓ Ação: Agendar reunião

/oportunidade [id] [ação]
→ "opp 42 aprovar"
→ "opp 42 perdeu preço"
→ "opp 42 negociar"

/contato [busca]
→ "contato ACME"
→ "contato João 1199999"

/prospeccao
→ Lista leads com follow-up hoje

/funil
→ Status do pipeline comercial
```

#### **BOT OPERAÇÕES** (@OrkestraOperacoesBot)

```markdown
# Comandos Principais:

evento [ação] [parâmetros]
→ "evento novo Casamento Silva"
→ "evento 475 status montagem"
→ "evento 475 problema atraso fornecedor"
→ "evento 475 checklist"
→ "evento 475 confirmado"
→ "evento 475 finalizado"

/fornecedor [evento] [ação]
→ "fornecedor 482 confirmar buffê"
→ "fornecedor 482 status dj"

/problema [evento] [descrição]
→ "problema 521 quebra 12 cadeiras"
→ "problema 521 avaria tapete"

/manha [data]
→ Lista eventos do dia com status

/semana [semana]
→ Overview da semana
```

#### **BOT ESTOQUE** (@OrkestraEstoqueBot)

```markdown
# Comandos Principais:

/entrada [item] [qtd] [fornecedor] [custo]
→ "entrada agua 100 fornecedor-x 5.50"
  ✓ 100x Água entrada registrada
  ✓ Fornecedor: Fornecedor-X
  ✓ Valor: R$ 550,00
  ✓ Lote: FT-2025-004

/saida [item] [qtd] [destino]
→ "saida cadeira 24 evento-478"
→ "saida agua 12 consumo-interno"

/retorno [evento] [item] [qtd] [estado]
→ "retorno 478 cadeira 22 ok"
→ "retorno 478 copo 5 quebrado"

/inventario [filtro]
→ "inventario tudo"
→ "inventario baixo"
→ "inventario evento-478"

/etiqueta [item] [tipo]
→ "etiqueta cadeira kit"
→ "etiqueta enxoval evento"

/avaria [item] [qtd] [motivo]
→ "avaria prato 3 quebrado"
```

#### **BOT FINANCEIRO** (@OrkestraFinanceiroBot)

```markdown
# Comandos Principais:

/caixa [período]
→ "caixa hoje"
→ "caixa semana"
→ "caixa mes"

/projeção [dias]
→ "projecao 7"
→ Mostra: Saldo atual + Entradas previstas - Saídas previstas

/pagar [filtro]
→ "pagar hoje"
→ "pagar vencidas"
→ "pagar fornecedor-x"

/receber [filtro]
→ "receber hoje"
→ "receber atrasadas"

/conta [ação] [valor] [descrição]
→ "conta pagar 2500 fornecedor-x NF-123"
→ "conta receber 15000 cliente-y parcela-2"

/transferir [origem] [destino] [valor]
→ "transferir caixa banco 5000"
```

#### **BOT DIRETORIA** (@OrkestraDiretoriaBot)

```markdown
# Comandos Principais:

/dashboard [empresa]
→ "dashboard laohana"
→ "dashboard tudo"

/aprovar [tipo] [id]
→ "aprovar desconto 45"
→ "aprovar pagamento 123"

/alertas
→ Lista alertas críticos pendentes

/meta [empresa] [período]
→ "meta qopera mes"
→ Mostra: Realizado vs Meta

/evento [id] [detalhe]
→ "evento 478 financeiro"
→ "evento 478 operacional"
→ "evento 478 comercial"
```

### 1.3 Linguagem Natural (Interpretação)

**Exemplos de mensagens livres:**

```
👤 Usuário: "Preciso de 50 cadeiras para o evento da ACME amanhã"
🤖 Bot: 
"Entendido! Registrando saída:
📦 Item: Cadeira
📊 Quantidade: 50
🎯 Destino: Evento ACME (ID: 482)
📅 Data: Amanhã (2025-04-09)

Confirmar com sim?"

👤 Usuário: "Sim"
🤖 Bot:
"✅ Saída registrada: MVT-2025-0892
📦 50x Cadeiras → Evento 482
📍 Status: Reservado
⏰ Retorno previsto: 2025-04-10"
```

```
👤 Usuário: "Chegou a cerveja do fornecedor, 200 unidades"
🤖 Bot:
"Entrada detectada:
🍺 Produto: Cerveja
📊 Quantidade: 200
🏢 Fornecedor: [último: Fornecedor-Y]
💰 Valor unitário: [estimado: R$ 4,50]

Confirmar ou corrigir?"

👤 Usuário: "Fornecedor é Z, valor 3,80"
🤖 Bot:
"✅ Entrada registrada: ENT-2025-0341
🍺 200x Cerveja (Fornecedor-Z)
💰 Total: R$ 760,00
📍 Estoque atual: 2.450 unidades"
```

---

## 📦 2. STOCK MOBILE ENGINE — Estoque via Smartphone

### 2.1 Arquitetura Mobile

```
┌─────────────────────────────────────────────────────┐
│                 SMARTPHONE                          │
├─────────────────────────────────────────────────────┤
│  📷 CÂMERA                   │  🖨️ IMPRESSORA      │
│  ├─ Barcode scanning         │  ├─ Bluetooth        │
│  ├─ QR code reading          │  ├─ Etiqueta 40x40   │
│  └─ Manual entry             │  ├─ Código item      │
│                              │  └─ QR Evento        │
├──────────────────────────────┼──────────────────────┤
│  📱 APLICATIVO               │  ☁️ SYNC             │
│  ├─ Offline mode             │  ├─ 4G/WiFi          │
│  ├─ Queue                    │  ├─ Background       │
│  └─ Simple UI                │  └─ Conflict         │
└──────────────────────────────┴──────────────────────┘
```

### 2.2 Tipos de QR Code

#### **QR de Item (Estoque Geral)**
```
ORKESTRA-ITEM::{
  "item_id": "uuid",
  "sku": "CAD-PAD-BRA",
  "name": "Cadeira Padrão Branca",
  "type": "patrimonio",
  "unit": "unidade"
}
```

#### **QR de Kit (Conjunto)**
```
ORKESTRA-KIT::{
  "kit_id": "uuid",
  "name": "Kit Casamento 100p",
  "items": [
    {"item_id": "uuid", "qty": 100, "name": "Cadeira"},
    {"item_id": "uuid", "qty": 50, "name": "Mesa 8L"},
    {"item_id": "uuid", "qty": 100, "name": "Prato"}
  ],
  "total_items": 250
}
```

#### **QR de Evento (Separador)**
```
ORKESTRA-EVT::{
  "event_id": "uuid",
  "ctt": "CTT-2025-0456",
  "client": "Nome Cliente",
  "date": "2025-04-15",
  "status": "montagem"
}
```

#### **QR de Caixa Logística**
```
ORKESTRA-BOX::{
  "box_id": "uuid",
  "event_id": "uuid",
  "type": "montagem",
  "contents_hash": "sha256",
  "weight_kg": 45
}
```

### 2.3 Fluxos Mobile

#### **FLUXO: ENTRADA**
```
[ABRIR APP] → [ESCANEAR QR ou digitar SKU]
         ↓
[SISTEMA BUSCA ITEM]
         ↓
[CONFIRMA ITEM] → [SE não estiver cadastrado → CADASTRO RÁPIDO]
         ↓
[INPUT QUANTIDADE] → [+/-] ou teclado
         ↓
[INPUT FORNECEDOR] → Busca ou novo
         ↓
[INPUT CUSTO UN] → (sugere último)
         ↓
[INPUT LOTE] → (opcional, gera automático)
         ↓
[INPUT VALIDADE] → (se aplicável)
         ↓
[CONFIRMAÇÃO] → [TIRAR FOTO] (opcional)
         ↓
[SYNC QUANDO ONLINE]
         ↓
[ETIQUETAR?] → [SIM → IMPRIME QR]
```

#### **FLUXO: SAÍDA (Evento)**
```
[ABRIR APP] → [ESCANEAR QR DO EVENTO]
         ↓
[CONFIRMA EVENTO: Casamento Silva - 15/04]
         ↓
[ESCANEAR ITENS]
    ├── Item 1: Cadeira → Qtd: 100
    ├── Item 2: Mesa → Qtd: 25
    └── Item 3: ...
         ↓
[VERIFICAR LISTA MONTAGEM]
    ✅ Cadeiras: 100/100
    ⚠️  Mesas: 23/25 (FALTAM 2)
    ✅ Copos: 200/200
         ↓
[CONFIRMAR DÍVIDAS]
         ↓
[ASSINAR DIGITAL]
         ↓
[SYNC]
         ↓
[IMPRIMIR RESUMO] (opcional)
```

#### **FLUXO: RETORNO**
```
[ABRIR APP] → [ESCANEAR QR DO EVENTO]
         ↓
[MODO: RETORNO]
         ↓
[ESCANEAR ITENS QUE VOLTARAM]
    ├── Cadeira 100 → [98 OK] [2 AVARIADAS]
    ├── Mesa 25 → [25 OK]
    └── ...
         ↓
[REGISTRAR AVARIAS]
    Cadeira #1: Quebrada → Foto → Motivo
    Cadeira #2: Riscada → Foto → Motivo
         ↓
[VERIFICAR CONTRA SAÍDA]
         ↓
[CONFIRMA]
         ↓
[SYNC]
```

### 2.4 Estrutura QR para Impressão

**Layout Etiqueta 40mm x 40mm:**

```
┌─────────────────────┐
│ ▓▓▓▓▓ QR CODE ▓▓▓▓▓ │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
├─────────────────────┤
│ SKU: CAD-PAD-BRA    │
│ Cadeira Padrão      │
│ Branca              │
└─────────────────────┘
```

**Layout Etiqueta 80mm x 30mm (para caixas):**

```
┌────────────────────────────────────────┐
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   │
│ ▓▓▓▓▓▓ QR EVENTO ▓▓▓▓▓▓▓▓▓▓▓▓     │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   │
├────────────────────────────────────────┤
│ CTT-2025-0456                          │
│ Casamento Silva                        │
│ 15/04/2025                             │
│ QOpera                                 │
└────────────────────────────────────────┘
```

---

## 📊 3. DASHBOARD MÍNIMO

### 3.1 Layout Dashboard (HTML Simples)

```
┌─────────────────────────────────────────────┐
│ 🎛️ ORKESTRA DASHBOARD      [QOpera ▼] 🔔 ⚙️ │
├─────────────────┬───────────────────────────┤
│                 │                           │
│ 📈 RECEITA      │ 📅 EVENTOS SEMANA         │
│ ─────────────── │                           │
│                 │ • 15/04 Casamento Silva   │
│ Projetada:      │ • 16/04 Evento ACME       │
│ R$ 450K         │ • 18/04 Formatura ABC     │
│                 │                           │
║ Realizada:      │ 🎯 PIPELINE               │
║ R$ 380K         │ ─────────────             │
║                 │                           │
║ Diferença:      │ Hot (5)  ████████░░  8    │
║ [   84%   ]     │ Med (12) ████████████ 12  │
║                 │ Frz (3)  ███░░░░░░░  3    │
│                 │                           │
├─────────────────┼───────────────────────────┤
│                 │                           │
│ ⚠️ ALERTAS      │ 📦 ESTOQUE                │
│ ─────────────── │ ─────────                 │
│                 │                           │
│ 🔴 Evento 478   │ 🔴 Água                   │
│    Atraso       │    150 un (min: 200)      │
│                 │                           │
│ 🟡 Lead 45      │ 🟡 Cerveja                │
│    3 dias       │    500 un (min: 600)      │
│                 │                           │
│ 🟠 Caixa        │                           │
│    Projeção -   │                           │
│                │                           │
└─────────────────┴───────────────────────────┘
```

### 3.2 Wireframes Dashboard

```html
<!-- Dashboard Minimal -->
<div class="dashboard">
  
  <!-- Header -->
  <header class="header">
    <h1>🎛️ Orkestra</h1>
    <select id="company-selector">
      <option value="all">Todas Empresas</option>
      <option value="qopera">QOpera</option>
      <option value="laohana">Laohana</option>
      <option value="robusta">Robusta</option>
    </select>
  </header>

  <!-- Grid -->
  <div class="dashboard-grid">
    
    <!-- Card Receita -->
    <div class="card card-revenue">
      <h3>📈 Receita</h3>
      <div class="metric">
        <label>Projetada (mês)</label>
        <value>R$ 450.000</value>
      </div>
      <div class="metric">
        <label>Realizada</label>
        <value class="highlight">R$ 380.000</value>
      </div>
      <div class="progress-bar">
        <div class="fill" style="width: 84%">84%</div>
      </div>
    </div>

    <!-- Card Eventos -->
    <div class="card card-events">
      <h3>📅 Eventos Semana</h3>
      <ul class="event-list">
        <li class="event">
          <date>15/04</date>
          <name>Casamento Silva</name>
          <status class="confirmed">✓</status>
        </li>
        <li class="event">
          <date>16/04</date>
          <name>Evento ACME</name>
          <status class="warning">!</status>
        </li>
      </ul>
    </div>

    <!-- Card Pipeline -->
    <div class="card card-pipeline">
      <h3>🎯 Pipeline</h3>
      <div class="pipeline-bars">
        <div class="bar-group">
          <label>Hot</label>
          <div class="bar"><div class="fill hot" style="width: 80%">8</div></div>
        </div>
        <div class="bar-group">
          <label>Médio</label>
          <div class="bar"><div class="fill medium" style="width: 100%">12</div></div>
        </div>
        <div class="bar-group">
          <label>Frio</label>
          <div class="bar"><div class="fill cold" style="width: 30%">3</div></div>
        </div>
      </div>
    </div>

    <!-- Card Alertas -->
    <div class="card card-alerts">
      <h3>⚠️ Alertas (5)</h3>
      <ul class="alert-list">
        <li class="alert alert-critical">
          <icon>🔴</icon>
          <text>Evento 478 atraso montagem</text>
        </li>
        <li class="alert alert-warning">
          <icon>🟡</icon>
          <text>Lead 45 sem contato 3 dias</text>
        </li>
      </ul>
    </div>

    <!-- Card Estoque -->
    <div class="card card-inventory">
      <h3>📦 Estoque Crítico</h3>
      <ul class="inventory-list">
        <li class="item low">
          <name>Água mineral</name>
          <stock>150 <small>/ mín 200</small></stock>
        </li>
        <li class="item warning">
          <name>Cerveja</name>
          <stock>500 <small>/ mín 600</small></stock>
        </li>
      </ul>
    </div>

    <!-- Card Caixa -->
    <div class="card card-cash">
      <h3>💰 Caixa Hoje</h3>
      <div class="cash-flow">
        <div class="in">↑ R$ 25.000</div>
        <div class="out">↓ R$ 18.500</div>
        <div class="balance positive">= R$ 6.500</div>
      </div>
    </div>

  </div>
</div>
```

---

## 🔔 4. SISTEMA DE ALERTAS

### 4.1 Tipos de Alerta

```python
ALERT_CATEGORIES = {
    # Operacionais
    'event_delay': {
        'severity': 'critical',
        'check': 'event_date - now < 7 days AND status != confirmed',
        'action': 'notify_operations',
        'sla': '4 hours'
    },
    'stock_critical': {
        'severity': 'critical', 
        'check': 'stock < min_stock',
        'action': 'notify_stock + purchase',
        'sla': '24 hours'
    },
    
    # Comerciais
    'lead_stale': {
        'severity': 'warning',
        'check': 'last_contact > 3 days',
        'action': 'auto_reengage',
        'sla': '48 hours'
    },
    'follow_up_missed': {
        'severity': 'warning',
        'check': 'follow_up_date < today AND no_contact',
        'action': 'escalate_to_ae',
        'sla': '24 hours'
    },
    
    # Financeiros
    'cash_projection_negative': {
        'severity': 'critical',
        'check': 'projected_cash < 0',
        'action': 'notify_cfo',
        'sla': 'immediate'
    },
    'invoice_overdue': {
        'severity': 'warning',
        'check': 'due_date < today AND status = pending',
        'action': 'send_reminder + alert',
        'sla': 'daily'
    },
    
    # Margens
    'margin_below_threshold': {
        'severity': 'warning',
        'check': 'calculated_margin < 25%',
        'action': 'require_approval',
        'sla': 'before_close'
    }
}
```

### 4.2 Entrega de Alertas

```
┌─────────────────────────────────────────┐
│           ALERT ENGINE                  │
├─────────────────────────────────────────┤
│                                         │
│  📱 Telegram DM          → Pessoal      │
│  ├─ Alertas críticos                   │
│  ├─ Aprovações pendentes               │
│  └─ Eventos do dia                     │
│                                         │
│  👥 Grupo de Op.       → Equipe        │
│  ├─ Mudanças de status                 │
│  ├─ Problemas operacionais             │
│  └─ Checklist concluídos               │
│                                         │
│  📧 Email              → Formal         │
│  ├─ Relatórios diários                 │
│  └─ Alertas financeiros                │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🚀 PLANO DE ROLLOUT

### FASE 1: Base (Semana 1)
- [ ] Configurar bots Telegram
- [ ] Criar grupos por empresa/perfil
- [ ] Deploy API endpoints
- [ ] Testar comandos básicos

### FASE 2: Estoque (Semana 2)
- [ ] Imprimir primeiros QRs
- [ ] Testar app mobile
- [ ] Treinar equipe de campo
- [ ] Sync offline

### FASE 3: Comercial (Semana 3)
- [ ] Importar leads existentes
- [ ] Configurar qualificação
- [ ] Testar integração calendar
- [ ] Treinar SDRs

### FASE 4: Completo (Semana 4)
- [ ] Todas empresas operando
- [ ] Dashboard ativo
- [ ] Alertas configurados
- [ ] Relatórios automáticos

---

🎛️ **Operational Deployment v1.0 — Sistema em Operação Real**
