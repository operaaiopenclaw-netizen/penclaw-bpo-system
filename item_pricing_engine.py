#!/usr/bin/env python3
"""
ITEM PRICING ENGINE
Calcula preço ideal baseado em margem alvo

REGRAS:
- NUNCA alterar preço automaticamente
- APENAS sugerir
- Margens alvo:
  * Bar: 70%+
  * Cozinha: 60%+
  * Café: 65%+
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


# 2. MARGENS ALVO POR CATEGORIA
TARGET_MARGINS = {
    "bar": 0.70,        # 70%+
    "cozinha": 0.60,    # 60%+
    "cafe": 0.65,       # 65%+
    "bebida": 0.70,     # Mapeado para bar
    "principal": 0.60,  # Mapeado para cozinha
    "entrada": 0.60,
    "acompanhamento": 0.60,
    "finger_food": 0.60,
    "coffee_break": 0.65  # Mapeado para cafe
}


@dataclass
class PricingSuggestion:
    recipe_id: str
    recipe_name: str
    category: str
    target_margin_pct: float
    current_price: Optional[float]
    cost_unit: Optional[float]
    ideal_price: Optional[float]
    margin_atual: Optional[float]
    margin_gap: Optional[float]  # Diferença entre alvo e atual
    variance_pct: Optional[float]  # Variação do preço atual vs ideal
    suggested_action: str
    priority: str  # HIGH, MEDIUM, LOW
    reason: str
    timestamp: str
    trace_mode: str = "calculated"


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
        filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def log_error(error_type: str, severity: str, entity: Optional[str], 
              description: str, source: str = "item_pricing"):
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
    errors["_meta"] = {
        "last_updated": datetime.now().isoformat(),
        "total_errors": len(errors["errors"])
    }
    
    save_json("errors.json", errors)
    
    emoji = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}
    print(f"{emoji.get(severity, '⚠️')} [{severity.upper()}] {error_type}: {description}")


def get_target_margin(category: str) -> float:
    """Retorna margem alvo baseado na categoria"""
    # Mapear categorias genéricas para margens específicas
    category_mapping = {
        "bar": ["bebida", "drink", "coquetel", "destilado", "cerveja", "vinho"],
        "cozinha": ["principal", "entrada", "acompanhamento", "finger_food", "sobremesa"],
        "cafe": ["coffee_break", "cafe", "lanche"]
    }
    
    # Verificar se categoria direta
    if category.lower() in TARGET_MARGINS:
        return TARGET_MARGINS[category.lower()]
    
    # Verificar mapeamento
    cat_lower = category.lower()
    for group, items in category_mapping.items():
        if cat_lower in items:
            return TARGET_MARGINS[group]
    
    # Padrão: cozinha
    return TARGET_MARGINS["cozinha"]


def load_item_performance() -> List[Dict]:
    """Carrega dados de performance de itens"""
    data = load_json("item_performance.json")
    return data.get("performances", [])


def load_recipes() -> Dict[str, Dict]:
    """Carrega receitas para obter categorias"""
    recipes = load_json("recipes.json")
    return recipes.get("receitas", {})


def load_recipe_costs() -> Dict[str, Dict]:
    """Carrega custos de receitas"""
    costs = load_json("recipe_costs.json")
    return costs.get("receitas_calculadas", {})


def calculate_ideal_price(cost_unit: float, target_margin: float) -> Optional[float]:
    """
    3. CALCULAR PREÇO IDEAL
    
    Fórmula: ideal_price = cost_unit / (1 - target_margin)
    
    Exemplo:
    - Custo: R$ 10,00
    - Margem alvo: 60% (0.60)
    - Preço ideal = 10 / (1 - 0.60) = 10 / 0.40 = R$ 25,00
    """
    if cost_unit <= 0 or target_margin >= 1:
        return None
    
    ideal_price = cost_unit / (1 - target_margin)
    return round(ideal_price, 2)


def process_pricing_suggestions() -> List[PricingSuggestion]:
    """Processa sugestões de preço"""
    
    print("\n🔍 Analisando custos e preços atuais...")
    
    # Carregar dados
    performances = load_item_performance()
    recipes = load_recipes()
    costs = load_recipe_costs()
    
    if not performances:
        log_error(
            "no_item_performance",
            "high",
            None,
            "item_performance.json não encontrado ou vazio - execute item_intelligence_engine primeiro",
            "process_pricing_suggestions"
        )
        return []
    
    if not recipes:
        log_error(
            "no_recipes",
            "high",
            None,
            "recipes.json não encontrado",
            "process_pricing_suggestions"
        )
        return []
    
    print(f"   ✓ {len(performances)} itens com performance")
    print(f"   ✓ {len(recipes)} receitas")
    
    suggestions = []
    
    for perf in performances:
        recipe_id = perf.get("recipe_id")
        
        if not recipe_id:
            log_error(
                "missing_recipe_id",
                "medium",
                None,
                "Item sem recipe_id ignorado",
                "process_pricing_suggestions"
            )
            continue
        
        # Obter dados da receita
        recipe = recipes.get(recipe_id, {})
        recipe_name = perf.get("recipe_name") or recipe.get("nome", recipe_id)
        category = recipe.get("categoria", "cozinha")
        
        # Obter custo
        cost_unit = perf.get("unit_cost")
        if not cost_unit:
            # Tentar de recipe_costs
            cost_data = costs.get(recipe_id, {})
            cost_unit = cost_data.get("custo_por_porcao")
        
        if not cost_unit:
            log_error(
                "no_cost_unit",
                "high",
                recipe_id,
                f"{recipe_name}: sem custo unitário calculado",
                "process_pricing_suggestions"
            )
            continue
        
        # Obter margem alvo
        target_margin = get_target_margin(category)
        target_margin_pct = round(target_margin * 100, 1)
        
        # Calcular preço ideal
        ideal_price = calculate_ideal_price(cost_unit, target_margin)
        if not ideal_price:
            log_error(
                "invalid_ideal_price",
                "medium",
                recipe_id,
                f"Não foi possível calcular preço ideal para {recipe_name}",
                "process_pricing_suggestions"
            )
            continue
        
        # Obter preço atual (venda)
        current_price = perf.get("sale_price")
        margin_atual = perf.get("margin_pct")
        
        # Calcular margem atual se não tiver
        if not margin_atual and current_price and cost_unit:
            margin_atual = ((current_price - cost_unit) / current_price * 100) if current_price > 0 else None
        
        # 4. COMPARAR E SUGERIR AÇÃO
        suggested_action = ""
        priority = "LOW"
        reason = ""
        variance_pct = None
        margin_gap = None
        
        if margin_atual is not None:
            margin_gap = round(target_margin_pct - margin_atual, 2)
        
        if current_price:
            # Com par preço atual
            if current_price < ideal_price * 0.85:
                # Preço muito abaixo do ideal
                variance_pct = round(((current_price - ideal_price) / ideal_price * 100), 1)
                suggested_action = "increase_price_significantly"
                priority = "HIGH"
                reason = f"Preço atual R$ {current_price:.2f} está {abs(variance_pct):.1f}% abaixo do ideal (R$ {ideal_price:.2f})"
                
            elif current_price < ideal_price:
                # Preço abaixo do ideal
                variance_pct = round(((current_price - ideal_price) / ideal_price * 100), 1)
                suggested_action = "increase_price"
                priority = "MEDIUM"
                reason = f"Preço atual R$ {current_price:.2f} está abaixo do ideal R$ {ideal_price:.2f}"
                
            elif current_price > ideal_price * 1.20:
                # Preço muito acima do ideal
                variance_pct = round(((current_price - ideal_price) / ideal_price * 100), 1)
                suggested_action = "evaluate_competitiveness"
                priority = "MEDIUM"
                reason = f"Preço atual R$ {current_price:.2f} está {variance_pct:.1f}% acima do ideal - verificar competitividade"
                
            else:
                # Preço no intervalo ideal
                suggested_action = "maintain_price"
                priority = "LOW"
                reason = f"Preço dentro da faixa ideal (R$ {current_price:.2f} vs R$ {ideal_price:.2f})"
        else:
            # Sem preço atual registrado
            suggested_action = "define_initial_price"
            priority = "HIGH"
            reason = f"Sem preço registrado - sugerido: R$ {ideal_price:.2f} (alcançar {target_margin_pct}% margem)"
        
        # Verificar margem específica
        if margin_atual is not None:
            if margin_atual < target_margin_pct - 10:
                # Margem muito abaixo
                if priority == "LOW":
                    priority = "HIGH"
                suggested_action = "increase_price_urgent" if "maintain" in suggested_action else suggested_action
                reason += f" | Margem atual {margin_atual:.1f}% vs alvo {target_margin_pct}%"
            elif margin_atual < target_margin_pct - 5:
                if priority == "LOW":
                    priority = "MEDIUM"
                reason += f" | Margem abaixo do alvo ({margin_atual:.1f}% vs {target_margin_pct}%)"
        
        # Criar sugestão
        suggestion = PricingSuggestion(
            recipe_id=recipe_id,
            recipe_name=recipe_name,
            category=category,
            target_margin_pct=target_margin_pct,
            current_price=current_price,
            cost_unit=cost_unit,
            ideal_price=ideal_price,
            margin_atual=margin_atual,
            margin_gap=margin_gap,
            variance_pct=variance_pct,
            suggested_action=suggested_action,
            priority=priority,
            reason=reason,
            timestamp=datetime.now().isoformat()
        )
        
        suggestions.append(suggestion)
    
    return suggestions


def save_pricing_suggestions(suggestions: List[PricingSuggestion]):
    """Salva sugestões de preço"""
    
    # 5. OUTPUT: pricing_suggestions.json
    output = {
        "_meta": {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_suggestions": len(suggestions),
            "margem_alvo": {
                "bar": "70%+",
                "cozinha": "60%+",
                "cafe": "65%+"
            },
            "breakdown": {
                "define_initial_price": sum(1 for s in suggestions if "define" in s.suggested_action),
                "increase_price": sum(1 for s in suggestions if "increase" in s.suggested_action),
                "maintain_price": sum(1 for s in suggestions if "maintain" in s.suggested_action),
                "evaluate": sum(1 for s in suggestions if "evaluate" in s.suggested_action)
            }
        },
        "suggestions": [asdict(s) for s in suggestions]
    }
    
    save_json("pricing_suggestions.json", output)
    print(f"\n✅ Sugestões salvas em: kitchen_data/pricing_suggestions.json")


def generate_csv_report(suggestions: List[PricingSuggestion]):
    """Gera CSV de sugestões"""
    
    headers = [
        "recipe_id", "recipe_name", "category", "target_margin_pct",
        "cost_unit", "current_price", "ideal_price", "margin_atual",
        "margin_gap", "suggested_action", "priority", "reason", "timestamp"
    ]
    
    data = []
    for s in suggestions:
        row = {
            "recipe_id": s.recipe_id,
            "recipe_name": s.recipe_name,
            "category": s.category,
            "target_margin_pct": s.target_margin_pct,
            "cost_unit": round(s.cost_unit, 2) if s.cost_unit else "",
            "current_price": round(s.current_price, 2) if s.current_price else "",
            "ideal_price": round(s.ideal_price, 2) if s.ideal_price else "",
            "margin_atual": round(s.margin_atual, 2) if s.margin_atual else "",
            "margin_gap": round(s.margin_gap, 2) if s.margin_gap else "",
            "suggested_action": s.suggested_action,
            "priority": s.priority,
            "reason": s.reason,
            "timestamp": s.timestamp
        }
        data.append(row)
    
    # Ordenar por prioridade
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    data.sort(key=lambda x: priority_order.get(x["priority"], 3))
    
    filepath = OUTPUT_DIR / "pricing_suggestions.csv"
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ CSV salvo em: output/pricing_suggestions.csv")


def print_pricing_report(suggestions: List[PricingSuggestion]):
    """Imprime relatório de precificação"""
    
    print("\n" + "="*90)
    print("💰 ITEM PRICING ENGINE REPORT")
    print("="*90)
    
    print("\n📋 MARGENS ALVO POR CATEGORIA:")
    print(f"{'─'*90}")
    print(f"  🍺 Bar (Bebidas):        70%+")
    print(f"  🍽️  Cozinha (Comidas):     60%+")
    print(f"  ☕ Café (Lanches):        65%+\n")
    
    # Separar por prioridade
    high = [s for s in suggestions if s.priority == "HIGH"]
    medium = [s for s in suggestions if s.priority == "MEDIUM"]
    low = [s for s in suggestions if s.priority == "LOW"]
    
    # HIGH - Definir preço inicial ou aumento urgente
    if high:
        print(f"{'─'*90}")
        print(f"🚨 SUGESTÕES PRIORITÁRIAS ({len(high)})")
        print(f"{'─'*90}")
        
        for s in high:
            print(f"\n   📦 {s.recipe_name} ({s.recipe_id})")
            print(f"      Categoria: {s.category} | Alvo: {s.target_margin_pct}%")
            print(f"      💵 Custo: R$ {s.cost_unit:>8.2f}")
            
            if s.current_price:
                print(f"      💵 Preço atual:  R$ {s.current_price:>8.2f}")
                print(f"      💵 Preço ideal:  R$ {s.ideal_price:>8.2f}")
                if s.margin_atual:
                    print(f"      📊 Margem atual: {s.margin_atual:>6.1f}%")
                print(f"      📈 Margem alvo: {s.target_margin_pct:>6.1f}%")
                
                if s.variance_pct:
                    print(f"      📉 Variação: {s.variance_pct:>+.1f}% vs ideal")
            else:
                print(f"      💵 Preço sugerido: R$ {s.ideal_price:>8.2f}")
                print(f"      ⚠️  Sem preço registrado!")
            
            print(f"      → Ação: {s.suggested_action}")
            print(f"      → Motivo: {s.reason}")
    
    # MEDIUM - Ajustes
    if medium:
        print(f"\n{'─'*90}")
        print(f"⚠️  AJUSTES RECOMENDADOS ({len(medium)})")
        print(f"{'─'*90}")
        
        for s in medium:
            print(f"\n   📦 {s.recipe_name}")
            print(f"      {s.custo_unit:>8.2f} (custo) → R$ {s.ideal_price:>8.2f} (ideal) | Atual: R$ {s.current_price or 0:>8.2f}")
            print(f"      → {s.suggested_action}")
    
    # LOW - Manutenção
    if low:
        print(f"\n{'─'*90}")
        print(f"✅ PREÇOS DENTRO DO IDEAL ({len(low)})")
        print(f"{'─'*90}")
        
        for s in low:
            print(f"   ✓ {s.recipe_name[:40]:<40} │ R$ {s.current_price:>7.2f} (margem: {s.margin_atual or 0:.1f}%)")
    
    # Resumo
    no_price = sum(1 for s in suggestions if not s.current_price)
    below_ideal = sum(1 for s in suggestions if s.current_price and s.current_price < s.ideal_price)
    above_ideal = sum(1 for s in suggestions if s.current_price and s.current_price > s.ideal_price * 1.15)
    
    print(f"\n{'='*90}")
    print("📊 RESUMO GERAL")
    print(f"{'='*90}")
    print(f"  Total analisado:        {len(suggestions):>4} itens")
    print(f"  🚨 Sem preço/registro:   {no_price:>4}")
    print(f"  ⚠️  Preço abaixo ideal:   {below_ideal:>4}")
    print(f"  🔍 Acima ideal (+15%):   {above_ideal:>4}")
    print(f"  ✅ No intervalo ideal:    {len(low):>4}")
    print(f"{'='*90}")
    
    print("\n⚠️  IMPORTANTE:")
    print("   Estas são sugestões apenas. NENHUM preço será alterado automaticamente.")
    print("   Decisão final é humana.")


def main():
    """Função principal"""
    
    print("🎛️ ITEM PRICING ENGINE - Orkestra Finance Brain")
    print("="*90)
    print("\n💰 Calculando preços ideais baseados em margem alvo")
    print("   Fórmula: ideal_price = cost / (1 - target_margin)")
    
    # Processar
    suggestions = process_pricing_suggestions()
    
    if not suggestions:
        print("\n❌ Nenhuma sugestão gerada")
        print("   É preciso dados de:")
        print("   - item_performance.json (execute item_intelligence_engine)")
        print("   - recipes.json")
        return
    
    # Salvar
    save_pricing_suggestions(suggestions)
    generate_csv_report(suggestions)
    print_pricing_report(suggestions)
    
    print(f"\n✅ Item Pricing Engine completado!")
    print(f"   {len(suggestions)} itens analisados")


if __name__ == "__main__":
    main()
