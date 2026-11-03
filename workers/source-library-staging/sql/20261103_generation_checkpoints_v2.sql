-- Staging only. Apply manually after review; never run against production.
-- Checkpoints contain model-generated intermediate content, not API credentials.
CREATE SCHEMA IF NOT EXISTS source_library_staging;
CREATE TABLE IF NOT EXISTS source_library_staging.generation_checkpoints_v2 (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_uid uuid NOT NULL,
    textbook_id uuid NOT NULL REFERENCES source_library_staging.textbooks(id) ON DELETE CASCADE,
    request_hash text NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    evidence_hash text NOT NULL CHECK (evidence_hash ~ '^[0-9a-f]{64}$'),
    stage text NOT NULL CHECK (stage IN ('concept_card', 'draft')),
    concept_card jsonb NOT NULL,
    draft jsonb,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '24 hours'),
    UNIQUE (owner_uid, request_hash),
    CHECK ((stage = 'concept_card' AND draft IS NULL) OR
           (stage = 'draft' AND draft IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS generation_checkpoints_v2_expiry_idx
    ON source_library_staging.generation_checkpoints_v2 (expires_at);
ALTER TABLE source_library_staging.generation_checkpoints_v2 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON source_library_staging.generation_checkpoints_v2 FROM PUBLIC, anon, authenticated;
-- Grant only the private staging backend DB role after confirming its identity.
