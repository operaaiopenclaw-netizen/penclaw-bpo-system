# POP COMERCIAL - VENDAS E ORÇAMENTOS
## Procedimento Operacional Padrão

**Código:** POP-COM-001  
**Versão:** 1.0  
**Data:** 2026-03-31  
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
*Data: 2026-03-31*
