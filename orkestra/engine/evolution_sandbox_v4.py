# evolution_sandbox_v4.py - Orkestra Evolution Sandbox V4
# Laboratório de evolução automática - propõe melhorias sem tocar produção

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ChangeType(Enum):
    NEW_RULE = "NEW_RULE"
    METRIC_ADJUSTMENT = "METRIC_ADJUSTMENT"
    PROMPT_DIFF = "PROMPT_DIFF"
    CODE_DIFF = "CODE_DIFF"


class RiskLevel(Enum):
    LOW = "LOW"      # Testado, baixo impacto
    MEDIUM = "MEDIUM"  # Moderado, necessita review
    HIGH = "HIGH"    # Alto risco, aprovação obrigatória
    CRITICAL = "CRITICAL"  # Sistema crítico, board approval


@dataclass
class Hypothesis:
    """Hipótese de melhoria."""
    id: str
    pattern_detected: str
    description: str
    proposed_change_type: ChangeType
    current_value: Any
    proposed_value: Any
    expected_impact: float
    risk_level: RiskLevel
    confidence: float
    evidence: List[Dict]


@dataclass
class SimulationResult:
    """Resultado de simulação no histórico."""
    hypothesis_id: str
    before_metrics: Dict
    after_metrics: Dict
    improvement_pct: float
    events_affected: int
    success_rate: float
    side_effects: List[str]


@dataclass
class EvolutionProposal:
    """Proposta de evolução completa."""
    id: str
    timestamp: str
    hypothesis: Hypothesis
    simulation: SimulationResult
    risk_assessment: str
    approval_status: str  # PENDING, APPROVED, REJECTED
    production_ready: bool


