"""Trusted staging review manifest derived from verified R2 queue + attestation.

Never use browser-supplied metadata as source authority. The original PDF
is independently checked by source_review_r2_loader_v2 before rendering.
"""
import hashlib
import json
import re

BUCKET = "srna-staging-textbooks"
MAX_QUEUE = 256 * 1024
KEY = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/[A-Za-z0-9._-]{1,150}\.pdf$", re.I)
SHA = re.compile(r"^[0-9a-f]{64}$")
CATEGORIES = {"ocr_error", "image_content_review", "short_text_review", "blank_candidate_review", "visual_blank_candidate_review"}


def load_staging_review_manifest(client, *, owner_uid, r2_key, bucket=BUCKET):
    if bucket != BUCKET:
        raise ValueError("Staging bucket required")
    if not isinstance(r2_key, str) or not KEY.fullmatch(r2_key) or r2_key.split("/")[0] != owner_uid:
        raise ValueError("Invalid owner-scoped PDF key")
    source = client.head_object(Bucket=bucket, Key=r2_key)
    if not isinstance(source, dict):
        raise ValueError("Source PDF missing")
    suffix = r2_key[len(owner_uid) + 1:]
    queue_key = owner_uid + "/_review_queues/" + suffix + ".json"
    att_obj = client.get_object(Bucket=bucket, Key=queue_key + ".source.json")
    if not isinstance(att_obj, dict):
        raise ValueError("Verified attestation missing")
    att_body = att_obj["Body"]
    try:
        att_bytes = att_body.read(MAX_QUEUE + 1)
    finally:
        att_body.close()
    if not isinstance(att_bytes, bytes) or len(att_bytes) > MAX_QUEUE:
        raise ValueError("Invalid attestation size")
    try:
        att = json.loads(att_bytes)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid attestation JSON") from exc
    if (not isinstance(att, dict) or att.get("schema_version") != 1
            or att.get("r2_key") != r2_key or not isinstance(att.get("source_sha256"), str)
            or not SHA.fullmatch(att["source_sha256"]) or not isinstance(att.get("queue_sha256"), str)
            or not SHA.fullmatch(att["queue_sha256"]) or not att.get("source_etag")
            or att["source_etag"] != source.get("ETag")
            or type(att.get("size_bytes")) is not int
            or att["size_bytes"] != source.get("ContentLength")):
        raise ValueError("Source attestation mismatch")
    queue_obj = client.get_object(Bucket=bucket, Key=queue_key)
    if not isinstance(queue_obj, dict):
        raise ValueError("Verified review queue missing")
    queue_body = queue_obj["Body"]
    try:
        queue_bytes = queue_body.read(MAX_QUEUE + 1)
    finally:
        queue_body.close()
    if not isinstance(queue_bytes, bytes) or len(queue_bytes) > MAX_QUEUE:
        raise ValueError("Invalid review queue size")
    if hashlib.sha256(queue_bytes).hexdigest() != att["queue_sha256"]:
        raise ValueError("Review queue fingerprint mismatch")
    try:
        queue = json.loads(queue_bytes)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid review queue JSON") from exc
    if (not isinstance(queue, dict) or queue.get("r2_key") != r2_key
            or queue.get("source_sha256") != att["source_sha256"]
            or queue.get("approval_enabled") is not False
            or type(queue.get("pdf_page_count")) is not int
            or queue["pdf_page_count"] < 1 or not isinstance(queue.get("pages"), list)
            or len(queue["pages"]) > queue["pdf_page_count"]):
        raise ValueError("Review queue source mismatch")
    seen = set()
    for page in queue["pages"]:
        if (not isinstance(page, dict) or type(page.get("pdf_page")) is not int
                or not 1 <= page["pdf_page"] <= queue["pdf_page_count"]
                or page["pdf_page"] in seen or page.get("review_category") not in CATEGORIES
                or type(page.get("characters")) is not int or page["characters"] < 0):
            raise ValueError("Invalid review queue page")
        seen.add(page["pdf_page"])
    latest = client.head_object(Bucket=bucket, Key=r2_key)
    if (latest.get("ETag") != source["ETag"]
            or latest.get("ContentLength") != source["ContentLength"]):
        raise ValueError("Source changed while loading manifest")
    return {"owner_uid": owner_uid, "r2_key": r2_key,
            "sha256": att["source_sha256"],
            "pdf_page_count": queue["pdf_page_count"]}
