// Read-only startup checks. Never create or alter production resources implicitly.
export async function verifySourceRuntimeResources({db,supabase,bucket='ai-textbook-sources'}){
 if(typeof db?.query!=='function'||typeof supabase?.storage?.getBucket!=='function')
  throw new TypeError('database and storage clients required');
 const required=['ai_source_documents','ai_source_sections','ai_source_chunks','ai_source_processing_jobs','ai_source_course_links'];
 const result=await db.query(
  "select table_name from information_schema.tables where table_schema=$1 and table_name=any($2::text[])",
  ['private',required]);
 const found=new Set((result.rows??[]).map(row=>row.table_name));
 for(const name of required) if(!found.has(name)) throw new Error('missing private source schema');
 const rls=await db.query("select relname,relrowsecurity from pg_class where relnamespace='private'::regnamespace and relname=any($1::text[])",[required]);
 const protectedNames=new Set((rls.rows??[]).filter(row=>row.relrowsecurity===true).map(row=>row.relname));
 if(required.some(name=>!protectedNames.has(name))) throw new Error('source table RLS disabled');
 const admin=await db.query("select to_regclass('private.snar_admins') as relation");
 if(!admin.rows?.[0]?.relation) throw new Error('private admin authorization table unavailable');
 const {data,error}=await supabase.storage.getBucket(bucket);
 if(error||!data||data.public!==false) throw new Error('private source storage bucket unavailable');
 return true;
}
