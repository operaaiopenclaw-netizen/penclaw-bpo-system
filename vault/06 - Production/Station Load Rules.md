# Station Load Rules

Como o motor de `ProductionPlan` divide carga entre estações de cozinha. Regras empíricas baseadas em capacidade real de preparo, não em teoria.

---

## Princípios

1. **Estação nunca > 85% de capacidade nominal**. Acima disso, tempo de emplacamento dispara e qualidade cai.
2. **Prato assinatura não compete com base**. Receitas de alta complexidade (> 15 min de finalização por prato) ganham estação dedicada; o resto equilibra entre estações genéricas.
3. **Frio na frente, quente no meio, finalização no fim**. Sequência física de estações segue o fluxo de serviço, não o organograma da cozinha.

---

## Tipos de estação

| Estação | Capacidade nominal (pratos/h) | Boa para |
|---|---|---|
| Frio 1 | 120 | Saladas, carpaccios, amuse-bouche |
| Frio 2 | 120 | Entradas geladas, sobremesas montadas |
| Quente Principal | 80 | Pratos de forno, grelhados, finalizações críticas |
| Quente Secundário | 100 | Guarnições, acompanhamentos, massas |
| Finalização/Empacotamento | 200 | Box individual, montagem final, embalagem |

Valores são **base**; `ItemAdjustment` por cozinha afina conforme histórico real.

---

## Regras de alocação

### Divisão 1: por temperatura

Receita `temperature = COLD` → só em Frio 1 ou Frio 2.
Receita `temperature = HOT` → só em Quente Principal ou Quente Secundário.
Receita `temperature = ROOM` → prefere Finalização; se saturada, vai para Frio 2.

### Divisão 2: por complexidade

Se `Recipe.complexityScore ≥ 4` (escala 1–5), receita **consome 1.3× sua contagem nominal** na estação (custo extra de atenção). O motor considera isso no cálculo de saturação.

### Divisão 3: dependências

Receita com `dependsOn` (ex.: finalização depende de base pronta) nunca roda simultaneamente com sua dependência na mesma estação — divide em janelas.

### Divisão 4: fallback quando saturado

Se qualquer estação > 85% prevista:

1. Motor tenta redistribuir receitas `complexityScore ≤ 2` para estação menos crítica.
2. Se ainda saturado, sugere **dobra de turno** (alerta MEDIUM: `PRODUCAO_SATURADA`).
3. Se recusado, flag no `/operations/risks?eventId=...` como risco HIGH de atraso.

---

## Exemplos

**Evento 150 convidados, menu 4 tempos**

- Entrada fria (150 pratos) → Frio 1 (125%? não, 125 divide em 2 janelas → OK)
- Prato principal quente (150 + acompanhamento) → Principal (80/h → precisa 2h de produção + buffer) + Secundário
- Sobremesa montada (150) → Frio 2 em janela pré-serviço

Motor confirma `ProductionPlan.status = APPROVED` quando todas as estações < 85% em nenhuma janela de 30 min.

---

## Ajustes específicos por cozinha

Motor guarda `KitchenCapacityProfile` por `kitchenId` — se a cozinha tem histórico de 70% do nominal em Quente Principal (equipamento mais lento, espaço apertado), usar esse valor.

Primeiro evento numa cozinha nova: usar nominais, marcar como **calibração**, reconciliar após e ajustar.

---

Tags: `#producao`  `#cozinha`  `#politica`
Links: `[[Alert Taxonomy]]` • `[[Margin Framework]]`
