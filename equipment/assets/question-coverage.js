(()=>{'use strict';
const DAY=86400000;
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
const hash=s=>{let h=2166136261;for(const c of String(s)){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return h>>>0};
function contentVersion(q){return String(q?.contentVersion||q?.sourceMeta?.contentVersion||hash([q?.stem,(q?.opts||[]).join('|'),(q?.ans||[]).join(',')].join('::')).toString(36))}
function unique(rows){const u=new Set(),c=new Set(),out=[];for(const q of rows||[]){if(!q?.uid||u.has(q.uid))continue;const ck=window.MBUAdaptiveQuiz?.contentKey?.(q)||String(q.stem||'').trim().toLowerCase();if(ck&&c.has(ck))continue;u.add(q.uid);if(ck)c.add(ck);out.push(q)}return out}
function seeded(rows,seed){return [...rows].sort((a,b)=>hash(seed+':'+a.uid)-hash(seed+':'+b.uid))}
function rowFor(history,q){return history?.get?.(q.uid+'@'+contentVersion(q))||history?.get?.(q.uid)||null}
function dynamicReviewRate(questions,attempts){
 let answered=0,correct=0;for(const q of questions){const a=attempts?.(q.uid);if(!a?.attempts)continue;answered+=Number(a.attempts)||0;correct+=Number(a.correct)||0}
 if(!answered)return .12;const accuracy=correct/answered;return accuracy>=.9?.10:accuracy<.7?.22:.15
}
function reviewWeight(q,attempts,priority,now){
 const a=attempts?.(q.uid),p=priority?.(q)||{},tries=Number(a?.attempts)||0,wrong=Number(a?.incorrect)||0,streak=Number(a?.streak)||0,last=Number(a?.lastAt)||0;
 if(!tries||!wrong)return -1;
 const ageDays=last?Math.max(0,(now-last)/DAY):30,cooldown=ageDays<1?-80:ageDays<3?-25:0,recovery=Math.min(35,streak*12);
 return wrong*22+Math.min(30,ageDays*2)+(p.due?35:0)+(Number(p.score)||0)*.35-recovery+cooldown
}
function select({questions,count,history=new Map(),attempts,priority,seed=String(Date.now()),now=Date.now(),reviewRate}){
 const pool=unique(questions),limit=Math.min(Math.max(1,Number(count)||50),pool.length);if(!pool.length)return{questions:[],meta:{newCount:0,reviewCount:0,cycle:1}};
 const histories=pool.map(q=>rowFor(history,q)).filter(Boolean),cycle=Math.max(1,...histories.map(x=>Number(x.coverage_cycle)||1));
 let unseen=pool.filter(q=>{const h=rowFor(history,q);return !h||Number(h.coverage_cycle||0)<cycle});
 if(!unseen.length){unseen=pool.slice();} // caller records cycle+1 below
 const rollover=histories.length>=pool.length&&!pool.some(q=>!rowFor(history,q)),activeCycle=rollover?cycle+1:cycle;
 const rate=clamp(Number.isFinite(reviewRate)?reviewRate:dynamicReviewRate(pool,attempts),.10,.25),targetReview=Math.min(Math.floor(limit*rate),Math.max(0,limit-1));
 const recentCutoff=now-2*DAY;
 const review=pool.map(q=>({q,h:rowFor(history,q),w:reviewWeight(q,attempts,priority,now)}))
   .filter(x=>x.h&&x.w>0&&Date.parse(x.h.last_issued_at||0)<recentCutoff)
   .sort((a,b)=>b.w-a.w||Date.parse(a.h.last_issued_at||0)-Date.parse(b.h.last_issued_at||0));
 const pickedReview=review.slice(0,targetReview).map(x=>x.q),used=new Set(pickedReview.map(q=>q.uid));
 const need=limit-pickedReview.length;
 let coverage=seeded(unseen.filter(q=>!used.has(q.uid)),seed).slice(0,need);
 if(coverage.length<need){
   const fill=pool.filter(q=>!used.has(q.uid)&&!coverage.some(x=>x.uid===q.uid)).sort((a,b)=>Date.parse(rowFor(history,a)?.last_issued_at||0)-Date.parse(rowFor(history,b)?.last_issued_at||0)||hash(seed+a.uid)-hash(seed+b.uid));
   coverage=coverage.concat(fill.slice(0,need-coverage.length))
 }
 const reviewIds=new Set(pickedReview.map(q=>q.uid)),raw=seeded([...coverage,...pickedReview],seed+':final'),selected=[];
 for(const q of raw){const concept=String(q.concept||q.topic||'');let at=selected.length;if(at&&String(selected[at-1].concept||selected[at-1].topic||'')===concept){const swap=raw.findIndex((x,i)=>i>at&&String(x.concept||x.topic||'')!==concept&&!selected.includes(x));if(swap>=0){selected.push(raw[swap]);raw.splice(swap,1);continue}}selected.push(q)}
 return{questions:selected,meta:{newCount:coverage.length,reviewCount:pickedReview.length,cycle:activeCycle,reviewRate:rate,items:selected.map(q=>{const h=rowFor(history,q);return{uid:q.uid,topic:q.topic||'Other',version:contentVersion(q),cycle:reviewIds.has(q.uid)?Math.max(1,Number(h?.coverage_cycle)||1):activeCycle,kind:reviewIds.has(q.uid)?'review':'coverage'}})}}
}
window.MBUQuestionCoverage={select,contentVersion,dynamicReviewRate};
})();