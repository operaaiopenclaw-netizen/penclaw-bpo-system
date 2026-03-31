#!/usr/bin/env python3
"""
MENU OPTIMIZATION ENGINE
Otimiza cardápio com matriz BCG adaptada

CLASSIFICAÇÃO:
- ⭐ ESTRELA: alta margem + alta venda
- 🐮 VACA LEITEIRA: alta margem + baixa venda  
- 🪤 ARMADILHA: baixa margem + alta venda
- ❌ PROBLEMA: baixa margem + baixa venda

AÇÕES:
- ESTRELA → promover, destacar no menu
- VACA LEITEIRA → aumentar marketing
- ARMADILHA → aumentar preço ou reduzir custo
- PROBLEMA → remover ou substituir
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# Limiares para classificação
THRESHOLDS = {
    "high_margin": 50.0,  # Margem acima de 50% = alta
    "high_volume": 30.0,   # Venda acima de 30 unidades = alta
    "margin": {
        "star": 60.0,
        "cow": 50.0,
        "trap": 40.0
    },
    "volume": {
        "star": 50.0,
        "cow": 20.0,
        "trap": 40.0
    }
}


class Classification(Enum):
    ESTRELA = "ESTRELA"
    VACA_LEITEIRA = "VACA_LEITEIRA"
    ARMADILHA = "ARMADILHA"
    PROBLEMA = "PROBLEMA"


@dataclass
class MenuStrategy:
    recipe_id: str
    recipe_name: str
    category: str
    avg_margin_pct: float
    total_quantity_sold: float
    total_revenue: float
    total_profit: float
    classification: str  # ESTRELA, VACA_LEITEIRA, ARMADILHA, PROBLEMA
    action: str
    priority: str
    reason: str
    suggestions: List[str]
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


def load_item_performance() -> List[Dict]:
    """Carrega performance de itens"""
    data = load_json("item_performance.json")
    return data.get("performances", [])


def aggregate_by_recipe(performances: List[Dict]) -> Dict[str, Dict]:
    """
    Agrega múltiplas performances do mesmo recipe_id
    
    Soma quantidade vendida, receita, lucro
    Média das margens ponderada por receita
    """
    aggregated = defaultdict(lambda: {
        "name": "",
        "category": "",
        "quantity_sold": 0.0,
        "revenue": 0.0,
        "profit": 0.0,
        "weighted_margin": 0.0,
        "count": 0,
        "events": []
    })
    
    for perf in performances:
        recipe_id = perf.get("recipe_id")
        if not recipe_id:
            continue
        
        qty = perf.get("quantity_sold") or 0
        revenue = perf.get("revenue") or 0
        profit = perf.get("gross_profit") or 0
        margin = perf.get("margin_pct") or 0
        
        agg = aggregated[recipe_id]
        agg["name"] = perf.get("recipe_name", recipe_id)
        agg["category"] = perf.get("category", "cozinha")
        agg["quantity_sold"] += qty
        agg["revenue"] += revenue
        agg["profit"] += profit
        
        # Margem ponderada
        if revenue > 0:
            agg["weighted_margin"] += margin * revenue
            agg["count"] += 1
            agg["events"].append(perf.get("event_id"))
    
    # Calcular média ponderada
    for recipe_id, data in aggregated.items():
        if data["revenue"] > 0 and data["count"] > 0:
            data["avg_margin_pct"] = data["weighted_margin"] / data["revenue"]
        else:
            data["avg_margin_pct"] = 0.0
    
    return aggregated


def classify_item(data: Dict) -> Tuple[str, str, List[str]]:
    """
    Classifica item na matriz BCG
    
    Retorna: (classificação, ação, sugestões)
    """
    margin = data.get("avg_margin_pct", 0)
    volume = data.get("quantity_sold", 0)
    revenue = data.get("revenue", 0)
    
    # Verificar se tem dados suficientes
    if margin == 0 or volume == 0:
        return "INSUFICIENTE", "aguardar_dados", ["Dados insuficientes para classificação"]
    
    # Classificar margem
    high_margin = margin >= THRESHOLDS["high_margin"]
    high_volume = volume >= THRESHOLDS["high_volume"]
    
    if high_margin and high_volume:
        # ⭐ ESTRELA
        return (
            "ESTRELA",
            "promover_e_destacar",
            [
                "Destacar no cardápio com foto e descrição premium",
                "Usar como carro-chefe de marketing",
                "Considerar bundle com itens complementares",
                "Manter qualidade e disponibilidade"
            ]
        )
    elif high_margin and not high_volume:
        # 🐮 VACA LEITEIRA
        return (
            "VACA_LEITEIRA",
            "aumentar_marketing",
            [
                "Criar campanha promocional específica",
                "Treinar equipe de vendas para sugerir",
                "Colocar em posição de destaque no cardápio",
                "Oferecer em degustação",
                "Criar pacote 'premium' com este item"
            ]
        )
    elif not high_margin and high_volume:
        # 🪤 ARMADILHA
        return (
            "ARMADILHA",
            "aumentar_preco_ou_reduzir_custo",
            [
                "Aumentar preço em 10-15% (alto volume aguenta)",
                "Revisar ficha técnica - reduzir insumos caros",
                "Negociar com fornecedor por volume",
                "Versão 'light' com custo menor",
                "Se não melhorar: considerar substituir"
            ]
        )
    else:
        # ❌ PROBLEMA
        return (
            "PROBLEMA",
            "remover_ou_substituir",
            [
                "Reformular receita completamente",
                "Substituir por alternativa mais lucrativa",
                "Se manter: usar como 'loss leader' estratégico",
                "Reduzir custo operacional (porções menores)",
                "Cortar do cardápio se não for estratégico"
            ]
        )


def determine_priority(classification: str, revenue: float) -> str:
    """Determina prioridade baseado na classificação e impacto financeiro"""
    
    if classification == "ESTRELA":
        return "MEDIUM"  # Manter, não é urgente
    elif classification == "VACA_LEITEIRA":
        return "HIGH"  # Alto potencial
    elif classification == "ARMADILHA":
        return "HIGH"  # Urgente - está queimando margem
    elif classification == "PROBLEMA":
        return "CRITICAL" if revenue > 5000 else "HIGH"
    else:
        return "LOW"


def process_menu_optimization() -> List[MenuStrategy]:
    """Processa otimização de cardápio"""
    
    print("\n🔍 Analisando performance do cardápio...")
    
    performances = load_item_performance()
    if not performances:
        print("❌ item_performance.json não encontrado. Execute item_intelligence_engine primeiro.")
        return []
    
    print(f"   ✓ {len(performances)} performances carregadas")
    
    # Agregar por receita
    aggregated = aggregate_by_recipe(performances)
    print(f"   ✓ {len(aggregated)} receitas únicas")
    
    strategies = []
    
    for recipe_id, data in aggregated.items():
        # Classificar
        classification, action, suggestions = classify_item(data)
        
        if classification == "INSUFICIENTE":
            continue
        
        # Determinar prioridade
        priority = determine_priority(classification, data.get("revenue", 0))
        
        # Criar estratégia
        strategy = MenuStrategy(
            recipe_id=recipe_id,
            recipe_name=data["name"],
            category=data["category"],
            avg_margin_pct=round(data["avg_margin_pct"], 2),
            total_quantity_sold=round(data["quantity_sold"], 2),
            total_revenue=round(data["revenue"], 2),
            total_profit=round(data["profit"], 2),
            classification=classification,
            action=action,
            priority=priority,
            reason=generate_reason(classification, data),
            suggestions=suggestions,
            timestamp=datetime.now().isoformat()
        )
        
        strategies.append(strategy)
    
    return strategies


def generate_reason(classification: str, data: Dict) -> str:
    """Gera explicação da classificação"""
    
    margin = data.get("avg_margin_pct", 0)
    volume = data.get("quantity_sold", 0)
    revenue = data.get("revenue", 0)
    
    if classification == "ESTRELA":
        return f"Alta margem ({margin:.1f}%) + Alto volume ({volume:.0f} vendas, R$ {revenue:,.2f})"
    elif classification == "VACA_LEITEIRA":
        return f"Alta margem ({margin:.1f}%) porém baixo volume ({volume:.0f} vendas)"
    elif classification == "ARMADILHA":
        return f"Alto volume ({volume:.0f} vendas, R$ {revenue:,.2f}) com margem baixa ({margin:.1f}%)"
    elif classification == "PROBLEMA":
        return f"Baixa margem ({margin:.1f}%) + Baixo volume ({volume:.0f} vendas)"
    else:
        return "Dados insuficientes"


def save_menu_strategy(strategies: List[MenuStrategy]):
    """Salva estratégia de cardápio"""
    
    output = {
        "_meta": {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_items": len(strategies),
            "methodology": "BCG Matrix Adaptada para Cardápio",
            "thresholds": THRESHOLDS,
            "breakdown": {
                "ESTRELA": sum(1 for s in strategies if s.classification == "ESTRELA"),
                "VACA_LEITEIRA": sum(1 for s in strategies if s.classification == "VACA_LEITEIRA"),
                "ARMADILHA": sum(1 for s in strategies if s.classification == "ARMADILHA"),
                "PROBLEMA": sum(1 for s in strategies if s.classification == "PROBLEMA")
            }
        },
        "strategies": [asdict(s) for s in strategies]
    }
    
    save_json("menu_strategy.json", output)
    print(f"\n✅ Estratégia salva em: kitchen_data/menu_strategy.json")


def generate_csv_report(strategies: List[MenuStrategy]):
    """Gera CSV de estratégia"""
    
    import csv
    
    headers = [
        "recipe_id", "recipe_name", "category", "classification",
        "avg_margin_pct", "total_quantity_sold", "total_revenue", "total_profit",
        "action", "priority", "reason", "suggestions"
    ]
    
    data = []
    for s in strategies:
        row = {
            "recipe_id": s.recipe_id,
            "recipe_name": s.recipe_name,
            "category": s.category,
            "classification": s.classification,
            "avg_margin_pct": s.avg_margin_pct,
            "total_quantity_sold": s.total_quantity_sold,
            "total_revenue": s.total_revenue,
            "total_profit": s.total_profit,
            "action": s.action,
            "priority": s.priority,
            "reason": s.reason,
            "suggestions": "; ".join(s.suggestions)
        }
        data.append(row)
    
    # Ordenar por prioridade
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    data.sort(key=lambda x: priority_order.get(x["priority"], 4))
    
    filepath = OUTPUT_DIR / "menu_strategy.csv"
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ CSV salvo em: output/menu_strategy.csv")


def print_matrix_report(strategies: List[MenuStrategy]):
    """Imprime relatório da matriz BCG"""
    
    print("\n" + "="*90)
    print("🎯 MENU OPTIMIZATION ENGINE REPORT")
    print("="*90)
    
    print("\n📊 MATRIZ BCG ADAPTADA")
    print("          │ Alta Margem        │ Baixa Margem")
    print("──────────┼────────────────────┼───────────────────")
    print("Alta Vol. │ ⭐ ESTRELA         │ 🪤 ARMADILHA")
    print("          │ Promover           │ Ajustar preço/custo")
    print("──────────┼────────────────────┼───────────────────")
    print("Baixa Vol.│ 🐮 VACA LEITEIRA   │ ❌ PROBLEMA")
    print("          │ Marketing          │ Remover/Substituir")
    print("──────────┴────────────────────┴───────────────────")
    
    # Separar por classificação
    estrelas = [s for s in strategies if s.classification == "ESTRELA"]
    vacas = [s for s in strategies if s.classification == "VACA_LEITEIRA"]
    armadilhas = [s for s in strategies if s.classification == "ARMADILHA"]
    problemas = [s for s in strategies if s.classification == "PROBLEMA"]
    
    # ⭐ ESTRELAS
    if estrelas:
        print(f"\n{'─'*90}")
        print(f"⭐ ESTRELAS ({len(estrelas)}) - Mantenha e Promova")
        print(f"{'─'*90}")
        print(f"   Itens com alta margem + alto volume")
        print(f"   Ação: Promover, Destacar, Carro-chefe\n")
        
        for s in estrelas:
            print(f"   {s.recipe_name}")
            print(f"      Margem: {s.avg_margin_pct:>5.1f}% | Vendas: {s.total_quantity_sold:>4.0f} | Receita: R$ {s.total_revenue:>8,.2f}")
            print(f"      → {s.suggestions[0] if s.suggestions else 'Manter qualidade'}")
    
    # 🐮 VACAS LEITEIRAS
    if vacas:
        print(f"\n{'─'*90}")
        print(f"🐮 VACAS LEITEIRAS ({len(vacas)}) - Potencial de Crescimento")
        print(f"{'─'*90}")
        print(f"   Itens com alta margem + baixo volume")
        print(f"   Ação: Aumentar marketing, Destacar no menu\n")
        
        for s in vacas:
            print(f"   {s.recipe_name}")
            print(f"      Margem: {s.avg_margin_pct:>5.1f}% | Vendas: {s.total_quantity_sold:>4.0f} | Prioridade: {s.priority}")
            print(f"      → {s.suggestions[0] if s.suggestions else 'Aumentar exposição'}")
    
    # 🪤 ARMADILHAS
    if armadilhas:
        print(f"\n{'─'*90}")
        print(f"🚨 ARMADILHAS ({len(armadilhas)}) - URGENTE!")
        print(f"{'─'*90}")
        print(f"   Itens com baixa margem + alto volume")
        print(f"   ⚠️  Estes itens estão QUEIMANDO margem do cardápio!")
        print(f"   Ação: Aumentar preço ou Reduzir custo\n")
        
        for s in armadilhas:
            print(f"   {s.recipe_name}")
            print(f"      Margem: {s.avg_margin_pct:>5.1f}% | Vendas: {s.total_quantity_sold:>4.0f} | Custo: R$ {s.total_revenue - s.total_profit:,.2f}")
            print(f"      🔥 Ação urgente: {s.suggestions[0] if s.suggestions else 'Revisar imediatamente'}")
    
    # ❌ PROBLEMAS
    if problemas:
        print(f"\n{'─'*90}")
        print(f"❌ PROBLEMAS ({len(problemas)}) - Revisar ou Remover")
        print(f"{'─'*90}")
        print(f"   Itens com baixa margem + baixo volume")
        print(f"   Ação: Remover ou Substituir\n")
        
        for s in problemas:
            print(f"   {s.recipe_name}")
            print(f"      Margem: {s.avg_margin_pct:>5.1f}% | Vendas: {s.total_quantity_sold:>4.0f}")
            print(f"      → {s.suggestions[0] if s.suggestions else 'Considerar corte'}")
    
    # Resumo
    print(f"\n{'='*90}")
    print("📈 RESUMO DA ANÁLISE")
    print(f"{'='*90}")
    print(f"  ⭐ Estrelas:        {len(estrelas):>3} (manter e promover)")
    print(f"  🐮 Vacas Leiteiras: {len(vacas):>3} (oportunidade de crescimento)")
    print(f"  🚨 Armadilhas:      {len(armadilhas):>3} (⚠️ URGENTE - ajustar)")
    print(f"  ❌ Problemas:       {len(problemas):>3} (revisar/remover)")
    print(f"  ────────────────────────────")
    print(f"  Total:             {len(strategies):>3} itens analisados")
    
    # Recomendação geral
    print(f"\n{'='*90}")
    print("💡 RECOMENDAÇÕES GERAIS")
    print(f"{'='*90}")
    
    total_revenue = sum(s.total_revenue for s in strategies)
    trap_revenue = sum(s.total_revenue for s in armadilhas)
    trap_impact = (trap_revenue / total_revenue * 100) if total_revenue else 0
    
    if armadilhas:
        print(f"   🚨 ATENÇÃO: {len(armadilhas)} ARMADILHAS geram R$ {trap_revenue:,.2f} ({trap_impact:.1f}% da receita total)")
        print(f"      Cada venda destes itens reduz margem do evento.")
        print(f"      Prioridade máxima: revisar preços e custos.")
    
    if vacas:
        print(f"\n   🐮 Potencial: {len(vacas)} VACAS LEITEIRAS com alta margem esperam marketing.")
        print(f"      Pequeno investimento em promoção pode dobrar volume.")
    
    if estrelas:
        print(f"\n   ⭐ {len(estrelas)} ESTRELAS são o core do seu negócio.")
        print(f"      Proteger qualidade e destacar sempre.")
    
    print(f"{'='*90}\n")


def main():
    """Função principal"""
    
    print("🎛️ MENU OPTIMIZATION ENGINE - Orkestra Finance Brain")
    print("="*90)
    print("\n📊 Analisando cardápio com Matriz BCG adaptada")
    print("   Classificação: ⭐🐮🚨❌")
    
    # Processar
    strategies = process_menu_optimization()
    
    if not strategies:
        print("\n❌ Nenhuma estratégia gerada")
        print("   Execute primeiro: item_intelligence_engine.py")
        return
    
    # Salvar
    save_menu_strategy(strategies)
    generate_csv_report(strategies)
    print_matrix_report(strategies)
    
    print(f"\n✅ Menu Optimization Engine completado!")
    print(f"   {len(strategies)} itens classificados")


if __name__ == "__main__":
    main()
