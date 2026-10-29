# AI Adaptive security advisor baseline

Date: 2026-10-29. Project: xqyasyambwdyhsjkftqu. Read-only inspection; no production changes.

The Supabase security advisor reported eight private-schema tables with RLS enabled and no policies. These are not necessarily exposed to clients; inspect schema grants before treating this as a vulnerability.

The advisor also reported one anonymous-callable SECURITY DEFINER function, public.snar_guest_heartbeat(uuid). Review whether its guest access is intentional and whether its input, rate limiting and privileges are safe.

The advisor flagged 23 authenticated-callable SECURITY DEFINER functions. Many are intentional application RPCs. Review their per-function authorization, ownership, search_path, grants and input validation; do not revoke access indiscriminately.

The source-material-storage.js client writes to the source-materials bucket using paths prefixed with the authenticated user's ID. This is a client convention, not proof that storage RLS enforces ownership. Exact storage policy predicates remain unverified.

Before introducing AI question tables: audit existing grants and storage RLS, implement least-privilege private schema, deny student access to unpublished questions, and test negative authorization cases. See docs/AI_ADAPTIVE_SECURITY_DESIGN.md.
