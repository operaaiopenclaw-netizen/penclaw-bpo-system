#!/usr/bin/env python3
"""
Estima preços de ingredientes para mercado de Curitiba/PR via Claude API.
Usa conhecimento do modelo + contexto de mercado atacadista food service.

Uso:
  ANTHROPIC_API_KEY=sk-... python3 scripts/estimate_prices_curitiba.py

  Ou com Perplexity:
  PPLX_API_KEY=pplx-... python3 scripts/estimate_prices_curitiba.py --provider perplexity
"""

import os
import json
import csv
import sys
import time
import argparse
from pathlib import Path

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ── Ingredients extracted from FT Aniversário 15 anos Yohanna.xlsx ──────────
INGREDIENTS = [
    {"name": "Coxinha Cremosa", "qty": 300.0, "unit": "UN"},
    {"name": "Água Mineral", "qty": 225.0, "unit": "L"},
    {"name": "Mini Donuts", "qty": 150.0, "unit": "UN"},
    {"name": "Espeto Coalho", "qty": 100.0, "unit": "UN"},
    {"name": "Pão de Brioche Burger", "qty": 100.0, "unit": "UN"},
    {"name": "Pão de Hot Dog", "qty": 100.0, "unit": "UN"},
    {"name": "Água com Gás", "qty": 79.0, "unit": "L"},
    {"name": "Ovo", "qty": 67.0, "unit": "UN"},
    {"name": "Refrigerante", "qty": 45.0, "unit": "L"},
    {"name": "Leite", "qty": 43.5, "unit": "L"},
    {"name": "Óleo", "qty": 42.0, "unit": "L"},
    {"name": "Batata Palito Congelada", "qty": 30.0, "unit": "KG"},
    {"name": "Azeite", "qty": 21.5, "unit": "L"},
    {"name": "Iogurte Natural", "qty": 20.0, "unit": "UN"},
    {"name": "Creme de Leite", "qty": 19.5, "unit": "L"},
    {"name": "Queijo Mozzarella de Búfala", "qty": 15.0, "unit": "KG"},
    {"name": "Morango Fresco", "qty": 14.0, "unit": "KG"},
    {"name": "Leite Condensado", "qty": 13.0, "unit": "KG"},
    {"name": "Gelatina de Morango", "qty": 12.0, "unit": "UN"},
    {"name": "Gelatina de Limão", "qty": 12.0, "unit": "UN"},
    {"name": "Gelatina de Framboesa", "qty": 12.0, "unit": "UN"},
    {"name": "Gelatina de Uva", "qty": 12.0, "unit": "UN"},
    {"name": "Gelatina de Abacaxi", "qty": 12.0, "unit": "UN"},
    {"name": "Beterraba", "qty": 10.0, "unit": "KG"},
    {"name": "Sorvete de Chocolate", "qty": 10.0, "unit": "KG"},
    {"name": "Chocolate Meio Amargo", "qty": 9.5, "unit": "KG"},
    {"name": "Farinha de Trigo", "qty": 9.27, "unit": "KG"},
    {"name": "Farinha Panko", "qty": 9.0, "unit": "KG"},
    {"name": "Tomate Pelati", "qty": 8.4, "unit": "KG"},
    {"name": "Peito Bovino", "qty": 8.0, "unit": "KG"},
    {"name": "Tomate Cereja Vermelho", "qty": 7.5, "unit": "KG"},
    {"name": "Tomate Italiano", "qty": 7.0, "unit": "KG"},
    {"name": "Cebola Branca", "qty": 7.0, "unit": "KG"},
    {"name": "Macarrão Yaksoba", "qty": 7.0, "unit": "KG"},
    {"name": "Acém", "qty": 7.0, "unit": "KG"},
    {"name": "Cenoura", "qty": 6.3, "unit": "KG"},
    {"name": "Músculo Bovino", "qty": 6.0, "unit": "KG"},
    {"name": "Manga", "qty": 6.0, "unit": "KG"},
    {"name": "Salsinha", "qty": 5.3, "unit": "KG"},
    {"name": "Massa de Pastel", "qty": 5.0, "unit": "KG"},
    {"name": "Tahine", "qty": 4.9, "unit": "KG"},
    {"name": "Molho Shou", "qty": 4.6, "unit": "L"},
    {"name": "Carne Seca", "qty": 4.5, "unit": "KG"},
    {"name": "Grão de Bico", "qty": 4.4, "unit": "KG"},
    {"name": "Queijo Mozzarella", "qty": 4.0, "unit": "KG"},
    {"name": "Brócolis", "qty": 4.0, "unit": "KG"},
    {"name": "Sorvete Belga", "qty": 4.0, "unit": "KG"},
    {"name": "Sorvete Tutti Frutti", "qty": 4.0, "unit": "KG"},
    {"name": "Focaccia", "qty": 4.0, "unit": "KG"},
    {"name": "Brioche Amanteigado", "qty": 4.0, "unit": "KG"},
    {"name": "Manteiga", "qty": 3.9, "unit": "KG"},
    {"name": "Queijo Parmesão", "qty": 3.9, "unit": "KG"},
    {"name": "Clara Pasteurizada", "qty": 3.8, "unit": "L"},
    {"name": "Ervilha", "qty": 3.5, "unit": "KG"},
    {"name": "Laranja Bahia", "qty": 3.5, "unit": "KG"},
    {"name": "Tomate Cereja Amarelo", "qty": 3.5, "unit": "KG"},
    {"name": "Acelga", "qty": 3.5, "unit": "KG"},
    {"name": "Limão Tahiti", "qty": 3.215, "unit": "KG"},
    {"name": "Vinagre de Maçã", "qty": 3.0, "unit": "KG"},
    {"name": "Queijo Canastra", "qty": 3.0, "unit": "KG"},
    {"name": "Queijo Tulha", "qty": 3.0, "unit": "KG"},
    {"name": "Queijo Coalho", "qty": 3.0, "unit": "KG"},
    {"name": "Queijo Boursan", "qty": 3.0, "unit": "KG"},
    {"name": "Queijo do Reino", "qty": 3.0, "unit": "KG"},
    {"name": "Peito de Frango", "qty": 3.0, "unit": "KG"},
    {"name": "Queijo Cheddar", "qty": 3.0, "unit": "KG"},
    {"name": "Abacaxi", "qty": 3.0, "unit": "KG"},
    {"name": "Calda de Chocolate", "qty": 3.0, "unit": "L"},
    {"name": "Pão Folha", "qty": 3.0, "unit": "KG"},
    {"name": "Gohan", "qty": 3.0, "unit": "KG"},
    {"name": "Manjericão Fresco", "qty": 2.8, "unit": "KG"},
    {"name": "Lentilha", "qty": 2.5, "unit": "KG"},
    {"name": "Cogumelo Paris", "qty": 2.5, "unit": "KG"},
    {"name": "Cogumelo Porto Belo", "qty": 2.5, "unit": "KG"},
    {"name": "Torrada", "qty": 2.5, "unit": "KG"},
    {"name": "Grissini", "qty": 2.5, "unit": "KG"},
    {"name": "Açém", "qty": 2.4, "unit": "KG"},
    {"name": "Mel", "qty": 2.3, "unit": "KG"},
    {"name": "Sal", "qty": 2.255, "unit": "KG"},
    {"name": "Açúcar", "qty": 2.03, "unit": "KG"},
    {"name": "Alho", "qty": 2.02, "unit": "KG"},
    {"name": "Pepino", "qty": 2.0, "unit": "KG"},
    {"name": "Vinagre de Vinho Branco", "qty": 2.0, "unit": "L"},
    {"name": "Tomate Verde", "qty": 2.0, "unit": "KG"},
    {"name": "Azeite Balsâmico", "qty": 2.0, "unit": "KG"},
    {"name": "Burrata", "qty": 2.0, "unit": "KG"},
    {"name": "Stracciatella", "qty": 2.0, "unit": "KG"},
    {"name": "Massa Filo", "qty": 2.0, "unit": "KG"},
    {"name": "Fusilli", "qty": 2.0, "unit": "KG"},
    {"name": "Penne", "qty": 2.0, "unit": "KG"},
    {"name": "Raviolli", "qty": 2.0, "unit": "KG"},
    {"name": "Tortelli", "qty": 2.0, "unit": "KG"},
    {"name": "Sushi", "qty": 2.0, "unit": "KG"},
    {"name": "Nigiri", "qty": 2.0, "unit": "KG"},
    {"name": "Abobrinha Italiana", "qty": 2.0, "unit": "KG"},
    {"name": "Batata Doce", "qty": 2.0, "unit": "KG"},
    {"name": "Berinjela", "qty": 2.0, "unit": "KG"},
    {"name": "Molho Tarê", "qty": 2.0, "unit": "L"},
    {"name": "Balas Fini", "qty": 2.0, "unit": "KG"},
    {"name": "Uva Verde", "qty": 2.0, "unit": "KG"},
    {"name": "Pêssego", "qty": 2.0, "unit": "KG"},
    {"name": "Açúcar Mascavo", "qty": 1.9, "unit": "KG"},
    {"name": "Goiaba Cascão", "qty": 1.8, "unit": "KG"},
    {"name": "Trigo Sarraceno", "qty": 1.7, "unit": "KG"},
    {"name": "Páprica Defumada", "qty": 1.58, "unit": "KG"},
    {"name": "Quinoa Branca", "qty": 1.5, "unit": "KG"},
    {"name": "Quinoa Vermelha", "qty": 1.5, "unit": "KG"},
    {"name": "Parma Nacional", "qty": 1.5, "unit": "KG"},
    {"name": "Coppa Artesanal", "qty": 1.5, "unit": "KG"},
    {"name": "Lombo Curado", "qty": 1.5, "unit": "KG"},
    {"name": "Pancetta Defumada", "qty": 1.5, "unit": "KG"},
    {"name": "Linguiça Blumenal", "qty": 1.5, "unit": "KG"},
    {"name": "Salame Milano", "qty": 1.5, "unit": "KG"},
    {"name": "Requeijão", "qty": 1.5, "unit": "KG"},
    {"name": "Melaço de Cana", "qty": 1.5, "unit": "L"},
    {"name": "Sashimi Atum", "qty": 1.5, "unit": "KG"},
    {"name": "Sashimi Salmão", "qty": 1.5, "unit": "KG"},
    {"name": "Sashimi Peixe Branco", "qty": 1.5, "unit": "KG"},
    {"name": "Jois", "qty": 1.5, "unit": "KG"},
    {"name": "Mirtilo", "qty": 1.5, "unit": "KG"},
    {"name": "Pimenta Síria", "qty": 1.3, "unit": "KG"},
    {"name": "Pimenta do Reino", "qty": 1.29, "unit": "KG"},
    {"name": "Amido de Milho", "qty": 1.25, "unit": "KG"},
    {"name": "Hortelã Fresca", "qty": 1.2, "unit": "KG"},
    {"name": "Nozes", "qty": 1.2, "unit": "KG"},
    {"name": "Chocolate em Pó", "qty": 1.1, "unit": "KG"},
    {"name": "Gema Pasteurizada", "qty": 1.1, "unit": "L"},
    {"name": "Limão Siciliano", "qty": 1.0, "unit": "KG"},
    {"name": "Vinho Tinto", "qty": 1.0, "unit": "KG"},
    {"name": "Repolho", "qty": 1.0, "unit": "KG"},
    {"name": "Mostarda Amarela", "qty": 1.0, "unit": "KG"},
    {"name": "Cornichon", "qty": 1.0, "unit": "KG"},
    {"name": "Framboesa", "qty": 1.0, "unit": "KG"},
    {"name": "Baunilha Fava", "qty": 1.0, "unit": "UN"},
    {"name": "Cominho", "qty": 0.95, "unit": "KG"},
    {"name": "Leite em Pó", "qty": 0.7, "unit": "KG"},
    {"name": "Vinho Branco", "qty": 0.5, "unit": "L"},
    {"name": "Semente de Mostarda", "qty": 0.4, "unit": "KG"},
    {"name": "Cacau em Pó", "qty": 0.4, "unit": "KG"},
    {"name": "Semente de Abóbora", "qty": 0.3, "unit": "KG"},
    {"name": "Gelatina em Folha", "qty": 0.3, "unit": "KG"},
    {"name": "Madeira Defumação", "qty": 0.3, "unit": "KG"},
    {"name": "Óleo de Gergelim Torrado", "qty": 0.3, "unit": "L"},
    {"name": "Pasta de Gochujang", "qty": 0.3, "unit": "KG"},
    {"name": "Vinagre de Arroz", "qty": 0.3, "unit": "L"},
    {"name": "Salsão", "qty": 0.25, "unit": "KG"},
    {"name": "Tomilho", "qty": 0.22, "unit": "KG"},
    {"name": "Ciboulette", "qty": 0.2, "unit": "KG"},
    {"name": "Flor de Sal", "qty": 0.18, "unit": "KG"},
    {"name": "Wasabi em Pó", "qty": 0.12, "unit": "KG"},
    {"name": "Pimenta em Grãos", "qty": 0.11, "unit": "KG"},
    {"name": "Azedinha Mini Red", "qty": 0.05, "unit": "KG"},
    {"name": "Pimenta Calabresa", "qty": 0.05, "unit": "KG"},
    {"name": "Gelatina em Pó", "qty": 0.04, "unit": "KG"},
    {"name": "Gengibre", "qty": 0.03, "unit": "KG"},
    {"name": "Óleo de Gergelim", "qty": 0.03, "unit": "L"},
    {"name": "Pimenta do Reino Branca", "qty": 0.02, "unit": "KG"},
    {"name": "Bicarbonato de Sódio", "qty": 0.02, "unit": "KG"},
    {"name": "Fermento Químico", "qty": 0.02, "unit": "KG"},
    {"name": "Noz Moscada", "qty": 0.01, "unit": "KG"},
    {"name": "Louro", "qty": 0.01, "unit": "KG"},
    # Non-ingredients / equipment — skip in price calc
    {"name": "Equip. Cascata", "qty": 1.0, "unit": "UN"},
]

