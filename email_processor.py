import imaplib
import email
from email.header import decode_header
import os
import json
from datetime import datetime
import importlib.util

# CONFIG
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASS")

# IMPORTA SEU PARSER (ajustado para o arquivo existente)
spec = importlib.util.spec_from_file_location("parser", "financial-email-parser.py")
parser_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser_module)
parse_email = parser_module.parse_financial_email  # Nome correto da função

OUTPUT_FILE = "financial_log.json"


def save_to_json(data):
    try:
        with open(OUTPUT_FILE, "r") as f:
            existing = json.load(f)
    except:
        existing = []

    existing.append(data)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def process_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, PASSWORD)
    mail.select("inbox")

    status, messages = mail.search(None, "ALL")
    mail_ids = messages[0].split()

    latest_emails = mail_ids[-5:]

    for i in latest_emails:
        status, msg_data = mail.fetch(i, "(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")

                body = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                else:
                    body = msg.get_payload(decode=True).decode()

                full_text = f"{subject}\n{body}"

                result = parse_email(full_text)

                if result.get("relevant"):
                    result["processed_at"] = datetime.now().isoformat()
                    result["email_subject"] = subject  # Metadata extra

                    print("\n✅ TRANSAÇÃO DETECTADA:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))

                    save_to_json(result)

    mail.logout()


if __name__ == "__main__":
    process_emails()
