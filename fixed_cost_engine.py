#!/usr/bin/env python3
"""
FIXED COST ALLOCATION ENGINE
Distribuição mensal de custos fixos por evento
Rateio proporcional à receita, separado por empresa

REGRAS:
- Nunca alocar custo fixo sem evento
- Separar Opera e La Orana
- Manter rastreabilidade por empresa
- Registrar erros em errors.json
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

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


def save_csv(filename: str, data: List[Dict], headers: List[str]):
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)


def log_error(error_type: str, severity: str, event_id: Optional[str], 
              description: str, source: str = "fixed_cost_engine"):
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
    
    emoji = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}
    print(f"{emoji.get(severity, '⚠️')} [{severity.upper()}] {error_type}: {description}")


def parse_month(date_str: str) -> Optional[str]:
    """Extrai ano-mês de uma data (YYYY-MM-DD -> YYYY-MM)"""
    if not date_str:
        return None
    try:
        parts = date_str.split("-")
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
    except:
        pass
    return None


def load_fixed_costs_by_month() -> Dict[str, Dict[str, float]]:
    """
    Carrega custos fixos agrupados por mês e empresa
    
    Retorno: { "YYYY-MM": { "opera": 10000.0, "la_orana": 7500.0 } }
    """
    fixed = load_csv("fixed_costs.csv")
    
    if not fixed:
        log_error(
            "fixed_costs_missing",
            "high",
            None,
            "Arquivo fixed_costs.csv não encontrado ou vazio",
            "load_fixed_costs_by_month"
        )
        return {}
    
    # Estrutura: {mes: {empresa: total}}
    by_month = defaultdict(lambda: defaultdict(float))
    
    for row in fixed:
        mes = row.get("mes", "")
        empresa = row.get("empresa", "").lower().strip()
        categoria = row.get("categoria", "")
        
        # Validar empresa
        if empresa not in ["opera", "la_orana"]:
            log_error(
                "invalid_company",
                "medium",
                None,
                f"Empresa deve ser 'opera' ou 'la_orana': {empresa}",
                "load_fixed_costs_by_month"
            )
            continue
        
        # Parse valor
        try:
            valor = float(row.get("valor", 0)) if row.get("valor") else 0
        except ValueError:
            log_error(
                "invalid_fixed_cost_value",
                "medium",
                None,
                f"Valor inválido: {row.get('valor')}",
                "load_fixed_costs_by_month"
            )
            continue
        
        by_month[mes][empresa] += valor
    
    return dict(by_month)


def load_events_by_month() -> Dict[str, Dict[str, List[Dict]]]:
    """
    Carrega eventos agrupados por mês e empresa
    
    Retorno: { "YYYY-MM": { "opera": [eventos], "la_orana": [eventos] } }
    """
    events = load_csv("events_consolidated.csv")
    
    if not events:
        log_error(
            "events_missing",
            "high",
            None,
            "Arquivo events_consolidated.csv não encontrado ou vazio",
            "load_events_by_month"
        )
        return {}
    
    # Estrutura: {mes: {empresa: [eventos]}}
    by_month = defaultdict(lambda: defaultdict(list))
    
    for row in events:
        event_id = row.get("event_id", "")
        date_event = row.get("date_event", "")
        empresa = row.get("company", "").lower().strip()
        
        mes = parse_month(date_event)
        if not mes:
            log_error(
                "invalid_event_date",
                "medium",
                event_id,
                f"Data inválida: {date_event}",
                "load_events_by_month"
            )
            continue
        
        # Validar empresa
        if empresa not in ["opera", "la_orana"]:
            log_error(
                "invalid_event_company",
                "high",
                event_id,
                f"Empresa inválida: {empresa}",
                "load_events_by_month"
            )
            continue
        
        # Parse receita
        try:
            revenue = float(row.get("revenue_total", 0)) if row.get("revenue_total") else 0
        except ValueError:
            log_error(
                "invalid_revenue",
                "high",
                event_id,
                f"Receita inválida: {row.get('revenue_total')}",
                "load_events_by_month"
            )
            revenue = 0
        
        event_data = {
            **row,
            "_parsed_revenue": revenue,
            "_parsed_company": empresa,
            "_parsed_month": mes
        }
        
        by_month[mes][empresa].append(event_data)
    
    return {m: dict(e) for m, e in by_month.items()}


def calculate_fixed_allocation(
    fixed_costs: Dict[str, Dict[str, float]],
    events: Dict[str, Dict[str, List[Dict]]]
) -> Dict[str, Dict[str, Any]]:
    """
    Calcula alocação de custos fixos para cada evento
    
    Fórmula:
    fixed_allocated = (event_revenue / total_revenue_empresa_mes) * total_fixed_empresa_mes
    
    Retorno:
    {
        "mes-empresa-event_id": {
            "event_id": "...",
            "empresa": "...",
            "mes": "...",
            "revenue": 10000,
            "total_fixed_month": 10000,
            "total_revenue_month": 50000,
            "fixed_allocated": 2000,
            "allocation_rate": 0.20
        }
    }
    """
    allocations = {}
    summary = {
        "total_allocated": 0,
        "by_month": {}
    }
    
    print("\n📊 Calculando alocações...")
    print("-" * 70)
    
    for mes, companies in events.items():
        summary["by_month"][mes] = {}
        
        for empresa, event_list in companies.items():
            # Obter custo fixo do mês/empresa
            fixed_for_month = fixed_costs.get(mes, {}).get(empresa, 0)
            
            if fixed_for_month == 0:
                log_error(
                    "no_fixed_costs",
                    "medium",
                    None,
                    f"{mes}/{empresa}: nenhum custo fixo registrado",
                    "calculate_fixed_allocation"
                )
                continue
            
            # Calcular receita total do mês/empresa
            total_revenue = sum(e.get("_parsed_revenue", 0) for e in event_list)
            
            if total_revenue == 0:
                log_error(
                    "zero_revenue_month",
                    "high",
                    None,
                    f"{mes}/{empresa}: receita total zero - não é possível ratear {fixed_for_month:,.2f}",
                    "calculate_fixed_allocation"
                )
                # Não alocar nada - perdemos o custo fixo do mês
                continue
            
            print(f"\n   📅 {mes} | 🏢 {empresa.upper()}")
            print(f"      Custo fixo: R$ {fixed_for_month:,.2f}")
            print(f"      Receita total: R$ {total_revenue:,.2f}")
            print(f"      Eventos: {len(event_list)}")
            
            # Alocar para cada evento
            for event in event_list:
                event_id = event.get("event_id", "")
                revenue = event.get("_parsed_revenue", 0)
                
                # Cálculo do rateio
                allocation_rate = revenue / total_revenue
                allocated = allocation_rate * fixed_for_month
                
                allocation = {
                    "event_id": event_id,
                    "empresa": empresa,
                    "mes": mes,
                    "revenue": round(revenue, 2),
                    "total_fixed_month": round(fixed_for_month, 2),
                    "total_revenue_month": round(total_revenue, 2),
                    "fixed_allocated": round(allocated, 2),
                    "allocation_rate": round(allocation_rate, 6),
                    "trace_mode": "direct",
                    "source": "fixed_cost_engine",
                    "timestamp": datetime.now().isoformat()
                }
                
                key = f"{mes}-{empresa}-{event_id}"
                allocations[key] = allocation
                
                summary["total_allocated"] += allocated
                
                print(f"         {event_id}: R$ {allocated:,.2f} ({allocation_rate*100:.2f}%)")
    
    return allocations, summary


def update_dre_with_fixed_allocations(allocations: Dict):
    """Atualiza DRE com as alocações calculadas"""
    
    # Carregar DRE existente
    dre_data = load_csv("dre_events_temp.csv")  # Será gerado pelo dre_engine
    
    # Se não existe, criar placeholder
    if not dre_data:
        log_error(
            "dre_not_found",
            "low",
            None,
            "DRE não encontrado - gerando apenas alocações fixas",
            "update_dre_with_fixed_allocations"
        )
    
    # Criar output de alocações
    output = []
    for key, alloc in allocations.items():
        output.append(alloc)
    
    # Ordenar por mês, empresa
    output.sort(key=lambda x: (x["mes"], x["empresa"], x["event_id"]))
    
    headers = [
        "event_id", "empresa", "mes", "revenue",
        "total_fixed_month", "total_revenue_month",
        "fixed_allocated", "allocation_rate",
        "trace_mode", "source", "timestamp"
    ]
    
    save_csv("fixed_allocations.csv", output, headers)
    print(f"\n✅ Alocações salvas em: output/fixed_allocations.csv")
    
    return output


def generate_fixed_cost_report(allocations: Dict, summary: Dict):
    """Gera relatório de alocação de custos fixos"""
    
    print("\n" + "="*80)
    print("📊 FIXED COST ALLOCATION REPORT")
    print("="*80)
    
    # Agrupar por mês/empresa
    by_month_emp = defaultdict(lambda: defaultdict(dict))
    
    for key, alloc in allocations.items():
        mes = alloc["mes"]
        empresa = alloc["empresa"]
        by_month_emp[mes][empresa][alloc["event_id"]] = alloc
    
    for mes in sorted(by_month_emp.keys()):
        print(f"\n{'─'*80}")
        print(f"📅 {mes}")
        print(f"{'─'*80}")
        
        for empresa in sorted(by_month_emp[mes].keys()):
            print(f"\n   🏢 {empresa.upper()}")
            print(f"   {'─'*60}")
            
            eventos = by_month_emp[mes][empresa]
            total_fixed = 0
            
            for event_id in sorted(eventos.keys()):
                a = eventos[event_id]
                print(f"      {event_id:>12} | R$ {a['revenue']:>12,.2f} | Rateio: {a['allocation_rate']*100:>6.2f}% | Alocado: R$ {a['fixed_allocated']:>10,.2f}")
                total_fixed = a["total_fixed_month"]  # Mesmo para todos do mês
            
            # Mostrar total
            total_allocated = sum(a["fixed_allocated"] for a in eventos.values())
            print(f"      {'─'*60}")
            print(f"      {'Total alocado:':>12} | {'':>14} | {'':>8} | R$ {total_allocated:>10,.2f}")
            print(f"      {'Custo fixo mês:':>12} | {'':>14} | {'':>8} | R$ {total_fixed:>10,.2f}")
            
            if abs(total_allocated - total_fixed) > 0.01:
                print(f"      ⚠️  DIFERENÇA: R$ {abs(total_allocated - total_fixed):,.2f}")
    
    print("\n" + "="*80)
    print(f"TOTAL GERAL ALOCADO: R$ {summary['total_allocated']:,.2f}")
    print("="*80)


def main():
    """Função principal"""
    
    print("🎛️ FIXED COST ALLOCATION ENGINE - Orkestra Finance Brain")
    print("="*80)
    
    # 1. Carregar dados
    print("\n📥 Carregando dados...")
    
    fixed_costs = load_fixed_costs_by_month()
    if not fixed_costs:
        print("❌ Nenhum custo fixo encontrado")
        return
    
    print(f"   ✓ {len(fixed_costs)} meses com custos fixos")
    
    events = load_events_by_month()
    if not events:
        print("❌ Nenhum evento encontrado")
        return
    
    print(f"   ✓ {len(events)} meses com eventos")
    
    # 2. Calcular alocações
    allocations, summary = calculate_fixed_allocation(fixed_costs, events)
    
    if not allocations:
        print("\n❌ Nenhuma alocação calculada")
        return
    
    # 3. Gerar saídas
    update_dre_with_fixed_allocations(allocations)
    generate_fixed_cost_report(allocations, summary)
    
    # 4. Salvar JSON detalhado
    save_json("fixed_allocations.json", {
        "_meta": {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "total_allocations": len(allocations),
            "total_value": round(summary["total_allocated"], 2)
        },
        "allocations": allocations,
        "summary": summary
    })
    
    print(f"\n✅ Fixed Cost Allocation Engine completado!")
    print(f"   Total alocado: R$ {summary['total_allocated']:,.2f}")
    print(f"   Arquivos: output/fixed_allocations.csv + kitchen_data/fixed_allocations.json")


if __name__ == "__main__":
    main()
