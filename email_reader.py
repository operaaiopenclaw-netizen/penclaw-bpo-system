import imaplib
import email
from email.header import decode_header
import os

IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASS")

def read_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, PASSWORD)
    mail.select("inbox")

    status, messages = mail.search(None, "ALL")
    mail_ids = messages[0].split()

    latest_emails = mail_ids[-5:] # últimos 5 emails

    for i in latest_emails:
        status, msg_data = mail.fetch(i, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")

                print("\n📩 SUBJECT:", subject)

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            print("BODY:", body[:500])
                else:
                    body = msg.get_payload(decode=True).decode()
                    print("BODY:", body[:500])

    mail.logout()

if __name__ == "__main__":
    read_emails()
