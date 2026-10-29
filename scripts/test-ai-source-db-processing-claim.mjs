import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceDbAdapter} from './ai-source-db-adapter.mjs';

test('processing claim is conditional and rejects concurrent work',async()=>{
 const calls=[];
 const db={query:async(sql,params)=>{calls.push({sql,params});return {rowCount:0}}};
 const adapter=createSourceDbAdapter(db);
 await assert.rejects(adapter.setStatus('doc-1','extracting'),/already active/);
 assert.match(calls[0].sql,/processing_status=any\(\$3::text\[\]\)/);
 assert.deepEqual(calls[0].params,['doc-1','extracting',['uploaded','ready','failed']]);
});

test('processing claim accepts an available document',async()=>{
 const db={query:async()=>({rowCount:1})};
 await assert.doesNotReject(createSourceDbAdapter(db).setStatus('doc-1','extracting'));
});

test('processing state transitions only accept their expected predecessor',async()=>{
 const calls=[];
 const db={query:async(sql,params)=>{calls.push(params);return {rowCount:1}}};
 const adapter=createSourceDbAdapter(db);
 for(const status of ['indexing','ready','failed']) await adapter.setStatus('doc-1',status);
 assert.deepEqual(calls.map(x=>x[2]),[['extracting'],['indexing'],['extracting','indexing']]);
});
