# intercompany_control.py - Orkestra Intercompany Control System
# Organiza fluxo financeiro entre STATUS (comercial) e LA ORANA (operação)

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class IntercompanyTransaction:
    """Transação entre empresas."""
    id: str
    date: str
    from_company: str
    to_company: str
    amount: float
    event_id: str
    description: str
    status: str  # pending, paid, confirmed
    source_doc: str = ""


@dataclass
class EventAllocation:
    """Alocação de evento entre empresas."""
    event_id: str
    revenue_total: float
    
    # Quem vende (recebe cliente)
    status_revenue: float  # comercial
    
    # Quem executa (faz caterin)
    la_orana_execution_cost: float
    la_orana_revenue_share: float
    
    # Cálculo de transferência
    status_to_la_orana: float  # quanto status deve pagar para LA ORANA
    
    # Saldos
    status_net: float
    la_orana_net: float


class IntercompanyControl:
    """
    Sistema de controle inter-empresas.
    Gerencia fluxo entre STATUS (comercial) e LA ORANA (operação).
    """
    
    # Regras de distribuição
    LA_ORANA_REVENUE_SHARE = 0.65  # LA ORANA fica com 65% da receita
    STATUS_COMMERCIAL_FEE = 0.35   # STATUS fica com 35% (comissão comercial)
    
    # Empresas
    STATUS = "STATUS"
    LA_ORANA = "LA ORANA"
    
    def __init__(self):
        self.events: List[EventAllocation] = []
        self.transfers: List[IntercompanyTransaction] = []
        self.balances: Dict[str, Dict] = {}
        self.pending_transfers: List[Dict] = []
        
    def allocate_event(self, event_id: str, revenue_total: float, 
                       execution_cost: float = None) -> EventAllocation:
        """
        Aloca receita e custos entre as duas empresas.
        
        Regra:
        - STATUS recebe 100% do cliente (venda)
        - LA ORANA executa (custo de operação)
        - STATUS paga LA ORANA: custo + margem OU % da receita
        
        Modelo padrão: Transferência = 65% da receita
        """
        # LA ORANA recebe % da receita por executar
        la_orana_revenue = revenue_total * self.LA_ORANA_REVENUE_SHARE
        
        # STATUS fica com comissão comercial
        status_revenue = revenue_total * self.STATUS_COMMERCIAL_FEE
        
        # Se tem custo de execução específico, calcular margem
        if execution_cost:
            # Modelo alternativo: custo + margem padrão (30%)
            la_orana_target = execution_cost * 1.30
            # Usar o MAIOR valor (protege LA ORANA)
            la_orana_amount = max(la_orana_revenue, la_orana_target)
        else:
            la_orana_amount = la_orana_revenue
            execution_cost = la_orana_amount * 0.70  # estimativa
        
        # STATUS deve transferir para LA ORANA
        status_to_la_orana = la_orana_amount
        
        # Cálculo de saldo líquido
        # STATUS: recebe tudo - paga LA ORANA
        status_net = status_revenue - status_to_la_orana
        # LA ORANA: recebe da STATUS - tem custo
        la_orana_net = la_orana_amount - execution_cost
        
        return EventAllocation(
            event_id=event_id,
            revenue_total=revenue_total,
            status_revenue=status_revenue,
            la_orana_execution_cost=execution_cost,
            la_orana_revenue_share=la_orana_amount,
            status_to_la_orana=status_to_la_orana,
            status_net=status_net,
            la_orana_net=la_orana_net
        )
    
    def load_events_from_datasets(self):
        """Carrega e aloca eventos dos datasets."""
        for year in ["2024", "2025"]:
            path = Path(f"data/event_dataset_{year}.json")
            if not path.exists():
                continue
            
            with open(path) as f:
                data = json.load(f)
            
            for contract in data.get("contracts", []):
                event_id = contract.get("contract_id", "UNKNOWN")
                revenue = contract.get("revenue_total", 0)
                
                # Estimar custo de execução (catering é a operação da LA ORANA)
                catering_revenue = contract.get("revenue_catering", 0)
                execution_cost = catering_revenue * 0.60  # 60% custo
                
                allocation = self.allocate_event(event_id, revenue, execution_cost)
                self.events.append(allocation)
        
        print(f"✅ {len(self.events)} eventos alocados entre STATUS e LA ORANA")
        return self
    
    def load_transfers(self, source_files: List[str] = None):
        """Carrega transferências entre empresas."""
        # Tentar carregar de arquivos
        files = source_files or ["financial_log.json", "data/intercompany_transfers.json"]
        
        for filepath in files:
            path = Path(filepath)
            if not path.exists():
                continue
            
            with open(path) as f:
                data = json.load(f)
            
            transactions = []
            if isinstance(data, list):
                transactions = data
            elif isinstance(data, dict):
                transactions = data.get("transactions", data.get("transfers", []))
            
            for txn in transactions:
                # Detectar se é transferência inter-empresas
                desc = str(txn.get("description", "")).lower()
                cat = str(txn.get("category", "")).lower()
                
                is_intercompany = any(k in desc or cat for k in [
                    "status", "la orana", "la_orana", "intercompany",
                    "transferencia", "transfer", "entre empresa"
                ])
                
                if is_intercompany:
                    # Determinar sentido
                    from_co = self.STATUS if "para la" in desc or "to la" in desc else self.LA_ORANA
                    to_co = self.LA_ORANA if from_co == self.STATUS else self.STATUS
                    
                    transfer = IntercompanyTransaction(
                        id=txn.get("id", str(len(self.transfers))),
                        date=txn.get("date", datetime.now().strftime("%Y-%m-%d")),
                        from_company=from_co,
                        to_company=to_co,
                        amount=float(txn.get("value", 0)),
                        event_id=txn.get("event", "GENERAL"),
                        description=txn.get("description", "Transferência"),
                        status=txn.get("status", "confirmed"),
                        source_doc=filepath
                    )
                    self.transfers.append(transfer)
        
        print(f"✅ {len(self.transfers)} transferências inter-empresas carregadas")
        return self
    
    def calculate_balances(self) -> Dict:
        """
        Calcula saldo entre as empresas.
        """
        # Inicializar
        status_balance = {"receitas": 0, "custos": 0, "transferencias_enviadas": 0, "transferencias_recebidas": 0}
        la_orana_balance = {"receitas": 0, "custos": 0, "transferencias_enviadas": 0, "transferencias_recebidas": 0}
        
        # Eventos alocados
        for alloc in self.events:
            status_balance["receitas"] += alloc.status_revenue
            status_balance["custos"] -= alloc.status_to_la_orana  # débito (deve pagar)
            
            la_orana_balance["receitas"] += alloc.la_orana_revenue_share
            la_orana_balance["custos"] -= alloc.la_orana_execution_cost
        
        # Transferências reais
        for transfer in self.transfers:
            if transfer.from_company == self.STATUS:
                status_balance["transferencias_enviadas"] += transfer.amount
                la_orana_balance["transferencias_recebidas"] += transfer.amount
            else:
                la_orana_balance["transferencias_enviadas"] += transfer.amount
                status_balance["transferencias_recebidas"] += transfer.amount
        
        # Calcular saldo líquido
        status_net = (status_balance["receitas"] + status_balance["transferencias_recebidas"] - 
                      status_balance["custos"] - status_balance["transferencias_enviadas"])
        
        la_orana_net = (la_orana_balance["receitas"] + la_orana_balance["transferencias_recebidas"] - 
                       la_orana_balance["custos"] - la_orana_balance["transferencias_enviadas"])
        
        # Quem deve para quem?
        # Se status_net > 0: STATUS tem saldo positivo
        # Se la_orana_net > 0: LA ORANA tem saldo positivo
        
        if status_net > la_orana_net:
            # STATUS está melhor, LA ORANA pode precisar de dinheiro
            saldo_devedor = self.LA_ORANA
            saldo_credor = self.STATUS
            valor_saldo = abs(status_net - la_orana_net)
        else:
            # LA ORANA está melhor
            saldo_devedor = self.STATUS
            saldo_credor = self.LA_ORANA
            valor_saldo = abs(la_orana_net - status_net)
        
        self.balances = {
            self.STATUS: {
                **status_balance,
                "saldo_liquido": status_net,
                "saldo_nome": "POSITIVO" if status_net >= 0 else "NEGATIVO"
            },
            self.LA_ORANA: {
                **la_orana_balance,
                "saldo_liquido": la_orana_net,
                "saldo_nome": "POSITIVO" if la_orana_net >= 0 else "NEGATIVO"
            },
            "consolidado": {
                "receitas_totais": status_balance["receitas"] + la_orana_balance["receitas"],
                "custos_totais": abs(status_balance["custos"]) + abs(la_orana_balance["custos"]),
                "saldo_sistema": status_net + la_orana_net,
                "empresa_devedora": saldo_devedor,
                "empresa_credora": saldo_credor,
                "valor_a_regularizar": valor_saldo,
                "situacao": "EQUILIBRADO" if valor_saldo < 1000 else "DESBALANCEADO"
            }
        }
        
        return self.balances
    
    def detect_issues(self) -> List[Dict]:
        """
        Detecta problemas no fluxo inter-empresas.
        """
        issues = []
        
        # 1. Transferências sem origem documentada
        status_event_total = sum(e.status_to_la_orana for e in self.events)
        status_transfer_total = sum(t.amount for t in self.transfers if t.from_company == self.STATUS)
        
        if abs(status_transfer_total - status_event_total) > 1000:
            diff = status_transfer_total - status_event_total
            issues.append({
                "type": "TRANSFERENCIA_SEM_ORIGEM",
                "severity": "HIGH" if abs(diff) > 5000 else "MEDIUM",
                "message": f"Transferências STATUS → LA ORANA: R$ {status_transfer_total:,.0f} | Previsto por eventos: R$ {status_event_total:,.0f}",
                "diferenca": diff,
                "detail": f"Diferença de R$ {abs(diff):,.0f} - {'Transferência a mais' if diff > 0 else 'Transferência a menos'}"})
        
        # 2. Uma empresa financiando a outra
        status_saldo = self.balances[self.STATUS]["saldo_liquido"]
        la_orana_saldo = self.balances[self.LA_ORANA]["saldo_liquido"]
        
        if status_saldo > 0 and la_orana_saldo < 0:
            # STATUS positivo financiando LA ORANA negativo
            issues.append({
                "type": "FINANCIAMENTO_CRUZADO",
                "severity": "HIGH",
                "message": f"STATUS financiando LA ORANA",
                "detail": f"STATUS saldo: R$ {status_saldo:,.0f} | LA ORANA saldo: R$ {la_orana_saldo:,.0f}",
                "quem_financia": self.STATUS,
                "quem_recebe": self.LA_ORANA,
                "valor_risco": abs(la_orana_saldo)})
        elif la_orana_saldo > 0 and status_saldo < 0:
            issues.append({
                "type": "FINANCIAMENTO_CRUZADO",
                "severity": "HIGH",
                "message": f"LA ORANA financiando STATUS",
                "detail": f"LA ORANA saldo: R$ {la_orana_saldo:,.0f} | STATUS saldo: R$ {status_saldo:,.0f}",
                "quem_financia": self.LA_ORANA,
                "quem_recebe": self.STATUS,
                "valor_risco": abs(status_saldo)})
        
        # 3. Eventos sem transferência correspondente
        for event in self.events:
            transferencias_evento = sum(t.amount for t in self.transfers 
                                       if t.event_id == event.event_id)
            if transferencias_evento == 0 and event.status_to_la_orana > 0:
                self.pending_transfers.append({
                    "event_id": event.event_id,
                    "from": self.STATUS,
                    "to": self.LA_ORANA,
                    "amount": event.status_to_la_orana,
                    "status": "PENDENTE"
                })
        
        if self.pending_transfers:
            total_pendente = sum(p["amount"] for p in self.pending_transfers)
            issues.append({
                "type": "TRANSFERENCIAS_PENDENTES",
                "severity": "MEDIUM",
                "message": f"{len(self.pending_transfers)} eventos sem transferência",
                "detail": f"Total pendente: R$ {total_pendente:,.0f}",
                "transfers": self.pending_transfers[:5]  # primeiros 5
            })
        
        # 4. Desbalanceamento de caixa
        if self.balances["consolidado"]["situacao"] == "DESBALANCEADO":
            issues.append({
                "type": "CAIXA_DESBALANCEADO",
                "severity": "HIGH",
                "message": f"Sistema desbalanceado - regularização necessária",
                "detail": f"{self.balances['consolidado']['empresa_devedora']} deve R$ {self.balances['consolidado']['valor_a_regularizar']:,.0f} para {self.balances['consolidado']['empresa_credora']}"
            })
        
        return issues
    
    def generate_recommendations(self, issues: List[Dict]) -> List[str]:
        """Gera recomendações baseadas nos issues."""
        recs = []
        
        financiamento = [i for i in issues if i["type"] == "FINANCIAMENTO_CRUZADO"]
        if financiamento:
            f = financiamento[0]
            recs.append(f"🚨 URGENTE: {f['quem_financia']} está financiando {f['quem_recebe']} em R$ {f['valor_risco']:,.0f}. Regularizar transferências imediatamente ou reestruturar modelo.")
        
        pendentes = [i for i in issues if i["type"] == "TRANSFERENCIAS_PENDENTES"]
        if pendentes:
            recs.append(f"⚠️ {pendentes[0]['message']} com total de {pendentes[0]['detail']}. Agendar transferências pendentes.")
        
        desbal = [i for i in issues if i["type"] == "CAIXA_DESBALANCEADO"]
        if desbal:
            recs.append(f"⚠️ Situação: {desbal[0]['detail']}. Necessário regularização contábil entre empresas.")
        
        sem_origem = [i for i in issues if i["type"] == "TRANSFERENCIA_SEM_ORIGEM"]
        if sem_origem:
            recs.append(f"ℹ️ Transferências fora do padrão: {sem_origem[0]['detail']}. Revisar documentação de origem.")
        
        if not recs:
            recs.append("✅ Fluxo inter-empresas organizado. Nenhuma ação necessária.")
        
        return recs
    
    def print_report(self, issues: List[Dict]):
        """Imprime relatório formatado."""
        print("\n" + "=" * 70)
        print("🔄 ORKESTRA INTERCOMPANY CONTROL")
        print("   STATUS (Comercial) ↔ LA ORANA (Operação)")
        print("=" * 70)
        
        # Resumo
        status = self.balances[self.STATUS]
        la_orana = self.balances[self.LA_ORANA]
        cons = self.balances["consolidado"]
        
        print(f"\n📊 RESUMO DAS EMPRESAS")
        print("-" * 70)
        
        print(f"\n🏢 STATUS (Comercial)")
        print(f"   Receitas:          R$ {status['receitas']:>12,.0f}")
        print(f"   Custos/Transfer:   R$ {abs(status['custos']):>12,.0f}")
        print(f"   Saldo Líquido:     R$ {status['saldo_liquido']:>12,.0f} [{status['saldo_nome']}]")
        
        print(f"\n🏢 LA ORANA (Operação)")
        print(f"   Receitas (65%):    R$ {la_orana['receitas']:>12,.0f}")
        print(f"   Custos Execução:   R$ {abs(la_orana['custos']):>12,.0f}")
        print(f"   Saldo Líquido:     R$ {la_orana['saldo_liquido']:>12,.0f} [{la_orana['saldo_nome']}]")
        
        print(f"\n📊 CONSOLIDADO")
        print(f"   Receitas Totais:   R$ {cons['receitas_totais']:>12,.0f}")
        print(f"   Custos Totais:     R$ {cons['custos_totais']:>12,.0f}")
        print(f"   Situação:          {cons['situacao']}")
        
        if cons['situacao'] == "DESBALANCEADO":
            print(f"\n   ⚠️  REGULARIZAÇÃO NECESSÁRIA:")
            print(f"   {cons['empresa_devedora']} deve pagar")
            print(f"   R$ {cons['valor_a_regularizar']:,.0f} para {cons['empresa_credora']}")
        else:
            print(f"\n   ✅ SISTEMA EQUILIBRADO")
        
        # Eventos detalhados
        print("\n" + "-" * 70)
        print("📋 EVENTOS MAIORES (Top 5)")
        print("-" * 70)
        print(f"{'Evento':<20} {'Receita':>12} {'Status→LA':>12} {'Status Saldo':>12} {'LA Saldo':>12}")
        print("-" * 70)
        for e in sorted(self.events, key=lambda x: x.revenue_total, reverse=True)[:5]:
            print(f"{e.event_id[:20]:<20} R$ {e.revenue_total:>10,.0f} R$ {e.status_to_la_orana:>10,.0f} R$ {e.status_net:>10,.0f} R$ {e.la_orana_net:>10,.0f}")
        
        # Alertas
        print("\n" + "-" * 70)
        print("🚨 ALERTAS")
        print("-" * 70)
        if issues:
            for issue in issues:
                icon = "🔴" if issue["severity"] == "HIGH" else "🟡"
                print(f"{icon} [{issue['severity']}] {issue['type']}")
                print(f"   → {issue['message']}")
                print(f"   → {issue['detail']}")
        else:
            print("   ✅ Nenhum alerta")
        
        # Recomendações
        print("\n" + "-" * 70)
        print("💡 RECOMENDAÇÕES")
        print("-" * 70)
        recs = self.generate_recommendations(issues)
        for rec in recs:
            print(f"   {rec}")
        
        # Transferências pendentes
        if self.pending_transfers:
            print("\n" + "-" * 70)
            print("📤 TRANSFERÊNCIAS PENDENTES")
            print("-" * 70)
            for pt in self.pending_transfers[:5]:
                print(f"   {pt['from']} → {pt['to']}: R$ {pt['amount']:,.0f} | Evento: {pt['event_id'][:15]}")
            if len(self.pending_transfers) > 5:
                print(f"   ... e mais {len(self.pending_transfers) - 5} transferências")
        
        print("\n" + "=" * 70)
    
    def generate_summary(self, issues: List[Dict]) -> Dict:
        """Gera resumo final."""
        return {
            "generated_at": datetime.now().isoformat(),
            "companies": {
                "STATUS": self.balances.get(self.STATUS, {}),
                "LA_ORANA": self.balances.get(self.LA_ORANA, {})
            },
            "consolidated": self.balances.get("consolidado", {}),
            "events": [{
                "event_id": e.event_id,
                "revenue": e.revenue_total,
                "status_to_la_orana": e.status_to_la_orana,
                "status_net": e.status_net,
                "la_orana_net": e.la_orana_net
            } for e in self.events],
            "issues": issues,
            "pending_transfers": self.pending_transfers,
            "recommendations": self.generate_recommendations(issues)
        }


def run_intercompany_analysis():
    """
    Executa análise completa de controle inter-empresas.
    """
    print("\n🚀 ORKESTRA INTERCOMPANY CONTROL")
    print("=" * 70)
    print("Organizando fluxo financeiro entre STATUS e LA ORANA")
    print("-" * 70)
    
    control = IntercompanyControl()
    
    # Carregar dados
    print("\n📂 Carregando eventos...")
    control.load_events_from_datasets()
    
    print("\n📂 Carregando transferências...")
    control.load_transfers()
    
    if not control.events:
        print("❌ Nenhum evento para analisar.")
        return {}
    
    # Calcular saldos
    print("\n💰 Calculando saldos...")
    control.calculate_balances()
    
    # Detectar problemas
    print("\n🔍 Detectando problemas...")
    issues = control.detect_issues()
    print(f"   {len(issues)} problemas encontrados")
    
    # Imprimir relatório
    control.print_report(issues)
    
    # Salvar
    summary = control.generate_summary(issues)
    
    output_path = Path("orkestra/memory/intercompany_report.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Relatório salvo: {output_path}")
    print("=" * 70)
    
    return summary


if __name__ == "__main__":
    run_intercompany_analysis()
