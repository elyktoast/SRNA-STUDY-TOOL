import test from 'node:test';
import assert from 'node:assert/strict';
import {createHmac} from 'node:crypto';
import gateway from '../src/index.js';

const secret = 'staging-test-secret-0123456789-0123456789';
const env = {
  STAGING_ONLY: 'true', AI_GENERATION_OPT_IN: 'true',
  AI_PROVIDER_API_KEY: 'test-key', STAGING_RECEIPT_SIGNING_SECRET: secret,
  AI_GENERATOR_MODEL: 'generator-model', AI_REVIEWER_MODEL: 'reviewer-model',
  AI_BLIND_REVIEW_OPT_IN: 'true', AI_REWRITE_OPT_IN: 'true',
};
const endpoint = 'https://example.workers.dev/internal/groq-relay';
function embeddingRequest(payload,valid=true){
 const body=JSON.stringify(payload),stamp=String(Math.floor(Date.now()/1000));
 const signature=valid?createHmac('sha256',secret).update('srna-groq-relay-v1\n'+stamp+'\n'+body).digest('hex'):'0'.repeat(64);
 return new Request(endpoint,{method:'POST',headers:{'Content-Type':'application/json','X-Relay-Timestamp':stamp,'X-Relay-Signature':signature},body});
}
const embeddingPayload={task:'semantic_embeddings',model:'@cf/baai/bge-m3',text:['Synthetic question stem']};
test('semantic relay requires HMAC and separate opt-in before native model calls',async()=>{
 let calls=0;const ai={run:async()=>{calls++;throw Error('must not run');}};
 for(const [request,config,status] of [
  [embeddingRequest(embeddingPayload,false),{...env,AI_EMBEDDING_RELAY_OPT_IN:'true',SEMANTIC_AI:ai},403],
  [embeddingRequest(embeddingPayload),{...env,SEMANTIC_AI:ai},503],
  [embeddingRequest(embeddingPayload),{...env,AI_EMBEDDING_RELAY_OPT_IN:'true'},503],
 ])assert.equal((await gateway.fetch(request,config)).status,status);
 assert.equal(calls,0);
});
test('semantic relay bounds input, pins model and returns only validated vectors',async()=>{
 const vector=[1,...Array(1023).fill(0)],calls=[];
 const config={...env,AI_EMBEDDING_RELAY_OPT_IN:'true',SEMANTIC_AI:{run:async(model,body)=>{calls.push({model,body});return {data:[vector],private_provider_field:'never forward'};}}};
 const response=await gateway.fetch(embeddingRequest(embeddingPayload),config);
 assert.equal(response.status,200);assert.equal(response.headers.get('Cache-Control'),'private, no-store');
 assert.deepEqual(await response.json(),{model:embeddingPayload.model,shape:[1,1024],data:[vector]});
 assert.deepEqual(calls,[{model:embeddingPayload.model,body:{text:embeddingPayload.text}}]);
 for(const body of [{...embeddingPayload,model:'other-model'},{...embeddingPayload,text:['x'.repeat(10001)]},
  {...embeddingPayload,text:Array(33).fill('x')},{...embeddingPayload,text:Array(32).fill('x'.repeat(5000))},
  {...embeddingPayload,text:[...Array(31).fill('x'),'x'.repeat(3200)]},{...embeddingPayload,text:Array(16).fill('λ'.repeat(1600))},
  {...embeddingPayload,extra:'forbidden'},{...embeddingPayload,text:['']}]){
  assert.equal((await gateway.fetch(embeddingRequest(body),config)).status,400);
 }
 assert.equal(calls.length,1);
});
test('malformed native embedding results and provider failures fail closed without private diagnostics',async()=>{
 for(const result of [{data:[[1,0]]},{data:[Array(1024).fill(0)]},{data:[[NaN,...Array(1023).fill(0)]]},{data:[]}]){
  const config={...env,AI_EMBEDDING_RELAY_OPT_IN:'true',SEMANTIC_AI:{run:async()=>result}};
  const response=await gateway.fetch(embeddingRequest(embeddingPayload),config);
  assert.equal(response.status,502);assert.deepEqual(await response.json(),{error:'provider_failed',rule:'PROVIDER_UPSTREAM'});
 }
 const config={...env,AI_EMBEDDING_RELAY_OPT_IN:'true',SEMANTIC_AI:{run:async()=>{throw Error('private provider response');}}};
 const response=await gateway.fetch(embeddingRequest(embeddingPayload),config);
 assert.equal(response.status,503);assert.deepEqual(await response.json(),{error:'relay_network'});
 const context={...config,SEMANTIC_AI:{run:async()=>{throw Error('Max context reached 99488 tokens but model supports only 60000 private details');}}};
 const rejected=await gateway.fetch(embeddingRequest(embeddingPayload),context);
 assert.equal(rejected.status,413);assert.deepEqual(await rejected.json(),{error:'provider_failed',rule:'PROVIDER_REQUEST_REJECTED'});
});
test('429 diagnostics expose only fixed dimensions and bounded numbers; fractional waits round up',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>Response.json({error:{message:'Rate limit reached: tokens per day (TPD): Limit 200000, Used 199999, Requested 4000. private token and source text'}},{status:429,headers:{'Retry-After':'2.45','x-ratelimit-remaining-tokens':'8000'}});
 try{
  const response=await gateway.fetch(request('blind_review','reviewer-model'),env);
  assert.deepEqual(await response.json(),{error:'provider_failed',rule:'PROVIDER_RATE_LIMIT',provider_status:429,remaining_tokens:8000,rate_limit_dimension:'tokens_per_day',limit:200000,used:199999,requested:4000,retry_after_seconds:3});
 }finally{globalThis.fetch=original;}
});
test('missing Retry-After uses only an explicit bounded provider retry interval',async()=>{
 const original=globalThis.fetch;
 try{
  for(const [wait,expected] of [['25.123s',26],['12.123456789012345s',13],['0.000000000000001s',1],['500ms',1],['9999s',undefined]]){
   globalThis.fetch=async()=>Response.json({error:{message:'Tokens per minute (TPM). Please try again in '+wait+'. private source text'}},{status:429});
   const data=await (await gateway.fetch(request('blind_review','reviewer-model'),env)).json();
   assert.equal(data.retry_after_seconds,expected);
   assert.equal(data.rate_limit_dimension,'tokens_per_minute');
   assert.ok(!JSON.stringify(data).includes('private'));
  }
 }finally{globalThis.fetch=original;}
});
test('oversized and invalid upstream error bodies cannot become relay diagnostics',async()=>{
 const original=globalThis.fetch;
 try{
  for(const message of ['private'.repeat(1000),'not json']){
   globalThis.fetch=async()=>new Response(message,{status:429,headers:{'Retry-After':'invalid'}});
   const data=await (await gateway.fetch(request('blind_review','reviewer-model'),env)).json();
   assert.deepEqual(data,{error:'provider_failed',rule:'PROVIDER_RATE_LIMIT',provider_status:429});
  }
 }finally{globalThis.fetch=original;}
});
function request(step, model, options={}) {
  const body = JSON.stringify({
    model, max_tokens: 1024, temperature: 0.2,
    messages: [{role:'system',content:'Return JSON'},
      {role:'user',content:JSON.stringify({
        step, rules_version:'2.0', auto_publish:false,
        ...(['blind_review','option_review'].includes(step)?{blind:true}:{}),
        ...(['explanation_review','editorial_review','options_only_review'].includes(step)?{independent:true}:{}),
        ...(step==='explanation_review'?{fields:[{id:'e0',passage_ids:['s0']}],source_passages:[{passage_id:'s0',quote_spans:[{id:'q0',text:'Source fact'}]}]}:{}),
        ...(step==='options_only_review'?{format:'MC',select_count:1,options:['A','B','C','D'].map(id=>({id,text:'Choice '+id}))}:{}),
        ...options,
      })}],
  });
  const stamp = String(Math.floor(Date.now()/1000));
  const signature = createHmac('sha256',secret)
    .update('srna-groq-relay-v1\n'+stamp+'\n'+body).digest('hex');
  return new Request(endpoint,{method:'POST',headers:{
    'Content-Type':'application/json','X-Relay-Timestamp':stamp,
    'X-Relay-Signature':signature},body});
}
test('source explanation review requires its own flag and distinct reviewer identity',async()=>{
 const original=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});};
 try{
  assert.equal((await gateway.fetch(request('explanation_review','reviewer-model'),env)).status,400);
  const enabled={...env,AI_EXPLANATION_REVIEW_OPT_IN:'true'};
  assert.equal((await gateway.fetch(request('explanation_review','generator-model'),enabled)).status,400);
  assert.equal(calls,0);
  assert.equal((await gateway.fetch(request('explanation_review','reviewer-model'),enabled)).status,200);
  assert.equal(calls,1);
 }finally{globalThis.fetch=original;}
});
test('relay rejects swapped model identities before contacting provider', async () => {
  const original = globalThis.fetch;
  let calls=0;
  globalThis.fetch = async () => {calls++;throw Error('unexpected upstream');};
  try {
    for (const [step,model] of [['blind_review','generator-model'],
      ['item_draft','reviewer-model'],['rewrite','reviewer-model']]) {
      const response=await gateway.fetch(request(step,model),env);
      assert.equal(response.status,400,step);
    }
    assert.equal(calls,0);
  } finally {globalThis.fetch=original;}
});
test('relay accepts opted-in rewrite and independent review',async()=>{
  const original=globalThis.fetch;
  const calls=[];
  globalThis.fetch=async (url,options)=>{
    calls.push({url:String(url),options});
    return new Response(JSON.stringify({choices:[{message:{content:'{}'}}]}),
      {status:200,headers:{'Content-Type':'application/json'}});
  };
  try {
    for(const [step,model] of [['rewrite','generator-model'],
      ['blind_review','reviewer-model']]) {
      const response=await gateway.fetch(request(step,model),env);
      assert.equal(response.status,200,step);
    }
    assert.equal(calls.length,2);
  } finally {globalThis.fetch=original;}
});
test('disabled optional review steps cannot contact provider',async()=>{
  const original=globalThis.fetch;
  let calls=0;globalThis.fetch=async()=>{calls++;throw Error('unexpected');};
  try {
    assert.equal((await gateway.fetch(request('rewrite','generator-model'),
      {...env,AI_REWRITE_OPT_IN:'false'})).status,400);
    assert.equal((await gateway.fetch(request('blind_review','reviewer-model'),
      {...env,AI_BLIND_REVIEW_OPT_IN:'false'})).status,400);
    assert.equal(calls,0);
  } finally {globalThis.fetch=original;}
});

