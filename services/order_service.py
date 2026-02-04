# services/order_service.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hashlib
from extractor.ner_extractor import extract_order_details
from extractor.email_fetcher import fetch_emails
from services.confidence_engine import calculate_confidence
from services.validate_service import validate_extracted
from erp.models import add_order, session as db_session, PurchaseOrder


# ---------------- EMAIL FINGERPRINT ----------------
def email_fingerprint(subject: str, body: str) -> str:
    raw = (subject or "") + (body or "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------- DUPLICATE CHECK ----------------
def is_duplicate(email_hash: str) -> bool:
    return db_session.query(PurchaseOrder).filter(
        PurchaseOrder.email_hash == email_hash
    ).first() is not None


# ---------------- PRIORITY DETECTION ----------------
def detect_priority(text: str) -> str:
    keywords = ["urgent", "immediately", "asap", "high priority"]
    return "Urgent" if any(k in (text or "").lower() for k in keywords) else "Normal"


# ---------------- CORE PIPELINE ----------------
def process_emails(email_user, email_pass):
    """
    ERP Pipeline:
    Fetch → Extract → Validate → Score → Save
    """
    emails = fetch_emails(email_user, email_pass)
    if not emails:
        return 0

    added = 0

    for mail in emails:
        subject = mail.get("subject", "")
        body = mail.get("body", "")

        email_hash = email_fingerprint(subject, body)
        if is_duplicate(email_hash):
            continue

        # ---- NER Extraction ----
        details = extract_order_details(body, subject=subject)

        # Store raw email for ML training
        details["raw_text"] = body

        # ---- Validation ----
        issues = validate_extracted(details)

        # ---- Confidence ----
        confidence = calculate_confidence(details)

        # ---- ERP Decision ----
        if confidence >= 85:
            status = "Approved"
        elif confidence >= 70:
            status = "Needs Review"
        else:
            status = "Rejected"

        priority = detect_priority(subject + " " + body)

        # ---- Save ----
        add_order(
            details=details,
            subject=subject,
            email_hash=email_hash,
            order_status=status,
            confidence_score=confidence,
            priority_level=priority,
            remarks=", ".join(issues) if issues else None
        )

        added += 1

    return added
