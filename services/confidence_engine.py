# services/confidence_engine.py

def calculate_confidence(details: dict) -> float:
    score = 0

    if details.get("product"):
        score += 25

    if details.get("quantity"):
        score += 25

    if details.get("due_date"):
        score += 20

    if details.get("retailer_name"):
        score += 15

    if details.get("retailer_email"):
        score += 10

    if details.get("retailer_address"):
        score += 5

    return round(score, 2)
