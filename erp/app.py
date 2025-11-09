# erp/app.py
import sys, os
from flask import Flask, render_template
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor.email_fetcher import fetch_emails
from extractor.ner_extractor import extract_order_details
from erp.models import add_order, session, Order
from config import EMAIL_USER, EMAIL_PASS

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Display all saved orders"""
    orders = session.query(Order).all()
    return render_template("dashboard.html", orders=orders)

@app.route('/scan')
def scan_emails():
    """Fetch new emails, extract details, and save to DB"""
    print("📬 Scanning mailbox for new order emails...")
    emails = fetch_emails(EMAIL_USER, EMAIL_PASS)

    if not emails:
        print("⚠️ No new order emails found.")
        return "⚠️ No new order emails found."

    for mail in emails:
        print(f"✉️ Processing email: {mail['subject']}")
        details = extract_order_details(mail["body"])
        print("📨 Extracted Details:", details)

        add_order(details, mail["subject"])

    return "✅ ERP updated successfully! Orders saved to database."

if __name__ == "__main__":
    app.run(debug=True)
