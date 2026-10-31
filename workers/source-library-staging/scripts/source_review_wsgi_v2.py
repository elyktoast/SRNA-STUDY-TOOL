"""WSGI deployment entrypoint for the staging-only reviewer preview service."""
import os
from source_review_http_v2 import create_app
from source_review_runtime_v2 import StagingReviewRuntime


def build_app():
    if os.environ.get("STAGING_ONLY") != "true":
        raise RuntimeError("Staging-only reviewer service")
    names = ("STAGING_DATABASE_URL", "STAGING_R2_ACCOUNT_ID",
             "STAGING_R2_ACCESS_KEY_ID", "STAGING_R2_SECRET_ACCESS_KEY",
             "SUPABASE_URL", "SUPABASE_ANON_KEY", "STAGING_RECEIPT_SIGNING_SECRET")
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing staging configuration: " + ", ".join(missing))
    # Fail closed if a deployment accidentally points at a non-staging backend.
    from urllib.parse import urlparse
    db = urlparse(os.environ["STAGING_DATABASE_URL"])
    supabase = urlparse(os.environ["SUPABASE_URL"])
    if (db.scheme not in ("postgres", "postgresql") or
            not db.hostname or
            not (db.hostname == "db.xqyasyambwdyhsjkftqu.supabase.co" or
                 (db.hostname.endswith(".pooler.supabase.com") and
                  db.username and db.username.endswith(".xqyasyambwdyhsjkftqu"))) or
            supabase.scheme != "https" or
            supabase.hostname != "xqyasyambwdyhsjkftqu.supabase.co"):
        raise RuntimeError("Reviewer service must use the designated staging Supabase project")
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


app = build_app()
