import unittest
from review_r2_chapters import audit

class ReviewAuditTests(unittest.TestCase):
    def test_invalid_owner(self):
        with self.assertRaises(ValueError):
            audit('invalid', 'invalid/book.pdf', None)

if __name__ == '__main__':
    unittest.main()
