// Staging-only gateway for a private reviewer container binding.
// Deliberately no public backend URL, receipt, or approval routes.
const ORIGIN = 'https://staging.srnastudytool.com';
const PROJECT = 'https://xqyasyambwdyhsjkftqu.supabase.co';
const paths = new Set(['/review/manifest', '/review/page.png']);
const common = {'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','X-Review-Approval-Enabled':'false'};
function respond(status,origin,body=''){
 const headers={...common,'Content-Type':'application/json'};
 if(origin===ORIGIN){headers['Access-Control-Allow-Origin']=ORIGIN;headers.Vary='Origin';}
 return new Response(status===204?null:body,{status,headers});
}
export default {
 async fetch(request,env){
  const url=new URL(request.url),origin=request.headers.get('Origin');
  if(env.STAGING_ONLY!=='true'||env.SUPABASE_URL!==PROJECT||!env.SUPABASE_ANON_KEY||!env.REVIEWER_CONTAINER){
   console.error('staging_reviewer_failure',JSON.stringify({stage:'configuration',reason:'required_binding_unavailable'}));
   return respond(503,null,'{"error":"staging_not_configured"}');
  }
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
  if(!/^Bearer [^\s]{1,8192}$/.test(token))return respond(401,origin,'{"error":"authentication_required"}');
  // Verify the staging identity before starting or contacting the private container.
  let identity;
  try{
   const auth=await fetch(PROJECT+'/auth/v1/user',{headers:{Authorization:token,apikey:env.SUPABASE_ANON_KEY},redirect:'error'});
   if(!auth.ok)return respond(403,origin,'{"error":"forbidden"}');
   identity=await auth.json();
  }catch(error){
   const type=error instanceof TypeError?'type_error':error?.name==='SyntaxError'?'invalid_json':error?.name==='AbortError'?'aborted':'other_exception';
   // Only log preapproved categories: exception messages can contain URLs or sensitive request data.
   const message=String(error?.message||'').toLowerCase();
   const cause=String(error?.cause?.message||'').toLowerCase();
   const category=/redirect/.test(message+' '+cause)?'redirect_rejected':
    /invalid.*header|header.*invalid/.test(message+' '+cause)?'header_rejected':
    /dns|resolve|lookup|name_not_resolved/.test(message+' '+cause)?'dns_failure':
    /tls|certificate|ssl/.test(message+' '+cause)?'tls_failure':
    /network|connection|connect|fetch failed/.test(message+' '+cause)?'connection_failure':
    'unclassified';
   console.error('staging_reviewer_failure',JSON.stringify({stage:'identity',reason:'supabase_request_failed',exception_type:type,failure_category:category}));
   return respond(503,origin,'{"error":"identity_unavailable"}');
  }
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
   if(upstream.ok){
    const digest=upstream.headers.get('X-Verified-Source-SHA256')||'';
    const type=(upstream.headers.get('Content-Type')||'').toLowerCase();
    if(!/^[a-f0-9]{64}$/.test(digest))return respond(502,origin,'{"error":"missing_source_integrity"}');
    if(url.pathname==='/review/page.png'){
      if(!type.startsWith('image/png')||!/^[a-f0-9]{64}$/.test(upstream.headers.get('X-Page-Image-SHA256')||''))
       return respond(502,origin,'{"error":"invalid_page_integrity"}');
    }else{
     if(!type.startsWith('application/json'))return respond(502,origin,'{"error":"invalid_manifest_type"}');
     let manifest;
     try{manifest=await upstream.clone().json()}catch{return respond(502,origin,'{"error":"invalid_manifest"}');}
     if(manifest?.source_sha256!==digest||
        !Number.isSafeInteger(manifest?.pdf_page_count)||manifest.pdf_page_count<1||
        manifest.approval_enabled!==false)
      return respond(502,origin,'{"error":"manifest_integrity_mismatch"}');
    }
   }
   return new Response(upstream.body,{status:upstream.status,headers});
  }catch{
   console.error('staging_reviewer_failure',JSON.stringify({stage:'container',reason:'startup_or_upstream_failed'}));
   return respond(503,origin,'{"error":"reviewer_unavailable"}');
  }
 }
};

