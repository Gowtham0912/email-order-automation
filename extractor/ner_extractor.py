import re
from typing import Dict, Optional, Tuple, List
import spacy
import dateparser
from dateparser.search import search_dates

nlp = spacy.load("en_core_web_sm")

LABELS = {
    "product": [
        r"\bproduct\s*name\b", r"\bproduct\b", r"\bitem\b",
    ],
    "quantity": [
        r"\bquantity\b", r"\bqty\b", r"\bq\.?t\.?y\.?\b"
    ],
    "due_date": [
        r"\bdue\s*date\b", r"\bdelivery\s*date\b", r"\brequired\s*by\b",
        r"\bneed\s*by\b", r"\bbefore\b", r"\bexpected\s*delivery\b"
    ],
    "address": [
        r"\bdelivery\s*location\b", r"\baddress\b", r"\bship\s*to\b", r"\bdeliver\s*to\b"
    ],
    "retailer_name": [
        r"\bretailer\s*name\b", r"\bcustomer\s*name\b", r"\bcompany\s*name\b"
    ],
    "email": [
        r"\bemail\b", r"\be-mail\b"
    ],
    "contact": [
        r"\bcontact\b", r"\bphone\b", r"\bmobile\b", r"\btel\b"
    ],
}

SEPARATORS = r"\s*(?:[:\-–—]|is|=)\s*"

STOP_AFTER_VALUE = re.compile(
    r"\b(?:kindly|thanks|thank\s*you|best|regards|email|contact|phone|mobile|subject)\b",
    re.IGNORECASE
)

def _normalize(text: str) -> str:
    # Fix OCR artifacts and collapse whitespace
    t = text.replace("\r", "\n")
    t = t.replace("\xa0", " ")
    # Remove hyphen line-break joins like 'Submersible-\nBorewell' → 'SubmersibleBorewell'
    t = re.sub(r"-\s*\n\s*", "", t)
    # Turn multiple newlines into single
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()

def _split_lines(text: str) -> List[str]:
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
    return [ln for ln in lines if ln]

def _match_label(line: str, patterns: List[str]) -> bool:
    for p in patterns:
        if re.search(p, line, re.IGNORECASE):
            return True
    return False

def _value_after_label(line: str) -> Optional[str]:
    # Grab value after "Label: value" / "Label - value" / "Label = value" / "Label is value"
    m = re.split(SEPARATORS, line, maxsplit=1)
    if len(m) == 2:
        val = m[1].strip(" ,.;")
        return val or None
    return None

def _extend_wrapped_value(idx: int, lines: List[str]) -> str:
    """If a value wraps to the next line(s), append them until a new label starts or a stop word appears."""
    val = _value_after_label(lines[idx]) or ""
    j = idx + 1
    while j < len(lines):
        nxt = lines[j]
        # ✅ fixed: remove 'any()' around _match_label()
        if _match_label(nxt, sum(LABELS.values(), [])) or STOP_AFTER_VALUE.search(nxt):
            break
        # Heuristic: if next line is short or looks like continuation, append
        if len(nxt) <= 80 or ("," in nxt or "-" in nxt):
            val += " " + nxt.strip(" ,.;")
            j += 1
        else:
            break
    return val.strip()


def _first_future_date(text: str) -> Optional[str]:
    # Prefer dates in the future
    try:
        hits = search_dates(text, settings={"PREFER_DATES_FROM": "future"})
        if not hits:
            return None
        # Choose the first hit that looks sensible (4-digit year preferred)
        for frag, dt in hits:
            if re.search(r"\b\d{4}\b", frag) or re.search(r"\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b", frag):
                return dt.date().isoformat()
        # Else return first parsed date
        return hits[0][1].date().isoformat()
    except Exception:
        return None

def _quantity_from_text(val: str) -> Optional[str]:
    # Extract numeric part; supports "150", "150 units", "100 pcs", "Qty: 75"
    m = re.search(r"\b(\d{1,7})(?:\s*(?:units?|pcs?|pieces?|nos?))?\b", val, re.IGNORECASE)
    return m.group(1) if m else None

def _email_from_text(text: str) -> Optional[str]:
    m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return m.group(0) if m else None

