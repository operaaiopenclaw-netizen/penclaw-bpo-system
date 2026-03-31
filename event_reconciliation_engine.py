#!/usr/bin/env python3
"""
EVENT RECONCILIATION ENGINE
Compara resultado do sistema com resultado real do evento
Apenas MENSURA diferença - NÃO corrige dados

CLASSIFICAÇÃO:
- OK → erro < 5%
- ATENÇÃO → 5% a 15%
- ERRO → > 15%
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from statistics import mean

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# Limiares de classificação
THRESHOLDS = {
    "ok": 0.05,      # 5%
    "atencao": 0.15  # 15%
}


@dataclass
class ReconciliationResult:
    event_id: str
    n_ctt: str
    company: str
    date_event: str
    
    # Sistema
    sistema_revenue: Optional[float]
    sistema_cmv: Optional[float]
    sistema_profit: Optional[float]
    
    # Real
    real_revenue: Optional[float]
    real_cmv: Optional[float]
    real_profit: Optional[float]
    
    # Diferenças absolutas
    diff_revenue: Optional[float]
    diff_cmv: Optional[float]
    diff_profit: Optional[float]
    
    # Diferenças percentuais
    diff_revenue_pct: Optional[float]
    diff_cmv_pct: Optional[float]
    diff_profit_pct: Optional[float]
    
    # Status
    status_revenue: str  # OK, ATENCAO, ERRO
    status_cmv: str
    status_profit: str
    status_geral: str  # OK, ATENCAO, ERRO, CRITICO
    
    # Explicação
    analysis: str
    timestamp: str


class EventReconciliationEngine:
    """Motor de reconciliação de eventos"""
    
    def __init__(self):
        self.reconciliations = []
        self.summary = {}
    
    def parse_float(self, value) -> Optional[float]:
        """Parser seguro de float"""
        try:
            if value is None or value == "":
                return None
            return float(value)
        except:
            return None
    
    def load_sistema_data(self) -> Dict[str, Dict]:
        """Carrega dados do sistema (DRE)"""
        filepath = OUTPUT_DIR / "dre_events.csv"
        if not filepath.exists():
            filepath = DATA_DIR / "dre_events.csv"
        
        sistema_data = {}
        
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    event_id = row.get("event_id")
                    if event_id:
                        sistema_data[event_id] = {
                            "event_id": event_id,
                            "revenue": self.parse_float(row.get("revenue_total")),
                            "cmv": self.parse_float(row.get("cmv_total")),
                            "profit": self.parse_float(row.get("net_profit")),
                            "gross_profit": self.parse_float(row.get("gross_profit")),
                            "company": row.get("company", "")
                        }
        
        return sistema_data
    
    def load_real_data(self) -> Dict[str, Dict]:
        """
        Carrega dados reais
        
        Espera arquivo: real_events_financial.csv
        Formato: event_id, real_revenue, real_cmv, real_profit
        
        Se não existir, tenta buscar de outras fontes ou retorna vazio
        """
        filepath = DATA_DIR / "real_events_financial.csv"
        real_data = {}
        
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    event_id = row.get("event_id")
                    if event_id:
                        real_data[event_id] = {
                            "event_id": event_id,
                            "revenue": self.parse_float(row.get("real_revenue")),
                            "cmv": self.parse_float(row.get("real_cmv")),
                            "profit": self.parse_float(row.get("real_profit")),
                            "source": row.get("source", "manual_csv"),
                            "data_source": row.get("data_source", "")  # NF, banco, etc
                        }
        else:
            # Se não tem dados reais, criar placeholder
            print("   ⚠️  real_events_financial.csv não encontrado")
            print("      Criando template...")
            self._create_real_data_template()
        
        return real_data
    
    def _create_real_data_template(self):
        """Cria template CSV para dados reais"""
        
        template = """event_id,real_revenue,real_cmv,real_profit,source,data_source,observacoes
