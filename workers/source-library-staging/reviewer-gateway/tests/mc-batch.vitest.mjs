import {env} from 'cloudflare:workers';
import {evictDurableObject, runDurableObjectAlarm, runInDurableObject} from 'cloudflare:test';
import {expect, it} from 'vitest';

function fixture(count, topics) {
 const owner = crypto.randomUUID();
 const stub = env.MC_BATCH.getByName(owner);
 const id = crypto.randomUUID();
 const control = (action, fields={}) => stub.control(owner,{action,id,...fields});
 const start = () => control('start',{count,confirm:true,jobs:topics.map(topic => ({topic,format:'MC',textbook_id:'book'}))});
 return {owner,stub,start,control};
}

it('stores distinct IDs for 25, 50, and 100 attempts and isolates owners', async () => {
 for (const count of [25,50,100]) {
  const {stub,owner,start,control} = fixture(count,Array(count).fill('topic'));
  const {batch} = await start();
  expect(batch.items).toHaveLength(count);
  expect(new Set(batch.items.map(item => item.id)).size).toBe(count);
  expect((await start()).batch.items).toEqual(batch.items);
  await evictDurableObject(stub);
  expect((await control('status')).batch.items).toEqual(batch.items);
  expect(await env.MC_BATCH.getByName(crypto.randomUUID()).control(owner,{action:'status'})).toEqual({batch:null});
  await control('cancel');
  await runDurableObjectAlarm(stub);
  expect((await control('status')).batch.items.every(item => item.status === 'queued')).toBe(true);
 }
});

it('holds an incomplete review and automatically proceeds after provider cooldown', async () => {
 const {stub,start,control} = fixture(25,['first','second','provider outage','last']);
 await start();
 for (let index=0;index<3;index++) expect(await runDurableObjectAlarm(stub)).toBe(true);
 const {batch} = await control('status');
 expect(batch.status).toBe('running');
 expect(batch.reason).toBe('waiting_to_retry_provider');
 expect(batch.nextRunAt).toBeGreaterThan(Date.now());
 expect(batch.items.map(item => item.status)).toEqual(['ready','ready','held','queued']);
 await runDurableObjectAlarm(stub);
 expect((await control('status')).batch.status).toBe('complete');
});

it('after eviction reads completion for the same ID without another paid attempt', async () => {
 const {stub,start,control} = fixture(25,['disconnect']);
 const {batch:initial} = await start();
 await runDurableObjectAlarm(stub);
 expect((await control('status')).batch.items[0].status).toBe('started');
 await runInDurableObject(stub, async (_instance,state) => {
  expect((await state.storage.get('batch')).items[0].id).toBe(initial.items[0].id);
 });
 await evictDurableObject(stub);
 await runDurableObjectAlarm(stub);
 expect((await control('status')).batch.items[0]).toMatchObject({status:'ready',draftId:initial.items[0].id});
});

it('leaves ambiguous work recovery-only, then advances after its deadline', async () => {
 const {stub,start,control} = fixture(25,['unconfirmed','next']);
 await start();
 await runDurableObjectAlarm(stub);
 await runDurableObjectAlarm(stub);
 expect((await control('status')).batch.items[0].status).toBe('started');
 await runInDurableObject(stub, async (_instance,state) => {
  const batch = await state.storage.get('batch');
  batch.items[0].startedAt = Date.now() - 18 * 60_000;
  await state.storage.put('batch',batch);
 });
 await runDurableObjectAlarm(stub);
 const {batch} = await control('status');
 expect(batch.status).toBe('running');
 expect(batch.items.map(item => item.status)).toEqual(['unknown','queued']);
 await runDurableObjectAlarm(stub);
 expect((await control('status')).batch.status).toBe('complete');
});

it('uses the original attempt time when a persisted slot has no start timestamp', async () => {
 const {stub,start,control} = fixture(25,['legacy interruption','next']);
 await start();
 await runDurableObjectAlarm(stub);
 await runInDurableObject(stub, async (_instance,state) => {
  const batch = await state.storage.get('batch');
  delete batch.items[0].startedAt;
  await state.storage.put('batch',batch);
 });
 await runDurableObjectAlarm(stub);
 const {batch} = await control('status');
 expect(batch.items.map(item => item.status)).toEqual(['unknown','queued']);
 await runDurableObjectAlarm(stub);
 expect((await control('status')).batch.items.map(item => item.status)).toEqual(['unknown','ready']);
});

