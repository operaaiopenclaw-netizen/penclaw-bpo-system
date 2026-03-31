#!/usr/bin/env python3
"""
OpenClaw BPO - Procurement Orchestrator
Motor unificado de gerenciamento de compras
Conecta demanda → fornecedores → decisão → ordem
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os

class Urgency(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Status(Enum):
    PENDING = "pending"
    HOMOLOGATED = "homologated"
    BLOCKED = "blocked"

@dataclass
class ProductDemand:
    sku: str
    name: str
    category: str
    quantity: float
    unit: str
    urgency: Urgency
    event_ids: List[str]
    delivery_date: str

@dataclass
class EligibleSupplier:
    supplier_id: str
    name: str
    category: str
    score: float
    status: str
    delivery_days: int
    payment_terms: str
    last_price: Optional[float]
    reliability: float

@dataclass
class QuoteComparison:
    supplier_id: str
    supplier_name: str
    unit_price: float
    total_price: float
    delivery_hours: int
    payment_terms: str
    quality_score: float
    overall_score: float

@dataclass
class PurchaseDecision:
    product_sku: str
    product_name: str
    recommended_supplier: str
    unit_price: float
    total_price: float
    quantity: float
    unit: str
    justification: str
    risk_level: str
    savings: float
    urgency: str
    status: str

class ProcurementOrchestrator:
    """
    Orquestrador completo de processo de compras
    """
    
    def __init__(self, base_path: str = ".openclaw/procurement"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Arquivos de entrada
        self.suppliers_file = self.base_path / "suppliers.json"
        self.demand_file = self.base_path / "procurement_demand.json"
        self.cash_file = self.base_path.parent / "cash_position.json"
        self.quotes_file = self.base_path / "quotes.json"
        
        # Arquivos de saída
        self.eligible_file = self.base_path / "eligible_suppliers.json"
        self.rfq_batch_file = self.base_path / "rfq_dispatch_batch.json"
        self.comparison_file = self.base_path / "quote_comparison.json"
        self.decision_file = self.base_path / "procurement_decision.json"
        self.po_file = self.base_path / "purchase_orders_suggested.json"
        self.cash_impact_file = self.base_path / "procurement_cash_impact.json"
        self.history_file = self.base_path / "procurement_history.json"
        self.executive_file = self.base_path / "PROCUREMENT_EXECUTIVE_REPORT.json"
        
        self.data = {}
        
    def load_all(self) -> bool:
        """Carrega todos os dados de entrada"""
        print("[ORCHESTRATOR] Carregando dados...")
        
        required = ["suppliers", "procurement_demand", "cash_position", "quotes"]
        
        for key in required:
            file_path = getattr(self, f"{key}_file")
            if file_path.exists():
                with open(file_path) as f:
                    self.data[key] = json.load(f)
                print(f"  ✅ {key}")
            else:
                print(f"  ⚠️  {key} não encontrado")
                self.data[key] = {}
        
        return len(self.data) > 0
    
    def step_1_eligibility(self) -> Dict:
        """
        Etapa 1: Determina fornecedores elegíveis por produto
        """
        print("\n[1/9] ELIGIBILIDADE DE FORNECEDORES")
        
        if "procurement_demand" not in self.data:
            print("  ❌ Sem demanda para processar")
            return {}
        
        demand = self.data["procurement_demand"].get("demand_by_category", {})
        suppliers = self.data.get("suppliers", {}).get("suppliers", [])
        
        eligibility = {
            "generated_at": datetime.now().isoformat(),
            "products": []
        }
        
        for category, data in demand.items():
            products = data.get("products", [])
            
            for product in products:
                sku = product.get("sku")
                
                # Encontrar fornecedores por categoria
                eligible = []
                for sup in suppliers:
                    sup_categories = sup.get("categories", [])
                    if category in sup_categories or any(c in sup_categories for c in data.get("category_products", [])):
                        score = sup.get("score", {})
                        perf = sup.get("performance", {})
                        
                        supplier_data = {
                            "supplier_id": sup.get("supplier_id"),
                            "name": sup.get("name"),
                            "category": category,
                            "score": score.get("overall", 0),
                            "status": sup.get("status"),
                            "delivery_time_days": sup.get("delivery", {}).get("time_hours", 48) / 24,
                            "payment_terms": sup.get("delivery", {}).get("payment_terms", "30 dias"),
                            "last_price_reference": None,  # Buscar histórico
                            "reliability": perf.get("on_time_rate", 0)
                        }
                        
                        # Priorizar homologados
                        if sup.get("status") == "homologated":
                            supplier_data["priority"] = 1
                        elif sup.get("status") == "pending":
                            supplier_data["priority"] = 2
                        else:
                            supplier_data["priority"] = 3
                        
                        eligible.append(supplier_data)
                
                # Ordenar por prioridade e score
                eligible.sort(key=lambda x: (x["priority"], -x["score"]))
                
                eligibility["products"].append({
                    "product_sku": sku,
                    "product_name": product.get("name"),
                    "category": category,
                    "quantity": product.get("quantity"),
                    "unit": product.get("unit"),
                    "urgency": product.get("urgency"),
                    "eligible_suppliers_count": len(eligible),
                    "eligible_suppliers": eligible[:5]  # Top 5
                })
        
        with open(self.eligible_file, 'w') as f:
            json.dump(eligibility, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ {len(eligibility['products'])} produtos analisados")
        return eligibility
    
    def step_2_rfq_pipeline(self, eligibility: Dict) -> Dict:
        """
        Etapa 2: Cria lotes de RFQ consolidados por fornecedor
        """
        print("\n[2/9] RFQ PIPELINE")
        
        rfq_batch = {
            "generated_at": datetime.now().isoformat(),
            "batches": []
        }
        
        # Agrupar por fornecedor
        supplier_products = {}
        
        for product in eligibility.get("products", []):
            for supplier in product.get("eligible_suppliers", []):
                sup_id = supplier["supplier_id"]
                
                if sup_id not in supplier_products:
                    supplier_products[sup_id] = {
                        "supplier_id": sup_id,
                        "supplier_name": supplier["name"],
                        "category": supplier["category"],
                        "contact": supplier.get("whatsapp", ""),
                        "products": []
                    }
                
                supplier_products[sup_id]["products"].append({
                    "sku": product["product_sku"],
                    "name": product["product_name"],
                    "quantity": product["quantity"],
                    "unit": product["unit"],
                    "urgency": product["urgency"]
                })
        
        # Criar lotes
        for sup_id, batch in supplier_products.items():
            # Gerar mensagem de RFQ
            items_text = "\n".join([
                f"• {p['name']}: {p['quantity']} {p['unit']}"
                for p in batch["products"]
            ])
            
            urgency_text = "COTAÇÃO URGENTE" if any(
                p["urgency"] == "critical" for p in batch["products"]
            ) else "Solicitação de Orçamento"
            
            message = f"""*{urgency_text} - STATUS/LA ORANA*

