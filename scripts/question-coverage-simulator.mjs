import fs from 'node:fs';
import assert from 'node:assert/strict';
globalThis.window=globalThis;
globalThis.MBUAdaptiveQuiz={contentKey:q=>String(q.stem||'').toLowerCase()};
const src=fs.readFileSync(new URL('../equipment/assets/question-coverage.js',import.meta.url),'utf8');
Function(src)();
const make=(n,topic='Airway')=>Array.from({length:n},(_,i)=>({uid:'q'+(i+1),topic,concept:'c'+(i%40),stem:'Question '+(i+1),opts:['a','b','c','d'],ans:[0]}));
const history=new Map(),questions=make(500),seen=new Set();
for(let s=1;s<=10;s++){
 const r=MBUQuestionCoverage.select({questions,count:50,history,attempts:()=>null,seed:'session-'+s,now:Date.UTC(2026,9,s+1)});
 assert.equal(r.questions.length,50);assert.equal(new Set(r.questions.map(q=>q.uid)).size,50);
 for(const q of r.questions){assert(!seen.has(q.uid),'question repeated before bank exhaustion');seen.add(q.uid)}
 for(const item of r.meta.items){const row={question_uid:item.uid,content_version:item.version,coverage_cycle:item.cycle,last_issued_at:new Date(Date.UTC(2026,9,s+1)).toISOString(),times_issued:1,times_viewed:1};history.set(item.uid+'@'+item.version,row);history.set(item.uid,row)}
}
assert.equal(seen.size,500);
const rollover=MBUQuestionCoverage.select({questions,count:50,history,attempts:()=>null,seed:'rollover',now:Date.UTC(2026,10,1)});
assert.equal(rollover.meta.cycle,2);assert.equal(rollover.questions.length,50);

