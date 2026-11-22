"""Accept verified generated MC drafts into the private staging bank."""
from uuid import UUID

from item_draft_revalidation_v2 import revalidate
from item_draft_review_contract_v2 import approval_issues
from item_draft_storage_v2 import get_draft, review
from item_generation_checkpoint_store_v2 import fingerprint, lookup_batch_slot
from item_mc_batch_v2 import _embed_stems
from item_semantic_duplicates import screen
from item_explanation_review_v2 import fields_for
from item_source_reconciliation_v2 import _format_normalized


def _proofs(screening, question):
    option_report = screening.get("independent_option_adjudication", {})
    stages = screening["stages"]
    if (option_report.get("status") != "reviewed" or option_report.get("issues") != []
            or stages["options_only"].get("trials") != 5
            or stages["editorial_quality"].get("counterfactual_verification", {}).get("status") != "pass"):
        return None
    judgments = option_report.get("judgments", [])
    if not isinstance(judgments, list) or len(judgments) != 4:
        return None
    key = question.get("key", [])
    if not isinstance(key, list) or len(key) != 1 or key[0] not in ("A", "B", "C", "D"):
        return None
    proofs = []
    seen = set()
    for judgment in judgments:
        option = judgment.get("option_id")
        verdict = "supports_key" if option in key else "refutes_distractor"
        ids, quotes = judgment.get("passage_ids"), judgment.get("quotes")
        if (option not in ("A", "B", "C", "D") or option in seen
                or judgment.get("verdict") != verdict
                or judgment.get("source_conflict_found") is not False
                or not isinstance(ids, list) or not ids or not isinstance(quotes, list) or not quotes):
            return None
        seen.add(option)
        proofs.extend((ids, quote) for quote in quotes)
    explanations = stages["explanation_evidence"]
    support = explanations.get("source_support")
    if not isinstance(support, list) or not support:
        return None
    covered = []
    for group in support:
        covered.extend(group["fields"])
        quotes = group.get("quotes")
        if not isinstance(quotes, list) or not quotes:
            return None
        proofs.extend(([ref.get("passage_id")], ref.get("quote")) for ref in quotes)
    if sorted(covered) != sorted(field["label"] for field in fields_for(question)):
        return None
    return proofs


def bank_duplicate_checker(conn, owner_uid, secret):
    """Compare a candidate with every other owner-private approved MC draft."""
    def check(item, draft_id):
        with conn.cursor() as cur:
            cur.execute("""
              select id::text, question_json->>'stem'
              from source_library_staging.generated_question_drafts_v2
              where owner_uid=%s::uuid and id<>%s::uuid
                and status='approved_for_bank' and question_format='MC'
            """, (owner_uid, draft_id))
            rows = cur.fetchall()
        if not rows:
            return False
        stem = item["stem"]
        vectors = _embed_stems(owner_uid, secret, [stem, *(text for _, text in rows)])
        return bool(screen(vectors[stem], [{"item_id":key, "embedding":vectors[text]} for key,text in rows]))
    return check


def recovered_screening(draft, checkpoint):
    """Allow the trusted option-only recheck to replace its own report."""
    original = checkpoint.get("screening") or {}
    current = draft["screening"]
    proof = current.get("saved_option_review") or {}
    if (checkpoint.get("item") != draft["question"] or
            (checkpoint.get("saved_draft") or {}).get("draft_id") != draft["draft_id"] or
            proof.get("recorded_by") != "trusted_saved_option_review" or
            proof.get("question_sha256") != fingerprint(draft["question"])):
        return None
    if (original.get("independent_option_adjudication") or {}).get("judgments"):
        return None
    option = "independent_option_evidence"
    stages = original.get("stages") or {}
    if stages.get(option, {}).get("status") != "pending":
        return None
    previous = {name:report for name, report in stages.items() if name != option}
    verified = {name:report for name, report in (current.get("stages") or {}).items() if name != option}
    return current if previous == verified else None


