// Trusted PostgreSQL adapter. All SQL is parameterized; no client table access.
export function createSourceUploadIntentDb(db){
 if(typeof db?.query!=='function') throw new TypeError('database query adapter required');
 return {
  async createIntent(intent){
   if(!intent||intent.status!=='pending'||intent.bucket!=='srna-private-textbooks')
    throw new Error('invalid upload intent');
   const result=await db.query(
    `insert into private.ai_source_upload_intents
      (id,actor_id,title,file_bytes,mime_type,storage_bucket,storage_path,status,created_at)
     values ($1,$2,$3,$4,$5,$6,$7,'pending',$8)
     returning id`,
    [intent.id,intent.actorId,intent.title,intent.fileBytes,intent.mimeType,
     intent.bucket,intent.storagePath,intent.createdAt]);
   if(result.rowCount!==1) throw new Error('upload intent insert failed');
  },
  async getOwnedIntent({uploadId,actorId}){
   if(typeof uploadId!=='string'||!/^[0-9a-f-]{36}$/i.test(uploadId))
    throw new Error('invalid upload ID');
   if(typeof actorId!=='string'||!actorId.trim()) throw new Error('invalid actor');
   const result=await db.query(
    `select id,title,file_bytes,mime_type,storage_bucket,storage_path,status,
            document_id,created_at,expires_at
       from private.ai_source_upload_intents
      where id=$1 and actor_id=$2 and expires_at>now()`,
    [uploadId,actorId]);
   return result.rows?.[0]??null;
  },
  async getSession({uploadId,actorId}){
   const result=await db.query(
    `select r2_multipart_id as multipart_id,r2_completed_at
       from private.ai_source_upload_intents
      where id=$1 and actor_id=$2 and status='uploading' and expires_at>now()`,
    [uploadId,actorId]);
   return result.rows?.[0]??null;
  },
  async saveSession({uploadId,actorId,multipartId}){
   if(typeof multipartId!=='string'||!multipartId||multipartId.length>512)
    throw new Error('invalid R2 multipart session');
   const result=await db.query(
    `update private.ai_source_upload_intents
        set r2_multipart_id=$3,updated_at=now()
      where id=$1 and actor_id=$2 and status='uploading'
        and storage_bucket='srna-private-textbooks' and expires_at>now()
        and r2_multipart_id is null
      returning id`,[uploadId,actorId,multipartId]);
   return result.rowCount===1;
  },
  async markComplete({uploadId,actorId,multipartId}){
   const result=await db.query(
    `update private.ai_source_upload_intents
        set r2_completed_at=now(),updated_at=now()
      where id=$1 and actor_id=$2 and status='uploading'
        and r2_multipart_id=$3 and r2_completed_at is null
      returning id`,[uploadId,actorId,multipartId]);
   return result.rowCount===1;
  },
  async markUploading({uploadId,actorId}){
   const result=await db.query(
    `update private.ai_source_upload_intents
        set status='uploading',updated_at=now()
      where id=$1 and actor_id=$2 and status='pending' and expires_at>now()
      returning id`,
    [uploadId,actorId]);
   return result.rowCount===1;
  },
  async failVerification({uploadId,actorId}){
   if(typeof uploadId!=='string'||!/^[0-9a-f-]{36}$/i.test(uploadId)||
      typeof actorId!=='string'||!actorId.trim()) throw new Error('invalid upload identity');
   const result=await db.query(
    `update private.ai_source_upload_intents
        set status='failed',updated_at=now()
      where id=$1 and actor_id=$2 and status='verifying'
      returning id`,[uploadId,actorId]);
   if(result.rowCount!==1) throw new Error('upload failure transition unavailable');
  },
  async claimVerification({uploadId,actorId}){
   const result=await db.query(
    `update private.ai_source_upload_intents
        set status='verifying',updated_at=now()
      where id=$1 and actor_id=$2 and status='uploading'
        and expires_at>now()
      returning id,storage_bucket,storage_path,file_bytes,title`,
    [uploadId,actorId]);
   return result.rows?.[0]??null;
  }
 };
}

// Transactional finalization: creates one document and links it to the claimed intent.
// Caller must have verified the private object's size, PDF signature and SHA-256.
export function createSourceUploadFinalizer(db){
 if(typeof db?.connect!=='function') throw new TypeError('transaction-capable database required');
 return async function completeVerifiedIntent({uploadId,actorId,intent,sha256,fileBytes,mimeType}){
  if(typeof uploadId!=='string'||!/^[0-9a-f-]{36}$/i.test(uploadId)||
     typeof actorId!=='string'||!actorId.trim()) throw new Error('invalid upload identity');
  if(typeof sha256!=='string'||!/^[a-f0-9]{64}$/.test(sha256)||
     mimeType!=='application/pdf'||!Number.isSafeInteger(fileBytes)||fileBytes<8||
     fileBytes>524288000) throw new Error('invalid verified source metadata');
  const client=await db.connect();
  try{
   await client.query('BEGIN');
   const row=await client.query(
    `select id,title,file_bytes,mime_type,storage_bucket,storage_path,status,document_id
       from private.ai_source_upload_intents
      where id=$1 and actor_id=$2 for update`,[uploadId,actorId]);
   const current=row.rows?.[0];
   if(!current||current.status!=='verifying'||current.document_id||
      current.storage_bucket!=='srna-private-textbooks'||
      current.storage_path!==`documents/${uploadId}.pdf`||
      typeof current.title!=='string'||!current.title.trim()||
      Number(current.file_bytes)!==fileBytes||current.mime_type!==mimeType||
      intent?.storage_path!==current.storage_path||
      intent?.storage_bucket!==current.storage_bucket||
      Number(intent?.file_bytes)!==fileBytes)
    throw new Error('upload not eligible for finalization');
   const inserted=await client.query(
    `insert into private.ai_source_documents
      (title,source_kind,storage_bucket,storage_path,sha256,mime_type,file_bytes)
     values ($1,'textbook',$2,$3,$4,$5,$6) returning id,processing_status`,
    [current.title,current.storage_bucket,current.storage_path,sha256,mimeType,fileBytes]);
   if(inserted.rows?.length!==1) throw new Error('document insert failed');
   const document=inserted.rows[0];
   const updated=await client.query(
    `update private.ai_source_upload_intents
        set status='completed',document_id=$3,updated_at=now()
      where id=$1 and actor_id=$2 and status='verifying' and document_id is null
      returning id`,[uploadId,actorId,document.id]);
   if(updated.rowCount!==1) throw new Error('upload finalization conflict');
   await client.query('COMMIT');
   return document;
  }catch(error){
   try{await client.query('ROLLBACK')}catch(rollbackError){
    throw new AggregateError([error,rollbackError],'upload finalization rollback failed');
   }
   throw error;
  }finally{client.release?.()}
 };
}
