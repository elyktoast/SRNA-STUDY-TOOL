"""Fail-closed provenance registration checks, without a live database."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from register_legacy_provenance import register


class LegacyProvenanceTests(unittest.TestCase):
    def test_rejects_unverified_r2_digest_before_db_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "source.pdf"
            pdf.write_bytes(b"%PDF-1.7\\nexample")
            digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
            manifest = {"size_bytes": pdf.stat().st_size, "sha256": digest}
            with patch("register_legacy_provenance.validate", return_value=manifest):
                with self.assertRaisesRegex(ValueError, "Independent R2"):
                    register(tmp, pdf, None, downloaded_sha256=None)
                with self.assertRaisesRegex(ValueError, "Independent R2"):
                    register(tmp, pdf, None, downloaded_sha256="0" * 64)
                with self.assertRaisesRegex(ValueError, "fingerprint"):
                    pdf.write_bytes(b"%PDF-1.7\\ntampered")
                    register(tmp, pdf, None, downloaded_sha256=digest)


if __name__ == "__main__":
    unittest.main()