class EvolutionSandboxV4:
    """
    Sandbox de evolução V4.
    Propõe melhorias automaticamente, mas NUNCA aplica sem aprovação.
    """
    
    def __init__(self):
        self.proposals: List[EvolutionProposal] = []
        self.pending_approvals: List[EvolutionProposal] = []
        self.history = []
        self.changes_rejected = []
        self.changes_approved = []
        
    def load_historical_data(self) -> Dict:
        """Carrega todos os dados históricos."""
        data = {
            "performance": [],
            "errors": [],
            "decisions": [],
            "events": []
        }
        
        # Performance
        perf_path = Path("orkestra/memory/performance.json")
        if perf_path.exists():
            with open(perf_path) as f:
                data["performance"] = json.load(f).get("records", [])
        
        # Errors
        err_path = Path("orkestra/memory/errors.json")
        if err_path.exists():
            with open(err_path) as f:
                data["errors"] = json.load(f).get("errors", [])
        
        # Decisions
        dec_path = Path("orkestra/memory/decisions.json")
        if dec_path.exists():
            with open(dec_path) as f:
                data["decisions"] = json.load(f).get("decisions", [])
        
        # Events
        for year in ["2024", "2025"]:
            event_path = Path(f"data/event_dataset_{year}.json")
            if event_path.exists():
                with open(event_path) as f:
                    data["events"].extend(json.load(f).get("contracts", []))
        
        print(f"✅ Dados carregados:")
        print(f"   Performance: {len(data['performance'])} registros")
        print(f"   Errors: {len(data['errors'])} registros")
        print(f"   Decisions: {len(data['decisions'])} registros")
        print(f"   Events: {len(data['events'])} contratos")
        
        return data
    
    def detect_recurring_patterns(self, data: Dict) -> List[Dict]:
        """
        Detecta padrões que repetem >= 3x.
        """
        patterns = []
        
        # Pattern 1: Erros do mesmo tipo
        error_types = {}
        for err in data["errors"]:
            err_type = err.get("error_type", "unknown")
            if err_type not in error_types:
                error_types[err_type] = []
            error_types[err_type].append(err)
        
        for err_type, errs in error_types.items():
            if len(errs) >= 3:
                patterns.append({
                    "type": "RECURRING_ERROR",
                    "category": err_type,
                    "occurrences": len(errs),
                    "severity": errs[0].get("severity", "low"),
                    "suggestion": f"Implementar prevenção para {err_type}",
                    "evidence": errs[:3]
                })
        
        # Pattern 2: Margens consistentemente baixas
        low_margin_events = [e for e in data["performance"] 
                           if e.get("margin_pct", 0) < 0.25]
        if len(low_margin_events) >= 3:
            avg_margin = sum(e.get("margin_pct", 0) for e in low_margin_events) / len(low_margin_events)
            patterns.append({
                "type": "CONSISTENT_LOW_MARGIN",
                "category": "financial",
                "occurrences": len(low_margin_events),
                "average": avg_margin,
                "suggestion": f"Revisar pricing - margem média {avg_margin*100:.1f}% abaixo do target",
                "evidence": low_margin_events[:3]
            })
        
        # Pattern 3: Cancelamentos
        cancelled = [e for e in data["events"] if e.get("status") == "CANCELLED"]
        if len(cancelled) >= 2:
            patterns.append({
                "type": "CANCELLATION_PATTERN",
                "category": "operational",
                "occurrences": len(cancelled),
                "suggestion": "Analisar causas de cancelamento",
                "evidence": cancelled
            })
        
        # Pattern 4: Decisões que não melhoraram
        bad_decisions = [d for d in data["decisions"] 
                        if d.get("result") in ["margin_not_improved", "failure"]]
        if len(bad_decisions) >= 3:
            patterns.append({
                "type": "INEFFECTIVE_DECISION",
                "category": "strategic",
                "occurrences": len(bad_decisions),
                "suggestion": "Revisar framework de decisões",
                "evidence": bad_decisions[:3]
            })
        
        print(f"\n🔍 {len(patterns)} padrões detectados:")
        for p in patterns:
            print(f"   ⚠️ {p['type']}: {p['occurrences']}x - {p['suggestion']}")
        
        return patterns
    
    def create_hypothesis(self, pattern: Dict) -> Optional[Hypothesis]:
        """
        Cria hipótese de mudança baseada no padrão.
        """
        h_id = f"HYP_{pattern['type']}_{int(datetime.now().timestamp())}"
        
        if pattern["type"] == "RECURRING_ERROR":
            if pattern["category"] == "stockout":
                return Hypothesis(
                    id=h_id,
                    pattern_detected="stockout_recurring",
                    description="Rupturas de estoque recorrentes indicam previsão insuficiente",
                    proposed_change_type=ChangeType.METRIC_ADJUSTMENT,
                    current_value={"safety_margin": 0.20},
                    proposed_value={"safety_margin": 0.25},
                    expected_impact=15.0,  # Reduzir rupturas em 15%
                    risk_level=RiskLevel.LOW,
                    confidence=75.0,
                    evidence=pattern["evidence"]
                )
            
            elif pattern["category"] == "portion_calculation":
                return Hypothesis(
                    id=h_id,
                    pattern_detected="wrong_portion_sizing",
                    description="Porções mal calculadas causam desperdício",
                    proposed_change_type=ChangeType.NEW_RULE,
                    current_value="Cálculo manual",
                    proposed_value="Validador automático de porções",
                    expected_impact=8.0,  # Reduzir desperdício em 8%
                    risk_level=RiskLevel.MEDIUM,
                    confidence=65.0,
                    evidence=pattern["evidence"]
                )
        
        elif pattern["type"] == "CONSISTENT_LOW_MARGIN":
            return Hypothesis(
                id=h_id,
                pattern_detected="low_margin_trend",
                description=f"Margem média {pattern['average']*100:.1f}% consistentemente abaixo do target",
                proposed_change_type=ChangeType.CODE_DIFF,
                current_value="TARGET_MARGIN = 0.30",
                proposed_value="TARGET_MARGIN = 0.35 + alerta abaixo de 0.28",
                expected_impact=20.0,  # Melhorar margem em 5% absolutos
                risk_level=RiskLevel.HIGH,
                confidence=85.0,
                evidence=pattern["evidence"]
            )
        
        elif pattern["type"] == "INEFFECTIVE_DECISION":
            return Hypothesis(
                id=h_id,
                pattern_detected="change_supplier_not_working",
                description="Ação 'change_supplier' não melhorando margem conforme esperado",
                proposed_change_type=ChangeType.PROMPT_DIFF,
                current_value="Sugerir change_supplier quando margem < 30%",
                proposed_value="Sugerir change_supplier apenas se custo categoria > 40%",
                expected_impact=12.0,
                risk_level=RiskLevel.MEDIUM,
                confidence=60.0,
                evidence=pattern["evidence"]
            )
        
        return None
    
    def simulate_on_history(self, hypothesis: Hypothesis, data: Dict) -> SimulationResult:
        """
        Simula a hipótese no histórico de dados.
        """
        print(f"\n🔬 Simulando hipótese {hypothesis.id}...")
        
        events = data["events"]
        affected = 0
        successes = 0
        
        # Métricas antes
        before_metrics = {
            "avg_margin": sum(e.get("margin", 0) for e in events) / len(events) if events else 0,
            "success_rate": len([e for e in events if e.get("margin", 0) > 0.25]) / len(events) * 100 if events else 0
        }
        
        # Simular com nova regra/métrica
        after_metrics = before_metrics.copy()
        
        if hypothesis.proposed_change_type == ChangeType.METRIC_ADJUSTMENT:
            # Simular com margem de segurança maior
            if "safety_margin" in str(hypothesis.proposed_value):
                # Estimar que rupturas diminuem
                after_metrics["stockout_rate"] = 5.0  # De 15% para 5%
                affected = len([e for e in events if e.get("status") != "CANCELLED"])
                successes = int(affected * 0.85)
        
        elif hypothesis.proposed_change_type == ChangeType.CODE_DIFF:
            # Simular com novo target de margem
            if "TARGET_MARGIN" in str(hypothesis.proposed_value):
                # Eventos com margem 25-30% seriam alertados
                borderline = [e for e in events if 0.25 <= e.get("margin", 0) < 0.30]
                affected = len(borderline)
                # Estima que metade seria aprovado com ajuste
                successes = affected // 2
                after_metrics["avg_margin"] = before_metrics["avg_margin"] + 0.03
        
        elif hypothesis.proposed_change_type == ChangeType.NEW_RULE:
            # Validador de porções
            if "porc" in str(hypothesis.proposed_value).lower():
                waste_events = [e for e in events if e.get("contract_id", "").startswith("EVT")]
                affected = len(waste_events)
                successes = int(affected * 0.75)
                after_metrics["waste_reduction"] = 8.0
        
        # Calcular melhoria
        improvement = ((after_metrics.get("avg_margin", 0) - before_metrics["avg_margin"]) 
                      / before_metrics["avg_margin"] * 100) if before_metrics["avg_margin"] > 0 else 0
        
        # Side effects
        side_effects = []
        if hypothesis.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            side_effects.append("Pode reduzir volume de eventos aprovados")
        if hypothesis.proposed_change_type == ChangeType.PROMPT_DIFF:
            side_effects.append("Requer re-treinamento de agentes")
        
        return SimulationResult(
            hypothesis_id=hypothesis.id,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            improvement_pct=improvement,
            events_affected=affected,
            success_rate=(successes / affected * 100) if affected > 0 else 0,
            side_effects=side_effects
        )
    
    def assess_risk(self, hypothesis: Hypothesis, simulation: SimulationResult) -> str:
        """
        Avalia risco da proposta.
        """
        risk_factors = []
        
        # Risco base
        if hypothesis.risk_level == RiskLevel.HIGH:
            risk_factors.append("Mudança em parâmetro crítico")
        
        # Impacto no volume
        if simulation.events_affected > len(simulation.before_metrics.get("events", [])) * 0.3:
            risk_factors.append("Afeta >30% dos eventos")
        
        # Efeitos colaterais
        if simulation.side_effects:
            risk_factors.extend(simulation.side_effects)
        
        # Confiança baixa
        if hypothesis.confidence < 70:
            risk_factors.append("Confiança abaixo do threshold")
        
        if not risk_factors:
            return "RISCO BAIXO - Aprovação automática disponível"
        
        return " | ".join(risk_factors)
    
    def create_proposal(self, hypothesis: Hypothesis, 
                       simulation: SimulationResult,
                       risk: str) -> EvolutionProposal:
        """Cria proposta completa."""
        
        proposal_id = f"PROP_{hypothesis.id}_{int(datetime.now().timestamp())}"
        
        return EvolutionProposal(
            id=proposal_id,
            timestamp=datetime.now().isoformat(),
            hypothesis=hypothesis,
            simulation=simulation,
            risk_assessment=risk,
            approval_status="PENDING",
            production_ready=(hypothesis.risk_level == RiskLevel.LOW and 
                            simulation.improvement_pct > 0 and 
                            hypothesis.confidence > 80)
        )
    
    def generate_diff(self, hypothesis: Hypothesis) -> str:
        """Gera diff/simulação visual da mudança."""
        if hypothesis.proposed_change_type == ChangeType.METRIC_ADJUSTMENT:
            return f"""
--- a/metrics.py
+++ b/metrics.py
@@ -1,5 +1,5 @@
 # Safety margin for inventory
-SAFETY_MARGIN = {hypothesis.current_value.get('safety_margin', 0.20)}
+SAFETY_MARGIN = {hypothesis.proposed_value.get('safety_margin', 0.25)}
 """
        
        elif hypothesis.proposed_change_type == ChangeType.CODE_DIFF:
            return f"""
--- a/event_simulator.py
+++ b/event_simulator.py
@@ -1,5 +1,5 @@
 # Target margin threshold
-TARGET_MARGIN = 0.30
+TARGET_MARGIN = 0.35
 """
        
        elif hypothesis.proposed_change_type == ChangeType.PROMPT_DIFF:
            return f"""
--- a/prompts/decision.txt
+++ b/prompts/decision.txt
@@ -1,5 +1,8 @@
 Quando sugerir change_supplier:
-Custo > 40%
+Custo > 40% E
+Fornecedor já trocado < 2x no histórico
 """
        
        return "# Diff não disponível para este tipo de mudança"
    
    def print_proposal(self, proposal: EvolutionProposal):
        """Imprime proposta formatada."""
        h = proposal.hypothesis
        s = proposal.simulation
        
        print("\n" + "=" * 70)
        print("🧪 PROPOSTA DE EVOLUÇÃO - SANDBOX V4")
        print("=" * 70)
        
        print(f"\n[HYPOTHESIS] {h.id}")
        print(f"   Padrão: {h.pattern_detected}")
        print(f"   Descrição: {h.description}")
        print(f"   Tipo: {h.proposed_change_type.value}")
        
        print(f"\n[PROPOSED CHANGE]")
        print(f   De: {h.current_value}")
        print(f   Para: {h.proposed_value}")
        
        # Diff
        diff = self.generate_diff(h)
        if diff:
            print(f"\n[DIFF]\n{diff}")
        
        print(f"\n[SIMULATION RESULT]")
        print(f"   Eventos afetados: {s.events_affected}")
        print(f"   Taxa de sucesso: {s.success_rate:.1f}%")
        print(f"   Melhoria estimada: {s.improvement_pct:+.1f}%")
        
        print(f"   Antes:")
        for k, v in s.before_metrics.items():
            print(f"      {k}: {v}")
        print(f"   Depois:")
        for k, v in s.after_metrics.items():
            print(f"      {k}: {v}")
        
        if s.side_effects:
            print(f"\n[Side Effects]")
            for se in s.side_effects:
                print(f"   ⚠️ {se}")
        
        print(f"\n[RISK LEVEL] {h.risk_level.value}")
        print(f"   Assessment: {proposal.risk_assessment}")
        
        print(f"\n[CONFIDENCE] {h.confidence:.0f}%")
        
        status_icon = "⏳" if proposal.approval_status == "PENDING" else "✅" if proposal.approval_status == "APPROVED" else "❌"
        print(f"\n[APPROVAL STATUS] {status_icon} {proposal.approval_status}")
        
        if proposal.production_ready:
            print(f"\n🚀 PRONTO PARA PRODUÇÃO - Após aprovação")
        else:
            print(f"\n⚠️  REQUER APROVAÇÃO MANUAL")
        
        print("\n" + "=" * 70)
        print("💡 PARA APROVAR: /approve {proposal.id}")
        print("💡 PARA REJEITAR: /reject {proposal.id}")
        print("=" * 70)
    
    def save_proposal(self, proposal: EvolutionProposal):
        """Salva proposta para revisão."""
        output_path = Path(f"orkestra/sandbox/proposals/{proposal.id}.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "id": proposal.id,
            "timestamp": proposal.timestamp,
            "hypothesis": {
                "id": proposal.hypothesis.id,
                "pattern": proposal.hypothesis.pattern_detected,
                "change_type": proposal.hypothesis.proposed_change_type.value,
                "current": str(proposal.hypothesis.current_value),
                "proposed": str(proposal.hypothesis.proposed_value),
                "confidence": proposal.hypothesis.confidence
            },
            "simulation": {
                "events_affected": proposal.simulation.events_affected,
                "improvement_pct": proposal.simulation.improvement_pct,
                "success_rate": proposal.simulation.success_rate
            },
            "risk": proposal.risk_assessment,
            "status": proposal.approval_status,
            "production_ready": proposal.production_ready
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        return output_path
    
    def run_evolution_cycle(self):
        """Executa ciclo completo de evolução."""
        print("\n" + "=" * 70)
        print("🧬 ORKESTRA EVOLUTION SANDBOX V4")
        print("   Laboratório de Melhorias Automáticas")
        print("=" * 70)
        print("\n⚠️  IMPORTANTE: Todas as mudanças são propostas, NÃO aplicadas automaticamente")
        print("   Aprovação humana obrigatória para ir a produção")
        print("=" * 70)
        
        # 1. Carregar histórico
        print("\n📂 Carregando histórico...")
        data = self.load_historical_data()
        
        # 2. Detectar padrões
        print("\n🔍 Detectando padrões...")
        patterns = self.detect_recurring_patterns(data)
        
        if not patterns:
            print("\n✅ Nenhum padrão crítico detectado. Sistema está otimizado.")
            return []
        
        # 3. Criar hipóteses
        print("\n🧠 Criando hipóteses...")
        hypotheses = []
        for pattern in patterns:
            h = self.create_hypothesis(pattern)
            if h:
                hypotheses.append(h)
        
        print(f"   {len(hypotheses)} hipóteses geradas")
        
        # 4. Simular e criar propostas
        proposals = []
        for h in hypotheses:
            print(f"\n   Simulando {h.id}...")
            simulation = self.simulate_on_history(h, data)
            risk = self.assess_risk(h, simulation)
            proposal = self.create_proposal(h, simulation, risk)
            proposals.append(proposal)
            
            # Imprimir
            self.print_proposal(proposal)
            
            # Salvar
            path = self.save_proposal(proposal)
            print(f"\n💾 Proposta salva: {path}")
        
        # 5. Agregar pendentes
        self.pending_approvals = [p for p in proposals if p.approval_status == "PENDING"]
        
        print("\n" + "=" * 70)
        print("📊 RESUMO DO CICLO DE EVOLUÇÃO")
        print("=" * 70)
        print(f"   Padrões detectados: {len(patterns)}")
        print(f"   Hipóteses criadas: {len(hypotheses)}")
        print(f"   Propostas geradas: {len(proposals)}")
        print(f"   Aguardando aprovação: {len(self.pending_approvals)}")
        
        print(f"\n   📋 Comandos disponíveis:")
        print(f"      /list_proposals - Ver todas as propostas")
        print(f"      /approve [ID] - Aprovar proposta")
        print(f"      /reject [ID] - Rejeitar proposta")
        print(f"      /apply_approved - Aplicar todas aprovadas")
        
        print("\n" + "=" * 70)
        print("✅ EVOLUTION SANDBOX V4 COMPLETO")
        print("=" * 70)
        
        return proposals


def run_evolution_sandbox():
    """Entry point."""
    sandbox = EvolutionSandboxV4()
    return sandbox.run_evolution_cycle()


if __name__ == "__main__":
    run_evolution_sandbox()
