"""Staging-only authenticated import adapter; not exposed as an HTTP route.

Only trusted server code should supply auth_provider and protected_role_store.
No client-provided reviewer ID or admin flag is accepted.
"""
from source_review_identity_v2 import resolve_admin_reviewer
from import_extraction import import_passages


def import_with_verified_reviewer(folder, manifest, connection, *,
                                  access_token, auth_provider, protected_role_store):
    reviewer = resolve_admin_reviewer(
        access_token, auth_provider=auth_provider,
        protected_role_store=protected_role_store)
    # An administrator may review a source owned by another user only through
    # a separately authorized workflow; this importer is owner-scoped.
    if manifest.get("owner_uid") != reviewer.uid:
        raise ValueError("Reviewer does not own source")
    return import_passages(
        folder, manifest, connection,
        authenticated_reviewer_uid=reviewer.uid,
        reviewer_is_admin=reviewer.is_admin)
