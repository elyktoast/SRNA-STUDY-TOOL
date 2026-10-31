"""Staging-only authenticated HTTP page-image preview.

This WSGI service deliberately DOES NOT issue inspection receipts or approve
pages: a completed application write cannot prove client delivery. Its purpose
is to deploy the real trusted PyMuPDF renderer safely before the receipt
acknowledgment protocol is designed and accepted.
"""
import hashlib
import json
import os
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from source_review_runtime_v2 import StagingReviewRuntime
from source_review_page_loader_v2 import load_verified_review_page
from source_review_manifest_r2_v2 import load_staging_review_manifest
from source_review_r2_loader_v2 import fetch_verified_staging_pdf

MAX_PATH = 2048
STAGING_ORIGIN = "https://staging.srnastudytool.com"


def response(start_response, status, payload, content_type="application/json", extra=()):
    headers = [("Content-Type", content_type), ("Cache-Control", "private, no-store"),
               ("X-Content-Type-Options", "nosniff"),
               ("X-Frame-Options", "DENY"),
               ("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"),
               ("Referrer-Policy", "no-referrer"),
               ("Content-Length", str(len(payload))),
               ("X-Review-Approval-Enabled", "false"), *extra]
    start_response(status, headers)
    return [payload]


def create_app(runtime):
    if not isinstance(runtime, StagingReviewRuntime):
        raise ValueError("Trusted staging runtime required")

    def app(environ, start_response):
        original_start_response = start_response

        def start_response(status, headers, exc_info=None):
            if environ.get("HTTP_ORIGIN") == STAGING_ORIGIN:
                headers = [*headers, ("Access-Control-Allow-Origin", STAGING_ORIGIN),
                           ("Access-Control-Expose-Headers",
                            "X-Review-Approval-Enabled, X-Verified-Source-SHA256, X-Page-Image-SHA256"),
                           ("Vary", "Origin")]
            if exc_info is None:
                return original_start_response(status, headers)
            return original_start_response(status, headers, exc_info)
        origin = environ.get("HTTP_ORIGIN")
        if origin and origin != STAGING_ORIGIN:
            return response(start_response, "403 Forbidden", b'{"error":"forbidden_origin"}')
        if environ.get("REQUEST_METHOD") == "OPTIONS":
            if origin != STAGING_ORIGIN or environ.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD") != "GET":
                return response(start_response, "403 Forbidden", b'{"error":"forbidden_preflight"}')
            return response(start_response, "204 No Content", b"", extra=[
                ("Access-Control-Allow-Methods", "GET"),
                ("Access-Control-Allow-Headers", "Authorization"),
                ("Access-Control-Max-Age", "300")])
        if environ.get("REQUEST_METHOD") != "GET":
            return response(start_response, "405 Method Not Allowed", b'{"error":"method_not_allowed"}')
        path = environ.get("PATH_INFO", "")
        if path == "/health":
            return response(start_response, "200 OK", b'{"ok":true,"environment":"staging","approval_enabled":false}')
        if path not in ("/review/page.png", "/review/manifest"):
            return response(start_response, "404 Not Found", b'{"error":"not_found"}')
        auth = environ.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Bearer ") or len(auth) > 8192:
            return response(start_response, "401 Unauthorized", b'{"error":"authentication_required"}')
        token = auth[7:]
        if not token or token != token.strip():
            return response(start_response, "401 Unauthorized", b'{"error":"authentication_required"}')
        query = environ.get("QUERY_STRING", "")
        if len(query) > MAX_PATH:
            return response(start_response, "400 Bad Request", b'{"error":"invalid_query"}')
        try:
            params = parse_qs(query, keep_blank_values=True, strict_parsing=True)
            if set(params) != ({"path"} if path == "/review/manifest" else {"path", "page"}):
                raise ValueError("Invalid query fields")
            if any(len(v) != 1 for v in params.values()):
                raise ValueError("Duplicate query parameter")
            key = params["path"][0]
            if path == "/review/page.png":
                raw_page = params["page"][0]
                if not raw_page.isascii() or not raw_page.isdecimal() or len(raw_page) > 8:
                    raise ValueError("Invalid PDF page")
                page_number = int(raw_page)
                if page_number < 1:
                    raise ValueError("Invalid PDF page")
            # Always authenticate before loading R2 metadata or PDF bytes.
            reviewer = runtime._reviewer(token)
        except ValueError:
            return response(start_response, "400 Bad Request", b'{"error":"invalid_request"}')
        except Exception:
            return response(start_response, "403 Forbidden", b'{"error":"forbidden"}')
        try:
            manifest = load_staging_review_manifest(
                runtime.r2, owner_uid=reviewer.uid, r2_key=key)
            if (manifest.get("owner_uid") != reviewer.uid or manifest.get("r2_key") != key
                    or not isinstance(manifest.get("sha256"), str)
                    or len(manifest["sha256"]) != 64
                    or type(manifest.get("pdf_page_count")) is not int
                    or manifest["pdf_page_count"] < 1):
                raise ValueError("Trusted manifest identity mismatch")
            if path == "/review/manifest":
                body = json.dumps({"source_sha256": manifest["sha256"],
                                   "pdf_page_count": manifest["pdf_page_count"],
                                   "approval_enabled": False}, separators=(",", ":")).encode()
                return response(start_response, "200 OK", body)
            if page_number > manifest["pdf_page_count"]:
                raise ValueError("Page outside verified manifest")
            source = fetch_verified_staging_pdf(
                runtime.r2, owner_uid=reviewer.uid, r2_key=key,
                expected_sha256=manifest["sha256"])
            page = load_verified_review_page(
                owner_uid=reviewer.uid, r2_key=key, pdf_page=page_number,
                manifest_loader=lambda owner, source_key: manifest,
                source_loader=lambda owner, source_key: source)
            png = page["png"]
            if (not isinstance(png, bytes) or not png.startswith(bytes([137, 80, 78, 71, 13, 10, 26, 10]))
                    or hashlib.sha256(png).hexdigest() != page["image_sha256"]
                    or page["source_sha256"] != manifest["sha256"]):
                raise ValueError("Rendered page integrity mismatch")
            return response(start_response, "200 OK", png, "image/png",
                            [("X-Verified-Source-SHA256", page["source_sha256"]),
                             ("X-Page-Image-SHA256", page["image_sha256"])])
        except ValueError:
            return response(start_response, "409 Conflict", b'{"error":"source_or_page_verification_failed"}')
        except Exception:
            return response(start_response, "503 Service Unavailable", b'{"error":"trusted_review_unavailable"}')
    return app


def main():
    # Reuse the WSGI entrypoint's strict staging identity checks. Never allow
    # the development server to bypass the deployment configuration guard.
    from source_review_wsgi_v2 import app
    # This server is only suitable for same-host private development.
    with make_server("127.0.0.1", int(os.environ.get("PORT", "8789")), app) as server:
        server.serve_forever()

if __name__ == "__main__":
    main()
