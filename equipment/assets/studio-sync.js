(function(){
  const ctx=window.MBU_CONTEXT||{},courseId=String(ctx.courseId||''),examId=String(ctx.examId||'');
  const STORE=courseId==='equipment'&&examId==='exam-1'?'mbu_exam1_studio_v1':`mbu_studio_${courseId}_${examId}_v1`;
  let cache=null,reportContext=null;

  function normalizeBank(bank){
    const s=String(bank ?? '').trim();
    if(/^\d+$/.test(s)) return 'b'+s;
    const haz=s.match(/^haz(\d+)$/i);
    if(haz) return 'h'+haz[1];
    if(/^b\d+$/i.test(s)||/^h\d+$/i.test(s)||s==='hh') return s.toLowerCase();
    return s;
  }

  function normalizeKey(k){
    return String(k||'')
      .replace(/^bhaz(\d+)-/i,'h$1-')
      .replace(/^bb(\d+)-/i,'b$1-')
      .replace(/^bh(\d+)-/i,'h$1-')
      .replace(/^bhh-/i,'hh-');
  }

  function plainObject(v){return !!v&&typeof v==='object'&&!Array.isArray(v)}
  function normalizeSessionState(v){
    if(!plainObject(v)||!Array.isArray(v.uids))return null;
    const uids=[],seen=new Set();
    for(const raw of v.uids){
      if(typeof raw!=='string'&&typeof raw!=='number')continue;
      const uid=normalizeKey(raw);if(!uid||seen.has(uid))continue;seen.add(uid);uids.push(uid)
    }
    if(!uids.length)return null;
    const n=Number(v.pos),pos=Number.isFinite(n)?Math.max(0,Math.min(Math.trunc(n),uids.length-1)):0,answers={};
    if(plainObject(v.answers))for(const [rawUid,result] of Object.entries(v.answers)){
      const uid=normalizeKey(rawUid);
      if(!seen.has(uid)||!plainObject(result))continue;
      const selected=Array.isArray(result.selected)?[...new Set(result.selected.map(Number).filter(x=>Number.isInteger(x)&&x>=0))].sort((a,b)=>a-b):[];
      const matching=plainObject(result.matching)?Object.fromEntries(Object.entries(result.matching).map(([k,val])=>[String(k),String(val)])) : null;
      if(!Array.isArray(result.selected)&&!matching)continue;
      answers[uid]={ok:!!result.ok,selected,...(matching?{matching}:{}),at:Number.isFinite(Number(result.at))?Number(result.at):0}
    }
    const allowedModes=new Set(['custom','smart','due','missed','flagged','weak','adaptive']);const mode=allowedModes.has(String(v.mode||''))?String(v.mode):'',crosses={};
    if(mode==='adaptive'&&plainObject(v.crosses))for(const [rawKey,on] of Object.entries(v.crosses)){if(!on)continue;const cut=rawKey.lastIndexOf(':');if(cut<1)continue;const uid=normalizeKey(rawKey.slice(0,cut)),opt=Number(rawKey.slice(cut+1));if(seen.has(uid)&&Number.isInteger(opt)&&opt>=0)crosses[uid+':'+opt]=true}
    const out={uids,pos,answers,updated:Number.isFinite(Number(v.updated))?Number(v.updated):0};if(mode)out.mode=mode;if(mode==='adaptive')out.crosses=crosses;if(plainObject(v.coverageMeta)){out.coverageMeta={sessionId:String(v.coverageMeta.sessionId||''),newCount:Math.max(0,Number(v.coverageMeta.newCount)||0),reviewCount:Math.max(0,Number(v.coverageMeta.reviewCount)||0),cycle:Math.max(1,Number(v.coverageMeta.cycle)||1),reviewRate:Math.max(0,Math.min(1,Number(v.coverageMeta.reviewRate)||0))}}
    if(v.crossCourse===true)out.crossCourse=true;
    if(typeof v.sessionId==='string')out.sessionId=v.sessionId;else if(out.coverageMeta?.sessionId)out.sessionId=out.coverageMeta.sessionId;
    if(plainObject(v.lifecycle))out.lifecycle=Object.fromEntries(Object.entries(v.lifecycle).filter(([k,n])=>Number.isFinite(Number(n))&&Number(n)>0));
    if(plainObject(v.questionSessionIds))out.questionSessionIds=Object.fromEntries(Object.entries(v.questionSessionIds).filter(([uid,id])=>seen.has(uid)&&typeof id==='string'));
    if(v.mode==='adaptive'&&plainObject(v.adaptive)){
      const a=v.adaptive,seenUids=Array.isArray(a.seenUids)?[...new Set(a.seenUids.map(normalizeKey).filter(Boolean))]:uids.slice(),topicCounts=plainObject(a.topicCounts)?Object.fromEntries(Object.entries(a.topicCounts).map(([k,n])=>[String(k),Math.max(0,Number(n)||0)])):{};
      out.mode='adaptive';
      const poolUids=Array.isArray(a.poolUids)?[...new Set(a.poolUids.map(normalizeKey).filter(Boolean))]:uids.slice(),seenContentKeys=Array.isArray(a.seenContentKeys)?[...new Set(a.seenContentKeys.map(String).filter(Boolean))]:[];
      const theta=Math.max(-2.5,Math.min(2.5,Number(a.theta)||0)),se=Math.max(0,Number(a.se)||0),information=Math.max(0,Number(a.information)||0);
      const numericMap=v=>plainObject(v)?Object.fromEntries(Object.entries(v).map(([k,n])=>[String(k),Math.max(0,Number(n)||0)])):{};
      out.adaptive={mode:'adaptive',version:Math.max(2,Number(a.version)||2),engine:String(a.engine||''),theta,se,information,currentDifficulty:a.currentDifficulty!=null&&Number.isFinite(Number(a.currentDifficulty))?Math.max(-2.5,Math.min(2.5,Number(a.currentDifficulty))):null,currentChallenge:a.currentChallenge!=null&&Number.isFinite(Number(a.currentChallenge))?Number(a.currentChallenge):null,currentProbability:a.currentProbability!=null&&Number.isFinite(Number(a.currentProbability))?Number(a.currentProbability):null,currentUncertainty:a.currentUncertainty!=null&&Number.isFinite(Number(a.currentUncertainty))?Math.max(0,Math.min(1,Number(a.currentUncertainty))):null,currentFocus:String(a.currentFocus||''),currentTopic:String(a.currentTopic||''),currentConcept:String(a.currentConcept||''),currentPhase:String(a.currentPhase||''),level:Math.max(1,Math.min(5,Number(a.level)||3)),answered:Math.max(0,Number(a.answered)||0),correct:Math.max(0,Number(a.correct)||0),maxQuestions:Math.max(1,Math.min(200,Number(a.maxQuestions)||50)),seenUids,seenContentKeys,poolUids,topicCounts,focusCounts:numericMap(a.focusCounts),blueprintTargets:numericMap(a.blueprintTargets),selectionSeed:(Number(a.selectionSeed)>>>0)||1,selectionStep:Math.max(0,Number(a.selectionStep)||0),path:Array.isArray(a.path)?a.path.filter(plainObject).slice(-200):[],currentLevel:Math.max(1,Math.min(5,Number(a.currentLevel)||Number(a.level)||3))}
    }
    return out
  }

  function db(){
    if(cache)return cache;
    let d;
    try{d=JSON.parse(localStorage.getItem(STORE)||'{}')}catch(e){d={}}
    if(!plainObject(d))d={};
    let changed=false;
    for(const field of ['ans','flags','crosses']){
      const present=Object.prototype.hasOwnProperty.call(d,field),raw=d[field],src=plainObject(raw)?raw:{},next={};
      if(present&&!plainObject(raw))changed=true;
      for(const [k,v] of Object.entries(src)){
        const nk=normalizeKey(k);if(nk!==k)changed=true;
        if(field==='ans'){
          if(!plainObject(v)){changed=true;continue}
          if(nk in next){changed=true;continue}
          next[nk]=v
        }else{
          if(!v){changed=true;continue}
          if(v!==true)changed=true;
          if(nk in next){changed=true;continue}
          next[nk]=true
        }
      }
      d[field]=next
    }
    const reportPresent=Object.prototype.hasOwnProperty.call(d,'reports'),rawReports=d.reports,reports=Array.isArray(rawReports)?rawReports:[];
    if(reportPresent&&!Array.isArray(rawReports))changed=true;
    d.reports=[];
    for(const x of reports){
      if(!plainObject(x)){changed=true;continue}
      const uid=normalizeKey(x.uid),bank=normalizeBank(x.bank);
      if(uid!==x.uid||bank!==x.bank)changed=true;
      d.reports.push({...x,uid,bank})
    }
    for(const field of ['active','searchReturn']){
      if(!Object.prototype.hasOwnProperty.call(d,field))continue;
      const next=normalizeSessionState(d[field]);
      if(JSON.stringify(next)!==JSON.stringify(d[field]))changed=true;
      d[field]=next
    }
    cache=d;
    if(changed)save(d);
    else try{lastSerialized=JSON.stringify(d)}catch(e){}
    return cache
  }
  let lastSerialized='';
  function save(d){
    cache=d;
    try{
      const serialized=JSON.stringify(d);
      if(serialized===lastSerialized)return;
      localStorage.setItem(STORE,serialized);
      window.MBUAppCore?.touchStore?.(STORE);
      lastSerialized=serialized;
    }catch(e){}
  }
  window.addEventListener('storage',e=>{if(e.key===STORE){cache=null;lastSerialized=''}});
  function key(bank,q){
    if(q&&q.uid)return normalizeKey(q.uid);
    return normalizeBank(bank)+'-'+q.id
  }
  function topicOf(q){
    const direct=String(q.topic||q.lec||'').trim();
    if(direct)return direct;
    const refs=Array.isArray(q.ref)?q.ref.join('; '):'';
    const src=String(q.citation||q.src||refs||'').trim().toLowerCase().replace(/₂/g,'2');
    if(src.includes('workstation hazards')||src.includes('hazards & safety'))return 'Workstation Hazards';
    if(src.includes('medical gas'))return 'Medical Gases';
    if(src.includes('airway equipment'))return 'Airway';
    if(src.includes('co2')&&src.includes('scaveng'))return 'CO₂ & Scavenging';
    if(src.includes('monitoring')||src.includes('intraoperative assessment'))return 'Monitoring';
    return String(q.concept||'Other');
  }
  function flagged(bank,q){return !!db().flags[key(bank,q)]}
  function toggleFlag(bank,q){const d=db(),k=key(bank,q),next=!d.flags[k];if(next)d.flags[k]=true;else delete d.flags[k];save(d);return next}
  function stageAnswer(bank,q,ok){if(q?.courseId&&(q.courseId!==courseId||q.examId!==examId)){const store=q.courseId==='equipment'&&q.examId==='exam-1'?'mbu_exam1_studio_v1':`mbu_studio_${q.courseId}_${q.examId}_v1`;let d;try{d=JSON.parse(localStorage.getItem(store)||'null')}catch{}if(!plainObject(d))d={};if(!plainObject(d.ans))d.ans={};d.ans[key(bank,q)]={ok:!!ok,at:Date.now(),topic:topicOf(q),bank:normalizeBank(bank)};localStorage.setItem(store,JSON.stringify(d));window.MBUAppCore?.touchStore?.(store);return db()}const d=db(),b=normalizeBank(bank),k=key(b,q);d.ans[k]={ok:!!ok,at:Date.now(),topic:topicOf(q),bank:b};return d}
  function answer(bank,q,ok){const d=stageAnswer(bank,q,ok);save(d)}

  function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
  function arr(v){return Array.isArray(v)?v:(v===undefined||v===null?[]:[v])}
  function questionMeta(bank,q,extra){
    const b=normalizeBank(bank),isMatching=String(q.type||'').toLowerCase()==='matching',options=arr(q.options??q.c),answer=isMatching?[]:arr(q.answer??q.correct??q.a).map(Number).filter(Number.isInteger);
    const selected=arr(extra&&extra.selected).map(Number).filter(Number.isInteger),matching=isMatching?{prompts:arr(q.matching?.prompts??q.prompts).map(String),choices:arr(q.matching?.choices??q.choices).map(String),answer:plainObject(q.matching?.answer)?q.matching.answer:(plainObject(q.answer)?q.answer:{}),selected:plainObject(extra&&extra.matching)?extra.matching:{}}:null;
    const sourceRaw=q.citation??q.src??q.ref??'';
    return {
      uid:key(b,q),
      bank:b,
      bankLabel:String((extra&&extra.bankLabel)||q.bankLabel||b),
      set:String((extra&&extra.set)??q.set??q.setn??''),
      questionNumber:String((extra&&extra.questionNumber)??q.id??q.seq??''),
      topic:topicOf(q),
      stem:String(q.stem||q.q||''),
      options:options.map(String),
      answerIndexes:answer,
      answerText:answer.map(i=>options[i]).filter(v=>v!==undefined).map(String),
      selectedIndexes:selected,
      selectedText:selected.map(i=>options[i]).filter(v=>v!==undefined).map(String),
      ...(matching?{matching}:{}),
      explanation:String(q.explanation||q.why||q.exp||''),
      source:Array.isArray(sourceRaw)?sourceRaw.join('; '):String(sourceRaw||''),
      page:String(q.page||''),
      pageUrl:(()=>{const u=new URL(location.origin+location.pathname);u.searchParams.set('question',key(b,q));return u.href})(),
      build:(document.body.innerHTML.match(/MBU_BUILD:([^<*]+)/)||[])[1]?.trim()||'',
    };
  }

  function ensureReportUI(){
    if(document.getElementById('mbu-report-modal'))return;
    const style=document.createElement('style');style.id='mbu-report-style';style.textContent=
      '#mbu-report-modal{display:none;position:fixed;inset:0;z-index:10020;background:#0008;align-items:center;justify-content:center;padding:14px}'+
      '#mbu-report-modal.open{display:flex}.mbu-report-card{width:min(600px,100%);max-height:92vh;overflow:auto;background:#fff;border-radius:14px;padding:20px;box-shadow:0 14px 42px #0006;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#1a202c}'+
      '.mbu-report-head{display:flex;justify-content:space-between;gap:12px;align-items:center}.mbu-report-head h2{margin:0;font-size:20px;color:#1a365d}.mbu-report-close{border:0;background:transparent;font-size:28px;cursor:pointer;color:#4a5568}.mbu-report-summary{margin:12px 0;padding:11px;background:#f7fafc;border:1px solid #e2e8f0;border-radius:9px;font-size:14px}.mbu-report-field{display:grid;gap:6px;margin-top:12px}.mbu-report-field label{font-weight:750;font-size:14px}.mbu-report-field select,.mbu-report-field input,.mbu-report-field textarea{width:100%;font:inherit;font-size:16px;padding:10px;border:1px solid #a0aec0;border-radius:8px;background:#fff}.mbu-report-field textarea{min-height:110px;resize:vertical}.mbu-report-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:16px;flex-wrap:wrap}.mbu-report-btn{border:0;border-radius:8px;padding:10px 14px;font-weight:800;cursor:pointer;background:#1a365d;color:#fff}.mbu-report-btn.out{background:#fff;color:#1a365d;border:1px solid #1a365d}.mbu-report-status{min-height:20px;margin-top:10px;font-size:13px;color:#4a5568}.mbu-report-btn:disabled{opacity:.55;cursor:not-allowed}';
    document.head.appendChild(style);
    const wrap=document.createElement('div');
    wrap.innerHTML='<div id="mbu-report-modal" role="dialog" aria-modal="true" aria-labelledby="mbu-report-title"><form class="mbu-report-card" id="mbu-report-form"><div class="mbu-report-head"><h2 id="mbu-report-title">Report Question Issue</h2><button class="mbu-report-close" type="button" aria-label="Close report form">&times;</button></div><div class="mbu-report-summary" id="mbu-report-summary"></div><div class="mbu-report-field"><label for="mbu-report-reason">What is wrong?</label><select id="mbu-report-reason" required><option value="">Choose an issue</option><option>Wrong answer</option><option>Ambiguous question</option><option>Typo / wording</option><option>Explanation issue</option><option>Source / citation issue</option><option>Image / figure issue</option><option>Other</option></select></div><div class="mbu-report-field"><label for="mbu-report-comment">Tell me what you noticed</label><textarea id="mbu-report-comment" maxlength="2000" required placeholder="Example: I think choices B and C could both be correct because..."></textarea></div><div class="mbu-report-actions"><button class="mbu-report-btn out" type="button" id="mbu-report-cancel">Cancel</button><button class="mbu-report-btn" type="submit" id="mbu-report-submit">Send Report</button></div><div class="mbu-report-status" id="mbu-report-status" role="status" aria-live="polite"></div></form></div>';
    document.body.appendChild(wrap);
    const modal=document.getElementById('mbu-report-modal');
    const close=()=>{modal.classList.remove('open');reportContext=null};
    document.querySelector('.mbu-report-close').onclick=close;
    document.getElementById('mbu-report-cancel').onclick=close;
    modal.addEventListener('click',e=>{if(e.target===modal)close()});
    document.getElementById('mbu-report-form').addEventListener('submit',submitReport);
  }

  async function submitReport(e){
    e.preventDefault();
    if(!reportContext)return;
    const reason=document.getElementById('mbu-report-reason').value.trim();
    const comment=document.getElementById('mbu-report-comment').value.trim();
    if(!reason||!comment)return;
    const submit=document.getElementById('mbu-report-submit'),status=document.getElementById('mbu-report-status');
    submit.disabled=true;status.textContent='Sending report…';
    const payload={...reportContext,reason,comment,date:new Date().toISOString()};
    const d=db(),local={...payload,sent:false};
    d.reports.push(local);save(d);
    window.MBUStudyIntelligence?.addIssue?.(payload.bank,{uid:payload.uid,bank:payload.bank,bankLabel:payload.bankLabel,set:payload.set,id:payload.questionNumber,topic:payload.topic,stem:payload.stem},{bankLabel:payload.bankLabel,set:payload.set,questionId:payload.questionNumber,reason,comment,href:payload.pageUrl});
    try{
      if(!window.MBUSupabase?.submitQuestionReport)throw new Error('Sign in to send question reports.');
      local.remoteId=await window.MBUSupabase.submitQuestionReport(payload);
      local.sent=true;local.sentAt=new Date().toISOString();save(d);
      status.textContent='Report sent. Thank you.';
      setTimeout(()=>{document.getElementById('mbu-report-modal')?.classList.remove('open');reportContext=null},700);
    }catch(err){
      status.textContent='Could not send online. A backup was saved on this device. '+err.message;
    }finally{submit.disabled=false}
  }


  function pendingReports(){
    return db().reports.filter(r=>r&&typeof r==='object'&&!r.sent);
  }

  function legacyPayload(r){
    return {
      uid:normalizeKey(r.uid||((r.bank||'unknown')+'-saved')),
      bank:normalizeBank(r.bank||''),
      bankLabel:String(r.bankLabel||r.bank||'Unknown bank'),
      set:String(r.set||''),
      questionNumber:String(r.questionNumber||''),
      topic:String(r.topic||''),
      stem:String(r.stem||'Saved question report'),
      options:arr(r.options).map(String),
      answerIndexes:arr(r.answerIndexes),
      answerText:arr(r.answerText).map(String),
      selectedIndexes:arr(r.selectedIndexes),
      selectedText:arr(r.selectedText).map(String),
      explanation:String(r.explanation||''),
      source:String(r.source||''),
      page:String(r.page||''),
      pageUrl:(()=>{try{const u=new URL(String(r.pageUrl||location.href),location.href);return u.origin+u.pathname}catch{return location.origin+location.pathname}})(),
      build:String(r.build||'legacy-local-report'),
      reason:String(r.reason||'Other').slice(0,120),
      comment:String(r.comment||r.reason||'Saved before online reporting was enabled.').slice(0,2000),
      date:String(r.date||new Date().toISOString())
    };
  }

  async function sendSavedReports(onProgress){
    if(!window.MBUSupabase?.submitQuestionReport)throw new Error('Sign in to send saved question reports.');
    const d=db(),pending=d.reports.filter(r=>r&&typeof r==='object'&&!r.sent);
    let sent=0,failed=0;
    for(let i=0;i<pending.length;i++){
      const r=pending[i],payload=legacyPayload(r);
      try{
        r.remoteId=await window.MBUSupabase.submitQuestionReport(payload);
        r.sent=true;r.sentAt=new Date().toISOString();r.migrated=!(r.comment||r.answerIndexes||r.options);
        sent++;
      }catch(err){
        r.lastSendError=String(err&&err.message?err.message:err);
        failed++;
      }
      save(d);
      if(typeof onProgress==='function')onProgress({done:i+1,total:pending.length,sent,failed});
    }
    return {total:pending.length,sent,failed};
  }

  function report(bank,q,extra){
    ensureReportUI();
    reportContext=questionMeta(bank,q,extra||{});
    const modal=document.getElementById('mbu-report-modal');
    document.getElementById('mbu-report-summary').innerHTML='<b>'+esc(reportContext.bankLabel)+(reportContext.set?' · Set '+esc(reportContext.set):'')+(reportContext.questionNumber?' · Q'+esc(reportContext.questionNumber):'')+'</b><div style="margin-top:5px">'+esc(reportContext.stem)+'</div><div style="margin-top:5px;color:#718096">ID: '+esc(reportContext.uid)+'</div>';
    document.getElementById('mbu-report-reason').value='';
    document.getElementById('mbu-report-comment').value='';
    document.getElementById('mbu-report-status').textContent='';
    modal.classList.add('open');
    setTimeout(()=>document.getElementById('mbu-report-reason')?.focus(),0);
    return true;
  }

  window.MBUStudio={STORE,db,save,key,flagged,toggleFlag,stageAnswer,answer,report,normalizeBank,topicOf,questionMeta,pendingReports,sendSavedReports};
})();