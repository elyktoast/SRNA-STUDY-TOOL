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

Live deployment and complete generation must be verified separately.
