# simulator.py - Orkestra Event Simulator
# Simula eventos futuros aplicando regras aprendidas

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Carregar regras aprendidas
def load_learning_rules() -> Dict:
    """Carrega regras geradas pelo Learning Engine."""
    try:
        with open("orkestra/memory/learning_report.json", "r") as f:
            data = json.load(f)
            return {
                "rules": data.get("rules", []),
                "insights": data.get("insights", []),
                "avg_margin": data.get("avg_margin_historical", 0.177)
            }
    except:
        return {
            "rules": [],
            "insights": [],
            "avg_margin": 0.65  # fallback: custo = 65% da receita
        }


def calculate_adjusted_cost(receita: float, event_type: str = "standard") -> float:
    """
    Calcula custo estimado ajustado com base nas regras aprendidas.
    """
    learning = load_learning_rules()
    rules = learning["rules"]
    
    # Base: custo médio histórico (~65% da receita para margem ~35%)
    # Mas nosso histórico mostra margem de 17.7%, então custo ~82%
    base_custo_ratio = 0.823  # 1 - 0.177
    
    custo = receita * base_custo_ratio
    ajustes = []
    economia_total = 0
    
    # Aplicar regras que reduzem custo
    for rule in rules:
        action = rule.get("action", "").lower()
        priority = rule.get("priority", "LOW")
        
        # Regra 1: change_supplier -> economia em bebidas (~15%)
        if "supplier" in action:
            economia = receita * 0.15 * 0.25  # 25% = typical beverages share
            economia_total += economia
            ajustes.append(f"📉 Troca fornecedor: -R$ {economia:,.0f}")
        
        # Regra 2: optimize_team_size -> economia em staff (~10%)
        elif "team" in action:
            economia = receita * 0.10 * 0.22  # 22% = typical staff share
            economia_total += economia
            ajustes.append(f"👥 Otimização equipe: -R$ {economia:,.0f}")
        
        # Regra 3: checklist estoque -> evita custo emergência (~5%)
        elif "estoque" in action:
            economia = receita * 0.05
            economia_total += economia
            ajustes.append(f"📦 Checklist estoque: -R$ {economia:,.0f}")
        
        # Regra 4: revisar preços -> não afeta custo, mas alerta
        elif "preço" in action or "preco" in action:
            ajustes.append(f"⚠️  Preço: abaixo do ideal - revisar!")
    
    custo_ajustado = custo - economia_total
    custo_ajustado = max(custo_ajustado, receita * 0.5)  # floor: 50%
    
    return custo_ajustado, ajustes


def simulate_event(event: Dict) -> Dict:
    """
    Simula um evento aplicando regras aprendidas do sistema.
    """
    receita = event.get("expected_revenue", 0)
    nome = event.get("name", "Sem nome")
    event_type = event.get("type", "standard")
    
    # Calcular custo com ajustes
    custo_estimado, ajustes = calculate_adjusted_cost(receita, event_type)
    
    # Calcular margem
    margem = (receita - custo_estimado) / receita if receita > 0 else 0
    
    # Decisão
    if margem < 0:
        decision = "REJECT"
        icon = "❌"
    elif margem < 0.3:
        decision = "REVIEW"
        icon = "⚠️"
    else:
        decision = "APPROVE"
        icon = "✅"
    
    # Alertas baseados em insights históricos
    alertas = []
    learning = load_learning_rules()
    
    for insight in learning.get("insights", []):
        rec = insight.get("recommendation", "")
        if "bebida" in rec.lower() and margem < 0.35:
            alertas.append("🍺 Cuidado: bebidas consumiram >35% em eventos anteriores")
        if "staff" in rec.lower() and margem < 0.25:
            alertas.append("👥 Alerta: custo de staff foi problema em eventos similares")
    
    return {
        "event": nome,
        "receita": receita,
        "custo_estimado": custo_ajustado,
        "custo_base": receita * 0.823,
        "economia_regras": receita * 0.823 - custo_estimado,
        "margem": margem,
        "margem_pct": margem * 100,
        "decisão": decision,
        "icon": icon,
        "ajustes_aplicados": ajustes,
        "alertas": alertas,
        "recomendacoes": generate_recommendations(decision, margem, ajustes)
    }


def generate_recommendations(decision: str, margin: float, ajustes: List[str]) -> List[str]:
    """Gera recomendações baseadas na decisão."""
    recs = []
    
    if decision == "REJECT":
        recs = [
            "Aumentar preço de venda em 20-30%", 
            "Reduzir escopo do evento",
            "Negociar pacote menor com cliente"
        ]
    elif decision == "REVIEW":
        recs = [
            "Aplicar ajustes sugeridos acima",
            "Cotar fornecedores alternativos antes de confirmar",
            "Revisar necessidade real de cada item"
        ]
        if not ajustes:
            recs.append("⚠️  Nenhuma regra de economia aplicável - margem será apertada")
    else:
        recs = [
            "✅ Evento rentável - pode confirmar",
            "Aplicar ajustes para margem ainda melhor"
        ]
    
    return recs


