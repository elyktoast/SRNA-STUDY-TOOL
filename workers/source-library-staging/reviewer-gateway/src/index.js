// Staging-only gateway for a private reviewer container binding.
// Deliberately no public backend URL, receipt, or approval routes.
const ORIGIN = 'https://staging.srnastudytool.com';
const PROJECT = 'https://xqyasyambwdyhsjkftqu.supabase.co';
const paths = new Set(['/review/manifest', '/review/page.png', '/generation/preflight', '/generation/one', '/generation/provider-check', '/generation/checkpoint-readiness', '/generation/textbooks']);
const draftPath = /^\/generation\/drafts(?:\/[0-9a-fA-F-]{36}(?:\/review|\/revalidate|\/revisions)?)?$/;
const common = {'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','X-Review-Approval-Enabled':'false'};
function respond(status,origin,body=''){
 const headers={...common,'Content-Type':'application/json'};
 if(origin===ORIGIN){headers['Access-Control-Allow-Origin']=ORIGIN;headers.Vary='Origin';}
 return new Response(status===204?null:body,{status,headers});
}
// Signed server-to-server relay: no browser bearer, no provider key in the container request.
function relayFailure(error,provider,step){
 const name=String(error?.name||'');
 const reason=String(error?.message||'').toLowerCase();
 const timeout=name==='TimeoutError'||name==='AbortError'||/timed out|timeout/.test(reason);
 const category=timeout?'timeout':name==='TypeError'?'network':'runtime';
 // Never log credentials, request bodies, URLs or provider exception messages.
 console.error('staging_relay_failure',JSON.stringify({provider,step,category}));
 return respond(503,null,JSON.stringify({error:timeout?'relay_timeout':'relay_network',category}));
}
async function relayGroq(request,env){
 if(env.STAGING_ONLY!=='true'||env.AI_GENERATION_OPT_IN!=='true'||!env.AI_PROVIDER_API_KEY||!env.STAGING_RECEIPT_SIGNING_SECRET)return respond(503,null,'{"error":"relay_disabled"}');
 if(request.method!=='POST'||request.headers.get('Content-Type')!=='application/json')return respond(405,null,'{"error":"method_not_allowed"}');
 const length=Number(request.headers.get('Content-Length')||0);
 if(length>524288)return respond(413,null,'{"error":"request_too_large"}');
 const bytes=new Uint8Array(await request.arrayBuffer());
 if(bytes.length>524288)return respond(413,null,'{"error":"request_too_large"}');
 const timestamp=request.headers.get('X-Relay-Timestamp')||'';
 const signature=request.headers.get('X-Relay-Signature')||'';
 if(!/^\d{10}$/.test(timestamp)||Math.abs(Date.now()/1000-Number(timestamp))>30||!/^\b[a-f0-9]{64}\b$/.test(signature))return respond(403,null,'{"error":"forbidden"}');
 const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(env.STAGING_RECEIPT_SIGNING_SECRET),{name:'HMAC',hash:'SHA-256'},false,['sign']);
 const prefix=new TextEncoder().encode('srna-groq-relay-v1\n'+timestamp+'\n');
 const signed=new Uint8Array(prefix.length+bytes.length);signed.set(prefix);signed.set(bytes,prefix.length);
 const expected=new Uint8Array(await crypto.subtle.sign('HMAC',key,signed));
 const received=new Uint8Array(signature.match(/../g).map(x=>parseInt(x,16)));
 let mismatch=0;for(let i=0;i<32;i++)mismatch|=expected[i]^received[i];
 if(mismatch)return respond(403,null,'{"error":"forbidden"}');
 let payload;try{payload=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes))}catch{return respond(400,null,'{"error":"invalid_json"}')}
 if(payload?.diagnostic==='groq_models'&&Object.keys(payload).length===1){
  try{
   const response=await fetch('https://api.groq.com/openai/v1/models',{method:'GET',headers:{Authorization:'Bearer '+env.AI_PROVIDER_API_KEY},redirect:'manual',signal:AbortSignal.timeout(8000)});
   const status=response.status;
   return respond(200,null,JSON.stringify({check:'groq_models_via_signed_relay',provider_status:[200,401,403,429].includes(status)?status:0,rule:status===200?'OK':status===401?'PROVIDER_AUTH':status===403?'PROVIDER_FORBIDDEN':status===429?'PROVIDER_RATE_LIMIT':'PROVIDER_OTHER',generation_performed:false}));
  }catch{return respond(503,null,'{"error":"relay_network"}')}
 }
 if(payload?.diagnostic==='hybrid_models'&&Object.keys(payload).length===1){
  if(env.AI_HYBRID_ENABLED!=='true'||!env.AI_GEMINI_API_KEY)return respond(503,null,'{"error":"relay_disabled"}');
  try{
   const check=await fetch('https://generativelanguage.googleapis.com/v1beta/models',{headers:{'x-goog-api-key':env.AI_GEMINI_API_KEY},redirect:'manual',signal:AbortSignal.timeout(8000)});
   if(!check.ok)return respond(200,null,JSON.stringify({check:'gemini_models',provider_status:check.status,generation_performed:false,model_available:false}));
   const body=await check.json();const models=Array.isArray(body.models)?body.models:[];
   const selected='models/'+env.AI_GEMINI_MODEL;
   return respond(200,null,JSON.stringify({check:'gemini_models',provider_status:200,generation_performed:false,model_available:models.some(m=>m.name===selected&&m.supportedGenerationMethods?.includes('generateContent')),available_flash_models:models.filter(m=>m.name?.includes('flash')&&m.supportedGenerationMethods?.includes('generateContent')).map(m=>m.name).slice(0,12)}));
  }catch{return respond(503,null,'{"error":"relay_network"}')}
 }
 if(!([env.AI_GENERATOR_MODEL, ...(env.AI_BLIND_REVIEW_OPT_IN==='true'?[env.AI_REVIEWER_MODEL]:[])].includes(payload?.model))||!Array.isArray(payload.messages)||payload.messages.length!==2||payload.messages[0]?.role!=='system'||payload.messages[1]?.role!=='user'||typeof payload.messages[1]?.content!=='string'||payload.messages[1].content.length>300000||!Number.isInteger(payload.max_tokens)||payload.max_tokens<256||payload.max_tokens>8192||payload.temperature!==0.2)return respond(400,null,'{"error":"invalid_provider_payload"}');
 let step;try{step=JSON.parse(payload.messages[1].content)}catch{return respond(400,null,'{"error":"invalid_step"}')}
 if(!['concept_card','item_draft','rationale','rewrite','blind_review'].includes(step?.step)||step.rules_version!=='2.0'||step.auto_publish!==false||(step.step==='rewrite'&&env.AI_REWRITE_OPT_IN!=='true')||(step.step==='blind_review'&&(env.AI_BLIND_REVIEW_OPT_IN!=='true'||payload.model!==env.AI_REVIEWER_MODEL||payload.model===env.AI_GENERATOR_MODEL||step.blind!==true))||(step.step!=='blind_review'&&payload.model!==env.AI_GENERATOR_MODEL))return respond(400,null,'{"error":"invalid_step"}');
 try{
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),55000);
  const hybrid=env.AI_HYBRID_ENABLED==='true';
  const provider=hybrid&&step.step==='concept_card'?'gemini':hybrid&&step.step==='rationale'?'cloudflare':'groq';
  if(provider==='gemini'&&(!env.AI_GEMINI_API_KEY||!/^gemini-[a-zA-Z0-9.-]+$/.test(env.AI_GEMINI_MODEL||'')))return respond(503,null,'{"error":"relay_disabled"}');
  if(provider==='cloudflare'&&(!env.AI_CLOUDFLARE_ACCOUNT_ID||!env.AI_CLOUDFLARE_API_TOKEN||!/^@[a-zA-Z0-9/_-]+$/.test(env.AI_CLOUDFLARE_MODEL||'')))return respond(503,null,'{"error":"relay_disabled"}');
  const input=payload.messages[0].content+'\n'+payload.messages[1].content;
  const target=provider==='gemini'?'https://generativelanguage.googleapis.com/v1beta/models/'+encodeURIComponent(env.AI_GEMINI_MODEL)+':generateContent':provider==='cloudflare'?'https://api.cloudflare.com/client/v4/accounts/'+encodeURIComponent(env.AI_CLOUDFLARE_ACCOUNT_ID)+'/ai/run/'+env.AI_CLOUDFLARE_MODEL:'https://api.groq.com/openai/v1/chat/completions';
  const providerHeaders=provider==='gemini'?{'x-goog-api-key':env.AI_GEMINI_API_KEY,'Content-Type':'application/json'}:provider==='cloudflare'?{Authorization:'Bearer '+env.AI_CLOUDFLARE_API_TOKEN,'Content-Type':'application/json'}:{Authorization:'Bearer '+env.AI_PROVIDER_API_KEY,'Content-Type':'application/json'};
  const providerBody=provider==='gemini'?JSON.stringify({contents:[{parts:[{text:input}]}],generationConfig:{temperature:0.2,maxOutputTokens:payload.max_tokens,responseMimeType:'application/json',thinkingConfig:{thinkingBudget:0}}}):provider==='cloudflare'?JSON.stringify({messages:[{role:'user',content:input}],max_tokens:payload.max_tokens,temperature:0.2}):bytes;
  let upstream;
  if(provider==='gemini'){
   // Resolve the API IDs from Google's own model listing; dashboard labels are not API IDs.
   // API IDs from Google's model catalog, not human-readable display names.
   // Prefer the configured, verified API model; never assume marketing names are valid IDs.
   const preferred=[env.AI_GEMINI_MODEL];
   const available=new Set();
   let listingSucceeded=false;
   try{
    let next='';
    for(let page=0;page<2;page++){
     const listing=await fetch('https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000'+(next?'&pageToken='+encodeURIComponent(next):''),{headers:{'x-goog-api-key':env.AI_GEMINI_API_KEY},redirect:'manual',signal:controller.signal});
     if(!listing.ok)break;
     listingSucceeded=true;
     const data=await listing.json();
     for(const model of data.models||[]){
      if(typeof model.name==='string'&&model.name.startsWith('models/gemini-')&&/^[a-zA-Z0-9.-]+$/.test(model.name.slice('models/'.length))&&model.supportedGenerationMethods?.includes('generateContent'))available.add(model.name);
     }
     next=data.nextPageToken||'';if(!next)break;
    }
   }catch{}
   const configured='models/'+env.AI_GEMINI_MODEL;
   const order=[...new Set([...preferred.map(id=>'models/'+id),configured])];
   const candidates=listingSucceeded?order.filter(id=>available.has(id)):[configured];
   if(!candidates.length)return respond(502,null,'{"error":"provider_failed","rule":"PROVIDER_MODEL_UNAVAILABLE"}');
   for(const model of candidates){
    upstream=await fetch('https://generativelanguage.googleapis.com/v1beta/'+model+':generateContent',{method:'POST',headers:providerHeaders,body:providerBody,redirect:'manual',signal:controller.signal});
    // Do not retry throttled or rejected requests; no automatic paid duplicate generation.
    if(upstream.ok||![404].includes(upstream.status))break;
    await upstream.body?.cancel();
   }
  }else{
   upstream=await fetch(target,{method:'POST',headers:providerHeaders,body:providerBody,redirect:'manual',signal:controller.signal});
  }
  if(!upstream)return respond(503,null,'{"error":"relay_network"}');
  if(!upstream.ok){const rule=upstream.status===400||upstream.status===422?'PROVIDER_REQUEST_REJECTED':upstream.status===404?'PROVIDER_MODEL_UNAVAILABLE':upstream.status===401?'PROVIDER_AUTH':upstream.status===403?'PROVIDER_FORBIDDEN':upstream.status===429?'PROVIDER_RATE_LIMIT':'PROVIDER_UPSTREAM';const rawRetry=upstream.headers.get('Retry-After');
   const seconds=rawRetry!==null&&/^\d{1,5}$/.test(rawRetry)?Math.min(3600,Number(rawRetry)):null;
   const remainingRequests=upstream.headers.get('x-ratelimit-remaining-requests');
   const remainingTokens=upstream.headers.get('x-ratelimit-remaining-tokens');
   const safeCount=v=>v!==null&&/^\d{1,10}$/.test(v)?Number(v):null;
   const rateLimit=rule==='PROVIDER_RATE_LIMIT'?{
    ...(safeCount(remainingRequests)!==null?{remaining_requests:safeCount(remainingRequests)}:{}),
    ...(safeCount(remainingTokens)!==null?{remaining_tokens:safeCount(remainingTokens)}:{})
   }:{};
   return respond(502,null,JSON.stringify({error:'provider_failed',rule,...rateLimit,...(rule==='PROVIDER_RATE_LIMIT'&&seconds!==null?{retry_after_seconds:seconds}:{})}))}
  const result=await upstream.arrayBuffer();if(result.byteLength>262144)return respond(502,null,'{"error":"provider_response_too_large"}');
  if(provider==='groq')return new Response(result,{status:200,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
  let data;try{data=JSON.parse(new TextDecoder().decode(result))}catch{return respond(502,null,'{"error":"provider_failed","rule":"PROVIDER_UPSTREAM"}')}
  const rawContent=provider==='gemini'?data?.candidates?.[0]?.content?.parts?.map(p=>p.text||'').join(''):data?.result?.response;
  const content=typeof rawContent==='string'?rawContent:rawContent&&typeof rawContent==='object'?JSON.stringify(rawContent):null;
  if(typeof content!=='string'||content.length>262144)return respond(502,null,'{"error":"provider_failed","rule":"PROVIDER_UPSTREAM"}');
  return respond(200,null,JSON.stringify({choices:[{message:{content}}]}));
 }catch(error){return relayFailure(error,typeof provider==='string'?provider:'unknown',typeof step?.step==='string'?step.step:'unknown')}
 finally{clearTimeout(timeout)}
}
export default {
 async fetch(request,env){
  const url=new URL(request.url),origin=request.headers.get('Origin');
  if(url.pathname==='/internal/groq-relay')return relayGroq(request,env);
  if(env.STAGING_ONLY!=='true'||env.SUPABASE_URL!==PROJECT||!env.SUPABASE_ANON_KEY||!env.REVIEWER_CONTAINER){
   console.error('staging_reviewer_failure',JSON.stringify({stage:'configuration',reason:'required_binding_unavailable'}));
   return respond(503,null,'{"error":"staging_not_configured"}');
  }
  if(origin!==ORIGIN||(!paths.has(url.pathname)&&!draftPath.test(url.pathname)))return respond(403,null,'{"error":"forbidden"}');
  const generation=url.pathname==='/generation/preflight';
  const generateOne=url.pathname==='/generation/one';
  const providerCheck=url.pathname==='/generation/provider-check';
  const checkpointCheck=url.pathname==='/generation/checkpoint-readiness';
  const textbookList=url.pathname==='/generation/textbooks';
  const draftWrite=draftPath.test(url.pathname)&&(request.method==='POST'||(request.method==='OPTIONS'&&request.headers.get('Access-Control-Request-Method')==='POST'));
  const draftPostAllowed=url.pathname==='/generation/drafts'||url.pathname.endsWith('/review')||url.pathname.endsWith('/revisions');
  const draftRead=draftPath.test(url.pathname)&&!url.pathname.endsWith('/review');
    const allowedMethods=(generation||generateOne)?'POST':draftPath.test(url.pathname)?(url.pathname.endsWith('/review')?'POST':draftPostAllowed?'GET, POST':'GET'):'GET';
  if(request.method==='OPTIONS'){
   const requestedHeaders=(request.headers.get('Access-Control-Request-Headers')||'').toLowerCase().replace(/\s/g,'');
   if(!allowedMethods.split(', ').includes(request.headers.get('Access-Control-Request-Method'))||
      !((generation||generateOne||draftWrite)?['authorization,content-type','content-type,authorization'].includes(requestedHeaders):requestedHeaders==='authorization'))
    return respond(403,origin,'{"error":"forbidden_preflight"}');
   const response=respond(204,origin);
   response.headers.set('Access-Control-Allow-Methods',allowedMethods);
   response.headers.set('Access-Control-Allow-Headers',(generation||generateOne||draftWrite)?'Authorization, Content-Type':'Authorization');
   response.headers.set('Access-Control-Max-Age','300');
   return response;
  }
  if(!allowedMethods.split(', ').includes(request.method))return respond(405,origin,'{"error":"method_not_allowed"}');
  if((generation||draftRead||providerCheck||checkpointCheck||textbookList)&&url.search)return respond(400,origin,'{"error":"invalid_query"}');
  if((generation||generateOne||draftWrite)&&Number(request.headers.get('Content-Length')||0)>8192)return respond(413,origin,'{"error":"request_too_large"}');
  if((generation||generateOne||draftWrite)&&(url.search||!/^application\/json(?:;|$)/i.test(request.headers.get('Content-Type')||'')))return respond(400,origin,'{"error":"invalid_request"}');
  if(url.search.length>2048||(!generation&&!generateOne&&!draftWrite&&request.headers.get('Content-Length'))||request.headers.get('Transfer-Encoding'))
   return respond(400,origin,'{"error":"invalid_request"}');
  const params=[...url.searchParams.keys()];
  if(!generation&&!generateOne&&!draftRead&&!draftWrite&&!providerCheck&&!checkpointCheck&&!textbookList&&(params.length!==(url.pathname==='/review/manifest'?1:2)||
     !params.includes('path')||(url.pathname==='/review/page.png'&&!params.includes('page'))||
     new Set(params).size!==params.length))return respond(400,origin,'{"error":"invalid_query"}');
  const token=request.headers.get('Authorization')||'';
  if(!/^Bearer [^\s]{1,8192}$/.test(token))return respond(401,origin,'{"error":"authentication_required"}');
  // Verify the staging identity before starting or contacting the private container.
  let identity;
  try{
   const auth=await fetch(PROJECT+'/auth/v1/user',{headers:{Authorization:token,apikey:env.SUPABASE_ANON_KEY},redirect:'manual'});
   // Cloudflare Workers does not support redirect:'error'; manual prevents credential forwarding.
   // Reject redirects explicitly without following them or exposing their Location header.
   if(auth.status>=300&&auth.status<400){
    console.error('staging_reviewer_auth_denied',JSON.stringify({stage:'supabase',category:'redirect',status:auth.status}));
    return respond(403,origin,'{"error":"forbidden"}');
   }
   if(!auth.ok){
    const body=await auth.clone().json().catch(()=>null);
    const rawCode=typeof body?.code==='string'?body.code:typeof body?.error_code==='string'?body.error_code:'';
    const allowedCodes=new Set(['invalid_credentials','bad_jwt','invalid_jwt','jwt_expired','session_not_found','session_expired','user_not_found','invalid_token','invalid_api_key','api_key_invalid']);
    const safeCode=allowedCodes.has(rawCode)?rawCode:'unclassified';
    // Supabase may use msg/message/error rather than a machine-readable code.
    // Classify internally, emitting only a static label; never emit the response.
    const detail=[body?.msg,body?.message,body?.error,body?.error_description]
      .filter(x=>typeof x==='string').join(' ').toLowerCase();
    const hint=/api.?key|apikey|invalid key|no api key/.test(detail)?'api_key':
      /signature|signing|verification key/.test(detail)?'signature':
      /expired|exp claim/.test(detail)?'expired':
      /revoked|session.*not.*found|session.*invalid/.test(detail)?'session':
      /invalid.*jwt|jwt.*invalid|bad jwt|malformed/.test(detail)?'jwt_invalid':
      /user.*not.*found|user.*deleted/.test(detail)?'user_missing':
      /authorization|bearer|token/.test(detail)?'credential_other':'unclassified';
    console.error('staging_reviewer_auth_denied',JSON.stringify({stage:'supabase',category:'identity_rejected',status:auth.status,code:safeCode,hint}));
    return respond(403,origin,'{"error":"forbidden"}');
   }
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
  let containerStage='binding';
  try{
   const container=env.REVIEWER_CONTAINER.getByName('staging-reviewer');
   containerStage='startup';
   const required=['STAGING_DATABASE_URL','STAGING_R2_ACCOUNT_ID','STAGING_R2_ACCESS_KEY_ID','STAGING_R2_SECRET_ACCESS_KEY','SUPABASE_ANON_KEY','STAGING_RECEIPT_SIGNING_SECRET'];
   for(const key of required){
    if(!env[key]){
     console.error('staging_reviewer_failure',JSON.stringify({stage:'configuration',reason:'container_secret_missing',name:key}));
     return respond(503,origin,'{"error":"staging_not_configured"}');
    }
   }
   if(env.AI_HYBRID_ENABLED==='true'){
    const keys=['AI_GEMINI_API_KEY','AI_GEMINI_MODEL','AI_CLOUDFLARE_ACCOUNT_ID','AI_CLOUDFLARE_API_TOKEN','AI_CLOUDFLARE_MODEL'];
    if(env.AI_GENERATION_OPT_IN!=='true'||!keys.every(key=>typeof env[key]==='string'&&env[key].length>0)){
     return respond(503,origin,'{"error":"staging_not_configured"}');
    }
   }
   const envVars={STAGING_ONLY:'true',SUPABASE_URL:PROJECT};
   for(const key of required)envVars[key]=env[key];
   // Model credentials remain server-side. Incomplete configuration disables generation.
   const aiKeys=['AI_PROVIDER_ENDPOINT','AI_ALLOWED_HOSTS','AI_PROVIDER_API_KEY','AI_GENERATOR_MODEL'];
   // Never silently disable requested checkpointing because model configuration is incomplete.
   if(env.AI_GENERATION_CHECKPOINTS_ENABLED==='true'&&
      (env.AI_GENERATION_OPT_IN!=='true'||!aiKeys.every(key=>typeof env[key]==='string'&&env[key].length>0))){
    console.error('staging_reviewer_failure',JSON.stringify({stage:'configuration',reason:'checkpoint_ai_config_incomplete'}));
    return respond(503,origin,'{"error":"staging_not_configured"}');
   }
   if(env.AI_GENERATION_OPT_IN==='true'&&aiKeys.every(key=>typeof env[key]==='string'&&env[key].length>0)){
    envVars.AI_GENERATION_OPT_IN='true';
    for(const key of aiKeys)envVars[key]=env[key];
    if(env.AI_REWRITE_OPT_IN==='true')envVars.AI_REWRITE_OPT_IN='true';
    if(env.AI_BLIND_REVIEW_OPT_IN==='true'){
     if(typeof env.AI_REVIEWER_MODEL!=='string'||!env.AI_REVIEWER_MODEL.trim()||env.AI_REVIEWER_MODEL===env.AI_GENERATOR_MODEL)
      return respond(503,origin,'{"error":"staging_not_configured"}');
     envVars.AI_BLIND_REVIEW_OPT_IN='true';
     envVars.AI_REVIEWER_MODEL=env.AI_REVIEWER_MODEL;
    }
    if(env.AI_GENERATION_CHECKPOINTS_ENABLED==='true')envVars.AI_GENERATION_CHECKPOINTS_ENABLED='true';
    if(env.AI_HYBRID_ENABLED==='true')envVars.AI_HYBRID_ENABLED='true';
   }
   await container.startAndWaitForPorts({startOptions:{envVars}});
   containerStage='upstream_request';
   let body;
   if(generation||generateOne||draftWrite){
    const reader=request.body?.getReader();
    if(!reader)return respond(400,origin,'{"error":"invalid_request"}');
    const chunks=[];let total=0;
    while(true){const {done,value}=await reader.read();if(done)break;total+=value.byteLength;
     if(total>8192){await reader.cancel();return respond(413,origin,'{"error":"request_too_large"}');}
     chunks.push(value);
    }
    const bytes=new Uint8Array(total);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
    body=new TextDecoder('utf-8',{fatal:true}).decode(bytes);
   }
   const upstream=await container.fetch(new Request('http://reviewer.internal'+url.pathname+url.search,{
    method:(generation||generateOne||draftWrite)?'POST':'GET',headers:{Authorization:token,Origin:ORIGIN,...((generation||generateOne||draftWrite)?{'Content-Type':'application/json'}:{})},...((generation||generateOne||draftWrite)?{body}:{})
   }));
   containerStage='upstream_response';
   if(upstream.status===500 && (generation||generateOne)){
    // Never log upstream response text: it could contain source excerpts or secrets.
    const contentType=(upstream.headers.get('Content-Type')||'').toLowerCase();
    const body=contentType.startsWith('application/json')?await upstream.clone().json().catch(()=>null):null;
    const allowedErrors=new Set(['generation_preflight_unavailable','generation_or_evidence_unavailable','reviewer_backend_unavailable','internal_server_error']);
    const allowedRules=new Set(['GENERATION_RUNTIME_ERROR','DEPENDENCY_UNAVAILABLE','UPSTREAM_CONNECTION','RUNTIME_IO','DATABASE_CONNECTION','DATABASE_TIMEOUT']);
    console.error('staging_reviewer_failure',JSON.stringify({stage:'backend',reason:'upstream_500',route:generation?'preflight':'generate_one',content_type:contentType.startsWith('application/json')?'json':'non_json',error:allowedErrors.has(body?.error)?body.error:'UNCLASSIFIED',rule:allowedRules.has(body?.rule)?body.rule:'UNCLASSIFIED'}));
   }
   if(upstream.status===503){
    const body=await upstream.clone().json().catch(()=>null);
    const allowed=new Set(['configuration','database','dependency','backend']);
    const category=body?.error==='reviewer_backend_unavailable'&&allowed.has(body?.stage)?body.stage:'unclassified';
    const rules=new Set(['STAGING_ONLY','MISSING_BINDING','PROJECT_URL','SIGNING_SECRET_LENGTH','DATABASE_URL_PARSE','DATABASE_SCHEME','DATABASE_HOST','DATABASE_CREDENTIAL_FORMAT','DATABASE_PROJECT_HOST','DATABASE_USERNAME','DATABASE_PATH','DATABASE_OPTIONS','MISSING_STAGING_DATABASE_URL','MISSING_STAGING_R2_ACCOUNT_ID','MISSING_STAGING_R2_ACCESS_KEY_ID','MISSING_STAGING_R2_SECRET_ACCESS_KEY','MISSING_SUPABASE_URL','MISSING_SUPABASE_ANON_KEY','MISSING_STAGING_RECEIPT_SIGNING_SECRET','DATABASE_PASSWORD_REJECTED','DATABASE_ROLE_OR_NAME','DATABASE_PERMISSION','DATABASE_CONNECTION','DATABASE_NETWORK_OR_TLS','DATABASE_OTHER','DATABASE_CAPACITY','DATABASE_NETWORK_UNREACHABLE','DATABASE_DNS','DATABASE_TIMEOUT','DATABASE_TLS','DATABASE_CONNECTION_REFUSED','DATABASE_ACCESS_POLICY']);
    const generationRules=new Set(['UPSTREAM_CONNECTION','UPSTREAM_HTTP','DEPENDENCY_UNAVAILABLE','RUNTIME_IO','GENERATION_RUNTIME_ERROR','PROVIDER_TRANSPORT','PROVIDER_RESPONSE','PROVIDER_AUTH','PROVIDER_FORBIDDEN','PROVIDER_RATE_LIMIT','PROVIDER_REQUEST_REJECTED','PROVIDER_UPSTREAM','PROVIDER_HTTP_OTHER','PROVIDER_TIMEOUT','PROVIDER_NETWORK','PROVIDER_INVALID_JSON','PROVIDER_REDIRECT','PROVIDER_ENDPOINT','PROVIDER_REQUEST','PROVIDER_REQUEST_SIZE','PROVIDER_RESPONSE_SIZE','RELAY_AUTH','RELAY_HTTP','RELAY_UNAVAILABLE','RELAY_NETWORK','RELAY_DISABLED','RELAY_UPSTREAM','RELAY_PAYLOAD','RELAY_METHOD','RELAY_SIZE','RELAY_EDGE_403',...([400,401,403,404,405,413,429,500,502,503,504,0].map(n=>'RELAY_HTTP_'+n))]);
    const safeErrors=new Set(['generation_preflight_unavailable','reviewer_backend_unavailable','staging_not_configured','provider_check_unavailable']);
    const error=safeErrors.has(body?.error)?body.error:'UNCLASSIFIED';
    const rule=body?.error==='generation_preflight_unavailable'&&generationRules.has(body?.rule)?body.rule:['configuration','database'].includes(category)&&rules.has(body?.rule)?body.rule:'NONE';
    console.error('staging_reviewer_failure',JSON.stringify({stage:'backend',reason:'upstream_503',category,error,rule}));
   }
   if(upstream.status===503){
    const body=await upstream.clone().json().catch(()=>null);
    if(body?.error==='trusted_review_unavailable'){
     const allowed=new Set(['STORAGE_UNKNOWN','STORAGE_MISSING_SOURCE_OR_QUEUE','STORAGE_CREDENTIALS_OR_PERMISSION','STORAGE_RATE_LIMIT','STORAGE_PROVIDER_ERROR','STORAGE_CONNECTION','STORAGE_DEPENDENCY']);
     const rule=allowed.has(body?.rule)?body.rule:'NONE';
     console.error('staging_reviewer_failure',JSON.stringify({stage:'storage',reason:'trusted_manifest_unavailable',rule}));
    }
   }
   if(upstream.status===409){
    const conflict=await upstream.clone().json().catch(()=>null);
    const category=typeof conflict?.error==='string'&&/^[a-z][a-z0-9_]{0,63}$/.test(conflict.error)?conflict.error:'unclassified';
    console.error('staging_reviewer_failure',JSON.stringify({stage:'manifest',reason:'upstream_409',category}));
   }
   const headers=new Headers(common);
   headers.set('Access-Control-Allow-Origin',ORIGIN);headers.set('Vary','Origin');
   headers.set('Access-Control-Expose-Headers','X-Review-Approval-Enabled, X-Verified-Source-SHA256, X-Page-Image-SHA256');
   for(const name of ['Content-Type','X-Verified-Source-SHA256','X-Page-Image-SHA256']){
    const value=upstream.headers.get(name);if(value)headers.set(name,value);
   }
   if(!generation&&!generateOne&&!draftRead&&!draftWrite&&!providerCheck&&!textbookList&&upstream.headers.get('X-Review-Approval-Enabled')!=='false')return respond(502,origin,'{"error":"unsafe_upstream"}');
   if(upstream.ok&&generation){
    if(!(upstream.headers.get('Content-Type')||'').startsWith('application/json'))return respond(502,origin,'{"error":"invalid_preflight_type"}');
    const data=await upstream.clone().json().catch(()=>null);
    if(data?.dry_run!==true||data?.can_publish!==false||data?.database_writes!==false||!Number.isSafeInteger(data?.passage_count))return respond(502,origin,'{"error":"unsafe_preflight"}');
   }
   if(upstream.ok&&generateOne){
    const data=await upstream.clone().json().catch(()=>null);
    if(!(upstream.headers.get('Content-Type')||'').startsWith('application/json')||data?.dry_run!==false||data?.can_publish!==false||data?.database_writes!==false||data?.requires_human_review!==true||!data?.item||typeof data.item!=='object')return respond(502,origin,'{"error":"unsafe_generation_response"}');
   }
   if(upstream.ok&&draftRead&&!draftWrite){
    if(!(upstream.headers.get('Content-Type')||'').startsWith('application/json'))return respond(502,origin,'{"error":"invalid_draft_type"}');
    const data=await upstream.clone().json().catch(()=>null);
    if(!data||typeof data!=='object'||data.published!==false&&!(Array.isArray(data.drafts)&&data.drafts.every(x=>x&&typeof x==='object'&&typeof x.draft_id==='string')))return respond(502,origin,'{"error":"unsafe_draft_response"}');
   }
   if(upstream.ok&&draftWrite){
    const data=await upstream.clone().json().catch(()=>null);
    if(!(upstream.headers.get('Content-Type')||'').startsWith('application/json')||!data||typeof data!=='object'||data.published===true||typeof data.draft_id!=='string'||!data.draft_id) return respond(502,origin,'{"error":"unsafe_draft_write"}');
   }
   if(upstream.ok&&!generation&&!generateOne&&!draftRead&&!draftWrite&&!providerCheck&&!textbookList){
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
   if(providerCheck){
    // The private reviewer performs its normal authorization check first. Only then
    // probe provider metadata endpoints; never call an inference/generation endpoint.
    const containerResult=upstream.ok?await upstream.clone().json().catch(()=>null):null;
    const unavailable=upstream.status===503?await upstream.clone().json().catch(()=>null):null;
    if(upstream.ok&&(containerResult?.check!=='groq_models_via_signed_relay'||!Number.isInteger(containerResult.provider_status)))
     return respond(502,origin,'{"error":"invalid_provider_check"}');
    if(!upstream.ok&&!(upstream.status===503&&unavailable?.error==='provider_check_unavailable'))
     return new Response(upstream.body,{status:upstream.status,headers});
    const probe=async(name,endpoint,headers)=>{
     if(!headers)return {provider:name,state:'NOT_CONFIGURED',generation_performed:false};
     try{
      const response=await fetch(endpoint,{method:'GET',headers,redirect:'manual',signal:AbortSignal.timeout(8000)});
      const status=response.status;await response.body?.cancel();
      return {provider:name,state:status===200?'OK':status===401?'AUTH':status===403?'FORBIDDEN':status===404?'NOT_FOUND':status===429?'RATE_LIMIT':status>=300&&status<400?'REDIRECT':'OTHER',generation_performed:false};
     }catch{return {provider:name,state:'NETWORK',generation_performed:false}}
    };
    const providers=await Promise.all([
     probe('gemini','https://generativelanguage.googleapis.com/v1beta/models',env.AI_HYBRID_ENABLED==='true'&&env.AI_GEMINI_API_KEY?{'x-goog-api-key':env.AI_GEMINI_API_KEY}:null),
     probe('groq','https://api.groq.com/openai/v1/models',env.AI_PROVIDER_API_KEY?{Authorization:'Bearer '+env.AI_PROVIDER_API_KEY}:null),
     probe('cloudflare','https://api.cloudflare.com/client/v4/accounts/'+encodeURIComponent(env.AI_CLOUDFLARE_ACCOUNT_ID||'')+'/ai/models/search',env.AI_HYBRID_ENABLED==='true'&&env.AI_CLOUDFLARE_API_TOKEN&&env.AI_CLOUDFLARE_ACCOUNT_ID?{Authorization:'Bearer '+env.AI_CLOUDFLARE_API_TOKEN}:null)
    ]);
    const relayRules=new Set(['CONFIGURATION','RELAY_EDGE_403','RELAY_EDGE_WAF_1020','RELAY_EDGE_CLOUDFLARE','RELAY_EDGE_ACCESS_DENIED','RELAY_NETWORK',...([0,400,401,403,404,405,413,429,500,502,503,504].map(n=>'RELAY_HTTP_'+n))]);
    const relayRule=relayRules.has(unavailable?.rule)?unavailable.rule:'UNCLASSIFIED';
    const relayOK=upstream.ok&&containerResult.provider_status===200;
    return respond(200,origin,JSON.stringify({check:'hybrid_provider_readiness',generation_performed:false,providers,container_relay:relayOK?'OK':'UNAVAILABLE',container_relay_rule:relayOK?'OK':upstream.ok?'PROVIDER_'+containerResult.provider_status:relayRule,metadata_ready:relayOK&&providers.every(provider=>provider.state==='OK'),generation_ready:false}));
   }
   return new Response(upstream.body,{status:upstream.status,headers});
  }catch(error){
   // Container runtime exceptions may contain sensitive details. Only emit fixed categories.
   const detail=String(error?.message||'').toLowerCase();
   const category=/no container instance.*provided|no container instance.*available|cannot.*provide.*container instance/.test(detail)?'instance_allocation_unavailable':
    /port|listen|connection refused/.test(detail)?'port_unavailable':
    /image|pull|registry/.test(detail)?'image_unavailable':
    /limit|quota|capacity|resource/.test(detail)?'capacity':
    /timeout|timed out/.test(detail)?'timeout':
    /secret|env|variable/.test(detail)?'environment':
    /not found|missing/.test(detail)?'missing_resource':
    /not running|stopped|crash|exit/.test(detail)?'process_exit':'unclassified';
   console.error('staging_reviewer_failure',JSON.stringify({stage:'container',reason:'startup_or_upstream_failed',substage:containerStage,category}));
   return respond(503,origin,'{"error":"reviewer_unavailable"}');
  }
 }
};

