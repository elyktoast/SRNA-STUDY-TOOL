"""Coverage analysis of reviewed questions and indexed passage candidates."""
from board_item_quality import BLUEPRINTS, blueprint_counts
from nbcrna_taxonomy import SECTIONS, coverage
from nbcrna_classifier import classify_passages


def report(questions, passages, *, mode="NCE", exam_size=100):
    if mode not in BLUEPRINTS:
        raise ValueError("Invalid exam mode")
    reviewed = [q for q in questions if q.get("status") == "approved"
                and q.get("evidenceVerificationStatus") == "verified"
                and q.get("citationVerified") is True]
    question_coverage = coverage(reviewed, mode)
    passage_candidates = classify_passages(passages)
    candidate_counts = {domain: {section: 0 for section in sections}
                        for domain, sections in SECTIONS.items()}
    ambiguous = unclassified = 0
    for result in passage_candidates:
        if result["status"] == "suggested":
            candidate = result["candidates"][0]
            candidate_counts[candidate["domain"]][candidate["section"]] += 1
        elif result["status"] == "ambiguous":
            ambiguous += 1
        else:
            unclassified += 1
    targets = blueprint_counts(exam_size, BLUEPRINTS[mode])
    gaps = {domain: max(0, target - question_coverage["domains"][domain]["total"])
            for domain, target in targets.items()}
    return {"mode": mode, "exam_size": exam_size, "targets": targets,
            "verified_approved_question_coverage": question_coverage,
            "question_shortfalls": gaps,
            "passage_candidate_counts": candidate_counts,
            "ambiguous_passages": ambiguous,
            "unclassified_passages": unclassified,
            "passage_classifications_are_verified": False}
