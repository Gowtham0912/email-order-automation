import imaplib
import email
from bs4 import BeautifulSoup

def clean_email_body(raw_body):
    """Remove HTML tags and return clean plain text."""
    try:
        soup = BeautifulSoup(raw_body, "html.parser")
        text = soup.get_text(separator="\n")
        return text.strip()
    except Exception:
        return raw_body

def fetch_emails(email_user, email_pass):
    """
    Fetch unread order-related emails from Gmail inbox.
    Returns a list of dicts: { 'subject': str, 'body': str }
    """
    mail_data = []

    try:
        # Connect to Gmail
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(email_user, email_pass)
        imap.select("inbox")

        # Search unread emails with keyword 'order'
        status, messages = imap.search(None, '(UNSEEN SUBJECT "order")')

        email_ids = messages[0].split()
        if not email_ids:
            print("⚠️ No new order emails found.")
            return []

        for e_id in email_ids:
            res, msg_data = imap.fetch(e_id, "(RFC822)")
            raw_msg = msg_data[0][1]
            msg = email.message_from_bytes(raw_msg)

            subject = msg["subject"]
            body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
                    elif content_type == "text/html":
                        html_body = part.get_payload(decode=True).decode(errors="ignore")
                        body = clean_email_body(html_body)
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")
                body = clean_email_body(body)

            mail_data.append({"subject": subject, "body": body})

        imap.close()
        imap.logout()
        print(f"📥 {len(mail_data)} new email(s) fetched successfully.")
        return mail_data

    except Exception as e:
        print("❌ Email fetching error:", e)
        return []
