let byId=id=>document.getElementById(id);const STORE=MBUStudio.STORE;let DB=MBUStudio.db();if(!DB.active)DB.active=null;DB.crosses=DB.crosses||{};let BANK_MANIFEST=null,STUDIO_SOURCE_CATALOG=[],STUDIO_SOURCES=[],STUDIO_SOURCE_ORDER=[],STUDIO_SOURCE_BY_KEY=new Map(),STUDIO_SOURCE_STATE=new Map(),STUDIO_LOAD_GENERATION=0;let ALL=[],ALL_BY_UID=new Map(),BANK_QUESTIONS=new Map(),STUDIO_BANK_LABELS=new Map(),STUDIO_SET_NAMES=new Map(),STUDIO_SET_COUNTS=new Map(),STUDIO_TOPIC_COUNTS=new Map(),STUDIO_LECTURE_COUNTS=new Map(),session=[],pos=0,sel=new Set(),graded=false,autoTimer=null;function seedStudioSourceCatalog(){
STUDIO_BANK_LABELS.clear();STUDIO_SET_NAMES.clear();STUDIO_SET_COUNTS.clear();for(const src of STUDIO_SOURCE_CATALOG){
if(!src.bank.startsWith('h'))STUDIO_BANK_LABELS.set(src.bank,src.label);for(const set of src.sets){
const key=src.bank+':'+set;STUDIO_SET_NAMES.set(key,src.setLabels?.[set]||('Practice Set '+set));STUDIO_SET_COUNTS.set(key,src.count);}
}
}
const save=()=>MBUStudio.save(DB);function saveActive(){if(!session.length)return;const uids=session.map(q=>q.uid),existing=DB.active&&Array.isArray(DB.active.uids)?DB.active:null,same=existing&&existing.uids.length===uids.length&&existing.uids.every((uid,i)=>uid===uids[i]);if(same&&existing.pos===pos)return;DB.active={...(existing||{}),uids,pos,answers:existing&&existing.answers&&typeof existing.answers==='object'?existing.answers:{},updated:Date.now()};save()}
function sessionAnswer(uid){return DB.active&&DB.active.answers?DB.active.answers[uid]:null}
function studioCrossStore(){if(DB.active?.mode==='adaptive'){if(!DB.active.crosses||typeof DB.active.crosses!=='object'||Array.isArray(DB.active.crosses))DB.active.crosses={};return DB.active.crosses}return DB.crosses}
function setSessionAnswer(uid,result){if(!DB.active||!DB.active.answers)saveActive();DB.active.answers[uid]=result;save()}
function clearActive(){DB.active=null;save()}
function studioHasFailedSource(){for(const state of STUDIO_SOURCE_STATE.values())if(state.status==='failed')return true;return false}
function reconcileActiveState(){
const a=DB.active;if(!a||!Array.isArray(a.uids)||!a.uids.length)return null;const old=a.uids,base=Math.min(Math.max(Number(a.pos)||0,0),old.length-1),currentUid=old[base],uids=[],seen=new Set();for(const uid of old)if(ALL_BY_UID.has(uid)&&!seen.has(uid)){seen.add(uid);uids.push(uid)}
if(!uids.length){clearActive();return null}
const answers={};for(const uid of uids)if(a.answers&&a.answers[uid])answers[uid]=a.answers[uid];const crosses={};if(a.mode==='adaptive'&&a.crosses&&typeof a.crosses==='object'&&!Array.isArray(a.crosses)){for(const [k,on] of Object.entries(a.crosses)){if(!on)continue;const cut=k.lastIndexOf(':');if(cut<1)continue;const uid=k.slice(0,cut);if(seen.has(uid))crosses[k]=true}}
let nextPos=currentUid?uids.indexOf(currentUid):-1;if(nextPos<0)nextPos=Math.min(base,uids.length-1);const changed=uids.length!==old.length||uids.some((uid,i)=>uid!==old[i])||nextPos!==a.pos||Object.keys(answers).length!==Object.keys(a.answers||{}).length||(a.mode==='adaptive'&&Object.keys(crosses).length!==Object.keys(a.crosses||{}).length);if(changed){DB.active={...a,uids,pos:nextPos,answers,...(a.mode==='adaptive'?{crosses}: {})};save()}
return DB.active
}
function resumeActive(){
const active=reconcileActiveState();if(!active||!Array.isArray(active.uids)||!active.uids.length)return renderHome();const qs=active.uids.map(id=>ALL_BY_UID.get(id)).filter(Boolean);if(qs.length!==active.uids.length){renderHome();return}
session=qs;pos=Math.min(active.pos||0,session.length-1);showQ()
}
function endActiveQuiz(){studioSessionGeneration++;clearTimeout(autoTimer);autoTimer=null;if(!DB.active)return;clearActive();session=[];pos=0;renderHome()}
function activeButton(){
let old=byId('resumeActiveRow');if(old)old.remove();if(!DB.active||!Array.isArray(DB.active.uids)||!DB.active.uids.length||!ALL_BY_UID.size)return;const missing=DB.active.uids.some(id=>!ALL_BY_UID.has(id)),anchor=byId('studioQuickModes'),row=document.createElement('div'),b=document.createElement('button'),end=document.createElement('button');row.id='resumeActiveRow';row.className='resume-active-row';b.id='resumeActive';b.className='btn resume-active-main';end.id='endActiveQuiz';end.className='btn out resume-active-end';end.textContent='End Quiz';end.setAttribute('aria-label','End active quiz');end.onclick=endActiveQuiz;if(missing&&studioHasFailedSource()){b.disabled=true;b.textContent='⏸ Resume Active Quiz · retry failed source first'}else{const active=reconcileActiveState();if(!active)return;b.textContent='▶ Resume Active Quiz · Question '+(active.pos+1)+' / '+active.uids.length;b.onclick=resumeActive}row.append(b,end);anchor?.parentNode?.insertBefore(row,anchor)
}
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));async function studioFetch(url){const requestUrl=new URL(url,location.href);if(url!=='banks.json'&&window.MBU_BUILD_ID)requestUrl.searchParams.set('b',window.MBU_BUILD_ID);return window.MBUBuild.fetchJSON(requestUrl,{cache:url==='banks.json'?'no-store':'force-cache',timeout:12000})}
function showLoadErrors(errors){
const el=byId('loadmsg');if(!el){if(errors.length)console.warn('Study Studio load:',...errors);return}if(errors.length){el.classList.remove('hidden');el.textContent=errors.join(' | ')}else{el.classList.add('hidden');el.textContent=''}
}
function renderStudioLoadState(){
const panel=byId('studioLoadPanel'),summary=byId('studioLoadSummary'),list=byId('studioLoadSources'),home=byId('home');if(!panel||!summary||!list)return;const states=[...STUDIO_SOURCE_STATE.values()],total=states.length;let ready=0,failed=0,loading=0;for(const x of states){if(x.status==='ready')ready++;else if(x.status==='failed')failed++;else if(x.status==='loading')loading++}
if(home)home.setAttribute('aria-busy',loading?'true':'false');if(!total){panel.classList.add('hidden');return}
const complete=ready+failed;const text=loading?'Loading question banks… '+complete+' / '+total+' complete · '+ALL.length+' questions ready':failed?ready+' / '+total+' sources ready · '+failed+' failed · '+ALL.length+' questions available':'All '+total+' sources ready · '+ALL.length+' questions loaded';summary.textContent=text;
list.innerHTML=states.map(x=>'<div class="studio-load-source '+(x.status==='failed'?'failed':'')+'"><span><b>'+esc(x.label)+'</b> <span class="mut">· '+(x.status==='ready'?(x.count+' questions ready'):x.status==='failed'?('failed: '+esc(x.error)):x.status==='loading'?'loading…':'waiting')+'</span></span>'+(x.status==='failed'?'<button class="btn out" type="button" id="studio-retry-'+esc(x.key)+'" onclick="retryStudioSource(\''+esc(x.key)+'\')">Retry</button>':'')+'</div>').join('');panel.classList.toggle('hidden',!loading&&!failed);}
function addLoadedQuestions(qs){
if(!qs.length)return;for(const q of qs)if(ALL_BY_UID.has(q.uid))throw Error('duplicate question uid '+q.uid);ALL.push(...qs);for(const q of qs){
ALL_BY_UID.set(q.uid,q);if(!BANK_QUESTIONS.has(q.bank))BANK_QUESTIONS.set(q.bank,[]);BANK_QUESTIONS.get(q.bank).push(q);if(!String(q.bank).startsWith('h'))STUDIO_BANK_LABELS.set(q.bank,q.bankLabel);const sk=sourceSetKey(q);if(!STUDIO_SET_NAMES.has(sk))STUDIO_SET_NAMES.set(sk,setLabel(q));STUDIO_TOPIC_COUNTS.set(q.topic,(STUDIO_TOPIC_COUNTS.get(q.topic)||0)+1);STUDIO_LECTURE_COUNTS.set(q.bankLabel,(STUDIO_LECTURE_COUNTS.get(q.bankLabel)||0)+1);}
}
function sortLoadedQuestions(){
ALL.sort((a,b)=>STUDIO_SOURCE_ORDER.indexOf(a.bank)-STUDIO_SOURCE_ORDER.indexOf(b.bank)||a.set-b.set||a.seq-b.seq);for(const qs of BANK_QUESTIONS.values())qs.sort((a,b)=>a.set-b.set||a.seq-b.seq)
}
async function hydrateStudioSource(source,generation=STUDIO_LOAD_GENERATION){
const [url,key,label,meta]=source,state=STUDIO_SOURCE_STATE.get(key)||{key,label,status:'waiting',count:0,error:''};state.status='loading';state.error='';STUDIO_SOURCE_STATE.set(key,state);renderStudioLoadState();try{
const payload=await studioFetch(url);if(generation!==STUDIO_LOAD_GENERATION)return false;if(meta.format!=='canonical')throw Error('unsupported source format '+meta.format);const all=Array.isArray(payload)?payload:(payload.questions||[]);if(!Array.isArray(all))throw Error('canonical question data is invalid');const raw=meta.setFilter?all.filter(q=>Number(q.set)===Number(meta.setFilter)):all;if(Number.isFinite(Number(meta.count))&&raw.length!==Number(meta.count))throw Error('question count '+raw.length+' does not match manifest '+meta.count);if(meta.sourceTitleContract&&raw.some(q=>String(q.sourceTitle||'').trim()!==String(meta.sourceTitleContract)))throw Error('sourceTitle does not match manifest source contract');const qs=raw.map((q,i)=>{
let img=q.imageSvg||q.image||null;if(img&&typeof img==='object'&&img.kind==='direct'&&img.url)img={...img,url:new URL(img.url,new URL('./',location.href)).href};if(meta.imageBase){
const rawKey=q.imageId||q.image||'',safe=String(rawKey).replace(/[^A-Za-z0-9_-]/g,'');if(safe&&safe===String(rawKey))img={kind:'direct',url:meta.imageBase.replace(/\/?$/,'/')+safe+'.png'};}
const studioSet=String(key).startsWith('h')?1:(q.set||1);return norm({...q,img},key,studioSet,i,label,String(key).startsWith('h')?'Workstation Hazards':undefined)
});addLoadedQuestions(qs);state.status='ready';state.count=qs.length;state.error='';try{buildTopics()}catch(e){console.error('Studio selector render failed:',label,e)}
renderStudioLoadState();return true
}catch(e){
state.status='failed';state.count=0;state.error=e&&e.name==='AbortError'?'timed out':String(e&&e.message?e.message:e);console.error('Studio source failed:',label,e);renderStudioLoadState();return false
}
}
async function retryStudioSource(key){
const state=STUDIO_SOURCE_STATE.get(key),source=STUDIO_SOURCE_BY_KEY.get(key);if(!state||state.status!=='failed'||!source)return;const ok=await hydrateStudioSource(source,STUDIO_LOAD_GENERATION);if(!ok)return;sortLoadedQuestions();syncBankData();buildTopics();renderHome();renderStudioLoadState()
}
async function loadBanks(){
const generation=++STUDIO_LOAD_GENERATION;ALL=[];ALL_BY_UID.clear();BANK_QUESTIONS.clear();STUDIO_TOPIC_COUNTS.clear();STUDIO_SOURCE_STATE.clear();STUDIO_SOURCE_BY_KEY.clear();try{
BANK_MANIFEST=await studioFetch('banks.json');if(!BANK_MANIFEST||!Array.isArray(BANK_MANIFEST.studioSources))throw Error('invalid bank manifest');window.MBU_FEATURES={...(window.MBU_FEATURES||{}),questionGenerator:BANK_MANIFEST.features?.questionGenerator||{enabled:false,status:'unconfigured'}};if(window.MBU_FEATURES.questionGenerator?.enabled&&!window.MBUQuestionGenerator){await window.MBUBuild?.loadStyle?.('question-generator-ui.css');await window.MBUBuild?.loadStyle?.('source-material-library.css');await window.MBUBuild?.loadScript?.('question-generator.js');await window.MBUBuild?.loadScript?.('question-generator-gemini.js');for(const asset of ['material-ingest.js','source-material-storage.js','source-material-library.js'])await window.MBUBuild?.loadScript?.(asset);await window.MBUBuild?.loadScript?.('question-generator-ui.js')}}catch(e){showLoadErrors(['Bank manifest failed: '+e.message]);console.error(e);byId('home')?.setAttribute('aria-busy','false');return}
STUDIO_SOURCE_CATALOG=BANK_MANIFEST.studioSources.map(src=>({bank:src.key,label:src.groupLabel||src.label,sets:src.sets,setLabels:src.setLabels||null,count:src.count}));seedStudioSourceCatalog();buildTopics();STUDIO_SOURCES=BANK_MANIFEST.studioSources.map(src=>[src.data,src.key,src.label,src]);STUDIO_SOURCE_ORDER=STUDIO_SOURCES.map(x=>x[1]);for(const source of STUDIO_SOURCES){const [,key,label]=source;STUDIO_SOURCE_BY_KEY.set(key,source);STUDIO_SOURCE_STATE.set(key,{key,label,status:'waiting',count:0,error:''})}
try{renderHome()}catch(e){}
renderStudioLoadState();await Promise.all(STUDIO_SOURCES.map(source=>hydrateStudioSource(source,generation)));if(generation!==STUDIO_LOAD_GENERATION)return;if(window.MBUQuestionGenerator?.enabled?.()){
for(const [key,label,rows,setLabel] of [['generated','Generated Bank',window.MBUQuestionGenerator.studioQuestions(),'Approved Generated Questions'],['classmate','Classmate Bank',window.MBUQuestionGenerator.classmateQuestions(),'Saved Generated Questions']])if(rows.length||key==='classmate'){STUDIO_SOURCE_CATALOG.push({bank:key,label,sets:[1],setLabels:{1:setLabel},count:rows.length});STUDIO_SOURCE_ORDER.push(key);seedStudioSourceCatalog();if(rows.length)addLoadedQuestions(rows.map((q,i)=>norm(q,key,1,i,label)));}
}
function refreshGeneratedStudioBanks(){
  if(!window.MBUQuestionGenerator?.enabled?.())return;
  const generated=window.MBUQuestionGenerator.studioQuestions(),classmate=window.MBUQuestionGenerator.classmateQuestions();
  ALL=ALL.filter(q=>q.bank!=='generated'&&q.bank!=='classmate');
  for(const key of ['generated','classmate']){STUDIO_SOURCE_CATALOG=STUDIO_SOURCE_CATALOG.filter(x=>x.bank!==key);const at=STUDIO_SOURCE_ORDER.indexOf(key);if(at>=0)STUDIO_SOURCE_ORDER.splice(at,1)}
  for(const [key,label,rows,setLabel] of [['generated','Generated Bank',generated,'Approved Generated Questions'],['classmate','Classmate Bank',classmate,'Saved Generated Questions']])if(rows.length||key==='classmate'){STUDIO_SOURCE_CATALOG.push({bank:key,label,sets:[1],setLabels:{1:setLabel},count:rows.length});STUDIO_SOURCE_ORDER.push(key);if(rows.length)addLoadedQuestions(rows.map((q,i)=>norm(q,key,1,i,label)))}
  sortLoadedQuestions();syncBankData();seedStudioSourceCatalog();buildTopics();renderHome();
}
window.addEventListener('mbu-generated-questions-changed',()=>{try{refreshGeneratedStudioBanks()}catch(e){console.error('Generated bank refresh failed',e)}});
sortLoadedQuestions();try{
syncBankData();window.MBUStudyIntelligence?.seedLegacy?.(Object.entries(DB.ans||{}).map(([uid,r])=>({uid,bank:r.bank,bankLabel:STUDIO_BANK_LABELS.get(r.bank)||r.bank,topic:r.topic,at:r.at,ok:r.ok})));window.MBUQuestionSearch?.reset?.();buildTopics();initialStudioBuildMode();const params=new URLSearchParams(location.search),rawQuestion=params.get('question'),question=String(rawQuestion||'').replace(/^bp1-preop-assessment-/i,'preop-assessment-'),requested=params.get('mode');if(question&&ALL_BY_UID.has(question))practiceSearch(question);else if(requested==='hazards-missed')startMode('hazards-missed');else if(requested==='combined-missed')startMode('combined-missed');else if(requested==='due')startMode('due');else if(requested==='weak')startMode('weak');else if(requested==='smart')startMode('smart');else if(requested==='adaptive')openAdaptiveEntry();else if(DB.active?.mode==='adaptive'&&reconcileActiveState())resumeActive();else renderHome()}catch(e){showLoadErrors(['Studio render failed: '+e.message]);console.error(e)}
renderStudioLoadState()
}
function canonicalTopic(topic){const name=String(topic||'Other').trim();const low=name.toLowerCase().replace(/₂/g,'2');if(low.includes('co2')&&low.includes('scaveng'))return 'CO₂ & Scavenging';if(low.includes('medical gas'))return 'Medical Gases';if(low.includes('airway equipment')||low==='airway')return 'Airway';if(low.includes('intraoperative assessment')||low.startsWith('monitoring'))return 'Monitoring';if(low.includes('workstation hazards')||low.includes('hazards & safety'))return 'Workstation Hazards';return name}
function inferredTopic(q){if(q.topic)return q.topic;if(q.lec)return q.lec;const refs=Array.isArray(q.ref)?q.ref.join(';'):'';const src=String(q.citation||q.src||refs||'').trim();if(/^Medical Gas Systems in Anesthesia/i.test(src))return 'Medical Gases';if(/^Intraoperative Assessment|^Monitoring/i.test(src))return 'Monitoring';if(/^Airway Equipment/i.test(src))return 'Airway';if(/^CO2 and Scavenging|^CO2 Absorbents and Scavenging|^CO₂ & Scavenging/i.test(src))return 'CO₂ & Scavenging';if(/^Anesthesia Workstation Hazards|^Hazards & safety/i.test(src))return 'Workstation Hazards';return 'Other'}
function norm(q,b,set,i,label,forcedTopic){
const isMatching=String(q.type||'').toLowerCase()==='matching',rawAns=q.answer??q.correct??q.a??[],ans=isMatching?[]:(Array.isArray(rawAns)?rawAns:[rawAns]).map(Number).filter(Number.isInteger);const opts=Array.isArray(q.options)?q.options:(Array.isArray(q.c)?q.c:[]),matching=isMatching?{prompts:Array.isArray(q.prompts)?q.prompts.map(String):[],choices:Array.isArray(q.choices)?q.choices.map(String):[],answer:q.answer&&typeof q.answer==='object'&&!Array.isArray(q.answer)?{...q.answer}:{}}:null;if(isMatching&&(!matching.prompts.length||!matching.choices.length||matching.prompts.some(p=>!Object.prototype.hasOwnProperty.call(matching.answer,p))))throw Error('invalid matching question '+String(q.id??(set+'-'+i)));const rawSrc=q.citation??((q.src||'')+(q.page?' · '+q.page:''))??'';const src=Array.isArray(rawSrc)?rawSrc.join(';'):String(rawSrc||((q.ref||[]).join(';')));const stem=String(q.stem||q.q||''),exp=String(q.explanation||q.why||q.exp||''),topic=canonicalTopic(forcedTopic||inferredTopic(q)),matchSearch=matching?(matching.prompts.join(' ')+' '+matching.choices.join(' ')):'';return{uid:b+'-'+(q.id??(set+'-'+i)),bank:b,bankLabel:label||b,set,seq:i,topic,stem,opts,ans,matching,exp,src,img:q.img||q.imageSvg||q.image||null,type:String(q.type||''),concept:String(q.concept||''),disc:String(q.disc||''),sourceTitle:String(q.sourceTitle||''),sourceMeta:q.sourceMeta&&typeof q.sourceMeta==='object'?q.sourceMeta:null,searchText:(stem+' '+topic+' '+matchSearch+' '+exp+' '+src).toLowerCase()}
}
function syncBankData(){
let syncChanged=false;const put=(q,ok,bank,force=false)=>{if(!q)return;const prev=DB.ans[q.uid],nextOk=!!ok;if(!force&&prev)return;if(prev&&prev.ok===nextOk&&prev.bank===bank&&prev.topic===q.topic)return;DB.ans[q.uid]={ok:nextOk,at:Date.now(),topic:q.topic,bank};syncChanged=true};const syncCanonical=(bank,key)=>{
try{
const d=JSON.parse(localStorage.getItem(key)||'null');if(!d||!d.sets)return false;let found=false;for(const [setKey,st] of Object.entries(d.sets||{})){
const set=Number(setKey),qs=(BANK_QUESTIONS.get(bank)||[]).filter(q=>q.set===set);if(!st||!st.graded)continue;for(const [i,on] of Object.entries(st.graded)){if(!on)continue;const q=qs[Number(i)];if(q){put(q,st.correct&&st.correct[i],bank);found=true}}
}
return found
}catch(e){return false}
};syncCanonical('b1','SRNA_COMBINED_EXAM_SET_1_2026_V1');syncCanonical('b2','srna_all5_groundup_v1');syncCanonical('b3','srna_equipment_dashboard_v1');try{
const b2=JSON.parse(localStorage.getItem('srna_all5_groundup_v1')||'null');if(b2&&b2.sets)for(let s=0;s<5;s++){const st=b2.sets[s]||{},qs=(BANK_QUESTIONS.get('b2')||[]).filter(q=>q.set===s+1);Object.entries(st.answered||{}).forEach(([i,ok])=>put(qs[+i],ok,'b2'))}
}catch(e){}
try{
const raw=localStorage.getItem('srna_equipment_dashboard_v1');const b3=raw&&JSON.parse(raw),byId=new Map((BANK_QUESTIONS.get('b3')||[]).map(q=>[String(q.uid).slice(3),q]));if(b3&&b3.ex)Object.values(b3.ex).forEach(exam=>Object.entries(exam.ans||{}).forEach(([id,result])=>put(byId.get(String(id)),result&&result.ok,'b3')));else if(b3&&b3.answered)Object.entries(b3.answered).forEach(([id,ok])=>put(byId.get(String(id)),ok,'b3'))
}catch(e){}
try{
const combined=JSON.parse(localStorage.getItem('MBU_COMBINED_BANK_2026_V1')||'null');if(combined&&combined.sets){
const byId=new Map((BANK_QUESTIONS.get('combined')||[]).map(q=>[String(q.uid).slice('combined-'.length),q]));for(let set=1;set<=3;set++){
const st=combined.sets[set]||{};Object.keys(st.graded||{}).forEach(id=>{if(st.graded[id])put(byId.get(String(id)),st.correct&&st.correct[id],'combined')});}
}
}catch(e){}
for(const [bank,key,kind] of [
['h1','SRNA_HAZARDS_BANK_1_2026_V2','graded'],['h2','SRNA_HAZARDS_BANK_2_2026_V1','graded'],['h3','hazards_practice3_progress_2026_V2','ans'],['hh','hazards_harder_progress_2026_V1','ans']
]){
try{
const d=JSON.parse(localStorage.getItem(key)||'null');if(!d)continue;const map=new Map((BANK_QUESTIONS.get(bank)||[]).map(q=>[String(q.uid).slice(bank.length+1),q]));if(kind==='graded')Object.keys(d.graded||{}).forEach(id=>{if(d.graded[id])put(map.get(String(id)),d.correct&&d.correct[id],bank)});else Object.entries(d.ans||{}).forEach(([id,result])=>put(map.get(String(id)),result&&result.ok,bank,bank==='h3'||bank==='hh'));}catch(e){}
}
if(syncChanged)save();}
let buildMode='sets',adaptiveEntryPending=false;function adaptiveAccountReady(){const status=window.MBUSupabase?.status?.()||{};return !!status.signedIn&&status.legalAccepted===true&&status.accessStatus==='active'}
function syncAdaptiveStartLabel(){
const toggle=byId('adaptiveToggle'),button=document.querySelector('.studio-start-btn');if(button)button.textContent=toggle?.checked?'Begin Adaptive Quiz':'Start Quiz'
}
function adaptiveToggleChanged(input){
if(!input?.checked){syncAdaptiveStartLabel();return true}
if(adaptiveAccountReady()){syncAdaptiveStartLabel();return true}
input.checked=false;syncAdaptiveStartLabel();window.MBUAppCore?.openAccount?.(input);return false
}
function clearAdaptiveEntryParam(){const url=new URL(location.href);url.searchParams.delete('mode');history.replaceState(null,'',url.pathname+url.search+url.hash)}
function prepareAdaptiveEntry(){
renderHome();if(unifiedStudioSource()){buildMode='topics';setChecks('topicChecks',true)}else{setBuildMode('sets');setChecks('sourceChecks',true)}
const count=byId('count');if(count)count.value='100';const toggle=byId('adaptiveToggle');if(!toggle)return null;toggle.checked=true;syncAdaptiveStartLabel();return toggle
}
function focusAdaptiveStart(){
const card=document.querySelector('.studio-adaptive-card'),button=document.querySelector('.studio-start-btn');card?.scrollIntoView?.({block:'center',behavior:'smooth'});button?.focus?.()
}
async function resolveAdaptiveAccount(){
try{if(window.MBUAuthReady&&typeof window.MBUAuthReady.then==='function')await window.MBUAuthReady}catch{}
const api=window.MBUSupabase;if(!api)return{signedIn:false,legalAccepted:false,accessStatus:'unavailable'};let info=api.status?.()||{};if(!info.signedIn)return info;if(info.legalAccepted!==true){try{await api.refreshLegalAcceptance?.()}catch{}info=api.status?.()||info}
if(info.signedIn&&info.legalAccepted===true&&info.accessStatus!=='active'){try{await api.refreshAccountAccess?.()}catch{}info=api.status?.()||info}
return info
}
async function openAdaptiveEntry(){
const toggle=prepareAdaptiveEntry();if(!toggle)return;adaptiveEntryPending=true;toggle.checked=false;syncAdaptiveStartLabel();const info=await resolveAdaptiveAccount();if(info.signedIn&&info.legalAccepted===true&&info.accessStatus==='active'){
toggle.checked=true;syncAdaptiveStartLabel();adaptiveEntryPending=false;clearAdaptiveEntryParam();window.MBUAppCore?.closeAccount?.();focusAdaptiveStart();return
}
adaptiveEntryPending=true;window.MBUAppCore?.openAccount?.(toggle);focusAdaptiveStart()
}
window.addEventListener('mbu:supabase-status',()=>{
if(!adaptiveEntryPending||!adaptiveAccountReady())return;const toggle=prepareAdaptiveEntry();if(toggle)toggle.checked=true;adaptiveEntryPending=false;clearAdaptiveEntryParam();window.MBUAppCore?.closeAccount?.();focusAdaptiveStart()
});function unifiedStudioSource(){return BANK_MANIFEST?.studio?.sourceMode==='unified'}
function setBuildMode(mode){buildMode=mode==='topics'?'topics':'sets';byId('sourcePickbox').classList.toggle('hidden',buildMode!=='sets');byId('topicPickbox').classList.toggle('hidden',buildMode!=='topics');byId('buildSetsBtn').classList.toggle('out',buildMode!=='sets');byId('buildTopicsBtn').classList.toggle('out',buildMode!=='topics');byId('buildModeHelp').textContent=buildMode==='sets'?(unifiedStudioSource()?'Use the complete unified 3,500-question Exam 1 pool.':'Choose one or more practice sets. Questions can come from any topic in those sets.'):(unifiedStudioSource()?'Choose one or more of the seven Exam 1 lecture topics.':'Choose one or more topics. Studio will pull matching questions from the full loaded question pool.')}
function setChecks(id,on){document.querySelectorAll('#'+id+' input[type=checkbox]').forEach(x=>x.checked=on)}
function checkedValues(id){return [...document.querySelectorAll('#'+id+' input[type=checkbox]:checked')].map(x=>x.value)}
function setLabel(q){if(q.bank==='hh')return 'Challenge Set';if(q.bank==='h1'||q.bank==='h2'||q.bank==='h3')return q.bankLabel;return q.set===7?'Challenge Set':'Practice Set '+q.set}
function sourceSetKey(q){return q.bank+':'+q.set}
function initialStudioBuildMode(){if(unifiedStudioSource()){buildMode='topics';return}setBuildMode('sets')}

let studioCorePromise=null;window.MBUStudioCoreReady=()=>studioCorePromise||(studioCorePromise=loadBanks());
