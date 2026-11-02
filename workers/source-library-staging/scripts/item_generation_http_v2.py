"""Authenticated, staging-only WSGI bridge for indexed question generation.

Mount in a trusted Python service with staging PostgreSQL; never in the
Cloudflare upload Worker. Defaults to evidence-only preflight, no model calls.
"""
import json
from uuid import UUID

from run_grounded_generation_v2 import execute

MAX_BODY = 8192
FIELDS = {"topic", "mode", "domain", "section", "objective", "format",
          "item_id", "textbook_id", "section_id", "include_subsections",
          "page_start", "page_end", "limit", "execute", "confirm_paid_calls"}
REQUIRED = {"topic", "mode", "domain", "section", "objective", "item_id"}


def create_app(*, conn_factory, resolve_admin, environment):
    if not callable(conn_factory) or not callable(resolve_admin):
        raise ValueError("Trusted connection and admin identity adapters required")
    if environment.get("STAGING_ONLY") != "true":
        raise ValueError("Staging-only service required")

    def app(environ, start_response):
        def respond(status, body):
            data = json.dumps(body).encode()
            start_response(status, [("Access-Control-Allow-Origin", "https://staging.srnastudytool.com"),
                                   ("Vary", "Origin"), ("Content-Type", "application/json"),
                                   ("Cache-Control", "private, no-store"),
                                   ("X-Content-Type-Options", "nosniff"),
                                   ("Content-Length", str(len(data)))])
            return [data]

        if environ.get("PATH_INFO") != "/generation/preflight":
            return respond("404 Not Found", {"error": "not_found"})
        if environ.get("HTTP_ORIGIN") != "https://staging.srnastudytool.com":
            return respond("403 Forbidden", {"error": "forbidden_origin"})
        if environ.get("REQUEST_METHOD") == "OPTIONS":
            if (environ.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD") != "POST"
                    or environ.get("HTTP_ACCESS_CONTROL_REQUEST_HEADERS", "").lower().replace(" ", "") not in
                    ("authorization,content-type", "content-type,authorization")):
                return respond("403 Forbidden", {"error": "forbidden_preflight"})
            start_response("204 No Content", [("Access-Control-Allow-Origin", "https://staging.srnastudytool.com"),
                ("Access-Control-Allow-Methods", "POST"),
                ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
                ("Cache-Control", "private, no-store"), ("Vary", "Origin")])
            return [b""]
        if environ.get("REQUEST_METHOD") != "POST":
            return respond("405 Method Not Allowed", {"error": "method_not_allowed"})
        bearer = environ.get("HTTP_AUTHORIZATION", "")
        if not bearer.startswith("Bearer ") or len(bearer) > 8192:
            return respond("401 Unauthorized", {"error": "authentication_required"})
        try:
            owner = resolve_admin(bearer[7:])
            if str(UUID(owner)) != owner.lower():
                raise ValueError('Invalid identity')
        except Exception:
            return respond("403 Forbidden", {"error": "forbidden"})
        try:
            length = int(environ.get("CONTENT_LENGTH", "0"))
            if length < 1 or length > MAX_BODY:
                raise ValueError()
            data = json.loads(environ["wsgi.input"].read(length))
            if (not isinstance(data, dict) or not REQUIRED <= data.keys()
                    or not data.keys() <= FIELDS
                    or any(not isinstance(data[k], str) or not data[k].strip()
                           for k in REQUIRED)):
                raise ValueError()
            if data.get("execute") is not None or data.get("confirm_paid_calls") is not None:
                raise ValueError("HTTP route is preflight-only")
            from types import SimpleNamespace
            args = SimpleNamespace(**{**{"textbook_id": None, "section_id": None,
                "include_subsections": False, "page_start": None,
                "page_end": None, "limit": 8, "format": "MC"}, **data,
                "owner_uid": owner, "execute": False, "confirm_paid_calls": False})
            if args.mode not in ("NCE", "SEE") or args.format not in ("MC", "MS", "SA", "DD", "HS"):
                raise ValueError()
            if type(args.limit) is not int or not 1 <= args.limit <= 20:
                raise ValueError()
            if type(args.include_subsections) is not bool:
                raise ValueError()
            for page in (args.page_start, args.page_end):
                if page is not None and (type(page) is not int or page < 1):
                    raise ValueError()
            if args.page_start and args.page_end and args.page_start > args.page_end:
                raise ValueError()
        except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
            return respond("400 Bad Request", {"error": "invalid_request"})
        try:
            with conn_factory() as conn:
                result = execute(conn, args, environment)
            return respond("200 OK", result)
        except ValueError:
            return respond("422 Unprocessable Entity", {"error": "no_indexed_evidence"})
        except Exception:
            return respond("503 Service Unavailable", {"error": "generation_preflight_unavailable"})
    return app
