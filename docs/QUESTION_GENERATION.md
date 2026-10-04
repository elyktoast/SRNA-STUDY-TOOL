# Question generation framework

## Status

Question generation is intentionally **disabled and unconfigured**.

The repository contains the framework needed to add material-based question generation later without choosing a provider today. No AI service, local model, API key, endpoint, or vendor is currently required or selected.

Manifest flag:

```json
"features": {
  "questionGenerator": {
    "enabled": false,
    "status": "unconfigured",
    "storageKey": "mbu_generated_questions_v1",
    "provider": null
  }
}
```

## Planned flow

1. Source material is supplied by the user.
2. A registered provider returns question drafts.
3. Drafts are normalized into the SNAR Study Tool generated-question schema.
4. Every draft must pass structural validation.
5. The user reviews, edits, approves, or rejects the draft.
6. Only approved questions are eligible to appear as the **Generated Bank** in Study Studio.
7. The generated-question store participates in the existing local-first backup and Supabase sync system.

Generated questions never enter Quiz Banks 1–3, Combined, or Hazards automatically.

## Provider contract

Providers are registered at runtime:

```js
MBUQuestionGenerator.registerProvider(name, {
  async generate(request) {
    return { questions: [] };
  }
});
```

The request includes source material, source name, citation, and question count. The browser provider calls the authenticated Supabase Edge Function, which handles provider fallback without exposing API credentials.

## Required review metadata

Before approval, each generated question must contain:

- question stem;
- at least two unique answer choices;
- valid keyed answer indexes;
- a valid single- or multiple-answer type;
- explanation/rationale;
- either a citation or source excerpt.

The source requirement is deliberate. Generated medical/anesthesia questions should remain traceable to the supplied material rather than relying only on model output.

## Storage and sync

Generated drafts and approved questions use:

`mbu_generated_questions_v1`

The key is part of the normal SNAR Study Tool sync contract. Nothing is written until the generator framework is actually used.

Provider credentials or local endpoint settings are not stored in this generated-question store.
