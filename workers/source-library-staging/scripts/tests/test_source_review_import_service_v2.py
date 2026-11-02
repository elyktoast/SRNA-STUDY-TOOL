import unittest
from unittest.mock import patch
from source_review_import_service_v2 import import_with_verified_reviewer

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"

class Auth:
    def get_user(self, token):
        if token != "valid": raise ValueError("invalid session")
        return {"id": UID, "active": True, "user_metadata": {"role": "admin"}}

class Roles:
    def __init__(self, admin): self.admin = admin
    def is_active_admin(self, uid): return self.admin

class VerifiedImportTests(unittest.TestCase):
    @patch("source_review_import_service_v2.import_passages")
    def test_verified_admin_is_forwarded(self, importer):
        importer.return_value = "textbook-id"
        result = import_with_verified_reviewer("folder", {"owner_uid": UID}, "conn",
            access_token="valid", auth_provider=Auth(), protected_role_store=Roles(True))
        self.assertEqual(result, "textbook-id")
        importer.assert_called_once_with(
            "folder", {"owner_uid": UID}, "conn",
            authenticated_reviewer_uid=UID, reviewer_is_admin=True)

    @patch("source_review_import_service_v2.import_passages")
    def test_forged_admin_metadata_cannot_import(self, importer):
        with self.assertRaisesRegex(ValueError, "Active admin"):
            import_with_verified_reviewer("folder", {}, "conn",
                access_token="valid", auth_provider=Auth(), protected_role_store=Roles(False))
        importer.assert_not_called()

    @patch("source_review_import_service_v2.import_passages")
    def test_invalid_session_cannot_import(self, importer):
        with self.assertRaises(ValueError):
            import_with_verified_reviewer("folder", {}, "conn",
                access_token="expired", auth_provider=Auth(), protected_role_store=Roles(True))
        importer.assert_not_called()

    @patch("source_review_import_service_v2.import_passages")
    def test_cross_owner_admin_cannot_import(self, importer):
        other_uid = "d7c8ad4c-673d-4d87-a122-7d9bff4451bc"
        with self.assertRaisesRegex(ValueError, "does not own source"):
            import_with_verified_reviewer("folder", {"owner_uid": other_uid}, "conn",
                access_token="valid", auth_provider=Auth(), protected_role_store=Roles(True))
        importer.assert_not_called()

    @patch("source_review_import_service_v2.import_with_verified_reviewer")
    @patch("source_review_roles_supabase_v2.ProtectedReviewerRoleStore")
    @patch("source_review_auth_supabase_v2.SupabaseAuthProvider")
    def test_supabase_composition(self, auth_cls, roles_cls, verified_import):
        from source_review_import_service_v2 import import_with_supabase_reviewer
        auth_cls.return_value = object()
        roles_cls.return_value = object()
        verified_import.return_value = "imported"
        result = import_with_supabase_reviewer(
            "folder", {"owner_uid": UID}, "connection",
            access_token="token", supabase_url="https://example.supabase.co",
            supabase_api_key="public-key")
        self.assertEqual(result, "imported")
        auth_cls.assert_called_once_with("https://example.supabase.co", "public-key")
        roles_cls.assert_called_once_with("connection")
        verified_import.assert_called_once_with(
            "folder", {"owner_uid": UID}, "connection",
            access_token="token", auth_provider=auth_cls.return_value,
            protected_role_store=roles_cls.return_value)

if __name__ == "__main__":
    unittest.main()
