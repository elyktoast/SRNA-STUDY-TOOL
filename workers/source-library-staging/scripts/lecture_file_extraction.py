"""Read-only lecture extraction using the textbook PDF parser's PyMuPDF dependency.

Never silently treat image-only slides as complete text. OCR must be run by
an explicitly configured trusted worker before planning such slides.
"""
from io import BytesIO

MAX_LECTURE_BYTES = 25 * 1024 * 1024
MAX_LECTURE_PAGES = 500

def extract_lecture(data, filename):
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_LECTURE_BYTES:
        raise ValueError("Lecture file is empty or exceeds 25 MB")
    if not isinstance(filename, str) or len(filename) > 255:
        raise ValueError("Invalid filename")
    name = filename.lower()
    if name.endswith(".pdf"):
        if not data.startswith(b"%PDF-"):
            raise ValueError("PDF signature mismatch")
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        try:
            if doc.needs_pass or not 1 <= len(doc) <= MAX_LECTURE_PAGES:
                raise ValueError("Encrypted or oversized PDF")
            pages = []
            for i, page in enumerate(doc):
                value = page.get_text("text", sort=True).strip()
                images = len(page.get_images(full=True))
                pages.append({"page": i + 1, "text": value,
                              "needs_visual_review": not bool(value) or (images > 0 and len(value) < 100),
                              "image_count": images})
        finally:
            doc.close()
        kind = "pdf"
    elif name.endswith(".pptx"):
        if data[:2] != b"PK":
            raise ValueError("PowerPoint signature mismatch")
        from pptx import Presentation
        prs = Presentation(BytesIO(data))
        if not 1 <= len(prs.slides) <= MAX_LECTURE_PAGES:
            raise ValueError("Oversized presentation")
        pages = []
        for i, slide in enumerate(prs.slides):
            chunks = []
            images = 0
            for shape in slide.shapes:
                if shape.has_text_frame:
                    chunks.extend(p.text for p in shape.text_frame.paragraphs if p.text.strip())
                if shape.has_table:
                    for row in shape.table.rows:
                        chunks.append(" | ".join(cell.text for cell in row.cells))
                if shape.shape_type == 13:
                    images += 1
            value = "\n".join(chunks).strip()
            pages.append({"page": i + 1, "text": value,
                          "needs_visual_review": not bool(value) or (images > 0 and len(value) < 100),
                          "image_count": images})
        kind = "pptx"
    else:
        raise ValueError("Only PDF and PPTX lectures are supported")
    review_pages = [p["page"] for p in pages if p["needs_visual_review"]]
    return {"format": kind, "filename": filename, "page_count": len(pages),
            "pages": pages, "requires_ocr_or_visual_review": bool(review_pages),
            "review_pages": review_pages, "extraction_complete": not bool(review_pages),
            "database_writes": False, "provider_calls": False}
