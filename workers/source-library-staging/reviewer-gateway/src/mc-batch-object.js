import {DurableObject} from 'cloudflare:workers';
import {acceptedCount, executeSlot, newSlot, prepare, snapshot} from './mc-batch.js';

const recoveryDeadline = 17 * 60_000;
const recoveryInterval = 60_000;
const earlyRecovery = 5000;
const accessRetry = 60_000;
const targetWindow = 12 * 60 * 60_000;

function targetStop(batch) {
 if (batch.goal !== 'accepted') return;
 if (acceptedCount(batch) >= batch.requested) return 'target_reached';
 if (Date.now() >= batch.deadlineAt) return 'time_budget_exhausted';
 if (batch.items.length >= batch.attemptLimit && !batch.items.some(item => item.status === 'queued')) {
  return 'attempt_budget_exhausted';
 }
}

function finish(batch, reason) {
 batch.status = 'complete';
 if (reason) batch.reason = reason;
 else delete batch.reason;
 delete batch.nextRunAt;
}

function continuationDelay(batch, result) {
 if (result.reason === 'batch_access_denied') return accessRetry;
 if (!['review_provider_unavailable','generation_provider_unavailable'].includes(result.reason)) {
  batch.providerFailures = 0;
  return 1000;
 }
 batch.providerFailures = (batch.providerFailures || 0) + 1;
 return Math.max(Math.min(120_000, 15_000 * 2 ** Math.min(batch.providerFailures - 1, 3)),
                 (result.retryAfter || 0) * 1000);
}

function schedule(txn, batch, delay) {
 batch.nextRunAt = Date.now() + delay;
 return txn.setAlarm(batch.nextRunAt);
}

function scheduleNext(txn, batch, delay) {
 const remaining = batch.goal === 'accepted' ? batch.deadlineAt - Date.now() : delay;
 return schedule(txn,batch,Math.max(1,Math.min(delay,remaining)));
}

export class McBatch extends DurableObject {
 async control(owner,data) {
  const storage = this.ctx.storage;
  return storage.transaction(async txn => {
   const batch = await txn.get('batch');
   if (batch && batch.owner !== owner) return {error:'batch_access_denied'};
   if (data.action === 'start') {
    if (batch?.id === data.id) return snapshot(batch);
    if (batch && !['complete','cancelled'].includes(batch.status)) return {error:'batch_already_active'};
    if (await txn.get('started:' + data.id)) return {error:'batch_already_submitted'};
    const items = prepare(data);
    if (!items) return {error:'invalid_batch'};
    const next = {id:data.id, owner, requested:data.count, status:'running',items};
    if (data.goal === 'accepted') {
     Object.assign(next,{goal:'accepted',attemptLimit:data.count * 2,deadlineAt:Date.now() + targetWindow,
                         initialJobCount:items.length});
    }
    await schedule(txn,next,1000);
    await txn.put({batch:next,['started:' + data.id]:true});
    return snapshot(next);
   }
   if (data.action === 'status') {
    // Existing paused batches had no alarm. The first authenticated status
    // read after upgrading upgrades the state and restores scheduling.
    if (batch?.status === 'paused') await this.resume(txn,batch);
    else if (['running','cancelling'].includes(batch?.status) && await txn.getAlarm() === null) {
     await schedule(txn,batch,Math.max(1000,(batch.nextRunAt || 0)-Date.now()));
     await txn.put('batch',batch);
    }
    return snapshot(batch);
   }
   if (!batch || batch.id !== data.id) return {error:'batch_changed'};
   if (data.action === 'cancel' && ['running','paused'].includes(batch.status)) {
    batch.status = batch.items.some(item => item.status === 'started') ? 'cancelling' : 'cancelled';
    if (batch.status === 'cancelled') {
     await txn.deleteAlarm();
     delete batch.nextRunAt;
    }
    delete batch.reason;
    await txn.put('batch',batch);
   } else if (data.action === 'resume' && batch.status === 'paused') {
    await this.resume(txn,batch);
   }
   return snapshot(batch);
  });
 }

 async resume(txn,batch) {
  batch.status = batch.goal === 'accepted' || batch.items.some(item => item.status === 'queued' || item.status === 'started')
   ? 'running' : 'complete';
  delete batch.reason;
  if (batch.status === 'running') await schedule(txn,batch,1000);
  await txn.put('batch',batch);
 }

