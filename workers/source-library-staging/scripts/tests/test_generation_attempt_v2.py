import unittest
from unittest.mock import MagicMock, patch
from threading import Lock
from item_generation_attempt_v2 import attempt, reserve_rewrite, finish, GenerationBusy, GenerationAlreadyStarted

KEY=dict(owner_uid='00000000-0000-4000-8000-000000000001',textbook_id='00000000-0000-4000-8000-000000000002',item_id='00000000-0000-4000-8000-000000000003',request_hash='a'*64,evidence_hash='b'*64)

class AttemptTests(unittest.TestCase):
    def connection(self,rows):
        conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect=rows
        return conn,cur

    def test_claim_commits_before_provider_and_is_item_scoped_not_expiry_scoped(self):
        conn,cur=self.connection([('id',)])
        with attempt(conn,**KEY):
            self.assertEqual(conn.commit.call_count,1)
            sql,params=cur.execute.call_args.args
            self.assertIn('on conflict (owner_uid,item_id) do nothing',sql)
            self.assertIn("t.status='ready'",sql)
            self.assertNotIn('expires_at',sql)
            self.assertEqual(params[-2:],(KEY['owner_uid'],KEY['textbook_id']))
        self.assertTrue(__import__('item_generation_attempt_v2')._active.acquire(blocking=False))
        __import__('item_generation_attempt_v2')._active.release()

    def test_busy_and_replayed_items_never_reach_paid_body(self):
        conn,cur=self.connection([None])
        with self.assertRaises(GenerationAlreadyStarted):
            with attempt(conn,**KEY):self.fail('paid body reached')
        held=Lock();held.acquire()
        with patch('item_generation_attempt_v2._active',held):
            conn=MagicMock()
            with self.assertRaises(GenerationBusy):
                with attempt(conn,**KEY):self.fail('paid body reached')
            conn.cursor.assert_not_called()
        held.release()

    def test_interruption_does_not_delete_receipt_or_release_rewrite_budget(self):
        conn,cur=self.connection([('id',)])
        with self.assertRaisesRegex(RuntimeError,'interrupted'):
            with attempt(conn,**KEY):raise RuntimeError('interrupted')
        statements=[c.args[0].lower() for c in cur.execute.call_args_list]
        self.assertFalse(any('delete ' in s for s in statements))
        self.assertFalse(__import__('item_generation_attempt_v2')._active.locked())

    def test_rewrite_reserved_once_and_committed_before_provider(self):
        conn,cur=self.connection([('id',),None])
        reserve_rewrite(conn,**KEY);self.assertEqual(conn.commit.call_count,1)
        sql,params=cur.execute.call_args.args
        self.assertIn('rewrite_reserved=false',sql);self.assertIn("state='started'",sql)
        self.assertEqual(params,(KEY['owner_uid'],KEY['textbook_id'],KEY['item_id'],KEY['request_hash'],KEY['evidence_hash']))
        with self.assertRaises(GenerationAlreadyStarted):reserve_rewrite(conn,**KEY)

    def test_invalid_ids_and_fingerprints_fail_before_database(self):
        for change in ({'item_id':'not-a-uuid'},{'request_hash':'bad'},{'owner_uid':'no'}):
            conn=MagicMock()
            with self.subTest(change=change),self.assertRaises(ValueError):
                with attempt(conn,**{**KEY,**change}):pass
            conn.cursor.assert_not_called()

    def test_commit_failure_releases_process_lock_without_releasing_durable_budget(self):
        conn,cur=self.connection([('id',)])
        conn.commit.side_effect=OSError('socket unavailable')
        with self.assertRaisesRegex(OSError,'socket unavailable'):
            with attempt(conn,**KEY):self.fail('paid body reached')
        self.assertFalse(__import__('item_generation_attempt_v2')._active.locked())

    def test_finish_only_changes_started_attempt(self):
        conn,cur=self.connection([('id',),None])
        finish(conn,owner_uid=KEY['owner_uid'],item_id=KEY['item_id'])
        self.assertIn("state='started'",cur.execute.call_args.args[0])
        conn.commit.assert_called_once()
        with self.assertRaises(GenerationAlreadyStarted):finish(conn,owner_uid=KEY['owner_uid'],item_id=KEY['item_id'])
