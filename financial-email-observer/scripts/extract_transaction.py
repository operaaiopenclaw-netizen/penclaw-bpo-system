#!/usr/bin/env python3
"""
Financial Email Transaction Extractor

Parses unstructured email text to extract financial transaction data.
Converts payment confirmations, invoices, and receipts into structured JSON.

Usage:
    from extract_transaction import parse_email
    
    result = parse_email(email_content)
    print(result)

Or run as CLI:
    python extract_transaction.py < email.txt
    python extract_transaction.py --input email.txt --output result.json
"""

import re
import json
import sys
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class Transaction:
    transaction_type: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "BRL"
    amount_formatted: Optional[str] = None
    date: Optional[str] = None
    counterparty: Optional[str] = None
    description: Optional[str] = None
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    account_last4: Optional[str] = None
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_type": self.transaction_type,
            "amount": self.amount,
            "currency": self.currency,
            "amount_formatted": self.amount_formatted,
            "date": self.date,
            "counterparty": self.counterparty,
            "description": self.description,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "account_last4": self.account_last4,
            "confidence": round(self.confidence, 2),
        }


def extract_amount(text: str) -> tuple[Optional[float], str, float]:
    """
    Extract monetary value from text.
    
    Returns:
        Tuple of (amount, formatted_string, confidence)
    """
    patterns = [
        # Brazilian format: R$ 1.234,56 or R$1234,56
        (r'R\$\s*([\d.]+),?\s*(\d{2})?', 'BRL', 1.0),
        # US format: $1,234.56 or $1234.56
        (r'\$\s*([\d,]+)\.?(\d{2})?', 'USD', 1.0),
        # Generic with currency code
        (r'(\d+[.,]?\d{0,2})\s*(?:USD|EUR|GBP)', None, 0.9),
        # Plain number with decimal: 1234.56 or 1,234.56
        (r'(\d{1,3}(?:[,.]\d{3})*[.,]\d{2})', 'BRL', 0.7),
    ]
    
    for pattern, currency, confidence in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(0)
            
            # Extract numeric value
            numeric_match = re.search(r'[\d.,]+', amount_str)
            if numeric_match:
                numeric_str = numeric_match.group()
                
                # Clean and convert
                if ',' in numeric_str and '.' in numeric_str:
                    # Format: 1,234.56
                    numeric_str = numeric_str.replace(',', '')
                elif ',' in numeric_str:
                    # Brazilian: 1.234,56
                    numeric_str = numeric_str.replace('.', '').replace(',', '.')
                
                try:
                    amount = float(numeric_str)
                    return amount, amount_str.strip(), confidence
                except ValueError:
                    continue
    
    return None, None, 0.0


def extract_date(text: str) -> tuple[Optional[str], float]:
    """
    Extract date from text in various formats.
    Returns ISO format (YYYY-MM-DD).
    """
    patterns = [
        # Brazilian: 24/03/2026 or 24-03-2026
        (r'(\d{2})[/-](\d{2})[/-](\d{4})', lambda m: f"{m.group(3)}-{m.group(2)}-{m.group(1)}", 1.0),
        # US: 03/24/2026
        (r'(\d{2})[/-](\d{2})[/-](\d{4})', lambda m: f"{m.group(3)}-{m.group(1)}-{m.group(2)}", 0.9),
        # ISO: 2026-03-24
        (r'(\d{4})[/-](\d{2})[/-](\d{2})', lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}", 1.0),
        # Textual: 24 de março de 2026 or March 24, 2026
        (r'(\d{1,2})\s+de?\s+(\w+)\s+de?\s+(\d{4})', None, 0.8),
    ]
    
    months_pt = {
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
        'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
        'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12',
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12',
    }
    
    months_en = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    }
    
    for pattern, formatter, confidence in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if formatter:
                try:
                    date_str = formatter(match)
                    # Validate date
                    datetime.strptime(date_str, '%Y-%m-%d')
                    return date_str, confidence
                except ValueError:
                    continue
            else:
                # Handle textual dates
                day = match.group(1).zfill(2)
                month_str = match.group(2).lower()
                year = match.group(3)
                
                month = months_pt.get(month_str) or months_en.get(month_str)
                if month:
                    return f"{year}-{month}-{day}", confidence
    
    return None, 0.0


