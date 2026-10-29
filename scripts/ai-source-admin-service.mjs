import {processSourceDocument} from './ai-source-pipeline.mjs';

// The authorization callback must verify the current user server-side.
// Never accept an isAdmin flag from request bodies or browser state.
export async function processAdminSourceDocument({
 documentId,actorId,authorizeAdmin,loadPages,saveChunks,setStatus
}){
 if(typeof authorizeAdmin!=='function') throw new TypeError('server admin authorization required');
 if(typeof actorId!=='string'||!actorId.trim()) throw new Error('authenticated actor required');
 const allowed=await authorizeAdmin(actorId);
 if(allowed!==true) throw new Error('source processing access denied');
 return processSourceDocument({documentId,loadPages,saveChunks,setStatus});
}
