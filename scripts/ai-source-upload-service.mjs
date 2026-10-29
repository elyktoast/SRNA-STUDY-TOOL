import {validateSourceUpload} from './ai-source-upload-validation.mjs';
export async function uploadAdminSource(options){
 const {actorId,authorizeAdmin,bytes,title,storagePath,uploadPrivate,createRecord,removePrivate}=options;
 if(typeof authorizeAdmin!=='function'||!actorId||await authorizeAdmin(actorId)!==true)
  throw new Error('source upload access denied');
 if(typeof uploadPrivate!=='function'||typeof createRecord!=='function'||typeof removePrivate!=='function')
  throw new TypeError('upload adapters required');
 if(typeof storagePath!=='string'||!storagePath.trim()||storagePath.startsWith('/')||storagePath.includes('..'))
  throw new Error('invalid private storage path');
 const metadata=validateSourceUpload(bytes,title);
 await uploadPrivate(storagePath,bytes);
 try{
  return await createRecord({...metadata,storagePath});
 }catch(error){
  try{await removePrivate(storagePath)}
  catch(cleanupError){throw new AggregateError([error,cleanupError],'record creation and upload cleanup failed')}
  throw error;
 }
}
