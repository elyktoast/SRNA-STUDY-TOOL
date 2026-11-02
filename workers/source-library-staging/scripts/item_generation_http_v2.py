"""Authenticated, staging-only WSGI bridge for indexed question generation.

Mount in a trusted Python service with staging PostgreSQL; never in the
Cloudflare upload Worker. Defaults to evidence-only preflight, no model calls.
"""
import json
import re
from uuid import UUID

from run_grounded_generation_v2 import execute
from item_draft_storage_v2 import list_drafts, get_draft, review

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

        path = environ.get("PATH_INFO", "")
        draft_match = re.fullmatch(r"/generation/drafts/([0-9a-fA-F-]{36})(/review)?", path)
        if path not in ("/generation/preflight", "/generation/drafts") and not draft_match:
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
        method = environ.get("REQUEST_METHOD")
        if path != "/generation/preflight":
            allowed = ("GET",) if path == "/generation/drafts" or (draft_match and not draft_match.group(2)) else ("POST",)
            if method not in allowed:
                return respond("405 Method Not Allowed", {"error": "method_not_allowed"})
        elif method != "POST":
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
        if path != "/generation/preflight":
            try:
                if method == "GET":
                    with conn_factory() as conn:
                        result = (list_drafts(conn, owner_uid=owner)
                                  if path == "/generation/drafts" else
                                  get_draft(conn, owner_uid=owner, draft_id=draft_match.group(1)))
                    return respond("200 OK", {"drafts": result} if path == "/generation/drafts" else result)
                length = int(environ.get("CONTENT_LENGTH", "0"))
                if length < 1 or length > MAX_BODY:
                    raise ValueError("Invalid body size")
                payload = json.loads(environ["wsgi.input"].read(length))
                if not isinstance(payload, dict) or set(payload) != {"status", "notes"}:
                    raise ValueError("Invalid review body")
                with conn_factory() as conn:
                    result = review(conn, owner_uid=owner, reviewer_uid=owner,
                                    draft_id=draft_match.group(1),
                                    status=payload["status"], notes=payload["notes"])
                return respond("200 OK", result)
            except (ValueError, TypeError, KeyError):
                return respond("422 Unprocessable Entity", {"error": "invalid_or_unavailable_draft"})
            except Exception:
                return respond("503 Service Unavailable", {"error": "draft_service_unavailable"})
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
            if "execute" in data or "confirm_paid_calls" in data:
                raise ValueError("HTTP route is preflight-only")
            from types import SimpleNamespace
            args = SimpleNamespace(**{**{"textbook_id": None, "section_id": None,
                "include_subsections": False, "page_start": None,
                "page_end": None, "limit": 8, "format": "MC"}, **data,
                "owner_uid": owner, "execute": False, "confirm_paid_calls": False})
            if (args.mode not in ("NCE", "SEE") or args.format not in ("MC", "MS", "SA", "DD", "HS")
                    or args.domain not in ("I", "II", "III", "IV")
                    or not re.fullmatch(r"[A-Z]", args.section)
                    or not re.fullmatch(r"(I|II|III|IV)\.[A-Z]\.\d+(?:\.\d+)*", args.objective)
                    or args.objective.split(".")[:2] != [args.domain, args.section]):
                raise ValueError()
            if type(args.limit) is not int or not 1 <= args.limit <= 20:
                raise ValueError()
            if type(args.include_subsections) is not bool:
                raise ValueError()
            for field in ("textbook_id", "section_id"):
                value = getattr(args, field)
                if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > 200):
                    raise ValueError()
            if len(args.topic) > 500 or any(len(getattr(args, field)) > 200 for field in ("mode", "domain", "section", "objective", "item_id", "format")):
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
