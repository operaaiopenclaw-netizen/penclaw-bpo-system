#!/usr/bin/env python3
"""
AUTO ACTION ENGINE - CONTROLLED
Executa ações automaticamente sob regras controladas

PERMISSÕES AUTO:
- ✅ ajuste de quantidade de compra
- ✅ alerta de margem baixa
- ✅ alerta de desperdício

NÃO EXECUTAR (sugestão apenas):
- ❌ mudança de preço
- ❌ alteração de receita
- ❌ troca de fornecedor crítica

SEGURANÇA:
- Sempre rastreabilidade
- Log em actions_log.json
- Rollback possível
"""

import json
import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class ActionType(Enum):
    ADJUST_QUANTITY = "adjust_quantity"      # ✅ Auto permitido
    ALERT_MARGIN = "alert_margin"           # ✅ Auto permitido
    ALERT_WASTE = "alert_waste"             # ✅ Auto permitido
    ALERT_STOCKOUT = "alert_stockout"       # ✅ Auto permitido
    
    SUGGEST_SUPPLIER = "suggest_supplier"   # ❌ Só sugestão
    REVIEW_PRICING = "review_pricing"       # ❌ Só sugestão
    CHANGE_RECIPE = "change_recipe"         # ❌ Só sugestão


class ActionStatus(Enum):
    PENDING = "pending"
    AUTO_EXECUTED = "auto_executed"
    MANUAL_REQUIRED = "manual_required"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


@dataclass
class Action:
    action_id: str
    rollback_id: str  # Para reversão
    action_type: str
    status: str
    auto_permitted: bool
    target_entity: str  # item_id, event_id, etc
    target_name: str
    current_value: Optional[float]
    proposed_value: Optional[float]
    reason: str
    priority: str
    trace_mode: str
    timestamp: str
    executed_at: Optional[str]
    rolled_back_at: Optional[str]
    rollback_reason: Optional[str]


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
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        filepath = DATA_DIR / filename
    if not filepath.exists():
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def log_action(action: Action):
    """Registra ação em actions_log.json"""
    actions_log = load_json("actions_log.json")
    
    if "actions" not in actions_log:
        actions_log["actions"] = []
    
    actions_log["actions"].append(asdict(action))
    
    actions_log["_meta"] = {
        "last_updated": datetime.now().isoformat(),
        "total_actions": len(actions_log["actions"])
    }
    
    save_json("actions_log.json", actions_log)


def log_error(error_type: str, severity: str, entity: Optional[str], 
              description: str, source: str = "auto_action"):
    """Registra erro em errors.json"""
    errors = load_json("errors.json")
    
    if "errors" not in errors:
        errors["errors"] = []
    
    error_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": error_type,
        "severity": severity,
        "event_id": entity,
        "description": description,
        "source": source
    }
    
    errors["errors"].append(error_entry)
    errors["_meta"]["total_errors"] = len(errors["errors"])
    
    save_json("errors.json", errors)


def generate_rollback_id() -> str:
    """Gera ID único para rollback"""
    return f"RB-{uuid.uuid4().hex[:8].upper()}"


def is_auto_permitted(action_type: str) -> bool:
    """Verifica se ação pode ser executada automaticamente"""
    permitted = [
        ActionType.ADJUST_QUANTITY.value,
        ActionType.ALERT_MARGIN.value,
        ActionType.ALERT_WASTE.value,
        ActionType.ALERT_STOCKOUT.value
    ]
    return action_type in permitted


def load_procurement_suggestions() -> List[Dict]:
    """Carrega sugestões de compra"""
    proc_json = DATA_DIR / "procurement_suggestions.json"
    if proc_json.exists():
        data = load_json("procurement_suggestions.json")
        return data.get("suggestions", [])
    
    # Fallback CSV
    return load_csv("procurement_suggestions.csv")


def load_margin_validation() -> List[Dict]:
    """Carrega validações de margem"""
    data = load_json("decisions.json")
    if data and data.get("decisions"):
        return data.get("decisions", [])
    
    return load_csv("margin_validation.csv")


def load_waste_data() -> List[Dict]:
    """Carrega dados de desperdício"""
    waste = load_json("waste_log.json")
    records = []
    
    for event_id, data in waste.get("registros", {}).items():
        desp = data.get("totais_desperdicio", {})
        if desp.get("percentual_desperdicio"):
            records.append({
                "event_id": event_id,
                "waste_pct": desp.get("percentual_desperdicio"),
                "waste_total": desp.get("custo_total_perdido", 0),
                "status": desp.get("status", "")
            })
    
    return records


