#!/usr/bin/env python3
"""Generate a private local HTML contact sheet for textbook image review.

Images are rendered from the original authorized PDF and linked by relative
paths. Never publish this directory or attach it to public GitHub Actions.
"""
import argparse
import html
import json
from pathlib import Path

from render_image_asset import render_asset
from review_image_assets import create_review


def build_sheet(pdf, index_dir, output_dir, limit=100):
    index_dir, output_dir = Path(index_dir), Path(output_dir)
    if not 1 <= limit <= 500:
        raise ValueError("Invalid review limit")
    review = create_review(index_dir)
    assets = json.loads((index_dir / "image_assets.json").read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in assets[:limit]:
        aid = asset["asset_id"]
        # Identifier format is validated by render_asset before use as a path.
        target = output_dir / "previews" / (aid + ".png")
        render_asset(pdf, index_dir, aid, target)
        rows.append(
            "<article><img loading='lazy' src='previews/" + html.escape(aid, quote=True)
            + ".png' alt='PDF image placement'><p><code>" + html.escape(aid)
            + "</code> · PDF page " + str(asset["pdf_page"])
            + "</p><p>Review status: pending</p></article>"
        )
    style = ("body{font:16px system-ui;margin:2rem;max-width:1100px}"
             "main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem}"
             "article{border:1px solid #aaa;border-radius:8px;padding:1rem}"
             "img{max-width:100%;max-height:300px;object-fit:contain}"
             "code{overflow-wrap:anywhere}")
    page = ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Private image review</title><style>" + style + "</style>"
            "<h1>Private image review</h1>"
            "<p>Local only. Inspect images and record decisions in a separate review JSON. "
            "An image on the same page as a passage is not necessarily related.</p>"
            "<main>" + "".join(rows) + "</main></html>")
    (output_dir / "index.html").write_text(page, encoding="utf-8")
    review_path = output_dir / "review.json"
    if not review_path.exists():
        review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    return {"rendered": len(rows), "total": len(assets), "review_file": str(review_path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(build_sheet(args.pdf, args.index, args.out, args.limit), indent=2))


if __name__ == "__main__":
    main()