SYSTEM_PROMPT = """Você é um especialista em precificação de insumos para food service no Brasil.
Sua tarefa é estimar preços de compra no atacado/distribuidor para mercado de Curitiba/PR em abril de 2026.

Contexto:
- Cliente: empresa de catering/buffet em Curitiba
- Compra em atacadistas como MAKRO, Casa do Restaurante, distribuidores locais
- Volume: evento 150 pax (compras em quantidades intermediárias, não varejo nem ultra-atacado)
- Preços em R$ por unidade de medida indicada (KG, L, UN)

Responda APENAS com JSON válido no formato abaixo, sem texto adicional:
{
  "prices": [
    {"name": "Nome Ingrediente", "unit": "KG", "price_per_unit": 12.50, "confidence": "high|medium|low", "notes": "observação opcional"}
  ]
}

Confidence:
- high: produto comum, preço bem estabelecido
- medium: produto específico, variação moderada
- low: produto premium/importado/pouco comum, estimativa ampla
"""

def build_batch_prompt(batch: list[dict]) -> str:
    items = "\n".join(
        f"- {ing['name']} ({ing['unit']})"
        for ing in batch
        if ing['name'] != 'Equip. Cascata'
    )
    return f"""Estime o preço de compra no atacado (Curitiba/PR, abril 2026) para cada ingrediente abaixo.
Para itens de unidade UN (coxinha, mini donuts, pão, gelatina caixa), estime o preço POR UNIDADE.

Ingredientes:
{items}"""


