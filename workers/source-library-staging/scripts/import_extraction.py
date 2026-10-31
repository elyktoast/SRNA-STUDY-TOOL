#!/usr/bin/env python3
"""Import previously extracted staging passages into the private Supabase schema.

Requires: pip install 'psycopg[binary]'
Usage:
  python import_extraction.py ./extracted --dry-run
  DATABASE_URL=... python import_extraction.py ./extracted --apply

Only server-side operators with explicit staging database credentials should run this.
Never use the Supabase anon key, browser tokens, or a production database URL.
"""
import argparse
import json
import os
import re
from pathlib import Path

MAX_BATCH = 200
SCHEMA = "source_library_staging"


def read_jsonl(path):
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{line_number}: invalid JSON") from exc


def validate(folder):
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("status") != "extracted_not_indexed":
        raise ValueError("Unexpected extraction manifest")
    if manifest.get("citation_verified") is not False:
        raise ValueError("Extraction must not claim citation verification")
    owner, key = manifest.get("owner_uid"), manifest.get("r2_key")
    filename = manifest.get("filename")
    if (not isinstance(filename, str)
            or not re.fullmatch(r"[A-Za-z0-9._-]{1,150}\.pdf", filename, re.I)
            or filename in (".pdf", "..pdf")):
        raise ValueError("Invalid source PDF filename")
    if type(manifest.get("requires_ocr_review")) is not bool:
        raise ValueError("Invalid OCR review flag")
    if not isinstance(manifest.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", manifest["sha256"]):
        raise ValueError("Missing PDF SHA-256 digest")
    if type(manifest.get("size_bytes")) is not int or not 5 <= manifest["size_bytes"] <= 300 * 1024 * 1024:
        raise ValueError("Invalid source PDF size")
    if not isinstance(owner, str) or not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", owner, re.I) or not isinstance(key, str) or not key.startswith(owner + "/") or ".." in key or not key.lower().endswith(".pdf"):
        raise ValueError("Invalid owner/key relationship")
    page_count = manifest.get("pdf_page_count")
    if type(page_count) is not int or page_count < 1:
        raise ValueError("Invalid PDF page count")
    count, last = 0, -1
    for passage in read_jsonl(folder / "passages.jsonl"):
        idx = passage.get("chunk_index")
        start, end = passage.get("page_start"), passage.get("page_end")
        if type(idx) is not int or idx != last + 1:
            raise ValueError("Passages must have contiguous indexes")
        if type(start) is not int or type(end) is not int or start < 1 or end < start:
            raise ValueError("Invalid passage page reference")
        if end > page_count:
            raise ValueError("Passage outside document")
        if not isinstance(passage.get("content"), str) or not passage["content"].strip():
            raise ValueError("Empty passage")
        last = idx
        count += 1
    if type(manifest.get("passage_count")) is not int or count != manifest["passage_count"]:
        raise ValueError("Manifest passage count mismatch")
    if count == 0:
        raise ValueError("No searchable passages extracted; OCR or manual review required")
    low_pages = manifest.get("low_text_pages")
    if (not isinstance(low_pages, list) or any(type(p) is not int or p < 1 or p > page_count for p in low_pages)
            or len(set(low_pages)) != len(low_pages)
            or manifest["requires_ocr_review"] != bool(low_pages)):
        raise ValueError("Invalid low-text page metadata")
    image_pages = manifest.get("image_pages", [])
    if (not isinstance(image_pages, list)
            or any(type(p) is not int or p < 1 or p > page_count for p in image_pages)
            or len(set(image_pages)) != len(image_pages)):
        raise ValueError("Invalid embedded-image page metadata")
    # Optional visual sidecars are metadata only. Reject corrupted references
    # before any database writes, without treating proximity as verified meaning.
    assets_path = folder / "image_assets.json"
    links_path = folder / "passage_image_links.json"
    if assets_path.exists() != links_path.exists():
        raise ValueError("Incomplete image association sidecars")
    if assets_path.exists():
        assets = json.loads(assets_path.read_text(encoding="utf-8"))
        links = json.loads(links_path.read_text(encoding="utf-8"))
        if not isinstance(assets, list) or not isinstance(links, list):
            raise ValueError("Invalid image association sidecars")
        asset_pages = {}
        for asset in assets:
            if not isinstance(asset, dict):
                raise ValueError("Invalid image asset reference")
            aid, page = asset.get("asset_id"), asset.get("pdf_page")
            bbox = asset.get("bbox")
            if (not isinstance(aid, str) or not re.fullmatch(r"p[0-9]{4,}-x[0-9]+-n[0-9]+", aid)
                    or aid in asset_pages or type(page) is not int or page not in image_pages
                    or asset.get("source") != "original_pdf"
                    or asset.get("review_status") != "unreviewed"
                    or not isinstance(bbox, list) or len(bbox) != 4
                    or any(type(v) not in (int, float) or not -1e7 < v < 1e7 for v in bbox)
                    or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]):
                raise ValueError("Invalid image asset reference")
            asset_pages[aid] = page
        passage_pages = {p["chunk_index"]:p["page_start"]
                         for p in read_jsonl(folder / "passages.jsonl")}
        linked = set()
        for link in links:
            if not isinstance(link, dict):
                raise ValueError("Invalid passage image association")
            idx, page = link.get("chunk_index"), link.get("pdf_page")
            ids = link.get("candidate_asset_ids")
            if (type(idx) is not int or idx in linked
                    or type(page) is not int or passage_pages.get(idx) != page
                    or link.get("association") != "same_pdf_page_unverified"
                    or not isinstance(ids, list) or not ids
                    or any(not isinstance(aid, str) or asset_pages.get(aid) != page for aid in ids)
                    or len(ids) != len(set(ids))):
                raise ValueError("Invalid passage image association")
            linked.add(idx)
    # An embedded image can be a photo, chart, or decorative asset. Do not
    # equate image presence with missing text or successful OCR.
    # PDF bookmarks are provisional section boundaries, not verified print citations.
    sections_path = folder / "sections.jsonl"
    sections = list(read_jsonl(sections_path)) if sections_path.exists() else []
    if type(manifest.get("section_count", 0)) is not int or len(sections) != manifest.get("section_count", 0):
        raise ValueError("Manifest section count mismatch")
    previous_page = 0
    for section in sections:
        page = section.get("start_page")
        if (not isinstance(page, int) or isinstance(page, bool)
                or not 1 <= page <= manifest["pdf_page_count"]
                or not isinstance(section.get("heading"), str)
                or not section["heading"].strip()
                or section.get("source") != "pdf_bookmark"
                or type(section.get("level")) is not int
                or not 1 <= section["level"] <= 32):
            raise ValueError("Invalid PDF bookmark section")
        if page < previous_page:
            raise ValueError("PDF bookmark sections must be ordered by page")
        previous_page = page
    # Check the section metadata against the extracted page stream before DB writes.
    # A PDF page number is a physical position, not a verified printed citation.
    if manifest.get("page_numbering") not in (None, "physical_pdf_page_1_based"):
        raise ValueError("Unsupported page numbering")
    return manifest


