"""Opt-in PostgreSQL integration test for one-time page challenge consumption.

Run only against a disposable staging database with the nonce schema installed:
 SRNA_NONCE_TEST_DATABASE_URL=postgresql://... python -m unittest tests.test_source_review_nonce_postgres_v2
Never point this test at a production database.
"""
import os
import threading
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from source_review_nonces_v2 import register_inspection_nonce, consume_inspection_nonce

URL = os.environ.get("SRNA_NONCE_TEST_DATABASE_URL")
SCHEMA = "source_library_staging.page_inspection_nonces_v2"


@unittest.skipUnless(URL, "Requires an explicitly configured disposable PostgreSQL DSN")
class PostgreSQLNonceConcurrencyTests(unittest.TestCase):
    def test_two_simultaneous_consumers_only_one_succeeds(self):
        import psycopg
        uid = str(uuid.uuid4())
        nonce = uuid.uuid4().hex
        key = uid + "/disposable-nonce-test.pdf"
        fields = dict(nonce=nonce, reviewer_uid=uid, owner_uid=uid,
                      source_sha256="a" * 64, r2_key=key, pdf_page=7)
        # All writes are isolated to a unique nonce in the disposable database.
        with psycopg.connect(URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass(%s)", (SCHEMA,))
                if cur.fetchone()[0] is None:
                    self.fail("Disposable database lacks nonce schema")
            register_inspection_nonce(conn, **fields,
                                      issued_at=datetime.now(timezone.utc).timestamp())
        barrier = threading.Barrier(2)
        results = []
        lock = threading.Lock()

        def consume():
            try:
                with psycopg.connect(URL) as conn:
                    barrier.wait(timeout=15)
                    with conn.transaction():
                        consume_inspection_nonce(conn, **fields)
                outcome = "success"
            except ValueError:
                outcome = "rejected"
            except Exception as exc:
                outcome = type(exc).__name__
            with lock:
                results.append(outcome)

        threads = [threading.Thread(target=consume, daemon=True) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads),
                        "Concurrent consumption did not terminate")
        self.assertCountEqual(results, ["success", "rejected"])
        with psycopg.connect(URL) as conn:
            with self.assertRaisesRegex(ValueError, "already consumed"):
                consume_inspection_nonce(conn, **fields)


if __name__ == "__main__":
    unittest.main()
