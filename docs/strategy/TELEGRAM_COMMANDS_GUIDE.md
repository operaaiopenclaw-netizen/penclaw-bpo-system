# GUIA DE COMANDOS TELEGRAM — Orkestra Finance Brain

**Versão:** 1.0 — Quick Reference  
**Data:** 2026-04-08

---

## 🤖 @OrkestraComercialBot

### Leads & Oportunidades

```
/lead [nome] [tipo] [pessoas] [orçamento]
  → Registra novo lead
  → Ex: "lead João casamento 150 25000"
  
/opp [id] [ação]
  → Gerencia oportunidade
  → Ações: ver, editar, aprovar, perdeu, ganho
  → Ex: "opp 42 aprovar", "opp 45 ganho"

/prospectar
  → Lista leads com follow-up hoje

/funil
  → Pipeline atual com filtros
  → Ex: "funil hot", "funil mes"

/contato [busca]
  → Busca cliente por nome/email
  → Ex: "contato ACME", "contato joao@email.com"

/historico [cliente]
  → Histórico de eventos do cliente
```

---

## 🔧 @OrkestraOperacoesBot

### Eventos & Checklist

```
evento [comando] [parâmetros]

  novo [nome]
    → "evento novo Casamento Silva"
    
  [id] status [estado]
    → "evento 475 status montagem"
    → Estados: contrato, briefing, producao, montagem, execucao, finalizado
    
  [id] checklist
    → Mostra checklist do evento
    → Marca: "evento 475 checklist ok 5"
    
  [id] problema [descricao]
    → "evento 475 problema atraso fornecedor"
    
  [id] nota [texto]
    → Adiciona nota ao evento

/fornecedor [evento] [ação]
  → "fornecedor 482 confirmar buffê"
  → "fornecedor 482 status dj"

/entrega [evento]
  → Status de entregas pendentes

/reuniao [evento] [data]
  → Agenda briefing com cliente

/manha [data]
  → Eventos do dia (hoje se não informar)

/semana [data]
  → Overview da semana

/problemas [filtro]
  → Lista problemas abertos
  → Filtros: hoje, evento-123, criticos
```

---

## 📦 @OrkestraEstoqueBot

### Movimentação de Estoque

```
/entrada [item] [qtd] [fornecedor] [valor]
  → Registra entrada de material
  → Ex: "entrada agua 100 fornecedor-x 5.50"
  → Ex: "entrada cerveja 50 cervejaria-y 4.20"
  → Responde com: ID da movimentação, estoque atual, custo médio

/saida [item] [qtd] [destino]
  → Registra saída para evento ou consumo
  → Ex: "saida cadeira 24 evento-478"
  → Ex: "saida agua 10 consumo-interno"
  → Ex: "saida enxoval kit casamento-125"

/retorno [evento] [item] [qtd] [estado]
  → Registra retorno de evento
  → Estados: ok, avariado, perdido, incompleto
  → Ex: "retorno 478 cadeira 24 ok"
  → Ex: "retorno 478 copo 5 avariado"

/transferir [origem] [destino] [item] [qtd]
  → Move entre depósitos
  → Ex: "transferir dep1 dep2 cadeira 50"

/inventario [comando]
  
  listar [filtro]
    → "inventario listar tudo"
    → "inventario listar baixo"
    → "inventario listar evento-478"
    
  contar [item]
    → Faz contagem física
    → "inventario contar cadeira"
    
  ajustar [item] [qtd] [motivo]
    → Ajuste por perda/avaria
    → "inventario ajustar prato 5 quebrado"

/etiqueta [item] [tipo]
  → Gera QR code para impressão
  → Tipos: item, kit, caixa, evento
  → Ex: "etiqueta cadeira item"
  → Ex: "etiqueta kit casamento-100p kit"

/localizar [item]
  → Onde está o item
  → Ex: "localizar cadeira branca"

/custo [item] [periodo]
  → Histórico de custos
  → Ex: "custo cerveja 6meses"

/consumo [evento]
  → Relatório de consumo vs previsto
  → "consumo 478"
```

**Respostas do Bot Estoque:**
```
✅ ENTRADA REGISTRADA

ID: ENT-2025-0042
Item: Água mineral 500ml
Quantidade: 100 unidades
Fornecedor: Fornecedor-X
Valor unitário: R$ 5,50
Total: R$ 550,00
Lote: L-2025-04-042

📊 Estoque atual: 2.450 unidades
💰 Custo médio: R$ 5,42/un
📍 Local: Depósito Principal
```

---

## 💰 @OrkestraFinanceiroBot

### Consultas & Registros

```
/caixa [periodo]
  → "caixa hoje"
  → "caixa semana"
  → "caixa mes"
  → Mostra: Saldo inicial + Entradas - Saídas = Saldo final

/projeção [dias]
  → Projeção de fluxo
  → "projecao 7" (próximos 7 dias)
  → "projecao 30"
  → Mostra: Saldo projetado por dia

/pagar [filtro]
  → Contas a pagar
  → "pagar hoje"
  → "pagar vencidas"
  → "pagar semana"
  → "pagar fornecedor-x"

/receber [filtro]
  → Contas a receber
  → "receber hoje"
  → "receber atrasadas"
  → "receber evento-478"

/conta [ação] [parâmetros]
  
  pagar [valor] [fornecedor] [descricao] [vencimento]
    → "conta pagar 2500 fornecedor-x NF-123 15/04"
    
  receber [valor] [cliente] [descricao] [vencimento]
    → "conta receber 15000 cliente-y parcela-2 20/04"
    
  quitar [id] [valor] [data]
    → "conta quitar 123 15000 10/04"

/transferir [origem] [destino] [valor] [data]
  → "transferir caixa banco 5000 hoje"

/extrato [conta] [periodo]
  → Movimentações da conta
  → "extrato caixa semana"

/custo [evento]
  → Custo real vs previsto
  → "custo 478"

/margem [evento]
  → Margem calculada
  → "margem 478" (mostra: previsto vs real)

/comissao [vendedor] [periodo]
  → Calcula comissões
  → "comissao ana mes"
```

