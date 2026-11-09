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


const geminiEnv={...env,AI_HYBRID_ENABLED:'true',AI_GEMINI_API_KEY:'test-key',
 AI_GEMINI_MODEL:'gemini-2.5-flash',AI_GEMINI_FALLBACK_MODEL:'gemini-2.5-flash-lite'};
const okGemini=()=>new Response(JSON.stringify({candidates:[{content:{parts:[{text:'{}'}]}}]}),{status:200});
async function scenario(handler,configuration=geminiEnv){
 const original=globalThis.fetch, calls=[];
 globalThis.fetch=async(url,options)=>{calls.push({url:String(url),options});return handler(String(url),options,calls.length)};
 try{return {response:await gateway.fetch(request('concept_card','generator-model'),configuration),calls};}
 finally{globalThis.fetch=original;}
}
test('Gemini generation never fetches model catalog',async()=>{
 const {response,calls}=await scenario(()=>okGemini());
 assert.equal(response.status,200);assert.equal(calls.length,1);
 assert.ok(calls[0].url.endsWith('/models/gemini-2.5-flash:generateContent'));
});
test('Gemini 429 falls back exactly once to configured alternate',async()=>{
 const {response,calls}=await scenario((url)=>url.includes('flash-lite')?okGemini():new Response('{}',{status:429}));
 assert.equal(response.status,200);assert.equal(calls.length,2);
 assert.ok(calls[1].url.includes('flash-lite:generateContent'));
});
test('Gemini 404 falls back to configured alternate',async()=>{
 const {response,calls}=await scenario((url)=>url.includes('flash-lite')?okGemini():new Response('{}',{status:404}));
 assert.equal(response.status,200);assert.equal(calls.length,2);
});
test('Gemini 429 without alternate does not retry',async()=>{
 const {response,calls}=await scenario(()=>new Response('{}',{status:429}),{...geminiEnv,AI_GEMINI_FALLBACK_MODEL:''});
 assert.equal(response.status,502);assert.equal((await response.json()).rule,'PROVIDER_RATE_LIMIT');assert.equal(calls.length,1);
});
test('Gemini duplicate alternate does not retry',async()=>{
 const {calls}=await scenario(()=>new Response('{}',{status:429}),{...geminiEnv,AI_GEMINI_FALLBACK_MODEL:'gemini-2.5-flash'});
 assert.equal(calls.length,1);
});
test('Gemini invalid alternate never contacts untrusted model',async()=>{
 const {calls}=await scenario(()=>new Response('{}',{status:429}),{...geminiEnv,AI_GEMINI_FALLBACK_MODEL:'../../bad'});
 assert.equal(calls.length,1);
});
test('Gemini 403 never falls back',async()=>{
 const {response,calls}=await scenario(()=>new Response('{}',{status:403}));
 assert.equal((await response.json()).rule,'PROVIDER_FORBIDDEN');assert.equal(calls.length,1);
});
test('Gemini 500 never falls back',async()=>{
 const {response,calls}=await scenario(()=>new Response('{}',{status:500}));
 assert.equal((await response.json()).rule,'PROVIDER_UPSTREAM');assert.equal(calls.length,1);
});
test('Gemini timeout never falls back',async()=>{
 const {response,calls}=await scenario(()=>{const e=new Error('timed out');e.name='TimeoutError';throw e;});
 assert.equal((await response.json()).error,'relay_timeout');assert.equal(calls.length,1);
});
test('Gemini malformed success never falls back',async()=>{
 const {response,calls}=await scenario(()=>new Response('not json',{status:200}));
 assert.equal((await response.json()).rule,'PROVIDER_UPSTREAM');assert.equal(calls.length,1);
});
test('Gemini alternate 429 stops after second attempt',async()=>{
 const {response,calls}=await scenario(()=>new Response('{}',{status:429}));
 assert.equal((await response.json()).rule,'PROVIDER_RATE_LIMIT');assert.equal(calls.length,2);
});
test('Gemini empty candidate never falls back',async()=>{
 const {response,calls}=await scenario(()=>new Response('{}',{status:200}));
 assert.equal((await response.json()).rule,'PROVIDER_UPSTREAM');assert.equal(calls.length,1);
});
