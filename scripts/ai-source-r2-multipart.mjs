// Trusted server-side multipart controller. Only call after validating a signed-in
// administrator and an active, owned upload intent in the database.
import {R2_SOURCE_BUCKET} from './ai-source-r2-storage.mjs';
import {MAX_TEXTBOOK_BYTES} from './ai-source-upload-constants.mjs';
import {R2_PART_BYTES} from './ai-source-r2-upload-config.mjs';
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ETAG=/^(?:[^"\r\n]{1,256}|"[^"\r\n]{1,256}")$/;
export function createR2MultipartController({client,commands,presign}){
 if(typeof client?.send!=='function'||typeof presign!=='function'||
    !['CreateMultipartUploadCommand','UploadPartCommand','CompleteMultipartUploadCommand','AbortMultipartUploadCommand','ListPartsCommand']
      .every(name=>typeof commands?.[name]==='function'))
  throw new TypeError('trusted R2 multipart dependencies required');
 const check=(intent)=>{
  if(!intent||!UUID.test(intent.id)||intent.storage_bucket!==R2_SOURCE_BUCKET||
     intent.storage_path!==`documents/${intent.id}.pdf`||
     !Number.isSafeInteger(Number(intent.file_bytes))||
     Number(intent.file_bytes)<8||Number(intent.file_bytes)>MAX_TEXTBOOK_BYTES||
     intent.status!=='uploading')throw new Error('invalid active R2 upload intent');
 };
 return {
  async initiate(intent){
   check(intent);
   const result=await client.send(new commands.CreateMultipartUploadCommand({
    Bucket:R2_SOURCE_BUCKET,Key:intent.storage_path,ContentType:'application/pdf'
   }));
   if(typeof result?.UploadId!=='string'||!result.UploadId)throw new Error('R2 multipart session unavailable');
   return {multipartId:result.UploadId,partBytes:R2_PART_BYTES};
  },
  async signPart(intent,{multipartId,partNumber}){
   check(intent);
   const count=Math.ceil(Number(intent.file_bytes)/R2_PART_BYTES);
   if(typeof multipartId!=='string'||!multipartId||multipartId.length>512||
      !Number.isInteger(partNumber)||partNumber<1||partNumber>count)
    throw new Error('invalid R2 multipart part');
   const url=await presign(client,new commands.UploadPartCommand({
    Bucket:R2_SOURCE_BUCKET,Key:intent.storage_path,UploadId:multipartId,PartNumber:partNumber
   }),{expiresIn:300});
   if(typeof url!=='string'||!url.startsWith('https://'))throw new Error('R2 part signature unavailable');
   return {url,partNumber,partBytes:R2_PART_BYTES};
  },
  async listParts(intent,{multipartId}){
   check(intent);
   if(typeof multipartId!=='string'||!multipartId||multipartId.length>512)
    throw new Error('invalid R2 multipart session');
   const count=Math.ceil(Number(intent.file_bytes)/R2_PART_BYTES);
   const parts=[];
   let marker;
   do{
    const result=await client.send(new commands.ListPartsCommand({
     Bucket:R2_SOURCE_BUCKET,Key:intent.storage_path,UploadId:multipartId,
     ...(marker?{PartNumberMarker:marker}:{})
    }));
    for(const part of result.Parts??[]){
     const number=part.PartNumber;
     const expected=number===count?Number(intent.file_bytes)-(count-1)*R2_PART_BYTES:R2_PART_BYTES;
     if(!Number.isInteger(number)||number<1||number>count||
        typeof part.ETag!=='string'||!ETAG.test(part.ETag)||
        Number(part.Size)!==expected)
      throw new Error('invalid R2 uploaded part metadata');
     parts.push({PartNumber:number,ETag:part.ETag});
    }
    if(!result.IsTruncated)break;
    const oldMarker=marker??0;
    marker=result.NextPartNumberMarker;
    if(!Number.isInteger(marker)||marker<=oldMarker||marker>count||parts.length>count)
     throw new Error('invalid R2 part pagination');
   }while(true);
   if(new Set(parts.map(part=>part.PartNumber)).size!==parts.length)
    throw new Error('duplicate R2 uploaded part');
   return {parts:parts.sort((a,b)=>a.PartNumber-b.PartNumber)};
  },
  async complete(intent,{multipartId,parts}){
   check(intent);
   const count=Math.ceil(Number(intent.file_bytes)/R2_PART_BYTES);
   if(typeof multipartId!=='string'||!multipartId||multipartId.length>512||
      !Array.isArray(parts)||parts.length!==count||
      parts.some((part,index)=>part?.PartNumber!==index+1||typeof part?.ETag!=='string'||!ETAG.test(part.ETag)))
    throw new Error('invalid R2 multipart completion');
   await client.send(new commands.CompleteMultipartUploadCommand({
    Bucket:R2_SOURCE_BUCKET,Key:intent.storage_path,UploadId:multipartId,
    MultipartUpload:{Parts:parts}
   }));
   return {completed:true};
  },
  async abort(intent,{multipartId}){
   check(intent);
   if(typeof multipartId!=='string'||!multipartId||multipartId.length>512)
    throw new Error('invalid R2 multipart session');
   await client.send(new commands.AbortMultipartUploadCommand({
    Bucket:R2_SOURCE_BUCKET,Key:intent.storage_path,UploadId:multipartId
   }));
   return {aborted:true};
  }
 };
}
