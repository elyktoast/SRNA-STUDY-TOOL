"""Accept verified generated MC drafts into the private staging bank."""
from uuid import UUID

from item_draft_revalidation_v2 import revalidate
from item_draft_review_contract_v2 import approval_issues
from item_draft_storage_v2 import review
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


def accept_generated_batch_draft(conn, *, owner_uid, saved, result):
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
    decision = review(conn, owner_uid=owner_uid, reviewer_uid=owner_uid,
                      draft_id=saved["draft_id"], status="approved_for_bank",
                      notes="Automatically accepted for this owner's private staging bank after saved automated checks and current-source quote verification. No human review recorded.")
    return {**saved, **decision}
