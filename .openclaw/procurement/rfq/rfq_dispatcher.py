#!/usr/bin/env python3
"""
RFQ Dispatcher - Sistema de Cotação Automática
Gera e envia pedidos de orçamento aos fornecedores
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random

class RFQDispatcher:
    """Gerador e enviador de RFQs (Requests for Quotation)"""
    
    def __init__(self, base_path: str = ".openclaw/procurement"):
        self.base_path = Path(base_path)
        self.suppliers_path = self.base_path / "suppliers" / "suppliers.json"
        self.rfq_log_path = self.base_path / "rfq" / "rfq_log.json"
        self.rfq_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.load_suppliers()
        
    def load_suppliers(self):
        """Carrega base de fornecedores"""
        if self.suppliers_path.exists():
            with open(self.suppliers_path) as f:
                self.suppliers = json.load(f)
        else:
            self.suppliers = {"suppliers": []}
    
    def create_rfq(self, 
                   event_id: str,
                   required_items: List[Dict],
                   delivery_date: str,
                   notes: str = "") -> Dict:
        """
        Cria um novo RFQ
        
        Args:
            event_id: ID do evento
            required_items: Lista de itens necessários [{sku, quantity, unit}]
            delivery_date: Data de entrega necessária
            notes: Observações adicionais
        """
        rfq_id = f"RFQ-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}"
        
        rfq = {
            "rfq_id": rfq_id,
            "event_id": event_id,
            "created_at": datetime.now().isoformat(),
            "delivery_date": delivery_date,
            "status": "draft",
            "required_items": required_items,
            "notes": notes,
            "suppliers_contacted": [],
            "quotes_received": []
        }
        
        # Identificar fornecedores relevantes
        relevant_suppliers = self._identify_suppliers(required_items)
        rfq["potential_suppliers"] = [s["supplier_id"] for s in relevant_suppliers]
        
        return rfq
    
    def _identify_suppliers(self, items: List[Dict]) -> List[Dict]:
        """Identifica fornecedores que podem atender os itens"""
        relevant = []
        item_skus = [item["sku"] for item in items]
        
        for supplier in self.suppliers.get("suppliers", []):
            supplier_skus = [p["sku"] for p in supplier.get("products", [])]
            if any(sku in supplier_skus for sku in item_skus):
                if supplier["status"] == "homologated":
                    relevant.append(supplier)
        
        # Ordenar por score
        relevant.sort(key=lambda x: x.get("score", {}).get("overall", 0), reverse=True)
        return relevant
    
    def dispatch_rfq(self, rfq: Dict, suppliers: Optional[List[str]] = None) -> Dict:
        """
        Envia RFQ aos fornecedores
        
        Simula envio via WhatsApp/Telegram
        """
        rfq["status"] = "sent"
        rfq["sent_at"] = datetime.now().isoformat()
        
        target_suppliers = suppliers or rfq.get("potential_suppliers", [])
        
        dispatched = []
        for supplier_id in target_suppliers:
            supplier = self._get_supplier(supplier_id)
            if supplier:
                # Simular envio
                dispatch_record = {
                    "supplier_id": supplier_id,
                    "method": "whatsapp",
                    "contact": supplier["contact"]["whatsapp"],
                    "sent_at": datetime.now().isoformat(),
                    "status": "pending_response",
                    "expected_response_hours": 24
                }
                dispatched.append(dispatch_record)
                
                # Log de mensagem simulada
                message = self._generate_whatsapp_message(rfq, supplier)
                dispatch_record["message_preview"] = message[:100] + "..."
        
        rfq["suppliers_contacted"] = dispatched
        rfq["response_deadline"] = (datetime.now() + timedelta(hours=48)).isoformat()
        
        return rfq
    
    def _get_supplier(self, supplier_id: str) -> Optional[Dict]:
        """Busca fornecedor por ID"""
        for s in self.suppliers.get("suppliers", []):
            if s["supplier_id"] == supplier_id:
                return s
        return None
    
    def _generate_whatsapp_message(self, rfq: Dict, supplier: Dict) -> str:
        """Gera mensagem de WhatsApp para o fornecedor"""
        items_text = "\n".join([
            f"• {item['sku']}: {item['quantity']} {item['unit']}"
            for item in rfq["required_items"]
        ])
        
        message = f"""*ORÇAMENTO URGENTE - STATUS/LA ORANA*

