# learning_engine_v2.py - Orkestra Adaptive Learning Engine V2
# Transforma dados históricos em inteligência adaptativa

import json
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Pattern:
    """Padrão detectado no aprendizado."""
    category: str
    item: str
    occurrence_count: int
    avg_error: float
    direction: str  # 'excess' or 'shortage'
    suggested_adjustment: float
    confidence: float


@dataclass
class Rule:
    """Regra gerada pelo aprendizado."""
    id: str
    condition: str
    action: str
    impact_expected: float
    confidence: float
    created_at: str
    triggered_count: int = 0
    success_count: int = 0


class LearningEngineV2:
    """
    Motor de aprendizado adaptativo V2.
    Aprende com eventos realizados e ajusta métricas automaticamente.
    """
    
    def __init__(self):
        self.events_realized = []
        self.forecasts = []
        self.consumption_real = []
        self.financial_actual = []
        self.patterns = defaultdict(list)
        self.rules = []
        self.metrics = {
            "beverage": {
                "agua_lpp": 1.2,
                "cerveja_cpp": 2.0,
                "refrigerante_lpp": 0.5,
                "suco_lpp": 0.3,
                "gelo_kgpp": 1.6
            },
            "food_cost_pct": 0.30,
            "staff_ratio": 0.15,
            "margin_target": 0.30,
            "min_margin_acceptable": 0.25
        }
    
    def load_historical_data(self):
        """Carrega todos os dados históricos para análise."""
        print("\n📂 Carregando dados históricos...")
        
        # Carregar eventos realizados
        for year in ["2024", "2025"]:
            path = Path(f"data/event_dataset_{year}.json")
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    for contract in data.get("contracts", []):
                        if contract.get("status") in ["EXECUTED", "COMPLETED", "REALIZADO", "FINALIZADO"]:
                            self.events_realized.append(contract)
        
        # Carregar financial log
        log_path = Path("financial_log.json")
        if log_path.exists():
            with open(log_path) as f:
                self.financial_actual = json.load(f).get("transactions", [])
        
        # Carregar memory
        mem_path = Path("memory/performance.json")
        if mem_path.exists():
            with open(mem_path) as f:
                self.consumption_real = json.load(f).get("records", [])
        
        print(f"   ✅ {len(self.events_realized)} eventos realizados")
        print(f"   ✅ {len(self.financial_actual)} transações financeiras")
        print(f"   ✅ {len(self.consumption_real)} registros de consumo")
        
        return self
    
    def calculate_consumption_error(self, event_id: str) -> Dict:
        """
        Calcula erro de consumo: real vs previsto.
        """
        # Buscar consumo real (se disponível)
        real = next((r for r in self.consumption_real if r.get("event") == event_id), None)
        
        if not real:
            return {"available": False}
        
        # Buscar evento
        event = next((e for e in self.events_realized if e.get("contract_id") == event_id), None)
        if not event:
            return {"available": False}
        
        people = real.get("participants", event.get("people", 100))
        
        # Previsão original (baseada em métricas atuais)
        forecast = {
            "agua": people * self.metrics["beverage"]["agua_lpp"],
            "cerveja": people * self.metrics["beverage"]["cerveja_cpp"],
            "refrigerante": people * self.metrics["beverage"]["refrigerante_lpp"],
            "suco": people * self.metrics["beverage"]["suco_lpp"],
            "gelo": people * self.metrics["beverage"]["gelo_kgpp"]
        }
        
        # Consumo real (dos registros)
        actual = real.get("consumption", {})
        
        # Calcular erros
        errors = {}
        for item in forecast.keys():
            predicted = forecast[item]
            actual_val = actual.get(item, 0)
            error = actual_val - predicted
            error_pct = (error / predicted * 100) if predicted > 0 else 0
            
            errors[item] = {
                "predicted": predicted,
                "actual": actual_val,
                "error": error,
                "error_pct": error_pct,
                "direction": "excess" if error > 0 else "shortage" if error < 0 else "ok"
            }
        
        return {
            "available": True,
            "event_id": event_id,
            "people": people,
            "forecast": forecast,
            "actual": actual,
            "errors": errors
        }
    
    def calculate_financial_error(self, event_id: str) -> Dict:
        """
        Calcula erro financeiro: lucro real vs previsto.
        """
        # Buscar receita real
        event = next((e for e in self.events_realized if e.get("contract_id") == event_id), None)
        if not event:
            return {"available": False}
        
        revenue_actual = event.get("revenue_total", 0)
        
        # Custo previsto (baseado no forecast)
        from event_simulator_engine import simulate_event
        
        event_for_sim = {
            "name": event_id,
            "expected_revenue": revenue_actual,
            "people": event.get("people", 100),
            "has_open_bar": True,
            "high_staff": True
        }
        sim = simulate_event(event_for_sim)
        
        cost_predicted = sim["custo_estimado"]
        profit_predicted = revenue_actual - cost_predicted
        margin_predicted = profit_predicted / revenue_actual if revenue_actual > 0 else 0
        
        # Custo real (dos registros financeiros)
        costs_actual = sum(t.get("value", 0) for t in self.financial_actual 
                          if t.get("event") == event_id and t.get("type") != "income")
        
        profit_actual = revenue_actual - costs_actual
        margin_actual = profit_actual / revenue_actual if revenue_actual > 0 else 0
        
        return {
            "available": True,
            "event_id": event_id,
            "revenue": revenue_actual,
            "cost_predicted": cost_predicted,
            "cost_actual": costs_actual,
            "profit_predicted": profit_predicted,
            "profit_actual": profit_actual,
            "margin_predicted": margin_predicted,
            "margin_actual": margin_actual,
            "error_profit": profit_actual - profit_predicted,
            "error_margin": margin_actual - margin_predicted
        }
    
    def analyze_patterns(self, min_occurrences: int = 3) -> List[Pattern]:
        """
        Detecta padrões que se repetem ≥3x.
        """
        print("\n🔍 Analisando padrões...")
        
        # Agrupar erros por categoria
        errors_by_item = defaultdict(list)
        
        for event in self.events_realized:
            event_id = event.get("contract_id")
            cons_error = self.calculate_consumption_error(event_id)
            
            if cons_error.get("available"):
                for item, data in cons_error.get("errors", {}).items():
                    if data["direction"] != "ok":
                        errors_by_item[item].append({
                            "event_id": event_id,
                            "error": data["error"],
                            "error_pct": data["error_pct"],
                            "direction": data["direction"]
                        })
        
        patterns = []
        
        for item, errors in errors_by_item.items():
            if len(errors) >= min_occurrences:
                # Calcular erro médio
                avg_error = statistics.mean(e["error_pct"] for e in errors)
                direction = errors[0]["direction"]
                
                # Sugerir ajuste
                if direction == "excess":
                    # Sobrou - reduzir previsão
                    adjustment = -abs(avg_error) * 0.8  # Reduzir 80% do erro
                else:
                    # Faltou - aumentar previsão
                    adjustment = abs(avg_error) * 1.2  # Aumentar 120% do erro
                
                # Confiança baseada em consistência
                std_dev = statistics.stdev([e["error_pct"] for e in errors]) if len(errors) > 1 else 0
                confidence = min(95, 60 + (len(errors) * 5) - (std_dev * 2))
                
                pattern = Pattern(
                    category="consumption",
                    item=item,
                    occurrence_count=len(errors),
                    avg_error=avg_error,
                    direction=direction,
                    suggested_adjustment=adjustment,
                    confidence=max(0, confidence)
                )
                patterns.append(pattern)
        
        # Analisar padrões financeiros
        financial_errors = []
        for event in self.events_realized:
            fin_error = self.calculate_financial_error(event.get("contract_id"))
            if fin_error.get("available"):
                financial_errors.append(fin_error)
        
        if len(financial_errors) >= min_occurrences:
            avg_margin_error = statistics.mean(e["error_margin"] for e in financial_errors)
            
            if abs(avg_margin_error) > 0.05:  # Mais de 5% de erro
                pattern = Pattern(
                    category="financial",
                    item="margin_forecast",
                    occurrence_count=len(financial_errors),
                    avg_error=avg_margin_error * 100,
                    direction="shortage" if avg_margin_error < 0 else "excess",
                    suggested_adjustment=avg_margin_error * 0.8,
                    confidence=min(90, 50 + len(financial_errors) * 3)
                )
                patterns.append(pattern)
        
        print(f"   ✅ {len(patterns)} padrões detectados")
        return patterns
    
    def generate_rules(self, patterns: List[Pattern]) -> List[Rule]:
        """
        Gera regras automáticas baseadas nos padrões.
        """
        print("\n⚙️  Gerando regras...")
        
        rules = []
        
        for p in patterns:
            if p.confidence < 50:
                continue
            
            # Criar ID único
            rule_id = f"RULE_{p.category.upper()}_{p.item.upper()}_{int(datetime.now().timestamp())}"
            
            # Condição
            if p.category == "consumption":
                condition = f"Consumo de {p.item} tem {p.direction} em {abs(p.avg_error):.1f}% da média"
                
                if p.item == "cerveja":
                    if p.direction == "excess":
                        action = f"Reduzir previsão cerveja em {abs(p.suggested_adjustment):.1f}% (evita sobra)"
                    else:
                        action = f"Aumentar previsão cerveja em {abs(p.suggested_adjustment):.1f}% (evita falta)"
                
                elif p.item == "agua":
                    if p.direction == "excess":
                        action = f"Reduzir previsão água em {abs(p.suggested_adjustment):.1f}% (otimizar estoque)"
                    else:
                        action = f"Aumentar previsão água em {abs(p.suggested_adjustment):.1f}% (evita ruptura)"
                
                elif p.item == "gelo":
                    action = f"Ajustar previsão gelo conforme evento (variável por temperatura)"
                
                else:
                    action = f"Ajustar previsão {p.item} em {abs(p.suggested_adjustment):.1f}%"
                
                impact = abs(p.avg_error) * 0.15  # Economia estimada
            
            elif p.category == "financial":
                condition = f"Margem real abaixo do previsto em {abs(p.avg_error):.1f}%"
                
                if p.item == "margin_forecast":
                    action = "Aumentar markup de custo em 5-10% nos orçamentos"
                    impact = 8.0  # % de melhoria estimada
                else:
                    action = "Revisar estrutura de custos antes de firmar contrato"
                    impact = 5.0
            
            else:
                continue
            
            rule = Rule(
                id=rule_id,
                condition=condition,
                action=action,
                impact_expected=impact,
                confidence=p.confidence,
                created_at=datetime.now().isoformat()
            )
            rules.append(rule)
        
        print(f"   ✅ {len(rules)} regras geradas")
        return rules
    
    def update_metrics(self, patterns: List[Pattern]):
        """
        Atualiza métricas baseado no aprendizado.
        """
        print("\n📊 Atualizando métricas...")
        
        adjustments = []
        
        for p in patterns:
            if p.category == "consumption" and p.item in self.metrics["beverage"]:
                # Calcular novo valor
                current = self.metrics["beverage"][p.item]
                adjustment = p.suggested_adjustment / 100
                new_value = current * (1 + adjustment)
                
                # Limitar mudança (regra mestre: nunca alterar drasticamente)
                max_change = 0.20  # Máximo 20%
                if abs(adjustment) > max_change:
                    adjustment = max_change if adjustment > 0 else -max_change
                    new_value = current * (1 + adjustment)
                
                self.metrics["beverage"][p.item] = new_value
                
                adjustments.append({
                    "item": p.item,
                    "old_value": current,
                    "new_value": round(new_value, 2),
                    "change_pct": round(adjustment * 100, 1)
                })
        
        if adjustments:
            print(f"   ⚙️  {len(adjustments)} métricas ajustadas:")
            for adj in adjustments:
                print(f"      {adj['item']}: {adj['old_value']} → {adj['new_value']} ({adj['change_pct']:+}%)")
        else:
            print("   ✅ Nenhuma alteração necessária")
        
        return adjustments
    
    def generate_insights(self, patterns: List[Pattern], rules: List[Rule], adjustments: List[Dict]) -> Dict:
        """
        Gera insights completos.
        """
        insights = {
            "learning_date": datetime.now().isoformat(),
            "source_data": {
                "events_analyzed": len(self.events_realized),
                "transactions_analyzed": len(self.financial_actual),
                "consumption_records": len(self.consumption_real)
            },
            "patterns_found": [
                {
                    "category": p.category,
                    "item": p.item,
                    "occurrences": p.occurrence_count,
                    "avg_error": round(p.avg_error, 2),
                    "direction": p.direction,
                    "confidence": round(p.confidence, 1)
                }
                for p in patterns
            ],
            "rules_created": [
                {
                    "id": r.id,
                    "condition": r.condition,
                    "action": r.action,
                    "impact_expected": r.impact_expected,
                    "confidence": round(r.confidence, 1)
                }
                for r in rules
            ],
            "automatic_adjustments": adjustments,
            "updated_metrics": {
                "beverage": self.metrics["beverage"],
                "food_cost_pct": self.metrics["food_cost_pct"],
                "margin_target": self.metrics["margin_target"]
            },
            "recommendations": self._generate_recommendations(patterns, rules)
        }
        
        return insights
    
    def _generate_recommendations(self, patterns: List[Pattern], rules: List[Rule]) -> List[str]:
        """Gera recomendações baseadas nos padrões."""
        recs = []
        
        # Cerveja
        cerveja = next((p for p in patterns if p.item == "cerveja"), None)
        if cerveja:
            if cerveja.direction == "excess":
                recs.append(f"🍺 Cerveja sempre sobrando: ajustar em {abs(cerveja.suggested_adjustment):.1f}% menor")
            else:
                recs.append(f"🍺 Cerveja sempre faltando: aumentar previsão em {abs(cerveja.suggested_adjustment):.1f}%")
        
        # Água
        agua = next((p for p in patterns if p.item == "agua"), None)
        if agua:
            if agua.direction == "shortage":
                recs.append(f"💧 Água sempre em falta: aumentar previsão em {abs(agua.suggested_adjustment):.1f}%")
        
        # Staff
        staff_patterns = [p for p in patterns if "staff" in p.item.lower()]
        if staff_patterns:
            recs.append(f"👥 Margem impactada por custo de staff: considerar redução de escala")
        
        # Geral
        if len(patterns) >= 5:
            recs.append(f"📊 {len(patterns)} padrões consistentes detectados - sistema está aprendendo bem")
        
        if len(rules) == 0:
            recs.append("✅ Operação previsível - nenhuma regra nova necessária")
        
        return recs
    
    def print_report(self, insights: Dict):
        """Imprime relatório de aprendizado."""
        print("\n" + "=" * 70)
        print("🧠 ORKESTRA LEARNING ENGINE V2 - ADAPTIVE INTELLIGENCE")
        print("=" * 70)
        
        print(f"\n📊 FONTE DE DADOS")
        print("-" * 70)
        src = insights["source_data"]
        print(f"   Eventos analisados: {src['events_analyzed']}")
        print(f"   Transações: {src['transactions_analyzed']}")
        print(f"   Registros de consumo: {src['consumption_records']}")
        
        print(f"\n🔍 PADRÕES ENCONTRADOS")
        print("-" * 70)
        for p in insights["patterns_found"]:
            icon = "📈" if p["direction"] == "excess" else "📉" if p["direction"] == "shortage" else "➡️"
            print(f"   {icon} {p['item'].upper()}: {p['occurrences']}x com {p['direction']}")
            print(f"      Erro médio: {p['avg_error']:.1f}% | Confiança: {p['confidence']:.0f}%")
        
        print(f"\n⚙️  REGRAS NOVAS")
        print("-" * 70)
        for r in insights["rules_created"]:
            conf_icon = "🟢" if r["confidence"] > 70 else "🟡"
            print(f"   {conf_icon} [{r['confidence']:.0f}%] {r['id'][:40]}")
            print(f"      Condição: {r['condition'][:50]}...")
            print(f"      AÇÃO: {r['action']}")
            print(f"      Impacto esperado: {r['impact_expected']:.1f}%")
        
        print(f"\n📊 AJUSTES AUTOMÁTICOS")
        print("-" * 70)
        adj = insights["automatic_adjustments"]
        if adj:
            for a in adj:
                direction = "↑" if a["change_pct"] > 0 else "↓"
                print(f"   {direction} {a['item']}: {a['old_value']} → {a['new_value']} ({a['change_pct']:+.1f}%)")
        else:
            print("   ✅ Nenhuma alteração necessária")
        
        print(f"\n💡 RECOMENDAÇÕES")
        print("-" * 70)
        for rec in insights["recommendations"]:
            print(f"   {rec}")
        
        print("\n" + "=" * 70)
    
    def save_results(self, insights: Dict):
        """Salva resultados do aprendizado."""
        output_path = Path("orkestra/memory/learning_v2_report.json")
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(insights, f, indent=2, ensure_ascii=False)
        
        # Também salvar métricas atualizadas
        metrics_path = Path("orkestra/memory/adaptive_metrics.json")
        with open(metrics_path, "w") as f:
            json.dump(insights["updated_metrics"], f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Relatório salvo: {output_path}")
        print(f"💾 Métricas adaptativas: {metrics_path}")
        
        return output_path


def run_learning_v2():
    """
    Executa Learning Engine V2 completo.
    """
    print("\n" + "=" * 70)
    print("🧠 ORKESTRA LEARNING ENGINE V2")
    print("   Inteligência Adaptativa Baseada em Dados")
    print("=" * 70)
    
    engine = LearningEngineV2()
    
    # Carregar dados
    engine.load_historical_data()
    
    if engine.events_realized:
        # Analisar padrões
        patterns = engine.analyze_patterns(min_occurrences=3)
        
        # Gerar regras
        rules = engine.generate_rules(patterns)
        
        # Atualizar métricas
        adjustments = engine.update_metrics(patterns)
        
        # Gerar insights
        insights = engine.generate_insights(patterns, rules, adjustments)
        
        # Imprimir relatório
        engine.print_report(insights)
        
        # Salvar
        engine.save_results(insights)
        
    else:
        print("\n⚠️  Dados históricos insuficientes para aprendizado.")
        print("   Necessário: pelo menos 3 eventos realizados")
    
    print("\n" + "=" * 70)
    print("✅ LEARNING ENGINE V2 COMPLETO")
    print("=" * 70)
    
    return engine


if __name__ == "__main__":
    run_learning_v2()
