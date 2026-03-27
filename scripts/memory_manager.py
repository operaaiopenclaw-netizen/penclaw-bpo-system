# memory_manager.py - Orkestra Memory Layer 2
# Sistema de aprendizado e memória operacional

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


# Diretório de memória
MEMORY_DIR = Path("memory")


def ensure_memory_dir():
    """Garante que o diretório de memória existe."""
    MEMORY_DIR.mkdir(exist_ok=True)


@dataclass
class DecisionRecord:
    """Registro de decisão tomada e seu resultado."""
    id: str
    timestamp: str
    event: str
    margin: float
    margin_before: float
    issue: str
    cause: str
    action: str
    result: str
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DecisionRecord":
        return cls(**data)


@dataclass
class ErrorRecord:
    """Registro de erro ou incidente para análise futura."""
    id: str
    timestamp: str
    event: str
    error_type: str
    severity: str  # low, medium, high, critical
    description: str
    impact: str
    resolution: str
    prevention: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ErrorRecord":
        return cls(**data)


@dataclass
class PerformanceRecord:
    """Registro de métricas de performance por evento/período."""
    id: str
    timestamp: str
    event: str
    period: str  # daily, weekly, monthly, event
    revenue: float
    costs: float
    margin_pct: float
    targets_met: List[str]
    targets_missed: List[str]
    kpis: Dict[str, float]
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PerformanceRecord":
        return cls(**data)


