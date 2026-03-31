#!/usr/bin/env python3
"""
SALES DASHBOARD ENGINE
Otimiza performance comercial com base em margem real

Foco: Performance de vendas, ticket médio, conversão e alertas comerciais
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
class SalesKPI:
    name: str
    value: Any
    formatted: str
    benchmark: Optional[float]
    status: str  # "good", "warning", "critical"
    trend: str  # "up", "down", "stable"
    context: str


class SalesDashboardEngine:
    """Motor de dashboard comercial"""
    
    def __init__(self):
        self.dashboard = {
            "_meta": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "focus": "performance_comercial",
                "currency": "BRL"
            },
            "resumo_comercial": {},
            "kpis_vendas": [],
            "analise_eventos": {},
            "alertas_comerciais": [],
            "rankings": {},
            "tendencias": {},
            "recomendacoes": []
        }
    
    def load_csv(self, filename: str) -> List[Dict]:
        """Carrega CSV"""
        filepath = DATA_DIR / filename
        if not filepath.exists():
            filepath = OUTPUT_DIR / filename
        if not filepath.exists():
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    
    def parse_float(self, value) -> Optional[float]:
        """Parser seguro de float"""
        try:
            if value is None or value == "":
                return None
            return float(value)
        except:
            return None
    
    def parse_int(self, value) -> Optional[int]:
        """Parser seguro de int"""
        try:
            if value is None or value == "":
                return None
            return int(float(value))
        except:
            return None
    
    def calculate_sales_metrics(self):
        """
        1. MÉTRICAS PRINCIPAIS
        Calcula KPIs comerciais fundamentais
        """
        
        print("   📊 Calculando métricas de vendas...")
        
        events = self.load_csv("events_consolidated.csv")
        dre = self.load_csv("dre_events.csv")
        
        if not events:
            print("      ⚠️ Nenhum evento encontrado")
            return
        
        # Indexar DRE por event_id
        dre_by_event = {}
        for d in dre:
            event_id = d.get("event_id")
            if event_id:
                dre_by_event[event_id] = d
        
        # Métricas base
        total_eventos = len(events)
        
        receitas = [self.parse_float(e.get("revenue_total")) for e in events]
        receitas_validas = [r for r in receitas if r is not None and r > 0]
        
        # Ticket médio
        ticket_medio = mean(receitas_validas) if receitas_validas else 0
        ticket_mediano = median(receitas_validas) if receitas_validas else 0
        
        # Receita total
        receita_total = sum(receitas_validas) if receitas_validas else 0
        
        # Por status
        eventos_confirmados = [e for e in events if e.get("status") == "confirmed"]
        eventos_proposta = [e for e in events if e.get("status") == "proposal"]
        eventos_cancelados = [e for e in events if e.get("status") == "canceled"]
        
        # Análise de margem (de DRE)
        margins = []
        lucrativos = []
        prejuizo = []
        
        for event_id, d in dre_by_event.items():
            margin = self.parse_float(d.get("gross_margin"))
            lucro = self.parse_float(d.get("net_profit"))
            
            if margin is not None:
                margins.append(margin)
                if lucro is not None:
                    if lucro > 0:
                        lucrativos.append(event_id)
                    elif lucro < 0:
                        prejuizo.append(event_id)
        
        margem_media = mean(margins) if margins else 0
        margem_mediana = median(margins) if margins else 0
        
        # Taxa de lucratividade
        pct_lucrativos = (len(lucrativos) / len(margins) * 100) if margins else 0
        pct_prejuizo = (len(prejuizo) / len(margins) * 100) if margins else 0
        
        # Por empresa
        by_company = defaultdict(lambda: {"count": 0, "revenue": 0, "margin": []})
        for e in events:
            company = e.get("company", "nao_identificado")
            by_company[company]["count"] += 1
            
            rev = self.parse_float(e.get("revenue_total"))
            if rev:
                by_company[company]["revenue"] += rev
            
            # Buscar margem no DRE
            event_id = e.get("event_id")
            if event_id in dre_by_event:
                m = self.parse_float(dre_by_event[event_id].get("gross_margin"))
                if m is not None:
                    by_company[company]["margin"].append(m)
        
        # Ticket médio por empresa
        for company, data in by_company.items():
            if data["count"] > 0:
                data["ticket_medio"] = data["revenue"] / data["count"]
                data["margem_media"] = mean(data["margin"]) if data["margin"] else 0
        
        # 2. DETECTAR: Eventos vendidos com baixa margem
        eventos_baixa_margem = []
        eventos_risco = []
        
        for event_id, d in dre_by_event.items():
            margin = self.parse_float(d.get("gross_margin"))
            receita = self.parse_float(d.get("revenue_total"))
            
            if margin is not None:
                # Baixa margem (< 20%)
                if margin < 20:
                    eventos_baixa_margem.append({
                        "event_id": event_id,
                        "revenue": receita,
                        "margin": margin,
                        "motivo": "Margem abaixo de 20%",
                        "acao": "Revisar preço ou reduzir custo"
                    })
                
                # Risco: margem negativa ou < 10%
                if margin < 10:
                    eventos_risco.append({
                        "event_id": event_id,
                        "revenue": receita,
                        "margin": margin,
                        "motivo": "Margem crítica (< 10%)",
                        "acao": "URGENTE: Revisar orçamento"
                    })
        
        # Ordenar por risco (menor margem primeiro)
        eventos_baixa_margem.sort(key=lambda x: x["margin"])
        eventos_risco.sort(key=lambda x: x["margin"])
        
        # Salvar no dashboard
        self.dashboard["resumo_comercial"] = {
            "total_eventos": total_eventos,
            "receita_total": round(receita_total, 2),
            "receita_formatada": f"R$ {receita_total:,.2f}",
            "ticket_medio": round(ticket_medio, 2),
            "ticket_medio_formatado": f"R$ {ticket_medio:,.2f}",
            "ticket_mediano": round(ticket_mediano, 2),
            "eventos_confirmados": len(eventos_confirmados),
            "eventos_proposta": len(eventos_proposta),
            "eventos_cancelados": len(eventos_cancelados),
            "taxa_confirmacao": round(len(eventos_confirmados) / total_eventos * 100, 1) if total_eventos else 0,
            "margem_media": round(margem_media, 2),
            "margem_mediana": round(margem_mediana, 2),
            "pct_lucrativos": round(pct_lucrativos, 1),
            "pct_prejuizo": round(pct_prejuizo, 1),
            "eventos_lucrativos": len(lucrativos),
            "eventos_prejuizo": len(prejuizo)
        }
        
        self.dashboard["analise_por_empresa"] = {
            company: {
                "eventos": data["count"],
                "receita": round(data["revenue"], 2),
                "ticket_medio": round(data.get("ticket_medio", 0), 2),
                "margem_media": round(data.get("margem_media", 0), 2)
            }
            for company, data in by_company.items()
        }
        
        self.dashboard["alertas_comerciais"] = {
            "eventos_baixa_margem": eventos_baixa_margem[:10],  # Top 10
            "eventos_risco": eventos_risco[:10],
            "total_baixa_margem": len(eventos_baixa_margem),
            "total_risco": len(eventos_risco),
            "pct_eventos_em_risco": round(len(eventos_risco) / total_eventos * 100, 1) if total_eventos else 0
        }
        
        print(f"      ✓ {total_eventos} eventos analisados")
        print(f"      ✓ Ticket médio: R$ {ticket_medio:,.2f}")
        print(f"      ✓ Margem média: {margem_media:.1f}%")
        
        if eventos_risco:
            print(f"      🚨 {len(eventos_risco)} eventos em risco!" if isinstance(eventos_risco, list) else f"      🚨 {len(eventos_risco)} eventos em risco!")
    
    def calculate_advanced_kpis(self):
        """
        KPIs Avançados
        """
        
        print("   🎯 Calculando KPIs avançados...")
        
        resumo = self.dashboard.get("resumo_comercial", {})
        
        # 1. Eficiência Comercial
        taxa_confirmacao = resumo.get("taxa_confirmacao", 0)
        if taxa_confirmacao >= 80:
            eficiencia = "OTIMA"
            status = "good"
        elif taxa_confirmacao >= 60:
            eficiencia = "BOA"
            status = "good"
        elif taxa_confirmacao >= 40:
            eficiencia = "ACEITAVEL"
            status = "warning"
        else:
            eficiencia = "BAIXA"
            status = "critical"
        
        # 2. Saúde de Margem
        margem = resumo.get("margem_media", 0)
        if margem >= 35:
            saude_margem = "SAUDAVEL"
            m_status = "good"
        elif margem >= 25:
            saude_margem = "ACEITAVEL"
            m_status = "good"
        elif margem >= 15:
            saude_margem = "ATENCAO"
            m_status = "warning"
        else:
            saude_margem = "CRITICA"
            m_status = "critical"
        
        # 3. Ticket Médio vs Meta
        ticket = resumo.get("ticket_medio", 0)
        meta = 20000  # Meta exemplo
        if ticket >= meta * 1.2:
            ticket_status = "good"
            ticket_trend = "up"
        elif ticket >= meta:
            ticket_status = "good"
            ticket_trend = "stable"
        else:
            ticket_status = "warning"
            ticket_trend = "down"
        
        self.dashboard["kpis_vendas"] = [
            {
                "kpi_id": "EFICIENCIA_COMERCIAL",
                "nome": "Eficiência Comercial",
                "valor": taxa_confirmacao,
                "formatado": f"{taxa_confirmacao:.1f}%",
                "status": status,
                "classificacao": eficiencia,
                "meta": 70,
                "contexto": f"{resumo.get('eventos_confirmados', 0)} de {resumo.get('total_eventos', 0)} eventos confirmados"
            },
            {
                "kpi_id": "SAUDE_MARGEM",
                "nome": "Saúde da Margem",
                "valor": margem,
                "formatado": f"{margem:.1f}%",
                "status": m_status,
                "classificacao": saude_margem,
                "meta": 30,
                "contexto": f"Média de margem bruta nos eventos"
            },
            {
                "kpi_id": "TICKET_MEDIO",
                "nome": "Ticket Médio",
                "valor": resumo.get("ticket_medio", 0),
                "formatado": f"R$ {resumo.get('ticket_medio', 0):,.2f}",
                "status": ticket_status,
                "trend": ticket_trend,
                "meta": meta,
                "contexto": f"Mediana: R$ {resumo.get('ticket_mediano', 0):,.2f}"
            },
            {
                "kpi_id": "TAXA_LUCRATIVIDADE",
                "nome": "Taxa de Lucratividade",
                "valor": resumo.get("pct_lucrativos", 0),
                "formatado": f"{resumo.get('pct_lucrativos', 0):.1f}%",
                "status": "good" if resumo.get("pct_lucrativos", 0) >= 80 else "warning" if resumo.get("pct_lucrativos", 0) >= 60 else "critical",
                "meta": 80,
                "contexto": f"{resumo.get('eventos_lucrativos', 0)} eventos com lucro"
            },
            {
                "kpi_id": "RECEITA_POR_EVENTO",
                "nome": "Receita Média/Evento",
                "valor": resumo.get("receita_total", 0) / resumo.get("total_eventos", 1) if resumo.get("total_eventos") else 0,
                "formatado": f"R$ {(resumo.get('receita_total', 0) / resumo.get('total_eventos', 1) if resumo.get('total_eventos') else 0):,.2f}",
                "status": "stable",
                "contexto": f"Total: R$ {resumo.get('receita_total', 0):,.2f}"
            }
        ]
        
        print(f"      ✓ {len(self.dashboard['kpis_vendas'])} KPIs calculados")
    
    def generate_rankings(self):
        """
        Rankings comerciais
        """
        
        print("   🏆 Gerando rankings...")
        
        events = self.load_csv("events_consolidated.csv")
        dre = self.load_csv("dre_events.csv")
        
        # Indexar DRE
        dre_by_event = {}
        event_company = {}
        
        for d in dre:
            event_id = d.get("event_id")
            if event_id:
                dre_by_event[event_id] = d
        
        for e in events:
            event_company[e.get("event_id")] = e.get("company", "")
        
        # Eventos por receita
        events_by_revenue = []
        for e in events:
            event_id = e.get("event_id")
            rev = self.parse_float(e.get("revenue_total"))
            
            if rev:
                # Buscar margem
                margin = None
                if event_id in dre_by_event:
                    margin = self.parse_float(dre_by_event[event_id].get("gross_margin"))
                
                events_by_revenue.append({
                    "event_id": event_id,
                    "cliente": e.get("client_name", ""),
                    "revenue": rev,
                    "margin": margin,
                    "company": event_company.get(event_id, "")
                })
        
        events_by_revenue.sort(key=lambda x: x["revenue"], reverse=True)
        
        # Eventos por lucro (de DRE)
        events_by_profit = []
        for event_id, d in dre_by_event.items():
            profit = self.parse_float(d.get("net_profit"))
            receita = self.parse_float(d.get("revenue_total"))
            margin = self.parse_float(d.get("gross_margin"))
            
            if profit is not None:
                events_by_profit.append({
                    "event_id": event_id,
                    "profit": profit,
                    "revenue": receita,
                    "margin": margin,
                    "company": event_company.get(event_id, "")
                })
        
        events_by_profit.sort(key=lambda x: x["profit"], reverse=True)
        
        # Top prejuízos
        prejuizos = [e for e in events_by_profit if e["profit"] < 0]
        prejuizos.sort(key=lambda x: x["profit"])
        
        self.dashboard["rankings"] = {
            "maior_receita": events_by_revenue[:10],
            "maior_lucro": events_by_profit[:10],
            "maiores_prejuizos": prejuizos[:10],
            "total_eventos_analisados": len(events_by_revenue),
            "total_com_lucro": len([e for e in events_by_profit if e["profit"] > 0]),
            "total_com_prejuizo": len(prejuizos)
        }
        
        print(f"      ✓ Top 10 por receita")
        print(f"      ✓ Top 10 por lucro")
        if prejuizos:
            print(f"      ⚠️  {len(prejuizos)} eventos com prejuízo")
    
    def generate_recommendations(self):
        """
        Recomendações comerciais
        """
        
        print("   💡 Gerando recomendações comerciais...")
        
        recommendations = []
        alertas = self.dashboard.get("alertas_comerciais", {})
        resumo = self.dashboard.get("resumo_comercial", {})
        
        # 1. Alerta: Eventos em risco
        if alertas.get("total_risco", 0) > 0:
            recommendations.append({
                "priority": "CRITICAL",
                "area": "vendas",
                "headline": f"🚨 {alertas['total_risco']} eventos com margem crítica",
                "description": f"{alertas['total_risco']} eventos foram vendidos com margem abaixo de 10%, gerando risco de prejuízo real.",
                "action": "Revisar URGENTEMENTE os preços ou custos destes eventos. Considerar renegociação com cliente.",
                "impact": "HIGH"
            })
        
        # 2. Alerta: Baixa margem
        if alertas.get("total_baixa_margem", 0) > 3:
            recommendations.append({
                "priority": "HIGH",
                "area": "precificacao",
                "headline": f"⚠️ {alertas['total_baixa_margem']} eventos com margem < 20%",
                "description": "Padrão de vendas com margem insuficiente. Risco de não cobrir custos fixos após rateio.",
                "action": "Revisar tabela de preços. Aumentar markup em 10-15%. Negociar melhor com fornecedores.",
                "impact": "HIGH"
            })
        
        # 3. Ticket médio
        ticket = resumo.get("ticket_medio", 0)
        if ticket < 15000:
            recommendations.append({
                "priority": "MEDIUM",
                "area": "vendas",
                "headline": "📉 Ticket médio abaixo do ideal",
                "description": f"Ticket médio de R$ {ticket:,.2f} sugere foco em eventos de menor porte.",
                "action": "Direcionar prospecção para eventos de maior valor. Criar pacotes premium.",
                "impact": "MEDIUM"
            })
        
        # 4. Eficiência comercial
        taxa = resumo.get("taxa_confirmacao", 0)
        if taxa < 60:
            recommendations.append({
                "priority": "HIGH",
                "area": "comercial",
                "headline": "🎯 Taxa de confirmação baixa",
                "description": f"{taxa:.1f}% de conversão de propostas. Muitos eventos ficam em aberto.",
                "action": "Revisar processo de follow-up. Oferecer condições diferenciadas para fechamento rápido.",
                "impact": "HIGH"
            })
        
        # 5. Margem geral
        margem = resumo.get("margem_media", 0)
        if margem < 25:
            recommendations.append({
                "priority": "HIGH",
                "area": "financeiro",
                "headline": "📊 Margem média insuficiente",
                "description": f"Margem de {margem:.1f}% não garante lucratividade após custos fixos.",
                "action": "Aumentar preços base em 15-20% OU reduzir custos de 10-15%. Priorizar um caminho.",
                "impact": "CRITICAL"
            })
        
        # 6. Otimização
        if not recommendations:
            recommendations.append({
                "priority": "LOW",
                "area": "crescimento",
                "headline": "✅ Performance comercial estável",
                "description": "Indicadores dentro dos parâmetros. Foco pode ser em crescimento.",
                "action": "Testar aumento de 5-10% em eventos novos. Monitorar impacto na conversão.",
                "impact": "MEDIUM"
            })
        
        self.dashboard["recomendacoes"] = recommendations
        
        print(f"      ✓ {len(recommendations)} recomendações geradas")
    
    def save_dashboard(self):
        """Salva dashboard"""
        
        filepath = DATA_DIR / "sales_dashboard.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.dashboard, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Dashboard salvo em: kitchen_data/sales_dashboard.json")
    
    def print_report(self):
        """Imprime relatório"""
        
        print("\n" + "="*80)
        print("📈 SALES DASHBOARD - PERFORMANCE COMERCIAL")
        print("="*80)
        
        resumo = self.dashboard.get("resumo_comercial", {})
        
        # Header
        print(f"\n💰 RESUMO COMERCIAL")
        print(f"{'─'*80}")
        print(f"   Total de Eventos:     {resumo.get('total_eventos', 0):>8}")
        print(f"   Receita Total:        R$ {resumo.get('receita_total', 0):>12,.2f}")
        print(f"   Ticket Médio:         R$ {resumo.get('ticket_medio', 0):>12,.2f}")
        print(f"   Margem Média:         {resumo.get('margem_media', 0):>8.1f}%")
        print(f"\n   Eventos Confirmados:  {resumo.get('eventos_confirmados', 0):>8}")
        print(f"   Propostas Pendentes:  {resumo.get('eventos_proposta', 0):>8}")
        print(f"   Taxa Conversão:       {resumo.get('taxa_confirmacao', 0):>8.1f}%")
        print(f"\n   ✓ Lucrativos:         {resumo.get('eventos_lucrativos', 0):>8} ({resumo.get('pct_lucrativos', 0):.1f}%)")
        print(f"   ✗ Em Prejuízo:        {resumo.get('eventos_prejuizo', 0):>8} ({resumo.get('pct_prejuizo', 0):.1f}%)")
        
        # KPIs
        kpis = self.dashboard.get("kpis_vendas", [])
        if kpis:
            print(f"\n🎯 KPIs DE VENDAS")
            print(f"{'─'*80}")
            
            for kpi in kpis:
                emoji = {"good": "🟢", "warning": "🟡", "critical": "🔴", "stable": "⚪"}.get(kpi.get("status"), "⚪")
                print(f"   {emoji} {kpi['nome']}")
                print(f"      Valor: {kpi['formatado']}")
                print(f"      Status: {kpi.get('classificacao', 'N/A')}")
                if kpi.get('meta'):
                    print(f"      Meta: {kpi['meta']}")
                print(f"      {kpi['contexto']}")
        
        # Análise por empresa
        empresas = self.dashboard.get("analise_por_empresa", {})
        if empresas:
            print(f"\n🏢 POR EMPRESA")
            print(f"{'─'*80}")
            
            for company, data in empresas.items():
                print(f"   {company.upper()}")
                print(f"      Eventos: {data.get('eventos', 0)}")
                print(f"      Receita: R$ {data.get('receita', 0):,.2f}")
                print(f"      Ticket: R$ {data.get('ticket_medio', 0):,.2f}")
                print(f"      Margem: {data.get('margem_media', 0):.1f}%")
        
        # Alertas
        alertas = self.dashboard.get("alertas_comerciais", {})
        
        if alertas.get("total_risco", 0) > 0:
            print(f"\n🚨 ALERTAS CRÍTICOS")
            print(f"{'─'*80}")
            print(f"   {alertas['total_risco']} eventos em RISCO (margem < 10%)")
            print(f"   {alertas['total_baixa_margem']} eventos com BAIXA MARGEM (< 20%)")
            print(f"\n   Top Riscos:")
            for risco in alertas.get("eventos_risco", [])[:3]:
                print(f"      • {risco['event_id']}: {risco['margin']:.1f}% margem")
        
        # Recomendações
        recs = self.dashboard.get("recomendacoes", [])
        if recs:
            print(f"\n💡 RECOMENDAÇÕES COMERCIAIS")
            print(f"{'─'*80}")
            
            for rec in recs:
                emoji = {"CRITICAL": "🚨", "HIGH": "🔴", "MEDIUM": "⚠️", "LOW": "ℹ️"}.get(rec.get("priority"), "⚪")
                print(f"\n   {emoji} [{rec['priority']}] {rec['headline']}")
                print(f"      {rec['description']}")
                print(f"      → Ação: {rec['action']}")
        
        # Rankings
        rankings = self.dashboard.get("rankings", {})
        
        if rankings.get("maior_receita"):
            print(f"\n🏆 TOP 5 POR RECEITA")
            print(f"{'─'*80}")
            for i, ev in enumerate(rankings["maior_receita"][:5], 1):
                print(f"   {i}. {ev['event_id']:<12} R$ {ev['revenue']:>10,.2f}")
        
        print(f"\n{'='*80}")
        print("📊 Para detalhes completos, consulte sales_dashboard.json")
        print(f"{'='*80}\n")


def main():
    """Função principal"""
    
    print("🎛️ SALES DASHBOARD ENGINE - Orkestra Finance Brain")
    print("="*80)
    print("\n📈 Otimizando performance comercial")
    print("   Foco: Margem real, ticket médio, conversão")
    
    engine = SalesDashboardEngine()
    
    # Processar
    print("\n🔄 Processando dados comerciais...")
    
    engine.calculate_sales_metrics()
    engine.calculate_advanced_kpis()
    engine.generate_rankings()
    engine.generate_recommendations()
    
    # Salvar
    engine.save_dashboard()
    
    # Imprimir
    engine.print_report()
    
    print("✅ Sales Dashboard Engine completado!")


if __name__ == "__main__":
    main()
