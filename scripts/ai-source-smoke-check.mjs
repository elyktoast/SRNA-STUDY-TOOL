// Run before a live PDF test:
// SOURCE_API_URL=https://your-app.example SOURCE_ACCESS_TOKEN=<admin token> node scripts/ai-source-smoke-check.mjs
// Keep tokens in environment variables; never put them in command arguments or logs.
export async function checkSourceApi({baseUrl,accessToken,fetchImpl=fetch}){
 if(typeof baseUrl!=='string'||!/^https:\/\/[^/?#]+(?:\/)?$/.test(baseUrl))
  throw new Error('SOURCE_API_URL must be an HTTPS origin');
 if(typeof accessToken!=='string'||!accessToken.trim())throw new Error('SOURCE_ACCESS_TOKEN required');
 const response=await fetchImpl(baseUrl.replace(/\/$/,'')+'/source/documents',{
  method:'GET',headers:{authorization:'Bearer '+accessToken,accept:'application/json'},
  redirect:'manual',signal:AbortSignal.timeout(10000)
 });
 if(response.status===401)return {ready:false,reason:'authentication rejected'};
 if(response.status===403)return {ready:false,reason:'administrator access denied'};
 if(response.status===404)return {ready:false,reason:'source API route not exposed by reverse proxy'};
 if(response.status>=300&&response.status<400)return {ready:false,reason:'unexpected redirect from source API'};
 if(!response.ok)return {ready:false,reason:'source API returned HTTP '+response.status};
 const type=response.headers?.get?.('content-type')||'';
 if(!type.includes('application/json'))return {ready:false,reason:'source API returned non-JSON response'};
 return {ready:true,reason:'authenticated source API is reachable'};
}
if(process.argv[1]&&import.meta.url===new URL('file://'+process.argv[1]).href){
 checkSourceApi({baseUrl:process.env.SOURCE_API_URL,accessToken:process.env.SOURCE_ACCESS_TOKEN})
  .then(result=>{console.log(result.reason);if(!result.ready)process.exitCode=1})
  .catch(()=>{console.error('Source API connectivity check failed');process.exitCode=1});
}
