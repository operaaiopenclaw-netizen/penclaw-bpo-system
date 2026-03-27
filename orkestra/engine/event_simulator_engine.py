import json

TARGET_MARGIN = 0.30

def simulate_event(event):

    receita = event["expected_revenue"]
    pessoas = event.get("people", 100)

    # BASEADO NO TEU HISTÓRICO REAL
    custo_base_ratio = 0.65

    # AJUSTES DINÂMICOS
    ajustes = 0

    if event.get("has_open_bar"):
        ajustes += 0.10  # bebidas explodem custo

    if event.get("high_staff"):
        ajustes += 0.05

    custo_ratio_final = custo_base_ratio + ajustes

    custo_estimado = receita * custo_ratio_final
    margem = (receita - custo_estimado) / receita

    # DECISÃO
    if margem < 0:
        decision = "REJECT"
    elif margem < TARGET_MARGIN:
        decision = "REVIEW"
    else:
        decision = "APPROVE"

    return {
        "event": event["name"],
        "receita": receita,
        "custo_estimado": round(custo_estimado, 2),
        "margem": round(margem, 4),
        "decision": decision,
        "cost_ratio": custo_ratio_final
    }


def price_per_person(pricing, people):
    """
    Calcula preço por pessoa com base em diferentes estratégias de pricing.
    """
    return {
        "min_pax": round(pricing["preco_minimo"] / people, 2),
        "target_pax": round(pricing["preco_target"] / people, 2),
        "aggressive_pax": round(pricing["preco_agressivo"] / people, 2)
    }


def suggest_fix(event, sim):
    """
    Sugere correção para evento com margem abaixo do target.
    Como corrigir: aumento de preço ou redução de custo.
    """
    margem = sim["margem"]
    receita = sim["receita"]
    custo = sim["custo_estimado"]

    target = TARGET_MARGIN  # 0.30

    if margem >= target:
        return {
            "status": "OK",
            "action": "NO_ACTION",
            "suggestion": "Margem adequada - nenhuma ação necessária"
        }

    # Quanto precisa melhorar
    margem_gap = target - margem

    # Ajuste de preço necessário
    novo_preco = receita / (1 - target)
    aumento = novo_preco - receita

    # Alternativa: redução de custo
    novo_custo = receita * (1 - target)
    reducao_custo = custo - novo_custo

    return {
        "status": "ADJUST_REQUIRED",
        "action": "INCREASE_PRICE_OR_REDUCE_COST",
        "margem_atual": round(margem, 4),
        "margem_target": target,
        "margem_gap": round(margem_gap, 4),
        "increase_revenue_needed": round(aumento, 2),
        "reduce_cost_needed": round(reducao_custo, 2),
        "suggestion": f"Aumentar receita em R$ {round(aumento,2)} ou reduzir custos em R$ {round(reducao_custo,2)}",
        "new_target_price": round(novo_preco, 2)
    }


# Teste rápido
if __name__ == "__main__":
    test_events = [
        {"name": "Casamento Padrão", "expected_revenue": 30000, "people": 100},
        {"name": "Formatura Open Bar", "expected_revenue": 50000, "people": 200, "has_open_bar": True},
        {"name": "Corporativo Staff Alto", "expected_revenue": 40000, "people": 150, "high_staff": True},
        {"name": "Festa Completa", "expected_revenue": 60000, "people": 250, "has_open_bar": True, "high_staff": True},
    ]
    
    print("=" * 60)
    print("🎛️ ORKESTRA EVENT SIMULATOR ENGINE")
    print("=" * 60)
    print(f"\nTarget Margin: {TARGET_MARGIN*100}%")
    print("-" * 60)
    
    for event in test_events:
        # Simular evento
        result = simulate_event(event)
        
        # Sugerir correção se necessário
        fix = suggest_fix(event, result)
        
        icon = "✅" if result["decision"] == "APPROVE" else "⚠️" if result["decision"] == "REVIEW" else "❌"
        
        print(f"\n{icon} {result['event']}")
        print(f"   Receita: R$ {result['receita']:,.0f}")
        print(f"   Custo Est.: R$ {result['custo_estimado']:,.0f}")
        print(f"   Margem: {result['margem']*100:.1f}%")
        print(f"   Decisão: {result['decision']}")
        print(f"   Cost Ratio: {result['cost_ratio']:.0%}")
        
        # 👥 PREÇO POR PESSOA
        pricing = {
            "preco_minimo": result['receita'] * 0.90,  # 10% abaixo
            "preco_target": result['receita'],         # preço atual
            "preco_agressivo": result['receita'] * 1.15  # 15% acima
        }
        pax_price = price_per_person(pricing, event["people"])
        
        print(f"\n   👥 PREÇO POR PESSOA:")
        print(f"      Mínimo: R$ {pax_price['min_pax']:,.2f}")
        print(f"      Target: R$ {pax_price['target_pax']:,.2f}")
        print(f"      Agressivo: R$ {pax_price['aggressive_pax']:,.2f}")
        
        # Mostrar sugestão de correção SE margem abaixo do target
        if fix['status'] != "OK":
            print(f"\n   💡 COMO CORRIGIR:")
            print(f"      Status: {fix['status']}")
            print(f"      Gap de margem: {(fix['margem_gap']*100):.1f}%")
            print(f"\n      📈 OPÇÃO 1 - Aumentar Preço:")
            print(f"         Novo preço: R$ {fix['new_target_price']:,.0f}")
            print(f"         Aumento necessário: +R$ {fix['increase_revenue_needed']:,.0f}")
            print(f"         Novo preço/pax: R$ {fix['new_target_price']/event['people']:,.2f}")
            print(f"\n      📉 OPÇÃO 2 - Reduzir Custos:")
            print(f"         Redução necessária: -R$ {fix['reduce_cost_needed']:,.0f}")
            print(f"\n      🎯 Sugestão: {fix['suggestion']}")
