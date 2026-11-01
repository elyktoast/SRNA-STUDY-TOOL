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
    if any(not env.get(name) for name in names):
        raise ConfigurationError("MISSING_BINDING")
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


def build_app():
    validate_staging_configuration(os.environ)
    import boto3
    import psycopg
    # Connections are per-process. The single-worker staging configuration
    # keeps the privileged connection lifecycle explicit.
    conn = psycopg.connect(os.environ["STAGING_DATABASE_URL"], autocommit=True, connect_timeout=5)
    r2 = boto3.client("s3",
        endpoint_url="https://" + os.environ["STAGING_R2_ACCOUNT_ID"] + ".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["STAGING_R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["STAGING_R2_SECRET_ACCESS_KEY"],
        region_name="auto")
    return create_app(StagingReviewRuntime(
        conn=conn, r2_client=r2, supabase_url=os.environ["SUPABASE_URL"],
        supabase_api_key=os.environ["SUPABASE_ANON_KEY"],
        signing_secret=os.environ["STAGING_RECEIPT_SIGNING_SECRET"]))


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
                    logging.getLogger("reviewer").error("staging_reviewer_backend_failure category=%s rule=%s", category, exc.rule if isinstance(exc, ConfigurationError) else "NONE")
                    from source_review_http_v2 import response
                    payload = ('{"error":"reviewer_backend_unavailable","stage":"' + category + '"}').encode()
                    return response(start_response, "503 Service Unavailable", payload)
    return _app(environ, start_response)

