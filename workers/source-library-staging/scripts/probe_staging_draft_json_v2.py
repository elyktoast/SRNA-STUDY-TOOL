"""Isolated signed drafting probes; no rationale, screening, save or publish."""
import json
import os
import time
import psycopg
from build_question_evidence import build_evidence
from item_generation_contract_v2 import build_step
from item_ai_https_transport_v2 import make_transport, TransportError

if os.environ.get('CONFIRM_STAGING_DRAFT_PROBE') != 'true':
    raise SystemExit('Explicit staging drafting probe opt-in required')
with psycopg.connect(os.environ['STAGING_DATABASE_URL'],sslmode='require',connect_timeout=8) as conn:
    packet=build_evidence(conn,'c003287a-10ce-4cc9-926e-ef7c3a162a26','Preoxygenation',textbook_id='6f1b2869-d6ad-4adf-a9d8-888e8a3d9b9d',limit=8)
evidence=packet['sources']
assert evidence
# Diagnostic concept only, grounded in the retrieved pulmonary oxygen-reserve
# passage. This is not a generated question and is never saved or approved.
source=next(p for p in evidence if p['passage_id']=='48ae6394-a0ad-499a-93ed-8542526c3028')
concept={'objective':'III.H.4','mechanism':'Preoxygenation increases pulmonary oxygen content and removes nitrogen from the functional residual capacity.','relevance':'The pulmonary oxygen reservoir delays arterial desaturation during apnea.','misconception':'A normal oxygen saturation alone establishes an adequate pulmonary oxygen reserve.','counterfactual':'Without preoxygenation the oxygen reserve in the functional residual capacity is limited.','evidence_ids':[source['passage_id']]}
step=build_step('item_draft',mode='NCE',domain='III',section='H',objective='III.H.4',evidence=evidence,format='MC',concept_card=concept)
transport=make_transport(allowed_hosts=['api.groq.com'],timeout_seconds=60,relay_url='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay',relay_secret=os.environ['STAGING_RECEIPT_SIGNING_SECRET'])
system='Return exactly one valid JSON object and no markdown. Follow the supplied NCE/SEE v2.0 step contract. For rewrite, return the complete corrected item and preserve protected metadata. For blind_review, independently solve the supplied item without a key or rationale: return item_id and key array for MC/MS, numeric_answer for SA, pairs for DD, or region for HS. Do not claim human verification.'
probes=[('bounded_json',{'max_tokens':2600,'reasoning_effort':'low','response_format':{'type':'json_object'}})]
if os.environ.get('PROBE_BASELINE')=='true':
    probes.insert(0,('baseline',{'max_tokens':2600}))