test('relay classifies outbound network exceptions without exposing exception text',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>{throw new TypeError('private token should never be exposed');};
 try{
  const response=await gateway.fetch(request('item_draft','generator-model'),env);
  assert.equal(response.status,503);
  const body=await response.json();
  assert.equal(body.error,'relay_network');
  assert.equal(body.category,'network');
  assert.equal(JSON.stringify(body).includes('private token'),false);
 }finally{globalThis.fetch=original;}
});



const cloudflareEnv={...env,AI_HYBRID_ENABLED:'true',
 AI_CLOUDFLARE_ACCOUNT_ID:'test-account',AI_CLOUDFLARE_API_TOKEN:'test-token',
 AI_CLOUDFLARE_MODEL:'@cf/qwen/qwen3.8-27b'};
test('concept card uses Cloudflare AI, never Gemini',async()=>{
 const original=globalThis.fetch,urls=[];
 globalThis.fetch=async(url)=>{urls.push(String(url));return new Response(JSON.stringify({result:{response:'{}'}}),{status:200});};
 try{
  const response=await gateway.fetch(request('concept_card','generator-model'),cloudflareEnv);
  assert.equal(response.status,200);
  assert.equal(urls.length,1);
  assert.ok(urls[0].includes('/ai/run/@cf/qwen/qwen3.8-27b'));
  assert.ok(!urls[0].includes('googleapis'));
 }finally{globalThis.fetch=original;}
});
test('concept card works without Gemini credentials',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>new Response(JSON.stringify({result:{response:'{}'}}),{status:200});
 try{assert.equal((await gateway.fetch(request('concept_card','generator-model'),cloudflareEnv)).status,200)}
 finally{globalThis.fetch=original;}
});
test('Qwen JSON steps preserve roles and disable budget-consuming thinking',async()=>{
 const original=globalThis.fetch,calls=[];
 globalThis.fetch=async(url,options)=>{
  calls.push({url:String(url),body:JSON.parse(options.body)});
  return Response.json({success:true,result:{choices:[{message:{content:'{}'},finish_reason:'stop'}]}});
 };
 try{
  for(const step of ['concept_card'])assert.equal((await gateway.fetch(request(step,'generator-model'),cloudflareEnv)).status,200);
  for(const {body} of calls){
   assert.equal(body.messages[0].role,'system');
   assert.equal(body.messages[1].role,'user');
   assert.deepEqual(body.chat_template_kwargs,{enable_thinking:false});
   assert.deepEqual(body.response_format,{type:'json_object'});
   assert.equal(body.max_tokens,1024);
  }
 }finally{globalThis.fetch=original;}
});
test('rationale uses bounded Groq JSON rather than the slow Cloudflare route',async()=>{
 const original=globalThis.fetch; let calls=0;
 globalThis.fetch=async(url,options)=>{
  calls++; assert.ok(String(url).includes('api.groq.com'));
  const body=JSON.parse(options.body);
  assert.equal(JSON.parse(body.messages[1].content).step,'rationale');
  assert.equal(body.reasoning_effort,'medium');
  assert.deepEqual(body.response_format,{type:'json_object'});
  assert.equal(body.chat_template_kwargs,undefined);
  return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});
 };
 try{assert.equal((await gateway.fetch(request('rationale','openai/gpt-oss-120b'),{...cloudflareEnv,AI_GENERATOR_MODEL:'openai/gpt-oss-120b'})).status,200);assert.equal(calls,1);}
 finally{globalThis.fetch=original;}
});
test('Groq drafting retains original request without Qwen-specific settings',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async(url,options)=>{
  assert.ok(String(url).includes('api.groq.com'));
  const body=JSON.parse(new TextDecoder().decode(options.body));
  assert.equal(body.chat_template_kwargs,undefined);
  assert.equal(body.response_format,undefined);
  return Response.json({choices:[{message:{content:'{}'}}]});
 };
 try{assert.equal((await gateway.fetch(request('item_draft','generator-model'),cloudflareEnv)).status,200);}
 finally{globalThis.fetch=original;}
});
test('GPT-OSS drafting and rewriting request bounded JSON with medium authoring effort',async()=>{
 const original=globalThis.fetch;
 const model='openai/gpt-oss-120b';
 globalThis.fetch=async(url,options)=>{
  assert.ok(String(url).includes('api.groq.com'));
  const body=JSON.parse(options.body);
  assert.deepEqual(body.response_format,{type:'json_object'});
  assert.equal(body.reasoning_effort,'medium');
  assert.equal(body.max_tokens,1024);
  assert.equal(body.chat_template_kwargs,undefined);
  return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});
 };
 try{
  for(const step of ['item_draft','rewrite'])assert.equal((await gateway.fetch(request(step,model),{...cloudflareEnv,AI_GENERATOR_MODEL:model})).status,200);
 }finally{globalThis.fetch=original;}
});
test('Groq truncated JSON is rejected before reaching the Python JSON parser',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>Response.json({choices:[{message:{content:'{"stem":'},finish_reason:'length'}]});
 try{
  const response=await gateway.fetch(request('item_draft','generator-model'),env);
  assert.equal(response.status,502);
  assert.equal((await response.json()).reason,'provider_incomplete');
 }finally{globalThis.fetch=original;}
});
test('distinct Groq Qwen blind reviewer requests JSON without GPT-specific reasoning controls',async()=>{
 const original=globalThis.fetch,model='qwen/qwen3.8-27b';
 globalThis.fetch=async(url,options)=>{
  assert.ok(String(url).includes('api.groq.com'));
  const body=JSON.parse(options.body);
  assert.deepEqual(body.response_format,{type:'json_object'});
  assert.equal(body.reasoning_effort,undefined);
  assert.equal(JSON.parse(body.messages[1].content).blind,true);
  return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});
 };
 try{assert.equal((await gateway.fetch(request('blind_review',model),{...cloudflareEnv,AI_REVIEWER_MODEL:model})).status,200);}
 finally{globalThis.fetch=original;}
});
test('Cloudflare model 404 does not retry or call Gemini',async()=>{
 const original=globalThis.fetch,urls=[];
 globalThis.fetch=async(url)=>{urls.push(String(url));return new Response('{}',{status:404});};
 try{
  const response=await gateway.fetch(request('concept_card','generator-model'),cloudflareEnv);
  assert.equal((await response.json()).rule,'PROVIDER_MODEL_UNAVAILABLE');
  assert.equal(urls.length,1);
 }finally{globalThis.fetch=original;}
});

