import hashlib
import hmac
import io
import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_mc_batch_v2 import _embed_stems, authenticate, prior_ids, with_draft_neighbors


class BatchBoundaryTests(unittest.TestCase):
    def test_signed_body_is_bound_to_action_and_owner_and_requires_current_admin(self):
        owner, secret = str(uuid4()), "x" * 32
        timestamp = str(int(time.time()))
        payload = json.dumps({"request": {"format": "MC"}, "prior": []}).encode()
        message = f"srna-mc-batch-v1\nrun\n{owner}\n{timestamp}\n".encode() + payload
        signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
        headers = {"REQUEST_METHOD": "POST", "CONTENT_LENGTH": str(len(payload)),
                   "HTTP_X_BATCH_OWNER": owner, "HTTP_X_BATCH_TIME": timestamp,
                   "HTTP_X_BATCH_SIGNATURE": signature}
        conn_factory = MagicMock()
        with patch("item_mc_batch_v2.ProtectedReviewerRoleStore") as roles:
            roles.return_value.is_active_admin.return_value = True
            self.assertEqual(authenticate({**headers, "wsgi.input": io.BytesIO(payload)},
                                          "run", secret, conn_factory)[0], owner)
            for action, uid, body in (("access", owner, payload), ("run", str(uuid4()), payload),
                                      ("run", owner, payload.replace(b"MC", b"MS"))):
                with self.assertRaises(ValueError):
                    authenticate({**headers, "HTTP_X_BATCH_OWNER": uid, "wsgi.input": io.BytesIO(body)},
                                 action, secret, conn_factory)
            roles.return_value.is_active_admin.return_value = False
            with self.assertRaises(ValueError):
                authenticate({**headers, "wsgi.input": io.BytesIO(payload)}, "run", secret, conn_factory)

    def test_accepted_target_keeps_all_prior_drafts_within_the_signed_limit(self):
        ids = [str(uuid4()) for _ in range(200)]
        self.assertEqual(prior_ids(ids[:-1]), ids[:-1])
        with self.assertRaises(ValueError):
            prior_ids(ids)

    def test_batch_draft_neighbors_require_complete_owner_scoped_lookup(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        owner, draft_id, item_id = (str(uuid4()) for _ in range(3))
        canonical = {"embedding": [1, 0], "neighbors": [], "search_complete": True, "index_id": "canonical"}
        cursor.fetchall.return_value = []
        with self.assertRaises(ValueError):
            with_draft_neighbors(lambda _: canonical, conn, owner, [draft_id], "fixture")
        cursor.fetchall.return_value = [(draft_id, item_id, "Prior stem")]
        with patch("item_mc_batch_v2._embed_stems", return_value={"Prior stem": (1, 0)}):
            lookup = with_draft_neighbors(lambda _: canonical, conn, owner, [draft_id], "fixture")
            self.assertEqual(lookup({"item_id": str(uuid4())})["neighbors"],
                             [{"item_id": item_id, "embedding": (1, 0)}])
        self.assertEqual(cursor.execute.call_args.args[1], (owner, [draft_id]))

    def test_cold_batch_coalesces_unique_stems_and_reuses_only_same_owner_cache(self):
        owner = str(uuid4())
        stems = [f"Synthetic stem {i}" for i in range(40)]
        vector = [1.0] + [0.0] * 1023
        with patch("item_mc_batch_v2.make_embed_many") as factory:
            embed = factory.return_value
            embed.side_effect = lambda texts: [vector for _ in texts]
            first = _embed_stems(owner, "fixture", stems + stems[:2])
            self.assertEqual(len(first), 40)
            self.assertEqual([len(call.args[0]) for call in embed.call_args_list], [32, 8])
            self.assertEqual(_embed_stems(owner, "fixture", stems[:2]), {s: first[s] for s in stems[:2]})
            self.assertEqual(embed.call_count, 2)
            _embed_stems(str(uuid4()), "fixture", stems[:1])
            self.assertEqual(embed.call_count, 3)

    def test_attempt_start_time_uses_the_original_owner_book_and_slot(self):
        from item_generation_checkpoint_store_v2 import lookup_batch_slot

        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        owner, book, item = (str(uuid4()) for _ in range(3))
        scope = {"owner_uid": owner, "textbook_id": book, "item_id": item}
        cursor.fetchone.return_value = None
        self.assertEqual(lookup_batch_slot(conn, **scope), (None, None))
        cursor.fetchone.return_value = ("a" * 64, "b" * 64, None, 1795312217377)
        self.assertEqual(lookup_batch_slot(conn, **scope), (None, 1795312217377))
        self.assertEqual(cursor.execute.call_args.args[1], (owner, book, item))

    def test_completed_slot_recovery_uses_reservation_and_rejects_wrong_identity(self):
        from item_generation_checkpoint_store_v2 import recover_completed_batch_slot

        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        owner, book, slot = (str(uuid4()) for _ in range(3))
        scope = {"owner_uid": owner, "textbook_id": book, "item_id": slot}
        cursor.fetchone.return_value = None
        self.assertIsNone(recover_completed_batch_slot(conn, **scope))
        self.assertEqual(cursor.execute.call_args.args[1], (owner, book, slot))
        result = {"item": {"item_id": slot, "format": "MC"}}
        cursor.fetchone.return_value = ("a" * 64, "b" * 64, result, 1795312217377)
        recovered = recover_completed_batch_slot(conn, **scope)
        self.assertEqual(recovered["_checkpoint_key"], {
            "textbook_id": book, "request_hash": "a" * 64, "evidence_hash": "b" * 64})
        result["item"]["item_id"] = str(uuid4())
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            recover_completed_batch_slot(conn, **scope)
