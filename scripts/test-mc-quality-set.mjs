import assert from 'node:assert/strict';
import {test} from 'node:test';
import {runSet,samples} from './verify-mc-quality-set.mjs';
const time=1800000000000,sha='cb7cac08963165953f9d002c299e9b39cdcfd510';
const deployment={verification:'connected_cloudflare_deployment_read',verified_at:new Date(time).toISOString(),build:{commit_hash:sha,status:'stopped',build_outcome:'success',stopped_on:new Date(time-180000).toISOString()},app:{updated_at:new Date(time-120000).toISOString(),configuration:{image:'fixture'},health:{errors:[]}},instances:[]};
function fixture(mode){
 const calls=[],rows=[];let item;
 const fetchImpl=async(url,options={})=>{
  const body=options.body?JSON.parse(options.body):null;calls.push({url,body});let value;
  if(url.includes('/git/ref/'))value={object:{sha}};
  else if(url.endsWith('/auth/v1/user'))value={id:'c003287a-10ce-4cc9-926e-ef7c3a162a26'};
  else if(url.endsWith('/textbooks'))value={textbooks:Array.from({length:7},(_,i)=>({id:'book'+i}))};
  else if(url.endsWith('/lecture-plan'))value={auto_generate:false,auto_publish:false,count:1,jobs:[{path:'/generation/preflight',body:{...body,topic:body.lecture_text,textbook_id:'book0',textbook_ids:['book0']}}]};
  else if(url.endsWith('/preflight'))value={authoring_contract:'2026-11-11-v23',authoring_provider:'cloudflare',authoring_delivery_model:'@cf/zai-org/glm-5.3',resume:{resumable:mode==='used'}};
  else if(url.endsWith('/one')){
   if(mode==='timeout')throw Error('transport failure');
   if(mode==='server')return Response.json({error:'runtime'}, {status:500});
   item=body.item_id;value={published:false,can_publish:false,draft_id:item};
  }else if(url.endsWith('/revalidate'))value={database_writes:false,generation_performed:false,published:false,issues:mode==='blocked'?[{rule_id:'R-12.2'}]:[]};
  else value={published:false,question:{stem:'synthetic',options:[],key:['A'],rationale:{}},screening:{rewrite_attempts_used:1,stages:{...Object.fromEntries(Array.from({length:10},(_,i)=>['stage'+i,{status:mode==='blocked'&&i===9?'flag':'pass'}])),human_review:{status:'pending'}}}};
  return Response.json(value);
 };
 return {calls,rows,run:overrides=>runSet({env:{CONFIRM_PAID_MC_SET:'true',GITHUB_RUN_ATTEMPT:'1',STAGING_SUPABASE_ANON_KEY:'fixture',SRNA_STAGING_REVIEWER_ACCESS_TOKEN:'fixture',...overrides},fetchImpl,deployment,now:()=>time,emit:()=>{},save:value=>rows.push(structuredClone(value))})};
}
test('fixed acceptance requests each new MC once, retains results, and never approves or regrades',async()=>{
 const f=fixture();const result=await f.run();assert.equal(result.length,samples.length);assert.ok(result.every(r=>r.accepted));
 const paid=f.calls.filter(c=>c.url.endsWith('/generation/one'));
 assert.deepEqual(paid.map(c=>c.body.item_id),samples.map(s=>s.item_id));
 assert.ok(paid.every(c=>c.body.format==='MC'));assert.equal(f.rows.length,samples.length);
 assert.ok(f.calls.every(c=>!c.url.endsWith('/review')&&!c.url.endsWith('/complete-options')));
});
test('transport and clinical failures remain failures without rerolls',async()=>{
 for(const mode of ['timeout','server','blocked']){
  const f=fixture(mode),result=await f.run();assert.ok(result.every(r=>!r.accepted));
  assert.equal(f.calls.filter(c=>c.url.endsWith('/generation/one')).length,mode==='blocked'?samples.length:1);
  if(mode!=='blocked')assert.ok(result.slice(1).every(r=>r.not_run));
  if(mode==='blocked')assert.ok(result.every(r=>r.draft_id&&r.blockers.stage9&&r.current_source_issues.length));
 }
});
test('used checkpoints or repeated workflow attempts block paid replay',async()=>{
 const used=fixture('used');const results=await used.run();assert.ok(results.every(r=>!r.accepted));
 assert.equal(used.calls.filter(c=>c.url.endsWith('/generation/one')).length,0);
 const rerun=fixture();await assert.rejects(rerun.run({GITHUB_RUN_ATTEMPT:'2'}));assert.equal(rerun.calls.length,0);
});
