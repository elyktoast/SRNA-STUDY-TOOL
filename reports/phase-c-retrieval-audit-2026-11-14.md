# Phase C retrieval audit — November 14, 2026 (Eastern)

## Verified scope

Audited `fix/board-question-quality` at
`d859672e4ac4dcc7ba75e1a8672f4f12a8460269` against the connected staging
database and deployment. No textbook reindexing, source alteration, production
data writes, approval, publication, or production deployment was performed.

Cloudflare Pages staging deployment `5dd4aca3-5c87-451c-a76f-e13f874d09e5`
succeeded with this exact commit. Reviewer gateway deployment
`ab07db23-fb33-41e5-8581-a5d7cb9569a0` serves version
`812048c8-277d-41a1-b386-98f2c3eed0f0`; the PR deployment notification
also identifies `d859672e` as its source. This audit does not certify the
container image independently.

`main` remains `fa20a18e840cf6fa9466122fe511b5d5ba08a0ce`; the current
generation work is in open PR #189. The only other remote branch,
`fix/evidence-preflight-limit-label`, has two unique commits about the former
five-result label. Current code already labels the 20-result preflight and
eight-result generation limits; do not merge that older branch wholesale.

| Book | PDF pages | Passages | Sections | Matching source versions |
| --- | ---: | ---: | ---: | ---: |
| Miller | 13,364 | 17,897 | 932 | 1 |
| Barash | 5,335 | 9,389 | 3,015 | 1 |
| Jaffe | 3,469 | 4,890 | 99 | 1 |
| Hines/Stoelting | 721 | 3,003 | 0 | 1 |
| Nagelhout/Elisha | 1,660 | 7,844 | 0 | 1 |
| Flood | 3,011 | 4,470 | 1,967 | 1 |
| Ehrenwerth | 656 | 2,575 | 1,098 | 1 |
| OR guide | 420 | 574 | 0 | **0** |

All eight books are `ready` with `indexed_at` populated: 28,636 PDF pages and
50,642 passages. No missing search vectors or out-of-range/reversed PDF page
coordinates were found. These checks establish database consistency, not that
the excerpt actually appears on the cited original page.

Extraction derives sections from explicit PDF bookmarks (`doc.get_toc`), not
inferred chapter headings. Zero sections therefore do not block text search;
chapter filtering is unavailable for Hines, Nagelhout, and the OR guide. The OR
guide additionally lacks a source-version record matching its current key/size.
Do not backfill a guessed digest or reindex solely to manufacture chapters.

## Live retrieval findings and bounded repair

Queried six topics separately for every book: propofol, laryngoscopy, carbon
dioxide, aortic stenosis, laparoscopy, and neuromuscular blockade. There were
matches in 47/48 book/topic pairs. Ehrenwerth had no aortic-stenosis match;
this negative result alone is not an indexing defect. These are lexical probes,
not a clinically adjudicated recall benchmark.

The production search's cover-density rank sometimes promotes reference lists
and indexes over teaching content. The repair demotes only explicitly labelled
back matter, preserving all candidates, owner/book/page filters, source IDs,
verbatim excerpts, and the existing rank within each group.

Executed the exact new ordering expression against staging in read-only SQL:

| Query | Old top PDF page | New top PDF page |
| --- | ---: | ---: |
| Miller: carbon dioxide | 12,868 (Index) | 7,516 |
| Nagelhout: laryngoscopy | 1,287 (References) | 566 |
| Nagelhout: neuromuscular blockade | 221 (References) | 213 |

Other reference fragments without an explicit label can still rank highly,
including the Jaffe/Miller laparoscopy probes. This is a limited improvement,
not complete reference detection or evidence sufficiency verification. No
claim that the replacement top results alone support an entire question.

The exact production SQL expression also passed an eight-row, read-only
PostgreSQL regression: labelled back matter was demoted, numbered clinical
steps and an `Index of refraction` heading stayed eligible as teaching content,
and no rows were dropped. The reusable test is
`test_search_ranking_postgres_v2.py`; set the private
`SRNA_RETRIEVAL_TEST_DATABASE_URL` to run it through unittest. Without that
explicit credential it skips. Its SQL was separately executed successfully
through the connected database during this audit.

## Deployed behavior and remaining gaps

- The signed-in staging AI catalog lists all eight books after refresh.
- Hines `aortic stenosis`, NCE/I.B.1/MC, returned 20 indexed passages through
  the deployed authenticated preflight. No generation is implied by preflight.
- The reviewer boundary smoke test was stale: a POST without JSON received
  HTTP 400 while approval was enabled. The repaired probe sends valid JSON
  without authorization and requires 401/403. It returned 401; all remaining
  reviewer auth/CORS probes passed. This does not approve any page.
- The existing November 10 Eastern acceptance draft
  `43d13b5b-bceb-483a-bec0-d3c77231a45b` remains `pending_review` in staging.
  It is historical evidence, not a fresh generation in this audit.
- A fresh UI generation attempt reached the browser confirmation prompt, but
  browser control timed out while accepting it. No new checkpoint or saved
  draft was observed. Do not retry automatically or claim a new success.
- Shell GitHub credentials and private staging runtime secrets are unavailable
  in this workspace. Connected GitHub tools do not expose workflow dispatch.
- All five formats exist in the schema/pipeline and offline tests. This audit
  has not live-validated five formats, a lecture upload, a batch, provider
  fallback, original page images across eight books, editions, or printed pages.
- Lecture planning can search all books, but `staging_http_jobs` chooses one
  evidence book for each generation job, and checkpointed generation requires
  an explicit textbook ID. This does not yet fulfill multi-book evidence within
  a generated question.

## Validation and next milestone

- 975 Python tests ran: 972 passed, three skipped (including the new
  credential-gated PostgreSQL test); its SQL passed separately on staging.
- All 163 staging Node tests passed again after the repair.
- Repository validation, performance budgets, and diff whitespace checks passed.
- Both public staging Worker and repaired reviewer boundary smoke tests passed.

Next: resume the authenticated UI or authorized Actions generation test once
browser control works, inspect a newly saved draft and its source pages, then
finish the OR guide provenance comparison and measure retrieval relevance
against independently inspected source pages. Validate all five formats and a
lecture batch before describing Phase C as complete. No automatic publication.
