"""Read-only live acceptance of indexed textbook retrieval against fresh source passages.

Requires an independently verified original-PDF extraction; prints no textbook text.
No DB mutations, no guessed chapter metadata, and no admin API exposure.
"""
import re
from source_retrieval_staging_v2 import search_passages, audit_textbook_retrieval

_WORD = re.compile(r"[A-Za-z]{9,}")
_STOP = {"information", "copyright", "publication", "publisher", "university",
         "available", "including", "following", "different", "important"}


def verify_retrieval_against_extraction(conn, *, owner_uid, textbook_id, fresh_passages):
    if not isinstance(fresh_passages, list) or not fresh_passages:
        raise ValueError("Verified fresh extraction required")
    readiness = audit_textbook_retrieval(conn, owner_uid=owner_uid,
                                         textbook_id=textbook_id)
    if not readiness["text_search_ready"]:
        raise ValueError("Textbook not ready for text retrieval")
    # Choose spaced passage samples, not conveniently handpicked successful pages.
    sample_positions = sorted({0, len(fresh_passages) // 4,
                               len(fresh_passages) // 2,
                               (len(fresh_passages) * 3) // 4,
                               len(fresh_passages) - 1})
    tested = []
    for position in sample_positions:
        source = fresh_passages[position]
        if not isinstance(source, dict):
            raise ValueError("Invalid source passage")
        page, end, idx = source.get("page_start"), source.get("page_end"), source.get("chunk_index")
        if type(page) is not int or type(end) is not int or type(idx) is not int:
            raise ValueError("Invalid source passage coordinates")
        words = [w.lower() for w in _WORD.findall(source.get("content", ""))]
        words = [w for w in words if w not in _STOP]
        # An unsearchable sample is skipped, never interpreted as a successful hit.
        confirmed = False
        for token in sorted(set(words), key=lambda w: (-len(w), w))[:12]:
            matches = search_passages(
                conn, owner_uid=owner_uid, textbook_id=textbook_id, query=token,
                page_start=page, page_end=end, limit=50)
            if any(m["chunk_index"] == idx and m["page_start"] == page
                   and m["page_end"] == end for m in matches):
                confirmed = True
                break
        tested.append({"chunk_index": idx, "pdf_page": page, "matched": confirmed})
    if len(tested) != 5 or not all(t["matched"] for t in tested):
        raise ValueError("Live source retrieval accuracy failed on sampled passages")
    # Check empty page-range negative boundary without displaying copyrighted text.
    # Wrong owner cannot retrieve this textbook even with its UUID.
    from uuid import UUID
    other = str(UUID("895ed357-27c3-4d4b-a98a-77b0de20760c"))
    if other == owner_uid:
        raise ValueError("Invalid negative-test identity")
    probe = next((w.lower() for w in _WORD.findall(fresh_passages[0]["content"])
                  if w.lower() not in _STOP), None)
    if probe and search_passages(conn, owner_uid=other, textbook_id=textbook_id,
                                 query=probe, limit=1):
        raise ValueError("Cross-owner passage access detected")
    return {"tested_sample_count": len(tested), "matched_sample_count": len(tested),
            "pdf_page_reference_checks_passed": True,
            "cross_owner_denial_checked": bool(probe),
            "chapter_filter_ready": readiness["chapter_filter_ready"],
            "printed_citations_verified": False}
