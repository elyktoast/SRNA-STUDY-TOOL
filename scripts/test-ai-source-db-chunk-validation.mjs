import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceDbAdapter} from './ai-source-db-adapter.mjs';

const valid={documentId:'doc-1',chunkOrder:0,content:'A valid passage',contentHash:'abc'};

test('invalid batches never acquire a transaction or delete existing passages',async()=>{
 let connected=false;
 const db={query:async()=>({}),connect:async()=>{connected=true;throw new Error('should not connect')}};
 const adapter=createSourceDbAdapter(db);
 const invalid=[
  [{...valid,documentId:'another-document'}],
  [{...valid,chunkOrder:-1}],
  [valid,{...valid}],
  [{...valid,content:'  '}],
  [{...valid,contentHash:''}],
  [valid,{...valid,chunkOrder:1,content:''}]
 ];
 for(const chunks of invalid){
  await assert.rejects(adapter.saveChunks('doc-1',chunks),/source mismatch|invalid|duplicate/);
 }
 assert.equal(connected,false);
});
