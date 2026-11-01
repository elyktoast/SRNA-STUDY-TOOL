# Equipment Exam 2 — clinical readability and respiratory-monitoring review

Audit date: 2026-11-01. Scope: 1,000 canonical Exam 2 questions across three existing JSON files. This is a **structural/content-screening audit**, not textbook verification. No question ID, embedded image, or existing learner history is changed. One figure-confirmed answer revision changes R054 from single-answer [2] to multi-answer [2,3]; all other corrected questions retain their existing keyed answer indexes. The regional/neuraxial source bank is not rewritten.

## Anesthesia terminology policy

- Keep familiar practice abbreviations, including BP, OR, HR, MAP, ECG, ETT, LMA, FGF, FRC, PEEP, PIP, Pplat, EtCO2, SpO2, FiO2, MAC, TIVA, TOF, PONV, and similar common clinical terms.
- In respiratory/ventilation context use **Vt** for tidal volume and **MV** for minute ventilation. Normalize ambiguous old **TV/VE** presentation in this context only; never normalize uppercase **VT** globally because it can mean ventricular tachycardia.
- On first occurrence, write **mean airway pressure (Pmean)**, **airway resistance (Raw)**, **inspiratory time (Ti)**, and **expiratory time (Te)**.
- Expand genuinely uncommon abbreviations at first occurrence. For regional/neuraxial **display only**, show full regional term with its acronym at each use; do not edit regional/neuraxial question-bank records.
- Question display formatting does not change canonical answer comparisons, answer choice values, citations, or existing learner progress.

## Respiratory-monitoring inventory

All **224** questions with topic `Respiratory monitoring` were inventoried: 110 in Exam 2 bank 1 and 114 in bank 2. Bank 3 contains none. **54** are image-dependent, so any claimed figure-answer correction requires inspecting the actual embedded figure. The structural audit checks answer-index validity, missing citations, professor attributions and lecture-dependent stems; it is not proof that every rationale/answer is textbook-correct.

**26** respiratory-monitoring questions still cite **Franck** as lecture material, and must remain on source-verification review rather than being silently relabeled to a textbook:

Bank 1 (12): NUR868-R015, R020, R029, R054, R068, R070, R071, R072, R073, R085, R100, R103.

Bank 2 (14): NUR868-S2-M211, M214, R201, R202, R203, R207, R208, R209, R211, R223, R245, R274, R301, R303.

These counts were verified against canonical fields (stem, explanation, citation), excluding base64 images. The review queue alone is not an adequate count of source citations. Do not erase these names unless a real, independently checked replacement reference is available.

Run `node scripts/audit-exam2-respiratory-monitoring.mjs --baseline-check` to reproduce the inventory; it exits nonzero if pool or Franck counts change without an intentional re-audit.

## Admin report queue — 12 reports in status `new`

Status snapshot: 45 already `fixed`, 3 `declined`, 12 `new`. These proposals **do not automatically close reports**.

| Report | Question ID | Proposed disposition | Why |
|---|---|---|---|
| 49 | NUR868-S2-M208 | Hold for citation verification | Explanation/source cites a course lecture; no independent textbook passage checked |
| 50 | NUR868-T059 | Wording fix in PR; recheck dual plausible mechanisms | Original answer options allow shivering as an independent mechanism; revised stem specifies catecholamine pathway, preserving existing answer index |
| 51 | NUR868-T058 | Hold for source verification | The numerical ~55% comparison must be verified against study population, outcome and source, not merely relabeled |
| 52 | NUR868-S2-R280 | Wording fix in PR | Removes lecture-dependent framing; direct patient assessment remains the keyed answer |
| 53 | NUR868-V019 | Wording fix in PR | Removes reliance on an unnamed lecture example while preserving the keyed equipment-design example |
| 54 | NUR868-S2-T207 | Wording improved; visual QA remains | Inspected the embedded schematic and clarified that its red markers represent temperature measurement sites; the keyed peripheral site remains 7 |
| 55 | NUR868-V034 | Wording fix in PR | Tests clinically useful early alarm activation rather than “per lecture” |
| 56 | NUR868-S2-R295 | Wording/choice fix in PR | Removes “per lecture” and replaces vague answer “Unclear” with a more specific statement about inconsistent findings |
| 57 | NUR868-R054 | **Answer-key correction in PR** | Inspected the actual figure: both panels **B and C** show decelerating inspiratory flow. Updated to two-answer multi-select, indexes [2,3], with a corrected explanation; requires answer-revision QA before closing |
| 58 | NUR868-S2-T250 | Wording/choice fix in PR | Replaces instructor-specific wording and device-specific response with response to measured temperature |
| 59 | NUR868-V016 | Wording fix in PR | Removes reference to lecture, retains task-complexity answer |
| 60 | NUR868-S2-B283 | Wording fix in PR | Specifies sevoflurane wash-in and retains the keyed combination of changes |

Previously **declined** respiratory report **48**, question NUR868-R056, concerns whether the pressure–volume-loop figure is present. The canonical question contains embedded image data; check that it displays in the actual quiz before considering reopening the report.

## Release gates

1. Ensure all acronym unit tests and complete repository/quiz/browser quality gates pass.
2. Review the 10 edited report questions in the admin interface and verify no unintended answer ambiguities. The figure-based R054 answer revision must be checked for learner-history/version handling. Do not close held source-verification reports on code commit alone.
3. Verify 26 Franck references against the actual primary textbook and images before replacing citations.
4. Leave status fields unchanged until a reviewer confirms the fixes; do not auto-close based on a code commit.
