#!/usr/bin/env python3
"""
DRE ENGINE CORE
Demonstração de Resultado do Exercício por Evento

REGRAS:
- NUNCA assumir valores faltantes
- Se CMV ausente → erro crítico
- Se receita = 0 → ignorar margem
- Registrar inconsistências em errors.json
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_json(filename: str) -> Dict:
    filepath = DATA_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_json(filename: str, data: Dict):
    filepath = DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_csv(filename: str) -> List[Dict]:
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_csv(filename: str, data: List[Dict], headers: List[str] = None):
    filepath = OUTPUT_DIR / filename
    if not data:
        return
    
    if not headers:
        headers = list(data[0].keys())
    
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)


def log_error(error_type: str, severity: str, event_id: Optional[str], description: str):
    """Registra erro em errors.json"""
    errors = load_json("errors.json")
    
    if "errors" not in errors:
        errors["errors"] = []
    
    error_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": error_type,
        "severity": severity,
        "event_id": event_id,
        "description": description,
        "source": "dre_engine"
    }
    
    errors["errors"].append(error_entry)
    errors["_meta"] = {
        "last_updated": datetime.now().isoformat(),
        "total_errors": len(errors["errors"])
    }
    
    save_json("errors.json", errors)
    
    emoji = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}
    print(f"{emoji.get(severity, '⚠️')} [{severity.upper()}] {error_type}: {description}")


@dataclass
class DRE_Event:
    """Estrutura de DRE por evento"""
    event_id: str
    company: str
    date_event: str
    revenue_total: Optional[float] = None
    cmv_total: Optional[float] = None
    gross_profit: Optional[float] = None
    gross_margin: Optional[float] = None
    fixed_allocated: Optional[float] = None
    net_profit: Optional[float] = None
    net_margin: Optional[float] = None
    status: str = "ok"
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def validate_inputs() -> Tuple[bool, List[str]]:
    """Valida se todos os inputs obrigatórios existem"""
    errors = []
    
    # 1. Verificar events_consolidated.csv
    events = load_csv("events_consolidated.csv")
    if not events:
        errors.append("events_consolidated.csv não encontrado ou vazio - DRE não pode ser calculado")
    else:
        # Validar estrutura
        required_fields = ["event_id", "n_ctt", "revenue_total"]
        for field in required_fields:
            if field not in events[0]:
                errors.append(f"Campo obrigatório ausente em events_consolidated.csv: {field}")
    
    # 2. Verificar cmv_log.json
    cmv = load_json("cmv_log.json")
    if not cmv or not cmv.get("eventos"):
        errors.append("cmv_log.json vazio ou não encontrado - CMV será marcado como incompleto")
    
    # 3. Verificar fixed_costs.csv
    fixed = load_csv("fixed_costs.csv")
    if not fixed:
        errors.append("fixed_costs.csv não encontrado ou vazio - rateio de custos fixos será inválido")
    
    if errors:
        for e in errors:
            log_error("input_validation", "high", None, e)
    
    return len(errors) == 0, errors


def load_events_consolidated() -> Dict[str, Dict]:
    """Carrega e indexa eventos consolidados por event_id"""
    events = load_csv("events_consolidated.csv")
    indexed = {}
    
    for event in events:
        event_id = event.get("event_id")
        n_ctt = event.get("n_ctt")
        
        if not event_id or not n_ctt:
            log_error(
                "missing_event_id_or_ctt",
                "high",
                event_id or None,
                f"Evento sem event_id ou n_ctt: {event}"
            )
            continue
        
        # Validar campos numéricos
        try:
            revenue = float(event.get("revenue_total", 0)) if event.get("revenue_total") else None
        except ValueError:
            log_error(
                "invalid_revenue",
                "high",
                event_id,
                f"revenue_total inválido: {event.get('revenue_total')}"
            )
            revenue = None
        
        indexed[event_id] = {
            "event_id": event_id,
            "n_ctt": n_ctt,
            "company": event.get("company", ""),
            "date_event": event.get("date_event", ""),
            "revenue_total": revenue,
            "client_name": event.get("client_name", ""),
            "event_type": event.get("event_type", ""),
            "status": event.get("status", "")
        }
    
    return indexed


def load_cmv_events() -> Dict[str, float]:
    """Carrega CMV calculado por evento"""
    cmv_data = load_json("cmv_log.json")
    cmv_by_event = {}
    
    for event_id, data in cmv_data.get("eventos", {}).items():
        cmv_total = data.get("cmv_total")
        confidence = data.get("cost_confidence_score", 0)
        
        if cmv_total is not None and confidence >= 0.4:  # Mínimo de confiança
            cmv_by_event[event_id] = float(cmv_total)
        elif cmv_total is not None and confidence < 0.4:
            log_error(
                "low_cmv_confidence",
                "medium",
                event_id,
                f"CMV com confiança baixa ({confidence}) - usando mesmo assim"
            )
            cmv_by_event[event_id] = float(cmv_total)
        else:
            log_error(
                "cmv_missing",
                "high",
                event_id,
                "CMV não calculado para evento"
            )
    
    return cmv_by_event


def load_fixed_costs() -> Tuple[Optional[float], List[str]]:
    """Carrega e soma custos fixos"""
    fixed = load_csv("fixed_costs.csv")
    
    if not fixed:
        log_error(
            "fixed_costs_missing",
            "high",
            None,
            "Arquivo fixed_costs.csv não encontrado ou vazio"
        )
        return None, []
    
    total_fixed = 0.0
    details = []
    
    for item in fixed:
        try:
            # Support both "amount" (canonical) and "valor" (legacy CSV field name)
            raw = item.get("amount") or item.get("valor")
            amount = float(raw) if raw else 0.0
            total_fixed += amount
            details.append({
                "cost_type": item.get("cost_type", ""),
                "description": item.get("description", ""),
                "amount": amount,
                "period": item.get("period", "")
            })
        except ValueError:
            log_error(
                "invalid_fixed_cost",
                "medium",
                None,
                f"Valor inválido em custo fixo: {item}"
            )
    
    return total_fixed, details


def calculate_fixed_allocation(
    event_revenue: float,
    total_revenue_all_events: float,
    total_fixed_costs: float
) -> float:
    """
    Rateio proporcional de custos fixos
    
    Alocação = (Receita do Evento / Receita Total) × Custo Fixo Total
    """
    if total_revenue_all_events == 0:
        log_error(
            "zero_total_revenue",
            "high",
            None,
            "Receita total zero - não é possível ratear custos fixos"
        )
        return 0.0
    
    allocation = (event_revenue / total_revenue_all_events) * total_fixed_costs
    return round(allocation, 2)


def process_dre() -> List[DRE_Event]:
    """
    Processa DRE para todos os eventos
    """
    print("\n📊 DRE ENGINE CORE - Iniciando processamento")
    print("="*60)
    
    # Validar inputs
    valid, errors = validate_inputs()
    if not valid:
        print(f"❌ {len(errors)} erros de validação encontrados")
    
    # 1. Carregar dados
    print("\n📥 Carregando dados...")
    
    events = load_events_consolidated()
    print(f"   ✓ {len(events)} eventos carregados")
    
    cmv = load_cmv_events()
    print(f"   ✓ {len(cmv)} CMVs carregados")
    
    total_fixed, fixed_details = load_fixed_costs()
    print(f"   ✓ Custos fixos: R$ {total_fixed:,.2f}" if total_fixed else "   ⚠️ Custos fixos não disponíveis")
    
    # 2. Calcular receita total para rateio
    total_revenue = sum(
        e.get("revenue_total", 0) or 0 
        for e in events.values()
    )
    print(f"   ✓ Receita total: R$ {total_revenue:,.2f}")
    
    # 3. Processar cada evento
    print("\n📈 Calculando DRE...")
    dre_results = []
    
    for event_id, event_data in events.items():
        dre = DRE_Event(
            event_id=event_id,
            company=event_data.get("company", ""),
            date_event=event_data.get("date_event", "")
        )
        
        # Receita
        revenue = event_data.get("revenue_total")
        if revenue is None:
            log_error(
                "revenue_missing",
                "high",
                event_id,
                "Evento sem receita registrada - DRE não pode ser calculado"
            )
            dre.status = "error"
            dre.errors.append("revenue_total ausente")
            dre_results.append(dre)
            continue
        
        dre.revenue_total = revenue
        
        # CMV
        cmv_value = cmv.get(event_id)
        if cmv_value is None:
            log_error(
                "cmv_missing",
                "high",
                event_id,
                "CMV não encontrado para evento - gross_profit não calculado"
            )
            dre.status = "error"
            dre.errors.append("cmv_total ausente")
            dre_results.append(dre)
            continue
        
        dre.cmv_total = cmv_value
        
        # Cálculos principais
        # Gross Profit = Revenue - CMV
        dre.gross_profit = round(revenue - cmv_value, 2)
        
        # Gross Margin (se receita > 0)
        if revenue > 0:
            dre.gross_margin = round((dre.gross_profit / revenue) * 100, 2)
        else:
            dre.gross_margin = None  # Receita = 0, ignorar margem
            log_error(
                "zero_revenue",
                "medium",
                event_id,
                "Receita zero - margem não calculada"
            )
        
        # Alocação de custos fixos
        if total_fixed and total_revenue > 0:
            dre.fixed_allocated = calculate_fixed_allocation(
                revenue, total_revenue, total_fixed
            )
        
        # Net Profit = Gross Profit - Fixed Allocated
        if dre.fixed_allocated is not None:
            dre.net_profit = round(dre.gross_profit - dre.fixed_allocated, 2)
        else:
            dre.fixed_allocated = 0.0
            dre.net_profit = dre.gross_profit
        
        # Net Margin (se receita > 0)
        if revenue > 0:
            dre.net_margin = round((dre.net_profit / revenue) * 100, 2)
        else:
            dre.net_margin = None
        
        # Status
        if dre.gross_profit < 0:
            dre.status = "loss"
        elif dre.errors:
            dre.status = "warning"
        
        dre_results.append(dre)
        
        # Print resumo
        print(f"   {event_id}: Receita R$ {revenue:,.2f} | CMV R$ {cmv_value:,.2f} | Lucro R$ {dre.gross_profit:,.2f}")
    
    return dre_results


def generate_dre_csv(dre_events: List[DRE_Event]):
    """Gera arquivo CSV com DRE de todos os eventos"""
    
    # Converter para dicts
    data = []
    for dre in dre_events:
        row = {
            "event_id": dre.event_id,
            "company": dre.company,
            "date_event": dre.date_event,
            "revenue_total": dre.revenue_total if dre.revenue_total is not None else "",
            "cmv_total": dre.cmv_total if dre.cmv_total is not None else "",
            "gross_profit": dre.gross_profit if dre.gross_profit is not None else "",
            "gross_margin": f"{dre.gross_margin:.2f}" if dre.gross_margin is not None else "",
            "fixed_allocated": dre.fixed_allocated if dre.fixed_allocated is not None else "",
            "net_profit": dre.net_profit if dre.net_profit is not None else "",
            "net_margin": f"{dre.net_margin:.2f}" if dre.net_margin is not None else "",
            "status": dre.status,
            "errors": ";".join(dre.errors) if dre.errors else ""
        }
        data.append(row)
    
    # Ordenar por date_event
    data.sort(key=lambda x: x["date_event"])
    
    headers = [
        "event_id", "company", "date_event",
        "revenue_total", "cmv_total", "gross_profit", "gross_margin",
        "fixed_allocated", "net_profit", "net_margin",
        "status", "errors"
    ]
    
    save_csv("dre_events.csv", data, headers)
    print(f"\n✅ DRE salvo em: output/dre_events.csv")
    
    return data


def generate_dre_summary(dre_events: List[DRE_Event]) -> Dict:
    """Gera resumo analítico do DRE"""
    
    total_revenue = sum(d.revenue_total or 0 for d in dre_events)
    total_cmv = sum(d.cmv_total or 0 for d in dre_events)
    total_gross = sum(d.gross_profit or 0 for d in dre_events)
    total_fixed = sum(d.fixed_allocated or 0 for d in dre_events)
    total_net = sum(d.net_profit or 0 for d in dre_events)
    
    # Contadores
    count_ok = sum(1 for d in dre_events if d.status == "ok")
    count_loss = sum(1 for d in dre_events if d.status == "loss")
    count_error = sum(1 for d in dre_events if d.status == "error")
    count_warning = sum(1 for d in dre_events if d.status == "warning")
    
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_events": len(dre_events),
        "totals": {
            "revenue": round(total_revenue, 2),
            "cmv": round(total_cmv, 2),
            "gross_profit": round(total_gross, 2),
            "gross_margin": round((total_gross / total_revenue * 100), 2) if total_revenue else 0,
            "fixed_allocated": round(total_fixed, 2),
            "net_profit": round(total_net, 2),
            "net_margin": round((total_net / total_revenue * 100), 2) if total_revenue else 0
        },
        "breakdown": {
            "ok": count_ok,
            "loss": count_loss,
            "warning": count_warning,
            "error": count_error
        },
        "events_detail": [
            {
                "event_id": d.event_id,
                "revenue": d.revenue_total,
                "cmv": d.cmv_total,
                "gross_margin": d.gross_margin,
                "net_margin": d.net_margin,
                "status": d.status
            }
            for d in dre_events
        ]
    }
    
    save_json("dre_summary.json", summary)
    print(f"✅ Resumo salvo em: kitchen_data/dre_summary.json")
    
    return summary


def print_dre_report(dre_events: List[DRE_Event]):
    """Imprime relatório formatado"""
    
    print("\n" + "="*80)
    print("📊 RELATÓRIO DRE - DEMONSTRAÇÃO DE RESULTADO POR EVENTO")
    print("="*80)
    
    total_revenue = sum(d.revenue_total or 0 for d in dre_events)
    total_cmv = sum(d.cmv_total or 0 for d in dre_events)
    total_net = sum(d.net_profit or 0 for d in dre_events)
    
    print(f"\n{'EVENTO':<15} {'RECEITA':>12} {'CMV':>12} {'LUCRO BRUTO':>14} {'MARGEM BRUTA':>12} {'LUCRO LIQ':>12}")
    print("-"*80)
    
    for dre in dre_events:
        status_emoji = {
            "ok": "✅",
            "loss": "🔴",
            "warning": "⚠️",
            "error": "❌"
        }.get(dre.status, "❓")
        
        revenue = dre.revenue_total or 0
        cmv = dre.cmv_total or 0
        gross = dre.gross_profit or 0
        gross_margin = f"{dre.gross_margin:.1f}%" if dre.gross_margin is not None else "N/A"
        net = dre.net_profit or 0
        
        print(f"{status_emoji} {dre.event_id:<12} R$ {revenue:>10,.2f} R$ {cmv:>10,.2f} R$ {gross:>12,.2f} {gross_margin:>11} R$ {net:>10,.2f}")
    
    print("-"*80)
    print(f"{'TOTAL':<15} R$ {total_revenue:>10,.2f} R$ {total_cmv:>10,.2f} R$ {total_revenue - total_cmv:>12,.2f} {'':>11} R$ {total_net:>10,.2f}")
    
    print("\n" + "="*80)
    print("LEGENDA:")
    print("  ✅ OK        = Evento rentável")
    print("  🔴 LOSS      = Prejuízo (CMV > Receita)")
    print("  ⚠️ WARNING   = Evento com alerta")
    print("  ❌ ERROR     = Dados incompletos")
    print("="*80)


if __name__ == "__main__":
    print("🎛️ DRE ENGINE CORE - Orkestra Finance Brain")
    
    # Processar
    dre_events = process_dre()
    
    if not dre_events:
        print("\n❌ Nenhum evento processado - verifique os arquivos de entrada")
        exit(1)
    
    # Gerar saídas
    generate_dre_csv(dre_events)
    generate_dre_summary(dre_events)
    print_dre_report(dre_events)
    
    print("\n✅ DRE completado com sucesso!")
