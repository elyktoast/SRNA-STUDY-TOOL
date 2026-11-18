import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {settled,completedWorkerBuild,needsReadOnlyWarmup} from './wait-staging-reviewer-rollout.mjs';
const now=200000,started=0,app={updated_at:new Date(100000).toISOString(),configuration:{image:'new-image'},health:{errors:[]}};
test('warm-up CLI exits after identity and catalog even when a paid flag is present',()=>{
 const script=new URL('./verify-one-staging-question.mjs',import.meta.url).href;
 const source=`
 process.env.STAGING_SUPABASE_ANON_KEY='synthetic-key';
 process.env.SRNA_STAGING_REVIEWER_ACCESS_TOKEN='synthetic-session';
 process.env.STAGING_TEST_ADMIN_EMAIL='';process.env.STAGING_TEST_ADMIN_PASSWORD='';
 process.argv.push('--warmup-only','--confirm-paid-generation');
 let calls=0;
 const {default:https}=await import('node:https');
 const {syncBuiltinESMExports}=await import('node:module');
 const {EventEmitter}=await import('node:events');
 const {Readable}=await import('node:stream');
 https.request=(target,options,callback)=>{
  const url=String(target);calls++;let body;
  if(calls===1&&url==='https://xqyasyambwdyhsjkftqu.supabase.co/auth/v1/user')body={id:'c003287a-10ce-4cc9-926e-ef7c3a162a26'};
  else if(calls===2&&url==='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/generation/textbooks')body={textbooks:[]};
  else throw Error('Unexpected operation after catalog warm-up');
  const req=new EventEmitter();req.write=()=>{};req.end=()=>{
   const res=Readable.from([Buffer.from(JSON.stringify(body))]);res.statusCode=200;res.headers={'content-type':'application/json'};callback(res);
  };return req;
 };
 syncBuiltinESMExports();
 globalThis.fetch=()=>{throw Error('Unexpected fetch network call')};
 await import(${JSON.stringify(script)});throw Error('Warm-up failed to exit');`;
 const output=execFileSync(process.execPath,['--input-type=module','--eval',source],{encoding:'utf8'});
 assert.match(output,/Authenticated read-only staging warm-up completed/);
 assert.doesNotMatch(output,/acceptance_item_id|draft_id/);
});
test('idle active rollout permits only a read-only warm-up after exact-build quiet period',()=>{
 const idle=[{status:{state:'inactive'}}],active={...app,active_rollout_id:'rollout'};
 assert.equal(needsReadOnlyWarmup(active,idle,now,100000),true);
 assert.equal(settled(active,idle,now,started,100000),false);
 for(const [a,i,t] of [[active,idle,180000],[app,idle,100000],[active,[{status:{state:'running'}}],100000],[{...active,health:{errors:[{}]}},idle,100000],[active,[],100000]]){
  assert.equal(needsReadOnlyWarmup(a,i,now,t),false);
 }
});
test('rollout gate rejects the early ready window that interrupted generation',()=>{
 assert.equal(settled(app,[],80000,started),false);
 assert.equal(settled({...app,updated_at:new Date(160000).toISOString()},[],now,started),false);
});
test('rollout gate rejects active rollout and old running image',()=>{
 assert.equal(settled({...app,active_rollout_id:'rollout'},[],now,started),false);
 assert.equal(settled(app,[{status:{state:'running'},image:'old-image'}],now,started),false);
});
test('settled target image or inactive instance permits authenticated warmup',()=>{
 assert.equal(settled(app,[{status:{state:'running'},image:'new-image'}],now,started),true);
 assert.equal(settled(app,[{status:{state:'inactive'}}],now,started),true);
});
test('failed state and missing or invalid metadata fail closed',()=>{
 assert.equal(settled(app,[{status:{state:'failed'}}],now,started),false);
 assert.equal(settled({...app,updated_at:'invalid'},[],now,started),false);
 assert.equal(settled({...app,health:{errors:[{}]}},[],now,started),false);
 assert.equal(settled(app,null,now,started),false);
});

const sha='a'.repeat(40),finished={id:1,head_sha:sha,name:'Workers Builds: srna-source-reviewer-gateway-staging',app:{slug:'cloudflare-workers-and-pages'},status:'completed',conclusion:'success',completed_at:new Date(100000).toISOString()};
test('old settled container cannot authorize a commit whose build is still running',()=>{
 assert.equal(completedWorkerBuild([{...finished,status:'in_progress',conclusion:null}],sha),null);
 assert.equal(completedWorkerBuild([finished],'b'.repeat(40)),null);
 assert.equal(completedWorkerBuild([{...finished,app:{slug:'untrusted'}}],sha),null);
 assert.equal(completedWorkerBuild([finished],sha),100000);
 assert.equal(settled(app,[],now,started,180000),false);
 assert.equal(settled(app,[],now,started,100000),true);
});
test('latest failed build is not hidden behind an older success',()=>{
 assert.equal(completedWorkerBuild([finished,{...finished,id:2,conclusion:'failure'}],sha),null);
});
