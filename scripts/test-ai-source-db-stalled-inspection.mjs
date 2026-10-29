import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceDbAdapter} from './ai-source-db-adapter.mjs';

test('stalled inspection is read-only and uses a bounded threshold',async()=>{
 const calls=[];
 const db={query:async(sql,params)=>{calls.push({sql,params});return {rows:[{id:'doc-1',processing_status:'extracting'}]}}};
 const result=await createSourceDbAdapter(db).listStalledDocuments({olderThanMinutes:90});
 assert.equal(result.length,1);
 assert.match(calls[0].sql,/^select /);
 assert.match(calls[0].sql,/limit 100/);
 assert.deepEqual(calls[0].params,[90]);
});

test('stalled inspection rejects invalid thresholds before database access',async()=>{
 let called=false;
 const db={query:async()=>{called=true;return {rows:[]}}};
 for(const olderThanMinutes of [0,-1,1.5,10081,NaN]){
  await assert.rejects(createSourceDbAdapter(db).listStalledDocuments({olderThanMinutes}),/invalid stale-processing threshold/);
 }
 assert.equal(called,false);
});
