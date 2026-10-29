import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceDbAdapter} from './ai-source-db-adapter.mjs';

function harness(status){
 const calls=[];
 const client={query:async(sql)=>{
  calls.push(sql);
  if(sql.includes('for update')) return {rows:status===null?[]:[{processing_status:status}]};
  return {rowCount:1,rows:[]};
 },release:()=>calls.push('RELEASE')};
 return {calls,db:{query:async()=>({}),connect:async()=>client}};
}
const chunk={documentId:'doc-1',chunkOrder:0,content:'sample',pageStart:1,pageEnd:1,contentHash:'abc'};

test('chunk replacement locks document and commits when indexing',async()=>{
 const {calls,db}=harness('indexing');
 await createSourceDbAdapter(db).saveChunks('doc-1',[chunk]);
 assert.deepEqual(calls.slice(0,2),['BEGIN','select processing_status from private.ai_source_documents where id=$1 for update']);
 assert.ok(calls.some(sql=>sql.startsWith('delete from private.ai_source_chunks')));
 assert.ok(calls.includes('COMMIT'));
 assert.equal(calls.at(-1),'RELEASE');
});

test('chunk replacement rejects non-indexing documents without deleting passages',async()=>{
 for(const status of ['ready','extracting','failed',null]){
  const {calls,db}=harness(status);
  await assert.rejects(createSourceDbAdapter(db).saveChunks('doc-1',[chunk]),/not in indexing state/);
  assert.ok(calls.includes('ROLLBACK'));
  assert.ok(!calls.some(sql=>sql.startsWith('delete from private.ai_source_chunks')));
  assert.ok(!calls.includes('COMMIT'));
 }
});
