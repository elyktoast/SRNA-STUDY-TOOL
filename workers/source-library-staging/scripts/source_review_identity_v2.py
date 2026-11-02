"""Staging-only server-side reviewer identity resolution.

An authenticated session must be resolved by a trusted auth provider. Admin
membership must come from a protected server-side role lookup. This module
never accepts client-declared roles or user_metadata as authorization.
The adapters are intentionally injected; no production auth is wired yet.
"""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class VerifiedReviewer:
    uid: str
    is_admin: bool


def _uuid(value):
    if not isinstance(value, str):
        raise ValueError("Invalid reviewer identity")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid reviewer identity") from exc
    if parsed.version is None or str(parsed) != value.lower():
        raise ValueError("Invalid reviewer identity")
    return str(parsed)


def resolve_admin_reviewer(access_token, *, auth_provider, protected_role_store):
    """Resolve token using server adapters; never use decoded unverified JWT claims.

    auth_provider.get_user(access_token) must validate the token with the
    authentication authority, including expiry and revocation as supported.
    protected_role_store.is_active_admin(uid) must query a server-protected
    role store, not client claims or mutable user_metadata.
    """
    if not isinstance(access_token, str) or not access_token.strip() or access_token != access_token.strip():
        raise ValueError("Authenticated reviewer session required")
    if auth_provider is None or protected_role_store is None:
        raise ValueError("Trusted reviewer verification adapters required")
    # Fail closed if the trusted authentication or role provider errors. In
    # particular, caller-supplied JWT claims and metadata are never a fallback.
    user = auth_provider.get_user(access_token)
    if not isinstance(user, dict) or user.get("active") is not True:
        raise ValueError("Reviewer session is invalid")
    uid = _uuid(user.get("id"))
    # The verified auth UID is the only identity passed to the protected role
    # lookup. Authorization must be evaluated at import time, not cached from
    # a caller-provided flag.
    is_admin = protected_role_store.is_active_admin(uid)
    if is_admin is not True:
        raise ValueError("Active admin reviewer required")
    return VerifiedReviewer(uid=uid, is_admin=True)
