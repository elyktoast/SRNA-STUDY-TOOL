import unittest
from source_review_identity_v2 import resolve_admin_reviewer, VerifiedReviewer

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"

class Auth:
    def __init__(self, user=None): self.user = user
    def get_user(self, token):
        if token != "verified-token": raise ValueError("Expired or invalid token")
        return self.user

class Roles:
    def __init__(self, result=True): self.result = result; self.lookups = []
    def is_active_admin(self, uid):
        self.lookups.append(uid)
        return self.result

class ReviewerIdentityTests(unittest.TestCase):
    def test_verified_admin(self):
        roles = Roles()
        reviewer = resolve_admin_reviewer("verified-token",
            auth_provider=Auth({"id": UID, "active": True, "user_metadata": {"role": "student"}}),
            protected_role_store=roles)
        self.assertEqual(reviewer, VerifiedReviewer(UID, True))
        self.assertEqual(roles.lookups, [UID])
    def test_unverified_token_rejected(self):
        with self.assertRaises(ValueError):
            resolve_admin_reviewer("forged", auth_provider=Auth({"id": UID, "active": True}), protected_role_store=Roles())
    def test_nonadmin_rejected_despite_claim(self):
        with self.assertRaisesRegex(ValueError, "Active admin"):
            resolve_admin_reviewer("verified-token",
                auth_provider=Auth({"id": UID, "active": True, "user_metadata": {"role": "admin"}}),
                protected_role_store=Roles(False))
    def test_inactive_and_invalid_uid_rejected(self):
        for user in ({"id": UID, "active": False}, {"id": "bad", "active": True}, None):
            with self.subTest(user=user), self.assertRaises(ValueError):
                resolve_admin_reviewer("verified-token", auth_provider=Auth(user), protected_role_store=Roles())
    def test_missing_adapters_or_token_rejected(self):
        for token, auth, roles in (("", Auth(), Roles()), ("verified-token", None, Roles()),
                                   ("verified-token", Auth(), None)):
            with self.assertRaises(ValueError):
                resolve_admin_reviewer(token, auth_provider=auth, protected_role_store=roles)

if __name__ == "__main__":
    unittest.main()
