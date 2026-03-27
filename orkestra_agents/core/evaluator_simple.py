# evaluator_simple.py - Avaliador Simplificado de Eventos
# Versão minimalista do Event Profitability Agent

def evaluate_event(event):
    """
    Avalia um evento baseado na margem projetada.
    
    Args:
        event: dict com chave 'margin' (float entre 0 e 1)
    
    Returns:
        str: "REJECT", "REVIEW", ou "APPROVE"
    """
    margin = event.get("margin", 0)
    
    if margin < 0:
        return "REJECT"
    
    if margin < 0.3:
        return "REVIEW"
    
    return "APPROVE"


def evaluate_event_detailed(event):
    """
    Versão detalhada com justificativa.
    """
    margin = event.get("margin", 0)
    complexity = event.get("complexity", "medium")
    capacity = event.get("capacity", 0)
    
    result = {
        "decision": "",
        "margin": margin,
        "rationale": "",
        "recommendations": []
    }
    
    # Decisão base
    if margin < 0:
        result["decision"] = "REJECT"
        result["rationale"] = "Margem negativa - evento gerará prejuízo"
        result["recommendations"] = [
            "Aumentar preço de venda",
            "Reduzir escopo do evento",
            "Negociar custos com fornecedores"
        ]
    
    elif margin < 0.15:
        result["decision"] = "REJECT"
        result["rationale"] = "Margem crítica (< 15%) - risco operacional muito alto"
        result["recommendations"] = [
            "Reprojetar oferta",
            "Buscar economias de escala",
            "Aumentar ticket médio"
        ]
    
    elif margin < 0.3:
        result["decision"] = "REVIEW"
        result["rationale"] = "Margem abaixo do ideal (30%)"
        
        if complexity == "high":
            result["rationale"] += " + complexidade alta"
            result["recommendations"].append("Reavaliar complexidade operacional")
        
        if capacity > 500:
            result["rationale"] += " + alto volume"
            result["recommendations"].append("Verificar capacidade de atendimento")
        
        result["recommendations"].extend([
            "Revisar estrutura de custos",
            "Cotar fornecedores alternativos",
            "Ajustar proporção de categorias"
        ])
    
    elif margin < 0.4:
        result["decision"] = "APPROVE"
        result["rationale"] = "Margem saudável"
        result["recommendations"] = [
            "Monitorar custos durante execução",
            "Manter padrão"
        ]
    
    else:
        result["decision"] = "APPROVE"
        result["rationale"] = "Margem excelente"
        result["recommendations"] = [
            "Usar como benchmark para eventos similares",
            "Replicar estrutura de custos"
        ]
    
    # Alerta especial para complexidade
    if complexity == "high" and margin < 0.35:
        result["warning"] = "Evento de alta complexidade com margem apertada"
    
    return result


# Teste rápido
if __name__ == "__main__":
    test_events = [
        {"name": "Festa Pequena", "margin": 0.45, "complexity": "low", "capacity": 50},
        {"name": "Casamento Médio", "margin": 0.25, "complexity": "medium", "capacity": 150},
        {"name": "Formatura Grande", "margin": 0.15, "complexity": "high", "capacity": 500},
        {"name": "Evento Perda", "margin": -0.05, "complexity": "high", "capacity": 300},
    ]
    
    print("=" * 60)
    print("🎛️ ORKESTRA EVENT EVALUATOR (SIMPLE)")
    print("=" * 60)
    
    for ev in test_events:
        decision = evaluate_event(ev)
        detailed = evaluate_event_detailed(ev)
        
        icon = "❌" if decision == "REJECT" else "⚠️" if decision == "REVIEW" else "✅"
        print(f"\n{icon} {ev['name']}")
        print(f"   Margem: {ev['margin']:.0%}")
        print(f"   Decisão: {decision}")
        print(f"   Racional: {detailed['rationale']}")
        
        if detailed.get('recommendations'):
            print(f"   Sugestões: {', '.join(detailed['recommendations'][:2])}")