def _signature_name(lines: List[str]) -> Optional[str]:
    """
    Look for signature block: 'Best regards,' 'Regards,' 'Sincerely,' etc.
    Take 1–2 lines following as the name (skip lines that are obviously labels).
    """
    for i, ln in enumerate(lines):
        if re.search(r"\b(best\s*regards|regards|warm\s*regards|sincerely|thanks)\b", ln, re.IGNORECASE):
            # Consider next 1–2 lines as possible name/company
            for k in range(1, 3):
                if i + k < len(lines):
                    cand = lines[i + k].strip(" ,.;")
                    # skip if looks like a label line
                    if any(_match_label(cand, sum(LABELS.values(), []))):
                        continue
                    # require at least two tokens to avoid lone letters like "R"
                    if len(cand.split()) >= 2:
                        return cand
    return None

def extract_order_details(text: str, subject: Optional[str] = None) -> Dict[str, Optional[str]]:
    details = {
        "product": None,
        "quantity": None,
        "due_date": None,
        "retailer_name": None,
        "retailer_email": None,
        "retailer_address": None,
    }

    raw = _normalize(text)
    lines = _split_lines(raw)

    # Pass 1: key:value style extraction per line (robust for OCR)
    for i, ln in enumerate(lines):
        low = ln.lower()

        # PRODUCT
        if details["product"] is None and _match_label(low, LABELS["product"]):
            details["product"] = _extend_wrapped_value(i, lines)

        # QUANTITY
        if details["quantity"] is None and _match_label(low, LABELS["quantity"]):
            val = _extend_wrapped_value(i, lines)
            details["quantity"] = _quantity_from_text(val) or val

        # DUE DATE
        if details["due_date"] is None and _match_label(low, LABELS["due_date"]):
            segment = _extend_wrapped_value(i, lines)
            # parse just this segment first
            dt = dateparser.parse(segment, settings={"PREFER_DATES_FROM": "future"})
            if dt:
                details["due_date"] = dt.date().isoformat()

        # ADDRESS
        if details["retailer_address"] is None and _match_label(low, LABELS["address"]):
            addr = _extend_wrapped_value(i, lines)
            # Trim trailing stop phrases
            stop = STOP_AFTER_VALUE.search(addr)
            if stop:
                addr = addr[:stop.start()].strip(" ,.;")
            details["retailer_address"] = addr

        # RETAILER NAME (explicit label)
        if details["retailer_name"] is None and _match_label(low, LABELS["retailer_name"]):
            nm = _extend_wrapped_value(i, lines)
            # Remove trailing words that look like labels bleeding through
            nm = re.sub(r"\b(retailer\s*name|quantity|due\s*date|address|email)\b.*$", "", nm, flags=re.IGNORECASE).strip(" ,.;")
            # require at least 2 tokens to avoid "R"
            if len(nm.split()) >= 2:
                details["retailer_name"] = nm

        # RETAILER EMAIL (explicit label or anywhere)
        if details["retailer_email"] is None and (_match_label(low, LABELS["email"]) or "@" in ln):
            em = _email_from_text(ln)
            if em:
                details["retailer_email"] = em

    # Pass 2: subject-based product fallback
    if not details["product"] and subject:
        m = re.search(r"(?:order\s*for|place\s*order\s*for|po\s*for)\s+(.+)", subject, re.IGNORECASE)
        if m:
            details["product"] = m.group(1).strip(" .")

    # Pass 3: global fallbacks

    # Date fallback: scan whole text for any plausible future date
    if not details["due_date"]:
        details["due_date"] = _first_future_date(raw)

    # Quantity fallback: if not found near label, scan whole text
    if not details["quantity"]:
        m = re.search(r"\b(\d{1,7})\s*(?:units?|pcs?|pieces?|nos?)?\b", raw, re.IGNORECASE)
        if m:
            details["quantity"] = m.group(1)

    # Retailer email fallback
    if not details["retailer_email"]:
        details["retailer_email"] = _email_from_text(raw)

    # Retailer name fallback: signature block
    if not details["retailer_name"]:
        sig = _signature_name(lines)
        if sig and len(sig.split()) >= 2:
            details["retailer_name"] = sig

    # Last-resort NER fallback for retailer name
    if not details["retailer_name"]:
        doc = nlp(raw)
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PERSON") and len(ent.text.split()) >= 2:
                details["retailer_name"] = ent.text.strip()
                break

    # Final cleanup: prevent label leakage like "Tamil Nadu Retailer Name"
    if details["retailer_name"]:
        details["retailer_name"] = re.sub(
            r"\b(retailer\s*name|quantity|due\s*date|address|email)\b.*$",
            "", details["retailer_name"], flags=re.IGNORECASE
        ).strip(" ,.;")

    return details
