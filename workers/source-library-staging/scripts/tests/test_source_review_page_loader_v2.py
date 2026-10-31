import unittest
from unittest.mock import patch
from source_review_page_loader_v2 import load_verified_review_page

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
KEY = UID + "/synthetic.pdf"
MANIFEST = {"owner_uid": UID, "r2_key": KEY, "sha256": "a" * 64, "pdf_page_count": 3}


def load(**overrides):
    manifest = {**MANIFEST, **overrides}
    return load_verified_review_page(
        owner_uid=UID, r2_key=KEY, pdf_page=2,
        manifest_loader=lambda owner, key: manifest,
        source_loader=lambda owner, key: b"%PDF-synthetic")


class PageLoaderTests(unittest.TestCase):
    @patch("source_review_page_loader_v2.render_verified_pdf_page", return_value=(b"png", "b" * 64))
    def test_verified_source_and_page_binding(self, render):
        result = load()
        self.assertEqual(result["source_sha256"], "a" * 64)
        self.assertEqual(result["image_sha256"], "b" * 64)
        render.assert_called_once_with(
            b"%PDF-synthetic", expected_source_sha256="a" * 64, pdf_page=2)

    @patch("source_review_page_loader_v2.render_verified_pdf_page")
    def test_wrong_owner_manifest_fails_before_render(self, render):
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            load(owner_uid="e" * 36)
        render.assert_not_called()

    @patch("source_review_page_loader_v2.render_verified_pdf_page")
    def test_wrong_key_manifest_fails_before_render(self, render):
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            load(r2_key=UID + "/other.pdf")
        render.assert_not_called()

    @patch("source_review_page_loader_v2.render_verified_pdf_page")
    def test_missing_fingerprint_fails_before_render(self, render):
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            load(sha256=None)
        render.assert_not_called()

    @patch("source_review_page_loader_v2.render_verified_pdf_page")
    def test_manifest_page_limit_fails_before_render(self, render):
        with self.assertRaisesRegex(ValueError, "outside"):
            load(pdf_page_count=1)
        render.assert_not_called()

    @patch("source_review_page_loader_v2.render_verified_pdf_page")
    def test_cross_owner_key_rejected_before_storage(self, render):
        with self.assertRaisesRegex(ValueError, "owner-scoped"):
            load_verified_review_page(
                owner_uid=UID, r2_key="another-user/book.pdf", pdf_page=1,
                manifest_loader=lambda *_: self.fail("manifest accessed"),
                source_loader=lambda *_: self.fail("R2 accessed"))
        render.assert_not_called()

    def test_unsafe_r2_key_rejected_before_any_storage_access(self):
        for suffix in ("../other.pdf", "./book.pdf", "folder//book.pdf",
                       "folder/../book.pdf", "folder/./book.pdf",
                       "folder" + chr(92) + "book.pdf", "book.pdf" + chr(10), "book.pdf" + chr(127)):
            with self.subTest(suffix=repr(suffix)):
                with self.assertRaisesRegex(ValueError, "owner-scoped"):
                    load_verified_review_page(
                        owner_uid=UID, r2_key=UID + "/" + suffix, pdf_page=1,
                        manifest_loader=lambda *_: self.fail("manifest accessed"),
                        source_loader=lambda *_: self.fail("R2 accessed"))

    def test_missing_adapters_rejected(self):
        with self.assertRaisesRegex(ValueError, "adapters"):
            load_verified_review_page(
                owner_uid=UID, r2_key=KEY, pdf_page=1,
                manifest_loader=None, source_loader=None)


if __name__ == "__main__":
    unittest.main()
