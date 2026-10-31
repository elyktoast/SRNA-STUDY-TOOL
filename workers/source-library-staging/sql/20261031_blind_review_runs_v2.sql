-- Private staging migration. Apply only to the source-library staging project.
-- No browser/anon/authenticated grants; backend DB role must be provisioned
-- separately with narrowly scoped privileges.
CREATE SCHEMA IF NOT EXISTS source_library_staging;
CREATE TABLE IF NOT EXISTS source_library_staging.blind_review_runs (
    run_id text PRIMARY KEY,
    item_id text NOT NULL,
    owner_uid uuid NOT NULL,
    state text NOT NULL DEFAULT 'pending'
        CHECK (state IN ('pending', 'consumed')),
    blind_status text CHECK (blind_status IN ('pass', 'flag')),
    created_at timestamptz NOT NULL DEFAULT now(),
    consumed_at timestamptz,
    CONSTRAINT consumed_consistency CHECK (
        (state = 'pending' AND consumed_at IS NULL AND blind_status IS NULL)
        OR (state = 'consumed' AND consumed_at IS NOT NULL AND blind_status IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS blind_review_runs_owner_item_idx
    ON source_library_staging.blind_review_runs (owner_uid, item_id);
ALTER TABLE source_library_staging.blind_review_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON source_library_staging.blind_review_runs FROM PUBLIC, anon, authenticated;
