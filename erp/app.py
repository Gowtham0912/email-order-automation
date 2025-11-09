import sys, os
from flask import Flask, render_template
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor.email_fetcher import fetch_emails
from extractor.ner_extractor import extract_order_details
from erp.models import add_order, session, PurchaseOrder
from config import EMAIL_USER, EMAIL_PASS

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Display all saved purchase orders"""
    orders = session.query(PurchaseOrder).all()
    return render_template("dashboard.html", orders=orders)

@app.route('/scan')
def scan_emails():
    """Fetch new emails, extract details, and save to DB"""
    print("\n📬 Scanning mailbox for new order emails...")
    emails = fetch_emails(EMAIL_USER, EMAIL_PASS)

    if not emails:
        print("⚠️ No new order emails found.")
        return "⚠️ No new order emails found."

    for mail in emails:
        print(f"\n✉️ Processing Email Subject: {mail['subject']}")
        details = extract_order_details(mail["body"], subject=mail["subject"])
        print("📨 Extracted Details:", details)
        add_order(details, mail["subject"])

    print("✅ ERP database updated successfully!")
    return "✅ ERP updated successfully! Orders saved to database."

if __name__ == "__main__":
    app.run(debug=True)
