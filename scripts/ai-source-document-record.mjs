export function createSourceDocumentRecord(db,{bucket='ai-textbook-sources'}={}){
 if(typeof db?.query!=='function') throw new TypeError('database client required');
 return async function createRecord(meta){
  if(typeof meta?.storagePath!=='string'||!meta.storagePath.trim()) throw new Error('storage path required');
  if(typeof meta?.sha256!=='string'||!/^[a-f0-9]{64}$/.test(meta.sha256)) throw new Error('checksum required');
  const result=await db.query(
   'insert into private.ai_source_documents (title,source_kind,storage_bucket,storage_path,sha256,mime_type,file_bytes) values ($1,$2,$3,$4,$5,$6,$7) returning id,processing_status',
   [meta.title,'textbook',bucket,meta.storagePath,meta.sha256,meta.mimeType,meta.fileBytes]);
  if(result.rows?.length!==1) throw new Error('document insert failed');
  return result.rows[0];
 };
}
