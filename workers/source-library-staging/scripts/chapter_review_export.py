#!/usr/bin/env python3
"""Local-only human review packet. Never upload it to CI artifacts or a database."""
import html
from pathlib import Path
from chapter_review import review_fingerprint

def render_review_html(groups, pdf_name):
    """Escape PDF-derived headings; keep decisions unapproved by default."""
    fingerprint = review_fingerprint(groups)
    rows = []
    for index, group in enumerate(groups, 1):
        options = []
        for c in group["candidates"]:
            title = html.escape(c["heading"], quote=True)
            options.append(f'<li>PDF p. {c["pdf_page"]} · {html.escape(c["detector"])} · {title}</li>')
        rows.append(
            f'<section data-group="{index}"><h2>Group {index}: PDF pages {group["first_page"]}–{group["last_page"]}</h2>'
            + '<ul>' + ''.join(options) + '</ul>'
            + '<label>Decision <select class="decision"><option>Needs review</option><option>Chapter</option>'
              '<option>Subsection</option><option>Reject</option></select></label>'
            + '<label>Notes <textarea class="notes" placeholder="Review notes (local only)"></textarea></label></section>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Chapter candidate review</title><style>'
            'body{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}'
            'section{border:1px solid #aaa;border-radius:10px;padding:1rem;margin:1rem 0}'
            'label{display:block;margin-top:.75rem}textarea{display:block;width:95%;min-height:3rem}'
            '</style><h1>Unverified chapter candidates</h1><p>Source: '
            + html.escape(pdf_name, quote=True)
            + '</p><p>This is a local visual review only. Selection does not save, approve,'
              ' or import anything automatically. Export decisions after checking the PDF.</p>'
            + '<button id="export" type="button">Export review decisions (JSON)</button>'
            + ''.join(rows) + '<script>'
              'document.getElementById("export").addEventListener("click",()=>{' 
              'const decisions=Array.from(document.querySelectorAll("section[data-group]")).map(s=>({'
              'group:Number(s.dataset.group),decision:s.querySelector(".decision").value,'
              'notes:s.querySelector(".notes").value}));'
              'const blob=new Blob([JSON.stringify({schema_version:2,review_fingerprint:"' + fingerprint + '",decisions},null,2)],'
              '{type:"application/json"});const url=URL.createObjectURL(blob);'
              'const a=document.createElement("a");a.href=url;a.download="chapter-review-decisions.json";'
              'a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});'
              '</script></html>')

def write_local_review(groups, pdf_name, destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("Refusing to overwrite an existing review")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_review_html(groups, pdf_name), encoding="utf-8")
    return destination