class MemoryLayer:
    """
    Camada 2 de memória - Aprendizado operacional
    """
    
    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        ensure_memory_dir()
        
        # Arquivos de memória
        self.decisions_file = self.memory_dir / "decisions.json"
        self.errors_file = self.memory_dir / "errors.json"
        self.performance_file = self.memory_dir / "performance.json"
        
        # Inicializar arquivos se não existirem
        self._init_files()
    
    def _init_files(self):
        """Inicializa arquivos JSON se não existirem."""
        files_defaults = {
            self.decisions_file: {"decisions": [], "metadata": {"version": "1.0", "last_update": ""}},
            self.errors_file: {"errors": [], "metadata": {"version": "1.0", "last_update": ""}},
            self.performance_file: {"records": [], "metadata": {"version": "1.0", "last_update": ""}}
        }
        
        for filepath, default in files_defaults.items():
            if not filepath.exists():
                self._write_json(filepath, default)
    
    def _read_json(self, filepath: Path) -> Dict:
        """Lê arquivo JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_json(self, filepath: Path, data: Dict):
        """Escreve arquivo JSON atualizando timestamp."""
        if "metadata" in data:
            data["metadata"]["last_update"] = datetime.now().isoformat()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _generate_id(self, prefix: str) -> str:
        """Gera ID único com prefixo e timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}"
    
    # ============================================
    # DECISIONS - Aprendizado de decisões
    # ============================================
    
    def add_decision(self, event: str, margin: float, issue: str, 
                     cause: str, action: str, result: str, 
                     margin_before: float = 0, notes: str = "") -> str:
        """
        Adiciona uma decisão ao histórico.
        """
        decision = DecisionRecord(
            id=self._generate_id("DEC"),
            timestamp=datetime.now().isoformat(),
            event=event,
            margin=margin,
            margin_before=margin_before,
            issue=issue,
            cause=cause,
            action=action,
            result=result,
            notes=notes
        )
        
        data = self._read_json(self.decisions_file)
        data["decisions"].insert(0, decision.to_dict())  # Novos primeiro
        self._write_json(self.decisions_file, data)
        
        return decision.id
    
    def get_decisions(self, event: Optional[str] = None, 
                      limit: int = 50) -> List[DecisionRecord]:
        """
        Recupera decisões, opcionalmente filtradas por evento.
        """
        data = self._read_json(self.decisions_file)
        decisions = [DecisionRecord.from_dict(d) for d in data["decisions"]]
        
        if event:
            decisions = [d for d in decisions if d.event == event]
        
        return decisions[:limit]
    
    def get_successful_actions(self, issue_type: str, limit: int = 5) -> List[str]:
        """
        Recupera ações que funcionaram para um tipo de problema.
        Aprendizado ativo - reutiliza soluções que deram certo.
        """
        decisions = self.get_decisions(limit=100)
        successful = [
            d.action for d in decisions 
            if d.issue == issue_type and d.result in ["margin_improved", "success", "resolved"]
        ]
        return list(dict.fromkeys(successful))[:limit]  # Remove duplicatas
    
    def find_similar_issues(self, event: str, margin: float, 
                           threshold: float = 0.05) -> List[DecisionRecord]:
        """
        Encontra problemas similares no histórico.
        """
        decisions = self.get_decisions(limit=100)
        similar = [
            d for d in decisions 
            if abs(d.margin - margin) <= threshold and d.event != event
        ]
        return similar
    
    # ============================================
    # ERRORS - Aprendizado de erros
    # ============================================
    
    def add_error(self, event: str, error_type: str, severity: str,
                  description: str, impact: str, resolution: str, 
                  prevention: str) -> str:
        """
        Registra um erro ou incidente para análise futura.
        """
        error = ErrorRecord(
            id=self._generate_id("ERR"),
            timestamp=datetime.now().isoformat(),
            event=event,
            error_type=error_type,
            severity=severity,
            description=description,
            impact=impact,
            resolution=resolution,
            prevention=prevention
        )
        
        data = self._read_json(self.errors_file)
        data["errors"].insert(0, error.to_dict())
        self._write_json(self.errors_file, data)
        
        return error.id
    
    def get_errors(self, severity: Optional[str] = None, 
                  event: Optional[str] = None) -> List[ErrorRecord]:
        """
        Recupera erros registrados.
        """
        data = self._read_json(self.errors_file)
        errors = [ErrorRecord.from_dict(e) for e in data["errors"]]
        
        if severity:
            errors = [e for e in errors if e.severity == severity]
        if event:
            errors = [e for e in errors if e.event == event]
        
        return errors
    
    def get_prevention_tips(self, error_type: str) -> List[str]:
        """
        Retorna dicas de prevenção baseadas em erros passados.
        """
        errors = self.get_errors()
        tips = [
            e.prevention for e in errors 
            if e.error_type == error_type
        ]
        return list(dict.fromkeys(tips))
    
    # ============================================
    # PERFORMANCE - Histórico de desempenho
    # ============================================
    
    def add_performance(self, event: str, revenue: float, costs: float,
                       targets_met: List[str], targets_missed: List[str],
                       kpis: Dict[str, float], period: str = "event") -> str:
        """
        Registra métricas de performance de um evento.
        """
        margin_pct = ((revenue - costs) / revenue * 100) if revenue > 0 else 0
        
        record = PerformanceRecord(
            id=self._generate_id("PERF"),
            timestamp=datetime.now().isoformat(),
            event=event,
            period=period,
            revenue=revenue,
            costs=costs,
            margin_pct=margin_pct,
            targets_met=targets_met,
            targets_missed=targets_missed,
            kpis=kpis
        )
        
        data = self._read_json(self.performance_file)
        data["records"].insert(0, record.to_dict())
        self._write_json(self.performance_file, data)
        
        return record.id
    
    def get_performance(self, event: Optional[str] = None) -> List[PerformanceRecord]:
        """
        Recupera registros de performance.
        """
        data = self._read_json(self.performance_file)
        records = [PerformanceRecord.from_dict(r) for r in data["records"]]
        
        if event:
            records = [r for r in records if r.event == event]
        
        return records
    
    def get_average_margin(self, last_n: int = 10) -> float:
        """
        Calcula margem média dos últimos N eventos.
        """
        records = self.get_performance()[:last_n]
        if not records:
            return 0.0
        return sum(r.margin_pct for r in records) / len(records)
    
    def get_trend(self, metric: str = "margin_pct", last_n: int = 10) -> str:
        """
        Retorna tendência de um métrica.
        """
        records = self.get_performance()[:last_n]
        if len(records) < 3:
            return "insufficient_data"
        
        # Analisar primeira metade vs segunda metade
        mid = len(records) // 2
        first_half = sum(r.kpis.get(metric, r.margin_pct) for r in records[:mid]) / mid if mid > 0 else 0
        second_half = sum(r.kpis.get(metric, r.margin_pct) for r in records[mid:]) / (len(records) - mid)
        
        diff = second_half - first_half
        if diff > 2:
            return "improving"
        elif diff < -2:
            return "declining"
        return "stable"
    
    # ============================================
    # INSIGHTS - Inteligência da memória
    # ============================================
    
    def generate_insights(self) -> Dict[str, Any]:
        """
        Gera insights baseados nos dados de memória.
        """
        avg_margin = self.get_average_margin(20)
        trend = self.get_trend()
        
        # Problemas recorrentes
        decisions = self.get_decisions(limit=30)
        issues = {}
        for d in decisions:
            issues[d.issue] = issues.get(d.issue, 0) + 1
        top_issues = sorted(issues.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Sugestões baseadas em ações que deram certo
        suggestions = {}
        for issue, _ in top_issues:
            actions = self.get_successful_actions(issue, 3)
            if actions:
                suggestions[issue] = actions
        
        return {
            "avg_margin_last_20": round(avg_margin, 2),
            "trend": trend,
            "top_recurring_issues": [i[0] for i in top_issues],
            "suggested_actions": suggestions,
            "total_decisions": len(decisions),
            "total_errors": len(self.get_errors())
        }
    
    def get_context_for_decision(self, event: str, margin: float, 
                                 issue: str) -> Dict[str, Any]:
        """
        Recupera contexto relevante para tomada de decisão.
        """
        similar = self.find_similar_issues(event, margin)
        successful_actions = self.get_successful_actions(issue, 3)
        avg_margin = self.get_average_margin(10)
        trend = self.get_trend()
        
        return {
            "similar_past_issues": [s.to_dict() for s in similar[:3]],
            "actions_that_worked": successful_actions,
            "avg_margin_benchmark": avg_margin,
            "current_trend": trend,
            "recommendation": "learned" if similar else "new_case"
        }


# Instância singleton para uso global
memory = MemoryLayer()


# ============================================
# FUNÇÕES DE CONVENIÊNCIA
# ============================================

def log_decision(event: str, margin: float, issue: str, cause: str,
                 action: str, result: str, margin_before: float = 0) -> str:
    """Registra uma decisão."""
    return memory.add_decision(event, margin, issue, cause, action, result, margin_before)


def log_error(event: str, error_type: str, severity: str, description: str,
              impact: str, resolution: str, prevention: str) -> str:
    """Registra um erro."""
    return memory.add_error(event, error_type, severity, description, impact, resolution, prevention)


def log_performance(event: str, revenue: float, costs: float, 
                  targets_met: List[str], targets_missed: List[str],
                  kpis: Dict[str, float]) -> str:
    """Registra performance."""
    return memory.add_performance(event, revenue, costs, targets_met, targets_missed, kpis)


def get_smart_suggestions(issue: str, margin: float) -> List[str]:
    """Obtém sugestões inteligentes baseadas em memória."""
    actions = memory.get_successful_actions(issue, 5)
    return actions if actions else ["Nenhum histórico similar - analisar caso a caso"]


# Exemplo de uso
if __name__ == "__main__":
    mem = MemoryLayer()
    
    # Exemplo: registrar decisão
    decision_id = mem.add_decision(
        event="medicina_formatura",
        margin=0.22,
        margin_before=0.18,
        issue="low_margin",
        cause="high_beverage_cost",
        action="change_supplier",
        result="margin_improved",
        notes="Troca de fornecedor de bebidas resultou em economia de 15%"
    )
    
    print(f"Decisão registrada: {decision_id}")
    
    # Recuperar insights
    insights = mem.generate_insights()
    print(f"\nInsights: {json.dumps(insights, indent=2)}")
