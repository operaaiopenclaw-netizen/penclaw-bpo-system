---
name: financial-email-observer
description: Monitor email inbox and extract financial transactions from messages. Use when (1) processing emails containing payment confirmations, invoices, receipts, or bank notifications, (2) extracting transaction data for accounting or expense tracking, (3) identifying amounts, dates, payees, and payment methods from email content, or (4) converting unstructured email financial data into structured records.
---

# Financial Email Observer

## Overview

Extract structured financial transaction data from emails. Parses unstructured email text to identify payments, invoices, receipts, and banking activity, converting them into standardized JSON records ready for accounting systems.

## Quick Start

Process a single email by providing the message content:

```python
from scripts.extract_transaction import parse_email

# Parse raw email text
email_text = """From: noreply@bank.com
Subject: PIX Receipt - Payment Confirmed

Payment of R$ 1,250.00 to ACME Supplies confirmed on 24/03/2026.
Transaction ID: PIX-123456789
"""

result = parse_email(email_text)
# Returns structured transaction data
```

See `scripts/` for executable tools.

## Transaction Types Supported

### 1. Payment Confirmations
- PIX receipts
- Bank transfer confirmations
- Credit card transaction alerts
- Bill payment confirmations

### 2. Invoices & Bills
- Vendor invoices
- Utility bills
- Subscription renewals
- Service charges

### 3. Receipts
- Purchase receipts
- Expense reimbursements
- Refund notifications

### 4. Banking Activity
- Deposit notifications
- Withdrawal alerts
- Fee charges
- Account statements (summarized)

## Supported Fields

Each extracted transaction includes:

| Field | Description | Example |
|-------|-------------|---------|
| `transaction_type` | Type of financial activity | `payment`, `invoice`, `receipt`, `transfer` |
| `amount` | Monetary value (with currency) | `1250.00` |
| `currency` | Currency code | `BRL`, `USD` |
| `amount_formatted` | Formatted string | `R$ 1.250,00` |
| `date` | Transaction date (ISO format) | `2026-03-24` |
| `counterparty` | Payee or payer name | `ACME Supplies` |
| `description` | Transaction description | `Office supplies` |
| `payment_method` | How payment was made | `PIX`, `Credit Card`, `Transfer` |
| `transaction_id` | Reference number | `PIX-123456789` |
| `account_last4` | Last 4 digits (if present) | `8921` |
| `confidence` | Extraction confidence score | `0.95` |

## How to Use

### Direct Email Processing

```python
from scripts.extract_transaction import parse_email

# Process a raw email
result = parse_email(email_content)
print(result)
```

### Batch Processing

```python
from scripts.extract_transaction import parse_email

emails = [email1, email2, email3]  # List of email texts
results = []

for email in emails:
    try:
        transaction = parse_email(email)
        if transaction['amount']:
            results.append(transaction)
    except Exception as e:
        print(f"Failed to process email: {e}")
```

### Integration with Accounting

Use the output to create records:

```json
{
  "transaction_type": "payment",
  "amount": 1250.00,
  "currency": "BRL",
  "date": "2026-03-24",
  "counterparty": "ACME Supplies",
  "payment_method": "PIX",
  "description": "Payment confirmed"
}
```

## Confidence Scoring

Each extraction includes a confidence score (0-1) based on:
- Presence of amount indicators (R$, $, USD, etc.)
- Date formatting clarity
- Transaction keywords detected
- Pattern match quality

**Interpretation:**
- `> 0.9`: High confidence, likely accurate
- `0.7-0.9`: Medium confidence, review recommended
- `< 0.7`: Low confidence, manual verification needed

## Important Notes

- **Privacy**: This skill processes email content; handle sensitive financial data securely
- **Validation**: Always review extractions with confidence < 0.9
- **Currency**: Defaults to BRL for Brazilian Portuguese, configurable to USD
- **Date Parsing**: Supports Brazilian (DD/MM/YYYY) and ISO (YYYY-MM-DD) formats
- **Error Handling**: Returns `None` values for fields that cannot be extracted

## Resources

### scripts/
- `extract_transaction.py` - Main parsing script with `parse_email()` function

## Limitations

- Does not connect to email servers (processes provided content only)
- Supports structured text emails; complex HTML may require preprocessing
- Limited to extraction from the provided text; cannot query external sources
