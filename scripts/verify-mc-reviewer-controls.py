"""Fixed reviewer calibration, never a question-bank acceptance or draft regrade."""
import json
import os
import hashlib
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


RECOGNITION = (
    ("recognition_force", "Isometric tension from an evoked adductor pollicis contraction is read from a force transducer under preload. Which method records that force?",
     ("Electromyography", "Mechanomyography", "Acceleromyography", "Kinemyography"), "B"),
    ("recognition_acceleration", "A sensor attached to a freely moving thumb reports its acceleration after nerve stimulation. Which method uses that measurement?",
     ("Kinemyography", "Mechanomyography", "Electromyography", "Acceleromyography"), "D"),
    ("recognition_electrical", "A monitor evaluates the evoked compound muscle action potential detected by surface electrodes. Which method uses that muscle signal?",
     ("Electromyography", "Acceleromyography", "Kinemyography", "Mechanomyography"), "A"),
    ("recognition_bending", "A piezoelectric film deforms with thumb movement and develops a bending-related electrical signal. Which method uses that film principle?",
     ("Acceleromyography", "Mechanomyography", "Kinemyography", "Electromyography"), "C"),
)
CLINICAL_CLAIMS = (
    ("supported_distinct_measurements", "Mechanomyography measures muscle contraction force, whereas kinemyography records a bending-dependent electrical signal from a polymer strip.", "supported"),
    ("supported_strip_mechanism", "A kinemyography strip produces an electrical signal when it bends during thumb movement.", "supported"),
    ("false_force_interchangeability", "Kinemyography and mechanomyography are interchangeable measurements of muscle force.", "unsupported"),
    ("false_mmg_electrical", "Mechanomyography directly records the muscle electrical response and does not measure contraction force.", "unsupported"),
)
SOURCE_IDS = ("15a11b47-866d-4f18-9f02-c7bb58eec091", "af4bdfb9-63ec-4ce2-a06d-cc1b89dc9ff2", "fa3536f9-f5b1-4e1b-92b9-814408b3c371")


def run_clinical(adapter, sources, rows):
    # Independent fixed controls, not readings of any generated or held draft.
    for name, stem, texts, expected in RECOGNITION:
        response=_call_with_bounded_rate_wait(adapter,{"step":"blind_review","rules_version":"2.0",
            "auto_publish":False,"blind":True,"item_id":"reviewer-control-"+name,"format":"MC",
            "stem":stem,"options":[{"id":oid,"text":text} for oid,text in zip("ABCD",texts)]})
        actual=response.get("key")
        rows.append({"case":name,"kind":"blind_reference","expected":[expected],"observed":actual,"pass":actual==[expected]})
    packet,lookup=prepare({"source_passages":sources})
    fields=[{"id":"e"+str(i),"label":"rationale.distractor_breakdown."+"ABCD"[i],"text":text,
        "passage_ids":list(SOURCE_IDS),"assessment":"clinical_fact"} for i,(_,text,_) in enumerate(CLINICAL_CLAIMS)]
    response=_call_with_bounded_rate_wait(adapter,{"step":"explanation_review","rules_version":"2.0",
        "auto_publish":False,"independent":True,"fields":fields,"source_passages":packet["source_passages"]})
    actual={}
    groups=response.get("supported_groups");unsupported=response.get("unsupported")
    valid=isinstance(groups,list) and isinstance(unsupported,list)
    if valid:
        for group in groups:
            refs=group.get("quote_refs",[])
            if not refs or any(not isinstance(r,dict) or r.get("passage_id") not in lookup
                    or r.get("span_id") not in lookup[r["passage_id"]] for r in refs):valid=False;break
            for fid in group.get("field_ids",[]):
                if fid in actual:valid=False
                actual[fid]="supported"
        for field in unsupported:
            fid=field.get("field_id")
            if fid in actual:valid=False
            actual[fid]="unsupported"
        valid=valid and set(actual)=={f["id"] for f in fields}
    for i,(name,_,expected) in enumerate(CLINICAL_CLAIMS):
        observed=actual.get("e"+str(i)) if valid else "invalid"
        rows.append({"case":name,"kind":"clinical_source_reference","expected":expected,"observed":observed,"pass":observed==expected})


