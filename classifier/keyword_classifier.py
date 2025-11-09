ORDER_KEYWORDS = [
    "place order", "purchase order", "po#", "po #", "purchase", "order request",
    "order placed", "request to ship", "please supply", "need", "quantity"
]

def is_order_email(text):
    t = text.lower()
    for kw in ORDER_KEYWORDS:
        if kw in t:
            return True
    return False
