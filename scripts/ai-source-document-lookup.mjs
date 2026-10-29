export function createSourceDocumentLookup(db){
 if(typeof db?.query!=='function') throw new TypeError('database client required');
 return async function lookupDocument(documentId){
  if(typeof documentId!=='string'||!documentId.trim()) throw new Error('document ID required');
  const result=await db.query(
   'select id,storage_bucket,storage_path,mime_type,file_bytes,sha256 from private.ai_source_documents where id=$1',
   [documentId]);
  if(result.rows?.length!==1) return null;
  return result.rows[0];
 };
}
