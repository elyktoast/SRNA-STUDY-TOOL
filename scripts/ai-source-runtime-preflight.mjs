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
 const columns=await db.query("select column_name from information_schema.columns where table_schema='private' and table_name='ai_source_chunks' and column_name=any($1::text[])",[['printed_page','section_heading']]);
 const citationColumns=new Set((columns.rows??[]).map(row=>row.column_name));
 if(!citationColumns.has('printed_page')||!citationColumns.has('section_heading')) throw new Error('source citation metadata schema missing');
 const grants=await db.query("select table_name,privilege_type,grantee from information_schema.role_table_grants where table_schema='private' and table_name=any($1::text[]) and grantee=any($2::text[])",[required,['anon','authenticated','PUBLIC']]);
 if((grants.rows??[]).length) throw new Error('source tables exposed to client roles');
 const schemaGrants=await db.query("select role_name from unnest($1::text[]) as role_name where has_schema_privilege(role_name, 'private', 'USAGE')",[['anon','authenticated','PUBLIC']]);
 if((schemaGrants.rows??[]).length) throw new Error('private source schema exposed to client roles');
 const admin=await db.query("select to_regclass('private.snar_admins') as relation");
 if(!admin.rows?.[0]?.relation) throw new Error('private admin authorization table unavailable');
 const {data,error}=await supabase.storage.getBucket(bucket);
 if(error||!data||data.public!==false) throw new Error('private source storage bucket unavailable');
 if(!Array.isArray(data.allowed_mime_types)||data.allowed_mime_types.length!==1||data.allowed_mime_types[0]!=='application/pdf') throw new Error('source bucket must allow PDF only');
 if(!Number.isInteger(data.file_size_limit)||data.file_size_limit<1||data.file_size_limit>104857600) throw new Error('source bucket size limit invalid');
 return true;
}
