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
from item_mc_batch_v2 import authenticate, with_draft_neighbors


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

    def test_batch_draft_neighbors_require_complete_owner_scoped_lookup(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        owner, draft_id, item_id = (str(uuid4()) for _ in range(3))
        canonical = {"embedding": [1, 0], "neighbors": [], "search_complete": True, "index_id": "canonical"}
        cursor.fetchall.return_value = []
        with self.assertRaises(ValueError):
            with_draft_neighbors(lambda _: canonical, conn, owner, [draft_id], "fixture")
        cursor.fetchall.return_value = [(draft_id, item_id, "Prior stem")]
        with patch("item_mc_batch_v2._embed_stem", return_value=(1, 0)):
            lookup = with_draft_neighbors(lambda _: canonical, conn, owner, [draft_id], "fixture")
            self.assertEqual(lookup({"item_id": str(uuid4())})["neighbors"],
                             [{"item_id": item_id, "embedding": (1, 0)}])
        self.assertEqual(cursor.execute.call_args.args[1], (owner, [draft_id]))
