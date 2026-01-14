import sys, os, imaplib, io, threading, time
import pandas as pd
from fpdf import FPDF
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, send_file

# make sure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extractor.email_fetcher import fetch_emails
from extractor.ner_extractor import extract_order_details
from erp.models import add_order, session as db_session, PurchaseOrder

app = Flask(__name__)
app.secret_key = "super_secret_key_123"  # Change later

# ---------------- AUTO SCAN STATE ----------------
auto_scan_enabled = False
auto_scan_thread = None

# ---------------- COMMON SCAN LOGIC ----------------
def run_scan(email_user, email_pass):
    print(f"\n📬 Scanning mailbox for new order emails ({email_user})...")
    emails = fetch_emails(email_user, email_pass)

    if not emails:
        return 0

    added = 0
    for mail in emails:
        print(f"\n✉️ Processing Email Subject: {mail['subject']}")
        details = extract_order_details(mail["body"], subject=mail["subject"])
        print("📨 Extracted Details:", details)
        add_order(details, mail["subject"])
        added += 1

    return added

# ---------------- AUTO SCAN WORKER ----------------
def auto_scan_worker(email_user, email_pass):
    global auto_scan_enabled
    while auto_scan_enabled:
        print("🔄 Automatic scan running...")
        run_scan(email_user, email_pass)
        time.sleep(60)  # scan every 60 seconds

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_user = request.form.get('email', '').strip()
        email_pass = request.form.get('password', '').strip()

        if not email_user or not email_pass:
            return render_template('login.html', error="⚠️ Both fields are required!")

        try:
            imap = imaplib.IMAP4_SSL("imap.gmail.com")
            imap.login(email_user, email_pass)
            imap.logout()

            session['email_user'] = email_user
            session['email_pass'] = email_pass
            return redirect(url_for('dashboard'))

        except imaplib.IMAP4.error:
            return render_template('login.html', error="❌ Invalid email or app password.")
        except Exception as e:
            return render_template('login.html', error=f"⚠️ Gmail connection error: {e}")

    if "email_user" in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if "email_user" not in session:
        return redirect(url_for('login'))

    orders = db_session.query(PurchaseOrder).all()
    return render_template("dashboard.html", orders=orders)

# ---------------- MANUAL SCAN ----------------
@app.route('/scan', methods=['POST'])
def scan_emails():
    global auto_scan_enabled

    if "email_user" not in session or "email_pass" not in session:
        return jsonify({"status": "unauthorized", "message": "⚠️ Please log in first."})

    if auto_scan_enabled:
        return jsonify({
            "status": "blocked",
            "message": "⚠️ Automatic scan is running. Turn it off to use manual scan."
        })

    added = run_scan(session['email_user'], session['email_pass'])

    if added == 0:
        return jsonify({"status": "no_new", "message": "⚠️ No new order emails found."})

    return jsonify({"status": "updated", "message": f"✅ {added} new order(s) added successfully!"})

# ---------------- TOGGLE AUTO SCAN ----------------
@app.route('/toggle-auto-scan', methods=['POST'])
def toggle_auto_scan():
    global auto_scan_enabled, auto_scan_thread

    if "email_user" not in session or "email_pass" not in session:
        return jsonify({"status": "unauthorized"})

    enabled = request.json.get("enabled", False)
    auto_scan_enabled = enabled

    if enabled:
        if auto_scan_thread is None or not auto_scan_thread.is_alive():
            auto_scan_thread = threading.Thread(
                target=auto_scan_worker,
                args=(session['email_user'], session['email_pass']),
                daemon=True
            )
            auto_scan_thread.start()

    return jsonify({"auto_scan": auto_scan_enabled})

# ---------------- AUTO SCAN STATUS ----------------
@app.route('/auto-scan-status')
def auto_scan_status():
    return jsonify({"auto_scan": auto_scan_enabled})

# ---------------- DELETE ORDER ----------------
@app.route('/delete/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    if "email_user" not in session:
        return jsonify({"success": False, "message": "⚠️ Please log in first."})

    order = db_session.query(PurchaseOrder).get(order_id)
    if order:
        db_session.delete(order)
        db_session.commit()
        return jsonify({"success": True, "message": "Order deleted successfully!"})

    return jsonify({"success": False, "message": "Order not found!"})

# ---------------- GET ORDERS ----------------
@app.route('/orders')
def get_orders():
    if "email_user" not in session:
        return jsonify([])

    orders = db_session.query(PurchaseOrder).all()
    return jsonify([
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
    ])

# ---------------- EXPORT TO EXCEL ----------------
@app.route('/export/excel')
def export_excel():
    if "email_user" not in session:
        return redirect(url_for('login'))

    orders = db_session.query(PurchaseOrder).all()
    df = pd.DataFrame([{
        "Order ID": o.id,
        "Product Name": o.product_name,
        "Quantity": o.quantity_ordered,
        "Due Date": o.delivery_due_date,
        "Retailer Name": getattr(o, "retailer_name", ""),
        "Retailer Email": o.retailer_email,
        "Retailer Address": o.retailer_address,
        "Email Subject": o.client_email_subject,
    } for o in orders])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    return send_file(output, as_attachment=True,
                     download_name="ERP_Orders.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------- EXPORT TO PDF ----------------
@app.route('/export/pdf')
def export_pdf():
    if "email_user" not in session:
        return redirect(url_for('login'))

    orders = db_session.query(PurchaseOrder).all()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, txt="ERP Purchase Order Report", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=11)

    for o in orders:
        text = f"""
Order ID: {o.id}
Product: {o.product_name}
Quantity: {o.quantity_ordered}
Due Date: {o.delivery_due_date}
Retailer: {getattr(o, "retailer_name", "")}
Email: {o.retailer_email}
Address: {o.retailer_address}
Subject: {o.client_email_subject}
------------------------------
"""
        pdf.multi_cell(0, 8, text.encode("latin-1", "ignore").decode("latin-1"))

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name="ERP_Orders.pdf",
                     mimetype="application/pdf")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
