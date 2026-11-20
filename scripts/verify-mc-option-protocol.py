"""Fixed fictional option-review controls. No drafts, authoring, or DB access."""
import json
import os
from pathlib import Path

from item_ai_provider_v2 import make_adapter
from item_ai_https_transport_v2 import make_transport
from run_grounded_generation_v2 import _call_with_bounded_rate_wait


DEFINITIONS = {
    "A": "The fictional Aster sensor measures contraction force against a load cell; it does not record film bending or muscle electrical action potentials.",
    "B": "The fictional Birch sensor measures acceleration of a moving mass; it does not record film bending or muscle electrical action potentials.",
    "C": "The fictional Cedar sensor measures bending of a flexible film; it does not record muscle electrical action potentials.",
    "D": "The fictional Dove sensor records the electrical action potential of muscle; it does not record film bending.",
}


def run(adapter, rows):
    for incomplete in (False, True):
        sources = [{"passage_id": "source-"+oid,
                    "excerpt": "The fictional Dove sensor has a grey outer case." if incomplete and oid == "D" else text}
                   for oid, text in DEFINITIONS.items()]
        request = {"step": "option_review", "rules_version": "2.0", "auto_publish": False,
                   "blind": True, "format": "MC", "task": "independent_option_adjudication",
                   "stem": "Which fictional sensor records the muscle electrical action potential?" if incomplete else
                           "Which fictional sensor records bending of a flexible film?",
                   "options": [{"id": oid, "text": name} for oid, name in
                               zip("ABCD", ("Aster", "Birch", "Cedar", "Dove"))],
                   "retrieval": {"option_audits": [{"option_id": oid, "retrieved_passage_ids": ["source-"+oid]}
                                                  for oid in "ABCD"]},
                   "source_passages": sources}
        response = _call_with_bounded_rate_wait(adapter, request)
        judgments = response.get("judgments")
        if not isinstance(judgments, list) or [j.get("option_id") for j in judgments] != list("ABCD"):
            raise ValueError("Fixed option coverage invalid")
        for judgment in judgments:
            oid = judgment["option_id"]
            expected = ("uncertain" if oid == "D" else "refutes_distractor") if incomplete else (
                "supports_key" if oid == "C" else "refutes_distractor")
            quotes, refs = judgment.get("quotes"), judgment.get("passage_ids")
            source = next(s["excerpt"] for s in sources if s["passage_id"] == "source-"+oid)
            grounded = (quotes == [] and refs == []) if expected == "uncertain" else (
                isinstance(quotes, list) and 1 <= len(quotes) <= 8 and refs == ["source-"+oid]
                and all(isinstance(q, str) and len(q) >= 6 and q in source for q in quotes))
            rows.append({"case": ("incomplete" if incomplete else "complete")+"_"+oid,
                         "expected": expected, "observed": judgment.get("verdict"),
                         "citations_grounded": bool(grounded),
                         "source_conflict_found": judgment.get("source_conflict_found"),
                         "pass": judgment.get("verdict") == expected and grounded
                                 and judgment.get("source_conflict_found") is False})


def main():
    if os.environ.get("CONFIRM_PAID_OPTION_CONTROLS") != "true" or os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise SystemExit("One explicitly authorized option protocol control run required")
    config = json.loads((Path(os.environ["REVIEWER_SOURCE_ROOT"])/
                         "workers/source-library-staging/reviewer-gateway/wrangler.json").read_text())["vars"]
    model = config["AI_REVIEWER_MODEL"]
    if model != "openai/gpt-oss-120b":
        raise SystemExit("Pinned reviewer model required")
    transport = make_transport(allowed_hosts=["api.groq.com"],
        relay_url="https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",
        relay_secret=os.environ["STAGING_RECEIPT_SIGNING_SECRET"])
    adapter = make_adapter(endpoint="https://api.groq.com/openai/v1/chat/completions",
        api_key="relay-authenticated", model=model, transport=transport, owner_opt_in=True, staging=True)
    result = {"reviewer_model": model, "controls": [], "max_logical_reviews": 2,
              "database_writes": False, "drafts_read": False, "question_generation_performed": False,
              "published": False, "clinical_acceptance": False}
    try:
        run(adapter, result["controls"])
    except Exception as error:
        rule = getattr(error, "rule", None)
        result["control_error"] = rule if rule in {"PROVIDER_RATE_LIMIT", "PROVIDER_TIMEOUT", "PROVIDER_UPSTREAM",
            "PROVIDER_AUTH", "PROVIDER_FORBIDDEN", "PROVIDER_NETWORK", "PROVIDER_REQUEST_REJECTED"} else "CONTROL_RESPONSE_INVALID"
    result["pass"] = len(result["controls"]) == 8 and all(r["pass"] for r in result["controls"])
    Path("/tmp/mc-option-protocol-controls.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    if not result["pass"]:
        raise SystemExit("Fixed option protocol controls did not pass")


if __name__ == "__main__":
    main()