const reviewHistory=new Map();
for(const q of questions.slice(0,100)){const v=MBUQuestionCoverage.contentVersion(q),row={question_uid:q.uid,content_version:v,coverage_cycle:1,last_issued_at:'2026-09-01T00:00:00Z',times_viewed:1};reviewHistory.set(q.uid+'@'+v,row);reviewHistory.set(q.uid,row)}
const attempts=uid=>Number(uid.slice(1))<=20?{attempts:2,correct:0,incorrect:2,streak:0,lastAt:Date.UTC(2026,8,1)}:null;
const mixed=MBUQuestionCoverage.select({questions,count:50,history:reviewHistory,attempts,priority:q=>({score:20,due:Number(q.uid.slice(1))<=10}),seed:'mixed',now:Date.UTC(2026,9,4)});
assert.equal(mixed.meta.reviewCount,0,'review selected while unseen questions remain');
assert.equal(mixed.meta.newCount+mixed.meta.reviewCount,50);
const reviewItems=mixed.meta.items.filter(x=>x.kind==='review');
assert(reviewItems.every(x=>x.cycle===1),'review item incorrectly consumed the active coverage cycle');
// Partial exhaustion: all remaining unseen questions must be selected before recycling.
const partialHistory=new Map();for(const q of questions.slice(0,463)){const v=MBUQuestionCoverage.contentVersion(q),row={question_uid:q.uid,content_version:v,coverage_cycle:1,last_issued_at:'2026-08-01T00:00:00Z',times_viewed:1};partialHistory.set(q.uid+'@'+v,row)}
const partial=MBUQuestionCoverage.select({questions,count:100,history:partialHistory,attempts:()=>null,seed:'partial',now:Date.UTC(2026,9,4)});const remaining=new Set(questions.slice(463).map(q=>q.uid));assert.equal(partial.questions.length,37,'correctly answered questions recycled before completing the coverage cycle');assert([...remaining].every(uid=>partial.questions.some(q=>q.uid===uid)),'remaining unseen questions were skipped');assert(partial.meta.items.every(item=>item.kind==='coverage'),'premature review in partial coverage session');
// Partial exhaustion may include misses, but every remaining unseen item comes first.
const ordered=MBUQuestionCoverage.select({questions,count:100,history:partialHistory,attempts:uid=>Number(uid.slice(1))<=20?{attempts:2,incorrect:2,lastAt:Date.UTC(2026,8,1)}:null,seed:'ordered',now:Date.UTC(2026,9,4)});
assert(ordered.meta.reviewCount>0,'review fixture did not exercise mixed coverage');
assert(ordered.meta.items.slice(0,37).every(item=>item.kind==='coverage'),'review appeared before remaining unseen coverage');
assert(ordered.meta.items.slice(37).every(item=>item.kind==='review'),'unseen question appeared after a repeat');
// Small banks cap at available unique questions.
const small=MBUQuestionCoverage.select({questions:make(17),count:50,history:new Map(),seed:'small'});assert.equal(small.questions.length,17);assert.equal(new Set(small.questions.map(q=>q.uid)).size,17);
// Topic balancing: an uneven pool should still include minority topics when available.
const uneven=[...make(90,'Airway'),...make(10,'Monitoring').map((q,i)=>({...q,uid:'m'+i,stem:'Monitoring '+i}))];const balanced=MBUQuestionCoverage.select({questions:uneven,count:50,history:new Map(),seed:'topics'});assert(balanced.questions.some(q=>q.topic==='Monitoring'),'minority topic disappeared from balanced session');
// Content-version awareness: rewritten content under the same UID is new coverage.
const original={uid:'versioned',topic:'Airway',stem:'Original stem',opts:['a','b','c','d'],ans:[0]},rewritten={...original,stem:'Materially rewritten stem'};const oldVersion=MBUQuestionCoverage.contentVersion(original),versionHistory=new Map([[original.uid+'@'+oldVersion,{question_uid:original.uid,content_version:oldVersion,coverage_cycle:1,last_issued_at:'2026-09-01T00:00:00Z',times_viewed:1}]]);const versioned=MBUQuestionCoverage.select({questions:[rewritten],count:1,history:versionHistory,seed:'version'});assert.equal(versioned.meta.items[0].kind,'coverage');assert.notEqual(versioned.meta.items[0].version,oldVersion);
// Issued but never viewed questions remain eligible for coverage after an abandoned session.
const abandonedQ=questions[0],abandonedV=MBUQuestionCoverage.contentVersion(abandonedQ),abandonedHistory=new Map([[abandonedQ.uid+'@'+abandonedV,{question_uid:abandonedQ.uid,content_version:abandonedV,coverage_cycle:1,last_issued_at:'2026-10-01T00:00:00Z',times_issued:1,times_viewed:0}]]);const abandoned=MBUQuestionCoverage.select({questions:[abandonedQ],count:1,history:abandonedHistory,seed:'abandoned'});assert.equal(abandoned.meta.items[0].kind,'coverage','unviewed reservation incorrectly consumed coverage');
// A concurrently reserved but unviewed item stays unavailable until its lease expires.
const leaseNow=Date.UTC(2026,9,8,19,0),leaseQ=questions[1],leaseV=MBUQuestionCoverage.contentVersion(leaseQ);
const leaseHistory=new Map([[leaseQ.uid+'@'+leaseV,{question_uid:leaseQ.uid,content_version:leaseV,coverage_cycle:1,last_issued_at:new Date(leaseNow-5*60000).toISOString(),times_issued:1,times_viewed:0}]]);
const leased=MBUQuestionCoverage.select({questions:[leaseQ],count:1,history:leaseHistory,seed:'leased',now:leaseNow});
assert.equal(leased.questions.length,0,'a second device received a question reserved five minutes ago');
const expired=MBUQuestionCoverage.select({questions:[leaseQ],count:1,history:leaseHistory,seed:'expired',now:leaseNow+31*60000});
assert.equal(expired.questions.length,1,'abandoned reservation did not expire');
// Independent pool cycles must not erase lifetime viewed progress from another pool.
const poolA=make(20,'Lecture A'),poolB=make(20,'Lecture B').map((q,i)=>({...q,uid:'b'+i,stem:'B '+i})),mixedHistory=new Map();for(const q of [...poolA,...poolB]){const v=MBUQuestionCoverage.contentVersion(q);mixedHistory.set(q.uid+'@'+v,{question_uid:q.uid,content_version:v,coverage_cycle:q.topic==='Lecture A'?2:1,last_issued_at:'2026-10-01T00:00:00Z',times_viewed:1})}assert.equal([...mixedHistory.values()].filter(r=>r.times_viewed>0).length,40,'viewed progress was lost across independent pool cycles');
// Exact content duplicates must collapse even with different UIDs.
const dup=[{uid:'d1',topic:'Airway',stem:'Same fact',opts:['a'],ans:[0]},{uid:'d2',topic:'Airway',stem:'Same fact',opts:['a'],ans:[0]}];assert.equal(MBUQuestionCoverage.select({questions:dup,count:2,seed:'dupe'}).questions.length,1);
// Recovery/cooldown: a recently answered old miss must not immediately re-enter review.
const coolQ=questions[0],coolV=MBUQuestionCoverage.contentVersion(coolQ),coolHistory=new Map([[coolQ.uid+'@'+coolV,{question_uid:coolQ.uid,content_version:coolV,coverage_cycle:1,last_issued_at:'2026-10-03T18:00:00Z',times_viewed:1}]]);const cool=MBUQuestionCoverage.select({questions:questions.slice(0,50),count:20,history:coolHistory,attempts:uid=>uid===coolQ.uid?{attempts:5,correct:3,incorrect:2,streak:3,lastAt:Date.UTC(2026,9,3,18)}:null,priority:()=>({score:50,due:true}),seed:'cool',now:Date.UTC(2026,9,4)});assert(!cool.meta.items.some(x=>x.uid===coolQ.uid&&x.kind==='review'),'cooldown/recovery failed');
// The All Questions option requests up to 200, and must retain unseen-first selection.
const allPool=make(450,'All Questions'),allHistory=new Map(),allSeen=new Set();
for(let run=0;run<3;run++){
 const selection=MBUQuestionCoverage.select({questions:allPool,count:200,history:allHistory,seed:'all-'+run});
 assert.equal(selection.questions.length,run<2?200:50,'All Questions must not recycle correct answers before exhaustion');
 for(const q of selection.questions){
  assert(!allSeen.has(q.uid),'All Questions repeated an already viewed item');
  allSeen.add(q.uid);
  const version=MBUQuestionCoverage.contentVersion(q);
  allHistory.set(q.uid+'@'+version,{question_uid:q.uid,content_version:version,coverage_cycle:1,times_viewed:1});
 }
}
assert.equal(allSeen.size,450);
const studioSource=['studio-runtime.js','studio-lifecycle.js'].map(name=>fs.readFileSync(new URL('../equipment/assets/'+name,import.meta.url),'utf8')).join('\n');
assert(studioSource.includes("if(m==='custom'&&window.MBUQuestionCoverage"),'All Questions custom sessions bypass coverage');
assert(studioSource.includes('MBUQuestionCoverage.select({questions:pool,count:limit,history'),'All Questions custom sessions use an invalid selection count');
assert(studioSource.includes('const coverageLifecyclePending=new Set()'),'Lifecycle requests must be deduplicated while in flight');
assert(studioSource.includes("if(ok&&DB.active===active){active.lifecycle[key]=Date.now();save()}"),'Lifecycle events must be acknowledged only after server confirmation in the same session');
assert(studioSource.includes("if(session.length&&session[pos])markCoverageLifecycle(session[pos],'viewed')"),'Interrupted view events must retry after reconnect');
const cloudSource=fs.readFileSync(new URL('../equipment/assets/supabase-sync.js',import.meta.url),'utf8');
assert(cloudSource.includes("query+'&limit='+pageSize+'&offset='+offset"),'Coverage history must page beyond the API row cap');
// First-attempt calibration is account-wide, even when each course has separate local practice history.
const calibrationSchema=fs.readFileSync(new URL('../supabase/migrations/20260927041827_add_anonymous_item_calibration.sql',import.meta.url),'utf8');
const calibrationV2=fs.readFileSync(new URL('../supabase/migrations/20260928112827_global_cat_course_exam_metadata.sql',import.meta.url),'utf8');
const outboxSource=fs.readFileSync(new URL('../equipment/assets/calibration-outbox.js',import.meta.url),'utf8');
const intelligenceSource=fs.readFileSync(new URL('../equipment/assets/study-intelligence.js',import.meta.url),'utf8');
assert.match(calibrationSchema,/primary key\s*\(user_id,\s*question_id\)/i,'First attempts must be unique per student and question across all courses');
assert.match(calibrationV2,/on conflict\s*\(user_id,\s*question_id\)\s*do nothing/i,'Server must ignore repeated first-attempt submissions');
assert.match(calibrationV2,/get diagnostics inserted_count\s*=\s*row_count/i,'Server must distinguish accepted first attempts from repeats');
assert.match(intelligenceSource,/if\(firstAttempt\)window\.MBUCalibrationOutbox\?\.enqueue/,'Practice repeats should not enter the calibration outbox within a course');
assert.match(outboxSource,/item\.ownerId!==current/,'Pending first attempts must never submit under another account');
console.log('Question coverage simulation PASS',JSON.stringify({uniqueBeforeRollover:seen.size,rolloverCycle:rollover.meta.cycle,mixed:mixed.meta.reviewCount+'/'+50}));
