# AI Adaptive security design

## Verified from repository
The existing operator admin role is in private.snar_admins. The private.snar_is_admin(uuid) function checks that role. Public snar_admin_status() is callable by authenticated users, and returns whether the current auth.uid() is an admin. The private admin function is not directly granted to browser roles. Source: supabase/migrations/20260927122319_add_operator_admin_role_and_compliance_rpcs.sql.

## Proposed design (not deployed)
Create private source and generated-question tables with RLS. Allow only server endpoints that validate the current authenticated user against the existing admin mechanism to list, edit or publish candidates. Experimental beta delivery must use a separate narrow endpoint that returns only a validated question for its assigned session, never the private bank or answer key. Publishing must require an explicit admin action, be idempotent and preserve existing canonical question IDs and learner history.

## Pending verification
Read live function grants and source-materials bucket policy predicates. Test anonymous and student denial. Audit the browser-local generated drafts and design optional migration. Do not run schema migrations before security tests and rollback plan are reviewed.
