"""Server-only staging reviewer role adapter.

Uses the canonical private.snar_admins operator-admin authority.\nRequires a privileged, non-browser database connection. Never use an
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
        # This query requires a trusted direct PostgreSQL connection with
        # private-schema read access. A service-role REST key is insufficient.
        with self.connection.cursor() as cur:
            cur.execute(
                """SELECT EXISTS (
                    SELECT 1 FROM private.snar_admins
                    WHERE user_id = %s AND role = 'operator_admin'
                )""",
                (str(parsed),),
            )
            result = cur.fetchone()
        if not result or type(result[0]) is not bool:
            raise ValueError("Protected role lookup returned invalid result")
        return result[0]
