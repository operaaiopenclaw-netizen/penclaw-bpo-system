#!/usr/bin/env python3
"""
PROCUREMENT_ENGINE | Orkestra MVP
Gerencia previsão de compras e provisionamento financeiro baseado em agenda de eventos.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# ============================================================
# MÉTRICAS BASE VALIDADAS (MVP)
# ============================================================
METRICAS_BASE = {
    "soft_corporativo": {
        "agua_1L": 1,  # 1L por pessoa
        "descricao": "Soft drinks e água para eventos corporativos"
    },
    "open_bar_universitario": {
        "agua_L": 1.2,  # 1,2L por pessoa
        "cerveja_latas": 2,  # 2 latas por pessoa
        "gelo_kg": 1.6,  # 1,6kg por pessoa / 6h
        "descricao": "Padrão open bar universitário"
    },
    "coffee_break": {
        "bebidas_L": 0.8,  # 0,8L por pessoa
        "descricao": "Café da manhã/coffee break"
    },
    "venda_alcool": {
        "fator_cerveja": 0.7,  # reduz cerveja
        "fator_soft": 1.3,  # aumenta soft
        "descricao": "Eventos com venda de álcool"
    }
}


# ============================================================
# DATA CLASSES
# ============================================================
@dataclass
class Evento:
    nome: str
    data: str  # YYYY-MM-DD
    tipo: str  # soft_corporativo, open_bar_universitario, coffee_break, etc
    pessoas: int
    duracao_horas: int
    servicos: List[str]  # buffet, bar, soft, coffee, etc
    observacoes: str = ""


@dataclass
class PrevisaoConsumo:
    evento: str
    categoria: str
    quantidade: float
    unidade: str
    origem_metrica: str


# ============================================================
# CLASSE PRINCIPAL
# ============================================================
class ProcurementEngine:
    """Motor de previsão de compras para eventos."""
    
    def __init__(self):
        self.eventos = []
        self.previsoes = []
        self.estoque = {}
        self.historico = {}
    
    def adicionar_evento(self, evento: Evento) -> Dict:
        """Adiciona evento e calcula consumo previsto."""
        self.eventos.append(evento)
        return self._calcular_previsao(evento)
    
    def _calcular_previsao(self, evento: Evento) -> Dict:
        """Calcula consumo previsto para um evento."""
        previsao = {
            "evento": evento.nome,
            "data": evento.data,
            "pessoas": evento.pessoas,
            "duracao_horas": evento.duracao_horas,
            "itens": []
        }
        
        # Calcula baseado no tipo do evento
        if evento.tipo in METRICAS_BASE:
            metricas = METRICAS_BASE[evento.tipo]
            
            if evento.tipo == "soft_corporativo":
                previsao["itens"].append({
                    "item": "Água 1L",
                    "quantidade": evento.pessoas * metricas["agua_1L"],
                    "unidade": "L",
                    "categoria": "bebida"
                })
            
            elif evento.tipo == "open_bar_universitario":
                # Água
                previsao["itens"].append({
                    "item": "Água (varios)",
                    "quantidade": evento.pessoas * metricas["agua_L"],
                    "unidade": "L",
                    "categoria": "bebida"
                })
                
                # Cerveja
                qtd_cerveja = evento.pessoas * metricas["cerveja_latas"]
                if "venda" in evento.observacoes.lower():
                    qtd_cerveja *= METRICAS_BASE["venda_alcool"]["fator_cerveja"]
                
                previsao["itens"].append({
                    "item": "Cerveja (latas)",
                    "quantidade": round(qtd_cerveja),
                    "unidade": "latas",
                    "categoria": "bebida"
                })
                
                # Gelo
                blocos_6h = evento.duracao_horas / 6
                qtd_gelo = evento.pessoas * metricas["gelo_kg"] * blocos_6h
                previsao["itens"].append({
                    "item": "Gelo",
                    "quantidade": round(qtd_gelo),
                    "unidade": "kg",
                    "categoria": "operacao"
                })
            
            elif evento.tipo == "coffee_break":
                previsao["itens"].append({
                    "item": "Bebidas (cafés/sucos)",
                    "quantidade": evento.pessoas * metricas["bebidas_L"],
                    "unidade": "L",
                    "categoria": "bebida"
                })
        
        return previsao
    
    def consolidar_semana(self, data_inicio: str) -> Dict:
        """Consolida previsões de uma semana."""
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = inicio + timedelta(days=7)
        
        eventos_semana = [
            e for e in self.eventos 
            if inicio <= datetime.strptime(e.data, "%Y-%m-%d") < fim
        ]
        
        if not eventos_semana:
            return {"status": "sem_eventos", "mensagem": "Nenhum evento na semana"}
        
        consolidacao = {
            "periodo": f"{data_inicio} a {(fim - timedelta(days=1)).strftime('%Y-%m-%d')}",
            "total_eventos": len(eventos_semana),
            "total_pessoas": sum(e.pessoas for e in eventos_semana),
            "itens_consolidados": {}
        }
        
        for evento in eventos_semana:
            previsao = self._calcular_previsao(evento)
            for item in previsao["itens"]:
                nome = item["item"]
                if nome not in consolidacao["itens_consolidados"]:
                    consolidacao["itens_consolidados"][nome] = {
                        "quantidade": 0,
                        "unidade": item["unidade"],
                        "categoria": item["categoria"]
                    }
                consolidacao["itens_consolidados"][nome]["quantidade"] += item["quantidade"]
        
        return consolidacao
    
    def gerar_lista_compras(self, data_inicio: str) -> Dict:
        """Gera lista de compras necessárias."""
        consolidacao = self.consolidar_semana(data_inicio)
        
        if "itens_consolidados" not in consolidacao:
            return consolidacao
        
        lista_compras = []
        for item, dados in consolidacao["itens_consolidados"].items():
            necessario = dados["quantidade"]
            estoque = self.estoque.get(item, 0)
            comprar = max(0, necessario - estoque)
            
            status = "OK" if comprar == 0 else "COMPRAR"
            
            lista_compras.append({
                "item": item,
                "necessario": necessario,
                "estoque": estoque,
                "comprar": comprar,
                "unidade": dados["unidade"],
                "categoria": dados["categoria"],
                "status": status
            })
        
        return {
            "periodo": consolidacao["periodo"],
            "itens": lista_compras
        }
    
    def estimar_custo(self, lista_compras: Dict, precos: Optional[Dict] = None) -> Dict:
        """Estima custo financeiro (se preços disponíveis)."""
        if not precos:
            return {
                "status": "sem_precos",
                "mensagem": "Informe preços unitários para calcular custo"
            }
        
        total = 0
        detalhamento = []
        
        for item in lista_compras.get("itens", []):
            preco_unit = precos.get(item["item"], 0)
            custo_item = item["comprar"] * preco_unit
            total += custo_item
            
            detalhamento.append({
                "item": item["item"],
                "quantidade": item["comprar"],
                "unidade": item["unidade"],
                "preco_unit": preco_unit,
                "custo_total": custo_item
            })
        
        return {
            "custo_total": total,
            "itens": detalhamento
        }
    
    def gerar_relatorio_completo(self, data_inicio: str, precos: Optional[Dict] = None) -> Dict:
        """Gera relatório completo de procurement."""
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        
        relatorio = {
            "data_geracao": datetime.now().isoformat(),
            "periodo": f"{data_inicio} a {(inicio + timedelta(days=6)).strftime('%Y-%m-%d')}",
            "status": "simulacao",
            "alertas": [],
            "secao_1_eventos": [],
            "secao_2_consolidacao": {},
            "secao_3_compras": [],
            "secao_4_financeiro": {}
        }
        
        # Verifica se há eventos
        eventos_semana = [
            e for e in self.eventos
            if inicio <= datetime.strptime(e.data, "%Y-%m-%d") < inicio + timedelta(days=7)
        ]
        
        if not eventos_semana:
            relatorio["alertas"].append({
                "tipo": "aviso",
                "mensagem": "Nenhum evento encontrado para a semana"
            })
            return relatorio
        
        # Seção 1: Eventos
        for evento in eventos_semana:
            previsao = self._calcular_previsao(evento)
            relatorio["secao_1_eventos"].append(previsao)
        
        # Seção 2: Consolidação
        relatorio["secao_2_consolidacao"] = self.consolidar_semana(data_inicio)
        
        # Seção 3: Compras
        lista = self.gerar_lista_compras(data_inicio)
        relatorio["secao_3_compras"] = lista
        
        # Seção 4: Financeiro
        if precos:
            financeiro = self.estimar_custo(lista, precos)
            relatorio["secao_4_financeiro"] = financeiro
        else:
            relatorio["secao_4_financeiro"] = {
                "status": "sem_precos",
                "mensagem": "Adicione precos para calcular provisionamento"
            }
            relatorio["alertas"].append({
                "tipo": "atencao",
                "mensagem": "Preços unitários não informados - custo não calculado"
            })
        
        return relatorio


def load_events():
    """Carrega eventos do estado Orkestra."""
    try:
        with open("orkestra-events-state.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("events", {})
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
    print("🎛️ PROCUREMENT_ENGINE - Orkestra MVP")
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
