import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {readSourceRuntimeConfig} from './ai-source-runtime-config.mjs';
import {createSourceRuntime} from './ai-source-runtime.mjs';
import {createSourcePdfJsProvider} from './ai-source-pdfjs-provider.mjs';
import {verifySourceRuntimeResources} from './ai-source-runtime-preflight.mjs';
import {createSourceUploadStorageStream} from './ai-source-upload-storage-stream.mjs';
import {createSourceUploadIntentDb,createSourceUploadFinalizer} from './ai-source-upload-intent-db.mjs';
import {createSourceUploadRoutes} from './ai-source-upload-routes.mjs';
import {createSourceAdminVerifier} from './ai-source-admin-verifier.mjs';

export async function startSourceServer(env=process.env){
 const {port,host}=readSourceRuntimeConfig(env);
 const require=createRequire(import.meta.url);
 const {Pool}=require('pg');
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
  const uploadStorage=createSourceUploadStorageStream({supabase});
  const uploadRoutes=createSourceUploadRoutes({
   authorizeAdmin:createSourceAdminVerifier(db),
   createIntent:intents.createIntent,
   markUploading:intents.markUploading,
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
