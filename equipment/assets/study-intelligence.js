/* Shared study intelligence: attempts, spaced review, mastery, activity, reports, analytics, and adaptive priority. */
(()=>{'use strict';
const ctx=window.MBU_CONTEXT||{},courseId=String(ctx.courseId||''),examId=String(ctx.examId||''),STORE=courseId==='equipment'&&examId==='exam-1'?'mbu_study_intelligence_v1':`mbu_study_intelligence_${courseId}_${examId}_v1`,SCHEMA=1,MAX_ACTIVITY=1200,DAY=86400000;
let cache=null,lastSerialized='';
const plain=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
const safeJSON=(raw,fallback)=>{try{return JSON.parse(raw)??fallback}catch{return fallback}};
const now=()=>Date.now(),clamp=(v,min,max)=>Math.max(min,Math.min(max,v));
const uidOf=(bank,q)=>String(q?.uid||((bank||q?.bank||'unknown')+'-'+(q?.id??q?.seq??'unknown')));
const topicOf=q=>String(q?.topic||q?.lec||q?.concept||'Other').trim()||'Other';
const bankOf=(bank,q)=>String(bank||q?.bank||'unknown');
const bankLabelOf=(label,bank,q)=>String(label||q?.bankLabel||bankOf(bank,q));
const blank=()=>({schema:SCHEMA,updatedAt:0,attempts:{},reviews:{},activity:[],issues:[],seededLegacy:false});
function normalize(raw){
  const d=plain(raw)&&Number(raw.schema)===SCHEMA?raw:blank();
  d.attempts=plain(d.attempts)?d.attempts:{};
  d.reviews=plain(d.reviews)?d.reviews:{};
  d.activity=Array.isArray(d.activity)?d.activity.filter(plain).slice(-MAX_ACTIVITY):[];
  d.issues=Array.isArray(d.issues)?d.issues.filter(plain).slice(-500):[];
  d.seededLegacy=!!d.seededLegacy;
  return d
}
function db(){if(cache)return cache;cache=normalize(safeJSON(localStorage.getItem(STORE),null));return cache}
function save(d=db()){
  d.updatedAt=now();const serialized=JSON.stringify(d);if(serialized===lastSerialized)return d;
  localStorage.setItem(STORE,serialized);lastSerialized=serialized;cache=d;window.MBUAppCore?.touchStore?.(STORE);return d
}
window.addEventListener('storage',e=>{if(e.key===STORE){cache=null;lastSerialized=''}});
function reviewInterval(attempt,ok){
  if(!ok)return 1;
  const streak=Math.max(1,Number(attempt?.streak)||1);
  return streak===1?3:streak===2?7:streak===3?14:30
}
function questionMeta(bank,q,extra={}){
  return{uid:uidOf(bank,q),courseId,examId,bank:bankOf(bank,q),bankLabel:bankLabelOf(extra.bankLabel,bank,q),set:Number(extra.set??q?.set??q?.setn??1)||1,questionId:String(extra.questionId??q?.id??q?.seq??''),topic:topicOf(q),stem:String(q?.stem||q?.q||'').trim(),href:String(extra.href||location.href)}
}
function recordAnswer(bank,q,ok,extra={}){
  const d=db(),meta=questionMeta(bank,q,extra),t=Number(extra.at)||now(),prev=d.attempts[meta.uid]||{},correct=Number(prev.correct)||0,incorrect=Number(prev.incorrect)||0,attempts=Number(prev.attempts)||0,firstAttempt=attempts===0;
  const next={...prev,...meta,attempts:attempts+1,correct:correct+(ok?1:0),incorrect:incorrect+(ok?0:1),lastAt:t,lastCorrect:!!ok,streak:ok?(Number(prev.streak)||0)+1:0};
  d.attempts[meta.uid]=next;
  const days=reviewInterval(next,!!ok);d.reviews[meta.uid]={uid:meta.uid,dueAt:t+days*DAY,intervalDays:days,lastAt:t,lastCorrect:!!ok};
  d.activity.push({id:meta.uid+':'+t,at:t,type:'answer',uid:meta.uid,bank:meta.bank,bankLabel:meta.bankLabel,topic:meta.topic,ok:!!ok,href:meta.href});
  if(d.activity.length>MAX_ACTIVITY)d.activity.splice(0,d.activity.length-MAX_ACTIVITY);
  save(d);if(firstAttempt)window.MBUCalibrationOutbox?.enqueue?.(STORE,meta.uid,{questionId:meta.uid,correct:!!ok,responseMs:extra.responseMs??null,sessionMode:extra.sessionMode||'unknown',courseId:meta.courseId,examId:meta.examId,bankId:meta.bank,topic:meta.topic});
  return next
}
function seedLegacy(records=[]){
  const d=db();if(d.seededLegacy)return false;let changed=false;
  for(const r of records){
    if(!r||!r.uid||d.attempts[r.uid])continue;
    const at=Number(r.at)||0,ok=!!r.ok;
    d.attempts[r.uid]={uid:String(r.uid),bank:String(r.bank||'unknown'),bankLabel:String(r.bankLabel||r.bank||'Unknown'),set:Number(r.set)||1,questionId:String(r.questionId||''),topic:String(r.topic||'Other'),stem:String(r.stem||''),href:String(r.href||''),attempts:1,correct:ok?1:0,incorrect:ok?0:1,lastAt:at,lastCorrect:ok,streak:ok?1:0};
    if(at)d.reviews[r.uid]={uid:String(r.uid),dueAt:at+reviewInterval(d.attempts[r.uid],ok)*DAY,intervalDays:reviewInterval(d.attempts[r.uid],ok),lastAt:at,lastCorrect:ok};
    changed=true
  }
  d.seededLegacy=true;save(d);return changed
}
function due(at=now()){return Object.values(db().reviews).filter(r=>(Number(r.dueAt)||0)<=at).sort((a,b)=>a.dueAt-b.dueAt)}
function stats(rows){
  const questions=rows.length,correct=rows.reduce((n,a)=>n+(Number(a.correct)||0),0),attempts=rows.reduce((n,a)=>n+(Number(a.attempts)||0),0);
  return{questions,attempts,correct,accuracy:attempts?Math.round(correct/attempts*100):0}
}
function masteryRow(rows,activity,at=now()){
  const base=stats(rows),attempts=base.attempts,correct=base.correct;
  if(!attempts)return{...base,mastery:0,confidence:0,trend:0,lastAt:0,status:'No data'};
  const ordered=(activity||[]).filter(x=>x.type==='answer').sort((a,b)=>a.at-b.at),recent=ordered.slice(-12),recentCorrect=recent.filter(x=>x.ok).length;
  const lifetime=(correct+2)/(attempts+4),recentRate=recent.length?(recentCorrect+1)/(recent.length+2):lifetime;
  const mastery=Math.round(100*clamp(lifetime*.7+recentRate*.3,0,1)),lastAt=Math.max(...rows.map(x=>Number(x.lastAt)||0),0),ageDays=lastAt?Math.max(0,(at-lastAt)/DAY):365;
  const evidence=1-Math.exp(-attempts/12),breadth=.65+.35*(1-Math.exp(-base.questions/6)),freshness=.65+.35*Math.exp(-ageDays/45),confidence=Math.round(100*clamp(evidence*breadth*freshness,0,1));
  let trend=0;
  if(recent.length>=6){const cut=Math.floor(recent.length/2),a=recent.slice(0,cut),b=recent.slice(cut),pct=x=>x.length?x.filter(v=>v.ok).length/x.length*100:0;trend=Math.round(pct(b)-pct(a))}
  const status=mastery<60?'Needs work':mastery<75?'Developing':mastery<88?'Solid':'Strong';
  return{...base,mastery,confidence,trend,lastAt,status}
}
function analytics(){
  const attempts=Object.values(db().attempts),byTopic={},byBank={};
  for(const a of attempts){(byTopic[a.topic]??=[]).push(a);(byBank[a.bankLabel||a.bank]??=[]).push(a)}
  const convert=o=>Object.fromEntries(Object.entries(o).map(([k,v])=>[k,stats(v)]));
  const cutoff7=now()-7*DAY,cutoff30=now()-30*DAY,activity=db().activity.filter(x=>x.type==='answer');
  const windowStats=cutoff=>{const xs=activity.filter(x=>x.at>=cutoff);return{answered:xs.length,correct:xs.filter(x=>x.ok).length,accuracy:xs.length?Math.round(xs.filter(x=>x.ok).length/xs.length*100):0}};
  return{overall:stats(attempts),byTopic:convert(byTopic),byBank:convert(byBank),last7:windowStats(cutoff7),last30:windowStats(cutoff30),due:due().length}
}
function mastery(at=now()){
  const d=db(),rows=Object.values(d.attempts),activity=d.activity.filter(x=>x.type==='answer'),grouped={};
  for(const a of rows)(grouped[a.topic]??=[]).push(a);
  const byTopic=Object.fromEntries(Object.entries(grouped).map(([topic,x])=>[topic,masteryRow(x,activity.filter(a=>a.topic===topic),at)]));
  const topics=Object.entries(byTopic).sort((a,b)=>a[1].mastery-b[1].mastery||b[1].confidence-a[1].confidence||a[0].localeCompare(b[0]));
  const overall=masteryRow(rows,activity,at);
  return{overall,byTopic,weakest:topics.slice(0,3).map(([topic,x])=>({topic,...x})),strongest:[...topics].reverse().slice(0,3).map(([topic,x])=>({topic,...x})),topicsPracticed:topics.length,due:due(at).length}
}
function questionStats(uid){const a=db().attempts[String(uid||'')];return a?{...a}:null}
function topicStats(topic){const rows=Object.values(db().attempts).filter(x=>x.topic===String(topic||''));return stats(rows)}
function priorityForQuestion(q,at=now(),snapshot=null){
  const d=db(),uid=String(q?.uid||''),personal=d.attempts[uid],review=d.reviews[uid],topic=topicOf(q),topicMastery=(snapshot||mastery(at)).byTopic?.[topic];
  let score=0,reason='Balanced practice';
  if(!personal){score+=30;reason='New coverage'}
  if(review&&Number(review.dueAt)<=at){score+=45;reason='Due review'}
  if(personal&&!personal.lastCorrect){score+=28;reason='Needs another pass'}
  if(topicMastery&&topicMastery.confidence>=15&&topicMastery.mastery<75){score+=Math.min(28,(75-topicMastery.mastery)*.9);if(reason==='Balanced practice'||reason==='New coverage')reason='Weak topic'}
  if(personal){score+=Math.min(14,(Number(personal.incorrect)||0)*3);const stale=Math.max(0,Math.floor((at-(Number(personal.lastAt)||at))/DAY));score+=Math.min(12,stale/3)}
  return{score:Math.round(clamp(score,0,100)),reason,topic,mastery:topicMastery?.mastery??null,confidence:topicMastery?.confidence??0,due:!!(review&&Number(review.dueAt)<=at),seen:!!personal}
}
function scoreQuestion(q,at=now()){return priorityForQuestion(q,at).score}
function tieRank(uid){let h=2166136261;for(const c of String(uid||'')){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return h>>>0}
function smartReview(questions,count=50){
  const n=Math.max(1,Math.min(Number(count)||50,questions.length)),snapshot=mastery();
  return questions.map((q,i)=>({q,score:priorityForQuestion(q,now(),snapshot).score,tie:tieRank(q.uid||i)})).sort((a,b)=>b.score-a.score||a.tie-b.tie).slice(0,n).map(x=>x.q)
}
function weakReview(questions,count=50,topicLimit=3){
  const m=mastery(),weak=Object.entries(m.byTopic||{}).filter(([,x])=>Number(x?.attempts)>=3).sort((a,b)=>a[1].mastery-b[1].mastery||b[1].confidence-a[1].confidence).slice(0,Math.max(1,Number(topicLimit)||3)).map(([topic])=>topic);
  if(!weak.length)return smartReview(questions,count);
  const allowed=new Set(weak),pool=questions.filter(q=>allowed.has(topicOf(q)));
  return smartReview(pool.length?pool:questions,count)
}
function recentActivity(limit=20){return db().activity.slice(-Math.max(1,limit)).reverse().map(x=>({...x}))}
function recommendation(a=analytics()){
  if(a.due)return{type:'due',label:'Review due questions',detail:a.due+' question'+(a.due===1?' is':'s are')+' ready for spaced review'};
  const m=mastery(),weak=m.weakest.find(x=>x.attempts>=3&&x.confidence>=15);
  if(weak)return{type:'topic',topic:weak.topic,label:'Review '+weak.topic,detail:weak.mastery+'% mastery estimate · '+weak.confidence+'% confidence'};
  return{type:'smart',label:'Start Smart Review',detail:'Builds priorities from your answer history'}
}
function summary(){const a=analytics(),todayStart=new Date();todayStart.setHours(0,0,0,0);const today=db().activity.filter(x=>x.type==='answer'&&x.at>=todayStart.getTime());return{...a,recommendation:recommendation(a),mastery:mastery(),today:{answered:today.length,correct:today.filter(x=>x.ok).length,accuracy:today.length?Math.round(today.filter(x=>x.ok).length/today.length*100):0,topics:new Set(today.map(x=>x.topic)).size}}}
function addIssue(bank,q,details={}){
  const d=db(),meta=questionMeta(bank,q,details),issue={id:meta.uid+':issue:'+now(),...meta,reason:String(details.reason||'Other'),comment:String(details.comment||''),at:now(),status:'open'};
  d.issues.push(issue);if(d.issues.length>500)d.issues.splice(0,d.issues.length-500);save(d);return issue
}
function issues(){return db().issues.map(x=>({...x}))}
function closeIssue(id){const d=db(),x=d.issues.find(x=>x.id===id);if(!x)return false;x.status='closed';x.closedAt=now();save(d);return true}
function clearAll(){localStorage.removeItem(STORE);cache=null;lastSerialized=''}
window.MBUStudyIntelligence={STORE,schema:SCHEMA,recordAnswer,seedLegacy,due,smartReview,weakReview,questionStats,topicStats,analytics,mastery,priorityForQuestion,recentActivity,recommendation,summary,addIssue,issues,closeIssue,questionMeta,clearAll};
})();
