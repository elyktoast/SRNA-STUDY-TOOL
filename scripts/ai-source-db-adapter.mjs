// Trusted backend only. The caller must enforce admin authorization.
// db is a privileged Postgres adapter implementing query(sql,params).
export function createSourceDbAdapter(db){
 if(!db||typeof db.query!=='function') throw new TypeError('database query adapter required');
 return {
  async setStatus(documentId,status){
   if(!['extracting','indexing','ready','failed'].includes(status)) throw new Error('invalid processing status');
   const result=await db.query(
    'update private.ai_source_documents set processing_status=$2,updated_at=now() where id=$1 returning id',
    [documentId,status]);
   if(result.rowCount!==1) throw new Error('source document missing or inaccessible');
  },
  async saveChunks(documentId,chunks){
   if(!Array.isArray(chunks)||chunks.length===0) throw new Error('no chunks to save');
   // A transaction avoids partially indexed books on interrupted writes.
   const client=typeof db.connect==='function'?await db.connect():null;
   if(!client) throw new Error('transaction-capable database adapter required');
   try{
    await client.query('BEGIN');
    await client.query('delete from private.ai_source_chunks where document_id=$1',[documentId]);
    for(const c of chunks){
     if(c.documentId!==documentId) throw new Error('source mismatch');
     await client.query(
      'insert into private.ai_source_chunks (document_id,chunk_order,content,page_start,page_end,content_hash,extraction_method) values ($1,$2,$3,$4,$5,$6,$7)',
      [documentId,c.chunkOrder,c.content,c.pageStart,c.pageEnd,c.contentHash,c.extractionMethod??'text']);
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
