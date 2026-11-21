# MC generator: current staging status

Updated November 21, 2026. Repository: `elyktoast/SRNA-STUDY-TOOL`, not CMS.

## Current version

Source `270f631a7adcad74b58f56895d9744bdf3a69601`, contract `2026-11-21-v43`, staging only, PR #189. CI, Pages and Worker build 180c6c30-25ee-473b-8531-e4fb798e7691 passed; settled image f4ecbfc16731d569454f3cc43f99a81e27cfe61c1065b943f7532fd2ff8ecbaf. Fixed teaching/source run 44914744284 passed all eight controls in one logical review, without reading drafts, generating questions or DB writes. Fresh full v43 acceptance pending. Relevance authoring now states only the supported distinction; source review applies assessment mode before judging clinical claims. Supported instructional framing and unsupported accuracy/outcome/interchangeability assertions are tested separately with fictional references, never held drafts. Local Python: 1119 passed, four skipped.

## Latest completed result: v42 lecture focus works; source gate held

[Run 44913276868](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44913276868) tested exact source f539ba7fca76949977bb68e649705c1d086faeb4 / v42, settled image fdd7647eb96ae5198b8476600b5314a58235ed86994809979b698bd7fc172679, build 58044f57-a7be-41de-bd37-82b594f0ee0b. The synthetic lecture heading + bullet + bold marker reached the focused topic before paid authoring; actual provided PDF page 14 also passed offline extraction. This is not an actual browser file-upload test.

Item a6fb8441-9491-4b06-92ef-53c295870208 saved draft 72474f74-3f7a-49db-b002-dba83e920d6b, held and unpublished at 8/10 with one rewrite. All checks except explanatory source support and not-yet-invoked independent option review passed. One relevance statement was flagged with 'no source on teaching relevance'; all other explanatory fields passed. Relevance was identical to its initially passing version. Do not inherit that earlier pass or regrade this held draft. Current-index revalidation reported two issues; no acceptance claimed. Four source-review 429s recovered with existing bounded waits.

Four earlier automated passing drafts remain the total, all requiring human clinical review. Main/production unchanged, other question formats paused. Actual browser upload and durable 25/50/100 generation remain unfinished.

## Previous v41 result

Run 44843428029 saved draft 7e411bbc-13d5-48a4-8bb6-560533671f6b at 7/10, held for a product-brand alternate blind disagreement and pending source review. v42 carries slide teaching points, avoids unrequested product trivia, and prevents resampling an unchanged failed alternate question. The held draft was not regraded.

## Prior EMG result and source-repair fix

[Run 44838771926](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44838771926) saved unpublished draft `eab3e3a2-39de-44b1-b158-ba6649002971` at **8/10** after one rewrite (request `bf60f65d-d535-499c-88dc-68b8aaaf32c1`, artifact `14679789118`). Source explanation claims stayed flagged, so independent option adjudication was correctly not invoked. Blind, editorial, options-only and all other checks passed. The saved original distractor explanations were unchanged; a repeated review judged them differently. Do not inherit old clinical passes or regrade this held draft.

The repair could not retrieve definitions for a concept-card counterfactual source error, and its source-ID lock forbade adding needed citations. v40 fixes both within the same owner/book/page scope: bounded peer-definition retrieval and append-only trusted/cited concept references during explicit concept-source repair. Dropped, reordered, duplicate, uncited or foreign sources remain rejected. The author keeps educational relevance narrow and uses positive definitions for precise alternate cases. One rewrite and all full source/clinical checks remain in force. Local validation: 1,111 Python tests (four skipped) and eight focused answer-integrity regressions passed.

## Preceding KMG full pipeline result

[Run 44835251027](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44835251027) tested exact v36 source `049e5de27b78e9559b1ffd261ef7a80258bdf8f8`, build `27c6fe21-3be1-4ff6-8e34-d3f20b38a897`, settled image `e419c286155d45ac3cef7eaf594c6396be52b9383d9934b4f312a305b7039f4e`.

Fresh KMG request `8de61099-af11-418d-9119-b6f7ee5d0b2c` saved draft `1e621288-c8e9-4ca9-8961-ee38c906e028` at **9/10 automated checks**, zero rewrites, one current-source issue, unpublished. Blind answers, editorial, schema, evidence, duplicates, deterministic text, options-only and explanation support passed. Independent option review was pending with `REVIEW_RESPONSE_INVALID / option_quote_refs_invalid`. The workflow correctly failed after retaining artifact `14679045857`. No new passing draft is claimed. Do not regrade this completed held draft to chase a pass.

The provider schema permitted definite true/false judgments without quote references, which downstream validation correctly rejected. v37 now expresses the actual contract: a definite answer requires 1–8 option-scoped source references; null uncertainty requires none and stays blocked. The prompt makes the requirement explicit for both correct and incorrect options. The backend still refuses uncited definite responses and does not fill or correct clinical verdicts.

## Provider schema correction

The first option protocol run [44837125871](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44837125871) returned `PROVIDER_REQUEST_REJECTED`, parameter `response_format`, before any judgments. No question was authored. v38 removes the zero-length-array schema branch: explicit uncertain judgments use `answers_stem:null, quote_refs:null` on the wire, normalized only for that uncertain case to an empty internal list. Definite judgments still require source citations. Fixed schema-keyword diagnostics never expose raw provider messages. Local Python and gateway/relay suites pass again. The changed schema must pass the fixed option controls before generation.

