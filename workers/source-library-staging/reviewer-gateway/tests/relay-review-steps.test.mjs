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

test('hybrid concept card falls back to configured Gemini API model when preferred labels are absent', async()=>{
  const original=globalThis.fetch;
  const calls=[];
  globalThis.fetch=async (url,options)=>{
    calls.push(String(url));
    if(String(url).includes('/v1beta/models?pageSize=')){
      return new Response(JSON.stringify({models:[{name:'models/gemini-2.5-flash',displayName:'Gemini 2.5 Flash',supportedGenerationMethods:['generateContent']}]}),{status:200});
    }
    return new Response(JSON.stringify({candidates:[{content:{parts:[{text:'{}'}]}}]}),{status:200});
  };
  try{
    const response=await gateway.fetch(request('concept_card','generator-model'),{
      ...env,AI_HYBRID_ENABLED:'true',AI_GEMINI_API_KEY:'test-gemini-key',AI_GEMINI_MODEL:'gemini-2.5-flash',
    });
    assert.equal(response.status,200);
    assert.ok(calls.some(url=>url.endsWith('/models/gemini-2.5-flash:generateContent')));
  }finally{globalThis.fetch=original;}
});

test('hybrid concept card refuses unconfigured models without paid generation',async()=>{
 const original=globalThis.fetch;const calls=[];
 globalThis.fetch=async(url)=>{
  calls.push(String(url));
  if(String(url).includes('/v1beta/models?pageSize=')){
   return new Response(JSON.stringify({models:[
    {name:'models/gemini-other-flash',supportedGenerationMethods:['generateContent']},
   ]}),{status:200});
  }
  throw Error('must not call provider generation');
 };
 try{
  const response=await gateway.fetch(request('concept_card','generator-model'),{
   ...env,AI_HYBRID_ENABLED:'true',AI_GEMINI_API_KEY:'test-key',AI_GEMINI_MODEL:'gemini-2.5-flash',
  });
  assert.equal(response.status,502);
  assert.equal((await response.json()).rule,'PROVIDER_MODEL_UNAVAILABLE');
  assert.equal(calls.filter(url=>url.includes(':generateContent')).length,0);
 }finally{globalThis.fetch=original;}
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
