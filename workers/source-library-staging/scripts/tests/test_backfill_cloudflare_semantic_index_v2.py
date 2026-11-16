import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backfill_cloudflare_semantic_index_v2 import backfill, verify_controls
from item_cloudflare_embeddings_v2 import MODEL

OWNER='c003287a-10ce-4cc9-926e-ef7c3a162a26'
OTHER='00000000-0000-4000-8000-000000000001'
VECTOR=[1.0]+[0.0]*1023
class Cursor:
    def __init__(self,conn):self.conn=conn;self.rowcount=0
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,sql,params):self.rows=list(self.conn.rows.values())
    def fetchall(self):return self.rows
    def executemany(self,sql,records):
        self.rowcount=0
        for item_id,owner,model,vector,stem_hash in records:
            old=self.conn.rows.get(item_id)
            if old is None or old[1]==owner:
                self.conn.pending[item_id]=(item_id,owner,stem_hash,model,vector)
                self.rowcount+=1
class Conn:
    def __init__(self):self.rows={};self.pending={};self.commits=0
    def cursor(self):return Cursor(self)
    def commit(self):self.rows.update(self.pending);self.pending={};self.commits+=1

class CloudflareBackfillTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'private.json'
        entries=[];stems=[]
        for n in range(33):
            stem='Private synthetic stem '+str(n);identifier='item-'+str(n)
            entries.append({'item_id':identifier,'stem_hash':hashlib.sha256(stem.encode()).hexdigest()})
            stems.append({'item_id':identifier,'stem':stem})
        digest=hashlib.sha256(json.dumps(entries,separators=(',',':')).encode()).hexdigest()
        self.path.write_text(json.dumps({'schema_version':1,'inventory_digest':digest,'item_count':33,'entries':entries,'stems':stems}))
        self.hashes={e['item_id']:e['stem_hash'] for e in entries}

    @patch('backfill_cloudflare_semantic_index_v2.reconcile',return_value={'ready':True})
    def test_interrupted_batch_resumes_without_reembedding_committed_items(self,reconcile):
        conn=Conn();calls=[]
        def interrupted(texts):
            calls.append(texts)
            if len(calls)==2:raise RuntimeError('interrupted')
            return [VECTOR for _ in texts]
        logs=io.StringIO()
        with contextlib.redirect_stdout(logs):
            with self.assertRaises(RuntimeError):
                backfill(conn,self.path,owner_uid=OWNER,embed_many=interrupted,apply=True,max_new=10000)
            self.assertEqual(len(conn.rows),32);self.assertEqual(conn.commits,1)
            resumed=[]
            def embed(texts):resumed.extend(texts);return [VECTOR for _ in texts]
            result=backfill(conn,self.path,owner_uid=OWNER,embed_many=embed,apply=True,max_new=10000)
        self.assertEqual(len(resumed),1);self.assertEqual(result['new_embeddings'],1)
        self.assertTrue(result['complete']);self.assertEqual(len(conn.rows),33)
        self.assertNotIn('Private synthetic',logs.getvalue())
        reconcile.assert_called_once()

    def test_preflight_makes_no_embedding_calls_or_writes(self):
        conn=Conn()
        result=backfill(conn,self.path,owner_uid=OWNER,embed_many=lambda texts:self.fail('no call'))
        self.assertEqual(result['remaining'],33);self.assertEqual(conn.commits,0)

    def test_foreign_owner_or_unexpected_inventory_stops_before_paid_calls(self):
        for row in (('item-0',OTHER,self.hashes['item-0'],MODEL,VECTOR),('unexpected',OWNER,'a'*64,MODEL,VECTOR)):
            conn=Conn();conn.rows[row[0]]=row
            with self.assertRaises(ValueError):
                backfill(conn,self.path,owner_uid=OWNER,embed_many=lambda texts:self.fail('no call'),apply=True)
            self.assertEqual(conn.commits,0)

    def test_invalid_embedding_cannot_be_committed(self):
        conn=Conn()
        with self.assertRaises(ValueError):
            backfill(conn,self.path,owner_uid=OWNER,embed_many=lambda texts:[[0.0]*1024 for _ in texts],apply=True)
        self.assertEqual(conn.commits,0);self.assertEqual(conn.rows,{})

    def test_stale_model_hash_and_dimensions_are_not_reused(self):
        for model,stem_hash,vector in (('old-model',self.hashes['item-0'],VECTOR),
                                     (MODEL,'a'*64,VECTOR),(MODEL,self.hashes['item-0'],[1.0,0.0])):
            conn=Conn();conn.rows['item-0']=('item-0',OWNER,stem_hash,model,vector)
            result=backfill(conn,self.path,owner_uid=OWNER,embed_many=lambda texts:self.fail('no call'))
            self.assertEqual(result['existing'],0)

    @patch('backfill_cloudflare_semantic_index_v2.build_semantic_lookup')
    def test_live_controls_require_known_duplicate_and_unrelated_negative(self,builder):
        orthogonal=[0.0,1.0]+[0.0]*1022
        def lookup(item):
            return {'embedding':VECTOR if item['item_id'].endswith('duplicate') else orthogonal,
                    'neighbors':[{'item_id':'item-0','embedding':VECTOR}]}
        builder.return_value=lookup
        result=verify_controls(Conn(),self.path,owner_uid=OWNER,embed_many=lambda texts:self.fail('factory mocked'))
        self.assertTrue(result['known_duplicate_detected']);self.assertEqual(result['unrelated_control_matches'],0)
        builder.return_value=lambda item:{'embedding':orthogonal,'neighbors':[{'item_id':'item-0','embedding':VECTOR}]}
        with self.assertRaisesRegex(ValueError,'Known duplicate control failed'):
            verify_controls(Conn(),self.path,owner_uid=OWNER,embed_many=lambda texts:[])
        builder.return_value=lambda item:{'embedding':VECTOR,'neighbors':[{'item_id':'item-0','embedding':VECTOR}]}
        with self.assertRaisesRegex(ValueError,'Unrelated semantic control failed'):
            verify_controls(Conn(),self.path,owner_uid=OWNER,embed_many=lambda texts:[])
