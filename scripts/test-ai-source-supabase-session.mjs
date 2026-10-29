import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceSupabaseSessionVerifier} from './ai-source-supabase-session.mjs';
test('validated bearer token resolves user ID',async()=>{
 const verify=createSourceSupabaseSessionVerifier({auth:{getUser:async token=>{
  assert.equal(token,'valid-token');
  return {data:{user:{id:'user-1'}},error:null};
 }}});
 assert.equal(await verify({headers:{authorization:'Bearer valid-token'}}),'user-1');
});
test('missing or invalid tokens fail closed',async()=>{
 let called=false;
 const verify=createSourceSupabaseSessionVerifier({auth:{getUser:async()=>{called=true;return {data:{user:null},error:{message:'invalid'}}}}});
 assert.equal(await verify({headers:{authorization:'Basic wrong'}}),null);
 assert.equal(called,false);
 assert.equal(await verify({headers:{authorization:'Bearer invalid'}}),null);
});
