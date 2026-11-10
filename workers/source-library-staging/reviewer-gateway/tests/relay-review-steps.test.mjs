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
  for(const [wait,expected] of [['25.123s',26],['500ms',1],['9999s',undefined]]){
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
