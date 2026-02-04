# services/validate_service.py
from datetime import datetime


def validate_extracted(data):
    issues = []

    # ---- Quantity ----
    if not data.get("quantity"):
        issues.append("Missing quantity")
    else:
        try:
            q = float(data["quantity"])
            if q <= 0:
                issues.append("Quantity <= 0")
        except:
            issues.append("Quantity not numeric")

    # ---- Unit ----
    if not data.get("unit"):
        issues.append("Missing unit")

    # ---- Due Date ----
    if data.get("due_date"):
        parsed = False
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                dt = datetime.strptime(data["due_date"], fmt)
                data["due_date_parsed"] = dt.isoformat()
                parsed = True
                break
            except:
                pass
        if not parsed:
            issues.append("Invalid due date format")

    return issues
