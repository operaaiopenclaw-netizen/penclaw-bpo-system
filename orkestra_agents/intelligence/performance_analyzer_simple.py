# performance_analyzer_simple.py - Analisador de Performance Simplificado
# Exemplo prático de Self Improvement para Orkestra

import json
from collections import defaultdict
from pathlib import Path


def load_json(path):
    """Carrega JSON com fallback para lista vazia."""
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return []


def analyze_performance(filepath="memory/performance.json"):
    """
    Analisa histórico de performance e identifica padrões problemáticos.
    """
    data = load_json(filepath)
    
    # Se for dict com chave 'records', extrai a lista
    if isinstance(data, dict):
        data = data.get("records", [])
    
    insights = []
    
    for item in data:
        margin = item.get("margin_pct", item.get("margin", 0))
        event = item.get("event", "unknown")
        
        if margin < 0:
            insights.append({
                "event": event,
                "margin": margin,
                "issue": "negative_margin",
                "severity": "critical",
                "suggestion": "reprice_or_reduce_cost",
                "action": "BLOCK_EVENT_TYPE"
            })
        
        elif margin < 0.30:
            insights.append({
                "event": event,
                "margin": margin,
                "issue": "low_margin",
                "severity": "warning",
                "suggestion": "optimize_cost_structure",
                "action": "REVIEW_CATEGORIES"
            })
    
    return insights


def analyze_by_category(filepath="memory/performance.json"):
    """
    Analisa gastos por categoria para identificar desvios.
    """
    data = load_json(filepath)
    
    if isinstance(data, dict):
        data = data.get("records", [])
    
    category_totals = defaultdict(lambda: {"cost": 0, "revenue": 0, "count": 0})
    
    for item in data:
        kpis = item.get("kpis", {})
        for cat, value in kpis.items():
            if "cost" in cat.lower():
                category_totals[cat]["cost"] += value
            if "revenue" in cat.lower():
                category_totals[cat]["revenue"] += value
        
        # Contar ocorrências
        for cat in kpis.keys():
            category_totals[cat]["count"] += 1
    
    insights = []
    
    for cat, totals in category_totals.items():
        if totals["revenue"] > 0:
            pct = totals["cost"] / totals["revenue"]
            if pct > 0.40:  # Mais de 40% da receita
                insights.append({
                    "category": cat,
                    "percentage": round(pct * 100, 1),
                    "issue": "high_category_spend",
                    "suggestion": f"review_{cat}_supplier"
                })
    
    return insights


def generate_rules(insights):
    """
    Gera regras operacionais baseadas nos insights.
    """
    rules = []
    
    # Agrupar por tipo de problema
    negative_margins = [i for i in insights if i.get("issue") == "negative_margin"]
    low_margins = [i for i in insights if i.get("issue") == "low_margin"]
    
    # Regras para margem negativa
    if len(negative_margins) >= 2:
        rules.append({
            "type": "BLOCK",
            "condition": "margin_projected < 0",
            "action": "REQUIRE_MANAGER_APPROVAL",
            "priority": "CRITICAL",
            "rationale": f"{len(negative_margins)} eventos com prejuízo no histórico"
        })
    
    # Regras para margem baixa
    if len(low_margins) >= 3:
        rules.append({
            "type": "ADJUST",
            "target": "MARGIN_THRESHOLD",
            "from": "30%",
            "to": "35%",
            "priority": "HIGH",
            "rationale": f"{len(low_margins)} eventos abaixo do threshold"
        })
    
    # Regras para categorias problemáticas
    high_spend = [i for i in insights if i.get("issue") == "high_category_spend"]
    for h in high_spend:
        cat = h.get("category", "unknown")
        rules.append({
            "type": "ALERT",
            "target": f"CATEGORY_{cat}",
            "condition": f"{cat}_cost > 40%",
            "action": "FLAG_FOR_REVIEW",
            "priority": "MEDIUM",
            "rationale": f"{h.get('percentage')}% da receita consumida por {cat}"
        })
    
    return rules


def print_report(insights, rules):
    """
    Gera relatório legível.
    """
    print("=" * 60)
    print("🎛️ ORKESTRA PERFORMANCE ANALYZER REPORT")
    print("=" * 60)
    
    print("\n📊 INSIGHTS IDENTIFICADOS:")
    if insights:
        for i in insights:
            emoji = "🔴" if i.get("severity") == "critical" else "🟡"
            print(f"\n   {emoji} Evento: {i.get('event', 'N/A')}")
            print(f"      Problema: {i.get('issue', 'N/A')}")
            if 'margin' in i:
                print(f"      Margem: {i['margin']:.1%}")
            print(f"      Sugestão: {i.get('suggestion', 'N/A')}")
    else:
        print("   ✅ Nenhum problema identificado - performance saudável")
    
    print("\n📜 REGRAS GERADAS:")
    if rules:
        for r in rules:
            emoji = "🚫" if r.get("type") == "BLOCK" else "⚙️" if r.get("type") == "ADJUST" else "⚠️"
            print(f"\n   {emoji} [{r.get('priority', 'LOW')}] {r.get('type')}")
            print(f"      Ação: {r.get('action', 'N/A')}")
            if 'rationale' in r:
                print(f"      Motivo: {r.get('rationale')}")
    else:
        print("   ✅ Nenhuma regra nova necessária")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Executar análise
    insights = analyze_performance()
    category_insights = analyze_by_category()
    all_insights = insights + category_insights
    
    rules = generate_rules(all_insights)
    
    print_report(all_insights, rules)
    
    # Salvar resultados
    result = {
        "timestamp": Path("memory/performance.json").stat().st_mtime if Path("memory/performance.json").exists() else None,
        "insights_count": len(all_insights),
        "rules_generated": len(rules),
        "insights": all_insights,
        "rules": rules
    }
    
    output_path = "memory/performance_analysis.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n💾 Análise salva em: {output_path}")
