"""WSGI deployment entrypoint for the staging-only reviewer preview service."""
import os
import threading
from source_review_http_v2 import create_app
from source_review_runtime_v2 import StagingReviewRuntime


class ConfigurationError(RuntimeError):
    def __init__(self, rule):
        self.rule = rule
        super().__init__("Staging configuration rejected")


def validate_staging_configuration(env):
    """Fail closed, returning only fixed rule IDs, never secret material."""
    from urllib.parse import urlsplit, parse_qs, unquote
    if env.get("STAGING_ONLY") != "true":
        raise ConfigurationError("STAGING_ONLY")
    names = ("STAGING_DATABASE_URL", "STAGING_R2_ACCOUNT_ID",
             "STAGING_R2_ACCESS_KEY_ID", "STAGING_R2_SECRET_ACCESS_KEY",
             "SUPABASE_URL", "SUPABASE_ANON_KEY", "STAGING_RECEIPT_SIGNING_SECRET")
    for name in names:
        if not env.get(name):
            raise ConfigurationError("MISSING_" + name)
    if env["SUPABASE_URL"] != "https://xqyasyambwdyhsjkftqu.supabase.co":
        raise ConfigurationError("PROJECT_URL")
    if len(env["STAGING_RECEIPT_SIGNING_SECRET"]) < 32:
        raise ConfigurationError("SIGNING_SECRET_LENGTH")
    raw = env["STAGING_DATABASE_URL"]
    try:
        db = urlsplit(raw)
        host, username, password = db.hostname, db.username, db.password
        query = parse_qs(db.query, strict_parsing=True, keep_blank_values=True) if db.query else {}
    except (ValueError, TypeError):
        raise ConfigurationError("DATABASE_URL_PARSE") from None
    if db.scheme not in ("postgres", "postgresql"):
        raise ConfigurationError("DATABASE_SCHEME")
    if not host:
        raise ConfigurationError("DATABASE_HOST")
    if not username or not password:
        raise ConfigurationError("DATABASE_CREDENTIAL_FORMAT")
    # Reject raw URL delimiters in userinfo; credentials with reserved characters must be percent-encoded.
    userinfo = db.netloc.rsplit("@", 1)[0] if "@" in db.netloc else ""
    if db.netloc.count("@") != 1 or ":" not in userinfo or "#" in raw.split("?", 1)[0]:
        raise ConfigurationError("DATABASE_CREDENTIAL_FORMAT")
    direct = host == "db.xqyasyambwdyhsjkftqu.supabase.co"
    pooler = host.endswith(".pooler.supabase.com")
    if not (direct or pooler):
        raise ConfigurationError("DATABASE_PROJECT_HOST")
    expected_user = "postgres" if direct else "postgres.xqyasyambwdyhsjkftqu"
    if unquote(username) != expected_user:
        raise ConfigurationError("DATABASE_USERNAME")
    if db.path != "/postgres" or db.fragment:
        raise ConfigurationError("DATABASE_PATH")
    allowed = {"sslmode", "connect_timeout", "application_name"}
    if (not set(query).issubset(allowed) or
        any(len(values) != 1 or not values[0] for values in query.values()) or
        query.get("sslmode", ["require"])[0] not in ("require", "verify-ca", "verify-full")):
        raise ConfigurationError("DATABASE_OPTIONS")
    timeout = query.get("connect_timeout")
    if timeout and (not timeout[0].isdigit() or not 1 <= int(timeout[0]) <= 30):
        raise ConfigurationError("DATABASE_OPTIONS")
    # Never allow sslmode=disable or an unexpected project/host/user combination.
    return True


def database_failure_rule(exc):
    """Return a stable error ID without leaking libpq connection strings."""
    import psycopg
    if not isinstance(exc, psycopg.Error):
        return "NONE"
    state = exc.sqlstate or ""
    if state == "28P01":
        return "DATABASE_PASSWORD_REJECTED"
    if state in ("28000", "3D000"):
        return "DATABASE_ROLE_OR_NAME"
    if state == "42501":
        return "DATABASE_PERMISSION"
    if state in ("53300", "53400"):
        return "DATABASE_CAPACITY"
    if state.startswith("08"):
        return "DATABASE_CONNECTION"
    if isinstance(exc, psycopg.OperationalError):
        # The message is examined in-memory only; never print it or send it to a client.
        detail = str(exc).lower()
        if "no route to host" in detail or "network is unreachable" in detail:
            return "DATABASE_NETWORK_UNREACHABLE"
        if "could not translate host name" in detail or "name or service not known" in detail:
            return "DATABASE_DNS"
        if "password authentication failed" in detail or "invalid password" in detail:
            return "DATABASE_PASSWORD_REJECTED"
        if "connection timed out" in detail or "timeout expired" in detail or "operation timed out" in detail:
            return "DATABASE_TIMEOUT"
        if "certificate verify failed" in detail or "ssl error" in detail or "tls" in detail:
            return "DATABASE_TLS"
        if "connection refused" in detail:
            return "DATABASE_CONNECTION_REFUSED"
        if "no pg_hba.conf entry" in detail:
            return "DATABASE_ACCESS_POLICY"
        return "DATABASE_NETWORK_OR_TLS"
    return "DATABASE_OTHER"



