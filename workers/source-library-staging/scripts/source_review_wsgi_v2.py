"""WSGI deployment entrypoint for the staging-only reviewer preview service."""
import os
import threading
from source_review_http_v2 import create_app
from source_review_runtime_v2 import StagingReviewRuntime


def validate_staging_configuration(env):
    if env.get("STAGING_ONLY") != "true":
        raise RuntimeError("Staging-only reviewer service")
    names = ("STAGING_DATABASE_URL", "STAGING_R2_ACCOUNT_ID",
             "STAGING_R2_ACCESS_KEY_ID", "STAGING_R2_SECRET_ACCESS_KEY",
             "SUPABASE_URL", "SUPABASE_ANON_KEY", "STAGING_RECEIPT_SIGNING_SECRET")
    missing = [name for name in names if not env.get(name)]
    if missing:
        raise RuntimeError("Missing staging configuration: " + ", ".join(missing))
    # Fail closed if a deployment accidentally points at a non-staging backend.
    from urllib.parse import urlparse
    db = urlparse(env["STAGING_DATABASE_URL"])
    if (db.scheme not in ("postgres", "postgresql") or
            not db.hostname or
            not (db.hostname == "db.xqyasyambwdyhsjkftqu.supabase.co" or
                 (db.hostname.endswith(".pooler.supabase.com") and
                  db.username == "postgres.xqyasyambwdyhsjkftqu")) or
            env["SUPABASE_URL"] != "https://xqyasyambwdyhsjkftqu.supabase.co" or
            db.path != "/postgres" or db.fragment or db.query or
            ((db.hostname == "db.xqyasyambwdyhsjkftqu.supabase.co" and db.username != "postgres") or
             (db.hostname.endswith(".pooler.supabase.com") and db.username != "postgres.xqyasyambwdyhsjkftqu"))):
        raise RuntimeError("Reviewer service must use the designated staging Supabase project")
    return True


def build_app():
    validate_staging_configuration(os.environ)
    import boto3
    import psycopg
    # Connections are per-process. The single-worker staging configuration
    # keeps the privileged connection lifecycle explicit.
    conn = psycopg.connect(os.environ["STAGING_DATABASE_URL"], autocommit=True)
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
validate_staging_configuration(os.environ)
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
                except Exception:
                    # Never expose connection strings, credentials, or driver errors.
                    from source_review_http_v2 import response
                    return response(start_response, "503 Service Unavailable",
                                    b'{"error":"reviewer_backend_unavailable"}')
    return _app(environ, start_response)

