import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceApiRequest} from './ai-source-browser-request.mjs';

test('source API adapter uses a current bearer token for every upload request',async()=>{
 const calls=[];let token='first-token';
 const request=createSourceApiRequest({
  baseUrl:'https://source.example/',
  getAccessToken:async()=>token,
  fetchImpl:async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>({status:'uploading'})}}
 });
 assert.equal((await request('/source/uploads/start',{uploadId:'id'})).status,'uploading');
 token='refreshed-token';
 await request('/source/uploads/r2/create',{uploadId:'id'});
 assert.equal(calls[0].url,'https://source.example/source/uploads/start');
 assert.equal(calls[0].options.headers.authorization,'Bearer first-token');
 assert.equal(calls[1].options.headers.authorization,'Bearer refreshed-token');
 assert.equal(calls[0].options.credentials,'omit');
});
test('source API adapter rejects missing credentials and insecure URLs',async()=>{
 assert.throws(()=>createSourceApiRequest({baseUrl:'http://example.com',getAccessToken:async()=>''}),/HTTPS/);
 const request=createSourceApiRequest({getAccessToken:async()=>'',fetchImpl:async()=>{throw Error('must not fetch')}});
 await assert.rejects(request('/source/uploads/start',{uploadId:'id'}),/authentication required/);
});
test('source API adapter forwards sanitized API failures',async()=>{
 const request=createSourceApiRequest({getAccessToken:async()=> 'token',
  fetchImpl:async()=>({ok:false,json:async()=>({error:'upload not ready'})})});
 await assert.rejects(request('/source/uploads/verify',{uploadId:'id'}),/upload not ready/);
});