def build_app():
    validate_staging_configuration(os.environ)
    import boto3
    import psycopg
    # Connections are per-process. The single-worker staging configuration
    # keeps the privileged connection lifecycle explicit.
    conn = psycopg.connect(os.environ["STAGING_DATABASE_URL"], autocommit=True, connect_timeout=8, sslmode="require")
    r2 = boto3.client("s3",
        endpoint_url="https://" + os.environ["STAGING_R2_ACCOUNT_ID"] + ".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["STAGING_R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["STAGING_R2_SECRET_ACCESS_KEY"],
        region_name="auto")
    runtime = StagingReviewRuntime(
        conn=conn, r2_client=r2, supabase_url=os.environ["SUPABASE_URL"],
        supabase_api_key=os.environ["SUPABASE_ANON_KEY"],
        signing_secret=os.environ["STAGING_RECEIPT_SIGNING_SECRET"])
    reviewer_app = create_app(runtime)
    from item_generation_http_v2 import create_app as generation_app
    def index_readiness(owner):
        from check_semantic_index_readiness_v2 import check
        inventory_path = os.environ.get("SEMANTIC_INDEX_INVENTORY_PATH")
        configured_owner = os.environ.get("SEMANTIC_INDEX_OWNER_UID")
        if not inventory_path or owner != configured_owner:
            raise ValueError("Index readiness not configured for authenticated owner")
        return check(inventory_path=inventory_path, env=os.environ,
                     connect=psycopg.connect)

    def semantic_lookup_factory(db_conn, owner, textbook_id):
        # No paid embedding request at factory construction; only the eventual
        # schema-valid candidate triggers an explicitly opted-in provider call.
        if (os.environ.get("AI_GENERATION_OPT_IN") != "true"
                or os.environ.get("AI_SEMANTIC_EMBEDDING_OPT_IN") != "true"):
            return None
        from item_semantic_live_bridge_v2 import make_gemini_embed, build_semantic_lookup
        embed = make_gemini_embed(
            api_key=os.environ.get("AI_SEMANTIC_GEMINI_API_KEY", ""),
            model=os.environ.get("SEMANTIC_INDEX_EMBEDDING_MODEL"),
            enabled=True)
        return build_semantic_lookup(
            db_conn, owner_uid=owner, env=os.environ, embed=embed)

    generation = generation_app(
        conn_factory=lambda: psycopg.connect(os.environ["STAGING_DATABASE_URL"],
            connect_timeout=8, sslmode="require"),
        resolve_admin=lambda token: runtime._reviewer(token).uid,
        environment=os.environ, readiness_factory=index_readiness,
        semantic_lookup_factory=semantic_lookup_factory)
    return lambda environ, start_response: (
        generation(environ, start_response)
        if (environ.get("PATH_INFO") in ("/generation/preflight", "/generation/one", "/generation/provider-check", "/generation/index-readiness") or
            environ.get("PATH_INFO", "").startswith("/generation/drafts"))
        else reviewer_app(environ, start_response))


# Do not make the HTTP listener depend on an eager database connection.
# Startup health means the listener is available, not that storage is ready.
_app = None
_lock = threading.Lock()


def app(environ, start_response):
    global _app
    if environ.get("PATH_INFO") == "/health" and environ.get("REQUEST_METHOD") == "GET":
        from source_review_http_v2 import response
        return response(start_response, "200 OK",
                        b'{"ok":true,"environment":"staging","approval_enabled":false}')
    if _app is None:
        with _lock:
            if _app is None:
                try:
                    _app = build_app()
                except Exception as exc:
                    # Only emit fixed error categories, never driver messages, SQL or credentials.
                    import logging
                    category = "configuration" if isinstance(exc, ConfigurationError) else (
                        "database" if isinstance(exc, __import__("psycopg").Error) else
                        "dependency" if isinstance(exc, ImportError) else "backend")
                    logging.getLogger("reviewer").error("staging_reviewer_backend_failure category=%s rule=%s", category, exc.rule if isinstance(exc, ConfigurationError) else database_failure_rule(exc))
                    from source_review_http_v2 import response
                    rule = exc.rule if isinstance(exc, ConfigurationError) else database_failure_rule(exc)
                    payload = ('{"error":"reviewer_backend_unavailable","stage":"' + category + '","rule":"' + rule + '"}').encode()
                    return response(start_response, "503 Service Unavailable", payload)
    return _app(environ, start_response)

