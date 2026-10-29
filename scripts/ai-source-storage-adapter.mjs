import {assertSourceChecksum} from './ai-source-checksum.mjs';
// Server-only adapter. Supply a privileged Supabase client after admin authorization.
// Never return a public URL for textbook source files.
export function createPrivateSourceReader({supabase,bucket='ai-textbook-sources'}){
 if(!supabase||typeof supabase.storage?.from!=='function')
  throw new TypeError('Supabase Storage client required');
 if(typeof bucket!=='string'||!bucket.trim()) throw new TypeError('bucket required');
 return async function readPrivatePdf(documentId,lookupDocument){
  if(typeof lookupDocument!=='function') throw new TypeError('document lookup required');
  const document=await lookupDocument(documentId);
  if(!document||document.id!==documentId) throw new Error('source document not found');
  if(document.storage_bucket!==bucket) throw new Error('source bucket mismatch');
  if(document.mime_type!=='application/pdf') throw new Error('unsupported source MIME type');
  if(typeof document.storage_path!=='string'||!document.storage_path.trim())
   throw new Error('missing private source path');
  const {data,error}=await supabase.storage.from(bucket).download(document.storage_path);
  if(error) throw error;
  if(!data||typeof data.arrayBuffer!=='function') throw new Error('private source download failed');
  const bytes=new Uint8Array(await data.arrayBuffer());
  if(bytes.length!==document.file_bytes) throw new Error('source file length mismatch');
  assertSourceChecksum(bytes,document.sha256);
  return bytes;
 };
}
