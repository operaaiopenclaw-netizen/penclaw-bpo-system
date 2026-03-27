# decision_engine_v3.py - Orkestra Decision Engine V3
# Tomada de decisões automáticas com base em múltiplos sinais

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Paths
sys.path.insert(0, str(Path(__file__).parent))


class Decision(Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"
    HOLD_CASH = "HOLD_CASH"
    ADJUST_PRICE = "ADJUST_PRICE"
    REDUCE_STAFF = "REDUCE_STAFF"
    CHANGE_SUPPLIER = "CHANGE_SUPPLIER"
    FREEZE_EVENT = "FREEZE_EVENT"


@dataclass
class DecisionSignal:
    """Sinal que influencia a decisão."""
    source: str
    metric: str
    value: float
    threshold: float
    severity: str
    message: str


@dataclass
class ExecutiveDecision:
    """Decisão executiva final."""
    event_id: str
    primary_decision: Decision
    confidence: float
    rationale: str
    actions: List[str]
    alerts: List[str]
    auto_execute: bool


class DecisionEngineV3:
    """
    Motor de decisão executiva V3.
    Integra margem, caixa, CMV e intercompany para decisões automáticas.
    """
    
    def __init__(self):
        self.metrics = {
            "min_margin": 0.25,  # Margem mínima aceitável
            "critical_margin": 0.0,  # Margem crítica (prejuízo)
            "max_custo_financeiro": 0.08,  # 8% da receita
            "cmv_max": 0.35,  # CMV máximo aceitável
            "intercompany_threshold": 10000,  # Limite de transferência
        }
        self.signals = []
        self.decisions = []
        
    def load_datasets(self) -> Dict:
        """Carrega todos os datasets necessários."""
        datasets = {
            "events": [],
            "dre": {},
            "cashflow": {},
            "intercompany": {},
            "learning_rules": []
        }
        
        # Eventos 2024 e 2025
        for year in ["2024", "2025"]:
            path = Path(f"data/event_dataset_{year}.json")
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    datasets["events"].extend(data.get("contracts", []))
        
        # Cashflow report
        cf_path = Path("orkestra/memory/cashflow_report.json")
        if cf_path.exists():
            with open(cf_path) as f:
                datasets["cashflow"] = json.load(f)
        
        # Intercompany report
        ic_path = Path("orkestra/memory/intercompany_report.json")
        if ic_path.exists():
            with open(ic_path) as f:
                datasets["intercompany"] = json.load(f)
        
        # Learning rules (V2)
        lr_path = Path("orkestra/memory/learning_v2_report.json")
        if lr_path.exists():
            with open(lr_path) as f:
                datasets["learning_rules"] = json.load(f)
        
        print(f"✅ {len(datasets['events'])} eventos carregados")
        return datasets
    
    def calculate_event_metrics(self, event: Dict, datasets: Dict) -> Dict:
        """
        Calcula métricas completas para um evento.
        """
        event_id = event.get("contract_id", "UNKNOWN")
        revenue = event.get("revenue_total", 0)
        
        # Simular custos (baseado nos engines anteriores)
        from event_simulator_engine import simulate_event
        
        sim = simulate_event({
            "name": event_id,
            "expected_revenue": revenue,
            "people": event.get("people", 100),
            "has_open_bar": True,
            "high_staff": False
        })
        
        cost = sim["custo_estimado"]
        margin = sim["margem"]
        
        # Calcular CMV (Custo da Mercadoria Vendida)
        # ~60% do custo é CMV (bebidas + food)
        cmv = cost * 0.60
        cmv_pct = (cmv / revenue) if revenue > 0 else 0
        
        # Custo financeiro estimado (custos de transação, juros, etc)
        # ~5% da receita
        custo_financeiro = revenue * 0.05
        custo_fin_pct = 0.05
        
        return {
            "event_id": event_id,
            "revenue": revenue,
            "cost": cost,
            "profit": revenue - cost,
            "margin": margin,
            "margin_pct": margin * 100,
            "cmv": cmv,
            "cmv_pct": cmv_pct,
            "custo_financeiro": custo_financeiro,
            "custo_financeiro_pct": custo_fin_pct,
            "status": event.get("status", "UNKNOWN"),
            "date": event.get("date", "2025-01-01")
        }
    
    def analyze_intercompany_position(self, event_id: str, datasets: Dict) -> Dict:
        """
        Analisa posição inter-empresas para o evento.
        """
        ic_data = datasets.get("intercompany", {})
        
        # Verificar se há desbalanceamento
        status_balance = ic_data.get("companies", {}).get("STATUS", {}).get("saldo_liquido", 0)
        la_orana_balance = ic_data.get("companies", {}).get("LA_ORANA", {}).get("saldo_liquido", 0)
        
        # Se STATUS positivo e LA ORANA negativo, há problema
        if status_balance > 0 and la_orana_balance < 0:
            imbalance = abs(la_orana_balance)
            return {
                "has_imbalance": True,
                "imbalance_amount": imbalance,
                "status": "LA_ORANA_OWES_STATUS",
                "recommendation": "BLOCK_NEW_TRANSFERS"
            }
        
        return {
            "has_imbalance": False,
            "imbalance_amount": 0,
            "status": "BALANCED",
            "recommendation": "PROCEED"
        }
    
    def check_cash_stress(self, event_date: str, datasets: Dict) -> Dict:
        """
        Verifica situação de caixa para a data do evento.
        """
        cf_data = datasets.get("cashflow", {})
        summary = cf_data.get("summary", {})
        
        # Simplificado: verificar se há meses com caixa negativo
        cash_need = summary.get("cash_need", 0)
        negative_months = summary.get("negative_months", 0)
        
        if negative_months > 0:
            return {
                "cash_stress": True,
                "severity": "HIGH" if cash_need > 50000 else "MEDIUM",
                "cash_need": cash_need,
                "message": f"{negative_months} meses com caixa negativo, necessidade de R$ {cash_need:,.0f}",
                "recommendation": "HOLD_CASH" if cash_need > 30000 else "MONITOR"
            }
        
        return {
            "cash_stress": False,
            "severity": "LOW",
            "cash_need": 0,
            "message": "Caixa saudável",
            "recommendation": "PROCEED"
        }
    
    def check_learning_rules(self, event: Dict, datasets: Dict) -> List[Dict]:
        """
        Verifica regras de aprendizado aplicáveis.
        """
        rules = datasets.get("learning_rules", {})
        applicable = []
        
        # Extrair insights de padrões
        patterns = rules.get("patterns_found", [])
        
        for pattern in patterns:
            # Verificar se padrão se aplica a este evento
            if pattern.get("category") == "consumption":
                applicable.append({
                    "type": "CONSUMPTION_ADJUSTMENT",
                    "item": pattern.get("item"),
                    "suggested_adjustment": pattern.get("suggested_adjustment"),
                    "confidence": pattern.get("confidence"),
                    "message": f"Ajustar {pattern['item']} em {pattern['suggested_adjustment']:.1f}% por histórico"
                })
        
        # Regras de margem
        if event.get("revenue_total", 0) > 50000:
            # Eventos grandes
            applicable.append({
                "type": "LARGE_EVENT_DISCOUNT",
                "message": "Evento grande - negociar margem mais competitiva",
                "confidence": 70
            })
        
        return applicable
    
    def evaluate_event(self, event: Dict, datasets: Dict) -> ExecutiveDecision:
        """
        Avalia um evento e toma decisão executiva.
        """
        event_id = event.get("contract_id", "UNKNOWN")
        
        # Coletar sinais
        signals = []
        actions = []
        alerts = []
        
        # 1. Métricas do evento
        metrics = self.calculate_event_metrics(event, datasets)
        margin = metrics["margin"]
        cmv_pct = metrics["cmv_pct"]
        
        # REGRA 1: Margem < 0
        if margin < 0:
            signals.append(DecisionSignal(
                source="MARGIN",
                metric="margin",
                value=margin,
                threshold=0,
                severity="CRITICAL",
                message=f"Margem negativa: {metrics['margin_pct']:.1f}%"
            ))
            actions.append("REJECT: Prejuízo projetado")
            alerts.append(f"CRITICAL: {event_id} terá prejuízo de R$ {abs(metrics['profit']):,.0f}")
        
        # REGRA 2: Margem < 25%
        elif margin < 0.25:
            signals.append(DecisionSignal(
                source="MARGIN",
                metric="margin",
                value=margin,
                threshold=0.25,
                severity="HIGH",
                message=f"Margem abaixo do mínimo: {metrics['margin_pct']:.1f}% (< 25%)"
            ))
            actions.append("REVIEW: Margem insuficiente")
            actions.append("ADJUST_PRICE: Aumentar preço ou reduzir custo")
            alerts.append(f"HIGH: {event_id} margem apenas {metrics['margin_pct']:.1f}%")
        
        # REGRA 6: Evento não cobre custo incremental + margem mínima
        else:
            # Verificar se é viável
            if metrics["profit"] < 10000:  # Lucro mínimo de 10k
                signals.append(DecisionSignal(
                    source="PROFITABILITY",
                    metric="profit",
                    value=metrics["profit"],
                    threshold=10000,
                    severity="MEDIUM",
                    message=f"Lucro abaixo do mínimo aceitável: R$ {metrics['profit']:,.0f}"
                ))
                actions.append("FREEZE_EVENT: Revisar escopo")
        
        # REGRA 3: Custo financeiro > 8%
        if metrics["custo_financeiro_pct"] > 0.08:
            signals.append(DecisionSignal(
                source="CASH",
                metric="custo_financeiro",
                value=metrics["custo_financeiro_pct"],
                threshold=0.08,
                severity="HIGH",
                message=f"Custo financeiro alto: {metrics['custo_financeiro_pct']*100:.1f}% (> 8%)"
            ))
            actions.append("HOLD_CASH: Estresse de caixa detectado")
            alerts.append(f"CASH ALERT: {event_id} causa estresse de caixa")
        
        # REGRA 5: CMV fora da faixa
        if cmv_pct > self.metrics["cmv_max"]:
            signals.append(DecisionSignal(
                source="CMV",
                metric="cmv",
                value=cmv_pct,
                threshold=self.metrics["cmv_max"],
                severity="MEDIUM",
                message=f"CMV alto: {cmv_pct*100:.1f}%"
            ))
            actions.append("CHANGE_SUPPLIER: CMV acima do histórico")
            actions.append("ADJUST_PRICE: Repassar custo")
        
        # Verificar intercompany
        ic_position = self.analyze_intercompany_position(event_id, datasets)
        if ic_position["has_imbalance"]:
            # REGRA 4: Intercompany desbalanceado
            signals.append(DecisionSignal(
                source="INTERCOMPANY",
                metric="intercompany_balance",
                value=ic_position["imbalance_amount"],
                threshold=self.metrics["intercompany_threshold"],
                severity="MEDIUM",
                message=f"Desbalanceamento inter-empresas: R$ {ic_position['imbalance_amount']:,.0f}"
            ))
            actions.append("BLOCK: Transferências novas congeladas")
            alerts.append(f"INTERCOMPANY: {event_id} não pode prosseguir até regularização")
        
        # Verificar caixa
        cash_status = self.check_cash_stress(event.get("date", "2025-01-01"), datasets)
        if cash_status["cash_stress"]:
            signals.append(DecisionSignal(
                source="CASHFLOW",
                metric="cash_need",
                value=cash_status["cash_need"],
                threshold=30000,
                severity=cash_status["severity"],
                message=cash_status["message"]
            ))
            if cash_status["severity"] == "HIGH":
                actions.append("HOLD_CASH: Prioridade a caixa próprio")
        
        # Verificar regras de aprendizado
        learning_rules = self.check_learning_rules(event, datasets)
        for rule in learning_rules:
            if rule.get("confidence", 0) > 60:
                actions.append(f"APPLY_RULE: {rule['type']} - {rule.get('item', 'N/A')}")
        
        # DETERMINAR DECISÃO FINAL
        critical_signals = [s for s in signals if s.severity == "CRITICAL"]
        high_signals = [s for s in signals if s.severity == "HIGH"]
        
        if critical_signals:
            decision = Decision.REJECT
            confidence = 0.95
            rationale = "Prejuízo projetado - evento inviável"
        elif high_signals:
            # Verificar tipo de sinal alto
            if any(s.source == "INTERCOMPANY" for s in high_signals):
                decision = Decision.FREEZE_EVENT
                confidence = 0.85
                rationale = "Desbalanceamento inter-empresas - aguardar regularização"
            elif any(s.source == "CASH" for s in high_signals):
                decision = Decision.HOLD_CASH
                confidence = 0.80
                rationale = "Estresse de caixa - priorizar liquidez"
            else:
                decision = Decision.REVIEW
                confidence = 0.75
                rationale = "Margem ou CMV fora dos padrões - revisar"
        elif any(s.severity == "MEDIUM" for s in signals):
            decision = Decision.ADJUST_PRICE
            confidence = 0.70
            rationale = "Ajustes necessários - preço ou fornecedor"
        else:
            decision = Decision.APPROVE
            confidence = 0.90
            rationale = "Evento dentro dos parâmetros - aprovar"
        
        # Se há regras de redução de staff
        if any("staff" in a.lower() for a in actions):
            decision = Decision.REDUCE_STAFF
            rationale += " - otimizar equipe"
        
        return ExecutiveDecision(
            event_id=event_id,
            primary_decision=decision,
            confidence=confidence,
            rationale=rationale,
            actions=actions if actions else ["PROCEED: Nenhuma ação necessária"],
            alerts=alerts if alerts else ["✅ Sem alertas críticos"],
            auto_execute=decision in [Decision.REJECT, Decision.APPROVE] and confidence > 0.85
        )
    
    def generate_executive_report(self, decisions: List[ExecutiveDecision]) -> Dict:
        """Gera relatório executivo de decisões."""
        
        total = len(decisions)
        approved = len([d for d in decisions if d.primary_decision == Decision.APPROVE])
        review = len([d for d in decisions if d.primary_decision == Decision.REVIEW])
        rejected = len([d for d in decisions if d.primary_decision == Decision.REJECT])
        hold_cash = len([d for d in decisions if d.primary_decision == Decision.HOLD_CASH])
        adjust = len([d for d in decisions if d.primary_decision == Decision.ADJUST_PRICE])
        
        critical_alerts = [d for d in decisions if any("CRITICAL" in a for a in d.alerts)]
        
        revenue_at_risk = sum(
            self.calculate_event_metrics(
                {"contract_id": d.event_id, "revenue_total": 50000},  # simplificado
                {}
            ).get("revenue", 0)
            for d in rejected
        )
        
        return {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_events": total,
                "approved": approved,
                "review": review,
                "rejected": rejected,
                "hold_cash": hold_cash,
                "adjust_price": adjust,
                "critical_alerts": len(critical_alerts),
                "revenue_at_risk": revenue_at_risk
            },
            "decisions": [
                {
                    "event_id": d.event_id,
                    "decision": d.primary_decision.value,
                    "confidence": round(d.confidence, 2),
                    "rationale": d.rationale,
                    "actions": d.actions,
                    "alerts": d.alerts,
                    "auto_execute": d.auto_execute
                }
                for d in decisions
            ]
        }
    
    def print_executive_summary(self, report: Dict):
        """Imprime resumo executivo."""
        print("\n" + "=" * 70)
        print("🎯 ORKESTRA DECISION ENGINE V3 - EXECUTIVE SUMMARY")
        print("=" * 70)
        
        summary = report["summary"]
        
        print(f"\n📊 PANORAMA GERAL")
        print("-" * 70)
        print(f"   Total Eventos Analisados: {summary['total_events']}")
        print(f"   ✅ Aprovados:           {summary['approved']}")
        print(f"   ⚠️  Revisar:            {summary['review']}")
        print(f"   ❌ Rejeitados:          {summary['rejected']}")
        print(f"   💰 Hold Cash:           {summary['hold_cash']}")
        print(f"   ⚙️  Ajustar Preço:      {summary['adjust_price']}")
        
        print(f"\n🚨 CRITICAL ALERTS: {summary['critical_alerts']}")
        if summary['revenue_at_risk'] > 0:
            print(f"💸 Receita em Risco: R$ {summary['revenue_at_risk']:,.0f}")
        
        print("\n" + "-" * 70)
        print("📋 DECISÕES POR EVENTO")
        print("-" * 70)
        
        for d in report["decisions"][:10]:  # Primeiros 10
            icon = {
                "APPROVE": "✅",
                "REVIEW": "⚠️",
                "REJECT": "❌",
                "HOLD_CASH": "💰",
                "ADJUST_PRICE": "⚙️",
                "REDUCE_STAFF": "👥",
                "CHANGE_SUPPLIER": "🏭",
                "FREEZE_EVENT": "🛑"
            }.get(d["decision"], "➡️")
            
            print(f"\n{icon} {d['event_id']}")
            print(f"   Decisão: {d['decision']} ({d['confidence']:.0%} confiança)")
            print(f"   Racional: {d['rationale']}")
            
            if d["alerts"] and d["alerts"][0] != "✅ Sem alertas críticos":
                print(f"   🚨 Alertas:")
                for alert in d["alerts"][:2]:
                    print(f"      - {alert}")
            
            print(f"   Ações:")
            for action in d["actions"][:2]:
                print(f"      → {action}")
        
        print("\n" + "=" * 70)
    
    def save_results(self, report: Dict):
        """Salva resultados."""
        output_path = Path("orkestra/memory/decision_report_v3.json")
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Relatório salvo: {output_path}")
        return output_path


def run_decision_engine_v3():
    """Executa Decision Engine V3 completo."""
    print("\n" + "=" * 70)
    print("🎯 ORKESTRA DECISION ENGINE V3")
    print("   Sistema de Decisões Executivas Automáticas")
    print("=" * 70)
    
    engine = DecisionEngineV3()
    
    # Carregar datasets
    datasets = engine.load_datasets()
    
    if not datasets["events"]:
        print("\n❌ Nenhum evento para analisar.")
        return None
    
    # Tomar decisões para cada evento
    print("\n🔍 Analisando eventos...")
    decisions = []
    
    for event in datasets["events"]:
        if event.get("status") not in ["CANCELLED", "CANCELADO"]:
            decision = engine.evaluate_event(event, datasets)
            decisions.append(decision)
    
    print(f"   ✅ {len(decisions)} eventos analisados")
    
    # Gerar relatório
    report = engine.generate_executive_report(decisions)
    
    # Imprimir
    engine.print_executive_summary(report)
    
    # Salvar
    engine.save_results(report)
    
    print("\n" + "=" * 70)
    print("✅ DECISION ENGINE V3 COMPLETO")
    print("=" * 70)
    
    return report


if __name__ == "__main__":
    run_decision_engine_v3()
