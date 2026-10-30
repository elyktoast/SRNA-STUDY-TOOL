#!/usr/bin/env python3
"""Local-only human review packet. Never upload it to CI artifacts or a database."""
import html
import json
from pathlib import Path

def render_review_html(groups, pdf_name):
    """Escape PDF-derived headings; keep decisions unapproved by default."""
    rows = []
    for index, group in enumerate(groups, 1):
        options = []
        for c in group["candidates"]:
            title = html.escape(c["heading"], quote=True)
            options.append(f'<li>PDF p. {c["pdf_page"]} · {html.escape(c["detector"])} · {title}</li>')
        rows.append(
            f'<section><h2>Group {index}: PDF pages {group["first_page"]}–{group["last_page"]}</h2>'
            + '<ul>' + ''.join(options) + '</ul>'
            + '<label>Decision <select><option>Needs review</option><option>Chapter</option>'
              '<option>Subsection</option><option>Reject</option></select></label>'
            + '<label>Notes <textarea placeholder="Review notes (local only)"></textarea></label></section>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Chapter candidate review</title><style>'
            'body{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}'
            'section{border:1px solid #aaa;border-radius:10px;padding:1rem;margin:1rem 0}'
            'label{display:block;margin-top:.75rem}textarea{display:block;width:95%;min-height:3rem}'
            '</style><h1>Unverified chapter candidates</h1><p>Source: '
            + html.escape(pdf_name, quote=True)
            + '</p><p>This is a local visual review only. Selection does not save, approve,'
              ' or import anything. Record decisions separately after checking the PDF.</p>'
            + ''.join(rows) + '</html>')

def write_local_review(groups, pdf_name, destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("Refusing to overwrite an existing review")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_review_html(groups, pdf_name), encoding="utf-8")
    return destination
