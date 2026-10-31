#!/usr/bin/env python3
"""Review-only PDF typography candidates. Never assigns sections or verifies citations."""
import re
from collections import Counter

NUMBER = re.compile(r"^(?:chapter\s+)?(?:[0-9]{1,3}|[IVXLCDM]{1,8})(?:[.:-]\s*|\s+)", re.I)
EXCLUDE = {"contents", "references", "index", "bibliography", "preface", "foreword"}
def propose_layout(pdf):
    import fitz
    with fitz.open(pdf) as doc:
        page_lines = []
        sizes = Counter()
        for i in range(len(doc)):
            page = doc.load_page(i)
            lines = []
            for block in page.get_text("dict").get("blocks", []):
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    spans = [s for s in line["spans"] if s["text"].strip()]
                    if not spans:
                        continue
                    text = " ".join(s["text"].strip() for s in spans)
                    size = max(float(s["size"]) for s in spans)
                    bold = any("bold" in s.get("font", "").lower() for s in spans)
                    y = min(float(s["bbox"][1]) for s in spans)
                    lines.append((y, text, size, bold))
                    if len(text) >= 35:
                        sizes[round(size, 1)] += len(text)
            page_lines.append(sorted(lines))
        body = sizes.most_common(1)[0][0] if sizes else 12.0
        candidates = []
        for i, lines in enumerate(page_lines):
            for y, title, size, bold in lines[:16]:
                t = title.strip()
                if not (5 <= len(t) <= 100 and len(t.split()) <= 12):
                    continue
                if t.casefold() in EXCLUDE or t.endswith((".", "?", "!")):
                    continue
                if not re.search(r"[A-Za-z]", t):
                    continue
                if not (size >= body * 1.3 or (bold and size >= body * 1.12)):
                    continue
                if y > 0.48 * doc[i].rect.height:
                    continue
                if not (NUMBER.match(t) or size >= body * 1.65):
                    continue
                candidates.append({"pdf_page": i + 1, "heading": t, "font_size": round(size, 1),
                                   "body_size": body, "source": "unverified_layout_heuristic",
                                   "review_required": True})
                break
        return candidates
