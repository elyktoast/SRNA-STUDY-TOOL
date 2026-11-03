-- Read-only staging checkpoint migration verification.
-- Run in staging SQL editor AFTER applying 20261103_generation_checkpoints_v2.sql.
-- Do not execute on production. No textbook passages or model content returned.
BEGIN READ ONLY;
SELECT current_database() AS database_name,
       to_regclass('source_library_staging.generation_checkpoints_v2') IS NOT NULL
           AS checkpoint_table_present;
SELECT c.relrowsecurity AS row_level_security_enabled,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_can_select,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS authenticated_can_select
FROM pg_class c
WHERE c.oid = to_regclass('source_library_staging.generation_checkpoints_v2');
SELECT conname AS constraint_name, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = to_regclass('source_library_staging.generation_checkpoints_v2')
ORDER BY conname;
SELECT indexname FROM pg_indexes
WHERE schemaname='source_library_staging'
  AND tablename='generation_checkpoints_v2'
ORDER BY indexname;
COMMIT;
