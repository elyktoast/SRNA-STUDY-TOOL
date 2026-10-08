(()=>{'use strict';
async function accountStats(){
 const token=await MBUSupabase.accessToken();if(!token)throw Error('Sign in first.');
 const cfg=window.MBU_SUPABASE_CONFIG||{},base=String(cfg.url||'').replace(/\/$/,''),key=cfg.publishableKey||cfg.anonKey||'';if(!base||!key)throw Error('Stats not configured.');const api=async path=>{const r=await fetch(base+path,{headers:{apikey:key,Authorization:'Bearer '+token}});if(!r.ok)throw Error('Stats ('+r.status+')');return r.json()},rows=[],groups=new Map(),unique=new Set();for(let offset=0;;offset+=500){const page=await api('/rest/v1/mbu_question_exposure?select=course_id,exam_id,question_uid,content_version,times_answered,first_answered_at&first_answered_at=not.is.null&order=course_id.asc,exam_id.asc,question_uid.asc,content_version.asc&limit=500&offset='+offset);if(!Array.isArray(page))throw Error('Invalid coverage history.');rows.push(...page);if(page.length<500)break}let totalAttempts=0;
 for(const r of rows||[]){const k=String(r.course_id||'')+'::'+String(r.exam_id||''),g=groups.get(k)||{courseId:String(r.course_id||''),examId:String(r.exam_id||''),uniqueAnswered:0,totalAttempts:0};const id=k+'::'+String(r.question_uid||'');if(!unique.has(id)){unique.add(id);g.uniqueAnswered++}g.totalAttempts+=Number(r.times_answered)||0;totalAttempts+=Number(r.times_answered)||0;groups.set(k,g)}
 const roots=[['equipment','exam-1','Equipment','equipment/exam-1/banks.json'],['basic-principles','exam-1','Basic Principles','basic-principles/exam-1/banks.json'],['pharm','clinical-pharm','Clinical Pharm','pharm/clinical-pharm/banks.json']],inventory=[];
 for(const [courseId,examId,label,path] of roots){try{const m=await MBUBuild.fetchJSON(new URL(path,MBUSupabase.appRoot),{cache:'force-cache'});inventory.push({courseId,examId,label,total:(m.studioSources||[]).reduce((n,x)=>n+Number(x.count||0),0)})}catch{}}
 return{uniqueAnswered:unique.size,totalAttempts,courses:[...groups.values()],inventory}
}
window.MBUAccountStatistics={read:accountStats};
})();
