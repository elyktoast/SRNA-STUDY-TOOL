#!/usr/bin/env python3
"""Loopback-only review editor for an already generated private contact sheet.

Start after build_image_review_sheet.py. No remote access, no image uploads.
"""
import argparse
import html
import json
import os
import tempfile
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from review_image_assets import validate_review, ALLOWED


def save_decision(index_dir, review_path, asset_id, decision):
    if decision not in ALLOWED or decision == "pending":
        raise ValueError("Invalid decision")
    review_path = Path(review_path)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    validate_review(index_dir, review)
    matches = [item for item in review["decisions"] if item["asset_id"] == asset_id]
    if len(matches) != 1:
        raise ValueError("Unknown image asset")
    matches[0]["decision"] = decision
    validate_review(index_dir, review)
    fd, temp_name = tempfile.mkstemp(prefix=".review-", suffix=".json", dir=review_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(review, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, review_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def serve(index_dir, sheet_dir, port=8765):
    index_dir, sheet_dir = Path(index_dir).resolve(), Path(sheet_dir).resolve()
    review_path = sheet_dir / "review.json"
    validate_review(index_dir, json.loads(review_path.read_text(encoding="utf-8")))
    assets = json.loads((index_dir / "image_assets.json").read_text(encoding="utf-8"))
    asset_ids = {a["asset_id"] for a in assets}
    csrf_token = secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/":
                review = json.loads(review_path.read_text(encoding="utf-8"))
                validate_review(index_dir, review)
                items = []
                for item in review["decisions"]:
                    aid = item["asset_id"]
                    if aid not in asset_ids:
                        continue
                    image = sheet_dir / "previews" / (aid + ".png")
                    if not image.is_file():
                        continue
                    controls = "".join(
                        "<button name='decision' value='" + html.escape(choice) + "'>" +
                        html.escape(choice.replace("_", " ")) + "</button> "
                        for choice in ("relevant", "decorative", "needs_review"))
                    items.append("<article><img src='/preview/" + html.escape(aid, quote=True) +
                                 "' alt='Source image'><p>" + html.escape(aid) +
                                 " — " + html.escape(item["decision"]) +
                                 "</p><form method='post' action='/decision'>" +
                                 "<input type='hidden' name='csrf_token' value='" + csrf_token + "'>" +
                                 "<input type='hidden' name='asset_id' value='" +
                                 html.escape(aid, quote=True) + "'>" + controls + "</form></article>")
                body = ("<!doctype html><html lang='en'><meta charset='utf-8'>"
                        "<title>Private textbook image review</title>"
                        "<style>body{font:16px system-ui;margin:2rem}"
                        "main{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem}"
                        "article{padding:1rem;border:1px solid #aaa}img{max-width:100%;max-height:260px}</style>"
                        "<h1>Private textbook image review</h1>"
                        "<p>Local only. Decisions describe image relevance, not verified passage matches.</p>"
                        "<main>" + "".join(items) + "</main></html>").encode()
                self.respond(200, "text/html; charset=utf-8", body)
            elif path.startswith("/preview/"):
                aid = path[len("/preview/"):]
                if aid not in asset_ids:
                    self.send_error(404)
                    return
                target = sheet_dir / "previews" / (aid + ".png")
                if not target.is_file() or target.is_symlink():
                    self.send_error(404)
                    return
                self.respond(200, "image/png", target.read_bytes())
            else:
                self.send_error(404)

        def do_POST(self):
            if urlsplit(self.path).path != "/decision":
                self.send_error(404)
                return
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                self.send_error(403)
                return
            if self.headers.get("Origin") not in (None, f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
                self.send_error(403)
                return
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/x-www-form-urlencoded":
                self.send_error(415)
                return
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= length <= 1024:
                    raise ValueError("Invalid payload size")
                fields = parse_qs(self.rfile.read(length).decode("utf-8"), strict_parsing=True)
                if set(fields) != {"asset_id", "decision", "csrf_token"} or any(len(v) != 1 for v in fields.values()):
                    raise ValueError("Invalid form")
                if not secrets.compare_digest(fields["csrf_token"][0], csrf_token):
                    raise ValueError("Invalid review form token")
                save_decision(index_dir, review_path, fields["asset_id"][0], fields["decision"][0])
            except (ValueError, UnicodeError, KeyError, json.JSONDecodeError):
                self.send_error(400)
                return
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def respond(self, code, mime, body):
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; form-action 'self'")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Private review: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--sheet", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(args.index, args.sheet, args.port)
