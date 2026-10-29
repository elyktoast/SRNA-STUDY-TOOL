// Use only with a trusted server-side PostgreSQL connection.
// actorId must come from a verified session, not a client-supplied field.
export function createSourceAdminVerifier(db){
 if(typeof db?.query!=='function') throw new TypeError('database client required');
 return async function authorizeAdmin(actorId){
  if(typeof actorId!=='string'||!actorId.trim()) return false;
  const result=await db.query(
   'select exists(select 1 from private.snar_admins where user_id=$1) as allowed',
   [actorId]);
  return result.rows?.[0]?.allowed===true;
 };
}
