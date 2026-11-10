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
from item_text_checks import check as text_checks
from run_grounded_generation_v2 import _call_with_bounded_rate_wait

parser = argparse.ArgumentParser()
parser.add_argument("--confirm-paid-review", action="store_true")
args = parser.parse_args()
if not args.confirm_paid_review:
    parser.error("Explicit paid review confirmation required")
with psycopg.connect(os.environ["STAGING_DATABASE_URL"], options="-c default_transaction_read_only=on") as conn:
    with conn.cursor() as cur:
        cur.execute("""select id::text,question_json,topic from source_library_staging.generated_question_drafts_v2
            where id=any(%s::uuid[]) and owner_uid=%s order by created_at""",
            (["2b7f969b-b9f0-4ed4-9131-e84e0b325a37", "b9880dde-631b-41a2-b684-c57871f89770"], "c003287a-10ce-4cc9-926e-ef7c3a162a26"))
        questions = cur.fetchall()
        if len(questions) != 2:
            raise SystemExit("Known-defect controls unavailable")
transport = make_transport(allowed_hosts=["api.groq.com"],
    relay_url="https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",
    relay_secret=os.environ["STAGING_RECEIPT_SIGNING_SECRET"])
config = json.loads(Path("workers/source-library-staging/reviewer-gateway/wrangler.json").read_text())["vars"]
model = config["AI_EDITORIAL_REVIEWER_MODEL"]
adapter = make_adapter(endpoint="https://api.groq.com/openai/v1/chat/completions", api_key="relay-authenticated",
    model=model, transport=transport, owner_opt_in=True, staging=True)
blind_adapter = make_adapter(endpoint="https://api.groq.com/openai/v1/chat/completions", api_key="relay-authenticated",
    model=config["AI_REVIEWER_MODEL"], transport=transport, owner_opt_in=True, staging=True)
def blind(payload):
    return _call_with_bounded_rate_wait(blind_adapter, {**payload,"step":"blind_review","blind":True,"rules_version":"2.0","auto_publish":False})
for draft, question, topic in questions:
    report = editorial(question, lambda payload: _call_with_bounded_rate_wait(adapter, payload),
                       counterfactual_reviewer=blind, selected_topic=topic)
    rules = {i["rule_id"] for i in report["issues"]}
    deterministic = {i["rule_id"] for i in text_checks(question)}
    old = draft == "2b7f969b-b9f0-4ed4-9131-e84e0b325a37"
    print(json.dumps({"case":"previously_missed_board_defects" if old else "ineffective_management_counterfactual",
        "status":report["status"], "flagged_rules":sorted(rules), "model_flagged_rules":report.get("model_flagged_rules"),
        "deterministic_rules":sorted(deterministic | set(report.get("deterministic_rules",[]))),
        "counterfactual_status":report.get("counterfactual_verification",{}).get("status"),
        "provider_rule":report.get("provider_rule"), "review_error":report.get("review_error"),
        "reviewer_model":model, "database_writes":False, "published":False}))
    required = {"R-1.3","R-5.3","R-9"} if old else {"R-5.3"}
    deterministic_required = {"R-8.4"} if old else {"R-4.2","R-8.5"}
    if report["status"] != "flag" or not required.issubset(rules) or not deterministic_required.issubset(deterministic):
        raise SystemExit("Board quality regression did not catch all known defects")