const qwenEnv={...env,AI_HYBRID_ENABLED:'true',
 AI_CLOUDFLARE_ACCOUNT_ID:'test-account',AI_CLOUDFLARE_API_TOKEN:'test-token',
 AI_CLOUDFLARE_MODEL:'@cf/qwen/qwen3.8-27b'};
async function qwenMock(result,status=200){
 const original=globalThis.fetch;
 globalThis.fetch=async()=>new Response(JSON.stringify(result),{status});
 try{return await gateway.fetch(request('concept_card','generator-model'),qwenEnv)}
 finally{globalThis.fetch=original}
}
test('Qwen 3.8 choices message content is returned to pipeline',async()=>{
 const response=await qwenMock({success:true,result:{choices:[{message:{role:'assistant',content:'{"topic":"airway"}'},finish_reason:'stop'}]}});
 assert.equal(response.status,200);
 assert.equal((await response.json()).choices[0].message.content,'{"topic":"airway"}');
});
test('legacy Workers AI response format still supported',async()=>{
 const response=await qwenMock({success:true,result:{response:'{"topic":"legacy"}'}});
 assert.equal(response.status,200);
});
test('Qwen refusal is rejected',async()=>{
 const response=await qwenMock({success:true,result:{choices:[{message:{content:'no',refusal:'blocked'},finish_reason:'stop'}]}});
 assert.equal((await response.json()).reason,'provider_refusal');
});
test('Qwen token-truncated generation is rejected',async()=>{
 const response=await qwenMock({success:true,result:{choices:[{message:{content:'partial'},finish_reason:'length'}]}});
 assert.equal((await response.json()).reason,'provider_incomplete');
});
test('Qwen empty output is rejected',async()=>{
 const response=await qwenMock({success:true,result:{choices:[{message:{content:'   '},finish_reason:'stop'}]}});
 assert.equal((await response.json()).reason,'provider_empty_content');
});
test('Qwen provider envelope failure is rejected',async()=>{
 const response=await qwenMock({success:false,result:{choices:[{message:{content:'bad'},finish_reason:'stop'}]}});
 assert.equal((await response.json()).reason,'provider_envelope_failed');
});
test('Qwen oversized content is rejected',async()=>{
 const response=await qwenMock({success:true,result:{choices:[{message:{content:'a'.repeat(262145)},finish_reason:'stop'}]}});
 assert.equal(response.status,502);
});
test('Qwen malformed JSON response is rejected',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>new Response('not json',{status:200});
 try{const response=await gateway.fetch(request('concept_card','generator-model'),qwenEnv);assert.equal(response.status,502)}
 finally{globalThis.fetch=original}
});
test('Qwen 503 includes sanitized provider HTTP status',async()=>{
 const response=await qwenMock({errors:[]},503);
 const body=await response.json();assert.equal(body.provider_status,503);assert.equal(body.rule,'PROVIDER_UPSTREAM');
});
test('Qwen successful content does not leak reasoning metadata',async()=>{
 const response=await qwenMock({success:true,result:{choices:[{message:{content:'final',reasoning:'private chain'},finish_reason:'stop'}]}});
 const body=await response.json();assert.equal(body.choices[0].message.content,'final');assert.ok(!JSON.stringify(body).includes('private chain'));
});

