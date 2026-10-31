import hashlib
import unittest
from unittest.mock import patch

from source_review_page_render_v2 import render_verified_pdf_page


class FakePix:
    width = 150
    height = 150
    def tobytes(self, fmt):
        assert fmt == "png"
        return b"valid-png-bytes"


class FakePage:
    class Rect:
        width = 100
        height = 100
    rect = Rect()
    def get_pixmap(self, *, matrix, alpha):
        assert alpha is False
        return FakePix()


class FakeDoc:
    needs_pass = False
    def __len__(self):
        return 2
    def __getitem__(self, index):
        assert index in (0, 1)
        return FakePage()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class FakeFitz:
    @staticmethod
    def open(*, stream, filetype):
        assert stream == b"%PDF-test"
        assert filetype == "pdf"
        return FakeDoc()
    @staticmethod
    def Matrix(x, y):
        return (x, y)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.pdf = b"%PDF-test"
        self.digest = hashlib.sha256(self.pdf).hexdigest()

    def test_renders_verified_physical_page(self):
        with patch.dict("sys.modules", {"fitz": FakeFitz}):
            image, digest = render_verified_pdf_page(
                self.pdf, expected_source_sha256=self.digest, pdf_page=2)
        self.assertEqual(image, b"valid-png-bytes")
        self.assertEqual(digest, hashlib.sha256(image).hexdigest())

    def test_changed_pdf_rejected_before_open(self):
        with self.assertRaisesRegex(ValueError, "changed"):
            render_verified_pdf_page(
                self.pdf, expected_source_sha256="a" * 64, pdf_page=1)

    def test_bad_page_rejected_before_open(self):
        with self.assertRaisesRegex(ValueError, "physical"):
            render_verified_pdf_page(
                self.pdf, expected_source_sha256=self.digest, pdf_page=0)

    def test_oversized_pdf_rejected(self):
        with self.assertRaisesRegex(ValueError, "oversized"):
            render_verified_pdf_page(
                b"x" * (75 * 1024 * 1024 + 1),
                expected_source_sha256=self.digest, pdf_page=1)

    def test_out_of_range_page_rejected(self):
        with patch.dict("sys.modules", {"fitz": FakeFitz}):
            with self.assertRaisesRegex(ValueError, "outside"):
                render_verified_pdf_page(
                    self.pdf, expected_source_sha256=self.digest, pdf_page=3)

    def test_invalid_scale_rejected(self):
        with self.assertRaisesRegex(ValueError, "scale"):
            render_verified_pdf_page(
                self.pdf, expected_source_sha256=self.digest, pdf_page=1, scale=3)

    def test_rejects_encrypted_pdf(self):
        class EncryptedDoc(FakeDoc):
            needs_pass = True
        class EncryptedFitz(FakeFitz):
            @staticmethod
            def open(**kwargs):
                return EncryptedDoc()
        with patch.dict("sys.modules", {"fitz": EncryptedFitz}):
            with self.assertRaisesRegex(ValueError, "Encrypted"):
                render_verified_pdf_page(
                    self.pdf, expected_source_sha256=self.digest, pdf_page=1)


if __name__ == "__main__":
    unittest.main()
