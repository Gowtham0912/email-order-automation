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
    """
    Create deterministic hash for duplicate detection
    """
    raw = (subject or "") + (body or "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------- DUPLICATE CHECK ----------------
def is_duplicate(email_hash: str) -> bool:
    """
    Prevent re-processing of already handled emails
    """
    return db_session.query(PurchaseOrder).filter(
        PurchaseOrder.email_hash == email_hash
    ).first() is not None


# ---------------- PRIORITY DETECTION ----------------
def detect_priority(text: str) -> str:
    """
    Detect urgency keywords for ERP prioritization
    """
    keywords = ["urgent", "immediately", "asap", "high priority"]
    return "Urgent" if any(k in (text or "").lower() for k in keywords) else "Normal"


# ---------------- CORE PIPELINE ----------------
def process_emails(email_user, email_pass):
    """
    ERP Pipeline:
    Fetch → Extract → Validate → Confidence → Save
    """
    emails = fetch_emails(email_user, email_pass)
    if not emails:
        return 0

    added = 0

    for mail in emails:
        subject = mail.get("subject", "")
        body = mail.get("body", "")

        # ---- Duplicate protection ----
        email_hash = email_fingerprint(subject, body)
        if is_duplicate(email_hash):
            continue

        # ---- NER Extraction ----
        details = extract_order_details(body, subject=subject)

        # ---- Validation ----
        issues = validate_extracted(details)

        # ---- Confidence Score ----
        confidence = calculate_confidence(details)

        # ---- ERP Decisions ----
        if confidence >= 85:
            order_status = "Approved"
        elif confidence >= 70:
            order_status = "Needs Review"
        else:
            order_status = "Rejected"

        priority = detect_priority(subject + " " + body)

        # ---- Save to ERP ----
        add_order(
            details=details,
            subject=subject,
            email_hash=email_hash,
            order_status=order_status,
            confidence_score=confidence,
            priority_level=priority,
            remarks=", ".join(issues) if issues else None
        )

        added += 1

    return added
