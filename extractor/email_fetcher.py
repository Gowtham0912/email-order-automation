import imaplib, email
from email.header import decode_header
import os

def fetch_emails(EMAIL_USER, EMAIL_PASS, imap_server="imap.gmail.com"):
    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")
    status, messages = mail.search(None, '(UNSEEN SUBJECT "order")')
    emails = []

    for num in messages[0].split():
        _, data = mail.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])
        subject = decode_header(msg["Subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                try:
                    body = part.get_payload(decode=True).decode()
                except:
                    pass
        else:
            body = msg.get_payload(decode=True).decode()

        emails.append({"subject": subject, "body": body})
    return emails
