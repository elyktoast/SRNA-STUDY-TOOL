// Wrangler returns before container replacement finishes. Do not spend AI tokens
// while an old image can still be terminated by the asynchronous rollout.
import {pathToFileURL} from 'node:url';
export function completedWorkerBuild(checks,sha){
 if(!/^[a-f0-9]{40}$/.test(sha||'')||!Array.isArray(checks))return null;
 const matching=checks.filter(c=>c.head_sha===sha&&c.app?.slug==='cloudflare-workers-and-pages'
  &&c.name==='Workers Builds: srna-source-reviewer-gateway-staging').sort((a,b)=>b.id-a.id);
 const latest=matching[0],completed=Date.parse(latest?.completed_at);
 return latest?.status==='completed'&&latest?.conclusion==='success'&&Number.isFinite(completed)?completed:null;
}
export function settled(app,instances,now,started,buildCompleted=0){
 const updated=Date.parse(app?.updated_at);
 return now-started>=90000 && Number.isFinite(updated) && now-updated>=60000
  && Number.isFinite(buildCompleted) && now-buildCompleted>=90000
  && !app.active_rollout_id && typeof app.configuration?.image==='string'
  && Array.isArray(app.health?.errors) && app.health.errors.length===0
  && Array.isArray(instances) && instances.every(i=>
   ['inactive','stopped'].includes(i.status?.state)
   || (i.status?.state==='running'&&i.image===app.configuration.image));
}
async function main(){
 const account=process.env.CLOUDFLARE_ACCOUNT_ID,token=process.env.CLOUDFLARE_API_TOKEN;
 if(!/^[a-f0-9]{32}$/.test(account||'')||!token)throw Error('Staging deployment credentials required');
 const base=`https://api.cloudflare.com/client/v4/accounts/${account}/containers/applications/a03bdc12-da09-4e2c-b543-816ebad2e339`;
 const read=async path=>{
  const r=await fetch(base+path,{headers:{Authorization:'Bearer '+token},redirect:'error',signal:AbortSignal.timeout(8000)});
  if(!r.ok)throw Error('Container rollout metadata unavailable: HTTP '+r.status);
  const body=await r.json();if(!body.success)throw Error('Container rollout metadata unavailable');return body.result;
 };
 const started=Date.now();
 const direct=process.env.STAGING_DEPLOYMENT_JUST_COMPLETED==='true';
 const sha=process.env.GITHUB_SHA,githubToken=process.env.GITHUB_TOKEN;
 if(!direct&&(!/^[a-f0-9]{40}$/.test(sha||'')||!githubToken))throw Error('Exact staging build identity required');
 const readBuild=async()=>{
  if(direct)return started; // This job has just completed its own explicit deploy.
  const r=await fetch(`https://api.github.com/repos/elyktoast/SRNA-STUDY-TOOL/commits/${sha}/check-runs?per_page=100`,{
   headers:{Authorization:'Bearer '+githubToken,Accept:'application/vnd.github+json'},redirect:'error',signal:AbortSignal.timeout(8000)});
  if(!r.ok)throw Error('Staging build status unavailable: HTTP '+r.status);
  return completedWorkerBuild((await r.json()).check_runs,sha);
 };
 // The observed staging replacement exceeded four minutes even with no health
 // errors. Allow ten minutes; never waive image, health or quiet-period checks.
 while(Date.now()-started<600000){
  const [app,instances,completed]=await Promise.all([read(''),read('/instances-v2'),readBuild()]);
  if(completed!==null&&settled(app,instances,Date.now(),started,completed)){console.log('Exact staging build and container rollout settled; authenticated smoke may begin');return;}
  console.log('Waiting for staging container rollout; no AI calls performed');
  await new Promise(resolve=>setTimeout(resolve,10000));
 }
 throw Error('Container rollout did not settle; acceptance blocked before AI calls');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)await main();