The changed v38 nested schema was rejected again in [44838045602](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44838045602), before any judgments. Safe diagnostics named anyOf and required. v39 therefore removes nested anyOf and uses flat nullable fields: non-null reference arrays require 1–8 scoped references. The trusted backend still enforces the cross-field rule and rejects definite true/false answers with null, absent or empty citations. Only explicit null uncertainty normalizes to no citations and remains held. Local 1,107 Python and 109 gateway/relay checks pass.

## Fixed option protocol result and next full trial

A fixed protocol harness in `scripts/verify-mc-option-protocol.py` uses two logical reviewer calls with fictional sensors and eight option judgments. One packet supplies complete definitions; the other deliberately withholds a necessary definition. Expected outcomes never reach the model. This checks grounded definite judgments and honest uncited uncertainty through the real adapter/relay, without drafts, authoring, database access or approval.

[Run 44838658015](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44838658015) passed **8/8 option judgments** in two logical reviewer calls on exact deployed v39. Definite decisions cited their own supplied evidence; the missing-definition control returned uncertain with no citations. Artifact `14678979583` retains results. No drafts were read or generated and no DB access or approval occurred. The fresh next full-pipeline request is `bf60f65d-d535-499c-88dc-68b8aaaf32c1`, Electromyography, lecture physical page 14, objective II.C.4. It finished at 8/10 as recorded above; it must not be replayed.

The protocol workflow marker is `[verify-mc-option-protocol]`. The separate job is pinned to current v37 source and checks exact CI/build/container readiness before model calls. Do not trigger a replacement fresh generation until these controls pass. Never rerun a paid workflow attempt.

## Calibration and previous evidence

GPT-OSS passed all 16 fixed blind/source controls in [44731081223](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44731081223), compared with Qwen 15/16. The controls read no held drafts and cannot approve anything. That suite did not exercise the production option-citation protocol, which is why the new controls are necessary.

There are four recorded automated passing drafts, all pending clinical human review:

- Mechanomyography: `3daf8077-4a7d-44da-a9e9-3ab9d52b011e`, [44721919856](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44721919856), 10/10, zero current-source issues, one rewrite. Tested source `37ab875b00df21b795b8042d779186d9841564df`.
- Local anesthetic ionization/onset: `8da6a89a-26b3-44dd-ad42-a70405dc6e23`.
- Lecture FRC: `65c2e793-a7af-4746-bfb6-1abf9993085c`.
- Lecture shunt/dead space: `f6440562-8a49-4293-8d67-d78e8773b811`; sentence-boundary wording caveat remains for human review.

Earlier held KMG drafts `367b1b3a-2ca2-4b41-8f21-0de793cbea13` (44724391907) and `b15983b0-90b5-46c6-9d77-fb5a64e90d46` (44726466131) remain held. Their failures drove complete-case grammar repairs, protection of valid counterfactual cases, and reviewer calibration. The one-rewrite limit and unchanged-blind-question anti-resampling guard remain enforced.

## Lecture upload status

Extraction reports selected page numbers containing detected highlights/bold; formatting prioritizes concepts only when supported by textbooks. The supplied 19-page Peripheral Nerve Stimulation PDF was locally processed: highlights on pages 2, 8, 13 and 14; bold on all 19 pages. That check used zero model calls and no DB writes.

A resumed signed-in browser inspection opened Source Library and found that the Study Studio dialog omitted the lecture panel because it was only attached in the admin command center. v37 attaches the panel in the initial dialog too, improves upload instructions and bumps the frontend build marker. The deployed signed-in browser dialog was verified to expose the lecture file chooser, page-range fields, evidence-source selector and planning button. A review tab was retained.

Actual browser file upload remains unverified. The browser security policy denied retrieving the supplied PDF; no bypass was attempted. A real file selection is needed for end-to-end upload evidence. Diagrams/image-only pages and numeric/image certification remain separate constraints. Citations identify physical PDF pages, not verified printed pages.

## Validation and throughput

v37 local validation passed: **1,107 Python tests, four skipped; 109 gateway/relay Node checks; 57 UI/browser-adapter checks**. The restarted workspace initially lacked boto3; restoring the declared dependency resolved the nine environment-only checkpoint-test errors. A synthetic 9,000-by-1,024 comparison benchmark took 2.355 seconds locally, with no provider calls or database writes; deployed DB latency and container CPU allocation were not measured.

The earlier 12-minute MMG run had six explicit provider 429 waits accounting for about six minutes. Do not shorten waits or add retries to chase passes. Large-batch throughput is not demonstrated. 25/50/100 generation still needs dependable bounded background execution, resumable status and duplication checks across queued drafts. The current lecture UI supports 1–5 planning jobs and generates one question at a time.

## Resume rules

- Check the exact source CI, successful connected Worker build and settled container before paid calls. Wait outside Actions where possible to conserve minutes.
- One fresh request per planned topic. Completion recovery retrieves only the same completed request and never restarts generation. Fix a demonstrated failure before a replacement test.
- Canonical semantic index is complete at 9,000/9,000; seven trusted textbooks are indexed. Do not redo this. OR Guide remains held for provenance.
- Save result-only notes here or in PR metadata. Report-only Worker builds are excluded, so advancing application HEAD with report-only commits breaks exact-deployment acceptance identity.
- No bank approval, publication, merge to main or production deployment is authorized by these acceptance checks.
