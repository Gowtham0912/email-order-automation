import imaplib
import email
from bs4 import BeautifulSoup
import os
from extractor.ocr_utils import extract_text_from_pdf, extract_text_from_image  # ✅ added image OCR

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

        base_dir = os.path.dirname(os.path.abspath(__file__))
        attach_dir = os.path.join(base_dir, "attachments")
        os.makedirs(attach_dir, exist_ok=True)

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
                    filename = part.get_filename()

                    # --- Email body (plain or HTML) ---
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body = part.get_payload(decode=True).decode(errors="ignore")

                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        html_body = part.get_payload(decode=True).decode(errors="ignore")
                        body = clean_email_body(html_body)

                    # --- Handle attachments (PDF + Images) ---
                    elif filename:
                        filepath = os.path.join(attach_dir, filename)
                        with open(filepath, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        print(f"📎 Saved attachment: {filename}")

                        ext = filename.lower()
                        extracted_text = ""

                        # PDF OCR
                        if ext.endswith(".pdf"):
                            extracted_text = extract_text_from_pdf(filepath)

                        # Image OCR
                        elif ext.endswith((".jpg", ".jpeg", ".png", ".tiff", ".bmp")):
                            extracted_text = extract_text_from_image(filepath)

                        if extracted_text.strip():
                            body += f"\n\n[Extracted from {filename}]\n{extracted_text}"

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