Olá {supplier['contact']['responsible']},

Solicitamos orçamento para evento *{rfq['event_id']}*:

*ITENS NECESSÁRIOS:*
{items_text}

*ENTREGA:* {rfq['delivery_date']}
*RESPOSTA ESPERADA:* 24h

Por favor enviar:
- Preço unitário
- Preço total
- Prazo de entrega
- Condição de pagamento
- Validade da proposta

Agradecemos!
"""
        return message
    
    def log_rfq(self, rfq: Dict):
        """Registra RFQ no log"""
        log_entry = {
            "rfq_id": rfq["rfq_id"],
            "event_id": rfq["event_id"],
            "created_at": rfq["created_at"],
            "status": rfq["status"],
            "items_count": len(rfq["required_items"]),
            "suppliers_contacted": len(rfq["suppliers_contacted"]),
            "response_deadline": rfq.get("response_deadline")
        }
        
        # Carregar log existente
        log = []
        if self.rfq_log_path.exists():
            with open(self.rfq_log_path) as f:
                log = json.load(f)
        
        log.append(log_entry)
        
        with open(self.rfq_log_path, "w") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
    
    def check_response_status(self, rfq_id: str) -> Dict:
        """Verifica status das respostas"""
        # Simular verificação
        return {
            "rfq_id": rfq_id,
            "total_contacted": 3,
            "responded": 2,
            "pending": 1,
            "overdue": 0,
            "can_proceed": True
        }
    
    def generate_event_rfq(self, event_data: Dict) -> Dict:
        """
        Gera RFQ completo baseado em dados de evento
        
        Args:
            event_data: Dados do evento com forecast de consumo
        """
        # Extrair necessidades do evento
        items = []
        
        if event_data.get("has_bar"):
            items.extend([
                {"sku": "BEB-001", "quantity": event_data.get("guests", 100) * 0.5, "unit": "caixa"},
                {"sku": "GEL-001", "quantity": event_data.get("guests", 100) * 0.2, "unit": "saco"}
            ])
        
        if event_data.get("has_buffet"):
            items.extend([
                {"sku": "BUF-001", "quantity": event_data.get("guests", 100) * 0.15, "unit": "kg"},
                {"sku": "BUF-003", "quantity": event_data.get("guests", 100) * 0.1, "unit": "kg"}
            ])
        
        if event_data.get("needs_staff"):
            items.extend([
                {"sku": "STF-001", "quantity": event_data.get("duration_hours", 4), "unit": "hora"},
                {"sku": "STF-002", "quantity": event_data.get("guests", 100) / 20 * event_data.get("duration_hours", 4), "unit": "hora"}
            ])
        
        rfq = self.create_rfq(
            event_id=event_data.get("event_id", "EVT-UNKNOWN"),
            required_items=items,
            delivery_date=event_data.get("event_date", (datetime.now() + timedelta(days=7)).isoformat()),
            notes=event_data.get("notes", "")
        )
        
        return rfq


# Demo/Teste
if __name__ == "__main__":
    dispatcher = RFQDispatcher()
    
    # Exemplo de evento
    event = {
        "event_id": "EV-2025-04-15-001",
        "event_date": "2025-04-15T18:00:00",
        "guests": 150,
        "duration_hours": 6,
        "has_bar": True,
        "has_buffet": True,
        "needs_staff": True,
        "notes": "Casamento - área externa"
    }
    
    rfq = dispatcher.generate_event_rfq(event)
    rfq_dispatched = dispatcher.dispatch_rfq(rfq)
    dispatcher.log_rfq(rfq_dispatched)
    
    print("RFQ Gerado:")
    print(json.dumps(rfq_dispatched, indent=2, ensure_ascii=False))
