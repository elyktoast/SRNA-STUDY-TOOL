import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {settled} from './wait-staging-reviewer-rollout.mjs';
const target='24959edc87f2e02c0465d70f788e31b65e0d0844';
const token=process.env.CLOUDFLARE_API_TOKEN;
assert.ok(token,'Staging deployment credential unavailable');
const base='https://api.cloudflare.com/client/v4/accounts/5a84e0fe00e430d25e901b260861381e';
async function read(path){
 const r=await fetch(base+path,{headers:{Authorization:'Bearer '+token},redirect:'error',signal:AbortSignal.timeout(15000)});
 assert.ok(r.ok,'Staging deployment metadata unavailable: HTTP '+r.status);
 const v=await r.json();assert.equal(v.success,true);return v.result;
}
const application='/containers/applications/a03bdc12-da09-4e2c-b543-816ebad2e339';
let verified=false;
for(let i=0;i<6;i++){
 const [builds,app,instances]=await Promise.all([read('/builds/workers/d2335d1893bf45a396c690f63a045835/builds'),read(application),read(application+'/instances-v2')]);
 const build=builds.find(b=>b.build_trigger_metadata?.commit_hash===target&&b.build_trigger_metadata?.branch==='fix/board-question-quality');
 const now=Date.now();
 if(build?.status==='stopped'&&build.build_outcome==='success'&&settled(app,instances,now,now-90000,Date.parse(build.stopped_on))){
  const snapshot={verification:'connected_cloudflare_deployment_read',verified_at:new Date(now).toISOString(),
   build:{build_uuid:build.build_uuid,status:build.status,build_outcome:build.build_outcome,commit_hash:target,stopped_on:build.stopped_on},
   app:{updated_at:app.updated_at,active_rollout_id:app.active_rollout_id,configuration:{image:app.configuration.image},health:{errors:app.health.errors}},
   instances:instances.map(v=>({status:v.status,image:v.image}))};
  writeFileSync('/tmp/pn-deployment.json',JSON.stringify(snapshot));
  console.log(JSON.stringify({target,build:build.build_uuid,image:app.configuration.image,verified:true}));
  verified=true;break;
 }
 if(i<5)await new Promise(resolve=>setTimeout(resolve,20000));
}
assert.ok(verified,'Exact staging rollout has not settled');
