import os
import magic  # optional to detect MIME
from .ocr_utils import ocr_pdf, ocr_image

def extract_text_from_attachment(path):
    path = str(path)
    ext = path.split('.')[-1].lower()
    if ext in ("pdf",):
        return ocr_pdf(path)
    elif ext in ("png","jpg","jpeg","tiff"):
        return ocr_image(path)
    elif ext in ("txt","eml"):
        with open(path, "r", errors="ignore") as f:
            return f.read()
    else:
        # fallback: try binary->ocr or return empty
        return ""
