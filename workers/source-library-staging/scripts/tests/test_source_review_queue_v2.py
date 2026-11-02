import unittest
from source_review_queue_v2 import build_review_queue

UID = "123e4567-e89b-42d3-a456-426614174000"
BASE = {"schema_version": 1, "owner_uid": UID, "r2_key": UID+"/book.pdf",
        "sha256": "a"*64, "pdf_page_count": 6, "low_text_pages": [5, 2],
        "low_text_details": [
            {"pdf_page": 5, "review_category": "ocr_error", "characters": 0, "ocr_failed": True},
            {"pdf_page": 2, "review_category": "image_content_review", "characters": 4, "has_images": True},
        ]}
class QueueTests(unittest.TestCase):
    def test_queue_sorted_and_never_approves(self):
        queue = build_review_queue(BASE)
        self.assertEqual([p["pdf_page"] for p in queue["pages"]], [2, 5])
        self.assertFalse(queue["approval_enabled"])
        self.assertNotIn("text", str(queue))
    def test_rejects_malformed_source_and_page_inventory(self):
        cases = [
            {"owner_uid": "other"}, {"sha256": "wrong"}, {"r2_key": "other/book.pdf"},
            {"pdf_page_count": True}, {"low_text_pages": [2, 2]},
            {"low_text_pages": [2, 3]},
            {"low_text_details": [BASE["low_text_details"][0]]},
            {"low_text_details": [{**BASE["low_text_details"][0], "pdf_page": 7}, BASE["low_text_details"][1]]},
            {"low_text_details": [{**BASE["low_text_details"][0], "review_category": "approved"}, BASE["low_text_details"][1]]},
        ]
        for change in cases:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    build_review_queue({**BASE, **change})

if __name__ == "__main__":
    unittest.main()
