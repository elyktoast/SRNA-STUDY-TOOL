"""Exclusive per-source PostgreSQL advisory lock for staging R2 publication.

A dedicated database connection owns the transaction until all R2 writes finish.
This coordinates cooperating publisher processes, not arbitrary R2 writers.
"""
import hashlib
from contextlib import contextmanager


class PublicationLock:
    def __init__(self, key, connection):
        self.key = key
        self.connection = connection
        self.active = True

    def assert_held(self, key):
        if not self.active or key != self.key or self.connection.closed:
            raise ValueError("Publication lock not held for source")
        # A lock is transaction-scoped; if the transaction has ended,
        # the connection can remain open while the lock is already gone.
        # psycopg TransactionStatus.INTRANS == 2. A closed transaction
        # releases pg_try_advisory_xact_lock even if the connection survives.
        if self.connection.info.transaction_status != 2:
            raise ValueError("Publication lock transaction is no longer active")


@contextmanager
def exclusive_publication_lock(database_url, bucket, pdf_key):
    if not database_url:
        raise ValueError("DATABASE_URL required for exclusive publication locking")
    import psycopg
    identity = (bucket + "\0" + pdf_key).encode("utf-8")
    lock_id = int.from_bytes(hashlib.sha256(identity).digest()[:8], "big", signed=True)
    with psycopg.connect(database_url, autocommit=False) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", (lock_id,))
                acquired = cursor.fetchone()
                if not acquired or acquired[0] is not True:
                    raise ValueError("Concurrent publication in progress for source")
            lock = PublicationLock(pdf_key, connection)
            try:
                yield lock
            finally:
                lock.active = False
