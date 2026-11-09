import json, os, psycopg
from item_ai_https_transport_v2 import make_transport, TransportError
from item_ai_provider_v2 import make_adapter
from item_option_retrieval_audit_v2 import audit
from item_option_adjudication_handoff_v2 import run
from search_passages import search
owner="c003287a-10ce-4cc9-926e-ef7c3a162a26"
book="6f1b2869-d6ad-4adf-a9d8-888e8a3d9b9d"
topic="malignant hyperthermia triggering nontriggering agents"
with psycopg.connect(os.environ["STAGING_DATABASE_URL"], options="-c default_transaction_read_only=on") as conn:
    with conn.cursor() as cur:
        cur.execute("select question_json from source_library_staging.generated_question_drafts_v2 where id=%s and owner_uid=%s",("56636be0-5655-43f4-b7a8-543d59323521", owner))
        item=cur.fetchone()[0]
    retrieval=audit(conn,owner,item,textbook_id=book,limit=2,context_query=topic)
    passages={}
    for entry in retrieval["option_audits"]:
        for query in entry["search_queries"]:
            for p in search(conn,query,owner,limit=5,textbook_id=book):
                passages[p["passage_id"]]=p
transport=make_transport(allowed_hosts=["api.groq.com"],relay_url="https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",relay_secret=os.environ["STAGING_RECEIPT_SIGNING_SECRET"])
adapter=make_adapter(endpoint="https://api.groq.com/openai/v1/chat/completions",api_key="relay-authenticated",model="qwen/qwen3.8-27b",transport=transport,owner_opt_in=True,staging=True)
def reviewer(payload):
    print(json.dumps({"source_count":len(payload["source_passages"]),"payload_characters":len(json.dumps(payload))}))
    try:
        response=adapter({**payload,"step":"option_review","blind":True,"rules_version":"2.0","auto_publish":False})
    except TransportError as e:
        print(json.dumps({"rule":e.rule,"retry_after_seconds":e.retry_after_seconds,"remaining_requests":e.remaining_requests,"remaining_tokens":e.remaining_tokens}))
        raise
    return [{**j,"contradiction_found":j["source_conflict_found"]} for j in response["judgments"]]
report=run(item,retrieval,reviewer,source_passages=list(passages.values()),generator_model_id="openai/gpt-oss-120b",reviewer_model_id="qwen/qwen3.8-27b",require_quotes=True)
print(json.dumps({"status":report["status"],"provider_rule":report.get("provider_rule"),"issues":report.get("issues")}))
