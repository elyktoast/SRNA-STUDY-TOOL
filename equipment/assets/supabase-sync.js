(()=>{'use strict';
const cfg=window.MBU_SUPABASE_CONFIG||{},sync=window.MBUSync,SESSION_KEY='mbu_supabase_session_v1',OWNER_KEY='mbu_cloud_local_owner_v1',META_KEY='mbu_sync_meta_v1',STATUS_EVENT='mbu:supabase-status',script=document.currentScript,APP_ROOT=new URL('../../',script?.src||location.href).href;
if(!cfg.url||!cfg.publishableKey||!sync){console.warn('Supabase sync is not configured');return}
const base=cfg.url.replace(/\/$/,''),REQUEST_TIMEOUT=10000,AUTO_SYNC_INTERVAL=5*60*1000,LEGAL_VERSION='2026-09-27-v6',LEGAL_TERMS_VERSION=LEGAL_VERSION,LEGAL_PRIVACY_VERSION=LEGAL_VERSION;
let syncing=false,syncQueued=false,lastSyncAt=0,lastState='signed-out',remoteByKey=new Map(),calibrationByKey=new Map(),calibrationFetchedAt=0,timer=null,autoSyncTimer=null,guestTimer=null,recoveryMode=false,legalAccepted=null,accountAccess='signed_out';
const safeJSON=(raw,fallback=null)=>{try{return JSON.parse(raw)}catch{return fallback}};
const session=()=>safeJSON(localStorage.getItem(SESSION_KEY));
async function clearTrackedLocalData(){for(const key of Object.keys((await sync.exportSnapshot()).stores||{}))localStorage.removeItem(key);localStorage.removeItem(META_KEY)}
async function prepareLocalOwner(userId){const id=String(userId||'');if(!id)return false;const owner=localStorage.getItem(OWNER_KEY),switched=!!owner&&owner!==id;if(switched)await clearTrackedLocalData();if(owner!==id)localStorage.setItem(OWNER_KEY,id);return switched}
const emit=(state,detail={})=>{lastState=state;window.dispatchEvent(new CustomEvent(STATUS_EVENT,{detail:{state,lastSyncAt,...detail}}))};
function normalizeAuth(data){const source=data?.session||data;if(!source?.access_token||!source?.refresh_token)return null;const expiresAt=Number(source.expires_at)||Math.floor(Date.now()/1000)+(Number(source.expires_in)||3600);return{access_token:source.access_token,refresh_token:source.refresh_token,expires_at:expiresAt,user:data?.user||source.user||null}}
function saveSession(s){if(s)localStorage.setItem(SESSION_KEY,JSON.stringify(s));else localStorage.removeItem(SESSION_KEY)}
async function hydrateUser(s){if(!s?.access_token)return s;try{const user=await raw('/auth/v1/user',{token:s.access_token});return{...s,user:user||s.user||null}}catch{return s}}
async function consumeAuthRedirect(){
if(!location.hash||location.hash.length<2)return null;
const p=new URLSearchParams(location.hash.slice(1)),error=p.get('error_description')||p.get('error');
if(error){
history.replaceState(null,'',location.pathname+location.search);
emit('error',{error});
return null
}
if(!p.get('access_token')||!p.get('refresh_token'))return null;
let s=normalizeAuth({
access_token:p.get('access_token'),
refresh_token:p.get('refresh_token'),
expires_in:Number(p.get('expires_in')||3600),
expires_at:Number(p.get('expires_at')||0)
});
if(!s)return null;
s=await hydrateUser(s);if(!s?.user?.id)throw Error('Could not verify the signed-in account.');recoveryMode=p.get('type')==='recovery';
history.replaceState(null,'',location.pathname+location.search);
emit(recoveryMode?'password-recovery':'signed-in',{email:s.user?.email||''});
return s
}
async function raw(path,{method='GET',body,token,headers={}}={}){
const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),REQUEST_TIMEOUT);
try{
const response=await fetch(base+path,{method,headers:{apikey:cfg.publishableKey,'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{}),...headers},body:body===undefined?undefined:JSON.stringify(body),signal:ctl.signal});
const text=await response.text();const data=text?safeJSON(text,text):null;
if(!response.ok){const msg=(data&&typeof data==='object'&&(data.msg||data.message||data.error_description||data.error))||('HTTP '+response.status);const e=Error(String(msg));e.status=response.status;throw e}
return data
}finally{clearTimeout(timer)}
}
async function refresh(){
const s=session();if(!s?.refresh_token)return null;
try{const data=await raw('/auth/v1/token?grant_type=refresh_token',{method:'POST',body:{refresh_token:s.refresh_token}}),next=normalizeAuth(data);saveSession(next);return next}
catch(e){if([400,401,403].includes(e?.status)){saveSession(null);legalAccepted=null;accountAccess='signed_out';emit('signed-out',{error:e.message})}else emit('error',{error:'Session refresh failed: '+e.message});return null}
}
async function validSession(){
let s=session();if(!s)return null;
if(Number(s.expires_at||0)*1000-Date.now()<60000)s=await refresh();
return s
}
async function api(path,opts={}){
const s=await validSession();if(!s?.access_token)throw Error('Sign in to use cloud sync.');
return raw(path,{...opts,token:s.access_token})
}
const writeState=(key,payload,meta,expected)=>api('/rest/v1/rpc/mbu_sync_write_state',{method:'POST',body:{p_store_key:key,p_payload:payload,p_device_id:String(meta.deviceId||sync.deviceId()),p_client_revision:Number(meta.revision)||0,p_client_updated_at:new Date(Number(meta.updatedAt)||Date.now()).toISOString(),p_expected_server_revision:Number(expected)||0}});
const adminRpc=(name,body={})=>{requireLegal();return api('/rest/v1/rpc/'+name,{method:'POST',body})};
async function refreshLegalAcceptance(){
const s=await validSession();if(!s?.access_token){legalAccepted=null;return false}
try{
const ok=await raw('/rest/v1/rpc/snar_has_current_legal_acceptance',{method:'POST',token:s.access_token,body:{p_terms_version:LEGAL_TERMS_VERSION,p_privacy_version:LEGAL_PRIVACY_VERSION}});
legalAccepted=ok===true;return legalAccepted
}catch(e){
legalAccepted=null;emit('error',{email:s.user?.email||'',error:'Could not verify account agreement: '+e.message});return false
}
}
async function refreshAccountAccess(){
const s=await validSession();if(!s?.access_token){accountAccess='signed_out';return accountAccess}
try{accountAccess=String(await raw('/rest/v1/rpc/snar_account_access_status',{method:'POST',token:s.access_token,body:{}})||'unknown')}
catch{accountAccess='unknown'}
return accountAccess
}
function requireAccountAccess(){
requireLegal();
if(accountAccess!=='active')throw Error('This account\'s cloud and Adaptive Mode access is suspended.')
}
function guestSessionId(){
let id=sessionStorage.getItem('snar_guest_session_v1');
if(!id){
id=globalThis.crypto?.randomUUID?.()||('00000000-0000-4000-8000-'+Math.random().toString(16).slice(2,14).padEnd(12,'0'));
sessionStorage.setItem('snar_guest_session_v1',id);
}
return id
}
async function guestHeartbeat(){
if(session())return false;
try{return await raw('/rest/v1/rpc/snar_guest_heartbeat',{method:'POST',body:{p_session_id:guestSessionId()}})===true}catch{return false}
}
function stopGuestHeartbeat(){if(guestTimer){clearInterval(guestTimer);guestTimer=null}}
function startGuestHeartbeat(){
stopGuestHeartbeat();if(session())return;
guestHeartbeat().catch(()=>{});
guestTimer=setInterval(()=>{if(!session())guestHeartbeat().catch(()=>{})},5*60*1000)
}
async function acceptCurrentLegal(adultAck=false){
if(adultAck!==true)throw Error('Confirm that you are 18+ and agree to the current Terms and Privacy Notice.');
const s=await validSession();if(!s?.access_token)throw Error('Sign in first.');
const ok=await raw('/rest/v1/rpc/snar_accept_current_legal',{method:'POST',token:s.access_token,body:{p_terms_version:LEGAL_TERMS_VERSION,p_privacy_version:LEGAL_PRIVACY_VERSION,p_adult_ack:true}});
legalAccepted=ok===true;if(!legalAccepted)throw Error('Could not record legal acceptance.');
await refreshAccountAccess();
if(accountAccess!=='active'){emit('access-suspended',{email:s.user?.email||''});return true}
emit('signed-in',{email:s.user?.email||''});
stopGuestHeartbeat();startAutoSync();
setTimeout(()=>fullSync({reloadOnImport:false}).catch(()=>{}),50);
setTimeout(()=>refreshCalibration(true).catch(()=>{}),100);
return true
}
async function signIn(email,password){
emit('signing-in');const data=await raw('/auth/v1/token?grant_type=password',{method:'POST',body:{email:String(email||'').trim(),password:String(password||'')}});
const s=normalizeAuth(data);if(!s)throw Error('Supabase did not return a session.');const switched=await prepareLocalOwner(s.user?.id);saveSession(s);stopGuestHeartbeat();if(switched){emit('local-owner-changed',{email:s.user?.email||email});return s}if(!await refreshLegalAcceptance()){emit('legal-required',{email:s.user?.email||email});return s}await refreshAccountAccess();if(accountAccess!=='active'){emit('access-suspended',{email:s.user?.email||email});return s}emit('signed-in',{email:s.user?.email||email});await fullSync({reloadOnImport:false});startAutoSync();return s
}
async function signUp(email,password,accepted=false){
if(accepted!==true)throw Error('You must confirm that you are 18+ and agree to the Terms and Privacy Notice before creating an account.');
const acceptedAt=new Date().toISOString();emit('signing-up');const data=await raw('/auth/v1/signup?redirect_to='+encodeURIComponent(APP_ROOT),{method:'POST',body:{email:String(email||'').trim(),password:String(password||''),data:{snar_terms_version:LEGAL_TERMS_VERSION,snar_privacy_version:LEGAL_PRIVACY_VERSION,snar_adult_ack:true,snar_accepted_at:acceptedAt}}}),s=normalizeAuth(data);
if(s){const switched=await prepareLocalOwner(s.user?.id);saveSession(s);stopGuestHeartbeat();if(switched){emit('local-owner-changed',{email:s.user?.email||email});return{session:s,confirmationRequired:false}}if(!await refreshLegalAcceptance())await acceptCurrentLegal(true);else{await refreshAccountAccess();if(accountAccess==='active'){emit('signed-in',{email:s.user?.email||email});await fullSync({reloadOnImport:false});startAutoSync()}else emit('access-suspended',{email:s.user?.email||email})}return{session:s,confirmationRequired:false}}
emit('confirmation-required',{email:String(email||'').trim()});return{session:null,confirmationRequired:true}
}
function resetCloudSession(){stopAutoSync();clearTimeout(timer);timer=0;syncQueued=false;saveSession(null);sessionStorage.removeItem('mbu_post_auth_target');legalAccepted=null;accountAccess='signed_out';remoteByKey.clear();calibrationByKey.clear();calibrationFetchedAt=0;emit('signed-out');startGuestHeartbeat()}async function signOut(){
const s=session();if(s?.access_token&&legalAccepted===true&&accountAccess==='active'){if(!navigator.onLine)throw Error('Reconnect');try{await fullSync()}catch{throw Error('Sync failed')}}
try{if(s?.access_token)await raw('/auth/v1/logout',{method:'POST',token:s.access_token})}catch{}
await clearTrackedLocalData();localStorage.removeItem(OWNER_KEY);resetCloudSession()
}
async function resendConfirmation(email){const value=String(email||'').trim();if(!value)throw Error('Enter your email address first.');await raw('/auth/v1/resend?redirect_to='+encodeURIComponent(APP_ROOT),{method:'POST',body:{type:'signup',email:value}});emit('confirmation-required',{email:value});return true}
async function requestPasswordReset(email){const value=String(email||'').trim();if(!value)throw Error('Enter your email address first.');await raw('/auth/v1/recover?redirect_to='+encodeURIComponent(APP_ROOT),{method:'POST',body:{email:value}});emit('recovery-sent',{email:value});return true}
async function updatePassword(password){const value=String(password||'');if(value.length<8)throw Error('Password must be at least 8 characters.');const s=await validSession();if(!s?.access_token)throw Error('Open the password reset link from your email first.');await raw('/auth/v1/user',{method:'PUT',token:s.access_token,body:{password:value}});recoveryMode=false;if(!await refreshLegalAcceptance()){emit('legal-required',{email:s.user?.email||''});return true}await refreshAccountAccess();if(accountAccess==='active'){emit('signed-in',{email:s.user?.email||''});startAutoSync()}else emit('access-suspended',{email:s.user?.email||''});return true}
function currentUser(){return session()?.user||null}
async function deleteAccount(){
const s=await validSession();if(!s?.access_token)throw Error('Sign in to delete your account.');
await raw('/functions/v1/delete-account',{method:'POST',body:{},token:s.access_token});
await clearTrackedLocalData();localStorage.removeItem(OWNER_KEY);
resetCloudSession();return true
}
async function submitSuggestion(category,message){
requireAccountAccess();
const cleaned=String(message||'').trim();if(cleaned.length<3)throw Error('Enter a suggestion before sending.');if(cleaned.length>1500)throw Error('Suggestion must be 1500 characters or fewer.');
const id=await api('/rest/v1/rpc/snar_submit_suggestion',{method:'POST',body:{p_category:String(category||'idea'),p_message:cleaned}});
return Number(id)||0
}
async function submitQuestionReport(report){
requireAccountAccess();
const id=await api('/rest/v1/rpc/snar_submit_question_report',{method:'POST',body:{p_report:report&&typeof report==='object'?report:{}}});
return Number(id)||0
}
async function submitPrivacyRequest(requestType,details=''){
const s=await validSession();if(!s?.user?.id)throw Error('Sign in to submit a privacy request.');
const type=String(requestType||'').toLowerCase();
if(!['access','correction','deletion','appeal','other'].includes(type))throw Error('Choose a valid privacy request type.');
const rows=await api('/rest/v1/snar_privacy_requests',{method:'POST',body:{user_id:s.user.id,request_type:type,details:String(details||'').slice(0,4000)},headers:{Prefer:'return=representation'}});
return Number(rows?.[0]?.id)||0
}
function requireLegal(){if(legalAccepted!==true)throw Error('Accept the current Terms and Privacy Notice first.')}
async function submitItemContribution(x){
requireAccountAccess();if(!x?.questionId)return false;
return await api('/rest/v1/rpc/mbu_submit_item_contribution_v2',{method:'POST',body:{p_question_id:x.questionId,p_correct:!!x.correct,p_response_ms:x.responseMs??null,p_session_mode:x.sessionMode||'unknown',p_course_id:x.courseId||window.MBU_CONTEXT?.courseId||'?',p_exam_id:x.examId||window.MBU_CONTEXT?.examId||'?',p_bank_id:x.bankId||'unknown',p_topic:x.topic||'Other'}})===true
}
async function refreshCalibration(force=false){
requireAccountAccess();if(!force&&calibrationFetchedAt&&Date.now()-calibrationFetchedAt<300000)return calibrationByKey;
const rows=await api('/rest/v1/mbu_item_calibration?select=question_id,unique_learners,correct_first_attempts,incorrect_first_attempts,adaptive_first_attempts,response_samples,avg_response_ms,p_value,difficulty_logit,standard_error,confidence,updated_at');calibrationByKey=new Map((rows||[]).map(r=>[String(r.question_id),r]));calibrationFetchedAt=Date.now();return calibrationByKey
}
function calibration(questionId){return calibrationByKey.get(String(questionId||''))||null}
async function listDevices(){
requireAccountAccess();
const s=await validSession();if(!s?.user?.id)return[];
const rows=await api('/rest/v1/mbu_sync_devices?select=device_id,device_label,app_build,first_seen_at,last_seen_at&user_id=eq.'+encodeURIComponent(s.user.id)+'&order=last_seen_at.desc');
return(rows||[]).map(row=>({...row,current:row.device_id===sync.deviceId()}))
}
async function removeDevice(deviceId){
requireAccountAccess();
const s=await validSession();if(!s?.user?.id)throw Error('Sign in to manage devices.');
const id=String(deviceId||'');if(!id)throw Error('Device id is required.');if(id===sync.deviceId())throw Error('You cannot remove the device you are currently using.');
await api('/rest/v1/mbu_sync_devices?user_id=eq.'+encodeURIComponent(s.user.id)+'&device_id=eq.'+encodeURIComponent(id),{method:'DELETE',headers:{Prefer:'return=minimal'}});return true
}
async function listHistory(limit=30){
requireAccountAccess();
const s=await validSession();if(!s?.user?.id)return[];
const n=Math.max(1,Math.min(Number(limit)||30,100));
return await api('/rest/v1/mbu_sync_versions?select=id,store_key,device_id,server_revision,saved_at,client_revision,client_updated_at&user_id=eq.'+encodeURIComponent(s.user.id)+'&order=saved_at.desc&limit='+n)
}
async function restoreVersion(versionId){
requireAccountAccess();
const s=await validSession();if(!s?.user?.id)throw Error('Sign in to restore cloud history.');
const id=Number(versionId);if(!Number.isInteger(id)||id<1)throw Error('Invalid history version.');
const versions=await api('/rest/v1/mbu_sync_versions?select=id,store_key,payload,server_revision,saved_at&user_id=eq.'+encodeURIComponent(s.user.id)+'&id=eq.'+id+'&limit=1'),version=versions?.[0];
if(!version)throw Error('That history version is no longer available.');
const rows=await api('/rest/v1/mbu_sync_state?select=store_key,server_revision,client_revision&user_id=eq.'+encodeURIComponent(s.user.id)+'&store_key=eq.'+encodeURIComponent(version.store_key)+'&limit=1'),current=rows?.[0];
if(!current)throw Error('Current cloud state for this study area was not found.');
const restoreMeta={deviceId:sync.deviceId(),revision:(Number(current.client_revision)||0)+1,updatedAt:Date.now()},result=await writeState(version.store_key,version.payload,restoreMeta,current.server_revision);
if(result?.applied===false)throw Error('Cloud progress changed while restoring. Refresh history and try again.');
const restoredRow=result?.row||{store_key:version.store_key,payload:version.payload,device_id:sync.deviceId(),client_revision:(Number(current.client_revision)||0)+1,client_updated_at:new Date().toISOString(),server_revision:(Number(current.server_revision)||0)+1};
remoteByKey.set(version.store_key,restoredRow);
const merged=await sync.importSnapshot(cloudSnapshot([restoredRow],s.user),{mode:'replace'});
await fullSync({reloadOnImport:false});
if(merged?.imported>0)emit('restore-applied',{email:s.user?.email||'',storeKey:version.store_key})
return{storeKey:version.store_key,savedAt:version.saved_at}
}
function cloudSnapshot(rows,user){
const stores={},meta={};for(const row of rows||[]){stores[row.store_key]=JSON.stringify(row.payload);meta[row.store_key]={revision:Number(row.client_revision)||0,updatedAt:Date.parse(row.client_updated_at)||0,deviceId:String(row.device_id||'cloud'),serverRevision:Number(row.server_revision)||0}}
return{app:sync.APP,schema:sync.schema,createdAt:Date.now(),deviceId:'cloud:'+user.id,stores,meta}
}
async function pull(){
const s=await validSession();if(!s?.user?.id)return null;
const rows=await api('/rest/v1/mbu_sync_state?select=store_key,payload,device_id,client_revision,client_updated_at,server_revision,server_updated_at&user_id=eq.'+encodeURIComponent(s.user.id));
remoteByKey=new Map((rows||[]).map(r=>[r.store_key,r]));return cloudSnapshot(rows,s.user)
}
function equivalent(remote,payload,meta){
return !!remote&&Number(remote.client_revision)===Number(meta?.revision||0)&&String(remote.device_id||'')===String(meta?.deviceId||'')&&Date.parse(remote.client_updated_at)===Number(meta?.updatedAt||0)&&JSON.stringify(remote.payload)===JSON.stringify(payload)
}
async function push(snapshot){
const s=await validSession();if(!s?.user?.id)return false;let conflictImports=0;
for(const [key,rawValue] of Object.entries(snapshot.stores||{})){
let payload;try{payload=JSON.parse(rawValue)}catch{continue}
const meta=snapshot.meta?.[key]||{revision:0,updatedAt:snapshot.createdAt,deviceId:snapshot.deviceId,serverRevision:0},remote=remoteByKey.get(key);
if(equivalent(remote,payload,meta))continue;
const writeMeta={...meta,deviceId:meta.deviceId||snapshot.deviceId,updatedAt:Number(meta.updatedAt)||snapshot.createdAt||Date.now()},result=await writeState(key,payload,writeMeta,remote?.server_revision??meta.serverRevision??0);
const row=result?.row||null;
if(row)remoteByKey.set(key,row);
if(result?.applied!==false&&row)sync.acknowledgeServerWrite?.(key,row,meta);
if(result?.applied===false&&row){
const merged=await sync.importSnapshot(cloudSnapshot([row],s.user));
conflictImports+=Number(merged?.imported)||0;
if(!merged?.imported){
  const retry=await writeState(key,payload,writeMeta,row.server_revision);
  const retryRow=retry?.row||null;if(retryRow)remoteByKey.set(key,retryRow);
  if(retry?.applied===false)throw Error('Cloud progress changed again while syncing. Retry sync.');
  if(retryRow)sync.acknowledgeServerWrite?.(key,retryRow,meta)
}
}else if(result?.applied===false){
remoteByKey.delete(key);throw Error('Cloud sync conflict could not be resolved. Retry sync.');
}
}
await api('/rest/v1/mbu_sync_devices?on_conflict=user_id,device_id',{method:'POST',body:{user_id:s.user.id,device_id:sync.deviceId(),device_label:navigator.platform||'Browser',app_build:window.MBU_BUILD_ID||'',last_seen_at:new Date().toISOString()},headers:{Prefer:'resolution=merge-duplicates,return=minimal'}});
return{conflictImports}
}
sync.registerAdapter('supabase',{pull,push});
async function fullSync({reloadOnImport=false}={}){
requireAccountAccess();
if(syncing){syncQueued=true;return null}const s=await validSession();if(!s?.user?.id){emit('signed-out');return null}
syncing=true;emit('syncing',{email:s.user?.email||''});
try{
const result=await sync.syncWith('supabase');lastSyncAt=Date.now();emit('synced',{email:s.user?.email||'',result});
if(reloadOnImport&&(result?.imported>0||result?.pushResult?.conflictImports>0))emit('synced-import',{email:s.user?.email||'',result})
return result
}catch(e){emit('error',{email:s.user?.email||'',error:e.message});throw e}
finally{syncing=false;if(syncQueued){syncQueued=false;scheduleSync(0)}}
}
async function pushLocal(){
if(legalAccepted!==true||accountAccess!=='active')return null;
if(syncing){syncQueued=true;return null}const s=await validSession();if(!s?.user?.id)return null;
if(!remoteByKey.size)return fullSync();
syncing=true;emit('syncing',{email:s.user?.email||''});
try{const snapshot=await sync.exportSnapshot();await push(snapshot);lastSyncAt=Date.now();emit('synced',{email:s.user?.email||''});return true}
catch(e){emit('error',{email:s.user?.email||'',error:e.message});throw e}
finally{syncing=false;if(syncQueued){syncQueued=false;scheduleSync(0)}}
}
function scheduleSync(delay=1500){if(!session()||legalAccepted!==true||accountAccess!=='active')return;clearTimeout(timer);timer=setTimeout(()=>{timer=null;pushLocal().catch(()=>{})},delay)}
function stopAutoSync(){if(autoSyncTimer){clearInterval(autoSyncTimer);autoSyncTimer=null}}
function startAutoSync(){
stopAutoSync();if(!session()||legalAccepted!==true||accountAccess!=='active')return;
autoSyncTimer=setInterval(()=>{if(session()&&legalAccepted===true&&accountAccess==='active'&&navigator.onLine)fullSync({reloadOnImport:false}).catch(()=>{})},AUTO_SYNC_INTERVAL)
}
async function questionExposure(courseId,examId){
requireAccountAccess();const s=await validSession();if(!s?.user?.id)return[];if(navigator.onLine===false)throw Error('Coverage offline');
const query='/rest/v1/mbu_question_exposure?select=question_uid,topic,content_version,first_issued_at,last_issued_at,times_issued,coverage_cycle,last_session_id,first_viewed_at,last_viewed_at,times_viewed,first_answered_at,last_answered_at,times_answered&user_id=eq.'+encodeURIComponent(s.user.id)+'&course_id=eq.'+encodeURIComponent(String(courseId||''))+'&exam_id=eq.'+encodeURIComponent(String(examId||''));
return await api(query)
}
async function accountQuestionStats(){
requireAccountAccess();const s=await validSession();if(!s?.user?.id)return{uniqueAnswered:0,totalAttempts:0,courses:[]};if(navigator.onLine===false)throw Error('Account statistics need a connection.');
const query='/rest/v1/mbu_question_exposure?select=course_id,exam_id,question_uid,times_answered,first_answered_at&user_id=eq.'+encodeURIComponent(s.user.id)+'&first_answered_at=not.is.null',rows=await api(query),groups=new Map();let totalAttempts=0;
for(const r of rows||[]){const key=String(r.course_id||'')+'::'+String(r.exam_id||''),g=groups.get(key)||{courseId:String(r.course_id||''),examId:String(r.exam_id||''),uniqueAnswered:0,totalAttempts:0};g.uniqueAnswered++;g.totalAttempts+=Number(r.times_answered)||0;totalAttempts+=Number(r.times_answered)||0;groups.set(key,g)}
return{uniqueAnswered:(rows||[]).length,totalAttempts,courses:[...groups.values()]}
}
async function markQuestionLifecycle(x){requireAccountAccess();if(!x?.questionUid||!x?.sessionId)return false;return await api('/rest/v1/rpc/mbu_mark_question_lifecycle',{method:'POST',body:{p_course_id:String(x.courseId||''),p_exam_id:String(x.examId||''),p_question_uid:String(x.questionUid),p_content_version:String(x.contentVersion||'1'),p_event:x.event,p_session_id:x.sessionId}})===true}
async function resetQuestionCoverage(courseId,examId){requireAccountAccess();return Number(await api('/rest/v1/rpc/mbu_reset_question_coverage',{method:'POST',body:{p_course_id:String(courseId||''),p_exam_id:String(examId||'')}}))||0}
async function recordQuestionSession(x){
requireAccountAccess();if(!x?.sessionId||!Array.isArray(x.items))throw Error('Invalid question session.');if(!navigator.onLine)throw Error('Coverage needs a connection.');
return await api('/rest/v1/rpc/mbu_record_question_session',{method:'POST',body:{p_session_id:x.sessionId,p_course_id:String(x.courseId||''),p_exam_id:String(x.examId||''),p_mode:String(x.mode||'custom'),p_items:x.items,p_new_count:Number(x.newCount)||0,p_review_count:Number(x.reviewCount)||0}})===true
}
async function adminStatus(){const s=await validSession();if(!s?.access_token||legalAccepted!==true)return{is_admin:false,role:null};return await api('/rest/v1/rpc/snar_admin_status',{method:'POST',body:{}})}
function status(){const s=session();return{signedIn:!!s?.access_token,email:s?.user?.email||'',state:lastState,lastSyncAt,user:s?.user||null,recoveryMode,legalAccepted,accessStatus:accountAccess,termsVersion:LEGAL_TERMS_VERSION,privacyVersion:LEGAL_PRIVACY_VERSION,autoSyncIntervalMs:AUTO_SYNC_INTERVAL,nextAutoSyncAt:s?.access_token&&legalAccepted===true&&accountAccess==='active'?(lastSyncAt||Date.now())+AUTO_SYNC_INTERVAL:0}}
window.addEventListener('focus',()=>{if(session()&&legalAccepted===true&&accountAccess==='active'&&Date.now()-lastSyncAt>120000)fullSync().catch(()=>{})});
window.addEventListener('online',()=>{if(session()&&legalAccepted===true&&accountAccess==='active')fullSync().catch(()=>{})});
async function handleAuthRedirect(){
const redirected=await consumeAuthRedirect();if(!redirected)return false;
const switched=await prepareLocalOwner(redirected.user.id);saveSession(redirected);if(switched)emit('local-owner-changed',{email:redirected.user?.email||''})
if(!recoveryMode&&!await refreshLegalAcceptance()){emit('legal-required',{email:redirected.user?.email||''});return true}
await refreshAccountAccess();if(accountAccess!=='active'){emit('access-suspended',{email:redirected.user?.email||''});return true}
stopGuestHeartbeat();startAutoSync();setTimeout(()=>fullSync({reloadOnImport:false}).catch(()=>{}),100);return true
}
window.addEventListener('hashchange',()=>handleAuthRedirect().catch(e=>{emit('error',{error:e.message});console.error('Supabase auth redirect failed',e)}));
window.MBUSupabase={signIn,signUp,signOut,deleteAccount,resendConfirmation,requestPasswordReset,updatePassword,status,currentUser,accessToken:async()=>{const s=await validSession();return s?.access_token||null},refreshLegalAcceptance,refreshAccountAccess,acceptCurrentLegal,submitPrivacyRequest,submitSuggestion,submitQuestionReport,submitItemContribution,refreshCalibration,calibration,listDevices,removeDevice,listHistory,restoreVersion,questionExposure,accountQuestionStats,markQuestionLifecycle,resetQuestionCoverage,recordQuestionSession,adminStatus,adminRpc,syncNow:()=>fullSync({reloadOnImport:false}),scheduleSync,refresh,appRoot:APP_ROOT,autoSyncIntervalMs:AUTO_SYNC_INTERVAL};
const authReady=(async()=>{
if(await handleAuthRedirect())return true;
if(session()){
const valid=await validSession();
if(valid?.user?.id){const switched=await prepareLocalOwner(valid.user.id);if(switched)emit('local-owner-changed',{email:valid.user?.email||''});stopGuestHeartbeat();if(!recoveryMode&&!await refreshLegalAcceptance()){emit('legal-required',{email:valid.user?.email||''});return true}await refreshAccountAccess();if(!recoveryMode&&accountAccess!=='active'){emit('access-suspended',{email:valid.user?.email||''});return true}startAutoSync();setTimeout(()=>fullSync({reloadOnImport:false}).catch(()=>{}),400);setTimeout(()=>refreshCalibration().catch(()=>{}),250);emit(recoveryMode?'password-recovery':'signed-in',{email:valid.user?.email||''});return true}
if(session())return false
}
emit('signed-out');startGuestHeartbeat();return false
})().catch(e=>{emit('error',{error:e.message});console.error('Supabase auth bootstrap failed',e);return false});
window.MBUAuthReady=authReady;
})();
