/* CAT uses canonical course manifests; ordinary Studio pools stay course-scoped. */
const CAT_COURSES=[{courseId:'equipment',examId:'exam-1'},{courseId:'basic-principles',examId:'exam-1'},{courseId:'pharm',examId:'clinical-pharm'}];
let CAT_ALL=[],CAT_BY_UID=new Map(),catPoolPromise=null,catPoolFailed=false;
function catQuestionContext(q){return q?.courseId?{courseId:q.courseId,examId:q.examId}:(window.MBU_CONTEXT||{})}
function catSessionPool(){return DB.active?.crossCourse?CAT_ALL:ALL}
function catQuestion(uid){return ALL_BY_UID.get(uid)||CAT_BY_UID.get(uid)}
async function loadCatPool(){
 if(catPoolPromise)return catPoolPromise;
 catPoolPromise=(async()=>{
 const groups=await Promise.all(CAT_COURSES.map(async ctx=>{
 const root=new URL(ctx.courseId+'/'+ctx.examId+'/',MBUBuild.appRoot),manifest=await MBUBuild.fetchJSON(new URL('banks.json',root),{cache:'no-store'});
 if(!Array.isArray(manifest.studioSources))throw Error('Invalid CAT manifest: '+ctx.courseId);
 const sources=await Promise.all(manifest.studioSources.map(async src=>{
 if(src.format!=='canonical')throw Error('Invalid CAT source: '+src.key);
 const payload=await studioFetch(new URL(src.data,root).href),all=Array.isArray(payload)?payload:payload.questions;
 if(!Array.isArray(all))throw Error('Invalid CAT data: '+src.key);
 const raw=src.setFilter?all.filter(q=>Number(q.set)===Number(src.setFilter)):all;
 if(raw.length!==Number(src.count))throw Error('Incomplete CAT source: '+src.key);
 return raw.map((q,i)=>{
 const row=norm(q,src.key,String(src.key).startsWith('h')?1:q.set||1,i,src.label);
 if(src.imageBase&&q.imageId)row.img={kind:'direct',url:new URL(src.imageBase.replace(/\/?$/,'/')+q.imageId+'.png',root).href};
 else if(row.img?.kind==='direct')row.img={...row.img,url:new URL(row.img.url,root).href};
 return {...row,...ctx};
 });
 }));return sources.flat();
 }));
 const rows=groups.flat(),ids=new Set();for(const q of rows){if(ids.has(q.uid))throw Error('Duplicate CAT question ID: '+q.uid);ids.add(q.uid)}
 CAT_ALL=rows;CAT_BY_UID=new Map(rows.map(q=>[q.uid,q]));catPoolFailed=false;return rows;
 })().catch(e=>{catPoolFailed=true;catPoolPromise=null;throw e});return catPoolPromise;
}
async function catExposureRows(crossCourse){
 const contexts=crossCourse?CAT_COURSES:[window.MBU_CONTEXT||{}];
 return (await Promise.all(contexts.map(async ctx=>(await MBUSupabase.questionExposure(ctx.courseId,ctx.examId)).map(row=>({...row,...ctx}))))).flat();
}
function catUnseenPool(pool,rows){
 const blocked=new Set(),keys=new Set();
 for(const r of rows)if(Number(r.times_viewed)>0||Number(r.times_answered)>0||Number(r.times_issued)>0&&Date.now()-Date.parse(r.last_issued_at||0)<30*60000)blocked.add(r.question_uid);
 for(const q of pool)if(blocked.has(q.uid)||MBUStudyIntelligence.questionStats(q.uid,q)?.attempts)keys.add(MBUAdaptiveQuiz.contentKey(q));
 return pool.filter(q=>!keys.has(MBUAdaptiveQuiz.contentKey(q)));
}
