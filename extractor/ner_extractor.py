# extractor/ner_extractor.py
import re
from typing import Dict, Optional, List
import spacy
import dateparser
from dateparser.search import search_dates

nlp = spacy.load("en_core_web_sm")

MONTHS = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"

LABELS = {
    "product":   [r"\bproduct\s*name\b", r"\bproduct\b", r"\bitem\b", r"\bmodel\b"],
    "quantity":  [r"\bquantity\b", r"\bqty\b", r"\bq\.?t\.?y\.?\b", r"\bunits?\b", r"\bpcs?\b"],
    "due_date":  [r"\bdue\s*date\b", r"\bdelivery\s*date\b", r"\brequired\s*by\b", r"\bneed\s*by\b",
                  r"\bdue\s*by\b", r"\bdue\s*on\b", r"\bon\s*or\s*before\b", r"\bdeliver(?:ed)?\s*by\b", r"\bbefore\b", r"\bby\b"],
    "address":   [r"\bdelivery\s*location\b", r"\baddress\b", r"\bship\s*to\b", r"\bdeliver\s*to\b",
                  r"\blocation\b", r"\bshipping\s*address\b", r"\bbilling\s*address\b"],
    "retailer_name": [r"\bretailer\s*name\b", r"\bcontact\s*person\b", r"\bcustomer\s*name\b",
                      r"\bcompany\s*name\b", r"\bname\b"],
    "email":     [r"\bemail\b", r"\be-mail\b", r"@"],
}

DATE_PATTERNS = [
    rf"\b\d{{1,2}}[\/\-]\d{{1,2}}[\/\-]\d{{2,4}}\b",           # 14-11-2025 / 14/11/25
    rf"\b\d{{4}}[\/\-]\d{{1,2}}[\/\-]\d{{1,2}}\b",             # 2025-11-14
    rf"\b\d{{1,2}}\s+{MONTHS}\s+\d{{4}}\b",                    # 14 November 2025
    rf"\b{MONTHS}\s+\d{{1,2}},?\s+\d{{4}}\b",                  # Nov 14, 2025
]

STOP_MARK = re.compile(r"\b(thanks|thank\s*you|best|regards|email|contact|phone|mobile|subject)\b", re.I)

WORD_NUM = {
    "a": "1", "an": "1", "one": "1", "single": "1",
    "two": "2", "couple": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"
}

# ---------- utilities ----------
def _normalize(text: str) -> str:
    t = (text or "").replace("\r", "\n").replace("\xa0", " ")
    t = re.sub(r"-\s*\n\s*", "", t)     # join hyphenated line breaks
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()

def _split_lines(text: str) -> List[str]:
    return [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n") if ln.strip()]

def _kv_value(line: str, patterns: List[str]) -> Optional[str]:
    """
    Match only true labeled lines:  <label> [: - — = is] <value>
    Avoid triggering just because a word like 'product' appears in a sentence.
    """
    for p in patterns:
        m = re.search(rf"({p})\s*(?:[:\-–—=]|(?:\s+is\b))\s*(.+)$", line, re.I)
        if m:
            val = m.group(2).strip(" ,.;")
            return val or None
    return None

def _extend_wrapped_value(i: int, lines: List[str], acc: str) -> str:
    """Carry value to following continuation lines until a new label or stop word."""
    val = acc
    j = i + 1
    while j < len(lines):
        nxt = lines[j]
        if STOP_MARK.search(nxt):
            break
        # stop if the next line looks like a new labeled field
        if any(_kv_value(nxt, pats) for pats in LABELS.values()):
            break
        if len(nxt) <= 80 or "," in nxt:
            val += " " + nxt.strip(" ,.;")
            j += 1
        else:
            break
    return val.strip()

def _email(text: str) -> Optional[str]:
    m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text or "")
    return m.group(0) if m else None

