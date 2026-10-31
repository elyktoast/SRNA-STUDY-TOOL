// Staging-only gateway for a private reviewer container binding.
// Deliberately no public backend URL, receipt, or approval routes.
const ORIGIN = 'https://staging.srnastudytool.com';
const PROJECT = 'https://xqyasyambwdyhsjkftqu.supabase.co';
const paths = new Set(['/review/manifest', '/review/page.png']);
const common = {'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','X-Review-Approval-Enabled':'false'};
function respond(status,origin,body=''){
 const headers={...common,'Content-Type':'application/json'};
 if(origin===ORIGIN){headers['Access-Control-Allow-Origin']=ORIGIN;headers.Vary='Origin';}
 return new Response(body,{status,headers});
}
export default {
 async fetch(request,env){
  const url=new URL(request.url),origin=request.headers.get('Origin');
  if(env.STAGING_ONLY!=='true'||env.SUPABASE_URL!==PROJECT||!env.REVIEWER_CONTAINER)
   return respond(503,null,'{"error":"staging_not_configured"}');
  if(origin!==ORIGIN||!paths.has(url.pathname))return respond(403,null,'{"error":"forbidden"}');
  if(request.method==='OPTIONS'){
   if(request.headers.get('Access-Control-Request-Method')!=='GET'||
      request.headers.get('Access-Control-Request-Headers')?.trim().toLowerCase()!=='authorization')
    return respond(403,origin,'{"error":"forbidden_preflight"}');
   const response=respond(204,origin);
   response.headers.set('Access-Control-Allow-Methods','GET');
   response.headers.set('Access-Control-Allow-Headers','Authorization');
   response.headers.set('Access-Control-Max-Age','300');
   return response;
  }
  if(request.method!=='GET')return respond(405,origin,'{"error":"method_not_allowed"}');
  if(url.search.length>2048||request.headers.get('Content-Length')||request.headers.get('Transfer-Encoding'))
   return respond(400,origin,'{"error":"invalid_request"}');
  const params=[...url.searchParams.keys()];
  if(params.length!==(url.pathname==='/review/manifest'?1:2)||
     !params.includes('path')||(url.pathname==='/review/page.png'&&!params.includes('page'))||
     new Set(params).size!==params.length)return respond(400,origin,'{"error":"invalid_query"}');
  const token=request.headers.get('Authorization')||'';
  if(!/^Bearer [^\\s]{1,8192}$/.test(token))return respond(401,origin,'{"error":"authentication_required"}');
  // Verify the staging identity before starting or contacting the private container.
  let identity;
  try{
   const auth=await fetch(PROJECT+'/auth/v1/user',{headers:{Authorization:token,apikey:env.SUPABASE_ANON_KEY},redirect:'error'});
   if(!auth.ok)return respond(403,origin,'{"error":"forbidden"}');
   identity=await auth.json();
  }catch{return respond(503,origin,'{"error":"identity_unavailable"}');}
  if(!identity?.id||identity.is_anonymous===true)return respond(403,origin,'{"error":"forbidden"}');
  // Application-side role and source ownership checks remain mandatory.
  try{
   const container=env.REVIEWER_CONTAINER.getByName('staging-reviewer');
   await container.startAndWaitForPorts();
   const upstream=await container.fetch(new Request('http://reviewer.internal'+url.pathname+url.search,{
    method:'GET',headers:{Authorization:token,Origin:ORIGIN}
   }));
   const headers=new Headers(common);
   headers.set('Access-Control-Allow-Origin',ORIGIN);headers.set('Vary','Origin');
   headers.set('Access-Control-Expose-Headers','X-Review-Approval-Enabled, X-Verified-Source-SHA256, X-Page-Image-SHA256');
   for(const name of ['Content-Type','X-Verified-Source-SHA256','X-Page-Image-SHA256']){
    const value=upstream.headers.get(name);if(value)headers.set(name,value);
   }
   if(upstream.headers.get('X-Review-Approval-Enabled')!=='false')return respond(502,origin,'{"error":"unsafe_upstream"}');
   return new Response(upstream.body,{status:upstream.status,headers});
  }catch{return respond(503,origin,'{"error":"reviewer_unavailable"}');}
 }
};
