/* Lazy Phase 3 question-level analytics for operator admins. */
(()=>{'use strict';
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
const href=(uid,m)=>m?.practiceUrl||new URL('equipment/exam-1/studio.html?question='+encodeURIComponent(String(uid||'')),MBUSupabase.appRoot||location.href).href;
let rows=[],meta=new Map(),contentReview=new Map(),measuredCount=0,reviewGroupCount=0;
function reasons(r){const a=[];if(Number(r.report_count||0)>0||r.review_signal==='reported')a.push('Learner report');if(r.review_signal==='high_miss')a.push('High miss rate');if(r.review_signal==='very_easy')a.push('Very easy');for(const x of contentReview.get(String(r.question_id))||[])a.push(x);if(r.needs_review&&!a.length)a.push('Analytics review flag');return[...new Set(a)]}function signal(r){return reasons(r).join(' · ')}
function needsReview(r){return!!r.needs_review||contentReview.has(String(r.question_id))}
function matches(r,filter,q){
  if(filter==='review'&&!needsReview(r))return false;
  if(filter==='content'&&!contentReview.has(String(r.question_id)))return false;
  if(filter==='reported'&&Number(r.report_count||0)<1)return false;
  if(filter==='mature'&&Number(r.unique_learners||0)<25)return false;
  if(filter==='early'&&(Number(r.unique_learners||0)<5||Number(r.unique_learners||0)>=25))return false;
  if(filter==='collecting'&&Number(r.unique_learners||0)>=5)return false;
  if(!q)return true;const m=meta.get(r.question_id)||{},hay=[r.question_id,m.label,m.topic,m.stem,m.source].join(' ').toLowerCase();return hay.includes(q)
}
function draw(host){
  const filter=host.querySelector('[data-qa-filter]')?.value||'all',q=(host.querySelector('[data-qa-search]')?.value||'').trim().toLowerCase(),shown=rows.filter(r=>matches(r,filter,q));
  const out=host.querySelector('[data-qa-rows]');
  out.innerHTML=shown.map(r=>{const m=meta.get(r.question_id)||{},acc=r.first_attempt_accuracy==null?'—':Number(r.first_attempt_accuracy)+'%',sig=signal(r),learners=Number(r.unique_learners||0),reports=Number(r.report_count||0);
    return '<div class="mbu-cloud-row"><div><strong>'+esc(m.label||r.question_id)+' · '+esc(r.question_id)+'</strong><span>'+learners+' learner'+(learners===1?'':'s')+' · '+acc+' first-attempt accuracy · '+Number(r.adaptive_first_attempts||0)+' Adaptive · '+(learners>=25?'Population sample (25+)':learners>=5?'Early sample (5–24)':'Insufficient sample (under 5)')+'</span>'+(sig?'<small><b>Why review:</b> '+esc(sig)+'</small>':'')+'<small>'+esc(m.topic||'Unknown topic')+(m.source?' · '+esc(m.source):'')+(m.stem?' · '+esc(m.stem):'')+'</small><small>'+reports+' report'+(reports===1?'':'s')+(r.avg_response_ms?' · avg '+Math.round(Number(r.avg_response_ms)/1000)+'s response':'')+'</small></div><a class="secondary" target="_blank" rel="noopener" href="'+esc(href(r.question_id,m))+'">Open exact question</a></div>'
  }).join('')||'<div class="mbu-muted">No questions match this view.</div>';
  host.querySelector('[data-qa-count]').textContent=shown.length+' shown · '+measuredCount+' measured · '+contentReview.size+' content-review items';
}
async function mount(host,msg){
  host.innerHTML='<div class="admin-loading">Loading question analytics…</div>';
  try{
    const reviewUrl=new URL('reports/question-content-review.json',MBUSupabase.appRoot||location.href),[data,modes,trend,review]=await Promise.all([MBUSupabase.adminRpc('snar_admin_question_analytics',{p_limit:10000,p_review_only:false}),MBUSupabase.adminRpc('snar_admin_mode_analytics'),MBUSupabase.adminRpc('snar_admin_usage_trend',{p_days:30}),MBUBuild.fetchJSON(reviewUrl,{cache:'force-cache'})]);
    const measured=Array.isArray(data)?data:[];measuredCount=measured.length;contentReview=new Map();reviewGroupCount=Array.isArray(review?.candidates)?review.candidates.length:0;
    for(const c of review?.candidates||[]){const label=c.type==='exact_stem_variant'?'Exact-stem variant':c.type==='near_duplicate_key_variation'?'Near-duplicate key variation':'Content review';for(const uid of c.questions||[]){const key=String(uid),list=contentReview.get(key)||[];if(!list.includes(label))list.push(label);contentReview.set(key,list)}}
    const merged=new Map(measured.map(x=>[String(x.question_id),x]));for(const uid of contentReview.keys())if(!merged.has(uid))merged.set(uid,{question_id:uid,unique_learners:0,first_attempt_accuracy:null,adaptive_first_attempts:0,report_count:0,maturity:'unmeasured',review_signal:'none',needs_review:false});rows=[...merged.values()];
    if(!window.MBUQuestionSearch)await window.MBUBuild?.loadScript?.('question-search.js');
    const index=await window.MBUQuestionSearch?.getIndex?.()||[];meta=new Map(index.map(x=>[x.uid,x]));
    const modeData=Array.isArray(modes)?modes:[],trendData=Array.isArray(trend)?trend:[],canonicalIndex=index.filter(x=>x.bank!=='generated'),totalQuestions=canonicalIndex.length;
    const totalAttempts=modeData.reduce((n,x)=>n+Number(x.first_attempts||0),0),weightedCorrect=modeData.reduce((n,x)=>n+Number(x.first_attempts||0)*Number(x.accuracy||0)/100,0),overallAccuracy=totalAttempts?Math.round(weightedCorrect/totalAttempts):0;
    const maxModeLearners=modeData.reduce((n,x)=>Math.max(n,Number(x.unique_users||0)),0),maxLearners=measured.reduce((n,x)=>Math.max(n,Number(x.unique_learners||0)),0),mature=measured.filter(x=>Number(x.unique_learners||0)>=25).length,coveragePct=totalQuestions?Math.round(measuredCount/totalQuestions*1000)/10:0;
    const reviewCount=rows.filter(needsReview).length,eligible=measured.filter(x=>Number(x.unique_learners||0)>=5),tooEasy=eligible.filter(x=>Number(x.first_attempt_accuracy)>=90).length,difficult=eligible.filter(x=>Number(x.first_attempt_accuracy)<40).length,healthy=eligible.filter(x=>Number(x.first_attempt_accuracy)>=40&&Number(x.first_attempt_accuracy)<90).length,reported=measured.filter(x=>Number(x.report_count||0)>0).length,slow=measured.filter(x=>Number(x.response_samples||0)>=5&&Number(x.avg_response_ms||0)>=45000).length;
    const readiness=mature?mature+' question'+(mature===1?' has':'s have')+' reached 25 learners and can contribute population difficulty.':'Still collecting data. No question has reached 25 learners yet, so Adaptive difficulty is not using population performance.';
    const modeRows=modeData.map(x=>'<tr><td><strong>'+esc(x.session_mode)+'</strong></td><td>'+Number(x.first_attempts||0).toLocaleString()+'</td><td>'+Number(x.unique_users||0)+'</td><td>'+Number(x.accuracy||0)+'%</td><td>'+Number(x.first_attempts_7d||0).toLocaleString()+'</td><td>'+Number(x.first_attempts_30d||0).toLocaleString()+'</td></tr>').join('')||'<tr><td colspan="6">No mode usage yet.</td></tr>';
    const trendRows=trendData.slice().reverse().map(x=>'<div class="mbu-cloud-row"><div><strong>'+esc(x.day)+'</strong><span>'+Number(x.first_attempts||0)+' first attempts · '+Number(x.accuracy||0)+'% accuracy · '+Number(x.adaptive_first_attempts||0)+' Adaptive</span>'+(x.avg_response_ms?'<small>Avg response '+Math.round(Number(x.avg_response_ms)/1000)+'s from '+Number(x.response_samples||0)+' timed responses</small>':'')+'</div></div>').join('')||'<div class="mbu-muted">No first-attempt activity in this window.</div>';
    host.innerHTML='<div class="qa-dashboard">'+
      '<div class="qa-summary-grid">'+
        '<div class="qa-stat"><span>First attempts</span><strong>'+totalAttempts.toLocaleString()+'</strong><small>Across all study modes</small></div>'+
        '<div class="qa-stat"><span>Overall accuracy</span><strong>'+overallAccuracy+'%</strong><small>Weighted first-attempt accuracy</small></div>'+
        '<div class="qa-stat"><span>Questions seen</span><strong>'+measuredCount.toLocaleString()+'</strong><small>Of '+totalQuestions.toLocaleString()+' canonical questions</small></div>'+
        '<div class="qa-stat"><span>Bank coverage</span><strong>'+coveragePct+'%</strong><small>Questions with learner data</small></div>'+
        '<div class="qa-stat"><span>Questions with 5+ learners</span><strong>'+eligible.length.toLocaleString()+'</strong><small>Early performance sample; '+mature+' reached 25+ learners</small></div>'+
      '</div>'+
      '<section class="qa-readiness"><div><strong>Calibration status</strong><p>'+esc(readiness)+'</p></div><div class="qa-progress" aria-label="'+coveragePct+' percent question coverage"><i style="width:'+Math.min(100,coveragePct)+'%"></i></div><small>'+measuredCount.toLocaleString()+' / '+totalQuestions.toLocaleString()+' questions have learner data · most-used mode reaches '+maxModeLearners+' contributing learners</small></section>'+
      '<div class="qa-two-col">'+
        '<section class="admin-card"><div class="admin-card-head"><div><h4>Question performance</h4><p>Early descriptive results from questions with 5+ learners; not validated population difficulty until 25+ learners.</p></div></div><div class="qa-performance">'+
          '<div><strong>'+eligible.length+'</strong><span>5+ learner sample</span></div>'+
          '<div><strong>'+healthy+'</strong><span>40–89% correct (descriptive)</span></div>'+
          '<div><strong>'+tooEasy+'</strong><span>≥90% correct (review difficulty)</span></div>'+
          '<div><strong>'+difficult+'</strong><span>&lt;40% correct (review clarity)</span></div>'+
        '</div></section>'+
        '<section class="admin-card"><div class="admin-card-head"><div><h4>Needs attention</h4><p>Signals worth checking, not automatic evidence that a question is wrong.</p></div></div><div class="qa-attention">'+
          '<button data-jump-filter="review"><strong>'+reviewCount+'</strong><span>Needs review</span></button>'+
          '<button data-jump-filter="reported"><strong>'+reported+'</strong><span>Reported questions</span></button>'+
          '<button data-jump-filter="content"><strong>'+contentReview.size+'</strong><span>Duplicate/content-review items</span></button>'+
          '<div><strong>'+slow+'</strong><span>Slow-response items ≥45s</span></div>'+
        '</div></section>'+
      '</div>'+
      '<section class="admin-card"><div class="admin-card-head"><div><h4>Usage by study mode</h4><p>How first attempts are being generated.</p></div></div><div class="qa-table-wrap"><table class="qa-table"><thead><tr><th>Mode</th><th>Attempts</th><th>Learners</th><th>Accuracy</th><th>7 days</th><th>30 days</th></tr></thead><tbody>'+modeRows+'</tbody></table></div></section>'+
      '<details class="admin-card qa-explorer"><summary>Question explorer <span>Search individual question analytics</span></summary><div class="mbu-app-tools__actions"><input data-qa-search type="search" placeholder="Search question, topic, source…" aria-label="Search question analytics"><select data-qa-filter aria-label="Filter question analytics"><option value="all">All measured</option><option value="review">Needs review</option><option value="content">Content review</option><option value="reported">Reported</option><option value="mature">25+ learners</option><option value="early">5–24 learners</option><option value="collecting">Collecting &lt;5</option></select></div><p class="mbu-muted" data-qa-count></p><div data-qa-rows></div></details>'+
      '<details class="admin-card qa-advanced"><summary>Advanced analytics <span>Daily history and CAT readiness details</span></summary><p class="mbu-muted"><b>CAT readiness:</b> '+esc(readiness)+'</p><h5>First-attempt usage by mode</h5><p class="mbu-muted">Compact summary is shown above. Detailed activity is retained here for auditing.</p><h5>Recent first-attempt activity</h5><p class="mbu-muted">Daily aggregate only. No learner identities or raw response rows are shown.</p><div data-qa-trend>'+trendRows+'</div><p class="mbu-muted">Content review groups: '+reviewGroupCount+' · 25+ learners: '+mature+'</p></details>'+
    '</div>';
    host.querySelector('[data-qa-search]').oninput=()=>draw(host);host.querySelector('[data-qa-filter]').onchange=()=>draw(host);host.querySelectorAll('[data-jump-filter]').forEach(btn=>btn.onclick=()=>{const details=host.querySelector('.qa-explorer'),select=host.querySelector('[data-qa-filter]');details.open=true;select.value=btn.dataset.jumpFilter||'all';draw(host);details.scrollIntoView({behavior:'smooth',block:'start'})});draw(host)
  }catch(e){host.innerHTML='<div class="mbu-muted">Question analytics could not load: '+esc(e.message)+'</div>';if(msg)msg.textContent=e.message}
}
window.SRNAQuestionAnalytics={mount};
})();