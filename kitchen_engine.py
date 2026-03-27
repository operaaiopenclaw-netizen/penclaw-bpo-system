#!/usr/bin/env python3
"""
KITCHEN_ENGINE - Orkestra
Cálculo de consumo de cozinha baseado em fichas técnicas.
"""

import json

def load_recipes():
    """Carrega receitas do arquivo JSON."""
    try:
        with open("recipes.json", "r", encoding="utf-8") as f:
            return json.load(f).get("recipes", {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Erro ao carregar recipes.json: {e}")
        return {}

def calculate_event(menu, pax, recipes):
    """
    Calcula consumo para um evento baseado no menu e número de pessoas.
    
    Args:
        menu: Lista de nomes de pratos
        pax: Número de pessoas
        recipes: Dicionário de receitas
    
    Returns:
        Dicionário de ingredientes e quantidades totais
    """
    consumo = {}
    
    for prato in menu:
        r = recipes.get(prato)
        if not r:
            print(f"⚠️  Receita não encontrada: {prato}")
            continue
        
        # Calcula fator de escala
        rendimento = r.get("rendimento", 100)
        if rendimento == 0:
            print(f"⚠️  Rendimento zero para: {prato}")
            continue
            
        fator = pax / rendimento
        
        print(f"🍽️  {prato}: fator {fator:.2f} (pax {pax} / rendimento {rendimento})")
        
        # Multiplica ingredientes
        for ing in r.get("ingredientes", []):
            nome = ing.get("nome", "")
            qtd_base = ing.get("quantidade", 0)
            
            if nome and qtd_base > 0:
                qtd_total = qtd_base * fator
                consumo[nome] = consumo.get(nome, 0) + qtd_total
    
    return consumo

def calculate_cost(consumo, precos):
    """
    Calcula custo total baseado em preços unitários.
    
    Args:
        consumo: Dicionário de ingredientes e quantidades
        precos: Dicionário de preços unitários por ingrediente
    
    Returns:
        Custo total e detalhamento
    """
    total = 0
    detalhamento = []
    
    for ingrediente, qtd in consumo.items():
        preco_unit = precos.get(ingrediente, 0)
        if preco_unit == 0:
            print(f"⚠️  Preço não encontrado para: {ingrediente}")
        
        custo = qtd * preco_unit
        total += custo
        
        detalhamento.append({
            "ingrediente": ingrediente,
            "quantidade": round(qtd, 2),
            "preco_unit": preco_unit,
            "custo": round(custo, 2)
        })
    
    return {
        "custo_total": round(total, 2),
        "detalhamento": detalhamento
    }

if __name__ == "__main__":
    print("=" * 60)
    print("🍳 KITCHEN_ENGINE - Orkestra")
    print("=" * 60)
    
    # Carrega receitas
    recipes = load_recipes()
    
    if not recipes:
        print("\n❌ Nenhuma receita encontrada.")
        print("   Execute extract_recipes.py primeiro para gerar recipes.json")
        exit(1)
    
    print(f"\n📚 {len(recipes)} receita(s) carregada(s)")
    
    # Exemplo de menu
    menu = ["proteina_principal", "arroz_base"]
    pax = 300
    
    print(f"\n🎯 Evento: {pax} pessoas")
    print(f"📋 Menu: {', '.join(menu)}")
    
    # Calcula consumo
    consumo = calculate_event(menu, pax, recipes)
    
    print("\n" + "=" * 60)
    print("🥘 CONSUMO CALCULADO:")
    print("=" * 60)
    
    for ingrediente, qtd in sorted(consumo.items()):
        print(f"  {ingrediente:30} {qtd:8.2f}")
    
    # Exemplo de cálculo de custo (precos ficticios)
    precos_exemplo = {
        "frango desfiado": 12.50,
        "arroz": 3.20,
        "cebola": 2.80
    }
    
    print("\n" + "=" * 60)
    print("💰 CUSTO ESTIMADO:")
    print("=" * 60)
    
    custo = calculate_cost(consumo, precos_exemplo)
    
    for item in custo["detalhamento"]:
        print(f"  {item['ingrediente']:30} {item['quantidade']:8.2f} x R$ {item['preco_unit']:.2f} = R$ {item['custo']:.2f}")
    
    print(f"\n  {'CUSTO TOTAL':30} {'':8}   R$ {custo['custo_total']:.2f}")
    
    print("\n" + "=" * 60)
    print("✅ Cálculo concluído!")
    print("=" * 60)