def extract_counterparty(text: str) -> tuple[Optional[str], float]:
    """Extract payee or payer name from text."""
    patterns = [
        # PIX patterns
        (r'(?:para|to|destinat[áa]rio|benefici[áa]rio)\s*:?\s*([A-Z][A-Za-z\s]+(?:Ltda|ME|SA|LLC)?)\s*(?:\d|\n|$)', 0.95),
        # "pago a" / "paid to"
        (r'(?:pago|pagamento)\s+(?:a|para|to)\s+([A-Z][A-Za-z\s]+)\.?', 0.9),
        # "de" before amount
        (r'de\s+([A-Z][A-Za-z\s]+(?:Ltda|ME|SA|LLC)?)\s+(?:no\s+valor|no\s+montante)', 0.85),
        # After "from" / "de"
        (r'from\s+([A-Z][A-Za-z\s]+(?:Inc|LLC|Corp)?)', 0.8),
        # Capitalized company names
        (r'(?:empresa|company|fornecedor|vendor)\s*:?\s*([A-Z][A-Za-z\s]+)', 0.75),
    ]
    
    for pattern, confidence in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            counterparty = match.group(1).strip()
            # Clean up
            counterparty = re.sub(r'\s+', ' ', counterparty)
            counterparty = counterparty.rstrip('.')
            if len(counterparty) > 2:
                return counterparty, confidence
    
    return None, 0.0


def extract_payment_method(text: str) -> tuple[Optional[str], float]:
    """Extract payment method from text."""
    methods = [
        (r'\bPIX\b', 'PIX', 1.0),
        (r'\bTED\b', 'TED', 1.0),
        (r'\bDOC\b', 'DOC', 1.0),
        (r'cart[ãa]o de cr[eé]dito', 'Credit Card', 0.95),
        (r'cart[ãa]o de d[eé]bito', 'Debit Card', 0.95),
        (r'dinheiro', 'Cash', 0.95),
        (r'\bcash\b', 'Cash', 0.95),
        (r'\bcredit card\b', 'Credit Card', 0.9),
        (r'\bdebit card\b', 'Debit Card', 0.9),
        (r'transfer[êe]ncia', 'Transfer', 0.9),
        (r'\btransfer\b', 'Transfer', 0.9),
        (r'boleto', 'Boleto', 0.95),
        (r'\bwire\b', 'Wire Transfer', 0.85),
    ]
    
    for pattern, method, confidence in methods:
        if re.search(pattern, text, re.IGNORECASE):
            return method, confidence
    
    return None, 0.5


def extract_transaction_id(text: str) -> tuple[Optional[str], float]:
    """Extract transaction or reference ID."""
    patterns = [
        # PIX ID
        (r'(?:transa[çc][ãa]o|transaction)\s*:?\s*#?\s*(\w+[-]?\d+)', 0.95),
        # Reference numbers
        (r'(?:refer[êe]ncia|reference)\s*:?\s*#?\s*(\w+[-]?\d+)', 0.95),
        # NFe number
        (r'(?:NF-e?|nota fiscal)\s*:?\s*#?\s*(\d+)', 0.95),
        # Generic ID patterns
        (r'(?:ID|n[úu]mero)\s*:?\s*#?(\w{6,})', 0.85),
    ]
    
    for pattern, confidence in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), confidence
    
    return None, 0.0


def extract_account_last4(text: str) -> tuple[Optional[str], float]:
    """Extract last 4 digits of account/card."""
    patterns = [
        (r'(?:cart[ãa]o|card)\s*[*x]+(\d{4})', 1.0),
        (r'conta\s*:?\s*\*+(\d{4})', 0.95),
        (r'terminada em[/\s]*(\d{4})', 0.95),
        (r'ending in[\s*]*(\d{4})', 0.95),
        (r'\*{4}[\s-]*(\d{4})', 0.9),
    ]
    
    for pattern, confidence in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1), confidence
    
    return None, 0.0


