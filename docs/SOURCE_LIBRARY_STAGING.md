# Source Library staging isolation

## Verified existing implementation
- Browser source storage: `equipment/assets/source-material-storage.js` uses Supabase Storage bucket `source-materials`.
- Source Library UI: `equipment/assets/source-material-library.js` calls the storage adapter's save/list/file/download/remove methods.
- Question generation: `supabase/functions/generate-questions/index.ts` is a separate Supabase Edge Function.
- Cloudflare R2 staging bucket: `srna-staging-textbooks` (previously provisioned; recheck before deployment).

## Safety requirements
1. Keep production's Supabase storage adapter unchanged until staging passes integration tests.
2. Implement a separate staging adapter with the same public method interface.
3. Bind a dedicated R2 bucket to the staging Worker through an environment-specific binding; never select a bucket using untrusted request parameters.
4. Verify Supabase JWTs server-side and require an explicit admin allowlist or verified admin role. A decoded JWT in the browser is not authorization.
5. Reject cross-origin requests outside the exact staging origin; CORS alone is not authentication.
6. Validate upload MIME type, PDF magic bytes, size, key prefix and object ownership. Do not publish R2 objects.
7. Keep staging metadata, Supabase credentials and generation endpoints isolated from production.
8. Test non-admin rejection, invalid/expired tokens, oversized files, malicious paths, duplicate uploads, missing objects, deletion authorization, and staging-to-production access denial.
9. Deploy the staging hostname only after the hosting target and Worker routes are known.
10. Never merge or deploy staging configuration to production before all gates pass.

## Next implementation
Inspect existing Supabase admin role validation, application hosting and runtime configuration before writing the Worker. Decide whether staging will use a separate Supabase project or a dedicated staging database. Add a dedicated staging Worker with private R2 binding, then wire the browser adapter using a staging-only config flag.

Production remains the default and must not be modified by this staging work.
