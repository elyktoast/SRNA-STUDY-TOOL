"""Fixed fictional teaching/source controls; never a held-draft regrade."""
import json
import os
from pathlib import Path
from item_ai_provider_v2 import make_adapter
from item_ai_https_transport_v2 import make_transport
from item_source_quote_spans_v2 import prepare
from run_grounded_generation_v2 import _call_with_bounded_rate_wait

SOURCES = [
    {'passage_id':'control-aster','excerpt':'The fictional Aster sensor records bending of a flexible strip.'},
    {'passage_id':'control-birch','excerpt':'The fictional Birch sensor measures contraction force against a load cell.'},
    {'passage_id':'control-limitation','excerpt':'Aster and Birch values must not be used interchangeably.'},
]
SCOPES = (['control-aster','control-birch'],['control-aster'],['control-aster','control-birch'],
          ['control-limitation'],['control-aster'],['control-limitation'],['control-aster'],['control-aster'])
CASES = (
    ('teaching_distinction', 'This item distinguishes the measurements recorded by Aster and Birch.', True),
    ('teaching_mechanism', 'Understanding Aster means recognizing that it records strip bending.', True),
    ('teaching_contrast', 'This question teaches strip bending versus contraction force.', True),
    ('teaching_limitation', 'This item teaches that Aster and Birch values are not interchangeable.', True),
    ('false_force', 'This question teaches that Aster directly measures contraction force.', False),
    ('false_interchangeability', 'Learning this distinction permits using Aster and Birch values interchangeably.', False),
    ('unsupported_accuracy', 'Knowing the Aster mechanism guarantees accurate force measurement.', False),
    ('unsupported_outcome', 'Understanding Aster improves patient recovery outcomes.', False),
)

def run(adapter):
    packet, lookup=prepare({'source_passages':SOURCES})
    fields=[{'id':'e'+str(i),'label':'concept_card.relevance','text':text,
             'passage_ids':SCOPES[i],'assessment':'teaching_application'}
            for i,(_,text,_) in enumerate(CASES)]
    response=_call_with_bounded_rate_wait(adapter,{'step':'explanation_review','rules_version':'2.0',
        'auto_publish':False,'independent':True,'fields':fields,'source_passages':packet['source_passages']})
    judgments={}
    for group in response['supported_groups']:
        refs=group['quote_refs']
        if not refs or any(r.get('passage_id') not in lookup
                or r.get('span_id') not in lookup[r['passage_id']] for r in refs):
            raise ValueError('Control citations invalid')
        for fid in group['field_ids']:
            scope=SCOPES[int(fid[1:])]
            if any(r['passage_id'] not in scope for r in refs): raise ValueError('Control source scope invalid')
            if fid in judgments: raise ValueError('Repeated control field')
            judgments[fid]=True
    for finding in response['unsupported']:
        fid=finding['field_id']
        if fid in judgments: raise ValueError('Repeated control field')
        judgments[fid]=False
    if set(judgments)!={f['id'] for f in fields}: raise ValueError('Incomplete control fields')
    return [{'case':name,'expected':expected,'observed':judgments['e'+str(i)],
             'pass':judgments['e'+str(i)] is expected} for i,(name,_,expected) in enumerate(CASES)]

def main():
    if os.environ.get('CONFIRM_PAID_TEACHING_CONTROLS')!='true' or os.environ.get('GITHUB_RUN_ATTEMPT')!='1':
        raise SystemExit('First fixed control attempt required')
    config=json.loads((Path(os.environ['REVIEWER_SOURCE_ROOT'])/
                       'workers/source-library-staging/reviewer-gateway/wrangler.json').read_text())['vars']
    model=config['AI_REVIEWER_MODEL']
    if model!='openai/gpt-oss-120b': raise SystemExit('Pinned source reviewer required')
    transport=make_transport(allowed_hosts=['api.groq.com'],
        relay_url='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay',
        relay_secret=os.environ['STAGING_RECEIPT_SIGNING_SECRET'])
    adapter=make_adapter(endpoint='https://api.groq.com/openai/v1/chat/completions',
        api_key='relay-authenticated',model=model,transport=transport,owner_opt_in=True,staging=True)
    result={'reviewer_model':model,'controls':[],'drafts_read':False,'database_writes':False,
            'question_generation_performed':False,'field_scoped_sources':True,'max_logical_reviews':1,'clinical_acceptance':False}
    try:
        result['controls']=run(adapter)
    except Exception as exc:
        result['error_type']=type(exc).__name__
    result['pass']=len(result['controls'])==8 and all(c['pass'] for c in result['controls'])
    Path('/tmp/mc-teaching-controls.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    if not result['pass']: raise SystemExit('Teaching-source controls failed')

if __name__=='__main__': main()
