"""No-network tests for staging R2 streaming download and processing."""
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("process_r2_textbook", ROOT / "process_r2_textbook.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeBody:
    def __init__(self, data):
        self.data = data
        self.closed = False

    def iter_chunks(self, chunk_size):
        yield self.data[:4]
        yield self.data[4:]

    def close(self):
        self.closed = True


class FakeR2:
    def __init__(self, data, declared=None, metadata=None):
        self.data = data
        self.declared = len(data) if declared is None else declared
        self.body = FakeBody(data)
        self.metadata = metadata or {}

    def head_object(self, Bucket, Key):
        return {"ContentLength": self.declared, "Metadata": self.metadata}

    def get_object(self, Bucket, Key):
        return {"Body": self.body}


class R2RunnerTests(unittest.TestCase):
    def setUp(self):
        self.owner = "895ed357-27c3-4d4b-a98a-77b0de20760c"
        self.key = self.owner + "/book.pdf"
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "download.pdf"

    def test_real_pdf_through_fake_r2_to_extraction(self):
        """Exercise the actual PDF extractor and validation with fake R2 bytes."""
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Airway assessment and intubation safety.")
        doc.set_toc([[1, "Airway", 1]])
        payload = doc.tobytes()
        doc.close()
        client = FakeR2(payload, metadata={"name": "Anesthesia_Textbook.pdf"})
        result = module.run(self.owner, self.key, apply=False, client=client)
        self.assertEqual(result["pdf_pages"], 1)
        self.assertEqual(result["passages"], 1)
        self.assertFalse(result["indexed"])
        self.assertEqual(result["r2_sha256"], __import__("hashlib").sha256(payload).hexdigest())

    def test_rejects_changed_download_before_processing(self):
        payload = b"%PDF-1.7 fake contents"
        client = FakeR2(payload)
        original_fetch = module.fetch_r2

        def corrupted_fetch(path, owner, key, r2_client):
            result = original_fetch(path, owner, key, r2_client)
            path.write_bytes(b"%PDF-1.7 tampered contents")
            return result

        with patch.object(module, "fetch_r2", side_effect=corrupted_fetch):
            with patch.object(module, "process") as processor:
                with self.assertRaisesRegex(ValueError, "changed before extraction"):
                    module.run(self.owner, self.key, apply=True, client=client)
                processor.assert_not_called()

    def test_runner_preserves_pdf_filename(self):
        payload = b"%PDF-1.7 fake contents"
        with patch.object(module, "process", return_value={"passages": 1, "indexed": False}) as process:
            result = module.run(self.owner, self.key, apply=False, client=FakeR2(payload))
        self.assertEqual(process.call_args.args[0].name, "book.pdf")
        self.assertEqual(result["r2_key"], self.key)

    def test_runner_uses_safe_original_name(self):
        payload = b"%PDF-1.7 fake contents"
        client = FakeR2(payload, metadata={"name": "Nurse_Anesthesia_7e.pdf"})
        with patch.object(module, "process", return_value={"passages": 1}) as process:
            module.run(self.owner, self.key, client=client)
        self.assertEqual(process.call_args.args[0].name, "Nurse_Anesthesia_7e.pdf")

    def test_runner_rejects_unsafe_metadata_filename(self):
        payload = b"%PDF-1.7 fake contents"
        client = FakeR2(payload, metadata={"name": "../another.pdf"})
        with patch.object(module, "process", return_value={"passages": 1}) as process:
            module.run(self.owner, self.key, client=client)
        self.assertEqual(process.call_args.args[0].name, "book.pdf")

    def test_download_and_hash(self):
        import hashlib
        payload = b"%PDF-1.7 fake contents"
        client = FakeR2(payload)
        result = module.fetch_r2(self.path, self.owner, self.key, client)
        self.assertEqual(self.path.read_bytes(), payload)
        self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertTrue(client.body.closed)

    def test_rejects_wrong_owner_before_request(self):
        with self.assertRaisesRegex(ValueError, "owner-scoped"):
            module.fetch_r2(self.path, self.owner, "someone-else/book.pdf", FakeR2(b"%PDF-"))

    def test_rejects_short_download(self):
        client = FakeR2(b"%PDF-1.7", declared=100)
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            module.fetch_r2(self.path, self.owner, self.key, client)
        self.assertTrue(client.body.closed)

    def test_rejects_oversized_download(self):
        client = FakeR2(b"%PDF-1.7 too long", declared=5)
        with self.assertRaisesRegex(ValueError, "exceeded"):
            module.fetch_r2(self.path, self.owner, self.key, client)
        self.assertTrue(client.body.closed)


if __name__ == "__main__":
    unittest.main()
