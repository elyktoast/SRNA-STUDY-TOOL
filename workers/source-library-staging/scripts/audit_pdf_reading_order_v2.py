"""Read-only comparison against a source-version-bound original staging PDF.

Prints diagnostic counts and hashes only, never textbook excerpts or images.
Does not import passages, repair citations, approve pages, or invoke a model.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
import re
import unicodedata
from uuid import UUID

import fitz
from extract_textbook import page_text
from source_review_r2_loader_v2 import BUCKET, verified_staging_pdf_file


# Short continuity anchors from the two already inspected original pages.
# These are regression probes, not clinical answer keys or sufficient evidence.
NAGELHOUT_PROBES = {
    731: {'static_paragraph_continuity': 'lung tissue and chest wall alone'},
    732: {'dynamic_paragraph_continuity': 'lung tissue compliance in combination'},
}
NAGELHOUT_ID = '6f1b2869-d6ad-4adf-a9d8-888e8a3d9b9d'


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def compare_page(page, probes=None):
    legacy = page_text(page)
    candidate = page_text(page, reading_order='blocks')
    probes = probes or {}
    glyphs = lambda text: Counter(c for c in unicodedata.normalize('NFKC', text) if not c.isspace())
    # A separate raw character inventory distinguishes candidate loss from
    # omissions introduced by the legacy word/line reconstruction itself.
    raw = page.get_text('rawdict')
    original = ''.join(char['c'] for block in raw['blocks'] if block['type'] == 0
                       for line in block['lines'] for span in line['spans']
                       for char in span['chars'])
    differences = lambda a, b: {f'U+{ord(char):04X}': count
                                for char, count in sorted((glyphs(a)-glyphs(b)).items())}
    return {
        'legacy_sha256': hashlib.sha256(legacy.encode()).hexdigest(),
        'block_sha256': hashlib.sha256(candidate.encode()).hexdigest(),
        'text_changed': legacy != candidate,
        'non_whitespace_characters_preserved': glyphs(legacy) == glyphs(candidate),
        'legacy_matches_source_glyphs': glyphs(legacy) == glyphs(original),
        'block_matches_source_glyphs': glyphs(candidate) == glyphs(original),
        'legacy_only_codepoints': differences(legacy, candidate),
        'block_only_codepoints': differences(candidate, legacy),
        'legacy_wide_gap_rows': sum(bool(re.search(r'\S[ \t]{8,}\S', line))
                                    for line in page.get_text('text', sort=True).splitlines()),
        'text_block_count': sum(b[6] == 0 for b in page.get_text('blocks')),
        'legacy_continuity_checks': {key: normalized(value) in normalized(legacy)
                                     for key, value in probes.items()},
        'block_continuity_checks': {key: normalized(value) in normalized(candidate)
                                    for key, value in probes.items()},
    }


def audit(conn, client, *, owner_uid, textbook_id, pages):
    for value in (owner_uid, textbook_id):
        if not isinstance(value, str) or str(UUID(value)) != value.lower():
            raise ValueError('Canonical owner and textbook UUIDs required')
    if (not isinstance(pages, list) or not 1 <= len(pages) <= 20
            or any(type(page) is not int or page < 1 for page in pages)
            or len(pages) != len(set(pages))):
        raise ValueError('One to twenty distinct physical PDF pages required')
    with conn.cursor() as cur:
        cur.execute("""
          select t.filename,t.r2_key,t.file_size_bytes,t.page_count,v.source_sha256
          from source_library_staging.textbooks t
          join source_library_staging.source_versions v on v.textbook_id=t.id
            and v.owner_uid=t.owner_uid and v.r2_key=t.r2_key
            and v.file_size_bytes=t.file_size_bytes
          where t.owner_uid=%s::uuid and t.id=%s::uuid and t.status='ready'
          order by v.recorded_at desc limit 1
        """, (owner_uid, textbook_id))
        row = cur.fetchone()
    if not row:
        raise ValueError('Ready owned textbook with matching source provenance required')
    filename, key, size, count, digest = row
    if type(count) is not int or max(pages) > count:
        raise ValueError('Page outside recorded original PDF')
    probes = NAGELHOUT_PROBES if textbook_id == NAGELHOUT_ID else {}
    with verified_staging_pdf_file(client, owner_uid=owner_uid, r2_key=key,
                                  expected_sha256=digest, bucket=BUCKET) as path:
        if os.path.getsize(path) != size:
            raise ValueError('Original size differs from source provenance')
        with fitz.open(path) as doc:
            if len(doc) != count:
                raise ValueError('Original page count differs from source provenance')
            results = [{'pdf_page': page, **compare_page(doc[page-1], probes.get(page))}
                       for page in pages]
    passed = all(r['non_whitespace_characters_preserved'] and
                 all(r['block_continuity_checks'].values()) for r in results)
    return {'textbook_id': textbook_id, 'filename': filename,
            'source_sha256': digest, 'source_binding_verified': True,
            'pdf_page_count': count, 'pages': results, 'candidate_checks_passed': passed,
            'clinical_accuracy_verified': False, 'full_reading_order_verified': False,
            'database_writes': False, 'r2_writes': False, 'provider_calls': False,
            'index_replaced': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--owner-uid', required=True)
    parser.add_argument('--textbook-id', required=True)
    parser.add_argument('--pages', required=True)
    args = parser.parse_args()
    if os.environ.get('STAGING_ONLY') != 'true':
        raise SystemExit('Explicit staging-only execution required')
    import boto3
    import psycopg
    client = boto3.client('s3', region_name='auto',
                         endpoint_url='https://'+os.environ['STAGING_R2_ACCOUNT_ID']+'.r2.cloudflarestorage.com',
                         aws_access_key_id=os.environ['STAGING_R2_ACCESS_KEY_ID'],
                         aws_secret_access_key=os.environ['STAGING_R2_SECRET_ACCESS_KEY'])
    with psycopg.connect(os.environ['STAGING_DATABASE_URL']) as conn:
        with conn.transaction():
            conn.execute('SET TRANSACTION READ ONLY')
            result = audit(conn, client, owner_uid=args.owner_uid, textbook_id=args.textbook_id,
                           pages=[int(value) for value in args.pages.split(',')])
    print(json.dumps(result, indent=2))
    if not result['candidate_checks_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
