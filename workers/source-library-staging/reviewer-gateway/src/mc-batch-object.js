import {DurableObject} from 'cloudflare:workers';
import {executeSlot, prepare, snapshot} from './mc-batch.js';

const recoveryDelay = 15 * 60_000;
export class McBatch extends DurableObject {
 async control(owner,data) {
  const storage = this.ctx.storage;
  const batch = await storage.get('batch');
  if (data.action === 'status') return snapshot(batch);
  if (data.action === 'start') {
   if (batch?.id === data.id) return snapshot(batch);
   if (batch && !['complete','cancelled'].includes(batch.status)) return {error:'batch_already_active'};
   if (await storage.get('started:' + data.id)) return {error:'batch_already_submitted'};
   const items = prepare(data);
   if (!items) return {error:'invalid_batch'};
   const next = {id:data.id, owner, requested:data.count, status:'running',items};
   await storage.transaction(async txn => {
    const current = await txn.get('batch');
    if (await txn.get('started:' + data.id)) throw Error('batch_already_submitted');
    if (current?.id !== batch?.id || (current && !['complete','cancelled'].includes(current.status))) throw Error('batch_changed');
    await txn.put({batch:next,['started:' + data.id]:true});
    await txn.setAlarm(Date.now()+1000);
   });
   return snapshot(next);
  }
  if (!batch || batch.id !== data.id) return {error:'batch_changed'};
  return storage.transaction(async txn => {
   const current = await txn.get('batch');
   if (current.id !== data.id) return {error:'batch_changed'};
   if (data.action === 'cancel' && ['running','paused'].includes(current.status)) {
    current.status = current.items.some(item => item.status === 'started') ? 'cancelling' : 'cancelled';
   } else if (data.action === 'resume' && current.status === 'paused') {
    current.status = current.items.some(item => item.status === 'queued') ? 'running' : 'complete';
    delete current.reason;
    if (current.status === 'running') await txn.setAlarm(Date.now()+1000);
   }
   await txn.put('batch',current);
   return snapshot(current);
  });
 }

 async alarm() {
  const storage = this.ctx.storage;
  const work = await storage.transaction(async txn => {
   const batch = await txn.get('batch');
   if (!batch || !['running','cancelling'].includes(batch.status)) return null;
   const started = batch.items.find(item => item.status === 'started');
   const slot = started || (batch.status === 'running' && batch.items.find(item => item.status === 'queued'));
   if (!slot) return null;
   slot.status = 'started';
   await txn.put('batch',batch);
   await txn.setAlarm(Date.now()+recoveryDelay);
   return {batch,slot,recover:!!started};
  });
  if (!work) return;
  let result;
  try {
   result = await executeSlot(this.env,work.batch,work.slot,work.recover);
  } catch {
   if (!work.recover) return; // The scheduled alarm reads the completed checkpoint only.
   result = {status:'unknown',reason:'completion_unverified'};
  }
  await storage.transaction(async txn => {
   const batch = await txn.get('batch');
   if (batch.id !== work.batch.id) return;
   const slot = batch.items.find(item => item.id === work.slot.id);
   Object.assign(slot,result);
   if (batch.status === 'cancelling') batch.status = 'cancelled';
   else if (result.reason && result.reason !== 'generation_rejected') {
    batch.status = 'paused';
    batch.reason = result.reason;
   } else if (!batch.items.some(item => item.status === 'queued')) batch.status = 'complete';
   await txn.put('batch',batch);
   if (batch.status === 'running') await txn.setAlarm(Date.now()+1000);
   else await txn.deleteAlarm();
  });
 }
}
