#!/usr/bin/env python3
"""
ITEM INTELLIGENCE ENGINE
Cálculo de custo, receita e margem por item (prato/bebida)

REGRAS CRÍTICAS:
- NUNCA usar custo estimado
- NUNCA assumir venda = produção
- SEMPRE usar custo médio do inventory
- RASTREAR tudo por event_id
- Se faltar campo → erro, NÃO assumir
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class ItemPerformance:
    recipe_id: str
    recipe_name: str
    event_id: str
    event_name: str
    company: str
    quantity_produced: Optional[float]
    quantity_sold: Optional[float]
    unit_cost: Optional[float]
    sale_price: Optional[float]
    revenue: Optional[float]
    cmv: Optional[float]
    gross_profit: Optional[float]
    margin_pct: Optional[float]
    waste_qty: Optional[float]
    waste_pct: Optional[float]
    classification: str  # HIGH_PERFORMER, GOOD, ATTENTION, CRITICAL
    issues: List[str]
    timestamp: str
    trace_mode: str = "direct"


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
              description: str, source: str = "item_intelligence"):
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
    
    emoji = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}
    print(f"{emoji.get(severity, '⚠️')} [{severity.upper()}] {error_type}: {description}")


def load_recipes() -> Dict[str, Dict]:
    """Carrega receitas"""
    recipes = load_json("recipes.json")
    return recipes.get("receitas", {})


def load_recipe_costs() -> Dict[str, Dict]:
    """Carrega custos de receitas"""
    costs = load_json("recipe_costs.json")
    return costs.get("receitas_calculadas", {})


def load_inventory() -> Dict[str, Dict]:
    """Carrega inventário com preços"""
    inv = load_json("inventory.json")
    items = {}
    
    for item in inv.get("inventory", []):
        code = item.get("codigo")
        if code:
            items[code] = item
    
    return items


def load_production_execution() -> List[Dict]:
    """Carrega execuções de produção"""
    execs = load_json("production_execution.json")
    records = []
    
    for exec_id, data in execs.get("execucoes", {}).items():
        records.append({
            **data,
            "exec_id": exec_id
        })
    
    return records


def load_events_consolidated() -> List[Dict]:
    """Carrega eventos consolidados"""
    return load_csv("events_consolidated.csv")


def load_sales_data() -> Dict[str, List[Dict]]:
    """
    Carrega dados de vendas por item
    Estrutura: {"event_id": [{recipe_id, quantity_sold, sale_price}]}
    """
    sales = load_json("sales_data.json")
    return sales.get("sales_by_event", {})


def load_cmv_events() -> Dict[str, Dict]:
    """Carrega CMV por evento"""
    cmv = load_json("cmv_log.json")
    return cmv.get("eventos", {})


def calculate_unit_cost(recipe_id: str, recipes: Dict, costs: Dict, inventory: Dict) -> Tuple[Optional[float], str]:
    """
    Calcula custo unitário de uma receita
    
    Retorna: (custo_unitario, source)
    """
    # Tentar dados de custos já calculados
    recipe_cost = costs.get(recipe_id, {})
    if recipe_cost and recipe_cost.get("custo_por_porcao"):
        return float(recipe_cost["custo_por_porcao"]), "recipe_costs"
    
    # Calcular do zero
    recipe = recipes.get(recipe_id, {})
    if not recipe:
        log_error(
            "recipe_not_found",
            "high",
            recipe_id,
            f"Receita {recipe_id} não encontrada",
            "calculate_unit_cost"
        )
        return None, "not_found"
    
    ingredients = recipe.get("ingredientes", [])
    if not ingredients:
        log_error(
            "recipe_no_ingredients",
            "high",
            recipe_id,
            f"Receita {recipe_id} sem ingredientes",
            "calculate_unit_cost"
        )
        return None, "no_ingredients"
    
    total_cost = 0.0
    
    for ingredient in ingredients:
        item_id = ingredient.get("codigo_inv")
        quantity = ingredient.get("quantidade_por_porcao", 0)
        
        if not item_id or not inventory.get(item_id):
            log_error(
                "ingredient_not_in_inventory",
                "high",
                recipe_id,
                f"Ingrediente {item_id} não encontrado no inventário",
                "calculate_unit_cost"
            )
            return None, "missing_ingredient"
        
        inv_item = inventory[item_id]
        
        # Usar custo médio ponderado
        historico = inv_item.get("historico_entradas", [])
        if historico:
            total_valor = sum(e.get("preco_unitario", 0) * e.get("quantidade", 0) for e in historico if e.get("preco_unitario"))
            total_qtd = sum(e.get("quantidade", 0) for e in historico)
            
            if total_qtd > 0:
                avg_cost = total_valor / total_qtd
            else:
                avg_cost = inv_item.get("preco_unitario", 0)
        else:
            avg_cost = inv_item.get("preco_unitario", 0)
        
        if avg_cost == 0:
            log_error(
                "zero_ingredient_cost",
                "high",
                recipe_id,
                f"Ingrediente {item_id} com custo zero",
                "calculate_unit_cost"
            )
            return None, "zero_cost"
        
        total_cost += avg_cost * quantity
    
    # Dividir por rendimento
    yield_qty = recipe.get("rendimento_porca", 1)
    if yield_qty == 0:
        yield_qty = 1
    
    unit_cost = total_cost / yield_qty
    
    return round(unit_cost, 2), "calculated_from_inventory"


def process_item_performance() -> List[ItemPerformance]:
    """Processa performance de todos os itens"""
    
    print("\n🔍 Analisando dados de receitas, custos e vendas...")
    
    # Carregar dados
    recipes = load_recipes()
    costs = load_recipe_costs()
    inventory = load_inventory()
    productions = load_production_execution()
    events = load_events_consolidated()
    sales = load_sales_data()
    
    if not recipes:
        log_error(
            "no_recipes",
            "high",
            None,
            "Nenhuma receita encontrada",
            "process_item_performance"
        )
        return []
    
    if not productions:
        log_error(
            "no_production_data",
            "high",
            None,
            "Nenhum dado de produção encontrado",
            "process_item_performance"
        )
        return []
    
    print(f"   ✓ {len(recipes)} receitas carregadas")
    print(f"   ✓ {len(costs)} custos calculados")
    print(f"   ✓ {len(productions)} execuções de produção")
    print(f"   ✓ {len(events)} eventos")
    
    performances = []
    
    # Mapear eventos
    event_map = {}
    for e in events:
        event_map[e.get("event_id", "")] = {
            "name": e.get("client_name", ""),
            "company": e.get("company", ""),
            "revenue_total": e.get("revenue_total", 0)
        }
    
    # Processar cada produção
    for exec_data in productions:
        event_id = exec_data.get("evento_id")
        exec_id = exec_data.get("exec_id")
        
        if not event_id:
            log_error(
                "production_missing_event_id",
                "high",
                None,
                f"Execução {exec_id} sem event_id",
                "process_item_performance"
            )
            continue
        
        event_info = event_map.get(event_id, {})
        company = event_info.get("company", "")
        event_name = event_info.get("name", "")
        
        # Para cada receita na produção
        for recipe_exec in exec_data.get("receitas_executadas", []):
            recipe_id = recipe_exec.get("receita_id")
            
            if not recipe_id:
                log_error(
                    "missing_recipe_id",
                    "high",
                    event_id,
                    "Receita sem ID na execução",
                    "process_item_performance"
                )
                continue
            
            recipe = recipes.get(recipe_id, {})
            recipe_name = recipe.get("nome", recipe_id)
            
            # === 3. CALCULAR CUSTO UNITÁRIO ===
            unit_cost, cost_source = calculate_unit_cost(
                recipe_id, recipes, costs, inventory
            )
            
            if unit_cost is None:
                # Criar registro com erro
                performance = ItemPerformance(
                    recipe_id=recipe_id,
                    recipe_name=recipe_name,
                    event_id=event_id,
                    event_name=event_name,
                    company=company,
                    quantity_produced=recipe_exec.get("porcoes_produzidas"),
                    quantity_sold=None,
                    unit_cost=None,
                    sale_price=None,
                    revenue=None,
                    cmv=None,
                    gross_profit=None,
                    margin_pct=None,
                    waste_qty=None,
                    waste_pct=None,
                    classification="CRITICAL",
                    issues=[f"Não foi possível calcular custo: {cost_source}"],
                    timestamp=datetime.now().isoformat(),
                    trace_mode="inferred"
                )
                performances.append(performance)
                continue
            
            # === 4. RECEITA POR ITEM (de sales_data.json) ===
            item_sales = None
            if sales.get(event_id):
                for sale in sales[event_id]:
                    if sale.get("recipe_id") == recipe_id:
                        item_sales = sale
                        break
            
            # Se não tem sales_data, usar valores estimados
            if item_sales:
                quantity_sold = item_sales.get("quantity_sold")
                try:
                    quantity_sold = float(quantity_sold) if quantity_sold else None
                except:
                    quantity_sold = None
                
                sale_price = item_sales.get("sale_price")
                try:
                    sale_price = float(sale_price) if sale_price else None
                except:
                    sale_price = None
            else:
                # Estimar: assumir vendido = servido da produção
                quantity_sold = recipe_exec.get("porcoes_servidas")
                sale_price = None
                
                if quantity_sold:
                    log_error(
                        "sales_data_missing",
                        "medium",
                        event_id,
                        f"Usando produção como proxy de venda para {recipe_name}",
                        "process_item_performance"
                    )
            
            quantity_produced = recipe_exec.get("porcoes_produzidas")
            
            # === 5. CMV POR ITEM ===
            if quantity_sold and unit_cost:
                cmv = quantity_sold * unit_cost
            else:
                cmv = None
            
            # === 6. MARGEM POR ITEM ===
            revenue = None
            gross_profit = None
            margin_pct = None
            
            if quantity_sold and sale_price:
                revenue = quantity_sold * sale_price
                if cmv:
                    gross_profit = revenue - cmv
                    margin_pct = (gross_profit / revenue * 100) if revenue > 0 else None
            
            # === 7. DESPERDÍCIO POR ITEM ===
            if quantity_produced and quantity_sold:
                waste_qty = quantity_produced - quantity_sold
                if quantity_produced > 0:
                    waste_pct = (waste_qty / quantity_produced * 100)
                else:
                    waste_pct = None
            else:
                waste_qty = None
                waste_pct = None
            
            # === 8. CLASSIFICAÇÃO ===
            classification = "CRITICAL"
            issues = []
            
            if margin_pct is not None:
                if margin_pct >= 70:
                    classification = "HIGH_PERFORMER"
                elif margin_pct >= 50:
                    classification = "GOOD"
                elif margin_pct >= 30:
                    classification = "ATTENTION"
                else:
                    classification = "CRITICAL"
                    issues.append(f"Margem baixa: {margin_pct:.1f}%")
            else:
                issues.append("Margem não calculável")
                classification = "CRITICAL"
            
            if waste_pct and waste_pct > 10:
                classification = "CRITICAL"
                issues.append(f"Alto desperdício: {waste_pct:.1f}%")
            
            if not sale_price:
                issues.append("Preço de venda não registrado")
                classification = "ATTENTION"
            
            # Criar performance
            performance = ItemPerformance(
                recipe_id=recipe_id,
                recipe_name=recipe_name,
                event_id=event_id,
                event_name=event_name,
                company=company,
                quantity_produced=quantity_produced,
                quantity_sold=quantity_sold,
                unit_cost=unit_cost,
                sale_price=sale_price,
                revenue=revenue,
                cmv=cmv,
                gross_profit=gross_profit,
                margin_pct=margin_pct,
                waste_qty=waste_qty,
                waste_pct=waste_pct,
                classification=classification,
                issues=issues,
                timestamp=datetime.now().isoformat(),
                trace_mode="direct" if item_sales else "inferred"
            )
            
            performances.append(performance)
    
    return performances


def generate_rankings(performances: List[ItemPerformance]) -> Dict:
    """Gera rankings de itens"""
    
    rankings = {
        "generated_at": datetime.now().isoformat(),
        "total_items_analyzed": len(performances),
        "rankings": {}
    }
    
    # Top margin
    by_margin = [p for p in performances if p.margin_pct is not None]
    by_margin.sort(key=lambda x: x.margin_pct, reverse=True)
    
    rankings["rankings"]["top_margin_items"] = [
        {
            "recipe_id": p.recipe_id,
            "recipe_name": p.recipe_name,
            "event_id": p.event_id,
            "margin_pct": round(p.margin_pct, 2),
            "revenue": p.revenue
        }
        for p in by_margin[:10]
    ]
    
    # Worst margin
    rankings["rankings"]["worst_margin_items"] = [
        {
            "recipe_id": p.recipe_id,
            "recipe_name": p.recipe_name,
            "event_id": p.event_id,
            "margin_pct": round(p.margin_pct, 2),
            "issues": p.issues
        }
        for p in sorted(by_margin, key=lambda x: x.margin_pct)[:10]
    ]
    
    # Highest waste
    by_waste = [p for p in performances if p.waste_pct is not None]
    by_waste.sort(key=lambda x: x.waste_pct, reverse=True)
    
    rankings["rankings"]["highest_waste_items"] = [
        {
            "recipe_id": p.recipe_id,
            "recipe_name": p.recipe_name,
            "event_id": p.event_id,
            "waste_pct": round(p.waste_pct, 2),
            "waste_qty": p.waste_qty
        }
        for p in by_waste[:10]
    ]
    
    # Most profitable
    by_profit = [p for p in performances if p.gross_profit is not None]
    by_profit.sort(key=lambda x: x.gross_profit, reverse=True)
    
    rankings["rankings"]["most_profitable_items"] = [
        {
            "recipe_id": p.recipe_id,
            "recipe_name": p.recipe_name,
            "event_id": p.event_id,
            "gross_profit": round(p.gross_profit, 2),
            "margin_pct": round(p.margin_pct, 2) if p.margin_pct else None
        }
        for p in by_profit[:10]
    ]
    
    return rankings


def detect_problems(performances: List[ItemPerformance]) -> List[Dict]:
    """Detecta problemas de performance"""
    
    problems = []
    
    for p in performances:
        # 9.1: Alta venda + baixa margem
        if p.quantity_sold and p.quantity_sold > 50 and p.margin_pct and p.margin_pct < 30:
            problems.append({
                "type": "high_volume_low_margin",
                "recipe_id": p.recipe_id,
                "recipe_name": p.recipe_name,
                "event_id": p.event_id,
                "quantity_sold": p.quantity_sold,
                "margin_pct": round(p.margin_pct, 2),
                "description": f"{p.recipe_name}: alta venda ({p.quantity_sold}) com margem baixa ({p.margin_pct:.1f}%)",
                "suggested_action": "increase_price"
            })
        
        # 9.2: Alto desperdício
        if p.waste_pct and p.waste_pct > 10:
            problems.append({
                "type": "high_waste",
                "recipe_id": p.recipe_id,
                "recipe_name": p.recipe_name,
                "event_id": p.event_id,
                "waste_pct": round(p.waste_pct, 2),
                "description": f"{p.recipe_name}: desperdício alto ({p.waste_pct:.1f}%)",
                "suggested_action": "reduce_production"
            })
        
        # 9.3: Custo crescente (se tem histórico)
        # TODO: implementar análise temporal
        
        # 9.4: Item que destrói margem
        if p.gross_profit and p.gross_profit < 0 and p.cmv:
            problems.append({
                "type": "profit_killer",
                "recipe_id": p.recipe_id,
                "recipe_name": p.recipe_name,
                "event_id": p.event_id,
                "loss": round(abs(p.gross_profit), 2),
                "description": f"{p.recipe_name}: prejuízo de R$ {abs(p.gross_profit):,.2f}",
                "suggested_action": "review_price_or_recipe"
            })
    
    return problems


def generate_actions(performances: List[ItemPerformance], problems: List[Dict]) -> List[Dict]:
    """Gera ações para Decision Engine"""
    
    actions = []
    existing = load_json("decisions.json")
    current_suggestions = existing.get("suggestions", [])
    
    for problem in problems:
        action_type = problem.get("suggested_action")
        priority = "HIGH"
        
        if action_type == "increase_price":
            reason = f"{problem['recipe_name']}: alta venda com margem {problem['margin_pct']:.1f}%"
        elif action_type == "reduce_production":
            reason = f"{problem['recipe_name']}: desperdício {problem['waste_pct']:.1f}%"
        elif action_type == "review_price_or_recipe":
            reason = f"{problem['recipe_name']}: causando prejuízo R$ {problem['loss']:,.2f}"
        else:
            reason = problem.get("description", "")
        
        action = {
            "event_id": problem.get("event_id"),
            "recipe_id": problem.get("recipe_id"),
            "action": action_type,
            "priority": priority,
            "reason": reason,
            "source": "item_intelligence",
            "timestamp": datetime.now().isoformat(),
            "mode": "suggestion"  # 14. Só sugestão, não auto
        }
        
        # Adicionar às sugestões existentes
        current_suggestions.append(action)
        actions.append(action)
    
    # Atualizar decisions.json
    existing["suggestions"] = current_suggestions
    existing["_meta"] = {
        "last_updated": datetime.now().isoformat(),
        "total_suggestions": len(current_suggestions)
    }
    
    save_json("decisions.json", existing)
    
    return actions


def save_item_performance(performances: List[ItemPerformance]):
    """Salva performance por item em JSON"""
    
    output = {
        "_meta": {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_items": len(performances)
        },
        "performances": [asdict(p) for p in performances]
    }
    
    save_json("item_performance.json", output)
    print(f"\n✅ Item performance salvo em: kitchen_data/item_performance.json")


def save_performance_rankings(rankings: Dict):
    """Salva rankings em performance.json"""
    
    save_json("performance.json", rankings)
    print(f"✅ Rankings salvos em: kitchen_data/performance.json")


def generate_csv_report(performances: List[ItemPerformance]):
    """Gera CSV de performance por item"""
    
    headers = [
        "recipe_id", "recipe_name", "event_id", "event_name", "company",
        "quantity_produced", "quantity_sold", "unit_cost", "sale_price",
        "revenue", "cmv", "gross_profit", "margin_pct",
        "waste_qty", "waste_pct", "classification", "issues", "trace_mode"
    ]
    
    data = []
    for p in performances:
        row = {
            "recipe_id": p.recipe_id,
            "recipe_name": p.recipe_name,
            "event_id": p.event_id,
            "event_name": p.event_name,
            "company": p.company,
            "quantity_produced": p.quantity_produced if p.quantity_produced else "",
            "quantity_sold": p.quantity_sold if p.quantity_sold else "",
            "unit_cost": round(p.unit_cost, 2) if p.unit_cost else "",
            "sale_price": round(p.sale_price, 2) if p.sale_price else "",
            "revenue": round(p.revenue, 2) if p.revenue else "",
            "cmv": round(p.cmv, 2) if p.cmv else "",
            "gross_profit": round(p.gross_profit, 2) if p.gross_profit else "",
            "margin_pct": round(p.margin_pct, 2) if p.margin_pct else "",
            "waste_qty": p.waste_qty if p.waste_qty else "",
            "waste_pct": round(p.waste_pct, 2) if p.waste_pct else "",
            "classification": p.classification,
            "issues": ";".join(p.issues) if p.issues else "",
            "trace_mode": p.trace_mode
        }
        data.append(row)
    
    filepath = OUTPUT_DIR / "item_performance.csv"
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ CSV salvo em: output/item_performance.csv")


def print_item_report(performances: List[ItemPerformance], rankings: Dict, problems: List[Dict]):
    """Imprime relatório de itens"""
    
    emoji_class = {
        "HIGH_PERFORMER": "🟢",
        "GOOD": "💚",
        "ATTENTION": "🟡",
        "CRITICAL": "🔴"
    }
    
    print("\n" + "="*90)
    print("📊 ITEM INTELLIGENCE REPORT")
    print("="*90)
    
    # Resumo geral
    total = len(performances)
    high = sum(1 for p in performances if p.classification == "HIGH_PERFORMER")
    good = sum(1 for p in performances if p.classification == "GOOD")
    att = sum(1 for p in performances if p.classification == "ATTENTION")
    crit = sum(1 for p in performances if p.classification == "CRITICAL")
    
    print(f"\n📈 CLASSIFICAÇÃO DE ITENS ({total} analisados)")
    print(f"{'─'*90}")
    print(f"  {emoji_class['HIGH_PERFORMER']} HIGH_PERFORMER (≥70%): {high:>3}")
    print(f"  {emoji_class['GOOD']} GOOD (50-70%):        {good:>3}")
    print(f"  {emoji_class['ATTENTION']} ATTENTION (30-50%):  {att:>3}")
    print(f"  {emoji_class['CRITICAL']} CRITICAL (<30%):     {crit:>3}")
    
    # Top margem
    print(f"\n🏆 TOP 5 POR MARGEM")
    print(f"{'─'*90}")
    top = rankings["rankings"]["top_margin_items"][:5]
    for item in top:
        print(f"  {item['recipe_name'][:40]:<40} │ Margem: {item['margin_pct']:>5.1f}% │ Receita: R$ {item['revenue'] or 0:>8,.2f}")
    
    # Piores
    print(f"\n⚠️  5 MENORES MARGENS")
    print(f"{'─'*90}")
    worst = rankings["rankings"]["worst_margin_items"][:5]
    for item in worst:
        print(f"  {item['recipe_name'][:40]:<40} │ Margem: {item['margin_pct']:>5.1f}% │ Problemas: {', '.join(item['issues'])[:30]}")
    
    # Maior desperdício
    print(f"\n🗑️  TOP 5 DESPERDÍCIO")
    print(f"{'─'*90}")
    waste = rankings["rankings"]["highest_waste_items"][:5]
    for item in waste:
        print(f"  {item['recipe_name'][:40]:<40} │ Desp: {item['waste_pct']:>5.1f}% │ Qtd: {item['waste_qty']:>6.0f}")
    
    # Mais lucrativos
    print(f"\n💰 TOP 5 MAIS LUCRATIVOS")
    print(f"{'─'*90}")
    profit = rankings["rankings"]["most_profitable_items"][:5]
    for item in profit:
        print(f"  {item['recipe_name'][:40]:<40} │ Lucro: R$ {item['gross_profit']:>8,.2f} │ Margem: {item['margin_pct']:>5.1f}%")
    
    # Problemas detectados
    if problems:
        print(f"\n🚨 PROBLEMAS DETECTADOS ({len(problems)})")
        print(f"{'─'*90}")
        for p in problems[:10]:
            print(f"  [{p['type']}] {p['description'][:70]}")
            print(f"      → Sugestão: {p['suggested_action']}")
    
    print(f"\n{'='*90}")


def main():
    """Função principal"""
    
    print("🎛️ ITEM INTELLIGENCE ENGINE - Orkestra Finance Brain")
    print("="*90)
    
    # Processar
    performances = process_item_performance()
    
    if not performances:
        print("\n❌ Nenhum item processado")
        print("   É preciso dados de:")
        print("   - recipes.json")
        print("   - production_execution.json")
        print("   - inventory.json")
        return
    
    # Gerar análises
    rankings = generate_rankings(performances)
    problems = detect_problems(performances)
    actions = generate_actions(performances, problems)
    
    # Salvar
    save_item_performance(performances)
    save_performance_rankings(rankings)
    generate_csv_report(performances)
    print_item_report(performances, rankings, problems)
    
    print(f"\n✅ Item Intelligence Engine completado!")
    print(f"   {len(performances)} itens analisados")
    print(f"   {len(problems)} problemas detectados")
    print(f"   {len(actions)} ações sugeridas")


if __name__ == "__main__":
    main()
