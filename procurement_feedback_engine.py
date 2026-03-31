#!/usr/bin/env python3
"""
PROCUREMENT FEEDBACK LOOP ENGINE
Ajusta compras com base no consumo real

REGRAS:
- Identificar insumos mais consumidos
- Calcular custo médio real
- Detectar variação de preço
- Sugerir troca de fornecedor
- Ajustar volume de compra
- Prevenir ruptura
"""

import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class ProcurementSuggestion:
    item_id: str
    item_name: str
    suggestion_type: str  # "change_supplier", "adjust_volume", "prevent_stockout", "optimize_price"
    priority: str  # "HIGH", "MEDIUM", "LOW"
    current_avg_cost: Optional[float]
    historical_avg_cost: Optional[float]
    price_variation_pct: Optional[float]
    monthly_consumption: float
    recommended_action: str
    reason: str
    timestamp: str
    trace_mode: str = "inferred"


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


def log_error(error_type: str, severity: str, item_id: Optional[str], 
              description: str, source: str = "procurement_feedback"):
    """Registra erro em errors.json"""
    errors = load_json("errors.json")
    
    if "errors" not in errors:
        errors["errors"] = []
    
    error_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": error_type,
        "severity": severity,
        "event_id": item_id,
        "description": description,
        "source": source
    }
    
    errors["errors"].append(error_entry)
    errors["_meta"] = {
        "last_updated": datetime.now().isoformat(),
        "total_errors": len(errors["errors"])
    }
    
    save_json("errors.json", errors)
    
    emoji = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}
    print(f"{emoji.get(severity, '⚠️')} [{severity.upper()}] {error_type}: {description}")


def load_consumption_data() -> Dict[str, Dict]:
    """Carrega dados de consumo real do waste_log"""
    waste = load_json("waste_log.json")
    consumption = defaultdict(lambda: {"total": 0.0, "by_event": []})
    
    for event_id, data in waste.get("registros", {}).items():
        consumos = data.get("consumo", [])
        for c in consumos:
            item_id = c.get("item_id")
            qtd = c.get("quantity_used", 0)
            if item_id and qtd:
                consumption[item_id]["total"] += qtd
                consumption[item_id]["by_event"].append({
                    "event_id": event_id,
                    "quantity": qtd,
                    "date": data.get("data_evento", "")
                })
    
    return dict(consumption)


def load_inventory_with_history() -> Dict[str, Dict]:
    """Carrega inventário com histórico de preços"""
    inventory = load_json("inventory.json")
    items = {}
    
    for item in inventory.get("inventory", []):
        item_id = item.get("codigo")
        if item_id:
            items[item_id] = item
    
    return items


def load_events() -> List[Dict]:
    """Carrega eventos históricos para análise temporal"""
    return load_csv("events_consolidated.csv")


def calculate_monthly_consumption(item_id: str, consumption_data: Dict, 
                                   months: int = 3) -> float:
    """Calcula consumo mensal médio"""
    item_data = consumption_data.get(item_id, {})
    total = item_data.get("total", 0)
    
    # Se não tem dados, retornar 0
    if total == 0:
        return 0.0
    
    # Estimar baseado em eventos disponíveis
    events = item_data.get("by_event", [])
    if not events:
        return 0.0
    
    # Calcular média mensal (assumindo eventos distribuídos)
    avg_per_month = total / max(months, 1)
    return round(avg_per_month, 2)