 async alarm() {
  const storage = this.ctx.storage;
  const work = await storage.transaction(async txn => {
   const batch = await txn.get('batch');
   if (!batch || !['running','cancelling'].includes(batch.status)) return null;
   const started = batch.items.find(item => item.status === 'started');
   let slot = started;
   if (!slot && batch.status === 'running') {
    const stop = targetStop(batch);
    if (stop) {
     finish(batch,stop);
     await txn.put('batch',batch);
     return null;
    }
    slot = batch.items.find(item => item.status === 'queued');
    if (!slot && batch.goal === 'accepted') {
     // Reuse the grounded task, with a new identity and the full set of
     // previous drafts as duplicate checks. Rotate through all planned topics.
     const index = (batch.items.length - batch.initialJobCount) % batch.initialJobCount;
     slot = newSlot(batch.items[index].request);
     batch.items.push(slot);
    }
   }
   if (!slot) {
    if (batch.status === 'cancelling') batch.status = 'cancelled';
    else finish(batch);
    delete batch.nextRunAt;
    await txn.put('batch',batch);
    return null;
   }
   slot.status = 'started';
   slot.startedAt ??= Date.now();
   if (started) slot.recoveryChecks = (slot.recoveryChecks || 0) + 1;
   // Persist a watchdog before sending any request. On a crash the next
   // invocation is recovery-only and cannot issue another paid generation.
   await schedule(txn,batch,started ? recoveryInterval : recoveryDeadline);
   await txn.put('batch',batch);
   return {batch,slot,recover:!!started};
  });
  if (!work) return;
  let result;
  try {
   result = await executeSlot(this.env,work.batch,work.slot,work.recover);
  } catch {
   result = {status:'interrupted'};
  }
  await storage.transaction(async txn => {
   const batch = await txn.get('batch');
   if (batch?.id !== work.batch.id) return;
   const slot = batch.items.find(item => item.id === work.slot.id);
   if (slot?.status !== 'started') return;

   if (result.status === 'busy' && !work.recover) {
    // A trusted admission rejection happened before this slot was claimed.
    slot.status = 'queued';
    delete slot.startedAt;
    delete slot.recoveryChecks;
    delete slot.endedRequest;
    if (batch.status === 'cancelling') batch.status = 'cancelled';
    else {
     batch.reason = 'waiting_for_generator';
     await scheduleNext(txn,batch,5000);
    }
   } else if (['interrupted','checkpoint_missing','provider_failed'].includes(result.status)) {
    if (!work.recover && result.status === 'provider_failed') {
     slot.endedRequest = true;
     slot.providerRetryAfter = result.retryAfter;
    }
    if (result.attemptedAt !== undefined) slot.startedAt = Math.min(slot.startedAt,result.attemptedAt);
    // A dropped reply could still belong to a running attempt. Read its
    // checkpoint early, but leave the original recovery window intact.
    const expired = Date.now() - slot.startedAt >= recoveryDeadline;
    const exhausted = work.recover && (expired || (slot.endedRequest && slot.recoveryChecks >= 2));
    if (!exhausted) {
     batch.reason = 'recovering_current_attempt';
     await schedule(txn,batch,work.recover && !slot.endedRequest ? recoveryInterval : earlyRecovery);
     await txn.put('batch',batch);
     return;
    }
    const knownFailure = slot.endedRequest && result.status === 'checkpoint_missing';
    result = {status:knownFailure ? 'failed' : 'unknown',
              reason:slot.endedRequest ? 'generation_provider_unavailable' : 'completion_unverified',
              retryAfter:slot.providerRetryAfter};
   }
   if (result.status !== 'busy' || work.recover) {
    Object.assign(slot,{status:result.status,...(result.reason ? {reason:result.reason} : {}),
                         ...(result.draftId ? {draftId:result.draftId,accepted:result.accepted === true} : {})});
    delete batch.reason;
    const stop = targetStop(batch);
    if (batch.status === 'cancelling') batch.status = 'cancelled';
    else if (stop) finish(batch,stop);
    else if (batch.goal !== 'accepted' && !batch.items.some(item => item.status === 'queued')) finish(batch);
    if (batch.status === 'running') {
     const delay = continuationDelay(batch,result);
     if (delay > 1000) batch.reason = 'waiting_to_retry_provider';
     await scheduleNext(txn,batch,delay);
    }
   }
   if (batch.status !== 'running') {
    delete batch.nextRunAt;
    await txn.deleteAlarm();
   }
   await txn.put('batch',batch);
  });
 }
}
