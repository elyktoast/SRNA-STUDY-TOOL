import {createSourceServerWorkflow} from './ai-source-server-workflow.mjs';
import {createSourceAdminVerifier} from './ai-source-admin-verifier.mjs';
import {createSourceSupabaseSessionVerifier} from './ai-source-supabase-session.mjs';
import {createSourceNodeServer} from './ai-source-node-http.mjs';

// Trusted server process only. db is a transaction-capable PostgreSQL pool.
// supabaseStorage is a server-side privileged Storage client.
// supabaseAuth validates user access tokens via auth.getUser(token).
export function createSourceRuntime({db,supabaseStorage,supabaseAuth,getDocument,ocrPage,maxBytes}){
 if(typeof db?.query!=='function'||typeof db?.connect!=='function')
  throw new TypeError('transaction-capable PostgreSQL pool required');
 const authorizeAdmin=createSourceAdminVerifier(db);
 const getAuthenticatedActor=createSourceSupabaseSessionVerifier(supabaseAuth);
 const workflow=createSourceServerWorkflow({
  db,supabase:supabaseStorage,authorizeAdmin,getDocument,ocrPage
 });
 return createSourceNodeServer({workflow,getAuthenticatedActor,maxBytes});
}
