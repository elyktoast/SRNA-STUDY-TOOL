"""Read-only PostgreSQL test of the exact draft INSERT evidence predicate."""
import os
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from item_draft_storage_v2 import SOURCE_EVIDENCE_MATCH_SQL


def ownership_fixture_sql():
    return """
      with textbooks(id,owner_uid,status) as (values
        ('primary','owner','ready'), ('second','owner','ready'),
        ('foreign','other-owner','ready'), ('pending','owner','processing')),
      passages(id,textbook_id) as (values
        ('p1','primary'),('p2','second'),('p3','foreign'),('p4','pending')),
      evidence(label,ev,expected) as (values
        ('same book','{"passage_id":"p1","textbook_id":"primary"}'::jsonb,true),
        ('second owned book','{"passage_id":"p2","textbook_id":"second"}'::jsonb,true),
        ('foreign owner','{"passage_id":"p3","textbook_id":"foreign"}'::jsonb,false),
        ('not ready','{"passage_id":"p4","textbook_id":"pending"}'::jsonb,false),
        ('spoofed book','{"passage_id":"p2","textbook_id":"primary"}'::jsonb,false),
        ('missing passage','{"passage_id":"missing","textbook_id":"second"}'::jsonb,false),
        ('missing book field','{"passage_id":"p1"}'::jsonb,false))
      select label,expected,exists(select 1 from passages p
        join textbooks source on source.id=p.textbook_id
        where """ + SOURCE_EVIDENCE_MATCH_SQL + """
      ) as allowed from evidence cross join textbooks t where t.id='primary'
      order by label
    """


@unittest.skipUnless(os.environ.get('SRNA_RETRIEVAL_TEST_DATABASE_URL'), 'Explicit staging test database required')
class MultiBookPostgresTests(unittest.TestCase):
    def test_only_exact_passage_book_pairs_in_ready_owned_books_are_allowed(self):
        import psycopg
        with psycopg.connect(os.environ['SRNA_RETRIEVAL_TEST_DATABASE_URL']) as conn:
            with conn.transaction():
                conn.execute('SET TRANSACTION READ ONLY')
                rows = conn.execute(ownership_fixture_sql()).fetchall()
        self.assertEqual(len(rows),7)
        for label, expected, allowed in rows:
            with self.subTest(label=label):
                self.assertEqual(allowed,expected)
