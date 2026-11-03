"""Offline tests for checkpoint fingerprints and staging feature gate."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from item_generation_checkpoint_store_v2 import fingerprint, record, load, status, complete
from run_grounded_generation_v2 import execute


class FingerprintTests(unittest.TestCase):
    def test_order_independent_mapping_hash(self):
        self.assertEqual(fingerprint({"a": 1, "b": 2}), fingerprint({"b": 2, "a": 1}))
        self.assertNotEqual(fingerprint({"a": 1}), fingerprint({"a": 2}))

    def test_fingerprint_normalizes_postgres_types(self):
        owner = UUID("11111111-1111-4111-8111-111111111111")
        timestamp = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
        self.assertEqual(
            fingerprint({"owner": owner, "at": timestamp, "score": Decimal("1.25")}),
            fingerprint({"score": "1.25", "at": timestamp.isoformat(),
                         "owner": str(owner)}))

    def test_expired_checkpoint_replacement_requires_expiry(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("checkpoint-id",)
        record(conn, owner_uid="11111111-1111-4111-8111-111111111111",
               textbook_id="22222222-2222-4222-8222-222222222222",
               request_hash="a" * 64, evidence_hash="b" * 64,
               stage="concept_card", value={"topic": "airway"})
        sql = cursor.execute.call_args.args[0]
        self.assertIn("on conflict (owner_uid,request_hash) do update", sql)
        self.assertIn("generation_checkpoints_v2.expires_at <= now()", sql)
        self.assertIn("draft=NULL", sql)

    def test_resume_status_exposes_metadata_only(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("draft", 120)
        value = status(conn, owner_uid="11111111-1111-4111-8111-111111111111",
                       textbook_id="22222222-2222-4222-8222-222222222222",
                       request_hash="a" * 64, evidence_hash="b" * 64)
        self.assertEqual(value, {"resumable": True, "next_stage": "rationale",
                                 "expires_in_seconds": 120})
        self.assertNotIn("draft", value)
        cursor.fetchone.return_value = None
        self.assertEqual(status(conn, owner_uid="11111111-1111-4111-8111-111111111111",
                                textbook_id="22222222-2222-4222-8222-222222222222",
                                request_hash="a" * 64, evidence_hash="b" * 64),
                         {"resumable": False, "next_stage": "concept_card"})

    def test_stage_advance_requires_ready_textbook_and_matching_evidence(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("checkpoint-id",)
        record(conn, owner_uid="11111111-1111-4111-8111-111111111111",
               textbook_id="22222222-2222-4222-8222-222222222222",
               request_hash="a" * 64, evidence_hash="b" * 64,
               stage="draft", value={"format": "MC", "stem": "Example"})
        sql, params = cursor.execute.call_args.args
        self.assertIn("t.status='ready'", sql)
        self.assertIn("c.evidence_hash=%s", sql)
        self.assertIn("c.stage='concept_card'", sql)
        self.assertEqual(params[-2:], ("a" * 64, "b" * 64))
        conn.commit.assert_called_once()

    def test_complete_requires_matching_ready_source_and_draft(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("checkpoint-id",)
        complete(conn, owner_uid="11111111-1111-4111-8111-111111111111",
                 textbook_id="22222222-2222-4222-8222-222222222222",
                 request_hash="a" * 64, evidence_hash="b" * 64)
        sql, params = cursor.execute.call_args.args
        self.assertIn("t.status='ready'", sql)
        self.assertIn("c.stage='draft'", sql)
        self.assertIn("c.textbook_id=%s::uuid", sql)
        self.assertEqual(params[2], "22222222-2222-4222-8222-222222222222")
        conn.commit.assert_called_once()
        cursor.fetchone.return_value = None
        with self.assertRaisesRegex(ValueError, "No matching draft"):
            complete(conn, owner_uid="11111111-1111-4111-8111-111111111111",
                     textbook_id="22222222-2222-4222-8222-222222222222",
                     request_hash="a" * 64, evidence_hash="b" * 64)
        conn.commit.assert_called_once()

    def test_invalid_record_fails_before_database_use(self):
        with self.assertRaisesRegex(ValueError, "Invalid checkpoint fingerprint"):
            record(object(), owner_uid="11111111-1111-4111-8111-111111111111",
                   textbook_id="22222222-2222-4222-8222-222222222222",
                   request_hash="bad", evidence_hash="f" * 64,
                   stage="concept_card", value={"x": 1})

    def test_checkpoint_owner_and_evidence_bound_query(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("draft", {"objective": "III.H.4"}, {"stem": "Test"})
        owner = "11111111-1111-4111-8111-111111111111"
        book = "22222222-2222-4222-8222-222222222222"
        result = load(conn, owner_uid=owner, textbook_id=book,
                      request_hash="a" * 64, evidence_hash="b" * 64)
        self.assertEqual(result["draft"]["stem"], "Test")
        sql, params = cursor.execute.call_args.args
        self.assertIn("t.owner_uid=%s::uuid", sql)
        self.assertIn("c.expires_at>now()", sql)
        self.assertEqual(params, (owner, book, owner, "a" * 64, "b" * 64))

    def test_record_commits_each_valid_stage(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("checkpoint-id",)
        record(conn, owner_uid="11111111-1111-4111-8111-111111111111",
               textbook_id="22222222-2222-4222-8222-222222222222",
               request_hash="a" * 64, evidence_hash="b" * 64,
               stage="concept_card", value={"objective": "III.H.4"})
        conn.commit.assert_called_once()

    def test_feature_enabled_resumes_saved_stages(self):
        args = SimpleNamespace(owner_uid="11111111-1111-4111-8111-111111111111",
            topic="airway", mode="NCE", domain="III", section="H", objective="III.H.4",
            format="MC", item_id="q1", textbook_id="22222222-2222-4222-8222-222222222222",
            section_id=None, include_subsections=False, page_start=None,
            page_end=None, limit=8, execute=True, confirm_paid_calls=True)
        evidence = {"topic": "airway", "evidence_count": 1,
                    "can_generate_grounded_questions": True,
                    "sources": [{"passage_id": "p1", "textbook_id": args.textbook_id,
                                 "excerpt": "Indexed evidence"}]}
        result = {"item_id": "q1", "item": {"stem": "Question"},
                  "next_state": "needs_editorial_review", "screening": {},
                  "source_evidence": {}, "generator_issues": []}
        env = {"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true",
               "AI_GENERATION_CHECKPOINTS_ENABLED": "true",
               "AI_PROVIDER_ENDPOINT": "https://api.groq.com/openai/v1/chat/completions",
               "AI_ALLOWED_HOSTS": "api.groq.com", "AI_GENERATOR_MODEL": "openai/gpt-oss-120b",
               "STAGING_RECEIPT_SIGNING_SECRET": "x" * 40}
        saved = {"concept_card": {"objective": "III.H.4"}, "draft": {"stem": "Saved draft"}}
        with patch("run_grounded_generation_v2.build_evidence", return_value=evidence), \
             patch("run_grounded_generation_v2.make_transport", return_value=lambda **k: {}), \
             patch("run_grounded_generation_v2.make_adapter", return_value=lambda x: {}), \
             patch("run_grounded_generation_v2.generate_from_index", return_value=result) as generate, \
             patch("run_grounded_generation_v2.load", return_value=saved) as checkpoint_load, \
             patch("run_grounded_generation_v2.record") as checkpoint_record, \
             patch("run_grounded_generation_v2.complete") as checkpoint_complete:
            execute(object(), args, env)
            checkpoint_load.assert_called_once()
            self.assertEqual(generate.call_args.kwargs["checkpoint"], saved)
            generate.call_args.kwargs["on_checkpoint"]("draft", {"stem": "Another draft"})
            checkpoint_record.assert_called_once()
            checkpoint_complete.assert_called_once()

    def test_preflight_resume_metadata_no_provider_call(self):
        args = SimpleNamespace(owner_uid="11111111-1111-4111-8111-111111111111",
            topic="airway", mode="NCE", domain="III", section="H", objective="III.H.4",
            format="MC", item_id="q1", textbook_id="22222222-2222-4222-8222-222222222222",
            section_id=None, include_subsections=False, page_start=None,
            page_end=None, limit=8, execute=False, confirm_paid_calls=False)
        evidence = {"topic": "airway", "evidence_count": 1,
                    "can_generate_grounded_questions": True,
                    "sources": [{"passage_id": "p1", "textbook_id": args.textbook_id}]}
        with patch("run_grounded_generation_v2.build_evidence", return_value=evidence), \
             patch("item_generation_checkpoint_store_v2.status",
                   return_value={"resumable": True, "next_stage": "rationale",
                                 "expires_in_seconds": 90}) as checkpoint_status, \
             patch("run_grounded_generation_v2.make_transport") as transport:
            output = execute(object(), args, {"STAGING_ONLY": "true",
                "AI_GENERATION_CHECKPOINTS_ENABLED": "true"})
        self.assertTrue(output["dry_run"])
        self.assertEqual(output["resume"]["next_stage"], "rationale")
        checkpoint_status.assert_called_once()
        transport.assert_not_called()

    def test_feature_disabled_does_not_access_checkpoint_storage(self):
        args = SimpleNamespace(owner_uid="owner", topic="airway", mode="NCE",
            domain="I", section="A", objective="I.A.1", format="MC", item_id="q1",
            textbook_id="book", section_id=None, include_subsections=False,
            page_start=None, page_end=None, limit=8, execute=True, confirm_paid_calls=True)
        evidence = {"topic": "airway", "evidence_count": 1,
                    "can_generate_grounded_questions": True,
                    "sources": [{"passage_id": "p1", "textbook_id": "book",
                                 "excerpt": "Indexed evidence"}]}
        result = {"item_id": "q1", "item": {"stem": "Question"},
                  "next_state": "needs_editorial_review", "screening": {},
                  "source_evidence": {}, "generator_issues": []}
        env = {"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true",
               "AI_PROVIDER_ENDPOINT": "https://api.groq.com/openai/v1/chat/completions",
               "AI_ALLOWED_HOSTS": "api.groq.com", "AI_GENERATOR_MODEL": "openai/gpt-oss-120b",
               "STAGING_RECEIPT_SIGNING_SECRET": "x" * 40}
        with patch("run_grounded_generation_v2.build_evidence", return_value=evidence), \
             patch("run_grounded_generation_v2.make_transport", return_value=lambda **k: {}), \
             patch("run_grounded_generation_v2.make_adapter", return_value=lambda x: {}), \
             patch("run_grounded_generation_v2.generate_from_index", return_value=result) as generate, \
             patch("run_grounded_generation_v2.load") as checkpoint_load, \
             patch("run_grounded_generation_v2.record") as checkpoint_record:
            execute(object(), args, env)
        checkpoint_load.assert_not_called()
        checkpoint_record.assert_not_called()
        self.assertIsNone(generate.call_args.kwargs["checkpoint"])
        self.assertIsNone(generate.call_args.kwargs["on_checkpoint"])


if __name__ == "__main__":
    unittest.main()
