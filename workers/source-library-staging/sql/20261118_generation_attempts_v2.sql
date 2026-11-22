-- Private staging-only receipts. Never truncate/reset this budget ledger.
CREATE TABLE source_library_staging.generation_attempts_v2 (
    owner_uid uuid NOT NULL,
    item_id uuid NOT NULL,
    -- Historical ID only: deleting a book must neither reset its item budget nor be blocked.
    textbook_id uuid,
    request_hash text CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    evidence_hash text CHECK (evidence_hash ~ '^[0-9a-f]{64}$'),
    state text NOT NULL DEFAULT 'started' CHECK (state IN ('started','completed','legacy_blocked')),
    rewrite_reserved boolean NOT NULL DEFAULT false,
    started_at timestamptz NOT NULL DEFAULT now(),
    rewrite_reserved_at timestamptz,
    completed_at timestamptz,
    PRIMARY KEY (owner_uid,item_id),
    CHECK (state='legacy_blocked' OR (textbook_id IS NOT NULL AND request_hash IS NOT NULL AND evidence_hash IS NOT NULL)),
    CHECK (NOT rewrite_reserved OR rewrite_reserved_at IS NOT NULL)
);
ALTER TABLE source_library_staging.generation_attempts_v2 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON source_library_staging.generation_attempts_v2 FROM PUBLIC,anon,authenticated;
-- Earlier saved questions may be read/reviewed, but their item IDs cannot author again.
INSERT INTO source_library_staging.generation_attempts_v2
    (owner_uid,item_id,textbook_id,state,rewrite_reserved,rewrite_reserved_at)
SELECT DISTINCT ON (owner_uid,question_json->>'item_id')
    owner_uid,(question_json->>'item_id')::uuid,textbook_id,'legacy_blocked',true,now()
FROM source_library_staging.generated_question_drafts_v2
WHERE question_json->>'item_id' ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
ON CONFLICT DO NOTHING;
-- Known ambiguous partial attempts from the recorded acceptance run. Their
-- historic rewrite budget cannot be reconstructed safely: never replay them.
INSERT INTO source_library_staging.generation_attempts_v2
    (owner_uid,item_id,textbook_id,state,rewrite_reserved,rewrite_reserved_at)
VALUES
 ('c003287a-10ce-4cc9-926e-ef7c3a162a26','8881f83d-42c3-4f35-95b5-84619a906657','8343459f-0595-4375-8ac6-7700e6792abe','legacy_blocked',true,now()),
 ('c003287a-10ce-4cc9-926e-ef7c3a162a26','05c89209-3ca5-42fe-b172-adf4d7d648df',NULL,'legacy_blocked',true,now())
ON CONFLICT DO NOTHING;
