#!/usr/bin/env python3
"""
DECISION ENGINE OPERATIONAL
Gera ações práticas com base na DRE, performance e desperdício

REGRAS:
- margin < 10% → reduce_cost, review_menu
- desperdício > 8% → adjust_recipe, reduce_production
- CMV alto → change_supplier
- Prejuízo → HIGH
- Baixa margem → MEDIUM
- Otimização → LOW
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class Decision:
    event_id: str
    company: str
    date_event: str
    gross_margin: Optional[float]
    net_margin: Optional[float]
    waste_pct: Optional[float]
    actions: List[str]
    priority: str  # HIGH, MEDIUM, LOW
    rationale: str
    status: str  # "active" | "resolved"
    timestamp: str


def load_json(filename: str) -> Dict:
    filepath = DATA_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_json(filename: str, data: Dict):
    filepath = DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_csv(filename: str) -> List[Dict]:
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def parse_float(val):
    try:
        return float(val) if val else 0
    except:
        return 0


def load_dre() -> List[Dict]:
    """Carrega dados da DRE"""
    dre_path = OUTPUT_DIR / "dre_events.csv"
    if dre_path.exists():
        return load_csv("dre_events.csv")
    
    # Fallback: construir de events + cmv + fixed
    events = load_csv("events_consolidated.csv")
    if not events:
        return []
    
    cmv_data = load_json("cmv_log.json")
    fixed_allocs = load_json("fixed_allocations.json")
    
    records = []
    for e in events:
        event_id = e.get("event_id")
        revenue = parse_float(e.get("revenue_total"))
        
        cmv = cmv_data.get("eventos", {}).get(event_id, {}).get("cmv_total")
        fixed = None
        for key, alloc in fixed_allocs.get("allocations", {}).items():
            if alloc.get("event_id") == event_id:
                fixed = alloc.get("fixed_allocated")
                break
        
        gross_profit = revenue - cmv if cmv else None
        gross_margin = (gross_profit / revenue * 100) if gross_profit and revenue else None
        
        net_profit = (gross_profit - fixed) if gross_profit and fixed else None
        net_margin = (net_profit / revenue * 100) if net_profit and revenue else None
        
        records.append({
            "event_id": event_id,
            "company": e.get("company", ""),
            "date_event": e.get("date_event", ""),
            "revenue": revenue,
            "cmv": cmv,
            "gross_profit": gross_profit,
            "gross_margin": gross_margin,
            "fixed_allocated": fixed,
            "net_profit": net_profit,
            "net_margin": net_margin
        })
    
    return records


def load_waste() -> Dict[str, float]:
    """Carrega percentual de desperdício por evento"""
    waste = load_json("waste_log.json")
    waste_by_event = {}
    
    for event_id, data in waste.get("registros", {}).items():
        pct = data.get("totais_desperdicio", {}).get("percentual_desperdicio")
        if pct is not None:
            waste_by_event[event_id] = pct
    
    return waste_by_event


def determine_actions(dre: Dict, waste_pct: Optional[float]) -> Tuple[List[str], str, str]:
    """
    Determina ações necessárias e prioridade
    
    Retorna: (actions, priority, rationale)
    """
    actions = []
    priority = "LOW"
    rationale_parts = []
    
    gross_margin = dre.get("gross_margin")
    net_margin = dre.get("net_margin")
    cmv = dre.get("cmv")
    revenue = dre.get("revenue", 0)
    event_id = dre.get("event_id", "")
    
    # === PREJUÍZO (CRITICAL) ===
    if gross_margin is not None and gross_margin < 0:
        actions.append("urgent_review_pricing")
        actions.append("negotiate_supplier_immediately")
        priority = "HIGH"
        rationale_parts.append(f"PREJUÍZO: margem bruta {gross_margin:.1f}% negativa")
        return actions, priority, " | ".join(rationale_parts)
    
    # === MARGEM BAIXA ===
    if gross_margin is not None and gross_margin < 10:
        actions.append("reduce_cost")
        actions.append("review_menu")
        priority = "MEDIUM"
        rationale_parts.append(f"Margem baixa: {gross_margin:.1f}% (mínimo 10%)")
    
    # === DESPERDÍCIO ALTO ===
    if waste_pct is not None and waste_pct > 8:
        actions.append("adjust_recipe")
        actions.append("reduce_production")
        if priority == "LOW":
            priority = "MEDIUM"
        rationale_parts.append(f"Desperdício alto: {waste_pct:.1f}% (limite 8%)")
    
    # === CMV ALTO (acima de 70% da receita) ===
    if cmv and revenue > 0:
        cmv_rate = cmv / revenue * 100
        if cmv_rate > 70:
            actions.append("change_supplier")
            actions.append("negotiate_prices")
            if priority == "LOW":
                priority = "MEDIUM"
            rationale_parts.append(f"CMV alto: {cmv_rate:.1f}% da receita")
    
    # === MARGEM LÍQUIDA NEGATIVA ===
    if net_margin is not None and net_margin < 0:
        actions.append("review_fixed_costs")
        actions.append("increase_volume")
        priority = "HIGH"
        rationale_parts.append(f"Prejuízo líquido: {net_margin:.1f}%")
    
    # Se nada crítico mas margem < 20%
    if gross_margin is not None and gross_margin < 20 and priority == "LOW":
        actions.append("optimize_processes")
        rationale_parts.append(f"Margem em acompanhamento: {gross_margin:.1f}%")
    
    # Se tudo ok
    if not actions:
        actions.append("maintain_standards")
        rationale_parts.append(f"Performance adequada: margem {gross_margin:.1f}%")
    
    return actions, priority, " | ".join(rationale_parts)


def generate_decisions() -> List[Decision]:
    """Gera decisões para todos os eventos"""
    
    print("\n🎯 Gerando decisões operacionais...")
    
    dre_data = load_dre()
    if not dre_data:
        print("❌ Nenhum dado DRE encontrado")
        return []
    
    waste_data = load_waste()
    
    decisions = []
    
    for dre in dre_data:
        event_id = dre.get("event_id", "")
        waste_pct = waste_data.get(event_id)
        
        actions, priority, rationale = determine_actions(dre, waste_pct)
        
        decision = Decision(
            event_id=event_id,
            company=dre.get("company", ""),
            date_event=dre.get("date_event", ""),
            gross_margin=dre.get("gross_margin"),
            net_margin=dre.get("net_margin"),
            waste_pct=waste_pct,
            actions=actions,
            priority=priority,
            rationale=rationale,
            status="active",
            timestamp=datetime.now().isoformat()
        )
        
        decisions.append(decision)
    
    return decisions


def save_decisions(decisions: List[Decision]):
    """Salva decisões em JSON"""
    
    output = {
        "_meta": {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_decisions": len(decisions),
            "breakdown": {
                "HIGH": sum(1 for d in decisions if d.priority == "HIGH"),
                "MEDIUM": sum(1 for d in decisions if d.priority == "MEDIUM"),
                "LOW": sum(1 for d in decisions if d.priority == "LOW")
            }
        },
        "decisions": [asdict(d) for d in decisions]
    }
    
    save_json("decisions.json", output)
    print(f"\n✅ Decisions salvo em: kitchen_data/decisions.json")
    
    return output


def generate_actions_csv(decisions: List[Decision]):
    """Gera CSV de ações"""
    
    headers = [
        "event_id", "company", "gross_margin", "net_margin", "waste_pct",
        "priority", "actions", "rationale", "status", "timestamp"
    ]
    
    data = []
    for d in decisions:
        row = {
            "event_id": d.event_id,
            "company": d.company,
            "gross_margin": round(d.gross_margin, 2) if d.gross_margin else "",
            "net_margin": round(d.net_margin, 2) if d.net_margin else "",
            "waste_pct": round(d.waste_pct, 2) if d.waste_pct else "",
            "priority": d.priority,
            "actions": "; ".join(d.actions),
            "rationale": d.rationale,
            "status": d.status,
            "timestamp": d.timestamp
        }
        data.append(row)
    
    # Ordenar por prioridade
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    data.sort(key=lambda x: priority_order.get(x["priority"], 3))
    
    filepath = OUTPUT_DIR / "operational_actions.csv"
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ Ações salvas em: output/operational_actions.csv")


def print_action_report(decisions: List[Decision]):
    """Imprime relatório de ações"""
    
    emoji_priority = {
        "HIGH": "🚨 HIGH",
        "MEDIUM": "⚠️  MEDIUM",
        "LOW": "ℹ️  LOW"
    }
    
    print("\n" + "="*90)
    print("🎯 DECISION ENGINE OPERATIONAL REPORT")
    print("="*90)
    
    # Separar por prioridade
    high = [d for d in decisions if d.priority == "HIGH"]
    medium = [d for d in decisions if d.priority == "MEDIUM"]
    low = [d for d in decisions if d.priority == "LOW"]
    
    # HIGH
    if high:
        print(f"\n{'─'*90}")
        print("🚨 AÇÕES PRIORITÁRIAS - URGENTE")
        print(f"{'─'*90}")
        for d in high:
            print(f"\n   {d.event_id:<12} | {d.company:<8}")
            print(f"      Ações: {', '.join(d.actions)}")
            print(f"      Motivo: {d.rationale}")
    
    # MEDIUM
    if medium:
        print(f"\n{'─'*90}")
        print("⚠️  AÇÕES MÉDIAS - REVISAR")
        print(f"{'─'*90}")
        for d in medium:
            print(f"\n   {d.event_id:<12} | {d.company:<8}")
            print(f"      Ações: {', '.join(d.actions)}")
            print(f"      Motivo: {d.rationale}")
    
    # LOW
    if low:
        print(f"\n{'─'*90}")
        print("ℹ️  AÇÕES DE OTIMIZAÇÃO - MONITORAR")
        print(f"{'─'*90}")
        for d in low:
            print(f"\n   {d.event_id:<12} | {d.company:<8}")
            print(f"      Ações: {', '.join(d.actions)}")
            if d.rationale:
                print(f"      Nota: {d.rationale}")
    
    # Resumo
    print(f"\n{'='*90}")
    print("RESUMO DE AÇÕES")
    print(f"{'='*90}")
    print(f"  🚨 HIGH:   {len(high):>3} decisões")
    print(f"  ⚠️  MEDIUM: {len(medium):>3} decisões")
    print(f"  ℹ️  LOW:    {len(low):>3} decisões")
    print(f"  ─────────────────")
    print(f"  TOTAL:    {len(decisions):>3} decisões")
    print("="*90)


def main():
    """Função principal"""
    
    print("🎛️ DECISION ENGINE OPERATIONAL - Orkestra Finance Brain")
    print("="*90)
    
    # Gerar decisões
    decisions = generate_decisions()
    
    if not decisions:
        print("\n❌ Nenhuma decisão gerada")
        return
    
    # Salvar
    save_decisions(decisions)
    generate_actions_csv(decisions)
    print_action_report(decisions)
    
    print("\n✅ Decision Engine completado!")


if __name__ == "__main__":
    main()