test('independent option review requires explicit flag and distinct reviewer identity',async()=>{
 const original=globalThis.fetch; let calls=0;
 globalThis.fetch=async()=>{calls++;return new Response(JSON.stringify({choices:[{message:{content:'{}'}}]}),{status:200});};
 try{
  assert.equal((await gateway.fetch(request('option_review','reviewer-model'),env)).status,400);
  assert.equal((await gateway.fetch(request('option_review','generator-model'),{...env,AI_OPTION_REVIEW_OPT_IN:'true'})).status,400);
  assert.equal(calls,0);
  assert.equal((await gateway.fetch(request('option_review','reviewer-model'),{...env,AI_OPTION_REVIEW_OPT_IN:'true'})).status,200);
  assert.equal(calls,1);
 }finally{globalThis.fetch=original;}
});

test('Groq-only authoring mode keeps all three calls on the existing JSON route',async()=>{
 const original=globalThis.fetch; const steps=[];
 globalThis.fetch=async(url,options)=>{
  assert.ok(String(url).includes('api.groq.com'));
  const body=JSON.parse(options.body); steps.push(JSON.parse(body.messages[1].content).step);
  const step=JSON.parse(body.messages[1].content).step;
  assert.equal(body.response_format.type,step==='concept_card'?'json_schema':'json_object'); assert.equal(body.reasoning_effort,'medium');
  return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});
 };
 try{
  for(const step of ['concept_card','item_draft','rationale'])assert.equal((await gateway.fetch(request(step,'openai/gpt-oss-120b'),{...cloudflareEnv,AI_HYBRID_ENABLED:'false',AI_GENERATOR_MODEL:'openai/gpt-oss-120b'})).status,200);
  assert.deepEqual(steps,['concept_card','item_draft','rationale']);
 }finally{globalThis.fetch=original;}
});

test('Qwen explanation audit preserves the established JSON request settings',async()=>{
 const original=globalThis.fetch,model='qwen/qwen3.8-27b',seen=[];
 globalThis.fetch=async(url,options)=>{seen.push(JSON.parse(options.body));return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});};
 try{
  const configured={...env,AI_REVIEWER_MODEL:model,AI_EXPLANATION_REVIEW_OPT_IN:'true',AI_OPTION_REVIEW_OPT_IN:'true'};
  for(const step of ['blind_review','option_review','explanation_review'])assert.equal((await gateway.fetch(request(step,model),configured)).status,200);
  assert.equal(seen[0].reasoning_effort,undefined);
  assert.equal(seen[1].reasoning_effort,undefined);
  assert.equal(seen[2].reasoning_effort,undefined);
 }finally{globalThis.fetch=original;}
});

test('editorial and options-only checks require their own authorized distinct reviewers',async()=>{
 const original=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});};
 try{
  const configured={...env,AI_EXPLANATION_REVIEW_OPT_IN:'true',AI_EDITORIAL_REVIEWER_MODEL:'editorial-model'};
  for(const [step,model] of [['editorial_review','editorial-model'],['options_only_review','reviewer-model']]){
   assert.equal((await gateway.fetch(request(step,'generator-model'),configured)).status,400);
   assert.equal((await gateway.fetch(request(step,model,{independent:false}),configured)).status,400);
  }
  assert.equal((await gateway.fetch(request('editorial_review','reviewer-model'),configured)).status,400);
  assert.equal((await gateway.fetch(request('blind_review','editorial-model'),configured)).status,400);
  assert.equal((await gateway.fetch(request('editorial_review','editorial-model'),env)).status,400);
  assert.equal((await gateway.fetch(request('options_only_review','reviewer-model'),{...configured,AI_BLIND_REVIEW_OPT_IN:'false'})).status,400);
  assert.equal(calls,0);
  for(const [step,model] of [['editorial_review','editorial-model'],['options_only_review','reviewer-model']])assert.equal((await gateway.fetch(request(step,model),configured)).status,200);
  assert.equal(calls,2);
 }finally{globalThis.fetch=original;}
});

test('authoring effort never changes editorial or independent Qwen settings',async()=>{
 const original=globalThis.fetch,seen=[];
 globalThis.fetch=async(url,options)=>{seen.push(JSON.parse(options.body));return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});};
 try{
  const configured={...env,AI_GENERATOR_MODEL:'openai/gpt-oss-120b',AI_REVIEWER_MODEL:'qwen/qwen3.8-27b',AI_EDITORIAL_REVIEWER_MODEL:'openai/gpt-oss-20b',AI_EXPLANATION_REVIEW_OPT_IN:'true'};
  assert.equal((await gateway.fetch(request('editorial_review','openai/gpt-oss-20b'),configured)).status,200);
  assert.equal((await gateway.fetch(request('blind_review','qwen/qwen3.8-27b'),configured)).status,200);
  assert.equal(seen[0].reasoning_effort,'low');
  assert.equal(seen[1].reasoning_effort,undefined);
  assert.ok(seen.every(b=>b.max_tokens===1024));
 }finally{globalThis.fetch=original;}
});

test('request rejection exposes only fixed provider codes and parameter names',async()=>{
 const original=globalThis.fetch;
 try{
  for(const [error,expected] of [
   [{code:'json_validate_failed',message:'private',failed_generation:'private question'},{provider_error_code:'json_validate_failed',failed_generation_chars:16,failed_json_shape:'invalid_json'}],
   [{code:'json_validate_failed',failed_generation:JSON.stringify({core_concept:'private',rationale:'private',private:'private'})},{provider_error_code:'json_validate_failed',failed_generation_chars:JSON.stringify({core_concept:'private',rationale:'private',private:'private'}).length,failed_json_shape:'object',failed_known_fields:['core_concept','rationale'],failed_unknown_field_count:1}],
   [{code:'private credential',param:'private source',message:'secret'},{}],
   [{code:'invalid_request_error',param:'reasoning_effort',message:'secret'},{provider_error_code:'invalid_request_error',provider_error_param:'reasoning_effort'}]]){
   globalThis.fetch=async()=>Response.json({error},{status:400});
   const data=await (await gateway.fetch(request('concept_card','generator-model'),env)).json();
   assert.deepEqual(data,{error:'provider_failed',rule:'PROVIDER_REQUEST_REJECTED',provider_status:400,...expected});
   assert.ok(!JSON.stringify(data).includes('private'));
  }
 }finally{globalThis.fetch=original;}
});

test('concept planning constrains only canonical fields and preserves untrusted evidence in user role',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async(url,options)=>{
  const body=JSON.parse(options.body),schema=body.response_format.json_schema;
  assert.equal(schema.strict,true);
  assert.equal(schema.schema.additionalProperties,false);
  assert.deepEqual(new Set(schema.schema.required),new Set(['objective','mechanism','relevance','misconception','counterfactual','evidence_ids']));
  assert.deepEqual(Object.keys(schema.schema.properties).sort(),[...schema.schema.required].sort());
  assert.deepEqual(schema.schema.properties.evidence_ids,{type:'array',items:{type:'string'}});
  assert.equal(body.messages[0].role,'system');
  assert.equal(JSON.parse(body.messages[1].content).evidence[0].excerpt,'untrusted textbook text');
  assert.ok(!body.messages[0].content.includes('untrusted textbook text'));
  return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});
 };
 try{assert.equal((await gateway.fetch(request('concept_card','openai/gpt-oss-120b',{evidence:[{excerpt:'untrusted textbook text'}]}),{...env,AI_GENERATOR_MODEL:'openai/gpt-oss-120b'})).status,200);}
 finally{globalThis.fetch=original;}
});

