# orchestrator.py - Orkestra Autonomous Pipeline
# Pipeline simplificado de execução autônoma

import json
import sys
from pathlib import Path
from datetime import datetime

# Configurar paths
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR.parent))  # Acessar scripts/
sys.path.insert(0, str(BASE_DIR))

# Importar simulador de eventos e sugestão de correção
from orkestra.engine.event_simulator_engine import simulate_event, suggest_fix

# Funções inline para evitar import errors
def evaluate_event(event):
    """Avalia margem do evento."""
    margin = event.get("margin", 0)
    if margin < 0:
        return "REJECT"
    if margin < 0.3:
        return "REVIEW"
    return "APPROVE"


def run_pipeline():
    """
    Executa o pipeline completo do Orkestra.
    """
    print("\n🚀 ORKESTRA AUTONOMOUS PIPELINE")
    print("=" * 60)
    
    # 1. LOAD DATA
    print("\n[1/5] CARREGANDO DADOS...")
    try:
        with open("financial_log.json") as f:
            raw = json.load(f)
        transactions = raw.get("transactions", [])
        
        if not transactions:
            print("❌ Nenhuma transação encontrada")
            return
        
        print(f"✅ {len(transactions)} transações carregadas")
    except FileNotFoundError:
        print("❌ Arquivo financial_log.json não encontrado")
        return
    
    # 1.5 SIMULAÇÃO PRÉ-EVENTO - Usando o engine
    print("\n🔮 SIMULAÇÃO PRÉ-EVENTO")
    print("-" * 40)
    
    event_test = {
        "name": "Formatura Medicina FUTURO",
        "expected_revenue": 900000,
        "people": 300,
        "has_open_bar": True,
        "high_staff": True
    }
    
    sim = simulate_event(event_test)
    
    icon = "✅" if sim["decision"] == "APPROVE" else "⚠️" if sim["decision"] == "REVIEW" else "❌"
    print(f"\n   {icon} {sim['event']}")
    print(f"   💰 Receita Esperada: R$ {sim['receita']:,.0f}")
    print(f"   💸 Custo Estimado: R$ {sim['custo_estimado']:,.0f}")
    print(f"   📊 Margem Projetada: {sim['margem']*100:.1f}%")
    print(f"   🎯 Decisão Simulada: {sim['decision']}")
    print(f"   📈 Cost Ratio: {sim['cost_ratio']:.0%}")
    print(f"      (base: 65% + open_bar: +10% + high_staff: +5%)")
    
    # 💡 SUGESTÃO DE CORREÇÃO
    fix = suggest_fix(event_test, sim)
    if fix.get('status') != "OK":
        print(f"\n   💡 COMO CORRIGIR:")
        print(f"      Status: {fix['status']}")
        print(f"      Gap: {(fix['margem_gap']*100):.1f}%")
        print(f"      📈 Opção 1: Aumentar receita +R$ {fix['increase_revenue_needed']:,.0f}")
        print(f"      📉 Opção 2: Reduzir custos -R$ {fix['reduce_cost_needed']:,.0f}")
        print(f"      🎯 {fix['suggestion']}")
    
    # 2. FINANCIAL ANALYSIS
    print("\n[2/5] ANÁLISE FINANCEIRA...")
    results = simple_financial_analysis(raw)
    print(f"✅ {len(results)} eventos analisados")
    
    # 3. DECISION LOOP
    print("\n[3/5] AVALIAÇÃO DE VIABILIDADE...")
    for event in results:
        decision = evaluate_event(event)
        event["decision"] = decision
        
        icon = "✅" if decision == "APPROVE" else "⚠️" if decision == "REVIEW" else "❌"
        print(f"\n   {icon} {event['event']}")
        print(f"      Receita: R$ {event.get('income', 0):,.0f}")
        print(f"      Custo: R$ {event.get('expense', 0):,.0f}")
        print(f"      Margem: {event.get('margin', 0)*100:.1f}%")
        print(f"      Decisão: {decision}")
    
    # 4. MEMORY SAVE
    print("\n[4/5] SALVANDO NA MEMÓRIA...")
    try:
        sys.path.insert(0, str(BASE_DIR.parent))
        from scripts.memory_manager import memory
        
        for event in results:
            memory.add_decision(
                event=event["event"],
                margin=event.get("margin", 0),
                issue="low_margin" if event.get("margin", 0) < 0.3 else "ok",
                cause="auto_detected",
                action="auto_review",
                result=event["decision"],
                margin_before=event.get("margin", 0),
                notes=f"Pipeline run {datetime.now().strftime('%Y-%m-%d')}" if event.get("margin", 0) < 0.3 else ""
            )
        print("✅ Memória atualizada")
    except Exception as e:
        print(f"⚠️  Erro ao salvar memória: {e}")
    
    # 5. PROCURAMENTO SIMULATION
    print("\n[5/5] PREVISÃO DE COMPRAS...")
    print("   📦 Simulação de procurement")
    print("      - Analisando eventos futuros...")
    print("      - Consolidando demanda...")
    print("      - Verificando estoque...")
    print("   ⚠️  Módulo procurement não implementado (stub)")
    
    # 6. RESUMO
    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETO")
    print("=" * 60)
    
    total_revenue = sum(e.get("income", 0) for e in results)
    total_cost = sum(e.get("expense", 0) for e in results)
    avg_margin = sum(e.get("margin", 0) for e in results) / len(results) if results else 0
    
    print(f"\n📊 RESUMO:")
    print(f"   Eventos: {len(results)}")
    print(f"   ✅ Aprovados: {sum(1 for e in results if e.get('decision') == 'APPROVE')}")
    print(f"   ⚠️  Revisar: {sum(1 for e in results if e.get('decision') == 'REVIEW')}")
    print(f"   ❌ Rejeitados: {sum(1 for e in results if e.get('decision') == 'REJECT')}")
    print(f"   💰 Receita Total: R$ {total_revenue:,.0f}")
    print(f"   📉 Custo Total: R$ {total_cost:,.0f}")
    print(f"   📊 Margem Média: {avg_margin*100:.1f}%")
    print(f"   💵 Lucro Total: R$ {total_revenue - total_cost:,.0f}")
    
    print("\n" + "=" * 60)
    
    # Salvar relatório
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "events_analyzed": len(results),
            "approved": sum(1 for e in results if e.get('decision') == "APPROVE"),
            "review": sum(1 for e in results if e.get('decision') == "REVIEW"),
            "rejected": sum(1 for e in results if e.get('decision') == "REJECT"),
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "avg_margin": avg_margin,
            "profit": total_revenue - total_cost
        },
        "events": results,
        "pre_event_simulation": sim  # Adicionar simulação futura
    }
    
    # Salvar em orkestra/memory/pipeline_report.json
    from pathlib import Path
    mem_dir = Path("orkestra/memory")
    mem_dir.mkdir(exist_ok=True)
    
    with open(mem_dir / "pipeline_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"💾 Relatório salvo: {mem_dir / 'pipeline_report.json'}")


def simple_financial_analysis(data: dict) -> list:
    """
    Análise financeira simplificada.
    """
    transactions = data.get("transactions", [])
    events = {}
    
    for t in transactions:
        event_name = t.get("event", "unknown")
        if event_name not in events:
            events[event_name] = {"income": 0, "expense": 0, "event": event_name}
        
        if t.get("type") == "income":
            events[event_name]["income"] += t.get("value", 0)
        else:
            events[event_name]["expense"] += t.get("value", 0)
    
    results = []
    for name, data in events.items():
        revenue = data["income"]
        cost = data["expense"]
        margin = (revenue - cost) / revenue if revenue > 0 else 0
        
        results.append({
            "event": name,
            "income": revenue,
            "expense": cost,
            "margin": margin
        })
    
    return results


if __name__ == "__main__":
    run_pipeline()
