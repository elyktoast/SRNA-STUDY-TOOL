"""Fixed reviewer calibration, never a question-bank acceptance or draft regrade."""
import json
import os
from pathlib import Path

from item_ai_provider_v2 import make_adapter
from item_ai_https_transport_v2 import make_transport
from item_source_quote_spans_v2 import prepare
from run_grounded_generation_v2 import _call_with_bounded_rate_wait

BLIND = (
    ("mmg_force", "Which physical response does mechanomyography quantify after motor nerve stimulation?",
     ("Muscle contraction force", "Muscle electrical activity", "Thumb acceleration", "Upper-arm cuff pressure"), "A"),
    ("amg_acceleration", "Which physical response does acceleromyography quantify after motor nerve stimulation?",
     ("Upper-arm cuff pressure", "Muscle contraction force", "Muscle electrical activity", "Thumb acceleration"), "D"),
    ("emg_electrical", "Which physical response does electromyography record after motor nerve stimulation?",
     ("Thumb acceleration", "Upper-arm cuff pressure", "Muscle electrical activity", "Muscle contraction force"), "C"),
    ("kmg_bending", "Which physical change in a piezoelectric sensor generates the recorded signal in kinemyography?",
     ("Upper-arm cuff pressure", "Bending of a strip during thumb movement", "Force against a load cell", "Acceleration of an attached mass"), "B"),
)
SOURCE = ("The fictional Aster sensor produces an electrical signal when its strip bends. "
          "Aster does not record cuff pressure. Aster values correlate poorly with the Birch reference. "
          "Aster values must not be used interchangeably with Birch values.")
CLAIMS = (
    ("supported_mechanism", "The Aster sensor produces an electrical signal when its strip bends.", "supported"),
    ("false_measurement", "The Aster sensor records cuff pressure.", "unsupported"),
    ("supported_without_unclaimed_caveat", "Bending the Aster sensor strip generates an electrical signal.", "supported"),
    ("false_interchangeability", "Aster values may be used interchangeably with Birch values.", "unsupported"),
)


def run(adapter, rows=None):
    rows = [] if rows is None else rows
    for name, stem, texts, expected in BLIND:
        request = {"step":"blind_review", "rules_version":"2.0", "auto_publish":False,
                   "blind":True, "item_id":"reviewer-control-"+name, "format":"MC", "stem":stem,
                   "options":[{"id":oid,"text":text} for oid,text in zip("ABCD",texts)]}
        response = _call_with_bounded_rate_wait(adapter,request)
        actual = response.get("key")
        rows.append({"case":name,"kind":"blind_reference","expected":[expected],"observed":actual,
                     "pass":actual == [expected]})
    packet, lookup = prepare({"source_passages":[{"passage_id":"control-source", "excerpt":SOURCE}]})
    for name, text, expected in CLAIMS:
        request = {"step":"explanation_review", "rules_version":"2.0", "auto_publish":False,
                   "independent":True, "fields":[{"id":"e0","label":"rationale.distractor_breakdown.A",
                        "text":text,"passage_ids":["control-source"],"assessment":"clinical_fact"}],
                   "source_passages":packet["source_passages"]}
        response = _call_with_bounded_rate_wait(adapter,request)
        supported = response.get("supported_groups")
        unsupported = response.get("unsupported")
        actual = "invalid"
        if isinstance(supported,list) and isinstance(unsupported,list):
            found=[fid for group in supported for fid in group.get("field_ids",[])] + [f.get("field_id") for f in unsupported]
            if found == ["e0"]:
                if len(supported)==1 and not unsupported:
                    refs=supported[0].get("quote_refs",[])
                    if refs and all(isinstance(r,dict) and r.get("passage_id")=="control-source"
                            and r.get("span_id") in lookup["control-source"] for r in refs):
                        actual="supported"
                elif not supported and len(unsupported)==1:
                    actual="unsupported"
        rows.append({"case":name,"kind":"source_reference","expected":expected,"observed":actual,
                     "pass":actual == expected})
    return rows


def main():
    if os.environ.get("CONFIRM_PAID_REVIEWER_CONTROLS") != "true" or os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise SystemExit("One explicitly authorized control run is required")
    root=Path(os.environ["REVIEWER_SOURCE_ROOT"])
    config=json.loads((root/"workers/source-library-staging/reviewer-gateway/wrangler.json").read_text())["vars"]
    model=config["AI_REVIEWER_MODEL"]
    if model != "qwen/qwen3.8-27b":
        raise SystemExit("Reference suite is pinned to the current reviewer")
    transport=make_transport(allowed_hosts=["api.groq.com"],
        relay_url="https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",
        relay_secret=os.environ["STAGING_RECEIPT_SIGNING_SECRET"])
    adapter=make_adapter(endpoint="https://api.groq.com/openai/v1/chat/completions",api_key="relay-authenticated",
                         model=model,transport=transport,owner_opt_in=True,staging=True)
    result={"reviewer_model":model,"controls":[],"database_writes":False,"drafts_read":False,
            "question_generation_performed":False,"max_logical_reviews":8,"published":False,"clinical_acceptance":False}
    try:
        run(adapter,result["controls"])
    except Exception as error:
        rule=getattr(error,"rule",None)
        result["control_error"]=rule if rule in {"PROVIDER_RATE_LIMIT","PROVIDER_AUTH","PROVIDER_FORBIDDEN","PROVIDER_REQUEST_REJECTED","PROVIDER_UPSTREAM","PROVIDER_TIMEOUT","PROVIDER_NETWORK","PROVIDER_INVALID_JSON","PROVIDER_MODEL_UNAVAILABLE","RELAY_AUTH","RELAY_NETWORK","RELAY_DISABLED","RELAY_UPSTREAM"} else "CONTROL_RESPONSE_INVALID"
    result["pass"]=len(result["controls"])==8 and all(row["pass"] for row in result["controls"])
    Path("/tmp/mc-reviewer-controls.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    if not result["pass"]:
        raise SystemExit("Reviewer calibration did not pass all fixed controls")

if __name__ == "__main__":
    main()
