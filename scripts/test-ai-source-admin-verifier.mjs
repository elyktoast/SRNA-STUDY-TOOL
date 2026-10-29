import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceAdminVerifier} from './ai-source-admin-verifier.mjs';
test('admin authorization uses a bound actor ID',async()=>{
 const authorize=createSourceAdminVerifier({query:async(sql,args)=>{
  assert.match(sql,/private\.snar_admins/);
  assert.deepEqual(args,['admin-1']);
  return {rows:[{allowed:true}]};
 }});
 assert.equal(await authorize('admin-1'),true);
});
test('missing and non-admin users are denied',async()=>{
 let queries=0;
 const authorize=createSourceAdminVerifier({query:async()=>{queries++;return {rows:[{allowed:false}]}}});
 assert.equal(await authorize(''),false);
 assert.equal(await authorize('student-1'),false);
 assert.equal(queries,1);
});