EVT001,25000.00,18000.00,7000.00,contabilidade,banco_efetivo,Receita via PIX
EVT002,18000.00,12000.00,6000.00,contabilidade,banco_efetivo,
EVT003,15000.00,11000.00,4000.00,contabilidade,banco_efetivo,
"""
        
        filepath = DATA_DIR / "real_events_financial_TEMPLATE.csv"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)
        
        print(f"      Template criado: {filepath}")
        print("      Renomeie para 'real_events_financial.csv' e preencha com dados reais")
    
    def calculate_difference(self, sistema: Optional[float], real: Optional[float]) -> Tuple[Optional[float], Optional[float], str]:
        """
        Calcula diferença entre sistema e real
        
        Retorna: (diff_absoluta, diff_pct, status)
        """
        if sistema is None or real is None:
            return None, None, "INDISPONIVEL"
        
        if sistema == 0:
            # Evitar divisão por zero
            if real == 0:
                return 0.0, 0.0, "OK"
            else:
                return real - sistema, 100.0, "ERRO"
        
        diff_abs = real - sistema
        diff_pct = (diff_abs / sistema) * 100
        
        # Classificar
        abs_pct = abs(diff_pct)
        
        if abs_pct < THRESHOLDS["ok"] * 100:
            status = "OK"
        elif abs_pct < THRESHOLDS["atencao"] * 100:
            status = "ATENCAO"
        else:
            status = "ERRO"
        
        return diff_abs, diff_pct, status
    
    def generate_analysis(self, rec: ReconciliationResult) -> str:
        """Gera análise textual da diferença"""
        
        parts = []
        
        # Análise de receita
        if rec.diff_revenue_pct is not None:
            if rec.status_revenue == "OK":
                parts.append(f"Receita: próxima do real ({rec.diff_revenue_pct:+.1f}%)")
            elif rec.diff_revenue_pct > 0:
                parts.append(f"Sistema SUBESTIMOU receita em {rec.diff_revenue_pct:.1f}%")
            else:
                parts.append(f"Sistema SOBRESTIMOU receita em {abs(rec.diff_revenue_pct):.1f}%")
        
        # Análise de CMV
        if rec.diff_cmv_pct is not None:
            if rec.status_cmv == "OK":
                parts.append(f"CMV: próximo do real ({rec.diff_cmv_pct:+.1f}%)")
            elif rec.diff_cmv_pct > 0:
                parts.append(f"CMV real MAIOR que sistema ({rec.diff_cmv_pct:+.1f}%) - custo subestimado")
            else:
                parts.append(f"CMV real MENOR que sistema ({rec.diff_cmv_pct:+.1f}%) - custo superestimado")
        
        # Análise de lucro
        if rec.diff_profit_pct is not None:
            if rec.status_profit == "OK":
                parts.append(f"Lucro: próximo do real ({rec.diff_profit_pct:+.1f}%)")
            elif rec.diff_profit_pct > 0:
                parts.append(f"Sistema SUBESTIMOU lucro em {rec.diff_profit_pct:.1f}%")
            else:
                parts.append(f"Sistema SOBRESTIMOU lucro em {abs(rec.diff_profit_pct):.1f}%")
        
        # Status geral
        if rec.status_geral == "OK":
            parts.append("✅ Sistema alinhado com realidade")
        elif rec.status_geral == "ATENCAO":
            parts.append("⚠️ Sistema com diferenças aceitáveis - monitorar")
        elif rec.status_geral == "ERRO":
            parts.append("🚨 Sistema com diferenças significativas - investigar")
        
        return " | ".join(parts) if parts else "Dados insuficientes para análise"
    
    def process_reconciliation(self):
        """Processa reconciliação para todos os eventos"""
        
        print("\n🔄 Iniciando reconciliação de eventos...")
        print("   Comparando: Sistema vs Real")
        
        # Carregar dados
        sistema = self.load_sistema_data()
        real = self.load_real_data()
        
        if not sistema:
            print("   ❌ Nenhum dado do sistema encontrado")
            print("      Execute dre_engine.py primeiro")
            return []
        
        if not real:
            print("   ⚠️  Nenhum dado real encontrado")
            print("      Preencha real_events_financial.csv")
            return []
        
        print(f"   ✓ {len(sistema)} eventos no sistema")
        print(f"   ✓ {len(real)} eventos com dados reais")
        
        reconciliations = []
        
        # Para cada evento com ambos os dados
        for event_id, sist_data in sistema.items():
            if event_id not in real:
                print(f"   ⚠️  {event_id}: sem dados reais - ignorado")
                continue
            
            real_data = real[event_id]
            
            # Calcular diferenças
            diff_rev, diff_rev_pct, status_rev = self.calculate_difference(
                sist_data.get("revenue"), real_data.get("revenue")
            )
            diff_cmv, diff_cmv_pct, status_cmv = self.calculate_difference(
                sist_data.get("cmv"), real_data.get("cmv")
            )
            diff_prof, diff_prof_pct, status_prof = self.calculate_difference(
                sist_data.get("profit"), real_data.get("profit")
            )
            
            # Status geral (pior dos casos)
            statuses = [status_rev, status_cmv, status_prof]
            if "ERRO" in statuses:
                status_geral = "ERRO"
            elif "ATENCAO" in statuses:
                status_geral = "ATENCAO"
            elif "INDISPONIVEL" in statuses:
                status_geral = "INCOMPLETO"
            else:
                status_geral = "OK"
            
            rec = ReconciliationResult(
                event_id=event_id,
                n_ctt=event_id.replace("EVT", "CTT"),  # Exemplo
                company=sist_data.get("company", ""),
                date_event="",  # Preencher se disponível
                
                sistema_revenue=sist_data.get("revenue"),
                sistema_cmv=sist_data.get("cmv"),
                sistema_profit=sist_data.get("profit"),
                
                real_revenue=real_data.get("revenue"),
                real_cmv=real_data.get("cmv"),
                real_profit=real_data.get("profit"),
                
                diff_revenue=diff_rev,
                diff_cmv=diff_cmv,
                diff_profit=diff_prof,
                
                diff_revenue_pct=diff_rev_pct,
                diff_cmv_pct=diff_cmv_pct,
                diff_profit_pct=diff_prof_pct,
                
                status_revenue=status_rev,
                status_cmv=status_cmv,
                status_profit=status_prof,
                status_geral=status_geral,
                
                analysis="",  # Preenchido depois
                timestamp=datetime.now().isoformat()
            )
            
            rec.analysis = self.generate_analysis(rec)
            reconciliations.append(rec)
        
        return reconciliations
    
    def generate_summary(self, reconciliations: List[ReconciliationResult]):
        """Gera resumo estatístico"""
        
        if not reconciliations:
            return {}
        
        total = len(reconciliations)
        
        # Por status
        ok = sum(1 for r in reconciliations if r.status_geral == "OK")
        atencao = sum(1 for r in reconciliations if r.status_geral == "ATENCAO")
        erro = sum(1 for r in reconciliations if r.status_geral == "ERRO")
        
        # Médias de diferença
        diffs_rev = [r.diff_revenue_pct for r in reconciliations if r.diff_revenue_pct is not None]
        diffs_cmv = [r.diff_cmv_pct for r in reconciliations if r.diff_cmv_pct is not None]
        diffs_prof = [r.diff_profit_pct for r in reconciliations if r.diff_profit_pct is not None]
        
        summary = {
            "total_eventos": total,
            "alinhados": {
                "quantidade": ok,
                "percentual": round(ok / total * 100, 1),
                "descricao": "Sistema próximo da realidade"
            },
            "atenção": {
                "quantidade": atencao,
                "percentual": round(atencao / total * 100, 1),
                "descricao": "Diferenças aceitáveis - monitorar"
            },
            "erros": {
                "quantidade": erro,
                "percentual": round(erro / total * 100, 1),
                "descricao": "Diferenças significativas - investigar"
            },
            "diferencas_medias": {
                "receita": round(mean(diffs_rev), 2) if diffs_rev else None,
                "cmv": round(mean(diffs_cmv), 2) if diffs_cmv else None,
                "lucro": round(mean(diffs_prof), 2) if diffs_prof else None
            },
            "maior_diferenca": {
                "revenue_max": max(diffs_rev, key=abs) if diffs_rev else None,
                "cmv_max": max(diffs_cmv, key=abs) if diffs_cmv else None,
                "profit_max": max(diffs_prof, key=abs) if diffs_prof else None
            }
        }
        
        return summary
    
    def save_report(self, reconciliations: List[ReconciliationResult]):
        """Salva relatório em JSON"""
        
        summary = self.generate_summary(reconciliations)
        
        output = {
            "_meta": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "disclaimer": "APENAS MENSURAÇÃO - NÃO CORRIGE DADOS",
                "thresholds": {
                    "ok_percent": THRESHOLDS["ok"] * 100,
                    "atencao_percent": THRESHOLDS["atencao"] * 100
                }
            },
            "summary": summary,
            "reconciliations": [asdict(r) for r in reconciliations],
            "recommendations": self._generate_recommendations(summary)
        }
        
        filepath = DATA_DIR / "reconciliation_report.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Relatório salvo: kitchen_data/reconciliation_report.json")
        
        return output
    
    def _generate_recommendations(self, summary: Dict) -> List[Dict]:
        """Gera recomendações baseadas no summary"""
        
        recs = []
        
        erro_pct = summary.get("erros", {}).get("percentual", 0)
        atencao_pct = summary.get("atencão", {}).get("percentual", 0)
        
        if erro_pct > 20:
            recs.append({
                "priority": "CRITICAL",
                "message": f"{erro_pct:.1f}% de eventos com diferença > 15%",
                "action": "Investigar sistematicamente casos de erro. Verificar fonte de dados real vs sistema.",
                "area": "data_quality"
            })
        elif erro_pct > 10:
            recs.append({
                "priority": "HIGH",
                "message": f"{erro_pct:.1f}% de eventos com diferença significativa",
                "action": "Revisar processo de coleta de dados reais. Amostragem pode estar enviesada.",
                "area": "process"
            })
        
        if atencao_pct > 30:
            recs.append({
                "priority": "MEDIUM",
                "message": f"{atencao_pct:.1f}% de eventos com diferença moderada",
                "action": "Normal para operação com variabilidade. Manter monitoramento.",
                "area": "monitoring"
            })
        
        if not recs:
            recs.append({
                "priority": "LOW",
                "message": "Sistema alinhado com realidade",
                "action": "Continuar coleta de dados para manter calibração",
                "area": "maintenance"
            })
        
        return recs
    
    def print_report(self, reconciliations: List[ReconciliationResult]):
        """Imprime relatório de reconciliação"""
        
        print("\n" + "="*80)
        print("📊 EVENT RECONCILIATION REPORT")
        print("="*80)
        print("   Sistema vs Realidade")
        print("   APENAS MENSURAÇÃO - NÃO CORRIGE DADOS")
        print("="*80)
        
        if not reconciliations:
            print("\n   ⚠️  Nenhuma reconciliação realizada")
            print("      Verifique se há dados em:")
            print("      - dre_events.csv (sistema)")
            print("      - real_events_financial.csv (real)")
            return
        
        # Resumo
        summary = self.generate_summary(reconciliations)
        
        print(f"\n📈 RESUMO ESTATÍSTICO")
        print(f"{'─'*80}")
        print(f"   Total de Eventos Analisados: {summary.get('total_eventos', 0)}")
        print(f"\n   ✅ Alinhados (erro < 5%):")
        print(f"      {summary['alinhados']['quantidade']} eventos ({summary['alinhados']['percentual']:.1f}%)")
        print(f"\n   ⚠️  Atenção (erro 5-15%):")
        print(f"      {summary['atenção']['quantidade']} eventos ({summary['atenção']['percentual']:.1f}%)")
        print(f"\n   🚨 Erro (erro > 15%):")
        print(f"      {summary['erros']['quantidade']} eventos ({summary['erros']['percentual']:.1f}%)")
        
        # Diferenças médias
        diffs = summary.get("diferencas_medias", {})
        print(f"\n📊 DIFERENÇAS MÉDIAS")
        print(f"{'─'*80}")
        if diffs.get("receita") is not None:
            print(f"   Receita: {diffs['receita']:+.2f}%")
        if diffs.get("cmv") is not None:
            print(f"   CMV:     {diffs['cmv']:+.2f}%")
        if diffs.get("lucro") is not None:
            print(f"   Lucro:   {diffs['lucro']:+.2f}%")
        
        # Maiores divergências
        print(f"\n⚠️ MAIORES DIVERGÊNCIAS")
        print(f"{'─'*80}")
        max_diff = summary.get("maior_diferenca", {})
        if max_diff.get("revenue_max"):
            print(f"   Receita: {max_diff['revenue_max']:+.1f}%")
        if max_diff.get("cmv_max"):
            print(f"   CMV:     {max_diff['cmv_max']:+.1f}%")
        if max_diff.get("profit_max"):
            print(f"   Lucro:   {max_diff['profit_max']:+.1f}%")
        
        # Detalhamento por evento
        print(f"\n📋 DETALHAMENTO POR EVENTO")
        print(f"{'─'*80}")
        
        # Ordenar por status (ERRO primeiro)
        def sort_key(r):
            order = {"ERRO": 0, "ATENCAO": 1, "OK": 2, "INCOMPLETO": 3}
            return order.get(r.status_geral, 4)
        
        sorted_recs = sorted(reconciliations, key=sort_key)
        
        for rec in sorted_recs:
            emoji = {"OK": "✅", "ATENCAO": "⚠️", "ERRO": "🚨", "INCOMPLETO": "❓"}.get(rec.status_geral, "⚪")
            
            print(f"\n   {emoji} {rec.event_id} [{rec.status_geral}]")
            
            # Receita
            if rec.diff_revenue_pct is not None:
                print(f"      Receita: Sistema R$ {rec.sistema_revenue:,.2f} vs Real R$ {rec.real_revenue:,.2f}")
                print(f"               Diferença: {rec.diff_revenue_pct:+.1f}% [{rec.status_revenue}]")
            
            # CMV
            if rec.diff_cmv_pct is not None:
                print(f"      CMV:     Sistema R$ {rec.sistema_cmv:,.2f} vs Real R$ {rec.real_cmv:,.2f}")
                print(f"               Diferença: {rec.diff_cmv_pct:+.1f}% [{rec.status_cmv}]")
            
            # Lucro
            if rec.diff_profit_pct is not None:
                print(f"      Lucro:   Sistema R$ {rec.sistema_profit:,.2f} vs Real R$ {rec.real_profit:,.2f}")
                print(f"               Diferença: {rec.diff_profit_pct:+.1f}% [{rec.status_profit}]")
            
            # Análise
            print(f"      💡 {rec.analysis}")
        
        # Recomendações
        print(f"\n💡 RECOMENDAÇÕES")
        print(f"{'─'*80}")
        # Recomendações são mostradas no save_report
        recs = self._generate_recommendations(summary)
        for rec in recs:
            emoji = {"CRITICAL": "🚨", "HIGH": "🔴", "MEDIUM": "⚠️", "LOW": "ℹ️"}.get(rec["priority"], "⚪")
            print(f"\n   {emoji} [{rec['priority']}] {rec['message']}")
            print(f"      → {rec['action']}")
        
        print(f"\n{'='*80}")
        print("⚠️  NOTA: Este relatório APENAS MENSURA diferenças.")
        print("    NENHUM dado foi corrigido automaticamente.")
        print("    Decisão de ajuste é manual e documentada em calibration_suggestions.json")
        print(f"{'='*80}\n")


def main():
    """Função principal"""
    
    print("🎛️ EVENT RECONCILIATION ENGINE - Orkestra Finance Brain")
    print("="*80)
    print("\n📊 Comparando: Sistema vs Realidade")
    print("   REGRA: Apenas MENSURA - NÃO CORRIGE")
    
    engine = EventReconciliationEngine()
    
    # Processar
    reconciliations = engine.process_reconciliation()
    
    if not reconciliations:
        print("\n❌ Reconciliação não realizada")
        print("   Certifique-se de ter:")
        print("   1. output/dre_events.csv (dados do sistema)")
        print("   2. kitchen_data/real_events_financial.csv (dados reais)")
        return
    
    # Salvar
    engine.save_report(reconciliations)
    
    # Imprimir
    engine.print_report(reconciliations)
    
    print(f"✅ Event Reconciliation Engine completado!")
    print(f"   {len(reconciliations)} eventos reconciliados")


if __name__ == "__main__":
    main()
