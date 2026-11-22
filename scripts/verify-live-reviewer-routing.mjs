import assert from 'node:assert/strict';
import {createHmac} from 'node:crypto';
const secret=process.env.STAGING_RECEIPT_SIGNING_SECRET;
assert.ok(secret);
const user={step:'explanation_review',rules_version:'2.0',auto_publish:false,independent:true,
 fields:[{id:'e0',text:'Sample bin B contains a blue token.',passage_ids:['s0']},
   {id:'e1',text:'Sample bin A contains a red token.',passage_ids:['s0']}],
 source_passages:[{passage_id:'s0',quote_spans:[{id:'q1',text:'Sample bin B contains a blue token.'}]}]};
const system='Return one JSON object with judgments keyed by every field ID. Each judgment must have supported (true, false or null), quote_refs (an array of passage:span IDs or null) and reason (brief string). Cite the exact supplied span for a supported field. Use false or null with null quote_refs when support is absent.';
const body=JSON.stringify({model:'openai/gpt-oss-120b',max_tokens:1000,temperature:0.2,
 messages:[{role:'system',content:system},{role:'user',content:JSON.stringify(user)}]});
const ts=String(Math.floor(Date.now()/1000));
const signature=createHmac('sha256',secret).update(['srna-groq-relay-v1',ts,body].join('\n')).digest('hex');
const start=Date.now();
const response=await fetch('https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay',
 {method:'POST',redirect:'error',signal:AbortSignal.timeout(55000),
 headers:{'Content-Type':'application/json','X-Relay-Timestamp':ts,'X-Relay-Signature':signature},body});
assert.equal(response.status,200);
const data=JSON.parse((await response.json()).choices[0].message.content).judgments;
assert.deepEqual(Object.keys(data).sort(),['e0','e1']);
assert.equal(data.e0.supported,true);
assert.deepEqual(data.e0.quote_refs,['s0:q1']);
assert.ok([false,null].includes(data.e1.supported));
assert.equal(data.e1.quote_refs,null);
console.log(JSON.stringify({synthetic_scoped_evidence:'passed',elapsed_ms:Date.now()-start}));
