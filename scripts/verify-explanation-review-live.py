"""Explicit paid, read-only negative/positive source-review regression.

No question, revision, approval or publication is written. Never print book text.
"""
import copy
from pathlib import Path
import argparse
import json
import os
import time
import psycopg
from item_ai_https_transport_v2 import make_transport
from item_ai_provider_v2 import make_adapter
from item_explanation_review_v2 import review
from run_grounded_generation_v2 import _call_with_bounded_rate_wait

parser = argparse.ArgumentParser()
parser.add_argument("--confirm-paid-review", action="store_true")
args = parser.parse_args()
if not args.confirm_paid_review:
    parser.error("Explicit paid review confirmation required")
owner = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
draft = "167026ce-7c1c-489f-8c4b-28255ac78ef8"
with psycopg.connect(os.environ["STAGING_DATABASE_URL"], options="-c default_transaction_read_only=on") as conn:
    with conn.cursor() as cur:
        cur.execute("""select question_json from source_library_staging.generated_question_drafts_v2
            where id=%s and owner_uid=%s and status='pending_review'""", (draft, owner))
        original = cur.fetchone()[0]
        cur.execute("""select question_json from source_library_staging.generated_draft_revisions_v2
            where draft_id=%s and owner_uid=%s order by revision_number desc limit 1""", (draft, owner))
        corrected = cur.fetchone()[0]
        ids = [e["passage_id"] for e in original["evidence"]]
        cur.execute("""select p.id::text,left(p.content,1200) from source_library_staging.passages p
            join source_library_staging.textbooks t on t.id=p.textbook_id
            where p.id::text=any(%s::text[]) and t.owner_uid=%s and t.status='ready'""", (ids, owner))
        sources = [{"passage_id":p[0], "excerpt":p[1]} for p in cur.fetchall()]
transport = make_transport(allowed_hosts=["api.groq.com"],
    relay_url="https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",
    relay_secret=os.environ["STAGING_RECEIPT_SIGNING_SECRET"])
reviewer_model = json.loads(Path("workers/source-library-staging/reviewer-gateway/wrangler.json").read_text())["vars"]["AI_REVIEWER_MODEL"]
adapter = make_adapter(endpoint="https://api.groq.com/openai/v1/chat/completions",
    api_key="relay-authenticated",model=reviewer_model,transport=transport,owner_opt_in=True,staging=True)
teaching = copy.deepcopy(corrected)
teaching["concept_card"].update({
    "relevance":"Recognizing triggering versus nontriggering drug categories helps clinicians select a nontriggering option for a susceptible patient.",
    "misconception":"A potential misconception is that an agent labeled nontriggering belongs in the triggering category.",
    "counterfactual":"Replacing a drug labeled triggering with a listed nontriggering option avoids exposure to that triggering drug."})
unlisted_examples = copy.deepcopy(corrected)
unlisted_examples["rationale"]["core_concept"] = "The supplied excerpt explicitly lists fentanyl as a safe opioid and lidocaine as a safe local anesthetic."
previous_started = None
for name, item, expected in (("unsupported_original", original, "flag"), ("corrected_revision", corrected, "pass"),
                             ("supported_teaching_framing", teaching, "pass"),
                             ("unlisted_named_examples", unlisted_examples, "flag")):
    # Explicit regression calls share a small provider minute quota. Pace the
    # harness instead of weakening the production one-retry limit.
    if previous_started is not None:
        time.sleep(max(0, 65 - (time.monotonic() - previous_started)))
    previous_started = time.monotonic()
    report = review(item, sources, lambda payload:_call_with_bounded_rate_wait(adapter, payload))
    fields = [i.get("field") for i in report["issues"]]
    print(json.dumps({"case":name,"reviewer_model":reviewer_model,"status":report["status"],"flagged_fields":fields,
                      "checked_fields":len(report.get("checked_fields", [])),
                      "provider_rule":report.get("provider_rule"),"review_error":report.get("review_error"),
                      "database_writes":False,"published":False}))
    if report["status"] != expected:
        raise SystemExit("Explanatory source regression did not meet its expected status")
    if name == "unsupported_original" and not {"concept_card.mechanism", "rationale.core_concept"}.issubset(fields):
        raise SystemExit("Known unsupported mechanism and exhaustive claim were not both flagged")
    if name == "unlisted_named_examples" and "rationale.core_concept" not in fields:
        raise SystemExit("Unlisted named drug examples were not flagged")
print("Independent explanatory review rejected unsupported claims and accepted the source-faithful revision")
