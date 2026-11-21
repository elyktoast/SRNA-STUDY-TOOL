"""Read-only source preparation plus concept-contract control, never a draft."""
import ast
import json
import os
from pathlib import Path
from types import SimpleNamespace
import psycopg
from build_question_evidence import build_evidence
from item_mc_source_discovery_v2 import discover
from item_mc_choice_plan_v2 import validate, source_refs
from item_source_quote_spans_v2 import prepare
from item_generation_contract_v2 import build_step
from item_generation_runner_v2 import CONCEPT_FIELDS
from item_ai_provider_v2 import make_adapter
from item_ai_https_transport_v2 import make_transport
from run_grounded_generation_v2 import _call_with_bounded_rate_wait

OWNER='c003287a-10ce-4cc9-926e-ef7c3a162a26'
TOPIC='Quantitative Monitoring: Electromyography — Record the evoked muscle action potential'

def main():
    if os.environ.get('CONFIRM_PAID_SOURCE_PREPARATION')!='true' or os.environ.get('GITHUB_RUN_ATTEMPT')!='1':
        raise SystemExit('First bounded preparation control required')
    root=Path(os.environ['REVIEWER_SOURCE_ROOT'])
    script_root=root/'workers/source-library-staging/scripts'
    config=json.loads((root/'workers/source-library-staging/reviewer-gateway/wrangler.json').read_text())['vars']
    if config.get('AI_SOURCE_DISCOVERY_OPT_IN')!='true' or config.get('AI_AUTHORING_PROVIDER')!='cloudflare':
        raise SystemExit('Pinned source preparation configuration required')
    allowed_errors={node.exc.args[0].value for node in ast.walk(ast.parse(
        (script_root/'item_mc_choice_plan_v2.py').read_text())) if isinstance(node,ast.Raise)
        and isinstance(node.exc,ast.Call) and isinstance(node.exc.func,ast.Name)
        and node.exc.func.id=='ValueError' and node.exc.args
        and isinstance(node.exc.args[0],ast.Constant) and isinstance(node.exc.args[0].value,str)}
    allowed_errors.update({'Concept metadata incomplete','Concept source identity invalid','Invalid source search plan'})
    transport=make_transport(allowed_hosts=['api.groq.com'],
        relay_url='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay',
        relay_secret=os.environ['STAGING_RECEIPT_SIGNING_SECRET'])
    adapter=make_adapter(endpoint='https://api.groq.com/openai/v1/chat/completions',
        api_key='relay-authenticated',model=config['AI_CLOUDFLARE_MODEL'].removeprefix('@cf/'),transport=transport,
        owner_opt_in=True,staging=True,max_output_tokens=8192)
    call=lambda p:_call_with_bounded_rate_wait(adapter,p)
    result={'drafts_read':False,'database_writes':False,'draft_generation_performed':False,
            'clinical_acceptance':False,'max_logical_authoring_calls':2,'pass':False}
    stage='retrieval'
    try:
        with psycopg.connect(os.environ['STAGING_DATABASE_URL'],connect_timeout=20,
            options='-c default_transaction_read_only=on -c statement_timeout=20000') as conn:
            with conn.cursor() as cur:
                cur.execute("select id::text from source_library_staging.textbooks where owner_uid=%s::uuid and status='ready' order by filename,id limit 9",(OWNER,))
                books=[r[0] for r in cur.fetchall()]
            if not 1 <= len(books) <= 8: raise ValueError('Selected library unavailable')
            args=SimpleNamespace(owner_uid=OWNER,topic=TOPIC,textbook_id=books[0],textbook_ids=books,
                section_id=None,include_subsections=False,page_start=None,page_end=None)
            initial=build_evidence(conn,OWNER,TOPIC,textbook_id=books[0],textbook_ids=books,limit=8)
            stage='source_discovery'
            packet,metadata=discover(conn,args,initial,call)
            result['source_discovery']=metadata
            result['initial_passages']=len(initial['sources']);result['prepared_passages']=len(packet['sources'])
            stage='concept_authoring'
            card=call(build_step('concept_card',mode='NCE',domain='II',section='C',objective='II.C.4',
                                evidence=packet['sources'],topic=TOPIC,format='MC'))
            if set(card)=={'concept_card'}: card=card['concept_card']
            stage='concept_contract'
            _,lookup=prepare({'source_passages':packet['sources']})
            grounding=(card.get('choice_plan') or {}).get('option_grounding',{})
            shapes={}
            for oid in 'ABCD':
                entry=grounding.get(oid) if isinstance(grounding,dict) else None
                if not isinstance(entry,dict): shapes[oid]={'entry_object':False};continue
                refs=source_refs(entry) if ('source_refs' in entry or all(k in entry for k in ('passage_id','span_ids'))) else None
                pids=[r.get('passage_id') for r in refs if isinstance(r,dict) and isinstance(r.get('passage_id'),str)] if isinstance(refs,list) else []
                span_duplicates=0;unknown=0
                for ref in refs if isinstance(refs,list) else []:
                    if not isinstance(ref,dict): unknown+=1;continue
                    pid,spans=ref.get('passage_id'),ref.get('span_ids')
                    if not isinstance(pid,str) or not isinstance(spans,list): unknown+=1;continue
                    valid_spans=[v for v in spans if isinstance(v,str)]
                    span_duplicates+=len(valid_spans)-len(set(valid_spans))
                    unknown+=sum(1 for sid in spans if not isinstance(sid,str) or pid not in lookup or sid not in lookup[pid])
                text=entry.get('explanation')
                shapes[oid]={'entry_object':True,'reference_count':len(refs) if isinstance(refs,list) else None,
                    'duplicate_passages':len(pids)-len(set(pids)),'duplicate_spans':span_duplicates,
                    'unknown_spans':unknown,'explanation_chars':len(text) if isinstance(text,str) else None,
                    'explanation_nonempty':isinstance(text,str) and bool(text.strip())}
            result['grounding_shape']=shapes
            raw_ids=card.get('evidence_ids')
            ids=[pid for pid in raw_ids if isinstance(pid,str)] if isinstance(raw_ids,list) else []
            result['concept_evidence_shape']={'count':len(raw_ids) if isinstance(raw_ids,list) else None,
                'unique_strings':len(set(ids)),'unknown_strings':sum(pid not in lookup for pid in ids)}
            validate(card.get('choice_plan'),packet['sources'])
            if (card.get('objective')!='II.C.4' or not isinstance(card.get('evidence_ids'),list)
                    or not card['evidence_ids'] or len(set(card['evidence_ids'])) != len(card['evidence_ids'])
                    or any(not isinstance(card.get(k),str) or not card[k].strip() for k in CONCEPT_FIELDS if k!='evidence_ids')):
                raise ValueError('Concept metadata incomplete')
            if not set(card['evidence_ids']).issubset({p['passage_id'] for p in packet['sources']}):
                raise ValueError('Concept source identity invalid')
            result['concept_contract_valid']=True
            result['pass']=True
    except Exception as exc:
        result['failed_stage']=stage
        result['error_rule']=getattr(exc,'rule',None) or 'PREPARATION_VALIDATION'
        result['validation_detail']=str(exc) if str(exc) in allowed_errors else None
    Path('/tmp/mc-source-preparation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    if not result['pass']: raise SystemExit('Source preparation control remains blocked')

if __name__=='__main__': main()
