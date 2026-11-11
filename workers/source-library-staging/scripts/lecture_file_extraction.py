"""Read-only lecture extraction using the textbook PDF parser's PyMuPDF dependency.

Never silently treat image-only slides as complete text. OCR must be run by
an explicitly configured trusted worker before planning such slides.
"""
from io import BytesIO
from zipfile import ZipFile, BadZipFile

MAX_LECTURE_BYTES = 25 * 1024 * 1024
MAX_LECTURE_PAGES = 500

def extract_lecture(data, filename, *, enable_ocr=False):
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
                if enable_ocr and (not value or (images and len(value) < 100)):
                    try:
                        ocr_page = page.get_textpage_ocr(language="eng", dpi=180, full=False)
                        ocr_text = page.get_text("text", textpage=ocr_page, sort=True).strip()
                        if len(ocr_text) > len(value):
                            value = ocr_text
                    except (RuntimeError, OSError):
                        pass  # Missing Tesseract or failed OCR remains flagged for review.
                pages.append({"page": i + 1, "text": value,
                              "needs_visual_review": not bool(value) or images > 0,
                              "image_count": images})
        finally:
            doc.close()
        kind = "pdf"
    elif name.endswith(".pptx"):
        if data[:2] != b"PK":
            raise ValueError("PowerPoint signature mismatch")
        # Inspect the OOXML container before handing it to the PowerPoint parser.
        # Prevent compressed archive bombs and unsupported macro-enabled files.
        try:
            with ZipFile(BytesIO(data)) as archive:
                members = archive.infolist()
                if len(members) > 3000 or sum(x.file_size for x in members) > 150 * 1024 * 1024:
                    raise ValueError("Presentation expanded size exceeds safe limit")
                if any(x.filename.startswith("/") or ".." in x.filename.split("/")
                       or x.flag_bits & 0x1 for x in members):
                    raise ValueError("Unsafe or encrypted presentation archive")
                if "[Content_Types].xml" not in archive.namelist() or "ppt/presentation.xml" not in archive.namelist():
                    raise ValueError("Not a valid PowerPoint presentation")
        except BadZipFile as exc:
            raise ValueError("Invalid PowerPoint archive") from exc
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
                    if enable_ocr:
                        try:
                            import fitz
                            image_doc = fitz.open(stream=shape.image.blob,
                                                  filetype=shape.image.ext)
                            try:
                                ocr_page = image_doc[0]
                                ocr_textpage = ocr_page.get_textpage_ocr(language="eng", dpi=180)
                                ocr_text = ocr_page.get_text("text", textpage=ocr_textpage).strip()
                                if ocr_text:
                                    chunks.append("[Image OCR; verify against slide] " + ocr_text)
                            finally:
                                image_doc.close()
                        except (RuntimeError, OSError, ValueError):
                            pass
            # Speaker notes often contain instructor context missing from slide text.
            if slide.has_notes_slide:
                notes = slide.notes_slide.notes_text_frame
                if notes is not None:
                    note_text = notes.text.strip()
                    if note_text:
                        chunks.append("[Speaker notes] " + note_text)
            value = "\n".join(chunks).strip()
            pages.append({"page": i + 1, "text": value,
                          "needs_visual_review": not bool(value) or images > 0,
                          "image_count": images})
        kind = "pptx"
    else:
        raise ValueError("Only PDF and PPTX lectures are supported")
    review_pages = [p["page"] for p in pages if p["needs_visual_review"]]
    return {"format": kind, "filename": filename, "page_count": len(pages),
            "pages": pages, "requires_ocr_or_visual_review": bool(review_pages),
            "review_pages": review_pages, "extraction_complete": not bool(review_pages), "ocr_requested": bool(enable_ocr),
            "database_writes": False, "provider_calls": False}
