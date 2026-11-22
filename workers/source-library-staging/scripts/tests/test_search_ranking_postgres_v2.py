"""Optional read-only PostgreSQL regression for the production ranking expression."""
import os
import unittest

from search_passages import BACK_MATTER_ORDER_SQL


def ranking_fixture_sql():
    # No tables are created, and no textbook excerpts are included.
    return """
        with candidates(id, heading, content, rank) as (values
          (1, 'Index', 'Dense repeated topic terms', 100),
          (2, null, 'References 1108.e3\n1. Study title.', 90),
          (3, 'Respiratory physiology', 'Explanatory teaching text.', 2),
          (4, null, '1. Assess ventilation.\n2. Check oxygenation.', 3),
          (5, 'Index of refraction', 'An optical equipment principle.', 1),
          (6, null, 'Clinical references may disagree on this topic.', 4),
          (7, 'Bibliography', 'A list of publications.', 80),
          (8, null, 'Bibliography\nA list of publications.', 70)
        )
        select p.id from candidates p
        cross join lateral (select p.heading) s
        order by """ + BACK_MATTER_ORDER_SQL + ", p.rank desc, p.id"


@unittest.skipUnless(os.environ.get('SRNA_RETRIEVAL_TEST_DATABASE_URL'),
                     'Explicit private PostgreSQL retrieval test URL required')
class SearchRankingPostgresTests(unittest.TestCase):
    def test_teaching_text_precedes_labelled_back_matter_without_dropping_rows(self):
        import psycopg
        with psycopg.connect(os.environ['SRNA_RETRIEVAL_TEST_DATABASE_URL']) as conn:
            with conn.transaction():
                conn.execute('SET TRANSACTION READ ONLY')
                rows = conn.execute(ranking_fixture_sql()).fetchall()
        self.assertEqual([r[0] for r in rows], [6, 4, 3, 5, 1, 2, 7, 8])


if __name__ == '__main__':
    unittest.main()
