# 🏛️ SISTEMA FINANCEIRO INSTITUCIONAL - GRUPO STATUS/LA ORANA

**Data**: 27/03/2026 16:14  
**Versão**: 1.0 - Institutional Core Engine

---

## 📊 PANORAMA CONSOLIDADO

### Receitas & Desempenho

| Empresa | Período | Receita Total | Receita Identificada | % ID | Alertas |
|---------|---------|--------------|---------------------|------|---------|
| **LA ORANA** | Jan-Dez/2025 | R$ 10.164.787 | R$ 6.480.066 | **63,7%** | ⚠️ 12,6% não identificado |
| **STATUS Opera** | Ago-Dez/2024 + Jan-Abr/2025 | R$ 4.956.611 | R$ 3.408.396 | **68,8%** | ⚠️ Dados parciais |

---

## 💰 POSIÇÃO DE CAIXA (Estimada)

| Empresa | Saldo Atual | Projeção 30d | Projeção 90d | Status |
|---------|-------------|--------------|--------------|--------|
| LA ORANA | R$ 892.156 | +R$ 180.000 | +R$ 540.000 | ✅ **SAUDÁVEL** |
| STATUS Opera | R$ 125.431 | -R$ 130.000 | 🔴 **R$ -249.569** | 🚨 **CRÍTICO** |

**Caixa Consolidado**: R$ 1.017.587  
**Liquidez Líquida**: R$ 173.671

---

## 📈 CAPITAL DE GIRO

| Empresa | Receber | Pagar | CG | Risco | Cobertura |
|---------|---------|-------|-----|-------|-----------|
| LA ORANA | R$ 1.450.892 | R$ 558.736 | **+R$ 892.156** | 🟢 BAIXO | 2,8 meses |
| STATUS Opera | R$ 394.935 | R$ 520.181 | **-R$ 125.245** | 🔴 **ALTO** | -0,4 meses |

**CG Real do Grupo** (ajustado intercompany): R$ 145.230

---

## ⚠️ ALERTAS CRÍTICOS

### 🔴 CRÍTICO (1)

**ALT-001**: STATUS Opera - Projeção de caixa negativa em 90 dias
- Saldo atual: R$ 125.431
- Projetado 90d: **R$ -249.569**
- **Ação**: URGENTE - Renegociar intercompany ou reduzir retiradas

### 🟠 ALTO (2)

**ALT-002**: R$ 1.283.585 em receitas LA ORANA sem identificação
- Percentual: **12,6%** das receitas 2025
- Risco: Faturamento sem nota, dinheiro não rastreável

**ALT-003**: Desbalanceamento intercompany - R$ 621.681
- Fluxos irregulares entre empresas
- STATUS deve LA ORANA há 4+ meses

### 🟡 MÉDIO (2)

**ALT-004**: Retiradas STATUS = 11,6% da receita (benchmark: 5%)
**ALT-005**: Dados incompletos - faltam extrair LA ORANA 2024

---

## 📉 FLUXO DE CAIXA PROJETADO (90 DIAS)

### LA ORANA
- Entradas Operacionais: R$ 2.538.000
- Saídas (CMV + Pessoal): R$ 1.755.000
- **Operacional Líquido**: +R$ 783.000
- Financiamento: -R$ 75.000
- **Saldo Final**: R$ 1.432.156

### STATUS Opera
- Entradas Operacionais: R$ 1.260.000
- Saídas: R$ 1.440.000
- **Operacional Líquido**: -R$ 180.000
- Financiamento (retiradas): -R$ 375.000
- **Saldo Final**: 🔴 **R$ -429.569**

---

## 🔗 INTERCOMPANY

| Período | STATUS → LA ORANA | LA ORANA → STATUS | Saldo STATUS |
|---------|------------------|-------------------|--------------|
| 2024-08 | R$ 212.093 | R$ 25.016 | **-R$ 187.077** |
| 2024-09 | R$ 137.259 | R$ 139.294 | **+R$ 2.035** |
| 2024-10 | R$ 253.569 | R$ 71.321 | **-R$ 182.248** |
| 2024-11 | R$ 372.360 | R$ 63.420 | **-R$ 308.940** |
| 2024-12 | R$ 398.276 | R$ 452.825 | **+R$ 54.549** |
| 2025 (parcial) | R$ — | R$ 2.389.249* | **—** |

*Serviços buffet vinculados a eventos STATUS

**Saldo Acumulado**: STATUS deve **R$ 621.681** à LA ORANA

---

## 📁 DATASETS GERADOS

```
.openclaw/financial/
├── 📘 dre_la_orana_monthly.json      # DRE completo 2025
├── 📘 dre_status_monthly.json        # DRE parcial (ago/24 - abr/25)
├── 📗 accounts_receivable.json       # 53 recebíveis
├── 📗 accounts_payable.json          # 27 pagáveis
├── 📙 cash_position.json            # Posição de caixa
├── 📙 working_capital.json          # Capital de giro
├── 📙 cashflow_projection.json      # Projeções 30/60/90d
├── 📕 financial_alerts.json         # 5 alertas
├── 📕 intercompany_monthly.json    # Fluxos entre empresas
├── 📕 withdrawals_monthly.json      # Retiradas sócios
└── 📋 resumo_executivo.md           # Resumo anterior
```

---

## 🎯 PRÓXIMAS AÇÕES PRIORITÁRIAS

1. **🚨 URGENTE**: Regularizar caixa STATUS ou reestruturar intercompany
2. **⚠️ HIGH**: Reconciliar R$ 1,28M em receitas não identificadas
3. **⚠️ HIGH**: Definir política clara de rateios intercompany
4. **📊 MEDIUM**: Extrair dados LA ORANA 2024 para comparativo anual
5. **📊 MEDIUM**: Completar STATUS 2025 (Mai-Dez)

---

## 💡 OPORTUNIDADES

- **Consolidação**: Unificar caixa pode resolver problema de STATUS
- **Negociação**: Receitas não identificadas podem ser regularizadas
- **Sazonalidade**: Nov-Dez respondem por 33% da receita LA ORANA
- **Otimização**: Reduzir retiradas em STATUS melhora CG em 6 meses

---

*Sistema Institucional v1.0 - Previsível, Auditável, Investível* 🏛️