**Respostas do Bot Financeiro:**
```
💰 CAIXA — HOJE (08/04/2025)

Saldo inicial:    R$ 45.230,00
Entradas:        +R$ 12.500,00
                ─────────────
Subtotal:         R$ 57.730,00
Saídas:          -R$  8.250,00
                ─────────────
💵 Saldo final:   R$ 49.480,00

📊 Compromissos hoje:
• Contas a pagar: R$ 5.000 (2 vencimentos)
• Contas a receber: R$ 15.000 (3 recebimentos)
```

---

## 📊 @OrkestraDiretoriaBot

### Gestão & Indicadores

```
/dashboard [empresa] [periodo]
  → Visão geral
  → "dashboard" (todas empresas, hoje)
  → "dashboard laohana"
  → "dashboard qopera mes"

/metricas [tipo] [periodo]
  → KPIs detalhados
  → "metricas financeiro mes"
  → "metricas comercial semana"
  → "metricas operacional dia"

/comparativo [empresas] [metrica]
  → Compara entre empresas
  → "comparativo qopera,laohana receita"

/aprovar [tipo] [id]
  → Aprovações pendentes
  → "aprovar desconto 45"
  → "aprovar pagamento 123"
  → "aprovar alteracao 478"

/alertas [filtro]
  → Lista alertas ativos
  → "alertas criticos"
  → "alertas hoje"
  → "alertas geral"

/meta [empresa] [periodo]
  → Realizado vs Meta
  → "meta laohana mes"
  → Mostra: progresso %, gap, projeção

/reuniao [tipo] [participantes]
  → Agenda reunião
  → "reuniao comercial ana,joao amanha 15h"

/relatorio [tipo] [periodo]
  → Gera relatório
  → "relatorio fechamento mes"
  → "relatorio pipeline semana"

/evento [id] [visao]
  → Visão completa do evento
  → "evento 478 tudo" (comercial + operacional + financeiro)
  → "evento 478 financeiro"
  → "evento 478 operacional"

/vendedor [nome] [periodo]
  → Performance individual
  → "vendedor ana mes"
```

**Respostas do Bot Diretoria:**
```
📊 DASHBOARD — LAOHANA
Período: Abril/2025 (08/04)

💰 FINANCEIRO
─────────────────
Meta faturamento:    R$ 500.000
Realizado:           R$ 380.000 (76%)
Projetado:           R$ 520.000 ✅

🎯 COMERCIAL
─────────────────
Meta eventos:        12
Fechados:            9 (75%)
Pipeline:            R$ 450.000

⚠️ ALERTAS CRÍTICOS: 2
• Evento 478 — atraso montagem
• Estoque — Água abaixo do mínimo
```

---

## 🎤 LINGUAGEM NATURAL (Mensagens Livres)

Todos os bots entendem linguagem natural:

### Exemplos funcionais:

```
👤 "Preciso registrar entrada de 100 águas do fornecedor X"
� → /entrada agua 100 fornecedor-x [valor último]

👤 "Evento 478 precisa de mais 20 cadeiras"
� → /saida cadeira 20 evento-478

👤 "Quanto temos em caixa?"
� → /caixa hoje

👤 "Lead novo: João, casamento, 150 pessoas, orçamento 25k"
� → /lead João casamento 150 25000

👤 "Evento da semana que vem da ACME está confirmado?"
� → Busca evento ACME + data + status

👤 "Problema: o DJ do evento 482 cancelou"
� → /evento 482 problema DJ cancelou

👤 "Como estamos em relação à meta do mês?"
� → /meta [empresa] mes
```

---

## 📱 MENUS INTERATIVOS (Telegram ReplyKeyboard)

```
┌─────────────────────────────────────────┐
│ 🎛️ MENU PRINCIPAL                      │
├─────────────────────────────────────────┤
│ [📦 Estoque] [🎯 Comercial]            │
│ [💰 Financeiro] [📊 Dashboard]           │
│ [⚙️ Configurações] [❓ Ajuda]           │
└─────────────────────────────────────────┘

Clicar em botão → executa comando equivalente
```

---

## 🚨 COMANDOS DE EMERGÊNCIA

```
/sos [descricao]
  → Alerta máxima prioridade
  → Notifica diretoria imediatamente
  → Ex: "sos evento 500 fornecedor principal faltou"

/urgente [comando]
  → Prioriza processamento
  → Salta fila de mensagens

/ajuda [topico]
  → Manual rápido
  → "ajuda estoque"
  → "ajuda comandos"

/status
  → Status do sistema
  → Mostra: bots online, API, último sync
```

---

## 📝 SHORTCUTS (Atalhos)

| Atalho | Comando Completo | Quando Usar |
|--------|-----------------|-------------|
| `e + número` | `evento [número]` | Rápido evento |
| `l + nome` | `lead [nome]` | Novo lead |
| `ent + item` | `entrada [item]` | Entrada estoque |
| `sai + item` | `saida [item]` | Saída estoque |
| `opp + id` | `opp [id]` | Oportunidade |
| `$` | `caixa hoje` | Ver caixa |
| `!!` | `/sos` | Emergência |

---

🎛️ **Quick Reference v1.0 — Operação Diária Orkestra**
