"""Resumable, private, staging-only canonical index population.

Only metadata is logged. Each validated batch commits independently; no stem
or vector artifact is uploaded. A fresh complete reconciliation is required.
"""
import argparse
import json
import os
from uuid import UUID
from backfill_semantic_embeddings_v2 import load_source
from import_semantic_index_v2 import validate_staging_db_url
from item_cloudflare_embeddings_v2 import MODEL, make_embed_many, valid_vector
from item_semantic_inventory_reconcile_v2 import reconcile
from item_semantic_live_bridge_v2 import build_semantic_lookup
from item_semantic_duplicates import screen

def backfill(conn, source_path, *, owner_uid, embed_many, apply=False, max_new=32):
    owner=str(UUID(owner_uid))
    if type(max_new) is not int or not 0<=max_new<=10000 or not callable(embed_many):
        raise ValueError("Invalid backfill configuration")
    source,stems=load_source(source_path)
    inventory={e['item_id']:e['stem_hash'] for e in source['entries']}
    if any(len(stem)>10000 for stem in stems.values()):
        raise ValueError('Canonical stem exceeds embedding input bound')
    # Resolve ownership conflicts and validate previous progress before any
    # paid call. Never overwrite another owner's row or reuse stale embeddings.
    with conn.cursor() as cur:
        cur.execute("""select item_id,owner_uid::text,stem_hash,embedding_model,embedding
          from source_library_staging.question_semantic_index_v2
          where owner_uid=%s::uuid or item_id=any(%s::text[])""",(owner,list(inventory)))
        rows=cur.fetchall()
    existing=set()
    for item_id,stored_owner,stem_hash,model,vector in rows:
        if stored_owner!=owner:
            raise ValueError("Canonical item ownership conflict")
        if model==MODEL and item_id not in inventory:
            raise ValueError("Unexpected canonical index entry requires reconciliation")
        if item_id in inventory and model==MODEL and inventory[item_id]==stem_hash and valid_vector(vector):
            existing.add(item_id)
    pending=[item_id for item_id in inventory if item_id not in existing]
    result={'expected':len(inventory),'existing':len(existing),'remaining':len(pending),
            'new_embeddings':0,'applied':apply,'complete':False,'model':MODEL,
            'inventory_digest':source['inventory_digest']}
    if not apply:
        return result
    batch=[]
    def commit_batch(ids):
        vectors=embed_many([stems[i] for i in ids])
        if not isinstance(vectors,list) or len(vectors)!=len(ids) or any(not valid_vector(v) for v in vectors):
            raise ValueError("Invalid embedding batch response")
        with conn.cursor() as cur:
            cur.executemany("""insert into source_library_staging.question_semantic_index_v2
              (item_id,owner_uid,embedding_model,embedding,stem_hash)
              values (%s,%s::uuid,%s,%s::double precision[],%s)
              on conflict (item_id) do update set embedding_model=excluded.embedding_model,
                embedding=excluded.embedding,stem_hash=excluded.stem_hash,updated_at=now()
              where question_semantic_index_v2.owner_uid=excluded.owner_uid""",
              [(item_id,owner,MODEL,vector,inventory[item_id]) for item_id,vector in zip(ids,vectors)])
            if cur.rowcount!=len(ids):
                raise ValueError("Canonical item ownership conflict")
        conn.commit()
        result['new_embeddings']+=len(ids)
        result['remaining']-=len(ids)
        print(json.dumps({'check':'semantic_backfill_progress','completed':result['expected']-result['remaining'],
                          'expected':result['expected'],'new_embeddings':result['new_embeddings']}),flush=True)
    for item_id in pending[:max_new]:
        # Bound each native request by both document count and total characters.
        if batch and (len(batch)==32 or sum(len(stems[i]) for i in batch)+len(stems[item_id])>128000):
            commit_batch(batch);batch=[]
        batch.append(item_id)
    if batch:
        commit_batch(batch)
    if not result['remaining']:
        verified=reconcile(conn,owner_uid=owner,embedding_model=MODEL,inventory=inventory)
        result['complete']=verified['ready']
    return result

def verify_controls(conn, source_path, *, owner_uid, embed_many):
    source,stems=load_source(source_path)
    env={'STAGING_ONLY':'true','AI_GENERATION_OPT_IN':'true','AI_SEMANTIC_EMBEDDING_OPT_IN':'true',
         'SEMANTIC_INDEX_OWNER_UID':owner_uid,'SEMANTIC_INDEX_EMBEDDING_MODEL':MODEL,
         'SEMANTIC_INDEX_INVENTORY_PATH':str(source_path)}
    lookup=build_semantic_lookup(conn,owner_uid=owner_uid,env=env,embed=lambda stem:embed_many([stem])[0])
    if lookup is None:
        raise ValueError('Complete canonical index required for controls')
    known_id=source['entries'][0]['item_id']
    known=lookup({'item_id':'semantic-control-known-duplicate','stem':stems[known_id]})
    matches=screen(known['embedding'],known['neighbors'])
    if not any(x['item_id']==known_id and x['similarity']>=0.99 for x in matches):
        raise ValueError('Known duplicate control failed')
    unrelated=lookup({'item_id':'semantic-control-unrelated','stem':'A ceramic teapot decorated with geometric stars sits beside a watercolor landscape in an art studio.'})
    if screen(unrelated['embedding'],unrelated['neighbors']):
        raise ValueError('Unrelated semantic control failed')
    return {'check':'semantic_controls','canonical_items':source['item_count'],'known_duplicate_detected':True,
            'unrelated_control_matches':0,'threshold':0.85,'model':MODEL,'question_generation':False,'draft_writes':False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--max-new',type=int,default=32)
    args=parser.parse_args()
    try:
        if os.environ.get('STAGING_ONLY')!='true':
            raise ValueError('Staging only')
        url=os.environ.get('STAGING_DATABASE_URL','')
        validate_staging_db_url(url)
        import psycopg
        embed=make_embed_many(enabled=args.apply,relay_secret=os.environ.get('STAGING_RECEIPT_SIGNING_SECRET')) if args.apply else lambda texts:None
        with psycopg.connect(url,connect_timeout=8,sslmode='require') as conn:
            result=backfill(conn,args.source,owner_uid=os.environ.get('SEMANTIC_INDEX_OWNER_UID',''),
                            embed_many=embed,apply=args.apply,max_new=args.max_new)
            if args.apply and result['complete']:
                print(json.dumps(verify_controls(conn,args.source,owner_uid=os.environ.get('SEMANTIC_INDEX_OWNER_UID',''),embed_many=embed)),flush=True)
        print(json.dumps(result,sort_keys=True))
        return 0 if result['complete'] or not args.apply else 1
    except Exception:
        print(json.dumps({'ok':False,'error':'SEMANTIC_BACKFILL_UNAVAILABLE'}))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
