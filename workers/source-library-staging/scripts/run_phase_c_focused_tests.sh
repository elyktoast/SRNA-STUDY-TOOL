#!/usr/bin/env bash
# Focused Phase C checks only: no database migration, network calls, or paid AI.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
cd "$ROOT/workers/source-library-staging/scripts"
python3 -m unittest \
  tests.test_item_semantic_index_db_v2 \
  tests.test_run_grounded_generation_v2 \
  tests.test_item_generation_http_v2 \
  tests.test_item_draft_revalidation_v2 \
  tests.test_item_draft_revision_v2 \
  tests.test_item_draft_revision_storage_v2 \
  tests.test_generation_nonclinical_defaults_v2 \
  tests.test_item_evidence_stage_consistency_v2
cd "$ROOT/workers/source-library-staging/reviewer-gateway"
node --test tests/relay-review-steps.test.mjs
echo "Focused Phase C checks passed (no live provider or database used)."
