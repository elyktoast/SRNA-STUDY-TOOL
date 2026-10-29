import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceDocumentLookup} from './ai-source-document-lookup.mjs';
test('retrieves storage metadata by bound document ID',async()=>{
 const lookup=createSourceDocumentLookup({query:async(sql,args)=>{
  assert.match(sql,/where id=\$1/);
  assert.deepEqual(args,['book-1']);
  return {rows:[{id:'book-1',storage_path:'admin/book.pdf'}]};
 }});
 assert.equal((await lookup('book-1')).storage_path,'admin/book.pdf');
});
test('missing record returns null',async()=>{
 const lookup=createSourceDocumentLookup({query:async()=>({rows:[]})});
 assert.equal(await lookup('missing'),null);
});
test('rejects missing document ID',async()=>{
 const lookup=createSourceDocumentLookup({query:async()=>({rows:[]})});
 await assert.rejects(lookup(''),/document ID/);
});
