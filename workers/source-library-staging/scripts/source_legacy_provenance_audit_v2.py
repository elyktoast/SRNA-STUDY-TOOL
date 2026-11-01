"""Read-only staging audit for legacy textbook provenance.

Checks the independent R2 signed-by-workflow attestation against the existing
indexed database record. Does NOT assert that legacy passages were derived from
the current bytes: that requires separately verified extraction/reindexing.
Never inserts provenance rows or changes an existing index.
"""
from uuid import UUID
from source_review_manifest_r2_v2 import load_staging_review_manifest


def audit_legacy_source(conn, r2, *, owner_uid, textbook_id, r2_key):
    for name, value in (("owner_uid", owner_uid), ("textbook_id", textbook_id)):
        if not isinstance(value, str):
            raise ValueError("Invalid " + name)
        try:
            if str(UUID(value)) != value.lower():
                raise ValueError()
        except ValueError:
            raise ValueError("Invalid " + name) from None
    if not isinstance(r2_key, str) or not r2_key.startswith(owner_uid + "/"):
        raise ValueError("Invalid owner-scoped R2 key")
    with conn.cursor() as cur:
        cur.execute(
            """SELECT t.status, t.page_count, t.file_size_bytes,
                      (SELECT COUNT(*) FROM source_library_staging.passages p
                       WHERE p.textbook_id=t.id),
                      (SELECT COUNT(*) FROM source_library_staging.source_versions v
                       WHERE v.textbook_id=t.id AND v.owner_uid=t.owner_uid)
               FROM source_library_staging.textbooks t
               WHERE t.id=%s::uuid AND t.owner_uid=%s::uuid AND t.r2_key=%s""",
            (textbook_id, owner_uid, r2_key))
        record = cur.fetchone()
    if not record:
        raise ValueError("Owner-scoped textbook not found")
    status, pages, size, passages, versions = record
    manifest = load_staging_review_manifest(r2, owner_uid=owner_uid, r2_key=r2_key)
    source_head = r2.head_object(Bucket="srna-staging-textbooks", Key=r2_key)
    metadata_consistent = (
        status == "ready" and pages == manifest["pdf_page_count"]
        and type(size) is int and size == source_head.get("ContentLength")
        and passages > 0)
    return {
        "indexed_passage_count": passages,
        "indexed_pdf_page_count": pages,
        "source_manifest_sha256": manifest["sha256"],
        "source_metadata_consistent": metadata_consistent,
        "source_version_count": versions,
        "historical_passage_provenance_verified": versions > 0,
        "safe_to_backfill_legacy_provenance": False,
        "requires_independent_reextraction_or_review": versions == 0,
    }
