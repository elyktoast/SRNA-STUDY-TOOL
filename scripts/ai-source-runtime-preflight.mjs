// Read-only startup checks. Never create or alter production resources implicitly.
export async function verifySourceRuntimeResources({db}){
 if(typeof db?.query!=='function')
  throw new TypeError('database client required');
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
 const r2Columns=await db.query("select column_name from information_schema.columns where table_schema='private' and table_name='ai_source_upload_intents' and column_name=any($1::text[])",[['r2_multipart_id','r2_completed_at']]);
 const r2Names=new Set((r2Columns.rows??[]).map(row=>row.column_name));
 if(!r2Names.has('r2_multipart_id')||!r2Names.has('r2_completed_at'))throw new Error('R2 session schema missing');
 return true;
}
