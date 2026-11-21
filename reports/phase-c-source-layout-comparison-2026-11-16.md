# Original-file layout comparison — November 16, 2026

## Verified improvement

[Read-only original-file comparison](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43888121531)
passed for six Nagelhout PDF pages. The PDF was streamed to a temporary file,
verified against its existing owner-scoped source-version SHA-256, inspected,
and removed. PostgreSQL ran in a read-only transaction. No passages, source
objects, review decisions, citations, or drafts were changed; no model ran.

| Physical PDF page | Candidate matches original glyph inventory | Legacy wide-gap rows | Continuity probe |
| --- | --- | ---: | --- |
| 135 | Yes | 14 | Not adjudicated |
| 213 | Yes | 16 | Not adjudicated |
| 566 | Yes | 64 | Not adjudicated |
| 599 | Yes | 23 | Not adjudicated |
| 731 | Yes | 12 | Static-compliance paragraph repaired |
| 732 | Yes | 11 | Dynamic-compliance paragraph repaired |

Both continuity probes failed with legacy row-based extraction and passed with
the block candidate. These narrow probes do not establish complete clinical
accuracy, column order, table associations, equations, or other books' layouts.

## Character-difference investigation

The first comparison correctly failed when the candidate did not match the
legacy character counts. A second diagnostic retained that gate and compared
each method with an independent inventory from the PDF's raw character spans.
The candidate matched the original inventory on all six pages; legacy text
omitted control glyphs. Diagnostics disclose Unicode codepoints and counts,
not textbook passages or images.

All six pages include one unmapped U+0001 glyph. Page 599 additionally contains
two U+0011 glyphs and one each of U+0018 and U+0019. Their clinical meaning has
not been inferred. The final audit measures conservation against the original
glyph inventory and continues to report these unresolved symbols explicitly.
`ready_for_index_replacement` and `full_reading_order_verified` remain false.

No extraction mode was promoted to the default. The existing Nagelhout index
and its 7,844 passage IDs remain intact. Resolve symbol/table interpretation
and broaden the original-file sample before any targeted index repair.

## Code and validation

The read-only operator audit and a branch-scoped, explicit-marker workflow are
in PR #190. The workflow reads only staging R2 and database resources and
uploads no textbook artifacts. Tests cover invalid inputs, source ownership and
provenance, page boundaries, character loss, omitted control glyphs, absence of
text/path disclosure, and read-only reporting.

- Local Python: 991 tests ran, 988 passed and three skipped.
- Repository validation, performance budgets, and whitespace checks passed.
- [Final source-code CI](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43888145583)
  passed Node, Python, container build, and repository validation.

## Remaining goal milestones

The indexing and unpublished-draft plumbing is established, and a prior single
MC acceptance exists. The latest generation failed quality acceptance, so
reliably producing strong questions with minimal editing remains unproven.

1. Repair and validate evidence reading order, symbols, and source provenance.
2. Pass representative question generation with supported explanations and
   independent correct-answer/distractor checks, respecting the one-rewrite cap.
3. Complete lecture-upload and all-five-format live acceptance, including
   unsupported lecture concepts and visual formats.
4. Finish multi-textbook evidence within one generated question and verify a
   representative batch, citation integrity, and duplicate handling.

An implementation percentage or completion date is not supported by the current
acceptance evidence. One further successful question would not close these
remaining milestones.
