#!/usr/bin/env python3
"""
CEO DASHBOARD ENGINE
Visão estratégica consolidada do negócio para tomada de decisão executiva

Foco: KPIs estratégicos, rankings e tendências de alto nível
"""

import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from statistics import mean, median
from collections import defaultdict
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class CEOIndicator:
    name: str
    value: Any
    unit: str
    trend: str  # "up", "down", "stable", "alert"
    target: Optional[Any]
    status: str  # "good", "warning", "critical"
    context: str


class CEODashboardEngine:
    """Motor de geração de dashboard executivo"""
    
    def __init__(self):
        self.dashboard = {
            "_meta": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "period": "current",
                "disclaimer": "Dados consolidados para decisão estratégica"
            },
            "kpi_summary": {},
            "financial_performance": {},
            "operational_health": {},
            "strategic_insights": {},
            "rankings": {},
            "alerts": [],
            "timestamp": datetime.now().isoformat()
        }
    
    def load_csv(self, filename: str) -> List[Dict]:
        """Carrega CSV"""
        filepath = OUTPUT_DIR / filename
        if not filepath.exists():
            filepath = DATA_DIR / filename
        if not filepath.exists():
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    
    def load_json(self, filename: str) -> Dict:
        """Carrega JSON"""
        filepath = DATA_DIR / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def parse_float(self, value) -> Optional[float]:
        """Parser seguro de float"""
        try:
            if value is None or value == "":
                return None
            return float(value)
        except:
            return None
    
    def calculate_kpis(self):
        """
        PROCESSAMENTO PRINCIPAL
        Calcula todos os KPIs estratégicos
        """
        
        print("\n📊 CALCULANDO INDICADORES ESTRATÉGICOS...")
        
        # Carregar dados
        dre_data = self.load_csv("dre_events.csv")
        item_perf = self.load_json("item_performance.json").get("performances", [])
        audit_data = self.load_json("financial_audit.json")
        
        # === 1. KPIs FINANCEIROS ===
        
        if dre_data:
            # Receita total
            receitas = [self.parse_float(e.get("revenue_total")) for e in dre_data]
            receitas_validas = [r for r in receitas if r is not None]
            receita_total = sum(receitas_validas) if receitas_validas else 0
            
            # Lucro total (lucro líquido)
            lucros = [self.parse_float(e.get("net_profit")) for e in dre_data]
            lucros_validos = [l for l in lucros if l is not None]
            lucro_total = sum(lucros_validos) if lucros_validos else 0
            
            # Margem média
            margins = [self.parse_float(e.get("gross_margin")) for e in dre_data]
            margins_validas = [m for m in margins if m is not None]
            margem_media = mean(margins_validas) if margins_validas else 0
            
            # CMV total e médio
            cmvs = [self.parse_float(e.get("cmv_total")) for e in dre_data]
            cmvs_validos = [c for c in cmvs if c is not None]
            cmv_total = sum(cmvs_validos) if cmvs_validos else 0
            cmv_medio = cmv_total / len(cmvs_validos) if cmvs_validos else 0
            
            # % Eventos lucrativos
            eventos_lucrativos = sum(1 for l in lucros_validos if l > 0)
            eventos_prejuizo = sum(1 for l in lucros_validos if l < 0)
            total_eventos = len(lucros_validos)
            
            pct_lucrativos = (eventos_lucrativos / total_eventos * 100) if total_eventos else 0
            pct_prejuizo = (eventos_prejuizo / total_eventos * 100) if total_eventos else 0
        else:
            receita_total = lucro_total = margem_media = cmv_total = cmv_medio = 0
            eventos_lucrativos = eventos_prejuizo = total_eventos = 0
            pct_lucrativos = pct_prejuizo = 0
        
        # === 2. KPIs OPERACIONAIS ===
        
        if item_perf:
            # Desperdício médio
            waste_pcts = [p.get("waste_pct") for p in item_perf if p.get("waste_pct")]
            waste_total = [p.get("waste_qty") for p in item_perf if p.get("waste_qty")]
            
            desperdicio_medio_pct = mean(waste_pcts) if waste_pcts else 0
            total_desperdicio = sum(waste_total) if waste_total else 0
            
            # Volume total vendido
            volumes = [p.get("quantity_sold") for p in item_perf if p.get("quantity_sold")]
            volume_total = sum(volumes) if volumes else 0
            
            # Itens mais problemáticos
            itens_criticos = sum(1 for p in item_perf 
                                if (p.get("margin_pct") and p["margin_pct"] < 10) 
                                or (p.get("waste_pct") and p["waste_pct"] > 20))
            
            # Itens saudáveis
            itens_saudaveis = sum(1 for p in item_perf 
                                 if p.get("margin_pct") and p["margin_pct"] > 40 
                                 and (not p.get("waste_pct") or p["waste_pct"] < 10))
        else:
            desperdicio_medio_pct = total_desperdicio = volume_total = 0
            itens_criticos = itens_saudaveis = 0
        
        # === 3. SALVAR KPIs ===
        
        self.dashboard["kpi_summary"] = {
            "last_updated": datetime.now().isoformat(),
            "currency": "BRL",
            "indicators": [
                {
                    "kpi_id": "REV_TOTAL",
                    "name": "Receita Total",
                    "value": round(receita_total, 2),
                    "formatted": f"R$ {receita_total:,.2f}",
                    "unit": "reais",
                    "trend": "stable",
                    "target": None,
                    "status": "good" if receita_total > 0 else "warning",
                    "context": f"Receita consolidada de {total_eventos} eventos"
                },
                {
                    "kpi_id": "LUCRO_TOTAL",
                    "name": "Lucro Total",
                    "value": round(lucro_total, 2),
                    "formatted": f"R$ {lucro_total:,.2f}",
                    "unit": "reais",
                    "trend": "up" if lucro_total > 0 else "down",
                    "target": None,
                    "status": "good" if lucro_total > 0 else "critical",
                    "context": f"Lucro líquido após custos fixos"
                },
                {
                    "kpi_id": "MARGEM_MEDIA",
                    "name": "Margem Média",
                    "value": round(margem_media, 2),
                    "formatted": f"{margem_media:.1f}%",
                    "unit": "percentual",
                    "trend": "stable",
                    "target": 30.0,
                    "status": "good" if margem_media >= 30 else "warning" if margem_media >= 20 else "critical",
                    "context": "Margem bruta média dos eventos"
                },
                {
                    "kpi_id": "PCT_LUCRATIVOS",
                    "name": "% Eventos Lucrativos",
                    "value": round(pct_lucrativos, 2),
                    "formatted": f"{pct_lucrativos:.1f}%",
                    "unit": "percentual",
                    "trend": "stable",
                    "target": 80.0,
                    "status": "good" if pct_lucrativos >= 80 else "warning" if pct_lucrativos >= 60 else "critical",
                    "context": f"{eventos_lucrativos} de {total_eventos} eventos com lucro"
                },
                {
                    "kpi_id": "PCT_PREJUIZO",
                    "name": "% Eventos com Prejuízo",
                    "value": round(pct_prejuizo, 2),
                    "formatted": f"{pct_prejuizo:.1f}%",
                    "unit": "percentual",
                    "trend": "down" if pct_prejuizo > 0 else "stable",
                    "target": 0.0,
                    "status": "critical" if pct_prejuizo > 20 else "warning" if pct_prejuizo > 5 else "good",
                    "context": f"{eventos_prejuizo} eventos operando com prejuízo"
                },
                {
                    "kpi_id": "CMV_MEDIO",
                    "name": "CMV Médio por Evento",
                    "value": round(cmv_medio, 2),
                    "formatted": f"R$ {cmv_medio:,.2f}",
                    "unit": "reais",
                    "trend": "stable",
                    "target": None,
                    "status": "warning",
                    "context": f"Custo médio de mercadoria por evento"
                },
                {
                    "kpi_id": "DESPERDICIO_MEDIO",
                    "name": "Desperdício Médio",
                    "value": round(desperdicio_medio_pct, 2),
                    "formatted": f"{desperdicio_medio_pct:.1f}%",
                    "unit": "percentual",
                    "trend": "down",
                    "target": 5.0,
                    "status": "good" if desperdicio_medio_pct <= 5 else "warning" if desperdicio_medio_pct <= 10 else "critical",
                    "context": f"{total_desperdicio:.0f} unidades desperdiçadas no período"
                },
                {
                    "kpi_id": "ITENS_CRITICOS",
                    "name": "Itens em Estado Crítico",
                    "value": itens_criticos,
                    "formatted": str(itens_criticos),
                    "unit": "count",
                    "trend": "down",
                    "target": 0,
                    "status": "critical" if itens_criticos > 5 else "warning" if itens_criticos > 0 else "good",
                    "context": f"Itens com margem <10% ou desperdício >20%"
                },
                {
                    "kpi_id": "VOLUME_TOTAL",
                    "name": "Volume Total Vendido",
                    "value": round(volume_total, 0),
                    "formatted": f"{volume_total:,.0f}",
                    "unit": "unidades",
                    "trend": "up",
                    "target": None,
                    "status": "good" if volume_total > 0 else "warning",
                    "context": "Total de unidades vendidas no período"
                }
            ]
        }
        
        # Contextualização financeira
        if receita_total > 0:
            lucratividade = (lucro_total / receita_total) * 100
            eficiencia_operacional = ((receita_total - cmv_total) / receita_total) * 100 if receita_total > 0 else 0
        else:
            lucratividade = eficiencia_operacional = 0
        
        self.dashboard["financial_performance"] = {
            "receita_total": round(receita_total, 2),
            "lucro_total": round(lucro_total, 2),
            "cmv_total": round(cmv_total, 2),
            "lucratividade_liquida": round(lucratividade, 2),
            "eficiencia_operacional": round(eficiencia_operacional, 2),
            "eventos_analisados": total_eventos,
            "eventos_lucrativos": eventos_lucrativos,
            "eventos_prejuizo": eventos_prejuizo,
            "pct_lucrativos": round(pct_lucrativos, 2),
            "pct_prejuizo": round(pct_prejuizo, 2)
        }
        
        self.dashboard["operational_health"] = {
            "volume_total": round(volume_total, 0),
            "desperdicio_medio_pct": round(desperdicio_medio_pct, 2),
            "total_desperdicio_unidades": round(total_desperdicio, 0),
            "itens_criticos": itens_criticos,
            "itens_saudaveis": itens_saudaveis,
            "taxa_eficiencia": round(100 - desperdicio_medio_pct, 2)
        }
        
        print(f"   ✓ {len(self.dashboard['kpi_summary']['indicators'])} KPIs calculados")
    
    def generate_rankings(self):
        """
        RANKINGS
        - Top lucro
        - Top prejuízo
        - Top itens
        - Piores itens
        """
        
        print("\n📈 GERANDO RANKINGS...")
        
        dre_data = self.load_csv("dre_events.csv")
        item_perf = self.load_json("item_performance.json").get("performances", [])
        
        rankings = {}
        
        # 1. TOP LUCRO (eventos)
        if dre_data:
            lucros_eventos = []
            for e in dre_data:
                lucro = self.parse_float(e.get("net_profit"))
                if lucro is not None:
                    lucros_eventos.append({
                        "event_id": e.get("event_id", ""),
                        "company": e.get("company", ""),
                        "revenue": self.parse_float(e.get("revenue_total")) or 0,
                        "lucro": lucro,
                        "margin": self.parse_float(e.get("gross_margin")) or 0
                    })
            
            lucros_eventos.sort(key=lambda x: x["lucro"], reverse=True)
            rankings["top_lucro_eventos"] = lucros_eventos[:5]
            rankings["top_prejuizo_eventos"] = sorted(lucros_eventos, key=lambda x: x["lucro"])[:5]
        
        # 2. TOP ITENS (performance)
        if item_perf:
            # Por lucro
            by_profit = [p for p in item_perf if p.get("gross_profit")]
            by_profit.sort(key=lambda x: x["gross_profit"], reverse=True)
            
            rankings["top_itens_lucro"] = [
                {
                    "recipe_id": p["recipe_id"],
                    "recipe_name": p.get("recipe_name", ""),
                    "gross_profit": round(p["gross_profit"], 2),
                    "margin_pct": round(p.get("margin_pct", 0), 1),
                    "revenue": p.get("revenue", 0)
                }
                for p in by_profit[:10]
            ]
            
            # Por margem
            by_margin = [p for p in item_perf if p.get("margin_pct")]
            by_margin.sort(key=lambda x: x["margin_pct"], reverse=True)
            
            rankings["top_itens_margem"] = [
                {
                    "recipe_id": p["recipe_id"],
                    "recipe_name": p.get("recipe_name", ""),
                    "margin_pct": round(p["margin_pct"], 1),
                    "gross_profit": p.get("gross_profit", 0)
                }
                for p in by_margin[:10]
            ]
            
            # Piores (prejuízo)
            by_loss = [p for p in item_perf if p.get("gross_profit") and p["gross_profit"] < 0]
            by_loss.sort(key=lambda x: x["gross_profit"])
            
            rankings["piores_itens"] = [
                {
                    "recipe_id": p["recipe_id"],
                    "recipe_name": p.get("recipe_name", ""),
                    "prejuizo": round(abs(p["gross_profit"]), 2),
                    "margin_pct": round(p.get("margin_pct", 0), 1)
                }
                for p in by_loss[:10]
            ]
            
            # Mais vendidos
            by_volume = [p for p in item_perf if p.get("quantity_sold")]
            by_volume.sort(key=lambda x: x["quantity_sold"], reverse=True)
            
            rankings["mais_vendidos"] = [
                {
                    "recipe_id": p["recipe_id"],
                    "recipe_name": p.get("recipe_name", ""),
                    "quantity_sold": p["quantity_sold"],
                    "revenue": p.get("revenue", 0)
                }
                for p in by_volume[:10]
            ]
        
        self.dashboard["rankings"] = rankings
        
        total_rankings = sum(len(v) for v in rankings.values())
        print(f"   ✓ {total_rankings} rankings gerados")
    
    def generate_strategic_insights(self):
        """Gera insights estratégicos de alto nível"""
        
        print("\n💡 GERANDO INSIGHTS ESTRATÉGICOS...")
        
        insights = []
        alerts = []
        
        fp = self.dashboard.get("financial_performance", {})
        oh = self.dashboard.get("operational_health", {})
        kpis = self.dashboard.get("kpi_summary", {}).get("indicators", [])
        
        # Converter para dict por ID
        kpi_dict = {k["kpi_id"]: k for k in kpis}
        
        # Insight 1: Saúde Financeira
        pct_lucrativos = kpi_dict.get("PCT_LUCRATIVOS", {}).get("value", 0)
        margem_media = kpi_dict.get("MARGEM_MEDIA", {}).get("value", 0)
        
        if pct_lucrativos >= 80 and margem_media >= 30:
            status_financeiro = "SAUDAVEL"
            desc = f"Excelente performance: {pct_lucrativos:.0f}% eventos lucrativos com {margem_media:.1f}% margem média"
        elif pct_lucrativos >= 60:
            status_financeiro = "ATENCAO"
            desc = f"Performance aceitável mas com margem: {pct_lucrativos:.0f}% eventos lucrativos, margem em {margem_media:.1f}%"
            alerts.append({
                "level": "warning",
                "area": "financial",
                "message": f"Margem média {margem_media:.1f}% está abaixo do ideal (30%+)"
            })
        else:
            status_financeiro = "CRITICO"
            desc = f"Alerta: Apenas {pct_lucrativos:.0f}% eventos lucrativos"
            alerts.append({
                "level": "critical",
                "area": "financial",
                "message": f"Situação crítica: {100-pct_lucrativos:.0f}% eventos em prejuízo"
            })
        
        insights.append({
            "category": "financial_health",
            "status": status_financeiro,
            "description": desc,
            "recommendation": "Manter" if status_financeiro == "SAUDAVEL" else "Revisar precificação e custos"
        })
        
        # Insight 2: Eficiência Operacional
        desperdicio = oh.get("desperdicio_medio_pct", 0)
        
        if desperdicio <= 5:
            status_ops = "OTIMO"
            desc_ops = f"Operação otimizada: desperdício de {desperdicio:.1f}%"
        elif desperdicio <= 10:
            status_ops = "BOM"
            desc_ops = f"Operação aceitável: desperdício em {desperdicio:.1f}%"
        else:
            status_ops = "PREOCUPACAO"
            desc_ops = f"Desperdício alto: {desperdicio:.1f}% impactando resultados"
            alerts.append({
                "level": "warning" if desperdicio <= 15 else "critical",
                "area": "operational",
                "message": f"Desperdício de {desperdicio:.1f}% - revisar previsão de produção"
            })
        
        insights.append({
            "category": "operational_efficiency",
            "status": status_ops,
            "description": desc_ops,
            "recommendation": "Manter boas práticas" if status_ops in ["OTIMO", "BOM"] else "Revisar faturas técnicas"
        })
        
        # Insight 3: Portfolio
        itens_criticos = oh.get("itens_criticos", 0)
        
        if itens_criticos == 0:
            status_portfolio = "SAUDAVEL"
            desc_port = "Todos os itens em estado operacional aceitável"
        elif itens_criticos <= 3:
            status_portfolio = "ATENCAO"
            desc_port = f"{itens_criticos} itens requerem revisão de preço ou custo"
            alerts.append({
                "level": "warning",
                "area": "portfolio",
                "message": f"{itens_criticos} itens com margem ou desperdício crítico"
            })
        else:
            status_portfolio = "RISCO"
            desc_port = f"{itens_criticos} itens em estado crítico - revisão urgente necessária"
            alerts.append({
                "level": "critical",
                "area": "portfolio",
                "message": f"{itens_criticos} itens comprometidos - revisão estratégica do cardápio"
            })
        
        insights.append({
            "category": "portfolio_health",
            "status": status_portfolio,
            "description": desc_port,
            "recommendation": "Manter cardápio" if status_portfolio == "SAUDAVEL" else "Reformular itens problemáticos"
        })
        
        self.dashboard["strategic_insights"] = {
            "summary": insights,
            "status_geral": self._calculate_overall_status(status_financeiro, status_ops, status_portfolio),
            "alerts": alerts
        }
        
        self.dashboard["alerts"] = alerts
        
        print(f"   ✓ {len(insights)} insights estratégicos")
        print(f"   ✓ {len(alerts)} alertas gerados")
    
    def _calculate_overall_status(self, fin: str, ops: str, port: str) -> str:
        """Calcula status geral do negócio"""
        critical = sum([fin == "CRITICO", ops == "PREOCUPACAO", port == "RISCO"])
        warning = sum([fin == "ATENCAO", ops in ["PREOCUPACAO"] or port == "ATENCAO"])
        
        if critical >= 2:
            return "CRITICO - Acao imediata necessaria"
        elif critical >= 1 or warning >= 2:
            return "ATENCAO - Revisao prioritaria recomendada"
        elif warning >= 1:
            return "ESTAVEL - Melhorias pontuais possiveis"
        else:
            return "SAUDAVEL - Operacao dentro dos parametros"
    
    def save_dashboard(self):
        """Salva o dashboard em JSON"""
        
        filepath = DATA_DIR / "ceo_dashboard.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.dashboard, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Dashboard salvo em: kitchen_data/ceo_dashboard.json")
    
    def print_ceo_report(self):
        """Imprime relatório para CEO"""
        
        print("\n" + "="*80)
        print("📊 CEO DASHBOARD - VISAO ESTRATEGICA CONSOLIDADA")
        print("="*80)
        print("   Dados atualizados em:", self.dashboard["_meta"]["generated_at"][:10])
        
        # Status geral
        status = self.dashboard["strategic_insights"].get("status_geral", "INDEFINIDO")
        
        print(f"\n{'='*80}")
        if "SAUDAVEL" in status or "ESTAVEL" in status:
            print("✅ STATUS GERAL:", status)
        elif "ATENCAO" in status:
            print("⚠️  STATUS GERAL:", status)
        else:
            print("🚨 STATUS GERAL:", status)
        print(f"{'='*80}")
        
        # KPIs principais
        print("\n💰 FINANCIAL PERFORMANCE")
        print(f"{'─'*80}")
        
        fp = self.dashboard.get("financial_performance", {})
        print(f"   Receita Total:       R$ {fp.get('receita_total', 0):>12,.2f}")
        print(f"   Lucro Total:         R$ {fp.get('lucro_total', 0):>12,.2f}")
        print(f"   Lucratividade:       {fp.get('lucratividade_liquida', 0):>12.1f}%")
        print(f"   Margem Média:        {fp.get('margem_media', 0):>12.1f}%")
        print(f"   CMV Total:           R$ {fp.get('cmv_total', 0):>12,.2f}")
        print(f"\n   Eventos Analisados:  {fp.get('eventos_analisados', 0):>12}")
        print(f"   ✓ Lucrativos:        {fp.get('eventos_lucrativos', 0):>12} ({fp.get('pct_lucrativos', 0):.1f}%)")
        print(f"   ✗ Prejuízo:          {fp.get('eventos_prejuizo', 0):>12} ({fp.get('pct_prejuizo', 0):.1f}%)")
        
        # Operational Health
        print(f"\n⚙️  OPERATIONAL HEALTH")
        print(f"{'─'*80}")
        
        oh = self.dashboard.get("operational_health", {})
        print(f"   Volume Total:        {oh.get('volume_total', 0):>12,.0f} unidades")
        print(f"   Taxa Eficiência:       {oh.get('taxa_eficiencia', 0):>12.1f}%")
        print(f"   Desperdício:         {oh.get('desperdicio_medio_pct', 0):>12.1f}%")
        print(f"   Itens Críticos:      {oh.get('itens_criticos', 0):>12}")
        
        # Rankings
        rankings = self.dashboard.get("rankings", {})
        
        if rankings.get("top_lucro_eventos"):
            print(f"\n🏆 TOP 5 EVENTOS MAIS LUCRATIVOS")
            print(f"{'─'*80}")
            for i, e in enumerate(rankings["top_lucro_eventos"][:5], 1):
                print(f"   {i}. {e['event_id']:<12} │ Lucro: R$ {e['lucro']:>10,.2f} │ Margem: {e['margin']:>5.1f}%")
        
        if rankings.get("top_itens_lucro"):
            print(f"\n⭐ TOP 5 ITENS MAIS LUCRATIVOS")
            print(f"{'─'*80}")
            for i, item in enumerate(rankings["top_itens_lucro"][:5], 1):
                print(f"   {i}. {item['recipe_name'][:30]:<30} │ R$ {item['gross_profit']:>8,.2f}")
        
        # Insights
        insights = self.dashboard.get("strategic_insights", {}).get("summary", [])
        
        if insights:
            print(f"\n💡 INSIGHTS ESTRATÉGICOS")
            print(f"{'─'*80}")
            for ins in insights:
                emoji = {
                    "SAUDAVEL": "🟢", "SAUDAVEL": "🟢", "OTIMO": "🟢",
                    "BOM": "💚", "ATENCAO": "🟡", "RISCO": "🔴",
                    "CRITICO": "🚨"
                }.get(ins.get("status", ""), "⚪")
                print(f"\n   {emoji} [{ins['category'].upper()}] {ins['status']}")
                print(f"      {ins['description']}")
                print(f"      → {ins['recommendation']}")
        
        # Alerts
        alerts = self.dashboard.get("alerts", [])
        
        if alerts:
            print(f"\n🚨 ALERTAS EXIGEM ATENÇÃO ({len(alerts)})")
            print(f"{'─'*80}")
            for alert in alerts:
                emoji = {"critical": "🚨", "warning": "⚠️"}.get(alert["level"], "⚪")
                print(f"   {emoji} [{alert['area'].upper()}] {alert['message']}")
        
        print(f"\n{'='*80}")
        print("📈 Para detalhes completos, consulte ceo_dashboard.json")
        print(f"{'='*80}\n")


def main():
    """Função principal"""
    
    print("🎛️ CEO DASHBOARD ENGINE - Orkestra Finance Brain")
    print("="*80)
    print("\n📊 Gerando visão estratégica consolidada do negócio")
    print("   Para: Tomada de decisão executiva")
    
    engine = CEODashboardEngine()
    
    # Processar
    print("\n🔄 Processando dados...")
    
    engine.calculate_kpis()
    engine.generate_rankings()
    engine.generate_strategic_insights()
    
    # Salvar
    engine.save_dashboard()
    
    # Imprimir
    engine.print_ceo_report()
    
    print("✅ CEO Dashboard Engine completado!")


if __name__ == "__main__":
    main()
