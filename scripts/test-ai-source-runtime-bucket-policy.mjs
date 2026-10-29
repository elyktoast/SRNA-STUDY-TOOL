import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createR2SourceStorageAdapter,R2_SOURCE_BUCKET} from './ai-source-r2-storage.mjs';
const validPath='documents/123e4567-e89b-42d3-a456-426614174000.pdf';
class HeadObjectCommand{constructor(input){this.input=input}}
class GetObjectCommand{constructor(input){this.input=input}}
function setup(result={ContentLength:8}){
 const calls=[];
 const client={send:async command=>{calls.push(command);return result}};
 return {adapter:createR2SourceStorageAdapter({client,commands:{HeadObjectCommand,GetObjectCommand}}),calls};
}
test('accepts a private PDF object in the designated R2 bucket',async()=>{
 const {adapter,calls}=setup();assert.deepEqual(await adapter.inspectObject({bucket:R2_SOURCE_BUCKET,path:validPath}),{size:8});
 assert.equal(calls[0].input.Bucket,R2_SOURCE_BUCKET);
 assert.equal(calls[0].input.Key,validPath);
});
test('rejects a different R2 bucket',async()=>{
 const {adapter,calls}=setup();await assert.rejects(adapter.inspectObject({bucket:'public-textbooks',path:validPath}),/invalid private R2 textbook path/);assert.equal(calls.length,0);
});
test('rejects a path outside the private PDF namespace',async()=>{
 const {adapter,calls}=setup();await assert.rejects(adapter.inspectObject({bucket:R2_SOURCE_BUCKET,path:'public/file.pdf'}),/invalid private R2 textbook path/);assert.equal(calls.length,0);
});
test('rejects malformed object size metadata',async()=>{
 const {adapter}=setup({ContentLength:'invalid'});await assert.rejects(adapter.inspectObject({bucket:R2_SOURCE_BUCKET,path:validPath}),/invalid R2 object size/);
});
test('rejects missing private object stream',async()=>{
 const {adapter}=setup({});await assert.rejects(async()=>{for await(const chunk of adapter.readObject({bucket:R2_SOURCE_BUCKET,path:validPath})){}},/private R2 stream unavailable/);
});
