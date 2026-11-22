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
