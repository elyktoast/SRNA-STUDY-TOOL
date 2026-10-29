// Validate configuration before opening an HTTP listener.
// Never log or return environment secrets to clients.
export function readSourceRuntimeConfig(env){
 const port=Number(env?.SOURCE_API_PORT??8787);
 const host=env?.SOURCE_API_HOST??'127.0.0.1';
 if(!Number.isInteger(port)||port<1||port>65535) throw new Error('invalid SOURCE_API_PORT');
 if(!['127.0.0.1','::1'].includes(host))
  throw new Error('source API must bind to loopback behind an authenticated reverse proxy');
 for(const name of ['SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY','SOURCE_DATABASE_URL']){
  if(typeof env?.[name]!=='string'||!env[name].trim()) throw new Error('missing '+name);
 }
 return {port,host};
}