def process_procurement_actions(suggestions: List[Dict]) -> List[Action]:
    """Processa sugestões de compra em ações"""
    actions = []
    
    for sug in suggestions:
        sugg_type = sug.get("suggestion_type", "")
        priority = sug.get("priority", "LOW")
        item_id = sug.get("item_id", "")
        item_name = sug.get("item_name", "")
        
        # Classificar tipo de ação
        action_type = None
        auto_permitted = False
        proposed_value = None
        
        if sugg_type == "prevent_stockout":
            # ✅ AUTO: Alerta de estoque
            action_type = ActionType.ALERT_STOCKOUT.value
            auto_permitted = True
            proposed_value = None
            
        elif sugg_type == "adjust_volume":
            # ✅ AUTO: Ajustar quantidade
            action_type = ActionType.ADJUST_QUANTITY.value
            auto_permitted = True
            # Sugerir quantidade com base em consumo
            monthly = float(sug.get("monthly_consumption", 0) or 0)
            if monthly > 0:
                proposed_value = round(monthly * 1.2, 2)  # +20% segurança
            
        elif sugg_type == "change_supplier":
            # ❌ MANUAL: Troca fornecedor é crítica
            action_type = ActionType.SUGGEST_SUPPLIER.value
            auto_permitted = False
            
        elif sugg_type == "optimize_price":
            # ❌ MANUAL: Preço precisa negociação humana
            action_type = ActionType.REVIEW_PRICING.value
            auto_permitted = False
        
        if action_type:
            action = Action(
                action_id=f"ACT-{uuid.uuid4().hex[:8].upper()}",
                rollback_id=generate_rollback_id(),
                action_type=action_type,
                status=ActionStatus.AUTO_EXECUTED.value if auto_permitted else ActionStatus.MANUAL_REQUIRED.value,
                auto_permitted=auto_permitted,
                target_entity=item_id,
                target_name=item_name,
                current_value=float(sug.get("current_avg_cost", 0)) if sug.get("current_avg_cost") else None,
                proposed_value=proposed_value,
                reason=sug.get("reason", ""),
                priority=priority,
                trace_mode="direct" if auto_permitted else "inferred",
                timestamp=datetime.now().isoformat(),
                executed_at=datetime.now().isoformat() if auto_permitted else None,
                rolled_back_at=None,
                rollback_reason=None
            )
            
            actions.append(action)
            log_action(action)
            
            if auto_permitted:
                print(f"   ✅ AUTO: {action_type} | {item_name} | Prioridade: {priority}")
            else:
                print(f"   👤 MANUAL: {action_type} | {item_name} | Aguardando aprovação")
    
    return actions


def process_margin_actions(validations: List[Dict]) -> List[Action]:
    """Processa validações de margem em ações"""
    actions = []
    
    for val in validations:
        status = val.get("status", "")
        event_id = val.get("event_id", "")
        company = val.get("company", "")
        gross_margin = val.get("gross_margin")
        
        if status in ["REJECT", "CRITICAL"] and gross_margin is not None:
            # ⚠️ Margem baixa → Alerta auto
            action = Action(
                action_id=f"ACT-{uuid.uuid4().hex[:8].upper()}",
                rollback_id=generate_rollback_id(),
                action_type=ActionType.ALERT_MARGIN.value,
                status=ActionStatus.AUTO_EXECUTED.value,
                auto_permitted=True,
                target_entity=event_id,
                target_name=f"{company} - {event_id}",
                current_value=float(gross_margin) if gross_margin else None,
                proposed_value=20.0,  # Meta: 20%
                reason=f"Margem {gross_margin:.1f}% abaixo do necessário" if gross_margin else "Margem crítica",
                priority="HIGH" if status == "CRITICAL" else "MEDIUM",
                trace_mode="direct",
                timestamp=datetime.now().isoformat(),
                executed_at=datetime.now().isoformat(),
                rolled_back_at=None,
                rollback_reason=None
            )
            
            actions.append(action)
            log_action(action)
            
            emoji = "🚨" if status == "CRITICAL" else "🔴"
            print(f"   {emoji} AUTO: ALERT_MARGIN | {event_id} | Margem: {gross_margin:.1f}%")
    
    return actions


def process_waste_actions(waste_data: List[Dict]) -> List[Action]:
    """Processa dados de desperdício em ações"""
    actions = []
    
    for waste in waste_data:
        event_id = waste.get("event_id", "")
        waste_pct = waste.get("waste_pct", 0)
        status = waste.get("status", "")
        
        if status in ["atencao", "critico"] or (waste_pct and waste_pct > 8):
            # ⚠️ Desperdício alto → Alerta auto
            action = Action(
                action_id=f"ACT-{uuid.uuid4().hex[:8].upper()}",
                rollback_id=generate_rollback_id(),
                action_type=ActionType.ALERT_WASTE.value,
                status=ActionStatus.AUTO_EXECUTED.value,
                auto_permitted=True,
                target_entity=event_id,
                target_name=event_id,
                current_value=float(waste_pct) if waste_pct else None,
                proposed_value=5.0,  # Meta: 5%
                reason=f"Desperdício {waste_pct:.1f}% acima do limite de 8%",
                priority="HIGH" if status == "critico" else "MEDIUM",
                trace_mode="direct",
                timestamp=datetime.now().isoformat(),
                executed_at=datetime.now().isoformat(),
                rolled_back_at=None,
                rollback_reason=None
            )
            
            actions.append(action)
            log_action(action)
            
            emoji = "🚨" if status == "critico" else "⚠️"
            print(f"   {emoji} AUTO: ALERT_WASTE | {event_id} | Desperdício: {waste_pct:.1f}%")
    
    return actions