def _strict_parse_date(fragment: str) -> Optional[str]:
    if not fragment:
        return None
    try:
        dt = dateparser.parse(
            fragment,
            settings={"STRICT_PARSING": True, "PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
            languages=["en"],
        )
        return dt.date().isoformat() if dt else None
    except Exception:
        try:
            dt = dateparser.parse(fragment, settings={"PREFER_DATES_FROM": "future"}, languages=["en"])
            return dt.date().isoformat() if dt else None
        except Exception:
            return None

def _find_best_date(text: str) -> Optional[str]:
    if not text:
        return None
    # 1) look near cues
    cue = re.search(r"(?:on\s*or\s*before|due\s*(?:on|by)|required\s*by|deliver(?:ed)?\s*by|before|by)\s+(.{0,60})", text, re.I)
    if cue:
        frag = cue.group(1)
        for pat in DATE_PATTERNS:
            m = re.search(pat, frag, re.I)
            if m:
                parsed = _strict_parse_date(m.group(0))
                if parsed:
                    return parsed
    # 2) scan entire text
    for pat in DATE_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            parsed = _strict_parse_date(m.group(0))
            if parsed:
                return parsed
    # 3) final strict search
    try:
        hits = search_dates(text, settings={"STRICT_PARSING": True, "PREFER_DATES_FROM": "future"}, languages=["en"])
        if hits:
            for frag, dt in hits:
                if re.search(r"[/-]|\b"+MONTHS+r"\b", frag, re.I):
                    return dt.date().isoformat()
            return hits[0][1].date().isoformat()
    except Exception:
        pass
    return None

def _quantity(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"\b(?:qty|quantity|units?|pcs?|pieces?|nos?)\b\D{0,5}(\d{1,5})\b", text, re.I)
    if m:
        return m.group(1)
    m = re.search(r"\b(?:need|want|buy|order|purchase)\s*(?:only\s*)?(\d{1,5}|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\b", text, re.I)
    if m:
        v = m.group(1).lower()
        return WORD_NUM.get(v, v)
    m = re.search(r"\b(\d{1,5})\s*(?:units?|pcs?|pieces?|nos?)\b", text, re.I)
    if m:
        return m.group(1)
    return None

def _name_conversational(text: str) -> Optional[str]:
    m = re.search(r"(?:my\s*name\s*is|this\s*is)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"\bI\s*am\s+(?!from\b)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", text)
    if m:
        return m.group(1).strip()
    return None

def _name_signature(lines: List[str]) -> Optional[str]:
    for ln in lines[-6:]:
        if "@" in ln or re.search(r"\d", ln):
            continue
        if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}$", ln.strip()):
            return ln.strip()
    return None

def _address(text: str) -> Optional[str]:
    m = re.search(r"(?:i\s*am\s*from|located\s*at|based\s*in)\s*([A-Za-z0-9,\- ]+)", text, re.I)
    if m:
        return m.group(1).strip(" ,.;")
    m = re.search(r"(?:address|deliver\s*to|delivery\s*location|ship\s*to)\s*[:\-–—=]?\s*([^\n\.]+)", text, re.I)
    if m:
        return m.group(1).strip(" ,.;")
    return None

def _product(text: str) -> Optional[str]:
    # true labeled product
    m = re.search(r"(?:product\s*name|product|item|model)\s*[:\-–—=]\s*([^\n,\.]+)", text, re.I)
    if m:
        return m.group(1).strip(" ,.;")
    # conversational: carefully bounded, stop at comma/period/“i need/need/on or before/by”
    m = re.search(
        r"(?:i\s*(?:want|need|would\s*like|am\s*looking\s*for|want\s*to\s*buy)\s*(?:the\s*)?(?:product|item)?(?:\s*(?:namely|called))?\s+)"
        r"([A-Za-z0-9][A-Za-z0-9\s\-\&\(\)\/]+?)"
        r"(?:\s*,|\s*\.\s*|\s+and\s+i\s+need|\s+i\s+need|\s+on\s+or\s+before|\s+by\b|\n|$)",
        text, re.I
    )
    if m:
        return m.group(1).strip(" ,.;")
    return None

# -------------- main --------------
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

    # PASS 1: only real labeled key:value lines
    for i, ln in enumerate(lines):
        # product
        if not details["product"]:
            v = _kv_value(ln, LABELS["product"])
            if v:
                details["product"] = _extend_wrapped_value(i, lines, v)
                continue
        # quantity
        if not details["quantity"]:
            v = _kv_value(ln, LABELS["quantity"])
            if v:
                details["quantity"] = _quantity(v) or v
        # due date
        if not details["due_date"]:
            v = _kv_value(ln, LABELS["due_date"])
            if v:
                dt = _find_best_date(v)
                if dt:
                    details["due_date"] = dt
        # address
        if not details["retailer_address"]:
            v = _kv_value(ln, LABELS["address"])
            if v:
                details["retailer_address"] = _extend_wrapped_value(i, lines, v)
        # name
        if not details["retailer_name"]:
            v = _kv_value(ln, LABELS["retailer_name"])
            if v and len(v.split()) >= 1:
                details["retailer_name"] = re.sub(r"\b(retailer|customer|company|name)\b", "", v, flags=re.I).strip(" ,.;")
        # email anywhere
        if not details["retailer_email"]:
            em = _email(ln)
            if em:
                details["retailer_email"] = em

    # PASS 2: conversational/full-text fallbacks
    if not details["product"]:
        details["product"] = _product(raw)
    if not details["quantity"]:
        details["quantity"] = _quantity(raw)
    if not details["due_date"]:
        details["due_date"] = _find_best_date(raw)
    if not details["retailer_address"]:
        details["retailer_address"] = _address(raw)
    if not details["retailer_email"]:
        details["retailer_email"] = _email(raw)
    if not details["retailer_name"]:
        details["retailer_name"] = _name_conversational(raw) or _name_signature(lines)
    if not details["retailer_name"]:
        # last resort: spaCy ORG/PERSON
        for ent in nlp(raw).ents:
            if ent.label_ in ("ORG", "PERSON") and len(ent.text.split()) >= 1:
                details["retailer_name"] = ent.text.strip()
                break

    # PASS 3: subject help
    if subject and not details["product"]:
        m = re.search(r"(?:order\s*for|place\s*order\s*for|places?\s+new\s+order\s*for|po\s*for)\s+(.+)", subject, re.I)
        if m:
            details["product"] = m.group(1).strip(" .")
    if subject and not details["due_date"]:
        maybe = _find_best_date(subject)
        if maybe:
            details["due_date"] = maybe

    # Cleanups
    if details["product"]:
        details["product"] = re.sub(r"\b(i\s*want|need|product|item|model|called|namely|to\s*buy)\b", "", details["product"], flags=re.I).strip(" ,.;")
    if details["retailer_address"]:
        details["retailer_address"] = re.sub(r"\b(address|deliver\s*to|delivery\s*location|ship\s*to|located\s*at|based\s*in|i\s*am\s*from)\b", "", details["retailer_address"], flags=re.I).strip(" ,.;")
    if details["retailer_name"]:
        details["retailer_name"] = re.sub(r"\b(my\s*name\s*is|this\s*is|i\s*am)\b", "", details["retailer_name"], flags=re.I).strip(" ,.;")

    return details
