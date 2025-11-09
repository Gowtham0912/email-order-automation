from datetime import datetime

def validate_extracted(data):
    issues = []

    # Validate quantity
    if not data.get("quantity"):
        issues.append("Missing quantity")
    else:
        try:
            q = int(data["quantity"])
            if q <= 0:
                issues.append("Quantity <= 0")
        except:
            issues.append("Quantity not numeric")

    # Validate due date
    if data.get("due_date"):
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                dt = datetime.strptime(data["due_date"], fmt)
                data["due_date_parsed"] = dt.isoformat()
                break
            except:
                pass
        if not data.get("due_date_parsed"):
            issues.append("Invalid due date format")

    return issues
