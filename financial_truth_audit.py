#!/usr/bin/env python3
"""
FINANCIAL TRUTH AUDIT ENGINE
Valida consistência total entre receita, CMV, estoque e DRE

REGRAS CRÍTICAS:
- NUNCA ajustar dados
- APENAS identificar erros
- Divergência CMV > 5% = erro crítico
- Venda > Produção = erro grave
- Produção >> Venda = desperdício oculto
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Limiares de consistência
THRESHOLDS = {
    "cmv_vs_estoque": 0.05,      # 5%
    "producao_vs_consumo": 0.10,  # 10%
    "venda_vs_producao": 0.15,   # 15%
    "margem_critica": 0.0        # CMV > Receita
}


@dataclass
class FinancialAudit:
    event_id: str
    n_ctt: str
    company: str
    date_event: str
    status: str  # CONSISTENTE, ALERTA, INCONSISTENTE
    
    # Dados financeiros
    receita_total: Optional[float]
    cmv_total: Optional[float]
    margem_bruta_pct: Optional[float]
    
    # Dados operacionais
    estoque_saida_total: Optional[float]
    consumo_real: Optional[float]
    producao_total: Optional[float]
    venda_total: Optional[float]
    
    # Validações
    validacoes: Dict[str, Any]
    divergencias: List[Dict]
    issues: List[str]
    
    # Scores
    confidence_score: float
    risco_financeiro: str  # ALTO, MEDIO, BAIXO
    
    timestamp: str


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
        filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def log_audit_error(error_type: str, severity: str, event_id: Optional[str], 
                    description: str, divergence_pct: Optional[float] = None):
    """Registra erro de auditoria"""
    
    errors = load_json("errors.json")
    if "audit_errors" not in errors:
        errors["audit_errors"] = []
    
    error_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": error_type,
        "severity": severity,
        "event_id": event_id,
        "description": description,
        "divergence_pct": divergence_pct,
        "source": "financial_truth_audit"
    }
    
    errors["audit_errors"].append(error_entry)
    
    # Também salvar em audit_errors separado
    audit_errors = load_json("audit_errors.json")
    if "errors" not in audit_errors:
        audit_errors["errors"] = []
    audit_errors["errors"].append(error_entry)
    audit_errors["_meta"] = {
        "last_updated": datetime.now().isoformat(),
        "total_errors": len(audit_errors["errors"])
    }
    save_json("audit_errors.json", audit_errors)
    
    emoji = {"CRITICO": "🚨", "ALTO": "🚨", "MEDIO": "⚠️", "BAIXO": "ℹ️"}
    print(f"{emoji.get(severity, '⚠️')} [{severity}] {error_type}: {description}")


def load_events_data() -> List[Dict]:
    """Carrega eventos consolidados"""
    return load_csv("events_consolidated.csv")


def load_cmv_data() -> Dict[str, Dict]:
    """Carrega CMV por evento"""
    cmv = load_json("cmv_log.json")
    return cmv.get("eventos", {})


def load_estoque_saida() -> Dict[str, float]:
    """Carrega saídas de estoque por evento"""
    # Buscar em waste_log ou production_execution
    waste = load_json("waste_log.json")
    estoque_saida = {}
    
    for event_id, data in waste.get("registros", {}).items():
        consumos = data.get("consumo", [])
        total = 0
        for c in consumos:
            # Tentar obter valor do consumo
            qty = c.get("quantity_used", 0)
            # Precisamos do preço - buscar no inventory
            estoque_saida[event_id] = estoque_saida.get(event_id, 0) + qty
    
    return estoque_saida


def load_producao_e_venda() -> Dict[str, Dict]:
    """Carrega dados de produção e venda por evento"""
    execs = load_json("production_execution.json")
    producao_por_evento = {}
    
    for exec_id, exec_data in execs.get("execucoes", {}).items():
        event_id = exec_data.get("evento_id")
        if not event_id:
            continue
        
        # Somar todas as receitas
        total_produzido = 0
        total_vendido = 0
        
        for receita in exec_data.get("receitas_executadas", []):
            total_produzido += receita.get("porcoes_produzidas", 0)
            total_vendido += receita.get("porcoes_servidas", 0)
        
        if event_id not in producao_por_evento:
            producao_por_evento[event_id] = {"produzido": 0, "vendido": 0}
        
        producao_por_evento[event_id]["produzido"] += total_produzido
        producao_por_evento[event_id]["vendido"] += total_vendido
    
    return producao_por_evento


def load_item_performance() -> Dict[str, List[Dict]]:
    """Carrega performance agregada por evento"""
    data = load_json("item_performance.json")
    performances = data.get("performances", [])
    
    by_event = defaultdict(list)
    for p in performances:
        event_id = p.get("event_id")
        if event_id:
            by_event[event_id].append(p)
    
    return dict(by_event)


def calculate_consumo_real(event_id: str, item_perf: Dict) -> Tuple[Optional[float], Optional[float]]:
    """Calcula consumo real e vendas totais de um evento"""
    
    vendas = item_perf.get(event_id, [])
    
    if not vendas:
        return None, None
    
    total_consumo = 0
    total_venda = 0
    
    for item in vendas:
        # Consumo = CMV se tiver
        if item.get("cmv"):
            total_consumo += item.get("cmv", 0)
        
        # Venda = revenue se tiver
        if item.get("revenue"):
            total_venda += item.get("revenue", 0)
    
    return total_consumo, total_venda


def validate_cmv_vs_estoque(cmv: Optional[float], estoque_saida: Optional[float], 
                            event_id: str) -> Tuple[bool, Optional[float], str]:
    """
    A. CMV vs estoque
    CMV ≈ consumo real de estoque
    Se divergência > 5% → erro crítico
    """
    
    if cmv is None or estoque_saida is None or estoque_saida == 0:
        return False, None, "Dados insuficientes"
    
    # Calcular divergência
    if cmv > 0:
        diferenca = abs(cmv - estoque_saida)
        divergencia_pct = (diferenca / cmv) * 100
    else:
        divergencia_pct = 0
    
    if divergencia_pct > THRESHOLDS["cmv_vs_estoque"] * 100:
        log_audit_error(
            "CMV_VS_ESTOQUE_DIVERGENCIA",
            "CRITICO",
            event_id,
            f"CMV (R$ {cmv:,.2f}) diverge {divergencia_pct:.1f}% do estoque (R$ {estoque_saida:,.2f})",
            divergencia_pct
        )
        return False, divergencia_pct, f"Divergência crítica: {divergencia_pct:.1f}%"
    
    return True, divergencia_pct, f"Dentro do limite: {divergencia_pct:.1f}%"


def validate_producao_vs_consumo(producao: Optional[float], consumo: Optional[float],
                                 event_id: str, recipe_id: str = None) -> Tuple[bool, Optional[float], str]:
    """
    B. PRODUÇÃO vs CONSUMO
    produção × ficha técnica ≈ consumo
    Se divergência → erro de ficha ou execução
    """
    
    if producao is None or consumo is None or consumo == 0:
        return False, None, "Dados insuficientes"
    
    # Produção deve estar próxima do consumo (com gap para desperdício aceitável)
    if producao > 0:
        divergencia_pct = ((producao - consumo) / producao) * 100
    else:
        divergencia_pct = 0
    
    # Permitir até 10% de gap
    if abs(divergencia_pct) > THRESHOLDS["producao_vs_consumo"] * 100:
        log_audit_error(
            "PRODUCAO_VS_CONSUMO_DIVERGENCIA",
            "ALTO",
            event_id,
            f"Produção ({producao:.0f}) vs Consumo ({consumo:.0f}) diverge {abs(divergencia_pct):.1f}%",
            abs(divergencia_pct)
        )
        return False, divergencia_pct, f"Possível erro de ficha técnica: {divergencia_pct:.1f}%"
    
    return True, divergencia_pct, f"Produção compatível: {divergencia_pct:.1f}% diferença"


def validate_venda_vs_producao(venda: Optional[float], producao: Optional[float],
                              event_id: str) -> Tuple[bool, str, str]:
    """
    C. VENDA vs PRODUÇÃO
    Se venda > produção → erro grave
    Se produção >> venda → desperdício oculto
    """
    
    if venda is None or producao is None:
        return False, "DADOS_INSUFICIENTES", "Dados de venda ou produção ausentes"
    
    # Erro GRAVE: venda maior que produção
    if venda > producao:
        excesso_pct = ((venda - producao) / producao * 100) if producao > 0 else 0
        log_audit_error(
            "VENDA_MAIOR_QUE_PRODUCAO",
            "CRITICO",
            event_id,
            f"Venda ({venda:.0f}) MAIOR que produção ({producao:.0f})! Excesso: {excesso_pct:.1f}%",
            excesso_pct
        )
        return False, "ERRO_GRAVE", f"Venda excede produção em {excesso_pct:.1f}%"
    
    # Desperdício oculto: produção muito maior que venda
    if producao > 0:
        taxa_utilizacao = (venda / producao) * 100
        desperdicio_pct = 100 - taxa_utilizacao
        
        if desperdicio_pct > 20:  # Mais de 20% de sobra
            log_audit_error(
                "DESPERDICIO_OCULTO",
                "MEDIO",
                event_id,
                f"Produção ({producao:.0f}) >> Venda ({venda:.0f}). Desperdício: {desperdicio_pct:.1f}%",
                desperdicio_pct
            )
            return False, "DESPERDICIO_OCULTO", f"Possível desperdício: {desperdicio_pct:.1f}% não vendido"
    
    return True, "CONSISTENTE", f"Venda/produção dentro dos parâmetros"


def validate_receita_vs_cmv(receita: Optional[float], cmv: Optional[float],
                           event_id: str) -> Tuple[bool, str, str]:
    """
    D. RECEITA vs CMV
    Se CMV > receita → prejuízo real
    """
    
    if receita is None or cmv is None:
        return False, "DADOS_INSUFICIENTES", "Receita ou CMV ausente"
    
    if receita == 0:
        return False, "RECEITA_ZERO", "Impossível calcular margem"
    
    margem = ((receita - cmv) / receita) * 100
    
    # Prejuízo real
    if cmv > receita:
        perda = cmv - receita
        log_audit_error(
            "PREJUIZO_REAL",
            "CRITICO",
            event_id,
            f"CMV (R$ {cmv:,.2f}) > Receita (R$ {receita:,.2f}). PERDA: R$ {perda:,.2f} ({margem:.1f}%)",
            margem
        )
        return False, "PREJUIZO_CONFIRMADO", f"PERDA REAL de R$ {perda:,.2f}"
    
    # Margem crítica
    if margem < 10:
        log_audit_error(
            "MARGEM_CRITICA",
            "ALTO",
            event_id,
            f"Margem de {margem:.1f}% está abaixo do mínimo aceitável (10%)",
            margem
        )
        return False, "MARGEM_RISCO", f"Margem de {margem:.1f}% é crítica"
    
    return True, "LUCRO_CONFIRMADO", f"Margem de {margem:.1f}%"


def classify_event_status(issues: List[str]) -> str:
    """3. Classificar: CONSISTENTE, ALERTA, INCONSISTENTE"""
    
    if not issues:
        return "CONSISTENTE"
    
    criticos = [i for i in issues if "CRITICO" in i or "CRITICA" in i or "GRAVE" in i]
    alertas = [i for i in issues if not ("CRITICO" in i or "CRITICA" in i or "GRAVE" in i)]
    
    if criticos:
        return "INCONSISTENTE"
    elif alertas:
        return "ALERTA"
    else:
        return "CONSISTENTE"


def calculate_risco_financeiro(receita: Optional[float], cmv: Optional[float],
                                 status: str, issues: List[str]) -> str:
    """
    5. Calculate financial risk
    For ordering events by risk
    """
    
    # Check for critical issues first
    critical_count = sum(1 for i in issues if "CRITICO" in i or "CRITICA" in i or "GRAVE" in i)
    
    if critical_count > 0:
        return "ALTO"
    
    if status == "INCONSISTENTE":
        return "ALTO"
    
    # Check margin
    if receita and cmv and receita > 0:
        margem = ((receita - cmv) / receita) * 100
        if margem < 10:
            return "ALTO"
        elif margem < 20:
            return "MEDIO"
    
    if status == "ALERTA":
        return "MEDIO"
    
    return "BAIXO"


def calculate_confidence_score(validacoes: Dict) -> float:
    """Calculate overall confidence score based on validations"""
    
    checks = [
        validacoes.get("cmv_vs_estoque_ok", False),
        validacoes.get("venda_vs_producao_ok", False),
        validacoes.get("receita_vs_cmv_ok", False)
    ]
    
    score = sum(1 for c in checks if c) / len(checks) if checks else 0
    return round(score, 2)


def process_financial_audit() -> List[FinancialAudit]:
    """Processa auditoria financeira para todos os eventos"""
    
    print("\n🔍 Realizando auditoria financeira completa...")
    print("   Validando: Receita ↔ CMV ↔ Estoque ↔ Produção ↔ Venda")
    
    # Carregar dados
    events = load_events_data()
    cmv_data = load_cmv_data()
    estoque_saida_dict = load_estoque_saida()   # renamed: dict keyed by event_id
    producao_e_venda = load_producao_e_venda()
    item_perf = load_item_performance()
    
    if not events:
        print("❌ Nenhum evento encontrado")
        return []
    
    print(f"   ✓ {len(events)} eventos para auditar")
    
    audits = []
    
    for event in events:
        event_id = event.get("event_id")
        n_ctt = event.get("n_ctt", event_id)
        company = event.get("company", "")
        date_event = event.get("date_event", "")
        
        issues = []
        validacoes = {}
        divergencias = []
        
        # Dados financeiros
        receita_total = None
        try:
            receita_total = float(event.get("revenue_total", 0)) if event.get("revenue_total") else None
        except:
            pass
        
        cmv_total = cmv_data.get(event_id, {}).get("cmv_total")
        
        # Dados operacionais — use estoque_saida_dict so the outer dict is never clobbered
        estoque_saida = estoque_saida_dict.get(event_id)
        prod_data = producao_e_venda.get(event_id, {})
        producao_total = prod_data.get("produzido")
        venda_total = prod_data.get("vendido")
        
        # Calcular consumo real se possível
        consumo_real, venda_calc = calculate_consumo_real(event_id, item_perf)
        
        # A: Validar CMV vs Estoque
        if cmv_total and estoque_saida:
            ok, pct, msg = validate_cmv_vs_estoque(cmv_total, estoque_saida, event_id)
            validacoes["cmv_vs_estoque_ok"] = ok
            validacoes["cmv_vs_estoque_msg"] = msg
            if pct is not None:
                divergencias.append({
                    "check": "CMV vs Estoque",
                    "divergencia_pct": pct,
                    "cmv": cmv_total,
                    "estoque": estoque_saida
                })
            if not ok:
                issues.append(f"CMV vs ESTOQUE: {msg}")
        
        # B: Validar Produção vs Consumo
        if producao_total and consumo_real:
            ok, pct, msg = validate_producao_vs_consumo(producao_total, consumo_real, event_id)
            validacoes["producao_vs_consumo_ok"] = ok
            validacoes["producao_vs_consumo_msg"] = msg
            if pct is not None:
                divergencias.append({
                    "check": "Produção vs Consumo",
                    "divergencia_pct": pct,
                    "producao": producao_total,
                    "consumo": consumo_real
                })
            if not ok:
                issues.append(f"PRODUCAO vs CONSUMO: {msg}")
        
        # C: Validar Venda vs Produção
        if venda_total and producao_total:
            ok, status, msg = validate_venda_vs_producao(venda_total, producao_total, event_id)
            validacoes["venda_vs_producao_ok"] = ok
            validacoes["venda_vs_producao_status"] = status
            validacoes["venda_vs_producao_msg"] = msg
            if not ok:
                issues.append(f"VENDA vs PRODUCAO [{status}]: {msg}")
        
        # D: Validar Receita vs CMV
        if receita_total and cmv_total:
            ok, status, msg = validate_receita_vs_cmv(receita_total, cmv_total, event_id)
            validacoes["receita_vs_cmv_ok"] = ok
            validacoes["receita_vs_cmv_status"] = status
            validacoes["receita_vs_cmv_msg"] = msg
            
            margem_bruta_pct = ((receita_total - cmv_total) / receita_total * 100) if receita_total > 0 else None
            validacoes["margem_bruta_pct"] = margem_bruta_pct
            
            if not ok:
                issues.append(f"RECEITA vs CMV [{status}]: {msg}")
        
        # Classificar status
        status = classify_event_status(issues)
        
        # Calcular scores
        confidence_score = calculate_confidence_score(validacoes)
        risco = calculate_risco_financeiro(receita_total, cmv_total, status, issues)
        
        # Criar audit
        audit = FinancialAudit(
            event_id=event_id,
            n_ctt=n_ctt,
            company=company,
            date_event=date_event,
            status=status,
            receita_total=receita_total,
            cmv_total=cmv_total,
            margem_bruta_pct=validacoes.get("margem_bruta_pct"),
            estoque_saida_total=estoque_saida,
            consumo_real=consumo_real,
            producao_total=producao_total,
            venda_total=venda_total,
            validacoes=validacoes,
            divergencias=divergencias,
            issues=issues if issues else [],
            confidence_score=confidence_score,
            risco_financeiro=risco,
            timestamp=datetime.now().isoformat()
        )
        
        audits.append(audit)
    
    return audits


def save_financial_audit(audits: List[FinancialAudit]):
    """4. Salvar financial_audit.json"""
    
    # Ordenar por risco (ALTO primeiro)
    risco_order = {"ALTO": 0, "MEDIO": 1, "BAIXO": 2}
    audits_sorted = sorted(audits, key=lambda x: (risco_order.get(x.risco_financeiro, 3), x.event_id))
    
    output = {
        "_meta": {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_audits": len(audits),
            "resumo": {
                "CONSISTENTE": sum(1 for a in audits if a.status == "CONSISTENTE"),
                "ALERTA": sum(1 for a in audits if a.status == "ALERTA"),
                "INCONSISTENTE": sum(1 for a in audits if a.status == "INCONSISTENTE")
            },
            "risco": {
                "ALTO": sum(1 for a in audits if a.risco_financeiro == "ALTO"),
                "MEDIO": sum(1 for a in audits if a.risco_financeiro == "MEDIO"),
                "BAIXO": sum(1 for a in audits if a.risco_financeiro == "BAIXO")
            },
            "ordenado_por": "risco_financeiro_desc"
        },
        "audits": [asdict(a) for a in audits_sorted]
    }
    
    save_json("financial_audit.json", output)
    print(f"\n✅ Auditoria salva em: kitchen_data/financial_audit.json")


def print_audit_report(audits: List[FinancialAudit]):
    """Imprime relatório de auditoria"""
    
    emoji_status = {
        "CONSISTENTE": "✅",
        "ALERTA": "⚠️",
        "INCONSISTENTE": "🚨"
    }
    
    emoji_risco = {
        "ALTO": "🔴",
        "MEDIO": "🟡",
        "BAIXO": "🟢"
    }
    
    print("\n" + "="*90)
    print("🔍 FINANCIAL TRUTH AUDIT REPORT")
    print("="*90)
    
    # Separar por risco
    alto = [a for a in audits if a.risco_financeiro == "ALTO"]
    medio = [a for a in audits if a.risco_financeiro == "MEDIO"]
    baixo = [a for a in audits if a.risco_financeiro == "BAIXO"]
    
    # ALTO RISCO
    if alto:
        print(f"\n{'─'*90}")
        print(f"🔴 EVENTOS DE ALTO RISCO ({len(alto)}) - ATENÇÃO IMEDIATA")
        print(f"{'─'*90}")
        
        for i, a in enumerate(alto, 1):
            print(f"\n   {i}. {a.event_id} (N CTT: {a.n_ctt})")
            print(f"      Status: {emoji_status[a.status]} {a.status}")
            print(f"      Empresa: {a.company}")
            print(f"      Renda: R$ {a.receita_total:,.2f}" if a.receita_total else "      Renda: N/A")
            print(f"      CMV: R$ {a.cmv_total:,.2f}" if a.cmv_total else "      CMV: N/A")
            print(f"      Margem: {a.margem_bruta_pct:.1f}%" if a.margem_bruta_pct else "      Margem: N/A")
            print(f"      Divergências: {len(a.divergencias)}")
            
            if a.issues:
                print(f"      ⚠️  Problemas ({len(a.issues)}):")
                for issue in a.issues[:3]:
                    print(f"         • {issue}")
            
            print(f"      Confidence: {a.confidence_score:.0%}")
    
    # MEDIO RISCO
    if medio:
        print(f"\n{'─'*90}")
        print(f"🟡 EVENTOS DE RISCO MÉDIO ({len(medio)}) - REVISAR")
        print(f"{'─'*90}")
        
        for a in medio:
            print(f"\n   {a.event_id}")
            print(f"      {emoji_status[a.status]} | R$ {a.receita_total or 0:,.2f} receita | Issues: {len(a.issues)}")
            if a.issues:
                print(f"      → {a.issues[0]}")
    
    # BAIXO RISCO
    if baixo:
        print(f"\n{'─'*90}")
        print(f"🟢 EVENTOS DE BAIXO RISCO ({len(baixo)}) - OK")
        print(f"{'─'*90}")
        
        for a in baixo:
            margem = f"{a.margem_bruta_pct:.1f}%" if a.margem_bruta_pct else "N/A"
            print(f"   ✅ {a.event_id:<12} | R$ {a.receita_total or 0:>10,.2f} | Margem: {margem:>6} | Confidence: {a.confidence_score:.0%}")
    
    # RESUMO
    print(f"\n{'='*90}")
    print("📊 RESUMO DA AUDITORIA")
    print(f"{'='*90}")
    
    status_summary = {"CONSISTENTE": 0, "ALERTA": 0, "INCONSISTENTE": 0}
    risco_summary = {"ALTO": 0, "MEDIO": 0, "BAIXO": 0}
    
    for a in audits:
        status_summary[a.status] += 1
        risco_summary[a.risco_financeiro] += 1
    
    print("\n   Status dos Dados:")
    print(f"      ✅ CONSISTENTE:    {status_summary['CONSISTENTE']:>3}")
    print(f"      ⚠️  ALERTA:        {status_summary['ALERTA']:>3}")
    print(f"      🚨 INCONSISTENTE:  {status_summary['INCONSISTENTE']:>3}")
    
    print("\n   Risco Financeiro:")
    print(f"      🔴 ALTO:   {risco_summary['ALTO']:>3}")
    print(f"      🟡 MEDIO:  {risco_summary['MEDIO']:>3}")
    print(f"      🟢 BAIXO:  {risco_summary['BAIXO']:>3}")
    
    # Alertas críticos
    criticos = sum(1 for a in audits if any("CRITICO" in i or "GRAVE" in i for i in a.issues))
    
    print(f"\n   Alertas Críticos: {criticos}")
    print("="*90)
    
    print("\n⚠️  NOTA:")
    print("   Todos os dados foram APENAS VALIDADOS.")
    print("   NENHUM ajuste foi feito automaticamente.")
    print("   Erros identificados estão em audit_errors.json")


def main():
    """Função principal"""
    
    print("🎛️ FINANCIAL TRUTH AUDIT ENGINE - Orkestra Finance Brain")
    print("="*90)
    print("\n🔍 Validação completa: Receita ↔ CMV ↔ Estoque ↔ Produção ↔ Venda")
    print("   REGRA: Apenas identificar, NUNCA ajustar")
    
    # Processar
    audits = process_financial_audit()
    
    if not audits:
        print("\n❌ Nenhum evento auditado")
        print("   Dados necessários:")
        print("   - events_consolidated.csv")
        print("   - cmv_log.json")
        print("   - production_execution.json")
        return
    
    # Salvar
    save_financial_audit(audits)
    print_audit_report(audits)
    
    print(f"\n✅ Financial Truth Audit completado!")
    print(f"   {len(audits)} eventos auditados")
    print(f"   Ordenado por risco financeiro")


if __name__ == "__main__":
    main()
