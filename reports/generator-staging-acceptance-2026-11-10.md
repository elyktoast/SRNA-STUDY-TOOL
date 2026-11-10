# One-question staging acceptance — November 10, 2026

> Superseded by post-acceptance audit: the earlier option reviewer cited only one component of the paired correct answer. Its automated pass did not establish complete independent key evidence. The question remains unpublished; stricter v17 coverage verification is pending.

## Verified outcome

One authenticated end-to-end staging generation passed the required automated
acceptance checks and saved one private, unpublished draft. No approval or
publication was performed.

- Draft: `578abeb7-edfa-4864-9a2f-cb0e611a5cde`
- Item: `ab4f5532-7ea1-4303-b9df-e1e2f772e9d3`
- Saved: 2026-11-10 20:53:08 UTC
- Status: `pending_review`; `reviewed_by` and `reviewed_at` remain null.
- Classification: NCE MC, I.A.2 Respiratory, application.
- Source: ready indexed `Nagelhout__Elisha_.pdf`, PDF pages 731–732.
- Both stored excerpts match the current owned index exactly. All 19 explanatory
  support-quote references were independently checked as verbatim indexed text.
- Exactly one draft record exists for the item ID.
- One protected automatic rewrite corrected flagged blueprint/context/reasoning
  and distractor issues. Its complete rechecks passed; zero generator issues
  remained. The key, keyed text and concept source IDs remain protected.

| Automated check | Result |
| --- | --- |
| Canonical schema | Pass |
| Deterministic wording and numeric guard | Pass |
| Indexed source/citation validation | Pass |
| Independent blind answer | Pass |
| Concept and rationale source review, all 15 fields | Pass |
| Independent editorial quality, all seven criteria | Pass |
| Changed-case fresh blind solve with different expected answer | Pass |
| Five shuffled options-only trials | Pass |
| Independent option retrieval and source adjudication | Pass |
| Unpublished persistence and subsequent authenticated read | Pass |

The final stem, choices and explanations were inspected after persistence. The
question distinguishes airway resistance from lung/chest-wall compliance and
explains why each alternative fails under the stated conditions. The full item
and copyrighted source excerpts remain in the private staging bank, not this
public report.

## Recovery changes

Provider failures had several distinct causes, rather than one interchangeable
upstream outage. Groq GPT-OSS 120B reached its explicit daily authoring quota.
Cloudflare GPT-OSS responses exposed response-format/contract failures, and exact
indexed-source planning probes also produced incorrect shared-dependency
reasoning. Staging authoring now uses verified Cloudflare `@cf/zai-org/glm-5.3`
with its documented wrapped JSON schema and bounded low reasoning. The recorded
underlying generator is `zai-org/glm-5.3`. Malformed, incomplete and refused
provider output still fails closed.

Independent Qwen source/blind/option reviews and GPT-OSS 20B editorial review
remain on Groq, separate from the author. Gemini and legacy hybrid generation
remain disabled. Per-minute review limits still occur; explicit bounded waits
were exercised in the successful run. A prior client connection reset did not
justify duplicate generation: its completed checkpoint and private saved result
were inspected before proceeding.

Private MC planning now names clinical response variables, renders parallel
choices without repeated labels, and diagnoses exact key/choice/condition
mismatches. All condition-dependent findings must belong to the complete
replaceable case. Existing canonical author edits can be tested without asking
another model to transcribe the same punctuation again. Independent editorial
rejection or a wrong changed-case blind answer still fails; a regression verifies
both and rejects appended unverified claims.

The source-explanation schema requires references for supported judgments while
allowing every field to be rejected. Existing exact-span, authorized-passage and
complete-field checks remain mandatory. Independent option retrieval retains up
to two context passages within its existing per-option budget, so a paired
concept does not lose its second source page. Direct option matches keep
priority. Retrieval alone never supplies a clinical verdict.

Textbook extraction/indexing, other question formats, independent review,
authentication/RLS, the one-rewrite limit and publication controls are preserved.
No database schema or indexing changes were made.

## Reproducible verification

Runtime code commit: `c06e53296a5582443e865c9019b17d08d2e72eef`

- [CI 42897945056](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/42897945056):
  885 Python tests, one skipped; 126 Node tests; container build and repository
  validation passed.
- [Deployment 42897941447](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/42897941447):
  settled container rollout, authenticated smoke and expected runtime authoring
  contract passed.
- [Acceptance 42898227641](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/42898227641):
  fresh generation, one rewrite, independent rechecks, private save and
  authenticated retrieval passed at 20:53:09 UTC.

## Limits and release state

This verifies one staging API flow, not batch reliability or empirical item
hardness. Response statistics remain fresh at zero/null; no psychometric results
were fabricated. Human clinical review and semantic duplicate verification remain
pending, and publication remains blocked. Edition and printed-page verification
are explicitly unrecorded/unverified; citations identify PDF pages only.

The consolidated changes remain in PR #189. Production/main was not merged or
deployed. This acceptance does not claim a fresh browser/admin-UI release test.
Larger batches and cross-textbook sourcing remain deferred as requested.
