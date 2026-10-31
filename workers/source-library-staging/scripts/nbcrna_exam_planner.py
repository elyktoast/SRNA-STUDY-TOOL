"""Deterministic blueprint-balanced exam selection from already reviewed items.

No unverified draft is eligible. If the bank lacks a domain, fail closed rather
than silently violating the official NBCRNA domain distribution.
"""
from board_item_quality import BLUEPRINTS, blueprint_counts
from nbcrna_taxonomy import validate_classification


def assemble(items, *, mode="NCE", count=100):
    if mode not in BLUEPRINTS:
        raise ValueError("Unknown exam mode")
    targets = blueprint_counts(count, BLUEPRINTS[mode])
    buckets = {domain: [] for domain in targets}
    for item in items:
        if (item.get("status") != "approved" or
            item.get("evidenceVerificationStatus") != "verified" or
            not item.get("citationVerified") or
            not validate_classification(item.get("nceDomain"),
                                        item.get("nceSection"),
                                        item.get("nceObjective")) or
            not item.get("nceSection")):
            continue
        buckets[item["nceDomain"]].append(item)
    missing = {domain: target - len(buckets[domain]) for domain, target in targets.items()
               if len(buckets[domain]) < target}
    if missing:
        return {"ready": False, "mode": mode, "required": targets,
                "shortfalls": missing, "questions": []}
    # Stable order; a production exam session should shuffle independently.
    return {"ready": True, "mode": mode, "required": targets,
            "shortfalls": {}, "questions": [
                item for domain, target in targets.items()
                for item in buckets[domain][:target]
            ]}
