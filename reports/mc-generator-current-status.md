# MC generator: current staging status

Updated November 20, 2026. Repository: `elyktoast/SRNA-STUDY-TOOL`, not CMS.

## Current source and deployment

- Branch `fix/board-question-quality`, [PR #189](https://github.com/elyktoast/SRNA-STUDY-TOOL/pull/189); main and production are unchanged.
- Application `605b3f4dd16f42524ec68fb89c773453169f52b0`; authoring contract `2026-11-20-v35`.
- v35 build `f89c91ba-eb11-4d85-87a2-b34ed3a99d7c` and settled image `f6bc32d571b62c1187c651c2aa665da3db7289962341bb3d9bb5ea906ecd93ef` succeeded. CI and Pages also passed.
- Local validation: 1,107 Python tests ran, four skipped; 27 browser-adapter and 30 workspace Node tests passed. CI passed.
- Gemini disabled. Cloudflare GLM authors; distinct Groq Qwen reviews. Human clinical review is mandatory before bank approval.

## Latest actual quality result

[44721919856](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44721919856) generated fresh mechanomyography draft `3daf8077-4a7d-44da-a9e9-3ab9d52b011e`: **10/10 automated checks, zero current-source issues, one rewrite, unpublished, human review pending**. Exact tested source was `37ab875b00df21b795b8042d779186d9841564df`, image `77d3546d366afecb0aa123e48a94d0e5104fbc2d1fb96d15b669e735dfe5dbeb`. Both blind solves, all explanatory-source checks and independent option review passed. Collection took about twelve minutes; large-batch throughput is not demonstrated.

Three earlier automated passing drafts also await human clinical review:

- Local anesthetic ionization/onset: `8da6a89a-26b3-44dd-ad42-a70405dc6e23`.
- Lecture FRC: `65c2e793-a7af-4746-bfb6-1abf9993085c`.
- Lecture shunt/dead space: `f6440562-8a49-4293-8d67-d78e8773b811`; a sentence-boundary wording caveat still needs review.

This is four recorded automated passing drafts, not overall generator acceptance. Never regrade completed held drafts to obtain a different verdict. Future acceptance workflows now retain artifacts first and fail when accepted=false; a result-collection job alone must not be treated as quality success.

## What changed

A failed rewrite expanded a counterfactual condition beyond 200 characters. v33 added literal-edit integrity checks and specific field/count diagnostics. A later rewrite moved research-laboratory context outside the replaceable condition and dropped the alternate operating-room setting. v34 now protects an actual independently passing alternate case during an unrelated repair. Invalid candidates remain held after their one rewrite; full clinical screening reruns after valid repair. The adapter/relay does not cache the previous blind answer.

The upload planner and staging UI now report selected page numbers containing detected highlighted and bold text. Formatting does not establish clinical truth or source support. The original 19-page Peripheral Nerve Stimulation PDF was locally processed: highlights on pages 2, 8, 13 and 14; bold text on all 19 pages. That local check used zero model calls and no database writes.

A signed-in Chrome staging session reached Study Studio and the Source Library button, but control stalled on opening that interface and again during recovery. No file chooser or actual upload result was observed. Browser upload remains unverified; do not assume the observed session was signed out. Text-bearing slides supply text only; diagrams, image-only pages and numeric/image certification remain separate constraints. Citations identify physical PDF pages, not verified printed pages.

## Current bounded pilot and next work

The next preselected distinct concept is **Kinemyography**, bolded on lecture page 15, objective II.C.4. Its verification source is pinned to the current deployed application above. Run [44724391907](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44724391907) correctly failed at **7/10**, draft `367b1b3a-2ca2-4b41-8f21-0de793cbea13`, unpublished. The original cases were truncated mid-clause and the alternate-case lock then blocked their grammar repair. A keyed mechanism explanation was also flagged because it omitted a separate correlation caveat. Do not regrade this completed held draft.

v35 exempts reported R-4.2 grammar and R-12.1 ambiguity from the alternate lock, requests short complete case sentences, and tells explanatory review to distinguish an actually false claim from an omitted unclaimed caveat. It preserves every source check and recorded verdict. A regression reproduces the overbroad lock and verifies the legitimate complete-case repair remains unpublished. The v35 control [44726466131](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44726466131) saved draft `b15983b0-90b5-46c6-9d77-fb5a64e90d46` at **7/10**, unpublished. Grammar and the counterfactual passed. The blind reviewer selected MMG for the KMG sensor description, and explanatory review alleged a does-not-correlate claim absent from the submitted explanation. The one rewrite left the blind question unchanged; the anti-resampling guard correctly held it before another clinical review. No new accepted question is claimed. Do not reroll this draft.

**Next action has changed: reviewer calibration before more generation.** A fixed eight-control harness tests four counterbalanced monitor definitions plus two supported and two explicitly false synthetic source claims. It reads no drafts, writes no database data, hides expected results from the model, and cannot approve anything. It uses the existing signed staging relay and current reviewer only. A failed control run records all completed cases; do not interpret passing controls as full MC generator acceptance. The fixed harness is not an acceptance regrade of any held draft.

Remaining goal: demonstrate consistency across representative concepts, verify actual lecture upload, and implement dependable bounded resumable throughput before enabling 25/50/100. Multiple response, short answer, drag and drop and hotspot remain paused. No question has been approved or published.

## Measured throughput blocker

Completed-run telemetry for the mechanomyography control recorded 37 relay events and six explicit provider 429 responses. The six existing bounded waits account for about six minutes. Successful review calls were generally under one second; Cloudflare authoring calls were roughly 7–20 seconds. The reported Groq TPM ceiling was 7,000 (one response reported a separate 1,000-token dimension). Provider retry suggestions ranged from 2–13 seconds, but the existing full-minute wait was deliberately introduced after request estimates varied between identical attempts. Do not just shorten that wait or add retries to chase a pass. Next performance work should measure quota-aware scheduling or source-preserving request packing, preserving all field coverage, source scoping and one-retry limits.

## Resume without repeating work

- Verification runner: `verify/mc-objective-heading-20261118`; saved read-only inspection runner: `verify/mc-saved-option-review-20261117`. Existing staging credentials are already configured in Actions.
- Canonical semantic index is complete at 9,000/9,000; seven trusted textbooks are indexed. Do not redo that work. OR Guide remains held for provenance.
- Check exact source CI, successful connected Worker build and settled image before paid calls. One fresh request per planned topic; completion recovery never restarts generation.
- Fix a demonstrated failure before replacement tests; if a question passes, broaden the fixed pilot to distinct concepts.
- Report-only Worker builds are excluded. Save result notes on this verification branch or in PR metadata so source HEAD remains the deployed SHA.


### Reviewer control results and current next step

The fixed basic controls [44728635341](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44728635341) passed **8/8**: four counterbalanced named-monitor definitions and two supported/two false synthetic source claims. No drafts were read, no questions generated and no database data written. This confirms basic protocol health; it does not resolve the production clinical-review disagreements.

A separate clinical suite now tests four new recognition controls and four balanced clinical assertions against three owner-scoped trusted textbook passages, using five logical reviewer calls. It does not rerun the eight basic controls or read held drafts. The source connection is read-only. Its result is pending. Preserve all source/answer holds and select any future reviewer model against the whole fixed positive/negative suite, never by finding a model that passes a held draft.
