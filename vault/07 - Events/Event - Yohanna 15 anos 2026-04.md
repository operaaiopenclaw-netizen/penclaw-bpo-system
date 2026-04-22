---
type: event
status: closed
event_date: 2026-04-19
reconciled_at: 2026-04-21
kitchen: cozinha-matriz
client_type: social
guests: 120
ticket_total: 28500
margin_projected: 0.32
margin_real: 0.27
cmv_real: 16948.97
tags: [evento, aniversario, teste-real, reconciliado]
---

# Event — Aniversário 15 anos Yohanna · 2026-04-19

Primeiro teste real do sistema ponta-a-ponta com reconciliação fechada. **Referência** para precificar aniversários sociais 100–150 convidados.

---

## Contexto

- **Cliente**: família Yohanna (pessoa física, indicação direta de operador).
- **Tipo**: aniversário 15 anos, formato buffet + finalização quente.
- **Data**: 2026-04-19 (sábado).
- **Local**: cozinha matriz, entrega no salão de festa do cliente.
- **Convidados confirmados**: 120.
- **Menu**: 4 tempos + estação de doces.

---

## Números

| Item | Projetado | Real | Δ |
|---|---|---|---|
| Receita | R$ 28.500,00 | R$ 28.500,00 | 0% |
| CMV | R$ 15.580,00 | R$ 16.948,97 | +8,8% |
| Custos diretos | R$ 3.600,00 | R$ 3.850,00 | +6,9% |
| Margem de contribuição | R$ 9.120 (32%) | R$ 7.701 (27%) | **−5 p.p.** |

**Classificação de margem**: Aceitável (faixa 25–35%), mas abaixo da meta de 30%.

---

## O que funcionou

- **Forecast de volume** por tempo acertou em 161 de 165 ingredientes (97.5%).
- **Procurement** fechou PO em primary para 100% do CMV, lead time médio 48h.
- **Station Load** ficou em 78% no pico (Quente Principal), dentro do limite.
- **Reconciliação automática** disparou em `event + 30h`, abaixo das 72h estipuladas.

---

## O que não funcionou

- **4 ingredientes importados** (trufa, azeite premium, queijo envelhecido, balsâmico reserva) tiveram preço > 15% acima do catálogo → responsável por ~60% do desvio de CMV. Ver `[[Learning - Ingredientes importados descalibram CMV 2026-04]]`.
- **Cliente pediu alteração 5 dias antes do evento** (trocar principal frio por quente), o sistema aceitou mas não recalculou margem — margem projetada foi revisada manualmente pelo operador, deveria ter sido automática.
- **2 itens de mise-en-place** (raspa de limão siciliano, flor comestível) passaram por backup supplier por ruptura em primary → custo +30% nesses itens.

---

## Ações

- ✅ `[[Learning - Ingredientes importados descalibram CMV 2026-04]]` aberto.
- ✅ `ItemAdjustment` criado para trufa (ajuste +12%), azeite premium (+10%), queijo envelhecido (+8%), balsâmico (+15%).
- 🟡 **Decision pendente**: aceitar alterações < 7 dias do evento sem recálculo automático de margem? Ver `[[Decision - Tratamento de alterações tardias de menu]]` (a criar).
- 🟡 Avaliar se raspa de limão siciliano e flor comestível merecem fornecedor secondary cadastrado (hoje só primary + backup).

---

## Commercial

- Closer: não aplicável — venda direta, sem comissão gerada neste evento (venda antes do motor de comissão entrar em produção).
- Futuros aniversários 15 anos neste perfil: precificar com margem projetada **33%** (teto contra desvio de importados), não 32%.

---

## Links

- Dados operacionais brutos: ORKESTRA `/operations/lifecycle/<id-yohanna>`
- `[[Learning - Ingredientes importados descalibram CMV 2026-04]]`
- `[[Supplier Segmentation]]` (backup usage note)
- `[[Margin Framework]]`
