(()=>{'use strict';
const runtime=window.MBUBuild,APP='SRNA Study Tool',SYNC_SCHEMA=1,DEVICE_KEY='mbu_device_id_v1',META_KEY='mbu_sync_meta_v1',errors=[],adapters=new Map(),ROOT_URL=runtime.appRoot;
let manifestPromise=null,toolsReturnFocus=null;const $=id=>document.getElementById(id),E=t=>document.createElement(t),Q=s=>document.querySelector(s),A=s=>document.querySelectorAll(s),B=document.body;
const now=Date.now;
const plain=v=>v&&typeof v==='object'&&!Array.isArray(v);
const safeJSON=(raw,fallback)=>{try{return JSON.parse(raw)??fallback}catch{return fallback}};
function randomId(){try{return crypto.randomUUID()}catch{return 'dev-'+now().toString(36)+'-'+Math.random().toString(36).slice(2)}}
function deviceId(){let id=localStorage.getItem(DEVICE_KEY);if(!id){id=randomId();localStorage.setItem(DEVICE_KEY,id)}return id}
function readMeta(){const v=safeJSON(localStorage.getItem(META_KEY),{});return plain(v)?v:{}}
function writeMeta(m){if(!plain(m)||!Object.keys(m).length)return localStorage.removeItem(META_KEY);localStorage.setItem(META_KEY,JSON.stringify(m))}
function record(kind,error,detail={}){
const item={at:new Date().toISOString(),kind:String(kind||'error'),message:String(error?.message||error||'Unknown error'),detail:plain(detail)?detail:{}};
errors.push(item);if(errors.length>25)errors.shift();return item
}
window.addEventListener('error',e=>record('window-error',e.error||e.message,{file:e.filename||'',line:e.lineno||0,column:e.colno||0}));
window.addEventListener('unhandledrejection',e=>record('unhandled-rejection',e.reason));
function manifestURL(){const c=window.MBU_CONTEXT||{};return c.manifestUrl?new URL(c.manifestUrl,location.href):c.examUrl?new URL('banks.json',new URL(c.examUrl,location.href)):new URL('../exam-1/banks.json',runtime.assetsBase)}
async function manifest(){
if(!manifestPromise)manifestPromise=runtime.fetchJSON(manifestURL(),{cache:'no-store'}).catch(e=>{manifestPromise=null;throw e});
return manifestPromise
}
function dynamicTrackedKey(k){return /^mbu_(studio|study_intelligence|generated_questions|course)_/.test(k||'')}
async function trackedKeys(){
const m=await manifest(),keys=new Set(['mbu_exam1_studio_v1','mbu_study_intelligence_v1']);
if(m.sync?.studioStorageKey)keys.add(m.sync.studioStorageKey);
for(const b of m.banks||[])if(b.storageKey)keys.add(b.storageKey);
for(const p of m.hazards?.pages||[])if(p.storageKey)keys.add(p.storageKey);
if(m.features?.questionGenerator?.storageKey)keys.add(m.features.questionGenerator.storageKey);
for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(dynamicTrackedKey(key))keys.add(key)}
for(const key of Object.keys(readMeta()))if(dynamicTrackedKey(key))keys.add(key);
return [...keys].sort()
}
function touchStore(key){
if(!key||key===META_KEY||key===DEVICE_KEY)return null;
const meta=readMeta(),prev=plain(meta[key])?meta[key]:{},entry={revision:(Number(prev.revision)||0)+1,updatedAt:now(),deviceId:deviceId(),serverRevision:Number(prev.serverRevision)||0,dirty:true};
meta[key]=entry;writeMeta(meta);window.MBUSupabase?.scheduleSync?.();return entry
}
function metaRank(x){return [Number(x?.updatedAt)||0,Number(x?.revision)||0,String(x?.deviceId||'')]}
function isRemoteNewer(remote,local){
const remoteServer=Number(remote?.serverRevision)||0,localServer=Number(local?.serverRevision)||0;
if(local?.dirty===true)return false;
if(remoteServer>0&&localServer>0&&remoteServer!==localServer)return remoteServer>localServer;
const a=metaRank(remote),b=metaRank(local);
if(a[0]!==b[0])return a[0]>b[0];
if(a[1]!==b[1])return a[1]>b[1];
return a[2]>b[2]
}
function acknowledgeServerWrite(key,row,submittedMeta){
if(!key||!plain(row)||!plain(submittedMeta))return false;
const meta=readMeta(),current=plain(meta[key])?meta[key]:null;if(!current)return false;
if(Number(current.revision)!==Number(submittedMeta.revision)||Number(current.updatedAt)!==Number(submittedMeta.updatedAt)||String(current.deviceId||'')!==String(submittedMeta.deviceId||''))return false;
meta[key]={...current,serverRevision:Number(row.server_revision)||Number(current.serverRevision)||0,dirty:false};writeMeta(meta);return true
}
async function exportSnapshot(){
const keys=await trackedKeys(),meta=readMeta(),stores={};
for(const key of keys){const raw=localStorage.getItem(key);if(raw!==null)stores[key]=raw}
return{app:APP,schema:SYNC_SCHEMA,createdAt:now(),deviceId:deviceId(),build:window.MBU_BUILD_ID||'',stores,meta:Object.fromEntries(keys.filter(k=>meta[k]).map(k=>[k,meta[k]]))}
}
function validateSnapshot(s){
if(!plain(s)||Number(s.schema)!==SYNC_SCHEMA||!plain(s.stores))throw Error('This is not a compatible SRNA Study Tool backup.');
for(const [key,raw] of Object.entries(s.stores))if(typeof key!=='string'||typeof raw!=='string')throw Error('Backup contains an invalid save entry.');
return s
}
async function importSnapshot(input,{mode='newer'}={}){
const s=validateSnapshot(input),allowed=new Set(await trackedKeys()),localMeta=readMeta(),nextMeta={...localMeta};let imported=0,skipped=0,unknown=0;
for(const [key,raw] of Object.entries(s.stores)){
if(!allowed.has(key)&&!dynamicTrackedKey(key)){unknown++;continue}
const localRaw=localStorage.getItem(key),remoteMeta=plain(s.meta?.[key])?s.meta[key]:{updatedAt:Number(s.createdAt)||0,revision:0,deviceId:String(s.deviceId||'')},should=mode==='replace'||localRaw===null||isRemoteNewer(remoteMeta,localMeta[key]);
if(!should){skipped++;continue}
localStorage.setItem(key,raw);nextMeta[key]={revision:Number(remoteMeta.revision)||0,updatedAt:Number(remoteMeta.updatedAt)||Number(s.createdAt)||now(),deviceId:String(remoteMeta.deviceId||s.deviceId||'import'),serverRevision:Number(remoteMeta.serverRevision)||0,dirty:false};imported++
}
writeMeta(nextMeta);return{imported,skipped,unknown}
}
async function downloadBackup(){
const snapshot=await exportSnapshot(),blob=new Blob([JSON.stringify(snapshot,null,2)+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),a=E('a');
a.href=url;a.download='srna-study-tool-backup-'+new Date().toISOString().slice(0,10)+'.json';B.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),0);return snapshot
}
async function importFile(file,opts){if(!file)throw Error('No backup file selected.');return importSnapshot(JSON.parse(await file.text()),opts)}
function registerAdapter(name,adapter){
if(!name||!plain(adapter)||(typeof adapter.pull!=='function'&&typeof adapter.push!=='function'))throw Error('Sync adapter must implement pull and/or push.');
adapters.set(String(name),adapter);return true
}
async function syncWith(name){
const adapter=adapters.get(String(name));if(!adapter)throw Error('Sync adapter is not registered: '+name);
let merge={imported:0,skipped:0,unknown:0};
if(typeof adapter.pull==='function'){const remote=await adapter.pull({app:APP,schema:SYNC_SCHEMA,deviceId:deviceId()});if(remote)merge=await importSnapshot(remote)}
const snapshot=await exportSnapshot();let pushResult=null;if(typeof adapter.push==='function')pushResult=await adapter.push(snapshot);
return{...merge,pushed:typeof adapter.push==='function',pushResult}
}
function ensureLegalFooter(){
if($('srna-legal-footer'))return;
const privacyURL=new URL('privacy.html',ROOT_URL).href,termsURL=new URL('terms.html',ROOT_URL).href,footer=E('footer');
footer.id='srna-legal-footer';footer.className='srna-legal-footer';footer.innerHTML='<a href="'+privacyURL+'">Privacy Notice</a><span aria-hidden="true">·</span><a href="'+termsURL+'">Terms of Use</a><span>SRNA Study Tool</span>';
B.append(footer)
}
function ensureA11y(){ensureLegalFooter();
let live=$('mbu-app-live');if(!live){live=E('div');live.id='mbu-app-live';live.className='mbu-visually-hidden';live.setAttribute('role','status');live.setAttribute('aria-live','polite');B.append(live)}
if(!Q('.mbu-skip-link')){const a=E('a');a.className='mbu-skip-link';a.href='#mbu-main';a.textContent='Skip to main content';a.onclick=()=>setTimeout(()=>$('mbu-main')?.focus(),0);B.prepend(a)}
const main=Q('#dashboard:not(.hidden),#home:not(.hidden),#main,.container,.wrap');if(main&&!$('mbu-main')){main.id='mbu-main';main.tabIndex=-1}
for(const el of A('.progress,#progress,#qprog')){el.setAttribute('role','status');el.setAttribute('aria-live','polite')}
}
function announce(text){ensureA11y();const live=$('mbu-app-live');if(live){live.textContent='';requestAnimationFrame(()=>{live.textContent=String(text||'')})}}
function focusQuestion(){
const el=$('stem')||$('qstem')||Q('#quiz .stem,#main .stem');
if(el){el.tabIndex=-1;el.focus({preventScroll:true})}
}
function diagnostics(){
return{app:APP,build:window.MBU_BUILD_ID||'',deviceId:deviceId(),url:location.href,online:navigator.onLine,errors:[...errors],syncMeta:readMeta(),userAgent:navigator.userAgent}
}
async function copyDiagnostics(){const text=JSON.stringify(diagnostics(),null,2);if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(text);return text}
function formatTime(ts){return ts?new Date(ts).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'}):'Not yet'}
function lastLocalSave(){const vals=Object.values(readMeta()).map(x=>Number(x?.updatedAt)||0).filter(Boolean);return vals.length?Math.max(...vals):0}
function cloudStatusText(info){
if(!info?.signedIn){if(info?.state==='confirmation-required')return 'Confirmation sent';if(info?.state==='recovery-sent')return 'Reset email sent';return 'Signed out'}
if(info.legalAccepted!==true)return info.state==='error'?'Could not verify account agreement':'Agreement required';
if(info.accessStatus==='suspended')return 'Account access suspended';
if(info.state==='syncing')return 'Syncing';
if(info.state==='error')return 'Sync error';
if(info.lastSyncAt)return 'Synced '+formatTime(info.lastSyncAt);
return 'Connected'
}
function cloudAutoSyncText(info){
if(!info?.signedIn)return 'Starts when signed in';
if(info.legalAccepted!==true)return 'Paused until agreement is accepted';
if(info.accessStatus==='suspended')return 'Sync and Adaptive Mode are suspended';
const mins=Math.max(1,Math.round(Number(info.autoSyncIntervalMs||0)/60000)),next=Number(info.nextAutoSyncAt)||0;
return 'Every '+mins+' min'+(next?'  next '+formatTime(next):'')
}
function modalFocusable(modal){return [...modal.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),a[href],details summary')].filter(x=>x.offsetParent!==null)}
function trapModalKey(e,modal,close){
if(e.key==='Escape'){close();return}
if(e.key!=='Tab')return;
const f=modalFocusable(modal);if(!f.length)return;const first=f[0],last=f[f.length-1],active=document.activeElement,inside=modal.contains(active);
if(e.shiftKey&&(!inside||active===first)){e.preventDefault();last.focus()}
else if(!e.shiftKey&&(!inside||active===last)){e.preventDefault();first.focus()}
}
function closeTools(){const modal=$('mbu-app-tools');if(!modal)return;modal.classList.remove('open');modal.setAttribute('aria-hidden','true');B.classList.remove('mbu-modal-open');toolsReturnFocus?.focus?.();toolsReturnFocus=null}
function closeAccount(){const modal=$('mbu-account-panel');if(!modal)return;modal.classList.remove('open');modal.setAttribute('aria-hidden','true');B.classList.remove('mbu-modal-open');toolsReturnFocus?.focus?.();toolsReturnFocus=null}
function updateCloudChip(){
const b=Q('.mbu-global-nav__cloud');if(!b)return;
const info=window.MBUSupabase?.status?.()||{signedIn:false,state:'unavailable'},label=b.querySelector('[data-cloud-chip-label]');
b.dataset.state=info.state||'signed-out';
label.textContent='Account';
const status=!info.signedIn?'Signed out':info.legalAccepted!==true?'Action required':info.accessStatus==='suspended'?'Suspended':info.state==='syncing'?'Syncing':info.state==='error'?'Sync error':'Synced';
b.title=info.signedIn?(info.email||'Account')+' · '+status:'Account · Signed out';
b.setAttribute('aria-label',b.title)
}
async function refreshTools(){
const modal=$('mbu-app-tools');if(!modal)return;
const keys=await trackedKeys(),saved=keys.filter(k=>localStorage.getItem(k)!==null).length,info=window.MBUSupabase?.status?.()||{signedIn:false,state:'unavailable'},local=lastLocalSave();
modal.querySelector('[data-tools-cloud]').textContent=window.MBUSupabase?cloudStatusText(info):'Unavailable';
modal.querySelector('[data-tools-auto]').textContent=window.MBUSupabase?cloudAutoSyncText(info):'Unavailable';
modal.querySelector('[data-tools-saves]').textContent=saved+' of '+keys.length;
modal.querySelector('[data-tools-saves-help]').textContent=saved?'Saved progress in '+saved+' study area'+(saved===1?'':'s')+' on this device.':'No study progress saved on this device.';
modal.querySelector('[data-tools-local]').textContent=local?formatTime(local):'No saves';
modal.querySelector('[data-build]').textContent=window.MBU_BUILD_ID||'unknown';
modal.querySelector('[data-device]').textContent=deviceId().slice(0,12);
modal.querySelector('[data-errors]').textContent=errors.length?errors.length+' captured':'0 issues detected';
const syncBtn=modal.querySelector('[data-tools-sync]');syncBtn.hidden=!info.signedIn;syncBtn.disabled=info.state==='syncing'||info.legalAccepted!==true||info.accessStatus==='suspended';
modal.querySelector('[data-tools-account]').textContent=info.signedIn?'Manage account':'Sign in';
const suggestionSubmit=modal.querySelector('[data-suggestion-submit]'),suggestionHelp=modal.querySelector('[data-suggestion-help]');if(suggestionSubmit&&suggestionHelp){const suggestionReady=!!info.signedIn&&info.legalAccepted===true&&info.accessStatus==='active';suggestionSubmit.disabled=!suggestionReady;suggestionHelp.textContent=suggestionReady?'Submissions go to the private admin Suggestions inbox.':'Sign in with an active account to submit suggestions.'}
updateCloudChip()
}
function refreshAccount(){
const modal=$('mbu-account-panel');if(!modal)return;
const info=window.MBUSupabase?.status?.()||{signedIn:false,state:'unavailable'},out=modal.querySelector('[data-cloud-signed-out]'),inside=modal.querySelector('[data-cloud-signed-in]'),recovery=modal.querySelector('[data-cloud-recovery]');
out.hidden=!!info.signedIn;inside.hidden=!info.signedIn||!!info.recoveryMode;recovery.hidden=!info.recoveryMode;
modal.querySelector('[data-cloud-user]').textContent=info.email||'';
const legalRequired=modal.querySelector('[data-cloud-legal-required]');
if(legalRequired)legalRequired.hidden=!(info.signedIn&&!info.recoveryMode&&info.legalAccepted!==true);
modal.querySelector('[data-cloud-status]').textContent=window.MBUSupabase?cloudStatusText(info):'Cloud unavailable';
modal.querySelector('[data-cloud-auto]').textContent=window.MBUSupabase?cloudAutoSyncText(info):'';
const syncBtn=modal.querySelector('[data-cloud-sync]');if(syncBtn)syncBtn.disabled=info.legalAccepted!==true||info.accessStatus==='suspended'||info.state==='syncing';
const deviceDetails=modal.querySelector('[data-cloud-devices-details]'),historyDetails=modal.querySelector('[data-cloud-history-details]');
if(deviceDetails)deviceDetails.hidden=info.legalAccepted!==true||info.accessStatus==='suspended';
if(historyDetails)historyDetails.hidden=info.legalAccepted!==true||info.accessStatus==='suspended';
const suspended=modal.querySelector('[data-cloud-suspended]');if(suspended)suspended.hidden=!(info.signedIn&&info.accessStatus==='suspended');
updateCloudChip()
}
let panelStylePromise=null,cloudManagementPromise=null;
async function ensurePanelStyles(){panelStylePromise=panelStylePromise||window.MBUBuild.loadStyle('app-panels.css');await panelStylePromise}
async function loadCloudManagement(){
if(window.SRNACloudManagement)return window.SRNACloudManagement;
cloudManagementPromise=cloudManagementPromise||window.MBUBuild.loadScript('cloud-management.js');
await cloudManagementPromise;
return window.SRNACloudManagement
}
let adminDashboardPromise=null;
async function refreshAdminAccess(modal){const entry=modal?.querySelector('[data-admin-entry]');if(!entry||!window.MBUSupabase)return false;entry.hidden=true;const info=MBUSupabase.status();if(!info.signedIn||info.legalAccepted!==true)return false;try{const admin=await MBUSupabase.adminStatus();entry.hidden=!admin?.is_admin;return!!admin?.is_admin}catch(e){record('admin-status',e);return false}}
async function openAdminDashboard(source){if(!await refreshAdminAccess($('mbu-account-panel')))return;adminDashboardPromise=adminDashboardPromise||window.MBUBuild.loadScript('admin-dashboard.js');await adminDashboardPromise;await window.SRNAAdminDashboard?.open?.(source)}
function ensureAccountPanel(){
if($('mbu-account-panel'))return;
const wrap=E('div'),privacyURL=new URL('privacy.html',ROOT_URL).href,termsURL=new URL('terms.html',ROOT_URL).href;
wrap.innerHTML='<div id="mbu-account-panel" class="mbu-account-panel" role="dialog" aria-modal="true" aria-labelledby="mbu-account-title" aria-hidden="true"><div class="mbu-account-panel__card"><div class="mbu-app-tools__head"><div><div class="mbu-section-kicker">Cloud account</div><h2 id="mbu-account-title">Sign in</h2><p class="mbu-modal-subtitle" data-account-subtitle>Sync progress and access Adaptive Mode.</p></div><button type="button" class="mbu-modal-close" data-account-close aria-label="Close account">x</button></div><div data-cloud-signed-out><div class="mbu-auth-switch" role="tablist" aria-label="Account action"><button type="button" role="tab" aria-selected="true" class="active" data-auth-view="signin">Sign in</button><button type="button" role="tab" aria-selected="false" data-auth-view="signup">Create account</button></div><section class="mbu-auth-view" data-auth-signin><label>Email<input type="email" data-cloud-email autocomplete="email"></label><label>Password<input type="password" data-cloud-password autocomplete="current-password"></label><button type="button" class="mbu-primary-action" data-cloud-signin>Sign in</button><div class="mbu-auth-links"><button type="button" data-cloud-forgot>Forgot password?</button><span aria-hidden="true">·</span><button type="button" data-cloud-resend>Resend confirmation</button></div><p class="mbu-auth-foot">Don\'t have an account? <button type="button" data-auth-go-signup>Create one</button></p></section><section class="mbu-auth-view" data-auth-signup hidden><label>Email<input type="email" data-cloud-signup-email autocomplete="email"></label><label>Password<input type="password" data-cloud-signup-password autocomplete="new-password" minlength="8" aria-describedby="mbu-signup-password-rules"><small id="mbu-signup-password-rules" class="mbu-field-help">Password must be at least 8 characters.</small></label><label>Confirm password<input type="password" data-cloud-signup-confirm autocomplete="new-password" minlength="8"></label><label class="mbu-consent"><input type="checkbox" data-cloud-consent> <span>I am at least 18 years old. I agree to the <a href="'+termsURL+'" target="_blank" rel="noopener">Terms of Use</a> and acknowledge the <a href="'+privacyURL+'" target="_blank" rel="noopener">Privacy Notice</a>.</span></label><button type="button" class="mbu-primary-action" data-cloud-signup>Create account</button><p class="mbu-account-privacy">First-attempt performance may be used to improve questions and Adaptive Mode. Calibration results are aggregated. <a href="'+privacyURL+'" target="_blank" rel="noopener">Read the full Privacy Notice.</a></p><p class="mbu-auth-foot">Already have an account? <button type="button" data-auth-go-signin>Sign in</button></p></section></div><div data-cloud-signed-in hidden><div class="mbu-account-hero"><div class="mbu-account-identity"><span class="mbu-status-dot"></span><div><span class="mbu-muted">Signed in as</span><strong data-cloud-user></strong></div></div><div class="mbu-account-status"><span class="mbu-account-status__label">Status</span><strong data-cloud-status></strong><span data-cloud-auto></span></div></div><div data-cloud-legal-required hidden class="mbu-tools-section mbu-attention-card"><h3>Updated account agreement required</h3><p>Accept the current Terms and Privacy Notice to continue cloud sync or Adaptive Mode.</p><label class="mbu-consent"><input type="checkbox" data-cloud-reaccept-consent> <span>I am at least 18 years old. I agree to the current <a href="'+termsURL+'" target="_blank" rel="noopener">Terms of Use</a> and acknowledge the current <a href="'+privacyURL+'" target="_blank" rel="noopener">Privacy Notice</a>.</span></label><div class="mbu-app-tools__actions"><button type="button" data-cloud-reaccept>Accept and continue</button></div></div><div data-cloud-suspended hidden class="mbu-tools-section mbu-attention-card"><h3>Account access suspended</h3><p>Sync and Adaptive Mode are suspended. Privacy, sign out, and account deletion remain available.</p></div><div class="mbu-account-primary-actions"><button type="button" class="mbu-primary-action" data-cloud-sync>Sync now</button><button type="button" class="mbu-text-action" data-cloud-signout>Sign out</button></div><div class="mbu-account-sections"><details class="mbu-tools-details" data-account-stats-details><summary><span><strong>Account statistics</strong><small>Your question progress across all courses</small></span></summary><div class="mbu-tools-details__body"><div data-account-stats></div></div></details><details class="mbu-tools-details" data-cloud-devices-details><summary><span><strong>Devices</strong><small>Browsers that have synced this account</small></span></summary><div class="mbu-tools-details__body"><p>Forget old device entries. This does not sign out that browser.</p><div data-cloud-devices></div></div></details><details class="mbu-tools-details" data-cloud-history-details><summary><span><strong>Restore progress</strong><small>Recover a recent synced version</small></span></summary><div class="mbu-tools-details__body"><p>Recent restore points are kept automatically. Restoring also preserves your current cloud progress first.</p><div data-cloud-history></div></div></details><details class="mbu-tools-details"><summary><span><strong>Privacy & account</strong><small>Legal, privacy, and deletion controls</small></span></summary><div class="mbu-tools-details__body"><p><a href="'+privacyURL+'" target="_blank" rel="noopener">Privacy Notice</a> · <a href="'+termsURL+'" target="_blank" rel="noopener">Terms of Use</a></p><label>Request type<select data-privacy-type><option value="access">Access</option><option value="correction">Correction</option><option value="deletion">Deletion</option><option value="appeal">Appeal decision</option><option value="other">Other</option></select></label><label>Details<textarea data-privacy-details maxlength="4000" rows="3" placeholder="Details (optional)"></textarea></label><div class="mbu-app-tools__actions"><button type="button" data-privacy-submit>Submit request</button></div><div class="mbu-danger-zone"><strong>Delete account</strong><p>Deletion removes cloud data and cannot be undone.</p><button type="button" class="mbu-danger-action" data-cloud-delete-account>Delete account & data</button></div></div></details></div><section class="mbu-tools-section mbu-admin-entry" data-admin-entry hidden><div class="mbu-section-heading"><div><h3>Admin Dashboard</h3><p>Operator analytics, account administration, reports, and compliance tools.</p></div><button type="button" class="secondary" data-admin-open>Open dashboard</button></div></section></div><div data-cloud-recovery hidden><p class="mbu-modal-subtitle">Choose a new account password.</p><label>New password<input type="password" data-cloud-new-password autocomplete="new-password" minlength="8"></label><button type="button" class="mbu-primary-action" data-cloud-update-password>Update password</button></div><div class="mbu-app-tools__status" data-account-message role="status" aria-live="polite"></div></div></div>';
B.append(wrap);
const modal=$('mbu-account-panel'),email=modal.querySelector('[data-cloud-email]'),password=modal.querySelector('[data-cloud-password]'),signupEmail=modal.querySelector('[data-cloud-signup-email]'),signupPassword=modal.querySelector('[data-cloud-signup-password]'),signupConfirm=modal.querySelector('[data-cloud-signup-confirm]'),newPassword=modal.querySelector('[data-cloud-new-password]'),consent=modal.querySelector('[data-cloud-consent]'),message=modal.querySelector('[data-account-message]'),title=modal.querySelector('#mbu-account-title'),subtitle=modal.querySelector('[data-account-subtitle]');
const setAuthView=view=>{const signup=view==='signup';modal.querySelector('[data-auth-signin]').hidden=signup;modal.querySelector('[data-auth-signup]').hidden=!signup;modal.querySelectorAll('[data-auth-view]').forEach(btn=>{const active=btn.dataset.authView===view;btn.classList.toggle('active',active);btn.setAttribute('aria-selected',String(active))});title.textContent=signup?'Create account':'Sign in';subtitle.textContent=signup?'Create an account for sync and Adaptive Mode.':'Sync progress and access Adaptive Mode.';(signup?signupEmail:email)?.focus()};
modal.querySelectorAll('[data-auth-view]').forEach(btn=>btn.onclick=()=>setAuthView(btn.dataset.authView));
modal.querySelector('[data-auth-go-signup]').onclick=()=>setAuthView('signup');
modal.querySelector('[data-auth-go-signin]').onclick=()=>setAuthView('signin');
const action=async fn=>{try{message.textContent='Working';await fn();password.value='';signupPassword.value='';signupConfirm.value='';message.textContent='';refreshAccount();await refreshAdminAccess(modal);await refreshTools()}catch(e){record('cloud-sync',e);message.textContent=e.message;refreshAccount()}};
modal.querySelector('[data-cloud-signin]').onclick=()=>action(()=>MBUSupabase.signIn(email.value,password.value));
const reaccept=modal.querySelector('[data-cloud-reaccept]'),reacceptConsent=modal.querySelector('[data-cloud-reaccept-consent]');if(reaccept)reaccept.onclick=()=>{if(!reacceptConsent?.checked){message.textContent='Confirm that you are 18+ and agree to the current Terms and Privacy Notice.';return}action(()=>MBUSupabase.acceptCurrentLegal(true))};
modal.querySelector('[data-cloud-signup]').onclick=()=>{if(signupPassword.value.length<8){message.textContent='Password must be at least 8 characters.';signupPassword.focus();return}if(signupPassword.value!==signupConfirm.value){message.textContent='Passwords do not match.';signupConfirm.focus();return}if(!consent.checked){message.textContent='Confirm that you are 18+ and agree to the Terms and Privacy Notice before creating an account.';return}action(()=>MBUSupabase.signUp(signupEmail.value,signupPassword.value,true))};
modal.querySelector('[data-cloud-forgot]').onclick=()=>action(()=>MBUSupabase.requestPasswordReset(email.value));
modal.querySelector('[data-cloud-resend]').onclick=()=>action(()=>MBUSupabase.resendConfirmation(email.value));
modal.querySelector('[data-cloud-update-password]').onclick=()=>action(()=>MBUSupabase.updatePassword(newPassword.value));
modal.querySelector('[data-cloud-sync]').onclick=()=>action(()=>MBUSupabase.syncNow());
modal.querySelector('[data-cloud-signout]').onclick=()=>action(()=>MBUSupabase.signOut());
modal.querySelector('[data-cloud-delete-account]').onclick=async()=>{if(!confirm('Delete your SRNA Study Tool account and account-linked cloud data? This cannot be undone.'))return;if(!confirm('Final confirmation: permanently delete this account?'))return;try{message.textContent='Deleting account…';await MBUSupabase.deleteAccount();message.textContent='Account deleted.';closeAccount();location.assign(ROOT_URL.href)}catch(e){record('account-delete',e);message.textContent=e.message;refreshAccount()}};
const privacySubmit=modal.querySelector('[data-privacy-submit]');if(privacySubmit)privacySubmit.onclick=async()=>{try{privacySubmit.disabled=true;message.textContent='Submitting…';const id=await MBUSupabase.submitPrivacyRequest(modal.querySelector('[data-privacy-type]').value,modal.querySelector('[data-privacy-details]').value);modal.querySelector('[data-privacy-details]').value='';message.textContent='Privacy request received'+(id?' (#'+id+')':'')+'.'}catch(e){record('privacy-request',e);message.textContent=e.message}finally{privacySubmit.disabled=false}};
modal.querySelector('[data-account-stats-details]').ontoggle=async e=>{if(e.currentTarget.open)(await loadCloudManagement()).renderStats(modal)};
modal.querySelector('[data-cloud-devices-details]').ontoggle=async e=>{if(e.currentTarget.open)(await loadCloudManagement()).renderDevices(modal)};
modal.querySelector('[data-cloud-history-details]').ontoggle=async e=>{if(e.currentTarget.open)(await loadCloudManagement()).renderHistory(modal)};
const adminOpen=modal.querySelector('[data-admin-open]');if(adminOpen)adminOpen.onclick=()=>openAdminDashboard(adminOpen);
modal.querySelector('[data-account-close]').onclick=closeAccount;modal.onclick=e=>{if(e.target===modal)closeAccount()};modal.onkeydown=e=>trapModalKey(e,modal,closeAccount);
}
async function openAccount(source){
await ensurePanelStyles();ensureAccountPanel();toolsReturnFocus=source||document.activeElement;const modal=$('mbu-account-panel');B.classList.add('mbu-modal-open');modal.classList.add('open');modal.setAttribute('aria-hidden','false');refreshAccount();
const info=window.MBUSupabase?.status?.(),title=modal.querySelector('#mbu-account-title'),subtitle=modal.querySelector('[data-account-subtitle]');
if(info?.recoveryMode){title.textContent='Reset password';subtitle.textContent='Secure your SRNA Study Tool account.'}
else if(info?.signedIn){title.textContent='Cloud & account';subtitle.textContent='Sync status, devices, restore history, and settings.'}
else{title.textContent='Sign in';subtitle.textContent='Sync progress and access Adaptive Mode.'}
await refreshAdminAccess(modal);(info?.recoveryMode?modal.querySelector('[data-cloud-new-password]'):info?.signedIn&&info.legalAccepted!==true?modal.querySelector('[data-cloud-reaccept-consent]'):info?.signedIn?modal.querySelector('[data-cloud-sync]'):modal.querySelector('[data-cloud-email]'))?.focus()
}
function ensureTools(){
if($('mbu-app-tools'))return;
const privacyURL=new URL('privacy.html',ROOT_URL).href,termsURL=new URL('terms.html',ROOT_URL).href,wrap=E('div');wrap.innerHTML='<div id="mbu-app-tools" class="mbu-app-tools" role="dialog" aria-modal="true" aria-labelledby="mbu-app-tools-title" aria-hidden="true"><div class="mbu-app-tools__card"><div class="mbu-app-tools__head"><div><div class="mbu-section-kicker">Study utility center</div><h2 id="mbu-app-tools-title">Tools</h2><p class="mbu-modal-subtitle">Backup, sync, and troubleshoot your study data.</p></div><button type="button" class="mbu-modal-close" data-close aria-label="Close tools">x</button></div><section class="mbu-tools-section mbu-tools-overview"><div class="mbu-section-heading"><div><h3>Progress & sync</h3><p>Current local and cloud status.</p></div><button type="button" class="mbu-text-action" data-tools-account>Manage account</button></div><div class="mbu-tools-grid mbu-tools-grid--status"><div><span>Cloud</span><strong data-tools-cloud></strong></div><div><span>Auto sync</span><strong data-tools-auto></strong></div><div><span>Saved study areas</span><strong data-tools-saves></strong><small data-tools-saves-help></small></div><div><span>Last local save</span><strong data-tools-local></strong></div></div><div class="mbu-app-tools__actions"><button type="button" data-tools-sync>Sync now</button></div><p class="mbu-app-tools__note">Progress saves locally. Sign in for cross-device cloud backup.</p></section><section class="mbu-tools-section"><div class="mbu-section-heading"><div><h3>Suggestions</h3><p>Send an idea, bug report, content correction, or improvement directly to the site admin.</p></div></div><div class="mbu-suggestion-form"><label>Type<select data-suggestion-category><option value="idea">Feature / improvement</option><option value="bug">Bug</option><option value="content">Content correction</option><option value="other">Other</option></select></label><label>Suggestion<textarea data-suggestion-message maxlength="1500" rows="4" placeholder="What should be added, fixed, or improved?"></textarea></label><div class="mbu-suggestion-footer"><small data-suggestion-help>Sign in to submit suggestions.</small><button type="button" class="mbu-primary-action" data-suggestion-submit>Send suggestion</button></div></div></section><section class="mbu-tools-section"><div class="mbu-section-heading"><div><h3>Backup & recovery</h3><p>Download or restore a portable progress backup.</p></div></div><div class="mbu-backup-actions"><button type="button" data-export><strong>Download backup</strong><span>Save a portable progress copy</span></button><button type="button" data-import><strong>Import backup</strong><span>Restore from a saved backup</span></button></div><input type="file" data-file accept="application/json,.json" hidden></section><details class="mbu-tools-details"><summary><span><strong>Troubleshooting & app info</strong><small>Diagnostics, build, and device</small></span></summary><div class="mbu-tools-details__body"><div class="mbu-tools-grid compact"><div><span>Issues</span><strong data-errors></strong></div><div><span>Device</span><strong data-device></strong></div><div class="wide"><span>Build</span><strong data-build></strong></div></div><div class="mbu-tools-legal-links"><a href="'+privacyURL+'" target="_blank" rel="noopener">Privacy Notice</a><span aria-hidden="true">·</span><a href="'+termsURL+'" target="_blank" rel="noopener">Terms of Use</a></div><div class="mbu-app-tools__actions"><button type="button" class="secondary" data-copy>Copy</button></div></div></details><div class="mbu-app-tools__status" role="status" aria-live="polite"></div></div></div>';B.append(wrap);
const modal=$('mbu-app-tools'),status=modal.querySelector('.mbu-app-tools__status'),file=modal.querySelector('[data-file]');
modal.querySelector('[data-close]').onclick=closeTools;modal.onclick=e=>{if(e.target===modal)closeTools()};modal.onkeydown=e=>trapModalKey(e,modal,closeTools);
const suggestionCategory=modal.querySelector('[data-suggestion-category]'),suggestionMessage=modal.querySelector('[data-suggestion-message]'),suggestionHelp=modal.querySelector('[data-suggestion-help]'),suggestionSubmit=modal.querySelector('[data-suggestion-submit]');
const refreshSuggestionState=()=>{const info=window.MBUSupabase?.status?.()||{};const ready=!!info.signedIn&&info.legalAccepted===true&&info.accessStatus==='active';suggestionSubmit.disabled=!ready;suggestionHelp.textContent=ready?'Submissions go to the private admin Suggestions inbox.':'Sign in with an active account to submit suggestions.'};
refreshSuggestionState();
suggestionSubmit.onclick=async()=>{const messageText=String(suggestionMessage.value||'').trim();if(messageText.length<3){status.textContent='Enter a suggestion before sending.';suggestionMessage.focus();return}try{suggestionSubmit.disabled=true;status.textContent='Sending suggestion…';const id=await MBUSupabase.submitSuggestion(suggestionCategory.value,messageText);suggestionMessage.value='';status.textContent='Suggestion sent'+(id?' (#'+id+')':'')+'. Thank you.';}catch(e){record('suggestion-submit',e);status.textContent='Suggestion failed: '+e.message}finally{refreshSuggestionState()}};
modal.querySelector('[data-tools-account]').onclick=()=>{closeTools();openAccount(Q('.mbu-global-nav__cloud')||Q('.mbu-global-nav__tools'))};
modal.querySelector('[data-tools-sync]').onclick=async()=>{try{status.textContent='Syncing';await MBUSupabase.syncNow();status.textContent='Synced';await refreshTools()}catch(e){record('cloud-sync',e);status.textContent='Sync failed: '+e.message}};
modal.querySelector('[data-export]').onclick=async()=>{try{await downloadBackup();status.textContent='Backup saved'}catch(e){record('backup-export',e);status.textContent='Backup failed: '+e.message}};
modal.querySelector('[data-import]').onclick=()=>file.click();
file.onchange=async()=>{try{const result=await importFile(file.files?.[0]);const parts=['Imported '+result.imported+' newer study area'+(result.imported===1?'':'s')];if(result.skipped)parts.push('kept '+result.skipped+' current/newer area'+(result.skipped===1?'':'s'));if(result.unknown)parts.push('ignored '+result.unknown+' unknown/legacy entr'+(result.unknown===1?'y':'ies'));status.textContent=parts.join(' · ')+'. Reload this page to use imported progress.';await refreshTools()}catch(e){record('backup-import',e);status.textContent='Import failed: '+e.message}finally{file.value=''}};
modal.querySelector('[data-copy]').onclick=async()=>{try{await copyDiagnostics();status.textContent='Diagnostics copied.'}catch(e){status.textContent='Could not copy diagnostics.'}}
}
async function openTools(source){await ensurePanelStyles();ensureTools();toolsReturnFocus=source||document.activeElement;const modal=$('mbu-app-tools');B.classList.add('mbu-modal-open');modal.classList.add('open');modal.setAttribute('aria-hidden','false');await refreshTools();modal.querySelector('[data-close]').focus()}
function mountNav(nav){
if(!nav||nav.querySelector('.mbu-global-nav__utilities'))return;
const utilities=E('div');utilities.className='mbu-global-nav__utilities';
const search=E('button');search.type='button';search.className='mbu-global-nav__search';search.textContent='Search';search.setAttribute('aria-label','Search all questions');search.onclick=async()=>{await ensurePanelStyles();if(!window.MBUQuestionSearch)await window.MBUBuild?.loadScript?.('question-search.js');window.MBUQuestionSearch?.open?.(search)};
const cloud=E('button');cloud.type='button';cloud.className='mbu-global-nav__cloud';cloud.innerHTML='<span class="mbu-status-dot" aria-hidden="true"></span><span data-cloud-chip-label>Account</span>';cloud.onclick=()=>openAccount(cloud);
const tools=E('button');tools.type='button';tools.className='mbu-global-nav__tools';tools.textContent='Tools';tools.setAttribute('aria-label','Open tools and diagnostics');tools.onclick=()=>openTools(tools);
utilities.append(search,cloud,tools);nav.append(utilities);updateCloudChip()
}
window.addEventListener('mbu:supabase-status',()=>{refreshAccount();refreshTools();updateCloudChip()});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ensureA11y,{once:true});else ensureA11y();
window.MBUDiagnostics={record,snapshot:diagnostics,copy:copyDiagnostics};
window.MBUSync={APP,schema:SYNC_SCHEMA,deviceId,touchStore,acknowledgeServerWrite,trackedKeys,exportSnapshot,importSnapshot,downloadBackup,importFile,registerAdapter,syncWith};
window.MBUAppCore={ensureA11y,announce,focusQuestion,mountNav,openTools,openAccount,closeAccount,touchStore,diagnostics};
})();