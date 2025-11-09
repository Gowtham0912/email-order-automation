import re
import spacy
from datetime import datetime
import dateparser

nlp = spacy.load("en_core_web_sm")

def extract_order_details(text, subject=None):
    """Extract product, quantity, due date, retailer details (name, email, address)."""
    details = {
        "product": None,
        "quantity": None,
        "due_date": None,
        "retailer_name": None,
        "retailer_email": None,
        "retailer_address": None,
    }

    # --- Clean text ---
    text = re.sub(r"\s+", " ", text).strip()

    # --- Retailer Email ---
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    if email_match:
        details["retailer_email"] = email_match.group(0).strip()

    # --- Address ---
    address_match = re.search(
        r"(?:Delivery\s*Location|Address|Ship\s*to|Deliver\s*to)\s*[:\- ]+\s*([^:]+?)(?=\s*(?:Kindly|Best|Regards|Email|$))",
        text,
        re.IGNORECASE
    )
    if address_match:
        details["retailer_address"] = address_match.group(1).strip(" ,.")

    # --- Retailer Name ---
    retailer_match = re.search(
        r"(?:Best\s*regards|Regards|Warm\s*regards|Sincerely|Thanks)[: ,\-]*\s*([A-Za-z0-9&\.\-\s]+?(?:Industries|Enterprises|Company|Co\.|Ltd|Pvt\.|Corporation|Agency|Traders|Stores)?)",
        text,
        re.IGNORECASE
    )
    if retailer_match:
        details["retailer_name"] = retailer_match.group(1).strip(" ,.")
    else:
        # fallback: last organization/person detected
        doc = nlp(text)
        for ent in reversed(doc.ents):
            if ent.label_ in ("ORG", "PERSON") and len(ent.text.split()) > 1:
                details["retailer_name"] = ent.text.strip()
                break

    # --- Product ---
    product_match = re.search(
        r"(?:Product\s*Name|Product|Item)\s*[:\- ]+\s*(.+?)(?=\s*(?:Quantity|Qty|Due\s*Date|Delivery|units|$))",
        text,
        re.IGNORECASE
    )
    if product_match:
        details["product"] = product_match.group(1).strip(" ,.")
    elif subject:
        subject_match = re.search(
            r"(?:Order\s*for|Place\s*Order\s*for|Request\s*to\s*Purchase|PO\s*for)\s+(.+)",
            subject,
            re.IGNORECASE
        )
        if subject_match:
            details["product"] = subject_match.group(1).strip()

    # --- Quantity ---
    qty_match = re.search(r"(?:Quantity|Qty)\s*[:\- ]*\s*([0-9,\.]+)", text, re.IGNORECASE)
    if qty_match:
        details["quantity"] = qty_match.group(1).strip()
    else:
        for ent in nlp(text).ents:
            if ent.label_ == "CARDINAL" and ent.text.isdigit():
                details["quantity"] = ent.text.strip()
                break

    # --- Due Date ---
    date_match = re.search(
        r"(?:Due\s*Date|Delivery\s*Date|Required\s*by|Before|Need\s*by|Expected\s*delivery)\s*[:\- ]*\s*([A-Za-z0-9,\s\-\/]+)",
        text,
        re.IGNORECASE
    )
    parsed_date = None
    if date_match:
        parsed_date = dateparser.parse(date_match.group(1), settings={"PREFER_DATES_FROM": "future"})
    if not parsed_date:
        for ent in nlp(text).ents:
            if ent.label_ == "DATE":
                parsed_date = dateparser.parse(ent.text, settings={"PREFER_DATES_FROM": "future"})
                if parsed_date:
                    break
    if parsed_date:
        details["due_date"] = parsed_date.date().isoformat()

    return details
