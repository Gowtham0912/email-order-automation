import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import os

# --- Optional: set paths if needed ---
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# POPPLER_PATH = r"C:\Program Files\poppler-24.02.0\Library\bin"

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF using OCR for each page."""
    try:
        print(f"🧾 Extracting text from PDF: {pdf_path}")
        # Use poppler_path only if you installed it manually, otherwise remove param
        pages = convert_from_path(pdf_path)  # , poppler_path=POPPLER_PATH
        text = ""
        for i, page in enumerate(pages):
            text += f"\n--- PAGE {i+1} ---\n"
            text += pytesseract.image_to_string(page)
        text = text.strip()
        if text:
            print("✅ OCR extraction complete.")
        else:
            print("⚠️ No text detected in PDF (possible quality issue).")
        return text
    except Exception as e:
        print(f"❌ OCR Error for {pdf_path}: {e}")
        return ""


def extract_text_from_image(image_path):
    """Extract text from image files (JPG, PNG, TIFF, etc.)."""
    try:
        print(f"🖼️ Extracting text from image: {image_path}")
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        text = text.strip()
        if text:
            print("✅ Image OCR extraction complete.")
        else:
            print("⚠️ No readable text detected in image.")
        return text
    except Exception as e:
        print(f"❌ OCR Error for image {image_path}: {e}")
        return ""
