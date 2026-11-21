# Flood Pharmacology — manual divider review handoff (staging only)

Status: **Human-reported review; not a database approval or import authorization.**

On 2026-11-12, the source owner reported personally inspecting each of the seven flagged physical PDF pages and identifying all as non-content section/header dividers. The owner supplied a screenshot of physical PDF page 2882 showing a “SUBJECT INDEX” divider. The other six page classifications are based on the owner's statement, not separately captured page images.

- Staging owner UID: `c003287a-10ce-4cc9-926e-ef7c3a162a26`
- Source R2 key: `c003287a-10ce-4cc9-926e-ef7c3a162a26/1878c3ce-7202-4569-82a0-5029d77b2054.pdf`
- Expected source SHA-256: `c831b51da96bd4d4178ea6913919d6b4a167c547590d4caf6c07c82e948c5aba`
- Physical PDF pages: **7, 10, 26, 29, 104, 2846, 2882**
- Requested review note: `Reviewed by source owner: non-content section/header divider; no educational text to OCR or index.`

## Required protected follow-through

1. Revalidate the verified R2 attestation, manifest, source SHA-256, owner identity, and page count (3011) against the deployed staging source.
2. Authenticate the owner as an active authorized reviewer using the protected staging role store. Do not use a user-provided reviewer ID or admin flag.
3. Present or securely acknowledge each exact verified page image through an accepted inspection protocol. Do not fabricate an inspection receipt from this handoff or the chat statement.
4. Record each page-specific approval and review note through the protected server-side decision writer with one-time receipts, source/page binding, and transactional nonce consumption.
5. Verify all seven approvals through the import authorization query. Exclude these divider pages from searchable content while preserving physical PDF numbering.
6. Run import dry-run and retrieval checks; obtain separate authorization before applying any database import.

**Never** clear `requires_ocr_review`, modify extraction metadata to suppress flags, insert synthetic approvals, bypass authorization, or claim this handoff is proof of completed live acceptance.
