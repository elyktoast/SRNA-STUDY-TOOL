// Wrangler returns before container replacement finishes. Do not spend AI tokens
// while an old image can still be terminated by the asynchronous rollout.
import {pathToFileURL} from 'node:url';
export function settled(app,instances,now,started){
 const updated=Date.parse(app?.updated_at);
 return now-started>=90000 && Number.isFinite(updated) && now-updated>=60000
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
 while(Date.now()-started<240000){
  const [app,instances]=await Promise.all([read(''),read('/instances-v2')]);
  if(settled(app,instances,Date.now(),started)){console.log('Staging container configuration settled; authenticated smoke may begin');return;}
  console.log('Waiting for staging container rollout; no AI calls performed');
  await new Promise(resolve=>setTimeout(resolve,10000));
 }
 throw Error('Container rollout did not settle; acceptance blocked before AI calls');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)await main();
