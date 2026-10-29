import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceDbAdapter} from './ai-source-db-adapter.mjs';

test('chunk writes commit atomically and use parameters',async()=>{
 const calls=[];
 const client={query:async(sql,args)=>{calls.push({sql,args});if(sql.startsWith('select processing_status'))return {rows:[{processing_status:'indexing'}]};return {rowCount:1}},release:()=>calls.push({sql:'RELEASE'})};
 const adapter=createSourceDbAdapter({query:async()=>({rowCount:1}),connect:async()=>client});
 await adapter.saveChunks('book-1',[{documentId:'book-1',chunkOrder:0,content:'content',pageStart:2,pageEnd:2,printedPage:'xii',sectionHeading:'Airway',contentHash:'hash'}]);
 assert.deepEqual(calls.map(x=>x.sql==='RELEASE'?'RELEASE':x.sql.split(' ')[0]),['BEGIN','select','delete','insert','COMMIT','RELEASE']);
 assert.equal(calls[3].args[0],'book-1');
 assert.equal(calls[3].args[2],'content');
 assert.equal(calls[3].args[5],'xii');
 assert.equal(calls[3].args[6],'Airway');
});
test('failed insert rolls back and releases connection',async()=>{
 const calls=[];
 const client={query:async(sql)=>{calls.push(sql);if(sql.startsWith('select processing_status'))return {rows:[{processing_status:'indexing'}]};if(sql.startsWith('insert'))throw Error('write failure');return {rowCount:1}},release:()=>calls.push('RELEASE')};
 const adapter=createSourceDbAdapter({query:async()=>({rowCount:1}),connect:async()=>client});
 await assert.rejects(adapter.saveChunks('book-1',[{documentId:'book-1',chunkOrder:0,content:'text',contentHash:'hash'}]),/write failure/);
 assert.ok(calls.includes('ROLLBACK'));
 assert.ok(!calls.includes('COMMIT'));
 assert.ok(calls.includes('RELEASE'));
});
test('status update requires exactly one matching source',async()=>{
 const adapter=createSourceDbAdapter({query:async()=>({rowCount:0})});
 await assert.rejects(adapter.setStatus('missing','ready'),/invalid source processing transition/);
 await assert.rejects(adapter.setStatus('missing','published'),/invalid processing status/);
});
test('transaction support is mandatory',async()=>{
 const adapter=createSourceDbAdapter({query:async()=>({rowCount:1})});
 await assert.rejects(adapter.saveChunks('book-1',[{documentId:'book-1',chunkOrder:0,content:'text',contentHash:'hash'}]),/transaction-capable/);
});
