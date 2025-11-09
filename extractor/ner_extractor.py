import spacy
nlp = spacy.load("en_core_web_sm")

def extract_order_details(text):
    doc = nlp(text)
    details = {"product": None, "quantity": None, "due_date": None}

    for ent in doc.ents:
        if ent.label_ == "DATE":
            details["due_date"] = ent.text
        elif ent.label_ == "CARDINAL":
            details["quantity"] = ent.text
        elif ent.label_ == "ORG" or ent.label_ == "PRODUCT":
            details["product"] = ent.text
    return details
