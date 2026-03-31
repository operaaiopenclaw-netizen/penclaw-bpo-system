# 🛒 PROCUREMENT FEEDBACK LOOP ENGINE

Ajusta compras com base no consumo real dos eventos.

---

## Objetivo

Identificar oportunidades de otimização de compra:
- Insumos mais consumidos
- Custo médio real vs histórico
- Variação de preço
- Risco de ruptura

---

## Tipos de Ação

| Tipo | Situação | Ação |
|------|----------|------|
| `change_supplier` | Preço subiu > 15% | Negociar fornecedor alternativo |
| `adjust_volume` | Variação > 5% | Ajustar qtd conforme tendência |
| `prevent_stockout` | Estoque < 7 dias | Compra urgente |
| `optimize_price` | Alto consumo + preço estável | Negociar desconto volume |

---

## Inputs

- `kitchen_data/waste_log.json` → Consumo real por evento
- `kitchen_data/inventory.json` → Estoque com histórico de preços
- `kitchen_data/events_consolidated.csv` → Eventos históricos

---

## Outputs

```
kitchen_data/procurement_suggestions.json
output/procurement_suggestions.csv
```

---

## Exemplo de Sugestão

```json
{
  "item_id": "CAR-001",
  "item_name": "Carne Seca Desfiada",
  "suggestion_type": "change_supplier",
  "priority": "HIGH",
  "current_avg_cost": 52.00,
  "historical_avg_cost": 45.00,
  "price_variation_pct": 15.5,
  "monthly_consumption": 25.5,
  "recommended_action": "Negociar com 3 fornecedores alternativos",
  "reason": "Preço subiu 15.5% vs média histórica"
}
```

---

## Uso

```bash
python3 procurement_feedback_engine.py
```

---

*Procurement Feedback Loop v1.0*
