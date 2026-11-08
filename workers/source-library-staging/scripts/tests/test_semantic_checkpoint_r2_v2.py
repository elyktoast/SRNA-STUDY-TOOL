import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
try:
    from cryptography.fernet import Fernet
    from semantic_checkpoint_r2_v2 import transfer, BUCKET, KEY
except ImportError:
    raise unittest.SkipTest('Optional cryptography dependency not installed')


class ClientError(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}


class FakeR2:
    class exceptions:
        ClientError = ClientError

    def __init__(self):
        self.objects = {}
    def get_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise ClientError("NoSuchKey")
        body = Mock()
        body.read.side_effect = lambda n: self.objects[(Bucket, Key)][:n]
        return {"Body": body}
    def head_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise ClientError("404")
        return {"ContentLength": len(self.objects[(Bucket, Key)])}
    def put_object(self, *, Bucket, Key, Body, **kwargs):
        self.objects[(Bucket, Key)] = Body


class TestEncryptedCheckpoint(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "progress.jsonl"
        self.client = FakeR2()
        self.env = {"STAGING_ONLY": "true", "SEMANTIC_CHECKPOINT_R2_OPT_IN": "true",
                    "SEMANTIC_CHECKPOINT_ENCRYPTION_KEY": Fernet.generate_key().decode()}

    def test_round_trip_encrypted_and_exclusive(self):
        original = b'{"schema_version":1}\\n{"item_id":"one"}\\n'
        self.path.write_bytes(original)
        self.assertEqual(transfer("save", self.path, env=self.env, client=self.client), {"saved": True})
        self.assertNotIn(original, self.client.objects[(BUCKET, KEY)])
        self.path.unlink()
        self.assertEqual(transfer("restore", self.path, env=self.env, client=self.client), {"restored": True})
        self.assertEqual(self.path.read_bytes(), original)
        with self.assertRaises(ValueError):
            transfer("restore", self.path, env=self.env, client=self.client)

    def test_remote_checkpoint_cannot_be_overwritten(self):
        self.path.write_bytes(b"first")
        transfer("save", self.path, env=self.env, client=self.client)
        first = self.client.objects[(BUCKET, KEY)]
        self.path.write_bytes(b"second")
        with self.assertRaises(ValueError):
            transfer("save", self.path, env=self.env, client=self.client)
        self.assertEqual(self.client.objects[(BUCKET, KEY)], first)

    def test_missing_checkpoint_does_not_create_file(self):
        self.assertEqual(transfer("restore", self.path, env=self.env, client=self.client),
                         {"restored": False})
        self.assertFalse(self.path.exists())

    def test_opt_in_required(self):
        with self.assertRaises(ValueError):
            transfer("restore", self.path, env={}, client=self.client)

    def test_wrong_encryption_key_fails_closed(self):
        self.path.write_bytes(b"private")
        transfer("save", self.path, env=self.env, client=self.client)
        self.path.unlink()
        bad = dict(self.env, SEMANTIC_CHECKPOINT_ENCRYPTION_KEY=Fernet.generate_key().decode())
        with self.assertRaises(Exception):
            transfer("restore", self.path, env=bad, client=self.client)
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
