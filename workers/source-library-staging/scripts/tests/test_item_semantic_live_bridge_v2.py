import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_semantic_live_bridge_v2 import make_gemini_embed, build_semantic_lookup

OWNER = "00000000-0000-4000-8000-000000000001"
HASH = "a" * 64


class GeminiEmbeddingTests(unittest.TestCase):
    def test_no_implicit_provider_calls(self):
        with self.assertRaisesRegex(ValueError, "opt-in"):
            make_gemini_embed(api_key="key", model="gemini-embedding-001", enabled=False)
        with self.assertRaisesRegex(ValueError, "model"):
            make_gemini_embed(api_key="key", model="other", enabled=True)

    def test_explicit_request_and_valid_response(self):
        opener = Mock()
        response = MagicMock()
        response.geturl.return_value = ("https://generativelanguage.googleapis.com/v1beta/models/"
                                        "gemini-embedding-001:embedContent")
        response.read.return_value = json.dumps({"embedding": {"values": [0.5, 0.25]}}).encode()
        opener.open.return_value.__enter__ = Mock(return_value=response)
        opener.open.return_value.__exit__ = Mock(return_value=False)
        embed = make_gemini_embed(api_key="test-key", model="gemini-embedding-001",
                                  enabled=True, opener=opener)
        opener.open.assert_not_called()
        self.assertEqual(embed("question stem"), [0.5, 0.25])
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertIn(b"SEMANTIC_SIMILARITY", request.data)
        self.assertEqual(request.get_header("X-goog-api-key"), "test-key")

    def test_bad_provider_vector_rejected(self):
        for values in ([0, 0], [float("nan"), 1], [1e308, 1], [1]):
            opener = Mock()
            response = MagicMock()
            response.geturl.return_value = ("https://generativelanguage.googleapis.com/v1beta/models/"
                                            "gemini-embedding-001:embedContent")
            response.read.return_value = json.dumps({"embedding": {"values": values}}).encode()
            opener.open.return_value.__enter__ = Mock(return_value=response)
            opener.open.return_value.__exit__ = Mock(return_value=False)
            embed = make_gemini_embed(api_key="key", model="gemini-embedding-001",
                                      enabled=True, opener=opener)
            with self.subTest(values=values), self.assertRaises(ValueError):
                embed("stem")


class LiveBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name) / "inventory.json"
        entries = [{"item_id": "prior-1", "stem_hash": HASH}]
        digest = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
        path.write_text(json.dumps({"schema_version": 1, "inventory_digest": digest,
                                    "item_count": 1, "entries": entries}))
        self.env = {"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true",
                    "AI_SEMANTIC_EMBEDDING_OPT_IN": "true",
                    "SEMANTIC_INDEX_OWNER_UID": OWNER,
                    "SEMANTIC_INDEX_EMBEDDING_MODEL": "gemini-embedding-001",
                    "SEMANTIC_INDEX_INVENTORY_PATH": str(path)}
        self.conn = MagicMock()
        cur = MagicMock()
        self.conn.cursor.return_value.__enter__ = Mock(return_value=cur)
        self.conn.cursor.return_value.__exit__ = Mock(return_value=False)
        self.cur = cur

    def test_disabled_never_queries_or_embeds(self):
        embed = Mock()
        result = build_semantic_lookup(self.conn, owner_uid=OWNER,
                                       env={**self.env, "AI_SEMANTIC_EMBEDDING_OPT_IN": "false"},
                                       embed=embed)
        self.assertIsNone(result)
        self.conn.cursor.assert_not_called()
        embed.assert_not_called()

    def test_incomplete_index_leaves_screening_pending_without_paid_call(self):
        embed = Mock()
        self.cur.fetchall.return_value = []
        callback = build_semantic_lookup(self.conn, owner_uid=OWNER, env=self.env, embed=embed)
        self.assertIsNone(callback)
        embed.assert_not_called()

    def test_verified_index_wires_candidate_lookup(self):
        embed = Mock(return_value=[1.0, 0.0])
        self.cur.fetchall.side_effect = [
            [("prior-1", HASH, [1.0, 0.0])],
            [("prior-1", [1.0, 0.0], HASH)]
        ]
        callback = build_semantic_lookup(self.conn, owner_uid=OWNER, env=self.env, embed=embed)
        embed.assert_not_called()
        result = callback({"item_id": "draft-1", "stem": "Example stem"})
        self.assertTrue(result["search_complete"])
        self.assertEqual(len(result["neighbors"]), 1)
        embed.assert_called_once_with("Example stem")

    def test_wrong_owner_rejected_before_db_or_paid_call(self):
        embed = Mock()
        with self.assertRaisesRegex(ValueError, "owner"):
            build_semantic_lookup(self.conn, owner_uid="00000000-0000-4000-8000-000000000002",
                                  env=self.env, embed=embed)
        self.conn.cursor.assert_not_called()
        embed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