def estimate_with_claude(ingredients: list[dict], api_key: str) -> list[dict]:
    client = anthropic.Anthropic(api_key=api_key)
    results = []

    # Filter out equipment
    items = [i for i in ingredients if i['name'] != 'Equip. Cascata']

    # Batch into groups of 25
    batch_size = 25
    batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]

    print(f"Consultando Claude em {len(batches)} batches ({len(items)} ingredientes)...")

    for idx, batch in enumerate(batches):
        print(f"  Batch {idx+1}/{len(batches)}: {[b['name'] for b in batch[:3]]}...")

        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_batch_prompt(batch)}]
        )

        text = response.content[0].text.strip()

        # Extract JSON if wrapped in markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)
            results.extend(data.get("prices", []))
        except json.JSONDecodeError as e:
            print(f"  ERRO parsing batch {idx+1}: {e}")
            print(f"  Response: {text[:200]}")

        # Rate limit pause
        if idx < len(batches) - 1:
            time.sleep(1)

    return results


def estimate_with_perplexity(ingredients: list[dict], api_key: str) -> list[dict]:
    items = [i for i in ingredients if i['name'] != 'Equip. Cascata']
    batch_size = 20
    batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]
    results = []

    print(f"Consultando Perplexity em {len(batches)} batches...")

    for idx, batch in enumerate(batches):
        print(f"  Batch {idx+1}/{len(batches)}...")

        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_batch_prompt(batch)}
            ],
            "max_tokens": 2000,
            "temperature": 0.1
        }

        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        resp.raise_for_status()

        text = resp.json()["choices"][0]["message"]["content"].strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)
            results.extend(data.get("prices", []))
        except json.JSONDecodeError as e:
            print(f"  ERRO parsing: {e}")

        if idx < len(batches) - 1:
            time.sleep(2)

    return results


