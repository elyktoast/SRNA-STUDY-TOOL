# Staging generator recovery

## Verified failure

The deployed gateway version `594c6650-0bff-4667-b64e-b48dbd5b8573`
logged Cloudflare concept-card HTTP 200 followed by PROVIDER_UPSTREAM at
2026-11-09 02:56:16 UTC. This reproduces on the latest version, not only an
old rollout. The earlier `model: none` diagnostic is corrected in that version.

An isolated concept-card request used the current step contract and the eight
ranked indexed Nagelhout passages for Airway management (9,600 excerpt
characters). Qwen's default thinking exhausted all 1,200 completion tokens:
HTTP 200, finish_reason=length, no valid JSON, 58,434 ms. Low reasoning effort
alone still exhausted 1,200 tokens and returned incomplete JSON (44,044 ms).

Keeping system/user roles, requesting JSON output and setting
chat_template_kwargs.enable_thinking=false returned finish_reason=stop and
all six concept-card fields using 510 completion tokens (29,459 ms).
No incomplete output was accepted and no validation gate was relaxed.

## Baseline and scope

The legacy Supabase generate-questions implementation used one schema-constrained
Gemini request over supplied material. It is separate from the current indexed
three-stage Python pipeline. Rolling it back would not preserve later safeguards.
The latest observed saved staging draft before recovery was created at
2026-11-08 20:59:11 UTC using openai/gpt-oss-120b, topic Intubation,
status pending_review, next_state needs_editorial_review. A saved draft is not
proof that every quality gate passed.

The recovery changes Qwen request settings, records sanitized output-failure
categories, and excludes Gemini from metadata diagnostics. Existing Groq drafting,
evidence retrieval, citation reconciliation, rewrite limits, independent blind
review and unpublished persistence remain in place. Staging configuration enables
the existing one-rewrite and blind-review paths with a distinct Groq reviewer,
qwen/qwen3.8-27b. Metadata availability alone does not verify live review.

PR #169 separately rebaselines two asset budgets; it does not repair generation.

## Offline verification

- 67 Node gateway, relay and workspace tests passed.
- 15 grounded execution, 17 screened generation, 11 grounded pipeline and
  15 checkpoint-store Python tests passed.
- Repository validation and performance budgets passed.

## First live acceptance and rollout failure

PR #170 deployed Worker version bcccb569-8bee-4254-9e94-df80d77059aa.
Authenticated source integrity, evidence preflight, private draft-bank reads and
the signed container relay passed. The live concept card completed in 9,795 ms
and Groq drafting in 5,619 ms, both HTTP 200.

At 03:22:46 UTC the container was terminated during the next stage. Cloudflare
logged `Runtime signalled the container to exit due to a new version rollout`.
Its application configuration changed at 03:22:37, after deployment commands and
smoke checks had already returned. No draft was saved by that interrupted run.

The deployment now waits before authenticated warmup: at least 90 seconds since
the gate began, at least 60 seconds since the last application configuration
update, no active rollout/errors, and no old running image or transitional
instance state. The bounded gate blocks paid acceptance if these conditions do
not settle. Four offline regressions cover the early-ready window, old image,
active rollout and invalid metadata. This is a settling criterion, not a claim
that Wrangler itself waits for container replacement.

## Groq drafting output budget

The settling gate passed and authenticated smoke succeeded on version
e910f323-1b49-441c-b381-16e485cb809c. The second acceptance stayed up but failed
at item_draft with PROVIDER_RESPONSE after Groq HTTP 200.

An isolated request through the signed internal relay reproduced GPT-OSS
finish_reason=length, exactly 2,600 completion tokens, and invalid JSON
(6,083 ms). A second immediate request received an explicit rate-limit response;
it was not silently retried. A later candidate-only probe using JSON-object mode
and low reasoning effort passed with all four options and their evidence-map
entries, finish_reason=stop, 1,100 completion tokens, and valid JSON (2,931 ms).
The token budget stayed at 2,600.

The gateway now applies those verified settings to Groq GPT-OSS generation and
rewrite requests, requests JSON for the distinct Groq Qwen reviewer, and rejects
truncated Groq output before it becomes an ambiguous Python parsing failure.
The diagnostic probes do not run rationale, screening, persistence or publication.

## Rationale deadline

After the Groq fix, live concept-card generation and drafting succeeded again;
drafting completed in 2,987 ms. Rationale generation exceeded the Python relay's
50-second deadline and returned PROVIDER_TIMEOUT with failed_step=rationale.
No draft was saved.

The rationale contract now specifies the exact flat object shape and concise
one- or two-sentence explanations for each field/choice. It prohibits repeating
the draft and source excerpts in the response, while retaining mechanism,
stem-context, affirmative-evidence, ambiguity and no-invented-citation requirements.
An isolated signed-relay rationale probe passed all four fields and all four
choice explanations in 9,923 ms. The drafting input for that probe completed in
2,872 ms with 1,091 tokens. No rationale timeout was extended and no evidence or
validation requirement was removed.

Full live acceptance still requires verification after this contract clarification.
