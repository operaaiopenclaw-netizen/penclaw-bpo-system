#!/usr/bin/env python3
"""
MARGIN VALIDATION ENGINE
Valida consistência financeira e qualidade da margem

REGRAS:
- CMV > receita → erro crítico (prejuízo total)
- Margem < 0 → prejuízo
- Margem < 10% → risco
- Evento com receita sem CMV → erro
- Registra tudo em errors.json + decisions.json
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class MarginStatus(Enum):
    APPROVE = "APPROVE"    # Margem >= 20%
    REVIEW = "REVIEW"      # 10% a 20%
    REJECT = "REJECT"      # < 10%
    CRITICAL = "CRITICAL"  # CMV > Receita (prejuízo)
    ERROR = "ERROR"        # Dados incompletos


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


def log_error(error_type: str, severity: str, event_id: Optional[str], 
              description: str, source: str = "margin_validation"):
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
        "source": source
    }
    
    errors["errors"].append(error_entry)
    errors["_meta"] = {
        "last_updated": datetime.now().isoformat(),
        "total_errors": len(errors["errors"])
    }
    
    save_json("errors.json", errors)
    
    emoji = {"CRITICAL": "🚨", "HIGH": "🚨", "MEDIUM": "⚠️", "LOW": "ℹ️"}
    sev = severity.upper() if severity else "MEDIUM"
    print(f"{emoji.get(sev, '⚠️')} [{sev}] {error_type}: {description}")


@dataclass
class MarginDecision:
    """Estrutura de decisão de margem"""
    event_id: str
    company: str
    date_event: str
    revenue: Optional[float]
    cmv: Optional[float]
    gross_profit: Optional[float]
    gross_margin: Optional[float]
    fixed_allocated: Optional[float]
    net_profit: Optional[float]
    net_margin: Optional[float]
    status: str
    issues: List[str]
    timestamp: str
    trace_mode: str = "direct"


def load_dre_data() -> List[Dict]:
    """Carrega DRE existente ou reconstrói dos fontes"""
    
    # Tentar carregar DRE gerado
    dre_csv = OUTPUT_DIR / "dre_events.csv"
    if dre_csv.exists():
        return load_csv("dre_events.csv")
    
    # Se não existe, construir do events + cmv + fixed
    print("   ⚠️ DRE não encontrado - construindo de fontes...")
    
    events = load_csv("events_consolidated.csv")
    if not events:
        return []
    
    # Carregar CMV
    cmv_data = load_json("cmv_log.json")
    fixed_allocs = load_json("fixed_allocations.json")
    
    dre_records = []
    
    for event in events:
        event_id = event.get("event_id")
        
        try:
            revenue = float(event.get("revenue_total", 0)) if event.get("revenue_total") else 0
        except:
            revenue = 0
        
        # Buscar CMV
        cmv = cmv_data.get("eventos", {}).get(event_id, {}).get("cmv_total")
        
        # Buscar fixed allocated
        fixed_key = None
        for key, alloc in fixed_allocs.get("allocations", {}).items():
            if alloc.get("event_id") == event_id:
                fixed_key = key
                break
        
        fixed = None
        if fixed_key:
            fixed = fixed_allocs["allocations"][fixed_key].get("fixed_allocated")
        
        # Calcular
        gross_profit = None
        gross_margin = None
        if cmv is not None:
            gross_profit = revenue - cmv
            if revenue > 0:
                gross_margin = (gross_profit / revenue) * 100
        
        net_profit = None
        net_margin = None
        if gross_profit is not None and fixed is not None:
            net_profit = gross_profit - fixed
            if revenue > 0:
                net_margin = (net_profit / revenue) * 100
        
        dre_records.append({
            "event_id": event_id,
            "company": event.get("company", ""),
            "date_event": event.get("date_event", ""),
            "revenue_total": revenue,
            "cmv_total": cmv if cmv else "",
            "gross_profit": gross_profit if gross_profit is not None else "",
            "gross_margin": gross_margin if gross_margin is not None else "",
            "fixed_allocated": fixed if fixed else "",
            "net_profit": net_profit if net_profit is not None else "",
            "net_margin": net_margin if net_margin is not None else ""
        })
    
    return dre_records


def classify_margin(margin_pct: float, cmv: float, revenue: float) -> Tuple[str, List[str]]:
    """
    Classifica margem e retorna status + issues
    
    - APPROVE: margem >= 20%
    - REVIEW: 10% a 20%
    - REJECT: < 10%
    - CRITICAL: CMV > receita (prejuízo)
    """
    issues = []
    
    # Erro crítico: CMV > Receita
    if cmv > revenue:
        issues.append(f"CMV ({cmv:,.2f}) maior que receita ({revenue:,.2f}) - PREJUÍZO TOTAL")
        return MarginStatus.CRITICAL.value, issues
    
    # Erro crítico: CMV = Receita (margem zero)
    if cmv == revenue:
        issues.append(f"CMV igual à receita - margem bruta zero")
        return MarginStatus.REJECT.value, issues
    
    # Classificação por margem
    if margin_pct < 0:
        issues.append(f"Margem negativa: {margin_pct:.2f}%")
        return MarginStatus.CRITICAL.value, issues
    
    if margin_pct < 10:
        issues.append(f"Margem muito baixa: {margin_pct:.2f}% (abaixo de 10%)")
        return MarginStatus.REJECT.value, issues
    
    if margin_pct < 20:
        issues.append(f"Margem em risco: {margin_pct:.2f}% (abaixo de 20%)")
        return MarginStatus.REVIEW.value, issues
    
    # Aprovado
    return MarginStatus.APPROVE.value, issues


def validate_margins() -> List[MarginDecision]:
    """Valida todas as margens e gera decisões"""
    
    print("\n🔍 Validando margens financeiras...")
    
    dre_data = load_dre_data()
    if not dre_data:
        log_error(
            "NO_DRE_DATA",
            "CRITICAL",
            None,
            "Nenhum dado financeiro disponível para validação",
            "validate_margins"
        )
        return []
    
    decisions = []
    
    for record in dre_data:
        event_id = record.get("event_id", "")
        company = record.get("company", "")
        date_event = record.get("date_event", "")
        
        # Parse valores
        try:
            revenue = float(record.get("revenue_total", 0)) if record.get("revenue_total") else 0
        except:
            revenue = 0
        
        cmv_str = record.get("cmv_total", "")
        try:
            cmv = float(cmv_str) if cmv_str else None
        except:
            cmv = None
        
        fixed_str = record.get("fixed_allocated", "")
        try:
            fixed = float(fixed_str) if fixed_str else None
        except:
            fixed = None
        
        gross_str = record.get("gross_margin", "")
        try:
            gross_margin = float(gross_str) if gross_str else None
        except:
            gross_margin = None
        
        net_str = record.get("net_margin", "")
        try:
            net_margin = float(net_str) if net_str else None
        except:
            net_margin = None
        
        issues = []
        
        # === DETECÇÃO 1: Evento com receita sem CMV ===
        if revenue > 0 and cmv is None:
            log_error(
                "REVENUE_WITHOUT_CMV",
                "CRITICAL",
                event_id,
                f"Evento com receita R$ {revenue:,.2f} mas sem CMV calculado",
                "validate_margins"
            )
            status = MarginStatus.ERROR.value
            issues.append("Receita registrada sem CMV - impossível calcular margem")
            
            decision = MarginDecision(
                event_id=event_id,
                company=company,
                date_event=date_event,
                revenue=revenue,
                cmv=None,
                gross_profit=None,
                gross_margin=None,
                fixed_allocated=None,
                net_profit=None,
                net_margin=None,
                status=status,
                issues=issues,
                timestamp=datetime.now().isoformat(),
                trace_mode="direct"
            )
            decisions.append(decision)
            continue
        
        # === DETECÇÃO 2: CMV > Receita (prejuízo total) ===
        if cmv and cmv > revenue:
            log_error(
                "CMV_EXCEEDS_REVENUE",
                "CRITICAL",
                event_id,
                f"CMV R$ {cmv:,.2f} excede receita R$ {revenue:,.2f} - PREJUÍZO",
                "validate_margins"
            )
            status = MarginStatus.CRITICAL.value
            issues.append(f"CMV maior que receita: CMV={cmv:,.2f}, Receita={revenue:,.2f}")
            
            decision = MarginDecision(
                event_id=event_id,
                company=company,
                date_event=date_event,
                revenue=revenue,
                cmv=cmv,
                gross_profit=revenue - cmv,
                gross_margin=gross_margin,
                fixed_allocated=fixed,
                net_profit=None,
                net_margin=None,
                status=status,
                issues=issues,
                timestamp=datetime.now().isoformat(),
                trace_mode="direct"
            )
            decisions.append(decision)
            continue
        
        # === DETECÇÃO 3: Margem negativa ===
        if gross_margin is not None and gross_margin < 0:
            log_error(
                "NEGATIVE_MARGIN",
                "CRITICAL",
                event_id,
                f"Margem bruta negativa: {gross_margin:.2f}%",
                "validate_margins"
            )
            status = MarginStatus.CRITICAL.value
            issues.append(f"Margem bruta negativa: {gross_margin:.2f}%")
            
            decision = MarginDecision(
                event_id=event_id,
                company=company,
                date_event=date_event,
                revenue=revenue,
                cmv=cmv,
                gross_profit=revenue - cmv if cmv else None,
                gross_margin=gross_margin,
                fixed_allocated=fixed,
                net_profit=net_margin,
                net_margin=net_margin,
                status=status,
                issues=issues,
                timestamp=datetime.now().isoformat(),
                trace_mode="direct"
            )
            decisions.append(decision)
            continue
        
        # === CLASSIFICAÇÃO POR MARGEM ===
        if gross_margin is not None:
            status, margin_issues = classify_margin(gross_margin, cmv or 0, revenue)
            issues.extend(margin_issues)
            
            # Log adicional para REJECT/REVIEW
            if status == MarginStatus.REJECT.value:
                log_error(
                    "LOW_MARGIN",
                    "HIGH",
                    event_id,
                    f"Margem bruta baixa: {gross_margin:.2f}% (abaixo de 10%)",
                    "validate_margins"
                )
            elif status == MarginStatus.REVIEW.value:
                log_error(
                    "MARGIN_REVIEW",
                    "MEDIUM",
                    event_id,
                    f"Margem em revisão: {gross_margin:.2f}% (10-20%)",
                    "validate_margins"
                )
        else:
            status = MarginStatus.ERROR.value
            issues.append("Margem não calculável")
        
        # Construir decisão
        decision = MarginDecision(
            event_id=event_id,
            company=company,
            date_event=date_event,
            revenue=revenue,
            cmv=cmv,
            gross_profit=revenue - cmv if cmv else None,
            gross_margin=gross_margin,
            fixed_allocated=fixed,
            net_profit=(revenue - cmv - fixed) if cmv and fixed else None,
            net_margin=net_margin,
            status=status,
            issues=issues,
            timestamp=datetime.now().isoformat(),
            trace_mode="direct"
        )
        decisions.append(decision)
    
    return decisions


def generate_decisions_json(decisions: List[MarginDecision]):
    """Gera decisions.json"""
    
    output = {
        "_meta": {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_decisions": len(decisions),
            "breakdown": {
                "APPROVE": sum(1 for d in decisions if d.status == "APPROVE"),
                "REVIEW": sum(1 for d in decisions if d.status == "REVIEW"),
                "REJECT": sum(1 for d in decisions if d.status == "REJECT"),
                "CRITICAL": sum(1 for d in decisions if d.status == "CRITICAL"),
                "ERROR": sum(1 for d in decisions if d.status == "ERROR")
            }
        },
        "decisions": [asdict(d) for d in decisions]
    }
    
    save_json("decisions.json", output)
    print(f"\n✅ Decisions salvo em: kitchen_data/decisions.json")
    
    return output


def print_margin_report(decisions: List[MarginDecision]):
    """Imprime relatório de margens"""
    
    emoji_status = {
        "APPROVE": "🟢",
        "REVIEW": "🟡",
        "REJECT": "🔴",
        "CRITICAL": "🚨",
        "ERROR": "❌"
    }
    
    print("\n" + "="*90)
    print("📊 MARGIN VALIDATION REPORT")
    print("="*90)
    
    print(f"\n{'EVENTO':<12} {'EMP':<8} {'RECEITA':>12} {'CMV':>12} {'L.BRUTO':>12} {'M.BRUTA':>10} {'NET':>12} {'STATUS':<10}")
    print("-"*90)
    
    for d in decisions:
        receita = f"R$ {d.revenue:>10,.2f}" if d.revenue else "N/A"
        cmv = f"R$ {d.cmv:>10,.2f}" if d.cmv else "N/A"
        gross = f"R$ {d.gross_profit:>10,.2f}" if d.gross_profit else "N/A"
        margin = f"{d.gross_margin:>7.1f}%" if d.gross_margin else "N/A"
        net = f"R$ {d.net_profit:>10,.2f}" if d.net_profit else "N/A"
        
        print(f"{d.event_id:<12} {d.company:<8} {receita:>12} {cmv:>12} {gross:>12} {margin:>10} {net:>12} {emoji_status.get(d.status, '❓')} {d.status}")
    
    print("-"*90)
    
    # Resumo
    counts = {
        "APPROVE": sum(1 for d in decisions if d.status == "APPROVE"),
        "REVIEW": sum(1 for d in decisions if d.status == "REVIEW"),
        "REJECT": sum(1 for d in decisions if d.status == "REJECT"),
        "CRITICAL": sum(1 for d in decisions if d.status == "CRITICAL"),
        "ERROR": sum(1 for d in decisions if d.status == "ERROR")
    }
    
    print(f"\n{'RESUMO':<20}")
    print(f"  🟢 APPROVE:  {counts['APPROVE']:>3} eventos")
    print(f"  🟡 REVIEW:   {counts['REVIEW']:>3} eventos")
    print(f"  🔴 REJECT:   {counts['REJECT']:>3} eventos")
    print(f"  🚨 CRITICAL: {counts['CRITICAL']:>3} eventos")
    print(f"  ❌ ERROR:    {counts['ERROR']:>3} eventos")
    
    total = len(decisions)
    approved_rate = (counts['APPROVE'] / total * 100) if total else 0
    
    print(f"\n  Taxa de aprovação: {approved_rate:.1f}%")
    print("="*90)


def generate_csv_summary(decisions: List[MarginDecision]):
    """Gera CSV de resumo"""
    
    headers = [
        "event_id", "company", "date_event", "revenue", "cmv",
        "gross_profit", "gross_margin", "net_profit", "net_margin",
        "status", "issues"
    ]
    
    data = []
    for d in decisions:
        row = {
            "event_id": d.event_id,
            "company": d.company,
            "date_event": d.date_event,
            "revenue": round(d.revenue, 2) if d.revenue else "",
            "cmv": round(d.cmv, 2) if d.cmv else "",
            "gross_profit": round(d.gross_profit, 2) if d.gross_profit else "",
            "gross_margin": round(d.gross_margin, 2) if d.gross_margin else "",
            "net_profit": round(d.net_profit, 2) if d.net_profit else "",
            "net_margin": round(d.net_margin, 2) if d.net_margin else "",
            "status": d.status,
            "issues": "; ".join(d.issues) if d.issues else ""
        }
        data.append(row)
    
    filepath = OUTPUT_DIR / "margin_validation.csv"
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ CSV salvo em: output/margin_validation.csv")


def main():
    """Função principal"""
    
    print("🎛️ MARGIN VALIDATION ENGINE - Orkestra Finance Brain")
    print("="*90)
    
    # Validar margens
    decisions = validate_margins()
    
    if not decisions:
        print("\n❌ Nenhum evento para validar")
        return
    
    # Gerar saídas
    generate_decisions_json(decisions)
    generate_csv_summary(decisions)
    print_margin_report(decisions)
    
    print("\n✅ Margin Validation Engine completado!")


if __name__ == "__main__":
    main()
