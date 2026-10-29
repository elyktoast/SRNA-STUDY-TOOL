# AI Adaptive — Phase 1 audit

Status: discovery only; no production schema or runtime changes.

## Confirmed baseline
- Existing CAT spans 7,000 canonical questions across Equipment Exam 1, Basic Principles Exam 1 and Clinical Pharmacology; equivalent-content filtering leaves 6,774 candidates before history exclusions (`docs/CROSS_COURSE_CAT.md`). Equipment Exam 2 should be separately assessed before adding to cross-course AI Adaptive.
- Existing session logic preserves owning-course identities, reservations, first attempts and resume state.
- CAT termination defaults to observe mode, 25 minimum and 75 maximum questions, with calibration gates (`equipment/assets/cat-termination.js`). Do not imply psychometric calibration merely from stored records.
- Existing operator admin role uses private table and `private.snar_is_admin(auth.uid())` in server-side functions (`legal/ADMIN_OPERATIONS.md`). Reuse it, but verify grants and RLS.
- Generator currently hardcodes 8.5/10 target and caps each call at 20 questions (`supabase/functions/generate-questions/index.ts`).
- Browser generator currently stores drafts and approvals in localStorage (`equipment/assets/question-generator.js`); it is not an admin-only central review queue.
- Authenticated source storage client uses `source-materials` bucket (`equipment/assets/source-material-storage.js`); verify actual storage policies before changing permissions.
- `docs/QUESTION_GENERATION.md` describes an earlier disabled/unconfigured state and appears outdated relative to enabled course manifests; reconcile documentation with deployed behavior.

## Supabase discovery
Project `xqyasyambwdyhsjkftqu` contains `mbu_item_calibration`, `mbu_question_exposure`, `mbu_question_sessions`, `mbu_question_lifecycle_events`, `mbu_sync_state`, `mbu_sync_versions`, `mbu_sync_devices`, and `snar_privacy_requests`. All listed public tables report RLS enabled. Counts are records, not verified unique users or calibrated items.

## Next gates
1. Inspect detailed schema, RLS policies, admin functions and storage policies read-only.
2. Document how generated questions and experimental scores will remain separate from canonical CAT contributions.
3. Design source_documents, source_chunks, generated_questions, generated_question_reviews and publication lineage with least-privilege permissions.
4. Add tests proving students cannot list or mutate unpublished questions and cannot fetch private source files.
5. Implement in a migration only after design review; do not write production data during discovery.
6. Build admin review UI before enabling any AI Adaptive student mode.

## Release constraints
Preserve canonical IDs, first-attempt accounting, course ownership, coverage exclusions and refresh/resume. Do not automatically publish generated questions. Require admin approval for shared-bank integration. Generated-question target difficulty must remain distinct from empirical difficulty.
