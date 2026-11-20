# MC generator: current staging status

Updated November 20, 2026. Repository: `elyktoast/SRNA-STUDY-TOOL`, not CMS.

## Current source and deployment

- Branch `fix/board-question-quality`, [PR #189](https://github.com/elyktoast/SRNA-STUDY-TOOL/pull/189); main and production are unchanged.
- Application `048ec81248e61960c66da7078d45e8e68752f56d`; authoring contract `2026-11-20-v34`.
- Connected staging build `ae9c84fa-800c-4185-bbab-405ca6582eaa` succeeded. Container image `0265ca4dcf97e6ce9b4f470d3ad46c8b2fd8f1711bd2d1bb23ac3ba7ba8ee89e`.
- Local validation: 1,106 Python tests ran, four skipped; 27 browser-adapter and 30 workspace Node tests passed. CI passed.
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

The next preselected distinct concept is **Kinemyography**, bolded on lecture page 15, objective II.C.4. Its verification source is pinned to the current deployed application above. Current run: [44724391907](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44724391907). **In progress; no acceptance claimed.** Do not rerun its request.

Remaining goal: demonstrate consistency across representative concepts, verify actual lecture upload, and implement dependable bounded resumable throughput before enabling 25/50/100. Multiple response, short answer, drag and drop and hotspot remain paused. No question has been approved or published.

## Resume without repeating work

- Verification runner: `verify/mc-objective-heading-20261118`; saved read-only inspection runner: `verify/mc-saved-option-review-20261117`. Existing staging credentials are already configured in Actions.
- Canonical semantic index is complete at 9,000/9,000; seven trusted textbooks are indexed. Do not redo that work. OR Guide remains held for provenance.
- Check exact source CI, successful connected Worker build and settled image before paid calls. One fresh request per planned topic; completion recovery never restarts generation.
- Fix a demonstrated failure before replacement tests; if a question passes, broaden the fixed pilot to distinct concepts.
- Report-only Worker builds are excluded. Save result notes on this verification branch or in PR metadata so source HEAD remains the deployed SHA.