def generate_actions_report(actions: List[Action]):
    """Gera relatório de ações executadas"""
    
    print("\n" + "="*90)
    print("⚙️  AUTO ACTION EXECUTION REPORT")
    print("="*90)
    
    auto = [a for a in actions if a.status == ActionStatus.AUTO_EXECUTED.value]
    manual = [a for a in actions if a.status == ActionStatus.MANUAL_REQUIRED.value]
    
    # Auto Executadas
    if auto:
        print(f"\n{'─'*90}")
        print(f"✅ AÇÕES EXECUTADAS AUTOMATICAMENTE ({len(auto)})")
        print(f"{'─'*90}")
        
        for a in auto:
            emoji = {
                ActionType.ADJUST_QUANTITY.value: "📦",
                ActionType.ALERT_MARGIN.value: "📊",
                ActionType.ALERT_WASTE.value: "🗑️",
                ActionType.ALERT_STOCKOUT.value: "🚨"
            }.get(a.action_type, "⚙️")
            
            print(f"\n   {emoji} {a.action_id}")
            print(f"      Tipo: {a.action_type}")
            print(f"      Alvo: {a.target_name}")
            print(f"      Motivo: {a.reason[:60]}...")
            if a.current_value and a.proposed_value:
                print(f"      Valores: {a.current_value} → {a.proposed_value}")
            print(f"      Rollback ID: {a.rollback_id}")
    
    # Manuais
    if manual:
        print(f"\n{'─'*90}")
        print(f"👤 AÇÕES QUE REQUEREM APROVAÇÃO MANUAL ({len(manual)})")
        print(f"{'─'*90}")
        
        for a in manual:
            print(f"\n   ⚠️  {a.action_id}")
            print(f"      Tipo: {a.action_type}")
            print(f"      Alvo: {a.target_name}")
            print(f"      Motivo: {a.reason}")
            print(f"      Razão manual: Ação crítica - requer decisão humana")
    
    # Resumo
    print(f"\n{'='*90}")
    print("RESUMO DE AÇÕES")
    print(f"{'='*90}")
    print(f"  ✅ Auto-executadas: {len(auto)}")
    print(f"  👤 Manuais pendentes: {len(manual)}")
    print(f"  Total: {len(actions)}")
    print(f"{'='*90}


def generate_actions_csv(actions: List[Action]):
    """Gera CSV de ações"""
    
    headers = [
        "action_id", "rollback_id", "action_type", "status", "auto_permitted",
        "target_entity", "target_name", "current_value", "proposed_value",
        "reason", "priority", "trace_mode", "timestamp", "executed_at"
    ]
    
    data = []
    for a in actions:
        row = {
            "action_id": a.action_id,
            "rollback_id": a.rollback_id,
            "action_type": a.action_type,
            "status": a.status,
            "auto_permitted": str(a.auto_permitted),
            "target_entity": a.target_entity,
            "target_name": a.target_name,
            "current_value": a.current_value if a.current_value else "",
            "proposed_value": a.proposed_value if a.proposed_value else "",
            "reason": a.reason,
            "priority": a.priority,
            "trace_mode": a.trace_mode,
            "timestamp": a.timestamp,
            "executed_at": a.executed_at if a.executed_at else ""
        }
        data.append(row)
    
    # Ordenar por prioridade
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    data.sort(key=lambda x: priority_order.get(x["priority"], 3))
    
    filepath = OUTPUT_DIR / "executed_actions.csv"
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ Ações salvas em: output/executed_actions.csv")


def main():
    """Função principal"""
    
    print("🎛️ AUTO ACTION ENGINE - Orkestra Finance Brain")
    print("="*90)
    print("\n⚙️  Executando ações controladas automaticamente...")
    print("   ✅ Permitido: ajuste quantidade, alertas")
    print("   ❌ Manual: mudança preço, receita, fornecedor")
    
    # Carregar dados
    print("\n📥 Carregando sugestões e validações...")
    
    procurement = load_procurement_suggestions()
    margins = load_margin_validation()
    waste = load_waste_data()
    
    all_actions = []
    
    # Processar cada fonte
    if procurement:
        print(f"\n🛒 Processando {len(procurement)} sugestões de compra...")
        actions = process_procurement_actions(procurement)
        all_actions.extend(actions)
    
    if margins:
        print(f"\n📊 Processando {len(margins)} validações de margem...")
        actions = process_margin_actions(margins)
        all_actions.extend(actions)
    
    if waste:
        print(f"\n🗑️ Processando {len(waste)} dados de desperdício...")
        actions = process_waste_actions(waste)
        all_actions.extend(actions)
    
    if not all_actions:
        print("\n⚠️  Nenhuma ação necessária no momento")
        
        # Criar arquivo vazio para documentar
        save_json("actions_log.json", {
            "_meta": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "total_actions": 0,
                "note": "Nenhuma ação executada - dados insuficientes"
            },
            "actions": []
        })
        return
    
    # Gerar saídas
    generate_actions_csv(all_actions)
    generate_actions_report(all_actions)
    
    print("\n✅ Auto Action Engine completado!")


if __name__ == "__main__":
    main()
