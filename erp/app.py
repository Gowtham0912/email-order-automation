import sys, os
from flask import Flask, render_template, jsonify, request
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor.email_fetcher import fetch_emails
from extractor.ner_extractor import extract_order_details
from erp.models import add_order, session, PurchaseOrder
from config import EMAIL_USER, EMAIL_PASS

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Display dashboard with all orders"""
    orders = session.query(PurchaseOrder).all()
    return render_template("dashboard.html", orders=orders)

@app.route('/scan', methods=['POST'])
def scan_emails():
    """Fetch new emails asynchronously and update ERP"""
    print("\n📬 Scanning mailbox for new order emails...")
    emails = fetch_emails(EMAIL_USER, EMAIL_PASS)

    if not emails:
        return jsonify({"status": "no_new", "message": "⚠️ No new order emails found."})

    added = 0
    for mail in emails:
        print(f"\n✉️ Processing Email Subject: {mail['subject']}")
        details = extract_order_details(mail["body"], subject=mail["subject"])
        print("📨 Extracted Details:", details)
        add_order(details, mail["subject"])
        added += 1

    return jsonify({"status": "updated", "message": f"✅ {added} new order(s) added successfully!"})

@app.route('/delete/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Delete a specific order by ID"""
    order = session.query(PurchaseOrder).get(order_id)
    if order:
        session.delete(order)
        session.commit()
        return jsonify({"success": True, "message": "Order deleted successfully!"})
    return jsonify({"success": False, "message": "Order not found!"})

@app.route('/orders')
def get_orders():
    """Return updated orders list as JSON (for live refresh)"""
    orders = session.query(PurchaseOrder).all()
    data = [
        {
            "id": o.id,
            "product_name": o.product_name,
            "quantity_ordered": o.quantity_ordered,
            "delivery_due_date": o.delivery_due_date,
            "retailer_name": getattr(o, "retailer_name", ""),
            "retailer_email": o.retailer_email,
            "retailer_address": o.retailer_address,
            "client_email_subject": o.client_email_subject,
        }
        for o in orders
    ]
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