def clinical_sources():
    import psycopg
    with psycopg.connect(os.environ["STAGING_DATABASE_URL"],connect_timeout=20,options="-c default_transaction_read_only=on -c statement_timeout=15000") as conn:
        with conn.cursor() as cur:
            cur.execute("""select p.id::text,p.content from source_library_staging.passages p
                join source_library_staging.textbooks t on t.id=p.textbook_id
                where p.id::text=any(%s::text[]) and t.owner_uid=%s::uuid and t.status='ready'""",
                (list(SOURCE_IDS),"c003287a-10ce-4cc9-926e-ef7c3a162a26"))
            rows=cur.fetchall()
    if len(rows)!=3 or {r[0] for r in rows}!=set(SOURCE_IDS):
        raise ValueError("Reference passages unavailable")
    return [{"passage_id":pid,"excerpt":text} for pid,text in rows]


def main():
    if os.environ.get("CONFIRM_PAID_REVIEWER_CONTROLS") != "true" or os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise SystemExit("One explicitly authorized control run is required")
    root=Path(os.environ["REVIEWER_SOURCE_ROOT"])
    config=json.loads((root/"workers/source-library-staging/reviewer-gateway/wrangler.json").read_text())["vars"]
    candidate=os.environ.get("REVIEWER_CONTROL_CANDIDATE")=="true"
    model=config.get("AI_REVIEWER_CALIBRATION_MODEL") if candidate else config["AI_REVIEWER_MODEL"]
    if (candidate and (config.get("AI_REVIEWER_CALIBRATION_OPT_IN")!="true" or model!="openai/gpt-oss-120b")) or (not candidate and model!="qwen/qwen3.8-27b"):
        raise SystemExit("Reference suite model must match the pinned configuration")
    base_transport=make_transport(allowed_hosts=["api.groq.com"],
        relay_url="https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",
        relay_secret=os.environ["STAGING_RECEIPT_SIGNING_SECRET"])
    def transport(**kwargs):
        if candidate:
            kwargs={**kwargs,"body":{**kwargs["body"],"srna_reviewer_calibration":"fixed-controls-v1"}}
        return base_transport(**kwargs)
    adapter=make_adapter(endpoint="https://api.groq.com/openai/v1/chat/completions",api_key="relay-authenticated",
                         model=model,transport=transport,owner_opt_in=True,staging=True)
    suite=os.environ.get("REVIEWER_CONTROL_SUITE","basic")
    if suite not in ("basic","clinical","all") or (candidate and suite!="all"):
        raise SystemExit("Unknown fixed control suite")
    result={"suite":suite,"calibration_candidate":candidate,"reviewer_model":model,"controls":[],"database_writes":False,"drafts_read":False,
            "question_generation_performed":False,"max_logical_reviews":13 if suite=="all" else 5 if suite=="clinical" else 8,"published":False,"clinical_acceptance":False,"source_passages_read":0}
    try:
        if suite in ("basic","all"):
            run(adapter,result["controls"])
        if suite in ("clinical","all"):
            sources=clinical_sources()
            result["source_passages_read"]=len(sources)
            result["source_packet_sha256"]=hashlib.sha256(json.dumps(sorted(sources,key=lambda s:s["passage_id"]),sort_keys=True).encode()).hexdigest()
            run_clinical(adapter,sources,result["controls"])
    except Exception as error:
        rule=getattr(error,"rule",None)
        result["control_error"]=rule if rule in {"PROVIDER_RATE_LIMIT","PROVIDER_AUTH","PROVIDER_FORBIDDEN","PROVIDER_REQUEST_REJECTED","PROVIDER_UPSTREAM","PROVIDER_TIMEOUT","PROVIDER_NETWORK","PROVIDER_INVALID_JSON","PROVIDER_MODEL_UNAVAILABLE","RELAY_AUTH","RELAY_NETWORK","RELAY_DISABLED","RELAY_UPSTREAM"} else "CONTROL_RESPONSE_INVALID"
    result["pass"]=len(result["controls"])==(16 if suite=="all" else 8) and all(row["pass"] for row in result["controls"])
    Path("/tmp/mc-reviewer-controls.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    if not result["pass"]:
        raise SystemExit("Reviewer calibration did not pass all fixed controls")

if __name__ == "__main__":
    main()