it('requeues an explicit busy refusal before payment without changing the slot ID', async () => {
 const {stub,start,control} = fixture(25,['busy once']);
 const {batch:original} = await start();
 await runDurableObjectAlarm(stub);
 const {batch} = await control('status');
 expect(batch.reason).toBe('waiting_for_generator');
 expect(batch.items[0]).toMatchObject({id:original.items[0].id,status:'queued'});
 await runDurableObjectAlarm(stub);
 expect((await control('status')).batch.items[0].status).toBe('ready');
});

it('bounds known provider failures and keeps processing without requiring manual resume', async () => {
 const {stub,start,control} = fixture(25,['explicit provider failure','next']);
 await start();
 for (let i=0;i<3;i++) await runDurableObjectAlarm(stub);
 const {batch} = await control('status');
 expect(batch.reason).toBe('waiting_to_retry_provider');
 expect(batch.nextRunAt - Date.now()).toBeGreaterThan(30_000);
 expect(batch.items[0]).toMatchObject({status:'failed',reason:'generation_provider_unavailable'});
 await runDurableObjectAlarm(stub);
 expect((await control('status')).batch.status).toBe('complete');
});

it('restores the alarm for a persisted legacy pause on the first status read', async () => {
 const {stub,start,control} = fixture(25,['next']);
 await start();
 await runInDurableObject(stub, async (_instance,state) => {
  const batch = await state.storage.get('batch');
  batch.status = 'paused';
  batch.reason = 'completion_unverified';
  await state.storage.put('batch',batch);
  await state.storage.deleteAlarm();
 });
 expect((await control('status')).batch.status).toBe('running');
 await runDurableObjectAlarm(stub);
 expect((await control('status')).batch.status).toBe('complete');
});

it('replaces held attempts and stops only after accepting the target', async () => {
 const {stub,control} = fixture(25,[]);
 const jobs = [...Array(24).fill('topic'), 'provider outage'].map(topic=>({topic,format:'MC',textbook_id:'book'}));
 const {batch:started} = await control('start',{count:25,confirm:true,goal:'accepted',jobs});
 expect(started).toMatchObject({acceptedCount:0,attemptLimit:50});
 for (let i=0;i<25;i++) await runDurableObjectAlarm(stub);
 const {batch:partial} = await control('status');
 expect(partial).toMatchObject({status:'running',acceptedCount:24});
 await evictDurableObject(stub);
 await runDurableObjectAlarm(stub);
 const {batch} = await control('status');
 expect(batch).toMatchObject({status:'complete',reason:'target_reached',acceptedCount:25});
 expect(batch.items).toHaveLength(26);
 expect(batch.items[25].id).not.toBe(started.items[0].id);
 expect(batch.items[25]).toMatchObject({accepted:true,topic:'topic'});
 expect(await runDurableObjectAlarm(stub)).toBe(false);
});

it('reports a shortfall at the attempt cap and cancels time-expired work before admission', async () => {
 const {stub,control} = fixture(25,[]);
 const jobs = [{topic:'provider outage',format:'MC',textbook_id:'book'}];
 await control('start',{count:25,confirm:true,goal:'accepted',jobs});
 for (let i=0;i<50;i++) await runDurableObjectAlarm(stub);
 const {batch:capped} = await control('status');
 expect(capped).toMatchObject({status:'complete',reason:'attempt_budget_exhausted',acceptedCount:0,attemptLimit:50});
 expect(capped.items).toHaveLength(50);
 expect(capped.items.every(item=>item.status==='held')).toBe(true);
 const id = crypto.randomUUID();
 await control('start',{id,count:25,confirm:true,goal:'accepted',jobs});
 await runInDurableObject(stub,async (_instance,state)=>{
  const batch = await state.storage.get('batch');
  batch.deadlineAt = Date.now()-1000;
  await state.storage.put('batch',batch);
 });
 await runDurableObjectAlarm(stub);
 const {batch:expired} = await control('status');
 expect(expired).toMatchObject({status:'complete',reason:'time_budget_exhausted',acceptedCount:0});
 expect(expired.items[0].status).toBe('queued');
});
