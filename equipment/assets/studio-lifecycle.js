/* Durable retries use the original reservation, even after completion or cancellation. */
const coverageLifecyclePending=new Set();
function lifecycleOwner(){return String(window.MBUSupabase?.currentUser?.()?.id||'')}
function retryCoverageLifecycle(){
 for(const [key,item] of Object.entries(DB.lifecycleOutbox||{})){
  if(item.ownerId!==lifecycleOwner()||coverageLifecyclePending.has(key))continue;
  const db=DB;coverageLifecyclePending.add(key);
  window.MBUSupabase.markQuestionLifecycle(item).then(ok=>{
   if(!ok||DB!==db||item.ownerId!==lifecycleOwner())return;
   delete db.lifecycleOutbox[key];const active=db.active;if(active&&(active.questionSessionIds?.[item.questionUid]||active.sessionId)===item.sessionId){active.lifecycle=active.lifecycle||{};active.lifecycle[item.event+':'+item.questionUid+':'+item.contentVersion]=Date.now()}save()
  }).catch(()=>{}).finally(()=>coverageLifecyclePending.delete(key));
 }
}
function markCoverageLifecycle(q,event){
 const active=DB.active;if(!active?.coverageMeta||!active.sessionId||!q||!window.MBUSupabase?.markQuestionLifecycle)return;
 const version=window.MBUQuestionCoverage?.contentVersion?.(q)||'1',sessionId=active.questionSessionIds?.[q.uid]||active.sessionId,key=event+':'+q.uid+':'+version,pendingKey=sessionId+':'+key;
 active.lifecycle=active.lifecycle||{};if(active.lifecycle[key])return;
 const ctx=window.MBU_CONTEXT||{};DB.lifecycleOutbox=DB.lifecycleOutbox||{};
 if(!DB.lifecycleOutbox[pendingKey]){DB.lifecycleOutbox[pendingKey]={ownerId:lifecycleOwner(),courseId:ctx.courseId,examId:ctx.examId,questionUid:q.uid,contentVersion:version,event,sessionId};save()}
 if(coverageLifecyclePending.has(pendingKey))return;
 const db=DB;coverageLifecyclePending.add(pendingKey);
 window.MBUSupabase.markQuestionLifecycle(db.lifecycleOutbox[pendingKey]).then(ok=>{
  if(!ok||DB!==db||db.lifecycleOutbox[pendingKey]?.ownerId!==lifecycleOwner())return;
  delete db.lifecycleOutbox[pendingKey];
  if(ok&&DB.active===active){active.lifecycle[key]=Date.now();save()}else save()
 }).catch(()=>{}).finally(()=>coverageLifecyclePending.delete(pendingKey))
}
function retryCoverageAnswers(){retryCoverageLifecycle();if(!DB.active?.coverageMeta)return;for(const [uid,a] of Object.entries(DB.active.answers||{}))if(a&&ALL_BY_UID.has(uid))markCoverageLifecycle(ALL_BY_UID.get(uid),'answered');if(session.length&&session[pos])markCoverageLifecycle(session[pos],'viewed')}
window.addEventListener('online',retryCoverageAnswers);