test('MC rationale requires every option explanation and a bounded-edit proposal in its output schema',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async(url,options)=>{
  const body=JSON.parse(options.body),schema=body.response_format.json_schema;
  assert.equal(schema.name,'srna_rationale_with_counterfactual_v2');
  assert.equal(schema.strict,true);
  assert.deepEqual(schema.schema.required,['core_concept','why_key_wins','trap','distractor_breakdown','counterfactual_test']);
  assert.deepEqual(schema.schema.properties.distractor_breakdown.required,['A','B','C','D']);
  assert.equal(schema.schema.properties.distractor_breakdown.additionalProperties,false);
  const proposal=schema.schema.properties.counterfactual_test;
  assert.deepEqual(proposal.required,['from_text','to_text','expected_key']);
  assert.equal(proposal.additionalProperties,false);
  assert.deepEqual(proposal.properties.expected_key.items.enum,['A','B','C','D']);
  assert.equal(body.reasoning_effort,'medium');
  return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});
 };
 try{assert.equal((await gateway.fetch(request('rationale','openai/gpt-oss-120b',{format:'MC',draft:{options:['A','B','C','D'].map(id=>({id,text:id}))}}),{...env,AI_GENERATOR_MODEL:'openai/gpt-oss-120b'})).status,200);}
 finally{globalThis.fetch=original;}
});

test('MC planning has a private distinct-response plan while generic concept cards retain six canonical fields',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async(url,options)=>{
  const body=JSON.parse(options.body),s=body.response_format.json_schema.schema;
  assert.ok(s.required.includes('choice_plan'));
  assert.equal(s.properties.choice_plan.additionalProperties,false);
  assert.deepEqual(s.properties.choice_plan.required,['response_variables','stem_condition','alternate_condition','lead_in','key','alternate_key','options','option_grounding']);
  assert.equal(s.properties.choice_plan.properties.options.items.additionalProperties,false);
  assert.deepEqual(s.properties.choice_plan.properties.options.items.required,['id','states']);
  return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});
 };
 try{assert.equal((await gateway.fetch(request('concept_card','openai/gpt-oss-120b',{format:'MC'}),{...env,AI_GENERATOR_MODEL:'openai/gpt-oss-120b'})).status,200);}
 finally{globalThis.fetch=original;}
});

test('planned MC rationale preserves the bound counterfactual and requests only canonical explanations',async()=>{
 const original=globalThis.fetch;
 for(const format of ['MC','MS']){
  globalThis.fetch=async(url,options)=>{
   const s=JSON.parse(options.body).response_format.json_schema.schema;
   assert.equal(s.additionalProperties,false);
   assert.deepEqual(s.properties.distractor_breakdown.required,['A','B','C','D']);
   if(format==='MC'){
    assert.deepEqual(s.required,['core_concept','why_key_wins','trap','distractor_breakdown']);
    assert.equal(s.properties.counterfactual_test,undefined);
   }else assert.ok(s.required.includes('counterfactual_test'));
   return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});
  };
  try{assert.equal((await gateway.fetch(request('rationale','openai/gpt-oss-120b',{format,choice_plan:{},draft:{options:['A','B','C','D'].map(id=>({id,text:id}))}}),{...env,AI_GENERATOR_MODEL:'openai/gpt-oss-120b'})).status,200);}
  finally{globalThis.fetch=original;}
 }
});

test('explicit Cloudflare GPT-OSS authoring keeps every independent review on Groq',async()=>{
 const old=globalThis.fetch;
 const cf={...env,AI_GENERATOR_MODEL:'openai/gpt-oss-120b',AI_REVIEWER_MODEL:'qwen/qwen3.8-27b',AI_AUTHORING_PROVIDER:'cloudflare',
  AI_CLOUDFLARE_ACCOUNT_ID:'account',AI_CLOUDFLARE_API_TOKEN:'cf-secret',AI_CLOUDFLARE_MODEL:'@cf/openai/gpt-oss-120b',
  AI_OPTION_REVIEW_OPT_IN:'true',AI_EXPLANATION_REVIEW_OPT_IN:'true',AI_EDITORIAL_REVIEWER_MODEL:'openai/gpt-oss-20b'};
 try{
  for(const step of ['concept_card','item_draft','rationale','rewrite']){
   globalThis.fetch=async(url,options)=>{
    assert.equal(url,'https://api.cloudflare.com/client/v4/accounts/account/ai/run/@cf/openai/gpt-oss-120b');
    const body=JSON.parse(options.body);
    assert.equal(body.messages[0].role,'system');assert.equal(body.messages[1].role,'user');
    assert.equal(body.reasoning_effort,'medium');assert.equal(body.max_tokens,1024);
    if(['concept_card','rationale'].includes(step)){
     assert.equal(body.response_format.type,'json_schema');
     const schema=body.response_format.json_schema;
     assert.equal(schema.type,'object');assert.equal(schema.additionalProperties,false);
     assert.equal(schema.schema,undefined,'Cloudflare takes the raw schema, not the Groq schema envelope');
     if(step==='concept_card')assert.ok(schema.required.includes('choice_plan'));
     else assert.deepEqual(schema.required,['core_concept','why_key_wins','trap','distractor_breakdown']);
    }else assert.deepEqual(body.response_format,{type:'json_object'});
    return Response.json({success:true,result:{choices:[{message:{content:'{}'},finish_reason:'stop'}]}});
   };
   assert.equal((await gateway.fetch(request(step,'openai/gpt-oss-120b',{format:'MC',choice_plan:{},draft:{options:['A','B','C','D'].map(id=>({id,text:id}))}}),cf)).status,200);
  }
  for(const step of ['blind_review','option_review','explanation_review','editorial_review','options_only_review']){
   const model=step==='editorial_review'?'openai/gpt-oss-20b':'qwen/qwen3.8-27b';
   globalThis.fetch=async(url,options)=>{
    assert.equal(url,'https://api.groq.com/openai/v1/chat/completions');
    assert.equal(JSON.parse(options.body).model,model);
    return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});
   };
   assert.equal((await gateway.fetch(request(step,model),cf)).status,200);
  }
 }finally{globalThis.fetch=old;}
});
test('Cloudflare authoring cannot disguise a different underlying generator model',async()=>{
 const old=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;return Response.json({});};
 try{
  const response=await gateway.fetch(request('concept_card','openai/gpt-oss-120b'),{...env,
   AI_GENERATOR_MODEL:'openai/gpt-oss-120b',AI_AUTHORING_PROVIDER:'cloudflare',
   AI_CLOUDFLARE_MODEL:'@cf/qwen/qwen3.8-27b',AI_CLOUDFLARE_ACCOUNT_ID:'account',AI_CLOUDFLARE_API_TOKEN:'secret'});
  assert.equal(response.status,503);assert.equal(calls,0);
 }finally{globalThis.fetch=old;}
});

