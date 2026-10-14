// Regression tests for questions rewritten in place (same ID, new content).
// 1. The runtime registry and scripts/content-revisions.json agree, and every fingerprint matches the bank file,
//    so a revised question cannot be edited again without bumping its revision.
// 2. Learner history from an earlier revision is preserved but not applied to the new content, and CAT calibration
//    for a revised question is collected under its own id, so first-attempt statistics never mix two versions.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const root=process.cwd(),read=p=>fs.readFileSync(root+'/'+p,'utf8');
const registrySrc=read('equipment/assets/content-revisions.js'),manifest=JSON.parse(read('scripts/content-revisions.json'));
const fnv=s=>{let h=2166136261;for(const c of s){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return(h>>>0).toString(16).padStart(8,'0')};

// ---- 1. registry integrity ----
const probe={};vm.runInNewContext(registrySrc,{window:probe});
const runtimeIds=Array.from(probe.MBUContentRevisions.list()).sort(),manifestIds=Object.keys(manifest.revisions).sort();
assert.deepEqual(runtimeIds,manifestIds,'content-revisions.js and scripts/content-revisions.json list different questions');
const banks={};for(const b of ['bank1','bank2','bank3'])banks[b]=new Map(JSON.parse(read('equipment/exam-1/data/'+b+'.json')).questions.map(q=>[String(q.id),q]));
for(const [uid,e] of Object.entries(manifest.revisions)){
  const bank={b1:'bank1',b2:'bank2',b3:'bank3'}[uid.split('-')[0]],q=banks[bank]?.get(String(e.id));
  assert.ok(q,uid+' is missing from '+bank+' (question IDs must never be removed)');
  assert.equal(Number(q.set),Number(e.set),uid+' moved from set '+e.set+' to set '+q.set);
  assert.equal(probe.MBUContentRevisions.revision(uid),Number(e.revision),uid+' runtime revision differs from manifest');
  assert.equal(fnv(JSON.stringify([q.stem,q.options,q.answer])),e.fingerprint,uid+' content changed without a revision bump (update scripts/content-revisions.json and content-revisions.js)');
}
assert.equal(probe.MBUContentRevisions.revision('b1-1'),1,'unlisted questions must stay at revision 1');
assert.equal(probe.MBUContentRevisions.calibrationId('b1-1'),'b1-1','unlisted questions keep their original calibration id');

// ---- 2. learner-state behavior ----
const DAY=86400000,T0=Date.UTC(2026,8,1);
function makeEnv({withRegistry=true,store=null,calibration={}}={}){
  const ls=new Map(store?[['mbu_study_intelligence_v1',JSON.stringify(store)]]:[]),enqueued=[];
  const window={MBU_CONTEXT:{courseId:'equipment',examId:'exam-1'},addEventListener(){},MBUCalibrationOutbox:{enqueue:(s,k,p)=>{enqueued.push({key:k,...p});return true}},MBUSupabase:{calibration:id=>calibration[id]||null}};
  const ctx={window,localStorage:{getItem:k=>ls.has(k)?ls.get(k):null,setItem:(k,v)=>ls.set(k,String(v)),removeItem:k=>ls.delete(k)},location:{href:'https://example.test/'},crypto:globalThis.crypto,console};
  ctx.globalThis=ctx;vm.createContext(ctx);
  if(withRegistry)vm.runInContext(registrySrc,ctx);
  vm.runInContext(read('equipment/assets/study-intelligence.js'),ctx);
  vm.runInContext(read('equipment/assets/adaptive-quiz.js'),ctx);
  return{si:window.MBUStudyIntelligence,aq:window.MBUAdaptiveQuiz,enqueued,saved:()=>JSON.parse(ls.get('mbu_study_intelligence_v1')||'null')};
}
const revisedUid=manifestIds.find(u=>u.startsWith('b1-')),stableUid='b1-1';
const legacyAttempt=(uid,ok)=>({uid,bank:'b1',bankLabel:'Quiz Bank 1',set:5,questionId:uid,topic:'Monitoring',stem:'old wording',href:'',attempts:2,correct:ok?2:0,incorrect:ok?0:2,lastAt:T0,lastCorrect:ok,streak:0});
const legacy={schema:1,updatedAt:T0,seededLegacy:true,issues:[],
  attempts:{[revisedUid]:legacyAttempt(revisedUid,false),[stableUid]:legacyAttempt(stableUid,false)},
  reviews:{[revisedUid]:{uid:revisedUid,dueAt:T0+DAY,lastAt:T0,lastCorrect:false},[stableUid]:{uid:stableUid,dueAt:T0+DAY,lastAt:T0,lastCorrect:false}},
  activity:[{id:revisedUid+':'+T0,at:T0,type:'answer',uid:revisedUid,topic:'Monitoring',ok:false},{id:stableUid+':'+T0,at:T0,type:'answer',uid:stableUid,topic:'Monitoring',ok:false}]};

{ // revised question: old history is not applied
  const env=makeEnv({store:structuredClone(legacy)});
  assert.equal(env.si.questionStats(revisedUid),null,'stats from an earlier revision must not apply to rewritten content');
  assert.ok(env.si.questionStats(stableUid),'unchanged questions keep their stats');
  const due=env.si.due(T0+2*DAY).map(r=>r.uid);
  assert.ok(!due.includes(revisedUid),'a rewritten question must not be scheduled as a missed-question review');
  assert.ok(due.includes(stableUid),'unchanged questions keep their review schedule');
  const pr=env.si.priorityForQuestion({uid:revisedUid,topic:'Monitoring'},T0+2*DAY);
  assert.equal(pr.seen,false);assert.equal(pr.due,false);assert.equal(pr.reason!=='Needs another pass',true);
  // overall analytics still count the preserved history
  assert.equal(env.si.analytics().overall.attempts,4,'earlier-revision attempts must remain in overall analytics');
}
{ // first answer on the new revision: preserved history, first-attempt calibration under the revision id
  const env=makeEnv({store:structuredClone(legacy)});
  env.si.recordAnswer('b1',{uid:revisedUid,id:revisedUid.slice(3),topic:'Monitoring',stem:'new wording'},true,{at:T0+3*DAY});
  const d=env.saved();
  assert.equal(d.attempts[revisedUid].attempts,1,'first answer on the new revision starts a fresh record');
  assert.equal(d.attempts[revisedUid].revision,2);
  assert.equal(d.attempts[revisedUid+'@r1'].attempts,2,'earlier-revision history is preserved, not deleted');
  assert.equal(d.attempts[revisedUid+'@r1'].retiredFrom,revisedUid);
  assert.equal(env.enqueued.length,1,'first attempt on the new revision is a calibration contribution');
  assert.equal(env.enqueued[0].questionId,revisedUid+'@r2');assert.equal(env.enqueued[0].key,revisedUid+'@r2');
  env.si.recordAnswer('b1',{uid:revisedUid,topic:'Monitoring',stem:'new wording'},false,{at:T0+4*DAY});
  assert.equal(env.enqueued.length,1,'only the first attempt on a revision is contributed');
  assert.equal(env.si.analytics().overall.attempts,6);
  // unchanged question: existing behavior, no new first-attempt contribution
  env.si.recordAnswer('b1',{uid:stableUid,topic:'Monitoring',stem:'old wording'},true,{at:T0+3*DAY});
  assert.equal(env.enqueued.length,1,'repeat answers on unchanged questions are not first attempts');
  assert.equal(env.saved().attempts[stableUid].attempts,3);
}
{ // CAT difficulty never borrows calibration from the earlier revision
  const cal={[revisedUid]:{unique_learners:400,difficulty_logit:2.5},[stableUid]:{unique_learners:400,difficulty_logit:2.5}};
  const env=makeEnv({calibration:cal});
  assert.equal(env.aq.difficultyEstimate({uid:revisedUid,stem:'Which device is used?'}).source,'structural','revised question must not use old calibration');
  assert.equal(env.aq.difficultyEstimate({uid:stableUid,stem:'Which device is used?'}).source,'blended','unchanged questions keep population calibration');
  const env2=makeEnv({calibration:{...cal,[revisedUid+'@r2']:{unique_learners:400,difficulty_logit:-1}}});
  assert.equal(env2.aq.difficultyEstimate({uid:revisedUid,stem:'Which device is used?'}).source,'blended','revised question uses its own calibration once collected');
}
{ // without the registry loaded, behavior is exactly the legacy behavior
  const env=makeEnv({withRegistry:false,store:structuredClone(legacy)});
  assert.ok(env.si.questionStats(revisedUid));
  env.si.recordAnswer('b1',{uid:revisedUid,topic:'Monitoring'},true,{at:T0+3*DAY});
  assert.equal(env.enqueued.length,0);assert.equal(env.saved().attempts[revisedUid].attempts,3);
}

// ---- 3. saved quiz state: Bank pages and Study Studio ----
function fakeDom(){const el=()=>{const e={style:{},dataset:{},classList:{add(){},remove(){},toggle(){},contains:()=>false},children:[],innerHTML:'',textContent:'',appendChild(c){this.children.push(c);return c},append(){},setAttribute(){},addEventListener(){},querySelector:()=>null,focus(){}};return e};const map=new Map();return{getElementById:id=>{if(!map.has(id))map.set(id,el());return map.get(id)},createElement:()=>el(),querySelectorAll:()=>[],body:{innerHTML:''}}}
function runBankPage(bankFile,bankKey,storageKey,stored){
  const ls=new Map([[storageKey,JSON.stringify(stored)]]),data=JSON.parse(read('equipment/exam-1/data/'+bankFile));
  const window={MBU_QUIZ_CONFIG:{id:bankKey,title:'Bank',studioBankKey:bankKey,storageKey,dataUrl:'x.json'},MBUBuild:{fetchJSON:async()=>data},scrollTo(){}};
  const ctx={window,document:fakeDom(),localStorage:{getItem:k=>ls.has(k)?ls.get(k):null,setItem:(k,v)=>ls.set(k,String(v)),removeItem:k=>ls.delete(k)},sessionStorage:{getItem:()=>null,setItem(){}},location:{href:'https://example.test/?',search:''},URL,URLSearchParams,console,setTimeout,clearTimeout,requestAnimationFrame:()=>0,confirm:()=>true};
  ctx.globalThis=ctx;vm.createContext(ctx);vm.runInContext(registrySrc,ctx);vm.runInContext(read('equipment/assets/quiz-engine.js'),ctx);
  return window.MBUQuizReady.then(()=>({state:JSON.parse(ls.get(storageKey)),data}))
}
{
  const data=JSON.parse(read('equipment/exam-1/data/bank1.json')).questions,bySet={};for(const q of data)(bySet[q.set]??=[]).push(q);
  const revId=revisedUid.slice(3),rq=data.find(q=>String(q.id)===revId),set=rq.set,idx=bySet[set].indexOf(rq),stableIdx=idx===0?1:0,stableQ=bySet[set][stableIdx];
  const st={answers:{[idx]:[0],[stableIdx]:[0],['r'+set+'_'+revId]:[1]},graded:{[idx]:true,[stableIdx]:true,['r'+set+'_'+revId]:true},correct:{[idx]:false,[stableIdx]:false,['r'+set+'_'+revId]:false},strikes:{[idx+'_2']:true,[stableIdx+'_1']:true},current:idx};
  const stored={sets:{[set]:st},missed:{[set]:[revId,stableQ.id]},test6:{answers:{['t6_'+set+'_'+revId]:[0]},graded:{['t6_'+set+'_'+revId]:true},correct:{['t6_'+set+'_'+revId]:false},strikes:{},current:0},lastSet:set};
  const {state}=await runBankPage('bank1.json','b1','SRNA_COMBINED_EXAM_SET_1_2026_V1',stored),s=state.sets[set];
  assert.ok(!(String(idx) in s.graded)&&!(String(idx) in s.answers),'bank page must not show an old answer against rewritten content');
  assert.ok(!(('r'+set+'_'+revId) in s.graded),'missed-review answer for old content is retired');
  assert.ok(!(('t6_'+set+'_'+revId) in state.test6.graded),'missed-bank answer for old content is retired');
  assert.ok(!((idx+'_2') in s.strikes),'cross-outs for old options are retired');
  assert.ok(!state.missed[set].includes(revId),'rewritten question leaves the missed list');
  assert.ok(state.missed[set].includes(stableQ.id)&&s.graded[stableIdx]===true&&s.strikes[stableIdx+'_1'],'unchanged questions keep answers, missed status and cross-outs');
  assert.deepEqual(JSON.parse(JSON.stringify(state.retired[revisedUid+'@r1'].answers)),{[idx]:[0],['r'+set+'_'+revId]:[1],['t6_'+set+'_'+revId]:[0]},'old answers (set, missed review, missed bank) are preserved in the retired archive');
  assert.equal(state.revisions[revisedUid],2);assert.equal(s.current,idx,'saved position is unchanged');
  const again=await runBankPage('bank1.json','b1','SRNA_COMBINED_EXAM_SET_1_2026_V1',state);
  assert.equal(JSON.stringify(again.state),JSON.stringify(state),'migration is idempotent across reloads');
  // a new answer recorded after migration is kept
  const answered=structuredClone(state);answered.sets[set].answers[idx]=[1];answered.sets[set].graded[idx]=true;answered.sets[set].correct[idx]=true;
  const kept=await runBankPage('bank1.json','b1','SRNA_COMBINED_EXAM_SET_1_2026_V1',answered);
  assert.equal(kept.state.sets[set].graded[idx],true,'answers on the new revision are never retired');
}
{
  const studioSrc=read('equipment/assets/studio-sync.js'),stableUid2='b1-2';
  const runStudio=stored=>{const ls=new Map([['mbu_exam1_studio_v1',JSON.stringify(stored)]]),window={MBU_CONTEXT:{courseId:'equipment',examId:'exam-1'},addEventListener(){}};const ctx={window,localStorage:{getItem:k=>ls.has(k)?ls.get(k):null,setItem:(k,v)=>ls.set(k,String(v)),removeItem:k=>ls.delete(k)},location:{origin:'https://example.test',pathname:'/'},document:fakeDom(),console};ctx.globalThis=ctx;vm.createContext(ctx);vm.runInContext(registrySrc,ctx);vm.runInContext(studioSrc,ctx);window.MBUStudio.db();return JSON.parse(ls.get('mbu_exam1_studio_v1'))};
  const session=(mode)=>({uids:[revisedUid,stableUid2],pos:0,mode,answers:{[revisedUid]:{ok:false,selected:[1],at:T0},[stableUid2]:{ok:true,selected:[0],at:T0}},updated:T0});
  const d=runStudio({ans:{[revisedUid]:{ok:false,at:T0},[stableUid2]:{ok:false,at:T0}},flags:{[revisedUid]:true,[stableUid2]:true},crosses:{[revisedUid+':1']:true,[stableUid2+':0']:true},reports:[],active:session('custom'),searchReturn:session('adaptive')});
  assert.ok(!d.ans[revisedUid]&&d.ans[revisedUid+'@r1'],'Studio answer history is archived, not deleted, and not applied to new content');
  assert.ok(!d.flags[revisedUid]&&d.flags[revisedUid+'@r1'],'flag on old content does not carry to the new question');
  assert.ok(!d.crosses[revisedUid+':1']&&d.crosses[stableUid2+':0'],'old cross-outs are cleared; unchanged ones kept');
  assert.ok(!d.active.answers[revisedUid]&&d.active.answers[stableUid2],'interrupted custom session: rewritten question becomes unanswered, others unchanged');
  assert.deepEqual(d.active.uids,[revisedUid,stableUid2],'session question order and IDs unchanged');
  assert.ok(d.searchReturn.answers[revisedUid],'adaptive session answers stay locked so CAT recovery and ability estimates are unchanged');
  assert.ok(d.ans[stableUid2]&&d.flags[stableUid2],'unchanged Studio records untouched');
  assert.equal(JSON.stringify(runStudio(d)),JSON.stringify(d),'Studio migration is idempotent');
  // A store with nothing to archive must not be rewritten at startup (avoids needless sync churn).
  {const ls=new Map([['mbu_exam1_studio_v1',JSON.stringify({ans:{[stableUid2]:{ok:true,at:T0}},flags:{},crosses:{},reports:[]})]]);let writes=0;
   const window={MBU_CONTEXT:{courseId:'equipment',examId:'exam-1'},addEventListener(){}};
   const ctx={window,localStorage:{getItem:k=>ls.has(k)?ls.get(k):null,setItem:(k,v)=>{writes++;ls.set(k,String(v))},removeItem:k=>ls.delete(k)},location:{origin:'https://example.test',pathname:'/'},document:fakeDom(),console};
   ctx.globalThis=ctx;vm.createContext(ctx);vm.runInContext(registrySrc,ctx);vm.runInContext(studioSrc,ctx);window.MBUStudio.db();
   assert.equal(writes,0,'Studio startup must not rewrite storage when no revised-question state exists');
   window.MBUStudio.answer('b1',{uid:revisedUid,id:revisedUid.slice(3),topic:'Monitoring'},true);
   const saved=JSON.parse(ls.get('mbu_exam1_studio_v1'));
   assert.equal(saved.revisions[revisedUid],2,'the revision mark is saved with the next real Studio write');
   assert.ok(saved.ans[revisedUid],'a new-revision answer is stored normally');
   const ctx2={...ctx};vm.createContext(ctx2);vm.runInContext(registrySrc,ctx2);vm.runInContext(studioSrc,ctx2);ctx2.window.MBUStudio.db();
   assert.ok(JSON.parse(ls.get('mbu_exam1_studio_v1')).ans[revisedUid],'a new-revision answer is never archived on reload')}
}
console.log('Content revision tests passed: '+manifestIds.length+' revised questions; fingerprints, IDs and sets verified; learner history preserved and isolated; calibration separated by revision; bank and Studio saved state migrated safely.');
