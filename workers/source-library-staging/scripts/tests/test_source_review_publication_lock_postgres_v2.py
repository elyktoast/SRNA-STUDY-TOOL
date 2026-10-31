"""Opt-in real PostgreSQL concurrency check; never runs without a test DSN.

Use a disposable staging database:
 SRNA_PUBLICATION_LOCK_TEST_DATABASE_URL=postgresql://... python -m unittest tests.test_source_review_publication_lock_postgres_v2
"""
import os
import threading
import unittest

from source_review_publication_lock_v2 import exclusive_publication_lock

URL = os.environ.get("SRNA_PUBLICATION_LOCK_TEST_DATABASE_URL")
BUCKET = "srna-staging-textbooks"
KEY = "123e4567-e89b-42d3-a456-426614174000/concurrency-test.pdf"


@unittest.skipUnless(URL, "Requires explicitly configured disposable PostgreSQL test database")
class PostgreSQLConcurrencyTests(unittest.TestCase):
    def test_simultaneous_source_lock_rejected_then_released(self):
        ready = threading.Event()
        release = threading.Event()
        errors = []

        def first_publisher():
            try:
                with exclusive_publication_lock(URL, BUCKET, KEY) as lock:
                    lock.assert_held(KEY)
                    ready.set()
                    if not release.wait(15):
                        raise RuntimeError("Test lock release timed out")
            except Exception as exc:
                errors.append(exc)
                ready.set()

        thread = threading.Thread(target=first_publisher, daemon=True)
        thread.start()
        try:
            self.assertTrue(ready.wait(15), "First publisher never acquired lock")
            self.assertFalse(errors, f"First publisher failed: {errors}")
            with self.assertRaisesRegex(ValueError, "Concurrent publication"):
                with exclusive_publication_lock(URL, BUCKET, KEY):
                    self.fail("Competing publisher acquired exclusive lock")
            with exclusive_publication_lock(URL, BUCKET, KEY + ".independent") as independent:
                independent.assert_held(KEY + ".independent")
        finally:
            release.set()
            thread.join(timeout=15)
        self.assertFalse(thread.is_alive(), "Lock owner did not terminate")
        self.assertFalse(errors, f"Lock owner failed: {errors}")
        with exclusive_publication_lock(URL, BUCKET, KEY) as retry:
            retry.assert_held(KEY)


if __name__ == "__main__":
    unittest.main()
