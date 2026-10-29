import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceServerWorkflow} from './ai-source-server-workflow.mjs';
test('browser supplied path is replaced with a server generated private key',async()=>{
 let uploadedPath,recordPath;
 const db={query:async(sql,args)=>{
  if(sql.startsWith('insert')){recordPath=args[3];return {rows:[{id:'book-1'}]}}
  return {rows:[]};
 }};
 const storage={upload:async(path)=>{uploadedPath=path;return {error:null}},remove:async()=>({error:null})};
 const workflow=createSourceServerWorkflow({
  db,supabase:{storage:{from:()=>storage}},authorizeAdmin:async()=>true,getDocument:()=>{}
 });
 const pdf=new Uint8Array([37,80,68,70,45,49,46,55,10]);
 await workflow.upload({actorId:'admin',title:'Equipment',bytes:pdf,storagePath:'outside.pdf'});
 assert.match(uploadedPath,/^documents\//);
 assert.equal(recordPath,uploadedPath);
 assert.notEqual(uploadedPath,'outside.pdf');
});
