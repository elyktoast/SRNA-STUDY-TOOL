import {startReviewer} from './container-start.js';

const path = '/generation/mc-batch';
const origin = 'https://staging.srnastudytool.com';
const uuid = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const fields = new Set('topic mode domain section objective format textbook_id textbook_ids section_id include_subsections page_start page_end limit item_id'.split(' '));
export const isBatchPath = value => value === path;

async function internal(env, owner, action, payload) {
 const container = await startReviewer(env);
 const body = JSON.stringify(payload);
 const timestamp = String(Math.floor(Date.now() / 1000));
 const encoder = new TextEncoder();
 const key = await crypto.subtle.importKey('raw', encoder.encode(env.STAGING_RECEIPT_SIGNING_SECRET), {name:'HMAC',hash:'SHA-256'}, false, ['sign']);
 const input = encoder.encode(['srna-mc-batch-v1', action, owner, timestamp, body].join('\n'));
 const signature = Array.from(new Uint8Array(await crypto.subtle.sign('HMAC', key, input)), byte => byte.toString(16).padStart(2,'0')).join('');
 return container.fetch(new Request('http://reviewer.internal/internal/mc-batch/' + action, {
  method:'POST', body, headers:{Origin:origin,'Content-Type':'application/json',
   'X-Batch-Owner':owner,'X-Batch-Time':timestamp,'X-Batch-Signature':signature},
 }));
}

export async function batchRoute(request, env, owner) {
 const headers = {'Access-Control-Allow-Origin':origin,Vary:'Origin','Cache-Control':'private, no-store'};
 const reply = (status, data) => Response.json(data,{status,headers});
 if (env.AI_MC_BATCH_ENABLED !== 'true' || env.AI_GENERATION_CHECKPOINTS_ENABLED !== 'true' || !env.MC_BATCH) return reply(503,{error:'batch_unavailable'});
 if (request.method === 'OPTIONS') return new Response(null,{status:204,headers:{...headers,
  'Access-Control-Allow-Methods':'POST','Access-Control-Allow-Headers':'Authorization, Content-Type'}});
 if (request.method !== 'POST' || new URL(request.url).search || !uuid.test(owner)) return reply(400,{error:'invalid_batch_request'});
 try {
  const reader = request.body?.getReader();
  if (!reader) return reply(400,{error:'invalid_batch_request'});
  const decoder = new TextDecoder('utf-8',{fatal:true});
  let body = '', size = 0;
  for (;;) {
   const {value,done} = await reader.read();
   if (done) break;
   size += value.byteLength;
   if (size > 128 * 1024) {
    await reader.cancel();
    return reply(413,{error:'batch_request_too_large'});
   }
   body += decoder.decode(value,{stream:true});
  }
  let data;
  try { data = JSON.parse(body + decoder.decode()); } catch { return reply(400,{error:'invalid_batch_request'}); }
  if (!['start','status','resume','cancel'].includes(data?.action)) return reply(400,{error:'invalid_batch_request'});
  if (!(await internal(env,owner,'access',{})).ok) return reply(403,{error:'batch_access_denied'});
  const queue = env.MC_BATCH.getByName(owner);
  const result = await queue.control(owner,data);
  return reply(result.error ? 409 : 200,result);
 } catch {
  return reply(503,{error:'batch_unavailable'});
 }
}

export function acceptedCount(batch) {
 return new Set(batch.items.filter(item => item.status === 'ready' && item.accepted === true && uuid.test(item.draftId))
  .map(item => item.draftId)).size;
}

export function newSlot(request) {
 return {id:crypto.randomUUID(),request,status:'queued'};
}

export function snapshot(batch) {
 if (!batch) return {batch:null};
 return {batch:{id:batch.id, requested:batch.requested, status:batch.status, reason:batch.reason, nextRunAt:batch.nextRunAt,
  ...(batch.goal === 'accepted' ? {goal:batch.goal,attemptLimit:batch.attemptLimit,
   deadlineAt:batch.deadlineAt,acceptedCount:acceptedCount(batch)} : {}),
  items:batch.items.map(({id,request,status,draftId,reason,accepted}) => ({id,topic:request.topic,status,draftId,reason,accepted}))}};
}

export function prepare(data) {
 if (!uuid.test(data.id) || ![25,50,100].includes(data.count) || data.confirm !== true ||
     (data.goal !== undefined && data.goal !== 'accepted') ||
     !Array.isArray(data.jobs) || !data.jobs.length || data.jobs.length > data.count) return null;
 if (data.jobs.some(job => !job || Object.keys(job).some(key => !fields.has(key)) ||
     job.format !== 'MC' || typeof job.topic !== 'string' || !job.topic.trim() ||
     typeof job.textbook_id !== 'string' || JSON.stringify(job).length > 1200)) return null;
 return data.jobs.map(({item_id:ignored,...request}) => newSlot(request));
}

export async function executeSlot(env, batch, slot, recover) {
 const prior = [...new Set(batch.items.filter(item => item.draftId).map(item => item.draftId))];
 const response = await internal(env,batch.owner,'run',{
  request:{...slot.request,item_id:slot.id,resume_completed_only:recover},prior,
 });
 if (!response.ok) {
  const body = await response.json().catch(() => null);
  if (response.status === 409 && body?.rule === 'GENERATION_BUSY' && !recover) return {status:'busy'};
  if (recover && response.status === 409 && body?.rule === 'CHECKPOINT_NOT_COMPLETE') {
   const startedAt = body.attempt_started_at_ms;
   const attemptedAt = Number.isSafeInteger(startedAt) && startedAt > 0 && startedAt <= Date.now()
    ? startedAt : undefined;
   return {status:'checkpoint_missing',attemptedAt};
  }
  if (!recover && [429,503].includes(response.status) && /^PROVIDER_[A-Z_]+$/.test(body?.rule || '')) {
   const retryAfter = Number.isInteger(body.retry_after_seconds) && body.retry_after_seconds > 0 &&
    body.retry_after_seconds <= 3600 ? body.retry_after_seconds : undefined;
   return {status:'provider_failed',retryAfter};
  }
  if (response.status >= 500 || response.status === 429 || response.status === 409 || recover) return {status:'interrupted'};
  return {status:'failed',reason:response.status === 403 ? 'batch_access_denied' : 'generation_rejected'};
 }
 const result = await response.json();
 if (!uuid.test(result.draft_id) || result.published !== false || typeof result.requires_human_review !== 'boolean') throw Error('invalid_generation_result');
 const names = ['schema','deterministic_text','math','evidence','duplicates','blind_model','editorial_quality','explanation_evidence','independent_option_evidence','options_only'];
 const stages = names.map(name => result.screening?.stages?.[name]);
 const passed = stages.every(stage => stage?.status === 'pass' && stage.issues?.length === 0);
 const ready = result.draft_status === 'approved_for_bank' && result.requires_human_review === false && passed;
 if (result.requires_human_review === false && !ready) throw Error('invalid_automatic_acceptance');
 const reviewReports = [...stages, result.screening?.independent_option_adjudication];
 const unavailable = reviewReports.some(report => /^(PROVIDER_|RELAY_)/.test(report?.provider_rule || report?.review_error || ''));
 return {status:ready?'ready':'held',draftId:result.draft_id,accepted:ready,...(unavailable?{reason:'review_provider_unavailable'}:{})};
}
