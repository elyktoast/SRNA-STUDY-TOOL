import hashlib
import unittest

from source_review_r2_loader_v2 import fetch_verified_staging_pdf

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
KEY = UID + "/synthetic.pdf"
PDF = b"%PDF-synthetic-data"


class Body:
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False
    def iter_chunks(self, chunk_size):
        yield from self.chunks
    def close(self):
        self.closed = True


class R2:
    def __init__(self, chunks=None, head_size=None, final_etag="stable"):
        self.body = Body([PDF] if chunks is None else chunks)
        self.size = len(PDF) if head_size is None else head_size
        self.final_etag = final_etag
        self.head_calls = 0
        self.get_calls = 0
    def head_object(self, *, Bucket, Key):
        assert Bucket == "srna-staging-textbooks" and Key == KEY
        self.head_calls += 1
        return {"ContentLength": self.size,
                "ETag": "stable" if self.head_calls == 1 else self.final_etag}
    def get_object(self, *, Bucket, Key):
        assert Bucket == "srna-staging-textbooks" and Key == KEY
        self.get_calls += 1
        return {"Body": self.body}


def fetch(client, digest=None, **kwargs):
    return fetch_verified_staging_pdf(
        client, owner_uid=UID, r2_key=KEY,
        expected_sha256=digest or hashlib.sha256(PDF).hexdigest(), **kwargs)


class R2LoaderTests(unittest.TestCase):
    def test_valid_source(self):
        client = R2()
        self.assertEqual(fetch(client), PDF)
        self.assertEqual(client.head_calls, 2)
        self.assertTrue(client.body.closed)

    def test_modified_content(self):
        client = R2(chunks=[b"%PDF-modified"])
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            fetch(client)
        self.assertTrue(client.body.closed)

    def test_incomplete_download(self):
        client = R2(chunks=[PDF[:-1]])
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            fetch(client)
        self.assertTrue(client.body.closed)

    def test_declared_size_exceeded(self):
        client = R2(chunks=[PDF, b"extra"])
        with self.assertRaisesRegex(ValueError, "exceeded"):
            fetch(client)
        self.assertTrue(client.body.closed)

    def test_source_replaced_during_fetch(self):
        client = R2(final_etag="replaced")
        with self.assertRaisesRegex(ValueError, "replaced"):
            fetch(client)
        self.assertTrue(client.body.closed)

    def test_cross_owner_key_rejected_before_r2(self):
        client = R2()
        with self.assertRaisesRegex(ValueError, "owner-scoped"):
            fetch_verified_staging_pdf(
                client, owner_uid=UID, r2_key="other-user/book.pdf",
                expected_sha256=hashlib.sha256(PDF).hexdigest())
        self.assertEqual(client.head_calls, 0)

    def test_production_bucket_rejected_before_r2(self):
        client = R2()
        with self.assertRaisesRegex(ValueError, "Staging bucket"):
            fetch(client, bucket="srna-private-textbooks")
        self.assertEqual(client.head_calls, 0)

    def test_missing_expected_digest_rejected_before_r2(self):
        client = R2()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            fetch_verified_staging_pdf(
                client, owner_uid=UID, r2_key=KEY, expected_sha256="")
        self.assertEqual(client.head_calls, 0)


if __name__ == "__main__":
    unittest.main()
