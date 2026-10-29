// Server-only admin listing. No storage keys or PDF bytes are returned.
export function createSourceLibraryReader(db,authorizeAdmin){
 if(typeof db?.query!=='function'||typeof authorizeAdmin!=='function')throw new TypeError('private database and admin verifier required');
 async function check(actorId){if(await authorizeAdmin(actorId)!==true)throw new Error('source library access denied')}
 return {
  async list({actorId}){
   await check(actorId);
   const result=await db.query("select id,title,edition,author,processing_status,created_at,updated_at from private.ai_source_documents order by created_at desc limit 250");
   return result.rows;
  },
  async detail({actorId,documentId}){
   await check(actorId);
   if(typeof documentId!=='string'||!/^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(documentId))throw new Error('invalid document ID');
   const document=await db.query('select id,title,edition,author,processing_status,metadata from private.ai_source_documents where id=$1',[documentId]);
   if(document.rows.length!==1)return null;
   const summary=await db.query('select count(*)::integer as chunk_count,max(page_end)::integer as page_count from private.ai_source_chunks where document_id=$1',[documentId]);
   const passages=await db.query('select page_start as "pageStart",page_end as "pageEnd",printed_page as "printedPage",section_heading as "sectionHeading",content from private.ai_source_chunks where document_id=$1 order by chunk_order limit 40',[documentId]);
   return {document:document.rows[0],pageCount:summary.rows[0]?.page_count??null,chunkCount:summary.rows[0]?.chunk_count??0,passages:passages.rows};
  }
 };
}
