import {validateSourceUpload} from './ai-source-upload-validation.mjs';
export async function uploadAdminSource(options){
 const {actorId,authorizeAdmin,bytes,title,storagePath,uploadPrivate,createRecord}=options;
 if(typeof authorizeAdmin!=='function'||await authorizeAdmin(actorId)!==true)
  throw new Error('source upload access denied');
 if(typeof uploadPrivate!=='function'||typeof createRecord!=='function')
  throw new TypeError('upload adapters required');
 const metadata=validateSourceUpload(bytes,title);
 await uploadPrivate(storagePath,bytes);
 return createRecord({...metadata,storagePath});
}
