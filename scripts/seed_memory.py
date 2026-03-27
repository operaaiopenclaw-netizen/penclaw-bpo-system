# seed_memory.py - Popula memory com dados históricos de exemplo
# Para demonstrar capacidade do Self Improvement Agent

import json
from datetime import datetime, timedelta
from pathlib import Path


def seed_decisions():
    """Popula decisions.json com cenários reais de eventos."""
    
    decisions = [
        # Evento 1: Casamento - Problema com bebidas
        {
            "id": "DEC_20260115_143000",
            "timestamp": "2026-01-15T14:30:00",
            "event": "casamento_silva_marques",
            "margin": 0.18,
            "margin_before": 0.28,
            "issue": "low_margin",
            "cause": "high_beverage_cost",
            "action": "change_supplier",
            "result": "margin_improved",
            "notes": "Troca fornecedor bebidas economia 18%"
        },
        # Evento 2: Formatura - Problema com proteína
        {
            "id": "DEC_20260203_100000",
            "timestamp": "2026-02-03T10:00:00",
            "event": "formatura_medicina_unesp",
            "margin": 0.22,
            "margin_before": 0.22,
            "issue": "low_margin",
            "cause": "high_protein_cost",
            "action": "reduce_portion_size",
            "result": "margin_improved",
            "notes": "Redução de 50g por pessoa economia 12%"
        },
        # Evento 3: Corporativo - Staff caro
        {
            "id": "DEC_20260220_090000",
            "timestamp": "2026-02-20T09:00:00",
            "event": "confraternizacao_techcorp",
            "margin": 0.15,
            "margin_before": 0.15,
            "issue": "low_margin",
            "cause": "high_staff_cost",
            "action": "optimize_team_size",
            "result": "margin_improved",
            "notes": "Redução 2 garçons mantido serviço"
        },
        # Evento 4: Aniversário - Ambientação excessiva
        {
            "id": "DEC_20260305_110000",
            "timestamp": "2026-03-05T11:00:00",
            "event": "aniversario_50anos_roberto",
            "margin": 0.20,
            "margin_before": 0.20,
            "issue": "low_margin",
            "cause": "high_ambiance_cost",
            "action": "simplify_decor",
            "result": "margin_improved",
            "notes": "Arranjos menores mesma percepção"
        },
        # Evento 5: Formatura - Bebidas de novo
        {
            "id": "DEC_20260315_160000",
            "timestamp": "2026-03-15T16:00:00",
            "event": "formatura_direito_puc",
            "margin": 0.19,
            "margin_before": 0.25,
            "issue": "low_margin",
            "cause": "high_beverage_cost",
            "action": "change_supplier",
            "result": "margin_improved",
            "notes": "Mesmo fornecedor troca - economia 15%"
        },
        # Evento 6: Casamento Bem-sucedido
        {
            "id": "DEC_20260320_090000",
            "timestamp": "2026-03-20T09:00:00",
            "event": "casamento_fernanda_pedro",
            "margin": 0.35,
            "margin_before": 0.35,
            "issue": "none",
            "cause": "none",
            "action": "maintain_standards",
            "result": "success",
            "notes": "Margem saudável padrão mantido"
        },
        # Evento 7: Evento com prejuízo
        {
            "id": "DEC_20260322_140000",
            "timestamp": "2026-03-22T14:00:00",
            "event": "festa_fim_ano_startup",
            "margin": -0.05,
            "margin_before": -0.05,
            "issue": "negative_margin",
            "cause": "underestimated_costs",
            "action": "repricing_required",
            "result": "loss_recorded",
            "notes": "Custo infraestrutura subestimado 30%"
        },
        # Evento 8: Evento médio - staff problema
        {
            "id": "DEC_20260318_100000",
            "timestamp": "2026-03-18T10:00:00",
            "event": "congresso_medicina",
            "margin": 0.16,
            "margin_before": 0.16,
            "issue": "low_margin",
            "cause": "high_staff_cost",
            "action": "optimize_team_size",
            "result": "margin_improved",
            "notes": "Mesmo ação staff funciona"
        }
    ]
    
    data = {
        "decisions": decisions,
        "metadata": {
            "version": "1.0",
            "last_update": datetime.now().isoformat(),
            "count": len(decisions)
        }
    }
    
    Path("memory/decisions.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"✅ {len(decisions)} decisões seedadas")


def seed_errors():
    """Popula errors.json com erros operacionais."""
    
    errors = [
        {
            "id": "ERR_20260210_083000",
            "timestamp": "2026-02-10T08:30:00",
            "event": "formatura_engenharia",
            "error_type": "stockout",
            "severity": "high",
            "description": "Falta de refrigerante durante evento",
            "impact": "Cliente insatisfeito, pedido emergencial custo 40% maior",
            "resolution": "Compra emergência fornecedor local",
            "prevention": "Aumentar margem segurança estoque para 25%"
        },
        {
            "id": "ERR_20260225_190000",
            "timestamp": "2026-02-25T19:00:00",
            "event": "casamento_fernanda",
            "error_type": "portion_calculation",
            "severity": "medium",
            "description": "Cálculo errado de carne, sobra 15kg",
            "impact": "Desperdício R$ 450,00",
            "resolution": "Doado para instituição caritativa",
            "prevention": "Validar calculadora de porções antes evento"
        },
        {
            "id": "ERR_20260310_120000",
            "timestamp": "2026-03-10T12:00:00",
            "event": "confraternizacao_empresa_x",
            "error_type": "staff_no_show",
            "severity": "high",
            "description": "2 garçons não compareceram",
            "impact": "Restante equipe sobrecarregado, serviço lento",
            "resolution": "Staff interno cobriu com hora extra",
            "prevention": "Contratar +20% staff com cláusula penal"
        },
        {
            "id": "ERR_20260318_210000",
            "timestamp": "2026-03-18T21:00:00",
            "event": "festa_debutante",
            "error_type": "stockout",
            "severity": "critical",
            "description": "Falta copos descartáveis meio evento",
            "impact": "Uso copos improvisados, imagem prejudicada",
            "resolution": "Compra urgente distribuidor 24h",
            "prevention": "Checklist estoque obrigatório 48h antes"
        }
    ]
    
    data = {
        "errors": errors,
        "metadata": {
            "version": "1.0",
            "last_update": datetime.now().isoformat(),
            "count": len(errors)
        }
    }
    
    Path("memory/errors.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"✅ {len(errors)} erros seedados")


def seed_performance():
    """Popula performance.json com métricas."""
    
    records = [
        {
            "id": "PERF_20260115_000000",
            "timestamp": "2026-01-15T00:00:00",
            "event": "casamento_silva_marques",
            "period": "event",
            "revenue": 25000,
            "costs": 20500,
            "margin_pct": 0.18,
            "targets_met": ["delivery_on_time"],
            "targets_missed": ["margin_above_30"],
            "kpis": {
                "protein_cost_pct": 28,
                "beverages_cost_pct": 32,
                "staff_cost_pct": 22,
                "ambiance_cost_pct": 18
            }
        },
        {
            "id": "PERF_20260203_000000",
            "timestamp": "2026-02-03T00:00:00",
            "event": "formatura_medicina_unesp",
            "period": "event",
            "revenue": 45000,
            "costs": 35100,
            "margin_pct": 0.22,
            "targets_met": ["food_quality", "service_rating"],
            "targets_missed": ["margin_above_30", "zero_waste"],
            "kpis": {
                "protein_cost_pct": 42,
                "beverages_cost_pct": 25,
                "staff_cost_pct": 18,
                "ambiance_cost_pct": 15
            }
        },
        {
            "id": "PERF_20260220_000000",
            "timestamp": "2026-02-20T00:00:00",
            "event": "confraternizacao_techcorp",
            "period": "event",
            "revenue": 30000,
            "costs": 25500,
            "margin_pct": 0.15,
            "targets_met": ["client_satisfaction"],
            "targets_missed": ["margin_above_30", "cost_within_budget"],
            "kpis": {
                "protein_cost_pct": 24,
                "beverages_cost_pct": 28,
                "staff_cost_pct": 35,
                "ambiance_cost_pct": 13
            }
        },
        {
            "id": "PERF_20260305_000000",
            "timestamp": "2026-03-05T00:00:00",
            "event": "aniversario_50anos_roberto",
            "period": "event",
            "revenue": 18000,
            "costs": 14400,
            "margin_pct": 0.20,
            "targets_met": ["decor_quality"],
            "targets_missed": ["margin_above_30"],
            "kpis": {
                "protein_cost_pct": 25,
                "beverages_cost_pct": 22,
                "staff_cost_pct": 20,
                "ambiance_cost_pct": 33
            }
        },
        {
            "id": "PERF_20260315_000000",
            "timestamp": "2026-03-15T00:00:00",
            "event": "formatura_direito_puc",
            "period": "event",
            "revenue": 40000,
            "costs": 32400,
            "margin_pct": 0.19,
            "targets_met": ["attendance"],
            "targets_missed": ["margin_above_30"],
            "kpis": {
                "protein_cost_pct": 30,
                "beverages_cost_pct": 38,
                "staff_cost_pct": 17,
                "ambiance_cost_pct": 15
            }
        },
        {
            "id": "PERF_20260320_000000",
            "timestamp": "2026-03-20T00:00:00",
            "event": "casamento_fernanda_pedro",
            "period": "event",
            "revenue": 50000,
            "costs": 32500,
            "margin_pct": 0.35,
            "targets_met": ["margin_above_30", "client_satisfaction", "on_time"],
            "targets_missed": [],
            "kpis": {
                "protein_cost_pct": 26,
                "beverages_cost_pct": 24,
                "staff_cost_pct": 20,
                "ambiance_cost_pct": 15
            }
        },
        {
            "id": "PERF_20260322_000000",
            "timestamp": "2026-03-22T00:00:00",
            "event": "festa_fim_ano_startup",
            "period": "event",
            "revenue": 20000,
            "costs": 21000,
            "margin_pct": -0.05,
            "targets_met": [],
            "targets_missed": ["margin_positive", "cost_within_budget", "profit_target"],
            "kpis": {
                "protein_cost_pct": 22,
                "beverages_cost_pct": 27,
                "staff_cost_pct": 25,
                "ambiance_cost_pct": 26
            }
        }
    ]
    
    data = {
        "records": records,
        "metadata": {
            "version": "1.0",
            "last_update": datetime.now().isoformat(),
            "count": len(records)
        }
    }
    
    Path("memory/performance.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"✅ {len(records)} registros de performance seedados")


if __name__ == "__main__":
    print("=" * 60)
    print("🌱 ORKESTRA MEMORY SEED")
    print("=" * 60)
    print()
    
    seed_decisions()
    seed_errors()
    seed_performance()
    
    print()
    print("=" * 60)
    print("✅ Dados históricos carregados com sucesso!")
    print("=" * 60)
    print("\nPróximo passo: rodar self_improvement_agent.py para análise")
