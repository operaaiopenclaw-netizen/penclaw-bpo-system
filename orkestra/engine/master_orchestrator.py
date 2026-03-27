# master_orchestrator.py - Orkestra Master Orchestrator
# Cérebro do sistema - integra todos os engines

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class ExecutiveSummary:
    """Resumo executivo do negócio."""
    receita_prevista: float
    custo_previsto: float
    lucro_previsto: float
    margem_prevista: float
    necessidade_caixa: float
    necessidade_compra: float
    risco_operacional: str


@dataclass
class Alert:
    """Alerta do sistema."""
    type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    message: str
    action_required: str


@dataclass
class AutoDecision:
    """Decisão automática do sistema."""
    trigger: str
    decision: str
    confidence: float
    rationale: str


class MasterOrchestrator:
    """
    Cérebro do Orkestra - integra todos os engines em um único fluxo.
    """
    
    def __init__(self):
        self.engines = {}
        self.events = []
        self.alerts = []
        self.decisions = []
        self.summary = None
        
    def load_engines(self):
        """Carrega todos os engines."""
        print("\n🔧 Carregando engines...")
        
        try:
            from event_simulator_engine import simulate_event, suggest_fix
            self.engines['simulator'] = {'simulate': simulate_event, 'fix': suggest_fix}
            print("   ✅ Event Simulator Engine")
        except Exception as e:
            print(f"   ⚠️  Event Simulator: {e}")
        
        try:
            from cashflow_engine import CashflowEngine
            self.engines['cashflow'] = CashflowEngine()
            print("   ✅ Cashflow Engine")
        except Exception as e:
            print(f"   ⚠️  Cashflow Engine: {e}")
        
        try:
            from event_profit_engine import EventProfitEngine
            self.engines['profit'] = EventProfitEngine()
            print("   ✅ Event Profit Engine")
        except Exception as e:
            print(f"   ⚠️  Event Profit Engine: {e}")
        
        try:
            from intercompany_control import IntercompanyControl
            self.engines['intercompany'] = IntercompanyControl()
            print("   ✅ Intercompany Control")
        except Exception as e:
            print(f"   ⚠️  Intercompany Control: {e}")
        
        # Procurement stub (se existir)
        if Path("orkestra/engine/procurement_engine.py").exists():
            try:
                from procurement_engine import ProcurementEngine
                self.engines['procurement'] = ProcurementEngine()
                print("   ✅ Procurement Engine")
            except Exception as e:
                print(f"   ⚠️  Procurement Engine: {e}")
        
    def load_future_events(self, events_data: List[Dict] = None):
        """Carrega eventos futuros para processamento."""
        if events_data:
            self.events = events_data
            return
        
        # Carregar de datasets
        try:
            for year in ["2024", "2025"]:
                path = Path(f"data/event_dataset_{year}.json")
                if path.exists():
                    with open(path) as f:
                        data = json.load(f)
                    for contract in data.get("contracts", []):
                        if contract.get("status") in ["CONFIRMED", "PENDING", "CONFIRMADO", "PENDENTE"]:
                            self.events.append({
                                "id": contract["contract_id"],
                                "name": contract["contract_id"],
                                "date": contract.get("date", "2025-01-01"),
                                "expected_revenue": contract.get("revenue_total", 0),
                                "people": 100,
                                "has_open_bar": True,  # default
                                "high_staff": False
                            })
        except Exception as e:
            # Usar eventos de teste
            self.events = [
                {"id": "EVT001", "name": "Formatura Medicina", "date": "2025-04-15", "expected_revenue": 50000, "people": 200, "has_open_bar": True, "high_staff": True},
                {"id": "EVT002", "name": "Casamento Centro", "date": "2025-05-20", "expected_revenue": 80000, "people": 150, "has_open_bar": True, "high_staff": False},
                {"id": "EVT003", "name": "Confraternização Corp", "date": "2025-06-10", "expected_revenue": 35000, "people": 100, "has_open_bar": False, "high_staff": True},
            ]
        
        print(f"\n📅 Eventos futuros carregados: {len(self.events)}")
    
    def run_forecast(self) -> Dict:
        """
        PASSO 1: Rodar forecast de eventos.
        Simula todos os eventos futuros.
        """
        print("\n" + "=" * 70)
        print("🔮 PASSO 1: FORECAST DE EVENTOS")
        print("=" * 70)
        
        projections = []
        total_revenue = 0
        total_custo = 0
        
        for event in self.events:
            try:
                result = self.engines['simulator']['simulate'](event)
                projections.append({
                    "event": event["name"],
                    "revenue": result["receita"],
                    "cost": result["custo_estimado"],
                    "margin": result["margem"],
                    "decision": result["decision"],
                    "cost_ratio": result["cost_ratio"]
                })
                
                total_revenue += result["receita"]
                total_custo += result["custo_estimado"]
                
                icon = "✅" if result["decision"] == "APPROVE" else "⚠️" if result["decision"] == "REVIEW" else "❌"
                print(f"\n   {icon} {event['name']}")
                print(f"      Receita: R$ {result['receita']:,.0f}")
                print(f"      Custo: R$ {result['custo_estimado']:,.0f}")
                print(f"      Margem: {result['margem']*100:.1f}%")
                print(f"      Status: {result['decision']}")
                
                # Sugestões se necessário
                if result["decision"] != "APPROVE":
                    fix = self.engines['simulator']['fix'](event, result)
                    if fix.get('status') != "OK":
                        print(f"      💡 Aumentar preço +R$ {fix['increase_revenue_needed']:,.0f} OU Reduzir custo -R$ {fix['reduce_cost_needed']:,.0f}")
                        
            except Exception as e:
                print(f"   ⚠️  Erro em {event['name']}: {e}")
        
        forecast_summary = {
            "events": len(projections),
            "total_revenue": total_revenue,
            "total_cost": total_custo,
            "projected_profit": total_revenue - total_custo,
            "avg_margin": ((total_revenue - total_custo) / total_revenue * 100) if total_revenue > 0 else 0,
            "projections": projections
        }
        
        print(f"\n   📊 FORECAST TOTAL:")
        print(f"      Receita: R$ {total_revenue:,.0f}")
        print(f"      Custo: R$ {total_custo:,.0f}")
        print(f"      Lucro: R$ {forecast_summary['projected_profit']:,.0f}")
        print(f"      Margem: {forecast_summary['avg_margin']:.1f}%")
        
        return forecast_summary
    
    def run_procurement(self, forecast: Dict) -> Dict:
        """
        PASSO 2: Rodar projeção de compras.
        """
        print("\n" + "=" * 70)
        print("📦 PASSO 2: PROJEÇÃO DE COMPRAS")
        print("=" * 70)
        
        people_total = sum(e.get("people", 100) for e in self.events)
        
        # Cálculo de necessidades baseado nos eventos
        necessities = {
            "agua_liters": people_total * 1.2,
            "cerveja_cans": people_total * 2,
            "refrigerante_liters": people_total * 0.5,
            "suco_liters": people_total * 0.3,
            "gelo_kg": people_total * 1.6,
            "staff_needed": people_total / 25  # 1 staff por 25 pessoas
        }
        
        costs = {
            "agua": necessities["agua_liters"] * 3.0,
            "cerveja": necessities["cerveja_cans"] * 5.0,
            "refrigerante": necessities["refrigerante_liters"] * 8.0,
            "suco": necessities["suco_liters"] * 12.0,
            "gelo": necessities["gelo_kg"] * 2.5,
            "staff": necessities["staff_needed"] * 250  # R$ 250 per staff
        }
        
        total_procurement = sum(costs.values())
        
        print(f"\n   👥 Total pessoas: {people_total}")
        print(f"\n   📊 NECESSIDADES:")
        print(f"      Água: {necessities['agua_liters']:,.0f} litros")
        print(f"      Cerveja: {necessities['cerveja_cans']:,.0f} latas")
        print(f"      Refrigerante: {necessities['refrigerante_liters']:,.0f} litros")
        print(f"      Gelo: {necessities['gelo_kg']:,.0f} kg")
        print(f"      Staff: {necessities['staff_needed']:,.0f} pessoas")
        
        print(f"\n   💰 CUSTO ESTIMADO:")
        for item, cost in costs.items():
            print(f"      {item.capitalize()}: R$ {cost:,.0f}")
        print(f"      ────────────────────────────────")
        print(f"      TOTAL: R$ {total_procurement:,.0f}")
        
        return {
            "necessities": necessities,
            "costs": costs,
            "total_cost": total_procurement,
            "events_covered": len(self.events)
        }
    
    def run_dre_per_event(self) -> Dict:
        """
        PASSO 3: Gerar DRE (Demonstração de Resultados) por evento.
        """
        print("\n" + "=" * 70)
        print("📊 PASSO 3: DRE POR EVENTO")
        print("=" * 70)
        
        try:
            if 'profit' in self.engines:
                # Load from datasets if not loaded
                if not self.engines['profit'].events:
                    self.engines['profit'].load_from_datasets()
                    self.engines['profit'].load_from_financial_log()
                
                if self.engines['profit'].events:
                    results = self.engines['profit'].analyze_all()
                    insights = self.engines['profit'].generate_insights()
                    
                    print(f"\n   📊 RESUMO:")
                    summary = insights['summary']
                    print(f"      Eventos: {summary['total_eventos']}")
                    print(f"      Receita: R$ {summary['total_receita']:,.0f}")
                    print(f"      Custo: R$ {summary['total_custo']:,.0f}")
                    print(f"      Lucro: R$ {summary['total_lucro']:,.0f}")
                    print(f"      Margem Média: {summary['margem_media']:.1f}%")
                    
                    # Verificar problemas
                    prejuizo = insights.get('distribuicao', {}).get('prejuizo', 0)
                    abaixo_meta = insights.get('distribuicao', {}).get('abaixo_meta', 0)
                    
                    if prejuizo > 0:
                        self.alerts.append(Alert(
                            type="EVENTO_PREJUIZO",
                            severity="CRITICAL",
                            message=f"{prejuizo} eventos com prejuízo",
                            action_required="Revisar preços ou cancelar eventos"
                        ))
                    
                    if abaixo_meta > 0:
                        total = len(results)
                        pct = (abaixo_meta / total * 100) if total > 0 else 0
                        if pct > 30:
                            self.alerts.append(Alert(
                                type="MARGEM_BAIXA",
                                severity="HIGH",
                                message=f"{pct:.0f}% dos eventos abaixo de 25% margem",
                                action_required="Aumentar preços em 10-15%"
                            ))
                    
                    return insights
                else:
                    print("   ⚠️  Sem eventos para análise DRE")
                    return {}
            else:
                print("   ⚠️  Event Profit Engine não disponível")
                return {}
        except Exception as e:
            print(f"   ⚠️  Erro em DRE: {e}")
            return {}
    
    def run_cashflow(self) -> Dict:
        """
        PASSO 4: Rodar fluxo de caixa.
        """
        print("\n" + "=" * 70)
        print("💰 PASSO 4: FLUXO DE CAIXA")
        print("=" * 70)
        
        try:
            if 'cashflow' in self.engines:
                engine = self.engines['cashflow']
                engine.load_transactions()
                cashflow = engine.rebuild_cashflow()
                alerts = engine.detect_cash_leaks()
                
                # Calcular necessidade de caixa
                saldo_meses = {m: d['saldo_real'] for m, d in cashflow.items()}
                meses_negativos = [m for m, s in saldo_meses.items() if s < 0]
                
                print(f"\n   📊 MESES ANALISADOS: {len(cashflow)}")
                print(f"   📊 MESES COM CAIXA NEGATIVO: {len(meses_negativos)}")
                
                if meses_negativos:
                    total_necessidade = sum(abs(saldo_meses[m]) for m in meses_negativos)
                    print(f"   📊 NECESSIDADE TOTAL DE CAIXA: R$ {total_necessidade:,.0f}")
                    
                    self.alerts.append(Alert(
                        type="NECESSIDADE_CAIXA",
                        severity="HIGH",
                        message=f"{len(meses_negativos)} meses precisam de aporte de R$ {total_necessidade:,.0f}",
                        action_required="Planejar financiamento ou antecipar recebíveis"
                    ))
                else:
                    print("   ✅ Caixa positivo em todos os meses")
                
                # Alertas de caixa
                for alert in alerts:
                    if alert['severity'] in ['HIGH', 'CRITICAL']:
                        self.alerts.append(Alert(
                            type=f"CASH_{alert['type']}",
                            severity=alert['severity'],
                            message=alert['message'],
                            action_required="Revisar fluxo de caixa"
                        ))
                
                return {
                    "months": len(cashflow),
                    "negative_months": len(meses_negativos),
                    "cash_need": sum(abs(saldo_meses[m]) for m in meses_negativos) if meses_negativos else 0,
                    "alerts": len(alerts)
                }
            else:
                print("   ⚠️  Cashflow Engine não disponível")
                return {}
        except Exception as e:
            print(f"   ⚠️  Erro em cashflow: {e}")
            return {}
    
    def run_intercompany_validation(self) -> Dict:
        """
        PASSO 5: Validar entre empresas.
        """
        print("\n" + "=" * 70)
        print("🔄 PASSO 5: VALIDAÇÃO ENTRE EMPRESAS")
        print("=" * 70)
        
        try:
            if 'intercompany' in self.engines:
                control = self.engines['intercompany']
                control.load_events_from_datasets()
                control.calculate_balances()
                issues = control.detect_issues()
                
                print(f"\n   📊 STATUS:")
                status_balance = control.balances.get(control.STATUS, {})
                la_orana_balance = control.balances.get(control.LA_ORANA, {})
                
                print(f"      STATUS saldo: R$ {status_balance.get('saldo_liquido', 0):,.0f}")
                print(f"      LA ORANA saldo: R$ {la_orana_balance.get('saldo_liquido', 0):,.0f}")
                
                if issues:
                    print(f"\n   🚨 {len(issues)} problemas detectados")
                    for issue in issues[:3]:
                        print(f"      [{issue['severity']}] {issue['type']}")
                        self.alerts.append(Alert(
                            type=f"INTER_{issue['type']}",
                            severity=issue['severity'],
                            message=issue['message'],
                            action_required="Regularizar entre empresas"
                        ))
                else:
                    print("   ✅ Sistema equilibrado")
                
                return {
                    "status_balance": status_balance.get('saldo_liquido', 0),
                    "la_orana_balance": la_orana_balance.get('saldo_liquido', 0),
                    "issues": len(issues)
                }
            else:
                print("   ⚠️  Intercompany Control não disponível")
                return {}
        except Exception as e:
            print(f"   ⚠️  Erro em intercompany: {e}")
            return {}
    
    def generate_auto_decisions(self, forecast: Dict, procurement: Dict, 
                                 cashflow: Dict, intercompany: Dict) -> List[AutoDecision]:
        """
        Gera decisões automáticas baseadas nos dados.
        """
        print("\n" + "=" * 70)
        print("🤖 GERANDO DECISÕES AUTOMÁTICAS")
        print("=" * 70)
        
        decisions = []
        
        # Decisão 1: Aumento de preço
        if forecast.get('avg_margin', 0) < 0.25:
            decisions.append(AutoDecision(
                trigger="MARGEM_BAIXA",
                decision="AUMENTAR_PRECO_10_PERCENT",
                confidence=0.85,
                rationale=f"Margem média {forecast['avg_margin']:.1f}% abaixo do ideal de 30%"
            ))
        
        # Decisão 2: Troca de fornecedor
        if procurement.get('total_cost', 0) > forecast.get('total_revenue', 0) * 0.70:
            decisions.append(AutoDecision(
                trigger="CUSTO_ALTO",
                decision="COTAR_FORNECEDORES_ALTERNATIVOS",
                confidence=0.75,
                rationale=f"Custo de {procurement['total_cost']:,.0f} representa >70% da receita"
            ))
        
        # Decisão 3: Redução de staff
        if any(e.get('people', 0) > 200 for e in self.events):
            decisions.append(AutoDecision(
                trigger="EVENTO_GRANDE_PORTE",
                decision="OTIMIZAR_STAFF_AUTOMATICO",
                confidence=0.70,
                rationale="Eventos >200 pessoas podem ter staff otimizado"
            ))
        
        # Decisão 4: Ajuste entre empresas
        if intercompany.get('issues', 0) > 0:
            decisions.append(AutoDecision(
                trigger="DESBALANCEAMENTO_INTERCOMPANY",
                decision="AGENDAR_TRANSFERENCIA_ENTRE_EMPRESAS",
                confidence=0.90,
                rationale="Saldos desbalanceados entre STATUS e LA ORANA"
            ))
        
        # Decisão 5: Financiamento
        if cashflow.get('cash_need', 0) > 0:
            decisions.append(AutoDecision(
                trigger="CAIXA_NEGATIVO",
                decision="ANTECIPAR_RECEBIVEIS_OU_FINANCIAMENTO",
                confidence=0.95,
                rationale=f"Necessidade de R$ {cashflow['cash_need']:,.0f} em aporte"
            ))
        
        self.decisions = decisions
        
        # Print
        for d in decisions:
            icon = "🎯" if d.confidence > 0.80 else "💡"
            print(f"\n   {icon} {d.decision}")
            print(f"      Gatilho: {d.trigger}")
            print(f"      Confiança: {d.confidence:.0%}")
            print(f"      Racional: {d.rationale}")
        
        return decisions
    
    def generate_executive_summary(self, forecast: Dict, procurement: Dict,
                                    cashflow: Dict, intercompany: Dict) -> ExecutiveSummary:
        """Gera resumo executivo final."""
        
        receita = forecast.get('total_revenue', 0)
        custo = forecast.get('total_cost', 0) + procurement.get('total_cost', 0)
        lucro = receita - custo
        margem = (lucro / receita * 100) if receita > 0 else 0
        
        # Risco operacional
        num_alerts = len([a for a in self.alerts if a.severity in ['CRITICAL', 'HIGH']])
        if num_alerts >= 3:
            risco = "ALTO"
        elif num_alerts >= 1:
            risco = "MÉDIO"
        else:
            risco = "BAIXO"
        
        self.summary = ExecutiveSummary(
            receita_prevista=receita,
            custo_previsto=custo,
            lucro_previsto=lucro,
            margem_prevista=margem,
            necessidade_caixa=cashflow.get('cash_need', 0),
            necessidade_compra=procurement.get('total_cost', 0),
            risco_operacional=risco
        )
        
        return self.summary
    
    def print_executive_report(self):
        """Imprime relatório executivo final."""
        print("\n" + "=" * 70)
        print("📊 ORKESTRA MASTER ORCHESTRATOR - EXECUTIVE REPORT")
        print("=" * 70)
        
        s = self.summary
        
        print(f"\n💰 PROJEÇÃO FINANCEIRA")
        print("-" * 70)
        print(f"   Receita Prevista:      R$ {s.receita_prevista:>15,.0f}")
        print(f"   Custo Previsto:        R$ {s.custo_previsto:>15,.0f}")
        print(f"   ────────────────────────────────────────────")
        print(f"   LUCRO PREVISTO:        R$ {s.lucro_previsto:>15,.0f}")
        print(f"   Margem Prevista:            {s.margem_prevista:>12.1f}%")
        
        print(f"\n💵 NECESSIDADES")
        print("-" * 70)
        print(f"   Necessidade de Caixa:  R$ {s.necessidade_caixa:>15,.0f}")
        print(f"   Necessidade de Compra: R$ {s.necessidade_compra:>15,.0f}")
        
        print(f"\n⚠️  RISCO OPERACIONAL: {s.risco_operacional}")
        
        print(f"\n🚨 ALERTAS ATIVOS: {len([a for a in self.alerts if a.severity in ['CRITICAL', 'HIGH']])} críticos")
        print(f"🤖 DECISÕES GERADAS: {len(self.decisions)}")
        
        print("\n" + "=" * 70)
    
    def save_results(self):
        """Salva resultados completos."""
        output = {
            "generated_at": datetime.now().isoformat(),
            "executive_summary": {
                "receita_prevista": self.summary.receita_prevista if self.summary else 0,
                "custo_previsto": self.summary.custo_previsto if self.summary else 0,
                "lucro_previsto": self.summary.lucro_previsto if self.summary else 0,
                "margem_prevista": self.summary.margem_prevista if self.summary else 0,
                "necessidade_caixa": self.summary.necessidade_caixa if self.summary else 0,
                "necessidade_compra": self.summary.necessidade_compra if self.summary else 0,
                "risco_operacional": self.summary.risco_operacional if self.summary else "DESCONHECIDO"
            },
            "alerts": [{"type": a.type, "severity": a.severity, "message": a.message} for a in self.alerts],
            "decisions": [{"trigger": d.trigger, "decision": d.decision, "confidence": d.confidence} for d in self.decisions]
        }
        
        output_path = Path("orkestra/memory/master_report.json")
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        return output_path


