import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceDocumentRecord} from './ai-source-document-record.mjs';
test('creates a private textbook record with parameterized values',async()=>{
 let args;
 const create=createSourceDocumentRecord({query:async(sql,params)=>{assert.match(sql,/private.ai_source_documents/);args=params;return {rows:[{id:'book-1',processing_status:'uploaded'}]}}});
 const result=await create({title:'Anesthesia Equipment',storagePath:'admin/book.pdf',sha256:'a'.repeat(64),mimeType:'application/pdf',fileBytes:100});
 assert.equal(result.id,'book-1');
 assert.equal(args[2],'ai-textbook-sources');
 assert.equal(args[4],'a'.repeat(64));
});
test('rejects invalid checksum before database access',async()=>{
 const create=createSourceDocumentRecord({query:async()=>{throw Error('should not query')}});
 await assert.rejects(create({storagePath:'book.pdf',sha256:'bad'}),/checksum/);
});
