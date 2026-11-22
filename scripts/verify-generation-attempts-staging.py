"""Disposable real-PostgreSQL attempt/concurrency/budget checks; no AI calls or questions."""
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from urllib.parse import urlsplit
import psycopg
from item_generation_attempt_v2 import attempt,reserve_rewrite,GenerationBusy,GenerationAlreadyStarted

url=os.environ['STAGING_DATABASE_URL']
host=urlsplit(url).hostname
assert host=='db.xqyasyambwdyhsjkftqu.supabase.co' or (host.endswith('.pooler.supabase.com') and urlsplit(url).username=='postgres.xqyasyambwdyhsjkftqu')
owner='c003287a-10ce-4cc9-926e-ef7c3a162a26'
ids=[str(uuid4()),str(uuid4())]
with psycopg.connect(url) as conn:
 with conn.cursor() as cur:
  cur.execute("select id::text from source_library_staging.textbooks where owner_uid=%s::uuid and status='ready' order by id limit 1",(owner,));book=cur.fetchone()[0]
key=dict(owner_uid=owner,textbook_id=book,item_id=ids[0],request_hash='a'*64,evidence_hash='b'*64)
def busy():
 with psycopg.connect(url) as other:
  try:
   with attempt(other,**{**key,'item_id':ids[1]}):raise AssertionError('Overlapping generation admitted')
  except GenerationBusy:return True
try:
 with psycopg.connect(url) as conn:
  try:
   with attempt(conn,**key):
    with ThreadPoolExecutor(max_workers=1) as pool:assert pool.submit(busy).result(timeout=15)
    reserve_rewrite(conn,**key)
    raise RuntimeError('Simulated interruption after durable rewrite reservation')
  except RuntimeError as exc:
   assert str(exc).startswith('Simulated interruption')
 for changed in ({},{'request_hash':'c'*64},{'evidence_hash':'d'*64}):
  with psycopg.connect(url) as conn:
   try:
    with attempt(conn,**{**key,**changed}):raise AssertionError('Paid replay admitted')
   except GenerationAlreadyStarted:pass
 with psycopg.connect(url) as conn:
  try:reserve_rewrite(conn,**key);raise AssertionError('Second rewrite admitted')
  except GenerationAlreadyStarted:pass
 with psycopg.connect(url) as conn:
  with conn.cursor() as cur:
   cur.execute('select rewrite_reserved,state from source_library_staging.generation_attempts_v2 where owner_uid=%s::uuid and item_id=%s::uuid',(owner,ids[0]));assert cur.fetchone()==(True,'started')
   cur.execute('select count(*) from source_library_staging.generation_attempts_v2 where owner_uid=%s::uuid and item_id=%s::uuid',(owner,ids[1]));assert cur.fetchone()[0]==0
 with psycopg.connect(url) as conn:
  with attempt(conn,**{**key,'item_id':ids[1]}):pass
 print('Real PostgreSQL checks passed: concurrent HTTP work blocked, interrupted budget retained, changed hashes cannot replay, new item admitted; zero AI calls and zero question writes')
finally:
 # Delete only the freshly allocated, unpaid test receipts. Never delete a real attempt.
 with psycopg.connect(url) as conn:
  with conn.cursor() as cur:cur.execute('delete from source_library_staging.generation_attempts_v2 where owner_uid=%s::uuid and item_id=any(%s::uuid[])',(owner,ids))
