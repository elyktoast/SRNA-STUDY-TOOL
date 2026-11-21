import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {settled} from './wait-staging-reviewer-rollout.mjs';
const target='dd3576a2434ac5528aec2f037e9d473515f59866';
const token=process.env.CLOUDFLARE_API_TOKEN;
assert.ok(token,'Staging deployment credential unavailable');
const base='https://api.cloudflare.com/client/v4/accounts/5a84e0fe00e430d25e901b260861381e';
async function read(path){
 const r=await fetch(base+path,{headers:{Authorization:'Bearer '+token},redirect:'error',signal:AbortSignal.timeout(15000)});
 assert.ok(r.ok,'Staging deployment metadata unavailable: '+path+' HTTP '+r.status);
 const v=await r.json();assert.equal(v.success,true);return v.result;
}
const application='/containers/applications/a03bdc12-da09-4e2c-b543-816ebad2e339';
let verified=false;
for(let i=0;i<12;i++){
 const checksResponse=await fetch('https://api.github.com/repos/elyktoast/SRNA-STUDY-TOOL/commits/'+target+'/check-runs?per_page=100',{headers:{Authorization:'Bearer '+process.env.GITHUB_TOKEN,Accept:'application/vnd.github+json'},redirect:'error',signal:AbortSignal.timeout(15000)});
 assert.ok(checksResponse.ok,'Staging build check unavailable');
 const checks=(await checksResponse.json()).check_runs;
 const ci=checks.find(c=>c.head_sha===target&&c.name==='staging-unit-tests');
 if(ci?.status==='completed'&&ci.conclusion!=='success')throw Error('Staging CI did not pass');
 if(ci?.status!=='completed'){if(i<11){await new Promise(resolve=>setTimeout(resolve,20000));continue;}throw Error('Staging CI incomplete');}
 const check=checks.filter(c=>c.head_sha===target&&c.app?.slug==='cloudflare-workers-and-pages'&&c.name==='Workers Builds: srna-source-reviewer-gateway-staging').sort((a,b)=>b.id-a.id)[0];
 if(check?.status!=='completed'||check?.conclusion!=='success'){
  if(i<11){await new Promise(resolve=>setTimeout(resolve,20000));continue;}
  throw Error('Staging build not successful');
 }
 const build={build_uuid:check.details_url.split('/').pop(),status:'stopped',build_outcome:'success',stopped_on:check.completed_at};
 const [app,instances]=await Promise.all([read(application),read(application+'/instances-v2')]);
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
 if(i<11)await new Promise(resolve=>setTimeout(resolve,20000));
}
assert.ok(verified,'Exact staging rollout has not settled');
