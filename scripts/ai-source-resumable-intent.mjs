import {randomUUID} from 'node:crypto';

import {MAX_TEXTBOOK_BYTES,TUS_CHUNK_BYTES} from './ai-source-upload-constants.mjs';
export {MAX_TEXTBOOK_BYTES,TUS_CHUNK_BYTES};

// Server-only intent creation. This does not grant Storage access or start a TUS transfer.
// Actor identity must come from verified authentication, never from a request body.
export async function createResumableSourceIntent({
 actorId,authorizeAdmin,title,fileBytes,mimeType,createIntent,
 now=()=>new Date(),newId=randomUUID
}){
 if(typeof authorizeAdmin!=='function'||typeof createIntent!=='function')
  throw new TypeError('trusted admin and persistence adapters required');
 if(typeof actorId!=='string'||!actorId.trim()||await authorizeAdmin(actorId)!==true)
  throw new Error('source upload access denied');
 if(typeof title!=='string'||!title.trim()||title.trim().length>250)
  throw new Error('invalid textbook title');
 if(!Number.isSafeInteger(fileBytes)||fileBytes<8||fileBytes>MAX_TEXTBOOK_BYTES)
  throw new Error('invalid textbook file size');
 if(mimeType!=='application/pdf') throw new Error('PDF required');
 const id=newId();
 if(typeof id!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id))
  throw new Error('invalid generated transfer ID');
 const created=now();
 if(!(created instanceof Date)||!Number.isFinite(created.getTime()))
  throw new Error('invalid upload timestamp');
 const intent={
  id,actorId,title:title.trim(),fileBytes,mimeType,
  bucket:'ai-textbook-sources',
  storagePath:'documents/'+id+'.pdf',
  status:'pending',createdAt:created.toISOString()
 };
 await createIntent(intent);
 // Do not return actor ID or privileged credentials to the browser.
 return {uploadId:id,title:intent.title,fileBytes,
  chunkBytes:TUS_CHUNK_BYTES,status:'pending'};
}
