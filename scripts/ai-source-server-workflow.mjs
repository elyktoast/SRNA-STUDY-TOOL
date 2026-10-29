import {uploadAdminSource} from './ai-source-upload-service.mjs';
import {createPrivateUploadAdapter} from './ai-source-private-upload-adapter.mjs';
import {createSourceDocumentRecord} from './ai-source-document-record.mjs';
import {createSourceDocumentLookup} from './ai-source-document-lookup.mjs';
import {createPrivateSourceReader} from './ai-source-storage-adapter.mjs';
import {createSourceDbAdapter} from './ai-source-db-adapter.mjs';
import {processAdminPdf} from './ai-source-pdf-worker.mjs';

export function createSourceServerWorkflow({db,supabase,authorizeAdmin,getDocument,ocrPage}){
 if(typeof authorizeAdmin!=='function') throw new TypeError('admin verifier required');
 const storage=createPrivateUploadAdapter(supabase);
 const createRecord=createSourceDocumentRecord(db);
 const lookup=createSourceDocumentLookup(db);
 const reader=createPrivateSourceReader({supabase});
 const indexing=createSourceDbAdapter(db);
 return {
  upload:args=>uploadAdminSource({...args,authorizeAdmin,...storage,createRecord}),
  process:args=>processAdminPdf({...args,authorizeAdmin,getDocument,ocrPage,
   readPrivatePdf:id=>reader(id,lookup),...indexing})
 };
}
