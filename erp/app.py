import sys, os, imaplib
from flask import Flask, render_template, jsonify, request, redirect, url_for, session

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor.email_fetcher import fetch_emails
from extractor.ner_extractor import extract_order_details
from erp.models import add_order, session as db_session, PurchaseOrder

app = Flask(__name__)
app.secret_key = "super_secret_key_123"  # Change this in production


# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login screen that validates Gmail IMAP login"""
    if request.method == 'POST':
        email_user = request.form.get('email', '').strip()
        email_pass = request.form.get('password', '').strip()

        if not email_user or not email_pass:
            return render_template('login.html', error="⚠️ Both fields are required!")

        # ✅ Try Gmail IMAP login
        try:
            imap = imaplib.IMAP4_SSL("imap.gmail.com")
            imap.login(email_user, email_pass)
            imap.logout()
            print(f"✅ Gmail login successful for {email_user}")

            # Store credentials in session
            session['email_user'] = email_user
            session['email_pass'] = email_pass

            return redirect(url_for('dashboard'))

        except imaplib.IMAP4.error:
            print(f"❌ Invalid credentials for {email_user}")
            return render_template('login.html', error="❌ Invalid email or app password.")
        except Exception as e:
            print("⚠️ Error during login:", e)
            return render_template('login.html', error=f"⚠️ Gmail connection error: {e}")

    # If already logged in, go to dashboard
    if "email_user" in session:
        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    print("👋 User logged out.")
    return redirect(url_for('login'))


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    """Show dashboard only if logged in"""
    if "email_user" not in session:
        return redirect(url_for('login'))

    orders = db_session.query(PurchaseOrder).all()
    return render_template("dashboard.html", orders=orders)


# ---------------- SCAN EMAILS ----------------
@app.route('/scan', methods=['POST'])
def scan_emails():
    """Fetch new emails for logged-in user"""
    if "email_user" not in session or "email_pass" not in session:
        return jsonify({"status": "unauthorized", "message": "⚠️ Please log in first."})

    email_user = session['email_user']
    email_pass = session['email_pass']

    print(f"\n📬 Scanning mailbox for new order emails ({email_user})...")
    emails = fetch_emails(email_user, email_pass)

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


# ---------------- DELETE ORDER ----------------
@app.route('/delete/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Delete order if logged in"""
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
    """Return all orders (protected)"""
    if "email_user" not in session:
        return jsonify([])

    orders = db_session.query(PurchaseOrder).all()
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