def simulate_event_simple(event: Dict) -> Dict:
    """
    Versão simples (match com o código do usuário).
    """
    receita = event.get("expected_revenue", event.get("revenue", 0))
    
    # Custo baseado no histórico (margem média 17.7% = custo 82.3%)
    custo_estimado = receita * 0.65  # Projeção otimista com regras aplicadas
    
    margem = (receita - custo_estimado) / receita if receita > 0 else 0
    
    if margem < 0:
        decision = "REJECT"
    elif margem < 0.3:
        decision = "REVIEW"
    else:
        decision = "APPROVE"
    
    return {
        "event": event.get("name", "unknown"),
        "receita": receita,
        "custo_estimado": custo_estimado,
        "margem": margem,
        "decisão": decision
    }


def run_simulation(events: List[Dict]) -> None:
    """
    Executa simulação para múltiplos eventos.
    """
    print("\n" + "=" * 70)
    print("🎛️ ORKESTRA EVENT SIMULATOR")
    print("=" * 70)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"Baseado em: regras aprendidas do Learning Engine")
    print("-" * 70)
    
    results = []
    total_receita = 0
    total_custo_base = 0
    total_custo_ajustado = 0
    
    for i, event in enumerate(events, 1):
        print(f"\n📊 Evento {i}: {event.get('name', 'N/A')}")
        
        # Simular com regras
        result = simulate_event(event)
        results.append(result)
        
        total_receita += result["receita"]
        total_custo_base += result["custo_base"]
        total_custo_ajustado += result["custo_estimado"]
        
        # Print
        print(f"   {result['icon']} Decisão: {result['decisão']}")
        print(f"   💰 Receita esperada: R$ {result['receita']:,.0f}")
        print(f"   💸 Custo estimado: R$ {result['custo_estimado']:,.0f}")
        print(f"      (Base: R$ {result['custo_base']:,.0f})")
        print(f"   📈 Margem: {result['margem_pct']:.1f}%")
        
        if result["economia_regras"] > 0:
            print(f"   💎 Economia c/ regras: R$ {result['economia_regras']:,.0f}")
        
        if result["ajustes_aplicados"]:
            print(f"\n   ⚙️  Regras aplicadas:")
            for ajuste in result["ajustes_aplicados"]:
                print(f"      {ajuste}")
        
        if result["alertas"]:
            print(f"\n   ⚠️  Alertas:")
            for alerta in result["alertas"]:
                print(f"      {alerta}")
        
        print(f"\n   📋 Recomendações:")
        for rec in result["recomendacoes"][:2]:
            print(f"      • {rec}")
    
    # Resumo
    print("\n" + "=" * 70)
    print("📊 RESUMO DA SIMULAÇÃO")
    print("=" * 70)
    
    economia_total = total_custo_base - total_custo_ajustado
    margem_media = (total_receita - total_custo_ajustado) / total_receita if total_receita > 0 else 0
    margem_sem_regras = (total_receita - total_custo_base) / total_receita if total_receita > 0 else 0
    
    print(f"\n   📊 Eventos simulados: {len(events)}")
    print(f"   💰 Receita total: R$ {total_receita:,.0f}")
    print(f"\n   📉 CENÁRIO SEM REGRAS:")
    print(f"      Custo: R$ {total_custo_base:,.0f}")
    print(f"      Margem: {margem_sem_regras*100:.1f}%")
    print(f"\n   📈 CENÁRIO COM REGRAS:")
    print(f"      Custo: R$ {total_custo_ajustado:,.0f}")
    print(f"      Margem: {margem_media*100:.1f}%")
    print(f"\n   💎 GANHO TOTAL:")
    print(f"      Economia: R$ {economia_total:,.0f}")
    print(f"      Aumento de margem: +{(margem_media - margem_sem_regras)*100:.1f}%")
    
    # Decisões
    approved = sum(1 for r in results if r["decisão"] == "APPROVE")
    review = sum(1 for r in results if r["decisão"] == "REVIEW")
    reject = sum(1 for r in results if r["decisão"] == "REJECT")
    
    print(f"\n   ✅ Aprovados: {approved} | ⚠️ Revisar: {review} | ❌ Rejeitados: {reject}")
    
    print("\n" + "=" * 70)
    
    # Salvar resultados
    output = {
        "timestamp": datetime.now().isoformat(),
        "events": results,
        "summary": {
            "total_receita": total_receita,
            "total_custo_base": total_custo_base,
            "total_custo_ajustado": total_custo_ajustado,
            "economia_total": economia_total,
            "margem_media": margem_media,
            "approved": approved,
            "review": review,
            "reject": reject
        }
    }
    
    with open("orkestra/memory/simulation_report.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print("💾 Relatório salvo: orkestra/memory/simulation_report.json")


if __name__ == "__main__":
    # Exemplo de uso
    test_events = [
        {"name": "Casamento Silva", "expected_revenue": 30000, "type": "casamento"},
        {"name": "Formatura Medicina", "expected_revenue": 50000, "type": "formatura"},
        {"name": "Evento Corporativo", "expected_revenue": 20000, "type": "corporativo"},
    ]
    
    run_simulation(test_events)
