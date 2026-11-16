# Phase C acceptance recovery — November 16, 2026

## Live acceptance result

The previously dispatched [one-question acceptance run](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43666543863)
completed and **failed quality acceptance**. It ran the deployed
`d859672e4ac4dcc7ba75e1a8672f4f12a8460269` implementation and saved
`e8919d19-c875-422b-b38c-b3622718ae0f` on November 14 at 9:16 PM Eastern.
No duplicate generation was started during this continuation.

Schema, deterministic wording, source-index matching, original blind answer,
and options-only screening passed. Explanation evidence retained R-2.4 and
the independently solved changed case retained R-5.3 after one rewrite.
Independent option adjudication did not complete; semantic duplicates and
human review remain pending. This is not an accepted question.

The failed draft was changed from `pending_review` to `needs_revision` using
an exact-ID, owner-scoped conditional staging update. Its question and evidence
were preserved. `reviewed_by` and `reviewed_at` remain null; no human clinical
approval or publication was recorded.

Both stored citations still match current indexed passages verbatim, the
correct textbook, and the recorded physical PDF pages. Matching an index is
not proof of extraction quality or complete support for every explanation.

## Source-page access restored

Fresh preview attempts failed twice with HTTP 503. Cloudflare's gateway logs
identified `STORAGE_MISSING_SOURCE_OR_QUEUE` and
`trusted_manifest_unavailable`, rather than a provider or model failure.

[Source recovery run 43882868826](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43882868826)
successfully published Nagelhout's private source-bound review queue and its
attestation. `apply=false` and `force_reindex=false`; the run did not import
passages or approve pages. It reported 1,660 PDF pages, 7,844 extracted
passages, no unresolved review pages, and `approval_enabled=false`.

The recovered PDF SHA-256 matches the existing staging source-version record:
`f34654a6c1c573ce5707a4ac105f826890b1bfb7923e62f27212113e4c828a71`.
Original size: 184,597,014 bytes.

The authenticated source viewer then successfully rendered physical PDF pages
731 and 732. Both were visually inspected without acknowledgment or approval.
The specific printed-page mappings visible on those images are 620 and 621,
respectively; other page mappings and the edition remain unverified.

Visual comparison confirms that the index interleaves adjacent text columns.
For example, static-compliance prose in the left column is combined with an
equation introduction in the right column; dynamic-compliance prose is combined
with separate surfactant/neonatal material. Do not interpret those combinations
as continuous textbook assertions. This defect does not by itself explain the
changed-case blind solver disagreement, since the blind solver receives no
answer key, rationale, or source excerpts.

## Code changes on the review branch

1. Reviewer configuration: entry pages that omit `reviewerApiUrl` now use the
   exact deployed staging gateway. Explicit empty overrides remain disabled;
   production origins, lookalikes, and arbitrary workers.dev hosts remain
   rejected. Existing PNG SHA-256 and source checks remain enforced.
2. Draft state: an automated stage with `flag` or `fail` now causes persistence
   as `needs_revision`. Pending duplicate/human checks alone retain
   `pending_review`. Acceptance logging occurs before its status assertion so
   the exact failed stages are visible even when automatic revision is needed.
3. Extraction candidate: `extract_textbook.py --reading-order blocks` preserves
   paragraph blocks instead of recombining adjacent columns into text rows.
   It passes real synthetic two-column PDF regressions and preserves all test
   tokens and physical-page coordinates. **This remains opt-in and has not been
   validated against the original Nagelhout file.** It does not guarantee full
   column, table, equation, figure, or OCR reading order. The default remains
   `legacy`; no indexed source text, IDs, or citations were replaced.

The first follow-up CI run passed Node, Python, and container checks but caught
a stale frontend build marker. The marker was updated; final CI must pass
before merging or deploying these changes.

## Validation and next work

- Local Python: 983 tests ran, 980 passed and three skipped.
- Staging Node suite: all 164 tests passed.
- Repository validation, performance budgets, and whitespace checks passed.
- Five new real-PDF tests cover paragraph integrity, word preservation,
  TextPage compatibility, single-column/blank pages, physical-page metadata,
  and rejection of an invalid extraction mode before file access.

Next, run a read-only comparison of block extraction against the now-accessible
original Nagelhout pages, expanding to representative two-column pages in the
other books. Inspect tables and equations separately before any targeted index
repair. Revisit retrieval context completeness for explanation relevance and
independent changed-case review without bypassing either gate. Only then run
another paid generation. The OR guide provenance, cross-book evidence within
one generated item, five-format live acceptance, lecture upload, and batch
acceptance remain open. Production and automatic publication remain untouched.
