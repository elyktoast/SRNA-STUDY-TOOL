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
 for(const item of r.meta.items){const row={question_uid:item.uid,content_version:item.version,coverage_cycle:item.cycle,last_issued_at:new Date(Date.UTC(2026,9,s+1)).toISOString(),times_issued:1};history.set(item.uid+'@'+item.version,row);history.set(item.uid,row)}
}
assert.equal(seen.size,500);
const rollover=MBUQuestionCoverage.select({questions,count:50,history,attempts:()=>null,seed:'rollover',now:Date.UTC(2026,10,1)});
assert.equal(rollover.meta.cycle,2);assert.equal(rollover.questions.length,50);

const reviewHistory=new Map();
for(const q of questions.slice(0,100)){const v=MBUQuestionCoverage.contentVersion(q),row={question_uid:q.uid,content_version:v,coverage_cycle:1,last_issued_at:'2026-09-01T00:00:00Z'};reviewHistory.set(q.uid+'@'+v,row);reviewHistory.set(q.uid,row)}
const attempts=uid=>Number(uid.slice(1))<=20?{attempts:2,correct:0,incorrect:2,streak:0,lastAt:Date.UTC(2026,8,1)}:null;
const mixed=MBUQuestionCoverage.select({questions,count:50,history:reviewHistory,attempts,priority:q=>({score:20,due:Number(q.uid.slice(1))<=10}),seed:'mixed',now:Date.UTC(2026,9,4)});
assert(mixed.meta.reviewCount>=5&&mixed.meta.reviewCount<=12,'review quota outside normal range');
assert.equal(mixed.meta.newCount+mixed.meta.reviewCount,50);
const reviewItems=mixed.meta.items.filter(x=>x.kind==='review');
assert(reviewItems.every(x=>x.cycle===1),'review item incorrectly consumed the active coverage cycle');
console.log('Question coverage simulation PASS',JSON.stringify({uniqueBeforeRollover:seen.size,rolloverCycle:rollover.meta.cycle,mixed:mixed.meta.reviewCount+'/'+50}));