def accept_recovered_draft(conn, *, owner_uid, draft_id, secret):
    draft = get_draft(conn, owner_uid=owner_uid, draft_id=draft_id)
    saved = {"draft_id":draft_id, "status":draft["status"]}
    item = draft.get("question") or {}
    screening = draft.get("screening") or {}
    if (draft["status"] != "pending_review" or not item.get("item_id")
            or not screening.get("saved_option_review")):
        return saved
    checkpoint, _ = lookup_batch_slot(conn, owner_uid=owner_uid,
        textbook_id=draft["textbook_id"], item_id=draft["question"]["item_id"])
    screening = recovered_screening(draft, checkpoint) if checkpoint else None
    if screening is None:
        return saved
    return accept_generated_batch_draft(conn, owner_uid=owner_uid, saved=saved,
        result={"item":draft["question"], "screening":screening},
        duplicate_check=bank_duplicate_checker(conn, owner_uid, secret))


def accept_generated_batch_draft(conn, *, owner_uid, saved, result, duplicate_check):
    if saved["status"] != "pending_review":
        return saved
    question, screening = result.get("item"), result.get("screening")
    if (not isinstance(question, dict) or question.get("format") != "MC"
            or not isinstance(screening, dict) or approval_issues(screening, "MC")):
        return saved
    try:
        proofs = _proofs(screening, question)
        if not proofs or len(proofs) > 200:
            return saved
        ids = sorted({str(UUID(pid)) for refs, _ in proofs for pid in refs})
        if len(ids) > 60 or any(not isinstance(quote, str) or not quote.strip() for _, quote in proofs):
            return saved
    except (KeyError, TypeError, AttributeError, ValueError):
        return saved

    # Serialize against manual revision/removal, and bind the proof to the
    # exact question and reports persisted by the generation checkpoint.
    with conn.cursor() as cur:
        cur.execute("select pg_advisory_xact_lock(hashtextextended(%s,0))", ("mc-staging-bank:"+owner_uid,))
        cur.execute("""
          select question_json,screening_json from source_library_staging.generated_question_drafts_v2
          where id=%s::uuid and owner_uid=%s::uuid and status='pending_review'
            and not exists (
              select 1 from source_library_staging.generated_draft_revisions_v2
              where draft_id=%s::uuid
            )
          for update
        """, (saved["draft_id"], owner_uid, saved["draft_id"]))
        row = cur.fetchone()
        if not row or row[0] != question or row[1] != screening:
            return saved
        # Read the current quote text by indexed UUID, retaining owner and
        # readiness checks on every supporting book.
        cur.execute("""
          select p.id::text,p.content from source_library_staging.passages p
          join source_library_staging.textbooks b on b.id=p.textbook_id
          where p.id=any(%s::uuid[]) and b.owner_uid=%s::uuid and b.status='ready'
        """, (ids, owner_uid))
        sources = {pid: _format_normalized(text) for pid, text in cur.fetchall()}
    normalized_quotes = {quote: _format_normalized(quote) for quote in {quote for _, quote in proofs}}
    if set(sources) != set(ids) or any(
            not normalized_quotes[quote] or not any(normalized_quotes[quote] in sources.get(pid, "") for pid in refs)
            for refs, quote in proofs):
        return saved
    validation = revalidate(conn, owner_uid=owner_uid, draft_id=saved["draft_id"])
    if validation["issues"]:
        return saved
    try:
        if duplicate_check(question, saved["draft_id"]):
            return saved
    except Exception:
        # An unavailable final duplicate check cannot approve a draft.
        return saved
    decision = review(conn, owner_uid=owner_uid, reviewer_uid=owner_uid,
                      draft_id=saved["draft_id"], status="approved_for_bank",
                      notes="Automatically accepted for this owner's private staging bank after saved automated checks and current-source quote verification. No human review recorded.")
    return {**saved, **decision}
