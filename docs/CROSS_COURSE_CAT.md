# Cross-course adaptive testing

Adaptive Quiz defaults to **All courses** in each Study Studio. It loads the canonical manifests for Equipment Exam 1 (2,000 questions), Basic Principles Exam 1 (4,000), and Clinical Pharmacology (1,000). Set/topic selections apply when the learner explicitly chooses **This course**. Ordinary quizzes and review pools stay scoped to their existing course.

The complete 7,000-row corpus is loaded before a new cross-course session can reserve a question. Existing adaptive content normalization removes equivalent-content candidates; this currently leaves 6,774 unique candidates before account-history exclusions. No fixed candidate total is encoded in the runtime. IDs remain the canonical bank-prefixed UIDs.

Each question carries its owning course and exam. Reservations, durable lifecycle deliveries, calibration contributions, study intelligence, and saved answer snapshots use that identity. These writes use existing stores and endpoints. A foreign-course answer preserves that course's separate active quiz, flags, and previous answer history. The initiating Studio owns the cross-course CAT session and its resume state.

Coverage history is loaded for all three courses using the authenticated, paginated existing adapter. Viewed/answered questions remain excluded across content versions, and equivalent content is excluded as well. Unviewed reservation leases expire under the existing 30-minute policy. The CAT engine continues to prevent repeated IDs and equivalent content within a session.

Resume reloads the full canonical corpus before reconciling a saved cross-course session. Failed bank loads retain the session and submitted answers; a reload after connectivity returns can resume the exact question. Cancellation or an account identity change invalidates an in-flight start before reservation. Legacy course-scoped CAT sessions continue to use their saved course pools.

No schema changes, production backfills, progress resets, or duplicate question-tracking structures are required.

Validation: `npm run quality`, `npm run test:cat` (all-course production-engine simulation; optional `--scope=course` for the original course pool), `npm run test:coverage`, and `npm run test:e2e`. Browser regressions mock cloud requests and never write student production data. Real multi-device production behavior still requires deployment and authenticated acceptance testing.
