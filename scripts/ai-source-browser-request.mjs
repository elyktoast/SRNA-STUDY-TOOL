// Browser adapter for the private source API. Supply a token from the existing
// authenticated Supabase session; never persist it or embed service-role secrets.
export function createSourceApiRequest({baseUrl='',getAccessToken,fetchImpl=fetch}={}){
 if(typeof getAccessToken!=='function'||typeof fetchImpl!=='function')
  throw new TypeError('authenticated source API adapters required');
 if(typeof baseUrl!=='string')throw new Error('source API URL must use HTTPS');
 let origin='';
 if(baseUrl!==''){
  let parsed;
  try{parsed=new URL(baseUrl)}catch{throw new Error('invalid source API URL')}
  if(parsed.protocol!=='https:'||parsed.username||parsed.password||
     parsed.search||parsed.hash||parsed.pathname!=='/'||!parsed.hostname)
   throw new Error('source API URL must be an HTTPS origin without credentials or paths');
  origin=parsed.origin;
 }
 return async function request(path,body){
  if(typeof path!=='string'||!/^\/source\/uploads\/[a-z0-9/]+$/.test(path)||
     !body||typeof body!=='object'||Array.isArray(body))
   throw new Error('invalid source API request');
  const token=await getAccessToken();
  if(typeof token!=='string'||!token.trim())throw new Error('source API authentication required');
  const response=await fetchImpl(origin+path,{
   method:'POST',credentials:'omit',
   headers:{'content-type':'application/json','authorization':'Bearer '+token},
   body:JSON.stringify(body)
  });
  if(!response||typeof response.json!=='function')throw new Error('invalid source API response');
  const result=await response.json();
  if(!response.ok)throw new Error(typeof result?.error==='string'?result.error:'source API request failed');
  return result;
 };
}
