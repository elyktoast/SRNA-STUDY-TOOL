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
    if not isinstance(owner, str) or not isinstance(key, str) or not key.startswith(owner + "/"):
        raise ValueError("Invalid owner/key relationship")
    count, last = 0, -1
    for passage in read_jsonl(folder / "passages.jsonl"):
        idx = passage.get("chunk_index")
        start, end = passage.get("page_start"), passage.get("page_end")
        if not isinstance(idx, int) or idx != last + 1:
            raise ValueError("Passages must have contiguous indexes")
        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
            raise ValueError("Invalid passage page reference")
        if end > manifest.get("pdf_page_count", 0):
            raise ValueError("Passage outside document")
        if not isinstance(passage.get("content"), str) or not passage["content"].strip():
            raise ValueError("Empty passage")
        last = idx
        count += 1
    if count != manifest.get("passage_count"):
        raise ValueError("Manifest passage count mismatch")
    if count == 0:
        raise ValueError("No searchable passages extracted; OCR or manual review required")
    return manifest


def import_passages(folder, manifest, connection):
    # Entire replacement is atomic. A failed import leaves the old index intact.
    with connection.transaction():
        with connection.cursor() as cur:
            cur.execute(
                """insert into source_library_staging.textbooks
                   (owner_uid,r2_key,filename,file_size_bytes,status,page_count)
                   values (%s,%s,%s,%s,'indexing',%s)
                   on conflict (r2_key) do update
                   set filename=excluded.filename,file_size_bytes=excluded.file_size_bytes,
                       page_count=excluded.page_count,status='indexing',error_message=null,
                       updated_at=now()
                   where source_library_staging.textbooks.owner_uid=excluded.owner_uid
                   returning id""",
                (manifest["owner_uid"], manifest["r2_key"], manifest["filename"],
                 manifest["size_bytes"], manifest["pdf_page_count"]),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Existing textbook belongs to another owner")
            textbook_id = row[0]
            cur.execute("delete from source_library_staging.passages where textbook_id=%s", (textbook_id,))
            cur.execute("delete from source_library_staging.sections where textbook_id=%s", (textbook_id,))
            batch = []
            for item in read_jsonl(folder / "passages.jsonl"):
                batch.append((textbook_id,item["chunk_index"],item["page_start"],
                              item["page_end"],item["content"]))
                if len(batch) >= MAX_BATCH:
                    cur.executemany(
                        """insert into source_library_staging.passages
                           (textbook_id,chunk_index,page_start,page_end,content)
                           values (%s,%s,%s,%s,%s)""", batch)
                    batch.clear()
            if batch:
                cur.executemany(
                    """insert into source_library_staging.passages
                       (textbook_id,chunk_index,page_start,page_end,content)
                       values (%s,%s,%s,%s,%s)""", batch)
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
