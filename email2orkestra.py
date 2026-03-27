#!/usr/bin/env python3
"""
Email 2 Orkestra - Integração Completa
Lê emails do Gmail → Extrai dados financeiros → Registra no Orkestra
"""

import imaplib
import email
from email.header import decode_header
import os
import json
from datetime import datetime
import importlib.util

# ============================================================
# CONFIGURAÇÃO
# ============================================================
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Arquivos de saída
FINANCIAL_LOG = "financial_log.json"
ORKESTRA_STATE = "orkestra-events-state.json"
PROCESSED_FILE = "processed_ids.txt"

# ============================================================
# CARREGA O PARSER FINANCEIRO
# ============================================================
spec = importlib.util.spec_from_file_location("parser", "financial-email-parser.py")
parser_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser_module)
parse_financial_email = parser_module.parse_financial_email

# ============================================================
# FUNÇÕES DE PERSISTÊNCIA
# ============================================================
def load_processed_ids():
    """Carrega IDs de emails já processados."""
    try:
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f.read().splitlines() if line.strip())
    except FileNotFoundError:
        return set()


def save_processed_id(message_id):
    """Salva ID de email processado."""
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(message_id + "\n")


def save_financial_log(transaction):
    """Salva transação no log financeiro."""
    try:
        with open(FINANCIAL_LOG, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"transactions": [], "last_updated": None}
    
    transaction["id"] = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(data['transactions']) + 1}"
    transaction["received_at"] = datetime.now().isoformat()
    
    data["transactions"].append(transaction)
    data["last_updated"] = datetime.now().isoformat()
    
    with open(FINANCIAL_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return transaction["id"]


def update_orkestra_state(transaction):
    """Atualiza o estado do Orkestra com a transação identificada."""
    try:
        with open(ORKESTRA_STATE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {
            "version": "1.1",
            "lastUpdated": datetime.now().isoformat(),
            "events": {},
            "resumo_geral": {
                "total_eventos": 0,
                "receita_geral": 0,
                "custo_geral": 0,
                "margem_geral": 0
            }
        }
    
    # Inicializa pending_transactions se não existir
    if "pending_transactions" not in state:
        state["pending_transactions"] = []
    
    # Cria entrada pending para classificação manual de evento
    pending_entry = {
        "transaction_id": transaction.get("id"),
        "type": transaction.get("type"),  # income/expense
        "value": transaction.get("value"),
        "category": transaction.get("category"),
        "source": transaction.get("source"),
        "description": transaction.get("email_subject", ""),
        "date": transaction.get("date"),
        "payment_method": transaction.get("payment_method"),
        "event": transaction.get("event"),  # Se detectado automaticamente
        "status": "needs_event_mapping" if not transaction.get("event") else "mapped",
        "detected_at": datetime.now().isoformat()
    }
    
    state["pending_transactions"].append(pending_entry)
    state["lastUpdated"] = datetime.now().isoformat()
    
    with open(ORKESTRA_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def classify_orkestra_operation(transaction):
    """Classifica a operação segundo o sistema Orkestra Finance Brain."""
    if transaction.get("type") == "income":
        return {
            "tipo": "conta_receber",
            "operacao_origem": "RECEBIMENTO",
            "status": "recebido"
        }
    elif transaction.get("type") == "expense":
        # Se já foi pago (comprovante), é PAGAMENTO
        # Se é boleto/fatura, é COMPRA (a pagar)
        doc_type = transaction.get("document_type", "")
        if doc_type in ["receipt", "pix"]:
            return {
                "tipo": "conta_pagar",
                "operacao_origem": "PAGAMENTO",
                "status": "liquidado"
            }
        else:
            return {
                "tipo": "conta_pagar",
                "operacao_origem": "COMPRA",
                "status": "pendente"
            }
    return None


def detect_event_risk(data, state):
    """Detecta risco de dominância de categoria dentro de um evento."""
    event = data.get("event")
    
    if not event:
        return data
    
    # Carrega estado do evento
    event_data = state.get("events", {}).get(event, {})
    total_cost = event_data.get("custo_total", 0)
    custos_por_categoria = event_data.get("custos_por_categoria", {})
    
    # Novo custo após esta transação
    transaction_value = data.get("value", 0) or 0
    if data.get("type") == "expense":
        new_total_cost = total_cost + transaction_value
    else:
        new_total_cost = total_cost
    
    # Verifica dominância da categoria atual
    category = data.get("category", "outros")
    current_cat_cost = custos_por_categoria.get(category, 0)
    
    # Atualiza com a transação atual
    new_cat_cost = current_cat_cost + transaction_value
    
    if new_total_cost > 0:
        ratio = new_cat_cost / new_total_cost
        
        # Alerta se categoria ultrapassa 40% do custo total
        if ratio > 0.4:
            if "alerts" not in data:
                data["alerts"] = []
            if "has_alerts" not in data:
                data["has_alerts"] = False
            
            data["alerts"].append({
                "type": "category_dominance",
                "severity": "warning",
                "message": f"{category} representa {ratio*100:.1f}% do custo do evento",
                "threshold": "40%",
                "current_ratio": f"{ratio*100:.1f}%"
            })
            data["has_alerts"] = True
            
            # Adiciona insight
            if "insights" not in data:
                data["insights"] = []
            if "has_insights" not in data:
                data["has_insights"] = False
                
            data["insights"].append({
                "type": "cost_review",
                "priority": "high",
                "message": f"{category.title()} está dominando o orçamento. Revisar necessidade ou buscar alternativas de fornecedor."
            })
            data["has_insights"] = True
    
    return data


# ============================================================
# PROCESSAMENTO DE EMAILS
# ============================================================
def extract_email_body(msg):
    """Extrai o corpo do email em texto puro."""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    break
                except:
                    pass
            elif content_type == "text/html":
                # Poderia converter HTML para texto, mas por ora pega o plain
                continue
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except:
            body = str(msg.get_payload())
    
    return body


def process_single_email(msg_data):
    """Processa um email individual."""
    msg = email.message_from_bytes(msg_data)
    
    # Extrai Message-ID (único globalmente)
    message_id = msg.get("Message-ID", "").strip("<>")
    
    # Extrai subject
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8")
    
    # Extrai remetente
    from_header = msg.get("From", "N/A")
    
    # Extrai data do email
    date_header = msg.get("Date", "")
    
    # Extrai corpo
    body = extract_email_body(msg)
    
    # Monta texto completo para análise
    full_text = f"Subject: {subject}\nFrom: {from_header}\nDate: {date_header}\n\n{body}"
    
    return {
        "message_id": message_id,
        "subject": subject,
        "from": from_header,
        "date": date_header,
        "body": body,
        "full_text": full_text
    }


def scan_emails(limit=10, unread_only=False):
    """
    Escaneia emails e processa os financeiros.
    
    Args:
        limit: Quantidade de emails a processar (do mais recente)
        unread_only: Se True, só processa emails não lidos
    """
    print("🔗 Conectando ao Gmail...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASS)
    mail.select("inbox")
    print("✅ Conectado!\n")
    
    # Carrega IDs já processados
    processed_ids = load_processed_ids()
    print(f"📋 {len(processed_ids)} email(s) já processados anteriormente\n")
    
    # Busca emails
    if unread_only:
        status, messages = mail.search(None, "UNSEEN")
    else:
        status, messages = mail.search(None, "ALL")
    
    mail_ids = messages[0].split()
    
    if not mail_ids:
        print("📭 Nenhum email encontrado.")
        mail.logout()
        return []
    
    # Pega os últimos N emails
    latest_emails = mail_ids[-limit:] if len(mail_ids) > limit else mail_ids
    
    # Filtra emails já processados
    new_emails = [eid for eid in latest_emails if eid.decode() not in processed_ids]
    skipped = len(latest_emails) - len(new_emails)
    
    if skipped > 0:
        print(f"⏭️  Pulando {skipped} email(s) já processado(s)")
    
    print(f"📧 Processando {len(new_emails)} email(s) novos...\n")
    
    financial_emails = []
    
    for idx, email_id in enumerate(new_emails, 1):
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                email_data = process_single_email(response_part[1])
                
                # Pula se Message-ID já foi processado
                if email_data.get("message_id") in processed_ids:
                    print(f"[{idx}] ⏭️  {email_data['subject'][:50]}... (já processado)")
                    continue
                
                print(f"[{idx}] 📩 {email_data['subject'][:50]}...")
                
                # Analisa com parser financeiro
                result = parse_financial_email(email_data["full_text"])
                
                if result.get("relevant"):
                    print(f"    💰 TRANSAÇÃO FINANCEIRA DETECTADA!")
                    
                    # Enriquece com metadados
                    transaction = {
                        **result,
                        "email_subject": email_data["subject"],
                        "email_from": email_data["from"],
                        "email_date": email_data["date"],
                        "processed_at": datetime.now().isoformat()
                    }
                    
                    # Classifica operação Orkestra
                    orkestra_op = classify_orkestra_operation(transaction)
                    if orkestra_op:
                        transaction["orkestra_op"] = orkestra_op
                    
                    # Carrega estado atual para análise de risco
                    try:
                        with open(ORKESTRA_STATE, "r", encoding="utf-8") as f:
                            current_state = json.load(f)
                    except (FileNotFoundError, json.JSONDecodeError):
                        current_state = {
                            "version": "1.1",
                            "events": {},
                            "pending_transactions": [],
                            "resumo_geral": {
                                "total_eventos": 0,
                                "receita_geral": 0,
                                "custo_geral": 0,
                                "margem_geral": 0
                            }
                        }
                    
                    # Detecta risco de dominância de categoria no evento
                    transaction = detect_event_risk(transaction, current_state)
                    
                    # Salva no log
                    txn_id = save_financial_log(transaction)
                    transaction["id"] = txn_id
                    
                    # Atualiza estado Orkestra
                    update_orkestra_state(transaction)
                    
                    financial_emails.append(transaction)
                    
                    # Display formatado
                    print(f"    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    print(f"    🆔 ID: {txn_id}")
                    print(f"    💵 Valor: R$ {transaction.get('value', 'N/A')}")
                    print(f"    📊 Tipo: {transaction.get('type', 'N/A')}")
                    print(f"    📋 Doc: {transaction.get('document_type', 'N/A')}")
                    print(f"    🏷️  Categoria: {transaction.get('category', 'N/A')}")
                    if transaction.get("macro_center"):
                        print(f"    🏭 Macro Centro: {transaction.get('macro_center')}")
                    if transaction.get("impact"):
                        print(f"    📈 Impacto: {transaction.get('impact')}")
                    print(f"    🏢 Origem: {transaction.get('source', 'N/A')}")
                    if transaction.get("event"):
                        print(f"    🎯 Evento: {transaction.get('event')}")
                    print(f"    🎛️  Orkestra: {orkestra_op['operacao_origem']} → {orkestra_op['status']}")
                    
                    # Mostra alertas se houver
                    if transaction.get("has_alerts"):
                        for alert in transaction.get("alerts", []):
                            icon = "🔴" if alert.get("severity") == "critical" else "🟡" if alert.get("severity") == "warning" else "🔵"
                            print(f"    {icon} Alerta: {alert.get('message', '')}")
                    
                    print(f"    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
                    
                    # Marca email como processado
                    if email_data.get("message_id"):
                        save_processed_id(email_data["message_id"])
                else:
                    print(f"    ⚪ Não-financeiro\n")
    
    mail.logout()
    print(f"🔒 Desconectado do Gmail")
    
    return financial_emails


# ============================================================
# INTERFACE CLI
# ============================================================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Email 2 Orkestra - Pipeline de emails financeiros",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python3 email2orkestra.py              # Processa últimos 10 emails
  python3 email2orkestra.py -n 20         # Processa últimos 20 emails
  python3 email2orkestra.py -u            # Só emails não lidos
  python3 email2orkestra.py -n 5 -u        # Últimos 5 não lidos
        """
    )
    parser.add_argument("-n", "--limit", type=int, default=10,
                        help="Quantidade de emails a processar (padrão: 10)")
    parser.add_argument("-u", "--unread", action="store_true",
                        help="Processar apenas emails não lidos")
    
    args = parser.parse_args()
    
    # Verifica credenciais
    if not EMAIL_ACCOUNT or not EMAIL_PASS:
        print("❌ ERRO: Configure as variáveis de ambiente:")
        print("   export EMAIL_USER='seu-email@gmail.com'")
        print("   export EMAIL_PASS='sua-senha-de-app'")
        return
    
    print("=" * 60)
    print("🎛️  EMAIL 2 ORKESTRA - Pipeline Financeiro")
    print("=" * 60)
    
    # Processa emails
    transactions = scan_emails(limit=args.limit, unread_only=args.unread)
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DA EXECUÇÃO")
    print("=" * 60)
    print(f"✅ Transações detectadas: {len(transactions)}")
    
    if transactions:
        total_income = sum(t.get("value", 0) for t in transactions if t.get("type") == "income")
        total_expense = sum(t.get("value", 0) for t in transactions if t.get("type") == "expense")
        
        print(f"📥 Entradas: R$ {total_income:.2f}")
        print(f"📤 Saídas: R$ {total_expense:.2f}")
        print(f"📁 Arquivos atualizados:")
        print(f"   • {FINANCIAL_LOG}")
        print(f"   • {ORKESTRA_STATE}")
        
        # Lista transações pendentes de mapeamento de evento
        unmapped = [t for t in transactions if not t.get("event")]
        if unmapped:
            print(f"\n⚠️  {len(unmapped)} transação(ões) precisam de vinculação a evento:")
            for t in unmapped:
                print(f"   • {t['id']}: {t.get('email_subject', 'N/A')[:40]}...")
    else:
        print("Nenhuma transação financeira encontrada nos emails processados.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
