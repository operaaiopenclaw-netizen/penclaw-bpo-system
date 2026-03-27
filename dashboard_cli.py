#!/usr/bin/env python3
"""
ORKESTRA DASHBOARD - Modo CLI
Dashboard de controle financeiro em terminal
"""

import json
import pandas as pd
from datetime import datetime

def gerar_dashboard():
    # Carrega dados
    with open("financial_log.json", "r") as f:
        raw = json.load(f)
    
    data = raw.get("transactions", [])
    df = pd.DataFrame(data)
    
    print("=" * 70)
    print("📊 ORKESTRA DASHBOARD (Modo Terminal)")
    print("=" * 70)
    print(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print()
    
    if df.empty:
        print("⚠️  Sem dados ainda.")
        return
    
    df["value"] = df["value"].fillna(0).astype(float)
    
    # KPIs
    total_expense = df[df["type"] == "expense"]["value"].sum()
    total_income = df[df["type"] == "income"]["value"].sum()
    margin = total_income - total_expense
    
    print("💰 KPIs Financeiros:")
    print(f"   Receita:   R$ {total_income:>12,.2f}")
    print(f"   Custos:    R$ {total_expense:>12,.2f}")
    print(f"   Margem:    R$ {margin:>12,.2f}")
    print()
    
    # Custos por categoria
    print("📦 Custos por Categoria:")
    print("-" * 50)
    expense_df = df[df["type"] == "expense"]
    if not expense_df.empty and "category" in expense_df.columns:
        cat_summary = expense_df.groupby("category")["value"].sum().sort_values(ascending=False)
        for cat, val in cat_summary.items():
            print(f"   {cat:<20} R$ {val:>12,.2f}")
    else:
        print("   Nenhuma despesa categorizada")
    print()
    
    # Transações recentes
    print("📜 Últimas Transações:")
    print("-" * 70)
    latest = df.sort_values("processed_at", ascending=False).head(5)
    for _, row in latest.iterrows():
        tipo = row['type']
        valor = row['value']
        cat = row.get('category', 'N/A')
        print(f"   {row['id'][:20]:<20} | {tipo:<7} | R$ {valor:>10,.2f} | {cat}")
    
    print()
    print("=" * 70)
    print("✅ Dashboard gerado!")
    print("=" * 70)

if __name__ == "__main__":
    gerar_dashboard()
