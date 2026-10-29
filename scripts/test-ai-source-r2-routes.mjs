import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createR2UploadRoutes} from './ai-source-r2-routes.mjs';
const actorId='11111111-1111-4111-8111-111111111111';
const uploadId='22222222-2222-4222-8222-222222222222';
const intent={id:uploadId,storage_bucket:'srna-private-textbooks',storage_path:`documents/${uploadId}.pdf`,status:'uploading',file_bytes:25165824};
function fixture(){
 let multipartId='session-one',completed=false,cleared=0,aborted=0;
 const controller={
  initiate:async()=>({multipartId:'session-new',partBytes:12582912}),
  signPart:async()=>({url:'https://example.com/part',partNumber:1,partBytes:12582912}),
  complete:async()=>({completed:true}),
  abort:async()=>{aborted++;return {aborted:true}}
 };
 const routes=createR2UploadRoutes({
  authorizeAdmin:async()=>true,getOwnedIntent:async()=>intent,controller,
  getSession:async()=>({multipart_id:multipartId,r2_completed_at:completed?new Date():null}),
  saveSession:async({multipartId:id})=>{multipartId=id;return true},
  markComplete:async()=>{completed=true;return true},
  clearSession:async()=>{multipartId=null;cleared++;return true}
 });
 return {routes,counts:()=>({cleared,aborted})};
}
test('aborting owned R2 upload clears session and permits a new one',async()=>{
 const f=fixture();
 const abort=await f.routes({path:'/source/uploads/r2/abort',actorId,body:{uploadId,multipartId:'session-one'}});
 assert.equal(abort.status,200);
 assert.deepEqual(f.counts(),{cleared:1,aborted:1});
 const restarted=await f.routes({path:'/source/uploads/r2/create',actorId,body:{uploadId}});
 assert.equal(restarted.status,200);
 assert.equal(restarted.body.multipartId,'session-new');
});
test('rejects multipart IDs not bound to the owned intent',async()=>{
 const f=fixture();
 const result=await f.routes({path:'/source/uploads/r2/abort',actorId,body:{uploadId,multipartId:'other-session'}});
 assert.equal(result.status,409);
 assert.deepEqual(f.counts(),{cleared:0,aborted:0});
});
test('rejects untrusted actor before any R2 operation',async()=>{
 const f=fixture();
 const result=await f.routes({path:'/source/uploads/r2/create',actorId:'not-a-uuid',body:{uploadId}});
 assert.equal(result.status,401);
});
