import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {readSourceRuntimeConfig} from './ai-source-runtime-config.mjs';
import {createSourceRuntime} from './ai-source-runtime.mjs';
import {createSourcePdfJsProvider} from './ai-source-pdfjs-provider.mjs';
import {verifySourceRuntimeResources} from './ai-source-runtime-preflight.mjs';
import {createR2SourceStorageAdapter} from './ai-source-r2-storage.mjs';
import {createR2MultipartController} from './ai-source-r2-multipart.mjs';
import {createSourceUploadIntentDb,createSourceUploadFinalizer} from './ai-source-upload-intent-db.mjs';
import {createSourceUploadRoutes} from './ai-source-upload-routes.mjs';
import {createSourceAdminVerifier} from './ai-source-admin-verifier.mjs';

export async function startSourceServer(env=process.env){
 const {port,host}=readSourceRuntimeConfig(env);
 const require=createRequire(import.meta.url);
 const {Pool}=require('pg');
 const {S3Client,HeadObjectCommand,GetObjectCommand,CreateMultipartUploadCommand,UploadPartCommand,CompleteMultipartUploadCommand,AbortMultipartUploadCommand,ListPartsCommand}=await import('@aws-sdk/client-s3');
 const {getSignedUrl}=await import('@aws-sdk/s3-request-presigner');
 for(const name of ['R2_ACCOUNT_ID','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY']){
  if(typeof env[name]!=='string'||!env[name].trim())throw new Error('R2 server credentials required');
 }
 if(!/^[0-9a-f]{32}$/i.test(env.R2_ACCOUNT_ID))throw new Error('invalid R2 account ID');
 const r2Client=new S3Client({region:'auto',endpoint:`https://${env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,credentials:{accessKeyId:env.R2_ACCESS_KEY_ID,secretAccessKey:env.R2_SECRET_ACCESS_KEY}});
 const {createClient}=await import('@supabase/supabase-js');
 const db=new Pool({connectionString:env.SOURCE_DATABASE_URL,ssl:{rejectUnauthorized:true}});
 const supabase=createClient(env.SUPABASE_URL,env.SUPABASE_SERVICE_ROLE_KEY,{
  auth:{persistSession:false,autoRefreshToken:false}
 });
 try{
  await verifySourceRuntimeResources({db,supabase});
 }catch{
  await db.end();
  throw new Error('textbook source resources not configured');
 }
 let getDocument;
 try{getDocument=await createSourcePdfJsProvider()}
 catch{
  await db.end();
  throw new Error('textbook PDF parser unavailable');
 }
 // No OCR provider is configured: scanned pages will fail closed, never be silently skipped.
 let server;
 try{
  // The legacy direct POST upload stays capped at 40 MiB.
  // Large PDFs use resumable Storage transfers and server-side verification.
  const intents=createSourceUploadIntentDb(db);
  const uploadStorage=createR2SourceStorageAdapter({client:r2Client,commands:{HeadObjectCommand,GetObjectCommand}});
  const r2Controller=createR2MultipartController({client:r2Client,presign:getSignedUrl,commands:{CreateMultipartUploadCommand,UploadPartCommand,CompleteMultipartUploadCommand,AbortMultipartUploadCommand,ListPartsCommand}});
  const uploadRoutes=createSourceUploadRoutes({
   authorizeAdmin:createSourceAdminVerifier(db),
   createIntent:intents.createIntent,
   markUploading:intents.markUploading,
   r2:{controller:r2Controller,getOwnedIntent:intents.getOwnedIntent,getSession:intents.getSession,saveSession:intents.saveSession,markComplete:intents.markComplete,clearSession:intents.clearSession},
   verifyAdapters:{
    claimVerification:intents.claimVerification,
    failVerification:intents.failVerification,
    completeVerifiedIntent:createSourceUploadFinalizer(db),
    inspectObject:uploadStorage.inspectObject,
    readObject:uploadStorage.readObject
   }
  });
  server=createSourceRuntime({db,supabaseStorage:supabase,supabaseAuth:supabase,getDocument,maxBytes:41943040,uploadRoutes});
 }catch(error){
  await db.end();
  throw error;
 }
 try{
  await new Promise((resolve,reject)=>{
   server.once('error',reject);
   server.listen(port,host,resolve);
  });
 }catch(error){
  await db.end();
  throw error;
 }
 server.once('close',()=>{void db.end()});
 return server;
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 startSourceServer().catch(error=>{
  // Keep credentials and connection strings out of process logs.
  console.error('Textbook source API failed to start');
  process.exitCode=1;
 });
}
