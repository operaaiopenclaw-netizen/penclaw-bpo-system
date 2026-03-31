#!/usr/bin/env python3
"""
SYSTEM CALIBRATION ENGINE
Ajusta parâmetros do sistema com base em inconsistências detectadas

REGRA CRÍTICA:
- NUNCA alterar automaticamente
- APENAS sugerir
- Aprender com padrões de erro
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class CalibrationSuggestion:
    suggestion_id: str
    target_type: str  # "recipe", "item", "supplier", "event_type", "system"
    target_id: str
    target_name: str
    pattern_detected: str
    current_value: Any
    suggested_value: Any
    reason: str
    affected_events: List[str]
    confidence: float
    priority: str
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


def load_audit_errors() -> List[Dict]:
    """Carrega erros da auditoria"""
    audit = load_json("audit_errors.json")
    return audit.get("errors", [])


def load_item_performance() -> List[Dict]:
    """Carrega performance por item"""
    data = load_json("item_performance.json")
    return data.get("performances", [])


def load_waste_log() -> Dict:
    """Carrega log de desperdício"""
    return load_json("waste_log.json")


def load_recipes() -> Dict:
    """Carrega receitas"""
    data = load_json("recipes.json")
    return data.get("receitas", {})


def load_events() -> List[Dict]:
    """Carrega eventos"""
    import csv
    filepath = DATA_DIR / "events_consolidated.csv"
    if not filepath.exists():
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def analyze_errors_by_item(errors: List[Dict]) -> Dict[str, List[Dict]]:
    """2.1 Identificar erro recorrente por item"""
    by_item = defaultdict(list)
    
    for error in errors:
        # Extrair item_id da descrição ou event_id
        desc = error.get("description", "")
        event_id = error.get("event_id", "")
        
        # Buscar item_id na descrição
        # Padrão: "Item ITEM-001" ou similar
        import re
        matches = re.findall(r'([A-Z]+-\d+)', desc)
        
        for item_id in matches:
            by_item[item_id].append(error)
    
    return dict(by_item)


def analyze_errors_by_event_type(errors: List[Dict], events: List[Dict]) -> Dict[str, List[Dict]]:
    """2.2 Identificar erro recorrente por tipo de evento"""
    by_type = defaultdict(list)
    
    # Mapear event_id para event_type
    event_types = {}
    for e in events:
        event_types[e.get("event_id")] = e.get("event_type", "desconhecido")
    
    for error in errors:
        event_id = error.get("event_id")
        if event_id:
            event_type = event_types.get(event_id, "desconhecido")
            by_type[event_type].append(error)
    
    return dict(by_type)


def analyze_errors_by_supplier(errors: List[Dict]) -> Dict[str, List[Dict]]:
    """2.3 Identificar erro recorrente por fornecedor"""
    by_supplier = defaultdict(list)
    
    # Carregar inventário para mapear fornecedores
    inventory = load_json("inventory.json").get("inventory", [])
    item_supplier = {}
    
    for item in inventory:
        item_id = item.get("codigo")
        supplier = item.get("fornecedor_atual", item.get("fornecedor", ""))
        if item_id and supplier:
            item_supplier[item_id] = supplier
    
    # Agrupar erros por fornecedor
    for error in errors:
        desc = error.get("description", "")
        event_id = error.get("event_id", "")
        
        import re
        matches = re.findall(r'([A-Z]+-\d+)', desc)
        
        for item_id in matches:
            supplier = item_supplier.get(item_id)
            if supplier:
                by_supplier[supplier].append({
                    **error,
                    "related_item": item_id
                })
    
    return dict(by_supplier)


def analyze_errors_by_recipe(errors: List[Dict]) -> Dict[str, List[Dict]]:
    """2.4 Identificar erro recorrente por receita"""
    by_recipe = defaultdict(list)
    
    for error in errors:
        desc = error.get("description", "")
        event_id = error.get("event_id", "")
        
        # Buscar recipe_id (formato REC###)
        import re
        matches = re.findall(r'(REC\d+)', desc)
        
        for recipe_id in matches:
            by_recipe[recipe_id].append(error)
    
    return dict(by_recipe)


def analyze_waste_patterns(item_perf: List[Dict]) -> Dict[str, Dict]:
    """Analisa padrões de desperdício"""
    waste_by_recipe = defaultdict(lambda: {
        "total_waste": 0,
        "total_produced": 0,
        "waste_events": [],
        "avg_waste_pct": 0
    })
    
    for perf in item_perf:
        recipe_id = perf.get("recipe_id")
        waste_pct = perf.get("waste_pct")
        waste_qty = perf.get("waste_qty")
        produced = perf.get("quantity_produced")
        
        if recipe_id and waste_pct is not None:
            waste_by_recipe[recipe_id]["total_waste"] += waste_qty or 0
            waste_by_recipe[recipe_id]["total_produced"] += produced or 0
            waste_by_recipe[recipe_id]["waste_events"].append(perf.get("event_id"))
    
    # Calcular médias
    for recipe_id, data in waste_by_recipe.items():
        if data["total_produced"] > 0:
            data["avg_waste_pct"] = (data["total_waste"] / data["total_produced"]) * 100
    
    return dict(waste_by_recipe)


def analyze_margin_patterns(item_perf: List[Dict]) -> Dict[str, Dict]:
    """Analisa padrões de margem"""
    margin_by_recipe = defaultdict(lambda: {
        "margins": [],
        "revenues": [],
        "avg_margin": 0,
        "min_margin": float('inf'),
        "max_margin": 0,
        "events": []
    })
    
    for perf in item_perf:
        recipe_id = perf.get("recipe_id")
        margin = perf.get("margin_pct")
        revenue = perf.get("revenue")
        
        if recipe_id and margin is not None:
            margin_by_recipe[recipe_id]["margins"].append(margin)
            margin_by_recipe[recipe_id]["revenues"].append(revenue or 0)
            margin_by_recipe[recipe_id]["min_margin"] = min(margin_by_recipe[recipe_id]["min_margin"], margin)
            margin_by_recipe[recipe_id]["max_margin"] = max(margin_by_recipe[recipe_id]["max_margin"], margin)
            margin_by_recipe[recipe_id]["events"].append(perf.get("event_id"))
    
    # Calcular médias
    for recipe_id, data in margin_by_recipe.items():
        if data["margins"]:
            data["avg_margin"] = sum(data["margins"]) / len(data["margins"])
    
    return dict(margin_by_recipe)


def generate_suggestions(
    errors_by_item: Dict,
    errors_by_event_type: Dict,
    errors_by_supplier: Dict,
    errors_by_recipe: Dict,
    waste_patterns: Dict,
    margin_patterns: Dict
) -> List[CalibrationSuggestion]:
    """3. Gerar sugestões de ajuste"""
    
    suggestions = []
    recipes = load_recipes()
    
    # 3.1 Ajustar ficha técnica (receitas com erro recorrente)
    for recipe_id, errors in errors_by_recipe.items():
        if len(errors) >= 3:  # Recorrente = 3+ erros
            recipe = recipes.get(recipe_id, {})
            recipe_name = recipe.get("nome", recipe_id)
            
            # Analisar tipo de erro
            error_types = [e.get("type") for e in errors]
            most_common = max(set(error_types), key=error_types.count)
            
            suggestion = CalibrationSuggestion(
                suggestion_id=f"CAL-{len(suggestions)+1:04d}",
                target_type="recipe",
                target_id=recipe_id,
                target_name=recipe_name,
                pattern_detected=f"Erro recorrente ({len(errors)} vezes): {most_common}",
                current_value="Ficha técnica atual",
                suggested_value="Revisar quantidades de insumos",
                reason=f"Padrão de erro consistente detectado em {len(errors)} eventos",
                affected_events=[e.get("event_id") for e in errors[:5]],
                confidence=min(len(errors) / 5, 0.9),
                priority="HIGH" if len(errors) >= 5 else "MEDIUM",
                timestamp=datetime.now().isoformat()
            )
            suggestions.append(asdict(suggestion))
    
    # 3.2 Ajustar consumo médio (itens com erro de CMV vs estoque)
    for item_id, errors in errors_by_item.items():
        cmv_errors = [e for e in errors if "CMV" in e.get("type", "")]
        if len(cmv_errors) >= 2:
            suggestion = CalibrationSuggestion(
                suggestion_id=f"CAL-{len(suggestions)+1:04d}",
                target_type="item",
                target_id=item_id,
                target_name=f"Item {item_id}",
                pattern_detected="Divergência recorrente CMV vs Estoque",
                current_value="Consumo médio atual",
                suggested_value="Recalcular com base em consumo real recente",
                reason=f"{len(cmv_errors)} divergências de CMV detectadas",
                affected_events=[e.get("event_id") for e in cmv_errors[:5]],
                confidence=min(len(cmv_errors) / 5, 0.85),
                priority="HIGH",
                timestamp=datetime.now().isoformat()
            )
            suggestions.append(asdict(suggestion))
    
    # 3.3 Ajustar previsão de produção (receitas com alto desperdício)
    for recipe_id, data in waste_patterns.items():
        if data["avg_waste_pct"] > 15:  # Mais de 15% de desperdício
            recipe = recipes.get(recipe_id, {})
            
            # Calcular fator de ajuste
            current_yield = recipe.get("rendimento_porca", 1)
            suggested_yield = current_yield * (1 - (data["avg_waste_pct"] / 100))
            
            suggestion = CalibrationSuggestion(
                suggestion_id=f"CAL-{len(suggestions)+1:04d}",
                target_type="recipe",
                target_id=recipe_id,
                target_name=recipe.get("nome", recipe_id),
                pattern_detected=f"Desperdício médio de {data['avg_waste_pct']:.1f}%",
                current_value=f"Rendimento: {current_yield} porções",
                suggested_value=f"Rendimento ajustado: {suggested_yield:.1f} porções",
                reason=f"Previsão de produção superestimada em {data['avg_waste_pct']:.1f}%",
                affected_events=data["waste_events"][:5],
                confidence=min(data["avg_waste_pct"] / 30, 0.9),
                priority="HIGH" if data["avg_waste_pct"] > 25 else "MEDIUM",
                timestamp=datetime.now().isoformat()
            )
            suggestions.append(asdict(suggestion))
    
    # 3.4 Ajustar compra (fornecedores com problemas recorrentes)
    for supplier, errors in errors_by_supplier.items():
        if len(errors) >= 3:
            # Buscar itens afetados
            affected_items = list(set(e.get("related_item") for e in errors if e.get("related_item")))
            
            suggestion = CalibrationSuggestion(
                suggestion_id=f"CAL-{len(suggestions)+1:04d}",
                target_type="supplier",
                target_id=supplier,
                target_name=supplier,
                pattern_detected=f"Problemas recorrentes ({len(errors)} ocorrências)",
                current_value="Fornecedor atual",
                suggested_value="Avaliar fornecedores alternativos",
                reason=f"{len(errors)} problemas relacionados a este fornecedor",
                affected_events=[e.get("event_id") for e in errors[:5]],
                confidence=min(len(errors) / 5, 0.8),
                priority="MEDIUM",
                timestamp=datetime.now().isoformat()
            )
            suggestions.append(asdict(suggestion))
    
    # 3.5 Ajustar margem alvo (receitas com margem consistentemente baixa)
    for recipe_id, data in margin_patterns.items():
        if data["avg_margin"] < 30 and len(data["margins"]) >= 2:
            recipe = recipes.get(recipe_id, {})
            
            suggestion = CalibrationSuggestion(
                suggestion_id=f"CAL-{len(suggestions)+1:04d}",
                target_type="recipe",
                target_id=recipe_id,
                target_name=recipe.get("nome", recipe_id),
                pattern_detected=f"Margem média de {data['avg_margin']:.1f}%",
                current_value="Preço atual ou ficha técnica",
                suggested_value="Aumentar preço ou reduzir custo",
                reason=f"Margem consistentemente abaixo do alvo (30%)",
                affected_events=data["events"][:5],
                confidence=min((30 - data["avg_margin"]) / 30, 0.9),
                priority="HIGH" if data["avg_margin"] < 20 else "MEDIUM",
                timestamp=datetime.now().isoformat()
            )
            suggestions.append(asdict(suggestion))
    
    return suggestions


def save_calibration_suggestions(suggestions: List[Dict]):
    """4. Salvar calibration_suggestions.json"""
    
    output = {
        "_meta": {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_suggestions": len(suggestions),
            "disclaimer": "SUGESTÕES APENAS - NENHUM AJUSTE AUTOMÁTICO REALIZADO",
            "breakdown": {
                "recipe": sum(1 for s in suggestions if s["target_type"] == "recipe"),
                "item": sum(1 for s in suggestions if s["target_type"] == "item"),
                "supplier": sum(1 for s in suggestions if s["target_type"] == "supplier"),
                "event_type": sum(1 for s in suggestions if s["target_type"] == "event_type")
            },
            "priority": {
                "HIGH": sum(1 for s in suggestions if s["priority"] == "HIGH"),
                "MEDIUM": sum(1 for s in suggestions if s["priority"] == "MEDIUM"),
                "LOW": sum(1 for s in suggestions if s["priority"] == "LOW")
            }
        },
        "suggestions": suggestions
    }
    
    save_json("calibration_suggestions.json", output)
    print(f"\n✅ Sugestões salvas em: kitchen_data/calibration_suggestions.json")


def generate_csv_report(suggestions: List[Dict]):
    """Gera CSV de sugestões"""
    
    import csv
    
    headers = [
        "suggestion_id", "target_type", "target_id", "target_name",
        "pattern_detected", "current_value", "suggested_value",
        "reason", "confidence", "priority", "affected_events", "timestamp"
    ]
    
    data = []
    for s in suggestions:
        row = {
            "suggestion_id": s["suggestion_id"],
            "target_type": s["target_type"],
            "target_id": s["target_id"],
            "target_name": s["target_name"],
            "pattern_detected": s["pattern_detected"],
            "current_value": str(s["current_value"]),
            "suggested_value": str(s["suggested_value"]),
            "reason": s["reason"],
            "confidence": f"{s['confidence']:.0%}",
            "priority": s["priority"],
            "affected_events": ";".join(s["affected_events"][:3]),
            "timestamp": s["timestamp"]
        }
        data.append(row)
    
    # Ordenar por prioridade
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    data.sort(key=lambda x: priority_order.get(x["priority"], 3))
    
    filepath = OUTPUT_DIR / "calibration_suggestions.csv"
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ CSV salvo em: output/calibration_suggestions.csv")


def print_calibration_report(suggestions: List[Dict]):
    """Imprime relatório de calibração"""
    
    print("\n" + "="*90)
    print("🔧 SYSTEM CALIBRATION ENGINE REPORT")
    print("="*90)
    
    print("\n⚠️  DISCLAIMER:")
    print("   " + "="*70)
    print("   ESTAS SÃO SUGESTÕES APENAS")
    print("   NENHUM PARÂMETRO SERÁ ALTERADO AUTOMATICAMENTE")
    print("   DECISÃO FINAL É HUMANA")
    print("   " + "="*70)
    
    # Separar por tipo
    by_type = defaultdict(list)
    for s in suggestions:
        by_type[s["target_type"]].append(s)
    
    # HIGH PRIORITY
    high = [s for s in suggestions if s["priority"] == "HIGH"]
    if high:
        print(f"\n{'─'*90}")
        print(f"🚨 SUGESTÕES PRIORITÁRIAS ({len(high)})")
        print(f"{'─'*90}")
        
        for s in high:
            print(f"\n   [{s['suggestion_id']}] {s['target_name']}")
            print(f"      Tipo: {s['target_type']}")
            print(f"      Padrão: {s['pattern_detected']}")
            print(f"      Atual: {s['current_value']}")
            print(f"      Sugerido: {s['suggested_value']}")
            print(f"      Confiança: {s['confidence']:.0%}")
            print(f"      Motivo: {s['reason']}")
            print(f"      Eventos afetados: {len(s['affected_events'])}")
    
    # Por categoria
    for target_type, items in by_type.items():
        print(f"\n{'─'*90}")
        
        if target_type == "recipe":
            print(f"📋 AJUSTES DE FICHA TÉCNICA ({len(items)})")
        elif target_type == "item":
            print(f"📦 AJUSTES DE CONSUMO ({len(items)})")
        elif target_type == "supplier":
            print(f"🏭 AJUSTES DE FORNECEDOR ({len(items)})")
        else:
            print(f"⚙️  AJUSTES DE SISTEMA ({len(items)})")
        
        print(f"{'─'*90}")
        
        for s in items:
            emoji = {"HIGH": "🚨", "MEDIUM": "⚠️", "LOW": "ℹ️"}.get(s["priority"], "❓")
            print(f"\n   {emoji} {s['target_name']}")
            print(f"      {s['pattern_detected']}")
            print(f"      → {s['suggested_value']}")
            print(f"      (confiança: {s['confidence']:.0%})")
    
    # Resumo
    print(f"\n{'='*90}")
    print("📊 RESUMO DA CALIBRAÇÃO")
    print(f"{'='*90}")
    
    print(f"\n   Por tipo:")
    for target_type, items in by_type.items():
        print(f"      {target_type}: {len(items)} sugestões")
    
    print(f"\n   Por prioridade:")
    print(f"      🚨 HIGH:   {sum(1 for s in suggestions if s['priority'] == 'HIGH'):>3}")
    print(f"      ⚠️  MEDIUM: {sum(1 for s in suggestions if s['priority'] == 'MEDIUM'):>3}")
    print(f"      ℹ️  LOW:    {sum(1 for s in suggestions if s['priority'] == 'LOW'):>3}")
    
    print(f"\n   Total: {len(suggestions)} sugestões de calibração")
    print(f"   Baseado em análise de padrões de erro")
    print("="*90)
    
    print("\n💡 RECOMENDAÇÃO:")
    print("   Revisar sugestões HIGH primeiro")
    print("   Antes de aplicar, validar em evento piloto")
    print("   Documentar mudanças em calibration_log.json")
    print("="*90 + "\n")


def main():
    """Função principal"""
    
    print("🎛️ SYSTEM CALIBRATION ENGINE - Orkestra Finance Brain")
    print("="*90)
    print("\n🔧 Analisando padrões de erro e sugerindo calibrações")
    print("   REGRA: Apenas sugerir, NUNCA alterar automaticamente")
    
    # Carregar dados
    print("\n📥 Carregando dados de auditoria...")
    
    errors = load_audit_errors()
    item_perf = load_item_performance()
    events = load_events()
    
    if not errors and not item_perf:
        print("\n⚠️  Dados insuficientes para calibração")
        print("   Execute primeiro:")
        print("   - financial_truth_audit.py")
        print("   - item_intelligence_engine.py")
        return
    
    print(f"   ✓ {len(errors)} erros de auditoria")
    print(f"   ✓ {len(item_perf)} performances de item")
    print(f"   ✓ {len(events)} eventos")
    
    # Analisar padrões
    print("\n🔍 Identificando padrões...")
    
    errors_by_item = analyze_errors_by_item(errors)
    errors_by_event_type = analyze_errors_by_event_type(errors, events)
    errors_by_supplier = analyze_errors_by_supplier(errors)
    errors_by_recipe = analyze_errors_by_recipe(errors)
    
    waste_patterns = analyze_waste_patterns(item_perf)
    margin_patterns = analyze_margin_patterns(item_perf)
    
    print(f"   ✓ {len(errors_by_item)} itens com padrão de erro")
    print(f"   ✓ {len(errors_by_event_type)} tipos de evento com padrão")
    print(f"   ✓ {len(errors_by_supplier)} fornecedores com padrão")
    print(f"   ✓ {len(errors_by_recipe)} receitas com padrão")
    print(f"   ✓ {len(waste_patterns)} padrões de desperdício")
    print(f"   ✓ {len(margin_patterns)} padrões de margem")
    
    # Gerar sugestões
    print("\n💡 Gerando sugestões de calibração...")
    suggestions = generate_suggestions(
        errors_by_item,
        errors_by_event_type,
        errors_by_supplier,
        errors_by_recipe,
        waste_patterns,
        margin_patterns
    )
    
    if not suggestions:
        print("\n✅ Nenhum padrão crítico detectado - sistema calibrado")
        save_calibration_suggestions([])
        return
    
    # Salvar
    save_calibration_suggestions(suggestions)
    generate_csv_report(suggestions)
    print_calibration_report(suggestions)
    
    print(f"\n✅ System Calibration Engine completado!")
    print(f"   {len(suggestions)} sugestões geradas")


if __name__ == "__main__":
    main()