def analyze_price_variation(item_id: str, inventory_items: Dict) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Analisa variação de preço de um item
    
    Retorna: (current_avg, historical_avg, variation_pct)
    """
    item = inventory_items.get(item_id)
    if not item:
        return None, None, None
    
    # Preço atual
    current_price = item.get("preco_unitario", 0)
    
    # Histórico
    historico = item.get("historico_entradas", [])
    
    if not historico:
        log_error(
            "no_price_history",
            "medium",
            item_id,
            f"Item {item_id} sem histórico de preços - usando preço atual",
            "analyze_price_variation"
        )
        return current_price, current_price, 0.0
    
    # Calcular média histórica ponderada
    total_valor = 0.0
    total_qtd = 0.0
    
    for entrada in historico:
        qtd = entrada.get("quantidade", 0)
        preco = entrada.get("preco_unitario", 0)
        if qtd > 0 and preco > 0:
            total_valor += qtd * preco
            total_qtd += qtd
    
    if total_qtd == 0:
        return current_price, current_price, 0.0
    
    historical_avg = total_valor / total_qtd
    
    # Calcular variação
    if historical_avg > 0:
        variation_pct = ((current_price - historical_avg) / historical_avg) * 100
        variation_pct = round(variation_pct, 2)
    else:
        variation_pct = 0.0
    
    return current_price, historical_avg, variation_pct


def check_stock_risk(item_id: str, inventory_items: Dict, monthly_consumption: float) -> Tuple[bool, float, str]:
    """
    Verifica risco de ruptura de estoque
    
    Retorna: (em_risco, dias_estoque, mensagem)
    """
    item = inventory_items.get(item_id)
    if not item:
        return True, 0, "Item não encontrado no inventário"
    
    qtd_atual = item.get("quantidade_atual", 0)
    
    if monthly_consumption <= 0:
        return False, float('inf'), "Sem consumo registrado"
    
    # Calcular dias de estoque
    daily_consumption = monthly_consumption / 30
    dias_estoque = qtd_atual / daily_consumption if daily_consumption > 0 else float('inf')
    
    dias_estoque = round(dias_estoque, 1)
    
    if dias_estoque < 7:
        return True, dias_estoque, f"Risco de ruptura: apenas {dias_estoque} dias de estoque"
    elif dias_estoque < 15:
        return False, dias_estoque, f"Estoque baixo: {dias_estoque} dias"
    else:
        return False, dias_estoque, f"Estoque adequado: {dias_estoque} dias"


def identify_suppliers(item_id: str, inventory_items: Dict) -> List[Dict]:
    """Identifica fornecedores alternativos para um item"""
    item = inventory_items.get(item_id)
    if not item:
        return []
    
    # Em implementação real, buscar de base de fornecedores
    # Aqui retornamos placeholder
    current_supplier = item.get("fornecedor_atual", "Desconhecido")
    alternative_suppliers = item.get("fornecedores_alternativos", [])
    
    return [
        {"name": current_supplier, "type": "current", "price": item.get("preco_unitario", 0)},
        *[{"name": s, "type": "alternative", "price": None} for s in alternative_suppliers]
    ]


def generate_procurement_suggestions() -> List[ProcurementSuggestion]:
    """Gera sugestões de compra baseadas em análise"""
    
    print("\n🔍 Analisando dados de consumo e preços...")
    
    # Carregar dados
    consumption = load_consumption_data()
    inventory = load_inventory_with_history()
    
    if not consumption:
        log_error(
            "no_consumption_data",
            "high",
            None,
            "Nenhum dado de consumo encontrado - executar engines de produção primeiro",
            "generate_procurement_suggestions"
        )
        return []
    
    if not inventory:
        log_error(
            "no_inventory",
            "high",
            None,
            "Inventário vazio - popular kitchen_data/inventory.json",
            "generate_procurement_suggestions"
        )
        return []
    
    print(f"   ✓ {len(consumption)} itens com consumo real")
    print(f"   ✓ {len(inventory)} itens no inventário")
    
    suggestions = []
    
    # Ordenar por consumo (mais consumidos primeiro)
    sorted_items = sorted(
        consumption.items(),
        key=lambda x: x[1]["total"],
        reverse=True
    )
    
    print(f"\n🎯 Processando {min(20, len(sorted_items))} itens mais consumidos...")
    
    for item_id, data in sorted_items[:20]:  # Top 20 consumidos
        item = inventory.get(item_id)
        if not item:
            continue
        
        item_name = item.get("nome", item_id)
        monthly_consumption = calculate_monthly_consumption(item_id, {item_id: data}, months=3)
        
        # Analisar variação de preço
        current_cost, hist_cost, variation = analyze_price_variation(item_id, inventory)
        
        # Verificar risco de ruptura
        at_risk, days_stock, risk_msg = check_stock_risk(item_id, inventory, monthly_consumption)
        
        # GERAR SUGESTÕES
        
        # 1. Troca de fornecedor (se preço subiu muito)
        if variation and variation > 15:
            suppliers = identify_suppliers(item_id, inventory)
            alt_suppliers = [s for s in suppliers if s["type"] == "alternative"]
            
            if alt_suppliers:
                suggestion = ProcurementSuggestion(
                    item_id=item_id,
                    item_name=item_name,
                    suggestion_type="change_supplier",
                    priority="HIGH",
                    current_avg_cost=current_cost,
                    historical_avg_cost=hist_cost,
                    price_variation_pct=variation,
                    monthly_consumption=monthly_consumption,
                    recommended_action=f"Negociar com {len(alt_suppliers)} fornecedores alternativos",
                    reason=f"Preço subiu {variation:.1f}% vs média histórica (de R$ {hist_cost:.2f} para R$ {current_cost:.2f})",
                    timestamp=datetime.now().isoformat()
                )
                suggestions.append(suggestion)
        
        # 2. Ajustar volume de compra (se variação de preço)
        if variation and abs(variation) > 5:
            priority = "HIGH" if abs(variation) > 15 else "MEDIUM"
            action = "aumentar_estoque" if variation < 0 else "reduzir_imediato"
            
            suggestion = ProcurementSuggestion(
                item_id=item_id,
                item_name=item_name,
                suggestion_type="adjust_volume",
                priority=priority,
                current_avg_cost=current_cost,
                historical_avg_cost=hist_cost,
                price_variation_pct=variation,
                monthly_consumption=monthly_consumption,
                recommended_action=f"{action} - variação {variation:.1f}% detectada",
                reason=f"Tendência de preço: {'queda' if variation < 0 else 'alta'} de {abs(variation):.1f}%",
                timestamp=datetime.now().isoformat()
            )
            suggestions.append(suggestion)
        
        # 3. Prevenir ruptura
        if at_risk:
            suggestion = ProcurementSuggestion(
                item_id=item_id,
                item_name=item_name,
                suggestion_type="prevent_stockout",
                priority="HIGH",
                current_avg_cost=current_cost,
                historical_avg_cost=hist_cost,
                price_variation_pct=variation,
                monthly_consumption=monthly_consumption,
                recommended_action=f"COMPRA URGENTE - estoque para {days_stock} dias",
                reason=risk_msg,
                timestamp=datetime.now().isoformat()
            )
            suggestions.append(suggestion)
        
        # 4. Otimização (itens de alto consumo sem alertas)
        elif monthly_consumption > 10 and (not variation or abs(variation) <= 5):
            suggestion = ProcurementSuggestion(
                item_id=item_id,
                item_name=item_name,
                suggestion_type="optimize_price",
                priority="LOW",
                current_avg_cost=current_cost,
                historical_avg_cost=hist_cost,
                price_variation_pct=variation,
                monthly_consumption=monthly_consumption,
                recommended_action="Monitorar preços e negociar volume",
                reason=f"Alto consumo ({monthly_consumption:.1f}/mês) - oportunidade para desconto por volume",
                timestamp=datetime.now().isoformat()
            )
            suggestions.append(suggestion)
    
    return suggestions


def save_procurement_suggestions(suggestions: List[ProcurementSuggestion]):
    """Salva sugestões em JSON"""
    
    output = {
        "_meta": {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_suggestions": len(suggestions),
            "breakdown": {
                "change_supplier": sum(1 for s in suggestions if s.suggestion_type == "change_supplier"),
                "adjust_volume": sum(1 for s in suggestions if s.suggestion_type == "adjust_volume"),
                "prevent_stockout": sum(1 for s in suggestions if s.suggestion_type == "prevent_stockout"),
                "optimize_price": sum(1 for s in suggestions if s.suggestion_type == "optimize_price")
            }
        },
        "suggestions": [asdict(s) for s in suggestions]
    }
    
    save_json("procurement_suggestions.json", output)
    print(f"\n✅ Sugestões salvas em: kitchen_data/procurement_suggestions.json")
    
    return output


def generate_csv_report(suggestions: List[ProcurementSuggestion]):
    """Gera relatório CSV"""
    
    headers = [
        "item_id", "item_name", "suggestion_type", "priority",
        "current_avg_cost", "historical_avg_cost", "price_variation_pct",
        "monthly_consumption", "recommended_action", "reason", "timestamp"
    ]
    
    data = []
    for s in suggestions:
        row = {
            "item_id": s.item_id,
            "item_name": s.item_name,
            "suggestion_type": s.suggestion_type,
            "priority": s.priority,
            "current_avg_cost": round(s.current_avg_cost, 2) if s.current_avg_cost else "",
            "historical_avg_cost": round(s.historical_avg_cost, 2) if s.historical_avg_cost else "",
            "price_variation_pct": round(s.price_variation_pct, 2) if s.price_variation_pct else "",
            "monthly_consumption": round(s.monthly_consumption, 2),
            "recommended_action": s.recommended_action,
            "reason": s.reason,
            "timestamp": s.timestamp
        }
        data.append(row)
    
    # Ordenar por prioridade
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    data.sort(key=lambda x: priority_order.get(x["priority"], 3))
    
    filepath = OUTPUT_DIR / "procurement_suggestions.csv"
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ CSV salvo em: output/procurement_suggestions.csv")


def print_procurement_report(suggestions: List[ProcurementSuggestion]):
    """Imprime relatório de ações de compra"""
    
    emoji_type = {
        "change_supplier": "🏭",
        "adjust_volume": "📦",
        "prevent_stockout": "🚨",
        "optimize_price": "💰"
    }
    
    emoji_priority = {
        "HIGH": "🚨 HIGH",
        "MEDIUM": "⚠️ MEDIUM",
        "LOW": "ℹ️ LOW"
    }
    
    print("\n" + "="*90)
    print("🛒 PROCUREMENT FEEDBACK LOOP REPORT")
    print("="*90)
    
    # Separar por prioridade
    high = [s for s in suggestions if s.priority == "HIGH"]
    medium = [s for s in suggestions if s.priority == "MEDIUM"]
    low = [s for s in suggestions if s.priority == "LOW"]
    
    # HIGH
    if high:
        print(f"\n{'─'*90}")
        print("🚨 AÇÕES PRIORITÁRIAS - URGENTE")
        print(f"{'─'*90}")
        for s in high:
            print(f"\n   {emoji_type.get(s.suggestion_type, '❓')} {s.item_name} ({s.item_id})")
            print(f"      Tipo: {s.suggestion_type}")
            print(f"      Ação: {s.recommended_action}")
            print(f"      Motivo: {s.reason}")
            if s.current_avg_cost:
                print(f"      Custo atual: R$ {s.current_avg_cost:.2f}")
            if s.price_variation_pct:
                print(f"      Variação: {s.price_variation_pct:+.1f}%")
            if s.monthly_consumption:
                print(f"      Consumo mensal: {s.monthly_consumption:.1f}")
    
    # MEDIUM
    if medium:
        print(f"\n{'─'*90}")
        print("⚠️  AÇÕES MÉDIAS - REVISAR")
        print(f"{'─'*90}")
        for s in medium:
            print(f"\n   {emoji_type.get(s.suggestion_type, '❓')} {s.item_name} ({s.item_id})")
            print(f"      Ação: {s.recommended_action}")
            print(f"      Motivo: {s.reason}")
    
    # LOW
    if low:
        print(f"\n{'─'*90}")
        print("💰 OPORTUNIDADES - MONITORAR")
        print(f"{'─'*90}")
        for s in low:
            print(f"\n   {emoji_type.get(s.suggestion_type, '❓')} {s.item_name}")
            print(f"      Ação: {s.recommended_action}")
            print(f"      Motivo: {s.reason}")
    
    # Resumo por tipo
    print(f"\n{'='*90}")
    print("RESUMO POR TIPO DE AÇÃO:")
    print(f"{'='*90}")
    
    types = ["change_supplier", "adjust_volume", "prevent_stockout", "optimize_price"]
    type_names = {
        "change_supplier": "🏭 Trocar Fornecedor",
        "adjust_volume": "📦 Ajustar Volume",
        "prevent_stockout": "🚨 Prevenir Ruptura",
        "optimize_price": "💰 Otimizar Preço"
    }
    
    for t in types:
        count = sum(1 for s in suggestions if s.suggestion_type == t)
        if count > 0:
            print(f"  {type_names.get(t, t)}: {count} sugestões")
    
    print(f"\n  TOTAL: {len(suggestions)} sugestões de compra")
    print("="*90)


def main():
    """Função principal"""
    
    print("🎛️ PROCUREMENT FEEDBACK LOOP ENGINE - Orkestra Finance Brain")
    print("="*90)
    
    # Gerar sugestões
    suggestions = generate_procurement_suggestions()
    
    if not suggestions:
        print("\n⚠️  Nenhuma sugestão gerada")
        print("   É preciso ter dados de:")
        print("   - kitchen_data/inventory.json (estoque)")
        print("   - kitchen_data/waste_log.json (consumo)")
        print("   - kitchen_data/events_consolidated.csv (eventos)")
        return
    
    # Salvar
    save_procurement_suggestions(suggestions)
    generate_csv_report(suggestions)
    print_procurement_report(suggestions)
    
    print("\n✅ Procurement Feedback Loop completado!")


if __name__ == "__main__":
    main()
