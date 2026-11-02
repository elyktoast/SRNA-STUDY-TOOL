#!/usr/bin/env python3
"""Render one source-linked PDF image placement for authorized local review.

No network, no public artifact uploads, and no persistence beyond the caller's
chosen local output. The PDF must already be obtained through an authorized
owner-scoped process. Metadata is untrusted and validated before rendering.
"""
import argparse
import json
import re
from pathlib import Path


def render_asset(pdf_path, index_dir, asset_id, output_path):
    import fitz
    pdf_path, index_dir, output_path = map(Path, (pdf_path, index_dir, output_path))
    if not re.fullmatch(r"p[0-9]{4,}-x[0-9]+-n[0-9]+", asset_id):
        raise ValueError("Invalid asset identifier")
    assets = json.loads((index_dir / "image_assets.json").read_text(encoding="utf-8"))
    matches = [a for a in assets if isinstance(a, dict) and a.get("asset_id") == asset_id]
    if len(matches) != 1:
        raise ValueError("Asset reference not unique or missing")
    asset = matches[0]
    page_number, xref, placement = asset.get("pdf_page"), asset.get("pdf_xref"), asset.get("placement")
    if (type(page_number) is not int or type(xref) is not int or type(placement) is not int
            or page_number < 1 or xref < 1 or placement < 1
            or asset.get("source") != "original_pdf"):
        raise ValueError("Invalid asset provenance")
    if asset_id != f"p{page_number:04d}-x{xref}-n{placement}":
        raise ValueError("Asset identifier and provenance disagree")
    with fitz.open(pdf_path) as doc:
        if page_number > len(doc):
            raise ValueError("Asset page outside PDF")
        page = doc[page_number - 1]
        if xref not in {info[0] for info in page.get_images(full=True)}:
            raise ValueError("Image not present on source page")
        rects = page.get_image_rects(xref)
        if placement > len(rects):
            raise ValueError("Image placement missing")
        rect = rects[placement - 1] & page.rect
        stored = asset.get("bbox")
        if (not isinstance(stored, list) or len(stored) != 4
                or any(type(v) not in (int, float) for v in stored)
                or any(abs(float(a) - float(b)) > 0.02 for a, b in zip(stored, rect))):
            raise ValueError("Asset geometry does not match source PDF")
        if rect.is_empty:
            raise ValueError("Empty image placement")
        # Render the visible page placement (not a potentially misleading raw
        # xref, which may rely on masks or PDF transformations).
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), clip=rect, alpha=False)
        if pix.width * pix.height > 16_000_000:
            raise ValueError("Rendered asset exceeds pixel budget")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(output_path))
    return output_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    render_asset(args.pdf, args.index, args.asset_id, args.out)


if __name__ == "__main__":
    main()
