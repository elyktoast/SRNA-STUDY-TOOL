"""Unit tests for exclusive, transaction-scoped publication coordination."""
import sys
import threading
import types
import unittest
from unittest.mock import patch

from source_review_publication_lock_v2 import exclusive_publication_lock

KEY = "123e4567-e89b-42d3-a456-426614174000/book.pdf"
BUCKET = "srna-staging-textbooks"


class FakeDatabase:
    def __init__(self):
        self.guard = threading.Lock()
        self.held = set()
        self.keys = []

    def connect(self, url, autocommit=False):
        assert url == "postgres://test"
        assert autocommit is False
        db = self

        class Connection:
            closed = False
            info = type("Info", (), {"transaction_status": 2})()
            lock_id = None
            def __enter__(self):
                return self
            def __exit__(self, *args):
                if self.lock_id is not None:
                    with db.guard:
                        db.held.discard(self.lock_id)
                self.closed = True
            def transaction(self):
                return self
            def cursor(self):
                connection = self
                class Cursor:
                    def __enter__(self):
                        return connection
                    def __exit__(self, *args):
                        return False
                return Cursor()
            def execute(self, query, params):
                assert query == "SELECT pg_try_advisory_xact_lock(%s)"
                self.requested = params[0]
                db.keys.append(self.requested)
            def fetchone(self):
                with db.guard:
                    if self.requested in db.held:
                        return (False,)
                    db.held.add(self.requested)
                    self.lock_id = self.requested
                    return (True,)
        return Connection()


class LockTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDatabase()
        self.module = patch.dict(sys.modules, {"psycopg": types.SimpleNamespace(connect=self.db.connect)})
        self.module.start()
        self.addCleanup(self.module.stop)

    def test_second_publisher_rejected_until_first_releases(self):
        with exclusive_publication_lock("postgres://test", BUCKET, KEY) as first:
            first.assert_held(KEY)
            with self.assertRaisesRegex(ValueError, "Concurrent publication"):
                with exclusive_publication_lock("postgres://test", BUCKET, KEY):
                    self.fail("Second publisher entered")
            with self.assertRaisesRegex(ValueError, "not held"):
                first.assert_held(KEY + ".other")
        with self.assertRaisesRegex(ValueError, "not held"):
            first.assert_held(KEY)
        with exclusive_publication_lock("postgres://test", BUCKET, KEY) as later:
            later.assert_held(KEY)

    def test_independent_sources_can_publish(self):
        with exclusive_publication_lock("postgres://test", BUCKET, KEY):
            with exclusive_publication_lock("postgres://test", BUCKET, KEY + ".other") as other:
                other.assert_held(KEY + ".other")
        self.assertNotEqual(self.db.keys[0], self.db.keys[1])

    def test_exception_releases_lock(self):
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            with exclusive_publication_lock("postgres://test", BUCKET, KEY):
                raise RuntimeError("interrupted")
        with exclusive_publication_lock("postgres://test", BUCKET, KEY) as lock:
            lock.assert_held(KEY)

    def test_missing_database_url_rejected(self):
        with self.assertRaisesRegex(ValueError, "DATABASE_URL"):
            with exclusive_publication_lock("", BUCKET, KEY):
                self.fail("Unexpected lock")


if __name__ == "__main__":
    unittest.main()
