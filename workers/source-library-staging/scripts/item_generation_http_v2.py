"""Authenticated, staging-only WSGI bridge for indexed question generation.

Mount in a trusted Python service with staging PostgreSQL; never in the
Cloudflare upload Worker. Defaults to evidence-only preflight, no model calls.
"""
import json
import re
from uuid import UUID

from run_grounded_generation_v2 import execute
from item_draft_storage_v2 import save, list_drafts, get_draft, review
from item_generation_checkpoint_store_v2 import save_once
from item_draft_revalidation_v2 import revalidate
from item_draft_revision_storage_v2 import save_revision, list_revisions, RevisionValidationError

MAX_BODY = 8192
FIELDS = {"topic", "mode", "domain", "section", "objective", "format",
          "item_id", "textbook_id", "section_id", "include_subsections",
          "page_start", "page_end", "limit", "execute", "confirm_paid_calls"}
REQUIRED = {"topic", "mode", "domain", "section", "objective", "item_id"}


def create_app(*, conn_factory, resolve_admin, environment, semantic_lookup_factory=None, readiness_factory=None):
    if readiness_factory is not None and not callable(readiness_factory):
        raise ValueError("Trusted readiness factory required")
    if semantic_lookup_factory is not None and not callable(semantic_lookup_factory):
        raise ValueError("Trusted semantic lookup factory required")
    if not callable(conn_factory) or not callable(resolve_admin):
        raise ValueError("Trusted connection and admin identity adapters required")
    if environment.get("STAGING_ONLY") != "true":
        raise ValueError("Staging-only service required")

    def app(environ, start_response):
        def respond(status, body, retry_after=None):
            data = json.dumps(body).encode()
            start_response(status, [("Access-Control-Allow-Origin", "https://staging.srnastudytool.com"),
                                   ("Vary", "Origin"), ("Content-Type", "application/json"),
                                   ("Cache-Control", "private, no-store"),
                                   ("X-Content-Type-Options", "nosniff"),
                                   ("Content-Length", str(len(data)))] + ([("Retry-After", str(retry_after))] if type(retry_after) is int and 0 <= retry_after <= 3600 else []))
            return [data]

        path = environ.get("PATH_INFO", "")
        draft_match = re.fullmatch(r"/generation/drafts/([0-9a-fA-F-]{36})(/review|/revalidate|/revisions)?", path)
        textbook_list = path == "/generation/textbooks"
        readiness = path == "/generation/index-readiness"
        checkpoint_readiness = path == "/generation/checkpoint-readiness"
        diagnostic = path == "/generation/provider-check"
        if path not in ("/generation/preflight", "/generation/one", "/generation/drafts", "/generation/provider-check", "/generation/index-readiness", "/generation/checkpoint-readiness", "/generation/textbooks") and not draft_match:
            return respond("404 Not Found", {"error": "not_found"})
        if environ.get("HTTP_ORIGIN") != "https://staging.srnastudytool.com":
            return respond("403 Forbidden", {"error": "forbidden_origin"})
        if environ.get("REQUEST_METHOD") == "OPTIONS":
            requested = environ.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD")
            allowed = ("GET", "POST") if path == "/generation/drafts" or (draft_match and draft_match.group(2) == "/revisions") else (
                ("GET",) if diagnostic or readiness or checkpoint_readiness or textbook_list or (draft_match and draft_match.group(2) not in ("/review", "/revisions")) else ("POST",))
            headers = {x.strip().lower() for x in environ.get(
                "HTTP_ACCESS_CONTROL_REQUEST_HEADERS", "").split(",") if x.strip()}
            if requested not in allowed or not headers <= {"authorization", "content-type"}:
                return respond("403 Forbidden", {"error": "forbidden_preflight"})
            start_response("204 No Content", [("Access-Control-Allow-Origin", "https://staging.srnastudytool.com"),
                ("Access-Control-Allow-Methods", ", ".join(allowed)),
                ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
                ("Cache-Control", "private, no-store"), ("Vary", "Origin")])
            return [b""]
        method = environ.get("REQUEST_METHOD")
        if path not in ("/generation/preflight", "/generation/one"):
            allowed = ("GET", "POST") if path == "/generation/drafts" or (draft_match and draft_match.group(2) == "/revisions") else (("GET",) if diagnostic or readiness or checkpoint_readiness or textbook_list or (draft_match and draft_match.group(2) not in ("/review", "/revisions")) else ("POST",))
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
        if textbook_list:
            try:
                with conn_factory() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            select id::text, filename
                            from source_library_staging.textbooks
                            where owner_uid=%s::uuid and status='ready'
                            order by filename, id
                            limit 200
                        """, (owner,))
                        books = [{"id": row[0], "title": row[1]} for row in cur.fetchall()]
                return respond("200 OK", {"textbooks": books})
            except Exception:
                return respond("503 Service Unavailable", {"error": "textbook_list_unavailable"})
        if checkpoint_readiness:
            if method != "GET":
                return respond("405 Method Not Allowed", {"error": "method_not_allowed"})
            try:
                # Only the authenticated admin reaches this query. No writes or provider calls.
                with conn_factory() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                          select current_database() = 'postgres',
                            to_regclass('source_library_staging.generation_checkpoints_v2') is not null,
                            has_table_privilege(current_user,
                              'source_library_staging.generation_checkpoints_v2', 'SELECT'),
                            has_table_privilege(current_user,
                              'source_library_staging.generation_checkpoints_v2', 'INSERT')
                        """)
                        row = cur.fetchone()
                ready = bool(row and len(row) == 4 and all(v is True for v in row))
                return respond("200 OK" if ready else "503 Service Unavailable",
                               {"ready": ready, "check": "checkpoint_database_readiness",
                                "generation_performed": False, "database_writes": False})
            except Exception:
                return respond("503 Service Unavailable",
                               {"ready": False, "check": "checkpoint_database_readiness",
                                "generation_performed": False, "database_writes": False})
        if readiness:
            if method != "GET":
                return respond("405 Method Not Allowed", {"error": "method_not_allowed"})
            if readiness_factory is None:
                return respond("503 Service Unavailable", {"ready": False, "error": "index_readiness_unavailable"})
            try:
                result = readiness_factory(owner)
                keys = {"ready", "inventory_digest", "expected_count", "indexed_count",
                        "missing_count", "unexpected_count", "stale_count"}
                if (not isinstance(result, dict) or set(result) != keys
                        or type(result["ready"]) is not bool
                        or not isinstance(result["inventory_digest"], str)
                        or re.fullmatch(r"[a-f0-9]{64}", result["inventory_digest"]) is None
                        or any(type(result[k]) is not int or result[k] < 0
                               for k in keys - {"ready", "inventory_digest"})
                        or result["expected_count"] > 10000
                        or result["indexed_count"] > 10000
                        or result["missing_count"] + result["stale_count"]
                           > result["expected_count"]
                        or result["unexpected_count"] > result["indexed_count"]
                        or result["ready"] != (
                            result["missing_count"] == 0
                            and result["unexpected_count"] == 0
                            and result["stale_count"] == 0
                            and result["expected_count"] == result["indexed_count"])):
                    raise ValueError("Invalid readiness result")
                return respond("200 OK", result)
            except Exception:
                return respond("503 Service Unavailable", {"ready": False, "error": "index_readiness_unavailable"})
        if diagnostic:
            if method != "GET":
                return respond("405 Method Not Allowed", {"error": "method_not_allowed"})
            if environment.get("AI_GENERATION_OPT_IN") != "true":
                return respond("403 Forbidden", {"error": "generation_disabled"})
            # Exercise the actual Container -> signed Worker -> Groq path.
            # This request checks /models only and never invokes generation.
            import hashlib
            import hmac
            import time
            import urllib.error
            import urllib.request
            secret = environment.get("STAGING_RECEIPT_SIGNING_SECRET", "")
            if len(secret) < 32:
                return respond("503 Service Unavailable", {"error": "provider_check_unavailable", "rule": "CONFIGURATION"})
            body = b'{"diagnostic":"groq_models"}'
            stamp = str(int(time.time()))
            signature = hmac.new(secret.encode(), b'srna-groq-relay-v1\n' + stamp.encode() + b'\n' + body, hashlib.sha256).hexdigest()
            request = urllib.request.Request(
                "https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",
                data=body, method="POST", headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (compatible; SRNAStudyToolStagingRelay/1.0; +https://srnastudytool.com)",
                    "Accept": "application/json",
                    "X-Relay-Timestamp": stamp, "X-Relay-Signature": signature})
            from item_ai_https_transport_v2 import _NoRedirect
            try:
                with urllib.request.build_opener(_NoRedirect()).open(request, timeout=10) as response:
                    data = json.loads(response.read(2048))
                if (data.get("check") != "groq_models_via_signed_relay"
                        or data.get("generation_performed") is not False):
                    raise ValueError("Invalid relay diagnostic")
                return respond("200 OK", data)
            except urllib.error.HTTPError as exc:
                edge_denial = exc.code == 403 and exc.headers.get("X-Review-Approval-Enabled") != "false"
                if edge_denial:
                    snippet = exc.read(512).lower()
                    if b"error code: 1020" in snippet or b"error code 1020" in snippet:
                        rule = "RELAY_EDGE_WAF_1020"
                    elif b"cloudflare" in snippet or b"cf-error" in snippet or b"challenge-platform" in snippet:
                        rule = "RELAY_EDGE_CLOUDFLARE"
                    elif b"access denied" in snippet or b"forbidden" in snippet:
                        rule = "RELAY_EDGE_ACCESS_DENIED"
                    else:
                        rule = "RELAY_EDGE_403"
                else:
                    rule = "RELAY_HTTP_" + str(exc.code if exc.code in (400, 401, 403, 404, 405, 413, 429, 500, 502, 503, 504) else 0)
                return respond("503 Service Unavailable", {"error": "provider_check_unavailable", "rule": rule})
            except Exception:
                return respond("503 Service Unavailable", {"error": "provider_check_unavailable", "rule": "RELAY_NETWORK"})
        if path not in ("/generation/preflight", "/generation/one"):
            try:
                if method == "GET":
                    with conn_factory() as conn:
                        result = (list_drafts(conn, owner_uid=owner)
                                  if path == "/generation/drafts" else
                                  list_revisions(conn, owner_uid=owner, draft_id=draft_match.group(1))
                                  if draft_match.group(2) == "/revisions" else
                                  revalidate(conn, owner_uid=owner, draft_id=draft_match.group(1))
                                  if draft_match.group(2) == "/revalidate" else
                                  get_draft(conn, owner_uid=owner, draft_id=draft_match.group(1)))
                    return respond("200 OK", {"drafts": result} if path == "/generation/drafts" else result)
                length = int(environ.get("CONTENT_LENGTH", "0"))
                if length < 1 or length > MAX_BODY:
                    raise ValueError("Invalid body size")
                payload = json.loads(environ["wsgi.input"].read(length))
                if not isinstance(payload, dict) or "owner_uid" in payload or "reviewer_uid" in payload:
                    raise ValueError("Client identity is forbidden")
                if path == "/generation/drafts":
                    if len(json.dumps(payload)) > MAX_BODY:
                        raise ValueError("Oversized draft")
                    with conn_factory() as conn:
                        result = save(conn, {**payload, "owner_uid": owner})
                    return respond("201 Created", result)
                if draft_match and draft_match.group(2) == "/revisions":
                    if set(payload) not in ({"expected_parent_sha256", "citation_excerpts", "option_evidence", "reviewer_notes"}, {"expected_parent_sha256", "citation_excerpts", "option_evidence", "reviewer_notes", "question_edits"}):
                        raise ValueError("Invalid revision body")
                    raw_excerpts = payload["citation_excerpts"]
                    if not isinstance(raw_excerpts,dict) or any(not isinstance(k,str) or not k.isascii() or not k.isdecimal() or (k != "0" and k.startswith("0")) for k in raw_excerpts):
                        raise ValueError("Invalid citation indices")
                    excerpts = {int(k):v for k,v in raw_excerpts.items()}
                    with conn_factory() as conn:
                        result = save_revision(conn,owner_uid=owner,draft_id=draft_match.group(1),
                            expected_parent_sha256=payload["expected_parent_sha256"],
                            citation_excerpts=excerpts,option_evidence=payload["option_evidence"],
                            question_edits=payload.get("question_edits"),
                            reviewer_notes=payload["reviewer_notes"])
                    return respond("201 Created",result)
                if set(payload) != {"status", "notes"}:
                    raise ValueError("Invalid review body")
                with conn_factory() as conn:
                    result = review(conn, owner_uid=owner, reviewer_uid=owner,
                                    draft_id=draft_match.group(1),
                                    status=payload["status"], notes=payload["notes"])
                return respond("200 OK", result)
            except RevisionValidationError as exc:
                return respond("422 Unprocessable Entity", {"error": "revision_validation_failed", "issues": exc.issues})
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
                raise ValueError("Execution flags cannot be supplied by client")
            live = path == "/generation/one"
            if live and (not isinstance(data.get("textbook_id"), str) or not data["textbook_id"].strip()):
                raise ValueError("Explicit textbook required for saving generated drafts")
            if live and environment.get("AI_GENERATION_OPT_IN") != "true":
                return respond("403 Forbidden", {"error": "generation_disabled"})
            from types import SimpleNamespace
            args = SimpleNamespace(**{**{"textbook_id": None, "section_id": None,
                "include_subsections": False, "page_start": None,
                "page_end": None, "limit": (8 if live else 20), "format": "MC"}, **data,
                "owner_uid": owner, "execute": live, "confirm_paid_calls": live})
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
                semantic_lookup = (semantic_lookup_factory(conn, owner, args.textbook_id)
                                   if live and semantic_lookup_factory is not None else None)
                result = execute(conn, args, environment, semantic_lookup=semantic_lookup)
                if live:
                    # Persist the same generated item in the private, owner-scoped
                    # staging draft bank. This never publishes or approves it.
                    result = dict(result)
                    key = result.pop("_checkpoint_key", None)
                    if key is not None:
                        saved = save_once(conn, owner_uid=owner, save_payload=result["save_payload"],
                                          checkpoint_key=key, saver=save)
                    else:
                        saved = save(conn, {**result["save_payload"], "owner_uid": owner})
                    result = {**result, "draft_id": saved["draft_id"],
                              "draft_status": saved["status"], "published": False,
                              "requires_human_review": True}
            return respond("200 OK", result)
        except ValueError as exc:
            # Safe fixed categories only. Do not return source passages, model text,
            # credentials, or arbitrary exception strings to the browser.
            message = str(exc)
            if "No indexed textbook evidence" in message or "No indexed textbook evidence found" in message:
                rule = "NO_INDEXED_EVIDENCE"
            elif "Invalid or unverified indexed evidence" in message or "Verified indexed evidence" in message:
                rule = "INVALID_INDEXED_EVIDENCE"
            elif "Concept card" in message:
                rule = "CONCEPT_CARD_VALIDATION"
            elif "Generated draft" in message:
                rule = "DRAFT_VALIDATION"
            elif "Rationale incomplete" in message:
                rule = "RATIONALE_VALIDATION"
            elif "Provider" in message or "provider" in message or "Relay" in message or "relay" in message:
                rule = "PROVIDER_CONFIGURATION"
            else:
                rule = "GENERATION_VALIDATION"
            return respond("422 Unprocessable Entity", {"error": "generation_or_evidence_unavailable", "rule": rule})
        except Exception as exc:
            # Never log prompts, indexed passages, credentials or provider response bodies.
            # Fixed categories distinguish infrastructure failures from provider failures.
            import logging
            from urllib.error import HTTPError, URLError
            from item_ai_https_transport_v2 import TransportError
            from item_ai_provider_v2 import ProviderError
            if isinstance(exc, TransportError):
                rule = exc.rule
            elif isinstance(exc, ProviderError):
                rule = "PROVIDER_RESPONSE"
            elif isinstance(exc, (ConnectionError, TimeoutError, URLError)):
                rule = "UPSTREAM_CONNECTION"
            elif isinstance(exc, HTTPError):
                rule = "UPSTREAM_HTTP"
            elif isinstance(exc, (ImportError, ModuleNotFoundError)):
                rule = "DEPENDENCY_UNAVAILABLE"
            elif isinstance(exc, (OSError,)):
                rule = "RUNTIME_IO"
            else:
                rule = "GENERATION_RUNTIME_ERROR"
            logging.getLogger("generation").error(
                "staging_generation_failure endpoint=%s rule=%s exception_type=%s",
                "one" if path == "/generation/one" else "preflight",
                rule, type(exc).__name__)
            return respond("429 Too Many Requests" if rule == "PROVIDER_RATE_LIMIT" else "503 Service Unavailable",
                           {"error": "generation_preflight_unavailable", "rule": rule,
                            **({"failed_step": exc.generation_step} if getattr(exc, "generation_step", None) in ("concept_card", "item_draft", "rationale") else {}),
                            **({"retry_after_seconds": exc.retry_after_seconds} if isinstance(exc, TransportError) and exc.retry_after_seconds is not None else {}),
                            **({"remaining_requests": exc.remaining_requests} if isinstance(exc, TransportError) and exc.remaining_requests is not None else {}),
                            **({"remaining_tokens": exc.remaining_tokens} if isinstance(exc, TransportError) and exc.remaining_tokens is not None else {})},
                           retry_after=exc.retry_after_seconds if isinstance(exc, TransportError) else None)
    return app
