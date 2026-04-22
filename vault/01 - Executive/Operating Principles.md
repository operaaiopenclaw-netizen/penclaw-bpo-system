# Operating Principles

Princípios não-negociáveis. Se uma decisão conflita com algum destes, o **princípio ganha por padrão** — reverter exige registro explícito em `[[Dashboard - Decision Tracker]]`.

---

## 1. Margem antes de volume

Preferimos rejeitar um evento do que aceitar margem < 20%. Volume sem margem é fadiga operacional mascarada de crescimento.

**Aplicação**: vendedor não fecha abaixo de 20% sem aprovação de `sales_manager` + `finance`.

## 2. Reconciliar sempre, mesmo quando doer

Todo evento encerra com reconciliação real vs forecast em até 72h. Sem exceção. Reconciliação adiada vira dívida técnica no modelo de previsão.

**Aplicação**: `SOP - Event Closeout` (a criar) obriga reconciliação antes do próximo evento da mesma cozinha.

## 3. Auditabilidade por default

Toda decisão automatizada grava `OperationalDecision` com payload. Humano pode sempre perguntar "por quê?" ao sistema e obter resposta.

**Aplicação**: `policy-engine.ts` exige `reason` em toda decisão não-trivial.

## 4. Forecast é hipótese, não verdade

O sistema prevê, mas nunca "acredita" — sempre pronto para ser refutado por dado real. EWMA e ajustes por `ItemAdjustment` pesam histórico, mas rejeitam outliers inexplicados.

**Aplicação**: `RECONCILIACAO_VARIANCIA_ALTA` sempre abre um ciclo de análise, nunca auto-aceita.

## 5. Nenhum dado real fora do ORKESTRA

Estado ao vivo (estoque atual, parcela paga, margem realizada) vive no Postgres. Planilhas paralelas geram fé própria e matam a integridade do modelo.

**Aplicação**: este vault documenta, não transaciona.

## 6. Humano aprova, agente executa

Agentes autônomos executam tarefas de baixo risco. Toda operação financeira, toda decisão que afeta margem real, passa por aprovação humana via `ApprovalRequest`.

**Aplicação**: RBAC + `approvals.high.approve` (finance/admin only).

## 7. Comissão alinhada à margem

Vendedor ganha sobre margem de contribuição, não sobre faturamento. Se ele queima margem para fechar, queima junto a própria comissão.

**Aplicação**: `[[Commission Policy]]` — `baseType=MARGIN` é o default no motor de comissão.

## 8. Pague rápido, mas só o confirmado

Comissão da parcela libera em ≤ 7 dias após Payment confirmado (carência). Nunca antes. Clawback é pior que comissão atrasada.

**Aplicação**: `CommissionPlan.carencyDays` default 7 em contratos novos.

## 9. Aprendizado tem prazo

Toda lição capturada aqui precisa virar mudança em ≤ 30 dias — Decision, SOP, feature, ou parâmetro. Learning sem próximo passo é fofoca.

**Aplicação**: `[[Dashboard - Learning Index]]` mostra learnings sem outcome há >30 dias.

## 10. Simples > genial

Regra de 3 linhas supera heurística de machine learning quando ninguém entende a heurística. Só promovemos algoritmo quando a regra simples provou insuficiência — e o upgrade vem com Decision registrada.

**Aplicação**: `policy-engine.ts` começa com regras determinísticas; `agent` só entra depois.

---

Tags: `#principios`  `#governanca`
Links: `[[Mission]]` • `[[North Star Metrics]]` • `[[Commission Policy]]`
