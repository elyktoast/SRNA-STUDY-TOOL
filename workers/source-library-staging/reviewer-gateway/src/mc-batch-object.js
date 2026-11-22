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

function settleSlot(slot,result,recover) {
 if (result.status === 'busy' && !recover) {
  slot.status = 'queued';
  delete slot.startedAt;
  delete slot.recoveryChecks;
  delete slot.endedRequest;
  return {waiting:true,delay:5000};
 }
 if (['interrupted','checkpoint_missing','provider_failed'].includes(result.status)) {
  if (!recover && result.status === 'provider_failed') {
   slot.endedRequest = true;
   slot.providerRetryAfter = result.retryAfter;
  }
  if (result.attemptedAt !== undefined) slot.startedAt = Math.min(slot.startedAt,result.attemptedAt);
  const expired = Date.now() - slot.startedAt >= recoveryDeadline;
  if (!recover || (!expired && !(slot.endedRequest && slot.recoveryChecks >= 2))) {
   return {recovery:true,delay:recover && !slot.endedRequest ? recoveryInterval : earlyRecovery};
  }
  const knownFailure = slot.endedRequest && result.status === 'checkpoint_missing';
  result = {status:knownFailure ? 'failed' : 'unknown',
            reason:slot.endedRequest ? 'generation_provider_unavailable' : 'completion_unverified',
            retryAfter:slot.providerRetryAfter};
 }
 Object.assign(slot,{status:result.status,...(result.reason ? {reason:result.reason} : {}),
                      ...(result.draftId ? {draftId:result.draftId,accepted:result.accepted === true} : {})});
 return result;
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
   let slots = batch.items.filter(item => item.status === 'started');
   const recover = slots.length > 0;
   if (!recover && batch.status === 'running') {
    const stop = targetStop(batch);
    if (stop) {
     finish(batch,stop);
     await txn.put('batch',batch);
     return null;
    }
    const width = batch.goal === 'accepted' ? Math.min(2,batch.requested-acceptedCount(batch)) : 1;
    slots = batch.items.filter(item => item.status === 'queued').slice(0,width);
    // Fill available lanes without exceeding the confirmed attempt budget.
    while (batch.goal === 'accepted' && slots.length < width && batch.items.length < batch.attemptLimit) {
     const index = (batch.items.length - batch.initialJobCount) % batch.initialJobCount;
     const slot = newSlot(batch.items[index].request);
     batch.items.push(slot);
     slots.push(slot);
    }
   }
   if (!slots.length) {
    if (batch.status === 'cancelling') batch.status = 'cancelled';
    else finish(batch);
    delete batch.nextRunAt;
    await txn.put('batch',batch);
    return null;
   }
   for (const slot of slots) {
    slot.status = 'started';
    slot.startedAt ??= Date.now();
    if (recover) slot.recoveryChecks = (slot.recoveryChecks || 0) + 1;
   }
   // Durable before sending paid requests. An interrupted wave is recovered
   // by its original checkpoint IDs and never replayed.
   await schedule(txn,batch,recover ? recoveryInterval : recoveryDeadline);
   await txn.put('batch',batch);
   return {batch,slots,recover};
  });
  if (!work) return;
  const outcomes = await Promise.all(work.slots.map(async slot => {
   try { return await executeSlot(this.env,work.batch,slot,work.recover); }
   catch { return {status:'interrupted'}; }
  }));
  await storage.transaction(async txn => {
   const batch = await txn.get('batch');
   if (batch?.id !== work.batch.id) return;
   const recoveries = [], continuations = [];
   for(const [index,original] of work.slots.entries()){
    const slot=batch.items.find(item=>item.id===original.id);
    if(slot?.status!=='started')continue;
    const next=settleSlot(slot,outcomes[index],work.recover);
    if(next.recovery) recoveries.push(next.delay);
    else continuations.push(next);
   }
   delete batch.reason;
   for(const next of continuations){
    if(next.retryAfter)batch.providerReadyAt=Math.max(batch.providerReadyAt||0,Date.now()+next.retryAfter*1000);
   }
   if (recoveries.length) {
    batch.reason = 'recovering_current_attempt';
    await schedule(txn,batch,Math.min(...recoveries));
   } else {
    const stop = targetStop(batch);
    if (batch.status === 'cancelling') batch.status = 'cancelled';
    else if (stop) finish(batch,stop);
    else if (batch.goal !== 'accepted' && !batch.items.some(item => item.status === 'queued')) finish(batch);
    if (batch.status === 'running') {
     // Treat consecutive provider cooldowns by wave, and never let a
     // successful sibling cancel another request's Retry-After.
     const provider = continuations.filter(x=>x.reason==='generation_provider_unavailable'||x.reason==='review_provider_unavailable');
     let delay = provider.length
      ? continuationDelay(batch,{reason:provider[0].reason,retryAfter:Math.max(...provider.map(x=>x.retryAfter||0))})
      : continuationDelay(batch,{});
     delay = Math.max(delay,(batch.providerReadyAt||0)-Date.now());
     for (const next of continuations) delay = Math.max(delay,next.delay||0,next.reason==='batch_access_denied'?accessRetry:0);
     if (delay > 1000) batch.reason = continuations.some(x=>x.waiting) && delay===5000
      ? 'waiting_for_generator' : 'waiting_to_retry_provider';
     await scheduleNext(txn,batch,delay);
    }
   }
   if (batch.status !== 'running' && !recoveries.length) {
    delete batch.nextRunAt;
    await txn.deleteAlarm();
   }
   await txn.put('batch',batch);
  });
 }
}