def merge_prices_with_ingredients(ingredients: list[dict], prices: list[dict]) -> list[dict]:
    # Build price lookup by name (normalized)
    price_map = {p['name'].lower().strip(): p for p in prices}

    results = []
    for ing in ingredients:
        if ing['name'] == 'Equip. Cascata':
            continue

        key = ing['name'].lower().strip()
        price_info = price_map.get(key)

        # Try partial match if exact not found
        if not price_info:
            for pkey, pval in price_map.items():
                if ing['name'].lower() in pkey or pkey in ing['name'].lower():
                    price_info = pval
                    break

        price_per_unit = price_info['price_per_unit'] if price_info else 0.0
        confidence = price_info.get('confidence', 'unknown') if price_info else 'not_found'
        notes = price_info.get('notes', '') if price_info else 'Preço não encontrado'

        total_cost = ing['qty'] * price_per_unit

        results.append({
            "name": ing['name'],
            "qty": ing['qty'],
            "unit": ing['unit'],
            "price_per_unit": round(price_per_unit, 2),
            "total_cost": round(total_cost, 2),
            "confidence": confidence,
            "notes": notes
        })

    return results


def print_cmv_report(results: list[dict]) -> None:
    total_cost = sum(r['total_cost'] for r in results)
    not_found = [r for r in results if r['confidence'] == 'not_found']
    high_cost = sorted(results, key=lambda x: x['total_cost'], reverse=True)[:10]

    print("\n" + "="*60)
    print("  CMV - ANIVERSÁRIO 15 ANOS YOHANNA | 150 PAX")
    print("="*60)
    print(f"\n  CUSTO TOTAL DE INSUMOS: R$ {total_cost:,.2f}")
    print(f"  CUSTO POR PAX:          R$ {total_cost/150:,.2f}")
    print(f"\n  Ingredientes estimados: {len(results) - len(not_found)}/{len(results)}")

    if not_found:
        print(f"\n  ⚠ Sem preço ({len(not_found)}): {', '.join(r['name'] for r in not_found)}")

    print("\n  TOP 10 MAIOR CUSTO:")
    print(f"  {'Ingrediente':<35} {'Qtd':>8} {'Un':>4} {'R$/un':>8} {'Total':>10}")
    print("  " + "-"*68)
    for r in high_cost:
        print(f"  {r['name']:<35} {r['qty']:>8.2f} {r['unit']:>4} {r['price_per_unit']:>8.2f} {r['total_cost']:>10.2f}")

    print("\n" + "="*60)


