# 🍳 Kitchen Intelligence Engine (KIE)

Sistema de gestão de cozinha em eventos — controle de receitas, produção, custo e desperdício.

---

## 📁 Estrutura de Arquivos

```
kitchen_data/
├── recipes.json           # Receitas com ingredientes e rendimentos
├── recipe_costs.json      # Custos calculados automáticos
├── production_plan.json   # Planos de produção por evento
├── production_execution.json  # Registro de produção real
├── waste_log.json         # Registro de desperdício/post-evento
└── inventory.json         # Integração com estoque (fonte de preços)
```

**Código Fonte:**
- `kitchen_engine.py` — Core engine com todas as funções
- `kitchen_cli.py` — Interface interativa CLI

---

## 🎯 Funcionalidades

### A. Cálculo Automático de Custo por Receita
```python
atualizar_custos_receitas()
```
- Busca preços do `inventory.json`
- Recalcula custos de todas as receitas
- Exporta para `recipe_costs.json`

### B. Planejamento de Produção por Evento
```python
plano = criar_plano_producao(
    evento_id="EVT001",
    nome_evento="Casamento Silva",
    data_evento="2026-04-15",
    num_convidados=120,
    tipo_servico="buffet_completo"
)
```

### C. Integração com Estoque
```python
check_estoque_disponivel("EVT001")
```
- Lista itens faltantes
- Sugere compras necessárias
- Atualiza flag de validação

### D. Registro de Produção Real
```python
registrar_producao_real(execucao_id, evento_id, receitas_executadas)
```

### E. Cálculo de Desperdício
```python
registrar_desperdicio(evento_id, itens_desperdicio, observacao)
```
- Classifica desperdício (TIPO_A até TIPO_E)
- Calcula custo recuperável
- Flag de benchmarking (5% aceitável)

### F. CMV Real por Evento
```python
calcular_cmv_evento("EVT001")
```
- Retorna custo de mercadoria vendida
- Compara real vs planejado
- Indicadores de eficiência

---

## 🎛️ Como Usar

### Modo CLI (Interativo)
```bash
chmod +x kitchen_cli.py
python3 kitchen_cli.py
```

Menu:
```
1. 📊 Atualizar custos de receitas
2. 📝 Criar plano de produção
3. 📦 Verificar disponibilidade de estoque
4. 🍽️  Registrar produção real
5. 🗑️  Registrar desperdício
6. 💰 Calcular CMV
7. 💡 Sugestões de otimização
8. 📈 Relatório completo
```

### Modo API (Importar)
```python
from kitchen_engine import (
    atualizar_custos_receitas,
    criar_plano_producao,
    check_estoque_disponivel,
    registrar_producao_real,
    calcular_cmv_evento
)

# Usar funções diretamente
custo = calcular_cmv_evento("EVT001")
```

---

## 🔌 Integração

### Para Inventory/Procurement Engine
O engine espera:
```json
{
  "inventory": [
    {
      "codigo": "CAR-001",
      "nome": "Carne Seca Desfiada",
      "quantidade_atual": 50,
      "unidade": "kg",
      "preco_unitario": 45.00
    }
  ]
}
```

### Para Financial Core
CMVs calculados alimentam:
- `custo_total_evento`
- `margem_real`
- `benchmark_comparativo`

---

## 📊 Métricas e Alertas

### Desperdício (Benchmarks)
- **< 5%** → 🟢 Dentro do aceitável
- **5-10%** → 🟡 Atenção
- **> 10%** → 🔴 Crítico

### CMV
- Compara real vs planejado
- Identifica variações suspeitas
- Sugere ações corretivas

---

## 🚀 Próximos Passos

1. Preencher `inventory.json` com dados reais
2. Testar cálculo de receitas
3. Criar primeiro plano de evento
4. Integrar com sistema de compras

---

*Kitchen Intelligence Engine v1.0*  
*Criado em: 31/03/2026*
