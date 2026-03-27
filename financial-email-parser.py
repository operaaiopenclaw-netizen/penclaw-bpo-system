#!/usr/bin/env python3
"""
Financial Email Parser - Orkestra Finance Brain Integration

Extracts structured financial data from emails for event-based financial tracking.

Usage:
    python3 financial-email-parser.py < email.txt
    python3 financial-email-parser.py --input email.txt
"""

import re
import json
import sys
from datetime import datetime


def normalize_amount(amount_str):
    """Convert various amount formats to float."""
    # Remove currency symbols and spaces
    amount_str = re.sub(r'[R$\$\s]', '', amount_str)
    
    # Handle Brazilian format (1.234,56)
    if ',' in amount_str and '.' in amount_str:
        amount_str = amount_str.replace('.', '').replace(',', '.')
    elif ',' in amount_str:
        # Check if comma is decimal separator
        parts = amount_str.split(',')
        if len(parts[-1]) == 2:  # Likely Brazilian: 1250,00
            amount_str = amount_str.replace(',', '.')
        else:  # Likely thousands: 1,234
            amount_str = amount_str.replace(',', '')
    
    try:
        return float(amount_str)
    except:
        return None


def extract_amount(text):
    """Extract monetary value from email."""
    # Brazilian format patterns
    patterns = [
        r'R\$\s*([\d.,]+\d{2})',
        r'(?:valor|montante|amount)\s*:?\s*R?\$?\s*([\d.,]+)',
        r'\b(\d+[.,]\d{2})\s*(?:reais?|BRL)',
        r'(?:pago|pagamento|recebido)\s*:?\s*R?\$?\s*([\d.,]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = normalize_amount(match.group(1))
            if amount and amount > 0:
                return amount
    return None


def extract_date(text):
    """Extract date in ISO format."""
    # Brazilian formats
    patterns = [
        (r'\b(\d{2})[/-](\d{2})[/-](\d{4})\b', lambda m: f"{m.group(3)}-{m.group(2)}-{m.group(1)}"),
        (r'\b(\d{4})[/-](\d{2})[/-](\d{2})\b', lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),
    ]
    
    for pattern, formatter in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                date_str = formatter(match)
                datetime.strptime(date_str, '%Y-%m-%d')
                return date_str
            except:
                continue
    
    # If no date found, use today
    return datetime.now().strftime('%Y-%m-%d')


def detect_transaction_type(text):
    """Determine if income or expense."""
    text_lower = text.lower()
    
    # Expense indicators
    expense_keywords = [
        'pago', 'pagamento', 'debitado', 'saída', 'débito', 'compra',
        'paguei', 'paguemos', 'efetuado', 'debit',
        'charged', 'paid to', 'sent to', 'transfer to'
    ]
    
    # Income indicators  
    income_keywords = [
        'recebido', 'recebimento', 'creditado', 'entrada', 'crédito',
        'depositado', 'transferido para você', 'deposit',
        'received', 'credited', 'transfer from'
    ]
    
    for kw in expense_keywords:
        if kw in text_lower:
            return 'expense'
    
    for kw in income_keywords:
        if kw in text_lower:
            return 'income'
    
    # Default based on context
    if 'comprovante' in text_lower or 'recibo' in text_lower:
        return 'expense'
    
    return 'expense'  # Conservative default


def detect_document_type(text):
    """Detect financial document type."""
    text_lower = text.lower()
    
    if 'pix' in text_lower:
        return 'pix'
    elif any(x in text_lower for x in ['boleto', 'boleto']):
        return 'boleto'
    elif 'nfe' in text_lower or 'nota fiscal' in text_lower:
        return 'invoice'
    elif 'cartão' in text_lower or 'card' in text_lower:
        return 'card'
    elif 'fatura' in text_lower or 'bill' in text_lower:
        return 'invoice'
    elif 'comprovante' in text_lower or 'receipt' in text_lower:
        return 'receipt'
    elif any(x in text_lower for x in ['transferência', 'transfer', 'ted', 'doc']):
        return 'transfer'
    else:
        return 'payment'


def extract_source(text):
    """Extract who sent/paid."""
    text_lower = text.lower()
    
    # Patterns for Brazilian Portuguese
    patterns = [
        r'(?:de|from)\s*:?\s*([A-Z][A-Za-z\s]+(?:Ltda|ME|SA)?)',
        r'(?:para|to)\s*:?\s*([A-Z][A-Za-z\s]+(?:Ltda|ME|SA)?)',
        r'(?:pagador|payer)\s*:?\s*([A-Z][A-Za-z\s]+)',
        r'(?:recebedor|recebedora|payee)\s*:?\s*([A-Z][A-Za-z\s]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            source = match.group(1).strip()
            # Clean up
            source = re.sub(r'\s+', ' ', source)
            return source if len(source) > 2 else None
    
    return None


def extract_payment_method(text):
    """Extract payment method."""
    text_lower = text.lower()
    
    methods = [
        ('pix', 'PIX'),
        ('boleto', 'boleto'),
        ('cartão de crédito', 'card_credit'),
        ('cartão de débito', 'card_debit'),
        ('ted', 'TED'),
        ('doc', 'DOC'),
        ('dinheiro', 'cash'),
        ('transferência', 'transfer'),
    ]
    
    for keyword, method in methods:
        if keyword in text_lower:
            return method
    
    return None


def detect_category(text, doc_type):
    """Auto-classify category."""
    text_lower = text.lower()
    
    # Food/protein
    if any(x in text_lower for x in ['carne', 'frango', 'açougue', 'supermercado', 'mercado']):
        return 'proteina'
    
    # Drinks
    if any(x in text_lower for x in ['cerveja', 'bebida', 'refrigerante', 'vinho', 'água']):
        return 'bebida'
    
    # Staff
    if any(x in text_lower for x in ['garçom', 'bartender', 'segurança', 'motorista', 'equipe']):
        return 'staff'
    
    # Ambientação
    if any(x in text_lower for x in ['vela', 'flor', 'decor', 'arranjo', 'iluminação']):
        return 'ambientacao'
    
    # Materials
    if any(x in text_lower for x in ['copo', 'prato', 'talher', 'louça', 'material']):
        return 'material'
    
    # Infrastructure
    if any(x in text_lower for x in ['mesa', 'cadeira', 'tenda', 'palco', 'som']):
        return 'infraestrutura'
    
    # Service fees
    if 'taxa' in text_lower or 'tarifa' in text_lower:
        return 'taxas'
    
    return 'outros'


def extract_event(text):
    """Extract event name from text using multiple patterns."""
    import re
    
    patterns = [
        r"(medicina|direito|odontologia|engenharia|administracao|economia|psicologia|arquitetura|nutricao)\s*(\d{1,2}/\d{1,2})",
        r"evento:\s*([^\n\r]+)",
        r"para\s+(medicina|direito|odontologia|engenharia)\s+(\d{1,2}/\d{1,2})"
    ]

    for p in patterns:
        match = re.search(p, text.lower())
        if match:
            if len(match.groups()) == 2:
                return f"{match.group(1).title()}_{match.group(2)}"
            return match.group(1).strip()

    return None


def is_financial_email(text):
    """Check if email contains financial content."""
    text_lower = text.lower()
    
    financial_keywords = [
        'pagamento', 'recebimento', 'comprovante', 'pix', 'transferência',
        'boleto', 'fatura', 'nota fiscal', 'nfe', 'cartão',
        'débito', 'crédito', 'receipt', 'invoice', 'payment',
        'paid', 'received', 'charged', 'amount', 'valor'
    ]
    
    keyword_count = sum(1 for kw in financial_keywords if kw in text_lower)
    return keyword_count >= 2


def enrich_data(data):
    """Enrich transaction data with macro centers and impact mapping."""
    category_map = {
        "bebida": {
            "macro_center": "catering",
            "impact": "CMV"
        },
        "proteina": {
            "macro_center": "catering",
            "impact": "CMV"
        },
        "staff": {
            "macro_center": "operacao",
            "impact": "custo_fixo_variavel"
        },
        "ambientacao": {
            "macro_center": "decoracao",
            "impact": "custo_evento"
        },
        "material": {
            "macro_center": "operacao",
            "impact": "custo_evento"
        },
        "infraestrutura": {
            "macro_center": "operacao",
            "impact": "custo_evento"
        },
        "taxas": {
            "macro_center": "administrativo",
            "impact": "custo_fixo"
        }
    }
    
    category = data.get("category")
    if category and category in category_map:
        data.update(category_map[category])
    
    return data


def detect_risk(data):
    """Detect financial risks and alerts."""
    value = data.get("value", 0) or 0  # Handle None
    impact = data.get("impact", "")
    category = data.get("category", "")
    
    alerts = []
    
    # Alerta: Item de alto custo no CMV
    if impact == "CMV" and value > 3000:
        alerts.append({
            "type": "high_cost_item",
            "severity": "warning",
            "message": f"Item de alto custo no CMV: R$ {value:.2f}",
            "threshold": 3000
        })
    
    # Alerta: Staff muito caro
    if category == "staff" and value > 5000:
        alerts.append({
            "type": "high_staff_cost",
            "severity": "warning", 
            "message": f"Custo de staff elevado: R$ {value:.2f}",
            "threshold": 5000
        })
    
    # Alerta: Taxa de serviço alta
    if category == "taxas" and value > 1000:
        alerts.append({
            "type": "high_fee",
            "severity": "info",
            "message": f"Taxa elevada: R$ {value:.2f}",
            "threshold": 1000
        })
    
    # Alerta: Despesa sem evento vinculado
    if data.get("type") == "expense" and value > 500 and not data.get("event"):
        alerts.append({
            "type": "missing_event",
            "severity": "attention",
            "message": f"Despesa de R$ {value:.2f} sem evento identificado",
            "threshold": 500
        })
    
    if alerts:
        data["alerts"] = alerts
        data["has_alerts"] = True
    else:
        data["has_alerts"] = False
    
    return data


def parse_financial_email(text):
    """Main parser function."""
    # Check relevance
    if not is_financial_email(text):
        return {"relevant": False}
    
    # Extract data
    result = {
        "relevant": True,
        "type": detect_transaction_type(text),
        "document_type": detect_document_type(text),
        "value": extract_amount(text),
        "date": extract_date(text),
        "source": extract_source(text),
        "category": detect_category(text, detect_document_type(text)),
        "payment_method": extract_payment_method(text),
        "event": extract_event(text)
    }
    
    # Enrich with macro centers and impact
    result = enrich_data(result)
    
    # Detect risks and alerts
    result = detect_risk(result)
    
    # Generate insights based on alerts
    result = generate_insight(result)
    
    # Remove null values for cleaner output (except alerts which can be empty list)
    result = {k: v for k, v in result.items() if v is not None}
    
    return result


def generate_insight(data):
    """Generate actionable insights based on alerts and patterns."""
    alerts = data.get("alerts", [])
    insights = []
    
    for alert in alerts:
        alert_type = alert.get("type", "")
        
        if alert_type == "high_cost_item":
            insights.append({
                "type": "validation_needed",
                "priority": "high",
                "message": "Custo elevado detectado no CMV. Validar necessidade da compra e verificar se há alternativas de fornecedor."
            })
        
        elif alert_type == "high_staff_cost":
            insights.append({
                "type": "optimization",
                "priority": "medium",
                "message": "Custo com equipe elevado. Verificar se escala está adequada ao tamanho do evento."
            })
        
        elif alert_type == "high_fee":
            insights.append({
                "type": "review",
                "priority": "low",
                "message": "Taxa de serviço significativa. Confirmar se foi negociada previamente."
            })
        
        elif alert_type == "missing_event":
            value = data.get("value", 0)
            insights.append({
                "type": "action_required",
                "priority": "high",
                "message": f"Despesa de R$ {value:.2f} sem evento vinculado. Necessário mapear para evento correto no Orkestra."
            })
    
    # Insights adicionais baseados em padrões
    if data.get("category") == "proteina" and data.get("value", 0) > 2000:
        insights.append({
            "type": "cost_optimization",
            "priority": "medium",
            "message": "Compra de proteína significativa. Confirmar quantidade de convidados e cardápio aprovado."
        })
    
    if data.get("category") == "bebida" and data.get("value", 0) > 3000:
        insights.append({
            "type": "cost_optimization",
            "priority": "medium",
            "message": "Investimento em bebidas elevado. Verificar mix de bebidas e possibilidade de substituições."
        })
    
    if insights:
        data["insights"] = insights
        data["has_insights"] = True
    else:
        data["has_insights"] = False
    
    return data


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse financial emails for Orkestra')
    parser.add_argument('--input', '-i', help='Input file')
    args = parser.parse_args()
    
    # Read input
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                text = f.read()
        except:
            print(json.dumps({"relevant": False}), file=sys.stderr)
            sys.exit(1)
    else:
        text = sys.stdin.read()
    
    # Parse and output
    result = parse_financial_email(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