test('Cloudflare GLM uses its wrapped schema and bounded low reasoning without changing review delivery',async()=>{
 const old=globalThis.fetch;
 const cfg={...env,AI_REVIEWER_MODEL:'qwen/qwen3.8-27b',AI_GENERATOR_MODEL:'zai-org/glm-5.3',AI_AUTHORING_PROVIDER:'cloudflare',
  AI_CLOUDFLARE_ACCOUNT_ID:'account',AI_CLOUDFLARE_API_TOKEN:'cf-secret',AI_CLOUDFLARE_MODEL:'@cf/zai-org/glm-5.3'};
 try{
  for(const step of ['concept_card','item_draft','rationale','rewrite','blind_review']){
   globalThis.fetch=async(url,options)=>{
    const body=JSON.parse(options.body);
    if(step==='blind_review')assert.equal(url,'https://api.groq.com/openai/v1/chat/completions');
    else {
     assert.ok(url.endsWith('/ai/run/@cf/zai-org/glm-5.3'));
     assert.equal(body.reasoning_effort,'low');assert.equal(body.max_tokens,1024);
     if(step==='concept_card'){
      assert.equal(body.response_format.type,'json_schema');
      assert.equal(body.response_format.json_schema.name,'srna_concept_card_v2');
      assert.ok(body.response_format.json_schema.schema.required.includes('choice_plan'));
     }
    }
    return Response.json(step==='blind_review'?{choices:[{message:{content:'{}'},finish_reason:'stop'}]}:
     {success:true,result:{choices:[{message:{content:'{}'},finish_reason:'stop'}]}});
   };
   assert.equal((await gateway.fetch(request(step,step==='blind_review'?'qwen/qwen3.8-27b':'zai-org/glm-5.3',{format:'MC'}),cfg)).status,200);
  }
 }finally{globalThis.fetch=old;}
});

test('source explanation schema requires references for support but permits every field to be rejected',async()=>{
 const old=globalThis.fetch;
 const cfg={...env,AI_REVIEWER_MODEL:'qwen/qwen3.8-27b',AI_EXPLANATION_REVIEW_OPT_IN:'true'};
 try{
  globalThis.fetch=async(url,options)=>{
   assert.equal(url,'https://api.groq.com/openai/v1/chat/completions');
   const f=JSON.parse(options.body).response_format;
   assert.equal(f.type,'json_schema');assert.equal(f.json_schema.strict,true);
   const p=f.json_schema.schema.properties.judgments;
   assert.deepEqual(p.required,['e0','e1']);
   for(const field of Object.values(p.properties)){
    assert.deepEqual(field.properties.supported.type,['boolean','null']);
    assert.deepEqual(field.properties.quote_refs.type,['array','null']);
    assert.equal(field.properties.quote_refs.minItems,1);
    assert.deepEqual(field.properties.quote_refs.items.enum,['s0:q0']);
   }
   return Response.json({choices:[{message:{content:JSON.stringify({judgments:{e0:{supported:false,quote_refs:null,reason:'Not established'},e1:{supported:null,quote_refs:null,reason:'Uncertain'}}})},finish_reason:'stop'}]});
  };
  const r=await gateway.fetch(request('explanation_review','qwen/qwen3.8-27b',{fields:[{id:'e0',passage_ids:['s0']},{id:'e1',passage_ids:['s0']}],source_passages:[{passage_id:'s0',quote_spans:[{id:'q0',text:'Source statement'}]}]}),cfg);
  assert.equal(r.status,200);assert.deepEqual(JSON.parse((await r.json()).choices[0].message.content).judgments.e0.supported,false);
 }finally{globalThis.fetch=old;}
});

test('MC option review binds every option to its own passage and each passage to its own spans',async()=>{
 const old=globalThis.fetch;
 const model='qwen/qwen3.8-27b',ids=[...'ABCD'];
 const cfg={...env,AI_REVIEWER_MODEL:model,AI_OPTION_REVIEW_OPT_IN:'true'};
 const sources=[{passage_id:'s0',quote_spans:[{id:'q0',text:'Source statement'}]},
  {passage_id:'s1',quote_spans:[{id:'q1',text:'Another definition'}]}];
 const audits=ids.map((id,i)=>({option_id:id,retrieved_passage_ids:[i%2?'s1':'s0']}));
 let calls=0;
 try{
  globalThis.fetch=async(_url,options)=>{
   calls++;
   const {json_schema}=JSON.parse(options.body).response_format;
   assert.equal(json_schema.strict,true);
   const judgments=json_schema.schema.properties.judgments;
   assert.equal(judgments.type,'object');assert.equal(judgments.additionalProperties,false);
   assert.deepEqual(judgments.required,ids);
   for(const [i,id] of ids.entries()){
    const entry=judgments.properties[id];
     assert.equal(entry.additionalProperties,false);
     assert.equal(entry.anyOf,undefined);
     assert.deepEqual(entry.properties.answers_stem.type,['boolean','null']);
     assert.deepEqual(entry.properties.quote_refs.type,['array','null']);
     assert.equal(entry.properties.quote_refs.minItems,1);
     assert.equal(entry.properties.quote_refs.maxItems,8);
     assert.equal(entry.properties.verdict,undefined);
     assert.equal(entry.properties.option_id,undefined);assert.equal(entry.properties.passage_ids,undefined);
      const refs=entry.properties.quote_refs.items;
      assert.equal(refs.type,'string');
      assert.deepEqual(refs.enum,[i%2?'s1:q1':'s0:q0']);
     assert.ok(entry.required.includes('source_conflict_found'));
   }
   const output={judgments:Object.fromEntries(ids.map(id=>[id,{answers_stem:null,quote_refs:null,explanation:'Evidence insufficient',source_conflict_found:false}]))};
   return Response.json({choices:[{message:{content:JSON.stringify(output)},finish_reason:'stop'}]});
  };
  const step={format:'MC',options:ids.map(id=>({id,text:id})),source_passages:sources,retrieval:{option_audits:audits}};
  assert.equal((await gateway.fetch(request('option_review',model,step),cfg)).status,200);
  // Incomplete, duplicate or out-of-packet mappings must fail before provider use.
  for(const broken of [audits.slice(1),[audits[0],audits[0],audits[2],audits[3]],
    audits.map((a,i)=>i===0?{...a,retrieved_passage_ids:['unknown']}:a)]){
   assert.equal((await gateway.fetch(request('option_review',model,{...step,retrieval:{option_audits:broken}}),cfg)).status,400);
  }
  assert.equal(calls,1);
 }finally{globalThis.fetch=old;}
});

