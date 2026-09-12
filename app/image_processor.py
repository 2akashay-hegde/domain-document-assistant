import os
from typing import Dict, Any
from PIL import Image, ExifTags

def extract_image_info_and_text(file_path: str) -> Dict[str, Any]:
    """
    Extract comprehensive metadata and OCR text from an image file.
    
    Returns a dictionary containing:
    - filename, format, width, height, color_mode, file_size_kb, aspect_ratio, dpi
    - exif: metadata dict (if available)
    - ocr_text: extracted text from image (if present)
    - summary_text: combined text for RAG vector embedding
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")

    filename = os.path.basename(file_path)
    file_size_bytes = os.path.getsize(file_path)
    file_size_kb = round(file_size_bytes / 1024, 2)

    with Image.open(file_path) as img:
        img_format = img.format or os.path.splitext(filename)[1].replace(".", "").upper()
        width, height = img.size
        color_mode = img.mode
        dpi = img.info.get("dpi", (72, 72))

        aspect_ratio = f"{round(width / height, 2)}:1" if height else "N/A"

        # Extract EXIF metadata if present
        exif_data = {}
        try:
            raw_exif = img._getexif()
            if raw_exif:
                for tag_id, val in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    if isinstance(val, (str, int, float)):
                        exif_data[str(tag_name)] = val
        except Exception:
            pass

    # Extract OCR text using RapidOCR (with pytesseract & PyMuPDF fallback)
    ocr_text = ""
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        result, _ = engine(file_path)
        if result:
            lines = [item[1].strip() for item in result if len(item) >= 2 and item[1] and item[1].strip()]
            ocr_text = "\n".join(lines)
    except Exception as e:
        print(f"[OCR Warning] RapidOCR failed: {e}")

    if not ocr_text:
        try:
            import pytesseract
            with Image.open(file_path) as img:
                ocr_text = pytesseract.image_to_string(img).strip()
        except Exception:
            pass

    if not ocr_text:
        try:
            import fitz
            doc = fitz.open(file_path)
            if len(doc) > 0:
                ocr_text = doc[0].get_text().strip()
            doc.close()
        except Exception:
            pass

    if not ocr_text:
        ocr_text = "(No visible text detected via OCR in this image)"

    # Build comprehensive summary text representation for embedding & LLM context
    summary_lines = [
        f"Image File Information for: {filename}",
        f"- Format: {img_format}",
        f"- Dimensions: {width} x {height} pixels",
        f"- Aspect Ratio: {aspect_ratio}",
        f"- Color Mode: {color_mode}",
        f"- File Size: {file_size_kb} KB",
        f"- Resolution (DPI): {dpi[0]} x {dpi[1]}"
    ]

    if exif_data:
        summary_lines.append("- EXIF Properties:")
        for k, v in list(exif_data.items())[:10]:
            summary_lines.append(f"  • {k}: {v}")

    summary_lines.append(f"\nExtracted Image Text (OCR):\n{ocr_text}")

    summary_text = "\n".join(summary_lines)

    return {
        "filename": filename,
        "format": img_format,
        "width": width,
        "height": height,
        "color_mode": color_mode,
        "file_size_kb": file_size_kb,
        "aspect_ratio": aspect_ratio,
        "dpi": dpi,
        "exif": exif_data,
        "ocr_text": ocr_text,
        "summary_text": summary_text
    }
