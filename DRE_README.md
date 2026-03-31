# 📊 DRE ENGINE CORE

Demonstração de Resultado do Exercício por Evento

## Objetivo
Calcular DRE real para cada evento com base em:
- Receita consolidada
- CMV calculado
- Custos fixos rateados

## Fórmulas

```
Gross Profit = Revenue - CMV
Gross Margin = (Gross Profit / Revenue) × 100

Fixed Allocated = (Revenue / Total Revenue) × Total Fixed Costs

Net Profit = Gross Profit - Fixed Allocated
Net Margin = (Net Profit / Revenue) × 100
```

## Arquivos de Entrada

### 1. events_consolidated.csv
```csv
event_id,n_ctt,company,date_event,revenue_total,client_name,event_type,status
```

**Campos obrigatórios:**
- `event_id` - ID do evento
- `n_ctt` - Núnmero CTT (contrato)
- `company` - opera ou la_orana
- `revenue_total` - Receita do evento

### 2. cmv_log.json
Gerado pelo Kitchen Control Layer

### 3. fixed_costs.csv
```csv
cost_type,description,amount,period
aluguel,Salão Principal,5000.00,monthly
salarios,Equipe Operacional,8000.00,monthly
```

## Arquivos de Saída

### dre_events.csv
DRE detalhado por evento

### dre_summary.json
Resumo agregado com totais e análise

## Uso

```bash
python dre_engine.py
```

## Validações

- ✅ Receita obrigatória
- ✅ CMV obrigatório (erro se ausente)
- ✅ N CTT obrigatório
- ⚠️ Receita = 0 → margem ignorada
- 🚨 Todos os erros em `errors.json`

---

*DRE Engine v1.0 | Orkestra Finance Brain*
