// Trusted PostgreSQL adapter. All SQL is parameterized; no client table access.
export function createSourceUploadIntentDb(db){
 if(typeof db?.query!=='function') throw new TypeError('database query adapter required');
 return {
  async createIntent(intent){
   if(!intent||intent.status!=='pending'||intent.bucket!=='ai-textbook-sources')
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
  async claimVerification({uploadId,actorId}){
   const result=await db.query(
    `update private.ai_source_upload_intents
        set status='verifying',updated_at=now()
      where id=$1 and actor_id=$2 and status in ('pending','uploading')
        and expires_at>now()
      returning id,storage_bucket,storage_path,file_bytes,title`,
    [uploadId,actorId]);
   return result.rows?.[0]??null;
  }
 };
}
