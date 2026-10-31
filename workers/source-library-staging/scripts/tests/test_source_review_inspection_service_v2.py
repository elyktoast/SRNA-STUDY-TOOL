import unittest
from unittest.mock import patch
from source_review_inspection_service_v2 import inspect_and_register_page

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
KEY = UID + "/synthetic.pdf"
PAGE = {"owner_uid": UID, "r2_key": KEY, "pdf_page": 1,
        "source_sha256": "a" * 64, "image_sha256": "b" * 64,
        "png": b"trusted-png"}


class Auth:
    def get_user(self, token):
        return {"id": UID, "active": token == "valid"}


class Roles:
    def is_active_admin(self, uid):
        return uid == UID


def run(writer, **changes):
    args = dict(conn=object(), access_token="valid", auth_provider=Auth(),
                protected_role_store=Roles(), owner_uid=UID, r2_key=KEY,
                pdf_page=1, manifest_loader=lambda *_: {},
                source_loader=lambda *_: b"pdf", write_image=writer,
                signing_secret=b"s" * 32, now=1000)
    args.update(changes)
    return inspect_and_register_page(**args)


class InspectionServiceTests(unittest.TestCase):
    @patch("source_review_inspection_service_v2.register_delivered_page_receipt", return_value="signed")
    @patch("source_review_inspection_service_v2.load_verified_review_page", return_value=PAGE)
    def test_delivery_before_receipt(self, load, register):
        seen = []
        def write(data, **kwargs):
            seen.append((data, kwargs))
            self.assertFalse(register.called)
        result = run(write)
        self.assertEqual(result["receipt"], "signed")
        self.assertEqual(seen[0][0], b"trusted-png")
        self.assertEqual(seen[0][1]["cache_control"], "private, no-store")
        register.assert_called_once()

    @patch("source_review_inspection_service_v2.register_delivered_page_receipt")
    @patch("source_review_inspection_service_v2.load_verified_review_page", return_value=PAGE)
    def test_failed_delivery_never_registers(self, load, register):
        def fail(*args, **kwargs):
            raise OSError("stream failed")
        with self.assertRaisesRegex(OSError, "stream failed"):
            run(fail)
        register.assert_not_called()

    @patch("source_review_inspection_service_v2.register_delivered_page_receipt")
    @patch("source_review_inspection_service_v2.load_verified_review_page")
    def test_cross_owner_rejected_before_source_read(self, load, register):
        with self.assertRaisesRegex(ValueError, "does not own"):
            run(lambda *_a, **_kw: None,
                owner_uid="c003287a-10ce-4cc9-926e-ef7c3a162a26")
        load.assert_not_called()
        register.assert_not_called()

    @patch("source_review_inspection_service_v2.register_delivered_page_receipt")
    @patch("source_review_inspection_service_v2.load_verified_review_page")
    def test_invalid_session_rejected_before_source_read(self, load, register):
        with self.assertRaisesRegex(ValueError, "invalid"):
            run(lambda *_a, **_kw: None, access_token="revoked")
        load.assert_not_called()
        register.assert_not_called()


if __name__ == "__main__":
    unittest.main()
