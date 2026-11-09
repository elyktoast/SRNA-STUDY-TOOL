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
function request(step, model, options={}) {
  const body = JSON.stringify({
    model, max_tokens: 1024, temperature: 0.2,
    messages: [{role:'system',content:'Return JSON'},
      {role:'user',content:JSON.stringify({
        step, rules_version:'2.0', auto_publish:false,
        ...(step==='blind_review'?{blind:true}:{}),
      })}],
  });
  const stamp = String(Math.floor(Date.now()/1000));
  const signature = createHmac('sha256',secret)
    .update('srna-groq-relay-v1\n'+stamp+'\n'+body).digest('hex');
  return new Request(endpoint,{method:'POST',headers:{
    'Content-Type':'application/json','X-Relay-Timestamp':stamp,
    'X-Relay-Signature':signature},body});
}
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
