#!/usr/bin/env python3
"""
PROCUREMENT_SIMPLE - Orkestra MVP (Versão Leve)
Calcula previsão de compras baseada em eventos
"""

import json

def load_events():
    """Carrega eventos do estado Orkestra."""
    try:
        with open("orkestra-events-state.json", "r", encoding="utf-8") as f:
            return json.load(f).get("events", {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Erro ao carregar eventos: {e}")
        return {}

def estimate_procurement(events):
    """
    Estima compras baseado em métricas padronizadas:
    - Água: 1.2L por pessoa
    - Cerveja: 2 unidades por pessoa
    - Gelo: 1.6kg por pessoa / 6h
    """
    compras = {}
    
    for event_id, e in events.items():
        pessoas = e.get("pessoas", 100)
        duracao = e.get("duracao_horas", 6)
        
        # Cálculo base
        agua = pessoas * 1.2
        cerveja = pessoas * 2
        
        # Gelo proporcional à duração (base 6h)
        blocos_6h = duracao / 6
        gelo = (pessoas * 1.6) * blocos_6h
        
        compras[event_id] = {
            "nome": e.get("nome", event_id),
            "data": e.get("data", "N/A"),
            "pessoas": pessoas,
            "duracao_horas": duracao,
            "agua_L": round(agua, 1),
            "cerveja_un": round(cerveja),
            "gelo_kg": round(gelo, 1)
        }
    
    return compras


if __name__ == "__main__":
    print("=" * 60)
    print("📦 PROCUREMENT_SIMPLE - Orkestra MVP")
    print("=" * 60)
    
    events = load_events()
    
    if not events:
        print("\n❌ Nenhum evento encontrado em orkestra-events-state.json")
        print("   Adicione eventos manualmente ou execute email2orkestra.py")
        exit(1)
    
    print(f"\n📅 {len(events)} evento(s) carregado(s)")
    
    compras = estimate_procurement(events)
    
    print("\n" + "=" * 60)
    print("📦 PREVISÃO DE COMPRAS POR EVENTO:")
    print("=" * 60)
    
    for event_id, itens in compras.items():
        print(f"\n🎯 {itens['nome']}")
        print(f"   Data: {itens['data']}")
        print(f"   Público: {itens['pessoas']} pessoas")
        print(f"   Duração: {itens['duracao_horas']}h")
        print(f"   ├── Água: {itens['agua_L']} L")
        print(f"   ├── Cerveja: {itens['cerveja_un']} un")
        print(f"   └── Gelo: {itens['gelo_kg']} kg")
    
    # Consolidação
    total_agua = sum(c['agua_L'] for c in compras.values())
    total_cerveja = sum(c['cerveja_un'] for c in compras.values())
    total_gelo = sum(c['gelo_kg'] for c in compras.values())
    
    print("\n" + "=" * 60)
    print("📊 CONSOLIDAÇÃO TOTAL:")
    print("=" * 60)
    print(f"├── Água: {total_agua:.1f} L")
    print(f"├── Cerveja: {total_cerveja} unidades")
    print(f"└── Gelo: {total_gelo:.1f} kg")
    
    print("\n" + "=" * 60)
    print("✅ Previsão gerada com sucesso (modo SIMULAÇÃO)")
    print("⚠️  Regra: Nunca executar compras automaticamente")
    print("=" * 60)
