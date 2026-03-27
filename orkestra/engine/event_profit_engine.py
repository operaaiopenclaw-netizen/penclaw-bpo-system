# event_profit_engine.py - Orkestra Event Profit Engine
# Calcula lucro real por evento com métricas operacionais

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class Event:
    contract_id: str
    name: str
    date: str
    people: int
    revenue_locacao: float
    revenue_catering: float
    revenue_bar: float
    revenue_staff: float
    revenue_extras: float


@dataclass
class CostBreakdown:
    beverages: float
    food: float
    staff: float
    logistics: float
    total: float


class EventProfitEngine:
    """
    Motor de cálculo de lucro por evento.
    """
    
    # Métricas de consumo (por pessoa)
    BEVERAGE_METRICS = {
        "agua": {"liters_pp": 1.2, "cost_per_liter": 3.0},
        "cerveja": {"cans_pp": 2, "cost_per_can": 5.0},
        "refrigerante": {"liters_pp": 0.5, "cost_per_liter": 8.0},
        "suco": {"liters_pp": 0.3, "cost_per_liter": 12.0},
        "gelo": {"kg_pp": 1.6, "cost_per_kg": 2.5},
    }
    
    # Configurações
    FOOD_COST_PCT = 0.30  # 30% da receita de catering
    STAFF_COST_PCT = 0.15  # 15% da receita total
    LOGISTICS_COST_PCT = 0.08  # 8% da receita total
    
    def __init__(self):
        self.events: List[Event] = []
        self.results: List[Dict] = []
        
    def load_from_datasets(self):
        """Carrega eventos dos datasets 2024/2025."""
        for year in ["2024", "2025"]:
            path = Path(f"data/event_dataset_{year}.json")
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    for contract in data.get("contracts", []):
                        # Extrair número de pessoas do contrato ou default
                        people = 100  # default
                        try:
                            # Tentar extrair do contract_id ou notas
                            if "people" in contract.get("_raw", {}):
                                people = int(contract["_raw"]["people"])
                        except:
                            pass
                        
                        event = Event(
                            contract_id=contract.get("contract_id", "UNKNOWN"),
                            name=contract.get("contract_id", "UNKNOWN"),
                            date=contract.get("date", "2024-01-01"),
                            people=people,
                            revenue_locacao=contract.get("revenue_locacao", 0),
                            revenue_catering=contract.get("revenue_catering", 0),
                            revenue_bar=0,  # não separado no dataset
                            revenue_staff=0,
                            revenue_extras=0
                        )
                        self.events.append(event)
        
        print(f"✅ {len(self.events)} eventos carregados")
        return self
    
    def load_from_financial_log(self):
        """Carrega eventos do financial_log.json."""
        log_path = Path("financial_log.json")
        if log_path.exists():
            with open(log_path) as f:
                data = json.load(f)
                
            # Agrupar por evento
            events_data = {}
            for txn in data.get("transactions", []):
                event_name = txn.get("event", "UNKNOWN")
                if event_name not in events_data:
                    events_data[event_name] = {
                        "receita": 0,
                        "despesa": 0,
                        "people": txn.get("people", 100)
                    }
                
                if txn.get("type") == "income":
                    events_data[event_name]["receita"] += txn.get("value", 0)
                else:
                    events_data[event_name]["despesa"] += txn.get("value", 0)
            
            # Criar objetos Event
            for name, data in events_data.items():
                event = Event(
                    contract_id=name,
                    name=name,
                    date="2024-01-01",
                    people=data["people"],
                    revenue_locacao=data["receita"],
                    revenue_catering=0,
                    revenue_bar=0,
                    revenue_staff=0,
                    revenue_extras=0
                )
                self.events.append(event)
        
        return self
    
    def calculate_beverage_cost(self, event: Event) -> float:
        """
        Calcula custo de bebidas baseado nas métricas de consumo.
        """
        pax = event.people
        
        # Calcular item por item
        custo_agua = pax * self.BEVERAGE_METRICS["agua"]["liters_pp"] * self.BEVERAGE_METRICS["agua"]["cost_per_liter"]
        custo_cerveja = pax * self.BEVERAGE_METRICS["cerveja"]["cans_pp"] * self.BEVERAGE_METRICS["cerveja"]["cost_per_can"]
        custo_refrigerante = pax * self.BEVERAGE_METRICS["refrigerante"]["liters_pp"] * self.BEVERAGE_METRICS["refrigerante"]["cost_per_liter"]
        custo_suco = pax * self.BEVERAGE_METRICS["suco"]["liters_pp"] * self.BEVERAGE_METRICS["suco"]["cost_per_liter"]
        custo_gelo = pax * self.BEVERAGE_METRICS["gelo"]["kg_pp"] * self.BEVERAGE_METRICS["gelo"]["cost_per_kg"]
        
        total = custo_agua + custo_cerveja + custo_refrigerante + custo_suco + custo_gelo
        
        return total
    
    def calculate_food_cost(self, event: Event) -> float:
        """
        Calcula custo de food (30% da receita de catering).
        """
        # Base: 30% da receita de catering
        base_cost = event.revenue_catering * self.FOOD_COST_PCT
        
        # Ajuste por tipo de evento
        # Mais pessoas = economia de escala
        if event.people > 200:
            scale_factor = 0.95  # 5% desconto
        elif event.people > 100:
            scale_factor = 0.97  # 3% desconto
        else:
            scale_factor = 1.0
        
        return base_cost * scale_factor
    
    def calculate_staff_cost(self, event: Event) -> float:
        """
        Calcula custo de staff (proporcional à complexidade).
        """
        receita_total = (event.revenue_locacao + event.revenue_catering + 
                        event.revenue_bar + event.revenue_staff + event.revenue_extras)
        
        # Base: 15% da receita
        base_cost = receita_total * self.STAFF_COST_PCT
        
        # Ajuste por número de pessoas
        # Mais pessoas = mais staff necessário
        if event.people > 200:
            complexity_factor = 1.2
        elif event.people > 100:
            complexity_factor = 1.1
        else:
            complexity_factor = 1.0
        
        return base_cost * complexity_factor
    
    def calculate_logistics_cost(self, event: Event) -> float:
        """
        Calcula custo de logística.
        """
        receita_total = (event.revenue_locacao + event.revenue_catering + 
                        event.revenue_bar + event.revenue_staff + event.revenue_extras)
        
        return receita_total * self.LOGISTICS_COST_PCT
    
    def calculate_event_profit(self, event: Event) -> Dict:
        """
        Calcula lucro completo de um evento.
        """
        # RECEITA TOTAL
        receita = (event.revenue_locacao + event.revenue_catering + 
                   event.revenue_bar + event.revenue_staff + event.revenue_extras)
        
        # CUSTOS
        custo_bebidas = self.calculate_beverage_cost(event)
        custo_food = self.calculate_food_cost(event)
        custo_staff = self.calculate_staff_cost(event)
        custo_logistica = self.calculate_logistics_cost(event)
        
        cmv = custo_bebidas + custo_food  # Custo da mercadoria vendida
        custo_total = cmv + custo_staff + custo_logistica
        
        # LUCRO
        lucro = receita - custo_total
        margem = (lucro / receita) if receita > 0 else 0
        
        # Classificação
        if margem < 0:
            status = "❌ PREJUÍZO"
            icon = "❌"
        elif margem < 0.25:
            status = "⚠️ ABAIXO META"
            icon = "⚠️"
        elif margem < 0.35:
            status = "✅ SAUDÁVEL"
            icon = "✅"
        else:
            status = "🌟 EXCELENTE"
            icon = "🌟"
        
        return {
            "contract_id": event.contract_id,
            "name": event.name,
            "date": event.date,
            "people": event.people,
            "receita": round(receita, 2),
            "receita_per_capita": round(receita / event.people, 2) if event.people > 0 else 0,
            "custos": {
                "bebidas": round(custo_bebidas, 2),
                "food": round(custo_food, 2),
                "cmv": round(cmv, 2),
                "staff": round(custo_staff, 2),
                "logistica": round(custo_logistica, 2),
                "total": round(custo_total, 2)
            },
            "lucro": round(lucro, 2),
            "margem": round(margem, 4),
            "margem_pct": round(margem * 100, 2),
            "status": status,
            "icon": icon
        }
    
    def analyze_all(self) -> List[Dict]:
        """
        Analisa todos os eventos.
        """
        print("\n📊 Calculando lucros...")
        self.results = [self.calculate_event_profit(e) for e in self.events]
        return self.results
    
    def generate_insights(self) -> Dict:
        """
        Gera insights sobre os eventos.
        """
        if not self.results:
            return {}
        
        # Agrupar por status
        prejuizo = [r for r in self.results if r["margem"] < 0]
        abaixo_meta = [r for r in self.results if 0 <= r["margem"] < 0.25]
        saudaveis = [r for r in self.results if 0.25 <= r["margem"] < 0.35]
        excelentes = [r for r in self.results if r["margem"] >= 0.35]
        
        # Melhores e piores
        melhores = sorted(self.results, key=lambda x: x["margem"], reverse=True)[:5]
        piores = sorted(self.results, key=lambda x: x["margem"])[:5]
        
        # Estatísticas
        total_receita = sum(r["receita"] for r in self.results)
        total_custo = sum(r["custos"]["total"] for r in self.results)
        total_lucro = sum(r["lucro"] for r in self.results)
        margem_media = (total_lucro / total_receita) if total_receita > 0 else 0
        
        # Prejuízo total
        prejuizo_total = sum(r["lucro"] for r in prejuizo)
        
        # Recomendações
        recomendacoes = []
        
        if prejuizo:
            recomendacoes.append(f"🚨 {len(prejuizo)} eventos com prejuízo. Avaliar se reajustar preços ou cancelar.")
        
        if abaixo_meta:
            pct_abaixo = len(abaixo_meta) / len(self.results) * 100
            recomendacoes.append(f"⚠️ {len(abaixo_meta)} eventos ({pct_abaixo:.1f}%) abaixo de 25% margem. Revisar estrutura de custos.")
        
        if margem_media < 0.25:
            recomendacoes.append(f"📉 Margem média geral {margem_media*100:.1f}% abaixo do ideal (30%). Buscar aumento de 10% nos orçamentos.")
        
        if melhores:
            top_event = melhores[0]
            recomendacoes.append(f"💡 Melhor evento: {top_event['name']} com {top_event['margem_pct']}% margem. Analisar modelo para replicação.")
        
        # Métricas por tipo de evento (se houver dados)
        receita_per_capita_media = sum(r["receita_per_capita"] for r in self.results) / len(self.results) if self.results else 0
        
        return {
            "summary": {
                "total_eventos": len(self.results),
                "total_receita": round(total_receita, 2),
                "total_custo": round(total_custo, 2),
                "total_lucro": round(total_lucro, 2),
                "margem_media": round(margem_media * 100, 2),
                "receita_per_capita_media": round(receita_per_capita_media, 2),
                "prejuizo_total": round(prejuizo_total, 2)
            },
            "distribuicao": {
                "prejuizo": len(prejuizo),
                "abaixo_meta": len(abaixo_meta),
                "saudaveis": len(saudaveis),
                "excelentes": len(excelentes)
            },
            "melhores_eventos": melhores,
            "piores_eventos": piores,
            "eventos_prejuizo": prejuizo,
            "eventos_abaixo_25": abaixo_meta,
            "recomendacoes": recomendacoes
        }
    
    def print_report(self, insights: Dict):
        """Imprime relatório formatado."""
        print("\n" + "=" * 70)
        print("📊 ORKESTRA EVENT PROFIT ENGINE - RELATÓRIO")
        print("=" * 70)
        
        summary = insights["summary"]
        print(f"\n💰 RESUMO GERAL")
        print("-" * 70)
        print(f"   Total Eventos:      {summary['total_eventos']:>10}")
        print(f"   Receita Total:      R$ {summary['total_receita']:>10,.0f}")
        print(f"   Custo Total:        R$ {summary['total_custo']:>10,.0f}")
        print(f"   LUCRO TOTAL:        R$ {summary['total_lucro']:>10,.0f}")
        print(f"   Margem Média:          {summary['margem_media']:>10.1f}%")
        print(f"   Ticket Médio:       R$ {summary['receita_per_capita_media']:>10,.0f}/pessoa")
        
        if summary['prejuizo_total'] < 0:
            print(f"\n   ❌ PREJUÍZO TOTAL:  R$ {abs(summary['prejuizo_total']):,.0f}")
        
        print("\n" + "-" * 70)
        print("📈 DISTRIBUIÇÃO POR MARGEM")
        print("-" * 70)
        dist = insights["distribuicao"]
        for status, count in dist.items():
            icon = {"prejuizo": "❌", "abaixo_meta": "⚠️", "saudaveis": "✅", "excelentes": "🌟"}.get(status, "➡️")
            print(f"   {icon} {status.replace('_', ' ').title():<20}: {count:>5}")
        
        if insights["eventos_prejuizo"]:
            print("\n" + "-" * 70)
            print("🔴 EVENTOS COM PREJUÍZO")
            print("-" * 70)
            for evt in insights["eventos_prejuizo"][:3]:
                print(f"   ❌ {evt['name']}: Lucro R$ {evt['lucro']:,.0f} ({evt['margem_pct']}%)")
        
        if insights["eventos_abaixo_25"]:
            print("\n" + "-" * 70)
            print("⚠️  EVENTOS ABAIXO DE 25% MARGEM")
            print("-" * 70)
            for evt in insights["eventos_abaixo_25"][:5]:
                print(f"   ⚠️ {evt['name']}: Margem {evt['margem_pct']}%")
        
        if insights["melhores_eventos"]:
            print("\n" + "-" * 70)
            print("🌟 TOP 5 MELHORES EVENTOS")
            print("-" * 70)
            for i, evt in enumerate(insights["melhores_eventos"], 1):
                print(f"   {i}. {evt['name']}: Margem {evt['margem_pct']}% | Lucro R$ {evt['lucro']:,.0f}")
        
        print("\n" + "-" * 70)
        print("💡 RECOMENDAÇÕES DO SISTEMA")
        print("-" * 70)
        for rec in insights["recomendacoes"]:
            print(f"   {rec}")
        
        print("\n" + "=" * 70)
        
        # Tabela detalhada
        print("\n📋 DETALHAMENTO POR EVENTO")
        print("-" * 70)
        print(f"{'Evento':<25} {'Receita':>12} {'Custo':>12} {'Lucro':>12} {'Margem':>10}")
        print("-" * 70)
        for r in sorted(self.results, key=lambda x: x["margem"], reverse=True)[:10]:
            print(f"{r['name'][:25]:<25} R$ {r['receita']:>10,.0f} R$ {r['custos']['total']:>10,.0f} R$ {r['lucro']:>10,.0f} {r['margem_pct']:>9.1f}%")
        print("=" * 70)


def run_profit_analysis():
    """
    Executa análise completa de lucro por evento.
    """
    print("\n🚀 ORKESTRA EVENT PROFIT ENGINE")
    print("=" * 70)
    
    engine = EventProfitEngine()
    
    # Carregar dados
    print("\n📂 Carregando dados...")
    engine.load_from_datasets()
    engine.load_from_financial_log()
    
    if not engine.events:
        print("❌ Nenhum evento encontrado. Verifique os datasets.")
        return {}
    
    # Analisar
    results = engine.analyze_all()
    insights = engine.generate_insights()
    
    # Imprimir relatório
    engine.print_report(insights)
    
    # Salvar
    output = {
        "generated_at": datetime.now().isoformat(),
        "summary": insights["summary"],
        "distribuicao": insights["distribuicao"],
        "events": results,
        "insights": insights
    }
    
    output_path = Path("orkestra/memory/event_profit_report.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Relatório salvo: {output_path}")
    
    return insights


if __name__ == "__main__":
    run_profit_analysis()
