"""Explicit paid, read-only regression against the previously saved flawed item.

The question stays in private storage. No excerpts, prompts or responses are logged.
"""
import argparse
import json
import os
from pathlib import Path
import psycopg
from item_ai_https_transport_v2 import make_transport
from item_ai_provider_v2 import make_adapter
from item_board_quality_v2 import editorial, obsolete_issues
from run_grounded_generation_v2 import _call_with_bounded_rate_wait

parser = argparse.ArgumentParser()
parser.add_argument("--confirm-paid-review", action="store_true")
args = parser.parse_args()
if not args.confirm_paid_review:
    parser.error("Explicit paid review confirmation required")
with psycopg.connect(os.environ["STAGING_DATABASE_URL"], options="-c default_transaction_read_only=on") as conn:
    with conn.cursor() as cur:
        cur.execute("""select question_json from source_library_staging.generated_question_drafts_v2
            where id=%s and owner_uid=%s""", ("2b7f969b-b9f0-4ed4-9131-e84e0b325a37", "c003287a-10ce-4cc9-926e-ef7c3a162a26"))
        question = cur.fetchone()[0]
transport = make_transport(allowed_hosts=["api.groq.com"],
    relay_url="https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",
    relay_secret=os.environ["STAGING_RECEIPT_SIGNING_SECRET"])
model = json.loads(Path("workers/source-library-staging/reviewer-gateway/wrangler.json").read_text())["vars"]["AI_REVIEWER_MODEL"]
adapter = make_adapter(endpoint="https://api.groq.com/openai/v1/chat/completions", api_key="relay-authenticated",
    model=model, transport=transport, owner_opt_in=True, staging=True)
report = editorial(question, lambda payload: _call_with_bounded_rate_wait(adapter, payload))
rules = {i["rule_id"] for i in report["issues"]}
obsolete = obsolete_issues(question)
print(json.dumps({"case":"previously_missed_board_defects", "status":report["status"],
    "flagged_rules":sorted(rules), "obsolete_rejected":any(i["rule_id"] == "R-8.4" for i in obsolete),
    "provider_rule":report.get("provider_rule"), "review_error":report.get("review_error"),
    "reviewer_model":model, "database_writes":False, "published":False}))
if report["status"] != "flag" or not {"R-1.3", "R-5.3", "R-9"}.issubset(rules) or not obsolete:
    raise SystemExit("Independent board quality regression did not catch all known defects")
