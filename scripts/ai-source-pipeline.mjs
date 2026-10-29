import {buildSourceManifest} from './ai-source-manifest.mjs';
import {validateSourceManifest} from './ai-source-ingestion-checks.mjs';

// Dependency-injected pipeline: no secrets or browser credentials in this module.
// Adapter implementations must verify admin access and use private storage.
export async function processSourceDocument({documentId,loadPages,saveChunks,setStatus}){
 if(typeof documentId!=='string'||!documentId.trim()) throw new TypeError('documentId required');
 for(const [name,fn] of Object.entries({loadPages,saveChunks,setStatus}))
   if(typeof fn!=='function') throw new TypeError(name+' must be a function');
 await setStatus(documentId,'extracting');
 try{
   const pages=await loadPages(documentId);
   const manifest=buildSourceManifest({documentId,pages});
   const result=validateSourceManifest(manifest);
   if(!result.ok) throw new Error('source validation failed: '+result.errors.join('; '));
   await setStatus(documentId,'indexing');
   await saveChunks(documentId,manifest.chunks);
   // Ready means text indexing completed; vector embeddings may be pending.
   await setStatus(documentId,'ready');
   return {status:'ready',chunkCount:manifest.chunks.length,pagesSeen:manifest.pagesSeen};
 }catch(error){
   try{await setStatus(documentId,'failed')}catch(statusError){
     throw new AggregateError([error,statusError],'processing failed and failed-status update failed');
   }
   throw error;
 }
}
