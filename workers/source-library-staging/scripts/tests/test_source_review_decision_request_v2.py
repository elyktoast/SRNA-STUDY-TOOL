"""Fail-closed validation of proposed staging approval requests."""
import json
import unittest

from source_review_decision_request_v2 import parse_approval_request

UID = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
KEY = UID + "/1878c3ce-7202-4569-82a0-5029d77b2054.pdf"
PAYLOAD = {
    "path": KEY, "page": 2882, "source_sha256": "a" * 64,
    "image_sha256": "b" * 64, "receipt": "synthetic-receipt",
    "classification": "non_content_divider",
    "review_note": "Owner inspected original PDF divider page",
}


class DecisionRequestTests(unittest.TestCase):
    def encode(self, payload):
        return json.dumps(payload).encode()

    def test_valid_divider_review_payload(self):
        self.assertEqual(parse_approval_request(self.encode(PAYLOAD)), PAYLOAD)

    def test_rejects_missing_extra_and_malformed_fields(self):
        invalid = [
            {**PAYLOAD, "page": True},
            {**PAYLOAD, "page": 0},
            {**PAYLOAD, "page": 100001},
            {**PAYLOAD, "path": "../secret.pdf"},
            {**PAYLOAD, "path": KEY.replace(".pdf", "/../bad.pdf")},
            {**PAYLOAD, "path": KEY.replace(".pdf", ".txt")},
            {**PAYLOAD, "classification": ["non_content_divider"]},
            {**PAYLOAD, "classification": "auto_approved"},
            {**PAYLOAD, "review_note": "short"},
            {**PAYLOAD, "receipt": ""},
            {**PAYLOAD, "source_sha256": "not-a-sha"},
            {**PAYLOAD, "extra": "admin"},
            {k: v for k, v in PAYLOAD.items() if k != "receipt"},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_approval_request(self.encode(value))

    def test_rejects_duplicate_keys_even_when_last_value_is_valid(self):
        body = self.encode(PAYLOAD).decode()
        for duplicate in ('"page":0,', '"classification":"auto_approved",',
                          '"path":"other.pdf",'):
            with self.subTest(duplicate=duplicate), self.assertRaisesRegex(ValueError, "Duplicate"):
                parse_approval_request(("{" + duplicate + body[1:]).encode())

    def test_rejects_nonfinite_values_and_control_character_notes(self):
        body = self.encode(PAYLOAD).decode()
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant), self.assertRaises(ValueError):
                parse_approval_request(body.replace('"page": 2882', '"page": ' + constant).encode())
        for note in ("Valid note\\nwith newline", "Valid note\\twith tab", "Valid note\\u007fDEL"):
            with self.subTest(note=note), self.assertRaises(ValueError):
                parse_approval_request(self.encode({**PAYLOAD, "review_note": note}))

    def test_rejects_invalid_transport_bytes(self):
        for value in (b"", b"{", b"\xff", b"x" * 8193, None, "not bytes"):
            with self.subTest(value=repr(value)[:30]), self.assertRaises(ValueError):
                parse_approval_request(value)


if __name__ == "__main__":
    unittest.main()
