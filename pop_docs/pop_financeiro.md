# POP FINANCEIRO - CONTABILIDADE E ANÁLISE
## Procedimento Operacional Padrão

**Código:** POP-FIN-001  
**Versão:** 1.0  
**Data:** 2026-03-31  
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
*Data: 2026-03-31*
