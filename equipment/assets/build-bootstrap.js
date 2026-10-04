(()=>{'use strict';
const script=document.currentScript,cfg=window.MBU_BOOT||{},assetsBase=new URL(cfg.assetsBase||'./',script?.src||location.href),buildUrl=new URL(cfg.buildUrl||'../build.json',script?.src||location.href);document.documentElement.dataset.mbuBoot='loading';const gate=document.createElement('style');gate.textContent='html[data-mbu-boot="loading"] body>*:not(#srna-legal-gate){visibility:hidden;pointer-events:none}html[data-mbu-boot="loading"] body>#srna-legal-gate{visibility:visible;pointer-events:auto}';document.head.append(gate);
const specOf=x=>typeof x==='string'?{src:x}:x||{},REQUEST_TIMEOUT=12000,ASSET_TIMEOUT=15000;
const fetchTimed=async(url,opts={},timeout=REQUEST_TIMEOUT)=>{const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),timeout);try{return await fetch(url,{...opts,signal:ctl.signal})}finally{clearTimeout(timer)}};
async function start(){
const response=await fetchTimed(buildUrl.href+'?t='+Date.now(),{cache:'no-store',credentials:'same-origin'});
if(!response.ok)throw Error('Build manifest HTTP '+response.status);
const manifest=await response.json(),build=manifest&&typeof manifest.build==='string'?manifest.build.trim():'';
if(!build)throw Error('Invalid build manifest');
const urlFor=src=>{const u=new URL(src,assetsBase);u.searchParams.set('b',build);return u};
const jsonCache=new Map();
const fetchJSON=async(input,{cache='force-cache',timeout=12000}={})=>{
  const url=new URL(input,location.href),key=url.href;if(jsonCache.has(key))return jsonCache.get(key);
  const request=(async()=>{const response=await fetchTimed(url,{cache,credentials:'same-origin'},timeout);if(!response.ok)throw Error('HTTP '+response.status+' for '+url.pathname);const text=await response.text();if(!text.trim())throw Error('Empty JSON response for '+url.pathname);try{return JSON.parse(text)}catch(e){throw Error('Invalid JSON at '+url.pathname+': '+e.message)}})();
  jsonCache.set(key,request);try{return await request}catch(e){jsonCache.delete(key);throw e}
};
const loads=new Map(),once=(key,make)=>loads.get(key)||loads.set(key,make()).get(key);
const loadStyle=src=>{const href=urlFor(src).href;return once('c'+href,()=>new Promise((resolve,reject)=>{const l=document.createElement('link'),timer=setTimeout(()=>{l.remove();reject(Error('Stylesheet timed out: '+src))},ASSET_TIMEOUT);l.rel='stylesheet';l.href=href;l.onload=()=>{clearTimeout(timer);resolve()};l.onerror=()=>{clearTimeout(timer);l.remove();reject(Error('Stylesheet failed: '+src))};document.head.append(l)}))};
const loadScript=async raw=>{const spec=specOf(raw),url=urlFor(spec.src),data=Object.entries(spec.data||{});await once('j'+url.href+JSON.stringify(data),()=>new Promise((resolve,reject)=>{const s=document.createElement('script'),timer=setTimeout(()=>{s.remove();reject(Error('Script timed out: '+spec.src))},ASSET_TIMEOUT);s.src=url.href;for(const [k,v] of data)s.dataset[k]=String(v);s.onload=()=>{clearTimeout(timer);resolve()};s.onerror=()=>{clearTimeout(timer);s.remove();reject(Error('Script failed: '+spec.src))};document.body.append(s)}));if(spec.waitFor){const ready=window[spec.waitFor];if(ready&&typeof ready.then==='function')await ready}};
window.MBU_BUILD_ID=build;window.MBUBuild={id:build,assetsBase,buildUrl,urlFor,loadStyle,loadScript,fetchJSON};
await loadStyle('app-core.css');
await loadScript('app-core.js');
await loadScript('legal-gate.js');
if(window.SRNALegalReady)await window.SRNALegalReady;
await loadScript('course-context.js');
await loadScript('calibration-outbox.js');
await loadScript('study-intelligence.js');
await loadScript('answer-order.js');
await loadScript('supabase-config.js');
await loadScript('supabase-sync.js');
if(window.MBUAuthReady&&typeof window.MBUAuthReady.then==='function')await window.MBUAuthReady;
await window.MBUCalibrationOutbox?.flushAll?.();
const ctx=window.MBU_CONTEXT||{},root=new URL('../../',assetsBase),path=location.pathname,protectedCourse=['equipment/','basic-principles/','pharm/'].some(x=>path.startsWith(root.pathname+x));
if(protectedCourse){
  const info=window.MBUSupabase?.status?.()||{};
  if(!(info.signedIn&&info.legalAccepted===true&&info.accessStatus==='active')&&!info.recoveryMode){
    const home=root.href;
    sessionStorage.setItem('mbu_post_auth_target',location.href);
    location.replace(home);
    return build;
  }
}
const postAuthTarget=sessionStorage.getItem('mbu_post_auth_target');
if(!protectedCourse&&postAuthTarget){
  const info=window.MBUSupabase?.status?.()||{};
  if(info.signedIn&&info.legalAccepted===true&&info.accessStatus==='active'&&!info.recoveryMode){
    let target=null;try{const candidate=new URL(postAuthTarget,location.href);if(candidate.origin===root.origin&&['equipment/','basic-principles/','pharm/'].some(course=>candidate.pathname.startsWith(root.pathname+course)))target=candidate.href}catch{}
    sessionStorage.removeItem('mbu_post_auth_target');
    if(target){location.replace(target);return build}
  }
}
if(protectedCourse){
  const enforceAccess=()=>{
    const info=window.MBUSupabase?.status?.()||{};
    if(!(info.signedIn&&info.legalAccepted===true&&info.accessStatus==='active')&&!info.recoveryMode){
      sessionStorage.setItem('mbu_post_auth_target',location.href);
      location.replace(new URL('../../',assetsBase).href);
    }
  };
  window.addEventListener('mbu:supabase-status',enforceAccess);
  window.addEventListener('pageshow',event=>{if(event.persisted)enforceAccess()});
}
await Promise.all((cfg.styles||[]).map(loadStyle));
for(const entry of cfg.scripts||[])await loadScript(entry);
if(typeof cfg.ready==='function')await cfg.ready();
return build
}
const showFailure=e=>{let box=document.getElementById('mbu-bootstrap-failure');if(!box){box=document.createElement('div');box.id='mbu-bootstrap-failure';box.setAttribute('role','alert');box.style.cssText='max-width:720px;margin:48px auto;padding:24px;font:16px/1.5 system-ui,sans-serif;border:1px solid #cbd5e0;border-radius:12px;background:#fff;color:#1a202c';document.body.append(box)}box.innerHTML='<h1 style="margin-top:0;font-size:1.35rem">SRNA Study Tool could not finish loading</h1><p>Your saved study progress was not changed. Check your connection and try again.</p><button type="button" style="font:inherit;padding:9px 14px;cursor:pointer">Try again</button>';box.querySelector('button').onclick=()=>location.reload();return e};
const ready=start().catch(e=>{console.error('SRNA Study Tool bootstrap failed',e);showFailure(e);throw e}).finally(()=>{delete document.documentElement.dataset.mbuBoot;gate.remove()});
window.MBUPageReady=ready;if(cfg.readyGlobal)window[cfg.readyGlobal]=ready;
})();