test('review approval and acknowledgment remain blocked at public gateway',async()=>{
 const reviewer={...env,SUPABASE_URL:'https://xqyasyambwdyhsjkftqu.supabase.co',
   SUPABASE_ANON_KEY:'test-anon',REVIEWER_CONTAINER:{fetch:async()=>{throw Error('private endpoint reached')}}};
 for(const path of ['/review/approve','/review/acknowledge']){
  const result=await gateway.fetch(new Request('https://staging.example'+path,{
   method:'POST',headers:{Origin:'https://staging.srnastudytool.com',
     Authorization:'Bearer test','Content-Type':'application/json'},body:'{}'}),reviewer);
  assert.equal(result.status,403,path);
 }
});

test('acknowledgment is disabled by default and approval is never public',async()=>{
 let backendCalls=0;
 const reviewer={...env,SUPABASE_URL:'https://xqyasyambwdyhsjkftqu.supabase.co',
   SUPABASE_ANON_KEY:'test-anon',REVIEWER_CONTAINER:{fetch:async()=>{backendCalls++;throw Error('private endpoint reached')}}};
 const make=(path)=>new Request('https://staging.example'+path,{
   method:'POST',headers:{Origin:'https://staging.srnastudytool.com',
     Authorization:'Bearer test','Content-Type':'application/json'},body:'{}'});
 const ack=await gateway.fetch(make('/review/acknowledge'),reviewer);
 assert.equal(ack.status,403);
 assert.equal((await ack.json()).error,'acknowledgment_disabled');
 assert.equal((await gateway.fetch(make('/review/approve'),
   {...reviewer,STAGING_ACKNOWLEDGMENT_ENABLED:'true'})).status,403);
 assert.equal(backendCalls,0);
});

test('opted-in acknowledgment authenticates, forwards only expected body and rejects unsafe upstream receipt',async()=>{
 const oldFetch=globalThis.fetch;
 const forwarded=[];
 const container={
   startAndWaitForPorts:async()=>{},
   fetch:async req=>{
     forwarded.push({path:new URL(req.url).pathname,method:req.method,body:await req.text()});
     return Response.json({receipt:'x'.repeat(80),approved:false},{headers:{'X-Review-Approval-Enabled':'false'}});
   }
 };
 const reviewer={...env,STAGING_ACKNOWLEDGMENT_ENABLED:'true',
   SUPABASE_URL:'https://xqyasyambwdyhsjkftqu.supabase.co',SUPABASE_ANON_KEY:'test-anon',
   STAGING_DATABASE_URL:'test-db',STAGING_R2_ACCOUNT_ID:'test-account',
   STAGING_R2_ACCESS_KEY_ID:'test-id',STAGING_R2_SECRET_ACCESS_KEY:'test-secret',
   REVIEWER_CONTAINER:{getByName:()=>container}};
 const payload={path:'d7c8ad4c-673d-4d87-a122-7d9bff4451bb/book.pdf',
   page:7,challenge:'signed.fixture',acknowledged:true};
 const make=body=>new Request('https://staging.example/review/acknowledge',{
   method:'POST',headers:{Origin:'https://staging.srnastudytool.com',
     Authorization:'Bearer test','Content-Type':'application/json'},body:JSON.stringify(body)});
 globalThis.fetch=async()=>Response.json({id:'d7c8ad4c-673d-4d87-a122-7d9bff4451bb'});
 try{
   const ok=await gateway.fetch(make(payload),reviewer);
   assert.equal(ok.status,200);
   assert.equal((await ok.json()).approved,false);
   assert.deepEqual(forwarded,[{path:'/review/acknowledge',method:'POST',body:JSON.stringify(payload)}]);
   const invalid=await gateway.fetch(make({...payload,acknowledged:false}),reviewer);
   assert.equal(invalid.status,400);
   assert.equal(forwarded.length,1);
   container.fetch=async()=>Response.json({receipt:'x'.repeat(80),approved:true},{headers:{'X-Review-Approval-Enabled':'false'}});
   const unsafe=await gateway.fetch(make(payload),reviewer);
   assert.equal(unsafe.status,502);
 }finally{globalThis.fetch=oldFetch;}
});

test('options-only schema constrains shape without revealing or forcing the expected key',async()=>{
 const old=globalThis.fetch,cfg={...env,AI_REVIEWER_MODEL:'qwen/qwen3.8-27b'};
 try{
  for(const answer of ['A','B','C','D']){
   globalThis.fetch=async(url,options)=>{
    const body=JSON.parse(options.body),f=body.response_format;
    assert.equal(body.reasoning_effort,'none');assert.equal(body.reasoning_format,'hidden');
    assert.equal(f.type,'json_schema');assert.equal(f.json_schema.strict,true);
    const s=f.json_schema.schema;assert.deepEqual(s.required,['key']);assert.equal(s.additionalProperties,false);
    assert.deepEqual(s.properties.key.items.enum,['A','B','C','D']);
    assert.equal(s.properties.key.minItems,1);assert.equal(s.properties.key.maxItems,1);
    const step=JSON.parse(body.messages[1].content);assert.equal(step.key,undefined);assert.equal(step.stem,undefined);
    return Response.json({choices:[{message:{content:JSON.stringify({key:[answer]})},finish_reason:'stop'}]});
   };
   const result=await gateway.fetch(request('options_only_review',cfg.AI_REVIEWER_MODEL),cfg);
   assert.equal(result.status,200);assert.deepEqual(JSON.parse((await result.json()).choices[0].message.content),{key:[answer]});
  }
  let calls=0;globalThis.fetch=async()=>{calls++;throw Error('Unexpected provider request')};
  for(const invalid of [{select_count:2},{options:[{id:'A',text:'one'}]},{options:['A','A','C','D'].map(id=>({id,text:id}))}]){
   assert.equal((await gateway.fetch(request('options_only_review',cfg.AI_REVIEWER_MODEL,invalid),cfg)).status,400);
  }
  assert.equal(calls,0);
 }finally{globalThis.fetch=old;}
});

test('cue output settings do not disable the independent clinical reviewers reasoning',async()=>{
 const old=globalThis.fetch;
 const cfg={...env,AI_REVIEWER_MODEL:'qwen/qwen3.8-27b',AI_EDITORIAL_REVIEWER_MODEL:'qwen/qwen3.8-27b',AI_EXPLANATION_REVIEW_OPT_IN:'true',AI_OPTION_REVIEW_OPT_IN:'true'};
 let calls=0;
 try{
  globalThis.fetch=async(url,options)=>{
   calls++;const body=JSON.parse(options.body);
   assert.equal(body.reasoning_effort,undefined);assert.equal(body.reasoning_format,undefined);
   return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});
  };
  for(const step of ['blind_review','option_review','explanation_review','editorial_review']){
   assert.equal((await gateway.fetch(request(step,cfg.AI_REVIEWER_MODEL),cfg)).status,200);
  }
  assert.equal(calls,4);
 }finally{globalThis.fetch=old;}
});