def determine_transaction_type(text: str) -> tuple[str, float]:
    """Determine the type of financial transaction."""
    type_keywords = [
        # Payment confirmations
        (r'\b(pagamento confirmado|comprovante|receipt|payment confirmed)\b', 'payment', 1.0),
        (r'\bpago\b', 'payment', 0.95),
        (r'\bpaid\b', 'payment', 0.95),
        # Invoices
        (r'\b(fatura|invoice|nota fiscal|NF-e?)\b', 'invoice', 1.0),
        (r'\bbill\b', 'invoice', 0.9),
        # Receipts
        (r'\b(comprovante|recibo|receipt)\b', 'receipt', 1.0),
        (r'\bcompra\b', 'purchase', 0.9),
        (r'\bpurchase\b', 'purchase', 0.9),
        # Transfers
        (r'\b(transfer[êe]ncia|transfer)\b', 'transfer', 0.95),
        (r'\bdeposit\b', 'deposit', 0.95),
        (r'\bdeposito\b', 'deposit', 0.95),
        # Refunds
        (r'\b(estorno|reembolso|refund)\b', 'refund', 0.95),
    ]
    
    for pattern, trans_type, confidence in type_keywords:
        if re.search(pattern, text, re.IGNORECASE):
            return trans_type, confidence
    
    # Default to generic transaction
    return 'transaction', 0.5


def parse_email(email_content: str) -> Dict[str, Any]:
    """
    Main function to parse email and extract transaction data.
    
    Args:
        email_content: Raw email text content
        
    Returns:
        Dictionary with extracted transaction fields
    """
    transaction = Transaction()
    confidence_scores = []
    
    # Extract transaction type
    trans_type, conf = determine_transaction_type(email_content)
    transaction.transaction_type = trans_type
    confidence_scores.append(conf)
    
    # Extract amount
    amount, amount_formatted, conf = extract_amount(email_content)
    transaction.amount = amount
    transaction.amount_formatted = amount_formatted
    confidence_scores.append(conf)
    
    # Detect currency
    if 'R$' in email_content or re.search(r'\breal(?:es)?\b', email_content, re.IGNORECASE):
        transaction.currency = 'BRL'
    elif '$' in email_content and 'R$' not in email_content:
        transaction.currency = 'USD'
    elif re.search(r'\busd?\b|\bd[oó]lar', email_content, re.IGNORECASE):
        transaction.currency = 'USD'
    else:
        transaction.currency = 'BRL'  # Default
    
    # Extract date
    date_str, conf = extract_date(email_content)
    transaction.date = date_str
    confidence_scores.append(conf)
    
    # Extract counterparty
    counterparty, conf = extract_counterparty(email_content)
    transaction.counterparty = counterparty
    confidence_scores.append(conf)
    
    # Extract payment method
    payment_method, conf = extract_payment_method(email_content)
    transaction.payment_method = payment_method
    confidence_scores.append(conf)
    
    # Extract transaction ID
    trans_id, conf = extract_transaction_id(email_content)
    transaction.transaction_id = trans_id
    confidence_scores.append(conf)
    
    # Extract account last 4
    account_last4, conf = extract_account_last4(email_content)
    transaction.account_last4 = account_last4
    if account_last4:
        confidence_scores.append(conf)
    
    # Calculate overall confidence (weighted average)
    non_zero_scores = [s for s in confidence_scores if s > 0]
    if non_zero_scores:
        transaction.confidence = sum(non_zero_scores) / len(non_zero_scores)
    
    # Extract description (subject or first line)
    lines = email_content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('From:') and not line.startswith('Subject:'):
            transaction.description = line[:200]  # First meaningful line
            break
    
    return transaction.to_dict()


def main():
    """CLI interface for extracting transactions from emails."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract financial transactions from email content'
    )
    parser.add_argument('--input', '-i', help='Input file containing email content')
    parser.add_argument('--output', '-o', help='Output file for JSON result')
    
    args = parser.parse_args()
    
    # Read input
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                email_content = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin
        try:
            email_content = sys.stdin.read()
        except Exception as e:
            print(f"Error reading stdin: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Parse email
    result = parse_email(email_content)
    
    # Output result
    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"Result saved to {args.output}")
        except Exception as e:
            print(f"Error writing output: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
