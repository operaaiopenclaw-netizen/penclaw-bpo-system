# Sistema de Rotina Financeira - Empresa

## 📊 Visão Geral

Sistema estruturado para controle financeiro completo: contas a pagar/receber, conciliação bancária e fluxo de caixa.

---

## 🔁 ROTINA DIÁRIA

### Manhã (1ª coisa)
1. **Conferir caixa do dia anterior**
   - [ ] Fechamento de caixa anterior está correto?
   - [ ] Valor físico bate com sistema?

2. **Extratos bancários (todos os bancos)**
   - [ ] Baixar extratos do dia anterior
   - [ ] Identificar movimentações não registradas
   - [ ] Registrar no sistema

3. **Emails/Notificações financeiras**
   - [ ] Recebimentos confirmados (boletos pagos)
   - [ ] Alertas de vencimento
   - [ ] Comunicados de bancos

### Tarde
4. **Contas a Receber - Acompanhamento**
   - [ ] Boletos vencendo hoje/amanhã: cobrar cliente
   - [ ] Boletos vencidos: ligar/email para cobrança
   - [ ] Confirmar recebimentos que entraram

5. **Contas a Pagar - Preparação**
   - [ ] Revisar vencimentos dos próximos 3 dias
   - [ ] Confirmar saldo disponível para pagamentos
   - [ ] Agendar/efetuar pagamentos do dia

6. **Lançamentos do dia**
   - [ ] Notas fiscais emitidas → registrar receita
   - [ ] Despesas do dia → registrar saídas
   - [ ] Registrar no caixa ou contas específicas

---

## 📅 ROTINA SEMANAL (Toda Segunda-feira)

### Contas a Receber
- [ ] Relatório de inadimplência (clientes em atraso)
- [ ] Análise: quem precisa de cobrança intensiva?
- [ ] Atualizar negociações/propostas de parcelamento

### Contas a Pagar
- [ ] Mapear todos os vencimentos da semana
- [ ] Priorizar pagamentos (fornecedores críticos, impostos)
- [ ] Verificar descontos por pagamento antecipado

### Conciliação Bancária
- [ ] Conciliar TODAS as movimentações da semana anterior
- [ ] Identificar lançamentos pendentes
- [ ] Resolver divergências

### Fluxo de Caixa
- [ ] Projeção de caixa para a semana (entradas x saídas)
- [ ] Alertar gestão se houver risco de "aperto"

---

## 📆 ROTINA MENSAL

### Semana 1 (Dias 1-7)
- [ ] Fechamento do mês anterior
- [ ] Conciliação bancária completa de todos os bancos
- [ ] Relatório de inadimplência do mês
- [ ] Contabilidade: enviar documentos para contador

### Semana 2 (Dias 8-14)
- [ ] Análise de fluxo de caixa do mês anterior
- [ ] Comparar: realizado vs projetado
- [ ] Identificar desvios e causas

### Semana 3 (Dias 15-21)
- [ ] Projeção de caixa para os próximos 30-60 dias
- [ ] Reunião com gestão: situação financeira
- [ ] Verificar saldos de fornecedores (débitos pendentes)

### Semana 4 (Dias 22-fim)
- [ ] Preparação de pagamentos do próximo mês
- [ ] Verificar impostos a pagar (DAS, INSS, IR, etc.)
- [ ] Backup de todos os arquivos financeiros

---

## 📋 TEMPLATES ÚTEIS

### 1. Planilha de Contas a Pagar (Estrutura)
| Fornecedor | Descrição | Vencimento | Valor | Status | Pagamento |
|------------|-----------|------------|-------|--------|-----------|
| Ex: Forn A | Matéria-prima | 10/03/2026 | R$5.000 | Pendente | - |

### 2. Planilha de Contas a Receber (Estrutura)
| Cliente | NF | Emissão | Vencimento | Valor | Status | Recebimento |
|---------|-----|---------|------------|-------|--------|-------------|
| Ex: Cliente B | 1234 | 01/03/2026 | 15/03/2026 | R$8.000 | Pendente | - |

### 3. Fluxo de Caixa Diário (Estrutura)
| Data | Saldo Inicial | Entradas | Saídas | Saldo Final | Observação |
|------|---------------|----------|--------|-------------|------------|
| 24/03/2026 | R$10.000 | R$15.000 | R$8.000 | R$17.000 | - |

---

## 🚨 ALERTAS E CONTROLES

### Vermelho (Ação Imediata)
- Saldo negativo projetado nos próximos 7 dias
- Conta a pagar sem saldo para cobrir no vencimento
- Inadimplência acima de X% (definir % da empresa)

### Amarelo (Atenção)
- Cliente habitual atrasou 1º boleto
- Despesa acima da média histórica
- Saldo baixo em conta específica

### Verde (Normal)
- Tudo dentro do planejado
- Recebimentos em dia
- Pagamentos programados com saldo suficiente

---

## 📝 CHECKLIST DE FECHAMENTO MENSAL

- [ ] Todos os recebimentos do mês registrados
- [ ] Todas as contas pagas do mês registradas
- [ ] Conciliação bancária: 100% ok
- [ ] Caixa físico conferido e fechado
- [ ] Relatório mensal gerado e salvo
- [ ] Backup realizado
- [ ] Contador recebeu documentação
- [ ] Gestão recebeu resumo executivo

---

## 💡 DICAS DE EXECUÇÃO

1. **Automatize o máximo possível**
   - Importação automática de extratos bancários
   - Cobrança automática de boletos (email)
   - Alertas automáticos de vencimento

2. **Documente tudo**
   - Anexe NF/comprovantes a cada lançamento
   - Use descrições claras (evite "serviço", use "manutenção ar cond X PT")

3. **Separe contas**
   - Conta operacional (dia a dia)
   - Conta reserva/emergência
   - Conta específica para impostos/investimentos

4. **Controle de acesso**
   - Quem pode aprovar pagamentos?
   - Quem pode alterar registros?
   - Quem visualiza apenas relatórios?

---

## 📁 ESTRUTURA DE PASTAS SUGERIDA

```
FINANCEIRO/
├── 01_CONTAS_A_PAGAR/
│   ├── 2026/
│   │   ├── 03_MARCO/
│   │   ├── 04_ABRIL/
│   └── ...
├── 02_CONTAS_A_RECEBER/
│   ├── 2026/
│   └── ...
├── 03_EXTRATOS_BANCARIOS/
│   ├── BANCO_A/
│   ├── BANCO_B/
│   └── ...
├── 04_FLUXO_DE_CAIXA/
│   └── ...
├── 05_CONCILIACOES/
│   └── ...
└── 06_RELATORIOS/
    └── ...
```

---

*Última atualização: 24/03/2026*
*Próxima revisão mensal: 31/03/2026*
