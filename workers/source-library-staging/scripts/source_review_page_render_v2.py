"""Trusted server-only PDF page rendering for staging inspection.

The caller must obtain PDF bytes from the authenticated owner's immutable
R2 source and independently resolve the expected source SHA-256 from trusted
storage. Never accept the expected digest from a browser request.
"""
import hashlib
import io

MAX_PDF_BYTES = 75 * 1024 * 1024
MAX_PIXELS = 16_000_000


def render_verified_pdf_page(pdf_bytes, *, expected_source_sha256, pdf_page, scale=1.5):
    """Return (PNG bytes, SHA-256 of PNG) for a verified physical PDF page.

    No receipt is issued here. A trusted delivery handler must successfully
    deliver these exact PNG bytes before registering a nonce and signing one.
    """
    import fitz
    if not isinstance(pdf_bytes, bytes) or not pdf_bytes or len(pdf_bytes) > MAX_PDF_BYTES:
        raise ValueError("Invalid or oversized source PDF")
    if not isinstance(expected_source_sha256, str) or len(expected_source_sha256) != 64 or any(
        c not in "0123456789abcdef" for c in expected_source_sha256
    ):
        raise ValueError("Invalid trusted source fingerprint")
    if hashlib.sha256(pdf_bytes).hexdigest() != expected_source_sha256:
        raise ValueError("Source PDF changed since review manifest")
    if type(pdf_page) is not int or pdf_page < 1:
        raise ValueError("Invalid physical PDF page")
    if type(scale) not in (int, float) or not 1 <= scale <= 2:
        raise ValueError("Invalid render scale")
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        if document.needs_pass or pdf_page > len(document):
            raise ValueError("Encrypted PDF or page outside source")
        page = document[pdf_page - 1]
        width = round(page.rect.width * scale)
        height = round(page.rect.height * scale)
        if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
            raise ValueError("Page exceeds render budget")
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        if pixmap.width * pixmap.height > MAX_PIXELS:
            raise ValueError("Rendered page exceeds pixel budget")
        png = pixmap.tobytes("png")
    return png, hashlib.sha256(png).hexdigest()
