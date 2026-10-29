// Browser-side R2 multipart transfer. The authenticated request adapter must
// enforce CSRF/session protections. No R2 credentials enter browser code.
import {R2_PART_BYTES,R2_UPLOAD_CONCURRENCY} from './ai-source-r2-upload-config.mjs';
export async function uploadPdfToR2({file,uploadId,request,fetchPart=fetch,progress=()=>{},signal,concurrency=R2_UPLOAD_CONCURRENCY}){
 if(!file||!Number.isSafeInteger(file.size)||file.size<8||file.type!=='application/pdf')throw new Error('invalid PDF');
 if(typeof request!=='function'||typeof fetchPart!=='function'||typeof progress!=='function')throw new TypeError('upload adapters required');
 if(!Number.isInteger(concurrency)||concurrency<1||concurrency>3)throw new Error('invalid concurrency');
 if(signal?.aborted)throw new Error('upload canceled');
 const started=await request('/source/uploads/r2/create',{uploadId});
 if(typeof started?.multipartId!=='string'||!started.multipartId||started.partBytes!==R2_PART_BYTES)throw new Error('invalid R2 upload session');
 const total=Math.ceil(file.size/R2_PART_BYTES),parts=new Array(total);
 const recovered=await request('/source/uploads/r2/parts',{uploadId,multipartId:started.multipartId});
 if(!Array.isArray(recovered?.parts))throw new Error('R2 part recovery unavailable');
 let done=0;
 for(const part of recovered.parts){
  const index=part.PartNumber-1;
  if(!Number.isInteger(index)||index<0||index>=total||parts[index]||
     typeof part.ETag!=='string'||part.ETag.length>258)
   throw new Error('invalid recovered R2 part');
  parts[index]={PartNumber:part.PartNumber,ETag:part.ETag};
  done+=Math.min(R2_PART_BYTES,file.size-index*R2_PART_BYTES);
 }
 progress({bytesUploaded:done,bytesTotal:file.size});
 let next=0,failure;
 const worker=async()=>{
  while(next<total&&!failure){
   if(signal?.aborted)throw new Error('upload canceled');
   const index=next++,partNumber=index+1;
   if(parts[index])continue;
   const start=index*R2_PART_BYTES,end=Math.min(start+R2_PART_BYTES,file.size);
   let response;
   for(let attempt=0;attempt<3;attempt++){
    if(signal?.aborted)throw new Error('upload canceled');
    // Refresh the signature for each retry: a previous URL may have expired.
    const signed=await request('/source/uploads/r2/sign',{uploadId,multipartId:started.multipartId,partNumber});
    if(typeof signed?.url!=='string'||!signed.url.startsWith('https://'))throw new Error('invalid R2 signed part');
    try{
     response=await fetchPart(signed.url,{method:'PUT',body:file.slice(start,end),signal});
     if(response.ok)break;
    }catch(error){if(attempt===2)throw error}
   }
   if(!response?.ok)throw new Error('R2 part upload failed');
   const etag=response.headers?.get?.('etag');
   if(typeof etag!=='string'||!/^"?[^"\r\n]{1,256}"?$/.test(etag))throw new Error('R2 part ETag unavailable');
   parts[index]={PartNumber:partNumber,ETag:etag};
   done+=end-start;
   progress({bytesUploaded:done,bytesTotal:file.size});
  }
 };
 try{
  await Promise.all(Array.from({length:Math.min(concurrency,total)},async()=>{try{await worker()}catch(error){failure??=error}}));
  if(failure)throw failure;
  if(signal?.aborted)throw new Error('upload canceled');
  const completed=await request('/source/uploads/r2/complete',{uploadId,multipartId:started.multipartId,parts});
  if(completed?.completed!==true)throw new Error('R2 completion unavailable');
  return {uploadId,bytes:file.size};
 }catch(error){
  if(signal?.aborted){try{await request('/source/uploads/r2/abort',{uploadId,multipartId:started.multipartId})}catch{}}
  throw error;
 }
}
