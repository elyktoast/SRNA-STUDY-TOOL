// Private R2 textbook storage. Inject an S3-compatible client configured for Cloudflare R2.
// The adapter never returns public URLs or object bytes to the browser.
import {TUS_CHUNK_BYTES} from './ai-source-upload-constants.mjs';

export const R2_SOURCE_BUCKET='srna-private-textbooks';
const PATH=/^documents\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.pdf$/i;
function check(bucket,path){
 if(bucket!==R2_SOURCE_BUCKET||typeof path!=='string'||!PATH.test(path))
  throw new Error('invalid private R2 textbook path');
}
export function createR2SourceStorageAdapter({client,commands}){
 if(!client||typeof client.send!=='function'||!commands?.HeadObjectCommand||!commands?.GetObjectCommand)
  throw new TypeError('trusted R2 S3 client and command constructors required');
 return {
  async inspectObject({bucket,path}){
   check(bucket,path);
   const result=await client.send(new commands.HeadObjectCommand({Bucket:bucket,Key:path}));
   const size=Number(result?.ContentLength);
   if(!Number.isSafeInteger(size)||size<8)throw new Error('invalid R2 object size');
   return {size};
  },
  async *readObject({bucket,path}){
   check(bucket,path);
   const result=await client.send(new commands.GetObjectCommand({Bucket:bucket,Key:path}));
   if(!result?.Body||typeof result.Body[Symbol.asyncIterator]!=='function')
    throw new Error('private R2 stream unavailable');
   for await(const chunk of result.Body){
    if(!(chunk instanceof Uint8Array)||!chunk.length)throw new Error('invalid R2 stream');
    for(let offset=0;offset<chunk.length;offset+=TUS_CHUNK_BYTES)
     yield chunk.subarray(offset,offset+TUS_CHUNK_BYTES);
   }
  }
 };
}
