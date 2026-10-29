import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceUploadRoutes} from './ai-source-upload-routes.mjs';
const id='01234567-89ab-4def-8abc-0123456789ab';
const make=(authorizeAdmin=async()=>true)=>createSourceUploadRoutes({
 authorizeAdmin,createIntent:async()=>{},markUploading:async()=>true,verifyAdapters:{}});
test('unknown route returns 404',async()=>{
 const result=await make()({path:'/source/uploads/unknown',actorId:'admin',body:{}});
 assert.equal(result.status,404);
});
test('missing session returns 401',async()=>{
 const result=await make()({path:'/source/uploads/initiate',body:{}});
 assert.equal(result.status,401);
});
test('non-admin returns 403',async()=>{
 const result=await make(async()=>false)({path:'/source/uploads/initiate',actorId:'user',body:{}});
 assert.equal(result.status,403);
});
test('admin can create upload intent',async()=>{
 const result=await make()({path:'/source/uploads/initiate',actorId:'admin',body:{title:'Book',fileBytes:330000000,mimeType:'application/pdf'}});
 assert.equal(result.status,201);
 assert.equal(result.body.upload.fileBytes,330000000);
});
test('start rejects malformed upload IDs',async()=>{
 const result=await make()({path:'/source/uploads/start',actorId:'admin',body:{uploadId:'bad'}});
 assert.equal(result.status,400);
});
test('start marks valid upload session',async()=>{
 const result=await make()({path:'/source/uploads/start',actorId:'admin',body:{uploadId:id}});
 assert.equal(result.status,200);
});
