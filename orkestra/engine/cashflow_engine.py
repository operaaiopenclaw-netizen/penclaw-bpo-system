# cashflow_engine.py - Orkestra Cashflow Engine
# Reconstrói fluxo de caixa real e detecta vazamentos financeiros

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Optional


class CashflowEngine:
    """
    Motor de análise de fluxo de caixa real.
    Detecta vazamentos financeiros e inconsistências.
    """
    
    def __init__(self):
        self.transactions: List[Dict] = []
        self.monthly_flow: Dict[str, Dict] = {}
        self.alerts: List[Dict] = []
        
    def normalize_date(self, date_str: str) -> str:
        """Normaliza data para YYYY-MM."""
        try:
            # Tentar ISO format
            if len(date_str) >= 7 and date_str[4] == '-':
                return date_str[:7]  # YYYY-MM
            # Outros formatos
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                try:
                    dt = datetime.strptime(date_str[:10], fmt)
                    return dt.strftime("%Y-%m")
                except:
                    continue
        except:
            pass
        return date_str[:7] if len(date_str) >= 7 else "unknown"
    
    def parse_value(self, value: Any) -> float:
        """Extrai valor numérico."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remover R$, espaços, pontos de milhar
            clean = value.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
            try:
                return float(clean)
            except:
                return 0.0
        return 0.0
    
    def classify_transaction(self, txn: Dict) -> str:
        """
        Classifica transação em categoria financeira.
        """
        tipo = str(txn.get("type", "")).lower()
        categoria = str(txn.get("category", "")).lower()
        descricao = str(txn.get("description", txn.get("descricao", ""))).lower()
        
        # Receitas
        if tipo in ["income", "receita", "entrada", "recebimento"]:
            if "transfer" in descricao or "entre empresa" in descricao:
                return "TRANSFERENCIA_ENTRADA"
            return "RECEITA_OPERACIONAL"
        
        # Despesas operacionais
        if categoria in ["protein", "beverages", "bebidas", "staff", "ambiance", "supplies", "infrastructure"]:
            return "CUSTO_OPERACIONAL"
        
        # Despesas fixas
        if any(k in descricao for k in ["aluguel", "salario", "salário", "condominio", "luz", "agua", "internet", "telefone"]):
            return "DESPESA_FIXA"
        
        # Despesas variáveis
        if any(k in descricao for k in ["combustivel", "comida", "transporte", "material", "imprevisto"]):
            return "DESPESA_VARIAVEL"
        
        # Transferências
        if any(k in descricao for k in ["transferencia", "transferência", "entre empresa", "envio", "recebimento outra"])
            return "TRANSFERENCIA_SAIDA" if tipo in ["expense", "despesa", "saida"] else "TRANSFERENCIA_ENTRADA"
        
        # Retiradas sócios
        if any(k in descricao for k in ["pro-labore", "prolabore", "dividendo", "retirada", "socio", "sócio", "distribuicao", "distribuição"]):
            return "RETIRADA_SOCIO"
        
        # Padrão
        return "OUTRO"
    
    def load_transactions(self, source_files: List[str] = None) -> "CashflowEngine":
        """
        Carrega transações de múltiplas fontes.
        """
        # Carregar de financial_log.json
        log_path = Path("financial_log.json")
        if log_path.exists():
            with open(log_path) as f:
                data = json.load(f)
                self.transactions.extend(data.get("transactions", []))
        
        # Carregar de datasets de eventos
        for year in ["2024", "2025"]:
            dataset_path = Path(f"data/event_dataset_{year}.json")
            if dataset_path.exists():
                with open(dataset_path) as f:
                    data = json.load(f)
                    # Extrair transações dos contratos
                    for contract in data.get("contracts", []):
                        # Criar transação de receita
                        if contract.get("revenue_total", 0) > 0:
                            self.transactions.append({
                                "type": "income",
                                "value": contract["revenue_total"],
                                "category": "event",
                                "event": contract["contract_id"],
                                "date": contract.get("date", "2024-01-01"),
                                "description": f"Receita {contract['contract_id']}"
                            })
                        # Custos estimados (70% da receita como proxy)
                        if contract.get("revenue_locacao", 0) > 0:
                            self.transactions.append({
                                "type": "expense",
                                "value": contract["revenue_locacao"],
                                "category": "infrastructure",
                                "event": contract["contract_id"],
                                "date": contract.get("date", "2024-01-01"),
                                "description": f"Custo locação {contract['contract_id']}"
                            })
                        if contract.get("revenue_catering", 0) > 0:
                            self.transactions.append({
                                "type": "expense",
                                "value": contract["revenue_catering"] * 0.6,  # 60% custo
                                "category": "beverages",
                                "event": contract["contract_id"],
                                "date": contract.get("date", "2024-01-01"),
                                "description": f"Custo catering {contract['contract_id']}"
                            })
        
        # Arquivos adicionais
        if source_files:
            for filepath in source_files:
                if Path(filepath).exists():
                    with open(filepath) as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self.transactions.extend(data)
                        elif isinstance(data, dict) and "transactions" in data:
                            self.transactions.extend(data["transactions"])
        
        print(f"✅ {len(self.transactions)} transações carregadas")
        return self
    
    def rebuild_cashflow(self) -> Dict:
        """
        Reconstrói fluxo de caixa mês a mês.
        """
        # Agrupar por mês
        monthly = defaultdict(lambda: {
            "entradas": 0.0,
            "saidas": 0.0,
            "receita_operacional": 0.0,
            "custo_operacional": 0.0,
            "despesa_fixa": 0.0,
            "despesa_variavel": 0.0,
            "transferencia_entrada": 0.0,
            "transferencia_saida": 0.0,
            "retirada_socio": 0.0,
            "outro": 0.0,
            "transacoes": []
        })
        
        for txn in self.transactions:
            date = txn.get("date", "")
            month = self.normalize_date(date) if date else "unknown"
            value = self.parse_value(txn.get("value", 0))
            category = self.classify_transaction(txn)
            
            # Classificar
            if category == "RECEITA_OPERACIONAL":
                monthly[month]["entradas"] += value
                monthly[month]["receita_operacional"] += value
            elif category == "TRANSFERENCIA_ENTRADA":
                monthly[month]["transferencia_entrada"] += value
            else:
                # É saída
                monthly[month]["saidas"] += value
                
                if category == "CUSTO_OPERACIONAL":
                    monthly[month]["custo_operacional"] += value
                elif category == "DESPESA_FIXA":
                    monthly[month]["despesa_fixa"] += value
                elif category == "DESPESA_VARIAVEL":
                    monthly[month]["despesa_variavel"] += value
                elif category == "TRANSFERENCIA_SAIDA":
                    monthly[month]["transferencia_saida"] += value
                elif category == "RETIRADA_SOCIO":
                    monthly[month]["retirada_socio"] += value
                else:
                    monthly[month]["outro"] += value
            
            monthly[month]["transacoes"].append(txn)
        
        # Calcular saldos
        for month, data in monthly.items():
            data["saldo_real"] = data["entradas"] - data["saidas"]
            data["saldo_ajustado"] = (
                data["receita_operacional"] 
                - data["custo_operacional"] 
                - data["despesa_fixa"] 
                - data["despesa_variavel"]
            )
            data["lucro_contabil"] = (
                data["receita_operacional"] 
                - data["custo_operacional"]
            )
            data["diferenca"] = data["saldo_real"] - data["saldo_ajustado"]
        
        self.monthly_flow = dict(monthly)
        return self.monthly_flow
    
    def detect_cash_leaks(self) -> List[Dict]:
        """
        Detecta vazamentos financeiros.
        """
        alerts = []
        
        for month, data in self.monthly_flow.items():
            # Alerta 1: Lucro contábil positivo mas caixa real negativo
            if data["lucro_contabil"] > 0 and data["saldo_real"] < 0:
                alerts.append({
                    "month": month,
                    "type": "LUCRO_POSITIVO_CAIXA_NEGATIVO",
                    "severity": "HIGH",
                    "message": f"Mês {month}: Lucro R$ {data['lucro_contabil']:,.2f} mas caixa R$ {data['saldo_real']:,.2f}",
                    "details": {
                        "lucro_contabil": data["lucro_contabil"],
                        "saldo_real": data["saldo_real"],
                        "diferenca": data["diferenca"]
                    }
                })
            
            # Alerta 2: Retiradas de sócio > 20% do lucro
            if data["lucro_contabil"] > 0:
                retirada_pct = (data["retirada_socio"] / data["lucro_contabil"]) * 100
                if retirada_pct > 20:
                    alerts.append({
                        "month": month,
                        "type": "RETIRADA_EXCESSIVA",
                        "severity": "MEDIUM",
                        "message": f"Mês {month}: Retirada R$ {data['retirada_socio']:,.2f} ({retirada_pct:.1f}% do lucro)",
                        "details": {
                            "retirada": data["retirada_socio"],
                            "lucro": data["lucro_contabil"],
                            "percentual": retirada_pct
                        }
                    })
            
            # Alerta 3: Transferências desbalanceadas
            net_transfer = data["transferencia_entrada"] - data["transferencia_saida"]
            if abs(net_transfer) > data["receita_operacional"] * 0.5:
                alerts.append({
                    "month": month,
                    "type": "TRANSFERENCIA_DESBALANCEADA",
                    "severity": "LOW",
                    "message": f"Mês {month}: Transferência líquida R$ {net_transfer:,.2f}",
                    "details": {
                        "entrada": data["transferencia_entrada"],
                        "saida": data["transferencia_saida"],
                        "liquido": net_transfer
                    }
                })
            
            # Alerta 4: Vazamento detectado (despesas fixas altas)
            if data["despesa_fixa"] > data["receita_operacional"] * 0.3:
                alerts.append({
                    "month": month,
                    "type": "ALTA_CARGA_FIXA",
                    "severity": "MEDIUM",
                    "message": f"Mês {month}: Despesas fixas R$ {data['despesa_fixa']:,.2f} ({(data['despesa_fixa']/data['receita_operacional']*100):.1f}% da receita)",
                    "details": {
                        "despesa_fixa": data["despesa_fixa"],
                        "receita": data["receita_operacional"]
                    }
                })
        
        self.alerts = alerts
        return alerts
    
    def generate_report(self) -> Dict:
        """
        Gera relatório completo.
        """
        if not self.monthly_flow:
            self.rebuild_cashflow()
        
        if not self.alerts:
            self.detect_cash_leaks()
        
        # Calcular totais
        total_entradas = sum(m["entradas"] for m in self.monthly_flow.values())
        total_saidas = sum(m["saidas"] for m in self.monthly_flow.values())
        total_lucro = sum(m["lucro_contabil"] for m in self.monthly_flow.values())
        total_retiradas = sum(m["retirada_socio"] for m in self.monthly_flow.values())
        
        # Identificar meses com problema
        meses_problema = [a["month"] for a in self.alerts if a["severity"] == "HIGH"]
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start": min(self.monthly_flow.keys()) if self.monthly_flow else None,
                "end": max(self.monthly_flow.keys()) if self.monthly_flow else None
            },
            "summary": {
                "total_meses": len(self.monthly_flow),
                "total_entradas": round(total_entradas, 2),
                "total_saidas": round(total_saidas, 2),
                "saldo_final": round(total_entradas - total_saidas, 2),
                "lucro_contabil_total": round(total_lucro, 2),
                "total_retiradas": round(total_retiradas, 2),
                "retiradas_vs_lucro_pct": round((total_retiradas / total_lucro * 100), 2) if total_lucro > 0 else 0,
                "meses_com_problema": meses_problema,
                "total_alertas": len(self.alerts)
            },
            "monthly_cashflow": self.monthly_flow,
            "alerts": self.alerts,
            "critical_issues": [a for a in self.alerts if a["severity"] == "HIGH"],
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Gera recomendações baseadas nos alertas."""
        recs = []
        
        # Alertas de lucro positivo caixa negativo
        lucro_caixa = [a for a in self.alerts if a["type"] == "LUCRO_POSITIVO_CAIXA_NEGATIVO"]
        if lucro_caixa:
            recs.append(f"🚨 {len(lucro_caixa)} meses com lucro contábil positivo mas caixa real negativo. Revisar timing de recebimentos e pagamentos.")
        
        # Retiradas excessivas
        retiradas = [a for a in self.alerts if a["type"] == "RETIRADA_EXCESSIVA"]
        if retiradas:
            total_retirada_pct = sum(a["details"]["retirada"] for a in retiradas) / sum(a["details"]["lucro"] for a in retiradas) * 100 if any(a["details"]["lucro"] > 0 for a in retiradas) else 0
            recs.append(f"⚠️ Retiradas de sócios estão em média {total_retirada_pct:.1f}% do lucro. Considerar limitar a 20% para reinvestimento.")
        
        # Transferências
        transfers = [a for a in self.alerts if a["type"] == "TRANSFERENCIA_DESBALANCEADA"]
        if transfers:
            recs.append(f"ℹ️ Detectadas transferências desbalanceadas entre empresas. Revisar estrutura de caixa consolidado.")
        
        # Despesas fixas
        fixas = [a for a in self.alerts if a["type"] == "ALTA_CARGA_FIXA"]
        if fixas:
            recs.append(f"📈 {len(fixas)} meses com alta carga fixa (>30% receita). Negociar contratos ou buscar receitas recorrentes.")
        
        if not recs:
            recs.append("✅ Fluxo de caixa saudável. Nenhuma ação necessária.")
        
        return recs
    
    def print_report(self, report: Dict):
        """Imprime relatório formatado."""
        print("\n" + "=" * 70)
        print("💰 ORKESTRA CASHFLOW ENGINE REPORT")
        print("=" * 70)
        
        summary = report["summary"]
        print(f"\n📊 PERÍODO: {report['period']['start']} a {report['period']['end']}")
        print(f"📊 TOTAL MESES: {summary['total_meses']}")
        
        print("\n" + "-" * 70)
        print("💰 RESUMO FINANCEIRO")
        print("-" * 70)
        print(f"   Entradas:           R$ {summary['total_entradas']:>15,.2f}")
        print(f"   Saídas:             R$ {summary['total_saidas']:>15,.2f}")
        print(f"   ───────────────────────────────────────")
        print(f"   SALDO REAL:         R$ {summary['saldo_final']:>15,.2f}")
        print(f"   LUCRO CONTÁBIL:     R$ {summary['lucro_contabil_total']:>15,.2f}")
        print(f"   DIFERENÇA:          R$ {summary['saldo_final'] - summary['lucro_contabil_total']:>15,.2f}")
        
        print("\n" + "-" * 70)
        print("📊 RETIRADAS")
        print("-" * 70)
        print(f"   Total Retiradas:    R$ {summary['total_retiradas']:>15,.2f}")
        print(f"   % do Lucro:         {summary['retiradas_vs_lucro_pct']:>16.1f}%")
        status = "✅ OK" if summary['retiradas_vs_lucro_pct'] <= 20 else "⚠️  ACIMA DO IDEAL"
        print(f"   Status:             {status:>15}")
        
        print("\n" + "-" * 70)
        print("🔴 ALERTAS CRÍTICOS")
        print("-" * 70)
        if report["critical_issues"]:
            for alert in report["critical_issues"][:5]:
                print(f"   [{alert['severity']}] {alert['type']}")
                print(f"   → {alert['message']}")
        else:
            print("   ✅ Nenhum alerta crítico")
        
        print("\n" + "-" * 70)
        print("💡 RECOMENDAÇÕES")
        print("-" * 70)
        for rec in report["recommendations"]:
            print(f"   {rec}")
        
        if report["monthly_cashflow"]:
            print("\n" + "-" * 70)
            print("📅 FLUXO MENSAL (últimos 6 meses)")
            print("-" * 70)
            months = sorted(report["monthly_cashflow"].keys())[-6:]
            for month in months:
                data = report["monthly_cashflow"][month]
                status = "✅" if data['saldo_real'] >= 0 else "❌"
                print(f"   {status} {month}: Entradas R$ {data['entradas']:>10,.0f} | Saídas R$ {data['saidas']:>10,.0f} | Saldo R$ {data['saldo_real']:>10,.0f}")
        
        print("\n" + "=" * 70)
        print(f"💾 Total Alertas: {summary['total_alertas']}")
        print(f"💾 Relatório salvo: orkestra/memory/cashflow_report.json")
        print("=" * 70)


def run_cashflow_analysis(source_files: List[str] = None):
    """
    Executa análise completa de fluxo de caixa.
    """
    print("\n🚀 ORKESTRA CASHFLOW ENGINE")
    print("=" * 70)
    
    engine = CashflowEngine()
    engine.load_transactions(source_files)
    
    print("\n🔍 Reconstruindo fluxo de caixa...")
    engine.rebuild_cashflow()
    
    print("\n🔍 Detectando vazamentos...")
    leaks = engine.detect_cash_leaks()
    print(f"   {len(leaks)} alertas encontrados")
    
    print("\n📊 Gerando relatório...")
    report = engine.generate_report()
    
    # Salvar
    output_path = Path("orkestra/memory/cashflow_report.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Imprimir
    engine.print_report(report)
    
    return report


if __name__ == "__main__":
    import sys
    
    # Arquivos adicionais opcionais
    extra_files = sys.argv[1:] if len(sys.argv) > 1 else None
    
    run_cashflow_analysis(extra_files)
