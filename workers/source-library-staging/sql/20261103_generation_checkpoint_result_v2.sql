-- Staging-only additive migration: preserve a screened generation response for safe recovery.
-- The result remains private and expires with its checkpoint; never publish automatically.
ALTER TABLE source_library_staging.generation_checkpoints_v2
  ADD COLUMN IF NOT EXISTS completed_result jsonb;
ALTER TABLE source_library_staging.generation_checkpoints_v2
  DROP CONSTRAINT IF EXISTS generation_checkpoints_v2_completed_result_check;
ALTER TABLE source_library_staging.generation_checkpoints_v2
  ADD CONSTRAINT generation_checkpoints_v2_completed_result_check
  CHECK ((status = 'completed' AND completed_result IS NOT NULL)
      OR (status <> 'completed' AND completed_result IS NULL));
