import {createHash} from 'node:crypto';
import {MAX_TEXTBOOK_BYTES,TUS_CHUNK_BYTES} from './ai-source-upload-constants.mjs';

// Server-only finalization. Caller must resolve actor from verified session.
// A TUS success notification alone is not proof of an intact textbook.
export async function verifyCompletedTextbook({
 actorId,uploadId,authorizeAdmin,claimVerification,inspectObject,
 readObject,completeVerifiedIntent,failVerification
}){
 if(typeof authorizeAdmin!=='function'||typeof claimVerification!=='function'||
    typeof inspectObject!=='function'||typeof readObject!=='function'||
    typeof completeVerifiedIntent!=='function'||typeof failVerification!=='function')
  throw new TypeError('trusted upload verification adapters required');
 if(typeof actorId!=='string'||!actorId.trim()||await authorizeAdmin(actorId)!==true)
  throw new Error('source upload access denied');
 if(typeof uploadId!=='string'||!/^[0-9a-f-]{36}$/i.test(uploadId))
  throw new Error('invalid upload ID');
 const intent=await claimVerification({uploadId,actorId});
 if(!intent) throw new Error('upload unavailable for verification');
 try{
  if(intent.storage_bucket!=='srna-private-textbooks'||
     intent.storage_path!==`documents/${uploadId}.pdf`||
     !Number.isSafeInteger(Number(intent.file_bytes))||
     Number(intent.file_bytes)<8||Number(intent.file_bytes)>MAX_TEXTBOOK_BYTES)
   throw new Error('invalid upload intent metadata');
  const size=Number(intent.file_bytes);
  const object=await inspectObject({bucket:intent.storage_bucket,path:intent.storage_path});
  if(!object||!Number.isSafeInteger(Number(object.size))||Number(object.size)!==size)
   throw new Error('uploaded object size mismatch');
  // readObject must yield bounded Uint8Array chunks from private server storage.
  const hash=createHash('sha256');
  let count=0;
  let signature=Buffer.alloc(0);
  for await(const part of readObject({bucket:intent.storage_bucket,path:intent.storage_path})){
   if(!(part instanceof Uint8Array)||part.length===0||part.length>TUS_CHUNK_BYTES)
    throw new Error('invalid upload stream chunk size');
   if(signature.length<5) signature=Buffer.concat([signature,Buffer.from(part.subarray(0,5-signature.length))]);
   count+=part.length;
   if(count>size) throw new Error('uploaded object exceeds expected size');
   hash.update(part);
  }
  if(count!==size) throw new Error('uploaded object length mismatch');
  if(signature.toString('ascii')!=='%PDF-') throw new Error('uploaded file is not a PDF');
  const sha256=hash.digest('hex');
  const document=await completeVerifiedIntent({uploadId,actorId,intent,sha256,fileBytes:count,mimeType:'application/pdf'});
  if(!document) throw new Error('document completion failed');
  return {uploadId,document};
 }catch(error){
  try{await failVerification({uploadId,actorId})}catch(failure){throw new AggregateError([error,failure],'verification and failure transition failed')}
  throw error;
 }
}
