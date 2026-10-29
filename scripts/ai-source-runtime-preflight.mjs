// Read-only startup checks. Never create or alter production resources implicitly.
export async function verifySourceRuntimeResources({db,supabase,bucket='ai-textbook-sources'}){
 if(typeof db?.query!=='function'||typeof supabase?.storage?.getBucket!=='function')
  throw new TypeError('database and storage clients required');
 const required=['ai_source_documents','ai_source_sections','ai_source_chunks','ai_source_processing_jobs','ai_source_course_links','ai_source_upload_intents'];
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
 // Effective privileges catch inherited and PUBLIC grants, not just direct ACL entries.
 const grants=await db.query(
  "select roles.client_role, names.table_name from unnest($1::text[]) as roles(client_role) cross join unnest($2::text[]) as names(table_name) where has_table_privilege(roles.client_role, format('%I.%I','private',names.table_name), 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
  [['anon','authenticated'],required]);
 if((grants.rows??[]).length) throw new Error('source tables exposed to client roles');
 const schemaGrants=await db.query("select client_role from unnest($1::text[]) as roles(client_role) where has_schema_privilege(client_role, 'private', 'USAGE')",[['anon','authenticated']]);
 if((schemaGrants.rows??[]).length) throw new Error('private source schema exposed to client roles');
 const admin=await db.query("select to_regclass('private.snar_admins') as relation");
 if(!admin.rows?.[0]?.relation) throw new Error('private admin authorization table unavailable');
 const helper=await db.query("select to_regprocedure('storage.can_insert_ai_source_object(text,text)') as routine");
 if(!helper.rows?.[0]?.routine) throw new Error('source upload helper unavailable');
 const {data,error}=await supabase.storage.getBucket(bucket);
 if(error||!data||data.public!==false) throw new Error('private source storage bucket unavailable');
 if(!Array.isArray(data.allowed_mime_types)||data.allowed_mime_types.length!==1||data.allowed_mime_types[0]!=='application/pdf') throw new Error('source bucket must allow PDF only');
 // Full textbook objects need a larger bucket even when uploaded in TUS chunks.
 // The old single-request upload endpoint remains separately capped at 40 MiB.
 if(!Number.isSafeInteger(data.file_size_limit)||data.file_size_limit<346030080||data.file_size_limit>524288000)
  throw new Error('source bucket must support 330 MiB textbooks (up to 500 MiB)');
 return true;
}
