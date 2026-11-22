"""Finish one missing MC option review, never generate/rewrite/approve a question."""
import copy
import json
from uuid import UUID
from urllib.parse import urlsplit
from item_draft_storage_v2 import get_draft
from item_draft_revalidation_v2 import revalidate
from item_generation_checkpoint_store_v2 import fingerprint
from item_draft_review_contract_v2 import approval_issues
from item_option_retrieval_audit_v2 import audit
from item_option_adjudication_handoff_v2 import run
from item_option_audit_screening_v2 import attach
from item_ai_provider_v2 import make_adapter
from item_ai_https_transport_v2 import make_transport
from search_passages import search


class OptionReviewConflict(ValueError):
    pass


def eligible(draft):
    if (not isinstance(draft, dict) or draft.get('format') != 'MC'
            or draft.get('status') != 'pending_review' or draft.get('published') is not False):
        return False
    screening = draft.get('screening')
    if not isinstance(screening, dict):
        return False
    stages = screening.get('stages')
    if not isinstance(stages,dict):
        return False
    pending = stages.get('independent_option_evidence')
    prior = screening.get('independent_option_adjudication') or {}
    if not isinstance(pending,dict) or not isinstance(prior,dict):
        return False
    # An actual clinical judgment must not be sampled again for a better grade.
    if pending.get('status') != 'pending' or prior.get('judgments'):
        return False
    issues = approval_issues(screening, 'MC')
    return bool(issues) and all(x.get('field') == 'screening.stages.independent_option_evidence' for x in issues)


def configured_reviewer(env):
    if (env.get('STAGING_ONLY') != 'true' or env.get('AI_OPTION_REVIEW_OPT_IN') != 'true'
            or not env.get('AI_GENERATOR_MODEL') or not env.get('AI_REVIEWER_MODEL')
            or env['AI_GENERATOR_MODEL'] == env['AI_REVIEWER_MODEL']):
        raise ValueError('Independent option review is not configured')
    endpoint = env.get('AI_PROVIDER_ENDPOINT', '')
    host = urlsplit(endpoint).hostname
    if not host or host not in set(filter(None, env.get('AI_ALLOWED_HOSTS', '').split(','))):
        raise ValueError('Reviewer host is not configured')
    secret = env.get('STAGING_RECEIPT_SIGNING_SECRET', '')
    if not secret:
        raise ValueError('Reviewer relay is not configured')
    transport = make_transport(allowed_hosts=[host], timeout_seconds=50,
        relay_url='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay',
        relay_secret=secret)
    adapter = make_adapter(endpoint=endpoint, api_key=env.get('AI_PROVIDER_API_KEY', ''),
        model=env['AI_REVIEWER_MODEL'], transport=transport, owner_opt_in=True, staging=True)
    def reviewer(payload):
        from run_grounded_generation_v2 import _call_with_bounded_rate_wait
        response = _call_with_bounded_rate_wait(adapter, {**payload, 'step':'option_review',
            'blind':True, 'rules_version':'2.0', 'auto_publish':False})
        if (set(response) != {'judgments'} or not isinstance(response['judgments'], list)
                or any(not isinstance(j, dict) or type(j.get('source_conflict_found')) is not bool
                       for j in response['judgments'])):
            raise ValueError('Invalid independent judgments')
        return [{**j, 'contradiction_found':j['source_conflict_found']} for j in response['judgments']]
    return reviewer


