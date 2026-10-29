// Server-only session verifier. Use a Supabase Auth client with getUser(token).
// Never trust user IDs or admin flags from request headers.
export function createSourceSupabaseSessionVerifier(supabase){
 if(typeof supabase?.auth?.getUser!=='function') throw new TypeError('Supabase Auth client required');
 return async function getAuthenticatedActor({headers}={}){
  const header=headers?.authorization;
  if(typeof header!=='string'||!/^Bearer [^\s]+$/i.test(header)) return null;
  const token=header.slice(7);
  const {data,error}=await supabase.auth.getUser(token);
  if(error||typeof data?.user?.id!=='string') return null;
  return data.user.id;
 };
}
