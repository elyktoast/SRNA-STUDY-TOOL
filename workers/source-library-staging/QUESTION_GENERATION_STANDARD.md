# Governing question generation standard

**NCE/SEE Item Generation Standard v2.0 — October 31, 2026** is the sole governing specification for new textbook-grounded items (R-19.1). It supersedes earlier rulebooks. The owner-provided nine-page PDF is the authoritative document; this file is an implementation pointer, not a replacement or paraphrased copy. Do not publish private textbook excerpts.

## Implementation order

1. **Section 12.1**: seven-stage check pipeline; stages 1–5 in code, stage 6 separate blind model, stage 7 human clinical approval. One rewrite only; never auto-approve.
2. **Section 15**: versioned item JSON contract, evidence IDs, concept card, five formats, self-check rule IDs, review state, audit and statistics.
3. **Section 17**: private indexing with page images, concept/draft/rationale/screening as separate calls, format-specific rendering/scoring, dry-run default, security and regression tests.
4. **Section 18**: drafting system prompt using selected topic, concept card and retrieved passages only.

All other sections remain binding on the generator and reviewers. Preserve stable R-* rule IDs in diagnostics and audits.

## Differences from earlier staging prototypes

- Multi-select: 4–6 options; explicit '(Select 2.)' or '(Select 3.)' (R-7.2), not 4–8.
- Drag-and-drop: four items and four targets, one-to-one (R-7.4); experimental multiple-use matching must be separately labeled and must not silently override v2.0.
- Numeric short answer is a genuine numeric-entry format; hotspot requires a licensed/original figure and region metadata.
- Ban true/false, flashcards and fill-in-the-blank (R-7.6).
- Use reasoning levels recall/application/analysis, about one-third each; default format target per 100: 70 MC / 12 MS / 6 SA / 6 DD / 6 HS (R-10).
- The v2.0 Section 15 JSON is the canonical authoring schema. Existing legacy question-bank fields need a tested adapter, not an undocumented substitution.
- Rule precedence: acceptance > accuracy > evidence > key > format > style (R-0.5).

**Status:** Implementation pointer only. Existing code is not yet fully compliant. Do not represent these requirements as shipped until the corresponding code and tests pass.
