"""Server-only staging reviewer role adapter.

Requires a privileged, non-browser database connection. Never use an
anon/authenticated database connection or accept client-supplied roles.
"""
from uuid import UUID


class ProtectedReviewerRoleStore:
    def __init__(self, connection):
        if connection is None:
            raise ValueError("Protected database connection required")
        self.connection = connection

    def is_active_admin(self, uid):
        if not isinstance(uid, str):
            raise ValueError("Verified reviewer UID required")
        try:
            parsed = UUID(uid)
        except ValueError as exc:
            raise ValueError("Invalid reviewer UID") from exc
        if str(parsed) != uid.lower() or parsed.version is None:
            raise ValueError("Invalid reviewer UID")
        with self.connection.cursor() as cur:
            cur.execute(
                """SELECT EXISTS (
                    SELECT 1 FROM source_library_staging.reviewer_roles_v2
                    WHERE reviewer_uid = %s AND role = 'admin'
                      AND active IS TRUE AND revoked_at IS NULL
                )""",
                (str(parsed),),
            )
            result = cur.fetchone()
        if not result or type(result[0]) is not bool:
            raise ValueError("Protected role lookup returned invalid result")
        return result[0]
