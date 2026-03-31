# POP PRODUÇÃO - EXECUÇÃO DE EVENTOS
## Procedimento Operacional Padrão

**Código:** POP-PROD-001  
**Versão:** 1.0  
**Data:** 2026-03-31  
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
{
  "evento_id": "EVT123",
  "nome_evento": "Casamento Silva",
  "data_execucao": "2026-05-15",
  "responsavel_kitchen": "Chef Ana Maria",
  "equipe": ["João", "Pedro"],
  "receitas_executadas": [
    {
      "receita_id": "REC001",
      "nome": "Escondidinho",
      "porcoes_planejadas": 120,
      "porcoes_produzidas": 130,
      "porcoes_servidas": 118,
      "porcoes_restantes": 12
    }
  ]
}
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
*Data: 2026-03-31*
