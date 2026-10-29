// Trusted backend only. The caller must enforce admin authorization.
// db is a privileged Postgres adapter implementing query(sql,params).
export function createSourceDbAdapter(db){
 if(!db||typeof db.query!=='function') throw new TypeError('database query adapter required');
 return {
  // Inspection only: never automatically reclaim a possibly still-running worker.
  async listStalledDocuments({olderThanMinutes=60}={}){
   if(!Number.isSafeInteger(olderThanMinutes)||olderThanMinutes<1||olderThanMinutes>10080)
    throw new RangeError('invalid stale-processing threshold');
   const result=await db.query(
    "select id,title,processing_status,updated_at from private.ai_source_documents where processing_status in ('extracting','indexing') and updated_at < now() - ($1::integer * interval '1 minute') order by updated_at asc limit 100",
    [olderThanMinutes]);
   return result.rows??[];
  },
  async setStatus(documentId,status){
   if(!['extracting','indexing','ready','failed'].includes(status)) throw new Error('invalid processing status');
   // Atomically claim processing: a second worker must not replace another worker's chunks.
   const expected={extracting:['uploaded','ready','failed'],indexing:['extracting'],ready:['indexing'],failed:['extracting','indexing']};
   const sql='update private.ai_source_documents set processing_status=$2,updated_at=now() where id=$1 and processing_status=any($3::text[]) returning id';
   const result=await db.query(
    sql,
    [documentId,status,expected[status]]);
   if(result.rowCount!==1) throw new Error(status==='extracting'?'source processing already active or document unavailable':'invalid source processing transition');
  },
  async saveChunks(documentId,chunks){
   if(!Array.isArray(chunks)||chunks.length===0) throw new Error('no chunks to save');
   // A transaction avoids partially indexed books on interrupted writes.
   const client=typeof db.connect==='function'?await db.connect():null;
   if(!client) throw new Error('transaction-capable database adapter required');
   try{
    await client.query('BEGIN');
    // Serialize writes for this document and refuse writes outside the indexing stage.
    const state=await client.query(
     'select processing_status from private.ai_source_documents where id=$1 for update',[documentId]);
    if(state.rows?.[0]?.processing_status!=='indexing')
     throw new Error('source document not in indexing state');
    await client.query('delete from private.ai_source_chunks where document_id=$1',[documentId]);
    for(const c of chunks){
     if(c.documentId!==documentId) throw new Error('source mismatch');
     await client.query(
      'insert into private.ai_source_chunks (document_id,chunk_order,content,page_start,page_end,printed_page,section_heading,content_hash,extraction_method) values ($1,$2,$3,$4,$5,$6,$7,$8,$9)',
      [documentId,c.chunkOrder,c.content,c.pageStart,c.pageEnd,c.printedPage??null,c.sectionHeading??null,c.contentHash,c.extractionMethod??'text']);
    }
    await client.query('COMMIT');
   }catch(error){
    try{await client.query('ROLLBACK')}catch(rollbackError){
     throw new AggregateError([error,rollbackError],'chunk write and rollback failed');
    }
    throw error;
   }finally{client.release?.()}
  }
 };
}
