#!/usr/bin/env python3
"""
Extract Recipes from Excel - Orkestra Kitchen Supply Engine
Extrai fichas técnicas de planilhas Excel para JSON
"""

import pandas as pd
import json
import sys
from pathlib import Path

def classify_ingredient(ingrediente):
    """
    Classifica ingrediente por categoria nutricional.
    
    Args:
        ingrediente: Nome do ingrediente
    
    Returns:
        str: Categoria (proteina, carbo, laticinio, sobremesa, outros)
    """
    nome = ingrediente.lower()
    
    # Proteínas
    if any(x in nome for x in ["frango", "carne", "peixe", "picanha", "mignon", "costela", "calabresa", "linguiça", "bacon", "presunto", "salame", "atum", "salmão", "camarão"]):
        return "proteina"
    
    # Carboidratos
    if any(x in nome for x in ["arroz", "massa", "farinha", "pão", "pao", "batata", "mandioca", "polenta", "cuscuz", "pasta", "lasanha", "penne", "espaguete", "risoto"]):
        return "carbo"
    
    # Laticínios
    if any(x in nome for x in ["leite", "queijo", "mussarela", "parmesão", "requeijão", "creme", "manteiga", "iogurte", "coalhada", "catupiry"]):
        return "laticinio"
    
    # Sobremesa / Açúcares
    if any(x in nome for x in ["açucar", "acucar", "chocolate", "avelã", "avela", "morango", "frutas vermelhas", "coco", "canela", "baunilha", "gelatina", "panna cotta", "mousse", "brigadeiro", "doce"]):
        return "sobremesa"
    
    # Vegetais / Hortaliças
    if any(x in nome for x in ["alho", "cebola", "tomate", "cenoura", "pimentão", "cheiro verde", "salsa", "coentro", "manjericão", "orégano", "alface", "tomilho", "limão", "azeitona", "alcaparra"]):
        return "hortalicas"
    
    # Óleos / Gorduras
    if any(x in nome for x in ["azeite", "óleo", "oleo", "gordura", "margarina"]):
        return "oleos"
    
    return "outros"


def extract_recipes_from_excel(file_path, rendimento_padrao=100):
    """
    Extrai receitas de planilha Excel.
    
    Args:
        file_path: Caminho para arquivo Excel
        rendimento_padrao: Rendimento base da receita (padrão: 100 pessoas)
    
    Returns:
        dict: Estrutura de receitas formatada
    """
    print(f"📖 Lendo planilha: {file_path}")
    
    try:
        df = pd.read_excel(file_path, header=None)
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {file_path}")
        return None
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return None
    
    recipes = {}
    current_recipe = None
    
    print(f"📊 Processando {len(df)} linhas...")
    
    for idx, row in df.iterrows():
        # Coluna 0 = Nome do prato
        prato = str(row[0]).strip() if pd.notnull(row[0]) else ""
        
        # Detecta novo prato (não vazio, não 'nan', não 'total')
        if prato and prato.lower() not in ["nan", "total", "none", ""]:
            current_recipe = prato
            recipes[current_recipe] = {
                "rendimento": rendimento_padrao,
                "rendimento_obs": f"Base para {rendimento_padrao} pessoas",
                "ingredientes": [],
                "linha_origem": idx + 1
            }
            print(f"  🍽️  Encontrado: {prato}")
        
        # Se temos um prato ativo, extrai ingredientes
        if current_recipe and len(row) >= 4:
            ingrediente = str(row[1]).strip() if pd.notnull(row[1]) else ""
            quantidade = row[2] if pd.notnull(row[2]) else 0
            unidade = str(row[3]).strip() if pd.notnull(row[3]) else ""
            
            # Ignora linhas sem ingrediente válido
            if ingrediente and ingrediente.lower() not in ["nan", "none", "", "ingrediente"]:
                try:
                    qtd_float = float(quantidade)
                except (ValueError, TypeError):
                    qtd_float = 0
                
                recipes[current_recipe]["ingredientes"].append({
                    "nome": ingrediente,
                    "quantidade": qtd_float,
                    "unidade": unidade,
                    "categoria": classify_ingredient(ingrediente),
                    "linha": idx + 1
                })
    
    # Limpa receitas sem ingredientes
    recipes = {k: v for k, v in recipes.items() if v["ingredientes"]}
    
    print(f"\n✅ Total de receitas extraídas: {len(recipes)}")
    
    return {
        "metadata": {
            "arquivo_origem": str(file_path),
            "total_receitas": len(recipes),
            "rendimento_padrao": rendimento_padrao,
            "formato": "ficha_tecnica_orkestra_v1"
        },
        "recipes": recipes
    }


def salvar_recipes(data, output_file="recipes.json"):
    """Salva receitas em arquivo JSON."""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Salvo em: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extrai fichas técnicas de planilhas Excel para o Orkestra"
    )
    parser.add_argument("input", nargs="?", default="PEDIDO FORMATURA 1.xlsx",
                        help="Arquivo Excel de entrada (padrão: PEDIDO FORMATURA 1.xlsx)")
    parser.add_argument("-o", "--output", default="recipes.json",
                        help="Arquivo JSON de saída (padrão: recipes.json)")
    parser.add_argument("-r", "--rendimento", type=int, default=100,
                        help="Rendimento padrão das receitas (padrão: 100)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🍽️  KITCHEN_SUPPLY_ENGINE - Extract Recipes")
    print("=" * 60)
    
    # Extrai
    data = extract_recipes_from_excel(args.input, args.rendimento)
    
    if data:
        # Salva
        if salvar_recipes(data, args.output):
            print("\n📋 Resumo:")
            print(f"  • Receitas: {len(data['recipes'])}")
            total_ingredientes = sum(len(r['ingredientes']) for r in data['recipes'].values())
            print(f"  • Ingredientes totais: {total_ingredientes}")
            
            # Lista receitas
            print("\n  Receitas extraídas:")
            for nome, dados in data['recipes'].items():
                print(f"    - {nome}: {len(dados['ingredientes'])} ingredientes")
            
            print(f"\n🎛️  Pronto para integração com KITCHEN_SUPPLY_ENGINE")
        else:
            sys.exit(1)
    else:
        print("\n❌ Falha na extração")
        sys.exit(1)


if __name__ == "__main__":
    main()
