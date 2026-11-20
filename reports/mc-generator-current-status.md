# MC generator: current staging status

Updated November 20, 2026. Repository: `elyktoast/SRNA-STUDY-TOOL`, not CMS.

## Current version

- Staging branch `fix/board-question-quality`, [PR #189](https://github.com/elyktoast/SRNA-STUDY-TOOL/pull/189).
- Current source `d285b1da4a83a74472c9e9db9824d10f0b46bc64`, contract `2026-11-20-v39`. CI and connected Worker/container rollout are pending. v37 had passed CI/deployment and its restored upload controls were verified in the live browser.
- Cloudflare GLM authors. GPT-OSS 120B is in a limited trial for blind, explanatory-source and independent option review. Qwen remains the editorial reviewer. Gemini is disabled.
- Main and production are unchanged. All generated drafts remain unpublished and require clinical human review before bank approval. Other question formats remain paused.

## Latest full pipeline result

[Run 44835251027](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44835251027) tested exact v36 source `049e5de27b78e9559b1ffd261ef7a80258bdf8f8`, build `27c6fe21-3be1-4ff6-8e34-d3f20b38a897`, settled image `e419c286155d45ac3cef7eaf594c6396be52b9383d9934b4f312a305b7039f4e`.

Fresh KMG request `8de61099-af11-418d-9119-b6f7ee5d0b2c` saved draft `1e621288-c8e9-4ca9-8961-ee38c906e028` at **9/10 automated checks**, zero rewrites, one current-source issue, unpublished. Blind answers, editorial, schema, evidence, duplicates, deterministic text, options-only and explanation support passed. Independent option review was pending with `REVIEW_RESPONSE_INVALID / option_quote_refs_invalid`. The workflow correctly failed after retaining artifact `14679045857`. No new passing draft is claimed. Do not regrade this completed held draft to chase a pass.

The provider schema permitted definite true/false judgments without quote references, which downstream validation correctly rejected. v37 now expresses the actual contract: a definite answer requires 1–8 option-scoped source references; null uncertainty requires none and stays blocked. The prompt makes the requirement explicit for both correct and incorrect options. The backend still refuses uncited definite responses and does not fill or correct clinical verdicts.

## Provider schema correction

The first option protocol run [44837125871](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44837125871) returned `PROVIDER_REQUEST_REJECTED`, parameter `response_format`, before any judgments. No question was authored. v38 removes the zero-length-array schema branch: explicit uncertain judgments use `answers_stem:null, quote_refs:null` on the wire, normalized only for that uncertain case to an empty internal list. Definite judgments still require source citations. Fixed schema-keyword diagnostics never expose raw provider messages. Local Python and gateway/relay suites pass again. The changed schema must pass the fixed option controls before generation.

The changed v38 nested schema was rejected again in [44838045602](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44838045602), before any judgments. Safe diagnostics named anyOf and required. v39 therefore removes nested anyOf and uses flat nullable fields: non-null reference arrays require 1–8 scoped references. The trusted backend still enforces the cross-field rule and rejects definite true/false answers with null, absent or empty citations. Only explicit null uncertainty normalizes to no citations and remains held. Local 1,107 Python and 109 gateway/relay checks pass.

## Next bounded check

A fixed protocol harness in `scripts/verify-mc-option-protocol.py` uses two logical reviewer calls with fictional sensors and eight option judgments. One packet supplies complete definitions; the other deliberately withholds a necessary definition. Expected outcomes never reach the model. This checks grounded definite judgments and honest uncited uncertainty through the real adapter/relay, without drafts, authoring, database access or approval.

The workflow marker is `[verify-mc-option-protocol]`. The separate job is pinned to current v37 source and checks exact CI/build/container readiness before model calls. Do not trigger a replacement fresh generation until these controls pass. Never rerun a paid workflow attempt.

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
