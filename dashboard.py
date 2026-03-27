#!/usr/bin/env python3
"""
ORKESTRA CONTROL PANEL
Dashboard completo de controle financeiro e operacional
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(layout="wide")

st.title("📊 ORKESTRA CONTROL PANEL")

# ========================
# LOAD DATA
# ========================

with open("financial_log.json", "r") as f:
    raw = json.load(f)

data = raw.get("transactions", [])
df = pd.DataFrame(data)

if df.empty:
    st.warning("Sem dados ainda")
    st.stop()

# ========================
# NORMALIZAÇÃO DE DADOS
# ========================

# Detecta campo de valor
if "value" in df.columns:
    df["value"] = df["value"].astype(float)
elif "amount" in df.columns:
    df["value"] = df["amount"].astype(float)
elif "valor" in df.columns:
    df["value"] = df["valor"].astype(float)
else:
    st.error("❌ Nenhuma coluna de valor encontrada (value/amount/valor)")
    st.stop()

# Garante colunas essenciais
for col in ["type", "category", "event"]:
    if col not in df.columns:
        df[col] = "unknown"

# ========================
# KPIs
# ========================

total_expense = df[df["type"] == "expense"]["value"].sum()
total_income = df[df["type"] == "income"]["value"].sum()
margin = total_income - total_expense

col1, col2, col3 = st.columns(3)

col1.metric("💰 Receita", f"R$ {total_income:,.2f}")
col2.metric("💸 Custos", f"R$ {total_expense:,.2f}")
col3.metric("📊 Margem", f"R$ {margin:,.2f}")

st.divider()

# ========================
# CATEGORIA
# ========================

st.subheader("📦 Custos por Categoria")

cat_df = (
    df[df["type"] == "expense"]
    .groupby("category")["value"]
    .sum()
)

st.bar_chart(cat_df)

# ========================
# EVENTOS
# ========================

st.subheader("🎯 Performance por Evento")

event_df = (
    df.groupby(["event", "type"])["value"]
    .sum()
    .unstack()
    .fillna(0)
)

event_df["margin"] = event_df.get("income", 0) - event_df.get("expense", 0)

st.dataframe(event_df)

# ========================
# ALERTAS
# ========================

st.subheader("🚨 Alertas")

if "has_alerts" in df.columns:
    alerts = df[df["has_alerts"] == True]
else:
    alerts = pd.DataFrame()

if not alerts.empty:
    st.dataframe(alerts)
else:
    st.success("Sem alertas críticos")