for label,settings in probes:
    body={'model':'openai/gpt-oss-120b','messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(step,ensure_ascii=False)}],'temperature':0.2,**settings}
    started=time.monotonic()
    try:
        response=transport(endpoint='https://api.groq.com/openai/v1/chat/completions',headers={},body=body)
    except TransportError as error:
        print(json.dumps({'probe':label,'rule':error.rule,'retry_after_seconds':error.retry_after_seconds,'remaining_tokens':error.remaining_tokens}),flush=True)
        raise SystemExit('Signed draft probe transport failed') from None
    choice=response.get('choices',[{}])[0]
    try:
        parsed=json.loads(choice.get('message',{}).get('content',''))
        valid=isinstance(parsed,dict)
    except (ValueError,TypeError):
        parsed={};valid=False
    shape=valid and parsed.get('format')=='MC' and isinstance(parsed.get('stem'),str) and len(parsed.get('options',[]))==4 and isinstance(parsed.get('distractor_evidence'),dict) and set(parsed['distractor_evidence'])=={'A','B','C','D'}
    finish=choice.get('finish_reason');finish=finish if finish in ('stop','length','tool_calls','content_filter') else 'other'
    print(json.dumps({'probe':label,'elapsed_ms':round((time.monotonic()-started)*1000),'finish_reason':finish,'valid_json':valid,'draft_shape_valid':shape,'completion_tokens':response.get('usage',{}).get('completion_tokens')}),flush=True)
    if label=='bounded_json' and not (shape and finish=='stop'):
        raise SystemExit('Bounded JSON drafting probe failed; full generation remains unverified')
if os.environ.get('PROBE_RATIONALE')=='true':
    request=build_step('rationale',mode='NCE',domain='III',section='H',objective='III.H.4',evidence=evidence,format='MC',concept_card=concept,draft=parsed)
    body={'model':'openai/gpt-oss-120b','messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(request,ensure_ascii=False)}],'temperature':0.2,'max_tokens':1400}
    started=time.monotonic()
    try:
        result=transport(endpoint='https://api.groq.com/openai/v1/chat/completions',headers={},body=body)
        rationale=json.loads(result['choices'][0]['message']['content'])
    except TransportError as error:
        print(json.dumps({'probe':'rationale','rule':error.rule}),flush=True)
        raise SystemExit('Isolated rationale transport failed') from None
    except (ValueError,TypeError,KeyError):
        raise SystemExit('Isolated rationale JSON parsing failed') from None
    valid=isinstance(rationale,dict) and all(isinstance(rationale.get(k),str) and rationale[k].strip() for k in ('core_concept','why_key_wins','trap')) and isinstance(rationale.get('distractor_breakdown'),dict) and set(rationale['distractor_breakdown'])=={'A','B','C','D'}
    print(json.dumps({'probe':'rationale','elapsed_ms':round((time.monotonic()-started)*1000),'required_shape_valid':valid,'all_options_explained':valid}),flush=True)
    if not valid: raise SystemExit('Isolated rationale contract failed')
if os.environ.get('PROBE_SCREENING')=='true':
    from types import SimpleNamespace
    from unittest.mock import patch
    from item_ai_provider_v2 import make_adapter as real_make_adapter
    from run_grounded_generation_v2 import execute
    # Reuse the already tested responses; do not pay to regenerate earlier
    # stages while isolating screening/rewrite/blind review. No draft is saved.
    cached={'concept_card':concept,'item_draft':parsed,'rationale':rationale}
    def factory(**kwargs):
        real=real_make_adapter(**kwargs)
        if kwargs['model']=='openai/gpt-oss-120b':
            return lambda request: cached[request['step']] if request['step'] in cached else real(request)
        return real
    args=SimpleNamespace(topic='Preoxygenation',mode='NCE',domain='III',section='H',objective='III.H.4',format='MC',item_id='a0680579-3281-44b4-9476-11d530e12ef3',textbook_id='6f1b2869-d6ad-4adf-a9d8-888e8a3d9b9d',limit=8,section_id=None,include_subsections=False,page_start=None,page_end=None,owner_uid='c003287a-10ce-4cc9-926e-ef7c3a162a26',execute=True,confirm_paid_calls=True)
    environment={'STAGING_ONLY':'true','AI_GENERATION_OPT_IN':'true','AI_PROVIDER_ENDPOINT':'https://api.groq.com/openai/v1/chat/completions','AI_ALLOWED_HOSTS':'api.groq.com','AI_PROVIDER_API_KEY':'signed-relay-only','AI_GENERATOR_MODEL':'openai/gpt-oss-120b','AI_REWRITE_OPT_IN':'true','AI_BLIND_REVIEW_OPT_IN':'true','AI_REVIEWER_MODEL':'qwen/qwen3.8-27b','STAGING_RECEIPT_SIGNING_SECRET':os.environ['STAGING_RECEIPT_SIGNING_SECRET']}
    with psycopg.connect(os.environ['STAGING_DATABASE_URL'],sslmode='require',connect_timeout=8) as conn,patch('run_grounded_generation_v2.make_adapter',side_effect=factory):
        result=execute(conn,args,environment)
    stages={name:value['status'] for name,value in result['screening']['stages'].items()}
    print(json.dumps({'probe':'screening','stages':stages,'generator_issue_rules':[i['rule_id'] for i in result['generator_issues']],'rewrite_attempts':result['screening']['rewrite_attempts_used'],'can_publish':result['can_publish'],'saved':False}),flush=True)
    if any(stages.get(name)!='pass' for name in ('schema','evidence','deterministic_text','blind_model')):
        raise SystemExit('Isolated quality screening did not pass; full acceptance remains blocked')
