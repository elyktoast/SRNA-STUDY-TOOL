// Server-side only. Supply a privileged storage client after authorization.
export function createPrivateUploadAdapter(supabase,bucket='ai-textbook-sources'){
 if(typeof supabase?.storage?.from!=='function') throw new TypeError('storage client required');
 const storage=supabase.storage.from(bucket);
 return {
  async uploadPrivate(path,bytes){
   const {error}=await storage.upload(path,bytes,{contentType:'application/pdf',upsert:false});
   if(error) throw error;
  },
  async removePrivate(path){
   const {data,error}=await storage.remove([path]);
   if(error) throw error;
   return data;
  }
 };
}
