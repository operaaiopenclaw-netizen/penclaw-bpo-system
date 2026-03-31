#!/usr/bin/env python3
"""
POP GENERATOR ENGINE
Gera Procedimentos Operacionais Padrão (POPs) para cada departamento
Baseado no sistema OpenClaw/Kitchen Intelligence

DEPARTAMENTOS:
- Comercial
- Produção
- Estoque
- Financeiro
- Gestão
"""

from pathlib import Path
from datetime import datetime

POP_DIR = Path(__file__).parent / "pop_docs"
POP_DIR.mkdir(exist_ok=True)


class POPGenerator:
    """Gerador de POPs"""
    
    def __init__(self):
        self.pops = {}
    
    def generate_all_pops(self):
        """Gera todos os POPs"""
        
        print("\n📋 GERANDO POPS - Procedimentos Operacionais Padrão")
        print("="*80)
        
        self.pop_comercial()
        self.pop_producao()
        self.pop_estoque()
        self.pop_financeiro()
        self.pop_gestao()
        
        print(f"\n✅ Todos os POPs gerados em: pop_docs/")
    
    def pop_comercial(self):
        """POP Comercial - Vendas e Orçamentos"""
        
        content = """# POP COMERCIAL - VENDAS E ORÇAMENTOS
## Procedimento Operacional Padrão

**Código:** POP-COM-001  
**Versão:** 1.0  
**Data:** {date}  
**Sistema:** OpenClaw Orkestra Finance Brain

---

## A. OBJETIVO

Padronizar processo de vendas, orçamentação e fechamento de eventos, garantindo:
- Preços baseados em margem alvo
- Rastreabilidade total (N CTT obrigatório)
- Consistência de dados para demais departamentos
- Previsibilidade de lucro antes do fechamento

---

## B. RESPONSÁVEL

**Cargo:** Consultor Comercial / Gerente Comercial  
**Aprovação:** Diretor Comercial (eventos > R$ 10.000)  
**Sistema:** OpenClaw Dashboard

---

## C. INPUTS (Dados Necessários)

### Antes da Proposta:
1. **Ficha Técnica de Interesse** (do cliente)
   - Tipo de evento
   - Número de convidados
   - Preferências de menu
   - Data do evento

2. **Dados Master** (do sistema):
   - `recipes.json` - base de receitas
   - `recipe_costs.json` - custos atualizados
   - `pricing_suggestions.json` - preços ideais

3. **Histórico** (se cliente recorrente):
   - Eventos anteriores
   - Margens realizadas
   - Satisfação

---

## D. PROCESSO PASSO A PASSO

### ETAPA 1: Cadastro do Evento (5 min)

**Ação:** Registrar no `events_consolidated.csv`

```csv
event_id,n_ctt,company,date_event,revenue_total,client_name,event_type,status
EVT123,CTT202600123,opera,2026-05-15,0.00,Cliente XYZ,Casamento,proposal
```

**Checklist:**
- [ ] Event_id único (formato: EVT + número sequencial)
- [ ] N CTT preenchido (obrigatório para rastreabilidade)
- [ ] Company definido (opera ou la_orana)
- [ ] Data no formato YYYY-MM-DD
- [ ] Status inicial: "proposal"

**Erro Comum:** Esquecer o N CTT → Correção: SEMPRE preencher antes de salvar

---

### ETAPA 2: Consulta de Precificação (10 min)

**Ação:** Executar `item_pricing_engine.py`

```bash
python3 item_pricing_engine.py
```

**Analisar:** `output/pricing_suggestions.csv`

**O que procurar:**
1. Custo das receitas solicitadas
2. Preço ideal para margem alvo:
   - Bar: 70%+
   - Cozinha: 60%+
   - Café: 65%+
3. Sugestões de ajuste

**Decisão:**
- Se preço sugerido ≤ orçamento cliente: APROVAR
- Se preço > orçamento: Negociar OU Substituir receita

---

### ETAPA 3: Análise de Margem (10 min)

**Ação:** Consultar `pricing_suggestions.json`

**Verificar:**
- Margem esperada do evento
- Itens de alto risco
- Armadilhas (vendem bem, margem ruim)

**Regra:** NUNCA fechar evento com margem < 20% sem aprovação do CEO

---

### ETAPA 4: Montagem da Proposta (20 min)

**Ação:** Criar proposta detalhada

**Estrutura:**
1. **Resumo do Evento**
   - Data, local, convidados
   - N CTT: [obrigatório]

2. **Cardápio**
   - Receitas com código (ex: REC001)
   - Preço por item
   - Margem esperada (do sistema)

3. **Orçamento**
   - Subtotal: R$ X
   - Taxa de serviço: X%
   - Total: R$ X
   - Margem estimada: X%

4. **Condições**
   - Sinal: 50%
   - Cancelamento: política

---

### ETAPA 5: Validação da Margem (5 min)

**Ação:** Simular no DRE

```bash
python3 dre_engine.py --simulate [event_id]
```

**Verificar:**
- Custo estimado × preço proposto
- Margem bruta projetada
- Custo fixo rateado
- Lucro líquido esperado

**Stop Loss:** Se lucro líquido < 5% da receita → REPROVAR

---

### ETAPA 6: Envio e Follow-up (contínuo)

**Status no CSV:**
- Proposta enviada: `status=proposal_sent`
- Negociação: `status=negotiating`
- Aprovada: `status=confirmed` + preencher `revenue_total`
- Rejeitada: `status=lost` + motivo

**Regra:** Atualizar status em até 24h após mudança

---

## E. OUTPUTS (O Que Deve Ser Gerado)

### 1. sales_dashboard.json
**Responsável:** Sistema (automático)  
**Vizualização:** CEO Dashboard

### 2. events_consolidated.csv (atualizado)
**Campos obrigatórios após fechamento:**
- `event_id` - preenchido
- `n_ctt` - preenchido
- `revenue_total` - preenchido (valor final)
- `status` = "confirmed"

### 3. Proposta PDF (fora do sistema)
**Armazenamento:** Pasta do evento (N CTT)

---

## F. ERROS COMUNS

| Erro | Impacto | Correção |
|------|---------|----------|
| Esquecer N CTT | Perda de rastreabilidade | Obrigatório antes de salvar |
| Preço sem consultar custo | Margem ruim | SEMPRE executar pricing_engine |
| Fechar sem checar margem | Prejuízo | Validação obrigatória |
| Status desatualizado Pipeline errado | Atualizar em 24h |

---

## G. CHECKLIST FINAL

Antes de marcar evento como "confirmed":

- [ ] N CTT preenchido e único
- [ ] Custo das receitas consultado
- [ ] Margem calculada (mínimo 20%)
- [ ] DRE simulado e aprovado
- [ ] Cliente aprovou por escrito
- [ ] Sinal de 50% recebido
- [ ] Status atualizado no CSV
- [ ] Pasta do evento criada (N CTT)

---

## FLUXO VISUAL

```
Levantamento → Cadastro → Pricing → Margem → 
Proposta → Simulação DRE → Aprovação → 
[CONFIRMADO] → Produção/Operações
```

**Próximo departamento:** Produção (recebe evento confirmado)

---

*POP gerado automaticamente pelo OpenClaw POP Generator Engine*  
*Data: {date}*
""".format(date=datetime.now().strftime("%Y-%m-%d"))
        
        filepath = POP_DIR / "pop_comercial.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ POP Comercial gerado: pop_docs/pop_comercial.md")
    
    def pop_producao(self):
        """POP Produção - Execução de Eventos"""
        
        content = """# POP PRODUÇÃO - EXECUÇÃO DE EVENTOS
## Procedimento Operacional Padrão

**Código:** POP-PROD-001  
**Versão:** 1.0  
**Data:** {date}  
**Sistema:** OpenClaw Orkestra Finance Brain

---

## A. OBJETIVO

Padronizar execução de eventos, garantindo:
- Produção conforme ficha técnica
- Rastreabilidade de consumo (por N CTT)
- Registro preciso de produção vs venda
- Dados para cálculo real de CMV

---

## B. RESPONSÁVEL

**Cargo:** Chef de Cozinha / Coordenador de Produção  
**Aprovação:** Gerente Operacional  
**Sistema:** Kitchen Engine + Production Execution

---

## C. INPUTS (Dados Necessários)

### 1. Pré-Evento (D-7):
- `production_plan.json` - plano aprovado
- Event ID + N CTT confirmado
- Número final de convidados

### 2. Dia do Evento (D-Day):
- `recipes.json` - fichas técnicas
- `inventory.json` - disponibilidade
- Equipe escalada

---

## D. PROCESSO PASSO A PASSO

### ETAPA 1: Verificação de Estoque (D-3)

**Ação:** Executar `fixed_cost_engine.py` (para consumo)

```bash
python3 kitchen_control_layer.py --check-stock [event_id]
```

**Output:** Verificação de disponibilidade

**Se FALTAR itens:**
1. Registrar em `errors.json`
2. Acionar Procurement para compra emergencial
3. Ajustar cardápio se necessário (com aprovação comercial)

**Checklist:**
- [ ] Todos os ingredientes disponíveis
- [ ] Qualidade verificada
- [ ] Quantidade suficiente + 10% margem

---

### ETAPA 2: Preparação (D-1)

**Ação:** Pré-preparo conforme fichas técnicas

**Registro obrigatório em `production_execution.json`:**

```json
{{
  "evento_id": "EVT123",
  "nome_evento": "Casamento Silva",
  "data_execucao": "2026-05-15",
  "responsavel_kitchen": "Chef Ana Maria",
  "equipe": ["João", "Pedro"],
  "receitas_executadas": [
    {{
      "receita_id": "REC001",
      "nome": "Escondidinho",
      "porcoes_planejadas": 120,
      "porcoes_produzidas": 130,
      "porcoes_servidas": 118,
      "porcoes_restantes": 12
    }}
  ]
}}
```

**Regras:**
- `porcoes_produzidas` = planejadas + margem de segurança (5-15%)
- `porcoes_servidas` = CONTAGEM REAL
- `porcoes_restantes` = produzidas - servidas

---

### ETAPA 3: Execução (D-Day)

**Ação:** Produzir e servir

**Durante o evento:**
1. **Registro contínuo** de saída de pratos
2. **Contagem** de sobremesas não servidas
3. **Foto/documentação** de estoque final (se > 15% sobra)

---

### ETAPA 4: Registro Pós-Evento (D+0, imediato)

**Ação:** Preencher `production_execution.json`

**Campos obrigatórios:**
- `porcoes_produzidas` (exato)
- `porcoes_servidas` (contagem real)
- `porcoes_restantes` (cálculo automático)

**Se ERRO na contagem:**
- Estimar baseado em peso/porção
- Registrar estimativa em `trace_mode`: "inferred"
- Justificar nas observações

---

### ETAPA 5: Baixa no Estoque (D+1)

**Ação:** Executar baixa automática

```bash
python3 kitchen_control_layer.py --baixa-estoque [execucao_id]
```

**Verificar:** `inventory.json` atualizado
- Quantidade antes
- Quantidade baixada
- Quantidade após

**Divergência > 5%:** Registrar em `errors.json` e investigar

---

### ETAPA 6: Registro de Desperdício (D+1)

**Ação:** Preencher `waste_log.json`

**Classificar sobras:**
- TIPO_A: Aproveitável (staff) → valoriza 30%
- TIPO_B: Doação → valoriza 10%
- TIPO_C: Descarte → perda total
- TIPO_D: Erro preparo → perda total
- TIPO_E: Estragado → perda total

**Foto obrigatória** se desperdício > 20% do produzido

---

## E. OUTPUTS (O Que Deve Ser Gerado)

### 1. production_execution.json
**Preenchido:** Immediatamente após evento

### 2. inventory.json (atualizado)
**Atualização:** Após baixa automática

### 3. waste_log.json
**Preenchido:** D+1, antes das 18h

### 4. cmv_log.json (gerado pelo sistema)
**Baseado em:** consumption × inventory avg price

---

## F. ERROS COMUNS

| Erro | Impacto | Correção |
|------|---------|----------|
| Contar porções servidas errado | CMV errado | Pesagem de sobra |
| Esquecer baixa no estoque | Invetário desatualizado | Checklist obrigatório |
| Não classificar desperdício | Perda de valorização | Preenchimento obrigatório |
| Porções produzidas ≠ servidas + restantes | Erro crítico | Recontar imediatamente |

---

## G. CHECKLIST FINAL

Antes de finalizar evento:

- [ ] Produção registrada (porcoes_produzidas)
- [ ] Serviço registrado (porcoes_servidas)
- [ ] Sobra calculada/contada
- [ ] Baixa no estoque executada
- [ ] Desperdício classificado
- [ ] Fotos de alta sobra (se > 20%)
- [ ] Equipe registrada
- [ ] Observações de incidentes

---

## FLUXO VISUAL

```
[Evento Confirmado]
    |
    v
Check Estoque → Pré-Preparo → Execução → Registro
    |                    |           |
    v                    v           v
Inventory         Production   CMV Real
(Baixa)           Execution    (Calculado)
```

**Próximo departamento:** Estoque (recebe baixa)

---

*POP gerado automaticamente pelo OpenClaw POP Generator Engine*  
*Data: {date}*
""".format(date=datetime.now().strftime("%Y-%m-%d"))
        
        filepath = POP_DIR / "pop_producao.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ POP Produção gerado: pop_docs/pop_producao.md")
    
    def pop_estoque(self):
        """POP Estoque - Gerenciamento de Inventário"""
        
        content = """# POP ESTOQUE - GERENCIAMENTO DE INVENTÁRIO
## Procedimento Operacional Padrão

**Código:** POP-EST-001  
**Versão:** 1.0  
**Data:** {date}  
**Sistema:** OpenClaw Orkestra Finance Brain

---

## A. OBJETIVO

Controlar estoque com precisão de custo, garantindo:
- Custo médio ponderado sempre atualizado
- Estoque vinculado a eventos (N CTT)
- Alertas de ruptura preventivos
- Rastreabilidade de lotes e fornecedores

---

## B. RESPONSÁVEL

**Cargo:** Almoxarife / Coordenador de Estoque  
**Aprovação:** Gerente Operacional (compras > R$ 5.000)  
**Sistema:** Procurement Feedback + Inventory

---

## C. INPUTS (Dados Necessários)

### Diários:
- Entradas de mercadoria (NF-e, recibos)
- Saídas por evento (baixas automáticas)
- Inventário físico (semanal)

### Eventos Agendados:
- `production_plan.json` (próximos 7 dias)
- `fixed_costs.csv` (necessidades calculadas)

---

## D. PROCESSO PASSO A PASSO

### ETAPA 1: Entrada de Mercadoria (Diário)

**Ação:** Receber e registrar

**Processo:**
1. Conferir físico vs nota fiscal
2. Verificar qualidade e validade
3. Registrar em `inventory.json`:

```json
{{
  "codigo": "CAR-001",
  "nome": "Carne Seca Desfiada",
  "quantidade_atual": 50.5,
  "unidade": "kg",
  "preco_unitario": 45.00,
  "fornecedor_atual": "Açougue Modelo",
  "historico_entradas": [
    {{
      "data": "2026-03-20",
      "quantidade": 25.0,
      "preco_unitario": 44.50,
      "fornecedor": "Açougue Modelo",
      "nota_fiscal": "NF12345"
    }}
  ]
}}
```

**Cálculo automático:**
- Custo médio ponderado = Soma(qtd × preço) / Soma(qtd)
- Atualização em `recipe_costs.json`

---

### ETAPA 2: Baixa Automática

**Ação:** Sistema executa (via produção)

**Processo:**
1. Production Execution gera baixa
2. Sistema atualiza `inventory.json`
3. Divergência > 5% → Alerta

**Verificação manual:**
- Conferir peso de sobras (se sobra > 15%)
- Validar classificação de desperdício

---

### ETAPA 3: Verificação de Ruptura (Segundas)

**Ação:** Executar `procurement_feedback_engine.py`

```bash
python3 procurement_feedback_engine.py
```

**Analisar:** Verificar alertas de:
- Estoque para < 7 dias
- Variação de preço > 15%
- Itens não encontrados

**Se ALERTA:**
1. Acionar compra urgente
2. Registrar em `procurement_suggestions.json`
3. Notificar chefes (se impacta eventos na semana)

---

### ETAPA 4: Inventário Físico (Sextas)

**Ação:** Contagem física

**Processo:**
1. Pesagem de todos os itens
2. Conferência com `inventory.json`
3. Ajuste de divergências:
   - Até 2%: ajuste direto
   - 2-5%: registro em `errors.json`
   - > 5%: investigação obrigatória

**Registro:**
```json
{{
  "data_inventario": "2026-03-28",
  "responsavel": "Carlos Almoxarife",
  "divergencias": [
    {{
      "item_id": "CAR-001",
      "sistema_kg": 50.5,
      "fisico_kg": 48.2,
      "diferenca_pct": -4.5,
      "acao": "investigacao"
    }}
  ]
}}
```

---

## E. OUTPUTS (O Que Deve Ser Gerado)

### 1. inventory.json (atualizado)
**Atualização:** Real-time (entradas/saídas)

### 2. procurement_suggestions.json
**Gerado:** Semanalmente ou em alerta

### 3. errors.json (se divergência)
**Registro:** Imediato

---

## F. ERROS COMUNS

| Erro | Impacto | Correção |
|------|---------|----------|
| Não registrar lote/fornecedor | Rastreabilidade perdida | Obrigatório no histórico |
| Preço de entrada errado | CMV incorreto | Conferência dupla |
| Inventário físico > 7 dias | Ruptura | Frequência obrigatória |
| Não atualizar custo médio | Margem errada | Automático via sistema |

---

## G. CHECKLIST FINAL

Diário:
- [ ] Entradas registradas com NF
- [ ] Baixas automáticas verificadas
- [ ] Alertas de ruptura tratados

Semanal:
- [ ] Inventário físico realizado
- [ ] Divergências investigadas
- [ ] Custo médio recalculado

---

## FLUXO VISUAL

```
Compra → Entrada → Inventory → Baixa (Auto) → Inventário Físico
                 ↑                     ↓
               Custo Médio       CMV Real (Evento)
```

**Próximo departamento:** Financeiro (recebe CMV)

---

*POP gerado automaticamente pelo OpenClaw POP Generator Engine*  
*Data: {date}*
""".format(date=datetime.now().strftime("%Y-%m-%d"))
        
        filepath = POP_DIR / "pop_estoque.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ POP Estoque gerado: pop_docs/pop_estoque.md")
    
    def pop_financeiro(self):
        """POP Financeiro - Contabilidade e Análise"""
        
        content = """# POP FINANCEIRO - CONTABILIDADE E ANÁLISE
## Procedimento Operacional Padrão

**Código:** POP-FIN-001  
**Versão:** 1.0  
**Data:** {date}  
**Sistema:** OpenClaw Orkestra Finance Brain

---

## A. OBJETIVO

Garantir rastreabilidade contábil completa:
- CMV real por evento (N CTT)
- Rateio correto de custos fixos
- DRE precisa e auditável
- Consistência total dos dados

---

## B. RESPONSÁVEL

**Cargo:** Analista Financeiro / Controller  
**Aprovação:** CFO / Diretor Financeiro  
**Sistema:** DRE Engine + Financial Truth Audit

---

## C. INPUTS (Dados Necessários)

### Semanais:
- `cmv_log.json` - por evento
- `fixed_costs.csv` - custos fixos mensais
- `financial_audit.json` - validações

### Mensais:
- Receitas confirmadas (conta bancária)
- Notas fiscais emitidas
- Comprovantes de pagamento

---

## D. PROCESSO PASSO A PASSO

### ETAPA 1: Consolidação Semanal (Segundas)

**Ação:** Executar engines financeiros

```bash
# 1. Verificar CMV
python3 kitchen_control_layer.py --update-costs

# 2. Calcular rateios
python3 fixed_cost_engine.py

# 3. Gerar DRE
python3 dre_engine.py

# 4. Validar consistência
python3 financial_truth_audit.py
```

**Verificar:** `output/dre_events.csv`

---

### ETAPA 2: Validação de Consistência (Terças)

**Ação:** Analisar `kitchen_data/financial_audit.json`

**Status esperado:**
- ✅ CONSISTENTE: prosseguir
- ⚠️ ALERTA: verificar divergências < 5%
- 🚨 INCONSISTENTE: investigar imediatamente

**Se INCONSISTENTE:**
1. Identificar eventos críticos
2. Cruzar com dados de origem:
   - Receita (banco) vs events_consolidated.csv
   - CMV (cmv_log.json) vs inventory
   - Produção vs Venda
3. Registrar discrepância em `audit_errors.json`
4. Notificar departamentos envolvidos

---

### ETAPA 3: Análise de Margem (Quartas)

**Ação:** Revisar margens

**Processo:**
1. Abrir `output/margin_validation.csv`
2. Identificar eventos:
   - CRITICAL: margem < 0%
   - REJECT: margem < 10%
   - REVIEW: margem 10-20%

**Ação por status:**
- CRITICAL: Reunião comercial urgente
- REJECT: Alerta e documentação
- REVIEW: Acompanhamento próximo

---

### ETAPA 4: Rateio de Custos Fixos (Mensal)

**Ação:** Calcular rateio

**Base:** `fixed_costs.csv`

**Fórmula:**
```
fixed_allocated_event = (event_revenue / total_month_revenue) × total_fixed_costs
```

**Verificação:**
- Soma dos rateios = total custos fixos (± 0.1%)
- Opera e La Orana separados

---

### ETAPA 5: Fechamento Mensal

**Ação:** Consolidar DRE completo

**Passos:**
1. Todas as notas fiscais lançadas
2. Todos os eventos com status "closed"
3. CMV validado para 100% dos eventos
4. Rateio de custos fixos aplicado
5. Lucro líquido por evento calculado

**Arquivo final:** `dre_[YYYY-MM].csv`

---

## E. OUTPUTS (O Que Deve Ser Gerado)

### 1. dre_events.csv
**Formato:** Semanal/Mensal  
**Conteúdo:** Receita, CMV, Margem, Lucro

### 2. financial_audit.json
**Validação:** Consistência de dados

### 3. audit_errors.json
**Registro:** Divergências encontradas

### 4. ceo_dashboard.json
**Visão:** Rastreabilidade para diretoria

---

## F. ERROS COMUNS

| Erro | Impacto | Correção |
|------|---------|----------|
| CMV sem event_id | Rastreabilidade perdida | Sempre vincular ao N CTT |
| Rateio errado | Lucro distorcido | Verificação automática |
| Receita ≠ banco | DRE incorreto | Conciliação obrigatória |
| Não validar semana | Erro acumulado | Validar financeira_cadência |

---

## G. CHECKLIST FINAL

Semanal:
- [ ] CMV calculado para todos eventos
- [ ] Rateio de custos fixos aplicado
- [ ] Consistência validada
- [ ] Divergências investigadas

Mensal:
- [ ] DRE fechado
- [ ] Receitas conciliadas com banco
- [ ] CMV auditável por evento
- [ ] Lucro líquido confirmado

---

## FLUXO VISUAL

```
Dados (Op) → CMV → Rateio → DRE → Validação → Fechamento
                ↑       ↑
           Inventory  Fixed Costs
```

**Próximo departamento:** Gestão (recebe dashboard)

---

*POP gerado automaticamente pelo OpenClaw POP Generator Engine*  
*Data: {date}*
""".format(date=datetime.now().strftime("%Y-%m-%d"))
        
        filepath = POP_DIR / "pop_financeiro.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ POP Financeiro gerado: pop_docs/pop_financeiro.md")
    
    def pop_gestao(self):
        """POP Gestão - Decisão Estratégica e Monitoramento"""
        
        content = """# POP GESTÃO - DECISÃO ESTRATÉGICA
## Procedimento Operacional Padrão

**Código:** POP-GES-001  
**Versão:** 1.0  
**Data:** {date}  
**Sistema:** OpenClaw Orkestra Finance Brain

---

## A. OBJETIVO

Tomada de decisão estratégica baseada em dados:
- Visão consolidada do negócio
- Priorização de problemas
- Alinhamento de ações
- Monitoramento de resultados

---

## B. RESPONSÁVEL

**Cargo:** CEO / Diretor Geral / Sócios  
**Apoio:** Controller, Head Comercial, Head de Operações  
**Sistema:** CEO Dashboard + Executive Report + Sales Dashboard

---

## C. INPUTS (Dados Necessários)

### Reunião Semanal (3ª feira, 9h):
- `ceo_dashboard.json` - KPIs estratégicos
- `executive_report.json` - storytelling
- `sales_dashboard.json` - performance comercial

### Reunião Mensal (1º dia útil, 10h):
- DRE fechado do mês anterior
- Rankings e análises competitivas
- Sugestões de calibração

---

## D. PROCESSO PASSO A PASSO

### ETAPA 1: Geração de Relatórios (Segunda, 8h)

**Ação:** Executar engines de relatório

```bash
# Dashboard executivo
python3 ceo_dashboard_engine.py

# Storytelling estratégico
python3 executive_report_engine.py

# Performance comercial
python3 sales_dashboard_engine.py
```

**Distribuição:** Enviar por e-mail aos participantes até 9h

---

### ETAPA 2: Reunião de Gestão (3ª feira, 9h)

**Pauta padrão (40 min):**

```
1. ABERTURA (5 min)
   - Visão rápida dos KPIs principais
   - Status geral: 🟢/🟡/🔴

2. STORYTELLING (10 min)
   - O QUE aconteceu na semana
   - POR QUE importa
   - Números com contexto

3. ALERTAS (10 min)
   - Eventos em risco
   - Itens críticos (armadilhas ⭐)
   - Divergências auditadas

4. DECISÕES (10 min)
   - Aprovações de ações sugeridas
   - Repriorização
   - Alocação de recursos

5. PRÓXIMA SEMANA (5 min)
   - Metas
   - Responsáveis
```

**Output:** Ata de decisões + Ações assignadas

---

### ETAPA 3: Ação e Acompanhamento (Diário)

**Ação:** Executar decisões

**Processos:**
1. `decision_engine.py` - gerar ações aprovadas
2. `auto_action_engine.py` - executar permitidas
3. `system_calibration_engine.py` - sugerir ajustes

**Monitoramento:**
- Daily standup (15 min) para críticos
- Status update em `decisions.json`

---

### ETAPA 4: Revisão Mensal (1º dia útil)

**Ação:** Análise estratégica

**Pauta (60 min):**
```
1. FECHAMENTO DO MÊS (15 min)
   - DRE consolidado
   - Margem real vs meta
   - Lucro por empresa

2. TENDÊNCIAS (15 min)
   - Comparação MoM
   - Top 5 itens (lucro, volume, margem)
   - Bottom 5 (problemas, prejuízo)

3. CALIBRAÇÃO (15 min)
   - Padrões de erro identificados
   - Sugestões de ajuste
   - Decisões: aprovar/melhorar/rejeitar

4. ESTRATÉGIA (15 min)
   - Objetivos próximo mês
   - Investimentos
   - Planos de contingência
```

---

## E. OUTPUTS (O Que Deve Ser Gerado)

### 1. Ata de Reuniões
**Conteúdo:** Decisões, responsáveis, prazos

### 2. Ações em `decisions.json`
**Status:** pending → approved → executed

### 3. Metas atualizadas
**Base:** Resultados reais + tendências

---

## F. ERROS COMUNS

| Erro | Impacto | Correção |
|------|---------|----------|
| Reunião sem dados preparados | Decisão intuitiva | Distrubuir antes |
| Decisão sem ação assignada | Inexecução | Sempre: quem/quando |
| Não revisar calibrações | Erro acumulado | Mensal obrigatório |
| Ignorar alertas críticos | Prejuízo | Responder em 24h |

---

## G. CHECKLIST FINAL

Semanal:
- [ ] Relatórios gerados e distribuídos
- [ ] Reunião realizada
- [ ] Decisões documentadas
- [ ] Ações assignadas

Mensal:
- [ ] DRE fechado conciliado
- [ ] Calibrações revisadas
- [ ] Metas ajustadas
- [ ] Estratégia definida

---

## FLUXO VISUAL

```
Dados → Relatórios → Reunião → Decisão → Ação → Resultado
  ↑_________________________________________________|
                    (Monitoramento)
```

**Ponto Central:** Gestão é onde tudo convergi para decisão

---

## INDICADORES DE SUCESSO

- Tempo entre problema → decisão: < 24h para críticos
- Eventos aprovados com margem > 30%: > 80%
- % de ações executadas: > 90%
- Tempo de reunião: < 60 min

---

*POP gerado automaticamente pelo OpenClaw POP Generator Engine*  
*Data: {date}*
""".format(date=datetime.now().strftime("%Y-%m-%d"))
        
        filepath = POP_DIR / "pop_gestao.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ POP Gestão gerado: pop_docs/pop_gestao.md")


def main():
    """Função principal"""
    
    print("🎛️ POP GENERATOR ENGINE - Orkestra Finance Brain")
    print("="*80)
    print("\n📋 Gerando Procedimentos Operacionais Padrão")
    print("   Baseado nos 16 engines do sistema")
    
    generator = POPGenerator()
    generator.generate_all_pops()
    
    print("\n✅ POP Generator Engine completado!")
    print(f"   5 POPs gerados em pop_docs/")
    print("\n   Arquivos:")
    print("      - pop_comercial.md")
    print("      - pop_producao.md")
    print("      - pop_estoque.md")
    print("      - pop_financeiro.md")
    print("      - pop_gestao.md")


if __name__ == "__main__":
    main()
