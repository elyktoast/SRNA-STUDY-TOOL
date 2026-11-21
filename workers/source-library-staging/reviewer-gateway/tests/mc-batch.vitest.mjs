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

it('serializes slots, holds an incomplete review, and resumes only unstarted slots', async () => {
 const {stub,start,control} = fixture(25,['first','second','provider outage','last']);
 await start();
 for (let index=0;index<3;index++) expect(await runDurableObjectAlarm(stub)).toBe(true);
 const {batch} = await control('status');
 expect(batch.status).toBe('paused');
 expect(batch.items.map(item => item.status)).toEqual(['ready','ready','held','queued']);
 expect(await runDurableObjectAlarm(stub)).toBe(false);
 await control('resume');
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

it('bounds completed-only reads and leaves the next item queued when completion is unknown', async () => {
 const {stub,start,control} = fixture(25,['unconfirmed','next']);
 await start();
 for (let index=0;index<4;index++) expect(await runDurableObjectAlarm(stub)).toBe(true);
 const {batch} = await control('status');
 expect(batch.status).toBe('paused');
 expect(batch.items.map(item => item.status)).toEqual(['unknown','queued']);
 expect(await runDurableObjectAlarm(stub)).toBe(false);
});