test('MC source-first schema agrees with Python plan fields and locks grounded rationale shape',async()=>{
 const {readFileSync}=await import('node:fs');
 const py=readFileSync(new URL('../../scripts/item_mc_choice_plan_v2.py',import.meta.url),'utf8');
 const fields=[...py.match(/fields = \{([^}]+)\}/)[1].matchAll(/"([a-z_]+)"/g)].map(m=>m[1]).sort();
 const original=globalThis.fetch;
 const cf={...env,AI_AUTHORING_PROVIDER:'cloudflare',AI_GENERATOR_MODEL:'zai-org/glm-5.3',AI_CLOUDFLARE_MODEL:'@cf/zai-org/glm-5.3',AI_CLOUDFLARE_ACCOUNT_ID:'account',AI_CLOUDFLARE_API_TOKEN:'fixture'};
 try{
  for(const step of ['concept_card','rationale']){
   globalThis.fetch=async(url,options)=>{
    const schema=JSON.parse(options.body).response_format.json_schema.schema;
    if(step==='concept_card'){
     assert.deepEqual([...schema.properties.choice_plan.required].sort(),fields);
     const grounding=schema.properties.choice_plan.properties.option_grounding;
     assert.deepEqual(grounding.required,['A','B','C','D']);assert.equal(grounding.additionalProperties,false);
     assert.deepEqual(grounding.properties.A.required,['source_refs','explanation']);
     const refs=grounding.properties.A.properties.source_refs;
     assert.equal(refs.minItems,1);assert.equal(refs.maxItems,3);
     assert.deepEqual(refs.items.required,['passage_id','span_ids']);
     assert.deepEqual(refs.items.properties.passage_id.enum,['p1']);
     assert.deepEqual(refs.items.properties.span_ids.items.enum,['q0']);
    }else{
     assert.deepEqual(schema.required,['core_concept','why_key_wins','trap']);
     assert.equal(schema.properties.distractor_breakdown,undefined);
     assert.equal(schema.properties.counterfactual_test,undefined);
    }
    return Response.json({success:true,result:{response:'{}'}});
   };
   const extra={format:'MC',evidence:[{passage_id:'p1',quote_spans:[{id:'q0',text:'Synthetic source'}]}],choice_plan:{option_grounding:{}},draft:{options:['A','B','C','D'].map(id=>({id,text:id}))}};
   assert.equal((await gateway.fetch(request(step,'zai-org/glm-5.3',extra),cf)).status,200);
  }
 }finally{globalThis.fetch=original;}
});

const calibrationModel='openai/gpt-oss-120b';
const calibrationEnv={...env,AI_REVIEWER_MODEL:'qwen/qwen3.8-27b',AI_EXPLANATION_REVIEW_OPT_IN:'true',
 AI_REVIEWER_CALIBRATION_OPT_IN:'true',AI_REVIEWER_CALIBRATION_MODEL:calibrationModel};
async function calibrationRequest(step='blind_review',patch={},stepFields={}){
 const payload=await request(step,calibrationModel,stepFields).json();
 return embeddingRequest({...payload,srna_reviewer_calibration:'fixed-controls-v1',...patch});
}
test('signed candidate calibration is separate from the configured generator reviewer',async()=>{
 const old=globalThis.fetch,seen=[];
 globalThis.fetch=async(url,options)=>{seen.push(JSON.parse(options.body));return Response.json({choices:[{message:{content:'{"key":["B"]}'},finish_reason:'stop'}]});};
 try{
  assert.equal((await gateway.fetch(await calibrationRequest(),calibrationEnv)).status,200);
  assert.equal(seen[0].model,calibrationModel);
  assert.ok(!Object.hasOwn(seen[0],'srna_reviewer_calibration'),'Private marker must not reach Groq');
  assert.equal((await gateway.fetch(request('blind_review','qwen/qwen3.8-27b'),calibrationEnv)).status,200);
  assert.equal(seen[1].model,'qwen/qwen3.8-27b');
  assert.equal(calibrationEnv.AI_REVIEWER_MODEL,'qwen/qwen3.8-27b');
 }finally{globalThis.fetch=old;}
});
test('candidate access requires its opt-in and signed explicit marker',async()=>{
 const old=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;throw Error('No upstream call allowed');};
 try{
  assert.equal((await gateway.fetch(request('blind_review',calibrationModel),calibrationEnv)).status,400);
  assert.equal((await gateway.fetch(await calibrationRequest(),{...calibrationEnv,AI_REVIEWER_CALIBRATION_OPT_IN:'false'})).status,400);
  assert.equal((await gateway.fetch(await calibrationRequest('blind_review',{srna_reviewer_calibration:'wrong'}),calibrationEnv)).status,400);
  assert.equal((await gateway.fetch(embeddingRequest({model:calibrationModel,srna_reviewer_calibration:'fixed-controls-v1'},false),calibrationEnv)).status,403);
  assert.equal(calls,0);
 }finally{globalThis.fetch=old;}
});
test('candidate calibration cannot author, revise, publish, or expand review budgets',async()=>{
 const old=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;throw Error('No upstream call allowed');};
 try{
  for(const step of ['concept_card','item_draft','rationale','rewrite','option_review','editorial_review','options_only_review']){
   assert.equal((await gateway.fetch(await calibrationRequest(step),calibrationEnv)).status,400,step);
  }
  assert.equal((await gateway.fetch(await calibrationRequest('blind_review',{max_tokens:1801}),calibrationEnv)).status,400);
  const payload=await request('blind_review',calibrationModel).json();payload.messages[1].content=JSON.stringify({step:'blind_review',rules_version:'2.0',auto_publish:false,blind:true,stem:'x'.repeat(20001)});
  assert.equal((await gateway.fetch(embeddingRequest({...payload,srna_reviewer_calibration:'fixed-controls-v1'}),calibrationEnv)).status,400);
  assert.equal(calls,0);
 }finally{globalThis.fetch=old;}
});
test('candidate source calibration uses strict scoped source identities',async()=>{
 const old=globalThis.fetch,seen=[];
 globalThis.fetch=async(url,options)=>{seen.push(JSON.parse(options.body));return Response.json({choices:[{message:{content:'{}'},finish_reason:'stop'}]});};
 try{
  const fields=[{id:'e0',passage_ids:['s0']}],source_passages=[{passage_id:'s0',quote_spans:[{id:'q0',text:'Source fact'}]}];
  assert.equal((await gateway.fetch(await calibrationRequest('explanation_review',{}, {fields,source_passages}),calibrationEnv)).status,200);
  const schema=seen[0].response_format;
  assert.equal(schema.type,'json_schema');assert.equal(schema.json_schema.strict,true);
  const fieldsSchema=schema.json_schema.schema.properties.judgments;
  assert.deepEqual(fieldsSchema.required,['e0']);
  assert.deepEqual(fieldsSchema.properties.e0.properties.quote_refs.items.enum,['s0:q0']);
  assert.equal(seen[0].model,calibrationModel);
  assert.ok(!Object.hasOwn(seen[0],'srna_reviewer_calibration'));
 }finally{globalThis.fetch=old;}
});
