# learning_engine.py - Orkestra Learning Engine
# Motor de aprendizado contínuo que analisa memória e gera insights

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_json(filepath):
    """Carrega JSON com fallback."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def analyze_decisions(filepath="orkestra/memory/decisions.json"):
    """
    Analisa histórico de decisões do Orkestra.
    """
    print("\n📊 ANALISANDO DECISIONS...")
    
    data = load_json(filepath)
    decisions = data.get("decisions", [])
    
    if not decisions:
        print("   ⚠️  Nenhuma decisão encontrada")
        return []
    
    insights = []
    
    # 1. Ações que melhoraram margem
    success_by_action = defaultdict(lambda: {"count": 0, "avg_improvement": 0})
    
    for d in decisions:
        result = d.get("result", "")
        action = d.get("action", "")
        margin_before = d.get("margin_before", 0)
        margin_after = d.get("margin", 0)
        
        if result in ["margin_improved", "success", "APPROVE"]:
            improvement = margin_after - margin_before
            success_by_action[action]["count"] += 1
            success_by_action[action]["avg_improvement"] = (
                (success_by_action[action]["avg_improvement"] * (success_by_action[action]["count"] - 1) + improvement)
                / success_by_action[action]["count"]
            )
    
    for action, stats in success_by_action.items():
        if stats["count"] >= 2:
            insights.append({
                "type": "positive_pattern",
                "action": action,
                "frequency": stats["count"],
                "avg_improvement": round(stats["avg_improvement"], 3),
                "recommendation": f"✅ '{action}' melhora margem em {stats['count']} eventos"
            })
    
    # 2. Causas de problemas
    cause_frequency = defaultdict(int)
    for d in decisions:
        cause = d.get("cause", "unknown")
        if cause != "unknown" and d.get("margin", 0) < 0.3:
            cause_frequency[cause] += 1
    
    for cause, count in cause_frequency.items():
        if count >= 2:
            insights.append({
                "type": "negative_pattern",
                "cause": cause,
                "frequency": count,
                "recommendation": f"⚠️  '{cause}' causa margem baixa em {count} eventos"
            })
    
    print(f"   ✅ {len(decisions)} decisões analisadas")
    print(f"   📈 {len([i for i in insights if i['type'] == 'positive_pattern'])} padrões positivos")
    print(f"   📉 {len([i for i in insights if i['type'] == 'negative_pattern'])} padrões de risco")
    
    return insights


def analyze_performance(filepath="orkestra/memory/performance.json"):
    """
    Analisa performance histórica.
    """
    print("\n📈 ANALISANDO PERFORMANCE...")
    
    data = load_json(filepath)
    records = data.get("records", [])
    
    if not records:
        print("   ⚠️  Nenhum registro de performance")
        return []
    
    insights = []
    
    # 1. Tendência de margem
    margins = [r.get("margin_pct", 0) for r in records]
    avg_margin = sum(margins) / len(margins) if margins else 0
    
    # Dividir em primeira e segunda metade
    mid = len(margins) // 2
    first_half = sum(margins[:mid]) / mid if mid > 0 else 0
    second_half = sum(margins[mid:]) / (len(margins) - mid) if mid < len(margins) else 0
    
    delta = second_half - first_half
    
    trend_emoji = "📈" if delta > 0.05 else "📉" if delta < -0.05 else "➡️"
    trend_msg = "melhorando" if delta > 0.05 else "piorando" if delta < -0.05 else "estável"
    
    insights.append({
        "type": "trend",
        "metric": "margin",
        "value": round(avg_margin, 3),
        "trend": trend_msg,
        "delta": round(delta, 3),
        "recommendation": f"{trend_emoji} Margem média {avg_margin:.1%} - tendência {trend_msg}"
    })
    
    # 2. Categorias mais caras
    category_totals = defaultdict(lambda: {"cost": 0, "revenue": 0})
    
    for r in records:
        kpis = r.get("kpis", {})
        for cat, value in kpis.items():
            if "cost" in cat.lower():
                cat_name = cat.replace("_cost_pct", "")
                category_totals[cat_name]["cost"] += value
            if "revenue" in cat.lower():
                cat_name = cat.replace("_revenue_pct", "")
                category_totals[cat_name]["revenue"] += value
    
    # Calcular médias
    for cat in category_totals:
        category_totals[cat]["avg"] = category_totals[cat]["cost"] / len(records)
    
    # Identificar categorias problemáticas (>40%)
    for cat, data in category_totals.items():
        if data["avg"] > 35:
            insights.append({
                "type": "category_alert",
                "category": cat,
                "avg_cost": round(data["avg"], 1),
                "recommendation": f"⚠️  '{cat}' consome {data['avg']:.0f}% do orçamento (alto)"
            })
    
    # 3. Eventos com prejuízo
    losses = [r for r in records if r.get("margin_pct", 0) < 0]
    if losses:
        insights.append({
            "type": "critical",
            "count": len(losses),
            "recommendation": f"🚨 {len(losses)} evento(s) com prejuízo no histórico"
        })
    
    print(f"   ✅ {len(records)} registros analisados")
    print(f"   📊 Margem média: {avg_margin:.1%}")
    
    return insights


def analyze_errors(filepath="orkestra/memory/errors.json"):
    """
    Analisa erros operacionais.
    """
    print("\n⚠️  ANALISANDO ERRORS...")
    
    data = load_json(filepath)
    errors = data.get("errors", [])
    
    if not errors:
        print("   ✅ Nenhum erro registrado")
        return []
    
    insights = []
    
    # Erros por tipo
    error_types = defaultdict(lambda: {"count": 0, "severity": []})
    
    for e in errors:
        err_type = e.get("error_type", "unknown")
        severity = e.get("severity", "low")
        
        error_types[err_type]["count"] += 1
        error_types[err_type]["severity"].append(severity)
    
    for err_type, data in error_types.items():
        if data["count"] >= 2:
            # Calcular severidade média
            sev_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            avg_sev = sum(sev_map.get(s, 1) for s in data["severity"]) / len(data["severity"])
            
            insights.append({
                "type": "recurring_error",
                "error_type": err_type,
                "count": data["count"],
                "avg_severity": round(avg_sev, 1),
                "recommendation": f"🔴 '{err_type}' ocorreu {data['count']}x (severidade média: {avg_sev:.1f})"
            })
    
    print(f"   ⚠️  {len(errors)} erros analisados")
    print(f"   🔴 {len(insights)} padrões de erro identificados")
    
    return insights


def generate_rules(all_insights):
    """
    Gera regras operacionais baseadas nos insights.
    """
    print("\n⚙️  GERANDO REGRAS...")
    
    rules = []
    
    # Regras de margem
    trend_insights = [i for i in all_insights if i.get("type") == "trend"]
    for t in trend_insights:
        if t.get("trend") == "piorando":
            rules.append({
                "priority": "HIGH",
                "type": "ADJUST",
                "target": "MARGIN_THRESHOLD",
                "action": "Aumentar threshold de alerta de 30% para 35%",
                "rationale": "Tendência de queda detectada"
            })
        elif t.get("value", 0) < 0.25:
            rules.append({
                "priority": "HIGH",
                "type": "REVIEW",
                "target": "PRICING_STRATEGY",
                "action": "Revisar tabela de preços - margem média abaixo de 25%",
                "rationale": f"Margem média atual: {t['value']:.1%}"
            })
    
    # Regras de categoria
    cat_alerts = [i for i in all_insights if i.get("type") == "category_alert"]
    for alert in cat_alerts:
        cat = alert.get("category", "")
        rules.append({
            "priority": "MEDIUM",
            "type": "MONITOR",
            "target": f"CATEGORY_{cat.upper()}",
            "action": f"Monitorar {cat} - representa {alert.get('avg_cost', 0):.0f}% do custo",
            "rationale": "Categoria acima do threshold de 35%"
        })
    
    # Regras de erro
    err_patterns = [i for i in all_insights if i.get("type") == "recurring_error"]
    for err in err_patterns:
        err_type = err.get("error_type", "")
        if err_type == "stockout":
            rules.append({
                "priority": "CRITICAL",
                "type": "PROCESS",
                "target": "INVENTORY_MANAGEMENT",
                "action": "Implementar checklist estoque 48h antes do evento",
                "rationale": f"{err.get('count', 0)} rupturas no histórico"
            })
    
    # Regras de ações que funcionam
    positive_patterns = [i for i in all_insights if i.get("type") == "positive_pattern"]
    for pattern in positive_patterns:
        action = pattern.get("action", "")
        rules.append({
            "priority": "LOW",
            "type": "AUTOSUGGEST",
            "target": "DECISION_SUPPORT",
            "action": f"Sugerir automaticamente '{action}' quando margem < 30%",
            "rationale": f"Ação melhorou margem em {pattern.get('frequency', 0)} eventos"
        })
    
    print(f"   ✅ {len(rules)} regras geradas")
    
    return rules


def print_report(decision_insights, perf_insights, error_insights, rules):
    """
    Imprime relatório completo.
    """
    print("\n" + "=" * 70)
    print("🎛️ ORKESTRA LEARNING ENGINE REPORT")
    print("=" * 70)
    print(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Insights
    all_insights = decision_insights + perf_insights + error_insights
    
    print("\n" + "-" * 70)
    print("📊 INSIGHTS IDENTIFICADOS")
    print("-" * 70)
    
    if all_insights:
        for i, insight in enumerate(all_insights, 1):
            print(f"\n{i}. {insight.get('recommendation', 'N/A')}")
            if insight.get('type') == 'positive_pattern':
                print(f"   📈 Frequência: {insight.get('frequency')} | Melhoria média: {insight.get('avg_improvement', 0):.1%}")
            elif insight.get('type') == 'category_alert':
                print(f"   📊 Custo médio: {insight.get('avg_cost', 0):.0f}%")
    else:
        print("   ℹ️  Dados insuficientes para insights significativos")
    
    # Regras
    print("\n" + "-" * 70)
    print("⚙️  REGRAS SUGERIDAS")
    print("-" * 70)
    
    if rules:
        # Ordenar por prioridade
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        rules_sorted = sorted(rules, key=lambda x: priority_order.get(x.get("priority", "LOW"), 4))
        
        for r in rules_sorted:
            emoji = {"CRITICAL": "🚨", "HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(r.get("priority"), "⚪")
            print(f"\n   {emoji} [{r.get('priority')}] {r.get('type')}")
            print(f"      📋 {r.get('action')}")
            print(f"      💭 {r.get('rationale')}")
    else:
        print("   ✅ Nenhuma regra necessária")
    
    # Resumo
    print("\n" + "-" * 70)
    print("📋 RESUMO EXECUTIVO")
    print("-" * 70)
    
    critical = len([r for r in rules if r.get("priority") == "CRITICAL"])
    high = len([r for r in rules if r.get("priority") == "HIGH"])
    medium = len([r for r in rules if r.get("priority") == "MEDIUM"])
    
    print(f"   🚨 Críticas: {critical}")
    print(f"   🔴 Alta: {high}")
    print(f"   🟡 Média: {medium}")
    print(f"   📊 Total insights: {len(all_insights)}")
    
    if critical > 0:
        print("\n   ⚠️  AÇÃO IMEDIATA NECESSÁRIA")
    
    print("\n" + "=" * 70)


def run_learning_engine():
    """
    Executa o motor de aprendizado completo.
    """
    print("🚀 ORKESTRA LEARNING ENGINE")
    print("=" * 70)
    
    # Verificar estrutura
    mem_dir = Path("orkestra/memory")
    if not mem_dir.exists():
        print("❌ Diretório orkestra/memory não encontrado")
        return
    
    # Analisar cada fonte
    decision_insights = analyze_decisions(mem_dir / "decisions.json")
    perf_insights = analyze_performance(mem_dir / "performance.json")
    error_insights = analyze_errors(mem_dir / "errors.json")
    
    # Gerar regras
    all_insights = decision_insights + perf_insights + error_insights
    rules = generate_rules(all_insights)
    
    # Imprimir relatório
    print_report(decision_insights, perf_insights, error_insights, rules)
    
    # Salvar resultados
    output = {
        "timestamp": datetime.now().isoformat(),
        "insights_count": len(all_insights),
        "rules_count": len(rules),
        "insights": all_insights,
        "rules": rules,
        "summary": {
            "critical": len([r for r in rules if r.get("priority") == "CRITICAL"]),
            "high": len([r for r in rules if r.get("priority") == "HIGH"]),
            "medium": len([r for r in rules if r.get("priority") == "MEDIUM"]),
            "low": len([r for r in rules if r.get("priority") == "LOW"])
        }
    }
    
    output_path = mem_dir / "learning_report.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Relatório salvo: {output_path}")
    print("✅ Learning Engine completo!")


if __name__ == "__main__":
    run_learning_engine()