def complete_option_review(conn, *, owner_uid, draft_id, expected_updated_at, environment, reviewer_factory=None):
    if environment.get('STAGING_ONLY') != 'true' or environment.get('AI_OPTION_REVIEW_OPT_IN') != 'true':
        raise ValueError('Staging option review opt-in required')
    owner, did = (str(UUID(str(v))) for v in (owner_uid, draft_id))
    with conn.cursor() as cur:
        cur.execute('select pg_try_advisory_xact_lock(hashtextextended(%s,0))', ('mc-option-review:'+owner+':'+did,))
        if cur.fetchone() != (True,):
            raise OptionReviewConflict('Review already running')
    draft = get_draft(conn, owner_uid=owner, draft_id=did)
    if not eligible(draft):
        raise ValueError('Only a missing option review may be completed')
    if not isinstance(expected_updated_at, str) or expected_updated_at != draft.get('updated_at'):
        raise OptionReviewConflict('Saved draft changed')
    with conn.cursor() as cur:
        cur.execute('select exists(select 1 from source_library_staging.generated_draft_revisions_v2 where owner_uid=%s::uuid and draft_id=%s::uuid)', (owner,did))
        if cur.fetchone() != (False,):
            raise OptionReviewConflict('Saved question has revisions')
    validation = revalidate(conn, owner_uid=owner, draft_id=did)
    if (not isinstance(validation.get('issues'), list) or not validation['issues']
            or any(x.get('field') != 'screening.stages.independent_option_evidence' for x in validation['issues'])):
        raise ValueError('Current source or saved verification is unavailable')
    item = draft['question']
    author_model = draft.get('model')
    if (not isinstance(author_model,str) or not author_model.strip()
            or item.get('model') != author_model or author_model == environment.get('AI_REVIEWER_MODEL')):
        raise ValueError('The reviewer must differ from the original question author')
    refs = draft['evidence'] + item.get('evidence', [])
    primary = draft['textbook_id']
    books = [primary] + sorted({x['textbook_id'] for x in refs if isinstance(x,dict) and isinstance(x.get('textbook_id'),str)} - {primary})
    budget = max(3,len(books))
    retrieval = audit(conn, owner, item, textbook_id=primary, textbook_ids=books,
                      context_query=draft['topic'], limit=budget)
    passages = {}
    for entry in retrieval['option_audits']:
        if entry['search_status'] != 'matches_found':
            continue
        for query in entry['search_queries']:
            for book in books:
                for passage in search(conn,query,owner,limit=max(5,budget),textbook_id=book):
                    if passage['passage_id'] in entry['retrieved_passage_ids']:
                        passages[passage['passage_id']] = passage
    factory = reviewer_factory or (lambda: configured_reviewer(environment))
    calls = []
    def reviewer(payload):
        # Resolve provider configuration only if the trusted handoff has evidence.
        adapter = factory()
        calls.append('option_review')
        return adapter(payload)
    report = run(item,retrieval,reviewer,source_passages=list(passages.values()),
        generator_model_id=author_model,
        reviewer_model_id=environment.get('AI_REVIEWER_MODEL'),require_quotes=True)
    original = copy.deepcopy(draft['screening'])
    result = attach({'screening':copy.deepcopy(original)},retrieval,report)
    updated = result['screening']
    snapshots = [{k:p[k] for k in ('passage_id','textbook_id','pdf_page_start','excerpt')} for p in passages.values()]
    updated['saved_option_review'] = {'recorded_by':'trusted_saved_option_review',
        'question_sha256':fingerprint(item),'source_packet_sha256':fingerprint(snapshots),
        'generator_model_id':author_model,'reviewer_model_id':environment.get('AI_REVIEWER_MODEL'),
        'generation_performed':False,'rewrite_performed':False,'paid_review_performed':bool(calls)}
    # Compare-and-swap protects concurrent edits, reviews, revisions and source changes.
    with conn.cursor() as cur:
        cur.execute('''update source_library_staging.generated_question_drafts_v2 d
          set screening_json=%s::jsonb,updated_at=now()
          where d.id=%s::uuid and d.owner_uid=%s::uuid and d.status='pending_review'
            and d.updated_at=%s::timestamptz and d.question_json=%s::jsonb and d.screening_json=%s::jsonb
            and not exists(select 1 from source_library_staging.generated_draft_revisions_v2 r where r.draft_id=d.id and r.owner_uid=d.owner_uid)
            and not exists(select 1 from jsonb_array_elements(%s::jsonb) s where not exists(
              select 1 from source_library_staging.passages p join source_library_staging.textbooks t on t.id=p.textbook_id
              where p.id::text=s->>'passage_id' and t.id::text=s->>'textbook_id'
                and t.owner_uid=d.owner_uid and t.status='ready'
                and p.page_start=(s->>'pdf_page_start')::integer and left(p.content,1600)=s->>'excerpt'))
          returning d.id::text''', (json.dumps(updated),did,owner,expected_updated_at,
            json.dumps(item),json.dumps(original),json.dumps(snapshots)))
        if cur.fetchone() is None:
            raise OptionReviewConflict('Draft or indexed evidence changed during review')
    return {'draft_id':did,'option_review_status':updated['stages']['independent_option_evidence']['status'],
            'automated_checks_passed':not approval_issues(updated,'MC'),
            'question_modified':False,'generation_performed':False,'rewrite_performed':False,
            'paid_review_performed':bool(calls),'database_writes':True,
            'published':False,'can_publish':False,'clinical_review_required':True}
