# POP ESTOQUE - GERENCIAMENTO DE INVENTÁRIO
## Procedimento Operacional Padrão

**Código:** POP-EST-001  
**Versão:** 1.0  
**Data:** 2026-03-31  
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
{
  "codigo": "CAR-001",
  "nome": "Carne Seca Desfiada",
  "quantidade_atual": 50.5,
  "unidade": "kg",
  "preco_unitario": 45.00,
  "fornecedor_atual": "Açougue Modelo",
  "historico_entradas": [
    {
      "data": "2026-03-20",
      "quantidade": 25.0,
      "preco_unitario": 44.50,
      "fornecedor": "Açougue Modelo",
      "nota_fiscal": "NF12345"
    }
  ]
}
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
{
  "data_inventario": "2026-03-28",
  "responsavel": "Carlos Almoxarife",
  "divergencias": [
    {
      "item_id": "CAR-001",
      "sistema_kg": 50.5,
      "fisico_kg": 48.2,
      "diferenca_pct": -4.5,
      "acao": "investigacao"
    }
  ]
}
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
*Data: 2026-03-31*
