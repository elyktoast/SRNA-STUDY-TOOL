/* Lazy cloud device/history management for SRNA Study Tool. */
(()=>{'use strict';
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
function storeLabel(key){
  const map={
    SRNA_COMBINED_EXAM_SET_1_2026_V1:'Quiz Bank 1',
    srna_all5_groundup_v1:'Quiz Bank 2',
    srna_equipment_dashboard_v1:'Quiz Bank 3',
    MBU_COMBINED_BANK_2026_V1:'Combined',
    SRNA_HAZARDS_BANK_1_2026_V2:'Hazards Set 1',
    SRNA_HAZARDS_BANK_2_2026_V1:'Hazards Set 2',
    hazards_practice3_progress_2026_V2:'Hazards Set 3',
    hazards_harder_progress_2026_V1:'Hazards Challenge',
    mbu_exam1_studio_v1:'Study Studio',
    mbu_study_intelligence_v1:'Study Intelligence',
    mbu_generated_questions_v1:'Generated Questions'
  };return map[key]||key
}
function relativeTime(ts){
  const t=Date.parse(ts)||Number(ts)||0;if(!t)return 'Unknown';
  const d=Math.max(0,Date.now()-t),min=Math.floor(d/60000),hr=Math.floor(d/3600000),day=Math.floor(d/86400000);
  return min<1?'Just now':min<60?min+'m ago':hr<24?hr+'h ago':day+'d ago'
}
async function accountStats(){
 const token=await MBUSupabase.accessToken();if(!token)throw Error('Sign in first.');
 const api=async url=>{const r=await fetch(new URL(url,MBUSupabase.appRoot),{headers:{apikey:window.SRNA_SUPABASE?.anonKey||'',Authorization:'Bearer '+token}});if(!r.ok)throw Error('Stats failed ('+r.status+')');return r.json()},rows=await api('https://vqmzhyvrqmboycnyoxcb.supabase.co/rest/v1/mbu_question_exposure?select=course_id,exam_id,question_uid,times_answered,first_answered_at&first_answered_at=not.is.null'),groups=new Map();let totalAttempts=0;
 for(const r of rows||[]){const k=String(r.course_id||'')+'::'+String(r.exam_id||''),g=groups.get(k)||{courseId:String(r.course_id||''),examId:String(r.exam_id||''),uniqueAnswered:0,totalAttempts:0};g.uniqueAnswered++;g.totalAttempts+=Number(r.times_answered)||0;totalAttempts+=Number(r.times_answered)||0;groups.set(k,g)}
 const roots=[['equipment','exam-1','Equipment','equipment/exam-1/banks.json'],['basic-principles','exam-1','Basic Principles','basic-principles/exam-1/banks.json'],['pharm','clinical-pharm','Clinical Pharm','pharm/clinical-pharm/banks.json']],inventory=[];
 for(const [courseId,examId,label,path] of roots){try{const m=await MBUBuild.fetchJSON(new URL(path,MBUSupabase.appRoot),{cache:'force-cache'});inventory.push({courseId,examId,label,total:(m.studioSources||[]).reduce((n,x)=>n+Number(x.count||0),0)})}catch{}}
 return{uniqueAnswered:(rows||[]).length,totalAttempts,courses:[...groups.values()],inventory}
}
async function renderStats(modal){
 const host=modal.querySelector('[data-account-stats]');if(!host)return;host.textContent='Loading';
 try{const s=await accountStats(),byKey=new Map(s.courses.map(x=>[x.courseId+'::'+x.examId,x])),total=s.inventory.reduce((n,x)=>n+x.total,0),answered=Math.min(s.uniqueAnswered,total||Infinity),pct=total?Math.round(answered/total*1000)/10:0;host.innerHTML='<div class="mbu-account-stats-summary"><div><span>Unique answered</span><strong>'+answered.toLocaleString()+' / '+total.toLocaleString()+'</strong><small>'+pct+'% of question library</small></div><div><span>Total answers</span><strong>'+s.totalAttempts.toLocaleString()+'</strong><small>Including repeats</small></div></div><div class="mbu-account-progress"><i style="width:'+Math.min(100,pct)+'%"></i></div><div class="mbu-account-stats-courses">'+s.inventory.map(x=>{const g=byKey.get(x.courseId+'::'+x.examId)||{uniqueAnswered:0,totalAttempts:0},u=Math.min(g.uniqueAnswered,x.total),p=x.total?Math.round(u/x.total*1000)/10:0;return '<div class="mbu-account-course-stat"><span><strong>'+esc(x.label)+'</strong><small>'+u.toLocaleString()+' / '+x.total.toLocaleString()+' unique · '+p+'% · '+g.totalAttempts.toLocaleString()+' answers</small><i><em style="width:'+Math.min(100,p)+'%"></em></i></span><b>'+Math.max(0,x.total-u).toLocaleString()+' left</b></div>'}).join('')+'</div><p class="mbu-account-stats-note">Each question counts once. New questions update the total.</p>'}catch(e){host.innerHTML='<div class="mbu-muted">'+esc(e.message)+'</div>'}
}
async function renderDevices(modal){
  const host=modal.querySelector('[data-cloud-devices]');if(!host)return;
  host.innerHTML='<div class="mbu-muted">Loading devices…</div>';
  try{
    const rows=await MBUSupabase.listDevices();
    host.innerHTML=rows.map(r=>'<div class="mbu-cloud-row"><div><strong>'+esc(r.current?'This device':(r.device_label||'Browser device'))+'</strong><span>'+esc(relativeTime(r.last_seen_at))+(r.app_build?' · '+esc(r.app_build):'')+'</span></div>'+(r.current?'<span class="mbu-pill">Current</span>':'<button type="button" class="secondary" data-remove-device="'+esc(r.device_id)+'">Forget</button>')+'</div>').join('')||'<div class="mbu-muted">No synced devices found.</div>';
    host.querySelectorAll('[data-remove-device]').forEach(btn=>btn.onclick=async()=>{if(!confirm('Forget this device entry? It can reappear if that device syncs again.'))return;btn.disabled=true;try{await MBUSupabase.removeDevice(btn.dataset.removeDevice);await renderDevices(modal)}catch(e){modal.querySelector('[data-account-message]').textContent=e.message;btn.disabled=false}})
  }catch(e){host.innerHTML='<div class="mbu-muted">Could not load devices: '+esc(e.message)+'</div>'}
}
async function renderHistory(modal){
  const host=modal.querySelector('[data-cloud-history]');if(!host)return;
  host.innerHTML='<div class="mbu-muted">Loading restore points…</div>';
  try{
    const rows=await MBUSupabase.listHistory(20);
    if(!rows.length){host.innerHTML='<div class="mbu-muted">No cloud restore points yet. Restore points appear automatically as synced progress changes.</div>';return}
    host.innerHTML='<div class="mbu-restore-summary"><strong>Recent restore points</strong><span>Up to 10 versions per study area are retained automatically.</span></div>'+rows.map(r=>'<div class="mbu-cloud-row mbu-restore-row"><div><strong>'+esc(storeLabel(r.store_key))+'</strong><span>'+esc(relativeTime(r.saved_at))+' · '+esc(new Date(r.saved_at).toLocaleString())+'</span><small>Cloud revision '+Number(r.server_revision||0)+'</small></div><button type="button" class="secondary" data-restore-version="'+Number(r.id)+'">Restore</button></div>').join('');
    host.querySelectorAll('[data-restore-version]').forEach(btn=>btn.onclick=async()=>{if(!confirm('Restore this version? Your current cloud progress is saved first, so you can undo the restore if needed.'))return;btn.disabled=true;const message=modal.querySelector('[data-account-message]');try{message.textContent='Restoring progress…';await MBUSupabase.restoreVersion(Number(btn.dataset.restoreVersion));message.textContent='Restore complete.'}catch(e){message.textContent=e.message;btn.disabled=false}})
  }catch(e){host.innerHTML='<div class="mbu-muted">Could not load restore points: '+esc(e.message)+'</div>'}
}
window.SRNACloudManagement={renderStats,renderDevices,renderHistory};
})();