def run_master_orchestrator():
    """
    Executa o Master Orchestrator completo.
    """
    print("\n" + "=" * 70)
    print("🧠 ORKESTRA - MASTER ORCHESTRATOR")
    print("   Cérebro do sistema Orkestra")
    print("=" * 70)
    
    orchestrator = MasterOrchestrator()
    
    # Passo 0: Carregar engines
    orchestrator.load_engines()
    
    # Passo 0.5: Carregar eventos
    orchestrator.load_future_events()
    
    if not orchestrator.events:
        print("\n❌ Nenhum evento futuro para processar.")
        return
    
    # Passo 1: Forecast
    forecast = orchestrator.run_forecast()
    
    # Passo 2: Procurement
    procurement = orchestrator.run_procurement(forecast)
    
    # Passo 3: DRE
    dre = orchestrator.run_dre_per_event()
    
    # Passo 4: Cashflow
    cashflow = orchestrator.run_cashflow()
    
    # Passo 5: Intercompany
    intercompany = orchestrator.run_intercompany_validation()
    
    # Gerar decisões automáticas
    decisions = orchestrator.generate_auto_decisions(forecast, procurement, cashflow, intercompany)
    
    # Gerar resumo executivo
    summary = orchestrator.generate_executive_summary(forecast, procurement, cashflow, intercompany)
    
    # Imprimir relatório
    orchestrator.print_executive_report()
    
    # Salvar
    output_path = orchestrator.save_results()
    print(f"\n💾 Relatório completo salvo: {output_path}")
    
    print("\n" + "=" * 70)
    print("✅ MASTER ORCHESTRATOR COMPLETO")
    print("=" * 70)
    
    return orchestrator


if __name__ == "__main__":
    run_master_orchestrator()
