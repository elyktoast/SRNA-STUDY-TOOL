import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceRuntime} from './ai-source-runtime.mjs';
test('runtime denies non-admin even with valid Supabase session',async()=>{
 let storageCalled=false;
 const db={
  query:async()=>({rows:[{allowed:false}]}),
  connect:async()=>{throw Error('should not open transaction')}
 };
 const storage={storage:{from:()=>({
  upload:async()=>{storageCalled=true;return {error:null}},
  download:async()=>{storageCalled=true;return {error:null}},
  remove:async()=>{storageCalled=true;return {error:null}}
 })}};
 const auth={auth:{getUser:async token=>({data:{user:{id:'student'}},error:null})}};
 const server=createSourceRuntime({db,supabaseStorage:storage,supabaseAuth:auth,getDocument:()=>{}});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const response=await fetch('http://127.0.0.1:'+server.address().port+'/source/upload',{
   method:'POST',headers:{authorization:'Bearer valid','x-source-title':'Book','content-type':'application/pdf'},
   body:new Uint8Array([37,80,68,70,45,49,46,55])
  });
  assert.equal(response.status,403);
  assert.equal(storageCalled,false);
 }finally{await new Promise(resolve=>server.close(resolve))}
});