def assert_safe_reindex(existing_sections):
    """Never replace a sectioned index until provenance-aware migration exists."""
    if type(existing_sections) is not int or existing_sections < 0:
        raise ValueError("Invalid existing section count")
    if existing_sections:
        raise ValueError(
            "Reindex blocked: existing chapter sections require preservation "
            "or explicit review before replacement"
        )


def validate_source_replacement(exists, prior_digest, incoming_digest):
    """Fail closed for legacy records and changed source content."""
    if not exists:
        return
    if prior_digest is None:
        raise ValueError("Reindex blocked: existing source fingerprint is unknown")
    if prior_digest != incoming_digest:
        raise ValueError("Reindex blocked: source PDF changed; create a new version")


def import_passages(folder, manifest, connection):
    # This is the central DB write boundary, including direct CLI and R2 imports.
    # Unauthenticated local page-review files must never clear extraction warnings.
    low = manifest.get("low_text_pages", [])
    failed = manifest.get("ocr_failed_pages", [])
    if (not isinstance(low, list) or not isinstance(failed, list)
            or any(type(p) is not int for p in low + failed)):
        raise ValueError("Invalid extraction review metadata")
    if type(manifest.get("requires_ocr_review")) is not bool:
        raise ValueError("Invalid extraction review flag")
    count = manifest.get("pdf_page_count")
    if type(count) is not int or count < 1 or any(
            p < 1 or p > count for p in low + failed):
        raise ValueError("Invalid extraction review page range")
    if len(set(low)) != len(low) or len(set(failed)) != len(failed):
        raise ValueError("Duplicate extraction review pages")
    if low or failed or manifest.get("requires_ocr_review") is True:
        raise ValueError(
            "Unresolved extraction review: central import requires trusted "
            "server-side page approval before indexing"
        )
    # Entire replacement is atomic. A failed import leaves the old index intact.
    with connection.transaction():
        with connection.cursor() as cur:
            # Serialize even first-time imports of the same R2 key, before row creation.
            # Row locks alone cannot protect a textbook that does not exist yet.
            cur.execute(
                "select pg_advisory_xact_lock(hashtextextended(%s, 0))",
                ("r2:" + manifest["owner_uid"] + ":" + manifest["r2_key"],))
            # Lock the existing textbook row before changing any index state.
            # A legacy record without a fingerprint must be reviewed, not guessed.
            cur.execute(
                """select id from source_library_staging.textbooks
                   where r2_key=%s for update""", (manifest["r2_key"],))
            existing = cur.fetchone()
            if existing is not None:
                cur.execute(
                    """select source_sha256 from source_library_staging.source_versions
                       where textbook_id=%s order by recorded_at desc, id desc limit 1""",
                    (existing[0],))
                prior = cur.fetchone()
                validate_source_replacement(True, prior[0] if prior else None, manifest["sha256"])
            # Serialize imports of identical content for the same owner.
            cur.execute(
                """select pg_advisory_xact_lock(
                     hashtextextended(%s, 0))""",
                (manifest["owner_uid"] + ":" + manifest["sha256"],))
            cur.execute(
                """select r2_key from source_library_staging.source_versions
                   where owner_uid=%s and source_sha256=%s and r2_key<>%s
                   limit 1""",
                (manifest["owner_uid"], manifest["sha256"], manifest["r2_key"]))
            duplicate = cur.fetchone()
            if duplicate is not None:
                raise ValueError(
                    "Duplicate textbook content already indexed under another R2 key"
                )
            cur.execute(
                """insert into source_library_staging.textbooks
                   (owner_uid,r2_key,filename,file_size_bytes,status,page_count,requires_ocr_review,low_text_page_count)
                   values (%s,%s,%s,%s,'indexing',%s,%s,%s)
                   on conflict (r2_key) do update
                   set filename=excluded.filename,file_size_bytes=excluded.file_size_bytes,
                       page_count=excluded.page_count,requires_ocr_review=excluded.requires_ocr_review,
                       low_text_page_count=excluded.low_text_page_count,status='indexing',error_message=null,
                       updated_at=now()
                   where source_library_staging.textbooks.owner_uid=excluded.owner_uid
                   returning id""",
                (manifest["owner_uid"], manifest["r2_key"], manifest["filename"],
                 manifest["size_bytes"], manifest["pdf_page_count"],
                 manifest["requires_ocr_review"], len(manifest.get("low_text_pages", []))),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Existing textbook belongs to another owner")
            textbook_id = row[0]
            # Provenance is persisted in the same transaction as the index.
            # The uniqueness constraint makes repeat imports idempotent.
            cur.execute(
                """insert into source_library_staging.source_versions
                   (textbook_id,owner_uid,source_sha256,file_size_bytes,r2_key)
                   values (%s,%s,%s,%s,%s)
                   on conflict (textbook_id,source_sha256) do nothing""",
                (textbook_id, manifest["owner_uid"], manifest["sha256"],
                 manifest["size_bytes"], manifest["r2_key"]))
            # Reindex only passage text when sections already exist.
            # Preserve reviewed headings, page boundaries, hierarchy and UUIDs.
            cur.execute(
                """select id,start_page from source_library_staging.sections
                   where textbook_id=%s order by section_order""", (textbook_id,))
            preserved_sections = cur.fetchall()
            if preserved_sections and any(type(page) is not int or not 1 <= page <= manifest['pdf_page_count'] for _, page in preserved_sections):
                raise ValueError("Reindex blocked: existing section has invalid start page")
            preserved_sections.sort(key=lambda item: item[1])
            cur.execute("delete from source_library_staging.passages where textbook_id=%s", (textbook_id,))
            section_ids = [(page, sid) for sid, page in preserved_sections]
            if not preserved_sections:
                # Initial indexing only: PDF bookmarks are provisional.
                parent_stack = []
                sections_path = folder / "sections.jsonl"
                if sections_path.exists():
                    for order, section in enumerate(read_jsonl(sections_path)):
                        level = section["level"]
                        while parent_stack and parent_stack[-1][0] >= level:
                            parent_stack.pop()
                        parent_id = parent_stack[-1][1] if parent_stack else None
                        cur.execute(
                            """insert into source_library_staging.sections
                               (textbook_id,parent_section_id,heading,section_order,start_page)
                               values (%s,%s,%s,%s,%s) returning id""",
                            (textbook_id, parent_id, section["heading"], order,
                             section["start_page"]),
                        )
                        section_id = cur.fetchone()[0]
                        parent_stack.append((level, section_id))
                        section_ids.append((section["start_page"], section_id))
            batch = []
            for item in read_jsonl(folder / "passages.jsonl"):
                section_id = next((sid for page, sid in reversed(section_ids)
                                   if page <= item["page_start"]), None)
                batch.append((textbook_id,section_id,item["chunk_index"],item["page_start"],
                              item["page_end"],item["content"]))
                if len(batch) >= MAX_BATCH:
                    cur.executemany(
                        """insert into source_library_staging.passages
                           (textbook_id,section_id,chunk_index,page_start,page_end,content)
                           values (%s,%s,%s,%s,%s,%s)""", batch)
                    batch.clear()
            if batch:
                cur.executemany(
                    """insert into source_library_staging.passages
                       (textbook_id,section_id,chunk_index,page_start,page_end,content)
                       values (%s,%s,%s,%s,%s,%s)""", batch)
            # 'ready' means searchable text exists, not verified citations or OCR completeness.
            cur.execute(
                """update source_library_staging.textbooks
                   set status='ready',indexed_at=now(),updated_at=now()
                   where id=%s""", (textbook_id,))
            return str(textbook_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    manifest = validate(args.folder)
    if args.dry_run:
        print(json.dumps({"valid": True, "passages": manifest["passage_count"],
                          "pdf_pages": manifest["pdf_page_count"],
                          "requires_ocr_review": manifest["requires_ocr_review"]}, indent=2))
        return
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL required for --apply")
    import psycopg
    with psycopg.connect(database_url, autocommit=False) as conn:
        textbook_id = import_passages(args.folder, manifest, conn)
    print(json.dumps({"imported": True, "textbook_id": textbook_id,
                      "passages": manifest["passage_count"]}))


if __name__ == "__main__":
    main()
