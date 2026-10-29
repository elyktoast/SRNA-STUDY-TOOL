// Trusted Node-only adapter. Never expose service-role credentials to browsers.
import {TUS_CHUNK_BYTES} from './ai-source-upload-constants.mjs';

export function createSourceUploadStorageStream({supabase,storageOrigin,fetchImpl=fetch}){
 if(typeof supabase?.storage?.from!=='function'||typeof fetchImpl!=='function')
  throw new TypeError('trusted Storage client and fetch required');
 const origin=new URL(storageOrigin);
 if(origin.protocol!=='https:'||origin.username||origin.password||origin.pathname!=='/'||origin.search||origin.hash)
  throw new TypeError('HTTPS Storage origin required');
 const validate=({bucket,path})=>{
  if(bucket!=='ai-textbook-sources'||typeof path!=='string'||
     !/^documents\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.pdf$/i.test(path))
   throw new Error('invalid private textbook object path');
 };
 // Download via an authenticated, short-lived signed URL generated server-side.
 // Never send this URL to the client or log it.
 const open=async({bucket,path})=>{
  validate({bucket,path});
  const {data,error}=await supabase.storage.from(bucket).createSignedUrl(path,60);
  if(error||typeof data?.signedUrl!=='string')throw new Error('private source URL unavailable');
  const signed=new URL(data.signedUrl);
  if(signed.protocol!=='https:'||signed.origin!==origin.origin||
     !signed.pathname.startsWith('/storage/v1/object/sign/ai-textbook-sources/'))
   throw new Error('untrusted private source URL');
  const response=await fetchImpl(signed.href,{redirect:'error',headers:{'accept-encoding':'identity'}});
  if(!response.ok||!response.body)throw new Error('private source stream unavailable');
  return response;
 };
 return {
  async inspectObject({bucket,path}){
   validate({bucket,path});
   const {data,error}=await supabase.storage.from(bucket).info(path);
   if(error||!data)throw new Error('private source metadata unavailable');
   return {size:data.size};
  },
  async *readObject({bucket,path}){
   const response=await open({bucket,path});
   const reader=response.body.getReader();
   try{
    while(true){
     const {done,value}=await reader.read();
     if(done)break;
     if(!(value instanceof Uint8Array)||!value.length)throw new Error('invalid private stream');
     for(let offset=0;offset<value.length;offset+=TUS_CHUNK_BYTES)
      yield value.subarray(offset,offset+TUS_CHUNK_BYTES);
    }
   }finally{await reader.cancel().catch(()=>{})}
  }
 };
}
