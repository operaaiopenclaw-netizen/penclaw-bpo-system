# self_improvement_agent.py - Orkestra Self Improvement Agent
# Analisa histórico e sugere ajustes estruturados (não altera código)

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass


MEMORY_DIR = Path("memory")


@dataclass
class Pattern:
    """Padrão identificado na análise."""
    tipo: str  # "positivo", "negativo", "neutro"
    descricao: str
    frequencia: int
    impacto_medio: float
    exemplos: List[str]
    confianca: float  # 0-1


@dataclass
class RegraSugerida:
    """Regra sugerida baseada em análise."""
    categoria: str  # "margem", "categoria", "operacional", "financeiro"
    tipo: str  # "ajuste", "novo", "remocao"
    descricao: str
    justificativa: str
    implementacao: str
    prioridade: str  # "alta", "media", "baixa"


class SelfImprovementAgent:
    """
    Agente de auto-melhoria que analisa histórico e sugere ajustes.
    NÃO ALTERA CÓDIGO - apenas gera sugestões estruturadas.
    """
    
    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
    
    def _load_json(self, filename: str) -> Dict:
        """Carrega arquivo JSON de memória."""
        filepath = self.memory_dir / filename
        if not filepath.exists():
            return {"data": []}
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_recent_data(self, data: List[Dict], dias: int = 90) -> List[Dict]:
        """Filtra dados dos últimos N dias."""
        cutoff = datetime.now() - timedelta(days=dias)
        recent = []
        for item in data:
            ts = item.get("timestamp", "")
            if ts:
                try:
                    item_date = datetime.fromisoformat(ts)
                    if item_date >= cutoff:
                        recent.append(item)
                except:
                    recent.append(item)
            else:
                recent.append(item)
        return recent
    
    # ============================================
    # ANÁLISE DE PADRÕES
    # ============================================
    
    def analyze_decision_patterns(self) -> List[Pattern]:
        """
        Analisa padrões em decisões passadas.
        Identifica o que funcionou vs o que não funcionou.
        """
        data = self._load_json("decisions.json")
        decisions = data.get("decisions", [])
        
        if len(decisions) < 3:
            return [Pattern(
                tipo="neutro",
                descricao="Dados insuficientes para identificar padrões (mínimo 3 decisões)",
                frequencia=0,
                impacto_medio=0.0,
                exemplos=[],
                confianca=0.0
            )]
        
        patterns = []
        
        # Padrão 1: Ações que melhoraram margem
        success_actions = {}
        for d in decisions:
            result = d.get("result", "")
            action = d.get("action", "")
            margin_delta = d.get("margin", 0) - d.get("margin_before", 0)
            
            if result in ["margin_improved", "success", "resolved"] and margin_delta > 0:
                if action not in success_actions:
                    success_actions[action] = {"count": 0, "delta": 0, "examples": []}
                success_actions[action]["count"] += 1
                success_actions[action]["delta"] += margin_delta
                success_actions[action]["examples"].append(d.get("event", "?"))
        
        for action, data in success_actions.items():
            if data["count"] >= 2:
                patterns.append(Pattern(
                    tipo="positivo",
                    descricao=f"Ação '{action}' consistentemente melhora margem",
                    frequencia=data["count"],
                    impacto_medio=data["delta"] / data["count"],
                    exemplos=data["examples"][:3],
                    confianca=min(0.9, 0.5 + (data["count"] * 0.1))
                ))
        
        # Padrão 2: Causas de margem baixa
        low_margin_causes = {}
        for d in decisions:
            if d.get("margin", 0) < 0.25:  # margem < 25%
                cause = d.get("cause", "unknown")
                if cause not in low_margin_causes:
                    low_margin_causes[cause] = {"count": 0, "examples": []}
                low_margin_causes[cause]["count"] += 1
                low_margin_causes[cause]["examples"].append(d.get("event", "?"))
        
        for cause, data in low_margin_causes.items():
            if data["count"] >= 2:
                patterns.append(Pattern(
                    tipo="negativo",
                    descricao=f"'{cause}' é causa recorrente de margem baixa",
                    frequencia=data["count"],
                    impacto_medio=-0.15,  # impacto negativo estimado
                    exemplos=data["examples"][:3],
                    confianca=min(0.85, 0.4 + (data["count"] * 0.1))
                ))
        
        # Padrão 3: Tipos de problemas mais comuns
        issue_types = {}
        for d in decisions:
            issue = d.get("issue", "unknown")
            issue_types[issue] = issue_types.get(issue, 0) + 1
        
        most_common = sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:3]
        for issue, count in most_common:
            if count >= 2:
                patterns.append(Pattern(
                    tipo="neutro",
                    descricao=f"'{issue}' é o tipo de problema mais frequente",
                    frequencia=count,
                    impacto_medio=0.0,
                    exemplos=[d.get("event", "?") for d in decisions if d.get("issue") == issue][:3],
                    confianca=0.7
                ))
        
        return patterns
    
    def analyze_error_patterns(self) -> List[Pattern]:
        """
        Analisa padrões em erros/incidentes.
        """
        data = self._load_json("errors.json")
        errors = data.get("errors", [])
        
        if len(errors) < 2:
            return []
        
        patterns = []
        
        # Erros por tipo
        error_types = {}
        for e in errors:
            err_type = e.get("error_type", "unknown")
            if err_type not in error_types:
                error_types[err_type] = {"count": 0, "severity_sum": 0}
            error_types[err_type]["count"] += 1
            
            severity_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            sev = severity_map.get(e.get("severity", "low"), 1)
            error_types[err_type]["severity_sum"] += sev
        
        for err_type, data in error_types.items():
            if data["count"] >= 2:
                avg_severity = data["severity_sum"] / data["count"]
                patterns.append(Pattern(
                    tipo="negativo",
                    descricao=f"Erros tipo '{err_type}' ocorrem com frequência (severidade média: {avg_severity:.1f})",
                    frequencia=data["count"],
                    impacto_medio=-avg_severity,
                    exemplos=[],
                    confianca=0.8
                ))
        
        return patterns
    
    def analyze_performance_trends(self) -> Dict[str, Any]:
        """
        Analisa tendências de performance.
        """
        data = self._load_json("performance.json")
        records = data.get("records", [])
        
        if len(records) < 3:
            return {"status": "insufficient_data"}
        
        # Calcular tendência de margem
        margins = [r.get("margin_pct", 0) for r in records]
        
        first_half = sum(margins[:len(margins)//2]) / (len(margins)//2) if len(margins) > 1 else 0
        second_half = sum(margins[len(margins)//2:]) / (len(margins) - len(margins)//2) if len(margins) > 1 else 0
        
        delta = second_half - first_half
        
        trend = "stable"
        if delta > 3:
            trend = "improving"
        elif delta < -3:
            trend = "declining"
        
        # Targets mais perdidos
        missed = []
        for r in records:
            missed.extend(r.get("targets_missed", []))
        
        from collections import Counter
        top_missed = Counter(missed).most_common(3)
        
        return {
            "status": "analyzed",
            "trend": trend,
            "margin_delta": round(delta, 2),
            "avg_margin": round(sum(margins) / len(margins), 2),
            "most_missed_targets": [t[0] for t in top_missed],
            "data_points": len(records)
        }
    
    # ============================================
    # GERAÇÃO DE REGRAS SUGERIDAS
    # ============================================
    
    def generate_rule_suggestions(self) -> List[RegraSugerida]:
        """
        Gera sugestões de regras baseadas em análise.
        """
        suggestions = []
        
        # Analisar padrões
        patterns = self.analyze_decision_patterns()
        error_patterns = self.analyze_error_patterns()
        trends = self.analyze_performance_trends()
        
        # Sugestão 1: Ajustar thresholds de margem se tendência estável
        if trends.get("trend") == "stable" and trends.get("avg_margin", 0) < 25:
            suggestions.append(RegraSugerida(
                categoria="margem",
                tipo="ajuste",
                descricao="Reduzir threshold mínimo de margem de 30% para 25%",
                justificativa=f"Margem média histórica é {trends.get('avg_margin', 0)}%. Threshold atual de 30% está gerando alertas excessivos.",
                implementacao="Alterar 'MARGEM_MINIMA' em event_profitability_agent.py de 0.30 para 0.25",
                prioridade="media"
            ))
        
        # Sugestão 2: Aumentar threshold de margem se tendência negativa
        if trends.get("trend") == "declining":
            suggestions.append(RegraSugerida(
                categoria="margem",
                tipo="ajuste",
                descricao="Aumentar threshold de alerta de margem de 30% para 35%",
                justificativa=f"Tendência de queda detectada (delta: {trends.get('margin_delta', 0)}%). Necessário maior cautela.",
                implementacao="Alterar 'MARGEM_MINIMA_ALERTA' em financial_analyzer.py de 0.30 para 0.35",
                prioridade="alta"
            ))
        
        # Sugestão 3: Novas regras para causas recorrentes
        for p in patterns:
            if p.tipo == "negativo" and "casa" in p.descricao.lower():
                cause = p.descricao.split("'")[1] if "'" in p.descricao else "custo"
                suggestions.append(RegraSugerida(
                    categoria="categoria",
                    tipo="novo",
                    descricao=f"Alerta preventivo quando '{cause}' identificado em estimativa inicial",
                    justificativa=f"'{cause}' causou {p.frequencia} casos de margem baixa. Requer monitoramento antecipado.",
                    implementacao="Adicionar validação em procurement_agent.py: verificar se '{cause}' nas projeções e alertar",
                    prioridade="alta" if p.frequencia >= 3 else "media"
                ))
        
        # Sugestão 4: Ações que deram certo virarem regras automáticas
        for p in patterns:
            if p.tipo == "positivo" and p.confianca >= 0.7:
                action = p.descricao.split("'")[1] if "'" in p.descricao else "ação"
                suggestions.append(RegraSugerida(
                    categoria="operacional",
                    tipo="novo",
                    descricao=f"Sugerir automaticamente '{action}' quando condições similares detectadas",
                    justificativa=f"Ação melhorou margem em {p.frequencia} eventos com confiança {p.confianca:.0%}",
                    implementacao="Integrar memory_manager em decision flow: quando issue=X encontrado, sugerir action=Y",
                    prioridade="baixa" if p.frequencia < 3 else "media"
                ))
        
        # Sugestão 5: Margem de segurança em compras
        perf_data = self._load_json("performance.json")
        records = perf_data.get("records", [])
        if records:
            rupturas_estimadas = sum(1 for r in records if "ruptura" in str(r.get("targets_missed", [])))
            if rupturas_estimadas > 0:
                suggestions.append(RegraSugerida(
                    categoria="operacional",
                    tipo="ajuste",
                    descricao="Aumentar margem de segurança de estoque de 20% para 25%",
                    justificativa=f"Detectadas {rupturas_estimadas} rupturas em histórico. Estoque atual é insuficiente.",
                    implementacao="Alterar 'MARGEM_SEGURANCA' em procurement_agent.py de 0.20 para 0.25",
                    prioridade="media"
                ))
        
        # Sugestão 6: Thresholds de categoria
        for p in patterns:
            if "bebida" in p.descricao.lower() or "bebidas" in p.descricao.lower():
                suggestions.append(RegraSugerida(
                    categoria="categoria",
                    tipo="ajuste",
                    descricao="Reduzir threshold alerta de bebidas de 40% para 35%",
                    justificativa="Bebidas frequentemente causam problemas de margem. Monitoramento mais rigoroso necessário.",
                    implementacao="Alterar 'THRESHOLD_BEBIDAS' em financial_analyzer.py de 0.40 para 0.35",
                    prioridade="media"
                ))
        
        return suggestions
    
    # ============================================
    # RELATÓRIO FINAL
    # ============================================
    
    def generate_report(self) -> str:
        """
        Gera relatório completo de auto-melhoria.
        NÃO ALTERA CÓDIGO - apenas sugere.
        """
        patterns = self.analyze_decision_patterns()
        error_patterns = self.analyze_error_patterns()
        trends = self.analyze_performance_trends()
        rules = self.generate_rule_suggestions()
        
        output = []
        output.append("=" * 70)
        output.append("🎛️ ORKESTRA SELF IMPROVEMENT ANALYSIS")
        output.append("=" * 70)
        output.append(f"📅 Análise gerada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("")
        
        # [1] INSIGHTS - Padrões identificados
        output.append("[1] INSIGHTS - PADRÕES IDENTIFICADOS")
        output.append("-" * 50)
        
        if patterns or error_patterns:
            for p in patterns + error_patterns:
                emoji = "✅" if p.tipo == "positivo" else "⚠️" if p.tipo == "neutro" else "🔴"
                output.append(f"\n{emoji} {p.descricao}")
                output.append(f"   Frequência: {p.frequencia} ocorrências")
                output.append(f"   Confiânça: {p.confianca:.0%}")
                if p.exemplos:
                    output.append(f"   Exemplos: {', '.join(p.exemplos)}")
        else:
            output.append("   ℹ️ Dados insuficientes para identificar padrões significativos.")
            output.append("   Recomendação: Acumular mais dados operacionais.")
        
        # Tendências
        if trends.get("status") == "analyzed":
            output.append("\n📊 TENDÊNCIAS DE PERFORMANCE:")
            trend_emoji = "📈" if trends.get("trend") == "improving" else "📉" if trends.get("trend") == "declining" else "➡️"
            output.append(f"   {trend_emoji} Tendência de margem: {trends.get('trend', 'stable')}")
            output.append(f"   📊 Margem média: {trends.get('avg_margin', 0)}%")
            if trends.get("most_missed_targets"):
                output.append(f"   🎯 Targets mais perdidos: {', '.join(trends['most_missed_targets'])}")
        
        # [2] REGRAS SUGERIDAS
        output.append("\n" + "=" * 70)
        output.append("[2] REGRAS SUGERIDAS - AJUSTES ESTRUTURADOS")
        output.append("=" * 70)
        output.append("⚠️  AVISO: Estas são SUGESTÕES. Revisar antes de implementar.")
        output.append("")
        
        if rules:
            for i, rule in enumerate(rules, 1):
                prioridade_emoji = "🔴" if rule.prioridade == "alta" else "🟡" if rule.prioridade == "media" else "🟢"
                output.append(f"\n[{i}] {prioridade_emoji} {rule.categoria.upper()} - {rule.tipo.upper()}")
                output.append(f"   📋 Descrição: {rule.descricao}")
                output.append(f"   💭 Justificativa: {rule.justificativa}")
                output.append(f"   🔧 Implementação: {rule.implementacao}")
                output.append(f"   ⚡ Prioridade: {rule.prioridade.upper()}")
        else:
            output.append("   ✅ Nenhuma regra requer ajuste no momento.")
            output.append("   Sistema operando dentro dos parâmetros esperados.")
        
        # [3] AÇÕES RECOMENDADAS
        output.append("\n" + "=" * 70)
        output.append("[3] PRÓXIMOS PASSOS RECOMENDADOS")
        output.append("=" * 70)
        
        if rules:
            high_priority = [r for r in rules if r.prioridade == "alta"]
            if high_priority:
                output.append("\n🔴 PRIORIDADE ALTA (implementar imediatamente):")
                for r in high_priority:
                    output.append(f"   • {r.descricao}")
            
            med_priority = [r for r in rules if r.prioridade == "media"]
            if med_priority:
                output.append("\n🟡 PRIORIDADE MÉDIA (implementar esta semana):")
                for r in med_priority:
                    output.append(f"   • {r.descricao}")
        
        output.append("\n📝 CHECKLIST DE IMPLEMENTAÇÃO:")
        output.append("   [ ] Revisar sugestões com equipe")
        output.append("   [ ] Validar mudanças em ambiente de teste")
        output.append("   [ ] Documentar alterações em AGENTS.md")
        output.append("   [ ] Monitorar impacto nas próximas 5 operações")
        
        output.append("\n" + "=" * 70)
        output.append("🎛️ ORKESTRA SELF IMPROVEMENT COMPLETE")
        output.append("=" * 70)
        
        return "\n".join(output)
    
    def export_suggestions_json(self, filepath: str = "memory/improvement_suggestions.json"):
        """
        Exporta sugestões em formato JSON para integração.
        """
        rules = self.generate_rule_suggestions()
        trends = self.analyze_performance_trends()
        
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "suggestions": [
                {
                    "categoria": r.categoria,
                    "tipo": r.tipo,
                    "descricao": r.descricao,
                    "justificativa": r.justificativa,
                    "implementacao": r.implementacao,
                    "prioridade": r.prioridade
                }
                for r in rules
            ],
            "trends": trends,
            "requires_action": len([r for r in rules if r.prioridade == "alta"]) > 0
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return filepath


# Execução principal
if __name__ == "__main__":
    import sys
    
    agent = SelfImprovementAgent()
    
    # Gerar relatório
    report = agent.generate_report()
    print(report)
    
    # Exportar JSON
    json_path = agent.export_suggestions_json()
    print(f"\n📁 Sugestões exportadas: {json_path}")