def save_outputs(results: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = output_dir / "yohanna_cmv_estimate.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        total = sum(r['total_cost'] for r in results)
        json.dump({
            "event": "Aniversário 15 anos Yohanna",
            "pax": 150,
            "total_cost": round(total, 2),
            "cost_per_pax": round(total / 150, 2),
            "estimated_at": "2026-04-17",
            "market": "Curitiba/PR - Atacado/Food Service",
            "ingredients": results
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  Salvo: {json_path}")

    # CSV
    csv_path = output_dir / "yohanna_cmv_estimate.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'qty', 'unit', 'price_per_unit', 'total_cost', 'confidence', 'notes'])
        writer.writeheader()
        writer.writerows(results)
    print(f"  Salvo: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description='Estima preços de ingredientes para Curitiba')
    parser.add_argument('--provider', choices=['claude', 'perplexity'], default='claude',
                       help='Provedor de IA (default: claude)')
    parser.add_argument('--output', default='kitchen_data',
                       help='Diretório de saída (default: kitchen_data)')
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / args.output

    if args.provider == 'claude':
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("ERRO: ANTHROPIC_API_KEY não definida.")
            print("  Execute: ANTHROPIC_API_KEY=sk-ant-... python3 scripts/estimate_prices_curitiba.py")
            sys.exit(1)
        if not HAS_ANTHROPIC:
            print("ERRO: pip install anthropic")
            sys.exit(1)
        prices = estimate_with_claude(INGREDIENTS, api_key)

    elif args.provider == 'perplexity':
        api_key = os.environ.get('PPLX_API_KEY')
        if not api_key:
            print("ERRO: PPLX_API_KEY não definida.")
            print("  Execute: PPLX_API_KEY=pplx-... python3 scripts/estimate_prices_curitiba.py --provider perplexity")
            sys.exit(1)
        if not HAS_REQUESTS:
            print("ERRO: pip install requests")
            sys.exit(1)
        prices = estimate_with_perplexity(INGREDIENTS, api_key)

    print(f"\n  {len(prices)} preços obtidos.")

    results = merge_prices_with_ingredients(INGREDIENTS, prices)
    print_cmv_report(results)
    save_outputs(results, output_dir)

    print("\n  Próximo passo:")
    print("  → Revise kitchen_data/yohanna_cmv_estimate.json")
    print("  → Ajuste preços que ficaram distantes da realidade")
    print("  → Use o CSV para importar na ficha técnica")


if __name__ == '__main__':
    main()
