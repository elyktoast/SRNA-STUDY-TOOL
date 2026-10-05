#!/usr/bin/env python3
from pathlib import Path
import json,sys
r=Path(__file__).resolve().parent
base=r/'basic-principles/exam-1'
m=json.loads((base/'banks.json').read_text())
errs=[]; ids=set(); total=0
for s in m['studioSources']:
 p=json.loads((base/s['data']).read_text()); qs=p['questions']; total+=len(qs)
 if len(qs)!=s['count']: errs.append(f"count mismatch {s['key']}")
 for q in qs:
  uid=s['key']+'-'+str(q['id'])
  if uid in ids: errs.append('duplicate '+uid)
  ids.add(uid)
  if not q.get('options') or not q.get('answer') or any(a<0 or a>=len(q['options']) for a in q['answer']): errs.append('bad answer '+uid)
  img=q.get('image')
  if img and not (base/img['url']).exists(): errs.append('missing image '+uid+' '+img['url'])
print(f"questions={total} unique={len(ids)} errors={len(errs)}")
for e in errs[:50]: print(e)
sys.exit(1 if errs or total!=4000 or len(ids)!=4000 else 0)
