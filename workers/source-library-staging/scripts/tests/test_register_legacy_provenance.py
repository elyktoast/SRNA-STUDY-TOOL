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


    def test_dry_run_does_not_insert_and_apply_registers_once(self):
        from unittest.mock import MagicMock
        from uuid import UUID
        owner = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
        key = owner + "/sample.pdf"
        digest = "a" * 64
        manifest = {"owner_uid": owner, "r2_key": key, "size_bytes": 100,
                    "pdf_page_count": 3, "sha256": digest}
        textbook_id = UUID("2a589498-aaa4-410f-b51a-00d3ab99eafd")

        def run_case(apply, versions):
            connection = MagicMock()
            cursor = connection.cursor.return_value.__enter__.return_value
            cursor.fetchone.side_effect = [
                (textbook_id, UUID(owner), 100, 3),
                None,
            ]
            cursor.fetchall.side_effect = [
                [(0, 1, 1, "passage")],
                versions,
            ]
            with patch("register_legacy_provenance.validate", return_value=manifest), \
                 patch("register_legacy_provenance.verify_pdf", return_value=digest), \
                 patch("register_legacy_provenance.compare_passages",
                       return_value={"matched": True, "passage_count": 1}):
                result = register(".", "source.pdf", connection, apply=apply,
                                  downloaded_sha256=digest)
            sql = [str(call.args[0]).lower() for call in cursor.execute.call_args_list]
            return result, sql

        result, sql = run_case(False, [])
        self.assertFalse(result["provenance_registered"])
        self.assertTrue(any("read only" in q for q in sql))
        self.assertFalse(any("insert into" in q for q in sql))

        result, sql = run_case(True, [])
        self.assertTrue(result["provenance_registered"])
        self.assertTrue(any("insert into" in q for q in sql))
        self.assertTrue(any("advisory_xact_lock" in q for q in sql))
        self.assertFalse(any("delete from" in q for q in sql))

        result, sql = run_case(True, [(digest, UUID(owner), 100, key)])
        self.assertTrue(result["already_registered"])
        self.assertFalse(any("insert into" in q for q in sql))


if __name__ == "__main__":
    unittest.main()