Olá,

Solicitamos orçamento para:

{items_text}

*INFORMAÇÕES NECESSÁRIAS:*
• Valor unitário de cada item
• Valor total do pedido
• Prazo de entrega
• Condição de pagamento
• Validade da proposta

Aguardo retorno em até 48h.

Obrigado!"""
            
            rfq_batch["batches"].append({
                "batch_id": f"RFQ-BATCH-{sup_id}",
                "supplier_id": sup_id,
                "supplier_name": batch["supplier_name"],
                "products": batch["products"],
                "message": message,
                "method": "whatsapp",
                "status": "ready_to_send"
            })
        
        with open(self.rfq_batch_file, 'w') as f:
            json.dump(rfq_batch, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ {len(rfq_batch['batches'])} lotes RFQ criados")
        return rfq_batch
    
    def step_3_quote_consolidation(self) -> Dict:
        """
        Etapa 3: Consolida e compara cotações recebidas
        """
        print("\n[3/9] CONSOLIDAÇÃO DE COTAÇÕES")
        
        quotes = self.data.get("quotes", {}).get("parsed_quotes", [])
        
        comparison = {
            "generated_at": datetime.now().isoformat(),
            "grouped_by_product": {},
            "summary": {}
        }
        
        for quote in quotes:
            items = quote.get("extracted_data", {}).get("items", [])
            
            for item in items:
                sku = item.get("sku")
                
                if sku not in comparison["grouped_by_product"]:
                    comparison["grouped_by_product"][sku] = {
                        "product": item.get("product"),
                        "sku": sku,
                        "quotes": []
                    }
                
                quote_data = {
                    "quote_id": quote.get("quote_id"),
                    "supplier_id": quote.get("supplier", {}).get("id"),
                    "supplier_name": quote.get("supplier", {}).get("name"),
                    "unit_price": item.get("unit_price"),
                    "total_price": item.get("total_price"),
                    "delivery_hours": quote.get("extracted_data", {}).get("delivery", {}).get("time_hours"),
                    "payment_terms": quote.get("extracted_data", {}).get("payment", {}).get("primary"),
                    "confidence": quote.get("confidence_score")
                }
                
                comparison["grouped_by_product"][sku]["quotes"].append(quote_data)
        
        # Adicionar recomendações
        for sku, data in comparison["grouped_by_product"].items():
            quotes = data["quotes"]
            
            if quotes:
                # Melhor preço
                best_price = min(quotes, key=lambda x: x["unit_price"])
                data["best_price"] = best_price
                
                # Melhor entrega
                best_delivery = min(quotes, key=lambda x: x.get("delivery_hours", 999))
                data["best_delivery"] = best_delivery
                
                # Recomendado (score ponderado)
                scores = []
                for q in quotes:
                    price_score = 10 - (q["unit_price"] / best_price["unit_price"] - 1) * 10
                    delivery_bonus = 1 if q.get("delivery_hours", 48) <= 48 else 0
                    confidence = q.get("confidence", 0.5) * 10
                    score = price_score * 0.5 + delivery_bonus * 3 + confidence * 0.5
                    scores.append((q, score))
                
                scores.sort(key=lambda x: x[1], reverse=True)
                data["recommended"] = scores[0][0] if scores else None
        
        with open(self.comparison_file, 'w') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ {len(comparison['grouped_by_product'])} produtos comparados")
        return comparison
    
    def step_4_make_decision(self, comparison: Dict) -> Dict:
        """
        Etapa 4: Toma decisão de compra
        """
        print("\n[4/9] DECISÃO DE COMPRA")
        
        decisions = {
            "generated_at": datetime.now().isoformat(),
            "decisions": []
        }
        
        for sku, data in comparison.get("grouped_by_product", {}).items():
            rec = data.get("recommended")
            
            if rec:
                # Análise de risco
                supplier_data = next(
                    (s for s in self.data.get("suppliers", {}).get("suppliers", [])
                    if s.get("supplier_id") == rec["supplier_id"]
                , {})
                
                reliability = supplier_data.get("performance", {}).get("on_time_rate", 0.85)
                
                if reliability > 0.95:
                    risk = "low"
                elif reliability > 0.90:
                    risk = "medium"
                else:
                    risk = "high"
                
                # Justificação
                reason = f"Fornecedor {rec['supplier_name']} selecionado. "
                if rec == data.get("best_price"):
                    reason += f"Melhor preço identificado: R$ {rec['unit_price']:.2f}"
                
                decision = {
                    "product_sku": sku,
                    "product_name": data["product"],
                    "recommended_supplier": rec["supplier_name"],
                    "supplier_id": rec["supplier_id"],
                    "unit_price": rec["unit_price"],
                    "total_price": rec["total_price"],
                    "justification": reason,
                    "risk_level": risk,
                    "status": "APPROVED" if risk != "high" else "REVIEW_NEEDED"
                }
                
                decisions["decisions"].append(decision)
        
        with open(self.decision_file, 'w') as f:
            json.dump(decisions, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ {len(decisions['decisions'])} decisões geradas")
        return decisions
    
    def step_5_generate_po(self, decisions: Dict) -> Dict:
        """
        Etapa 5: Gera ordens de compra sugeridas
        """
        print("\n[5/9] ORDENS DE COMPRA")
        
        pos = {
            "generated_at": datetime.now().isoformat(),
            "orders": []
        }
        
        # Agrupar por fornecedor
        by_supplier = {}
        for dec in decisions.get("decisions", []):
            sup_id = dec.get("supplier_id")
            
            if sup_id not in by_supplier:
                by_supplier[sup_id] = {
                    "supplier_id": sup_id,
                    "supplier_name": dec.get("recommended_supplier"),
                    "items": [],
                    "total": 0
                }
            
            by_supplier[sup_id]["items"].append({
                "product_sku": dec["product_sku"],
                "product_name": dec["product_name"],
                "unit_price": dec["unit_price"],
                "total_price": dec["total_price"]
            })
            by_supplier[sup_id]["total"] += dec["total_price"]
        
        for sup_id, order in by_supplier.items():
            pos["orders"].append(order)
        
        with open(self.po_file, 'w') as f:
            json.dump(pos, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ {len(pos['orders'])} ordens geradas")
        return pos
    
    def step_6_cash_impact(self, pos: Dict) -> Dict:
        """
        Etapa 6: Avalia impacto no caixa
        """
        print("\n[6/9] IMPACTO NO CAIXA")
        
        cash = self.data.get("cash_position", {})
        available = cash.get("companies", {}).get("LA ORANA", {}).get("current_balance", 0)
        
        impact = {
            "generated_at": datetime.now().isoformat(),
            "la_orana_available": available,
            "orders": []
        }
        
        total_spending = 0
        for order in pos.get("orders", []):
            total = order.get("total", 0)
            total_spending += total
            
            status = "safe_to_buy" if total < available * 0.1 else \
                     "needs_attention" if total < available * 0.3 else "cash_risk"
            
            impact["orders"].append({
                "supplier": order["supplier_name"],
                "total": total,
                "percent_of_available": (total / available * 100) if available else 0,
                "status": status
            })
        
        impact["total_spending"] = total_spending
        impact["remaining_after_purchase"] = available - total_spending
        impact["overall_status"] = "HEALTHY" if total_spending < available * 0.5 else "ATTENTION"
        
        with open(self.cash_impact_file, 'w') as f:
            json.dump(impact, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Impacto calculado: R$ {total_spending:,.2f}")
        return impact
    
    def step_7_update_memory(self, decisions: Dict, pos: Dict):
        """
        Etapa 7: Atualiza histórico de compras
        """
        print("\n[7/9] MEMÓRIA E APRENDIZADO")
        
        history = {
            "updated_at": datetime.now().isoformat(),
            "purchases": []
        }
        
        for dec in decisions.get("decisions", []):
            history["purchases"].append({
                "timestamp": datetime.now().isoformat(),
                "product_sku": dec["product_sku"],
                "product_name": dec["product_name"],
                "supplier": dec["recommended_supplier"],
                "unit_price": dec["unit_price"],
                "total_price": dec["total_price"],
                "savings_estimated": dec.get("savings", 0),
                "decision": dec["status"]
            })
        
        # Append to existing history
        existing = []
        if self.history_file.exists():
            with open(self.history_file) as f:
                existing = json.load(f).get("purchases", [])
        
        history["purchases"] = existing + history["purchases"]
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Histórico atualizado ({len(history['purchases'])} registros)")
    
    def generate_executive_report(self, eligibility: Dict, pos: Dict, impact: Dict):
        """
        Gera relatório executivo final
        """
        print("\n[8/9] RELATÓRIO EXECUTIVO")
        
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "system": "OpenClaw BPO Procurement",
                "version": "1.0"
            },
            "executive_summary": {
                "demand_consolidated": len(eligibility.get("products", [])),
                "eligible_suppliers": len(eligibility.get("products", [])),
                "purchase_orders": len(pos.get("orders", [])),
                "total_value": sum(o.get("total", 0) for o in pos.get("orders", [])),
                "cash_impact": impact.get("overall_status"),
                "next_actions": [
                    "1. Revisar ordens de compra sugeridas",
                    "2. Negociar condições com fornecedores",
                    "3. Confirmar disponibilidade de caixa",
                    "4. Executar compras aprovadas"
                ]
            },
            "deliverables": [
                "eligible_suppliers.json - Fornecedores por produto",
                "rfq_dispatch_batch.json - Lotes de cotação",
                "quote_comparison.json - Comparação de preços",
                "procurement_decision.json - Decisões de compra",
                "purchase_orders_suggested.json - Ordens sugeridas",
                "procurement_cash_impact.json - Impacto financeiro",
                "procurement_history.json - Histórico de compras"
            ]
        }
        
        with open(self.executive_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Report gerado: {self.executive_file}")
    
    def run_full_pipeline(self):
        """
        Executa pipeline completo
        """
        print("=" * 60)
        print("🤖 PROCUREMENT ORCHESTRATOR - BPO-SYSTEM")
        print("=" * 60)
        
        # Load
        if not self.load_all():
            print("❌ Falha ao carregar dados")
            return False
        
        # Execute steps
        eligibility = self.step_1_eligibility()
        
        # Check if we have quotes or need RFQ
        if self.quotes_file.exists() and self.quotes_file.stat().st_size > 100:
            print("\n  📊 Cotações recebidas - pulando RFQ step")
            rfq_batch = {}
        else:
            rfq_batch = self.step_2_rfq_pipeline(eligibility)
        
        if self.quotes_file.exists():
            comparison = self.step_3_quote_consolidation()
        else:
            print("\n  ⏳ Aguardando cotações dos fornecedores")
            comparison = {}
        
        if comparison:
            decisions = self.step_4_make_decision(comparison)
        else:
            decisions = {}
        
        if decisions:
            pos = self.step_5_generate_po(decisions)
            impact = self.step_6_cash_impact(pos)
            self.step_7_update_memory(decisions, pos)
        else:
            pos = {"orders": []}
            impact = {"overall_status": "PENDING_QUOTES"}
        
        # Generate report
        self.generate_executive_report(eligibility, pos, impact)
        
        print("\n" + "=" * 60)
        print("✅ ORQUESTRAÇÃO CONCLUÍDA")
        print("=" * 60)
        print(f"\nArquivos gerados em: {self.base_path}")
        print("-" * 60)
        
        return True


if __name__ == "__main__":
    orchestrator = ProcurementOrchestrator()
    orchestrator.run_full_pipeline()
