/* Adaptive 2.1. */
(()=>{'use strict';
const DIAGNOSTIC_LENGTH=6,TOP_CANDIDATES=8,CONCEPT_COOLDOWN=3,structuralCache=new WeakMap(),contentCache=new WeakMap(),conceptCache=new WeakMap();
const plain=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
const clamp=(v,min,max)=>Math.max(min,Math.min(max,v));
const clampLevel=v=>clamp(Number(v)||3,1,5);
const clampLogit=v=>clamp(Number(v)||0,-2.5,2.5);
const challengeToLogit=challenge=>clampLogit((clampLevel(challenge)-3)*1.25);
const logitToLevel=logit=>clampLevel(Math.round(3+clampLogit(logit)/1.25));
const logistic=x=>1/(1+Math.exp(-clamp(x,-12,12)));
const rowCertainty=row=>1-clamp(Number.isFinite(Number(row?.uncertainty))?Number(row.uncertainty):.9,.05,.95)*.35;
const popWeight=n=>n<25?0:n<100?.35:n<300?.6:.8;
const textOf=q=>String(q?.stem||q?.q||'');
function hash32(value){let h=2166136261;for(const c of String(value??'')){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return h>>>0}
function unitRandom(seed,step){let x=(Number(seed)>>>0)^Math.imul((Number(step)||0)+1,0x9e3779b1);x^=x>>>16;x=Math.imul(x,0x7feb352d);x^=x>>>15;x=Math.imul(x,0x846ca68b);x^=x>>>16;return(x>>>0)/4294967296}
function newSeed(){try{const a=new Uint32Array(1);crypto.getRandomValues(a);return a[0]||1}catch{return(hash32(Date.now()+':'+Math.random())||1)}}
function topicOf(q){return String(q?.topic||q?.lec||q?.concept||'Other').trim()||'Other'}
function conceptOf(q){
  if(q&&typeof q==='object'&&conceptCache.has(q))return conceptCache.get(q);
  const explicit=String(q?.concept||q?.disc||'').trim(),family=Array.isArray(q?.sourceMeta?.families)?String(q.sourceMeta.families[0]||'').trim():'',title=String(q?.sourceTitle||family||'').trim(),value=topicOf(q)+'|'+(explicit||title||'general');
  if(q&&typeof q==='object')conceptCache.set(q,value);return value
}
function contentKey(q){
  if(q&&typeof q==='object'&&contentCache.has(q))return contentCache.get(q);
  const stem=textOf(q).toLowerCase().replace(/[^a-z0-9]+/g,' ').trim(),value=stem||('uid:'+String(q?.uid||q?.id||''));
  if(q&&typeof q==='object')contentCache.set(q,value);return value
}
function questionStats(uid,q){return window.MBUStudyIntelligence?.questionStats?.(uid,q)||null}
function populationStats(uid){return window.MBUSupabase?.calibration?.(uid)||null}
function masterySnapshot(){return window.MBUStudyIntelligence?.mastery?.()||{byTopic:{}}}
function learningPriority(q,snapshot){return window.MBUStudyIntelligence?.priorityForQuestion?.(q,Date.now(),snapshot)||{score:0,reason:'Balanced practice',topic:topicOf(q),mastery:null,confidence:0,due:false,seen:!!questionStats(q?.uid,q)}}
function recentUids(limit=50){return new Set((window.MBUStudyIntelligence?.recentActivity?.(limit)||[]).map(x=>String(x.uid||'')))}
function recentContentKeys(questions,limit=50){
  const recent=recentUids(limit),keys=new Set(),byUid=new Map((questions||[]).filter(q=>q?.uid).map(q=>[String(q.uid),q]));
  for(const uid of recent){const saved=questionStats(uid),q=byUid.get(uid);if(saved?.stem)keys.add(contentKey({stem:saved.stem,uid}));else if(q)keys.add(contentKey(q))}
  return keys
}
function structuralEstimate(q){
  if(q&&typeof q==='object'&&structuralCache.has(q))return structuralCache.get(q);
  const stem=textOf(q),words=stem.trim().split(/\s+/).filter(Boolean).length,answers=Array.isArray(q?.ans)?q.ans:Array.isArray(q?.answer)?q.answer:[],options=Array.isArray(q?.options)?q.options:Array.isArray(q?.opts)?q.opts:[],multi=answers.length>1||String(q?.type||'').toLowerCase().includes('multi');
  let structural=2.65;
  if(multi)structural+=.5;if(options.length>=5)structural+=.12;if(words>=35)structural+=.22;if(words>=60)structural+=.18;
  if(/\b(patient|during|after|before|undergoing|receives|presents|intraoperative|preoperative|postoperative)\b/i.test(stem))structural+=.18;
  if(/\b(calculate|approximately|dose|concentration|minute ventilation|psig|mg\/kg|mcg\/kg|ml\/kg|mac)\b|%/i.test(stem))structural+=.24;
  if(/\b(not|except|least|incorrect)\b/i.test(stem))structural+=.12;if(q?.img||q?.image||q?.imageSvg||q?.imageId)structural+=.12;if(words<18&&/^(what|which|how)\b/i.test(stem.trim()))structural-=.15;
  structural=clampLevel(structural);const value={structuralChallenge:Math.round(structural*100)/100,structuralDifficulty:challengeToLogit(structural)};
  if(q&&typeof q==='object')structuralCache.set(q,value);return value
}
function difficultyEstimate(q){
  const base=structuralEstimate(q),pop=populationStats(q?.uid),learners=Number(pop?.unique_learners)||0,weight=popWeight(learners),popDifficulty=Number(pop?.difficulty_logit);
  let difficulty=base.structuralDifficulty,uncertainty=.9,source='structural';
  if(weight&&Number.isFinite(popDifficulty)){difficulty=clampLogit(base.structuralDifficulty*(1-weight)+clampLogit(popDifficulty)*weight);const popUncertainty=learners>=300?.22:learners>=100?.38:.58;uncertainty=clamp(.9*(1-weight)+popUncertainty*weight,.15,.95);source='blended'}
  return{challenge:Math.round(clampLevel(3+difficulty/1.25)*100)/100,difficulty,uncertainty,source,learners,structuralChallenge:base.structuralChallenge}
}
function challenge(q){return difficultyEstimate(q).challenge}
function estimateAbility(path=[]){
  const rows=Array.isArray(path)?path.filter(x=>plain(x)&&Number.isFinite(Number(x.difficulty))):[];
  let theta=0;const priorVar=2.25;
  for(let iter=0;iter<6;iter++){
    let gradient=-theta/priorVar,information=1/priorVar;
    for(const row of rows){const b=clampLogit(row.difficulty),p=logistic(theta-b),certainty=rowCertainty(row);gradient+=(((row.ok?1:0)-p)*certainty);information+=p*(1-p)*certainty}
    const step=gradient/Math.max(.15,information);theta=clampLogit(theta+clamp(step,-1,1));if(Math.abs(step)<.001)break
}
  let information=1/priorVar;
  for(const row of rows){const p=logistic(theta-clampLogit(row.difficulty)),certainty=rowCertainty(row);information+=p*(1-p)*certainty}
  return{theta,se:1/Math.sqrt(information),information}
}
function normalizeCounts(raw){return Object.fromEntries(Object.entries(plain(raw)?raw:{}).map(([k,v])=>[String(k),Math.max(0,Number(v)||0)]))}
function normalize(state,count=50){
  const s=plain(state)?state:{},seen=Array.isArray(s.seenUids)?[...new Set(s.seenUids.map(String).filter(Boolean))]:[],seenContentKeys=Array.isArray(s.seenContentKeys)?[...new Set(s.seenContentKeys.map(String).filter(Boolean))]:[],poolUids=Array.isArray(s.poolUids)?[...new Set(s.poolUids.map(String).filter(Boolean))]:[],path=Array.isArray(s.path)?s.path.filter(plain).slice(-200):[],estimate=path.length?estimateAbility(path):{theta:clampLogit(s.theta),se:Number(s.se)||1.5,information:Number(s.information)||0};
return{mode:'adaptive',version:3,engine:'2.1',theta:estimate.theta,se:estimate.se,information:estimate.information,level:logitToLevel(estimate.theta),answered:Math.max(0,Number(s.answered)||path.length),correct:Math.max(0,Number(s.correct)||path.filter(x=>x.ok).length),maxQuestions:Math.max(1,Math.min(200,Number(s.maxQuestions)||Number(count)||50)),seenUids:seen,seenContentKeys,poolUids,topicCounts:normalizeCounts(s.topicCounts),focusCounts:normalizeCounts(s.focusCounts),blueprintTargets:normalizeCounts(s.blueprintTargets),path,selectionSeed:(Number(s.selectionSeed)>>>0)||1,selectionStep:Math.max(0,Number(s.selectionStep)||0),currentLevel:logitToLevel(estimate.theta),currentDifficulty:s.currentDifficulty!=null&&Number.isFinite(Number(s.currentDifficulty))?clampLogit(s.currentDifficulty):null,currentChallenge:s.currentChallenge!=null&&Number.isFinite(Number(s.currentChallenge))?Number(s.currentChallenge):null,currentProbability:s.currentProbability!=null&&Number.isFinite(Number(s.currentProbability))?Number(s.currentProbability):null,currentUncertainty:s.currentUncertainty!=null&&Number.isFinite(Number(s.currentUncertainty))?Number(s.currentUncertainty):null,currentFocus:String(s.currentFocus||''),currentTopic:String(s.currentTopic||''),currentConcept:String(s.currentConcept||''),currentPhase:String(s.currentPhase||'')}
}
function uniquePool(questions,allowed){
const rows=[],seen=new Set(),ids=new Set();
for(const q of questions||[]){if(!q?.uid||ids.has(String(q.uid))||allowed&&!allowed.has(String(q.uid)))continue;ids.add(String(q.uid));const key=contentKey(q);if(seen.has(key))continue;seen.add(key);rows.push(q)}
  return rows
}
function distributionOf(questions,allowed){
  const counts={},rows=uniquePool(questions,allowed);for(const q of rows){const t=topicOf(q);counts[t]=(counts[t]||0)+1}
  return{counts,total:rows.length,rows}
}
function blueprintTargets(distribution,maxQuestions){
  const entries=Object.entries(distribution.counts),total=Math.max(1,distribution.total),limit=Math.min(maxQuestions,distribution.total),targets={},remainders=[];
  let used=0;
  for(const [topic,available] of entries){const raw=available/total*limit,base=Math.min(available,Math.floor(raw));targets[topic]=base;used+=base;remainders.push({topic,remainder:raw-base,available})}
  remainders.sort((a,b)=>b.remainder-a.remainder||a.topic.localeCompare(b.topic));
  while(used<limit){let placed=false;for(const row of remainders){if(targets[row.topic]<row.available){targets[row.topic]++;used++;placed=true;if(used>=limit)break}}if(!placed)break}
  return targets
}
function blueprintFeasible(topic,s,targets,deficits){
  const target=Number(targets[topic])||0,nextCount=(Number(s.topicCounts[topic])||0)+1;if(nextCount>target)return false;
  return deficits-1<=Math.max(0,s.maxQuestions-(s.answered+1))
}
function diagnosticTarget(answered){return[2,3,4,2.5,3.5,3][Math.min(DIAGNOSTIC_LENGTH-1,Math.max(0,Number(answered)||0))]}
function conceptPenalty(q,s){
  const concept=conceptOf(q),recent=s.path.slice(-CONCEPT_COOLDOWN).map(x=>String(x.concept||x.topic||'')),topic=topicOf(q);let penalty=0;
  if(recent[recent.length-1]===concept)penalty+=.18;else if(recent.includes(concept))penalty+=.1;
  if(s.path.at(-1)?.topic===topic)penalty+=.05;
  return{concept,penalty}
}
function candidateScore(q,s,distribution,recent,recentContent,snapshot,index,targets,deficits){
  const key=contentKey(q),estimate=difficultyEstimate(q),probability=logistic(s.theta-estimate.difficulty),information=probability*(1-probability),topic=topicOf(q),topicCount=Number(s.topicCounts[topic])||0,share=distribution.total?(distribution.counts[topic]||0)/distribution.total:0,expected=(s.answered+1)*share,balancePenalty=Math.max(0,topicCount-expected)*.055,personal=questionStats(q.uid,q),attempts=Math.max(0,Number(personal?.attempts)||0),recentPenalty=(recent.has(String(q.uid))||recentContent.has(key))?.15:0,priority=learningPriority(q,snapshot),diagnostic=s.answered<DIAGNOSTIC_LENGTH,correctRepeatPenalty=personal?.lastCorrect&&!priority.due?.85:0,priorExposurePenalty=correctRepeatPenalty||Math.min(.2,attempts*.05),personalizationWeight=diagnostic?.025:.2,priorityBonus=(priority.score/100)*personalizationWeight,newCoverageBonus=!priority.seen?.12:0,uncertaintyPenalty=estimate.uncertainty*(diagnostic?.025:.055),concept=conceptPenalty(q,s),diagnosticPenalty=diagnostic?Math.abs(estimate.challenge-diagnosticTarget(s.answered))*.09:0,diagnosticTopicPenalty=diagnostic&&topicCount>0?.08*topicCount:0,abilityPenalty=diagnostic?0:Math.abs(probability-.5),jitter=(unitRandom(s.selectionSeed^hash32(q.uid),s.selectionStep)-.5)*(diagnostic?.08:.04),score=abilityPenalty+diagnosticPenalty+diagnosticTopicPenalty+balancePenalty+recentPenalty+priorExposurePenalty+uncertaintyPenalty+concept.penalty-priorityBonus-newCoverageBonus+jitter;
  return{q,...estimate,probability,information,topic,concept:concept.concept,priority,score,tie:hash32(String(q.uid||index)+':'+s.selectionSeed),blueprintFeasible:blueprintFeasible(topic,s,targets,deficits)}
}
function chooseRandomesque(candidates,s){
  const sorted=[...candidates].sort((a,b)=>a.score-b.score||b.information-a.information||a.tie-b.tie),best=sorted[0];if(!best)return null;
  const tolerance=s.answered<DIAGNOSTIC_LENGTH?.14:.09,near=sorted.filter(x=>x.score<=best.score+tolerance).slice(0,TOP_CANDIDATES);
  if(near.length===1)return near[0];
  const r=unitRandom(s.selectionSeed,s.selectionStep),index=Math.min(near.length-1,Math.floor(r*near.length));return near[index]
}
function pick(questions,state){
  const s=normalize(state),seen=new Set(s.seenUids),allowed=s.poolUids.length?new Set(s.poolUids):null,seenContent=new Set(s.seenContentKeys);
  for(const q of questions)if(q?.uid&&seen.has(String(q.uid)))seenContent.add(contentKey(q));
  const recent=recentUids(50),recentContent=recentContentKeys(questions,50),distribution=distributionOf(questions,allowed),targets=Object.keys(s.blueprintTargets).length?s.blueprintTargets:blueprintTargets(distribution,s.maxQuestions),snapshot=masterySnapshot(),deficits=Object.entries(targets).reduce((n,[t,v])=>n+Math.max(0,Number(v)-(Number(s.topicCounts[t])||0)),0),candidates=[];let index=0;
for(const q of distribution.rows){
    const key=contentKey(q);
    if(!q?.uid||seen.has(String(q.uid))||seenContent.has(key)||(allowed&&!allowed.has(String(q.uid)))){index++;continue}
    candidates.push(candidateScore(q,s,distribution,recent,recentContent,snapshot,index,targets,deficits));index++
}
  let eligible=candidates.filter(x=>x.blueprintFeasible);if(!eligible.length)eligible=candidates;
  const chosen=chooseRandomesque(eligible,s);
  if(!chosen)return{question:null,state:{...s,blueprintTargets:targets}};
  const focus=s.answered<DIAGNOSTIC_LENGTH?'Diagnostic sampling':(chosen.priority.reason||'Balanced practice'),topic=chosen.topic,phase=s.answered<DIAGNOSTIC_LENGTH?'diagnostic':'adaptive';
  const next={...s,blueprintTargets:targets,seenUids:[...s.seenUids,String(chosen.q.uid)],seenContentKeys:[...seenContent,contentKey(chosen.q)],topicCounts:{...s.topicCounts,[topic]:(Number(s.topicCounts[topic])||0)+1},focusCounts:{...s.focusCounts,[focus]:(Number(s.focusCounts[focus])||0)+1},selectionStep:s.selectionStep+1,currentLevel:logitToLevel(s.theta),currentDifficulty:chosen.difficulty,currentChallenge:chosen.challenge,currentProbability:chosen.probability,currentUncertainty:chosen.uncertainty,currentFocus:focus,currentTopic:topic,currentConcept:chosen.concept,currentPhase:phase};
  return{question:chosen.q,state:next,challenge:chosen.challenge,difficulty:chosen.difficulty,probability:chosen.probability,information:chosen.information,uncertainty:chosen.uncertainty,difficultySource:chosen.source,focus,topic,concept:chosen.concept,phase,priority:chosen.priority.score,blueprint:{targets:{...targets},counts:{...next.topicCounts}}}
}
function start(questions,count=50,options={}){
questions=uniquePool(questions);const maxQuestions=Math.max(1,Math.min(Number(count)||50,questions.length||1)),seed=(Number(options.selectionSeed)>>>0)||newSeed();
  return pick(questions,normalize({theta:0,maxQuestions,poolUids:questions.map(q=>String(q.uid)),seenContentKeys:[],focusCounts:{},selectionSeed:seed},maxQuestions))
}
function advance(state,q,ok){
const s=normalize(state),estimate=s.currentDifficulty!=null&&Number.isFinite(Number(s.currentDifficulty))?{difficulty:clampLogit(s.currentDifficulty),challenge:Number(s.currentChallenge)||challenge(q),uncertainty:Number(s.currentUncertainty)||difficultyEstimate(q).uncertainty}:difficultyEstimate(q),before=s.theta,path=[...s.path,{uid:String(q?.uid||''),ok:!!ok,difficulty:estimate.difficulty,challenge:estimate.challenge,uncertainty:estimate.uncertainty,focus:s.currentFocus,topic:s.currentTopic||topicOf(q),concept:s.currentConcept||conceptOf(q),phase:s.currentPhase||'',at:Date.now()}].slice(-200),ability=estimateAbility(path),after=ability.theta;
  return{...s,theta:after,se:ability.se,information:ability.information,level:logitToLevel(after),currentLevel:logitToLevel(after),currentDifficulty:null,currentChallenge:null,currentProbability:null,currentUncertainty:null,currentFocus:'',currentTopic:'',currentConcept:'',currentPhase:'',answered:s.answered+1,correct:s.correct+(ok?1:0),path:[...path.slice(0,-1),{...path[path.length-1],thetaBefore:before,thetaAfter:after}]}
}
function sessionProfile(state,terminationPolicy={}){
  const s=normalize(state),accuracy=s.answered?Math.round(s.correct/s.answered*100):0,diagnosticRemaining=Math.max(0,DIAGNOSTIC_LENGTH-s.answered),blueprintRemaining={},termination=window.MBUCATTermination?.evaluate?.(s,terminationPolicy)||null;
  for(const [topic,target] of Object.entries(s.blueprintTargets))blueprintRemaining[topic]=Math.max(0,Number(target)-(Number(s.topicCounts[topic])||0));
  return{version:3,engine:'2.1',answered:s.answered,correct:s.correct,accuracy,challengeLevel:s.level,precision:s.se<=.55?'higher':s.se<=.85?'building':'early',diagnosticRemaining,phase:diagnosticRemaining?'diagnostic':'adaptive',focusCounts:{...s.focusCounts},blueprintTargets:{...s.blueprintTargets},blueprintRemaining,termination}
}
window.MBUAdaptiveQuiz={DIAGNOSTIC_LENGTH,challenge,difficultyEstimate,estimateAbility,blueprintTargets,normalize,start,pick,advance,sessionProfile,topicOf,conceptOf,contentKey};
})();
